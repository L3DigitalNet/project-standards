# State

**Last updated:** 2026-07-05

## State at a glance

- **project-spec Spec #3 `upgrade` IMPLEMENTED (2026-07-05, `testing`):** additive tier promotion; `upgrade SRC --to {standard|full}` with `-i`/`-o`/preview; three fail-closed gates (source-invalid, upgradeability precheck, output self-validation); U3 byte-exact round-trip. v1-core project-spec surface (validate/lint/extract/next/new/upgrade) complete.
- **Validator GFM false-reject fixes shipped (2026-07-05, `7b9754e`):** SV-TABLE ignores inline/escaped pipes; SV-ANCHOR honors GitHub repeated-heading anchors (`-1`); `_OMIT` accepts em-dash ranges. 3 TDD tests. From `/code-review high spec`; 6 more 🟡/🟢 findings deferred to `TODO.md`.
- **CI fix (`b76c96d`):** `validate-specs.yml` gates the this-repo validate/lint steps on a `spec:` block existing (was red at main-merge; no block yet). Auto-enables at registration.
- **Spec #1 read-only (`2a6c4c0`) + Spec #2 `spec new` (`8d48c22`) implemented.** `project-spec` (5th standard) stays in-dev draft — unregistered, excluded from validation.
- **CHANGELOG note still owed before next release** (validator strictness + python-tooling + upgrade/new surface) — see `TODO.md`.
- **`3.0.0` RELEASED on `main` 2026-06-12** (tags `v3.0.0`+`v3`; `v2` frozen at `3ece2c9`). `testing` ahead with unreleased work.

## Active incidents

- _None._ Gate green after GFM fixes: 723 tests, 98% branch cov, basedpyright 0/0/0, ruff, dogfood frontmatter, pip-audit clean.

## Session instructions

1. Live state auto-injected; check `git log` + tree before acting. Don't re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to split files.
3. Update **Last updated** + bullets whenever state changes.
4. Working branch is `testing`; do not merge into `main` without a release decision.
