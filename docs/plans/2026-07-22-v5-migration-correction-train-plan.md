---
title: 'V5 Migration Correction Train Implementation Plan'
slug: 'v5-migration-correction-train'
size: full
status: active
source: 'docs/specs/archive/2026-07-22-v5-migration-correction-train-design.md'
spec_ref: 'docs/specs/archive/2026-07-22-v5-migration-correction-train-design.md'
created: 2026-07-22
updated: 2026-07-22
owners:
  - 'Codex with Chris Purcell / L3DigitalNet'
test_framework: pytest
---

# V5 Migration Correction Train Implementation Plan

> **Definition, not state.** Routine progress lives in `.project-pipeline/2026-07-22-v5-migration-correction-train/`. This master changes only for appended discovered work or close-out harvest.

## 1. Objective

Deliver Project Standards 5.5.0 with bounded corrections for GitHub issues #16, #17, and #18, retain every released payload and exact-version behavior, publish one verified candidate from `main`, and close the issues only after hosted evidence is authoritative.

## 2. Background

The approved design identifies three 5.4.0 failures: raw whole-file migration signatures cannot recognize the documented disabled V4 format caller; Project Spec rejects a valid configured-empty corpus; and Agent Handoff counts package-managed instruction envelopes against consumer budgets. The solution requires an engine contract addition plus four immutable successor packages.

## 3. Scope

### 3.1 In Scope

- Dual source/signature views for opt-in semantic whole-file YAML/TOML signatures.
- Markdown Tooling 1.7, Standard Bundle Authoring 2.4, Project Spec 1.4, and Agent Handoff 1.4.
- Catalog 5 integration, exact predecessor compatibility, 5.5.0 qualification, publication, and issue closeout.

### 3.2 Out of Scope

- Arbitrary workflow inference, unknown-content relaxation, released-payload edits, invalid-config empty success, unauthenticated size subtraction, new test frameworks, and unrelated cleanup.

### 3.3 Assumptions

- The changes remain MINOR-compatible; evidence of a newly failing prior consumer blocks publication and reopens classification.
- GitHub and signing authority remain available; their absence blocks publication rather than weakening proof.

### 3.4 Constraints

- Use `uv`, Ruff, BasedPyright strict, pytest, candidate-wheel-first package validation, Prettier, and markdownlint.
- Every behavior task proves a right-reason RED and commits only after fresh task verification.
- Unknown semantic history and ambiguous Markdown fail closed.
- Follow `meta/versioning.md`: release commit on `main` before signed tags, hosted and downloaded-asset proof before issue closure.

## 4. Source Requirements

| ID | Requirement | Source | Priority | Task(s) |
| --- | --- | --- | --- | --- |
| FR-001 | Whole-file signatures may opt into YAML/TOML semantics; raw/bounded behavior stays unchanged. | design | must | T1 |
| FR-002 | Semantic normalization rejects ambiguous, noncanonical, and non-JSON input before writes. | design | must | T1 |
| FR-003 | Signature authentication and exact source-byte ownership stay distinct. | design | must | T1, T2 |
| FR-004 | Markdown Tooling 1.7 migrates supported `prettier: false` history to both disabled options. | #16 | must | T3 |
| FR-005 | Unsupported customized format callers remain blocked without mutation. | #16 | must | T3 |
| FR-006 | Project Spec 1.4 configured-empty validate/strict-lint succeeds with stable human/JSON output. | #17 | must | T4 |
| FR-007 | Project Spec 1.3 and absent/invalid/explicit-missing inputs retain errors. | #17 | must | T4 |
| FR-008 | Agent Handoff 1.4 excludes exact lock-authenticated managed Markdown envelopes. | #18 | must | T5 |
| FR-009 | Agent Handoff receives all Markdown lock units without changing `managed_units`. | design | must | T5 |
| FR-010 | Ambiguous or unauthenticated block lookalikes remain counted. | #18 | must | T5 |
| FR-011 | Legacy V4 size reporting excludes only its exact historical block. | #18 | must | T6 |
| FR-012 | Catalog 5 retains predecessors and selects all four successors. | design | must | T7 |
| FR-013 | One verified 5.5.0 candidate publishes from `main` with signed tags and byte-matching assets. | release contract | must | T8, T9, T10 |
| FR-014 | Issues #16-#18 close only after published and hosted evidence exists. | design | must | T10 |
| NFR-001 | Released payloads, immutable tags, historical selection, and exact-version behavior do not change. | design | must | T3-T5, T7, T9 |
| NFR-002 | New accepted states remain bounded by declared history or authenticated ownership. | design | must | T1-T3, T5, T6 |
| NFR-003 | RED/GREEN plus source, artifact, and hosted evidence supports every completion claim. | design | must | T1-T10 |
| NFR-004 | The train passes MINOR classification without newly failing a prior consumer. | version policy | must | T7, T9 |

## 5. Repository and Architecture Context

### 5.1 Relevant Components

| Component | Purpose | Paths |
| --- | --- | --- |
| Signature contract/migration | declaration, inspection, claims, locks, actions | `src/project_standards/package_contract/`, `src/project_standards/control_plane/migration.py` |
| Selected commands | exact package authority and snapshots | `src/project_standards/specs/`, `src/project_standards/agent_handoff/` |
| Immutable packages | providers, resources, migrations, docs | `standards/*/versions/` |
| Catalog/projection/release | selection, installed mirror, release truth | `catalogs/`, `src/project_standards/`, `meta/versioning.md`, `docs/handoff/` |

### 5.2 Existing Behavior

Whole-file `format` is forbidden and `_ObservedSignature` has one digest/content view. Project Spec raises `DiscoveryError` on zero selected matches. Agent Handoff snapshots only its own lock units and compares raw instruction-file length with budgets; the legacy reporter also counts its historical block.

### 5.3 Files Expected to Change

| Path | Action | Purpose | Task |
| --- | --- | --- | --- |
| `src/project_standards/package_contract/payload.py`, `src/project_standards/control_plane/migration.py` | modify | semantic signature dual view | T1-T2 |
| `standards/markdown-tooling/versions/1.7/**`, `standards/standard-bundle-authoring/versions/2.4/**` | create | #16 and authoring contract | T3 |
| `src/project_standards/specs/cli.py`, `standards/project-spec/versions/1.4/**` | modify/create | #17 | T4 |
| command snapshot/provider paths, `standards/agent-handoff/versions/1.4/**` | modify/create | #18 V5 | T5 |
| `src/project_standards/agent_handoff/validation.py` | modify | #18 legacy | T6 |
| family/catalog/projection/matrix files | generate/modify | compatible integration | T7 |
| version/changelog/status/deployment/session files | modify | release and closeout | T8, T10 |

### 5.4 Dependencies

No dependency changes. Use locked Python 3.14+, PyYAML, Pydantic, pytest, Ruff, BasedPyright, npm tooling, GitHub CLI, and GPG.

## 6. Test Strategy

- Assert public findings, exits/output, option values, lock/action digests, budgets, and convergence; mock calls alone do not prove behavior.
- Run targeted tests through `uv run pytest`, then related modules, Ruff, BasedPyright, package reconstruction, and source/wheel compatibility as appropriate.
- Use deterministic parameterization for finite parser/ambiguity cases; do not add Hypothesis solely for this train.

### 6.1 RED-GREEN-REFACTOR Contract

Each behavior task executes RED, Verify RED, minimum GREEN, Verify GREEN, bounded REFACTOR, and Verify Task. A wrong-reason RED stops. Refactor failure returns to GREEN and is recorded in notes.

### 6.2 Test Categories

| Category | Purpose | Location |
| --- | --- | --- |
| Contract/regression | declarations and #16-#18 | `tests/package_contract/`, focused command tests |
| Integration/compatibility | migration, lifecycle, source/wheel | `tests/control_plane/`, `tests/package_compatibility/` |
| End-to-end | candidate dogfood and publication | §13 and GitHub evidence |

### 6.3 TDD Exceptions

| Task | Reason | Validation |
| --- | --- | --- |
| T7 generated artifacts only | generated schema, projection, and catalog render have no independent behavior RED; selection and matrix changes retain T7.1/T7.2 | graph/schema/projection/catalog gates |
| T8-T10 | release preparation, qualification, and external publication are not behavior changes | version/build/hash/hosted/ref/issue evidence |

## 7. Execution Summary

| Task | Title | Phase | Depends on | Requirements | Primary verification |
| --- | --- | --- | --- | --- | --- |
| T1 | Semantic signature declaration and inspection | P1 | None | FR-001-003, NFR-002-003 | package/migration pytest |
| T2 | Exact source ownership through migration | P1 | T1 | FR-003, NFR-002-003 | preview/apply/lock pytest |
| T3 | Markdown migration successors | P2 | T2 | FR-004-005, NFR-001-003 | issue fixture/reconstruction |
| T4 | Project Spec empty corpus | P2 | T2 | FR-006-007, NFR-001, NFR-003 | selected CLI/reconstruction |
| T5 | V5 Agent Handoff size accounting | P2 | T2 | FR-008-010, NFR-001-003 | snapshot/provider adversarial tests |
| T6 | Legacy size accounting | P2 | None | FR-011, NFR-002-003 | validation regressions |
| T7 | Catalog 5 integration | P3 | T3-T6 | FR-012, NFR-001, NFR-003-004 | graph/projection/matrix |
| T8 | Prepare 5.5.0 candidate | P4 | T7 | FR-013, NFR-003 | version/build/hash gates |
| T9 | Qualify exact candidate | P4 | T8 | FR-013, NFR-001, NFR-003-004 | complete §13 gate |
| T10 | Publish and close out | P5 | T9 | FR-013-014, NFR-003 | refs/workflows/assets/issues/parity |

## 8. Implementation Tasks

## Phase P1: Migration Signature Foundation

### T1: Semantic signature declaration and inspection

- **goal:** Whole YAML/TOML signatures authenticate canonical semantics while retaining exact source bytes; raw/bounded behavior is unchanged. · **phase:** P1 · **depends_on:** [] · **requirements:** [FR-001, FR-002, FR-003, NFR-002, NFR-003] · **priority:** must
- **files:** package payload model/schema, migration inspection, package/migration tests
- **acceptance:** whole-file `format` validates without delimiters (TC-T1-001); semantic equivalents share a signature digest but retain distinct source bytes/digests (TC-T1-002); malformed/duplicate/anchor/non-JSON cases fail before providers (TC-T1-003); old raw/bounded cases are unchanged (TC-T1-004).
- **sub-tasks:**
  - **T1.1 RED** — add TC-T1-001 through TC-T1-004; expected failure: whole-file `format` and dual views are unsupported.
  - **T1.2 Verify RED** — run exact tests; confirm behavior failures, not collection failures.
  - **T1.3 GREEN** — relax only the declaration shape, add strict canonical inspection and separate source/signature fields, regenerate schema.
  - **T1.4 Verify GREEN** — focused package/migration tests plus schema check.
  - **T1.5 REFACTOR** — share normalization only without changing bounded behavior; otherwise none.
  - **T1.6 Verify Task** — focused tests, Ruff, BasedPyright, schema and diff checks; commit with IDs.

### T2: Exact source ownership through migration

- **goal:** Claims use signature digests; historical inspection, locks, removal actions, and apply preconditions use exact source bytes/digests. · **phase:** P1 · **depends_on:** [T1] · **requirements:** [FR-003, NFR-002, NFR-003] · **priority:** must
- **files:** migration engine and migration tests
- **acceptance:** snapshots/claims bind semantic digest (TC-T2-001); locks/actions bind source digest (TC-T2-002); byte-only preview/apply drift refuses writes (TC-T2-003); historical adapters consume source bytes (TC-T2-004); replay and reconciliation retain the recorded source digest and converge (TC-T2-005).
- **sub-tasks:**
  - **T2.1 RED** — add dual-digest preview/apply/replay tests; expected failure: the single digest cannot satisfy both contracts.
  - **T2.2 Verify RED** — confirm digest/lock/action assertions fail for the intended reason.
  - **T2.3 GREEN** — thread both views through claim validation, historical adapters, initial locks, actions, preconditions, and replay.
  - **T2.4 Verify GREEN** — migration module plus nearest executor/planner regressions.
  - **T2.5 REFACTOR** — make source/signature naming explicit; no redesign.
  - **T2.6 Verify Task** — focused tests, Ruff, BasedPyright, diff audit; commit with IDs.

## Phase P2: Versioned Consumer Corrections

### T3: Markdown migration successors

- **goal:** Markdown Tooling 1.7 migrates the supported disabled V4 caller; SBA 2.4 documents semantic signature limits. · **phase:** P2 · **depends_on:** [T2] · **requirements:** [FR-004, FR-005, NFR-001, NFR-002, NFR-003] · **priority:** must
- **files:** new 1.7/2.4 payloads, issue fixture, migration/provider/reconstruction tests
- **acceptance:** disabled state maps both options and converges (TC-T3-001); enabled state remains default (TC-T3-002); formatting variants of the closed shape pass (TC-T3-003); custom shape stays blocked (TC-T3-004); predecessors are byte-stable (TC-T3-005); SBA 2.4 is selected-resolvable and documents closed historical shapes, enumerated forms, and no arbitrary customization (TC-T3-006).
- **sub-tasks:**
  - **T3.1 RED** — add #16 fixture and known/unknown cases; expected failure: 1.6 reports conflict/digest.
  - **T3.2 Verify RED** — prove reported failure and independent custom refusal.
  - **T3.3 GREEN** — create full successors, enumerate digests, map disabled state, update authoring prose/integrity.
  - **T3.4 Verify GREEN** — focused migration/provider/reconstruction and package gates.
  - **T3.5 REFACTOR** — keep provider classification explicit/self-contained.
  - **T3.6 Verify Task** — tests, immutable diff proof, package/static/Markdown gates; commit with IDs.

### T4: Project Spec configured-empty corpus

- **goal:** Selected Project Spec 1.4 and later compatible 1.x versions visibly succeed on valid zero-match discovery while 1.3 and protected errors remain unchanged. · **phase:** P2 · **depends_on:** [T2] · **requirements:** [FR-006, FR-007, NFR-001, NFR-003] · **priority:** must
- **files:** spec CLI, new 1.4 payload, CLI/selected/reconstruction tests
- **acceptance:** validate/strict lint return 0 with informational human output and JSON `[]` (TC-T4-001); provider is skipped (TC-T4-002); 1.3 exits 2 while a synthetic later 1.x selection succeeds (TC-T4-003); absent configuration, empty `include_patterns`, invalid patterns, explicit missing paths, and symlinks fail under both 1.3 and 1.4, while `spec new` retains best-effort empty-corpus behavior (TC-T4-004); the full immutable 1.4 copy reconstructs from source/wheel and 1.3 bytes are unchanged (TC-T4-005).
- **sub-tasks:**
  - **T4.1 RED** — add versioned output/negative tests; expected failure: 1.4 zero matches raises discovery error.
  - **T4.2 Verify RED** — confirm 1.4 fails while protected negatives characterize current behavior.
  - **T4.3 GREEN** — create a full immutable 1.4 successor with documentation, manifest resources, and integrity inventory; enable zero-match success for selected Project Spec versions at least 1.4 within major 1; skip empty provider invocation.
  - **T4.4 Verify GREEN** — CLI/selected/provider/reconstruction suites.
  - **T4.5 REFACTOR** — name empty-result path; preserve legacy config routing.
  - **T4.6 Verify Task** — focused/package/static checks and diff audit; commit with IDs.

### T5: V5 Agent Handoff consumer-only size accounting

- **goal:** Agent Handoff 1.4 subtracts only exact managed envelopes authenticated by all-package Markdown lock units. · **phase:** P2 · **depends_on:** [T2] · **requirements:** [FR-008, FR-009, FR-010, NFR-001, NFR-002, NFR-003] · **priority:** must
- **files:** command snapshot/provider path declaration, Agent Handoff CLI, new 1.4 payload, selected/provider/reconstruction tests
- **acceptance:** new collection contains every `markdown-block` unit while `managed_units` stays local, referenced targets are path-validated, and the collection key is never treated as a repository path (TC-T5-001); exact Agent Handoff/Markdown/Python full envelopes subtract, including BEGIN/END and Prettier-control lines, with exact byte totals (TC-T5-002); malformed/nested/duplicate/unlocked/wrong-scope/drifted blocks count (TC-T5-003); the self-contained full immutable 1.4 copy reconstructs from source/wheel and 1.3 bytes are unchanged (TC-T5-004).
- **sub-tasks:**
  - **T5.1 RED** — add #18 and adversarial tests; expected failure: 1.3 counts full files and no all-package snapshot exists.
  - **T5.2 Verify RED** — confirm size failures and raw-count adversarial characterizations.
  - **T5.3 GREEN** — add distinct snapshot metadata and path validation; create a full immutable 1.4 successor with documentation, manifest resources, and integrity inventory; implement self-contained fail-closed envelope/digest matching.
  - **T5.4 Verify GREEN** — Agent Handoff CLI/selected/planning/reconstruction suites.
  - **T5.5 REFACTOR** — keep parser bounded; no mutable engine import into payload.
  - **T5.6 Verify Task** — focused/package/static checks and diff audit; commit with IDs.

### T6: Legacy Agent Handoff size accounting

- **goal:** V4 fallback excludes one exact historical block and counts malformed/multiple variants. · **phase:** P2 · **depends_on:** [] · **requirements:** [FR-011, NFR-002, NFR-003] · **priority:** must
- **files:** mutable Agent Handoff validation and legacy/validation tests
- **acceptance:** exact legacy envelope subtracts (TC-T6-001); partial/nested/duplicate/wrong markers count (TC-T6-002); unrelated validation stays green (TC-T6-003).
- **sub-tasks:**
  - **T6.1 RED** — add exact/adversarial budget tests; expected failure: exact block is counted.
  - **T6.2 Verify RED** — confirm only intended valid case differs.
  - **T6.3 GREEN** — add one private exact-marker stripper for legacy size reporting.
  - **T6.4 Verify GREEN** — validation/legacy/CLI modules.
  - **T6.5 REFACTOR** — keep helper single-purpose.
  - **T6.6 Verify Task** — focused/static/diff checks; commit with IDs.

## Phase P3: Catalog Integration

### T7: Integrate successors into Catalog 5

- **goal:** Retain all versions, select 1.7/1.4/1.4/2.4, and prove compatible source/wheel lifecycle. · **phase:** P3 · **depends_on:** [T3, T4, T5, T6] · **requirements:** [FR-012, NFR-001, NFR-003, NFR-004] · **priority:** must
- **files:** family/catalog/projection/schema/matrix/release tests
- **acceptance:** defaults and exact predecessors resolve (TC-T7-001); transitions converge (TC-T7-002); source/wheel matrix passes (TC-T7-003); classifier is MINOR with prior-pass proof (TC-T7-004).
- **sub-tasks:**
  - **T7.1 RED** — update selection/matrix expectations; expected failure: successors are absent.
  - **T7.2 Verify RED** — confirm integration absence, not payload invalidity.
  - **T7.3 GREEN** — update metadata and generate projections/schemas/catalog plus compatibility rows.
  - **T7.4 Verify GREEN** — catalog/lifecycle/reconstruction/matrix/classification tests.
  - **T7.5 REFACTOR** — only bounded fixture deduplication if needed.
  - **T7.6 Verify Task** — package/graph/schema/projection/catalog/source-wheel/static/immutable checks; commit with IDs.

## Phase P4: Candidate and Qualification

### T8: Prepare one 5.5.0 candidate

- **goal:** Create one release commit and one wheel/sdist pair as sole candidate evidence. · **phase:** P4 · **depends_on:** [T7] · **requirements:** [FR-013, NFR-003] · **priority:** must
- **files:** version/lock/changelog/status/deployment/session and build outputs
- **acceptance:** versions agree (TC-T8-001); prepared/published wording is truthful (TC-T8-002); one artifact pair has recorded hashes (TC-T8-003); extracted wheel reports 5.5.0 and successors (TC-T8-004).
- **sub-tasks:**
  - **T8.1 RED** — run 5.5.0 inventory assertions; expected failure: repository is 5.4.0.
  - **T8.2 Verify RED** — confirm only release references fail.
  - **T8.3 GREEN** — update authorized metadata, refresh lock, build once cleanly, extract wheel, record hashes in logs.
  - **T8.4 Verify GREEN** — version/release/docs/installed probes.
  - **T8.5 REFACTOR** — none.
  - **T8.6 Verify Task** — release/static/docs/diff checks; commit `release: prepare project standards 5.5.0` with IDs.

### T9: Qualify the exact candidate

- **goal:** Pass every local gate with the extracted T8 wheel first on `PYTHONPATH`, without rebuilding. · **phase:** P4 · **depends_on:** [T8] · **requirements:** [FR-013, NFR-001, NFR-003, NFR-004] · **priority:** must
- **files:** ephemeral logs only unless a genuine defect appends discovered work
- **acceptance:** static/security/Markdown/coherence pass (TC-T9-001); package gates pass (TC-T9-002); ordinary/compatibility/performance lanes pass (TC-T9-003); dogfood/classifier pass (TC-T9-004); hashes stay identical (TC-T9-005).
- **sub-tasks:**
  - **T9.1 RED** — assert candidate paths/hashes exist; expected failure: none after T8, so record qualification TDD exception.
  - **T9.2 Verify RED** — mark skipped with the exception reason and retain precondition evidence.
  - **T9.3 GREEN** — run §13 without rebuild; deterministic failure creates discovered work.
  - **T9.4 Verify GREEN** — re-run only transient external queries; keep deterministic evidence single-run.
  - **T9.5 REFACTOR** — none.
  - **T9.6 Verify Task** — re-hash, validate plan/checklists, confirm clean tracked tree and release identity.

## Phase P5: Publication and Close-out

### T10: Publish, verify, close issues, and close out

- **goal:** Publish exact 5.5.0 from `main`, verify it independently, close #16-#18, synchronize branches, and harvest durable facts. · **phase:** P5 · **depends_on:** [T9] · **requirements:** [FR-013, FR-014, NFR-003] · **priority:** must
- **files:** Git/GitHub state plus status/deployment/session/plan closeout
- **acceptance:** release commit precedes both signed annotated tags and `git verify-tag` succeeds for `v5.5.0` and `v5` (TC-T10-001); commit-bound workflows pass (TC-T10-002); downloads match T8 (TC-T10-003); issues close only after TC-T10-005 branch parity (TC-T10-004); branches/remotes/tags/release/handoff/worktree agree before issue closure (TC-T10-005).
- **sub-tasks:**
  - **T10.1 RED** — query refs/release/issues; expected failure: 5.5.0 absent and issues open.
  - **T10.2 Verify RED** — confirm authoritative absence, not query/auth failure.
  - **T10.3 GREEN** — land/push `main`; sign/push annotated `v5.5.0`; create a signed annotated `v5` at the same commit and move it by remote delete/re-push; release exact assets; wait/verify workflows and downloads; synchronize and confirm `testing` parity; only then close issues.
  - **T10.4 Verify GREEN** — re-query signatures, release, workflows, assets, issues, and parity independently.
  - **T10.5 REFACTOR** — update durable truth, harvest notes, close plan, delete scratch after commit.
  - **T10.6 Verify Task** — handoff validation, clean/parity proof, publication-record/closeout commit and pushes.

## 9. Cross-Cutting Requirements

| Concern | Verification | Task |
| --- | --- | --- |
| Fail-closed input/ownership | malformed signatures and block ambiguity tests | T1-T6 |
| Supply chain/compatibility | audits, signed refs, hash parity, source/wheel matrix | T7-T10 |
| Performance | existing serial lane; bounded parsers | T5, T9 |
| Documentation | SBA/package docs, changelog/status/deployment/handoff | T3, T8, T10 |

## 10. Integration and Migration

### 10.1 Integration Sequence

Foundation → independent successors → Catalog 5 → single candidate → qualification → publication.

### 10.2 Data or State Migration

- **Required:** yes · **Rollback:** pre-publication commit reversal; post-publication correcting release only · **Idempotent:** preview/apply/reconcile converge.
- V4 state migrates only for enumerated semantic history. Full-version tags and released payloads are immutable.

### 10.3 Compatibility Plan

Exact predecessors remain selected and tested; compatible `latest` advances. Source/wheel tests cover transitions, disable/re-enable, unknown refusal, and predecessor CLI behavior.

## 11. Risks and Decisions

| ID | Risk | Mitigation | Task |
| --- | --- | --- | --- |
| R-001 | semantic digest replaces source ownership | dual-digest end-to-end assertions | T1-T2 |
| R-002 | semantic history becomes unbounded | strict parser plus enumerated digests | T1, T3 |
| R-003 | empty success leaks to protected states | exact-version negative matrix | T4 |
| R-004 | size subtraction undercounts consumer bytes | lock/scope/digest auth; raw fallback | T5-T6 |
| R-005 | projections or artifacts drift | reconstruction, immutable diffs, hashes | T7-T10 |

| ID | Decision | Rationale | Task |
| --- | --- | --- | --- |
| D-001 | semantic signatures only for enumerated whole YAML/TOML history | formatting tolerance without arbitrary inference | T1-T3 |
| D-002 | separate source/signature views | authentication differs from ownership | T1-T2 |
| D-003 | empty success begins at Project Spec 1.4 | preserve 1.3 | T4 |
| D-004 | every V5 subtraction requires a lock unit | markers are not ownership | T5 |
| D-005 | publish as MINOR only after prior-pass proof | version policy | T7-T10 |

## 12. Open Questions

None. Discoveries that alter consumer behavior, ownership, versions, or classification block and return to the design checkpoint.

## 13. Final Verification

With the extracted candidate first on `PYTHONPATH`, without rebuilding:

1. `uv run ruff format --check .`; `uv run ruff check .`; `uv run basedpyright`.
2. `uv run coverage erase`; `uv run coverage run --source=project_standards -m pytest -m "not performance and not compatibility"`; `uv run pytest -m compatibility -n 4 --dist load --max-worker-restart=0`; `uv run pytest -m performance`; `uv run coverage report`.
3. `uv run pip-audit`.
4. `uv run project-standards standards validate-packages --root . --json`; `uv run project-standards standards validate-graph --root . --require-all-manifests --json`; `uv run project-standards standards generate-package-schemas --root . --check`; `uv run project-standards standards sync-payload-projection --root . --check`; `uv run project-standards standards render-catalog --root . --check`.
5. `npm ci`; `uv run pytest tests/coherence`; `npx prettier --check .`; `npx markdownlint-cli2 "**/*.md"`.
6. Candidate dogfood validation, frontmatter format check, reconcile JSON inspection, Agent Handoff conformance/drift/size, and release classification against the published baseline.
7. Re-hash wheel/sdist; `uv run scripts/plan.py validate docs/plans/2026-07-22-v5-migration-correction-train-plan.md`.

Done also requires complete checklist evidence, signed/hosted/asset proof, closed #16-#18, updated handoff truth, clean worktree, and local/remote `main`/`testing` parity.

## 14. Close-out

- **Completed:** _pending_ · final commit _pending_
- **Deviations / decisions:** _pending close-out_
- **Risks:** _pending close-out_
- **Deferred work:** _pending close-out_

After harvest and close-out commit, delete `.project-pipeline/2026-07-22-v5-migration-correction-train/`.

## Appendix A. Interface and Schema Changes

| Interface/model | Change | Compatibility |
| --- | --- | --- |
| legacy signature `format` | permit whole YAML/TOML; split observed source/signature views | additive; old declarations unchanged |
| Project Spec validate/lint | selected 1.4 zero-match success | exact 1.3 unchanged |
| Agent Handoff snapshot/size | add all-Markdown lock collection; authenticated subtraction | additive snapshot; versioned provider |

## Appendix B. Test Matrix

| Tests | Requirements | Task | Paths/type |
| --- | --- | --- | --- |
| TC-T1-001..004 | FR-001-003, NFR-002-003 | T1 | payload/migration contract/regression |
| TC-T2-001..005 | FR-003, NFR-002-003 | T2 | migration/replay integration |
| TC-T3-001..006 | FR-004-005, NFR-001-003 | T3 | migration/reconstruction/documentation compatibility |
| TC-T4-001..005 | FR-006-007, NFR-001, NFR-003 | T4 | spec CLI/reconstruction |
| TC-T5-001..004 | FR-008-010, NFR-001-003 | T5 | Agent Handoff selected/provider/reconstruction |
| TC-T6-001..003 | FR-011, NFR-002-003 | T6 | legacy validation regression |
| TC-T7-001..004 | FR-012, NFR-001, NFR-003-004 | T7 | catalog/lifecycle/matrix/release |
| TC-T8-001..004 | FR-013, NFR-003 | T8 | version/docs/build/integration |
| TC-T9-001..005 | FR-013, NFR-001, NFR-003-004 | T9 | complete local qualification |
| TC-T10-001..005 | FR-013-014, NFR-003 | T10 | refs/workflows/assets/issues/parity |

## Appendix C. Deferred Work

None at authoring. New out-of-design behavior requires an issue or owner-authorized appended task.
