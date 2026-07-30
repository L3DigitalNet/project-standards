"""The v1 tool registry: two generic discovery tools and the read fallback (plan T7, T8).

Deliberately SDK-free and repository-free, like every adapter module except
``transport``: each tool's declaration is a plain mapping the transport projects
onto ``types.Tool``, and every fact any of them serves comes from the T6 resource
registry or from ``McpServiceFacade``. Both boundaries are enforced by
``tests/mcp_server/contract/test_import_boundary.py``.

**Three tools, and only one of them is conditional.** ADR 0026 closes the v1
registry at six names; T8 completes the read-only discovery half of it.

* ``standards_list`` (FR-007) — the installed catalog, as the FR-001 masked
  projection. It takes no argument at all: a tool that accepted a standard id
  would be the per-standard surface FR-007 exists to replace.
* ``repo_inspect`` (FR-009) — one consumer repository's authoritative
  control-plane state, for an explicit ``repo_root``.
* ``standard_read`` (FR-008) — the resource-read fallback, registered only when
  the client matrix says a supported primary client needs it.

FR-007 and FR-009 make the first two unconditional parts of the surface, so the
matrix decides the third and nothing else. That distinction is why the tools
capability now survives the counterfactual matrix in which every client can read
resources directly, where T7's registry emptied entirely.

**``standards_list`` does not re-project the catalog.** FR-007's acceptance is
that the tool "returns the same installed catalog facts and exact resource URIs as
FR-001", and T6 already serves exactly that at ``standards://catalog/{major}``.
The projection is therefore taken from
:meth:`~project_standards.mcp_server.resources.ResourceRegistry.catalog_projection`
— the single producer of the FR-001 field mask — rather than rebuilt here. A
second producer is how the resource and the tool would come to disagree, which is
the failure one shared mapping exists to prevent, and it is also the shape the
T6.5 collapse of the URI grammar already ruled out for this adapter.

**``repo_inspect`` owns no path policy either.** The root goes through
:func:`~project_standards.mcp_server.repo_access.resolve_effective_root`, which is
the one place the server decides which directory a repository-scoped call may
touch: the explicit argument is mandatory, the launch-time boundary can only
narrow it, and containment is decided on resolved paths. The snapshot itself is
``McpServiceFacade.inspect_repo``'s, published verbatim — no health summary is
synthesized over the authoritative classification (DR-005).

**Every result is typed and structured, and the human half stays bounded.**
FR-022 requires each v1 tool to declare an output schema and to return
"protocol-supported structured content plus bounded human text where useful", so
:class:`ToolResult` carries both and :data:`ToolEntry.output_schema` is not
optional. ``standard_read``'s structured content publishes the resource's identity
and its DR-002 declaration rather than a second copy of the bytes: the bytes
already travel once in the result's embedded resource, and duplicating a payload
into structured content is exactly the "unnecessary verbosity" NFR-012 names. The
rejected alternative — mirroring the whole contents entry into
``structuredContent`` — is a complete answer twice on every read.

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

from collections.abc import Mapping
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

#: ADR 0026's frozen v1 registry spells all three names; nothing here may rename
#: them, and no fourth name may join them under T8 (the record's tool set is
#: closed and the plan's stop condition repeats it).
STANDARDS_LIST = "standards_list"
STANDARD_READ = "standard_read"
REPO_INSPECT = "repo_inspect"

#: ``standard_read``'s one input. Named for what it is — the canonical resource
#: URI — because a path-shaped argument name would advertise an addressing mode
#: FR-008 forbids.
STANDARD_READ_ARGUMENT = "uri"

#: ``repo_inspect``'s one input. Unlike the URI argument this spelling is
#: *contract*: FR-024 names it in the requirement text ("shall require an explicit
#: `repo_root`") and §5.5 names it on the facade method.
REPO_ROOT_ARGUMENT = "repo_root"

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

_ROOT_ARGUMENT_REMEDIATION = (
    f"call {REPO_INSPECT} with exactly one argument, {REPO_ROOT_ARGUMENT!r}, whose value is the "
    "absolute path of the repository to inspect"
)

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

#: ``repo_inspect``'s declared input. Required, and required *in the schema* as
#: well as in the handler, so a client can see FR-024's rule before it calls.
REPO_INSPECT_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        REPO_ROOT_ARGUMENT: {
            "type": "string",
            "description": (
                "Absolute path to the consumer repository to inspect. Required: the server "
                "never infers a repository from its working directory."
            ),
        }
    },
    "required": [REPO_ROOT_ARGUMENT],
    "additionalProperties": False,
}

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
    entries.append(
        ToolEntry(
            name=REPO_INSPECT,
            title=REPO_INSPECT_TITLE,
            description=REPO_INSPECT_DESCRIPTION,
            input_schema=REPO_INSPECT_INPUT_SCHEMA,
            output_schema=REPO_INSPECT_OUTPUT_SCHEMA,
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


def _standards_list(context: ToolContext, arguments: Mapping[str, Any] | None) -> ToolResult:
    """FR-007: the installed catalog, exactly as the FR-001 resource serves it.

    The human summary counts what the projection carries rather than what the
    facade holds, so it can never describe a listing the client did not receive.
    """
    _accepted(STANDARDS_LIST, arguments, (), _NO_ARGUMENT_REMEDIATION)
    projection = context.registry.catalog_projection()
    installed = cast("list[object]", projection["standards"])
    noun = "package" if len(installed) == 1 else "packages"
    return ToolResult(
        structured=projection,
        text=f"{len(installed)} standard {noun} installed in Catalog {projection['catalog_major']}.",
    )


def _repo_inspect(context: ToolContext, arguments: Mapping[str, Any] | None) -> ToolResult:
    """FR-009/FR-024/DR-005: one repository's authoritative state, for an explicit root.

    The root is normalized and contained by ``resolve_effective_root`` before the
    facade sees it, and the facade's snapshot is published verbatim. Neither step
    happens here, which is the point: containment policy has one owner and the
    state classification has another, and this tool is the wiring between them.
    """
    supplied = _accepted(REPO_INSPECT, arguments, (REPO_ROOT_ARGUMENT,), _ROOT_ARGUMENT_REMEDIATION)
    root = resolve_effective_root(
        supplied.get(REPO_ROOT_ARGUMENT), configured_boundary=context.configured_boundary
    )
    snapshot = context.facade.inspect_repo(root)
    count = len(snapshot.findings)
    noun = "finding" if count == 1 else "findings"
    return ToolResult(
        structured=snapshot.model_dump(mode="json"),
        text=f"Control plane state: {snapshot.state}; {count} {noun}.",
    )


def _standard_read(context: ToolContext, arguments: Mapping[str, Any] | None) -> ToolResult:
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


def invoke_tool(context: ToolContext, name: str, arguments: Mapping[str, Any] | None) -> ToolResult:
    """Answer one tool call, or refuse it structurally.

    The name is checked against the *registration set* rather than against the
    handler table: a tool the client matrix omitted has a handler but is not
    served, and answering it anyway would make the advertised surface a lie.

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
    return handler(context, arguments)


_HANDLERS = {
    STANDARDS_LIST: _standards_list,
    STANDARD_READ: _standard_read,
    REPO_INSPECT: _repo_inspect,
}
