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

- [ ] **(Informational, do not block) `spec new` symlinked-parent edge cases** (from Spec #2 final + security review, pre-existing, not regressions): (a) a deliberate above-cwd relative write like `spec new ../sibling/x.md` gets partial/arbitrary ancestor checking because pathlib does not normalize `..` before the `is_relative_to` bound; (b) a TOCTOU window exists between the parent-symlink check and `mkstemp`/`os.replace` (shared with `adopt/engine._atomic_write`). Both are acceptable for the Linux target; revisit only if `new` grows an engine-style `..`-rejecting pre-validation of `args.path`.
- [ ] **(Informational, do not block) OpenAPI is now 3.2.0 (2025-09-19).** The `project-spec` templates cite "OpenAPI Specification" unpinned, so no change is required; pin to 3.2.0 only if a spec needs a specific contract dialect. Recorded in the README §10 Source register (verified 2026-07-04).
- [ ] **Dependabot: bump markdownlint-cli2 `0.22.1` → `0.23.0` (coordinated pin bump; needs user go-ahead).** Two open moderate npm alerts (js-yaml ≤4.1.1 merge-key quadratic DoS GHSA-h67p-54hq-rp68; markdown-it ≤14.1.1 smartquotes quadratic DoS GHSA-6v5v-wf23-fmfq) — both transitive deps of the pinned dev-only `markdownlint-cli2@0.22.1`; not shipped, dev-tooling exposure only. The pin exists because it mirrors what `markdownlint-cli2-action@v23` bundles (see `tests/coherence/test_pins.py` — local↔CI co-satisfaction). Upstream `markdownlint-cli2-action@v24.0.0` (2026-07-03) bundles the fixed `0.23.0` + markdownlint `0.41.0`, so the fix is: bump the `package.json` pin + `test_pins.py` + the action ref in `lint-markdown.yml` **together**, re-run the coherence behavioral corpus, and check whether markdownlint 0.40→0.41 rule changes affect the corpus or downstream consumers of the reusable workflow (if consumer-visible, it's a versioned change per `meta/versioning.md`, not a silent bump). Investigated 2026-07-07 post-v4.3.0.
- [ ] **Branch protection adoption plan** (research complete for the user task above; not yet applied — do not apply without explicit go-ahead). Gathered via `gh api repos/L3DigitalNet/hw-radar/branches/main/protection` + repo file inspection:
  - **Timing:** apply at the next major release, not now — enabling required-PR/status-check protection on `main` needs to be coordinated with that release's first PR merge (rather than sprung on a workflow that currently allows direct pushes to `main`).
  - **hw-radar's actual config** (classic branch protection, not a ruleset — `gh api .../rulesets` returned `[]`): protects `main` only, `dev` is unprotected (404). Required status checks `["check", "dependency-review"]` (`strict: true`, both `app_id: 15368` = GitHub Actions), `required_pull_request_reviews` present with `dismiss_stale_reviews: true`, `require_code_owner_reviews: false`, `required_approving_review_count: 0`, `required_signatures: true`, `enforce_admins: true`, `required_conversation_resolution: true`, `allow_force_pushes: false`, `allow_deletions: false`, `required_linear_history: false`.
  - **Why those two checks:** hw-radar's `check.yml` job is named `check` (fmt/lint/type/test/cov/audit gate) and runs on push-to-main/dev + all PRs. `dependency-review.yml` job is named `dependency-review`, **PR-only** (OQ20-ratified OSS-license allowlist gate over `uv.lock` via `dependency-review-action`) — deliberately excluded from `push` so it only gates PRs, not direct-to-branch commits (documented gap, spec §16 covers the manual fallback).
  - **project-standards current state (updated 2026-07-06 — PARTIALLY DONE out-of-band):** `main` now carries a **ruleset** `release-pipeline` (added between this research and the v4.2.0 release) enforcing `required_signatures` + `non_fast_forward` + `deletion` — but **NOT** required status checks or PR reviews. It is a _ruleset_, not classic protection (`gh api .../branches/main/protection` is still 404; inspect via `gh api .../rulesets`). A companion ruleset `release-pipeline-tags` makes `v*.*.*` tags immutable (blocks deletion + non-fast-forward). So steps (3) signatures and part of (4) force-push/deletion below are effectively satisfied via rulesets; the remaining gap is step (1) required status checks + step (2) PR reviews. (The v4.2.0 release hit this live: unsigned prior-session commits were rejected by `main` and had to be re-signed via rebase.) Five CI workflows exist, all on `push: main` + `pull_request`, with job names: `check` (check.yml), `prettier` (format.yml), `lint` (lint-markdown.yml), `validate` (validate-markdown-frontmatter.yml), `validate-specs` (validate-specs.yml). No `dependency-review.yml` equivalent exists yet — project-standards ships Python tooling scaffolds/validators, not a locked runtime dependency set, so a license-gate workflow isn't a direct port; decide during implementation whether it's needed or N/A.
  - **Adoption steps (not yet executed):** (1) enable classic protection on `main` requiring the 5 existing job-name contexts (`check`, `prettier`, `lint`, `validate`, `validate-specs`) with `strict: true`; (2) set `required_pull_request_reviews` (`dismiss_stale_reviews: true`, `required_approving_review_count: 0` to match hw-radar's solo-maintainer posture, `require_code_owner_reviews: false`); (3) set `required_signatures: true` (repo already commits under GPG key `9375AFEFA6F841B0` per global git policy); (4) set `enforce_admins: true`, `required_conversation_resolution: true`, `allow_force_pushes: false`, `allow_deletions: false`; (5) leave `testing` unprotected, mirroring hw-radar's unprotected `dev` (the working branch merges to `main` for release, per existing `docs/handoff/state.md` release flow); (6) apply via `gh api repos/L3DigitalNet/project-standards/branches/main/protection -X PUT --input -` with a JSON payload (mirrors `hw-radar`'s), or the repo Settings UI; (7) decide on a `dependency-review.yml` port — likely deferred/N/A absent locked runtime deps.
- [ ] **MCP enablement program (specs ingested 2026-07-07; NOT started — do not begin implementation without explicit go-ahead).** Ordered, gated work; MCP server code must not start until **SPEC-MT01**'s readiness gate passes (**SPEC-RD01** Step 07). Specs + paths in `docs/handoff/specs-plans.md`. Before any SPEC-MS01 work, **recheck version-sensitive MCP references** — the MCP spec revision and the official Python SDK stable/pre-release line (REF-OQ-003 / SPEC-MS01 MS-0); do not rely on the July-2026 assumptions frozen in the reference pack.
  - **ADR backlog (→ `docs/adr/`, `adr-NNNN-...`; none created yet).** Each spec's §8.3 enumerates its full ADR set; the minimum required across the program is:
    1. Standard bundle authoring contract (SPEC-MT01)
    2. Manifest-first standard discovery (SPEC-MT01)
    3. Separate standard and artifact manifests (SPEC-MT01)
    4. Authority map and conflict-free composition (SPEC-MT01)
    5. Independent standard packages and relationship taxonomy (all three specs — the through-line principle)
    6. Stable generic agent/MCP tooling interface (SPEC-MT01/RD01)
    7. Standard provider / plugin model (SPEC-MT01)
    8. Standard graph validation gate (SPEC-MT01)
    9. Local stdio-first MCP transport (SPEC-RD01/MS01)
    10. Read-only-first / controlled-write-later (SPEC-RD01/MS01)
    11. MCP protocol and SDK version selection (SPEC-RD01/MS01)
    12. MCP roots and repo boundary policy (SPEC-MS01)
    13. MCP capability advertisement policy (SPEC-MS01)
    - Plus (from the specs' §8.3, same backlog): MCP-readiness-before-server-implementation, consumer-config-namespace-registry, agent-summary-vs-canonical-standard split, standard-resource-URIs-and-index, dogfood-consumer-fixtures-for-composition, MCP-server-boundary, MCP-resources-before-tools, MCP-SDK-adapter-boundary, remote-MCP-transport-deferred, manifest-generated-MCP-resources, plan-first-controlled-writes.
    - Note: the specs' own `related.adrs` frontmatter uses placeholder `adr-NNNN` names under `docs/adr/`; assign real zero-padded numbers when authored. The ADR standard documents `docs/decisions/` as its default index dir, but this repo uses **`docs/adr/`** per owner directive (2026-07-07) — reconcile the ADR standard's stated default vs this repo's actual dir if/when an ADR system is stood up here.
