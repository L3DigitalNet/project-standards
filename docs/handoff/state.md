# State

**Last updated:** 2026-07-04

## State at a glance

- **project-spec tooling Spec #1 — design + plan authored & codex-converged (2026-07-04):** `docs/superpowers/specs/2026-07-04-project-spec-tooling-design.md` (spec, 2 codex passes) + `docs/superpowers/plans/2026-07-04-project-spec-tooling-spec1.md` (12-task TDD plan, 3 codex passes, 16 findings applied). Scope = a `src/project_standards/specs/` subpackage: registry core (parses the bundled templates) + read-only `project-standards spec validate|lint|extract|next`; write cmds `new`/`upgrade` deferred to Spec #2; `check_specs.py` retired into the pytest gate. **NEXT: Codex implements Spec #1 from the plan in a parallel session — do not re-implement.**
- **`project-spec` (5th standard)** stays an in-dev draft — unregistered, excluded from validation (`standards/project-spec/**`). README §6 Adoption parked until the tooling ships.
- **CHANGELOG note still owed before next release** (validator strictness bumps + 2026-07-01 python-tooling changes) — see `TODO.md`.
- **`3.0.0` RELEASED on `main` 2026-06-12** (tags `v3.0.0`+`v3`; `v2` frozen at `3ece2c9`). `testing` is ahead with unreleased work.

## Active incidents

- _None._ This session was docs-only (spec + plan + codex-review records); no code changed. Last full gate green: 592 tests, 100% cov, basedpyright 0/0/0, ruff + prettier + markdownlint + dogfood + pip-audit clean.

## Session instructions

1. Live state auto-injected; check `git log` + tree before acting. Don't re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to split files.
3. Update **Last updated** + bullets whenever state changes.
4. Working branch is `testing`; do not merge into `main` without a release decision.
