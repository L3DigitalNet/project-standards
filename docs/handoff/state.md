# State

**Last updated:** 2026-07-06

## State at a glance

- **Issue #3 (F1–F4) IMPLEMENTED on `testing`, NOT yet released.** v4.1.0 prepared (CHANGELOG `[4.1.0]` + pyproject + `uv.lock` at `37b5fcc`); impl range `1341dc0..84c0054` = 8 TDD tasks + 1 coverage test. Adds `spec.reference_prefixes` config key, built-in `ADR` reference prefix, license/version token skip (dot-rule + broadened `NOT_AN_ID`), reworded `SV-ID-UNDECLARED`, opt-in `upgrade --config`, §8.3 `adr-0001-…` template example (4 files), README + tooling-notes docs. Backward-compat **loosening → MINOR**. Spec + plan both codex-converged; every task task-reviewed; final whole-branch review (opus) = **READY TO MERGE, 0 Critical/Important**. `testing` pushed to origin (`f60a35d..84c0054`).
- **Release DEFERRED (user decision 2026-07-06):** do NOT merge `testing`→`main` or tag v4.1.0 without explicit go-ahead. To cut it: merge→`main`, tag `v4.1.0` + move `v4`, GitHub release.
- **Spec B (F5 markdown-tooling formatter authority) from issue #3 NOT started** — separate spec/plan cycle still owed (markdownlint enforced vs Prettier advisory + `proseWrap` caveat).
- v4.0.0 remains the live `main` release (`c7c2fd8`; `v4` tag there); v3 frozen `e69ab6b`.

## Active incidents

- _None._ Gate green at `84c0054`: 808 tests, coverage complete, basedpyright 0/0/0, ruff, dogfood 19, pip-audit clean.

## Session instructions

1. Live state auto-injected; check `git log` + tree before acting. Don't re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to split files.
3. Update **Last updated** + bullets whenever state changes.
4. Working branch is `testing`; do not merge into `main` without a release decision.
