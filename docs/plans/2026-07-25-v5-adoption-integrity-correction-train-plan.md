---
title: 'V5 Adoption Integrity Correction Train Implementation Plan'
slug: 'v5-adoption-integrity-correction-train'
size: full
status: active
source: 'SPEC-VAIC, GitHub issues #32 and #35-#49, and the 2026-07-26 closed-issue regression audit'
spec_ref: 'docs/specs/2026-07-26-v5-adoption-integrity-correction-train-spec.md'
created: 2026-07-25
updated: 2026-07-26
owners:
  - 'Chris Purcell / L3DigitalNet'
  - 'Coding agent under human review'
test_framework: pytest
---

# V5 Adoption Integrity Correction Train Implementation Plan

> **This file is definition, not state.** The owner approved the original implementation contract for T1-T17 on 2026-07-26, selected SPEC-VAIC rev 0.4 Option 1, and authorized autonomous convergence through the rev 0.5-rev 0.7 review corrections and appended T19. T19 may not enter GREEN until this amendment and its independent reviews converge. Live progress belongs under `.project-pipeline/2026-07-25-v5-adoption-integrity-correction-train/`. T18 remains blocked on separate authorization for the exact qualified candidate.

## 1. Objective

Close GitHub issues #32 and #35-#49 in one internally phased correction train that:

- repairs engine-level diagnostics, composition, reconciliation, and recovery behavior;
- publishes immutable successor payloads for Python Tooling, Markdown Tooling, Agent Handoff, and CLI Documentation;
- preserves existing adopters through explicit migrations, one generic direct-edge package-configuration transform, and unchanged predecessor bytes;
- proves formatter, linter, package, migration, and release fixed points against one exact candidate wheel; and
- stops before implementation, release, or issue closure wherever human authorization is required.

## 2. Approval and Release Gates

1. This plan may be reviewed and edited while the MCP change hold remains active.
2. The durable 2026-07-26 closed-issue regression audit establishes SPEC-VAIC's pre-authorization `baseline_verified` state. T1 is the first authorized implementation task: it converts that proof into a committed ledger and reruns it before any current-train RED work.
3. The owner approved SPEC-VAIC rev 0.4 Option 1 and authorized autonomous convergence of the bounded T19 amendment, including rev 0.5-rev 0.7 review corrections, on 2026-07-26. T19 GREEN requires passing amended spec/plan validation and converged independent reviews; all prior T1-T17 authorization remains unchanged.
4. T18 additionally requires explicit release authorization after the complete candidate and Opus audit evidence are available.
5. No task may edit an immutable released payload. Package behavior changes ship only in successor payloads.
6. A newly discovered material requirement, incompatible issue expectation, package-boundary change, new payload, or expanded task change surface returns first to SPEC-VAIC and then to this master plan; both artifacts require renewed review and owner approval before the affected GREEN step continues. Pure evidence-pointer or wording corrections that do not change scope, behavior, or authorization may be synchronized without reopening approval.
7. The planned train version is Project Standards 5.9.0, subject to pre-GREEN analysis and exact-candidate `uv run project-standards packages check-release --baseline v5.8.0` evidence confirming MINOR. Any different classification or pass-to-fail consumer outcome stops before affected GREEN work or candidate assembly for owner disposition.
8. T15 assembles the exact release commit, including version, `uv.lock`, dated changelog, and release-current documentation bytes. T16 reviews it; T17 rebuilds and qualifies it without tracked changes; T18 may land it on `main` only by a tree-preserving fast-forward or equivalent unchanged-commit operation. Any byte or commit substitution restarts T15-T17 and requires renewed release authorization.
9. Every implementation task must pass the scope-verification checkpoints in §6.1. Optional cleanup, speculative hardening, generalized infrastructure, and unrelated maintenance are prohibited even when adjacent to an edited surface.

## 3. Scope

### 3.1 In Scope

- Frontmatter directory-argument diagnostics.
- JSON/JSONC composition that preserves a pinned Prettier fixed point.
- Reconciliation atomic failure behavior, pre-adoption conflict guidance, and exact-path managed-file restoration.
- TOML keyed-set handling for valid entries that omit an optional identity key.
- Structured, precise, redacted TOML and Agent Handoff diagnostics.
- Python Tooling configuration extensions, non-installable project mode, and safe performance-test defaults.
- One explicit, generic package-configuration transform contract for direct automatic package upgrades, instantiated only by Python Tooling predecessor-to-1.9 edges in this train.
- Markdown Tooling exclusion, caller, permission, Prettier, markdownlint, and autofix safety.
- Agent Handoff adoption guidance for independently managed `.agents/` files.
- CLI Documentation valid adoption TOML and an optional multi-CLI usage-index input.
- Release-document/catalog consistency checks and the current Standard Bundle Authoring 2.5 prose correction.
- Immutable successor payloads, migrations, candidate-wheel qualification, Opus audit, and authorized issue/release closeout.

### 3.2 Out of Scope

- Walking a directory passed to `format-frontmatter` or another explicit-path frontmatter command; the supported interface remains file/glob/config driven.
- Silently swallowing pytest exit code 5 when performance tests are explicitly enabled.
- Reformatting unrelated consumer JSON/JSONC content.
- General damaged-file recovery, partial managed-block recovery, or overloading `--repair-state`.
- Automatic detection of every third-party tool that may scan `.agents/`.
- Multiple generated CLI usage artifacts or a generated multi-command CI matrix.
- Adding Hypothesis solely for this train; existing parametrization and generated fixtures supply property-style coverage.
- Remediating the development-only `markdownlint-cli2` to `js-yaml` advisory chain or changing Node dependency pins solely for that advisory (SPEC-VAIC C-006).
- Package-ID-specific engine logic, implicit historical-provider execution, an arbitrary patch/expression language, multi-hop transforms, composition of multiple transforms in one plan, a new upgrade CLI, or multi-file transaction redesign.
- MCP implementation, publication without explicit authorization, or drive-by work outside the listed issues.

### 3.3 Compatibility Rules

- Python Tooling 1.8, Markdown Tooling 1.8, Agent Handoff 1.4, and CLI Documentation 1.3 remain byte-identical.
- Fresh successor adopters receive corrected defaults.
- Every qualifying family-indexed Python Tooling predecessor whose schema declares `ci.performance` with default true has a direct opted-in edge to 1.9; enabled CI materializes the prior effective value, disabled CI materializes false, and explicit true/false remains unchanged. Family-indexed versions that default it false or do not declare it receive no FR-017 edge.
- The transform changes only declared `/ci/performance`; its introduced leaf is valid under both predecessor and 1.9 schemas, the complete result is 1.9-valid, the provider is idempotent, and unrelated target defaults are never materialized.
- Successor-only options added in the same desired-config change remain available to target validation and do not have to validate against the predecessor schema.
- Omitted successor-only options render no extra configuration, preserving the predecessor default projection except for deliberately corrected defaults.
- Existing consumer-owned content and valid unkeyed TOML entries remain preserved.
- Exact-version and `version = "latest"` consumers that pass under 5.8.0 remain passing after migration to the candidate.
- Neither the pinned lint-selected nor format-selected corpus may widen for an existing consumer without owner disposition under SPEC-VAIC AW-004.

## 4. Governing Requirements and Traceability

SPEC-VAIC is the requirement authority. This plan uses its IDs directly; it does not create a parallel requirement namespace. T1 refreshes the live issue threads before RED, but any material change returns to the specification before the plan changes.

| Spec requirement | Issue/source | Owning task(s) | Planned evidence |
| --- | --- | --- | --- |
| FR-001 | #32 | T2 | TC-T2-001 |
| FR-002 | #35 | T1, T3 | TC-T1-002, TC-T3-001, TC-T3-002 |
| FR-003 | #36 | T14, T17 | TC-T14-001, TC-T14-002, TC-T17-002 |
| FR-004 | #37 | T7 | TC-T7-001 |
| FR-005 | #37 | T7 | TC-T7-002, TC-T7-003 |
| FR-006 | #38 | T10 | TC-T10-001 |
| FR-007 | #39 | T4 | TC-T4-001, TC-T4-002 |
| FR-008 | #40 | T8 | TC-T8-001 |
| FR-009 | #41 | T8 | TC-T8-002 |
| FR-010 | #42 | T13 | TC-T13-002 |
| FR-011 | #43 | T12 | TC-T12-001 |
| FR-012 | #44 | T11, T15 | TC-T11-001, TC-T11-002, TC-T11-003, TC-T15-001 |
| FR-013 | #45 | T5 | TC-T5-002, TC-T5-003 |
| FR-014 | #46 | T13 | TC-T13-001 |
| FR-015 | #47 | T1, T9, T15 | TC-T1-002, TC-T9-001, TC-T9-002, TC-T15-003 |
| FR-016 | #48 | T10 | TC-T10-002 |
| FR-017 | #49 | T8, T19 | TC-T8-003, TC-T8-004, TC-T19-001, TC-T19-002, TC-T19-003 |
| FR-018 | #46 | T5 | TC-T5-001, TC-T5-003 |
| FR-019 | Release/package contract | T8-T15, T19 | TC-T8-004, TC-T9-002, TC-T10-002, TC-T11-002, TC-T12-001, TC-T13-002, TC-T14-002, TC-T15-001, TC-T15-002, TC-T19-003 |
| FR-020 | Owner/release contract | T17, T18 | TC-T17-002, TC-T18-001, TC-T18-002 |
| FR-021 | Generic package-config transform | T19, T15, T17 | TC-T19-001, TC-T19-002, TC-T19-003, TC-T15-001, TC-T17-002 |
| NFR-001 | Pinned-tool fixed point | T1, T3, T9-T11, T15 | TC-T1-001, TC-T3-001, TC-T9-001, TC-T10-002, TC-T11-001, TC-T15-001 |
| NFR-002 | Diagnostic non-disclosure | T5, T7, T19 | TC-T5-001, TC-T5-002, TC-T5-003, TC-T7-003, TC-T19-002 |
| NFR-003 | Atomic error behavior | T6 | TC-T6-001, TC-T6-002 |
| NFR-004 | Released payload immutability | T1, T8-T13, T15, T17, T19 | TC-T1-005, TC-T8-004, TC-T9-002, TC-T10-002, TC-T11-002, TC-T12-001, TC-T13-002, TC-T15-002, TC-T17-002, TC-T19-003 |
| NFR-005 | Issue regression safety | T1, T15, T17, T18 | TC-T1-003, TC-T15-004, TC-T17-002, TC-T18-002 |
| NFR-006 | Exact-candidate release quality | T17, T18 | TC-T17-001, TC-T17-002, TC-T18-001 |
| NFR-007 | Opus candidate review | T16, T17, T18 | TC-T16-001, TC-T17-002, TC-T18-002 |
| NFR-008 | Consumer outcome compatibility | T1, T3, T4, T9, T19, T15, T17 | TC-T1-004, TC-T3-002, TC-T4-001, TC-T9-001, TC-T19-003, TC-T15-003, TC-T17-002 |
| NFR-009 | Release classification | T1, T14, T17 | TC-T1-004, TC-T14-002, TC-T17-002 |
| IR-001 | Explicit-path CLI contract | T2 | TC-T2-001 |
| IR-002 | Managed-restore CLI contract | T7 | TC-T7-002, TC-T7-003 |
| IR-003 | Usage-index configuration | T13 | TC-T13-002 |
| IR-004 | Versioned structured findings and release classification | T5, T14, T17, T19 | TC-T5-001, TC-T5-002, TC-T14-002, TC-T17-002, TC-T19-002 |
| IR-005 | Package-config transform preview/check/apply | T19, T15, T17 | TC-T19-002, TC-T19-003, TC-T15-001, TC-T17-002 |
| DR-001 | Restore preview/apply state | T7 | TC-T7-002, TC-T7-003 |
| DR-002 | Evolvable issue ledger | T1, T15, T17, T18 | TC-T1-003, TC-T15-004, TC-T17-002, TC-T18-002 |

### 4.1 Constraint Enforcement

| Spec constraint | Plan enforcement | Evidence |
| --- | --- | --- |
| C-001 | P2 edits only new successor paths; T1 captures and T15/T17 compare every released predecessor digest. | TC-T1-005, TC-T15-002, TC-T17-002 |
| C-002 | T1 baseline and T15/T17 candidate installed-authority gates put one exact extracted wheel first on `PYTHONPATH`. | TC-T1-003, TC-T15-001, TC-T17-001 |
| C-003 | Task-local gates and §11 preserve Ruff, BasedPyright, pytest/coverage, pip-audit, package, Node, coherence, and managed-document authorities. | T1-T17 Verify Task steps; TC-T17-001 |
| C-004 | The owner-granted MCP-hold exception authorizes T1-T17 and bounded T19 implementation; further scope expansion returns to the owner. | §2 gates; OQ-001 |
| C-005 | T17 stops unpublished; T18 starts only with authorization naming the exact commit and artifact digests. | TC-T17-002, TC-T18-001 |
| C-006 | `package.json` and `package-lock.json` dependency pins remain byte-identical to v5.8.0 unless the owner separately authorizes a scope change. | TC-T1-006, TC-T17-002 |
| C-007 | Outcome-aware ledger execution and canonical proof-symbol digests reject missing, skipped, xfailed, xpassed, errored, deleted, or changed proof outside DR-002. | TC-T1-003, TC-T15-004, TC-T17-002 |
| C-008 | `spec_ref`, direct IDs, §4/§7/Appendix B transpose checks, plan validation, and verified Opus plan review block approval on drift. | plan validator plus Opus plan result |
| C-009 | T19 permits only explicit direct automatic-edge opt-in whose schema evolution passes the bounded declaration-eligibility profile, one provider and one plan transform, declared pointer diffs, introduced-leaf dual-schema validity, target validity, idempotence, ordinary plan/apply preconditions, and no package-ID branch. | TC-T19-001, TC-T19-002, TC-T19-003, TC-T17-002 plus T19 scope logs |

## 5. Architecture and Expected Change Surface

| Area | Expected paths | Contract |
| --- | --- | --- |
| Frontmatter CLI | `src/project_standards/cli.py`, `frontmatter_commands.py`, `format_frontmatter.py`, `validate_frontmatter.py`, `validate_id.py`, explicit caller tests | Shared explicit-path classification; caller-specific unsupported-directory diagnostics. |
| Structured adapters | `src/project_standards/control_plane/adapters/jsonc.py`, `toml.py`, adapter tests | Preserve semantic ownership and unrelated bytes while satisfying declared fixed points. |
| Reconcile planning/execution | `src/project_standards/control_plane/{planner,executor,cli}.py`, tests | Error findings block all apply; restore is exact, explicit, and preconditioned. |
| Package-config transform | `src/project_standards/package_contract/payload.py`, generated standard-payload schema, `src/project_standards/control_plane/{resolution,planner,schemas,config_edit}.py`, bounded nested-inline support in `control_plane/adapters/toml.py`, generated reconciliation-plan schema 1.3, `codec.py` only if required to reuse the canonical TOML scalar renderer, focused package/control-plane/compatibility tests | One explicitly opted-in direct-edge provider; pointer-limited, introduced-leaf dual-schema-valid, target-valid, idempotent config action with typed value-redacted evidence inside ordinary planning. No CLI, executor, lock-schema, or package-ID-specific branch. |
| Diagnostics | control-plane finding/codec/schema source, `src/project_standards/agent_handoff/`, generated schemas, tests | Structured locations and bounded measures under a shared redaction rule; reconciliation-plan 1.2 at T5 and candidate-emitted 1.3 at T19, plus Agent Handoff envelope 1.1. |
| Python Tooling successor | `standards/python-tooling/versions/1.9/`, family manifest, schemas, providers, migration/tests | Additive configuration, non-installable mode, corrected fresh default, behavior-preserving migration. |
| Markdown Tooling successor | `standards/markdown-tooling/versions/1.9/`, family manifest, providers, docs/tests | Pinned-tool file-set and fixed-point convergence. |
| Shared Markdown reusable workflows | `.github/workflows/format.yml`, `.github/workflows/lint-markdown.yml`, workflow/caller integration tests | Shared by every released Markdown Tooling version through `@v5`; unchanged by default. Any required edit invokes SPEC-VAIC AW-004 owner disposition before GREEN. |
| Agent Handoff successor | `standards/agent-handoff/versions/1.5/`, family manifest, docs/tests | Clear independent-tool exclusion ownership. |
| CLI Documentation successor | `standards/cli-documentation/versions/1.4/`, family manifest, schema/docs/tests | Valid TOML and optional referenced usage index. |
| Regression ledger | repository test metadata/validator, focused semantic assertions, current-train tests | Stable issue contract IDs with executable baseline/candidate references and reviewed amendment history. |
| Markdown ownership declaration | `tests/coherence/declaration.py`, `tests/coherence/test_declaration.py`, `tests/test_markdownlint_config.py`, observed-consumer fixtures | Accept predecessor `MD060` style-any before activation and explicit `MD060: false` after activation; retain the #27 literal fixture. |
| Release consistency | release/package validation source and tests; root `README.md`, `UPGRADING.md`; `standards/README.md`; every mutable family-level `standards/{family}/*.md` document | Every family version reference equals its candidate-catalog default or carries an asserted historical classification; candidate commit, catalog, defaults, links, commands, and prose agree before tag. |
| Projection and release | `.standards/config.toml`, `standards/catalog.md`, packaged catalog/payload projections, changelog/status/handoff | Each P2 owner regenerates its staged-successor surfaces; successors activate together only after all earlier tasks pass. |

**Successor staging rule:** T8, T9/T11, T12, and T13 create complete consumer payloads, including their adoption guides, with `availability = "consumer"` and add each version to its family `standard.toml`, but do not add those versions to canonical `catalogs/5.toml`. T8 owns Python Tooling 1.9's fresh default and package features; T19 solely adds its generic-transform provider/declarations and the required family/projection digest consequences after the engine contract exists. Each owning P2 task that creates or changes staged-successor bytes regenerates the family-manifest aggregate digest, the corresponding packaged payload projection, and `standards/catalog.md`; the new catalog row remains `unadvertised`, and later byte changes alter that row only when its rendered resource/provider/output counts change. Package, integrity, graph, schema, provider-unit, documentation, rendered-catalog, and payload-projection gates cover the family-indexed staged payloads directly, while resolution cannot select an uncatalogued version and this repository's `version = "latest"` selectors remain on the released defaults. After T19 and the final owning P2 task finish, those successor bytes/digests are final. T15 solely owns canonical catalog activation: it changes the four prior defaults to retained, adds the four already-validated successors as defaults without changing payload/family bytes, regenerates the resulting catalog projections and `standards/catalog.md` role column, verifies the unchanged payload projection, and reruns every package/provider/migration/integration gate. Released predecessor bytes never change.

## 6. Test Strategy

- Use pytest test names `test_unit__condition__expected_result`, with the three segments replaced by specific behavior terms, for new tests.
- Each bug fix begins with a focused regression that fails against the current code for the intended reason.
- T1 derives exact Prettier and markdownlint-cli2 versions from the repository lockfile (currently 3.8.3 and 0.23.1), verifies the installed executables match, and then supplies shared subprocess oracles pinned to those derived versions.
- Property-style coverage uses parametrized generated cases for JSON/JSONC whitespace and insertion positions, exclusion forms, TOML keyed entries, digest mismatches, and config option combinations. A new property-testing dependency requires separate owner approval.
- Fixed-point invariant: if an owned input is clean under the applicable pinned formatter before composition, the composed output is clean under the same formatter; semantic parsing and unrelated consumer values are preserved.
- Atomicity invariant: an error-bearing reconciliation plan produces no filesystem mutation and a nonzero result, regardless of `--apply`.
- Restore invariant: preview is non-mutating; apply succeeds only for one exact exclusively managed whole-file target whose current/lock/desired digests still match the preview preconditions.
- Migration invariant: migrating a current exact payload preserves effective prior behavior unless the issue explicitly requires a corrected migration outcome.
- Package-config transform invariant: only an exact applied-source/direct-selected-target opt-in runs; source validation precedes provider execution; the declared pointer allowlist is nonempty and the semantic diff is a possibly empty subset of it; explicit true/false and every second invocation require an empty diff; output validates under source and target schemas and is idempotent; preview/check never writes; apply publishes one lexical config action before dependent artifacts/lock; stale or unknown authority and multiple transforms fail before writes.
- Regression invariant: the exact 5.8.0 wheel passes every applicable committed seed-ledger row before current-train RED; the candidate passes every applicable seed/current-train row before release authorization.
- Anti-weakening invariant: each row declares exact pytest nodes or semantic assertions plus canonical AST/source digests for every proof function/helper/fixture symbol on which it relies. The outcome runner requires every mapped proof to report `passed`; missing, skipped, xfailed, xpassed, failed, or errored outcomes fail. Any proof-symbol digest change requires the complete DR-002 amendment record and same-behavior baseline/candidate evidence.
- Consumer-outcome invariant: exact-version and `latest` fixtures are compared from 5.8.0 through candidate migration, and no validation, lint, format, reconcile, or installed-workflow result may move from pass to fail.
- Release-identity invariant: T17 qualifies the final release commit only after its version, lock, changelog, documentation, and candidate-specific bytes are complete; T18 lands that exact commit unchanged.

### 6.1 Scope Verification Checkpoints

Each T1-T17 and T19 checklist must record a task base commit and the task's declared requirements, acceptance tests, and expected paths before any task edit. The executor then performs these checkpoints:

1. **Task start:** compare the clean working tree and intended paths with the task definition. Record the base commit and allowed change surface in the task log. Mechanically required generated outputs or cross-file contract counterparts are allowed only when named before editing.
2. **Before GREEN:** inspect `git diff --name-status "$TASK_BASE"` and `git diff --stat "$TASK_BASE"`. The RED diff may contain only focused tests, fixtures, and ephemeral evidence needed to prove the task's specified behavior. Production changes or unrelated cleanup at this checkpoint are a hard stop.
3. **Before Verify Task:** repeat the name/status and stat review, inspect the complete diff against the task's requirements and acceptance tests, and run `git diff --check`. Every changed path and behavior must be necessary for the current task or a previously declared generated/cross-file counterpart. REFACTOR may simplify only inside that verified surface and may not introduce a new abstraction, option, dependency, framework, or generalized capability without a demonstrated task requirement.
4. **Phase boundary:** after the final task in each phase, compare the aggregate phase diff and commits with SPEC-VAIC scope, constraints, and non-goals before starting the next phase.

An unplanned path, behavior, dependency, cleanup, or generalized mechanism stops the task. Record it in `.project-pipeline/2026-07-25-v5-adoption-integrity-correction-train/notes.md`; remove it from the current diff or route it through the plan's discovered-work/spec-change procedure and obtain any required renewed approval. Do not absorb it because it is convenient or nearby.

### 6.2 TDD Exceptions

| Task | Exception reason | Objective validation |
| --- | --- | --- |
| T16 | Independent adversarial review is evidence, not production behavior. | Complete candidate bundle, recorded Opus verdict, and no unresolved Critical/High finding. |
| T17 | Candidate qualification and handoff preparation integrate already-tested behavior. | One wheel digest and the complete repository gate against its extracted bytes. |
| T18 | Publication and tracker mutation are external release operations. | Explicit authorization, signed tag/release, hosted workflow and downloaded-asset parity, issue closure evidence. |

## 7. Execution Summary

| Task | Title | Phase | Depends on | Requirements |
| --- | --- | --- | --- | --- |
| T1 | Refresh issues; establish regression, tool, and compatibility baselines | P1 | None | FR-002, FR-015, NFR-001, NFR-004, NFR-005, NFR-008, NFR-009, DR-002 |
| T2 | Correct directory positional diagnostics | P1 | T1 | FR-001, IR-001 |
| T3 | Preserve JSON/JSONC formatter fixed points | P1 | T1 | FR-002, NFR-001, NFR-008 |
| T4 | Preserve valid optional-identity TOML entries | P1 | T1 | FR-007, NFR-008 |
| T5 | Add precise redacted structural diagnostics | P1 | T1 | FR-013, FR-018, NFR-002, IR-004 |
| T6 | Make error-bearing reconcile apply atomic | P1 | T1 | NFR-003 |
| T7 | Add whole-file conflict guidance and exact restore | P1 | T5, T6 | FR-004, FR-005, NFR-002, IR-002, DR-001 |
| T8 | Build Python Tooling 1.9 | P2 | T1 | FR-008, FR-009, FR-017, FR-019, NFR-004 |
| T9 | Converge Markdown exclusion file sets | P2 | T1 | FR-015, FR-019, NFR-001, NFR-004, NFR-008 |
| T10 | Stabilize Markdown callers and permissions | P2 | T1, T6, T9 | FR-006, FR-016, FR-019, NFR-001, NFR-004 |
| T11 | Converge Markdown lint/format safety | P2 | T1, T9, T10 | FR-012, FR-019, NFR-001, NFR-004 |
| T12 | Build Agent Handoff 1.5 adoption boundary | P2 | T5 | FR-011, FR-019, NFR-004 |
| T13 | Build CLI Documentation 1.4 | P2 | T5 | FR-010, FR-014, FR-019, IR-003, NFR-004 |
| T14 | Add candidate-bound release consistency | P3 | T8-T13 | FR-003, FR-019, NFR-009, IR-004 |
| T15 | Activate successors and prove migrations | P3 | T2-T14, T19 | FR-012, FR-015, FR-019, FR-021, NFR-001, NFR-004, NFR-005, NFR-008, IR-005, DR-002 |
| T16 | Run blocking Opus candidate audit | P3 | T15 | NFR-007 |
| T17 | Qualify the unchanged exact release commit | P3 | T16 | FR-003, FR-020, FR-021, NFR-004, NFR-005, NFR-006, NFR-007, NFR-008, NFR-009, IR-004, IR-005, DR-002 |
| T18 | Publish and close issues after authorization | P4 | T17 | FR-020, NFR-005, NFR-006, NFR-007, DR-002 |
| T19 | Add generic direct package-config transforms | P2/P3 prerequisite | T5, T8 | FR-017, FR-019, FR-021, NFR-002, NFR-004, NFR-008, IR-004, IR-005 |

## 8. Implementation Tasks

### Phase P1: Engine Integrity

#### T1: Refresh issues; establish regression, tool, and compatibility baselines

- **goal:** Freeze current issue acceptance, make closed-issue regression proof durable, and establish reusable pinned-tool and consumer-outcome truth surfaces. · **phase:** P1 · **depends_on:** [] · **requirements:** [FR-002, FR-015, NFR-001, NFR-004, NFR-005, NFR-008, NFR-009, DR-002] · **priority:** must
- **files:** issue evidence/checklists under `.project-pipeline/` (ephemeral); committed issue regression ledger/validator and #21 semantic guard under repository test surfaces; shared coherence/oracle and exact/default-track consumer fixtures under `tests/`
- **acceptance:** every open issue body/comment is rechecked without changing GitHub; the committed ledger covers #3 and #8-#31 with stable IDs, executable references, environments, canonical proof-symbol digests, outcome records, inclusion rationale, and amendment fields; missing/dangling/unexplained issue rows and missing/skipped/xfailed/xpassed/failed/errored/changed proofs fail; #21 has a dedicated semantic guard; the exact published 5.8.0 wheel passes every applicable seed row and the pre-train gates recorded in the durable audit; a v5.8.0-tag/published-wheel authority produces the predecessor payload digest ledger and Node dependency-pin baseline rather than trusting mutable working-tree digests; installed formatter/linter versions equal lockfile authority; JSON, JSONC, Markdown, YAML, and exclusion probes use those tools; exact-selection and `latest` consumer fixtures record 5.8.0 outcomes; planned-change analysis finds no pass-to-fail outcome and supports MINOR before affected GREEN (TC-T1-001 through TC-T1-006).
- **sub-tasks:**
  - **T1.0 CHARACTERIZE** — refresh #32 and #35-#49 read-only; bind the exact branch/commit and published 5.8.0 wheel digest; derive released predecessor digests and `package.json`/`package-lock.json` dependency-pin digests from v5.8.0 tag/published authority; re-run the durable closed-issue audit commands or their committed successor surface; derive tool versions from the lockfile and verify installed versions; run source-authoritative tests against source and installed-authority tests with the exact wheel first on `PYTHONPATH`; execute minimal reproductions for #35, #44, #47, and #48; characterize exact-selection and `latest` fixtures; and complete NFR-009 requirement-by-requirement analysis. Any closed-issue regression invokes SPEC-VAIC AW-003 and blocks this train; any other baseline failure blocks RED until proven environmental or returned to the approved spec/plan.
  - **T1.1 RED** — add ledger schema/reference/outcome/proof-digest/amendment failures; negative cases for missing, skipped, xfailed, xpassed, errored, deleted, assertion-relaxed, helper-relaxed, dangling, duplicate, and unexplained rows; the #21 semantic guard; a self-consistent predecessor-payload tamper that still fails against the captured baseline; Node pin-drift detection; oracle contract tests; distinct JSON/JSONC probes; effective-file-set probes; and baseline outcome-matrix assertions.
  - **T1.2 Verify RED** — prove the durable ledger/#21 guard/oracle/outcome surfaces are absent while direct commands reproduce the audited baseline and issue fixtures.
  - **T1.3 GREEN** — add the smallest committed outcome-aware ledger runner/validator, canonical AST/source proof-symbol digest resolver, semantic guard, predecessor/Node baseline comparison, and reusable test helpers/fixtures; require `passed` for each mapped proof and a complete DR-002 amendment for any proof digest change; do not call GitHub from normal tests or add a production formatter dependency.
  - **T1.4 Verify GREEN** — run every applicable seed row against the exact wheel, then the oracle/outcome tests on JSON, JSONC, Markdown table/directive, caller YAML, and exclusion cases.
  - **T1.5 REFACTOR** — centralize subprocess construction, stable diagnostic/outcome normalization, regression IDs, proof-symbol digesting, and fixture authorities; any reference or proof change follows DR-002.
  - **T1.6 Verify Task** — run seed-ledger negative/positive cases, #21 guard, predecessor/Node baseline guards, shared oracle/outcome tests, Ruff, BasedPyright, and `npm ci`; commit with spec requirement/test IDs.

#### T2: Correct directory positional diagnostics

- **goal:** Distinguish an existing directory from a missing file without adding directory walking. · **phase:** P1 · **depends_on:** [T1] · **requirements:** [FR-001, IR-001] · **priority:** must
- **files:** shared frontmatter explicit-path collector, `src/project_standards/cli.py`, `format_frontmatter.py`, `frontmatter_commands.py`, `validate_frontmatter.py`, `validate_id.py`, and their tests
- **interface/data:** extend `collect_paths` with an optional keyword carrying the caller's supported bare/config-driven invocation, following the existing opt-in `on_named_excluded` compatibility pattern. Every explicit-path caller supplies it; zero-keyword/empty-explicit-list callers retain their current signature and behavior. The helper classifies directories once and renders the named path plus that caller-specific invocation without walking it.
- **acceptance:** `format-frontmatter`, `validate-frontmatter`, `validate-id`, `project-standards fix`, and every routed explicit-path caller retain their usage/input exit class, name the unsupported directory, and show their own bare/config-driven invocation; missing paths retain “no such file”; named files preserve #29 behavior; config-only `validate-references` and spec/config discovery do not gain positional traversal (TC-T2-001).
- **sub-tasks:**
  - **T2.1 RED** — derive the authoritative inventory by searching every `collect_paths` call with a nonempty explicit list; add `project-standards fix DIRECTORY` plus directory, missing-path, named-file, bare invocation, and configured-glob cases for every caller; guard empty-list `validate_references.py` and `specs/config.py` call sites as config-only non-callers.
  - **T2.2 Verify RED** — prove only the directory case has the misleading current diagnostic.
  - **T2.3 GREEN** — add the optional invocation keyword, classify directory inputs before the missing-file branch, and emit caller-specific supported-interface guidance while preserving the existing call form.
  - **T2.4 Verify GREEN** — run targeted CLI/collector tests.
  - **T2.5 REFACTOR** — keep path classification single-pass and preserve current exception types.
  - **T2.6 Verify Task** — run the frontmatter suite, Ruff, and BasedPyright; commit with IDs.

#### T3: Preserve JSON/JSONC formatter fixed points

- **goal:** Make semantic JSON-family composition context-aware enough to preserve clean formatting without reserializing unrelated values. · **phase:** P1 · **depends_on:** [T1] · **requirements:** [FR-002, NFR-001, NFR-008] · **priority:** must
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

- **goal:** Match keyed TOML array entries without rejecting unrelated valid entries that omit the optional identity field. · **phase:** P1 · **depends_on:** [T1] · **requirements:** [FR-007, NFR-008] · **priority:** must
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

- **goal:** Add actionable locations and measures to TOML and Agent Handoff diagnostics under one no-content-leak contract. · **phase:** P1 · **depends_on:** [T1] · **requirements:** [FR-013, FR-018, NFR-002, IR-004] · **priority:** must
- **files:** control-plane finding/codec/model/schema source, `src/project_standards/agent_handoff/`, generated reconciliation/Agent Handoff schemas and snapshots, CLI/provider/model tests
- **acceptance:** TOML parse errors include parser-derived safe line/column and retain the original exception cause; handoff findings include root-relative path, structural locus, line when known, observed measure, and limit; JSON/text renderings agree; reconciliation-plan schema advances from 1.1 to the intra-candidate 1.2 checkpoint and Agent Handoff envelope from 1.0 to 1.1 with closed additive schemas; T19 later owns candidate-emitted reconciliation-plan 1.3, with 1.1/1.2 explicit prior recognition; secret-like scalar values and raw consumer lines never appear (TC-T5-001, TC-T5-002, TC-T5-003).
- **sub-tasks:**
  - **T5.0 CHARACTERIZE** — inventory diagnostic construction/rendering and classify safe structural fields versus forbidden content.
  - **T5.1 RED** — add exact location/measure, schema/envelope version, prior-version recognition/rejection, exception-chaining, renderer-parity, and adversarial secret-redaction regressions.
  - **T5.2 Verify RED** — prove current diagnostics omit required structure and that fixtures would detect content leakage.
  - **T5.3 GREEN** — extend typed finding/parse diagnostics and renderers with optional safe fields; chain original parse failures.
  - **T5.4 Verify GREEN** — run codec, handoff policy/link, provider, JSON, and text CLI cases.
  - **T5.5 REFACTOR** — centralize bounded diagnostic projection and eliminate duplicated message parsing.
  - **T5.6 Verify Task** — run control-plane and Agent Handoff suites, Ruff, and BasedPyright; commit with IDs.

#### T6: Make error-bearing reconcile apply atomic

- **goal:** Characterize every error-bearing apply path and preserve the invariant that it performs no mutation and returns nonzero. · **phase:** P1 · **depends_on:** [T1] · **requirements:** [NFR-003] · **priority:** must
- **files:** `src/project_standards/control_plane/{cli,planner,executor}.py`, reconciliation tests
- **acceptance:** for ordinary reconcile `--apply`, any error-severity finding blocks the complete plan before executor entry, leaves a filesystem snapshot unchanged, and exits nonzero in text and JSON modes; warning-only conflict-free plans retain current behavior. This ordinary-apply gate does not prevent the separately selected T7 `--restore-managed PATH --apply` recovery mode from handling its own exact preconditions (TC-T6-001, TC-T6-002).
- **sub-tasks:**
  - **T6.0 CHARACTERIZE** — identify whether the reported mutation is on ordinary reconcile apply, post-apply provider verification, migration apply, or recovery apply; for each path record executor entry, text/JSON exit, and before/after tree hashes, including a valid action plus error finding and a provider error after actions.
  - **T6.1 RED** — add mixed valid-mutation plus error-finding fixtures and before/after tree assertions.
  - **T6.2 Verify RED** — reproduce the exact mutation path if present. If no path mutates, prove the current gate already satisfies NFR-003 and make the new tree-snapshot/executor-entry cases guard current behavior rather than forcing a production change.
  - **T6.3 GREEN** — add the smallest missing pre-execution, rollback, or stable-exit correction on the characterized path; if no defect reproduces, add no production change.
  - **T6.4 Verify GREEN** — run CLI/planner/executor transaction and rollback regressions.
  - **T6.5 REFACTOR** — keep applicability and severity decisions in one typed boundary.
  - **T6.6 Verify Task** — run reconciliation suites, Ruff, and BasedPyright; commit with IDs.

#### T7: Add whole-file conflict guidance and exact restore

- **goal:** Make safe pre-adoption recovery explicit without turning reconciliation into general file repair. · **phase:** P1 · **depends_on:** [T5, T6] · **requirements:** [FR-004, FR-005, NFR-002, IR-002, DR-001] · **priority:** must
- **files:** control-plane planner/CLI/executor/models, recovery tests, CLI docs
- **interface/data:** add restore mode with grammar `reconcile --restore-managed PATH [--apply]`. Without `--apply`, it is a non-mutating preview; within restore mode, `--apply` is the explicit confirmation modifier, not ordinary reconcile apply. Restore mode cannot combine with `--check`, `--repair-state`, `--allow-major`, or an ordinary unqualified apply request. `PATH` must resolve to one declared, exclusively managed, whole-file target with an existing authoritative lock entry; it never accepts a glob or directory. Preview returns target, owner identity, current state as either an exact digest or `absent`, lock digest, desired digest, action (`overwrite`, `recreate`, or `noop`), and exact apply command. `noop` applies when current and desired digests already match and never writes. An existing divergent current file may differ from the lock digest: explicit restore is allowed to overwrite that drift only after preview, and the preview must say so without disclosing its bytes. A missing current file may be recreated only when the lock still proves exclusive ownership. Apply atomically requires the current state still equals the preview digest or remains absent, the lock and desired digests still match, and the regular-file/absence, containment, and ownership conditions still hold. The apply result records the superseded current digest or `absent` plus the resulting digest, never superseded content. An absent lock, a newly appeared file after an `absent` preview, or any changed digest fails closed.
- **acceptance:** conflict hints distinguish safe manual delete/reconcile for pre-adoption targets from consumer-owned, shared, partial, or otherwise unsafe cases; every unsafe class states why no destructive action is authorized; pre-adoption targets without a lock cannot use restore mode; restore preview is non-mutating; explicit apply overwrites a previewed divergent exclusively managed file or recreates a previewed absent locked file and touches only the requested target; a current-equals-desired preview/apply reports `noop` and performs no write; stale current/absent state, stale lock/desired digest, symlink, partial-block, shared/consumer-owned, absent lock, glob, and directory inputs fail closed (TC-T7-001, TC-T7-002, TC-T7-003).
- **sub-tasks:**
  - **T7.1 RED** — add pre-adoption conflict-guidance plus divergent-current overwrite, absent-current recreate, preview/apply, and every digest/state/ownership/security rejection case.
  - **T7.2 Verify RED** — confirm current behavior lacks the interface and current generic conflict hint cannot satisfy the ownership cases.
  - **T7.3 GREEN** — add explicit target resolution, preview model, digest preconditions, and executor path using existing atomic write safety; construct restore evidence and conflict hints through T5's shared bounded-diagnostic projection rather than task-local redaction.
  - **T7.4 Verify GREEN** — run recovery, reconciliation, symlink, transaction, text, and JSON cases.
  - **T7.5 REFACTOR** — share existing digest/containment and bounded-diagnostic projection primitives; assert one redaction entry point for findings and restore evidence; keep restore separate from incomplete-state repair.
  - **T7.6 Verify Task** — run complete control-plane recovery/executor/CLI suites, Ruff, and BasedPyright; commit with IDs.

### Phase P2: Immutable Successor Packages

#### T8: Build Python Tooling 1.9

- **goal:** Add requested closed configuration, non-installable mode, and the safe fresh performance default while staging the package surface T19 will bind to generic upgrade preservation. · **phase:** P2 · **depends_on:** [T1] · **requirements:** [FR-008, FR-009, FR-017, FR-019, NFR-004] · **priority:** must
- **files:** new `standards/python-tooling/versions/1.9/`, family manifest, provider/schema/migration/tests, `standards/catalog.md`, and the new packaged payload projection; no canonical source-catalog edit
- **interface/data:** add empty-default closed lists for Ruff `extend_include`, `extend_select`, `extend_ignore`, and coverage `omit`; explicit `extend_ignore` may suppress a baseline-selected rule as reviewed consumer intent; add `build_backend = "none"`; make fresh 1.9 `ci.performance = false`. Preserve existing V4 legacy migration behavior. T19, not T8, adds the new package-to-package transform declaration/provider contract and real initialized-upgrade lifecycle. Explicit true with no performance tests continues to expose pytest exit 5.
- **acceptance:** unique nonempty option combinations render canonical native tables and invalid/empty entries name their governing option; empty lists render no bytes; backend none omits only `[build-system]`; fresh default omits performance CI; direct legacy-provider unit tests remain corroborating evidence but are not counted as unified package-upgrade proof; the complete consumer payload is family-indexed but absent from the canonical catalog, passes package/graph/schema/rendered-catalog/payload-projection/provider-unit gates with its adoption guide intact, adds exactly one `unadvertised` generated-catalog row and its packaged payload projection, and leaves root `latest` on Python Tooling 1.8; predecessor payload bytes remain unchanged (TC-T8-001 through TC-T8-004).
- **sub-tasks:**
  - **T8.0 CHARACTERIZE** — pin 1.8 defaults, bytes, provider output, and migration mechanics.
  - **T8.1 RED** — add schema/provider/fresh-adoption/package regressions for every option and combination, explicit baseline-rule suppression, fresh false, explicit true exit 5, and retained V4 migration behavior; do not simulate a unified package upgrade by calling the legacy provider directly.
  - **T8.2 Verify RED** — confirm tests target absent 1.9 behavior while 1.8 characterization stays green.
  - **T8.3 GREEN** — create the complete uncatalogued consumer 1.9 payload/provider/schema/adoption guide with family registration and retained V4 migration; regenerate its packaged payload projection and `standards/catalog.md` `unadvertised` row; record the staged successor digest. T19 owns the later config-transform provider/declaration and final digest; T15 owns only canonical catalog/default activation.
  - **T8.4 Verify GREEN** — run Python Tooling package/provider/migration and pinned TOML checks.
  - **T8.5 REFACTOR** — derive rendered lists/defaults from typed config and avoid parallel ownership.
  - **T8.6 Verify Task** — run package tests, graph/schema/rendered-catalog/payload-projection checks, Ruff, and BasedPyright; commit with IDs.

#### T9: Converge Markdown exclusion file sets

- **goal:** Make configured exclusions express the same intended files for lint and format without assuming the reported normalization before reproducing it. · **phase:** P2 · **depends_on:** [T1] · **requirements:** [FR-015, FR-019, NFR-001, NFR-004, NFR-008] · **priority:** must
- **files:** new Markdown Tooling 1.9 payload/provider/schema/docs/tests and family manifest; `standards/catalog.md` and the new packaged payload projection; `.github/workflows/format.yml` and `lint-markdown.yml` as read-only characterization surfaces unless AW-004 is authorized; no canonical source-catalog edit
- **acceptance:** pinned effective-file-set cases cover `dir`, `dir/`, `dir/**`, nested files, supported negation, and platform separators across provider-rendered caller inputs, reusable-workflow input/materialization, shell/cwd behavior, and each tool's matching dialect; the causal record identifies the actual divergence; configured exclusions remain authority; the correction converges both tools on the intersection of their 5.8.0-selected corpora so neither lint nor format scope widens; the complete consumer 1.9 payload is family-indexed, package-visible, and uncatalogued while root `latest` remains on 1.8; shared reusable workflows stay byte-identical unless the owner explicitly dispositions AW-004 before GREEN; an exact 1.8 fixture remains unmigrated and compares its `@v5` workflow outcomes across baseline/candidate; Markdown Tooling 1.8 bytes remain unchanged (TC-T9-001, TC-T9-002).
- **sub-tasks:**
  - **T9.0 CHARACTERIZE** — reproduce #47 with pinned tools for every supported exclusion form; record selected sets at each boundary: provider-rendered caller inputs, lint workflow negated globs, format workflow synthesized ignore file, shell/cwd handling, and markdownlint/Prettier dialects.
  - **T9.1 RED** — add effective-file-set parity and rendered-ignore regressions bound to the confirmed cause plus an unmigrated exact-1.8 `@v5` workflow outcome fixture.
  - **T9.2 Verify RED** — prove which candidate cause or combination causes the divergence; do not pre-assume tool interpretation, provider rendering, workflow handling, shell expansion, or working-directory drift.
  - **T9.3 GREEN** — create complete uncatalogued consumer Markdown Tooling 1.9 with family registration, regenerate its packaged payload projection and `standards/catalog.md` `unadvertised` row, and implement only the characterized payload/provider materialization needed for the non-widening intersection. If shared workflow bytes must change, stop for AW-004 owner disposition before GREEN and extend the released-selection matrix; if no divergence reproduces, carry 1.8 rendering forward unchanged and add the guard. T11 completes and seals this successor; T15 owns only catalog/default activation.
  - **T9.4 Verify GREEN** — compare actual lint/format selected files and pinned exit results.
  - **T9.5 REFACTOR** — centralize exclusion projection while keeping tool-specific semantics explicit.
  - **T9.6 Verify Task** — run Markdown provider/oracle/package tests and schema/graph/rendered-catalog/payload-projection checks; commit with IDs.

#### T10: Stabilize Markdown callers and permissions

- **goal:** Render long caller inputs as Prettier-stable YAML and grant the minimum reusable-workflow read permission. · **phase:** P2 · **depends_on:** [T1, T6, T9] · **requirements:** [FR-006, FR-016, FR-019, NFR-001, NFR-004] · **priority:** must
- **files:** Markdown Tooling 1.9 caller provider/templates/tests, `standards/markdown-tooling/standard.toml`, `standards/catalog.md`, and the packaged Markdown Tooling 1.9 payload projection
- **acceptance:** both managed callers in the uncatalogued consumer 1.9 payload render exact job-level or workflow-level `contents: read` consistent with the called workflows; long globs/exclusions use stable block scalars; isolated successor reconcile reaches a clean fixed point and any formatter/planner error remains atomic; root `latest` remains 1.8 until T15; Markdown Tooling 1.8 bytes remain unchanged (TC-T10-001, TC-T10-002).
- **sub-tasks:**
  - **T10.1 RED** — add caller snapshots, pinned Prettier checks, permissions assertions, and reconcile fixed-point cases.
  - **T10.2 Verify RED** — reproduce scalar wrapping and managed-byte drift on the current caller.
  - **T10.3 GREEN** — render canonical block scalars and exact read permissions in both caller families; regenerate the family-manifest aggregate digest, packaged payload projection, and `standards/catalog.md` row, whose rendered values change only if the resource/provider/output counts changed.
  - **T10.4 Verify GREEN** — run provider, workflow schema, Prettier, and repeated reconcile cases.
  - **T10.5 REFACTOR** — share caller input rendering without widening workflow permissions.
  - **T10.6 Verify Task** — run Markdown package/coherence/control-plane tests, rendered-catalog and payload-projection checks, and Node gates; commit with IDs.

#### T11: Converge Markdown lint/format safety

- **goal:** Remove the markdownlint/Prettier table conflict and keep autofix out of the normal adoption path. · **phase:** P2 · **depends_on:** [T1, T9, T10] · **requirements:** [FR-012, FR-019, NFR-001, NFR-004] · **priority:** must
- **files:** Markdown Tooling 1.9 lint config, README/adopt guidance, examples/tests, split-ownership declaration/coherence tests, Markdown customization assertions, `standards/markdown-tooling/standard.toml`, `standards/catalog.md`, and the packaged Markdown Tooling 1.9 payload projection
- **interface/data:** render explicit `"MD060": false` because Prettier owns table layout and the rule set remains fully explicit; update the split-ownership assertion in the same change so it accepts the predecessor style-any form before activation and requires the explicit disabled form for the successor after activation; retain the #27 observed-consumer fixture's literal MD060 value; add the derived customization entry without hardcoding a fixed count; teach block `markdownlint-disable`/`markdownlint-enable` around exceptional regions; normal verification runs lint without `--fix`; an optional autofix recipe requires a clean starting diff, reviewed resulting diff, and follow-up Prettier/lint.
- **acceptance:** root `latest` remains 1.8 and coherence-green while the uncatalogued consumer 1.9 projection passes isolated successor coherence; T15's catalog/default activation makes the same unchanged 1.9 bytes root-selected and coherence-green; Prettier plus markdownlint reaches a fixed point for tables/directives; the #27 literal fixture remains unchanged; every copyable exceptional-region example uses paired block directives that stay attached after Prettier; underscores survive the normal recipe; every documented command is executable; Markdown Tooling 1.8 bytes remain unchanged (TC-T11-001 through TC-T11-003).
- **sub-tasks:**
  - **T11.1 RED** — add table/directive/underscore fixed-point fixtures, explicit-rule-set assertions, predecessor/successor split-ownership cases, #27 fixture-digest protection, and documentation-command assertions.
  - **T11.2 Verify RED** — reproduce the current MD060/directive/autofix conflict with pinned tools.
  - **T11.3 GREEN** — create the 1.9 lint config, revise adoption/reference/example guidance, update the split-ownership/customization declaration without changing the legacy observed-consumer fixture, regenerate the final family-manifest aggregate digest, packaged payload projection, and `standards/catalog.md` row, and seal the successor bytes.
  - **T11.4 Verify GREEN** — run coherence against both the unactivated 1.8 root form and isolated 1.9 successor form, then run Prettier/lint repeatedly and execute normal/optional recipes.
  - **T11.5 REFACTOR** — keep one formatting authority and one structural authority with no overlapping table rule.
  - **T11.6 Verify Task** — run Markdown package/coherence/docs tests, rendered-catalog and payload-projection checks, and Node gates; commit with IDs.

#### T12: Build Agent Handoff 1.5 adoption boundary

- **goal:** Document which locked Agent Handoff implementation files independent repository tooling must exclude. · **phase:** P2 · **depends_on:** [T5] · **requirements:** [FR-011, FR-019, NFR-004] · **priority:** must
- **files:** new `standards/agent-handoff/versions/1.5/`, adoption/reference/manifest/tests, family manifest, `standards/catalog.md`, and the new packaged payload projection; no canonical source-catalog edit
- **acceptance:** guidance derives locked paths from the payload's managed-artifact/locked-resource declarations, including `.agents/skills/agent-handoff/**` and `.agents/hooks/agent-handoff/session_start.py`; it explains why consumer formatters/type checkers do not own them and provides Python/Markdown exclusion patterns that actually match installed files; the complete consumer 1.5 payload is family-indexed and package-visible but uncatalogued while root `latest` remains 1.4; Agent Handoff 1.4 bytes remain unchanged (TC-T12-001).
- **sub-tasks:**
  - **T12.1 RED** — derive the authoritative locked-file inventory from payload managed-artifact targets/resources; add documentation-contract tests that every named path is declared and every copyable exclusion matches its installed file.
  - **T12.2 Verify RED** — confirm 1.4 lacks the contract and no engine detection is required.
  - **T12.3 GREEN** — create complete uncatalogued consumer 1.5 from 1.4 with family registration and only the adoption-boundary/compatible diagnostic documentation updates; regenerate its packaged payload projection and `standards/catalog.md` `unadvertised` row; record the final digest. T15 owns only catalog/default activation.
  - **T12.4 Verify GREEN** — run package, docs, and cross-package adoption checks.
  - **T12.5 REFACTOR** — keep ownership rationale in one referenced section and examples copyable.
  - **T12.6 Verify Task** — run Agent Handoff package/provider/docs/rendered-catalog/payload-projection gates; commit with IDs.

#### T13: Build CLI Documentation 1.4

- **goal:** Make adoption TOML valid and add one optional referenced multi-CLI usage index. · **phase:** P2 · **depends_on:** [T5] · **requirements:** [FR-010, FR-014, FR-019, IR-003, NFR-004] · **priority:** must
- **files:** new `standards/cli-documentation/versions/1.4/`, schema/provider/docs/examples/tests, family manifest, `standards/catalog.md`, and the new packaged payload projection; successor/default-guide TOML corpus tests; no canonical source-catalog edit
- **interface/data:** remove invalid `null` assignments from copyable TOML. Add optional `usage_index_path`, a contained repository-relative Markdown input that is consumer-owned and referenced by the managed usage surface. Default single-CLI generation is unchanged. Switching to the custom input does not delete the old create-only artifact.
- **acceptance:** every copyable TOML fence in CLI Documentation 1.4 and every candidate-default adoption guide changed by this train parses; non-copyable illustrative fragments, including copied-forward fragments, carry an explicit marker or non-TOML fence; the complete consumer 1.4 payload is family-indexed and package-visible but uncatalogued while root `latest` remains 1.3; CLI Documentation 1.1-1.3 remain byte-identical and their known invalid-null examples are asserted as historical limitations; absent custom path is byte-compatible with 1.3 behavior; valid custom index is referenced; absolute, escaping, missing, directory, symlink, and owned-output aliases fail closed; multiple generated usage artifacts remain unsupported (TC-T13-001, TC-T13-002).
- **stop/backtrack:** an invalid fence in a candidate-default guide owned by another planned successor routes to that successor task. An invalid fence in any released predecessor remains an immutable recorded limitation unless a separately approved successor owns its correction; never expand this task or edit predecessor bytes implicitly.
- **sub-tasks:**
  - **T13.0 CHARACTERIZE** — inventory the defined successor/default TOML corpus, classify copyable versus illustrative fragments, record the 1.1-1.3 known limitations/digests, and characterize 1.3 create-only artifact behavior.
  - **T13.1 RED** — add corpus TOML parsing, schema/path/security, default parity, custom-index, and transition preservation tests.
  - **T13.2 Verify RED** — prove current `null` and absent custom-index contract cause the intended failures.
  - **T13.3 GREEN** — create complete uncatalogued consumer 1.4 with family registration; implement schema/provider/docs, correct every invalid copyable fence in scope, mark every non-copyable illustrative fragment explicitly, regenerate its packaged payload projection and `standards/catalog.md` `unadvertised` row, and record the final digest. T15 owns only catalog/default activation.
  - **T13.4 Verify GREEN** — run CLI Docs package/provider/adoption and TOML corpus tests.
  - **T13.5 REFACTOR** — reuse extension/path containment primitives and retain one generated usage surface.
  - **T13.6 Verify Task** — run package/graph/schema/rendered-catalog/payload-projection/docs gates; commit with IDs.

### Phase P3: Integration and Candidate

#### T14: Add candidate-bound release consistency

- **goal:** Prevent a release commit whose release-facing documentation and default-package claims do not match its exact metadata and candidate catalog. · **phase:** P3 · **depends_on:** [T8, T9, T10, T11, T12, T13] · **requirements:** [FR-003, FR-019, NFR-009, IR-004] · **priority:** must
- **files:** release/package consistency validation source/tests/workflow as needed; root `README.md` and `UPGRADING.md`; catalog-derived inputs/fixtures for `standards/README.md` and every mutable Markdown document directly under each consumer-family directory; editable current-prose corrections in `standards/project-spec/README.md` and `standards/project-spec/adopt.md`
- **acceptance:** fixtures prove the gate fails independently on stale project version, release-current pins, package/default rows, family-level version references, versioned links, enable commands, internal package references, unclassified historical examples, or broken current-package links; for every mutable `standards/{family}/*.md` document, each reference to that family's version must equal the candidate-catalog default or carry an asserted explicit historical classification, with expected current values derived from the catalog rather than literals; deliberately historical references/permalinks remain classified and preserved; catalog/index regeneration is byte-idempotent; README’s current Standard Bundle Authoring reference is corrected from 2.4 to 2.5; the two stale Project Specification enable commands are corrected from 1.2 to its existing default 1.4; an exact release-commit fixture passes. This task does not bump the repository version or edit activation-owned successor-family documents; its Project Specification correction is release-current documentation owned by T14, while T15 assembles the four successor activations (TC-T14-001, TC-T14-002).
- **sub-tasks:**
  - **T14.1 RED** — add fixture commits/documents with each independent stale field, including separate current-reference cases in family `README.md`, `adopt.md`, `agent-summary.md`, and another direct family-level document plus an explicitly historical reference whose classification is removed; add release-current/historical classification, non-idempotent projection, current-repo SBA, and stale Project Specification command regressions.
  - **T14.2 Verify RED** — prove the current checker misses the historical #36 mismatch, current 2.4 SBA prose, and the two Project Specification 1.2 enable commands.
  - **T14.3 GREEN** — derive release-facing facts from supplied candidate metadata/catalog; scan every mutable Markdown document directly under every consumer-family directory and require each version, versioned link, and enable command for that family either to equal its candidate-catalog default or to carry an asserted explicit historical classification. Add the pre-tag gate, preserve classified history such as Python Tooling's build-backend timeline, correct the current SBA reference, and correct the two Project Specification enable commands to 1.4 without assembling release-version bytes or editing successor-family activation prose.
  - **T14.4 Verify GREEN** — run passing exact-candidate fixtures and failing stale/misclassified fixtures.
  - **T14.5 REFACTOR** — centralize release-fact extraction and keep historical immutable docs out of current-candidate assertions.
  - **T14.6 Verify Task** — run release/package/docs tests, workflow syntax, Ruff, and BasedPyright; commit with IDs.

#### T15: Activate successors and prove migrations

- **goal:** Select the four successors together, complete the release commit bytes, and prove package, transform, migration, issue-ledger, and consumer-outcome compatibility before Opus review. · **phase:** P3 · **depends_on:** [T2, T3, T4, T5, T6, T7, T8, T9, T10, T11, T12, T13, T14, T19] · **requirements:** [FR-012, FR-015, FR-019, FR-021, NFR-001, NFR-004, NFR-005, NFR-008, IR-005, DR-002] · **priority:** must
- **files:** family manifests, `.standards/config.toml`, canonical and generated catalog/projection artifacts including `standards/catalog.md`, `pyproject.toml`, `uv.lock`, `CHANGELOG.md`, root `README.md`, `UPGRADING.md`, `standards/README.md`, affected current-reference family-level Markdown documents including each successor family's `README.md`, `adopt.md`, and `agent-summary.md`, status/handoff candidate-preparation state, current-train ledger rows, cross-package/migration/coherence/outcome tests, and catalog-identity fixtures including `tests/package_contract/test_current_catalog_activation.py`
- **acceptance:** defaults select Python Tooling 1.9, Markdown Tooling 1.9, Agent Handoff 1.5, and CLI Documentation 1.4; the standards index and all affected current-reference family-level Markdown documents name those defaults and carry matching versioned links and enable commands where applicable, while every other direct family-level version reference retains an asserted historical classification; expectations derive from the candidate catalog; `standards/catalog.md` changes the staged successor rows from `unadvertised` to `default` and the predecessor rows from `default` to `retained`; after pre-GREEN analysis supports MINOR, the release commit carries version 5.9.0, regenerated `uv.lock`, dated changelog, release-current documentation, and classified historical references; `main` is an ancestor and the commit is fast-forwardable without tree change; every predecessor digest is unchanged; fresh/all-predecessor migration matrices include T19's direct Python transforms and detect loss of an effective gate as incompatibility, an unmigrated exact Markdown Tooling 1.8 `@v5` workflow fixture and `latest` outcome matrices converge without pass-to-fail results; catalog-identity fixtures derive package counts, versions, digests, roles, and migration predecessors from family/catalog/migration authorities rather than literals; the activated root uses explicit `MD060: false`, coherence stays green, and the #27 literal fixture is unchanged; every current-train issue has a committed executable ledger row; a preliminary wheel/sdist digest and complete candidate gate supply exact evidence for T16 (TC-T15-001 through TC-T15-004).
- **sub-tasks:**
  - **T15.1 RED** — add exact default-selection, candidate-derived standards index plus complete direct family-level current/historical reference consistency, generated-catalog role transition, predecessor-digest, fresh-adoption, all-predecessor migration, repeated-reconcile, exact-selection/`latest` pass-fail, activated coherence, current-train ledger completeness, release-byte, ancestry/fast-forward, and catalog-identity derivation cases.
  - **T15.2 Verify RED** — confirm all four family-indexed consumer successors, with complete adoption guides, pass package/integrity/graph/schema/provider-unit/rendered-catalog/payload-projection gates while canonical catalogs omit them and root `latest` still resolves 1.8/1.8/1.4/1.3; prove final activation is one indivisible catalog-only four-package transition.
  - **T15.3 GREEN** — as the sole owner of canonical `catalogs/5.toml` edits, add the four already-final successor identities/digests as defaults and change their four prior defaults to retained without changing any payload/family byte; regenerate the resulting packaged catalog projection and `standards/catalog.md` role column, verify the unchanged payload projection, and validate final migrations/providers together. Update the standards index and all current-reference family-level Markdown documents for the four successor families from candidate-catalog-derived defaults, including their `README.md`, `adopt.md`, and `agent-summary.md`, while preserving explicitly classified historical references. Add current-train ledger rows; after the planned MINOR gate remains satisfied, assemble the release commit with version 5.9.0, regenerated `uv.lock`, dated changelog, and release-current docs; do not tag, publish, close issues, or alter hosted state.
  - **T15.4 Verify GREEN** — run package, graph, schema, projection, migration, adoption, coherence, exact/default-track outcome, ledger, release-consistency, ancestry, and complete preliminary candidate gates; build and record preliminary wheel/sdist digests for T16.
  - **T15.5 REFACTOR** — remove duplicate fixtures; replace catalog payload-count arithmetic, inlined versions/digests/roles, and hand-listed migration predecessors with values derived from family manifests, catalog entries, and declared migration endpoints. This derivation is an exit condition, not optional cleanup.
  - **T15.6 Verify Task** — run all package/control-plane/coherence/docs/static gates; commit with IDs.

#### T16: Run blocking Opus candidate audit

- **goal:** Adversarially review the exact assembled release commit and candidate evidence against the specification, plan, issues, invariants, immutable-byte proof, and candidate diff. · **phase:** P3 · **depends_on:** [T15] · **requirements:** [NFR-007] · **priority:** must
- **files:** ignored review bundle/evidence; master-plan discovered tasks if required
- **acceptance:** Opus receives the exact release commit, preliminary artifact digests, complete gate evidence, requirement/test matrix, issue corpus, ledger, and immutable-byte proof in a bounded read-only bundle; the verified result binds that commit/artifact evidence; every Critical/High finding is fixed through its owning task and the T15-T16 sequence restarts, or is explicitly dispositioned by the owner (TC-T16-001).
- **sub-tasks:**
  - **T16.1 RED** — assemble the exact commit/diff, issue corpus, spec-plan-test matrix, test output, wheel/sdist and payload digests, ledger evidence, and known-risk register; mark the audit gate unsatisfied.
  - **T16.2 Verify RED** — verify the bundle is complete, contains no secrets, and points to the exact candidate commit.
  - **T16.3 GREEN** — run one substantive Claude Opus adversarial review; route discovered work to the earliest owning task, reassemble under T15, and begin a new exact-candidate review round as needed.
  - **T16.4 Verify GREEN** — rerun review after fixes until no unresolved Critical/High finding remains.
  - **T16.5 REFACTOR** — collapse duplicate evidence while preserving exact commands/commit/digests and minority concerns.
  - **T16.6 Verify Task** — validate the final audit disposition table and commit only durable plan/changelog/handoff consequences.

#### T17: Qualify the exact release commit and stop unpublished

- **goal:** Replay the authoritative gate against the unchanged Opus-reviewed release commit and prove its exact artifact bytes without publishing or changing tracked files. · **phase:** P3 · **depends_on:** [T16] · **requirements:** [FR-003, FR-020, FR-021, NFR-004, NFR-005, NFR-006, NFR-007, NFR-008, NFR-009, IR-004, IR-005, DR-002] · **priority:** must
- **files:** ignored/ephemeral candidate gate logs and artifact staging only; the tracked release commit assembled in T15 must not change
- **acceptance:** HEAD equals the Opus-reviewed release commit; `main` remains its ancestor and landing is fast-forwardable; rebuilding produces the same wheel/sdist digests reviewed in T16; one extracted wheel supplies all installed-authority package/control-plane/coherence/handoff tests with its path first on `PYTHONPATH`; the complete static/test/compatibility/performance/audit/package/graph/schema/projection/coherence/docs/handoff gate passes; exact/default-track and full outcome-aware seed/current-train ledgers pass; predecessor digests match the T1 v5.8.0 authority; Node dependency pins match the T1 baseline; release consistency and `packages check-release --baseline v5.8.0` report the exact candidate/MINOR result including IR-004 schema changes; `git status --porcelain` is empty, HEAD matches the recorded T15/T16 commit, and no tag, release, issue, or hosted state changed (TC-T17-001, TC-T17-002).
- **sub-tasks:**
  - **T17.1 RED** — instantiate the candidate checklist with every §11 command, exact T15/T16 commit and digests, and mark any missing/mismatched evidence as failure.
  - **T17.2 Verify RED** — confirm no stale build directory, source checkout, changed commit, missing ledger row, or non-fast-forward landing can satisfy qualification.
  - **T17.3 GREEN** — rebuild wheel/sdist from the unchanged release commit, extract the wheel, run the full gate, and retain evidence outside tracked scope.
  - **T17.4 Verify GREEN** — repeat release consistency, release classification including IR-004, payload/artifact and Node-pin baselines, outcome-aware issue ledgers, plan/spec transpose validation, handoff conformance, ancestry, empty `git status --porcelain`, and recorded-HEAD checks at the exact commit.
  - **T17.5 REFACTOR** — remove transient build output from tracked scope and consolidate only external/ignored evidence pointers without changing HEAD.
  - **T17.6 Verify Task** — prove exact reviewed commit, reproducible artifact digests, complete green gate, clean worktree, and unpublished/unchanged hosted state; stop for explicit release authorization.

### Phase P4: Authorized Release

#### T18: Publish and close issues after authorization

- **goal:** Release the verified correction train and close only issues proven by hosted/artifact evidence. · **phase:** P4 · **depends_on:** [T17] · **requirements:** [FR-020, NFR-005, NFR-006, NFR-007, DR-002] · **priority:** must
- **files:** final release publication metadata plus status/deployed/handoff/session records; no new version bump
- **preconditions:** explicit owner release authorization naming the T17 commit and wheel/sdist digests; no unresolved Critical/High Opus finding; T17 exact commit/digests unchanged; the live issue set matches committed ledger rows for every issue proposed for closure.
- **acceptance:** the exact release commit lands on `main` unchanged and without a merge-generated tree/commit substitution; signed immutable and moving-major tags identify that commit; hosted workflows are green; downloaded wheel/sdist match qualified digests/content; #32 and #35-#49 each receive exact closing evidence and close only when their committed row and acceptance are proven; a subsequent closeout commit may update status/deployed/handoff without altering the tagged/released bytes; required main/testing parity follows release policy (TC-T18-001, TC-T18-002).
- **failure handling:** stop after any failed external step and record the exact partial hosted state before further mutation. No issue closes until hosted workflows and downloaded-artifact parity are both proven. Tag, release, or asset remediation requires owner direction under `meta/versioning.md`; never delete or move immutable release state as an autonomous workaround.
- **sub-tasks:**
  - **T18.1 RED** — verify authorization, candidate identity/digests, live-to-ledger issue parity, and unchanged fast-forward landing; any absence or mismatch is a hard stop.
  - **T18.2 Verify RED** — confirm release/issue operations cannot begin from an unauthorized, changed, non-fast-forward, or ledger-incomplete candidate.
  - **T18.3 GREEN** — execute `meta/versioning.md` externally mutating requirements 0-2 against the exact qualified release commit, publish, monitor hosted workflows, verify downloaded artifacts, and close proven issues with concise evidence.
  - **T18.4 Verify GREEN** — prove tag, release, artifact, workflows, issue states, and required branch parity.
  - **T18.5 REFACTOR** — reconcile final changelog/status/deployed/handoff truth without altering released bytes.
  - **T18.6 Verify Task** — run final handoff/docs checks, commit/push authorized closeout, prove clean worktree and remote parity, then close the master plan.

### Appended P2/P3 Prerequisite

#### T19: Add generic direct package-config transforms

- **goal:** Add the minimum generic, explicitly opted-in direct package-upgrade configuration transform and use it to preserve Python Tooling's effective performance lane from every qualifying family-indexed predecessor into 1.9. · **phase:** P2/P3 prerequisite · **depends_on:** [T5, T8] · **requirements:** [FR-017, FR-019, FR-021, NFR-002, NFR-004, NFR-008, IR-004, IR-005] · **priority:** must
- **files:** `src/project_standards/package_contract/payload.py`; generated `src/project_standards/schemas/standard-payload.schema.json`; `src/project_standards/control_plane/resolution.py`, `planner.py`, `schemas.py`, `config_edit.py`, and bounded nested-inline-leaf support in `adapters/toml.py`; generated `src/project_standards/schemas/reconciliation-plan.schema.json`; `codec.py` only if required to reuse the canonical TOML scalar renderer; Python Tooling 1.9 `payload.toml`, provider, family digest, packaged projection, and generated catalog counterpart; focused payload/schema/provider/planner/config-edit tests, new `tests/control_plane/test_package_config_upgrade.py`, Python Tooling 1.9 contract tests, and one package-compatibility lifecycle test. `cli.py`, `executor.py`, lock schemas, catalog policy, released payloads, dependencies, release files, and other package providers are excluded.
- **interface/data:** add one default-absent configuration-transform JSON-pointer allowlist to an automatic direct package-to-package migration that uses its existing provider binding. Package validation rejects the declaration unless shared direct-property schema nodes retain the same validation keywords, allowing target-added properties, direct scalar-enum supersets, and default/annotation differences only at changed pointers; other widening remains WH-007. Planner first proves unchanged raw config target-valid, then builds the bounded source projection: recurse through direct object `properties`, omit target-only keys and direct target-only enum scalars as whole leaves, never filter collections per element, and preserve other values atomically. It resolves source-effective config through the existing full validator/default resolver, invokes one target provider through the existing runner, binds output to the invocation identity/no-legacy-claims, confines the semantic diff to declared pointers, requires introduced leaves under both schemas, complete output under the target schema, output projection under the source schema, and provider idempotence. Typed value-redacted transform evidence advances reconciliation-plan schema 1.2 to 1.3. Preview and `--check` are read-only; check reports ordinary drift. Apply re-plans under the ordinary writer lock and publishes one lexical config action before dependent artifacts and lock. Existing package evidence without an exact authoritative applied version, including inferred-only evidence, and more than one applicable transform fail closed.
- **acceptance:** synthetic generic fixtures prove valid opt-in, missing/wrong provider and invalid edge rejection, exact pointer minimality with legitimate empty diffs, complete-default/target-only-key-change rejection, bounded direct-property/direct-enum projection, whole-leaf omission with source-default resolution, no per-element filtering, declaration-time rejection of array/reference/combinator/range/type/rename/relocation widening, source/target validation, same-change successor-only key and enum success, provider identity/failure/invalid-output rejection, provider idempotence using a source projection recomputed from candidate output, typed no-value preview/check/apply and direct programmatic parity, stale-config CAS, unknown/inferred applied-version recovery guidance, multiple-transform rejection, config-first order, post-config-publication fault/resume, and second-pass fixed point. The candidate emits reconciliation-plan schema 1.3; decoders recognize 1.1 and 1.2 as prior versions and reject unsupported versions. A raw target-invalid consumer value on an opted-in edge uses the existing ordinary configuration diagnostic and remedy, not a transform finding. Fresh adoption, same-version selection, non-opted direct edges, manual edges, and indirect/multi-hop paths each prove no transform invocation. Lexical tests cover nested inline, dotted, and table forms without unrelated-byte normalization. Python Tooling tests derive the qualifying predecessor set from the family manifest and source schemas, require each member and only each member to have a direct 1.9 edge limited to `/ci/performance`, require package graph and declaration-eligibility validation to admit that exact edge set, and compare source-rendered artifacts/gates before and after: fresh 1.9 stays false and invokes no transform; enabled absent states materialize true; explicit true/false is unchanged; disabled CI materializes false without changing enabled or rendered behavior; same-change `build_backend = "none"` and new Ruff/coverage options remain unchanged; unrelated config bytes and target defaults remain absent; explicit true retains pytest exit 5. One source/extracted-wheel case proves identical preview, final config, artifacts, lock, and fixed point (TC-T19-001 through TC-T19-003).
- **scope checkpoints:** before RED, record the exact base, listed production/tests, C-009 invariants, and excluded paths. Before GREEN and before Verify Task, inspect name-status/stat/full diff against that allowlist; reject any package-ID branch, second transform composition, new CLI/provider operation, arbitrary patch language, multi-hop execution, whole-file normalization, transaction redesign, dependency, released-payload edit, or unrelated refactor. Generated schema/projection/catalog/family counterparts are allowed only when directly caused by the declared contract or Python Tooling 1.9 bytes.
- **sub-tasks:**
  - **T19.0 CHARACTERIZE** — verify T5's reconciliation-plan 1.2 and shared redaction projection as prerequisites; prove current direct version declarations lose providers during resolution and the staged V4 test bypasses unified upgrade; derive the qualifying Python predecessor set; confirm package graph and bounded declaration-eligibility validation admit the exact direct incoming edge set; and identify the existing `ControlAction`/`PlannedTarget`, executor tuple-order publication and writer-lock re-plan, and ordinary CLI drift path that carry the config action without `executor.py` or `cli.py` changes. Reproduce nested-inline TOML leaf limitations and current absence of typed config evidence. If any qualifying predecessor fails graph or declaration eligibility, stop before T19 RED and return to SPEC-VAIC under AW-005; do not narrow the set or substitute multi-hop behavior.
  - **T19.1 RED** — add the exact generic declaration/provider/lifecycle, target-only same-change options, typed evidence, lexical config, and Python qualifying-predecessor/five-state/source-wheel tests in the acceptance matrix; keep legacy migration suites unchanged.
  - **T19.2 Verify RED** — confirm failures identify the absent opt-in contract and engine lifecycle, while fresh 1.9, predecessor bytes, and unrelated transitions stay green.
  - **T19.3 GREEN** — implement only the declaration parser/schema, target-admissibility plus bounded direct-property/direct-enum source projection before artifact resolution, existing-provider invocation, pointer/introduced-leaf-schema/target/idempotence validation, typed value-redacted evidence, bounded lexical config plan action, Python Tooling 1.9 provider/direct declarations, and caused generated counterparts.
  - **T19.4 Verify GREEN** — run focused package/control-plane/compatibility tests, injected fault/resume, CLI/programmatic parity, and repeated fixed-point checks.
  - **T19.5 REFACTOR** — share only existing schema resolution and TOML rendering primitives inside the verified surface; do not introduce a general patch language, multi-transform compositor, or new transaction abstraction.
  - **T19.6 Verify Task** — repeat scope review; run Ruff, BasedPyright, package/graph/schema/projection/catalog gates, focused and complete required tests, and one exact extracted-wheel source/parity gate; commit with IDs and block T15 until green.

## 9. Integration, Risks, and Decisions

### 9.1 Integration Sequence

1. Establish shared external-tool oracles, then fix independent engine defects.
2. Build each immutable successor from its released predecessor.
3. Complete T19's generic direct-edge transform and seal Python Tooling 1.9 bytes before activation.
4. Add the candidate-bound release gate.
5. Activate successors together; complete version/lock/changelog/release-document bytes; run cross-package, regression-ledger, exact/default-track, and preliminary full candidate gates.
6. Obtain a blocking Opus audit bound to the exact assembled release commit and artifact digests.
7. Rebuild and qualify the unchanged commit and artifacts, then stop unpublished for release authorization.

### 9.2 Risks

| ID | Risk | Impact | Mitigation | Owner |
| --- | --- | --- | --- | --- |
| R-001 | #47 does not reproduce under pinned tools. | med | T9 characterizes actual selected files and adds a guard; no speculative normalization. | T9 |
| R-002 | Context-aware JSON formatting rewrites consumer bytes. | high | Lexical splice remains authoritative; property-style preservation cases bound the change. | T3 |
| R-003 | Restore becomes an unsafe generic repair path. | high | Exact declared target, exclusive whole-file ownership, preview, digests, containment, and mutual exclusion. | T7 |
| R-004 | Fresh performance default changes migrated behavior. | high | T19 derives every predecessor edge, limits changes to `/ci/performance`, and proves all effective states; explicit true retains pytest exit 5. | T8, T19 |
| R-005 | Diagnostic precision leaks consumer secrets. | high | Shared structural redaction schema and adversarial secret fixtures. | T5 |
| R-006 | Release docs drift after candidate validation. | high | Gate runs at exact final candidate commit immediately before tag and again in T17/T18. | T14, T17, T18 |
| R-007 | Correction train conflicts with the MCP hold. | high | No T1 execution without explicit owner exception; release has a second authorization gate. | Owner |
| R-008 | A ledger refactor hides or weakens a closed-issue regression. | high | Stable regression IDs, executable-reference validation, DR-002 amendment evidence, and exact baseline/candidate replay. | T1, T15, T17 |
| R-009 | Landing or closeout changes the qualified release tree. | high | T15 ancestry proof, T17 clean unchanged commit, T18 unchanged landing, and automatic rebuild/re-review/reauthorization on any mismatch. | T15-T18 |
| R-010 | Markdown ownership assertion turns red between successor creation and activation. | high | T11 tests predecessor style-any and successor explicit-false forms; T15 activates and rechecks without changing the #27 fixture. | T11, T15 |
| R-011 | A shared `@v5` reusable-workflow edit regresses released Markdown Tooling selections. | high | T9 characterizes provider, workflow-input, shell/cwd, and tool-dialect causes; workflows stay unchanged unless AW-004 is explicitly dispositioned; NFR-008 retains an unmigrated 1.8 fixture. | T9, T15, Owner |
| R-012 | A generic transform freezes unrelated defaults, introduces predecessor-invalid config, rejects valid same-change successor options, or cannot resume after interruption. | high | Pointer allowlist, exact minimality, source-declared projection, introduced-leaf dual-schema validity, target validation, provider idempotence, config-first fault/resume, same-change target-only success, and default-freezing rejection are T19 exit conditions. | T19 |

### 9.3 Governing Design Decisions

| Spec ID | Plan consequence |
| --- | --- |
| D-001 | Keep one correction train and one exact candidate proof surface across engine, successor, integration, and release phases. |
| D-002 | SPEC-VAIC governs; every task/test cites FR/NFR/IR/DR IDs directly and this plan introduces no parallel requirement namespace. |
| D-003 | Restore remains separate from `--repair-state` and ordinary reconcile apply. |
| D-004 | Production composition remains lexical/semantic; pinned external formatting tools stay test oracles. |
| D-005 | Markdown Tooling 1.9 renders explicit `MD060: false`; T11 keeps predecessor and successor coherence states valid with Prettier as table-layout authority. |
| D-006 | CLI Documentation references one consumer-owned usage index rather than generating multiple CLI artifacts. |
| D-007 | The committed issue-to-proof ledger, not chat or live GitHub during normal tests, is the durable regression authority. |
| D-008 | T19 uses one generic explicit direct-edge provider opt-in inside ordinary reconciliation; Python-specific core logic, implicit historical providers, a patch language, multi-hop execution, and multi-transform composition are prohibited. |

## 10. Open Questions

| ID | Question | Blocking? | Owner | Current assumption |
| --- | --- | --- | --- | --- |
| OQ-001 | Has the owner granted the MCP-hold exception for this train and bounded T19? | no; resolved | Owner and implementer | Yes. Option 1 and autonomous convergence are authorized; amended spec/plan validation and independent reviews remain T19 pre-GREEN quality gates, not new owner-approval gates. |
| OQ-002 | Does refreshed pinned-tool evidence confirm #47’s exact `dir/**` divergence? | yes at T9 GREEN | Implementer | Characterize first; do not pre-commit to normalization. |
| OQ-003 | Does the owner authorize the exact T17 candidate for release? | yes before T18 | Owner | No; T17 stops unpublished. |

## 11. Final Verification

- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run basedpyright`
- `CORRECTION_ARTIFACT_OUT="$(mktemp -d)"`
- `CORRECTION_WHEEL_RUNTIME="$(mktemp -d)"`
- `uv build --wheel --sdist --out-dir "$CORRECTION_ARTIFACT_OUT"`
- Record `sha256sum "$CORRECTION_ARTIFACT_OUT"/project_standards-*`.
- `python -m zipfile -e "$CORRECTION_ARTIFACT_OUT"/project_standards-*.whl "$CORRECTION_WHEEL_RUNTIME"`
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
- `uv run project-standards standards render-catalog --root . --check`
- `uv run project-standards packages check-release --root . --baseline v5.8.0`
- `npm ci`
- `uv run pytest tests/coherence -v`
- `npm run format:check`
- `npx markdownlint-cli2`
- `uv run project-standards validate`
- `uv run project-standards spec validate docs/specs/2026-07-26-v5-adoption-integrity-correction-train-spec.md`
- `uv run project-standards spec lint --strict docs/specs/2026-07-26-v5-adoption-integrity-correction-train-spec.md`
- `uv run scripts/plan.py validate docs/plans/2026-07-25-v5-adoption-integrity-correction-train-plan.md`
- `uv run project-standards agent-handoff validate --repo .`
- `uv run project-standards agent-handoff drift-check --repo .`
- `uv run project-standards agent-handoff size-report --repo .`
- `uv run project-standards agent-handoff shape-check --repo .`
- `git diff --check`
- For every T1-T17 and T19 commit, verify the recorded task base, allowed change surface, pre-GREEN scope result, pre-Verify-Task scope result, and any generated/cross-file counterpart justification are present in the ephemeral evidence.
- At each phase boundary, verify the completed task commits remain within SPEC-VAIC scope, constraints, and non-goals; unresolved scope exceptions block the next phase.
- Require `git status --porcelain` to produce no output.
- Compare `git rev-parse HEAD` with the exact T15/T16 recorded release commit.
- Audit every SPEC-VAIC FR/NFR/IR/DR and TC row bidirectionally against exact passing evidence; any missing Must evidence blocks T17.
- Run every applicable committed seed/current-train ledger row against its declared exact environment; compare the live issue set read-only only at release closeout.
- Replay the exact-selection and `version = "latest"` outcome matrices and prove neither lint nor format scope widened for existing corpora.
- Replay family-derived qualifying Python Tooling predecessor-to-1.9 transforms through source and extracted wheel; assert exact `/ci/performance` diffs, fresh bypass, introduced-leaf dual-schema validity, same-change successor-option success, idempotent fault recovery, unchanged unrelated config, and no effective-gate loss.
- Confirm predecessor payload digests match the T1 v5.8.0 tag/published-wheel ledger even if working-tree family/catalog digests were changed self-consistently.
- Confirm `package.json` and `package-lock.json` dependency pins match the T1/v5.8.0 baseline.
- Confirm `main` is an ancestor of the exact clean release commit, its wheel/sdist digests match T16 evidence, and it can land unchanged.
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
| Package migration declaration | automatic edge metadata; unified resolution does not invoke package-version providers | direct automatic edge may opt in one provider plus changed-pointer allowlist | Default absent; non-opted and legacy behavior unchanged. |
| Reconcile config action | config changes are not part of package-version reconcile planning | one pointer-limited, introduced-leaf dual-schema-valid, target-valid, idempotent lexical `.standards/config.toml` action with typed value-redacted plan evidence | Preview/check read-only; apply uses existing lock/re-plan/CAS and resumable config-first ordering. |
| Markdown Tooling config | 1.8 | 1.9 convergent file-set/caller/lint contract | 1.8 immutable. |
| Agent Handoff package | 1.4 | 1.5 exclusion/adoption guidance | 1.4 immutable. |
| CLI Documentation config | 1.3 single generated usage | 1.4 optional referenced usage index | Default remains single generated usage. |
| Release consistency | incomplete prose checks | exact candidate metadata/catalog/prose gate | Additive pre-tag failure gate. |

## Appendix B. Test Matrix

| Test ID | Requirement | Task | Exact target/evidence | Type |
| --- | --- | --- | --- | --- |
| TC-T1-001 | NFR-001 | T1 | Shared lock-derived Prettier/markdownlint oracle contract tests | contract |
| TC-T1-002 | FR-002, FR-015 | T1 | Live issue refresh plus minimal JSON/Markdown/exclusion/caller reproductions | characterization |
| TC-T1-003 | NFR-005, DR-002, C-007 | T1 | Outcome-aware seed ledger, proof-symbol digests, negative anti-weakening/amendment cases, exact 5.8.0 execution, and #21 guard | regression/audit |
| TC-T1-004 | NFR-008, NFR-009 | T1 | Exact-selection/`latest` 5.8.0 outcome baselines and planned-change release classification | compatibility |
| TC-T1-005 | NFR-004, C-001 | T1 | v5.8.0-authoritative predecessor digest ledger and self-consistent working-tree tamper rejection | compatibility/security |
| TC-T1-006 | C-006 | T1 | v5.8.0 Node dependency-pin baseline and unauthorized pin-drift rejection | scope/security |
| TC-T2-001 | FR-001, IR-001 | T2 | Enumerated directory/missing/named-file/bare/config-only cases including `project-standards fix` | regression |
| TC-T3-001 | FR-002, NFR-001 | T3 | Parametrized JSON/JSONC composition-to-Prettier fixed point | property/regression |
| TC-T3-002 | FR-002, NFR-008 | T3 | Semantic, unrelated-byte, and previously-passing outcome preservation across splice contexts | property/security |
| TC-T4-001 | FR-007, NFR-008 | T4 | Mixed keyed/unkeyed TOML preservation and baseline/candidate outcome | regression/compatibility |
| TC-T4-002 | FR-007 | T4 | Duplicate selected identity and non-table rejection | contract |
| TC-T5-001 | FR-018, NFR-002, IR-004 | T5 | TOML line/column, cause chaining, schema 1.2, renderer parity, and redaction | regression/security |
| TC-T5-002 | FR-013, NFR-002, IR-004 | T5 | Handoff path/locus/measure/limit, envelope 1.1, prior-version, and rendering contract | contract |
| TC-T5-003 | FR-013, FR-018, NFR-002 | T5 | Adversarial raw-value/content non-disclosure corpus | security |
| TC-T6-001 | NFR-003 | T6 | Error plan plus `--apply` returns nonzero with unchanged tree and no executor entry | regression/security |
| TC-T6-002 | NFR-003 | T6 | Warning-only conflict-free apply retains current transaction behavior | compatibility |
| TC-T7-001 | FR-004 | T7 | Ownership-sensitive pre-adoption conflict hints | regression |
| TC-T7-002 | FR-005, IR-002, DR-001 | T7 | Divergent-current overwrite, absent-current recreate, no-op preview/apply, and repeated reconcile | integration |
| TC-T7-003 | FR-005, NFR-002, IR-002, DR-001 | T7 | State/digest races, absent lock, one shared redaction projection, path/ownership/symlink/glob/directory rejection | security |
| TC-T8-001 | FR-008 | T8 | Ruff/coverage option schema, canonical rendering, validation, and explicit rule suppression | contract |
| TC-T8-002 | FR-009 | T8 | Backend none omits build-system and retains development tooling | regression |
| TC-T8-003 | FR-017 | T8 | Fresh default false and explicit true exit-5 behavior | integration |
| TC-T8-004 | FR-017, FR-019, NFR-004 | T8 | Uncatalogued-stage package/fresh-default surface, retained V4 migration behavior, and immutable 1.8 bytes; no claim of unified package-upgrade proof | migration/package |
| TC-T9-001 | FR-015, NFR-001, NFR-008 | T9 | Provider/workflow/shell/tool causal matrix plus unmigrated 1.8 `@v5` outcomes and no scope widening | integration |
| TC-T9-002 | FR-015, FR-019, NFR-004 | T9 | Non-widening normalization or no-divergence guard plus Markdown Tooling 1.8 digest | contract |
| TC-T10-001 | FR-006 | T10 | Both caller permissions and reusable-workflow compatibility | contract |
| TC-T10-002 | FR-016, FR-019, NFR-001, NFR-004 | T10 | Long caller inputs pass Prettier/reconcile; immutable Markdown Tooling 1.8 | regression |
| TC-T11-001 | FR-012, NFR-001 | T11 | Table/directive/underscore repeated Prettier-plus-lint fixed point | regression |
| TC-T11-002 | FR-012, FR-019, NFR-004 | T11 | Executable normal/guarded autofix docs and immutable Markdown Tooling 1.8 | documentation |
| TC-T11-003 | FR-012 | T11 | Predecessor/successor split-ownership coherence, explicit MD060 false, and unchanged #27 fixture | coherence |
| TC-T12-001 | FR-011, FR-019, NFR-004 | T12 | Locked-file independent-tool exclusion contract and Agent Handoff 1.4 digest | documentation |
| TC-T13-001 | FR-014 | T13 | Successor/default copyable TOML corpus plus illustrative markers and immutable known limitations | corpus |
| TC-T13-002 | FR-010, FR-019, IR-003, NFR-004 | T13 | Usage-index default/path/transition/security matrix and CLI Documentation 1.3 digest | contract |
| TC-T14-001 | FR-003 | T14 | Stale/misclassified project/package/default/current-link fixture failures | release |
| TC-T14-002 | FR-003, FR-019, NFR-009, IR-004 | T14 | Exact candidate fixture, idempotent projection, historical carve-outs, IR-004 classification, and SBA 2.5 guard | release |
| TC-T15-001 | FR-012, FR-019, FR-021, NFR-001, IR-005 | T15 | Catalog-only four-successor activation, defaults, generic transforms, migrations, coherence, and fixed point | integration |
| TC-T15-002 | FR-019, NFR-004 | T15 | Every predecessor digest and release-commit package projection | compatibility |
| TC-T15-003 | FR-015, NFR-008 | T15 | Unmigrated exact-1.8 and migrated-`latest` outcome matrix with no lint/format widening | compatibility |
| TC-T15-004 | NFR-005, DR-002 | T15 | Complete executable current-train ledger rows before candidate review | regression/audit |
| TC-T16-001 | NFR-007 | T16 | Verified exact-commit/artifact Opus review and Critical/High dispositions | adversarial review |
| TC-T17-001 | NFR-006 | T17 | Reproducible wheel/sdist and one extracted-wheel complete local gate | release candidate |
| TC-T17-002 | FR-003, FR-020, FR-021, NFR-004, NFR-005, NFR-006, NFR-007, NFR-008, NFR-009, IR-004, IR-005, DR-002, C-006, C-007, C-009 | T17 | Exact clean commit, classification, Node/payload baselines, transform lifecycle, outcome-aware ledgers, compatibility, Opus, ancestry, and unpublished checks | audit |
| TC-T18-001 | FR-020, NFR-006 | T18 | Explicit authorization, unchanged landing, signed tags/release, hosted workflows, artifact parity | release |
| TC-T18-002 | FR-020, NFR-005, NFR-007, DR-002 | T18 | Live-to-ledger issue parity, per-issue evidence, Opus blockers, closeout, and branch parity | closeout |
| TC-T19-001 | FR-017, FR-021, C-009 | T19 | Opt-in/direct-automatic/provider/pointer schema contract; bounded direct-property/direct-enum source projection, whole-leaf omission/source-default resolution, no per-element filtering, and declaration-time unsupported-widening rejection; introduced-leaf source/target validity; ordinary ERR-008 routing for raw target-invalid consumer config; target-only/default-freezing change rejection; non-idempotent and multi-transform rejection; fresh, same-version, non-opted, manual, and indirect/multi-hop bypass | contract/security |
| TC-T19-002 | FR-017, FR-021, NFR-002, IR-004, IR-005 | T19 | Typed value-redacted preview/check/apply/programmatic lifecycle; candidate schema 1.3 emission, 1.1/1.2 prior recognition, and unsupported-version rejection; exact possibly-empty pointer diff; inline/dotted/table lexical preservation; config-first order; stale/unknown/inferred authority; provider failure/invalid output; fault/resume; and second-pass fixed point | integration/recovery |
| TC-T19-003 | FR-017, FR-019, FR-021, NFR-004, NFR-008, IR-005 | T19 | Family-derived qualifying-predecessor/five-state/fresh-bypass matrix, same-change successor-only key/enum success, source-rendered behavior equivalence, and source/extracted-wheel equivalent config/artifacts/lock/fixed point | compatibility |

## Appendix C. Deferred Work

| Item | Reason deferred | Follow-up trigger |
| --- | --- | --- |
| Directory walking for frontmatter validation | Not required to fix #32 and changes selection semantics. | Separate approved feature request. |
| General damaged managed-file recovery | Exact whole-file recovery is the safe bounded issue scope. | Separate recovery specification with ownership/precondition model. |
| Hypothesis dependency | Existing generated parametrization is sufficient for this correction train. | Owner-approved testing dependency proposal. |
| Generated multi-CLI artifacts/CI | #42 can be satisfied by a referenced consumer-owned index. | Concrete need for multiple generated artifact identities. |
| Automatic third-party `.agents/` exclusion detection | Documentation plus current Python Tooling defaults address #43. | Evidence that a managed provider can safely own another tool’s config. |
| Multiple package-config transforms in one plan | FR-017 needs one package; ordering/merge semantics would enlarge the transaction contract. | A second package requires an opted-in transform and an approved composition design. |
