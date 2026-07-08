# State

**Last updated:** 2026-07-07

## State at a glance

- **v4.3.0 RELEASED (2026-07-07)** — CLI Documentation Standard (sixth); tags `v4.3.0@74db623` + `v4`, GitHub release Latest. `testing` is now **ahead of `main`** by the v5 work below (docs-only, unreleased). Full release detail: `deployed.md`.
- **v5.0.0 build-out active (`testing`, docs-only):** MCP specs ingested (`SPEC-MT01→RD01→MS01`; MCP impl **BLOCKED** until MT01 readiness gate). Step 00 inventory + Step 01 (13 ADRs, accepted) done; **Step 02** meta-standard (`SPEC-BA01`) spec+plan **Codex-converged, ready to execute** (5-task doc plan); Dependabot bump done. Detail: `TODO.md` v5 tracker, `specs-plans.md`, `architecture.md`.

## Active incidents

- _None._ Full gate green (ruff, basedpyright, pytest+coverage, pip-audit, coherence, prettier, markdownlint, frontmatter/spec validators).

## Ops notes

- **RELEASE FREEZE until v5.0.0 (set 2026-07-07).** Next release is **v5.0.0** (Meta-repo/MCP-readiness + all accrued standards changes). **No interim PATCH/MINOR** — version-affecting changes accumulate under CHANGELOG `[Unreleased]` and ship together at v5.0.0. Keep classifying; don't tag. Canonical: `meta/versioning.md`.
- **v5 build-out: agent teams pre-authorized** (until v5.0.0 releases) — subagents/teams/headless Codex OK without asking; **Sonnet or Opus** by complexity, **never Fable/Haiku**. Details in `AGENTS.md`.
- **Repo rulesets (active):** `main` requires signed commits + blocks force-push/deletion (no PR/status-check rule). `v*.*.*` tags block deletion + non-fast-forward. `commit.gpgsign`/`tag.gpgsign` are on (key `9375AFEFA6F841B0`) — unsigned commits will be rejected by `main`.

## Session instructions

1. Live state auto-injected; check `git log` + tree before acting. Don't re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to split files.
3. Update **Last updated** + bullets whenever state changes.
4. Working branch is `testing`; do not merge into `main` without a release decision.
