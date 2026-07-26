---
title: 'V5 Adoption Integrity Correction Train Implementation Plan'
slug: 'v5-adoption-integrity-correction-train'
size: full
status: active
source: 'GitHub issues #32 and #35-#49, triaged 2026-07-25'
spec_ref: ''
created: 2026-07-25
updated: 2026-07-25
owners:
  - 'Chris Purcell / L3DigitalNet'
  - 'Coding agent under human review'
test_framework: pytest
---

# V5 Adoption Integrity Correction Train Implementation Plan

> **This file is definition, not state.** It is the proposed implementation contract for owner review. Do not execute T1 or make implementation changes until the owner approves this plan and explicitly grants an exception to the active MCP change hold. Live progress, once authorized, belongs under `.project-pipeline/2026-07-25-v5-adoption-integrity-correction-train/`.

## 1. Objective

Close GitHub issues #32 and #35-#49 in one internally phased correction train that:

- repairs engine-level diagnostics, composition, reconciliation, and recovery behavior;
- publishes immutable successor payloads for Python Tooling, Markdown Tooling, Agent Handoff, and CLI Documentation;
- preserves existing adopters through explicit migrations and unchanged predecessor bytes;
- proves formatter, linter, package, migration, and release fixed points against one exact candidate wheel; and
- stops before implementation, release, or issue closure wherever human authorization is required.

## 2. Approval and Release Gates

1. This plan may be reviewed and edited while the MCP change hold remains active.
2. T1-T17 require both owner approval of this plan and an explicit exception to the MCP hold recorded in the durable handoff.
3. T18 additionally requires explicit release authorization after the complete candidate and Opus audit evidence are available.
4. No task may edit an immutable released payload. Package behavior changes ship only in successor payloads.
5. A newly discovered material requirement, incompatible issue expectation, package-boundary change, new payload, or expanded task change surface returns to this master plan and requires owner re-approval before the affected GREEN step continues. Pure evidence-pointer or wording corrections that do not change scope, behavior, or authorization may be synchronized without reopening approval.
6. The planned train version is Project Standards 5.9.0, subject to `uv run project-standards packages check-release --baseline v5.8.0` confirming MINOR. Any different classification stops before the version bump for owner disposition.

## 3. Scope

### 3.1 In Scope

- Frontmatter directory-argument diagnostics.
- JSON/JSONC composition that preserves a pinned Prettier fixed point.
- Reconciliation atomic failure behavior, pre-adoption conflict guidance, and exact-path managed-file restoration.
- TOML keyed-set handling for valid entries that omit an optional identity key.
- Structured, precise, redacted TOML and Agent Handoff diagnostics.
- Python Tooling configuration extensions, non-installable project mode, and safe performance-test defaults.
- Markdown Tooling exclusion, caller, permission, Prettier, markdownlint, and autofix safety.
- Agent Handoff adoption guidance for independently managed `.agents/` files.
- CLI Documentation valid adoption TOML and an optional multi-CLI usage-index input.
- Release-document/catalog consistency checks and the current Standard Bundle Authoring 2.5 prose correction.
- Immutable successor payloads, migrations, candidate-wheel qualification, Opus audit, and authorized issue/release closeout.

### 3.2 Out of Scope

- Walking a directory passed to `validate-frontmatter`; the supported interface remains file/glob/config driven.
- Silently swallowing pytest exit code 5 when performance tests are explicitly enabled.
- Reformatting unrelated consumer JSON/JSONC content.
- General damaged-file recovery, partial managed-block recovery, or overloading `--repair-state`.
- Automatic detection of every third-party tool that may scan `.agents/`.
- Multiple generated CLI usage artifacts or a generated multi-command CI matrix.
- Adding Hypothesis solely for this train; existing parametrization and generated fixtures supply property-style coverage.
- MCP implementation, publication without explicit authorization, or drive-by work outside the listed issues.

### 3.3 Compatibility Rules

- Python Tooling 1.8, Markdown Tooling 1.8, Agent Handoff 1.4, and CLI Documentation 1.3 remain byte-identical.
- Fresh successor adopters receive corrected defaults.
- Existing Python Tooling 1.8 adopters migrating to 1.9 receive an explicit `ci.performance = true` value so migration preserves their effective behavior.
- Omitted successor-only options render no extra configuration, preserving the predecessor default projection except for deliberately corrected defaults.
- Existing consumer-owned content and valid unkeyed TOML entries remain preserved.

## 4. Source Requirements

These plan-local requirements are derived from the live issue bodies and comments captured on 2026-07-25. T1 refreshes the threads before RED so later comments cannot be silently ignored.

| ID | Requirement | Source | Priority | Task(s) |
| --- | --- | --- | --- | --- |
| REQ-001 | Reject a directory positional with a supported-interface diagnostic, not “no such file”. | #32 | must | T2 |
| REQ-002 | Preserve Prettier-clean JSON and JSONC as Prettier-clean after semantic composition without rewriting unrelated content. | #35 | must | T1, T3 |
| REQ-003 | Bind release-facing version/default prose to the exact candidate catalog and commit. | #36 | must | T14, T17 |
| REQ-004 | Tell pre-adoption whole-file conflicts when delete/recreate is safe and who owns the replacement. | #37 | must | T7 |
| REQ-005 | Provide explicit preview/apply recovery for one exclusively managed whole-file target with lock/current/desired digest preconditions. | #37 | must | T7 |
| REQ-006 | Render `permissions: contents: read` in both Markdown Tooling managed caller workflows. | #38 | must | T10 |
| REQ-007 | Preserve unrelated TOML array entries that validly omit an optional keyed-set identity. | #39 | must | T4 |
| REQ-008 | Add closed additive Ruff `extend-include`, `extend-select`, and `extend-ignore` options and coverage `omit`. | #40 | must | T8 |
| REQ-009 | Support a non-installable Python repository by omitting `[build-system]` while retaining development tooling. | #41 | must | T8 |
| REQ-010 | Support an optional repository-relative, consumer-owned multi-CLI usage index without multiplying generated CLI artifacts. | #42 | must | T13 |
| REQ-011 | Document locked `.agents/` files that independent Python/Markdown tooling should exclude. | #43 | must | T12 |
| REQ-012 | Make Markdown table/directive guidance converge under Prettier and markdownlint; remove unsafe autofix from the normal recipe. | #44 | must | T11 |
| REQ-013 | Report Agent Handoff line/locus, observed measure, and allowed limit without exposing sensitive content. | #45 | must | T5 |
| REQ-014 | Make every adoption-guide TOML example parse and report TOML line/column diagnostics safely. | #46 | must | T5, T13 |
| REQ-015 | Make configured Markdown exclusions select the same intended effective file set for lint and format after pinned-tool characterization. | #47 | must | T1, T9 |
| REQ-016 | Render Prettier-stable caller YAML for long globs/exclusions and fail nonzero without partial mutation when planning has error findings. | #48 | must | T6, T10 |
| REQ-017 | Make fresh Python Tooling performance CI opt-in while preserving migrated 1.8 behavior explicitly. | #49 | must | T8 |
| REQ-018 | Use one pinned Prettier/markdownlint oracle and explicit fixed-point invariants across affected tasks. | Opus review | must | T1, T3, T9-T11 |
| REQ-019 | Use one diagnostic redaction contract: structural location and bounded measures are allowed; raw scalar values and consumer content are not. | Opus review | must | T5 |
| REQ-020 | Keep error-bearing reconcile apply atomic and distinct from the managed-file restore feature. | Opus review | must | T6, T7 |
| REQ-021 | Ship changes through immutable successor payloads and activate them only after package/migration validation. | release contract | must | T8-T15 |
| REQ-022 | Preserve released payload bytes and prior exact-version pass/fail behavior. | release contract | must | T8-T13, T15, T17 |
| REQ-023 | Qualify one extracted candidate wheel through source, package, graph, migration, coherence, docs, audit, and performance gates. | repository policy | must | T17 |
| REQ-024 | Treat unresolved Critical/High Opus findings as blockers, not advisory notes. | owner instruction | must | T16-T18 |
| REQ-025 | Publish, close issues, and update hosted evidence only after explicit release authorization. | owner/release contract | must | T18 |

## 5. Architecture and Expected Change Surface

| Area | Expected paths | Contract |
| --- | --- | --- |
| Frontmatter CLI | `src/project_standards/validate_frontmatter.py`, frontmatter tests | Directory positional is a distinct unsupported-input diagnostic. |
| Structured adapters | `src/project_standards/control_plane/adapters/jsonc.py`, `toml.py`, adapter tests | Preserve semantic ownership and unrelated bytes while satisfying declared fixed points. |
| Reconcile planning/execution | `src/project_standards/control_plane/{planner,executor,cli}.py`, tests | Error findings block all apply; restore is exact, explicit, and preconditioned. |
| Diagnostics | `src/project_standards/control_plane/codec.py`, `src/project_standards/agent_handoff/`, tests | Structured locations and bounded measures under a shared redaction rule. |
| Python Tooling successor | `standards/python-tooling/versions/1.9/`, family manifest, schemas, providers, migration/tests | Additive configuration, non-installable mode, corrected fresh default, behavior-preserving migration. |
| Markdown Tooling successor | `standards/markdown-tooling/versions/1.9/`, family manifest, providers, docs/tests | Pinned-tool file-set and fixed-point convergence. |
| Agent Handoff successor | `standards/agent-handoff/versions/1.5/`, family manifest, docs/tests | Clear independent-tool exclusion ownership. |
| CLI Documentation successor | `standards/cli-docs/versions/1.4/`, family manifest, schema/docs/tests | Valid TOML and optional referenced usage index. |
| Release consistency | release/package validation source and tests; `README.md`, `UPGRADING.md` | Candidate commit, catalog, defaults, and prose agree before tag. |
| Projection and release | `.standards/config.toml`, catalog/projection artifacts, changelog/status/handoff | Successors activate together only after all earlier tasks pass. |

## 6. Test Strategy

- Use pytest test names `test_unit__condition__expected_result`, with the three segments replaced by specific behavior terms, for new tests.
- Each bug fix begins with a focused regression that fails against the current code for the intended reason.
- T1 derives exact Prettier and markdownlint-cli2 versions from the repository lockfile (currently 3.8.3 and 0.23.1), verifies the installed executables match, and then supplies shared subprocess oracles pinned to those derived versions.
- Property-style coverage uses parametrized generated cases for JSON/JSONC whitespace and insertion positions, exclusion forms, TOML keyed entries, digest mismatches, and config option combinations. A new property-testing dependency requires separate owner approval.
- Fixed-point invariant: if an owned input is clean under the applicable pinned formatter before composition, the composed output is clean under the same formatter; semantic parsing and unrelated consumer values are preserved.
- Atomicity invariant: an error-bearing reconciliation plan produces no filesystem mutation and a nonzero result, regardless of `--apply`.
- Restore invariant: preview is non-mutating; apply succeeds only for one exact exclusively managed whole-file target whose current/lock/desired digests still match the preview preconditions.
- Migration invariant: migrating a current exact payload preserves effective prior behavior unless the issue explicitly requires a corrected migration outcome.

### 6.1 TDD Exceptions

| Task | Exception reason | Objective validation |
| --- | --- | --- |
| T16 | Independent adversarial review is evidence, not production behavior. | Complete candidate bundle, recorded Opus verdict, and no unresolved Critical/High finding. |
| T17 | Candidate qualification and handoff preparation integrate already-tested behavior. | One wheel digest and the complete repository gate against its extracted bytes. |
| T18 | Publication and tracker mutation are external release operations. | Explicit authorization, signed tag/release, hosted workflow and downloaded-asset parity, issue closure evidence. |

## 7. Execution Summary

| Task | Title | Phase | Depends on | Requirements |
| --- | --- | --- | --- | --- |
| T1 | Refresh issue corpus and build pinned formatting oracles | P1 | None | REQ-002, REQ-015, REQ-018 |
| T2 | Correct directory positional diagnostics | P1 | T1 | REQ-001 |
| T3 | Preserve JSON/JSONC formatter fixed points | P1 | T1 | REQ-002, REQ-018 |
| T4 | Preserve valid optional-identity TOML entries | P1 | T1 | REQ-007 |
| T5 | Add precise redacted structural diagnostics | P1 | T1 | REQ-013, REQ-014, REQ-019 |
| T6 | Make error-bearing reconcile apply atomic | P1 | T1 | REQ-016, REQ-020 |
| T7 | Add whole-file conflict guidance and exact restore | P1 | T6 | REQ-004, REQ-005, REQ-020 |
| T8 | Build Python Tooling 1.9 | P2 | T1 | REQ-008, REQ-009, REQ-017, REQ-021, REQ-022 |
| T9 | Converge Markdown exclusion file sets | P2 | T1 | REQ-015, REQ-018, REQ-021, REQ-022 |
| T10 | Stabilize Markdown callers and permissions | P2 | T1, T6, T9 | REQ-006, REQ-016, REQ-018, REQ-021, REQ-022 |
| T11 | Converge Markdown lint/format safety | P2 | T1, T9 | REQ-012, REQ-018, REQ-021, REQ-022 |
| T12 | Build Agent Handoff 1.5 adoption boundary | P2 | T5 | REQ-011, REQ-021, REQ-022 |
| T13 | Build CLI Documentation 1.4 | P2 | T5 | REQ-010, REQ-014, REQ-021, REQ-022 |
| T14 | Add candidate-bound release consistency | P3 | T8-T13 | REQ-003, REQ-021 |
| T15 | Activate successors and prove migrations | P3 | T2-T14 | REQ-021, REQ-022 |
| T16 | Run blocking Opus candidate audit | P3 | T15 | REQ-024 |
| T17 | Qualify one candidate wheel and prepare handoff | P3 | T16 | REQ-003, REQ-022, REQ-023, REQ-024 |
| T18 | Publish and close issues after authorization | P4 | T17 | REQ-024, REQ-025 |

## 8. Implementation Tasks

### Phase P1: Engine Integrity

#### T1: Refresh issue corpus and build pinned formatting oracles

- **goal:** Freeze current issue acceptance and establish one reusable pinned Prettier/markdownlint truth surface. · **phase:** P1 · **depends_on:** [] · **requirements:** [REQ-002, REQ-015, REQ-018] · **priority:** must
- **files:** issue evidence under `.project-pipeline/` (ephemeral), shared coherence/oracle fixtures under `tests/`
- **acceptance:** every open issue body/comment is rechecked and mapped without changing GitHub; the exact branch/commit and relevant pre-train Python/Node suites are green in their authoritative environments before RED; installed formatter/linter versions equal lockfile authority; JSON, JSONC, Markdown, YAML, and exclusion probes execute those pinned tools and expose normalized exit/result data (TC-T1-001, TC-T1-002).
- **sub-tasks:**
  - **T1.0 CHARACTERIZE** — refresh #32 and #35-#49 read-only; record the exact branch/commit; derive tool versions from the lockfile and verify installed versions; build/extract one clean current-release baseline wheel and put it first on `PYTHONPATH` for installed-distribution-dependent tests; run source-authoritative unit tests against source and installed-authoritative adoption/package tests against that wheel; run the relevant frontmatter, adapter, control-plane, package, coherence, and Node suites before RED; and run minimal reproductions for #35, #44, #47, and #48. Planning evidence on 2026-07-25 showed the two cited legacy-adopt tests fail only against source symlink projections and pass 2/2 against an extracted 5.8.0 wheel; T1 must reproduce rather than assume that result. Any other baseline failure blocks RED until it is proven environmental or added as discovered in-scope work under §2.5; do not hide it with a new expected-failure marker.
  - **T1.1 RED** — add oracle contract tests, including distinct JSON and JSONC parser/formatter probes and effective-file-set probes.
  - **T1.2 Verify RED** — confirm the shared oracle abstraction is absent while direct pinned commands reproduce the fixtures.
  - **T1.3 GREEN** — add the smallest reusable test helper/fixtures; do not add a production formatter dependency.
  - **T1.4 Verify GREEN** — run the oracle tests on clean/dirty JSON, JSONC, Markdown table/directive, caller YAML, and exclusion cases.
  - **T1.5 REFACTOR** — centralize subprocess construction, stable diagnostics, and fixture IDs.
  - **T1.6 Verify Task** — run the shared oracle tests, Ruff, BasedPyright, and `npm ci`; commit with requirement/test IDs.

#### T2: Correct directory positional diagnostics

- **goal:** Distinguish an existing directory from a missing file without adding directory walking. · **phase:** P1 · **depends_on:** [T1] · **requirements:** [REQ-001] · **priority:** must
- **files:** `src/project_standards/validate_frontmatter.py`, `tests/test_validate_frontmatter.py`
- **acceptance:** a directory positional exits with the config-error contract and points to config/glob/file usage; a missing path retains “no such file”; files and configured globs are unchanged (TC-T2-001).
- **sub-tasks:**
  - **T2.1 RED** — add distinct directory, missing-path, file, and configured-glob regression cases.
  - **T2.2 Verify RED** — prove only the directory case has the misleading current diagnostic.
  - **T2.3 GREEN** — classify directory inputs before the missing-file branch and emit the supported-interface guidance.
  - **T2.4 Verify GREEN** — run targeted CLI/collector tests.
  - **T2.5 REFACTOR** — keep path classification single-pass and preserve current exception types.
  - **T2.6 Verify Task** — run the frontmatter suite, Ruff, and BasedPyright; commit with IDs.

#### T3: Preserve JSON/JSONC formatter fixed points

- **goal:** Make semantic JSON-family composition context-aware enough to preserve clean formatting without reserializing unrelated values. · **phase:** P1 · **depends_on:** [T1] · **requirements:** [REQ-002, REQ-018] · **priority:** must
- **files:** `src/project_standards/control_plane/adapters/jsonc.py` (the shared JSON/JSONC adapter), adapter/planner/coherence tests
- **acceptance:** Prettier-clean JSON and JSONC stay clean after every supported semantic insertion/replacement; parsing succeeds under the appropriate parser; existing keys/comments/values outside owned units are byte-preserved where the adapter contract promises preservation (TC-T3-001, TC-T3-002).
- **sub-tasks:**
  - **T3.0 CHARACTERIZE** — confirm the shared adapter/parser boundaries, then enumerate root/nested, empty/nonempty, first/middle/last, compact/expanded, CRLF, and JSONC-comment insertion contexts.
  - **T3.1 RED** — add parametrized fixed-point, semantic-equivalence, and unrelated-byte-preservation regressions through the shared oracle.
  - **T3.2 Verify RED** — confirm failures reproduce #35 and are not caused by invalid fixtures or a mismatched parser.
  - **T3.3 GREEN** — derive inserted fragment layout from the containing clean context while retaining lexical splicing.
  - **T3.4 Verify GREEN** — run adapter, planner, and pinned Prettier cases for JSON and JSONC separately.
  - **T3.5 REFACTOR** — isolate context/layout inference from ownership and splice semantics.
  - **T3.6 Verify Task** — run JSON-family adapter/planner/coherence tests, Ruff, and BasedPyright; commit with IDs.

#### T4: Preserve valid optional-identity TOML entries

- **goal:** Match keyed TOML array entries without rejecting unrelated valid entries that omit the optional identity field. · **phase:** P1 · **depends_on:** [T1] · **requirements:** [REQ-007] · **priority:** must
- **files:** `src/project_standards/control_plane/adapters/toml.py`, TOML adapter/planner tests
- **acceptance:** entries lacking `matcher` are preserved and ignored for matcher-keyed lookup; the matching entry is managed; non-table elements and duplicate matching identities remain hard failures (TC-T4-001, TC-T4-002).
- **sub-tasks:**
  - **T4.1 RED** — add mixed keyed/unkeyed, duplicate keyed, wrong-type, and round-trip preservation cases.
  - **T4.2 Verify RED** — confirm the valid mixed case alone fails under the current all-entries-keyed assumption.
  - **T4.3 GREEN** — index only entries carrying the selected identity while validating structural hazards.
  - **T4.4 Verify GREEN** — run TOML adapter and Agent Handoff hook reconciliation cases.
  - **T4.5 REFACTOR** — share keyed lookup without weakening duplicate/type detection.
  - **T4.6 Verify Task** — run TOML/control-plane regressions, Ruff, and BasedPyright; commit with IDs.

#### T5: Add precise redacted structural diagnostics

- **goal:** Add actionable locations and measures to TOML and Agent Handoff diagnostics under one no-content-leak contract. · **phase:** P1 · **depends_on:** [T1] · **requirements:** [REQ-013, REQ-014, REQ-019] · **priority:** must
- **files:** `src/project_standards/control_plane/codec.py`, `src/project_standards/agent_handoff/`, CLI/provider/model tests
- **acceptance:** TOML parse errors include safe line/column; handoff findings include root-relative path, structural locus, line when known, observed measure, and limit; JSON/text renderings agree; secret-like scalar values and raw consumer lines never appear (TC-T5-001, TC-T5-002, TC-T5-003).
- **sub-tasks:**
  - **T5.0 CHARACTERIZE** — inventory diagnostic construction/rendering and classify safe structural fields versus forbidden content.
  - **T5.1 RED** — add exact location/measure/schema and adversarial secret-redaction regressions.
  - **T5.2 Verify RED** — prove current diagnostics omit required structure and that fixtures would detect content leakage.
  - **T5.3 GREEN** — extend typed finding/parse diagnostics and renderers with optional safe fields; chain original parse failures.
  - **T5.4 Verify GREEN** — run codec, handoff policy/link, provider, JSON, and text CLI cases.
  - **T5.5 REFACTOR** — centralize bounded diagnostic projection and eliminate duplicated message parsing.
  - **T5.6 Verify Task** — run control-plane and Agent Handoff suites, Ruff, and BasedPyright; commit with IDs.

#### T6: Make error-bearing reconcile apply atomic

- **goal:** Ensure planning errors prevent every mutation and return nonzero even when `--apply` is requested. · **phase:** P1 · **depends_on:** [T1] · **requirements:** [REQ-016, REQ-020] · **priority:** must
- **files:** `src/project_standards/control_plane/{cli,planner,executor}.py`, reconciliation tests
- **acceptance:** for ordinary reconcile `--apply`, any error-severity finding blocks the complete plan before executor entry, leaves a filesystem snapshot unchanged, and exits nonzero in text and JSON modes; warning-only conflict-free plans retain current behavior. This ordinary-apply gate does not prevent the separately selected T7 `--restore-managed PATH --apply` recovery mode from handling its own exact preconditions (TC-T6-001, TC-T6-002).
- **sub-tasks:**
  - **T6.1 RED** — add mixed valid-mutation plus error-finding fixtures and before/after tree assertions.
  - **T6.2 Verify RED** — reproduce partial apply/false success without involving restore behavior.
  - **T6.3 GREEN** — add one pre-execution applicability/error gate and stable nonzero result.
  - **T6.4 Verify GREEN** — run CLI/planner/executor transaction and rollback regressions.
  - **T6.5 REFACTOR** — keep applicability and severity decisions in one typed boundary.
  - **T6.6 Verify Task** — run reconciliation suites, Ruff, and BasedPyright; commit with IDs.

#### T7: Add whole-file conflict guidance and exact restore

- **goal:** Make safe pre-adoption recovery explicit without turning reconciliation into general file repair. · **phase:** P1 · **depends_on:** [T6] · **requirements:** [REQ-004, REQ-005, REQ-020] · **priority:** must
- **files:** control-plane planner/CLI/executor/models, recovery tests, CLI docs
- **interface/data:** add restore mode with grammar `reconcile --restore-managed PATH [--apply]`. Without `--apply`, it is a non-mutating preview; within restore mode, `--apply` is the explicit confirmation modifier, not ordinary reconcile apply. Restore mode cannot combine with `--check`, `--repair-state`, `--allow-major`, or an ordinary unqualified apply request. `PATH` must resolve to one declared, exclusively managed, whole-file target with an existing authoritative lock entry; it never accepts a glob or directory. Preview returns target, owner identity, current state as either an exact digest or `absent`, lock digest, desired digest, action (`overwrite`, `recreate`, or `noop`), and exact apply command. `noop` applies when current and desired digests already match and never writes. An existing divergent current file may differ from the lock digest: explicit restore is allowed to overwrite that drift only after preview, and the preview must say so without disclosing its bytes. A missing current file may be recreated only when the lock still proves exclusive ownership. Apply atomically requires the current state still equals the preview digest or remains absent, the lock and desired digests still match, and the regular-file/absence, containment, and ownership conditions still hold. The apply result records the superseded current digest or `absent` plus the resulting digest, never superseded content. An absent lock, a newly appeared file after an `absent` preview, or any changed digest fails closed.
- **acceptance:** conflict hints distinguish safe manual delete/reconcile for pre-adoption targets from consumer-owned/manual cases; pre-adoption targets without a lock cannot use restore mode; restore preview is non-mutating; explicit apply overwrites a previewed divergent exclusively managed file or recreates a previewed absent locked file and touches only the requested target; a current-equals-desired preview/apply reports `noop` and performs no write; stale current/absent state, stale lock/desired digest, symlink, partial-block, shared/consumer-owned, absent lock, glob, and directory inputs fail closed (TC-T7-001, TC-T7-002, TC-T7-003).
- **sub-tasks:**
  - **T7.1 RED** — add pre-adoption conflict-guidance plus divergent-current overwrite, absent-current recreate, preview/apply, and every digest/state/ownership/security rejection case.
  - **T7.2 Verify RED** — confirm current behavior lacks the interface and current generic conflict hint cannot satisfy the ownership cases.
  - **T7.3 GREEN** — add explicit target resolution, preview model, digest preconditions, and executor path using existing atomic write safety.
  - **T7.4 Verify GREEN** — run recovery, reconciliation, symlink, transaction, text, and JSON cases.
  - **T7.5 REFACTOR** — share existing digest/containment primitives; keep restore separate from incomplete-state repair.
  - **T7.6 Verify Task** — run complete control-plane recovery/executor/CLI suites, Ruff, and BasedPyright; commit with IDs.

### Phase P2: Immutable Successor Packages

#### T8: Build Python Tooling 1.9

- **goal:** Add requested closed configuration, non-installable mode, and safe fresh performance defaults with migration preservation. · **phase:** P2 · **depends_on:** [T1] · **requirements:** [REQ-008, REQ-009, REQ-017, REQ-021, REQ-022] · **priority:** must
- **files:** new `standards/python-tooling/versions/1.9/`, family manifest/provider/schema/migration/tests
- **interface/data:** add empty-default lists for Ruff `extend_include`, `extend_select`, `extend_ignore`, and coverage `omit`; add `build_backend = "none"`; make fresh 1.9 `ci.performance = false`; make 1.8-to-1.9 migration materialize explicit `ci.performance = true`. Explicit true with no performance tests continues to expose pytest exit 5.
- **acceptance:** option combinations render canonical native tables; empty options omit bytes; backend none omits only `[build-system]`; fresh default omits performance CI; migration preserves prior effective true; predecessor payload bytes remain unchanged (TC-T8-001 through TC-T8-004).
- **sub-tasks:**
  - **T8.0 CHARACTERIZE** — pin 1.8 defaults, bytes, provider output, and migration mechanics.
  - **T8.1 RED** — add schema/provider/fresh-adoption/migration/package regressions for every option and combination.
  - **T8.2 Verify RED** — confirm tests target absent 1.9 behavior while 1.8 characterization stays green.
  - **T8.3 GREEN** — create the immutable 1.9 payload/provider/schema and explicit preservation migration.
  - **T8.4 Verify GREEN** — run Python Tooling package/provider/migration and pinned TOML checks.
  - **T8.5 REFACTOR** — derive rendered lists/defaults from typed config and avoid parallel ownership.
  - **T8.6 Verify Task** — run package tests, graph/schema/projection checks, Ruff, and BasedPyright; commit with IDs.

#### T9: Converge Markdown exclusion file sets

- **goal:** Make configured exclusions express the same intended files for lint and format without assuming the reported normalization before reproducing it. · **phase:** P2 · **depends_on:** [T1] · **requirements:** [REQ-015, REQ-018, REQ-021, REQ-022] · **priority:** must
- **files:** new Markdown Tooling 1.9 provider/schema/docs/tests
- **acceptance:** pinned effective-file-set cases cover `dir`, `dir/`, `dir/**`, nested files, negation if supported, and platform separators; any format-only normalization is narrowly derived from confirmed pinned behavior while the original config remains lint authority; Markdown Tooling 1.8 bytes remain unchanged (TC-T9-001, TC-T9-002).
- **sub-tasks:**
  - **T9.0 CHARACTERIZE** — reproduce #47 with repository-pinned tools and record the minimal divergent syntax.
  - **T9.1 RED** — add effective-file-set parity and rendered-ignore regressions for the confirmed domain.
  - **T9.2 Verify RED** — prove the failure is tool interpretation, not shell expansion or test working-directory drift.
  - **T9.3 GREEN** — create Markdown Tooling 1.9 and implement the narrowest format materialization confirmed by characterization; if no divergence reproduces, carry the 1.8 exclusion rendering into 1.9 unchanged and add the characterization guard rather than speculative normalization.
  - **T9.4 Verify GREEN** — compare actual lint/format selected files and pinned exit results.
  - **T9.5 REFACTOR** — centralize exclusion projection while keeping tool-specific semantics explicit.
  - **T9.6 Verify Task** — run Markdown provider/oracle/package tests and schema/graph checks; commit with IDs.

#### T10: Stabilize Markdown callers and permissions

- **goal:** Render long caller inputs as Prettier-stable YAML and grant the minimum reusable-workflow read permission. · **phase:** P2 · **depends_on:** [T1, T6, T9] · **requirements:** [REQ-006, REQ-016, REQ-018, REQ-021, REQ-022] · **priority:** must
- **files:** Markdown Tooling 1.9 caller provider/templates/tests
- **acceptance:** both managed callers render exact job-level or workflow-level `contents: read` consistent with the called workflows; long globs/exclusions use stable block scalars; reconcile apply reaches a clean fixed point and any formatter/planner error remains atomic; Markdown Tooling 1.8 bytes remain unchanged (TC-T10-001, TC-T10-002).
- **sub-tasks:**
  - **T10.1 RED** — add caller snapshots, pinned Prettier checks, permissions assertions, and reconcile fixed-point cases.
  - **T10.2 Verify RED** — reproduce scalar wrapping and managed-byte drift on the current caller.
  - **T10.3 GREEN** — render canonical block scalars and exact read permissions in both caller families.
  - **T10.4 Verify GREEN** — run provider, workflow schema, Prettier, and repeated reconcile cases.
  - **T10.5 REFACTOR** — share caller input rendering without widening workflow permissions.
  - **T10.6 Verify Task** — run Markdown package/coherence/control-plane tests and Node gates; commit with IDs.

#### T11: Converge Markdown lint/format safety

- **goal:** Remove the markdownlint/Prettier table conflict and keep autofix out of the normal adoption path. · **phase:** P2 · **depends_on:** [T1, T9] · **requirements:** [REQ-012, REQ-018, REQ-021, REQ-022] · **priority:** must
- **files:** Markdown Tooling 1.9 lint config, README/adopt guidance, examples/tests
- **interface/data:** disable MD060 because Prettier owns table layout; teach block `markdownlint-disable`/`markdownlint-enable` around exceptional regions; normal verification runs lint without `--fix`; an explicit optional autofix recipe must require diff review and a follow-up Prettier/lint pass.
- **acceptance:** Prettier plus markdownlint reaches a fixed point for tables/directives; `disable-next-line` is not recommended for multi-node blocks; underscores survive the normal recipe; every documented command is executable; Markdown Tooling 1.8 bytes remain unchanged (TC-T11-001, TC-T11-002).
- **sub-tasks:**
  - **T11.1 RED** — add table/directive/underscore fixed-point fixtures and documentation-command assertions.
  - **T11.2 Verify RED** — reproduce the current MD060/directive/autofix conflict with pinned tools.
  - **T11.3 GREEN** — create 1.9 lint config and revise adoption/reference/example guidance.
  - **T11.4 Verify GREEN** — run Prettier then lint repeatedly and execute normal/optional recipes on fixtures.
  - **T11.5 REFACTOR** — keep one formatting authority and one structural authority with no overlapping table rule.
  - **T11.6 Verify Task** — run Markdown package/coherence/docs tests and Node gates; commit with IDs.

#### T12: Build Agent Handoff 1.5 adoption boundary

- **goal:** Document which locked Agent Handoff implementation files independent repository tooling must exclude. · **phase:** P2 · **depends_on:** [T5] · **requirements:** [REQ-011, REQ-021, REQ-022] · **priority:** must
- **files:** new `standards/agent-handoff/versions/1.5/`, adoption/reference/manifest/tests
- **acceptance:** guidance names locked `.agents/skills/agent-handoff/**` and `.agents/hooks/session_start.py`, explains why consumer formatters/type checkers do not own them, and provides Python/Markdown exclusion examples aligned with current package defaults; Agent Handoff 1.4 bytes remain unchanged (TC-T12-001).
- **sub-tasks:**
  - **T12.1 RED** — add documentation-contract and package-resource tests for the missing exclusion guidance.
  - **T12.2 Verify RED** — confirm 1.4 lacks the contract and no engine detection is required.
  - **T12.3 GREEN** — create 1.5 from 1.4 with only the adoption-boundary and compatible diagnostic documentation updates.
  - **T12.4 Verify GREEN** — run package, docs, and cross-package adoption checks.
  - **T12.5 REFACTOR** — keep ownership rationale in one referenced section and examples copyable.
  - **T12.6 Verify Task** — run Agent Handoff package/provider/docs gates; commit with IDs.

#### T13: Build CLI Documentation 1.4

- **goal:** Make adoption TOML valid and add one optional referenced multi-CLI usage index. · **phase:** P2 · **depends_on:** [T5] · **requirements:** [REQ-010, REQ-014, REQ-021, REQ-022] · **priority:** must
- **files:** new `standards/cli-docs/versions/1.4/`, schema/provider/docs/examples/tests; adoption-TOML sweep tests
- **interface/data:** remove invalid `null` assignments from copyable TOML. Add optional `usage_index_path`, a contained repository-relative Markdown input that is consumer-owned and referenced by the managed usage surface. Default single-CLI generation is unchanged. Switching to the custom input does not delete the old create-only artifact.
- **acceptance:** every TOML fence classified as copyable parses; absent custom path is byte-compatible with 1.3 behavior; valid custom index is referenced; missing/escaping/non-file paths fail clearly; multiple generated usage artifacts remain unsupported; CLI Documentation 1.3 bytes remain unchanged (TC-T13-001, TC-T13-002).
- **stop/backtrack:** if the repository-wide TOML sweep finds an invalid fence outside CLI Documentation 1.4—including in a released predecessor or another planned successor—do not edit a released payload or expand this task implicitly. Route the correction to the owning successor task, add or reopen work in this master plan under §2.5, and obtain owner re-approval before the affected GREEN step.
- **sub-tasks:**
  - **T13.0 CHARACTERIZE** — inventory all adoption-guide TOML fences and 1.3 create-only artifact behavior.
  - **T13.1 RED** — add corpus TOML parsing, schema/path/security, default parity, custom-index, and transition preservation tests.
  - **T13.2 Verify RED** — prove current `null` and absent custom-index contract cause the intended failures.
  - **T13.3 GREEN** — create 1.4 schema/provider/docs and correct every invalid copyable TOML fence.
  - **T13.4 Verify GREEN** — run CLI Docs package/provider/adoption and TOML corpus tests.
  - **T13.5 REFACTOR** — reuse extension/path containment primitives and retain one generated usage surface.
  - **T13.6 Verify Task** — run package/graph/schema/projection/docs gates; commit with IDs.

### Phase P3: Integration and Candidate

#### T14: Add candidate-bound release consistency

- **goal:** Prepare the planned 5.9.0 metadata and prevent a release tag whose README/UPGRADING/default-package claims do not match its exact candidate catalog. · **phase:** P3 · **depends_on:** [T8, T9, T10, T11, T12, T13] · **requirements:** [REQ-003, REQ-021] · **priority:** must
- **files:** project version/release metadata, release validation source/tests/workflow as needed, `README.md`, `UPGRADING.md`
- **acceptance:** `uv run project-standards packages check-release --baseline v5.8.0` confirms MINOR before the 5.9.0 bump; the gate then fails on stale project version, package version/default rows, install commands, or current-package links at the candidate commit; it validates the exact checked-out commit after the bump and before tag; README’s current Standard Bundle Authoring reference is corrected from 2.4 to 2.5 (TC-T14-001, TC-T14-002).
- **sub-tasks:**
  - **T14.1 RED** — add fixture commits/documents with each independent stale field and a current-repo regression.
  - **T14.2 Verify RED** — prove the current checker misses the historical #36 mismatch and current 2.4 prose.
  - **T14.3 GREEN** — after confirming MINOR classification, bump planned project metadata to 5.9.0, derive expected release-facing facts from that candidate metadata/catalog, and add the pre-tag gate.
  - **T14.4 Verify GREEN** — run passing current-candidate and failing stale-fixture cases.
  - **T14.5 REFACTOR** — centralize release-fact extraction and keep historical immutable docs out of current-candidate assertions.
  - **T14.6 Verify Task** — run release/package/docs tests, workflow syntax, Ruff, and BasedPyright; commit with IDs.

#### T15: Activate successors and prove migrations

- **goal:** Select the four successors together and prove package graph, projection, adoption, and migration compatibility. · **phase:** P3 · **depends_on:** [T2, T3, T4, T5, T6, T7, T8, T9, T10, T11, T12, T13, T14] · **requirements:** [REQ-021, REQ-022] · **priority:** must
- **files:** family manifests, `.standards/config.toml`, catalog/projection artifacts, `README.md`, `UPGRADING.md`, cross-package/migration/coherence tests, changelog draft
- **acceptance:** defaults select Python Tooling 1.9, Markdown Tooling 1.9, Agent Handoff 1.5, and CLI Documentation 1.4; README/UPGRADING current-default rows and links are updated to those exact selections and pass the T14 gate; every predecessor digest is unchanged; fresh and migration matrices converge; repeated reconcile is clean (TC-T15-001, TC-T15-002).
- **sub-tasks:**
  - **T15.1 RED** — add exact default-selection, predecessor-digest, fresh-adoption, all-predecessor migration, and repeated-reconcile matrix cases.
  - **T15.2 Verify RED** — confirm successor payloads pass alone but are not yet activated/projected.
  - **T15.3 GREEN** — activate exact successors, regenerate schemas/catalog/projection, and add the unreleased changelog entries.
  - **T15.4 Verify GREEN** — run package, graph, schema, projection, migration, adoption, and coherence matrices.
  - **T15.5 REFACTOR** — remove duplicate fixtures and derive all version cases from manifests/catalog authority.
  - **T15.6 Verify Task** — run all package/control-plane/coherence/docs/static gates; commit with IDs.

#### T16: Run blocking Opus candidate audit

- **goal:** Adversarially review the complete implementation against issues, plan, invariants, immutable-byte evidence, and candidate diff. · **phase:** P3 · **depends_on:** [T15] · **requirements:** [REQ-024] · **priority:** must
- **files:** ignored review bundle/evidence; master-plan discovered tasks if required
- **acceptance:** Opus receives a bounded read-only evidence bundle and returns a requirement-by-requirement verdict; every Critical/High finding is fixed through a plan task and re-reviewed or explicitly dispositioned by the owner (TC-T16-001).
- **sub-tasks:**
  - **T16.1 RED** — assemble the exact diff, issue corpus, plan matrix, test output, payload digests, and known-risk register; mark the audit gate unsatisfied.
  - **T16.2 Verify RED** — verify the bundle is complete, contains no secrets, and points to the exact candidate commit.
  - **T16.3 GREEN** — run one substantive Claude Opus adversarial review; add discovered work to this plan and return to the earliest owning task as needed.
  - **T16.4 Verify GREEN** — rerun review after fixes until no unresolved Critical/High finding remains.
  - **T16.5 REFACTOR** — collapse duplicate evidence while preserving exact commands/commit/digests and minority concerns.
  - **T16.6 Verify Task** — validate the final audit disposition table and commit only durable plan/changelog/handoff consequences.

#### T17: Qualify one candidate wheel and prepare handoff

- **goal:** Prove the exact candidate bytes locally and prepare, but do not publish, release/handoff evidence. · **phase:** P3 · **depends_on:** [T16] · **requirements:** [REQ-003, REQ-022, REQ-023, REQ-024] · **priority:** must
- **files:** release notes/changelog/status/handoff and ephemeral gate logs
- **acceptance:** one wheel digest supplies all package/control-plane/coherence tests with extracted bytes first on `PYTHONPATH`; full static/test/performance/audit/docs gates pass; release consistency and Opus gates pass at the exact commit; state says “candidate ready, unpublished” (TC-T17-001, TC-T17-002).
- **sub-tasks:**
  - **T17.1 RED** — create the candidate checklist with every §11 command and mark missing evidence as failure.
  - **T17.2 Verify RED** — confirm no stale build directory or source checkout can satisfy installed-candidate checks.
  - **T17.3 GREEN** — build/extract one wheel, run the full gate, and prepare release/handoff documents without tagging or publishing.
  - **T17.4 Verify GREEN** — repeat release consistency, payload digests, plan validation, and handoff conformance at the final commit.
  - **T17.5 REFACTOR** — remove transient build output from tracked scope and consolidate evidence pointers.
  - **T17.6 Verify Task** — prove clean worktree, exact local commit, candidate digest, complete green gate, and unpublished state; stop for authorization.

### Phase P4: Authorized Release

#### T18: Publish and close issues after authorization

- **goal:** Release the verified correction train and close only issues proven by hosted/artifact evidence. · **phase:** P4 · **depends_on:** [T17] · **requirements:** [REQ-024, REQ-025] · **priority:** must
- **files:** final release publication metadata plus status/deployed/handoff/session records; no new version bump
- **preconditions:** explicit owner release authorization naming this candidate; no unresolved Critical/High Opus finding; T17 exact commit and wheel digest unchanged.
- **acceptance:** signed tag/release and hosted workflows are green; downloaded release artifact matches the qualified digest/content; main/testing/tag parity follows release policy; #32 and #35-#49 each receive exact closing evidence and are closed only if its acceptance is proven (TC-T18-001, TC-T18-002).
- **sub-tasks:**
  - **T18.1 RED** — verify authorization and candidate identity; any absence or mismatch is a hard stop.
  - **T18.2 Verify RED** — confirm release/issue operations cannot begin from an unauthorized or changed candidate.
  - **T18.3 GREEN** — execute the repository release contract, monitor hosted workflows, verify downloaded artifacts, and close proven issues with concise evidence.
  - **T18.4 Verify GREEN** — prove tag, release, artifact, workflows, issue states, and required branch parity.
  - **T18.5 REFACTOR** — reconcile final changelog/status/deployed/handoff truth without altering released bytes.
  - **T18.6 Verify Task** — run final handoff/docs checks, commit/push authorized closeout, prove clean worktree and remote parity, then close the master plan.

## 9. Integration, Risks, and Decisions

### 9.1 Integration Sequence

1. Establish shared external-tool oracles, then fix independent engine defects.
2. Build each immutable successor from its released predecessor.
3. Add the candidate-bound release gate.
4. Activate successors together and run cross-package migration/coherence matrices.
5. Obtain a blocking Opus audit.
6. Qualify one exact candidate wheel and stop for release authorization.

### 9.2 Risks

| ID | Risk | Impact | Mitigation | Owner |
| --- | --- | --- | --- | --- |
| R-001 | #47 does not reproduce under pinned tools. | med | T9 characterizes actual selected files and adds a guard; no speculative normalization. | T9 |
| R-002 | Context-aware JSON formatting rewrites consumer bytes. | high | Lexical splice remains authoritative; property-style preservation cases bound the change. | T3 |
| R-003 | Restore becomes an unsafe generic repair path. | high | Exact declared target, exclusive whole-file ownership, preview, digests, containment, and mutual exclusion. | T7 |
| R-004 | Fresh performance default changes migrated behavior. | high | Migration materializes explicit true; explicit true retains pytest exit 5. | T8 |
| R-005 | Diagnostic precision leaks consumer secrets. | high | Shared structural redaction schema and adversarial secret fixtures. | T5 |
| R-006 | Release docs drift after candidate validation. | high | Gate runs at exact final candidate commit immediately before tag and again in T17/T18. | T14, T17, T18 |
| R-007 | Correction train conflicts with the MCP hold. | high | No T1 execution without explicit owner exception; release has a second authorization gate. | Owner |

### 9.3 Decisions

| ID | Decision | Rationale |
| --- | --- | --- |
| D-001 | Use one correction train with internal phases. | Shared formatter, control-plane, package, and release invariants need one candidate proof surface. |
| D-002 | Do not author a separate specification. | The issue corpus defines bounded corrections; this master plan carries explicit REQ and interface contracts without inventing a new product surface. |
| D-003 | Do not swallow pytest exit 5. | Explicit performance enablement should still fail when the declared suite is absent; only the fresh default changes. |
| D-004 | Keep restore separate from `--repair-state`. | Whole-file managed-byte recovery and incomplete control-plane recovery have different authorities and preconditions. |
| D-005 | Disable MD060 in the successor. | Prettier owns physical table layout; markdownlint retains structural rules without an overlapping layout authority. |
| D-006 | Support a referenced usage index, not multiple generated CLIs. | It addresses multi-CLI navigation while preserving one managed artifact contract and consumer ownership. |

## 10. Open Questions

| ID | Question | Blocking? | Owner | Current assumption |
| --- | --- | --- | --- | --- |
| OQ-001 | Does the owner approve this plan and grant an exception to the MCP hold? | yes before T1 | Owner | No; implementation remains blocked pending morning review. |
| OQ-002 | Does refreshed pinned-tool evidence confirm #47’s exact `dir/**` divergence? | yes at T9 GREEN | Implementer | Characterize first; do not pre-commit to normalization. |
| OQ-003 | Does the owner authorize the exact T17 candidate for release? | yes before T18 | Owner | No; T17 stops unpublished. |

## 11. Final Verification

- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run basedpyright`
- `CORRECTION_WHEEL_OUT="$(mktemp -d)"`
- `CORRECTION_WHEEL_RUNTIME="$(mktemp -d)"`
- `uv build --wheel --out-dir "$CORRECTION_WHEEL_OUT"`
- Record `sha256sum "$CORRECTION_WHEEL_OUT"/project_standards-*.whl`.
- `python -m zipfile -e "$CORRECTION_WHEEL_OUT"/project_standards-*.whl "$CORRECTION_WHEEL_RUNTIME"`
- `export PYTHONPATH="$CORRECTION_WHEEL_RUNTIME${PYTHONPATH:+:$PYTHONPATH}"`; keep this binding for every remaining package/control-plane/coherence/handoff check.
- `uv run coverage erase`
- `uv run coverage run --source=project_standards -m pytest -m "not performance and not compatibility"`
- `uv run pytest -m compatibility -n 4 --dist load --max-worker-restart=0`
- `uv run pytest -m performance`
- `uv run coverage report`
- `uv run pip-audit`
- `uv run project-standards standards validate-packages --root . --json`
- `uv run project-standards standards validate-graph --root . --require-all-manifests --json`
- `uv run project-standards standards generate-package-schemas --root . --check`
- `uv run project-standards standards sync-payload-projection --root . --check`
- `npm ci`
- `uv run pytest tests/coherence -v`
- `npm run format:check`
- `npx markdownlint-cli2`
- `uv run project-standards validate`
- `uv run scripts/plan.py validate docs/plans/2026-07-25-v5-adoption-integrity-correction-train-plan.md`
- `uv run project-standards agent-handoff validate --repo .`
- `uv run project-standards agent-handoff drift-check --repo .`
- `uv run project-standards agent-handoff size-report --repo .`
- `uv run project-standards agent-handoff shape-check --repo .`
- `git diff --check`
- Audit every REQ and TC row against exact passing evidence; any missing Must evidence blocks T17.
- Confirm predecessor payload digests match the pre-train baseline and no released payload path changed.
- Confirm the final candidate is unpublished and issue states are unchanged before requesting T18 authorization.

## 12. Close-out

- **Completed:** _pending_
- **Final commit and candidate wheel digest:** _pending_
- **Opus verdict and dispositions:** _pending_
- **Release authorization:** _pending_
- **Hosted/artifact/issue evidence:** _pending_

Teardown after authorized T18: harvest durable decisions into this section and handoff artifacts, set `status: complete`, validate/commit/push the closeout, prove remote parity and clean state, then remove `.project-pipeline/2026-07-25-v5-adoption-integrity-correction-train/`.

## Appendix A. Interface and Schema Changes

| Interface/model | Current | Planned | Compatibility |
| --- | --- | --- | --- |
| Frontmatter positional | file or misleading directory failure | file plus explicit unsupported-directory diagnostic | Existing file/glob behavior unchanged. |
| Reconcile apply | may continue around error findings | error findings block all mutation and return nonzero | Safer failure semantics. |
| Managed restore | absent | exact `--restore-managed PATH` preview/apply | Additive, explicit, fail-closed. |
| Finding/parse diagnostic | message-heavy | optional structural line/column/locus/measure/limit | Additive fields; renderers remain compatible. |
| Python Tooling config | 1.8 closed schema | 1.9 additive options, backend none, fresh performance false | 1.8 immutable; migration preserves true. |
| Markdown Tooling config | 1.8 | 1.9 convergent file-set/caller/lint contract | 1.8 immutable. |
| Agent Handoff package | 1.4 | 1.5 exclusion/adoption guidance | 1.4 immutable. |
| CLI Documentation config | 1.3 single generated usage | 1.4 optional referenced usage index | Default remains single generated usage. |
| Release consistency | incomplete prose checks | exact candidate metadata/catalog/prose gate | Additive pre-tag failure gate. |

## Appendix B. Test Matrix

| Test ID | Requirement | Task | Exact target/evidence | Type |
| --- | --- | --- | --- | --- |
| TC-T1-001 | REQ-018 | T1 | Shared pinned Prettier/markdownlint oracle contract tests | contract |
| TC-T1-002 | REQ-002, REQ-015 | T1 | Issue refresh plus minimal JSON/Markdown/exclusion/caller reproductions | characterization |
| TC-T2-001 | REQ-001 | T2 | Directory/missing/file/configured-glob frontmatter CLI cases | regression |
| TC-T3-001 | REQ-002, REQ-018 | T3 | Parametrized JSON/JSONC composition-to-Prettier fixed point | property/regression |
| TC-T3-002 | REQ-002 | T3 | Semantic and unrelated-byte preservation across splice contexts | property/security |
| TC-T4-001 | REQ-007 | T4 | Mixed keyed/unkeyed TOML array preservation | regression |
| TC-T4-002 | REQ-007 | T4 | Duplicate matching identity and non-table rejection | contract |
| TC-T5-001 | REQ-014, REQ-019 | T5 | TOML line/column and secret-redaction cases | regression/security |
| TC-T5-002 | REQ-013, REQ-019 | T5 | Handoff line/locus/measure/limit schema and rendering | contract |
| TC-T5-003 | REQ-019 | T5 | Adversarial raw-value/content non-disclosure corpus | security |
| TC-T6-001 | REQ-016, REQ-020 | T6 | Error plan plus `--apply` returns nonzero with unchanged tree | regression/security |
| TC-T6-002 | REQ-020 | T6 | Warning-only conflict-free apply retains current transaction behavior | compatibility |
| TC-T7-001 | REQ-004 | T7 | Ownership-sensitive pre-adoption conflict hints | regression |
| TC-T7-002 | REQ-005 | T7 | Divergent-current overwrite, absent-current recreate, and current-equals-desired no-op preview/apply, then repeated clean reconcile | integration |
| TC-T7-003 | REQ-005, REQ-020 | T7 | Changed current/absent state, stale lock/desired digest, absent lock, path/ownership/symlink/glob/directory rejection | security |
| TC-T8-001 | REQ-008 | T8 | Ruff/coverage option schema and canonical render combinations | contract |
| TC-T8-002 | REQ-009 | T8 | Backend none omits build-system and retains dev tooling | regression |
| TC-T8-003 | REQ-017 | T8 | Fresh default false, explicit true exit-5 behavior | integration |
| TC-T8-004 | REQ-017, REQ-022 | T8 | 1.8-to-1.9 migration materializes true; 1.8 bytes unchanged | migration |
| TC-T9-001 | REQ-015, REQ-018 | T9 | Pinned effective lint/format file-set matrix | integration |
| TC-T9-002 | REQ-015, REQ-022 | T9 | Narrow normalization or no-divergence characterization guard plus Markdown Tooling 1.8 digest | contract |
| TC-T10-001 | REQ-006 | T10 | Both caller permissions and reusable workflow compatibility | contract |
| TC-T10-002 | REQ-016, REQ-018, REQ-022 | T10 | Long caller inputs pass Prettier and repeated reconcile; Markdown Tooling 1.8 digest unchanged | regression |
| TC-T11-001 | REQ-012, REQ-018 | T11 | Table/directive/underscore repeated Prettier-plus-lint fixed point | regression |
| TC-T11-002 | REQ-012, REQ-022 | T11 | Executable normal and guarded optional autofix documentation; Markdown Tooling 1.8 digest unchanged | documentation |
| TC-T12-001 | REQ-011, REQ-022 | T12 | Locked-file independent-tool exclusion contract and Agent Handoff 1.4 digest | documentation |
| TC-T13-001 | REQ-014 | T13 | All classified copyable adoption TOML fences parse | corpus |
| TC-T13-002 | REQ-010, REQ-022 | T13 | Optional usage-index default/path/transition/security matrix and CLI Documentation 1.3 digest | contract |
| TC-T14-001 | REQ-003 | T14 | Stale project/package/default/link fixture failures | release |
| TC-T14-002 | REQ-003, REQ-021 | T14 | Exact candidate prose/catalog pass and SBA 2.5 regression | release |
| TC-T15-001 | REQ-021 | T15 | Four-successor default, fresh adoption, and migration matrix | integration |
| TC-T15-002 | REQ-022 | T15 | Predecessor digest ledger and repeated reconcile | compatibility |
| TC-T16-001 | REQ-024 | T16 | Exact-commit Opus review and Critical/High disposition table | adversarial review |
| TC-T17-001 | REQ-023 | T17 | One extracted-wheel complete local gate and digest | release candidate |
| TC-T17-002 | REQ-003, REQ-022, REQ-024 | T17 | Candidate consistency, immutable bytes, Opus, handoff, unpublished checks | audit |
| TC-T18-001 | REQ-025 | T18 | Explicit authorization, signed tag/release, hosted workflows, artifact parity | release |
| TC-T18-002 | REQ-024, REQ-025 | T18 | Per-issue closing evidence, no unresolved Critical/High finding, and required branch parity | closeout |

## Appendix C. Deferred Work

| Item | Reason deferred | Follow-up trigger |
| --- | --- | --- |
| Directory walking for frontmatter validation | Not required to fix #32 and changes selection semantics. | Separate approved feature request. |
| General damaged managed-file recovery | Exact whole-file recovery is the safe bounded issue scope. | Separate recovery specification with ownership/precondition model. |
| Hypothesis dependency | Existing generated parametrization is sufficient for this correction train. | Owner-approved testing dependency proposal. |
| Generated multi-CLI artifacts/CI | #42 can be satisfied by a referenced consumer-owned index. | Concrete need for multiple generated artifact identities. |
| Automatic third-party `.agents/` exclusion detection | Documentation plus current Python Tooling defaults address #43. | Evidence that a managed provider can safely own another tool’s config. |
