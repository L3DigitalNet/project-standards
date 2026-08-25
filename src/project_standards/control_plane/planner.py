"""Plan complete repository reconciliation against one immutable virtual tree.

The planner is deliberately a pure mutation boundary: it may read declared
payload and repository inputs and invoke phase-bounded read-only providers, but
it exposes no filesystem write primitive. The executor consumes the resulting
whole-file preconditions and proposed bytes in a later phase.
"""

from __future__ import annotations

import glob
import os
import shlex
import stat
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass, field, replace
from itertools import zip_longest
from pathlib import Path, PurePosixPath
from typing import Literal, cast

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
from project_standards.control_plane.adapters.base import (
    AdapterUnit,
    DocumentAdapter,
    decode_json_pointer,
)
from project_standards.control_plane.adapters.jsonc import (
    container_value_without_comments,
    format_fresh_json_container,
)
from project_standards.control_plane.catalog_refresh import CatalogRefreshPlan
from project_standards.control_plane.codec import (
    content_digest,
    parse_catalog,
    parse_config,
    parse_lock,
    render_catalog,
    semantic_digest,
)
from project_standards.control_plane.config_edit import (
    changed_package_config_pointers,
    render_package_config_transform,
)
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
    CreateOnlyAbsence,
    LockedInput,
    LockedUnit,
    LockHeader,
    UnitProvenance,
)
from project_standards.control_plane.paths import CatalogMajor
from project_standards.control_plane.providers import (
    ProviderInvocation,
    ProviderResult,
    invoke_provider,
    resolve_referenced_inputs,
)
from project_standards.control_plane.resolution import (
    AcceptedTrackTransition,
    DeclaredTransition,
    ResolutionRequest,
    ResolutionResult,
    ResolvedPackage,
    TrackTransitionKind,
    has_declared_transition_path,
    project_source_effective_config,
    resolve_packages,
    validate_source_transform_values,
)
from project_standards.control_plane.snapshot import (
    EntryKind,
    RepositorySnapshot,
    SnapshotEntry,
    resolved_target_paths,
)
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.paths import (
    PackageVersion,
    SafeRelativePath,
    Sha256Digest,
)
from project_standards.package_contract.payload import (
    AdapterKind,
    ArtifactPolicy,
    ConditionalMaterialization,
    ContributionDeclaration,
    JsonObject,
    JsonValue,
    MigrationDeclaration,
    PackageOptionSchema,
    ProviderEffect,
    ProviderKind,
    ProviderOperation,
    ProviderPhase,
    SharedIdentity,
    WholeArtifactDeclaration,
    contributions_overlap,
    validate_configuration_transform_eligibility,
)

type ProviderRunner = Callable[[ProviderInvocation], ProviderResult]


@dataclass(frozen=True, slots=True)
class PlannerRequest:
    """Bind all explicit inputs required for one read-only plan."""

    repo: Path
    resolution: ResolutionRequest
    payloads: tuple[InstalledPayload, ...]
    provider_runner: ProviderRunner | None = None
    catalog_refresh: CatalogRefreshPlan | None = None
    retired_targets: frozenset[SafeRelativePath] = frozenset()
    retired_content: tuple[tuple[SafeRelativePath, bytes], ...] = ()
    # Set by legacy-migration planning, which stands in for "legacy authority
    # still owns this repository". Conflict hints then name the migration write
    # entry point instead of ``reconcile --apply``, which is not runnable while
    # legacy authority stands (issue #81); that use changes no classification,
    # action, or lock outcome. It additionally tells the package-configuration
    # transform gate that adopted-legacy ownership is not applied-package
    # evidence (issue #83, see _prepare_configuration_transform). No other
    # planning outcome depends on it.
    migration_catalog: CatalogMajor | None = None


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
    shared_identity: str | None
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
class ConfigurationTransformEvidence:
    """Identify one config transform using only pointers, identities, and digests."""

    standard_id: str
    migration_id: str
    source: str
    target: str
    provider_id: str
    declared_pointers: tuple[str, ...]
    changed_pointers: tuple[str, ...]
    before_digest: str
    after_digest: str


@dataclass(frozen=True, slots=True)
class _PreparedConfigurationTransform:
    """Retain semantic transform output needed for one lexical config action."""

    declaration: MigrationDeclaration
    evidence: ConfigurationTransformEvidence
    before: JsonObject = field(repr=False)
    after: JsonObject = field(repr=False)


@dataclass(frozen=True, slots=True)
class ManagedRestorePreview:
    """Describe one content-safe exact-target restore decision."""

    target: str
    owner: str
    current_state: str
    lock_digest: str
    desired_digest: str
    action: Literal["overwrite", "recreate", "noop"]
    apply_command: str

    def to_jsonable(self) -> dict[str, JsonValue]:
        """Return the bounded fields safe for text and JSON projection."""
        return {
            "target": self.target,
            "owner": self.owner,
            "current_state": self.current_state,
            "lock_digest": self.lock_digest,
            "desired_digest": self.desired_digest,
            "action": self.action,
            "apply_command": self.apply_command,
        }


@dataclass(frozen=True, slots=True)
class ManagedRestorePlan:
    """Carry a public restore preview beside executor-only bytes and preconditions."""

    applicable: bool
    preview: ManagedRestorePreview | None
    findings: tuple[ControlFinding, ...]
    target_precondition_digest: str | None = None
    desired_content: bytes | None = field(default=None, repr=False)
    desired_mode: str | None = None
    authority_preconditions: tuple[TargetPrecondition, ...] = ()

    def to_jsonable(self) -> dict[str, JsonValue]:
        """Return restore facts without exposing current or desired content bytes."""
        return {
            "applicable": self.applicable,
            "preview": self.preview.to_jsonable() if self.preview is not None else None,
            "findings": cast(JsonValue, findings_to_jsonable(self.findings)),
        }


@dataclass(frozen=True, slots=True)
class _ManagedWholeFileTarget:
    """Retain one selected package's restore authority outside public plan output."""

    target: str
    standard_id: str
    version: str
    content: bytes = field(repr=False)
    mode: str | None
    digest: str


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
    namespace_prunes: tuple[str, ...]
    catalog_refresh: CatalogRefreshPlan | None
    next_lock: CentralLock
    configuration_transforms: tuple[ConfigurationTransformEvidence, ...] = ()
    # Restore candidates remain executor-private because provider-rendered bytes
    # must never enter ordinary text or JSON reconciliation evidence.
    restore_targets: tuple[_ManagedWholeFileTarget, ...] = ()
    # Targets whose mutating action names a file an EARLIER action in this same
    # `actions` order already publishes, because a consumer symlink collapsed
    # two declared paths onto one inode. The executor publishes the first and
    # treats these as satisfied by it; every logical target still gets its own
    # action, planned target, and lock artifact. Deliberately absent from
    # `to_jsonable`: alias handling is an executor instruction derived from live
    # filesystem shape, not a public plan fact, so plan output and the plan
    # fingerprint stay byte-identical for repositories that track no such link.
    alias_followers: tuple[str, ...] = ()

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
            }
            for package in self.resolution.packages
        ]
        transitions = [_transition_json(item) for item in self.resolution.track_transitions]
        public_lock = cast(JsonValue, self.next_lock.model_dump(mode="json"))
        return {
            "schema_version": "1.3",
            "applicable": self.applicable,
            "actions": cast(JsonValue, actions_to_jsonable(self.actions)),
            "configuration_transforms": cast(
                JsonValue,
                [asdict(item) for item in self.configuration_transforms],
            ),
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
            "namespace_prunes": list(self.namespace_prunes),
            "catalog_refresh": _catalog_refresh_json(self.catalog_refresh),
            "next_lock": public_lock,
            "proposed_lock": public_lock,
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
    # Diagnostics only. Whole-file artifacts carry ownership predicates but no
    # ContributionDeclaration, so the conflict hint reads this instead of
    # ``declaration`` to name their relinquishment option (issue #82).
    ownership_options: tuple[str, ...] = ()


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
    shared_identity: SharedIdentity | None
    versions: tuple[tuple[str, str], ...]
    policy: ArtifactPolicy
    mode: str | None
    provenance: UnitProvenance
    unit: AdapterUnit
    governing_options: tuple[str, ...] | None
    ownership_options: tuple[str, ...]


type _OwnedNaturalKey = tuple[str, str, str]
type _SelectedDeclarationKey = tuple[str, str, AdapterKind, str]
type _HistoricalAddress = tuple[str, str, AdapterKind, str]


@dataclass(frozen=True, slots=True)
class _HistoricalCreateOnlyUnit:
    version: PackageVersion
    digest: Sha256Digest


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


def _catalog_refresh_json(refresh: CatalogRefreshPlan | None) -> JsonValue:
    if refresh is None:
        return None
    return {
        "changed": refresh.changed,
        "classification": refresh.classification.value,
        "before": {
            "catalog": refresh.before.catalog,
            "release": refresh.before.release,
            "digest": refresh.before.digest.value,
        },
        "after": {
            "catalog": refresh.after.catalog,
            "release": refresh.after.release,
            "digest": refresh.after.digest.value,
        },
        "affected_selections": [
            {
                "standard_id": item.standard_id,
                "previous": item.previous.value if item.previous is not None else None,
                "current": item.current.value,
            }
            for item in refresh.affected_selections
        ],
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


def _selected_declaration_governing_options(
    selected: tuple[tuple[ResolvedPackage, InstalledPayload], ...],
) -> dict[_SelectedDeclarationKey, tuple[str, ...] | None]:
    """Index unambiguous governing metadata by package-owned semantic address."""
    candidates: dict[
        _SelectedDeclarationKey,
        set[tuple[str, ...] | None],
    ] = defaultdict(set)
    for package, payload in selected:
        for contribution in payload.manifest.contributions:
            key = (
                package.standard_id,
                contribution.target.original,
                contribution.adapter,
                contribution.scope,
            )
            # Inactive declarations remain diagnostic authority for locked units
            # that the selected configuration has de-declared. Reading their
            # manifest metadata never invokes an inactive render provider.
            declared = (
                tuple(contribution.governing_options)
                if contribution.governing_options is not None
                else None
            )
            candidates[key].add(declared)
    return {
        key: next(iter(declared)) if len(declared) == 1 else None
        for key, declared in candidates.items()
    }


def _locked_governing_options(
    locked: LockedUnit,
    selected_declarations: Mapping[
        _SelectedDeclarationKey,
        tuple[str, ...] | None,
    ],
) -> tuple[str, ...] | None:
    declared = {
        selected_declarations.get((owner, locked.path.original, locked.adapter, locked.scope))
        for owner in locked.owners
    }
    return next(iter(declared)) if len(declared) == 1 else None


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
    if content_digest(content) != expected:
        raise ControlPlaneError("planned payload source changed after integrity validation")
    return content


def _ownership_options(declaration: ConditionalMaterialization) -> tuple[str, ...]:
    """Name the "managed" ownership options that gate one declaration."""
    return tuple(
        sorted(
            {
                predicate.option
                for predicate in declaration.when_any
                if predicate.equals == "managed"
                and predicate.option.rsplit("/", 1)[-1].endswith("ownership")
            }
        )
    )


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
        ownership_options=_ownership_options(artifact),
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
    intents: list[_Intent] = []
    for package, payload in selected:
        package_snapshots: JsonObject = {
            **snapshots,
            "referenced_inputs": [
                cast(JsonValue, item.model_dump(mode="json"))
                for item in referenced_inputs
                if item.standard_id == package.standard_id
            ],
        }
        intents.extend(
            _artifact_intent(package, payload, artifact)
            for artifact in payload.manifest.artifacts
            if artifact.materializes(package.effective_config)
        )
        for contribution in payload.manifest.contributions:
            if not contribution.materializes(package.effective_config):
                continue
            content, provenance = _contribution_content(
                request=request,
                package=package,
                payload=payload,
                contribution=contribution,
                snapshots=package_snapshots,
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
                    ownership_options=_ownership_options(contribution),
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
    hint: str = "resolve the declared ownership or repository content before applying",
    expected: JsonValue | None = None,
    actual: JsonValue | None = None,
    expected_digest: str | None = None,
    actual_digest: str | None = None,
    governing_options: tuple[str, ...] | None = None,
    null_values: tuple[str, ...] = (),
    line: int | None = None,
    column: int | None = None,
    locus: str | None = None,
    observed: int | None = None,
    limit: int | None = None,
    first_difference_line: int | None = None,
    first_difference_expected: str | None = None,
) -> ControlFinding:
    return ControlFinding(
        code=code,
        severity="error",
        standard_id=standard_id,
        version=version,
        path=target,
        identity=identity,
        message=message,
        hint=hint,
        line=line,
        column=column,
        locus=locus,
        observed=observed,
        limit=limit,
        expected=expected,
        actual=actual,
        expected_digest=expected_digest,
        actual_digest=actual_digest,
        governing_options=governing_options,
        null_values=null_values,
        first_difference_line=first_difference_line,
        first_difference_expected=first_difference_expected,
    )


_EXCERPT_LIMIT = 120


def _first_difference_pointer(expected: bytes, actual: bytes) -> tuple[int, str] | None:
    """Locate the first differing line between two text blobs, quoting expected only.

    5.8.0 FR-012 / SPEC-CP01 confidentiality: the returned excerpt is drawn from
    EXPECTED (package-side, public) bytes only — consumer bytes are read solely to
    align line numbers and are never surfaced. Both sides must UTF-8 decode; a
    decode failure on either (binary/undecodable target) yields None so callers
    fall back to digest-only rendering. Decoding actual is mandatory because a
    consumer-only decode would make line numbers meaningless against undecodable
    consumer content.
    """
    try:
        expected_text = expected.decode("utf-8")
        actual_text = actual.decode("utf-8")
    except UnicodeDecodeError:
        return None
    expected_lines = expected_text.splitlines()
    actual_lines = actual_text.splitlines()
    for index, (expected_line, actual_line) in enumerate(zip_longest(expected_lines, actual_lines)):
        if expected_line == actual_line:
            continue
        line = expected_line or ""
        if len(line) > _EXCERPT_LIMIT:
            line = f"{line[:_EXCERPT_LIMIT]}…"
        return index + 1, line
    return None


def _consumer_alignment_hint(group: _DesiredGroup) -> str:
    if group.governing_options == ():
        return (
            "no declared package option governs this unit; align the repository "
            "content with the package value or take consumer ownership before applying"
        )
    if group.governing_options:
        return (
            "set a governing option so the package reproduces the repository "
            "value, or align the content before applying"
        )
    return "resolve the declared ownership or repository content before applying"


def _consumer_conflict_hint(group: _DesiredGroup, migration_catalog: CatalogMajor | None) -> str:
    if len(group.owners) > 1:
        return (
            f"ownership class: shared semantic unit; deleting {group.target.original} "
            "is not authorized because the file can contain consumer-owned or "
            f"separately managed content; {_consumer_alignment_hint(group)}"
        )
    if group.adapter is AdapterKind.WHOLE_FILE:
        # While legacy authority is the only authority, `reconcile --apply` is not
        # a runnable write path; the migration preview and its apply are.
        write_command = (
            "project-standards reconcile --apply"
            if migration_catalog is None
            else f"project-standards init --catalog {migration_catalog.value} --migrate"
        )
        recovery_command = f"rm -- {shlex.quote(group.target.original)} && {write_command}"
        hint = (
            "ownership class: pre-adoption exclusive whole-file target; deleting "
            f"{group.target.original} is permitted to let the selected package create "
            f"it; from the repository root, run {recovery_command}"
        )
        if migration_catalog is not None:
            hint = f"{hint}, then apply the reviewed plan with {write_command} --apply"
        if group.ownership_options:
            selectors = ", ".join(f'{option} = "managed"' for option in group.ownership_options)
            hint = f"{hint}; current ownership option: {selectors}"
        return hint
    return (
        f"ownership class: partial semantic unit; deleting {group.target.original} "
        "is not authorized because the file can contain consumer-owned or separately "
        f"managed content; {_consumer_alignment_hint(group)}"
    )


def _published_unit_value(value: JsonValue | bytes) -> JsonValue | None:
    """Publish a unit value only when it is JSON-representable.

    5.8.0 FR-012 / SPEC-CP01 confidentiality: byte-valued units are digest-only,
    because raw consumer or package bytes must never enter public diagnostics.
    """
    return None if isinstance(value, bytes) else value


def _null_unit_values(*sides: tuple[str, JsonValue | bytes]) -> tuple[str, ...]:
    """Name the evidence sides whose unit value is a genuine JSON null.

    ``findings_to_jsonable`` drops None fields, so an explicit null would be
    indistinguishable from an omitted (byte-valued or unknown) side without
    this list. Only sides whose value is actually observed may be passed.
    """
    return tuple(name for name, value in sides if value is None)


def _consumer_conflict_finding(
    group: _DesiredGroup,
    current: AdapterUnit,
    migration_catalog: CatalogMajor | None,
) -> ControlFinding:
    expected_value = group.unit.value
    actual_value = current.value
    # 5.8.0 FR-012 / SPEC-CP01: only whole-file text conflicts carry a line
    # pointer; property-level units already publish JSON expected/actual values,
    # and a "line number" over a byte-valued property unit would be meaningless.
    pointer: tuple[int, str] | None = None
    if (
        group.adapter is AdapterKind.WHOLE_FILE
        and isinstance(expected_value, bytes)
        and isinstance(actual_value, bytes)
    ):
        pointer = _first_difference_pointer(expected_value, actual_value)
    return _finding(
        "CP-CONSUMER-CONFLICT",
        target=group.target.original,
        identity=group.scope,
        standard_id=group.owners[0],
        version=group.versions[0][1],
        message="pre-existing consumer unit differs from the selected package value",
        hint=_consumer_conflict_hint(group, migration_catalog),
        expected=_published_unit_value(expected_value),
        actual=_published_unit_value(actual_value),
        expected_digest=group.unit.semantic_digest.value,
        actual_digest=current.semantic_digest.value,
        governing_options=group.governing_options,
        null_values=_null_unit_values(("expected", expected_value), ("actual", actual_value)),
        first_difference_line=None if pointer is None else pointer[0],
        first_difference_expected=None if pointer is None else pointer[1],
    )


def _modified_managed_drift_finding(
    group: _DesiredGroup,
    current: AdapterUnit,
    previous: LockedUnit,
) -> ControlFinding:
    """Explain managed drift with the same content-safe evidence as a conflict.

    Issue #87: the bare message left the operator to reconstruct the mismatch
    from Git history and the successor's adoption guide. The lock stores digests
    only, so the locked side publishes its semantic digest as the bounded
    structural equivalent of its value; the observed side publishes its JSON
    value beside its digest. ``governing_options`` names the target payload's
    option that can express the committed intent, which is the supported
    resolution the generic hint never disclosed.
    """
    return _finding(
        "CP-MODIFIED-MANAGED",
        target=group.target.original,
        identity=group.scope,
        standard_id=group.owners[0],
        version=group.versions[0][1],
        message="managed semantic value differs from the central lock",
        actual=_published_unit_value(current.value),
        expected_digest=previous.semantic_digest.value,
        actual_digest=current.semantic_digest.value,
        governing_options=group.governing_options,
        null_values=_null_unit_values(("actual", current.value)),
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
    transitions: frozenset[DeclaredTransition],
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
            ) and not _overlap_has_declared_transition(group, previous, transitions):
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


def _overlap_has_declared_transition(
    group: _DesiredGroup,
    previous: LockedUnit,
    transitions: frozenset[DeclaredTransition],
) -> bool:
    if set(group.owners) != set(previous.owners):
        return False
    current_versions = dict(group.versions)
    for owner in group.owners:
        source = previous.versions.get(owner)
        target_value = current_versions.get(owner)
        if source is None or target_value is None:
            return False
        target = PackageVersion(target_value)
        if source == target or not has_declared_transition_path(
            transitions,
            owner,
            source,
            target,
        ):
            return False
    return True


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
        # Shared groups keep governing metadata only when every owner declares the
        # same pointers; disagreement degrades to unknown rather than misattributing.
        declared = {
            tuple(item.intent.declaration.governing_options)
            if item.intent.declaration is not None
            and item.intent.declaration.governing_options is not None
            else None
            for item in items
        }
        governing = next(iter(declared)) if len(declared) == 1 else None
        ownership_options = tuple(
            sorted({option for item in items for option in item.intent.ownership_options})
        )
        groups.append(
            _DesiredGroup(
                target=first.intent.target,
                adapter=first.intent.adapter,
                scope=first.intent.scope,
                owners=tuple(sorted(item.intent.standard_id for item in items)),
                shared_identity=first.intent.shared_identity,
                versions=tuple(
                    sorted((item.intent.standard_id, item.intent.version) for item in items)
                ),
                policy=first.intent.policy,
                mode=first.intent.mode,
                provenance=provenance,
                unit=first.unit,
                governing_options=governing,
                ownership_options=ownership_options,
            )
        )
    return tuple(groups), tuple(sort_findings(findings))


def _package_version_key(version: PackageVersion) -> tuple[int, int]:
    return (version.major, version.minor)


def _historical_create_only_units(
    selected: tuple[tuple[ResolvedPackage, InstalledPayload], ...],
    payloads: Iterable[InstalledPayload],
    registry: AdapterRegistry,
) -> dict[_HistoricalAddress, tuple[_HistoricalCreateOnlyUnit, ...]]:
    """Normalize the static create-only history for selected package addresses.

    The complete installed payload set is the oracle because advertised package
    versions are permanent and integrity verified. Provider-rendered declarations
    are excluded: their output has no immutable package-side digest to compare.
    """
    selected_by_standard = {package.standard_id: package for package, _payload in selected}
    indexed: dict[_HistoricalAddress, list[_HistoricalCreateOnlyUnit]] = defaultdict(list)
    for payload in payloads:
        identity = payload.manifest.payload
        package = selected_by_standard.get(identity.standard)
        if package is None:
            continue
        declarations: list[tuple[SafeRelativePath, AdapterKind, str, bytes]] = []
        declarations.extend(
            (
                artifact.target,
                AdapterKind.WHOLE_FILE,
                "$file",
                _read_payload_file(payload, artifact.source, artifact.digest),
            )
            for artifact in payload.manifest.artifacts
            if artifact.policy is ArtifactPolicy.CREATE_ONLY
            and artifact.materializes(package.effective_config)
        )
        declarations.extend(
            (
                contribution.target,
                contribution.adapter,
                contribution.scope,
                _read_payload_file(payload, contribution.source, contribution.source_digest),
            )
            for contribution in payload.manifest.contributions
            if contribution.policy is ArtifactPolicy.CREATE_ONLY
            and contribution.materializes(package.effective_config)
            and contribution.source is not None
            and contribution.source_digest is not None
        )
        for target, adapter_kind, scope, content in declarations:
            state = registry.get(adapter_kind).inspect(content, (scope,))
            if len(state.units) != 1:
                raise ControlPlaneError(
                    f"advertised create-only source does not contain its semantic scope: {scope}"
                )
            indexed[(identity.standard, target.original, adapter_kind, scope)].append(
                _HistoricalCreateOnlyUnit(identity.version, state.units[0].semantic_digest)
            )
    return {
        address: tuple(
            sorted(
                units,
                key=lambda item: (*_package_version_key(item.version), item.digest.value),
            )
        )
        for address, units in indexed.items()
    }


def _create_only_stale_findings(
    group: _DesiredGroup,
    current: AdapterUnit | None,
    historical: Mapping[_HistoricalAddress, tuple[_HistoricalCreateOnlyUnit, ...]],
) -> tuple[ControlFinding, ...]:
    # Selected equality outranks history: unchanged bytes shared with an older
    # payload are current content, not evidence that the consumer missed an update.
    if (
        current is None
        or group.policy is not ArtifactPolicy.CREATE_ONLY
        or group.provenance is not UnitProvenance.SOURCE
        or current.semantic_digest == group.unit.semantic_digest
    ):
        return ()
    findings: list[ControlFinding] = []
    for standard_id, selected_value in group.versions:
        selected = PackageVersion(selected_value)
        matches = [
            unit
            for unit in historical.get(
                (standard_id, group.target.original, group.adapter, group.scope),
                (),
            )
            if _package_version_key(unit.version) < _package_version_key(selected)
            and unit.digest == current.semantic_digest
        ]
        if not matches:
            continue
        nearest = max(matches, key=lambda item: _package_version_key(item.version))
        findings.append(
            ControlFinding(
                code="CP-CREATE-ONLY-STALE",
                severity="warning",
                standard_id=standard_id,
                version=selected.value,
                path=group.target.original,
                identity=group.scope,
                message=(
                    "create-only unit matches advertised version "
                    f"{nearest.version.value} instead of selected version {selected.value}"
                ),
                hint=(
                    "review the selected package adoption guide and manually copy or "
                    "merge the current create-only content when appropriate"
                ),
                expected_digest=group.unit.semantic_digest.value,
                actual_digest=current.semantic_digest.value,
            )
        )
    return tuple(findings)


def _managed_restore_targets(
    groups: tuple[_DesiredGroup, ...],
    blocked_targets: frozenset[str],
) -> tuple[_ManagedWholeFileTarget, ...]:
    """Retain only unambiguous, exclusively managed whole-file restore authorities."""
    by_target: dict[str, list[_DesiredGroup]] = defaultdict(list)
    for group in groups:
        by_target[group.target.original].append(group)
    candidates: list[_ManagedWholeFileTarget] = []
    for target, target_groups in sorted(by_target.items()):
        if target in blocked_targets or len(target_groups) != 1:
            continue
        group = target_groups[0]
        if (
            group.adapter is not AdapterKind.WHOLE_FILE
            or group.scope != "$file"
            or group.policy is not ArtifactPolicy.MANAGED
            or len(group.owners) != 1
            or group.shared_identity is not None
        ):
            continue
        candidates.append(
            _ManagedWholeFileTarget(
                target=target,
                standard_id=group.owners[0],
                version=group.versions[0][1],
                content=group.unit.raw,
                mode=group.mode,
                digest=content_digest(group.unit.raw).value,
            )
        )
    return tuple(candidates)


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
        shared_identity=group.shared_identity,
        versions=group.versions,
        provenance=group.provenance,
        before_digest=current.semantic_digest.value if current else None,
        after_digest=group.unit.semantic_digest.value,
    )


def _group_natural_key(group: _DesiredGroup) -> _OwnedNaturalKey:
    return (group.target.original, group.adapter.value, group.scope)


def _matches_affected_legacy_state(
    group: _DesiredGroup,
    resolution: ResolutionResult,
    previous_lock: CentralLock,
) -> bool:
    """Limit damaged-lock inference to unchanged selections written by 5.0.x."""
    release = previous_lock.project_standards.release.split(".")
    if release[:2] != ["5", "0"]:
        return False
    current = {package.standard_id: package.applied for package in resolution.packages}
    for owner, version in group.versions:
        prior = previous_lock.standards.get(owner)
        applied = current.get(owner)
        if (
            prior is None
            or applied is None
            or prior.resolved.value != version
            or prior.effective_config_digest != applied.effective_config_digest
        ):
            return False
    return True


def _retained_create_only_absence_keys(
    groups: tuple[_DesiredGroup, ...],
    resolution: ResolutionResult,
    previous_lock: CentralLock,
) -> frozenset[_OwnedNaturalKey]:
    artifacts = {artifact.natural_key: artifact for artifact in previous_lock.artifacts}
    absences = {absence.natural_key for absence in previous_lock.create_only_absences}
    retained: set[_OwnedNaturalKey] = set()
    for group in groups:
        if group.policy is not ArtifactPolicy.CREATE_ONLY:
            continue
        key = _group_natural_key(group)
        prior = artifacts.get(key)
        if key in absences or (prior is not None and prior.policy is ArtifactPolicy.CREATE_ONLY):
            retained.add(key)
            continue
        if prior is None and _matches_affected_legacy_state(group, resolution, previous_lock):
            retained.add(key)
    return frozenset(retained)


def _classify_desired(
    group: _DesiredGroup,
    current: AdapterUnit | None,
    previous: LockedUnit | None,
    entry: SnapshotEntry,
    *,
    preserve_absence: bool,
    migration_catalog: CatalogMajor | None,
) -> tuple[PlannedUnit | None, ControlFinding | None]:
    if previous is None:
        if current is None:
            if preserve_absence:
                return _unit_plan(ActionKind.PRESERVE, group, current), None
            return _unit_plan(ActionKind.CREATE, group, current), None
        if current.semantic_digest == group.unit.semantic_digest:
            return _unit_plan(ActionKind.ADOPT, group, current), None
        if group.policy is ArtifactPolicy.CREATE_ONLY and entry.kind is EntryKind.REGULAR:
            return _unit_plan(ActionKind.PRESERVE, group, current), None
        return None, _consumer_conflict_finding(group, current, migration_catalog)
    if previous.adapter is not group.adapter or previous.scope != group.scope:
        return None, _finding(
            "CP-LOCK-INCONSISTENT",
            target=group.target.original,
            identity=group.scope,
            standard_id=group.owners[0],
            version=group.versions[0][1],
            message="locked unit identity does not match the selected declaration",
        )
    if previous.policy is ArtifactPolicy.CREATE_ONLY:
        # The desired payload policy governs classification; the locked policy
        # is history. On a create-only→managed flip whose unit is absent, the
        # managed declaration must be recreated in the same cycle (issue #76):
        # keeping PRESERVE here while absence detection keys on the current
        # policy left the unit neither live nor disclaimed, so the lock dropped
        # it and convergence took a second apply. A present unit still plans
        # PRESERVE, adopting the consumer's bytes as the managed baseline.
        if group.policy is not ArtifactPolicy.CREATE_ONLY and current is None:
            return _unit_plan(ActionKind.CREATE, group, current), None
        return _unit_plan(ActionKind.PRESERVE, group, current), None
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
            governing_options=group.governing_options,
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
    # Equivalence outranks lock drift (issue #87). When the repository already
    # holds exactly what the selected package renders, the older locked digest
    # is history, not a conflict to adjudicate: applying would rewrite the same
    # bytes, and blocking here forced consumers to destroy live content by
    # restoring the stale value just so the successor could plan it back from a
    # newly supported option. Drift that the target does NOT reproduce still
    # fails closed below.
    if current.semantic_digest == group.unit.semantic_digest:
        if group.mode is not None and entry.mode != group.mode:
            return _unit_plan(ActionKind.UPDATE, group, current), None
        kind = ActionKind.NOOP if previous.owners == group.owners else ActionKind.PRESERVE
        return _unit_plan(kind, group, current), None
    if current.semantic_digest != previous.semantic_digest:
        return None, _modified_managed_drift_finding(group, current, previous)
    return _unit_plan(ActionKind.UPDATE, group, current), None


def _classify_removed(
    previous: LockedUnit,
    current: AdapterUnit | None,
    entry: SnapshotEntry,
    governing_options: tuple[str, ...] | None,
) -> tuple[PlannedUnit | None, ControlFinding | None]:
    versions = tuple((owner, version.value) for owner, version in previous.versions.items())
    unit = PlannedUnit(
        kind=ActionKind.REMOVE,
        target=previous.path.original,
        adapter=previous.adapter.value,
        scope=previous.scope,
        owners=previous.owners,
        shared_identity=previous.shared_identity,
        versions=versions,
        provenance=previous.provenance,
        before_digest=current.semantic_digest.value if current else None,
        after_digest=None,
    )
    if previous.policy is ArtifactPolicy.CREATE_ONLY:
        return replace(unit, kind=ActionKind.PRESERVE), None
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
            governing_options=governing_options,
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
    if previous.adapter is AdapterKind.WHOLE_FILE and not previous.created_container:
        return replace(unit, kind=ActionKind.PRESERVE), None
    return unit, None


def _change(
    unit: PlannedUnit,
    desired: _DesiredGroup | None,
    *,
    prune_empty_ancestors: bool,
) -> UnitChange:
    if unit.kind in {ActionKind.CREATE, ActionKind.ADOPT, ActionKind.UPDATE}:
        if desired is None:
            raise ControlPlaneError("mutating unit action is missing desired content")
        return UnitChange(
            unit.kind,
            unit.scope,
            content=desired.unit.raw,
            value=desired.unit.value,
        )
    return UnitChange(
        unit.kind,
        unit.scope,
        prune_empty_ancestors=prune_empty_ancestors,
    )


def _target_action(
    *,
    entry: SnapshotEntry,
    adapter: AdapterKind,
    rendered: bytes,
    units: tuple[PlannedUnit, ...],
    mode: str | None,
    remove_container: bool = False,
) -> ControlAction:
    if entry.kind is EntryKind.MISSING:
        # Empty rendered bytes are not evidence of "nothing to do": a managed
        # artifact may legitimately declare zero-byte content (`py.typed`,
        # `.gitkeep` — issue #77). Creation over a missing path is decided by
        # whether any unit plans CREATE; a disclaimed create-only absence plans
        # PRESERVE and correctly stays NOOP.
        kind = (
            ActionKind.CREATE
            if rendered or any(unit.kind is ActionKind.CREATE for unit in units)
            else ActionKind.NOOP
        )
    elif remove_container or (
        adapter is AdapterKind.WHOLE_FILE
        and rendered == b""
        and entry.kind is EntryKind.REGULAR
        # The whole-file adapter renders b"" for a genuine REMOVE and, equally, for
        # a non-mutating PRESERVE/NOOP over a file that is already empty — a
        # create-only artifact whose consumer bytes were truncated to zero. Empty
        # output alone is therefore not evidence of removal; only the unit action
        # is (issue #66 deleted preserved consumer files without it).
        and any(unit.kind is ActionKind.REMOVE for unit in units)
    ):
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
    after = (
        None
        if kind is ActionKind.REMOVE
        or (kind is ActionKind.NOOP and entry.kind is EntryKind.MISSING)
        else content_digest(rendered).value
    )
    summaries = {
        ActionKind.CREATE: "create composed target",
        ActionKind.ADOPT: "adopt matching managed units",
        ActionKind.UPDATE: "update managed units in target",
        ActionKind.PRESERVE: "preserve consumer bytes outside managed changes",
        ActionKind.REMOVE: "remove managed target",
        ActionKind.NOOP: "target already matches managed units",
    }
    return ControlAction(
        kind=kind,
        target=entry.path.original,
        adapter=adapter.value,
        scope="$target",
        standard_id="project-standards",
        summary=f"{summaries[kind]} ({len(units)} semantic unit(s))",
        before_digest=(entry.content_digest.value if entry.content_digest is not None else None),
        after_digest=after,
        before_mode=(entry.mode if entry.kind is EntryKind.REGULAR else None),
        after_mode=(
            None
            if kind is ActionKind.REMOVE
            or (kind is ActionKind.NOOP and entry.kind is EntryKind.MISSING)
            else mode
        ),
        content=rendered,
    )


def _nested_empty(path: tuple[str, ...], leaf: JsonValue) -> JsonObject:
    nested: JsonValue = leaf
    for component in reversed(path):
        nested = {component: nested}
    return cast(JsonObject, nested)


def _merge_empty_scaffold(target: JsonObject, addition: JsonObject) -> None:
    for key, value in addition.items():
        current = target.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            _merge_empty_scaffold(current, value)
        elif current is None:
            target[key] = value
        elif current != value:
            raise ControlPlaneError("removed JSON scopes imply incompatible empty scaffolds")


def _json_empty_scaffold(scopes: tuple[str, ...]) -> JsonObject:
    result: JsonObject = {}
    for scope in scopes:
        prefix, body = scope.split(":", 1)
        pointer = body.split("#", 1)[0]
        path = decode_json_pointer(pointer)
        if prefix == "key":
            scaffold = _nested_empty(path[:-1], {})
        elif prefix in {"set", "keyed-set"}:
            scaffold = _nested_empty(path, [])
        else:
            raise ControlPlaneError("JSON removal scope cannot define an empty scaffold")
        _merge_empty_scaffold(result, scaffold)
    return result


def _container_is_package_empty(
    adapter: AdapterKind,
    rendered: bytes,
    scopes: tuple[str, ...],
) -> bool:
    """Return whether removing the file cannot discard a consumer-owned unit."""
    if not rendered.strip():
        return True
    if adapter in {AdapterKind.JSON, AdapterKind.JSONC}:
        value = container_value_without_comments(rendered, adapter)
        return value == {} or value == _json_empty_scaffold(scopes)
    return False


def _is_newly_absent_create_only(
    group: _DesiredGroup,
    planned: PlannedUnit,
    current: AdapterUnit | None,
    prior_absences: frozenset[_OwnedNaturalKey],
) -> bool:
    """Detect a create-only unit the consumer deleted since the previous lock.

    A deleted unit is invisible to the action list: it plans PRESERVE, renders
    nothing, and leaves `create_only_absences` as the sole evidence (issue #70).
    Absence is `current is None` — the unit is gone from its container, or the
    whole-file target does not exist. It is deliberately NOT "renders empty":
    an existing zero-byte create-only file still carries a `$file` unit and must
    stay silent, which is the #66 truncation neighbor. Keys already recorded as
    absent are steady state, not drift, so they report nothing.
    """
    return (
        group.policy is ArtifactPolicy.CREATE_ONLY
        and planned.kind is ActionKind.PRESERVE
        and current is None
        and _group_natural_key(group) not in prior_absences
    )


def _create_only_absence_finding(group: _DesiredGroup) -> ControlFinding:
    """Explain create-only lock drift that no planned action can account for."""
    return ControlFinding(
        code="CP-CREATE-ONLY-ABSENT",
        severity="warning",
        standard_id=group.owners[0],
        version=group.versions[0][1],
        path=group.target.original,
        identity=group.scope,
        message=(
            "create-only unit is absent from the repository; reconciliation records "
            "the removal in the lock and never recreates it"
        ),
        hint=(
            "run reconcile --apply to record the absence, or restore the unit to "
            "return it to the lock's live artifacts"
        ),
    )


def _render_targets(
    *,
    snapshot: RepositorySnapshot,
    groups: tuple[_DesiredGroup, ...],
    previous_lock: CentralLock,
    registry: AdapterRegistry,
    blocked_targets: frozenset[str],
    retained_absence_keys: frozenset[_OwnedNaturalKey],
    transitions: frozenset[DeclaredTransition],
    migration_catalog: CatalogMajor | None,
    historical_create_only: Mapping[_HistoricalAddress, tuple[_HistoricalCreateOnlyUnit, ...]],
    selected_declarations: Mapping[
        _SelectedDeclarationKey,
        tuple[str, ...] | None,
    ],
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
    prior_absences = frozenset(
        absence.natural_key for absence in previous_lock.create_only_absences
    )
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
        except ControlPlaneError as exc:
            findings.append(
                _finding(
                    "CP-MALFORMED-CONTAINER",
                    target=target,
                    identity="$target",
                    standard_id=(desired[0].owners[0] if desired else previous[0].owners[0]),
                    version="",
                    message="target cannot be parsed as its declared semantic container",
                    line=exc.line,
                    column=exc.column,
                    locus="TOML syntax" if adapter_kind is AdapterKind.TOML else "syntax",
                )
            )
            continue
        previous_map = {(item.adapter, item.scope): item for item in previous}
        desired_map = {(item.adapter, item.scope): item for item in desired}
        target_units: list[PlannedUnit] = []
        target_findings: list[ControlFinding] = []
        newly_absent: list[_DesiredGroup] = []
        for group in desired:
            current_unit = current_units.get(group.scope)
            planned, finding = _classify_desired(
                group,
                current_unit,
                previous_map.get((group.adapter, group.scope)),
                entry,
                preserve_absence=_group_natural_key(group) in retained_absence_keys,
                migration_catalog=migration_catalog,
            )
            if finding is not None:
                target_findings.append(finding)
            elif planned is not None:
                target_units.append(planned)
                if _is_newly_absent_create_only(
                    group,
                    planned,
                    current_unit,
                    prior_absences,
                ):
                    newly_absent.append(group)
        for locked in previous:
            if (locked.adapter, locked.scope) in desired_map:
                continue
            if any(
                contributions_overlap(
                    _scope_declaration(group.target, group.adapter, group.scope, "desired"),
                    _scope_declaration(locked.path, locked.adapter, locked.scope, "previous"),
                )
                and _overlap_has_declared_transition(group, locked, transitions)
                for group in desired
            ):
                continue
            planned, finding = _classify_removed(
                locked,
                current_units.get(locked.scope),
                entry,
                _locked_governing_options(locked, selected_declarations),
            )
            if finding is not None:
                target_findings.append(finding)
            elif planned is not None:
                target_units.append(planned)
        if target_findings:
            findings.extend(target_findings)
            continue
        for group in desired:
            findings.extend(
                _create_only_stale_findings(
                    group,
                    current_units.get(group.scope),
                    historical_create_only,
                )
            )
        findings.extend(_create_only_absence_finding(group) for group in newly_absent)
        platform_created_container = bool(previous) and all(
            item.created_container for item in previous
        )
        changes = tuple(
            _change(
                unit,
                desired_map.get((adapter_kind, unit.scope)),
                prune_empty_ancestors=platform_created_container,
            )
            for unit in sorted(target_units, key=lambda item: item.scope.encode("utf-8"))
        )
        rendered = adapter.render(adapter.inspect(current_content, scopes), changes)
        if entry.kind is EntryKind.MISSING and adapter_kind in {
            AdapterKind.JSON,
            AdapterKind.JSONC,
        }:
            rendered = format_fresh_json_container(rendered, adapter_kind)
        # `created_container` alone is insufficient: consumers may have added
        # unrelated units after adoption. Prune only the exact empty scaffold
        # left by removing every managed unit, and preserve any comment or value.
        remove_container = (
            not desired
            and bool(previous)
            and all(
                item.created_container and item.policy is ArtifactPolicy.MANAGED
                for item in previous
            )
            and _container_is_package_empty(adapter_kind, rendered, scopes)
        )
        if remove_container:
            rendered = b""
        mode = entry.mode
        if adapter_kind is AdapterKind.WHOLE_FILE and desired and desired[0].mode is not None:
            mode = desired[0].mode
        action = _target_action(
            entry=entry,
            adapter=adapter_kind,
            rendered=rendered,
            units=tuple(target_units),
            mode=mode,
            remove_container=remove_container,
        )
        actions.append(action)
        unit_plans.extend(target_units)
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
    retained_absence_keys: frozenset[_OwnedNaturalKey],
) -> tuple[tuple[LockedUnit, ...], tuple[CreateOnlyAbsence, ...]]:
    target_map = {item.target: item for item in targets}
    grouped: dict[str, list[_DesiredGroup]] = defaultdict(list)
    for group in groups:
        grouped[group.target.original].append(group)
    previous = {item.natural_key: item for item in previous_lock.artifacts}
    locked: list[LockedUnit] = []
    absences: list[CreateOnlyAbsence] = []
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
            key = _group_natural_key(group)
            if key in retained_absence_keys and (entry.kind is EntryKind.MISSING or unit is None):
                absences.append(
                    CreateOnlyAbsence(
                        path=group.target,
                        adapter=group.adapter,
                        scope=group.scope,
                        owners=group.owners,
                        shared_identity=group.shared_identity,
                        versions={
                            owner: PackageVersion(version) for owner, version in group.versions
                        },
                        provenance=group.provenance,
                    )
                )
                continue
            if unit is None:
                continue
            prior = previous.get(key)
            if group.policy is ArtifactPolicy.CREATE_ONLY and prior is not None:
                locked.append(
                    prior.model_copy(
                        update={
                            "owners": group.owners,
                            "shared_identity": group.shared_identity,
                            "versions": {
                                owner: PackageVersion(version) for owner, version in group.versions
                            },
                            "provenance": group.provenance,
                            "policy": group.policy,
                        }
                    )
                )
                continue
            locked.append(
                LockedUnit(
                    path=group.target,
                    adapter=group.adapter,
                    scope=group.scope,
                    owners=group.owners,
                    shared_identity=group.shared_identity,
                    versions={owner: PackageVersion(version) for owner, version in group.versions},
                    provenance=group.provenance,
                    policy=group.policy,
                    semantic_digest=unit.semantic_digest,
                    content_digest=content_digest(unit.raw),
                    mode=group.mode,
                    created_container=(
                        entry.kind is EntryKind.MISSING
                        or (prior is not None and prior.created_container)
                    ),
                )
            )
    return (
        tuple(sorted(locked, key=lambda item: item.natural_key)),
        tuple(sorted(absences, key=lambda item: item.natural_key)),
    )


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
                and provider.kind
                in {
                    ProviderKind.PYTHON,
                    ProviderKind.COMMAND,
                    ProviderKind.DOCUMENTATION_ONLY,
                }
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


def _package_namespace(path: str) -> str | None:
    prefix = ".standards/packages/"
    if not path.startswith(prefix):
        return None
    remainder = path.removeprefix(prefix)
    standard_id, separator, _relative = remainder.partition("/")
    return standard_id if standard_id and separator else None


def _namespace_findings(
    repo: Path,
    selected: tuple[tuple[ResolvedPackage, InstalledPayload], ...],
    previous_lock: CentralLock,
) -> tuple[ControlFinding, ...]:
    declared: set[str] = {
        unit.path.original
        for unit in (*previous_lock.artifacts, *previous_lock.create_only_absences)
        if _package_namespace(unit.path.original) is not None
    }
    for _package, payload in selected:
        declared.update(
            artifact.target.original
            for artifact in payload.manifest.artifacts
            if _package_namespace(artifact.target.original) is not None
        )
        declared.update(
            contribution.target.original
            for contribution in payload.manifest.contributions
            if _package_namespace(contribution.target.original) is not None
        )
    root = repo / ".standards/packages"
    if not root.exists() and not root.is_symlink():
        return ()
    findings: list[ControlFinding] = []
    try:
        if root.is_symlink() or not root.is_dir():
            return (
                _finding(
                    "CP-UNDECLARED-PACKAGE-CONTENT",
                    target=".standards/packages",
                    identity="$namespace",
                    standard_id="project-standards",
                    version="",
                    message="package namespace root is not a regular directory",
                ),
            )
        entries = sorted(
            root.rglob("*"),
            key=lambda item: item.relative_to(repo).as_posix().encode("utf-8"),
        )
        for entry in entries:
            relative = entry.relative_to(repo).as_posix()
            if entry.is_dir() and not entry.is_symlink():
                continue
            if relative in declared and entry.is_file() and not entry.is_symlink():
                continue
            standard_id = _package_namespace(relative) or "project-standards"
            code = (
                "CP-DUPLICATE-PACKAGE-LOCK"
                if entry.name in {"lock.json", "lock.toml", "provenance.lock"}
                else "CP-UNDECLARED-PACKAGE-CONTENT"
            )
            identity = "$namespace"
            if entry.is_file() and not entry.is_symlink():
                identity = f"$namespace:{_safe_undeclared_digest(entry).value}"
            findings.append(
                _finding(
                    code,
                    target=relative,
                    identity=identity,
                    standard_id=standard_id,
                    version="",
                    message="package namespace contains an undeclared durable entry",
                )
            )
    except OSError as exc:
        raise ControlPlaneError("package namespaces could not be inspected safely") from exc
    return tuple(sort_findings(findings))


def _safe_undeclared_digest(path: Path) -> Sha256Digest:
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ControlPlaneError("undeclared package entry could not be opened safely") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ControlPlaneError("undeclared package entry changed type during inspection")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        after = os.fstat(descriptor)
    except OSError as exc:
        raise ControlPlaneError("undeclared package entry could not be read safely") from exc
    finally:
        os.close(descriptor)
    stable = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_mode")
    if any(getattr(before, field) != getattr(after, field) for field in stable):
        raise ControlPlaneError("undeclared package entry changed during inspection")
    return content_digest(b"".join(chunks))


def _namespace_prunes(
    repo: Path,
    selected: tuple[tuple[ResolvedPackage, InstalledPayload], ...],
    units: tuple[PlannedUnit, ...],
    findings: tuple[ControlFinding, ...],
) -> tuple[str, ...]:
    enabled = {package.standard_id for package, _payload in selected}
    blocked = {finding.path for finding in findings}
    candidates: list[str] = []
    root = repo / ".standards/packages"
    if not root.is_dir() or root.is_symlink():
        return ()
    for namespace in sorted(root.iterdir(), key=lambda item: item.name.encode("utf-8")):
        if namespace.name in enabled or namespace.is_symlink() or not namespace.is_dir():
            continue
        prefix = f".standards/packages/{namespace.name}/"
        namespace_units = [unit for unit in units if unit.target.startswith(prefix)]
        if not namespace_units or any(path.startswith(prefix) for path in blocked):
            continue
        if all(unit.kind is ActionKind.REMOVE for unit in namespace_units):
            candidates.append(prefix.removesuffix("/"))
    return tuple(candidates)


def _next_lock(
    request: PlannerRequest,
    resolution: ResolutionResult,
    artifacts: tuple[LockedUnit, ...],
    create_only_absences: tuple[CreateOnlyAbsence, ...],
    referenced_inputs: tuple[LockedInput, ...],
) -> CentralLock:
    desired_value = cast(JsonValue, request.resolution.desired.model_dump(mode="json"))
    catalog = request.resolution.catalog.project_standards
    return CentralLock(
        project_standards=LockHeader(
            schema_version="1.1",
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
        create_only_absences=list(create_only_absences),
        referenced_inputs=list(referenced_inputs),
    )


def _resolution_schema_map(
    request: ResolutionRequest,
) -> dict[tuple[str, str], PackageOptionSchema]:
    return {
        (payload.standard_id, payload.version.value): payload.option_schema
        for payload in request.payloads
    }


def _transform_invocation(
    *,
    request: PlannerRequest,
    payload: InstalledPayload,
    declaration: MigrationDeclaration,
    effective_config: JsonObject,
    raw_config: JsonObject,
    selector: str,
) -> ProviderResult:
    provider_id = declaration.provider
    source = declaration.from_endpoint.package_version
    target = declaration.to_endpoint.package_version
    pointers = declaration.configuration_transform
    if provider_id is None or source is None or target is None or pointers is None:
        raise ControlPlaneError("configuration transform declaration is incomplete")
    runner = request.provider_runner or invoke_provider
    return runner(
        ProviderInvocation(
            repo=request.repo,
            payload=payload,
            standard_id=payload.manifest.payload.standard,
            version=target,
            provider_id=provider_id,
            operation=ProviderOperation.MIGRATE,
            effective_config=effective_config,
            snapshots={
                "configuration_transform": {
                    "migration_id": declaration.id,
                    "source": declaration.from_endpoint.value,
                    "target": declaration.to_endpoint.value,
                    "provider_id": provider_id,
                    "selector": selector,
                    "raw_config": raw_config,
                    "declared_pointers": list(pointers),
                }
            },
        )
    )


def _configuration_transform_output(
    result: ProviderResult,
    *,
    standard_id: str,
    target: PackageVersion,
    selector: object,
) -> tuple[JsonObject, tuple[str, ...]]:
    report = result.migration_report
    if result.effect is not ProviderEffect.MIGRATION_REPORT or report is None:
        raise ControlPlaneError("configuration transform provider returned the wrong effect")
    if report.claims or report.findings:
        raise ControlPlaneError("configuration transform provider returned legacy evidence")
    if (
        report.package.standard_id != standard_id
        or report.package.version != target
        or report.package.selector != selector
    ):
        raise ControlPlaneError("configuration transform provider output identity is inconsistent")
    return report.package.config, report.package.recognized_settings


def _config_pointer_is_present(config: JsonObject, pointer: str) -> bool:
    current: JsonValue = config
    for token in pointer.split("/")[1:]:
        decoded = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or decoded not in current:
            return False
        current = current[decoded]
    return True


def _prepare_configuration_transform(
    request: PlannerRequest,
    resolution: ResolutionResult,
    payloads: Mapping[tuple[str, str], InstalledPayload],
) -> tuple[PlannerRequest, ResolutionResult, _PreparedConfigurationTransform | None]:
    candidates: list[
        tuple[ResolvedPackage, InstalledPayload, InstalledPayload, MigrationDeclaration]
    ] = []
    for package in resolution.packages:
        previous = request.resolution.previous_lock.standards.get(package.standard_id)
        target_payload = payloads[(package.standard_id, package.applied.resolved.value)]
        transform_declarations = tuple(
            migration
            for migration in target_payload.manifest.migrations
            if migration.configuration_transform is not None
        )
        if previous is None:
            lock = request.resolution.previous_lock
            has_inferred_evidence = any(
                package.standard_id in record.owners
                for record in (*lock.artifacts, *lock.create_only_absences)
            ) or any(item.standard_id == package.standard_id for item in lock.referenced_inputs)
            # SPEC-VAIC FR-021: inferred-only *package* evidence — a unified lock
            # that owns units for this package but records no exact applied
            # version — fails closed for the recovery authority to resolve.
            # Legacy-migration planning is not that state: its previous lock is
            # synthesized from adopted legacy units, so ownership here proves
            # legacy authority, never a V5 applied version, and there is no
            # recovery authority to route to. The package is freshly selected
            # under EC-011, no package-to-package edge applies, and the legacy
            # provider alone owns the migrated config (issue #83).
            if (
                transform_declarations
                and has_inferred_evidence
                and request.migration_catalog is None
            ):
                raise ControlPlaneError(
                    "configuration transform requires exact authoritative applied package evidence"
                )
            continue
        if previous.resolved == package.applied.resolved:
            continue
        matches = [
            migration
            for migration in transform_declarations
            if migration.from_endpoint.package_version == previous.resolved
            and migration.to_endpoint.package_version == package.applied.resolved
        ]
        if not matches:
            continue
        source_payload = payloads.get((package.standard_id, previous.resolved.value))
        if (
            source_payload is None
            or source_payload.integrity.aggregate_digest != previous.payload_digest
        ):
            raise ControlPlaneError(
                "configuration transform requires exact authoritative applied package evidence"
            )
        candidates.extend(
            (package, source_payload, target_payload, migration) for migration in matches
        )
    if not candidates:
        return request, resolution, None
    if len(candidates) != 1:
        raise ControlPlaneError("reconciliation contains more than one applicable config transform")

    package, source_payload, target_payload, declaration = candidates[0]
    standard_id = package.standard_id
    desired_package = request.resolution.desired.standards[standard_id]
    raw_config = desired_package.config
    schemas = _resolution_schema_map(request.resolution)
    source_schema = schemas.get((standard_id, source_payload.manifest.payload.version.value))
    target_schema = schemas.get((standard_id, target_payload.manifest.payload.version.value))

    if not isinstance(source_schema, PackageOptionSchema) or not isinstance(
        target_schema, PackageOptionSchema
    ):
        raise ControlPlaneError("configuration transform schemas are unavailable")
    pointers = tuple(declaration.configuration_transform or ())
    validate_configuration_transform_eligibility(source_schema, target_schema, pointers)
    try:
        source_effective = project_source_effective_config(
            raw_config,
            source_schema,
            target_schema,
        )
    except PackageContractError as exc:
        raise ControlPlaneError(
            "package config cannot be projected to the applied source; "
            "reconcile the package upgrade first, then adopt the successor-only value"
        ) from exc
    selector = (
        desired_package.version.value
        if isinstance(desired_package.version, PackageVersion)
        else desired_package.version
    )
    first = _transform_invocation(
        request=request,
        payload=target_payload,
        declaration=declaration,
        effective_config=source_effective,
        raw_config=raw_config,
        selector=selector,
    )
    transformed, recognized = _configuration_transform_output(
        first,
        standard_id=standard_id,
        target=package.applied.resolved,
        selector=desired_package.version,
    )
    changed = changed_package_config_pointers(raw_config, transformed)
    explicit_pointers = {
        pointer for pointer in pointers if _config_pointer_is_present(raw_config, pointer)
    }
    if explicit_pointers.intersection(changed):
        raise ControlPlaneError("configuration transform changed an explicit consumer option")
    if not set(changed).issubset(pointers) or tuple(recognized) != changed:
        raise ControlPlaneError(
            "configuration transform provider changed options outside its declaration"
        )
    target_schema.resolve_options(transformed)
    validate_source_transform_values(transformed, changed, source_schema)
    try:
        candidate_source_effective = project_source_effective_config(
            transformed,
            source_schema,
            target_schema,
        )
    except PackageContractError as exc:
        raise ControlPlaneError(
            "package config cannot be projected to the applied source; "
            "reconcile the package upgrade first, then adopt the successor-only value"
        ) from exc
    second = _transform_invocation(
        request=request,
        payload=target_payload,
        declaration=declaration,
        effective_config=candidate_source_effective,
        raw_config=transformed,
        selector=selector,
    )
    repeated, repeated_recognized = _configuration_transform_output(
        second,
        standard_id=standard_id,
        target=package.applied.resolved,
        selector=desired_package.version,
    )
    repeated_json = cast(JsonValue, repeated)
    transformed_json = cast(JsonValue, transformed)
    if semantic_digest(repeated_json) != semantic_digest(transformed_json) or repeated_recognized:
        raise ControlPlaneError("configuration transform provider is not idempotent")

    transformed_package = desired_package.model_copy(update={"config": transformed})
    transformed_desired = request.resolution.desired.model_copy(
        update={
            "standards": {
                **request.resolution.desired.standards,
                standard_id: transformed_package,
            }
        }
    )
    transformed_resolution_request = replace(request.resolution, desired=transformed_desired)
    transformed_request = replace(request, resolution=transformed_resolution_request)
    transformed_resolution = resolve_packages(transformed_resolution_request)
    evidence = ConfigurationTransformEvidence(
        standard_id=standard_id,
        migration_id=declaration.id,
        source=source_payload.manifest.payload.version.value,
        target=target_payload.manifest.payload.version.value,
        provider_id=declaration.provider or "",
        declared_pointers=pointers,
        changed_pointers=changed,
        before_digest=semantic_digest(cast(JsonValue, raw_config)).value,
        after_digest=semantic_digest(cast(JsonValue, transformed)).value,
    )
    return (
        transformed_request,
        transformed_resolution,
        _PreparedConfigurationTransform(
            declaration,
            evidence,
            raw_config,
            transformed,
        ),
    )


def _catalog_refresh_target(
    refresh: CatalogRefreshPlan,
    snapshot: RepositorySnapshot,
) -> tuple[ControlAction | None, PlannedTarget | None, ControlFinding | None]:
    path = SafeRelativePath.parse(".standards/catalog.toml")
    entry = snapshot.entry(path)
    committed = render_catalog(refresh.committed)
    installed = render_catalog(refresh.installed)
    if entry.kind is not EntryKind.REGULAR or entry.content != committed:
        return (
            None,
            None,
            _finding(
                "CP-CATALOG-PRECONDITION",
                target=path.original,
                identity="$catalog",
                standard_id="project-standards",
                version="",
                message="committed catalog changed before refresh planning",
            ),
        )
    return (
        ControlAction(
            kind=ActionKind.UPDATE,
            target=path.original,
            adapter=AdapterKind.WHOLE_FILE.value,
            scope="$catalog",
            standard_id="project-standards",
            summary=(
                f"refresh catalog {refresh.before.catalog} from "
                f"{refresh.before.release} to {refresh.after.release}"
            ),
            before_digest=entry.precondition_digest.value,
            after_digest=content_digest(installed).value,
            content=installed,
        ),
        PlannedTarget(path.original, installed, "0644"),
        None,
    )


def _validate_consumer_state(
    request: PlannerRequest,
    resolution: ResolutionResult,
    payloads: Mapping[tuple[str, str], InstalledPayload],
) -> tuple[ControlFinding, ...]:
    """Run every selected package's consumer-state validation before any write.

    Issue #109: enabling a package could plan a file the package's own adoption
    guide cannot use, because nothing consulted the repository state a package
    depends on but does not own. Planning is the last point before a write, so
    this is where an unauthorized adoption has to stop.

    Scoping is structural, never by package id: `consumer_state_input` answers
    only for families whose declared input is repository bytes that exist BEFORE
    this package writes anything. Installed-state validators (Agent Handoff's
    hooks and layout) and document-corpus validators would otherwise report the
    very gaps the pending apply is about to fill, which is the regression T12
    caught in migration planning. Findings are surfaced verbatim: the provider's
    own remediation is the operator's decision, not a rewritten summary.
    """
    # Deferred for the import cycle the executor documents at its own dispatch
    # site: provider_inputs imports command_resolution, which imports the CLI.
    from project_standards.control_plane.provider_inputs import consumer_state_input

    if request.migration_catalog is not None:
        # Legacy migration planning owns its own validation pass and arrives here
        # with legacy authority still standing.
        return ()
    runner = request.provider_runner or invoke_provider
    findings: list[ControlFinding] = []
    for package in resolution.packages:
        version = package.applied.resolved
        payload = payloads.get((package.standard_id, version.value))
        if payload is None:
            continue
        if request.resolution.previous_lock.standards.get(package.standard_id) is not None:
            # Fresh adoption only (REQ-089/#109 wording: "would CREATE"). An
            # already-applied package — including one a V4 migration just
            # published — writes nothing new here, so a repository condition it
            # did not create must not become a new steady-state gate failure.
            continue
        # Issue #118: the resolved options travel with the request because part of
        # the consumer state a package depends on is named BY those options — the
        # declared source and test roots — and is unknowable from a fixed path list.
        snapshots = consumer_state_input(
            request.repo,
            package.standard_id,
            package.effective_config,
        )
        if snapshots is None:
            continue
        for provider in payload.manifest.providers:
            if provider.operation is not ProviderOperation.VALIDATE:
                continue
            result = runner(
                ProviderInvocation(
                    repo=request.repo,
                    payload=payload,
                    standard_id=package.standard_id,
                    version=version,
                    provider_id=provider.id,
                    operation=ProviderOperation.VALIDATE,
                    effective_config=package.effective_config,
                    snapshots=snapshots,
                )
            )
            if result.effect is not ProviderEffect.FINDINGS:
                raise ControlPlaneError("consumer-state validation returned the wrong effect")
            findings.extend(result.findings)
    return tuple(findings)


# One declared target's asserted state after apply: absent, or exact bytes and
# mode. `None` marks a target the plan asserts nothing about, which therefore
# neither conflicts with an alias nor may be skipped as one.
type _EndState = tuple[bytes, str | None] | Literal["absent"] | None

_ALIAS_MUTATIONS = frozenset({ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE})


def _end_state(
    target: str, removed: frozenset[str], planned: Mapping[str, PlannedTarget]
) -> _EndState:
    if target in removed:
        return "absent"
    item = planned.get(target)
    return None if item is None else (item.content, item.mode)


def _alias_analysis(
    repo: Path,
    targets: tuple[SafeRelativePath, ...],
    actions: tuple[ControlAction, ...],
    planned_targets: tuple[PlannedTarget, ...],
) -> tuple[tuple[ControlFinding, ...], tuple[str, ...]]:
    """Reconcile declared targets that a consumer symlink collapsed onto one file.

    Agent Handoff and GitHub Workflow each declare byte-identical twins under
    `.agents/skills/<name>` and `.claude/skills/<name>`. A consumer that links
    one directory at the other leaves two declared targets naming a single
    inode, so publishing the first invalidates the second's plan-time
    precondition and `--apply` stopped with CP-PRECONDITION until a second run
    converged (issue #179 follow-up). The fix belongs at plan time, where the
    resolved shape of the repository is already being read: one publish
    satisfies the whole alias group, and every logical target keeps its own
    action, planned bytes, and lock artifact so the lock still describes both
    declared paths.

    Aliased targets that assert DIFFERENT end states fail closed with an error
    finding instead of racing to a last-writer-wins result: one file cannot hold
    two contents, so applying either would publish a lock the repository
    contradicts. Rejected alternative — writing the group in action order and
    letting the last action win — hides a genuine payload or consumer conflict
    behind a plan that silently discards bytes.

    Returns the conflict findings and the follower targets, in that order.
    """
    resolved = resolved_target_paths(repo, targets)
    groups: dict[PurePosixPath, list[str]] = {}
    for original, physical in resolved.items():
        groups.setdefault(physical, []).append(original)
    aliased = {physical for physical, members in groups.items() if len(members) > 1}
    if not aliased:
        return ((), ())
    removed = frozenset(action.target for action in actions if action.kind is ActionKind.REMOVE)
    planned = {item.target: item for item in planned_targets}
    findings: list[ControlFinding] = []
    for physical in sorted(aliased, key=str):
        declared = [
            (member, state)
            for member in sorted(groups[physical])
            if (state := _end_state(member, removed, planned)) is not None
        ]
        # Naming the first PAIR that actually differs keeps the message useful
        # when three or more names share one file and only one disagrees.
        first, expected = declared[0] if declared else ("", None)
        divergent = next((member for member, state in declared[1:] if state != expected), None)
        if divergent is not None:
            findings.append(
                _finding(
                    "CP-ALIAS-CONFLICT",
                    target=first,
                    identity="$file",
                    standard_id="project-standards",
                    version="",
                    message=(
                        f"declared targets {first} and {divergent} name one repository file "
                        "through a symlink but require different content"
                    ),
                    hint=(
                        "replace the symlink with a real directory, or reconcile the "
                        "declared content of the aliased targets, before applying"
                    ),
                )
            )
    followers: list[str] = []
    published: set[PurePosixPath] = set()
    seen: set[str] = set()
    for action in actions:
        if action.kind not in _ALIAS_MUTATIONS or action.target in seen:
            continue
        seen.add(action.target)
        physical = resolved.get(action.target)
        if physical is None or physical not in aliased:
            continue
        if physical in published:
            followers.append(action.target)
        else:
            published.add(physical)
    return (tuple(findings), tuple(followers))


def plan_reconciliation(request: PlannerRequest) -> ReconciliationPlan:
    """Build one deterministic, complete, and read-only reconciliation plan."""
    original_request = request
    resolution = resolve_packages(request.resolution)
    payloads = _payload_map(request.payloads)
    request, resolution, prepared_transform = _prepare_configuration_transform(
        request,
        resolution,
        payloads,
    )
    selected = _selected_payloads(resolution, payloads)
    selected_declarations = _selected_declaration_governing_options(selected)
    paths = _target_paths(selected, request.resolution.previous_lock)
    if prepared_transform is not None:
        paths = tuple(
            sorted(
                (*paths, SafeRelativePath.parse(".standards/config.toml")),
                key=lambda item: item.original.encode("utf-8"),
            )
        )
    if request.catalog_refresh is not None and request.catalog_refresh.changed:
        paths = tuple(
            sorted(
                (*paths, SafeRelativePath.parse(".standards/catalog.toml")),
                key=lambda item: item.original.encode("utf-8"),
            )
        )
    snapshot = RepositorySnapshot.capture(request.repo, paths)
    if request.retired_targets or request.retired_content:
        # Migration replacement plans must not parse retired whole-file bytes as
        # consumer content. Bounded legacy blocks instead expose their preserved
        # outside bytes. Apply still binds either view to the exact live file.
        retired = {path.original for path in request.retired_targets}
        replacement_content = {path.original: content for path, content in request.retired_content}
        snapshot = RepositorySnapshot(
            snapshot.root,
            snapshot.targets,
            tuple(
                (
                    SnapshotEntry(
                        path=entry.path,
                        kind=EntryKind.MISSING,
                        content=None,
                        mode=entry.mode,
                        link_target=None,
                        content_digest=None,
                        precondition_digest=entry.precondition_digest,
                    )
                    if entry.path.original in retired and entry.kind is EntryKind.REGULAR
                    else SnapshotEntry(
                        path=entry.path,
                        kind=EntryKind.REGULAR,
                        content=replacement_content[entry.path.original],
                        mode=entry.mode,
                        link_target=None,
                        content_digest=content_digest(replacement_content[entry.path.original]),
                        precondition_digest=entry.precondition_digest,
                    )
                    if entry.path.original in replacement_content
                    and entry.kind is EntryKind.REGULAR
                    else entry
                )
                for entry in snapshot.entries
            ),
        )
    config_action: ControlAction | None = None
    config_target: PlannedTarget | None = None
    if prepared_transform is not None:
        config_path = SafeRelativePath.parse(".standards/config.toml")
        config_entry = snapshot.entry(config_path)
        if config_entry.kind is not EntryKind.REGULAR or config_entry.content is None:
            raise ControlPlaneError(
                "configuration transform requires a regular persisted desired config"
            )
        if parse_config(config_entry.content) != original_request.resolution.desired:
            raise ControlPlaneError(
                "persisted desired config differs from the planner transform input"
            )
        rendered_config = render_package_config_transform(
            config_entry.content,
            prepared_transform.evidence.standard_id,
            prepared_transform.after,
            prepared_transform.evidence.declared_pointers,
        )
        if rendered_config != config_entry.content:
            config_action = ControlAction(
                kind=ActionKind.UPDATE,
                target=config_path.original,
                adapter=AdapterKind.TOML.value,
                scope=(f"table:/standards/{prepared_transform.evidence.standard_id}/config"),
                standard_id=prepared_transform.evidence.standard_id,
                summary=(
                    "materialize declared package configuration transform "
                    f"{prepared_transform.evidence.migration_id}"
                ),
                before_digest=config_entry.content_digest.value
                if config_entry.content_digest is not None
                else None,
                after_digest=content_digest(rendered_config).value,
                before_mode=config_entry.mode,
                after_mode=config_entry.mode,
                content=rendered_config,
            )
            config_target = PlannedTarget(
                config_path.original,
                rendered_config,
                config_entry.mode,
            )
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
    historical_create_only = _historical_create_only_units(selected, payloads.values(), registry)
    retained_absence_keys = _retained_create_only_absence_keys(
        groups,
        resolution,
        request.resolution.previous_lock,
    )
    findings.extend(group_findings)
    findings.extend(
        _historical_overlap_findings(
            request.resolution.previous_lock,
            groups,
            request.resolution.transition_paths,
        )
    )
    findings.extend(_namespace_findings(request.repo, selected, request.resolution.previous_lock))
    restore_targets = _managed_restore_targets(
        groups,
        frozenset(finding.path for finding in findings if finding.path),
    )
    actions, units, target_findings, targets = _render_targets(
        snapshot=snapshot,
        groups=groups,
        previous_lock=request.resolution.previous_lock,
        registry=registry,
        blocked_targets=frozenset(finding.path for finding in findings if finding.path),
        retained_absence_keys=retained_absence_keys,
        transitions=request.resolution.transition_paths,
        migration_catalog=request.migration_catalog,
        historical_create_only=historical_create_only,
        selected_declarations=selected_declarations,
    )
    findings.extend(target_findings)
    if request.catalog_refresh is not None and request.catalog_refresh.changed:
        catalog_action, catalog_target, catalog_finding = _catalog_refresh_target(
            request.catalog_refresh,
            snapshot,
        )
        if catalog_finding is not None:
            findings.append(catalog_finding)
        if catalog_action is not None and catalog_target is not None:
            actions = tuple(sort_actions((*actions, catalog_action)))
            targets = tuple(
                sorted((*targets, catalog_target), key=lambda item: item.target.encode("utf-8"))
            )
    findings.extend(_validate_consumer_state(request, resolution, payloads))
    # The configuration action is prepended only at the end, so the analysis is
    # handed the same sequence the executor will publish in — a follower is
    # defined by publication order, and that order must not depend on where a
    # tuple happens to be assembled.
    alias_findings, alias_followers = _alias_analysis(
        request.repo,
        snapshot.targets,
        ((config_action, *actions) if config_action is not None else actions),
        ((config_target, *targets) if config_target is not None else targets),
    )
    findings.extend(alias_findings)
    ordered_findings = tuple(sort_findings(findings))
    applicable = not any(finding.severity == "error" for finding in ordered_findings)
    namespace_prunes = _namespace_prunes(
        request.repo,
        selected,
        units,
        ordered_findings,
    )
    if applicable:
        artifacts, create_only_absences = _locked_after(
            groups=groups,
            targets=targets,
            snapshot=snapshot,
            previous_lock=request.resolution.previous_lock,
            registry=registry,
            retained_absence_keys=retained_absence_keys,
        )
        next_lock = _next_lock(
            request,
            resolution,
            artifacts,
            create_only_absences,
            referenced_inputs,
        )
    else:
        next_lock = request.resolution.previous_lock
    if config_action is not None and config_target is not None:
        actions = (config_action, *actions)
        targets = (config_target, *targets)
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
        namespace_prunes=namespace_prunes,
        catalog_refresh=request.catalog_refresh,
        next_lock=next_lock,
        configuration_transforms=(
            (prepared_transform.evidence,) if prepared_transform is not None else ()
        ),
        restore_targets=restore_targets,
        alias_followers=alias_followers,
    )


def _restore_refusal(
    code: str,
    *,
    target: str,
    message: str,
    hint: str,
    standard_id: str = "project-standards",
    version: str = "",
) -> ManagedRestorePlan:
    finding = ControlFinding(
        code=code,
        severity="error",
        standard_id=standard_id,
        version=version,
        path=target,
        identity="$file",
        message=message,
        hint=hint,
        locus="managed restore",
    )
    return ManagedRestorePlan(False, None, (finding,))


def _restore_authority_snapshot(
    request: PlannerRequest,
    target: str,
) -> tuple[RepositorySnapshot, tuple[TargetPrecondition, ...]] | ManagedRestorePlan:
    authority_paths = tuple(
        SafeRelativePath.parse(path)
        for path in (
            ".standards/config.toml",
            ".standards/catalog.toml",
            ".standards/lock.toml",
        )
    )
    snapshot = RepositorySnapshot.capture(request.repo, authority_paths)
    entries = {entry.path.original: entry for entry in snapshot.entries}
    if any(entry.kind is not EntryKind.REGULAR for entry in entries.values()):
        return _restore_refusal(
            "CP-RESTORE-AUTHORITY",
            target=target,
            message="managed restore requires regular persisted config, catalog, and lock authorities",
            hint="restore the complete control-plane authority before retrying",
        )
    try:
        config_entry = entries[".standards/config.toml"]
        catalog_entry = entries[".standards/catalog.toml"]
        lock_entry = entries[".standards/lock.toml"]
        if (
            config_entry.content is None
            or catalog_entry.content is None
            or lock_entry.content is None
        ):
            raise ControlPlaneError("persisted restore authority has no readable content")
        expected_catalog = (
            request.catalog_refresh.committed
            if request.catalog_refresh is not None
            else request.resolution.catalog
        )
        if (
            parse_config(config_entry.content) != request.resolution.desired
            or parse_catalog(catalog_entry.content) != expected_catalog
            or parse_lock(lock_entry.content) != request.resolution.previous_lock
        ):
            raise ControlPlaneError("persisted restore authority differs from planner inputs")
    except ControlPlaneError, ValueError:
        return _restore_refusal(
            "CP-RESTORE-AUTHORITY",
            target=target,
            message="persisted restore authority does not match the reviewed planner state",
            hint="rebuild the preview from the current config, catalog, and lock",
        )
    return (
        snapshot,
        tuple(
            TargetPrecondition(entry.path.original, entry.precondition_digest.value)
            for entry in snapshot.entries
        ),
    )


def plan_managed_restore(request: PlannerRequest, target: str) -> ManagedRestorePlan:
    """Preview exact restoration of one lock-backed, exclusively managed whole file."""
    try:
        if glob.has_magic(target):
            raise ValueError("glob syntax is not accepted")
        relative = SafeRelativePath.parse(target)
    except ValueError:
        return _restore_refusal(
            "CP-RESTORE-PATH",
            target="",
            message="managed restore requires one canonical repository-relative file path",
            hint="supply one declared path without glob, absolute, or traversal syntax",
        )

    authority = _restore_authority_snapshot(request, relative.original)
    if isinstance(authority, ManagedRestorePlan):
        return authority
    _authority_snapshot, authority_preconditions = authority

    parent = request.repo / relative.normalized.parent
    try:
        parent_metadata = parent.lstat()
    except OSError:
        return _restore_refusal(
            "CP-RESTORE-PATH",
            target=relative.original,
            message="managed restore target parent is not an existing directory",
            hint="create or restore the declared parent through its owning workflow before retrying",
        )
    if not stat.S_ISDIR(parent_metadata.st_mode):
        return _restore_refusal(
            "CP-RESTORE-PATH",
            target=relative.original,
            message="managed restore target parent is not an existing safe directory",
            hint="replace the unsafe parent through its owning workflow before retrying",
        )

    reconciliation = plan_reconciliation(request)
    candidates = [
        item for item in reconciliation.restore_targets if item.target == relative.original
    ]
    if len(candidates) != 1:
        return _restore_refusal(
            "CP-RESTORE-OWNERSHIP",
            target=relative.original,
            message="target is not one unambiguous exclusively managed whole-file declaration",
            hint="no destructive action is authorized for partial, shared, or consumer-owned content",
        )
    candidate = candidates[0]
    locked = [item for item in request.resolution.previous_lock.artifacts if item.path == relative]
    if len(locked) != 1:
        return _restore_refusal(
            "CP-RESTORE-LOCK",
            target=relative.original,
            message="target has no single authoritative lock entry",
            hint="pre-adoption targets cannot use restore; resolve ownership and reconcile first",
            standard_id=candidate.standard_id,
            version=candidate.version,
        )
    lock = locked[0]
    if (
        lock.adapter is not AdapterKind.WHOLE_FILE
        or lock.scope != "$file"
        or lock.policy is not ArtifactPolicy.MANAGED
        or lock.owners != (candidate.standard_id,)
        or lock.shared_identity is not None
    ):
        return _restore_refusal(
            "CP-RESTORE-OWNERSHIP",
            target=relative.original,
            message="lock entry does not prove exclusive managed whole-file ownership",
            hint="no destructive action is authorized for partial, shared, or create-only content",
            standard_id=candidate.standard_id,
            version=candidate.version,
        )

    current = RepositorySnapshot.capture(request.repo, (relative,)).entry(relative)
    if current.kind not in {EntryKind.MISSING, EntryKind.REGULAR}:
        return _restore_refusal(
            "CP-RESTORE-PATH",
            target=relative.original,
            message="managed restore target is neither absent nor a regular file",
            hint="replace the unsafe path with an absent or regular declared target",
            standard_id=candidate.standard_id,
            version=candidate.version,
        )
    current_state = (
        "absent"
        if current.kind is EntryKind.MISSING
        else cast(Sha256Digest, current.content_digest).value
    )
    if current.kind is EntryKind.MISSING:
        action: Literal["overwrite", "recreate", "noop"] = "recreate"
    elif current_state == candidate.digest:
        action = "noop"
    else:
        action = "overwrite"
    preview = ManagedRestorePreview(
        target=relative.original,
        owner=candidate.standard_id,
        current_state=current_state,
        lock_digest=lock.content_digest.value,
        desired_digest=candidate.digest,
        action=action,
        apply_command=(
            "project-standards reconcile --restore-managed "
            f"{shlex.quote(relative.original)} --apply"
        ),
    )
    return ManagedRestorePlan(
        applicable=True,
        preview=preview,
        findings=(),
        target_precondition_digest=current.precondition_digest.value,
        desired_content=candidate.content,
        desired_mode=candidate.mode,
        authority_preconditions=authority_preconditions,
    )
