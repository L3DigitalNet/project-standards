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

- [ ] Decide whether document-body references should be explicit links.

  For example, `docs/specs/2026-07-07-project-standards-mcp-server-implementation-spec.md` references `SPEC-MT01` throughout. Would links to that document provide a benefit?
  - My thought is that it could be useful for building a map/graph in the future.
  - Add a repository-wide link consistency checker.

    If links match in some places but not others, that could indicate drift and prompt a deeper investigation. Plain references such as `SPEC-MT01` are harder to verify; explicit links would also let human readers go directly to the source.
  - This could help identify and maintain links in `related:` frontmatter field by scanning for links to the document.
  - Have a scanning tool that scans the repo for links, produces a graph, and self-heals the repo by reconciling any graph inconsistencies.

Pre-release owner work is tracked in the durable v5.0.0 project tracker below.

## Agent tasks

### P1 — Dedicated post-v5 package programs

Start these only after the v5.0.0 release closes. Give each package its own design, review, implementation, and release cycle; do not combine either package with the v5 release push.

- [ ] Create and release the provider-neutral `project-toolbox` standard.

  Develop this first. Formally design, review, implement, register, and document V1 with the four proven workflows plus one routing skill. Install managed core workflows under `.agents/workflows/project-toolbox/`, keep `docs/workflows/` for local extensions, and document the later operational-suite and extension-framework waves.
  - [ ] Convert the installed Codex `review-orchestrator` skill into a managed workflow under `.agents/workflows/project-toolbox/`.

- [ ] Create and release the `agent-managed-repo` standard.

  Develop this after `project-toolbox` closes. Use `docs/future-standards/github-repository-governance-standard.md` as the provisional guide. Formally design, review, implement, register, and document the standard.

- [ ] Reconcile GitHub repository settings with `agent-managed-repo`.

  Blocked on the released `agent-managed-repo` standard. Then apply its required-review, required-check, action-security, Dependabot, and release-policy rules to this repository.

### P2 — Parallel and post-release work

- [ ] Finish Agent Handoff consumer retirement.

  Refresh the 26-repository retirement ledger against the current default branches, then resolve its six remaining concrete-evidence default-branch rows through each repository's authorized workflow. After v5, verify the published artifact, run the final dependency search, and obtain owner approval before deleting the deprecated engine.

- [ ] Continue the MCP enablement program after the readiness gate.

  Recheck MCP protocol, Python SDK, licensing, and client capabilities before SPEC-MS01 MS-0. Keep server code blocked until Step 07 passes.

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
- [x] 2026-07-12 - CP01 package migration and release-readiness follow-on integrated (`592bde8`…`e4e4761`).

### ⬜ Pending

Meta-repo readiness (`SPEC-MT01`), ordered — see SPEC-RD01 §19, Steps 00–07:

**Execution order:** clear P0 release debt, complete P1 readiness, then cut and publish under P3. Agent Handoff default-branch integrations may continue in parallel without widening the v5 package scope.

- [x] Step 00 - Baseline inventory (`194637e`).
- [x] Step 01 - ADR foundation accepted (`ee98d0f`).
- [x] Step 02 - Standard Bundle Authoring Standard implemented.
- [x] Step 03 - `standard.toml` manifest schema and fixtures implemented.
- [x] Step 04 - Standards graph validator implemented (`8d23a0c`).
- [x] Step 05 - Existing standards retrofitted with manifests.
- [x] 2026-07-09 - Step 06 dogfood fixtures, generated catalog, relationship catalog, and `adopt.toml` linkage implemented (`39b9f76`).

  Adoption-mode parity, package versions, artifact provenance, and repo-local skill installs are now baseline graph/catalog facts.

- [x] 2026-07-10 - Pre-Step-07 readiness remediation completed (`70b20ee`…`342a802`).

#### P0 — Clear release debt and finalize v5 scope

- [x] 2026-07-11 - Published the current `testing` baseline and verified hosted CI (`5d21517`).

  Hosted Standards graph and catalog run `29145160155` passed for the published baseline.

- [x] 2026-07-10 - Re-reviewed and approved Consumer Standards Control Plane `SPEC-CP01`.

  Round 3 converged at `0093a87` with no blocker or new major finding. Revision 0.4 applies the optional audit-lineage clarification and is approved for implementation planning.

- [x] 2026-07-10 - Integrated `docs/workflows/` as managed project documentation (`2a7ed25`).

  Preserved the drafts, added them to the managed frontmatter scope, and added conformant metadata with current relationships.

- [x] 2026-07-10 - Defined the project-level workflow routing and authority direction (`24d13de`).

  The future `project-toolbox` package owns managed core workflows under `.agents/workflows/project-toolbox/`; consumer-authored local workflows remain managed project documents under `docs/workflows/`. Record the general workflow-installation methodology in an ADR when the separate toolbox spec is written.

- [x] 2026-07-12 - Reconciled the v5 scope after deferring `project-toolbox` and `agent-managed-repo` (this commit).

  SPEC-BA02 rev 0.8 and the synchronized indexes set the v5 launch scope to the nine catalog 5 families. Both provisional package inputs remain tracked for dedicated post-v5 programs and neither package gates Step 07.

- [x] 2026-07-12 - Ran the first comprehensive housekeeping and repository-debt inventory (this commit).

  Required validators, package checks, Prettier, markdownlint, `pip-audit`, and `npm audit` pass. The inventory found 42 review/evidence artifacts, 15 plans, 12 future-standard drafts plus two indexes, two ignored scratch files, current-document shape warnings, and broad supplemental link-integrity debt. Follow-up tasks below preserve append-only history and require owner approval before deleting user-authored material.

- [ ] Classify and prune completed ephemeral plans and reviews.

  Inventory: 29 Codex review rounds, 13 review/evidence documents, 13 completed plans, one in-progress Agent Handoff plan, and one superseded `check` drift plan. Verify that final targets and durable session/spec records preserve every outcome. Retain the release-cut evidence and active plan; treat the superseded plan as a deletion candidate. Obtain owner approval before deleting completed review or plan artifacts and update all references and indexes in the same change.

- [ ] Finalize link and anchor integrity after artifact disposition.
  - [x] 2026-07-12 - Audited 1,924 local links across 305 source files: zero failures; 29 duplicate workflow anchors removed.
  - [ ] After artifact disposition, audit retained reviews. Exclude sessions, projections, fixtures, transcripts, and scratch files.

- [x] 2026-07-12 - Classified and indexed every provisional future-standard document (this commit).

  The index accounts for 12 drafts and two indexes. It retains governance for post-v5 `agent-managed-repo`, keeps the Usage Documentation spec set, routes two inputs to consolidation, and marks the superseded Agent Handoff and usage transcripts as owner-approved deletion candidates. Transcript paths are explicitly historical examples, not current repo references.

- [x] 2026-07-12 - Moved all retained, maintained specifications to `docs/specs/` (this commit).

  Six current specs live at the root, superseded SPEC-BA01 lives under `archive/`, and the eight-document Usage Documentation set lives under `future/`. All 15 documents are indexed and pass `spec validate` and `spec lint`. Historical designs remain separate under `docs/superpowers/specs/`; a BA02 compatibility symlink preserves the immutable catalog 5 payload link.

- [x] 2026-07-12 - Resolved current handoff shape debt without rewriting append-only history (this commit).

  `AGENTS.md` and `CLAUDE.md` are within their byte targets; the architecture map now describes catalog 5; current bug lessons meet shape limits. Historical session-row warnings remain accepted append-only history.

- [ ] Review ignored scratch content with the owner.

  `docs/scratch/scratch.md` is an interrupted-session transcript and `docs/scratch/tree_output.md` is a generated tree snapshot. Both are correctly ignored and untracked; delete them only with owner approval.

- [x] 2026-07-12 - Reconciled the stale GitHub issue and pull-request queue (remote state).

  Closed issue #3 and obsolete draft PR #4 after verifying the signed v4.1.0/v4.2.0 releases. PR #5 was already superseded on `testing`. Closed incomplete main-era action PRs #1, #2, and #6 in favor of the v5-wide replacement below. GitHub now reports no open pull requests.

- [ ] Apply the reviewed GitHub Action upgrades across the complete v5 authority surface.

  Owner approval required for the high-risk CI change. Upstream review confirms setup-node v6 and checkout v7 use Node 24; setup-node v6 can auto-enable npm caching, and setup-uv v8.3.2 is maintenance-only at SHA `11f9893b081a58869d3b5fccaea48c9e9e46f990`. Preserve registered legacy bytes. Update only live root/V2 workflows, provider output, payload digests, and current documentation; set `package-manager-cache: false` where v4 intentionally omitted caching; document the runner floor; regenerate projections and prove source/wheel parity. Markdownlint action v24 is already current.

- [x] 2026-07-12 - Resolved deferred maintenance decision debt before release (this commit).
  - [x] `spec new` already rejects symlinks in the existing parent chain and target, with bounded traversal and regression tests. No extra v5 check is needed.
  - [x] Keep the documented policy: the contract targets OpenAPI 3.2.0; templates cite the specification without a dialect pin unless a project needs one.
  - [x] Catalog 5 `reconcile --check`, central-lock convergence, transactional repair, and package drift providers supersede the v2.2 `check` plan.

#### P1 — Complete v5 architecture and readiness

- [x] 2026-07-10 - Resolved root-artifact ownership and semantic composition across standards.

  The approved design uses consumer-owned containers, typed package contributions, syntax-preserving adapters, reference-counted shared units, and no precedence. Adversarial review converged in round 2 at `b229602`; the result now feeds `SPEC-BA02` and is adopted by ADR 0023.

- [x] 2026-07-10 - Accepted the unified control-plane and catalog-channel architecture.

  ADR 0023 establishes the neutral `.standards/` control plane, explicit reconciliation, central lock, and semantic composition; ADR 0024 establishes catalog-scoped non-breaking defaults and opt-in breaking package candidates. Superseded and retained ADRs, the ADR index, and `meta/versioning.md` are reconciled.

- [x] 2026-07-10 - Superseded the Standard Bundle Authoring design contract with approved `SPEC-BA02`.

  `SPEC-BA02` defines the Full V2 authoring contract: family indexes, immutable payloads, fixed package-option namespaces, repository catalog channels, migrations, semantic contributions, trusted bounded providers, integrity, and the reduced adoption-guide role. Revs 0.4-0.5 pin the aggregate-digest contract and complete relation/legacy-state declarations; rev 0.6 records implementation evidence only. SPEC-BA01 remains superseded implementation history until V2 execution replaces its package.

- [x] 2026-07-10 - Implemented the BA02 package-contract foundation (`4e507d6` through this closeout).

  Added strict V2 family, payload, option, catalog, integrity, release, graph, schema, CLI, and installed-projection boundaries. A three-family/five-payload fixture proves channel roles and declaration shapes; offline wheel rediscovery, 100-order determinism, and the explicit 100-family/1,000-payload/10,000-unit CI scale gate pass. Runtime providers/adapters and current-package migration remain deliberately unclaimed.

- [x] Normalize every v5 specification into a clean final baseline.

  Task 18 reconciled final ADR/design decisions, stale status and DoD rows, and all implementation traceability. SPEC-MT01 OQ-005 is resolved as hand-authored, machine-checked summaries; no implementation deviation is recorded. Owner acceptance of the empty deviations logs remains a release-closeout action.

- [x] 2026-07-12 - Confirmed every catalog 5 package is ready for later MCP exposure (this commit).

  The [package review](superpowers/research/2026-07-12-catalog-5-mcp-exposure-review.md) covers all nine families. It found and fixed one pre-release gap: Python Tooling's agent summary lacked a canonical README backlink. A catalog-wide regression test, refreshed integrity metadata, 494 package-contract tests, and all package/graph/catalog/projection gates pass. The two deferred packages remain outside this gate.

- [ ] Complete the pre-release housekeeping and repository-hygiene sweep.

  Repeat the workflow checklist after P0 findings and readiness fixes land. Resolve all actionable warnings, refresh indexes and status, classify retained plans, reviews, and provisional documents, and preserve append-only history.

- [ ] Step 07 - MCP-readiness gate passes.

  Blocked on v5 scope reconciliation, P0 debt disposition, the catalog 5 MCP-exposure review, and the final housekeeping pass. Then produce the readiness report and checklist and confirm no blocking graph, package, documentation, migration, or compatibility gaps remain.

#### P3 — Cut and publish v5.0.0

- [ ] Prepare the v5 release commit for `main`.

  Atomically migrate this source checkout to the V2 control plane in the release commit; do not stage `.standards/` earlier. Bump v5 workflow and adoption refs, registry contracts, per-standard metadata, `pyproject.toml`, and `uv.lock`. Promote CHANGELOG `[Unreleased]` and rewrite `UPGRADING.md` for v4 to v5.

- [ ] Run the complete release checklist and land the release commit on `main`.

  Follow `meta/versioning.md`, run local and hosted gates, and ensure the exact release commit exists on `main` before creating tags.

- [ ] Sign and publish `v5.0.0`, advance the `v5` tag, and publish the GitHub release.

- [ ] Lift the release freeze and record deployed v5 truth.

  Update `meta/versioning.md`, `docs/handoff/state.md`, deployment/status records, and the retained v5 tracker only after the release refs are live.
