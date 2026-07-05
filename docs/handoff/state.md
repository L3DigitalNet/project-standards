# State

**Last updated:** 2026-07-05

## State at a glance

- **v4.0.0 RELEASED on `main` 2026-07-05** (release commit `c7c2fd8`; tags `v4.0.0` + moving `v4`; `v3` frozen at `e69ab6b`; GitHub release live). MAJOR: six validator/config strictness bumps + Python Tooling ruff floor `>=0.14`; ships **project-spec** (5th standard) as additive opt-in. Release commit carried every checklist item: `standards-ref` defaults + all `@v3`→`@v4` doc pins (incl. the project-spec adopt.md availability banner), `UPGRADING.md` rewritten v3→v4, pyproject `4.0.0` + `uv.lock`, CHANGELOG `[4.0.0]` migration notes. All 5 CI workflows green on `main`.
- **Pre-release drift caught while cutting:** two spec-design docs failed Prettier + markdownlint (60× MD049) — `testing` never runs format/lint CI (push triggers are `main`-only); fixed in `a2fe444` before the release commit.
- **`testing` synced to `main`** post-release; branches identical.

## Active incidents

- _None._ Gate green: 796 tests, 98% branch cov, basedpyright 0/0/0, ruff, dogfood (19), pip-audit clean.

## Session instructions

1. Live state auto-injected; check `git log` + tree before acting. Don't re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to split files.
3. Update **Last updated** + bullets whenever state changes.
4. Working branch is `testing`; do not merge into `main` without a release decision.
