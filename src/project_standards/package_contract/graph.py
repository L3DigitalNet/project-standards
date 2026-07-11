"""Pure cross-payload graph, ownership, migration, and catalog validation."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from project_standards.package_contract.catalog import (
    CatalogPackageEntry,
    CatalogRole,
    validate_catalog_source,
)
from project_standards.package_contract.diagnostics import (
    PackageContractError,
    PackageFinding,
    sort_findings,
)
from project_standards.package_contract.payload import (
    ContributionDeclaration,
    PayloadManifest,
    RelationEvidenceKind,
    WholeArtifactDeclaration,
    contributions_overlap,
)
from project_standards.package_contract.repository import PackageRepository


@dataclass(frozen=True, slots=True)
class _OutputOwner:
    standard_id: str
    version: str
    kind: str
    declaration: WholeArtifactDeclaration | ContributionDeclaration


def _finding(
    code: str,
    standard_id: str,
    version: str,
    identity: str,
    message: str,
) -> PackageFinding:
    return PackageFinding(
        code=code,
        severity="error",
        standard_id=standard_id,
        version=version,
        path="standards",
        identity=identity,
        message=message,
        hint="make package relationships, ownership, and migrations explicit and conflict-free",
    )


def _payloads(repository: PackageRepository) -> list[PayloadManifest]:
    return sorted(
        (payload.manifest for payload in repository.payloads),
        key=lambda manifest: (
            manifest.payload.standard,
            manifest.payload.version.sort_key,
        ),
    )


def _validate_relations(
    payloads: list[PayloadManifest], family_ids: set[str]
) -> list[PackageFinding]:
    findings: list[PackageFinding] = []
    extends_edges: set[tuple[str, str]] = set()
    extends_versions: dict[tuple[str, str], set[str]] = defaultdict(set)
    for payload in payloads:
        standard_id = payload.payload.standard
        version = payload.payload.version.value
        relation_groups = {
            "companion": payload.relations.companions,
            "extends": payload.relations.extends,
            "conflict": payload.relations.conflicts,
        }
        for relation, targets in relation_groups.items():
            for target in targets:
                identity = f"{relation}:{target}"
                if target == standard_id:
                    findings.append(
                        _finding(
                            "PC-RELATION-SELF",
                            standard_id,
                            version,
                            identity,
                            "package relation cannot target its own family",
                        )
                    )
                elif target not in family_ids:
                    findings.append(
                        _finding(
                            "PC-RELATION-MISSING",
                            standard_id,
                            version,
                            identity,
                            "package relation targets an unknown family",
                        )
                    )
                elif relation == "extends":
                    extends_edges.add((standard_id, target))
                    extends_versions[(standard_id, target)].add(version)

        expected_evidence = {
            (RelationEvidenceKind.EXTENDS.value, target) for target in payload.relations.extends
        } | {
            (RelationEvidenceKind.CONFLICTS.value, target) for target in payload.relations.conflicts
        }
        evidence_keys = [
            (evidence.kind.value, evidence.target) for evidence in payload.relation_evidence
        ]
        resource_by_id = {resource.id: resource for resource in payload.resources}
        invalid_evidence = set(evidence_keys) != expected_evidence or len(evidence_keys) != len(
            set(evidence_keys)
        )
        invalid_evidence = invalid_evidence or any(
            evidence.resource not in resource_by_id
            or resource_by_id[evidence.resource].role != "relation-evidence"
            or resource_by_id[evidence.resource].media_type != "text/markdown"
            for evidence in payload.relation_evidence
        )
        if invalid_evidence:
            findings.append(
                _finding(
                    "PC-RELATION-EVIDENCE",
                    standard_id,
                    version,
                    "relations",
                    "extends and conflicts must have exact payload-owned ADR evidence",
                )
            )

        hidden = set(payload.capabilities.consumes_platform) & family_ids
        for target in sorted(hidden):
            findings.append(
                _finding(
                    "PC-HIDDEN-REQUIREMENT",
                    standard_id,
                    version,
                    f"capability:{target}",
                    "platform capability consumption cannot name a package family",
                )
            )

    adjacency: dict[str, set[str]] = defaultdict(set)
    for source, target in extends_edges:
        adjacency[source].add(target)
    for source, target in sorted(extends_edges):
        if _reachable(adjacency, target, source):
            for version in sorted(extends_versions[(source, target)]):
                findings.append(
                    _finding(
                        "PC-RELATION-CYCLE",
                        source,
                        version,
                        f"extends:{target}",
                        "extends relations form a cycle",
                    )
                )
    return findings


def _reachable(adjacency: dict[str, set[str]], start: str, target: str) -> bool:
    pending = [start]
    seen: set[str] = set()
    while pending:
        current = pending.pop()
        if current == target:
            return True
        if current in seen:
            continue
        seen.add(current)
        pending.extend(sorted(adjacency.get(current, ()), reverse=True))
    return False


def _target_overlap(left: str, right: str) -> bool:
    return left == right or left.startswith(f"{right}/") or right.startswith(f"{left}/")


def _shared_signature(contribution: ContributionDeclaration) -> tuple[object, ...]:
    return (
        contribution.target.original,
        contribution.adapter.value,
        contribution.scope,
        contribution.source.original if contribution.source else None,
        contribution.source_digest.value if contribution.source_digest else None,
        contribution.provider,
        contribution.policy.value,
    )


def _validate_outputs(payloads: list[PayloadManifest]) -> list[PackageFinding]:
    findings: list[PackageFinding] = []
    outputs: list[_OutputOwner] = []
    shared: dict[str, list[_OutputOwner]] = defaultdict(list)
    for payload in payloads:
        standard_id = payload.payload.standard
        version = payload.payload.version.value
        outputs.extend(
            _OutputOwner(standard_id, version, "artifact", artifact)
            for artifact in payload.artifacts
        )
        for contribution in payload.contributions:
            owner = _OutputOwner(standard_id, version, "contribution", contribution)
            outputs.append(owner)
            if contribution.shared_identity is not None:
                shared[contribution.shared_identity].append(owner)

    mismatched_shared: set[str] = set()
    for shared_id, owners in sorted(shared.items()):
        if len({owner.standard_id for owner in owners}) < 2:
            continue
        signatures = {
            _shared_signature(owner.declaration)
            for owner in owners
            if isinstance(owner.declaration, ContributionDeclaration)
        }
        if len(signatures) > 1:
            mismatched_shared.add(shared_id)
            for owner in sorted(
                owners,
                key=lambda item: (
                    item.standard_id,
                    item.version,
                    item.declaration.id,
                ),
            ):
                findings.append(
                    _finding(
                        "PC-SHARED-IDENTITY-MISMATCH",
                        owner.standard_id,
                        owner.version,
                        f"shared:{shared_id}:{owner.declaration.id}",
                        "shared contribution owners do not normalize identically",
                    )
                )

    ordered = sorted(
        outputs,
        key=lambda owner: (
            owner.standard_id,
            owner.version,
            owner.kind,
            owner.declaration.id,
        ),
    )
    for index, left in enumerate(ordered):
        for right in ordered[index + 1 :]:
            if left.standard_id == right.standard_id:
                continue
            if not _owners_overlap(left, right):
                continue
            left_contribution = (
                left.declaration if isinstance(left.declaration, ContributionDeclaration) else None
            )
            right_contribution = (
                right.declaration
                if isinstance(right.declaration, ContributionDeclaration)
                else None
            )
            left_shared = (
                left_contribution.shared_identity if left_contribution is not None else None
            )
            right_shared = (
                right_contribution.shared_identity if right_contribution is not None else None
            )
            if left_shared is not None and left_shared == right_shared:
                if left_shared in mismatched_shared:
                    continue
                if (
                    left_contribution is not None
                    and right_contribution is not None
                    and _shared_signature(left_contribution)
                    == _shared_signature(right_contribution)
                ):
                    continue
            findings.extend(
                _owner_pair_findings(
                    "PC-OUTPUT-OVERLAP",
                    left,
                    right,
                    "independent packages claim overlapping repository output",
                )
            )

    for payload in payloads:
        for extension in payload.extensions:
            if extension.preferred_root is None:
                continue
            root = extension.preferred_root.removesuffix("/")
            for owner in ordered:
                if owner.standard_id == payload.payload.standard:
                    continue
                if not _target_overlap(root, owner.declaration.target.original):
                    continue
                extension_owner = _OutputOwner(
                    payload.payload.standard,
                    payload.payload.version.value,
                    "extension",
                    owner.declaration,
                )
                findings.extend(
                    _owner_pair_findings(
                        "PC-EXTENSION-OUTPUT-OVERLAP",
                        extension_owner,
                        owner,
                        "managed output overlaps another package's consumer-owned extension root",
                        left_identity=f"extension:{extension.id}",
                    )
                )
    return findings


def _owner_pair_findings(
    code: str,
    left: _OutputOwner,
    right: _OutputOwner,
    message: str,
    *,
    left_identity: str | None = None,
) -> list[PackageFinding]:
    left_id = left_identity or f"{left.kind}:{left.declaration.id}"
    right_id = f"{right.kind}:{right.declaration.id}"
    return [
        _finding(
            code,
            left.standard_id,
            left.version,
            f"{left_id}|{right.standard_id}:{right_id}",
            message,
        ),
        _finding(
            code,
            right.standard_id,
            right.version,
            f"{right_id}|{left.standard_id}:{left_id}",
            message,
        ),
    ]


def _owners_overlap(left: _OutputOwner, right: _OutputOwner) -> bool:
    left_target = left.declaration.target.original
    right_target = right.declaration.target.original
    if left.kind == "artifact" or right.kind == "artifact":
        return _target_overlap(left_target, right_target)
    if not isinstance(left.declaration, ContributionDeclaration) or not isinstance(
        right.declaration, ContributionDeclaration
    ):
        return False
    return contributions_overlap(left.declaration, right.declaration)


def _validate_migrations(
    repository: PackageRepository, payloads: list[PayloadManifest]
) -> list[PackageFinding]:
    findings: list[PackageFinding] = []
    versions: dict[str, set[str]] = defaultdict(set)
    migration_edges: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for family in repository.families:
        versions[family.manifest.standard.id].update(
            entry.version.value for entry in family.manifest.versions
        )

    for payload in payloads:
        standard_id = payload.payload.standard
        version = payload.payload.version.value
        artifact_ids = {artifact.id for artifact in payload.artifacts}
        contribution_ids = {item.id for item in payload.contributions}
        legacy_state_ids = {state.id for state in payload.legacy_states}
        used_legacy_states: set[str] = set()
        for migration in payload.migrations:
            invalid_endpoint = False
            for endpoint in (migration.from_endpoint, migration.to_endpoint):
                if endpoint.package_version is not None and (
                    endpoint.package_version.value not in versions[standard_id]
                ):
                    invalid_endpoint = True
                if endpoint.legacy_state is not None:
                    if endpoint.legacy_state not in legacy_state_ids:
                        invalid_endpoint = True
                    else:
                        used_legacy_states.add(endpoint.legacy_state)
            if invalid_endpoint:
                findings.append(
                    _finding(
                        "PC-MIGRATION-ENDPOINT",
                        standard_id,
                        version,
                        f"migration:{migration.id}",
                        "migration references an unknown package version or legacy state",
                    )
                )
            for affected in migration.affected:
                kind, identity = affected.split(":", 1)
                if (kind == "artifact" and identity not in artifact_ids) or (
                    kind == "contribution" and identity not in contribution_ids
                ):
                    findings.append(
                        _finding(
                            "PC-MIGRATION-AFFECTED",
                            standard_id,
                            version,
                            f"migration:{migration.id}:{affected}",
                            "migration affected identity is not declared by its payload",
                        )
                    )
            source = migration.from_endpoint.package_version
            target = migration.to_endpoint.package_version
            if source is not None and target is not None and not invalid_endpoint:
                migration_edges[standard_id][source.value].add(target.value)
                if migration.reversible:
                    migration_edges[standard_id][target.value].add(source.value)
        if legacy_state_ids - used_legacy_states:
            findings.append(
                _finding(
                    "PC-MIGRATION-ENDPOINT",
                    standard_id,
                    version,
                    "legacy-states",
                    "payload declares an unused legacy state",
                )
            )

    if repository.catalog is None:
        return findings
    try:
        validate_catalog_source(
            repository.catalog,
            repository.family_map,
            repository.payload_map,
        )
    except PackageContractError as exc:
        findings.append(
            _finding(
                "PC-CATALOG-GRAPH",
                "project-standards",
                "",
                "catalog",
                str(exc),
            )
        )
        return findings

    by_standard: dict[str, list[CatalogPackageEntry]] = defaultdict(list)
    for entry in repository.catalog.packages:
        by_standard[entry.id].append(entry)
    for standard_id, raw_entries in sorted(by_standard.items()):
        entries = sorted(raw_entries, key=lambda item: item.version.sort_key)
        default = next(
            (entry for entry in entries if entry.role is CatalogRole.DEFAULT),
            None,
        )
        if default is None:
            continue
        for entry in entries:
            if entry.version.major == default.version.major:
                continue
            if not _reachable(
                migration_edges[standard_id],
                default.version.value,
                entry.version.value,
            ):
                findings.append(
                    _finding(
                        "PC-MIGRATION-ENTRY",
                        standard_id,
                        entry.version.value,
                        f"catalog:{repository.catalog.catalog_major}",
                        "advertised non-default package major has no entry path",
                    )
                )
            if not _reachable(
                migration_edges[standard_id],
                entry.version.value,
                default.version.value,
            ):
                findings.append(
                    _finding(
                        "PC-MIGRATION-EXIT",
                        standard_id,
                        entry.version.value,
                        f"catalog:{repository.catalog.catalog_major}",
                        "advertised non-default package major has no exit path",
                    )
                )
    return findings


def validate_package_graph(repository: PackageRepository) -> tuple[PackageFinding, ...]:
    """Return deterministic findings without executing any provider."""
    payloads = _payloads(repository)
    findings = list(repository.findings)
    family_ids = {family.manifest.standard.id for family in repository.families}
    findings.extend(_validate_relations(payloads, family_ids))
    findings.extend(_validate_outputs(payloads))
    findings.extend(_validate_migrations(repository, payloads))
    return tuple(sort_findings(findings))


def validate_package_repository(
    repository: PackageRepository,
) -> tuple[PackageFinding, ...]:
    """Validate the complete normalized repository without executing providers."""
    return validate_package_graph(repository)
