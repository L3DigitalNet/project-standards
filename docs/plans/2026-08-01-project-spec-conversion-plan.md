---
plan_format: 3
title: 'Project Specification Preservation-First Conversion Implementation Plan'
slug: 'project-spec-conversion'
status: active
revision: 1
revises_revision: 0
revision_reason: 'initial implementation plan for approved SPEC-055C revision 0.2'
pause_reason: ''
source: 'approved SPEC-055C revision 0.2; L3DigitalNet/project-standards#55; owner interface clarification'
spec_ref: 'docs/specs/2026-08-01-project-spec-conversion-plan-input.md'
created: 2026-08-11
updated: 2026-08-11
owners:
  - 'Chris Purcell / L3DigitalNet'
  - 'Coding agents under human review'
---

# Project Specification Preservation-First Conversion Implementation Plan

> **Definition, not state.** Authoring drafts live under `.project-pipeline/2026-08-01-project-spec-conversion/authoring/`; the orchestrator alone generates and mutates execution state under `.project-pipeline/2026-08-01-project-spec-conversion/execution/`.

## 1. Objective

Add a public, opt-in `project-standards spec import` workflow to the selected Project Specification 1.9 package. An operator supplies a contained legacy source, a distinct contained `--output` target, and an explicit specification ID; preview produces a deterministic, structurally valid conversion and digest without writing, while apply regenerates the same typed plan from current snapshots and writes once only when the supplied digest matches. Every source byte remains represented exactly once at an exact canonical destination or in review, and existing `spec new`, `spec upgrade`, predecessor packages, and adoption without conversion remain unchanged.

## 2. Authority and Source Map

| Source | Source Role | Authority / Use | Version / Date | Affected Plan Surface |
| --- | --- | --- | --- | --- |
| `request` | normative | Execute the approved #55 design against the unpublished 1.9 candidate; require explicit `--output`, preserve the source, infer no target, use targeted proof only, and do not run a repository-wide gate, create a release candidate, publish, or cut 1.10. | 2026-08-11 | §§1, 3, 6–13; T1–T2 |
| `spec:docs/specs/2026-08-01-project-spec-conversion-plan-input.md#7-requirements` | normative | Preservation, mapping, diagnostics, preview/apply, refusal, determinism, compatibility, and interface obligations. | approved revision 0.2, 2026-08-11 | §§1, 3–12; T1–T2 |
| `spec:docs/specs/2026-08-01-project-spec-conversion-plan-input.md#83-design-decisions` | decision | Reuse `ProviderOperation.FIX`, exact registry-title matching, adaptive review fences, one explicit ID, and digest-bound regeneration; reject fuzzy mapping and persisted plan handles. | approved revision 0.2 | §§3–5, 9–12; T1–T2 |
| `spec:docs/specs/2026-08-01-project-spec-conversion-plan-input.md#101-primary-workflow` | normative | The operator supplies contained source and target paths; apply regenerates once and executes one matching in-memory plan. | approved revision 0.2 | §3, Appendix A, T2 |
| `issue:L3DigitalNet/project-standards#55` | normative | Accepted conversion outcome, adoption limitation, explicit-confirmation boundary, end-to-end fixture, and preservation acceptance. | live body verified 2026-08-11 | §§1, 3, 6–12; T1–T2 |
| `repo:src/project_standards/specs/cli.py::_run_upgrade` | current-state evidence | Selected-package dispatch, safe source/target snapshots, lock selection, human/JSON errors, and existing `--output` convention. | `b459448f` | §§4–5, 9; T2 |
| `repo:src/project_standards/cli_contract.py::PUBLIC_COMMAND_EXIT_CODES` | current-state evidence | Public command exit-code registry and documentation parity contract. | `b459448f` | §§4–7, 9; T2 |
| `repo:src/project_standards/specs/document.py::parse_document` | current-state evidence | Fence-aware structural parsing and current document validation seam. | `b459448f` | §§4–5, 9; T1 |
| `repo:src/project_standards/specs/registry.py::registry_from_templates` | current-state evidence | Selected template registry and canonical `section_titles` source. | `b459448f` | §§4–5, 9; T1 |
| `repo:src/project_standards/control_plane/schemas.py::MutationPlanSchema` | current-state evidence | Closed typed mutation plan currently carries actions and content-safe diagnostics but no import block/disposition report. | `b459448f` | §§4–5, 9, Appendix A; T1 |
| `repo:src/project_standards/control_plane/providers.py::_bind_fix_actions_to_snapshots` | current-state evidence | `FIX` already binds whole-file create/update actions to immutable document snapshots. | `b459448f` | §§3–5, 9; T1–T2 |
| `repo:src/project_standards/control_plane/executor.py::apply_authoring_plan` | current-state evidence | Existing contained, staged, preconditioned whole-file executor and cleanup behavior. | `b459448f` | §§3–5, 9–10; T1–T2 |
| `repo:standards/project-spec/versions/1.9/payload.toml` | current-state evidence | Unpublished selected payload has scaffold/upgrade mutation-plan providers but no import `FIX` provider. | Project Specification 1.9 at `b459448f` | §§4–6, 9; T2 |
| `repo:standards/project-spec/versions/1.9/providers/project_spec.py::run_upgrade` | current-state evidence | Selected 1.9 authoring-provider pattern and registry/template ownership. | Project Specification 1.9 at `b459448f` | §§4–6, 9; T2 |
| `repo:tests/package_contract/test_project_spec_1_9.py::test_project_spec_1_9__is_complete_and_preserves_every_1_8_byte` | current-state evidence | Candidate integrity and predecessor immutability pattern; the same file owns projection, provider/schema, digest, and selected-catalog assertions. | `b459448f` | §§6–9, 12; T2 |
| `repo:docs/handoff/conventions.md#18-match-verification-to-the-changed-surface` | decision | Engine changes require focused tests/statics; payload/catalog changes require the five package validators and Markdown checks. | current | §§3, 7, 9, 12; T1–T2 |
| `repo:docs/handoff/conventions.md#22-rexec-v02-is-a-remote-only-root-configured-execution-path` | operational evidence | Compatible CPU-heavy checks use `rexec`; Git/index/history and local bootstrap work remain direct-local. | current | §§3, 7, 9, 12; T1–T2 |

Conflict precedence: current explicit owner direction resolves the CLI target omission; the approved specification governs behavior and architecture; #55 supplies accepted outcome context; repository code/tests establish current state only. No material target conflict remains.

## 3. Scope, Boundaries, and Constraints

### 3.1 In Scope

- A deterministic conversion core that partitions raw source bytes without gaps or overlap, strips only the approved ASCII decimal/dotted/optional-punctuation heading prefix, and exact-matches the remainder to the selected 1.9 `Registry.section_titles` values.
- A closed typed import-plan report carrying source/target snapshots, explicit ID, ordered mapped/review dispositions, content-safe owner-decision diagnostics, target bytes, and a deterministic digest alongside the existing whole-file mutation action.
- Public `project-standards spec import SOURCE --output TARGET --id SPEC-XXXX` preview and `--apply --expected-plan-digest DIGEST` behavior through the selected 1.9 `FIX` provider.
- Structural validation, adaptive-fence preservation, human/JSON reporting, containment/precondition/fault cleanup, and regressions for no-match/new-spec-only adoption plus existing `new` and `upgrade` behavior.
- Project Specification 1.9 payload/provider/schema/docs, package digest/catalog/lock state, source projection, CLI reference, and focused tests needed to ship the feature in the later consolidated release.

### 3.2 Out of Scope and Deferred

- No fuzzy, semantic, alias, case-folded, whitespace-normalized, or best-effort heading mapping; no automatic resolution of review content.
- No source overwrite, `--in-place`, inferred/default output target, persisted plan file/handle, new provider operation, Project Specification 1.10, conversion-on-adoption option, or new mapping profile.
- No mutation of Project Specification 1.8 or another released payload, no unrelated control-plane redesign, and no change to `new`/`upgrade` public behavior.
- No `scripts/verify.sh`, hosted CI, release candidate, version bump, tag, asset, publication, GitHub mutation, release note, or issue closure. The umbrella T43 owns one full integrated qualification and publication.

### 3.3 Ownership and Preserved Behavior

| Boundary | Owner / Responsibility |
| --- | --- |
| T1 owns | Pure conversion/block-accounting behavior, the closed typed import-plan extension, central generated mutation-plan schema, and focused unit/property/provider/executor proof. |
| T2 owns | Public CLI, selected 1.9 provider/payload/schema/docs, digest/catalog/lock/projection reconciliation, end-to-end/fault/compatibility proof, and all generator-owned Project Spec 1.9 outputs. |
| Plan does not own | Editorial owner decisions, source cleanup, automatic adoption conversion, final release qualification/publication, or consumer repositories. |
| Must preserve | Source bytes and source file, existing target on refusal, `new`/`upgrade`, no-match/new-spec-only adoption success, 1.8 bytes/digest, unrelated provider operations/packages/configuration, and the executor's fail-closed semantics. |

### 3.4 Constraints and Authorization

- `--output` is required in preview and apply, must be consumer-root-relative and distinct from `SOURCE`, and has no default. Apply may create a missing target or update a regular target only under the same explicit overwrite policy the import parser exposes; it never mutates `SOURCE`.
- The source partition must be deterministic, gap-free, non-overlapping, and cover the entire raw byte sequence. Every partition block has exactly one ordered disposition; rendering may choose a repository-conforming representation only if an independent byte-accounting oracle can recover every original byte exactly once and structural validation passes.
- A heading maps only after stripping one leading ASCII decimal or dotted-decimal number plus the approved optional punctuation/separator; the remaining title must equal one selected canonical title byte-for-byte. A near match, unlisted title, preamble, duplicate destination, or otherwise ambiguous block goes to review.
- Preview and apply each create one in-memory plan. Apply compares its deterministic digest with the operator value before calling `apply_authoring_plan` exactly once; a mismatch or refusal calls the executor zero times.
- Project Specification 1.9 remains the selected mutable candidate. Update its aggregate digest and all local catalog/lock declarations coherently; do not cut a successor version.
- Run `scripts/bootstrap-worktree.sh` direct-local when each implementation worktree is created and again after `src/**` or payload changes. Run compatible CPU-heavy focused tests/statics through `rexec --`; keep Git/diff/plan-state checks local.
- Use correct-reason RED before each behavior change. Do not run or wait for repository-wide or hosted gates in this child plan.

## 4. Current State and Target State

### 4.1 Current State

The `spec` group exposes validate, lint, extract, next, new, and upgrade. Selected-package `new`/`upgrade` snapshot safe paths, invoke versioned providers, receive a closed `MutationPlanSchema`, and write through `apply_authoring_plan`. `ProviderOperation.FIX` already owns authoring mutation-plan semantics and binds actions to immutable document snapshots, but Project Specification 1.9 declares no `FIX` provider and the plan schema cannot yet carry the required block/disposition report.

Project Specification 1.9 is already the local Catalog 5 default and remains unpublished. Its provider derives the registry from immutable templates and emits scaffold/upgrade plans; its 1.8 predecessor is protected by an exact digest. The package contract and symlink-only projection already provide the integrity and activation surfaces this feature must update coherently.

### 4.2 Target State

The conversion core produces one closed, deterministic typed plan whose ordered records prove total byte accounting and exact mapping/review dispositions. The selected 1.9 provider renders and structurally validates the target, exposes only content-safe diagnostics, and returns one whole-file create/update action bound to the target snapshot.

The public CLI requires explicit source, output, and ID. Preview reports content, mappings, review records, diagnostics, plan digest, selected provider, and `written: false` without filesystem changes. Apply regenerates once from current source/target snapshots, refuses a missing/wrong/stale digest before execution, and passes the matching plan once to the existing executor. The source never changes, failure publishes nothing, and successful apply reports exactly one target write.

### 4.3 Delta Summary

| Area | Current | Target | Must Preserve |
| --- | --- | --- | --- |
| Conversion behavior | No import core or public verb. | Exact mapping plus review-visible total preservation. | No semantic guessing or byte loss. |
| Typed plan | Actions and diagnostics only. | Closed import records and deterministic digest remain in memory with the action. | Existing mutation plans continue validating unchanged. |
| Public CLI | `new` and additive `upgrade`. | Explicit source/output/ID preview and digest-bound apply. | Existing verbs and exit contracts. |
| Provider/package | 1.9 has no `FIX` import provider. | One 1.9 `FIX` mutation-plan provider and documented workflow. | 1.8 bytes; no 1.10/new operation. |
| Generated state | 1.9 digest/catalog/lock reflect pre-import payload. | All digest declarations and projection checks reflect the amended 1.9 payload. | Package role/default and unrelated generated state. |

## 5. Change Surface and Architecture

### 5.1 Components and Ownership

| Component / Surface | Current Responsibility | Planned Responsibility | Paths / Contracts | Owning Task |
| --- | --- | --- | --- | --- |
| Conversion core | None. | Partition raw bytes, exact-match headings, render mapped/review content, validate invariants, and produce typed records. | `specs/commands/import_legacy.py`; `project-spec-import-plan-v1` | T1 |
| Control-plane schema | Closed mutation actions/diagnostics. | Carry the closed import report without weakening existing action validation. | `control_plane/schemas.py`; generated mutation schema | T1 |
| Provider boundary | Generic `FIX` snapshot/action binding. | Preserve generic binding and transport import records to the caller/executor. | `providers.py::_bind_fix_actions_to_snapshots` | T1 |
| CLI/orchestration | Selected `new`/`upgrade` paths. | Snapshot distinct source/output, invoke 1.9 import provider once per command, report preview, and conditionally execute once. | `specs/cli.py`; `cli.py`; CLI contract | T2 |
| Selected payload | 1.9 scaffold/upgrade/render/validate providers. | Add one `FIX` import provider backed by the T1 core and selected templates. | 1.9 provider, manifest, schemas | T2 |
| Package/generated truth | Current 1.9 digest and projection. | Recompute digest/catalog/lock and verify symlink projection after the amended payload. | family manifest, Catalog 5, `.standards`, projection | T2 |
| Documentation | `new`/`upgrade` reference and adoption guidance only. | Exact import preview/apply/review/no-op/refusal guidance. | 1.9 docs; `docs/usage.md` | T2 |

### 5.2 Control and State Flow

1. The CLI captures safe immutable snapshots for distinct source and output paths and passes explicit ID plus mode to the selected 1.9 `FIX` provider.
2. The provider invokes the pure conversion core with the selected registry/templates. The core produces one typed in-memory plan with ordered dispositions, diagnostics, target bytes, snapshot identities, and canonical digest.
3. Preview serializes that same plan to human/JSON output and writes nothing.
4. Apply regenerates one current plan, compares its digest with `--expected-plan-digest`, then either refuses before execution or calls `apply_authoring_plan` once with the plan's whole-file action.
5. The executor rechecks preconditions, stages the complete target, rechecks before first publication, publishes one target, and cleans staged state on every path.

### 5.3 Change-Surface Matrix

| Surface | Applies? | Invariant / Required Change | Proof | Task |
| --- | --- | --- | --- | --- |
| Behavior | yes | Exact mapping, total preservation, review routing, preview, and guarded apply. | PV-T1-001, PV-T2-001 | T1–T2 |
| Architecture / dependency direction | yes | CLI → selected `FIX` provider → pure core → existing executor; no direct writer. | PV-T2-001 | T2 |
| Public interface | yes | Required `SOURCE`, `--output`, `--id`; apply additionally requires digest. | PV-T2-001 | T2 |
| Data / state | yes | One transient typed plan; no persisted handle; source unchanged. | PV-T1-001, PV-T2-001 | T1–T2 |
| Configuration | yes | 1.9 digest/catalog/lock changes only; no import option. | PV-T2-002 | T2 |
| Security / trust | yes | Containment, no-follow snapshots, content-safe diagnostics, and preconditioned publication. | PV-T2-001 | T2 |
| Compatibility / migration | yes | 1.8/new/upgrade/adoption behavior remains exact; import is opt-in. | PV-T2-001, PV-T2-002 | T2 |
| Operations / deployment | no | No service, external environment, or publication action. | PV-T2-002 | T2 |
| Documentation | yes | Public CLI and 1.9 adoption guidance agree. | PV-T2-002 | T2 |
| Durable evidence | no | Committed source/tests/checkpoints reproduce all proof. | PV-T1-001, PV-T2-001, PV-T2-002 | T1–T2 |

### 5.4 Binding Decisions

| ID | Decision | Rationale | Source | Affected Task(s) |
| --- | --- | --- | --- | --- |
| D-001 | Reuse `ProviderOperation.FIX`, the closed typed mutation-plan path, and `apply_authoring_plan`. | Existing platform boundary already supplies snapshot binding, containment, staging, and rollback. | SPEC-055C D-001 | T1–T2 |
| D-002 | Require explicit `--id` and `--output` for preview/apply; never overwrite source or infer target. | Approved workflow requires source/target paths and source immutability; existing `upgrade --output` is the compatible public convention. | SPEC-055C §§9–10, IR-001–IR-003; owner clarification | T2 |
| D-003 | Strip only the approved numeric prefix and exact-match selected registry titles. | Determinism and preservation exclude aliases and semantic inference. | SPEC-055C D-003 | T1 |
| D-004 | Route duplicates, near/unlisted headings, preamble, and ambiguity to adaptive-fenced review with owner-decision diagnostics. | A visible unresolved decision is safer than guessed placement or loss. | SPEC-055C D-004–D-005 | T1 |
| D-005 | Digest the canonical closed plan representation; apply regenerates once and executes the matching in-memory plan once. | Binds write authorization to reviewed current bytes without persistent handles. | SPEC-055C D-002; FR-008 | T1–T2 |
| D-006 | Amend the unpublished 1.9 payload and its local digest/catalog truth; do not create 1.10 or publish. | #55 and #62 are one consolidated successor train. | request; SPEC-055C lifecycle | T2 |

## 6. Requirements and Acceptance

| ID | Requirement | Source | Priority | Owner Task | Task(s) | Proof(s) |
| --- | --- | --- | --- | --- | --- | --- |
| FR-001 | Public import uses the selected 1.9 `FIX` mutation-plan provider and no new operation. | SPEC-055C §7.1 | Must | T2 | T2 | PV-T2-001, PV-T2-002 |
| FR-002 | Preview/apply require explicit valid ID; neither mints one. | SPEC-055C §7.1 | Must | T2 | T1, T2 | PV-T1-001, PV-T2-001 |
| FR-003 | Only the approved ASCII numeric prefix is stripped; the remainder must exactly equal one selected canonical title. | SPEC-055C §7.1 | Must | T1 | T1, T2 | PV-T1-001, PV-T2-001 |
| FR-004 | Every raw source byte is represented exactly once at a mapped destination or in review. | SPEC-055C §7.1 | Must | T1 | T1, T2 | PV-T1-001, PV-T2-001 |
| FR-005 | Ambiguous, duplicate, and unmapped blocks remain review-visible with owner-decision diagnostics. | SPEC-055C §7.1 | Must | T1 | T1, T2 | PV-T1-001, PV-T2-001 |
| FR-006 | The rendered target structurally validates; structural invalidity refuses while review-only diagnostics remain nonfatal. | SPEC-055C §7.1 | Must | T1 | T1, T2 | PV-T1-001, PV-T2-001 |
| FR-007 | Preview is read-only and reports target, diagnostics, deterministic plan digest, and `written: false`. | SPEC-055C §7.1 | Must | T2 | T2 | PV-T2-001 |
| FR-008 | Apply requires expected digest, regenerates once, refuses mismatch, and invokes the executor once only for the matching plan. | SPEC-055C §7.1 | Must | T2 | T1, T2 | PV-T1-001, PV-T2-001 |
| FR-009 | Unsafe paths, aliases, stale preconditions, and staging faults leave source/target unchanged and staged state clean. | SPEC-055C §7.1 | Must | T2 | T2 | PV-T2-001 |
| FR-010 | No-match/new-spec-only adoption remains a successful informational no-op with no writes. | SPEC-055C §7.1 | Must | T2 | T2 | PV-T2-001, PV-T2-002 |
| NFR-001 | Accounting and all preconditions complete before the first write. | SPEC-055C §7.2 | Must | T2 | T1, T2 | PV-T1-001, PV-T2-001 |
| NFR-002 | Identical bytes/options yield byte-identical ordered reports, target content, and plan digest. | SPEC-055C §7.2 | Must | T1 | T1, T2 | PV-T1-001, PV-T2-001 |
| NFR-003 | Mapping is isolated from parsing, rendering/planning, and executor mechanics. | SPEC-055C §7.2 | Should | T1 | T1 | PV-T1-001 |
| IR-001 | CLI is `spec import SOURCE --output TARGET --id SPEC-XXXX`; apply additionally requires `--apply --expected-plan-digest DIGEST`. | SPEC-055C IR-001; owner clarification | Must | T2 | T2 | PV-T2-001, PV-T2-002 |
| IR-002 | Human output reports source, target, selected 1.9 provider, summary, review diagnostics, digest, and write state. | SPEC-055C IR-002 | Must | T2 | T2 | PV-T2-001, PV-T2-002 |
| IR-003 | JSON uses stable versioned `ok`, `written`, `source`, `target`, `spec_id`, `plan_digest`, `mappings`, `review`, `diagnostics`, and `error` fields. | SPEC-055C IR-003; owner clarification | Must | T2 | T2 | PV-T2-001, PV-T2-002 |
| DR-001 | The transient typed plan retains source/target digests, explicit ID, ordered dispositions/diagnostics, target bytes, and canonical plan digest. | SPEC-055C §7.4 | Must | T1 | T1, T2 | PV-T1-001, PV-T2-001 |
| DR-002 | Every preserved raw block uses an adaptive delimiter that its bytes cannot close. | SPEC-055C §7.4 | Must | T1 | T1, T2 | PV-T1-001, PV-T2-001 |

## 7. Verification and Evidence Strategy

- **Correct-reason RED:** T1 tests fail only because the import core/typed report is absent. T2 tests fail only because the public verb and selected 1.9 import provider are absent. Import, collection, fixture, environment, timeout, and stale-runtime failures do not establish RED.
- **Oracles:** selected 1.9 `Registry.section_titles`; an independent gap-free byte-range/accounting oracle; canonical JSON serialization; current `FIX` snapshot binding; external filesystem snapshots; the immutable 1.8 aggregate digest; existing `new`/`upgrade` and adoption regressions.
- **Layers:** unit, table/property/model, schema/provider contract, CLI integration, deterministic repeat, round-trip byte recovery, filesystem/transaction/fault, package integrity/graph/projection, compatibility, statics, and documentation parity.
- **Negative controls:** near/case/space/punctuation variants, duplicate destination, unlisted/preamble/fence-like bytes, altered plan field, wrong/stale digest, source/target alias, symlink/path escape, target edit after preview, staged/publication fault, forced conversion, changed predecessor byte, stale catalog digest, and accidental repository-wide-gate receipt.
- **Commands:** task bodies name focused reproducible commands. Compatible pytest, Ruff, BasedPyright, and package validators use `rexec --`; `scripts/bootstrap-worktree.sh`, plan bridge, Git/diff, and plan state remain direct-local.
- **Evidence:** all results are repeatable and ephemeral; concise task evidence belongs in generated checklist state and checkpoint trailers. No durable EV artifact is required.
- **Late failure:** block the owning task; after a completed checkpoint append a correction task with `corrects:` and `discovered_from:` and rerun only affected focused proof. Never weaken preservation or move the full release gate into this plan.

## 8. Execution Summary

| Task | Title | Disposition | Work Type | Phase | Depends On | Requirement(s) | Primary Proof | Parallel / Conflict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T1 | Build the deterministic typed conversion core | active | behavior | P1 | None | FR-002–FR-006, FR-008, NFR-001–NFR-003, DR-001–DR-002 | PV-T1-001 | no / T2 contract consumer |
| T2 | Wire the public selected-1.9 workflow and package truth | active | brownfield-behavior | P2 | T1 | FR-001–FR-010, NFR-001–NFR-002, IR-001–IR-003, DR-001–DR-002 | PV-T2-001, PV-T2-002 | no / T1 contract producer |

## 9. Implementation Tasks

### Phase P1: Deterministic conversion and typed plan contract

#### T1: Build the deterministic typed conversion core

- **disposition:** active
- **outcome:** A pure conversion core and closed mutation-plan extension deterministically account for every source byte, exact-map only approved headings, route all other blocks to adaptive-fenced review, structurally validate target bytes, and carry a canonical digest plus content-safe ordered records without changing existing mutation-plan behavior.
- **work_type:** behavior
- **checkpoint:** one green commit with task/requirement/proof evidence and required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** []
- **dependency_reason:** none
- **requirements:** [FR-002, FR-003, FR-004, FR-005, FR-006, FR-008, NFR-001, NFR-002, NFR-003, DR-001, DR-002]
- **proof:** [PV-T1-001]
- **source_refs:** [spec:docs/specs/2026-08-01-project-spec-conversion-plan-input.md#7-requirements, spec:docs/specs/2026-08-01-project-spec-conversion-plan-input.md#9-data-model, spec:docs/specs/2026-08-01-project-spec-conversion-plan-input.md#17-testing-and-acceptance, repo:src/project_standards/specs/document.py::parse_document, repo:src/project_standards/specs/registry.py::registry_from_templates, repo:src/project_standards/control_plane/schemas.py::MutationPlanSchema, repo:src/project_standards/control_plane/providers.py::_bind_fix_actions_to_snapshots, repo:src/project_standards/control_plane/executor.py::apply_authoring_plan]
- **consumes:** [raw source bytes, explicit spec ID, distinct safe source/target snapshots, selected 1.9 templates and Registry.section_titles]
- **produces:** [project-spec-import-plan-v1]
- **preserves:** [existing mutation-plan inputs/actions/diagnostics, executor behavior, source bytes/file, target bytes until execution, no semantic inference]
- **invariants:** [gap-free non-overlapping total byte partition; one ordered disposition per block; exact title equality after only approved prefix stripping; duplicates/near/unlisted/preamble review-only; adaptive delimiter cannot be closed by block bytes; structurally valid target; deterministic canonical digest covers every write-relevant and report-relevant field; diagnostics omit raw source prose]
- **executor_discretion:** [private model/helper names, internal partition representation, mapped-block rendering representation, property-test library/fixture layout, provided every binding invariant and public-consumer contract in Appendix A remains exact]
- **files:** [`src/project_standards/specs/commands/import_legacy.py` (create; owner T1), `src/project_standards/control_plane/schemas.py` (modify; owner T1), `src/project_standards/schemas/mutation-plan.schema.json` (generated; owner T1), `tests/test_spec_import.py` (create; owner T1), `tests/control_plane/test_schemas.py` (modify; owner T1), `tests/control_plane/test_providers.py` (modify; owner T1), `tests/control_plane/test_authoring_executor.py` (modify; owner T1)]
- **parallel_safe:** no
- **conflicts_with:** [T2]
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** If total accounting, structural validity, closed schema, legacy mutation-plan compatibility, or executor non-interpretation fails, abandon the partial core/schema delta and restore the last green checkpoint. Do not weaken closed validation, normalize author bytes, or defer T1 acceptance to T2.
- **acceptance:** PV-T1-001 proves the independent byte-range oracle recovers the complete source exactly once; exact/dotted/punctuated headings map only to selected canonical titles; near/unlisted/duplicate/fence-like blocks remain recoverable in review with content-safe diagnostics; identical inputs yield identical target/report/digest; structural invalidity refuses; existing mutation plans and executor behavior remain valid.
- **sub-tasks:**
  - **T1.1 PRECHECK** — run `scripts/bootstrap-worktree.sh`; inspect selected registry/template parsing, generic `FIX` binding, the closed mutation schema, executor plan consumption, and unchanged 1.8/1.9 package schemas.
  - **T1.2 RED** — add table/property/model tests for the complete mapping/accounting/determinism/refusal contract and closed typed report, including a mutation that changes one covered plan field while retaining target bytes.
  - **T1.3 Verify RED** — run `rexec -- uv run pytest tests/test_spec_import.py tests/control_plane/test_schemas.py tests/control_plane/test_providers.py tests/control_plane/test_authoring_executor.py`; require failures naming the absent import core/report contract only.
  - **T1.4 GREEN** — implement the pure core, closed typed report/schema generation, generic provider transport, and executor-compatible plan while preserving existing plan defaults.
  - **T1.5 Verify GREEN** — rerun the focused suite; run the central schema generator check and targeted Ruff/BasedPyright over T1-owned paths through `rexec`; inspect that no payload/predecessor/catalog path changed.
  - **T1.6 Verify Task** — run PV-T1-001 once on final T1 bytes, inspect the exact task diff, and commit with required checkpoint trailers. Do not run `scripts/verify.sh` or hosted CI.

### Phase P2: Public selected-provider workflow and package closure

#### T2: Wire the public selected-1.9 workflow and package truth

- **disposition:** active
- **outcome:** `spec import` previews and digest-applies one selected-1.9 typed plan through the existing executor; human/JSON output, refusal/rollback, no-op and compatibility behavior are proven; Project Specification 1.9 payload, documentation, digest/catalog/lock state, and projection converge without any release action.
- **work_type:** brownfield-behavior
- **checkpoint:** one green commit with task/requirement/proof evidence and required `Plan-*` checkpoint trailers
- **boundary:** public
- **depends_on:** [T1]
- **dependency_reason:** T2 consumes the closed `project-spec-import-plan-v1` data/digest/report contract and conversion behavior produced by T1.
- **requirements:** [FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-009, FR-010, NFR-001, NFR-002, IR-001, IR-002, IR-003, DR-001, DR-002]
- **proof:** [PV-T2-001, PV-T2-002]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#55, spec:docs/specs/2026-08-01-project-spec-conversion-plan-input.md#73-interface-requirements, spec:docs/specs/2026-08-01-project-spec-conversion-plan-input.md#101-primary-workflow, spec:docs/specs/2026-08-01-project-spec-conversion-plan-input.md#12-error-handling-and-recovery, repo:src/project_standards/specs/cli.py::_run_upgrade, repo:src/project_standards/cli_contract.py::PUBLIC_COMMAND_EXIT_CODES, repo:standards/project-spec/versions/1.9/payload.toml, repo:standards/project-spec/versions/1.9/providers/project_spec.py::run_upgrade, repo:tests/package_contract/test_project_spec_1_9.py::test_project_spec_1_9__is_complete_and_preserves_every_1_8_byte]
- **consumes:** [project-spec-import-plan-v1, selected Project Specification 1.9 registry/templates, safe source/target snapshots, existing apply_authoring_plan contract]
- **produces:** [project-standards-spec-import-v1, project-spec-1.9-import-provider-v1]
- **preserves:** [source file; target on preview/refusal/fault; `spec new`; `spec upgrade`; no-match/new-spec-only adoption; Project Specification 1.8 bytes/digest; existing provider operations; unrelated packages/catalog/lock/artifacts; no publication]
- **invariants:** [required distinct source/output and explicit ID; preview lock/read path only; apply requires expected digest and write lock; one provider plan generated per invocation; mismatch/refusal calls executor zero times; match calls executor once with that same plan; JSON fields/version/exit 0-or-2 stable; provider operation exactly FIX; one whole-file create/update target; selected version exactly 1.9; generated state updated only through owning generators/reconcile]
- **executor_discretion:** [private CLI/helper names, exact concise human wording, JSON schema version token, test fixture organization, and whether a regular output needs an explicit overwrite flag, provided overwrite is never implicit and the public contracts/refusal classes remain exact]
- **files:** [`src/project_standards/specs/cli.py` (modify; owner T2), `src/project_standards/cli.py` (modify help only; owner T2), `src/project_standards/cli_contract.py` (modify exit contract; owner T2), `tests/test_spec_import_cli.py` (create; owner T2), `tests/test_spec_cli.py` (modify lock/help regressions; owner T2), `standards/project-spec/versions/1.9/providers/project_spec.py` (modify; owner T2), `standards/project-spec/versions/1.9/payload.toml` (modify; owner T2), `standards/project-spec/versions/1.9/schemas/provider-input.schema.json` (modify; owner T2), `standards/project-spec/versions/1.9/schemas/mutation-plan.schema.json` (modify; owner T2), `standards/project-spec/versions/1.9/{README.md,adopt.md,agent-summary.md}` (modify; owner T2), `src/project_standards/payloads/project-spec/1.9/**` (generated symlink projection; owner T2), `standards/project-spec/standard.toml` (modify digest only; owner T2), `catalogs/5.toml` (modify 1.9 digest only; owner T2), `.standards/catalog.toml` (generated 1.9 digest only; owner T2), `.standards/lock.toml` (generated selected 1.9 digest only; owner T2), `docs/usage.md` (modify; owner T2), `tests/package_contract/test_project_spec_1_9.py` (modify; owner T2)]
- **parallel_safe:** no
- **conflicts_with:** [T1]
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** Preserve the T1 checkpoint. On CLI/provider/fault failure, revert only T2-owned public/package/generated paths and leave source/target fixtures unchanged; on digest/projection/reconcile failure, regenerate from the authoritative 1.9 payload rather than hand-editing symlinks or unrelated lock state. Do not cut 1.10, mutate 1.8, permit in-place conversion, or run the release gate.
- **acceptance:** PV-T2-001 proves read-only deterministic preview, stable human/JSON reports, explicit distinct output/ID, digest-bound one-call apply, zero-write mismatch/stale/unsafe/fault paths, full byte recovery, structural validity, and `new`/`upgrade`/adoption compatibility. PV-T2-002 proves the amended 1.9 provider/schema/docs are complete, 1.8 is byte/digest exact, 1.9 remains default/unpublished, payload/family/catalog/lock/projection agree, generated state converges, and no full/hosted/release action occurred.
- **sub-tasks:**
  - **T2.1 PRECHECK** — run `scripts/bootstrap-worktree.sh`; confirm T1 checkpoint identity/proof, selected 1.9 provider/manifest/schema/resource declarations, current CLI/help/docs inventory, exact 1.8 digest, 1.9 projection, and expected digest/catalog/lock owners.
  - **T2.2 CHARACTERIZE** — run focused existing `new`, `upgrade`, authoring-executor, selected-provider, adoption-no-match, and 1.9 package tests to capture the preserved green baseline.
  - **T2.3 RED** — add public parser/help/human/JSON/lock tests and selected-provider end-to-end tests covering preview, matching apply, wrong/stale digest, source/output alias, unsafe/symlink paths, structural refusal, review diagnostics, fault cleanup, repeat determinism, and no-match/new-spec-only behavior.
  - **T2.4 Verify RED** — run the new focused CLI/package nodes through `rexec`; require failure because `import` and the 1.9 `FIX` provider are absent, while the characterized preservation set remains green.
  - **T2.5 GREEN** — wire parser/lock/output/dispatch, add the selected 1.9 provider and schema enum, render the typed plan/report, compare expected digest before one executor call, document the workflow, update payload digests/family/catalog declarations, synchronize the projection, and reconcile producer `.standards` state.
  - **T2.6 Verify GREEN** — rerun focused unit/property/provider/executor/CLI/round-trip/fault/compatibility/package tests; run Tier 1 validators, reconcile a second time to a no-op, targeted Ruff/BasedPyright, and scoped documentation formatting/lint through the appropriate local/rexec boundary; inspect exact 1.8 bytes and task diff.
  - **T2.7 Verify Task** — run PV-T2-001 and PV-T2-002 once on final T2 bytes, validate all plan requirements/proofs, and commit with required checkpoint trailers. Do not build a release candidate, run `scripts/verify.sh`, invoke hosted CI, publish, or mutate GitHub.

## 10. Integration, Migration, and Recovery

### 10.1 Integration Sequence

1. T1 lands the closed conversion/typed-plan contract and focused engine proof without changing the selected payload or public CLI.
2. T2 consumes that checkpoint, wires one selected 1.9 public workflow, updates all payload/digest/projection/documentation owners coherently, and ends with focused integration plus package validation green.
3. The parent T27 records child-plan completion. The umbrella T43 later combines this checkpoint with the rest of v5.19, builds the release candidate, runs the sole full/hosted gates, and decides publication.

### 10.2 State and Compatibility Transition

- **Persistent migration:** none. Import is explicit and creates/updates only the requested target after digest confirmation.
- **Compatibility period:** Project Specification 1.8 remains immutable and selectable; 1.9 remains the local default candidate. Existing exact selections, new/upgrade, and adoption without import are unchanged.
- **Idempotency/repeat:** unchanged inputs/options yield the same preview/digest. Apply is not automatically retried; any retry starts with a fresh preview/current digest. Reconcile after the payload digest update must converge to no diff.
- **Point of no return:** none before later release publication. Task checkpoints can be reverted as coherent local commits; published predecessors are never rewritten.
- **Failure recovery:** preview/mismatch/validation refuse before execution; executor faults leave the prior target and source unchanged and clean staging; recovery starts from a fresh preview and never reuses a stored plan.

### 10.3 Late Failure and Correction

A failed child completion check blocks the owning task. If T1 is already complete, a T2-discovered core/schema defect becomes an append-only correction task depending on T1 and T2 as appropriate; it never edits T1 history. A final umbrella gate failure becomes an umbrella correction task and does not retroactively broaden this plan's gate scope.

## 11. Risks, Assumptions, and Open Questions

### 11.1 Risks

| ID | Risk | Likelihood | Impact | Treatment | Owner / Task |
| --- | --- | --- | --- | --- | --- |
| R-001 | A renderer can appear structurally valid while dropping or duplicating author bytes. | medium | high | Independent range/digest accounting and round-trip recovery, including fence-like bytes and mutation negative controls. | T1 |
| R-002 | Preview/apply can accidentally compare one plan then execute another. | medium | high | Identity-based one-plan tests count provider generation and executor calls and mutate snapshots between invocations. | T2 |
| R-003 | Amending mutable 1.9 can leave package/family/catalog/lock/projection digests inconsistent. | medium | high | T2 owns the whole generated surface, five package validators, reconcile convergence, and exact diff review. | T2 |
| R-004 | The new verb can regress `new`, `upgrade`, or adoption/no-match behavior. | low | high | Characterize before RED and run focused compatibility/integration tests in T2. | T2 |

### 11.2 Assumptions

| ID | Assumption | Impact if False |
| --- | --- | --- |
| A-001 | The existing generic mutation-plan contract can be extended with a closed optional import report while legacy plan payloads remain byte-semantically accepted. | Stop T1 and return the minimum schema/architecture amendment; do not introduce a second provider effect or persisted handle. |
| A-002 | The approved target can be rendered structurally valid while preserving each raw source block exactly once under a mapped or review disposition. | Stop T1 and report a specification feasibility defect with the smallest failing byte vector; do not normalize or discard bytes. |

### 11.3 Open Questions

None. The required output-target contract was resolved by owner direction on 2026-08-11; mapping, apply, version, and publication boundaries are approved in SPEC-055C revision 0.2.

## 12. Final Verification

- T1 and T2 each have one identity-matched checkpoint with passing owned proof; the child plan validates under repository bridge 3.5.0 and has no ready correction/blocker.
- Every Must/Should requirement maps exactly to passing Appendix B evidence, and the independent byte oracle recovers every source byte once from the final output/report.
- Public preview/apply, deterministic digest, exact mapping, review diagnostics, structural validation, mismatch/stale/unsafe/fault cleanup, and one-executor-call behavior pass in the focused integration environment.
- Existing `spec new`, `spec upgrade`, no-match/new-spec-only adoption, generic provider/executor behavior, and Project Specification 1.8 bytes/digest remain green.
- Project Specification 1.9 provider/payload/schema/docs, family digest, Catalog 5, `.standards` catalog/lock, and symlink projection agree; a second reconcile is a no-op; unrelated package/generated state is unchanged.
- Targeted Ruff/BasedPyright and scoped Markdown format/lint pass for changed paths. No `scripts/verify.sh`, hosted run, release candidate, version/tag/asset/publication, or GitHub mutation is present; those remain T43 work.
- Any failed condition creates or routes to an append-only correction task; final verification never patches implementation directly or weakens preservation.

## 13. Close-out

- **Completed:** pending both child checkpoints and parent T27 completion evidence.
- **Decisions / deviations harvested:** retain the explicit `--output`, source-immutable, no-default clarification in this durable plan; record any approved deviation in the source specification before implementing it.
- **Risks closed / accepted:** pending T1 accounting and T2 workflow/package proof.
- **Deferred/discovered work filed:** additional mapping profiles and automatic review resolution require separate approved specifications/issues; no speculative follow-up is created by default.
- **Source/ADR/handoff reconciliation:** no ADR or handoff mutation is owned here; parent/release closeout records the final current state.
- **Scratch teardown:** only after terminal child checkpoints and parent consumption are confirmed and no recovery evidence exists solely under `.project-pipeline`.

## Appendix A. Interface and State Contracts

| Contract | Owner / Producer Task | Consumer(s) | Current | Planned / States | Errors / Limits | Compatibility / Invariant | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `project-spec-import-plan-v1` | T1 | T2 CLI/provider; existing executor | Generic plan has actions/diagnostics only. | Closed optional import report: source/target snapshots, explicit ID, ordered block ranges/digests/dispositions/destinations, review diagnostics, target bytes/action, canonical plan digest. | Duplicate/gapped/overlapping block, invalid disposition, unsafe target, structural failure, or digest inconsistency refuses. | Existing plans without import report remain valid; executor consumes only existing action/diagnostic safety fields and never interprets import metadata. | SPEC-055C §§7–9 |
| `project-standards-spec-import-v1` | T2 | Operator / CLI documentation | No verb. | `spec import SOURCE --output TARGET --id SPEC-XXXX [--json] [--apply --expected-plan-digest DIGEST]`; preview is default. | Missing/invalid ID/output/digest, same source/target, unsafe path, structural refusal, mismatch, stale precondition, and fault exit 2 with no write. | Source never changes; target has no inferred default; a regular target is never overwritten implicitly; existing verbs unchanged. | SPEC-055C IR-001–IR-003; owner clarification |
| `project-spec-1.9-import-provider-v1` | T2 | CLI / provider runner | No 1.9 `FIX` provider. | One Python provider, operation `fix`, phase `authoring`, effect `mutation-plan`, selected 1.9 templates/registry, closed input/output schemas. | Any undeclared target/action, wrong version/operation, malformed report, or provider/schema failure refuses. | No new operation/effect; one whole-file create/update action bound to declared snapshot; 1.8 unchanged. | SPEC-055C FR-001; payload contract |
| `import-plan-apply-state-v1` | T2 | Existing executor | Scaffold/upgrade apply immediately after planning. | Previewed → applied only after a fresh current plan matches expected digest; otherwise refused. No persisted state. | A mismatch/refusal calls executor zero times; a match calls it once; automatic retry forbidden. | All checks before first write; executor final precondition/staging/cleanup remain authoritative. | SPEC-055C FR-007–FR-009 |

## Appendix B. Requirement-to-Proof Traceability

| Proof ID | Requirement(s) | Task | Method | Oracle | Command / Procedure | Expected Result | Negative Control | Environment | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PV-T1-001 | FR-002–FR-006, FR-008, NFR-001–NFR-003, DR-001–DR-002 | T1 | unit/property/model/schema/provider/executor contract | selected 1.9 registry titles; independent raw byte-range/digest partition; canonical JSON digest; existing closed mutation-plan/executor contracts | `rexec -- uv run pytest tests/test_spec_import.py tests/control_plane/test_schemas.py tests/control_plane/test_providers.py tests/control_plane/test_authoring_executor.py`; run schema generation check and targeted Ruff/BasedPyright | RED identifies only absent conversion/report behavior. GREEN recovers all input bytes once, exact-maps only allowed titles, reviews all ambiguity safely, produces structurally valid deterministic bytes/report/digest, rejects invalid plans, and preserves legacy plan/executor behavior. | Near/case/space/unlisted title, duplicate destination, preamble, embedded fence delimiter, one-byte gap/overlap/duplication, changed report field with unchanged target, raw prose in diagnostics, or unclosed schema object. | Bootstrapped isolated worktree; CPU checks via rexec; no Git dependency | ephemeral |
| PV-T2-001 | FR-001–FR-010, NFR-001–NFR-002, IR-001–IR-003, DR-001–DR-002 | T2 | repeatable isolated CLI/provider regression with deterministic and round-trip checks | CLI interface contract; filesystem snapshots external to mutation path; T1 byte oracle/digest; generic `FIX` binding; executor call counter; existing new/upgrade/adoption behavior | `rexec -- uv run pytest tests/test_spec_import.py tests/test_spec_import_cli.py tests/test_spec_cli.py tests/test_spec_new_cli.py tests/test_spec_upgrade_cli.py tests/control_plane/test_providers.py tests/control_plane/test_authoring_executor.py tests/test_adopt_engine.py`; targeted statics | Preview twice is byte/digest identical and writes nothing; matching apply publishes one structurally valid target through one executor call; all refusal paths call it zero times and preserve source/prior target; JSON/human fields and exit codes are stable; compatibility tests remain green. | Missing output/ID/digest, source=target, wrong/stale digest, snapshot edit, symlink/path escape, staged-write error, second plan/executor call, forced conversion, or `new`/`upgrade` behavior drift. | Bootstrapped isolated worktree and contained temp repositories; CPU checks via rexec | ephemeral |
| PV-T2-002 | FR-001, FR-010, IR-001–IR-003 | T2 | package integrity/graph/projection/reconcile/documentation contract | immutable 1.8 aggregate digest and bytes; 1.9 manifest/schema/provider declarations; standard validators; generated-state convergence; docs/help inventory | Run `tests/package_contract/test_project_spec_1_9.py` and `tests/test_usage_doc_inventory.py`; run five `project-standards standards` validators, reconcile apply/check convergence, scoped Prettier/markdownlint, exact Git diff/predecessor inspection; explicitly inspect absence of full/hosted/release receipts | 1.9 declares one conforming import `FIX` provider and complete docs/schema; all payload/family/catalog/lock/projection digests agree; 1.8 and unrelated state are exact; second reconcile is no-op; no release/gate action occurred. | Stale manifest/resource/family/catalog/lock digest, missing projection entry, changed 1.8 byte, altered 1.9 role/default, undocumented option/exit, manual symlink/generated drift, or `scripts/verify.sh`/hosted/publication receipt. | Bootstrapped isolated worktree; Git/diff local; compatible package/doc CPU checks via rexec | ephemeral |

## Appendix C. Durable Evidence

Not applicable: all acceptance evidence is inexpensive and reproducible from committed source, tests, package manifests, generated state, and identity-bearing task checkpoints.

## Appendix D. Deferred Work

| Item | Reason Deferred | Follow-up / Reopen Trigger |
| --- | --- | --- |
| Additional source-format mapping profiles | Each format needs an approved exact mapping table and fixtures. | A concrete format has both and receives a new approved specification revision. |
| Automatic review resolution | It requires editorial judgment forbidden by the preservation-first contract. | An owner approves a deterministic rule that preserves all source bytes. |
| Release qualification/publication | The v5.19 train deliberately runs one integrated full/hosted gate after every content change. | Umbrella T43 reaches release preparation after this child checkpoint. |
