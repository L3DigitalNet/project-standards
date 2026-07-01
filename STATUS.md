# Project Status

This is the human-facing completion summary for the project. Agents maintain it so the project builder can re-orient quickly.

## Completed

- `3.0.0` released on `main` (2026-06-12; tags `v3.0.0`/`v3`; `v2` frozen at `3ece2c9`; GitHub release live).
- Validator review pass (Fable, 2026-06-12): 58 findings across `src/` validation files, 55 implemented (one commit per finding, `f8c9697`…`9da01a9`), 3 skipped with recorded rationale. Headliners: UnicodeDecodeError crashes at read boundaries, `--fix` corrupting block-scalar ids while reporting success, silent green CI on missing files / typo'd `--config`.
- Test-suite exhaustiveness pass (2026-06-12, `c55ca81`): coverage 93% → 100% (statements + branches), 509 → 584 tests.
- Handoff system resynced to engine v3.4 (2026-07-01): SessionStart hooks, `.codex/config.toml`, this file, and `TODO.md`'s section headings brought current; `docs/handoff/specs-plans.md` backfilled to index `docs/superpowers/specs/README.md`.
- Python Tooling standard review + fixes (2026-07-01): the §15 CI-workflow scaffold was invalid YAML (tab-indented) — repaired and byte-locked to the bundle artifact with drift tests; ruff floor raised to `>=0.14` (0.9–0.13 can't run `py314` non-preview); dead `pytest-cov` dropped from all dev groups; adopt CLI now delivers the full `.vscode/` trio (settings/tasks were silently missing); audit-note trail backfilled. 587 tests, 100% coverage.

## Current State

- Four standards defined: **Markdown Frontmatter** and **ADR** (enforced by a Python validator downstream repos run via a reusable CI workflow), **Markdown Tooling** (copy-adopt markdownlint/Prettier/EditorConfig), **Python Tooling SSOT** (copy-adopt scaffolds). **Python Coding** is an in-development reference-only draft, unregistered and excluded from validation/adopt.
- `testing` is ~58 commits ahead of `main` carrying validator strictness bumps (F29/F30/F37/F41/F46/F3/F4) not yet released.

## Recent Changes

- [2026-06-12] 55/58 validator findings implemented; coverage 93% → 100%, 584 tests; `3.0.0` released on `main`.
- [2026-07-01] Handoff-system-v3 resynced to engine v3.4.
- [2026-07-01] Python Tooling standard reviewed: 11 findings fixed (invalid §15 YAML, ruff floor, adopt `.vscode` gap, pytest-cov, doc↔bundle drift guards).
- [2026-07-01] Markdown standards swept for the same class: starter/caller/prettierrc doc fences byte-locked to bundles (starter example had dropped `**/*.template.md`); drift tests added.

## Notes For The Builder

- A CHANGELOG entry + version-bump decision for the `testing`-branch validator strictness bumps is still owed before the next release (see `TODO.md`).
- Residual out-of-scope gaps noted during the 2026-06-12 verification remain open in `format-frontmatter` (typo'd `--config` silently defaults and still writes files; non-UTF-8 input can traceback; doc_type enum read eagerly at import) and in `cli.py --help` text.
