# State

**Last updated:** 2026-07-01

## State at a glance

- **Standards corpus reviewed + fixed (2026-07-01, 3 passes — full detail in `sessions/2026-07.md`):** python-tooling §15 was invalid YAML (tab-indented) → doc scaffolds now byte-locked to bundle twins behind `<!-- prettier-ignore -->` with drift tests (conventions §9); ruff floor →`>=0.14`; `pytest-cov` dropped; adopt CLI now delivers `.vscode/settings.json`+`tasks.json`; frontmatter starter/caller fences re-synced (starter had lost `**/*.template.md`); cross-standard pass: pre-commit ban vs frontmatter hooks resolved via §3 scope note (no ADR needed), stale pre-F37 tags pattern fixed, template id placeholders now teach the enforced format, md-tooling adopt gained the missing VS Code-settings + agent-block steps. Combined adoption of all four standards verified collision-free with all gates passing.
- **Handoff system resynced to engine v3.4 (2026-07-01)** — hooks/config byte-matched, `STATUS.md` created, `specs-plans.md` backfilled; `validate-layout.sh` clean apart from local `python3`-shim false positives.
- **CHANGELOG note owed before next release** — validator strictness bumps (F29/F30/F37/F41/F46/F3/F4) **plus** 2026-07-01 python-tooling consumer-visible changes (ruff floor, pytest-cov removal, new `.vscode` artifacts) — tracked in `TODO.md`.
- **`3.0.0` RELEASED on `main` 2026-06-12** (tags `v3.0.0`+`v3`; `v2` frozen at `3ece2c9`). `testing` is ~60 commits ahead of `main` with the unreleased fixes.

## Active incidents

- _None._ Full gate green: 592 tests, 100% cov, basedpyright 0/0/0, prettier/markdownlint/dogfood clean.

## Session instructions

1. Live state auto-injected; check `git log` + tree before acting. Don't re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to split files.
3. Update **Last updated** + bullets whenever state changes.
4. Working branch is `testing`; `staging` is deleted. Do not merge `testing` into `main` without a release decision.
