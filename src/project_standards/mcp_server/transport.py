"""The one module that touches the MCP SDK (ADR 0025, plan T5).

Everything protocol-shaped lives behind these two functions so that an SDK
release — this major line has already renamed its server API once — changes one
file rather than the whole adapter.

**Why the low-level ``Server`` and not ``MCPServer``.** ``MCPServer``
unconditionally installs list handlers *and* ``subscriptions/listen``, and the
SDK derives its 2026-07-28 ``listChanged``/``subscribe`` bits from whether that
subscription method is served. An empty ``MCPServer`` therefore advertises three
feature families it has nothing registered for and three change-notification
streams it has never implemented, which violates DR-007 and ADR 0026's
"``listChanged`` is false for all three capabilities without exception". The
defect is era-specific: the same object is honest at 2025-06-18. A bare
low-level ``Server`` derives its capabilities from actual registrations in both
eras and still answers the mandatory ``server/discover``, so it is the only
construction that can be truthful here. Recorded at T5.1 with probe evidence.

T6 registers the three ADR 0026 resource forms; prompts and tools arrive at T7
and T8. Only the handlers that exist are passed, so the SDK derives the advertised
capability set from the actual registrations — the property the transport suite
asserts rather than any hard-coded list.

**Error mapping lives here because the wire code does, and it is revision-aware.**
``mcp_services`` and ``resources`` speak ``ServiceError``; JSON-RPC codes are
SDK/protocol vocabulary, so the translation is this module's job — and one class
of it depends on the revision the connection negotiated:

* a canonical URI naming something the catalog does not declare is ``-32002`` on
  the pre-2026 revisions that define that code and ``INVALID_PARAMS`` at
  2026-07-28, which moved not-found onto the standard code;
* a non-canonical URI is ``INVALID_PARAMS`` in every revision — no revision
  defines a resource whose name it could be;
* an integrity or catalog fault is ``INTERNAL_ERROR`` in every revision, because
  nothing the client sent was wrong.

In all three the structured ``ServiceError`` fields travel in ``error.data``,
which is what keeps NFR-004's "code, message, affected path/standard, severity,
remediation" machine-readable instead of collapsing into prose.
"""

from __future__ import annotations

import base64
from typing import Any

import anyio
import mcp_types as types
from mcp.server.context import ServerRequestContext
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import MCPError
from mcp_types import INTERNAL_ERROR, INVALID_PARAMS
from mcp_types.version import MODERN_PROTOCOL_VERSIONS

from project_standards.mcp_server.models import (
    PHASE_INSTRUCTIONS,
    SERVER_NAME,
    AdapterConfiguration,
    server_version,
)
from project_standards.mcp_server.resources import (
    ResourceEntry,
    ResourcePayload,
    ResourceTemplateEntry,
    build_resource_registry,
)
from project_standards.mcp_services import McpServiceFacade, ServiceError

# Service codes whose cause is a corrupted or drifted distribution rather than a
# bad request. Everything else a resource read can raise names something the
# client asked for that does not exist or is not canonical.
_SERVER_FAULT_CODES = frozenset({"resource-integrity", "catalog-invalid"})

# Refusals that mean "this URI is canonical, but the installed catalog declares no
# such thing". They are the only class whose wire code is revision-dependent.
_NOT_FOUND_CODES = frozenset({"catalog-not-found", "standard-not-found", "resource-not-found"})

# The resource-not-found code the pre-2026 revisions define. The evidence matrix
# records the change: resource-not-found was `-32002` through 2025-11-25 and
# became `INVALID_PARAMS` at 2026-07-28, with clients advised to keep accepting
# the old value. `mcp_types` cannot export it — under the 2026-07-28 allocation
# policy it is listed as reserved-never-reused — so a legacy connection is the
# only place it may appear, and it is spelled here rather than imported for
# exactly that reason (T6.4 Codex GREEN review, F2).
LEGACY_RESOURCE_NOT_FOUND = -32002


def _protocol_error(error: ServiceError, protocol_version: str) -> MCPError:
    """Project one structured service failure onto the JSON-RPC wire.

    The message is the service's own and the published fields ride in ``data``;
    nothing is invented and nothing is dropped. Optional identity fields are
    omitted when unset rather than sent as nulls, so a client can tell "this
    failure has no affected standard" from "this failure did not say".

    ``protocol_version`` is the *negotiated* revision of this connection, taken
    from the SDK's request context rather than guessed, because the not-found code
    is revision-dependent and the SDK never rewrites a code the adapter chose. A
    server that answered a 2025-06-18 client with the modern code would be
    reporting a failure that revision does not define. The other two classes are
    revision-stable: a non-canonical URI is a bad parameter in every revision, and
    a digest mismatch is a server fault in every revision.
    """
    data: dict[str, Any] = {
        "code": error.code,
        "severity": error.severity,
        "remediation": error.remediation,
    }
    for name in ("standard_id", "version", "path"):
        value = getattr(error, name)
        if value is not None:
            data[name] = value
    if error.code in _SERVER_FAULT_CODES:
        code = INTERNAL_ERROR
    elif error.code in _NOT_FOUND_CODES and protocol_version not in MODERN_PROTOCOL_VERSIONS:
        code = LEGACY_RESOURCE_NOT_FOUND
    else:
        code = INVALID_PARAMS
    return MCPError(code=code, message=error.message, data=data)


# Namespaced `_meta` key carrying the §5.5 `ResourceDescriptor` projection.
# DR-002 requires the exposed resource to include the declared resource id, role,
# media type, digest, standard id, and exact package version, and the protocol's
# `Resource`/`ResourceContents` types have named slots for only the URI and media
# type — so the remaining declared facts ride here. The key is prefixed because
# `_meta` is a shared namespace: `io.modelcontextprotocol/` is reserved for
# spec-defined keys, so an implementation-defined one must not sit bare.
DECLARATION_META_KEY = "dev.project-standards/declaration"


def _declaration_meta(declared: dict[str, str] | None) -> dict[str, Any] | None:
    return None if declared is None else {DECLARATION_META_KEY: declared}


def _resource(entry: ResourceEntry) -> types.Resource:
    return types.Resource(
        uri=entry.uri,
        name=entry.name,
        title=entry.title,
        description=entry.description,
        mime_type=entry.media_type,
        _meta=_declaration_meta(entry.declared),
    )


def _resource_template(entry: ResourceTemplateEntry) -> types.ResourceTemplate:
    return types.ResourceTemplate(
        uri_template=entry.uri_template,
        name=entry.name,
        title=entry.title,
        description=entry.description,
        mime_type=entry.media_type or None,
    )


def _contents(payload: ResourcePayload) -> types.TextResourceContents | types.BlobResourceContents:
    """Carry exact bytes in the representation the payload selected.

    ``resources`` already decided and, for the text branch, already proved the
    bytes decode; this is a mechanical projection so that no byte-level policy
    lives in the SDK-facing layer.
    """
    if payload.as_text:
        return types.TextResourceContents(
            uri=payload.uri,
            mime_type=payload.media_type,
            text=payload.data.decode("utf-8"),
            _meta=_declaration_meta(payload.declared),
        )
    return types.BlobResourceContents(
        uri=payload.uri,
        mime_type=payload.media_type,
        blob=base64.b64encode(payload.data).decode("ascii"),
        _meta=_declaration_meta(payload.declared),
    )


def create_server(
    facade: McpServiceFacade, configuration: AdapterConfiguration
) -> Server[dict[str, Any]]:
    """Build the SDK server carrying exactly the ADR 0026 frozen configuration.

    Identity, version, and instructions are read from module constants, never
    from ``configuration``: the record makes them frozen facts, and routing them
    through a caller-supplied object would let a caller rename the server or
    advertise features it does not register. ``configuration`` therefore carries
    only the one launch-time input the record leaves open, which no resource
    handler consults — resources are distribution-scoped, and the boundary
    narrows *repository* roots for the tools T8/T9 add.

    The registry is built before the ``Server`` object exists, so a registration
    that cannot be expressed canonically aborts the launch instead of producing a
    server with a partial resource list.
    """
    registry = build_resource_registry(facade)
    del configuration  # consumed by the repository-scoped tools T8/T9 register.

    # The paginated params are optional in the SDK's handler contract and both
    # listings are single-page by construction: the registration set is fixed at
    # start and bounded by the installed catalog, so there is no cursor to honour
    # and never a `nextCursor` to emit.
    async def _list_resources(
        _context: object, _params: types.PaginatedRequestParams | None
    ) -> types.ListResourcesResult:
        return types.ListResourcesResult(
            resources=[_resource(entry) for entry in registry.listings()]
        )

    async def _list_resource_templates(
        _context: object, _params: types.PaginatedRequestParams | None
    ) -> types.ListResourceTemplatesResult:
        return types.ListResourceTemplatesResult(
            resource_templates=[_resource_template(entry) for entry in registry.templates()]
        )

    async def _read_resource(
        context: ServerRequestContext[dict[str, Any], Any],
        params: types.ReadResourceRequestParams,
    ) -> types.ReadResourceResult:
        try:
            payload = registry.read(params.uri)
        except ServiceError as error:
            raise _protocol_error(error, context.protocol_version) from error
        return types.ReadResourceResult(contents=[_contents(payload)])

    return Server(
        SERVER_NAME,
        version=server_version(),
        instructions=PHASE_INSTRUCTIONS,
        on_list_resources=_list_resources,
        on_list_resource_templates=_list_resource_templates,
        on_read_resource=_read_resource,
    )


async def _serve_stdio(server: Server[dict[str, Any]]) -> None:
    """Serve one stdio connection until the client closes stdin.

    ``stdio_server()`` claims file descriptors 0 and 1 and points fd 1 at stderr
    for the duration, so a stray print from anywhere in the process misses the
    protocol wire instead of corrupting the next frame. That is defence in
    depth, not the primary control: nothing in this adapter writes to stdout.
    """
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def run_stdio(server: Server[dict[str, Any]]) -> None:
    """Run the server over stdio until the connection ends.

    Synchronous by design: the entry point is a CLI subcommand, and the async
    runtime is an implementation detail of the transport rather than something
    the launch surface should own.
    """
    anyio.run(_serve_stdio, server)
