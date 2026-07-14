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

Work from P0 through P2 for the shortest safe path to v5.0.0. P3 and P4 are explicitly post-release and must not delay that path.

### P0 — Correct audited release inputs

- [x] Synchronize the v5 execution plan and current-state indexes.

  Mark coverage Task 9 committed at `7d4d5fa`; add the audited prerequisites before Task 10; correct stale CP01/BA02 revisions, Step 07 status, Standard Bundle Authoring 2.0 status, and V5 configuration guidance in maintained indexes.

- [x] Repair the Markdown Frontmatter release-workflow bootstrap.

  The V2-composed job cannot call this repository at `@v5` before that tag exists. Make the first `main` release run bootstrap-safe, retain a canonical public `workflow_call` endpoint for consumers, and test both pre-tag and published-ref paths.

- [x] Repair the Project Specification generated workflow under unified authority.

  Stop the current V2 caller from passing `.standards/config.toml` as an explicit legacy override. Reconcile the resource, provider, adoption guide, root workflow, CLI semantics, and tests with an end-to-end generated-command check.

- [x] Correct stale shipped package and release guidance.

  Update the Frontmatter skill and wheel twin, active CLI Documentation example, Project Specification tooling notes, Python Coding 0.5 banner, current family docs, and ADR package-versus-contract changelog wording. Preserve frozen legacy resources and historical migration records.

- [x] Regenerate all integrity outputs affected by the release-input fixes.

  Refresh payload, family, and catalog digests; schemas; installed projections; bundled resources; and source/wheel regression expectations. Prove package validation, graph validation, and fixed-point projection remain clean.

- [x] Re-run coverage Task 9 and replace the retained preliminary evidence.

  Repeat the exact predecessor and two-path migration replay only after P0 inputs stabilize. Bind the new release-input hash and patch, obtain an independent release-critical review, and leave a committed clean pre-atomic checkpoint.

### P1 — Complete the pre-atomic gate

- [x] Run coverage Task 10's complete verification-only gate.

  Run the integrity/catalog, focused, full repository, package, document, spec, handoff, dependency, and performance checks from the stable checkpoint. Require a clean tree and no generated diff.

### P2 — Cut and publish v5.0.0

- [ ] Resolve editable-source V2 distribution loading and rerun the Task 11 gates.

  The migrated root discovers `.standards/`, but `InstalledDistribution.current()` rejects the canonical symlink-only source projection before direct CLI behavior runs.

  Design and approve a source-checkout adapter that keeps installed-wheel checks fail closed. Add regression coverage, update release-only expectations, rerun both gates, and refresh evidence. Current checkpoint: 491 focused tests pass; the ordinary phase has 89 failures.

- [ ] Complete Task 11 and prepare the v5 release candidate for promotion to `main`.

  Start from the verified predecessor. Migrate the source root to V2, create `.standards/`, remove `.project-standards.yml`, transition root workflows and commands, bump project and lock versions, promote the changelog, and finish the active v4-to-v5 reference sweep. Do not stage `.standards/` earlier.

- [ ] Bind final release evidence and verify the atomic parent-to-release diff.

  Run the migrated-root gate, repeat the Task 9 proof against the actual release tree, derive the complete-release record, rerun all local release gates, and prove the single commit contains exactly the intended transition.

- [ ] Land the exact release commit on remote `main` and pass hosted gates.

  Confirm local and remote SHA equality before tagging. Require every protected `main` workflow to pass, including the repaired standards workflow, and confirm the two default-branch Dependabot alerts close against the already-updated lock.

- [ ] Sign and publish `v5.0.0`, advance the `v5` tag, and publish the GitHub release.

  GPG-sign both refs at the exact release commit, verify their remote dereferenced SHAs, publish from the promoted release notes, and probe the published wheel and GitHub release.

- [ ] Close the v5 release and record deployed truth.

  Lift the freeze and update `meta/versioning.md`, deployment, status, task, handoff, and release-history records only after the refs and artifact are live. Reconcile `testing` with the released `main` tip.

### P3 — Post-release cleanup and deferred standards

- [ ] Finish Agent Handoff consumer retirement.

  Refresh the 26-repository ledger, resolve its six remaining concrete-evidence default-branch rows through authorized workflows, verify the published v5 artifact, run the final dependency search, and obtain owner approval before deleting the deprecated engine.

- [ ] Resolve the owner-reviewed future-artifact dispositions.

  Delete the two approved superseded transcripts, consolidate the retained Project Specification guidance into its durable owner, then update `docs/future-standards/README.md`, inbound links, and the local-link audit.

- [ ] Decide and complete the Python Coding package's post-v5 status path.

  Keep 0.5 reference-only until its draft requirements, adoption posture, and release criteria are explicitly accepted or the package is deliberately retained as reference material.

- [ ] Review the Usage Documentation Site specification set.

  Treat the moved eight-document set as a separate post-v5 program: reconcile requirements and decisions, obtain formal specification approval, then design and plan implementation.

- [ ] Continue MCP server enablement after v5.

  Step 07 is complete. Before SPEC-MS01 MS-0, recheck the MCP protocol, Python SDK, licensing, and client capabilities; resolve remaining owner decisions before server implementation.

### P4 — Dedicated post-v5 package programs

- [ ] Create and release the provider-neutral `project-toolbox` standard.

  Develop this first as its own design, review, implementation, and release cycle. Package the four proven workflows plus one routing skill under `.agents/workflows/project-toolbox/`; retain `docs/workflows/` for local extensions.
  - [ ] Convert the installed Codex `review-orchestrator` skill into a managed `project-toolbox` workflow.

- [ ] Add template-repository autopopulation after `project-toolbox` is released.

  Design the bootstrap and update flow against the released provider-neutral workflow package rather than embedding a second unmanaged copy.

- [ ] Create and release the `agent-managed-repo` standard.

  Develop this only after `project-toolbox` closes. Use `docs/future-standards/github-repository-governance-standard.md` as the provisional input to a separate design, review, implementation, and release cycle.

- [ ] Reconcile this repository's GitHub settings with `agent-managed-repo`.

  After that package is released, apply its required-review, required-check, action-security, Dependabot, and release-policy rules here.
