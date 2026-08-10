---
plan_format: 3
title: 'Schema Payload Reference Validation Implementation Plan'
slug: 'schema-payload-reference-validation'
status: active
revision: 1
revises_revision: 0
revision_reason: 'initial plan'
pause_reason: ''
source: 'issue L3DigitalNet/project-standards#156; approved triage Option 1'
spec_ref: ''
created: 2026-08-10
updated: 2026-08-10
owners:
  - 'Project Standards maintainers'
---

# Schema Payload Reference Validation Implementation Plan

> **Definition, not state.** This plan stops at a verified local checkpoint. Plan authoring did not generate execution state; during execution, the orchestrator alone generates and mutates the ephemeral state under `.project-pipeline/2026-08-10-schema-payload-reference-validation/execution/`.

## 1. Objective

Make `standards validate-graph` fail deterministically when any declared JSON schema in a successor payload still pins a predecessor identity, migration, endpoint, or selector that the successor manifest does not declare. The check must be family-agnostic, use manifest-derived facts rather than version-pattern heuristics, preserve valid predecessor migration edges, and be documented at the version-cut authoring point before the 5.19 payload cuts.

## 2. Authority and Source Map

| Source | Source Role | Authority / Use | Version / Date | Affected Plan Surface |
| --- | --- | --- | --- | --- |
| `issue:L3DigitalNet/project-standards#156` | normative | Outcome, Option 1 placement in `validate_package_graph`, acceptance, release boundary, and no-payload-cut scope. | 2026-08-10 | §§1, 3, 5–12; T1–T2 |
| `repo:tests/package_contract/helpers.py::assert_schema_payload_references` | current-state evidence | Existing manifest-derived boundary and the three literal classes to preserve while removing per-family opt-in. | `ff894721` | §§4–5; T1 |
| `repo:src/project_standards/package_contract/repository.py::build_package_repository` | current-state evidence | Load boundary and normalized `LoadedPayload` shape; builder-backed repositories currently retain no arbitrary JSON documents. | `ff894721` | §§4–5; T1 |
| `repo:src/project_standards/package_contract/graph.py::validate_package_graph` | decision | Approved hosted validation entrypoint and deterministic graph-finding flow. | `ff894721` | §§4–5; T1 |
| `repo:tests/package_contract/test_graph.py::_repository` | current-state evidence | Synthetic graph fixtures hand-construct `LoadedPayload`; their pure construction contract must remain valid. | `ff894721` | §§4–5; T1 |
| `repo:standards/standard-bundle-authoring/README.md` | current-state evidence | Mutable family landing page that directs authors to the versioned author workflow. | `ff894721` | §§3–5; T2 |
| `repo:tests/package_contract/test_github_workflow_1_1.py` | current-state evidence | Current regression caller records the provider-input historical failure class. | `ff894721` | §§4, 7; T1 |
| `repo:tests/package_contract/test_agent_handoff_1_11.py` | current-state evidence | Current regression caller records the nested migration-report historical failure class. | `ff894721` | §§4, 7; T1 |
| `repo:tests/package_contract/test_python_tooling_1_13.py` | current-state evidence | Current regression caller records the migration/source enum historical failure class. | `ff894721` | §§4, 7; T1 |
| `repo:standards/standard-bundle-authoring/versions/2.6/README.md#author-workflow` | current-state evidence | Immutable workflow content that the mutable landing page routes authors to. | `ff894721` | §§3–5; T2 |

Conflict precedence: the issue's approved Option 1 and acceptance criteria govern. Current helper/test implementation is evidence for the semantic boundary, not authority to retain opt-in wiring.

## 3. Scope, Boundaries, and Constraints

### 3.1 In Scope

- A normalized, builder-populated representation of every declared JSON schema document needed by the graph check, plus fail-closed normalized handling when such a document cannot load.
- A family-agnostic graph finding for a schema literal that contradicts the containing payload manifest, with stable identity, ordering, and ordinary validator exit behavior.
- Focused graph/repository regression coverage, including the three historical shapes, valid declared predecessor edges, synthetic fixtures, invalid JSON, and a clean full-corpus check.
- Mutable Standard Bundle Authoring landing-page guidance that tells successor-cut authors this check is part of the author workflow and points to the graph validation command.

### 3.2 Out of Scope and Deferred

- No new payload version, catalog row, digest change, release-level change, publication, or issue closure; the parent 5.19 work owns those outcomes.
- No regex or version-shaped-literal detector, family-specific future test call, provider execution, or runtime schema-validation redesign.
- No modification of immutable published payload bytes. A later payload cut uses this graph check as its guard.
- This authoring task did not generate `.project-pipeline` state. During execution, only the orchestrator may generate or mutate that ephemeral state; workers must not edit it directly. Agent Handoff and GitHub mutation remain outside this child plan.

### 3.3 Ownership and Preserved Behavior

| Boundary | Owner / Responsibility |
| --- | --- |
| T1 owns | Repository normalization, graph validation, focused regression fixtures/tests, and removal or adaptation of obsolete per-family opt-in coverage. |
| T2 owns | The mutable authoring landing-page explanation and local integrated proof. |
| Depends on | `PayloadManifest` as the sole authority for package identity, migrations, endpoints, selectors, provider ownership, resources, and declared schema locations. |
| Does not own | New 5.19 payload content, catalogs, release/publication, or historical package repair. |
| Must preserve | Pure hand-built graph fixtures, valid manifest-declared predecessor migration edges, existing package findings' ordering/exit taxonomy, and no provider execution. |

### 3.4 Constraints and Authorization

- The approved design is Option 1: the check is standards-owned and runs through `validate_package_graph`, not through a future family test call.
- The expectation set is derived from `PayloadManifest`; schema text under validation may not establish its own allowed version, migration, endpoint, selector, or provider closure.
- A malformed declared JSON schema is a repository-load/validation finding, not an uncaught parser error and not a reason for a builder-backed repository to silently omit the check.
- Complete at a local verified checkpoint. Do not close #156, cut a payload, publish, or alter package bytes under this plan.

## 4. Current State and Target State

### 4.1 Current State

`build_package_repository` loads each V2 manifest, integrity record, and option schema into `LoadedPayload`; it does not retain parsed contents for arbitrary declared JSON schemas. `validate_package_graph` is a pure deterministic aggregator over those normalized payload facts. `assert_schema_payload_references` already walks every declared `.json` resource in selected family tests and derives identity, migration IDs, package/legacy endpoints, selectors, and provider-specific migration closure from the manifest. That guard is opt-in: four successor-family test modules must remember to call it.

The current corpus scan is clean (433 declared JSON schema artifacts and 585 version-shaped literals), but the scan does not make future successor cuts fail unless a family-specific test calls the helper. Three staged-cut defects were previously corrected: `github-workflow@1.1` provider-input version const (`b4d85907`), `agent-handoff@1.11` nested migration-report version const (`d6332978`), and `python-tooling@1.13` configuration-transform `migration_id`/`source` enum (`698acbe5`).

### 4.2 Target State

Every repository built through `build_package_repository` carries the declared JSON schema facts needed for graph validation, and `validate_package_graph` produces deterministic `PackageFinding` records for stale/foreign payload references. Synthetic repositories remain pure: they can omit the builder-only schema-document facts and continue exercising unrelated graph rules. A malformed declared JSON schema produces a stable load-boundary finding rather than aborting validation. The full current corpus remains clean, while each historical defect shape and a newly seeded stale literal fail without adding a family-specific helper call.

### 4.3 Delta Summary

| Area | Current | Target | Must Preserve |
| --- | --- | --- | --- |
| Schema-reference coverage | Test helper checks only callers that opt in. | Graph validator checks all builder-loaded declared JSON schemas. | Manifest-derived expectations and all declared JSON resource coverage. |
| Normalized repository | `LoadedPayload` has manifest, integrity, and option schema. | It additionally exposes immutable parsed JSON-schema facts or a normalized load finding. | Existing positional synthetic fixture construction remains valid and filesystem-free. |
| Diagnostics | No graph code/identity for stale schema payload literals. | Stable graph finding identifies payload, declared schema resource, JSON pointer/property, and violated manifest-derived relation. | Existing finding sort order and CLI nonzero-on-findings behavior. |
| Author guidance | Versioned workflow says validate schemas/graph, but the mutable landing page does not name this successor-copy guard. | Landing page tells authors to run graph validation after copying/cutting a successor because all declared JSON schemas are checked against its manifest. | Immutable `2.6` payload documentation remains unchanged. |

## 5. Change Surface and Architecture

### 5.1 Components and Ownership

| Component / Surface | Current Responsibility | Planned Responsibility | Paths / Contracts | Owning Task |
| --- | --- | --- | --- | --- |
| Repository loader | Loads manifest, integrity, and options only. | Loads declared JSON schema documents once at the repository boundary; either retains immutable normalized facts or records a stable payload-load finding. | `repository.py`, `LoadedPayload`, `build_package_repository` | T1 |
| Graph validator | Validates relations, outputs, and migrations. | Consumes optional normalized schema facts and emits sorted stale-reference findings without provider execution or disk reads. | `graph.py::validate_package_graph` | T1 |
| Historical helper/callers | Duplicated per-family opt-in assertion boundary. | Is retired or reduced to test-only fixture support after its manifest-derived traversal is lifted into the production owner; callers no longer provide coverage wiring. | `tests/package_contract/helpers.py`; four successor test modules | T1 |
| Author guidance | Root landing page routes authors to the immutable author workflow. | Adds concise successor-schema-reference guard guidance in the mutable landing page. | `standards/standard-bundle-authoring/README.md` | T2 |

### 5.2 Validation Flow

```text
payload.toml + declared JSON schema resources
          │
          ▼
build_package_repository
  ├─ normalized LoadedPayload schema facts
  └─ stable load finding for unreadable/invalid JSON
          │
          ▼
validate_package_graph
  ├─ derive allowed identity/migrations/endpoints/selectors/provider closure from PayloadManifest
  ├─ compare every loaded schema property scope
  └─ sort PackageFinding records → standards validate-graph exit 1 when any exist
```

### 5.3 Change-Surface Matrix

| Surface | Applies? | Invariant / Required Change | Proof | Task |
| --- | --- | --- | --- | --- |
| Behavior | yes | Every builder-backed declared JSON schema is checked; stale literals and malformed JSON fail deterministically. | PV-T1-001 | T1 |
| Architecture / dependency direction | yes | Repository boundary parses/normalizes; pure graph consumes facts; manifest remains expectation authority. | PV-T1-001 | T1 |
| Public / cross-task interface | yes | `LoadedPayload` gains backward-compatible optional normalized schema facts; graph findings use stable package diagnostic fields. | PV-T1-001 | T1 |
| Data / state | no | No persistent state or migration is introduced. | PV-T1-001 | T1 |
| Configuration | no | No user configuration, catalog, or package option changes. | PV-T2-001 | T2 |
| Security / trust | yes | Parse untrusted repository JSON as data only; no provider execution, path expansion, or regex-derived authority. | PV-T1-001 | T1 |
| Compatibility / migration | yes | Declared predecessor migration edges stay valid; synthetic fixtures and existing graph diagnostics remain usable. | PV-T1-001 | T1 |
| Operations / deployment | yes | Finish at a local checkpoint; release/cut/publication remain parent-owned. | PV-T2-001 | T2 |
| Documentation | yes | Mutable successor-authoring entry point accurately names the automatic graph guard. | PV-T2-001 | T2 |
| Durable evidence | no | Committed focused tests and documentation are reproducible local evidence. | PV-T2-001 | T2 |

### 5.4 Binding Decisions

| ID | Decision | Rationale | Source | Affected Task(s) |
| --- | --- | --- | --- | --- |
| D-001 | Host validation in `validate_package_graph`; do not add future per-family calls. | The defect is standards-wide and future payloads must inherit coverage automatically. | approved issue #156 Option 1 | T1 |
| D-002 | Reuse the helper's manifest-derived semantic boundary; do not substitute regex/version-shape matching. | Only the manifest knows declared migrations, endpoints, selectors, and provider closure. | issue #156; existing helper | T1 |
| D-003 | Keep graph validation pure for synthetic fixtures by making builder-loaded schema facts optional/backward-compatible, while builder-backed repositories always supply or fail them. | Existing graph unit tests construct `LoadedPayload` directly; skipping builder inputs must not weaken real repository validation. | issue #156; `test_graph.py::_repository` | T1 |
| D-004 | Use one deterministic finding identity per violated schema location/property and normal graph CLI exit semantics. | Operators need stable diagnostics, and `validate-graph` already owns finding ordering and exit behavior. | issue #156; `diagnostics.py` | T1 |
| D-005 | Document the guard in mutable Standard Bundle Authoring root guidance, not immutable `2.6` bytes. | The root page is the maintained entry point for author workflow and released payload docs are immutable. | issue #156; root README | T2 |

## 6. Requirements and Acceptance

| ID | Requirement | Source | Priority | Owner Task | Task(s) | Proof(s) |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-001 | The graph validator shall report every stale/foreign schema payload reference from all builder-loaded declared JSON schemas using manifest-derived identity, migration, endpoint, selector, and provider-closure facts. | `issue:L3DigitalNet/project-standards#156` | Must | T1 | T1 | PV-T1-001 |
| REQ-002 | A deliberately seeded stale const or enum shall fail graph validation without adding a family-specific test helper call, with deterministic finding identity, sort order, and nonzero validator exit. | `issue:L3DigitalNet/project-standards#156` | Must | T1 | T1 | PV-T1-001 |
| REQ-003 | Legitimate declared predecessor migration edges shall remain clean; the three historical defect shapes shall each be rejected; invalid JSON shall remain a normalized load/validation finding. | `issue:L3DigitalNet/project-standards#156` | Must | T1 | T1 | PV-T1-001 |
| REQ-004 | Pure synthetic graph fixtures shall remain constructible without filesystem-backed schema documents, while a builder-backed repository cannot silently skip schema-reference validation. | `issue:L3DigitalNet/project-standards#156` | Must | T1 | T1 | PV-T1-001 |
| REQ-005 | The successor-cut authoring entry point shall document the automatic manifest-to-schema graph guard, and the current corpus shall remain clean. | `issue:L3DigitalNet/project-standards#156` | Must | T2 | T2 | PV-T2-001 |

## 7. Verification and Evidence Strategy

- **Authoritative commands:** targeted package graph/repository pytest modules; `uv run project-standards standards validate-packages --root . --json`; `uv run project-standards standards validate-graph --root . --require-all-manifests --json`; `uv run project-standards standards generate-package-schemas --root . --check`; `uv run project-standards standards sync-payload-projection --root . --check`; `uv run project-standards standards render-catalog --root . --check`; Git-tracked Prettier and markdownlint commands from `AGENTS.md`; and the fast `scripts/verify.sh` run directly local after a fresh bootstrap runtime. Compatible isolated CPU-heavy commands may use rexec, but the Git-dependent fast gate may not.
- **Oracles:** `PayloadManifest` declarations, `PackageFinding` sorting/CLI contract, and the exact stale literals restored from commits `b4d85907`, `d6332978`, and `698acbe5`.
- **Negative controls:** stale successor `version` const, nested migration-report `version` const, stale configuration-transform `migration_id` and `source` enum, a declared predecessor edge that must remain clean, malformed JSON, and an unrelated synthetic graph fixture with no schema facts.
- **Test layers:** normalization/load-boundary unit tests, pure graph unit tests, command/exit JSON diagnostic test, historical mutation controls, full source corpus graph validation, package-contract validators, and documentation format/lint.
- **External environments:** none. No provider, network, catalog publication, or external service is required.
- **Evidence:** all proof is reproducible from committed tests and source; no durable evidence artifact is required.
- **Late failure:** block the owning task. If a completed checkpoint is disproved, append a correction task with `corrects:` and `discovered_from:` rather than changing its definition; rerun the failed proof before a later payload cut.

## 8. Execution Summary

| Task | Title | Disposition | Work Type | Phase | Depends On | Requirement(s) | Primary Proof | Parallel / Conflict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T1 | Normalize and validate schema payload references | active | behavior | P1 | None | REQ-001, REQ-002, REQ-003, REQ-004 | PV-T1-001 | no / owns graph, repository, and test seam |
| T2 | Document the successor-cut guard and verify the repository | active | documentation | P2 | T1 | REQ-005 | PV-T2-001 | no / consumes T1 graph behavior |

## 9. Implementation Tasks

### Phase P1: Repository-Owned Validation

#### T1: Normalize and validate schema payload references

- **disposition:** active
- **outcome:** Builder-backed graph validation detects stale schema payload references from every declared JSON schema resource with stable diagnostics, while synthetic graph repositories remain pure and valid manifest edges remain clean.
- **work_type:** behavior
- **checkpoint:** one green commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** []
- **dependency_reason:** none
- **requirements:** [REQ-001, REQ-002, REQ-003, REQ-004]
- **proof:** [PV-T1-001]
- **source_refs:** [issue:L3DigitalNet/project-standards#156, repo:src/project_standards/package_contract/repository.py::build_package_repository, repo:src/project_standards/package_contract/graph.py::validate_package_graph, repo:tests/package_contract/helpers.py::assert_schema_payload_references, repo:tests/package_contract/test_graph.py::_repository]
- **consumes:** [V2 `PayloadManifest`, declared JSON resources, package finding sort/CLI contract, existing pure graph fixture factory]
- **produces:** [schema-payload-reference-graph-validation-v1]
- **preserves:** [manifest-derived allowance rules, no provider execution, deterministic existing findings, valid predecessor migration edges, positional synthetic `LoadedPayload` fixtures]
- **invariants:** [every builder-loaded declared JSON schema is checked or produces a normalized load finding; schema under test never defines its own allowed references; one stable finding identity per violated location/property; graph validation performs no filesystem reads once given its repository]
- **executor_discretion:** [private dataclass/type/helper names, exact focused fixture layout, whether the lifted traversal remains shared testable code or is a graph-private helper, and concise message wording consistent with package diagnostics]
- **files:** [`src/project_standards/package_contract/repository.py` (modify; owner T1), `src/project_standards/package_contract/graph.py` (modify; owner T1), `tests/package_contract/test_graph.py` (modify; owner T1), `tests/package_contract/helpers.py` (modify/delete only if its production-lifted behavior makes it redundant; owner T1), `tests/package_contract/test_adr_1_5.py` (modify only to remove obsolete opt-in wiring; owner T1), `tests/package_contract/test_agent_handoff_1_11.py` (modify only to remove obsolete opt-in wiring; owner T1), `tests/package_contract/test_github_workflow_1_1.py` (modify only to remove obsolete opt-in wiring; owner T1), `tests/package_contract/test_python_tooling_1_13.py` (modify only to remove obsolete opt-in wiring; owner T1)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** Restore the last green checkpoint if normalization or finding identity is incompatible. Do not weaken the manifest boundary, skip a malformed resource, make graph validation read live files, or preserve per-family calls merely to make a partial implementation pass.
- **acceptance:** PV-T1-001 proves a builder-created repository reports deterministic, stably sorted stale-reference findings and the normal nonzero graph-validator result for a seeded const/enum without any family-specific call; it accepts declared predecessor edges and existing synthetic fixtures; it rejects all three historical shapes and malformed declared JSON without an uncaught exception; and it leaves the current corpus graph-clean.
- **sub-tasks:**
  - **T1.1 CHARACTERIZE** — inventory the current helper's manifest-derived rules and its four callers; capture focused baseline behavior for valid predecessor migration edges, graph finding ordering, and synthetic fixture construction.
  - **T1.2 RED** — add builder-backed graph/repository tests that introduce a stale successor const or enum without calling the helper, reconstruct each of the `b4d85907`, `d6332978`, and `698acbe5` shapes, exercise a valid declared predecessor edge, and feed invalid JSON through the repository boundary. Expected failures are absent schema-reference findings or an unnormalized load failure, not fixture/import errors.
  - **T1.3 Verify RED** — run the focused graph/repository test selection and the `validate-graph --json` fixture/command assertion. Confirm failure identity, ordering, and exit behavior show the missing graph-owned behavior.
  - **T1.4 GREEN** — lift the helper's manifest-derived traversal into the repository/graph ownership boundary; retain builder-loaded immutable JSON facts, create a stable load finding for malformed JSON, and emit graph findings per invalid schema location/property. Give the new `LoadedPayload` member a backward-compatible default or equivalent so `_repository` remains pure, but make `build_package_repository` always populate the facts or record its failure.
  - **T1.5 Verify GREEN** — rerun focused graph/repository and the four historical regression modules; confirm callers no longer need to opt in if their redundant wiring is removed, legitimate manifest-declared migration edges remain clean, malformed JSON is reported rather than raised, and a clean builder-backed repository reaches the check.
  - **T1.6 REFACTOR** — remove only duplicate/obsolete helper and caller wiring after graph-owned coverage proves it; preserve test readability and no filesystem coupling in synthetic graph fixtures.
  - **T1.7 Verify Task** — run PV-T1-001's focused tests, `uv run ruff format --check src tests`, `uv run ruff check src tests`, `rexec -- uv run basedpyright`, `git diff --check`, and the five package/graph/schema/projection/catalog checks applicable to the code/test surface after a fresh runtime bootstrap; create the required checkpoint.

### Phase P2: Authoring Guidance and Integrated Checkpoint

#### T2: Document the successor-cut guard and verify the repository

- **disposition:** active
- **outcome:** The maintained Standard Bundle Authoring landing page directs successor-cut authors to the automatic graph schema-reference guard, and the complete current corpus proves clean under the integrated implementation.
- **work_type:** documentation
- **checkpoint:** one green commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** public
- **depends_on:** [T1]
- **dependency_reason:** consumes `schema-payload-reference-graph-validation-v1` so documentation describes shipped behavior rather than a planned convention
- **requirements:** [REQ-005]
- **proof:** [PV-T2-001]
- **source_refs:** [issue:L3DigitalNet/project-standards#156, repo:standards/standard-bundle-authoring/README.md, repo:standards/standard-bundle-authoring/versions/2.6/README.md#author-workflow, repo:src/project_standards/package_contract/graph.py::validate_package_graph]
- **consumes:** [schema-payload-reference-graph-validation-v1, mutable family landing-page ownership, current V2 author workflow]
- **produces:** [successor-schema-reference-author-guidance-v1, local-integrated-validation-receipt]
- **preserves:** [immutable `versions/2.6/README.md` bytes, existing root-page author workflow routing, no payload/catalog cut, no issue closure/publication]
- **invariants:** [guidance names the automatic manifest-derived graph check and its command without promising regex scanning or runtime provider execution; corpus proof uses actual declared resource/manifest facts]
- **executor_discretion:** [exact paragraph placement and wording, test grouping, and whether a narrowly scoped documentation assertion is useful]
- **files:** [`standards/standard-bundle-authoring/README.md` (modify; owner T2), `tests/test_standard_bundle_authoring_guidance.py` (create only if a focused documentation assertion is genuinely needed; owner T2)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** Revert only the mutable root-page wording if it misstates delivered behavior; do not edit immutable authoring payload bytes or expand this task into a package/version cut. If corpus validation exposes a validator defect, append a correction task against T1 and return to its proof.
- **acceptance:** PV-T2-001 proves the root authoring entry point says that successor cuts must run graph validation because every declared JSON schema is compared with the successor manifest, the current corpus emits no schema-reference findings, all package-contract validators pass, documentation format/lint pass, and the fast repository gate completes green.
- **sub-tasks:**
  - **T2.1 CHARACTERIZE** — verify the mutable landing page is the maintained authoring entry point and the versioned `2.6` guide is immutable package content; record the exact current graph command.
  - **T2.2 RED** — add a narrowly scoped documentation/behavior assertion only if needed to prove the landing page omits the delivered guard; expected failure is the missing successor-schema-reference guidance, not a payload or catalog difference.
  - **T2.3 GREEN** — add concise root-page guidance explaining that copied successor schemas are checked against manifest-derived identity/migration/endpoint/selector facts by `standards validate-graph` and must be clean before a cut proceeds.
  - **T2.4 Verify GREEN** — run the full source corpus `validate-graph --require-all-manifests --json`; confirm zero schema-reference findings and preserve the valid migration controls from T1.
  - **T2.5 REFACTOR** — remove duplicate wording only if it obscures the one maintained authoring instruction; do not revise immutable `2.6` content.
  - **T2.6 Verify Task** — rerun PV-T2-001: all five package/graph/schema/projection/catalog checks, the Git-tracked Prettier and markdownlint gates, `git diff --check`, then `scripts/bootstrap-worktree.sh` and `scripts/verify.sh`; create the required checkpoint and stop at the local verified boundary.

## 10. Integration, Migration, and Recovery

### 10.1 Integration Sequence

1. T1 establishes a normalized repository-to-pure-graph contract and proves correct-reason RED for stale references and malformed JSON.
2. T1's green proof shows the manifest-derived migration boundary accepts legitimate predecessor edges, catches all historical shapes, and leaves no synthetic-fixture coupling.
3. T2 documents the delivered behavior in the mutable authoring entry point and runs the complete current corpus and fast gate. Stop after its local checkpoint; the parent 5.19 train decides payload cuts, issue closure, and publication.

### 10.2 Migration / State / Configuration Transition

- Required: no persistent data, consumer configuration, or package migration transition.
- Compatibility period: graph diagnostics are additive validation; valid manifests and synthetic fixtures remain supported.
- Idempotency: graph validation is read-only and deterministic for identical normalized input.
- Point of no return: none.
- Rollback / forward repair: revert the owning checkpoint before a payload cut, or append a correction task for a completed checkpoint; never alter released payloads to hide a validator finding.
- Recovery proof: PV-T1-001 demonstrates normalized malformed-input failure and graph purity; PV-T2-001 demonstrates clean corpus revalidation.

### 10.3 Late Failure and Correction

An unexpected schema form, missing manifest fact, or integration regression blocks the current task. If target intent is unclear, return the smallest decision request to #156's owner; otherwise append a new correction task with permanent ID and `corrects:`/`discovered_from:` references. Completed task definitions and generated state are never rewritten.

## 11. Risks, Assumptions, and Open Questions

### 11.1 Risks

| ID | Risk | Likelihood | Impact | Treatment | Owner / Task |
| --- | --- | --- | --- | --- | --- |
| R-001 | Lifting the helper changes a permissive/strict edge for an unusual declared schema scope. | medium | high | Derive all allowances from the existing helper and prove the clean corpus plus historical mutations before removing callers. | T1 |
| R-002 | A loader design breaks positional synthetic fixtures or lets real builder paths omit parsed schema facts. | medium | high | Require backward-compatible synthetic construction and an explicit builder-backed cannot-skip proof. | T1 |
| R-003 | Documentation accidentally changes immutable payload content. | low | medium | Limit T2 to the mutable family root and assert the versioned guide remains untouched. | T2 |
| R-004 | A broad gate masks an inadequate focused proof. | low | high | Require correct-reason RED and deterministic graph/CLI assertions before package validators and fast gate. | T1 |

### 11.2 Assumptions

| ID | Assumption | Impact if False |
| --- | --- | --- |
| A-001 | Every schema reference that this guard owns is in a manifest-declared `.json` resource, as the existing helper currently defines the corpus. | Expand the authoritative resource-selection rule only with an owner decision, then amend T1 before implementation. |
| A-002 | The current 433-artifact/585-literal scan is a characterization baseline, not a permanently hardcoded product contract. | Keep corpus-clean proof but derive the active set from manifests rather than freeze counts that change with legitimate payload cuts. |

### 11.3 Open Questions

None.

## 12. Final Verification

- Every Must requirement maps to T1 or T2 and its passing Appendix B proof.
- Correct-reason RED demonstrates the missing graph-owned behavior before implementation; focused GREEN proof demonstrates deterministic finding/exit behavior, invalid-JSON containment, valid migration compatibility, historical negative controls, and pure synthetic fixtures.
- `build_package_repository` cannot silently omit the check for a declared JSON schema; `validate_package_graph` stays free of provider execution and post-build filesystem reads.
- The full source corpus is schema-reference clean; package, graph, schema, projection, catalog, Python static, documentation, and fast-gate checks pass as applicable.
- The only documentation change is the mutable Standard Bundle Authoring landing page; no payload/catalog/publication/issue-closure work is claimed.

## 13. Close-out

- **Completed:** pending T1 and T2 checkpoints.
- **Decisions / deviations harvested:** record only unexpected schema-boundary decisions that change #156 intent.
- **Risks closed / accepted:** close R-001 through R-004 with task proof, or retain a bounded follow-up.
- **Deferred/discovered work filed:** parent 5.19 work owns payload cuts, #156 closure, and publication.
- **Source/ADR/handoff reconciliation:** no Agent Handoff mutation belongs to this child plan.
- **Scratch teardown:** authoring generated no state. During execution, only the orchestrator may generate, mutate, or tear down execution state after its evidence is harvested; workers never edit it directly.

## Appendix A. Interface and State Contracts

| Contract | Owner / Producer Task | Consumer(s) | Current | Planned / States | Errors / Limits | Compatibility / Invariant | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Builder-to-graph schema facts | T1 | `validate_package_graph`, graph CLI | `LoadedPayload` lacks arbitrary schema contents. | Builder supplies immutable parsed facts for each declared JSON schema; synthetic fixtures may omit the optional facts. | Invalid/unreadable JSON becomes a stable load finding; no uncaught parse error. | Builder-backed repositories cannot skip; synthetic graphs stay pure. | `repository.py::build_package_repository`; #156 D-003 |
| Schema-reference finding | T1 | graph CLI, package validators, T2 corpus proof | No graph finding exists. | One sorted `PackageFinding` per violated declared schema location/property, naming payload/resource/pointer identity and manifest contradiction. | Validator returns its standard nonzero finding exit. | No regex authority; existing diagnostic field/sort contract remains. | `diagnostics.py`; #156 D-004 |
| Successor-author guidance | T2 | package authors | Root page links to workflow only. | Root page names automatic graph guard and command. | No payload mutation. | Immutable `2.6` guide stays unchanged. | `standard-bundle-authoring/README.md`; #156 D-005 |

## Appendix B. Requirement-to-Proof Traceability

| Proof ID | Requirement(s) | Task | Method | Oracle | Command / Procedure | Expected Result | Negative Control | Environment | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PV-T1-001 | REQ-001, REQ-002, REQ-003, REQ-004 | T1 | focused repository/graph/CLI regression | Manifest-derived expected sets; `PackageFinding` sort and CLI contracts; historical commit mutations | Run focused `tests/package_contract/test_graph.py` plus affected repository/caller modules, then the graph CLI JSON assertion against its committed temporary fixture. | Seeded stale const/enum yields deterministic ordered finding and exit 1 without a family call; valid declared edge and pure synthetic fixture are clean; malformed JSON is normalized; all historical shapes fail. | Reintroduce the provider-input const from `b4d85907`, nested migration-report const from `d6332978`, and migration/source enum from `698acbe5`; add malformed JSON and an undeclared stale literal. | local candidate runtime after bootstrap where required | ephemeral |
| PV-T2-001 | REQ-005 | T2 | documentation plus integrated package/repository verification | Mutable root-page content; manifest-discovered source corpus; package validators | Run the five package/graph/schema/projection/catalog checks, Git-tracked Prettier and markdownlint checks, then `scripts/bootstrap-worktree.sh` and direct-local `scripts/verify.sh`. | Guidance accurately names the automatic guard; `validate-graph --require-all-manifests --json` is clean for the full corpus; documentation and fast gate pass. | Remove/alter the new guidance in its focused assertion if retained; rerun the three T1 historical mutations before accepting corpus clean. | local checkout; Git-dependent fast gate runs directly local | ephemeral |

## Appendix C. Durable Evidence

Not applicable: committed focused regressions, the root-page change, and repeatable local validation provide durable evidence; no expensive, external, or non-repeatable artifact is introduced.

## Appendix D. Deferred Work

| Item | Reason Deferred | Follow-up / Reopen Trigger |
| --- | --- | --- |
| 5.19 successor payload cuts, issue #156 closure, and publication | This child plan owns only the generic guard and a local verified checkpoint. | Parent 5.19 execution consumes T2's checkpoint before cutting any payload. |
