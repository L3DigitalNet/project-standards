# Handoff State

## Current focus

- MCP T2 closed 2026-07-28 at `e06da3b`: SDK-free facade serves exact catalog/standard/resource; suites 3869+133 green; T3 ready.
- T1 closed at `d695d46` (`mcp==2.0.0`, ADRs 0025/0026); ledger repair `37a6486`; Codex-reviewed T2 DTO shapes await owner glance.
- 5.11.0 remains published from `ab75635`; trackers #75–#77 open, #55/#62 deferred; `standards://` URI alignment awaits owner (ADR 0026).
- MCP hold through T12: defer significant non-MCP features, refactors, standards work, releases, and changes; owner directs exceptions.

## Active incidents

- Engine deletion is blocked until all consumers validate, the final dependency search is clean, and the owner approves.
