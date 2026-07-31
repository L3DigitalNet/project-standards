"""Bounded, non-mutating provider services behind the facade (T4, §5.5, ADR 0025).

Three frozen operations live here: ``invoke_read_provider`` dispatches exactly
one declared provider, and ``validate_repo``/``drift_check`` compose it over the
consumer's *current* exact resolution.

Nothing in this module re-implements provider semantics. Identity qualification,
payload-resource closure, input/output schema validation, the declared-live-path
integrity check, and effect-typed result construction all stay inside
``invoke_provider`` (``control_plane/providers.py:732``), which the worker calls
through the same ``selected_command``/``invoke_selected_provider`` pair the CLI
uses. What this module adds is exactly the execution boundary ADR 0025 requires
and the dispatcher does not have — proven absent by the T4.0 characterization:

* a spawned worker process on the server's own interpreter, so a provider cannot
  block the protocol loop, take the server down with it, or write to the
  descriptor the stdio transport owns;
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
import os
import selectors
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import IO, Any, cast

from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.diagnostics import ControlFinding, ControlPlaneError
from project_standards.control_plane.distribution import InstalledDistribution, InstalledPayload
from project_standards.control_plane.executor import reconciliation_fingerprint
from project_standards.control_plane.locking import ControlPlaneBusyError
from project_standards.control_plane.planner import ReconciliationPlan, plan_reconciliation
from project_standards.control_plane.resolution import resolve_packages
from project_standards.mcp_services.consumer import (
    Finding,
    StableJson,
    map_finding,
    resolve_consumer_root,
    stable_json,
)
from project_standards.mcp_services.models import ServiceError, ServiceModel
from project_standards.mcp_services.provider_worker import (
    INPUT_AUTHORITY_FIELD,
    RESULT_LIMIT_BYTES,
    SEAM_AUTHORITY,
    safe_detail,
)
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.payload import ProviderDeclaration, ProviderEffect

# ADR 0025: "The provider timeout is 30 seconds per provider invocation." This is
# a module global rather than a default argument on purpose — the execution path
# reads it at call time, which is what makes the bound injectable and therefore
# provable in both directions.
PROVIDER_TIMEOUT_SECONDS: float = 30

# How long a worker gets to honour SIGTERM before SIGKILL. ADR 0025 fixes the
# sequence, not this interval; it only has to be long enough for a cooperative
# process to exit and short enough that an uncooperative one is not tolerated.
TERMINATION_GRACE_SECONDS = 1.0

# Slice length for waits that must also notice the worker leader exiting. One
# quiet slice after the leader is gone means a still-open pipe belongs to a
# descendant rather than to the invocation itself.
_POLL_SECONDS = 0.05

# Per-stream capture cap, then a cap on the composed diagnostic text. Both are
# applied with an explicit, quantified marker: DR-008 makes diagnostics bounded
# supplemental text, and ADR 0025 forbids silent truncation.
STREAM_LIMIT_BYTES = 8_192
DIAGNOSTIC_LIMIT_CHARS = 16_384

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
# the caller's, unchanged; the composites send the seam directive instead, and the
# worker builds the authoritative corpus on its own side of the pipe — the
# measured authoritative inputs (290 KB to 4.8 MB on a real consumer, 2026-07-30)
# are one to eighteen times the frozen `REQUEST_LIMIT_BYTES`, so they cannot cross
# it and the bound is not raised to let them.
_CALLER_AUTHORITY = "caller"

# Composite dispatch supplies no input of its own. The empty object is not a
# placeholder: it is exactly what a standard outside the seam's four families
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

# Started with `-c` rather than `-m`: the parent already imports the worker
# module (for its transport limit), so `-m` would re-execute it as `__main__`
# and emit a RuntimeWarning onto the very stderr this service captures as
# diagnostics.
_WORKER_BOOTSTRAP = (
    "from project_standards.mcp_services.provider_worker import main; raise SystemExit(main())"
)


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


@dataclass(slots=True)
class _Capture:
    """One bounded worker stream: what was kept and how much was discarded.

    Every stream is drained to EOF even after its limit is reached, because a
    worker blocked on a full pipe would defeat the very bound this enforces.
    """

    label: str
    limit: int
    kept: bytearray = field(default_factory=bytearray)
    dropped: int = 0

    def append(self, data: bytes) -> None:
        room = max(0, self.limit - len(self.kept))
        if room:
            self.kept.extend(data[:room])
        self.dropped += len(data) - min(room, len(data))

    def section(self) -> list[str]:
        if not self.kept and not self.dropped:
            return []
        sections = [f"{self.label}: {self.kept.decode('utf-8', errors='replace')}"]
        if self.dropped:
            sections.append(
                f"[project-standards: {self.dropped} bytes of worker {self.label} omitted "
                f"after the {self.limit}-byte capture limit]"
            )
        return sections


class _Timeout(Exception):
    """Internal signal that the configured bound elapsed."""


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


class _Transport:
    """One deadline-bound, non-blocking exchange with a worker process.

    Request bytes and all three inbound streams live in a single ``selectors``
    loop. That is not an optimization: a blocking ``write()`` on stdin can outlast
    the execution bound whenever a worker fills stderr before reading its request
    (T4.4 Codex GREEN review, finding 4), and reading the result first deadlocks
    the moment a provider fills the stdout pipe. Everything is therefore driven by
    readiness, and every wait is a slice of the remaining deadline.
    """

    def __init__(self, captures: dict[int, _Capture], stdin: IO[bytes]) -> None:
        self._captures = captures
        self._selector = selectors.DefaultSelector()
        self.open: set[int] = set()
        for descriptor in captures:
            os.set_blocking(descriptor, False)
            self._selector.register(descriptor, selectors.EVENT_READ)
            self.open.add(descriptor)
        # The stream object is kept, not just its number: closing the descriptor
        # is what gives the worker EOF on its request, and it must be closed
        # through the object subprocess owns so teardown cannot double-close it.
        self._stdin: IO[bytes] | None = stdin
        self._stdin_fd = stdin.fileno()
        os.set_blocking(self._stdin_fd, False)
        self._selector.register(self._stdin_fd, selectors.EVENT_WRITE)
        self._pending = b""

    def send(self, request: bytes) -> None:
        self._pending = request

    def run(
        self,
        deadline: float,
        *,
        until_closed: int | None = None,
        leader: subprocess.Popen[bytes] | None = None,
    ) -> bool:
        """Pump until the stop condition, returning False when the deadline expires.

        ``leader`` closes the second half of finding 3. A provider-forked
        descendant inherits every pipe, so the result descriptor can stay open
        long after the worker leader has written its frame and exited. Waiting on
        readiness alone would then burn the whole deadline on a process that is
        no longer producing anything, so whenever a leader is supplied the wait is
        sliced: once it has exited and one quiet slice passes, the exchange is
        over and teardown reaps the rest of the group.
        """
        while True:
            if until_closed is not None:
                if until_closed not in self.open and not self._pending:
                    return True
            elif not self.open and self._stdin is None:
                return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            window = remaining if leader is None else min(remaining, _POLL_SECONDS)
            events = self._selector.select(window)
            if events:
                for key, mask in events:
                    descriptor = int(key.fd)
                    if self._stdin is not None and descriptor == self._stdin_fd:
                        if mask & selectors.EVENT_WRITE:
                            self._write()
                        continue
                    self._read(descriptor)
                continue
            if leader is not None and until_closed is not None and leader.poll() is not None:
                return True
            if window >= remaining:
                return False

    def _write(self) -> None:
        if self._stdin is None:  # pragma: no cover - unregistered with the descriptor
            return
        try:
            written = os.write(self._stdin_fd, self._pending) if self._pending else 0
        except BlockingIOError:  # pragma: no cover - selector said writable
            return
        except OSError:
            # The worker is gone; there is nothing left to deliver.
            written = len(self._pending)
        self._pending = self._pending[written:]
        if not self._pending:
            self._close_stdin()

    def _read(self, descriptor: int) -> None:
        try:
            data = os.read(descriptor, 65_536)
        except BlockingIOError:  # pragma: no cover - selector said readable
            return
        except OSError:
            data = b""
        if data:
            self._captures[descriptor].append(data)
            return
        self._selector.unregister(descriptor)
        self.open.discard(descriptor)

    def _close_stdin(self) -> None:
        """Unregister *and* close: EOF on the request is what unblocks the worker."""
        stdin = self._stdin
        if stdin is None:
            return
        self._selector.unregister(self._stdin_fd)
        self._stdin = None
        if not stdin.closed:
            stdin.close()

    def close(self) -> None:
        self._close_stdin()
        for descriptor in tuple(self.open):
            self._selector.unregister(descriptor)
            self.open.discard(descriptor)
        self._selector.close()


def _worker_environment() -> dict[str, str]:
    """Give the worker the parent's exact import path, per ADR 0025."""
    environment = dict(os.environ)
    entries = [entry for entry in sys.path if entry]
    if entries:
        environment["PYTHONPATH"] = os.pathsep.join(entries)
    return environment


def _signal_group(process: subprocess.Popen[bytes], signal_number: int) -> None:
    """Signal the worker's whole process group, never just its leader.

    The worker is started with ``start_new_session=True``, so its pid is its
    session and group leader. Signalling only the leader lets a provider-created
    descendant survive holding the inherited pipes open (T4.4 Codex GREEN review,
    finding 3), so the group is the unit of termination on every path — including
    after the leader has already exited.
    """
    try:
        os.killpg(process.pid, signal_number)
    except ProcessLookupError, PermissionError, OSError:
        return


def _teardown(process: subprocess.Popen[bytes], transport: _Transport) -> None:
    """Release the worker group, draining throughout, on every completion path.

    Draining continues across the SIGTERM grace on purpose: a cooperative handler
    that writes more than a pipe capacity before exiting would otherwise block on
    a parent that had stopped reading, and be escalated to SIGKILL for the
    parent's own inaction (finding 9).
    """
    settled = transport.run(time.monotonic() + TERMINATION_GRACE_SECONDS)
    _signal_group(process, signal.SIGTERM)
    if not settled or process.poll() is None:
        transport.run(time.monotonic() + TERMINATION_GRACE_SECONDS)
    if process.poll() is None or transport.open:
        _signal_group(process, signal.SIGKILL)
        transport.run(time.monotonic() + TERMINATION_GRACE_SECONDS)
    # Reaping happens only after the last killpg: an unreaped pid cannot be
    # recycled, so the group identifier stayed unambiguous throughout.
    try:
        process.wait(timeout=TERMINATION_GRACE_SECONDS)
    except subprocess.TimeoutExpired:  # pragma: no cover - SIGKILL is not refusable
        process.kill()
        process.wait()
    transport.close()
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is not None and not stream.closed:
            stream.close()


def _frame_error(reason: str, selection: _Selection) -> ServiceError:
    return _error(
        "provider-frame-invalid",
        f"the bounded provider worker returned {reason}",
        _DISPATCH_REMEDIATION,
        standard_id=selection.standard_id,
        version=selection.version,
    )


def _validated_frame(raw: bytes, selection: _Selection) -> dict[str, Any]:
    """Validate one inbound IPC frame strictly before any of it is believed.

    The process that executes provider bytes also owns the response descriptor,
    so a payload that violates its declaration can write whatever it likes here.
    ADR 0025's trust model already grants those bytes far more than this on the
    authoritative in-process path, so the answer is not another sandbox
    (plan:339) — it is that the parent believes nothing it has not checked
    (T4.4 Codex GREEN review, finding 2, disposition ACCEPT-BOUNDED).
    """
    if len(raw) > RESULT_LIMIT_BYTES:
        raise _frame_error("a result above the transport limit", selection)
    try:
        decoded: object = json.loads(raw)
    except ValueError as exc:
        raise _frame_error("no readable result", selection) from exc
    if not isinstance(decoded, dict):
        raise _frame_error("a result that is not a JSON object", selection)
    frame = cast("dict[str, Any]", decoded)
    status = frame.get("status")
    if status not in {"ok", "error"}:
        raise _frame_error("a result with no recognized status", selection)
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


def _run_worker(
    request: bytes, timeout: float, selection: _Selection
) -> tuple[dict[str, Any], _Capture, _Capture]:
    """Spawn one bounded worker group and return its validated response.

    Every exit path — success, timeout, kill, crash, and parent-side cancellation
    — runs the same teardown, so no pipe, descriptor, or process in the worker's
    group survives this function (ADR 0025 confirmation clause).
    """
    stdout = _Capture("stdout", STREAM_LIMIT_BYTES)
    stderr = _Capture("stderr", STREAM_LIMIT_BYTES)
    # One byte of headroom so an oversized response is detected rather than
    # silently trimmed into something that still parses.
    result = _Capture("result", RESULT_LIMIT_BYTES + 1)
    result_read, result_write = os.pipe()
    process: subprocess.Popen[bytes] | None = None
    transport: _Transport | None = None
    try:
        try:
            process = subprocess.Popen(
                [sys.executable, "-c", _WORKER_BOOTSTRAP, str(result_write)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                pass_fds=(result_write,),
                close_fds=True,
                start_new_session=True,
                env=_worker_environment(),
            )
        except OSError as exc:
            raise _error(
                "provider-worker-unavailable",
                "the bounded provider worker could not be started",
                "verify the installed distribution and retry",
                standard_id=selection.standard_id,
                version=selection.version,
            ) from exc
        finally:
            os.close(result_write)
            result_write = -1

        assert process.stdin is not None
        assert process.stdout is not None
        assert process.stderr is not None
        deadline = time.monotonic() + timeout
        transport = _Transport(
            {
                result_read: result,
                process.stdout.fileno(): stdout,
                process.stderr.fileno(): stderr,
            },
            process.stdin,
        )
        transport.send(request)
        try:
            if not transport.run(deadline, until_closed=result_read, leader=process):
                raise _Timeout
        except _Timeout as exc:
            raise _error(
                "provider-timeout",
                f"the provider did not finish within the {timeout}-second execution bound "
                "and its worker group was terminated",
                _TIMEOUT_REMEDIATION,
                standard_id=selection.standard_id,
                version=selection.version,
            ) from exc
        except OSError as exc:
            raise _error(
                "provider-worker-failed",
                "the bounded provider worker ended before returning a result",
                _TIMEOUT_REMEDIATION,
                standard_id=selection.standard_id,
                version=selection.version,
            ) from exc
        except (KeyboardInterrupt, SystemExit) as exc:
            # Parent-side cancellation: a Ctrl-C, an interval timer, or a
            # shutdown signal delivered while the synchronous wait was in
            # progress. The plan requires the same cleanup as a timeout, reported
            # as a structured failure rather than a half-torn-down process. Only
            # these two carriers are converted — an ordinary exception here is a
            # defect in this module and must stay loud.
            raise _error(
                "provider-cancelled",
                "the provider invocation was cancelled and its worker group was terminated",
                _TIMEOUT_REMEDIATION,
                standard_id=selection.standard_id,
                version=selection.version,
            ) from exc
        return _validated_frame(bytes(result.kept), selection), stdout, stderr
    finally:
        if result_write != -1:  # pragma: no cover - only when Popen never ran
            os.close(result_write)
        if process is not None and transport is not None:
            _teardown(process, transport)
        elif process is not None:  # pragma: no cover - transport construction failed
            _signal_group(process, signal.SIGKILL)
            process.wait()
        os.close(result_read)


def _compose_diagnostics(notice: str | None, stdout: _Capture, stderr: _Capture) -> str:
    """Bound the worker's captured output, marking every omission explicitly."""
    sections: list[str] = []
    if notice:
        # The authoritative dispatcher destroys provider text and publishes only
        # this notice; dropping it would be a silent loss of the one fact it kept.
        sections.append(notice)
    sections.extend(stdout.section())
    sections.extend(stderr.section())
    composed = "\n".join(sections)
    if len(composed) > DIAGNOSTIC_LIMIT_CHARS:
        omitted = len(composed) - DIAGNOSTIC_LIMIT_CHARS
        composed = (
            composed[:DIAGNOSTIC_LIMIT_CHARS]
            + f"\n[project-standards: {omitted} further diagnostic characters omitted "
            f"after the {DIAGNOSTIC_LIMIT_CHARS}-character limit]"
        )
    return composed


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
    response, stdout, stderr = _run_worker(request, float(PROVIDER_TIMEOUT_SECONDS), selection)
    if response.get("status") != "ok":
        code = response.get("code")
        detail = response.get("detail")
        raise _error(
            code if isinstance(code, str) and code else "provider-invocation-failed",
            # Re-filtered here, not merely trusted: the worker already redacts its
            # own failure text, but a frame written by provider bytes has not been
            # through that filter (finding 2).
            safe_detail(
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
        diagnostics=_compose_diagnostics(response.get("output_notice"), stdout, stderr),
        output=stable_json(response.get("output")),
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
