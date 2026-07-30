"""Generic discovery tools: ``standards_list`` and ``repo_inspect`` (T8).

Covers TC-T8-001 (structured catalog output equals the resource facts), TC-T8-002
(repo inspection handles missing/partial/current state with explicit
containment), TC-T8-003 (metadata is compact and declares read-only effect),
TC-T8-004 (tools stay typed and generic), and TC-T8-005 (relationships preserve
exact V2 declarations).

Four authorities constrain every expectation here and none of them may be
re-derived by the modules under test:

*The spec* — FR-007 (``standards_list`` "returns the same installed catalog facts
and exact resource URIs as FR-001"), FR-009 (``repo_inspect`` "reports
missing/invalid state, and does not treat legacy config as current authority"),
FR-021 (relations "distinguish companions, extensions, and conflicts exactly as
V2 declarations encode them; empty relations remain independent"), FR-022 (typed
input/output models plus "protocol-supported structured content plus bounded
human text where useful"), FR-023 (descriptions "state purpose, input authority,
and read-only effect" and "tests snapshot the supported-client tool metadata"),
FR-024 (an explicit ``repo_root``, with advertised roots able only to narrow),
NFR-012 (metadata and default outputs avoid unnecessary verbosity), IR-003 (typed
generic schemas; "tool list is small and stable across fixture standard
addition"), DR-005 (the bounded snapshot), and DR-006 (relationship preservation).

*ADR 0026* — the v1 registry names both tools, freezes them read-only, and keeps
``listChanged`` false. The record's tool set is closed: T8 may add no tool of its
own naming. It freezes *behavior*, not protocol annotations: ``readOnlyHint`` and
the rest of ``ToolAnnotations`` are deliberately unasserted here, because FR-023
places the read-only claim in the description and no record makes the optional
annotation object binding (T8.2 Codex RED review, F7).

*The plan's T8 block* — ``standards_list`` "takes no package-specific argument";
``repo_inspect`` "requires explicit ``repo_root`` and returns
``RepoInspectionSnapshot``"; and "neither tool reads resources or repository file
contents itself". Its stop condition forbids ``standards_resolve``,
recommendations, and per-standard tool names.

*The service layer* — every expected value comes from ``McpServiceFacade`` over
the same bytes the server serves. T8 is a registration and mapping task, so its
oracle is the layer that already owns the facts, never a second copy of them.

**Harness reuse, stated exactly.** ``test_transport.py`` owns the
subprocess/transcript/capability machinery, ``test_resources.py`` owns the
fixture distribution, era machinery, and recording facade, ``test_standard_read.py``
owns the tool-listing/calling probes and the client-matrix launch, and
``tests/mcp_services/test_consumer.py`` owns the consumer state fixtures and the
release-relative technique for the two classifications its shared builder
excludes. Two things are *added* rather than reused, and both are additions to
this file alone: the filesystem-audit prologue below, which no existing suite
needed because no existing tool takes a repository root, and the per-tool
metadata snapshot FR-023 asks for. One reused helper was generalized in the
module that owns it — ``test_standard_read.call_tool`` now takes a whole argument
mapping — rather than forked here (T8.2 Codex RED review, F9).

Two RED controls run against bare or already-registered surfaces, so that every
probe this file depends on is exercised even while the T8 registration is absent:

* ``test_structured_output_probes_observe_a_typed_tool_result`` confirms the
  selected SDK carries ``outputSchema`` and ``structuredContent`` over stdio in
  both eras and that the probes read them from the right place. (A *missing*
  structured field already fails loudly — ``structured`` asserts it — so this is
  a check on the transport and the probes, not a guard against vacuous passes.)
* ``test_filesystem_probe_attributes_reads_to_their_layer`` drives the audit
  prologue against ``standard_read``, which T7 already registers, and proves the
  prologue can both see a real payload read and attribute it to the layer that
  performed it. Without it, "the adapter never reads a file itself" would be the
  unfalsifiable oracle the review found (F6).
"""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol, cast

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from mcp_types import METHOD_NOT_FOUND

from project_standards._version import package_version
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.state import StateKind
from project_standards.mcp_services import CatalogDescriptor, RelationshipSet
from tests.mcp_server.test_resources import (
    CATALOG_URI,
    ERA_IDS,
    ERAS,
    FIXTURE_SUBTREES,
    GENERATED_ID_PREFIX,
    GENERATED_VERSION,
    MODERN_ERA,
    Era,
    GeneratedFamily,
    add_generated_family,
    build_fixture_runtime,
    catalog_projection,
    declared_resources,
    metadata_document,
    oracle_facade,
    resource_session,
    spy_calls,
    spy_launch,
)
from tests.mcp_server.test_standard_read import (
    EVIDENCE_NAME,
    FROZEN_CLIENT_MATRIX,
    NUL,
    call_tool,
    client_matrix_evidence,
    list_tools,
    matrix_launch,
    require_tools_module,
    tool_names,
)
from tests.mcp_server.test_standard_read import (
    TOOL_NAME as STANDARD_READ,
)
from tests.mcp_server.test_transport import (
    FROZEN_V1_TOOLS,
    ServerProcess,
    as_object,
    assert_capabilities_match_reachable_registrations,
    assert_no_list_change_promises,
    assert_no_write_surface,
    assert_stdout_is_protocol_only,
    boundary_option_name,
    cli_launch_with,
    declared_capabilities,
    expect_error,
    expect_result,
    require_mcp_subcommand,
)
from tests.mcp_services.helpers import build_installed_tree
from tests.mcp_services.test_consumer import build_consumer_repo, build_state_fixtures

ADAPTER_PACKAGE = "project_standards.mcp_server"
TOOLS_MODULE = f"{ADAPTER_PACKAGE}.tools"

# ADR 0026's frozen v1 registry spells both tools; T8 may not rename them.
STANDARDS_LIST = "standards_list"
REPO_INSPECT = "repo_inspect"
DISCOVERY_TOOLS = (STANDARDS_LIST, REPO_INSPECT)

# The three T9 registered, named here only so the conformance map below can call
# them. Their metadata is reviewed by the suite that owns them.
RECONCILE_PREVIEW = "reconcile_preview"
VALIDATE_REPO = "validate_repo"
DRIFT_CHECK = "drift_check"

# FR-024 and §5.5 both name the argument, so its spelling is contract rather than
# an implementation choice: "The server shall require an explicit `repo_root`".
REPO_ROOT_ARGUMENT = "repo_root"

# The plan's stop condition, as names. `standards_resolve` is named by the record;
# the rest are the shapes it forbids by kind — a per-standard tool, or anything
# that recommends rather than reports.
FORBIDDEN_TOOL_NAMES = ("standards_resolve",)
FORBIDDEN_TOOL_TOKENS = ("resolve", "recommend", "suggest", "advise", "best")

# ---------------------------------------------------------------------------
# FR-023's reviewed metadata snapshot
# ---------------------------------------------------------------------------
#
# FR-023's acceptance is "tests snapshot the supported-client tool metadata", and
# its content obligation is that descriptions "state purpose, input authority, and
# read-only effect". This block is that snapshot: the exact name, title,
# description, input schema, and output schema of every tool the supported-client
# matrix registers, reviewed as test code.
#
# It replaces the character budgets an earlier revision of this suite invented
# (a 10,000-character listing ceiling, 500-character descriptions, 32-character
# names). Those were rejected because none of them is a record fact: a
# tool-*result* warning measured in tokens says nothing about a tools/list
# payload measured in characters, and a description that satisfies a length bound
# can still fail to state its authority while an unbounded one states everything
# required (T8.2 Codex RED review, F1/F2; freeze #4 overturned).
#
# A snapshot is stricter than any budget in the direction that matters: nothing
# can be dropped, reworded, retyped, or added without this constant changing, and
# changing it is a review.
#
# **Scope: three of six, deliberately.** This constant reviews the three tools
# *this* suite registers. T9's three consumer tools are reviewed the same way by
# the suite that registers them
# (`tests/mcp_server/test_consumer_tools.EXPECTED_CONSUMER_TOOL_METADATA`), and
# whole-surface equality over all six lives there, in
# `test_consumer_tool_metadata_is_compact_and_read_only`, as equality with the
# union of the two constants.
#
# The split is the reviewed resolution of forward conflict (b), not a weakening:
# each suite reviews the metadata it introduced, which is what FR-023's
# "test-reviewed" asks for, and rewording a reviewed T8 constant from a later
# task would be the bigger change (T9.4 Codex GREEN review, F5). The
# alternative — centralizing six entries here — was rejected for the same reason,
# and because `test_consumer_tools` already imports this module for the shared
# schema and probe helpers, so importing back would make the two mutually
# dependent.
#
# The wire spelling is the protocol's (`inputSchema`, `outputSchema`), because
# this is compared against what a client actually receives.

_ANY_JSON: dict[str, Any] = {"type": ["object", "array", "string", "number", "boolean", "null"]}

_RELATIONSHIP_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "companions": {"type": "array", "items": {"type": "string"}},
        "extends": {"type": "array", "items": {"type": "string"}},
        "conflicts": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["companions", "extends", "conflicts"],
    "additionalProperties": False,
}

_CATALOG_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "catalog_major": {"type": "integer"},
        "standards": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "standard_id": {"type": "string"},
                    "title": {"type": "string"},
                    "status": {"type": "string"},
                    "package_version": {"type": "string"},
                    "exposure": {"type": "string"},
                    "capabilities": {"type": "array", "items": {"type": "string"}},
                    "relationships": _RELATIONSHIP_SCHEMA,
                    "resources": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"uri": {"type": "string"}},
                            "required": ["uri"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": [
                    "standard_id",
                    "title",
                    "status",
                    "package_version",
                    "exposure",
                    "capabilities",
                    "relationships",
                    "resources",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": ["catalog_major", "standards"],
    "additionalProperties": False,
}


def _nullable(*declared: dict[str, Any]) -> dict[str, Any]:
    """One optional §5.5 field: the declared kind, or an explicit null.

    ``ServiceModel`` serializes the whole frozen field set, so an optional field is
    *present and null* rather than absent. That is what lets the objects below be
    both closed and fully required.
    """
    return {"anyOf": [*declared, {"type": "null"}]}


# Closed and complete against the frozen §5.5 `Finding`. An earlier revision left
# it open on the theory that the optional line/locus/conflict/digest fields appear
# only when reported, which is false for these DTOs — so the schema accepted
# arbitrary extra properties and any type at all in those slots, which is not the
# typed result FR-022 requires (T8.4 Codex GREEN review, F2).
_FINDING_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "rule_id": {"type": "string"},
        "severity": {"type": "string"},
        "standard_id": {"type": "string"},
        "version": {"type": "string"},
        "path": {"type": "string"},
        "identity": {"type": "string"},
        "message": {"type": "string"},
        "remediation": {"type": "string"},
        "line": _nullable({"type": "integer"}),
        "column": _nullable({"type": "integer"}),
        "locus": _nullable({"type": "string"}),
        "observed": _nullable({"type": "integer"}),
        "limit": _nullable({"type": "integer"}),
        "expected": _ANY_JSON,
        "actual": _ANY_JSON,
        "expected_digest": _nullable({"type": "string"}),
        "actual_digest": _nullable({"type": "string"}),
        "governing_options": _nullable({"type": "array", "items": {"type": "string"}}),
        "null_values": {"type": "array", "items": {"type": "string"}},
        "first_difference_line": _nullable({"type": "integer"}),
        "first_difference_expected": _nullable({"type": "string"}),
    },
    "required": [
        "rule_id",
        "severity",
        "standard_id",
        "version",
        "path",
        "identity",
        "message",
        "remediation",
        "line",
        "column",
        "locus",
        "observed",
        "limit",
        "expected",
        "actual",
        "expected_digest",
        "actual_digest",
        "governing_options",
        "null_values",
        "first_difference_line",
        "first_difference_expected",
    ],
    "additionalProperties": False,
}

_SNAPSHOT_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "repo_root": {"type": "string"},
        "state": {"type": "string"},
        "desired_config": _ANY_JSON,
        "consumer_catalog": _ANY_JSON,
        "central_lock": _ANY_JSON,
        "findings": {"type": "array", "items": _FINDING_SCHEMA},
    },
    "required": [
        "repo_root",
        "state",
        "desired_config",
        "consumer_catalog",
        "central_lock",
        "findings",
    ],
    "additionalProperties": False,
}

# DR-002's declaration in full. Written as "an object of strings" in an earlier
# revision, which accepted `{}` and `{"wrong": "value"}` and therefore declared
# nothing about the six facts DR-002 requires an exposed resource to carry (T8.4
# Codex GREEN review, F1).
_DECLARATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "uri": {"type": "string"},
        "resource_id": {"type": "string"},
        "role": {"type": "string"},
        "media_type": {"type": "string"},
        "digest": {"type": "string"},
        "standard_id": {"type": "string"},
        "package_version": {"type": "string"},
    },
    "required": [
        "uri",
        "resource_id",
        "role",
        "media_type",
        "digest",
        "standard_id",
        "package_version",
    ],
    "additionalProperties": False,
}

_RESOURCE_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "uri": {"type": "string"},
        "media_type": {"type": "string"},
        "declaration": _nullable(_DECLARATION_SCHEMA),
    },
    "required": ["uri", "media_type", "declaration"],
    "additionalProperties": False,
}

EXPECTED_TOOL_METADATA: dict[str, dict[str, Any]] = {
    STANDARDS_LIST: {
        "name": STANDARDS_LIST,
        "title": "List installed standard packages",
        "description": (
            "List every standard package installed in Catalog 5: id, title, status, exact "
            "version, exposure, capabilities, declared relationships, and version-qualified "
            "resource URIs. Takes no arguments; the installed distribution is the only "
            "authority. Read-only: it writes nothing."
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "outputSchema": _CATALOG_OUTPUT_SCHEMA,
    },
    STANDARD_READ: {
        "name": STANDARD_READ,
        "title": "Read one installed standard resource",
        "description": (
            "Return the exact bytes and declared media type of one installed standard "
            "resource, addressed by its canonical standards:// URI. Same content as reading "
            "the resource directly; use this when the client cannot read MCP resources. "
            "Accepts only declared resource URIs, never filesystem paths. Read-only: it "
            "writes nothing."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "uri": {
                    "type": "string",
                    "format": "uri",
                    "description": (
                        "A canonical standards:// resource URI, exactly as the installed "
                        "catalog declares its ids and versions."
                    ),
                }
            },
            "required": ["uri"],
            "additionalProperties": False,
        },
        "outputSchema": _RESOURCE_OUTPUT_SCHEMA,
    },
    REPO_INSPECT: {
        "name": REPO_INSPECT,
        "title": "Inspect one consumer repository's standards state",
        "description": (
            "Report the current control-plane state of one consumer repository: its "
            "authoritative classification, the parsed .standards/ desired, catalog, and lock "
            "state, and bounded findings. The repository is the explicit repo_root argument, "
            "never the working directory; a launch-time boundary can only narrow it. "
            "Read-only: it writes nothing."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                REPO_ROOT_ARGUMENT: {
                    "type": "string",
                    "description": (
                        "Absolute path to the consumer repository to inspect. Required: the "
                        "server never infers a repository from its working directory."
                    ),
                }
            },
            "required": [REPO_ROOT_ARGUMENT],
            "additionalProperties": False,
        },
        "outputSchema": _SNAPSHOT_OUTPUT_SCHEMA,
    },
}

# FR-023's three content obligations, asserted against the reviewed constants
# above rather than against whatever the server happens to serve. Equality with
# the snapshot constrains the implementation; these constrain the snapshot, so a
# future edit that quietly drops a tool's authority statement fails here.
#
# *Purpose* and *input authority* are per-tool phrases because the two are
# per-tool facts. *Read-only effect* is shared, and is checked as a claim-shaped
# phrase rather than a word so that a truthful sentence is never mistaken for a
# missing one (the T6.4 F3 lesson) — with the negations the review found
# explicitly excluded (F1).
REVIEWED_DESCRIPTION_CLAIMS: dict[str, tuple[str, ...]] = {
    STANDARDS_LIST: ("standard package", "installed", "catalog 5", "takes no arguments"),
    STANDARD_READ: ("bytes", "standards://", "never filesystem paths"),
    REPO_INSPECT: ("consumer repository", "repo_root", "never the working directory"),
}

READ_ONLY_CLAIMS = ("read-only", "read only", "never writes", "writes nothing", "does not write")

NEGATED_READ_ONLY_CLAIMS = (
    "not read-only",
    "not read only",
    "never read-only",
    "read-write",
    "writes to",
    "may write",
)

# The words a compact description should not need. Marketing and hedging are the
# verbosity NFR-012 targets, and "recommend" is also the plan's forbidden shape.
FORBIDDEN_DESCRIPTION_TOKENS = ("recommend", "should probably", "powerful", "simply", "just use")

# A sentinel planted in consumer files that DR-005 forbids the snapshot from
# carrying. Distinct per session so a stale fixture cannot mask a real leak.
CONSUMER_SENTINEL = f"do-not-publish-consumer-content-{uuid.uuid4().hex[:8]}"

# ---------------------------------------------------------------------------
# The filesystem-audit prologue (T8.2 Codex RED review, F6)
# ---------------------------------------------------------------------------
#
# "Neither tool reads resources or repository file contents itself" is invisible
# from the wire *and* invisible to the recording facade: a tool with its own
# reader records no facade call, which an oracle that only counts facade calls
# reads as success. So the server process is additionally audited at the one place
# a direct read cannot hide — CPython's `open` audit event, which fires for
# `builtins.open` and `os.open` alike and cannot be bypassed by a lazy import or
# a helper module.
#
# Each watched open is attributed to the *innermost distribution frame that asked
# for it*: `mcp_server/...` means the adapter opened the file itself, anything
# else under `project_standards/` means the adapter delegated and an authoritative
# layer performed the read. Nothing else is recorded, so the attribution never
# depends on which service module the facade happens to route through.
#
# Watched roots are passed in rather than being "everything", because the runtime
# root also holds the .py files the import system reads: watching those would bury
# the record in import traffic and, worse, attribute an import triggered inside an
# adapter function to an adapter read.
FS_PREFIX = "T8-FS "

FS_AUDIT_PROLOGUE = '''
import json as _fs_json
import sys as _fs_sys

_FS_WATCHED = tuple(__WATCHED__)
_FS_ADAPTER = "/project_standards/mcp_server/"
_FS_PACKAGE = "/project_standards/"
_FS_SELFTEST = __SELFTEST__


def _fs_reader():
    """The innermost distribution frame in the stack that requested this open."""
    frame = _fs_sys._getframe()
    while frame is not None:
        name = frame.f_code.co_filename
        if _FS_PACKAGE in name:
            return name
        frame = frame.f_back
    return ""


def _fs_audit(event, arguments):
    if event != "open":
        return
    path = arguments[0]
    if not isinstance(path, str) or not path.startswith(_FS_WATCHED):
        return
    origin = _fs_reader()
    layer = "adapter" if _FS_ADAPTER in origin else "service" if origin else "foreign"
    print(
        "__FS_PREFIX__" + _fs_json.dumps({"path": path, "layer": layer, "origin": origin}),
        file=_fs_sys.stderr,
        flush=True,
    )


_fs_sys.addaudithook(_fs_audit)

if _FS_SELFTEST is not None:
    # Prove the "adapter" attribution is reachable, not merely spelled: a code
    # object compiled with an adapter filename produces exactly the frame a real
    # adapter-side read would, so the classifier is exercised in both directions
    # by the control test rather than trusted in one.
    exec(
        compile(
            "open(_FS_SELFTEST, 'rb').close()",
            _FS_ADAPTER + "_audit_selftest.py",
            "exec",
        ),
        {"_FS_SELFTEST": _FS_SELFTEST},
    )
'''


def audited_spy_launch(
    package_root: Path, *, watch: Sequence[Path], selftest: Path | None = None
) -> str:
    """The reused recording-facade launch, with the filesystem audit installed first.

    Composition rather than a fork: ``test_resources.spy_launch`` still produces
    the whole server script, and the prologue is prepended so the audit hook is
    installed before any distribution module is imported.
    """
    prologue = (
        FS_AUDIT_PROLOGUE.replace("__WATCHED__", repr([f"{path.resolve()}/" for path in watch]))
        .replace("__SELFTEST__", repr(None if selftest is None else str(selftest.resolve())))
        .replace("__FS_PREFIX__", FS_PREFIX)
    )
    return prologue + spy_launch(package_root)


def audited_opens(server: ServerProcess) -> list[dict[str, Any]]:
    """Every watched file open the audited server has reported so far."""
    records: list[dict[str, Any]] = []
    for line in bytes(server.stderr_bytes).decode("utf-8", "replace").splitlines():
        if line.startswith(FS_PREFIX):
            records.append(as_object(json.loads(line.removeprefix(FS_PREFIX)), "an open record"))
    return records


def opens_by_layer(records: Sequence[Mapping[str, Any]], layer: str) -> list[str]:
    return [str(record.get("path")) for record in records if record.get("layer") == layer]


# The facade methods each tool may reach while answering one call. Both sets are
# upper bounds rather than exact expectations, and the reason is the review's
# (F6): ``standards_list`` answers from the catalog the facade validated at
# construction, so requiring a per-call ``catalog`` reload would demand work no
# requirement asks for. What is forbidden is what matters — ``resource`` in
# either window means a tool reached for payload bytes to build a listing, which
# NFR-002 and the plan both refuse here.
ALLOWED_FACADE_CALLS: dict[str, frozenset[str]] = {
    STANDARDS_LIST: frozenset({"catalog"}),
    REPO_INSPECT: frozenset({"catalog", "inspect_repo"}),
}

# RED control only. A bare SDK server whose single tool declares an output schema
# and returns structured content plus one bounded text block — the metadata
# features the assertions below depend on being *observable*. It carries no
# ``ToolAnnotations``: FR-023 puts the read-only claim in the description, and no
# record makes the optional annotation object binding (F7). Not a template for
# T8.3.
BARE_SDK_STRUCTURED_CONTROL = """
import anyio
import mcp_types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

STRUCTURED = {"standards": [{"standard_id": "control"}]}


async def _list_tools(ctx, params):
    return types.ListToolsResult(
        tools=[
            types.Tool(
                name="standards_list",
                title="Control",
                description="Control tool. Read-only.",
                inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
                outputSchema={"type": "object", "properties": {"standards": {"type": "array"}}},
            )
        ]
    )


async def _call_tool(ctx, params):
    return types.CallToolResult(
        content=[types.TextContent(type="text", text="1 standard.")], structuredContent=STRUCTURED
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

CONTROL_STRUCTURED = {"standards": [{"standard_id": "control"}]}


# -- planned surface -----------------------------------------------------------


def require_discovery_tools(server: ServerProcess, era: Era) -> dict[str, dict[str, Any]]:
    """The two advertised discovery tools, or an explicit RED assertion.

    The planned absence T8 closes is a *registration*, not a module: ``tools.py``
    already exists from T7, so the assertion that must fail before T8.3 is that
    these two names are advertised. Asserted inside a collected test, per the
    plan's RED contract.
    """
    entries = {str(entry.get("name")): dict(entry) for entry in list_tools(server, era)}
    missing = [name for name in DISCOVERY_TOOLS if name not in entries]
    assert not missing, server.diagnosis(
        f"planned T8 tools {missing} are not advertised; the discovery-tool registration does "
        f"not exist yet. tools/list carried {sorted(entries)}"
    )
    return {name: entries[name] for name in DISCOVERY_TOOLS}


def tools_module() -> ModuleType:
    """The T7 tool module, which T8 extends rather than creates."""
    return require_tools_module()


# -- fixtures ------------------------------------------------------------------


@pytest.fixture(scope="module")
def full_runtime(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The fixture catalog as an importable installed distribution, shared read-only."""
    return build_fixture_runtime(tmp_path_factory.mktemp("discovery-full"))


@pytest.fixture(scope="module")
def grown_family(tmp_path_factory: pytest.TempPathFactory) -> GeneratedFamily:
    """The fixture catalog plus one family whose identity is generated per session.

    IR-003's acceptance is that the tool list stays "small and stable across
    fixture standard addition", and a predictable growth target would let an
    adapter with per-package branches pass a test that exists to forbid them
    (the T6.2 F5 rule).
    """
    runtime = build_fixture_runtime(tmp_path_factory.mktemp("discovery-grown"))
    return add_generated_family(
        runtime / "project_standards",
        standard_id=f"{GENERATED_ID_PREFIX}-{uuid.uuid4().hex[:10]}",
        version=GENERATED_VERSION,
    )


def _successor_release(release: str) -> str:
    """One release higher than ``release`` within the same catalog major.

    Derived rather than written down: a hard-coded version would either drift
    behind the installed release or cross the major boundary, and crossing it
    would classify as ``TOOL_MISMATCH`` instead of the ``NEWER_RELEASE`` this
    builds.
    """
    major, minor, *_ = release.split(".")
    return f"{major}.{int(minor) + 1}.0"


@pytest.fixture(scope="module")
def consumer_repos(full_runtime: Path, tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """One consumer repository per authoritative state, keyed by state value.

    Eight of the ten come from ``tests/mcp_services/test_consumer.py``'s own state
    builder — that module was written to share them and already owns every rule
    about what makes each classification real — against the *same* installed
    distribution the server serves, so the classification the tool reports and the
    classification the oracle computes cannot differ for fixture reasons.

    The remaining two are the ones that builder deliberately excludes, because
    they are properties of the *observing release* rather than of the repository:
    ``NEWER_RELEASE`` needs a control plane written by a later release of the same
    major, and ``TOOL_MISMATCH`` needs one written for a different catalog major.
    Both are built with the technique TC-T3-001 uses for exactly this reason — a
    second ``InstalledDistribution`` over the same package bytes at a different
    release, and an alternate-major installed tree — rather than with a second
    copy of the state rules (T8.2 Codex RED review, F5). The server's own
    release is what observes them, which is what makes them reachable over the
    wire at all.

    A sentinel is planted in a consumer file of every initialized repository:
    DR-005 forbids the snapshot from carrying unrelated file content, and a
    canary is the only way to prove an absence.
    """
    parent = tmp_path_factory.mktemp("discovery-consumers")
    package_root = full_runtime / "project_standards"
    distribution = InstalledDistribution(package_root, tool_release=package_version())
    repos = {kind.value: path for kind, path in build_state_fixtures(parent, distribution).items()}

    repos[StateKind.NEWER_RELEASE.value] = build_consumer_repo(
        parent,
        "state-newer-release",
        distribution=InstalledDistribution(
            package_root, tool_release=_successor_release(package_version())
        ),
        select_alpha=False,
    )
    alternate = build_installed_tree(
        tmp_path_factory.mktemp("discovery-major-six"), alternate_major=6
    )
    repos[StateKind.TOOL_MISMATCH.value] = build_consumer_repo(
        parent,
        "state-tool-mismatch",
        distribution=InstalledDistribution(alternate, tool_release="6.0.0"),
        select_alpha=False,
        catalog_major="6",
    )

    for path in repos.values():
        extension = path / ".standards/extensions/alpha/options.toml"
        if extension.is_file():
            extension.write_text(
                f'consumer = true\nsentinel = "{CONSUMER_SENTINEL}"\n', encoding="utf-8"
            )
    return repos


# -- protocol probes -----------------------------------------------------------


def structured(server: ServerProcess, frame: Mapping[str, Any], *, label: str) -> dict[str, Any]:
    """The structured content of one successful tool result, with its text bounded.

    FR-022 requires v1 tools to "return protocol-supported structured content
    plus bounded human text where useful", and the SDK's carrier for the first is
    ``structuredContent``. Structured content is required rather than merely
    accepted because the alternative — facts recoverable only by parsing human
    text — is what a typed output schema exists to replace.

    The human half is checked here rather than discarded (T8.2 Codex RED review,
    F3): NFR-012 and plan T8 both require the default text to be bounded, and a
    result whose ``content`` was never inspected could carry an arbitrarily large
    prose rendering of the same facts while every structural assertion passed.

    "Bounded" is expressed against the structured content instead of against an
    invented character budget: the text is a *summary* of the answer, so it may
    not be longer than the answer, and it may not be a second paragraph-shaped
    document. That admits any honest one-line summary and refuses the failure mode
    the requirement names.
    """
    result = expect_result(server, frame)
    assert not result.get("isError"), server.diagnosis(
        f"{label} reported a failure for a call that must succeed: {result!r}"
    )
    content = result.get("structuredContent")
    assert isinstance(content, dict), server.diagnosis(
        f"{label} returned no structuredContent object; FR-022 requires structured output "
        f"rather than facts a client must parse out of prose: {result!r}"
    )
    body = cast("dict[str, Any]", content)

    blocks = result.get("content")
    assert isinstance(blocks, list), server.diagnosis(
        f"{label} returned no content array, which the protocol requires: {result!r}"
    )
    budget = len(rendered(body))
    human = ""
    for block in cast("list[object]", blocks):
        entry = as_object(block, f"a {label} content block")
        if entry.get("type") != "text":
            continue
        text = entry.get("text")
        assert isinstance(text, str), server.diagnosis(
            f"{label} returned a text block with no string text: {entry!r}"
        )
        assert "\n\n" not in text.strip(), server.diagnosis(
            f"{label}'s human text is multi-paragraph; NFR-012 wants a bounded summary, not a "
            f"prose rendering of the structured answer: {text!r}"
        )
        human += text
    assert len(human) <= budget, server.diagnosis(
        f"{label}'s human text is {len(human)} characters against {budget} of structured "
        "content; a summary that outgrows its answer is the verbosity NFR-012 forbids"
    )
    return body


def rendered(value: object) -> str:
    return json.dumps(value, sort_keys=True, default=str)


def input_properties(server: ServerProcess, entry: Mapping[str, Any]) -> dict[str, Any]:
    schema = as_object(entry.get("inputSchema"), f"the {entry.get('name')!r} input schema")
    assert schema.get("type") == "object", server.diagnosis(
        f"{entry.get('name')!r} must declare an object input schema; got {schema.get('type')!r}"
    )
    raw = schema.get("properties")
    return as_object(cast("object", raw), "input properties") if isinstance(raw, dict) else {}


def required_names(entry: Mapping[str, Any]) -> list[str]:
    schema = as_object(entry.get("inputSchema"), "input schema")
    raw = schema.get("required")
    return [str(name) for name in cast("list[object]", raw)] if isinstance(raw, list) else []


def facade_calls(server: ServerProcess) -> list[str]:
    """The names of the facade methods the recording server has reported so far."""
    return [str(record.get("call")) for record in spy_calls(server)]


def refusal_of(server: ServerProcess, frame: Mapping[str, Any], *, why: str) -> dict[str, Any]:
    """One structured refusal, in either form the protocol allows for a tool."""
    if "error" in frame:
        return expect_error(server, frame)
    result = expect_result(server, frame)
    assert result.get("isError"), server.diagnosis(f"{why} was answered successfully: {frame!r}")
    return result


def service_code(refusal: Mapping[str, Any]) -> object:
    """The stable service code a refusal published, or its JSON-RPC code."""
    data = refusal.get("data")
    if isinstance(data, dict):
        published = cast("dict[str, object]", data).get("code")
        if published is not None:
            return published
    return refusal.get("code")


class _SchemaValidator(Protocol):
    """The one validator method used here, typed so strict mode can see it."""

    def iter_errors(self, instance: object) -> Iterator[object]: ...


def assert_valid_schema(server: ServerProcess, schema: object, *, label: str) -> dict[str, Any]:
    """One declared schema, checked against the JSON Schema metaschema itself.

    An empty object is a legal schema that constrains nothing, so "a schema is
    declared" and "the result is typed" are different claims (T8.2 Codex RED
    review, F4). Both halves are asserted: the declaration must validate as a
    2020-12 schema *and* must actually constrain the instance kind.
    """
    declared = as_object(schema, label)
    try:
        Draft202012Validator.check_schema(declared)
    except SchemaError as error:  # pragma: no cover - failure path is the assertion
        raise AssertionError(
            server.diagnosis(f"{label} is not a valid JSON Schema: {error.message}")
        ) from error
    assert declared, server.diagnosis(f"{label} is empty, so it types nothing (FR-022, IR-003)")
    assert declared.get("type") == "object", server.diagnosis(
        f"{label} must type its instance as an object; got {declared.get('type')!r}"
    )
    return declared


def assert_conforms(
    server: ServerProcess, instance: Mapping[str, Any], schema: Mapping[str, Any], *, label: str
) -> None:
    """One returned tool result, validated against the schema the tool declared.

    Reached through ``iter_errors`` behind a narrow protocol, which is how the
    control-plane provider validator already calls this library under strict
    typing.
    """
    validator = cast("_SchemaValidator", Draft202012Validator(dict(schema)))
    error = next(validator.iter_errors(dict(instance)), None)
    assert error is None, server.diagnosis(
        f"{label} returned structured content that violates its own declared output schema: {error}"
    )


def mentioned_standard_ids(document: object, catalog: CatalogDescriptor) -> set[str]:
    """Every declared standard id that appears as a token in a rendered document.

    Identifier tokens keep hyphens (the T6.1 rule), so the resource id
    ``relation-beta`` is not read as a mention of the standard ``beta``.
    """
    tokens = set(re.findall(r"[a-z0-9][a-z0-9-]*", rendered(document)))
    return {descriptor.standard_id for descriptor in catalog.standards} & tokens


# -- RED controls --------------------------------------------------------------


def test_structured_output_probes_observe_a_typed_tool_result() -> None:
    """RED control (T8.2): typed output and structured content are visible on the wire.

    The metadata assertions below read ``outputSchema`` and ``structuredContent``
    out of protocol frames, so this drives the same probes against a bare SDK
    server that publishes both, in both eras. What it establishes is that the
    selected SDK carries them over stdio and that the probes look in the right
    place — not that a missing field would be tolerated, which ``structured``
    already refuses outright.
    """
    for era in (ERAS[0], MODERN_ERA):
        with ServerProcess(BARE_SDK_STRUCTURED_CONTROL, label=f"structured-control-{era.name}") as (
            server
        ):
            result = era.open(server)
            capabilities = declared_capabilities(result)
            assert capabilities.get("tools") is not None
            assert_no_list_change_promises(capabilities)
            reachable = assert_capabilities_match_reachable_registrations(
                server, capabilities, envelope=era.envelope
            )
            assert_no_write_surface(server, reachable)

            entry = next(item for item in list_tools(server, era) if item["name"] == STANDARDS_LIST)
            assert isinstance(entry.get("outputSchema"), dict), (
                "the control declares an output schema, so the probe must observe one"
            )
            assert input_properties(server, entry) == {}
            body = structured(
                server,
                call_tool(server, era, name=STANDARDS_LIST, arguments={}),
                label="the control",
            )
            assert body == CONTROL_STRUCTURED
            assert server.finish() == 0
            assert_stdout_is_protocol_only(server)


def test_filesystem_probe_attributes_reads_to_their_layer(full_runtime: Path) -> None:
    """RED control (T8.2, review F6): the audit prologue is a falsifiable oracle.

    ``test_discovery_tools_reach_facts_only_through_the_facade`` claims that no
    watched file is opened by the adapter itself. An oracle that could not see a
    read, or could not tell who performed it, would satisfy that claim by being
    blind — which is exactly what the review found in the facade-call-only
    version.

    So both directions are established here, against surfaces that already exist
    at RED. ``standard_read`` is driven through the audited server for one
    declared payload resource, and the resulting record must be a *service*-layer
    open of that payload: the probe sees real reads and attributes delegation
    correctly. The prologue's self-test performs the same open from a frame
    compiled with an adapter filename, and that record must be attributed to the
    *adapter*: the failing classification is reachable, so its absence later is
    evidence rather than silence.
    """
    require_mcp_subcommand()
    era = MODERN_ERA
    package_root = full_runtime / "project_standards"
    catalog = oracle_facade(full_runtime).catalog()
    uri = sorted(declared_resources(catalog))[0]
    watched = [package_root / name for name in FIXTURE_SUBTREES]
    probe_target = next(iter(sorted((package_root / "payloads").rglob("*.md"))))

    script = audited_spy_launch(package_root, watch=watched, selftest=probe_target)
    with resource_session(era, runtime_root=full_runtime, label="fs-control", script=script) as (
        server,
        _,
    ):
        server.drain(0.5)
        startup = audited_opens(server)
        assert str(probe_target) in opens_by_layer(startup, "adapter"), server.diagnosis(
            "the prologue's adapter-attributed self-test open was not recorded as an adapter "
            f"read, so the classification the facade test relies on is unreachable: {startup!r}"
        )

        before = len(audited_opens(server))
        # Asserted as a plain successful result rather than through ``structured``:
        # this control has to pass while T8 is absent, and ``standard_read`` gains
        # its structured content at T8.3.
        read = expect_result(server, call_tool(server, era, "uri", uri, name=STANDARD_READ))
        assert not read.get("isError"), server.diagnosis(
            f"{STANDARD_READ} refused {uri}, so nothing was read to observe: {read!r}"
        )
        server.drain(0.5)
        window = audited_opens(server)[before:]
        service_reads = opens_by_layer(window, "service")
        assert service_reads, server.diagnosis(
            f"reading {uri} through {STANDARD_READ} recorded no watched open, so the probe "
            f"cannot observe payload reads at all: {window!r}"
        )
        assert all("/payloads/" in path for path in service_reads), server.diagnosis(
            f"the recorded reads are not payload reads: {service_reads!r}"
        )
        assert not opens_by_layer(window, "adapter"), server.diagnosis(
            f"{STANDARD_READ} delegates to the resource service, so no adapter-layer open may "
            f"be recorded for it: {window!r}"
        )
        assert server.finish() == 0


# -- frozen acceptance tests ---------------------------------------------------


@pytest.mark.parametrize("era", ERAS, ids=ERA_IDS)
def test_standards_list_matches_catalog_resource(full_runtime: Path, era: Era) -> None:
    """TC-T8-001 (FR-007, FR-021, FR-022): one catalog projection, two surfaces.

    FR-007's acceptance is exact — the tool "returns the same installed catalog
    facts and exact resource URIs as FR-001" — and T6 already serves those facts
    at ``standards://catalog/5`` as the FR-001 field-masked projection. So the
    assertion is equality, three ways, on one connection: the tool's structured
    content equals the service layer's masked projection, equals the document the
    catalog resource serves, and carries every declared package and payload URI
    verbatim.

    Node-for-node equality of the *decoded* documents rather than "contains the
    same facts" follows the T7 precedent for ``standard_read``: a re-serialized or
    field-dropped copy is a second projection of the catalog, which is exactly
    what one shared mapping exists to prevent. Key *order* is deliberately not
    asserted, and this test does not claim to detect it: a JSON object has no
    declared member order on the wire, so ordering is not a protocol fact a client
    could rely on (T8.2 Codex RED review, F10). Sequence order is asserted, since
    that is declared.

    The tool must also take no package-specific argument (plan:423): a tool that
    accepted a standard id would be the per-standard surface FR-007 exists to
    replace, and would make the catalog listing depend on what the caller already
    knew.
    """
    require_mcp_subcommand()
    facade = oracle_facade(full_runtime)
    catalog = facade.catalog()
    expected = catalog_projection(catalog)

    with resource_session(era, runtime_root=full_runtime, label="standards-list") as (server, _):
        entry = require_discovery_tools(server, era)[STANDARDS_LIST]

        # No package-specific argument: nothing required, and no property named
        # for a package, standard, or version.
        assert required_names(entry) == [], server.diagnosis(
            f"{STANDARDS_LIST} requires {required_names(entry)}; plan:423 gives it no "
            "package-specific argument"
        )
        specific = sorted(
            name
            for name in input_properties(server, entry)
            if any(token in name.lower() for token in ("standard", "package", "version", "id"))
        )
        assert not specific, server.diagnosis(
            f"{STANDARDS_LIST} declares package-specific arguments {specific}"
        )

        body = structured(
            server, call_tool(server, era, name=STANDARDS_LIST, arguments={}), label=STANDARDS_LIST
        )
        assert body == expected, server.diagnosis(
            f"{STANDARDS_LIST} does not return the exact FR-001 catalog projection"
        )
        assert body == metadata_document(server, era, CATALOG_URI), server.diagnosis(
            f"{STANDARDS_LIST} and {CATALOG_URI} disagree, so the catalog has two projections"
        )

        # "exact resource URIs as FR-001": every declared payload URI, verbatim.
        rendered_body = rendered(body)
        for uri in declared_resources(catalog):
            assert uri in rendered_body, server.diagnosis(
                f"{STANDARDS_LIST} omits the declared resource URI {uri}"
            )

        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


@pytest.mark.parametrize("era", ERAS, ids=ERA_IDS)
def test_repo_inspect_requires_contained_explicit_root_and_preserves_snapshot(
    full_runtime: Path, consumer_repos: dict[str, Path], era: Era
) -> None:
    """TC-T8-002 (FR-009, FR-024, DR-005): every state, exactly; every root, explicitly.

    Three obligations, asserted together because they are one tool's contract.

    *Every authoritative state, preserved.* The tool is run against one
    repository per classification ``StateKind`` defines — the set is asserted to
    be complete rather than assumed, so a new classification fails here instead of
    escaping — and its structured output must equal
    ``McpServiceFacade.inspect_repo(...).model_dump(mode="json")`` for that
    repository, node for node. That is FR-009's "reports missing/invalid state"
    and DR-005's bounded snapshot in one assertion, and it is what stops the tool
    from inventing a health summary over the authoritative classification. The
    legacy-only case additionally proves FR-009's "does not treat legacy config
    as current authority": a repository carrying only ``.project-standards.yml``
    is reported as such, with no parsed desired state.

    *An explicit root, or nothing.* FR-024 requires ``repo_root``, so a call
    omitting it is a structured refusal rather than an inspection of the working
    directory — the failure mode that would make the tool's answer depend on how
    the server happened to be launched.

    *Containment, and only narrowing.* The NUL-bearing, nonexistent, and
    non-string cases are the structural refusals T5 froze; the launch-boundary
    half is proven on the wire by
    ``test_repo_inspect_containment_follows_the_launch_boundary``.

    *And no consumer file content.* DR-005 excludes unrelated content, so a
    sentinel planted inside a consumer file must appear in no answer.

    Each state's answer is additionally validated against the output schema the
    tool advertised. That is here rather than only in TC-T8-004 because the
    ``Finding`` arm of that schema is only reachable from a *degraded* repository:
    nine of the ten classifications carry findings and the initialized one carries
    none, so a conformance check that saw only the initialized snapshot would never
    validate a finding at all.
    """
    require_mcp_subcommand()
    facade = oracle_facade(full_runtime)
    assert set(consumer_repos) == {kind.value for kind in StateKind}, (
        "the fixtures do not cover every authoritative classification, so TC-T8-002's "
        f"'every state' claim would be nominal: missing "
        f"{sorted({kind.value for kind in StateKind} - set(consumer_repos))}"
    )

    with resource_session(era, runtime_root=full_runtime, label="repo-inspect") as (server, _):
        entry = require_discovery_tools(server, era)[REPO_INSPECT]

        assert required_names(entry) == [REPO_ROOT_ARGUMENT], server.diagnosis(
            f"FR-024 requires an explicit {REPO_ROOT_ARGUMENT!r}; the schema requires "
            f"{required_names(entry)}"
        )
        declared_output = assert_valid_schema(
            server, entry.get("outputSchema"), label=f"{REPO_INSPECT}'s output schema"
        )

        for state, repo in sorted(consumer_repos.items()):
            body = structured(
                server,
                call_tool(
                    server, era, name=REPO_INSPECT, arguments={REPO_ROOT_ARGUMENT: str(repo)}
                ),
                label=f"{REPO_INSPECT}({state})",
            )
            snapshot = facade.inspect_repo(repo).model_dump(mode="json")
            assert body == snapshot, server.diagnosis(
                f"{REPO_INSPECT} does not preserve the exact RepoInspectionSnapshot for the "
                f"{state} repository"
            )
            assert body["state"] == state, server.diagnosis(
                f"the {state} repository was reported as {body['state']!r}"
            )
            assert body["repo_root"] == ".", server.diagnosis(
                "DR-005 normalizes the root identity to '.'; got "
                f"{body['repo_root']!r} for the {state} repository"
            )
            assert CONSUMER_SENTINEL not in rendered(body), server.diagnosis(
                f"the {state} snapshot carries consumer file content"
            )
            # Conformance is checked per state rather than once, because nine of
            # the ten classifications carry findings and the initialized one
            # carries none: a schema validated only against the empty case never
            # meets a `Finding` instance at all (T8.4 Codex GREEN review, F2).
            assert_conforms(server, body, declared_output, label=f"{REPO_INSPECT}({state})")

        # Legacy config is never current authority (FR-009).
        legacy = structured(
            server,
            call_tool(
                server,
                era,
                name=REPO_INSPECT,
                arguments={REPO_ROOT_ARGUMENT: str(consumer_repos[StateKind.LEGACY_ONLY.value])},
            ),
            label=f"{REPO_INSPECT}(legacy)",
        )
        assert legacy["desired_config"] is None, server.diagnosis(
            "a legacy-only repository has no current desired state, so the slot must be absent"
        )

        # An explicit root is required, and structural refusals stay structural.
        for arguments, why in (
            ({}, "no repo_root at all"),
            ({REPO_ROOT_ARGUMENT: str(full_runtime / "no-such-repository")}, "a missing root"),
            ({REPO_ROOT_ARGUMENT: f"{full_runtime}{NUL}"}, "a NUL-bearing root"),
            ({REPO_ROOT_ARGUMENT: 17}, "a non-string root"),
        ):
            frame = call_tool(server, era, name=REPO_INSPECT, arguments=arguments)
            assert "error" in frame or expect_result(server, frame).get("isError"), (
                server.diagnosis(f"{REPO_INSPECT} answered {why} successfully: {frame!r}")
            )
            assert CONSUMER_SENTINEL not in rendered(frame)
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


def test_repo_inspect_containment_follows_the_launch_boundary(
    full_runtime: Path, consumer_repos: dict[str, Path], tmp_path: Path
) -> None:
    """FR-024 / ADR 0026: the configured boundary narrows this tool, and only narrows.

    T5 proved the boundary reaches adapter construction and that
    ``resolve_effective_root`` honours it, but at that task no tool took a
    ``repo_root``, so nothing closed the path from the launch option to a
    protocol call. ``repo_inspect`` is the first tool that does, which makes this
    the task that must prove the boundary is enforced *on the wire* rather than
    only in the resolver.

    Three observations, because "refused" alone would not distinguish the
    boundary from an ordinary bad root (T8.2 Codex RED review, F10):

    * inside the boundary, the same root inspects normally;
    * outside it, the root is refused;
    * on a second server launched with no boundary, that *same* root inspects
      normally.

    The third is what makes the refusal attributable to the boundary rather than
    to the root: the directory exists, resolves, and is a perfectly valid consumer
    root — what it is not, in the first server, is admissible. Its refusal code is
    also required to differ from the missing-root class, so the two failure
    taxonomies cannot silently collapse into one.
    """
    era = MODERN_ERA
    require_mcp_subcommand()
    option = boundary_option_name(require_mcp_subcommand())

    inside = consumer_repos[StateKind.INITIALIZED.value]
    boundary = inside.parent
    outside = tmp_path / "elsewhere"
    outside.mkdir()

    script = cli_launch_with([option, str(boundary)])
    with resource_session(
        era, runtime_root=full_runtime, label="repo-inspect-boundary", script=script
    ) as (server, _):
        require_discovery_tools(server, era)
        body = structured(
            server,
            call_tool(server, era, name=REPO_INSPECT, arguments={REPO_ROOT_ARGUMENT: str(inside)}),
            label="an in-boundary root",
        )
        assert body["state"] == StateKind.INITIALIZED.value

        refused = refusal_of(
            server,
            call_tool(server, era, name=REPO_INSPECT, arguments={REPO_ROOT_ARGUMENT: str(outside)}),
            why=f"a root outside {boundary}",
        )
        missing = refusal_of(
            server,
            call_tool(
                server,
                era,
                name=REPO_INSPECT,
                arguments={REPO_ROOT_ARGUMENT: str(boundary / "no-such-repository")},
            ),
            why="a nonexistent root inside the boundary",
        )
        assert service_code(refused) != service_code(missing), server.diagnosis(
            "an out-of-boundary root and a nonexistent root are different failures, so they "
            f"may not share a stable code: both reported {service_code(refused)!r}"
        )
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)

    with resource_session(era, runtime_root=full_runtime, label="repo-inspect-unbounded") as (
        server,
        _,
    ):
        require_discovery_tools(server, era)
        unbounded = structured(
            server,
            call_tool(server, era, name=REPO_INSPECT, arguments={REPO_ROOT_ARGUMENT: str(outside)}),
            label="the same root with no boundary configured",
        )
        assert unbounded["state"] == StateKind.UNINITIALIZED.value, server.diagnosis(
            "the out-of-boundary root must be an ordinary inspectable directory, or its refusal "
            "above proved nothing about the boundary"
        )
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


def test_tool_metadata_is_compact_and_read_only(full_runtime: Path) -> None:
    """TC-T8-003 (FR-023, NFR-012): the advertised metadata, snapshotted and reviewed.

    Tool metadata is paid on every session before a single call, so FR-023 wants
    it "concise, unambiguous, and test-reviewed" and its acceptance is that
    "tests snapshot the supported-client tool metadata". This is that snapshot:
    the whole advertised surface must equal :data:`EXPECTED_TOOL_METADATA`, field
    for field, for every tool the recorded client matrix registers.

    **Scope: the three tools this suite registers.** T9 completed the registry,
    and each suite reviews the metadata it introduced — whole-surface equality
    over all six is asserted by
    ``tests/mcp_server/test_consumer_tools.test_consumer_tool_metadata_is_compact_and_read_only``
    against the union of the two reviewed constants. What stays here
    unilaterally is that the advertised surface is exactly ADR 0026's frozen
    registry, so a seventh tool, a renamed tool, or a missing one fails here as
    well (T9.4 Codex GREEN review, F5).

    Snapshot equality is what an invented budget could not give. A description
    that had grown into documentation, a retyped schema, a dropped authority
    sentence, and a schema that enumerated installed standard ids all change this
    constant; none of them is reliably caught by a character count, and a
    character count additionally rejects conforming metadata for reasons no
    record states (T8.2 Codex RED review, F1/F2).

    The constant is then held to FR-023's own three obligations — purpose, input
    authority, and read-only effect — so that a future edit to the snapshot has
    to keep saying what the requirement demands. Protocol annotations are not
    asserted: FR-023 places the read-only claim in the description, ADR 0026
    freezes behavior rather than annotation presence, and the SDK treats
    ``ToolAnnotations`` as optional (F7).
    """
    require_mcp_subcommand()
    era = MODERN_ERA
    with resource_session(era, runtime_root=full_runtime, label="tool-metadata") as (server, _):
        require_discovery_tools(server, era)
        entries = list_tools(server, era)
        served = {str(entry.get("name")): dict(entry) for entry in entries}
        assert len(served) == len(entries), server.diagnosis(
            f"a tool is advertised more than once: {tool_names(entries)}"
        )
        reviewed_here = {
            name: entry for name, entry in served.items() if name in EXPECTED_TOOL_METADATA
        }
        assert reviewed_here == EXPECTED_TOOL_METADATA, server.diagnosis(
            "the metadata of the tools this suite registers is not the reviewed FR-023 "
            f"snapshot.\nserved:   {rendered(reviewed_here)}\n"
            f"reviewed: {rendered(EXPECTED_TOOL_METADATA)}"
        )
        assert set(served) == FROZEN_V1_TOOLS, server.diagnosis(
            "the advertised surface is not exactly ADR 0026's frozen v1 registry. The tools "
            "outside this suite's snapshot are reviewed by "
            "tests/mcp_server/test_consumer_tools.py, which asserts whole-surface equality "
            f"against the union.\nadvertised: {sorted(served)}\n"
            f"frozen:     {sorted(FROZEN_V1_TOOLS)}"
        )
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)

    for name, metadata in EXPECTED_TOOL_METADATA.items():
        description = str(metadata["description"])
        lowered = description.lower()
        assert "\n" not in description.strip(), (
            f"{name}'s reviewed description is multi-paragraph; a tool picker shows one line"
        )
        missing = [claim for claim in REVIEWED_DESCRIPTION_CLAIMS[name] if claim not in lowered]
        assert not missing, (
            f"{name}'s reviewed description no longer states its purpose and input authority; "
            f"missing {missing} (FR-023)"
        )
        assert any(claim in lowered for claim in READ_ONLY_CLAIMS), (
            f"{name}'s reviewed description does not state its read-only effect (FR-023)"
        )
        negated = [claim for claim in NEGATED_READ_ONLY_CLAIMS if claim in lowered]
        assert not negated, f"{name}'s reviewed description negates the read-only claim: {negated}"
        forbidden = [token for token in FORBIDDEN_DESCRIPTION_TOKENS if token in lowered]
        assert not forbidden, (
            f"{name}'s reviewed description carries verbosity or recommendation language: "
            f"{forbidden}"
        )


def test_tools_are_typed_and_generic(
    full_runtime: Path, grown_family: GeneratedFamily, consumer_repos: dict[str, Path]
) -> None:
    """TC-T8-004 (IR-003, FR-022): real typed schemas, and a surface data cannot grow.

    IR-003's acceptance has two halves and both are asserted.

    *Typed.* Every registered tool declares an object input schema and an object
    output schema, each of which must itself validate against the JSON Schema
    2020-12 metaschema — and, the part a presence check cannot give, every tool is
    then *called* and its structured content is validated against the output
    schema it declared. A declared ``{}`` satisfies "has an output schema" while
    typing nothing, and a schema no instance is ever checked against is a comment
    (T8.2 Codex RED review, F4). ``standard_read`` is called here too, because
    FR-022's "every v1 tool ... returns protocol-supported structured content"
    does not exempt the fallback — and it is called twice, once for a declared
    payload resource and once for a metadata form, so both arms of its nullable
    declaration slot are exercised rather than only the populated one.

    Deliberately *not* asserted: that every input property carries a direct
    ``type``. JSON Schema 2020-12 expresses a typed property through ``$ref``,
    ``anyOf``, ``const``, and ``enum`` as legitimately as through ``type``, so
    that rule rejected conforming schemas (F4, amended disposition). The
    metaschema check plus instance validation is the sound version of the same
    claim.

    *Generic.* Adding an installed standard must change no tool. The comparison is
    made against a distribution that differs by exactly one family whose identity
    is generated per session, so an adapter carrying per-package branches cannot
    pass by naming what it knows. The whole advertised metadata is compared, not
    just the names: a schema that grew an enum of installed standard ids would be
    per-package branching by another route.

    *And the growth has to reach the answer.* The grown session calls
    ``standards_list`` too, and its structured content must equal *that* runtime's
    own facade projection and the catalog resource it serves in the same session,
    with the generated standard present. Comparing only the tool *surface* across
    the two distributions left a hole a hardcoded fixture catalog would fit
    through: a tool that always answered with the baseline catalog would show an
    identical surface and an identical answer, and pass (T8.4 Codex GREEN review,
    F3). This is the positive provenance half of "growth lives in the data".

    The plan's stop condition is checked here too, as names: no
    ``standards_resolve``, nothing that recommends rather than reports, no tool
    named after a standard, and nothing outside ADR 0026's frozen six.
    """
    require_mcp_subcommand()
    era = MODERN_ERA
    catalog = oracle_facade(full_runtime).catalog()
    repo = consumer_repos[StateKind.INITIALIZED.value]
    resource_uri = sorted(declared_resources(catalog))[0]
    # Every advertised tool needs a conformance call here, and the assertion in
    # the loop below says so, so this map grows with the registry: T9 registered
    # three repository-scoped tools and each takes the same explicit root
    # (T9.2 Codex RED review, F7 — the conflict this map would otherwise have
    # become at T9 GREEN).
    root_arguments = {REPO_ROOT_ARGUMENT: str(repo)}
    call_arguments: dict[str, dict[str, Any]] = {
        STANDARDS_LIST: {},
        REPO_INSPECT: root_arguments,
        STANDARD_READ: {"uri": resource_uri},
        RECONCILE_PREVIEW: root_arguments,
        VALIDATE_REPO: root_arguments,
        DRIFT_CHECK: root_arguments,
    }
    grown_expected = catalog_projection(oracle_facade(grown_family.runtime).catalog())

    surfaces: list[str] = []
    for label, runtime in (("baseline", full_runtime), ("grown", grown_family.runtime)):
        with resource_session(era, runtime_root=runtime, label=f"typed-{label}") as (server, _):
            require_discovery_tools(server, era)
            entries = list_tools(server, era)
            names = tool_names(entries)

            unknown = sorted(set(names) - FROZEN_V1_TOOLS)
            assert not unknown, server.diagnosis(
                f"tools outside ADR 0026's frozen v1 registry are advertised: {unknown}"
            )
            forbidden = sorted(name for name in names if name in FORBIDDEN_TOOL_NAMES)
            assert not forbidden, server.diagnosis(f"the plan forbids {forbidden} under T8")
            shaped = sorted(
                name
                for name in names
                if any(token in name for token in FORBIDDEN_TOOL_TOKENS)
                or mentioned_standard_ids(name, catalog)
            )
            assert not shaped, server.diagnosis(
                f"{shaped} name a per-standard or recommending surface the plan forbids"
            )

            for entry in entries:
                name = str(entry.get("name"))
                assert_valid_schema(
                    server, entry.get("inputSchema"), label=f"{name}'s input schema"
                )
                output = assert_valid_schema(
                    server, entry.get("outputSchema"), label=f"{name}'s output schema"
                )
                if label != "baseline":
                    continue
                assert name in call_arguments, server.diagnosis(
                    f"{name} is advertised but this test has no conformance call for it; every "
                    "v1 tool must return structured content (FR-022)"
                )
                body = structured(
                    server,
                    call_tool(server, era, name=name, arguments=call_arguments[name]),
                    label=name,
                )
                assert_conforms(server, body, output, label=name)
                if name == STANDARD_READ:
                    # The metadata forms declare no payload resource, so this is
                    # the null arm of the declaration slot. Both arms are needed:
                    # a schema checked only against a populated declaration cannot
                    # show that it accepts the absence and rejects a partial one.
                    metadata = structured(
                        server,
                        call_tool(server, era, name=name, arguments={"uri": CATALOG_URI}),
                        label=f"{name}({CATALOG_URI})",
                    )
                    assert metadata["declaration"] is None, server.diagnosis(
                        f"{CATALOG_URI} declares no payload resource, so its declaration slot "
                        f"must be absent; got {metadata['declaration']!r}"
                    )
                    assert_conforms(server, metadata, output, label=f"{name}({CATALOG_URI})")

            if label == "grown":
                grown_body = structured(
                    server,
                    call_tool(server, era, name=STANDARDS_LIST, arguments={}),
                    label=f"{STANDARDS_LIST} on the grown distribution",
                )
                assert grown_body == grown_expected, server.diagnosis(
                    f"{STANDARDS_LIST} does not return the grown distribution's own catalog "
                    "projection, so its answer is not derived from the installed catalog it "
                    "was launched over"
                )
                assert grown_body == metadata_document(server, era, CATALOG_URI), server.diagnosis(
                    f"{STANDARDS_LIST} and {CATALOG_URI} disagree on the grown distribution"
                )
                assert grown_family.standard_id in rendered(grown_body), server.diagnosis(
                    "the generated standard is installed but absent from the listing; growth "
                    "must appear in the data (FR-004)"
                )

            surfaces.append(rendered(sorted(entries, key=lambda item: str(item.get("name")))))
            assert server.finish() == 0

    assert surfaces[0] == surfaces[1], (
        "installing a standard changed the tool surface; IR-003 requires the tool list to be "
        "stable across fixture standard addition, and FR-004 keeps growth in the data"
    )
    assert grown_family.standard_id not in surfaces[1], (
        "the tool surface names the generated standard, which is per-package branching"
    )


@pytest.mark.parametrize("era", ERAS, ids=ERA_IDS)
def test_relationships_preserve_v2_declarations(full_runtime: Path, era: Era) -> None:
    """TC-T8-005 (DR-006, FR-021): companions, extends, and conflicts, exactly.

    DR-006 is precise — relationship data "shall preserve V2 companions, extends,
    and conflicts exactly; independence is the empty default" — and FR-021 adds
    that results must *distinguish* the three and that "companions never block".
    Distinguishing is unachievable without named buckets, and the only named
    buckets in the contract are the ``RelationshipSet`` fields the service layer
    already publishes, so the assertion is equality against those fields per
    declared package rather than a reconstruction from prose.

    Independence is asserted as a positive, not skipped: a package that declares
    no relation must carry all three buckets empty and must mention no other
    declared standard anywhere in its entry. Both halves are guarded against
    vacuity the way the reused T6 relationship test guards them — at least one
    fixture package declares a relation, and at least one does not (T8.2 Codex
    RED review, F8) — because a fixture in which every package is related leaves
    the empty default entirely untested.
    """
    require_mcp_subcommand()
    catalog = oracle_facade(full_runtime).catalog()
    related = [
        descriptor
        for descriptor in catalog.standards
        if descriptor.relationships != RelationshipSet()
    ]
    assert related, "the fixture catalog declares no relationships, so this test is vacuous"
    assert len(related) < len(catalog.standards), (
        "every fixture package declares relations, so the independent-package half of DR-006's "
        "'independence is the empty default' is untested"
    )

    with resource_session(era, runtime_root=full_runtime, label="relationships") as (server, _):
        require_discovery_tools(server, era)
        body = structured(
            server, call_tool(server, era, name=STANDARDS_LIST, arguments={}), label=STANDARDS_LIST
        )
        # Keyed by exact package identity, not by standard id. The fixture catalog
        # advertises two versions of `alpha` concurrently — which is the whole point
        # of ADR 0024's version-qualified channels — and they declare *different*
        # relations, so an id-keyed map silently drops one and compares the other
        # against the wrong declaration.
        served = {
            (str(entry.get("standard_id")), str(entry.get("package_version"))): entry
            for entry in (
                as_object(item, "a standards_list entry")
                for item in cast("list[object]", body.get("standards", []))
            )
        }
        assert set(served) == {
            (descriptor.standard_id, descriptor.package_version) for descriptor in catalog.standards
        }

        for descriptor in catalog.standards:
            entry = served[(descriptor.standard_id, descriptor.package_version)]
            expected = descriptor.relationships.model_dump(mode="json")
            assert entry.get("relationships") == expected, server.diagnosis(
                f"{descriptor.standard_id} relationships {entry.get('relationships')!r} differ "
                f"from the declared {expected!r}"
            )
            union = {
                related_id
                for bucket in expected.values()
                for related_id in cast("list[str]", bucket)
                if related_id != descriptor.standard_id
            }
            mentioned = mentioned_standard_ids(entry, catalog) - {descriptor.standard_id}
            assert mentioned == union, server.diagnosis(
                f"{descriptor.standard_id} mentions {sorted(mentioned)} but declares "
                f"{sorted(union)}; nothing may be dropped or invented"
            )
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


# -- carry-forward obligations and boundaries ----------------------------------


def test_discovery_tools_register_independently_of_the_client_matrix(full_runtime: Path) -> None:
    """T7.4 review carry-forward: only the fallback is conditional.

    ``standard_read`` exists because the client matrix says a supported primary
    client cannot reach resources directly (FR-008), and T7 froze four matrix
    outcomes around exactly that. The discovery tools are not fallbacks: FR-007
    and FR-009 make them unconditional parts of the v1 surface, so the
    counterfactual matrix in which every client has direct resource access must
    remove ``standard_read`` and *nothing else*.

    The T7 test asserted membership rather than set equality precisely so this
    task could widen it; what that test cannot see, and this one must, is that
    the tools capability itself survives the all-direct case now that two
    unconditional tools exist.
    """
    require_mcp_subcommand()
    era = MODERN_ERA
    module = tools_module()
    evidence = client_matrix_evidence(module)
    assert evidence == FROZEN_CLIENT_MATRIX, (
        f"{EVIDENCE_NAME} is no longer the frozen T1 matrix; refresh T1 rather than this test"
    )
    all_direct = dict.fromkeys(evidence, True)

    script = matrix_launch(full_runtime / "project_standards", all_direct)
    with resource_session(
        era, runtime_root=full_runtime, label="matrix-all-direct", script=script
    ) as (server, result):
        capabilities = declared_capabilities(result)
        reachable = assert_capabilities_match_reachable_registrations(
            server, capabilities, envelope=era.envelope
        )
        assert reachable.get("tools") is not None, server.diagnosis(
            "the all-direct matrix removed the whole tools capability; only the FR-008 fallback "
            "is conditional on the client matrix"
        )
        advertised = set(tool_names(list_tools(server, era)))
        assert STANDARD_READ not in advertised, server.diagnosis(
            f"every client has direct resource access, so {STANDARD_READ} must be omitted"
        )
        missing = [name for name in DISCOVERY_TOOLS if name not in advertised]
        assert not missing, server.diagnosis(
            f"{missing} are unconditional, but the all-direct matrix removed them: "
            f"{sorted(advertised)}"
        )
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


def test_discovery_tools_reach_facts_only_through_the_facade(
    full_runtime: Path, consumer_repos: dict[str, Path]
) -> None:
    """Plan T8: "neither tool reads resources or repository file contents itself".

    Invisible from the wire — a tool that opened files and returned the right
    answer looks identical to one that delegated — so it is observed at two
    boundaries at once, and both are needed.

    *The service boundary*, through the recording facade T6 built for the same
    question. Each call's facade traffic must fall inside the set that tool is
    allowed to reach (:data:`ALLOWED_FACADE_CALLS`), which forbids ``resource``
    in both windows: a listing built from payload bytes is the cost NFR-002 and
    the plan refuse here. ``repo_inspect`` must additionally *make* the
    ``inspect_repo`` call, because that is the only authority that reloads
    consumer state per call. ``standards_list`` is held to no positive
    requirement, since answering from the catalog the facade validated at
    construction is correct and a per-call reload would be work no requirement
    asks for (T8.2 Codex RED review, F6).

    *The filesystem boundary*, through the audit prologue. Facade traffic alone
    cannot falsify this claim in the direction that matters: a tool with its own
    reader records *no* facade call, which a call-counting oracle reads as
    success. So every watched open is attributed to the layer that performed it,
    and no watched open in either window may be attributed to the adapter. The
    prologue's ability to see and attribute a real read is established
    independently by ``test_filesystem_probe_attributes_reads_to_their_layer``.
    """
    require_mcp_subcommand()
    era = MODERN_ERA
    repo = consumer_repos[StateKind.INITIALIZED.value]
    package_root = full_runtime / "project_standards"
    watched = [*(package_root / name for name in FIXTURE_SUBTREES), repo.parent]
    script = audited_spy_launch(package_root, watch=watched)

    with resource_session(era, runtime_root=full_runtime, label="discovery-spy", script=script) as (
        server,
        _,
    ):
        require_discovery_tools(server, era)

        for name, arguments in (
            (STANDARDS_LIST, {}),
            (REPO_INSPECT, {REPO_ROOT_ARGUMENT: str(repo)}),
        ):
            before_calls = len(facade_calls(server))
            before_opens = len(audited_opens(server))
            structured(server, call_tool(server, era, name=name, arguments=arguments), label=name)
            server.drain(0.5)
            calls = facade_calls(server)[before_calls:]
            opens = audited_opens(server)[before_opens:]

            unexpected = sorted(set(calls) - ALLOWED_FACADE_CALLS[name])
            assert not unexpected, server.diagnosis(
                f"{name} reached facade methods it may not: {unexpected} (recorded {calls})"
            )
            adapter_reads = opens_by_layer(opens, "adapter")
            assert not adapter_reads, server.diagnosis(
                f"{name} opened watched files itself instead of delegating: {adapter_reads}"
            )

            if name == REPO_INSPECT:
                assert "inspect_repo" in calls, server.diagnosis(
                    f"{REPO_INSPECT} answered without calling the facade's inspect_repo: {calls}"
                )
                # The control plane opens `.standards/` once and then reads each
                # state file with `os.open(name, dir_fd=...)`, so the individual
                # files reach an audit hook as *relative* names with no resolvable
                # root; the directory open is the absolute, attributable evidence
                # that the authoritative loader touched this repository on this
                # call. The adapter has only the absolute root to work from, so an
                # adapter-side read of a consumer file would be absolute and would
                # still be caught by the negative assertion above.
                control_reads = [
                    path for path in opens_by_layer(opens, "service") if path.startswith(str(repo))
                ]
                assert control_reads, server.diagnosis(
                    "no authoritative read of the consumer repository was recorded, so the "
                    f"snapshot did not come from the repository: {opens!r}"
                )
        assert server.finish() == 0


def test_registered_tools_keep_the_transport_capability_contract(full_runtime: Path) -> None:
    """FR-025/IR-008/DR-007: two more tools change the registry, not the promises.

    T5 asserts an equivalence between declared capabilities and reachable
    registrations rather than an emptiness, so every task that registers
    something reruns it against its own server. Here that means: tools declared
    and reachable, prompts still absent (T8 approves no prompt role either),
    ``listChanged`` still false, ``subscribe`` still absent, and the subscription
    methods still unserved for a registration set ADR 0026 fixes at process
    start.
    """
    require_mcp_subcommand()
    for era in ERAS:
        with resource_session(era, runtime_root=full_runtime, label=f"capability-{era.name}") as (
            server,
            result,
        ):
            capabilities = declared_capabilities(result)
            reachable = assert_capabilities_match_reachable_registrations(
                server, capabilities, envelope=era.envelope
            )
            assert_no_write_surface(server, reachable)
            assert_no_list_change_promises(capabilities)
            require_discovery_tools(server, era)
            assert capabilities.get("prompts") is None, server.diagnosis(
                "T8 approves no prompt role, so the prompts capability must stay absent"
            )
            for method, params in (
                ("resources/subscribe", {"uri": CATALOG_URI}),
                (
                    "subscriptions/listen",
                    {"notifications": {"resourcesListChanged": True}} if era.modern else {},
                ),
            ):
                error = expect_error(server, server.call(method, era.params(params)))
                assert error["code"] == METHOD_NOT_FOUND, server.diagnosis(
                    f"{method} answered {error!r} for a static registration set"
                )
            assert server.finish() == 0
            assert_stdout_is_protocol_only(server)
