---
plan_format: 3
title: 'Create-Only Content Advisory Implementation Plan'
slug: 'create-only-content-advisory'
status: active
revision: 1
revises_revision: 0
revision_reason: 'initial plan'
pause_reason: ''
source: 'issue L3DigitalNet/project-standards#157; owner decision of 2026-08-10'
spec_ref: ''
created: 2026-08-10
updated: 2026-08-10
owners:
  - 'Project Standards maintainers'
---

# Create-Only Content Advisory Implementation Plan

> **Definition, not state.** This plan stops at a verified local checkpoint. Plan authoring did not generate execution state; during execution, the orchestrator alone generates and mutates the ephemeral state under `.project-pipeline/2026-08-10-create-only-content-advisory/execution/`.

## 1. Objective

Make stale, unmodified create-only content discoverable without weakening create-only ownership. For each currently selected and materialized create-only unit, the control plane will compare the observed consumer content with the immutable content digests carried by every permanently advertised version of that package. Content matching the selected version stays silent; content matching a strictly earlier advertised version emits one non-blocking advisory in validation and drift reporting; customized, unmatched, absent, or newer-version content stays silent under this advisory. The engine gains no refresh command, overwrite branch, lock rewrite, or automatic update path.

## 2. Authority and Source Map

| Source | Source Role | Authority / Use | Version / Date | Affected Plan Surface |
| --- | --- | --- | --- | --- |
| `issue:L3DigitalNet/project-standards#157` | normative | The issue defines the alternatives and acceptance boundary; owner comment `5235741187` selects permanent create-only ownership, the advisory, silent current/customized cases, no refresh path, no payload cut, ADR content, and durable bug closure. | owner decision 2026-08-10 | §§1, 3–13; T1–T2 |
| `adr:docs/adr/adr-0024-catalog-scoped-package-version-channels.md#catalog-channels` | decision | Guarantees every advertised version has an immutable embedded payload and remains advertised permanently; this is the advisory's complete historical digest oracle. | accepted 2026-07-27; amended 2026-08-09 | §§3–7, 10–13; T1–T2 |
| `adr:docs/adr/adr-0028-create-only-artifact-refresh.md#amendments` | decision | Makes manual copy the sanctioned refresh, preserves consumer ownership, records current lock behavior, and reserves the previously open automated path that this issue now rejects. | amended 2026-08-09 | §§3–6, 10–13; T1–T2 |
| `repo:docs/handoff/bugs/006-create-only-artifacts-invisible-to-drift-check.md` | current-state evidence | Records the stale-scaffold failure, the lock-based false provenance trap, and the still-open issue #157 disposition that must be closed. | `5e1b04f1` | §§4–6, 9, 13; T2 |
| `repo:src/project_standards/control_plane/cli.py::build_planner_request` | current-state evidence | Loads every advertised payload from one integrity-checked installed catalog and gives the planner both all payloads and the selected resolution. | `5e1b04f1` | §§4–5; T1 |
| `repo:src/project_standards/control_plane/planner.py::plan_reconciliation` | current-state evidence | Owns repository snapshotting, selected create-only semantic-unit normalization, sorted control findings, and the plan result consumed by validation and drift reporting. | `5e1b04f1` | §§4–9; T1 |
| `repo:src/project_standards/control_plane/planner.py::_read_payload_file` | current-state evidence | Enforces that source bytes come from the integrity-verified installed payload and still match the declared digest. | `5e1b04f1` | §§4–7, Appendix A; T1 |
| `repo:src/project_standards/control_plane/planner.py::_is_newly_absent_create_only` | current-state evidence | Defines permanent create-only absence and the existing `CP-CREATE-ONLY-ABSENT` neighbor that this advisory must not replace or duplicate. | `5e1b04f1` | §§3–7; T1 |
| `repo:src/project_standards/control_plane/cli.py::validate_repository` | current-state evidence | Top-level `project-standards validate` emits planner findings while warning-only findings do not independently fail validation. | `5e1b04f1` | §§4–7, Appendix A; T1 |
| `repo:src/project_standards/mcp_services/providers.py::drift_check` | current-state evidence | The read-only drift report serializes the reconciliation plan's actions and findings without reclassifying them. | `5e1b04f1` | §§4–7, Appendix A; T1 |
| `repo:tests/control_plane/planner_helpers.py::write_payload` | current-state evidence | Provides integrity-checked artifact and semantic-contribution fixtures but currently models one advertised version per family in `resolution_request`. | `5e1b04f1` | §§4, 7, 9; T1 |
| `repo:docs/handoff/conventions.md` | operational evidence | Governs durable bug ownership, proportional validation, full-gate timing, and rexec/local execution boundaries. | `5e1b04f1` | §§3, 7, 9, 12–13; T2 |

Conflict precedence: the issue owner's 2026-08-10 decision governs the target. ADR 0024 supplies the permanent historical-data dependency; ADR 0028 supplies the manual-copy and ownership boundary but is amended where it still reserves an automated path or describes notification as absent. Current code and tests establish implementation seams, not target authority.

## 3. Scope, Boundaries, and Constraints

### 3.1 In Scope

- One stable warning advisory for a selected, materialized create-only semantic unit whose observed digest does not match its selected payload unit but does match the equivalent unit in at least one strictly earlier, permanently advertised version of the same package.
- Matching across both whole-file create-only artifacts and static create-only semantic contributions, using their normalized target, adapter, and scope rather than lock version metadata or consumer bytes in output.
- Deterministic advisory identity, ordering, human output, JSON serialization, current-version identity, and matched-superseded-version selection.
- Correct-reason regression coverage for stale, current, customized/unmatched, absent, duplicate historical digest, newer/candidate, unrelated address/package, whole-file, and semantic-contribution cases.
- Integration proof that top-level validation and the read-only drift report both expose the same planner advisory without mutation or an advisory-only nonzero result.
- An ADR 0028 amendment recording the permanent rejection of refresh, the accepted customized-copy blind spot, and the explicit dependency on ADR 0024 permanent advertisement; durable bug 006 is updated to its terminal outcome.

### 3.2 Out of Scope and Permanent Non-Goals

- No `reconcile --refresh-create-only`, `upgrade` provider operation, per-artifact refresh option, automatic refresh, overwrite action, or other engine write path for create-only content.
- No change to `CP-CREATE-ONLY-ABSENT`, `create_only_absences`, create-only preservation, lock digests, lock schema, reconciliation actions, drift calculation, apply behavior, or provider effects.
- No advisory for customized/unmatched bytes, content matching a newer advertised version, provider-generated create-only content without an immutable declared source digest, unselected packages, non-materialized declarations, managed units, or consumer-owned paths with no selected declaration.
- No package version, payload byte, catalog row, aggregate digest, release number, changelog, package cut, publication, or GitHub lifecycle mutation.
- No generated `.project-pipeline` state during authoring. During execution, workers do not edit generated state directly.

### 3.3 Ownership and Preserved Behavior

| Boundary | Owner / Responsibility |
| --- | --- |
| T1 owns | Planner-side historical digest matching, diagnostic contract, fixture support, focused behavior tests, validation presentation proof, and drift-report proof. |
| T2 owns | The ADR 0028 amendment, durable bug 006 terminal update, Agent Handoff validation, documentation gates, and final repository gate. |
| Depends on | ADR 0024's immutable embedded payloads and permanent advertisement; the installed catalog/payload integrity boundary; selected resolution and adapter semantic digests. |
| Does not own | Consumer refresh or overwrite, lock provenance redesign, package release mechanics, package-specific validation providers, or GitHub issue state. |
| Must preserve | Consumer-authored create-only bytes, permanent absence semantics, current silent/no-drift behavior, warning-only exit behavior, content confidentiality, stable finding ordering, and all existing managed/partial/shared reconciliation behavior. |

### 3.4 Constraints and Authorization

- The historical oracle is the integrity-verified installed catalog payload set, never Git history, the network, the consumer lock's recorded version, or a family-specific table.
- Current selected content wins before historical matching: if the observed digest equals the selected payload unit, emit no advisory even when older versions share the same digest.
- A historical match is stale only when its package version sorts strictly before the selected resolved version. A match found only in a later retained/candidate version is not evidence of staleness and remains silent.
- Emit at most one advisory per selected semantic address. When the same observed digest occurs in several earlier versions, name the greatest matching earlier version as the deterministic nearest superseded identity.
- The advisory is severity `warning`, is content-safe, and does not change `applicable`, plan actions, the next lock, `_drift`, or command exit status by itself.
- Complete at a verified local checkpoint. Do not mutate live consumers, GitHub work state, payload projections, or release state under this plan.

## 4. Current State and Target State

### 4.1 Current State

`InstalledDistribution.load_catalog` verifies and retains every payload advertised in the selected catalog major. `build_planner_request` supplies that complete set to `PlannerRequest.payloads`, while package resolution chooses the current version and effective options. `plan_reconciliation` reads selected sources through `_read_payload_file`, normalizes artifacts and contributions through the adapter registry, captures the current repository once, and already knows which selected units are create-only.

The planner currently classifies any existing create-only unit as `PRESERVE`, regardless of whether its bytes equal the selected payload, an older payload, or consumer customization. That is the correct write policy. Its only create-only-specific warning is `CP-CREATE-ONLY-ABSENT`, emitted once when the consumer deletes a locked create-only unit; recorded absence then remains permanent. No code compares observed content with equivalent create-only sources from the other advertised versions.

Planner findings are already the shared read model. `validate_repository` emits them for top-level validation. Reconciliation preview/check emits them in human and JSON output. The MCP `drift_check` report publishes the plan's own serialized findings. Warning findings do not make the plan inapplicable, and `_drift` depends only on mutating actions or next-lock change. This existing route can expose an advisory without adding a command or write path.

Four currently advertised families contain create-only output: `adr`, `agent-handoff`, `cli-documentation`, and `markdown-frontmatter`. The last includes semantic contributions, so whole-file-only matching would leave a known family uncovered.

### 4.2 Target State

The planner builds a deterministic historical index from the immutable installed payload set for static create-only declarations. Each current selected/materialized create-only unit is compared by package and normalized semantic address. The observed semantic digest is classified in this order:

1. Selected-version digest match: current, no advisory.
2. Greatest strictly earlier advertised-version digest match: stale scaffold, one `CP-CREATE-ONLY-STALE` warning naming both that matched version and the selected version.
3. No earlier match, including customized bytes or a later-version-only match: consumer-authored/indeterminate, no advisory.
4. Missing or otherwise uninspectable current unit: no stale advisory; existing absence, path, or parse findings remain authoritative.

The warning carries the selected standard/version, target, adapter scope identity, observed and selected digests, and a safe manual-review hint. It never publishes consumer bytes. Identical inputs produce identical finding order and human/JSON output. Validation and drift reporting expose the same planner result, remain read-only, and remain successful when this warning is the only finding.

ADR 0028 records that create-only is permanently create-only, manual editing/copy remains the only refresh, no explicit refresh command will be added, customized copies are intentionally silent because staleness is unknowable, and the advisory depends on ADR 0024 retaining every advertised immutable payload. Durable bug 006 no longer points to an open decision or says validation/drift-check are blind to an unchanged historical scaffold.

### 4.3 Delta Summary

| Area | Current | Target | Must Preserve |
| --- | --- | --- | --- |
| Create-only writes | Preserve present consumer content; permanently record deletion. | Unchanged. | No refresh or overwrite path; `CP-CREATE-ONLY-ABSENT` remains load-bearing. |
| Currency signal | No historical content comparison. | Warning only for exact match to the nearest strictly earlier advertised create-only unit digest. | Current, customized, later-only, absent, nonselected, and unrelated content stay silent. |
| Historical oracle | All advertised payloads are already loaded and integrity checked but unused for currency. | Planner derives candidates from the complete installed set and normalized static unit sources. | ADR 0024 permanence; no network, Git, lock-version, or hardcoded-family dependency. |
| Public output | Planner findings flow to validation, reconcile reports, and MCP drift reports. | Stable `CP-CREATE-ONLY-STALE` warning uses the same flow. | Warning alone does not imply drift/failure and exposes no consumer bytes. |
| Governance | ADR 0028 reserves automation; bug 006 defers to #157. | ADR rejects automation permanently and names limits/dependency; bug is terminal. | Accepted-text/amendment discipline and manual-copy ownership. |

## 5. Change Surface and Architecture

### 5.1 Components and Ownership

| Component / Surface | Current Responsibility | Planned Responsibility | Paths / Contracts | Owning Task |
| --- | --- | --- | --- | --- |
| Installed payload input | Complete verified advertised payload set plus selected resolution. | Unchanged; becomes the sole historical digest oracle. | `distribution.py`, `PlannerRequest.payloads` | T1 consumes |
| Planner create-only classification | Normalize selected unit and preserve consumer bytes; report new absence. | Additionally compare inspectable current semantic digest with selected and earlier equivalent static unit digests, then add a warning only for an earlier match. | `planner.py::plan_reconciliation` and bounded private helpers | T1 |
| Diagnostic presentation | Sort and serialize `ControlFinding`; validation/check surfaces emit plan findings. | Carry one stable content-safe warning without special-case renderer logic unless a focused presentation test proves it necessary. | `diagnostics.py`, `control_plane/cli.py` | T1 |
| Drift service | Publishes plan actions/findings plus package drift providers. | Exposes the planner warning unchanged. | `mcp_services/providers.py::drift_check` | T1 verifies; modify only if existing projection cannot satisfy the contract |
| Test fixtures | Build integrity-checked payloads and a single-version-per-family resolution. | Represent several advertised versions for one selected family and both artifact/contribution create-only units without hardcoded production families. | `tests/control_plane/planner_helpers.py` | T1 |
| Decision and durable bug | Manual copy and open automation reservation; issue #157 pending. | Permanent no-refresh decision, customized-copy limit, ADR 0024 dependency, and terminal bug lesson. | ADR 0028; bug 006 | T2 |

### 5.2 Content-Match Flow

```text
integrity-verified advertised payloads + selected resolution
                    │
                    ▼
normalize static create-only declarations by
(standard, target, adapter, scope, version, semantic digest)
                    │
repository snapshot ──► selected/materialized create-only unit
                    │
                    ▼
          observed semantic digest
          ├─ equals selected digest ───────────────► silent
          ├─ equals greatest strictly earlier digest ► one warning
          ├─ equals only newer digest ─────────────► silent
          └─ unmatched/customized/absent ──────────► silent here
                    │
                    ▼
sorted ReconciliationPlan.findings
          ├─ project-standards validate
          ├─ reconcile preview/check human + JSON
          └─ MCP drift_check report
```

### 5.3 Change-Surface Matrix

| Surface | Applies? | Invariant / Required Change | Proof | Task |
| --- | --- | --- | --- | --- |
| Behavior | yes | Exact earlier content match warns; current, customized, later-only, absent, and unrelated content do not. | PV-T1-001 | T1 |
| Architecture / dependency direction | yes | Planner consumes the already verified complete payload set and adapter semantics; no family dispatch or new service owns matching. | PV-T1-001 | T1 |
| Public / cross-task interface | yes | One stable warning code/identity/message is projected unchanged to validation and drift reporting. | PV-T1-002 | T1 |
| Data / persistent state | no | No schema, lock, absence, action, or applied-state mutation is introduced. | PV-T1-001 | T1 |
| Configuration | no | No option or command flag selects, suppresses, or refreshes create-only content. | PV-T1-002 | T1 |
| Security / trust | yes | Only verified package sources and content digests are published; raw consumer bytes remain private. | PV-T1-001 | T1 |
| Compatibility / migration | yes | Existing warning-only exit semantics, create-only preservation, absence, and provider-generated behavior remain unchanged. | PV-T1-001, PV-T1-002 | T1 |
| Operations / deployment | no | No rollout or consumer mutation; finish locally. | PV-T2-001 | T2 |
| Documentation / owner truth | yes | ADR 0028 and bug 006 record the settled decision and limitation. | PV-T2-001 | T2 |
| Durable evidence | no | Committed regression tests, ADR, and bug record are repeatable durable proof. | PV-T2-001 | T2 |

### 5.4 Binding Decisions

| ID | Decision | Rationale | Source | Affected Task(s) |
| --- | --- | --- | --- | --- |
| D-001 | Create-only remains permanently non-overwriting; no refresh command or engine write path is added. | Writing consumer-authored content breaks the defining trust boundary and buys only a wrapper around a manual edit that content matching can verify. | issue #157 owner decision | T1–T2 |
| D-002 | Match the current selected semantic unit against equivalent static create-only units from every advertised version of the same package, independent of lock content/version fields. | ADR 0024 makes installed payloads a complete immutable oracle; lock facts record creation/selection, not current content currency. | issue #157; ADR 0024; ADR 0028 | T1 |
| D-003 | Selected match takes precedence; otherwise only a strictly earlier match is stale. Customized/unmatched, later-only, absent, and provider-generated-without-digest cases remain silent. | These are the no-false-positive boundaries required by create-only ownership and the accepted customized-copy limitation. | issue #157 owner decision | T1–T2 |
| D-004 | Emit one `CP-CREATE-ONLY-STALE` warning per semantic address; when several earlier versions share the digest, name the greatest matching earlier version. | One deterministic nearest-version identity avoids duplicate warnings while still comparing the complete permanent catalog. | direct derivation from the owner decision's deterministic advisory requirement | T1 |
| D-005 | Reuse the planner finding stream; do not add a package provider, command, schema, action kind, or lock field. | Validation and drift reporting already consume the same content-safe planner facts, so the change remains read-only and generic. | current planner/CLI/service evidence | T1 |
| D-006 | Amend ADR 0028 and retain bug 006 as a terminal durable lesson. | The settled control-plane boundary and its permanent dependency/limitation must outlive issue comments and ephemeral execution state. | issue #157 acceptance criteria and owner decision | T2 |

## 6. Requirements and Acceptance

| ID | Requirement | Source | Priority | Owner Task | Task(s) | Proof(s) |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-001 | For every selected and materialized static create-only semantic unit, the planner shall compare observed content with the equivalent unit digests available across every advertised version of the same package. | issue #157 owner decision; ADR 0024 | Must | T1 | T1 | PV-T1-001 |
| REQ-002 | A selected-version digest match shall be silent, even if an earlier version has identical bytes; otherwise a strictly earlier match shall emit exactly one warning naming the selected version and greatest matching earlier version. | issue #157 owner decision; D-004 | Must | T1 | T1 | PV-T1-001 |
| REQ-003 | Customized/unmatched, later-version-only, absent, non-materialized, unselected, unrelated-address/package, managed, and provider-generated create-only content without a declared immutable source digest shall emit no stale-content advisory. | issue #157 accepted limitation and no-false-positive boundary | Must | T1 | T1 | PV-T1-001 |
| REQ-004 | The advisory shall use stable code `CP-CREATE-ONLY-STALE`, warning severity, selected standard/version plus target/scope identity, observed and selected digests, content-safe manual-review guidance, deterministic ordering, and no consumer bytes. | issue #157; existing `ControlFinding` contract | Must | T1 | T1 | PV-T1-001, PV-T1-002 |
| REQ-005 | Validation and drift reporting shall both expose the same advisory while remaining read-only and successful when it is the only finding; reconcile applicability, actions, next lock, drift classification, and apply behavior shall remain unchanged. | issue #157; D-005 | Must | T1 | T1 | PV-T1-002 |
| REQ-006 | `CP-CREATE-ONLY-ABSENT`, permanent absence records, create-only preservation, current/customized silence, and all non-create-only behavior shall remain unchanged. | issue #157 out-of-scope list; ADR 0028 | Must | T1 | T1 | PV-T1-001 |
| REQ-007 | ADR 0028 shall reject explicit refresh permanently, accept the customized-copy blind spot, name ADR 0024 permanent advertisement as a reliability dependency, retain manual copy/edit ownership, and direct readers away from the refuted earlier outcome. | issue #157 acceptance criteria and owner decision | Must | T2 | T2 | PV-T2-001 |
| REQ-008 | Durable bug 006 shall record the shipped advisory outcome, remove the pending #157 disposition and obsolete blindness claims, and remain a concise terminal lesson without rewriting unrelated handoff state. | issue #157 acceptance criteria and owner decision | Must | T2 | T2 | PV-T2-001 |
| REQ-009 | The change shall make no package/payload/catalog/release/GitHub mutation and shall finish with the repository's applicable engine, documentation, Agent Handoff, and full local gates green. | issue #157 release boundary; repository instructions | Must | T2 | T2 | PV-T2-001 |

## 7. Verification and Evidence Strategy

- **Authoritative commands:** focused pytest modules for planner, control-plane CLI, and MCP provider services; `uv run ruff format --check src tests`; `uv run ruff check src tests`; `rexec -- uv run basedpyright`; candidate-runtime `uv run project-standards validate`; Agent Handoff validate/drift-check; Git-tracked Prettier and markdownlint; `git diff --check`; and direct-local `scripts/verify.sh --full` after the last content change.
- **Oracles:** the selected payload's normalized semantic unit digest; the same semantic address in integrity-verified installed payloads; `PackageVersion` ordering; ADR 0024 permanent advertisement; existing `ControlFinding` sort/serialization and warning exit semantics.
- **Negative controls:** current bytes also shared by older versions, a unique earlier digest, the same digest in several earlier versions, customized bytes, a digest found only in a later candidate, absent target, changed semantic address, another package, managed policy, static semantic contribution, and provider-generated content without a declared source digest.
- **Test layers:** planner unit/regression, fixture contract, CLI human/JSON integration, top-level validation read-only behavior, MCP drift-report projection/determinism, Agent Handoff/document inspection, and the full repository gate.
- **External environments:** no network, provider service, live consumer, catalog publication, or GitHub mutation. `rexec` is used only for compatible BasedPyright; the Git-dependent repository gate runs directly local.
- **Evidence:** ordinary command output is ephemeral. Committed tests plus ADR 0028 and bug 006 are the durable record; no separate evidence artifact is required.
- **Late failure:** block the owning task. If a completed checkpoint is disproved, append a correction task with `corrects:` and `discovered_from:` and rerun the failed proof; never rewrite completed task history or weaken the trust boundary.

## 8. Execution Summary

| Task | Title | Disposition | Work Type | Phase | Depends On | Requirement(s) | Primary Proof | Parallel / Conflict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T1 | Add the deterministic create-only stale-content advisory | active | brownfield-behavior | P1 | None | REQ-001–REQ-006 | PV-T1-001, PV-T1-002 | no / owns planner and behavior tests |
| T2 | Amend the decision, close bug 006, and verify locally | active | documentation | P2 | T1 | REQ-007–REQ-009 | PV-T2-001 | no / consumes T1 diagnostic contract |

## 9. Implementation Tasks

### Phase P1: Engine Advisory and Behavioral Proof

#### T1: Add the deterministic create-only stale-content advisory

- **disposition:** active
- **outcome:** The generic reconciliation planner emits one content-safe, non-blocking `CP-CREATE-ONLY-STALE` warning only when an observed selected create-only semantic unit exactly matches the equivalent unit from a strictly earlier advertised package version; validation and drift reporting expose the same deterministic result.
- **work_type:** brownfield-behavior
- **checkpoint:** one green commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** []
- **dependency_reason:** none
- **requirements:** [REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006]
- **proof:** [PV-T1-001, PV-T1-002]
- **source_refs:** [issue:L3DigitalNet/project-standards#157, adr:docs/adr/adr-0024-catalog-scoped-package-version-channels.md#catalog-channels, adr:docs/adr/adr-0028-create-only-artifact-refresh.md#amendments, repo:src/project_standards/control_plane/planner.py::plan_reconciliation, repo:src/project_standards/control_plane/planner.py::_read_payload_file, repo:src/project_standards/control_plane/cli.py::validate_repository, repo:src/project_standards/mcp_services/providers.py::drift_check]
- **consumes:** [integrity-verified complete `PlannerRequest.payloads`, selected `ResolutionResult`, one repository snapshot, adapter-normalized selected create-only semantic units, `PackageVersion` ordering]
- **produces:** [create-only-content-advisory-v1, stable `CP-CREATE-ONLY-STALE` diagnostic contract]
- **preserves:** [create-only consumer bytes, `CP-CREATE-ONLY-ABSENT`, lock and action semantics, current/customized silence, provider-generated behavior, selected provider interfaces, deterministic plan ordering]
- **invariants:** [selected digest match is checked before historical matches; matching is confined to the same standard and normalized target/adapter/scope; only static integrity-verified source declarations participate; one advisory names the greatest strictly earlier match; warning-only output never changes drift/applicability/exit; consumer bytes never enter diagnostics]
- **executor_discretion:** [private helper and immutable index types, exact test fixture decomposition, whether existing renderer/service files need code changes after integration tests, and comment placement consistent with the code-comments contract]
- **files:** [`src/project_standards/control_plane/planner.py` (modify; owner T1), `src/project_standards/control_plane/diagnostics.py` (modify only if the existing generic finding contract cannot carry the stable advisory; owner T1), `src/project_standards/control_plane/cli.py` (modify only if existing projection cannot satisfy validation/check output; owner T1), `src/project_standards/mcp_services/providers.py` (modify only if existing drift projection cannot expose the plan finding unchanged; owner T1), `tests/control_plane/planner_helpers.py` (modify; owner T1), `tests/control_plane/test_planner.py` (modify; owner T1), `tests/control_plane/test_cli.py` (modify; owner T1), `tests/mcp_services/test_providers.py` (modify; owner T1)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** Revert the T1 checkpoint as one unit if focused or integrated proof fails; no persistent consumer state is changed. If historical declaration normalization exposes an unsupported consequential case, stop and request the smallest owner decision instead of broadening the advisory or guessing staleness.
- **acceptance:** PV-T1-001 proves exact classification across whole-file and semantic contribution boundaries with no false positives and no write/lock drift; PV-T1-002 proves the same stable warning appears through validation and drift reporting in human/JSON service forms, remains deterministic/read-only, and does not cause a nonzero outcome by itself.
- **sub-tasks:**
  - **T1.1 CHARACTERIZE** — pin existing behavior for selected current, edited/customized, and deleted create-only units, including `PRESERVE`, `CP-CREATE-ONLY-ABSENT`, unchanged next-lock/drift semantics, warning output, and the planner/service finding projection.
  - **T1.2 RED** — extend the generic integrity-checked fixture to advertise at least two versions of one family while selecting the successor; add whole-file and semantic-contribution cases whose repository content exactly matches the predecessor. Expected failure: the plan and validation/drift outputs remain silent because no historical digest comparison exists.
  - **T1.3 Verify RED** — run the focused planner/CLI/service tests and confirm failure is the missing `CP-CREATE-ONLY-STALE` advisory, not fixture resolution, payload integrity, command routing, collection, or environment failure.
  - **T1.4 GREEN** — add the minimum generic planner logic to normalize comparable static create-only declarations across all advertised payloads, apply the binding classification order, and append the content-safe warning to sorted plan findings without changing actions, locks, or provider calls.
  - **T1.5 Verify GREEN** — cover selected-current precedence, nearest earlier version selection when digests repeat, customized/unmatched silence, later-only silence, absent silence beside existing absence behavior, package/address/policy isolation, provider-generated exclusion, whole-file and semantic-contribution matches, stable digests/message/ordering, and unchanged plan/action/lock results.
  - **T1.6 Integration Proof** — prove top-level `project-standards validate`, reconcile human/JSON check output, and MCP drift reporting surface the same warning and stay read-only; repeat identical calls to prove byte-stable structured output and assert advisory-only validation/check exits `0`.
  - **T1.7 REFACTOR** — keep family identity out of the shared control plane, remove duplicate fixture-only mechanics, and add or revise comments only for the permanent-advertisement dependency, selected-before-historical ordering, or confidentiality/no-false-positive invariant; audit every touched comment.
  - **T1.8 Verify Task** — after `scripts/bootstrap-worktree.sh`, run PV-T1-001 and PV-T1-002 focused tests, `uv run ruff format --check src tests`, `uv run ruff check src tests`, `rexec -- uv run basedpyright`, and `git diff --check`; create the required checkpoint only from green output.

### Phase P2: Decision, Durable Bug, and Integrated Checkpoint

#### T2: Amend the decision, close bug 006, and verify locally

- **disposition:** active
- **outcome:** ADR 0028 records permanent create-only/manual ownership and the delivered advisory's accepted limit and ADR 0024 dependency; bug 006 records the terminal fix; the complete repository passes its final local gate with no payload or release mutation.
- **work_type:** documentation
- **checkpoint:** one green documentation/closeout commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** public
- **depends_on:** [T1]
- **dependency_reason:** consumes `create-only-content-advisory-v1` and its observed diagnostic contract so the ADR and durable bug describe delivered, proven behavior rather than a planned mechanism
- **requirements:** [REQ-007, REQ-008, REQ-009]
- **proof:** [PV-T2-001]
- **source_refs:** [issue:L3DigitalNet/project-standards#157, adr:docs/adr/adr-0024-catalog-scoped-package-version-channels.md#catalog-channels, adr:docs/adr/adr-0028-create-only-artifact-refresh.md#amendments, repo:docs/handoff/bugs/006-create-only-artifacts-invisible-to-drift-check.md, repo:docs/handoff/conventions.md]
- **consumes:** [create-only-content-advisory-v1, stable `CP-CREATE-ONLY-STALE` diagnostic contract, ADR 1.5 amendment discipline, Agent Handoff durable-bug ownership]
- **produces:** [amended-create-only-decision-v2, terminal-bug-006-record, local-integrated-validation-receipt]
- **preserves:** [accepted ADR text outside the amendment mechanism, manual-copy ownership, bug history and stable ID/path, unrelated handoff state, payload/catalog/release bytes, GitHub state]
- **invariants:** [ADR rejects refresh rather than leaving it reserved; customized copies are explicitly silent and accepted; advisory reliability explicitly depends on permanent advertisement; a prominent amendment pointer prevents readers from following the refuted delete-and-reconcile outcome; bug closure does not erase the cause or lesson]
- **implementation followed by verification:** update only the ADR and durable bug owner truth, then run reference, handoff, Markdown, candidate-runtime, and full repository verification before the checkpoint
- **executor_discretion:** [exact amendment prose and pointer placement, compact bug wording, and whether a narrowly scoped documentation assertion is useful]
- **files:** [`docs/adr/adr-0028-create-only-artifact-refresh.md` (modify; owner T2), `docs/handoff/bugs/006-create-only-artifacts-invisible-to-drift-check.md` (modify; owner T2), `tests/test_documentation_contract.py` or an existing focused documentation test (modify only if needed to pin a machine-checkable owner-truth invariant; owner T2)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** Revert only T2's documentation checkpoint if wording or final validation fails; T1 remains an independently green behavior checkpoint. Do not edit payload projections or handoff state to silence drift. If the full gate disproves T1, append a correction task against T1, complete it, then rerun T2 proof.
- **acceptance:** PV-T2-001 proves ADR 0028 and bug 006 state the settled outcome without stale/open guidance, Agent Handoff and Markdown checks pass, the candidate runtime validates the repository, the full direct-local gate passes after the last content change, and Git confirms only intended engine/test/ADR/bug paths changed with no payload/catalog/release/GitHub mutation.
- **sub-tasks:**
  - **T2.1 INVENTORY** — reread ADR 0028's accepted outcome/amendment structure, ADR 0024's permanent advertisement clauses, bug 006, T1's final diagnostic output, and repository handoff conventions; identify every obsolete reservation/blindness statement before editing.
  - **T2.2 UPDATE** — append the 2026-08-10 ADR amendment and add the reader-facing pointer permitted by ADR 1.5: create-only remains permanent, explicit refresh and advisory-free variants are rejected, manual copy/edit remains sanctioned, customized copies are intentionally silent, and reliability depends on every advertised immutable payload remaining installed under ADR 0024.
  - **T2.3 UPDATE** — retain bug 006's ID/path and historical cause, but mark the advisory outcome terminal, replace the pending #157 branch and obsolete validate/drift blindness lessons, and name the permanent customized-copy limit and manual remedy.
  - **T2.4 VERIFY REFERENCES** — inspect local links, ADR amendment/frontmatter conformance, bug status/body consistency, and T1's code/tests; assert no language promises refresh, automatic overwrite, lock-based currency, or detection of customized staleness.
  - **T2.5 VERIFY REFERENCES** — run scoped Prettier and markdownlint for the ADR, bug, and plan-referenced documentation; run `project-standards agent-handoff validate --repo .`, `project-standards agent-handoff drift-check --repo .`, and `git diff --check`.
  - **T2.6 Verify Task** — after the last content edit run `scripts/bootstrap-worktree.sh`, candidate-runtime `uv run project-standards validate`, Git-tracked Prettier and markdownlint over their declared scope, and direct-local `scripts/verify.sh --full`. Inspect final status/diff, create the required checkpoint only from green output, and stop; do not cut or publish a package or mutate GitHub.

## 10. Integration, Migration, and Recovery

### 10.1 Integration Sequence

1. T1 characterizes current preservation/absence/output behavior and proves correct-reason RED for the missing historical match.
2. T1 implements and verifies the generic advisory across planner, validation, reconcile check, and drift service boundaries, then commits one green checkpoint.
3. T2 consumes the proven diagnostic contract, amends ADR 0028 and bug 006, validates handoff/documentation, then runs the full local repository gate after all content changes.
4. Stop at the local verified checkpoint. A later release workflow owns versioning, package publication, and GitHub lifecycle state.

### 10.2 State, Compatibility, and Recovery

- Required persistent migration: none. The advisory reads one repository snapshot and immutable installed payload facts and writes nothing.
- Compatibility: warning-only output is additive. Current and customized create-only consumers keep their existing clean behavior; existing absence warnings and all action/lock semantics remain stable.
- Idempotency/determinism: identical installed distribution, configuration, lock, and repository snapshot produce identical findings and no state change.
- Point of no return: none.
- Rollback: revert the T1 advisory checkpoint and T2 owner-truth checkpoint before release, or append a correction task after a completed checkpoint is disproved.
- Recovery proof: PV-T1-001 asserts unchanged actions/next lock and all silent controls; PV-T1-002 asserts read-only repeated presentation; PV-T2-001 proves final repository conformance.

### 10.3 Late Failure and Correction

An unsupported static declaration shape, ambiguous historical equivalence, or false-positive case blocks T1 rather than expanding detection. A material change to the permanent ownership decision returns to issue authority and requires plan revision. A normal implementation defect discovered after T1 creates an append-only correction task that owns the affected paths and reruns T1 proofs before T2 can complete. Final-gate fixes never occur invisibly inside T2 verification.

## 11. Risks, Assumptions, and Open Questions

### 11.1 Risks

| ID | Risk | Likelihood | Impact | Treatment | Owner / Task |
| --- | --- | --- | --- | --- | --- |
| R-001 | Raw artifact digest and adapter semantic digest are conflated, causing semantic contributions to miss or falsely match. | medium | high | Normalize candidate source through the same adapter/scope contract used for current selected units; prove both whole-file and YAML/structured contribution cases. | T1 |
| R-002 | Repeated digests across old and current payloads create duplicate or false stale warnings. | high | high | Bind selected-match precedence, one warning per address, and greatest-earlier-version selection; test duplicate digests explicitly. | T1 |
| R-003 | A later candidate or unrelated package/address is treated as stale evidence. | medium | high | Require same standard/address and strict `historical < selected` ordering; add negative controls. | T1 |
| R-004 | The warning accidentally changes clean exits, drift, next-lock metadata, or apply behavior. | low | high | Assert warning severity and unchanged plan state/exit/read-only snapshots in planner, CLI, and service integration tests. | T1 |
| R-005 | ADR or bug prose promises customized-staleness detection that the engine intentionally cannot provide. | medium | high | State the accepted blind spot explicitly and cross-check docs against current/unmatched negative tests. | T2 |
| R-006 | The historical oracle silently degrades if advertised versions are removed. | low under current policy | high | Name ADR 0024 as a load-bearing dependency in code rationale and ADR 0028; retain release-policy enforcement outside this plan. | T1–T2 |

### 11.2 Assumptions

| ID | Assumption | Impact if False |
| --- | --- | --- |
| A-001 | `PlannerRequest.payloads` continues to contain the complete integrity-verified advertised payload set for the selected catalog major. | Stop T1 and move the oracle to the installed-catalog boundary without adding network/Git/lock authority; amend file claims before implementation. |
| A-002 | Static create-only artifacts and contributions expose immutable declared source bytes that can be normalized through their adapter; provider-generated content without such a digest remains outside reliable comparison. | Keep that declaration silent and return any proposed expansion to owner decision rather than infer a digest. |
| A-003 | A package version strictly lower than the selected resolved version is the repository's authoritative definition of “superseded” for this advisory. | If package lifecycle introduces a non-ordering supersession relation, revise D-004 and the proof matrix before execution. |

### 11.3 Open Questions

None.

## 12. Final Verification

- Every Must requirement maps to T1 or T2 and a passing Appendix B proof; no acceptance is deferred beyond its owner task.
- Correct-reason RED fails only because historical create-only matching is absent. GREEN proves whole-file and semantic-contribution coverage plus all required silent controls.
- `CP-CREATE-ONLY-STALE` identity, severity, standard/version, target/scope, digests, nearest earlier version, hint, ordering, human output, and structured output are deterministic and content-safe.
- Top-level validation, reconcile check, and MCP drift reporting expose the planner warning without repository mutation, nonzero advisory-only exit, action change, next-lock change, or provider refresh behavior.
- `CP-CREATE-ONLY-ABSENT`, current-version silence, customized silence, later-only silence, and every non-create-only path remain compatible.
- ADR 0028 rejects refresh permanently and records the customized-copy limit and ADR 0024 dependency; bug 006 is terminal and no stale guidance remains.
- Candidate-runtime validation, Agent Handoff validation/drift-check, Markdown format/lint, Python format/lint/type checks, targeted tests, and direct-local `scripts/verify.sh --full` pass after the final content change.
- Final Git inspection shows no package payload, catalog, release, generated `.project-pipeline`, unrelated handoff, GitHub, or other out-of-scope mutation.

## 13. Close-out

- **Completed:** pending T1 and T2 checkpoints and final local gate.
- **Decisions / deviations harvested:** ADR 0028 owns the permanent no-refresh decision, customized-copy limit, rejected alternatives, and ADR 0024 dependency. Any material deviation requires owner approval before closeout.
- **Risks closed / accepted:** T1 proof closes false-positive/output risks; ADR 0028 explicitly accepts customized-copy silence and the permanent-advertisement dependency.
- **Deferred/discovered work filed:** package/release/publication/GitHub lifecycle work remains outside this plan. Only genuinely new durable work is filed; no speculative hardening is added.
- **Source/ADR/handoff reconciliation:** T2 updates exactly ADR 0028 and bug 006. Do not rewrite `docs/handoff/state.md`, session logs, status, TODO, or conventions for this bounded outcome.
- **Scratch teardown:** authoring generated no state. During execution, the orchestrator harvests checkpoint evidence and removes only this plan's ephemeral execution state after no irreplaceable information remains.

## Appendix A. Interface and State Contracts

| Contract | Owner / Producer Task | Consumer(s) | Current | Planned / States | Errors / Limits | Compatibility / Invariant | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Historical create-only digest oracle | T1 | planner classification | Complete advertised installed payloads exist but are used only for selection/source reads. | Static create-only declarations normalize by standard + target + adapter + scope + version + semantic digest. | Exclude unverified, provider-generated-without-digest, non-equivalent, or non-materialized current units; never fall back to lock/network/Git. | Every candidate is integrity verified; ADR 0024 permanent advertisement is load-bearing. | ADR 0024; `distribution.py`; `_read_payload_file` |
| Stale-content classification | T1 | diagnostic creation | Every present create-only unit preserves silently. | Selected match → silent; else greatest strictly earlier match → warning; otherwise silent. | At most one warning per current address; missing/uninspectable state stays with existing findings. | Classification never authorizes mutation or claims customized content is current/stale. | issue #157 owner decision; D-003/D-004 |
| `CP-CREATE-ONLY-STALE` finding | T1 | validation, reconcile presentation, MCP drift report, T2 docs | No advisory identity exists. | Warning names selected and nearest earlier matching version; selected standard/version, target/scope, observed/selected digest, and manual-review hint are stable. | No consumer bytes; warning alone does not fail or create drift. | Generic `ControlFinding` sorting/serialization remains the sole presentation contract. | `diagnostics.py`; `cli.py`; issue #157 |
| Create-only state | Existing planner/executor; T1 preserves | reconcile/apply/lock consumers | Present units preserve; deletion records permanent absence; lock retains creation digest. | Unchanged. Advisory is derived read-only state outside actions and lock. | `CP-CREATE-ONLY-ABSENT` remains authoritative for deletion. | No refresh command, action, overwrite, lock rewrite, or resurrection. | ADR 0028; `_is_newly_absent_create_only` |
| Governance record | T2 | maintainers and future agents | ADR reserves automation; bug defers outcome to #157. | ADR permanently rejects refresh and records limitation/dependency; bug records delivered terminal outcome. | Accepted text is amended, not silently rewritten into false history. | Manual copy/edit remains consumer-owned; no package cut. | ADR 0028; bug 006; issue #157 |

## Appendix B. Requirement-to-Proof Traceability

| Proof ID | Requirement(s) | Task | Method | Oracle | Command / Procedure | Expected Result | Negative Control | Environment | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PV-T1-001 | REQ-001, REQ-002, REQ-003, REQ-004, REQ-006 | T1 | focused planner/fixture regression with immutable synthetic payloads | Selected normalized unit digest; integrity-verified same-address payload sources; `PackageVersion` ordering; existing action/lock results | Run focused tests in `tests/control_plane/test_planner.py` and affected helper tests after RED/GREEN. | Unique predecessor bytes yield exactly one `CP-CREATE-ONLY-STALE`; repeated older digests name the greatest earlier version; whole-file and semantic-contribution matches behave identically; selected/current, customized, later-only, absent, unrelated, managed, and provider-generated controls are silent; actions/next lock/absence behavior remain unchanged. | Seed old bytes into a selected successor; then substitute current bytes, arbitrary edited bytes, a future-only digest, missing target, different scope/package, managed policy, and provider-generated source. | isolated local pytest fixtures; no network/provider process required beyond existing fakes | ephemeral |
| PV-T1-002 | REQ-004, REQ-005 | T1 | CLI/service integration and deterministic repeat | Existing `ControlFinding` human/JSON projection, validation warning exit contract, MCP drift plan projection, before/after tree snapshot | Run focused `tests/control_plane/test_cli.py` and `tests/mcp_services/test_providers.py`; invoke identical warning-only validation/check/drift calls twice. | Validation and drift report contain the same stable code/version/path/scope/digests and content-safe guidance; human/JSON ordering is stable; validation/check exit `0`; repository tree, actions, and next lock are unchanged. | Remove the advisory, make it error severity, mutate next lock, include raw bytes, or reorder advertised fixture inputs. | isolated consumer fixture with installed synthetic distribution | ephemeral |
| PV-T2-001 | REQ-007, REQ-008, REQ-009 | T2 | owner-truth inspection plus repository gates | Issue #157 owner decision; ADR 0024/0028 amendment contracts; Agent Handoff validators; repository gate | Run scoped and Git-tracked Prettier/markdownlint, `project-standards agent-handoff validate --repo .`, `project-standards agent-handoff drift-check --repo .`, `git diff --check`, `scripts/bootstrap-worktree.sh`, candidate-runtime `uv run project-standards validate`, and direct-local `scripts/verify.sh --full`; inspect final Git diff/name-status. | ADR and bug state the settled outcome/limit/dependency with no stale reservation; all checks pass; only T1/T2-owned engine, test, ADR, and bug paths differ; no payload/catalog/release/pipeline/GitHub mutation exists. | Search for the old pending #157 language, automated-path reservation, delete-and-reconcile guidance without amendment pointer, and claims that customized staleness is detectable; fail on any match that remains authoritative. | local Git checkout; full gate direct because it reads Git; compatible BasedPyright already proved through rexec in T1 | ephemeral |

## Appendix D. Deferred Work

| Item | Reason Deferred | Follow-up / Reopen Trigger |
| --- | --- | --- |
| Package release, payload cut, catalog mutation, publication, and GitHub issue transition | The owner classified this as engine-only with no payload cut; this plan is limited to implementation, durable owner truth, and a local verified checkpoint. | A separately authorized release/lifecycle workflow consumes T2's green checkpoint. |
