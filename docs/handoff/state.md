# State

**Last updated:** 2026-06-08

## State at a glance

- **`adopt` CLI + `validate-id` (hardened) IMPLEMENTED on `testing` (`2.1.0` target), NOT tagged.** 299 tests, 91% cov, basedpyright 0/0/0, ruff clean. `validate-id --fix` is source-preserving (inline comments + per-line endings). **E3 (release commit + tag `v2.1.0` + move `v2` + `deployed.md`) HELD — resume only on explicit user go.**
- **Frontmatter suite spec + plan codex-CONVERGED, NOT implemented** (`docs/superpowers/{specs,plans}/2026-06-08-frontmatter-suite*`; spec r3, plan r4). Adds `format-frontmatter`, `validate-references`, `project-standards fix`, `.pre-commit-hooks.yaml`; folds into the same held `2.1.0`. Build order Phase 0→A→B→C (~26 TDD tasks). **OPEN decision:** plan Task 0.5 rejects duplicate keys in `parse_frontmatter` — a documented narrow exception to "no consumer newly-fails"; confirm or scope to formatter-only.
- **Gate GREEN.** `2.0.0` released 2026-06-07 (`v2.0.0` + moving `v2`; `v1` frozen at `1.2.0`). **BREAKING** `requires-python >=3.14`. See `CHANGELOG.md` + `deployed.md`.
- Repo on handoff-system-v3. Validator at `src/project_standards/` (schema bundled); standards in `standards/<name>/…` + `meta/versioning.md`; consumer contract unchanged.

## Active incidents

- None.

## Session instructions

1. Live state is auto-injected by the SessionStart hook; check `git log` + working tree before acting. Do not re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to its split file (history → `sessions/`, backlog → `architecture.md`, patterns → `conventions.md`).
3. Update **Last updated** and the bullets whenever state changes.
4. `2.1.0` bundles adopt CLI + validate-id (built) + the frontmatter suite (spec+plan only, not built). E3 cuts the release once everything intended for 2.1.0 is implemented and green. `main` holds releases.
