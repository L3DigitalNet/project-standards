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

- [ ] Disable markdownlint MD060. It conflicts with Prettier.

## Agent Tracked Tasks

- [ ] **CHANGELOG entry for the 2026-06-12 validator strictness bumps before the next release.** Consumer-visible behavior changes on `testing`: F29 datetime frontmatter values now rejected (no time-truncation); F30 unquoted numeric config versions exit 2; F37 tags pattern tightened to `^[a-z0-9]+(-[a-z0-9]+)*$` (in-place 1.1 schema change); F41 duplicate config keys exit 2; F46 non-string frontmatter keys rejected; F3/F4 missing explicit files and typo'd `--config` exit 2 instead of passing green. Decide whether these ride a version bump per the previously-passing rule in `meta/versioning.md` (the 2.1.0 duplicate-key precedent documented a strictness bump in CHANGELOG).
- [ ] **Residual out-of-scope gaps from the 2026-06-12 verification** (adjacent files, outside the review target): `format-frontmatter` still silently defaults on a typo'd `--config` (and it _writes_ files), can traceback on non-UTF-8 input (F1/F4 class; `format_frontmatter.py:597,651`), and reads its doc_type enum eagerly at import from the default schema (F11/F27 class); `project-standards validate --help` still says "Additional glob pattern" (`cli.py:188`, F42 class).
