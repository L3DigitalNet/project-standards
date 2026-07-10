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

Pre-release owner work is tracked in the durable v5.0.0 project tracker below.

## Agent tasks

- [ ] `spec new` symlinked-parent edge cases.

  Informational, non-blocking. Revisit only if `new` adds engine-style path pre-validation beyond the current Linux target assumptions.

- [ ] OpenAPI 3.2.0 pin decision.

  Informational, non-blocking. Templates cite the unpinned OpenAPI Specification; pin only when a spec needs a specific contract dialect.

- [ ] MCP enablement program.

  Specs are ingested. Do not start MCP server code until the SPEC-MT01 readiness gate passes. Recheck MCP spec and SDK versions before SPEC-MS01 MS-0.

  SPEC-MT01 ADRs 0001-0013 are authored and accepted. SPEC-MS01 server ADRs remain deferred to the server phase.

  Future ADR themes: MCP boundary, resources-before-tools, SDK adapter, remote transport deferral, manifest resources, and plan-first controlled writes.

- [ ] Complete Agent Handoff consumer retirement from the tracked inventory.

  Migrate one repo per reviewed change. Delete the old engine only after every row validates, v5 is published, the final dependency search is clean, and the owner explicitly approves.

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
- [x] 2026-07-10 - FR-013 agent-summary coverage and traceability completed (`529ec72`…`27bed75`).

### ⬜ Pending

Meta-repo readiness (`SPEC-MT01`), ordered — see SPEC-RD01 §19, Steps 00–07:

- [x] Step 00 - Baseline inventory (`194637e`).
- [x] Step 01 - ADR foundation accepted (`ee98d0f`).
- [x] Step 02 - Standard Bundle Authoring Standard implemented.
- [x] Step 03 - `standard.toml` manifest schema and fixtures implemented.
- [x] Step 04 - Standards graph validator implemented (`8d23a0c`).
- [x] Step 05 - Existing standards retrofitted with manifests.
- [x] 2026-07-09 - Step 06 dogfood fixtures, generated catalog, relationship catalog, and `adopt.toml` linkage implemented (`39b9f76`).

  Adoption-mode parity, package versions, artifact provenance, and repo-local skill installs are now baseline graph/catalog facts.

- [x] 2026-07-10 - Pre-Step-07 readiness remediation completed (`70b20ee`…`342a802`).

V5 standard and repository prerequisites — complete before the Step 07 readiness gate:

- [ ] Create and release the `agent-managed-repo` standard for v5.0.0.

  Use `docs/future-standards/github-repository-governance-standard.md` as the provisional guide. Formally design, review, implement, register, and document the standard before release.

- [ ] Reconcile the Standard Bundle Authoring Standard with the final v5 architecture.

  Audit recent meta-repo ADRs and structural changes, then update the standard, manifest guidance, templates, and examples where required.

- [ ] Resolve root-artifact placement for both tooling standards.

  Determine whether Python Tooling and Markdown Tooling artifacts can share a consolidated location without breaking tool discovery or consumer contracts. Implement the approved design before release.

- [ ] Normalize every v5 specification into a clean final baseline.

  Reconcile final ADR and design decisions, including MCP changes. Remove amendment-style narration and release no spec with unresolved deviations.

- [ ] Confirm every v5 standard is ready for later MCP exposure.

  Resolve compatibility gaps before release so MCP implementation does not immediately require corrective per-standard releases.

- [ ] Complete the pre-release housekeeping and repository-hygiene sweep.

- [ ] Bring `docs/workflows/` into managed-document scope.

  Add conformant frontmatter, current links and references, and project-level agent guidance that routes relevant work through these workflow documents.

- [ ] Decide whether repository workflows require an ADR.

  If an ADR materially improves workflow authority and consistency, create and accept it before completing the workflow documentation task.

- [ ] Reconcile GitHub repository settings with `agent-managed-repo`.

  Keep repository-policy changes paused. After the standard is approved, define required-review and required-check behavior there, then apply the resulting v5 policy to this repository.

- [ ] Step 07 - MCP-readiness gate passes.

Release cut (after readiness is complete):

- [ ] Promote CHANGELOG `[Unreleased]` to `## [5.0.0]`.
- [ ] Bump registry contracts, per-standard metadata, `pyproject`, and `uv.lock`.
- [ ] Run the `meta/versioning.md` release checklist.
- [ ] Lift the release freeze in `meta/versioning.md` and `docs/handoff/state.md`.
