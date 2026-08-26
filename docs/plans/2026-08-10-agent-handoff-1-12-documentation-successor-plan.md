---
plan_format: 3
title: 'Agent Handoff 1.12 Documentation Successor Implementation Plan'
slug: 'agent-handoff-1-12-documentation-successor'
status: active
revision: 1
revises_revision: 0
revision_reason: 'initial plan from issues 140 and 165 and their 2026-08-10 triage boundary'
pause_reason: ''
source: 'issues L3DigitalNet/project-standards#140 and #165; verified 2026-08-10 triage and package evidence'
spec_ref: ''
created: 2026-08-10
updated: 2026-08-10
owners:
  - 'Project Standards maintainers'
  - 'Coding agents under human review'
---

# Agent Handoff 1.12 Documentation Successor Implementation Plan

> **Definition, not state.** Plan authoring generated no `.project-pipeline` state. During execution, the orchestrator alone generates and mutates ephemeral state under `.project-pipeline/2026-08-10-agent-handoff-1-12-documentation-successor/execution/`.

## 1. Objective

Cut one complete, unadvertised `agent-handoff@1.12` documentation successor that tells a clean V5-native consumer that reconciliation retires the superseded managed Python launcher, removes the false manual `git rm` instruction, and names the compiled launcher as the current confirmation target in the legacy-migration runbook. Preserve all Agent Handoff 1.11 bytes and modes, preserve intentionally legacy integration references, leave the `created_container=False` retirement residual for a separate owner decision, and stop at a locally verified candidate without activating or publishing it.

## 2. Authority and Source Map

<!-- release-consistency: historical standard-bundle-authoring -->

| Source | Source Role | Authority / Use | Version / Date | Affected Plan Surface |
| --- | --- | --- | --- | --- |
| `request` | normative | Binding paired scope, unadvertised 1.12 boundary, explicit exclusions, #156 entry gate, predecessor preservation, verification, and no-implementation handoff. | 2026-08-10 | §§1–13; T1 |
| `issue:L3DigitalNet/project-standards#140` | normative | Correct the 1.11 adoption guide for clean V5-native whole-file retirement; keep the `created_container=False` residual separate. Verified against the 2026-08-10 triage comment. | verified 2026-08-10 | §§1, 3–7, 9–12; T1 |
| `issue:L3DigitalNet/project-standards#165` | normative | Correct exactly the current-launcher confirmation target; preserve intentionally legacy references; batch the correction in 1.12. Verified against the 2026-08-10 triage comment. | verified 2026-08-10 | §§1, 3–7, 9–12; T1 |
| `repo:docs/plans/2026-08-10-schema-payload-reference-validation-plan.md#t2-document-the-successor-cut-guard-and-verify-the-repository` | decision | #156 T2/PV-T2-001 must be terminal and green before any successor payload write. | revision 1, 2026-08-10 | §§3, 8–10; T1 |
| `repo:standards/agent-handoff/versions/1.11/adopt.md#upgrade-from-19-or-earlier` | current-state evidence | Carries the false no-retirement claim and manual `git rm` step. | Agent Handoff 1.11 | §§4–7; T1 |
| `repo:standards/agent-handoff/versions/1.11/resources/legacy-migration.md#4-retire-obsolete-repo-local-artifacts` | current-state evidence | Step 2 names the retired Python launcher as the current confirmation target; the rest of the 97-line audit is correct. | Agent Handoff 1.11 | §§4–7; T1 |
| `repo:standards/agent-handoff/versions/1.11/payload.toml` | current-state evidence | Declares the compiled launcher target, legacy-reference roles, 43-file payload inventory, migrations, providers, outputs, and digests. | aggregate `sha256:570cc7cf345fc953d535e1fab8f7ad52bcea5d81eaf3d5a3641d1b40580c9ea2` | §§3–7, 9–12; T1 |
| `repo:src/project_standards/control_plane/planner.py::_classify_removed` | current-state evidence | Clean managed whole files created by the platform retire; modified bytes block with `CP-MODIFIED-MANAGED`; whole files with `created_container=False` preserve. | `23c0036f` | §§3–7; T1 |
| `repo:src/project_standards/control_plane/migration.py::_adopted_legacy_units` | current-state evidence | ADOPT-disposition whole-file migration records use `created_container=False`, defining the deferred residual boundary. | `23c0036f` | §§3–5, 11; T1 |
| `repo:tests/package_contract/test_agent_handoff_1_11.py` | current-state evidence | Established predecessor-byte/mode, payload identity, projection, launcher, and deferred-advertisement contract pattern. | `23c0036f` | §§5–7, 9, 12; T1 |
| `repo:standards/standard-bundle-authoring/versions/2.6/README.md#author-workflow` | normative | V2 successor, digest, projection, catalog, and immutability contract. | 2.6 | §§3, 7, 9, 12; T1 |
| `repo:docs/handoff/conventions.md#18-match-verification-to-the-changed-surface` | normative | Proportional verification contract and exact payload/package gate selection. | 2026-08-10 | §§3, 7, 9, 12; T1 |

Conflict precedence: the direct request and the 2026-08-10 issue triage override #140's obsolete title, reproduction, and engine-oriented acceptance criteria. Existing engine behavior establishes the wording boundary only; this plan neither changes nor ratifies the unresolved `created_container=False` semantics.

## 3. Scope, Boundaries, and Constraints

### 3.1 In Scope

- A complete `standards/agent-handoff/versions/1.12/` payload copied from 1.11, with exactly the six permitted payload-path changes: `README.md`, `adopt.md`, `payload.toml`, `resources/legacy-migration.md`, `schemas/provider-input.schema.json`, and `schemas/migration-report.schema.json`.
- Adoption guidance limited to clean V5-native managed whole-file retirement: reconciliation removes the unchanged superseded `.agents/hooks/agent-handoff/session_start.py`, and consumer-modified bytes fail closed with `CP-MODIFIED-MANAGED` rather than being deleted.
- One correction in legacy-migration §4 step 2: the current confirmation target becomes `.agents/hooks/agent-handoff/session-start`.
- The 1.12 family-index row and aggregate digest, 43-link relative source projection, generated `standards/catalog.md` facts with role `unadvertised`, executable-path mode inventory, focused package contract, and an Unreleased changelog entry for #140/#165.
- Focused documentation assertions and mutation-based negative controls proving that the two reported defects and plausible over-corrections are rejected.

### 3.2 Out of Scope and Deferred

- No control-plane, planner, executor, migration, schema-model, or artifact-policy behavior change; no new retirement declaration or provider behavior.
- No decision or prescriptive workaround for whole-file retirement where the applied lock has `created_container=False`, including adopted pre-existing containers and residual V4-migration cases. A separately governed decision may change that behavior later.
- No Agent Handoff provider migration, command-provider work, Go rebuild, launcher rebuild, or any part of issue #142.
- No edit to any 1.11 or older payload byte or mode. The 1.12 legacy Claude/Codex integration resources remain byte-identical to 1.11 even though they intentionally name the retired per-harness Python launcher.
- No `catalogs/5.toml` entry, Catalog 5/default selection change, family-root authority repoint, `.standards` selection/reconcile, release version bump, tag, asset, push, issue mutation, or publication.
- No execution-state generation during authoring. During implementation, workers never edit `.project-pipeline` files directly.

### 3.3 Ownership and Preserved Behavior

| Boundary | Owner / Responsibility |
| --- | --- |
| T1 owns | The complete 1.12 candidate, its focused contract and mode allowlist, family digest/index, projection, generated unadvertised catalog facts, and changelog entry. |
| Depends on | #156 T2/PV-T2-001 terminal checkpoint and clean graph/corpus guard before the first payload write. |
| Does not own | Retirement engine semantics, migrated/adopted residual behavior, #142, activation, release/publication, family-root current-authority pages, or GitHub lifecycle state. |
| Must preserve | All 43 Agent Handoff 1.11 files and modes; only six corresponding 1.12 files may differ. Options, artifacts, contributions, providers, templates, launcher bytes/mode, rendered registrations, and legacy-reference roles remain unchanged. |

### 3.4 Constraints and Authorization

- **EG-001 — schema-reference gate:** before creating `versions/1.12/` or writing any successor payload byte, validate the #156 master and verify a unique terminal commit carrying `Plan-Id: 2026-08-10/schema-payload-reference-validation`, `Plan-Task: T2`, `Plan-Status: done`, and `Plan-Proofs: PV-T2-001`. Rerun that proof's graph/corpus acceptance. Absence, mismatch, or failure blocks T1.
- If the #156 plan is revised, pause before payload writes and consume the replacement checkpoint only through an approved revision of this plan; do not infer equivalence from T1 or from the current graph implementation.
- Run `uv run python scripts/family_preflight.py agent-handoff` before authoring. Its current result reports all nine applicable declaration sites as declared, but it predicts gates and replaces none.
- The successor retains exactly 43 payload files. The six-path delta allowlist is exhaustive, not permission to change all six arbitrarily: mechanical identity/digest edits occur only where 1.12 requires them, #140 owns the adoption section, and #165 owns one runbook line.
- `standards/catalog.md` is generator-owned. `catalogs/5.toml`, the three mutable family-root documents, `.standards/config.toml`, and `.standards/lock.toml` must remain unchanged so 1.11 stays the selected/default authority.
- Run `scripts/bootstrap-worktree.sh` in a fresh execution worktree and again after payload/projection changes. Package and Markdown checks are short and run directly. The Git/index/history-dependent `scripts/verify.sh --full` gate runs directly in the local checkout; do not send it through rexec, whose worker receives no `.git`.

## 4. Current State and Target State

### 4.1 Current State

Agent Handoff 1.11 is Catalog 5's default and the mutable family pages point to it. Its complete payload has 43 regular files, 28 declared resources, 8 providers, and 18 consumer outputs; its projection contains one relative symlink per payload file. The 1.11 adoption guide still says the payload has no retirement policy and directs a manual `git rm`, although `_classify_removed` removes an unchanged managed whole file when the platform created its container and refuses modified bytes.

The same guide's universal wording would also conceal a real residual: `_classify_removed` preserves a whole file when the prior lock says `created_container=False`, and migrated/adopted whole files can carry that value. No owner decision in #140 resolves that case.

Legacy-migration §4 step 2 is the only wrong current-artifact reference in its 97 lines. The adjacent `resources/integration/claude-session-start.json` and `codex-session-start.toml` also name `session_start.py`, but `payload.toml` declares them as `legacy-reference` resources. They describe pre-1.10 source registrations and are intentionally not the live registrations rendered by the provider.

At base `23c0036f`, #156 T1 and its narrow helper-preservation correction are committed, but the active #156 plan's T2 documentation/verification checkpoint is not yet in history. T1 is therefore blocked at EG-001 even though the graph guard implementation is present.

### 4.2 Target State

Agent Handoff 1.12 is a complete, exact-selectable but unadvertised documentation candidate. Its adoption guide describes the clean V5-native retirement result and its modified-byte refusal without manual deletion or a universal claim about migrated/adopted locks. Its legacy-migration runbook confirms the selected harnesses reference the compiled current launcher before legacy copies are removed, while its intentional legacy-reference fixtures stay unchanged.

The family index and source projection include 1.12 at a validated aggregate digest; generated catalog documentation labels it `unadvertised`. Catalog 5, producer self-host selection, lock state, family-root current authority, engine behavior, and every 1.11 byte remain unchanged.

### 4.3 Delta Summary

| Area | Current | Target | Must Preserve |
| --- | --- | --- | --- |
| V5-native retirement guidance | Claims no retirement policy and instructs manual `git rm`. | Says reconcile removes the unchanged platform-created managed whole file and blocks modified bytes. | No claim or workaround for `created_container=False`. |
| Legacy migration confirmation | Names retired `.agents/hooks/agent-handoff/session_start.py` as the current target. | Names `.agents/hooks/agent-handoff/session-start`. | Correct legacy-copy and legacy-reference mentions of `session_start.py`. |
| Payload identity | 1.11 is indexed, projected, and default. | 1.12 is indexed, projected, and rendered as unadvertised. | 1.11 bytes/modes/digest and all selected/default/root navigation state. |
| Runtime behavior | Existing provider, launcher, option, output, and engine behavior. | No runtime change. | Exact 1.11 bytes for all non-documentation/mechanical-identity payload paths. |

## 5. Change Surface and Architecture

### 5.1 Components and Ownership

| Component / Surface | Current Responsibility | Planned Responsibility | Paths / Contracts | Owning Task |
| --- | --- | --- | --- | --- |
| Adoption guidance | 1.11 documents the wrong retirement result. | 1.12 documents only the verified clean V5-native path and modified-byte refusal. | `agent-handoff-1.12-retirement-guidance-v1` | T1 |
| Legacy-migration guidance | One confirmation target names the retired launcher. | One line names the compiled launcher; legacy evidence stays historical. | `agent-handoff-1.12-legacy-target-v1` | T1 |
| Immutable package candidate | 1.11 is complete and advertised. | 1.12 is a complete unadvertised successor with a six-path payload delta. | V2 family/payload/digest/projection contracts | T1 |
| Package proof | 1.11 contract pins its earlier successor boundary. | A new focused contract pins 1.12 docs, identity, immutability, mode, projection, and non-activation. | `tests/package_contract/test_agent_handoff_1_12.py` | T1 |

### 5.2 Change-Surface Matrix

| Surface | Applies? | Invariant / Required Change | Proof | Task |
| --- | --- | --- | --- | --- |
| Behavior | no | Runtime and reconcile behavior remain unchanged; documentation is corrected to current behavior. | PV-T1-001 | T1 |
| Architecture / dependency direction | no | Package/provider/control-plane ownership is unchanged. | PV-T1-001 | T1 |
| Public / cross-task interface | yes | Versioned adoption and migration guidance changes; package schemas change only their required 1.12 identity constants. | PV-T1-001 | T1 |
| Data / state | no | No consumer or repository state transition executes. | PV-T1-001 | T1 |
| Configuration | no | Option schema, defaults, provider requests, artifacts, contributions, and rendered registrations stay exact. | PV-T1-001 | T1 |
| Security / trust | no | No executable, trust, credential, subprocess, or permission boundary changes. | PV-T1-001 | T1 |
| Compatibility / migration | yes | 1.11 is immutable; 1.12 changes guidance only and adds no migration edge from 1.11. | PV-T1-001 | T1 |
| Operations / deployment | yes | Stop at an unadvertised local checkpoint; activation/publication remain external. | PV-T1-001 | T1 |
| Documentation | yes | Correct #140 and exactly one #165 confirmation target while retaining historical references. | PV-T1-001 | T1 |
| Durable evidence | no | Committed package contract and checkpoint reproduce all acceptance. | PV-T1-001 | T1 |

### 5.3 Binding Decisions

| ID | Decision | Rationale | Source | Affected Task(s) |
| --- | --- | --- | --- | --- |
| D-001 | Describe retirement only for an unchanged, V5-native, platform-created managed whole file; name `CP-MODIFIED-MANAGED` for modified bytes. | This is the verified engine behavior and resolves the false guide without deciding the residual. | request; #140 triage; `_classify_removed` | T1 |
| D-002 | Do not prescribe deletion, preservation, migration, or lock rewriting for `created_container=False`. | Migrated/adopted whole-file semantics need a separate owner decision. | request; #140 triage; migration evidence | T1 |
| D-003 | Change only §4 step 2's confirmation target; keep adjacent legacy integration fixtures unchanged and declared `legacy-reference`. | The full-file audit found one wrong current target and confirmed the neighboring references are historical evidence. | #165 triage; 1.11 manifest | T1 |
| D-004 | Cut 1.12 as a complete unadvertised successor and defer Catalog 5/root-family activation. | Package completion and release activation are separate authority boundaries. | request; V2 authoring contract; 1.11 cut precedent | T1 |
| D-005 | Require #156 T2/PV-T2-001 before the first successor payload write. | The family-agnostic graph guard must protect this cut on arrival rather than be applied retroactively. | request; active #156 plan | T1 |

## 6. Requirements and Acceptance

| ID | Requirement | Source | Priority | Owner Task | Task(s) | Proof(s) |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-001 | No 1.12 payload write shall occur until EG-001 validates #156 T2/PV-T2-001 and its graph/corpus acceptance. | `request`; #156 plan | Must | T1 | T1 | PV-T1-001 |
| REQ-002 | The 1.12 adoption guide shall state that clean V5-native reconciliation removes the unchanged superseded managed Python launcher and that modified bytes produce `CP-MODIFIED-MANAGED`. | #140 triage; engine evidence | Must | T1 | T1 | PV-T1-001 |
| REQ-003 | The 1.12 adoption guide shall remove the manual `git rm` step and shall neither claim nor prescribe behavior for the `created_container=False` migrated/adopted residual. | `request`; #140 triage | Must | T1 | T1 | PV-T1-001 |
| REQ-004 | Legacy-migration §4 step 2 shall name `.agents/hooks/agent-handoff/session-start` as the current confirmation target, with no other runbook correction. | #165 body and triage | Must | T1 | T1 | PV-T1-001 |
| REQ-005 | The 1.12 legacy Claude/Codex integration resources and every other intentionally historical reference shall remain byte-identical to 1.11 and retain `legacy-reference` roles. | #165 triage | Must | T1 | T1 | PV-T1-001 |
| REQ-006 | 1.12 shall contain the same 43 paths and modes as 1.11; only the six declared payload paths may differ, and options, artifacts, contributions, providers, templates, and launcher bytes/mode shall be exact. | `request`; 1.11 contract; V2 authoring | Must | T1 | T1 | PV-T1-001 |
| REQ-007 | 1.12 identity, migration endpoints, schema constants, declared file digests, family aggregate, relative projection, executable-mode inventory, and generated catalog facts shall agree. | V2 authoring; #156 | Must | T1 | T1 | PV-T1-001 |
| REQ-008 | `catalogs/5.toml`, family-root authority pages, producer configuration/lock, release version, and GitHub state shall remain unchanged; generated catalog documentation shall label 1.12 `unadvertised` while 1.11 remains default. | `request`; V2 catalog boundary | Must | T1 | T1 | PV-T1-001 |
| REQ-009 | The Unreleased changelog shall record the paired documentation successor and its no-runtime-change/unadvertised boundary without repeating the false manual guidance. | repository release-documentation precedent | Should | T1 | T1 | PV-T1-001 |
| REQ-010 | Focused package/documentation checks, all five package validators, scoped and Git-tracked Markdown gates, diff checks, and the final local full gate shall pass after the last content change. | `request`; repository convention 18 | Must | T1 | T1 | PV-T1-001 |

## 7. Verification and Evidence Strategy

- **Entry oracle:** #156's active master and terminal T2 checkpoint trailers, followed by its PV-T2-001 graph/corpus proof. A present T1 implementation is insufficient.
- **Package oracle:** the immutable 1.11 tree and aggregate digest, the V2 family/payload validators, manifest-derived graph validation, projection checker, generated catalog renderer, and Git mode policy.
- **Documentation oracle:** #140/#165 latest triage, `_classify_removed`, the 1.11 payload's current launcher target and legacy roles, and exact text/count assertions in the focused 1.12 contract.
- **Negative controls:** temporarily restore the false manual `git rm` block, replace the corrected confirmation target with `session_start.py`, alter an unchanged legacy integration resource, and add an advertising row for 1.12; each mutation must fail the focused contract for its intended reason before restoration. Graph validation must also reject a stale 1.11 self-version constant in a 1.12 schema.
- **Test layers:** documentation/static inspection, byte-and-mode predecessor comparison, payload integrity/family graph, schema-reference validation, projection/catalog generation, repository mode policy, Markdown format/lint, and final repository qualification.
- **External environments:** none. GitHub reads informed the plan; implementation performs no GitHub mutation or live consumer operation.
- **Evidence:** command output is ephemeral. The committed focused contract and identity-bearing T1 checkpoint are sufficient durable proof.
- **Late failure:** block T1, append a correction task with permanent ID and `corrects:`/`discovered_from:` if intent is unchanged, and rerun PV-T1-001. Return an unresolved engine/residual decision to #140's owner rather than widening this plan.

## 8. Execution Summary

| Task | Title | Disposition | Work Type | Phase | Depends On | Requirement(s) | Primary Proof | Parallel / Conflict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T1 | Cut and verify Agent Handoff 1.12 documentation successor | active | documentation | P1 | None | REQ-001–REQ-010 | PV-T1-001 | no / owns all successor and generated aggregate paths |

## 9. Implementation Tasks

### Phase P1: Documentation Successor Candidate

#### T1: Cut and verify Agent Handoff 1.12 documentation successor

- **disposition:** active
- **outcome:** One complete Agent Handoff 1.12 candidate corrects #140 and #165 within the six-path payload delta, preserves 1.11 and historical evidence, remains unadvertised, and reaches a green local checkpoint.
- **work_type:** documentation
- **checkpoint:** one green commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** []
- **dependency_reason:** none
- **requirements:** [REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-008, REQ-009, REQ-010]
- **proof:** [PV-T1-001]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#140, issue:L3DigitalNet/project-standards#165, repo:docs/plans/2026-08-10-schema-payload-reference-validation-plan.md#t2-document-the-successor-cut-guard-and-verify-the-repository, repo:standards/agent-handoff/versions/1.11/adopt.md#upgrade-from-19-or-earlier, repo:standards/agent-handoff/versions/1.11/resources/legacy-migration.md#4-retire-obsolete-repo-local-artifacts, repo:standards/agent-handoff/versions/1.11/payload.toml, repo:src/project_standards/control_plane/planner.py::_classify_removed]
- **consumes:** [validated #156 T2/PV-T2-001 checkpoint, immutable Agent Handoff 1.11 payload, V2 package/digest/projection/catalog contracts]
- **produces:** [agent-handoff-1.12-retirement-guidance-v1, agent-handoff-1.12-legacy-target-v1, complete unadvertised Agent Handoff 1.12 candidate, validated T1 checkpoint]
- **preserves:** [all 1.11 bytes/modes/digest, `created_container=False` decision boundary, legacy-reference fixtures/roles, runtime/provider/option/output behavior, Catalog 5 and family-root selection]
- **invariants:** [six-path payload delta is exhaustive; one current-target runbook line changes; all schema/version/migration identities derive from 1.12; generated files use their owners; no release or GitHub action]
- **executor_discretion:** [precise concise prose within D-001–D-003, test helper factoring, assertion order, changelog wording, mechanical digest calculation]
- **files:** [`standards/agent-handoff/versions/1.12/**` (create; owner T1), `standards/agent-handoff/standard.toml` (modify; owner T1), `src/project_standards/payloads/agent-handoff/1.12/**` (create through projection generator; owner T1), `standards/catalog.md` (modify through catalog renderer; owner T1), `tests/package_contract/test_agent_handoff_1_12.py` (create; owner T1), `tests/test_repository_hygiene.py` (modify executable-path inventory; owner T1), `CHANGELOG.md` (modify Unreleased only; owner T1)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** block before writes if EG-001 fails. Before the checkpoint, revert only the unreleased T1 paths or forward-fix them; after a completed checkpoint, append a correction task. Never edit 1.11, relax a negative control, resolve the residual implicitly, or activate/publish to make a gate pass.
- **acceptance:** PV-T1-001 proves EG-001 preceded all payload writes; the two corrected documents state exactly their approved current targets; mutation controls reject the former defects and over-corrections; 1.12 has 43 matching paths/modes with exactly six permitted differences; all package identities/digests/projection/catalog facts agree; 1.11 remains exact/default; 1.12 remains unadvertised; and the exact package, Markdown, diff, and full repository gates pass.
- **sub-tasks:**
  - **T1.1 PRECHECK / INVENTORY** — validate EG-001 and record its commit; run `scripts/bootstrap-worktree.sh`; run `uv run python scripts/family_preflight.py agent-handoff`; capture the 1.11 43-path/mode/digest inventory, current catalog/root/lock state, six-path intended delta, legacy-reference bytes/roles, and focused negative-control expectations before editing.
  - **T1.2 AUTHOR CONTRACT** — add the 1.12 focused package contract and executable-path inventory first. Its initial failure must be the absent 1.12 candidate or the two still-incorrect copied guidance assertions, not collection, environment, or predecessor drift.
  - **T1.3 APPLY** — copy 1.11 to 1.12; apply only the approved #140 and #165 prose plus mechanical 1.12 identity/migration/schema/digest updates; add the family aggregate row and Unreleased changelog entry. Do not edit 1.11, family-root authority, Catalog 5, engine/provider code, or legacy integration bytes.
  - **T1.4 GENERATE** — run the projection generator in write mode and catalog renderer in write mode; verify exactly 43 relative 1.12 projection links, the new executable path is mode-classified, and generated catalog facts show 1.12 `unadvertised` while 1.11 remains `default`.
  - **T1.5 VERIFY GUIDANCE / NEGATIVE CONTROLS** — run the focused contract, exact `rg`/diff inspection, and the four temporary mutation controls from §7 one at a time; each must fail for the named reason, then restore the candidate and rerun green. Confirm the legacy runbook contains one historical per-harness `session_start.py` reference and one current `session-start` confirmation, and the two legacy integration resources equal 1.11 bytes.
  - **T1.6 Verify Task** — rerun `scripts/bootstrap-worktree.sh`; execute PV-T1-001's focused tests, five package commands, scoped/new-file and Git-tracked Markdown gates, `git diff --check`, and direct-local `scripts/verify.sh --full`; inspect final name-status and diff against the authorized paths; validate this plan; create and validate the T1 checkpoint.

## 10. Integration, Migration, and Recovery

### 10.1 Integration Sequence

1. Verify EG-001 and bootstrap before any successor write.
2. Create the focused contract and complete 1.12 as one serialized package candidate.
3. Generate projection/catalog facts, run mutation controls, then run exact package and Markdown gates.
4. Run the final direct-local full gate and checkpoint T1. Activation/release work may consume the checkpoint later under separate authority.

### 10.2 Candidate Transition

- Required: package-candidate composition only; no consumer migration or live reconciliation.
- Compatibility period: 1.11 remains Catalog 5 default/current family authority while 1.12 is indexed and exact-selectable only from the producer source as unadvertised.
- Idempotency: repeated projection generation and catalog rendering over unchanged source produce no diff; every `--check` command remains green.
- Point of no return: none in this plan. Publication and issue closure are external.
- Rollback / forward repair: remove/revert the unreleased 1.12 checkpoint before external consumption, or append a correction task after completion. Preserve 1.11 and the #156 checkpoint.
- Recovery proof: PV-T1-001 byte/mode/digest comparisons, generated-file checks, non-activation controls, and rerun idempotency.

### 10.3 Late Failure and Correction

A stale #156 checkpoint, unexpected seventh payload difference, graph/schema-reference finding, changed legacy fixture, accidental activation, Markdown failure, or full-gate failure blocks T1. If the failure exposes unresolved retirement intent, return the smallest amendment request to #140's owner. Otherwise append one correction task, preserve completed history, and rerun the focused proof plus every final gate.

## 11. Risks, Assumptions, and Open Questions

### 11.1 Risks

| ID | Risk | Likelihood | Impact | Treatment | Owner / Task |
| --- | --- | --- | --- | --- | --- |
| R-001 | Correct V5-native wording is read as a universal promise for migrated/adopted locks. | medium | high | Name the clean V5-native precondition and explicit deferred residual; reject broader/manual prose in focused assertions. | T1 |
| R-002 | A broad search replaces correct historical `session_start.py` evidence. | medium | high | Allow one runbook historical occurrence, byte-compare both legacy integration resources, and pin their `legacy-reference` roles. | T1 |
| R-003 | Copying 1.11 leaves a stale self-version, migration endpoint, resource digest, or executable inventory row. | medium | high | EG-001, manifest-derived graph validation, exhaustive byte/mode contract, family preflight, projection/catalog checks, and full gate. | T1 |
| R-004 | The candidate advances default/root/self-host state before release authority. | low | high | Assert `catalogs/5.toml`, family roots, `.standards` config/lock, and release version unchanged; require generated role `unadvertised`. | T1 |

### 11.2 Assumptions

| ID | Assumption | Impact if False |
| --- | --- | --- |
| A-001 | #156's final prerequisite remains T2/PV-T2-001 under plan revision 1. | If revised or superseded, block before payload writes and revise EG-001 under owner authority. |
| A-002 | The approved #140 correction may describe current behavior without adding an engine regression fixture in this documentation-only cut. | If the owner requires new engine behavior/proof, split that work into a separately authorized plan rather than widening T1. |

### 11.3 Open Questions

None.

## 12. Final Verification

- Bridge 3.5.0 validates this plan and the T1 checkpoint/trailer identity; EG-001 names a unique valid #156 T2 checkpoint and its PV-T2-001 rerun is green.
- Every Must/Should requirement maps to T1 and passing PV-T1-001; no documentation claim relies on a broad gate in place of focused assertions.
- The 1.12 adoption guide contains no manual `git rm` instruction or false no-retirement claim, describes only clean V5-native removal plus modified-byte refusal, and leaves `created_container=False` unresolved.
- Legacy-migration §4 uses the compiled launcher as the one current confirmation target; all correct legacy references and both legacy integration resource bytes/roles remain exact.
- The 1.12 and 1.11 payload trees each contain 43 matching paths and modes; exactly the six allowed 1.12 paths differ; all options, artifacts, contributions, providers, templates, launcher bytes, and outputs remain equivalent.
- 1.12 manifest identity, migration endpoints, schema constants, raw digests, family aggregate, 43 relative projection links, executable allowlist, and generated catalog facts are internally consistent. The #156 graph guard rejects the stale-identity mutation.
- `catalogs/5.toml`, family-root authority docs, `.standards/config.toml`, `.standards/lock.toml`, release metadata/version, 1.11 bytes/digest, and GitHub state remain unchanged; 1.11 is default and 1.12 is unadvertised.
- **Binding** — Run and observe success for these verification commands:

  ```bash
  PYTHONPATH="$PWD/build/wheel-runtime" uv run pytest \
    tests/package_contract/test_agent_handoff_1_12.py \
    tests/test_repository_hygiene.py
  uv run project-standards standards validate-packages --root . --json
  uv run project-standards standards validate-graph --root . --require-all-manifests --json
  uv run project-standards standards generate-package-schemas --root . --check
  uv run project-standards standards sync-payload-projection --root . --check
  uv run project-standards standards render-catalog --root . --check
  git ls-files -z -- ':(glob)**/*.md' ':(glob)**/*.json' ':(glob)**/*.jsonc' ':(glob)**/*.yml' ':(glob)**/*.yaml' | xargs -0 -r npx prettier --check --
  git ls-files -z -- ':(glob)**/*.md' ':(glob,exclude).pytest_cache/**' ':(glob,exclude).ruff_cache/**' ':(glob,exclude).venv/**' ':(glob,exclude)node_modules/**' | sed -z 's|^|:|' | xargs -0 -r npx markdownlint-cli2 --no-globs
  git diff --check
  scripts/verify.sh --full
  ```

- Before the Git-tracked Markdown commands, explicitly run Prettier/markdownlint over every new untracked 1.12 Markdown path or stage intent-to-add so the new files cannot escape the corpus. Run all Git-dependent commands directly in the local checkout, never via rexec.
- No blocker, unapproved deviation, unresolved correction, activation/publication action, or orphan generated fact remains.

## 13. Close-out

- **Completed:** record the T1 checkpoint commit and the verified unadvertised 1.12 aggregate digest.
- **Decisions / deviations harvested:** record only an approved change to the six-path delta, retirement wording boundary, or prerequisite checkpoint; do not rewrite completed task definitions.
- **Risks closed / accepted:** close R-001 through R-004 from focused proof or route a remaining residual to separately governed work.
- **Deferred/discovered work filed:** `created_container=False` semantics, #142, Catalog/default activation, release publication, and issue closure remain external.
- **Source/ADR/handoff reconciliation:** update no ADR or Agent Handoff state under this plan. The Unreleased changelog and versioned package are the durable implementation record; a parent release workflow owns later lifecycle truth.
- **Scratch teardown:** only the orchestrator may remove execution state after the checkpoint, concise evidence, and any correction notes are committed and no downstream consumer needs ephemeral logs.

## Appendix A. Interface and State Contracts

| Contract | Owner / Producer Task | Consumer(s) | Current | Planned / States | Errors / Limits | Compatibility / Invariant | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `agent-handoff-1.12-retirement-guidance-v1` | T1 | V5-native adopters | Guide says retirement is unsupported and manual. | For unchanged managed whole file with platform-created container: reconcile removes; modified bytes: `CP-MODIFIED-MANAGED`; `created_container=False`: deferred, no prescription. | No engine or consumer mutation under this plan. | Wording cannot broaden verified behavior into migrated/adopted semantics. | #140 triage; `_classify_removed` |
| `agent-handoff-1.12-legacy-target-v1` | T1 | legacy-migration readers | §4 current confirmation target is retired Python path. | §4 confirms `.agents/hooks/agent-handoff/session-start`; historical evidence keeps `session_start.py`. | Exactly one runbook current-target line changes. | Legacy integration resources remain byte-identical and `legacy-reference`. | #165 triage; 1.11 payload |
| Unadvertised Agent Handoff 1.12 candidate | T1 | future release activation | 1.11 default, indexed, projected, root authority. | 1.12 complete/indexed/projected/generated as `unadvertised`; 1.11 selection unchanged. | Failed EG-001, package gate, or accidental activation blocks. | 43 paths/modes; six-path delta; no 1.11-to-1.12 migration needed for documentation-only rendering. | V2 authoring; request |

## Appendix B. Requirement-to-Proof Traceability

| Proof ID | Requirement(s) | Task | Method | Oracle | Command / Procedure | Expected Result | Negative Control | Environment | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PV-T1-001 | REQ-001–REQ-010 | T1 | documentation, byte/mode package contract, manifest-derived graph, projection/catalog, repository qualification | #140/#165 triage; `_classify_removed`; immutable 1.11 digest/tree; 1.11 manifest legacy roles; V2 validators; #156 T2 checkpoint | Verify EG-001; run `tests/package_contract/test_agent_handoff_1_12.py` and mode policy; run the five exact package commands, scoped/new-file and Git-tracked Markdown gates, `git diff --check`, and direct-local `scripts/verify.sh --full`; inspect final diff/name-status. | Approved guidance and current target are exact; six-path/43-file predecessor contract and legacy preservation pass; identities/digests/links/modes agree; 1.12 is unadvertised and 1.11 remains default/exact; all gates pass. | Reinsert manual `git rm`; restore wrong confirmation target; mutate a legacy integration byte; advertise 1.12; stale one schema self-version to 1.11. Each focused check/graph run fails for the intended reason, then restoration returns green. | bootstrapped local Git checkout; Git-dependent gate direct local | ephemeral |

## Appendix C. Durable Evidence

No separate evidence record is required: the committed focused package contract and validated identity-bearing T1 checkpoint make the inexpensive acceptance reproducible.

## Appendix D. Deferred Work

| Item | Reason Deferred | Follow-up / Reopen Trigger |
| --- | --- | --- |
| Whole-file retirement with `created_container=False` | #140 triage identifies a real migrated/adopted residual but no owner decision selects removal, preservation, or lock semantics. | A separately approved issue/design records the desired compatibility and migration behavior. |
| Agent Handoff command-provider/Go migration (#142) | Provider resources are not installed consumer artifacts and are explicitly outside this documentation cut. | Execute only under #142's own ADR/plan and dependency gates. |
| Catalog 5/default activation, family-root repoint, release publication, and issue closure | This plan must stop with an unadvertised local candidate. | A parent release workflow consumes the validated T1 checkpoint and explicitly authorizes activation/publication. |
