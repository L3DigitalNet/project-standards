"""Validate graph-wide standard metadata rules."""

from __future__ import annotations

import fnmatch
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from project_standards.adopt.engine import resolve_source
from project_standards.adopt.errors import ManifestError
from project_standards.adopt.manifest import ArtifactProvenance
from project_standards.standard_manifest import AdoptionMode
from project_standards.standards_graph.model import (
    GraphFinding,
    StandardNode,
    StandardsGraph,
    sort_findings,
)

_PLATFORM_CAPABILITIES = frozenset(
    {
        "project-standards.validate",
        "project-standards.fix",
        "project-standards.drift-check",
        "project-standards.id-next",
        "project-standards.extract",
        "project-standards.render",
    }
)
_ADOPT_RESOURCE_REQUIRED_MODES = frozenset(
    {AdoptionMode.VALIDATOR, AdoptionMode.COPY_ADOPT, AdoptionMode.CLI}
)


def _rel(path: object) -> str:
    return str(path)


def _finding(
    code: str,
    node: StandardNode,
    path: str,
    message: str,
    hint: str,
) -> GraphFinding:
    return GraphFinding(
        code=code,
        severity="error",
        standard_id=node.standard_id,
        path=path,
        message=message,
        hint=hint,
    )


def _validate_missing_manifests(
    graph: StandardsGraph, require_all_manifests: bool
) -> list[GraphFinding]:
    if not require_all_manifests:
        return []
    return [
        GraphFinding(
            code="SG-MANIFEST-MISSING",
            severity="error",
            standard_id=path.name,
            path=_rel(path),
            message=f"standard directory {path.name!r} has no standard.toml",
            hint="add a standard.toml manifest or remove the standard directory",
        )
        for path in graph.missing_manifest_dirs
    ]


def _validate_namespaces(graph: StandardsGraph) -> list[GraphFinding]:
    owners: dict[str, list[StandardNode]] = defaultdict(list)
    for node in graph.standards:
        for namespace in node.manifest.config.namespaces:
            owners[namespace].append(node)

    findings: list[GraphFinding] = []
    for namespace, nodes in sorted(owners.items()):
        if len(nodes) < 2:
            continue
        ids = ", ".join(node.standard_id for node in nodes)
        for node in nodes:
            findings.append(
                _finding(
                    "SG-CONFIG-DUPLICATE-NAMESPACE",
                    node,
                    _rel(node.manifest_path),
                    f"namespace {namespace!r} is claimed by multiple standards: {ids}",
                    f"choose one owning standard for namespace {namespace!r}",
                )
            )
    return findings


def _validate_artifact_manifests(graph: StandardsGraph) -> list[GraphFinding]:
    findings = [
        GraphFinding(
            code="SG-ARTIFACT-MANIFEST-ORPHAN",
            severity="error",
            standard_id=path.parent.name,
            path=_rel(path),
            message=f"packaged artifact manifest for {path.parent.name!r} is not linked",
            hint="add [artifacts].manifest to the standard.toml or remove the orphan manifest",
        )
        for path in graph.orphan_artifact_manifests
    ]
    for node in graph.standards:
        artifact_link = node.manifest.artifacts
        declared = artifact_link is not None
        if artifact_link is not None:
            assert node.artifact_manifest_path is not None
            expected = (
                graph.root
                / "src"
                / "project_standards"
                / "bundles"
                / node.standard_id
                / "adopt.toml"
            )
            if not node.artifact_manifest_path.is_relative_to(graph.root):
                findings.append(
                    _finding(
                        "SG-ARTIFACT-MANIFEST-ESCAPE",
                        node,
                        artifact_link.manifest,
                        f"{node.standard_id} artifact manifest resolves outside the repository",
                        "link the standard's packaged adopt.toml inside the repository bundle tree",
                    )
                )
            elif node.artifact_manifest_path != expected:
                findings.append(
                    _finding(
                        "SG-ARTIFACT-MANIFEST-MISMATCH",
                        node,
                        artifact_link.manifest,
                        f"{node.standard_id} artifact link does not name its own packaged manifest",
                        f"set manifest to src/project_standards/bundles/{node.standard_id}/adopt.toml",
                    )
                )
        if declared and node.artifact_manifest is None:
            assert node.artifact_manifest_path is not None
            findings.append(
                _finding(
                    "SG-ARTIFACT-MANIFEST-MISSING",
                    node,
                    _rel(node.artifact_manifest_path),
                    f"{node.standard_id} links an artifact manifest that does not exist",
                    "create the linked adopt.toml or remove the [artifacts] table",
                )
            )
            continue
        if declared and node.manifest.standard.adoption in {
            AdoptionMode.NONE,
            AdoptionMode.REFERENCE_ONLY,
        }:
            findings.append(
                _finding(
                    "SG-ARTIFACT-NONADOPTABLE",
                    node,
                    _rel(node.manifest_path),
                    f"{node.standard_id} is non-adoptable but links packaged artifacts",
                    "remove the artifact link or choose an adoptable mode",
                )
            )
        artifact_manifest = node.artifact_manifest
        if artifact_manifest is None or node.artifact_manifest_path is None:
            continue
        bundles_dir = node.artifact_manifest_path.parent.parent
        for artifact in artifact_manifest.artifacts:
            try:
                packaged = resolve_source(artifact, node.standard_id, bundles_dir)
            except ManifestError as exc:
                findings.append(
                    _finding(
                        "SG-ARTIFACT-SOURCE-MISSING",
                        node,
                        _rel(node.artifact_manifest_path),
                        str(exc),
                        "restore the packaged source or correct the artifact declaration",
                    )
                )
                continue
            if artifact.provenance in {
                ArtifactProvenance.SOURCE_OWNED,
                ArtifactProvenance.GENERATED,
            }:
                assert artifact.canonical is not None
                canonical_rel = Path(artifact.canonical)
                canonical = (graph.root / canonical_rel).resolve()
                if (
                    canonical_rel.is_absolute()
                    or ".." in canonical_rel.parts
                    or not canonical.is_relative_to(graph.root)
                    or not canonical.is_file()
                ):
                    findings.append(
                        _finding(
                            "SG-ARTIFACT-CANONICAL-MISSING",
                            node,
                            artifact.canonical,
                            f"canonical source for {packaged.name!r} is missing or unsafe",
                            "declare an existing repository-relative canonical source",
                        )
                    )
                elif (
                    artifact.provenance is ArtifactProvenance.SOURCE_OWNED
                    and packaged.read_bytes() != canonical.read_bytes()
                ):
                    findings.append(
                        _finding(
                            "SG-ARTIFACT-PARITY",
                            node,
                            artifact.canonical,
                            f"packaged artifact {packaged.name!r} differs from its canonical source",
                            "refresh the packaged mirror from the canonical source",
                        )
                    )
            source_rel = artifact.source or ""
            if (source_rel.startswith("skills/") or "/skills/" in source_rel) and (
                artifact.dest is None or not artifact.dest.startswith(".agents/skills/")
            ):
                findings.append(
                    _finding(
                        "SG-ARTIFACT-SKILL-DEST",
                        node,
                        _rel(node.artifact_manifest_path),
                        f"standard-packaged skill installs outside .agents/skills: {artifact.dest!r}",
                        "install standard-owned skills under .agents/skills/<skill-id>/",
                    )
                )
    return findings


def _validate_resources_and_providers(graph: StandardsGraph) -> list[GraphFinding]:
    findings: list[GraphFinding] = []
    for node in graph.standards:
        resources = node.manifest.resources.as_dict()
        if (
            node.manifest.standard.adoption in _ADOPT_RESOURCE_REQUIRED_MODES
            and "adopt" not in resources
        ):
            findings.append(
                _finding(
                    "SG-RESOURCE-ADOPT-MISSING",
                    node,
                    _rel(node.manifest_path),
                    f"{node.standard_id} is adoptable but has no 'adopt' resource",
                    'add adopt = "adopt.md" to [resources] or use a non-adoptable adoption mode',
                )
            )
        for provider in node.manifest.providers:
            for field_name, resource_id in (
                ("input_schema", provider.input_schema),
                ("output_schema", provider.output_schema),
            ):
                if resource_id is not None and resource_id not in resources:
                    findings.append(
                        _finding(
                            "SG-PROVIDER-SCHEMA-MISSING",
                            node,
                            _rel(node.manifest_path),
                            f"provider {provider.operation!r} references {field_name} resource "
                            f"{resource_id!r} that is not declared",
                            "declare the schema in [resources] or remove the provider schema reference",
                        )
                    )
    return findings


def _extension_connects(left: StandardNode, right: StandardNode) -> bool:
    return (
        right.standard_id in left.manifest.relations.extends and _has_extension_adr_resource(left)
    ) or (
        left.standard_id in right.manifest.relations.extends and _has_extension_adr_resource(right)
    )


def _target_suffix(pattern: str) -> str | None:
    prefix = "**/*"
    if pattern.startswith(prefix) and len(pattern) > len(prefix):
        return pattern[len(prefix) :]
    return None


def _literal_has_suffix(pattern: str, suffix: str) -> bool:
    return not any(ch in pattern for ch in "*?[]") and pattern.endswith(suffix)


def targets_may_overlap(left: str, right: str) -> bool:
    """Return True when two consumer-file glob targets have an obvious intersection."""
    if left == right or left in {"**/*", "**/*.*"} or right in {"**/*", "**/*.*"}:
        return True
    if fnmatch.fnmatch(left, right) or fnmatch.fnmatch(right, left):
        return True
    left_suffix = _target_suffix(left)
    right_suffix = _target_suffix(right)
    if left_suffix is not None and right_suffix is not None:
        return left_suffix == right_suffix
    if left_suffix is not None:
        return _literal_has_suffix(right, left_suffix)
    if right_suffix is not None:
        return _literal_has_suffix(left, right_suffix)
    return False


def _validate_authorities(graph: StandardsGraph) -> list[GraphFinding]:
    findings: list[GraphFinding] = []
    authority_rows = [
        (node, authority)
        for node in graph.standards
        for authority in node.manifest.authority
        if authority.mutates
    ]
    for (left_node, left), (right_node, right) in combinations(authority_rows, 2):
        if left_node.standard_id == right_node.standard_id:
            continue
        if left.domain != right.domain or left.concern != right.concern:
            continue
        if left.owner == right.owner:
            continue
        if not targets_may_overlap(left.target, right.target):
            continue
        if _extension_connects(left_node, right_node):
            continue
        for node, other in ((left_node, right_node), (right_node, left_node)):
            findings.append(
                _finding(
                    "SG-AUTHORITY-CONFLICT",
                    node,
                    _rel(node.manifest_path),
                    f"{node.standard_id} authority conflicts with {other.standard_id} "
                    f"for {left.domain}/{left.concern}",
                    "use one owner, split target globs, or declare an ADR-backed extends relationship",
                )
            )
    return findings


def _has_extension_adr_resource(node: StandardNode) -> bool:
    resources = node.manifest.resources.as_dict()
    return "extension_adr" in resources


def _validate_relationship_targets(graph: StandardsGraph) -> list[GraphFinding]:
    findings: list[GraphFinding] = []
    ids = graph.ids
    for node in graph.standards:
        relation_map = {
            "companions": node.manifest.relations.companions,
            "extends": node.manifest.relations.extends,
            "conflicts": node.manifest.relations.conflicts,
        }
        for relation_name, targets in relation_map.items():
            for target in targets:
                if target not in ids:
                    findings.append(
                        _finding(
                            "SG-REL-MISSING-STANDARD",
                            node,
                            _rel(node.manifest_path),
                            f"{relation_name} target {target!r} is not a known standard",
                            "declare only existing standard ids in relations",
                        )
                    )
        if node.manifest.relations.extends and not _has_extension_adr_resource(node):
            findings.append(
                _finding(
                    "SG-REL-EXTENDS-NO-ADR",
                    node,
                    _rel(node.manifest_path),
                    f"{node.standard_id} declares extends without an ADR resource",
                    "add a bundle-local extension_adr resource documenting the extension",
                )
            )
    return findings


def _extends_cycle_participants(graph: StandardsGraph) -> frozenset[str]:
    edges = {node.standard_id: tuple(node.manifest.relations.extends) for node in graph.standards}
    cycle_participants: set[str] = set()
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str, stack: tuple[str, ...]) -> None:
        if node_id in visiting:
            cycle_start = stack.index(node_id)
            cycle_participants.update(stack[cycle_start:])
            return
        if node_id in visited:
            return
        visiting.add(node_id)
        for target in edges.get(node_id, ()):
            if target in edges:
                visit(target, (*stack, target))
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in edges:
        visit(node_id, (node_id,))
    return frozenset(cycle_participants)


def _validate_extends_cycles(graph: StandardsGraph) -> list[GraphFinding]:
    cycle_participants = _extends_cycle_participants(graph)
    if not cycle_participants:
        return []
    return [
        _finding(
            "SG-REL-EXTENDS-CYCLE",
            node,
            _rel(node.manifest_path),
            "extends relationships contain a cycle",
            "remove the cycle so extension relationships form a directed acyclic graph",
        )
        for node in graph.standards
        if node.standard_id in cycle_participants
    ]


def _validate_capabilities(graph: StandardsGraph) -> list[GraphFinding]:
    findings: list[GraphFinding] = []
    provided_by_standard = {
        capability for node in graph.standards for capability in node.manifest.capabilities.provides
    }
    for node in graph.standards:
        for capability in node.manifest.capabilities.consumes_platform:
            if capability in provided_by_standard:
                findings.append(
                    _finding(
                        "SG-CAPABILITY-STANDARD-CONSUMED",
                        node,
                        _rel(node.manifest_path),
                        f"consumes_platform {capability!r} is provided by a standard",
                        "model standard-to-standard relationships with companions or extends, not consumes_platform",
                    )
                )
            elif capability not in _PLATFORM_CAPABILITIES:
                findings.append(
                    _finding(
                        "SG-CAPABILITY-PLATFORM-UNKNOWN",
                        node,
                        _rel(node.manifest_path),
                        f"platform capability {capability!r} is not registered",
                        "add the capability to the platform registry or remove it from consumes_platform",
                    )
                )
    return findings


def validate_graph(
    graph: StandardsGraph, *, require_all_manifests: bool = False
) -> list[GraphFinding]:
    """Return deterministic graph validation findings."""
    findings: list[GraphFinding] = []
    findings.extend(_validate_missing_manifests(graph, require_all_manifests))
    findings.extend(_validate_artifact_manifests(graph))
    findings.extend(_validate_namespaces(graph))
    findings.extend(_validate_resources_and_providers(graph))
    findings.extend(_validate_authorities(graph))
    findings.extend(_validate_relationship_targets(graph))
    findings.extend(_validate_extends_cycles(graph))
    findings.extend(_validate_capabilities(graph))
    return sort_findings(findings)
