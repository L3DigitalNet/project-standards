# State

**Last updated:** 2026-06-06

## State at a glance

- `1.3.0` is feature-complete on `testing` (DEC-1…9) but **unreleased** — the release ritual was deliberately out of scope. `main` holds releases; the moving `v1` tag tracks the newest. Exact delta: `git log main..testing`.
- Gate green (2026-06-06): pytest 129, coverage 93% branch (≥85 gate), ruff + basedpyright + pip-audit clean, prettier + markdownlint clean, validate-frontmatter ✓ 12. Six-step gate in `conventions.md` §3.
- Repo migrated to handoff-system-v3 on 2026-06-05 (this layout).
- Python Tooling SSOT adopted + validator at `src/project_standards/` (schema bundled); standards in per-standard bundles `standards/<name>/…` + `meta/versioning.md` (`standards/README.md` index); consumer contract unchanged. Repo fully conforms to all four standards.
- **Per-standard versioning** landed on `testing` 2026-06-06: each standard carries a `major.minor` **contract version** selected in `.project-standards.yml` (`markdown.frontmatter.version`, `markdown.adr.version`, `python_tooling.version`); bundled `registry.json` + validator FM→ADR compat gate; no-`version` configs validate byte-identically. Spec+plan in `docs/superpowers/`.

## Active incidents

- None.

## Session instructions

1. Live state is auto-injected by the SessionStart hook; check `git log` + working tree before acting. Do not re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to its split file (history → `sessions/`, backlog → `architecture.md`, patterns → `conventions.md`).
3. Update **Last updated** and the bullets whenever state changes.
4. Next obvious work: run the release ritual (cut tag, move `v1`, fast-forward `main`). ⚠️ `requires-python` `>=3.11`→`>=3.13` is breaking for CLI consumers, so the release is **LOCKED as `2.0.0`** (not `1.3.0`) per `meta/versioning.md` (see `CHANGELOG.md` + `deployed.md`). See `deployed.md`.
