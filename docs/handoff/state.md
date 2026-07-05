# State

**Last updated:** 2026-07-04

## State at a glance

- **`project-spec` (5th standard) README authored (2026-07-04):** in-development draft — unregistered, excluded from validation (`standards/project-spec/**` in `.project-standards.yml`). §1–§10 written except **§6 Adoption (parked** until tooling+distribution exist). Guarantee-driven: §3 = 8 guarantees (G1–G8); §5 = capability set traced to them (`validate`/`lint`/`extract`/`next`/`new`/`upgrade` core + `status` planned + agent review contract). Full detail in `sessions/2026-07.md`.
- **NEXT SESSION: plan/spec the project-spec tooling** (brainstorm → spec → plan; §5 is the requirements outline). Unblocks §6 Adoption. Tracked in `TODO.md`.
- **3 pre-existing red gates fixed** this session — the project-spec commits (453df7f/d24f276) landed un-gated, leaving frontmatter/markdownlint/ruff red on `testing`; all repaired.
- **CHANGELOG note still owed before next release** (validator strictness bumps + 2026-07-01 python-tooling changes) — see `TODO.md`.
- **`3.0.0` RELEASED on `main` 2026-06-12** (tags `v3.0.0`+`v3`; `v2` frozen at `3ece2c9`). `testing` is ~65 commits ahead with unreleased work.

## Active incidents

- _None._ Full gate green: 592 tests, 100% cov, basedpyright 0/0/0, ruff + prettier + markdownlint + dogfood clean, pip-audit clean.

## Session instructions

1. Live state auto-injected; check `git log` + tree before acting. Don't re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to split files.
3. Update **Last updated** + bullets whenever state changes.
4. Working branch is `testing`; do not merge into `main` without a release decision.
