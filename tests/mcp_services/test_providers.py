"""Bounded non-mutating provider services behind the SDK-free facade (T4).

Covers TC-T4-001 (validate/drift orchestration over the current exact
resolution), TC-T4-003 (bounded, fingerprint-neutral diagnostics), TC-T4-004
(every DR-003 finding field), TC-T4-005 (the ADR 0025 execution bound with a
reaped worker), TC-T4-006 (exact payload qualification), and TC-T4-007 (declared
result fields preserved).

Two authorities constrain every expectation here and neither may be re-derived
by the service under test:

*The dispatcher* — ``invoke_provider`` — owns provider semantics and delegates
execution to the control-plane runner shared by direct and MCP calls. Identity
qualification, resource closure, input/output schema validation, effect-typed
result construction, the 30-second bound, group teardown, bounded JSON IPC, and
file-descriptor-level capture are therefore one control-plane contract. Parity
is asserted against that dispatcher directly.

*The control plane* — ``build_planner_request``/``plan_reconciliation`` for the
reconciliation identity, and ``selected_command``/``invoke_selected_provider``
(``src/project_standards/control_plane/command_resolution.py:163``) for the
"current exact resolution" that selects a package's payload and effective
config. ``validate_repo`` and ``drift_check`` are compositions over those, so a
service that re-resolves, re-plans, or re-fingerprints cannot pass.

Every fixture provider writes one ``WORKER-PROBE pid=… exe=…`` line to file
descriptor 2. That single channel carries the process-separation proof for every
approved operation and both composite tools without adding a field to any DTO
(T4.2 Codex review F6, disposition ACCEPT-AMENDED): the dispatcher cannot
capture it in-process, so it can only ever reach a caller through a real worker
boundary.

This module also owns the T4 fixture builders, which the worker and security
suites import. T4's file list does not include ``tests/mcp_services/helpers.py``,
so — following the T3 precedent — the builders live beside their first consumer
rather than being duplicated across three suites.
"""

from __future__ import annotations

import base64
import hashlib
import importlib
import importlib.util
import json
import os
import re
import shutil
import stat
import sys
import time
import tomllib
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, fields
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from project_standards.control_plane import provider_subprocess
from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.command_resolution import (
    SelectedCommandPackage,
    invoke_selected_provider,
    selected_command,
)
from project_standards.control_plane.diagnostics import ControlFinding, ControlPlaneError
from project_standards.control_plane.distribution import InstalledDistribution, InstalledPayload
from project_standards.control_plane.executor import reconciliation_fingerprint
from project_standards.control_plane.locking import LockMode
from project_standards.control_plane.paths import CatalogMajor
from project_standards.control_plane.planner import ReconciliationPlan, plan_reconciliation
from project_standards.control_plane.provider_inputs import (
    NoDeclaredProviderInput,
    provider_dispatch_input,
)
from project_standards.control_plane.providers import ProviderResult
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.paths import PackageVersion
from project_standards.package_contract.payload import (
    JsonObject,
    PayloadAvailability,
    PayloadManifest,
    ProviderDeclaration,
    ProviderEffect,
    ProviderKind,
    ProviderOperation,
)
from project_standards.package_contract.projection import sync_payload_projection
from tests.control_plane.test_command_provider_end_to_end import (
    COMMAND_FIXTURE_RESOURCE,
    COMMAND_FIXTURE_STANDARD,
    COMMAND_FIXTURE_VERSION,
    command_provider_distribution,
    initialize_command_provider_repo,
    reconcile_command_provider_repo,
)
from tests.control_plane.test_command_providers import command_payload
from tests.mcp_services.helpers import FULL_FIXTURE, import_mcp_services
from tests.mcp_services.test_consumer import TOOL_RELEASE, dumped, field_names, model_config_of

# The four operations ADR 0025 approves. Nothing in the suite asserts that an
# implementation publishes this tuple under any name (T4.2 review F15): the
# allowlist is frozen only by which declared providers are accepted and which
# are refused before process creation.
APPROVED_OPERATIONS = ("validate", "verify", "lint", "drift-check")

# ADR 0025: "The provider timeout is 30 seconds per provider invocation."
ADR_TIMEOUT_SECONDS = 30

# Issue #158 measured a 7.901-second unloaded maximum and a 356-second saturated
# outlier; this finite test-only margin leaves the production 30-second default intact.
REAL_PACKAGE_PROVIDER_TIMEOUT_SECONDS = 400.0

# alpha 2.0 is the fixture's default-role consumer version, so it is what the
# authoritative resolution selects for an enabled `alpha`; alpha 3.0 is the
# candidate version used to prove exact version qualification.
SELECTED_STANDARD = "alpha"
SELECTED_VERSION = "2.0"
CANDIDATE_VERSION = "3.0"

# alpha 2.0's declared repository-relative extension input. These identities are
# read from the payload manifest and its config schema, not invented.
EXTENSION_ID = "local-options"
EXTENSION_OPTION = "extension_path"
EXTENSION_PATH = ".standards/extensions/alpha/options.toml"

# Every byte the noisy providers write is this character, so any other character
# in the returned diagnostics is text the service itself added — which is how
# the truncation indication is proven without freezing a marker sentence.
NOISE_BYTE = "x"
NOISE_LENGTH = 4_000_000
OVERSIZE_LENGTH = 4_000_000

# The deliberately slow provider used for the bidirectional bound proof. It must
# be long enough that spawn latency cannot be mistaken for the provider itself.
MEDIUM_SLEEP_SECONDS = 3.0

# What every provider that must outlive its own invocation sleeps for. Named so
# the watchdogs below are derived from it rather than from a second literal that
# could drift past it and stop meaning "sooner than the provider's own course".
HAZARD_SLEEP_SECONDS = 300

# Why no bound in this suite is a fixed number (issue #147).
#
# The shared runner starts its deadline when ``Popen`` returns, not when the
# provider's first statement runs, so every injected bound has to outlast a cold
# interpreter that imports the whole installed distribution before the payload is
# even loaded. That start-up costs a few tenths of a second on an idle machine
# and was measured between 1.2 s and 10 s while the gate ran this suite at
# ``-n 16`` beside its two other lanes. A bound picked to fire *during* a
# provider therefore fires during the worker's own import instead, and the
# fixture never installs the signal handler — or writes the sentinel — that the
# assertion afterwards is about. That is a race with the scheduler, not a
# statement about the service, and it is why this set failed nondeterministically
# under gate parallelism while passing serially.
#
# The remedy is not a bigger constant. Each bounded proof escalates its own bound
# until the fixture's own "I started" sentinel shows the worker got far enough
# for the proof to mean anything, and every claim that used to be read off the
# wall clock is now read off a sentinel instead. What remains in seconds is a
# watchdog against hanging, never an oracle about speed.
FIRST_BOUND_SECONDS = 2.0
BOUND_CEILING_SECONDS = 64.0

# Comfortably beyond any escalation and any teardown, and still far short of the
# course a hazard provider would run if nothing bounded it — so "finished before
# this" still means "the service, not the provider, ended the invocation".
WATCHDOG_SECONDS = HAZARD_SLEEP_SECONDS / 3

PROBE_PATTERN = re.compile(r"WORKER-PROBE pid=(\d+) exe=(\S+)")

_PROVIDER_SOURCE = """

def _probe():
    import os
    import sys

    # File-descriptor level on purpose: the authoritative dispatcher redirects
    # only sys.stdout/sys.stderr, so this line can reach a caller only through a
    # real worker process whose descriptors were captured.
    os.write(2, ("WORKER-PROBE pid=%d exe=%s\\n" % (os.getpid(), sys.executable)).encode())


def _sentinel(name, text="1"):
    import pathlib

    # At the installed distribution root: outside the consumer repository, so a
    # sentinel can never be confused with a repository mutation, and outside the
    # payload directory, whose integrity check rejects any undeclared file and
    # would otherwise break every later call in the same test.
    pathlib.Path(__file__).parents[3].joinpath(name).write_text(text, "utf-8")


def _base_finding():
    return {
        "code": "ALPHA-VALIDATE",
        "severity": "warning",
        "path": "README.md",
        "identity": "$file",
        "message": "alpha validate finding",
        "hint": "edit README.md",
        "line": 12,
        "column": 7,
        "locus": "document heading",
        "observed": 191,
        "limit": 160,
    }


def validate(_request, _resources):
    _probe()
    return {"findings": [_base_finding()], "checked": 3, "profile": "strict"}


def verify(_request, _resources):
    _probe()
    return {"findings": [], "checked": 1, "profile": "strict"}


def lint(_request, _resources):
    _probe()
    return {"findings": [], "checked": 0, "profile": "lenient"}


def drift_check(_request, _resources):
    import os
    import time

    _probe()
    # Deliberately nondeterministic: two calls in the same repository must
    # differ here while the reconciliation fingerprint stays identical.
    os.write(2, ("drift nonce %d %r\\n" % (os.getpid(), time.monotonic())).encode())
    finding = _base_finding()
    finding["code"] = "ALPHA-DRIFT"
    finding["severity"] = "error"
    finding["message"] = "alpha drift finding"
    return {"findings": [finding], "checked": 2, "profile": "strict"}


def fix(_request, _resources):
    _sentinel("MUTATING-PROVIDER-RAN")
    return {
        "schema_version": "1.0",
        "standard_id": "alpha",
        "version": "2.0",
        "actions": [],
    }


def semantic_review(_request, _resources):
    _sentinel("SEMANTIC-REVIEW-RAN")
    return {"findings": [], "checked": 0, "profile": "strict"}


def _plain(value):
    # The dispatcher hands providers a deep-frozen input (MappingProxyType and
    # tuples, control_plane/providers.py:297), which json.dumps refuses; a
    # provider that echoes its input must therefore thaw it first.
    if hasattr(value, "items"):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def echo(request, _resources):
    _probe()
    snapshots = _plain(request["snapshots"])
    finding = _base_finding()
    finding["code"] = "ALPHA-ECHO"
    finding["path"] = snapshots.get("echo_path") or "README.md"
    finding["message"] = "nonce=%s" % (snapshots.get("nonce"),)
    return {
        "findings": [finding],
        "echo_config": _plain(request["config"]),
        "echo_snapshots": snapshots,
        "echo_identity": [request["standard_id"], request["version"], request["operation"]],
        "checked": 0,
    }


def printer(_request, _resources):
    import sys

    # Python-level only: the dispatcher swallows this text and keeps just its
    # one-line notice, which is the only thing a worker can preserve.
    print("PRINTER-PYTHON-STDOUT")
    print("PRINTER-PYTHON-STDERR", file=sys.stderr)
    return {"findings": [], "checked": 0, "profile": "strict"}


def probe(_request, _resources):
    import os
    import sys

    _probe()
    print("PROBE-PYTHON-STDOUT")
    print("PROBE-PYTHON-STDERR", file=sys.stderr)
    os.write(1, b"PROBE-FD-STDOUT\\n")
    os.write(2, b"PROBE-FD-STDERR\\n")
    finding = _base_finding()
    finding["code"] = "ALPHA-PROBE"
    finding["message"] = "pid=%d" % os.getpid()
    return {"findings": [finding], "checked": 0, "profile": "strict"}


def noisy(_request, _resources):
    import os

    os.write(1, b"x" * NOISE_LENGTH_LITERAL)
    return {"findings": [], "checked": 0, "profile": "strict"}


def dual(_request, _resources):
    import os

    os.write(1, b"x" * NOISE_LENGTH_LITERAL)
    os.write(2, b"x" * NOISE_LENGTH_LITERAL)
    return {"findings": [], "checked": 0, "profile": "strict"}


def huge(_request, _resources):
    return {"findings": [], "checked": 0, "blob": "x" * OVERSIZE_LENGTH_LITERAL}


def slow(_request, _resources):
    import time

    time.sleep(HAZARD_SLEEP_LITERAL)
    return {"findings": [], "checked": 0, "profile": "strict"}


def medium(_request, _resources):
    import time

    # Written before the sleep and after it, so a caller can tell "this provider
    # never ran" from "this provider ran to completion" without timing anything.
    _sentinel("MEDIUM-STARTED")
    time.sleep(MEDIUM_SLEEP_LITERAL)
    _sentinel("MEDIUM-COMPLETED")
    _probe()
    return {"findings": [], "checked": 0, "profile": "strict"}


def stubborn(_request, _resources):
    import signal
    import time

    def _received(*_args):
        # Records the polite termination request and deliberately keeps running,
        # so only SIGKILL can end this process (ADR 0025).
        _sentinel("SIGTERM-RECEIVED")

    signal.signal(signal.SIGTERM, _received)
    signal.signal(signal.SIGINT, _received)
    # Strictly after both handlers are armed: its presence is what licenses a
    # caller to read a missing SIGTERM sentinel as "the polite signal was never
    # sent" rather than "the bound fired before this process could handle one".
    _sentinel("STUBBORN-ARMED")
    while True:
        time.sleep(0.05)


def ready(_request, _resources):
    import os
    import time

    _sentinel("WORKER-READY", str(os.getpid()))
    time.sleep(HAZARD_SLEEP_LITERAL)
    return {"findings": [], "checked": 0, "profile": "strict"}


def forker(_request, _resources):
    import os
    import time

    # The descendant inherits stdout, stderr, and the result descriptor, then
    # outlives its parent: only group termination can end it.
    child = os.fork()
    if child == 0:
        time.sleep(HAZARD_SLEEP_LITERAL)
        os._exit(0)
    _sentinel("FORKED-CHILD", str(child))
    time.sleep(HAZARD_SLEEP_LITERAL)
    return {"findings": [], "checked": 0, "profile": "strict"}


def forker_exit(_request, _resources):
    import os
    import time

    child = os.fork()
    if child == 0:
        time.sleep(HAZARD_SLEEP_LITERAL)
        os._exit(0)
    _sentinel("FORKED-CHILD", str(child))
    return {"findings": [], "checked": 0, "profile": "strict"}


def cooperative(_request, _resources):
    import os
    import signal
    import time

    def _received(*_args):
        # More than a pipe capacity: a parent that stopped reading during the
        # SIGTERM grace would block this handler and escalate to SIGKILL, so the
        # sentinel below would never be written.
        os.write(2, b"c" * 300000)
        _sentinel("COOPERATIVE-EXIT")
        os._exit(0)

    signal.signal(signal.SIGTERM, _received)
    # As with `stubborn`: armed first, announced second, so the caller can
    # distinguish a parent that stopped draining from a worker that was killed
    # before it had a handler at all.
    _sentinel("COOPERATIVE-ARMED")
    while True:
        time.sleep(0.05)


def unordered(_request, _resources):
    # Keys inserted by iterating a set: the insertion order is hash-seed
    # dependent and survives a JSON round trip, so it differs between worker
    # processes unless the service canonicalizes it.
    names = {"zeta", "alpha", "mu", "kappa", "beta", "omega", "iota", "sigma"}
    return {"findings": [], "checked": 0, "unordered": {name: 1 for name in names}}


def crash(_request, _resources):
    import os

    os._exit(9)
"""


def _digest(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def require_service_module(name: str) -> ModuleType:
    """Import one planned T4 service module through an in-test existence assertion.

    The plan's RED contract requires a missing planned symbol to fail as a
    collected assertion, never as a module import error, so no test module may
    import ``project_standards.mcp_services.providers`` at module scope.
    """
    qualified = f"project_standards.mcp_services.{name}"
    assert importlib.util.find_spec(qualified) is not None, (
        f"planned module {qualified} is absent; the T4 provider service does not exist yet"
    )
    return importlib.import_module(qualified)


def require_attribute(owner: object, name: str, label: str) -> Any:
    """Return one planned attribute, or fail as an explicit RED assertion."""
    assert hasattr(owner, name), (
        f"planned {label} {name} is absent; the T4 provider service does not exist yet"
    )
    return getattr(owner, name)


def require_operation(facade: object, name: str) -> Any:
    """Return one planned §5.5 facade operation, or fail as an explicit RED assertion."""
    assert hasattr(facade, name), (
        f"planned facade operation McpServiceFacade.{name} is absent; "
        "the T4 provider service does not exist yet"
    )
    return getattr(facade, name)


def require_dto(services: ModuleType, name: str) -> Any:
    """Return one planned §5.5 DTO from the public facade package surface."""
    assert hasattr(services, name), (
        f"planned DTO project_standards.mcp_services.{name} is absent from the public "
        "facade surface; the T4 provider service does not exist yet"
    )
    return getattr(services, name)


# ---------------------------------------------------------------------------
# Fixture construction
# ---------------------------------------------------------------------------

# id, operation, phase, effect, entrypoint symbol. Present in every tree so the
# composite tools always see the same declared surface.
_CLEAN_PROVIDERS: tuple[tuple[str, str, str, str, str], ...] = (
    ("validate-alpha", "validate", "validate", "findings", "validate"),
    ("verify-alpha", "verify", "verify", "findings", "verify"),
    ("lint-alpha", "lint", "validate", "findings", "lint"),
    ("drift-check-alpha", "drift-check", "validate", "findings", "drift_check"),
    ("fix-alpha", "fix", "authoring", "mutation-plan", "fix"),
    # A genuinely declared findings-effect provider that ADR 0025 nonetheless
    # excludes from the approved set (SPEC-RD01 OQ-006). Invoking it by its own
    # matching ID is what separates an operation allowlist from the dispatcher's
    # operation/declaration agreement check (T4.2 review F2).
    ("semantic-review-alpha", "semantic-review", "validate", "findings", "semantic_review"),
)

# behavior -> (provider id, operation, phase, effect, entrypoint symbol)
_HAZARD_PROVIDERS: dict[str, tuple[str, str, str, str, str]] = {
    "echo": ("echo-alpha", "validate", "validate", "findings", "echo"),
    "printer": ("printer-alpha", "validate", "validate", "findings", "printer"),
    "probe": ("probe-alpha", "validate", "validate", "findings", "probe"),
    "noisy": ("noisy-alpha", "validate", "validate", "findings", "noisy"),
    "dual": ("dual-alpha", "validate", "validate", "findings", "dual"),
    "huge": ("huge-alpha", "validate", "validate", "findings", "huge"),
    "slow": ("slow-alpha", "validate", "validate", "findings", "slow"),
    "medium": ("medium-alpha", "validate", "validate", "findings", "medium"),
    "stubborn": ("stubborn-alpha", "validate", "validate", "findings", "stubborn"),
    "ready": ("ready-alpha", "validate", "validate", "findings", "ready"),
    "crash": ("crash-alpha", "validate", "validate", "findings", "crash"),
    "forker": ("forker-alpha", "validate", "validate", "findings", "forker"),
    "forker-exit": ("forker-exit-alpha", "validate", "validate", "findings", "forker_exit"),
    "cooperative": ("cooperative-alpha", "validate", "validate", "findings", "cooperative"),
    "unordered": ("unordered-alpha", "validate", "validate", "findings", "unordered"),
}

MUTATION_SENTINEL = "MUTATING-PROVIDER-RAN"
SEMANTIC_SENTINEL = "SEMANTIC-REVIEW-RAN"
SIGTERM_SENTINEL = "SIGTERM-RECEIVED"
READY_SENTINEL = "WORKER-READY"
FORKED_SENTINEL = "FORKED-CHILD"
COOPERATIVE_SENTINEL = "COOPERATIVE-EXIT"

# "The worker reached the provider" sentinels. Each is written by its fixture at
# the exact point that makes the assertion after it meaningful — after a signal
# handler is armed, or before a sleep whose completion is the thing in question —
# so a bound that expired during interpreter start-up is distinguishable from the
# service defect the test exists to catch.
MEDIUM_STARTED_SENTINEL = "MEDIUM-STARTED"
MEDIUM_COMPLETED_SENTINEL = "MEDIUM-COMPLETED"
STUBBORN_ARMED_SENTINEL = "STUBBORN-ARMED"
COOPERATIVE_ARMED_SENTINEL = "COOPERATIVE-ARMED"

# Phrases a termination failure may never use. Killing a worker ends execution;
# it does not undo a write, and ADR 0025 buys fault isolation rather than
# rollback (T4.4 Codex GREEN review F1, disposition REJECT-AS-WRITTEN /
# ACCEPT-BOUNDED — the residual is queued as a T10 hardening candidate).
UNCHANGED_CLAIMS = (
    "was not modified",
    "were not modified",
    "unchanged",
    "no changes",
    "nothing was written",
    "left intact",
)


def _provider_block(provider_id: str, operation: str, phase: str, effect: str, symbol: str) -> str:
    return (
        "\n[[providers]]\n"
        f'id = "{provider_id}"\n'
        f'operation = "{operation}"\n'
        'kind = "python"\n'
        f'phase = "{phase}"\n'
        f'effect = "{effect}"\n'
        f'entrypoint = "payload:provider-code#{symbol}"\n'
        'input_schema = "provider-input"\n'
        'output_schema = "provider-output"\n'
        "resources = []\n"
    )


def _declared_aggregate(repository: Path, standard_id: str, version: str) -> str:
    family = tomllib.loads(
        (repository / "standards" / standard_id / "standard.toml").read_text(encoding="utf-8")
    )
    entries: list[dict[str, str]] = family["versions"]
    match = next(entry for entry in entries if entry["version"] == version)
    return match["digest"]


def _reseal(repository: Path, standard_id: str, version: str) -> None:
    """Re-authenticate one edited payload across all three digest sites.

    A payload's aggregate digest is recorded twice — in its family index and in
    the catalog generation — and both are compared, never recomputed, by the
    loaders. This mirrors the established reseal pattern at
    ``tests/test_installed_wrappers.py:81`` and
    ``tests/control_plane/test_config_edit.py:527``.
    """
    payload_dir = repository / "standards" / standard_id / "versions" / version
    manifest_path = payload_dir / "payload.toml"
    manifest = PayloadManifest.model_validate(
        tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    )
    old_aggregate = _declared_aggregate(repository, standard_id, version)
    aggregate = validate_payload_integrity(payload_dir, manifest).aggregate_digest.value
    for path in (
        repository / "standards" / standard_id / "standard.toml",
        repository / "catalogs/5.toml",
    ):
        path.write_text(
            path.read_text(encoding="utf-8").replace(old_aggregate, aggregate), encoding="utf-8"
        )


def build_provider_tree(tmp_path: Path, *, hazards: tuple[str, ...] = ()) -> Path:
    """Project the full fixture into an installed tree whose alpha 2.0 runs providers.

    The upstream fixture declares no validate/verify/lint/drift-check provider
    anywhere (only ``render``/``migrate``), so T4 cannot exercise its own
    contract without adding them. Nothing outside ``tmp_path`` is touched: the
    fixture is copied, alpha 2.0's existing ``provider-code`` resource gains new
    entrypoint symbols, the manifest gains matching declarations, and the payload
    is resealed.

    ``hazards`` adds deliberately hostile or instrumented providers used only by
    tests that call ``invoke_read_provider`` directly. They are opt-in because
    they declare ``validate`` operations, so a tree carrying them would also feed
    them to ``validate_repo``.
    """
    repository = tmp_path / "repository"
    shutil.copytree(FULL_FIXTURE / "standards", repository / "standards")
    shutil.copytree(FULL_FIXTURE / "catalogs", repository / "catalogs")

    payload_dir = repository / "standards" / SELECTED_STANDARD / "versions" / SELECTED_VERSION
    code_path = payload_dir / "provider.py"
    original = code_path.read_bytes()
    source = (
        _PROVIDER_SOURCE.replace("NOISE_LENGTH_LITERAL", str(NOISE_LENGTH))
        .replace("OVERSIZE_LENGTH_LITERAL", str(OVERSIZE_LENGTH))
        .replace("MEDIUM_SLEEP_LITERAL", str(MEDIUM_SLEEP_SECONDS))
        .replace("HAZARD_SLEEP_LITERAL", str(HAZARD_SLEEP_SECONDS))
    )
    code_path.write_text(original.decode("utf-8") + source, encoding="utf-8")

    manifest_path = payload_dir / "payload.toml"
    text = manifest_path.read_text(encoding="utf-8").replace(
        _digest(original), _digest(code_path.read_bytes())
    )
    for declaration in _CLEAN_PROVIDERS:
        text += _provider_block(*declaration)
    for behavior in hazards:
        text += _provider_block(*_HAZARD_PROVIDERS[behavior])
    manifest_path.write_text(text, encoding="utf-8")
    _reseal(repository, SELECTED_STANDARD, SELECTED_VERSION)

    # alpha 3.0 declares the same provider id with version-distinct bytes, so an
    # implementation that ignores the requested version cannot pass TC-T4-006.
    candidate_dir = repository / "standards" / SELECTED_STANDARD / "versions" / CANDIDATE_VERSION
    candidate_code = candidate_dir / "provider.py"
    candidate_original = candidate_code.read_bytes()
    candidate_code.write_text(
        candidate_original.decode("utf-8")
        + '\n\ndef validate(_request, _resources):\n    return {"findings": [], "checked": 30}\n',
        encoding="utf-8",
    )
    candidate_manifest = candidate_dir / "payload.toml"
    candidate_manifest.write_text(
        candidate_manifest.read_text(encoding="utf-8").replace(
            _digest(candidate_original), _digest(candidate_code.read_bytes())
        )
        + _provider_block("validate-alpha", "validate", "validate", "findings", "validate"),
        encoding="utf-8",
    )
    _reseal(repository, SELECTED_STANDARD, CANDIDATE_VERSION)

    package = repository / "src/project_standards"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    assert sync_payload_projection(repository, check=False) == ()
    installed = tmp_path / "installed/project_standards"
    shutil.copytree(package, installed)
    shutil.rmtree(repository)
    return installed


def build_provider_distribution(
    tmp_path: Path, *, hazards: tuple[str, ...] = ()
) -> InstalledDistribution:
    """Return one installed distribution whose alpha 2.0 declares runnable providers."""
    return InstalledDistribution(
        build_provider_tree(tmp_path, hazards=hazards), tool_release=TOOL_RELEASE
    )


def build_provider_repo(
    tmp_path: Path,
    name: str,
    *,
    distribution: InstalledDistribution,
    extension_content: str = "consumer = true\n",
) -> Path:
    """Initialize one consumer control plane with ``alpha`` enabled.

    ``extension_content`` varies the repository-relative referenced input alpha
    declares, so two repositories built from the same distribution differ in a
    fact only the *effective root* can supply (T4.2 review F1).
    """
    from project_standards.control_plane.bootstrap import initialize_control_plane
    from project_standards.control_plane.config_edit import set_standard_enabled

    repo = tmp_path / name
    repo.mkdir(parents=True)
    initialize_control_plane(repo, "5", distribution=distribution)
    extension = repo / EXTENSION_PATH
    extension.parent.mkdir(parents=True)
    extension.write_text(extension_content, encoding="utf-8")
    set_standard_enabled(repo, "alpha", True)
    return repo


def build_facade(services: ModuleType, distribution: InstalledDistribution) -> Any:
    return services.McpServiceFacade.from_installed(distribution, CatalogMajor("5"))


def payload_sentinel(distribution: InstalledDistribution, name: str) -> Path | None:
    """Return the payload-side sentinel one fixture provider writes, if it ran."""
    return next(iter(sorted(distribution.package_root.rglob(name))), None)


def clear_sentinels(distribution: InstalledDistribution, *names: str) -> None:
    """Remove the named sentinels so the next attempt observes only its own run."""
    for name in names:
        existing = payload_sentinel(distribution, name)
        if existing is not None:
            existing.unlink()


@dataclass(frozen=True)
class BoundedTermination:
    """One invocation the injected bound ended after its provider had started."""

    error: Any
    bound: float
    elapsed: float


def terminate_after_provider_starts(
    call: Callable[[], Any],
    *,
    services: ModuleType,
    providers: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    distribution: InstalledDistribution,
    started: str,
    clear: tuple[str, ...] = (),
) -> BoundedTermination:
    """Bound one hazard provider, escalating until the provider itself ran.

    Every caller here wants the same precondition and none of them can state it
    in seconds: the bound must expire while the *provider* is executing, but the
    same bound also covers the worker's interpreter start-up, whose cost varies
    by an order of magnitude with machine load (see the note beside
    ``FIRST_BOUND_SECONDS``). A fixed bound therefore encodes an assumption about
    the scheduler, and under gate parallelism that assumption is simply false.

    The precondition is instead *observed*: after each attempt the fixture's own
    ``started`` sentinel says whether the worker reached the provider, and the
    bound doubles until it did. Escalating cannot mask a service defect, because
    the property each caller asserts afterwards — SIGTERM before SIGKILL, a
    parent that keeps draining, a descendant that dies with its group — is
    unaffected by how long the bound was; only the guarantee that the provider
    was alive to exhibit it depends on this loop.

    ``clear`` names further sentinels this provider writes later in its life, so
    a retry cannot inherit an earlier attempt's evidence.
    """
    bound = FIRST_BOUND_SECONDS
    while True:
        clear_sentinels(distribution, started, *clear)
        monkeypatch.setattr(providers, "PROVIDER_TIMEOUT_SECONDS", bound)
        began = time.monotonic()
        with pytest.raises(services.ServiceError) as raised:
            call()
        elapsed = time.monotonic() - began
        if payload_sentinel(distribution, started) is not None:
            return BoundedTermination(raised.value, bound, elapsed)
        assert bound * 2 <= BOUND_CEILING_SECONDS, (
            f"no worker reached {started!r} within a {bound:.1f}s bound, so this machine "
            "cannot start a provider worker inside any bound this suite is willing to "
            "inject; the service was never exercised"
        )
        bound *= 2


def mutating_provider_ran(distribution: InstalledDistribution) -> bool:
    """Report whether a refused mutating/unapproved provider's bytes ever executed.

    The sentinels are written beside the payload rather than inside the consumer
    repository, so proving a refusal happened before dispatch never depends on
    the repository no-write assertions it is meant to be independent of.
    """
    return any(
        payload_sentinel(distribution, name) is not None
        for name in (MUTATION_SENTINEL, SEMANTIC_SENTINEL)
    )


def referenced_input_snapshot(repo: Path, **extra: Any) -> dict[str, Any]:
    """Build typed input that forces the dispatcher to read a root-relative file.

    ``referenced_inputs`` is the authoritative snapshot key
    (``control_plane/providers.py:134``): the dispatcher resolves each entry
    against the *effective root*, verifies its digest, and materializes its bytes
    into ``referenced_input_content``. A service that forwards a wrong root, a
    stale root, or an empty input cannot reproduce those bytes.
    """
    content = (repo / EXTENSION_PATH).read_bytes()
    return {
        "referenced_inputs": [
            {
                "standard_id": SELECTED_STANDARD,
                "extension_id": EXTENSION_ID,
                "path": EXTENSION_PATH,
                "digest": _digest(content),
            }
        ],
        **extra,
    }


# ---------------------------------------------------------------------------
# Authoritative oracles and shared assertions
# ---------------------------------------------------------------------------


def oracle_plan(repo: Path, distribution: InstalledDistribution) -> ReconciliationPlan:
    """Return the authoritative reconciliation plan for one repository."""
    return plan_reconciliation(build_planner_request(repo, distribution, frozenset()))


def oracle_selected(repo: Path, distribution: InstalledDistribution) -> SelectedCommandPackage:
    """Return the authoritative command selection for the enabled alpha package."""
    with selected_command(
        repo,
        SELECTED_STANDARD,
        distribution,
        mode=LockMode.READ,
        require_reconciled=False,
    ) as selected:
        assert selected is not None, "the fixture repository must have unified package authority"
        return selected


def oracle_dispatch(
    repo: Path,
    distribution: InstalledDistribution,
    *,
    standard_id: str,
    provider_id: str,
    operation: ProviderOperation,
    snapshots: dict[str, Any] | None = None,
) -> ProviderResult:
    """Invoke one provider through the authoritative in-process command path.

    This is the parity oracle: the same payload, the same resolved effective
    config, and the same dispatcher the CLI uses, so a worker result that
    differs by anything other than the declared normalization is a T4 defect.
    """
    with selected_command(
        repo,
        standard_id,
        distribution,
        mode=LockMode.READ,
        require_reconciled=False,
    ) as selected:
        assert selected is not None, "the fixture repository must have unified package authority"
        return invoke_selected_provider(
            selected, operation, snapshots or {}, provider_id=provider_id
        )


# ---------------------------------------------------------------------------
# T14: the real-packaged-provider path
# ---------------------------------------------------------------------------

# This repository is the consumer root for every T14 real-provider node. It is
# the only root that has the shipping Catalog 5 packages enabled, reconciled, and
# populated with real documents, and it is the root the T11 smoke discovery was
# made against. T15's own frozen equivalence node uses it for the same reason.
REAL_CONSUMER_ROOT = Path(__file__).resolve().parents[2]

# Which authority owns each shipping provider's typed input, read from the T14.1
# authoritative-site census (logs/T14.1.txt §3) rather than from the service under
# test or from the seam's own branch table:
#
# * `family` — the provider has a public command that dispatches it, and that
#   command's shape is authoritative: frontmatter/adr through
#   `frontmatter_commands`, project-spec through `specs/cli.py`, and all three
#   agent-handoff providers — INCLUDING `verify` — through `agent_handoff/cli.py`.
# * `plan-bound` — the provider has no public command at all and is
#   authoritatively dispatched only by the executor's post-apply verification.
# * `planner-owned` — the provider's only authoritative input is the pre-write
#   consumer-state snapshot the reconcile planner builds for a FRESH adoption
#   (`control_plane/planner.py::_validate_consumer_state` via
#   `provider_inputs.consumer_state_input`, issue #109). No other caller may
#   supply it: the planner deliberately skips an already-applied package so a
#   repository condition the pending apply did not create cannot become a new
#   steady-state gate failure, and the provider answers `{"findings": []}` when
#   the input is absent precisely so generic dispatch stays correct. Serving it
#   from the seam would make the MCP composite report findings the CLI does not
#   — the control-plane/service divergence T14 exists to prevent — so generic
#   dispatch IS the authority here, and the row below is what keeps that an
#   explicit declaration rather than a silent fallback.
#
# `agent-handoff/verify` is the row that makes this table an oracle rather than a
# restatement: the seam serves it under BOTH authorities (33 keys against 41), so
# a composite that reached for the plan-bound shape would still get an input and
# would still fail here.
AUTHORITATIVE_INPUT_OWNER: dict[tuple[str, str], str] = {
    ("adr", "validate-adr"): "family",
    ("agent-handoff", "validate"): "family",
    ("agent-handoff", "verify"): "family",
    ("agent-handoff", "drift-check"): "family",
    ("markdown-frontmatter", "validate-frontmatter"): "family",
    ("project-spec", "validate"): "family",
    ("project-spec", "lint"): "family",
    # github-workflow splits across both authorities rather than sitting in one:
    # `validate` and `drift-check` are family-served because their providers build
    # their entire answer from `snapshots`, so the generic empty input would report
    # every delivered artifact missing; `verify` has no public command at all and
    # stays with the executor's post-apply plan-bound snapshot, the same authority
    # the three rows below name.
    ("github-workflow", "validate"): "family",
    ("github-workflow", "drift-check"): "family",
    ("github-workflow", "verify"): "plan-bound",
    ("cli-documentation", "verify-workflow"): "plan-bound",
    ("markdown-tooling", "verify-format"): "plan-bound",
    ("markdown-tooling", "verify-lint"): "plan-bound",
    ("python-tooling", "verify-toolchain"): "plan-bound",
    ("python-tooling", "validate-consumer-state"): "planner-owned",
}

# The one owner class for which the composite's generic (empty) dispatch is the
# authoritative behavior; named so both the parity oracle and TC-T14-004 read the
# exemption from the census instead of restating a package id.
PLANNER_OWNED = "planner-owned"


# Generated, cached, and vendored trees a composite never reads and every other
# process on this machine writes to. Everything else — the whole consumer corpus
# the seam captures, the control plane the in-worker plan reads, and the sources
# beside them — is inside the digest.
_UNWATCHED_TREES = frozenset(
    {
        ".git",
        ".venv",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".workflow",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
    }
)

# Root-level files the coverage-instrumented gate itself creates and removes
# mid-run: xdist workers save `.coverage.<host>.<pid>.*` on exit while this
# digest may be sampling on another worker. The composite under test writes no
# coverage data, so excluding these cannot mask the write this digest guards.
# Applied at the root only — a `.coverage*`-named file deeper in the corpus
# (e.g. a future `.coveragerc` fixture) stays watched.
_UNWATCHED_FILE_PREFIX = ".coverage"


def real_tree_digest(root: Path) -> str:
    """Digest one real repository's inode facts, without reading its content.

    The bounded variant of ``tree_state`` for a root of this size: 12,149 entries
    in 0.28 s, against several minutes if every file's bytes were read. Mode,
    size, inode, and change time are what T4's own capture uses to catch a write
    that puts the original bytes back — an unprivileged process can restore
    neither ``st_ctime_ns`` nor an inode on demand.
    """
    digest = hashlib.sha256()
    for current, directories, files in os.walk(root, followlinks=False):
        directories[:] = sorted(item for item in directories if item not in _UNWATCHED_TREES)
        base = Path(current)
        if base == root / ".claude":
            # Agent worktrees are full transient checkouts inside the live
            # root — the same shared-mutable-state class as .workflow.
            directories[:] = [item for item in directories if item != "worktrees"]
        watched_files = (
            [item for item in files if not item.startswith(_UNWATCHED_FILE_PREFIX)]
            if base == root
            else list(files)
        )
        for name in sorted(watched_files) + list(directories):
            entry = base / name
            try:
                info = entry.lstat()
            except OSError:  # pragma: no cover - a racing external process
                continue
            digest.update(
                f"{entry.relative_to(root).as_posix()}|{info.st_mode}|{info.st_size}|"
                f"{info.st_ino}|{info.st_ctime_ns}|{info.st_mtime_ns}\n".encode()
            )
    return digest.hexdigest()


def real_packaged_distribution() -> InstalledDistribution:
    """Return the shipping distribution this repository dogfoods.

    Deliberately not a fixture projection. Every other composite node in this
    suite runs against synthetic `alpha` providers that ignore their input, which
    is exactly the masking that let empty-input dispatch look correct for three
    tasks; only real packaged providers reading a real corpus can fail the way the
    T11 smoke failed.
    """
    return InstalledDistribution.current()


def authoritative_direct_dispatch(
    repo: Path,
    distribution: InstalledDistribution,
    *,
    standard_id: str,
    provider_id: str,
    operation: ProviderOperation,
    owner: str,
) -> ProviderResult:
    """Dispatch one shipping provider in-process the way its own authority does.

    The parity oracle for TC-T14-001. Under worker-side construction the service
    never holds the built input at any observable boundary, so the comparison is
    over *consequences* — the findings and the declared output — against the same
    dispatcher the CLI and the executor use, fed the input the seam builds for the
    authority `AUTHORITATIVE_INPUT_OWNER` names.

    Calling the seam here is not the oracle importing its implementation: the seam
    is an independently frozen authority (TC-T15-001 proves it equals all four
    pre-existing in-site constructions against a test-owned reconstruction), and
    the code under test is `mcp_services` composite dispatch, which is a different
    module. What this oracle does NOT take from the implementation is the
    *routing* — which authority owns which provider — which is declared above.
    """
    with selected_command(
        repo,
        standard_id,
        distribution,
        mode=LockMode.READ,
        require_reconciled=False,
    ) as selected:
        assert selected is not None, f"{standard_id} must have unified package authority"
        snapshots: JsonObject
        if owner == PLANNER_OWNED:
            # Not a seam shape at all: the planner owns this provider's only
            # authoritative input and supplies it on fresh adoption only, so for
            # every other dispatcher — this composite included — the empty input
            # is what the authority sends.
            snapshots = {}
        elif owner == "family":
            snapshots = provider_dispatch_input(selected, operation, provider_id=provider_id)
        else:
            snapshots = provider_dispatch_input(
                None,
                operation,
                repo=repo,
                standard_id=standard_id,
                plan=oracle_plan(repo, distribution),
                provider_id=provider_id,
            )
        return invoke_selected_provider(selected, operation, snapshots, provider_id=provider_id)


def oracle_selection(
    repo: Path, distribution: InstalledDistribution, operations: frozenset[str]
) -> list[tuple[str, str, str, str]]:
    """Return the exact ordered identities T4 must dispatch, one per declaration.

    Derived from the authoritative resolution rather than from the fixture's own
    declarations, so a service that widens selection to unselected packages,
    non-consumer availability, or unapproved operations fails here. The result is
    a sorted *sequence*, so a duplicated dispatch fails on cardinality (T4.2
    review F3).
    """
    plan = oracle_plan(repo, distribution)
    selected: list[tuple[str, str, str, str]] = []
    payloads = {
        (payload.manifest.payload.standard, payload.manifest.payload.version.value): payload
        for payload in distribution.load_catalog(CatalogMajor("5")).payloads
    }
    for package in plan.resolution.packages:
        version = package.applied.resolved.value
        payload = payloads[(package.standard_id, version)]
        for declaration in payload.manifest.providers:
            if declaration.operation.value in operations:
                selected.append(
                    (package.standard_id, version, declaration.id, declaration.operation.value)
                )
    return sorted(selected)


def result_identity(result: Any) -> tuple[str, str, str, str]:
    return (result.standard_id, result.version, result.provider_id, result.operation)


def result_sequence(report: Any) -> list[tuple[str, str, str, str]]:
    return [result_identity(item) for item in report.results]


# The DR-003 field set, derived from the authoritative model rather than
# enumerated: `code` becomes `rule_id`, `hint` becomes `remediation`, and every
# other field — including one added to the control plane later — must survive.
MAPPED_FINDING_FIELDS = frozenset(
    {item.name for item in fields(ControlFinding)} - {"code", "hint"} | {"rule_id", "remediation"}
)


def mapped_finding(finding: ControlFinding) -> dict[str, Any]:
    """Project one authoritative finding onto the declared DR-003 field names."""
    projection = {item.name: getattr(finding, item.name) for item in fields(ControlFinding)}
    projection["rule_id"] = projection.pop("code")
    projection["remediation"] = projection.pop("hint")
    return projection


def published_finding(finding: Any) -> dict[str, Any]:
    """Project one published DTO finding onto the same DR-003 field set."""
    return {name: getattr(finding, name) for name in MAPPED_FINDING_FIELDS}


def tree_state(repo: Path) -> dict[str, tuple[int, int, int, int, str, bytes | None]]:
    """Capture inode, mode, change time, link target, and bytes for every entry.

    Extends the T3 capture with ``st_ino`` and ``st_ctime_ns`` (T4.2 review F17,
    orchestrator substitution for a filesystem-event watcher). Unprivileged code
    cannot restore a change time or reuse an inode on demand, so a service that
    rewrites, chmods, or replaces a file and then puts the original bytes back is
    still detected by the before/after comparison the plan names as the oracle.
    """
    captured: dict[str, tuple[int, int, int, int, str, bytes | None]] = {}
    for path in sorted(repo.rglob("*")):
        info = path.lstat()
        link = str(path.readlink()) if path.is_symlink() else ""
        content = path.read_bytes() if path.is_file() and not path.is_symlink() else None
        captured[path.relative_to(repo).as_posix()] = (
            stat.S_IFMT(info.st_mode),
            stat.S_IMODE(info.st_mode),
            info.st_ino,
            info.st_ctime_ns,
            link,
            content,
        )
    return captured


def open_descriptors() -> dict[int, str]:
    """Return this process's open descriptors mapped to their targets."""
    descriptors: dict[int, str] = {}
    for entry in sorted(Path("/proc/self/fd").iterdir(), key=lambda item: item.name):
        try:
            descriptors[int(entry.name)] = str(entry.readlink())
        except OSError:
            continue
    return descriptors


def child_processes() -> dict[int, str]:
    """Return every child of this process — running or zombie — described.

    Read from procfs rather than through ``os.waitpid(-1, os.WNOHANG)``, which is
    wrong here twice over (issue #147). It reports pid ``0`` when this process
    merely has a child that has not exited, which is indistinguishable in its
    return value from a real surviving worker; and it *reaps* whatever it finds,
    destroying an exit status that its actual owner — any other test sharing this
    xdist worker process — still has to collect. Procfs answers the question the
    confirmation clause actually asks, observes it without consuming it, and can
    name the survivor when there is one.

    A zombie is still listed as a child, so an unreaped worker is caught exactly
    as before; only the reaping side effect and the false pid ``0`` are gone.
    """
    children: dict[int, str] = {}
    for task in Path("/proc/self/task").iterdir():
        try:
            entries = (task / "children").read_text(encoding="utf-8").split()
        except OSError:  # pragma: no cover - the thread exited mid-scan
            continue
        for entry in entries:
            pid = int(entry)
            children[pid] = _describe_process(pid)
    return children


def _describe_process(pid: int) -> str:
    """Return one child's state letter and command line, for a failure message."""
    root = Path("/proc") / str(pid)
    try:
        state = root.joinpath("stat").read_text(encoding="utf-8").rpartition(") ")[2][:1]
    except OSError:  # pragma: no cover - the child was reaped mid-scan
        state = "?"
    try:
        command = (
            root.joinpath("cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        )
    except OSError:  # pragma: no cover - the child was reaped mid-scan
        command = ""
    return f"state={state or '?'} cmd={command.strip() or '<gone>'}"


def assert_no_unreaped_children() -> None:
    """Fail if any child process of this process survives the invocation."""
    surviving = child_processes()
    assert not surviving, "a worker process survived the invocation: " + ", ".join(
        f"pid {pid} ({description})" for pid, description in sorted(surviving.items())
    )


def worker_identity(result: Any) -> tuple[int, str]:
    """Return the (pid, executable) the provider reported from inside the worker."""
    match = PROBE_PATTERN.search(result.diagnostics)
    assert match is not None, (
        f"{result.provider_id} published no worker probe line; its file-descriptor "
        "output never crossed a process boundary"
    )
    return int(match.group(1)), match.group(2)


def assert_ran_in_worker(result: Any) -> None:
    """Assert one result was produced by a separate process on this interpreter."""
    pid, executable = worker_identity(result)
    assert pid != os.getpid(), (
        f"{result.provider_id} executed inside the service process (pid {pid})"
    )
    assert executable == sys.executable, (
        f"{result.provider_id} ran under {executable}, not the server interpreter"
    )


def assert_error_is_content_safe(
    error: Any,
    repo: Path,
    distribution: InstalledDistribution,
    *,
    forbidden: tuple[str, ...] = (),
    identified: bool = False,
) -> None:
    """Assert every public ServiceError field is structured, safe, and honest.

    T4.2 review F16: the consumer root is not the only secret — an absolute
    payload path from a worker traceback, or raw provider output, must not reach
    a caller through any public field either.

    T4.4 review F1: a termination failure may not claim the repository is
    unchanged, because terminating a worker does not undo a write. F10: a
    worker-boundary failure must say which selected package it belongs to.
    """
    assert isinstance(error.code, str) and error.code
    assert isinstance(error.message, str) and error.message
    assert isinstance(error.remediation, str) and error.remediation
    assert error.severity == "error"
    published = json.dumps(
        [
            error.code,
            error.message,
            error.remediation,
            error.standard_id,
            error.version,
            error.path,
            error.severity,
            str(error),
        ]
    )
    for secret in (str(repo.resolve()), str(distribution.package_root.resolve()), *forbidden):
        assert secret not in published, f"a structured failure published {secret!r}"
    if error.path is not None:
        assert not Path(error.path).is_absolute()
    lowered = f"{error.message} {error.remediation}".lower()
    for claim in UNCHANGED_CLAIMS:
        assert claim not in lowered, (
            f"a structured failure claimed {claim!r}; termination is not rollback"
        )
    if identified:
        assert error.standard_id == SELECTED_STANDARD
        assert error.version == SELECTED_VERSION


def assert_process_gone(pid: int, *, timeout: float = WATCHDOG_SECONDS) -> None:
    """Poll until one pid disappears, then require that it has.

    Already a behaviour-based wait, so the deadline is only a watchdog: it costs
    nothing when the process is gone immediately, which is the passing case, and
    a descendant that outlives its group is still sleeping for
    ``HAZARD_SLEEP_SECONDS`` when this gives up.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.05)
    raise AssertionError(f"process {pid} survived the invocation")


def assert_truncation_is_explicit(text: str, filler: str = NOISE_BYTE) -> None:
    """Assert a truncated stream carries a recognizable, quantified indication.

    T4.2 review F9: "any extra character" is not an oracle. The provider emits a
    single repeated character, so everything else in the returned text is
    service-authored; that residue must read as an indication (a word) and must
    quantify what was dropped (a number). The exact sentence stays unfrozen,
    because no binding document defines it.
    """
    marker = "".join(character for character in text if character != filler)
    assert re.search(r"[A-Za-z]{5,}", marker), (
        f"truncation carried no recognizable indication: {marker[:400]!r}"
    )
    assert re.search(r"[0-9]{4,}", marker), (
        f"truncation carried no omitted-byte information: {marker[:400]!r}"
    )


# ---------------------------------------------------------------------------
# TC-T4-001: validate/drift orchestration over the current exact resolution
# ---------------------------------------------------------------------------


def _unit_provider_selection(providers: ModuleType, kind: ProviderKind) -> Any:
    selection_type = require_attribute(providers, "_Selection", "qualified selection")
    declaration = ProviderDeclaration.model_validate(
        {
            "id": "validate-demo",
            "operation": "validate",
            "kind": kind.value,
            "phase": "validate",
            "effect": "findings",
            "entrypoint": (
                "payload:provider-code"
                if kind is ProviderKind.COMMAND
                else "payload:provider-code#validate"
            ),
            "input_schema": "provider-input",
            "output_schema": "provider-output",
            "resources": [],
            **(
                {"platforms": ["linux/amd64"], "mode": "0755"}
                if kind is ProviderKind.COMMAND
                else {}
            ),
        }
    )
    return selection_type(
        standard_id="demo",
        version="1.2",
        declaration=declaration,
    )


def _unit_distribution(root: Path) -> Any:
    return SimpleNamespace(
        package_root=root / "distribution",
        tool_release=SimpleNamespace(value="5.18.0"),
    )


def _unit_selected_package(root: Path, selection: Any) -> Any:
    return SimpleNamespace(
        repo=root,
        payload=SimpleNamespace(
            manifest=SimpleNamespace(
                payload=SimpleNamespace(standard=selection.standard_id),
                providers=[selection.declaration],
            )
        ),
        resolved=PackageVersion("1.2"),
        effective_config={"mode": "strict"},
    )


def _unit_provider_result() -> ProviderResult:
    return ProviderResult(
        ProviderEffect.FINDINGS,
        findings=(),
        structured_output={"findings": []},
    )


def _unexpected_call(message: str) -> Callable[..., Any]:
    def fail(*_args: object, **_kwargs: object) -> Any:
        raise AssertionError(message)

    return fail


def test_mcp_command_parent_preserves_single_provider_input_and_skips_python_worker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    providers = require_service_module("providers")
    selection = _unit_provider_selection(providers, ProviderKind.COMMAND)
    caller_input = {"caller": {"nested": ["unchanged"]}}
    invocations: list[Any] = []

    @contextmanager
    def selected(*_args: object, **_kwargs: object) -> Any:
        yield _unit_selected_package(tmp_path, selection)

    def direct(invocation: Any) -> ProviderResult:
        invocations.append(invocation)
        return _unit_provider_result()

    def nested(*_args: object, **_kwargs: object) -> Any:
        raise AssertionError("command dispatch entered the Python worker")

    monkeypatch.setattr(providers, "selected_command", selected, raising=False)
    monkeypatch.setattr(providers, "invoke_provider", direct, raising=False)
    monkeypatch.setattr(providers, "run_provider_subprocess", nested)

    result = providers._dispatch(
        _unit_distribution(tmp_path),
        tmp_path,
        selection,
        caller_input,
    )

    assert len(invocations) == 1
    assert invocations[0].snapshots is caller_input
    assert result.status == "completed"


def test_mcp_command_parent_runs_one_real_command_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    providers = require_service_module("providers")
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = command_payload(
        tmp_path / "payload",
        operation=ProviderOperation.VALIDATE,
        effect=ProviderEffect.FINDINGS,
    )
    declaration = payload.manifest.providers[0]
    selection_type = require_attribute(providers, "_Selection", "qualified selection")
    selection = selection_type(
        standard_id="demo",
        version="1.2",
        declaration=declaration,
    )
    qualified = SimpleNamespace(
        repo=repo,
        payload=payload,
        resolved=PackageVersion("1.2"),
        effective_config={"mode": "strict"},
    )

    @contextmanager
    def selected(*_args: object, **_kwargs: object) -> Any:
        yield qualified

    monkeypatch.setattr(providers, "selected_command", selected)
    monkeypatch.setattr(
        providers,
        "run_provider_subprocess",
        _unexpected_call("command dispatch created a Python worker"),
    )

    result = providers._dispatch(
        _unit_distribution(tmp_path),
        repo,
        selection,
        {"caller": "unchanged"},
    )

    assert result.status == "completed"
    assert result.findings == ()
    assert dumped(result)["output"] == {"findings": []}


@pytest.mark.parametrize(
    ("authority_input", "expected"),
    [
        ({"family": {"documents": ["README.md"]}}, {"family": {"documents": ["README.md"]}}),
        ({"plan_bound": {"verification": True}}, {"plan_bound": {"verification": True}}),
        (None, {}),
    ],
    ids=("family-first", "plan-bound", "generic-empty"),
)
def test_mcp_command_parent_uses_authoritative_composite_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    authority_input: dict[str, Any] | None,
    expected: dict[str, Any],
) -> None:
    providers = require_service_module("providers")
    selection = _unit_provider_selection(providers, ProviderKind.COMMAND)
    directive = {"directive": "must-not-reach-command"}
    invocations: list[Any] = []
    authority_calls: list[tuple[Any, ProviderOperation, str]] = []

    @contextmanager
    def selected(*_args: object, **_kwargs: object) -> Any:
        yield _unit_selected_package(tmp_path, selection)

    def authoritative(
        qualified: Any,
        operation: ProviderOperation,
        *,
        provider_id: str,
        planner_runner: Any,
    ) -> dict[str, Any] | None:
        assert planner_runner is providers.invoke_provider
        authority_calls.append((qualified, operation, provider_id))
        return authority_input

    def direct(invocation: Any) -> ProviderResult:
        invocations.append(invocation)
        return _unit_provider_result()

    monkeypatch.setattr(providers, "selected_command", selected, raising=False)
    monkeypatch.setattr(
        providers,
        "authoritative_provider_input",
        authoritative,
        raising=False,
    )
    monkeypatch.setattr(providers, "invoke_provider", direct, raising=False)
    monkeypatch.setattr(
        providers,
        "run_provider_subprocess",
        _unexpected_call("command dispatch entered the Python worker"),
    )

    providers._dispatch(
        _unit_distribution(tmp_path),
        tmp_path,
        selection,
        directive,
        input_authority=providers.SEAM_AUTHORITY,
    )

    assert [(operation, provider_id) for _, operation, provider_id in authority_calls] == [
        (ProviderOperation.VALIDATE, "validate-demo")
    ]
    assert invocations[0].snapshots == expected
    assert invocations[0].snapshots is not directive


def test_mcp_command_parent_keeps_authority_failure_isolated_per_composite_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    providers = require_service_module("providers")
    selection = _unit_provider_selection(providers, ProviderKind.COMMAND)

    @contextmanager
    def selected(*_args: object, **_kwargs: object) -> Any:
        yield _unit_selected_package(tmp_path, selection)

    def fail_authority(*_args: object, **_kwargs: object) -> Any:
        raise ValueError("private authority detail")

    monkeypatch.setattr(providers, "selected_command", selected, raising=False)
    monkeypatch.setattr(
        providers,
        "authoritative_provider_input",
        fail_authority,
        raising=False,
    )
    monkeypatch.setattr(
        providers,
        "invoke_provider",
        _unexpected_call("authority failure executed command bytes"),
        raising=False,
    )

    result = providers._composite_dispatch(
        _unit_distribution(tmp_path),
        tmp_path,
        selection,
    )

    assert result.status == "control-plane-unavailable"
    assert result.findings == ()
    assert "private authority detail" not in result.diagnostics


def test_python_provider_stays_on_existing_mcp_worker_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    providers = require_service_module("providers")
    selection = _unit_provider_selection(providers, ProviderKind.PYTHON)
    requests: list[dict[str, Any]] = []

    def worker(
        argv: tuple[str, ...],
        request: bytes,
        **_kwargs: object,
    ) -> provider_subprocess.ProviderSubprocessOutcome:
        requests.append(json.loads(request))
        assert argv == provider_subprocess.python_worker_argv()
        return provider_subprocess.ProviderSubprocessOutcome(
            {
                "status": "ok",
                "effect": "findings",
                "output": {"findings": []},
                "output_notice": None,
                "findings": [],
            },
            provider_subprocess.CapturedStream("stdout", 8192),
            provider_subprocess.CapturedStream("stderr", 8192),
        )

    monkeypatch.setattr(providers, "run_provider_subprocess", worker)
    monkeypatch.setattr(
        providers,
        "invoke_provider",
        _unexpected_call("Python provider bypassed its worker"),
        raising=False,
    )

    result = providers._dispatch(
        _unit_distribution(tmp_path),
        tmp_path,
        selection,
        {"caller": "input"},
    )

    assert len(requests) == 1
    assert requests[0]["provider_input"] == {"caller": "input"}
    assert result.status == "completed"


def test_go_command_fixture_runs_real_mcp_routes_with_one_child_per_invocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    services = import_mcp_services()
    distribution = command_provider_distribution(tmp_path)
    repo = initialize_command_provider_repo(tmp_path, distribution)
    reconcile_command_provider_repo(repo, distribution)
    facade = build_facade(services, distribution)
    real_popen = provider_subprocess.subprocess.Popen
    spawned: list[tuple[object, ...]] = []

    def counted_popen(*args: Any, **kwargs: Any) -> Any:
        spawned.append(args)
        return real_popen(*args, **kwargs)

    monkeypatch.setattr(provider_subprocess.subprocess, "Popen", counted_popen)

    expected_resource = base64.b64encode(COMMAND_FIXTURE_RESOURCE).decode("ascii")
    rendered_content = b"command-provider-fixture|render|" + COMMAND_FIXTURE_RESOURCE
    rendered_digest = f"sha256:{hashlib.sha256(rendered_content).hexdigest()}"
    rendered_target = ".standards/command-provider-fixture.txt"

    direct = require_operation(facade, "invoke_read_provider")(
        repo,
        standard_id=COMMAND_FIXTURE_STANDARD,
        version=COMMAND_FIXTURE_VERSION,
        provider_id="validate-fixture",
        operation="validate",
        provider_input={"mcp": {"nested": ["unchanged"]}},
    )
    assert len(spawned) == 1
    direct_output = dumped(direct)["output"]
    assert direct_output["observed"]["snapshots"] == {"mcp": {"nested": ["unchanged"]}}
    assert direct_output["observed"]["resource_base64"] == expected_resource
    assert direct_output["observed"]["environment"] == []

    before_validate = len(spawned)
    validation = require_operation(facade, "validate_repo")(repo)
    validation_results = {item.provider_id: dumped(item) for item in validation.results}
    assert set(validation_results) == {
        "validate-fixture",
        "verify-fixture",
    }
    assert {item["status"] for item in validation_results.values()} == {"completed"}
    validate_observed = validation_results["validate-fixture"]["output"]["observed"]
    assert validate_observed["operation"] == "validate"
    assert validate_observed["resource_base64"] == expected_resource
    assert validate_observed["environment"] == []
    verify_observed = validation_results["verify-fixture"]["output"]["observed"]
    assert verify_observed["operation"] == "verify"
    assert verify_observed["resource_base64"] == expected_resource
    assert verify_observed["environment"] == []
    assert verify_observed["snapshots"][rendered_target] == {
        "content_base64": base64.b64encode(rendered_content).decode("ascii"),
        "content_digest": rendered_digest,
        "kind": "regular",
        "mode": "0644",
    }
    # Verify input is plan-bound: render-fixture runs as its own command child
    # before verify-fixture, so provider invocations exceed reported results by one.
    assert len(spawned) - before_validate == len(validation.results) + 1

    before_drift = len(spawned)
    drift = require_operation(facade, "drift_check")(repo)
    drift_result = dumped(drift.results[0])
    assert drift_result["provider_id"] == "drift-check-fixture"
    assert drift_result["status"] == "completed"
    drift_observed = drift_result["output"]["observed"]
    assert drift_observed["operation"] == "drift-check"
    assert drift_observed["resource_base64"] == expected_resource
    assert drift_observed["environment"] == []
    assert [
        (action["kind"], action["target"], action["after_digest"])
        for action in dumped(drift)["actions"]
    ] == [("no-op", rendered_target, rendered_digest)]
    # Drift publishes the plan and target provider separately: render-fixture
    # runs while planning, but only drift-check-fixture appears in the results.
    assert len(spawned) - before_drift == len(drift.results) + 1
    assert_no_unreaped_children()


def test_validate_repo_selects_applicable_exact_providers(tmp_path: Path) -> None:
    """TC-T4-001: only resolved validate/verify/lint declarations, typed and ordered."""
    services = import_mcp_services()
    distribution = build_provider_distribution(tmp_path)
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)

    validate_repo = require_operation(facade, "validate_repo")
    report = validate_repo(repo)

    # The complete ordered sequence, including cardinality: a service that
    # dispatches an applicable provider twice fails here (T4.2 review F3). The
    # order is the DR-009 documented key T2 already uses for
    # StandardDescriptor.providers.
    expected = oracle_selection(repo, distribution, frozenset({"validate", "verify", "lint"}))
    assert result_sequence(report) == expected
    assert expected, "the fixture must resolve at least one applicable provider"

    # Drift-check and semantic-review are separate surfaces and must not leak in.
    assert all(item.operation in {"validate", "verify", "lint"} for item in report.results)
    # Unselected packages contribute nothing: beta is reference-only, gamma is
    # internal, and alpha 3.0 is the candidate version the resolution rejected.
    assert all(item.standard_id == SELECTED_STANDARD for item in report.results)
    assert all(item.version == SELECTED_VERSION for item in report.results)
    assert result_sequence(validate_repo(repo)) == expected

    # Every composite dispatch really crossed a process boundary (review F6).
    for item in report.results:
        assert_ran_in_worker(item)

    assert report.repo_root == "."
    assert dumped(report)["repo_root"] == "."
    assert report.findings == tuple(finding for item in report.results for finding in item.findings)
    assert report.findings, "the fixture validate provider must publish a finding"
    assert not mutating_provider_ran(distribution)


def test_validate_repo_reloads_the_current_resolution_between_calls(tmp_path: Path) -> None:
    """TC-T4-001: selection follows the live control plane, not facade construction."""
    from project_standards.control_plane.config_edit import set_standard_enabled

    services = import_mcp_services()
    distribution = build_provider_distribution(tmp_path)
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)

    validate_repo = require_operation(facade, "validate_repo")
    assert validate_repo(repo).results, "alpha must be selected while enabled"

    set_standard_enabled(repo, "alpha", False)
    assert oracle_selection(repo, distribution, frozenset({"validate", "verify", "lint"})) == []
    assert validate_repo(repo).results == ()


def test_drift_check_preserves_reconciliation_and_typed_provider_results(tmp_path: Path) -> None:
    """TC-T4-001: authoritative reconciliation facts plus drift-check results, no summary."""
    services = import_mcp_services()
    distribution = build_provider_distribution(tmp_path)
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    # Without this the plan carries no findings at all and "preserves
    # authoritative findings" would be a vacuous assertion over an empty tuple
    # (T4.2 review F4).
    plant_reconciliation_finding(repo, distribution)

    drift_check = require_operation(facade, "drift_check")
    report = drift_check(repo)

    plan = oracle_plan(repo, distribution)
    public = plan.to_jsonable()
    assert public["findings"], (
        "the fixture must produce at least one authoritative reconciliation finding"
    )
    assert report.reconciliation_fingerprint == reconciliation_fingerprint(plan)
    assert json.dumps(dumped(report)["actions"], sort_keys=True) == json.dumps(
        public["actions"], sort_keys=True
    )
    assert json.dumps(dumped(report)["findings"], sort_keys=True) == json.dumps(
        public["findings"], sort_keys=True
    )

    expected = oracle_selection(repo, distribution, frozenset({"drift-check"}))
    assert result_sequence(report) == expected
    assert expected, "the fixture must resolve a drift-check provider"
    for item in report.results:
        assert_ran_in_worker(item)
    assert report.repo_root == "."
    assert dumped(report)["repo_root"] == "."

    # No invented confidence, relevance, or clean-state boolean: §5.5 forbids a
    # synthesized summary, and every reported fact must trace to an authority.
    projection = dumped(report)
    assert not [name for name, value in projection.items() if isinstance(value, bool)]
    assert field_names(type(report)) == {
        "repo_root",
        "reconciliation_fingerprint",
        "actions",
        "findings",
        "results",
    }


def test_drift_check__create_only_stale_advisory__is_stable_and_read_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tests.control_plane.planner_helpers import stale_create_only_plan

    providers = require_service_module("providers")
    distribution = build_provider_distribution(tmp_path / "distribution")
    repo, _request, plan = stale_create_only_plan(tmp_path / "consumer-fixture")
    before = {
        path.relative_to(repo).as_posix(): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file()
    }

    def planned(
        _distribution: InstalledDistribution,
        _root: Path,
    ) -> ReconciliationPlan:
        return plan

    def no_selection(
        _distribution: InstalledDistribution,
        _root: Path,
    ) -> dict[str, tuple[str, InstalledPayload]]:
        return {}

    monkeypatch.setattr(providers, "_plan", planned)
    monkeypatch.setattr(providers, "_resolved_selection", no_selection)

    first = providers.drift_check(distribution, repo)
    second = providers.drift_check(distribution, repo)

    assert dumped(first) == dumped(second)
    [finding] = [
        item for item in dumped(first)["findings"] if item["code"] == "CP-CREATE-ONLY-STALE"
    ]
    assert finding["severity"] == "warning"
    assert finding["standard_id"] == "demo"
    assert finding["version"] == "2.0"
    assert finding["path"] == "usage.md"
    assert finding["identity"] == "$file"
    assert "1.0 instead of selected version 2.0" in finding["message"]
    assert "old usage" not in json.dumps(dumped(first))
    assert json.dumps(dumped(first)["actions"], sort_keys=True) == json.dumps(
        plan.to_jsonable()["actions"], sort_keys=True
    )
    assert {
        path.relative_to(repo).as_posix(): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file()
    } == before


# ---------------------------------------------------------------------------
# TC-T4-001: typed input, effective configuration, and effective-root forwarding
# ---------------------------------------------------------------------------


def test_typed_input_effective_config_and_root_are_forwarded(tmp_path: Path) -> None:
    """TC-T4-001 (FR-012, IR-009): the worker receives the real root, config, and input."""
    services = import_mcp_services()
    distribution = build_provider_distribution(tmp_path, hazards=("echo",))
    facade = build_facade(services, distribution)
    invoke = require_operation(facade, "invoke_read_provider")

    # Two repositories from one distribution, differing only in the bytes of the
    # declared repository-relative referenced input.
    first = build_provider_repo(
        tmp_path, "first", distribution=distribution, extension_content="nonce = 1\n"
    )
    second = build_provider_repo(
        tmp_path, "second", distribution=distribution, extension_content="nonce = 2222\n"
    )

    echoed: dict[str, bytes] = {}
    for label, repo in (("first", first), ("second", second)):
        nonce = f"nonce-{label}"
        result = invoke(
            repo,
            standard_id=SELECTED_STANDARD,
            version=SELECTED_VERSION,
            provider_id="echo-alpha",
            operation="validate",
            provider_input=referenced_input_snapshot(repo, nonce=nonce),
        )
        assert_ran_in_worker(result)
        output = dumped(result)["output"]

        # Typed input arrives intact, nested keys included.
        assert output["echo_snapshots"]["nonce"] == nonce
        assert result.findings[0].message == f"nonce={nonce}"
        # Exact identity reaches the dispatcher, not a default.
        assert output["echo_identity"] == [SELECTED_STANDARD, SELECTED_VERSION, "validate"]
        # The selected effective configuration is the authoritative one.
        assert output["echo_config"] == oracle_selected(repo, distribution).effective_config
        assert output["echo_config"][EXTENSION_OPTION] == EXTENSION_PATH
        # Root-derived bytes: only the correct effective root can produce these.
        materialized = output["echo_snapshots"]["referenced_input_content"]
        assert len(materialized) == 1
        echoed[label] = base64.b64decode(materialized[0]["content_base64"])
        assert echoed[label] == (repo / EXTENSION_PATH).read_bytes()

    assert echoed["first"] != echoed["second"], (
        "both repositories produced identical referenced-input bytes; the effective "
        "root was not forwarded"
    )


def test_absolute_provider_finding_paths_are_published_root_relative(tmp_path: Path) -> None:
    """TC-T4-004 (DR-003): a root path is normalized to a stable root-relative path."""
    services = import_mcp_services()
    distribution = build_provider_distribution(tmp_path, hazards=("echo",))
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    invoke = require_operation(facade, "invoke_read_provider")

    absolute = str((repo / "README.md").resolve())
    provider_input = referenced_input_snapshot(repo, nonce="abs", echo_path=absolute)
    oracle = oracle_dispatch(
        repo,
        distribution,
        standard_id=SELECTED_STANDARD,
        provider_id="echo-alpha",
        operation=ProviderOperation.VALIDATE,
        snapshots=dict(provider_input),
    )
    assert oracle.findings[0].path == absolute, (
        "the fixture must hand the service an absolute in-root path to normalize"
    )

    result = invoke(
        repo,
        standard_id=SELECTED_STANDARD,
        version=SELECTED_VERSION,
        provider_id="echo-alpha",
        operation="validate",
        provider_input=provider_input,
    )
    published = result.findings[0]
    assert not Path(published.path).is_absolute()
    assert published.path == "README.md"
    # Scoped to the published finding on purpose: `output` is the provider's own
    # declared output, which §5.5 requires verbatim, and this test planted the
    # absolute root inside it through typed input. Envelope-wide root absence is
    # asserted where nothing plants one — see
    # test_finding_model_requires_every_declared_field.
    assert str(repo.resolve()) not in json.dumps(dumped(published))


# ---------------------------------------------------------------------------
# TC-T4-003: bounded, fingerprint-neutral diagnostics
# ---------------------------------------------------------------------------


def test_provider_diagnostics_are_bounded_and_fingerprint_neutral(tmp_path: Path) -> None:
    """TC-T4-003 (DR-008): diagnostics are capped, marked when cut, and never identity."""
    services = import_mcp_services()
    distribution = build_provider_distribution(tmp_path, hazards=("noisy", "dual"))
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)

    invoke = require_operation(facade, "invoke_read_provider")

    def noisy_call(provider_id: str) -> Any:
        return invoke(
            repo,
            standard_id=SELECTED_STANDARD,
            version=SELECTED_VERSION,
            provider_id=provider_id,
            operation="validate",
            provider_input={},
        )

    # One stream and both streams: a cap applied per stream still lets a
    # dual-stream provider double the envelope (T4.2 review F8).
    for provider_id, emitted in (("noisy-alpha", NOISE_LENGTH), ("dual-alpha", 2 * NOISE_LENGTH)):
        result = noisy_call(provider_id)
        diagnostics = result.diagnostics
        assert isinstance(diagnostics, str)
        assert len(diagnostics) < emitted, (
            f"{provider_id} pushed {emitted} bytes across IPC unbounded"
        )
        assert NOISE_BYTE in diagnostics, "the bounded prefix of the provider output must survive"
        assert_truncation_is_explicit(diagnostics)
        # The whole serialized envelope is bounded, not just this one field.
        assert len(json.dumps(dumped(result))) < emitted
        assert diagnostics == noisy_call(provider_id).diagnostics

    # DR-008: raw diagnostics are supplemental text and never participate in an
    # identity. The drift provider emits pid- and clock-dependent bytes, so two
    # calls differ in diagnostics while the reconciliation identity is stable.
    drift_check = require_operation(facade, "drift_check")
    first = drift_check(repo)
    second = drift_check(repo)
    pairs = [
        (a.diagnostics, b.diagnostics) for a, b in zip(first.results, second.results, strict=True)
    ]
    assert any(a != b for a, b in pairs), (
        "the drift fixture must produce per-call diagnostics for this proof to bind"
    )
    assert first.reconciliation_fingerprint == second.reconciliation_fingerprint
    assert first.reconciliation_fingerprint == reconciliation_fingerprint(
        oracle_plan(repo, distribution)
    )
    for text, _ in pairs:
        assert text not in first.reconciliation_fingerprint


def test_oversized_structured_output_cannot_cross_ipc_unbounded(tmp_path: Path) -> None:
    """TC-T4-003 (DR-008, ADR 0025): the result envelope itself is bounded and marked."""
    services = import_mcp_services()
    distribution = build_provider_distribution(tmp_path, hazards=("huge",))
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    invoke = require_operation(facade, "invoke_read_provider")

    before = tree_state(repo)
    try:
        result = invoke(
            repo,
            standard_id=SELECTED_STANDARD,
            version=SELECTED_VERSION,
            provider_id="huge-alpha",
            operation="validate",
            provider_input={},
        )
    except services.ServiceError as error:
        # A bounded, schema-preserving structured failure is the other approved
        # outcome; it may not carry the payload it refused to transport.
        assert_error_is_content_safe(error, repo, distribution)
        assert len(error.message) < OVERSIZE_LENGTH // 100
        assert NOISE_BYTE * 1000 not in error.message
    else:
        serialized = json.dumps(dumped(result))
        assert len(serialized) < OVERSIZE_LENGTH, "an unbounded result crossed the IPC boundary"
        assert_truncation_is_explicit(serialized)
    assert tree_state(repo) == before
    assert_no_unreaped_children()


# ---------------------------------------------------------------------------
# TC-T4-004: every DR-003 finding field
# ---------------------------------------------------------------------------


def test_finding_model_requires_every_declared_field(tmp_path: Path) -> None:
    """TC-T4-004 (DR-003): the provider finding mapping drops no authoritative field."""
    services = import_mcp_services()
    distribution = build_provider_distribution(tmp_path)
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    finding_type = require_dto(services, "Finding")

    # Derived, not enumerated: a control-plane finding field added later must
    # appear on the DTO instead of being silently dropped.
    declared = {item.name for item in fields(ControlFinding)} - {"code", "hint"}
    assert field_names(finding_type) == declared | {"rule_id", "remediation"}

    invoke = require_operation(facade, "invoke_read_provider")
    result = invoke(
        repo,
        standard_id=SELECTED_STANDARD,
        version=SELECTED_VERSION,
        provider_id="validate-alpha",
        operation="validate",
        provider_input={},
    )
    oracle = oracle_dispatch(
        repo,
        distribution,
        standard_id=SELECTED_STANDARD,
        provider_id="validate-alpha",
        operation=ProviderOperation.VALIDATE,
    )
    assert len(oracle.findings) == 1
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert isinstance(finding, finding_type)
    assert published_finding(finding) == mapped_finding(oracle.findings[0])

    # Identity fields are stamped by the dispatcher from the invocation, so a
    # service that forwards a provider-declared identity instead would diverge.
    assert finding.standard_id == SELECTED_STANDARD
    assert finding.version == SELECTED_VERSION
    assert finding.rule_id == "ALPHA-VALIDATE"
    assert finding.remediation == "edit README.md"
    assert (finding.line, finding.column, finding.locus) == (12, 7, "document heading")
    assert (finding.observed, finding.limit) == (191, 160)

    # Stable root-relative paths: no absolute path and no consumer/distribution
    # root may appear anywhere in a published finding.
    validate_repo = require_operation(facade, "validate_repo")
    drift_check = require_operation(facade, "drift_check")
    published = [*validate_repo(repo).findings, *result.findings]
    for item in drift_check(repo).results:
        published.extend(item.findings)
    assert published
    for item in published:
        assert not Path(item.path).is_absolute()
        serialized = json.dumps(dumped(item))
        assert str(repo.resolve()) not in serialized
        assert str(distribution.package_root.resolve()) not in serialized


# ---------------------------------------------------------------------------
# TC-T4-005: the ADR 0025 execution bound, termination, and cancellation
# ---------------------------------------------------------------------------


def test_slow_provider_returns_bounded_diagnostic_and_worker_is_reaped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TC-T4-005: the approved bound decides termination, and SIGTERM precedes SIGKILL.

    The bound is proven *bidirectionally* through the same seam (T4.2 review
    F10): one provider of known duration must succeed when the bound exceeds it
    and time out when the bound is below it, so an implementation whose real
    bound is some other number fails one of the two directions. The shipped value
    is separately asserted against the ADR, which keeps the suite off a literal
    30-second wait (plan sub-task T4.4).

    Both directions are read off the fixture's own sentinels rather than off the
    clock (issue #147). "It completed" is the completion sentinel and a result;
    "it was terminated" is a structured failure with that sentinel *absent*. Those
    are the facts the ADR bound is about, and unlike an elapsed-time comparison
    they cannot be flipped by a loaded machine — the previous form compared
    elapsed time against the provider's own 3-second sleep, a margin smaller than
    the worker start-up cost this suite sees under gate parallelism.
    """
    services = import_mcp_services()
    providers = require_service_module("providers")
    bound = require_attribute(providers, "PROVIDER_TIMEOUT_SECONDS", "T4 module constant")
    assert bound == ADR_TIMEOUT_SECONDS

    distribution = build_provider_distribution(tmp_path, hazards=("medium", "slow", "stubborn"))
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    invoke = require_operation(facade, "invoke_read_provider")

    def call(provider_id: str) -> Any:
        return invoke(
            repo,
            standard_id=SELECTED_STANDARD,
            version=SELECTED_VERSION,
            provider_id=provider_id,
            operation="validate",
            provider_input={},
        )

    before = tree_state(repo)

    # Above the provider's duration: it completes, so the effective bound is not
    # some smaller hidden constant. The bound is generous because its *size* is
    # not the claim — that it exceeds the provider's duration is — and a bound
    # only a few seconds clear of the provider is a bound the worker's own
    # start-up can consume on a loaded machine.
    monkeypatch.setattr(
        providers, "PROVIDER_TIMEOUT_SECONDS", MEDIUM_SLEEP_SECONDS + BOUND_CEILING_SECONDS
    )
    started = time.monotonic()
    completed = call("medium-alpha")
    elapsed = time.monotonic() - started
    assert elapsed >= MEDIUM_SLEEP_SECONDS
    assert elapsed < WATCHDOG_SECONDS
    assert payload_sentinel(distribution, MEDIUM_COMPLETED_SENTINEL) is not None, (
        "the provider returned without reaching the end of its own body"
    )
    assert_ran_in_worker(completed)

    # Below it: the same provider is terminated, so the effective bound is not
    # some larger hidden constant either. A bound the provider outlives can only
    # end this call by expiring, and the absent completion sentinel is what says
    # the provider did not simply finish first.
    clear_sentinels(distribution, MEDIUM_STARTED_SENTINEL, MEDIUM_COMPLETED_SENTINEL)
    monkeypatch.setattr(providers, "PROVIDER_TIMEOUT_SECONDS", 1.0)
    started = time.monotonic()
    with pytest.raises(services.ServiceError) as raised:
        call("medium-alpha")
    assert time.monotonic() - started < WATCHDOG_SECONDS
    assert payload_sentinel(distribution, MEDIUM_COMPLETED_SENTINEL) is None, (
        "the injected bound did not decide termination; the provider ran to completion"
    )
    assert_error_is_content_safe(raised.value, repo, distribution)

    # A provider that never returns: bounded at all is the whole claim, and it
    # sleeps far longer than this watchdog, so returning proves the service ended
    # it rather than waiting it out.
    monkeypatch.setattr(providers, "PROVIDER_TIMEOUT_SECONDS", FIRST_BOUND_SECONDS)
    started = time.monotonic()
    with pytest.raises(services.ServiceError) as raised:
        call("slow-alpha")
    assert time.monotonic() - started < WATCHDOG_SECONDS, "slow-alpha was not bounded"
    assert_error_is_content_safe(raised.value, repo, distribution)

    # One that refuses SIGTERM: the sentinel proves the polite signal was
    # delivered first and forced termination followed (ADR 0025; T4.2 review
    # F11). Its bound is escalated until the fixture reports its handlers armed,
    # so a missing SIGTERM sentinel can only mean the signal was never sent.
    stubborn = terminate_after_provider_starts(
        lambda: call("stubborn-alpha"),
        services=services,
        providers=providers,
        monkeypatch=monkeypatch,
        distribution=distribution,
        started=STUBBORN_ARMED_SENTINEL,
        clear=(SIGTERM_SENTINEL,),
    )
    assert stubborn.elapsed < WATCHDOG_SECONDS, "stubborn-alpha was not bounded"
    assert_error_is_content_safe(stubborn.error, repo, distribution)

    assert payload_sentinel(distribution, SIGTERM_SENTINEL) is not None, (
        "the stubborn worker was killed without first receiving SIGTERM"
    )
    assert tree_state(repo) == before
    assert_no_unreaped_children()


def test_cancelled_invocation_terminates_and_releases_the_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TC-T4-005 (plan §8 T4, "timeout or cancellation"): interruption cleans up fully.

    The facade is synchronous, so cancellation is a parent-side interruption of
    the wait rather than an invented async API (T4.2 review F12, disposition
    ACCEPT-AMENDED). The worker announces its pid through a payload-side sentinel
    before sleeping, so the test can prove the exact process is gone.

    Cancellation has to arrive while the worker is *running the provider*, and
    the interval that guarantees that is a property of the machine rather than a
    constant (issue #147): a cold worker takes a few tenths of a second to reach
    its provider when idle and seconds when the gate is saturated. The interval
    is therefore doubled until the fixture's own pid sentinel proves the worker
    got there, exactly as the bounded-termination proofs escalate their bound.
    """
    import signal

    services = import_mcp_services()
    providers = require_service_module("providers")
    distribution = build_provider_distribution(tmp_path, hazards=("ready",))
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    invoke = require_operation(facade, "invoke_read_provider")
    monkeypatch.setattr(providers, "PROVIDER_TIMEOUT_SECONDS", float(HAZARD_SLEEP_SECONDS))

    before = tree_state(repo)
    descriptors = open_descriptors()

    def interrupt(*_args: object) -> None:
        raise KeyboardInterrupt("cancelled")

    def cancel_after(interval: float) -> Any:
        clear_sentinels(distribution, READY_SENTINEL)
        previous = signal.signal(signal.SIGALRM, interrupt)
        try:
            signal.setitimer(signal.ITIMER_REAL, interval)
            with pytest.raises(services.ServiceError) as raised:
                invoke(
                    repo,
                    standard_id=SELECTED_STANDARD,
                    version=SELECTED_VERSION,
                    provider_id="ready-alpha",
                    operation="validate",
                    provider_input={},
                )
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0.0)
            signal.signal(signal.SIGALRM, previous)
        return raised.value

    interval = FIRST_BOUND_SECONDS
    error = cancel_after(interval)
    while payload_sentinel(distribution, READY_SENTINEL) is None:
        assert interval * 2 <= BOUND_CEILING_SECONDS, (
            "the cancellation fixture never reached its worker within any interval this "
            f"test is willing to wait ({interval:.1f}s)"
        )
        interval *= 2
        error = cancel_after(interval)

    assert_error_is_content_safe(error, repo, distribution)
    sentinel = payload_sentinel(distribution, READY_SENTINEL)
    assert sentinel is not None
    worker_pid = int(sentinel.read_text(encoding="utf-8"))
    assert worker_pid != os.getpid()
    with pytest.raises(ProcessLookupError):
        os.kill(worker_pid, 0)
    assert tree_state(repo) == before
    assert open_descriptors() == descriptors
    assert_no_unreaped_children()


# ---------------------------------------------------------------------------
# TC-T4-006 / TC-T4-007: exact qualification and declared result fields
# ---------------------------------------------------------------------------


def test_dispatch_is_exact_payload_qualified(tmp_path: Path) -> None:
    """TC-T4-006 (IR-009): identity, version, provider, and operation must all match."""
    services = import_mcp_services()
    distribution = build_provider_distribution(tmp_path)
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    invoke = require_operation(facade, "invoke_read_provider")

    def call(**overrides: Any) -> Any:
        request: dict[str, Any] = {
            "standard_id": SELECTED_STANDARD,
            "version": SELECTED_VERSION,
            "provider_id": "validate-alpha",
            "operation": "validate",
            "provider_input": {},
        }
        request.update(overrides)
        return invoke(repo, **request)

    result = call()
    assert result_identity(result) == (
        SELECTED_STANDARD,
        SELECTED_VERSION,
        "validate-alpha",
        "validate",
    )

    # alpha 3.0 declares the same provider id with different bytes, and the
    # repository resolves 2.0. The version is a qualification the request must
    # satisfy, never a selector that can reach an unresolved payload: there is
    # no authoritative effective config for a version the resolution rejected.
    assert dumped(result)["output"]["checked"] == 3, "alpha 2.0 bytes must be what ran"

    for overrides in (
        {"standard_id": "no-such-standard"},
        {"standard_id": "beta", "version": "1.0"},
        {"version": CANDIDATE_VERSION},
        {"version": "9.9"},
        {"version": "1.0"},
        {"provider_id": "no-such-provider"},
        {"provider_id": "lint-alpha"},
        {"operation": "lint"},
    ):
        with pytest.raises(services.ServiceError) as raised:
            call(**overrides)
        assert_error_is_content_safe(raised.value, repo, distribution)


def test_provider_result_preserves_declared_fields(tmp_path: Path) -> None:
    """TC-T4-007 (DR-008): the typed result carries identity, contract, and output."""
    services = import_mcp_services()
    distribution = build_provider_distribution(tmp_path)
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    invoke = require_operation(facade, "invoke_read_provider")

    result = invoke(
        repo,
        standard_id=SELECTED_STANDARD,
        version=SELECTED_VERSION,
        provider_id="validate-alpha",
        operation="validate",
        provider_input={},
    )
    assert field_names(type(result)) == {
        "standard_id",
        "version",
        "provider_id",
        "operation",
        "phase",
        "effect",
        "status",
        "findings",
        "diagnostics",
        "output",
    }

    declaration = next(
        item
        for item in facade.standard(SELECTED_STANDARD, SELECTED_VERSION).providers
        if item.provider_id == "validate-alpha"
    )
    assert (result.operation, result.phase, result.effect) == (
        declaration.operation,
        declaration.phase,
        declaration.effect,
    )
    assert result.effect == ProviderEffect.FINDINGS.value

    oracle = oracle_dispatch(
        repo,
        distribution,
        standard_id=SELECTED_STANDARD,
        provider_id="validate-alpha",
        operation=ProviderOperation.VALIDATE,
    )
    # "every declared output-schema field": the validated provider output the
    # dispatcher already published, not a re-derived subset.
    assert dumped(result)["output"] == oracle.structured_output
    assert dumped(result)["output"]["checked"] == 3
    assert dumped(result)["output"]["profile"] == "strict"

    assert isinstance(result.status, str) and result.status
    assert (
        result.status
        == invoke(
            repo,
            standard_id=SELECTED_STANDARD,
            version=SELECTED_VERSION,
            provider_id="lint-alpha",
            operation="lint",
            provider_input={},
        ).status
    ), "status reports the dispatch outcome, not the finding content"

    # Stable DTO discipline, as for every other §5.5 model.
    config = model_config_of(type(result))
    assert config.get("frozen") is True
    assert config.get("extra") == "forbid"
    assert config.get("strict") is True
    assert isinstance(result.findings, tuple)

    # Byte-golden stability over the *stable* facts. `diagnostics` is excluded by
    # contract, not by convenience: DR-008 makes it bounded supplemental text
    # that never participates in an identity, and TC-T4-003 requires it to differ
    # between two otherwise identical calls (the drift nonce). The worker probe
    # channel this suite uses for process separation carries a per-call pid for
    # the same reason.
    def stable_projection(model: Any) -> str:
        projection = dumped(model)
        del projection["diagnostics"]
        return json.dumps(projection, sort_keys=True)

    assert stable_projection(result) == stable_projection(
        invoke(
            repo,
            standard_id=SELECTED_STANDARD,
            version=SELECTED_VERSION,
            provider_id="validate-alpha",
            operation="validate",
            provider_input={},
        )
    )


def test_public_result_dtos_are_frozen_by_class_and_annotation(tmp_path: Path) -> None:
    """TC-T4-007 (§5.5, DR-009): the named DTOs are the public, typed contract.

    T4.2 review F14: anonymous internal models carrying the right attribute names
    are not the frozen contract. Each §5.5 DTO row names a type, so the exported
    class identity and the typed relationships between the three types are
    asserted, not only their field names.
    """
    services = import_mcp_services()
    distribution = build_provider_distribution(tmp_path)
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)

    operation_result = require_dto(services, "ProviderOperationResult")
    validation_report = require_dto(services, "ValidationReport")
    drift_report = require_dto(services, "DriftReport")
    finding_type = require_dto(services, "Finding")

    direct = require_operation(facade, "invoke_read_provider")(
        repo,
        standard_id=SELECTED_STANDARD,
        version=SELECTED_VERSION,
        provider_id="validate-alpha",
        operation="validate",
        provider_input={},
    )
    report = require_operation(facade, "validate_repo")(repo)
    drift = require_operation(facade, "drift_check")(repo)

    assert type(direct) is operation_result
    assert type(report) is validation_report
    assert type(drift) is drift_report
    assert all(type(item) is operation_result for item in report.results)
    assert all(type(item) is operation_result for item in drift.results)
    assert all(type(item) is finding_type for item in report.findings)
    assert all(type(item) is finding_type for item in direct.findings)

    annotations = {
        (operation_result, "findings"): tuple[finding_type, ...],
        (validation_report, "results"): tuple[operation_result, ...],
        (validation_report, "findings"): tuple[finding_type, ...],
        (drift_report, "results"): tuple[operation_result, ...],
    }
    for (model, name), expected in annotations.items():
        declared: dict[str, Any] = model.model_fields
        assert declared[name].annotation == expected, f"{model.__name__}.{name} is not {expected}"
    for model in (operation_result, validation_report, drift_report):
        config = model_config_of(model)
        assert config.get("frozen") is True
        assert config.get("extra") == "forbid"
        assert config.get("strict") is True


def test_reports_are_typed_root_relative_and_free_of_timestamps(tmp_path: Path) -> None:
    """§5.5/DR-009: reports are frozen DTOs with no absolute path and no duration."""
    services = import_mcp_services()
    distribution = build_provider_distribution(tmp_path)
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)

    reports = [
        require_operation(facade, "validate_repo")(repo),
        require_operation(facade, "drift_check")(repo),
    ]
    for report in reports:
        assert isinstance(report.results, tuple)
        serialized = json.dumps(dumped(report))
        assert str(repo.resolve()) not in serialized
        assert str(distribution.package_root.resolve()) not in serialized
        assert not {"timestamp", "duration", "elapsed", "started_at", "finished_at"} & field_names(
            type(report)
        )

    assert field_names(type(reports[0])) == {"repo_root", "results", "findings"}


def plant_reconciliation_finding(repo: Path, distribution: InstalledDistribution) -> None:
    """Leave the repository in a state whose authoritative plan carries a finding.

    ``CP-CREATE-ONLY-ABSENT`` is used because the packaged fixture can produce
    it without manufacturing historical payload bytes. Like the stale-content
    advisory, it preserves applicability; error findings instead drop the
    offending target's action, which would make the actions comparison vacuous.
    The fixture reconciles once, then deletes the create-only ``.editorconfig``
    contribution the lock still records, plus the managed
    ``.standards/alpha/config.toml`` so a mutating action survives alongside it.
    """
    from project_standards.control_plane.executor import ApplyRequest, apply_reconciliation

    request = build_planner_request(repo, distribution, frozenset())
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings
    assert apply_reconciliation(ApplyRequest(request, plan)).success
    (repo / ".editorconfig").unlink()
    (repo / ".standards/alpha/config.toml").unlink()


# ---------------------------------------------------------------------------
# T4.4 Codex GREEN review: transport, termination, and trust-boundary rework
# ---------------------------------------------------------------------------


def test_termination_failures_never_claim_the_repository_is_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F1 (bounded accept): a killed worker is not a rollback, and the text says so.

    ADR 0025 buys bounded execution and fault isolation, not isolation from a
    trusted payload's filesystem access, and the plan forbids adding a sandbox
    layer to get it. What the service must not do is assert a guarantee it
    cannot provide: every termination path is checked for the claim, and each
    carries the identity of the selection it belongs to (F10).
    """
    services = import_mcp_services()
    providers = require_service_module("providers")
    distribution = build_provider_distribution(tmp_path, hazards=("slow", "stubborn", "crash"))
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    invoke = require_operation(facade, "invoke_read_provider")
    monkeypatch.setattr(providers, "PROVIDER_TIMEOUT_SECONDS", 1.0)

    for provider_id in ("slow-alpha", "stubborn-alpha", "crash-alpha"):
        with pytest.raises(services.ServiceError) as raised:
            invoke(
                repo,
                standard_id=SELECTED_STANDARD,
                version=SELECTED_VERSION,
                provider_id=provider_id,
                operation="validate",
                provider_input={},
            )
        assert_error_is_content_safe(raised.value, repo, distribution, identified=True)
    assert_no_unreaped_children()


def test_worker_group_termination_leaves_no_descendant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F3: a provider-forked descendant dies with the group, on both leader paths.

    Both halves need the provider to have *forked* before anything is asserted
    about the descendant, which the fork sentinel reports directly; the bound and
    the watchdogs are sized off that observation rather than off a constant that
    a loaded machine can invalidate (issue #147).
    """
    services = import_mcp_services()
    providers = require_service_module("providers")
    distribution = build_provider_distribution(tmp_path, hazards=("forker", "forker-exit"))
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    invoke = require_operation(facade, "invoke_read_provider")

    descriptors = open_descriptors()
    before = tree_state(repo)

    def call(provider_id: str) -> Any:
        return invoke(
            repo,
            standard_id=SELECTED_STANDARD,
            version=SELECTED_VERSION,
            provider_id=provider_id,
            operation="validate",
            provider_input={},
        )

    # The leader hangs: the invocation ends at the bound and the descendant must
    # die with the group rather than being orphaned holding the pipes.
    hung = terminate_after_provider_starts(
        lambda: call("forker-alpha"),
        services=services,
        providers=providers,
        monkeypatch=monkeypatch,
        distribution=distribution,
        started=FORKED_SENTINEL,
    )
    assert hung.elapsed < WATCHDOG_SECONDS
    assert_error_is_content_safe(hung.error, repo, distribution, identified=True)
    forked = int(_require_sentinel(distribution, FORKED_SENTINEL).read_text(encoding="utf-8"))
    assert_process_gone(forked)
    assert open_descriptors() == descriptors
    assert_no_unreaped_children()

    _require_sentinel(distribution, FORKED_SENTINEL).unlink()

    # The leader exits normally while the descendant still holds every inherited
    # pipe open: the result must still arrive, promptly, and the descendant must
    # still be reaped. "Promptly" is against the descendant's own course, which is
    # what a parent waiting on the inherited pipes would sit through — not against
    # the leader's start-up, which is not this test's subject. The bound sits above
    # the watchdog and far below that course, so this half cannot be decided by the
    # bound, and a parent that did wait on the pipes still ends in about a minute
    # rather than five.
    monkeypatch.setattr(providers, "PROVIDER_TIMEOUT_SECONDS", 2 * BOUND_CEILING_SECONDS)
    started = time.monotonic()
    result = call("forker-exit-alpha")
    assert time.monotonic() - started < WATCHDOG_SECONDS
    assert result.status
    survivor = int(_require_sentinel(distribution, FORKED_SENTINEL).read_text(encoding="utf-8"))
    assert_process_gone(survivor)
    assert open_descriptors() == descriptors
    assert tree_state(repo) == before
    assert_no_unreaped_children()


def _require_sentinel(distribution: InstalledDistribution, name: str) -> Path:
    found = payload_sentinel(distribution, name)
    assert found is not None, f"the fixture never wrote its {name} sentinel"
    return found


def test_cooperative_shutdown_is_drained_instead_of_escalated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F9: the parent keeps draining across the SIGTERM grace.

    The fixture's handler writes far more than a pipe capacity before exiting. A
    parent that stopped reading while waiting for the worker to die would block
    that handler and escalate to SIGKILL for its own inaction, and the sentinel
    written after the flood would never appear.

    A worker killed before it ever installed that handler would leave the same
    missing sentinel while proving nothing about draining, and under gate
    parallelism a short bound expires during interpreter start-up often enough to
    make that the usual outcome (issue #147). The bound is therefore escalated
    until the fixture reports its handler armed, which is the precondition this
    assertion has always silently assumed.
    """
    services = import_mcp_services()
    providers = require_service_module("providers")
    distribution = build_provider_distribution(tmp_path, hazards=("cooperative",))
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    invoke = require_operation(facade, "invoke_read_provider")

    attempt = terminate_after_provider_starts(
        lambda: invoke(
            repo,
            standard_id=SELECTED_STANDARD,
            version=SELECTED_VERSION,
            provider_id="cooperative-alpha",
            operation="validate",
            provider_input={},
        ),
        services=services,
        providers=providers,
        monkeypatch=monkeypatch,
        distribution=distribution,
        started=COOPERATIVE_ARMED_SENTINEL,
        clear=(COOPERATIVE_SENTINEL,),
    )
    assert_error_is_content_safe(attempt.error, repo, distribution, identified=True)
    assert payload_sentinel(distribution, COOPERATIVE_SENTINEL) is not None, (
        "the cooperative handler never finished; the parent stopped draining during "
        "the termination grace"
    )
    assert_no_unreaped_children()


def test_execution_bound_is_not_extended_after_the_streams_close(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F8: no bonus wait past the deadline, only the termination grace.

    "Never the provider's own duration" is asserted through the fixture's own
    completion sentinel rather than through elapsed time (issue #147). Elapsed
    time carries a term this claim is not about — the worker's cold start, which
    the bound covers but the ceiling below did not account for, and which under
    gate parallelism is larger than the provider's whole sleep. The sentinel says
    directly whether the provider ran to completion, so a parent that waited for
    it is caught on any machine at any speed.
    """
    services = import_mcp_services()
    providers = require_service_module("providers")
    distribution = build_provider_distribution(tmp_path, hazards=("medium",))
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    invoke = require_operation(facade, "invoke_read_provider")

    def call(provider_id: str) -> Any:
        return invoke(
            repo,
            standard_id=SELECTED_STANDARD,
            version=SELECTED_VERSION,
            provider_id=provider_id,
            operation="validate",
            provider_input={},
        )

    # The fixed cost of one whole invocation on this machine, right now: a cold
    # interpreter that imports the installed distribution before the payload is
    # loaded at all. It sits inside every elapsed measurement and outside every
    # injected bound, so the ceiling below has to be told what it currently is
    # instead of assuming a figure from an idle machine.
    monkeypatch.setattr(providers, "PROVIDER_TIMEOUT_SECONDS", float(HAZARD_SLEEP_SECONDS))
    measured = time.monotonic()
    call("validate-alpha")
    overhead = time.monotonic() - measured

    bound = 1.0
    monkeypatch.setattr(providers, "PROVIDER_TIMEOUT_SECONDS", bound)
    grace = require_attribute(
        provider_subprocess,
        "TERMINATION_GRACE_SECONDS",
        "shared provider-runner constant",
    )
    started = time.monotonic()
    with pytest.raises(services.ServiceError) as raised:
        call("medium-alpha")
    elapsed = time.monotonic() - started
    # Worker start-up, plus the bound, plus at most the declared termination grace
    # applied a bounded number of times, plus scheduling slack.
    ceiling = 3 * overhead + bound + 4 * float(grace) + 1.0
    assert elapsed < ceiling, f"termination took {elapsed:.2f}s against a {ceiling:.2f}s ceiling"
    assert payload_sentinel(distribution, MEDIUM_COMPLETED_SENTINEL) is None, (
        "the invocation waited for the provider's own duration instead of ending at the bound"
    )
    assert_error_is_content_safe(raised.value, repo, distribution, identified=True)
    assert_no_unreaped_children()


def test_typed_input_is_validated_recursively_before_any_worker(tmp_path: Path) -> None:
    """F5: strict JSON types and string-only keys at every depth, pre-worker."""
    services = import_mcp_services()
    distribution = build_provider_distribution(tmp_path)
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    invoke = require_operation(facade, "invoke_read_provider")

    before = tree_state(repo)
    for provider_input in (
        # The duplicate-collapse case: JSON would render both keys as "1" and the
        # receiving parser would discard one, so dispatch would not receive the
        # exact typed input that was passed.
        {"nested": {1: "first", "1": "second"}},
        {"nested": {"deeper": {2.5: "collapsed"}}},
        {"nested": [{"ok": 1}, {None: "collapsed"}]},
        {"nested": {"deeper": [1, 2, {3: "collapsed"}]}},
        {"nested": {"deeper": float("inf")}},
        {"nested": [1, 2, {1, 2}]},
        {"nested": {"deeper": b"bytes"}},
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
        assert_error_is_content_safe(raised.value, repo, distribution)
    assert tree_state(repo) == before
    assert_no_unreaped_children()


def test_finding_paths_must_be_contained_in_the_consumer_root(tmp_path: Path) -> None:
    """F6 (amended): relative traversal is refused exactly like an absolute escape."""
    services = import_mcp_services()
    distribution = build_provider_distribution(tmp_path, hazards=("echo",))
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    invoke = require_operation(facade, "invoke_read_provider")

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret").write_text("do-not-publish\n", encoding="utf-8")

    for escape in ("../outside/secret", "nested/../../outside/secret", str(outside / "secret")):
        with pytest.raises(services.ServiceError) as raised:
            invoke(
                repo,
                standard_id=SELECTED_STANDARD,
                version=SELECTED_VERSION,
                provider_id="echo-alpha",
                operation="validate",
                provider_input=referenced_input_snapshot(repo, nonce="esc", echo_path=escape),
            )
        error = raised.value
        assert_error_is_content_safe(
            error, repo, distribution, forbidden=("do-not-publish",), identified=True
        )
        assert "secret" not in f"{error.message}{error.remediation}{error.path}"
    assert_no_unreaped_children()


def test_provider_output_key_order_is_canonical_across_worker_processes(
    tmp_path: Path,
) -> None:
    """F7: mapping keys are canonicalized, so results survive randomized hash seeds.

    ``stable_json`` preserved insertion order before this rework
    (``consumer.py:333``), and the fixture provider builds its output keys by
    iterating a set — an order that is hash-seed dependent and survives a JSON
    round trip. Every worker is a fresh interpreter with its own seed, so
    repeated invocations are a genuine cross-seed comparison.
    """
    services = import_mcp_services()
    distribution = build_provider_distribution(tmp_path, hazards=("unordered",))
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    invoke = require_operation(facade, "invoke_read_provider")

    projections: set[str] = set()
    for _ in range(4):
        result = invoke(
            repo,
            standard_id=SELECTED_STANDARD,
            version=SELECTED_VERSION,
            provider_id="unordered-alpha",
            operation="validate",
            provider_input={},
        )
        output = dumped(result)["output"]
        assert list(output["unordered"]) == sorted(output["unordered"]), (
            "mapping keys were published in producer insertion order"
        )
        projections.add(json.dumps(output))
    assert len(projections) == 1, (
        f"identical invocations serialized {len(projections)} different ways"
    )


# ---------------------------------------------------------------------------
# TC-T14-001..004: authoritative typed input for composite dispatch
# ---------------------------------------------------------------------------


def test_composite_dispatch_input_matches_authoritative_direct_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TC-T14-001: every composite result equals its authority's own dispatch.

    The composite sends a seam directive rather than a built input, so nothing at
    the service boundary exposes the bytes a provider received. The oracle is
    therefore the consequence: for each applicable shipping provider, the findings
    and declared output the composite publishes must equal what the same provider
    produces when dispatched in-process by its own authority.

    The second half is what keeps the first from being vacuous. Empty input — what
    composite dispatch sent before T14 — must produce a DIFFERENT answer for at
    least one provider, or this node would pass against the defect it exists to
    close (T11: agent-handoff/validate answered 24 findings where its authority
    answers 240, and three other providers raised outright).
    """
    services = import_mcp_services()
    providers = require_service_module("providers")
    monkeypatch.setattr(
        providers, "PROVIDER_TIMEOUT_SECONDS", REAL_PACKAGE_PROVIDER_TIMEOUT_SECONDS
    )
    distribution = real_packaged_distribution()
    facade = build_facade(services, distribution)
    validate_repo = require_operation(facade, "validate_repo")

    report = validate_repo(REAL_CONSUMER_ROOT)
    applicable = oracle_selection(
        REAL_CONSUMER_ROOT, distribution, frozenset({"validate", "verify", "lint"})
    )
    assert result_sequence(report) == applicable
    assert applicable, "this repository must resolve applicable shipping providers"

    for item in report.results:
        owner = AUTHORITATIVE_INPUT_OWNER.get((item.standard_id, item.provider_id))
        assert owner is not None, (
            f"{item.standard_id}/{item.provider_id} has no declared authoritative input owner; "
            "the census in AUTHORITATIVE_INPUT_OWNER is stale"
        )
        oracle = authoritative_direct_dispatch(
            REAL_CONSUMER_ROOT,
            distribution,
            standard_id=item.standard_id,
            provider_id=item.provider_id,
            operation=ProviderOperation(item.operation),
            owner=owner,
        )
        assert [published_finding(finding) for finding in item.findings] == [
            mapped_finding(finding) for finding in oracle.findings
        ], (
            f"{item.standard_id}/{item.provider_id} did not answer what its own authority "
            "answers for this root"
        )
        assert dumped(item)["output"] == oracle.structured_output

    # Mutation control: the pre-T14 input is observably wrong for a real provider.
    assert empty_input_diverges(REAL_CONSUMER_ROOT, distribution, applicable), (
        "empty input produced the authoritative answer for every provider, so this "
        "node cannot distinguish seam-built input from the defect"
    )


def empty_input_diverges(
    repo: Path,
    distribution: InstalledDistribution,
    applicable: list[tuple[str, str, str, str]],
) -> bool:
    """Report whether any shipping provider answers differently on empty input.

    Refusing outright counts as divergence: three of the four providers the T11
    smoke exercised raise rather than answer when handed ``{}``.
    """
    for standard_id, _version, provider_id, operation in applicable:
        owner = AUTHORITATIVE_INPUT_OWNER[(standard_id, provider_id)]
        authoritative = authoritative_direct_dispatch(
            repo,
            distribution,
            standard_id=standard_id,
            provider_id=provider_id,
            operation=ProviderOperation(operation),
            owner=owner,
        )
        try:
            empty = oracle_dispatch(
                repo,
                distribution,
                standard_id=standard_id,
                provider_id=provider_id,
                operation=ProviderOperation(operation),
            )
        except ValueError, ControlPlaneError, PackageContractError:
            return True
        if [mapped_finding(item) for item in authoritative.findings] != [
            mapped_finding(item) for item in empty.findings
        ]:
            return True
    return False


def test_real_packaged_provider_validates_real_consumer_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TC-T14-002: shipping providers complete against a real consumer repository.

    The end-to-end half of T14. Before it, `adr/validate-adr`,
    `markdown-frontmatter/validate-frontmatter` and both project-spec providers
    raised `provider failed with ValueError` on this exact root (the T11 client
    matrix), and the composite aborted on the first of them.
    """
    services = import_mcp_services()
    providers = require_service_module("providers")
    monkeypatch.setattr(
        providers, "PROVIDER_TIMEOUT_SECONDS", REAL_PACKAGE_PROVIDER_TIMEOUT_SECONDS
    )
    distribution = real_packaged_distribution()
    facade = build_facade(services, distribution)

    # T14 review F2: the composite no-write proof elsewhere in this suite runs on
    # the synthetic `alpha` package, which is family-less and therefore never
    # reaches `authoritative_provider_input` or its in-worker plan. This is the
    # only node that exercises that read surface, so it carries the snapshot.
    before = real_tree_digest(REAL_CONSUMER_ROOT)

    report = require_operation(facade, "validate_repo")(REAL_CONSUMER_ROOT)
    assert report.repo_root == "."
    assert report.results, "this repository must resolve applicable shipping providers"
    unfinished = [
        (item.standard_id, item.provider_id, item.status, item.diagnostics[:300])
        for item in report.results
        if item.status != "completed"
    ]
    assert not unfinished, f"shipping providers did not complete: {unfinished}"

    # The four the T11 smoke recorded as crashing on empty input.
    crashed_before = {
        ("adr", "validate-adr"),
        ("markdown-frontmatter", "validate-frontmatter"),
        ("project-spec", "validate"),
        ("project-spec", "lint"),
    }
    served = {(item.standard_id, item.provider_id) for item in report.results}
    assert crashed_before <= served

    drift = require_operation(facade, "drift_check")(REAL_CONSUMER_ROOT)
    assert drift.results, "this repository must resolve a shipping drift-check provider"
    assert all(item.status == "completed" for item in drift.results)

    assert real_tree_digest(REAL_CONSUMER_ROOT) == before, (
        "a composite call wrote to the real consumer repository; the worker-side seam, "
        "its corpus capture, or its in-worker reconciliation plan is not read-only"
    )


def test_provider_failure_isolates_to_typed_per_result_failure(tmp_path: Path) -> None:
    """TC-T14-003: one provider's failure is a typed result, not a lost report.

    `crash-alpha` calls ``os._exit(9)`` inside its worker, so the failure is a
    real dispatch failure rather than a simulated one. Its siblings must still
    answer, the composite must still return, and the failure must be published in
    the closed §5.5 result shape — which carries no error field, so the outcome
    lands in ``status`` and ``diagnostics`` with no findings invented.
    """
    services = import_mcp_services()
    distribution = build_provider_distribution(tmp_path, hazards=("crash", "probe"))
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)

    report = require_operation(facade, "validate_repo")(repo)

    expected = oracle_selection(repo, distribution, frozenset({"validate", "verify", "lint"}))
    assert result_sequence(report) == expected, (
        "a failing provider changed which providers the composite answered for"
    )

    # The status a provider that finished reports, read from a live single-provider
    # dispatch rather than pinned as a literal: nothing in §5.5 or the T9 schema
    # freezes the word, and this suite already treats status that way.
    completed = require_operation(facade, "invoke_read_provider")(
        repo,
        standard_id=SELECTED_STANDARD,
        version=SELECTED_VERSION,
        provider_id="validate-alpha",
        operation="validate",
        provider_input={},
    ).status

    results = {item.provider_id: item for item in report.results}
    failed = results["crash-alpha"]
    assert failed.status != completed, "the crashed provider reported success"
    assert isinstance(failed.status, str) and failed.status
    assert failed.findings == ()
    assert isinstance(failed.diagnostics, str) and failed.diagnostics
    assert str(repo.resolve()) not in failed.diagnostics
    assert str(distribution.package_root.resolve()) not in failed.diagnostics
    for claim in UNCHANGED_CLAIMS:
        assert claim not in failed.diagnostics.lower()
    # Identity survives the failure: a caller must be able to say which provider
    # did not answer, which is the whole point of a per-result failure.
    assert (failed.standard_id, failed.version, failed.operation) == (
        SELECTED_STANDARD,
        SELECTED_VERSION,
        "validate",
    )

    siblings = [item for item in report.results if item.provider_id != "crash-alpha"]
    assert siblings, "the fixture must declare providers beside the failing one"
    assert all(item.status == completed for item in siblings)
    assert_ran_in_worker(results["probe-alpha"])
    assert report.findings == tuple(finding for item in report.results for finding in item.findings)
    assert report.findings, "the surviving providers must still publish their findings"
    assert_no_unreaped_children()


def build_unconstructible_family_consumer(tmp_path: Path) -> tuple[InstalledDistribution, Path]:
    """Reconcile a real markdown-frontmatter consumer, then break what the seam reads.

    A *family* standard is the point: the seam declares an authoritative input for
    `markdown-frontmatter/validate-frontmatter` and then cannot build it, which is
    the case T14 review F1 separates from a family-less standard. The consumer
    declares a custom frontmatter schema that the lock does not carry as a
    referenced input, so resolution still selects the package and only
    construction fails — with a `CommandResolutionError`, which is precisely the
    class the pre-F1 worker converted into an empty input. Built from the T15
    custom-schema consumer recipe (``tests/control_plane/test_command_resolution.py``).
    """
    from project_standards.control_plane.bootstrap import initialize_control_plane

    installed = tmp_path / "unconstructible-installed/project_standards"
    shutil.copytree(REAL_CONSUMER_ROOT / "src/project_standards", installed, symlinks=False)
    distribution = InstalledDistribution(installed, tool_release=TOOL_RELEASE)
    repo = tmp_path / "unconstructible-consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=distribution)
    control = repo / ".standards"
    schema = control / "extensions/markdown-frontmatter/schema.json"
    schema.parent.mkdir(parents=True)
    schema.write_bytes(json.dumps({"type": "object"}, sort_keys=True).encode())
    (control / "config.toml").write_bytes(
        b'[project_standards]\nschema_version = "1.0"\ncatalog = "5"\n\n'
        b'[standards.markdown-frontmatter]\nenabled = true\nversion = "latest"\n\n'
        b"[standards.markdown-frontmatter.config]\n"
        b'contract_version = "1.1"\n'
        b'schema = "custom"\n'
        b'schema_path = ".standards/extensions/markdown-frontmatter/schema.json"\n'
        b"required = false\n"
        b'include = ["handbook/**/*.md"]\n'
        b"exclude = []\n"
    )
    handbook = repo / "handbook"
    handbook.mkdir()
    (handbook / "one.md").write_text("---\ntitle: one\n---\n\n# One\n", encoding="utf-8")
    return distribution, repo


def test_unconstructible_authoritative_input_fails_typed_rather_than_empty(
    tmp_path: Path,
) -> None:
    """TC-T14-003 (review F1): a seam that cannot build must not degrade to ``{}``.

    The family-less tolerance is a one-case exemption, and this is the case next
    to it. `markdown-frontmatter` *has* a declared authority here; its declared
    custom schema is not a locked referenced input, so construction fails with the
    very error class a worker that caught `CommandResolutionError` wholesale used
    to answer with ``{}``. It must surface instead as a typed per-result failure
    carrying the seam's own refusal — never as the generic empty input, which
    would hand a real packaged provider the exact wrong corpus the T11 smoke
    found.
    """
    services = import_mcp_services()
    distribution, repo = build_unconstructible_family_consumer(tmp_path)
    facade = build_facade(services, distribution)

    # What the seam says, taken independently of the service under test.
    with selected_command(
        repo,
        "markdown-frontmatter",
        distribution,
        mode=LockMode.READ,
        require_reconciled=False,
    ) as selected:
        assert selected is not None
        # The base class, deliberately: a construction failure may surface as any
        # control-plane error the capture raises. What matters is the one class it
        # must NOT be.
        with pytest.raises(ControlPlaneError) as refused:
            provider_dispatch_input(
                selected,
                ProviderOperation.VALIDATE,
                provider_id="validate-frontmatter",
            )
    assert not isinstance(refused.value, NoDeclaredProviderInput), (
        "a family standard whose input cannot be built must not report an absent "
        "declaration; that is the conflation T14 review F1 names"
    )

    report = require_operation(facade, "validate_repo")(repo)
    results = {item.provider_id: item for item in report.results}
    failed = results["validate-frontmatter"]
    assert failed.status != "completed"
    assert failed.findings == ()
    assert failed.output is None
    assert refused.value.message in failed.diagnostics, (
        "the per-result failure does not carry the seam's construction failure, so the "
        f"provider was dispatched with something else: {failed.diagnostics[:400]!r}"
    )
    assert_no_unreaped_children()


def test_every_shipping_catalog_provider_is_seam_served() -> None:
    """TC-T14-004: no shipping provider may fall back to generic dispatch.

    Standards outside the seam's five families keep the existing generic input, so
    the fixture standards the rest of this suite depends on are unaffected. That
    tolerance is exactly what could let a future packaged standard reopen the
    empty-input defect silently, so the shipping catalog is pinned: every provider
    the composite operations dispatch for a real consumer must obtain seam-built
    input from the worker-side authority.

    "Applicable" is defined as the T4 selection rule — a provider of a package the
    live resolution selects, declaring one of the composite operations — evaluated
    against this repository, whose control plane enables every consumer-role
    package in Catalog 5. The membership assertion is what makes a newly shipped
    package fail here rather than pass unnoticed.

    One declared exemption: a `planner-owned` provider (see
    `AUTHORITATIVE_INPUT_OWNER`) has no seam authority to fall back FROM — generic
    dispatch is what its own authority does everywhere except fresh-adoption
    planning — so serving it here would create the CLI/service divergence this
    node exists to prevent rather than close a defect.
    """
    worker = importlib.import_module("project_standards.control_plane.provider_worker")
    seam_input = require_attribute(
        worker,
        "authoritative_provider_input",
        "T14 worker-side seam authority",
    )
    distribution = real_packaged_distribution()

    consumer_packages = {
        payload.manifest.payload.standard
        for payload in distribution.load_catalog(CatalogMajor("5")).payloads
        if payload.manifest.payload.availability is PayloadAvailability.CONSUMER
    }
    applicable = oracle_selection(
        REAL_CONSUMER_ROOT,
        distribution,
        frozenset({"validate", "verify", "lint", "drift-check"}),
    )
    exercised = {standard_id for standard_id, _version, _provider, _operation in applicable}
    assert exercised == consumer_packages, (
        "this repository no longer enables every consumer-role package in the shipping "
        f"catalog, so the canary is blind: missing {sorted(consumer_packages - exercised)}"
    )

    unserved: list[tuple[str, str]] = []
    for standard_id, _version, provider_id, operation in applicable:
        with selected_command(
            REAL_CONSUMER_ROOT,
            standard_id,
            distribution,
            mode=LockMode.READ,
            require_reconciled=False,
        ) as selected:
            assert selected is not None
            built = seam_input(
                selected,
                ProviderOperation(operation),
                provider_id=provider_id,
            )
        if not built and AUTHORITATIVE_INPUT_OWNER.get((standard_id, provider_id)) != PLANNER_OWNED:
            # Fails closed on a NEW provider: an id absent from the census reads
            # as `None`, never as the exemption, so only a reviewed declaration
            # can take a shipping provider out of this canary.
            unserved.append((standard_id, provider_id))
    assert not unserved, (
        "these shipping providers fall back to generic dispatch and would receive the "
        f"empty input T14 exists to remove: {unserved}"
    )
