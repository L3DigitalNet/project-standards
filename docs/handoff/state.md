# Handoff State

## Current focus

- MCP T1 (Step 09) closed 2026-07-28 at `d695d46`: `mcp==2.0.0` pinned, ADRs 0025/0026 accepted, SPEC-RD01 1.6 / SPEC-MS01 1.3; T2 ready.
- Ledger repair `37a6486` split node pins (v5.8.0 capture vs current tree); suite 3856 green under the wheel-runtime PYTHONPATH.
- 5.11.0 remains published from `ab75635`; trackers #75–#77 open, #55/#62 deferred; `standards://` URI alignment awaits owner (ADR 0026).
- MCP hold through T12: defer significant non-MCP features, refactors, standards work, releases, and changes; owner directs exceptions.

## Active incidents

- Engine deletion is blocked until all consumers validate, the final dependency search is clean, and the owner approves.
