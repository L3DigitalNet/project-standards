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

- [x] **DONE 2026-06-12 — v3.0.0 released.** Fast-forwarded `main`→`staging`; signed tag `v3.0.0` + moving `v3` published; `v2` frozen; GitHub release live; `deployed.md` flipped staged→published. `staging` deleted; `testing` fast-forwarded to `main`.

## Repo & Agent Tracked Tasks

- [x] **Implement the frontmatter suite** — DONE 2026-06-09 on `testing` (Phases 0→A→B→C, subagent-driven, two-stage review + gate per phase). Ships `format-frontmatter`, `validate-references` (opt-in), `project-standards fix`, `validate` also runs references, `.pre-commit-hooks.yaml`. 423 tests, 92% cov, basedpyright 0/0/0, ruff clean, pip-audit clean; dogfood `format-frontmatter --check` + `project-standards validate`/`fix` clean on the repo.
- [x] **Decide the Task 0.5 invariant question** — RESOLVED 2026-06-09 (user-confirmed): `parse_frontmatter` rejects duplicate top-level keys (`validate`/`fix` + consumer CI now error on them). Documented as a contract-strictness bump in CHANGELOG 2.1.0.
- [x] **Cut the `3.0.0` release — DONE 2026-06-12.** `main` at `2320d37`; tags `v3.0.0` + `v3` published; `v2` frozen; GitHub release live; `deployed.md` published.
- [x] **Green the prettier/`format.yml` CI gate** — DONE 2026-06-09 (`281afe4`). Real failures were 13 `docs/codex-reviews/**` transcripts + 2 authored docs (`src/project_standards/README.md`, `standards/markdown-frontmatter/adopt.md`) — NOT the bundle scaffolds the earlier note guessed. Added `.prettierignore` (codex-reviews, handoff) + prettier-formatted the 2 authored docs; `prettier --check .` clean; format-frontmatter + markdownlint stay green.
