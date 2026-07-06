# State

**Last updated:** 2026-07-06

## State at a glance

- **Spec B (F5 markdown-tooling formatter authority) IMPLEMENTED on `testing`, NOT released.** Impl `2eb1c1e..d61a74c` = 10 TDD tasks. Ships an OPT-IN reusable repo-wide Prettier gate: `format.yml` made dual-role (`workflow_call` + `prettier: false` job-level opt-out) + adoptable `format.caller.yml`; repo-local coherence tool under `tests/coherence/` (pins + hermetic split declaration + Node behavioral co-satisfaction + CI `coherence.yml`). `markdown_tooling 1.0→1.1`; DEC-9 superseded by DEC-10. Additive ⇒ **MINOR**; `@v4`, `lint-markdown.yml`, frontmatter workflow all untouched (verified).
- **CHANGELOG written as `[4.2.0]`; pyproject/uv.lock still at 4.1.0** — version bump + release are a separate deferred step (user may instead fold Spec B into a combined 4.1.0 release).
- **Issue #3 (F1–F4) IMPLEMENTED, NOT released.** v4.1.0 prepared (`37b5fcc`); impl `1341dc0..84c0054`. Loosening → MINOR; whole-branch review READY TO MERGE.
- **Release DEFERRED (user, 2026-07-06):** do NOT merge `testing`→`main` or tag any version without explicit go-ahead.
- v4.0.0 live on `main` (`c7c2fd8`; `v4` tag); v3 frozen `e69ab6b`.

## Active incidents

- _None._ Full gate green at `d61a74c`: 829 tests, coverage 98%, basedpyright 0/0/0, ruff, dogfood 19, coherence 8 (behavioral ran under `npm ci`), `prettier --check .` + markdownlint clean, pip-audit clean.

## Session instructions

1. Live state auto-injected; check `git log` + tree before acting. Don't re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to split files.
3. Update **Last updated** + bullets whenever state changes.
4. Working branch is `testing`; do not merge into `main` without a release decision.
