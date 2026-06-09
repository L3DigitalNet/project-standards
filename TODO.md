# TODO **Do not delete.**

## Purpose

This document is the user's visible task list alongside the v3 handoff system. Use it to track action items, follow-ups, and personal notes that should stay easy to find instead of living only in agent-facing handoff docs.

## Usage Instructions

- Write each actionable item as an unchecked Markdown task: `- [ ]`.
- When an item is completed during a session, change its marker to `- [x]`.
- During v3 handoff closeout, delete completed items from this document.
- Mirror any handoff task, todo, pending item, or follow-up here so the user can track it.
- Do not start or complete TODO items unless the user explicitly asks for that work.

<!-- LLM-EDIT-BOUNDARY: DO NOT EDIT ABOVE THIS LINE -->

## User Tracked Tasks

## Repo & Agent Tracked Tasks

- [x] **Implement the frontmatter suite** — DONE 2026-06-09 on `testing` (Phases 0→A→B→C, subagent-driven, two-stage review + gate per phase). Ships `format-frontmatter`, `validate-references` (opt-in), `project-standards fix`, `validate` also runs references, `.pre-commit-hooks.yaml`. 423 tests, 92% cov, basedpyright 0/0/0, ruff clean, pip-audit clean; dogfood `format-frontmatter --check` + `project-standards validate`/`fix` clean on the repo.
- [x] **Decide the Task 0.5 invariant question** — RESOLVED 2026-06-09 (user-confirmed): `parse_frontmatter` rejects duplicate top-level keys (`validate`/`fix` + consumer CI now error on them). Documented as a contract-strictness bump in CHANGELOG 2.1.0.
- [ ] **Cut the `3.0.0` release — STAGED on `staging`, NOT yet on `main` (E3).** Full payload (adopt CLI + validate-id + frontmatter suite) implemented, codex-reviewed, release-readiness-reviewed ×5, green. Version **DECIDED: 3.0.0 (MAJOR)** — `validate-id` now runs in consumer CI + `parse_frontmatter` rejects duplicate keys (both `meta/versioning.md` previously-passing-rule triggers). The atomic `v2→v3` contract bump is **DONE on `staging`** in one signed commit (`afb3618`); tag/freeze/main-push remain for the all-at-once final push.
  - **Done on `staging` (commit `afb3618`, gate green at 3.0.0):**
    - [x] `pyproject.toml` 2.0.0→3.0.0 + `uv lock` (caller stub `{{ref}}` now renders `@v3` via `major_ref()`; dogfood test confirms).
    - [x] `project-standards.starter.yml` `standards_version` `v2`→`v3`.
    - [x] `validate-markdown-frontmatter.yml` `standards-ref` default `v2`→`v3` (the pin consumers inherit) + example comments `@v1`→`@v3`.
    - [x] `lint-markdown.yml` comment `@v2`→`@v3`.
    - [x] `.project-standards.yml` `standards_version` `v2.0.0`→`v3.0.0` (repo's own config).
    - [x] All four adopt guides + `README.md` + `meta/versioning.md` + `markdown-tooling/README.md` + `python-tooling/build-backend.md`: authored `@v1`/`@v2` pins → `@v3`; "next major" → `@v4`; availability facts ("first ships in 2.0.0") preserved as history.
    - [x] Straggler grep clean. `docs/python-backend.md` keeps illustrative `@v2` (scratch/advisory, not consumer-facing, out of validation scope) — intentional.
    - [x] `deployed.md` updated (commit `ef56e09`): v3.0.0 + moving v3 marked staged; v2 freezes AT the push (still the live moving 2.x tag until then).
  - **Deferred to the all-at-once `main` push (explicit user go ONLY):**
    - [ ] Fast-forward `main`→`staging`.
    - [ ] Signed tag `v3.0.0`; create moving `v3`; **freeze `v2`** (stop moving it — `@v2` trackers stay on 2.0.0).
    - [ ] GitHub release; flip `deployed.md` staged→published.
  - **Optional polish (behavior-neutral; for the review passes — NOT blocking the release):**
    - [ ] Schema `$id` floats on `main` — leave as-is (identity URI, not a fetch/validation pin; schema byte-stable across the major, so a new `$id` would wrongly re-identify an identical schema). Revisit only as a deliberate de-float to a stable schema-version path, never a moving git tag.
    - [ ] Filename prose: `adopt.md` §2/§6 tell humans to create `validate-standards.yml` while the `adopt` CLI scaffolds `validate-markdown-frontmatter.yml` — cosmetic (works under any name); align the prose or add a one-line note.
- [x] **Green the prettier/`format.yml` CI gate** — DONE 2026-06-09 (`281afe4`). Real failures were 13 `docs/codex-reviews/**` transcripts + 2 authored docs (`src/project_standards/README.md`, `standards/markdown-frontmatter/adopt.md`) — NOT the bundle scaffolds the earlier note guessed. Added `.prettierignore` (codex-reviews, handoff) + prettier-formatted the 2 authored docs; `prettier --check .` clean; format-frontmatter + markdownlint stay green.
