# Project Tasks

## Purpose

This document is the user-visible and agent-visible work queue for the repo-local agent-handoff standard.

## Usage Instructions

- Write each actionable item as an unchecked Markdown task: `- [ ]`.
- When an item is completed during a session, change its marker to `- [x]`.
- During agent-handoff closeout, delete completed standalone items after recording current outcomes in `docs/STATUS.md`.
- Mirror any handoff task, todo, pending item, or follow-up here so the user can track it.
- Do not start or complete TODO items unless the user explicitly asks for that work.

<!-- LLM-EDIT-BOUNDARY: DO NOT EDIT ABOVE THIS LINE -->

## User tasks

- [ ] Update GitHub repo settings.
- [ ] Does `standards/standard-bundle-authoring` need any updates to reflect recent meta-repo ADRs and
  structure changes? If so, update the standard and its examples.
- [ ] The two tooling standards `python-tooling` and `markdown-tooling` put a lot of files in the repo root.
  Is it possible to move these to a consolidated location, or is that incompatible with the requirements
  of the config file by the tooling design itself?
- [ ]

## Agent tasks

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

- [ ] Complete Agent Handoff consumer retirement from the tracked inventory.

  Migrate one repo per reviewed change. Delete the old engine only after every row validates, v5 is published,
  the final dependency search is clean, and the owner explicitly approves.

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
- [x] 2026-07-09 - Agent Handoff v1 package, dogfood adoption, and release-readiness evidence completed (`11cabc7`, `bd3cee5`).

### ⬜ Pending

Meta-repo readiness (`SPEC-MT01`), ordered — see SPEC-RD01 §19, Steps 00–07:

- [x] Step 00 - Baseline inventory (`194637e`).
- [x] Step 01 - ADR foundation accepted (`ee98d0f`).
- [x] Step 02 - Standard Bundle Authoring Standard implemented.
- [x] Step 03 - `standard.toml` manifest schema and fixtures implemented.
- [x] Step 04 - Standards graph validator implemented (`8d23a0c`).
- [x] Step 05 - Existing standards retrofitted with manifests.
- [x] 2026-07-09 - Step 06 dogfood fixtures, generated catalog, relationship catalog, and `adopt.toml` linkage implemented (this closeout).

  Adoption-mode parity, package versions, artifact provenance, and repo-local skill installs are now baseline graph/catalog facts.

- [ ] Step 07 - MCP-readiness gate passes.

Release cut (after readiness is complete):

- [ ] Promote CHANGELOG `[Unreleased]` to `## [5.0.0]`.
- [ ] Bump registry contracts, per-standard metadata, `pyproject`, and `uv.lock`.
- [ ] Run the `meta/versioning.md` release checklist.
- [ ] Lift the release freeze in `meta/versioning.md` and `docs/handoff/state.md`.
