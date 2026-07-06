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

- [ ] Adopt the branch protection strategy and PR requirements from the `hw-radar` repo.

## Agent Tracked Tasks

- [ ] **Spec B (F5 markdown-tooling formatter authority) — ready to implement.** Spec `a564163` + 10-task TDD plan `da01e97` on `testing`, both codex-converged (spec 5 passes / plan 4 passes, "no significant findings"). Ships an OPT-IN reusable repo-wide Prettier gate (`format.yml` + `format.caller.yml`) superseding DEC-9 via a new DEC-10; additive ⇒ MINOR (`markdown_tooling 1.0→1.1`, tool `v4.x`; `@v4` + `lint-markdown.yml` untouched) + a repo-local coherence tool (`tests/coherence/`). Execute via subagent-driven-development. When released, add a CHANGELOG line (already drafted in the plan's Task 9).
- [ ] **(Informational, do not block) `spec new` symlinked-parent edge cases** (from Spec #2 final + security review, pre-existing, not regressions): (a) a deliberate above-cwd relative write like `spec new ../sibling/x.md` gets partial/arbitrary ancestor checking because pathlib does not normalize `..` before the `is_relative_to` bound; (b) a TOCTOU window exists between the parent-symlink check and `mkstemp`/`os.replace` (shared with `adopt/engine._atomic_write`). Both are acceptable for the Linux target; revisit only if `new` grows an engine-style `..`-rejecting pre-validation of `args.path`.
- [ ] **(Informational, do not block) OpenAPI is now 3.2.0 (2025-09-19).** The `project-spec` templates cite "OpenAPI Specification" unpinned, so no change is required; pin to 3.2.0 only if a spec needs a specific contract dialect. Recorded in the README §10 Source register (verified 2026-07-04).
- [ ] **Branch protection adoption plan** (research complete for the user task above; not yet applied — do not apply without explicit go-ahead). Gathered via `gh api repos/L3DigitalNet/hw-radar/branches/main/protection` + repo file inspection:
  - **Timing:** apply at the next major release, not now — enabling required-PR/status-check protection on `main` needs to be coordinated with that release's first PR merge (rather than sprung on a workflow that currently allows direct pushes to `main`).
  - **hw-radar's actual config** (classic branch protection, not a ruleset — `gh api .../rulesets` returned `[]`): protects `main` only, `dev` is unprotected (404). Required status checks `["check", "dependency-review"]` (`strict: true`, both `app_id: 15368` = GitHub Actions), `required_pull_request_reviews` present with `dismiss_stale_reviews: true`, `require_code_owner_reviews: false`, `required_approving_review_count: 0`, `required_signatures: true`, `enforce_admins: true`, `required_conversation_resolution: true`, `allow_force_pushes: false`, `allow_deletions: false`, `required_linear_history: false`.
  - **Why those two checks:** hw-radar's `check.yml` job is named `check` (fmt/lint/type/test/cov/audit gate) and runs on push-to-main/dev + all PRs. `dependency-review.yml` job is named `dependency-review`, **PR-only** (OQ20-ratified OSS-license allowlist gate over `uv.lock` via `dependency-review-action`) — deliberately excluded from `push` so it only gates PRs, not direct-to-branch commits (documented gap, spec §16 covers the manual fallback).
  - **project-standards current state:** `main` has **no** branch protection (`gh api .../branches/main/protection` → 404). Five CI workflows exist, all on `push: main` + `pull_request`, with job names: `check` (check.yml), `prettier` (format.yml), `lint` (lint-markdown.yml), `validate` (validate-markdown-frontmatter.yml), `validate-specs` (validate-specs.yml). No `dependency-review.yml` equivalent exists yet — project-standards ships Python tooling scaffolds/validators, not a locked runtime dependency set, so a license-gate workflow isn't a direct port; decide during implementation whether it's needed or N/A.
  - **Adoption steps (not yet executed):** (1) enable classic protection on `main` requiring the 5 existing job-name contexts (`check`, `prettier`, `lint`, `validate`, `validate-specs`) with `strict: true`; (2) set `required_pull_request_reviews` (`dismiss_stale_reviews: true`, `required_approving_review_count: 0` to match hw-radar's solo-maintainer posture, `require_code_owner_reviews: false`); (3) set `required_signatures: true` (repo already commits under GPG key `9375AFEFA6F841B0` per global git policy); (4) set `enforce_admins: true`, `required_conversation_resolution: true`, `allow_force_pushes: false`, `allow_deletions: false`; (5) leave `testing` unprotected, mirroring hw-radar's unprotected `dev` (the working branch merges to `main` for release, per existing `docs/handoff/state.md` release flow); (6) apply via `gh api repos/L3DigitalNet/project-standards/branches/main/protection -X PUT --input -` with a JSON payload (mirrors `hw-radar`'s), or the repo Settings UI; (7) decide on a `dependency-review.yml` port — likely deferred/N/A absent locked runtime deps.
