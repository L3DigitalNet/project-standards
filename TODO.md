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
    - Note: the specs' own `related.adrs` frontmatter uses placeholder `adr-NNNN` names under `docs/adr/`; assign real zero-padded numbers when authored. The ADR standard now prescribes **`docs/adr/`** as its canonical ADR directory (corrected 2026-07-07 per owner directive; was `docs/decisions/`) — recorded in CHANGELOG `[Unreleased]` (`adr` contract `1.0`→`1.1`). Under the **release freeze**, this ships in **v5.0.0** — the `registry.json`/version-metadata bump happens at that cut, not a separate release.

## 🚀 v5.0.0 Project Tracker — Meta-Repo Standards Platform (DURABLE)

<!-- DO NOT DELETE OR MOVE THIS SECTION, OR ANY COMPLETED ITEM WITHIN IT, UNTIL v5.0.0 IS RELEASED. -->

**Retention rule — this OVERRIDES the "delete completed items" instruction at the top of this file.** This is the durable, user-facing progress log for the **v5.0.0** release. Keep the **full history** here until v5.0.0 ships:

- **Never delete, move, or un-check a completed (`- [x]`) item.** Completed items stay in place, in order, as the release's running history.
- Add new work as unchecked items; check them off with a date + commit ref when done.
- Only after v5.0.0 is tagged and released may the owner archive or prune this section.

**Scope:** v5.0.0 = implement the Meta-repo readiness spec (`SPEC-MT01`) + every standards change that lands before the release (per the freeze in `meta/versioning.md`). The MCP _server_ itself (`SPEC-MS01`) is gated after the readiness gate and belongs to a later release, not v5.0.0. Specs + paths: `docs/handoff/specs-plans.md`.

**Working permissions (owner-granted 2026-07-07, active until v5.0.0 releases):** agent teams, subagents, and headless Codex may be used freely for this build-out without asking each time — models **Sonnet** (mechanical/parallel) or **Opus** (complex) by task complexity, **never Fable or Haiku**. This permission expires at the v5.0.0 release.

### ✅ Completed — retained history (do not remove)

- [x] **2026-07-07 — MCP enablement specs ingested** (`76b09da`) — SPEC-MT01/RD01/MS01 (Full project specs) + reference pack placed under `docs/superpowers/`, wired into `spec.include`, the spec index, and handoff.
- [x] **2026-07-07 — ADR standard canonical directory → `docs/adr/`** (`7f12567`) — standards change accruing to v5.0.0; `adr` contract `1.0`→`1.1` (registry bump applied at the release cut).
- [x] **2026-07-07 — Release-freeze policy set** (`2c76096`) — no interim patch/minor releases; version-affecting changes roll into v5.0.0.
- [x] **2026-07-07 — Dependabot security bump** (`abc44bf`) — `markdownlint-cli2` `0.22.1`→`0.23.0` (markdownlint `0.41.0`) + reusable-workflow action `v23`→`v24` + `test_pins.py`. Cleared 2 moderate npm DoS alerts (js-yaml→`5.2.0`, markdown-it→`14.2.0`); `npm audit` 0 vulns; 85-file corpus lints clean under 0.41; coherence 8/8, 868 tests green.

### ⬜ Pending

Meta-repo readiness (`SPEC-MT01`), ordered — see SPEC-RD01 §19, Steps 00–07:

- [x] **Step 00 — Baseline inventory** of standards, registry, bundles, manifests, validators, tests, and workflows. — done 2026-07-07 (`194637e`); deliverable: `docs/superpowers/research/2026-07-07-spec-mt01-baseline-inventory.md`.
- [ ] **Step 01 — ADR foundation:** author the required ADR set under `docs/adr/` (the 13+ ADRs listed in the MCP program item above).
- [ ] **Step 02 — Standard Bundle Authoring Standard** (the meta-standard) drafted.
- [ ] **Step 03 — `standard.toml` manifest** schema/model + valid/invalid fixtures.
- [ ] **Step 04 — Standards graph validator** (authority / capability / resource / relationship, including hidden-dependency rejection) + CLI.
- [ ] **Step 05 — Retrofit** every existing standard with a manifest, authorities, and resources.
- [ ] **Step 06 — Dogfood fixtures** + generated standards index + relationship catalog.
- [ ] **Step 07 — MCP-readiness gate** passes (no blocking gaps, no hidden hard dependencies, no stale generated indexes).

Release cut (after readiness is complete):

- [ ] Promote CHANGELOG `[Unreleased]` → `## [5.0.0]` with consumer migration notes.
- [ ] Bump `registry.json` contract versions (incl. `adr 1.1`) + per-standard version metadata + `pyproject` + `uv.lock`.
- [ ] Run the `meta/versioning.md` release checklist (pin bumps, `UPGRADING.md`, signed `v5.0.0` + moving `v5` tags, GitHub release).
- [ ] Lift the release freeze in `meta/versioning.md` and `docs/handoff/state.md`.
