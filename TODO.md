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

- [ ] **Cut the `2.1.0` release (adopt CLI) — HELD.** Adopt CLI is implemented + green on `testing` (plan A–E2, commits `7d6a773…865710f`). Before running E3: (a) roll in the other items intended for this release (e.g. `validate-id`); (b) get the full SSOT gate green (untested `validate_id.py` → coverage 82%; resolve the 88-col editor reformats vs repo `line-length = 100`). Then E3 = version bump + `uv.lock` + dated changelog in one commit, signed tag `v2.1.0`, move `v2`, update `deployed.md`.
