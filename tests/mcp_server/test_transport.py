"""Stdio transport, capability truthfulness, and launch boundary of the adapter (T5).

Covers TC-T5-001 (protocol-clean stdout across initialize and error paths),
TC-T5-002 (advertised capabilities equal the registration set and imply neither
writes nor a remote transport), TC-T5-004 (``listChanged`` only with an
implemented notification path), TC-T5-005 (``project-standards mcp`` launches
the server), and TC-T5-006 (every log and diagnostic on stderr).

Three authorities constrain every expectation here and none of them may be
re-derived by the adapter under test:

*The protocol* — revision ``2026-07-28`` is final and keeps the stdio framing
unchanged: newline-delimited JSON-RPC, "The server MUST NOT write JSON-RPC
requests to stdout", logs on stderr. That revision removed the ``initialize``
handshake in favour of a per-request ``_meta`` envelope and made
``server/discover`` mandatory, while every earlier revision still negotiates
through ``initialize``. Both eras are exercised because the installed Codex CLI
speaks ``2025-06-18`` only, so a modern-only server fails against a released
client (evidence matrix, "Dual-era serving is required").

*The SDK* — ``mcp==2.0.0`` serves both eras from one server object (ADR 0025),
but it locks a connection's era at its opening request: a classic connection
refuses a request carrying the modern envelope and a modern connection refuses
``initialize``. Every probe below therefore uses one process per era (T5.2 Codex
review F1). The revision strings are read out of ``mcp_types.version`` rather
than spelled here, so a future SDK that adds a revision widens this suite
instead of silently escaping it.

*ADR 0026* (``adr-0026-project-standards-mcp-local-read-only-transport.md``) —
the frozen adapter configuration: server name ``project-standards``, one
optional launch-time root-boundary CLI option, capabilities that declare only
what is implemented with ``listChanged`` false and ``subscribe`` absent, a
static instructions string, and stdout reserved for protocol messages.

**Forward compatibility is a design constraint here, not a nicety.** T6, T7, and
T8 register resources, prompts, and tools while rerunning this suite, so no
assertion may freeze a feature list to empty (review F2). What is asserted
instead is the equivalence — a declared capability must have a reachable
listing, an undeclared one must not — plus the negatives ADR 0026 freezes
permanently: no write or remote surface, no ``subscribe``, ``listChanged``
false, and every advertised tool drawn from the frozen six-tool v1 registry.
T5's emptiness follows from the equivalence rather than being pinned by it.

``test_transport_harness_speaks_the_protocol_against_a_bare_sdk_server`` and
``test_modern_list_result_contract_is_satisfiable_by_the_sdk`` are the RED
controls required by T5.2: they drive this module's framing, deadline,
transcript, and capability machinery against bare SDK servers that already
exist, so a failure anywhere else in the file is provably the absent adapter
rather than an invalid protocol fixture. Those control scripts are *test
oracles*, not sketches of the GREEN design.

Every subprocess interaction in this module is deadline-bound — reads and writes
alike, on one monotonic clock — and every server is killed by process group on
the way out, so no fixture here can hang the suite.
"""

from __future__ import annotations

import ast
import contextlib
import dataclasses
import importlib.util
import json
import os
import re
import selectors
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from types import ModuleType, TracebackType
from typing import Any, cast

import pytest
from mcp_types import (
    CLIENT_CAPABILITIES_META_KEY,
    CLIENT_INFO_META_KEY,
    METHOD_NOT_FOUND,
    PROTOCOL_VERSION_META_KEY,
)
from mcp_types.version import HANDSHAKE_PROTOCOL_VERSIONS, MODERN_PROTOCOL_VERSIONS

import project_standards
from project_standards._version import package_version

# The exact revision the installed Codex CLI 0.146.0 hardcodes. It is spelled
# out because it is a *client* fact frozen by the evidence matrix, not an SDK
# value; the assertion below keeps it honest against the SDK's own register.
# The value survives the 0.145.0 -> 0.146.0 refresh: 0.146.0 registers the
# `mcp_2026_07_28` feature disabled by default, so the released client still
# negotiates 2025-06-18 only.
CODEX_CLIENT_REVISION = "2025-06-18"

# ADR 0026, frozen adapter configuration.
FROZEN_SERVER_NAME = "project-standards"

# ADR 0026's complete v1 tool registry. Every entry is read-only by
# construction, which is what makes "advertised tools are a subset of this set"
# a permanent FR-018 write-omission proof rather than a T5-only emptiness pin.
FROZEN_V1_TOOLS = frozenset(
    {
        "standards_list",
        "standard_read",
        "repo_inspect",
        "reconcile_preview",
        "validate_repo",
        "drift_check",
    }
)

# Wall-clock bounds. Every read, write, and exit is bounded, so a server that
# never answers fails the test instead of stalling the suite.
FRAME_DEADLINE = 15.0
WRITE_DEADLINE = 15.0
EXIT_DEADLINE = 15.0
QUIET_WINDOW = 1.0

_PACKAGE_FILE = project_standards.__file__
assert _PACKAGE_FILE is not None, "project_standards must be importable from a real file"
# The importable root of the *same* distribution this test process resolved, so
# a subprocess server is never served by a different build than the assertions.
RUNTIME_ROOT = Path(_PACKAGE_FILE).resolve().parent.parent

ADAPTER_PACKAGE = "project_standards.mcp_server"

# Launch through the unified CLI, which ADR 0025 requires to work in the
# standard install rather than behind an extra, and which IR-001 makes the
# documented launch surface. The adapter entry point is deliberately *not*
# named here: no binding document freezes its callable (review F3).
CLI_LAUNCH = """
from project_standards.cli import main

raise SystemExit(main(["mcp"]))
"""


def cli_launch_with(arguments: Sequence[str]) -> str:
    return (
        "from project_standards.cli import main\n\n"
        f"raise SystemExit(main({['mcp', *arguments]!r}))\n"
    )


# RED control only. A bare low-level SDK server with an empty registry, used to
# prove the transcript machinery in this module is correct before it is pointed
# at the absent adapter. It is not a template for T5.3.
BARE_SDK_CONTROL = """
import anyio
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

server = Server("project-standards", version="0", instructions="control")


async def _serve() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


anyio.run(_serve)
"""

# Second RED control: one registered (empty) resource listing, so the *successful*
# modern-list branch of the capability helper is exercised against SDK-owned
# output rather than only against the METHOD_NOT_FOUND branch (review F11).
BARE_SDK_CONTROL_WITH_LIST = """
import anyio
import mcp_types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server


async def _list_resources(ctx, params):
    return types.ListResourcesResult(resources=[])


server = Server(
    "project-standards", version="0", instructions="control", on_list_resources=_list_resources
)


async def _serve() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


anyio.run(_serve)
"""

# Capability key -> list method. The result key equals the capability key for all
# three feature families in every revision the SDK serves.
FEATURE_FAMILIES: dict[str, str] = {
    "tools": "tools/list",
    "resources": "resources/list",
    "prompts": "prompts/list",
}

# ADR 0026: "No capability is declared for sampling, roots, or logging." No
# completion handler exists either, so declaring completions would be a lie.
FORBIDDEN_CAPABILITIES = ("logging", "sampling", "roots", "completions")

# SEP-2549/SEP-2322: every 2026-07-28 list result carries these.
MODERN_RESULT_FIELDS = ("resultType", "ttlMs", "cacheScope")

# NFR-008: no Streamable HTTP entry point in v1. Matched as module *paths* so a
# plain `from mcp.server.streamable_http import ...` cannot evade an alias list
# (review F10). The ASGI/HTTP roots are the stack such an entry point would need.
REMOTE_IMPORT_ROOTS = ("starlette", "sse_starlette", "uvicorn", "httpx", "httpx2")
REMOTE_PATH_TOKENS = ("sse", "streamable_http", "http", "auth")
REMOTE_SDK_ATTRIBUTES = (
    "run_sse_async",
    "run_streamable_http_async",
    "sse_app",
    "streamable_http_app",
    "streamable_http_manager",
    "StreamableHTTPSessionManager",
)
REMOTE_TRANSPORT_LITERALS = ("sse", "streamable-http")
REMOTE_LAUNCHER_PATTERN = re.compile(r"^(run|serve|start)_.*(http|sse|remote|stream)")
REMOTE_CLI_OPTION_TOKENS = ("http", "sse", "host", "port", "remote", "bind", "listen")


def require_adapter_module(name: str) -> ModuleType:
    """Import one planned adapter module, or fail as an explicit RED assertion.

    The plan's RED contract requires a missing planned module to surface as a
    test assertion rather than a collection error, so no test module in this
    tree may import ``project_standards.mcp_server`` at module scope.
    """
    dotted = ADAPTER_PACKAGE if not name else f"{ADAPTER_PACKAGE}.{name}"
    try:
        spec = importlib.util.find_spec(dotted)
    except ModuleNotFoundError:
        spec = None
    assert spec is not None, (
        f"planned module {dotted} is absent; the T5 stdio adapter does not exist yet"
    )
    return importlib.import_module(dotted)


def require_attribute(owner: object, name: str, label: str) -> Any:
    """Return one planned attribute, or fail as an explicit RED assertion."""
    assert hasattr(owner, name), (
        f"planned {label} {name} is absent; the T5 stdio adapter does not exist yet"
    )
    return getattr(owner, name)


def require_mcp_subcommand() -> str:
    """Return `project-standards mcp --help` output, or fail as a RED assertion."""
    result = run_cli(["mcp", "--help"])
    assert result.returncode == 0, (
        f"`project-standards mcp` is not a CLI subcommand yet:\n{result.stderr or result.stdout}"
    )
    return result.stdout


def modern_meta(version: str) -> dict[str, Any]:
    """Build the 2026-07-28 per-request envelope the classifier requires."""
    return {
        PROTOCOL_VERSION_META_KEY: version,
        CLIENT_CAPABILITIES_META_KEY: {},
        CLIENT_INFO_META_KEY: {"name": "t5-red-probe", "version": "0"},
    }


class ServerProcess:
    """A deadline-bound stdio server subprocess with a JSON-RPC line transcript.

    Both child streams are drained by one non-blocking ``selectors`` loop and
    stdin is written through the same loop on the same monotonic clock: a server
    that fills its stderr pipe while the test waits on stdout would deadlock,
    and so would a large frame written into a full stdin pipe before any read
    deadline had started (review F13). That is the same failure mode T4 hit on
    the provider worker. The child gets its own session so the whole process
    group can be killed even if it spawns descendants.
    """

    def __init__(self, script: str, *, runtime_root: Path = RUNTIME_ROOT, label: str) -> None:
        self._script = script
        self._runtime_root = runtime_root
        self._label = label
        self._process: subprocess.Popen[bytes] | None = None
        self._selector = selectors.DefaultSelector()
        self._pending = bytearray()
        self._next_id = 0
        self.stdout_bytes = bytearray()
        self.stderr_bytes = bytearray()
        self.sent_ids: list[int] = []

    def __enter__(self) -> ServerProcess:
        environment = {
            **os.environ,
            "PYTHONPATH": str(self._runtime_root),
            "PYTHONUNBUFFERED": "1",
            "NO_COLOR": "1",
        }
        process = subprocess.Popen(
            [sys.executable, "-c", self._script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            start_new_session=True,
        )
        assert process.stdout is not None
        assert process.stderr is not None
        assert process.stdin is not None
        self._process = process
        os.set_blocking(process.stdin.fileno(), False)
        self._selector.register(process.stdout, selectors.EVENT_READ, "stdout")
        self._selector.register(process.stderr, selectors.EVENT_READ, "stderr")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    # -- process control -------------------------------------------------

    def _require_process(self) -> subprocess.Popen[bytes]:
        assert self._process is not None, "the server process was never started"
        return self._process

    def close(self) -> None:
        """Kill the server's process group and release every pipe."""
        process = self._process
        self._selector.close()
        if process is None:
            return
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None and not stream.closed:
                with contextlib.suppress(OSError, BlockingIOError):
                    stream.close()
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except OSError, ProcessLookupError:
                process.kill()
        try:
            process.wait(timeout=EXIT_DEADLINE)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive
            process.kill()
            process.wait(timeout=EXIT_DEADLINE)
        self._process = None

    # -- transport -------------------------------------------------------

    def _pump_once(self, timeout: float) -> None:
        if not self._selector.get_map():
            return
        for key, _ in self._selector.select(timeout=timeout):
            try:
                chunk = os.read(key.fd, 65536)
            except OSError:  # pragma: no cover - defensive
                chunk = b""
            if not chunk:
                self._selector.unregister(key.fileobj)
                continue
            if key.data == "stdout":
                self.stdout_bytes.extend(chunk)
                self._pending.extend(chunk)
            else:
                self.stderr_bytes.extend(chunk)

    def diagnosis(self, reason: str) -> str:
        process = self._process
        status = "already reaped" if process is None else f"exit={process.poll()}"
        stderr_tail = bytes(self.stderr_bytes[-4000:]).decode("utf-8", "replace")
        stdout_tail = bytes(self.stdout_bytes[-1000:]).decode("utf-8", "replace")
        return (
            f"[{self._label}] {reason} ({status})\n"
            f"--- server stderr tail ---\n{stderr_tail}\n"
            f"--- server stdout tail ---\n{stdout_tail}"
        )

    def send_raw(self, payload: bytes, *, timeout: float = WRITE_DEADLINE) -> None:
        """Write to the server's stdin without ever blocking past the deadline.

        The descriptor is non-blocking, so a full pipe surfaces as a short write
        or ``BlockingIOError`` and is retried while the child's own output keeps
        draining. That is what stops a large outbound frame from deadlocking
        against a server that is busy writing — the read deadline cannot help,
        because it has not started yet (review F13).
        """
        process = self._require_process()
        stdin = process.stdin
        assert stdin is not None
        deadline = time.monotonic() + timeout
        view = memoryview(payload)
        while view:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AssertionError(
                    self.diagnosis(f"stdin write did not complete within {timeout:.1f}s")
                )
            try:
                written = os.write(stdin.fileno(), view)
            except BlockingIOError:
                written = 0
            except (BrokenPipeError, ValueError, OSError) as exc:
                # Drain whatever the server managed to say before it went away,
                # so the failure names the real cause, not the broken pipe.
                self.drain(2.0)
                raise AssertionError(
                    self.diagnosis(f"could not write to the server: {exc}")
                ) from exc
            if written:
                view = view[written:]
            if view:
                # Keep the child's own pipes moving while its stdin is full.
                self._pump_once(min(remaining, 0.05))

    def send(self, message: Mapping[str, Any]) -> None:
        self.send_raw((json.dumps(message) + "\n").encode("utf-8"))

    def notify(self, method: str, params: Mapping[str, Any] | None = None) -> None:
        message: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        self.send(message)

    def request(self, method: str, params: Mapping[str, Any] | None = None) -> int:
        self._next_id += 1
        identifier = self._next_id
        self.sent_ids.append(identifier)
        message: dict[str, Any] = {"jsonrpc": "2.0", "id": identifier, "method": method}
        if params is not None:
            message["params"] = params
        self.send(message)
        return identifier

    def read_frame(self, timeout: float = FRAME_DEADLINE) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while b"\n" not in self._pending:
            if not self._selector.get_map():
                raise AssertionError(
                    self.diagnosis("the server closed stdout without writing a protocol frame")
                )
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AssertionError(
                    self.diagnosis(f"no protocol frame arrived within {timeout:.1f}s")
                )
            self._pump_once(min(remaining, 0.25))
        line, _, rest = bytes(self._pending).partition(b"\n")
        self._pending[:] = rest
        try:
            frame = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AssertionError(
                self.diagnosis(f"stdout carried a non-JSON line: {line!r}")
            ) from exc
        assert isinstance(frame, dict), self.diagnosis(
            f"stdout carried a non-object frame: {line!r}"
        )
        return cast("dict[str, Any]", frame)

    def call(
        self,
        method: str,
        params: Mapping[str, Any] | None = None,
        *,
        timeout: float = FRAME_DEADLINE,
    ) -> dict[str, Any]:
        identifier = self.request(method, params)
        frame = self.read_frame(timeout)
        assert frame.get("id") == identifier, self.diagnosis(
            f"expected a response to id {identifier}, got {frame!r}"
        )
        assert frame.get("jsonrpc") == "2.0", self.diagnosis(
            f"frame is not JSON-RPC 2.0: {frame!r}"
        )
        return frame

    def drain(self, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        while self._selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            self._pump_once(min(remaining, 0.25))

    def finish(self, timeout: float = EXIT_DEADLINE) -> int:
        """Close stdin, drain both streams, and return the server's exit code."""
        process = self._require_process()
        if process.stdin is not None and not process.stdin.closed:
            with contextlib.suppress(OSError, BlockingIOError):
                process.stdin.close()
        self.drain(timeout)
        try:
            return process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise AssertionError(
                self.diagnosis(f"the server did not exit within {timeout:.1f}s")
            ) from exc

    # -- protocol helpers ------------------------------------------------

    def handshake(self, version: str) -> dict[str, Any]:
        """Run the classic initialize handshake and return its result object."""
        frame = self.call(
            "initialize",
            {
                "protocolVersion": version,
                "capabilities": {},
                "clientInfo": {"name": "t5-red-probe", "version": "0"},
            },
        )
        result = expect_result(self, frame)
        self.notify("notifications/initialized", {})
        return result

    def discover(self, version: str) -> dict[str, Any]:
        """Run the mandatory 2026-07-28 discovery request and return its result."""
        frame = self.call("server/discover", {"_meta": modern_meta(version)})
        return expect_result(self, frame)


def expect_result(server: ServerProcess, frame: Mapping[str, Any]) -> dict[str, Any]:
    assert "error" not in frame, server.diagnosis(f"expected a result, got an error: {frame!r}")
    result = frame.get("result")
    assert isinstance(result, dict), server.diagnosis(f"result is not an object: {frame!r}")
    return cast("dict[str, Any]", result)


def expect_error(server: ServerProcess, frame: Mapping[str, Any]) -> dict[str, Any]:
    """Assert one structured JSON-RPC error envelope (NFR-004)."""
    raw = frame.get("error")
    assert isinstance(raw, dict), server.diagnosis(f"expected an error, got: {frame!r}")
    error = cast("dict[str, Any]", raw)
    assert isinstance(error.get("code"), int), server.diagnosis(
        f"error code is not an int: {error!r}"
    )
    message = error.get("message")
    assert isinstance(message, str) and message, server.diagnosis(
        f"error message is empty: {error!r}"
    )
    return error


def as_object(value: object, label: str) -> dict[str, Any]:
    """Narrow one decoded JSON value to an object, or fail with a readable label."""
    assert isinstance(value, dict), f"{label} is not a JSON object: {value!r}"
    return cast("dict[str, Any]", value)


def assert_stdout_is_protocol_only(server: ServerProcess) -> list[dict[str, Any]]:
    """NFR-003/IR-006: every stdout byte belongs to a JSON-RPC response frame.

    Checked over the *whole* session transcript rather than per read, so a stray
    banner, warning, or traceback interleaved anywhere on stdout fails even when
    the individual responses parsed.
    """
    raw = bytes(server.stdout_bytes)
    assert raw == b"" or raw.endswith(b"\n"), server.diagnosis(
        "stdout ended with an unterminated line, so it carried more than framed messages"
    )
    frames: list[dict[str, Any]] = []
    for index, line in enumerate(raw.split(b"\n")):
        if not line:
            continue
        try:
            decoded = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AssertionError(
                server.diagnosis(f"stdout line {index} is not JSON-RPC: {line!r}")
            ) from exc
        assert isinstance(decoded, dict), server.diagnosis(f"stdout line {index} is not an object")
        frame = cast("dict[str, Any]", decoded)
        assert frame.get("jsonrpc") == "2.0", server.diagnosis(
            f"stdout line {index} is not a JSON-RPC 2.0 message: {frame!r}"
        )
        assert "result" in frame or "error" in frame, server.diagnosis(
            f"stdout line {index} is not a response: {frame!r}"
        )
        # A null id is legal on exactly one class of frame: the JSON-RPC error
        # for a message the server could not attribute to a request. Anything
        # else answering an id the client never sent is a protocol fault.
        assert frame.get("id") in server.sent_ids or ("id" in frame and "error" in frame), (
            server.diagnosis(f"stdout line {index} answers an id the client never sent: {frame!r}")
        )
        frames.append(frame)
    return frames


def answered_ids(frames: Sequence[Mapping[str, Any]]) -> list[Any]:
    """The request ids the transcript actually answered, in wire order."""
    return [frame["id"] for frame in frames if frame.get("id") is not None]


def declared_capabilities(result: Mapping[str, Any]) -> dict[str, Any]:
    capabilities = result.get("capabilities")
    assert isinstance(capabilities, dict), f"result carried no capability object: {result!r}"
    return cast("dict[str, Any]", capabilities)


def assert_modern_result_contract(server: ServerProcess, result: Mapping[str, Any]) -> None:
    """SEP-2322/SEP-2549: every successful 2026-07-28 result carries these fields.

    They are protocol-owned envelope metadata, so an adapter that hand-assembled
    a listing outside the SDK would drop them; asserting them is how the
    evidence matrix's "result envelopes are protocol-owned and must be produced
    by the SDK, not hand-assembled" becomes testable.
    """
    missing = [field for field in MODERN_RESULT_FIELDS if field not in result]
    assert not missing, server.diagnosis(
        f"a 2026-07-28 result is missing required envelope fields {missing}: {result!r}"
    )


def assert_capabilities_match_reachable_registrations(
    server: ServerProcess, capabilities: Mapping[str, Any], *, envelope: Mapping[str, Any] | None
) -> dict[str, list[Any]]:
    """FR-025/IR-008/DR-007: no declaration without a serveable registration.

    Both directions are checked because both are lies: an undeclared family
    whose listing still answers hides a registration, and a declared family
    whose listing is unreachable advertises a feature the server cannot serve.

    Deliberately *not* asserted: that any list is empty. T6/T7/T8 register real
    resources, prompts, and tools while rerunning this suite, and the contents
    of those registries belong to their owning task's tests (review F2). At T5
    nothing is registered, so the equivalence yields empty listings on its own.

    Returns the reachable items per family so callers can apply the permanent
    ADR 0026 negatives to them.
    """
    modern = envelope is not None
    reachable: dict[str, list[Any]] = {}
    for family, method in FEATURE_FAMILIES.items():
        params: dict[str, Any] = dict(envelope) if envelope is not None else {}
        frame = server.call(method, params)
        if family in capabilities and capabilities[family] is not None:
            result = expect_result(server, frame)
            items = result.get(family)
            assert isinstance(items, list), server.diagnosis(
                f"{method} returned no {family} array: {result!r}"
            )
            if modern:
                assert_modern_result_contract(server, result)
            reachable[family] = cast("list[Any]", items)
        else:
            error = expect_error(server, frame)
            assert error["code"] == METHOD_NOT_FOUND, server.diagnosis(
                f"{family} is undeclared, so {method} must not be served: {error!r}"
            )

    # Resource templates ride under the resources capability rather than
    # declaring one of their own, so a registered template would never appear in
    # the families loop above; its reachability is tied to the same capability.
    template_frame = server.call(
        "resources/templates/list", dict(envelope) if envelope is not None else {}
    )
    if "error" in template_frame:
        assert expect_error(server, template_frame)["code"] == METHOD_NOT_FOUND, server.diagnosis(
            f"unexpected failure listing resource templates: {template_frame!r}"
        )
    else:
        template_result = expect_result(server, template_frame)
        assert isinstance(template_result.get("resourceTemplates"), list), server.diagnosis(
            f"resources/templates/list returned no array: {template_result!r}"
        )
        assert capabilities.get("resources") is not None, server.diagnosis(
            "resource templates are served without a declared resources capability"
        )
        if modern:
            assert_modern_result_contract(server, template_result)

    for forbidden in FORBIDDEN_CAPABILITIES:
        assert capabilities.get(forbidden) is None, (
            f"ADR 0026 declares no {forbidden} capability, but the server advertised "
            f"{capabilities[forbidden]!r}"
        )
    for open_ended in ("experimental", "extensions"):
        value = capabilities.get(open_ended)
        assert value in (None, {}), (
            f"{open_ended} must stay empty while nothing is registered, got {value!r}"
        )
    return reachable


def advertised_tool_names(reachable: Mapping[str, list[Any]]) -> set[Any]:
    return {
        as_object(tool, "a tools/list entry").get("name") for tool in reachable.get("tools", [])
    }


def assert_no_write_surface(server: ServerProcess, reachable: Mapping[str, list[Any]]) -> None:
    """FR-018/ADR 0026: every reachable tool is drawn from the read-only v1 six.

    Written as a subset rule rather than as "no tools" so it keeps proving the
    write omission after T8 registers the real registry: all six frozen tools
    are read-only, so a subset of them cannot contain a mutating tool. At T5 the
    subset is empty and the same assertion holds.
    """
    unknown = {name for name in advertised_tool_names(reachable) if name not in FROZEN_V1_TOOLS}
    assert not unknown, server.diagnosis(
        f"tools outside ADR 0026's frozen read-only v1 registry are advertised: {sorted(unknown)}"
    )


def assert_no_list_change_promises(capabilities: Mapping[str, Any]) -> None:
    """DR-007/ADR 0026: ``listChanged`` false and ``subscribe`` absent, always.

    ADR 0026 makes the registration sets static for the process lifetime, so
    this is a permanent negative rather than a T5-phase one: there is never
    anything to notify, in any era, at any task boundary.
    """
    for family in FEATURE_FAMILIES:
        raw = capabilities.get(family)
        if raw is None:
            continue
        declared = as_object(raw, f"the {family} capability")
        assert not declared.get("listChanged"), (
            f"{family} advertises listChanged with no implemented notification path: {declared!r}"
        )
        assert not declared.get("subscribe"), (
            f"{family} advertises subscribe, which ADR 0026 forbids in v1: {declared!r}"
        )


def assert_instructions_are_truthful(
    server: ServerProcess, result: Mapping[str, Any], reachable: Mapping[str, list[Any]]
) -> str:
    """ADR 0026 (2026-07-29 phase amendment): static, era-stable, and truthful.

    The frozen six-tool text becomes binding at the task that completes the
    registry it describes; until then the string must not name a tool, prompt,
    or URI scheme that is not registered. ``None`` is not acceptable at any
    phase — the record requires an instructions string and Codex CLI documents
    server instructions as a real client-visible feature.
    """
    instructions = result.get("instructions")
    assert isinstance(instructions, str) and instructions.strip(), server.diagnosis(
        f"the server must serve a non-empty instructions string, got {instructions!r}"
    )
    advertised = advertised_tool_names(reachable)
    claimed = {
        name
        for name in FROZEN_V1_TOOLS
        if re.search(rf"\b{re.escape(name)}\b", instructions) and name not in advertised
    }
    assert not claimed, server.diagnosis(
        f"instructions name tools this server does not register: {sorted(claimed)}"
    )
    if "standards://" in instructions:
        assert reachable.get("resources") or reachable.get("prompts"), server.diagnosis(
            "instructions advertise the standards:// URI scheme with nothing registered under it"
        )
    return instructions


def adapter_source_files() -> list[Path]:
    package = require_adapter_module("")
    package_file = package.__file__
    assert package_file is not None, f"{ADAPTER_PACKAGE} must live in a real directory"
    return sorted(Path(package_file).parent.rglob("*.py"))


def cli_source_file() -> Path:
    from project_standards import cli

    cli_file = cli.__file__
    assert cli_file is not None
    return Path(cli_file)


def run_cli(
    arguments: Sequence[str], *, timeout: float = EXIT_DEADLINE
) -> subprocess.CompletedProcess[str]:
    """Run the unified CLI in a subprocess against the same distribution."""
    script = (
        f"from project_standards.cli import main\n\nraise SystemExit(main({list(arguments)!r}))\n"
    )
    return subprocess.run(
        [sys.executable, "-c", script],
        env={**os.environ, "PYTHONPATH": str(RUNTIME_ROOT), "NO_COLOR": "1", "COLUMNS": "200"},
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def boundary_option_name(help_text: str) -> str:
    """Discover the ADR 0026 launch-time boundary option from `mcp --help`.

    Discovered rather than frozen: the record fixes that exactly one optional
    launch-time boundary exists and that the adapter configuration "is not
    implementer-tunable in v1 beyond the items listed here", not what the option
    is called (review F8).
    """
    options = {
        option for option in re.findall(r"--[a-z0-9][a-z0-9-]*", help_text) if option != "--help"
    }
    assert len(options) == 1, (
        "ADR 0026 allows exactly one optional launch option on the `mcp` form "
        f"(the configured root boundary); found {sorted(options)}"
    )
    return options.pop()


def is_remote_module_path(dotted: str) -> bool:
    """Whether a dotted import names a remote-transport module path.

    Matched on path components rather than on an alias list, so
    ``from mcp.server.streamable_http import X`` is caught as surely as
    ``import mcp.server.sse`` (review F10).
    """
    parts = dotted.split(".")
    if parts[0] in REMOTE_IMPORT_ROOTS:
        return True
    if parts[0] != "mcp":
        return False
    return any(token in part.lstrip("_") for part in parts[1:] for token in REMOTE_PATH_TOKENS)


@pytest.fixture
def tampered_runtime(tmp_path: Path) -> Iterator[Path]:
    """A copy of the importable distribution with one payload byte corrupted.

    The eager full-installed-distribution integrity check that
    ``McpServiceFacade.from_installed`` performs must fail against this tree, so
    a server launched with it on ``PYTHONPATH`` can never reach stdio.
    """
    runtime = tmp_path / "tampered"
    package = runtime / "project_standards"
    shutil.copytree(RUNTIME_ROOT / "project_standards", package)
    payloads = sorted((package / "payloads").rglob("*.md"))
    assert payloads, "the installed distribution declares no payload resource to corrupt"
    target = payloads[0]
    target.write_bytes(target.read_bytes() + b"\ntampered by the T5 startup-integrity fixture\n")
    yield runtime


def test_transport_harness_speaks_the_protocol_against_a_bare_sdk_server() -> None:
    """RED control (T5.2): the fixtures, framing, and deadlines are themselves valid.

    Every other test in this file drives the same machinery against a module
    that does not exist yet. This one drives it against a bare SDK server with
    an empty registry, so a failure elsewhere is provably the absent adapter and
    not a broken protocol fixture. It also demonstrates that the selected SDK
    *can* express a truthful empty registry over stdio without contaminating
    stdout, which is the T5 stop/backtrack condition.

    One process per era: the SDK locks a connection's era at its opening
    request, so a single process cannot legally be probed both ways (review F1).
    """
    with ServerProcess(BARE_SDK_CONTROL, label="bare-sdk-control") as server:
        result = server.handshake(CODEX_CLIENT_REVISION)
        assert result["protocolVersion"] == CODEX_CLIENT_REVISION
        capabilities = declared_capabilities(result)
        reachable = assert_capabilities_match_reachable_registrations(
            server, capabilities, envelope=None
        )
        assert_no_write_surface(server, reachable)
        assert_no_list_change_promises(capabilities)
        expect_error(server, server.call("no/such/method", {}))
        server.send_raw(b"this line is not JSON at all\n")
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)

    for version in MODERN_PROTOCOL_VERSIONS:
        with ServerProcess(BARE_SDK_CONTROL, label=f"bare-sdk-control-{version}") as server:
            result = server.discover(version)
            assert version in result["supportedVersions"]
            assert_modern_result_contract(server, result)
            capabilities = declared_capabilities(result)
            reachable = assert_capabilities_match_reachable_registrations(
                server, capabilities, envelope={"_meta": modern_meta(version)}
            )
            assert_no_write_surface(server, reachable)
            assert_no_list_change_promises(capabilities)
            assert server.finish() == 0
            assert_stdout_is_protocol_only(server)


def test_modern_list_result_contract_is_satisfiable_by_the_sdk() -> None:
    """RED control (review F11): the successful modern-list branch has a live oracle.

    The empty-registry control above only ever takes the METHOD_NOT_FOUND branch
    of the capability helper, so the ``resultType``/``ttlMs``/``cacheScope``
    assertions would never execute until T6 registered something. This control
    registers one (empty) resource listing on a bare SDK server, which makes the
    successful branch run against SDK-owned output today — and proves those
    fields are the SDK's to produce rather than something an adapter must
    synthesize.
    """
    version = MODERN_PROTOCOL_VERSIONS[-1]
    with ServerProcess(BARE_SDK_CONTROL_WITH_LIST, label="bare-sdk-list-control") as server:
        result = server.discover(version)
        capabilities = declared_capabilities(result)
        assert capabilities.get("resources") is not None, (
            "the control server registers a resource listing, so it must declare the capability"
        )
        assert_no_list_change_promises(capabilities)
        reachable = assert_capabilities_match_reachable_registrations(
            server, capabilities, envelope={"_meta": modern_meta(version)}
        )
        assert "resources" in reachable, "the declared resources capability must be reachable"
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)

    # The classic envelope carries no result-contract fields, which is why the
    # modern assertions are era-scoped rather than applied everywhere.
    with ServerProcess(BARE_SDK_CONTROL_WITH_LIST, label="bare-sdk-list-classic") as server:
        capabilities = declared_capabilities(server.handshake(CODEX_CLIENT_REVISION))
        assert_capabilities_match_reachable_registrations(server, capabilities, envelope=None)
        assert server.finish() == 0


def test_sdk_register_still_contains_the_frozen_client_revision() -> None:
    """The Codex CLI revision this suite pins must remain one the SDK negotiates.

    ADR 0025 selected ``mcp==2.0.0`` precisely because it serves 2025-06-18 from
    the same server as 2026-07-28. If a future pin drops that revision, the
    dual-era premise of every transport test below is void and the failure
    should name that, not look like an adapter bug.
    """
    assert CODEX_CLIENT_REVISION in HANDSHAKE_PROTOCOL_VERSIONS
    assert MODERN_PROTOCOL_VERSIONS, "the SDK must advertise at least one modern revision"


def test_stdio_initialize_and_errors_keep_stdout_protocol_clean() -> None:
    """TC-T5-001 (FR-025, NFR-003, IR-006): the happy and error paths share one clean wire.

    The transcript deliberately mixes a successful handshake, an unknown method,
    malformed params on a spec method, and a line that is not JSON at all,
    because stdout contamination is most likely on exactly those paths — an SDK
    or adapter that prints a traceback or a parser complaint would corrupt the
    channel for every later frame.
    """
    require_mcp_subcommand()
    with ServerProcess(CLI_LAUNCH, label="classic-transcript") as server:
        result = server.handshake(CODEX_CLIENT_REVISION)
        assert result["protocolVersion"] == CODEX_CLIENT_REVISION
        server_info = as_object(result.get("serverInfo"), "serverInfo")
        assert server_info.get("name") == FROZEN_SERVER_NAME

        unknown = expect_error(server, server.call("standards/definitely-not-a-method", {}))
        assert unknown["code"] == METHOD_NOT_FOUND

        # Malformed params on a spec method: the SDK surface-validates before
        # handler lookup, so this is a structured error, one frame, and nothing
        # else on the wire.
        expect_error(server, server.call("resources/read", {"uri": []}))

        server.send_raw(b"{ this is not valid json\n")
        server.send_raw(b"\n")
        # The connection must survive both, and keep answering on the same wire.
        expect_error(server, server.call("standards/definitely-not-a-method", {}))

        assert server.finish() == 0
        frames = assert_stdout_is_protocol_only(server)
        assert answered_ids(frames) == server.sent_ids, (
            "every request must get exactly one response, in order"
        )


def test_every_sdk_advertised_revision_is_served_by_one_server() -> None:
    """FR-025/ADR 0025: dual-era serving, taken from the SDK's own register.

    The revisions are read from ``mcp_types.version`` rather than listed here so
    that an SDK bump which adds a revision widens this assertion instead of
    escaping it. The handshake era matters because Codex CLI 0.145.0 speaks
    2025-06-18 only; the modern era matters because 2026-07-28 is the final
    published revision and makes ``server/discover`` mandatory. "One server"
    means one built artifact, not one connection — the SDK locks each
    connection's era at its opening request.
    """
    require_mcp_subcommand()
    for version in HANDSHAKE_PROTOCOL_VERSIONS:
        with ServerProcess(CLI_LAUNCH, label=f"handshake-{version}") as server:
            result = server.handshake(version)
            assert result["protocolVersion"] == version, (
                f"the server counter-offered {result['protocolVersion']!r} for {version!r}"
            )
            assert server.finish() == 0
            assert_stdout_is_protocol_only(server)

    for version in MODERN_PROTOCOL_VERSIONS:
        with ServerProcess(CLI_LAUNCH, label=f"modern-{version}") as server:
            result = server.discover(version)
            assert version in result["supportedVersions"]
            assert_modern_result_contract(server, result)
            assert server.finish() == 0
            assert_stdout_is_protocol_only(server)


def test_each_era_refuses_the_other_eras_opening_contract() -> None:
    """FR-025: dual-era means era-honest, not era-permissive.

    2026-07-28 removed the handshake, and a connection opened in one era cannot
    be switched to the other. Both refusals are asserted because a server that
    accepted either would be advertising a lifecycle the revision does not have
    — and because this is the SDK behaviour that forces every other probe in
    this file to use one process per era.
    """
    require_mcp_subcommand()
    version = MODERN_PROTOCOL_VERSIONS[-1]
    with ServerProcess(CLI_LAUNCH, label="modern-then-initialize") as server:
        server.discover(version)
        error = expect_error(
            server,
            server.call(
                "initialize",
                {
                    "_meta": modern_meta(version),
                    "protocolVersion": CODEX_CLIENT_REVISION,
                    "capabilities": {},
                },
            ),
        )
        assert error["code"] != METHOD_NOT_FOUND
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)

    with ServerProcess(CLI_LAUNCH, label="classic-then-envelope") as server:
        server.handshake(CODEX_CLIENT_REVISION)
        error = expect_error(
            server, server.call("server/discover", {"_meta": modern_meta(version)})
        )
        assert error["code"] != METHOD_NOT_FOUND
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


def test_capabilities_match_registry_and_omit_write_and_remote() -> None:
    """TC-T5-002 (FR-018, FR-025, NFR-008, IR-008): declarations equal registrations.

    The equivalence is asserted in both directions and in both eras, together
    with the negatives ADR 0026 freezes permanently. It is deliberately not an
    emptiness pin: T6/T7/T8 register real features while rerunning this suite,
    and their contents belong to their own tests (review F2). At T5 nothing is
    registered, so the equivalence yields empty listings by itself.

    "Omit write" is the subset rule against ADR 0026's read-only six-tool
    registry. "Omit remote" is proven at the source level by
    ``test_no_remote_transport_entry_point_exists_in_the_adapter_or_cli``,
    because an HTTP entry point that no test happens to launch is still a
    shipped remote surface.
    """
    require_mcp_subcommand()
    with ServerProcess(CLI_LAUNCH, label="capabilities-classic") as server:
        capabilities = declared_capabilities(server.handshake(CODEX_CLIENT_REVISION))
        reachable = assert_capabilities_match_reachable_registrations(
            server, capabilities, envelope=None
        )
        assert_no_write_surface(server, reachable)
        assert_no_list_change_promises(capabilities)
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)

    version = MODERN_PROTOCOL_VERSIONS[-1]
    with ServerProcess(CLI_LAUNCH, label="capabilities-modern") as server:
        result = server.discover(version)
        assert_modern_result_contract(server, result)
        capabilities = declared_capabilities(result)
        reachable = assert_capabilities_match_reachable_registrations(
            server, capabilities, envelope={"_meta": modern_meta(version)}
        )
        assert_no_write_surface(server, reachable)
        assert_no_list_change_promises(capabilities)
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


def test_no_remote_transport_entry_point_exists_in_the_adapter_or_cli() -> None:
    """NFR-008 (FR-018 neighbour): v1 ships stdio and nothing else.

    Checked in the source rather than over the wire: an unused HTTP launcher is
    still a shipped remote surface, and "no Streamable HTTP entry point in v1"
    is a statement about what exists, not about what a test happened to call.

    Matched on module *paths* so ``from mcp.server.streamable_http import ...``
    cannot slip past an alias list, and extended to ``project_standards.cli``
    because T5 modifies that module and a second launcher would most naturally
    live there (review F10).
    """
    scanned = [*adapter_source_files(), cli_source_file()]
    offenders: dict[str, set[str]] = {}
    launchers: dict[str, set[str]] = {}
    for module_path in scanned:
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        found: set[str] = set()
        defined: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found |= {alias.name for alias in node.names if is_remote_module_path(alias.name)}
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                if is_remote_module_path(node.module):
                    found.add(node.module)
                found |= {
                    f"{node.module}.{alias.name}"
                    for alias in node.names
                    if alias.name in REMOTE_SDK_ATTRIBUTES
                    or is_remote_module_path(f"{node.module}.{alias.name}")
                }
            elif isinstance(node, ast.Attribute) and node.attr in REMOTE_SDK_ATTRIBUTES:
                found.add(node.attr)
            elif (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value in REMOTE_TRANSPORT_LITERALS
            ):
                found.add(node.value)
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and (
                REMOTE_LAUNCHER_PATTERN.match(node.name)
            ):
                defined.add(node.name)
        if found:
            offenders[module_path.name] = found
        if defined:
            launchers[module_path.name] = defined
    assert not offenders, f"a remote-transport surface is present: {offenders}"
    assert not launchers, f"a second, non-stdio launcher is defined: {launchers}"

    help_text = require_mcp_subcommand()
    lowered = help_text.lower()
    advertised = {
        option
        for option in re.findall(r"--[a-z0-9][a-z0-9-]*", lowered)
        if any(token in option for token in REMOTE_CLI_OPTION_TOKENS)
    }
    assert not advertised, f"`project-standards mcp` advertises remote options: {advertised}"


def test_list_changed_requires_notifications() -> None:
    """TC-T5-004 (DR-007, IR-008): no notification path, no notification promise.

    Three claims are separable and all three are asserted: nothing declares
    ``listChanged`` or ``subscribe`` in either era; the subscription method that
    would deliver 2026-07-28 change notifications is not served; and no
    notification frame is ever written to the wire during a full session.

    The middle claim is what makes this test discriminating. The SDK derives its
    modern-era ``listChanged`` and ``subscribe`` bits from whether the
    subscription-listen method is served, so a server built on an ergonomic
    wrapper that always registers it advertises change notifications it has
    never implemented.
    """
    require_mcp_subcommand()
    with ServerProcess(CLI_LAUNCH, label="listchanged-classic") as server:
        capabilities = declared_capabilities(server.handshake(CODEX_CLIENT_REVISION))
        assert_no_list_change_promises(capabilities)
        # Well-formed params on purpose: the SDK surface-validates spec methods
        # before handler lookup, so a malformed body would answer INVALID_PARAMS
        # and mask whether the method is served at all.
        for method, params in (
            ("resources/subscribe", {"uri": "standards://catalog/5"}),
            ("subscriptions/listen", {}),
        ):
            error = expect_error(server, server.call(method, params))
            assert error["code"] == METHOD_NOT_FOUND, (
                f"{method} is served, which is a notification path T5 has not implemented"
            )
        assert server.finish() == 0
        frames = assert_stdout_is_protocol_only(server)
        assert all("id" in frame for frame in frames), (
            "the server emitted a notification frame with no implemented notification path"
        )

    version = MODERN_PROTOCOL_VERSIONS[-1]
    with ServerProcess(CLI_LAUNCH, label="listchanged-modern") as server:
        assert_no_list_change_promises(declared_capabilities(server.discover(version)))
        # Well-formed by the 2026-07-28 surface (an opt-in filter is required),
        # so the refusal is "not served" rather than "malformed params".
        listen = {
            "_meta": modern_meta(version),
            "notifications": {"resourcesListChanged": True},
        }
        error = expect_error(server, server.call("subscriptions/listen", listen))
        assert error["code"] == METHOD_NOT_FOUND
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


def test_cli_launches_stdio_server() -> None:
    """TC-T5-005 (IR-001, FR-025): `project-standards mcp` is the launch surface.

    ADR 0025 rejected an optional ``project-standards[mcp]`` extra precisely so
    this subcommand works in the standard install, so the launch is exercised
    through the unified CLI's own ``main`` — the exact callable the console
    script entry point binds. One process per era, because the SDK locks a
    connection's era at its opening request (review F1).
    """
    require_mcp_subcommand()
    with ServerProcess(CLI_LAUNCH, label="cli-launch-classic") as server:
        result = server.handshake(CODEX_CLIENT_REVISION)
        assert result["protocolVersion"] == CODEX_CLIENT_REVISION
        server_info = as_object(result.get("serverInfo"), "serverInfo")
        assert server_info.get("name") == FROZEN_SERVER_NAME
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)

    version = MODERN_PROTOCOL_VERSIONS[-1]
    with ServerProcess(CLI_LAUNCH, label="cli-launch-modern") as server:
        result = server.discover(version)
        assert version in result["supportedVersions"]
        stamped = as_object(result.get("_meta", {}), "modern result _meta")
        info = as_object(
            stamped.get("io.modelcontextprotocol/serverInfo", {}), "stamped serverInfo"
        )
        assert info.get("name") == FROZEN_SERVER_NAME
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


def test_configured_root_boundary_option_reaches_adapter_configuration(tmp_path: Path) -> None:
    """ADR 0026 frozen configuration + review F8: the option is wired, not decorative.

    ADR 0026 allows exactly one launch-time knob — the optional configured root
    boundary, default none — and states the configuration "is not
    implementer-tunable in v1 beyond the items listed here". Its *spelling* is
    not frozen by any binding document, so it is discovered from ``--help`` at
    runtime.

    Wiring is proven in two linked halves, because at this task boundary no tool
    accepts a ``repo_root`` and there is therefore no protocol path from the
    option to the resolver yet. First: the value supplied on the command line
    must reach adapter construction, observed through a spy on the adapter
    factory rather than through a frozen parameter name. Second: that same
    value, handed to ``resolve_effective_root``, must reject an out-of-boundary
    root and accept an in-boundary one. Together they close the CLI-to-resolver
    path that T9's tools complete.
    """
    help_text = require_mcp_subcommand()
    option = boundary_option_name(help_text)

    transport = require_adapter_module("transport")
    repo_access = require_adapter_module("repo_access")
    from project_standards import cli
    from project_standards.mcp_services import ServiceError

    workspace = tmp_path / "workspace"
    inside = workspace / "consumer"
    inside.mkdir(parents=True)
    outside = tmp_path / "elsewhere"
    outside.mkdir()

    observed: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    real_create_server = transport.create_server

    def spy_create_server(*args: Any, **kwargs: Any) -> Any:
        observed.append((args, kwargs))
        return real_create_server(*args, **kwargs)

    served: list[Any] = []

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(transport, "create_server", spy_create_server)
        patch.setattr(transport, "run_stdio", served.append)
        exit_code = cli.main(["mcp", option, str(workspace)])

    assert exit_code == 0, f"`project-standards mcp {option} {workspace}` failed"
    assert observed, "the CLI never constructed a server through transport.create_server"
    assert served, "the CLI never handed the constructed server to transport.run_stdio"

    # The boundary must arrive at adapter construction. Compared by string over
    # every supplied argument value so a normalizing implementation still
    # matches; the parameter name and position are deliberately not asserted.
    resolved = workspace.resolve(strict=True)
    supplied = {str(value) for args, kwargs in observed for value in (*args, *kwargs.values())}
    assert any(str(resolved) in value or str(workspace) in value for value in supplied), (
        f"the configured boundary never reached adapter construction; saw {sorted(supplied)}"
    )

    # ... and the same value must actually narrow the resolver.
    assert repo_access.resolve_effective_root(inside, configured_boundary=workspace) == (
        inside.resolve(strict=True)
    )
    with pytest.raises(ServiceError):
        repo_access.resolve_effective_root(outside, configured_boundary=workspace)

    # Default none: the server must also start with no launch option at all.
    with ServerProcess(CLI_LAUNCH, label="cli-default-boundary") as server:
        server.handshake(CODEX_CLIENT_REVISION)
        assert server.finish() == 0


def test_cli_rejects_an_invalid_configured_boundary_without_touching_stdout(
    tmp_path: Path,
) -> None:
    """Plan T5: a refused launch input is a structured failure, never a broken wire.

    A boundary that cannot be resolved must abort the launch the same way a
    failed integrity check does — non-zero exit, diagnostic on stderr, not one
    byte on the protocol channel — rather than starting a server that silently
    ignores the option it was given.
    """
    help_text = require_mcp_subcommand()
    option = boundary_option_name(help_text)
    missing = tmp_path / "no-such-boundary"

    with ServerProcess(
        cli_launch_with([option, str(missing)]), label="cli-invalid-boundary"
    ) as server:
        server.request(
            "initialize",
            {
                "protocolVersion": CODEX_CLIENT_REVISION,
                "capabilities": {},
                "clientInfo": {"name": "t5-red-probe", "version": "0"},
            },
        )
        exit_code = server.finish()
        assert exit_code != 0, server.diagnosis("an unresolvable boundary still started stdio")
        assert bytes(server.stdout_bytes) == b"", server.diagnosis(
            "a refused launch input wrote to the protocol channel"
        )
        assert bytes(server.stderr_bytes), server.diagnosis(
            "a refused launch input produced no diagnostic on stderr"
        )


def test_logs_use_stderr_only() -> None:
    """TC-T5-006 (NFR-003, IR-006): stdout is the protocol channel and nothing else.

    While serving, a transcript that provokes parser complaints, unknown-method
    errors, and malformed params must leave stdout byte-for-byte protocol. The
    startup half of the claim lives in
    ``test_startup_integrity_failure_precedes_stdio_and_never_touches_stdout``,
    which is where a naive implementation would print.
    """
    require_mcp_subcommand()
    with ServerProcess(CLI_LAUNCH, label="stderr-serving") as server:
        server.handshake(CODEX_CLIENT_REVISION)
        server.send_raw(b"not json\n")
        server.notify("notifications/there-is-no-such-notification", {})
        expect_error(server, server.call("prompts/get", {"name": 12345}))
        expect_error(server, server.call("standards/definitely-not-a-method", {}))
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


def test_startup_integrity_failure_precedes_stdio_and_never_touches_stdout(
    tampered_runtime: Path,
) -> None:
    """Plan T5 interface/data: the eager integrity check completes before stdio starts.

    Three parts, because a non-zero exit with something on stderr is far too
    weak an oracle on its own (review F5). The unit seam proves the failure is a
    structured ``ServiceError`` with populated fields, which is what plan:373
    requires every startup error to map to; the control launch proves the same
    machinery starts a real server against the real distribution; and the
    failing launch proves the corrupted distribution aborts before stdio,
    answering nothing and writing not one byte to the protocol channel.
    """
    require_mcp_subcommand()

    from project_standards._version import package_version
    from project_standards.control_plane.distribution import InstalledDistribution
    from project_standards.control_plane.paths import CatalogMajor
    from project_standards.mcp_services import McpServiceFacade, ServiceError

    with pytest.raises(ServiceError) as raised:
        McpServiceFacade.from_installed(
            InstalledDistribution(
                tampered_runtime / "project_standards", tool_release=package_version()
            ),
            CatalogMajor("5"),
        )
    failure = raised.value
    assert isinstance(failure.code, str) and failure.code
    assert isinstance(failure.message, str) and failure.message
    assert isinstance(failure.remediation, str) and failure.remediation
    assert failure.severity == "error"

    with ServerProcess(CLI_LAUNCH, label="startup-control") as control:
        control.handshake(CODEX_CLIENT_REVISION)
        assert control.finish() == 0
        assert_stdout_is_protocol_only(control)

    with ServerProcess(CLI_LAUNCH, runtime_root=tampered_runtime, label="startup-tampered") as bad:
        bad.request(
            "initialize",
            {
                "protocolVersion": CODEX_CLIENT_REVISION,
                "capabilities": {},
                "clientInfo": {"name": "t5-red-probe", "version": "0"},
            },
        )
        exit_code = bad.finish()
        assert exit_code != 0, bad.diagnosis("a corrupted distribution still started stdio")
        assert bytes(bad.stdout_bytes) == b"", bad.diagnosis(
            "a failed startup wrote to the protocol channel"
        )
        assert bytes(bad.stderr_bytes), bad.diagnosis(
            "a failed startup produced no diagnostic on stderr"
        )


def test_server_writes_nothing_to_stdout_before_the_first_request() -> None:
    """NFR-003: no banner, no greeting, no readiness line.

    A server that announced itself on stdout would corrupt the first frame for
    every client, and the fault would look like a client bug. The quiet window
    is followed by a real exchange so this cannot pass against a server that
    never started at all.
    """
    require_mcp_subcommand()
    with ServerProcess(CLI_LAUNCH, label="quiet-start") as server:
        server.drain(QUIET_WINDOW)
        assert bytes(server.stdout_bytes) == b"", server.diagnosis(
            "the server wrote to stdout before receiving any request"
        )
        server.handshake(CODEX_CLIENT_REVISION)
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


def test_server_identity_and_instructions_are_static_truthful_and_era_stable() -> None:
    """ADR 0026 frozen adapter configuration, as amended 2026-07-29 (review F6).

    The record's six-tool draft text becomes binding at the task that completes
    the registry it describes; before then the server must still serve a static,
    era-stable, truthful instructions string. This pins everything the phase
    rule asserts — non-``None``, non-empty, identical on a repeated read,
    identical across two independent processes, identical between the classic
    and modern eras, and naming no tool or URI scheme this server does not
    register — while leaving the phase wording to the implementation.
    """
    require_mcp_subcommand()
    version = MODERN_PROTOCOL_VERSIONS[-1]
    classic: list[str] = []
    for attempt in range(2):
        with ServerProcess(CLI_LAUNCH, label=f"identity-classic-{attempt}") as server:
            result = server.handshake(CODEX_CLIENT_REVISION)
            server_info = as_object(result.get("serverInfo"), "serverInfo")
            assert server_info.get("name") == FROZEN_SERVER_NAME
            reachable = assert_capabilities_match_reachable_registrations(
                server, declared_capabilities(result), envelope=None
            )
            instructions = assert_instructions_are_truthful(server, result, reachable)
            # Static for the process lifetime: a second read on the same
            # connection must return the identical value.
            assert server.handshake(CODEX_CLIENT_REVISION).get("instructions") == instructions
            classic.append(instructions)
            assert server.finish() == 0
    assert classic[0] == classic[1], f"the instructions string varied between processes: {classic}"

    with ServerProcess(CLI_LAUNCH, label="identity-modern") as server:
        result = server.discover(version)
        reachable = assert_capabilities_match_reachable_registrations(
            server, declared_capabilities(result), envelope={"_meta": modern_meta(version)}
        )
        modern = assert_instructions_are_truthful(server, result, reachable)
        assert modern == classic[0], (
            f"the instructions string must be era-stable; classic {classic[0]!r} != {modern!r}"
        )
        assert server.finish() == 0


def test_adapter_configuration_exposes_only_the_launch_time_boundary() -> None:
    """ADR 0026 (review F1): the frozen configuration is not caller-tunable.

    The record says ``create_server`` "is not implementer-tunable in v1 beyond
    the items listed here", and of those items exactly one is a launch input:
    the optional configured root boundary. Identity, version, and instructions
    are frozen facts, so a caller must have no way to supply them — a public
    field accepting ``server_name`` or ``instructions`` would let a caller
    rename the server or advertise features it does not register, which is the
    untruthful surface TC-T5-002 exists to police.

    Asserted against the *served* values as well as the constructor shape, so a
    module that keeps the constants but ignores them still fails.
    """
    require_mcp_subcommand()
    models = require_adapter_module("models")
    configuration = require_attribute(models, "AdapterConfiguration", "adapter configuration")

    fields = {field.name for field in dataclasses.fields(configuration)}
    assert fields == {"configured_boundary"}, (
        f"AdapterConfiguration must carry only the launch-time boundary, got {sorted(fields)}"
    )
    assert require_attribute(models, "SERVER_NAME", "frozen server name") == FROZEN_SERVER_NAME

    instructions_constant = require_attribute(models, "PHASE_INSTRUCTIONS", "phase instructions")
    assert isinstance(instructions_constant, str) and instructions_constant.strip()

    with ServerProcess(CLI_LAUNCH, label="frozen-configuration") as server:
        result = server.handshake(CODEX_CLIENT_REVISION)
        server_info = as_object(result.get("serverInfo"), "serverInfo")
        assert server_info.get("name") == FROZEN_SERVER_NAME
        assert result.get("instructions") == instructions_constant, (
            "the served instructions must be the frozen constant, not a caller-supplied string"
        )
        # The version is the installed distribution's own metadata, so the
        # protocol identity can never disagree with the distribution the facade
        # was built from.
        assert server_info.get("version") == package_version()
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


def test_malformed_launch_syntax_writes_no_stdout(tmp_path: Path) -> None:
    """NFR-003 (review F3, partial disposition): usage errors keep stdout clean.

    Malformed launch *syntax* stays on the unified CLI's uniform argparse
    surface — exit 2 with a usage diagnostic on stderr — rather than being
    converted into a ``ServiceError``. ADR 0025 puts ``mcp`` on the unified CLI
    precisely so it behaves like every other subcommand, and no binding document
    makes usage errors structured service failures; forking argparse semantics
    for one subcommand would be an undocumented divergence.

    What NFR-003 *does* require on that path is that stdout stays empty, because
    a client that launched the server is already reading fd 1 as the protocol
    channel. That is what this pins. Semantic boundary-*value* errors are a
    different class and travel the structured launch-refusal path, which
    ``test_cli_rejects_an_invalid_configured_boundary_without_touching_stdout``
    covers.
    """
    help_text = require_mcp_subcommand()
    option = boundary_option_name(help_text)

    for arguments in (
        [option],  # option present, value missing
        ["--no-such-option", str(tmp_path)],
        ["unexpected-positional"],
    ):
        result = run_cli(["mcp", *arguments])
        assert result.returncode != 0, f"`mcp {' '.join(arguments)}` should not have succeeded"
        assert result.stdout == "", (
            f"`mcp {' '.join(arguments)}` wrote to the protocol channel: {result.stdout!r}"
        )
        assert result.stderr.strip(), (
            f"`mcp {' '.join(arguments)}` produced no diagnostic on stderr"
        )


def test_transport_module_exposes_the_named_adapter_surface() -> None:
    """§5.5 / ADR 0025: ``create_server`` and ``run_stdio`` exist in the adapter.

    Both names are frozen by ADR 0025's interface list, so they are asserted
    literally. Nothing else is: the review dropped the arity and parameter-shape
    pins because no binding document states them, and the boundary option's
    journey into adapter configuration is proven behaviourally instead, by
    ``test_configured_root_boundary_option_reaches_adapter_configuration``.
    """
    transport = require_adapter_module("transport")
    for name in ("create_server", "run_stdio"):
        assert hasattr(transport, name), (
            f"planned §5.5 adapter callable transport.{name} is absent; "
            "the T5 stdio adapter does not exist yet"
        )
        assert callable(getattr(transport, name))
