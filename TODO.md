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

- [ ] `spec new` symlinked-parent edge cases.

  Informational, non-blocking. Revisit only if `new` adds engine-style path pre-validation beyond the current Linux target assumptions.

- [ ] OpenAPI 3.2.0 pin decision.

  Informational, non-blocking. Templates cite the unpinned OpenAPI Specification; pin only when a spec needs a specific contract dialect.

- [ ] Branch protection adoption.

  Research is complete; do not apply without explicit go-ahead. Apply near the next major release so required checks and PR review are coordinated with release flow.

  `main` already has rulesets for signed commits, non-fast-forward, and deletion. Remaining gaps: required status checks and PR reviews.

  Candidate checks: `check`, `prettier`, `lint`, `validate`, and `validate-specs`. Decide whether dependency review is N/A for this repo.

- [ ] MCP enablement program.

  Specs are ingested. Do not start MCP server code until the SPEC-MT01 readiness gate passes. Recheck MCP spec and SDK versions before SPEC-MS01 MS-0.

  SPEC-MT01 ADRs 0001-0013 are authored and accepted. SPEC-MS01 server ADRs remain deferred to the server phase.

  Future ADR themes: MCP boundary, resources-before-tools, SDK adapter, remote transport deferral, manifest resources, and plan-first controlled writes.

## 🚀 v5.0.0 Project Tracker — Meta-Repo Standards Platform (DURABLE)

<!-- DO NOT DELETE OR MOVE THIS SECTION, OR ANY COMPLETED ITEM WITHIN IT, UNTIL v5.0.0 IS RELEASED. -->

**Retention rule — this overrides the delete-completed instruction above.** Keep the full v5.0.0 progress history here until v5.0.0 ships.

Completed items stay checked and in order. Add new work as unchecked items and check it off with a date plus commit ref when done.

**Scope:** v5.0.0 implements SPEC-MT01 and all standards changes that land before the release. SPEC-MS01 server work is gated after the readiness gate.

**Working permissions:** individual sub-agents and headless Codex are allowed. Agent teams or `Workflow` orchestration still need approval and a cost sketch.

### ✅ Completed — retained history (do not remove)

- [x] 2026-07-07 - MCP enablement specs ingested (`76b09da`).
- [x] 2026-07-07 - ADR canonical directory set to `docs/adr/` (`7f12567`).
- [x] 2026-07-07 - Release-freeze policy set (`2c76096`).
- [x] 2026-07-07 - Dependabot security bump completed (`abc44bf`).
- [x] 2026-07-07 - SPEC-MT01 ADR foundation accepted (`ee98d0f`).
- [x] 2026-07-09 - Markdown Frontmatter value guidance and skill ownership done.
- [x] 2026-07-09 - Standard package methodology ADRs and compliance pass done.

### ⬜ Pending

Meta-repo readiness (`SPEC-MT01`), ordered — see SPEC-RD01 §19, Steps 00–07:

- [x] Step 00 - Baseline inventory (`194637e`).
- [x] Step 01 - ADR foundation accepted (`ee98d0f`).
- [x] Step 02 - Standard Bundle Authoring Standard implemented.
- [x] Step 03 - `standard.toml` manifest schema and fixtures implemented.
- [x] Step 04 - Standards graph validator implemented (`8d23a0c`).
- [x] Step 05 - Existing standards retrofitted with manifests.
- [ ] Step 06 - Dogfood fixtures, indexes, relationship catalog, and `adopt.toml` linkage.

  Step 06 now treats adoption-mode parity, package versions, artifact provenance, and repo-local skill installs as baseline graph/index facts.

- [ ] Step 07 - MCP-readiness gate passes.

Release cut (after readiness is complete):

- [ ] Promote CHANGELOG `[Unreleased]` to `## [5.0.0]`.
- [ ] Bump registry contracts, per-standard metadata, `pyproject`, and `uv.lock`.
- [ ] Run the `meta/versioning.md` release checklist.
- [ ] Lift the release freeze in `meta/versioning.md` and `docs/handoff/state.md`.
