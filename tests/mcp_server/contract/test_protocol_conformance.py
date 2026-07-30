"""One complete conformance transcript, and the bounds the whole surface stays inside (T10).

Covers TC-T10-001 (the selected-revision transcript with its capability, error,
and finding contracts) and TC-T10-007 (registry metadata and default text inside
the T1-frozen bounds).

**Why this file exists after T5-T9 already proved most of its parts.** Every
earlier suite proves one task's registrations against the surface that existed
when it was written. None of them walks the *finished* surface end to end in a
single session, and ADR 0026's Confirmation clause is a list of properties about
the finished server — the declared capability set equals the registration set,
``subscribe`` absent, ``listChanged`` false on all three, prompts declared only
when prompt-role resources exist, the server name and instructions pinned, and no
non-protocol output on ``stdout``. T10 is where that list is checked as one list,
against one transcript, with every tool actually called.

**Everything this file pins is spelled here, not imported from the adapter.** The
namespace, the declared-fact set, and the JSON-RPC codes are literals taken from
SPEC-MS01 DR-002 (spec:325), plan:207, and ADR 0026's 2026-07-30 error-taxonomy
amendment. A golden that read its expectation out of the implementation would
pass a rename of the thing it claims to freeze (T10.2 Codex RED review, F4).

**The transcript runs a provider that writes at both levels.** plan:458 requires
"at least one provider fixture [that] writes to Python and file-descriptor
stdout/stderr so the transcript proves worker output cannot contaminate protocol
stdout". ``probe-alpha`` from the T4 hazard tree is exactly that provider, and it
declares a ``validate`` operation with a ``findings`` effect, so ``validate_repo``
reaches it without any new dispatch surface. Worker text may reach a client
through exactly one door — the ``ProviderOperationResult.diagnostics`` slot
plan:458 bounds it to — so the mask applied before the leak scan is the
*positional* T9 one, not a recursive strip: text in a provider-declared
``output.diagnostics`` is contamination, and a recursive mask would hide it
(review F5).

**What this file deliberately does not re-run.** The URI canonicalization matrix
(T6), the root-containment matrix (T8/T9), and the write-audit proofs (T9) are
exhaustive in their owning suites. What the transcript adds is that one refusal of
each *class* still travels the frozen error contract when the whole registry is
live. The inherited T5-T9 coverage this file depends on rather than repeats is
listed in the pipeline notes under "T10 inherited coverage map".

Harness reuse, stated exactly, following the T9 convention: ``test_transport``
owns the subprocess, capability, and stdout machinery; ``test_resources`` owns the
era machinery and the fixture runtime; ``test_standard_read`` owns the tool-call
probes and the client-matrix launch; ``test_discovery_tools`` owns the
structured-result probes, the reviewed discovery metadata, and the frozen finding
schema; ``test_consumer_tools`` owns the reviewed consumer metadata, the
instructions renderer, the positional diagnostics mask, and the provider fixtures;
``tests/mcp_services`` owns the provider tree. The two things added here are the
hazard-carrying runtime (``build_provider_runtime`` in ``test_consumer_tools``
takes no ``hazards`` argument and lives outside T10's file list) and the
faulty-facade launch, because no existing suite can make a handler raise something
that is not a ``ServiceError``.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any, cast

import pytest

from project_standards._version import package_version
from project_standards.control_plane.distribution import InstalledDistribution
from tests.mcp_server.test_consumer_tools import (
    CONSUMER_TOOLS,
    CONTROL_PLANE_SLOT,
    EXPECTED_CONSUMER_TOOL_METADATA,
    FINDING_SCHEMA,
    FROZEN_SIX_TOOL_INSTRUCTIONS,
    INSTRUCTIONS_TOOL_ORDER,
    PREVIEW_SLOT,
    RECONCILE_PREVIEW,
    REQUIRED_ERROR_DATA_FIELDS,
    error_data,
    instructions_for,
    plant_excluded_content,
    without_diagnostics,
)
from tests.mcp_server.test_discovery_tools import (
    EXPECTED_TOOL_METADATA,
    REPO_INSPECT,
    REPO_ROOT_ARGUMENT,
    STANDARDS_LIST,
    assert_conforms,
    structured,
)
from tests.mcp_server.test_resources import (
    CATALOG_URI,
    ERA_IDS,
    ERAS,
    FIXTURE_SUBTREES,
    MODERN_ERA,
    Era,
    declared_resources,
    oracle_facade,
    resource_session,
)
from tests.mcp_server.test_standard_read import (
    FROZEN_CLIENT_MATRIX,
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
    CLI_LAUNCH,
    FROZEN_SERVER_NAME,
    FROZEN_V1_TOOLS,
    RUNTIME_ROOT,
    ServerProcess,
    as_object,
    assert_capabilities_match_reachable_registrations,
    assert_no_list_change_promises,
    assert_no_write_surface,
    assert_stdout_is_protocol_only,
    declared_capabilities,
    expect_error,
    expect_result,
    require_mcp_subcommand,
)
from tests.mcp_services.test_providers import build_provider_repo, build_provider_tree

ADAPTER_PACKAGE = "project_standards.mcp_server"

# The complete v1 registry, in ADR 0026's own enumeration order.
V1_TOOL_ORDER = INSTRUCTIONS_TOOL_ORDER

# -- frozen wire literals ------------------------------------------------------
#
# Spelled, never imported. A golden that reads its expectation out of the module
# under test passes a rename of the very thing it claims to pin (review F4).

#: DR-002's declaration projection travels under this exact `_meta` key. The
#: namespace is implementation-defined, so it must not sit bare and must not
#: claim the spec-reserved `io.modelcontextprotocol/` space.
DECLARATION_META_KEY = "dev.project-standards/declaration"

#: SPEC-MS01 DR-002 (spec:325) and plan:207: "URI, declared resource ID, role,
#: media type, digest, standard ID, and exact package version" — seven facts,
#: the URI included. The T10.1 "six-vs-seven" finding was refuted against this
#: row; the wire matches the spec.
DR002_DECLARED_FACTS = (
    "uri",
    "resource_id",
    "role",
    "media_type",
    "digest",
    "standard_id",
    "package_version",
)

# ADR 0026's 2026-07-30 error-taxonomy amendment, as exact wire codes rather than
# a reserved-range test. Protocol-defined values are spec-anchored, so pinning
# them is not the invented-spelling pattern the T3 F10 precedent bars.
INTERNAL_ERROR = -32603
INVALID_PARAMS = -32602
LEGACY_RESOURCE_NOT_FOUND = -32002

#: DR-003: "Findings shall carry rule ID, severity, standard ID, path, message,
#: and remediation", in the `Finding` DTO's vocabulary, which T3 froze.
DR003_FINDING_FIELDS = ("rule_id", "severity", "standard_id", "path", "message", "remediation")

#: NFR-004's machine-readable half, imported from the T9 suite that first stated
#: it so the two cannot disagree about what "structured" means.
NFR004_ERROR_DATA_FIELDS = REQUIRED_ERROR_DATA_FIELDS

#: The exact key set of a §5.5 `ProviderOperationResult` projection. Used to scope
#: the provider-payload exclusion *structurally* rather than by key name at any
#: depth (review F6): only a real provider result may hide an `output` subtree
#: from the DR-003 walk.
PROVIDER_RESULT_KEYS = frozenset(
    {
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
)
PROVIDER_PAYLOAD_FIELD = "output"

# -- reviewed numeric bounds (NFR-012) -----------------------------------------
#
# NFR-012 authorizes a bound; no contract document names a number, so these are
# reviewed *test* constants with their measurement recorded here and in the
# pipeline notes, flagged for owner visibility at closeout rather than frozen in
# a contract document this session (review F7 amendment).

#: Measured 2026-07-30: the longest advertised title is 52 bytes. A multi-line
#: title fails separately.
MAX_TITLE_BYTES = 80

#: Measured 2026-07-30: the longest reviewed description is `drift_check`'s at
#: 348 bytes. The ceiling admits an honest rewrite and refuses a paragraph.
MAX_DESCRIPTION_BYTES = 640

#: FR-022's "bounded human text where useful". Measured 2026-07-30 across all six
#: tools against the provider fixture: `standard_read` 0, `validate_repo` 39,
#: `standards_list` 43, `repo_inspect` 45, `drift_check` 53, `reconcile_preview`
#: **59** — the maximum. Every summary is one line whose only variable parts are
#: small integer counts, which grow logarithmically, so 160 bytes is ~2.7x the
#: measured maximum and still refuses a second prose copy of the answer.
MAX_DEFAULT_TEXT_BYTES = 160

# The hazard provider plan:458 names: Python-level *and* file-descriptor writes
# on both channels, declaring an approved `validate`/`findings` operation.
TRANSCRIPT_HAZARD = "probe"

#: Every byte `probe-alpha` emits, at both levels and on both channels.
WORKER_SENTINELS = (
    "PROBE-PYTHON-STDOUT",
    "PROBE-FD-STDOUT",
    "PROBE-PYTHON-STDERR",
    "PROBE-FD-STDERR",
    "WORKER-PROBE",
)

# The sentinel a faulty handler raises with, shaped like consumer content so one
# probe covers NFR-004's structure and FR-028's exclusion at once.
FAULT_SENTINEL = "T10-UNMAPPED-HANDLER-CONTENT-9f3a1c"

#: The stable `ServiceError` code ADR 0026's taxonomy amendment ratifies for an
#: unexpected handler failure. Spelled as a literal: requiring only a *non-empty*
#: code let any other string satisfy the class, so the one product change T10 made
#: was not actually pinned to the classification the record assigns it (T10.4
#: Codex GREEN review, F1).
UNEXPECTED_INTERNAL_CODE = "internal-error"

#: The two facade methods that reach the adapter's two handler wrappers. Faulting
#: `resource` puts an unexpected exception inside `_read_resource`; faulting
#: `inspect_repo` puts one inside `_call_tool`. The T10.1 revision reached only
#: the second (review F3).
FAULT_TARGETS = ("resource", "inspect_repo")

COUNT_WORDS = ("No", "One", "Two", "Three", "Four", "Five", "Six")

# The record's own sentence boundaries. ADR 0026's amendment allows a reduced
# rendering to change "the count word and the enumeration" and nothing else, so
# everything before and after this one sentence must be byte-identical in every
# rendering the matrix can produce.
INSTRUCTION_HEAD_MARK = "exactly as the installed catalog declares them. "
INSTRUCTION_TAIL_MARK = " Every repository-scoped tool requires"

# Serves the real adapter over a facade whose named method raises something that
# is *not* a `ServiceError`. Nothing else is replaced: the registry, the mapping,
# and the transport are the production ones, so what the client sees is exactly
# what a genuine adapter bug would produce.
FAULTY_LAUNCH_TEMPLATE = '''
from pathlib import Path

from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.paths import CatalogMajor
from project_standards.mcp_server import transport
from project_standards.mcp_server.models import AdapterConfiguration
from project_standards.mcp_services import McpServiceFacade


class FaultyFacade:
    """The real facade, with one method replaced by an unexpected failure."""

    def __init__(self, inner):
        self._inner = inner

    def __getattr__(self, name):
        if name == "__FAULTY_METHOD__":

            def failing(*_args, **_kwargs):
                raise RuntimeError("__FAULT_SENTINEL__")

            return failing
        return getattr(self._inner, name)


facade = McpServiceFacade.from_installed(
    InstalledDistribution(Path("__PACKAGE_ROOT__"), tool_release="__TOOL_RELEASE__"),
    CatalogMajor("__CATALOG_MAJOR__"),
)
transport.run_stdio(transport.create_server(FaultyFacade(facade), AdapterConfiguration()))
'''

# RED control. A bare SDK server that registers one of each feature family, used
# to prove this module's conformance walk and its ADR 0026 checklist read
# SDK-owned output correctly before they are pointed at the adapter.
BARE_SDK_CONFORMANCE_CONTROL = """
import anyio
import mcp_types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import MCPError
from mcp_types import INVALID_PARAMS

RESOURCE_URI = "standards://catalog/5"


async def _list_resources(ctx, params):
    return types.ListResourcesResult(
        resources=[types.Resource(uri=RESOURCE_URI, name="catalog", mime_type="application/json")]
    )


async def _list_resource_templates(ctx, params):
    return types.ListResourceTemplatesResult(
        resource_templates=[
            types.ResourceTemplate(
                uri_template="standards://{standard_id}/{version}", name="package"
            )
        ]
    )


async def _read_resource(ctx, params):
    if params.uri != RESOURCE_URI:
        raise MCPError(code=INVALID_PARAMS, message="undeclared resource", data={"code": "x"})
    return types.ReadResourceResult(
        contents=[
            types.TextResourceContents(uri=RESOURCE_URI, mime_type="application/json", text="{}")
        ]
    )


async def _list_tools(ctx, params):
    return types.ListToolsResult(
        tools=[
            types.Tool(
                name="standards_list",
                title="control",
                description="control",
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
                output_schema={"type": "object", "properties": {}, "additionalProperties": False},
            )
        ]
    )


async def _call_tool(ctx, params):
    return types.CallToolResult(
        content=[types.TextContent(type="text", text="control")], structured_content={}
    )


server = Server(
    "project-standards",
    version="0",
    instructions="control",
    on_list_resources=_list_resources,
    on_list_resource_templates=_list_resource_templates,
    on_read_resource=_read_resource,
    on_list_tools=_list_tools,
    on_call_tool=_call_tool,
)


async def _serve() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


anyio.run(_serve)
"""


# -- narrowing and rendering ---------------------------------------------------


def as_array(value: object, label: str) -> list[object]:
    """Narrow one decoded JSON value to an array, or fail with a readable label.

    The array counterpart of the T5 harness's ``as_object``. Decoded JSON is
    ``object`` all the way down, so every array has to be narrowed explicitly;
    one helper keeps the failure message useful and the suites free of scattered
    ``cast`` calls.
    """
    assert isinstance(value, list), f"{label} is not a JSON array: {value!r}"
    return cast("list[object]", value)


def wire(value: object) -> str:
    """One rendering that preserves the order the wire carried.

    **Never** ``sort_keys`` and never ``default=str``. ``json.loads`` preserves a
    JSON object's key order into the decoded ``dict``, so re-encoding without
    sorting reproduces exactly the sequence the server emitted — the only
    rendering under which a hash-seed-dependent key order is visible at all. The
    T8 ``rendered()`` helper sorts, which is right for the substring searches it
    was written for and wrong for any determinism or golden comparison (review
    F1). ``default`` is deliberately absent: every value here came off the wire as
    JSON, so a non-serializable object is a defect in the caller rather than
    something to stringify silently.
    """
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def json_leaves(value: object, path: str = "$") -> Iterator[tuple[str, object]]:
    """Every scalar leaf of a decoded JSON document, with its dotted location.

    Keys are visited in sorted order so a caller comparing two *walks* is
    comparing documents rather than key insertion order. Order-sensitive
    comparisons use :func:`wire` instead.
    """
    if isinstance(value, dict):
        for key, item in sorted(cast("dict[str, object]", value).items()):
            yield from json_leaves(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(cast("list[object]", value)):
            yield from json_leaves(item, f"{path}[{index}]")
    else:
        yield path, value


def is_provider_result(mapping: Mapping[str, object]) -> bool:
    """Whether one object is a §5.5 ``ProviderOperationResult`` projection.

    Structural rather than nominal, which is what scopes the payload exclusion in
    :func:`findings_in`: only an object carrying the DTO's exact key set may hide
    an ``output`` subtree from the DR-003 walk, so a document that merely happens
    to have a field named ``output`` is still walked (review F6).
    """
    return set(mapping) == set(PROVIDER_RESULT_KEYS)


def findings_in(document: object, path: str = "$") -> list[tuple[str, object]]:
    """Every element of every ``findings`` array, located, and **unfiltered**.

    Elements are returned as found, malformed ones included, because silently
    discarding a non-object entry is how a walker comes to certify a document it
    never examined (review F6). The caller asserts objecthood.

    The one subtree the walk refuses to enter is the ``output`` of a *structurally
    identified* provider result: ``ProviderOperationResult.output`` is the
    provider's own declared payload, which DR-008 requires the result to preserve
    verbatim, so it speaks the provider's schema rather than the service layer's
    and DR-003 has no authority over it.
    """
    found: list[tuple[str, object]] = []
    if isinstance(document, dict):
        mapping = cast("dict[str, object]", document)
        raw = mapping.get("findings")
        if isinstance(raw, list):
            found += [
                (f"{path}.findings[{index}]", item)
                for index, item in enumerate(cast("list[object]", raw))
            ]
        skip = PROVIDER_PAYLOAD_FIELD if is_provider_result(mapping) else None
        for key, item in mapping.items():
            if key == "findings" or key == skip:
                continue
            found += findings_in(item, f"{path}.{key}")
    elif isinstance(document, list):
        for index, item in enumerate(cast("list[object]", document)):
            found += findings_in(item, f"{path}[{index}]")
    return found


def masked_documents(documents: Mapping[str, Any]) -> dict[str, Any]:
    """Every document with the DTO's own ``diagnostics`` slot masked, and nothing else.

    ``without_diagnostics`` is T9's *positional* mask — the top-level
    ``diagnostics`` of each entry in a ``results`` array — and it is the correct
    one here for the reason the T9 F3 arbitration gave in the other direction:
    plan:458 bounds worker output to that one slot, so worker text appearing in a
    provider-declared ``output.diagnostics`` **is** contamination, and a recursive
    strip would hide exactly the defect this scan exists to find (review F5).
    """
    return {
        name: without_diagnostics(as_object(document, name)) for name, document in documents.items()
    }


def faulty_launch(package_root: Path, method: str) -> str:
    """A launch script whose facade raises an unmapped exception from ``method``."""
    return (
        FAULTY_LAUNCH_TEMPLATE.replace("__FAULTY_METHOD__", method)
        .replace("__FAULT_SENTINEL__", FAULT_SENTINEL)
        .replace("__PACKAGE_ROOT__", str(package_root))
        .replace("__TOOL_RELEASE__", package_version())
        .replace("__CATALOG_MAJOR__", "5")
    )


def call_arguments(repo: Path, *, read_uri: str = CATALOG_URI) -> dict[str, dict[str, Any]]:
    """One valid argument mapping per registered v1 tool.

    The single producer for all three T10 contract suites. ``read_uri`` is the only
    thing that ever differed between them: the determinism goldens address a
    *payload* resource so ``standard_read``'s declaration slot is non-null, while
    the transcript and the recommendation scan address the catalog. Everything else
    — the empty ``standards_list`` call and the four ``repo_root`` tools — was
    identical text in three files (T10.5).
    """
    return {
        STANDARDS_LIST: {},
        STANDARD_READ: {"uri": read_uri},
        REPO_INSPECT: {REPO_ROOT_ARGUMENT: str(repo)},
        **{name: {REPO_ROOT_ARGUMENT: str(repo)} for name in CONSUMER_TOOLS},
    }


def planned_consumer_repo(runtime: Path, parent: Path) -> Path:
    """One initialized consumer repository over ``runtime``, carrying FR-028's classes.

    The three-line distribution/repo/plant sequence was written out in three
    fixtures that differed only in their temporary directory. It is one sequence
    with one meaning — "a repository this distribution can plan, seeded with the
    four exclusion classes" — so it has one producer (T10.5).
    """
    distribution = InstalledDistribution(
        runtime / "project_standards", tool_release=package_version()
    )
    repo = build_provider_repo(parent, "planned", distribution=distribution)
    plant_excluded_content(repo)
    return repo


def server_identity(result: Mapping[str, Any]) -> dict[str, Any]:
    """The server's name and version, from whichever slot this era carries them.

    ``initialize`` answers with a top-level ``serverInfo``; 2026-07-28 moved it into
    the spec-reserved ``_meta`` namespace. Two call sites did the same branch
    inline (T10.5).
    """
    info = result.get("serverInfo")
    if info is None:
        meta = as_object(result.get("_meta"), "the discovery _meta envelope")
        info = meta.get("io.modelcontextprotocol/serverInfo")
    return as_object(info, "the server identity")


def assert_protocol_only_stdout(server: ServerProcess) -> list[dict[str, Any]]:
    """NFR-003/IR-006/DR-007: every stdout byte is a response, and none is a notification.

    A stricter form of the T5 helper, which this calls first. The addition is
    DR-007's other half: ``listChanged: false`` is only half of "no change
    notification is promised" — the server must also never *send* one, and a
    notification is a frame carrying a ``method`` and no answered id. Nothing in
    ADR 0026's registry can change during a process lifetime, so this is a
    permanent negative rather than a phase one (review F11).
    """
    frames = assert_stdout_is_protocol_only(server)
    notifications = [frame for frame in frames if "method" in frame]
    assert not notifications, server.diagnosis(
        f"the server sent {len(notifications)} notification(s) while declaring listChanged false "
        f"on every capability: {notifications}"
    )
    return frames


def _boolean_assignments(width: int) -> list[tuple[bool, ...]]:
    """Every boolean tuple of the given width, in a stable order."""
    return [
        tuple(bool(index >> position & 1) for position in range(width)) for index in range(2**width)
    ]


def _instruction_parts(rendering: str) -> tuple[str, str, str]:
    """Split one rendering into (before, enumeration sentence, after)."""
    head, head_mark, rest = rendering.partition(INSTRUCTION_HEAD_MARK)
    assert head_mark, f"the rendering no longer carries the record's URI sentence: {rendering!r}"
    sentence, tail_mark, tail = rest.partition(INSTRUCTION_TAIL_MARK)
    assert tail_mark, (
        f"the rendering no longer carries the record's repo_root sentence: {rendering!r}"
    )
    return head, sentence, tail


# -- fixtures ------------------------------------------------------------------


def build_hazard_runtime(destination: Path, hazards: tuple[str, ...]) -> Path:
    """An importable runtime whose alpha 2.0 declares runnable *and* hazard providers.

    The same composition ``test_consumer_tools.build_provider_runtime`` performs,
    with the one difference T10 needs: ``hazards`` reaches ``build_provider_tree``.
    That helper's own signature already takes them; the T9 wrapper does not pass
    them, and ``test_consumer_tools.py`` is outside T10's declared file list, so
    the wrapper is composed again here rather than widened there.
    """
    staging = destination / "staging"
    installed = build_provider_tree(staging, hazards=hazards)
    runtime = destination / "runtime"
    package = runtime / "project_standards"
    package.mkdir(parents=True)
    for entry in sorted((RUNTIME_ROOT / "project_standards").iterdir()):
        if entry.name in FIXTURE_SUBTREES or entry.name == "__pycache__":
            continue
        (package / entry.name).symlink_to(entry)
    for name in FIXTURE_SUBTREES:
        shutil.copytree(installed / name, package / name)
    shutil.rmtree(installed.parent)
    return runtime


@pytest.fixture(scope="module")
def transcript_runtime(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The fixture catalog whose ``validate`` set includes the two-level noisy provider."""
    return build_hazard_runtime(tmp_path_factory.mktemp("conformance"), (TRANSCRIPT_HAZARD,))


@pytest.fixture(scope="module")
def transcript_repo(transcript_runtime: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One planned consumer repository, carrying FR-028's four exclusion classes."""
    return planned_consumer_repo(transcript_runtime, tmp_path_factory.mktemp("conformance-repo"))


# -- shared assertions ---------------------------------------------------------


def assert_adr_0026_capability_clause(
    server: ServerProcess, result: Mapping[str, Any], era: Era, *, runtime: Path
) -> dict[str, list[Any]]:
    """ADR 0026's Confirmation clause, checked as one list against one session.

    1. the declared capability set equals the registration set (both directions);
    2. ``subscribe`` absent and ``listChanged`` false on all three;
    3. prompts declared only when prompt-role resources exist — and no installed
       distribution declares one, so the capability must be absent;
    4. the server name is ``project-standards`` and the version is the installed
       distribution's;
    5. the instructions string is the record's rendering for this registry;
    6. no advertised tool sits outside the frozen read-only six.
    """
    capabilities = declared_capabilities(result)
    reachable = assert_capabilities_match_reachable_registrations(
        server, capabilities, envelope=era.envelope
    )
    assert_no_list_change_promises(capabilities)
    assert_no_write_surface(server, reachable)

    facade = oracle_facade(runtime)
    catalog = facade.catalog()
    roles = {resource.role for descriptor in catalog.standards for resource in descriptor.resources}
    assert roles, "the fixture catalog declares no resource role, so clause 3 would hold vacuously"
    assert capabilities.get("prompts") is None, server.diagnosis(
        "ADR 0026 declares prompts only from approved prompt-role resources, and this "
        f"distribution's {len(roles)} declared roles include none: {capabilities.get('prompts')!r}"
    )

    identity = server_identity(result)
    assert identity.get("name") == FROZEN_SERVER_NAME, server.diagnosis(
        f"ADR 0026 freezes the server name as {FROZEN_SERVER_NAME!r}: {identity!r}"
    )
    assert identity.get("version") == package_version(), server.diagnosis(
        f"the server must report the installed distribution's version: {identity!r}"
    )

    advertised = sorted(tool_names(list_tools(server, era)))
    assert set(advertised) <= set(FROZEN_V1_TOOLS), server.diagnosis(
        f"tools outside ADR 0026's closed v1 registry are advertised: {advertised}"
    )
    served = result.get("instructions")
    assert served == instructions_for(advertised), server.diagnosis(
        f"the served instructions are not ADR 0026's rendering for this registry.\n"
        f"served:   {served!r}\nexpected: {instructions_for(advertised)!r}"
    )
    return reachable


def assert_findings_conform(server: ServerProcess, documents: Mapping[str, Any]) -> int:
    """DR-003 over every typed finding a session produced, values included.

    Three obligations, and the first two are what the T10.1 revision omitted
    (review F6): every element of a ``findings`` array must be an *object* — a
    string or a null there is a malformed result, not something to skip — and
    every finding must validate against the frozen ``Finding`` schema, so a
    present-but-empty ``rule_id`` or a numeric ``severity`` fails. Only then is
    the named-field presence check meaningful.
    """
    located = [entry for document in documents.values() for entry in findings_in(document)]
    assert located, server.diagnosis(
        "the transcript produced no finding, so DR-003 would hold vacuously"
    )
    malformed = [(where, item) for where, item in located if not isinstance(item, dict)]
    assert not malformed, server.diagnosis(
        f"a findings array carries {len(malformed)} non-object element(s), which no consumer of "
        f"DR-003 can read: {malformed[:3]}"
    )
    for where, item in located:
        finding = cast("dict[str, Any]", item)
        missing = [field for field in DR003_FINDING_FIELDS if field not in finding]
        assert not missing, server.diagnosis(
            f"DR-003 requires every finding to carry {list(DR003_FINDING_FIELDS)}; {missing} are "
            f"absent from {where}: {finding!r}"
        )
        empty = [field for field in DR003_FINDING_FIELDS if finding.get(field) in (None, "")]
        assert not empty, server.diagnosis(
            f"DR-003's fields {empty} are present but carry no value at {where}: {finding!r}"
        )
        assert_conforms(server, finding, FINDING_SCHEMA, label=f"the finding at {where}")
    return len(located)


# -- RED controls --------------------------------------------------------------


def test_conformance_walk_probe_observes_a_complete_session() -> None:
    """RED control: the transcript walk and its helpers are valid.

    Deliberately green. It drives this module's session machinery, its result
    narrowing, its leaf walker, and the order-preserving renderer against a bare
    SDK server that registers one of each feature family and refuses an undeclared
    URI, so a failure anywhere else in this file is provably a property of the
    adapter rather than an invalid probe. The renderer is exercised against a
    **reversed dictionary**, which is the exact variance the T10.1 comparison
    erased (review F1).
    """
    era = MODERN_ERA
    with ServerProcess(BARE_SDK_CONFORMANCE_CONTROL, label="conformance-control") as server:
        opened = era.open(server)
        capabilities = declared_capabilities(opened)
        assert set(capabilities) >= {"resources", "tools"}, (
            f"the control must declare the families it registered: {capabilities!r}"
        )
        assert_no_list_change_promises(capabilities)

        listing = expect_result(server, server.call("resources/list", era.params()))
        assert len(as_array(listing.get("resources"), "the control listing")) == 1, listing

        contents = expect_result(
            server, server.call("resources/read", era.params({"uri": CATALOG_URI}))
        )
        assert as_array(contents.get("contents"), "the control read"), contents

        answered = expect_result(
            server, server.call("tools/call", era.params({"name": STANDARDS_LIST, "arguments": {}}))
        )
        assert answered.get("structuredContent") == {}, answered

        refused = expect_error(
            server, server.call("resources/read", era.params({"uri": "standards://nope"}))
        )
        assert refused.get("code") == INVALID_PARAMS, refused

        assert dict(json_leaves({"a": [{"b": 1}], "c": "x"})) == {"$.a[0].b": 1, "$.c": "x"}, (
            "the leaf walker is wrong"
        )
        assert wire({"b": 1, "a": 2}) == '{"b":1,"a":2}', "the renderer sorts keys"
        assert wire({"b": 1, "a": 2}) != wire({"a": 2, "b": 1}), (
            "the renderer cannot see a reversed dictionary, so no determinism claim built on it "
            "would mean anything"
        )

        assert server.finish() == 0, "the control server did not exit cleanly"
        assert_protocol_only_stdout(server)


def test_finding_and_contamination_walkers_reject_planted_defects() -> None:
    """RED control: the DR-003 walker and the contamination mask are not vacuous.

    Deliberately green, and deliberately negative. Four plants, one per way the
    T10.1 revision's helpers could have certified a defect (review F5/F6):

    * a **nested leak** — a worker sentinel inside a provider result's
      ``output.diagnostics``, which the positional mask must leave visible;
    * a **malformed finding** — a string and a null where objects belong;
    * a **misplaced ``output``** — a subtree named ``output`` on an object that is
      *not* a provider result, whose findings must still be walked;
    * a **real provider payload** — whose findings must not be walked.
    """
    provider_result: dict[str, Any] = {
        "standard_id": "alpha",
        "version": "2.0",
        "provider_id": "probe-alpha",
        "operation": "validate",
        "phase": "validate",
        "effect": "findings",
        "status": "completed",
        "findings": [],
        "diagnostics": "stdout: PROBE-FD-STDOUT\n",
        "output": {"diagnostics": "PROBE-PYTHON-STDOUT", "findings": [{"code": "X"}], "checked": 1},
    }
    document = {"repo_root": ".", "results": [provider_result], "findings": []}
    masked = masked_documents({"validate_repo": document})
    body = wire(masked["validate_repo"])
    assert "PROBE-FD-STDOUT" not in body, (
        "the positional mask did not clear the DTO's own diagnostics slot"
    )
    assert "PROBE-PYTHON-STDOUT" in body, (
        "the mask erased a provider-declared output.diagnostics, so a nested leak would pass "
        "unnoticed — the defect the T9 F3 arbitration names in the other direction"
    )

    assert is_provider_result(provider_result), "the provider-result shape check is wrong"
    assert not is_provider_result({"output": {}, "findings": []}), (
        "a document that merely has an `output` field must not be treated as a provider result"
    )
    walked = findings_in({"output": {"findings": [{"rule_id": "R"}]}})
    assert [where for where, _ in walked] == ["$.output.findings[0]"], (
        f"a misplaced `output` subtree was skipped: {walked}"
    )
    hidden = findings_in(provider_result)
    assert all("output" not in where for where, _ in hidden), (
        f"the provider payload was walked, so the provider's own vocabulary would be judged "
        f"against the DTO's: {hidden}"
    )

    malformed = findings_in({"findings": ["not an object", None, {"rule_id": "R"}]})
    assert len(malformed) == 3, (
        f"the walker discarded malformed elements instead of returning them: {malformed}"
    )
    assert [isinstance(item, dict) for _, item in malformed] == [False, False, True], (
        "the walker no longer returns elements as found"
    )


def test_frozen_wire_literals_still_describe_the_installed_sdk() -> None:
    """Guard the guard: the spelled JSON-RPC codes must still be the SDK's own.

    The codes are spelled rather than imported so an SDK renumbering fails the
    goldens instead of silently moving them. That is only safe if a renumbering is
    also *diagnosable*, so the correspondence is stated once, here, with a message
    naming which side moved. ``-32002`` is deliberately absent: the 2026-07-28
    allocation policy lists it as reserved-never-reused, so ``mcp_types`` cannot
    export it and a legacy connection is the only place it may legally appear.
    """
    import mcp_types

    assert mcp_types.INTERNAL_ERROR == INTERNAL_ERROR, (
        f"the SDK renumbered INTERNAL_ERROR to {mcp_types.INTERNAL_ERROR}; ADR 0026's taxonomy "
        f"amendment freezes {INTERNAL_ERROR}"
    )
    assert mcp_types.INVALID_PARAMS == INVALID_PARAMS, (
        f"the SDK renumbered INVALID_PARAMS to {mcp_types.INVALID_PARAMS}; ADR 0026's taxonomy "
        f"amendment freezes {INVALID_PARAMS}"
    )


# -- acceptance ----------------------------------------------------------------


@pytest.mark.parametrize("era", ERAS, ids=ERA_IDS)
def test_selected_revision_transcript_capabilities_errors_and_findings_conform(
    transcript_runtime: Path, transcript_repo: Path, era: Era
) -> None:
    """TC-T10-001 (FR-025, FR-029, NFR-003, NFR-004, NFR-011, IR-008, DR-003, DR-007).

    One session, the whole finished surface, per protocol era:

    * the opening contract and ADR 0026's complete Confirmation clause;
    * every resource form — concrete listing, both templates, one read;
    * every registered tool called with a valid argument, including the two that
      dispatch providers;
    * one refusal of each class the adapter owns, each carrying NFR-004's fields
      in ``error.data`` under the **exact** wire code ADR 0026's taxonomy
      amendment assigns it for this revision;
    * DR-003's six fields, present, populated, and schema-valid, on every typed
      finding the session produced;
    * a clean shutdown with protocol-only stdout and no notification at all.

    ``validate_repo`` runs ``probe-alpha``, which writes to Python-level *and*
    file-descriptor stdout and stderr. Contamination has two shapes and both are
    checked over the whole transcript: raw bytes on the wire fail
    :func:`assert_protocol_only_stdout`, which requires every stdout line to be a
    well-formed response answering a sent id; and worker text in a field that did
    not declare it fails the leak scan, which masks **only** the DTO's own
    ``diagnostics`` slot, so a sentinel in a provider-declared
    ``output.diagnostics`` is caught rather than hidden.
    """
    require_mcp_subcommand()
    with resource_session(
        era, runtime_root=transcript_runtime, label="conformance", script=CLI_LAUNCH
    ) as (server, opened):
        assert_adr_0026_capability_clause(server, opened, era, runtime=transcript_runtime)

        templates = as_array(
            expect_result(server, server.call("resources/templates/list", era.params())).get(
                "resourceTemplates"
            ),
            "the resource-template listing",
        )
        assert templates, server.diagnosis(
            f"ADR 0026's two parameterized forms must be advertised: {templates!r}"
        )

        catalog = oracle_facade(transcript_runtime).catalog()
        declared = declared_resources(catalog)
        assert declared, "the fixture catalog declares no payload resource to read"
        read = expect_result(
            server, server.call("resources/read", era.params({"uri": next(iter(declared))}))
        )
        assert as_array(read.get("contents"), "a declared resource read"), server.diagnosis(
            f"a declared resource read returned no contents: {read!r}"
        )

        advertised = tool_names(list_tools(server, era))
        arguments = call_arguments(transcript_repo)
        documents: dict[str, Any] = {}
        for name in advertised:
            assert name in arguments, server.diagnosis(
                f"the transcript has no valid argument for advertised tool {name!r}"
            )
            frame = call_tool(server, era, name=name, arguments=arguments[name])
            documents[name] = structured(server, frame, label=name)
        assert set(documents) == set(advertised), "every advertised tool must be called"
        envelope = as_object(documents.get(RECONCILE_PREVIEW), RECONCILE_PREVIEW)
        assert set(envelope) == {PREVIEW_SLOT, CONTROL_PLANE_SLOT}, server.diagnosis(
            f"the §5.5 preview envelope is not closed: {sorted(envelope)}"
        )

        assert_findings_conform(server, documents)

        not_found_code = INVALID_PARAMS if era.modern else LEGACY_RESOURCE_NOT_FOUND
        refusals: dict[str, tuple[Mapping[str, Any], int]] = {
            "unknown tool": (
                call_tool(server, era, name="standards_resolve", arguments={}),
                INVALID_PARAMS,
            ),
            "undeclared argument": (
                call_tool(server, era, name=STANDARDS_LIST, arguments={"standard_id": "alpha"}),
                INVALID_PARAMS,
            ),
            "non-canonical uri": (
                server.call("resources/read", era.params({"uri": "standards://catalog/5/"})),
                INVALID_PARAMS,
            ),
            "undeclared uri": (
                server.call("resources/read", era.params({"uri": "standards://absent/9.9"})),
                not_found_code,
            ),
            "refused root": (
                call_tool(
                    server, era, name=REPO_INSPECT, arguments={REPO_ROOT_ARGUMENT: "relative/path"}
                ),
                INVALID_PARAMS,
            ),
        }
        for label, (frame, expected_code) in refusals.items():
            refusal = expect_error(server, frame)
            data = error_data(server, refusal, label=label)
            absent = [field for field in NFR004_ERROR_DATA_FIELDS if not data.get(field)]
            assert not absent, server.diagnosis(
                f"the {label} refusal is missing NFR-004 fields {absent}: {refusal!r}"
            )
            assert refusal.get("code") == expected_code, server.diagnosis(
                f"ADR 0026's taxonomy assigns the {label} class {expected_code} under "
                f"{era.revision}; the server answered {refusal.get('code')!r}"
            )

        assert server.finish() == 0, server.diagnosis("the server did not shut down cleanly")
        frames = assert_protocol_only_stdout(server)
        assert len(frames) == len(server.sent_ids), server.diagnosis(
            f"the transcript answered {len(frames)} of {len(server.sent_ids)} requests"
        )

        whole = wire(frames)
        carried = [sentinel for sentinel in WORKER_SENTINELS if sentinel in whole]
        assert carried, server.diagnosis(
            "no worker sentinel appears anywhere in the transcript, so the noisy provider never "
            "ran and the contamination proof would be vacuous"
        )
        scrubbed = wire(masked_documents(documents))
        leaked = [sentinel for sentinel in WORKER_SENTINELS if sentinel in scrubbed]
        assert not leaked, server.diagnosis(
            "provider worker output reached a field that is not the DTO's bounded diagnostics "
            f"slot: {leaked}"
        )


@pytest.mark.parametrize("era", ERAS, ids=ERA_IDS)
@pytest.mark.parametrize("faulted", FAULT_TARGETS)
def test_unexpected_handler_failures_stay_structured_in_both_eras(
    transcript_runtime: Path, transcript_repo: Path, era: Era, faulted: str
) -> None:
    """NFR-004/FR-028 and ADR 0026's taxonomy amendment, on both handler wrappers.

    NFR-004 is unconditional — "All tool/resource failures shall be structured" —
    and the adapter maps only ``ServiceError``. Anything else a handler raises
    reaches the SDK's generic path, which the amendment forbids serving:
    2026-07-28 answers ``-32603`` with no ``data``, and 2025-06-18 answers
    ``code: 0`` carrying the **raw exception text**, which is also FR-028's
    exclusion.

    Both wrappers are faulted, because they are two independent code paths and the
    first revision of this test reached only ``_call_tool`` (review F3): faulting
    ``McpServiceFacade.resource`` puts an unexpected exception inside
    ``_read_resource``, and faulting ``inspect_repo`` puts one inside
    ``_call_tool``.

    The same server then answers a not-found and an invalid-parameter refusal, so
    the amendment's other two classes are pinned at their **exact** codes on the
    same connection — a reserved-range test would have accepted the SDK's generic
    body.

    The fault is injected at the facade, so every line of registration, dispatch,
    and mapping under test is the production one.
    """
    require_mcp_subcommand()
    script = faulty_launch(transcript_runtime / "project_standards", faulted)
    catalog = oracle_facade(transcript_runtime).catalog()
    payload_uri = next(iter(declared_resources(catalog)))
    with resource_session(
        era, runtime_root=transcript_runtime, label=f"unmapped-{faulted}", script=script
    ) as (server, _opened):
        if faulted == "resource":
            frame = server.call("resources/read", era.params({"uri": payload_uri}))
        else:
            frame = call_tool(
                server,
                era,
                name=REPO_INSPECT,
                arguments={REPO_ROOT_ARGUMENT: str(transcript_repo)},
            )
        refusal = expect_error(server, frame)
        assert refusal.get("code") == INTERNAL_ERROR, server.diagnosis(
            f"ADR 0026 maps an unexpected handler failure to {INTERNAL_ERROR} in both eras; the "
            f"server answered {refusal.get('code')!r} for a fault in {faulted!r}"
        )
        assert FAULT_SENTINEL not in wire(refusal), server.diagnosis(
            "the raw exception text reached the client, so an unmapped failure publishes whatever "
            f"the exception happened to carry: {refusal!r}"
        )
        data = error_data(server, refusal, label=f"unmapped {faulted} failure")
        absent = [field for field in NFR004_ERROR_DATA_FIELDS if not data.get(field)]
        assert not absent, server.diagnosis(
            f"an unmapped handler failure carries none of NFR-004's fields {absent}: {refusal!r}"
        )
        assert data.get("code") == UNEXPECTED_INTERNAL_CODE, server.diagnosis(
            f"ADR 0026's taxonomy amendment classifies an unexpected handler failure as "
            f"{UNEXPECTED_INTERNAL_CODE!r}; the server published {data.get('code')!r} for a fault "
            f"in {faulted!r}. A merely non-empty code would let any classification pass."
        )

        not_found = expect_error(
            server, server.call("resources/read", era.params({"uri": "standards://absent/9.9"}))
        )
        expected_not_found = INVALID_PARAMS if era.modern else LEGACY_RESOURCE_NOT_FOUND
        assert not_found.get("code") == expected_not_found, server.diagnosis(
            f"ADR 0026 maps the not-found class to {expected_not_found} under {era.revision}; the "
            f"server answered {not_found.get('code')!r}"
        )
        invalid = expect_error(
            server, server.call("resources/read", era.params({"uri": "standards://catalog/5/"}))
        )
        assert invalid.get("code") == INVALID_PARAMS, server.diagnosis(
            f"ADR 0026 maps a non-canonical URI to {INVALID_PARAMS} under every revision; the "
            f"server answered {invalid.get('code')!r}"
        )

        assert server.finish() == 0, server.diagnosis("the server did not survive the failure")
        frames = assert_protocol_only_stdout(server)
        assert FAULT_SENTINEL not in wire(frames), server.diagnosis(
            "the exception text reached stdout"
        )
        # The operator half of the contract, and the half a purely negative test
        # cannot state: the exception is kept off the wire *and* delivered to
        # stderr. Without this, deleting the adapter's `logger.exception` call
        # would leave the suite green while the traceback vanished entirely
        # (review F4).
        diagnostics = bytes(server.stderr_bytes).decode("utf-8", "replace")
        assert FAULT_SENTINEL in diagnostics, server.diagnosis(
            "the exception never reached stderr, so the failure the client was told to report is "
            f"unrecoverable for the operator who could act on it (fault in {faulted!r})"
        )


def test_registry_metadata_and_default_text_stay_within_frozen_bounds(
    transcript_runtime: Path, transcript_repo: Path
) -> None:
    """TC-T10-007 (NFR-012): the advertised surface stays inside its reviewed bounds.

    Four bounds, and one exhaustive enumeration.

    *The reviewed metadata itself.* The served tool surface must equal the reviewed
    constants T8 and T9 own, imported rather than copied so the two cannot drift.

    *Compactness.* Every title and description is one line inside a byte ceiling.

    *Bounded default text, actually exercised.* Every advertised tool is **called**
    and its human text held to :data:`MAX_DEFAULT_TEXT_BYTES` on one line — the
    T10.1 revision declared that ceiling and never invoked a tool (review F7).

    *Every rendering the matrix can produce.* ADR 0026's 2026-07-30 amendment binds
    the frozen text per session registry. This enumerates the complete boolean
    assignment space over ``CLIENT_DIRECT_RESOURCE_ACCESS``'s keys and launches
    **one server per assignment**, not one per resulting registry: that equal
    registries yield equal renderings is the property to prove, not the assumption
    to select on. The bound on what may differ is structural — each rendering is
    split on the record's own surrounding sentences, head and tail must be
    byte-identical to the frozen text's, and the middle must be the count word and
    enumeration for that registry.
    """
    require_mcp_subcommand()
    era = MODERN_ERA
    expected_metadata = {**EXPECTED_TOOL_METADATA, **EXPECTED_CONSUMER_TOOL_METADATA}
    assert set(expected_metadata) == set(FROZEN_V1_TOOLS), (
        "the reviewed metadata constants no longer cover ADR 0026's whole v1 registry: "
        f"{sorted(expected_metadata)}"
    )
    assert instructions_for(sorted(V1_TOOL_ORDER)) == FROZEN_SIX_TOOL_INSTRUCTIONS, (
        "the rendering generator no longer reproduces ADR 0026's own text, so the reduced "
        "renderings derived from it cannot be trusted either"
    )
    frozen_head, _frozen_sentence, frozen_tail = _instruction_parts(FROZEN_SIX_TOOL_INSTRUCTIONS)

    package_root = transcript_runtime / "project_standards"
    module = require_tools_module()
    evidence = client_matrix_evidence(module)
    assert evidence == FROZEN_CLIENT_MATRIX, (
        "the client matrix is no longer the frozen T1 evidence; refresh T1 rather than this test"
    )

    keys = sorted(evidence)
    assignments = [dict(zip(keys, bits, strict=True)) for bits in _boolean_assignments(len(keys))]
    assert len(assignments) == 2 ** len(keys), "the assignment enumeration is incomplete"
    arguments = call_arguments(transcript_repo)
    renderings: dict[frozenset[str], list[tuple[str, str]]] = {}

    for assignment in assignments:
        registry = frozenset(FROZEN_V1_TOOLS) - (
            {STANDARD_READ} if all(assignment.values()) else set()
        )
        label = "-".join(f"{name}={int(flag)}" for name, flag in sorted(assignment.items()))
        with resource_session(
            era,
            runtime_root=transcript_runtime,
            label=f"bounds-{label}",
            script=matrix_launch(package_root, assignment),
        ) as (server, opened):
            entries = {str(entry["name"]): entry for entry in list_tools(server, era)}
            assert set(entries) == set(registry), server.diagnosis(
                f"matrix {assignment} must register {sorted(registry)}; advertised "
                f"{sorted(entries)}"
            )
            for name, entry in sorted(entries.items()):
                # The whole advertised entry, `name` included: the reviewed
                # constants carry it, so comparing a projection would let a
                # renamed tool keep a reviewed body.
                assert dict(entry) == expected_metadata[name], server.diagnosis(
                    f"{name}'s advertised metadata is not the reviewed snapshot.\n"
                    f"served:   {json.dumps(dict(entry), indent=2, sort_keys=True)}\n"
                    f"reviewed: {json.dumps(expected_metadata[name], indent=2, sort_keys=True)}"
                )
                title = str(entry.get("title"))
                description = str(entry.get("description"))
                assert "\n" not in title and "\n" not in description, server.diagnosis(
                    f"{name}'s metadata is multi-line, which no client renders compactly"
                )
                assert len(title.encode()) <= MAX_TITLE_BYTES, server.diagnosis(
                    f"{name}'s title is {len(title.encode())} bytes, over {MAX_TITLE_BYTES}"
                )
                assert len(description.encode()) <= MAX_DESCRIPTION_BYTES, server.diagnosis(
                    f"{name}'s description is {len(description.encode())} bytes, over "
                    f"{MAX_DESCRIPTION_BYTES}"
                )

            for name in sorted(entries):
                result = expect_result(
                    server, call_tool(server, era, name=name, arguments=arguments[name])
                )
                blocks = as_array(result.get("content"), f"the {name} content array")
                texts = [
                    str(cast("dict[str, object]", block).get("text", ""))
                    for block in blocks
                    if isinstance(block, dict)
                    and cast("dict[str, object]", block).get("type") == "text"
                ]
                assert len(texts) <= 1, server.diagnosis(
                    f"{name} returned {len(texts)} text blocks; FR-022 asks for one bounded summary"
                )
                text = texts[0] if texts else ""
                assert "\n" not in text.strip(), server.diagnosis(
                    f"{name}'s default text is multi-line: {text!r}"
                )
                assert len(text.encode()) <= MAX_DEFAULT_TEXT_BYTES, server.diagnosis(
                    f"{name}'s default text is {len(text.encode())} bytes, over the reviewed "
                    f"{MAX_DEFAULT_TEXT_BYTES}: {text!r}"
                )

            served_instructions = str(opened.get("instructions"))
            head, sentence, tail = _instruction_parts(served_instructions)
            assert (head, tail) == (frozen_head, frozen_tail), server.diagnosis(
                "the rendering changed text outside the enumeration sentence, which ADR 0026's "
                f"amendment does not allow:\n{served_instructions!r}"
            )
            names = [name for name in V1_TOOL_ORDER if name in registry]
            expected_sentence = (
                f"{COUNT_WORDS[len(names)]} tools are available: "
                f"{', '.join(names[:-1])}, and {names[-1]}."
            )
            assert sentence == expected_sentence, server.diagnosis(
                f"the enumeration sentence is not the record's, reduced to this registry.\n"
                f"served:   {sentence!r}\nexpected: {expected_sentence!r}"
            )
            renderings.setdefault(registry, []).append((label, served_instructions))

            assert server.finish() == 0
            assert_protocol_only_stdout(server)

    assert len(renderings) == 2, (
        f"the matrix must be able to produce two distinct registries; got {len(renderings)}"
    )
    for registry, observed in sorted(renderings.items(), key=lambda item: -len(item[0])):
        distinct = {rendering for _label, rendering in observed}
        assert len(distinct) == 1, (
            f"assignments yielding the same registry {sorted(registry)} served different "
            f"instructions, so the rendering depends on the assignment rather than on the "
            f"registry: {observed}"
        )


def test_declaration_metadata_and_embedded_carrier_are_a_stable_wire_contract(
    transcript_runtime: Path,
) -> None:
    """DR-002/FR-008: the ``_meta`` namespace and the embedded carrier are compatibility.

    Everything asserted here is a **literal** taken from SPEC-MS01 DR-002
    (spec:325) and plan:207 — the key ``dev.project-standards/declaration`` and the
    seven declared facts including the URI. The T10.1 revision read both out of the
    implementation, so renaming the key or reshaping the DTO and the wire together
    would have passed (review F4).

    Three properties:

    * the key is exactly the namespaced literal, and not under the spec-reserved
      ``io.modelcontextprotocol/`` space;
    * its value carries exactly DR-002's seven facts, each equal to the oracle
      facade's own declared value;
    * ``standard_read``'s embedded carrier is byte-identical to the object
      ``resources/read`` produces for the same URI — FR-008's "same
      descriptor/bytes mapping", ``_meta`` included.
    """
    require_mcp_subcommand()
    era = MODERN_ERA
    assert not DECLARATION_META_KEY.startswith("io.modelcontextprotocol/"), (
        "the io.modelcontextprotocol/ namespace is reserved for spec-defined keys"
    )
    assert "/" in DECLARATION_META_KEY, "an implementation-defined _meta key must be namespaced"

    facade = oracle_facade(transcript_runtime)
    catalog = facade.catalog()
    descriptor = next(
        resource
        for standard in catalog.standards
        for resource in standard.resources
        if resource.media_type.startswith("text/")
    )
    expected_declaration = {
        "uri": descriptor.uri,
        "resource_id": descriptor.resource_id,
        "role": descriptor.role,
        "media_type": descriptor.media_type,
        "digest": descriptor.digest,
        "standard_id": descriptor.standard_id,
        "package_version": descriptor.package_version,
    }
    assert tuple(expected_declaration) == DR002_DECLARED_FACTS, (
        "the expected declaration no longer spells DR-002's seven facts in order"
    )

    with resource_session(
        era, runtime_root=transcript_runtime, label="declaration", script=CLI_LAUNCH
    ) as (server, _opened):
        read = expect_result(
            server, server.call("resources/read", era.params({"uri": descriptor.uri}))
        )
        contents = as_array(read.get("contents"), "the read contents array")
        assert len(contents) == 1, server.diagnosis(
            f"a resource read must return exactly one contents entry: {read!r}"
        )
        entry = as_object(contents[0], "the read contents entry")
        meta = as_object(entry.get("_meta"), "the read contents _meta")
        assert set(meta) == {DECLARATION_META_KEY}, server.diagnosis(
            f"the read _meta must carry only {DECLARATION_META_KEY!r}: {sorted(meta)}"
        )
        projection = as_object(meta[DECLARATION_META_KEY], "the declaration projection")
        assert set(projection) == set(DR002_DECLARED_FACTS), server.diagnosis(
            f"the declaration projection is not DR-002's seven facts: {sorted(projection)}"
        )
        assert projection == expected_declaration, server.diagnosis(
            f"the declaration values are not the ones the catalog declares: {projection!r}"
        )

        frame = call_tool(server, era, name=STANDARD_READ, arguments={"uri": descriptor.uri})
        result = expect_result(server, frame)
        blocks = as_array(result.get("content"), f"the {STANDARD_READ} content array")
        assert blocks, server.diagnosis(f"{STANDARD_READ} returned no content block: {result!r}")
        carriers = [
            cast("dict[str, Any]", block)
            for block in blocks
            if isinstance(block, dict) and "resource" in cast("dict[str, object]", block)
        ]
        assert len(carriers) == 1, server.diagnosis(
            f"{STANDARD_READ} must carry the payload in exactly one embedded resource: {blocks!r}"
        )
        assert carriers[0]["resource"] == entry, server.diagnosis(
            "the embedded carrier is not the object resources/read produced for the same URI, so "
            f"FR-008's one mapping has become two.\nembedded: {carriers[0]['resource']!r}\n"
            f"read:     {entry!r}"
        )

        assert server.finish() == 0
        assert_protocol_only_stdout(server)


@pytest.mark.parametrize("era", ERAS, ids=ERA_IDS)
def test_registered_surface_never_answers_with_an_is_error_result(
    transcript_runtime: Path, transcript_repo: Path, era: Era
) -> None:
    """NFR-004: every refusal is a JSON-RPC error, never a successful ``isError`` result.

    The protocol allows a tool to report failure either way, and the two are not
    interchangeable here: ``isError: true`` carries prose in a content block, while
    the JSON-RPC error carries the ``ServiceError`` fields in ``error.data``. ADR
    0026's taxonomy amendment settles the choice — a refusal "is delivered as a
    JSON-RPC error, never as a successful ``isError`` result".

    Run in **both** eras (review F13): error behaviour is demonstrably era-divergent
    in this SDK, so a modern-only assertion is exactly the wrong place to stop
    parameterizing.
    """
    require_mcp_subcommand()
    refused = {
        STANDARDS_LIST: {"standard_id": "alpha"},
        STANDARD_READ: {"uri": "../../etc/passwd"},
        REPO_INSPECT: {REPO_ROOT_ARGUMENT: str(transcript_repo / "missing")},
        **{name: {REPO_ROOT_ARGUMENT: "relative"} for name in CONSUMER_TOOLS},
    }
    with resource_session(
        era, runtime_root=transcript_runtime, label="is-error", script=CLI_LAUNCH
    ) as (server, _opened):
        for name in tool_names(list_tools(server, era)):
            frame = call_tool(server, era, name=name, arguments=refused[name])
            assert "error" in frame, server.diagnosis(
                f"{name} answered a refused call with a successful result; ADR 0026 requires the "
                f"structured JSON-RPC error: {frame!r}"
            )
            assert frame.get("result") is None, server.diagnosis(
                f"{name} returned both an error and a result: {frame!r}"
            )
            failure = as_object(frame.get("error"), f"the {name} refusal")
            assert failure.get("code") != 0, server.diagnosis(
                f"{name} answered with code 0, which no protocol revision defines: {frame!r}"
            )
        assert server.finish() == 0
        assert_protocol_only_stdout(server)
