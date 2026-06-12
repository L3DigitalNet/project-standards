# State

**Last updated:** 2026-06-12

## State at a glance

- **Validator review pass 2026-06-12 (Fable, review-then-implement):** 58 findings over `src/` validation files (`docs/fable-findings.md`); user selected all — **55 implemented** (one commit per finding/pair, IDs in subjects, `f8c9697`…`9da01a9`), 3 skipped w/ recorded rationale. Headliners: UnicodeDecodeError crashes at read boundaries (F1), `--fix` corrupting block-scalar ids while reporting success (F2), silent green CI on missing files/typo'd `--config` (F3/F4). Fresh-context verifier: 0 failures.
- **Test-suite exhaustiveness pass 2026-06-12 (`c55ca81`):** coverage 93% → **100%** (statements + branches), 509 → **584 tests**. Every error path covered; remaining defensive guards covered via failure injection; `__main__` guards excluded via coverage `exclude_also`.
- **Strictness bumps need a CHANGELOG note at next release** (TODO.md): F29 datetime rejection, F30 quoted versions, F37 tags pattern, F41 config dup keys, F46 non-string keys, F3/F4 new exit-2 paths.
- **`3.0.0` RELEASED on `main` 2026-06-12** (tags `v3.0.0`+`v3`; `v2` frozen at `3ece2c9`; GitHub release live). `testing` is now ~58 commits ahead of `main` with the unreleased validator fixes.

## Active incidents

- _None._ Full gate green: 584 tests, 100% cov, basedpyright 0/0/0, prettier/markdownlint/dogfood clean.

## Session instructions

1. Live state auto-injected; check `git log` + tree before acting. Don't re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to split files.
3. Update **Last updated** + bullets whenever state changes.
4. Working branch is `testing`; `staging` is deleted. Do not merge `testing` into `main` without a release decision.
