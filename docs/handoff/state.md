# State

**Last updated:** 2026-06-06

## State at a glance

- Unreleased work is complete on `testing` (1.3.0 lint/format + Python Tooling SSOT + standards restructure + per-standard versioning); release ritual deliberately deferred. `main` holds releases; moving `v1` tracks newest. Delta: `git log main..testing`.
- Gate green (2026-06-06): pytest 139, coverage 98% branch (≥85 gate), ruff + basedpyright + pip-audit clean, prettier + markdownlint clean, validate-frontmatter ✓ 12. Six-step gate in `conventions.md` §3.
- Repo on handoff-system-v3 (2026-06-05). Validator at `src/project_standards/` (schema bundled); standards in per-standard bundles `standards/<name>/…` + `meta/versioning.md` (`standards/README.md` index); consumer contract unchanged.
- **Per-standard versioning** on `testing` 2026-06-06: each standard has a `major.minor` **contract version** selected in `.project-standards.yml`; `registry.json` + validator FM→ADR compat gate; no-`version` configs validate byte-identically. Spec+plan in `docs/superpowers/`.
- **Python Tooling scope flexibility** 2026-06-06: `src/` governs the product only — tooling/`scripts/`/archived/non-product Python may live outside `src/` (linted+formatted, not strict-typed); external-program dirs (`.claude/`…) excluded; full stack still mandatory.

## Active incidents

- None.

## Session instructions

1. Live state is auto-injected by the SessionStart hook; check `git log` + working tree before acting. Do not re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to its split file (history → `sessions/`, backlog → `architecture.md`, patterns → `conventions.md`).
3. Update **Last updated** and the bullets whenever state changes.
4. Next obvious work: run the release ritual (cut tag, move `v1`, fast-forward `main`). ⚠️ `requires-python` `>=3.11`→`>=3.13` is breaking for CLI consumers, so the release is **LOCKED as `2.0.0`** (not `1.3.0`) per `meta/versioning.md` (see `CHANGELOG.md` + `deployed.md`). See `deployed.md`.
