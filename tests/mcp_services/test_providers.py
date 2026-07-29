"""Bounded non-mutating provider services behind the SDK-free facade (T4).

Covers TC-T4-001 (validate/drift orchestration over the current exact
resolution), TC-T4-003 (bounded, fingerprint-neutral diagnostics), TC-T4-004
(every DR-003 finding field), TC-T4-005 (the ADR 0025 execution bound with a
reaped worker), TC-T4-006 (exact payload qualification), and TC-T4-007 (declared
result fields preserved).

Two authorities constrain every expectation here and neither may be re-derived
by the service under test:

*The dispatcher* — ``invoke_provider``
(``src/project_standards/control_plane/providers.py:732``) — owns provider
semantics. ``T4.0`` pinned what it does and does not do: it compiles and executes
provider bytes in the calling process with no timeout, no cancellation, no
process boundary, and Python-level-only output capture, and it *discards* the
captured text, keeping only a one-line ``output_notice``. Everything ADR 0025
adds — the worker process, the 30-second bound, SIGTERM-then-SIGKILL with
reaping, bounded JSON IPC with explicit truncation markers, and
file-descriptor-level stream capture — is therefore new T4 surface, while
identity qualification, resource closure, input/output schema validation, and
effect-typed result construction stay with the dispatcher. Parity is asserted
against it directly.

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
from dataclasses import fields
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.command_resolution import (
    SelectedCommandPackage,
    invoke_selected_provider,
    selected_command,
)
from project_standards.control_plane.diagnostics import ControlFinding
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.executor import reconciliation_fingerprint
from project_standards.control_plane.locking import LockMode
from project_standards.control_plane.paths import CatalogMajor
from project_standards.control_plane.planner import ReconciliationPlan, plan_reconciliation
from project_standards.control_plane.providers import ProviderResult
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    PayloadManifest,
    ProviderEffect,
    ProviderOperation,
)
from project_standards.package_contract.projection import sync_payload_projection
from tests.mcp_services.helpers import FULL_FIXTURE, import_mcp_services
from tests.mcp_services.test_consumer import TOOL_RELEASE, dumped, field_names, model_config_of

# The four operations ADR 0025 approves. Nothing in the suite asserts that an
# implementation publishes this tuple under any name (T4.2 review F15): the
# allowlist is frozen only by which declared providers are accepted and which
# are refused before process creation.
APPROVED_OPERATIONS = ("validate", "verify", "lint", "drift-check")

# ADR 0025: "The provider timeout is 30 seconds per provider invocation."
ADR_TIMEOUT_SECONDS = 30

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

    time.sleep(300)
    return {"findings": [], "checked": 0, "profile": "strict"}


def medium(_request, _resources):
    import time

    time.sleep(MEDIUM_SLEEP_LITERAL)
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
    while True:
        time.sleep(0.05)


def ready(_request, _resources):
    import os
    import time

    _sentinel("WORKER-READY", str(os.getpid()))
    time.sleep(300)
    return {"findings": [], "checked": 0, "profile": "strict"}


def forker(_request, _resources):
    import os
    import time

    # The descendant inherits stdout, stderr, and the result descriptor, then
    # outlives its parent: only group termination can end it.
    child = os.fork()
    if child == 0:
        time.sleep(300)
        os._exit(0)
    _sentinel("FORKED-CHILD", str(child))
    time.sleep(300)
    return {"findings": [], "checked": 0, "profile": "strict"}


def forker_exit(_request, _resources):
    import os
    import time

    child = os.fork()
    if child == 0:
        time.sleep(300)
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


def assert_no_unreaped_children() -> None:
    """Fail if any child process of this process survives the invocation."""
    try:
        pid, _ = os.waitpid(-1, os.WNOHANG)
    except ChildProcessError:
        return
    raise AssertionError(f"a worker process survived the invocation (waitpid returned {pid})")


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


def assert_process_gone(pid: int, *, timeout: float = 10.0) -> None:
    """Wait briefly for one pid to disappear, then require that it has."""
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
    # some smaller hidden constant.
    monkeypatch.setattr(providers, "PROVIDER_TIMEOUT_SECONDS", MEDIUM_SLEEP_SECONDS + 12.0)
    started = time.monotonic()
    completed = call("medium-alpha")
    elapsed = time.monotonic() - started
    assert elapsed >= MEDIUM_SLEEP_SECONDS
    assert elapsed < MEDIUM_SLEEP_SECONDS + 12.0
    assert_ran_in_worker(completed)

    # Below it: the same provider is terminated, so the effective bound is not
    # some larger hidden constant either.
    monkeypatch.setattr(providers, "PROVIDER_TIMEOUT_SECONDS", 1.0)
    started = time.monotonic()
    with pytest.raises(services.ServiceError) as raised:
        call("medium-alpha")
    elapsed = time.monotonic() - started
    assert elapsed < MEDIUM_SLEEP_SECONDS, "the injected bound did not decide termination"
    assert_error_is_content_safe(raised.value, repo, distribution)

    # A provider that never returns, and one that refuses SIGTERM: the sentinel
    # proves the polite signal was delivered first and forced termination
    # followed (ADR 0025; T4.2 review F11).
    for provider_id in ("slow-alpha", "stubborn-alpha"):
        started = time.monotonic()
        with pytest.raises(services.ServiceError) as raised:
            call(provider_id)
        assert time.monotonic() - started < 20, f"{provider_id} was not bounded"
        assert_error_is_content_safe(raised.value, repo, distribution)

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
    """
    import signal

    services = import_mcp_services()
    providers = require_service_module("providers")
    distribution = build_provider_distribution(tmp_path, hazards=("ready",))
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    invoke = require_operation(facade, "invoke_read_provider")
    monkeypatch.setattr(providers, "PROVIDER_TIMEOUT_SECONDS", 300.0)

    before = tree_state(repo)
    descriptors = open_descriptors()

    def interrupt(*_args: object) -> None:
        raise KeyboardInterrupt("cancelled")

    previous = signal.signal(signal.SIGALRM, interrupt)
    try:
        signal.setitimer(signal.ITIMER_REAL, 4.0)
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

    assert_error_is_content_safe(raised.value, repo, distribution)
    sentinel = payload_sentinel(distribution, READY_SENTINEL)
    assert sentinel is not None, "the cancellation fixture never reached its worker"
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

    ``CP-CREATE-ONLY-ABSENT`` (``control_plane/planner.py:1526``) is the only
    finding the planner emits at ``severity="warning"``; every other code path
    forces ``applicable = False`` *and* drops the offending target's action
    (``planner.py:1664``), which would make the actions comparison vacuous
    instead. So the fixture reconciles once, then deletes the create-only
    ``.editorconfig`` contribution the lock still records — the consumer-side
    deletion the planner is designed to report — plus the managed
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
    """F3: a provider-forked descendant dies with the group, on both leader paths."""
    services = import_mcp_services()
    providers = require_service_module("providers")
    distribution = build_provider_distribution(tmp_path, hazards=("forker", "forker-exit"))
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    invoke = require_operation(facade, "invoke_read_provider")
    monkeypatch.setattr(providers, "PROVIDER_TIMEOUT_SECONDS", 4.0)

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
    started = time.monotonic()
    with pytest.raises(services.ServiceError) as raised:
        call("forker-alpha")
    assert time.monotonic() - started < 20
    assert_error_is_content_safe(raised.value, repo, distribution, identified=True)
    forked = int(_require_sentinel(distribution, FORKED_SENTINEL).read_text(encoding="utf-8"))
    assert_process_gone(forked)
    assert open_descriptors() == descriptors
    assert_no_unreaped_children()

    _require_sentinel(distribution, FORKED_SENTINEL).unlink()

    # The leader exits normally while the descendant still holds every inherited
    # pipe open: the result must still arrive, promptly, and the descendant must
    # still be reaped.
    started = time.monotonic()
    result = call("forker-exit-alpha")
    assert time.monotonic() - started < 20
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
    """
    services = import_mcp_services()
    providers = require_service_module("providers")
    distribution = build_provider_distribution(tmp_path, hazards=("cooperative",))
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    invoke = require_operation(facade, "invoke_read_provider")
    monkeypatch.setattr(providers, "PROVIDER_TIMEOUT_SECONDS", 1.0)

    with pytest.raises(services.ServiceError) as raised:
        invoke(
            repo,
            standard_id=SELECTED_STANDARD,
            version=SELECTED_VERSION,
            provider_id="cooperative-alpha",
            operation="validate",
            provider_input={},
        )
    assert_error_is_content_safe(raised.value, repo, distribution, identified=True)
    assert payload_sentinel(distribution, COOPERATIVE_SENTINEL) is not None, (
        "the cooperative handler never finished; the parent stopped draining during "
        "the termination grace"
    )
    assert_no_unreaped_children()


def test_execution_bound_is_not_extended_after_the_streams_close(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F8: no bonus wait past the deadline, only the termination grace."""
    services = import_mcp_services()
    providers = require_service_module("providers")
    distribution = build_provider_distribution(tmp_path, hazards=("medium",))
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    invoke = require_operation(facade, "invoke_read_provider")

    bound = 1.0
    monkeypatch.setattr(providers, "PROVIDER_TIMEOUT_SECONDS", bound)
    grace = require_attribute(providers, "TERMINATION_GRACE_SECONDS", "T4 module constant")
    started = time.monotonic()
    with pytest.raises(services.ServiceError) as raised:
        invoke(
            repo,
            standard_id=SELECTED_STANDARD,
            version=SELECTED_VERSION,
            provider_id="medium-alpha",
            operation="validate",
            provider_input={},
        )
    elapsed = time.monotonic() - started
    # The bound, plus at most the declared termination grace applied a bounded
    # number of times, plus scheduling slack — never the provider's own duration.
    assert elapsed < bound + 4 * float(grace) + 1.0, f"termination took {elapsed:.2f}s"
    assert elapsed < MEDIUM_SLEEP_SECONDS
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
