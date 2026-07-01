# State

**Last updated:** 2026-07-01

## State at a glance

- **Python Tooling standard reviewed + fixed (2026-07-01):** §15 template was invalid YAML (tab-indented) — now byte-locked to the bundle `check.yml` behind `<!-- prettier-ignore -->` with drift tests (conventions §9); ruff floor →`>=0.14` (first non-preview py314); `pytest-cov` dropped (doc/fragment/repo); adopt CLI now delivers `.vscode/settings.json`+`tasks.json`; §25 audit notes backfilled.
- **Markdown standards swept for the same defect class (2026-07-01):** no tab YAML, but frontmatter adopt.md's starter example had dropped the `**/*.template.md` exclusion and both adopt.md scaffolds had Prettier quote drift — starter/caller/prettierrc fences now byte-locked to bundles with drift + no-tab-yaml + snippet-ref tests.
- **Handoff system resynced to engine v3.4 (2026-07-01)** — hooks/config byte-matched, `STATUS.md` created, `specs-plans.md` backfilled; `validate-layout.sh` clean apart from local `python3`-shim false positives.
- **CHANGELOG note owed before next release** — validator strictness bumps (F29/F30/F37/F41/F46/F3/F4) **plus** 2026-07-01 python-tooling consumer-visible changes (ruff floor, pytest-cov removal, new `.vscode` artifacts) — tracked in `TODO.md`.
- **`3.0.0` RELEASED on `main` 2026-06-12** (tags `v3.0.0`+`v3`; `v2` frozen at `3ece2c9`). `testing` is ~60 commits ahead of `main` with the unreleased fixes.

## Active incidents

- _None._ Full gate green: 591 tests, 100% cov, basedpyright 0/0/0, prettier/markdownlint/dogfood clean.

## Session instructions

1. Live state auto-injected; check `git log` + tree before acting. Don't re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to split files.
3. Update **Last updated** + bullets whenever state changes.
4. Working branch is `testing`; `staging` is deleted. Do not merge `testing` into `main` without a release decision.
