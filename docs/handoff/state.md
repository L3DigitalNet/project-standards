# Handoff State

## Current focus

- Settle the widened v5.15.0 boundary with the owner, revise the plan to match, then resume at T35.
- Program work outside that boundary stays not-started: T2–T8, T16, T19, T22, T24–T29, T36.
- SPEC-GSF3 durable document-reference tooling: T1 is ready for a fresh implementation session.

## Active incidents

- All `agent-handoff` commands fail mid-cycle: the catalog carries new payloads while the tool release still reads 5.14.0.
- `pip-audit`: `cryptography` 49.0.0 is vulnerable (PYSEC-2026-3552, fix 50.0.0); the release gate stays red until the lock advances.
- SessionStart injected repo context without the `state.md` block on 2026-08-04; the hook renders correctly when run directly.
