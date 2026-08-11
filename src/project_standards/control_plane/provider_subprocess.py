"""Own bounded provider process transport for every control-plane caller.

The result channel is a third inherited descriptor appended to ``argv``. Standard
output and standard error are diagnostics only, so all three inbound streams and
the request pipe are pumped in one selector loop under one deadline. Every exit
path tears down the complete process group before returning or raising.
"""

from __future__ import annotations

import json
import os
import re
import selectors
import signal
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import IO, cast

type JsonValue = None | bool | int | float | str | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]

PROVIDER_TIMEOUT_SECONDS: float = 30
TERMINATION_GRACE_SECONDS = 1.0
STREAM_LIMIT_BYTES = 8_192
RESULT_LIMIT_BYTES = 262_144
DIAGNOSTIC_LIMIT_CHARS = 16_384

_POLL_SECONDS = 0.05
_TIMEOUT_REMEDIATION = (
    "re-run after the provider is fixed or its work is reduced, then inspect the "
    "repository with repo_inspect"
)
_PYTHON_WORKER_BOOTSTRAP = (
    "from project_standards.control_plane.provider_worker import main; raise SystemExit(main())"
)
_ABSOLUTE_PATH_PATTERN = re.compile(r"(?:^|[\s'\"(])/[\w.\-/]{4,}")
REDACTED_FAILURE_DETAIL = "the failure detail was withheld because it named a filesystem path"


class ProviderSubprocessError(RuntimeError):
    """Report a stable, content-safe failure of the provider process boundary."""

    def __init__(self, code: str, message: str, remediation: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.remediation = remediation


def safe_failure_detail(text: str, secrets: tuple[str, ...]) -> str:
    """Return child failure text only when it names no root or absolute path."""
    if any(secret and secret in text for secret in secrets):
        return REDACTED_FAILURE_DETAIL
    if _ABSOLUTE_PATH_PATTERN.search(text):
        return REDACTED_FAILURE_DETAIL
    return text


@dataclass(slots=True)
class CapturedStream:
    """Retain one bounded diagnostic stream while draining all of its bytes."""

    label: str
    limit: int
    _kept: bytearray = field(default_factory=bytearray)
    omitted: int = 0

    @property
    def content(self) -> bytes:
        """Return the retained prefix as immutable bytes."""
        return bytes(self._kept)

    def append(self, data: bytes) -> None:
        room = max(0, self.limit - len(self._kept))
        if room:
            self._kept.extend(data[:room])
        self.omitted += len(data) - min(room, len(data))

    def sections(self) -> list[str]:
        """Render retained bytes and an explicit omission marker when needed."""
        if not self._kept and not self.omitted:
            return []
        sections = [f"{self.label}: {self._kept.decode('utf-8', errors='replace')}"]
        if self.omitted:
            sections.append(
                f"[project-standards: {self.omitted} bytes of worker {self.label} omitted "
                f"after the {self.limit}-byte capture limit]"
            )
        return sections


@dataclass(frozen=True, slots=True)
class ProviderSubprocessOutcome:
    """Return one validated response frame and both bounded diagnostic streams."""

    frame: JsonObject
    stdout: CapturedStream
    stderr: CapturedStream
    returncode: int = 0


class _Timeout(Exception):
    """Signal that the one invocation deadline elapsed."""


class _Transport:
    """Pump request, result, stdout, and stderr without allowing pipe deadlock."""

    def __init__(self, captures: dict[int, CapturedStream], stdin: IO[bytes]) -> None:
        self._captures = captures
        self._selector = selectors.DefaultSelector()
        self.open: set[int] = set()
        for descriptor in captures:
            os.set_blocking(descriptor, False)
            self._selector.register(descriptor, selectors.EVENT_READ)
            self.open.add(descriptor)
        # Close through subprocess's stream object: closing only the integer fd
        # leaves its buffered owner alive and can double-close a recycled number.
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
        """Pump until the stop condition, returning false at the deadline.

        A provider descendant can inherit every pipe after its leader exits. The
        sliced wait notices that state promptly so teardown, not the invocation
        deadline, owns termination of the remaining process group.
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
        if self._stdin is None:  # pragma: no cover - descriptor is unregistered
            return
        try:
            written = os.write(self._stdin_fd, self._pending) if self._pending else 0
        except BlockingIOError:  # pragma: no cover - selector reported writable
            return
        except OSError:
            written = len(self._pending)
        self._pending = self._pending[written:]
        if not self._pending:
            self._close_stdin()

    def _read(self, descriptor: int) -> None:
        try:
            data = os.read(descriptor, 65_536)
        except BlockingIOError:  # pragma: no cover - selector reported readable
            return
        except OSError:
            data = b""
        if data:
            self._captures[descriptor].append(data)
            return
        self._selector.unregister(descriptor)
        self.open.discard(descriptor)

    def _close_stdin(self) -> None:
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


def python_worker_environment() -> dict[str, str]:
    """Return the caller environment plus the exact active Python import path."""
    environment = dict(os.environ)
    entries = [entry for entry in sys.path if entry]
    if entries:
        environment["PYTHONPATH"] = os.pathsep.join(entries)
    return environment


def python_worker_argv() -> tuple[str, ...]:
    """Return the fixed interpreter/bootstrap argv for the Python provider child."""
    return (sys.executable, "-c", _PYTHON_WORKER_BOOTSTRAP)


def encode_provider_request(value: JsonObject) -> bytes:
    """Serialize one strict provider request into deterministic UTF-8 JSON."""
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ProviderSubprocessError(
            "provider-input-invalid",
            "typed provider input is not JSON-safe",
            "pass typed provider input containing only JSON-safe values with string keys",
        ) from exc


def compose_provider_diagnostics(
    notice: str | None,
    stdout: CapturedStream,
    stderr: CapturedStream,
) -> str:
    """Compose bounded diagnostics without silently dropping any retained stream."""
    sections: list[str] = []
    if notice:
        sections.append(notice)
    sections.extend(stdout.sections())
    sections.extend(stderr.sections())
    composed = "\n".join(sections)
    if len(composed) <= DIAGNOSTIC_LIMIT_CHARS:
        return composed
    omitted = len(composed) - DIAGNOSTIC_LIMIT_CHARS
    return (
        composed[:DIAGNOSTIC_LIMIT_CHARS]
        + f"\n[project-standards: {omitted} further diagnostic characters omitted "
        f"after the {DIAGNOSTIC_LIMIT_CHARS}-character limit]"
    )


def _signal_group(process: subprocess.Popen[bytes], signal_number: int) -> None:
    """Signal the isolated process group, including provider-created descendants."""
    try:
        os.killpg(process.pid, signal_number)
    except ProcessLookupError, PermissionError, OSError:
        return


def _teardown(process: subprocess.Popen[bytes], transport: _Transport) -> None:
    """Drain, terminate, reap, and close one complete provider process group."""
    settled = transport.run(time.monotonic() + TERMINATION_GRACE_SECONDS)
    _signal_group(process, signal.SIGTERM)
    if not settled or process.poll() is None:
        transport.run(time.monotonic() + TERMINATION_GRACE_SECONDS)
    if process.poll() is None or transport.open:
        _signal_group(process, signal.SIGKILL)
        transport.run(time.monotonic() + TERMINATION_GRACE_SECONDS)
    # Reap only after the last group signal. Until wait returns, the leader pid
    # cannot be recycled into an unrelated process-group identifier.
    try:
        process.wait(timeout=TERMINATION_GRACE_SECONDS)
    except subprocess.TimeoutExpired:  # pragma: no cover - SIGKILL is not refusable
        process.kill()
        process.wait()
    transport.close()
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is not None and not stream.closed:
            stream.close()


def _validated_frame(raw: bytes, *, validate_status: bool) -> JsonObject:
    if len(raw) > RESULT_LIMIT_BYTES:
        raise ProviderSubprocessError(
            "provider-frame-invalid",
            "the bounded provider worker returned a result above the transport limit",
            _TIMEOUT_REMEDIATION,
        )
    try:
        text = raw.decode("utf-8")

        def closed_object(pairs: list[tuple[str, JsonValue]]) -> JsonObject:
            result: JsonObject = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate JSON object field")
                result[key] = value
            return result

        decoded = cast(object, json.loads(text, object_pairs_hook=closed_object))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ProviderSubprocessError(
            "provider-frame-invalid",
            "the bounded provider worker returned no readable result",
            _TIMEOUT_REMEDIATION,
        ) from exc
    if not isinstance(decoded, dict):
        raise ProviderSubprocessError(
            "provider-frame-invalid",
            "the bounded provider worker returned a result that is not a JSON object",
            _TIMEOUT_REMEDIATION,
        )
    frame = cast(JsonObject, decoded)
    status = frame.get("status")
    if validate_status and (not isinstance(status, str) or status not in {"ok", "error"}):
        raise ProviderSubprocessError(
            "provider-frame-invalid",
            "the bounded provider worker returned a result with no recognized status",
            _TIMEOUT_REMEDIATION,
        )
    return frame


def run_provider_subprocess(
    argv: Sequence[str],
    request: bytes,
    *,
    timeout: float,
    environment: Mapping[str, str],
    validate_status: bool = True,
) -> ProviderSubprocessOutcome:
    """Run one provider group and return its bounded frame and diagnostics.

    ``argv`` omits the result descriptor; this function appends it, which makes
    the descriptor ``argv[1]`` for a native command and the final bootstrap
    argument for the Python worker. No caller owns signal, pipe, or reap logic.
    """
    if not argv:
        raise ValueError("provider argv must not be empty")
    if timeout <= 0:
        raise ValueError("provider timeout must be positive")

    stdout = CapturedStream("stdout", STREAM_LIMIT_BYTES)
    stderr = CapturedStream("stderr", STREAM_LIMIT_BYTES)
    result = CapturedStream("result", RESULT_LIMIT_BYTES + 1)
    result_read, result_write = os.pipe()
    process: subprocess.Popen[bytes] | None = None
    transport: _Transport | None = None
    raw_result: bytes | None = None
    try:
        try:
            process = subprocess.Popen(
                [*argv, str(result_write)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                pass_fds=(result_write,),
                close_fds=True,
                start_new_session=True,
                env=dict(environment),
            )
        except OSError as exc:
            raise ProviderSubprocessError(
                "provider-worker-unavailable",
                "the bounded provider worker could not be started",
                "verify the installed distribution and retry",
            ) from exc
        finally:
            os.close(result_write)
            result_write = -1

        assert process.stdin is not None
        assert process.stdout is not None
        assert process.stderr is not None
        transport = _Transport(
            {
                result_read: result,
                process.stdout.fileno(): stdout,
                process.stderr.fileno(): stderr,
            },
            process.stdin,
        )
        transport.send(request)
        deadline = time.monotonic() + timeout
        try:
            if not transport.run(deadline, until_closed=result_read, leader=process):
                raise _Timeout
        except _Timeout as exc:
            raise ProviderSubprocessError(
                "provider-timeout",
                f"the provider did not finish within the {timeout}-second execution bound "
                "and its worker group was terminated",
                _TIMEOUT_REMEDIATION,
            ) from exc
        except OSError as exc:
            raise ProviderSubprocessError(
                "provider-worker-failed",
                "the bounded provider worker ended before returning a result",
                _TIMEOUT_REMEDIATION,
            ) from exc
        except (KeyboardInterrupt, SystemExit) as exc:
            # Cancellation must use the same teardown as timeout. Converting only
            # these carriers keeps ordinary implementation defects loud.
            raise ProviderSubprocessError(
                "provider-cancelled",
                "the provider invocation was cancelled and its worker group was terminated",
                _TIMEOUT_REMEDIATION,
            ) from exc
        raw_result = result.content
    finally:
        if result_write != -1:  # pragma: no cover - only when Popen never ran
            os.close(result_write)
        if process is not None and transport is not None:
            _teardown(process, transport)
        elif process is not None:  # pragma: no cover - transport construction failed
            _signal_group(process, signal.SIGKILL)
            process.wait()
        os.close(result_read)
    assert process is not None
    assert raw_result is not None
    if not validate_status and process.returncode != 0:
        raise ProviderSubprocessError(
            "provider-command-failed",
            "the command provider exited with a nonzero status",
            _TIMEOUT_REMEDIATION,
        )
    return ProviderSubprocessOutcome(
        _validated_frame(raw_result, validate_status=validate_status),
        stdout,
        stderr,
        process.returncode,
    )
