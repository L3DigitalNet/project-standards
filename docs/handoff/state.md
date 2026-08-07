# Handoff State

## Current focus

- `github-workflow@1.0` is release-ready and self-hosted here; deferred and discovered work is registered in the plan §13 close-out.
- Issue #133 findings: `docs/research/2026-08-07-plan-execution-efficiency.md`; follow-ups #134–#137 filed, all Inbox pending triage.
- Next release is the v5.17.0 ADR train: #127 as `adr` 1.5 (non-breaking), then #128's 21 items; `github-workflow@1.0` follows (OQ-001).
- Decision owed before #128 item 1: how a create-only artifact reaches an existing consumer (bug 006).
- Tail: T24–T29 (#62, #55; T24 ready), deferred #116, SPEC-GSF3 T1, Usage Doc Site V2 specs; owner: 1.12 legacy-digest residual.

## Active incidents

- `testing` HEAD is red on markdownlint: 53 errors in 21 files, all `.agents/skills/go-*/`, from `d4d83bcc` landing without lint exclusions.
- Three `tests/mcp_services/test_providers.py` failures under the parallel ordinary lane; the composite-dispatch one passes in isolation.
