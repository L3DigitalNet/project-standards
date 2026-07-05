# State

**Last updated:** 2026-07-05

## State at a glance

- **project-spec tooling Spec #1 implemented (2026-07-05, `2a6c4c0`):** new `src/project_standards/specs/` subpackage parses bundled templates into a registry and exposes read-only `project-standards spec validate|lint|extract|next`; `spec:` discovery + JSON/error-boundary behavior covered; reusable `validate-specs.yml` added; `check_specs.py` retired into maintainer pytest tests. `new`/`upgrade` remain deferred to Spec #2.
- **`project-spec` (5th standard)** stays an in-dev draft — unregistered, excluded from validation (`standards/project-spec/**`). README §6 Adoption + registration now unblocked by local Spec #1 tooling.
- **CHANGELOG note still owed before next release** (validator strictness bumps + 2026-07-01 python-tooling changes) — see `TODO.md`.
- **`3.0.0` RELEASED on `main` 2026-06-12** (tags `v3.0.0`+`v3`; `v2` frozen at `3ece2c9`). `testing` is ahead with unreleased work.

## Active incidents

- _None._ Last gate green after Spec #1 implementation: 651 tests, 98% cov, basedpyright 0/0/0, ruff, prettier, markdownlint, dogfood frontmatter, and pip-audit clean.

## Session instructions

1. Live state auto-injected; check `git log` + tree before acting. Don't re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to split files.
3. Update **Last updated** + bullets whenever state changes.
4. Working branch is `testing`; do not merge into `main` without a release decision.
