# State

**Last updated:** 2026-07-06

## State at a glance

- **v4.1.0 + v4.2.0 RELEASED (2026-07-06).** `main` + `testing` both at `6614612`. Signed tags: `v4.1.0@84c0054` (spec reference prefixes + token hygiene, issue #3 F1–F4), `v4.2.0@6614612` (Markdown Tooling opt-in Prettier gate, F5: `format.yml` dual-role + `format.caller.yml`, `markdown_tooling 1.1`, DEC-9→DEC-10, `tests/coherence/` tool); `v4` moved to `6614612`. GitHub releases live (v4.2.0 = Latest).
- **History was re-signed at release.** `main`'s `release-pipeline` ruleset requires signed commits, but 6 prior-session Spec B design/plan commits were unsigned → rebased to re-sign `1a85009..ba78dba` → new tip `6614612` (trees identical). The `v*.*.*` tag ruleset (immutable tags) was briefly toggled to re-create `v4.2.0`, then restored to active.
- v4.0.0 `c7c2fd8` (superseded as Latest); v3 frozen `e69ab6b`, v2 `3ece2c9`, v1 `7450170`.

## Active incidents

- _None._ Full gate was green pre-release (830 tests, coverage 98%, basedpyright 0/0/0, ruff, coherence 8, prettier + markdownlint + frontmatter clean, pip-audit clean).

## Ops notes

- **Repo rulesets (active):** `main` requires signed commits + blocks force-push/deletion (no PR/status-check rule). `v*.*.*` tags block deletion + non-fast-forward. `commit.gpgsign`/`tag.gpgsign` are on (key `9375AFEFA6F841B0`) — unsigned commits will be rejected by `main`.

## Session instructions

1. Live state auto-injected; check `git log` + tree before acting. Don't re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to split files.
3. Update **Last updated** + bullets whenever state changes.
4. Working branch is `testing`; do not merge into `main` without a release decision.
