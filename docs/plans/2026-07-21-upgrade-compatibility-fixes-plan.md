---
title: 'Upgrade Compatibility Fixes Implementation Plan'
slug: 'upgrade-compatibility-fixes'
size: standard
status: active
source: 'GitHub issues #14 and #15 plus approved design'
spec_ref: 'docs/specs/archive/2026-07-21-upgrade-compatibility-fixes-design.md'
created: 2026-07-21
updated: 2026-07-21
owners:
  - 'Codex with Chris Purcell / L3DigitalNet'
test_framework: pytest
---

# Upgrade Compatibility Fixes Implementation Plan

> **Definition, not state.** Live progress and evidence belong under `.project-pipeline/2026-07-21-upgrade-compatibility-fixes/`.

## 1. Objective

Publish Project Standards 5.4.0 with Python Tooling 1.5 and Markdown Tooling 1.6 fixes for GitHub issues #14/#15, full release proof, and evidence-backed issue closure.

## 2. Background

Python Tooling 1.4 owns entire checker and pytest TOML tables, so legitimate consumer extensions make V4 migration conflict. Markdown Tooling 1.5 emits literal glob prose that strict MD037/MD049 configurations parse as emphasis. Released payloads are immutable, so both fixes require compatible successors.

## 3. Scope

### 3.1 In Scope

- Successor payloads, regression/lifecycle coverage, catalog/projection integration, consumer docs, candidate verification, release publication, hosted proof, and issue closure.

### 3.2 Out of Scope

- Generic adapter/migration changes, pass-through option expansion, broad pyproject ownership escapes, or released-payload mutation.

### 3.3 Assumptions

- Existing release credentials and signing identity remain available; absence blocks publication only.

### 3.4 Constraints

- Canonical payloads live under `standards/`; generated projections are never hand-edited.
- Behavior changes follow RED-GREEN-REFACTOR and source/wheel parity.
- Release 5.4.0 lands on `main` before signed tags and GitHub publication.

## 4. Requirements and Traceability

| ID | Requirement | Source | Priority | Task(s) | Verified by |
| --- | --- | --- | --- | --- | --- |
| FR-001 | Preserve `extraPaths` and `pythonpath` through migration/convergence. | design | must | T1 | TC-T1-001 |
| FR-002 | Manage all canonical checker/pytest keys with one checker family. | design | must | T1 | TC-T1-002 |
| FR-003 | Preserve lifecycle lock integrity and historical selection. | design | must | T1, T3 | TC-T1-002, TC-T3-001 |
| FR-004 | Code-wrap globs and pass strict emphasis lint. | design | must | T2 | TC-T2-001 |
| FR-005 | Retain old payloads and advance compatible defaults. | design | must | T3 | TC-T3-001 |
| FR-006 | Publish byte-verified 5.4.0 with signed tags and hosted proof. | design | must | T4, T5 | TC-T4-001, TC-T5-001 |
| FR-007 | Close #14/#15 only after publication. | design | must | T5 | TC-T5-002 |
| NFR-001 | Keep released payloads/tags/selections immutable. | design | must | T3, T4 | TC-T3-002, TC-T4-001 |
| NFR-002 | Preserve passing outcomes; classify as MINOR. | design | must | T3, T4 | TC-T3-002, TC-T4-001 |
| NFR-003 | Require RED/GREEN and fresh local/hosted evidence. | design | must | T1, T2, T4, T5 | all test cases |

## 5. Repository Context

### 5.1 Relevant Components

| Component | Purpose | Paths |
| --- | --- | --- |
| Package families | Provider/config/migration contracts | `standards/python-tooling/`, `standards/markdown-tooling/` |
| Regression suites | Reconstruction/lifecycle/coherence proof | `tests/package_contract/`, `tests/coherence/` |
| Catalog/release | Selection, versioning, publication truth | `catalogs/5.toml`, `pyproject.toml`, `CHANGELOG.md`, `docs/handoff/` |

### 5.2 Existing Behavior

The affected Python contributions are whole tables; Markdown scope prose joins raw glob strings. Catalog 5 defaults to Python 1.4 and Markdown 1.5; Project Standards 5.3.1 is published.

### 5.3 Expected File Changes

| Path | Action | Purpose | Task |
| --- | --- | --- | --- |
| `standards/python-tooling/versions/1.5/`, Python tests | create/modify | Key ownership fix | T1 |
| `standards/markdown-tooling/versions/1.6/`, Markdown tests | create/modify | Code-span fix | T2 |
| Family/catalog/projection/docs surfaces | modify/regenerate | Advertise compatible defaults | T3 |
| Version/changelog/status/handoff/release evidence | modify | Prepare and publish 5.4.0 | T4, T5 |

### 5.4 Dependencies

| Dependency        | Type     | Constraint                  | Reason                  |
| ----------------- | -------- | --------------------------- | ----------------------- |
| pytest            | dev      | repository lock             | Regression execution    |
| markdownlint-cli2 | dev      | 0.23.1                      | Exact lint proof        |
| GitHub/GPG        | external | repository release contract | Publication and signing |

## 6. Test Strategy

- Use `uv run pytest`, Ruff, BasedPyright, package graph/schema/projection gates, pinned Node tooling, and the complete extracted-candidate release gate from repository instructions.
- Each behavior task observes focused RED, implements minimum GREEN, runs adjacent suites, then commits.
- Declarative release/publication tasks use explicit TDD exceptions and objective pre/post state checks.

### 6.1 RED-GREEN-REFACTOR Contract

RED must fail for the missing behavior, GREEN must be minimal, REFACTOR preserves green, and Verify Task runs focused plus adjacent static/integration checks.

### 6.2 Special Cases

Copy released payloads only after RED; generate integrity/catalog/projection metadata from final canonical bytes; reuse one candidate artifact pair through verification and upload.

## 7. Execution Summary

| Task | Title | Phase | Depends on | Requirement(s) | Primary verification |
| --- | --- | --- | --- | --- | --- |
| T1 | Python key ownership | P1 | None | FR-001/2/3, NFR-003 | Python reconstruction suite |
| T2 | Markdown code-span globs | P1 | T1 | FR-004, NFR-003 | reconstruction/coherence |
| T3 | Package/catalog integration | P2 | T1, T2 | FR-003/5, NFR-001/2 | package/release checks |
| T4 | 5.4.0 candidate gate | P2 | T3 | FR-006, NFR-001/2/3 | full candidate gate |
| T5 | Publication and closure | P3 | T4 | FR-006/7, NFR-003 | live GitHub proof |

## 8. Implementation Tasks

### Phase P1: Regression Fixes

#### T1: Python Tooling key-level ownership

- **goal:** Preserve consumer-only checker/pytest keys while managing canonical keys. · **depends_on:** [] · **requirements:** [FR-001, FR-002, FR-003, NFR-003] · **priority:** must
- **files:** Python reconstruction tests; `standards/python-tooling/versions/1.5/`
- **acceptance:** issue fixture previews/applies/converges with values preserved (TC-T1-001); canonical key lock set, one checker, lifecycle convergence (TC-T1-002).
- **sub-tasks:**
  - **T1.1 RED** — add the V4 `extraPaths`/`pythonpath` fixture; expected failure: two whole-table conflicts.
  - **T1.2 Verify RED** — run the focused migration test; confirm the expected conflicts.
  - **T1.3 GREEN** — create 1.5 with selected-checker and pytest key contributions/value rendering.
  - **T1.4 Verify GREEN** — run migration, lifecycle, reconstruction, and integrity tests.
  - **T1.5 REFACTOR** — consolidate scope rendering only if clearer; otherwise none.
  - **T1.6 Verify Task** — focused suite, Ruff, BasedPyright, integrity/projection; commit IDs.

##### T1 Test Cases

| ID | Test | Type | Expected result |
| --- | --- | --- | --- |
| TC-T1-001 | V4 extended pyproject migration | regression | apply succeeds; values survive; second plan converges |
| TC-T1-002 | key scopes and lifecycle | contract/integration | only canonical keys locked; transitions converge |

#### T2: Markdown Tooling code-span globs

- **goal:** Make managed glob prose immune to emphasis parsing. · **depends_on:** [T1] · **requirements:** [FR-004, NFR-003] · **priority:** must
- **files:** Markdown reconstruction/coherence tests; `standards/markdown-tooling/versions/1.6/`
- **acceptance:** every default/custom glob is code-wrapped and pinned markdownlint reports zero MD037/MD049 findings (TC-T2-001).
- **sub-tasks:**
  - **T2.1 RED** — add provider/linter regression; expected failure: raw globs trigger emphasis findings.
  - **T2.2 Verify RED** — run focused tests; confirm literal rendering is causal.
  - **T2.3 GREEN** — create 1.6 and wrap each schema-safe glob before joining.
  - **T2.4 Verify GREEN** — run reconstruction and coherence behavior tests.
  - **T2.5 REFACTOR** — keep rendering local; otherwise none.
  - **T2.6 Verify Task** — focused suites, Ruff, BasedPyright, integrity/projection; commit IDs.

##### T2 Test Cases

| ID | Test | Type | Expected result |
| --- | --- | --- | --- |
| TC-T2-001 | strict instruction rendering | regression | code spans present; zero strict-emphasis findings |

### Phase P2: Integration and Candidate

#### T3: Package graph and consumer documentation

- **goal:** Retain old payloads and advertise corrected compatible defaults. · **depends_on:** [T1, T2] · **requirements:** [FR-003, FR-005, NFR-001, NFR-002] · **priority:** must
- **files:** family indexes, catalog, projections, package/catalog docs, catalog tests
- **acceptance:** new defaults resolve; old exact selectors remain byte-identical (TC-T3-001); release classification is MINOR (TC-T3-002).
- **sub-tasks:**
  - **T3.1 RED** — update current-catalog expectations; expected failure: versions are absent.
  - **T3.2 Verify RED** — run catalog activation/registry tests; confirm absence.
  - **T3.3 GREEN** — register versions, generate metadata/projections, synchronize docs.
  - **T3.4 Verify GREEN** — catalog, registry, graph, schema, projection, historical tests.
  - **T3.5 REFACTOR** — deduplicate prose only; otherwise none.
  - **T3.6 Verify Task** — package commands, focused pytest, Markdown/static checks; commit IDs.

##### T3 Test Cases

| ID | Test | Type | Expected result |
| --- | --- | --- | --- |
| TC-T3-001 | catalog activation/history | integration | new defaults and retained exact versions work |
| TC-T3-002 | baseline/classification | release | no historical drift; MINOR required |

#### T4: 5.4.0 candidate and repository release gate

- **goal:** Prepare one 5.4.0 artifact pair and pass every release gate. · **depends_on:** [T3] · **requirements:** [FR-006, NFR-001, NFR-002, NFR-003] · **priority:** must
- **files:** version/lock/changelog, release fixtures, status/TODO/handoff
- **acceptance:** exact candidate passes source/installed/compatibility/performance/security/package/docs/handoff checks and release commit lands on `main` (TC-T4-001).
- **sub-tasks:**
  - **T4.1 RED** — TDD exception: record expected unreleased metadata/classification blockers.
  - **T4.2 Verify RED** — confirm no behavior blocker remains.
  - **T4.3 GREEN** — set 5.4.0 metadata, update truth surfaces, build/extract once.
  - **T4.4 Verify GREEN** — run the complete gate against the extracted candidate.
  - **T4.5 REFACTOR** — enforce release diff allowlist; remove runtime artifacts.
  - **T4.6 Verify Task** — rerun classification/hashes/gates/handoff/parity; commit/integrate.

##### T4 Test Cases

| ID | Test | Type | Expected result |
| --- | --- | --- | --- |
| TC-T4-001 | exact candidate gate | release | all required gates pass on one artifact pair |

### Phase P3: Publication

#### T5: Publish, verify, and close issues

- **goal:** Make 5.4.0 live and close #14/#15 with proof. · **depends_on:** [T4] · **requirements:** [FR-006, FR-007, NFR-003] · **priority:** must
- **files:** Git/GitHub refs, release/assets/issues, deployed/status/session truth
- **acceptance:** signed tags/release/assets/workflows/branches agree (TC-T5-001); both issues close with evidence (TC-T5-002).
- **sub-tasks:**
  - **T5.1 RED** — TDD exception: prove release/tag/assets/closed issue states are absent.
  - **T5.2 Verify RED** — confirm no conflicting immutable tag/release exists.
  - **T5.3 GREEN** — push release commit, sign/publish tags, upload retained artifacts, synchronize branches.
  - **T5.4 Verify GREEN** — wait workflows, download/compare assets, prove parity.
  - **T5.5 REFACTOR** — record exact deployment/session evidence; trim eager state.
  - **T5.6 Verify Task** — close/re-query issues and live release state; validate/push final record.

##### T5 Test Cases

| ID | Test | Type | Expected result |
| --- | --- | --- | --- |
| TC-T5-001 | live release proof | operational | exact refs/assets/workflows/branches agree |
| TC-T5-002 | issue closure proof | operational | #14/#15 closed with 5.4.0 evidence |

## 9. Cross-Cutting Requirements

| Concern | Applies? | How verified | Owning task |
| --- | --- | --- | --- |
| Security/performance | yes | audits, signed tags, serial performance gate | T4, T5 |
| Compatibility/migration | yes | V4/lifecycle/catalog/history suites | T1, T3, T4 |
| Documentation | yes | package/release/handoff sync and Markdown gates | T3, T4, T5 |

## 10. Integration or Migration

- **Migration required:** yes · **Rollback supported:** exact historical selectors/refs · **Idempotent:** yes.
- Author/test payloads, register compatible defaults, prepare/land 5.4.0, publish/verify, close issues.

## 11. Risks and Decisions

| ID | Risk | Likelihood | Impact | Mitigation | Owning task |
| --- | --- | --- | --- | --- | --- |
| R-001 | Stale table/lock units | medium | high | lifecycle and lock-scope tests | T1 |
| R-002 | Payload/projection drift | medium | high | generated integrity/source-wheel gates | T1-T4 |
| R-003 | Hosted state divergence | low | high | exact-SHA/hash/workflow/parity proof | T4, T5 |

| ID | Decision | Rationale | Affected task(s) |
| --- | --- | --- | --- |
| D-001 | Key-level TOML ownership | Preserves arbitrary consumer extensions without engine changes | T1 |
| D-002 | Inline-code globs | Fixes parsing without weakening lint policy | T2 |
| D-003 | Release 5.4.0 | Compatible payload additions are MINOR | T3-T5 |

## 12. Open Questions

None blocking; autonomous sane defaults and full release are authorized.

## 13. Final Verification

Run the complete source/extracted-wheel Python lanes, package graph/schema/projection/catalog checks, npm/Markdown/coherence/audits, dogfood/handoff checks, exact artifact/tag/release/workflow/branch proof, and closed issue query.

## 14. Close-out

- **Completed:** pending
- **Deviations / decisions:** pending
- **Risks / deferred work:** pending

Repository convention keeps only active plans: harvest durable facts, then delete this plan and its scratch directory at final closeout.
