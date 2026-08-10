---
plan_format: 3
title: 'Python Tooling VS Code Task Prefix Implementation Plan'
slug: 'python-tooling-vscode-task-prefix'
status: active
revision: 1
revises_revision: 0
revision_reason: 'initial plan from issue 153 and the owner-approved closed-prefix design'
pause_reason: ''
source: 'issue L3DigitalNet/project-standards#153; owner decision 2026-08-10; coordinated 5.19 candidate boundary'
spec_ref: ''
created: 2026-08-10
updated: 2026-08-10
owners:
  - 'Project Standards maintainers'
  - 'Coding agents under human review'
---

# Python Tooling VS Code Task Prefix Implementation Plan

> **Definition, not state.** Plan authoring generated no `.project-pipeline` state. During execution, the orchestrator alone generates and mutates ephemeral state under `.project-pipeline/2026-08-10-python-tooling-vscode-task-prefix/execution/`.

## 1. Objective

Produce an unadvertised Python Tooling 1.14 candidate that lets a consumer select the exact "python: " namespace for the five managed VS Code task labels while an omitted or empty `vscode.task_prefix` keeps Python Tooling 1.13 output byte-for-byte. The candidate must express both label sets through static option-gated contributions, document the reserved labels and safe migration, and pair with a generic planner correction so every missing-unit `CP-MODIFIED-MANAGED` finding names an unambiguous governing option without changing central-lock identity or schema.

## 2. Authority and Source Map

| Source | Source Role | Authority / Use | Version / Date | Affected Plan Surface |
| --- | --- | --- | --- | --- |
| `request` | normative | Requires one format-3 plan, an unadvertised successor, no lock-version or scope-key redesign, an explicit #156 gate, adversarial proof, exact validators, and a local release boundary. | 2026-08-10 | §§1, 3, 5–13; T1–T2 |
| `issue:L3DigitalNet/project-standards#153` | normative | Defines the closed prefix option, default compatibility, parallel `when_any` contribution sets, reserved labels, migration note, diagnostic outcome, and ADOPT question. | body and owner comment verified 2026-08-10 | §§1, 3–12; T1–T2 |
| `repo:docs/plans/2026-08-10-schema-payload-reference-validation-plan.md#t2-document-the-successor-cut-guard-and-verify-the-repository` | decision | Supplies the identity-bearing T2/PV-T2-001 checkpoint and clean corpus proof required before any successor payload write. | revision 1, 2026-08-10 | §§3, 7–10; T2 |
| `repo:src/project_standards/control_plane/planner.py::_classify_desired` | current-state evidence | Missing active managed units emit `CP-MODIFIED-MANAGED` with the selected group available but omit `group.governing_options`. | `23c0036f` | §§4–5; T1 |
| `repo:src/project_standards/control_plane/planner.py::_classify_removed` | current-state evidence | Missing de-declared locked units emit the same code while receiving only `LockedUnit`, whose versioned schema deliberately carries no governing-option metadata. | `23c0036f` | §§4–5; T1 |
| `repo:src/project_standards/control_plane/planner.py::_desired_intents` | current-state evidence | Materialization filters inactive declarations before grouping even though the selected payload still carries their option metadata. | `23c0036f` | §§4–5; T1 |
| `repo:src/project_standards/control_plane/diagnostics.py::ControlFinding` | current-state evidence | `governing_options` already has a three-state public model; human and JSON renderers already expose it. | `23c0036f` | §§4–5, 7; T1 |
| `contract:standards/python-tooling/versions/1.13/config.schema.json` | current-state evidence | The closed `vscode` object currently contains only `format_on_save`; resolved nested defaults are the compatibility baseline. | Python Tooling 1.13 | §§4–5; T2 |
| `repo:standards/python-tooling/versions/1.13/payload.toml` | current-state evidence | Five unconditional managed keyed-set contributions use the literal labels as semantic addresses and declare no governing option. | Python Tooling 1.13 | §§4–5; T2 |
| `repo:standards/python-tooling/versions/1.13/providers/python_tooling.py::_task` | current-state evidence | The provider derives the label from the declared scope and uses it as the command-table key. | Python Tooling 1.13 | §§4–5; T2 |
| `repo:tests/package_contract/test_python_tooling_1_13.py` | current-state evidence | Establishes the successor-test pattern, exact predecessor digest control, option-resolution helpers, high-level reconciliation, documentation, and projection assertions. | `23c0036f` | §§7, 9; T2 |
| `adr:docs/adr/adr-0024-catalog-scoped-package-version-channels.md#catalog-channels` | decision | An unadvertised repository payload does not advance release classification; advertisement/default activation and immutable released bytes are separate boundaries. | accepted 2026-07-27; amended 2026-08-09 | §§3, 10–13; T2 |
| `repo:standards/standard-bundle-authoring/README.md#released-version-errata` | normative | Names the five package, graph, schema, projection, and catalog checks required for a successor candidate. | Standard Bundle Authoring 2.6 | §§3, 7, 9, 12; T2 |

Conflict precedence: the direct request narrows issue #153's “new advertised maximum” release classification to an unadvertised 1.14 candidate in this plan. The issue still governs product behavior; a later release workflow may advertise the verified candidate and then classify that release as MINOR. Existing code and tests establish the starting seams only. The selected-declaration design below resolves the issue comment's implementation-time lock-versus-threading choice without versioning the lock.

## 3. Scope, Boundaries, and Constraints

### 3.1 In Scope

- Generic planner enrichment for missing active and missing de-declared managed semantic units, using unambiguous governing-option metadata from the selected payload.
- A complete Python Tooling 1.14 source payload and executable source projection with closed `vscode.task_prefix` values `""` and `"python: "`, default `""`.
- Two static five-contribution sets in 1.14: unprefixed labels active only for `""`, and "python: " labels active only for `"python: "`; every task contribution declares `/vscode/task_prefix` as governing it.
- Provider rendering that accepts only the selected declaration's exact expected label, maps it to the existing base command, and returns one schema-valid task without free-form scope templating.
- Versioned 1.14 standard, agent summary, and adoption guidance naming the five reserved default labels and the verified migration paths.
- Focused engine and package regressions, exact-selected high-level reconciliation, predecessor immutability, unadvertised-candidate proof, and proportional repository qualification.

### 3.2 Out of Scope and Deferred

- No central-lock field, lock schema version, reconciliation-plan schema version, contribution address change, rename primitive, scope interpolation, scope-as-lock-key redesign, free-form prefix, or new adapter behavior.
- No edit to Python Tooling 1.13 or any older payload byte, symlink target, mode, digest, option default, or documentation.
- No `tasks_ownership` escape hatch, arbitrary task renaming, additional VS Code tasks, task command changes, task group changes, or consumer-owned workflow/script redesign.
- No `catalogs/5.toml`, `.standards/config.toml`, `.standards/lock.toml`, family-root activation page, changelog, tool version, release tag, asset, publication, or GitHub lifecycle mutation.
- No execution-state generation during authoring. Workers never edit `.project-pipeline` state directly during implementation.

### 3.3 Ownership and Preserved Behavior

| Boundary | Owner / Responsibility |
| --- | --- |
| T1 owns | Generic planner metadata threading, both missing-unit classification paths, focused diagnostics tests, and one green engine checkpoint. |
| T2 owns | Python Tooling 1.14 source/projection/index/generated-catalog contribution, option-gated tasks/provider/docs, exact-selected migration contract, and final integrated qualification. |
| Depends on | T1's diagnostic contract; #156 plan T2/PV-T2-001 before T2 payload writes; V2 family/projection/catalog generators. |
| Does not own | #156 implementation, package activation/advertisement, release publication, consumer repository edits, or GitHub issue state. |
| Must preserve | 1.13 exact bytes and behavior; omitted-config compatibility; existing five commands and task bodies; diagnostic code/severity/package identity; deterministic planning; consumer-owned unrelated JSONC units. |

### 3.4 Constraints and Authorization

- **EG-001 — successor-payload entry gate:** before T2 writes `standards/python-tooling/versions/1.14/**` or its projection/index/catalog facts, verify the #156 plan is valid and terminal at a commit carrying exactly `Plan-Id: 2026-08-10/schema-payload-reference-validation`, `Plan-Task: T2`, `Plan-Status: done`, and `Plan-Proofs: PV-T2-001`; rerun that proof's graph/corpus acceptance. A missing/mismatched checkpoint or failed proof blocks T2 before payload mutation.
- T1 may proceed before EG-001 because it changes no payload. T2 depends on T1 so the candidate's missing-unit and migration proof exercises the delivered diagnostic behavior, not a hypothetical future fix.
- For removed locked units, metadata comes from selected payload declarations at the same package-owned semantic address. Several applicable declarations contribute detail only when their normalized option-pointer tuples agree; absent or conflicting metadata remains `None` rather than guessing.
- `LockedUnit`, the serialized central lock, and the natural key `(path, adapter, scope)` remain unchanged. The selected package is the resolution authority for how its current declaration can express intent.
- The only sanctioned non-empty prefix in 1.14 is "python: ", derived from issue #153's reported target labels (`python: check`, `python: fix`, and peers). Values with different case, spacing, punctuation, quotes, escapes, control characters, or suffixes are invalid at option resolution.
- Empty/default configuration materializes exactly the existing five unprefixed tasks and no prefixed or duplicate implicit units. It must render the same task bytes as 1.13 for every command-shaping option combination already supported.
- Run `uv run python scripts/family_preflight.py python-tooling` before claiming T2 files; it must still report every applicable declaration site present. After any `src/**` or payload change, rerun `scripts/bootstrap-worktree.sh` rather than reconstructing the candidate-wheel sequence.
- Git/history/index-dependent commands, including `scripts/verify.sh`, run directly in the local checkout. Compatible standalone BasedPyright runs as `rexec -- uv run basedpyright`; Git and package metadata inspection never runs through rexec.

## 4. Current State and Target State

### 4.1 Current State

Python Tooling 1.13 is the Catalog 5 default and this repository's selected self-hosted version. Its resolved `vscode` configuration defaults only `format_on_save`. Five unconditional managed contributions own `.vscode/tasks.json` at `keyed-set:/tasks#label=check`, `fix`, `test`, `typecheck`, and `audit`. The provider parses the label from the scope, looks it up directly in a five-key command map, and emits that literal label.

The planner already enriches value-drift findings with `group.governing_options`. It does not do so when an active desired unit is missing even though `_DesiredGroup` carries the metadata. When configuration de-declares a locked unit, `_classify_removed` sees only `LockedUnit`; the lock correctly records ownership and digests rather than package option metadata. The selected payload still contains inactive declarations, but `_desired_intents` filters them before reconciliation classification.

A clean consumer that switches from unprefixed to prefixed declarations should remove five lock-matching old units and create five new ones. A consumer that already hand-renamed has matching future prefixed units but is also missing the five still-locked unprefixed units, so its plan remains blocked until the old units are restored. The issue's ADOPT question is therefore about the new prefixed copies after restoration, not permission to ignore missing locked units.

### 4.2 Target State

Both missing-managed classification paths populate the existing finding field when the selected declaration supplies one unambiguous tuple. Human and JSON reports continue using the current renderers, package/version identity, error severity, and hint taxonomy. No lock or public schema changes.

Python Tooling 1.14 is complete and source-exact-selectable but unadvertised. Its resolved schema accepts only `""` and `"python: "`; omission resolves to `""`. Static predicates activate exactly one five-task contribution set. `_task` validates the scope against the resolved prefix plus a closed base-label set, maps the base label to the existing command, and emits the full scope identity as the label. Default output is byte-identical to 1.13; opted-in output changes labels only.

Versioned guidance makes `check`, `fix`, `test`, `typecheck`, and `audit` visibly reserved when the default is selected. It explains a clean option switch and the already-renamed recovery: restore the five managed unprefixed units while retaining matching prefixed copies, enable `task_prefix = "python: "`, preview, and reconcile; the old units REMOVE and matching new units ADOPT. If prefixed copies do not exist, the same switch produces CREATE for them.

### 4.3 Delta Summary

| Area | Current | Target | Must Preserve |
| --- | --- | --- | --- |
| Missing-unit diagnostics | Package/version and semantic identity only. | Adds unambiguous selected-declaration governing options for active and de-declared units. | Existing code, severity, message/hint behavior, ordering, and three-state metadata semantics. |
| Configuration | `vscode.format_on_save`; no naming option. | Closed `vscode.task_prefix` values are empty and "python: "; the default is empty. | Old config omission remains valid and resolves to predecessor behavior. |
| Task declarations | One unconditional five-label set. | Two mutually exclusive static five-label sets gated by the option. | Literal semantic addresses; no interpolation or lock-key change. |
| Task provider | Scope label is also the base command key. | Exact selected full label maps to a closed base command key. | Commands, groups, problem matchers, JSON value serialization, and task count. |
| Migration | Manual rename blocks with an unexplained missing-unit error. | Diagnostic names `/vscode/task_prefix`; documented restore-first flow proves REMOVE plus ADOPT/CREATE. | Modified managed units still fail closed; no rename shortcut. |
| Package/release | 1.13 advertised/default/self-selected. | 1.14 complete and unadvertised; 1.13 remains selected. | Released bytes and all activation/publication boundaries. |

## 5. Change Surface and Architecture

### 5.1 Components and Ownership

| Component / Surface | Current Responsibility | Planned Responsibility | Paths / Contracts | Owning Task |
| --- | --- | --- | --- | --- |
| Planner declaration metadata | Active groups alone carry governing options. | Build/read an unambiguous selected-declaration option index for missing active and removed locked scopes. | `planner-missing-managed-governance-v1`; `planner.py` | T1 |
| Finding renderers | Render `governing_options` when populated. | Unchanged; consume the field added at classification. | `ControlFinding`; human/JSON serialization | T1 |
| Python Tooling option schema | Closed `vscode` object with one boolean. | Adds the exact two-value `task_prefix` enum and nested default. | 1.14 `config.schema.json` | T2 |
| Python Tooling task declarations | Five unconditional literal scopes. | Ten literal declarations in two mutually exclusive `when_any` sets, all governed by `/vscode/task_prefix`. | 1.14 `payload.toml` | T2 |
| Python Tooling provider | Five scope labels map directly to commands. | Ten exact full labels resolve through one closed prefix/base-label contract. | 1.14 `_task`; provider schemas unchanged | T2 |
| Documentation/migration | Generic shared-unit guidance only. | Versioned reserved-label warning, configuration example, and verified clean/already-renamed transition. | 1.14 `README.md`, `adopt.md`, `agent-summary.md` | T2 |
| Candidate/index/projection | 1.13 is latest family payload and installed projection. | 1.14 appears in family index, source projection, and generated catalog as unadvertised only. | V2 package contracts | T2 |

### 5.2 Planning and Rendering Flow

```text
selected payload declarations + resolved vscode.task_prefix
        │
        ├─ all declarations ──> unambiguous metadata by owned address ──> missing-unit finding
        │
        └─ materializing declarations
              ├─ ""         ──> five existing literal scopes
              └─ "python: " ──> five prefixed literal scopes
                                      │
                                      ▼
                         provider validates exact full label
                                      │
                                      ▼
                         existing base command + full label
```

### 5.3 Change-Surface Matrix

| Surface | Applies? | Invariant / Required Change | Proof | Task |
| --- | --- | --- | --- | --- |
| Behavior | yes | Missing managed units name the governing option; exact prefix selection changes labels only. | PV-T1-001, PV-T2-001 | T1–T2 |
| Architecture / dependency direction | yes | Planner derives diagnostic metadata from selected package declarations; package provider owns task semantics. | PV-T1-001, PV-T2-001 | T1–T2 |
| Public / cross-task interface | yes | Existing `ControlFinding.governing_options` and contribution schemas are reused without a schema bump. | PV-T1-001 | T1 |
| Data / state | no | No new persistent state; lock shape and natural keys stay unchanged. | PV-T1-001, PV-T2-001 | T1–T2 |
| Configuration | yes | Closed nested enum/default; old omissions resolve identically. | PV-T2-001 | T2 |
| Security / trust | yes | No free-form interpolation; exact enum and exact scope/prefix/base matching reject escaping and label injection. | PV-T2-001 | T2 |
| Compatibility / migration | yes | 1.13 stays exact; clean and already-renamed consumers have deterministic documented transitions. | PV-T2-001 | T2 |
| Operations / deployment | yes | Stop at an unadvertised local checkpoint; separate parent work owns activation and publication. | PV-T2-001 | T2 |
| Documentation | yes | Reserved labels, option syntax, and migration truth live in versioned 1.14 resources. | PV-T2-001 | T2 |
| Durable evidence | no | Committed regressions and identity-bearing checkpoints are inexpensive and reproducible. | PV-T1-001, PV-T2-001 | T1–T2 |

### 5.4 Binding Decisions

| ID | Decision | Rationale | Source | Affected Task(s) |
| --- | --- | --- | --- | --- |
| D-001 | Read missing-unit governing options from the selected payload's declarations; do not persist them in `LockedUnit`. | Diagnostic repair needs current resolution guidance, while the lock remains an ownership/digest record and no versioned-state change is necessary. | request; issue #153 owner decision; planner evidence | T1 |
| D-002 | Publish declaration metadata only when every same-address candidate agrees; otherwise retain `None`. | A misleading option is worse than omitted guidance, and the existing three-state finding contract distinguishes unknown from empty. | existing `_group_desired` degradation rule; direct derivation | T1 |
| D-003 | The complete 1.14 enum contains `""` and `"python: "`. | The issue requires a closed option and reports the desired exact `python: task` palette; one non-empty value keeps declaration growth bounded. | issue #153 reproduction and owner decision | T2 |
| D-004 | Use parallel literal contribution sets gated by `/vscode/task_prefix`; never template a scope. | Literal scope remains contribution identity and the planner already handles de-declaration plus creation. | issue #153 owner decision; payload contract | T2 |
| D-005 | Validate full labels as exactly `prefix + base_label`, then select commands by the closed base label. | This preserves commands while preventing suffix matching, arbitrary prefixes, escaping, and divergence between rendered label and declared identity. | issue #153; adapter identity contract; provider evidence | T2 |
| D-006 | Keep restore-first migration for an already-renamed consumer, while preserving matching prefixed copies for ADOPT. | The old locked units remain missing and must fail closed; after restoration the same plan can REMOVE old units and ADOPT matching new units. | issue #153 ADOPT question; planner classification evidence | T2 |
| D-007 | Finish with 1.14 unadvertised and 1.13 still Catalog/default/self-host selected. | This plan prepares and proves the candidate; advertisement and MINOR release classification belong to the coordinated release boundary. | request; ADR 0024 | T2 |

## 6. Requirements and Acceptance

| ID | Requirement | Source | Priority | Owner Task | Task(s) | Proof(s) |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-001 | Missing active and missing de-declared managed semantic-unit `CP-MODIFIED-MANAGED` findings shall carry the selected declaration's unambiguous `governing_options` tuple. | issue #153 diagnostic scope; request | Must | T1 | T1 | PV-T1-001 |
| REQ-002 | Diagnostic enrichment shall preserve finding code, error severity, owning package/version, semantic identity, ordering, human/JSON rendering, and unknown/empty/ambiguous metadata semantics without changing the lock or public schemas. | issue #153; request; current finding contract | Must | T1 | T1 | PV-T1-001 |
| REQ-003 | Python Tooling 1.14 shall add closed `vscode.task_prefix` values `""` and `"python: "`, default `""`; configurations that omit the field shall resolve and render exactly as 1.13. | issue #153 acceptance; request | Must | T2 | T2 | PV-T2-001 |
| REQ-004 | Exactly one five-task contribution set shall materialize for each valid option value, using literal keyed-set scopes, `/vscode/task_prefix` governance, and provider output whose labels match those scopes while commands and other task fields remain unchanged. | issue #153 owner decision | Must | T2 | T2 | PV-T2-001 |
| REQ-005 | Invalid prefixes and adversarial label/escaping variants shall fail option resolution or exact provider scope validation; no value may create extra, duplicate, partial-match, or implicit prefixed tasks. | request; closed-enum and adapter identity contracts | Must | T2 | T2 | PV-T2-001 |
| REQ-006 | A clean 1.13 lock switching to `"python: "` shall plan five deterministic REMOVE and five CREATE units; unchanged/default reconciliation shall be a fixed point. | issue #153 acceptance; request | Must | T2 | T2 | PV-T2-001 |
| REQ-007 | An already-renamed consumer shall remain blocked while old locked labels are absent, with `/vscode/task_prefix` in the diagnostic; after restoring the old labels, matching prefixed tasks shall ADOPT and old tasks shall REMOVE without duplicate creation. | issue #153 migration and ADOPT verification | Must | T2 | T1, T2 | PV-T1-001, PV-T2-001 |
| REQ-008 | Versioned 1.14 guidance shall reserve `check`, `fix`, `test`, `typecheck`, and `audit` at the empty default and document clean and already-renamed migration procedures matching verified planner behavior. | issue #153 acceptance | Must | T2 | T2 | PV-T2-001 |
| REQ-009 | Python Tooling 1.14 shall be a complete unadvertised candidate after #156 T2/PV-T2-001, while every 1.13 byte/mode/digest and all Catalog 5/default/self-host selections remain unchanged. | request; #156 gate; ADR 0024 | Must | T2 | T2 | PV-T2-001 |

## 7. Verification and Evidence Strategy

- **Authoritative commands:** focused planner/CLI tests; `tests/package_contract/test_python_tooling_1_14.py`; `uv run python scripts/family_preflight.py python-tooling`; `uv run project-standards standards validate-packages --root . --json`; `uv run project-standards standards validate-graph --root . --require-all-manifests --json`; `uv run project-standards standards generate-package-schemas --root . --check`; `uv run project-standards standards sync-payload-projection --root . --check`; `uv run project-standards standards render-catalog --root . --check`; Git-tracked Prettier and markdownlint; Ruff; `rexec -- uv run basedpyright`; direct-local `scripts/verify.sh` after T1 and `scripts/verify.sh --full` after T2.
- **Oracles:** selected `ContributionDeclaration.governing_options`; existing three-state `ControlFinding` serialization; the pinned 1.13 aggregate digest and complete file/mode tree; exact 1.13 provider output; JSONC semantic identity checks; resolved option schema; `ActionKind` unit plans; the #156 checkpoint and corpus proof; unchanged Catalog 5/self-host selections.
- **Negative controls:** a missing active unit; a missing gated-off locked unit; absent, explicitly empty, agreed, and conflicting declaration metadata; default omission; each invalid near-prefix (`python:`, "Python: ", "python - "), quotes/backslashes/newlines/control characters; a scope with a valid suffix but wrong prefix; duplicate or both-set materialization; modified old task content; already-renamed state before and after restoration; predecessor-byte mutation; accidental catalog/default activation.
- **Test layers:** planner unit/regression, human/JSON diagnostics, option-schema resolution, direct provider contract, payload integrity/graph/projection/catalog, exact-selected plan/apply reconciliation, migration/idempotency, predecessor immutability, documentation inspection, Python statics, Markdown gates, and fast/full repository qualification.
- **Correct-reason RED:** T1 tests must fail only because governing options are absent from missing-unit findings. T2 tests must fail first because 1.14 and its option/contributions do not exist, while 1.13 controls pass; implementation starts only after those reasons are observed.
- **External environments:** no network, VS Code process, hosted CI, consumer repository, or GitHub mutation is required. JSONC adapter output and high-level reconciliation are the native behavior oracle.
- **Evidence:** ordinary repeatable outputs are ephemeral. The T1 and T2 commits with valid `Plan-*` trailers are the durable checkpoint trail; no separate evidence artifact is required.
- **Late failure:** block the owning task. If later integration disproves a completed checkpoint, append a correction task with `corrects:` and `discovered_from:`, rerun its proof, and do not rewrite completed definitions or weaken missing-managed enforcement.

## 8. Execution Summary

| Task | Title | Disposition | Work Type | Phase | Depends On | Requirement(s) | Primary Proof | Parallel / Conflict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T1 | Enrich missing-managed diagnostics from selected declarations | active | brownfield-behavior | P1 | None | REQ-001, REQ-002, REQ-007 | PV-T1-001 | no / owns planner classification seam |
| T2 | Cut and verify unadvertised Python Tooling 1.14 | active | brownfield-behavior | P2 | T1 | REQ-003–REQ-009 | PV-T2-001 | no / waits for external EG-001 and owns candidate aggregate |

EG-001 is an external execution precondition, not a local task ID. It binds T2 before any payload write and names the #156 plan's T2/PV-T2-001 checkpoint, distinct from this plan's own T2/PV-T2-001 identity.

## 9. Implementation Tasks

### Phase P1: Generic Diagnostic Checkpoint

#### T1: Enrich missing-managed diagnostics from selected declarations

- **disposition:** active
- **outcome:** Both planner paths that reject a missing managed semantic unit populate the existing governing-option field from unambiguous selected-declaration metadata, with no lock/schema change and no change to enforcement.
- **work_type:** brownfield-behavior
- **checkpoint:** one green engine commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** []
- **dependency_reason:** none
- **requirements:** [REQ-001, REQ-002, REQ-007]
- **proof:** [PV-T1-001]
- **source_refs:** [issue:L3DigitalNet/project-standards#153, repo:src/project_standards/control_plane/planner.py::_desired_intents, repo:src/project_standards/control_plane/planner.py::_classify_desired, repo:src/project_standards/control_plane/planner.py::_classify_removed, repo:src/project_standards/control_plane/diagnostics.py::ControlFinding]
- **consumes:** [selected payload manifests and effective configuration, normalized contribution addresses, current `governing_options` three-state contract, previous `LockedUnit` ownership/digest records]
- **produces:** [planner-missing-managed-governance-v1]
- **preserves:** [central-lock bytes/schema/natural keys, finding code/severity/package/version/identity, existing hint/messages unless a focused wording assertion requires no change, stable sort order, unknown versus explicit-empty semantics, fail-closed missing-managed behavior]
- **invariants:** [current selected declarations are diagnostic authority; inactive declarations are never rendered merely to obtain metadata; a locked unit receives metadata only from the same owner/address; disagreement degrades to unknown; no consumer content beyond existing bounded fields is published]
- **executor_discretion:** [private helper/type names, whether metadata is indexed before or during target rendering, exact fixture organization, and whether one concise cross-file invariant comment is warranted; comments may explain declaration-versus-lock authority but must not narrate syntax]
- **files:** [`src/project_standards/control_plane/planner.py` (modify; owner T1), `tests/control_plane/test_planner.py` (modify; owner T1), `tests/control_plane/test_cli.py` (modify only if needed for focused human/JSON end-to-end rendering; owner T1)]
- **parallel_safe:** no
- **conflicts_with:** [T2]
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** revert the T1 checkpoint if selected-declaration lookup misattributes metadata or changes classification. Never add a lock field, infer from option-name text, render inactive contributions, or suppress `CP-MODIFIED-MANAGED` to recover.
- **acceptance:** PV-T1-001 proves active-missing and de-declared-missing findings carry the exact selected declaration tuple in model, human, and JSON output; absent metadata stays unknown, explicit empty stays `none declared`, conflicting declarations degrade to unknown; finding identity/enforcement/order stay unchanged; central-lock serialization and schema bytes are identical.
- **sub-tasks:**
  - **T1.1 CHARACTERIZE** — capture the active-missing and removed-missing planner paths, current finding/renderer output, selected declaration inventory, and lock serialization baseline. Include a gated declaration whose inactive old scope remains in the selected payload.
  - **T1.2 RED** — add focused tests for an active missing managed unit and an option-declared locked unit missing after de-declaration. Expected failures are `governing_options is None` or the absent human/JSON line while the existing `CP-MODIFIED-MANAGED` finding still appears.
  - **T1.3 Verify RED** — run the focused planner/CLI selection and confirm the failures are the missing metadata, not malformed fixtures, changed classification, missing package identity, or renderer failure.
  - **T1.4 GREEN** — supply the active group tuple directly and make unambiguous selected-declaration metadata available to removed-unit classification by owner/address. Preserve `LockedUnit`; do not materialize inactive providers or change semantic-address comparison.
  - **T1.5 Verify GREEN / REFACTOR** — prove all metadata states and both paths; reduce duplicated indexing only if behavior stays explicit. Audit touched comments and retain only the declaration-authority/ambiguity invariant if it is not recoverable from code.
  - **T1.6 Verify Task** — rerun PV-T1-001; `uv run ruff format --check src tests`; `uv run ruff check src tests`; `rexec -- uv run basedpyright`; `git diff --check`; then `scripts/bootstrap-worktree.sh` and direct-local `scripts/verify.sh`; inspect the diff to confirm no model/schema/lock file changed; create the checkpoint.

### Phase P2: Unadvertised Successor Candidate

#### T2: Cut and verify unadvertised Python Tooling 1.14

- **disposition:** active
- **outcome:** Python Tooling 1.14 is a complete unadvertised candidate whose exact closed prefix selection changes only the five task labels, whose migrations and diagnostics are proven at the real planner boundary, and whose predecessor and active selections remain unchanged.
- **work_type:** brownfield-behavior
- **checkpoint:** one green candidate/integration commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** public
- **depends_on:** [T1]
- **dependency_reason:** consumes `planner-missing-managed-governance-v1` so the candidate's hand-renamed migration proof and documentation describe delivered diagnostic behavior
- **requirements:** [REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-008, REQ-009]
- **proof:** [PV-T2-001]
- **source_refs:** [issue:L3DigitalNet/project-standards#153, repo:docs/plans/2026-08-10-schema-payload-reference-validation-plan.md#t2-document-the-successor-cut-guard-and-verify-the-repository, contract:standards/python-tooling/versions/1.13/config.schema.json, repo:standards/python-tooling/versions/1.13/payload.toml, repo:standards/python-tooling/versions/1.13/providers/python_tooling.py::_task, repo:tests/package_contract/test_python_tooling_1_13.py::_payload, adr:docs/adr/adr-0024-catalog-scoped-package-version-channels.md#catalog-channels]
- **consumes:** [planner-missing-managed-governance-v1, verified EG-001 checkpoint, immutable complete Python Tooling 1.13 payload, V2 family/projection/catalog contracts, existing JSONC adapter and task command contract]
- **produces:** [python-tooling-1.14-task-prefix-v1, unadvertised Python Tooling 1.14 source/projection/catalog contribution, verified migration guidance]
- **preserves:** [all 1.13 bytes/modes/digest, old configuration acceptance, default resolved config/output, five command strings and task non-label fields, unrelated JSONC tasks/settings, lock schema and address identity, Catalog 5/default/self-host selection]
- **invariants:** [exactly one five-task set materializes; scope identity equals rendered label; the only base labels are check/fix/test/typecheck/audit; invalid values fail before provider rendering; option flips remove only lock-matching old units; modified/missing locked units remain errors]
- **executor_discretion:** [unique contribution IDs, private provider helper names, test parametrization layout, exact concise versioned prose around the binding option/reserved/migration facts, and mechanical digest/projection workflow]
- **files:** [`standards/python-tooling/versions/1.14/**` (create; owner T2), `src/project_standards/payloads/python-tooling/1.14/**` (create via projection; owner T2), `standards/python-tooling/standard.toml` (modify; owner T2), `tests/package_contract/test_python_tooling_1_14.py` (create; owner T2), `standards/catalog.md` (modify through renderer; owner T2)]
- **parallel_safe:** no
- **conflicts_with:** [T1]
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** if EG-001 is absent or differs, block before writes. After writes, revert only the unreleased T2 candidate or append a correction task; never edit 1.13, activate 1.14, loosen the enum, add scope templating, bypass missing-managed errors, or change the lock.
- **acceptance:** PV-T2-001 proves EG-001; exact schema values/default and omitted-config compatibility; exact one-set materialization and scope/label identity; unchanged commands/task fields; adversarial rejection; 1.13 byte/mode/digest immutability; default fixed point; five ordered REMOVE plus five CREATE on a clean switch; blocked already-renamed diagnostics naming `/vscode/task_prefix`; REMOVE plus ADOPT after restoration; accurate versioned reserved/migration guidance; complete projection/index/catalog integrity; and 1.14 remains unadvertised while Catalog/default/self-host retain 1.13.
- **sub-tasks:**
  - **T2.1 PRECHECK / CHARACTERIZE** — validate EG-001 and T1 checkpoints; rerun #156 PV-T2-001; run family preflight; capture 1.13's exact aggregate, files, modes, resolved defaults, five task renderings, family index, generated catalog row, and Catalog/self-host selections.
  - **T2.2 RED** — create the focused 1.14 contract before payload bytes. Assert the exact schema, materialization matrix, provider labels/commands, invalid values/scopes, default parity, clean switch, already-renamed states, versioned prose, predecessor digest, projection, and unadvertised selection. Expected failures are the absent 1.14 candidate and missing target behaviors while all 1.13 controls pass.
  - **T2.3 Verify RED** — run only the focused 1.14 contract and confirm failure is not an import/schema-fixture error, stale runtime, predecessor mutation, or absent T1 behavior.
  - **T2.4 GREEN** — copy 1.13 to 1.14 mechanically, update successor identities and manifest-derived schema literals, add the exact option/default, gate the two literal contribution sets, render full labels through exact prefix/base validation, and update only versioned 1.14 documentation. Refresh resource/aggregate digests, projection, family index, and generated unadvertised catalog facts.
  - **T2.5 Verify GREEN** — prove default/omitted byte parity across all five tasks; exact prefixed output; unchanged commands/groups/problem matchers; one-set cardinality; out-of-enum and suffix/escape rejection; deterministic REMOVE/CREATE and restore-then-ADOPT transitions; governing-option diagnostics; unrelated JSONC preservation; and the complete predecessor/unadvertised controls.
  - **T2.6 REFACTOR** — remove duplication only within 1.14 while keeping the literal scopes and independent contribution declarations inspectable. Audit comments against the code-comments contract; retain only the non-obvious scope/label identity invariant and update both declaration/provider ends if commented.
  - **T2.7 Verify Task** — rerun bootstrap; PV-T2-001 and PV-T1-001; Python Tooling 1.13 regressions; family preflight; all five package/graph/schema/projection/catalog checks; Git-tracked Prettier and markdownlint; Ruff; `rexec -- uv run basedpyright`; candidate-runtime `uv run project-standards validate`; `git diff --check`; immutable-predecessor and no-activation diff inspection; then direct-local `scripts/verify.sh --full`; create and validate the checkpoint.

## 10. Integration, Migration, and Recovery

### 10.1 Integration Sequence

1. T1 lands the generic missing-managed diagnostic contract without touching payloads and leaves the engine at a green checkpoint.
2. Verify EG-001 against the external #156 plan and rerun its corpus proof. Only then may T2 create Python Tooling 1.14.
3. T2 proves the candidate directly and through exact-selected reconciliation, refreshes the projection/index/generated catalog, and runs the final full gate.
4. Stop with 1.14 unadvertised. A separate parent release workflow may consume T2's checkpoint, advertise/activate the candidate, perform release-current documentation and reconciliation, classify the release as MINOR, publish, and close #153.

### 10.2 Consumer Configuration Transition

- Required: only for consumers opting into "python: " labels; omitted/empty configuration is a no-op.
- Clean consumer: set `[standards.python-tooling.config.vscode] task_prefix = "python: "`, preview, then apply. Five unchanged locked unprefixed units REMOVE and five absent prefixed units CREATE in deterministic semantic-address order.
- Already-renamed consumer: before enabling, restore the five unprefixed managed units to their lock-matching values while retaining any matching "python: " copies. Then enable, preview, and apply. The old units REMOVE and matching prefixed units ADOPT; absent prefixed units CREATE. Until restoration, missing old units continue to block and name `/vscode/task_prefix`.
- Compatibility period: 1.13 remains advertised/default/self-host selected and immutable while 1.14 is an exact-selected source candidate only.
- Idempotency: the next identical reconcile after either successful transition is NOOP with the same lock and task bytes.
- Point of no return: none in this plan. The candidate is unreleased and activation/publication is external.
- Rollback / forward repair: revert the T2 candidate before downstream consumption, or append a correction task after its checkpoint. A consumer rollback after later activation must select its prior version and reconcile under that future release's documented boundary; this plan performs no live consumer operation.
- Recovery proof: PV-T1-001 covers fail-closed diagnostics; PV-T2-001 covers default fixed point, clean REMOVE/CREATE, restored REMOVE/ADOPT, and modified/missing negative cases.

### 10.3 Late Failure and Correction

A mismatched #156 checkpoint, stale successor schema reference, contribution overlap, provider/scope identity error, ambiguous diagnostic attribution, predecessor-byte difference, accidental activation, or full-gate failure blocks the current task. If authority is unclear, return the smallest amendment request to issue #153 or the #156 plan owner. Otherwise append a permanent correction task with `corrects:` and `discovered_from:`, preserve completed checkpoints, and rerun the failed focused proof plus final integration.

## 11. Risks, Assumptions, and Open Questions

### 11.1 Risks

| ID | Risk | Likelihood | Impact | Treatment | Owner / Task |
| --- | --- | --- | --- | --- | --- |
| R-001 | Inactive-declaration lookup attributes an option from another owner or incompatible declaration. | medium | high | Key by normalized address and owner; require identical tuples; negative-test ambiguity and unknown fallback. | T1 |
| R-002 | Prefix parsing accepts a label by suffix and renders bytes that disagree with its declared identity. | medium | high | Validate exact `resolved_prefix + closed_base_label`, assert all ten scope/label pairs, and reject near-prefix/escape controls. | T2 |
| R-003 | Both contribution sets materialize or neither does because nested defaults/predicate pointers differ. | medium | high | Assert resolved omission/default and exact five-unit cardinality for both values before high-level migration proof. | T2 |
| R-004 | The migration note overstates ADOPT and tells an already-renamed consumer to skip restoration. | medium | high | Prove pre-restoration failure and post-restoration REMOVE/ADOPT separately; make the guide match those observed actions. | T2 |
| R-005 | Mechanical copying leaves stale 1.13 schema identities or accidentally activates the candidate. | medium | high | Block on #156, run its graph proof plus the five validators, and pin Catalog/self-host/family-root negative controls. | T2 |
| R-006 | A broad final gate hides weak task-level option or migration proof. | low | high | Require correct-reason RED and exact action/label/cardinality assertions before package and full gates. | T1–T2 |

### 11.2 Assumptions

| ID | Assumption | Impact if False |
| --- | --- | --- |
| A-001 | #156's final payload-cut gate remains plan `2026-08-10/schema-payload-reference-validation` T2/PV-T2-001. | Pause T2 before writes and revise EG-001 only after the upstream owner records the replacement checkpoint contract. |
| A-002 | The issue's exact `python: check` examples authorize "python: " as 1.14's sole non-empty enum value. | A different sanctioned prefix changes public schema, literal scopes, docs, and proofs; pause T2 and obtain an owner amendment rather than choosing during implementation. |
| A-003 | Selected 1.14 retains inactive unprefixed declarations, so removed-unit metadata can be derived without historical-payload or lock changes. | If the package contract cannot expose them without rendering, stop T1 and request a diagnostic-boundary decision; do not version the lock by default. |

### 11.3 Open Questions

None.

## 12. Final Verification

- Bridge 3.5.0 validates this plan and both identity-bearing task checkpoints; EG-001 was verified before any T2 payload write.
- Every Must requirement maps exactly to completed tasks and passing Appendix B proof; correct-reason RED was observed before each behavior implementation.
- Missing active and removed locked units expose only unambiguous selected-declaration governance while preserving enforcement, package identity, serialization, and lock bytes.
- Python Tooling 1.14 resolves exactly two prefix values, materializes exactly five tasks per value, keeps scope equal to label, rejects adversarial values/scopes, and changes no command or other task field.
- Omitted/default 1.14 output is byte-identical to 1.13; all 1.13 files, modes, and aggregate digest remain exact.
- Exact-selected high-level plans prove default idempotency, five REMOVE plus five CREATE for a clean switch, pre-restoration failure with `/vscode/task_prefix`, and post-restoration REMOVE plus ADOPT without duplicates.
- Versioned 1.14 guidance names all five reserved labels and matches the proven clean/already-renamed procedures.
- The #156 schema guard, family preflight, five package validators, Markdown gates, Ruff, remote BasedPyright, candidate-runtime validation, `git diff --check`, and direct-local full gate pass after the last content change.
- `catalogs/5.toml`, `.standards/config.toml`, `.standards/lock.toml`, family-root activation docs, release metadata, published refs/assets, and GitHub state remain unchanged; 1.14 is unadvertised and 1.13 remains selected.
- No blocker, unapproved deviation, incomplete correction, or orphan generated-catalog change remains.

## 13. Close-out

- **Completed:** record T1 and T2 checkpoint commits and provide T2's validated candidate handoff to the parent 5.19 release workflow.
- **Decisions / deviations harvested:** record only approved changes to the diagnostic metadata boundary, closed enum, migration actions, or candidate activation handoff; do not rewrite completed tasks.
- **Risks closed / accepted:** close R-001 through R-006 from focused and integrated proof or file one bounded follow-up outside activation.
- **Deferred/discovered work filed:** Catalog advertisement/default activation, producer reconcile, release-current docs/changelog/version, publication, consumer rollout, and issue #153 closure stay with the parent release workflow.
- **Source/ADR/handoff reconciliation:** no ADR, Agent Handoff, llm-wiki, or GitHub mutation is part of this child plan. The executor reports the T2 checkpoint through the parent workflow's existing handoff.
- **Scratch teardown:** only the orchestrator may remove execution state after checkpoint identities and concise evidence pointers are committed and the parent handoff is consumable.

## Appendix A. Interface and State Contracts

| Contract | Owner / Producer Task | Consumer(s) | Current | Planned / States | Errors / Limits | Compatibility / Invariant | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `planner-missing-managed-governance-v1` | T1 | planner reports, T2 migration proof, operators | Active value drift can expose governance; missing-unit paths cannot. | Missing active group uses its tuple; missing removed lock matches unambiguous selected declarations by owner/address; human/JSON use existing field. | Absent metadata is unknown; explicit empty is `none declared`; disagreement is unknown; finding remains error. | No lock/model/schema change, no inactive provider execution, no semantic-classification waiver. | issue #153; `_classify_desired`; `_classify_removed` |
| `python-tooling-1.14-task-prefix-v1` | T2 | provider, JSONC adapter, consumers | Five unconditional unprefixed scopes. | `""` selects exact unprefixed scopes; `"python: "` selects exact prefixed scopes; each label equals its scope identity and maps to one existing base command. | All other values fail schema resolution; wrong full label/suffix fails provider validation. | Exactly five tasks; commands/non-label fields and default bytes match 1.13. | issue #153; 1.14 schema/payload/provider |
| Task-prefix transition | T2 | planner/executor, adoption guide | No package-supported rename; manual rename is managed drift. | Clean: five REMOVE + five CREATE. Already renamed: blocked until restoration, then five REMOVE + five ADOPT for matching copies. | Modified/missing old units remain `CP-MODIFIED-MANAGED` with `/vscode/task_prefix`; no rename primitive. | Deterministic, idempotent, unrelated JSONC units preserved. | issue #153; planner `ActionKind` contract |
| Unadvertised Python Tooling candidate | T2 | parent 5.19 release workflow | 1.13 advertised/default/self-host selected. | 1.14 complete in family index/source projection/generated catalog but absent from Catalog 5 selections. | Failed EG-001/package proof or accidental selection blocks handoff. | Released bytes immutable; advertisement and MINOR classification remain external. | ADR 0024; Standard Bundle Authoring 2.6 |

## Appendix B. Requirement-to-Proof Traceability

| Proof ID | Requirement(s) | Task | Method | Oracle | Command / Procedure | Expected Result | Negative Control | Environment | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PV-T1-001 | REQ-001, REQ-002, REQ-007 | T1 | focused planner plus human/JSON diagnostic regression | Selected declaration pointers; existing `ControlFinding` serialization; central-lock before/after bytes | Run focused cases in `tests/control_plane/test_planner.py` and, if used, `tests/control_plane/test_cli.py`; serialize the plan finding and central lock. | Both missing paths report the exact tuple and retain code/severity/package/version/identity/order; absent/empty/ambiguous states render correctly; lock/model/schema bytes and classification remain unchanged. | Omit governance, declare `[]`, give same-address declarations conflicting tuples, use another owner/address, and hand-delete a gated-off locked unit; a hollow “always task_prefix” implementation fails attribution controls. | local isolated planner fixtures | ephemeral |
| PV-T2-001 | REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-008, REQ-009 | T2 | option/provider/package contract plus exact-selected plan/apply transition and repository qualification | Exact enum/default; 1.13 pinned aggregate/tree and renderings; JSONC identity; `ActionKind`; EG-001; unchanged Catalog/self-host selection | Run `tests/package_contract/test_python_tooling_1_14.py`, T1 proof, 1.13 regressions, family preflight, five package validators, Markdown/Ruff, remote BasedPyright, candidate validation, and direct-local full gate after bootstrap. | Exactly five correct tasks per valid value; default bytes equal 1.13; invalid values/scopes fail; clean switch is five REMOVE/five CREATE; already-renamed is blocked then five REMOVE/five ADOPT after restoration; guidance matches; candidate is complete/unadvertised and 1.13 exact/selected. | Near-prefixes, quotes/backslashes/newline/control input, valid suffix under wrong prefix, both/no-set materialization mutation, modified/missing old task, already-renamed pre-restoration, predecessor mutation, stale schema literal, and catalog/self-host activation. | local Git-aware source/candidate runtime after verified external EG-001; BasedPyright via rexec | ephemeral |

## Appendix C. Durable Evidence

No separate evidence record is required: committed focused regressions, immutable predecessor controls, generated package checks, and validated identity-bearing T1/T2 checkpoints make all acceptance results inexpensive and reproducible.

## Appendix D. Deferred Work

| Item | Reason Deferred | Follow-up / Reopen Trigger |
| --- | --- | --- |
| Catalog 5 advertisement/default activation and self-host reconcile | This plan must leave 1.14 unadvertised and 1.13 selected so candidate implementation and release authority remain separate. | Parent 5.19 release workflow consumes the validated T2 checkpoint and explicitly authorizes activation. |
| Release classification, changelog/version, tags/assets, publication, consumer rollout, and issue #153 closure | These are release/lifecycle actions outside this child implementation plan. | Begin only after candidate checkpoint acceptance and the parent release preflight; advertisement makes the release MINOR under ADR 0024. |
| Free-form prefixes or `vscode.tasks_ownership` | Rejected/deferred by the owner decision; either adds scope templating/identity redesign or relinquishes managed updates. | A new issue and owner-approved design explicitly authorize the larger contract. |
