# Handoff State

## Current focus

- All 20 open issues except #168 triaged 2026-08-09; comments posted. 14 carried a wrong premise.
- All seven owner decisions resolved 2026-08-10; each issue carries its decision, alternatives, and costs.
- Release shape resolved 2026-08-10: 5.19.0 is the 20-issue consolidation train; `project-toolbox` moved to 5.20.0.
- Tails: T24 ready (#62 then #55), SPEC-GSF3 T1, Usage Doc Site V2 specs; #129 stays deferred.

## Active incidents

- Two real-provider MCP proofs flake under load (#158); the 30 s bound is ADR 0025, not 0026, and is not frozen by amendment.
- ADRs 0026 and 0010 still claim an open URI producer divergence that closed at `e400f83f` on 2026-07-29; #161 corrects both (bug 009).
