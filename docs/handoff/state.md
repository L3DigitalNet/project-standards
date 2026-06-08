# State

**Last updated:** 2026-06-08

## State at a glance

- **`adopt` CLI IMPLEMENTED on `testing` (`2.1.0` target), NOT tagged.** Plan `docs/superpowers/plans/2026-06-08-adopt-cli.md` phases A–E2 committed: `project-standards adopt|list|validate` (engine `src/project_standards/adopt/`, bundles `src/project_standards/bundles/`), 223 tests green, wheel ships bundles, CHANGELOG `[Unreleased]` written. **E3 (version bump + `uv.lock` + dated changelog in one commit, then tag `v2.1.0` + move `v2`, then `deployed.md`) is PENDING — needs a stable green tree + explicit approval.**
- **Gate caveat:** full-repo SSOT gate is red from concurrent in-flight work (untested `validate_id.py` → coverage 82%; 88-col reformats of `registry`/`sync_*`/`validate_frontmatter`). The adopt code itself is fully green (format/lint/type/tests; ~94% coverage excl. `validate_id.py`). Resolve before E3.
- **`2.0.0` released** 2026-06-07 (`v2.0.0` + moving `v2` on `main`; `v1` frozen at `v1.2.0`). Consumers re-pin `@v1`→`@v2`; **BREAKING** `requires-python` now `>=3.14`. Details in `CHANGELOG.md` + `deployed.md`.
- Repo on handoff-system-v3. Validator at `src/project_standards/` (schema bundled); standards in per-standard bundles `standards/<name>/…` + `meta/versioning.md`; consumer contract unchanged.

## Active incidents

- None. (The `setup-uv @v8` breakage is fixed and now published at `@v2`.)

## Session instructions

1. Live state is auto-injected by the SessionStart hook; check `git log` + working tree before acting. Do not re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to its split file (history → `sessions/`, backlog → `architecture.md`, patterns → `conventions.md`).
3. Update **Last updated** and the bullets whenever state changes.
4. `2.1.0` (adopt CLI) is implemented on `testing` but **not released** — E3 cuts the release commit + tag once the tree is stable and green. `main` holds releases.
