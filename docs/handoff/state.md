# State

**Last updated:** 2026-07-07

## State at a glance

- **Sixth standard (cli-documentation) integrated on `testing`** (commits `a09b431..HEAD`): bundle (README/adopt/templates/examples/resources), adopt artifacts (usage scaffold + `cli-docs-check` workflow template + config fragment), `cli_documentation` contract 1.0 registered end-to-end, `--version` on all seven console scripts, `--help` fixed on the two sync commands, dogfood `docs/usage.md`. Full gate green. **Release decision (v4.3.0) pending** — not tagged, not merged to `main`, no version bump yet.
- v4.1.0 + v4.2.0 RELEASED (2026-07-06); `main` at `6614612` (`v4.1.0@84c0054`, `v4.2.0@6614612`, `v4` moved to `6614612`, GitHub releases live). v4.0.0 `c7c2fd8`; v3 `e69ab6b`, v2 `3ece2c9`, v1 `7450170`.

## Active incidents

- _None._ Full gate green (ruff, basedpyright, pytest+coverage, pip-audit, coherence, prettier, markdownlint, frontmatter/spec validators).

## Ops notes

- **Repo rulesets (active):** `main` requires signed commits + blocks force-push/deletion (no PR/status-check rule). `v*.*.*` tags block deletion + non-fast-forward. `commit.gpgsign`/`tag.gpgsign` are on (key `9375AFEFA6F841B0`) — unsigned commits will be rejected by `main`.

## Session instructions

1. Live state auto-injected; check `git log` + tree before acting. Don't re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to split files.
3. Update **Last updated** + bullets whenever state changes.
4. Working branch is `testing`; do not merge into `main` without a release decision.
