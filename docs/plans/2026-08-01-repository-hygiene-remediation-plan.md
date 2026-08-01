---
title: 'Repository Hygiene Remediation Implementation Plan'
slug: 'repository-hygiene-remediation'
size: standard
status: active
source: 'docs/reviews/2026-08-01-repository-hygiene-maintenance-review.md; owner authorization 2026-08-01'
spec_ref: ''
created: 2026-08-01
updated: 2026-08-01
owners:
  - 'Chris Purcell / L3DigitalNet'
test_framework: pytest
---

# Repository Hygiene Remediation Implementation Plan

> **This file is definition, not state.** Live progress belongs under `.project-pipeline/2026-08-01-repository-hygiene-remediation/`.

## 1. Objective

Correct every repository finding and both behavior-preserving simplifications approved in the 2026-08-01 hygiene review, restore one coherent 5.14 release candidate, and preserve immutable package history and consumer-owned state.

## 2. Background

The review found three high, five medium, and two low repository findings. The root catalog/lock lineage is inconsistent; public release guidance and retained lifecycle documents drift; the local gate does not reuse its exact wheel; Node/action maintenance is incomplete; mutable files carry unnecessary executable modes; and two repeated Python primitives have safe consolidation paths.

## 3. Scope

### 3.1 In Scope

- HYG-001 through HYG-010 and S-001/S-002 from the source review.
- A 5.14.0 local release-preparation candidate and dogfood reconciliation.
- Four merged local-branch deletions and ordinary Git maintenance after repository verification.

### 3.2 Out of Scope

- Push, tag, GitHub release, issue mutation, or external publication.
- Provider-input retirement, immutable predecessor rewrites, and mass historical-document cleanup.
- Deleting active `.scratch` or `.project-pipeline` evidence before its owning work closes.

### 3.3 Assumptions

- The owner's “Correct all” authorizes the policy choices in HYG-003, HYG-006, HYG-007, and HYG-009.
- The same authorization explicitly approves one combined 5.14 correction train rather than publishing the lineage repair before HYG-010/S-001/S-002, and approves deletion of the four review-identified merged branches plus ordinary non-aggressive Git maintenance after fresh proof.
- `5.14.0` is the next minor release because Agent Handoff 1.8 advances a standard package.

### 3.4 Constraints

- Use RED-GREEN-REFACTOR for code and executable-policy changes.
- Never hand-edit `.standards/lock.toml` or alter advertised predecessor payload bytes.
- Release preparation runs only from clean local `main`; no remote mutation is authorized.
- Preserve unrelated and consumer-owned content.

## 4. Requirements and Traceability

| ID | Requirement | Source | Priority | Task(s) | Verified by |
| --- | --- | --- | --- | --- | --- |
| REQ-001 | Reconcile maintained lifecycle documents and remove competing stale authority. | HYG-003, HYG-005, HYG-006 | must | T1 | TC-T1-001 |
| REQ-002 | Make the local gate reuse one exact candidate wheel and test its orchestration. | HYG-004, HYG-008 | must | T2 | TC-T2-001 |
| REQ-003 | Add recurring npm maintenance and immutable external-action pins. | HYG-007, HYG-009 | must | T3, T9 | TC-T3-001, TC-T9-001 |
| REQ-004 | Remove accidental executable modes only from mutable files and prevent recurrence. | HYG-010 | must | T4 | TC-T4-001 |
| REQ-005 | Consolidate Agent Handoff optional reads without changing security semantics. | S-001 | should | T5 | TC-T5-001 |
| REQ-006 | Consolidate adapter newline/offset helpers with byte-layout parity. | S-002 | should | T6 | TC-T6-001 |
| REQ-007 | Prepare 5.14.0, restore released lineage, reconcile dogfood, and align README. | HYG-001, HYG-002 | must | T7 | TC-T7-001 |
| REQ-008 | Complete verification and safe local repository cleanup without deleting active evidence. | J-001, J-002, J-003 | should | T8 | TC-T8-001 |

## 5. Repository Context

### 5.1 Relevant Components

| Component | Purpose | Paths |
| --- | --- | --- |
| Lifecycle docs | Current specs/plans and navigation | `docs/specs/`, `docs/plans/`, `docs/handoff/specs-plans.md` |
| Release control | Version, catalog, lock, public guidance | `pyproject.toml`, `CHANGELOG.md`, `.standards/`, `README.md` |
| Verification | Local/hosted candidate evidence | `scripts/verify.sh`, `tests/package_compatibility/`, `.github/workflows/` |
| Python boundaries | Handoff and structured adapters | `src/project_standards/agent_handoff/`, `src/project_standards/control_plane/adapters/` |

### 5.2 Existing Behavior

Package, schema, projection, dependency, formatting, lint, and type checks pass. Root reconcile and root-dependent validation fail because the catalog advanced without its lock. The pushed testing workflow also rejects the unchanged 5.13.0 release identity.

### 5.3 Expected File Changes

| Path | Action | Purpose | Task |
| --- | --- | --- | --- |
| `docs/plans/2026-07-09-agent-handoff-standard-package.md` | delete | retire competing completed plan | T1 |
| `docs/specs/**`, `docs/handoff/specs-plans.md` | modify | lifecycle and link accuracy | T1 |
| `scripts/verify.sh`, `tests/test_repository_test_gate.py` | modify | exact-wheel local gate | T2 |
| `.github/dependabot.yml`, `.github/workflows/*.yml`, tests | modify | dependency/action policy | T3 |
| mutable mode-bearing files and mode test | modify | executable-mode hygiene | T4 |
| Agent Handoff and adapter modules/tests | modify | safe simplifications | T5, T6 |
| release/catalog/lock/README/changelog surfaces | modify | 5.14 candidate and dogfood refresh | T7 |
| three managed workflow package successors and projections | add/modify | make action pins authoritative payload content | T9 |

### 5.4 Dependencies

No new runtime or development dependency is planned.

## 6. Test Strategy

- **Framework:** pytest through uv; configuration in `pyproject.toml`; tests under `tests/`.
- **Commands:** targeted `uv run pytest {path}`; statics `uv run ruff check .`, `uv run ruff format --check .`, `uv run basedpyright`.
- Documentation uses Prettier, markdownlint, and applicable project validators.
- Release qualification uses a fresh extracted candidate wheel and `scripts/verify.sh --full` only after the last content change.

### 6.1 RED-GREEN-REFACTOR contract

Each executable change receives a failing observable regression, verified for the intended reason, then the smallest implementation, targeted verification, behavior-preserving cleanup, and task gate. Documentation/release/operational tasks use the stated objective validation as a TDD exception.

## 7. Execution Summary

| Task | Title | Phase | Depends on | Requirement(s) | Primary verification |
| --- | --- | --- | --- | --- | --- |
| T1 | Reconcile lifecycle documentation | P1 | None | REQ-001 | doc and plan validation |
| T2 | Reuse the exact wheel in the local gate | P1 | None | REQ-002 | repository-gate tests |
| T3 | Harden dependency and action maintenance | P1 | None | REQ-003 | workflow-policy tests |
| T4 | Normalize mutable executable modes | P1 | None | REQ-004 | mode-policy test |
| T5 | Share Agent Handoff optional reads | P2 | T1 | REQ-005 | Agent Handoff tests |
| T6 | Share adapter text primitives | P2 | T2 | REQ-006 | adapter tests |
| T7 | Prepare and reconcile 5.14.0 | P3 | T1, T2, T3, T4, T5, T6, T9 | REQ-007 | release/full gate |
| T8 | Close verification and local cleanup | P3 | T7 | REQ-008 | parity and hygiene inspection |
| T9 | Author managed workflow successors | P2 | T3, T4 | REQ-003 | package/control-plane gates |

## 8. Implementation Tasks

### Phase P1: Repository Policy and Documentation

#### T1: Reconcile lifecycle documentation

- **goal:** one current execution authority and no maintained stale lifecycle links · **depends_on:** [] · **requirements:** [REQ-001] · **priority:** must
- **files:** stale Agent Handoff plan (delete), maintained specs/indexes/handoff pointers (modify)
- **acceptance:** T32 receives the remaining retirement pointer; the obsolete plan is removed; SPEC-VAIC links durable completion evidence; SPEC-RD01 receives a controlled successor revision with revision-history/frontmatter updates, preserved historical sequencing, shipped read-only delivery, and still-deferred controlled-write/remote phases (TC-T1-001)
- **sub-tasks:**
  - **T1.1 RED** — add/extend documentation lifecycle assertions; expected failure is the stale plan/link/roadmap state.
  - **T1.2 Verify RED** — run the focused documentation tests; failure is the intended drift.
  - **T1.3 GREEN** — apply the smallest lifecycle/document changes, re-lock SPEC-RD01 through its established revision procedure, and delete the completed plan.
  - **T1.4 Verify GREEN** — focused tests plus Prettier, markdownlint, revision-history/frontmatter parity, and plan/spec validation.
  - **T1.5 REFACTOR** — remove duplicate lifecycle wording only where authority remains clear.
  - **T1.6 Verify Task** — documentation tests and gates; commit with IDs.

#### T2: Reuse the exact wheel in the local gate

- **goal:** ordinary and compatibility lanes validate one prepared candidate artifact · **depends_on:** [] · **requirements:** [REQ-002] · **priority:** must
- **files:** `scripts/verify.sh`, `tests/test_repository_test_gate.py`
- **acceptance:** zero/multiple wheels fail before lanes; one absolute resolved wheel is exported to compatibility; fast/full ordering is preserved; a failing lane produces a nonzero aggregate exit while all intended lane results are reported (TC-T2-001)
- **sub-tasks:**
  - **T2.1 RED** — add hermetic gate-policy/orchestration tests for zero/one/multiple wheels, absolute compatibility export, fast/full ordering, and aggregate failure; expected failures are the absent selection/export and uncovered shell orchestration.
  - **T2.2 Verify RED** — focused tests fail for the missing local behavior.
  - **T2.3 GREEN** — select/export the exact prepared wheel in `verify.sh`.
  - **T2.4 Verify GREEN** — focused policy and smoke orchestration tests pass.
  - **T2.5 REFACTOR** — share wheel selection without changing lane behavior.
  - **T2.6 Verify Task** — focused tests, `bash -n`, Ruff, and BasedPyright; commit with IDs.

#### T3: Harden dependency and action maintenance

- **goal:** recurring npm updates/audit and immutable external-action references · **depends_on:** [] · **requirements:** [REQ-003] · **priority:** must
- **files:** `.github/dependabot.yml`, `.github/workflows/*.yml`, workflow-policy tests
- **acceptance:** npm Dependabot is configured; Check runs `npm audit --package-lock-only`; every external action step is SHA-pinned with a version comment (TC-T3-001)
- **sub-tasks:**
  - **T3.1 RED** — add workflow/dependabot policy tests; expected failure is current missing npm lane/audit and mutable action tags.
  - **T3.2 Verify RED** — focused tests fail only on those policies.
  - **T3.3 GREEN** — add the npm lane/audit and verified action SHAs.
  - **T3.4 Verify GREEN** — workflow tests and live read-only audits pass.
  - **T3.5 REFACTOR** — normalize comments without changing workflow triggers or permissions.
  - **T3.6 Verify Task** — workflow tests, YAML/Markdown gates, and dependency audits; commit with IDs.

#### T4: Normalize mutable executable modes

- **goal:** mutable Python/Markdown resources are non-executable while immutable history remains untouched · **depends_on:** [] · **requirements:** [REQ-004] · **priority:** must
- **files:** mutable mode-bearing files and repository hygiene test
- **acceptance:** every anchor `100755` path is classified into an explicit executable allowlist, mutable normalization allowlist, or immutable/projection exclusion before editing; mutable non-shebang source/resources are `100644`; advertised version directories remain byte/mode identical (TC-T4-001)
- **sub-tasks:**
  - **T4.1 RED** — inventory every anchor `100755` path, freeze the three-way classification, and add a Git-mode policy test; expected failure lists only the explicit mutable normalization allowlist.
  - **T4.2 Verify RED** — focused test fails for executable mutable files.
  - **T4.3 GREEN** — change only authorized mutable modes.
  - **T4.4 Verify GREEN** — mode test and predecessor-byte checks pass.
  - **T4.5 REFACTOR** — none.
  - **T4.6 Verify Task** — focused/package checks and diff inspection; commit with IDs.

### Phase P2: Behavior-Preserving Simplification

#### T5: Share Agent Handoff optional reads

- **goal:** one secure optional-read primitive with unchanged absent/error behavior · **depends_on:** [T1] · **requirements:** [REQ-005] · **priority:** should
- **files:** Agent Handoff paths/planning/validation modules and path tests
- **acceptance:** present and absent paths behave identically; repository-boundary/read failures still propagate (TC-T5-001)
- **sub-tasks:**
  - **T5.1 RED** — characterize present, absent, and rejected paths before extraction.
  - **T5.2 Verify RED** — characterization passes and mutation check shows duplicate replacement would be caught.
  - **T5.3 GREEN** — move the exact helper to `paths.py` and update both consumers.
  - **T5.4 Verify GREEN** — path, planning, and validation tests pass.
  - **T5.5 REFACTOR** — remove only the two duplicate definitions/import noise.
  - **T5.6 Verify Task** — Agent Handoff tests, Ruff, BasedPyright; commit with IDs.

#### T6: Share adapter text primitives

- **goal:** one owner for newline and line-start calculations with exact byte-layout parity · **depends_on:** [T2] · **requirements:** [REQ-006] · **priority:** should
- **files:** adapter base/five adapters and adapter-base tests
- **acceptance:** LF, CRLF, no-newline, mixed-ending, and offset cases preserve current results; all adapter suites remain byte-exact (TC-T6-001)
- **sub-tasks:**
  - **T6.1 RED** — characterize shared newline/offset behavior, including mixed endings.
  - **T6.2 Verify RED** — characterization passes and direct shared API expectation is absent.
  - **T6.3 GREEN** — add base helpers and replace seven local copies.
  - **T6.4 Verify GREEN** — base and five adapter suites pass.
  - **T6.5 REFACTOR** — remove obsolete helpers/imports only.
  - **T6.6 Verify Task** — adapter tests, Ruff, BasedPyright; commit with IDs.

### Phase P3: Release Reconciliation and Closeout

#### T7: Prepare and reconcile 5.14.0

- **goal:** one clean 5.14.0 candidate whose public docs, catalog, lock, managed registrations, and release classification agree · **depends_on:** [T1, T2, T3, T4, T5, T6, T9] · **requirements:** [REQ-007] · **priority:** must
- **files:** release metadata, README, catalog/lock, managed harness registrations, changelog
- **acceptance:** exact v5.13 catalog lineage is restored before candidate reconcile; 5.14 candidate preview/apply converges; README installs 5.14 and names AH 1.8; full source/candidate/package/release gates pass (TC-T7-001)
- **sub-tasks:**
  - **T7.1 RED** — retain the current CP-CONTROL-STATE and PC-RELEASE-LEVEL evidence.
  - **T7.2 Verify RED** — confirm lineage/version causes, not payload mutation.
  - **T7.3 GREEN** — promote clean local work to `main`, run release prep, restore catalog from v5.13.0, build candidate, preview/apply reconcile, and align release docs.
  - **T7.4 Verify GREEN** — second reconcile no-op; Agent Handoff validate/drift and release classification pass.
  - **T7.5 REFACTOR** — generated normalization only.
  - **T7.6 Verify Task** — fresh exact candidate, `scripts/verify.sh --full`, package/doc/release gates; commit with IDs.

#### T8: Close verification and safe local cleanup

- **goal:** verified clean local branches/object state without deleting active evidence · **depends_on:** [T7] · **requirements:** [REQ-008] · **priority:** should
- **files:** plan closeout and local Git metadata only
- **acceptance:** merged branch candidates are removed after re-verification; normal Git maintenance reports no corruption; active scratch/pipeline evidence remains until harvested; testing/main local relationship is documented (TC-T8-001)
- **sub-tasks:**
  - **T8.1 RED** — inventory merged branches, worktrees, object state, and active evidence.
  - **T8.2 Verify RED** — prove exact safe deletion targets and retained evidence owners.
  - **T8.3 GREEN** — delete only verified merged unattached branches and run ordinary Git maintenance.
  - **T8.4 Verify GREEN** — Git integrity, branch/worktree, status, and evidence-retention checks pass.
  - **T8.5 REFACTOR** — none.
  - **T8.6 Verify Task** — final repository gates and plan closeout evidence.

### Discovered Work

#### T9: Author managed workflow successors

- **goal:** make the approved immutable action pins authoritative managed payload content rather than root-only drift · **depends_on:** [T3, T4] · **requirements:** [REQ-003] · **priority:** must
- **files:** successor package versions for Markdown Frontmatter, Markdown Tooling, and Project Spec; package declarations, non-versioned mirrors, projections, catalog tests
- **acceptance:** each changed managed workflow is sourced from a new immutable successor version; every predecessor remains byte/mode-identical; package/catalog/projection checks pass; root reconciliation reports no `CP-MODIFIED-MANAGED` findings for the pinned workflows (TC-T9-001)
- **sub-tasks:**
  - **T9.1 RED** — add package-policy tests proving root managed workflow pins must match advertised payload sources; expected failure names the four root-only modified-managed paths.
  - **T9.2 Verify RED** — candidate reconciliation remains non-applicable only for the intended package-authority mismatch.
  - **T9.3 GREEN** — author the three smallest successor packages through the established package-version procedure, update mutable mirrors/declarations, and regenerate projections without altering predecessors.
  - **T9.4 Verify GREEN** — focused package tests and candidate reconciliation no longer report modified-managed findings.
  - **T9.5 REFACTOR** — normalize generated metadata only; do not broaden package behavior.
  - **T9.6 Verify Task** — predecessor proof plus package, graph, schema, projection, catalog, Ruff, and BasedPyright gates; commit with IDs.

## 9. Cross-Cutting Requirements

| Concern | Applies? | How verified | Owning task |
| --- | --- | --- | --- |
| Error handling | yes | zero/multiple wheel tests and control-plane fail-closed checks | T2, T7 |
| Security | yes | immutable action pins, audits, path boundary tests | T3, T5 |
| Performance | yes | existing timing gates retained | T2, T7 |
| Compatibility/migration | yes | predecessor bytes, exact candidate, no-op reconcile | T4, T7 |
| Documentation | yes | doc lifecycle and release parity checks | T1, T7 |

## 10. Integration or Migration

- **Migration required:** yes · **Rollback supported:** yes before publication · **Idempotent:** yes after reconcile
- Sequence: implement/commit T1-T6 on `testing`; implement/commit discovered T9 after T3/T4; fast-forward local `main`; prepare 5.14; restore exact v5.13 catalog lineage; reconcile with the fresh candidate; verify and commit exact result.
- No remote branch, tag, release, or issue is mutated.

## 11. Risks and Decisions

| ID | Risk | Likelihood | Impact | Mitigation | Owning task |
| --- | --- | --- | --- | --- | --- |
| R-001 | Wrong catalog restoration loses candidate intent | medium | high | restore one exact file from tag, then let candidate transaction regenerate state | T7 |
| R-002 | Action SHA belongs to fork/wrong tag | low | high | verify each SHA against official repository tag before edit | T3 |
| R-003 | Mode changes touch immutable payloads | medium | high | explicit mutable allowlist plus predecessor-byte check | T4 |
| R-004 | Refactor changes byte semantics | low | high | characterization and exact adapter/handoff suites | T5, T6 |
| R-005 | Root-only security pins violate managed package ownership | high | high | ship pins in new immutable successor payloads and re-run candidate reconciliation | T9, T7 |

| ID | Decision | Rationale | Affected task(s) |
| --- | --- | --- | --- |
| D-001 | Pin external actions and add npm maintenance/audit | Owner authorized every review correction. | T3 |
| D-002 | Transfer retirement work to T32 and retire obsolete plan | Removes competing authority without rewriting history. | T1 |
| D-003 | Retain active scratch evidence | It is not a repository defect and still supports release work. | T8 |
| D-004 | Combine all approved repository corrections into 5.14 before final qualification | The owner's “Correct all” supersedes the review's conservative post-release deferral for HYG-010/S-001/S-002 and avoids an otherwise unnecessary second release. | T4, T5, T6, T7 |
| D-005 | Delete four verified merged branches and run ordinary Git maintenance | The owner's “Correct all” is the explicit retention decision requested by J-001/J-002; deletion remains conditional on fresh target proof and excludes active worktrees/evidence. | T8 |
| D-006 | Add three managed workflow package successors to the 5.14 train | Candidate reconciliation proved root-only pinning is rejected as modified managed content; successors preserve ownership and complete the authorized correction. | T9, T7 |

## 12. Open Questions

None. Remote publication remains a separate authorization boundary, not an implementation question.

## 13. Final Verification

- `uv run ruff check .`, `uv run ruff format --check .`, `uv run basedpyright`.
- Fresh candidate and `scripts/verify.sh --full` pass.
- Package/graph/schema/projection/catalog/release checks pass.
- Reconcile no-op, Agent Handoff validate/drift-check, Prettier, markdownlint, and maintained-doc validation pass.
- Every requirement maps to completed evidence; no immutable predecessor changed.

## 14. Close-out

- **Completed:** _pending_ · final commit _pending_
- **Deviations / decisions harvested from notes:** _pending close-out_
- **Risks closed / accepted:** _pending close-out_
- **Deferred work filed:** push, tag, publication, and issue mutation remain separately authorized.

Teardown after harvest: set complete, commit master, then remove `.project-pipeline/2026-08-01-repository-hygiene-remediation/`.
