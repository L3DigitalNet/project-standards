# State

**Last updated:** 2026-07-05

## State at a glance

- **`project-spec` (5th standard) REGISTERED (2026-07-05, `testing`):** full `validate|lint|extract|next|new|upgrade` surface complete, bug-fixed (3 🟡 + 2 🟢 from `/code-review high spec`), adoption docs written, `spec:` config block live, dogfood example added, `README.md`/`meta/versioning.md` updated. CI (`validate-specs.yml`) auto-activated.
- **Residual `format-frontmatter`/`cli.py` gaps fixed (2026-07-05):** typo'd `--config` no longer silently formats; non-UTF-8 input no longer tracebacks; `validate --help` `--glob` text corrected.
- **CHANGELOG caught up + version resolved (2026-07-05):** `project-spec` registration is MINOR; six validator/config strictness bumps + a Python Tooling floor raise are each independently MAJOR (previously-passing rule); `pytest-cov` removal confirmed PATCH via commit history. **Next release off `testing` is MAJOR (v4.0.0).**
- **`3.0.0` RELEASED on `main` 2026-06-12** (tags `v3.0.0`+`v3`; `v2` frozen at `3ece2c9`). `testing` ahead — next release will be v4.0.0, not yet cut.
- **Docs pruned for v4.0.0 (2026-07-05):** 53 deleted — codex-reviews (31), `fable-findings.md`, `python-backend.md`, all implemented plans + `v1.1.0/` archive. Kept: all specs + the pending `check`-drift plan; distribution folders audited clean. `specs-plans.md` table pruned.

## Active incidents

- _None._ Gate green: 790 tests, 98% branch cov, basedpyright 0/0/0, ruff, dogfood frontmatter, pip-audit clean.

## Session instructions

1. Live state auto-injected; check `git log` + tree before acting. Don't re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to split files.
3. Update **Last updated** + bullets whenever state changes.
4. Working branch is `testing`; do not merge into `main` without a release decision.
