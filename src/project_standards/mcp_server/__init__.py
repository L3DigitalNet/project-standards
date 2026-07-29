"""Protocol adapter for the Project Standards MCP server (ADR 0025, ADR 0026).

This package is the *only* place the MCP SDK may appear, and within it only
``transport`` may import SDK types (plan T5). Everything here is registration
and mapping over :mod:`project_standards.mcp_services`; package, control-plane,
and provider semantics stay on the far side of that facade (NFR-006).

Nothing is imported eagerly. Importing this package must not drag in the SDK,
so the adapter modules are reached by name (``mcp_server.transport``,
``mcp_server.entrypoint``, ``mcp_server.repo_access``, ``mcp_server.models``)
rather than re-exported here.
"""
