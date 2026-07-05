# Project Status

This is the human-facing completion summary for the project. Agents maintain it so the project builder can re-orient quickly.

## Completed

- `3.0.0` released on `main` (2026-06-12; tags `v3.0.0`/`v3`; `v2` frozen at `3ece2c9`; GitHub release live).
- Validator review pass (Fable, 2026-06-12): 58 findings across `src/` validation files, 55 implemented (one commit per finding, `f8c9697`…`9da01a9`), 3 skipped with recorded rationale. Headliners: UnicodeDecodeError crashes at read boundaries, `--fix` corrupting block-scalar ids while reporting success, silent green CI on missing files / typo'd `--config`.
- Test-suite exhaustiveness pass (2026-06-12, `c55ca81`): coverage 93% → 100% (statements + branches), 509 → 584 tests.
- Handoff system resynced to engine v3.4 (2026-07-01): SessionStart hooks, `.codex/config.toml`, this file, and `TODO.md`'s section headings brought current; `docs/handoff/specs-plans.md` backfilled to index `docs/superpowers/specs/README.md`.
- Python Tooling standard review + fixes (2026-07-01): the §15 CI-workflow scaffold was invalid YAML (tab-indented) — repaired and byte-locked to the bundle artifact with drift tests; ruff floor raised to `>=0.14` (0.9–0.13 can't run `py314` non-preview); dead `pytest-cov` dropped from all dev groups; adopt CLI now delivers the full `.vscode/` trio (settings/tasks were silently missing); audit-note trail backfilled. 587 tests, 100% coverage.
- **`project-spec` (5th standard) README authored (2026-07-04):** an in-development draft (unregistered, excluded from validation). §1–§10 written except §6 Adoption (parked pending tooling). Guarantee-driven: §3 Features = 8 guarantees (G1–G8); §5 Tooling = a capability set traced to them (`validate`/`lint`/`extract`/`next`/`new`/`upgrade` core + `status` planned + agent review contract). Fixed 3 pre-existing red gates the earlier project-spec commits introduced un-gated (frontmatter, markdownlint, ruff). Full gate green.
- **project-spec tooling Spec #1 designed + planned (2026-07-04):** brainstormed → spec (`docs/superpowers/specs/2026-07-04-project-spec-tooling-design.md`) → 12-task TDD plan (`docs/superpowers/plans/2026-07-04-project-spec-tooling-spec1.md`), both codex-converged (spec 2 passes, plan 3 passes; 24 findings applied total). Scope = registry core + read-only `spec validate|lint|extract|next`; `new`/`upgrade` deferred to Spec #2; `check_specs.py` retired into pytest. Implementation to be done by Codex in a parallel session.

## Current State

- Four standards defined: **Markdown Frontmatter** and **ADR** (enforced by a Python validator downstream repos run via a reusable CI workflow), **Markdown Tooling** (copy-adopt markdownlint/Prettier/EditorConfig), **Python Tooling SSOT** (copy-adopt scaffolds). **Python Coding** and **Project Specification** are in-development drafts, unregistered and excluded from validation/adopt.
- `testing` is ~65 commits ahead of `main` carrying validator strictness bumps (F29/F30/F37/F41/F46/F3/F4) not yet released.

## Recent Changes

- [2026-06-12] 55/58 validator findings implemented; coverage 93% → 100%, 584 tests; `3.0.0` released on `main`.
- [2026-07-01] Handoff-system-v3 resynced to engine v3.4.
- [2026-07-01] Python Tooling standard reviewed: 11 findings fixed (invalid §15 YAML, ruff floor, adopt `.vscode` gap, pytest-cov, doc↔bundle drift guards).
- [2026-07-01] Markdown standards swept for the same class: starter/caller/prettierrc doc fences byte-locked to bundles (starter example had dropped `**/*.template.md`); drift tests added.
- [2026-07-01] Full cross-standard consistency review: combined adoption of all four standards verified collision-free with every gate passing; pre-commit ban vs frontmatter hooks resolved (scope note), stale tags pattern, template id placeholders, and two missing md-tooling adopt steps fixed.
- [2026-07-04] `project-spec` README §1–§10 authored (minus §6 Adoption); 8 guarantees + guarantee-traced tooling capability set defined; 3 pre-existing red gates from the un-gated project-spec commits fixed.
- [2026-07-04] project-spec tooling Spec #1 designed + planned (both codex-converged). Next: Codex implements Spec #1 from the plan in a parallel session.

## Notes For The Builder

- A CHANGELOG entry + version-bump decision for the `testing`-branch validator strictness bumps is still owed before the next release (see `TODO.md`).
- Residual out-of-scope gaps noted during the 2026-06-12 verification remain open in `format-frontmatter` (typo'd `--config` silently defaults and still writes files; non-UTF-8 input can traceback; doc_type enum read eagerly at import) and in `cli.py --help` text.
