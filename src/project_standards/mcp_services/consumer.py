"""Consumer inspection and reconciliation services behind the facade (T3, §5.5).

This module composes the existing authoritative control plane and adds no
semantics of its own: ``detect_control_plane_state`` classifies the repository,
``build_planner_request`` assembles the only frozen ``PlannerRequest``,
``plan_reconciliation`` produces the plan, and ``reconciliation_fingerprint``
produces its identity. The DTOs here are mapped views over those values, never a
second durable schema (DR-004).

Three boundary rules drive the shape of everything below.

*Root inputs* are refused before any state is loaded: a repository root must be
explicit, absolute, traversal-free, and resolve to a real directory. Resolution
happens once and the resolved root is what every later phase receives, so a
symlinked root that lands on a real repository is accepted (the approved
boundary is the resolved root) while a symlink *inside* the control plane that
leaves that root is refused by the authoritative loader, which reports it as
malformed without reading the target.

*Unusable control-plane state* splits by operation. ``inspect_repo`` is the
carrier of degraded state: it returns the exact authoritative classification
plus findings derived from it. ``reconcile`` raises a structured
``ServiceError`` instead, because a preview may only ever be an authoritative
``ReconciliationPlan`` projection with an executor-produced fingerprint —
fabricating a degraded plan envelope would invent the very schema §5.5's
stop/backtrack rule forbids. SPEC-MS01 EC-005 is satisfied one layer up, where
the ``reconcile_preview`` tool composes both operations (T9 obligation).

*Diagnostics are content-safe*: messages come from the authoritative
content-safe surfaces (``ControlPlaneState.detail``, ``ControlPlaneError``'s
pre-rendered message) or from fixed text, paths are root-relative, and no
absolute consumer path is ever echoed back.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.diagnostics import ControlFinding, ControlPlaneError
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.executor import reconciliation_fingerprint
from project_standards.control_plane.locking import ControlPlaneBusyError
from project_standards.control_plane.planner import ReconciliationPlan, plan_reconciliation
from project_standards.control_plane.state import (
    ControlPlaneState,
    StateKind,
    detect_control_plane_state,
)
from project_standards.mcp_services.models import ServiceError, ServiceModel
from project_standards.package_contract.diagnostics import PackageContractError

# One immutable JSON tree. Sequences are tuples so a returned preview cannot be
# mutated in place; mappings stay dictionaries because pydantic has no frozen
# mapping type, and each call validates a freshly built projection, so no state
# is shared between calls (proven by the deep-isolation test).
type StableJson = str | int | float | bool | None | tuple[StableJson, ...] | dict[str, StableJson]

# The normalized root identity: stable results never carry an absolute consumer
# path, so the root serializes as "." and every child path is relative to it.
_ROOT_IDENTITY = "."

_ROOT_ERROR_CODE = "repo-root-invalid"
_ROOT_REMEDIATION = (
    "pass an explicit absolute path to an existing repository directory, "
    "without parent-directory segments"
)
_STATE_ERROR_CODE = "control-plane-unavailable"
_PLANNING_ERROR_CODE = "reconciliation-unavailable"
_BUSY_ERROR_CODE = "control-plane-busy"
_BUSY_REMEDIATION = "retry after the concurrent standards operation completes"
_PLANNING_REMEDIATION = "repair the reported control-plane input and preview reconciliation again"
_GENERIC_PLANNING_MESSAGE = "reconciliation could not be planned for this repository"

# Identity fields for findings the service derives from control-plane state.
# ``project-standards`` is the same owner identity the control-plane recovery
# module stamps on its own state findings.
_CONTROL_OWNER = "project-standards"
_CONTROL_IDENTITY = "$control-plane"
_CONTROL_DIRECTORY = ".standards"

_STATE_REMEDIATION = {
    StateKind.UNINITIALIZED: "run `project-standards init` to create the control plane",
    StateKind.LEGACY_ONLY: "migrate the legacy configuration to the unified control plane",
    StateKind.INCOMPLETE: "run `project-standards reconcile --repair-state` to recover",
    StateKind.DUAL_AUTHORITY: (
        "remove the legacy authority file and keep .standards/ as the only authority"
    ),
    StateKind.MALFORMED: "repair the reported control-plane file and rerun inspection",
    StateKind.INCONSISTENT: "align the catalog major recorded across the control-plane files",
    StateKind.TOOL_MISMATCH: "install the release whose major matches the configured catalog",
    StateKind.NEWER_RELEASE: "upgrade the installed release to at least the recorded release",
    StateKind.INTERRUPTED_REFRESH: (
        "run `project-standards reconcile --repair-state` to finish the interrupted refresh"
    ),
}


class Finding(ServiceModel):
    """One control-plane finding in the protocol-neutral §5.5 shape.

    Every field mirrors ``ControlFinding`` one-to-one except the two declared
    renames — ``code`` becomes ``rule_id`` and ``hint`` becomes ``remediation``
    — so an optional structural, locus, conflict, or digest fact can never be
    dropped as the control-plane model evolves. Paths are root-relative.
    """

    rule_id: str
    severity: str
    standard_id: str
    version: str
    path: str
    identity: str
    message: str
    remediation: str
    line: int | None = None
    column: int | None = None
    locus: str | None = None
    observed: int | None = None
    limit: int | None = None
    expected: StableJson | None = None
    actual: StableJson | None = None
    expected_digest: str | None = None
    actual_digest: str | None = None
    governing_options: tuple[str, ...] | None = None
    null_values: tuple[str, ...] = ()
    first_difference_line: int | None = None
    first_difference_expected: str | None = None


class RepoInspectionSnapshot(ServiceModel):
    """Bounded typed view of one consumer control plane (DR-005).

    ``state`` is the authoritative ``StateKind`` value, so an agent always sees
    the exact classification instead of an invented health summary. The three
    parsed-state slots carry the authoritative control-plane models projected to
    JSON, and are absent whenever that state could not be loaded. No consumer
    file content ever appears here.
    """

    repo_root: str
    state: str
    desired_config: StableJson | None
    consumer_catalog: StableJson | None
    central_lock: StableJson | None
    findings: tuple[Finding, ...]


class ReconciliationPreview(ServiceModel):
    """Dry-run reconciliation facts: the existing plan serialization plus its identity.

    Field for field this is ``ReconciliationPlan.to_jsonable()`` (DR-004 — no
    parallel MCP plan schema) with ``reconciliation_fingerprint`` added, after a
    single normalization pass that deep-freezes the projection's sequences. The
    executor-only proposed bytes carried by ``ReconciliationPlan.targets`` are
    deliberately absent: a preview may never publish staged content.
    """

    schema_version: str
    applicable: bool
    actions: tuple[StableJson, ...]
    configuration_transforms: tuple[StableJson, ...]
    units: tuple[StableJson, ...]
    findings: tuple[StableJson, ...]
    preconditions: tuple[StableJson, ...]
    resolution: StableJson
    verification_requests: tuple[StableJson, ...]
    provider_notices: tuple[StableJson, ...]
    namespace_prunes: tuple[str, ...]
    catalog_refresh: StableJson
    next_lock: StableJson
    proposed_lock: StableJson
    reconciliation_fingerprint: str


def resolve_consumer_root(repo_root: Path) -> Path:
    """Return the resolved explicit consumer root, or refuse the input.

    Refusal happens before any state is loaded and never echoes the rejected
    path back: a structured error may not become a filesystem oracle.
    """
    if not isinstance(repo_root, Path):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise _root_error("repository root must be a path")
    if not repo_root.is_absolute():
        # A relative root would resolve against the process working directory,
        # which makes the result depend on ambient state (FR-024, NFR-005).
        raise _root_error("repository root must be an absolute path")
    if ".." in repo_root.parts:
        raise _root_error("repository root must not contain parent-directory segments")
    try:
        resolved = repo_root.resolve(strict=True)
    except OSError as exc:
        raise _root_error("repository root could not be resolved") from exc
    if not resolved.is_dir():
        raise _root_error("repository root must be an existing directory")
    return resolved


def inspect_repo(distribution: InstalledDistribution, repo_root: Path) -> RepoInspectionSnapshot:
    """Return the current bounded snapshot of one consumer control plane."""
    state = _current_state(distribution, repo_root)
    return RepoInspectionSnapshot(
        repo_root=_ROOT_IDENTITY,
        state=state.kind.value,
        desired_config=_projected(state.config),
        consumer_catalog=_projected(state.catalog),
        central_lock=_projected(state.lock),
        findings=tuple(_finding(item) for item in _state_findings(state)),
    )


def reconcile(distribution: InstalledDistribution, repo_root: Path) -> ReconciliationPreview:
    """Return the dry-run reconciliation preview for one consumer repository.

    A preview exists only where the authoritative planner can produce a plan.
    Every other outcome — unusable state, a refused control-plane input, lock
    contention — is a structured failure, because the alternative would be an
    invented plan envelope with an invented fingerprint. ``inspect_repo`` is
    where an agent learns *why* the repository cannot be planned.
    """
    state = _current_state(distribution, repo_root)
    if state.kind is not StateKind.INITIALIZED:
        raise ServiceError(
            code=_STATE_ERROR_CODE,
            message=_safe_message(
                state.detail or f"control plane is {state.kind.value}", state.repo
            ),
            remediation=_STATE_REMEDIATION.get(state.kind, _PLANNING_REMEDIATION),
            path=_state_path(state),
            severity="error",
        )
    try:
        plan = plan_reconciliation(
            build_planner_request(state.repo, distribution, frozenset(), state=state)
        )
    except ControlPlaneBusyError as exc:
        raise _busy_error() from exc
    except ControlPlaneError as exc:
        # ControlPlaneError publishes a pre-rendered content-safe message and
        # typed structural coordinates; str(exc) would append rendered location
        # text, so the safe message and the relative path are used instead.
        raise ServiceError(
            code=_PLANNING_ERROR_CODE,
            message=_safe_message(exc.message, state.repo),
            remediation=_PLANNING_REMEDIATION,
            path=_relative(exc.path),
            severity="error",
        ) from exc
    except (PackageContractError, ValueError, OSError) as exc:
        # These carry no content-safety contract — a package-contract failure
        # can name an absolute installed path — so only fixed text is published.
        raise ServiceError(
            code=_PLANNING_ERROR_CODE,
            message=_GENERIC_PLANNING_MESSAGE,
            remediation=_PLANNING_REMEDIATION,
            severity="error",
        ) from exc
    return _preview(plan)


def _root_error(message: str) -> ServiceError:
    return ServiceError(
        code=_ROOT_ERROR_CODE,
        message=message,
        remediation=_ROOT_REMEDIATION,
        severity="error",
    )


def _busy_error() -> ServiceError:
    return ServiceError(
        code=_BUSY_ERROR_CODE,
        message="the consumer control plane is locked by another standards operation",
        remediation=_BUSY_REMEDIATION,
        severity="error",
    )


def _current_state(distribution: InstalledDistribution, repo_root: Path) -> ControlPlaneState:
    """Reload the authoritative state for one call; nothing is cached across calls.

    The root is resolved exactly once here and the resolved value is what every
    later phase receives, so containment is decided in one place.
    """
    resolved = resolve_consumer_root(repo_root)
    try:
        return detect_control_plane_state(resolved, tool_release=distribution.tool_release.value)
    except ControlPlaneBusyError as exc:
        raise _busy_error() from exc
    except ValueError as exc:
        raise _root_error("repository root could not be inspected") from exc


def _relative(path: str | None) -> str | None:
    """Keep only root-relative paths; an absolute path never leaves the service."""
    if path is None:
        return None
    return None if Path(path).is_absolute() else path


def _safe_message(message: str, root: Path) -> str:
    """Refuse to publish any message that names the resolved consumer root."""
    return _GENERIC_PLANNING_MESSAGE if str(root) in message else message


def _state_path(state: ControlPlaneState) -> str | None:
    if state.malformed_file is not None:
        return f"{_CONTROL_DIRECTORY}/{state.malformed_file}"
    if state.missing_files:
        return f"{_CONTROL_DIRECTORY}/{state.missing_files[0]}"
    return _CONTROL_DIRECTORY if state.kind is not StateKind.UNINITIALIZED else None


def _projected(model: Any) -> StableJson | None:
    if model is None:
        return None
    return _stable(model.model_dump(mode="json"))


def _stable(value: object) -> StableJson:
    """Normalize one authoritative projection into the immutable JSON tree.

    The authoritative serializers emit dataclass projections that still contain
    tuples, so this pass is what makes the preview's declared type honest — and
    it deep-freezes every sequence on the way through.
    """
    if value is None or isinstance(value, str | bool | int | float):
        return value
    if isinstance(value, Mapping):
        mapping = cast("Mapping[object, object]", value)
        return {str(key): _stable(item) for key, item in mapping.items()}
    if isinstance(value, Sequence) and not isinstance(value, bytes | bytearray):
        sequence = cast("Sequence[object]", value)
        return tuple(_stable(item) for item in sequence)
    # Unreachable for authoritative output (bytes included: proposed content is
    # executor-only). Refusing beats publishing an opaque object or raw bytes
    # into a stable result.
    raise ServiceError(
        code=_PLANNING_ERROR_CODE,
        message=_GENERIC_PLANNING_MESSAGE,
        remediation=_PLANNING_REMEDIATION,
        severity="error",
    )


def _state_findings(state: ControlPlaneState) -> tuple[ControlFinding, ...]:
    """Describe one unusable control-plane state as authoritative findings."""
    if state.kind is StateKind.INITIALIZED:
        return ()
    remediation = _STATE_REMEDIATION.get(state.kind, _PLANNING_REMEDIATION)
    message = _safe_message(state.detail or f"control plane is {state.kind.value}", state.repo)
    code = f"control-plane-{state.kind.value}"
    if state.missing_files:
        return tuple(
            _control_finding(
                code=code,
                path=f"{_CONTROL_DIRECTORY}/{name}",
                message=message,
                hint=remediation,
            )
            for name in state.missing_files
        )
    path = (
        f"{_CONTROL_DIRECTORY}/{state.malformed_file}"
        if state.malformed_file is not None
        else _CONTROL_DIRECTORY
    )
    return (
        _control_finding(
            code=code,
            path=path,
            message=message,
            hint=remediation,
            line=state.line,
            column=state.column,
        ),
    )


def _control_finding(
    *,
    code: str,
    path: str,
    message: str,
    hint: str,
    line: int | None = None,
    column: int | None = None,
) -> ControlFinding:
    return ControlFinding(
        code=code,
        severity="error",
        standard_id=_CONTROL_OWNER,
        version="",
        path=path,
        identity=_CONTROL_IDENTITY,
        message=message,
        hint=hint,
        line=line,
        column=column,
    )


def _finding(finding: ControlFinding) -> Finding:
    return Finding(
        rule_id=finding.code,
        severity=finding.severity,
        standard_id=finding.standard_id,
        version=finding.version,
        path=finding.path,
        identity=finding.identity,
        message=finding.message,
        remediation=finding.hint,
        line=finding.line,
        column=finding.column,
        locus=finding.locus,
        observed=finding.observed,
        limit=finding.limit,
        expected=_stable(finding.expected),
        actual=_stable(finding.actual),
        expected_digest=finding.expected_digest,
        actual_digest=finding.actual_digest,
        governing_options=finding.governing_options,
        null_values=finding.null_values,
        first_difference_line=finding.first_difference_line,
        first_difference_expected=finding.first_difference_expected,
    )


def _sequence(value: StableJson) -> tuple[StableJson, ...]:
    """Narrow one already-normalized list field; the projection declares it a list."""
    assert isinstance(value, tuple)
    return value


def _strings(value: StableJson) -> tuple[str, ...]:
    return tuple(str(item) for item in _sequence(value))


def _preview(plan: ReconciliationPlan) -> ReconciliationPreview:
    """Map one authoritative plan onto the frozen preview DTO."""
    public = _stable(plan.to_jsonable())
    assert isinstance(public, dict)
    return ReconciliationPreview(
        schema_version=str(public["schema_version"]),
        applicable=bool(public["applicable"]),
        actions=_sequence(public["actions"]),
        configuration_transforms=_sequence(public["configuration_transforms"]),
        units=_sequence(public["units"]),
        findings=_sequence(public["findings"]),
        preconditions=_sequence(public["preconditions"]),
        resolution=public["resolution"],
        verification_requests=_sequence(public["verification_requests"]),
        provider_notices=_sequence(public["provider_notices"]),
        namespace_prunes=_strings(public["namespace_prunes"]),
        catalog_refresh=public["catalog_refresh"],
        next_lock=public["next_lock"],
        proposed_lock=public["proposed_lock"],
        # The executor is the only producer of a reconciliation identity.
        reconciliation_fingerprint=reconciliation_fingerprint(plan),
    )
