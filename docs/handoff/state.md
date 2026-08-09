# Handoff State

## Current focus

- `agent-handoff@1.10` is default: its SessionStart hook is a Go binary (#138). `linux/amd64` only; upgraders remove the old hook (#140).
- v5.17.0 is published at `29c875ab`: `github-workflow@1.0` advertised (payload now frozen — changes need a new cut); follow-ups #143–#147 sit in Inbox.
- v5.18.0 is the ADR train: #127 as `adr` 1.5 (non-breaking), then #128's 21 items; bug 006 decision owed before #128 item 1.
- Tail: T24–T29 (#62, #55; T24 ready), deferred #116, SPEC-GSF3 T1, Usage Doc Site V2 specs; owner: 1.12 legacy-digest residual.

## Active incidents

- `test_slow_provider_..._is_reaped` fails in the ordinary lane on a clean gate run; two neighbours fail only under load. Not a regression.
- MCP determinism and frozen-bounds contract tests join that load-sensitive set: six fail under gate parallelism, all 57 pass serially. Tracked as #147.
