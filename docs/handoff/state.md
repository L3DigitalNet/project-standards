# State

**Last updated:** 2026-07-07

## State at a glance

- **v4.3.0 RELEASED (2026-07-07)** — CLI Documentation Standard (sixth), `cli_documentation` contract 1.0, `--version`/`--help` CLI fixes, dogfood `docs/usage.md`. Release commit `74db623`; `main` fast-forwarded from `f1994bb`; signed tags `v4.3.0@74db623`, `v4` moved to `74db623`; GitHub release live (Latest). `main` and `testing` in sync.
- Prior tags: `v4.2.0@6614612`, `v4.1.0@84c0054`, v4.0.0 `c7c2fd8`; v3 `e69ab6b`, v2 `3ece2c9`, v1 `7450170`.
- **MCP enablement specs ingested (2026-07-07, docs-only):** draft `SPEC-MT01`→`SPEC-RD01`→`SPEC-MS01` in `docs/superpowers/specs/` + reference pack in `docs/superpowers/research/`; MCP impl **BLOCKED** until SPEC-MT01 readiness gate. Standards stay independent packages (groups = recommendations). ADR backlog → `docs/adr/`, in `TODO.md`. Detail: `specs-plans.md`, `architecture.md`.

## Active incidents

- _None._ Full gate green (ruff, basedpyright, pytest+coverage, pip-audit, coherence, prettier, markdownlint, frontmatter/spec validators).

## Ops notes

- **RELEASE FREEZE until v5.0.0 (set 2026-07-07).** Next release is **v5.0.0** (Meta-repo/MCP-readiness + all accrued standards changes). **No interim PATCH/MINOR** — version-affecting changes accumulate under CHANGELOG `[Unreleased]` and ship together at v5.0.0. Keep classifying; don't tag. Canonical: `meta/versioning.md`.
- **Repo rulesets (active):** `main` requires signed commits + blocks force-push/deletion (no PR/status-check rule). `v*.*.*` tags block deletion + non-fast-forward. `commit.gpgsign`/`tag.gpgsign` are on (key `9375AFEFA6F841B0`) — unsigned commits will be rejected by `main`.

## Session instructions

1. Live state auto-injected; check `git log` + tree before acting. Don't re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to split files.
3. Update **Last updated** + bullets whenever state changes.
4. Working branch is `testing`; do not merge into `main` without a release decision.
