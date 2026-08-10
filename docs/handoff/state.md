# Handoff State

## Current focus

- v5.18.0 published at `68203eca`; 14 issues closed by cuts `adr@1.5`, `python-tooling@1.13`, `agent-handoff@1.11`, `github-workflow@1.1`.
- ADR 0028 was amended in-release: `CP-CREATE-ONLY-ABSENT` is permanent, so create-only refresh is a manual copy, not delete-and-reconcile.
- Next is 5.19.0 `project-toolbox` planning per `ROADMAP.md`. #129 stays open and deferred; both its prerequisites are now closed.
- Tails: T24–T29 (#62, #55; T24 ready), SPEC-GSF3 T1, Usage Doc Site V2 specs; follow-ups #156–#167 are in Inbox, untriaged.

## Active incidents

- Two real-provider MCP proofs flake under load: one failure in three clean gate runs, and 244–356 s outliers vs the 30 s bound (#158).
