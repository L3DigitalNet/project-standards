"""The ``standard_read`` fallback and the client matrix that decides it (plan T7).

Deliberately SDK-free and repository-free, like every adapter module except
``transport``: the tool's declaration is a plain mapping the transport projects
onto ``types.Tool``, and every package fact it serves comes from the T6 resource
registry. Both boundaries are enforced by
``tests/mcp_server/contract/test_import_boundary.py``.

**The registration decision is data, not judgement.** FR-008 exposes this tool
"when any supported primary client cannot give the model direct resource
access", and names the Step 09 compatibility matrix as what decides the
condition: "when it holds, the tool is mandatory". The plan repeats it — "the
implementer has no discretion to omit it" — and requires the matrix to be
evaluated *mechanically*. :data:`CLIENT_DIRECT_RESOURCE_ACCESS` is that matrix,
transcribed to the one question FR-008 asks of each client, and
:func:`standard_read_is_required` is the evaluation. Both are read at server
construction, so substituting the evidence changes the served tool surface with
no other code path involved.

**It is a fallback, not a convenience.** ADR 0026: "Codex CLI 0.145.0 has no
established model-initiated resource access, so without it Codex users have no
path to standard content." That is also why it delegates rather than reads:
plan:406 forbids "a second resource-reading implementation", so
:func:`invoke_tool` calls the same :class:`~project_standards.mcp_server.resources.ResourceRegistry`
that answers ``resources/read``, and inherits its URI canonicalization,
registration-index lookup, digest recheck, and refusal taxonomy unchanged.

**It cannot take a path.** FR-008: the tool "cannot accept arbitrary paths"; the
plan: "with no path argument". The input is one canonical ``standards://``
resource URI and nothing else, which the schema declares and
:func:`invoke_tool` enforces — a filesystem path reaching the registry is
refused by the same grammar that refuses it on ``resources/read``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from project_standards.mcp_server.resources import (
    CATALOG_SEGMENT,
    PACKAGE_TEMPLATE,
    RESOURCE_TEMPLATE,
    SCHEME,
    ResourcePayload,
    ResourceRegistry,
)
from project_standards.mcp_services import ServiceError

#: ADR 0026's frozen v1 registry spells the tool; nothing here may rename it.
STANDARD_READ = "standard_read"

#: Its one input. Named for what it is — the canonical resource URI — because a
#: path-shaped argument name would advertise an addressing mode FR-008 forbids.
STANDARD_READ_ARGUMENT = "uri"

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

#: Stable failure codes this layer owns. Everything a *read* can fail with is
#: already spelled by ``resources``/``mcp_services`` and is passed through
#: untouched, so only the two argument-shape classes are new: they are refused
#: before any URI is parsed, so no existing code describes them.
TOOL_NOT_FOUND = "tool-not-found"
TOOL_ARGUMENTS_INVALID = "tool-arguments-invalid"

_ARGUMENT_REMEDIATION = (
    f"call {STANDARD_READ} with exactly one argument, {STANDARD_READ_ARGUMENT!r}, whose value is "
    f"one canonical resource URI of the form {SCHEME}{CATALOG_SEGMENT}/{{catalog_major}}, "
    f"{PACKAGE_TEMPLATE}, or {RESOURCE_TEMPLATE}"
)

STANDARD_READ_DESCRIPTION = (
    "Return the exact bytes and declared media type of one installed standard resource, "
    f"addressed by its canonical {SCHEME} URI. Same content as reading the resource "
    "directly; use this when the client cannot read MCP resources. Accepts only declared "
    "resource URIs, never filesystem paths."
)

#: The tool's declared input, as JSON Schema. ``type: string`` is the contract:
#: plan:405 makes the input "one canonical resource URI", which is a string on
#: the wire, and a schema that typed it otherwise would advertise an input the
#: tool cannot take. ``format: uri`` states the kind without constraining the
#: scheme in the schema — the authority on which URIs resolve is the ADR 0026
#: grammar in ``resources``, and duplicating it as a regex here would create the
#: second producer of that grammar T6.5 collapsed.
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


@dataclass(frozen=True, slots=True)
class ToolEntry:
    """One registered tool, protocol-neutral.

    The transport projects this onto the SDK's ``types.Tool``; keeping it a plain
    dataclass is what lets the registration set be built, inspected, and decided
    on without the SDK being importable outside ``transport``.
    """

    name: str
    title: str
    description: str
    input_schema: dict[str, Any]


def standard_read_is_required(clients: Mapping[str, bool] | None = None) -> bool:
    """FR-008's condition: does any supported primary client lack direct access?

    ``clients`` defaults to :data:`CLIENT_DIRECT_RESOURCE_ACCESS` read at call
    time, so the decision always reflects the matrix as it stands when the server
    is built rather than as it stood when this module was imported.
    """
    evidence = CLIENT_DIRECT_RESOURCE_ACCESS if clients is None else clients
    return not all(evidence.values())


def build_tool_registry() -> tuple[ToolEntry, ...]:
    """The process's tool registration set, decided from the client matrix.

    Fixed for the process lifetime once built, which is what makes ADR 0026's
    ``listChanged: false`` truthful for tools as well as resources. Empty when
    every supported primary client gives the model direct resource access —
    the one case in which the plan permits the tool's omission, and the case in
    which the resource surface is the access path.
    """
    if not standard_read_is_required():
        return ()
    return (
        ToolEntry(
            name=STANDARD_READ,
            title="Read one installed standard resource",
            description=STANDARD_READ_DESCRIPTION,
            input_schema=STANDARD_READ_INPUT_SCHEMA,
        ),
    )


def invoke_tool(
    registry: ResourceRegistry, name: str, arguments: Mapping[str, Any] | None
) -> ResourcePayload:
    """Answer one tool call by delegating to the resource registry.

    The argument shape is checked here and the URI is not: everything about
    *which* URIs resolve — canonicalization, the registration index, the digest
    recheck on every read — belongs to ``resources`` and is reached rather than
    repeated, because plan:406 forbids a second resource-reading implementation.
    The consequence is the one FR-008 wants: this tool and ``resources/read``
    cannot disagree, on bytes or on refusals, because they are the same read.

    Raises:
        ServiceError: for an unknown tool or a malformed argument set, and
            whatever the registry raises for the URI itself.
    """
    if name != STANDARD_READ:
        raise ServiceError(
            code=TOOL_NOT_FOUND,
            message=f"this server registers no tool named {name!r}",
            remediation="list the available tools and call one of them",
        )
    supplied = dict(arguments or {})
    unexpected = sorted(set(supplied) - {STANDARD_READ_ARGUMENT})
    if unexpected:
        raise ServiceError(
            code=TOOL_ARGUMENTS_INVALID,
            message=f"{STANDARD_READ} accepts no argument named {unexpected[0]!r}",
            remediation=_ARGUMENT_REMEDIATION,
        )
    uri = supplied.get(STANDARD_READ_ARGUMENT)
    if not isinstance(uri, str):
        raise ServiceError(
            code=TOOL_ARGUMENTS_INVALID,
            message=(
                f"{STANDARD_READ} requires the {STANDARD_READ_ARGUMENT!r} argument to be one "
                f"resource URI string; got {type(uri).__name__}"
            ),
            remediation=_ARGUMENT_REMEDIATION,
        )
    return registry.read(uri)
