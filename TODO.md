# TODO

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

- [ ] Fix markdownlint MD060. It conflicts with Prettier.

## Agent Tracked Tasks

- [ ] **(Informational, do not block) `spec new` symlinked-parent edge cases** (from Spec #2 final + security review, pre-existing, not regressions): (a) a deliberate above-cwd relative write like `spec new ../sibling/x.md` gets partial/arbitrary ancestor checking because pathlib does not normalize `..` before the `is_relative_to` bound; (b) a TOCTOU window exists between the parent-symlink check and `mkstemp`/`os.replace` (shared with `adopt/engine._atomic_write`). Both are acceptable for the Linux target; revisit only if `new` grows an engine-style `..`-rejecting pre-validation of `args.path`.
- [ ] **(Informational, do not block) OpenAPI is now 3.2.0 (2025-09-19).** The `project-spec` templates cite "OpenAPI Specification" unpinned, so no change is required; pin to 3.2.0 only if a spec needs a specific contract dialect. Recorded in the README §10 Source register (verified 2026-07-04).
- [ ] **Cut the v4.0.0 release when ready.** `CHANGELOG.md`'s `[Unreleased]` section is fully itemized and classified — see its release-planning note. Follow `meta/versioning.md`'s release-requirements checklist (tag, move the moving major, write migration notes, update the changelog section header).
