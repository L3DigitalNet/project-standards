# State

**Last updated:** 2026-06-08

## State at a glance

- **Next up — `adopt` CLI (`2.1.0` target):** spec + plan codex-converged and committed on `testing`, **ready to implement** (not started, not tagged). Plan = `docs/superpowers/plans/2026-06-08-adopt-cli.md`; audit trail in `docs/codex-reviews/`. Adds `project-standards adopt|list|validate`; templates under `src/project_standards/bundles/`; the version bump + `uv.lock` + dated changelog land in one release commit at the end (E3, user-approved).
- **Uncommitted in tree (unrelated):** `sync-vscode-colors` + `sync-standards-include` scripts (+ src/tests) and modified `.vscode/settings.json` — pre-existing WIP, not mine. Commit/stash before implementing adopt; the plan's C2 preserves their `[project.scripts]` entries.
- **`2.0.0` released** 2026-06-07: tag `v2.0.0` + moving `v2` on `main`; `v1` frozen at `v1.2.0` (does not advance — 2.0.0 is breaking). `main` == `testing` at the release commit. Consumers re-pin `@v1`→`@v2` (see `CHANGELOG.md` migration notes + `deployed.md`).
- What 2.0.0 shipped + **BREAKING** `requires-python >=3.11`→`>=3.14`: see `CHANGELOG.md` + `deployed.md`.
- Repo on handoff-system-v3. Validator at `src/project_standards/` (schema bundled); standards in per-standard bundles `standards/<name>/…` + `meta/versioning.md`; consumer contract unchanged.

## Active incidents

- None. (The `setup-uv @v8` breakage is fixed and now published at `@v2`.)

## Session instructions

1. Live state is auto-injected by the SessionStart hook; check `git log` + working tree before acting. Do not re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to its split file (history → `sessions/`, backlog → `architecture.md`, patterns → `conventions.md`).
3. Update **Last updated** and the bullets whenever state changes.
4. `2.0.0` is shipped; no pending release. Develop the next change on `testing`; `main` holds releases.
