---
plan_format: 3
title: 'Package Version Reference Sweep Implementation Plan'
slug: 'package-version-reference-sweep'
status: active
revision: 1
revises_revision: 0
revision_reason: 'initial plan correcting issue 164 from release-literal rewriting to catalog-derived package-reference review'
pause_reason: ''
source: 'issue L3DigitalNet/project-standards#164 and owner correction of 2026-08-10'
spec_ref: ''
created: 2026-08-10
updated: 2026-08-10
owners:
  - 'Project Standards maintainers'
---

# Package Version Reference Sweep Implementation Plan

> **Definition, not state.** This plan stops at one verified local checkpoint. Plan authoring did not generate execution state; during execution, the orchestrator alone generates and mutates the ephemeral state under `.project-pipeline/2026-08-10-package-version-reference-sweep/execution/`.

## 1. Objective

Give the release owner an early, deterministic review report for stale package-version references in each selected package family's mutable root `README.md`, `adopt.md`, and `agent-summary.md`. The report derives the expected version independently for every family from the candidate catalog source, names the expected selection beside each mismatching path and line, and never rewrites documentation or turns a reference mismatch into an automatic release-prep mutation.

This corrects issue #164's real defect without implementing its invalid premise. The existing outgoing Project Standards release-literal sweep remains separate and unchanged; in particular, `standards/*/agent-summary.md` does not join that sweep because those documents carry package versions rather than the tool release version. `packages check-release` remains the authoritative fail-closed release-consistency gate; the new sweep is its earlier, human-readable review aid.

## 2. Authority and Source Map

| Source | Source Role | Authority / Use | Version / Date | Affected Plan Surface |
| --- | --- | --- | --- | --- |
| `request` | normative | Correct and fulfill #164 as a catalog-derived, report-only package-version review across the three named mutable family-root documents; preserve the outgoing release-literal sweep; include RED, unit/CLI/integration proof, predecessor/no-op controls, rexec v0.2 discipline, and a proportional gate. | 2026-08-10 | §§1, 3, 5–13; T1 |
| `issue:L3DigitalNet/project-standards#164#issuecomment-5235511206` | normative | Owner correction: release prep reports rather than rewrites; the release-version glob would find no agent-summary package pins; the real feature is a per-family package-version sweep derived from the catalog. | 2026-08-10 | §§1, 3–7, 9–12; T1 |
| `repo:meta/versioning.md#release-requirements` | normative | Release ordering, candidate catalog activation/reconciliation, judgment-owned document review, exact-candidate proof, and the rule that `release_prep.py` remains mechanical. | `e24f50ef` | §§3–7, 9–13; T1 |
| `repo:catalogs/5.toml` | current-state evidence | Author-owned candidate catalog shape and current examples of `default`, `retained`, `reference-only`, and `internal` roles. | `e24f50ef` | §§4–6; T1 |
| `repo:src/project_standards/package_contract/catalog.py::CatalogRole` | current-state evidence | Closed role vocabulary and the existing consumer invariant of exactly one default package version. | `e24f50ef` | §§4–6; T1 |
| `repo:src/project_standards/package_contract/release_consistency.py::_family_facts` | current-state evidence | Existing candidate-catalog comparison semantics: consumer current is `default`; internal current is the numeric maximum; candidate and retained entries are not selected. | `e24f50ef` | §§4–7; T1 |
| `repo:src/project_standards/package_contract/release_consistency.py::_references` | current-state evidence | Existing package-reference grammar for exact selectors, versioned paths, enable arguments, and package/family prose. | `e24f50ef` | §§4–7; T1 |
| `repo:src/project_standards/package_contract/release_consistency.py::validate_release_consistency` | current-state evidence | `packages check-release` already treats mutable family-root Markdown as release-current and remains the authoritative release gate. | `e24f50ef` | §§1, 3–7, 9–13; T1 |
| `repo:scripts/release_prep.py::sweep_version_references` | current-state evidence | Existing outgoing tool-release literal report, target collection, report-only output, and `StepResult` summary contract. | `e24f50ef` | §§4–7, 9–12; T1 |
| `repo:scripts/release_prep.py::main` | current-state evidence | Release-prep sequencing validates changelog/baseline before the first write, then bumps the tool version, reports references, updates the changelog, verifies, and prints the handoff. | `e24f50ef` | §§4–7, 9–12; T1 |
| `repo:tests/test_release_prep.py` | current-state evidence | Two existing regression tests cover the printed candidate handoff and non-`main` refusal, but no reference-sweep behavior. | `e24f50ef` | §§4, 7, 9–12; T1 |
| `repo:standards/adr/README.md` | current-state evidence | Representative mutable consumer-family prose containing exact selectors, shallow `versions/` links, enable arguments, current package prose, and a predecessor reference. | `e24f50ef` | §§4–7; T1 |
| `repo:standards/python-coding/README.md` | current-state evidence | Representative reference-only family with no adoption guide and a historical predecessor link. | `e24f50ef` | §§3–7; T1 |
| `repo:standards/standard-bundle-authoring/README.md` | current-state evidence | Representative internal family whose current authority is the numeric maximum and which has no adoption guide. | `e24f50ef` | §§3–7; T1 |
| `repo:scripts/README.md` | informative | Current operator-facing description of the single outgoing-release report. | `e24f50ef` | §§4–6, 9–12; T1 |

Conflict precedence: the request and issue owner's correction replace the issue body's rewrite/glob outcome and acceptance criteria. The release contract governs release ordering and judgment boundaries. Current code supplies comparison and output patterns, but does not authorize automatic rewriting or a second release-consistency gate.

## 3. Scope, Boundaries, and Constraints

### 3.1 In Scope

- A second `release_prep.py` report that reads `catalogs/{target-major}.toml`, resolves one selected version per advertised family, and reviews existing `standards/{family}/README.md`, `adopt.md`, and `agent-summary.md` files against that version.
- Stable matching and comparison rules aligned with the repository's current release-consistency grammar: `{family}@{major}.{minor}`, family-local or full `versions/{major}.{minor}/` paths, `standards enable {family} --version[= ]{major}.{minor}`, and package/family current-version prose.
- Deterministic path/line reporting that names family, observed version, expected selected version, and the reason the line needs review; current references and intentionally historical predecessor prose are no-op controls.
- Pre-mutation validation of the candidate catalog input, release-prep summary integration, focused unit and `main()`/CLI orchestration tests, and the two operator documents that own the release behavior.

### 3.2 Out of Scope and Deferred

- Do not add `standards/*/agent-summary.md` to `sweep_version_references` or otherwise change that function's outgoing Project Standards release-literal target set.
- Do not rewrite any family-root document, package selector, link, command, catalog, payload, projection, lock, release version, or changelog entry as part of the package-reference report.
- Do not change `release_consistency.py`, `packages check-release`, its diagnostics, the package-contract schema, catalog roles, family manifests, payload bytes, or generated catalog projections.
- Do not scan immutable `standards/*/versions/**` payloads, arbitrary family-root Markdown, repository-wide prose, or documents outside the three named root classes.
- Do not add a package activation, release, tag, publication, GitHub mutation, or durable evidence artifact under this plan.

### 3.3 Ownership and Preserved Behavior

| Boundary | Owner / Responsibility |
| --- | --- |
| Plan owns | The early human-readable package-reference review in release prep, its tests, and its operator documentation. |
| Depends on | A syntactically usable candidate source at `catalogs/{target-major}.toml`, current family-root documents, the release contract, and the later authoritative `packages check-release` gate. |
| Does not own | Catalog correctness beyond the minimum selection facts needed for safe reporting; release-consistency classification; package activation; document edits; release publication. |
| Must preserve | Report-only semantics; existing release-literal sweep bytes and target classes; changelog/version mutation ordering; dry-run behavior; summary/manual handoff; all `check-release` authority and diagnostics. |

### 3.4 Constraints and Authorization

- Use the target release major to select the author-owned candidate source `catalogs/{target-major}.toml`; do not read `.standards/catalog.toml`, because that generated consumer projection may legitimately await the release's reconcile step.
- Resolve consumer packages from the sole `role = "default"` entry. Resolve `internal` and `reference-only` families from the numerically greatest package version in their respective role. `retained` and `candidate` entries never become the expected current version. Compare `(major, minor)` numerically so `1.10` sorts after `1.9`.
- Validate and compute the complete report plan before `bump_version` or any other release-prep write. A missing/malformed target-major catalog, non-canonical package version, duplicate package/version row, or ambiguous selection fails release prep while the tree is still pristine. Reference mismatches themselves remain successful review findings: they neither fail the command nor mutate a document.
- Scan only regular existing named files under catalog-selected family directories, in family/path/line order. A role-appropriate family without `adopt.md` is valid; reference-only and internal families in the current corpus demonstrate this no-op case.
- Recognize only package-version forms established by the current release-consistency grammar. Apply its family-local interpretation to shallow `versions/{version}/` links and its historical-section/phrase classification so released-history and migration references do not masquerade as current drift. Private helper decomposition and exact non-sensitive prose remain executor discretion.
- Keep the package report visibly separate from the outgoing release-literal report and label it `review; nothing was rewritten`. The returned summary detail reports the number of mismatching occurrences, including zero.
- Run `scripts/bootstrap-worktree.sh` directly in an implementation worktree. Git/index/history-dependent work and the repository gate run direct-local. CPU-intensive synchronized-tree-compatible checks run through rexec v0.2 as `rexec -- COMMAND`; no local/fallback rexec switch exists or may be introduced.

## 4. Current State and Target State

### 4.1 Current State

`sweep_version_references` receives the outgoing Project Standards release version and prints literal occurrences across a curated review corpus. Family-root `adopt.md` and `README.md` happen to be in that corpus, but they normally carry package versions such as `adr@1.5` and `versions/1.5/`, not the tool release version such as `5.18.0`. Adding `agent-summary.md` to the same target list therefore would not find the stale package references described by #164. The function reports only; it never substitutes.

The candidate catalog source already distinguishes consumer defaults, retained/candidate versions, reference-only packages, and internal packages. The release-consistency implementation already compares mutable family-root Markdown with catalog-current package facts and rejects stale current assertions during `packages check-release`, but that authoritative JSON finding arrives late in the mechanical chain and has no focused release-prep regression. `tests/test_release_prep.py` does not exercise either reference report.

### 4.2 Target State

Before release prep performs its first write, it loads the target-major catalog source into a deterministic package-reference review plan. For each selected family it reads only the three allowed mutable root documents, recognizes current-bearing package-version references under the established grammar, and classifies mismatches against the catalog-selected version while ignoring classified historical predecessor references. After the existing outgoing release-literal report, release prep prints a separate package-reference review section and records its mismatch count in the closing summary.

Current references, a family whose selected version did not advance, absent optional adoption guides, and classified predecessor/history lines are successful no-ops. A stale current assertion is printed with enough identity to edit by judgment, but the command returns success unless another release-prep step fails. The later `packages check-release` invocation remains the fail-closed machine decision.

### 4.3 Delta Summary

| Area | Current | Target | Must Preserve |
| --- | --- | --- | --- |
| Selection input | One outgoing tool-release literal. | One expected package version per family from `catalogs/{target-major}.toml`. | Candidate source ownership; numeric package ordering. |
| Review corpus | Curated tool-release paths; family `agent-summary.md` absent. | Separate exact family-root `README.md`, optional `adopt.md`, and `agent-summary.md` corpus. | Existing tool-release target set unchanged; immutable payloads excluded. |
| Reference semantics | Substring match for one tool version. | Established package selector/link/argument/prose grammar plus historical classification. | Review-only output; later `check-release` remains authoritative. |
| Failure ordering | Changelog and baseline preflight occur before mutation; the existing sweep cannot fail on catalog shape. | Package-report inputs and selection also validate before mutation. | No new partial-release state on report setup failure. |
| Evidence | No release-prep sweep tests. | Correct-reason RED, selection/matching units, CLI sequencing, no-mutation and no-op controls, fast gate. | Existing two regression tests and manual handoff text. |

## 5. Change Surface and Architecture

### 5.1 Components and Ownership

| Component / Surface | Current Responsibility | Planned Responsibility | Paths / Contracts | Owning Task |
| --- | --- | --- | --- | --- |
| Candidate package facts | Used later by package-contract commands. | Supply minimal validated selected family/version facts before release mutation. | `catalogs/{target-major}.toml`; `scripts/release_prep.py` | T1 |
| Package-reference review | Absent from release prep. | Compare recognized current-bearing family-root references and print deterministic review lines/count. | `scripts/release_prep.py`; `standards/{family}/{README,adopt,agent-summary}.md` read-only | T1 |
| CLI orchestration | Runs one outgoing-release report after version bump. | Precomputes package review before mutation, then prints both independent reports and summary rows. | `scripts/release_prep.py::main`; `StepResult` | T1 |
| Regression proof | Covers manual handoff and non-main refusal only. | Covers catalog roles/order, grammar, historical/no-op behavior, stale predecessor report, CLI sequencing, and byte preservation. | `tests/test_release_prep.py` | T1 |
| Operator truth | Describes only outgoing-release references. | Distinguishes the two reports and later authoritative release gate. | `meta/versioning.md`; `scripts/README.md` | T1 |

### 5.2 Change-Surface Matrix

| Surface | Applies? | Invariant / Required Change | Proof | Task |
| --- | --- | --- | --- | --- |
| Behavior | yes | Add deterministic catalog-selected package-reference review without mutation or mismatch failure. | PV-T1-001, PV-T1-002 | T1 |
| Architecture / dependency direction | yes | Keep the release script stdlib-only and read candidate catalog/family docs directly; do not import the installed package or generated projection. | PV-T1-001 | T1 |
| Public / cross-task interface | yes | Preserve CLI arguments/exits; add one clearly labeled output section and summary row. | PV-T1-002 | T1 |
| Data / state | yes | Validate report inputs before any existing release write; never write scanned docs/catalog. | PV-T1-002 | T1 |
| Configuration | no | No configuration or catalog mutation. | PV-T1-002 | T1 |
| Security / trust | yes | Bound reads to target-major catalog and exact regular family-root files; malformed selection fails before mutation. | PV-T1-001, PV-T1-002 | T1 |
| Compatibility / migration | yes | Existing literal sweep, dry-run, summary, verification chain, and later release gate retain their behavior. | PV-T1-002 | T1 |
| Operations / deployment | no | No live action, release, or publication. | PV-T1-003 | T1 |
| Documentation | yes | Release contract and script reference describe both reports accurately. | PV-T1-003 | T1 |
| Durable evidence | no | Focused tests and commit make the repeatable proof durable; logs remain ephemeral. | PV-T1-003 | T1 |

### 5.3 Binding Decisions

| ID | Decision | Rationale | Source | Affected Task(s) |
| --- | --- | --- | --- | --- |
| D-001 | Add a second package-reference report; do not broaden the outgoing release-literal target list. | Package and tool releases are different axes; `agent-summary.md` contains package references. | #164 owner correction; current corpus | T1 |
| D-002 | Read `catalogs/{target-major}.toml` and resolve default/max-by-role numerically. | It is the author-owned candidate source available before reconcile; generated consumer state can lag legitimately. | `meta/versioning.md`; catalog/release-consistency code | T1 |
| D-003 | Reference mismatches are report-only, while malformed selection input fails before mutation. | The script supplies judgment-free review but must not create partial release state from a late precondition failure. | `meta/versioning.md`; `release_prep.py` sequencing | T1 |
| D-004 | Reuse the established reference forms and historical classification as a behavioral contract without changing `release_consistency.py`. | A parallel grammar would drift; changing the authoritative gate is outside #164. | `release_consistency.py::_references`; request | T1 |

## 6. Requirements and Acceptance

| ID | Requirement | Source | Priority | Owner Task | Task(s) | Proof(s) |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-001 | Resolve each selected package version from the target-major candidate catalog: sole consumer default or numeric maximum for internal/reference-only roles; never retained/candidate. | `request`, `meta/versioning.md`, catalog role evidence | Must | T1 | T1 | PV-T1-001 |
| REQ-002 | Review only the three named mutable family-root document classes using stable package selector/link/argument/prose recognition and historical classification. | `request`, #164 owner correction | Must | T1 | T1 | PV-T1-001 |
| REQ-003 | Print stale current references deterministically with observed/expected identity while current, unchanged, optional-absent, and historical predecessor cases are no-ops. | `request` | Must | T1 | T1 | PV-T1-001 |
| REQ-004 | Preserve report-only semantics, CLI exit behavior, dry-run, and the outgoing release-literal sweep, including exclusion of family agent summaries from that old sweep. | `request`, #164 owner correction | Must | T1 | T1 | PV-T1-002 |
| REQ-005 | Validate package-report inputs before the first release mutation and integrate the independent result into `main()` output and the closing `StepResult` summary. | `meta/versioning.md`, current `main()` sequencing | Must | T1 | T1 | PV-T1-002 |
| REQ-006 | Keep the release contract and script reference synchronized with the two review reports and later authoritative `packages check-release` gate. | `request`, `meta/versioning.md` | Should | T1 | T1 | PV-T1-003 |
| REQ-007 | Pass focused unit/CLI integration checks, Python statics, scoped Markdown checks, and the direct-local fast repository gate under rexec v0.2 discipline. | `request`, repository instructions | Must | T1 | T1 | PV-T1-003 |

## 7. Verification and Evidence Strategy

- **Authoritative commands:** direct-local `scripts/bootstrap-worktree.sh`; `rexec -- uv run pytest tests/test_release_prep.py`; `rexec -- uv run ruff format --check scripts/release_prep.py tests/test_release_prep.py`; `rexec -- uv run ruff check scripts/release_prep.py tests/test_release_prep.py`; `rexec -- uv run basedpyright`; `rexec -- npx prettier --check -- meta/versioning.md scripts/README.md`; `rexec -- npx markdownlint-cli2 --no-globs :meta/versioning.md :scripts/README.md`; `git diff --check`; and exactly one direct-local `scripts/verify.sh`.
- **Oracles:** target-major catalog entries and role rules; current `release_consistency.py` reference/historical behavior; immutable pre-task bytes for scanned documents and the existing release-literal target set; existing `main()` ordering and summary contract.
- **Negative controls:** consumer default with newer candidate and older retained rows; numeric `1.10` versus `1.9`; reference-only/internal maximum; stale predecessor in a current assertion; the same predecessor in classified history; missing optional `adopt.md`; current selected references; an `agent-summary.md` containing the outgoing tool-release literal; malformed/ambiguous catalog input; and scanned-document byte comparison before/after reporting.
- **Test layers:** pure selection and reference-classification units; output/order tests; `main()`/CLI orchestration with a temporary repository and controlled mutation seams; existing release-prep regressions; Python statics; scoped documentation validation; fast integrated repository gate.
- **External environments:** no GitHub, network, package publication, or live release run is required. The implementation worktree uses rexec v0.2 for compatible CPU work; Git-aware gate behavior remains direct-local because `.git` is never synchronized.
- **Evidence:** command output is ephemeral. The T1 commit and its validated `Plan-*` trailers are the durable checkpoint; no separate evidence file is justified.
- **Late failure:** block T1 before checkpoint. A later integrated failure against a completed T1 creates an append-only correction task with `corrects: [T1]` and `discovered_from:`; do not weaken selection/reference rules or rewrite completed history.

## 8. Execution Summary

| Task | Title | Disposition | Work Type | Phase | Depends On | Requirement(s) | Primary Proof | Parallel / Conflict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T1 | Add catalog-derived package-reference review to release prep | active | brownfield-behavior | P1 | None | REQ-001–REQ-007 | PV-T1-001, PV-T1-002, PV-T1-003 | no / release script, test, and owner docs |

## 9. Implementation Tasks

### Phase P1: Release-Prep Review Behavior

#### T1: Add catalog-derived package-reference review to release prep

- **disposition:** active
- **outcome:** `release_prep.py` produces a deterministic, candidate-catalog-derived review of stale current package-version references in the three mutable family-root document classes, without modifying them, changing the existing release-literal sweep, or displacing `packages check-release` as the release gate.
- **work_type:** brownfield-behavior
- **checkpoint:** one green commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** public
- **depends_on:** []
- **dependency_reason:** none
- **requirements:** [REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007]
- **proof:** [PV-T1-001, PV-T1-002, PV-T1-003]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#164#issuecomment-5235511206, repo:meta/versioning.md#release-requirements, repo:scripts/release_prep.py::sweep_version_references, repo:scripts/release_prep.py::main, repo:src/project_standards/package_contract/release_consistency.py::_family_facts, repo:src/project_standards/package_contract/release_consistency.py::_references, repo:tests/test_release_prep.py::_release_prep_module]
- **consumes:** [target release major, author-owned candidate catalog TOML, exact mutable family-root document bytes, established package reference and historical semantics, existing release-prep step ordering]
- **produces:** [package-version-reference-review-v1 output section, package-reference `StepResult`, focused release-prep regression suite, synchronized operator documentation]
- **preserves:** [all scanned document/catalog bytes, existing outgoing-release reference sweep and target set, CLI arguments and exit meanings, dry-run behavior, changelog/version mechanics, verification/manual handoff, authoritative package release-consistency gate]
- **invariants:** [selection is catalog-derived and numeric, all report preparation precedes release mutation, path/line output is deterministic, mismatches are review-only, malformed selection input fails before writes, immutable version payloads are never scanned]
- **executor_discretion:** [private dataclass/helper names, whether planning and printing are separate private functions, exact concise header/detail wording within the required identity and report-only contract, focused fixture construction]
- **files:** [`scripts/release_prep.py` (modify; owner T1), `tests/test_release_prep.py` (modify; owner T1), `meta/versioning.md` (modify; owner T1), `scripts/README.md` (modify; owner T1)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** on RED or implementation failure, restore the last green task-owned files and keep the release command unchanged. On catalog-preflight failure, exit before `bump_version`; never recover by reading the generated consumer catalog, skipping ambiguity, rewriting documentation, or weakening the later release gate.
- **acceptance:** PV-T1-001 proves selection, reference recognition, historical/current classification, deterministic stale reporting, and predecessor/no-op cases; PV-T1-002 proves pre-mutation CLI integration, byte preservation, mismatch success, and exact preservation of the outgoing release-literal sweep; PV-T1-003 proves operator truth and the proportional repository gate.
- **sub-tasks:**
  - **T1.1 CHARACTERIZE / PRECHECK** — run bootstrap, `rexec config show`, and `rexec doctor`; capture the existing release-literal targets/output, `main()` ordering, representative consumer/reference-only/internal root forms, and pre-task bytes for all four claimed files.
  - **T1.2 RED** — add focused tests with a target-major catalog whose selected package is a successor while one current family-root selector/link/enable/prose reference still names the predecessor; expected failure is absence of a package-reference review line/header, not import, fixture, branch, or release-mutation failure.
  - **T1.3 Verify RED** — run the focused release-prep test selection through rexec and confirm the test reaches the current report boundary, returns no package review, and fails on that missing behavior for the intended reason.
  - **T1.4 GREEN** — implement minimum pre-mutation candidate-catalog selection, bounded root-document matching/classification, deterministic report output and summary integration; update the two owner documents without touching the old target collection or any scanned package document.
  - **T1.5 Verify GREEN / REFACTOR** — prove consumer default, candidate/retained exclusion, reference-only/internal numeric max, stale predecessor, historical predecessor, current/no-change, absent optional adopt guide, malformed preflight, mismatch-success, document-byte preservation, dry-run, and old-sweep exclusion cases; remove only duplicated private logic while retaining the binding grammar.
  - **T1.6 Verify Task** — run PV-T1-001–PV-T1-003, Python statics, scoped Markdown checks, `git diff --check`, inspect the exact four-file implementation diff, then run exactly one direct-local fast `scripts/verify.sh`; create the checkpoint only when every result is green.

## 10. Integration, Migration, and Recovery

### 10.1 Integration Sequence

1. From a green implementation worktree, characterize the existing literal sweep and add correct-reason RED at the new package-report boundary.
2. Compute and validate the package review plan before release mutation, then print it as a separate report in the established reference-review portion of `main()`.
3. Preserve the later verification chain: a review mismatch remains exit-zero at this step, while `packages check-release` makes the authoritative release decision.
4. Run focused proof and the one fast gate; checkpoint all four task-owned paths together so behavior and operator truth cannot diverge.

### 10.2 Failure and Recovery

- No data or configuration migration exists, no live release is run, and there is no point of no return in this task.
- Catalog/read/selection setup failure aborts before `bump_version`, leaving repository bytes untouched.
- A package-reference mismatch prints for owner review and does not alter exit status; the owner edits family-root prose separately during the release cut and reruns the command/gate.
- A post-checkpoint integration failure produces a correction task and reruns the focused proof plus fast gate. Reverting the one checkpoint restores prior release-prep behavior without payload or state migration.

## 11. Risks, Assumptions, and Open Questions

| ID | Risk / Assumption | Likelihood | Impact | Treatment / Impact if False | Owner / Task |
| --- | --- | --- | --- | --- | --- |
| R-001 | A second independently invented grammar could disagree with `packages check-release`. | medium | medium | Bind to the existing recognized forms and historical rules; cross-test the same representative lines without changing the gate. | T1 |
| R-002 | Lexicographic max would choose `1.9` over `1.10`. | medium | high | Parse canonical package versions into numeric pairs and include the explicit negative control. | T1 |
| R-003 | Catalog validation after the version bump could leave a partial release tree. | low | high | Plan/validate the entire report before any existing write and assert ordering in the `main()` integration test. | T1 |
| A-001 | The target release major names the candidate catalog source to review. | high confidence | If false, MAJOR release prep would inspect the outgoing catalog and misreport new defaults. | Confirmed by release-contract candidate/catalog-major ordering; T1 uses target major. | T1 |
| A-002 | Missing `adopt.md` is valid for non-consumer family roles. | high confidence | If false, the report would need to become a family-shape validator. | Current reference-only/internal families and package availability contract establish the no-op; shape validation remains elsewhere. | T1 |

No blocking open questions remain. Exact private helper names and output punctuation are deliberately left to the executor within the binding identity, ordering, and report-only contract.

## 12. Final Verification

Completion requires all of the following on the integrated T1 checkpoint:

1. Reconcile REQ-001–REQ-007 with PV-T1-001–PV-T1-003 and the checkpoint trailers; no requirement or proof is orphaned.
2. Confirm the stale successor/predecessor fixture fails for the correct reason before implementation and passes afterward, while current, unchanged, historical, and absent-optional cases remain no-ops.
3. Confirm malformed/ambiguous catalog input aborts before the first mutation and a reference mismatch itself remains report-only and exit-zero.
4. Confirm only exact selected family-root `README.md`, `adopt.md`, and `agent-summary.md` files are read, immutable payloads are excluded, and scanned file/catalog bytes remain unchanged.
5. Confirm `sweep_version_references` retains its prior target set/output contract and an outgoing tool-release literal present only in a family `agent-summary.md` is not added to that old report.
6. Confirm the two operator documents distinguish the outgoing tool-release report, the candidate-catalog package report, owner judgment, and the later `packages check-release` gate.
7. Confirm focused tests, Ruff, BasedPyright, scoped Prettier/markdownlint, `git diff --check`, and exactly one direct-local fast repository gate are green; no full gate is required for this intermediate scripts/tests/docs correction.
8. If any integrated check fails after checkpoint, append a correction task and rerun this decision; do not repair code inside final verification or silently change completed T1.

## 13. Close-out

- Record the final checkpoint commit and validated `Plan-*` identity before marking T1 done.
- Harvest only material deviations or newly discovered release-contract work; file unrelated follow-up rather than broadening #164.
- Return issue #164 to the release orchestrator with the corrected acceptance evidence; do not close the issue or publish under this plan.
- Preserve the final behavior/operator truth in the four task-owned files. No separate handoff, evidence document, package cut, or llm-wiki contribution is required for this repository-local implementation detail unless execution establishes a reusable cross-repository lesson.
- Delete this plan and its execution scratch only through the parent release plan's close-out after the checkpoint, issue lifecycle, and release evidence are durably reconciled.

## Appendix B. Requirement-to-Proof Traceability

| Proof ID | Requirement(s) | Task | Method | Oracle | Command / Procedure | Expected Result | Negative Control | Environment | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PV-T1-001 | REQ-001, REQ-002, REQ-003 | T1 | unit and property-style table tests | Candidate catalog role rows; numeric package-version ordering; current release-consistency reference/historical forms | `rexec -- uv run pytest tests/test_release_prep.py` focused on selection, matching, and output cases | Consumer default and internal/reference-only numeric max produce deterministic expectations; stale current references print observed/expected path lines; current, unchanged, historical predecessor, and absent optional documents produce zero mismatches. | Newer candidate/older retained rows, `1.9` versus `1.10`, predecessor moved between current and historical contexts, and a hollow family-root glob without grammar. | rexec v0.2 remote worker, synchronized source tree | ephemeral |
| PV-T1-002 | REQ-004, REQ-005 | T1 | CLI orchestration and byte-preservation integration | Pre-task `main()` order, `StepResult` contract, old target-set characterization, and exact input bytes | `rexec -- uv run pytest tests/test_release_prep.py` focused on `main()`, dry-run, sequencing, and preservation cases | Report inputs validate before mutation; mismatch run succeeds and prints the new independent section/summary; malformed selection stops before the bump seam; all scanned bytes and existing release-literal behavior remain unchanged. | Malformed/ambiguous catalog, mutation spy before report-plan completion, outgoing tool-release literal present only in `agent-summary.md`, and deliberate scanned-byte comparison. | rexec v0.2 remote worker with temporary repository fixtures; no live release | ephemeral |
| PV-T1-003 | REQ-006, REQ-007 | T1 | documentation inspection, static analysis, and integrated regression | Release contract, repository instructions, and exact four-file diff | Focused Python/Markdown commands from §7, `git diff --check`, then one direct-local `scripts/verify.sh` | Operator docs describe both reports and later gate accurately; Python and Markdown checks pass; fast repository gate is green; diff contains only the four claimed implementation paths. | Reintroducing rewrite language, claiming agent summaries joined the old literal sweep, omitting `check-release` authority, or changing an unclaimed path fails inspection/gates. | rexec v0.2 for synchronized CPU checks; local Git-aware fast gate | ephemeral |
