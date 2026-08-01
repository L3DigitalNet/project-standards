---
title: 'Open-Issue Resolution Program Plan'
slug: 'open-issue-resolution-program'
size: full
status: active
source: 'GitHub open-issue inventory frozen 2026-08-01T09:21:01Z; owner-approved TODO decisions'
spec_ref: ''
created: 2026-08-01
updated: 2026-08-01
owners:
  - 'Chris Purcell / L3DigitalNet'
  - 'Coding agent under human review'
test_framework: pytest
---

# Open-Issue Resolution Program Plan

> **This file is definition, not state.** It is the durable map for resolving the 24 issues open at the 2026-08-01T09:21:01Z inventory freeze and three owner-approved TODO tasks. Live progress belongs in phase checklists under `.project-pipeline/2026-08-01-open-issue-resolution-program/`. Large feature work receives an approved specification and child plan before implementation.

## 1. Objective

Resolve the frozen open-issue inventory and the three owner-approved TODO tasks with the fewest practical release trains, without mixing uncertain feature design into corrective work, rewriting immutable payloads, or repeatedly paying full release qualification for isolated fixes.

## 2. Strategy

The inventory frozen at 2026-08-01T09:21:01Z contains 24 open issues. Issue #109 joined the Python Tooling train because fresh adoption can emit a tool-only `pyproject.toml` that the required `uv lock` step rejects. New comments on #80 and #55 strengthen existing acceptance criteria but add no task: #80 reproduces on the exact v5.13.0/Agent Handoff 1.7 release, and #55 confirms that adopting Project Spec for future documents while leaving a house-format corpus outside configured scope is a valid preservation-safe mode.

1. Align the release-level contract before preparing another repository release.
2. Publish the already-verified Agent Handoff 1.8 fix for #80 immediately.
3. Batch Agent Handoff command authority, inventory, diagnostics, and duplicate-registration fixes.
4. Batch migration, planner, and structured-adapter fixes in one control-plane train.
5. Batch Markdown Tooling and Python Tooling successors in one repository release, including the Python Tooling authority and fresh-adoption corrections.
6. Finish the two remaining Agent Handoff consumers as a small manual operational closeout.
7. Dispose of the #84 transient before the control-plane release and resolve documentation independently.
8. Treat #62 and #55 as separate feature programs with approval gates.
9. Close issues only after published-artifact evidence or an accepted no-change disposition.

## 3. Scope

### 3.1 In Scope

- Issues #55, #62, #75–#77, #80, #83, #84, #86–#91, #95, #98, #99, #101, #102, and #105–#109.
- Immutable successor payloads, engine releases, regression-ledger proofs, release qualification, and issue closeout.
- Owner decisions required by #101, #107, #99, #62, and #55.
- Catalog release-level alignment, the Python Tooling authority correction, and final Agent Handoff consumer retirement.

### 3.2 Out of Scope

- Issues opened after the 2026-08-01T09:21:01Z freeze unless appended as owner-approved discovered work.
- Unrelated roadmap features, refactors, or consumer cleanup.
- Retiring `control_plane/provider_inputs.py`; it remains centralized compatibility code until separately reprioritized.
- Rewriting published tags or predecessor payload bytes.
- Pushes, tags, releases, or GitHub writes without explicit authorization at the relevant gate.

### 3.3 Constraints

- Preserve unrelated content in the in-flight changes to `docs/STATUS.md`, `docs/TODO.md`, `docs/adoption-prompt.md`, `docs/handoff/specs-plans.md`, and `docs/handoff/sessions/2026-08.md`.
- Use RED–GREEN–REFACTOR for behavior changes and characterize brownfield behavior first where needed.
- Run `scripts/verify.sh` on intermediate train commits and `scripts/verify.sh --full` after the last content change and at release preparation.
- Build and extract a fresh candidate wheel for installed-authority checks.
- Retain every predecessor package version byte-for-byte and selectable.
- Maintain one issue regression and ledger proof for every corrected defect.

## 4. Requirements

| ID | Requirement | Source | Priority | Task(s) |
| --- | --- | --- | --- | --- |
| REQ-080 | Publish and close the verified SessionStart shim fix. | #80 | must | T1 |
| REQ-075 | Pair Agent Handoff enrichment by semantic rule. | #75 | must | T2 |
| REQ-090 | Exclude lock-authenticated current artifacts from legacy findings. | #90 | must | T3 |
| REQ-091 | Run read-only commands against the currently locked payload before refresh. | #91 | must | T4 |
| REQ-101 | Make the documented pre-apply size/shape checkpoint usable or redefine it accurately. | #101 | must | T5 |
| REQ-102 | Detect legacy and managed startup handlers that would inject twice. | #102 | must | T6 |
| REQ-107 | Align engine and provider secret-reference policy after owner decision. | #107 | must | T7 |
| REQ-076 | Converge create-only→managed transitions over absent targets in one apply. | #76 | must | T9 |
| REQ-077 | Create declared empty managed artifacts instead of planning no-op. | #77 | must | T9 |
| REQ-083 | Produce an actionable V4 Python Tooling migration plan. | #83 | must | T10 |
| REQ-087 | Make managed successor drift actionable and intent-preserving. | #87 | must | T11 |
| REQ-098 | Validate selected Frontmatter IDs before retiring legacy authority. | #98 | must | T12 |
| REQ-105 | Coalesce TOML creates sharing an inline parent. | #105 | must | T13 |
| REQ-106 | Remove JSONC residue without losing comments or line endings. | #106 | must | T14 |
| REQ-088 | Bound Prettier to Markdown Tooling's declared corpus. | #88 | must | T16 |
| REQ-089 | Resolve local `src` source before an untyped editable install. | #89 | must | T17 |
| REQ-095 | Bound Ruff to declared Python source and test roots. | #95 | must | T18 |
| REQ-099 | Preserve or explicitly model Ruff plugin sub-tables. | #99 | must | T19 |
| REQ-086 | Support or explicitly reject monorepos with no implicit Python root. | #86 | must | T20 |
| REQ-108 | Prevent published MCP docs from presenting candidate installation as current. | #108 | must | T22 |
| REQ-109 | Reject fresh Python Tooling adoption before writing when consumer-owned PEP 621 project metadata is absent. | #109; owner decision 2026-08-01 | must | T33 |
| REQ-084 | Reproduce and fix, or evidence-dispose, the transient PyYAML failure. | #84 | should | T23 |
| REQ-062 | Add an approved conformance surface for shared Project Spec boilerplate. | #62 | should | T24, T25 |
| REQ-055 | Add an approved preservation-first house-format conversion path. | #55 | should | T26, T27 |
| REQ-900 | Preserve immutable predecessors and qualify each release train once. | Release contract | must | T1, T8, T15, T21, T28 |
| REQ-901 | Leave no frozen issue open without an accepted disposition. | Owner request | must | T29 |
| REQ-902 | Classify owner-designated catalog majors as MAJOR, releases with a standard-package version advance as MINOR, and releases without one as PATCH. A newly introduced package or a newly advertised version above that package's prior advertised maximum is an advance; internal and reference-only packages count, while older retained history and unadvertised payloads do not. Advertised versions are permanent and cannot be removed in any release. | `docs/TODO.md`; owner decisions 2026-08-01 | must | T30 |
| REQ-903 | Replace Python Tooling 1.10's stale V1-authority statement in the already-planned compatible successor without changing 1.10. | `docs/TODO.md`; owner decision 2026-08-01 | must | T31 |
| REQ-904 | Manually converge and verify the two remaining Agent Handoff consumers, then close the retirement records. | `docs/TODO.md`; owner decision 2026-08-01 | must | T32 |

## 5. Architecture and Test Strategy

| Train | Primary surfaces | Primary tests |
| --- | --- | --- |
| Agent Handoff | `src/project_standards/agent_handoff/`, `standards/agent-handoff/` | `tests/agent_handoff/`, Agent Handoff package contracts |
| Control plane | `src/project_standards/control_plane/` | `tests/control_plane/`, migration fixtures |
| Tooling packages | `standards/markdown-tooling/`, `standards/python-tooling/` | Markdown/Python Tooling package contracts and real-tool oracles |
| Project Spec | `src/project_standards/specs/`, `standards/project-spec/` | `tests/test_spec_*.py`, Project Spec reconstruction |
| Release contract | `meta/versioning.md`, `src/project_standards/package_contract/release.py` | release-classification and CLI matrices |

For every issue: reproduce first, assert observable output, run the nearest subsystem suite, and add a regression-ledger proof. Adapter tasks use parametrized/property-style matrices for ordering, nesting, line endings, comments, and whitespace. Train qualification tasks run package/graph/schema/projection checks, fresh wheel extraction, installed reproductions, the full serial battery, release classification, hosted checks, and asset-byte verification. Real-tool oracles execute the lock-resolved versions and record them with the evidence.

### 5.1 TDD Exceptions

| Task | Reason | Objective validation |
| --- | --- | --- |
| T1 | Implementation already exists; remaining work is release qualification. | Existing #80 regressions and release gates |
| T22 | Historical v5.12.0 is immutable. | Current-doc fix plus future-release contract test |
| T23 | Investigation may establish no repository defect. | Bounded reproduction matrix |
| T24, T26 | Specification and owner approval precede behavior. | Spec validation and child-plan validation |
| T29 | Tracker reconciliation is operational closeout. | Live issue query and handoff/document gates |
| T32 | Consumer retirement is an operational closeout, not new product behavior. | Per-consumer Agent Handoff validation, drift check, and authoritative-branch proof |

## 6. Execution Summary

| Task | Title | Phase | Depends on | Requirement(s) | Primary verification |
| --- | --- | --- | --- | --- | --- |
| T1 | Publish Agent Handoff 1.8 | P1 | T30 | REQ-080, REQ-900 | #80 installed probes and release gate |
| T2 | Correct enrichment pairing | P2 | T1 | REQ-075 | Agent Handoff selected-routing tests |
| T3 | Make legacy inventory lock-aware | P2 | T1 | REQ-090 | legacy and routing tests |
| T4 | Route reads through locked payloads | P2 | T3 | REQ-091 | older-control-plane fixtures |
| T5 | Restore pre-apply reports | P2 | T4 | REQ-101 | enabled-but-unlocked fixtures |
| T6 | Detect duplicate startup injection | P2 | T3 | REQ-102 | Claude/Codex duplicate fixtures |
| T7 | Align secret-reference policy | P2 | T1 | REQ-107 | engine/provider parity matrix |
| T8 | Qualify Agent Handoff train | P2 | T2–T7 | REQ-900 | full release battery |
| T9 | Correct absent-artifact planning | P3 | T8 | REQ-076, REQ-077 | planner/executor matrix |
| T10 | Supply V4 transform evidence | P3 | T8 | REQ-083 | V4 migration fixture |
| T11 | Make successor drift actionable | P3 | T9 | REQ-087 | diagnostic/transition tests |
| T12 | Validate IDs before retirement | P3 | T10 | REQ-098 | migration verification fixture |
| T13 | Coalesce TOML creates | P3 | T9 | REQ-105 | TOML adapter matrix |
| T14 | Normalize JSONC deletion residue | P3 | T9 | REQ-106 | JSONC layout matrix |
| T15 | Qualify control-plane train | P3 | T9–T14, T23 | REQ-900 | full release battery |
| T16 | Bound Markdown formatting scope | P4 | T15 | REQ-088 | real Prettier corpus parity |
| T17 | Fix Python import precedence | P4 | T15 | REQ-089 | real BasedPyright fixture |
| T18 | Bound Ruff scope | P4 | T15 | REQ-095 | real Ruff corpus parity |
| T19 | Preserve Ruff plugin config | P4 | T18 | REQ-099 | semantic ownership tests |
| T20 | Add no-implicit-root layout | P4 | T17–T19 | REQ-086 | monorepo reconstruction |
| T21 | Qualify tooling successors | P4 | T16–T20, T31, T33 | REQ-900 | full release battery |
| T22 | Correct MCP release docs | P5 | T1 | REQ-108 | release-doc contract |
| T23 | Dispose of PyYAML transient | P5 | T8 | REQ-084 | isolated install matrix |
| T24 | Specify conformance lint | P6 | T21 | REQ-062 | approved spec/child plan |
| T25 | Implement conformance lint | P6 | T24 | REQ-062 | child plan and release gate |
| T26 | Specify spec conversion | P7 | T25 | REQ-055 | approved spec/child plan |
| T27 | Implement spec conversion | P7 | T26 | REQ-055 | child plan and semantic audit |
| T28 | Qualify feature release | P7 | T27 | REQ-900 | full release battery |
| T29 | Reconcile tracker and close | P8 | T22–T28, T32 | REQ-901 | zero unresolved frozen issues |
| T30 | Align catalog release levels | P9 | None | REQ-902 | release-level matrix and documentation parity |
| T31 | Correct Python Tooling authority | P9 | T20, T30 | REQ-903 | successor contract and predecessor immutability |
| T32 | Finish Agent Handoff consumer retirement | P9 | T30 | REQ-904 | two consumer validation and drift checks |
| T33 | Guard Python Tooling fresh adoption | P9 | T20, T31 | REQ-109 | no-write preflight and real uv lock fixture |

## 7. Implementation Tasks

Task IDs are permanent and append-only; `depends_on` is the execution authority rather than numeric task or phase order. T30 is the sole program entrypoint. After it completes, T1 and the independent T32 operational closeout become ready.

### Phase P1: Release the Completed Fix

#### T1: Publish Agent Handoff 1.8

- **goal:** Re-verify the existing #80 candidate, publish it from clean `main`, reconcile dogfood clients, and close #80. · **phase:** P1 · **depends_on:** [T30] · **requirements:** [REQ-080, REQ-900] · **priority:** must
- **files:** `standards/agent-handoff/versions/1.8/`, catalog/projection/lock and release/handoff surfaces, `tests/package_contract/test_agent_handoff_1_8.py`
- **acceptance:** exact v5.13.0/Agent Handoff 1.7 direct and harness-style launches reproduce the shim failure; direct, uv-fallback, and unavailable-runtime successor lanes behave correctly for both harnesses; predecessors and published assets verify; any failed prepublication gate aborts publication under §8.1.
- **sub-tasks:**
  - **T1.1 RED** — reproduce the published v5.13.0/Agent Handoff 1.7 failure through both direct and harness-style launch.
  - **T1.2 Verify RED** — confirm published behavior, not environment drift.
  - **T1.3 GREEN** — prepare the existing verified successor for release without redesign.
  - **T1.4 Verify GREEN** — run source and installed-wheel harness probes.
  - **T1.5 REFACTOR** — none; release work must not alter verified behavior.
  - **T1.6 Verify Task** — package checks, fresh wheel, `scripts/verify.sh --full`, hosted checks, asset parity, recovery-gate check, authorized publication and closure.

### Phase P2: Agent Handoff Authority Train

#### T2: Correct enrichment pairing for #75

- **goal:** Attach engine coordinates only to the matching provider rule. · **phase:** P2 · **depends_on:** [T1] · **requirements:** [REQ-075] · **priority:** must
- **files:** `src/project_standards/agent_handoff/cli.py`, `tests/agent_handoff/test_selected_routing.py`
- **acceptance:** mixed forbidden/overlong paragraph findings keep correct rule, line, observed value, and limit regardless of order.
- **sub-tasks:**
  - **T2.1 RED** — add the mixed multi-paragraph FIFO-mispair fixture.
  - **T2.2 Verify RED** — confirm semantic misattribution.
  - **T2.3 GREEN** — match enrichment by rule identity and compatible measurement.
  - **T2.4 Verify GREEN** — run focused and full Agent Handoff tests.
  - **T2.5 REFACTOR** — centralize rule identity if useful.
  - **T2.6 Verify Task** — targeted tests, Ruff, BasedPyright, `scripts/verify.sh`.

#### T3: Make legacy inventory lock-aware for #90

- **goal:** Suppress legacy signatures authenticated as current by the applied lock. · **phase:** P2 · **depends_on:** [T1] · **requirements:** [REQ-090] · **priority:** must
- **files:** `src/project_standards/agent_handoff/legacy.py`, routing code, legacy/routing tests
- **acceptance:** managed hook/registration evidence is clean while unowned duplicates remain visible.
- **sub-tasks:**
  - **T3.1 RED** — reproduce locked-current false positives.
  - **T3.2 Verify RED** — confirm exact current signatures are misclassified.
  - **T3.3 GREEN** — add bounded lock-provenance authentication.
  - **T3.4 Verify GREEN** — run legacy and adversarial duplicate tests.
  - **T3.5 REFACTOR** — separate signature detection from provenance.
  - **T3.6 Verify Task** — targeted tests, Ruff, BasedPyright, `scripts/verify.sh`.

#### T4: Route read-only commands through locked payloads for #91

- **goal:** Use the applied payload before catalog refresh. · **phase:** P2 · **depends_on:** [T3] · **requirements:** [REQ-091] · **priority:** must
- **files:** Agent Handoff CLI/provider dispatch and selected-routing tests
- **acceptance:** older V5 fixtures run `legacy-report` before reconciliation without mutation and disclose the locked basis.
- **sub-tasks:**
  - **T4.1 RED** — reproduce `selected command package is not reconciled`.
  - **T4.2 Verify RED** — confirm ordinary preview remains applicable.
  - **T4.3 GREEN** — resolve read authority from authenticated lock facts.
  - **T4.4 Verify GREEN** — run routing, tampered-lock, and missing-payload tests.
  - **T4.5 REFACTOR** — expose one read-authority resolver.
  - **T4.6 Verify Task** — targeted tests, Ruff, BasedPyright, `scripts/verify.sh`.

#### T5: Restore the pre-apply report checkpoint for #101

- **goal:** Make size/shape reports usable before apply or deliberately redefine the workflow. · **phase:** P2 · **depends_on:** [T4] · **requirements:** [REQ-101] · **priority:** must
- **files:** Agent Handoff routing, `UPGRADING.md`, selected-routing tests
- **acceptance:** the documented checkpoint provides equivalent pre-write safety and an accurate diagnostic.
- **sub-tasks:**
  - **T5.1 RED** — reproduce enabled-but-unlocked refusal.
  - **T5.2 Verify RED** — confirm the state is normal and unmutated.
  - **T5.3 GREEN** — implement the approved desired-state report or workflow correction.
  - **T5.4 Verify GREEN** — run pre/post-apply reports and doc parity checks.
  - **T5.5 REFACTOR** — reuse T4 authority resolution where valid.
  - **T5.6 Verify Task** — targeted tests, documentation gates, `scripts/verify.sh`.

#### T6: Detect duplicate startup injection for #102

- **goal:** Block or report legacy SessionStart handlers that remain live beside managed handlers. · **phase:** P2 · **depends_on:** [T3] · **requirements:** [REQ-102] · **priority:** must
- **files:** Agent Handoff provider/planning/validation and Claude/Codex fixtures
- **acceptance:** matcher-less and differently matched legacy groups cannot yield a green double injection.
- **sub-tasks:**
  - **T6.1 RED** — reproduce both harness double-injection shapes.
  - **T6.2 Verify RED** — confirm reconcile/validate/drift are falsely green.
  - **T6.3 GREEN** — add shared semantic overlap detection.
  - **T6.4 Verify GREEN** — prove unrelated handlers remain consumer-owned.
  - **T6.5 REFACTOR** — centralize overlap semantics.
  - **T6.6 Verify Task** — targeted tests, Ruff, BasedPyright, `scripts/verify.sh`.

#### T7: Align secret-reference policy for #107

- **goal:** Apply the owner-selected uppercase-reference policy in engine and provider. · **phase:** P2 · **depends_on:** [T1] · **requirements:** [REQ-107] · **priority:** must
- **files:** `src/project_standards/agent_handoff/policy.py`, successor provider, parity tests
- **acceptance:** env-reference and command-substitution cases produce identical safe findings; compatibility impact is documented.
- **sub-tasks:**
  - **T7.1 RED** — freeze the divergence matrix and owner decision.
  - **T7.2 Verify RED** — confirm only the named cases diverge.
  - **T7.3 GREEN** — implement the selected policy in engine/successor.
  - **T7.4 Verify GREEN** — run parity, redaction, and predecessor tests.
  - **T7.5 REFACTOR** — share data only without blurring authority.
  - **T7.6 Verify Task** — targeted/package tests and `scripts/verify.sh`.

#### T8: Qualify the Agent Handoff authority train

- **goal:** Publish T2–T7 in one release and close their issues. · **phase:** P2 · **depends_on:** [T2, T3, T4, T5, T6, T7] · **requirements:** [REQ-900] · **priority:** must
- **files:** successor/catalog/projection/lock, regression ledger, release/handoff docs
- **acceptance:** predecessor bytes, candidate parity, full gate, hosted checks, assets, recovery decision, and six closures verify.
- **sub-tasks:**
  - **T8.1 RED** — run original reproductions against the prior release.
  - **T8.2 Verify RED** — map failures one-to-one to regressions.
  - **T8.3 GREEN** — activate successors and release metadata only.
  - **T8.4 Verify GREEN** — run package and installed-wheel checks.
  - **T8.5 REFACTOR** — generated normalization only.
  - **T8.6 Verify Task** — `scripts/verify.sh --full`, release/hosted/artifact proof, §8.1 recovery-gate check, authorized publication and closure.

### Phase P3: Control-Plane Train

#### T9: Correct absent-artifact planning for #76/#77

- **goal:** Create empty managed files and converge create-only→managed absent targets in one apply. · **phase:** P3 · **depends_on:** [T8] · **requirements:** [REQ-076, REQ-077] · **priority:** must
- **files:** `src/project_standards/control_plane/planner.py`, planner/executor tests
- **acceptance:** empty `py.typed`/`.gitkeep` and deleted-container policy transitions converge while verification stays fail-closed.
- **sub-tasks:**
  - **T9.1 RED** — add empty-CREATE and policy-transition regressions.
  - **T9.2 Verify RED** — confirm no-op/two-cycle behavior.
  - **T9.3 GREEN** — distinguish `None` from empty bytes and align policy authority.
  - **T9.4 Verify GREEN** — run planner/executor/lock matrices.
  - **T9.5 REFACTOR** — name lifecycle policy authority.
  - **T9.6 Verify Task** — control-plane tests, Ruff, BasedPyright, `scripts/verify.sh`.

#### T10: Supply V4 transform evidence for #83

- **goal:** Produce a Python Tooling migration plan or actionable package-specific finding. · **phase:** P3 · **depends_on:** [T8] · **requirements:** [REQ-083] · **priority:** must
- **files:** `src/project_standards/control_plane/migration.py`, evidence models, V4 fixtures/tests
- **acceptance:** the issue fixture previews in human/JSON modes; missing evidence names package, transform, input, and safe action.
- **sub-tasks:**
  - **T10.1 RED** — add the exact V4 Python Tooling fixture.
  - **T10.2 Verify RED** — confirm the opaque evidence failure.
  - **T10.3 GREEN** — derive exact evidence or emit bounded diagnostics.
  - **T10.4 Verify GREEN** — run migration/transform/corruption parity tests.
  - **T10.5 REFACTOR** — centralize evidence without restoring legacy authority.
  - **T10.6 Verify Task** — migration tests, Ruff, BasedPyright, `scripts/verify.sh`.

#### T11: Make successor drift actionable for #87

- **goal:** Explain drift and accept target rendering that exactly subsumes declared intent. · **phase:** P3 · **depends_on:** [T9] · **requirements:** [REQ-087] · **priority:** must
- **files:** control-plane diagnostics/planner/schema and lifecycle tests
- **acceptance:** safe expected/observed/option evidence is present; equivalent successor intent needs no destructive temporary restore.
- **sub-tasks:**
  - **T11.1 RED** — reproduce opaque diagnostics and two-phase workaround.
  - **T11.2 Verify RED** — confirm old-lock drift blocks semantic equivalence.
  - **T11.3 GREEN** — enrich findings and add fail-closed equivalence planning.
  - **T11.4 Verify GREEN** — run drift/redaction/malicious-target tests.
  - **T11.5 REFACTOR** — separate evidence from authorization.
  - **T11.6 Verify Task** — tests, schema checks, Ruff, BasedPyright, `scripts/verify.sh`.

#### T12: Validate Frontmatter IDs before retirement for #98

- **goal:** Make migration predict complete selected-package validation. · **phase:** P3 · **depends_on:** [T10] · **requirements:** [REQ-098] · **priority:** must
- **files:** migration verification dispatch, Frontmatter provider contract, migration fixtures
- **acceptance:** invalid IDs block before lock publication with reviewed repair guidance and no implicit document changes.
- **sub-tasks:**
  - **T12.1 RED** — add the legacy-ID false-success fixture.
  - **T12.2 Verify RED** — confirm `validate-id` fails after successful migration.
  - **T12.3 GREEN** — invoke complete selected-provider validation before retirement.
  - **T12.4 Verify GREEN** — run valid/invalid/referenced/no-write matrices.
  - **T12.5 REFACTOR** — expose one selected-package verification seam.
  - **T12.6 Verify Task** — migration/frontmatter tests and `scripts/verify.sh`.

#### T13: Coalesce TOML creates for #105

- **goal:** Render shared missing/empty inline parents atomically without duplicate keys. · **phase:** P3 · **depends_on:** [T9] · **requirements:** [REQ-105] · **priority:** must
- **files:** `src/project_standards/control_plane/adapters/toml.py`, adapter/planner tests
- **acceptance:** flat/nested, empty/nonempty, and ordering permutations yield valid TOML and preserve consumer values.
- **sub-tasks:**
  - **T13.1 RED** — add shared-parent CREATE permutations.
  - **T13.2 Verify RED** — confirm invalid or duplicate output.
  - **T13.3 GREEN** — coalesce inserts per inline-container locus.
  - **T13.4 Verify GREEN** — run adapter/planner batch matrices.
  - **T13.5 REFACTOR** — isolate coalescing from single-edit rendering.
  - **T13.6 Verify Task** — TOML/control-plane tests and `scripts/verify.sh`.

#### T14: Normalize JSONC deletion residue for #106

- **goal:** Remove newly empty lines/containers while preserving comments, CRLF, and surviving bytes. · **phase:** P3 · **depends_on:** [T9] · **requirements:** [REQ-106] · **priority:** must
- **files:** `src/project_standards/control_plane/adapters/jsonc.py`, adapter tests
- **acceptance:** sole-member, comma-leading, comma-own-line, LF/CRLF, and comment-adjacent layouts converge safely.
- **sub-tasks:**
  - **T14.1 RED** — add the complete residue layout matrix.
  - **T14.2 Verify RED** — confirm residue rather than semantic corruption.
  - **T14.3 GREEN** — recompute spans after separator deletion and collapse proven-safe spans.
  - **T14.4 Verify GREEN** — run removal/byte/parse tests.
  - **T14.5 REFACTOR** — centralize post-deletion whitespace analysis.
  - **T14.6 Verify Task** — JSONC/control-plane tests and `scripts/verify.sh`.

#### T15: Qualify the control-plane train

- **goal:** Publish T9–T14 together and close seven issues after #84 has a verified disposition. · **phase:** P3 · **depends_on:** [T9, T10, T11, T12, T13, T14, T23] · **requirements:** [REQ-900] · **priority:** must
- **files:** regression ledger, release/version/handoff docs
- **acceptance:** original reproductions, the #84 disposition, compatibility matrix, full gate, hosted checks, assets, recovery decision, and closures verify.
- **sub-tasks:**
  - **T15.1 RED** — run original reproductions against the prior release.
  - **T15.2 Verify RED** — map failures to train regressions.
  - **T15.3 GREEN** — prepare release metadata only.
  - **T15.4 Verify GREEN** — run fresh candidate migration/adapter/planner probes.
  - **T15.5 REFACTOR** — generated normalization only.
  - **T15.6 Verify Task** — `scripts/verify.sh --full`, release/hosted/artifact proof, §8.1 recovery-gate check, authorized publication and closure.

### Phase P4: Tooling Scope and Configuration Train

#### T16: Bound Markdown formatting scope for #88

- **goal:** Make local/workflow Prettier commands select only configured Markdown/structured text. · **phase:** P4 · **depends_on:** [T15] · **requirements:** [REQ-088] · **priority:** must
- **files:** Markdown Tooling successor provider/docs and real-tool tests
- **acceptance:** languages and ignored scratch outside configured globs are never traversed.
- **sub-tasks:**
  - **T16.1 RED** — add mixed tracked/ignored corpus reproduction.
  - **T16.2 Verify RED** — confirm dot traversal exceeds scope.
  - **T16.3 GREEN** — render deterministic bounded invocation.
  - **T16.4 Verify GREEN** — run real Prettier set-parity tests.
  - **T16.5 REFACTOR** — share selection without new glob authority.
  - **T16.6 Verify Task** — package/real-tool tests and `scripts/verify.sh`.

#### T17: Fix Python import precedence for #89

- **goal:** Resolve managed `src` code as first-party typed source. · **phase:** P4 · **depends_on:** [T15] · **requirements:** [REQ-089] · **priority:** must
- **files:** Python Tooling successor provider/schema/docs and BasedPyright tests
- **acceptance:** strict tests do not resolve an untyped editable install first; other layouts remain compatible.
- **sub-tasks:**
  - **T17.1 RED** — add editable src-layout missing-stub fixture.
  - **T17.2 Verify RED** — capture wrong resolution ordering.
  - **T17.3 GREEN** — implement approved path/marker contract.
  - **T17.4 Verify GREEN** — run src/flat/marker/additional-root matrix.
  - **T17.5 REFACTOR** — derive import roots once.
  - **T17.6 Verify Task** — package/real BasedPyright tests and `scripts/verify.sh`.

#### T18: Bound Ruff scope for #95

- **goal:** Select only declared first-party source/test roots. · **phase:** P4 · **depends_on:** [T15] · **requirements:** [REQ-095] · **priority:** must
- **files:** Python Tooling successor provider/docs/scripts/workflows and Ruff tests
- **acceptance:** nested projects and undeclared scripts remain untouched; every declared root is covered.
- **sub-tasks:**
  - **T18.1 RED** — add declared/nested/unrelated corpus.
  - **T18.2 Verify RED** — confirm dot reaches out-of-bound files.
  - **T18.3 GREEN** — derive deterministic Ruff arguments.
  - **T18.4 Verify GREEN** — run real Ruff selection tests.
  - **T18.5 REFACTOR** — share normalized roots where contracts coincide.
  - **T18.6 Verify Task** — package/real-tool tests and `scripts/verify.sh`.

#### T19: Preserve Ruff plugin configuration for #99

- **goal:** Keep undeclared plugin sub-tables consumer-owned or expose a bounded typed option. · **phase:** P4 · **depends_on:** [T18] · **requirements:** [REQ-099] · **priority:** must
- **files:** Python Tooling successor provider/schema/docs and ownership tests
- **acceptance:** Typer's targeted B008 configuration reconciles without global suppression, source churn, or split-file workaround.
- **sub-tasks:**
  - **T19.1 RED** — reproduce table conflict and lint consequence.
  - **T19.2 Verify RED** — prove current options cannot express intent.
  - **T19.3 GREEN** — implement approved ownership/option contract.
  - **T19.4 Verify GREEN** — run plugin/governed-key/round-trip tests.
  - **T19.5 REFACTOR** — declare ownership once.
  - **T19.6 Verify Task** — package/control-plane tests and `scripts/verify.sh`.

#### T20: Add a no-implicit-root layout for #86

- **goal:** Support explicit roots without forcing `src` or `.` and reject empty unsuitable configurations. · **phase:** P4 · **depends_on:** [T17, T18, T19] · **requirements:** [REQ-086] · **priority:** must
- **files:** Python Tooling successor schema/provider/docs/migration and monorepo tests
- **acceptance:** explicit-root consumers get a bounded gate; src/flat predecessors remain unchanged.
- **sub-tasks:**
  - **T20.1 RED** — add mixed-monorepo and unsuitable-default fixtures.
  - **T20.2 Verify RED** — prove forced missing/widened roots.
  - **T20.3 GREEN** — add approved no-implicit-root mode.
  - **T20.4 Verify GREEN** — run fresh/migration/empty/predecessor matrices.
  - **T20.5 REFACTOR** — use one normalized root model.
  - **T20.6 Verify Task** — package/real-tool tests and `scripts/verify.sh`.

#### T21: Qualify tooling successors

- **goal:** Publish T16–T20, T31, and T33 in one repository release and close six issues. · **phase:** P4 · **depends_on:** [T16, T17, T18, T19, T20, T31, T33] · **requirements:** [REQ-900] · **priority:** must
- **files:** family indexes, catalog/projection/lock, ledger, release/handoff docs
- **acceptance:** predecessors, corrected Python Tooling authority and fresh-adoption preflight, real-tool scopes, full gate, hosted checks, assets, recovery decision, and six closures verify.
- **sub-tasks:**
  - **T21.1 RED** — run six reproductions against prior defaults.
  - **T21.2 Verify RED** — map failures to successor tests.
  - **T21.3 GREEN** — activate successors/release metadata.
  - **T21.4 Verify GREEN** — run package/candidate consumer probes.
  - **T21.5 REFACTOR** — generated normalization only.
  - **T21.6 Verify Task** — `scripts/verify.sh --full`, release/hosted/artifact proof, §8.1 recovery-gate check, authorized publication and closure.

### Phase P5: Documentation and Pre-Release Investigation

#### T22: Correct MCP release docs for #108

- **goal:** Lead current/future MCP docs with exact-release installation without rewriting v5.12.0. · **phase:** P5 · **depends_on:** [T1] · **requirements:** [REQ-108] · **priority:** must
- **files:** `docs/mcp-server.md`, related current docs, release-doc contract tests
- **acceptance:** candidate instructions are development-only and future releases cannot ship candidate-as-current prose.
- **sub-tasks:**
  - **T22.1 RED** — add contradictory release-state scan.
  - **T22.2 Verify RED** — confirm current source exposure.
  - **T22.3 GREEN** — correct mutable docs and add regression guard.
  - **T22.4 Verify GREEN** — run contract and Markdown gates.
  - **T22.5 REFACTOR** — centralize wording only if already supported.
  - **T22.6 Verify Task** — targeted contract/documentation validation.

#### T23: Dispose of the PyYAML transient for #84

- **goal:** Reproduce a repository-owned defect and fix it, or record a bounded no-reproduction disposition before the control-plane release. · **phase:** P5 · **depends_on:** [T8] · **requirements:** [REQ-084] · **priority:** should
- **files:** isolated reproduction harness; source/tests only after proven cause
- **acceptance:** fresh installs, concurrent install/launch, and repeated paired previews establish cause or a documented threshold; T15 remains blocked until the evidence-backed disposition is accepted.
- **sub-tasks:**
  - **T23.1 RED** — run the bounded isolated matrix.
  - **T23.2 Verify RED** — prove missing/partial installed bytes if reproduced.
  - **T23.3 GREEN** — implement only a proven fix or prepare disposition.
  - **T23.4 Verify GREEN** — rerun matrix and integrity checks.
  - **T23.5 REFACTOR** — none unless a fix duplicates verification.
  - **T23.6 Verify Task** — affected gates and evidence-backed issue update.

### Phase P6: Project Spec Conformance Feature

#### T24: Specify conformance linting for #62

- **goal:** Approve exact surfaces, phrasing policy, compatibility mode, and rollout. · **phase:** P6 · **depends_on:** [T21] · **requirements:** [REQ-062] · **priority:** should
- **files:** new `docs/specs/` specification, child `docs/plans/` plan, issue #62
- **acceptance:** byte-exact/structural/advisory checks and existing-consumer impact are explicit and reviewed.
- **sub-tasks:**
  - **T24.1 RED** — inventory canonical/divergent documents and unresolved decisions.
  - **T24.2 Verify RED** — confirm current validators accept divergence.
  - **T24.3 GREEN** — author and obtain approval for spec/child plan.
  - **T24.4 Verify GREEN** — validate requirements and traceability.
  - **T24.5 REFACTOR** — remove unrelated feature scope.
  - **T24.6 Verify Task** — doc gates, converged review, owner approval.

#### T25: Implement conformance linting for #62

- **goal:** Execute the approved child plan and publish its behavior. · **phase:** P6 · **depends_on:** [T24] · **requirements:** [REQ-062] · **priority:** should
- **files:** frozen by the approved #62 specification and child plan
- **acceptance:** canonical/divergent/tailored/predecessor documents produce approved results and #62 closes after release.
- **sub-tasks:**
  - **T25.1 RED** — execute child-plan failing conformance tests.
  - **T25.2 Verify RED** — require spec-defined failure reasons.
  - **T25.3 GREEN** — execute bounded behavior tasks.
  - **T25.4 Verify GREEN** — run child package/compatibility suites.
  - **T25.5 REFACTOR** — follow child-plan cleanup boundaries.
  - **T25.6 Verify Task** — child completion, fresh candidate, `scripts/verify.sh --full`, authorized release/closure.

### Phase P7: Project Spec Conversion Feature

#### T26: Specify house-format conversion for #55

- **goal:** Approve preservation, ambiguity, preview/apply, rollback, and semantic-review contracts. · **phase:** P7 · **depends_on:** [T25] · **requirements:** [REQ-055] · **priority:** should
- **files:** new `docs/specs/` specification, child `docs/plans/` plan, issue #55
- **acceptance:** unrecognized prose cannot be discarded; ambiguous choices remain explicit; rollback is defined; safe adoption for future canonical specs with an excluded/no-match legacy corpus remains supported and never forces conversion.
- **sub-tasks:**
  - **T26.1 RED** — characterize corpora and ambiguous mappings.
  - **T26.2 Verify RED** — confirm no existing command satisfies the contract.
  - **T26.3 GREEN** — author and obtain approval for spec/child plan.
  - **T26.4 Verify GREEN** — validate coverage, mutation bounds, fixtures, rollback.
  - **T26.5 REFACTOR** — remove unsafe semantic inference.
  - **T26.6 Verify Task** — doc gates, converged review, owner approval.

#### T27: Implement preservation-first conversion for #55

- **goal:** Execute the approved child plan and publish the safe conversion surface. · **phase:** P7 · **depends_on:** [T26] · **requirements:** [REQ-055] · **priority:** should
- **files:** frozen by the approved #55 specification and child plan
- **acceptance:** conversion is explicit and opt-in; recognized structure maps deterministically; unmapped content stays intact/review-visible; apply is guarded; new-spec-only/no-match consumers retain their existing successful behavior.
- **sub-tasks:**
  - **T27.1 RED** — execute preservation/ambiguity regressions.
  - **T27.2 Verify RED** — confirm missing behavior, never fixture loss.
  - **T27.3 GREEN** — implement minimal preview/guarded apply.
  - **T27.4 Verify GREEN** — run property/integration/round-trip/rollback suites.
  - **T27.5 REFACTOR** — do not add heuristic rewriting.
  - **T27.6 Verify Task** — child completion, semantic audit, fresh candidate/full gate.

#### T28: Qualify the feature release

- **goal:** Publish #55 without regressing #62 or correction trains. · **phase:** P7 · **depends_on:** [T27] · **requirements:** [REQ-900] · **priority:** must
- **files:** release metadata, ledger, docs, handoff surfaces
- **acceptance:** source/candidate/installed parity, migration safety, hosted checks, assets, recovery decision, and #55 closure verify.
- **sub-tasks:**
  - **T28.1 RED** — run original manual-only reproduction.
  - **T28.2 Verify RED** — confirm only missing import surface fails.
  - **T28.3 GREEN** — prepare activation/release docs only.
  - **T28.4 Verify GREEN** — run child and cross-train regressions.
  - **T28.5 REFACTOR** — generated normalization only.
  - **T28.6 Verify Task** — `scripts/verify.sh --full`, release/hosted/artifact proof, §8.1 recovery-gate check, authorized publication/closure.

### Phase P8: Tracker and Program Closeout

#### T29: Reconcile the tracker and close the program

- **goal:** Account for every frozen issue, harvest durable outcomes, and retire active state. · **phase:** P8 · **depends_on:** [T22, T23, T24, T25, T26, T27, T28, T32] · **requirements:** [REQ-901] · **priority:** must
- **files:** this plan at closeout, `docs/STATUS.md`, `docs/TODO.md`, handoff records, GitHub issues
- **acceptance:** all 24 issues are closed or explicitly accepted; docs/releases/ledger agree; scratch is harvested and removed.
- **sub-tasks:**
  - **T29.1 RED** — query frozen issue set and list open/evidence-incomplete items.
  - **T29.2 Verify RED** — reconcile tracker, releases, ledger, and handoff.
  - **T29.3 GREEN** — apply authorized closures/comments and route durable facts.
  - **T29.4 Verify GREEN** — rerun issue and handoff/document validation.
  - **T29.5 REFACTOR** — remove completed active-queue detail, preserve lessons.
  - **T29.6 Verify Task** — handoff validate/drift-check, doc gates, plan validation; harvest notes, mark complete, delete scratch.

### Phase P9: Owner-Approved Cross-Cutting and Discovered Work

#### T30: Align catalog release-level classification

- **goal:** Make catalog release levels follow the owner-approved package-composition policy while preserving all immutable-package and forbidden-transition checks. · **phase:** P9 · **depends_on:** [] · **requirements:** [REQ-902] · **priority:** must
- **files:** `docs/adr/adr-0024-catalog-scoped-package-version-channels.md`, `meta/versioning.md`, `src/project_standards/package_contract/release.py`, `tests/package_contract/test_release.py`, package CLI tests and generated schemas as needed
- **acceptance:** a matching tool/catalog major increment is accepted as the owner's MAJOR designation unless another contract is forbidden; otherwise any standard-package version advance requires exactly MINOR and no standard-package version advance requires exactly PATCH. Per package ID, a newly introduced package or a newly advertised version above the prior advertised maximum is an advance; internal and reference-only packages count, while older retained history and unadvertised payloads do not. Advertised-version removal, package downgrade, immutable-byte violations, and same-catalog breaking-default promotion remain forbidden, and ADR 0024 plus `meta/versioning.md` use the same rule.
- **sub-tasks:**
  - **T30.0 CHARACTERIZE** — freeze current classification and boundary behavior for patch-only engine/docs changes, compatible package-version advances, owner-selected major versions, and forbidden mutations.
  - **T30.1 RED** — add the approved exact-level and version-advance matrix, including rejection of MINOR without an advance, PATCH with one, advertised-version removal, downgrade, and same-catalog breaking-default promotion.
  - **T30.2 Verify RED** — confirm failures expose the current highest-severity/minimum-floor contract rather than fixture or parsing errors.
  - **T30.3 GREEN** — separate forbidden-transition detection from the owner/package-composition release-level rule and align `meta/versioning.md`.
  - **T30.4 Verify GREEN** — run focused release and package CLI matrices, including unchanged predecessor and major-designation cases.
  - **T30.5 REFACTOR** — name the package-version-advance predicate once without broad release-module redesign.
  - **T30.6 Verify Task** — run focused tests, Ruff, BasedPyright, package contracts, and `scripts/verify.sh`.

#### T31: Correct the Python Tooling successor's authority statement

- **goal:** Make the already-planned compatible Python Tooling successor state the current V5 package/control-plane authority without altering immutable 1.10. · **phase:** P9 · **depends_on:** [T20, T30] · **requirements:** [REQ-903] · **priority:** must
- **files:** planned Python Tooling successor README and focused package-contract test; activation remains in T21
- **acceptance:** Python Tooling 1.10 remains byte-identical; its planned successor contains no claim that the V1 root manifest is current authority, consistently identifies the selected V5 package/control plane as authoritative, and is activated and qualified by T21 rather than a separate release train.
- **sub-tasks:**
  - **T31.1 RED** — add a successor contract test that rejects the stale V1-authority statement and requires the current V5 authority statement.
  - **T31.2 Verify RED** — confirm the planned successor still carries the copied 1.10 contradiction.
  - **T31.3 GREEN** — make the smallest content correction across the successor surfaces that state package authority.
  - **T31.4 Verify GREEN** — run the focused successor contract and predecessor-byte checks.
  - **T31.5 REFACTOR** — remove duplicate wording only within the successor when byte-lock contracts permit it.
  - **T31.6 Verify Task** — run Python Tooling package tests, package/graph/schema/projection checks, and `scripts/verify.sh`.

#### T32: Finish Agent Handoff consumer retirement

- **goal:** Manually converge the two remaining protected consumers and close the retirement records without creating generalized migration machinery. · **phase:** P9 · **depends_on:** [T30] · **requirements:** [REQ-904] · **priority:** must
- **files:** authoritative branches for `website-aboutme` and `website-l3digital.net`; retirement inventory, Agent Handoff plan/spec closeout, `docs/TODO.md`, and handoff records in this repository
- **acceptance:** each remaining consumer has only the standards-managed Agent Handoff document/hook pair on its authoritative branch, passes `project-standards agent-handoff validate --repo .` and `drift-check --repo .` using its selected control plane, preserves unrelated work, and has remote parity after separately authorized publication; retirement records name the verified final state.
- **sub-tasks:**
  - **T32.1 RED** — recheck the retirement inventory and capture the exact remaining per-consumer merge or managed-file delta.
  - **T32.2 Verify RED** — prove `docmend` and `hw-radar` are already merged, limit the remaining scope to the two website consumers, and distinguish Agent Handoff work from unrelated catalog drift.
  - **T32.3 GREEN** — manually update each consumer through its established protected-branch workflow after reviewing the exact diff and obtaining publication authorization.
  - **T32.4 Verify GREEN** — run Agent Handoff validate and drift-check in each consumer and prove its authoritative branch contains the managed system only.
  - **T32.5 REFACTOR** — none; do not create reusable migration or reconciliation machinery for this closeout.
  - **T32.6 Verify Task** — prove both consumer remotes, update retirement and handoff documents, run repository document/handoff gates, and close the TODO.

#### T33: Guard Python Tooling fresh adoption for #109

- **goal:** Reject fresh adoption before any write when Python Tooling would create `pyproject.toml` without consumer-owned PEP 621 project metadata. · **phase:** P9 · **depends_on:** [T20, T31] · **requirements:** [REQ-109] · **priority:** must
- **files:** planned Python Tooling successor provider/findings/docs, package-contract and real-uv consumer fixtures; activation remains in T21
- **acceptance:** an absent `pyproject.toml` or missing `[project]` table produces an actionable no-write finding that names the required consumer decision and installable/non-installable routes; existing valid `[project]` metadata is preserved; the documented apply → `uv lock` flow succeeds with the lock-resolved uv version; Python Tooling 1.10 remains byte-identical.
- **sub-tasks:**
  - **T33.1 RED** — add fresh installable and non-installable fixtures that currently reconcile a tool-only `pyproject.toml` and fail `uv lock`.
  - **T33.2 Verify RED** — confirm the failure is missing consumer-owned `[project]` metadata rather than dependency or backend resolution.
  - **T33.3 GREEN** — add the smallest fail-before-write provider/preflight finding and guided adoption documentation without generating project identity.
  - **T33.4 Verify GREEN** — prove invalid fresh adoption writes nothing and valid consumer-authored metadata reaches a successful real `uv lock`.
  - **T33.5 REFACTOR** — share metadata-presence checks only within the successor boundary; do not add project-identity inference.
  - **T33.6 Verify Task** — run Python Tooling package/real-uv tests, predecessor-byte checks, package contracts, and `scripts/verify.sh`.

## 8. Release Boundaries and Effort

| Release/train | Issues | Active effort |
| --- | --- | --: |
| A — ready fix | #80; #108 may ride | 0.5–1.5 days |
| B — Agent Handoff authority | #75, #90, #91, #101, #102, #107 | 10–20 days |
| C — control plane | #76, #77, #83, #87, #98, #105, #106 | 18–31 days |
| D — tooling successors | #86, #88, #89, #95, #99, #109 | 14–26 days |
| Pre-release investigation | #84 | 1–2 days before fix estimate |
| E — conformance feature | #62 | 5–10 days after approval |
| F — conversion feature | #55 | 10–20 days after approval |
| Owner TODOs | Release policy, Python Tooling authority, Agent Handoff retirement | 1–3 days plus protected-branch review latency |

### 8.1 Release Failure and Recovery

- A failed source, candidate, installed, full, hosted, classification, or artifact gate stops publication and issue closure. Correct the unpublished successor or release metadata, rebuild from clean state, and rerun the complete qualification task.
- A defect found after publication never authorizes rewriting or deleting immutable tags, assets, or payloads. Record the affected release, stop recommending it where mutable documentation permits, prepare a corrective successor, and rerun the same qualification and owner-authorization gates.
- If a train cannot be corrected without broadening its approved scope, leave its issues open and return to owner review rather than silently dropping a gate or splitting an unplanned emergency release.

## 9. Owner Gates

| Gate | Blocking task | Working assumption |
| --- | --- | --- |
| Catalog release classification | T30 | **Resolved:** owner designation is the only MAJOR route; a newly introduced package or newly advertised version above that package's prior maximum is exactly MINOR; no such advance is exactly PATCH. Internal/reference-only advances count; older retained history and unadvertised payloads do not. Advertised versions are permanent even across MAJOR releases. This replaces the prior highest-severity and previously-passing override rules and amends ADR 0024. |
| Python Tooling fresh adoption | T33 | **Resolved:** preserve consumer ownership of `[project]`; reject before writing and guide installable/non-installable setup instead of generating or inferring identity. |
| Bare uppercase references | T7 | Preserve explicit env-var references; reject command-substitution laundering. |
| Desired-state versus reordered reports | T5 | Prefer desired-state read-only reports if provenance stays fail-closed. |
| Ruff sub-table ownership | T19 | Prefer consumer ownership for undeclared plugin keys. |
| #62 compatibility mode | T24 | New strict successor rule with documented advisory path. |
| #55 safe mappings | T26 | Map exact recognized headings only; preserve all other content for review. |

## 10. Risks

| ID | Risk | Mitigation | Owner task |
| --- | --- | --- | --- |
| R-001 | One giant train becomes unreviewable. | Fixed release boundaries and one issue regression per task. | T8, T15, T21 |
| R-002 | Predecessor bytes drift. | Successor-only package edits and byte gates. | Qualification tasks |
| R-003 | #55/#62 block corrections. | Separate post-correction approval gates. | T24–T27 |
| R-004 | Adapter cleanup damages consumer bytes. | Layout/property matrices and byte controls. | T13, T14 |
| R-005 | Issues close before users can install fixes. | Require published evidence or accepted disposition. | Qualification tasks, T29 |
| R-006 | New issues prevent convergence. | Freeze inventory; append only approved discovered work. | T29 |
| R-007 | Release semantics accidentally weaken immutable-package or catalog-history enforcement. | Separate level selection from forbidden findings, retain the mutation matrix, forbid advertised-version removal and downgrade, and amend ADR 0024 in the same task. | T30 |
| R-008 | Small consumer retirement expands into generalized migration work. | Limit T32 to the two named consumers and manual verified updates. | T32 |
| R-009 | A compatibility-breaking correction receives MINOR because the owner has not designated MAJOR. | Present the change surface at every release gate and require an explicit owner MAJOR decision before publication; never infer MAJOR in tooling. | Qualification tasks |
| R-010 | A release fails after metadata preparation or publication. | Apply §8.1; preserve immutable artifacts and issue a fully requalified successor. | T1, T8, T15, T21, T28 |
| R-011 | Fresh Python Tooling adoption writes an unusable partial project. | Block before writes when `[project]` is absent and prove the guided valid path with real uv. | T33 |

## 11. Definition of Done

- Every requirement in §4 is completed or has an owner-accepted no-change disposition.
- Every fixed defect has regression-ledger and source/candidate proof.
- Package changes ship only as immutable successors; predecessors remain byte-identical/selectable.
- Every train passes package contracts, graph/schema/projection checks, fresh installed probes, `scripts/verify.sh --full`, classification, hosted checks, and artifact verification.
- GitHub has no frozen issue open without an accepted monitoring disposition.
- Status, TODO, handoff, roadmap, changelog, release notes, and GitHub agree.
- Catalog release-level documentation and `check-release` agree with the owner/package-composition policy.
- Python Tooling's selected successor contains the corrected V5-authority statement and no-write fresh-adoption guard, and the two remaining Agent Handoff consumers are verified retired.
- Closeout notes are harvested, this plan is marked complete, and its `.project-pipeline/` directory is removed.

## 12. Close-out

- **Completed:** pending
- **Final release/commit:** pending
- **Decisions harvested:** pending
- **Accepted residuals:** pending
- **Deferred:** issues opened after 2026-08-01T09:21:01Z unless explicitly appended; `control_plane/provider_inputs.py` retirement

## Appendix A. Test Traceability

| Test ID | Requirement(s) | Task | Test surface | Type |
| --- | --- | --- | --- | --- |
| TC-T1-001 | REQ-080, REQ-900 | T1 | Agent Handoff 1.8 harness probes and release qualification | release regression |
| TC-T2-001 | REQ-075 | T2 | enrichment pairing | regression |
| TC-T3-001 | REQ-090 | T3 | lock-aware legacy inventory | regression |
| TC-T4-001 | REQ-091 | T4 | old-control-plane routing | integration |
| TC-T5-001 | REQ-101 | T5 | pre-apply reports | integration |
| TC-T6-001 | REQ-102 | T6 | duplicate injection | regression |
| TC-T7-001 | REQ-107 | T7 | secret-reference parity | contract |
| TC-T8-001 | REQ-900 | T8 | Agent Handoff train qualification and recovery gate | release contract |
| TC-T9-001 | REQ-076, REQ-077 | T9 | absent-artifact planner matrix | regression |
| TC-T10-001 | REQ-083 | T10 | V4 migration | integration |
| TC-T11-001 | REQ-087 | T11 | successor drift | regression |
| TC-T12-001 | REQ-098 | T12 | pre-retirement validation | integration |
| TC-T13-001 | REQ-105 | T13 | TOML CREATE permutations | property/regression |
| TC-T14-001 | REQ-106 | T14 | JSONC layouts | property/regression |
| TC-T15-001 | REQ-900 | T15 | control-plane qualification, #84 disposition, and recovery gate | release contract |
| TC-T16-001 | REQ-088 | T16 | Prettier corpus parity | contract |
| TC-T17-001 | REQ-089 | T17 | BasedPyright resolution | integration |
| TC-T18-001 | REQ-095 | T18 | Ruff corpus parity | contract |
| TC-T19-001 | REQ-099 | T19 | Ruff plugin ownership | contract |
| TC-T20-001 | REQ-086 | T20 | mixed-monorepo reconstruction | integration |
| TC-T21-001 | REQ-900 | T21 | tooling-successor qualification and recovery gate | release contract |
| TC-T22-001 | REQ-108 | T22 | release-state docs | contract |
| TC-T23-001 | REQ-084 | T23 | isolated install matrix | investigation |
| TC-T24-001 | REQ-062 | T24 | approved conformance specification and child-plan validation | design gate |
| TC-T25-001 | REQ-062 | T25 | approved conformance corpus | feature contract |
| TC-T26-001 | REQ-055 | T26 | approved conversion specification and child-plan validation | design gate |
| TC-T27-001 | REQ-055 | T27 | approved conversion corpus | feature contract |
| TC-T28-001 | REQ-900 | T28 | feature-release qualification and recovery gate | release contract |
| TC-T29-001 | REQ-901 | T29 | frozen-inventory reconciliation and closeout | operational |
| TC-T30-001 | REQ-902 | T30 | catalog release-level matrix | contract/regression |
| TC-T31-001 | REQ-903 | T31 | Python Tooling successor authority prose and predecessor bytes | package contract |
| TC-T32-001 | REQ-904 | T32 | two consumer validate/drift and authoritative-branch proof | operational |
| TC-T33-001 | REQ-109 | T33 | no-write preflight and valid real-uv lock path | contract/integration |

## Appendix B. Discovered Work Policy

An issue opened after 2026-08-01T09:21:01Z is not automatically part of this program. Record it in GitHub, decide whether it blocks the active train, and append the next permanent task ID only with owner approval. Otherwise route it to a later release or separate specification so this program can converge.
