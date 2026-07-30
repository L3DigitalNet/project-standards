"""The complete v1 tool registry (plan T7, T8, T9).

Deliberately SDK-free and repository-free, like every adapter module except
``transport``: each tool's declaration is a plain mapping the transport projects
onto ``types.Tool``, and every fact any of them serves comes from the T6 resource
registry or from ``McpServiceFacade``. Both boundaries are enforced by
``tests/mcp_server/contract/test_import_boundary.py``.

**Six tools, and only one of them is conditional.** ADR 0026 closes the v1
registry at these names; T9 completes it.

* ``standards_list`` (FR-007) — the installed catalog, as the FR-001 masked
  projection. It takes no argument at all: a tool that accepted a standard id
  would be the per-standard surface FR-007 exists to replace.
* ``standard_read`` (FR-008) — the resource-read fallback, registered only when
  the client matrix says a supported primary client needs it.
* ``repo_inspect`` (FR-009) — one consumer repository's authoritative
  control-plane state, for an explicit ``repo_root``.
* ``reconcile_preview`` (FR-011) — the dry-run plan, or the control-plane state
  that explains why no plan exists.
* ``validate_repo`` (FR-012) — the applicable validate/verify/lint provider
  results for one repository.
* ``drift_check`` (FR-013) — reconciliation facts plus applicable drift-check
  results, uninterpreted.

Every requirement above except FR-008 puts its tool in the surface outright, so
the matrix decides the fallback and nothing else — which is why the tools
capability survives the counterfactual matrix in which every client can read
resources directly, where T7's registry emptied entirely.

**Nothing here re-derives a domain fact.** ``standards_list`` takes the FR-001
field mask from
:meth:`~project_standards.mcp_server.resources.ResourceRegistry.catalog_projection`
rather than rebuilding it; the four repository-scoped tools publish
``McpServiceFacade`` DTOs verbatim. That is not stylistic: a second producer of
the catalog projection is how the resource and the tool would come to disagree,
and a second producer of a report is what DR-004 ("no parallel MCP plan schema")
and plan:439 ("without performing provider selection or drift interpretation in
``mcp_server``") forbid outright. No handler names a provider, an operation, or a
payload version, so no unapproved operation is even expressible here.

**One root policy, one place.** Every repository-scoped tool reaches
:func:`~project_standards.mcp_server.repo_access.resolve_effective_root` through
:func:`_resolved_root`: the explicit argument is mandatory, the launch-time
boundary and the client's advertised roots may only narrow, and containment is
decided on resolved paths. A tool that resolved its own root would be a second
place those rules could drift.

**``reconcile_preview`` is the one composed answer**, and its shape is contract:
§5.5 freezes a closed two-slot envelope whose populated slot follows the
*authoritative classification* rather than a caught failure code, because
``McpServiceFacade.reconcile`` raises for a degraded control plane, for lock
contention, and for a planner refusal alike — and only the first is EC-005's
"returns control-plane findings". The other two stay structured refusals.

**Every result is typed and structured, and the human half stays bounded.**
FR-022 requires each v1 tool to declare an output schema and to return
"protocol-supported structured content plus bounded human text where useful", so
:class:`ToolResult` carries both and :data:`ToolEntry.output_schema` is not
optional. Two deliberate restraints in the text half: ``standard_read``'s
structured content publishes the resource's identity and its DR-002 declaration
rather than a second copy of the bytes (they already travel once in the embedded
resource, and duplicating a payload is the "unnecessary verbosity" NFR-012
names), and ``drift_check``'s summary counts what the report carries without
asserting anything about it — a line announcing "no drift" would be the invented
clean-state boolean §5.5 forbids, wearing prose.

**``standard_read`` cannot take a path.** FR-008: the tool "cannot accept
arbitrary paths"; the plan: "with no path argument". The input is one canonical
``standards://`` resource URI and nothing else, which the schema declares and
:func:`invoke_tool` enforces — a filesystem path reaching the registry is refused
by the same grammar that refuses it on ``resources/read``. It also delegates
rather than reads: plan:406 forbids "a second resource-reading implementation", so
the call goes to the same :class:`~project_standards.mcp_server.resources.ResourceRegistry`
that answers ``resources/read`` and inherits its URI canonicalization,
registration-index lookup, digest recheck, and refusal taxonomy unchanged.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from project_standards.mcp_server.models import CATALOG_MAJOR
from project_standards.mcp_server.repo_access import resolve_effective_root
from project_standards.mcp_server.resources import (
    CATALOG_SEGMENT,
    PACKAGE_TEMPLATE,
    RESOURCE_TEMPLATE,
    SCHEME,
    ResourcePayload,
    ResourceRegistry,
)
from project_standards.mcp_services import McpServiceFacade, ServiceError

#: ADR 0026's frozen v1 registry spells all six names; nothing here may rename
#: them, and no seventh name may join them (the record's tool set is closed and
#: the plan's stop condition repeats it).
STANDARDS_LIST = "standards_list"
STANDARD_READ = "standard_read"
REPO_INSPECT = "repo_inspect"
RECONCILE_PREVIEW = "reconcile_preview"
VALIDATE_REPO = "validate_repo"
DRIFT_CHECK = "drift_check"

#: The tools that address a consumer repository rather than the installed
#: distribution. They are the only ones that take a ``repo_root``, the only ones
#: the launch-time boundary narrows, and the only ones for which a client's
#: advertised roots are consulted: asking a client for roots before listing the
#: installed catalog would be a round trip no rule uses.
REPOSITORY_SCOPED_TOOLS = frozenset({REPO_INSPECT, RECONCILE_PREVIEW, VALIDATE_REPO, DRIFT_CHECK})

#: The authoritative ``StateKind.INITIALIZED`` value, spelled rather than
#: imported. The §5.5 ``reconcile_preview`` row makes the published slot follow
#: the authoritative classification, so this comparison has to happen — but T5's
#: import-boundary contract forbids ``tools.py`` from importing
#: ``control_plane.state`` at all, and ``mcp_services`` exports no state
#: vocabulary. The literal is pinned by tests rather than by an import: the
#: EC-005 suite drives every degraded classification ``StateKind`` defines and
#: requires the control-plane slot for each, so a new or renamed classification
#: fails there instead of silently publishing a preview.
INITIALIZED_STATE = "initialized"

#: ``standard_read``'s one input. Named for what it is — the canonical resource
#: URI — because a path-shaped argument name would advertise an addressing mode
#: FR-008 forbids.
STANDARD_READ_ARGUMENT = "uri"

#: The one input every repository-scoped tool takes. Unlike the URI argument this
#: spelling is *contract*: FR-024 names it in the requirement text ("shall require
#: an explicit `repo_root`") and §5.5 names it on the facade methods.
REPO_ROOT_ARGUMENT = "repo_root"

#: The two slots of the §5.5 ``reconcile_preview`` tool-result envelope. Exactly
#: one is non-null on every call, and which one follows the authoritative state
#: classification rather than a caught failure code.
PREVIEW_SLOT = "preview"
CONTROL_PLANE_SLOT = "control_plane"

#: What a client advertised for one call, in the two forms ADR 0026's root rules
#: distinguish: ``None`` is *no advertised set* — the client declared no roots
#: capability, or could not be asked — and an empty sequence is *the client
#: advertised none*, which admits no repository at all. ``resolve_effective_root``
#: treats them as opposites, so the alias exists to keep that distinction visible
#: at every signature that carries it.
type RootSet = Sequence[object] | None

#: The Step 09 client matrix, transcribed to the single question FR-008 asks of
#: each supported primary client: *does this client give the model direct
#: resource access?*
#:
#: Sourced from the T1 evidence matrix
#: (``docs/research/2026-07-28-project-standards-mcp-protocol-sdk-client-matrix.md``):
#: Claude Code 2.1.220 references resources as ``@server:uri`` mentions and its
#: built-in tools list and read them; Codex CLI 0.145.0 has ``read_resource`` in
#: its client source, but *model-initiated* resource access "is not established
#: at 0.145.0", which the required-fallbacks table records as the reason this
#: tool is REQUIRED rather than optional.
#:
#: Read at server construction rather than captured at import, so this is the one
#: place the registration decision can be changed — by refreshing T1, never by an
#: implementation choice elsewhere.
CLIENT_DIRECT_RESOURCE_ACCESS: Mapping[str, bool] = {
    "claude-code": True,
    "codex-cli": False,
}

#: Stable failure codes this layer owns. Everything a *read* or an *inspection*
#: can fail with is already spelled by ``resources``, ``repo_access``, or
#: ``mcp_services`` and is passed through untouched, so only the two
#: argument-shape classes are new: they are refused before any URI or root is
#: parsed, so no existing code describes them.
TOOL_NOT_FOUND = "tool-not-found"
TOOL_ARGUMENTS_INVALID = "tool-arguments-invalid"

_URI_REMEDIATION = (
    f"call {STANDARD_READ} with exactly one argument, {STANDARD_READ_ARGUMENT!r}, whose value is "
    f"one canonical resource URI of the form {SCHEME}{CATALOG_SEGMENT}/{{catalog_major}}, "
    f"{PACKAGE_TEMPLATE}, or {RESOURCE_TEMPLATE}"
)


def _root_remediation(name: str) -> str:
    """The remediation every repository-scoped refusal carries, named for its tool.

    One producer rather than a constant per tool: the four tools take the same
    argument under the same rule, so four sentences would be four chances to
    describe it differently — and the only per-tool fact in it is the name, which
    the caller already has (T9.5).
    """
    return (
        f"call {name} with exactly one argument, {REPO_ROOT_ARGUMENT!r}, whose value is the "
        "absolute path of the repository to operate on"
    )


def _plural(count: int, singular: str, plural: str | None = None) -> str:
    """``count`` and its noun, agreeing. Used by every tool's bounded summary.

    The seven hand-written ternaries this replaces were identical in shape and
    differed only in the noun, which is exactly the duplication plan:447 asks this
    task to remove — and a summary that says "1 findings" is the kind of defect
    nobody writes a test for (T9.5).
    """
    return f"{count} {singular if count == 1 else plural or f'{singular}s'}"


_NO_ARGUMENT_REMEDIATION = f"call {STANDARDS_LIST} with no arguments"

# -- declared metadata ---------------------------------------------------------
#
# FR-023 wants tool metadata "concise, unambiguous, and test-reviewed", and its
# acceptance is that descriptions "state purpose, input authority, and read-only
# effect". Each description below carries those three in that order, and the whole
# advertised surface is pinned by the reviewed snapshot in
# ``tests/mcp_server/test_discovery_tools.py`` — so a reworded description, a
# retyped schema, or a dropped authority sentence is a review, not an edit.
#
# Protocol annotations (``ToolAnnotations``/``readOnlyHint``) are deliberately not
# declared. FR-023 places the read-only claim in the description, ADR 0026 freezes
# read-only *behavior* rather than annotation presence, and the SDK treats the
# annotation object as optional; adopting it needs a record amendment rather than
# an implementation choice (T8.2 Codex RED review, F7).

STANDARDS_LIST_TITLE = "List installed standard packages"
STANDARDS_LIST_DESCRIPTION = (
    f"List every standard package installed in Catalog {CATALOG_MAJOR}: id, title, status, "
    "exact version, exposure, capabilities, declared relationships, and version-qualified "
    "resource URIs. Takes no arguments; the installed distribution is the only authority. "
    "Read-only: it writes nothing."
)

STANDARD_READ_TITLE = "Read one installed standard resource"
STANDARD_READ_DESCRIPTION = (
    "Return the exact bytes and declared media type of one installed standard resource, "
    f"addressed by its canonical {SCHEME} URI. Same content as reading the resource "
    "directly; use this when the client cannot read MCP resources. Accepts only declared "
    "resource URIs, never filesystem paths. Read-only: it writes nothing."
)

REPO_INSPECT_TITLE = "Inspect one consumer repository's standards state"
REPO_INSPECT_DESCRIPTION = (
    "Report the current control-plane state of one consumer repository: its authoritative "
    "classification, the parsed .standards/ desired, catalog, and lock state, and bounded "
    f"findings. The repository is the explicit {REPO_ROOT_ARGUMENT} argument, never the "
    "working directory; a launch-time boundary can only narrow it. Read-only: it writes "
    "nothing."
)

RECONCILE_PREVIEW_TITLE = "Preview reconciliation for one consumer repository"
RECONCILE_PREVIEW_DESCRIPTION = (
    "Return the dry-run reconciliation plan for one consumer repository: actions, "
    "findings, preconditions, provider notices, next lock, and the control plane's own "
    "reconciliation fingerprint. When the repository cannot be planned, its "
    "control-plane state and findings are returned instead. The repository is the "
    "explicit repo_root argument, never the working directory. Read-only: it plans but "
    "never applies, and writes nothing."
)

VALIDATE_REPO_TITLE = "Validate one consumer repository against its standards"
VALIDATE_REPO_DESCRIPTION = (
    "Run every applicable validate, verify, and lint provider declared by the standards "
    "this consumer repository currently resolves, and return their typed status, "
    "findings, and bounded diagnostics. Providers are chosen by the repository's own "
    "resolution and cannot be named by the caller. The repository is the explicit "
    "repo_root argument, never the working directory. Read-only: no mutating provider "
    "operation is dispatched and nothing is written."
)

DRIFT_CHECK_TITLE = "Report standards drift for one consumer repository"
DRIFT_CHECK_DESCRIPTION = (
    "Report drift for one consumer repository: the control plane's own reconciliation "
    "actions, findings, and fingerprint, plus the results of every applicable "
    "drift-check provider. Facts only, with no summary verdict, confidence, or "
    "clean-state flag invented. The repository is the explicit repo_root argument, "
    "never the working directory. Read-only: it writes nothing."
)

#: ``standards_list`` takes nothing. ``additionalProperties: false`` is the
#: schema-level half of the refusal :func:`invoke_tool` enforces on the wire.
STANDARDS_LIST_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}

#: ``standard_read``'s declared input. ``type: string`` is the contract: plan:405
#: makes the input "one canonical resource URI", which is a string on the wire, and
#: a schema that typed it otherwise would advertise an input the tool cannot take.
#: ``format: uri`` states the kind without constraining the scheme in the schema —
#: the authority on which URIs resolve is the ADR 0026 grammar in ``resources``,
#: and duplicating it as a regex here would create the second producer of that
#: grammar T6.5 collapsed.
STANDARD_READ_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        STANDARD_READ_ARGUMENT: {
            "type": "string",
            "format": "uri",
            "description": (
                f"A canonical {SCHEME} resource URI, exactly as the installed catalog "
                "declares its ids and versions."
            ),
        }
    },
    "required": [STANDARD_READ_ARGUMENT],
    "additionalProperties": False,
}


def repo_root_input_schema(description: str) -> dict[str, Any]:
    """FR-024's explicit root, declared in the schema as well as in the handler.

    Required *in the schema* so a client can see the rule before it calls. The
    property sentence differs per tool because the purpose does; the
    required-clause is identical everywhere, so the one rule a caller must learn
    reads the same on all four repository-scoped tools.
    """
    return {
        "type": "object",
        "properties": {REPO_ROOT_ARGUMENT: {"type": "string", "description": description}},
        "required": [REPO_ROOT_ARGUMENT],
        "additionalProperties": False,
    }


REPO_INSPECT_INPUT_SCHEMA: dict[str, Any] = repo_root_input_schema(
    "Absolute path to the consumer repository to inspect. Required: the server "
    "never infers a repository from its working directory."
)

RECONCILE_PREVIEW_INPUT_SCHEMA: dict[str, Any] = repo_root_input_schema(
    "Absolute path to the consumer repository to preview reconciliation for. Required: "
    "the server never infers a repository from its working directory."
)

VALIDATE_REPO_INPUT_SCHEMA: dict[str, Any] = repo_root_input_schema(
    "Absolute path to the consumer repository to validate. Required: the server never "
    "infers a repository from its working directory."
)

DRIFT_CHECK_INPUT_SCHEMA: dict[str, Any] = repo_root_input_schema(
    "Absolute path to the consumer repository to report drift for. Required: the server "
    "never infers a repository from its working directory."
)

#: Any JSON value, spelled out rather than written as the empty schema. ``{}`` is a
#: legal schema that constrains nothing, which is indistinguishable from having
#: forgotten to type a field; these three slots really do carry "the parsed
#: authoritative control-plane document, whatever shape it has, or nothing".
_ANY_JSON: dict[str, Any] = {"type": ["object", "array", "string", "number", "boolean", "null"]}

#: The ordered string tuple every §5.5 collection of identifiers projects to.
#: Single-sited because it recurs six times across the two output schemas below —
#: the three relation buckets, ``capabilities``, ``governing_options``, and
#: ``null_values`` — and a fragment repeated that often is a fragment that gets
#: edited in four places out of five.
_STRING_ARRAY: dict[str, Any] = {"type": "array", "items": {"type": "string"}}

_RELATIONSHIP_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "companions": _STRING_ARRAY,
        "extends": _STRING_ARRAY,
        "conflicts": _STRING_ARRAY,
    },
    "required": ["companions", "extends", "conflicts"],
    "additionalProperties": False,
}

#: The FR-001 masked catalog projection, as a schema. Closed (`additionalProperties:
#: false`) and fully required on purpose: the projection is produced by
#: ``ResourceRegistry.catalog_projection`` from the ``CatalogDescriptor`` DTO, so a
#: field the mask starts or stops carrying makes the served instance fail its own
#: declared schema instead of silently changing an untyped blob.
STANDARDS_LIST_OUTPUT_SCHEMA: dict[str, Any] = {
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
                    "capabilities": _STRING_ARRAY,
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

    The DTOs never omit an optional field — ``ServiceModel`` serializes the whole
    frozen field set — so "optional" means *present and null*, not absent. Spelling
    that as ``anyOf[kind, null]`` is what lets the object below be closed and fully
    required without refusing a finding that simply had nothing to report.
    """
    return {"anyOf": [*declared, {"type": "null"}]}


#: One ``Finding``, closed and complete against the frozen §5.5 field list.
#:
#: Every field is enumerated, including the optional line/locus/conflict/digest
#: ones, and the object is closed. An earlier revision left it open on the theory
#: that the optionals "appear only when the control plane reports them" — which is
#: false for these DTOs: ``model_dump`` emits the whole field set with nulls, so an
#: open object bought nothing and cost the typed contract FR-022 requires. It
#: accepted arbitrary extra properties and any type at all in the optional slots
#: (T8.4 Codex GREEN review, F2).
#:
#: ``expected`` and ``actual`` carry the control plane's own ``StableJson``, whose
#: shape is by definition unconstrained; ``null_values`` is a defaulted tuple
#: rather than an optional, so it is a non-nullable array.
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
        "governing_options": _nullable(_STRING_ARRAY),
        "null_values": _STRING_ARRAY,
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

#: DR-005's bounded snapshot, as a schema: the normalized root identity, the exact
#: authoritative classification, the three parsed-state slots, and the findings.
#: Closed, because "no unrelated file contents" is part of the requirement and an
#: open object would let one appear.
REPO_INSPECT_OUTPUT_SCHEMA: dict[str, Any] = {
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

#: DR-002's declaration, as a schema: the complete declared field set of one
#: ``ResourceDescriptor``, closed and fully required.
#:
#: Enumerated rather than written as "an object of strings" (T8.4 Codex GREEN
#: review, F1): that shorthand accepted ``{}`` and ``{"wrong": "value"}``, so it
#: declared nothing about the six facts DR-002 requires the exposed resource to
#: carry — resource id, role, media type, digest, standard identity, and exact
#: package version — plus the canonical URI. Every value is a string because
#: ``resources._declaration`` stringifies the DTO projection.
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

#: Any JSON value, as an array element. The three composite reports carry the
#: control plane's *own* serializations here — a plan action, a plan finding, a
#: resolution — whose shapes belong to the control plane rather than to this
#: adapter, which is exactly why DR-004 forbids re-describing them.
_ANY_JSON_ARRAY: dict[str, Any] = {"type": "array", "items": _ANY_JSON}

#: ``ReconciliationPreview``, closed and complete against the frozen §5.5 field
#: list: every public field of ``ReconciliationPlan.to_jsonable()`` plus
#: ``reconciliation_fingerprint``, and nothing else. The executor-only proposed
#: bytes have no slot at all, which is the schema-level half of "a preview may
#: never publish staged content".
PREVIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "schema_version": {"type": "string"},
        "applicable": {"type": "boolean"},
        "actions": _ANY_JSON_ARRAY,
        "configuration_transforms": _ANY_JSON_ARRAY,
        "units": _ANY_JSON_ARRAY,
        "findings": _ANY_JSON_ARRAY,
        "preconditions": _ANY_JSON_ARRAY,
        "resolution": _ANY_JSON,
        "verification_requests": _ANY_JSON_ARRAY,
        "provider_notices": _ANY_JSON_ARRAY,
        "namespace_prunes": _STRING_ARRAY,
        "catalog_refresh": _ANY_JSON,
        "next_lock": _ANY_JSON,
        "proposed_lock": _ANY_JSON,
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

#: EC-005's envelope, frozen field-by-field by the master plan §5.5 DTO table
#: (2026-07-30): both slots required, exactly one non-null, the populated slot
#: chosen by the authoritative state classification. Closed, because a third slot
#: would be the parallel plan schema DR-004 forbids.
#:
#: **"Exactly one" is enforced by the schema, not merely by the handler.** Two
#: independently nullable properties would validate a both-null document (an
#: answer carrying nothing) and a both-populated one (an answer carrying a
#: preview *and* the state that says no preview exists), neither of which the
#: record permits — so the two valid arms are spelled as ``oneOf`` and a client
#: validating against the advertised schema rejects the other two combinations
#: (T9.4 Codex GREEN review, F2).
RECONCILE_PREVIEW_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        PREVIEW_SLOT: _nullable(PREVIEW_SCHEMA),
        CONTROL_PLANE_SLOT: _nullable(REPO_INSPECT_OUTPUT_SCHEMA),
    },
    "required": [PREVIEW_SLOT, CONTROL_PLANE_SLOT],
    "additionalProperties": False,
    "oneOf": [
        {
            "properties": {
                PREVIEW_SLOT: PREVIEW_SCHEMA,
                CONTROL_PLANE_SLOT: {"type": "null"},
            }
        },
        {
            "properties": {
                PREVIEW_SLOT: {"type": "null"},
                CONTROL_PLANE_SLOT: REPO_INSPECT_OUTPUT_SCHEMA,
            }
        },
    ],
}

#: DR-008's declared provider-result fields, closed and fully required: identity,
#: operation, phase/effect, status, findings, bounded diagnostics, and the
#: declared output-schema fields the dispatcher already validated and published.
_PROVIDER_RESULT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "standard_id": {"type": "string"},
        "version": {"type": "string"},
        "provider_id": {"type": "string"},
        "operation": {"type": "string"},
        "phase": {"type": "string"},
        "effect": {"type": "string"},
        "status": {"type": "string"},
        "findings": {"type": "array", "items": _FINDING_SCHEMA},
        "diagnostics": {"type": "string"},
        "output": _ANY_JSON,
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
        "diagnostics",
        "output",
    ],
    "additionalProperties": False,
}

VALIDATE_REPO_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "repo_root": {"type": "string"},
        "results": {"type": "array", "items": _PROVIDER_RESULT_SCHEMA},
        "findings": {"type": "array", "items": _FINDING_SCHEMA},
    },
    "required": ["repo_root", "results", "findings"],
    "additionalProperties": False,
}

#: ``DriftReport.findings`` carries the *plan's* own findings serialization, not
#: the protocol-neutral ``Finding`` DTO that ``ValidationReport.findings``
#: carries. The difference is contract rather than accident: drift findings come
#: from ``ReconciliationPlan.to_jsonable()``, whose shape belongs to the control
#: plane, and re-describing it here is what DR-004 forbids.
DRIFT_CHECK_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "repo_root": {"type": "string"},
        "reconciliation_fingerprint": {"type": "string"},
        "actions": _ANY_JSON_ARRAY,
        "findings": _ANY_JSON_ARRAY,
        "results": {"type": "array", "items": _PROVIDER_RESULT_SCHEMA},
    },
    "required": ["repo_root", "reconciliation_fingerprint", "actions", "findings", "results"],
    "additionalProperties": False,
}

#: ``standard_read``'s structured half: which resource was read and what the
#: catalog declares about it. ``declaration`` is null for the two metadata forms,
#: which declare no payload resource of their own — so the slot is the complete
#: declaration or nothing, never a partial one.
STANDARD_READ_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "uri": {"type": "string"},
        "media_type": {"type": "string"},
        "declaration": _nullable(_DECLARATION_SCHEMA),
    },
    "required": ["uri", "media_type", "declaration"],
    "additionalProperties": False,
}


@dataclass(frozen=True, slots=True)
class ToolEntry:
    """One registered tool, protocol-neutral.

    The transport projects this onto the SDK's ``types.Tool``; keeping it a plain
    dataclass is what lets the registration set be built, inspected, and decided
    on without the SDK being importable outside ``transport``.

    ``output_schema`` is required rather than optional because FR-022 requires
    every v1 tool to declare one: a tool that returned structured content while
    declaring no schema for it would hand clients an untyped blob.
    """

    name: str
    title: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ToolResult:
    """One answered tool call, in the carriers FR-022 names.

    ``structured`` is the typed answer and is always present. ``text`` is the
    bounded human summary, empty where prose adds nothing — for ``standard_read``
    the bytes *are* the answer, so a prose restatement of them would be the
    verbosity NFR-012 forbids. ``payload`` is set only by ``standard_read``, whose
    result must stay the same descriptor/bytes mapping ``resources/read`` produces
    (FR-008).
    """

    structured: dict[str, Any]
    text: str = ""
    payload: ResourcePayload | None = None


@dataclass(frozen=True, slots=True)
class ToolContext:
    """Everything a tool call is allowed to reach, assembled once per process.

    Passed in rather than looked up so that the reachable surface is visible in
    one place: the resource registry (for the catalog projection and for the
    delegated read), the facade (for consumer inspection), the launch-time
    boundary, and the registration set. Nothing here can read a file or a
    repository on its own.

    ``tools`` is carried because the registration set is what makes an unknown
    tool name a refusal: ``standard_read`` is absent under the all-direct client
    matrix, and calling an unregistered name must fail as ``tool-not-found``
    rather than be answered.
    """

    registry: ResourceRegistry
    facade: McpServiceFacade
    tools: tuple[ToolEntry, ...]
    configured_boundary: Path | None = None
    _names: frozenset[str] = field(init=False, repr=False, compare=False, default=frozenset())

    def __post_init__(self) -> None:
        object.__setattr__(self, "_names", frozenset(entry.name for entry in self.tools))

    def registers(self, name: str) -> bool:
        return name in self._names


def standard_read_is_required(clients: Mapping[str, bool] | None = None) -> bool:
    """FR-008's condition: does any supported primary client lack direct access?

    ``clients`` defaults to :data:`CLIENT_DIRECT_RESOURCE_ACCESS` read at call
    time, so the decision always reflects the matrix as it stands when the server
    is built rather than as it stood when this module was imported.
    """
    evidence = CLIENT_DIRECT_RESOURCE_ACCESS if clients is None else clients
    return not all(evidence.values())


def build_tool_registry() -> tuple[ToolEntry, ...]:
    """The process's tool registration set, in ADR 0026's registry order.

    Fixed for the process lifetime once built, which is what makes ADR 0026's
    ``listChanged: false`` truthful for tools as well as resources. The two
    discovery tools are unconditional — FR-007 and FR-009 put them in the v1
    surface outright — so only ``standard_read`` consults the client matrix, and
    the set is never empty. That is the difference T8 makes to T7's registry: the
    tools capability no longer disappears when every client can read resources
    directly.
    """
    entries = [
        ToolEntry(
            name=STANDARDS_LIST,
            title=STANDARDS_LIST_TITLE,
            description=STANDARDS_LIST_DESCRIPTION,
            input_schema=STANDARDS_LIST_INPUT_SCHEMA,
            output_schema=STANDARDS_LIST_OUTPUT_SCHEMA,
        )
    ]
    if standard_read_is_required():
        entries.append(
            ToolEntry(
                name=STANDARD_READ,
                title=STANDARD_READ_TITLE,
                description=STANDARD_READ_DESCRIPTION,
                input_schema=STANDARD_READ_INPUT_SCHEMA,
                output_schema=STANDARD_READ_OUTPUT_SCHEMA,
            )
        )
    entries.extend(
        (
            ToolEntry(
                name=REPO_INSPECT,
                title=REPO_INSPECT_TITLE,
                description=REPO_INSPECT_DESCRIPTION,
                input_schema=REPO_INSPECT_INPUT_SCHEMA,
                output_schema=REPO_INSPECT_OUTPUT_SCHEMA,
            ),
            ToolEntry(
                name=RECONCILE_PREVIEW,
                title=RECONCILE_PREVIEW_TITLE,
                description=RECONCILE_PREVIEW_DESCRIPTION,
                input_schema=RECONCILE_PREVIEW_INPUT_SCHEMA,
                output_schema=RECONCILE_PREVIEW_OUTPUT_SCHEMA,
            ),
            ToolEntry(
                name=VALIDATE_REPO,
                title=VALIDATE_REPO_TITLE,
                description=VALIDATE_REPO_DESCRIPTION,
                input_schema=VALIDATE_REPO_INPUT_SCHEMA,
                output_schema=VALIDATE_REPO_OUTPUT_SCHEMA,
            ),
            ToolEntry(
                name=DRIFT_CHECK,
                title=DRIFT_CHECK_TITLE,
                description=DRIFT_CHECK_DESCRIPTION,
                input_schema=DRIFT_CHECK_INPUT_SCHEMA,
                output_schema=DRIFT_CHECK_OUTPUT_SCHEMA,
            ),
        )
    )
    return tuple(entries)


def _arguments_error(message: str, remediation: str) -> ServiceError:
    return ServiceError(code=TOOL_ARGUMENTS_INVALID, message=message, remediation=remediation)


def _accepted(
    name: str, arguments: Mapping[str, Any] | None, allowed: tuple[str, ...], remediation: str
) -> dict[str, Any]:
    """The supplied arguments, after refusing anything the tool does not declare.

    Enforced on the wire as well as in the schema: ``additionalProperties: false``
    tells a client what the tool takes, and this is what happens to a client that
    sends something else anyway.
    """
    supplied = dict(arguments or {})
    unexpected = sorted(set(supplied) - set(allowed))
    if unexpected:
        raise _arguments_error(f"{name} accepts no argument named {unexpected[0]!r}", remediation)
    return supplied


def _standards_list(
    context: ToolContext, arguments: Mapping[str, Any] | None, _roots: RootSet
) -> ToolResult:
    """FR-007: the installed catalog, exactly as the FR-001 resource serves it.

    The human summary counts what the projection carries rather than what the
    facade holds, so it can never describe a listing the client did not receive.
    """
    _accepted(STANDARDS_LIST, arguments, (), _NO_ARGUMENT_REMEDIATION)
    projection = context.registry.catalog_projection()
    installed = cast("list[object]", projection["standards"])
    return ToolResult(
        structured=projection,
        text=(
            f"{_plural(len(installed), 'standard package')} installed in "
            f"Catalog {projection['catalog_major']}."
        ),
    )


def _resolved_root(
    context: ToolContext,
    name: str,
    arguments: Mapping[str, Any] | None,
    client_roots: RootSet,
) -> Path:
    """The one path every repository-scoped tool takes to a filesystem root.

    Single-sited because the record's root rules are written for *every*
    repository-scoped tool: the explicit argument is mandatory, the launch-time
    boundary and the client's advertised roots may only narrow, and containment
    is decided on resolved paths. A tool that resolved its own root would be a
    second place those rules could drift.
    """
    supplied = _accepted(name, arguments, (REPO_ROOT_ARGUMENT,), _root_remediation(name))
    return resolve_effective_root(
        supplied.get(REPO_ROOT_ARGUMENT),
        configured_boundary=context.configured_boundary,
        client_roots=client_roots,
    )


def _repo_inspect(
    context: ToolContext, arguments: Mapping[str, Any] | None, client_roots: RootSet
) -> ToolResult:
    """FR-009/FR-024/DR-005: one repository's authoritative state, for an explicit root.

    The root is normalized and contained by ``resolve_effective_root`` before the
    facade sees it, and the facade's snapshot is published verbatim. Neither step
    happens here, which is the point: containment policy has one owner and the
    state classification has another, and this tool is the wiring between them.
    """
    root = _resolved_root(context, REPO_INSPECT, arguments, client_roots)
    snapshot = context.facade.inspect_repo(root)
    return ToolResult(
        structured=snapshot.model_dump(mode="json"),
        text=f"Control plane state: {snapshot.state}; {_plural(len(snapshot.findings), 'finding')}.",
    )


def _reconcile_preview(
    context: ToolContext, arguments: Mapping[str, Any] | None, client_roots: RootSet
) -> ToolResult:
    """FR-011/DR-004/EC-005: the dry-run plan, or the state that explains its absence.

    The §5.5 tool-result row makes this envelope contract rather than choice:
    two required nullable slots, exactly one non-null, and **the slot follows the
    authoritative classification** — not a caught failure code. That distinction
    is the whole design. ``McpServiceFacade.reconcile`` raises for every
    non-``initialized`` state *and* for lock contention *and* for a planner
    refusal on a perfectly good repository; catching a ``ServiceError`` and
    reading its code would silently turn the last two into a "degraded" answer.
    Asking ``inspect_repo`` first is what keeps EC-005's obligation ("returns
    control-plane findings") separate from a real failure, which stays a
    structured refusal.

    Neither arm is synthesized: the preview slot is ``reconcile``'s own
    projection and the control-plane slot is ``inspect_repo``'s own snapshot, so
    the control plane keeps one serialization and DR-004's "no parallel MCP plan
    schema" holds in both directions.
    """
    root = _resolved_root(context, RECONCILE_PREVIEW, arguments, client_roots)
    snapshot = context.facade.inspect_repo(root)
    if snapshot.state != INITIALIZED_STATE:
        return ToolResult(
            structured={
                PREVIEW_SLOT: None,
                CONTROL_PLANE_SLOT: snapshot.model_dump(mode="json"),
            },
            text=(
                f"No reconciliation preview: control plane state is {snapshot.state}; "
                f"{_plural(len(snapshot.findings), 'finding')}."
            ),
        )
    preview = context.facade.reconcile(root)
    return ToolResult(
        structured={PREVIEW_SLOT: preview.model_dump(mode="json"), CONTROL_PLANE_SLOT: None},
        text=(
            f"Reconciliation preview: {_plural(len(preview.actions), 'planned action')}; "
            "nothing applied."
        ),
    )


def _validate_repo(
    context: ToolContext, arguments: Mapping[str, Any] | None, client_roots: RootSet
) -> ToolResult:
    """FR-012: the applicable validate/verify/lint results, exactly as the service ran them.

    Provider *selection* happens in ``mcp_services`` and nowhere else (plan:439:
    "without performing provider selection or drift interpretation in
    ``mcp_server``"), so this handler names no operation, no provider, and no
    payload version — it forwards one contained root and publishes the report.
    """
    root = _resolved_root(context, VALIDATE_REPO, arguments, client_roots)
    report = context.facade.validate_repo(root)
    return ToolResult(
        structured=report.model_dump(mode="json"),
        text=(
            f"{_plural(len(report.results), 'applicable provider')} ran; "
            f"{_plural(len(report.findings), 'finding')}."
        ),
    )


def _drift_check(
    context: ToolContext, arguments: Mapping[str, Any] | None, client_roots: RootSet
) -> ToolResult:
    """FR-013/FR-017: reconciliation facts plus drift-check results, uninterpreted.

    The summary counts what the report carries and asserts nothing about it: §5.5
    forbids inventing a confidence, a relevance, or a clean-state boolean, and a
    human line that announced "no drift" would be exactly that invention wearing
    prose. The fingerprint is the executor's own, so the protocol introduces no
    competing plan identity.
    """
    root = _resolved_root(context, DRIFT_CHECK, arguments, client_roots)
    report = context.facade.drift_check(root)
    return ToolResult(
        structured=report.model_dump(mode="json"),
        text=(
            f"{_plural(len(report.actions), 'reconciliation action')}; "
            f"{_plural(len(report.results), 'drift-check provider')} ran."
        ),
    )


def _standard_read(
    context: ToolContext, arguments: Mapping[str, Any] | None, _roots: RootSet
) -> ToolResult:
    """FR-008: the same read ``resources/read`` performs, reached the same way.

    The argument shape is checked here and the URI is not: everything about
    *which* URIs resolve — canonicalization, the registration index, the digest
    recheck on every read — belongs to ``resources`` and is reached rather than
    repeated, because plan:406 forbids a second resource-reading implementation.
    The consequence is the one FR-008 wants: this tool and ``resources/read``
    cannot disagree, on bytes or on refusals, because they are the same read.
    """
    supplied = _accepted(STANDARD_READ, arguments, (STANDARD_READ_ARGUMENT,), _URI_REMEDIATION)
    uri = supplied.get(STANDARD_READ_ARGUMENT)
    if not isinstance(uri, str):
        raise _arguments_error(
            f"{STANDARD_READ} requires the {STANDARD_READ_ARGUMENT!r} argument to be one "
            f"resource URI string; got {type(uri).__name__}",
            _URI_REMEDIATION,
        )
    payload = context.registry.read(uri)
    return ToolResult(
        structured={
            "uri": payload.uri,
            "media_type": payload.media_type,
            "declaration": payload.declared,
        },
        payload=payload,
    )


def invoke_tool(
    context: ToolContext,
    name: str,
    arguments: Mapping[str, Any] | None,
    client_roots: RootSet = None,
) -> ToolResult:
    """Answer one tool call, or refuse it structurally.

    The name is checked against the *registration set* rather than against the
    handler table: a tool the client matrix omitted has a handler but is not
    served, and answering it anyway would make the advertised surface a lie.

    ``client_roots`` carries what the client advertised for *this* call, and its
    two empty forms are deliberately different — ``None`` is "no advertised set"
    and ``()`` is "the client advertised none", which
    :func:`~project_standards.mcp_server.repo_access.resolve_effective_root`
    treats as unconstrained and refuse-everything respectively. Collapsing them
    would either widen authority or refuse every call from a client that cannot
    be asked.

    Raises:
        ServiceError: for an unknown tool or a malformed argument set, and
            whatever the registry, the root resolver, or the facade raises for
            the input itself.
    """
    handler = _HANDLERS.get(name)
    if handler is None or not context.registers(name):
        raise ServiceError(
            code=TOOL_NOT_FOUND,
            message=f"this server registers no tool named {name!r}",
            remediation="list the available tools and call one of them",
        )
    return handler(context, arguments, client_roots)


_HANDLERS: dict[str, Callable[[ToolContext, Mapping[str, Any] | None, RootSet], ToolResult]] = {
    STANDARDS_LIST: _standards_list,
    STANDARD_READ: _standard_read,
    REPO_INSPECT: _repo_inspect,
    RECONCILE_PREVIEW: _reconcile_preview,
    VALIDATE_REPO: _validate_repo,
    DRIFT_CHECK: _drift_check,
}
