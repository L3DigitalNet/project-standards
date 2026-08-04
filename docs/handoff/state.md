# Handoff State

## Current focus

- Revision 4 widened v5.15.0. Ready work is T2, T3, T7, and T22; the new tasks are T38, T39, and T40.
- T35 stays blocked until its dependencies land; its blocker text predates the revision that resolved it.
- SPEC-GSF3 durable document-reference tooling: T1 is ready for a fresh implementation session.

## Active incidents

- `agent-handoff` commands all fail mid-cycle on the read-only catalog lineage guard; filed as issue #123.
- `pip-audit`: `cryptography` 49.0.0 is vulnerable (PYSEC-2026-3552, fix 50.0.0); the release gate stays red until the lock advances.
- SessionStart never injects `state.md`: the 1.8 Claude hook keeps `args: []`, so its `sh -c` wrapper is spawned without a shell (#122).
