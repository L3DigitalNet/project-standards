---
plan_format: 3
title: 'Runner Label Reachability Advisory Implementation Plan'
slug: 'runner-label-advisory'
status: active
revision: 2
revises_revision: 1
revision_reason: 'bind T3 to the integrated #62 revision-2 Project Specification 1.9 checkpoint'
pause_reason: ''
source: 'issue L3DigitalNet/project-standards#143; verified triage and coordinated 5.19 release constraints'
spec_ref: ''
created: 2026-08-10
updated: 2026-08-10
owners:
  - 'Project Standards maintainers'
  - 'Coding agents under human review'
---

# Runner Label Reachability Advisory Implementation Plan

> **Definition, not state.** Plan authoring generated no `.project-pipeline` state. During execution, the orchestrator alone generates and mutates ephemeral state under `.project-pipeline/2026-08-10-runner-label-advisory/execution/`.

## 1. Objective

Ship unadvertised Markdown Tooling 1.15 and Markdown Frontmatter 1.11 candidates and extend the separately composed Project Specification 1.9 candidate so reconciliation reports a package-specific, non-fatal warning whenever non-empty `runner_labels` cannot reach an enabled caller. The advisory covers both consumer-owned callers and direct self-hosted workflow mode, stays silent when labels are empty or can reach a managed caller, and reaches a verified cross-package checkpoint before Project Specification conformance task T4 activates 1.9.

## 2. Authority and Source Map

| Source | Source Role | Authority / Use | Version / Date | Affected Plan Surface |
| --- | --- | --- | --- | --- |
| `issue:L3DigitalNet/project-standards#143` | normative | Outcome, reconcile-layer acceptance, package-specific wording, remedies, and no automatic rewrite/configuration scope. | body and comments verified 2026-08-10 | §§1, 3, 5–12; T1–T4 |
| `repo:ROADMAP.md#project-specification-conformance` | decision | #143 is separately governed in the 5.19 train and precedes #62 activation. | `5e1b04f1` | §§3, 8–12; T3–T4 |
| `repo:docs/plans/2026-08-10-schema-payload-reference-validation-plan.md#t2-document-the-successor-cut-guard-and-verify-the-repository` | decision | #156 must supply its verified T2 checkpoint before any successor payload mutation. | revision 1, 2026-08-10 | §§3, 8–10; T1–T3 |
| `repo:docs/plans/2026-08-01-project-spec-conformance-plan.md#t3-compose-and-verify-project-specification-19-candidate` | decision | Produces the unreleased, unadvertised Project Specification 1.9 candidate that #143 must extend rather than recut; integrated checkpoint `318946a5` carries revision-2 digest `d0ae03fd…09d4c`. | revision 2, 2026-08-10 | §§3–5, 8–10; T3 |
| `repo:docs/plans/2026-08-01-project-spec-conformance-plan.md#t4-activate-19-and-remediate-selected-dogfood` | decision | Consumes this plan's verified cross-package checkpoint before Catalog/self-host activation. | revision 2, 2026-08-10 | §§3, 8–12; T4 |
| `spec:docs/specs/2026-08-01-project-spec-conformance-plan-input.md#selected-design` | decision | #62's conformance findings, coverage, exact matching, and predecessor-preservation contract that #143 must not change. | approved 2026-08-10 | §§3–5, 7, 9–12; T3–T4 |
| `repo:src/project_standards/control_plane/executor.py::_verify` | current-state evidence | Verify-phase warnings are retained in `ApplyResult.verification_findings`; only error findings fail apply. | `5e1b04f1` | §§4–5; T1–T4 |
| `repo:src/project_standards/control_plane/planner.py::_verification_requests` | current-state evidence | Every selected payload verify-phase findings provider becomes a post-apply reconciliation request. | `5e1b04f1` | §§4–5; T1–T4 |
| `repo:standards/markdown-tooling/versions/1.14/providers/markdown_tooling.py::_verify` | current-state evidence | Existing per-caller verify providers, enabled-tool gate, ownership removal, and self-hosted render path. | Markdown Tooling 1.14 | §§4–5; T1 |
| `repo:standards/markdown-frontmatter/versions/1.10/providers/frontmatter.py::run_render_workflow` | current-state evidence | Managed/consumer-owned contribution boundary and caller/self-hosted render paths; no verify provider exists. | Markdown Frontmatter 1.10 | §§4–5; T2 |
| `repo:standards/project-spec/versions/1.8/providers/project_spec.py::run_render_workflow` | current-state evidence | Managed/consumer-owned contribution boundary and caller/self-hosted render paths; no verify provider exists in 1.8. | Project Specification 1.8 | §§4–5; T3 |
| `repo:tests/package_contract/test_markdown_tooling_1_14.py` | current-state evidence | Successor immutability, projection, runner-label rendering, and self-hosted negative-control pattern. | `5e1b04f1` | §§4, 7; T1 |
| `repo:tests/package_contract/test_markdown_frontmatter_1_10.py` | current-state evidence | Successor immutability, projection, runner-label rendering, and self-hosted negative-control pattern. | `5e1b04f1` | §§4, 7; T2 |
| `repo:tests/package_contract/test_project_spec_1_8.py` | current-state evidence | Predecessor immutability and runner-label reachability baseline that #62's 1.9 candidate must retain. | `5e1b04f1` | §§4, 7; T3 |

Conflict precedence: issue #143 and its latest triage comment define advisory behavior. The two active child plans define release sequencing and file-ownership handoffs. Existing providers and tests establish the starting seams only; they do not narrow the accepted two-path warning boundary.

## 3. Scope, Boundaries, and Constraints

### 3.1 In Scope

- Provider-owned verify findings for a non-empty `runner_labels` selection that cannot reach an enabled caller because its workflow is consumer-owned or because `workflow_mode = "self-hosted"` bypasses `workflow_call` inputs.
- Package- and caller-specific warning identity and repair guidance: a consumer-owned caller must pass `runner-labels` itself or return the caller to management; direct self-hosted mode must move to a caller path or own and pin its `runs-on` selection.
- Complete Markdown Tooling 1.15 and Markdown Frontmatter 1.11 V2 payload candidates, source projections, family indexes, versioned documentation, package contracts, and generated unadvertised catalog entries.
- A serialized advisory extension to the unreleased Project Specification 1.9 candidate produced by #62 T3, preserving its conformance-lint behavior and proof.
- Direct-provider/package proof for each successor plus one cross-package reconciliation matrix over exact-selected candidates.

### 3.2 Out of Scope and Deferred

- No configuration key, option default, config-schema shape, severity enum, public finding schema, control-plane conditional, or central package-ID table.
- No automatic rewrite of consumer-owned workflows and no change to managed-caller rendering, runner-label serialization, reusable workflows, runner groups, or label eligibility.
- No edit to released Markdown Tooling 1.14, Markdown Frontmatter 1.10, Project Specification 1.8, or any older payload byte or mode.
- No Catalog 5 default change, self-host reconcile, root family-page activation, release version/changelog work, tag, asset, push, issue mutation, or publication. Project Specification T4 and the parent 5.19 release workflow own activation and publication.
- No execution-state generation during authoring. During implementation, workers never edit `.project-pipeline` files directly.

### 3.3 Ownership and Preserved Behavior

| Boundary | Owner / Responsibility |
| --- | --- |
| T1 owns | Markdown Tooling 1.15 advisory behavior, versioned package truth, projection, focused contract, and its serialized catalog contribution. |
| T2 owns | Markdown Frontmatter 1.11 verify-provider addition, versioned package truth, projection, focused contract, and its serialized catalog contribution. |
| T3 owns | Only the #143 extension of the completed #62 Project Specification 1.9 candidate, its refreshed digest/projection/tests, and its serialized catalog contribution. |
| T4 owns | The generated `standards/catalog.md` aggregate, cross-package reconcile-layer oracle, final integrated proof, and the verified checkpoint consumed by #62 T4. |
| Depends on | #156 T2 before T1–T3 payload writes; #62 T3 before T3 touches Project Specification 1.9; repository provider/checkpoint contracts. |
| Does not own | #156 implementation, #62 conformance engine/CLI behavior, Catalog/self-host activation, release publication, runner infrastructure, or GitHub lifecycle state. |
| Must preserve | Existing successful reconciliation and drift errors, empty/default rendering, managed-caller behavior, warning non-fatality, package option surfaces, released payload bytes, and #62's complete `project-spec-1.9-lint-v1` contract. |

### 3.4 Constraints and Authorization

- **EG-001 — payload-cut gate:** before T1, T2, or T3 writes any successor payload, verify #156 plan T2 is terminal at a commit carrying `Plan-Id: 2026-08-10/schema-payload-reference-validation`, `Plan-Task: T2`, `Plan-Status: done`, and `Plan-Proofs: PV-T2-001`; validate that plan and rerun its graph/corpus acceptance. Absence or failed proof blocks all payload work.
- **EG-002 — Project Specification handoff:** before T3 writes Project Specification 1.9, verify exact commit `318946a54acf0053ffa2e6068ba34fcf9b2808c7` carries `Plan-Id: 2026-08-10/project-spec-conformance`, `Plan-Task: T3`, `Plan-Revision: 2`, `Plan-Definition-Digest: d0ae03fd313d984abdb635e439cb3ea47d44c9f8bbf8a39c2a2cd95383609d4c`, `Plan-Status: done`, and `Plan-Proofs: PV-T3-001`; validate the plan and confirm 1.9 is complete, unadvertised, and Catalog/self-host still select 1.8.
- **EG-003 — activation handoff:** #62 T4 may begin only after this plan's T4 commit carries `Plan-Id: 2026-08-10/runner-label-advisory`, `Plan-Task: T4`, `Plan-Status: done`, and `Plan-Proofs: PV-T4-001`, and the plan plus checkpoint validate.
- The warning condition is derived from resolved configuration. Empty/unset `runner_labels` is silent. Markdown Tooling evaluates each enabled lint/format caller independently; a disabled tool produces no dead-caller warning.
- The successor schemas retain the same option set, types, and defaults. Mechanical successor identity constants and manifest/resource digests may change, but no configuration or public finding-schema contract may widen.
- `standards/catalog.md` is generator-owned and serialized through T4 as aggregator. T1–T3 may refresh their contributions only in dependency order; no two task worktrees independently merge that file.
- Run `scripts/family_preflight.py` before each new successor cut. After any payload or `src/**` change, rerun `scripts/bootstrap-worktree.sh`; do not reconstruct its steps.
- Git/history/index-dependent commands, including `scripts/verify.sh`, run directly in the local checkout. Compatible CPU-heavy BasedPyright runs as `rexec -- uv run basedpyright`. Git and package metadata inspection never runs through rexec.

## 4. Current State and Target State

### 4.1 Current State

All three released packages accept optional `runner_labels` and inject them only into caller-mode `workflow_call` inputs. A consumer-owned caller is excluded from the managed expectation set, while self-hosted mode returns a direct static workflow before caller rendering. The configured value is therefore inert in both paths.

Markdown Tooling already has post-apply verify providers for its lint and format targets, but they report only managed-byte drift. Markdown Frontmatter and Project Specification expose findings providers for document validation, not post-apply reconciliation verification, so their manifests currently request no verify-phase reconciliation result. The control plane already preserves warning findings without failing apply; an error finding alone makes verification fatal.

Catalog 5 currently advertises Markdown Tooling 1.14, Markdown Frontmatter 1.10, and Project Specification 1.8. The active #62 child plan separately composes Project Specification 1.9 with conformance linting before #143 may edit it, then waits for this plan's final checkpoint before activating it.

### 4.2 Target State

Each successor payload owns a verify-phase advisory at its package boundary. A non-empty label selection yields one warning per affected enabled caller, with the provider invocation supplying the package/version identity and the finding naming the caller path and the reason labels are unreachable. Managed caller mode with non-empty labels remains clean; empty/unset labels remain clean for every ownership/mode combination. Existing error findings, rendering, and reconciliation semantics remain unchanged.

Markdown Tooling 1.15 and Markdown Frontmatter 1.11 are complete unadvertised candidates. Project Specification 1.9 remains the same #62 candidate, extended in place only after #62 T3 and still unadvertised. The final cross-package reconciliation proof leaves Catalog 5 and self-host state unchanged and supplies the checkpoint #62 T4 requires.

### 4.3 Delta Summary

| Area | Current | Target | Must Preserve |
| --- | --- | --- | --- |
| Advisory behavior | Inert `runner_labels` configurations are silent. | Verify-phase warning names each affected package/caller and a state-correct remedy. | Warning is non-fatal; error findings retain current failure behavior. |
| Markdown Tooling | 1.14 verify providers report drift only. | 1.15 adds dead-label warnings to the existing per-tool verify seam. | Disabled tools, rendering, drift detection, and 1.14 bytes. |
| Markdown Frontmatter | 1.10 has no post-apply verify provider. | 1.11 declares a findings verify provider for caller reachability. | Document validation, render/migration behavior, and 1.10 bytes. |
| Project Specification | 1.8 has no verify provider; #62 composes 1.9 independently. | The completed #62 1.9 candidate gains only #143's reachability verify contract. | #62 lint/coverage behavior, conformance proof, and 1.8 bytes. |
| Package/config state | Three advertised predecessors; no candidate rows. | Three complete unadvertised successor candidates. | Catalog/self-host selections and option schemas/defaults do not advance. |

## 5. Change Surface and Architecture

### 5.1 Components and Ownership

| Component / Surface | Current Responsibility | Planned Responsibility | Paths / Contracts | Owning Task |
| --- | --- | --- | --- | --- |
| Markdown Tooling verification | Per-enabled-tool managed-byte verification. | Retain drift checks and add one warning when that enabled caller cannot receive non-empty labels. | `runner-label-reachability-v1`; 1.15 provider/manifest | T1 |
| Markdown Frontmatter verification | No post-apply verify request. | Add a config-only verify provider returning the same advisory contract. | `runner-label-reachability-v1`; 1.11 provider/manifest | T2 |
| Project Specification verification | No post-apply verify request; #62 owns 1.9 lint contract. | Add a config-only verify provider without altering conformance validation/lint output. | `runner-label-reachability-v1`; 1.9 provider/manifest | T3 |
| Package candidates | Released predecessors and selected projections. | Complete source payload, family index, symlink projection, versioned docs, and unadvertised generated catalog facts. | V2 family/payload/projection contracts | T1–T3; aggregate T4 |
| Reconcile integration | Warnings can traverse apply, but no real three-package advisory matrix exists. | Exact-selected plan/apply proof covers triggers, silences, warning identity, non-fatality, and unchanged selections. | `runner-label-advisory-checkpoint-v1` | T4 |

### 5.2 Verification Flow

```text
resolved package config + planned target snapshot
                    │
                    ▼
selected successor verify provider
  ├─ runner_labels empty                         → no reachability warning
  ├─ managed caller mode                         → existing verification only
  ├─ consumer-owned enabled caller               → package/caller warning + own-caller remedy
  └─ self-hosted enabled caller                  → package/caller warning + mode/runs-on remedy
                    │
                    ▼
executor post-apply verification
  ├─ warning findings retained; apply succeeds
  └─ existing error findings still fail apply
```

### 5.3 Change-Surface Matrix

| Surface | Applies? | Invariant / Required Change | Proof | Task |
| --- | --- | --- | --- | --- |
| Behavior | yes | Both unreachable-label paths warn; reachable/empty paths stay silent. | PV-T1-001–PV-T4-001 | T1–T4 |
| Architecture / dependency direction | yes | Package providers own package option/ownership semantics; the control plane remains generic. | PV-T4-001 | T1–T4 |
| Public / cross-task interface | yes | Findings retain the existing provider schema and severity; new verify declarations use existing operation/effect contracts. | PV-T1-001–PV-T4-001 | T1–T4 |
| Data / state | no | No persistent state or migration is introduced. | PV-T4-001 | T4 |
| Configuration | yes | No key/default/schema-shape change; only resolved existing values drive warnings. | PV-T1-001–PV-T4-001 | T1–T4 |
| Security / trust | yes | Labels remain schema-validated data; providers execute no label content, subprocess, network, or path expansion. | PV-T1-001–PV-T3-001 | T1–T3 |
| Compatibility / migration | yes | Released payloads are byte/mode immutable; selected/default roles do not advance. | PV-T1-001–PV-T4-001 | T1–T4 |
| Operations / deployment | yes | Stop at an unpublished local checkpoint; #62 T4 and parent release work own activation. | PV-T4-001 | T4 |
| Documentation | yes | Each versioned successor explains when the option is inert and how to repair it. | PV-T1-001–PV-T3-001 | T1–T3 |
| Durable evidence | no | Committed contracts and identity-bearing task checkpoints are reproducible. | PV-T4-001 | T4 |

### 5.4 Binding Decisions

| ID | Decision | Rationale | Source | Affected Task(s) |
| --- | --- | --- | --- | --- |
| D-001 | Emit provider-owned `warning` findings; do not change the control-plane model or hardcode package semantics centrally. | The severity and transport already exist, while ownership option names differ by package. | issue #143 triage; current provider/executor boundary | T1–T4 |
| D-002 | Treat both consumer-owned callers and `workflow_mode = "self-hosted"` as unreachable when labels are non-empty. | Both paths bypass the caller input that alone can carry `runner-labels`. | issue #143 latest triage comment; current render paths | T1–T4 |
| D-003 | Emit one warning per affected enabled caller, with provider invocation identity naming the package. | Markdown Tooling has two independently enabled/owned callers; per-caller findings identify the exact repair surface without inventing a central aggregate. | issue #143 package-specific wording; current per-tool verify providers | T1, T4 |
| D-004 | Add verify declarations to the two payloads that lack them, reusing existing input/findings schemas unchanged. | Reconcile executes verify-phase providers for every selected payload; document validation is not a steady-state post-apply hook. | planner/executor current-state evidence | T2–T3 |
| D-005 | Cut 1.15 and 1.11, but extend the already composed 1.9 candidate rather than making a second Project Specification cut. | The #62/#143 collision is explicitly resolved as one Project Specification 1.9 payload. | issue #143 triage; #62 T3/T4 contract | T1–T3 |
| D-006 | Keep all three candidates unadvertised and use this plan's T4 as the #62 activation prerequisite. | Activation must include the complete same-train Project Specification candidate and remain under #62 T4/parent release authority. | active #62 child plan | T3–T4 |

## 6. Requirements and Acceptance

| ID | Requirement | Source | Priority | Owner Task | Task(s) | Proof(s) |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-001 | For each enabled caller in the three successors, non-empty `runner_labels` with consumer-owned caller ownership or direct self-hosted mode shall emit a non-fatal warning naming the selected package, affected caller, unreachable reason, and state-correct remedy. | issue #143 body and latest triage comment | Must | T4 | T1, T2, T3, T4 | PV-T1-001, PV-T2-001, PV-T3-001, PV-T4-001 |
| REQ-002 | Empty/unset labels and non-empty labels in managed caller mode shall emit no reachability warning; disabled Markdown Tooling callers, existing drift errors, rendering bytes, and apply failure taxonomy shall remain unchanged. | issue #143 acceptance; current providers/executor | Must | T4 | T1, T2, T3, T4 | PV-T1-001, PV-T2-001, PV-T3-001, PV-T4-001 |
| REQ-003 | Markdown Tooling 1.15 shall be a complete unadvertised successor whose two existing verify providers implement the advisory while 1.14 remains byte/mode immutable. | issue #143; release constraint | Must | T1 | T1, T4 | PV-T1-001, PV-T4-001 |
| REQ-004 | Markdown Frontmatter 1.11 shall be a complete unadvertised successor with an existing-schema verify declaration and advisory while 1.10 remains byte/mode immutable. | issue #143; release constraint | Must | T2 | T2, T4 | PV-T2-001, PV-T4-001 |
| REQ-005 | The #62-produced Project Specification 1.9 candidate shall gain the existing-schema verify advisory without changing its conformance lint/coverage contract, and Project Specification 1.8 shall remain byte/mode immutable. | issue #143; #62 T3 contract | Must | T3 | T3, T4 | PV-T3-001, PV-T4-001 |
| REQ-006 | Exact-selected cross-package reconciliation shall prove warning transport and negative cases, leave Catalog/self-host selections unchanged, and finish at a validated T4 checkpoint before #62 T4 activation. | issue #143 acceptance; #62 T4 contract | Must | T4 | T4 | PV-T4-001 |

## 7. Verification and Evidence Strategy

- **Authoritative commands:** focused successor package contracts; a cross-package exact-selected plan/apply regression; the five package/graph/schema/projection/catalog validators; Git-tracked Prettier and markdownlint; Ruff; `rexec -- uv run basedpyright`; direct-local intermediate `scripts/verify.sh`; and direct-local final `scripts/verify.sh --full`.
- **Oracles:** resolved option values; contribution ownership/mode predicates; provider invocation `standard_id`/version enrichment; current executor warning/error behavior; released predecessor aggregate digests and file bytes/modes; #62 PV-T3-001; and unchanged Catalog/self-host selections.
- **Negative controls:** empty and absent labels; managed caller mode; one disabled Markdown Tooling tool; one consumer-owned Markdown Tooling caller while the other remains managed; self-hosted mode; an existing drift error alongside an advisory; duplicate-provider/advisory mutation; predecessor-byte mutation; config-schema/default drift; accidental catalog activation; and removal of #62 conformance metadata/checks.
- **Test layers:** direct provider contract, payload integrity/family/projection, generated catalog, control-plane plan/apply integration, predecessor compatibility, source/candidate runtime, Python static checks, Markdown validation, and fast/full repository gates.
- **External environments:** no network, hosted runner, GitHub mutation, or live runner pool is needed. Git-aware repository gates run only in the local checkout; BasedPyright may run remotely through rexec.
- **Evidence:** repeatable command output is ephemeral. The four task commits and their validated `Plan-*` trailers are the durable checkpoint trail; no separate evidence document is required.
- **Late failure:** block the owning task. If an integrated failure disproves a completed package checkpoint, append a correction task with `corrects:` and `discovered_from:`, rerun its proof, then rerun PV-T4-001 without changing completed definitions.

## 8. Execution Summary

| Task | Title | Disposition | Work Type | Phase | Depends On | Requirement(s) | Primary Proof | Parallel / Conflict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T1 | Cut Markdown Tooling 1.15 with reachability warnings | active | brownfield-behavior | P1 | None | REQ-001, REQ-002, REQ-003 | PV-T1-001 | no / generated catalog owner T4 |
| T2 | Cut Markdown Frontmatter 1.11 with reconciliation verification | active | brownfield-behavior | P1 | T1 | REQ-001, REQ-002, REQ-004 | PV-T2-001 | no / serialized catalog and projection allowlist |
| T3 | Extend the composed Project Specification 1.9 candidate | active | brownfield-behavior | P2 | T2 | REQ-001, REQ-002, REQ-005 | PV-T3-001 | no / #62 ownership handoff and generated catalog |
| T4 | Prove cross-package reconciliation and checkpoint the candidate set | active | transition | P3 | T3 | REQ-001–REQ-006 | PV-T4-001 | no / aggregate test and generated catalog owner |

External gates are execution preconditions, not local task IDs: EG-001 binds every payload task, EG-002 additionally binds T3, and EG-003 is the downstream handoff produced by T4.

## 9. Implementation Tasks

### Phase P1: Independent Successor Packages

#### T1: Cut Markdown Tooling 1.15 with reachability warnings

- **disposition:** active
- **outcome:** Markdown Tooling 1.15 is a complete unadvertised candidate whose existing lint/format verify providers add precise non-fatal reachability warnings without changing rendering, disabled-tool behavior, or drift errors.
- **work_type:** brownfield-behavior
- **checkpoint:** one green commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** public
- **depends_on:** []
- **dependency_reason:** none
- **requirements:** [REQ-001, REQ-002, REQ-003]
- **proof:** [PV-T1-001]
- **source_refs:** [issue:L3DigitalNet/project-standards#143, repo:standards/markdown-tooling/versions/1.14/providers/markdown_tooling.py::_verify, repo:tests/package_contract/test_markdown_tooling_1_14.py::test_markdown_tooling_1_14__self_hosted_mode__ignores_the_caller_option, repo:docs/plans/2026-08-10-schema-payload-reference-validation-plan.md#t2-document-the-successor-cut-guard-and-verify-the-repository]
- **consumes:** [verified EG-001 checkpoint, complete immutable Markdown Tooling 1.14 payload, existing per-tool verify/provider findings contract, V2 family/projection/catalog contracts]
- **produces:** [markdown-tooling-1.15-runner-label-advisory-v1, unadvertised Markdown Tooling 1.15 source/projection/catalog contribution]
- **preserves:** [all 1.14 bytes/modes, option schema/defaults, empty and managed caller rendering, disabled-tool silence, existing drift finding codes/severity/exit behavior, Catalog 5 and self-host selection]
- **invariants:** [one warning per affected enabled lint/format caller, package/version supplied by provider invocation, no central control-plane condition, provider findings remain schema-valid and deterministically ordered]
- **executor_discretion:** [family-native warning code names, private helper names, exact sentence wording within the required identity/remedy contract, focused fixture organization, mechanical copy/digest workflow]
- **files:** [`standards/markdown-tooling/versions/1.15/**` (create; owner T1), `src/project_standards/payloads/markdown-tooling/1.15/**` (create via projection; owner T1), `standards/markdown-tooling/standard.toml` (modify; owner T1), `tests/package_contract/test_markdown_tooling_1_15.py` (create; owner T1), `standards/catalog.md` (modify through renderer; owner T4)]
- **parallel_safe:** no
- **conflicts_with:** [T2, T3, T4]
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** revert only the T1 checkpoint/candidate if advisory or package proof fails. Never modify 1.14, suppress an existing drift error, weaken EG-001, or advance Catalog/self-host selection to recover.
- **acceptance:** PV-T1-001 proves enabled lint and format callers warn independently for consumer-owned and self-hosted label configurations, remain silent for empty/managed/disabled cases, retain existing drift errors and non-fatal warning transport, preserve every 1.14 byte/mode, and form a valid unadvertised 1.15 payload/projection/catalog contribution.
- **sub-tasks:**
  - **T1.1 PRECHECK / CHARACTERIZE** — validate EG-001 and run `scripts/family_preflight.py markdown-tooling`; capture 1.14 aggregate/files/modes, resolved defaults, per-tool verify findings, caller renders, catalog/self-host roles, and current package gates.
  - **T1.2 RED** — mechanically copy 1.14 into an identity-correct 1.15 test candidate without advisory logic, add focused provider cases, and confirm failures are missing reachability warnings while drift/empty/managed cases already produce their characterized results.
  - **T1.3 Verify RED** — run the focused 1.15 provider selection and confirm neither absent paths, stale digests, import errors, nor fixtures explain the failure.
  - **T1.4 GREEN** — add the minimum per-tool warning condition and versioned documentation, refresh payload identity/digests/family index/projection, and render the unadvertised catalog contribution.
  - **T1.5 Verify GREEN / REFACTOR** — prove the consumer-owned, self-hosted, managed, empty, disabled, mixed-ownership, and drift-plus-warning matrix; remove only duplicated private condition/wording while keeping results fixed.
  - **T1.6 Verify Task** — rerun bootstrap; PV-T1-001; the five package checks; Markdown checks; Ruff; `rexec -- uv run basedpyright`; `git diff --check`; immutable-predecessor/diff inspection; and direct-local `scripts/verify.sh`; create the checkpoint.

#### T2: Cut Markdown Frontmatter 1.11 with reconciliation verification

- **disposition:** active
- **outcome:** Markdown Frontmatter 1.11 is a complete unadvertised candidate with a post-apply verify declaration that reports the reachability advisory without changing document validation, workflow rendering, migration, or option behavior.
- **work_type:** brownfield-behavior
- **checkpoint:** one green commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** public
- **depends_on:** [T1]
- **dependency_reason:** ordering-only: T2 consumes T1's rendered `standards/catalog.md` contribution and serializes the next aggregate update; EG-001 independently remains mandatory
- **requirements:** [REQ-001, REQ-002, REQ-004]
- **proof:** [PV-T2-001]
- **source_refs:** [issue:L3DigitalNet/project-standards#143, repo:standards/markdown-frontmatter/versions/1.10/providers/frontmatter.py::run_render_workflow, repo:tests/package_contract/test_markdown_frontmatter_1_10.py::test_markdown_frontmatter_1_10__self_hosted_mode__ignores_the_caller_option, repo:src/project_standards/control_plane/planner.py::_verification_requests]
- **consumes:** [verified EG-001 checkpoint, T1 generated-catalog state, complete immutable Markdown Frontmatter 1.10 payload, existing provider input/findings schemas, V2 family/projection contracts]
- **produces:** [markdown-frontmatter-1.11-runner-label-advisory-v1, unadvertised Markdown Frontmatter 1.11 source/projection/catalog contribution]
- **preserves:** [all 1.10 bytes/modes, option schema/defaults, validate/id-next/fix/migrate results, caller/self-hosted rendering, managed contribution ownership, Catalog 5 and self-host selection]
- **invariants:** [one config-only verify provider uses existing schemas; non-empty labels warn only when the configured caller path cannot consume them; no document snapshot or provider resource is required for the advisory]
- **executor_discretion:** [family-native warning code, verify provider/helper names, exact sentence wording within the required identity/remedy contract, focused fixture organization, mechanical copy/digest workflow]
- **files:** [`standards/markdown-frontmatter/versions/1.11/**` (create; owner T2), `src/project_standards/payloads/markdown-frontmatter/1.11/**` (create via projection; owner T2), `standards/markdown-frontmatter/standard.toml` (modify; owner T2), `tests/package_contract/test_markdown_frontmatter_1_11.py` (create; owner T2), `tests/test_repository_hygiene.py` (modify only for the new immutable executable projection entries predicted by family preflight; owner T2), `standards/catalog.md` (modify through renderer; owner T4)]
- **parallel_safe:** no
- **conflicts_with:** [T1, T3, T4]
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** revert only the T2 checkpoint/candidate while retaining T1. Do not reuse document validation as a steady-state reconcile hook, change existing schemas to fit the provider, edit 1.10, or activate 1.11.
- **acceptance:** PV-T2-001 proves the new verify request appears in reconciliation, emits one schema-valid warning for consumer-owned or self-hosted non-empty labels, remains silent for empty/managed cases, preserves all other provider behavior and every 1.10 byte/mode, and forms a valid unadvertised 1.11 payload/projection/catalog contribution.
- **sub-tasks:**
  - **T2.1 PRECHECK / CHARACTERIZE** — reconfirm EG-001 and T1, run `scripts/family_preflight.py markdown-frontmatter`, and capture 1.10 aggregate/files/modes, provider declarations/results, resolved defaults, renders, executable projection allowlist, and catalog/self-host roles.
  - **T2.2 RED** — mechanically copy 1.10 into an identity-correct 1.11 test candidate without a verify declaration/implementation, add focused provider/manifest cases, and confirm the intended failure is the missing post-apply advisory contract.
  - **T2.3 Verify RED** — prove the candidate otherwise loads and validates so missing provider/advisory behavior, not identity, schema, import, or fixture failure, causes RED.
  - **T2.4 GREEN** — add the config-only verify provider/declaration and versioned documentation, refresh identities/digests/family index/projection and only the predicted executable allowlist, then render the unadvertised catalog contribution.
  - **T2.5 Verify GREEN / REFACTOR** — prove consumer-owned, self-hosted, managed, and empty cases plus unchanged validate/render/migrate behavior; keep the advisory helper local to package semantics.
  - **T2.6 Verify Task** — rerun bootstrap; PV-T2-001 and T1 regression; the five package checks; Markdown checks; Ruff; `rexec -- uv run basedpyright`; `git diff --check`; immutable-predecessor/diff inspection; and direct-local `scripts/verify.sh`; create the checkpoint.

### Phase P2: Shared Project Specification Candidate

#### T3: Extend the composed Project Specification 1.9 candidate

- **disposition:** active
- **outcome:** The verified, unadvertised Project Specification 1.9 candidate produced by #62 T3 gains only #143's post-apply reachability advisory and remains green under the complete conformance-lint contract.
- **work_type:** brownfield-behavior
- **checkpoint:** one green commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** [T2]
- **dependency_reason:** ordering-only: T3 consumes T2's serialized generated catalog and completed companion candidates; EG-002 separately supplies the authoritative 1.9 candidate and transfers its overlapping file claims after #62 T3 completion
- **requirements:** [REQ-001, REQ-002, REQ-005]
- **proof:** [PV-T3-001]
- **source_refs:** [issue:L3DigitalNet/project-standards#143, repo:docs/plans/2026-08-01-project-spec-conformance-plan.md#t3-compose-and-verify-project-specification-19-candidate, spec:docs/specs/2026-08-01-project-spec-conformance-plan-input.md#selected-design, repo:standards/project-spec/versions/1.8/providers/project_spec.py::run_render_workflow, repo:tests/package_contract/test_project_spec_1_8.py::test_project_spec_1_8__self_hosted_mode__ignores_the_caller_option]
- **consumes:** [verified EG-002 checkpoint, project-spec-1.9-lint-v1, complete unadvertised 1.9 source/projection/family/catalog facts, T1/T2 companion candidates, existing provider input/findings schemas]
- **produces:** [project-spec-1.9-runner-label-advisory-v1, #143-extended unadvertised Project Specification 1.9 source/projection/catalog contribution]
- **preserves:** [all Project Specification 1.8 bytes/modes, #62 conformance codes/checks/loci/line/severity and human/JSON behavior, 1.9 templates/schemas except unavoidable refreshed manifest identity/digests, Catalog 5/self-host 1.8 selection]
- **invariants:** [no second Project Specification version directory, no edit before EG-002, verify provider remains separate from document validate/lint providers, PV-T3-001 from the #62 plan reruns after the extension]
- **executor_discretion:** [family-native warning code, verify provider/helper names, exact sentence wording within the required identity/remedy contract, placement of concise advisory prose in existing 1.9 versioned docs]
- **files:** [`standards/project-spec/versions/1.9/providers/project_spec.py` (modify after EG-002; owner T3), `standards/project-spec/versions/1.9/payload.toml` (modify after EG-002; owner T3), `standards/project-spec/versions/1.9/{README.md,adopt.md,agent-summary.md}` (modify only for #143 owner truth; owner T3), `src/project_standards/payloads/project-spec/1.9/**` (refresh corresponding symlink projection after EG-002; owner T3), `standards/project-spec/standard.toml` (refresh 1.9 digest after EG-002; owner T3), `tests/package_contract/test_project_spec_1_9.py` (modify after #62 T3 ownership transfer; owner T3), `standards/catalog.md` (modify through renderer; owner T4)]
- **parallel_safe:** no
- **conflicts_with:** [T1, T2, T4]
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** if EG-002 is absent or its candidate differs from the declared contract, block before writes. After writes, revert only #143's 1.9 delta or append a correction task; never recopy 1.8 over the #62 candidate, weaken conformance proof, create 1.10, or activate the package.
- **acceptance:** PV-T3-001 proves consumer-owned and self-hosted non-empty labels emit the one Project Specification warning, managed/empty cases remain silent, the existing 1.9 conformance/coverage contract and its full #62 PV-T3-001 proof remain green, every 1.8 byte/mode remains immutable, and the refreshed 1.9 candidate stays complete and unadvertised.
- **sub-tasks:**
  - **T3.1 PRECHECK / CHARACTERIZE** — validate EG-002 and T2; capture the checkpoint commit, exact 1.9 digest/files/modes, #62 focused results, provider list, generated catalog row, and 1.8/default selections before editing.
  - **T3.2 RED** — extend the existing 1.9 contract with direct verify cases first; expected failures are the missing verify declaration/advisory while #62 conformance tests remain green.
  - **T3.3 Verify RED** — run the focused 1.9 selection and prove the failure is not missing candidate state, schema/import breakage, or conformance drift.
  - **T3.4 GREEN** — add the config-only verify provider/declaration and concise #143 versioned owner truth; refresh only affected manifest digests, 1.9 family aggregate, projection, and generated catalog facts.
  - **T3.5 Verify GREEN / REFACTOR** — prove the reachability matrix and rerun the complete #62 PV-T3-001 source/candidate contract; reject any conformance, template, output, or default-selection difference.
  - **T3.6 Verify Task** — rerun bootstrap; PV-T3-001 plus #62 PV-T1-001–PV-T3-001; T1/T2 regressions; the five package checks; Markdown checks; Ruff; `rexec -- uv run basedpyright`; `git diff --check`; immutable-predecessor/diff inspection; and direct-local `scripts/verify.sh`; create the checkpoint.

### Phase P3: Cross-Package Reconciliation Checkpoint

#### T4: Prove cross-package reconciliation and checkpoint the candidate set

- **disposition:** active
- **outcome:** A real exact-selected reconciliation matrix proves the three candidate packages surface only the intended non-fatal warnings, and its green commit becomes the sole #143 checkpoint consumed by #62 T4.
- **work_type:** transition
- **checkpoint:** one green integration-test commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** [T3]
- **dependency_reason:** consumes all three successor advisory contracts, their source projections, and the serialized unadvertised generated catalog produced through T3
- **requirements:** [REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006]
- **proof:** [PV-T4-001]
- **source_refs:** [issue:L3DigitalNet/project-standards#143, repo:src/project_standards/control_plane/planner.py::_verification_requests, repo:src/project_standards/control_plane/executor.py::_verify, repo:docs/plans/2026-08-01-project-spec-conformance-plan.md#t4-activate-19-and-remediate-selected-dogfood]
- **consumes:** [markdown-tooling-1.15-runner-label-advisory-v1, markdown-frontmatter-1.11-runner-label-advisory-v1, project-spec-1.9-runner-label-advisory-v1, unadvertised generated catalog aggregate]
- **produces:** [runner-label-advisory-checkpoint-v1, verified EG-003 handoff for #62 T4]
- **preserves:** [all package-task acceptance, warning ordering/serialization, existing error fatality, Catalog 5/default/self-host selections, no release or GitHub side effects]
- **invariants:** [tests execute the control-plane plan/apply boundary rather than only provider helpers; each expected warning is cardinality-checked; a warning-only apply succeeds and carries findings; an error still fails]
- **executor_discretion:** [integration fixture factoring, temporary repository layout, table organization, exact assertions beyond the binding finding fields and counts]
- **files:** [`tests/package_contract/test_runner_label_advisory.py` (create; owner T4), `standards/catalog.md` (final render/check; owner T4)]
- **parallel_safe:** no
- **conflicts_with:** [T1, T2, T3]
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** a failed integrated case blocks EG-003. Route the defect to an append-only correction task against its package owner, rerun that package proof, then rerun T4; never waive a failure, edit #62 T4, or activate/publish from this plan.
- **acceptance:** PV-T4-001 proves exact-selected plan/apply reconciliation emits the expected package/caller warning cardinality for both unreachable states, emits none for empty/managed/disabled controls, succeeds with warnings, still fails on an injected existing error, preserves all task-level package and #62 conformance proofs, leaves advertised/default/self-host roles unchanged, and yields a bridge-validated T4 checkpoint eligible for EG-003.
- **sub-tasks:**
  - **T4.1 ANCHOR** — validate this plan and T1–T3 checkpoints, inventory exact candidate digests/provider declarations/catalog roles, and freeze the expected warning matrix before adding the integrated test.
  - **T4.2 VERIFY PREREQUISITES** — rerun each package's focused proof and #62 PV-T3-001; block if any package task is not independently green.
  - **T4.3 RUN** — add and execute the real plan/apply matrix for all three exact-selected candidates, including warning-only success, no-warning controls, mixed Markdown Tooling ownership/enabled states, and an existing-error failure control.
  - **T4.4 TRIAGE / RERUN** — route any failure to its owning task/correction, then rerun the focused matrix and package proofs without weakening codes, counts, remedies, or negative controls.
  - **T4.5 Verify Task** — final-render `standards/catalog.md`; rerun bootstrap; PV-T4-001; all four focused files; the five package checks; Markdown checks; Ruff; `rexec -- uv run basedpyright`; `git diff --check`; direct-local `scripts/verify.sh --full`; validate the plan; create and validate the T4 checkpoint.

## 10. Integration, Migration, and Recovery

### 10.1 Integration Sequence

1. Verify EG-001 before any payload write. T1 cuts Markdown Tooling 1.15 and leaves a green unadvertised candidate.
2. T2 serializes the generated catalog, cuts Markdown Frontmatter 1.11, and leaves T1 plus T2 green and unadvertised.
3. Independently wait for and verify EG-002. T3 then receives the Project Specification 1.9 file claims, adds only #143's provider contract, reruns #62 PV-T3-001, and leaves all three candidates unadvertised.
4. T4 exercises the real reconciliation boundary, owns the final generated catalog aggregate, runs the final full gate, and records EG-003. Only then may #62 T4 take Project Specification/catalog ownership for activation.

### 10.2 Candidate / Selection Transition

- Required: candidate composition only; no consumer configuration or persistent-data migration.
- Compatibility period: 1.14, 1.10, and 1.8 remain advertised/default while 1.15, 1.11, and 1.9 are exact-selectable unadvertised candidates.
- Idempotency: repeated package validators, catalog rendering, source projection checks, and warning-only reconciliation over identical input produce no new repository change and the same ordered finding set.
- Point of no return: none in this plan. Release publication and issue closure are external.
- Rollback / forward repair: revert the latest unreleased package checkpoint before downstream consumption, or append a correction task after a completed checkpoint. Preserve released bytes and the #62 T3 base checkpoint.
- Recovery proof: task-level predecessor/digest checks plus PV-T4-001's repeat reconciliation and unchanged catalog/self-host roles.

### 10.3 Late Failure and Correction

A missing external checkpoint, unexpected 1.9 composition, duplicate/missing warning, package validation defect, conformance regression, or full-gate failure blocks the current task and EG-003. If target authority is unclear, return the smallest amendment request to the owning issue/plan. Otherwise append a permanent correction task with `corrects:` and `discovered_from:`, preserve completed history, and rerun the failed package proof plus PV-T4-001.

## 11. Risks, Assumptions, and Open Questions

### 11.1 Risks

| ID | Risk | Likelihood | Impact | Treatment | Owner / Task |
| --- | --- | --- | --- | --- | --- |
| R-001 | A package emits duplicate warnings because more than one findings provider evaluates the same caller. | medium | medium | Give each caller one verify owner and assert exact cardinality at provider and plan/apply layers. | T1–T4 |
| R-002 | The Project Specification edit overwrites or weakens #62's independently composed 1.9 contract. | medium | high | Block on EG-002, scope T3 to advisory files, compare the pre-edit candidate, and rerun #62 PV-T3-001. | T3 |
| R-003 | Parallel successor cuts produce incompatible `standards/catalog.md` output or family aggregate state. | medium | high | Serialize T1→T2→T3 and make T4 the sole aggregate owner/final renderer. | T1–T4 |
| R-004 | Warning wording offers a remedy that is valid for consumer-owned mode but wrong for direct self-hosted mode. | medium | medium | Assert state-specific hint content for both modes; keep the caller path and unreachable cause in each finding. | T1–T4 |
| R-005 | A candidate accidentally becomes Catalog 5/default/self-host selected before integrated proof. | low | high | Negative controls pin `catalogs/5.toml`, `.standards/config.toml`, `.standards/lock.toml`, family-root activation docs, and catalog roles unchanged/unadvertised. | T1–T4 |

### 11.2 Assumptions

| ID | Assumption | Impact if False |
| --- | --- | --- |
| A-001 | #156's final implementation checkpoint remains the T2/PV-T2-001 contract named by its active plan. | If that plan is revised, pause before payload writes and update EG-001 only through an approved plan revision. |
| A-002 | #62 T3 produced Project Specification 1.9 under the file/digest/conformance contracts declared in revision 2 and checkpointed at `318946a5`. | If the version, task, or acceptance changes, pause T3 and revise this plan after the upstream owner records the new contract. |
| A-003 | Existing provider input and findings schemas can express a config-only verify request without schema-shape changes. | If direct loading disproves this, stop T2/T3 and request an interface decision; do not widen schemas or move semantics into the engine implicitly. |

### 11.3 Open Questions

None.

## 12. Final Verification

- Bridge 3.5.0 validates this plan and every T1–T4 checkpoint/trailer identity; EG-001 and EG-002 were verified before their guarded writes, and EG-003 names the final T4 commit.
- Every Must requirement maps exactly to completed tasks and passing Appendix B proofs; no package task relies on T4 to excuse a failed direct-provider or package contract.
- Exact provider and plan/apply matrices prove both unreachable states, all silent controls, package/caller identity, state-correct remedies, deterministic cardinality/order, warning-only success, and existing-error failure.
- Markdown Tooling 1.15, Markdown Frontmatter 1.11, and the #143-extended Project Specification 1.9 pass payload integrity, family graph, schema generation, source projection, and catalog rendering as unadvertised candidates.
- Released 1.14, 1.10, and 1.8 payload bytes/modes/digests remain exact; configuration option sets/defaults and managed render behavior do not change.
- #62 PV-T1-001 through PV-T3-001 remain green after T3/T4; Project Specification 1.9 still exposes the approved conformance findings and clean-run coverage contract.
- `catalogs/5.toml`, `.standards/config.toml`, `.standards/lock.toml`, advertised family-root docs, release metadata, and GitHub state remain unchanged.
- The five package validators, Markdown gates, Ruff, `rexec -- uv run basedpyright`, `git diff --check`, and direct-local `scripts/verify.sh --full` pass after the last content change.
- No blocker, unapproved deviation, incomplete correction, publication action, or orphan generated-catalog contribution remains.

## 13. Close-out

- **Completed:** record T1–T4 checkpoint commits and the validated EG-003 handoff for #62 T4.
- **Decisions / deviations harvested:** record only approved changes to finding identity, upstream checkpoint contracts, or package ownership boundaries; do not rewrite completed task definitions.
- **Risks closed / accepted:** close R-001 through R-005 from proof or retain a bounded issue owned outside activation.
- **Deferred/discovered work filed:** activation, release publication, issue closure, and any runner-infrastructure change remain with #62 T4/parent 5.19 work or a separately governed issue.
- **Source/ADR/handoff reconciliation:** no ADR, Agent Handoff, or GitHub mutation is part of this plan. Provide the checkpoint commit to the #62 executor through its existing T4 precheck.
- **Scratch teardown:** only the orchestrator may remove this plan's execution state after all four checkpoints and concise evidence pointers are committed and EG-003 is consumable.

## Appendix A. Interface and State Contracts

| Contract | Owner / Producer Task | Consumer(s) | Current | Planned / States | Errors / Limits | Compatibility / Invariant | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `runner-label-reachability-v1` | T4 aggregate; T1–T3 package implementations | package users, reconcile CLI, T4 integration | Non-empty labels are silent when ownership/mode bypasses caller input. | Existing-schema warning per affected enabled caller; package/version from invocation; path/identity names caller; cause/remedy distinguishes consumer-owned from self-hosted. | Empty labels, managed caller mode, and disabled Markdown Tooling tool are silent; existing error findings remain errors. | Provider-owned semantics; no config/schema/control-plane change; deterministic finding ordering/cardinality. | issue #143; provider/executor contracts |
| Unadvertised successor set | T4 aggregate; T1–T3 package producers | #62 T4 and parent release work | Catalog defaults are 1.14/1.10/1.8. | Exact-selectable 1.15/1.11/1.9 candidates with generated `unadvertised` roles. | Missing EG-001/EG-002, package gate failure, or accidental activation blocks. | Released bytes immutable; `catalogs/5.toml` and self-host selection unchanged. | active #156/#62 plans; V2 package contracts |
| Project Specification ownership handoff | external #62 T3 → T3 → external #62 T4 | #143 T3, then #62 activation | #62 T3 owns composition; #62 T4 waits. | EG-002 transfers completed 1.9 advisory file claims to T3; EG-003 transfers verified candidate/catalog ownership to #62 T4. | No overlap or write before predecessor checkpoint; failed conformance proof blocks transfer. | One 1.9 cut; #62 behavior remains authoritative and fully reverified. | #62 child plan T3/T4 |
| `runner-label-advisory-checkpoint-v1` | T4 | #62 T4 | No #143 prerequisite exists. | Validated commit with plan identity/task/revision/digest/status/requirements/proofs trailers and green PV-T4-001. | Missing/mismatched trailer, plan validation, or proof blocks activation. | Checkpoint authorizes consumption only, not publication or issue closure. | EG-003; format-3 checkpoint contract |

## Appendix B. Requirement-to-Proof Traceability

| Proof ID | Requirement(s) | Task | Method | Oracle | Command / Procedure | Expected Result | Negative Control | Environment | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PV-T1-001 | REQ-001, REQ-002, REQ-003 | T1 | direct provider and V2 package contract | resolved 1.15 options; per-tool ownership/enabled predicates; released 1.14 digest/bytes/modes | Run `tests/package_contract/test_markdown_tooling_1_15.py`, then the five package validators and catalog check after bootstrap/projection. | Each enabled unreachable lint/format caller emits exactly one warning with correct path/cause/remedy; reachable/empty/disabled controls stay silent; drift errors persist; 1.15 is complete/unadvertised and 1.14 exact. | Set only one ownership consumer-owned; disable one tool; use self-hosted/managed modes; empty labels; inject managed-byte drift; mutate a 1.14 byte or activate 1.15. | local bootstrapped candidate runtime | ephemeral |
| PV-T2-001 | REQ-001, REQ-002, REQ-004 | T2 | provider-manifest and V2 package contract | planner verify-request selection; existing input/findings schemas; released 1.10 digest/bytes/modes | Run `tests/package_contract/test_markdown_frontmatter_1_11.py`, T1 regression, and the five package validators after bootstrap/projection. | 1.11 declares one config-only verify request; consumer-owned/self-hosted labels warn once; managed/empty cases stay silent; all former providers match; 1.11 is complete/unadvertised and 1.10 exact. | Remove the provider declaration; emit from document validate instead; pass empty labels; use managed mode; alter schema shape/default; mutate 1.10 or activate 1.11. | local bootstrapped candidate runtime | ephemeral |
| PV-T3-001 | REQ-001, REQ-002, REQ-005 | T3 | serialized provider/package compatibility contract | EG-002 candidate digest and #62 PV-T3-001; released 1.8 digest/bytes/modes; existing schemas | Run the updated `tests/package_contract/test_project_spec_1_9.py`, all #62 T1–T3 focused tests/proofs, T1/T2 regressions, and five package validators. | 1.9 adds exactly the reachability verify contract; silent controls pass; conformance codes/checks/output and exact-selected profiles remain unchanged; 1.8 exact; 1.9 complete/unadvertised. | Remove conformance `checks`; alter warning/strict behavior; emit advisory from lint; pass empty/managed labels; mutate 1.8; create 1.10 or activate 1.9. | local bootstrapped source and candidate runtime after EG-002 | ephemeral |
| PV-T4-001 | REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006 | T4 | exact-selected control-plane plan/apply integration plus full repository qualification | real verification-request generation and executor warning/error contract; all three package proofs; unchanged catalog/self-host state | Run `tests/package_contract/test_runner_label_advisory.py` plus the three successor contracts; five package validators; Markdown/Ruff; remote BasedPyright; direct-local full gate; validate plan/checkpoint. | Exact warning counts, identities, paths, causes, remedies, order, and warning-only success match the matrix; no-warning controls stay empty; injected error fails; all candidates/proofs remain green/unadvertised; T4 checkpoint validates for EG-003. | Duplicate a provider/warning; omit one package; mix MT caller ownership/enabled state; empty/managed labels; inject an existing error; advance a catalog/self-host selection; break a checkpoint trailer. | local Git-aware source/candidate runtime; BasedPyright via rexec only | ephemeral |

## Appendix C. Durable Evidence

No separate evidence record is required: committed package/integration contracts and validated identity-bearing task checkpoints make every acceptance result inexpensive and reproducible.

## Appendix D. Deferred Work

| Item | Reason Deferred | Follow-up / Reopen Trigger |
| --- | --- | --- |
| Catalog 5/self-host activation and family-root documentation | This plan must leave all candidates unadvertised; #62 T4 owns the coordinated Project Specification activation boundary and parent release work owns the companion defaults. | Begin only after EG-003 and the owning activation/release prechecks pass. |
| Release publication, hosted CI, assets, and issue #143 closure | The plan ends at a local verified checkpoint and grants no release/GitHub authority. | Parent 5.19 release workflow explicitly authorizes and verifies publication. |
