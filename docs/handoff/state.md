# Handoff State

## Current focus

- Settle the widened v5.15.0 boundary with the owner, revise the plan to match, then resume at T35.
- Program work outside that boundary stays not-started: T2–T8, T16, T19, T22, T24–T29, T36.
- SPEC-GSF3 durable document-reference tooling: T1 is ready for a fresh implementation session.

## Active incidents

- `agent-handoff` commands all fail mid-cycle on the read-only catalog lineage guard; filed as issue #123.
- `pip-audit`: `cryptography` 49.0.0 is vulnerable (PYSEC-2026-3552, fix 50.0.0); the release gate stays red until the lock advances.
- SessionStart never injects `state.md`: the 1.8 Claude hook keeps `args: []`, so its `sh -c` wrapper is spawned without a shell (#122).
