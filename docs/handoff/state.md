# Handoff State

## Current focus

- All 20 open issues except #168 triaged 2026-08-09; comments posted. 14 carried a wrong premise.
- Owner decisions owed before specification: #142, #153, #157, #158, #159, #160, #161.
- Release shape unresolved: `ROADMAP.md` scopes 5.19.0 to `project-toolbox` alone; #168's title says v5.20.0, its body v5.19.0.
- Tails: T24 ready (#62 then #55), SPEC-GSF3 T1, Usage Doc Site V2 specs; #129 stays deferred.

## Active incidents

- Two real-provider MCP proofs flake under load (#158); the 30 s bound is ADR 0025, not 0026, and is not frozen by amendment.
- Executor state stale: `.project-pipeline/…/p4.md` and `p10.md` call T16/T19/T36 not-started though all completed 2026-08-05 (bug 008).
