# State

**Last updated:** 2026-07-06

## State at a glance

- **Spec B (F5 markdown-tooling formatter authority) IMPLEMENTED + REVIEWED on `testing`, NOT released.** Feature impl `2eb1c1e..d61a74c` = 10 TDD tasks: OPT-IN reusable repo-wide Prettier gate (`format.yml` dual-role `workflow_call` + `prettier: false` job-level opt-out; adoptable `format.caller.yml`), repo-local coherence tool `tests/coherence/` (pins + hermetic split declaration + Node behavioral co-satisfaction + CI `coherence.yml`), `markdown_tooling 1.0→1.1`, DEC-9→DEC-10. Additive ⇒ **MINOR**; `@v4`, `lint-markdown.yml`, frontmatter workflow untouched (verified). Scoped opus review = 0 Critical/Important; 2 follow-ups: behavioral-test hermeticity (`313db8e`) + `release: prepare v4.2.0`.
- **v4.2.0 prepared:** pyproject + uv.lock + CHANGELOG `[4.2.0]` all aligned at 4.2.0 (guarded by `test_version_consistency`). **Release plan (DEFERRED — needs user go-ahead):** tag `v4.1.0 @ 84c0054` + `v4.2.0 @ HEAD` (linear ancestors), move `v4` to HEAD, GitHub releases, then merge `testing`→`main`.
- **Issue #3 (F1–F4) also on `testing`, unreleased:** v4.1.0 prep `37b5fcc`; impl `1341dc0..84c0054`; whole-branch review READY TO MERGE.
- **Release DEFERRED (user, 2026-07-06):** do NOT merge or tag without explicit go-ahead.
- v4.0.0 live on `main` (`c7c2fd8`; `v4` tag); v3 frozen `e69ab6b`. `testing` pushed to origin.

## Active incidents

- _None._ Full gate green on the v4.2.0-prepared tree: 830 tests, coverage 98%, basedpyright 0/0/0, ruff, dogfood 19, coherence 8 (behavioral ran under `npm ci`), `prettier --check .` + markdownlint clean, pip-audit clean.

## Session instructions

1. Live state auto-injected; check `git log` + tree before acting. Don't re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to split files.
3. Update **Last updated** + bullets whenever state changes.
4. Working branch is `testing`; do not merge into `main` without a release decision.
