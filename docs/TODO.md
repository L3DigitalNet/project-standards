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

### P2 — Parallel, non-release-blocking work

- [ ] Complete Agent Handoff consumer retirement from the tracked inventory.

  Finish the remaining protected default-branch integrations. After v5 ships, verify the published artifact, run the final dependency search, and obtain owner approval before deleting the old engine.

- [ ] Continue the MCP enablement program after the readiness gate.

  Recheck MCP protocol, Python SDK, licensing, and client capabilities before SPEC-MS01 MS-0. Keep server code blocked until Step 07 passes.

### P3 — Deferred maintenance

- [ ] `spec new` symlinked-parent edge cases.

  Informational, non-blocking. Revisit only if `new` adds engine-style path pre-validation beyond the current Linux target assumptions.

- [ ] OpenAPI 3.2.0 pin decision.

  Informational, non-blocking. Templates cite the unpinned OpenAPI Specification; pin only when a spec needs a specific contract dialect.

- [ ] Triage the held `check` drift implementation plan.

  Decide after v5 whether `docs/superpowers/plans/2026-06-08-check-drift.md` is still needed, should be respecified, or is superseded by newer graph, adoption, and Agent Handoff drift tooling.

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

#### P0 — Establish a verified v5 baseline

- [x] 2026-07-11 - Published the current `testing` baseline and verified hosted CI (`5d21517`).

  Hosted Standards graph and catalog run `29145160155` passed for the published baseline.

- [x] 2026-07-10 - Re-reviewed and approved Consumer Standards Control Plane `SPEC-CP01`.

  Round 3 converged at `0093a87` with no blocker or new major finding. Revision 0.4 applies the optional audit-lineage clarification and is approved for implementation planning.

- [x] 2026-07-10 - Integrated `docs/workflows/` as managed project documentation (`2a7ed25`).

  Preserved the drafts, added them to the managed frontmatter scope, and added conformant metadata with current relationships.

- [x] 2026-07-10 - Defined the project-level workflow routing and authority direction (`24d13de`).

  The future `project-toolbox` package owns managed core workflows under `.agents/workflows/project-toolbox/`; consumer-authored local workflows remain managed project documents under `docs/workflows/`. Record the general workflow-installation methodology in an ADR when the separate toolbox spec is written.

- [ ] Reconcile the stale GitHub issue and pull-request queue.

  Issue #3 is implemented by v4.1/v4.2 and PR #4 is obsolete. Close them after review. Decide whether to rebase, replace, or close action-upgrade PRs #1 and #2 for v5.

#### P1 — Finalize the v5 standard architecture

- [x] 2026-07-10 - Resolved root-artifact ownership and semantic composition across standards.

  The approved design uses consumer-owned containers, typed package contributions, syntax-preserving adapters, reference-counted shared units, and no precedence. Adversarial review converged in round 2 at `b229602`; the result now feeds `SPEC-BA02` and is adopted by ADR 0023.

- [x] 2026-07-10 - Accepted the unified control-plane and catalog-channel architecture.

  ADR 0023 establishes the neutral `.standards/` control plane, explicit reconciliation, central lock, and semantic composition; ADR 0024 establishes catalog-scoped non-breaking defaults and opt-in breaking package candidates. Superseded and retained ADRs, the ADR index, and `meta/versioning.md` are reconciled.

- [x] 2026-07-10 - Superseded the Standard Bundle Authoring design contract with approved `SPEC-BA02`.

  `SPEC-BA02` defines the Full V2 authoring contract: family indexes, immutable payloads, fixed package-option namespaces, repository catalog channels, migrations, semantic contributions, trusted bounded providers, integrity, and the reduced adoption-guide role. Revs 0.4-0.5 pin the aggregate-digest contract and complete relation/legacy-state declarations; rev 0.6 records implementation evidence only. SPEC-BA01 remains superseded implementation history until V2 execution replaces its package.

- [x] 2026-07-10 - Implemented the BA02 package-contract foundation (`4e507d6` through this closeout).

  Added strict V2 family, payload, option, catalog, integrity, release, graph, schema, CLI, and installed-projection boundaries. A three-family/five-payload fixture proves channel roles and declaration shapes; offline wheel rediscovery, 100-order determinism, and the explicit 100-family/1,000-payload/10,000-unit CI scale gate pass. Runtime providers/adapters and current-package migration remain deliberately unclaimed.

- [ ] Complete the Consumer Standards Control Plane (`SPEC-CP01`) follow-on for v5.

  The approved 18-task mechanism-level core is complete through `e069c34`: neutral initialization, unified config and lock state, catalog-scoped resolution, bounded providers, semantic composition, lifecycle planning, transactional apply/recovery, and public reconciliation commands. Reconstruct and convert the current packages, implement legacy migration and same-major catalog refresh, prove compatibility for every current standard, then complete activation and release.

  The 18-task follow-on plan at `docs/superpowers/plans/2026-07-11-consumer-standards-control-plane-package-migration-release.md` passed the scratch-path convergence audit and is owner-approved. Execution is underway on `feature/v5-package-migration`; Tasks 1-8 provide typed reports, deterministic migration/apply, catalog refresh and recovery, Authoring 2.0 self-hosting, reference-only Python Coding 0.5, Markdown Frontmatter 1.2, and ADR 1.1 reconstruction. Task 9 reconstructs CLI Documentation 1.1 next; root family activation remains deferred to Task 14.

- [ ] Create and release the provider-neutral `project-toolbox` standard for v5.

  Specify this only after `SPEC-CP01` is approved. V1 packages the four proven workflows plus one routing skill, installs managed core workflows under `.agents/workflows/project-toolbox/`, keeps `docs/workflows/` for local extensions, and documents the later operational-suite and extension-framework waves.

  - [ ] Convert the installed Codex `review-orchestrator` skill into a managed workflow under `.agents/workflows/project-toolbox/`.

- [ ] Create and release the `agent-managed-repo` standard for v5.0.0.

  Use `docs/future-standards/github-repository-governance-standard.md` as the provisional guide. Formally design, review, implement, register, and document the standard before release.

- [ ] Reconcile GitHub repository settings with `agent-managed-repo`.

  Keep policy changes paused until the standard is approved. Then apply its required-review, required-check, action-security, Dependabot, and release-policy rules to this repository.

#### P2 — Close v5 documentation and readiness

- [ ] Normalize every v5 specification into a clean final baseline.

  Reconcile final ADR and design decisions, stale status rows, unchecked implemented DoD items, and open questions. Resolve or explicitly defer SPEC-MT01 OQ-005. Release no spec with unexplained deviations.

- [ ] Confirm every v5 standard is ready for later MCP exposure.

  Resolve compatibility gaps before release so MCP implementation does not immediately require corrective per-standard releases.

- [ ] Complete the pre-release housekeeping and repository-hygiene sweep.

  Run the workflow checklist; classify retained plans, reviews, and provisional future-standard documents; refresh indexes and status; address current-document shape warnings; preserve append-only history.

- [ ] Step 07 - MCP-readiness gate passes.

  Produce the readiness report and checklist. Confirm no blocking graph, package, documentation, migration, or standard-compatibility gaps remain.

#### P3 — Cut and publish v5.0.0

- [ ] Prepare the v5 release commit for `main`.

  Bump v5 workflow and adoption refs, registry contracts, per-standard metadata, `pyproject.toml`, and `uv.lock`. Promote CHANGELOG `[Unreleased]` and rewrite `UPGRADING.md` for v4 to v5.

- [ ] Run the complete release checklist and land the release commit on `main`.

  Follow `meta/versioning.md`, run local and hosted gates, and ensure the exact release commit exists on `main` before creating tags.

- [ ] Sign and publish `v5.0.0`, advance the `v5` tag, and publish the GitHub release.

- [ ] Lift the release freeze and record deployed v5 truth.

  Update `meta/versioning.md`, `docs/handoff/state.md`, deployment/status records, and the retained v5 tracker only after the release refs are live.
