# State

**Last updated:** 2026-06-09

## State at a glance

- **Full `2.1.0` payload IMPLEMENTED + GREEN on `testing`, NOT tagged.** adopt CLI + hardened `validate-id` + the frontmatter suite (`format-frontmatter`, `validate-references` opt-in, `project-standards fix`, `.pre-commit-hooks.yaml`, `validate` now runs all three validators). 423 tests, 92% cov, basedpyright 0/0/0, ruff clean, pip-audit clean; `format-frontmatter --check` + `project-standards validate`/`fix` clean on the repo. **E3 (release commit + tag `v2.1.0` + move `v2` + `deployed.md`) HELD — explicit user go only.**
- **Task 0.5 RESOLVED (user-confirmed):** `parse_frontmatter` rejects duplicate top-level keys — `validate`/`fix` + consumer CI now error on them (contract-strictness bump, in CHANGELOG 2.1.0).
- **Release version still OPEN:** `validate-id`-runs-in-CI may be MAJOR per `meta/versioning.md §3`; pick the number at E3. `2.0.0` released 2026-06-07. `main` holds releases.
- Repo on handoff-system-v3. Validator at `src/project_standards/`; standards in `standards/<name>/…` + `meta/versioning.md`.

## Active incidents

- _None._ prettier/`format.yml` greened 2026-06-09 (`.prettierignore` for codex-reviews/handoff + formatted two authored docs); markdownlint + prettier CI both green.

## Session instructions

1. Live state auto-injected by SessionStart hook; check `git log` + tree before acting. Don't re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to its split file.
3. Update **Last updated** + bullets whenever state changes.
4. E3 cuts `2.1.0` (now fully built + green) on the user's go: version bump + `uv.lock` + dated changelog in one signed commit, tag `v2.1.0`, move `v2`, update `deployed.md`.
