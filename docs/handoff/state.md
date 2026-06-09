# State

**Last updated:** 2026-06-09

## State at a glance

- **Full `3.0.0` payload IMPLEMENTED + GREEN on `testing`, NOT tagged.** adopt CLI + hardened `validate-id` + the frontmatter suite (`format-frontmatter`, `validate-references` opt-in, `project-standards fix`, `.pre-commit-hooks.yaml`, `validate` runs all three validators). 430 tests, 91% cov, basedpyright 0/0/0; ruff/prettier/markdownlint/pip-audit + dogfood clean. **Codex-reviewed** (7 P2/P3 fixed, 2 passes) **+ full release-readiness review done** (docs aligned to v3; pre-commit usage now documented). **E3 (the release) HELD — explicit user go only.**
- **Release version DECIDED: `3.0.0` (MAJOR).** Two `meta/versioning.md` "previously-passing rule" triggers: `validate-id` now runs in the consumer CI workflow (old-style ids newly fail) + `parse_frontmatter` rejects duplicate top-level keys (Task 0.5). CHANGELOG heading + `adopt.md` pins already aligned to v3.
- Repo on handoff-system-v3. `2.0.0` released 2026-06-07. `main` holds releases. Validator at `src/project_standards/`; standards in `standards/<name>/…` + `meta/versioning.md`.

## Active incidents

- _None._ prettier/`format.yml` + markdownlint CI both green.

## Session instructions

1. Live state auto-injected by SessionStart hook; check `git log` + tree before acting. Don't re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to its split file.
3. Update **Last updated** + bullets whenever state changes.
4. **E3 (cut `3.0.0`) on user go:** bump `pyproject` 2.0.0→3.0.0 + `uv.lock`; bump bundle/workflow v2→v3 pins (starter `standards_version`, caller stub, workflow `standards-ref` default ~line 44 + the adopt.md "defaults to v2" note); one signed commit; tag `v3.0.0`; **freeze `v2`** at `v2.0.0` + create moving `v3`; update `deployed.md`; GitHub release. CHANGELOG + adopt.md prose are already v3-aligned.
