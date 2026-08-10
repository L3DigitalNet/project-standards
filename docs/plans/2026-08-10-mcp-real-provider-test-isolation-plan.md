---
plan_format: 3
title: 'MCP Real Provider Test Isolation Implementation Plan'
slug: 'mcp-real-provider-test-isolation'
status: active
revision: 1
revises_revision: 0
revision_reason: 'initial plan for issue #158'
pause_reason: ''
source: 'issue #158 owner decision and measured local gate evidence'
spec_ref: ''
created: 2026-08-10
updated: 2026-08-10
owners:
  - 'Chris Purcell / L3DigitalNet'
  - 'Coding agent under human review'
---

# MCP Real Provider Test Isolation Implementation Plan

> **Definition, not state.** Authoring drafts live in `.project-pipeline/2026-08-10-mcp-real-provider-test-isolation/authoring/`; generated execution status and evidence pointers live in `.project-pipeline/2026-08-10-mcp-real-provider-test-isolation/execution/`.

## 1. Objective

Make the two real-package composite MCP regression tests deterministic when the fast gate saturates the worker, without changing the production provider execution contract. Each named test injects a generous, finite 400-second provider deadline, so it retains its real provider/process coverage and exceeds the 356-second starvation outlier with margin while remaining finite. This child plan ends at a verified local correction checkpoint; the parent v5.19 release work retains its ten-consecutive ordinary-lane evidence and issue closure.

## 2. Authority and Source Map

| Source | Source Role | Authority / Use | Version / Date | Affected Plan Surface |
| --- | --- | --- | --- | --- |
| `issue:L3DigitalNet/project-standards#158` | normative | Test-only finite injection in exactly the two named tests; no production timeout, boundary-proof, ADR, or payload change | owner decision 2026-08-10 | §§1, 3, 5–7; T1 |
| `request` | operational evidence | Owner-supplied clean-tree and loaded-fast-gate measurements: 15 calls topped out at 7.901s; two loaded failures isolated to the composite test; prior starvation outliers were 244–356s | observed 2026-08-10 | §§1, 4, 7, 9; T1 |
| `repo:src/project_standards/mcp_services/providers.py::PROVIDER_TIMEOUT_SECONDS` | current-state evidence | Production default is 30 seconds and is read at invocation time | `ff894721` | §§3–5; T1 |
| `repo:tests/mcp_services/test_providers.py::test_composite_dispatch_input_matches_authoritative_direct_dispatch` | current-state evidence | Real-package composite/direct-dispatch oracle and empty-input negative control | `ff894721` | §§4–7; T1 |
| `repo:tests/mcp_services/test_providers.py::test_real_packaged_provider_validates_real_consumer_root` | current-state evidence | Real consumer-root, completion, drift-check, and read-only oracle | `ff894721` | §§4–7; T1 |
| `repo:tests/mcp_services/test_provider_worker.py` | current-state evidence | Dedicated timeout and termination proofs inject their own bounds | `ff894721` | §§3, 6–7; T1 |
| `repo:tests/mcp_services/test_providers.py` | current-state evidence | Dedicated timeout and termination proofs inject their own bounds | `ff894721` | §§3, 6–7; T1 |
| `repo:scripts/verify.sh` | current-state evidence | Fast gate executes the ordinary suite concurrently and has a serial performance tail | `ff894721` | §§4, 7, 9; T1 |

Conflict precedence: the explicit owner decision fixes the target and scope. Measurements establish the chosen test ceiling; existing code and tests establish only the starting behavior and preservation obligations.

## 3. Scope, Boundaries, and Constraints

### 3.1 In Scope

- Add test-local `monkeypatch` injection of `providers.PROVIDER_TIMEOUT_SECONDS = 400.0` in exactly `test_composite_dispatch_input_matches_authoritative_direct_dispatch` and `test_real_packaged_provider_validates_real_consumer_root`.
- Preserve the two tests' existing real packaged distribution, provider, direct-dispatch, drift-check, mutation-control, and read-only assertions.
- Prove focused behavior, the dedicated timeout-boundary coverage, and a corrected local fast gate; leave concise evidence for the parent release's subsequent ordinary-lane accumulation.

### 3.2 Out of Scope and Deferred

- Changing the production `PROVIDER_TIMEOUT_SECONDS = 30` default, provider worker behavior, termination grace, public interface, ADR, standard payload, or catalog.
- Changing any dedicated timeout, SIGTERM/SIGKILL, cancellation, or worker-boundary proof.
- Requiring ten ordinary lanes before this correction checkpoint, holding the correction uncommitted while they accrue, publishing a release, or closing issue #158. The parent v5.19 release work owns those actions and evidence.

### 3.3 Ownership and Preserved Behavior

| Boundary | Owner / Responsibility |
| --- | --- |
| Plan owns | Test-only injection and local correction proof in `tests/mcp_services/test_providers.py` |
| Depends on | Existing call-time injection seam, real packaged runtime, and fast-gate orchestration |
| Does not own | Production provider execution, release qualification, issue lifecycle, ADRs, and payloads |
| Must preserve | 30-second production default; all dedicated timeout tests; both named tests' existing authoritative and no-write oracles |

### 3.4 Binding Decision

Use `400.0` seconds as the test-only ceiling. It is finite and exceeds the 356-second prior starvation outlier by about 12 percent, which is the relevant upper-bound evidence for a test intended to survive saturated-worker scheduling. The clean-tree measurement confirms the healthy provider work itself is far smaller: 15 calls topped out at 7.901 seconds (`cli-documentation/verify`); the other verify calls took 7.763, 7.804, 7.820, and 7.833 seconds, and the remaining calls took 0.993–1.190 seconds. The executor may use the existing imported provider module or the repository-conforming local import needed to patch it, but must inject only in the two named test functions. The production `30` remains exact and is not a comparator for this test-only scheduling ceiling.

## 4. Current State and Target State

### 4.1 Current State

`providers.py` exports a module-global `PROVIDER_TIMEOUT_SECONDS: float = 30` and passes its call-time value to `_run_worker`. The two named tests exercise all applicable shipping providers against this repository's real packaged distribution. On a clean, unloaded integrated tree they complete in 98.62 and 57.37 pytest seconds, respectively. Under the concurrent fast gate, two observed failures isolated to the composite test; isolated reruns passed, while historical saturation starvation lasted 244–356 seconds. The dedicated timeout tests already use local injections selected for their boundary or hazard assertions.

### 4.2 Target State

Only the two long-running real-package tests patch the call-time global to `400.0` before invoking the facade. The production module remains at 30 seconds, every dedicated boundary test remains unchanged, and the tests continue to distinguish authoritative input from empty input and composite read-only behavior. A local fast-gate correction checkpoint is green; later normal ordinary-lane gates supply release evidence without delaying this checkpoint.

### 4.3 Delta Summary

| Area | Current | Target | Must Preserve |
| --- | --- | --- | --- |
| Test scheduling isolation | Real-package calls inherit the 30-second production bound | Two named tests use a finite 400.0-second local bound | Real-provider execution and all existing assertions |
| Production behavior | 30-second call-time default | Unchanged | Provider timeout, worker lifecycle, and public behavior |
| Boundary proofs | Dedicated tests set their own bounds | Unchanged | Exact timeout/termination semantics and coverage |
| Release evidence | Two load-only failures; isolated reruns pass | Local correction checkpoint, then parent accumulates normal lanes | Ten-consecutive evidence remains a parent release criterion |

## 5. Change Surface and Architecture

| Surface | Planned Change | Preserved Contract | Owning Task |
| --- | --- | --- | --- |
| Test-local scheduling | Patch the call-time timeout seam to `400.0` inside exactly two real-package tests | Provider selection, process execution, and the tests' existing semantic oracles | T1 |
| Production provider service | No source change | `PROVIDER_TIMEOUT_SECONDS: float = 30` and worker timeout/termination behavior | T1 preservation proof |
| Dedicated boundary coverage | No test change | Existing local injections and timeout/termination assertions remain authoritative | T1 preservation proof |
| Gate execution | Run the repository fast gate directly in the local checkout | The gate reads Git history, index, and tracked corpus; rexec v0.2 synchronizes no Git metadata, so it must not run remotely | T1 |

## 6. Requirements and Acceptance

| ID | Requirement | Source | Priority | Owner Task | Task(s) | Proof(s) |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-001 | Exactly the two named real-package tests inject a finite 400.0-second provider timeout before their facade calls. | `issue:L3DigitalNet/project-standards#158` | Must | T1 | T1 | PV-T1-001 |
| REQ-002 | Production 30-second behavior and dedicated timeout/termination proofs remain unchanged. | `issue:L3DigitalNet/project-standards#158` | Must | T1 | T1 | PV-T1-002 |
| REQ-003 | The local correction ends with focused tests and the ordinary fast gate green; future ordinary-lane evidence is accumulated by the parent release without withholding this checkpoint. | `issue:L3DigitalNet/project-standards#158` | Must | T1 | T1 | PV-T1-003 |

## 7. Verification and Evidence Strategy

- **Correct-reason RED:** retain the two observed fast-gate failures where only `test_composite_dispatch_input_matches_authoritative_direct_dispatch` failed under load, contrasted with passing isolated reruns. They show saturation/starvation at the test's inherited unbounded-for-test production deadline, rather than an assertion or functional-provider defect. Do not manufacture a new failing production-timeout test or weaken an oracle.
- **Focused proof:** after the test-only edit, run both exact nodes with the extracted candidate runtime and confirm their existing direct-dispatch, empty-input, real-root completion, drift-check, and no-write assertions pass.
- **Preservation proof:** inspect the production constant remains `30`; run the dedicated provider-worker and provider timeout/termination selections unchanged, so a broad monkeypatch or altered boundary expectation is rejected.
- **Gate proof:** after `scripts/bootstrap-worktree.sh` establishes a current candidate runtime, run `scripts/verify.sh` directly in the local checkout and require exit 0. The gate reads Git history, index, and tracked corpus; rexec v0.2 synchronizes no Git metadata, so the full gate is not remotely runnable. The full serial battery is release-prep work, not a prerequisite of this child correction checkpoint.
- **Future evidence:** parent v5.19 records each subsequent normal ordinary-lane result and evaluates its existing ten-consecutive/issue-closure criterion. This plan records the local correction result only and neither resets nor substitutes for that series.
- **Evidence retention:** repeatable local output is ephemeral and belongs in the task checkpoint/checklist; no durable evidence artifact is required.

## 8. Execution Summary

| Task | Title | Disposition | Work Type | Phase | Depends On | Requirement(s) | Primary Proof | Parallel / Conflict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T1 | Isolate real-package provider tests with a finite local timeout | active | behavior | P1 | None | REQ-001, REQ-002, REQ-003 | PV-T1-001 | no / `tests/mcp_services/test_providers.py` |

## 9. Implementation Tasks

### Phase P1: Test-only correction

#### T1: Isolate real-package provider tests with a finite local timeout

- **disposition:** active
- **outcome:** the two named real-package tests alone inject a 400.0-second bound, remain authoritative end-to-end tests, and pass both focused and local-fast-gate proof without changing production or boundary-test semantics.
- **work_type:** behavior
- **checkpoint:** one green commit with the required `Plan-*` checkpoint trailers
- **boundary:** internal
- **depends_on:** []
- **dependency_reason:** none
- **requirements:** [REQ-001, REQ-002, REQ-003]
- **proof:** [PV-T1-001, PV-T1-002, PV-T1-003]
- **source_refs:** [issue:L3DigitalNet/project-standards#158, repo:src/project_standards/mcp_services/providers.py::PROVIDER_TIMEOUT_SECONDS, repo:tests/mcp_services/test_providers.py::test_composite_dispatch_input_matches_authoritative_direct_dispatch, repo:tests/mcp_services/test_providers.py::test_real_packaged_provider_validates_real_consumer_root, repo:scripts/verify.sh]
- **files:** [`tests/mcp_services/test_providers.py` (modify; owner T1)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** restore the sole test file to the last green checkpoint; if the selected ceiling proves insufficient or masks a distinct functional failure, stop and return to the owner rather than changing production behavior or widening test scope.
- **acceptance:** PV-T1-001 proves only the two named tests patch the 400.0-second call-time seam and retain their existing real-provider oracles; PV-T1-002 proves the production 30-second default and dedicated boundary proofs are untouched; PV-T1-003 proves both focused nodes and the local fast gate exit 0, with later ordinary-lane results recorded by the parent rather than made a checkpoint blocker.
- **sub-tasks:**
  - **T1.1 RED** — attach the two recorded loaded fast-gate failures and successful isolated reruns to the task evidence. Confirm their failure locus is the composite test under load, not an assertion regression; this is the correct-reason RED for the inherited test deadline.
  - **T1.2 Verify RED** — confirm the recorded failures are the correct-reason symptom: only the composite node fails under loaded fast-gate scheduling while isolated reruns pass, not because an assertion, provider result, or production timeout contract changed.
  - **T1.3 PRECHECK** — inspect the current `30` production constant, both named test bodies, and dedicated timeout/termination tests. Confirm that no other test will receive the new injection.
  - **T1.4 GREEN** — add a `monkeypatch` parameter and set the provider module's timeout to `400.0` inside exactly the two named test functions before their facade calls. Do not alter assertions, test selection, production code, ADRs, or dedicated boundary tests.
  - **T1.5 Verify GREEN** — run both exact tests against the current extracted candidate runtime and verify the authoritative direct-dispatch/empty-input and real-root completion/drift/no-write assertions remain active and pass.
  - **T1.6 Verify preservation** — inspect the production constant and run the existing dedicated timeout/termination test selections without modifying their injected values; reject a change to the 30-second default, shared fixture, or boundary proof.
  - **T1.7 Verify Task** — bootstrap the worktree if needed, run PV-T1-001 through PV-T1-003, inspect the final diff for the sole test-file change, and create the required local correction checkpoint. Hand the checkpoint/result to the parent release work for normal ordinary-lane accumulation; do not wait for ten gates or mutate issue state.

## 10. Integration, Migration, and Recovery

There is no persistent state, migration, interface rollout, or generated execution state in this correction. The sole test-file edit is reverted to the prior green checkpoint if focused proof or the local fast gate fails. A later release-lane failure appends a correction task under the parent plan; it does not rewrite a completed T1 definition.

## 11. Risks, Assumptions, and Open Questions

### 11.1 Risks

| ID | Risk | Likelihood | Impact | Treatment | Owner / Task |
| --- | --- | --- | --- | --- | --- |
| R-001 | A ceiling selected from unloaded measurements could be too small under a materially different worker load. | low | medium | 400.0 seconds exceeds the observed 356-second starvation outlier by about 12 percent; stop for owner direction if it fails rather than raising production/default scope. | T1 |
| R-002 | A broad fixture/module patch could unintentionally change timeout-boundary proof meaning. | low | high | Patch locally in exactly the two named tests and run dedicated boundary selections unchanged. | T1 |
| R-003 | A green local fast gate could be mistaken for the parent release's longitudinal evidence. | medium | medium | Explicitly hand future normal-lane recording and ten-consecutive evaluation to the parent release work. | Parent v5.19 |

### 11.2 Assumptions

| ID | Assumption | Impact if False |
| --- | --- | --- |
| A-001 | The observed 356-second starvation outlier is a suitable upper-bound basis for the 400.0-second test-only ceiling. | The owner must select a different finite test-only value; do not alter production behavior. |

## 12. Final Verification

- REQ-001 through REQ-003 map to T1 and pass PV-T1-001 through PV-T1-003.
- The final diff modifies only `tests/mcp_services/test_providers.py`; each injection is inside one of the two named tests and uses 400.0 seconds.
- `src/project_standards/mcp_services/providers.py` retains `PROVIDER_TIMEOUT_SECONDS: float = 30`; dedicated timeout/termination proofs remain unchanged and pass.
- The two exact real-package tests and local `scripts/verify.sh` exit 0 on the current candidate runtime.
- The correction is committed with the required task checkpoint trailers. The parent release receives the checkpoint and continues its own normal ordinary-lane evidence, release, and issue-close work.

## 13. Close-out

- **Completed:** pending T1 local correction checkpoint.
- **Decisions / deviations harvested:** 400.0-second test-only ceiling; no production or boundary-proof change.
- **Deferred/discovered work filed:** parent v5.19 owns future ordinary-lane evidence, release publication, and issue #158 closure.

## Appendix B. Requirement-to-Proof Traceability

| Proof ID | Requirement(s) | Task | Method | Oracle | Command / Procedure | Expected Result | Negative Control | Environment | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PV-T1-001 | REQ-001 | T1 | Focused integration regression | The existing direct-dispatch result equality, empty-input divergence, completion, drift, and read-only assertions | Run the two exact nodes in `tests/mcp_services/test_providers.py` against the current extracted candidate runtime | Both nodes exit 0 with their existing real-package assertions intact; only the two named functions set `400.0` | Empty input must still diverge, and a third test must not receive the injected ceiling | Local candidate runtime | ephemeral |
| PV-T1-002 | REQ-002 | T1 | Characterization and focused regression | Production module declaration and the dedicated timeout/termination tests' existing selected bounds | Inspect `providers.py`; run the existing dedicated timeout/termination selections from the two provider suites without edits | Production default remains exactly `30`; dedicated boundary tests pass with their own bounds | A changed default, shared fixture injection, or changed dedicated bound fails inspection or focused regression | Local candidate runtime | ephemeral |
| PV-T1-003 | REQ-003 | T1 | Local integration gate | `scripts/verify.sh` ordinary-lane orchestration plus the focused-node results | Run `scripts/bootstrap-worktree.sh` as needed, then run local `scripts/verify.sh` | Focused tests and the local fast gate exit 0; checkpoint is committed and handed to the parent for later normal-lane accumulation | A passing isolated rerun without a green fast gate, or treating this one gate as ten consecutive lanes, does not satisfy the proof | Local checkout with its current Git history, index, and tracked corpus | ephemeral |
