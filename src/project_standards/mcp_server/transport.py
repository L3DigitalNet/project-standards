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

At this task boundary nothing is registered, so no ``on_list_*`` handler is
passed and the SDK advertises no feature capability at all. T6, T7, and T8 add
registrations here; the capability set follows them automatically, which is the
property the transport suite asserts rather than any hard-coded list.
"""

from __future__ import annotations

from typing import Any

import anyio
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from project_standards.mcp_server.models import (
    PHASE_INSTRUCTIONS,
    SERVER_NAME,
    AdapterConfiguration,
    server_version,
)
from project_standards.mcp_services import McpServiceFacade


def create_server(
    facade: McpServiceFacade, configuration: AdapterConfiguration
) -> Server[dict[str, Any]]:
    """Build the SDK server carrying exactly the ADR 0026 frozen configuration.

    Identity, version, and instructions are read from module constants, never
    from ``configuration``: the record makes them frozen facts, and routing them
    through a caller-supplied object would let a caller rename the server or
    advertise features it does not register. ``configuration`` therefore carries
    only the one launch-time input the record leaves open.

    ``facade`` is accepted and deliberately unused at this task boundary: §5.5
    fixes it as an input to ``create_server``, and T6 onwards closes over it in
    the resource, prompt, and tool handlers registered here. Taking it now keeps
    the signature stable across those tasks instead of changing the frozen
    interface when the first registration lands.
    """
    del facade, configuration  # registrations arrive at T6; see the module docstring.
    return Server(
        SERVER_NAME,
        version=server_version(),
        instructions=PHASE_INSTRUCTIONS,
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
