---
plan_format: 3
title: 'Project Specification Conformance Linting Implementation Plan'
slug: 'project-spec-conformance'
status: active
revision: 3
revises_revision: 2
revision_reason: 'add the exact stale 1.9 activation assertion claim and defer repository-wide gates to final integrated release readiness'
pause_reason: ''
source: 'approved #62 design, issue acceptance, and current repository evidence'
spec_ref: 'docs/specs/2026-08-01-project-spec-conformance-plan-input.md'
created: 2026-08-10
updated: 2026-08-11
owners:
  - 'Chris Purcell / L3DigitalNet'
  - 'Coding agents under human review'
---

# Project Specification Conformance Linting Implementation Plan

> **Definition, not state.** Authoring drafts live in `.project-pipeline/2026-08-01-project-spec-conformance/authoring/`; generated execution status and evidence pointers live in `.project-pipeline/2026-08-01-project-spec-conformance/execution/`.

## 1. Objective

Ship a Project Specification 1.9 candidate whose selected `spec lint` path reports exact shared-boilerplate drift and noncanonical requirement phrasing without changing Project Specification 1.8 or legacy behavior. Ordinary lint remains advisory, strict lint enforces the warnings, and clean human and JSON output prove that both successor checks ran. This child plan stops at a fully verified repository candidate; parent task T25 retains publication, release evidence, and issue closure.

## 2. Authority and Source Map

| Source | Source Role | Authority / Use | Version / Date | Affected Plan Surface |
| --- | --- | --- | --- | --- |
| `spec:docs/specs/2026-08-01-project-spec-conformance-plan-input.md#selected-design` | decision | Exact checked surfaces, diagnostic families, tailoring boundary, and clean-run output | approved 2026-08-10 | §§1, 3–7; T1–T3 |
| `spec:docs/specs/2026-08-01-project-spec-conformance-plan-input.md#migration-and-compatibility` | decision | Successor-only activation, warning/strict rollout, additive JSON, and immutable predecessor | approved 2026-08-10 | §§3–7, 10; T2–T3 |
| `issue:L3DigitalNet/project-standards#62` | normative | User-visible problem, negative corpus, and acceptance criteria | verified 2026-08-10 | §§1, 3, 6–7; T1–T3 |
| `repo:src/project_standards/specs/commands/lint.py::lint_document` | current-state evidence | Shared lint engine and warning findings | `4c6d2b7e` | §4–5; T1 |
| `repo:src/project_standards/specs/registry.py::registry_from_templates` | current-state evidence | Version-selected template registry construction | `4c6d2b7e` | §4–5; T1 |
| `repo:src/project_standards/specs/cli.py::_run_setwide` | current-state evidence | Human/JSON projection and established strict exit behavior | `4c6d2b7e` | §4–5; T2 |
| `repo:standards/project-spec/versions/1.8/providers/project_spec.py::run_lint` | current-state evidence | Selected provider, payload-template authority, and findings result | Project Specification 1.8 | §4–5; T3 |
| `repo:standards/project-spec/standard.toml` | current-state evidence | Immutable version index and successor digest owner | `4c6d2b7e` | §4–5; T3 |
| `repo:catalogs/5.toml` | current-state evidence | Catalog 5 selection and retained/default roles | `4c6d2b7e` | §4–5; T3 |
| `repo:standards/catalog.md` | current-state evidence | Generated family-version inventory and advertised/unadvertised role projection | `4c6d2b7e` | §§4–5; T3, T5 |
| `repo:.standards/config.toml` | current-state evidence | Self-host selection and exact Project Specification dogfood corpus | `4c6d2b7e` | §§3–5, 10; T5 |
| `repo:tests/package_contract/test_project_spec_1_8.py::test_project_spec_1_8__successor__preserves_1_7_and_indexes_complete_payload` | current-state evidence | Predecessor-byte, package, projection, catalog, and navigation oracle pattern | `4c6d2b7e` | §§4, 7; T3 |
| `repo:tests/package_contract/test_project_spec_1_9.py::test_project_spec_1_9__projection_and_unadvertised_catalog_role_are_exact` | current-state evidence | T3 projection/integrity oracle whose activation-only tail still asserts 1.8 default, no 1.9 Catalog role, an unadvertised generated row, and a 1.8 self-host lock. T5 must update only those stale activation assertions while freezing every projection and non-activation byte. | T1–T3 checkpoint base `095aec56`; blocked T4 receipt 2026-08-11 | §§3–7, 9–12; T5 |
| `repo:ROADMAP.md` | decision | #143 remains a same-train companion but does not alter #62 behavior | 2026-08-10 | §§3, 10; T3 |
| `issue:L3DigitalNet/project-standards#143` | normative | Prior same-train advisory and Project Specification 1.9 collision boundary | verified 2026-08-10 | §§3, 5, 10; T5 |
| `repo:docs/plans/2026-08-10-schema-payload-reference-validation-plan.md#t2-document-the-successor-cut-guard-and-verify-the-repository` | decision | #156 must supply its verified graph/corpus checkpoint before T3 creates any successor payload byte. | revision 1, 2026-08-10 | §§3, 6–10; T3 |
| `request` | normative | Add only the stale Project Specification 1.9 activation-test claim to the bridge-valid replacement and run repository-wide fast/full gates once at final integrated release readiness, not per task. T5 retains targeted focused/package/source/candidate/installed/semantic proof; the release coordinator owns the final full gate and hosted CI. | 2026-08-11 | §§3, 7, 9–13; T5 and release boundary |

Conflict precedence: the approved design and issue acceptance define #62 behavior; repository code defines only the starting state. The roadmap coordinates a #143 edit after T3 composition and before T4 activation, but that edit cannot weaken or replace this plan's conformance contract.

## 3. Scope, Boundaries, and Constraints

### 3.1 In Scope

- An internal, provider-activated conformance mode in the shared lint engine that compares only the approved profile-specific canonical surfaces.
- `SL-BOILERPLATE` and `SL-REQUIREMENT-PHRASING` warning findings with the approved `locus` and physical `line` semantics.
- Optional provider coverage metadata that the selected CLI projects as clean human check names and the successor-only JSON `checks` array.
- A complete Project Specification 1.9 payload candidate, selected projection, family/catalog activation, adoption guidance, tooling notes, and package contracts.
- Activation and conformance repair of the repository's explicitly selected Project Specification dogfood corpus, with semantic preservation and revision-history updates.
- The named 1.9 package-contract node's activation-only assertions: Catalog 1.9 default with 1.8 retained, generated 1.9 default/current role instead of unadvertised, and self-host lock resolution to 1.9, while its projection/integrity assertions remain exact.
- Canonical, divergent, legitimately tailored, predecessor, source, candidate-wheel, and installed-wheel acceptance.

### 3.2 Out of Scope and Deferred

- Validation errors, severity/configuration frameworks, opt-ins, waivers, suppressions, fuzzy matching, automatic repair, or a new parser.
- Editing any Project Specification 1.8 payload byte or changing its human, JSON, finding, or exit behavior.
- Implementing the separate #143 advisory. Its verified Project Specification provider checkpoint and cross-package readiness are external preconditions to T5 activation; its edit must preserve and rerun this plan's candidate proof.
- Repairing specifications outside `.standards/config.toml`'s selected Project Specification corpus.
- Publishing a Project Standards release, creating tags/assets, pushing branches, or closing #62; parent task T25 owns those action-specific effects and `EV-009`.

### 3.3 Ownership and Preserved Behavior

| Boundary | Owner / Responsibility |
| --- | --- |
| Plan owns | #62 lint engine, optional coverage metadata projection, Project Specification 1.9 conformance behavior, selected dogfood repair, documentation, tests, and local release-candidate proof |
| Depends on | Approved T24 design, selected payload template resources, existing findings effect, repository package validators, #156 T2/PV-T2-001 before T3 payload writes, and parent T25 publication authority |
| Does not own | #143's cross-package advisory, non-dogfood consumer document repair, release publication, hosted issue mutation, or new lint policy/configuration |
| Must preserve | Every 1.8 payload byte and behavior; every non-activation byte/assertion in `test_project_spec_1_9__projection_and_unadvertised_catalog_role_are_exact`; legacy no-payload output; existing warning/strict exits; selected-spec meaning and lifecycle history; unrelated authored prose; immutable released history |

### 3.4 Constraints and Authorization

- Conformance is internally activated by the successor provider, not by consumer configuration. The shared engine defaults to current behavior so legacy and 1.8 callers remain unchanged.
- Lifecycle and Quality compare exact canonical text. Appendix A, B, and D are structurally isolated first and then compared exactly with the selected profile template.
- Every recognized FR, NFR, IR, and DR requirement row checks its `Requirement` cell, regardless of an optional Priority column, for the exact `The system shall` prefix.
- The CLI adds check coverage only when the selected provider returns the successor contract. Absence preserves the predecessor JSON key set and clean human format.
- Dogfood remediation changes only reported canonical surfaces and requirement cells, preserves each requirement's intent/acceptance/priority, and records a revision row in every changed approved or archived specification.
- T3 cannot create Project Specification 1.9 until #156 is terminal at a commit carrying `Plan-Id: 2026-08-10/schema-payload-reference-validation`, `Plan-Task: T2`, `Plan-Status: done`, and `Plan-Proofs: PV-T2-001`, and that graph/corpus proof reruns green.
- T5 cannot complete activation until the separately governed #143 work has supplied a verified Project Specification provider checkpoint and cross-package release-ready status. Absence blocks T5 without weakening or publishing the #62 candidate.
- CPU-intensive gates follow repository rexec policy except commands whose Git-history dependency requires direct local execution. Publication and GitHub issue mutation require parent T25's explicit action authorization.
- Repository-wide fast/full gates do not run per task. T5 uses targeted T1–T5 focused tests, five package checks, strict source/candidate/installed lint and validate, scoped documentation/diff checks, reconcile convergence, and semantic proof. The final integrated release coordinator runs the one repository-wide full gate and hosted CI.

## 4. Current State and Target State

### 4.1 Current State

`lint_document` emits structural, placeholder, guidance, traceability, and Definition-of-Done warnings from a registry derived from selected templates. Selected Project Specification providers call the same engine and return a schema-validated findings object. The CLI reduces that result to per-document findings, prints plain `OK` for a clean document, emits JSON objects with exactly `file`, `ok`, and `findings`, and returns 1 for lint warnings only under `--strict`. Project Specification 1.8 documents that shared prose is not machine-checked.

The provider result already retains schema-validated `structured_output`, so successor metadata can travel through the existing invocation boundary without changing the control-plane finding model. Catalog 5 selects Project Specification 1.8, and its package contract pins predecessor bytes, payload integrity, projection, navigation, and catalog role. The self-host config currently selects 10 Project Specification documents; a source scan found 605 recognized requirement rows, 575 of which lack the approved exact prefix across 9 files. Those counts orient remediation but do not replace successor lint findings as the task oracle.

The preserved T4 candidate on checkpoint base `095aec56` has exactly 16 claimed paths and no unclaimed edit or gate. Its correct RED recorded 406 findings across 9 selected documents: 366 requirement rows and 40 canonical surfaces. After the claimed repairs, strict source, candidate, and validate routes each report zero findings; reconcile advances 1.8 to 1.9 and a second run is a no-op; the unrelated GitHub Workflow 1.2 candidate remains unadvertised. Activation is bridge-blocked only because the T3-owned package-contract node retains four stale activation expectations.

### 4.2 Target State

The shared engine can run the two approved checks only when an internal caller requests them. Project Specification 1.9 requests them from its version-selected templates and returns the exact coverage names alongside findings. The selected CLI projects those names in clean human output and as `checks: ["shared-boilerplate", "mandatory-phrasing"]` in each successor JSON document result. Divergence remains a warning in ordinary lint and becomes exit 1 through the unchanged strict boundary.

Project Specification 1.9 is first composed as a complete unadvertised candidate, then activated as the Catalog 5 default only in the same checkpoint that repairs the selected dogfood corpus and reconciles self-host state. Project Specification 1.8 remains retained, byte-identical, selectable, and behaviorally unchanged. Legacy/no-payload execution and providers that omit coverage metadata retain their exact output shape.

### 4.3 Delta Summary

| Area | Current | Target | Must Preserve |
| --- | --- | --- | --- |
| Lint engine | Structural/authoring warnings only | Optional exact boilerplate and requirement-phrase warnings | Default-off legacy and predecessor behavior |
| Selected provider | Returns findings only | 1.9 activates conformance and declares two checks | 1.8 provider bytes and schema |
| Human/JSON CLI | Clean `OK`; JSON has three keys | 1.9 clean output names checks; JSON adds `checks` | Existing shape when metadata is absent |
| Package | 1.8 default | Complete 1.9 candidate, then atomic catalog/self-host activation | All predecessors retained and immutable |
| Documentation | Successor docs disclose no checks; 9 selected specs contain 575 noncanonical rows | 1.9 docs name checks and the selected dogfood corpus is strict-clean | Preserve requirement meaning, acceptance, priority, and revision history |
| Activation contract | The 1.9 projection test still expects 1.8 default/lock and 1.9 absent/unadvertised. | Preserve projection assertions; expect 1.9 default/current/selected with 1.8 retained. | Every non-activation assertion and predecessor/package invariant. |

## 5. Change Surface and Architecture

### 5.1 Components and Ownership

| Component / Surface | Current Responsibility | Planned Responsibility | Paths / Contracts | Owning Task |
| --- | --- | --- | --- | --- |
| Conformance engine | General lint warnings from parsed document/registry | Default-off exact surface and requirement-row checks | `conformance-lint-v1` | T1 |
| CLI projection | Findings-only human/JSON rendering | Preserve absent metadata; project declared check coverage | `spec-lint-coverage-v1` | T2 |
| Project Specification provider | 1.8 selected findings over payload templates | 1.9 activates both checks and returns coverage metadata | `project-spec-1.9-lint-v1` | T3 |
| Package candidate | 1.8 family default and projection | Complete unadvertised 1.9 candidate with 1.8 retained | V2 family/payload/projection contracts | T3 |
| Catalog/self-host activation | Catalog and self-host resolve 1.8 | Catalog and self-host resolve 1.9 only with a strict-clean selected corpus | `project-spec-1.9-dogfood-v1` | T5 |
| Package activation oracle | T3 test proves projection plus unadvertised candidate role. | Keep projection proof exact; advance only the named node's Catalog/generated/lock assertions with T5 activation. | `tests/package_contract/test_project_spec_1_9.py::test_project_spec_1_9__projection_and_unadvertised_catalog_role_are_exact` | T5 contributor; owner T3 |
| Documentation | Successor docs disclose unverified prose; selected specs carry divergent phrasing | Define checked surfaces/repair and remediate only successor-reported selected loci | 1.9 docs plus selected `.standards/config.toml` corpus | T3, T5 |

### 5.2 Control Flow

The selected 1.9 provider builds its registry from its own immutable template resources, calls the shared lint engine with the internal conformance mode enabled, and returns findings plus the two fixed check names under its successor output schema. The CLI reads schema-validated `structured_output`; it attaches the names to each document result and clean human line only when present. A 1.8 or legacy call never activates the mode and never supplies the metadata, so its output path is unchanged. The 1.9 candidate is proven by exact selection before Catalog 5 activation; activation and selected-corpus repair form one later checkpoint so the repository never claims a default it cannot pass under strict lint.

### 5.3 Change-Surface Matrix

| Surface | Applies? | Invariant / Required Change | Proof | Task |
| --- | --- | --- | --- | --- |
| Behavior | yes | Exact successor warnings and clean-run coverage | PV-T1-001, PV-T3-001 | T1, T3 |
| Architecture / dependency direction | yes | Payload selects policy; shared engine remains version-neutral/default-off | PV-T1-001, PV-T3-001 | T1, T3 |
| Public / cross-task interface | yes | Optional fixed `checks` metadata crosses provider-to-CLI boundary | PV-T2-001, PV-T3-001 | T2, T3 |
| Data / state | no | No persistent state or migration | PV-T3-001 | T3 |
| Configuration | yes | No new option; Catalog/self-host resolution advances only with corpus convergence | PV-T5-001 | T5 |
| Security / trust | yes | Untrusted document text is parsed and compared without execution or path expansion | PV-T1-001 | T1 |
| Compatibility / migration | yes | 1.8 bytes/behavior and absent-metadata output remain exact; selected specs preserve meaning through repair | PV-T2-001, PV-T3-001, PV-T5-001 | T2, T3, T5 |
| Operations / deployment | no | Publication is outside this child plan | PV-T3-001 | T3 |
| Documentation | yes | 1.9 owner truth matches behavior and selected specs become strict-clean without semantic drift | PV-T3-001, PV-T5-001 | T3, T5 |
| Test activation state | yes | One T3-owned package-contract node advances only its Catalog/generated/lock expectations; projection and non-activation assertions remain byte-exact. | PV-T5-001 | T5 |
| Durable evidence | no | Repeatable committed tests and package contracts suffice; T25 owns EV-009 | PV-T3-001 | T3 |

### 5.4 Binding Decisions

| ID | Decision | Rationale | Source | Affected Task(s) |
| --- | --- | --- | --- | --- |
| D-001 | Conformance activation is an internal successor-provider choice; the shared engine defaults off. | This is the narrow seam that preserves 1.8 and legacy behavior without a consumer-facing mode. | approved design, successor-only boundary | T1, T3 |
| D-002 | Coverage metadata is optional at the provider boundary and projected only when returned. | The successor gains observable clean coverage while predecessor JSON and human bytes remain unchanged. | approved D3 and existing `structured_output` | T2, T3 |
| D-003 | Canonical matching is exact and profile-selected; no waiver or fuzzy path exists. | The checked surfaces are documented interchangeability guarantees, not tailoring points. | approved D2 | T1, T3 |
| D-004 | #143 modifies the unreleased 1.9 candidate between T3 composition and activation, and must preserve/rerun #62 proof; it is not implemented here. | The current roadmap orders the same-train companion before #62 publication and requires one Project Specification cut. | approved design release boundary, issue #143, and `ROADMAP.md` | T3, T5 |
| D-005 | Compose 1.9 before advertising it; activate Catalog 5 and self-host only with selected-corpus remediation. | The repository is itself a strict consumer, so advertising first would create a knowingly red owner state. | `.standards/config.toml` and selected-corpus inventory | T3, T5 |
| D-006 | Supersede blocked T4 and let T5 correct only the activation assertions in the existing 1.9 projection/unadvertised-role node; repository-wide gates run once at final integrated release readiness rather than inside the replacement task. | Bridge 3.5 freezes blocked-task acceptance, while the same node owns both immutable projection and lifecycle state. The projection half is already green and only role/lock assertions must advance atomically. Targeted proof covers the changed surface without repeating broad gates. | blocked T4 receipt; request; bridge 3.5; repository proportional-verification policy | T4–T5; final release coordinator |

## 6. Requirements and Acceptance

| ID | Requirement | Source | Priority | Owner Task | Task(s) | Proof(s) |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-001 | The internal conformance engine shall report `SL-BOILERPLATE` for exact Lifecycle/Quality or profile-specific Appendix A/B/D drift, with the canonical surface in `locus`. | approved selected design | Must | T1 | T1, T3 | PV-T1-001, PV-T3-001 |
| REQ-002 | The engine shall report `SL-REQUIREMENT-PHRASING` for every recognized requirement row whose Requirement cell does not start with `The system shall`, with requirement ID in `locus` and its physical row in `line`. | approved selected design and #62 corpus | Must | T1 | T1, T3 | PV-T1-001, PV-T3-001 |
| REQ-003 | The CLI shall project optional successor check coverage to clean human output and an additive per-document JSON `checks` array while preserving exact output when metadata is absent. | approved D3 and compatibility decision | Must | T2 | T2, T3 | PV-T2-001, PV-T3-001 |
| REQ-004 | Project Specification 1.9 shall activate both warning families; ordinary lint remains exit 0 with warnings and strict lint returns 1 for either family. | approved D1 and issue acceptance | Must | T3 | T3 | PV-T3-001 |
| REQ-005 | Successor documentation shall name all checked surfaces, exact repair guidance, strict-mode impact, additive JSON compatibility, and the remaining semantic-review boundary. | approved design downstream impact | Must | T3 | T3 | PV-T3-001 |
| REQ-006 | Project Specification 1.9 shall be a complete selected V2 package candidate while every 1.8 byte and legacy/1.8 lint behavior remains unchanged. | approved compatibility decision and package contract | Must | T3 | T2, T3 | PV-T2-001, PV-T3-001 |
| REQ-007 | After the verified #143 prerequisite, Catalog/self-host activation shall leave every explicitly selected dogfood specification clean under successor strict lint while preserving its requirement meaning, acceptance, priority, and revision history. | repository dogfood policy, roadmap order, and approved migration impact | Must | T5 | T5 | PV-T5-001 |
| REQ-008 | No Project Specification 1.9 payload byte shall be created until #156 T2/PV-T2-001 is terminal, identity-matched, and green under its graph/corpus acceptance. | #156 plan and release coordination | Must | T3 | T3 | PV-T3-001 |

## 7. Verification and Evidence Strategy

- **Authoritative commands:** T1–T5 focused pytest files, including the named 1.9 activation node; the five package/graph/schema/projection/catalog checks; strict source/candidate/installed `spec lint` and `project-standards validate`; scoped Markdown and `git diff --check`; reconcile apply/no-op; and per-row semantic comparison. Repository-wide fast/full gates are excluded from task execution and run once on the final integrated release tree.
- **Oracles:** immutable profile templates, approved diagnostic/output contract, current 1.8 bytes and package tests, the selected provider's schema-validated structured output, the named 1.9 node's projection/integrity half, exact 1.9 default/current/selected activation state with 1.8 retained, and before/after requirement ID/acceptance/priority plus semantic review of selected-doc repairs.
- **Negative controls:** for each Light, Standard, and Full profile, mutate each canonical surface independently, alter only permitted surrounding prose, and remove the exact requirement prefix; also return no provider metadata, run selected 1.8 and legacy paths, deliberately change a predecessor byte in the proof fixture, retain one stale 1.8 activation assertion, or alter any non-activation assertion in the named 1.9 node.
- **Test layers:** unit parsing/comparison, CLI contract, selected-provider integration, V2 package contract, selected-corpus migration/semantic review, source/candidate/installed routing, package/static checks, activation assertions, and final release-coordinator repository/hosted verification.
- **External environments:** none for child-plan acceptance. The final release coordinator runs the repository-wide full gate locally because repository tests inspect Git metadata that rexec does not synchronize, then owns hosted CI.
- **Evidence:** repeatable T1–T3 output is ephemeral. T5 consumes blocked T4's expensive semantic migration receipt and completes targeted verification as `EV-001`: exact 16 claimed paths; correct RED 406 findings (366 rows and 40 surfaces) across 9 documents; strict source/candidate/validate zero; reconcile 1.8→1.9 then no-op; GitHub Workflow 1.2 still unadvertised; no unclaimed edit or gate. Parent T25 retains the one final full-gate, hosted, artifact, and issue-closure evidence in `EV-009`.
- **Late failure:** block the owning task, append a correction task for a completed checkpoint when necessary, and rerun the failed proof without weakening predecessor or exact-match requirements.

## 8. Execution Summary

| Task | Title | Disposition | Work Type | Phase | Depends On | Requirement(s) | Primary Proof | Parallel / Conflict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T1 | Add default-off conformance checks | active | behavior | P1 | None | REQ-001, REQ-002 | PV-T1-001 | yes / none |
| T2 | Project optional check coverage in the CLI | active | brownfield-behavior | P1 | None | REQ-003, REQ-006 | PV-T2-001 | yes / none |
| T3 | Compose and verify Project Specification 1.9 candidate | active | brownfield-behavior | P2 | T1, T2 | REQ-001–REQ-006, REQ-008 | PV-T3-001 | no / T1, T2 contracts and #156 gate |
| T4 | Activate 1.9 and remediate selected dogfood | superseded | migration | P3 | T3 | None | None | no / historical blocked boundary replaced by T5 |
| T5 | Complete 1.9 activation and targeted dogfood proof | active | migration | P3 | T3 | REQ-007 | PV-T5-001 | no / supersedes T4 and consumes its preserved candidate |

## 9. Implementation Tasks

### Phase P1: Version-Neutral Engine and CLI Contracts

#### T1: Add default-off conformance checks

- **disposition:** active
- **outcome:** The shared lint engine can perform the approved profile-aware exact comparisons and row-phrase checks without changing any caller that does not activate them.
- **work_type:** behavior
- **checkpoint:** one green commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** []
- **dependency_reason:** none
- **requirements:** [REQ-001, REQ-002]
- **proof:** [PV-T1-001]
- **source_refs:** [spec:docs/specs/2026-08-01-project-spec-conformance-plan-input.md#selected-design, issue:L3DigitalNet/project-standards#62, repo:src/project_standards/specs/commands/lint.py::lint_document, repo:src/project_standards/specs/registry.py::registry_from_templates]
- **consumes:** [parsed `SpecDocument`, registry built from a selected profile-template set, internal activation choice]
- **produces:** [conformance-lint-v1]
- **preserves:** [current lint findings and ordering when conformance is not activated, fenced-code masking, absolute line translation, no filesystem or network effects]
- **invariants:** [exact profile-selected comparisons only, one finding per divergent canonical surface or requirement row, no waiver/fuzzy/repair path]
- **executor_discretion:** [private helper names, whether immutable template bodies live on `Registry` or an equivalent internal value, fixture organization, exact diagnostic message wording within approved repair guidance]
- **files:** [`src/project_standards/specs/commands/lint.py` (modify; owner T1), `src/project_standards/specs/registry.py` (modify if needed; owner T1), `src/project_standards/specs/model.py` (modify if needed; owner T1), `tests/test_spec_conformance_lint.py` (create; owner T1)]
- **parallel_safe:** yes
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** revert the task checkpoint if the new mode cannot remain default-off; do not special-case a fixture or broaden a canonical boundary to recover a failing comparison.
- **acceptance:** PV-T1-001 proves, independently for Light, Standard, and Full, that each applicable canonical-surface mutation and noncanonical requirement row produces the exact code/locus/line, sanctioned surrounding tailoring remains clean, and the unactivated engine reproduces its pre-task result.
- **sub-tasks:**
  - **T1.1 RED** — add canonical, five-surface divergent, row-phrase, tailored-surrounding, fence, and unactivated compatibility cases; expected failures are missing conformance findings and API activation, not import/fixture errors.
  - **T1.2 Verify RED** — run `PYTHONPATH="$PWD/build/wheel-runtime" uv run pytest tests/test_spec_conformance_lint.py` and confirm only the absent target behavior fails.
  - **T1.3 GREEN** — add the minimum internal activation and exact comparison logic using the existing parser, structural slices, registry, and finding model.
  - **T1.4 Verify GREEN** — rerun `scripts/bootstrap-worktree.sh`, the focused file, and adjacent `tests/test_spec_lint.py` coverage.
  - **T1.5 REFACTOR** — remove duplicated parsing/slicing while retaining one canonical template authority; keep proof green.
  - **T1.6 Verify Task** — run PV-T1-001, Ruff, BasedPyright, `git diff --check`, and the intermediate fast gate; create the required checkpoint.

#### T2: Project optional check coverage in the CLI

- **disposition:** active
- **outcome:** The CLI preserves current output for legacy and predecessor providers while projecting a provider-declared two-check coverage contract to successor clean human and JSON results.
- **work_type:** brownfield-behavior
- **checkpoint:** one green commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** []
- **dependency_reason:** none
- **requirements:** [REQ-003, REQ-006]
- **proof:** [PV-T2-001]
- **source_refs:** [spec:docs/specs/2026-08-01-project-spec-conformance-plan-input.md#migration-and-compatibility, repo:src/project_standards/specs/cli.py::_run_setwide, repo:standards/project-spec/versions/1.8/providers/project_spec.py::run_lint]
- **consumes:** [schema-validated provider `structured_output` with optional fixed check-name array]
- **produces:** [spec-lint-coverage-v1]
- **preserves:** [legacy and 1.8 JSON key sets, existing finding payload, warning/strict exit taxonomy, validate behavior, selected path grouping]
- **invariants:** [CLI never infers coverage from package version or empty findings; only provider-declared validated metadata may produce `checks`]
- **executor_discretion:** [exact clean human punctuation/layout, private transport type, test double organization]
- **files:** [`src/project_standards/specs/cli.py` (modify; owner T2), `tests/test_spec_conformance_cli.py` (create; owner T2)]
- **parallel_safe:** yes
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** revert the task checkpoint if optional metadata cannot traverse without predecessor drift; do not hardcode 1.9 or add the field unconditionally.
- **acceptance:** PV-T2-001 proves a declared successor result names both checks in clean human output and the exact JSON array, while absent metadata reproduces the three-key JSON object and prior clean human line byte-for-byte.
- **sub-tasks:**
  - **T2.1 CHARACTERIZE** — freeze legacy and selected-1.8 clean human/JSON output plus current strict exits.
  - **T2.2 Verify Baseline** — run the characterization against `4c6d2b7e` behavior.
  - **T2.3 RED** — inject a schema-shaped provider result with the approved checks; expected failure is the missing coverage projection.
  - **T2.4 Verify RED** — run `PYTHONPATH="$PWD/build/wheel-runtime" uv run pytest tests/test_spec_conformance_cli.py` and confirm the correct missing field/name failure.
  - **T2.5 GREEN** — carry optional provider coverage through selected result grouping and render it only when declared.
  - **T2.6 Verify GREEN** — rerun bootstrap, the focused file, and adjacent `tests/test_spec_cli.py` and `tests/test_spec_selected_routing.py` coverage.
  - **T2.7 REFACTOR** — keep the optional contract localized and preserve validator output paths.
  - **T2.8 Verify Task** — run PV-T2-001, Ruff, BasedPyright, `git diff --check`, and the intermediate fast gate; create the required checkpoint.

### Phase P2: Successor Payload and Integrated Candidate

#### T3: Compose and verify Project Specification 1.9 candidate

- **disposition:** active
- **outcome:** Project Specification 1.9 is a complete exact-selectable candidate with the generated catalog's required `unadvertised` row but no Catalog 5 selection; it activates and documents #62 while 1.8/default behavior remains exact and the candidate remains safe for the required pre-activation #143 extension.
- **work_type:** brownfield-behavior
- **checkpoint:** one green commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** public
- **depends_on:** [T1, T2]
- **dependency_reason:** consumes `conformance-lint-v1` from T1 and `spec-lint-coverage-v1` from T2; external #156 T2/PV-T2-001 must be terminal and green before any payload write
- **requirements:** [REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-008]
- **proof:** [PV-T3-001]
- **source_refs:** [spec:docs/specs/2026-08-01-project-spec-conformance-plan-input.md#selected-design, spec:docs/specs/2026-08-01-project-spec-conformance-plan-input.md#migration-and-compatibility, issue:L3DigitalNet/project-standards#62, repo:docs/plans/2026-08-10-schema-payload-reference-validation-plan.md#t2-document-the-successor-cut-guard-and-verify-the-repository, repo:standards/project-spec/versions/1.8/providers/project_spec.py::run_lint, repo:standards/project-spec/standard.toml, repo:catalogs/5.toml, repo:tests/package_contract/test_project_spec_1_8.py::test_project_spec_1_8__successor__preserves_1_7_and_indexes_complete_payload, repo:ROADMAP.md]
- **consumes:** [validated #156 T2/PV-T2-001 checkpoint, conformance-lint-v1, spec-lint-coverage-v1, complete immutable 1.8 payload, Catalog 5/V2 family/projection contracts]
- **produces:** [project-spec-1.9-lint-v1, complete unadvertised Project Specification 1.9 payload candidate, exact-selected source/candidate acceptance]
- **preserves:** [every 1.8 byte and behavior, every older selectable version, 1.8 Catalog/self-host default, unrelated config/lock/catalog entries, current managed workflow behavior, #143 extension seam]
- **invariants:** [provider uses its own template resources, findings stay warnings, ordinary/strict exits stay 0/1, output schema fixes the two check names, package digest and projection match authored bytes]
- **executor_discretion:** [diagnostic sentence wording, fixture filenames, mechanical payload-copy technique, organization of focused selected-routing tests]
- **files:** [`standards/project-spec/versions/1.9/` (create; owner T3), `standards/project-spec/standard.toml` (modify; owner T3), `standards/catalog.md` (modify through render-catalog to add the unadvertised 1.9 row; owner T3), `src/project_standards/payloads/project-spec/1.9/` (create; owner T3), `tests/package_contract/test_project_spec_1_9.py` (create; owner T3), `tests/test_spec_selected_conformance.py` (create; owner T3)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** revert or forward-fix only the unreleased 1.9 candidate, its family/projection identity, and its generated unadvertised catalog row; never edit 1.8 or advance Catalog 5/self-host selection. The pre-activation #143 edit must rerun PV-T3-001.
- **acceptance:** PV-T3-001 proves exact-selected Light, Standard, and Full 1.9 canonical and legitimately tailored documents are clean with explicit check coverage; per-profile divergent surfaces/rows warn and strict-exit 1; all 1.8 bytes and outputs remain exact; payload integrity, family index, projection, successor docs, generated catalog freshness, and focused source/candidate checks pass while Catalog 5/self-host still select 1.8 and the 1.9 row remains unadvertised.
- **sub-tasks:**
  - **T3.1 CHARACTERIZE** — validate the exact #156 T2/PV-T2-001 checkpoint and rerun its graph/corpus acceptance before writes; then capture the 1.8 aggregate digest, file bytes/modes, selected clean/divergent output, family navigation, catalog role, and reconcile projection.
  - **T3.2 Verify Baseline** — run the 1.8 package contract and selected-routing baseline before creating 1.9.
  - **T3.3 RED** — add the 1.9 package/output schemas and package/selected tests first; expected failures are the absent 1.9 payload and provider activation.
  - **T3.4 Verify RED** — run focused package and selected tests and confirm the missing successor behavior, not fixture/import failure.
  - **T3.5 GREEN** — copy 1.8 to 1.9, change only successor-owned behavior/identity/docs/schemas, compute its digest, update the family index and source projection, and render its required `unadvertised` row without selecting it in Catalog 5.
  - **T3.6 Verify GREEN** — rerun bootstrap; focused T1–T3 tests; 1.8 and 1.9 package contracts; exact-selected routing; and all five package/graph/schema/projection/catalog checks against the unadvertised candidate.
  - **T3.7 REFACTOR** — audit provider/core duplication, package comments, tooling claims, and predecessor references without broadening the behavior.
  - **T3.8 Verify Task** — run PV-T3-001, candidate-wheel exact-selection checks, Markdown checks, `git diff --check`, and the intermediate fast gate; create the required checkpoint.

### Phase P3: Catalog Activation and Dogfood Migration

#### T4: Activate 1.9 and remediate selected dogfood

- **disposition:** superseded
- **outcome:** Catalog 5 and the repository self-host resolve Project Specification 1.9, and every explicitly selected specification is strict-clean without changing its requirement intent, acceptance, priority, or lifecycle history.
- **work_type:** migration
- **checkpoint:** one green commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** state
- **depends_on:** [T3]
- **dependency_reason:** consumes project-spec-1.9-lint-v1 and the complete unadvertised Project Specification 1.9 payload candidate from T3
- **requirements:** []
- **proof:** []
- **source_refs:** [spec:docs/specs/2026-08-01-project-spec-conformance-plan-input.md#migration-and-compatibility, issue:L3DigitalNet/project-standards#62, issue:L3DigitalNet/project-standards#143, repo:.standards/config.toml, repo:catalogs/5.toml, repo:ROADMAP.md]
- **consumes:** [project-spec-1.9-lint-v1, complete unadvertised Project Specification 1.9 payload candidate, verified #143 Project Specification provider checkpoint and cross-package release-ready status, exact selected-corpus snapshot from `.standards/config.toml`]
- **produces:** [project-spec-1.9-dogfood-v1, Catalog/self-host activation, strict-clean selected corpus, integrated source/candidate/installed acceptance]
- **preserves:** [each requirement ID/intent/rationale/acceptance/priority, non-reported authored prose, approved/superseded lifecycle meaning, all predecessor bytes, unrelated catalog/config/lock content]
- **invariants:** [#143 prerequisite verified before activation, inventory before writes, only successor-reported loci change, every changed approved/archived spec receives a revision row, reconcile is candidate-runtime-owned and convergent]
- **executor_discretion:** [per-file work allocation under one T4 aggregator, sentence grammar after the exact prefix, revision-row wording, order of independent document repairs]
- **files:** [`catalogs/5.toml` (modify; owner T4), `standards/catalog.md` (serialized contribution through render-catalog from T3's unadvertised row to the activated role; owner T3), `standards/project-spec/README.md` (modify; owner T4), `standards/project-spec/adopt.md` (modify; owner T4), `standards/project-spec/agent-summary.md` (modify; owner T4), `.standards/catalog.toml` (modify through reconcile; owner T4), `.standards/lock.toml` (modify through reconcile; owner T4), `standards/project-spec/examples/spec.example.md` (modify only if reported; owner T4), `docs/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md` (modify only if reported; owner T4), `docs/specs/2026-07-07-project-standards-mcp-enablement-roadmap-spec.md` (modify only if reported; owner T4), `docs/specs/2026-07-07-project-standards-mcp-server-implementation-spec.md` (modify only if reported; owner T4), `docs/specs/archive/2026-07-07-standard-bundle-authoring-standard.md` (modify only if reported; owner T4), `docs/specs/2026-07-10-standard-bundle-authoring-v2-spec.md` (modify only if reported; owner T4), `docs/specs/2026-07-09-agent-handoff-standard-package.md` (modify only if reported; owner T4), `docs/specs/2026-07-10-consumer-standards-control-plane-spec.md` (modify only if reported; owner T4), `docs/specs/2026-07-26-v5-adoption-integrity-correction-train-spec.md` (modify only if reported; owner T4), `docs/specs/2026-07-27-v5-validation-fidelity-correction-train-spec.md` (modify only if reported; owner T4), `tests/package_contract/test_project_spec_1_9_activation.py` (create; owner T4), `docs/research/2026-08-01-project-spec-conformance-dogfood-evidence.md` (create; owner T4)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** [T5]
- **evidence:** []
- **recovery:** not executable; T5 consumes the preserved blocked candidate and owns recovery without repeating already-green work
- **acceptance:** historical blocked activation boundary only; T5 owns the replacement acceptance and targeted completion proof

#### T5: Complete 1.9 activation and targeted dogfood proof

- **disposition:** active
- **outcome:** Catalog 5 and the repository self-host resolve Project Specification 1.9, and every explicitly selected specification is strict-clean without changing its requirement intent, acceptance, priority, or lifecycle history.
- **work_type:** migration
- **checkpoint:** one green replacement activation commit with task, requirement, proof IDs, supersession provenance, and the required `Plan-*` checkpoint trailers
- **boundary:** state
- **depends_on:** [T3]
- **dependency_reason:** supersedes blocked T4 after T3 and consumes its exact 16-path preserved candidate, correct-reason migration evidence, and already-green strict/reconcile results without repeating completed implementation
- **requirements:** [REQ-007]
- **proof:** [PV-T5-001]
- **source_refs:** [request, spec:docs/specs/2026-08-01-project-spec-conformance-plan-input.md#migration-and-compatibility, issue:L3DigitalNet/project-standards#62, issue:L3DigitalNet/project-standards#143, repo:.standards/config.toml, repo:catalogs/5.toml, repo:ROADMAP.md, repo:tests/package_contract/test_project_spec_1_9.py::test_project_spec_1_9__projection_and_unadvertised_catalog_role_are_exact]
- **consumes:** [project-spec-1.9-lint-v1, complete unadvertised Project Specification 1.9 payload candidate, verified #143 Project Specification provider checkpoint and cross-package release-ready status, exact selected-corpus snapshot from `.standards/config.toml`, preserved T4 16-path candidate and 406-finding migration receipt]
- **produces:** [project-spec-1.9-dogfood-v1, project-spec-1.9-activation-test-v1, Catalog/self-host activation, strict-clean selected corpus, integrated targeted source/candidate/installed acceptance]
- **preserves:** [each requirement ID/intent/rationale/acceptance/priority, non-reported authored prose, approved/superseded lifecycle meaning, all predecessor bytes, unrelated catalog/config/lock content, every projection/integrity and other non-activation assertion/byte in the named 1.9 package-contract node, GitHub Workflow 1.2 unadvertised role, exact 16-path candidate outside the newly claimed test correction]
- **invariants:** [#143 prerequisite remains verified, exact T4 inventory/evidence before continuation, only successor-reported loci plus the named stale activation assertions change, every changed approved/archived spec has a revision row, reconcile is candidate-runtime-owned and convergent, 1.9 is default/current/selected while 1.8 remains retained, no already-green migration work is redone, no repository-wide gate runs before final integrated release readiness]
- **executor_discretion:** [sentence grammar after the exact prefix, revision-row wording, order of remaining independent targeted proofs; no discretion to widen files, assertions, findings, or gates]
- **files:** [`catalogs/5.toml` (preserve existing T4 candidate edit; owner T5), `standards/catalog.md` (preserve serialized render-catalog contribution; owner T3), `standards/project-spec/README.md` (preserve existing T4 candidate edit; owner T5), `standards/project-spec/adopt.md` (preserve existing T4 candidate edit; owner T5), `standards/project-spec/agent-summary.md` (preserve existing T4 candidate edit; owner T5), `.standards/catalog.toml` (preserve reconciled candidate edit; owner T5), `.standards/lock.toml` (preserve reconciled candidate edit; owner T5), `docs/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md` (preserve reported repair; owner T5), `docs/specs/2026-07-07-project-standards-mcp-enablement-roadmap-spec.md` (preserve reported repair; owner T5), `docs/specs/2026-07-07-project-standards-mcp-server-implementation-spec.md` (preserve reported repair; owner T5), `docs/specs/archive/2026-07-07-standard-bundle-authoring-standard.md` (preserve reported repair; owner T5), `docs/specs/2026-07-10-standard-bundle-authoring-v2-spec.md` (preserve reported repair; owner T5), `docs/specs/2026-07-09-agent-handoff-standard-package.md` (preserve reported repair; owner T5), `docs/specs/2026-07-10-consumer-standards-control-plane-spec.md` (preserve reported repair; owner T5), `docs/specs/2026-07-26-v5-adoption-integrity-correction-train-spec.md` (preserve reported repair; owner T5), `docs/specs/2026-07-27-v5-validation-fidelity-correction-train-spec.md` (preserve reported repair; owner T5), `tests/package_contract/test_project_spec_1_9.py` (modify only stale activation assertions in `test_project_spec_1_9__projection_and_unadvertised_catalog_role_are_exact`; owner T3), `docs/research/2026-08-01-project-spec-conformance-dogfood-evidence.md` (complete targeted receipt only; owner T5)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** [T4]
- **superseded_by:** []
- **corrects:** []
- **discovered_from:** [T4]
- **evidence:** [EV-001]
- **recovery:** resume the exact preserved 16-path candidate on base `095aec56`; it has no unclaimed edit or gate, strict source/candidate/validate are clean, reconcile advances 1.8→1.9 and then no-ops, and GitHub Workflow 1.2 remains unadvertised. Do not recreate those edits or rerun proof already established solely to repeat it. Add only the named activation-assertion correction, then run the remaining targeted proof. If inventory, semantic review, reconcile, strict lint/validate, assertion freezing, or exact-path proof fails, restore the pre-continuation catalog/root/self-host/corpus/test snapshot as one unit; leave the unadvertised T3 candidate intact and never weaken the linter or run a repository-wide gate inside T5.
- **acceptance:** PV-T5-001 proves the #143 prerequisite remains checkpointed, the exact selected path set is unchanged, all 406 successor findings remain repaired, every changed requirement retains its ID/meaning/rationale/acceptance/priority and truthful revision history, strict lint and validate are clean through source/candidate/installed paths, catalog rendering and activation/reconcile converge, and the named 1.9 package-contract node advances only its stale activation assertions to 1.9 default/current/selected with 1.8 retained while preserving every projection/integrity and non-activation assertion.
- **sub-tasks:**
  - **T5.1 PRECHECK** — validate T1–T3 checkpoints and superseded T4; resume the exact 16-path candidate with no unclaimed edit/gate; verify the #143 checkpoint remains authoritative; freeze the selected path set/hashes and every non-activation byte in the named 1.9 test; confirm the preserved 406-finding receipt and no later drift.
  - **T5.2 SNAPSHOT** — retain the existing per-requirement before table and record only the named test node's activation-assertion span; do not regenerate snapshots or repeat completed repairs.
  - **T5.3 APPLY** — change only the named 1.9 node's Catalog/generated/lock activation assertions from 1.8/absent/unadvertised to 1.9 default/current/selected with 1.8 retained; preserve every other candidate and test byte.
  - **T5.4 VERIFY** — run the named 1.9 node, every T1–T4 focused regression, strict source/candidate/installed lint and validate, and compare every changed requirement against the retained before table; confirm meaning, acceptance, priority, lifecycle, projection, and non-activation assertion preservation.
  - **T5.5 PROVE RECOVERY** — confirm the retained isolated recovery receipt still applies, the second clean reconcile remains a no-op, and reverting only the new test correction restores the exact blocked candidate without touching T1–T3 or repeated migration work.
  - **T5.6 CAPTURE EVIDENCE** — finalize EV-001 with exact 16-path inventory, 406-finding RED and zero-finding strict results, per-document semantic review, #143 checkpoint, activation-test correction, catalog/reconcile convergence, GitHub Workflow 1.2 unadvertised control, and targeted proof; record explicitly that no intermediate repository gate ran.
  - **T5.7 Verify Task** — run PV-T5-001, T1–T4 focused tests, five package checks, strict source/candidate/installed lint and validate, scoped documentation/Markdown checks, `git diff --check`, reconcile/no-op, semantic comparison, and the exact-path/no-unclaimed-diff oracle; create the replacement checkpoint. Do not run `scripts/verify.sh` or `--full`; the final integrated release coordinator runs the one full gate and hosted CI.

## 10. Integration, Migration, and Recovery

### 10.1 Integration Sequence

1. T1 and T2 independently freeze their preservation seams, observe correct-reason RED, and land the version-neutral contracts.
2. T3 verifies #156 T2/PV-T2-001 before its first payload write, consumes both #62 contracts, composes the complete unadvertised 1.9 payload, renders its required unadvertised catalog row, and proves exact-selected behavior through the candidate wheel while Catalog 5/self-host selection remains on 1.8.
3. T4 remains the superseded historical blocked boundary. T5 verifies the separate #143 checkpoint/readiness, resumes the exact 16-path candidate without redoing green work, freezes non-activation test bytes, corrects only the named stale activation assertions, and completes semantic plus catalog/reconcile targeted proof.
4. The final integrated release coordinator reruns the complete child proof, executes the repository-wide full gate once, and owns hosted CI. The resulting child checkpoint is eligible for parent T25, but this plan has no publication authority.

### 10.2 Candidate and Compatibility Transition

- Required: yes, repository candidate only; no published-state migration.
- Compatibility period: T3 leaves 1.8 as the default; T5 completes the preserved activation so 1.9 is default while 1.8 remains retained/selectable.
- Idempotency: package projection, selected-corpus strict lint, and self-host reconcile checks must converge on repeat with no unplanned diff.
- Point of no return: none in this plan; release publication belongs to T25.
- Rollback / forward repair: restore the last green task checkpoint or fix only unreleased 1.9 plus its digest/catalog/projection. Never rewrite 1.8.
- Recovery proof: PV-T5-001 consumes the retained isolated pre-activation restoration and second reconcile receipt, then proves the narrow assertion correction can be reverted independently.

### 10.3 Late Failure and Correction

An integrated, stale-activation-test, dogfood, semantic-review, or later #143 same-candidate failure blocks T5/T25 acceptance. Append a correction task against the completed owner when necessary, preserve checkpoint history, rerun PV-T1-001 through PV-T3-001 plus PV-T5-001, and do not publish until the targeted child proof plus the release coordinator's one final full gate/hosted CI are green.

## 11. Risks, Assumptions, and Open Questions

### 11.1 Risks

| ID | Risk | Likelihood | Impact | Treatment | Owner / Task |
| --- | --- | --- | --- | --- | --- |
| R-001 | Structural extraction includes legitimate surrounding prose and creates false positives. | medium | high | Isolate only the approved paragraph/block boundaries and prove sanctioned outside tailoring remains clean. | T1 |
| R-002 | Optional coverage metadata leaks into 1.8 or legacy JSON/human output. | medium | high | Characterize exact absent-metadata output first and gate projection only on provider-declared metadata. | T2 |
| R-003 | The required #143 work changes the same unreleased 1.9 provider between T3 and activation completion. | high | medium | Preserve #62 tests as the compatibility oracle, rerun PV-T3-001 after the edit, and block T5 until its checkpoint is verified. | external #143 owner / T5 |
| R-004 | Package identity, digest, projection, generated catalog, or self-host lock advances incompletely. | medium | high | Run family preflight, render the catalog, reconcile through the candidate runtime, and require all five package/graph/schema/projection/catalog checks. | T3 |
| R-005 | Mechanical prefix repair changes the subject or meaning of hundreds of selected requirements. | high | high | Preserve T4's row snapshot, compare rationale/acceptance/priority, and require independent semantic review before T5 can complete. | T5 |
| R-006 | #143 is not checkpointed before the shared 1.9 activation boundary. | medium | high | T5 verifies the retained prerequisite before continuation; the separately governed #143 workflow must supply its provider checkpoint and cross-package readiness. | external #143 owner / T5 |
| R-007 | T3's combined projection/lifecycle node remains stale after activation or is over-edited while correcting its role/lock assertions. | high | medium | T5 claims only the named node, freezes its projection/non-activation bytes, advances only Catalog/generated/lock expectations, and runs focused/full package-contract proof. | T5 contributor; owner T3 |

### 11.2 Assumptions

| ID | Assumption | Impact if False |
| --- | --- | --- |
| A-001 | The existing selected provider's schema-validated `structured_output` remains the authoritative metadata carrier. | If it cannot preserve the fixed array, pause T2/T3 and return for an interface decision rather than adding a version hardcode. |
| A-002 | Project Specification 1.9 is the next successor identifier and remains unpublished during this plan. | If another task publishes 1.9 first, pause T3/T5 and revise the candidate/version boundary; a same-train unpublished #143 edit instead reruns this plan's proof. |
| A-003 | #156's terminal prerequisite remains T2/PV-T2-001 under plan revision 1. | If #156 is revised or superseded, keep T3 blocked and revise this plan's external gate rather than inferring checkpoint equivalence. |

### 11.3 Open Questions

None.

## 12. Final Verification

- `uv run --no-project scripts/plan.py validate docs/plans/2026-08-01-project-spec-conformance-plan.md` reports revision 3 valid and execution state matches all checkpoint commits.
- PV-T1-001, PV-T2-001, PV-T3-001, and PV-T5-001 pass from the integrated tree with no orphan requirement or proof; T4 remains non-executable superseded history.
- `uv run project-standards standards validate-packages --root . --json`, `validate-graph --root . --require-all-manifests --json`, `generate-package-schemas --root . --check`, `sync-payload-projection --root . --check`, and `render-catalog --root . --check` all pass against the candidate runtime.
- Candidate/installed `project-standards validate`, successor strict lint, the five package checks, scoped repository Markdown checks, `git diff --check`, reconcile/no-op, and semantic comparison pass in T5. The final integrated release coordinator then runs the repository-wide full gate once and owns hosted CI; neither broad gate is repeated per task.
- A clean 1.9 document names both checks in human and JSON output; independent Lifecycle, Quality, Appendix A/B/D, and requirement-row mutations produce the approved warning/locus/line and strict exit.
- Selected 1.8 and legacy runs retain exact human/JSON/finding/exit behavior, and every 1.8 payload byte/digest remains unchanged.
- The exact selected corpus is strict-clean; every changed requirement retains its ID, intent, rationale, acceptance, priority, and truthful revision history under independent semantic review.
- Package identity, catalog role, family navigation, projection, `.standards` resolution, and repeat reconcile are consistent; no publication, tag, asset, push, or issue mutation occurred.
- The separately governed #143 Project Specification checkpoint and cross-package readiness are recorded before activation; no blocker, unapproved deviation, or incomplete correction remains in the integrated candidate.
- The exact #156 T2/PV-T2-001 checkpoint is recorded and its graph/corpus acceptance reruns green before any Project Specification 1.9 payload write.

## 13. Close-out

- Record the final child-plan checkpoints and verification summary for parent T25 preflight.
- Harvest any approved deviation, corrected assumption, or #143 interaction into the owning plan/handoff artifact without rewriting completed task definitions.
- Keep release, hosted-CI, artifact, and issue-closure proof out of this plan; T25 stores it in `docs/research/2026-08-01-project-spec-conformance-release-evidence.md` as `EV-009`.
- Delete only this plan's authoring/execution scratch after all durable checkpoints and parent-consumable facts are committed.

## Appendix A. Interface and State Contracts

| Contract | Owner / Producer Task | Consumer(s) | Current | Planned / States | Errors / Limits | Compatibility / Invariant | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `conformance-lint-v1` | T1 | T3 provider | `lint_document` has no conformance mode | Internal default-off activation returns normal findings plus the two approved warning families | Unknown profile remains existing structural behavior; no exception/config surface | Disabled is result-equivalent to current lint; enabled uses selected templates only | approved selected design |
| `spec-lint-coverage-v1` | T2 | T3 provider and CLI users | Provider structured result carries findings; CLI discards other fields | Optional exact array `shared-boilerplate`, `mandatory-phrasing`; CLI projects only when present | Missing/invalid field cannot claim coverage; provider schema rejects invalid successor values | Absent metadata preserves exact predecessor human/JSON shape | approved D3 |
| `project-spec-1.9-lint-v1` | T3 | T5, selected CLI, and parent T25 | 1.8 returns findings only and does not activate conformance | 1.9 returns findings plus fixed checks and activates conformance for every linted document | Findings stay warning; strict converts any finding to exit 1; no validation effect | 1.8 bytes/behavior immutable; the pre-activation #143 edit preserves this contract | approved integrated design |
| `project-spec-1.9-dogfood-v1` | T5 | parent T25 | Catalog/self-host select 1.8; selected corpus contains conformance drift | After #143 readiness, Catalog/self-host select 1.9; selected corpus is strict-clean and semantically preserved | Missing #143 checkpoint, unreviewed row, changed path set, finding, or non-convergent catalog/reconcile blocks completion | Activation, corpus edits, rendered catalog, and self-host state form one recoverable checkpoint | `.standards/config.toml`, issue #143, and repository dogfood policy |
| `project-spec-1.9-activation-test-v1` | T5 contributor; owner T3 | T5 activation and final release coordinator | Projection is exact, but the combined node still expects 1.8 default/lock plus 1.9 absent/unadvertised. | Preserve projection/integrity assertions; expect 1.9 default/current/selected and 1.8 retained after activation. | Any non-activation byte change, missing retained predecessor, stale role/lock, or projection drift fails. | Shared-file contribution is limited to one named node and serialized after T3. | T3 package contract; blocked T4 activation receipt |
| Child-to-parent release boundary | T5 | parent T25 | no completed activated 1.9 candidate | verified unpublished activated candidate and checkpoint set | Any failed targeted proof, final gate, or missing explicit authorization blocks publication | T25 alone runs the one full gate/hosted CI, publishes, captures EV-009, and closes #62 | parent task T25 |

## Appendix B. Requirement-to-Proof Traceability

| Proof ID | Requirement(s) | Task | Method | Oracle | Command / Procedure | Expected Result | Negative Control | Environment | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PV-T1-001 | REQ-001, REQ-002 | T1 | unit and table/section contract | immutable profile templates and approved loci/line contract | `PYTHONPATH="$PWD/build/wheel-runtime" uv run pytest tests/test_spec_conformance_lint.py tests/test_spec_lint.py` | For each Light/Standard/Full profile, all five applicable canonical surfaces and recognized requirement cells classify exactly; tailored surrounding prose and disabled mode stay clean/current | in every profile mutate each applicable surface separately, remove the exact prefix, place lookalike text in fences/surrounding prose, and run with activation disabled | bootstrapped locked worktree | ephemeral |
| PV-T2-001 | REQ-003, REQ-006 | T2 | CLI characterization and contract | pre-task clean output plus provider-declared structured metadata | `PYTHONPATH="$PWD/build/wheel-runtime" uv run pytest tests/test_spec_conformance_cli.py tests/test_spec_cli.py tests/test_spec_selected_routing.py` | Declared checks appear in successor clean human/JSON output; absent metadata retains exact legacy/1.8 output and exits | supply no checks, invalid/untrusted inferred version, findings with no checks, and selected 1.8 | bootstrapped locked worktree | ephemeral |
| PV-T3-001 | REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-008 | T3 | selected integration and package contract | approved design, #156 T2 checkpoint, immutable 1.8 digest/bytes, V2 package validators, candidate wheel | validate #156 T2 identity and rerun its graph/corpus proof before writes; run focused T1–T3 tests, 1.8/1.9 package contracts, exact-selected routing for Light/Standard/Full, all five package checks, and Markdown gates | The #156 prerequisite is green before payload creation; each exact-selected 1.9 profile's canonical/tailored cases are clean with explicit coverage; per-profile divergent cases warn and strict-fail; payload/docs/projection and the generated unadvertised catalog row are complete; 1.8/default selection remains exact | remove or mismatch the #156 checkpoint; for each profile mutate a canonical surface/row; also mutate a 1.8 byte, omit one check/schema field, break projection/digest/catalog freshness, or accidentally advance Catalog 5/self-host selection | local bootstrapped source and candidate wheel | ephemeral |
| PV-T5-001 | REQ-007 | T5 | migration continuation, semantic inspection, selected source/candidate/installed regression, and exact activation-assertion correction | #143 checkpoint, exact 16-path candidate, blocked T4's 406-finding RED and per-ID snapshot, successor findings, immutable 1.9 templates, named T3 projection/activation node, and independent reviewer | Validate superseded T4 and #143 readiness; preserve the exact candidate and non-activation test bytes; confirm retained strict/reconcile proof; compare every changed row's ID/rationale/acceptance/priority and meaning; update only stale Catalog/generated/lock assertions; run T1–T5 focused tests, strict source/candidate/installed lint/validate, five package checks, scoped docs/diff checks, reconcile/no-op, and semantic proof. | #143 remains checkpointed; selected set stays exact and strict-clean; only reported loci/revision rows plus the named activation assertions differ from the pre-activation tree; meaning/acceptance/priority/lifecycle and projection assertions are preserved; Catalog/self-host converge on 1.9; targeted proof passes with no unclaimed edit/gate or repeated implementation. | Omit #143 checkpoint, recreate completed repairs, drop/add a selected path, change acceptance/priority, leave one finding, omit a revision row, retain stale 1.8/absent/unadvertised assertion, alter projection/non-activation bytes, fail activation mid-transition, or make a second render/reconcile change state. | Retained isolated recovery receipt plus local Git-aware source/candidate/installed environment; repository-wide full gate/hosted CI deferred to final release coordinator. | EV-001 |

## Appendix C. Durable Evidence

| Evidence ID | Producing Task | Path | Contents / Provenance | Privacy Exclusions | Retention Reason |
| --- | --- | --- | --- | --- | --- |
| EV-001 | T5 | `docs/research/2026-08-01-project-spec-conformance-dogfood-evidence.md` | Blocked T4's #143 readiness, exact 16-path candidate, 406-finding RED and zero-finding strict results, selected-path/hash inventory, semantic review, and reconcile convergence; T5 adds only the activation-test correction and targeted proof with explicit no-unclaimed-edit/gate receipt | no credentials, unbounded logs, private consumer data, or internal reasoning | Preserve the expensive hundreds-row migration and activation basis for parent T25 and later #143 verification; final full-gate/hosted evidence remains EV-009 |

## Appendix D. Deferred Work

| Item | Reason Deferred | Follow-up / Reopen Trigger |
| --- | --- | --- |
| #143 advisory in markdown-tooling, project-spec, and markdown-frontmatter | Separate accepted issue and cross-package behavior; this plan only preserves the shared 1.9 candidate seam | Execute and checkpoint #143 between T3 composition and T5 activation completion, then rerun PV-T3-001 |
| Non-dogfood consumer document repair | This plan owns only the repository's explicit selected corpus and adds no automatic repair | External consumers repair reported loci; a future repair tool requires separate approval |
| Severity promotion or suppression/configuration | Explicitly rejected/deferred by the approved design | Reopen only with ecosystem evidence or a Standard-sanctioned exception |
