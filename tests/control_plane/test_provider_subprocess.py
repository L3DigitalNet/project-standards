"""Shared bounded provider execution for control-plane and MCP callers.

Covers TC-T4-008: the worker's results equal authoritative direct dispatch for
the same effective root, payload identity, operation, and input; the controlled
fixture's files are unchanged by every supported operation; and neither
Python-level nor file-descriptor-level worker output can reach the process
``stdout`` the protocol will later own.

``T4.0`` established why each of those needs a worker at all. The authoritative
dispatcher executes provider bytes in the *calling* process
(``src/project_standards/control_plane/providers.py:817``) and captures output
only by rebinding ``sys.stdout``/``sys.stderr`` (``providers.py:805``), so a
provider's ``os.write(1, ...)`` goes straight to the caller's own descriptor —
proven empirically in
``.project-pipeline/2026-07-24-project-standards-mcp-server/logs/T4.0.txt``. The
fixture providers write at *both* levels for exactly that reason.

That same asymmetry decides what parity can mean for diagnostics (T4.2 Codex
review F7). The dispatcher destroys a provider's Python-level text and keeps
only a one-line ``ProviderResult.output_notice``, so raw prints are
unrecoverable by construction — but the notice itself is an authoritative fact
and dropping it would be a silent loss. Parity therefore requires the notice to
survive into bounded diagnostics, and requires nothing about the destroyed text.

ADR 0025's confirmation clause is the third obligation: after each of the four
completion paths — success, timeout, kill, and crash — the parent must hold no
open worker pipe, descriptor, or temporary IPC artifact, and no child may remain
unreaped. The baseline is taken *before the first* invocation, so a one-time
global pipe or fixed socket path cannot hide inside a warm-up (review F13).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from importlib import import_module
from pathlib import Path
from typing import Any

import pytest

from project_standards.control_plane import provider_subprocess
from project_standards.control_plane.provider_subprocess import (
    ProviderSubprocessError,
    python_worker_environment,
    run_provider_subprocess,
)
from project_standards.package_contract.payload import ProviderOperation
from tests.mcp_services.helpers import import_mcp_services
from tests.mcp_services.test_consumer import dumped
from tests.mcp_services.test_providers import (
    SELECTED_STANDARD,
    SELECTED_VERSION,
    assert_error_is_content_safe,
    assert_no_unreaped_children,
    assert_ran_in_worker,
    build_facade,
    build_provider_distribution,
    build_provider_repo,
    mapped_finding,
    open_descriptors,
    oracle_dispatch,
    published_finding,
    require_attribute,
    require_operation,
    require_service_module,
    result_identity,
    tree_state,
    worker_identity,
)

# The four ADR-approved operations paired with the fixture provider that
# declares each one.
SUPPORTED_DISPATCH: tuple[tuple[str, str, ProviderOperation], ...] = (
    ("validate-alpha", "validate", ProviderOperation.VALIDATE),
    ("verify-alpha", "verify", ProviderOperation.VERIFY),
    ("lint-alpha", "lint", ProviderOperation.LINT),
    ("drift-check-alpha", "drift-check", ProviderOperation.DRIFT_CHECK),
)

_FD_DIRECTORY = Path("/proc/self/fd")

requires_fd_introspection = pytest.mark.skipif(
    not _FD_DIRECTORY.is_dir(),
    reason="file-descriptor accounting needs /proc/self/fd",
)


def test_worker_matches_direct_dispatch_and_isolates_output_without_writes(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    """TC-T4-008: worker results equal direct dispatch; no writes, no stdout leakage."""
    services = import_mcp_services()
    distribution = build_provider_distribution(tmp_path, hazards=("probe",))
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    invoke = require_operation(facade, "invoke_read_provider")

    before = tree_state(repo)
    worker_pids: set[int] = set()
    for provider_id, operation, typed in SUPPORTED_DISPATCH:
        result = invoke(
            repo,
            standard_id=SELECTED_STANDARD,
            version=SELECTED_VERSION,
            provider_id=provider_id,
            operation=operation,
            provider_input={},
        )
        oracle = oracle_dispatch(
            repo,
            distribution,
            standard_id=SELECTED_STANDARD,
            provider_id=provider_id,
            operation=typed,
        )
        assert result_identity(result) == (
            SELECTED_STANDARD,
            SELECTED_VERSION,
            provider_id,
            operation,
        )
        assert result.effect == oracle.effect.value
        assert dumped(result)["output"] == oracle.structured_output
        # The declared normalization is the DR-003 rename plus root-relative
        # paths; nothing else may differ from the authoritative result.
        assert [published_finding(item) for item in result.findings] == [
            mapped_finding(item) for item in oracle.findings
        ]
        # Every approved operation ran in a separate process on this
        # interpreter, not only the instrumented probe provider (review F6).
        assert_ran_in_worker(result)
        worker_pids.add(worker_identity(result)[0])

        # Every supported operation is a read: type, mode, inode, ctime, link
        # target, and bytes must all be unchanged.
        assert tree_state(repo) == before, f"{operation} changed the consumer filesystem"

    # Both composite tools inherit the boundary rather than shortcutting it.
    for report in (
        require_operation(facade, "validate_repo")(repo),
        require_operation(facade, "drift_check")(repo),
    ):
        assert report.results
        for item in report.results:
            assert_ran_in_worker(item)
            worker_pids.add(worker_identity(item)[0])
    assert os.getpid() not in worker_pids
    assert tree_state(repo) == before

    # The print-only provider lives in its own distribution: it emits nothing at
    # the file-descriptor level by design, so a tree carrying it would also hand
    # it to validate_repo, where the process-separation proof needs the probe
    # channel every other fixture provider writes.
    printer_distribution = build_provider_distribution(tmp_path / "printer", hazards=("printer",))
    printer_facade = build_facade(services, printer_distribution)
    printer_repo = build_provider_repo(
        tmp_path / "printer", "consumer", distribution=printer_distribution
    )
    printer_oracle = oracle_dispatch(
        printer_repo,
        printer_distribution,
        standard_id=SELECTED_STANDARD,
        provider_id="printer-alpha",
        operation=ProviderOperation.VALIDATE,
    )
    assert printer_oracle.output_notice is not None, (
        "the print-only fixture must make the dispatcher publish an output notice"
    )

    # Everything above ran the authoritative dispatcher in *this* process, whose
    # fixture output legitimately reaches these streams; the isolation claim is
    # about what the service does, so the slate is cleared first.
    capfd.readouterr()
    printed = require_operation(printer_facade, "invoke_read_provider")(
        printer_repo,
        standard_id=SELECTED_STANDARD,
        version=SELECTED_VERSION,
        provider_id="printer-alpha",
        operation="validate",
        provider_input={},
    )
    probe = invoke(
        repo,
        standard_id=SELECTED_STANDARD,
        version=SELECTED_VERSION,
        provider_id="probe-alpha",
        operation="validate",
        provider_input={},
    )
    captured = capfd.readouterr()

    # An authoritative fact the dispatcher does publish must survive: the
    # one-line notice that provider output was suppressed (review F7).
    assert printer_oracle.output_notice in printed.diagnostics, (
        "the authoritative output notice was dropped instead of preserved"
    )
    assert probe.findings[0].message == f"pid={worker_identity(probe)[0]}"
    assert tree_state(repo) == before

    # Neither Python-level prints nor file-descriptor writes reached the streams
    # the stdio transport will own.
    for marker in (
        "PROBE-PYTHON-STDOUT",
        "PROBE-PYTHON-STDERR",
        "PROBE-FD-STDOUT",
        "PROBE-FD-STDERR",
        "PRINTER-PYTHON-STDOUT",
        "PRINTER-PYTHON-STDERR",
        "WORKER-PROBE",
    ):
        assert marker not in captured.out, f"{marker} contaminated protocol stdout"
        assert marker not in captured.err, f"{marker} contaminated the log stream"

    # File-descriptor-level output is exactly what the in-process dispatcher
    # cannot capture, so it must arrive as bounded diagnostics instead.
    assert "PROBE-FD-STDOUT" in probe.diagnostics
    assert "PROBE-FD-STDERR" in probe.diagnostics
    assert_no_unreaped_children()


def test_worker_module_is_sdk_free_and_importable_by_name() -> None:
    """IR-004/NFR-006: the worker is an ordinary SDK-free module of this package.

    ADR 0025 spawns the worker on the server's own interpreter and virtual
    environment, so it must be reachable by its dotted module name; and because
    it lives under ``mcp_services`` it may never reach for the SDK or the adapter
    package. The entry-point *shape* is deliberately not frozen here — the ADR
    fixes where provider code runs, not how the parent starts it.
    """
    worker = import_module("project_standards.control_plane.provider_worker")
    providers = require_service_module("providers")
    assert worker.__name__ == "project_standards.control_plane.provider_worker"
    for module in (worker, providers):
        source = Path(str(module.__file__)).read_text(encoding="utf-8")
        assert "import mcp\n" not in source
        assert "from mcp" not in source
        assert "mcp_server" not in source


def test_python_callers_share_one_control_plane_transport_implementation() -> None:
    """Direct and MCP routes call one runner; the worker cannot recursively spawn."""
    direct = import_module("project_standards.control_plane.providers")
    service = import_module("project_standards.mcp_services.providers")
    worker = import_module("project_standards.control_plane.provider_worker")

    direct_source = Path(str(direct.__file__)).read_text(encoding="utf-8")
    service_source = Path(str(service.__file__)).read_text(encoding="utf-8")
    worker_source = Path(str(worker.__file__)).read_text(encoding="utf-8")

    assert direct_source.count("run_provider_subprocess(") == 1
    assert service_source.count("run_provider_subprocess(") == 1
    assert "subprocess.Popen" not in direct_source
    assert "subprocess.Popen" not in service_source
    assert "run_provider_subprocess" not in worker_source
    assert "invoke_provider_in_child" in worker_source


def ipc_artifacts(scratch: Path) -> list[str]:
    """Return every filesystem artifact left inside the dedicated IPC directory."""
    return sorted(item.relative_to(scratch).as_posix() for item in scratch.rglob("*"))


@requires_fd_introspection
@pytest.mark.parametrize("path", ["success", "timeout", "kill", "crash"])
def test_worker_releases_every_resource_on_all_four_completion_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    """ADR 0025 confirmation: no descriptor, IPC artifact, or child survives any exit.

    The baseline is captured *before the first* invocation and re-compared after
    every later one, so a pipe or socket created once and leaked forever is
    caught rather than absorbed into a warm-up (T4.2 review F13). Temporary files
    are redirected into a dedicated directory so an IPC artifact cannot hide
    among the system temp directory's unrelated contents.
    """
    services = import_mcp_services()
    providers = require_service_module("providers")
    scratch = tmp_path / "ipc-scratch"
    scratch.mkdir()
    for variable in ("TMPDIR", "TEMP", "TMP"):
        monkeypatch.setenv(variable, str(scratch))
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))

    distribution = build_provider_distribution(tmp_path, hazards=("slow", "stubborn", "crash"))
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    invoke = require_operation(facade, "invoke_read_provider")

    provider_id = {
        "success": "validate-alpha",
        "timeout": "slow-alpha",
        "kill": "stubborn-alpha",
        "crash": "crash-alpha",
    }[path]
    if path in {"timeout", "kill"}:
        monkeypatch.setattr(providers, "PROVIDER_TIMEOUT_SECONDS", 1.0)

    def call() -> None:
        request: dict[str, Any] = {
            "standard_id": SELECTED_STANDARD,
            "version": SELECTED_VERSION,
            "provider_id": provider_id,
            "operation": "validate",
            "provider_input": {},
        }
        if path == "success":
            invoke(repo, **request)
            return
        with pytest.raises(services.ServiceError) as raised:
            invoke(repo, **request)
        assert_error_is_content_safe(raised.value, repo, distribution)

    baseline = (open_descriptors(), ipc_artifacts(scratch), tree_state(repo))
    for _ in range(3):
        call()
        observed = (open_descriptors(), ipc_artifacts(scratch), tree_state(repo))
        assert observed[0] == baseline[0], f"{path} leaked a worker descriptor"
        assert observed[1] == baseline[1], f"{path} left an IPC artifact behind: {observed[1]}"
        assert observed[2] == baseline[2], f"{path} changed the consumer filesystem"
        assert_no_unreaped_children()


def test_non_json_typed_input_is_refused_before_the_worker_starts(tmp_path: Path) -> None:
    """TC-T4-008 (FR-014): only JSON-safe typed input may cross the IPC boundary."""
    services = import_mcp_services()
    distribution = build_provider_distribution(tmp_path)
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    invoke = require_operation(facade, "invoke_read_provider")

    before = tree_state(repo)
    for provider_input in (
        {"unserializable": {1, 2}},
        {"unserializable": object()},
        {"not_finite": float("nan")},
        {"binary": b"bytes"},
        {1: "non-string-key"},
    ):
        with pytest.raises(services.ServiceError) as raised:
            invoke(
                repo,
                standard_id=SELECTED_STANDARD,
                version=SELECTED_VERSION,
                provider_id="validate-alpha",
                operation="validate",
                provider_input=provider_input,
            )
        error = raised.value
        assert_error_is_content_safe(error, repo, distribution)
        assert len(json.dumps([error.code, error.message, error.remediation])) < 4096
    assert tree_state(repo) == before
    assert_no_unreaped_children()


# ---------------------------------------------------------------------------
# T4.4 Codex GREEN review: the parent believes nothing it has not checked
# ---------------------------------------------------------------------------

# Each stub replaces the worker bootstrap with a hostile one that owns the same
# trusted response descriptor a provider does. That is the point: ADR 0025 does
# not sandbox payload bytes — the authoritative in-process path already grants
# them strictly more — so the boundary that must hold is the parent's, and it is
# exercised here without adding the third supervising process the plan forbids
# (T4.4 Codex GREEN review F2, disposition REJECT-AS-WRITTEN / ACCEPT-BOUNDED).
HOSTILE_FRAMES: tuple[tuple[str, str], ...] = (
    ("not-json", "os.write(fd, b'this is not json at all')"),
    ("not-an-object", "os.write(fd, b'[1, 2, 3]')"),
    ("no-status", 'os.write(fd, b\'{"effect": "findings", "findings": []}\')'),
    ("unknown-status", 'os.write(fd, b\'{"status": "forged"}\')'),
    ("missing-effect", 'os.write(fd, b\'{"status": "ok", "findings": []}\')'),
    (
        "findings-not-a-list",
        'os.write(fd, b\'{"status": "ok", "effect": "findings", "findings": {}}\')',
    ),
    (
        "malformed-finding",
        'os.write(fd, b\'{"status": "ok", "effect": "findings", "findings": [{"code": 1}]}\')',
    ),
    (
        "undeclared-finding-field",
        "os.write(fd, json.dumps({'status': 'ok', 'effect': 'findings', 'findings': ["
        "{'code': 'X', 'severity': 'error', 'standard_id': 'alpha', 'version': '2.0',"
        " 'path': 'README.md', 'identity': '$file', 'message': 'm', 'hint': 'h',"
        " 'injected': 'surprise'}]}).encode())",
    ),
    (
        "output-not-an-object",
        'os.write(fd, b\'{"status": "ok", "effect": "findings", "findings": [],'
        ' "output": "string"}\')',
    ),
    (
        "oversized",
        "os.write(fd, json.dumps({'status': 'ok', 'effect': 'findings', 'findings': [],"
        " 'output': {'blob': 'y' * 1000000}}).encode())",
    ),
)


def hostile_bootstrap(body: str) -> str:
    """Build a worker bootstrap that forges a response and exits successfully."""
    return f"import json, os, sys\nfd = int(sys.argv[1])\n{body}\nos.close(fd)\nos._exit(0)\n"


@pytest.mark.parametrize(("label", "body"), HOSTILE_FRAMES, ids=[row[0] for row in HOSTILE_FRAMES])
def test_forged_ipc_frames_are_refused_by_the_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, label: str, body: str
) -> None:
    """F2 (bounded accept): every inbound frame is validated for schema, type, and size."""
    services = import_mcp_services()
    distribution = build_provider_distribution(tmp_path)
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    invoke = require_operation(facade, "invoke_read_provider")
    monkeypatch.setattr(provider_subprocess, "_PYTHON_WORKER_BOOTSTRAP", hostile_bootstrap(body))

    before = tree_state(repo)
    with pytest.raises(services.ServiceError) as raised:
        invoke(
            repo,
            standard_id=SELECTED_STANDARD,
            version=SELECTED_VERSION,
            provider_id="validate-alpha",
            operation="validate",
            provider_input={},
        )
    error = raised.value
    assert_error_is_content_safe(error, repo, distribution, identified=True)
    assert len(error.message) < 4096, f"{label} produced an unbounded failure message"
    assert tree_state(repo) == before
    assert open_descriptors()
    assert_no_unreaped_children()


def test_forged_error_frames_cannot_publish_attacker_selected_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F2: a forged *error* frame cannot choose the text a caller is shown."""
    services = import_mcp_services()
    distribution = build_provider_distribution(tmp_path)
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    invoke = require_operation(facade, "invoke_read_provider")
    forged = json.dumps(
        {
            "status": "error",
            "code": "forged",
            "detail": f"/etc/shadow and {repo.resolve()}/secret leaked FORGED-SENTINEL",
        }
    )
    monkeypatch.setattr(
        provider_subprocess,
        "_PYTHON_WORKER_BOOTSTRAP",
        hostile_bootstrap(f"os.write(fd, {forged!r}.encode())"),
    )

    with pytest.raises(services.ServiceError) as raised:
        invoke(
            repo,
            standard_id=SELECTED_STANDARD,
            version=SELECTED_VERSION,
            provider_id="validate-alpha",
            operation="validate",
            provider_input={},
        )
    error = raised.value
    assert_error_is_content_safe(
        error, repo, distribution, forbidden=("/etc/shadow",), identified=True
    )
    assert "FORGED-SENTINEL" not in error.message
    assert_no_unreaped_children()


def test_a_worker_that_never_reads_its_request_still_fails_within_the_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F4: request transmission is inside the deadline-bound loop, not before it.

    The stub never reads stdin and never writes a result, and the request is far
    larger than a pipe buffer. A parent that wrote the request with a blocking
    ``write()`` before draining would block there indefinitely, outliving the
    execution bound entirely.
    """
    services = import_mcp_services()
    providers = require_service_module("providers")
    distribution = build_provider_distribution(tmp_path)
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    invoke = require_operation(facade, "invoke_read_provider")
    monkeypatch.setattr(providers, "PROVIDER_TIMEOUT_SECONDS", 2.0)
    monkeypatch.setattr(
        provider_subprocess,
        "_PYTHON_WORKER_BOOTSTRAP",
        "import time, sys\nsys.stderr.write('x' * 4096)\ntime.sleep(300)\n",
    )

    limit = require_attribute(providers, "REQUEST_LIMIT_BYTES", "T4 module constant")
    # Comfortably beyond any platform pipe capacity, and still inside the
    # service's own request bound so this exercises transmission, not rejection.
    payload = {"filler": "z" * int(limit * 0.6)}
    descriptors = open_descriptors()
    started = time.monotonic()
    with pytest.raises(services.ServiceError) as raised:
        invoke(
            repo,
            standard_id=SELECTED_STANDARD,
            version=SELECTED_VERSION,
            provider_id="validate-alpha",
            operation="validate",
            provider_input=payload,
        )
    elapsed = time.monotonic() - started
    assert elapsed < 20, f"the request send escaped the execution bound ({elapsed:.2f}s)"
    assert_error_is_content_safe(raised.value, repo, distribution, identified=True)
    assert open_descriptors() == descriptors
    assert_no_unreaped_children()


_RESULT_FD_SCRIPT = """
import json
import os
import sys

request = json.loads(sys.stdin.buffer.read())
os.write(1, b"stdout-data\\n")
os.write(2, b"stderr-data\\n")
with os.fdopen(int(sys.argv[1]), "wb") as stream:
    stream.write(json.dumps({"status": "ok", "result": request}).encode("utf-8"))
"""

_DESCENDANT_SCRIPT = """
import json
import os
import sys
import time

request = json.loads(sys.stdin.buffer.read())
child = os.fork()
if child == 0:
    request_path = request["sentinel"]
    with open(request_path, "w", encoding="utf-8") as stream:
        stream.write(str(os.getpid()))
    time.sleep(300)
    raise SystemExit(0)
time.sleep(300)
"""


def _python_argv(script: str) -> tuple[str, ...]:
    return (sys.executable, "-c", script)


def _assert_process_gone(pid: int) -> None:
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.01)
    pytest.fail(f"provider descendant {pid} survived subprocess teardown")


def test_run_provider_subprocess__separate_result_fd__captures_diagnostics() -> None:
    request = {"value": "expected"}

    outcome = run_provider_subprocess(
        _python_argv(_RESULT_FD_SCRIPT),
        json.dumps(request).encode("utf-8"),
        timeout=5.0,
        environment=python_worker_environment(),
    )

    assert outcome.frame == {"status": "ok", "result": request}
    assert outcome.stdout.content == b"stdout-data\n"
    assert outcome.stderr.content == b"stderr-data\n"


def test_run_provider_subprocess__timeout__terminates_descendant_group(tmp_path: Path) -> None:
    sentinel = tmp_path / "descendant.pid"

    with pytest.raises(ProviderSubprocessError) as raised:
        run_provider_subprocess(
            _python_argv(_DESCENDANT_SCRIPT),
            json.dumps({"sentinel": str(sentinel)}).encode("utf-8"),
            timeout=1.0,
            environment=python_worker_environment(),
        )

    assert raised.value.code == "provider-timeout"
    assert sentinel.is_file(), "the timeout expired before the fixture created its descendant"
    _assert_process_gone(int(sentinel.read_text(encoding="utf-8")))
