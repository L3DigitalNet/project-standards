"""Plan complete repository reconciliation against one immutable virtual tree.

The planner is deliberately a pure mutation boundary: it may read declared
payload and repository inputs and invoke phase-bounded read-only providers, but
it exposes no filesystem write primitive. The executor consumes the resulting
whole-file preconditions and proposed bytes in a later phase.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import cast

from project_standards.control_plane.adapters import (
    AdapterRegistry,
    EditorConfigAdapter,
    JsonAdapter,
    JsoncAdapter,
    MarkdownBlockAdapter,
    TomlAdapter,
    UnitChange,
    WholeFileAdapter,
    YamlAdapter,
)
from project_standards.control_plane.adapters.base import AdapterUnit, DocumentAdapter
from project_standards.control_plane.codec import semantic_digest
from project_standards.control_plane.diagnostics import (
    ActionKind,
    ControlAction,
    ControlFinding,
    ControlPlaneError,
    actions_to_jsonable,
    findings_to_jsonable,
    sort_actions,
    sort_findings,
)
from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.models import (
    AcceptedTrack,
    CentralLock,
    LockedInput,
    LockedUnit,
    LockHeader,
    UnitProvenance,
)
from project_standards.control_plane.providers import (
    ProviderInvocation,
    ProviderResult,
    invoke_provider,
    resolve_referenced_inputs,
)
from project_standards.control_plane.resolution import (
    AcceptedTrackTransition,
    ResolutionRequest,
    ResolutionResult,
    ResolvedPackage,
    TrackTransitionKind,
    resolve_packages,
)
from project_standards.control_plane.snapshot import (
    EntryKind,
    RepositorySnapshot,
    SnapshotEntry,
)
from project_standards.package_contract.paths import (
    PackageVersion,
    SafeRelativePath,
    Sha256Digest,
)
from project_standards.package_contract.payload import (
    AdapterKind,
    ArtifactPolicy,
    ContributionDeclaration,
    JsonObject,
    JsonValue,
    ProviderEffect,
    ProviderKind,
    ProviderOperation,
    ProviderPhase,
    SharedIdentity,
    WholeArtifactDeclaration,
    contributions_overlap,
)

type ProviderRunner = Callable[[ProviderInvocation], ProviderResult]


def _digest(content: bytes) -> Sha256Digest:
    return Sha256Digest(f"sha256:{hashlib.sha256(content).hexdigest()}")


@dataclass(frozen=True, slots=True)
class PlannerRequest:
    """Bind all explicit inputs required for one read-only plan."""

    repo: Path
    resolution: ResolutionRequest
    payloads: tuple[InstalledPayload, ...]
    provider_runner: ProviderRunner | None = None


@dataclass(frozen=True, slots=True)
class TargetPrecondition:
    """Bind one target to the exact whole-file state observed by planning."""

    target: str
    digest: str


@dataclass(frozen=True, slots=True)
class PlannedTarget:
    """Retain executor-only proposed bytes beside a public target identity."""

    target: str
    content: bytes
    mode: str | None


@dataclass(frozen=True, slots=True)
class PlannedUnit:
    """Describe one unit transition and its complete package provenance."""

    kind: ActionKind
    target: str
    adapter: str
    scope: str
    owners: tuple[str, ...]
    versions: tuple[tuple[str, str], ...]
    provenance: UnitProvenance
    before_digest: str | None
    after_digest: str | None


@dataclass(frozen=True, slots=True)
class VerificationRequest:
    """Defer one selected payload's declared verify provider until apply."""

    standard_id: str
    version: str
    provider_id: str


@dataclass(frozen=True, slots=True)
class ProviderNotice:
    """Report bounded provider output without retaining emitted text."""

    standard_id: str
    version: str
    provider_id: str
    message: str


@dataclass(frozen=True, slots=True)
class ReconciliationPlan:
    """Carry public plan facts and executor-only proposed state immutably."""

    applicable: bool
    actions: tuple[ControlAction, ...]
    units: tuple[PlannedUnit, ...]
    findings: tuple[ControlFinding, ...]
    targets: tuple[PlannedTarget, ...]
    preconditions: tuple[TargetPrecondition, ...]
    resolution: ResolutionResult
    verification_requests: tuple[VerificationRequest, ...]
    provider_notices: tuple[ProviderNotice, ...]
    next_lock: CentralLock

    def proposed_content(self, target: str) -> bytes:
        """Return the complete proposed bytes for one declared target."""
        for item in self.targets:
            if item.target == target:
                return item.content
        raise ControlPlaneError(f"plan does not contain target: {target}")

    def to_jsonable(self) -> dict[str, JsonValue]:
        """Return stable public facts without proposed or provider content bytes."""
        packages = [
            {
                "standard_id": package.standard_id,
                "applied": cast(
                    JsonValue,
                    package.applied.model_dump(mode="json"),
                ),
                "effective_config": cast(JsonValue, package.effective_config),
            }
            for package in self.resolution.packages
        ]
        transitions = [_transition_json(item) for item in self.resolution.track_transitions]
        return {
            "applicable": self.applicable,
            "actions": cast(JsonValue, actions_to_jsonable(self.actions)),
            "units": cast(
                JsonValue,
                [
                    {
                        **asdict(unit),
                        "kind": unit.kind.value,
                        "provenance": unit.provenance.value,
                        "versions": dict(unit.versions),
                    }
                    for unit in self.units
                ],
            ),
            "findings": cast(JsonValue, findings_to_jsonable(self.findings)),
            "preconditions": cast(
                JsonValue,
                [asdict(item) for item in self.preconditions],
            ),
            "resolution": {
                "packages": cast(JsonValue, packages),
                "track_transitions": cast(JsonValue, transitions),
            },
            "verification_requests": cast(
                JsonValue,
                [asdict(item) for item in self.verification_requests],
            ),
            "provider_notices": cast(
                JsonValue,
                [asdict(item) for item in self.provider_notices],
            ),
            "next_lock": cast(JsonValue, self.next_lock.model_dump(mode="json")),
        }


@dataclass(frozen=True, slots=True)
class _Intent:
    standard_id: str
    version: str
    target: SafeRelativePath
    adapter: AdapterKind
    scope: str
    policy: ArtifactPolicy
    mode: str | None
    shared_identity: SharedIdentity | None
    provenance: UnitProvenance
    content: bytes
    declaration: ContributionDeclaration | None


@dataclass(frozen=True, slots=True)
class _DesiredUnit:
    intent: _Intent
    unit: AdapterUnit


@dataclass(frozen=True, slots=True)
class _DesiredGroup:
    target: SafeRelativePath
    adapter: AdapterKind
    scope: str
    owners: tuple[str, ...]
    versions: tuple[tuple[str, str], ...]
    policy: ArtifactPolicy
    mode: str | None
    provenance: UnitProvenance
    unit: AdapterUnit


def _transition_json(transition: AcceptedTrackTransition) -> dict[str, JsonValue]:
    return {
        "standard_id": transition.standard_id,
        "kind": transition.kind.value,
        "previous": cast(
            JsonValue,
            transition.previous.model_dump(mode="json") if transition.previous else None,
        ),
        "current": cast(
            JsonValue,
            transition.current.model_dump(mode="json") if transition.current else None,
        ),
    }


def _registry() -> AdapterRegistry:
    registry = AdapterRegistry()
    for kind, adapter in (
        (AdapterKind.WHOLE_FILE, WholeFileAdapter()),
        (AdapterKind.TOML, TomlAdapter()),
        (AdapterKind.JSON, JsonAdapter()),
        (AdapterKind.JSONC, JsoncAdapter()),
        (AdapterKind.YAML, YamlAdapter()),
        (AdapterKind.EDITORCONFIG, EditorConfigAdapter()),
        (AdapterKind.MARKDOWN_BLOCK, MarkdownBlockAdapter()),
    ):
        registry.register(kind, adapter)
    return registry


def _payload_map(payloads: Iterable[InstalledPayload]) -> dict[tuple[str, str], InstalledPayload]:
    result: dict[tuple[str, str], InstalledPayload] = {}
    for payload in payloads:
        identity = payload.manifest.payload
        key = (identity.standard, identity.version.value)
        if key in result:
            raise ControlPlaneError("planner inputs contain a duplicate installed payload")
        result[key] = payload
    return result


def _selected_payloads(
    resolution: ResolutionResult,
    payloads: Mapping[tuple[str, str], InstalledPayload],
) -> tuple[tuple[ResolvedPackage, InstalledPayload], ...]:
    selected: list[tuple[ResolvedPackage, InstalledPayload]] = []
    for package in resolution.packages:
        key = (package.standard_id, package.applied.resolved.value)
        payload = payloads.get(key)
        if (
            payload is None
            or payload.integrity.aggregate_digest != package.applied.payload_digest
            or payload.manifest.payload.standard != package.standard_id
            or payload.manifest.payload.version != package.applied.resolved
        ):
            raise ControlPlaneError(
                f"selected installed payload does not match resolution: {package.standard_id}"
            )
        selected.append((package, payload))
    return tuple(sorted(selected, key=lambda item: item[0].standard_id.encode("utf-8")))


def _read_payload_file(
    payload: InstalledPayload,
    path: SafeRelativePath,
    expected: Sha256Digest,
) -> bytes:
    inventory = {item.path.original: item.digest for item in payload.integrity.inventory}
    if inventory.get(path.original) != expected:
        raise ControlPlaneError("planned payload source is outside verified integrity")
    candidate = payload.root / path.normalized
    try:
        if candidate.is_symlink():
            raise ControlPlaneError("planned payload source cannot be a symlink")
        resolved = candidate.resolve(strict=True)
        root = payload.root.resolve(strict=True)
        if not resolved.is_relative_to(root) or not resolved.is_file():
            raise ControlPlaneError("planned payload source escapes selected payload")
        content = resolved.read_bytes()
    except OSError as exc:
        raise ControlPlaneError("planned payload source could not be read") from exc
    if _digest(content) != expected:
        raise ControlPlaneError("planned payload source changed after integrity validation")
    return content


def _artifact_intent(
    package: ResolvedPackage,
    payload: InstalledPayload,
    artifact: WholeArtifactDeclaration,
) -> _Intent:
    return _Intent(
        standard_id=package.standard_id,
        version=package.applied.resolved.value,
        target=artifact.target,
        adapter=AdapterKind.WHOLE_FILE,
        scope="$file",
        policy=artifact.policy,
        mode=artifact.mode,
        shared_identity=None,
        provenance=UnitProvenance.SOURCE,
        content=_read_payload_file(payload, artifact.source, artifact.digest),
        declaration=None,
    )


def _snapshot_json(snapshot: RepositorySnapshot) -> JsonObject:
    return {
        entry.path.original: {
            "kind": entry.kind.value,
            "precondition_digest": entry.precondition_digest.value,
            "content_digest": entry.content_digest.value if entry.content_digest else None,
            "mode": entry.mode,
        }
        for entry in snapshot.entries
    }


def _contribution_content(
    *,
    request: PlannerRequest,
    package: ResolvedPackage,
    payload: InstalledPayload,
    contribution: ContributionDeclaration,
    snapshots: JsonObject,
    notices: list[ProviderNotice],
) -> tuple[bytes, UnitProvenance]:
    if contribution.source is not None and contribution.source_digest is not None:
        return (
            _read_payload_file(payload, contribution.source, contribution.source_digest),
            UnitProvenance.SOURCE,
        )
    provider_id = contribution.provider
    if provider_id is None:
        raise ControlPlaneError("semantic contribution has no content source")
    runner = request.provider_runner or invoke_provider
    result = runner(
        ProviderInvocation(
            repo=request.repo,
            payload=payload,
            standard_id=package.standard_id,
            version=package.applied.resolved,
            provider_id=provider_id,
            operation=ProviderOperation.RENDER,
            effective_config=package.effective_config,
            snapshots={
                **snapshots,
                "planned_contribution": {
                    "id": contribution.id,
                    "target": contribution.target.original,
                    "adapter": contribution.adapter.value,
                    "scope": contribution.scope,
                },
            },
        )
    )
    if result.effect is not ProviderEffect.CONTENT or result.content is None:
        raise ControlPlaneError("render provider did not return declared content")
    if result.output_notice is not None:
        notices.append(
            ProviderNotice(
                package.standard_id,
                package.applied.resolved.value,
                provider_id,
                result.output_notice,
            )
        )
    return result.content, UnitProvenance.PROVIDER


def _desired_intents(
    request: PlannerRequest,
    selected: tuple[tuple[ResolvedPackage, InstalledPayload], ...],
    snapshot: RepositorySnapshot,
    referenced_inputs: tuple[LockedInput, ...],
    notices: list[ProviderNotice],
) -> tuple[_Intent, ...]:
    snapshots = _snapshot_json(snapshot)
    snapshots["referenced_inputs"] = [
        cast(JsonValue, item.model_dump(mode="json")) for item in referenced_inputs
    ]
    intents: list[_Intent] = []
    for package, payload in selected:
        intents.extend(
            _artifact_intent(package, payload, artifact) for artifact in payload.manifest.artifacts
        )
        for contribution in payload.manifest.contributions:
            content, provenance = _contribution_content(
                request=request,
                package=package,
                payload=payload,
                contribution=contribution,
                snapshots=snapshots,
                notices=notices,
            )
            intents.append(
                _Intent(
                    standard_id=package.standard_id,
                    version=package.applied.resolved.value,
                    target=contribution.target,
                    adapter=contribution.adapter,
                    scope=contribution.scope,
                    policy=contribution.policy,
                    mode=None,
                    shared_identity=contribution.shared_identity,
                    provenance=provenance,
                    content=content,
                    declaration=contribution,
                )
            )
    return tuple(sorted(intents, key=_intent_order))


def _intent_order(intent: _Intent) -> tuple[bytes, bytes, bytes]:
    owner = intent.shared_identity or intent.standard_id
    return (
        intent.target.original.encode("utf-8"),
        owner.encode("utf-8"),
        intent.scope.encode("utf-8"),
    )


def _target_paths(
    selected: tuple[tuple[ResolvedPackage, InstalledPayload], ...],
    previous: CentralLock,
) -> tuple[SafeRelativePath, ...]:
    paths = {artifact.path.original: artifact.path for artifact in previous.artifacts}
    for _package, payload in selected:
        for artifact in payload.manifest.artifacts:
            paths[artifact.target.original] = artifact.target
        for contribution in payload.manifest.contributions:
            paths[contribution.target.original] = contribution.target
    return tuple(sorted(paths.values(), key=lambda item: item.original.encode("utf-8")))


def _finding(
    code: str,
    *,
    target: str,
    identity: str,
    standard_id: str,
    version: str,
    message: str,
) -> ControlFinding:
    return ControlFinding(
        code=code,
        severity="error",
        standard_id=standard_id,
        version=version,
        path=target,
        identity=identity,
        message=message,
        hint="resolve the declared ownership or repository content before applying",
    )


def _structural_findings(intents: tuple[_Intent, ...]) -> tuple[ControlFinding, ...]:
    findings: list[ControlFinding] = []
    shared: dict[str, _Intent] = {}
    for intent in intents:
        if intent.shared_identity is None:
            continue
        previous = shared.setdefault(intent.shared_identity, intent)
        previous_address = (
            previous.target,
            previous.adapter,
            previous.scope,
            previous.policy,
            previous.mode,
        )
        current_address = (
            intent.target,
            intent.adapter,
            intent.scope,
            intent.policy,
            intent.mode,
        )
        if previous_address == current_address:
            continue
        for target in sorted(
            {previous.target.original, intent.target.original},
            key=lambda item: item.encode("utf-8"),
        ):
            findings.append(
                _finding(
                    "CP-SHARED-CONFLICT",
                    target=target,
                    identity=intent.shared_identity,
                    standard_id=min(previous.standard_id, intent.standard_id),
                    version=min(previous.version, intent.version),
                    message="shared identity refers to incompatible semantic addresses",
                )
            )
    by_target: dict[str, list[_Intent]] = defaultdict(list)
    for intent in intents:
        by_target[intent.target.original].append(intent)
    for target, target_intents in sorted(by_target.items()):
        for index, left in enumerate(target_intents):
            for right in target_intents[index + 1 :]:
                if left.adapter is not right.adapter:
                    findings.append(
                        _finding(
                            "CP-ADAPTER-CONFLICT",
                            target=target,
                            identity=f"{left.scope}|{right.scope}",
                            standard_id=min(left.standard_id, right.standard_id),
                            version=min(left.version, right.version),
                            message="one target declares incompatible semantic adapters",
                        )
                    )
                    continue
                if left.adapter is AdapterKind.WHOLE_FILE:
                    findings.append(
                        _finding(
                            "CP-PACKAGE-OVERLAP",
                            target=target,
                            identity="$file",
                            standard_id=min(left.standard_id, right.standard_id),
                            version=min(left.version, right.version),
                            message="whole-file ownership overlaps another selected package",
                        )
                    )
                    continue
                if left.declaration is None or right.declaration is None:
                    continue
                if not contributions_overlap(left.declaration, right.declaration):
                    continue
                if left.scope == right.scope and (
                    left.shared_identity is not None
                    and left.shared_identity == right.shared_identity
                ):
                    continue
                findings.append(
                    _finding(
                        "CP-PACKAGE-OVERLAP",
                        target=target,
                        identity=f"{left.scope}|{right.scope}",
                        standard_id=min(left.standard_id, right.standard_id),
                        version=min(left.version, right.version),
                        message="selected semantic contribution scopes overlap",
                    )
                )
    return tuple(sort_findings(findings))


def _scope_declaration(
    target: SafeRelativePath,
    adapter: AdapterKind,
    scope: str,
    identity: str,
) -> ContributionDeclaration:
    return ContributionDeclaration(
        id=identity,
        target=target,
        adapter=adapter,
        scope=scope,
        policy=ArtifactPolicy.MANAGED,
        provider="render",
    )


def _historical_overlap_findings(
    previous_lock: CentralLock,
    groups: tuple[_DesiredGroup, ...],
) -> tuple[ControlFinding, ...]:
    findings: list[ControlFinding] = []
    by_target: dict[str, list[LockedUnit]] = defaultdict(list)
    for unit in previous_lock.artifacts:
        by_target[unit.path.original].append(unit)
    for target, units in sorted(by_target.items()):
        for index, left in enumerate(units):
            for right in units[index + 1 :]:
                if contributions_overlap(
                    _scope_declaration(left.path, left.adapter, left.scope, "left"),
                    _scope_declaration(right.path, right.adapter, right.scope, "right"),
                ):
                    findings.append(
                        _finding(
                            "CP-LOCK-INCONSISTENT",
                            target=target,
                            identity=f"{left.scope}|{right.scope}",
                            standard_id=min(*left.owners, *right.owners),
                            version="",
                            message="central lock contains overlapping semantic scopes",
                        )
                    )
    for group in groups:
        for previous in by_target.get(group.target.original, []):
            if previous.adapter is group.adapter and previous.scope == group.scope:
                continue
            if contributions_overlap(
                _scope_declaration(group.target, group.adapter, group.scope, "desired"),
                _scope_declaration(
                    previous.path,
                    previous.adapter,
                    previous.scope,
                    "previous",
                ),
            ):
                findings.append(
                    _finding(
                        "CP-LOCK-INCONSISTENT",
                        target=group.target.original,
                        identity=f"{group.scope}|{previous.scope}",
                        standard_id=min(group.owners[0], previous.owners[0]),
                        version=group.versions[0][1],
                        message="selected and locked semantic scopes overlap without a migration",
                    )
                )
    return tuple(sort_findings(findings))


def _normalize_desired(
    intents: tuple[_Intent, ...],
    registry: AdapterRegistry,
) -> tuple[_DesiredUnit, ...]:
    result: list[_DesiredUnit] = []
    for intent in intents:
        adapter = registry.get(intent.adapter)
        state = adapter.inspect(intent.content, (intent.scope,))
        if len(state.units) != 1:
            raise ControlPlaneError(
                f"declared desired source does not contain its semantic scope: {intent.scope}"
            )
        result.append(_DesiredUnit(intent, state.units[0]))
    return tuple(result)


def _group_desired(
    desired: tuple[_DesiredUnit, ...],
) -> tuple[tuple[_DesiredGroup, ...], tuple[ControlFinding, ...]]:
    exact: dict[tuple[str, AdapterKind, str], list[_DesiredUnit]] = defaultdict(list)
    for item in desired:
        exact[(item.intent.target.original, item.intent.adapter, item.intent.scope)].append(item)
    groups: list[_DesiredGroup] = []
    findings: list[ControlFinding] = []
    for (_target, _adapter, _scope), items in sorted(
        exact.items(),
        key=lambda item: (
            item[0][0].encode("utf-8"),
            item[0][1].value,
            item[0][2].encode("utf-8"),
        ),
    ):
        first = items[0]
        if len(items) > 1:
            shared_ids = {item.intent.shared_identity for item in items}
            digests = {item.unit.semantic_digest for item in items}
            if None in shared_ids or len(shared_ids) != 1:
                findings.append(
                    _finding(
                        "CP-PACKAGE-OVERLAP",
                        target=first.intent.target.original,
                        identity=first.intent.scope,
                        standard_id=min(item.intent.standard_id for item in items),
                        version=min(item.intent.version for item in items),
                        message="several packages claim one unit without a shared identity",
                    )
                )
                continue
            if len(digests) != 1:
                findings.append(
                    _finding(
                        "CP-SHARED-CONFLICT",
                        target=first.intent.target.original,
                        identity=cast(str, first.intent.shared_identity),
                        standard_id=min(item.intent.standard_id for item in items),
                        version=min(item.intent.version for item in items),
                        message="shared identity resolves to incompatible semantic values",
                    )
                )
                continue
        policies = {item.intent.policy for item in items}
        modes = {item.intent.mode for item in items}
        if len(policies) != 1 or len(modes) != 1:
            findings.append(
                _finding(
                    "CP-SHARED-CONFLICT",
                    target=first.intent.target.original,
                    identity=first.intent.scope,
                    standard_id=min(item.intent.standard_id for item in items),
                    version=min(item.intent.version for item in items),
                    message="shared unit declares incompatible lifecycle metadata",
                )
            )
            continue
        provenances = {item.intent.provenance for item in items}
        provenance = next(iter(provenances)) if len(provenances) == 1 else UnitProvenance.GENERATED
        groups.append(
            _DesiredGroup(
                target=first.intent.target,
                adapter=first.intent.adapter,
                scope=first.intent.scope,
                owners=tuple(sorted(item.intent.standard_id for item in items)),
                versions=tuple(
                    sorted((item.intent.standard_id, item.intent.version) for item in items)
                ),
                policy=first.intent.policy,
                mode=first.intent.mode,
                provenance=provenance,
                unit=first.unit,
            )
        )
    return tuple(groups), tuple(sort_findings(findings))


def _initial_content(kind: AdapterKind) -> bytes:
    if kind in {AdapterKind.JSON, AdapterKind.JSONC, AdapterKind.YAML}:
        return b"{}\n"
    return b""


def _current_state(
    adapter: DocumentAdapter,
    entry: SnapshotEntry,
    scopes: tuple[str, ...],
) -> tuple[bytes, dict[str, AdapterUnit]]:
    if entry.kind is EntryKind.MISSING:
        content = _initial_content(adapter.kind)
        if adapter.kind is AdapterKind.WHOLE_FILE:
            return content, {}
    elif entry.kind is EntryKind.REGULAR and entry.content is not None:
        content = entry.content
    else:
        raise ControlPlaneError("target is not a regular file or missing")
    state = adapter.inspect(content, scopes)
    return content, {unit.scope: unit for unit in state.units}


def _unit_plan(
    kind: ActionKind,
    group: _DesiredGroup,
    current: AdapterUnit | None,
) -> PlannedUnit:
    return PlannedUnit(
        kind=kind,
        target=group.target.original,
        adapter=group.adapter.value,
        scope=group.scope,
        owners=group.owners,
        versions=group.versions,
        provenance=group.provenance,
        before_digest=current.semantic_digest.value if current else None,
        after_digest=group.unit.semantic_digest.value,
    )


def _classify_desired(
    group: _DesiredGroup,
    current: AdapterUnit | None,
    previous: LockedUnit | None,
    entry: SnapshotEntry,
) -> tuple[PlannedUnit | None, ControlFinding | None]:
    if previous is None:
        if current is None:
            return _unit_plan(ActionKind.CREATE, group, current), None
        if current.semantic_digest == group.unit.semantic_digest:
            return _unit_plan(ActionKind.ADOPT, group, current), None
        return None, _finding(
            "CP-CONSUMER-CONFLICT",
            target=group.target.original,
            identity=group.scope,
            standard_id=group.owners[0],
            version=group.versions[0][1],
            message="pre-existing consumer unit differs from the selected package value",
        )
    if previous.adapter is not group.adapter or previous.scope != group.scope:
        return None, _finding(
            "CP-LOCK-INCONSISTENT",
            target=group.target.original,
            identity=group.scope,
            standard_id=group.owners[0],
            version=group.versions[0][1],
            message="locked unit identity does not match the selected declaration",
        )
    if current is None:
        if entry.kind is EntryKind.MISSING and previous.created_container:
            return _unit_plan(ActionKind.CREATE, group, current), None
        return None, _finding(
            "CP-MODIFIED-MANAGED",
            target=group.target.original,
            identity=group.scope,
            standard_id=group.owners[0],
            version=group.versions[0][1],
            message="previously managed semantic unit is missing",
        )
    if previous.mode is not None and entry.mode != previous.mode:
        return None, _finding(
            "CP-MODIFIED-MANAGED",
            target=group.target.original,
            identity=group.scope,
            standard_id=group.owners[0],
            version=group.versions[0][1],
            message="managed whole-file mode differs from the central lock",
        )
    if current.semantic_digest != previous.semantic_digest:
        return None, _finding(
            "CP-MODIFIED-MANAGED",
            target=group.target.original,
            identity=group.scope,
            standard_id=group.owners[0],
            version=group.versions[0][1],
            message="managed semantic value differs from the central lock",
        )
    if previous.policy is ArtifactPolicy.CREATE_ONLY:
        return _unit_plan(ActionKind.PRESERVE, group, current), None
    if current.semantic_digest == group.unit.semantic_digest:
        if group.mode is not None and entry.mode != group.mode:
            return _unit_plan(ActionKind.UPDATE, group, current), None
        kind = ActionKind.NOOP if previous.owners == group.owners else ActionKind.PRESERVE
        return _unit_plan(kind, group, current), None
    return _unit_plan(ActionKind.UPDATE, group, current), None


def _classify_removed(
    previous: LockedUnit,
    current: AdapterUnit | None,
    entry: SnapshotEntry,
) -> tuple[PlannedUnit | None, ControlFinding | None]:
    versions = tuple((owner, version.value) for owner, version in previous.versions.items())
    unit = PlannedUnit(
        kind=ActionKind.REMOVE,
        target=previous.path.original,
        adapter=previous.adapter.value,
        scope=previous.scope,
        owners=previous.owners,
        versions=versions,
        provenance=previous.provenance,
        before_digest=current.semantic_digest.value if current else None,
        after_digest=None,
    )
    if current is None:
        if entry.kind is EntryKind.MISSING:
            return unit, None
        return None, _finding(
            "CP-MODIFIED-MANAGED",
            target=previous.path.original,
            identity=previous.scope,
            standard_id=previous.owners[0],
            version=versions[0][1],
            message="previously managed semantic unit is missing from its container",
        )
    if current.semantic_digest != previous.semantic_digest:
        return None, _finding(
            "CP-MODIFIED-MANAGED",
            target=previous.path.original,
            identity=previous.scope,
            standard_id=previous.owners[0],
            version=versions[0][1],
            message="managed semantic value differs from the central lock",
        )
    if previous.policy is ArtifactPolicy.CREATE_ONLY or not previous.created_container:
        return replace(unit, kind=ActionKind.PRESERVE), None
    return unit, None


def _change(unit: PlannedUnit, desired: _DesiredGroup | None) -> UnitChange:
    if unit.kind in {ActionKind.CREATE, ActionKind.ADOPT, ActionKind.UPDATE}:
        if desired is None:
            raise ControlPlaneError("mutating unit action is missing desired content")
        return UnitChange(
            unit.kind,
            unit.scope,
            content=desired.unit.raw,
            value=desired.unit.value,
        )
    return UnitChange(unit.kind, unit.scope)


def _target_action(
    *,
    entry: SnapshotEntry,
    adapter: AdapterKind,
    rendered: bytes,
    units: tuple[PlannedUnit, ...],
) -> ControlAction:
    if entry.kind is EntryKind.MISSING:
        kind = ActionKind.CREATE if rendered else ActionKind.NOOP
    elif adapter is AdapterKind.WHOLE_FILE and rendered == b"" and entry.kind is EntryKind.REGULAR:
        kind = ActionKind.REMOVE
    elif entry.content == rendered:
        kinds = {unit.kind for unit in units}
        if ActionKind.UPDATE in kinds:
            kind = ActionKind.UPDATE
        elif ActionKind.ADOPT in kinds:
            kind = ActionKind.ADOPT
        elif ActionKind.PRESERVE in kinds:
            kind = ActionKind.PRESERVE
        else:
            kind = ActionKind.NOOP
    else:
        kind = ActionKind.UPDATE
    after = None if kind is ActionKind.REMOVE else _digest(rendered).value
    return ControlAction(
        kind=kind,
        target=entry.path.original,
        adapter=adapter.value,
        scope="$target",
        standard_id="project-standards",
        summary=f"{kind.value} reconciled target from {len(units)} semantic unit(s)",
        before_digest=entry.precondition_digest.value,
        after_digest=after,
        content=rendered,
    )


def _render_targets(
    *,
    snapshot: RepositorySnapshot,
    groups: tuple[_DesiredGroup, ...],
    previous_lock: CentralLock,
    registry: AdapterRegistry,
    blocked_targets: frozenset[str],
) -> tuple[
    tuple[ControlAction, ...],
    tuple[PlannedUnit, ...],
    tuple[ControlFinding, ...],
    tuple[PlannedTarget, ...],
]:
    desired_by_target: dict[str, list[_DesiredGroup]] = defaultdict(list)
    for group in groups:
        desired_by_target[group.target.original].append(group)
    previous_by_target: dict[str, list[LockedUnit]] = defaultdict(list)
    for previous in previous_lock.artifacts:
        previous_by_target[previous.path.original].append(previous)
    actions: list[ControlAction] = []
    unit_plans: list[PlannedUnit] = []
    findings: list[ControlFinding] = []
    targets: list[PlannedTarget] = []
    all_targets = sorted(set(desired_by_target) | set(previous_by_target))
    for target in all_targets:
        if target in blocked_targets:
            continue
        desired = desired_by_target[target]
        previous = previous_by_target[target]
        adapters = {item.adapter for item in desired} | {item.adapter for item in previous}
        if len(adapters) != 1:
            first_id = desired[0].owners[0] if desired else previous[0].owners[0]
            findings.append(
                _finding(
                    "CP-ADAPTER-CONFLICT",
                    target=target,
                    identity="$target",
                    standard_id=first_id,
                    version="",
                    message="desired and locked target adapters disagree",
                )
            )
            continue
        adapter_kind = next(iter(adapters))
        adapter = registry.get(adapter_kind)
        scopes = tuple(
            sorted(
                {item.scope for item in desired} | {item.scope for item in previous},
                key=lambda item: item.encode("utf-8"),
            )
        )
        entry = snapshot.entry(SafeRelativePath.parse(target))
        try:
            current_content, current_units = _current_state(adapter, entry, scopes)
        except ControlPlaneError:
            findings.append(
                _finding(
                    "CP-MALFORMED-CONTAINER",
                    target=target,
                    identity="$target",
                    standard_id=(desired[0].owners[0] if desired else previous[0].owners[0]),
                    version="",
                    message="target cannot be parsed as its declared semantic container",
                )
            )
            continue
        previous_map = {(item.adapter, item.scope): item for item in previous}
        desired_map = {(item.adapter, item.scope): item for item in desired}
        target_units: list[PlannedUnit] = []
        target_findings: list[ControlFinding] = []
        for group in desired:
            planned, finding = _classify_desired(
                group,
                current_units.get(group.scope),
                previous_map.get((group.adapter, group.scope)),
                entry,
            )
            if finding is not None:
                target_findings.append(finding)
            elif planned is not None:
                target_units.append(planned)
        for locked in previous:
            if (locked.adapter, locked.scope) in desired_map:
                continue
            planned, finding = _classify_removed(
                locked,
                current_units.get(locked.scope),
                entry,
            )
            if finding is not None:
                target_findings.append(finding)
            elif planned is not None:
                target_units.append(planned)
        if target_findings:
            findings.extend(target_findings)
            continue
        changes = tuple(
            _change(unit, desired_map.get((adapter_kind, unit.scope)))
            for unit in sorted(target_units, key=lambda item: item.scope.encode("utf-8"))
        )
        rendered = adapter.render(adapter.inspect(current_content, scopes), changes)
        action = _target_action(
            entry=entry,
            adapter=adapter_kind,
            rendered=rendered,
            units=tuple(target_units),
        )
        actions.append(action)
        unit_plans.extend(target_units)
        mode = desired[0].mode if adapter_kind is AdapterKind.WHOLE_FILE and desired else entry.mode
        targets.append(PlannedTarget(target, rendered, mode))
    ordered_units = tuple(
        sorted(
            unit_plans,
            key=lambda item: (
                item.target.encode("utf-8"),
                item.scope.encode("utf-8"),
                item.owners,
            ),
        )
    )
    return (
        tuple(sort_actions(actions)),
        ordered_units,
        tuple(sort_findings(findings)),
        tuple(sorted(targets, key=lambda item: item.target.encode("utf-8"))),
    )


def _locked_after(
    *,
    groups: tuple[_DesiredGroup, ...],
    targets: tuple[PlannedTarget, ...],
    snapshot: RepositorySnapshot,
    previous_lock: CentralLock,
    registry: AdapterRegistry,
) -> tuple[LockedUnit, ...]:
    target_map = {item.target: item for item in targets}
    grouped: dict[str, list[_DesiredGroup]] = defaultdict(list)
    for group in groups:
        grouped[group.target.original].append(group)
    previous = {item.natural_key: item for item in previous_lock.artifacts}
    locked: list[LockedUnit] = []
    for target, target_groups in grouped.items():
        planned = target_map.get(target)
        if planned is None:
            continue
        by_adapter = {group.adapter for group in target_groups}
        if len(by_adapter) != 1:
            continue
        adapter_kind = next(iter(by_adapter))
        adapter = registry.get(adapter_kind)
        scopes = tuple(group.scope for group in target_groups)
        state = adapter.inspect(planned.content, scopes)
        units = {unit.scope: unit for unit in state.units}
        entry = snapshot.entry(SafeRelativePath.parse(target))
        for group in target_groups:
            unit = units.get(group.scope)
            if unit is None:
                continue
            prior = previous.get((group.target.original, group.adapter.value, group.scope))
            locked.append(
                LockedUnit(
                    path=group.target,
                    adapter=group.adapter,
                    scope=group.scope,
                    owners=group.owners,
                    versions={owner: PackageVersion(version) for owner, version in group.versions},
                    provenance=group.provenance,
                    policy=group.policy,
                    semantic_digest=unit.semantic_digest,
                    content_digest=_digest(unit.raw),
                    mode=group.mode,
                    created_container=(
                        entry.kind is EntryKind.MISSING
                        or (prior is not None and prior.created_container)
                    ),
                )
            )
    return tuple(sorted(locked, key=lambda item: item.natural_key))


def _accepted_tracks(
    previous: Mapping[str, AcceptedTrack],
    transitions: tuple[AcceptedTrackTransition, ...],
) -> dict[str, AcceptedTrack]:
    result = dict(previous)
    for transition in transitions:
        if transition.kind is TrackTransitionKind.REMOVE:
            result.pop(transition.standard_id, None)
        elif transition.current is not None:
            result[transition.standard_id] = transition.current
    return dict(sorted(result.items()))


def _verification_requests(
    selected: tuple[tuple[ResolvedPackage, InstalledPayload], ...],
) -> tuple[VerificationRequest, ...]:
    requests: list[VerificationRequest] = []
    for package, payload in selected:
        for provider in payload.manifest.providers:
            if (
                provider.phase is ProviderPhase.VERIFY
                and provider.operation is ProviderOperation.VERIFY
                and provider.kind in {ProviderKind.PYTHON, ProviderKind.DOCUMENTATION_ONLY}
            ):
                requests.append(
                    VerificationRequest(
                        package.standard_id,
                        package.applied.resolved.value,
                        provider.id,
                    )
                )
    return tuple(
        sorted(
            requests,
            key=lambda item: (item.standard_id, item.version, item.provider_id),
        )
    )


def _referenced_inputs(
    request: PlannerRequest,
    selected: tuple[tuple[ResolvedPackage, InstalledPayload], ...],
) -> tuple[LockedInput, ...]:
    targets = tuple(
        sorted(
            {
                item.target.original: item.target
                for _package, payload in selected
                for item in (*payload.manifest.artifacts, *payload.manifest.contributions)
            }.values(),
            key=lambda item: item.original.encode("utf-8"),
        )
    )
    result: list[LockedInput] = []
    for package, payload in selected:
        result.extend(
            resolve_referenced_inputs(
                request.repo,
                standard_id=package.standard_id,
                version=package.applied.resolved,
                config=package.effective_config,
                extensions=tuple(payload.manifest.extensions),
                managed_targets=targets,
                enabled=True,
            )
        )
    return tuple(sorted(result, key=lambda item: item.natural_key))


def _next_lock(
    request: PlannerRequest,
    resolution: ResolutionResult,
    artifacts: tuple[LockedUnit, ...],
    referenced_inputs: tuple[LockedInput, ...],
) -> CentralLock:
    desired_value = cast(JsonValue, request.resolution.desired.model_dump(mode="json"))
    catalog = request.resolution.catalog.project_standards
    return CentralLock(
        project_standards=LockHeader(
            schema_version="1.0",
            catalog=catalog.catalog,
            release=catalog.release,
            catalog_digest=catalog.digest,
            config_digest=semantic_digest(desired_value),
        ),
        standards={package.standard_id: package.applied for package in resolution.packages},
        accepted_tracks=_accepted_tracks(
            request.resolution.previous_lock.accepted_tracks,
            resolution.track_transitions,
        ),
        artifacts=list(artifacts),
        referenced_inputs=list(referenced_inputs),
    )


def plan_reconciliation(request: PlannerRequest) -> ReconciliationPlan:
    """Build one deterministic, complete, and read-only reconciliation plan."""
    resolution = resolve_packages(request.resolution)
    payloads = _payload_map(request.payloads)
    selected = _selected_payloads(resolution, payloads)
    paths = _target_paths(selected, request.resolution.previous_lock)
    snapshot = RepositorySnapshot.capture(request.repo, paths)
    referenced_inputs = _referenced_inputs(request, selected)
    notices: list[ProviderNotice] = []
    intents = _desired_intents(
        request,
        selected,
        snapshot,
        referenced_inputs,
        notices,
    )
    registry = _registry()
    findings = list(_structural_findings(intents))
    try:
        desired = _normalize_desired(intents, registry)
    except ControlPlaneError as exc:
        findings.append(
            _finding(
                "CP-PAYLOAD-CONTENT",
                target="",
                identity="$payload",
                standard_id="project-standards",
                version="",
                message=str(exc),
            )
        )
        desired = ()
    groups, group_findings = _group_desired(desired)
    findings.extend(group_findings)
    findings.extend(_historical_overlap_findings(request.resolution.previous_lock, groups))
    actions, units, target_findings, targets = _render_targets(
        snapshot=snapshot,
        groups=groups,
        previous_lock=request.resolution.previous_lock,
        registry=registry,
        blocked_targets=frozenset(finding.path for finding in findings if finding.path),
    )
    findings.extend(target_findings)
    ordered_findings = tuple(sort_findings(findings))
    applicable = not any(finding.severity == "error" for finding in ordered_findings)
    if applicable:
        artifacts = _locked_after(
            groups=groups,
            targets=targets,
            snapshot=snapshot,
            previous_lock=request.resolution.previous_lock,
            registry=registry,
        )
        next_lock = _next_lock(
            request,
            resolution,
            artifacts,
            referenced_inputs,
        )
    else:
        next_lock = request.resolution.previous_lock
    return ReconciliationPlan(
        applicable=applicable,
        actions=actions,
        units=units,
        findings=ordered_findings,
        targets=targets,
        preconditions=tuple(
            TargetPrecondition(entry.path.original, entry.precondition_digest.value)
            for entry in snapshot.entries
        ),
        resolution=resolution,
        verification_requests=_verification_requests(selected),
        provider_notices=tuple(
            sorted(
                notices,
                key=lambda item: (item.standard_id, item.version, item.provider_id),
            )
        ),
        next_lock=next_lock,
    )
