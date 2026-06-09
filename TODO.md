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

- [ ] **Implement the frontmatter suite** — plan `docs/superpowers/plans/2026-06-08-frontmatter-suite.md` (codex spec ×3 + plan ×4, converged; ~26 TDD tasks, Phase 0→A→B→C). Builds `format-frontmatter` (autoformatter), `validate-references` (opt-in semantics), `project-standards fix`, and `.pre-commit-hooks.yaml`. Execute subagent-driven; toolchain gate after each phase.
- [ ] **Decide the Task 0.5 invariant question** (before/at implementation). The plan rejects duplicate top-level keys in `parse_frontmatter` — a documented narrow exception to "no consumer newly-fails". Confirm that exception, or scope duplicate-key detection to the formatter only (the tokenizer already refuses them).
- [ ] **Cut the `2.1.0` release — HELD (E3).** `2.1.0` bundles the adopt CLI + `validate-id` (both implemented + green on `testing`, 299 tests / 91% / gate green) **and** the frontmatter suite (above, not yet built). Run E3 only after the suite is implemented and the full gate is green: version bump + `uv.lock` + dated changelog in one commit, signed tag `v2.1.0`, move `v2`, update `deployed.md`. Resume only on explicit user go.
- [ ] **Green the prettier/`format.yml` CI gate.** `npx prettier --check .` is latently red on `docs/codex-reviews/**` (13 regenerated transcripts) + `src/project_standards/bundles/*` (5 shipped scaffolds with intentional placeholders); there is no `.prettierignore`. Recommended fix: add a `.prettierignore` mirroring the `.markdownlint-cli2.jsonc` `ignores` (`codex-reviews`, `handoff`), then decide whether to prettier-format the bundle scaffolds or ignore them too. (markdownlint's counterpart was scoped + greened 2026-06-09, commit `ec2b517`.)
