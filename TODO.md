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
- [ ] **Cut the `2.1.0` release — HELD (E3).** The full 2.1.0 payload (adopt CLI + validate-id + frontmatter suite) is now **implemented and green on `testing`**. Run E3 only on explicit user go: decide the version number first (`validate-id`-in-CI may be MAJOR per `meta/versioning.md §3`), then version bump + `uv.lock` + dated changelog in one commit, signed tag `v2.1.0`, move `v2`, update `deployed.md`.
- [x] **Green the prettier/`format.yml` CI gate** — DONE 2026-06-09 (`281afe4`). Real failures were 13 `docs/codex-reviews/**` transcripts + 2 authored docs (`src/project_standards/README.md`, `standards/markdown-frontmatter/adopt.md`) — NOT the bundle scaffolds the earlier note guessed. Added `.prettierignore` (codex-reviews, handoff) + prettier-formatted the 2 authored docs; `prettier --check .` clean; format-frontmatter + markdownlint stay green.
