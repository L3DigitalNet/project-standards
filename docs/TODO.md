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

- [ ] Re-run coverage Task 9 and replace the retained preliminary evidence.

  Repeat the exact predecessor and two-path migration replay only after P0 inputs stabilize. Bind the new release-input hash and patch, obtain an independent release-critical review, and leave a committed clean pre-atomic checkpoint.

### Autonomous session log — 2026-07-14

- Resumed clean `testing` at synchronized `6d111ff`; preceding Task 9 and release-audit changes were committed, so I did not replay them.
- Loaded the handoff and active plan contracts; retained the current checkout because the user requested continuation on this branch.
- Re-ran the focused Frontmatter and Project Specification workflow baseline: 52 tests passed.
- Synchronized the index to CP01 rev 0.11, BA02 rev 0.12, completed Step 07, implemented BA 2.0, and the V5 config transition.
- Marked coverage Task 9 committed in the execution plan and inserted the audited release-input checkpoint that must pass before Task 10.
- Frontmatter decision: migrated roots use self-hosted mode; new consumers use the published reusable caller. No missing-`@v5` conditional is possible.
- Project Spec decision: workflows use bare validate/lint commands; passing `.standards/config.toml` conflicts with unified authority.
- Frontmatter verification: the package reconstruction, workflow runtime, and hook slice passes (50 tests).
- Project Specification verification: the reusable workflow, caller rendering, migration, and package reconstruction slice passes (33 tests).
- Project Spec fix: removed `config-path` and generated `--config`; workflow calls now defer selection to the unified CLI resolver.
- Docs: updated Frontmatter skills, V5 CLI examples, Project Spec guidance, the Python Coding banner, and changelog wording; frozen V4 bytes remain exact.
- Integrity: refreshed four payload/family/catalog chains and the Frontmatter projection; package, graph, schema, projection, Ruff, and type gates passed.
- Reconstruction: 108 affected tests and 32 fast release tests passed; retained evidence awaited the canonical slow replay.
- Preliminary replay passed in 25m27s; its ledger modifies, rather than deletes, the Frontmatter public endpoint.
- Independent review found no Critical issues and three Important issues: stale evidence, a vacuous negative test, and direct-event input misuse.
- Negative migration tests now prove a recognized frozen baseline before either signed-file mutation.
- Frontmatter's immutable endpoint is reusable-only. Project Spec direct events install `v5` and run strict lint; reusable callers retain control.
- Post-review: 110 affected and 32 fast release tests plus package, graph, schema, projection, Ruff, and type gates passed; no major findings remain.
- Handoff shape/size passed with archive warnings; validation/drift initially exposed the AGENTS/CLAUDE mismatch diagnosed below.
- Final-input decision: update durable facts before hashing, then make no non-evidence edit until evidence currency passes.
- Canonical and no-override Task 9 replays passed in 25m20s and 25m21s; the exact emitted record and all 34 release-candidate tests match.
- Created clean checkpoint `04f45d5` without pushing; Task 10 then returned two newly exposed stale-input failures to the owning task.
- Task 10 Step 1 passed. Its focused gate found four stale catalog-activation digests; the corrected fixture passes all three tests.
- Handoff diagnosis: `6d111ff` collapsed canonical managed instruction lines. Restoring provider bytes makes validation and drift checks pass.
- Focused proof: 488 tests passed; its sole mismatch showed the instruction repair changes only the migration patch and migrated lock digests.
- Evidence diagnosis: 488/489 focused tests passed; an isolated probe reproduced the changed lock, proving stale evidence rather than nondeterminism.
- Full-gate follow-up: corrected the current/legacy skill contract, signed-resource frontmatter exemption, and generated catalog; focused tests pass.

### P1 — Complete the pre-atomic gate

- [ ] Run coverage Task 10's complete verification-only gate.

  Run the integrity/catalog, focused, full repository, package, document, spec, handoff, dependency, and performance checks from the stable checkpoint. Require a clean tree and no generated diff.

### P2 — Cut and publish v5.0.0

- [ ] Create Task 11 as one atomic v5 release commit on `main`.

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
