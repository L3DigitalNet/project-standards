"""Bounded, non-mutating provider services behind the facade (T4, §5.5, ADR 0025).

Three frozen operations live here: ``invoke_read_provider`` dispatches exactly
one declared provider, and ``validate_repo``/``drift_check`` compose it over the
consumer's *current* exact resolution.

Nothing in this module re-implements provider semantics or process transport.
Identity qualification, payload-resource closure, input/output validation, the
declared-live-path integrity check, typed results, and the ADR 0025 execution
boundary all belong to the control plane. This service retains only MCP request
qualification, authoritative composite-input selection, and DTO mapping:

* the shared runner spawns exactly one child — the fixed interpreter worker for
  Python or the verified materialized executable for a command — so provider
  code cannot block the protocol loop or write to the stdio transport descriptor;
* a 30-second per-invocation bound read from ``PROVIDER_TIMEOUT_SECONDS`` at call
  time (so a test or an operator can inject a different bound without the value
  being baked into a default argument), enforced by SIGTERM then SIGKILL with
  reaping on both paths;
* bounded JSON transport in both directions with never-silent truncation;
* release of every pipe, descriptor, and child on all four completion paths —
  success, timeout, kill, and crash — plus parent-side cancellation.

Two refusal rules are enforced *before* a process is created, because a refusal
that has already spawned a worker has already paid the cost it exists to avoid:
the operation must be one of the four ADR-approved ones, and the selected
declaration's effect must be ``findings``. Everything else — every
``mutation-plan``, every ``migration-report``, every ``content`` operation, and
``semantic-review`` despite its findings effect — is rejected while the request
is still just data.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, cast

from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.command_resolution import selected_command
from project_standards.control_plane.diagnostics import ControlFinding, ControlPlaneError
from project_standards.control_plane.distribution import InstalledDistribution, InstalledPayload
from project_standards.control_plane.executor import reconciliation_fingerprint
from project_standards.control_plane.locking import ControlPlaneBusyError, LockMode
from project_standards.control_plane.planner import ReconciliationPlan, plan_reconciliation
from project_standards.control_plane.provider_subprocess import (
    DIAGNOSTIC_LIMIT_CHARS,
    ProviderSubprocessError,
    compose_provider_diagnostics,
    python_worker_argv,
    python_worker_environment,
    run_provider_subprocess,
    safe_failure_detail,
)
from project_standards.control_plane.provider_subprocess import (
    PROVIDER_TIMEOUT_SECONDS as _DEFAULT_PROVIDER_TIMEOUT_SECONDS,
)
from project_standards.control_plane.provider_worker import (
    INPUT_AUTHORITY_FIELD,
    SEAM_AUTHORITY,
    authoritative_provider_input,
)
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.control_plane.resolution import resolve_packages
from project_standards.mcp_services.consumer import (
    Finding,
    StableJson,
    map_finding,
    resolve_consumer_root,
    stable_json,
)
from project_standards.mcp_services.models import ServiceError, ServiceModel
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.payload import (
    JsonObject,
    ProviderDeclaration,
    ProviderEffect,
    ProviderKind,
)

# ADR 0025: "The provider timeout is 30 seconds per provider invocation." This is
# a module global rather than a default argument on purpose — the execution path
# reads it at call time, which is what makes the bound injectable and therefore
# provable in both directions.
PROVIDER_TIMEOUT_SECONDS: float = _DEFAULT_PROVIDER_TIMEOUT_SECONDS

# The request is written to the worker's stdin incrementally inside the same
# deadline-bound loop that drains its output, so it may exceed a pipe buffer
# without the parent ever blocking on its own child; the cap only bounds what a
# caller can make the boundary carry.
REQUEST_LIMIT_BYTES = 262_144

# ADR 0025's T1-approved non-mutating effect set: effect `findings`, restricted
# to these four operations. `semantic-review` also declares `findings` and is
# deliberately absent (SPEC-RD01 OQ-006), as is the whole `content` effect.
_APPROVED_OPERATIONS = frozenset({"validate", "verify", "lint", "drift-check"})

_STATUS_COMPLETED = "completed"

# Who builds the dispatched provider's typed input. `invoke_read_provider` keeps
# the caller's unchanged. For composites, the Python worker builds the corpus on
# its side of the bounded request, while a command is prepared in the parent and
# receives the same authority result directly through its own stdin.
_CALLER_AUTHORITY = "caller"

# Composite dispatch supplies no input of its own. The empty object is not a
# placeholder: it is exactly what a standard outside the seam's five families
# still receives, so fixture and third-party standards keep the generic dispatch
# they have always had while every shipping provider is seam-served
# (pinned by TC-T14-004).
_SEAM_DIRECTIVE_INPUT: dict[str, Any] = {}

_ROOT_IDENTITY = "."

_DISPATCH_REMEDIATION = (
    "request a declared validate, verify, lint, or drift-check provider of the "
    "currently resolved package version"
)
# Deliberately makes no claim about the repository's state. Terminating a worker
# ends execution; it does not undo a write a trusted payload already performed,
# and ADR 0025 buys fault isolation rather than rollback (T4.4 Codex GREEN review
# F1, disposition REJECT-AS-WRITTEN / ACCEPT-BOUNDED).
_TIMEOUT_REMEDIATION = (
    "re-run after the provider is fixed or its work is reduced, then inspect the "
    "repository with repo_inspect"
)
_STATE_REMEDIATION = "repair the reported control-plane input and retry the operation"
_INPUT_REMEDIATION = "pass typed provider input containing only JSON-safe values with string keys"


class ProviderOperationResult(ServiceModel):
    """One completed provider invocation in the frozen §5.5 shape.

    ``output`` is the validated provider output the dispatcher already published
    (``ProviderResult.structured_output``) — "every declared output-schema
    field", not a re-derived subset. ``diagnostics`` is bounded supplemental text
    that never participates in any identity (DR-008); it is the only field whose
    value may legitimately differ between two otherwise identical calls, because
    it carries worker-side output such as process identity.
    """

    standard_id: str
    version: str
    provider_id: str
    operation: str
    phase: str
    effect: str
    status: str
    findings: tuple[Finding, ...]
    diagnostics: str
    output: StableJson


class ValidationReport(ServiceModel):
    """Applicable validate/verify/lint results for one consumer repository."""

    repo_root: str
    results: tuple[ProviderOperationResult, ...]
    findings: tuple[Finding, ...]


class DriftReport(ServiceModel):
    """Authoritative reconciliation facts plus applicable drift-check results.

    ``actions`` and ``findings`` are the plan's own public serialization and
    ``reconciliation_fingerprint`` is the executor's own identity, so no
    confidence, relevance, or clean-state boolean is synthesized here — §5.5
    forbids inventing one, and this DTO deliberately carries no boolean at all.
    """

    repo_root: str
    reconciliation_fingerprint: str
    actions: tuple[StableJson, ...]
    findings: tuple[StableJson, ...]
    results: tuple[ProviderOperationResult, ...]


@dataclass(frozen=True, slots=True)
class _Selection:
    """One exactly qualified declaration bound to its resolved payload version."""

    standard_id: str
    version: str
    declaration: ProviderDeclaration


def _error(
    code: str,
    message: str,
    remediation: str,
    *,
    standard_id: str | None = None,
    version: str | None = None,
) -> ServiceError:
    return ServiceError(
        code=code,
        message=message,
        remediation=remediation,
        standard_id=standard_id,
        version=version,
    )


# Every authoritative control-plane entry point this module calls fails through
# the same three classes, so the mapping onto the T2/T3 four-code taxonomy lives
# in one place rather than being repeated per call site (T4.5).
_CONTROL_PLANE_FAILURES = (
    ControlPlaneBusyError,
    ControlPlaneError,
    PackageContractError,
    ValueError,
    OSError,
)


def _control_plane_error(exc: BaseException, fallback: str) -> ServiceError:
    """Map one authoritative control-plane failure onto a content-safe service error."""
    if isinstance(exc, ControlPlaneBusyError):
        return _error(
            "control-plane-busy",
            "the consumer control plane is locked by another standards operation",
            "retry after the concurrent standards operation completes",
        )
    if isinstance(exc, ControlPlaneError):
        # ControlPlaneError publishes a pre-rendered content-safe message; the
        # other classes carry no such contract, so only fixed text is published.
        return _error("control-plane-unavailable", exc.message, _STATE_REMEDIATION)
    return _error("control-plane-unavailable", fallback, _STATE_REMEDIATION)


def _resolved_selection(
    distribution: InstalledDistribution, root: Path
) -> dict[str, tuple[str, InstalledPayload]]:
    """Return the current exact resolution as {standard_id: (version, payload)}.

    This is the same resolution ``selected_command`` performs, taken once for the
    whole call so a composite tool cannot see two different selections while it
    runs. It is a pure read: no provider executes here.
    """
    try:
        request = build_planner_request(root, distribution, frozenset())
        resolution = resolve_packages(request.resolution)
    except _CONTROL_PLANE_FAILURES as exc:
        raise _control_plane_error(
            exc, "the consumer control plane could not be resolved for provider dispatch"
        ) from exc
    payloads = {
        (item.manifest.payload.standard, item.manifest.payload.version.value): item
        for item in request.payloads
    }
    selected: dict[str, tuple[str, InstalledPayload]] = {}
    for package in resolution.packages:
        version = package.applied.resolved.value
        payload = payloads.get((package.standard_id, version))
        if payload is not None:
            selected[package.standard_id] = (version, payload)
    return selected


def _qualify(
    selected: dict[str, tuple[str, InstalledPayload]],
    *,
    standard_id: str,
    version: str,
    provider_id: str,
    operation: str,
) -> _Selection:
    """Refuse anything the current resolution does not exactly authorize.

    The requested version is a *qualification*, never a selector: there is no
    authoritative effective configuration for a version the resolution rejected,
    so reaching one would mean inventing inputs the control plane never produced.
    """
    if operation not in _APPROVED_OPERATIONS:
        raise _error(
            "provider-operation-refused",
            f"operation {operation!r} is outside the approved read-only provider set",
            _DISPATCH_REMEDIATION,
            standard_id=standard_id,
            version=version,
        )
    entry = selected.get(standard_id)
    if entry is None:
        raise _error(
            "provider-not-selected",
            f"the current resolution does not select {standard_id!r}",
            _DISPATCH_REMEDIATION,
            standard_id=standard_id,
            version=version,
        )
    resolved_version, payload = entry
    if resolved_version != version:
        raise _error(
            "provider-not-selected",
            f"the current resolution selects {standard_id!r} at a different version",
            _DISPATCH_REMEDIATION,
            standard_id=standard_id,
            version=version,
        )
    matches = [item for item in payload.manifest.providers if item.id == provider_id]
    if len(matches) != 1:
        raise _error(
            "provider-not-found",
            f"{standard_id!r} does not declare exactly one provider {provider_id!r}",
            _DISPATCH_REMEDIATION,
            standard_id=standard_id,
            version=version,
        )
    declaration = matches[0]
    if declaration.operation.value != operation:
        raise _error(
            "provider-operation-refused",
            f"provider {provider_id!r} does not declare operation {operation!r}",
            _DISPATCH_REMEDIATION,
            standard_id=standard_id,
            version=version,
        )
    if declaration.effect is not ProviderEffect.FINDINGS:
        raise _error(
            "provider-effect-refused",
            f"provider {provider_id!r} declares the {declaration.effect.value!r} effect, "
            "which this read-only service never dispatches",
            _DISPATCH_REMEDIATION,
            standard_id=standard_id,
            version=version,
        )
    return _Selection(standard_id=standard_id, version=version, declaration=declaration)


def _encoded_request(payload: dict[str, Any]) -> bytes:
    """Serialize the worker request, refusing anything not JSON-safe or bounded."""
    try:
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise _error(
            "provider-input-invalid",
            "typed provider input is not JSON-safe",
            _INPUT_REMEDIATION,
        ) from exc
    if len(encoded) > REQUEST_LIMIT_BYTES:
        raise _error(
            "provider-input-invalid",
            f"typed provider input serialized to {len(encoded)} bytes, above the "
            f"{REQUEST_LIMIT_BYTES}-byte request limit",
            _INPUT_REMEDIATION,
        )
    return encoded


def _validate_tree(value: object, location: str) -> None:
    """Reject anything that is not strict JSON with string keys, at every depth.

    Checking only the top level is not enough: ``{"n": {1: "a", "1": "b"}}``
    serializes to an object with two ``"1"`` keys, one of which the receiving
    parser silently discards, so the worker would not receive the exact typed
    input the caller passed (T4.4 Codex GREEN review, finding 5).
    """
    if value is None or isinstance(value, str | bool | int):
        return
    if isinstance(value, float):
        if value != value or value in {float("inf"), float("-inf")}:
            raise _error(
                "provider-input-invalid",
                f"typed provider input has a non-finite number at {location}",
                _INPUT_REMEDIATION,
            )
        return
    if isinstance(value, dict):
        mapping = cast("dict[object, object]", value)
        for key in mapping:
            if not isinstance(key, str):
                raise _error(
                    "provider-input-invalid",
                    f"typed provider input has a non-string key at {location}",
                    _INPUT_REMEDIATION,
                )
            _validate_tree(mapping[key], f"{location}.{key}")
        return
    if isinstance(value, list | tuple):
        sequence = list(cast("list[object] | tuple[object, ...]", value))
        for index, item in enumerate(sequence):
            _validate_tree(item, f"{location}[{index}]")
        return
    raise _error(
        "provider-input-invalid",
        f"typed provider input has a value that is not JSON at {location}",
        _INPUT_REMEDIATION,
    )


def _validated_input(provider_input: Any) -> dict[str, Any]:
    if provider_input is None:
        return {}
    if not isinstance(provider_input, dict):
        raise _error(
            "provider-input-invalid",
            "typed provider input must be a JSON object",
            _INPUT_REMEDIATION,
        )
    mapping = cast("dict[str, Any]", provider_input)
    _validate_tree(mapping, "$")
    return dict(mapping)


def _frame_error(reason: str, selection: _Selection) -> ServiceError:
    return _error(
        "provider-frame-invalid",
        f"the bounded provider worker returned {reason}",
        _DISPATCH_REMEDIATION,
        standard_id=selection.standard_id,
        version=selection.version,
    )


def _validated_frame(frame: dict[str, Any], selection: _Selection) -> dict[str, Any]:
    """Validate the provider-specific fields after generic frame validation.

    The process that executes provider bytes also owns the response descriptor,
    so a payload that violates its declaration can write whatever it likes here.
    ADR 0025's trust model already grants those bytes far more than this on the
    authoritative in-process path, so the answer is not another sandbox
    (plan:339) — it is that the parent believes nothing it has not checked
    (T4.4 Codex GREEN review, finding 2, disposition ACCEPT-BOUNDED).
    """
    status = frame.get("status")
    if status == "error":
        return frame
    if not isinstance(frame.get("effect"), str):
        raise _frame_error("a result with no declared effect", selection)
    notice = frame.get("output_notice")
    if notice is not None and not isinstance(notice, str):
        raise _frame_error("a result with a malformed output notice", selection)
    output = frame.get("output")
    if output is not None and not isinstance(output, dict):
        raise _frame_error("a result whose output is not a JSON object", selection)
    findings = frame.get("findings")
    if not isinstance(findings, list):
        raise _frame_error("a result whose findings are not an array", selection)
    for item in cast("list[object]", findings):
        if not isinstance(item, dict):
            raise _frame_error("a result containing a malformed finding", selection)
        _validated_raw_finding(cast("dict[str, Any]", item), selection)
    return frame


_REQUIRED_FINDING_FIELDS = ("code", "severity", "standard_id", "version", "path", "identity")
_TEXT_FINDING_FIELDS = (*_REQUIRED_FINDING_FIELDS, "message", "hint")


def _validated_raw_finding(item: dict[str, Any], selection: _Selection) -> None:
    unknown = set(item) - set(_CONTROL_FINDING_FIELDS)
    if unknown:
        raise _frame_error("a finding with undeclared fields", selection)
    for name in _TEXT_FINDING_FIELDS:
        if not isinstance(item.get(name), str):
            raise _frame_error(f"a finding with a malformed {name}", selection)


_CONTROL_FINDING_FIELDS = tuple(item.name for item in fields(ControlFinding))


def _contained_finding_path(value: str, root: Path, selection: _Selection) -> str:
    """Resolve one finding path against the consumer root and require containment.

    Relative paths need this as much as absolute ones: ``../outside/secret`` is
    already root-relative in shape and would have been published unchanged
    (T4.4 Codex GREEN review, finding 6). An uncontainable path is a provider
    contract violation, and it is reported as a structured per-invocation failure
    rather than silently rewritten — no schema is invented and no path a caller
    may not see is echoed back.
    """
    candidate = Path(value)
    try:
        resolved = (candidate if candidate.is_absolute() else root / candidate).resolve()
        return resolved.relative_to(root).as_posix()
    except (OSError, ValueError) as exc:
        raise _error(
            "provider-result-invalid",
            "the provider reported a finding outside the consumer repository",
            _DISPATCH_REMEDIATION,
            standard_id=selection.standard_id,
            version=selection.version,
        ) from exc


def _finding(raw: dict[str, Any], root: Path, selection: _Selection) -> Finding:
    """Rebuild one authoritative finding, then apply the declared DR-003 mapping."""
    prepared: dict[str, Any] = {}
    for name in _CONTROL_FINDING_FIELDS:
        value = raw.get(name)
        prepared[name] = tuple(cast("list[Any]", value)) if isinstance(value, list) else value
    prepared["path"] = _contained_finding_path(str(prepared["path"]), root, selection)
    return map_finding(ControlFinding(**prepared))


def invoke_read_provider(
    distribution: InstalledDistribution,
    repo_root: Path,
    *,
    standard_id: str,
    version: str,
    provider_id: str,
    operation: str,
    provider_input: Any = None,
) -> ProviderOperationResult:
    """Dispatch exactly one approved, non-mutating provider through a bounded worker."""
    root = resolve_consumer_root(repo_root)
    typed_input = _validated_input(provider_input)
    selected = _resolved_selection(distribution, root)
    selection = _qualify(
        selected,
        standard_id=standard_id,
        version=version,
        provider_id=provider_id,
        operation=operation,
    )
    return _dispatch(distribution, root, selection, typed_input)


def _dispatch(
    distribution: InstalledDistribution,
    root: Path,
    selection: _Selection,
    typed_input: dict[str, Any],
    *,
    input_authority: str = _CALLER_AUTHORITY,
) -> ProviderOperationResult:
    if selection.declaration.kind is ProviderKind.COMMAND:
        return _dispatch_command(
            distribution,
            root,
            selection,
            typed_input,
            input_authority=input_authority,
        )
    request = _encoded_request(
        {
            "package_root": str(distribution.package_root),
            "tool_release": distribution.tool_release.value,
            "repo_root": str(root),
            "standard_id": selection.standard_id,
            "version": selection.version,
            "provider_id": selection.declaration.id,
            "operation": selection.declaration.operation.value,
            "provider_input": typed_input,
            INPUT_AUTHORITY_FIELD: input_authority,
        }
    )
    # Read the bound at call time: this is the injection seam the ADR-approved
    # value is proven against in both directions.
    try:
        outcome = run_provider_subprocess(
            python_worker_argv(),
            request,
            timeout=float(PROVIDER_TIMEOUT_SECONDS),
            environment=python_worker_environment(),
        )
    except ProviderSubprocessError as exc:
        raise _error(
            exc.code,
            exc.message,
            exc.remediation,
            standard_id=selection.standard_id,
            version=selection.version,
        ) from exc
    response = _validated_frame(cast("dict[str, Any]", outcome.frame), selection)
    if response.get("status") != "ok":
        code = response.get("code")
        detail = response.get("detail")
        raise _error(
            code if isinstance(code, str) and code else "provider-invocation-failed",
            # Re-filtered here, not merely trusted: the worker already redacts its
            # own failure text, but a frame written by provider bytes has not been
            # through that filter (finding 2).
            safe_failure_detail(
                str(detail) if isinstance(detail, str) else "the provider invocation failed",
                (str(root), str(distribution.package_root)),
            ),
            _DISPATCH_REMEDIATION,
            standard_id=selection.standard_id,
            version=selection.version,
        )
    raw_findings: list[dict[str, Any]] = list(response.get("findings") or [])
    return ProviderOperationResult(
        standard_id=selection.standard_id,
        version=selection.version,
        provider_id=selection.declaration.id,
        operation=selection.declaration.operation.value,
        phase=selection.declaration.phase.value,
        effect=selection.declaration.effect.value,
        status=_STATUS_COMPLETED,
        findings=tuple(_finding(item, root, selection) for item in raw_findings),
        diagnostics=compose_provider_diagnostics(
            cast(str | None, response.get("output_notice")),
            outcome.stdout,
            outcome.stderr,
        ),
        output=stable_json(response.get("output")),
    )


def _dispatch_command(
    distribution: InstalledDistribution,
    root: Path,
    selection: _Selection,
    typed_input: dict[str, Any],
    *,
    input_authority: str,
) -> ProviderOperationResult:
    """Dispatch a command directly so each required provider is its only child.

    Plan-bound input may require another command provider's content first. That
    contribution uses this same kind-aware parent runner; the target command is
    still invoked only afterward with the completed plan's input.
    """
    try:
        with selected_command(
            root,
            selection.standard_id,
            distribution,
            mode=LockMode.READ,
            require_reconciled=False,
        ) as qualified:
            if qualified is None or qualified.resolved.value != selection.version:
                raise ControlPlaneError("qualified command provider selection changed")
            identity = qualified.payload.manifest.payload
            matches = [
                declaration
                for declaration in qualified.payload.manifest.providers
                if declaration.id == selection.declaration.id
            ]
            if (
                identity.standard != selection.standard_id
                or len(matches) != 1
                or matches[0] != selection.declaration
            ):
                raise ControlPlaneError("qualified command provider selection changed")
            snapshots = typed_input
            if input_authority == SEAM_AUTHORITY:
                authoritative = authoritative_provider_input(
                    qualified,
                    selection.declaration.operation,
                    provider_id=selection.declaration.id,
                    planner_runner=invoke_provider,
                )
                snapshots = {} if authoritative is None else dict(authoritative)
            result = invoke_provider(
                ProviderInvocation(
                    repo=qualified.repo,
                    payload=qualified.payload,
                    standard_id=selection.standard_id,
                    version=qualified.resolved,
                    provider_id=selection.declaration.id,
                    operation=selection.declaration.operation,
                    effective_config=qualified.effective_config,
                    snapshots=cast("JsonObject", snapshots),
                )
            )
    except _CONTROL_PLANE_FAILURES as exc:
        cause = exc.__cause__
        if isinstance(cause, ProviderSubprocessError):
            raise _error(
                cause.code,
                cause.message,
                cause.remediation,
                standard_id=selection.standard_id,
                version=selection.version,
            ) from exc
        mapped = _control_plane_error(
            exc,
            "the command provider could not be dispatched from the qualified selection",
        )
        raise _error(
            mapped.code,
            mapped.message,
            mapped.remediation,
            standard_id=selection.standard_id,
            version=selection.version,
        ) from exc

    raw_findings = [asdict(finding) for finding in result.findings]
    return ProviderOperationResult(
        standard_id=selection.standard_id,
        version=selection.version,
        provider_id=selection.declaration.id,
        operation=selection.declaration.operation.value,
        phase=selection.declaration.phase.value,
        effect=selection.declaration.effect.value,
        status=_STATUS_COMPLETED,
        findings=tuple(_finding(item, root, selection) for item in raw_findings),
        diagnostics=_bounded(result.output_notice or ""),
        output=stable_json(result.structured_output),
    )


def _applicable(
    selected: dict[str, tuple[str, InstalledPayload]], operations: frozenset[str]
) -> tuple[_Selection, ...]:
    """Return every resolved declaration for these operations in the DR-009 order."""
    found: list[_Selection] = []
    for standard_id, (version, payload) in selected.items():
        for declaration in payload.manifest.providers:
            if declaration.operation.value in operations:
                found.append(
                    _Selection(standard_id=standard_id, version=version, declaration=declaration)
                )
    return tuple(
        sorted(found, key=lambda item: (item.standard_id, item.version, item.declaration.id))
    )


def _failed_result(selection: _Selection, error: ServiceError) -> ProviderOperationResult:
    """Publish one provider failure as a typed result instead of aborting the report.

    A composite answers for every applicable provider, so one provider that
    crashes, exhausts its execution bound, or returns an unreadable frame must not
    delete its siblings' answers. The §5.5 result shape is closed and declares no
    error field, so the outcome lands in the two fields it does declare: ``status``
    carries the stable service code — the same taxonomy a single-provider dispatch
    raises, so a caller reads one vocabulary either way — and ``diagnostics``
    carries the already content-safe message and remediation. ``findings`` is
    empty because none were produced, never because none exist.
    """
    return ProviderOperationResult(
        standard_id=selection.standard_id,
        version=selection.version,
        provider_id=selection.declaration.id,
        operation=selection.declaration.operation.value,
        phase=selection.declaration.phase.value,
        effect=selection.declaration.effect.value,
        status=error.code,
        findings=(),
        diagnostics=_bounded(f"{error.message}\n{error.remediation}"),
        output=stable_json(None),
    )


def _bounded(text: str) -> str:
    if len(text) <= DIAGNOSTIC_LIMIT_CHARS:
        return text
    omitted = len(text) - DIAGNOSTIC_LIMIT_CHARS
    return (
        text[:DIAGNOSTIC_LIMIT_CHARS]
        + f"\n[project-standards: {omitted} further diagnostic characters omitted "
        f"after the {DIAGNOSTIC_LIMIT_CHARS}-character limit]"
    )


def _composite_dispatch(
    distribution: InstalledDistribution, root: Path, selection: _Selection
) -> ProviderOperationResult:
    """Dispatch one composite member under the seam directive, failing per result."""
    try:
        return _dispatch(
            distribution,
            root,
            selection,
            dict(_SEAM_DIRECTIVE_INPUT),
            input_authority=SEAM_AUTHORITY,
        )
    except ServiceError as exc:
        return _failed_result(selection, exc)


def validate_repo(distribution: InstalledDistribution, repo_root: Path) -> ValidationReport:
    """Run every applicable validate/verify/lint provider for one consumer root."""
    root = resolve_consumer_root(repo_root)
    selected = _resolved_selection(distribution, root)
    results = tuple(
        _composite_dispatch(distribution, root, selection)
        for selection in _applicable(selected, frozenset({"validate", "verify", "lint"}))
    )
    return ValidationReport(
        repo_root=_ROOT_IDENTITY,
        results=results,
        findings=tuple(finding for result in results for finding in result.findings),
    )


def drift_check(distribution: InstalledDistribution, repo_root: Path) -> DriftReport:
    """Return authoritative reconciliation facts plus applicable drift-check results."""
    root = resolve_consumer_root(repo_root)
    selected = _resolved_selection(distribution, root)
    plan = _plan(distribution, root)
    public = stable_json(plan.to_jsonable())
    assert isinstance(public, dict)
    actions = public["actions"]
    findings = public["findings"]
    assert isinstance(actions, tuple)
    assert isinstance(findings, tuple)
    results = tuple(
        _composite_dispatch(distribution, root, selection)
        for selection in _applicable(selected, frozenset({"drift-check"}))
    )
    return DriftReport(
        repo_root=_ROOT_IDENTITY,
        reconciliation_fingerprint=reconciliation_fingerprint(plan),
        actions=actions,
        findings=findings,
        results=results,
    )


def _plan(distribution: InstalledDistribution, root: Path) -> ReconciliationPlan:
    try:
        return plan_reconciliation(build_planner_request(root, distribution, frozenset()))
    except _CONTROL_PLANE_FAILURES as exc:
        raise _control_plane_error(
            exc, "reconciliation could not be planned for this repository"
        ) from exc


__all__ = [
    "PROVIDER_TIMEOUT_SECONDS",
    "DriftReport",
    "ProviderOperationResult",
    "ValidationReport",
    "drift_check",
    "invoke_read_provider",
    "validate_repo",
]
