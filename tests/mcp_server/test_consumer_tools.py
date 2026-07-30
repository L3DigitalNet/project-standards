"""Consumer tools: ``reconcile_preview``, ``validate_repo``, ``drift_check`` (T9).

Covers TC-T9-001 (protocol results preserve the typed service results),
TC-T9-002 (the provider allowlist, root containment, and content exclusion hold
through MCP), TC-T9-004 (the preview preserves the control-plane schema and
fingerprint), and TC-T9-005 (compact, reviewed, read-only metadata). TC-T9-003
lives in ``tests/mcp_server/security/test_no_writes.py``.

Four authorities constrain every expectation here and none of them may be
re-derived by the modules under test:

*The spec* — FR-011 (``reconcile_preview`` returns ``ReconciliationPlan.to_jsonable()``
facts "without applying them"), FR-012 (``validate_repo`` "dispatches applicable
validate/verify/lint providers and returns their typed status, findings, and
diagnostics"), FR-013 (``drift_check`` "derives drift from reconciliation/provider
results ... without reparsing CLI text"), FR-014 (helper operations stay generic
and payload-qualified, "operations with mutating effects are rejected"), FR-017
(planning output "preserves the existing plan fingerprint/preconditions without
creating a competing plan identity scheme"), FR-022 (typed input/output models
plus structured content and bounded human text), FR-023 (descriptions state
purpose, input authority, and read-only effect; "tests snapshot the
supported-client tool metadata"), FR-024 (an explicit ``repo_root``), FR-028
(``.env``, credential stores, private config, and unrelated files are "neither
read nor returned"), NFR-012, IR-003, IR-009, DR-004 (no parallel MCP plan
schema), and DR-008 (the declared provider-result fields).

*SPEC-MS01 §10.3 EC-005* — "Repo lacks ``.standards/config.toml``, catalog, or
lock" ⇒ "``repo_inspect`` reports the exact missing state and ``reconcile_preview``
returns control-plane findings". The T3.3 arbitration put that obligation on the
*tool* rather than on the facade: ``McpServiceFacade.reconcile`` raises for every
non-``initialized`` classification, so a discriminating tool-layer shape is
contractually forced.

*The master plan §5.5* — the ``reconcile_preview`` tool result is a frozen DTO
row: "Closed two-slot envelope with required nullable fields ``preview`` (the
exact ``McpServiceFacade.reconcile`` projection) and ``control_plane`` (the exact
``RepoInspectionSnapshot`` projection), exactly one non-null; the slot follows the
authoritative state classification … never a caught ``ServiceError`` code" (field
freeze 2026-07-30, T9 RED review F1). The clarifying sentence on the
``McpServiceFacade.reconcile`` row carries the other half: "EC-005's findings
requirement is satisfied by the T9 ``reconcile_preview`` tool composing
``inspect_repo``". Both arms serialize verbatim, so DR-004's "no parallel MCP plan
schema" is preserved rather than paralleled.

*ADR 0025/0026* — the approved non-mutating operation set is exactly
validate/verify/lint/drift-check with the ``findings`` effect; ADR 0025 names no
generic helper *tool* with an exact schema, so plan:439 registers none and the
allowlist reaches the protocol only through the two composite tools. ADR 0026
freezes the six-tool registry and the read-only behaviour; its 2026-07-30
amendment makes the instructions string bind *per session registry* — the
six-tool text for a session registering all six, the same text with the
enumeration reduced for a session whose matrix omits ``standard_read``. Protocol
annotations stay unasserted: ``ToolAnnotations``/``readOnlyHint`` are deliberately
absent here, as at T8 (T8.2 Codex RED review, F7). Client-advertised roots are the
record's other narrowing input (ADR 0026 root rules): they "may only validate or
narrow containment", "never substitute a missing ``repo_root``, never select a
different repository, and never widen the boundary".

*The service layer* — every expected value comes from ``McpServiceFacade`` and
from the authoritative planner/dispatcher oracles the T3/T4 suites already own.
T9 is a registration and mapping task, so its oracle is the layer that owns the
facts, never a second copy of them.

**Harness reuse, stated exactly.** ``test_transport.py`` owns the
subprocess/transcript/capability machinery, ``test_resources.py`` owns the era
machinery, the recording-facade launch, and the runtime linker,
``test_standard_read.py`` owns the tool-listing/calling probes and the
client-matrix launch, ``test_discovery_tools.py`` owns the structured-result and
schema probes, the filesystem-audit prologue, and the reviewed T8 metadata
snapshot this file *composes with* rather than copies, and
``tests/mcp_services/test_providers.py`` and ``test_consumer.py`` own the
provider tree, the consumer state fixtures, and the authoritative selection,
plan, and finding-key oracles. One helper is added — ``build_provider_runtime``,
nine lines composing the T4 provider tree with the T6 runtime linker — because
``build_fixture_runtime`` hard-codes a projection source that declares no
validate/verify/lint/drift-check provider anywhere, and T9's file list does not
include ``test_resources.py`` (deviation recorded in ``notes.md`` before the file
was created).

Two RED controls run against surfaces that already exist, so that every oracle
the acceptance tests depend on is exercised even while the T9 registration is
absent:

* ``test_provider_backed_fixture_serves_authoritative_results`` drives the facade
  directly over the provider distribution and proves the fixture really produces
  provider results, a real fingerprint, degraded-state refusals, and unexecuted
  mutating providers. Without it, every assertion below would stop at the absent
  registration with its oracles unproven.
* ``test_client_roots_probe_observes_the_back_channel_per_era`` drives a bare SDK
  server that asks its client for roots, in both eras, and pins what the SDK
  actually does: over classic stdio the server-to-client ``roots/list`` request
  is answered by the client, and at 2026-07-28 — where SEP-2577 deprecates Roots
  — the same call raises ``NoBackChannelError`` because the transport context has
  no back-channel at all. That measurement is what makes the client-root
  assertions below era-correct instead of aspirational, and it is why "the client
  declared roots but none could be fetched" must mean *no advertised set* rather
  than *an empty advertised set*: the two are opposite instructions to
  ``resolve_effective_root``.
"""

from __future__ import annotations

import json
import shutil
import uuid
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol, cast

import pytest
from jsonschema import Draft202012Validator
from mcp_types import CLIENT_CAPABILITIES_META_KEY, INVALID_PARAMS, METHOD_NOT_FOUND

from project_standards._version import package_version
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.executor import reconciliation_fingerprint
from project_standards.control_plane.state import StateKind
from project_standards.mcp_services import Finding, ServiceError
from tests.mcp_server.test_discovery_tools import (
    EXPECTED_TOOL_METADATA,
    FORBIDDEN_DESCRIPTION_TOKENS,
    FORBIDDEN_TOOL_NAMES,
    FORBIDDEN_TOOL_TOKENS,
    NEGATED_READ_ONLY_CLAIMS,
    READ_ONLY_CLAIMS,
    REPO_INSPECT,
    REPO_ROOT_ARGUMENT,
    STANDARDS_LIST,
    assert_conforms,
    assert_valid_schema,
    audited_opens,
    audited_spy_launch,
    facade_calls,
    input_properties,
    opens_by_layer,
    refusal_of,
    rendered,
    required_names,
    service_code,
    structured,
)
from tests.mcp_server.test_resources import (
    CATALOG_URI,
    ERA_IDS,
    ERAS,
    FIXTURE_SUBTREES,
    LEGACY_RESOURCE_NOT_FOUND,
    MODERN_ERA,
    Era,
    declared_resources,
    oracle_facade,
    resource_session,
    spy_launch,
)
from tests.mcp_server.test_standard_read import (
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
    CLI_LAUNCH,
    FROZEN_V1_TOOLS,
    RUNTIME_ROOT,
    ServerProcess,
    as_object,
    assert_capabilities_match_reachable_registrations,
    assert_instructions_are_truthful,
    assert_no_list_change_promises,
    assert_no_write_surface,
    assert_stdout_is_protocol_only,
    boundary_option_name,
    cli_launch_with,
    declared_capabilities,
    expect_error,
    expect_result,
    modern_meta,
    require_mcp_subcommand,
)
from tests.mcp_services.test_consumer import (
    build_state_fixtures,
    dumped,
    field_names,
    finding_json_keys,
)
from tests.mcp_services.test_providers import (
    APPROVED_OPERATIONS,
    build_provider_repo,
    build_provider_tree,
    mutating_provider_ran,
    oracle_plan,
    oracle_selection,
)

ADAPTER_PACKAGE = "project_standards.mcp_server"
TOOLS_MODULE = f"{ADAPTER_PACKAGE}.tools"

# ADR 0026's frozen v1 registry spells all three names; T9 may not rename them
# and may add no fourth (the record's tool set is closed, and the plan repeats it
# as a stop condition).
RECONCILE_PREVIEW = "reconcile_preview"
VALIDATE_REPO = "validate_repo"
DRIFT_CHECK = "drift_check"
CONSUMER_TOOLS = (RECONCILE_PREVIEW, VALIDATE_REPO, DRIFT_CHECK)

# The master plan §5.5 DTO row for the `reconcile_preview` tool result: a closed
# two-slot envelope, both fields required and nullable, exactly one non-null, with
# the slot following the authoritative state classification — `initialized`
# publishes `preview`, every other classification publishes `control_plane` via
# `inspect_repo` — and never a caught `ServiceError` code. Both arms serialize
# verbatim, which is what preserves DR-004 while satisfying EC-005 at the tool
# layer (field freeze 2026-07-30, T9 RED review F1).
PREVIEW_SLOT = "preview"
CONTROL_PLANE_SLOT = "control_plane"

# ADR 0026's frozen instructions text (adr-0026 line 163), binding at T9 by the
# 2026-07-29 amendment (line 165) and bound *per session registry* by the
# 2026-07-30 amendment (line 167). Two renderings are reachable, and the second is
# the first with "the count word and the enumeration shrink, nothing else
# changes": a session whose recorded matrix registers all six tools serves the
# six-tool text, and a session whose matrix omits the `standard_read` fallback
# serves the same text naming its actual five.
#
# Two normalizations are applied to the record's Markdown rendering, both
# following the convention `models.PHASE_INSTRUCTIONS` has used since T5:
# backticks are dropped, because the served value is a plain string; and
# `{catalog_major}` resolves to the generation this server exposes, because the
# record's own prose already says "Catalog 5" while the other two forms stay
# templates — they *are* the registered URI templates.
_INSTRUCTIONS_PREFIX = (
    "Project Standards is a read-only, local standards server. It exposes the installed "
    "Catalog 5 standard packages and reports on a consumer repository; it never writes to any "
    "repository. Standard content is addressed under the standards:// URI scheme as "
    "standards://catalog/5, standards://{standard_id}/{version}, and "
    "standards://{standard_id}/{version}/resources/{resource_id}, using ids and versions "
    "exactly as the installed catalog declares them. "
)
_INSTRUCTIONS_SUFFIX = (
    " Every repository-scoped tool requires an explicit repo_root argument; the server does "
    "not infer the repository from the working directory or from client roots."
)

# Index is the registry size. Written out because the record's sentence uses a
# count *word* ("Six tools are available"), and a rendering that said "6" would
# not be the frozen text with its enumeration reduced.
COUNT_WORDS = ("No", "One", "Two", "Three", "Four", "Five", "Six")

# ADR 0026's registry order, which is also the order the record's own sentence
# uses. The reduction removes a name; it does not reorder the rest.
INSTRUCTIONS_TOOL_ORDER = (
    "standards_list",
    "standard_read",
    "repo_inspect",
    "reconcile_preview",
    "validate_repo",
    "drift_check",
)


def instructions_for(registered: Sequence[str]) -> str:
    """The ADR 0026 instructions rendering for one session's actual registry."""
    names = [name for name in INSTRUCTIONS_TOOL_ORDER if name in set(registered)]
    assert len(names) == len(set(registered)), (
        f"the registry names something outside ADR 0026's frozen order: {sorted(registered)}"
    )
    enumeration = f"{', '.join(names[:-1])}, and {names[-1]}"
    return (
        f"{_INSTRUCTIONS_PREFIX}{COUNT_WORDS[len(names)]} tools are available: "
        f"{enumeration}.{_INSTRUCTIONS_SUFFIX}"
    )


# The record's own text, transcribed verbatim (modulo the two normalizations
# above) so the generator below is checked against the document rather than
# trusted. This is the rendering a session registering all six must serve.
FROZEN_SIX_TOOL_INSTRUCTIONS = (
    "Project Standards is a read-only, local standards server. It exposes the installed "
    "Catalog 5 standard packages and reports on a consumer repository; it never writes to any "
    "repository. Standard content is addressed under the standards:// URI scheme as "
    "standards://catalog/5, standards://{standard_id}/{version}, and "
    "standards://{standard_id}/{version}/resources/{resource_id}, using ids and versions "
    "exactly as the installed catalog declares them. Six tools are available: standards_list, "
    "standard_read, repo_inspect, reconcile_preview, validate_repo, and drift_check. Every "
    "repository-scoped tool requires an explicit repo_root argument; the server does not infer "
    "the repository from the working directory or from client roots."
)

# DR-008: `ProviderOperationResult.diagnostics` is bounded supplemental text that
# participates in no identity, and the T4 fixture providers deliberately write
# per-process nonces into it, so byte equality of a whole provider result is
# unachievable by construction. The exclusion is that DTO field and nothing else:
# a provider-declared *output* field that happens to be named `diagnostics` is
# ordinary declared output and must compare verbatim (T9.2 Codex RED review, F3).
DIAGNOSTICS_FIELD = "diagnostics"
DIAGNOSTICS_MASK = "<diagnostics>"
RESULTS_FIELD = "results"

# The two declared §5.5 renames between the authoritative control-plane finding
# serializer and the protocol-neutral `Finding`. Used to hold the published key
# set to `findings_to_jsonable`'s own output rather than to a private MCP shape.
DECLARED_FINDING_RENAMES = {"code": "rule_id", "hint": "remediation"}

# FR-028's four exclusion classes, planted with per-session sentinels so a stale
# fixture cannot mask a real leak. An absence claim needs a witness.
_SESSION = uuid.uuid4().hex[:8]
EXCLUDED_CONTENT: tuple[tuple[str, str], ...] = (
    (".env", f"do-not-publish-env-{_SESSION}"),
    ("secrets/credentials.toml", f"do-not-publish-credential-{_SESSION}"),
    ("private/id_ed25519", f"do-not-publish-private-key-{_SESSION}"),
    ("notes/unrelated.md", f"do-not-publish-unrelated-{_SESSION}"),
)
EXCLUDED_SENTINELS = tuple(sentinel for _, sentinel in EXCLUDED_CONTENT)

# The facade methods each tool may reach while answering one call. Upper bounds,
# following the T8 rule: `catalog` is allowed because the facade validated it at
# construction, and what matters is what is forbidden. `resource` would mean a
# tool reached for payload bytes; `invoke_read_provider` would mean the adapter
# performed the provider selection plan:439 keeps in the service layer (freeze
# #11). Neither appears in any allowed set.
ALLOWED_FACADE_CALLS: dict[str, frozenset[str]] = {
    RECONCILE_PREVIEW: frozenset({"catalog", "inspect_repo", "reconcile"}),
    VALIDATE_REPO: frozenset({"catalog", "validate_repo"}),
    DRIFT_CHECK: frozenset({"catalog", "drift_check"}),
}

# The facade call each tool must actually make: the authority that reloads the
# current consumer state for that answer.
REQUIRED_FACADE_CALL: dict[str, str] = {
    RECONCILE_PREVIEW: "reconcile",
    VALIDATE_REPO: "validate_repo",
    DRIFT_CHECK: "drift_check",
}

# ---------------------------------------------------------------------------
# FR-023's reviewed metadata snapshot, for the three tools T9 owns
# ---------------------------------------------------------------------------
#
# Composed with T8's reviewed constant rather than forking it (freeze #8): the
# served surface must equal `{**EXPECTED_TOOL_METADATA, **EXPECTED_CONSUMER_TOOL_METADATA}`,
# which stays correct whether T9.3 extends T8's constant to all six tools or
# leaves it at three. The wire spelling is the protocol's (`inputSchema`,
# `outputSchema`), because this is compared against what a client receives.

# Any JSON value, spelled out rather than written as `{}`. The slots that carry
# it hold the control plane's *own* serialization — a plan action, a resolution,
# a lock document, a provider's declared output — whose shape is by definition
# unconstrained here.
ANY_JSON: dict[str, Any] = {"type": ["object", "array", "string", "number", "boolean", "null"]}

STRING_ARRAY: dict[str, Any] = {"type": "array", "items": {"type": "string"}}
ANY_JSON_ARRAY: dict[str, Any] = {"type": "array", "items": ANY_JSON}

# Taken from the reviewed T8 snapshot rather than restated: the DR-005 snapshot
# and the §5.5 `Finding` already have one reviewed schema each, and a second copy
# here is the divergence one shared constant exists to prevent.
SNAPSHOT_SCHEMA = cast("dict[str, Any]", EXPECTED_TOOL_METADATA[REPO_INSPECT]["outputSchema"])
FINDING_SCHEMA = cast(
    "dict[str, Any]",
    cast("dict[str, Any]", cast("dict[str, Any]", SNAPSHOT_SCHEMA["properties"])["findings"])[
        "items"
    ],
)


class _Validator(Protocol):
    """The one validator method used here, typed so strict mode can see it.

    Declared locally rather than imported: ``test_discovery_tools`` types the same
    shape for its own positive-conformance helper, and reaching for another
    module's private protocol to run the *negative* check would couple two suites
    through a name neither publishes.
    """

    def iter_errors(self, instance: object) -> Iterator[object]: ...


def schema_rejects(schema: Mapping[str, Any], instance: Mapping[str, Any]) -> bool:
    """Whether one document fails the schema a tool actually advertised."""
    validator = cast("_Validator", Draft202012Validator(dict(schema)))
    return next(validator.iter_errors(dict(instance)), None) is not None


def nullable(*declared: dict[str, Any]) -> dict[str, Any]:
    """One optional slot: the declared kind, or an explicit null.

    ``ServiceModel`` serializes the whole frozen field set, so an optional field
    is *present and null* rather than absent. That is what lets the objects below
    be both closed and fully required.
    """
    return {"anyOf": [*declared, {"type": "null"}]}


def repo_root_input_schema(description: str) -> dict[str, Any]:
    """FR-024's explicit root, declared in the schema as well as in the handler.

    The property sentence is per-tool because the purpose differs; the
    required-clause is identical everywhere, so the rule a caller must learn
    reads the same on all four repository-scoped tools.
    """
    return {
        "type": "object",
        "properties": {REPO_ROOT_ARGUMENT: {"type": "string", "description": description}},
        "required": [REPO_ROOT_ARGUMENT],
        "additionalProperties": False,
    }


# `ReconciliationPreview`, closed and complete against the frozen §5.5 field
# list: every public field of `ReconciliationPlan.to_jsonable()` plus
# `reconciliation_fingerprint`, and nothing else. The executor-only proposed
# bytes have no slot at all, which is the schema-level half of "a preview may
# never publish staged content".
PREVIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "schema_version": {"type": "string"},
        "applicable": {"type": "boolean"},
        "actions": ANY_JSON_ARRAY,
        "configuration_transforms": ANY_JSON_ARRAY,
        "units": ANY_JSON_ARRAY,
        "findings": ANY_JSON_ARRAY,
        "preconditions": ANY_JSON_ARRAY,
        "resolution": ANY_JSON,
        "verification_requests": ANY_JSON_ARRAY,
        "provider_notices": ANY_JSON_ARRAY,
        "namespace_prunes": STRING_ARRAY,
        "catalog_refresh": ANY_JSON,
        "next_lock": ANY_JSON,
        "proposed_lock": ANY_JSON,
        "reconciliation_fingerprint": {"type": "string"},
    },
    "required": [
        "schema_version",
        "applicable",
        "actions",
        "configuration_transforms",
        "units",
        "findings",
        "preconditions",
        "resolution",
        "verification_requests",
        "provider_notices",
        "namespace_prunes",
        "catalog_refresh",
        "next_lock",
        "proposed_lock",
        "reconciliation_fingerprint",
    ],
    "additionalProperties": False,
}

# EC-005's envelope. Closed, both slots required, and — the part a pair of
# independently nullable properties could not express — exactly one of them
# populated, spelled as the two valid arms under `oneOf` so a client validating
# against the advertised schema rejects a both-null or both-populated document
# rather than merely being told about the rule in prose (T9.4 Codex GREEN review,
# F2; falsified in both directions by TC-T9-004).
RECONCILE_PREVIEW_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        PREVIEW_SLOT: nullable(PREVIEW_SCHEMA),
        CONTROL_PLANE_SLOT: nullable(SNAPSHOT_SCHEMA),
    },
    "required": [PREVIEW_SLOT, CONTROL_PLANE_SLOT],
    "additionalProperties": False,
    "oneOf": [
        {"properties": {PREVIEW_SLOT: PREVIEW_SCHEMA, CONTROL_PLANE_SLOT: {"type": "null"}}},
        {"properties": {PREVIEW_SLOT: {"type": "null"}, CONTROL_PLANE_SLOT: SNAPSHOT_SCHEMA}},
    ],
}

# DR-008's declared provider-result fields, closed and fully required: identity,
# operation, phase, effect, status, findings, diagnostics, and the declared
# output-schema fields the dispatcher already published.
PROVIDER_RESULT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "standard_id": {"type": "string"},
        "version": {"type": "string"},
        "provider_id": {"type": "string"},
        "operation": {"type": "string"},
        "phase": {"type": "string"},
        "effect": {"type": "string"},
        "status": {"type": "string"},
        "findings": {"type": "array", "items": FINDING_SCHEMA},
        DIAGNOSTICS_FIELD: {"type": "string"},
        "output": ANY_JSON,
    },
    "required": [
        "standard_id",
        "version",
        "provider_id",
        "operation",
        "phase",
        "effect",
        "status",
        "findings",
        DIAGNOSTICS_FIELD,
        "output",
    ],
    "additionalProperties": False,
}

VALIDATE_REPO_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "repo_root": {"type": "string"},
        "results": {"type": "array", "items": PROVIDER_RESULT_SCHEMA},
        "findings": {"type": "array", "items": FINDING_SCHEMA},
    },
    "required": ["repo_root", "results", "findings"],
    "additionalProperties": False,
}

# `DriftReport.findings` carries the *plan's* own findings serialization, not the
# protocol-neutral `Finding` DTO that `ValidationReport.findings` carries. The
# difference is contract, not accident: drift findings come from
# `ReconciliationPlan.to_jsonable()`, whose shape belongs to the control plane.
DRIFT_CHECK_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "repo_root": {"type": "string"},
        "reconciliation_fingerprint": {"type": "string"},
        "actions": ANY_JSON_ARRAY,
        "findings": ANY_JSON_ARRAY,
        "results": {"type": "array", "items": PROVIDER_RESULT_SCHEMA},
    },
    "required": ["repo_root", "reconciliation_fingerprint", "actions", "findings", "results"],
    "additionalProperties": False,
}

EXPECTED_CONSUMER_TOOL_METADATA: dict[str, dict[str, Any]] = {
    RECONCILE_PREVIEW: {
        "name": RECONCILE_PREVIEW,
        "title": "Preview reconciliation for one consumer repository",
        "description": (
            "Return the dry-run reconciliation plan for one consumer repository: actions, "
            "findings, preconditions, provider notices, next lock, and the control plane's own "
            "reconciliation fingerprint. When the repository cannot be planned, its "
            "control-plane state and findings are returned instead. The repository is the "
            "explicit repo_root argument, never the working directory. Read-only: it plans but "
            "never applies, and writes nothing."
        ),
        "inputSchema": repo_root_input_schema(
            "Absolute path to the consumer repository to preview reconciliation for. Required: "
            "the server never infers a repository from its working directory."
        ),
        "outputSchema": RECONCILE_PREVIEW_OUTPUT_SCHEMA,
    },
    VALIDATE_REPO: {
        "name": VALIDATE_REPO,
        "title": "Validate one consumer repository against its standards",
        "description": (
            "Run every applicable validate, verify, and lint provider declared by the standards "
            "this consumer repository currently resolves, and return their typed status, "
            "findings, and bounded diagnostics. Providers are chosen by the repository's own "
            "resolution and cannot be named by the caller. The repository is the explicit "
            "repo_root argument, never the working directory. Read-only: no mutating provider "
            "operation is dispatched and nothing is written."
        ),
        "inputSchema": repo_root_input_schema(
            "Absolute path to the consumer repository to validate. Required: the server never "
            "infers a repository from its working directory."
        ),
        "outputSchema": VALIDATE_REPO_OUTPUT_SCHEMA,
    },
    DRIFT_CHECK: {
        "name": DRIFT_CHECK,
        "title": "Report standards drift for one consumer repository",
        "description": (
            "Report drift for one consumer repository: the control plane's own reconciliation "
            "actions, findings, and fingerprint, plus the results of every applicable "
            "drift-check provider. Facts only, with no summary verdict, confidence, or "
            "clean-state flag invented. The repository is the explicit repo_root argument, "
            "never the working directory. Read-only: it writes nothing."
        ),
        "inputSchema": repo_root_input_schema(
            "Absolute path to the consumer repository to report drift for. Required: the server "
            "never infers a repository from its working directory."
        ),
        "outputSchema": DRIFT_CHECK_OUTPUT_SCHEMA,
    },
}

# FR-023's per-tool purpose and input-authority phrases, asserted against the
# reviewed constants above rather than against whatever the server happens to
# serve: equality with the snapshot constrains the implementation, and these
# constrain the snapshot.
REVIEWED_CONSUMER_DESCRIPTION_CLAIMS: dict[str, tuple[str, ...]] = {
    RECONCILE_PREVIEW: ("reconciliation", "repo_root", "never the working directory"),
    VALIDATE_REPO: ("validate", "resolution", "repo_root", "never the working directory"),
    DRIFT_CHECK: ("drift", "repo_root", "never the working directory"),
}

# Input property names that would let a caller name a provider operation,
# payload identity, or effect through the protocol. ADR 0025 names no generic
# helper tool, so plan:439 registers none: the only way an unapproved operation
# could be requested over MCP is through an argument, and no v1 tool declares
# one.
DISPATCH_ARGUMENT_TOKENS = (
    "operation",
    "provider",
    "effect",
    "entrypoint",
    "payload",
    "version",
    "standard",
    "apply",
    "write",
)

# The only input properties ADR 0026's six tools declare: one canonical resource
# URI for the fallback read, one explicit repository root for the four
# repository-scoped tools, and nothing at all for the catalog listing.
ALLOWED_INPUT_PROPERTIES = frozenset({REPO_ROOT_ARGUMENT, "uri"})


# RED control only. A bare SDK server whose single tool asks its client for
# advertised roots and reports what came back. It exists to measure the SDK's
# back-channel behaviour per era rather than to model the adapter: the T9 tools
# consult roots through `resolve_effective_root`, not by echoing them.
BARE_SDK_ROOTS_CONTROL = """
import warnings

import anyio
import mcp_types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server


async def _list_tools(ctx, params):
    return types.ListToolsResult(
        tools=[
            types.Tool(
                name="probe",
                title="Roots probe",
                description="Report the client's advertised roots. Read-only.",
                inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
            )
        ]
    )


async def _call_tool(ctx, params):
    try:
        with warnings.catch_warnings():
            # SEP-2577 deprecates Roots; the deprecation is the protocol's, not
            # this call's, and the warning would otherwise ride the server's
            # stderr for a measurement the record asks for.
            warnings.simplefilter("ignore")
            answer = await ctx.session.list_roots()
        text = "ROOTS=" + repr([str(root.uri) for root in answer.roots])
    except Exception as exc:
        text = "ROOTS-ERROR=" + type(exc).__name__
    return types.CallToolResult(content=[types.TextContent(type="text", text=text)])


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


# -- planned surface -----------------------------------------------------------


def require_consumer_tools(server: ServerProcess, era: Era) -> dict[str, dict[str, Any]]:
    """The three advertised consumer tools, or an explicit RED assertion.

    The planned absence T9 closes is a *registration*, not a module: ``tools.py``
    has existed since T7, so the assertion that must fail before T9.3 is that
    these three names are advertised. Asserted inside a collected test, per the
    plan's RED contract.
    """
    entries = {str(entry.get("name")): dict(entry) for entry in list_tools(server, era)}
    missing = [name for name in CONSUMER_TOOLS if name not in entries]
    assert not missing, server.diagnosis(
        f"planned T9 tools {missing} are not advertised; the consumer-tool registration does "
        f"not exist yet. tools/list carried {sorted(entries)}"
    )
    return {name: entries[name] for name in CONSUMER_TOOLS}


def tools_module() -> ModuleType:
    """The T7 tool module, which T9 extends rather than creates."""
    return require_tools_module()


# -- fixtures ------------------------------------------------------------------


def build_provider_runtime(destination: Path) -> Path:
    """Return an importable runtime whose alpha 2.0 declares runnable providers.

    A composition, not a fork: ``tests.mcp_services.test_providers.build_provider_tree``
    performs the projection (the upstream package fixture declares no
    validate/verify/lint/drift-check provider anywhere, only ``render``/``migrate``),
    and the symlink/copy step is the one ``build_fixture_runtime`` performs — the
    real adapter code linked in, only the three catalog subtrees replaced. It is
    duplicated rather than reached because ``build_fixture_runtime`` hard-codes
    its projection source and ``test_resources.py`` is outside T9's file list.

    The staging tree is deleted before returning, so a runtime that reached
    sibling source files instead of its own projection cannot pass.
    """
    staging = destination / "staging"
    installed = build_provider_tree(staging)
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


def plant_excluded_content(repo: Path) -> None:
    """Write FR-028's four exclusion classes into one consumer repository."""
    for relative, sentinel in EXCLUDED_CONTENT:
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"{sentinel}\n", encoding="utf-8")


@pytest.fixture(scope="module")
def provider_runtime(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The provider-declaring fixture catalog, shared read-only across tests."""
    return build_provider_runtime(tmp_path_factory.mktemp("consumer-tools"))


@pytest.fixture(scope="module")
def provider_distribution(provider_runtime: Path) -> InstalledDistribution:
    """The same installed distribution the server is launched over.

    Built at the server's own release so the classification a tool reports and
    the classification an oracle computes cannot differ for fixture reasons.
    """
    return InstalledDistribution(
        provider_runtime / "project_standards", tool_release=package_version()
    )


@pytest.fixture(scope="module")
def planned_repo(
    provider_distribution: InstalledDistribution, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    """One initialized consumer repository with ``alpha`` enabled and not yet applied.

    Enabling a package without reconciling is what gives the plan pending
    actions, preconditions, and staged targets — without them the preview
    assertions below would hold vacuously.
    """
    parent = tmp_path_factory.mktemp("consumer-planned")
    repo = build_provider_repo(parent, "planned", distribution=provider_distribution)
    plant_excluded_content(repo)
    return repo


@pytest.fixture(scope="module")
def degraded_repos(
    provider_distribution: InstalledDistribution, tmp_path_factory: pytest.TempPathFactory
) -> dict[str, Path]:
    """One repository per authoritative classification that cannot be planned.

    Taken from ``tests/mcp_services/test_consumer.py``'s own state builder, which
    already owns every rule about what makes each classification real, against
    the same installed distribution the server serves. ``initialized`` is
    excluded because it is the one classification that *can* be planned and is
    covered by ``planned_repo``.
    """
    parent = tmp_path_factory.mktemp("consumer-degraded")
    fixtures = build_state_fixtures(parent, provider_distribution)
    return {
        kind.value: path for kind, path in fixtures.items() if kind is not StateKind.INITIALIZED
    }


@pytest.fixture(scope="module")
def expected_documents(provider_runtime: Path, planned_repo: Path) -> dict[str, dict[str, Any]]:
    """The exact service-layer answer each consumer tool must project, computed once.

    Every value comes from ``McpServiceFacade`` over the same bytes the server
    serves. Computing them once is not only a cost decision: each composite call
    spawns one worker process per applicable declaration, and a per-test oracle
    would multiply that by the era parametrization for no additional coverage.
    """
    facade = oracle_facade(provider_runtime)
    return {
        RECONCILE_PREVIEW: {
            PREVIEW_SLOT: dumped(facade.reconcile(planned_repo)),
            CONTROL_PLANE_SLOT: None,
        },
        VALIDATE_REPO: dumped(facade.validate_repo(planned_repo)),
        DRIFT_CHECK: dumped(facade.drift_check(planned_repo)),
    }


# -- probes --------------------------------------------------------------------


def without_diagnostics(document: Mapping[str, Any]) -> dict[str, Any]:
    """One report with each provider result's own ``diagnostics`` field masked.

    DR-008 excludes exactly one thing from identity:
    ``ProviderOperationResult.diagnostics``. An earlier revision masked *every*
    key named ``diagnostics`` at any depth, which would also have masked a
    provider-declared ``output.diagnostics`` — declared output-schema fields that
    DR-008 requires the result to preserve, so a lossy or fabricated one would
    have compared equal (T9.2 Codex RED review, F3).

    The mask is therefore positional: the top-level field of each entry in
    ``results``, and nothing else. Documents without a ``results`` array — the
    ``reconcile_preview`` envelope — pass through untouched.
    """
    projected = dict(document)
    entries = projected.get(RESULTS_FIELD)
    if not isinstance(entries, list):
        return projected
    projected[RESULTS_FIELD] = [
        {**as_object(entry, "a provider result"), DIAGNOSTICS_FIELD: DIAGNOSTICS_MASK}
        for entry in cast("list[object]", entries)
    ]
    return projected


def masked_positions(document: Mapping[str, Any]) -> int:
    """How many values :func:`without_diagnostics` would replace in this document."""
    entries = document.get(RESULTS_FIELD)
    return len(cast("list[object]", entries)) if isinstance(entries, list) else 0


def _all_diagnostics(value: object) -> list[object]:
    """Every value under a key named ``diagnostics``, at any depth."""
    found: list[object] = []
    if isinstance(value, dict):
        for key, item in cast("dict[str, object]", value).items():
            if key == DIAGNOSTICS_FIELD:
                found.append(item)
            else:
                found.extend(_all_diagnostics(item))
    elif isinstance(value, list):
        for item in cast("list[object]", value):
            found.extend(_all_diagnostics(item))
    return found


def nested_diagnostics(document: Mapping[str, Any]) -> list[object]:
    """Every ``diagnostics`` value *below* a provider result's own field.

    Used to prove the mask is not silently covering a nested one: whatever a
    provider declares under ``output`` is ordinary declared output and must
    survive the comparison verbatim.
    """
    entries = document.get(RESULTS_FIELD)
    if not isinstance(entries, list):
        return _all_diagnostics(document)
    found: list[object] = []
    for entry in cast("list[object]", entries):
        result = as_object(entry, "a provider result")
        for key, item in result.items():
            if key != DIAGNOSTICS_FIELD:
                found.extend(_all_diagnostics(item))
    return found


def result_diagnostics(document: Mapping[str, Any]) -> list[object]:
    """Each provider result's own ``diagnostics`` value, in order."""
    entries = document.get(RESULTS_FIELD)
    if not isinstance(entries, list):
        return []
    return [
        as_object(entry, "a provider result").get(DIAGNOSTICS_FIELD)
        for entry in cast("list[object]", entries)
    ]


def result_identities(document: Mapping[str, Any]) -> list[tuple[str, str, str, str]]:
    """The ordered (standard, version, provider, operation) tuples a report published.

    A *sequence*, not a set, so a duplicated dispatch fails on cardinality — the
    T4 rule for the same claim.
    """
    entries = cast("list[object]", document.get("results", []))
    return [
        (
            str(entry.get("standard_id")),
            str(entry.get("version")),
            str(entry.get("provider_id")),
            str(entry.get("operation")),
        )
        for entry in (as_object(item, "a provider result") for item in entries)
    ]


def finding_paths(document: object) -> list[str]:
    """Every ``path`` a finding published anywhere in one document."""
    found: list[str] = []
    if isinstance(document, dict):
        entry = cast("dict[str, object]", document)
        value = entry.get("path")
        # `rule_id` is the §5.5 rename; `code` is the control plane's own
        # spelling, which `DriftReport.findings` preserves untouched.
        if isinstance(value, str) and ("rule_id" in entry or "code" in entry):
            found.append(value)
        for item in entry.values():
            found.extend(finding_paths(item))
    elif isinstance(document, list):
        for item in cast("list[object]", document):
            found.extend(finding_paths(item))
    return found


def authoritative_finding_keys() -> set[str]:
    """The §5.5 ``Finding`` key set, derived from the authoritative serializer.

    ``findings_to_jsonable`` is the control plane's own finding serialization;
    §5.5 renames exactly two of its keys and adds the defaulted ``null_values``.
    Deriving the expected set this way is what keeps the published finding shape
    pinned to the authoritative one rather than to a private MCP shape (freeze
    #1).
    """
    return {DECLARED_FINDING_RENAMES.get(key, key) for key in finding_json_keys()} | {"null_values"}


def assert_excludes_consumer_content(
    server: ServerProcess, document: object, *, label: str
) -> None:
    """FR-028: no planted secret, credential, private key, or unrelated file content.

    Applied to the **complete rendered protocol frame** of every answer and every
    refusal, diagnostics included (T9.2 Codex RED review, F9). Sweeping only the
    structured half would have left three carriers unexamined — the human text
    block, the bounded provider diagnostics, and a refusal's ``error.data`` — and
    the diagnostics carrier is exactly where captured provider output lands.

    The recorded bound: FR-028's "neither read nor returned" is proven here for
    *returned*, and for *read* in
    ``test_consumer_tools_reach_facts_only_through_the_facade`` — for the server
    process. A provider running in the worker interpreter legitimately reads the
    consumer repository, so its reads are neither observed nor forbidden; the
    payloads are digest-verified trusted bytes under ADR 0025's trust model, and
    the protocol-layer contract this suite polices is exclusion from what is
    served.
    """
    text = rendered(document)
    leaked = [sentinel for sentinel in EXCLUDED_SENTINELS if sentinel in text]
    assert not leaked, server.diagnosis(f"{label} carries excluded consumer content: {leaked}")


# -- refusal projection (FR-025/NFR-004, T9.2 Codex RED review F5) --------------

# The stable service codes a repository-scoped tool call can be refused with, and
# the layer that owns each. Written down because the assertion is that a refusal
# preserves *the service's own* published fields, and a test that accepted any
# code would not notice a mapping that invented one.
ROOT_INVALID_CODE = "repo-root-invalid"
ROOT_OUT_OF_BOUNDS_CODE = "repo-root-out-of-bounds"
TOOL_ARGUMENTS_INVALID_CODE = "tool-arguments-invalid"
TOOL_NOT_FOUND_CODE = "tool-not-found"

# The service layer's own code for a control plane it cannot resolve. It is the
# baseline outcome `validate_repo`/`drift_check` produce for an uninitialized
# repository, which EC-005 does not bind them to answer (freeze #6).
CONTROL_PLANE_UNAVAILABLE_CODE = "control-plane-unavailable"

# The complete `ServiceError` projection NFR-004 requires to stay
# machine-readable: "code, message, affected path/standard, severity,
# remediation". `severity` and `remediation` are always published; the identity
# fields are omitted rather than nulled when the failure has none, which is a
# distinction a client can act on.
REQUIRED_ERROR_DATA_FIELDS = ("code", "severity", "remediation")
OPTIONAL_ERROR_DATA_FIELDS = ("standard_id", "version", "path")


def error_data(server: ServerProcess, refusal: Mapping[str, Any], *, label: str) -> dict[str, Any]:
    """The structured ``ServiceError`` projection one refusal published."""
    data = refusal.get("data")
    assert isinstance(data, dict), server.diagnosis(
        f"{label} carries no structured error data; NFR-004 requires the code, severity, "
        f"remediation, and affected path/standard to stay machine-readable: {refusal!r}"
    )
    return cast("dict[str, Any]", data)


def assert_structured_refusal(
    server: ServerProcess,
    frame: Mapping[str, Any],
    *,
    label: str,
    code: str,
    wire_code: int,
) -> dict[str, Any]:
    """One refusal, asserted end to end: carrier, wire code, and every published field.

    The carrier is required to be a JSON-RPC *error*, not merely "either carrier
    the protocol allows". An earlier revision accepted both, which meant no
    assertion ever reached the wire code or the ``ServiceError`` projection at all
    (T9.2 Codex RED review, F5). The adapter maps refusals through
    ``_protocol_error``, so the error carrier is the one it produces; a tool that
    answered with ``isError`` instead would be a different mapping and must fail
    here rather than pass silently.
    """
    assert "error" in frame, server.diagnosis(
        f"{label} did not travel as a JSON-RPC error: {frame!r}"
    )
    error = expect_error(server, frame)
    assert error.get("code") == wire_code, server.diagnosis(
        f"{label} published wire code {error.get('code')!r}; this revision defines {wire_code} "
        f"for this refusal class"
    )
    message = error.get("message")
    assert isinstance(message, str) and message.strip(), server.diagnosis(
        f"{label} published no message: {error!r}"
    )
    data = error_data(server, error, label=label)
    missing = [name for name in REQUIRED_ERROR_DATA_FIELDS if not data.get(name)]
    assert not missing, server.diagnosis(
        f"{label} omits published error fields {missing}: {data!r}"
    )
    assert data.get("code") == code, server.diagnosis(
        f"{label} published stable code {data.get('code')!r}, expected {code!r}"
    )
    assert data.get("severity") == "error", server.diagnosis(
        f"{label} published severity {data.get('severity')!r}"
    )
    unexpected = [
        name for name in OPTIONAL_ERROR_DATA_FIELDS if name in data and data[name] is None
    ]
    assert not unexpected, server.diagnosis(
        f"{label} sent null identity fields {unexpected}; an absent affected standard must be "
        f"omitted rather than nulled, so a client can tell it apart from an unreported one"
    )
    extra = sorted(set(data) - set(REQUIRED_ERROR_DATA_FIELDS) - set(OPTIONAL_ERROR_DATA_FIELDS))
    assert not extra, server.diagnosis(
        f"{label} published undeclared error data fields {extra}: {data!r}"
    )
    assert_excludes_consumer_content(server, frame, label=label)
    return data


# -- client-advertised roots (ADR 0026 root rules, review F6) -------------------

ROOTS_METHOD = "roots/list"
ROOTS_CAPABILITY: dict[str, Any] = {"listChanged": False}

# A tool call answers once, after at most one roots round trip. Bounded so a
# server that loops asking for roots fails the test instead of hanging the suite.
MAX_BACK_CHANNEL_FRAMES = 8


def open_session_advertising_roots(server: ServerProcess, era: Era) -> dict[str, Any]:
    """Complete the opening contract as a client that declares the roots capability.

    The declaration lives in a different place per era — the classic
    ``initialize`` params, the modern per-request ``_meta`` envelope — which is
    exactly why it is done here rather than by hand at each call site.
    """
    if era.modern:
        return expect_result(
            server, server.call("server/discover", {"_meta": roots_meta(era.revision)})
        )
    frame = server.call(
        "initialize",
        {
            "protocolVersion": era.revision,
            "capabilities": {"roots": ROOTS_CAPABILITY},
            "clientInfo": {"name": "t9-roots-probe", "version": "0"},
        },
    )
    result = expect_result(server, frame)
    server.notify("notifications/initialized", {})
    return result


def roots_meta(revision: str) -> dict[str, Any]:
    """The modern per-request envelope for a client that declares roots."""
    return {**modern_meta(revision), CLIENT_CAPABILITIES_META_KEY: {"roots": ROOTS_CAPABILITY}}


def roots_envelope(era: Era) -> dict[str, Any]:
    """The per-request envelope for a roots-advertising session."""
    return {"_meta": roots_meta(era.revision)} if era.modern else {}


def assert_stdout_is_protocol_only_with_roots(server: ServerProcess) -> None:
    """NFR-003/IR-006 for the one session that carries server-initiated requests.

    ``test_transport.assert_stdout_is_protocol_only`` requires every stdout frame
    to be a *response*, which was exact for every session before this one: nothing
    the server sent was ever a request. A ``roots/list`` is a legitimate protocol
    frame that is not a response, so that helper is narrower than the protocol
    here rather than wrong — this is the same check with the one legal
    server-initiated method admitted, and nothing else: a banner, a warning, a
    traceback, or any other outbound method still fails.
    """
    raw = bytes(server.stdout_bytes)
    assert raw == b"" or raw.endswith(b"\n"), server.diagnosis(
        "stdout ended with an unterminated line, so it carried more than framed messages"
    )
    for index, line in enumerate(raw.split(b"\n")):
        if not line:
            continue
        decoded = json.loads(line)
        assert isinstance(decoded, dict), server.diagnosis(f"stdout line {index} is not an object")
        frame = cast("dict[str, Any]", decoded)
        assert frame.get("jsonrpc") == "2.0", server.diagnosis(
            f"stdout line {index} is not a JSON-RPC 2.0 message: {frame!r}"
        )
        if frame.get("method") == ROOTS_METHOD:
            continue
        assert "result" in frame or "error" in frame, server.diagnosis(
            f"stdout line {index} is neither a response nor a {ROOTS_METHOD} request: {frame!r}"
        )


def call_tool_answering_roots(
    server: ServerProcess,
    era: Era,
    *,
    name: str,
    arguments: Mapping[str, Any],
    roots: Sequence[Path] = (),
    raw_result: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], int]:
    """Call one tool and answer every ``roots/list`` the server sends while it runs.

    Returns the response frame and how many times the server asked. The count is
    part of the contract rather than diagnostics: a tool that never asks has not
    applied the narrowing input at all, and one that asks twice — or answers a
    later call from a cached set — is not applying it per call as the record
    requires.

    ``raw_result`` replaces the well-formed answer, so a *successful* but
    malformed ``roots/list`` response can be delivered. The SDK raises
    ``pydantic.ValidationError`` for that case rather than an ``MCPError``, which
    is a different escape path through the adapter (T9.4 Codex GREEN review, F3).
    """
    params = dict(roots_envelope(era))
    params.update({"name": name, "arguments": dict(arguments)})
    identifier = server.request("tools/call", params)
    answer: Mapping[str, Any] = (
        raw_result
        if raw_result is not None
        else {"roots": [{"uri": f"file://{path}"} for path in roots]}
    )
    asked = 0
    for _ in range(MAX_BACK_CHANNEL_FRAMES):
        frame = server.read_frame()
        if frame.get("method") == ROOTS_METHOD:
            asked += 1
            server.send({"jsonrpc": "2.0", "id": frame.get("id"), "result": dict(answer)})
            continue
        assert frame.get("id") == identifier, server.diagnosis(
            f"expected a response to id {identifier}, got {frame!r}"
        )
        return frame, asked
    raise AssertionError(
        server.diagnosis(f"the server never answered {name} after {MAX_BACK_CHANNEL_FRAMES} frames")
    )


def assert_roots_consulted_once(server: ServerProcess, era: Era, asked: int, *, label: str) -> None:
    """Exactly one ``roots/list`` per classic call, and none per modern call.

    Asserted on *every* repository-scoped call rather than on the first
    (T9.4 Codex GREEN review, F4). A per-tool or per-session cache would satisfy
    a first-call-only check while quietly applying a stale advertised set to every
    later call, which is precisely what the alternating root sets below are shaped
    to expose.
    """
    expected = 0 if era.modern else 1
    assert asked == expected, server.diagnosis(
        f"{label}: the server sent {asked} {ROOTS_METHOD} requests, expected {expected}. "
        "Advertised roots are an input to *this* call: the modern stdio context has no "
        "back-channel to ask on, and a classic call that skips the request is reusing an "
        "answer the client gave for a different call"
    )


def assert_unconstrained_baseline(
    server: ServerProcess, frame: Mapping[str, Any], *, name: str, label: str
) -> None:
    """The exact outcome each tool produces for an uninitialized root, unnarrowed.

    Replaces a weaker earlier oracle that only required the refusal *not* to be
    the containment class, which admitted an erroneous ``repo-root-invalid`` or
    ``root-boundary-invalid`` on a call nothing had narrowed (T9.4 Codex GREEN
    review, F1). The baselines are tool-specific because the contract is: EC-005
    binds ``reconcile_preview``, which answers an uninitialized directory with the
    control-plane arm of its envelope, while ``validate_repo`` and ``drift_check``
    keep the facade's structured refusal for a control plane they cannot resolve
    (freeze #6). Both are exactly what the same call produces with no advertised
    roots in play at all.
    """
    if name == RECONCILE_PREVIEW:
        body = structured(server, frame, label=label)
        assert body.get(PREVIEW_SLOT) is None, server.diagnosis(
            f"{label}: an uninitialized root cannot be planned, so no preview may be published"
        )
        snapshot = as_object(body.get(CONTROL_PLANE_SLOT), "the control-plane slot")
        assert snapshot["state"] == StateKind.UNINITIALIZED.value, server.diagnosis(
            f"{label}: expected the EC-005 arm for an uninitialized root; got state "
            f"{snapshot['state']!r}"
        )
        return
    assert_structured_refusal(
        server,
        frame,
        label=label,
        code=CONTROL_PLANE_UNAVAILABLE_CODE,
        wire_code=INVALID_PARAMS,
    )


# -- RED control ---------------------------------------------------------------


def test_provider_backed_fixture_serves_authoritative_results(
    provider_runtime: Path,
    provider_distribution: InstalledDistribution,
    planned_repo: Path,
    degraded_repos: dict[str, Path],
    expected_documents: dict[str, dict[str, Any]],
) -> None:
    """RED control (T9.2): every oracle the acceptance tests cannot reach yet.

    All four acceptance tests below stop at the absent registration, so their
    oracles would be entirely unproven at RED — the failure mode T6.1 and T8.1
    both had to close out of band. Here the same oracles are exercised inside a
    collected test, against the service layer that already exists:

    * the fixture distribution really declares runnable validate/verify/lint and
      drift-check providers, so ``validate_repo`` and ``drift_check`` return
      *non-empty* results rather than trivially equal empty reports;
    * the planned repository really has pending actions, preconditions, and
      staged target bytes, so the preview exclusions are not vacuous;
    * ``drift_check``'s fingerprint is the authoritative executor fingerprint for
      the same plan;
    * every degraded classification really refuses at the facade, which is what
      makes EC-005 a *tool*-layer obligation;
    * the declared mutating and excluded providers never execute, so the
      payload-side sentinels are a usable witness rather than a constant.

    It validates the very documents ``expected_documents`` publishes, rather than
    recomputing them: that fixture is the oracle every parity assertion below
    compares against, so proving *it* is what the control is for.
    """
    facade = oracle_facade(provider_runtime)

    plan = oracle_plan(planned_repo, provider_distribution)
    assert plan.actions, "the fixture repository has no pending actions"
    assert plan.preconditions, "the fixture plan binds no preconditions"
    assert plan.targets, "the fixture plan stages no target bytes"

    preview = as_object(
        expected_documents[RECONCILE_PREVIEW][PREVIEW_SLOT], "the expected preview document"
    )
    assert preview["reconciliation_fingerprint"] == reconciliation_fingerprint(plan)
    assert expected_documents[RECONCILE_PREVIEW][CONTROL_PLANE_SLOT] is None

    validation = expected_documents[VALIDATE_REPO]
    drift = expected_documents[DRIFT_CHECK]
    assert result_identities(validation) == oracle_selection(
        planned_repo, provider_distribution, frozenset({"validate", "verify", "lint"})
    )
    assert result_identities(drift) == oracle_selection(
        planned_repo, provider_distribution, frozenset({"drift-check"})
    )
    assert validation["results"], "no validate/verify/lint provider ran, so parity would be vacuous"
    assert drift["results"], "no drift-check provider ran, so parity would be vacuous"
    assert validation["findings"], "no provider finding was produced"
    assert drift["reconciliation_fingerprint"] == reconciliation_fingerprint(plan)

    # Every degraded classification refuses at the facade: EC-005 is satisfied by
    # the T9 tool composing `inspect_repo`, never by the facade inventing a plan.
    for state, repo in sorted(degraded_repos.items()):
        with pytest.raises(ServiceError):
            facade.reconcile(repo)
        snapshot = dumped(facade.inspect_repo(repo))
        assert snapshot["state"] == state
    assert any(dumped(facade.inspect_repo(repo))["findings"] for repo in degraded_repos.values()), (
        "no degraded fixture carries a control-plane finding, so EC-005's "
        "'returns control-plane findings' would be vacuous"
    )

    assert not mutating_provider_ran(provider_distribution), (
        "a mutating or excluded provider executed during the composite calls, so the "
        "payload-side sentinels cannot witness a refusal before dispatch"
    )
    assert set(APPROVED_OPERATIONS) == {"validate", "verify", "lint", "drift-check"}
    assert authoritative_finding_keys() == field_names(Finding), (
        "the §5.5 Finding field set no longer matches the authoritative finding serializer "
        "under the two declared renames"
    )


# -- frozen acceptance tests ---------------------------------------------------


@pytest.mark.parametrize("era", ERAS, ids=ERA_IDS)
def test_consumer_tools_preserve_typed_service_results(
    provider_runtime: Path,
    provider_distribution: InstalledDistribution,
    planned_repo: Path,
    expected_documents: dict[str, dict[str, Any]],
    era: Era,
) -> None:
    """TC-T9-001 (FR-011, FR-012, FR-013, FR-017, FR-022, IR-003, DR-004, DR-008).

    T9 is a mapping task, so the assertion is equality: each tool's structured
    content must equal the ``McpServiceFacade`` answer for the same repository,
    node for node, after masking the one field DR-008 excludes from identity.
    A re-serialized, field-dropped, or summarized copy is not the same result —
    the T7/T8 parity precedent, which the GREEN reviews upheld as "strong,
    appropriately adapter-level".

    Three further obligations ride on the same calls.

    *Fingerprint preservation (FR-017).* ``drift_check``'s
    ``reconciliation_fingerprint`` must equal the fingerprint the executor
    computes for the plan the authoritative planner produces over that
    repository, so the protocol cannot introduce a competing plan identity.

    *Typed results (FR-022).* Each answer is validated against the output schema
    that tool advertised, and the schema itself against the JSON Schema
    metaschema: a declared ``{}`` satisfies "has an output schema" while typing
    nothing.

    *Content exclusion (FR-028).* No planted secret, credential, private key, or
    unrelated file content appears in the complete rendered frame of any answer —
    structured content, human text, and bounded provider diagnostics alike.

    Masking is positional and minimal: only each provider result's own
    ``diagnostics`` field, which DR-008 excludes from identity, is replaced before
    comparison. Every nested value a provider declared under ``output`` — including
    one that happens to be named ``diagnostics`` — is compared verbatim, and the
    number of masked positions is asserted so the mask cannot quietly widen (T9.2
    Codex RED review, F3).

    Both eras are exercised: a result surface that works in one and not the
    other is broken for half the client matrix.
    """
    require_mcp_subcommand()
    plan = oracle_plan(planned_repo, provider_distribution)
    fingerprint = reconciliation_fingerprint(plan)

    with resource_session(era, runtime_root=provider_runtime, label="consumer-parity") as (
        server,
        _,
    ):
        entries = require_consumer_tools(server, era)
        for name in CONSUMER_TOOLS:
            declared = assert_valid_schema(
                server, entries[name].get("outputSchema"), label=f"{name}'s output schema"
            )
            frame = call_tool(
                server, era, name=name, arguments={REPO_ROOT_ARGUMENT: str(planned_repo)}
            )
            body = structured(server, frame, label=name)
            expected = expected_documents[name]
            assert without_diagnostics(body) == without_diagnostics(expected), server.diagnosis(
                f"{name} does not preserve the exact service result.\n"
                f"served:   {rendered(without_diagnostics(body))}\n"
                f"expected: {rendered(without_diagnostics(expected))}"
            )
            assert masked_positions(body) == masked_positions(expected), server.diagnosis(
                f"{name} published a different number of provider results than the service, so "
                "the diagnostics mask covered a different set of positions"
            )
            assert nested_diagnostics(body) == nested_diagnostics(expected), server.diagnosis(
                f"{name} altered a provider-declared nested diagnostics value; DR-008 excludes "
                "only the ProviderOperationResult field from identity"
            )
            served_diagnostics = result_diagnostics(body)
            assert all(isinstance(item, str) for item in served_diagnostics), server.diagnosis(
                f"{name} published a non-string diagnostics value: {served_diagnostics!r}"
            )
            assert_conforms(server, body, declared, label=name)
            assert_excludes_consumer_content(server, frame, label=name)

            if name == DRIFT_CHECK:
                assert body["reconciliation_fingerprint"] == fingerprint, server.diagnosis(
                    f"{DRIFT_CHECK} published a fingerprint the executor did not compute; "
                    "FR-017 forbids a competing plan identity"
                )
                assert body["repo_root"] == ".", server.diagnosis(
                    f"{DRIFT_CHECK} must normalize the root identity to '.'; got "
                    f"{body['repo_root']!r}"
                )
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


@pytest.mark.parametrize("era", ERAS, ids=ERA_IDS)
def test_preview_preserves_control_plane_schema(
    provider_runtime: Path,
    provider_distribution: InstalledDistribution,
    planned_repo: Path,
    era: Era,
) -> None:
    """TC-T9-004 (DR-004): the preview is the plan's own serialization, plus its identity.

    DR-004 is explicit — dry-run results "reuse stable control-plane
    serialization; no parallel MCP plan schema" — so the assertion is equality
    against ``ReconciliationPlan.to_jsonable()`` itself, with
    ``reconciliation_fingerprint`` added, for the plan the authoritative
    ``build_planner_request``/``plan_reconciliation`` pair produces over the same
    repository. Compared as serialized JSON rather than as Python objects,
    because the authoritative projection still contains dataclass tuples that
    render as arrays: object equality would compare representation rather than
    the stable wire contract (the T3 rule for the same claim).

    The field *set* is compared as well as the values, so a dropped, renamed, or
    added field fails even when its value happens to be empty.

    And the executor-only staged bytes stay executor-only: the plan's proposed
    target content must appear nowhere in the whole protocol frame. That is the
    T3 exclusion carried to the protocol layer, where a mapper could have
    reintroduced it.

    **The declared schema must enforce "exactly one non-null", not merely
    describe it.** §5.5 freezes the envelope as two required slots of which
    exactly one is populated; two independently nullable properties would also
    validate a both-null document (an answer carrying nothing) and a
    both-populated one (a preview *and* the state saying no preview exists). Both
    invalid combinations are therefore constructed here and required to fail the
    tool's *own advertised* schema — the T8 out-of-band falsification precedent,
    which is what turns "the served document validates" into evidence (T9.4 Codex
    GREEN review, F2).
    """
    require_mcp_subcommand()
    plan = oracle_plan(planned_repo, provider_distribution)
    jsonable = plan.to_jsonable()
    fingerprint = reconciliation_fingerprint(plan)
    assert plan.targets, "the fixture plan stages no bytes, so the exclusion below is vacuous"
    staged = plan.targets[0].content.decode("utf-8")

    with resource_session(era, runtime_root=provider_runtime, label="preview-schema") as (
        server,
        _,
    ):
        entry = require_consumer_tools(server, era)[RECONCILE_PREVIEW]
        declared = assert_valid_schema(
            server, entry.get("outputSchema"), label=f"{RECONCILE_PREVIEW}'s output schema"
        )
        frame = call_tool(
            server,
            era,
            name=RECONCILE_PREVIEW,
            arguments={REPO_ROOT_ARGUMENT: str(planned_repo)},
        )
        body = structured(server, frame, label=RECONCILE_PREVIEW)
        preview = as_object(body.get(PREVIEW_SLOT), f"the {RECONCILE_PREVIEW} preview slot")

        assert body.get(CONTROL_PLANE_SLOT) is None, server.diagnosis(
            "an initialized repository is planned, so the control-plane slot must be null; got "
            f"{body.get(CONTROL_PLANE_SLOT)!r}"
        )
        assert set(preview) == set(jsonable) | {"reconciliation_fingerprint"}, server.diagnosis(
            f"the preview field set differs from ReconciliationPlan.to_jsonable() plus the "
            f"fingerprint: served {sorted(preview)}"
        )
        assert json.dumps(preview, sort_keys=True) == json.dumps(
            {**jsonable, "reconciliation_fingerprint": fingerprint}, sort_keys=True
        ), server.diagnosis(
            f"{RECONCILE_PREVIEW} does not serve the authoritative plan serialization"
        )
        assert staged not in rendered(frame), server.diagnosis(
            "the plan's executor-only proposed bytes reached the protocol result"
        )
        assert_conforms(server, body, declared, label=RECONCILE_PREVIEW)

        # Falsification, both directions. The served document validates above;
        # these two must not, or the advertised schema is describing the
        # invariant rather than enforcing it.
        snapshot = dumped(oracle_facade(provider_runtime).inspect_repo(planned_repo))
        for invalid, why in (
            ({PREVIEW_SLOT: None, CONTROL_PLANE_SLOT: None}, "carries neither arm"),
            (
                {PREVIEW_SLOT: preview, CONTROL_PLANE_SLOT: snapshot},
                "carries both arms at once",
            ),
        ):
            assert schema_rejects(declared, invalid), server.diagnosis(
                f"the advertised {RECONCILE_PREVIEW} output schema accepts a document that "
                f"{why}; §5.5 freezes exactly one non-null slot"
            )
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


def test_provider_tools_enforce_exact_dispatch_root_allowlist_and_content_exclusion(
    provider_runtime: Path,
    provider_distribution: InstalledDistribution,
    planned_repo: Path,
) -> None:
    """TC-T9-002 (FR-014, FR-024, FR-028, IR-009): the allowlist, through the protocol.

    ADR 0025 names no generic helper tool with an exact schema, so plan:439
    registers none and there is no dispatch tool to point an out-of-set operation
    at. The allowlist therefore has to be proven where it is actually reachable,
    in three places (freeze #5).

    *The surface.* No advertised tool declares an input property other than the
    explicit ``repo_root`` and the fallback read's canonical URI, so no
    operation, provider id, payload version, or effect can be named through the
    protocol at all. This is the strongest form of "undeclared and mutating
    operations are rejected before dispatch": they are unrequestable.

    *The selection.* Each composite tool's returned result identities must equal
    the ordered selection the authoritative resolution yields for its own
    operation set — validate/verify/lint for ``validate_repo``, drift-check for
    ``drift_check``. A widened, narrowed, or duplicated dispatch fails on
    sequence equality. The fixture distribution deliberately also declares
    ``fix-alpha`` (``mutation-plan`` effect) and ``semantic-review-alpha``
    (``findings`` effect, excluded by SPEC-RD01 OQ-006), so the selection is a
    real filter rather than "everything declared".

    *The refusal before worker creation.* Those two providers write payload-side
    sentinels when their bytes execute, so their absence after every call is a
    witness that no worker was ever created for them — an absence claim with
    evidence, and one that is independent of the repository no-write assertions
    in ``security/test_no_writes.py``.

    Root containment and content exclusion ride on the same calls: the reported
    root is the normalized ``.`` identity, every finding path is repository
    relative with no traversal or absolute form, and none of the four planted
    exclusion classes appears in any answer or in any refusal. The *read* half of
    FR-028 is asserted separately, in
    ``test_consumer_tools_reach_facts_only_through_the_facade``, where the
    filesystem audit can see it.

    Modern era only (freeze #9): each call spawns one worker process per
    applicable declaration, and the classic era adds no mapping question
    TC-T9-001 does not already cover in both eras.
    """
    require_mcp_subcommand()
    era = MODERN_ERA
    expected_selection = {
        VALIDATE_REPO: oracle_selection(
            planned_repo, provider_distribution, frozenset({"validate", "verify", "lint"})
        ),
        DRIFT_CHECK: oracle_selection(
            planned_repo, provider_distribution, frozenset({"drift-check"})
        ),
    }
    assert all(expected_selection.values()), (
        "the fixture resolution selects no approved provider, so exact-dispatch equality "
        "would hold vacuously"
    )

    with resource_session(era, runtime_root=provider_runtime, label="consumer-dispatch") as (
        server,
        _,
    ):
        require_consumer_tools(server, era)

        # The surface half: nothing a caller can say names an operation.
        for entry in list_tools(server, era):
            name = str(entry.get("name"))
            properties = set(input_properties(server, entry))
            assert properties <= ALLOWED_INPUT_PROPERTIES, server.diagnosis(
                f"{name} declares input properties outside the v1 set: {sorted(properties)}"
            )
            offending = sorted(
                item
                for item in properties
                if any(token in item.lower() for token in DISPATCH_ARGUMENT_TOKENS)
            )
            assert not offending, server.diagnosis(
                f"{name} lets a caller name a provider operation or payload identity: {offending}"
            )
            if name in CONSUMER_TOOLS:
                assert required_names(entry) == [REPO_ROOT_ARGUMENT], server.diagnosis(
                    f"FR-024 requires an explicit {REPO_ROOT_ARGUMENT!r}; {name} requires "
                    f"{required_names(entry)}"
                )

        for name, expected in sorted(expected_selection.items()):
            frame = call_tool(
                server, era, name=name, arguments={REPO_ROOT_ARGUMENT: str(planned_repo)}
            )
            body = structured(server, frame, label=name)
            assert_excludes_consumer_content(server, frame, label=name)
            assert result_identities(body) == expected, server.diagnosis(
                f"{name} did not dispatch exactly the authoritative applicable selection.\n"
                f"served:   {result_identities(body)}\nexpected: {expected}"
            )
            assert body["repo_root"] == ".", server.diagnosis(
                f"{name} must normalize the root identity to '.'; got {body['repo_root']!r}"
            )
            paths = finding_paths(body)
            assert paths, server.diagnosis(f"{name} published no finding path to contain")
            escaping = sorted(
                path for path in paths if Path(path).is_absolute() or ".." in Path(path).parts
            )
            assert not escaping, server.diagnosis(
                f"{name} published finding paths outside the repository: {escaping}"
            )

        assert not mutating_provider_ran(provider_distribution), server.diagnosis(
            "a mutating or excluded provider executed through the composite tools; ADR 0025 "
            "refuses every unapproved operation before worker creation"
        )

        # Refusals leak nothing either: a structured error may not become a
        # filesystem or content oracle. Their full projection is asserted by
        # `test_consumer_tool_refusals_preserve_service_errors_in_both_eras`.
        for arguments, why in (
            ({}, "no repo_root at all"),
            ({REPO_ROOT_ARGUMENT: str(planned_repo / "no-such-repository")}, "a missing root"),
            ({REPO_ROOT_ARGUMENT: f"{planned_repo}{NUL}"}, "a NUL-bearing root"),
            ({REPO_ROOT_ARGUMENT: 17}, "a non-string root"),
        ):
            for name in CONSUMER_TOOLS:
                frame = call_tool(server, era, name=name, arguments=arguments)
                refusal_of(server, frame, why=f"{name} with {why}")
                assert_excludes_consumer_content(server, frame, label=f"{name} refusing {why}")
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


def test_consumer_tool_metadata_is_compact_and_read_only(provider_runtime: Path) -> None:
    """TC-T9-005 (FR-023, NFR-012): the advertised metadata, snapshotted and reviewed.

    Tool metadata is paid on every session before a single call, so FR-023 wants
    it "concise, unambiguous, and test-reviewed" and its acceptance is that
    "tests snapshot the supported-client tool metadata". This is that snapshot
    for the three tools T9 owns, composed with T8's reviewed constant rather than
    forking it: the whole advertised surface must equal
    ``{**EXPECTED_TOOL_METADATA, **EXPECTED_CONSUMER_TOOL_METADATA}``, field for
    field.

    Whole-surface equality is what an invented budget could not give, and the
    numbers an earlier task tried are deliberately not reintroduced (T8.2 Codex
    RED review, F1/F2). A description that had grown into documentation, a
    retyped schema, a dropped authority sentence, a seventh tool, and a schema
    that enumerated installed standard ids all change this constant, and changing
    it is a review.

    The constants are then held to FR-023's own three obligations — purpose,
    input authority, and read-only effect — so a future edit to the snapshot has
    to keep saying what the requirement demands. Protocol annotations are not
    asserted: FR-023 places the read-only claim in the description and ADR 0026
    freezes behaviour rather than annotation presence.
    """
    require_mcp_subcommand()
    era = MODERN_ERA
    reviewed = {**EXPECTED_TOOL_METADATA, **EXPECTED_CONSUMER_TOOL_METADATA}
    with resource_session(era, runtime_root=provider_runtime, label="consumer-metadata") as (
        server,
        _,
    ):
        require_consumer_tools(server, era)
        entries = list_tools(server, era)
        served = {str(entry.get("name")): dict(entry) for entry in entries}
        assert len(served) == len(entries), server.diagnosis(
            f"a tool is advertised more than once: {tool_names(entries)}"
        )
        assert served == reviewed, server.diagnosis(
            "the advertised tool metadata is not the reviewed FR-023 snapshot.\n"
            f"served:   {rendered(served)}\nreviewed: {rendered(reviewed)}"
        )
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)

    for name, metadata in EXPECTED_CONSUMER_TOOL_METADATA.items():
        description = str(metadata["description"])
        lowered = description.lower()
        assert "\n" not in description.strip(), (
            f"{name}'s reviewed description is multi-paragraph; a tool picker shows one line"
        )
        missing = [
            claim for claim in REVIEWED_CONSUMER_DESCRIPTION_CLAIMS[name] if claim not in lowered
        ]
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
        assert name not in FORBIDDEN_TOOL_NAMES
        shaped = [token for token in FORBIDDEN_TOOL_TOKENS if token in name]
        assert not shaped, f"{name} names a per-standard or recommending surface the plan forbids"


# -- EC-005, composition, containment, and the registry contract ----------------


def test_reconcile_preview_composes_inspect_repo_for_a_degraded_control_plane(
    provider_runtime: Path,
    degraded_repos: dict[str, Path],
) -> None:
    """SPEC-MS01 §10.3 EC-005: findings at the tool layer while the facade raises.

    The record is explicit — a repository lacking ``.standards/config.toml``, its
    catalog, or its lock is a case where "``reconcile_preview`` returns
    control-plane findings" — and the T3.3 arbitration put that obligation on the
    tool: ``McpServiceFacade.reconcile`` raises for every non-``initialized``
    classification, because a preview exists only where the authoritative planner
    produced a plan and fabricating one would mean inventing a schema-invalid
    envelope and a non-executor fingerprint.

    So the composition is asserted, for every classification that cannot be
    planned (freeze #1):

    * the call *succeeds*, because EC-005's verb is "returns";
    * the preview slot is null and the control-plane slot carries exactly
      ``McpServiceFacade.inspect_repo(...).model_dump(mode="json")``, node for
      node — the authoritative snapshot published verbatim, not a summary of it;
    * each published finding's key set is the §5.5 ``Finding`` field set, which
      is itself derived from ``findings_to_jsonable``'s own key set under the two
      declared renames, so the shape stays the control plane's rather than the
      adapter's;
    * the facade traffic for that call *includes* ``inspect_repo`` and *excludes*
      ``reconcile``. The exclusion is the freeze's teeth: selecting the slot by
      the authoritative classification, rather than by calling ``reconcile`` and
      reading the code off the ``ServiceError`` it raises, is what stops lock
      contention and planner refusals on an initialized repository from
      degrading into a "findings" answer.

    ``validate_repo`` and ``drift_check`` are asserted to keep refusing on the
    same repositories (freeze #6): EC-005 names ``repo_inspect`` and
    ``reconcile_preview`` and no other tool, and a validation report over a
    repository whose resolution could not be computed would have to invent the
    selection it reports on.
    """
    require_mcp_subcommand()
    era = MODERN_ERA
    facade = oracle_facade(provider_runtime)
    expected_snapshots = {
        state: dumped(facade.inspect_repo(repo)) for state, repo in degraded_repos.items()
    }
    assert any(snapshot["findings"] for snapshot in expected_snapshots.values()), (
        "no degraded fixture carries a control-plane finding, so this test would be vacuous"
    )

    script = spy_launch(provider_runtime / "project_standards")
    with resource_session(era, runtime_root=provider_runtime, label="ec-005", script=script) as (
        server,
        _,
    ):
        require_consumer_tools(server, era)
        for state, repo in sorted(degraded_repos.items()):
            before = len(facade_calls(server))
            body = structured(
                server,
                call_tool(
                    server, era, name=RECONCILE_PREVIEW, arguments={REPO_ROOT_ARGUMENT: str(repo)}
                ),
                label=f"{RECONCILE_PREVIEW}({state})",
            )
            server.drain(0.5)
            calls = facade_calls(server)[before:]

            assert body.get(PREVIEW_SLOT) is None, server.diagnosis(
                f"the {state} repository cannot be planned, so no preview may be published: "
                f"{body.get(PREVIEW_SLOT)!r}"
            )
            snapshot = as_object(body.get(CONTROL_PLANE_SLOT), "the control-plane slot")
            assert snapshot == expected_snapshots[state], server.diagnosis(
                f"{RECONCILE_PREVIEW} does not publish the authoritative inspect_repo snapshot "
                f"for the {state} repository"
            )
            assert snapshot["state"] == state
            for finding in cast("list[object]", snapshot["findings"]):
                published = as_object(finding, "a control-plane finding")
                assert set(published) == authoritative_finding_keys(), server.diagnosis(
                    f"a {state} finding is not the authoritative finding shape: {sorted(published)}"
                )
            assert "inspect_repo" in calls, server.diagnosis(
                f"{RECONCILE_PREVIEW} answered the {state} repository without composing "
                f"inspect_repo: {calls}"
            )
            assert "reconcile" not in calls, server.diagnosis(
                f"{RECONCILE_PREVIEW} called the facade's reconcile for the {state} repository, "
                "which cannot produce a plan; the slot is chosen by the authoritative "
                f"classification, not by reading a ServiceError code: {calls}"
            )

            for name in (VALIDATE_REPO, DRIFT_CHECK):
                refusal_of(
                    server,
                    call_tool(server, era, name=name, arguments={REPO_ROOT_ARGUMENT: str(repo)}),
                    why=f"{name} against the {state} repository",
                )
        assert server.finish() == 0


def test_consumer_tools_reach_facts_only_through_the_facade(
    provider_runtime: Path,
    planned_repo: Path,
) -> None:
    """Plan T9: every handler calls the facade, and performs no selection of its own.

    Invisible from the wire — a tool that assembled the same answer from its own
    reads and its own single dispatches looks identical to one that delegated —
    so it is observed at two boundaries at once, exactly as T8 observes the
    discovery tools.

    *The service boundary*, through the recording facade. Each call's facade
    traffic must fall inside :data:`ALLOWED_FACADE_CALLS` and must include the
    one authority that reloads current consumer state for that answer. Two
    exclusions carry the requirement: ``resource`` would mean a tool reached for
    payload bytes, and ``invoke_read_provider`` would mean the adapter performed
    the provider selection plan:439 keeps in the service layer — "without
    performing provider selection or drift interpretation in ``mcp_server``"
    (freeze #11).

    *The filesystem boundary*, through T8's audit prologue. Facade traffic alone
    cannot falsify the claim in the direction that matters: a tool with its own
    reader records *no* facade call, which a call-counting oracle reads as
    success. No watched open in any window may be attributed to the adapter.

    FR-028's *read* half is asserted here rather than in TC-T9-002, because this
    is the launch that can see it: none of the four planted exclusion files may
    be opened by the server process at all. The bound is recorded rather than
    hidden — the provider worker is a separate interpreter, so its reads are not
    visible to this hook; what constrains the worker is that it receives only the
    resolved root and typed empty input, and that its results carry none of the
    sentinels.
    """
    require_mcp_subcommand()
    era = MODERN_ERA
    package_root = provider_runtime / "project_standards"
    watched = [*(package_root / name for name in FIXTURE_SUBTREES), planned_repo.parent]
    script = audited_spy_launch(package_root, watch=watched)
    excluded_paths = {str(planned_repo / relative) for relative, _ in EXCLUDED_CONTENT}

    with resource_session(
        era, runtime_root=provider_runtime, label="consumer-spy", script=script
    ) as (server, _):
        require_consumer_tools(server, era)
        for name in CONSUMER_TOOLS:
            before_calls = len(facade_calls(server))
            before_opens = len(audited_opens(server))
            structured(
                server,
                call_tool(
                    server, era, name=name, arguments={REPO_ROOT_ARGUMENT: str(planned_repo)}
                ),
                label=name,
            )
            server.drain(0.5)
            calls = facade_calls(server)[before_calls:]
            opens = audited_opens(server)[before_opens:]

            unexpected = sorted(set(calls) - ALLOWED_FACADE_CALLS[name])
            assert not unexpected, server.diagnosis(
                f"{name} reached facade methods it may not: {unexpected} (recorded {calls})"
            )
            assert REQUIRED_FACADE_CALL[name] in calls, server.diagnosis(
                f"{name} answered without calling the facade's {REQUIRED_FACADE_CALL[name]}: "
                f"{calls}"
            )
            adapter_reads = opens_by_layer(opens, "adapter")
            assert not adapter_reads, server.diagnosis(
                f"{name} opened watched files itself instead of delegating: {adapter_reads}"
            )
            leaked = sorted(
                str(record.get("path"))
                for record in opens
                if str(record.get("path")) in excluded_paths
            )
            assert not leaked, server.diagnosis(
                f"{name} read excluded consumer content that FR-028 forbids reading: {leaked}"
            )
        assert server.finish() == 0


def test_consumer_tools_containment_follows_the_launch_boundary(
    provider_runtime: Path,
    planned_repo: Path,
    tmp_path: Path,
) -> None:
    """FR-024 / ADR 0026: the configured boundary narrows all three tools, and only narrows.

    T8 closed the path from the launch option to a protocol call for
    ``repo_inspect``; the same path must hold for every repository-scoped tool,
    because a boundary that constrained one tool and not another would be no
    boundary at all.

    Three observations, because "refused" alone would not distinguish the
    boundary from an ordinary bad root:

    * inside the boundary, the root is answered normally;
    * outside it, every consumer tool refuses it;
    * on a second server launched with no boundary, that *same* root is answered
      normally — by the EC-005 branch, since it is an uninitialized directory,
      which is what makes the refusal attributable to the boundary rather than to
      the root.

    The out-of-boundary refusal code must also differ from the missing-root
    class, so the two failure taxonomies cannot silently collapse into one.
    """
    require_mcp_subcommand()
    era = MODERN_ERA
    option = boundary_option_name(require_mcp_subcommand())
    boundary = planned_repo.parent
    outside = tmp_path / "elsewhere"
    outside.mkdir()

    script = cli_launch_with([option, str(boundary)])
    with resource_session(
        era, runtime_root=provider_runtime, label="consumer-boundary", script=script
    ) as (server, _):
        require_consumer_tools(server, era)
        inside = structured(
            server,
            call_tool(
                server,
                era,
                name=RECONCILE_PREVIEW,
                arguments={REPO_ROOT_ARGUMENT: str(planned_repo)},
            ),
            label="an in-boundary root",
        )
        assert inside.get(PREVIEW_SLOT) is not None

        for name in CONSUMER_TOOLS:
            refused = refusal_of(
                server,
                call_tool(server, era, name=name, arguments={REPO_ROOT_ARGUMENT: str(outside)}),
                why=f"{name} against a root outside {boundary}",
            )
            missing = refusal_of(
                server,
                call_tool(
                    server,
                    era,
                    name=name,
                    arguments={REPO_ROOT_ARGUMENT: str(boundary / "no-such-repository")},
                ),
                why=f"{name} against a nonexistent root inside the boundary",
            )
            assert service_code(refused) != service_code(missing), server.diagnosis(
                f"{name}: an out-of-boundary root and a nonexistent root are different failures, "
                f"so they may not share a stable code: both reported {service_code(refused)!r}"
            )
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)

    with resource_session(era, runtime_root=provider_runtime, label="consumer-unbounded") as (
        server,
        _,
    ):
        require_consumer_tools(server, era)
        unbounded = structured(
            server,
            call_tool(
                server, era, name=RECONCILE_PREVIEW, arguments={REPO_ROOT_ARGUMENT: str(outside)}
            ),
            label="the same root with no boundary configured",
        )
        snapshot = as_object(unbounded.get(CONTROL_PLANE_SLOT), "the control-plane slot")
        assert snapshot["state"] == StateKind.UNINITIALIZED.value, server.diagnosis(
            "the out-of-boundary root must be an ordinary answerable directory, or its refusal "
            "above proved nothing about the boundary"
        )
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


@pytest.mark.parametrize("matrix_name", ("recorded", "all-direct"))
def test_instructions_publish_the_frozen_six_tool_text(
    provider_runtime: Path, matrix_name: str
) -> None:
    """ADR 0026 (2026-07-30 amendment): the frozen text binds per session registry.

    The 2026-07-29 amendment made the record's draft text binding at the task
    that completes the registry it describes — this one. The 2026-07-30
    amendment, from this task's own RED review, settles what "binding" means when
    the registry is matrix-gated: a process registering all six serves the
    six-tool text; a process whose matrix omits the ``standard_read`` fallback
    serves *the same text* with the enumeration reduced to its actual registry —
    "the count word and the enumeration shrink, nothing else changes".

    The earlier reading — one matrix-stable string naming six tools in every
    session — is superseded and is the change this test exists to carry. It
    required a session that registers five tools to advertise six, which
    TC-T5-002, the T6.4 "may not promise" rule, and ADR 0026's
    capability/registration equivalence all forbid. Static-per-process survives:
    the rendering is fixed at construction from the T1 evidence matrix, which is
    recorded evidence rather than a knob.

    Both renderings are therefore pinned, each against the registry its own
    session actually advertises, and the truthfulness helper — whose "names tools
    this server does not register" rule was the residual the first revision could
    not satisfy — is run in *both* configurations.
    """
    require_mcp_subcommand()
    era = MODERN_ERA
    assert instructions_for(INSTRUCTIONS_TOOL_ORDER) == FROZEN_SIX_TOOL_INSTRUCTIONS, (
        "the rendering generator no longer reproduces the record's own text, so the reduced "
        "rendering it derives cannot be trusted either"
    )
    named = sorted(name for name in FROZEN_V1_TOOLS if name in FROZEN_SIX_TOOL_INSTRUCTIONS)
    assert named == sorted(FROZEN_V1_TOOLS), (
        "the frozen text no longer names ADR 0026's whole v1 registry, so pinning it would "
        f"prove nothing: {named}"
    )

    module = tools_module()
    evidence = client_matrix_evidence(module)
    assert evidence == FROZEN_CLIENT_MATRIX, (
        "the client matrix is no longer the frozen T1 evidence; refresh T1 rather than this test"
    )

    package_root = provider_runtime / "project_standards"
    if matrix_name == "recorded":
        script = matrix_launch(package_root, evidence)
        expected_registry = set(FROZEN_V1_TOOLS)
    else:
        script = matrix_launch(package_root, dict.fromkeys(evidence, True))
        expected_registry = set(FROZEN_V1_TOOLS) - {STANDARD_READ}

    with resource_session(
        era, runtime_root=provider_runtime, label=f"instructions-{matrix_name}", script=script
    ) as (server, result):
        capabilities = declared_capabilities(result)
        reachable = assert_capabilities_match_reachable_registrations(
            server, capabilities, envelope=era.envelope
        )
        advertised = set(tool_names(list_tools(server, era)))
        assert advertised == expected_registry, server.diagnosis(
            f"the {matrix_name} matrix must register {sorted(expected_registry)}; advertised "
            f"{sorted(advertised)}"
        )
        served = assert_instructions_are_truthful(server, result, reachable)
        assert served == instructions_for(sorted(advertised)), server.diagnosis(
            f"the served instructions are not ADR 0026's rendering for this session's registry.\n"
            f"served:   {served!r}\nexpected: {instructions_for(sorted(advertised))!r}"
        )
        if matrix_name == "recorded":
            assert served == FROZEN_SIX_TOOL_INSTRUCTIONS, server.diagnosis(
                "a session registering all six must serve the record's text verbatim"
            )
        else:
            assert STANDARD_READ not in served, server.diagnosis(
                f"the reduced rendering still names {STANDARD_READ}, which this session does "
                "not register"
            )
            assert (
                served.replace("Five", "Six").replace(
                    "standards_list, repo_inspect", "standards_list, standard_read, repo_inspect"
                )
                == FROZEN_SIX_TOOL_INSTRUCTIONS
            ), server.diagnosis(
                "the reduced rendering changed something other than the count word and the "
                f"enumeration:\n{served!r}"
            )
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


@pytest.mark.parametrize("era", ERAS, ids=ERA_IDS)
def test_registered_consumer_tools_keep_the_transport_capability_contract(
    provider_runtime: Path, era: Era
) -> None:
    """FR-025/IR-008/DR-007: the last three tools complete the registry, not the promises.

    T5 asserts an equivalence between declared capabilities and reachable
    registrations rather than an emptiness, so every task that registers
    something reruns it against its own server. Here that means: the advertised
    set is exactly ADR 0026's frozen six — the point at which "advertised tools
    are a subset of the frozen registry" becomes an equality — prompts still
    absent, ``listChanged`` still false, ``subscribe`` still absent, and the
    subscription methods still unserved for a registration set the record fixes
    at process start.
    """
    require_mcp_subcommand()
    with resource_session(era, runtime_root=provider_runtime, label="consumer-capability") as (
        server,
        result,
    ):
        capabilities = declared_capabilities(result)
        reachable = assert_capabilities_match_reachable_registrations(
            server, capabilities, envelope=era.envelope
        )
        assert_no_write_surface(server, reachable)
        assert_no_list_change_promises(capabilities)
        require_consumer_tools(server, era)
        advertised = set(tool_names(list_tools(server, era)))
        assert advertised == set(FROZEN_V1_TOOLS), server.diagnosis(
            f"the v1 registry is complete at T9; advertised {sorted(advertised)}"
        )
        assert STANDARDS_LIST in advertised and REPO_INSPECT in advertised
        assert capabilities.get("prompts") is None, server.diagnosis(
            "T9 approves no prompt role, so the prompts capability must stay absent"
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


# -- refusal projection and client-advertised roots ----------------------------


@pytest.mark.parametrize("era", ERAS, ids=ERA_IDS)
def test_consumer_tool_refusals_preserve_service_errors_in_both_eras(
    provider_runtime: Path, planned_repo: Path, era: Era
) -> None:
    """FR-025/NFR-004/IR-002: every refusal, in both eras, field by field.

    The first revision of this suite accepted "either carrier the protocol
    allows" and never reached a wire code or a published field, so a mapping that
    dropped the remediation, invented a code, or answered a 2025-06-18 client with
    a code that revision does not define would have passed (T9.2 Codex RED review,
    F5). Every refusal class a consumer tool can produce is therefore asserted
    end to end: the JSON-RPC error carrier, the exact wire code for the negotiated
    revision, a non-empty message, and the complete ``ServiceError`` projection —
    stable code, severity, remediation, and the affected path/standard fields
    omitted rather than nulled when the failure has none.

    **Which classes are era-dependent, and which are not.** ``transport`` maps
    exactly one class by revision: a *canonical* address naming something the
    installed catalog does not declare is ``-32002`` through 2025-11-25 and
    ``INVALID_PARAMS`` at 2026-07-28. No repository-scoped refusal is in that
    class — a bad root, an out-of-bounds root, and a malformed argument set are
    bad *parameters* in every revision, and inventing a not-found taxonomy for
    them would be a new mapping this task has no authority to add. So the
    repository refusals are asserted to be revision-stable ``INVALID_PARAMS``, and
    the era-dependent branch is proven live *in the same session* by the one
    refusal that does belong to it: an undeclared but canonical ``standards://``
    address through ``standard_read``. Without that control, "these codes do not
    vary by era" would be indistinguishable from "this server has no era-aware
    mapping at all".
    """
    require_mcp_subcommand()
    with resource_session(era, runtime_root=provider_runtime, label="consumer-refusals") as (
        server,
        _,
    ):
        require_consumer_tools(server, era)

        for name in CONSUMER_TOOLS:
            for arguments, code, label in (
                # An *absent* root is a root-input failure, not an argument-shape
                # one: `tool-arguments-invalid` covers what is refused before any
                # root is parsed — an argument the tool does not declare — while
                # the mandatory-argument rule belongs to the same rejection class
                # as a malformed or unusable root, and shares its stable code with
                # the T3 service resolver. Splitting "no root" from "bad root"
                # across two codes would fork one taxonomy for no requirement's
                # benefit (RED-oracle correction at T9.3; see notes.md).
                ({}, ROOT_INVALID_CODE, "no repo_root at all"),
                (
                    {REPO_ROOT_ARGUMENT: str(planned_repo), "operation": "fix"},
                    TOOL_ARGUMENTS_INVALID_CODE,
                    "an undeclared operation argument",
                ),
                (
                    {REPO_ROOT_ARGUMENT: str(planned_repo / "no-such-repository")},
                    ROOT_INVALID_CODE,
                    "a missing root",
                ),
                (
                    {REPO_ROOT_ARGUMENT: f"{planned_repo}{NUL}"},
                    ROOT_INVALID_CODE,
                    "a NUL-bearing root",
                ),
                ({REPO_ROOT_ARGUMENT: 17}, ROOT_INVALID_CODE, "a non-string root"),
                (
                    {REPO_ROOT_ARGUMENT: str(planned_repo.relative_to("/"))},
                    ROOT_INVALID_CODE,
                    "a relative root",
                ),
            ):
                assert_structured_refusal(
                    server,
                    call_tool(server, era, name=name, arguments=arguments),
                    label=f"{name} with {label}",
                    code=code,
                    wire_code=INVALID_PARAMS,
                )

        # An unregistered name is refused by the registry rather than by a
        # handler, and carries this layer's own stable code.
        assert_structured_refusal(
            server,
            call_tool(
                server,
                era,
                name="reconcile_apply",
                arguments={REPO_ROOT_ARGUMENT: str(planned_repo)},
            ),
            label="an unregistered tool name",
            code=TOOL_NOT_FOUND_CODE,
            wire_code=INVALID_PARAMS,
        )

        # The era-dependent branch, proven live on the same connection.
        catalog = oracle_facade(provider_runtime).catalog()
        declared = sorted(declared_resources(catalog))[0]
        undeclared = declared.rsplit("/", 1)[0] + "/no-such-resource"
        expected_wire = INVALID_PARAMS if era.modern else LEGACY_RESOURCE_NOT_FOUND
        assert_structured_refusal(
            server,
            call_tool(server, era, "uri", undeclared, name=STANDARD_READ),
            label="a canonical URI naming an undeclared resource",
            code="resource-not-found",
            wire_code=expected_wire,
        )
        assert server.finish() == 0
        assert_stdout_is_protocol_only(server)


def test_client_roots_probe_observes_the_back_channel_per_era() -> None:
    """RED control (T9.2, review F6): what the SDK actually does with roots, per era.

    The client-root assertions below depend on a server being *able* to ask its
    client for roots. That is not uniformly true, and guessing would have produced
    an oracle that passes for the wrong reason in one era. So a bare SDK server
    that calls ``session.list_roots()`` inside a tool handler is driven from this
    suite's raw client in both eras, and what it measures is frozen here:

    * classic (2025-06-18): the server-to-client ``roots/list`` request reaches the
      client over stdio and the client's answer reaches the handler;
    * modern (2026-07-28): the same call raises ``NoBackChannelError`` — SEP-2577
      deprecates Roots and the stdio transport context carries no back-channel for
      server-initiated requests at all.

    The consequence the adapter must honour, and which the assertions below
    encode: "the client declared roots but none could be fetched" is *no advertised
    set*, not *an empty advertised set*. ``resolve_effective_root`` treats those as
    opposites — ``None`` means unconstrained by advertised roots, ``()`` means the
    client has admitted no repository at all and every root is refused — so
    collapsing them would either widen authority or refuse every modern call.
    """
    for era in ERAS:
        with ServerProcess(BARE_SDK_ROOTS_CONTROL, label=f"roots-control-{era.name}") as server:
            open_session_advertising_roots(server, era)
            frame, asked = call_tool_answering_roots(
                server, era, name="probe", arguments={}, roots=[Path("/tmp")]
            )
            result = expect_result(server, frame)
            blocks = cast("list[object]", result.get("content"))
            text = "".join(
                str(as_object(block, "a content block").get("text", "")) for block in blocks
            )
            if era.modern:
                assert asked == 0, (
                    "2026-07-28 deprecates Roots and its stdio context has no back-channel, so "
                    f"no roots/list may reach the client; the server asked {asked} times"
                )
                assert "NoBackChannelError" in text, (
                    "the modern era must refuse a server-initiated request outright, or the "
                    f"adapter's fallback rule is built on a wrong measurement: {text!r}"
                )
            else:
                assert asked == 1, (
                    f"classic stdio carries the back-channel, so exactly one roots/list was "
                    f"expected; the server asked {asked} times"
                )
                assert "file:///tmp" in text, (
                    f"the client's advertised root did not reach the handler: {text!r}"
                )
            assert server.finish() == 0


@pytest.mark.parametrize("era", ERAS, ids=ERA_IDS)
def test_consumer_tools_narrow_to_client_advertised_roots(
    provider_runtime: Path, planned_repo: Path, tmp_path: Path, era: Era
) -> None:
    """ADR 0026 root rules: advertised roots narrow, and never do anything else.

    T5 proved ``resolve_effective_root`` honours ``client_roots``; T8 closed the
    path from the *launch* option to a protocol call. Nothing closed the path from
    a client's *advertised* roots to one, and the T5.1 notes deferred exactly that
    to this tool layer (T9.2 Codex RED review, F6). The record's rules are
    asserted through all three tools, and every call asserts its own
    ``roots/list`` count (F4) — one per classic call, none per modern call —
    because a per-tool or per-session cache would satisfy a first-call-only check
    while applying a stale advertised set to everything after it.

    * **narrow, positively.** A root inside the advertised set is answered
      normally, so the narrowing input cannot be satisfied by refusing everything.
    * **narrow, negatively.** A root outside every advertised root is refused with
      the containment code — distinct from the missing-root class, so the two
      taxonomies cannot collapse.
    * **an empty advertised set admits nothing.** A client that declares roots and
      then advertises none has admitted no repository, which is the opposite of
      advertising none at all; every call is refused.
    * **never substituted.** A call omitting ``repo_root`` is refused even when the
      advertised set contains exactly one perfectly good repository — the case
      where an implementation that "helpfully" defaulted would look correct.
    * **an unfetchable set narrows nothing.** A malformed ``roots/list`` answer,
      and the modern era's absent back-channel, both leave the explicit root
      authoritative — asserted as each tool's *exact* unconstrained baseline, not
      merely as "some other refusal".

    The advertised set alternates between calls (containing, excluding, empty,
    containing again), so a cached first answer changes a later verdict rather
    than being invisible.

    In the modern era the transport carries no back-channel (see the control
    above), so no advertised set can ever be fetched and every call runs
    unconstrained: the modern branch therefore asserts the same unconstrained
    baselines the classic branch reaches by advertising a containing root. That
    asymmetry is the point of parametrizing this test rather than pinning one era.
    """
    require_mcp_subcommand()
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    boundary = planned_repo.parent

    with ServerProcess(
        CLI_LAUNCH, runtime_root=provider_runtime, label=f"roots-tools-{era.name}"
    ) as server:
        open_session_advertising_roots(server, era)
        require_consumer_tools(server, era)
        for name in CONSUMER_TOOLS:
            # 1. Inside an advertised root: answered normally.
            inside_frame, asked = call_tool_answering_roots(
                server,
                era,
                name=name,
                arguments={REPO_ROOT_ARGUMENT: str(planned_repo)},
                roots=[boundary],
            )
            assert_roots_consulted_once(server, era, asked, label=f"{name} inside")
            structured(server, inside_frame, label=f"{name} inside an advertised root")

            # 2. An unrelated root, advertised: accepted in classic, unfetchable in
            #    modern — and in both the outcome must be this tool's exact
            #    unconstrained baseline for an uninitialized directory.
            baseline_frame, asked = call_tool_answering_roots(
                server,
                era,
                name=name,
                arguments={REPO_ROOT_ARGUMENT: str(outside)},
                roots=[outside],
            )
            assert_roots_consulted_once(server, era, asked, label=f"{name} baseline")
            assert_unconstrained_baseline(
                server, baseline_frame, name=name, label=f"{name} inside its own advertised root"
            )

            # 3. The same root, now outside every advertised root: refused for
            #    containment in classic, unnarrowed (and therefore identical to
            #    case 2) in modern.
            outside_frame, asked = call_tool_answering_roots(
                server,
                era,
                name=name,
                arguments={REPO_ROOT_ARGUMENT: str(outside)},
                roots=[boundary],
            )
            assert_roots_consulted_once(server, era, asked, label=f"{name} outside")
            if era.modern:
                assert_unconstrained_baseline(
                    server, outside_frame, name=name, label=f"{name} with unreachable roots"
                )
            else:
                assert_structured_refusal(
                    server,
                    outside_frame,
                    label=f"{name} outside every advertised root",
                    code=ROOT_OUT_OF_BOUNDS_CODE,
                    wire_code=INVALID_PARAMS,
                )

            # 4. An empty advertised set admits nothing.
            empty_frame, asked = call_tool_answering_roots(
                server,
                era,
                name=name,
                arguments={REPO_ROOT_ARGUMENT: str(planned_repo)},
                roots=[],
            )
            assert_roots_consulted_once(server, era, asked, label=f"{name} empty set")
            if era.modern:
                structured(server, empty_frame, label=f"{name} with no reachable roots")
            else:
                assert_structured_refusal(
                    server,
                    empty_frame,
                    label=f"{name} against an empty advertised set",
                    code=ROOT_OUT_OF_BOUNDS_CODE,
                    wire_code=INVALID_PARAMS,
                )

            # 5. Immediately afterwards, the same root with a *containing* set
            #    must succeed again. A server that cached the refuse-everything
            #    answer from case 4 fails here, which is what makes the per-call
            #    rule falsifiable rather than merely counted.
            recovered_frame, asked = call_tool_answering_roots(
                server,
                era,
                name=name,
                arguments={REPO_ROOT_ARGUMENT: str(planned_repo)},
                roots=[boundary],
            )
            assert_roots_consulted_once(server, era, asked, label=f"{name} after an empty set")
            structured(server, recovered_frame, label=f"{name} after an empty advertised set")

            # 6. A successful but malformed roots/list answer is unfetchable too:
            #    the SDK raises a validation error rather than an MCPError, and
            #    the explicit root must stay authoritative rather than the call
            #    dying (T9.4 Codex GREEN review, F3).
            malformed_frame, asked = call_tool_answering_roots(
                server,
                era,
                name=name,
                arguments={REPO_ROOT_ARGUMENT: str(outside)},
                raw_result={"roots": "not-a-list-of-roots"},
            )
            assert_roots_consulted_once(server, era, asked, label=f"{name} malformed roots")
            assert_unconstrained_baseline(
                server, malformed_frame, name=name, label=f"{name} with a malformed roots answer"
            )

            # 7. Never substituted, in either era: an advertised root that *is* a
            #    repository still cannot supply the mandatory argument.
            missing_frame, asked = call_tool_answering_roots(
                server, era, name=name, arguments={}, roots=[planned_repo]
            )
            assert_roots_consulted_once(server, era, asked, label=f"{name} missing repo_root")
            assert_structured_refusal(
                server,
                missing_frame,
                label=f"{name} with an advertised repository and no repo_root",
                code=ROOT_INVALID_CODE,
                wire_code=INVALID_PARAMS,
            )
        assert server.finish() == 0
        assert_stdout_is_protocol_only_with_roots(server)
