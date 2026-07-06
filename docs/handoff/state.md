# State

**Last updated:** 2026-07-06

## State at a glance

- **Spec B (F5 markdown-tooling formatter authority) DESIGNED + PLANNED, impl NOT started.** Spec `a564163` + plan `da01e97`, both codex-converged (spec 5 passes / plan 4 passes, "no significant findings"; audits in `docs/codex-reviews/`). Decision: ship an OPT-IN reusable repo-wide Prettier gate (`format.yml` + `format.caller.yml`), superseding DEC-9 via a new DEC-10; additive ⇒ **MINOR** (`markdown_tooling 1.0→1.1`, tool `v4.x`; `@v4` + `lint-markdown.yml` untouched). 10-task TDD plan + repo-local coherence tool under `tests/coherence/`.
- **Issue #3 (F1–F4) IMPLEMENTED, NOT released.** v4.1.0 prepared (`37b5fcc`); impl `1341dc0..84c0054`. Adds `spec.reference_prefixes`, built-in `ADR` prefix, license-token skip, opt-in `upgrade --config`. Loosening → MINOR; whole-branch review READY TO MERGE.
- **Release DEFERRED (user, 2026-07-06):** do NOT merge `testing`→`main` or tag v4.1.0 / Spec B without explicit go-ahead.
- v4.0.0 live on `main` (`c7c2fd8`; `v4` tag); v3 frozen `e69ab6b`.

## Active incidents

- _None._ Spec B is docs-only so far (no code). Gate green at `84c0054`: 808 tests, basedpyright 0/0/0, ruff, dogfood 19, pip-audit clean.

## Session instructions

1. Live state auto-injected; check `git log` + tree before acting. Don't re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to split files.
3. Update **Last updated** + bullets whenever state changes.
4. Working branch is `testing`; do not merge into `main` without a release decision.
