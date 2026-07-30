"""Truthful prompt-capability absence (T7).

Covers TC-T7-001 (FR-005): "declared prompts list/get or the server truthfully
advertises none".

Three authorities constrain every expectation here and none of them may be
re-derived by the module under test:

*FR-005* — "The server shall expose prompts only from declared prompt-role
resources and only where selected clients support them usefully." Both halves
are load-bearing: the *source* of a prompt is a declaration, and a prompt is
never an access path the client matrix requires.

*ADR 0026* — capability semantics: "Prompts: declared only when prompt-role
resources are registered, and when declared, with ``listChanged`` false;
otherwise the capability is absent"; and the v1 registry: "Prompts are
registered only from declared prompt-role resources. The server invents no
prompts of its own."

*The plan's T7 block* — "if the installed distribution has no T1-approved
prompt-role declaration, expose no prompts and advertise that truthfully — never
reinterpret ``agent-summary``, templates, or prose as prompts."

**The v1 state of that rule is absence, and it is absence for a data reason
rather than a coding one.** The installed distribution declares 22 distinct
resource roles and the fixture catalog 10, and ADR 0026 approves none of them as
a prompt role. So the tests below are not a vacuous "nothing is served by a
server that serves nothing": they first establish, from the service layer, that
a substantial declared-role inventory *is* present and reachable as resources,
and then require every one of those roles to stay a resource — no prompt, no
prompts capability, no ``prompts/list`` or ``prompts/get``, in either protocol
era.

The conditional derivation clause of plan:405 ("If prompts are approved, derive
names/content only from exact declared resources") is deliberately **not**
exercised here. Its precondition — a T1-approved prompt-role declaration — does
not exist, so a test of it would make latent derivation machinery mandatory
before any record approves a role (T7.2 Codex RED review, F2/F3, both accepted).
The absence branch alone satisfies TC-T7-001, and no implementation ABI is
asserted beyond the planned module the plan's file list names.

**The harness is reused, not re-implemented.** ``tests/mcp_server/
test_transport.py`` owns the deadline-bound subprocess, transcript, and
capability machinery; ``tests/mcp_server/test_resources.py`` owns the fixture
distribution builder, the service-layer oracle, and the era machinery. This
module imports both rather than forking copies that could drift from the T5/T6
contracts — the precedent T6.1 set and the T7.2 review upheld.

``test_prompt_probes_observe_a_prompt_surface_when_one_exists`` is the RED
control required by T7.2. Every "no prompts are served" assertion here is
unfalsifiable unless the probes can see a prompt surface that *is* there, so the
control drives the same helpers against a bare SDK server that registers one
prompt. It is a test oracle, not a sketch of the GREEN design.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest
from mcp_types import METHOD_NOT_FOUND

from project_standards._version import package_version
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.paths import CatalogMajor
from project_standards.mcp_server.models import CATALOG_MAJOR
from project_standards.mcp_services import CatalogDescriptor, McpServiceFacade
from tests.mcp_server.test_resources import (
    ERA_IDS,
    ERAS,
    Era,
    build_fixture_runtime,
    declared_resources,
    oracle_facade,
    resource_session,
)
from tests.mcp_server.test_transport import (
    CODEX_CLIENT_REVISION,
    MODERN_PROTOCOL_VERSIONS,
    RUNTIME_ROOT,
    ServerProcess,
    as_object,
    assert_capabilities_match_reachable_registrations,
    assert_modern_result_contract,
    assert_no_list_change_promises,
    assert_stdout_is_protocol_only,
    declared_capabilities,
    expect_error,
    expect_result,
    require_mcp_subcommand,
)

ADAPTER_PACKAGE = "project_standards.mcp_server"
PROMPTS_MODULE = f"{ADAPTER_PACKAGE}.prompts"

# The role plan:405 names outright, kept as a readable anchor for the two role
# families it also names by kind (templates and prose). This is not a registry:
# what the tests assert is that no declared role of any kind becomes a prompt.
PLAN_NAMED_NON_PROMPT_ROLE = "agent-summary"

# Bounded pagination follow, matching `tests/mcp_server/test_resources.py`: the
# registration set is fixed at process start, so a server that keeps handing out
# cursors is looping rather than paginating.
MAX_LIST_PAGES = 32

# RED control only. A bare SDK server that registers exactly one prompt, so the
# probes below are proven able to *see* a prompt surface before they are used to
# assert that the adapter serves none. Not a template for T7.3.
BARE_SDK_PROMPT_CONTROL = """
import anyio
import mcp_types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

CONTROL_PROMPT = "control-prompt"
CONTROL_BODY = "control prompt body"


async def _list_prompts(ctx, params):
    return types.ListPromptsResult(
        prompts=[types.Prompt(name=CONTROL_PROMPT, description="control")]
    )


async def _get_prompt(ctx, params):
    return types.GetPromptResult(
        description="control",
        messages=[
            types.PromptMessage(
                role="user", content=types.TextContent(type="text", text=CONTROL_BODY)
            )
        ],
    )


server = Server(
    "project-standards",
    version="0",
    instructions="control",
    on_list_prompts=_list_prompts,
    on_get_prompt=_get_prompt,
)


async def _serve() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


anyio.run(_serve)
"""

CONTROL_PROMPT_NAME = "control-prompt"
CONTROL_PROMPT_BODY = "control prompt body"


# -- planned surface -----------------------------------------------------------


def require_prompts_module() -> ModuleType:
    """Import the planned T7 prompt module, or fail as an explicit RED assertion.

    The plan's file list names ``mcp_server/prompts.py``, and ADR 0026 makes the
    prompt-registration decision a real decision even when its answer is "none":
    the module is where that decision lives, so its absence is asserted rather
    than inferred. The plan's RED contract requires a missing planned module to
    surface as a test assertion rather than a collection error, so nothing in
    this file imports it at module scope.

    Nothing about the module's *contents* is asserted anywhere in this file. The
    T7.2 review (F3) overturned the earlier "exactly one public collection of
    approved roles" rule as an uncontracted ABI, and it was removed: ADR 0026
    requires no invented prompts, not a public registry.
    """
    try:
        spec = importlib.util.find_spec(PROMPTS_MODULE)
    except ModuleNotFoundError:
        spec = None
    assert spec is not None, (
        f"planned module {PROMPTS_MODULE} is absent; the T7 prompt decision does not exist yet"
    )
    return importlib.import_module(PROMPTS_MODULE)


# -- catalogs ------------------------------------------------------------------


def installed_facade() -> McpServiceFacade:
    """The §5.5 facade over the *real* installed distribution this test process resolved.

    The fixture catalog is what the protocol assertions run against (T6.1), but
    FR-005's condition is a statement about the installed distribution, so its
    role inventory is read here as well. Nothing pins that inventory's
    membership — only that it is non-empty, which is what stops "no prompts" from
    being a claim about an empty catalog.
    """
    return McpServiceFacade.from_installed(
        InstalledDistribution(RUNTIME_ROOT / "project_standards", tool_release=package_version()),
        CatalogMajor(CATALOG_MAJOR),
    )


def declared_roles(catalog: CatalogDescriptor) -> frozenset[str]:
    return frozenset(
        resource.role for descriptor in catalog.standards for resource in descriptor.resources
    )


# -- protocol probes -----------------------------------------------------------


def list_prompts(server: ServerProcess, era: Era) -> list[dict[str, Any]]:
    """Every registered prompt, following pagination cursors if the server pages."""
    entries: list[dict[str, Any]] = []
    cursor: object = None
    for _ in range(MAX_LIST_PAGES):
        extra = {"cursor": cursor} if isinstance(cursor, str) else None
        result = expect_result(server, server.call("prompts/list", era.params(extra)))
        if era.modern:
            assert_modern_result_contract(server, result)
        raw = result.get("prompts")
        assert isinstance(raw, list), server.diagnosis(
            f"prompts/list returned no prompts array: {result!r}"
        )
        entries.extend(
            as_object(item, "a prompts/list entry") for item in cast("list[object]", raw)
        )
        cursor = result.get("nextCursor")
        if not isinstance(cursor, str) or not cursor:
            return entries
    raise AssertionError(server.diagnosis("prompts/list never stopped paginating"))


def get_prompt(server: ServerProcess, era: Era, name: str) -> dict[str, Any]:
    """One successful ``prompts/get`` result.

    Deliberately *not* checked against the modern list-result contract: the
    ``ttlMs``/``cacheScope`` envelope fields ride on the cacheable list and read
    results, and ``GetPromptResult`` carries neither — verified against the SDK
    by the control below, which is exactly the class of assumption a RED control
    exists to catch.
    """
    return expect_result(server, server.call("prompts/get", era.params({"name": name})))


def prompt_names(entries: Sequence[Mapping[str, Any]]) -> list[str]:
    names: list[str] = []
    for entry in entries:
        name = entry.get("name")
        assert isinstance(name, str) and name, f"a prompts/list entry carries no name: {entry!r}"
        names.append(name)
    return names


def rendered(value: Mapping[str, Any]) -> str:
    """One searchable rendering of a decoded frame, nested documents included."""
    return json.dumps(value, sort_keys=True)


@pytest.fixture(scope="module")
def full_runtime(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The fixture catalog as an importable installed distribution, shared read-only."""
    return build_fixture_runtime(tmp_path_factory.mktemp("prompts-full"))


# -- RED control ---------------------------------------------------------------


def test_prompt_probes_observe_a_prompt_surface_when_one_exists() -> None:
    """RED control (T7.2): "no prompts are served" is a falsifiable claim.

    Every prompt assertion in this file is satisfied trivially by a server that
    cannot serve prompts at all, so the probes are first driven against a bare
    SDK server that registers exactly one. It proves three things the rest of the
    file depends on: ``prompts/list`` and ``prompts/get`` are reachable when a
    prompt exists, the SDK derives the ``prompts`` capability from the registered
    handlers rather than from anything the adapter would have to assert, and the
    T5 capability equivalence recognises a populated prompt family.

    One process per era, because the SDK locks a connection's era at its opening
    request (T5.2 review F1).
    """
    with ServerProcess(BARE_SDK_PROMPT_CONTROL, label="prompt-control-classic") as server:
        result = server.handshake(CODEX_CLIENT_REVISION)
        capabilities = declared_capabilities(result)
        assert capabilities.get("prompts") is not None, (
            "the control server registers a prompt, so it must declare the capability"
        )
        assert_no_list_change_promises(capabilities)
        reachable = assert_capabilities_match_reachable_registrations(
            server, capabilities, envelope=None
        )
        assert reachable.get("prompts"), "the declared prompts capability must be reachable"
        classic = Era("classic", CODEX_CLIENT_REVISION, modern=False)
        assert prompt_names(list_prompts(server, classic)) == [CONTROL_PROMPT_NAME]
        assert CONTROL_PROMPT_BODY in rendered(get_prompt(server, classic, CONTROL_PROMPT_NAME))
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)

    version = MODERN_PROTOCOL_VERSIONS[-1]
    with ServerProcess(BARE_SDK_PROMPT_CONTROL, label="prompt-control-modern") as server:
        result = server.discover(version)
        capabilities = declared_capabilities(result)
        assert capabilities.get("prompts") is not None
        modern = Era(f"modern-{version}", version, modern=True)
        assert prompt_names(list_prompts(server, modern)) == [CONTROL_PROMPT_NAME]
        assert CONTROL_PROMPT_BODY in rendered(get_prompt(server, modern, CONTROL_PROMPT_NAME))
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


# -- frozen acceptance tests ---------------------------------------------------


def test_prompts_module_is_the_planned_registration_surface() -> None:
    """Plan T7 file list: ``mcp_server/prompts.py`` is where the prompt decision lives.

    Named because the plan names it. Nothing about its internals is asserted —
    the T7.2 review (F3) overturned the public approved-role collection as an
    uncontracted ABI, and T5's import boundary already constrains what the module
    may import.
    """
    require_prompts_module()


@pytest.mark.parametrize("era", ERAS, ids=ERA_IDS)
def test_prompts_derive_only_from_approved_resource_roles_or_are_absent(
    full_runtime: Path, era: Era
) -> None:
    """TC-T7-001 (FR-005): a full declared-role inventory, and not one prompt.

    The claim is not "a server with nothing registered serves no prompts" — that
    would be vacuous. It is that a server serving a real catalog, whose declared
    resources carry a substantial inventory of roles, still exposes no prompt,
    because ADR 0026 approves none of those roles. So the test establishes the
    inventory first, from the service layer over the same bytes the server
    serves, and only then asserts the absence:

    *The inventory is real.* The fixture catalog and the installed Catalog 5 both
    declare a non-empty set of resource roles, including the ``agent-summary``
    role plan:405 names outright as one that must never be reinterpreted.

    *The capability is absent.* ADR 0026: prompts are "declared only when
    prompt-role resources are registered ... otherwise the capability is absent".
    T5's equivalence helper then requires ``prompts/list`` to be unserved, and
    ``prompts/get`` is probed directly because a server can leave a listing empty
    while still answering a get.

    *And prompts are never an access path.* The client matrix records prompts as
    "an additive Claude Code affordance, never a required access path", so every
    declared resource must still read while the prompt surface is absent —
    exercised in both eras because Codex CLI 0.145.0 has no prompts capability at
    all and must lose nothing by it.

    *And the instructions must not promise one.* Checked with claim-shaped
    phrases rather than word-shaped ones, so a truthful denial ("no prompt is
    registered") is unaffected — the T6.4 F3 lesson, applied to the phase
    sentence T7 rewrites.
    """
    require_mcp_subcommand()
    require_prompts_module()

    facade = oracle_facade(full_runtime)
    catalog = facade.catalog()
    resources = declared_resources(catalog)
    fixture_roles = declared_roles(catalog)
    installed_roles = declared_roles(installed_facade().catalog())

    assert fixture_roles and installed_roles, (
        "both catalogs must declare resource roles, or the absence asserted below is vacuous"
    )
    assert PLAN_NAMED_NON_PROMPT_ROLE in fixture_roles & installed_roles, (
        f"{PLAN_NAMED_NON_PROMPT_ROLE!r} is the role plan:405 names outright; it must be present "
        "in both catalogs for this test to be asserting what it claims"
    )
    assert resources, "the fixture catalog declares no resource to keep as a resource"

    with resource_session(era, runtime_root=full_runtime, label="prompts-absent") as (
        server,
        result,
    ):
        capabilities = declared_capabilities(result)
        reachable = assert_capabilities_match_reachable_registrations(
            server, capabilities, envelope=era.envelope
        )
        assert_no_list_change_promises(capabilities)

        assert capabilities.get("prompts") is None, server.diagnosis(
            "no declared resource carries a prompt role approved by ADR 0026, so the prompts "
            f"capability must be absent; got {capabilities.get('prompts')!r}"
        )
        assert reachable.get("prompts") is None, server.diagnosis(
            "prompts/list is served while the capability is absent"
        )
        error = expect_error(server, server.call("prompts/get", era.params({"name": "any"})))
        assert error["code"] == METHOD_NOT_FOUND, server.diagnosis(
            f"prompts/get answered {error!r} for a server that registers no prompt"
        )

        # Every declared role stays a resource: prompts are additive, never an
        # access path, so nothing is lost by their absence.
        for uri in resources:
            contents = expect_result(
                server, server.call("resources/read", era.params({"uri": uri}))
            )
            assert contents.get("contents"), server.diagnosis(
                f"{uri} is unreadable, so the absent prompt surface removed an access path"
            )

        instructions = result.get("instructions")
        assert isinstance(instructions, str) and instructions.strip(), server.diagnosis(
            f"the server must serve a non-empty instructions string, got {instructions!r}"
        )
        promised = [
            phrase
            for phrase in (
                "/mcp__",
                "prompts are available",
                "prompts are registered",
                "available prompts",
                "use the prompt",
            )
            if phrase in instructions.lower()
        ]
        assert not promised, server.diagnosis(
            f"the instructions promise a prompt surface this build does not register: {promised}"
        )

        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)
