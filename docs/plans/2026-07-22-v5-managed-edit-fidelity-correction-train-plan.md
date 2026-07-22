---
title: 'V5 Managed-Edit Fidelity Correction Train Implementation Plan'
slug: 'v5-managed-edit-fidelity-correction-train'
size: standard
status: active
source: 'docs/specs/archive/2026-07-22-v5-managed-edit-fidelity-correction-train-design.md'
spec_ref: 'docs/specs/archive/2026-07-22-v5-managed-edit-fidelity-correction-train-design.md'
created: 2026-07-22
updated: 2026-07-22
owners:
  - 'Claude (Fable 5) with Chris Purcell / L3DigitalNet'
test_framework: pytest
---

# V5 Managed-Edit Fidelity Correction Train Implementation Plan

> **This file is definition, not state.** Committed to `docs/plans/2026-07-22-v5-managed-edit-fidelity-correction-train-plan.md`, read-only during implementation except at two checkpoints: (1) inserting discovered work as a new task, followed by `plan.py sync`; (2) close-out harvest. Live progress lives under `.project-pipeline/2026-07-22-v5-managed-edit-fidelity-correction-train/`, not here.

## 1. Objective

Deliver Project Standards 5.7.0 with bounded corrections for GitHub issues #24 and #25: a declarable checker-only tooling root through Python Tooling 1.7's per-root `additional_source_roots` form, and TOML managed-region rewrites that preserve consumer comments at meaningful anchors with no blank-line residue — publishing one verified candidate from `main` and closing the issues only after hosted evidence is authoritative.

## 2. Background

The approved design identifies two 5.6.0 defects reported from real consumer repositories. `additional_source_roots` feeds the checker `include`, Ruff `src`, and `coverage.run.source` from one string list, so a strictly-typed-but-untested tooling root flips the coverage gate red when declared and under-reports the gate when omitted. Separately, the TOML adapter's table- and keyed-set-scope updates splice the new fragment at the first owned statement and reduce the other owned statements to comments at dead offsets: interior comments of a managed multi-line array are displaced below the rewritten block, one stray blank line survives per rewritten statement, and key-scope updates silently delete interior value comments.

## 3. Scope

### 3.1 In Scope

- Anchored comment preservation and full-span consumption in the TOML adapter's UPDATE paths (table, keyed-set, key scopes).
- Python Tooling 1.7 with string-or-table `additional_source_roots` entries and a `coverage` flag; migrations from 1.6 and legacy V4.
- Catalog 5 integration retaining predecessors and advancing the Python Tooling default to 1.7.
- Adoption-guide and upgrade-doc corrections, 5.7.0 qualification, publication, and issue closeout.

### 3.2 Out of Scope

- Released-payload edits; coverage-only (unchecked) roots; extra per-root flags; comment changes to non-TOML adapters; consumer whitespace layout inside rewritten fragments; REMOVE/CREATE/ADOPT/NOOP/PRESERVE behavior; new dependencies.

### 3.3 Assumptions

- The train remains MINOR-compatible; evidence of a newly failing prior consumer blocks publication and reopens classification.
- Publication (merge to `main`, signed tags, GitHub release, issue closure) proceeds only on owner confirmation; its absence leaves the train complete-but-unpublished rather than weakening proof.

### 3.4 Constraints

- Use `uv`, Ruff, BasedPyright strict, pytest, candidate-wheel-first package validation, Prettier, and markdownlint.
- Released payload bytes are immutable; corrections are authored as the new 1.7 payload only.
- Full-suite pytest runs require the extracted candidate wheel first on `PYTHONPATH`; never run two suites concurrently.
- Follow `meta/versioning.md`: release commit on `main` before signed tags, hosted and downloaded-asset proof before issue closure.

## 4. Requirements and Traceability

| ID | Requirement | Source | Priority | Task(s) | Verified by |
| --- | --- | --- | --- | --- | --- |
| FR-001 | 1.7 accepts string or `{path, coverage}` entries; all roots join `include`/`src`, only covered roots join coverage `source`. | #24 | must | T2 | TC-T2-001 |
| FR-002 | String-only configs render byte-identical 1.6 output; `coverage = true` tables render as their string form. | #24 | must | T2 | TC-T2-002 |
| FR-003 | Schema rejects malformed table entries; provider rejects duplicate declared paths across forms. | #24 | must | T2 | TC-T2-003 |
| FR-004 | 1.6 → 1.7 and legacy V4 migrations carry `additional_source_roots` values including table entries. | #24 | must | T2 | TC-T2-004 |
| FR-005 | 1.7 retains the 1.6 governing-option declarations for the affected units. | #24 | must | T2 | TC-T2-005 |
| FR-006 | Table/keyed-set updates consume full spans and comment-only gaps; no blank-line residue. | #25 | must | T1 | TC-T1-002 |
| FR-007 | Harvested comments re-emit above their anchored statement, or above the fragment; key-scope interiors survive above the assignment. | #25 | must | T1 | TC-T1-001 |
| FR-008 | Rewrites are idempotent; `reconcile --check` is `no-op` after a comment-preserving apply. | #25 | must | T1 | TC-T1-006 |
| FR-009 | Catalog 5 retains predecessors and defaults Python Tooling to 1.7. | design | must | T3 | TC-T3-001 |
| FR-010 | 1.7 adoption guide documents the per-root form; upgrade docs state the comment-preservation contract. | design | must | T2, T4 | inspection + doc gate |
| FR-011 | 5.7.0 is built once, verified from the extracted candidate, published from `main` with signed tags and byte-matching assets. | design | must | T5, T6, T7 | T6 gate + T7 evidence |
| FR-012 | Issues #24 and #25 close only after publication evidence is available. | design | must | T7 | closure comments |
| NFR-001 | No released payload, tag, historical selection, or exact-version outcome changes. | design | must | T2, T3 | TC-T3-002 |
| NFR-002 | New states are bounded by closed options; unknown values fail closed. | design | must | T2 | TC-T2-003 |
| NFR-003 | RED before GREEN for behavior changes; release claims carry fresh evidence. | design | must | T1, T2, T6 | checklist evidence |
| NFR-004 | MINOR classification holds; no previously passing consumer outcome fails. | design | must | T6 | release-classification check |

## 5. Repository Context

### 5.1 Relevant Components

| Component | Purpose | Paths |
| --- | --- | --- |
| TOML adapter | Syntax-preserving managed-unit composition | `src/project_standards/control_plane/adapters/toml.py` |
| Python Tooling family | Canonical payload versions and family index | `standards/python-tooling/` |
| Payload projection | Installed copies of canonical payloads | `src/project_standards/payloads/python-tooling/` |
| Catalog 5 | Version selection and roles | `catalogs/5.toml`, `standards/catalog.md` |
| Compatibility proofs | Cross-version reconstruction and activation | `tests/package_compatibility/`, `tests/package_contract/` |

### 5.2 Existing Behavior

`_replacement_edits` splices the new fragment at the first selected statement and replaces each selected statement's code span with its extracted comments, leaving line terminators behind; key-scope updates replace the raw value span outright. Python Tooling 1.6's `_source_roots` appends every declared string to both the include and coverage lists unconditionally.

### 5.3 Expected File Changes

| Path | Action | Purpose | Task |
| --- | --- | --- | --- |
| `src/project_standards/control_plane/adapters/toml.py` | modify | Collector/weaver comment preservation | T1 |
| `tests/control_plane/test_adapters_toml.py` | modify | Byte-exact displacement regressions | T1 |
| `tests/control_plane/test_end_to_end.py` | modify | Annotated-apply reconcile regression | T1 |
| `standards/python-tooling/versions/1.7/` | create | Immutable 1.7 payload copy with per-root scoping | T2 |
| `standards/python-tooling/standard.toml` | modify | 1.7 version entry with aggregate digest | T2 |
| `src/project_standards/payloads/python-tooling/1.7/` | create | Regenerated projection | T3 |
| `tests/package_compatibility/test_python_tooling_reconstruction.py` | modify | 1.6/1.7 parity proofs | T2 |
| `catalogs/5.toml` | modify | Retain predecessors; default 1.7 | T3 |
| `standards/catalog.md` | modify | Regenerated rendered catalog | T3 |
| `standards/python-tooling/README.md`, `adopt.md`, `agent-summary.md` | modify | Family landing pages at 1.7 | T3 |
| `tests/package_contract/test_current_catalog_activation.py` | modify | Activation constants | T3 |
| `UPGRADING.md` | modify | Managed-TOML comment contract | T4 |
| `CHANGELOG.md`, `pyproject.toml` | modify | 5.7.0 release preparation | T5 |

### 5.4 Dependencies

| Dependency       | Type     | Constraint  | Reason                         |
| ---------------- | -------- | ----------- | ------------------------------ |
| `uv` toolchain   | dev      | repo-pinned | Build, env, and gate execution |
| GitHub + signing | external | available   | Publication evidence (T7 only) |

## 6. Test Strategy

- **Framework:** pytest, run through uv. Config: `pyproject.toml` · Test root: `tests/` · Fixtures: `tests/control_plane/fixtures/`, `tests/fixtures/`.
- **Commands:** (permanent reference palette — the `{…}` slots are filled per run, not at authoring)
  - Targeted: `uv run pytest {path}::{test}`
  - Full (candidate-first): `PYTHONPATH=$PWD/build/{runtime} uv run pytest`
  - Lint / format / types: `uv run ruff check .` · `uv run ruff format --check .` · `uv run basedpyright`
- **Coverage is a diagnostic, not a gate.** Acceptance is the Test Cases going green — not a coverage percentage.

### 6.1 RED-GREEN-REFACTOR contract

For every behavior-changing task: RED (focused failing test for wrong/absent behavior) → Verify RED (fails for the right reason) → GREEN (smallest production change) → Verify GREEN (targeted + nearest regressions) → REFACTOR (behavior-preserving) → Verify Task (task tests + ruff + basedpyright, then commit `T{n}: {summary} ({FR ids}, {TC ids})`).

### 6.2 Special cases

- T1's RED evidence was captured in-session before the fix was written (displacement and residue regressions failed byte-exact against the 5.6.0 adapter); the checklist records that evidence rather than re-reverting the fix.
- T3, T4, and T5 are integration/documentation tasks: `TDD exception: catalog wiring, documentation, and release preparation are verified by repository gates (activation tests, doc gate, release-classification check), not new unit RED cycles.`
- T6 and T7 are verification/publication tasks: `TDD exception: they execute existing gates and evidence collection.`

## 7. Execution Summary (dependency index)

| Task | Title | Phase | Depends on | Requirement(s) | Primary verification |
| --- | --- | --- | --- | --- | --- |
| T1 | TOML managed-region comment preservation | P1 | None | FR-006, FR-007, FR-008 | `uv run pytest tests/control_plane/test_adapters_toml.py` |
| T2 | Python Tooling 1.7 per-root coverage scoping | P1 | None | FR-001..FR-005, FR-010 | `uv run pytest tests/package_compatibility/test_python_tooling_reconstruction.py` |
| T3 | Catalog 5 integration | P2 | T2 | FR-009, NFR-001 | `uv run pytest tests/package_contract/test_current_catalog_activation.py` |
| T4 | Upgrade documentation | P2 | T1 | FR-010 | doc gate (Prettier + markdownlint) |
| T5 | Prepare the 5.7.0 candidate | P3 | T1, T2, T3, T4 | FR-011 | `uv build` + version-consistency tests |
| T6 | Qualify the exact candidate | P3 | T5 | FR-011, NFR-003, NFR-004 | full repository gate against extracted wheel |
| T7 | Publish, verify, and close issues | P3 | T6 | FR-011, FR-012 | hosted evidence + issue closure |

## 8. Implementation Tasks

### Phase P1: Behavior Corrections

#### T1: TOML managed-region comment preservation

- **goal:** Table-, keyed-set-, and key-scope UPDATE renders preserve consumer comments at anchored positions and leave no blank-line residue · **depends_on:** [] · **requirements:** [FR-006, FR-007, FR-008] · **priority:** must
- **files:** `src/project_standards/control_plane/adapters/toml.py` (modify), `tests/control_plane/test_adapters_toml.py` (test), `tests/control_plane/test_end_to_end.py` (test)
- **acceptance:** interior-array comments re-emit above their key (TC-T1-001); comment-free updates leave zero stray blank lines (TC-T1-002); own-line comments anchor to the following key (TC-T1-003); absent anchors fall back above the fragment (TC-T1-004); key-scope interior comments survive above the assignment (TC-T1-005); an annotated managed array applies end-to-end and re-checks `no-op` (TC-T1-006); existing fixed-point, removal, and CRLF suites stay green.
- **test cases:** TC-T1-001 `test_toml_table_update_relocates_interior_array_comments_above_their_key` (unit, byte-exact); TC-T1-002 `test_toml_table_update_leaves_no_blank_line_residue` (unit, byte-exact); TC-T1-003 `test_toml_table_update_anchors_own_line_comments_to_the_next_key` (unit); TC-T1-004 `test_toml_table_update_hoists_comments_for_keys_absent_from_the_fragment` (unit); TC-T1-005 `test_toml_key_update_preserves_interior_comments_above_the_assignment` (unit); TC-T1-006 end-to-end annotated reconcile regression (integration).
- **sub-tasks:**
  - **T1.1 RED** — the five adapter regressions above, expected failure: the 5.6.0 adapter displaces comments to dead offsets and leaves terminator blank lines.
  - **T1.2 Verify RED** — `uv run pytest tests/control_plane/test_adapters_toml.py`; failures are byte-mismatch displacement, not collection errors.
  - **T1.3 GREEN** — collector/weaver helpers plus full-span consumption in `toml.py`; key-scope interior harvest.
  - **T1.4 Verify GREEN** — targeted file + `uv run pytest tests/control_plane/`.
  - **T1.5 REFACTOR** — tighten helper naming/docstrings; keep tests green; record "none" if unneeded.
  - **T1.6 Verify Task** — add TC-T1-006, run task tests + `uv run ruff check .` + `uv run basedpyright`; commit with IDs.

#### T2: Python Tooling 1.7 per-root coverage scoping

- **goal:** An immutable 1.7 payload whose `additional_source_roots` accepts per-root coverage scoping with full 1.6 parity for string-only configs · **depends_on:** [] · **requirements:** [FR-001, FR-002, FR-003, FR-004, FR-005, FR-010, NFR-002] · **priority:** must
- **files:** `standards/python-tooling/versions/1.7/` (create), `standards/python-tooling/standard.toml` (modify), `tests/package_compatibility/test_python_tooling_reconstruction.py` (test)
- **acceptance:** mixed entries render `include`/`src` with every root and `source` with only covered roots for both layouts and both checkers (TC-T2-001); string-only parity is byte-exact against 1.6 across the reconstruction matrix (TC-T2-002); malformed tables fail schema and duplicate paths fail the provider (TC-T2-003); 1.6 → 1.7 and legacy V4 migrations carry table entries verbatim (TC-T2-004); governing-option declarations match 1.6 for the affected units (TC-T2-005); `adopt.md` documents the per-root form; payload integrity (per-resource digests, aggregate, family index) validates.
- **test cases:** TC-T2-001 mixed-entry rendering (unit); TC-T2-002 1.6/1.7 byte parity (compatibility); TC-T2-003 schema/provider rejection (unit); TC-T2-004 migration carriage (integration); TC-T2-005 governing-option parity (contract).
- **sub-tasks:**
  - **T2.1 RED** — reconstruction/parity and rendering tests for 1.7, expected failure: version 1.7 does not exist.
  - **T2.2 Verify RED** — `uv run pytest tests/package_compatibility/test_python_tooling_reconstruction.py`; failure is the missing payload, not fixture errors.
  - **T2.3 GREEN** — copy 1.6 → 1.7; edit schema, provider `_source_roots`, migrations, adopt.md; update per-resource digests first, then the aggregate and family index.
  - **T2.4 Verify GREEN** — targeted + `uv run pytest tests/package_contract/`.
  - **T2.5 REFACTOR** — none expected inside the immutable payload; record decision.
  - **T2.6 Verify Task** — task tests + ruff + basedpyright; commit with IDs.

### Phase P2: Integration and Documentation

#### T3: Catalog 5 integration

- **goal:** Catalog 5 retains every predecessor and defaults Python Tooling to 1.7 with regenerated projections and rendered catalog · **depends_on:** [T2] · **requirements:** [FR-009, NFR-001] · **priority:** must
- **files:** `catalogs/5.toml` (modify), `src/project_standards/payloads/python-tooling/1.7/` (create), `standards/catalog.md` (modify), family landing pages (modify), `tests/package_contract/test_current_catalog_activation.py` (test)
- **acceptance:** activation constants prove 1.7 default plus retained predecessors (TC-T3-001); historical catalog selections and exact-version outcomes are unchanged (TC-T3-002); projection sync and catalog rendering are clean.
- **sub-tasks:**
  - **T3.1 RED** — activation-test constants updated to expect 1.7, expected failure: catalog still defaults 1.6.
  - **T3.2 Verify RED** — `uv run pytest tests/package_contract/test_current_catalog_activation.py`; failure is the stale default.
  - **T3.3 GREEN** — catalog entry, projection sync, rendered catalog, landing pages.
  - **T3.4 Verify GREEN** — targeted + `uv run pytest tests/package_contract/ tests/package_compatibility/`.
  - **T3.5 REFACTOR** — none expected; record decision.
  - **T3.6 Verify Task** — task tests + ruff + basedpyright + doc gate; commit with IDs.

#### T4: Upgrade documentation

- **goal:** The upgrade documentation states the managed-TOML comment-preservation contract · **depends_on:** [T1] · **requirements:** [FR-010] · **priority:** must
- **files:** `UPGRADING.md` (modify)
- **acceptance:** the contract (anchored preservation, fragment fallback, no residue) is documented where consumers read upgrade behavior; doc gate green. `TDD exception: documentation; validated by Prettier + markdownlint and inspection.`
- **sub-tasks:**
  - **T4.1 RED** — skipped (TDD exception).
  - **T4.2 Verify RED** — skipped (TDD exception).
  - **T4.3 GREEN** — author the contract paragraph.
  - **T4.4 Verify GREEN** — doc gate.
  - **T4.5 REFACTOR** — none.
  - **T4.6 Verify Task** — Prettier + markdownlint; commit with IDs.

### Phase P3: Candidate, Qualification, and Publication

#### T5: Prepare the 5.7.0 candidate

- **goal:** One 5.7.0 wheel and sdist built from the release-ready tree · **depends_on:** [T1, T2, T3, T4] · **requirements:** [FR-011] · **priority:** must
- **files:** `CHANGELOG.md` (modify), `pyproject.toml` (modify), release goldens (modify)
- **acceptance:** version consistency tests pass; release classification reports MINOR; one candidate build extracted for all artifact-sensitive checks. `TDD exception: release preparation; validated by version-consistency tests and the classification gate.`
- **sub-tasks:**
  - **T5.1 RED** — skipped (TDD exception).
  - **T5.2 Verify RED** — skipped (TDD exception).
  - **T5.3 GREEN** — changelog conversion, version bump, goldens, `uv build`.
  - **T5.4 Verify GREEN** — `uv run pytest tests/test_version_consistency.py` and classification check.
  - **T5.5 REFACTOR** — none.
  - **T5.6 Verify Task** — commit with IDs.

#### T6: Qualify the exact candidate

- **goal:** The full repository gate passes against the extracted 5.7.0 candidate wheel · **depends_on:** [T5] · **requirements:** [FR-011, NFR-003, NFR-004] · **priority:** must
- **files:** none (verification only)
- **acceptance:** Ruff, BasedPyright, full pytest with coverage, compatibility matrix, pip-audit, package/graph/schema/projection gates, Prettier, markdownlint, coherence, dogfood `validate`, reconcile, and release-classification checks all pass against the one candidate. `TDD exception: executes existing gates.`
- **sub-tasks:**
  - **T6.1 RED** — skipped (TDD exception).
  - **T6.2 Verify RED** — skipped (TDD exception).
  - **T6.3 GREEN** — run the gate; fix nothing outside task scope without recording discovered work.
  - **T6.4 Verify GREEN** — all gate commands green in one session.
  - **T6.5 REFACTOR** — none.
  - **T6.6 Verify Task** — record evidence; commit any golden refresh with IDs.

#### T7: Publish, verify, and close issues

- **goal:** 5.7.0 published from `main` with signed tags, verified assets, and issues #24/#25 closed with evidence · **depends_on:** [T6] · **requirements:** [FR-011, FR-012] · **priority:** must
- **files:** none (publication and evidence)
- **acceptance:** owner confirmation obtained before publication; release commit merged to `main`; signed `v5.7.0` and moving `v5` tags; GitHub release with byte-matching assets; all release-commit workflows green; `testing` synchronized; issues closed with release evidence. `TDD exception: publication and evidence collection.`
- **sub-tasks:**
  - **T7.1 RED** — skipped (TDD exception).
  - **T7.2 Verify RED** — skipped (TDD exception).
  - **T7.3 GREEN** — publication sequence per `meta/versioning.md` after owner confirmation.
  - **T7.4 Verify GREEN** — hosted workflow runs and downloaded-asset digests.
  - **T7.5 REFACTOR** — none.
  - **T7.6 Verify Task** — close #24/#25 with evidence; close out the plan.

## 9. Cross-Cutting Requirements

| Concern | Applies? | How verified | Owning task |
| --- | --- | --- | --- |
| Error handling | yes | schema/provider rejection tests; adapter parse re-validation | T1, T2 |
| Compatibility / migration | yes | 1.6/1.7 parity matrix; migration carriage tests | T2, T3 |
| Documentation | yes | doc gate + inspection | T2, T4 |

## 10. Integration or Migration

- **Migration required:** yes (package 1.6 → 1.7 and legacy V4 → 1.7) · **Rollback supported:** no (payloads immutable; consumers may pin 1.6) · **Idempotent:** yes
- Sequence: 1. adapter fix lands (engine) 2. 1.7 payload authored 3. catalog default advances 4. one candidate qualifies 5. publish.
- Consumers on 1.6 see no rendered-byte change until they adopt 1.7; string-only configs stay byte-identical after adoption.

## 11. Risks and Decisions

| ID | Risk | Likelihood | Impact | Mitigation | Owning task |
| --- | --- | --- | --- | --- | --- |
| R-001 | Comment weaving breaks an unforeseen consumer TOML layout | low | med | byte-exact regressions; parse re-validation before write; interleaved-gap conservatism | T1 |
| R-002 | 1.7 parity misses a rendering path and reconciliation churns consumers | low | high | full reconstruction matrix parity proof | T2 |
| R-003 | Aggregate/digest wiring error blocks package validation late | med | low | digests-first wiring order; contract gate in T2 | T2 |

| ID | Decision | Rationale | Affected task(s) |
| --- | --- | --- | --- |
| D-001 | Preserve comments (anchored weave) rather than drop or refuse | Design "Alternatives rejected" 4-6: destruction is data loss; refusal blocks upgrades and needs planner/schema surface | T1 |
| D-002 | Per-root object form over split options or subtraction list | Design "Alternatives rejected" 1-3: one declaration per root; scope stated at declaration | T2 |

## 12. Open Questions

| Question | Blocking? | Owner | Current assumption |
| --- | --- | --- | --- |
| Owner confirmation to publish 5.7.0 | yes (T7 only) | Chris Purcell | Implementation and qualification proceed; T7 waits for confirmation. |

## 13. Final Verification (definition of done)

Run at close-out, evidence recorded in the checklist / notes, summary in §14.

- Full suite green: `PYTHONPATH=$PWD/build/{runtime} uv run pytest`
- Static: `uv run ruff check .` · `uv run ruff format --check .` · `uv run basedpyright`
- Every Must requirement maps to a completed task; every acceptance criterion satisfied.
- Every task `done` or `skipped` with a reason; no open blocker; blocking questions resolved.
- Risks closed or explicitly accepted; documentation current.

## 14. Close-out

- **Completed:** _pending_ · final commit _pending_
- **Deviations / decisions harvested from notes:** _pending close-out_
- **Risks closed / accepted:** _pending close-out_
- **Deferred work filed:** _pending close-out_

Teardown: harvest notes here (+ ADRs/issues) → set `status: complete`, update `updated` → commit master → `rm -rf .project-pipeline/2026-07-22-v5-managed-edit-fidelity-correction-train/`.
