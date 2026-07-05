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

- [ ] **CHANGELOG entry for the 2026-06-12 validator strictness bumps before the next release.** Consumer-visible behavior changes on `testing`: F29 datetime frontmatter values now rejected (no time-truncation); F30 unquoted numeric config versions exit 2; F37 tags pattern tightened to `^[a-z0-9]+(-[a-z0-9]+)*$` (in-place 1.1 schema change); F41 duplicate config keys exit 2; F46 non-string frontmatter keys rejected; F3/F4 missing explicit files and typo'd `--config` exit 2 instead of passing green. Decide whether these ride a version bump per the previously-passing rule in `meta/versioning.md` (the 2.1.0 duplicate-key precedent documented a strictness bump in CHANGELOG). **Also cover the 2026-07-01 python-tooling changes:** ruff dev-group floor `>=0.9.0`→`>=0.14`, `pytest-cov` removed from the fragment/baseline, and `adopt python-tooling` now writing two new files (`.vscode/settings.json`, `.vscode/tasks.json`) — additive per the adopt engine's skip-existing rule, but a changed artifact list is consumer-visible. The 2026-07-01 consistency review also changed the frontmatter template id placeholders (`replace-with-stable-id` → format-teaching hints) and added the python-tooling pre-commit scope note — both docs-plane, worth a CHANGELOG line.
- [ ] **Residual out-of-scope gaps from the 2026-06-12 verification** (adjacent files, outside the review target): `format-frontmatter` still silently defaults on a typo'd `--config` (and it _writes_ files), can traceback on non-UTF-8 input (F1/F4 class; `format_frontmatter.py:597,651`), and reads its doc_type enum eagerly at import from the default schema (F11/F27 class); `project-standards validate --help` still says "Additional glob pattern" (`cli.py:188`, F42 class).
- [ ] **Project-spec follow-on:** write README §6 Adoption and decide/register the `project-spec` standard. Spec #1 (read-only `validate|lint|extract|next`) and Spec #2 (`spec new` scaffold, `8d48c22`) are both implemented on `testing`; only the `upgrade` authoring command remains, deferred to **Spec #3** (the mutation-risk seam). When `project-spec` is registered/released, add a CHANGELOG line for the `spec new` command surface.
- [ ] **(Informational) `spec new` symlinked-parent edge cases** (from Spec #2 final + security review, pre-existing, not regressions — do not block): (a) a deliberate above-cwd relative write like `spec new ../sibling/x.md` gets partial/arbitrary ancestor checking because pathlib does not normalize `..` before the `is_relative_to` bound; (b) a TOCTOU window exists between the parent-symlink check and `mkstemp`/`os.replace` (shared with `adopt/engine._atomic_write`). Both are acceptable for the Linux target; revisit only if `new` grows an engine-style `..`-rejecting pre-validation of `args.path`.
- [ ] **(Informational) OpenAPI is now 3.2.0 (2025-09-19).** The `project-spec` templates cite "OpenAPI Specification" unpinned, so no change is required; pin to 3.2.0 only if a spec needs a specific contract dialect. Recorded in the README §10 Source register (verified 2026-07-04).
- [ ] **Deferred spec-tooling code-review findings (2026-07-05 `/code-review high spec`).** Three 🔴 validator false-rejections were fixed in `7b9754e` (SV-TABLE inline/escaped pipes, SV-ANCHOR repeated-heading anchors, `_OMIT` em-dash). Remaining, deferred by user decision:
  - 🟡 **`next_id.py:19` — hard `:03d` width.** Once a prefix passes 999 (or `MS` passes 9), `spec next` returns e.g. `FR-1000` (4 digits) that the validator's SV-ID-FMT rule then rejects — the tool hands out an ID its own validator forbids. Widen or cap-and-warn.
  - 🟡 **`next_id.py:11` — tier default disagreement.** `next` uses `doc.profile or "full"` while `validate._check_ids` uses `doc.profile or ""`; on a profile-less spec they disagree on tier-valid prefixes, so `next` can mint an ID `validate` immediately flags SV-ID-TIER. (Low real impact: a profile-less spec already fails `validate`.) Align the default.
  - 🟡 **`lint.py:45` — `_must_frs` exact `== 'Must'`.** `MUST`/`must` casing makes a mandatory FR invisible to the §17.3 traceability check, silently under-reporting SL-TRACE. Case-fold the priority compare.
  - 🟢 **`document.py:68` — O(n²) line-number scan.** `body[:m.start()].count('\n')` per ID token rescans the whole prefix each time; precompute a newline-offset table for linear parsing. No wrong output today.
  - 🟢 **`document.py:70` / `validate.py:97` — duplicated regexes.** `_DECLARE_ROW` re-implements `registry.declared_prefixes`, and the `^## Appendix ([A-Z]):` letter regex is a third copy (also `extract.py:22`). Drift risk — consolidate into the `registry` helpers (which `upgrade` will reuse, so worth doing before Spec #3 implementation).
