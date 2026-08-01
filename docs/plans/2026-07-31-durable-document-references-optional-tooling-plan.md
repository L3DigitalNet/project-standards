---
title: 'Durable Document References Optional Tooling Implementation Plan'
slug: 'durable-document-references-optional-tooling'
size: full
status: active
source: 'SPEC-GSF3'
spec_ref: 'docs/specs/2026-07-31-durable-document-references-optional-tooling-spec.md'
created: 2026-07-31
updated: 2026-07-31
owners:
  - 'Chris Purcell / L3DigitalNet'
  - 'Coding agent under human review'
test_framework: pytest
---

# Durable Document References Optional Tooling Implementation Plan

> **This file is definition, not state.** It is read-only during implementation except when appending discovered work followed by `plan.py sync`, and at close-out harvest. Live progress belongs in phase checklists under `.project-pipeline/2026-07-31-durable-document-references-optional-tooling/`.

## 1. Objective

Ship the optional `project-standards references` CLI in the main wheel with document-derived specification and ADR identity, deterministic reference checking and local graph output, preview-first guarded reconciliation, opt-in aggregate validation, and a remediated dogfood corpus. No standards package, MCP surface, persistent graph/cache, or implicit adoption is introduced.

## 2. Background

Stable identifiers and Markdown links currently coexist without one repository-level contract. Existing Project Specification, ADR, and Markdown Frontmatter validators own their document schemas, while `validate-references` checks a narrower metadata corpus and the standards graph models packages rather than documents. `SPEC-GSF3` defines a separate optional composition layer that keeps those owners intact while adding navigable first references, canonical-target validation, an ephemeral graph, and mechanically bounded repair.

The repository is brownfield. The implementation must preserve existing top-level CLI dispatch, control-plane configuration and schema generation, validator exit behavior, guarded descriptor-relative writes, candidate-wheel parity, and the hosted/full verification gates. Tasks that touch those seams begin with characterization or explicit regression coverage before new behavior.

## 3. Scope

### 3.1 In Scope

- A first-party `project_standards.references` package and top-level `references` command group.
- Closed `[tools.references]` desired-config models and generated schema projection.
- Contained corpus discovery and one structural Markdown scanner for this subsystem.
- Project Specification and ADR namespace adapters plus a document-derived canonical registry.
- Link, navigation, relationship, external-ID, advisory, and exit-status policy.
- Deterministic finding, graph, and reconciliation-plan schemas and human/JSON/DOT renderers.
- Preview-first reconciliation and descriptor-safe atomic per-file apply.
- Opt-in aggregate validation with separately attributed legacy and new findings.
- Source, candidate-wheel, installed-wheel, real-corpus, security, and cold-run evidence.
- Dogfood configuration, blocking-drift remediation, user documentation, and release classification.

### 3.2 Out of Scope

- A standards package, package selector, package graph change, or validator replacement.
- MCP tools/resources, a web UI, daemon, watcher, database, persistent cache, or committed graph.
- Additional identifier namespaces, external URL health checks, prose rewriting, or metadata curation.
- Automatic `related:` changes, broad editorial inference, or a multi-file transaction guarantee.
- `project-toolbox` relocation or compatibility work for a not-yet-approved relocation.
- Adding Hypothesis or another test/runtime dependency; parametrized pytest covers v1 invariants.

### 3.3 Assumptions

- Current repository-scale Markdown remains small enough for on-demand scanning; T14 records the required cold-run evidence.
- Existing YAML frontmatter parsing and guarded filesystem primitives can be reused without weakening their public owners.
- `reconcile --apply` recomputes and reports its plan in the apply invocation; prior previews are informative only.
- The owner instruction to continue planning authorizes an implementation plan against the current `SPEC-GSF3` draft contract without changing its lifecycle status.

### 3.4 Constraints

- Use Python 3.14, Pydantic, PyYAML, pytest, Ruff, BasedPyright, and existing repository dependencies only.
- Every behavior task follows RED, Verify RED, GREEN, Verify GREEN, REFACTOR, Verify Task.
- Reuse `validate_frontmatter.parse_frontmatter`, control-plane config/schema generation, and `_filesystem` guarded publication; do not create competing authorities.
- Read commands make no network calls and never mutate authored documents; explicit graph output changes only its guarded target.
- Stable human, JSON, DOT, finding-code, schema, and exit-status contracts are frozen by tests before integration.
- Preserve user/concurrent changes and do not publish, release, commit, or push outside each task's separately authorized implementation workflow.

## 4. Source Requirements

| ID | Requirement | Source | Priority | Task(s) |
| --- | --- | --- | --- | --- |
| FR-001 | Main-wheel command availability without standards selection | SPEC-GSF3 §7.1 | must | T11 |
| FR-002 | Explicit availability and opt-in aggregate execution | SPEC-GSF3 §7.1 | must | T1, T10 |
| FR-003 | Separate adapter identity discovery from configured policy scope | SPEC-GSF3 §7.1 | must | T2, T3 |
| FR-004 | Spec/ADR adapters and unique canonical registry | SPEC-GSF3 §7.1 | must | T3 |
| FR-005 | First prose local formal reference links canonically | SPEC-GSF3 §7.1 | must | T4 |
| FR-006 | Configured-index completeness and exact References linking | SPEC-GSF3 §7.1 | must | T4 |
| FR-007 | Structural, destination/path, and historical exemptions | SPEC-GSF3 §7.1 | must | T2, T4 |
| FR-008 | Broken local links and ID-label wrong targets block | SPEC-GSF3 §7.1 | must | T4 |
| FR-009 | Local-by-default namespaces and explicit external IDs | SPEC-GSF3 §7.1 | must | T3, T4 |
| FR-010 | Preserve schema-specific relationship forms | SPEC-GSF3 §7.1 | must | T5 |
| FR-011 | Relationship IDs/paths resolve; external prior specs stay off-graph | SPEC-GSF3 §7.1 | must | T5, T7 |
| FR-012 | Bounded current-document relationship advisories only | SPEC-GSF3 §7.1 | must | T5 |
| FR-013 | Check accumulates safe findings without mutation | SPEC-GSF3 §7.1 | must | T6 |
| FR-014 | Deterministic local document graph in JSON and DOT | SPEC-GSF3 §7.1 | must | T7 |
| FR-015 | Preview default and explicit recomputed apply | SPEC-GSF3 §7.1 | must | T8, T9 |
| FR-016 | Safe visible-label edits; never destination/path rewrites | SPEC-GSF3 §7.1 | must | T8 |
| FR-017 | Reconciliation never mutates editorial relationships | SPEC-GSF3 §7.1 | must | T8 |
| FR-018 | Group containment and digest preflight precede writes | SPEC-GSF3 §7.1 | must | T9 |
| FR-019 | Atomic per-file replacement without transaction claim | SPEC-GSF3 §7.1 | must | T9 |
| FR-020 | Preserve validators/package graph and attribute overlap | SPEC-GSF3 §7.1 | must | T10 |
| NFR-001 | Byte-deterministic unstamped outputs | SPEC-GSF3 §7.2 | must | T1, T6, T7, T8, T13 |
| NFR-002 | Network denial and no authored-corpus graph output | SPEC-GSF3 §7.2 | must | T2, T7, T9, T13 |
| NFR-003 | Versioned human/JSON semantic parity | SPEC-GSF3 §7.2 | must | T1, T6, T7, T8 |
| NFR-004 | Source/candidate/installed portability | SPEC-GSF3 §7.2 | must | T11, T14 |
| NFR-005 | Reproducible cold-run benchmark record | SPEC-GSF3 §7.2 | must | T14 |
| NFR-006 | Adapter-neutral policy model | SPEC-GSF3 §7.2 | must | T3, T4, T5 |
| NFR-007 | Stable bounded diagnostics and physical locations | SPEC-GSF3 §7.2 | must | T1, T6, T13 |
| IR-001 | Public `references check`, `graph`, and `reconcile` CLI | SPEC-GSF3 §7.3 | must | T6, T7, T8, T11 |
| IR-002 | Group-wide exit taxonomy and check output | SPEC-GSF3 §7.3 | must | T6, T7, T9, T13 |
| IR-003 | JSON/DOT graph stdout and guarded non-authored output | SPEC-GSF3 §7.3 | must | T7 |
| IR-004 | Recomputed preview/apply plan contract | SPEC-GSF3 §7.3 | must | T8, T9 |
| IR-005 | Closed `[tools.references]` configuration | SPEC-GSF3 §7.3 | must | T1 |
| IR-006 | Opt-in aggregate validation | SPEC-GSF3 §7.3 | must | T10 |
| DR-001 | Parsed document records retain required structure | SPEC-GSF3 §7.4 | must | T2 |
| DR-002 | Unique canonical and alias registry entries | SPEC-GSF3 §7.4 | must | T3 |
| DR-003 | Closed versioned finding report | SPEC-GSF3 §7.4 | must | T1, T6 |
| DR-004 | Deterministic local graph nodes and edges | SPEC-GSF3 §7.4 | must | T1, T7 |
| DR-005 | Closed digest-bound reconciliation plan | SPEC-GSF3 §7.4 | must | T1, T8, T9 |
| DR-006 | No persistent cache, graph, registry, or plan state | SPEC-GSF3 §7.4 | must | T7, T8, T13 |

## 5. Repository and Architecture Context

### 5.1 Relevant Components

| Component | Purpose | Paths |
| --- | --- | --- |
| Top-level CLI | Lazy dispatch and aggregate validation | `src/project_standards/cli.py` |
| Desired config | Strict `.standards/config.toml` model, codec, and generated schema | `src/project_standards/control_plane/models.py`, `codec.py`, `schemas.py`, `src/project_standards/schemas/consumer-config.schema.json` |
| Existing metadata reference pass | Legacy frontmatter reference behavior retained separately | `src/project_standards/validate_references.py`, `src/project_standards/frontmatter_commands.py` |
| Spec and frontmatter parsing | Existing schema-specific declaration/frontmatter authorities | `src/project_standards/specs/`, `src/project_standards/validate_frontmatter.py` |
| Filesystem mutation | Descriptor-relative containment and atomic replacement | `src/project_standards/_filesystem.py`, `src/project_standards/control_plane/executor.py` |
| Distribution | Wheel and compatibility probes | `pyproject.toml`, `tests/test_installed_wrappers.py`, `tests/package_compatibility/` |
| Verification | Fast/full, schema, package, and dogfood gates | `scripts/verify.sh`, `tests/README.md`, `README.md` |

### 5.2 Existing Behavior

`project-standards validate` currently dispatches frontmatter, ID, metadata-reference, and control-plane validation. The legacy metadata-reference pass treats several unresolved and reciprocal conditions as warnings and assumes well-formed unknown ADR IDs are external. Desired config is a strict Pydantic model with only `project_standards` and `standards`; its generated JSON schema rejects unknown top-level keys. Safe writers already provide contained descriptor-relative staging and atomic replacement. The new subsystem composes these surfaces but does not change standalone legacy semantics.

### 5.3 Files Expected to Change

| Path | Action | Purpose | Owning task |
| --- | --- | --- | --- |
| `src/project_standards/references/` | create | Models, config, scanner, identities, policy, graph, reconciliation, CLI | T1–T9 |
| `src/project_standards/control_plane/models.py` | modify | Compose optional tool configuration | T1 |
| `src/project_standards/control_plane/codec.py` | modify | Preserve/render the tool namespace | T1 |
| `src/project_standards/control_plane/config_edit.py` | modify | Preserve tools during standards-only edits | T1 |
| `src/project_standards/control_plane/migration.py` | modify | Preserve tools through config migration/rendering | T1 |
| `src/project_standards/control_plane/schemas.py` | modify | Generate public reference schemas | T1 |
| `src/project_standards/schemas/consumer-config.schema.json` | modify | Generated closed tool configuration | T1 |
| `src/project_standards/schemas/reference-*.schema.json` | create | Findings, graph, and plan contracts | T1 |
| `src/project_standards/cli.py` | modify | Lazy command dispatch and opt-in aggregate composition | T10, T11 |
| `tests/references/` | create | Unit, contract, integration, corpus, security, and performance tests | T1–T14 |
| `tests/control_plane/` | modify | Config parse/render/schema preservation | T1, T10 |
| `tests/test_installed_wrappers.py` | modify | Installed-wheel command probes | T11 |
| `tests/package_compatibility/` | modify | Candidate/legacy compatibility coverage | T11 |
| `.standards/config.toml` | modify | Dogfood scope and aggregate opt-in after remediation | T12 |
| `docs/specs/README.md` | modify | Index `SPEC-GSF3` during dogfood reconciliation | T12 |
| `docs/**/*.md` | modify as reported | Mechanically safe and reviewed blocking-drift remediation | T12 |
| `README.md` | modify | Human landing-page command/config summary | T14 |
| `src/project_standards/README.md` | modify | Installed package/CLI reference | T14 |
| `docs/reference-tooling.md` | create | Detailed policy, formats, exits, safety, and adoption guide | T14 |

### 5.4 Dependencies

| Dependency | Type | Version / constraint | Reason |
| --- | --- | --- | --- |
| Python | runtime | `>=3.14` | Existing project floor |
| Pydantic | runtime | Existing project constraint | Closed typed config and public envelopes |
| PyYAML | runtime | Existing project constraint | Reuse current frontmatter authority |
| pytest | dev | Existing project constraint | TDD and contract evidence |
| `_filesystem` guarded writer | internal | Current repository contract | Contained atomic publication |
| Hypothesis | dev | Not added in v1 | Dependency expansion was not approved; use parametrized invariants |

## 6. Test Strategy

- **Framework:** pytest through uv. Config: `pyproject.toml` · Test root: `tests/` · Shared fixtures: existing `tmp_path`, control-plane helpers, installed-wheel fixtures, plus new `tests/references/conftest.py` corpus builders.
- **Commands:**
  - Targeted: `uv run pytest {path}::{test}` · File: `uv run pytest {path}` · Subset: `uv run pytest {path} -k "{expr}"`
  - Full: `uv run pytest` · First failure: `uv run pytest -x` · Locals: `uv run pytest -l`
  - Static: `uv run ruff check .` · `uv run ruff format --check .` · `uv run basedpyright`
- **Coverage is diagnostic:** `uv run pytest --cov=project_standards --cov-report=term-missing`; no new percentage gate.
- **Metamorphic invariants:** repeated serialization is byte-identical; discovery order does not affect output; preview is idempotent; applying safe edits then rechecking removes exactly those findings; failed preflight preserves all target bytes.

### 6.1 RED-GREEN-REFACTOR Contract

For every behavior task: add one focused failing test; verify it fails for the missing behavior; implement the minimum behavior; verify targeted and adjacent regressions; refactor only while green; then run task tests, Ruff, BasedPyright, and applicable integration checks before the task commit. When a task creates a new module, its RED step may first add the smallest typed importable skeleton that raises a controlled `NotImplementedError`; an import or collection failure never satisfies Verify RED.

### 6.2 Test Categories

| Category | Purpose | Location |
| --- | --- | --- |
| Unit | Parser, adapters, policy, graph, planner | `tests/references/test_*.py` |
| Integration | CLI, config, aggregate, filesystem effects | `tests/references/test_cli_*.py`, `tests/control_plane/` |
| Contract | JSON schema, exits, human/JSON/DOT parity | `tests/references/test_contracts.py` |
| Regression | Existing validators, package graph, config rendering | Existing test files plus `tests/references/test_regressions.py` |
| Characterization | Brownfield dispatch, config, and real corpus | T1, T10, T12 |
| End-to-end | Source/candidate/installed command behavior | T11, T14 |

### 6.3 TDD Exceptions

| Task | Exception reason | Objective validation |
| --- | --- | --- |
| T12 | Corpus/document migration is data correction driven by the implemented checker, not production behavior | Preview review, explicit apply, targeted Prettier, `references check`, `spec validate`, `spec lint`, and `git diff --check` |
| T13 | Cross-cutting adversarial acceptance consolidates already-implemented safety contracts; forcing a production defect to manufacture RED would be dishonest | Mutation-sensitive assertions, fault injection, network denial, repository hashes, and the complete status matrix; any discovered production gap becomes appended discovered work before a fix |
| T14 | Documentation and benchmark record are deliverables around already-tested behavior | CLI examples against candidate wheel, benchmark command, link/format checks, and full verification gate |

## 7. Execution Summary

| Task | Title | Phase | Depends on | Requirement(s) | Primary verification |
| --- | --- | --- | --- | --- | --- |
| T1 | Freeze models, schemas, and tool configuration | P1 | None | FR-002, NFR-001, NFR-003, NFR-007, IR-005, DR-003–DR-005 | `uv run pytest tests/references/test_models.py tests/references/test_config.py tests/references/test_schemas.py` |
| T2 | Discover and structurally scan identity and policy scopes | P1 | T1 | FR-003, FR-007, NFR-002, DR-001 | `uv run pytest tests/references/test_discovery.py tests/references/test_markdown.py` |
| T3 | Build spec/ADR adapters and canonical registry | P1 | T1, T2 | FR-003, FR-004, FR-009, NFR-006, DR-002 | `uv run pytest tests/references/test_identities.py` |
| T4 | Enforce body, navigation, and local-link policy | P2 | T2, T3 | FR-005–FR-009, NFR-006 | `uv run pytest tests/references/test_policy_links.py` |
| T5 | Enforce relationship and advisory policy | P2 | T3, T4 | FR-010–FR-012, NFR-006 | `uv run pytest tests/references/test_policy_relationships.py` |
| T6 | Deliver check reporting and exit contracts | P2 | T4, T5 | FR-013, NFR-001, NFR-003, NFR-007, IR-001, IR-002, DR-003 | `uv run pytest tests/references/test_cli_check.py tests/references/test_contracts.py` |
| T7 | Generate deterministic local JSON/DOT graphs | P3 | T3, T4, T5 | FR-011, FR-014, NFR-001–NFR-003, IR-002, IR-003, DR-004, DR-006 | `uv run pytest tests/references/test_graph.py tests/references/test_cli_graph.py` |
| T8 | Plan only allowlisted reconciliation edits | P3 | T4, T5, T6 | FR-015–FR-017, NFR-001, NFR-003, IR-004, DR-005, DR-006 | `uv run pytest tests/references/test_reconcile_plan.py` |
| T9 | Apply plans through guarded per-file replacement | P3 | T8 | FR-015, FR-018, FR-019, NFR-002, IR-002, IR-004, DR-005 | `uv run pytest tests/references/test_reconcile_apply.py` |
| T10 | Compose opt-in aggregate validation | P4 | T1, T6 | FR-002, FR-020, IR-006 | `uv run pytest tests/references/test_aggregate.py tests/control_plane/test_models.py tests/control_plane/test_schemas.py` |
| T11 | Prove top-level and wheel distribution parity | P4 | T6, T7, T9, T10 | FR-001, NFR-004, IR-001 | `uv run pytest tests/references/test_distribution.py tests/test_installed_wrappers.py` |
| T12 | Reconcile and enable the dogfood corpus | P4 | T10, T11 | FR-003–FR-013, FR-020 | Candidate `project-standards references check --root .` plus document gates |
| T13 | Harden security, determinism, and failure boundaries | P5 | T7, T9, T10 | NFR-001, NFR-002, NFR-007, IR-002, DR-006 | `uv run pytest tests/references/test_security.py tests/references/test_invariants.py` |
| T14 | Record performance, document, and qualify release | P5 | T11, T12, T13 | NFR-004, NFR-005 | Candidate/installed probes and `scripts/verify.sh --full` |

## 8. Implementation Tasks

## Phase P1: Contracts, Discovery, and Identity

### T1: Freeze models, schemas, and tool configuration

- **goal:** Parse and preserve a closed optional `[tools.references]` configuration and serialize closed versioned finding, graph, and reconciliation-plan envelopes deterministically.
- **phase:** P1 · **depends_on:** [] · **requirements:** [FR-002, NFR-001, NFR-003, NFR-007, IR-005, DR-003, DR-004, DR-005] · **priority:** must

#### T1 Context

`DesiredConfig` and `consumer-config.schema.json` currently reject every top-level key except `project_standards` and `standards`. Extend that authority rather than parsing TOML independently. Reference envelope models live in the new subsystem; control-plane schema generation projects their closed JSON Schemas. Configuration without `[tools.references]` must remain byte/behavior compatible, while explicit/enabled empty effective scope fails as exit class `2` at command resolution.

#### T1 Files

| Action | Path | Purpose |
| --- | --- | --- |
| create | `src/project_standards/references/models.py` | Typed records and versioned public envelopes |
| create | `src/project_standards/references/config.py` | Closed tools configuration and effective-scope model |
| create | `src/project_standards/references/schemas.py` | Canonical schema generation |
| modify | `src/project_standards/control_plane/models.py` | Compose optional tool config into desired state |
| modify | `src/project_standards/control_plane/codec.py` | Canonically preserve/render `[tools.references]` |
| modify | `src/project_standards/control_plane/config_edit.py` | Preserve tools across standards-only config edits |
| modify | `src/project_standards/control_plane/migration.py` | Preserve tools across migration/render paths |
| modify | `src/project_standards/control_plane/schemas.py` | Generate reference schema files |
| create | `tests/references/test_models.py` | Envelope validation and ordering |
| create | `tests/references/test_config.py` | Config acceptance/refusal/preservation |
| create | `tests/references/test_schemas.py` | Checked-in schema parity |
| modify | `tests/control_plane/test_models.py` | Desired-config regression coverage |
| modify | `tests/control_plane/test_schemas.py` | Generated consumer schema coverage |

#### T1 Acceptance Criteria

- The exact approved keys and value shapes round-trip through desired config, while unknown keys and empty effective runs are rejected without echoing unrelated values. (TC-T1-001)
- Findings, graph, and plans reject extra fields and serialize byte-identically under stable input ordering. (TC-T1-002)
- Configs without `tools` retain current parsing, resolution, and rendering behavior. (TC-T1-003)

#### T1 Test Cases

| ID | Test | Type | Expected result |
| --- | --- | --- | --- |
| TC-T1-001 | `test_reference_tool_config_is_closed_and_preserved` | contract | Only approved fields parse and render canonically |
| TC-T1-002 | `test_reference_envelopes_are_closed_versioned_and_deterministic` | contract | Equal semantic inputs produce identical bytes |
| TC-T1-003 | `test_desired_config_without_tools_is_unchanged` | regression | Existing fixtures and canonical bytes remain valid |

#### T1 Sub-tasks

- **T1.0 CHARACTERIZE** — pin current `DesiredConfig` parse/render/schema bytes for a config without `tools` in `tests/control_plane/test_models.py` and `test_schemas.py`.
- **T1.1 RED** — add TC-T1-001 through TC-T1-003; expected failure: the model rejects `tools`, reference envelopes do not exist, and schema generation lacks their outputs.
- **T1.2 Verify RED** — run `uv run pytest tests/references/test_models.py tests/references/test_config.py tests/references/test_schemas.py tests/control_plane/test_models.py tests/control_plane/test_schemas.py`; confirm behavioral assertion failures, not import/fixture errors after minimal test scaffolding.
- **T1.3 GREEN** — implement strict models, canonical ordering/serialization, config codec preservation, and generated schemas with no command behavior yet.
- **T1.4 Verify GREEN** — rerun targeted tests plus `uv run pytest tests/control_plane/test_codec.py tests/control_plane/test_config_edit.py`.
- **T1.5 REFACTOR** — consolidate schema/version/order helpers without coupling the control plane to command execution; record `none` if no safe cleanup emerges.
- **T1.6 Verify Task** — targeted tests · `uv run ruff check src/project_standards/references src/project_standards/control_plane tests/references tests/control_plane` · `uv run ruff format --check src/project_standards/references src/project_standards/control_plane tests/references tests/control_plane` · `uv run basedpyright` · generated-schema check; commit with requirement and TC IDs.

### T2: Discover and structurally scan identity and policy scopes

- **goal:** Produce contained, physical-coordinate parsed records from adapter identity locations and configured policy scopes, with shared exclusions and no duplicate reads. · **phase:** P1 · **depends_on:** [T1] · **requirements:** [FR-003, FR-007, NFR-002, DR-001] · **priority:** must
- **files:** `src/project_standards/references/discovery.py` (create), `src/project_standards/references/markdown.py` (create), `tests/references/conftest.py` (create), `tests/references/test_discovery.py` (create), `tests/references/test_markdown.py` (create)
- **acceptance:** identity and enforcement scopes remain distinct; contained deterministic discovery parses overlaps once; destination/URL/path/frontmatter/code/self/historical ranges are classified; generated/fixture excludes receive no reads or identity authority (TC-T2-001–TC-T2-003).
- **sub-tasks:**
  - **T2.1 RED** — add discovery and scanner fixtures covering split scopes, traversal, symlinks, CRLF, Unicode, frontmatter, inline/fenced code, link destinations, autolinks, raw URLs, path-like tokens, reference links, headings, anchors, and shared exclusion; expected failure: no reference corpus scanner exists.
  - **T2.2 Verify RED** — run the two new test files and confirm missing behavior rather than malformed fixtures.
  - **T2.3 GREEN** — implement contained discovery and a single-pass structural scanner reusing the existing frontmatter authority.
  - **T2.4 Verify GREEN** — targeted tests plus `uv run pytest tests/test_validate_frontmatter.py tests/specs`.
  - **T2.5 REFACTOR** — centralize byte-offset-to-physical-coordinate conversion and structural ranges; no policy decisions in the scanner.
  - **T2.6 Verify Task** — task tests + Ruff + BasedPyright + read-only repository hash assertion; commit with IDs.

### T3: Build specification/ADR adapters and canonical registry

- **goal:** Derive one unambiguous local canonical registry across nonexcluded adapter-recognized locations, independent of policy `include`, and keep external mappings separate. · **phase:** P1 · **depends_on:** [T1, T2] · **requirements:** [FR-003, FR-004, FR-009, NFR-006, DR-002] · **priority:** must
- **files:** `src/project_standards/references/identities.py` (create), `tests/references/test_identities.py` (create), `tests/references/fixtures/` (create)
- **acceptance:** exact spec/ADR forms resolve inside and outside `include`; excluded declarations stay unknown; near misses stay nonmentions; duplicates/alias collisions block; mapped external IDs cannot shadow or become local graph nodes (TC-T3-001–TC-T3-003).
- **sub-tasks:**
  - **T3.1 RED** — add adapter-neutral registry tests for all accepted forms, boundaries, cases, ambiguity, external mappings, and malformed declarations; expected failure: no adapters/registry exist.
  - **T3.2 Verify RED** — targeted run; confirm assertions fail on missing identity behavior.
  - **T3.3 GREEN** — implement adapter protocol, spec and ADR adapters, canonical/alias collision detection, and separate external lookup.
  - **T3.4 Verify GREEN** — targeted plus existing spec, ADR, ID, and reference validator tests.
  - **T3.5 REFACTOR** — keep namespace regexes and declaration extraction inside adapters; policy consumes typed identities only.
  - **T3.6 Verify Task** — task tests + Ruff + BasedPyright; commit with IDs.

## Phase P2: Policy and Read-Only Check

### T4: Enforce body, navigation, and local-link policy

- **goal:** Emit blocking findings for visible first references, exact `References` entries, configured-index completeness, broken local links, unknown bare local IDs, and ID-label target drift while honoring every exemption. · **phase:** P2 · **depends_on:** [T2, T3] · **requirements:** [FR-005, FR-006, FR-007, FR-008, FR-009, NFR-006] · **priority:** must
- **files:** `src/project_standards/references/policy.py` (create), `tests/references/test_policy_links.py` (create)
- **acceptance:** linked-reference and visible-prose predicates are exact; title-only destinations and path tokens do not count; ordinary References sections enforce listed links only; configured indexes enforce complete canonical coverage; ordinary broken links block; external mappings stay separate (TC-T4-001–TC-T4-004).
- **sub-tasks:**
  - **T4.1 RED** — add table-driven fixtures for each required, destination/path-exempt, structural-exempt, broken, wrong-target, external, anchor, exact-References, and configured-index completeness case; expected failure: no policy findings.
  - **T4.2 Verify RED** — targeted run and verify representative failures assert observable codes, severity, and physical loci.
  - **T4.3 GREEN** — implement adapter-neutral body/navigation/local-link policy and stable finding codes.
  - **T4.4 Verify GREEN** — targeted plus scanner/identity suites.
  - **T4.5 REFACTOR** — deduplicate occurrence classification without widening mention grammar or combining editorial policy.
  - **T4.6 Verify Task** — task tests + Ruff + BasedPyright; commit with IDs.

### T5: Enforce relationship and advisory policy

- **goal:** Validate schema-specific relationship IDs/paths and emit only bounded advisory classes for strong reciprocal evidence, nonrequired one-sided relationships, redundancy, and current-document orphans. · **phase:** P2 · **depends_on:** [T3, T4] · **requirements:** [FR-010, FR-011, FR-012, NFR-006] · **priority:** must
- **files:** `src/project_standards/references/relationships.py` (create), `src/project_standards/references/policy.py` (modify), `tests/references/test_policy_relationships.py` (create)
- **acceptance:** Project Specification IDs and frontmatter paths retain distinct semantics; local/external/unresolved/ambiguous `prior_specs` cases have exact outcomes and only local resolutions create edges; unresolved/noncanonical relationships block; superseded/historical documents produce no bounded advisory (TC-T5-001–TC-T5-004).
- **sub-tasks:**
  - **T5.1 RED** — add relationship-form, local/external/unresolved/ambiguous prior-spec, strong-evidence threshold, below-threshold, redundancy, one-sided, current, superseded, historical, and orphan fixtures; expected failure: relationship policy is absent.
  - **T5.2 Verify RED** — targeted run; confirm failures distinguish blocking resolution from advisory judgment.
  - **T5.3 GREEN** — implement schema-specific extraction/resolution and advisory evidence rules over typed documents.
  - **T5.4 Verify GREEN** — targeted plus legacy `validate-references` tests to prove standalone behavior unchanged.
  - **T5.5 REFACTOR** — isolate relationship semantics from graph projection and reconciliation eligibility.
  - **T5.6 Verify Task** — task tests + Ruff + BasedPyright; commit with IDs.

### T6: Deliver check reporting and exit contracts

- **goal:** Expose `references check` with accumulated safe findings, stable human/JSON parity, bounded diagnostics, and the group-wide exit taxonomy. · **phase:** P2 · **depends_on:** [T4, T5] · **requirements:** [FR-013, NFR-001, NFR-003, NFR-007, IR-001, IR-002, DR-003] · **priority:** must
- **files:** `src/project_standards/references/cli.py` (create), `src/project_standards/references/reporting.py` (create), `tests/references/test_cli_check.py` (create), `tests/references/test_contracts.py` (create)
- **acceptance:** independent findings accumulate safely; human/JSON normalized records match; advisory-only exits 0, blocking/internal exits 1, invocation/config exits 2; no unrelated prose is echoed (TC-T6-001–TC-T6-004).
- **sub-tasks:**
  - **T6.1 RED** — add CLI and golden contract tests for clean/advisory/blocking/config/internal cases and safe finding accumulation; expected failure: command/report surfaces do not exist.
  - **T6.2 Verify RED** — targeted run; ensure failure is absent behavior, not argparse `SystemExit` escaping the embedding boundary.
  - **T6.3 GREEN** — implement read-only check orchestration, reporting, JSON serialization, and controlled error boundary.
  - **T6.4 Verify GREEN** — targeted plus T2–T5 and top-level CLI help regressions.
  - **T6.5 REFACTOR** — share semantic record normalization between human and JSON renderers without parsing rendered text.
  - **T6.6 Verify Task** — task tests + Ruff + BasedPyright + repository byte-hash assertion; commit with IDs.

## Phase P3: Graph and Guarded Reconciliation

### T7: Generate deterministic local JSON and DOT graphs

- **goal:** Build only validated local canonical/path nodes and six approved edge kinds, with deterministic JSON/DOT and guarded optional publication outside both reference scopes. · **phase:** P3 · **depends_on:** [T3, T4, T5] · **requirements:** [FR-011, FR-014, NFR-001, NFR-002, NFR-003, IR-002, IR-003, DR-004, DR-006] · **priority:** must
- **files:** `src/project_standards/references/graph.py` (create), `src/project_standards/references/cli.py` (modify), `tests/references/test_graph.py` (create), `tests/references/test_cli_graph.py` (create)
- **acceptance:** repeated outputs are byte-identical; unresolved and externally mapped relationships produce no nodes/edges; identity-invalid corpora publish nothing; symlinked, non-regular, identity-scope, and policy-scope targets fail as exit 2; valid publication preserves all other bytes (TC-T7-001–TC-T7-004).
- **sub-tasks:**
  - **T7.1 RED** — add graph model/edge/order/DOT and valid/symlink/directory/authored output-path tests; expected failure: graph command and builder are absent.
  - **T7.2 Verify RED** — targeted run; confirm observable graph/output assertions fail.
  - **T7.3 GREEN** — implement graph projection/renderers and guarded output through existing filesystem primitives.
  - **T7.4 Verify GREEN** — targeted plus policy/contracts/filesystem regressions.
  - **T7.5 REFACTOR** — centralize stable ordering and escaping shared by JSON/DOT without persistent state.
  - **T7.6 Verify Task** — task tests + Ruff + BasedPyright + stdout repository-hash and explicit-target effect checks; commit with IDs.

### T8: Plan only allowlisted reconciliation edits

- **goal:** Convert only uniquely determined visible first-reference, wrong-path, and configured-index findings into deterministic nonoverlapping digest-bound previews, never destination/URL/path spans. · **phase:** P3 · **depends_on:** [T4, T5, T6] · **requirements:** [FR-015, FR-016, FR-017, NFR-001, NFR-003, IR-004, DR-005, DR-006] · **priority:** must
- **files:** `src/project_standards/references/reconcile.py` (create), `src/project_standards/references/cli.py` (modify), `tests/references/test_reconcile_plan.py` (create)
- **acceptance:** safe visible-label positives yield exact spans/replacements/digests; destination, URL, path, ambiguity, editorial, and history cases yield no edits; repeated preview is byte-identical and read-only (TC-T8-001–TC-T8-004).
- **sub-tasks:**
  - **T8.1 RED** — add exact preview and mutation-allowlist tests including destination/path and overlapping-span refusal; expected failure: planner absent.
  - **T8.2 Verify RED** — targeted run; confirm failures assert plan content rather than mock calls.
  - **T8.3 GREEN** — implement finding-to-edit planning and preview reporting only.
  - **T8.4 Verify GREEN** — targeted plus link/relationship policy and contract tests.
  - **T8.5 REFACTOR** — keep span construction pure and make eligibility exhaustive over stable finding codes.
  - **T8.6 Verify Task** — task tests + Ruff + BasedPyright + byte-idempotence check; commit with IDs.

### T9: Apply plans through guarded per-file replacement

- **goal:** Recompute, report, group-preflight, and apply the current plan with repository containment, digest freshness, atomic per-file replacement, and honest partial-failure reporting. · **phase:** P3 · **depends_on:** [T8] · **requirements:** [FR-015, FR-018, FR-019, NFR-002, IR-002, IR-004, DR-005] · **priority:** must
- **files:** `src/project_standards/references/application.py` (create), `src/project_standards/references/cli.py` (modify), `tests/references/test_reconcile_apply.py` (create), `tests/test_filesystem.py` (modify if the shared primitive needs contract coverage)
- **acceptance:** all preconditions fail before first write; successful files are atomically replaced; induced later-file failure reports applied/unapplied targets without transaction claim; remaining blocking findings determine exit 1 (TC-T9-001–TC-T9-004).
- **sub-tasks:**
  - **T9.0 CHARACTERIZE** — pin the existing guarded writer's replace, no-follow, mode, and cleanup behavior used by the application boundary.
  - **T9.1 RED** — add apply/stale/symlink/concurrent/partial-publication/status tests; expected failure: no apply orchestration exists.
  - **T9.2 Verify RED** — targeted run; confirm no wrong-reason filesystem setup failures.
  - **T9.3 GREEN** — implement full-plan preflight and atomic per-file publication using existing guarded primitives.
  - **T9.4 Verify GREEN** — targeted plus shared filesystem and control-plane executor regressions.
  - **T9.5 REFACTOR** — centralize apply reports and cleanup without adding rollback or persistent plan state.
  - **T9.6 Verify Task** — task tests + Ruff + BasedPyright + interruption/no-truncation checks; commit with IDs.

## Phase P4: Aggregate Integration, Distribution, and Dogfood Adoption

### T10: Compose opt-in aggregate validation

- **goal:** Run the new checker from `project-standards validate` only when `[tools.references].enabled = true`, preserving and separately attributing legacy validator findings. · **phase:** P4 · **depends_on:** [T1, T6] · **requirements:** [FR-002, FR-020, IR-006] · **priority:** must
- **files:** `src/project_standards/cli.py` (modify), `src/project_standards/control_plane/models.py` (modify if needed), `tests/references/test_aggregate.py` (create), `tests/test_cli_validate_aggregate.py` (modify/create), `tests/test_validate_references.py` (modify only for characterization)
- **acceptance:** absent/disabled config emits no new findings; enabled runs new checks; overlapping defects retain distinct codes/severities/source attribution; existing standalone and package graph suites are unchanged (TC-T10-001–TC-T10-003).
- **sub-tasks:**
  - **T10.0 CHARACTERIZE** — pin current aggregate/standalone exit, ordering, and legacy warning behavior on an overlapping metadata defect.
  - **T10.1 RED** — add enabled/disabled/overlap aggregate tests; expected failure: aggregate dispatch ignores tools references.
  - **T10.2 Verify RED** — targeted run; confirm disabled characterization stays green while enabled assertions fail.
  - **T10.3 GREEN** — add lazy opt-in dispatch and attributed result composition without changing legacy provider behavior.
  - **T10.4 Verify GREEN** — targeted plus all legacy validate, control-plane, and standards-graph tests.
  - **T10.5 REFACTOR** — isolate aggregate selection from package resolution; no standard selection may enable the tool.
  - **T10.6 Verify Task** — task tests + Ruff + BasedPyright + aggregate help regression; commit with IDs.

### T11: Prove top-level and wheel distribution parity

- **goal:** Make `project-standards references {check,graph,reconcile}` available and equivalent from source, candidate, and installed wheels without selected standards or MCP configuration. · **phase:** P4 · **depends_on:** [T6, T7, T9, T10] · **requirements:** [FR-001, NFR-004, IR-001] · **priority:** must
- **files:** `src/project_standards/cli.py` (modify), `tests/references/test_distribution.py` (create), `tests/test_installed_wrappers.py` (modify), `tests/package_compatibility/matrix.py` (modify), packaging expectations as discovered (modify)
- **acceptance:** help exposes exactly three commands; normalized JSON/exits match across three distributions; absence of standards/MCP config does not remove explicit commands (TC-T11-001–TC-T11-003).
- **sub-tasks:**
  - **T11.1 RED** — add source/candidate/installed command availability and parity probes; expected failure: top-level dispatch/wheel lacks the group.
  - **T11.2 Verify RED** — run source-focused probes first and confirm missing command, not candidate setup failure.
  - **T11.3 GREEN** — add lazy top-level dispatch and any required package-data/schema projection.
  - **T11.4 Verify GREEN** — targeted source tests, then build/extract candidate and run candidate/installed probes.
  - **T11.5 REFACTOR** — keep MCP imports and standards selection out of the references import path.
  - **T11.6 Verify Task** — distribution tests + Ruff + BasedPyright + compatibility subset; commit with IDs.

### T12: Reconcile and enable the dogfood corpus

- **goal:** Record the full-corpus baseline, review/apply safe edits, manually resolve remaining objective drift, index the new spec, and enable the honest dogfood scope with zero blocking findings. · **phase:** P4 · **depends_on:** [T10, T11] · **requirements:** [FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-009, FR-010, FR-011, FR-012, FR-013, FR-020] · **priority:** must
- **files:** `.standards/config.toml` (modify), `docs/specs/README.md` (modify), `docs/**/*.md` (bounded modifications from reviewed findings), `tests/references/test_repository_corpus.py` (create), `docs/plans/2026-07-31-durable-document-references-optional-tooling-plan.md` (read-only except discovered-work checkpoint)
- **acceptance:** baseline recorded in scratch logs; preview reviewed before apply; only allowlisted edits automated; remaining objective findings fixed manually; configured corpus/check/index gates pass; no waiver/suppression is introduced (TC-T12-001–TC-T12-003).
- **sub-tasks:**
  - **T12.1 RED** — run candidate full-corpus check and record the expected blocking baseline; add structural corpus assertions that fail on duplicate IDs, missing configured index coverage, or hidden scope.
  - **T12.2 Verify RED** — confirm failures are policy drift, not config/parser/environment defects; classify every file edit before mutation.
  - **T12.3 GREEN** — preview/apply safe reconciliation, perform reviewed manual objective fixes, update index/spec selection and honest tool config, never auto-curate relationships.
  - **T12.4 Verify GREEN** — rerun corpus tests, `references check`, spec validate/lint, targeted Prettier, and `git diff --check`.
  - **T12.5 REFACTOR** — reduce only redundant mechanical edits; preserve authored meaning and advisory inventory.
  - **T12.6 Verify Task** — corpus/document/config checks plus fast repository gate; commit with IDs and exact changed-document inventory.

## Phase P5: Hardening, Documentation, and Qualification

### T13: Harden security, determinism, and failure boundaries

- **goal:** Prove containment, symlink/TOCTOU resistance, reference-scope output refusal, network denial, bounded diagnostics, deterministic ordering, no persistent state, and complete exit classification under adversarial inputs while recording the accepted no-hard-resource-cap boundary. · **phase:** P5 · **depends_on:** [T7, T9, T10] · **requirements:** [NFR-001, NFR-002, NFR-007, IR-002, DR-006] · **priority:** must
- **files:** `tests/references/test_security.py` (create), `tests/references/test_invariants.py` (create), `src/project_standards/references/` (modify only for exposed defects)
- **acceptance:** parametrized path/Unicode/order inputs preserve invariants; socket APIs are denied; invalid graph targets are unchanged at exit 2; injected failures leave no partial output; status matrix covers ERR-001–ERR-008; diagnostics omit unrelated text; no unsupported numeric resource limit is introduced (TC-T13-001–TC-T13-004).
- **sub-tasks:**
  - **T13.1 RED** — add adversarial parametrized invariants and mutation-sensitive plausible-wrong-output cases. Under the documented TDD exception, do not require correct production code to fail; first prove each assertion detects its injected wrong result.
  - **T13.2 Verify RED** — run the mutation/fault-injection controls, then the real implementation. If the real implementation fails, confirm the intended safety/determinism gap and append discovered work before changing production.
  - **T13.3 GREEN** — complete the acceptance matrix; implement only a separately recorded discovered task for any real gap, never an unplanned hardening change inside this verification task.
  - **T13.4 Verify GREEN** — targeted security/invariant tests plus all references tests.
  - **T13.5 REFACTOR** — consolidate error taxonomy and safety helpers only where behavior remains frozen.
  - **T13.6 Verify Task** — all references tests + Ruff + BasedPyright + network-denied execution; commit with IDs.

### T14: Record performance, document, and qualify release

- **goal:** Record reproducible cold-run evidence, publish accurate optional-tool documentation, classify the release, and pass final source/candidate/installed and full repository gates. · **phase:** P5 · **depends_on:** [T11, T12, T13] · **requirements:** [NFR-004, NFR-005] · **priority:** must
- **files:** `tests/references/test_performance.py` (create), `docs/reference-tooling.md` (create), `README.md` (modify), `src/project_standards/README.md` (modify), `meta/versioning.md` (read/classify; modify only if policy clarification is required), release notes/version files only under separate release authorization
- **acceptance:** benchmark record states environment/corpus shape/method/result without hardcoded counts; docs distinguish explicit availability from aggregate opt-in and MCP/standards adoption; full verification and candidate/installed probes pass (TC-T14-001–TC-T14-003).
- **sub-tasks:**
  - **T14.1 RED** — add benchmark harness contract and documentation example/inventory checks; expected failure: benchmark record and docs are absent.
  - **T14.2 Verify RED** — confirm missing deliverables, not environment setup, cause failures.
  - **T14.3 GREEN** — record benchmark, author docs, and apply the versioning classification without publishing a release.
  - **T14.4 Verify GREEN** — run targeted docs/benchmark tests and every documented command against candidate bytes.
  - **T14.5 REFACTOR** — remove duplicated docs while preserving one human landing summary and one detailed guide.
  - **T14.6 Verify Task** — build/extract candidate as README specifies; run `scripts/verify.sh --full`, package contract gates, candidate dogfood validation, installed-wheel parity, Prettier/markdownlint, and `git diff --check`; commit with IDs. Release publication remains separately authorized.

## 9. Cross-Cutting Requirements

| Concern | Applies? | How verified | Owning task |
| --- | --- | --- | --- |
| Error handling | yes | Group-wide status matrix and ERR-001–ERR-008 fault injection | T6, T9, T13 |
| Logging / observability | yes | Versioned bounded human/JSON reports; no service telemetry | T6, T13 |
| Security | yes | Containment, no-follow, network denial, stale-write, redaction, partial-output tests | T9, T13 |
| Performance | yes | Reproducible cold-run benchmark record, no numeric release threshold | T14 |
| Compatibility | yes | Legacy validators plus source/candidate/installed and compatibility matrix | T10, T11, T14 |
| Documentation | yes | Command/config/policy/safety examples exercised against candidate | T14 |

## 10. Integration and Migration

### 10.1 Integration Sequence

1. Freeze models/config/public schemas. 2. Build scanner and identity registry. 3. Add link/relationship policy and read-only check. 4. Add graph and reconciliation. 5. Opt into aggregate validation. 6. Qualify wheel distribution. 7. Baseline/remediate/enable the dogfood corpus. 8. Harden, document, benchmark, and run the full gate.

### 10.2 Data or State Migration

- **Required:** yes, authored-document drift only · **Rollback supported:** Git revert/forward correction · **Idempotent:** reconciliation preview/apply becomes empty after safe fixes.
- No tool-owned persistent state migrates. T12 updates authored Markdown and `.standards/config.toml` only after a reviewed candidate preview. Each file is atomically replaced, but the operation does not claim a multi-file transaction.

### 10.3 Compatibility Plan

The explicit command is always installed. Aggregate behavior remains absent unless configured. Existing `validate-references`, package validators, and standards graph retain their standalone code/severity/entry points. Aggregate overlap is separately attributed rather than silently deduplicated or reclassified. Older configs without `[tools.references]` remain valid and behaviorally unchanged.

## 11. Risks and Decisions

| ID | Risk | Likelihood | Impact | Mitigation | Owning task |
| --- | --- | --- | --- | --- | --- |
| R-001 | Structural scanner misclassifies code/link spans and creates blocking noise | medium | high | Physical-range fixtures and near-miss mutation cases before policy | T2, T4 |
| R-002 | Config rendering drops or rewrites consumer-owned tool data | medium | high | Brownfield round-trip characterization and generated schema tests | T1 |
| R-003 | New aggregate findings obscure legacy severity/source | medium | medium | Stable code namespaces and explicit overlapping-defect fixture | T10 |
| R-004 | Reconciliation overwrites concurrent/user edits | low | high | Complete digest/containment preflight before first write | T9 |
| R-005 | Dogfood adoption expands into unbounded editorial cleanup | medium | high | Safe allowlist, exact baseline, objective-only manual fixes, no waivers | T12 |
| R-006 | Source behavior differs from packaged/installed behavior | medium | high | Three-distribution normalized parity and candidate-first docs | T11, T14 |
| R-007 | Pathological repository-owned Markdown stalls or exhausts a validation run | low | medium | Accepted v1 risk; malformed-input coverage and reproducible benchmark, with later evidence-based limits only | T13, T14 |

| ID | Decision | Rationale | Affected task(s) |
| --- | --- | --- | --- |
| D-001 | Extend the existing desired-config authority for `[tools.references]` | Avoid a competing TOML parser/schema | T1, T10 |
| D-002 | Use one subsystem scanner plus existing frontmatter authority | Keep occurrence classification centralized without changing spec/ADR validators | T2–T5 |
| D-003 | Keep external mappings outside the local graph | Matches the local document graph contract | T3, T7 |
| D-004 | Discover identities at adapter-owned canonical locations independently of policy `include`, with shared `exclude` | Preserve honest phased adoption without giving generated/fixture copies identity authority | T2, T3, T12 |
| D-005 | Count formal IDs only in visible prose/labels and never rewrite destination or path spans | Avoid false positives and unsafe edits from ADR filenames and URLs | T2, T4, T8 |
| D-006 | Give configured indexes completeness responsibility; ordinary exact `References` sections enforce listed links only | Keep navigation enforcement deterministic and bounded | T4, T12 |
| D-004 | Recompute apply plans in-process | No hidden plan persistence or cross-run guarantee | T8, T9 |
| D-005 | Use existing pytest only | No unapproved Hypothesis dependency; retain strong parametrized invariants | T2, T7–T9, T13 |

## 12. Open Questions

| Question | Blocking? | Owner | Current assumption |
| --- | --- | --- | --- |
| Does an implementation defect require a new runtime Markdown parser dependency? | yes if encountered | Owner | No; use existing dependencies and stop rather than add one implicitly |
| Will the real corpus reveal ambiguous/editorial findings outside the safe repair allowlist? | no | Owner | Record as advisories or future work; do not mutate or block release unless objectively blocking under the spec |

## 13. Final Verification

- All 14 task checklists are `done` or explicitly `skipped` with evidence; no blocker remains.
- Every source requirement maps to passing Appendix B evidence and no accepted behavior depends on hardcoded corpus counts.
- Candidate projection is synchronized, wheel is built/extracted exactly as README documents, and candidate `PYTHONPATH` is first.
- `scripts/verify.sh --full` passes after the final content change.
- `uv run project-standards standards validate-packages --root . --json` passes.
- `uv run project-standards standards validate-graph --root . --require-all-manifests --json` passes.
- `uv run project-standards standards generate-package-schemas --root . --check` passes.
- `uv run project-standards standards sync-payload-projection --root . --check` passes.
- Candidate `project-standards validate`, `references check`, graph determinism, and reconcile preview pass against the dogfood scope.
- Source, candidate, and installed wheel normalized CLI probes pass without selected standards or MCP configuration.
- `uv run ruff check .`, `uv run ruff format --check .`, `uv run basedpyright`, and `uv run pip-audit` pass through the repository gate.
- Targeted Prettier and configured markdownlint checks pass for changed documentation; `git diff --check` is clean.
- The benchmark environment, corpus shape, command, and observed result are recorded; no numeric threshold is invented.
- Release/commit/push/publication occur only with their separate authorizations.

## 14. Close-out

- **Completed:** _pending_ · final commit _pending_
- **Deviations / decisions harvested from notes:** _pending close-out_
- **Risks closed / accepted:** _pending close-out_
- **Deferred work filed:** _pending close-out_

Teardown: harvest notes here and into specs/ADRs/issues as appropriate → set `status: complete` and update `updated` → commit master → remove `.project-pipeline/2026-07-31-durable-document-references-optional-tooling/`.

## Appendices

## Appendix A. Interface and Schema Changes

### A.1 Public Interfaces

| Interface | Current | Planned | Compatibility |
| --- | --- | --- | --- |
| `project-standards references` | Absent | `check`, `graph`, `reconcile` | Additive main-wheel CLI |
| `.standards/config.toml` | `project_standards` and `standards` | Optional closed `[tools.references]` | Existing configs unchanged |
| `project-standards validate` | Existing validators/control plane | Optional additional attributed reference findings | Disabled by default |
| Finding JSON | Absent | Versioned closed report envelope | New contract |
| Graph JSON/DOT | Absent | Deterministic local document graph | New contract |
| Reconciliation plan | Absent | Versioned digest-bound preview | New contract |

### A.2 Data Models

| Model | Field | Change | Validation | Migration |
| --- | --- | --- | --- | --- |
| `DesiredConfig` | `tools.references` | add optional | Strict nested Pydantic/generated schema | None when absent |
| Parsed document | path/identity/structure/links/mentions/relationships | add derived | Contained physical ranges | Memory only |
| Finding report | version/code/severity/locus/message/guidance | add | Closed deterministic schema | None |
| Graph | version/nodes/edges | add | Local resolved sorted/deduplicated | None |
| Reconciliation plan | repo/files/digests/spans/replacements | add | Closed, contained, nonoverlapping | Ephemeral only |

## Appendix B. Test Matrix

| Test ID | Requirement | Task | Test path | Type |
| --- | --- | --- | --- | --- |
| TC-T1-001 | FR-002, IR-005 | T1 | `tests/references/test_config.py::test_reference_tool_config_is_closed_and_preserved` | contract |
| TC-T1-002 | NFR-001, NFR-003, DR-003, DR-004, DR-005 | T1 | `tests/references/test_models.py::test_reference_envelopes_are_closed_versioned_and_deterministic` | contract |
| TC-T1-003 | FR-020 | T1 | `tests/control_plane/test_models.py::test_desired_config_without_tools_is_unchanged` | regression |
| TC-T2-001 | FR-003, NFR-002 | T2 | `tests/references/test_discovery.py::test_identity_and_policy_scopes_are_contained_distinct_and_share_exclusions` | unit |
| TC-T2-002 | FR-007, DR-001 | T2 | `tests/references/test_markdown.py::test_scanner_classifies_visible_destination_path_and_structural_ranges` | unit |
| TC-T2-003 | DR-001 | T2 | `tests/references/test_markdown.py::test_scanner_retains_inline_reference_links_anchors_and_crlf_coordinates` | unit |
| TC-T3-001 | FR-003, FR-004, NFR-006, DR-002 | T3 | `tests/references/test_identities.py::test_registry_resolves_exact_forms_outside_policy_include_but_not_exclude` | unit |
| TC-T3-002 | FR-004 | T3 | `tests/references/test_identities.py::test_registry_blocks_duplicate_and_alias_collisions` | unit |
| TC-T3-003 | FR-009 | T3 | `tests/references/test_identities.py::test_external_mapping_is_separate_and_cannot_shadow_local_identity` | unit |
| TC-T4-001 | FR-005, FR-007 | T4 | `tests/references/test_policy_links.py::test_first_visible_prose_link_and_destination_path_exemptions` | unit |
| TC-T4-002 | FR-006 | T4 | `tests/references/test_policy_links.py::test_configured_index_is_complete_and_exact_references_entries_link` | unit |
| TC-T4-003 | FR-008 | T4 | `tests/references/test_policy_links.py::test_broken_and_wrong_target_local_links_block` | unit |
| TC-T4-004 | FR-009 | T4 | `tests/references/test_policy_links.py::test_unknown_bare_external_link_and_mapping_policy` | unit |
| TC-T5-001 | FR-010 | T5 | `tests/references/test_policy_relationships.py::test_schema_specific_relationship_forms_are_preserved` | unit |
| TC-T5-002 | FR-011 | T5 | `tests/references/test_policy_relationships.py::test_relationship_ids_and_paths_have_exact_local_external_and_blocking_outcomes` | unit |
| TC-T5-003 | FR-012 | T5 | `tests/references/test_policy_relationships.py::test_strong_evidence_threshold_and_advisory_exit` | unit |
| TC-T5-004 | FR-012 | T5 | `tests/references/test_policy_relationships.py::test_only_current_orphan_one_sided_and_redundancy_cases_advise` | unit |
| TC-T6-001 | FR-013 | T6 | `tests/references/test_cli_check.py::test_check_accumulates_independent_safe_findings_without_writes` | integration |
| TC-T6-002 | NFR-003, DR-003 | T6 | `tests/references/test_contracts.py::test_check_human_and_json_semantics_match` | contract |
| TC-T6-003 | IR-002 | T6 | `tests/references/test_cli_check.py::test_check_exit_zero_one_two_contract` | integration |
| TC-T6-004 | NFR-007 | T6 | `tests/references/test_contracts.py::test_findings_have_stable_codes_physical_loci_and_bounded_text` | contract |
| TC-T7-001 | FR-014, DR-004 | T7 | `tests/references/test_graph.py::test_graph_contains_only_resolved_local_nodes_and_approved_edges` | unit |
| TC-T7-002 | NFR-001 | T7 | `tests/references/test_graph.py::test_json_and_dot_are_byte_deterministic_under_input_permutation` | unit |
| TC-T7-003 | NFR-002, IR-002, IR-003 | T7 | `tests/references/test_cli_graph.py::test_graph_output_rejects_symlink_nonregular_and_reference_scope_targets` | integration |
| TC-T7-004 | FR-014 | T7 | `tests/references/test_cli_graph.py::test_identity_invalid_graph_publishes_nothing` | regression |
| TC-T8-001 | FR-016 | T8 | `tests/references/test_reconcile_plan.py::test_planner_edits_only_safe_visible_spans_never_destinations_or_paths` | unit |
| TC-T8-002 | FR-017 | T8 | `tests/references/test_reconcile_plan.py::test_editorial_and_ambiguous_findings_never_plan_edits` | unit |
| TC-T8-003 | DR-005 | T8 | `tests/references/test_reconcile_plan.py::test_plan_is_digest_bound_nonoverlapping_and_closed` | contract |
| TC-T8-004 | FR-015, DR-006 | T8 | `tests/references/test_reconcile_plan.py::test_preview_is_deterministic_read_only_and_unpersisted` | integration |
| TC-T9-001 | FR-018 | T9 | `tests/references/test_reconcile_apply.py::test_group_preflight_fails_before_any_write` | integration |
| TC-T9-002 | FR-019 | T9 | `tests/references/test_reconcile_apply.py::test_each_successful_target_is_atomically_replaced` | integration |
| TC-T9-003 | FR-019 | T9 | `tests/references/test_reconcile_apply.py::test_late_publication_failure_reports_partial_state_without_transaction_claim` | regression |
| TC-T9-004 | IR-002, IR-004 | T9 | `tests/references/test_reconcile_apply.py::test_apply_recomputes_plan_and_exits_for_remaining_blockers` | integration |
| TC-T10-001 | FR-002, IR-006 | T10 | `tests/references/test_aggregate.py::test_aggregate_runs_only_when_explicitly_enabled` | integration |
| TC-T10-002 | FR-020 | T10 | `tests/references/test_aggregate.py::test_overlapping_legacy_and_new_findings_keep_codes_severities_and_sources` | regression |
| TC-T10-003 | FR-020 | T10 | `tests/references/test_aggregate.py::test_standalone_validators_and_package_graph_are_unchanged` | regression |
| TC-T11-001 | FR-001, IR-001 | T11 | `tests/references/test_distribution.py::test_source_candidate_and_installed_help_expose_exact_commands` | end-to-end |
| TC-T11-002 | NFR-004 | T11 | `tests/references/test_distribution.py::test_three_distribution_json_and_exit_parity` | end-to-end |
| TC-T11-003 | FR-001 | T11 | `tests/test_installed_wrappers.py::test_references_available_without_standard_or_mcp_selection` | end-to-end |
| TC-T12-001 | FR-003, FR-004 | T12 | `tests/references/test_repository_corpus.py::test_dogfood_scope_is_nonempty_honest_and_identity_unique` | integration |
| TC-T12-002 | FR-005–FR-011 | T12 | `tests/references/test_repository_corpus.py::test_dogfood_corpus_has_no_blocking_reference_drift` | integration |
| TC-T12-003 | FR-012, FR-013 | T12 | `tests/references/test_repository_corpus.py::test_advisory_inventory_is_structural_not_count_pinned` | integration |
| TC-T13-001 | NFR-001 | T13 | `tests/references/test_invariants.py::test_input_order_and_repeated_runs_preserve_exact_outputs` | regression |
| TC-T13-002 | NFR-002 | T13 | `tests/references/test_security.py::test_all_read_paths_deny_network_and_preserve_source_bytes` | security |
| TC-T13-003 | NFR-007 | T13 | `tests/references/test_security.py::test_adversarial_content_does_not_leak_unrelated_text` | security |
| TC-T13-004 | IR-002, DR-006 | T13 | `tests/references/test_invariants.py::test_failure_matrix_has_stable_exit_no_persistent_state_and_no_invented_resource_cap` | contract |
| TC-T14-001 | NFR-005 | T14 | `tests/references/test_performance.py::test_cold_run_benchmark_record_is_reproducible_and_count_independent` | performance |
| TC-T14-002 | NFR-004 | T14 | `tests/references/test_distribution.py::test_candidate_documented_examples_match_installed_behavior` | end-to-end |
| TC-T14-003 | FR-001, FR-002 | T14 | `tests/references/test_documentation.py::test_docs_distinguish_explicit_optional_aggregate_and_mcp_boundaries` | contract |

## Appendix C. Deferred Work

| Item | Reason deferred | Follow-up |
| --- | --- | --- |
| Additional formal-ID adapters | V1 is specs and ADRs only | New specification revision when a concrete namespace contract exists |
| Persistent scan cache | No measured need yet | Reconsider from recorded T14 benchmark evidence |
| MCP exposure | CLI contract must stabilize first | Separate approved MCP specification |
| `project-toolbox` relocation | Future package does not yet own this tool | Separate compatibility/migration decision |
| True multi-file transaction | Existing executor guarantees atomicity per file only | Future executor contract and recovery design |
| Hypothesis property tests | New dev dependency not approved for v1 | Optional follow-up if owner authorizes `uv add --dev hypothesis` |
