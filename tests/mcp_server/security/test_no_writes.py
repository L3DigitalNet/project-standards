"""No registered v1 tool can reach a write or an apply path (T9, TC-T9-003).

FR-018 is unconditional — "No registered v1 tool invokes reconciliation apply,
provider mutation, or consumer file writes" — and FR-019 defers the whole
controlled-write design to a later spec, so this suite exists to make the
omission provable rather than asserted. The plan's acceptance names the two
fixtures it wants: "registry and subprocess fixtures prove zero writes/apply
calls".

Four independent proofs, because each one alone has a hole the others close.

*The registry.* Every advertised tool is drawn from ADR 0026's frozen read-only
six, and no advertised tool declares an argument that could name an operation,
a payload identity, or a path to write. A tool that cannot be asked to write is
a stronger guarantee than one that refuses to.

*The names.* Every module under ``mcp_server`` is searched for the authoritative
apply, mutation-schema, provider-entrypoint, and provider-declaration symbols
plan:439 forbids it to import — and each of those symbols is first confirmed to
exist in its owning module, so a misspelling cannot make this test pass by
accident. This is the complement of ``contract/test_import_boundary.py``, which
checks import *direction*: a module on that suite's allowlist (``entrypoint``,
``repo_access``) may legitimately import the control plane, and nothing there
stops it from reaching an apply callable once it has.

*The syscalls.* The server runs in a subprocess with an audit hook installed
before any distribution module is imported, so every write *intent* — ``open``
with write flags, and the ``os``/``shutil`` mutators — is recorded with its
paths. No write intent may reach *or equal* the consumer repository or the
installed catalog subtrees, and no write intent may carry a relative path at
all. Intent is what a hook can see that a filesystem comparison cannot: a write
that failed, or one that rewrote a file with identical bytes, leaves no trace in
a tree snapshot.

*The filesystem.* The consumer repository's complete type/mode/link/bytes state
is captured before and after the whole session and must be identical. This is
the only proof that also covers the provider worker, which is a separate
interpreter the parent's audit hook cannot observe, and it is why the audit hook
is a complement rather than a substitute.

The mutating and excluded providers the T4 fixture tree declares write
payload-side sentinels when their bytes execute, so their absence is the witness
that no worker was ever created for them.

**Two bounds, recorded rather than hidden** (T9.2 Codex RED review, F4/F9, both
dispositioned against ADR 0025's trust model). Neither the provider worker's
writes nor its reads are instrumented, and a write that restored a file to
identical bytes is not detected. That is deliberate: installed payloads are
digest-verified *trusted* bytes, so the threat this suite polices is the
adapter or the facade reaching a write path — not an adversarial payload
concealing one. A payload that wanted to write could do so from any CLI
invocation of the same dispatcher, and the MCP surface neither widens nor
narrows that. What still constrains the worker here is the ``tree_state``
comparison, which sees any process's net effect, and the payload-side sentinels,
which fire when unapproved provider bytes execute at all.

**Harness reuse, stated exactly.** ``test_transport.py`` owns the subprocess and
capability machinery, ``test_resources.py`` owns the era machinery and the
recording-facade launch, ``test_standard_read.py`` owns the tool-call probes,
``test_discovery_tools.py`` owns the structured-result probes,
``test_consumer_tools.py`` owns the T9 fixtures and the planned-absence
assertion, and ``tests/mcp_services`` owns the provider tree and the
``tree_state`` capture. The one thing added here is the write-audit prologue,
because T8's filesystem prologue records ``open`` without its mode or flags and
therefore cannot tell a read from a write. It carries its own falsifiability
control: ``test_write_audit_prologue_records_writes_and_ignores_reads`` performs
a named write, a read, a mutator applied to the watched root itself, and a
directory-descriptor write with a relative name, and requires each to be
classified the way the acceptance assertions depend on — so "no write was
attempted" is falsifiable in every direction it claims.
"""

from __future__ import annotations

import ast
import importlib
import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

import pytest

from project_standards._version import package_version
from project_standards.control_plane.distribution import InstalledDistribution
from tests.mcp_server.test_consumer_tools import (
    CONSUMER_TOOLS,
    build_provider_runtime,
    plant_excluded_content,
    require_consumer_tools,
)
from tests.mcp_server.test_discovery_tools import (
    REPO_INSPECT,
    REPO_ROOT_ARGUMENT,
    STANDARDS_LIST,
    rendered,
    structured,
)
from tests.mcp_server.test_resources import (
    CATALOG_URI,
    FIXTURE_SUBTREES,
    MODERN_ERA,
    oracle_facade,
    resource_session,
    spy_launch,
)
from tests.mcp_server.test_standard_read import (
    TOOL_NAME as STANDARD_READ,
)
from tests.mcp_server.test_standard_read import (
    call_tool,
    list_tools,
    tool_names,
)
from tests.mcp_server.test_transport import (
    FROZEN_V1_TOOLS,
    ServerProcess,
    as_object,
    assert_capabilities_match_reachable_registrations,
    assert_no_write_surface,
    assert_stdout_is_protocol_only,
    declared_capabilities,
    require_adapter_module,
    require_mcp_subcommand,
)
from tests.mcp_services.test_consumer import tree_state
from tests.mcp_services.test_providers import (
    build_provider_repo,
    mutating_provider_ran,
)

ADAPTER_PACKAGE = "project_standards.mcp_server"

# The authoritative write path, by owning module and exact symbol. plan:439:
# "`mcp_server` must not import `apply_reconciliation`, `apply_authoring_plan`,
# mutation schemas, provider entrypoints, or provider declarations directly."
# Each name is confirmed to exist in its module before the adapter is searched
# for it, so this test cannot pass because a symbol was renamed upstream.
FORBIDDEN_AUTHORITY_SYMBOLS: dict[str, tuple[str, ...]] = {
    "project_standards.control_plane.executor": (
        "apply_reconciliation",
        "apply_authoring_plan",
        "apply_managed_restore",
        "apply_legacy_migration",
    ),
    "project_standards.control_plane.recovery": ("apply_recovery",),
    "project_standards.control_plane.schemas": (
        "MutationPlanSchema",
        "MutationActionSchema",
        "MutationDiagnosticSchema",
    ),
    "project_standards.control_plane.providers": ("invoke_provider",),
    "project_standards.package_contract.payload": (
        "ProviderDeclaration",
        "ProviderEffect",
        "ProviderOperation",
    ),
}

# Module-level names that would advertise an apply or write callable on the
# adapter's own surface, whatever they delegated to.
APPLY_CALLABLE_PREFIXES = ("apply", "write", "mutate", "fix_", "commit")

# Audit events that are writes by definition. `open` is classified separately,
# by its flags, because it is the only one of these that is usually a read.
MUTATING_AUDIT_EVENTS = (
    "os.rename",
    "os.remove",
    "os.mkdir",
    "os.rmdir",
    "os.link",
    "os.symlink",
    "os.chmod",
    "os.chown",
    "os.truncate",
    "os.utime",
    "shutil.copyfile",
    "shutil.copymode",
    "shutil.copystat",
    "shutil.copytree",
    "shutil.move",
    "shutil.rmtree",
    "shutil.unpack_archive",
)

WR_PREFIX = "T9-WR "

# Installed before any distribution module is imported, so no lazy import and no
# helper module can perform an unobserved write. Write *intent* is recorded, not
# effect: a failed write and a rewrite with identical bytes are both invisible to
# a filesystem comparison and both visible here.
#
# Every write-intent event is recorded regardless of location, because the
# `dir_fd` forms reach the hook with a relative name that no root prefix can
# match; reads are recorded only under the watched roots, since the import system
# reads the whole distribution and burying the record in that traffic would make
# the control below unreadable.
#
# One residual bound, recorded rather than hidden: a write performed against an
# already-open descriptor (`open(fd, "w")`, as the SDK's stdio writer does) has
# no path operand at all, so it is not recorded. The file behind such a
# descriptor was opened by name first, and that open carries the write flags, so
# the intent is still observable — one event earlier.
WRITE_AUDIT_PROLOGUE = '''
import json as _wr_json
import os as _wr_os
import sys as _wr_sys

_WR_WATCHED = tuple(__WATCHED__)
_WR_SELFTEST = __SELFTEST__
_WR_MUTATORS = frozenset(__MUTATORS__)
_WR_WRITE_FLAGS = (
    _wr_os.O_WRONLY | _wr_os.O_RDWR | _wr_os.O_CREAT | _wr_os.O_TRUNC | _wr_os.O_APPEND
)


def _wr_is_write(event, arguments):
    """Whether this event asked to modify something."""
    if event != "open":
        return True
    flags = arguments[2] if len(arguments) > 2 else None
    if isinstance(flags, int):
        return bool(flags & _WR_WRITE_FLAGS)
    mode = arguments[1] if len(arguments) > 1 else None
    return isinstance(mode, str) and any(character in mode for character in "wxa+")


def _wr_paths(event, arguments):
    """The path operands of one event, and nothing else.

    `open` carries (path, mode, flags), so only the first operand is a path: a
    blanket string filter would record the *mode* as one, which is both noise and
    a way for an fd-based reopen to look like a named file. Every other watched
    event carries paths as its string operands and integers for modes and
    descriptors.
    """
    if event == "open":
        first = arguments[0] if arguments else None
        return [first] if isinstance(first, str) else []
    return [item for item in arguments if isinstance(item, str)]


def _wr_audit(event, arguments):
    if event != "open" and event not in _WR_MUTATORS:
        return
    paths = _wr_paths(event, arguments)
    if not paths:
        return
    write = _wr_is_write(event, arguments)
    if not write and not any(path.startswith(_WR_WATCHED) for path in paths):
        return
    print(
        "__WR_PREFIX__" + _wr_json.dumps({"event": event, "paths": paths, "write": write}),
        file=_wr_sys.stderr,
        flush=True,
    )


_wr_sys.addaudithook(_wr_audit)

if _WR_SELFTEST is not None:
    # Falsifiability, in four directions (T9.2 Codex RED review, F4). Each of
    # these is a way a real write could reach the repository, and each must be
    # visible to the classifier that later has to report their absence.
    #
    #   1. a named write under a watched root      -> recorded, write
    #   2. a read of the same path                 -> recorded, not a write
    #   3. a mutator whose path IS the watched root -> recorded, write
    #      (prefix matching alone misses the root itself)
    #   4. a `dir_fd` write with a relative name    -> recorded with an
    #      unresolvable path, which is why every relative write intent is
    #      refused conservatively rather than matched against a name list
    with open(_WR_SELFTEST, "w", encoding="utf-8") as _wr_handle:
        _wr_handle.write("probe")
    with open(_WR_SELFTEST, encoding="utf-8") as _wr_handle:
        _wr_handle.read()

    _wr_root = _wr_os.path.dirname(_WR_SELFTEST)
    _wr_os.utime(_wr_root)

    _wr_directory = _wr_os.open(_wr_root, _wr_os.O_RDONLY | _wr_os.O_DIRECTORY)
    try:
        _wr_relative = _wr_os.open(
            "__SELFTEST_RELATIVE__",
            _wr_os.O_WRONLY | _wr_os.O_CREAT | _wr_os.O_TRUNC,
            0o600,
            dir_fd=_wr_directory,
        )
        _wr_os.close(_wr_relative)
    finally:
        _wr_os.close(_wr_directory)
'''

# The relative name the prologue's `dir_fd` self-test writes. Named here because
# the control has to find that exact record, and the acceptance test has to know
# that no such write happened on its own launch.
SELFTEST_RELATIVE_NAME = "audit-selftest-dir-fd.txt"


def write_audited_launch(
    package_root: Path, *, watch: Sequence[Path], selftest: Path | None = None
) -> str:
    """The reused recording-facade launch, with the write audit installed first.

    Composition rather than a fork: ``test_resources.spy_launch`` still produces
    the whole server script, and the prologue is prepended so the hook is
    installed before any distribution module is imported.
    """
    prologue = (
        WRITE_AUDIT_PROLOGUE.replace("__WATCHED__", repr([f"{path.resolve()}/" for path in watch]))
        .replace("__SELFTEST__", repr(None if selftest is None else str(selftest.resolve())))
        .replace("__SELFTEST_RELATIVE__", SELFTEST_RELATIVE_NAME)
        .replace("__MUTATORS__", repr(list(MUTATING_AUDIT_EVENTS)))
        .replace("__WR_PREFIX__", WR_PREFIX)
    )
    return prologue + spy_launch(package_root)


def write_records(server: ServerProcess) -> list[dict[str, Any]]:
    """Every filesystem event the audited server has reported so far."""
    records: list[dict[str, Any]] = []
    for line in bytes(server.stderr_bytes).decode("utf-8", "replace").splitlines():
        if line.startswith(WR_PREFIX):
            records.append(as_object(json.loads(line.removeprefix(WR_PREFIX)), "an audit record"))
    return records


def record_paths(record: dict[str, Any]) -> list[str]:
    return [str(item) for item in cast("list[object]", record.get("paths", []))]


def contained_by(path: str, roots: Sequence[Path]) -> bool:
    """Whether one recorded path is a watched root or lies under one.

    Equality counts. An earlier revision compared against ``f"{root}/"`` only,
    which silently exempted every mutator applied to the watched root *itself* —
    ``os.rmdir(repo)``, ``os.chmod(repo)``, ``os.rename(repo, ...)`` — the most
    destructive operations of the set (T9.2 Codex RED review, F4).
    """
    candidate = Path(path)
    return any(
        candidate == root.resolve() or candidate.is_relative_to(root.resolve()) for root in roots
    )


def writes_under(records: Sequence[dict[str, Any]], roots: Sequence[Path]) -> list[dict[str, Any]]:
    """Every recorded write intent whose paths reach or equal one of the watched roots."""
    return [
        record
        for record in records
        if record.get("write") and any(contained_by(path, roots) for path in record_paths(record))
    ]


def unresolvable_writes(records: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every recorded write intent whose path cannot be attributed to a root.

    A write issued against a directory descriptor reaches the audit hook as a
    *relative* name with no resolvable root, so containment cannot be decided for
    it. The rule is conservative rejection rather than a name list: an earlier
    revision refused only three control-plane basenames, which left every other
    ``dir_fd`` write to the repository unobserved. Any relative write intent at
    all is a finding here — the server's own read path uses ``dir_fd`` only with
    ``O_RDONLY``, so a relative *write* has no legitimate source in this process.
    """
    return [
        record
        for record in records
        if record.get("write")
        and any(not Path(path).is_absolute() for path in record_paths(record))
    ]


def adapter_sources() -> list[Path]:
    package = require_adapter_module("")
    package_file = package.__file__
    assert package_file is not None, f"{ADAPTER_PACKAGE} must live in a real directory"
    return sorted(Path(package_file).parent.rglob("*.py"))


@pytest.fixture(scope="module")
def provider_runtime(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The provider-declaring fixture catalog, built by the T9 suite's own helper."""
    return build_provider_runtime(tmp_path_factory.mktemp("no-writes"))


@pytest.fixture(scope="module")
def provider_distribution(provider_runtime: Path) -> InstalledDistribution:
    return InstalledDistribution(
        provider_runtime / "project_standards", tool_release=package_version()
    )


@pytest.fixture(scope="module")
def planned_repo(
    provider_distribution: InstalledDistribution, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    """One initialized consumer repository with pending reconciliation work.

    Pending work is the point: a repository with nothing to do would prove
    nothing about a tool that declined to apply anything.
    """
    parent = tmp_path_factory.mktemp("no-writes-consumer")
    repo = build_provider_repo(parent, "planned", distribution=provider_distribution)
    plant_excluded_content(repo)
    return repo


# -- RED controls and permanent negatives --------------------------------------


def test_write_audit_prologue_records_writes_and_ignores_reads(
    provider_runtime: Path, tmp_path: Path
) -> None:
    """RED control: the write oracle is falsifiable in every direction it claims.

    ``test_registry_and_calls_cannot_reach_writes_or_apply`` claims that no write
    intent reaches the consumer repository or the installed catalog. An oracle
    that could not see a write, or that classified every ``open`` as one, would
    satisfy that claim by being blind or by being useless — and one that matched
    only ``root + "/"`` would satisfy it while exempting the root itself. So the
    prologue's self-test performs four operations and each classification is
    required to appear (T9.2 Codex RED review, F4):

    * a named write under a watched root — recorded, and classified as a write;
    * a read of the same path — recorded, and *not* classified as a write;
    * ``os.utime`` on the watched root itself — recorded as a write and reported
      by :func:`writes_under`, which is the equality case a prefix match drops;
    * an ``O_WRONLY|O_CREAT`` write through a directory descriptor with a
      relative name — recorded with an unresolvable path and reported by
      :func:`unresolvable_writes`, which is why the acceptance test refuses every
      relative write intent rather than checking a list of file names.

    The same launch also establishes that the conservative rule is *satisfiable*:
    apart from the self-test's own, a server that starts up and answers the
    already-registered tools produces no relative write intent at all. Without
    that, the acceptance assertion could be unfalsifiable in the other direction —
    permanently red for reasons that have nothing to do with T9.
    """
    require_mcp_subcommand()
    era = MODERN_ERA
    probe = tmp_path / "audit-probe.txt"
    script = write_audited_launch(
        provider_runtime / "project_standards", watch=[tmp_path], selftest=probe
    )
    with resource_session(
        era, runtime_root=provider_runtime, label="write-control", script=script
    ) as (
        server,
        _,
    ):
        server.drain(0.5)
        records = write_records(server)
        probed = [record for record in records if str(probe) in record_paths(record)]
        assert [record for record in probed if record.get("write")], server.diagnosis(
            f"the prologue recorded no write for its own self-test write: {records!r}"
        )
        assert [record for record in probed if not record.get("write")], server.diagnosis(
            "the prologue recorded no read for its own self-test read, so every `open` is "
            f"being classified as a write: {records!r}"
        )

        # The equality case: a mutator applied to the watched root itself.
        exact = [
            record
            for record in writes_under(records, [tmp_path])
            if str(tmp_path.resolve()) in record_paths(record)
        ]
        assert exact, server.diagnosis(
            "a mutator applied to the watched root itself was not reported as contained; a "
            f"prefix-only match would exempt exactly that case: {records!r}"
        )

        # The unresolvable case: a `dir_fd` write with a relative name.
        relative = [
            record
            for record in unresolvable_writes(records)
            if SELFTEST_RELATIVE_NAME in record_paths(record)
        ]
        assert relative, server.diagnosis(
            "the prologue's dir_fd write was not recorded as an unresolvable write intent, so "
            f"the conservative rule could never fire: {records!r}"
        )

        # And the rule is satisfiable: nothing else in a live session is relative.
        baseline = [
            record
            for record in unresolvable_writes(records)
            if SELFTEST_RELATIVE_NAME not in record_paths(record)
        ]
        assert not baseline, server.diagnosis(
            "a server startup produced relative write intents of its own, so conservative "
            f"rejection would fail for reasons unrelated to T9: {baseline!r}"
        )
        assert server.finish() == 0


def test_adapter_never_names_apply_mutation_or_provider_entrypoints() -> None:
    """plan:439 / FR-018: the adapter cannot reach the write path by name.

    A permanent negative rather than a phase one, and deliberately independent of
    the import-direction contract in ``contract/test_import_boundary.py``: that
    suite allows ``entrypoint`` and ``repo_access`` to import the control plane,
    and nothing in it stops an allowlisted module from reaching an apply callable
    once it has. This searches every adapter source, including those two, for the
    exact authoritative symbols.

    Each forbidden symbol is first resolved in its owning module. Without that,
    a renamed or misspelled expectation would make the whole test vacuously
    green — the failure mode an absence assertion always has.
    """
    for module_name, symbols in FORBIDDEN_AUTHORITY_SYMBOLS.items():
        module = importlib.import_module(module_name)
        missing = [name for name in symbols if not hasattr(module, name)]
        assert not missing, (
            f"{module_name} no longer declares {missing}; this suite's absence assertion would "
            "be vacuous until the expectation is refreshed"
        )

    forbidden = sorted(
        {name for symbols in FORBIDDEN_AUTHORITY_SYMBOLS.values() for name in symbols}
    )
    offenders: dict[str, list[str]] = {}
    for source in adapter_sources():
        text = source.read_text(encoding="utf-8")
        found = [name for name in forbidden if re.search(rf"\b{re.escape(name)}\b", text)]
        if found:
            offenders[source.name] = found
    assert not offenders, (
        "adapter modules name the authoritative apply, mutation-schema, provider-entrypoint, or "
        f"provider-declaration surface: {offenders}"
    )

    # And no apply-shaped callable on the adapter's own surface, whatever it
    # would have delegated to.
    advertised: dict[str, list[str]] = {}
    for source in adapter_sources():
        if source.name == "__init__.py":
            continue
        tree = ast.parse(source.read_text(encoding="utf-8"))
        named = [
            node.name
            for node in tree.body
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
            and node.name.lstrip("_").lower().startswith(APPLY_CALLABLE_PREFIXES)
        ]
        if named:
            advertised[source.name] = named
    assert not advertised, f"the adapter declares apply- or write-shaped callables: {advertised}"


# -- frozen acceptance test ----------------------------------------------------


def test_registry_and_calls_cannot_reach_writes_or_apply(
    provider_runtime: Path,
    provider_distribution: InstalledDistribution,
    planned_repo: Path,
) -> None:
    """TC-T9-003 (FR-018, FR-019): every v1 tool, called, writing nothing.

    The registry half and the call half are one test because separating them
    would let each pass for the wrong reason: a registry of read-only names
    proves nothing if a handler writes, and a session that wrote nothing proves
    nothing if a mutating tool was simply never called. So every advertised tool
    is called — the whole frozen six, checked to be exactly the advertised set —
    against a repository with pending reconciliation work, and three independent
    oracles run across that session.

    *Write intent*, from the audit hook installed before any distribution module
    is imported. No ``open`` with write flags and no ``os``/``shutil`` mutator may
    reach *or equal* the consumer repository or the installed catalog subtrees,
    and no write intent may carry a relative path at all. The second rule is
    conservative by design: a write issued through a directory descriptor arrives
    with a name no root can be matched against, so it is refused rather than
    filtered against a list of file names that would miss every other target
    (T9.2 Codex RED review, F4).

    *Filesystem state*, from a complete type/mode/symlink/bytes capture of the
    repository before and after the session. This is the only oracle that also
    covers the provider worker, which is a separate interpreter the parent's hook
    cannot observe.

    *Provider execution*, from the payload-side sentinels the declared mutating
    (``fix``, ``mutation-plan`` effect) and excluded (``semantic-review``)
    providers write when their bytes run. Their absence is the witness that no
    worker was created for an unapproved operation.

    A repository with pending work is deliberate: ``reconcile_preview`` over a
    fully reconciled repository would have nothing to apply even if it tried.

    **What FR-019 means here, exactly.** FR-019 governs *future* write tools —
    "if controlled writes are later added, apply tools shall use the control
    plane's stale-plan and precondition checks" — and SPEC-MS01 defers its actual
    stale-plan/path-escape/approval tests to a later specification. This test
    cannot and does not bind a future implementation. What it establishes is
    FR-019's v1 satisfaction: the *proven absence* of any write or apply surface,
    which is what makes the future clause dormant rather than unmet. Adding a
    write tool requires an approved ADR 0025 amendment (the record allows no new
    operation without one), and that amendment is the point at which FR-019's
    substantive obligations become testable (T9.2 Codex RED review, F8).
    """
    require_mcp_subcommand()
    era = MODERN_ERA
    package_root = provider_runtime / "project_standards"
    watched = [*(package_root / name for name in FIXTURE_SUBTREES), planned_repo.parent]
    script = write_audited_launch(package_root, watch=watched)
    root_arguments = {REPO_ROOT_ARGUMENT: str(planned_repo)}
    call_arguments: dict[str, dict[str, Any]] = {
        STANDARDS_LIST: {},
        STANDARD_READ: {"uri": CATALOG_URI},
        REPO_INSPECT: root_arguments,
        **dict.fromkeys(CONSUMER_TOOLS, root_arguments),
    }

    facade = oracle_facade(provider_runtime)
    assert facade.reconcile(planned_repo).actions, (
        "the fixture repository has no pending reconciliation work, so a tool that tried to "
        "apply something would have nothing to write"
    )
    before = tree_state(planned_repo)

    with resource_session(era, runtime_root=provider_runtime, label="no-writes", script=script) as (
        server,
        result,
    ):
        require_consumer_tools(server, era)
        reachable = assert_capabilities_match_reachable_registrations(
            server, declared_capabilities(result), envelope=era.envelope
        )
        assert_no_write_surface(server, reachable)

        entries = list_tools(server, era)
        advertised = set(tool_names(entries))
        assert advertised == set(FROZEN_V1_TOOLS), server.diagnosis(
            f"the v1 registry is complete at T9 and read-only by construction; advertised "
            f"{sorted(advertised)}"
        )
        assert set(call_arguments) == advertised, server.diagnosis(
            "every advertised tool must be called here, or a mutating handler could hide behind "
            f"a name this test skipped: {sorted(advertised - set(call_arguments))}"
        )

        for name in sorted(advertised):
            structured(
                server,
                call_tool(server, era, name=name, arguments=call_arguments[name]),
                label=name,
            )
        server.drain(1.0)

        records = write_records(server)
        trespass = writes_under(records, watched)
        assert not trespass, server.diagnosis(
            f"a registered tool call attempted a write under or at the consumer repository or "
            f"the installed catalog: {rendered(trespass)}"
        )
        unresolvable = unresolvable_writes(records)
        assert not unresolvable, server.diagnosis(
            "a registered tool call attempted a write whose path cannot be attributed to any "
            "root — a directory-descriptor write, which this suite refuses conservatively "
            f"because containment cannot be decided for it: {rendered(unresolvable)}"
        )
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)

    assert tree_state(planned_repo) == before, (
        "the consumer repository changed across a read-only session; every v1 tool is read-only "
        "and the provider worker is bound by the same rule"
    )
    assert not mutating_provider_ran(provider_distribution), (
        "a declared mutating or excluded provider executed, so an unapproved operation reached "
        "a worker process"
    )
