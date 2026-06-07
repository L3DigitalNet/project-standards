# State

**Last updated:** 2026-06-07

## State at a glance

- **`2.0.0` released** 2026-06-07: tag `v2.0.0` + moving `v2` on `main`; `v1` frozen at `v1.2.0` (does not advance — 2.0.0 is breaking). `main` == `testing` at the release commit. Consumers re-pin `@v1`→`@v2` (see `CHANGELOG.md` migration notes + `deployed.md`).
- Shipped in 2.0.0: lint/format + MADR-4, Python Tooling SSOT (uv_build, src/, basedpyright, coverage, pip-audit), per-standard bundle restructure + `meta/`, Markdown Tooling Standard, per-standard contract versions, Python baseline 3.13→3.14, `setup-uv` SHA-pin. **BREAKING:** `requires-python >=3.11`→`>=3.14`.
- Repo on handoff-system-v3. Validator at `src/project_standards/` (schema bundled); standards in per-standard bundles `standards/<name>/…` + `meta/versioning.md`; consumer contract unchanged.

## Active incidents

- None. (The `setup-uv @v8` breakage is fixed and now published at `@v2`.)

## Session instructions

1. Live state is auto-injected by the SessionStart hook; check `git log` + working tree before acting. Do not re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to its split file (history → `sessions/`, backlog → `architecture.md`, patterns → `conventions.md`).
3. Update **Last updated** and the bullets whenever state changes.
4. `2.0.0` is shipped; no pending release. Develop the next change on `testing`; `main` holds releases.
