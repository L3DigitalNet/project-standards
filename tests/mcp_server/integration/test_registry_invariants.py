"""Growth changes data, never the registry — and CI runs the proof (T10, TC-T10-003).

Covers FR-018, NFR-001, NFR-008, and NFR-009 as one acceptance: "CI runs MCP
suites and proves no remote/write surface".

**NFR-001 is a scalability requirement stated as an invariance.** "Adding a
standard shall not require adding a top-level MCP tool", verified by a "fixture
standard test [that] verifies tool list unchanged while resources/metadata
update". T6 already proves that for one generated family against the tool list
that existed then — a list of *zero* tools. The invariance only becomes
interesting once the registry is complete, and it has to cover more than the
names: a server that kept six tools but rewrote a description, an input schema, or
the instructions string when a package appeared would still have made the
top-level surface a function of the catalog. So the whole advertised surface is
compared byte for byte across the growth, and the growth is three families rather
than one, because a per-standard registration defect could be invisible at n=1.

**The negatives are asserted against the live server, not against the source.**
T5's ``test_no_remote_transport_entry_point_exists_in_the_adapter_or_cli`` already
scans every adapter and CLI source file for an HTTP/SSE entry point, and T9's
``tests/mcp_server/security/test_no_writes.py`` already audits syscalls. Repeating
either would be the duplication T10.5 exists to remove. What is asserted instead is
what those suites cannot see: that *after* the catalog has grown, the running
server still advertises no capability, tool, tool input, or launch option through
which a remote transport or a write could be reached.

**CI presence is execution, not phase membership.** NFR-009 requires the protocol,
package fixture, and repository fixture tests to run in CI; it says nothing about
*which* phase. The first revision of this file froze an ordinary-phase-only policy
and forbade the ``compatibility`` marker, which invents a rule NFR-009 does not
state and would become a time bomb at T11, since ``check.yml`` deliberately runs a
compatibility phase (T10.2 Codex RED review, F10). What is proved here instead is
the requirement's own claim: every required node is selected by the **union** of the
executable pytest phases across every workflow file, ``*.yml`` and ``*.yaml`` alike.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import yaml

from tests.mcp_server.test_consumer_tools import ALLOWED_INPUT_PROPERTIES
from tests.mcp_server.test_discovery_tools import rendered
from tests.mcp_server.test_resources import (
    MODERN_ERA,
    Era,
    add_generated_family,
    build_fixture_runtime,
    list_resources,
    list_templates,
    metadata_document,
    oracle_facade,
    resource_session,
)
from tests.mcp_server.test_standard_read import list_tools, tool_names
from tests.mcp_server.test_transport import (
    CLI_LAUNCH,
    FROZEN_V1_TOOLS,
    REMOTE_CLI_OPTION_TOKENS,
    ServerProcess,
    as_object,
    assert_capabilities_match_reachable_registrations,
    assert_no_list_change_promises,
    assert_no_write_surface,
    assert_stdout_is_protocol_only,
    boundary_option_name,
    declared_capabilities,
    require_mcp_subcommand,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_DIRECTORY = REPO_ROOT / ".github/workflows"

# Both extensions GitHub accepts. Scanning only `*.yml` would miss a workflow that
# used the other spelling (review F10).
WORKFLOW_SUFFIXES = ("*.yml", "*.yaml")

#: Flags that change *where* tests run rather than *which* are selected, and whose
#: plugins are not loaded for a plain collection. Dropped with their values before
#: the collector is asked what a phase selects.
DISTRIBUTION_FLAGS = ("-n", "--dist", "--max-worker-restart", "--numprocesses")

#: The MCP node ids and paths NFR-009 requires CI to execute. Node ids rather than
#: directories alone, so a suite that stopped being collected — a lost package
#: marker, an import error, a renamed frozen contract — fails here rather than
#: quietly leaving the gate.
REQUIRED_CI_NODES = (
    "tests/mcp_services",
    "tests/mcp_server",
    "tests/mcp_server/contract/test_protocol_conformance.py",
    "tests/mcp_server/contract/test_determinism.py",
    "tests/mcp_server/contract/test_no_recommendations.py",
    "tests/mcp_server/contract/test_import_boundary.py",
    "tests/mcp_server/integration/test_server.py",
    "tests/mcp_server/integration/test_registry_invariants.py",
    "tests/mcp_server/security/test_no_writes.py",
)

# Three families rather than one: a registration defect that scaled with the
# catalog could be invisible at n=1, and the point of NFR-001 is exactly that
# scaling.
GROWTH_FAMILIES = (
    ("t10growth-one", "1.0"),
    ("t10growth-two", "2.5"),
    ("t10growth-three", "9.9"),
)


def advertised_surface(server: ServerProcess, era: Era) -> dict[str, list[Any]]:
    """Everything about the server that must not depend on the installed catalog."""
    return {
        "tools": sorted(
            [
                str(entry.get("name")),
                str(entry.get("title")),
                str(entry.get("description")),
                rendered(entry.get("inputSchema")),
                rendered(entry.get("outputSchema")),
            ]
            for entry in list_tools(server, era)
        ),
        "templates": sorted(str(entry.get("uriTemplate")) for entry in list_templates(server, era)),
    }


def workflow_document(path: Path) -> dict[str, Any]:
    """One parsed workflow file, or an explicit assertion naming what is missing."""
    assert path.is_file(), f"the workflow {path} does not exist"
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict), f"{path} is not a workflow mapping"
    return dict(cast("dict[str, Any]", loaded))


def workflow_commands(document: Mapping[str, Any]) -> list[str]:
    """Every ``run:`` script in one workflow, flattened across jobs and steps."""
    commands: list[str] = []
    jobs = document.get("jobs")
    if not isinstance(jobs, dict):
        return commands
    for job in cast("dict[str, object]", jobs).values():
        steps = as_object(job, "a workflow job").get("steps")
        if not isinstance(steps, list):
            continue
        for step in cast("list[object]", steps):
            script = as_object(step, "a workflow step").get("run")
            if isinstance(script, str):
                commands.append(script)
    return commands


def pytest_phases() -> list[tuple[Path, list[str]]]:
    """Every executable pytest invocation in every workflow, as argument lists.

    The ``uv run``/``coverage run`` prefixes are stripped so what remains is the
    argument vector pytest itself receives, which is what decides selection. A
    command that cannot be parsed is returned rather than skipped, so a shell form
    this helper does not understand fails the coverage assertion instead of
    silently shrinking the union.
    """
    phases: list[tuple[Path, list[str]]] = []
    for pattern in WORKFLOW_SUFFIXES:
        for path in sorted(WORKFLOW_DIRECTORY.glob(pattern)):
            for command in workflow_commands(workflow_document(path)):
                if "pytest" not in command:
                    continue
                for line in command.splitlines():
                    if "pytest" not in line:
                        continue
                    tokens = shlex.split(line)
                    if "pytest" not in tokens and "-m" not in tokens:
                        continue
                    index = next(
                        (
                            position
                            for position, token in enumerate(tokens)
                            if token == "pytest" or token.endswith("/pytest")
                        ),
                        None,
                    )
                    if index is None:
                        continue
                    phases.append((path, tokens[index + 1 :]))
    return phases


def collected_nodes(arguments: list[str]) -> set[str]:
    """Every node id one pytest argument vector selects, from pytest's own collector.

    Run rather than reasoned about: ``testpaths``, marker expressions, and path
    arguments interact, and the only authority on what a command selects is the
    collector. Distribution flags that need a plugin at runtime are dropped, since
    they change *where* tests run rather than *which* are selected.
    """
    stripped: list[str] = []
    skip = False
    for token in arguments:
        if skip:
            skip = False
            continue
        if token in DISTRIBUTION_FLAGS:
            # A separated flag takes the next token as its value; dropping the flag
            # alone would leave `4` behind, which pytest reads as a path argument
            # and refuses to collect.
            skip = True
            continue
        if any(token.startswith(f"{flag}=") for flag in DISTRIBUTION_FLAGS):
            continue
        stripped.append(token)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *stripped, "--collect-only", "-q", "--no-header"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    assert result.returncode in (0, 5), (
        f"collecting `pytest {' '.join(stripped)}` failed:\n{result.stdout[-4000:]}\n"
        f"{result.stderr[-2000:]}"
    )
    return {
        line.split("::", 1)[0] if "::" in line else line
        for line in result.stdout.splitlines()
        if line.startswith("tests/")
    }


# -- acceptance ----------------------------------------------------------------


def test_package_growth_adds_data_only_and_registry_has_no_remote_or_write_surface(
    tmp_path: Path,
) -> None:
    """TC-T10-003 (FR-018, NFR-001, NFR-008): the registry is catalog-independent.

    One fixture runtime, two sessions, three new standard families in between.

    *What must not change.* The declared capability set, every tool's name, title,
    description, input schema and output schema, the resource templates, and the
    instructions string — all compared byte for byte, because NFR-001's failure
    mode is a *top-level* surface that grows with the catalog and a rewritten
    description is that failure wearing different clothes.

    *What must change.* The concrete resource listing gains exactly one entry per
    added family, and the catalog resource's body carries the new standards.
    Without this half the invariance would be satisfied by a server that ignored
    the growth entirely, which is not scalability.

    *What must be absent, after the growth.* No capability, tool, tool input, or
    launch option through which a remote transport or a write could be reached.
    The scan is over the *live* surface rather than the source, because T5 and T9
    own the source and syscall halves; growth is the event this test exists to run
    them after.
    """
    require_mcp_subcommand()
    era = MODERN_ERA
    runtime = build_fixture_runtime(tmp_path / "growth")
    package_root = runtime / "project_standards"

    with resource_session(era, runtime_root=runtime, label="growth-before", script=CLI_LAUNCH) as (
        server,
        opened,
    ):
        before_capabilities = declared_capabilities(opened)
        reachable = assert_capabilities_match_reachable_registrations(
            server, before_capabilities, envelope=era.envelope
        )
        assert_no_list_change_promises(before_capabilities)
        assert_no_write_surface(server, reachable)
        before_surface = advertised_surface(server, era)
        before_instructions = opened.get("instructions")
        before_resources = sorted(str(entry.get("uri")) for entry in list_resources(server, era))
        before_catalog = metadata_document(server, era, "standards://catalog/5")
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)

    assert before_surface["tools"], "the pre-growth session advertised no tool to hold invariant"

    for standard_id, version in GROWTH_FAMILIES:
        add_generated_family(package_root, standard_id=standard_id, version=version)
    grown_catalog = oracle_facade(runtime).catalog()
    grown_ids = {descriptor.standard_id for descriptor in grown_catalog.standards}
    assert {standard_id for standard_id, _ in GROWTH_FAMILIES} <= grown_ids, (
        f"the growth fixture did not reach the installed catalog: {sorted(grown_ids)}"
    )

    with resource_session(era, runtime_root=runtime, label="growth-after", script=CLI_LAUNCH) as (
        server,
        opened,
    ):
        after_capabilities = declared_capabilities(opened)
        reachable = assert_capabilities_match_reachable_registrations(
            server, after_capabilities, envelope=era.envelope
        )
        assert_no_list_change_promises(after_capabilities)
        assert_no_write_surface(server, reachable)
        after_surface = advertised_surface(server, era)
        after_instructions = opened.get("instructions")
        after_resources = sorted(str(entry.get("uri")) for entry in list_resources(server, era))
        after_catalog = metadata_document(server, era, "standards://catalog/5")

        assert rendered(after_capabilities) == rendered(before_capabilities), server.diagnosis(
            "adding standards changed the declared capability set.\n"
            f"before: {rendered(before_capabilities)}\nafter:  {rendered(after_capabilities)}"
        )
        assert after_surface == before_surface, server.diagnosis(
            "adding standards changed the top-level tool surface, which NFR-001 forbids.\n"
            f"before: {json.dumps(before_surface, indent=2)}\n"
            f"after:  {json.dumps(after_surface, indent=2)}"
        )
        assert after_instructions == before_instructions, server.diagnosis(
            "adding standards changed the instructions string, which ADR 0026 makes a frozen fact "
            f"of the registry rather than of the catalog.\n{after_instructions!r}"
        )

        added = sorted(set(after_resources) - set(before_resources))
        assert len(added) == len(GROWTH_FAMILIES), server.diagnosis(
            f"growth added {len(added)} resource entries for {len(GROWTH_FAMILIES)} families: "
            f"{added}"
        )
        assert not set(before_resources) - set(after_resources), server.diagnosis(
            "growth removed a previously listed resource"
        )
        assert after_catalog != before_catalog, server.diagnosis(
            "the catalog resource ignored the growth entirely, so the invariance above is "
            "satisfied by a server that serves nothing new"
        )
        for standard_id, _version in GROWTH_FAMILIES:
            assert standard_id in rendered(after_catalog), server.diagnosis(
                f"the grown catalog resource does not carry {standard_id!r}"
            )

        advertised = set(tool_names(list_tools(server, era)))
        assert advertised <= set(FROZEN_V1_TOOLS), server.diagnosis(
            f"growth introduced a tool outside the closed v1 registry: {sorted(advertised)}"
        )
        for entry in list_tools(server, era):
            schema = as_object(entry.get("inputSchema"), "an input schema")
            properties = schema.get("properties")
            declared: set[str] = (
                set(as_object(properties, "input properties")) if properties else set()
            )
            assert declared <= ALLOWED_INPUT_PROPERTIES, server.diagnosis(
                f"{entry.get('name')!r} declares an input outside the read-only set "
                f"{sorted(ALLOWED_INPUT_PROPERTIES)}: {sorted(declared)}"
            )

        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)

    help_text = require_mcp_subcommand()
    option = boundary_option_name(help_text)
    remote = [token for token in REMOTE_CLI_OPTION_TOKENS if token in option.lower()]
    assert not remote, f"the launch surface exposes a remote-transport option {option!r}: {remote}"


def test_ci_executes_every_mcp_suite_across_its_pytest_phases() -> None:
    """TC-T10-003's other half (NFR-009): CI runs these suites, in some phase.

    NFR-009's acceptance is "`uv run pytest` covers services, server registration,
    and tool outputs" — an *execution* claim. It says nothing about which phase, and
    the first revision of this test invented an ordinary-phase-only policy plus a
    marker prohibition that would have failed the moment T11 marked an
    installed-wheel test ``compatibility``, which ``check.yml`` deliberately runs
    (review F10).

    So the assertion is the requirement's own: every required MCP path is selected
    by the **union** of the executable pytest phases found across every workflow
    file, both YAML extensions. Selection is answered by running each phase's own
    argument vector under ``--collect-only``, so ``testpaths``, marker expressions,
    and path arguments are resolved by the collector rather than by a reading of
    the YAML.

    The plan's other CI constraint is checked separately and structurally: no
    workflow beyond the existing gate may run the repository suite unscoped, which
    is what "do not create a second CI workflow" means in a file this test can see.
    """
    phases = pytest_phases()
    assert phases, f"no workflow under {WORKFLOW_DIRECTORY} runs pytest"

    union: set[str] = set()
    per_phase: dict[str, set[str]] = {}
    for path, arguments in phases:
        label = f"{path.name}: pytest {' '.join(arguments)}"
        selected = collected_nodes(arguments)
        per_phase[label] = selected
        union |= selected

    missing = [
        node for node in REQUIRED_CI_NODES if not any(item.startswith(node) for item in union)
    ]
    assert not missing, (
        "these MCP paths are not selected by any CI pytest phase, so NFR-009's 'CI runs services, "
        f"server registration, and tool outputs' is not evidenced: {missing}\n"
        f"phases: {sorted(per_phase)}"
    )

    unscoped = sorted(
        {
            path
            for path, arguments in phases
            if not any(token.startswith("tests/") or token == "tests" for token in arguments)
        }
    )
    assert len(unscoped) == 1, (
        "exactly one workflow may run the repository suite unscoped; the plan forbids a second CI "
        f"workflow for these tests. Unscoped workflows: {[str(path) for path in unscoped]}"
    )


def test_ci_phase_discovery_is_not_vacuous() -> None:
    """Guard the guard: the phase extractor must find the gate it claims to read.

    ``pytest_phases`` parses shell text, so a form it did not anticipate would
    yield an empty union and the coverage assertion above would pass by finding
    nothing to check. This states the floor: the repository's own gate contributes
    at least the three phases ``check.yml`` declares, and at least one of them
    selects a marker expression, so the marker path through the extractor is
    exercised too.
    """
    phases = pytest_phases()
    from_check = [arguments for path, arguments in phases if path.name == "check.yml"]
    assert len(from_check) >= 3, (
        f"check.yml declares an ordinary, a compatibility, and a performance phase; the extractor "
        f"found {len(from_check)}: {from_check}"
    )
    assert any("-m" in arguments for arguments in from_check), (
        f"no extracted phase carries a marker expression, so that branch is untested: {from_check}"
    )
    scoped = [arguments for path, arguments in phases if path.name == "coherence.yml"]
    assert scoped and any("tests/coherence" in arguments for arguments in scoped), (
        f"the path-scoped workflow was not extracted, so the unscoped test above proves less than "
        f"it reads: {scoped}"
    )
