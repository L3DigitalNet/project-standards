# State

**Last updated:** 2026-06-08

## State at a glance

- **`adopt` CLI + `validate-id` (full, hardened) IMPLEMENTED on `testing` (`2.1.0` target), NOT tagged.** 299 tests green, coverage 91%, basedpyright 0/0/0, ruff clean. **E3 (release commit + tag `v2.1.0` + move `v2` + `deployed.md`) HELD — resume only on explicit user go.**
- **`validate-id` is complete.** `--fix` mode is source-preserving (inline comments + per-line endings preserved). Validation corrected: ADR ids missing short-title now rejected; consecutive hyphens in slugs rejected. Validator + combined-command fully documented in `src/project_standards/README.md`.
- **Gate is GREEN.** All prior gate caveats (coverage 82%, 88-col reformats) resolved. E3 unblocked on toolchain.
- **`2.0.0` released** 2026-06-07 (`v2.0.0` + moving `v2` on `main`; `v1` frozen at `v1.2.0`). Consumers re-pin `@v1`→`@v2`; **BREAKING** `requires-python` now `>=3.14`. Details in `CHANGELOG.md` + `deployed.md`.
- Repo on handoff-system-v3. Validator at `src/project_standards/` (schema bundled); standards in per-standard bundles `standards/<name>/…` + `meta/versioning.md`; consumer contract unchanged.

## Active incidents

- None. (The `setup-uv @v8` breakage is fixed and now published at `@v2`.)

## Session instructions

1. Live state is auto-injected by the SessionStart hook; check `git log` + working tree before acting. Do not re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to its split file (history → `sessions/`, backlog → `architecture.md`, patterns → `conventions.md`).
3. Update **Last updated** and the bullets whenever state changes.
4. `2.1.0` (adopt CLI) is implemented on `testing` but **not released** — E3 cuts the release commit + tag once the tree is stable and green. `main` holds releases.
