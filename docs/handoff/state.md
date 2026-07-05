# State

**Last updated:** 2026-07-05

## State at a glance

- **Release-readiness audit + fixes (2026-07-05, `testing`, `38b7980`):** 33-agent audit → **18 verified findings (0 false positives), all in-scope ones fixed**. 🔴 `spec upgrade` failed self-validation on every tier-increasing upgrade of a fresh scaffold (dead Appendix D anchor) — fixed in `upgrade.py` + real-scaffold regression tests (**795 pass**). Drift corrected: AGENTS/CLAUDE now say **five** standards; `src` README `spec extract`/`next` signatures; CHANGELOG `### Fixed`; `meta/versioning.md` release checklist hardened. Four products audited clean (frontmatter, ADR, python-tooling, manifests). **Deferred to the release commit** (now mandated by the checklist): all `@v3`→`@v4` pin bumps + `UPGRADING.md` v3→v4 rewrite.
- **Next release off `testing` is MAJOR (v4.0.0)** — six validator strictness bumps + Python Tooling floor raise (each MAJOR) + project-spec (MINOR). Not yet cut.
- **`project-spec` (5th standard) REGISTERED:** full `validate|lint|extract|next|new|upgrade` surface, `spec:` config, `validate-specs.yml` CI.
- **`3.0.0` RELEASED on `main` 2026-06-12** (tags `v3.0.0`+`v3`; `v2` frozen at `3ece2c9`). `testing` ahead.
- **Docs pruned for v4.0.0 (`9bf50be`):** 53 deleted (codex-reviews, implemented plans, `v1.1.0/`). Kept all specs + pending `check`-drift plan.

## Active incidents

- _None._ Gate green: 795 tests, 98% branch cov, basedpyright 0/0/0, ruff, dogfood (19), pip-audit clean.

## Session instructions

1. Live state auto-injected; check `git log` + tree before acting. Don't re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to split files.
3. Update **Last updated** + bullets whenever state changes.
4. Working branch is `testing`; do not merge into `main` without a release decision.
