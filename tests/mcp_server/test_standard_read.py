"""The mandatory ``standard_read`` fallback and its client-matrix condition (T7).

Covers TC-T7-002 (FR-008): "``standard_read`` delegates to T2, rejects arbitrary
paths, and is registered whenever at least one supported primary client lacks
direct model resource access", plus the acceptance's counterfactual — "a matrix
fixture in which both clients provide direct access proves omission in only that
case".

Three authorities constrain every expectation here and none of them may be
re-derived by the module under test:

*FR-008* — "The server shall expose a generic ``standard_read`` compatibility
tool when any supported primary client cannot give the model direct resource
access ... The Step 09 compatibility matrix decides the condition; when it holds,
the tool is mandatory, delegates to the same exact-resource service as FR-003,
and cannot accept arbitrary paths."

*The T1 evidence matrix* — Codex CLI 0.145.0 has ``read_resource`` in its client
source but "model-initiated resource access is not established at 0.145.0", so
the required-fallbacks table records ``standard_read`` as REQUIRED: "Without the
tool, Codex users have no path to standard content." Claude Code 2.1.220 does
give the model direct resource access. The condition therefore holds today, and
the plan is explicit that when it holds "registration is mandatory and the
implementer has no discretion to omit it".

*The plan's T7 block and ADR 0026* — the tool's "input is one canonical resource
URI and its output is the same descriptor/bytes mapping as T6, with no path
argument", and its stop condition forbids "a second resource-reading
implementation". ADR 0026 lists ``standard_read`` in the frozen read-only v1
tool registry.

**The registration decision is evaluated, not assumed.** The plan requires the
matrix to be evaluated *mechanically*, and its acceptance requires a matrix
fixture in which both clients have direct access to prove omission in that case
alone. Both are exercised here by replacing the adapter's own client-matrix
evidence before ``create_server`` runs and observing the served tool surface, so
the condition is proven to be wired to evidence rather than to a constant.

**The harness is reused, not re-implemented.** ``tests/mcp_server/
test_transport.py`` owns the deadline-bound subprocess, transcript, and
capability machinery; ``tests/mcp_server/test_resources.py`` owns the fixture
distribution, the service-layer oracle, the era machinery, and the recording
facade that makes service-call ordering observable. This module imports both
rather than forking copies that could drift from the T5/T6 contracts.

``test_tool_probes_observe_a_registered_tool_and_its_payload`` is the RED control
required by T7.2: it drives the tool-listing, tool-call, and parity machinery
against a bare SDK server that already registers a tool, so a failure anywhere
else is provably the absent registration rather than a broken probe.
"""

from __future__ import annotations

import base64
import importlib
import importlib.util
import json
import uuid
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest
from mcp_types import INTERNAL_ERROR, INVALID_PARAMS, METHOD_NOT_FOUND

from project_standards._version import package_version
from project_standards.mcp_server.models import CATALOG_MAJOR
from tests.mcp_server.test_resources import (
    CATALOG_URI,
    ERA_IDS,
    ERAS,
    GENERATED_BINARY_RESOURCE,
    GENERATED_ID_PREFIX,
    GENERATED_VERSION,
    LEGACY_RESOURCE_NOT_FOUND,
    MODERN_ERA,
    SCHEME_PREFIX,
    Era,
    GeneratedFamily,
    add_generated_family,
    assert_structured_refusal,
    build_fixture_runtime,
    byte_canaries,
    declared_resources,
    oracle_facade,
    package_uri,
    payload_reads,
    read_frame,
    read_one,
    refusal_class,
    resource_session,
    spy_calls,
    spy_launch,
)
from tests.mcp_server.test_transport import (
    CODEX_CLIENT_REVISION,
    FROZEN_V1_TOOLS,
    MODERN_PROTOCOL_VERSIONS,
    ServerProcess,
    as_object,
    assert_capabilities_match_reachable_registrations,
    assert_modern_result_contract,
    assert_no_list_change_promises,
    assert_no_write_surface,
    assert_stdout_is_protocol_only,
    declared_capabilities,
    expect_error,
    expect_result,
    require_mcp_subcommand,
)

ADAPTER_PACKAGE = "project_standards.mcp_server"
TOOLS_MODULE = f"{ADAPTER_PACKAGE}.tools"

# ADR 0026's frozen v1 registry spells the tool. It is asserted literally because
# the record names it, exactly as the six-tool set is named in T5.
TOOL_NAME = "standard_read"

# The one named test seam this suite adds (T7.2 Codex RED review, F1). FR-008's
# condition is decided by the Step 09 compatibility matrix, so the adapter must
# carry that matrix in machine-readable form; this is the constant that holds it,
# mapping each supported primary client to whether it gives the model direct
# resource access. Frozen by name rather than discovered by module shape, so the
# seam is one visible constant instead of an implied ABI over `tools.py`.
EVIDENCE_NAME = "CLIENT_DIRECT_RESOURCE_ACCESS"

# The two supported primary clients, as the T1 matrix names them. Matched as
# case-insensitive substrings of whatever key the adapter uses, so the evidence
# may be keyed by product name, slug, or executable without this suite freezing
# a spelling it has no authority over.
CODEX_CLIENT_TOKEN = "codex"
CLAUDE_CLIENT_TOKEN = "claude"

# The frozen T1 primary-client matrix, key set and values (T7.4 Codex GREEN
# review, F2). Checking one Codex-like and one Claude-like row left the rest of
# the mapping unconstrained: a third row, or a renamed one, could change the
# evidence the registration decision is taken from without any test failing
# outside the seam. The whole mapping is therefore pinned to the two supported
# primary clients the evidence matrix records, with the values it records for
# them — Claude Code 2.1.220 gives the model direct resource access, Codex CLI
# 0.145.0 does not. A new supported client is a T1 refresh, and must fail here
# until that refresh happens.
FROZEN_CLIENT_MATRIX = {"claude-code": True, "codex-cli": False}

# Argument names that would make the tool path-addressable. FR-008 says it
# "cannot accept arbitrary paths" and the plan says "with no path argument", so
# an input property named for a path is a contract violation before any call is
# made.
PATH_ARGUMENT_TOKENS = ("path", "file", "dir", "root", "repo")

# Inputs that must never resolve. Filesystem forms, foreign schemes, traversal,
# and the non-canonical spellings ADR 0026 refuses; a fifth class — an absolute
# path into the fixture distribution's own payload tree — is added per test,
# because that is the one an implementation with a second read path would serve.
#
# The NUL-bearing entries are the T5 lesson carried onto this surface (review F2
# there): a NUL byte is a legal JSON string character, so any client can send
# one, and `Path.resolve` raises `ValueError` rather than `OSError` on it. The
# resource grammar lists it among its forbidden characters; the tool must inherit
# that refusal rather than pass the byte down (T7.4 Codex GREEN review, F1).
NUL = "\x00"
NON_URI_INPUTS = (
    "/etc/passwd",
    "etc/passwd",
    "../../etc/passwd",
    "file:///etc/passwd",
    "payloads/alpha/2.0/README.md",
    "./payloads/alpha/2.0/README.md",
    "~/.ssh/id_ed25519",
    "",
    "standards://",
    NUL,
    f"standards://{NUL}",
)

# Stable service codes whose wire code is revision-dependent: the evidence matrix
# records resource-not-found as -32002 through 2025-11-25 and INVALID_PARAMS from
# 2026-07-28. Spelled here because they are the *service* layer's own codes, which
# `mcp_services` publishes as part of its contract.
NOT_FOUND_SERVICE_CODES = ("catalog-not-found", "standard-not-found", "resource-not-found")

# The adapter-owned code for a URI that never reaches a lookup at all. Revision
# stable: a non-canonical URI is a bad parameter in every revision.
URI_INVALID_SERVICE_CODE = "resource-uri-invalid"

MAX_LIST_PAGES = 32

# RED control only. A bare SDK server that registers one tool returning an
# embedded resource, so the tool probes and the parity walk are proven able to
# observe a real tool result before they are used against the absent adapter.
BARE_SDK_TOOL_CONTROL = """
import anyio
import mcp_types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

CONTROL_URI = "standards://catalog/5"
CONTROL_TEXT = "control tool body"


async def _list_tools(ctx, params):
    return types.ListToolsResult(
        tools=[
            types.Tool(
                name="standard_read",
                description="control",
                inputSchema={
                    "type": "object",
                    "properties": {"uri": {"type": "string"}},
                    "required": ["uri"],
                    "additionalProperties": False,
                },
            )
        ]
    )


async def _call_tool(ctx, params):
    return types.CallToolResult(
        content=[
            types.EmbeddedResource(
                resource=types.TextResourceContents(
                    uri=CONTROL_URI, mimeType="text/plain", text=CONTROL_TEXT
                )
            )
        ]
    )


server = Server(
    "project-standards",
    version="0",
    instructions="control",
    on_list_tools=_list_tools,
    on_call_tool=_call_tool,
)


async def _serve() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


anyio.run(_serve)
"""

CONTROL_TOOL_URI = "standards://catalog/5"
CONTROL_TOOL_TEXT = "control tool body"

# Serves the real adapter with the client-matrix evidence replaced before
# `create_server` runs. That substitution is how the plan's "evaluate the T1
# matrix mechanically" and its both-clients-direct counterfactual become
# observable without a second production code path.
#
# The seam is one explicitly named module constant, set on `tools` by name
# (T7.2 Codex RED review, F1, accept-amended). The earlier revision discovered
# *any* public `Mapping[str, bool]` and patched it across every adapter module,
# which invented a singleton-mapping ABI the record never states and would break
# the moment T8/T9 add another boolean mapping to `tools.py`. A `create_server`
# keyword was rejected instead: §5.5 froze that signature at T5.
MATRIX_LAUNCH_TEMPLATE = """
from pathlib import Path

from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.paths import CatalogMajor
from project_standards.mcp_server import tools, transport
from project_standards.mcp_server.models import AdapterConfiguration
from project_standards.mcp_services import McpServiceFacade

assert hasattr(tools, "__EVIDENCE_NAME__"), (
    "project_standards.mcp_server.tools must publish __EVIDENCE_NAME__"
)
tools.__EVIDENCE_NAME__ = __EVIDENCE__

facade = McpServiceFacade.from_installed(
    InstalledDistribution(Path("__PACKAGE_ROOT__"), tool_release="__TOOL_RELEASE__"),
    CatalogMajor("__CATALOG_MAJOR__"),
)
transport.run_stdio(transport.create_server(facade, AdapterConfiguration()))
"""


# -- planned surface -----------------------------------------------------------


def require_tools_module() -> ModuleType:
    """Import the planned T7 tool module, or fail as an explicit RED assertion.

    The plan's RED contract requires a missing planned module to surface as a
    test assertion rather than a collection error, so nothing in this file
    imports ``project_standards.mcp_server.tools`` at module scope.
    """
    try:
        spec = importlib.util.find_spec(TOOLS_MODULE)
    except ModuleNotFoundError:
        spec = None
    assert spec is not None, (
        f"planned module {TOOLS_MODULE} is absent; the T7 {TOOL_NAME} fallback does not exist yet"
    )
    return importlib.import_module(TOOLS_MODULE)


def client_matrix_evidence(module: ModuleType) -> dict[str, bool]:
    """Return ``tools.CLIENT_DIRECT_RESOURCE_ACCESS``, the frozen client-matrix evidence.

    *One explicitly named constant, and no other structural rule* (T7.2 Codex
    RED review, F1). The plan requires the registration decision to be
    "evaluated mechanically" from the matrix, and its acceptance requires a
    matrix fixture in which both clients have direct access to prove omission in
    that case alone — neither is expressible without a machine-readable statement
    of the matrix. This is that statement: one boolean per supported primary
    client, answering the single question FR-008 asks of each — *does this client
    give the model direct resource access?*

    The name is frozen here so the test seam is narrow and visible rather than
    inferred from module shape. The earlier revision instead accepted any public
    ``Mapping[str, bool]`` and required there to be exactly one, which invented a
    singleton-mapping ABI the record never states and would have turned any
    second boolean mapping added by T8/T9 into a spurious failure.
    """
    evidence = getattr(module, EVIDENCE_NAME, None)
    assert isinstance(evidence, Mapping), (
        f"{TOOLS_MODULE}.{EVIDENCE_NAME} must be a mapping of supported primary client -> "
        f"whether that client gives the model direct resource access; got {evidence!r}"
    )
    items = cast("Mapping[object, object]", evidence)
    assert items and all(
        isinstance(key, str) and isinstance(flag, bool) for key, flag in items.items()
    ), f"{TOOLS_MODULE}.{EVIDENCE_NAME} must map client names to booleans; got {evidence!r}"
    return {str(key): bool(flag) for key, flag in items.items()}


def client_key(evidence: Mapping[str, bool], token: str) -> str:
    """The evidence key naming one supported primary client."""
    matches = sorted(key for key in evidence if token in key.lower())
    assert len(matches) == 1, (
        f"the client-matrix evidence must name {token!r} exactly once; got {sorted(evidence)}"
    )
    return matches[0]


def matrix_launch(package_root: Path, evidence: Mapping[str, bool]) -> str:
    """A launch script that serves the real adapter under a substituted matrix."""
    return (
        MATRIX_LAUNCH_TEMPLATE.replace("__EVIDENCE_NAME__", EVIDENCE_NAME)
        .replace("__EVIDENCE__", repr(dict(sorted(evidence.items()))))
        .replace("__PACKAGE_ROOT__", str(package_root))
        .replace("__TOOL_RELEASE__", package_version())
        .replace("__CATALOG_MAJOR__", CATALOG_MAJOR)
    )


# -- protocol probes -----------------------------------------------------------


def list_tools(server: ServerProcess, era: Era) -> list[dict[str, Any]]:
    """Every registered tool, following pagination cursors if the server pages."""
    entries: list[dict[str, Any]] = []
    cursor: object = None
    for _ in range(MAX_LIST_PAGES):
        extra = {"cursor": cursor} if isinstance(cursor, str) else None
        result = expect_result(server, server.call("tools/list", era.params(extra)))
        if era.modern:
            assert_modern_result_contract(server, result)
        raw = result.get("tools")
        assert isinstance(raw, list), server.diagnosis(
            f"tools/list returned no tools array: {result!r}"
        )
        entries.extend(as_object(item, "a tools/list entry") for item in cast("list[object]", raw))
        cursor = result.get("nextCursor")
        if not isinstance(cursor, str) or not cursor:
            return entries
    raise AssertionError(server.diagnosis("tools/list never stopped paginating"))


def tool_names(entries: Sequence[Mapping[str, Any]]) -> list[str]:
    names: list[str] = []
    for entry in entries:
        name = entry.get("name")
        assert isinstance(name, str) and name, f"a tools/list entry carries no name: {entry!r}"
        names.append(name)
    return names


def require_tool(server: ServerProcess, entries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """The advertised ``standard_read`` entry, or a RED assertion naming its absence."""
    matches = [entry for entry in entries if entry.get("name") == TOOL_NAME]
    assert len(matches) == 1, server.diagnosis(
        f"{TOOL_NAME} must be advertised exactly once; tools/list carried "
        f"{tool_names(entries)}. The T1 matrix records Codex CLI 0.145.0 as having no "
        "established model-initiated resource access, so registration is mandatory"
    )
    return dict(matches[0])


def tool_argument_name(server: ServerProcess, entry: Mapping[str, Any]) -> str:
    """The single input property the tool declares, checked against FR-008's limits.

    The property's *name* is discovered rather than frozen — no binding document
    spells it — but its cardinality and its kind are contract: one canonical
    resource URI, and nothing that would make the tool path-addressable.
    """
    schema = as_object(entry.get("inputSchema"), f"the {TOOL_NAME} input schema")
    properties = as_object(schema.get("properties"), f"the {TOOL_NAME} input properties")
    assert len(properties) == 1, server.diagnosis(
        f"{TOOL_NAME} takes exactly one canonical resource URI and no path argument; "
        f"its schema declares {sorted(properties)}"
    )
    name = next(iter(properties))
    offending = [token for token in PATH_ARGUMENT_TOKENS if token in name.lower()]
    assert not offending, server.diagnosis(
        f"{TOOL_NAME} declares a path-shaped argument {name!r} ({offending}); FR-008 forbids it"
    )
    required = schema.get("required")
    assert isinstance(required, list) and list(cast("list[object]", required)) == [name], (
        server.diagnosis(f"{TOOL_NAME} must require its one argument; got required={required!r}")
    )

    # The declared *kind*, not merely the declared name (T7.2 Codex RED review,
    # F4). plan:405 makes the input "one canonical resource URI", which is a
    # string on the wire; a schema typing it as an object, array, or anything
    # else would advertise an input the tool cannot take, and the name check
    # above only ever inferred the kind. URI semantics are asserted *if served*
    # rather than required, because JSON Schema offers several ways to say it
    # (`format`, `pattern`, `contentMediaType`) and no record picks one — but a
    # served `format` must not claim some other lexical space.
    declared = as_object(properties[name], f"the {TOOL_NAME} {name!r} property schema")
    assert declared.get("type") == "string", server.diagnosis(
        f"{TOOL_NAME}'s {name!r} input is one canonical standards:// URI, so its schema must "
        f"declare type 'string'; got {declared.get('type')!r} in {declared!r}"
    )
    served_format = declared.get("format")
    assert served_format is None or (
        isinstance(served_format, str) and "uri" in served_format.lower()
    ), server.diagnosis(
        f"{TOOL_NAME}'s {name!r} property declares format {served_format!r}, which describes "
        "something other than a URI"
    )
    pattern = declared.get("pattern")
    assert pattern is None or (isinstance(pattern, str) and SCHEME_PREFIX[:-2] in pattern), (
        server.diagnosis(
            f"{TOOL_NAME}'s {name!r} property declares pattern {pattern!r}, which does not "
            f"constrain the input to the {SCHEME_PREFIX} scheme it accepts"
        )
    )
    return name


def call_tool(
    server: ServerProcess,
    era: Era,
    argument: str | None = None,
    value: object = None,
    *,
    name: str = TOOL_NAME,
    arguments: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """One ``tools/call`` frame for any registered tool, successful or not.

    The single ``argument``/``value`` pair is this suite's shape, because
    ``standard_read`` takes exactly one input. ``arguments`` is the general form
    for tools that take none or several — generalized here rather than forked into
    the suite that needed it, so one probe keeps building every tool call frame
    (T8.2 Codex RED review, F9).
    """
    assert argument is None or arguments is None, (
        "pass either one argument/value pair or a whole arguments mapping, not both"
    )
    if arguments is not None:
        sent = dict(arguments)
    elif argument is not None:
        sent = {argument: value}
    else:
        sent = {}
    return server.call("tools/call", era.params({"name": name, "arguments": sent}))


def tool_result(server: ServerProcess, frame: Mapping[str, Any]) -> dict[str, Any]:
    """One successful tool result: no JSON-RPC error and no ``isError`` marker.

    Deliberately *not* checked against the modern list-result contract: the
    ``ttlMs``/``cacheScope`` envelope fields ride on the cacheable list and read
    results, and ``CallToolResult`` carries neither — verified against the SDK by
    the control below, which is exactly the class of assumption a RED control
    exists to catch.
    """
    result = expect_result(server, frame)
    assert not result.get("isError"), server.diagnosis(
        f"the tool reported a failure for a call that must succeed: {result!r}"
    )
    return result


def json_nodes(value: object) -> Iterator[object]:
    """Every node of a decoded JSON document, container-first.

    Placement inside a tool result is deliberately not frozen — the SDK offers
    several legal carriers for a resource payload — so parity is asserted as
    "some node equals the resource read's contents entry" rather than at a fixed
    path. What is frozen is the *equality*: the plan says the tool's output is
    "the same descriptor/bytes mapping as T6", so a re-serialized, re-ordered, or
    field-dropped copy is not the same mapping.
    """
    yield value
    if isinstance(value, dict):
        for item in cast("dict[str, object]", value).values():
            yield from json_nodes(item)
    elif isinstance(value, list):
        for item in cast("list[object]", value):
            yield from json_nodes(item)


def assert_carries(
    server: ServerProcess, result: Mapping[str, Any], expected: Mapping[str, Any], *, label: str
) -> None:
    assert any(node == expected for node in json_nodes(dict(result))), server.diagnosis(
        f"the tool result does not carry {label} as the resource read returns it.\n"
        f"expected node: {json.dumps(expected, sort_keys=True)}\n"
        f"result: {json.dumps(result, sort_keys=True)}"
    )


def assert_tool_refusal(
    server: ServerProcess, frame: Mapping[str, Any], *, sent: str
) -> dict[str, Any]:
    """One structured refusal, in either form the protocol allows for a tool.

    A tool failure may travel as a JSON-RPC error or as a result carrying
    ``isError``; both are structured and the record freezes neither, so both are
    accepted. What is refused in both branches is the same as for a resource
    read (T6.1): ``METHOD_NOT_FOUND`` would mean the tool is not registered at
    all rather than refusing, and the SDK's generic unhandled-exception body
    means the refusal was never designed, which NFR-004 forbids. Returns the
    JSON-RPC error object when the refusal travelled as one and the ``isError``
    result otherwise, so callers can both search it for leaked bytes and compare
    it field-by-field with the refusal ``resources/read`` produces.

    Two generic bodies are excluded, not one, because the SDK's exception
    fallback is era-dependent and only the modern half matches T6's rule.
    ``mcp/server/runner.py:548`` turns an unmapped modern-era handler exception
    into ``INTERNAL_ERROR``/"Internal server error"; the classic-era dispatcher
    instead pins ``ErrorData(code=0, message=str(exc))``
    (``mcp/shared/jsonrpc_dispatcher.py:755-757``, "code=0 pins existing-server
    compat"), which both hides the absent mapping *and* puts the raw exception
    text on the wire. Verified out of band at T7.1 against a control server that
    raises from its tool handler; ``0`` is not a code any revision defines, so
    excluding it can never reject a designed refusal.
    """
    if "error" in frame:
        error = expect_error(server, frame)
        assert error["code"] != METHOD_NOT_FOUND, server.diagnosis(
            f"{TOOL_NAME} is not served, so {sent!r} was never actually refused: {error!r}"
        )
        assert error["code"] != 0, server.diagnosis(
            f"{sent!r} was refused by an exception the handler never mapped (the classic-era "
            f"code-0 fallback, which also leaks the exception text): {error!r}"
        )
        assert not (
            error["code"] == INTERNAL_ERROR and error["message"] == "Internal server error"
        ), server.diagnosis(
            f"{sent!r} was refused by an unhandled exception, not a mapping: {error!r}"
        )
        return error
    result = expect_result(server, frame)
    assert result.get("isError"), server.diagnosis(
        f"{sent!r} was answered successfully; FR-008 forbids resolving it: {result!r}"
    )
    return result


def assert_refusal_parity(
    server: ServerProcess, era: Era, uri: str, tool_refusal: Mapping[str, Any]
) -> None:
    """The tool and ``resources/read`` must refuse one URI identically (T7.4 review F1).

    Byte parity on the success path is only half of "the same descriptor/bytes
    mapping as T6" — a fallback that resolved, or merely *described*, a bad URI
    differently from the resource read would still be a second reader, and it is
    on the refusal path that a second implementation is easiest to hide. So each
    refusal is compared against the one ``resources/read`` produces for the same
    URI, on all three things the wire carries:

    *Form.* Both must travel as JSON-RPC errors. The record freezes no form for a
    tool failure in general (``isError`` is equally structured), but it does
    require this tool to be the resource read, so the two cannot diverge here.

    *Structured data.* The whole ``data`` object — the stable service code,
    severity, remediation, and any affected standard/version/path — must be
    equal, which is NFR-004's "code, message, affected path/standard, severity,
    remediation" made comparable. The message is compared too: both are the same
    ``ServiceError``'s own message, so any difference means a second producer of
    refusal text.

    *Era-correct code.* The evidence matrix records resource-not-found as
    ``-32002`` through 2025-11-25 and ``INVALID_PARAMS`` from 2026-07-28, and T6
    already serves that split from the negotiated revision. The expected code is
    therefore derived from the *service* code the refusal carries rather than
    hard-coded per input, so a new refusal class widens this check instead of
    escaping it.
    """
    resource_refusal = assert_structured_refusal(server, read_frame(server, era, uri), uri=uri)
    assert "code" in tool_refusal and "message" in tool_refusal, server.diagnosis(
        f"{TOOL_NAME} refused {uri!r} with an isError result while resources/read refused it "
        f"with a JSON-RPC error; the two surfaces are the same read: {tool_refusal!r}"
    )
    assert tool_refusal["code"] == resource_refusal["code"], server.diagnosis(
        f"refusing {uri!r}: the tool answered code {tool_refusal['code']} and resources/read "
        f"answered {resource_refusal['code']}"
    )
    assert tool_refusal.get("data") == resource_refusal.get("data"), server.diagnosis(
        f"refusing {uri!r}: the tool published {tool_refusal.get('data')!r} and resources/read "
        f"published {resource_refusal.get('data')!r}"
    )
    assert tool_refusal["message"] == resource_refusal["message"], server.diagnosis(
        f"refusing {uri!r}: the two surfaces produced different refusal text, so one of them "
        "builds its own"
    )
    assert refusal_class(tool_refusal) == refusal_class(resource_refusal), server.diagnosis(
        f"refusing {uri!r}: the refusal classes differ"
    )

    data = tool_refusal.get("data")
    published = cast("dict[str, object]", data) if isinstance(data, dict) else {}
    service_code = published.get("code")
    if service_code in NOT_FOUND_SERVICE_CODES:
        expected = INVALID_PARAMS if era.modern else LEGACY_RESOURCE_NOT_FOUND
        assert tool_refusal["code"] == expected, server.diagnosis(
            f"{service_code} is a not-found class, so a {era.revision} connection must be "
            f"answered with {expected}; got {tool_refusal['code']}"
        )
    elif service_code == URI_INVALID_SERVICE_CODE:
        assert tool_refusal["code"] == INVALID_PARAMS, server.diagnosis(
            f"a non-canonical URI is a bad parameter in every revision; got "
            f"{tool_refusal['code']} for {uri!r}"
        )


@pytest.fixture(scope="module")
def full_runtime(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The fixture catalog as an importable installed distribution, shared read-only."""
    return build_fixture_runtime(tmp_path_factory.mktemp("standard-read-full"))


@pytest.fixture(scope="module")
def grown_family(tmp_path_factory: pytest.TempPathFactory) -> GeneratedFamily:
    """A fixture distribution carrying one family whose payload is not valid UTF-8.

    The identity is generated per session for the reason T6.2 review F5 records:
    a predictable target lets an adapter with per-package branches pass a test
    that exists to prove data-driven behaviour. Here it also supplies the only
    resource whose bytes cannot travel as text, which is what makes the tool's
    binary parity assertion meaningful rather than incidental.
    """
    runtime = build_fixture_runtime(tmp_path_factory.mktemp("standard-read-grown"))
    return add_generated_family(
        runtime / "project_standards",
        standard_id=f"{GENERATED_ID_PREFIX}-{uuid.uuid4().hex[:10]}",
        version=GENERATED_VERSION,
    )


# -- RED control ---------------------------------------------------------------


def test_tool_probes_observe_a_registered_tool_and_its_payload() -> None:
    """RED control (T7.2): "the tool is absent" is a falsifiable claim.

    Every assertion below drives listing, calling, schema-reading, and payload
    parity against a tool that does not exist yet. This one drives the same
    helpers against a bare SDK server that registers one, so a failure elsewhere
    is provably the absent registration and not a broken probe. It also
    demonstrates that the selected SDK can carry a resource payload through a
    tool result unchanged — the mechanism the T7 fallback needs and the reason
    exact-node parity is a fair oracle.

    One process per era, because the SDK locks a connection's era at its opening
    request (T5.2 review F1).
    """
    expected = {"uri": CONTROL_TOOL_URI, "mimeType": "text/plain", "text": CONTROL_TOOL_TEXT}

    for era in (
        Era("classic", CODEX_CLIENT_REVISION, modern=False),
        Era("modern", MODERN_PROTOCOL_VERSIONS[-1], modern=True),
    ):
        with ServerProcess(BARE_SDK_TOOL_CONTROL, label=f"tool-control-{era.name}") as server:
            result = era.open(server)
            capabilities = declared_capabilities(result)
            assert capabilities.get("tools") is not None, (
                "the control server registers a tool, so it must declare the capability"
            )
            assert_no_list_change_promises(capabilities)
            reachable = assert_capabilities_match_reachable_registrations(
                server, capabilities, envelope=era.envelope
            )
            assert_no_write_surface(server, reachable)

            entries = list_tools(server, era)
            entry = require_tool(server, entries)
            argument = tool_argument_name(server, entry)
            assert argument == "uri"
            called = tool_result(server, call_tool(server, era, argument, CONTROL_TOOL_URI))
            assert_carries(server, called, expected, label="the control payload")
            assert server.finish() == 0
            assert_stdout_is_protocol_only(server)


# -- frozen acceptance tests ---------------------------------------------------


def test_tools_module_is_the_planned_registration_surface() -> None:
    """Plan T7 file list + T1 matrix: ``mcp_server/tools.py`` carries the matrix evidence.

    The module is named because the plan names it. The evidence mapping is
    required because the plan requires the matrix to be "evaluated mechanically",
    and it is pinned *whole* rather than row-sampled (T7.4 Codex GREEN review,
    F2): the key set and every value must be exactly the T1 primary-client
    matrix. Checking only a Codex-like and a Claude-like row left the rest of the
    mapping free — a third row, or a renamed one, could change the evidence the
    registration decision reads without failing anything outside the seam, and
    transcribing the matrix wrongly is the one failure mode that would silently
    omit a tool the record makes mandatory.

    Adding a supported primary client is therefore a T1 refresh, not an edit
    here: this assertion fails until the evidence matrix records the new client's
    resource-access row, which is exactly the plan's stop/backtrack rule.
    """
    module = require_tools_module()
    evidence = client_matrix_evidence(module)
    assert evidence == FROZEN_CLIENT_MATRIX, (
        f"{EVIDENCE_NAME} must be exactly the T1 primary-client matrix "
        f"{FROZEN_CLIENT_MATRIX}; got {evidence}. Claude Code 2.1.220 gives the model direct "
        "resource access (client matrix); Codex CLI 0.145.0 does not (required-fallbacks table)"
    )
    codex = client_key(evidence, CODEX_CLIENT_TOKEN)
    claude = client_key(evidence, CLAUDE_CLIENT_TOKEN)
    assert evidence[codex] is False and evidence[claude] is True
    # FR-008's condition, evaluated over the transcribed evidence rather than
    # restated: at least one supported primary client lacks direct access, so
    # registration is mandatory and the implementer has no discretion.
    assert not all(evidence.values()), (
        f"{EVIDENCE_NAME} records every supported primary client as giving the model direct "
        "resource access, which contradicts the T1 required-fallbacks table"
    )


@pytest.mark.parametrize("era", ERAS, ids=ERA_IDS)
def test_standard_read_registration_follows_client_matrix_and_reuses_resource_service(
    full_runtime: Path, era: Era
) -> None:
    """TC-T7-002 (FR-008): mandatory registration, and byte-identical delegation.

    Two claims, asserted on one connection because they are one contract.

    *Registration is mandatory.* The T1 matrix records at least one supported
    primary client without direct model resource access, so the plan removes the
    implementer's discretion: the tool must be advertised, the tools capability
    must be declared and reachable, ``listChanged`` must stay false, and every
    advertised tool must still come from ADR 0026's read-only frozen six. The
    condition is read from the adapter's own evidence mapping rather than
    restated here, so a server that transcribed the matrix differently fails on
    the transcription rather than on the registration.

    *The tool is the resource read.* For every declared resource of the fixture
    catalog — and for the two metadata forms as well — the tool result must carry
    the ``resources/read`` contents entry for the same URI *as an equal node*:
    same bytes, same declared media type, same ``_meta`` declaration projection.
    That is what "the same descriptor/bytes mapping as T6" means, and it is the
    strongest available proof that the tool did not grow a second reader; the
    ordering half of that claim is proven through the recording facade in
    ``test_standard_read_reuses_the_resource_service_without_a_second_read_path``.

    Both eras run because the fallback exists *for* the 2025-06-18-only client:
    a tool that worked only on the modern connection would be useless to the
    client that needs it.
    """
    require_mcp_subcommand()
    module = require_tools_module()
    evidence = client_matrix_evidence(module)
    assert not all(evidence.values()), (
        "the T1 matrix condition no longer holds, so this task's registration rule changed; "
        "refresh T1 rather than adjusting the test (plan T7 stop/backtrack)"
    )

    facade = oracle_facade(full_runtime)
    catalog = facade.catalog()
    resources = declared_resources(catalog)

    with resource_session(era, runtime_root=full_runtime, label="standard-read") as (
        server,
        result,
    ):
        capabilities = declared_capabilities(result)
        reachable = assert_capabilities_match_reachable_registrations(
            server, capabilities, envelope=era.envelope
        )
        assert_no_list_change_promises(capabilities)
        assert_no_write_surface(server, reachable)
        assert reachable.get("tools") is not None, server.diagnosis(
            "the matrix condition holds, so the tools capability must be declared and reachable"
        )

        entries = list_tools(server, era)
        entry = require_tool(server, entries)
        argument = tool_argument_name(server, entry)
        unknown = sorted(name for name in tool_names(entries) if name not in FROZEN_V1_TOOLS)
        assert not unknown, server.diagnosis(f"tools outside ADR 0026's v1 registry: {unknown}")

        addressable = [CATALOG_URI, *(package_uri(d) for d in catalog.standards), *resources]
        for uri in addressable:
            expected = read_one(server, era, uri)
            called = tool_result(server, call_tool(server, era, argument, uri))
            assert_carries(server, called, expected, label=f"the exact read of {uri}")

        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


def test_standard_read_is_omitted_only_when_every_supported_client_has_direct_access(
    full_runtime: Path,
) -> None:
    """Plan T7 acceptance: the omission case is exactly one case.

    The plan's acceptance names a matrix fixture "in which both clients provide
    direct access" and requires it to prove omission *in only that case*, which
    is a claim about the decision function and not about today's data. Four
    matrices are therefore served, each by a real server built through
    ``create_server`` with the evidence substituted before construction:

    * both clients direct — the tool must be absent, and with no other tool
      registered at this task boundary the T5 equivalence keeps the capability
      honest by itself;
    * Codex lacking direct access (today's recorded matrix) — present;
    * Claude lacking it instead — present, because FR-008's condition is "any
      supported primary client", not "Codex";
    * neither having it — present.

    Membership is asserted rather than equality with the whole tool surface, so
    T8/T9 can register the rest of the frozen six without weakening this test.
    """
    require_mcp_subcommand()
    module = require_tools_module()
    evidence = client_matrix_evidence(module)
    codex = client_key(evidence, CODEX_CLIENT_TOKEN)
    claude = client_key(evidence, CLAUDE_CLIENT_TOKEN)

    matrices: tuple[tuple[str, dict[str, bool], bool], ...] = (
        ("both-direct", {**evidence, codex: True, claude: True}, False),
        ("codex-indirect", {**evidence, codex: False, claude: True}, True),
        ("claude-indirect", {**evidence, codex: True, claude: False}, True),
        ("neither-direct", {**evidence, codex: False, claude: False}, True),
    )
    era = MODERN_ERA
    package_root = full_runtime / "project_standards"
    for label, matrix, required in matrices:
        script = matrix_launch(package_root, matrix)
        with resource_session(
            era, runtime_root=full_runtime, label=f"matrix-{label}", script=script
        ) as (server, result):
            capabilities = declared_capabilities(result)
            reachable = assert_capabilities_match_reachable_registrations(
                server, capabilities, envelope=era.envelope
            )
            advertised = {
                str(as_object(tool, "a tools/list entry").get("name"))
                for tool in reachable.get("tools", [])
            }
            if required:
                assert TOOL_NAME in advertised, server.diagnosis(
                    f"{matrix} leaves a supported primary client without direct resource access, "
                    f"so {TOOL_NAME} is mandatory; advertised {sorted(advertised)}"
                )
            else:
                assert TOOL_NAME not in advertised, server.diagnosis(
                    f"{matrix} gives every supported primary client direct resource access, so "
                    f"{TOOL_NAME} must be omitted; advertised {sorted(advertised)}"
                )
                # The resource surface is the access path in that case, and it
                # must be untouched by the decision.
                read_one(server, era, CATALOG_URI)
            assert server.finish() == 0
            assert_stdout_is_protocol_only(server)


@pytest.mark.parametrize("era", ERAS, ids=ERA_IDS)
def test_standard_read_refuses_arbitrary_paths_and_non_canonical_uris(
    full_runtime: Path, era: Era
) -> None:
    """FR-008: "cannot accept arbitrary paths", and the T6 URI grammar still rules.

    The tool is the one surface where a filesystem argument would be plausible,
    so every filesystem shape is refused explicitly: absolute and relative paths,
    a payload path that really exists inside the served distribution, a
    ``file://`` URL, traversal, a home-relative path, and a NUL-bearing string —
    which is a legal JSON string a client can really send, and which the resource
    grammar lists among its forbidden characters. A second class covers the ADR
    0026 grammar — uppercase, trailing slash, the rejected three-segment index
    form, a mutable version alias — and a third covers URIs that are perfectly
    *canonical* but name nothing: an undeclared standard, an undeclared version
    of a declared standard, an undeclared resource of a declared version, and a
    catalog generation this server does not expose. That third class is the one
    that reaches the registration index, so it is where a second reader would
    diverge first.

    Every refusal is checked for three things. It must not leak payload bytes
    (FR-006) or an absolute filesystem path the client never sent (DR-009). And
    it must be *the same refusal* ``resources/read`` gives for the same URI —
    same JSON-RPC code, same structured data, same message, same refusal class,
    and the era-correct code for its class (T7.4 Codex GREEN review, F1). Byte
    parity on the success path cannot prove that: a second implementation is
    easiest to hide on the paths that never return bytes.
    """
    require_mcp_subcommand()
    module = require_tools_module()
    client_matrix_evidence(module)

    facade = oracle_facade(full_runtime)
    catalog = facade.catalog()
    canaries = byte_canaries(facade, catalog)
    sample = catalog.standards[0]
    declared_resource = sample.resources[0].resource_id
    payload_path = str(full_runtime / "project_standards" / "payloads")
    refusals = (
        *NON_URI_INPUTS,
        payload_path,
        f"{payload_path}/{sample.standard_id}/{sample.package_version}/README.md",
        f"STANDARDS://{sample.standard_id}/{sample.package_version}",
        f"standards://{sample.standard_id}/{sample.package_version}/",
        f"standards://{sample.standard_id}/latest",
        f"standards://{sample.standard_id}/{sample.package_version}/{declared_resource}",
        f"standards://{sample.standard_id}/{sample.package_version}/resources/../../../etc/passwd",
        f"standards://{sample.standard_id}/{sample.package_version}/resources/read{NUL}me",
        # Canonical in every respect, and declared by nothing.
        "standards://no-such-standard/1.0",
        f"standards://{sample.standard_id}/9999.0",
        f"standards://{sample.standard_id}/{sample.package_version}/resources/no-such-resource",
        f"standards://catalog/{int(CATALOG_MAJOR) + 1}",
    )

    with resource_session(era, runtime_root=full_runtime, label="standard-read-refusals") as (
        server,
        _,
    ):
        argument = tool_argument_name(server, require_tool(server, list_tools(server, era)))
        for sent in refusals:
            refusal = assert_tool_refusal(server, call_tool(server, era, argument, sent), sent=sent)
            assert_refusal_parity(server, era, sent, refusal)
            rendered = json.dumps(refusal, sort_keys=True)
            leaked = sorted(
                uri
                for uri, variants in canaries.items()
                if any(variant in rendered for variant in variants)
            )
            assert not leaked, server.diagnosis(f"refusing {sent!r} leaked bytes for {leaked}")
            # Echoing the offending input back is legitimate — T6's own refusals
            # quote the URI the client already holds — so the leak test is run
            # against the refusal with the echoed input removed. What must not
            # appear is a *server-side* absolute path the client never sent.
            scrubbed = rendered.replace(json.dumps(sent)[1:-1], "<the input>")
            assert str(full_runtime) not in scrubbed, server.diagnosis(
                f"refusing {sent!r} leaked a distribution path the client never sent"
            )

        # A non-string argument is a shape error, not a path — it must still be
        # structured rather than an unhandled exception. No parity is asserted
        # for it: ``resources/read`` has no equivalent, because the SDK
        # surface-validates ``uri`` as a string before any handler runs.
        assert_tool_refusal(server, call_tool(server, era, argument, ["/etc/passwd"]), sent="list")

        # The surface still works afterwards: a refusal is not a poisoned session.
        read_one(server, era, CATALOG_URI)
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


def test_standard_read_reuses_the_resource_service_without_a_second_read_path(
    full_runtime: Path,
) -> None:
    """Plan T7 stop condition: "do not create ... a second resource-reading implementation".

    Byte parity alone cannot prove this — two readers can agree on bytes — so the
    claim is observed at the service boundary instead, with the recording facade
    T6 built for the same reason. For one declared payload resource, the facade
    calls a ``tools/call`` provokes must equal the calls the equivalent
    ``resources/read`` provokes: same method, same selection arguments, same
    count. A tool that opened the payload file itself would record nothing, and a
    tool that re-read through a second service path would record something
    different.

    The comparison is delta-based on one connection, so process start-up calls
    (catalog construction) cannot mask the difference.
    """
    require_mcp_subcommand()
    module = require_tools_module()
    client_matrix_evidence(module)

    catalog = oracle_facade(full_runtime).catalog()
    resources = declared_resources(catalog)
    uri = sorted(resources)[0]
    era = MODERN_ERA

    with resource_session(
        era,
        runtime_root=full_runtime,
        label="standard-read-spy",
        script=spy_launch(full_runtime / "project_standards"),
    ) as (server, _):
        argument = tool_argument_name(server, require_tool(server, list_tools(server, era)))

        before = len(payload_reads(spy_calls(server)))
        read_one(server, era, uri)
        server.drain(0.5)
        after_read = payload_reads(spy_calls(server))
        by_resource = after_read[before:]
        assert by_resource, server.diagnosis(
            f"reading {uri} recorded no service call, so the spy oracle is not observing reads"
        )

        tool_result(server, call_tool(server, era, argument, uri))
        server.drain(0.5)
        by_tool = payload_reads(spy_calls(server))[len(after_read) :]
        assert by_tool == by_resource, server.diagnosis(
            f"{TOOL_NAME} reached the payload differently from resources/read for {uri}: "
            f"tool={by_tool} resource={by_resource}"
        )
        assert server.finish() == 0


def test_standard_read_carries_binary_payloads_byte_for_byte(
    grown_family: GeneratedFamily,
) -> None:
    """FR-003/FR-008: the fallback is exact for bytes that have no text form.

    The generated family's payload is not valid UTF-8 anywhere, so the protocol
    must take the base64 ``blob`` path. This is where a tool that stringified its
    result would diverge from the resource read while still looking plausible,
    and it is also the case a Codex user has no other way to reach — the whole
    reason the fallback is mandatory.
    """
    require_mcp_subcommand()
    module = require_tools_module()
    client_matrix_evidence(module)

    era = MODERN_ERA
    facade = oracle_facade(grown_family.runtime)
    declared = facade.resource(
        grown_family.standard_id, grown_family.version, GENERATED_BINARY_RESOURCE
    ).data
    with resource_session(era, runtime_root=grown_family.runtime, label="standard-read-binary") as (
        server,
        _,
    ):
        argument = tool_argument_name(server, require_tool(server, list_tools(server, era)))
        expected = read_one(server, era, grown_family.binary_uri)
        assert expected.get("blob"), server.diagnosis(
            "the binary fixture must travel as base64, or this parity check proves nothing"
        )
        called = tool_result(server, call_tool(server, era, argument, grown_family.binary_uri))
        assert_carries(server, called, expected, label="the binary payload")
        carried = json.dumps(called, sort_keys=True)
        assert base64.b64encode(declared).decode("ascii") in carried, server.diagnosis(
            "the tool result does not carry the declared bytes of the binary resource"
        )
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


def test_instructions_stay_truthful_once_the_fallback_tool_is_registered(
    full_runtime: Path,
) -> None:
    """ADR 0026 phase amendment (2026-07-29): the instructions describe *this* build.

    The record's frozen six-tool text becomes binding at T9; until then the
    served string must be "static, era-stable, and truthful for its phase". The
    T6 build satisfied that with a sentence stating that no prompt or tool is
    available, which becomes false the moment ``standard_read`` is registered —
    the same fault T6 had to fix in the other direction when it registered
    resources.

    So the phase rule is asserted in the two directions T7 makes live, without
    pinning any wording: no denial of the tool surface this build registers, and
    no promise of the five tools it does not. The prompt half stays a denial that
    must remain *true*, because no prompt is registered.
    """
    require_mcp_subcommand()
    module = require_tools_module()
    client_matrix_evidence(module)

    era = MODERN_ERA
    with resource_session(era, runtime_root=full_runtime, label="standard-read-instructions") as (
        server,
        result,
    ):
        advertised = set(tool_names(list_tools(server, era)))
        assert TOOL_NAME in advertised, server.diagnosis(
            f"{TOOL_NAME} is not registered, so this build's phase rule is not yet live"
        )
        instructions = result.get("instructions")
        assert isinstance(instructions, str) and instructions.strip(), server.diagnosis(
            f"the server must serve a non-empty instructions string, got {instructions!r}"
        )
        lowered = instructions.lower()
        denials = [
            phrase
            for phrase in ("no prompt or tool", "no tool is available", "no tools are registered")
            if phrase in lowered
        ]
        assert not denials, server.diagnosis(
            f"the instructions deny a tool surface this build registers: {denials}"
        )
        claimed = sorted(
            name for name in FROZEN_V1_TOOLS if name in instructions and name not in advertised
        )
        assert not claimed, server.diagnosis(
            f"the instructions name tools this build does not register: {claimed}"
        )
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)
