---
title: 'V5 Upgrade Usability Correction Train Implementation Plan'
slug: 'v5-upgrade-usability-correction-train'
size: full
status: active
source: 'docs/specs/archive/2026-07-22-v5-upgrade-usability-correction-train-design.md'
spec_ref: 'docs/specs/archive/2026-07-22-v5-upgrade-usability-correction-train-design.md'
created: 2026-07-22
updated: 2026-07-22
owners:
  - 'Claude (Fable 5) with Chris Purcell / L3DigitalNet'
test_framework: pytest
---

# V5 Upgrade Usability Correction Train Implementation Plan

> **Definition, not state.** Routine progress lives in `.project-pipeline/2026-07-22-v5-upgrade-usability-correction-train/`. This master changes only for appended discovered work or close-out harvest.

## 1. Objective

Deliver Project Standards 5.6.0 with bounded corrections for GitHub issues #20, #21, #22, and #23: an expressible multi-root Python Tooling gate, self-sufficient consumer-conflict diagnostics with governing-option pointers, an informative migration preview exit code, and truthful upgrade documentation — publishing one verified candidate from `main` and closing the issues only after hosted evidence is authoritative.

## 2. Background

The approved design identifies four 5.5.0 defects reported from one real V4 → V5 migration. Python Tooling 1.5 renders checker `include` and `coverage.run.source` from `source_layout` alone, so a second first-party root is inexpressible and migration blocks on two unresolvable conflicts. `CP-CONSUMER-CONFLICT` findings omit the expected value, observed value, and governing option. `init --migrate` preview exits 1 for ready and blocked plans alike. `UPGRADING.md` § 3 understates the legacy-config option surface that migration actually accepts and that conflict resolution requires.

## 3. Scope

### 3.1 In Scope

- Optional per-contribution governing-option pointers in the package contract.
- Enriched `CP-CONSUMER-CONFLICT` findings (values, digests, governing options) and the additive reconciliation-plan schema revision `1.1`.
- Migration preview exit 0 for an applicable, error-free plan.
- Python Tooling 1.6 with `additional_source_roots`, and Standard Bundle Authoring 2.5.
- Catalog 5 integration, `UPGRADING.md`/`docs/usage.md` corrections, 5.6.0 qualification, publication, and issue closeout.

### 3.2 Out of Scope

- Released-payload edits, source-root inference or superset acceptance, retrofitted option metadata on released payloads, raw byte contents on whole-file findings, exit-code changes for apply/no-op/state/reconcile paths, new dependencies, and unrelated cleanup.

### 3.3 Assumptions

- The changes remain MINOR-compatible; evidence of a newly failing prior consumer blocks publication and reopens classification.
- GitHub and signing authority remain available; their absence blocks publication rather than weakening proof.

### 3.4 Constraints

- Use `uv`, Ruff, BasedPyright strict, pytest, candidate-wheel-first package validation, Prettier, and markdownlint.
- Every behavior task proves a right-reason RED and commits only after fresh task verification.
- Unknown consumer values continue to fail closed as conflicts; option metadata is declared, never inferred.
- Follow `meta/versioning.md`: release commit on `main` before signed tags, hosted and downloaded-asset proof before issue closure.

## 4. Source Requirements

| ID | Requirement | Source | Priority | Task(s) |
| --- | --- | --- | --- | --- |
| FR-001 | Python Tooling 1.6 merges declared `additional_source_roots` after layout-derived roots into checker `include` and `coverage.run.source` for both layouts and both checkers. | #20 | must | T4 |
| FR-002 | Absent or empty option renders byte-identical Python Tooling 1.5 output. | #20 | must | T4 |
| FR-003 | Schema validation rejects absolute, traversing, empty, backslashed, or duplicate root entries before render. | #20 | must | T4 |
| FR-004 | V4 legacy migration recognizes `/python_tooling/additional_source_roots` and carries it into V5 options. | #20 | must | T4 |
| FR-005 | The package contract accepts optional per-contribution governing-option pointers; absent metadata changes nothing. | #22 | must | T1 |
| FR-006 | Semantic-unit conflicts carry expected/actual values (full JSON fidelity, truncated human); byte-valued and whole-file conflicts carry digests. | #22 | must | T2 |
| FR-007 | Findings list declared pointers, state "no declared option" for explicit empty declarations, and omit the field when metadata is absent. | #22 | must | T2 |
| FR-008 | Python Tooling 1.6 declares governing-option pointers for its option-governed `pyproject.toml` contributions. | #22 | must | T4 |
| FR-009 | The reconciliation-plan schema gains the optional finding fields additively at `schema_version` 1.1, regenerated through repository tooling. | #22 | must | T2 |
| FR-010 | Preview exits 0 for an applicable, error-free plan; blocked, refused, failed, and state-error paths retain their codes; apply/no-op unchanged. | #23 | must | T3 |
| FR-011 | `UPGRADING.md` §§ 1 and 3 and `docs/usage.md` document the corrected exit-code contract and the real migration option surface with a nested example. | #21, #23 | must | T7 |
| FR-012 | Python Tooling 1.6 `adopt.md` states where a migrating V4 consumer sets options before `.standards/config.toml` exists. | #21 | must | T4 |
| FR-013 | Standard Bundle Authoring 2.5 documents governing-option-pointer authoring semantics. | design | must | T5 |
| FR-014 | Catalog 5 retains all predecessors and selects Python Tooling 1.6 and Standard Bundle Authoring 2.5 as compatible defaults. | design | must | T6 |
| FR-015 | One verified 5.6.0 candidate publishes from `main` with signed tags and byte-matching assets. | release contract | must | T8, T9, T10 |
| FR-016 | Issues #20-#23 close only after published and hosted evidence exists. | design | must | T10 |
| NFR-001 | Released payloads, immutable tags, historical selection, and exact-version validation outcomes do not change; diagnostics and exit codes only become more informative. | design | must | T2-T6, T9 |
| NFR-002 | Newly expressible states are bounded by declared closed options or declared metadata; unknown values fail closed. | design | must | T1, T2, T4 |
| NFR-003 | RED/GREEN plus source, artifact, and hosted evidence supports every completion claim. | design | must | T1-T10 |
| NFR-004 | The train passes MINOR classification without newly failing a prior consumer. | version policy | must | T3, T6, T9 |

## 5. Repository and Architecture Context

### 5.1 Relevant Components

| Component | Purpose | Paths |
| --- | --- | --- |
| Package contract | contribution declarations, option schema, payload validation | `src/project_standards/package_contract/payload.py` |
| Control-plane planner/adapters | conflict classification and finding emission | `src/project_standards/control_plane/planner.py`, `src/project_standards/control_plane/adapters/whole_file.py` |
| Diagnostics and schemas | `ControlFinding`, public schemas, JSON/human rendering | `src/project_standards/control_plane/diagnostics.py`, `src/project_standards/control_plane/schemas.py`, `src/project_standards/control_plane/cli.py` |
| Immutable packages | providers, resources, migrations, docs | `standards/python-tooling/versions/`, `standards/standard-bundle-authoring/versions/` |
| Catalog/projection/release | selection, installed mirror, release truth | `catalogs/5.toml`, `standards/catalog.md`, `meta/versioning.md`, `docs/handoff/` |

### 5.2 Existing Behavior

`_source_roots` (Python Tooling provider) maps `source_layout` to fixed include/source lists with no additive option. `ContributionDeclaration` has no option linkage beyond gating `when_any` predicates. `ControlFinding` has no expected/actual/option fields and `PublicFindingSchema` is closed at `schema_version` 1.0. `_emit_migration_plan` returns 1 unconditionally for previews; tests pin exit 1 for an applicable plan. `UPGRADING.md` § 3 lists only ownership escapes; `docs/usage.md` states preview always exits 1.

### 5.3 Files Expected to Change

| Path | Action | Purpose | Task |
| --- | --- | --- | --- |
| `src/project_standards/package_contract/payload.py` | modify | `governing_options` declaration and pointer validation | T1 |
| `src/project_standards/control_plane/diagnostics.py`, `schemas.py`, `planner.py`, `adapters/whole_file.py`, `cli.py` | modify | enriched findings, schema 1.1, human truncation | T2 |
| `src/project_standards/control_plane/cli.py` | modify | preview exit code | T3 |
| `standards/python-tooling/versions/1.6/**` | create | #20 successor payload | T4 |
| `standards/standard-bundle-authoring/versions/2.5/**` | create | authoring contract documentation | T5 |
| `standards/python-tooling/standard.toml`, `standards/standard-bundle-authoring/standard.toml`, `catalogs/5.toml`, projections, `standards/catalog.md`, family landing pages, activation/reconstruction test constants | modify/generate | compatible integration | T6 |
| `UPGRADING.md`, `docs/usage.md` | modify | #21/#23 documentation | T7 |
| version/changelog/status/deployment/session files | modify | release and closeout | T8, T10 |

### 5.4 Dependencies

No dependency changes. Use locked Python 3.14+, PyYAML, Pydantic, pytest, Ruff, BasedPyright, npm tooling, GitHub CLI, and GPG.

## 6. Test Strategy

- **Framework:** pytest, run through uv. Config: `pyproject.toml` · Test root: `tests/` · Shared fixtures: existing control-plane and package-contract fixture helpers.
- **Commands:** targeted `uv run pytest tests/control_plane/test_cli.py -k "expr"`; full lanes per § 13.
- Assert public findings, exits/output, rendered option values, schema bytes, and convergence; mock calls alone do not prove behavior.
- Never run two `uv run` pytest suites concurrently; never edit docs or `.standards/` while a suite runs.
- **Coverage is a diagnostic, not a gate.** Acceptance is Appendix B going green.

### 6.1 RED-GREEN-REFACTOR contract

Each behavior task executes RED, Verify RED, minimum GREEN, Verify GREEN, bounded REFACTOR, and Verify Task. A wrong-reason RED stops. Refactor failure returns to GREEN and is recorded in notes.

### 6.2 Test categories

| Category | Purpose | Location |
| --- | --- | --- |
| Contract/regression | declarations, findings, exit codes, #20-#23 | `tests/package_contract/`, `tests/control_plane/` |
| Integration/compatibility | migration, lifecycle, source/wheel | `tests/control_plane/`, `tests/package_compatibility/` |
| End-to-end | candidate dogfood and publication | § 13 and GitHub evidence |

### 6.3 TDD exceptions

| Task | Exception reason | Objective validation |
| --- | --- | --- |
| T5 | documentation-only payload; behavior is contract prose | reconstruction/selection tests, package gates, Markdown gate |
| T6 generated artifacts | schema, projection, and catalog render have no independent behavior RED; selection changes retain T6.1/T6.2 | graph/schema/projection/catalog gates |
| T7 | documentation correction | Prettier/markdownlint plus content inspection commands |
| T8-T10 | release preparation, qualification, and external publication are not behavior changes | version/build/hash/hosted/ref/issue evidence |

## 7. Execution Summary (dependency index)

| Task | Title | Phase | Depends on | Requirement(s) | Primary verification |
| --- | --- | --- | --- | --- | --- |
| T1 | Governing-option contribution metadata | P1 | None | FR-005, NFR-002-003 | package-contract pytest |
| T2 | Enriched consumer-conflict findings | P1 | T1 | FR-006-007, FR-009, NFR-001-003 | planner/adapter/CLI/schema pytest |
| T3 | Migration preview exit code | P1 | None | FR-010, NFR-001, NFR-003-004 | CLI/migration pytest |
| T4 | Python Tooling 1.6 successor | P2 | T1, T2 | FR-001-004, FR-008, FR-012, NFR-001-003 | issue fixture/migration/reconstruction |
| T5 | Standard Bundle Authoring 2.5 | P2 | T1 | FR-013, NFR-001, NFR-003 | reconstruction/selection/package gates |
| T6 | Catalog 5 integration | P3 | T4, T5 | FR-014, NFR-001, NFR-003-004 | graph/projection/matrix |
| T7 | Upgrade documentation corrections | P3 | T3 | FR-011, NFR-003 | doc gate plus content inspection |
| T11 | Cross-agent Codex implementation review | P4 | T6, T7 | NFR-003 | reviewed findings dispositioned |
| T12 | Null-fidelity conflict values and exhaustive parity regression | P4 | T11 | FR-002, FR-006, NFR-001, NFR-003 | diagnostics/parity pytest |
| T8 | Prepare one 5.6.0 candidate | P4 | T6, T7, T11, T12 | FR-015, NFR-003 | version/build/hash gates |
| T9 | Qualify the exact candidate | P4 | T8 | FR-015, NFR-001, NFR-003-004 | complete § 13 gate |
| T10 | Publish, close issues, close out | P5 | T9 | FR-015-016, NFR-003 | refs/workflows/assets/issues/parity |

## 8. Implementation Tasks

## Phase P1: Contract and Diagnostics Foundation

### T1: Governing-option contribution metadata

- **goal:** A contribution may declare the option pointers that govern its rendered value; absent metadata loads, plans, and verifies exactly as today. · **phase:** P1 · **depends_on:** [] · **requirements:** [FR-005, NFR-002, NFR-003] · **priority:** must
- **files:** `src/project_standards/package_contract/payload.py` (modify), generated package schemas, `tests/package_contract/` (test)
- **acceptance:** absent, empty, and populated declarations all validate and round-trip (TC-T1-001); each declared pointer must resolve against the payload's declared option schema and an unresolvable pointer fails payload validation at load (TC-T1-002); every released payload still loads and verifies unchanged (TC-T1-003).
- **sub-tasks:**
  - **T1.1 RED** — add contract tests for absent/empty/populated `governing_options` and an unresolvable pointer; expected failure: the field is rejected as unknown.
  - **T1.2 Verify RED** — confirm unknown-field rejection, not collection errors.
  - **T1.3 GREEN** — add the optional field with pointer-resolution validation; regenerate package schemas through repository tooling.
  - **T1.4 Verify GREEN** — focused package-contract tests plus schema check.
  - **T1.5 REFACTOR** — keep pointer resolution shared with predicate validation only if it stays behavior-identical; otherwise none.
  - **T1.6 Verify Task** — focused tests, `uv run ruff check .`, `uv run ruff format --check .`, `uv run basedpyright`, schema gates; commit with IDs.

### T2: Enriched consumer-conflict findings

- **goal:** Both `CP-CONSUMER-CONFLICT` sites emit expected/actual values or digests and governing-option pointers, with full JSON fidelity, truncated human excerpts, and an additive schema revision. · **phase:** P1 · **depends_on:** [T1] · **requirements:** [FR-006, FR-007, FR-009, NFR-001, NFR-002, NFR-003] · **priority:** must
- **files:** `src/project_standards/control_plane/diagnostics.py`, `schemas.py`, `planner.py`, `adapters/whole_file.py`, `cli.py` (modify), `src/project_standards/schemas/reconciliation-plan.schema.json` (generate), `tests/control_plane/` (test)
- **acceptance:** semantic-unit conflicts carry expected/actual values and semantic digests in `--json` (TC-T2-001); whole-file and byte-valued conflicts carry digests only (TC-T2-002); populated pointers are listed, an explicitly empty declaration yields the no-declared-option statement, and absent metadata omits the fields (TC-T2-003); human output appends bounded single-line excerpts while JSON keeps full fidelity (TC-T2-004); the regenerated schema is additive at `schema_version` 1.1 and unset fields are omitted from JSON (TC-T2-005).
- **sub-tasks:**
  - **T2.1 RED** — add planner/adapter/CLI/schema regressions for the five acceptance behaviors; expected failure: findings carry no value, digest, or option fields.
  - **T2.2 Verify RED** — confirm missing-field failures, not fixture or import errors.
  - **T2.3 GREEN** — add optional `ControlFinding` fields, populate both sites from the in-scope values and the owning contribution's declaration, add human truncation, advance `PublicFindingSchema` and `schema_version`, regenerate the schema artifact.
  - **T2.4 Verify GREEN** — focused planner/adapter/CLI suites plus schema gate.
  - **T2.5 REFACTOR** — extract one bounded excerpt helper; no rendering redesign.
  - **T2.6 Verify Task** — focused tests, Ruff, BasedPyright, schema/projection gates; commit with IDs.

### T3: Migration preview exit code

- **goal:** Preview exits 0 exactly when the emitted plan is applicable and error-free; every other path keeps its current code, and JSON `ok`/`applicable` agree with the exit. · **phase:** P1 · **depends_on:** [] · **requirements:** [FR-010, NFR-001, NFR-003, NFR-004] · **priority:** must
- **files:** `src/project_standards/control_plane/cli.py` (modify), `tests/control_plane/test_cli.py`, `tests/control_plane/test_migration.py` (test)
- **acceptance:** ready preview exits 0 with `ok: true` (TC-T3-001); blocked preview exits 1 and refused apply exits 1 without writes (TC-T3-002); successful apply 0, failed apply 1, no-op 0, state error 2, and recovery previews follow the same readiness rule (TC-T3-003).
- **sub-tasks:**
  - **T3.1 RED** — update the pinned exit-code assertions to the readiness contract; expected failure: ready preview still returns 1.
  - **T3.2 Verify RED** — confirm only exit-code assertions fail while output-shape assertions hold.
  - **T3.3 GREEN** — return 0 from `_emit_migration_plan` for an applicable plan that is not a refused apply; change nothing else.
  - **T3.4 Verify GREEN** — focused CLI and migration suites.
  - **T3.5 REFACTOR** — none anticipated; record the assessment.
  - **T3.6 Verify Task** — focused tests, Ruff, BasedPyright; commit with IDs.

## Phase P2: Versioned Successors

### T4: Python Tooling 1.6 successor

- **goal:** Python Tooling 1.6 makes additional first-party roots expressible, recognized in legacy migration, documented for the migration phase, and self-describing via governing-option pointers. · **phase:** P2 · **depends_on:** [T1, T2] · **requirements:** [FR-001, FR-002, FR-003, FR-004, FR-008, FR-012, NFR-001, NFR-002, NFR-003] · **priority:** must
- **files:** `standards/python-tooling/versions/1.6/**` (create), issue #20 fixture, migration/provider/reconstruction tests
- **acceptance:** declared roots merge after layout-derived roots, deduplicated and order-preserving, into both checker `include` and `coverage.run.source` for both layouts and both checkers (TC-T4-001); empty option renders byte-identical 1.5 output (TC-T4-002); absolute, traversing, empty, backslashed, and duplicate entries fail schema resolution before render (TC-T4-003); the issue #20 legacy fixture resolves both reported conflicts from `.project-standards.yml` and converges, while an unmatched consumer value remains a conflict now naming the governing pointer (TC-T4-004); `adopt.md` documents the migration-phase option location and 1.5 payload bytes are unchanged (TC-T4-005); the full immutable 1.6 copy reconstructs from source and wheel (TC-T4-006).
- **sub-tasks:**
  - **T4.1 RED** — add the #20 fixture and merge/rejection/migration cases against 1.5; expected failure: the option is unknown and the conflicts are unresolvable.
  - **T4.2 Verify RED** — confirm the reported conflict pair reproduces and the option is rejected, not mis-collected.
  - **T4.3 GREEN** — author the full immutable 1.6 payload: schema option, `_source_roots` merge, migration wiring with the recognized key, `governing_options` declarations, documentation, manifest, and integrity inventory.
  - **T4.4 Verify GREEN** — focused provider/migration/reconstruction suites and package gates.
  - **T4.5 REFACTOR** — keep the merge helper single-purpose; no provider redesign.
  - **T4.6 Verify Task** — focused tests, immutable-predecessor diff proof, package/static/Markdown gates; commit with IDs.

### T5: Standard Bundle Authoring 2.5

- **goal:** The internal authoring standard documents governing-option-pointer semantics: declare exactly the options that can change a rendered unit, an empty list for fixed units, and never claim options that cannot produce the value. · **phase:** P2 · **depends_on:** [T1] · **requirements:** [FR-013, NFR-001, NFR-003] · **priority:** must
- **files:** `standards/standard-bundle-authoring/versions/2.5/**` (create), reconstruction/selection tests
- **acceptance:** 2.5 is selected-resolvable and documents absent/empty/populated semantics and the truthful-claim rule (TC-T5-001); 2.4 payload bytes are unchanged and the full immutable 2.5 copy reconstructs from source and wheel (TC-T5-002).
- **sub-tasks:**
  - **T5.1 RED** — add selection/reconstruction expectations for 2.5; expected failure: the version is absent.
  - **T5.2 Verify RED** — confirm absence, not payload invalidity.
  - **T5.3 GREEN** — author the full immutable 2.5 copy with updated documentation, manifest, and integrity inventory.
  - **T5.4 Verify GREEN** — reconstruction/selection suites and package gates.
  - **T5.5 REFACTOR** — none anticipated; record the assessment.
  - **T5.6 Verify Task** — focused tests, immutable diff proof, package/Markdown gates; commit with IDs.

## Phase P3: Integration and Documentation

### T6: Integrate successors into Catalog 5

- **goal:** Retain all predecessor versions, select Python Tooling 1.6 and Standard Bundle Authoring 2.5 as defaults, and prove the compatible source/wheel lifecycle and MINOR classification. · **phase:** P3 · **depends_on:** [T4, T5] · **requirements:** [FR-014, NFR-001, NFR-003, NFR-004] · **priority:** must
- **files:** family `standard.toml` indexes, `catalogs/5.toml`, payload projections, `standards/catalog.md`, family landing pages, activation/reconstruction/matrix/release tests
- **acceptance:** defaults and exact predecessors resolve (TC-T6-001); transitions converge and disable/re-enable stays clean (TC-T6-002); source/wheel compatibility matrix passes (TC-T6-003); the release classifier reports MINOR with prior-pass proof (TC-T6-004).
- **sub-tasks:**
  - **T6.1 RED** — update selection/matrix expectations; expected failure: successors are absent from the catalog.
  - **T6.2 Verify RED** — confirm integration absence, not payload invalidity.
  - **T6.3 GREEN** — append family versions, flip catalog roles, regenerate projections/schemas/catalog, refresh landing pages and test constants.
  - **T6.4 Verify GREEN** — catalog/lifecycle/reconstruction/matrix/classification tests.
  - **T6.5 REFACTOR** — only bounded fixture deduplication if needed.
  - **T6.6 Verify Task** — package/graph/schema/projection/catalog/source-wheel/static/immutable checks; commit with IDs.

### T7: Upgrade documentation corrections

- **goal:** `UPGRADING.md` and `docs/usage.md` state the readiness exit-code contract and the real legacy-config option surface with one nested example, scoping the unclaimed-setting warning to genuinely unrecognized keys. · **phase:** P3 · **depends_on:** [T3] · **requirements:** [FR-011, NFR-003] · **priority:** must
- **files:** `UPGRADING.md`, `docs/usage.md` (modify)
- **acceptance:** § 1 documents preview exit 0 ready / 1 blocked beside the workflow and `docs/usage.md` replaces the always-1 statement (TC-T7-001); § 3 states that any setting a selected package's migration provider recognizes is accepted under its legacy namespace, shows the nested `python_tooling.ruff.extend_exclude` example, and keeps the ownership-escape list as the whole-file subset (TC-T7-002); Prettier and markdownlint pass (TC-T7-003).
- **sub-tasks:**
  - **T7.1 RED** — record the TDD exception; capture failing content-inspection greps for the new statements.
  - **T7.2 Verify RED** — confirm the inspections fail against current docs.
  - **T7.3 GREEN** — apply the § 1, § 3, and usage corrections.
  - **T7.4 Verify GREEN** — content inspections pass; doc gate green.
  - **T7.5 REFACTOR** — none anticipated; record the assessment.
  - **T7.6 Verify Task** — `npx prettier --check`, `npx markdownlint-cli2`, content inspections; commit with IDs.

## Phase P4: Candidate and Qualification

### T11: Cross-agent Codex implementation review

- **goal:** An opposite-provider Codex review of the train's implementation commits completes before release preparation, with every finding dispositioned (fixed via appended discovered work, or rejected with recorded technical rationale). · **phase:** P4 · **depends_on:** [T6, T7] · **requirements:** [NFR-003] · **priority:** must
- **files:** ephemeral review bundle and logs; master plan only if findings append discovered work
- **acceptance:** the review runs through the cross-agent skill against the train's diff with the design doc as context (TC-T11-001); every finding has a disposition recorded in notes before T8 starts (TC-T11-002).
- **sub-tasks:**
  - **T11.1 RED** — user-directed review gate; record the TDD exception (review, not behavior).
  - **T11.2 Verify RED** — mark skipped with the exception reason.
  - **T11.3 GREEN** — invoke the cross-agent skill for a bounded adversarial review of the train's implementation; capture the report.
  - **T11.4 Verify GREEN** — disposition every finding; append discovered work for accepted defects.
  - **T11.5 REFACTOR** — none.
  - **T11.6 Verify Task** — dispositions recorded in notes; no undispositioned finding; commit any fixes under their own task IDs.

### T12: Null-fidelity conflict values and exhaustive parity regression

- **goal:** Accepted Codex findings are fixed: a JSON `null` expected/actual value serializes as an explicit null and renders as `null` in human output, and Python Tooling 1.5/1.6 rendering parity is proven for every materialized contribution across representative configurations. · **phase:** P4 · **depends_on:** [T11] · **requirements:** [FR-002, FR-006, NFR-001, NFR-003] · **priority:** must
- **files:** `src/project_standards/control_plane/diagnostics.py`, `planner.py`, `cli.py` (modify), `tests/control_plane/`, `tests/package_contract/test_python_tooling_reconstruction.py` (test)
- **acceptance:** a semantic conflict whose expected or actual value is JSON `null` emits `"expected": null` / `"actual": null` in `--json` and `null` in human output, distinguishable from unset fields that stay omitted (TC-T12-001); the parity regression derives its matrix from the 1.5 manifest's materialized contributions, compares provider-rendered and static units across default, flat/pyright, and options-set configurations, and asserts declared roots appear in ruff `src` (TC-T12-002).
- **sub-tasks:**
  - **T12.1 RED** — add null-value emission/serialization/rendering regressions and the manifest-derived parity regression; expected failure: null values vanish and the old seven-scope loop is the only parity proof.
  - **T12.2 Verify RED** — confirm null omission and coverage-gap failures, not fixture errors.
  - **T12.3 GREEN** — track null presence on `ControlFinding`, emit explicit nulls in JSON and human output, and replace the parity loop with the manifest-derived matrix.
  - **T12.4 Verify GREEN** — focused diagnostics/planner/CLI and reconstruction suites.
  - **T12.5 REFACTOR** — keep presence tracking private to the finding shape; no rendering redesign.
  - **T12.6 Verify Task** — focused tests, Ruff, BasedPyright, schema gate; commit with IDs.

### T8: Prepare one 5.6.0 candidate

- **goal:** Create one release commit and one wheel/sdist pair as sole candidate evidence. · **phase:** P4 · **depends_on:** [T6, T7, T11, T12] · **requirements:** [FR-015, NFR-003] · **priority:** must
- **files:** version/lock/changelog/status/deployment/session files and build outputs
- **acceptance:** versions agree across `pyproject.toml`, changelog, and docs (TC-T8-001); prepared/published wording is truthful (TC-T8-002); one artifact pair has recorded hashes (TC-T8-003); the extracted wheel reports 5.6.0 and the successors (TC-T8-004).
- **sub-tasks:**
  - **T8.1 RED** — run 5.6.0 inventory assertions; expected failure: repository is 5.5.0.
  - **T8.2 Verify RED** — confirm only release references fail.
  - **T8.3 GREEN** — update authorized metadata, refresh lock, build once cleanly, extract wheel, record hashes in logs.
  - **T8.4 Verify GREEN** — version/release/docs/installed probes.
  - **T8.5 REFACTOR** — none.
  - **T8.6 Verify Task** — release/static/docs/diff checks; commit `release: prepare project standards 5.6.0` with IDs.

### T9: Qualify the exact candidate

- **goal:** Pass every local gate with the extracted T8 wheel first on `PYTHONPATH`, without rebuilding. · **phase:** P4 · **depends_on:** [T8] · **requirements:** [FR-015, NFR-001, NFR-003, NFR-004] · **priority:** must
- **files:** ephemeral logs only unless a genuine defect appends discovered work
- **acceptance:** static/security/Markdown/coherence pass (TC-T9-001); package gates pass (TC-T9-002); ordinary/compatibility/performance lanes pass (TC-T9-003); dogfood/classifier pass (TC-T9-004); hashes stay identical (TC-T9-005).
- **sub-tasks:**
  - **T9.1 RED** — assert candidate paths/hashes exist; expected failure: none after T8, so record the qualification TDD exception.
  - **T9.2 Verify RED** — mark skipped with the exception reason and retain precondition evidence.
  - **T9.3 GREEN** — run § 13 without rebuild; deterministic failure creates discovered work.
  - **T9.4 Verify GREEN** — re-run only transient external queries; keep deterministic evidence single-run.
  - **T9.5 REFACTOR** — none.
  - **T9.6 Verify Task** — re-hash, validate plan/checklists, confirm clean tracked tree and release identity.

## Phase P5: Publication and Close-out

### T10: Publish, verify, close issues, and close out

- **goal:** Publish exact 5.6.0 from `main`, verify it independently, close #20-#23, synchronize branches, and harvest durable facts. · **phase:** P5 · **depends_on:** [T9] · **requirements:** [FR-015, FR-016, NFR-003] · **priority:** must
- **files:** Git/GitHub state plus status/deployment/session/plan closeout
- **acceptance:** the release commit precedes both signed annotated tags and `git verify-tag` succeeds for `v5.6.0` and `v5` (TC-T10-001); commit-bound workflows pass (TC-T10-002); downloads match T8 hashes (TC-T10-003); issues close only after TC-T10-005 branch parity (TC-T10-004); branches/remotes/tags/release/handoff/worktree agree before issue closure (TC-T10-005).
- **sub-tasks:**
  - **T10.1 RED** — query refs/release/issues; expected failure: 5.6.0 absent and issues open.
  - **T10.2 Verify RED** — confirm authoritative absence, not query/auth failure.
  - **T10.3 GREEN** — land/push `main`; sign/push annotated `v5.6.0`; move the signed `v5` tag; release exact assets; wait/verify workflows and downloads; synchronize and confirm `testing` parity; only then close issues.
  - **T10.4 Verify GREEN** — re-query signatures, release, workflows, assets, issues, and parity independently.
  - **T10.5 REFACTOR** — update durable truth, harvest notes, close plan, delete scratch after commit.
  - **T10.6 Verify Task** — handoff validation, clean/parity proof, publication-record/closeout commit and pushes.

## 9. Cross-Cutting Requirements

| Concern | Verification | Task |
| --- | --- | --- |
| Fail-closed input/ownership | rejection cases, unmatched-value conflict retention | T1-T4 |
| Supply chain/compatibility | audits, signed refs, hash parity, source/wheel matrix | T6, T8-T10 |
| Performance | existing serial lane; bounded excerpt rendering | T2, T9 |
| Documentation | successor docs, upgrade docs, changelog/status/deployment/handoff | T4, T5, T7, T8, T10 |

## 10. Integration and Migration

### 10.1 Integration Sequence

Contract foundation → diagnostics and exit code → independent successors → Catalog 5 and docs → single candidate → qualification → publication.

### 10.2 Data or State Migration

- **Required:** yes · **Rollback supported:** pre-publication commit reversal; post-publication correcting release only · **Idempotent:** preview/apply/reconcile converge.
- V4 state migrates only through declared recognized settings. Full-version tags and released payloads are immutable.

### 10.3 Compatibility Plan

Exact predecessors remain selected and tested; compatible `latest` advances. Source/wheel tests cover transitions, disable/re-enable, unknown refusal, and predecessor CLI behavior. The schema revision is additive; consumers of `schema_version` 1.0 payloads keep every existing field.

## 11. Risks and Decisions

| ID | Risk | Likelihood | Impact | Mitigation | Owning task |
| --- | --- | --- | --- | --- | --- |
| R-001 | governing-option claims drift from actual rendering | low | med | contract pointer validation plus truthful-claim authoring rule | T1, T5 |
| R-002 | value excerpts bloat or leak into human output | low | low | bounded single-line truncation; digests for bytes | T2 |
| R-003 | exit-code change breaks a consumer script relying on always-1 | low | med | documented contract change; failure exit becomes success only | T3, T7 |
| R-004 | merged roots regress existing consumers | low | high | byte-identical empty-option proof and predecessor byte-stability | T4 |
| R-005 | projections or artifacts drift | low | high | reconstruction, immutable diffs, hashes | T6, T8-T10 |

| ID | Decision | Rationale | Affected task(s) |
| --- | --- | --- | --- |
| D-001 | one closed additive option covers both include and coverage source | the two gate surfaces must stay in lockstep | T4 |
| D-002 | governing options are declared, never derived from predicates | predicates gate materialization, not value provenance | T1, T2, T5 |
| D-003 | whole-file conflicts carry digests, not bytes | contents are large/binary and available from the action stream | T2 |
| D-004 | preview exit aligns with `ok`/`applicable` | the exit code and JSON must not disagree | T3 |
| D-005 | publish as MINOR only after prior-pass proof | version policy | T6, T9 |

## 12. Open Questions

None. Discoveries that alter consumer behavior, ownership, versions, or classification block and return to the design checkpoint.

## 13. Final Verification (definition of done)

With the extracted candidate first on `PYTHONPATH`, without rebuilding:

1. `uv run ruff format --check .`; `uv run ruff check .`; `uv run basedpyright`.
2. `uv run coverage erase`; `uv run coverage run --source=project_standards -m pytest -m "not performance and not compatibility"`; `uv run pytest -m compatibility -n 4 --dist load --max-worker-restart=0`; `uv run pytest -m performance`; `uv run coverage report`.
3. `uv run pip-audit`.
4. `uv run project-standards standards validate-packages --root . --json`; `uv run project-standards standards validate-graph --root . --require-all-manifests --json`; `uv run project-standards standards generate-package-schemas --root . --check`; `uv run project-standards standards sync-payload-projection --root . --check`; `uv run project-standards standards render-catalog --root . --check`.
5. `npm ci`; `uv run pytest tests/coherence`; `npx prettier --check .`; `npx markdownlint-cli2 "**/*.md"`.
6. Candidate dogfood validation, frontmatter format check, reconcile JSON inspection, Agent Handoff conformance/drift/size, and release classification against the published baseline.
7. Re-hash wheel/sdist; `uv run scripts/plan.py validate docs/plans/2026-07-22-v5-upgrade-usability-correction-train-plan.md`.

Done also requires complete checklist evidence, signed/hosted/asset proof, closed #20-#23, updated handoff truth, clean worktree, and local/remote `main`/`testing` parity.

## 14. Close-out

- **Completed:** _pending_ · final commit _pending_
- **Deviations / decisions harvested from notes:** _pending close-out_
- **Risks closed / accepted:** _pending close-out_
- **Deferred work filed:** _pending close-out_

After harvest and close-out commit, delete `.project-pipeline/2026-07-22-v5-upgrade-usability-correction-train/`.

## Appendix A. Interface or Schema Changes

| Interface/model | Change | Compatibility |
| --- | --- | --- |
| `ContributionDeclaration` | optional `governing_options` pointer list with schema-resolution validation | additive; released payloads unchanged |
| `ControlFinding` / `PublicFindingSchema` | optional expected/actual value, digest, and governing-option fields; `schema_version` 1.1 | additive; unset fields omitted from JSON |
| `init --migrate` preview exit | 0 when applicable and error-free; nonzero paths unchanged | documented contract change; converts a failure exit to success only |
| Python Tooling config | `additional_source_roots` closed additive option | default empty renders 1.5-identical output |

## Appendix B. Test Matrix (traceability)

| Test ID | Requirement | Task | Test path | Type |
| --- | --- | --- | --- | --- |
| TC-T1-001..003 | FR-005, NFR-002-003 | T1 | `tests/package_contract/` contract/regression | contract |
| TC-T2-001..005 | FR-006-007, FR-009, NFR-001-003 | T2 | `tests/control_plane/` planner/adapter/CLI/schema | contract/regression |
| TC-T3-001..003 | FR-010, NFR-001, NFR-003-004 | T3 | `tests/control_plane/test_cli.py`, `tests/control_plane/test_migration.py` | regression |
| TC-T4-001..006 | FR-001-004, FR-008, FR-012, NFR-001-003 | T4 | provider/migration/reconstruction suites | integration/regression |
| TC-T5-001..002 | FR-013, NFR-001, NFR-003 | T5 | reconstruction/selection suites | contract |
| TC-T6-001..004 | FR-014, NFR-001, NFR-003-004 | T6 | catalog/lifecycle/matrix/release suites | integration/compatibility |
| TC-T7-001..003 | FR-011, NFR-003 | T7 | doc gate plus content inspections | documentation |
| TC-T11-001..002 | NFR-003 | T11 | cross-agent review report and dispositions | end-to-end |
| TC-T12-001..002 | FR-002, FR-006, NFR-001, NFR-003 | T12 | diagnostics null-fidelity and manifest-derived parity | regression |
| TC-T8-001..004 | FR-015, NFR-003 | T8 | version/docs/build/integration probes | end-to-end |
| TC-T9-001..005 | FR-015, NFR-001, NFR-003-004 | T9 | complete local qualification | end-to-end |
| TC-T10-001..005 | FR-015-016, NFR-003 | T10 | refs/workflows/assets/issues/parity | end-to-end |

## Appendix C. Deferred Work (identified at authoring)

None at authoring. New out-of-design behavior requires an issue or owner-authorized appended task.
