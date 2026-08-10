# Handoff State

## Current focus

- All 20 open issues except #168 were triaged; all seven owner decisions are resolved.
- Release shape resolved 2026-08-10: 5.19.0 is the 20-issue consolidation train; `project-toolbox` moved to 5.20.0.
- T25's #62 child plan is active at `3bb7c4cf`; T1/T2 are ready, but implementation has not begun.
- T4 waits for a separately governed verified #143 checkpoint. Tails: SPEC-GSF3 T1, Usage Doc Site V2 specs, #129 deferred.

## Active incidents

- Two real-provider MCP proofs flake under load (#158); the 30 s bound is ADR 0025, not 0026, and is not frozen by amendment.
- ADRs 0026 and 0010 still claim an open URI producer divergence that closed at `e400f83f` on 2026-07-29; #161 corrects both (bug 009).
