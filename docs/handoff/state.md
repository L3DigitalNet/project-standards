# Handoff State

## Current focus

- `agent-handoff@1.10` is default: its SessionStart hook is a Go binary (#138). `linux/amd64` only; upgraders remove the old hook (#140).
- v5.17.0 is published at `29c875ab` with `github-workflow@1.0`; follow-ups #143–#147 are triaged.
- v5.18.0 has 14 P1 issues; #141/#147 are Ready, #128 is Blocked; run #127 before #128 and decide bug 006 first.
- Tail: T24–T29 (#62, #55; T24 ready), deferred #116, SPEC-GSF3 T1, Usage Doc Site V2 specs; owner: 1.12 legacy-digest residual.

## Active incidents

- `test_slow_provider_..._is_reaped` fails in the ordinary lane on a clean gate run; two neighbours fail only under load. Not a regression.
- MCP determinism and frozen-bounds tests are load-sensitive: six fail under gate parallelism; all 57 pass serially (#147).
