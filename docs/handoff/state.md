# State

**Last updated:** 2026-07-09

## State at a glance

- **v4.3.0 RELEASED (2026-07-07)** — CLI Documentation Standard; tags `v4.3.0@74db623` + `v4`, GitHub release Latest. `testing` is **ahead of `main`** with unreleased v5 work. Detail: `deployed.md`.
- **v5.0.0 build-out active (`testing`):** MCP specs ingested (`SPEC-MT01→RD01→MS01`; impl **BLOCKED** until MT01 gate). Steps 00–05 + Markdown Frontmatter value/skill ownership work are done through this closeout; next is Step 06 dogfood fixtures/index/catalog + `adopt.toml` linkage. Detail: `TODO.md`.
- **Latest change:** Markdown Frontmatter now has split structure/value pages, a repo-frontmatter ADR template, baseline IT/network/infrastructure tags, ADR 0014/0015/0016, `standards/**` local-frontmatter exclusion, and standard-owned repo-local skill/adopt artifacts. Full gate + convergence review green.

## Active incidents

- _None known._ Full markdownlint still has a pre-existing `docs/future-standards/**` backlog outside the touched docs.

## Ops notes

- **RELEASE FREEZE until v5.0.0.** No interim PATCH/MINOR; changes accumulate under CHANGELOG `[Unreleased]`. Keep classifying; don't tag. Canonical: `meta/versioning.md`.
- **Sub-agent policy:** individual sub-agents + headless Codex OK unasked; agent teams / `Workflow` fan-out need ask-first + cost sketch. Never Fable. Detail: `AGENTS.md`.
- **Repo rulesets:** `main` requires signed commits + blocks force-push/deletion; `v*.*.*` tags block deletion + non-fast-forward. Unsigned commits will be rejected by `main`.

## Session instructions

1. Live state auto-injected; check `git log` + tree before acting. Don't re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to split files.
3. Update **Last updated** + bullets whenever state changes.
4. Working branch is `testing`; do not merge into `main` without a release decision.
