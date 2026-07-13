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

- [ ] Define the repository policy and tooling for durable document references.

  Decide when identifiers such as `SPEC-MT01` must link to their canonical documents. Define checks for inconsistent or missing links, maintenance of `related:` frontmatter, graph generation, and safe reconciliation of detected drift.

- [ ] Define structure and formatting instructions for `docs/STATUS.md`.

  The document is meant for human consumption but is currently a long, unordered list without a big-picture summary.

## Agent tasks

Work in priority order. P0 and P2 gate the v5 release; P3 may proceed independently without widening release scope. Do not start P4 until v5.0.0 is published.

### P0 — Resolve release debt

- [ ] Preserve optimized coverage settings through the atomic Python Tooling migration.

  Coverage Tasks 1–6 and all six checker-table materialization tasks are integrated on `testing` through `26fb984`. Canonical nested predicates, fail-closed schema validation, exactly-one-checker rendering, lifecycle/migration proofs, and both complete-gate oracles pass; the root locks the bundled `pyright==1.1.411` runtime. Next, amend parallel-coverage Tasks 9 and 11 for that exact pin, guarded provider-derived dev-group pre-alignment, and frozen predecessor reconstruction; freshly audit those amended tasks before Task 9. Then complete coverage Tasks 7–8, execute Tasks 9–11, refresh the deliberately stale release evidence, and perform the atomic root migration.

### P2 — Cut and publish v5.0.0

- [ ] Prepare the v5 release commit for `main`.

  Atomically migrate this source checkout to the V2 control plane; do not stage `.standards/` earlier. Update release references and metadata, bump `pyproject.toml` and `uv.lock`, promote CHANGELOG `[Unreleased]`, and rewrite `UPGRADING.md` for v4 to v5.

- [ ] Run the complete release checklist and land the release commit on `main`.

  Follow `meta/versioning.md`, run local and hosted gates, and confirm the exact release commit exists on `main` before tagging.

- [ ] Sign and publish `v5.0.0`, advance the `v5` tag, and publish the GitHub release.

- [ ] Lift the release freeze and record deployed v5 truth.

  Update `meta/versioning.md`, `docs/handoff/state.md`, deployment/status records, and release history only after the release refs are live.

### P3 — Parallel and post-release programs

- [ ] Finish Agent Handoff consumer retirement.

  Refresh the 26-repository ledger, resolve its six remaining concrete-evidence default-branch rows through authorized workflows, verify the published v5 artifact, run the final dependency search, and obtain owner approval before deleting the deprecated engine.

- [ ] Continue MCP server enablement after Step 07.

  Before SPEC-MS01 MS-0, recheck the MCP protocol, Python SDK, licensing, and client capabilities. Keep server implementation blocked until Step 07 passes.

### P4 — Dedicated post-v5 package programs

- [ ] Create and release the provider-neutral `project-toolbox` standard.

  Develop this first as its own design, review, implementation, and release cycle. Package the four proven workflows plus one routing skill under `.agents/workflows/project-toolbox/`; retain `docs/workflows/` for local extensions.
  - [ ] Convert the installed Codex `review-orchestrator` skill into a managed `project-toolbox` workflow.

- [ ] Create and release the `agent-managed-repo` standard.

  Develop this only after `project-toolbox` closes. Use `docs/future-standards/github-repository-governance-standard.md` as the provisional input to a separate design, review, implementation, and release cycle.

- [ ] Reconcile this repository's GitHub settings with `agent-managed-repo`.

  After that package is released, apply its required-review, required-check, action-security, Dependabot, and release-policy rules here.
