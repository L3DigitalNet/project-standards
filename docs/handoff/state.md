# State

**Last updated:** 2026-06-07

## State at a glance

- Unreleased work is complete on `testing` (1.3.0 lint/format + Python Tooling SSOT + standards restructure + per-standard versioning + Markdown Tooling Standard); release deferred. `main` holds releases; moving `v1` tracks newest. Delta: `git log main..testing`.
- Repo on handoff-system-v3 (2026-06-05). Validator at `src/project_standards/` (schema bundled); standards in per-standard bundles `standards/<name>/…` + `meta/versioning.md` (`standards/README.md` index); consumer contract unchanged.
- **Markdown Tooling Standard** on `testing` 2026-06-07: new `standards/markdown-tooling/` bundle (markdownlint + Prettier + EditorConfig), validated `markdown_tooling` `1.0`. Rides the locked `2.0.0`. (Versioning + restructure detail: `deployed.md`.)
- **Python baseline 3.13→3.14** on `testing` 2026-06-07: standard scaffolds + repo dogfood; `python_tooling` label stays `1.0`. Deepens the locked `2.0.0` breaking floor to `requires-python >=3.14`.

## Active incidents

- **setup-uv `@v8` ref withdrawn → broke CI.** Fixed in-repo 2026-06-07: all three refs SHA-pinned to `v8.2.0` (`check.yml`, reusable `validate-markdown-frontmatter.yml`, §15 template). Consumers on a moving `@vN` tag stay red until the release repoints it — another reason to un-defer the release.

## Session instructions

1. Live state is auto-injected by the SessionStart hook; check `git log` + working tree before acting. Do not re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to its split file (history → `sessions/`, backlog → `architecture.md`, patterns → `conventions.md`).
3. Update **Last updated** and the bullets whenever state changes.
4. Next obvious work: run the release ritual (cut tag, move `v1`, fast-forward `main`). ⚠️ `requires-python` `>=3.11`→`>=3.14` is breaking for CLI consumers, so the release is **LOCKED as `2.0.0`** (not `1.3.0`) per `meta/versioning.md` (see `CHANGELOG.md` + `deployed.md`). See `deployed.md`.
