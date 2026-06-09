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
- [ ] **Cut the `3.0.0` release — HELD (E3).** The full payload (adopt CLI + validate-id + frontmatter suite) is **implemented, codex-reviewed, release-readiness-reviewed ×2, and green on `testing`**. Version **DECIDED: 3.0.0 (MAJOR)** — `validate-id` now runs in consumer CI + `parse_frontmatter` rejects duplicate keys (both `meta/versioning.md` previously-passing-rule triggers). **Round-2 decision (user): leave consumer pins as-is on `testing` and reconcile ALL of them ATOMICALLY at E3** (the caller stub auto-bumps via `major_ref()` once `pyproject`→3.0.0; everything else is a manual edit). Run E3 only on explicit user go — atomic `v2→v3` bump in one signed commit:
  - [ ] `pyproject.toml` `version` 2.0.0→3.0.0 + `uv lock` (this auto-renders the caller stub `{{ref}}`→`v3`).
  - [ ] `src/project_standards/bundles/markdown-frontmatter/project-standards.starter.yml` `standards_version: "v2"`→`"v3"`.
  - [ ] `.github/workflows/validate-markdown-frontmatter.yml` `standards-ref` `default: "v2"`→`"v3"` (~line 44) + the example-comment `@v1`→`@v3` (~lines 24/27).
  - [ ] `standards/markdown-frontmatter/adopt.md` is already `@v3` (round 1) EXCEPT the "defaults to the major tag `v2`" note (~line 123)→`v3`; also `lint-markdown.yml@v2`→`@v3`.
  - [ ] The OTHER 3 adopt guides' `@v2`/"As of v2" quick-paths → `@v3`: `standards/adr/adopt.md`, `standards/python-tooling/adopt.md`, `standards/markdown-tooling/adopt.md`.
  - [ ] `README.md` stale pinning examples `@v1`/`@v2` (~lines 96/117/125) → `@v3`.
  - [ ] `src/project_standards/schemas/markdown-frontmatter.schema.json` `$id` pins `main` → consider `v3.0.0` path (minor; identity URI only).
  - [ ] Reconcile the workflow-filename guidance: `adopt.md` §2/§6 say create `validate-standards.yml` but `adopt` delivers `validate-markdown-frontmatter.yml` (cosmetic — consumer can name it anything; align the prose or note it).
  - [ ] Tag `v3.0.0` (signed); **freeze `v2`** at `v2.0.0`; create moving `v3`; update `deployed.md`; GitHub release.
- [x] **Green the prettier/`format.yml` CI gate** — DONE 2026-06-09 (`281afe4`). Real failures were 13 `docs/codex-reviews/**` transcripts + 2 authored docs (`src/project_standards/README.md`, `standards/markdown-frontmatter/adopt.md`) — NOT the bundle scaffolds the earlier note guessed. Added `.prettierignore` (codex-reviews, handoff) + prettier-formatted the 2 authored docs; `prettier --check .` clean; format-frontmatter + markdownlint stay green.
