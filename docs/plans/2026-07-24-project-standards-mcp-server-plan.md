---
title: 'Project Standards MCP Server Implementation Plan'
slug: 'project-standards-mcp-server'
size: full
status: active
source: 'SPEC-MS01 revision 1.4 and SPEC-RD01 revision 1.6'
spec_ref: 'docs/specs/2026-07-07-project-standards-mcp-server-implementation-spec.md'
created: 2026-07-24
updated: 2026-07-31
owners:
  - 'Chris Purcell / L3DigitalNet'
  - 'Coding agent under human review'
test_framework: pytest
---

# Project Standards MCP Server Implementation Plan

> **This file is definition, not state.** It remains read-only during implementation except when inserting discovered work followed by `uv run scripts/plan.py sync`, or during close-out harvest. Live progress belongs under `.project-pipeline/2026-07-24-project-standards-mcp-server/`.

## 1. Objective

Deliver a local, stdio, read-only Project Standards MCP server that exposes exact installed Catalog 5 resources and the existing unified consumer-control-plane results through a small generic interface, works in current Codex and Claude Code clients, and leaves package, reconciliation, provider, CLI, and CI semantics authoritative outside MCP.

## 2. Background

`SPEC-MT01` readiness is complete, and approved `SPEC-RD01` revision 1.5 and `SPEC-MS01` revision 1.1 lock the local read-only v1 boundary. Project Standards 5.8.0 now supplies the V2 package contracts, installed distribution, `.standards/` control plane, reconciliation plan, and provider dispatch needed by a thin MCP adapter. The original MCP plan predated those contracts and targeted an obsolete graph/adopt architecture. The protocol and Python SDK are also at a release boundary: 2025-11-25 is stable on 2026-07-24, while the breaking 2026-07-28 revision and Python SDK v2 have not yet reached the final stable combination this project will pin. Implementation therefore begins with a no-code protocol, dependency, client, and service-boundary freeze.

## 3. Scope

### 3.1 In Scope

- One SDK-independent package service facade for installed resources, consumer inspection, reconciliation previews, and non-mutating provider operations.
- One local stdio MCP adapter with exact resources, declared prompts where useful, a shared read fallback, and generic read-only tools.
- Exact-version and digest validation, explicit repository roots, bounded diagnostics, structured results, deterministic normalization, and fail-closed startup.
- Source-fixture, installed-wheel, protocol, Codex, and Claude Code verification.
- Client setup/reference/troubleshooting documentation and release-readiness evidence.

### 3.2 Out of Scope

- Any standards-package change or new package contract.
- Reconciliation apply, provider mutation, other consumer writes, remote transport, GitHub mutation, fleet reporting, sampling, or elicitation.
- Release-version bump/finalization, publication, tags, GitHub release creation, or release asset upload.
- Legacy V1 manifest, registry, `.project-standards.yml`, or copy-adopt support as current MCP authority.

### 3.3 Assumptions

- The final MCP protocol and stable-compatible Python SDK can be selected after the 2026-07-28 publication; if not, T1 remains blocked and no code begins.
- Existing public package/control-plane APIs provide the semantics characterized by T2-T4; a missing semantic capability requires a spec backtrack, not MCP-local reimplementation.
- Codex or Claude Code may require `standard_read`; both clients remain required release-candidate targets.

### 3.4 Constraints

- Execute tasks in dependency order and follow RED-GREEN-REFACTOR for every behavior change.
- SDK types and protocol revision branches stop at `project_standards.mcp_server`.
- Production resource authority is `InstalledDistribution`; source loading is an explicit test/development injection.
- Every consumer operation receives an explicit effective `repo_root`; client roots may only narrow it.
- stdout contains protocol messages only. Logs go to stderr.
- No task may add a mutating MCP tool or remote transport.
- Candidate-wheel verification puts the extracted wheel first on `PYTHONPATH`.

## 4. Source Requirements

| ID | Requirement | Source | Priority | Task(s) |
| --- | --- | --- | --- | --- |
| FR-001 | Generation-qualified installed catalog resource. | SPEC-MS01 §7.1 | must | T2, T6 |
| FR-002 | Exact per-package metadata resources. | SPEC-MS01 §7.1 | must | T2, T6 |
| FR-003 | Declared digest-checked payload resources. | SPEC-MS01 §7.1 | must | T2, T6 |
| FR-004 | Resource templates expand without code/tool changes. | SPEC-MS01 §7.1 | must | T6 |
| FR-005 | Declared, client-useful prompts only. | SPEC-MS01 §7.1 | should | T7 |
| FR-006 | Reject undeclared, invalid, or escaping resources. | SPEC-MS01 §7.1 | must | T2, T6 |
| FR-007 | Generic `standards_list`. | SPEC-MS01 §7.1 | must | T8 |
| FR-008 | Shared `standard_read` client fallback when the client-matrix condition holds. | SPEC-MS01 §7.1 | must | T7 |
| FR-009 | Current-control-plane `repo_inspect`. | SPEC-MS01 §7.1 | must | T3, T8 |
| FR-010 | Omit deterministic recommendations unless an existing typed service can justify them. | SPEC-MS01 §7.1 | could | T10 |
| FR-011 | Dry-run `reconcile_preview`. | SPEC-MS01 §7.1 | must | T3, T9 |
| FR-012 | Provider-backed `validate_repo`. | SPEC-MS01 §7.1 | must | T4, T9, T14 |
| FR-013 | Structured `drift_check`. | SPEC-MS01 §7.1 | should | T4, T9, T14 |
| FR-014 | Generic payload-qualified helper operations. | SPEC-MS01 §7.1 | should | T4, T9 |
| FR-015 | Delegate all semantics through the facade. | SPEC-MS01 §7.1 | must | T2, T3, T4, T15 |
| FR-016 | Preserve CLI/CI backstops. | SPEC-MS01 §7.1 | must | T11 |
| FR-017 | Preserve reconciliation fingerprints/preconditions. | SPEC-MS01 §7.1 | should | T3, T9 |
| FR-018 | No v1 write tools. | SPEC-MS01 §7.1 | must | T5, T9, T10 |
| FR-019 | Future writes reuse executor safety. | SPEC-MS01 §7.1 | should | T9 |
| FR-020 | Client setup and troubleshooting docs. | SPEC-MS01 §7.1 | should | T11 |
| FR-021 | Preserve declared relationships without hidden dependencies. | SPEC-MS01 §7.1 | must | T2, T6, T8, T13 |
| FR-022 | Typed structured tool results. | SPEC-MS01 §7.1 | must | T8, T9 |
| FR-023 | Compact reviewed tool metadata. | SPEC-MS01 §7.1 | should | T8, T9 |
| FR-024 | Explicit root with optional narrowing. | SPEC-MS01 §7.1 | must | T3, T5, T8, T9 |
| FR-025 | Accurate revision-specific capabilities. | SPEC-MS01 §7.1 | must | T5, T10 |
| FR-026 | SDK-independent service facade first. | SPEC-MS01 §7.1 | must | T2, T3, T4 |
| FR-027 | Installed exact-version production authority. | SPEC-MS01 §7.1 | must | T2, T6 |
| FR-028 | Exclude unrelated/secret consumer contents. | SPEC-MS01 §7.1 | must | T3, T9 |
| FR-029 | Final protocol/SDK/license/conformance gate. | SPEC-MS01 §7.1 | must | T1, T10 |
| FR-030 | Codex and Claude Code compatibility matrix. | SPEC-MS01 §7.1 | must | T1, T11 |
| NFR-001 | Package growth does not grow tool surface. | SPEC-MS01 §7.2 | must | T6, T10 |
| NFR-002 | Compact lazy discovery. | SPEC-MS01 §7.2 | must | T6 |
| NFR-003 | Protocol-only stdout. | SPEC-MS01 §7.2 | must | T5, T10 |
| NFR-004 | Structured clear errors. | SPEC-MS01 §7.2 | must | T5, T10 |
| NFR-005 | Explicit deterministic normalization. | SPEC-MS01 §7.2 | must | T2, T3, T4, T6, T10, T13, T14, T15 |
| NFR-006 | Thin MCP layer. | SPEC-MS01 §7.2 | must | T2, T3, T4, T5, T10 |
| NFR-007 | Bounded/cached common reads. | SPEC-MS01 §7.2 | should | T2, T6 |
| NFR-008 | No remote transport. | SPEC-MS01 §7.2 | must | T5, T10 |
| NFR-009 | Protocol/package/repo tests in CI. | SPEC-MS01 §7.2 | must | T10, T11 |
| NFR-010 | Installed/source equivalence. | SPEC-MS01 §7.2 | must | T2, T11 |
| NFR-011 | Stable pinned protocol/client contract. | SPEC-MS01 §7.2 | must | T1, T10, T11 |
| NFR-012 | Bounded tool context. | SPEC-MS01 §7.2 | should | T8, T9, T10 |
| NFR-013 | SDK/service authority isolation. | SPEC-MS01 §7.2 | must | T2, T5, T10 |
| IR-001 | Package MCP launch command. | SPEC-MS01 §7.3 | required | T5 |
| IR-002 | Generation/exact-version resource URIs. | SPEC-MS01 §7.3 | required | T6 |
| IR-003 | Typed generic MCP tools. | SPEC-MS01 §7.3 | required | T8, T9 |
| IR-004 | One typed package service facade. | SPEC-MS01 §7.3 | required | T2, T3, T4 |
| IR-005 | Explicit contained consumer filesystem access. | SPEC-MS01 §7.3 | required | T3 |
| IR-006 | Stderr-only logs. | SPEC-MS01 §7.3 | required | T5 |
| IR-007 | Explicit roots with optional narrowing. | SPEC-MS01 §7.3 | required | T3, T5 |
| IR-008 | Accurate revision-specific capability discovery. | SPEC-MS01 §7.3 | required | T5, T10 |
| IR-009 | Exact payload-qualified provider dispatch. | SPEC-MS01 §7.3 | required | T4, T9 |
| DR-001 | V2 package descriptor authority. | SPEC-MS01 §7.4 | required | T2, T13 |
| DR-002 | Exact resource descriptor fields and validation. | SPEC-MS01 §7.4 | required | T2, T6 |
| DR-003 | Required structured Finding fields. | SPEC-MS01 §7.4 | required | T4, T10 |
| DR-004 | Existing reconciliation preview schema. | SPEC-MS01 §7.4 | required | T3, T9 |
| DR-005 | Bounded repo inspection snapshot. | SPEC-MS01 §7.4 | required | T3, T8 |
| DR-006 | Exact V2 relationship result. | SPEC-MS01 §7.4 | required | T2, T8 |
| DR-007 | Truthful MCP capability descriptor/list changes. | SPEC-MS01 §7.4 | required | T5, T10 |
| DR-008 | Exact typed provider result. | SPEC-MS01 §7.4 | required | T4, T9 |
| DR-009 | Explicit deterministic normalization. | SPEC-MS01 §7.4 | required | T2, T3, T4, T10, T13, T14, T15 |

`FR-010` is Could-priority and is satisfied in v1 by an explicit omission: no current typed recommendation service exists, so T10 proves that the server registers no recommendation tool and returns no invented confidence or relevance result. Appendix C records the conditions for reconsidering it.

## 5. Repository and Architecture Context

### 5.1 Relevant Components

| Component | Purpose | Paths |
| --- | --- | --- |
| V2 package contracts | Exact family, payload, resource, relation, provider data. | `src/project_standards/package_contract/` |
| Installed distribution | Published runtime projection. | `src/project_standards/control_plane/distribution.py` |
| Consumer control plane | Desired/catalog/lock, reconciliation, providers, executor safety. | `src/project_standards/control_plane/` |
| Unified CLI | Package command dispatcher and future `mcp` launcher. | `src/project_standards/cli.py` |
| Service facade | Planned SDK-free MCP-facing domain boundary. | `src/project_standards/mcp_services/` |
| MCP adapter | Planned SDK-dependent stdio registration/mapping. | `src/project_standards/mcp_server/` |

### 5.2 Existing Behavior

The installed distribution and source package repository already validate exact payloads. Reconciliation already emits stable JSON and executor preconditions. Provider declarations already carry operation/phase/effect and typed schemas. The current `invoke_provider` path executes verified Python provider bytes in-process against the resolved consumer root and has no timeout or cancellation boundary; its direct-dispatch results are authoritative. T1 must approve the MCP-facing execution bound, and T4 must run that same dispatcher against the same effective root behind a worker boundary so CLI/control-plane semantics do not change accidentally. There is no MCP dependency, service facade, entrypoint, protocol adapter, or MCP client documentation.

### 5.3 Files Expected to Change

| Path | Action | Purpose | Owning task |
| --- | --- | --- | --- |
| `docs/adr/adr-0025-project-standards-mcp-service-and-sdk-boundary.md` | create | SDK-independent facade, adapter, dependency, and provider-execution boundary. | T1 |
| `docs/adr/adr-0026-project-standards-mcp-local-read-only-transport.md` | create | stdio/read-only scope, roots, resource URIs, capability rules, and remote deferral. | T1 |
| `docs/adr/README.md` | modify | Index the accepted Step 09 decisions. | T1 |
| `docs/research/2026-07-28-project-standards-mcp-protocol-sdk-client-matrix.md` | create/modify | Final official-source, license, conformance, and Codex/Claude evidence. | T1, T11 |
| `docs/research/2026-07-07-project-standards-mcp-specification-reference-pack.md` | modify | Replace the pre-publication protocol/SDK baseline with the frozen contract. | T1 |
| `docs/research/index.md` | modify | Index the final matrix and current reference-pack state. | T1 |
| `docs/specs/2026-07-07-project-standards-mcp-enablement-roadmap-spec.md` | modify | Resolve and revision the Step 09 roadmap questions. | T1 |
| `docs/specs/2026-07-07-project-standards-mcp-server-implementation-spec.md` | modify | Resolve/revision T1 questions and record the T11 real-consumer decision. | T1, T11 |
| `docs/specs/README.md` | modify | Keep exact governing-spec revisions/statuses current. | T1, T11 |
| `pyproject.toml`, `uv.lock` | modify | Exact approved MCP dependency. | T1 |
| `src/project_standards/mcp_services/` | create | SDK-independent facade/models. | T2-T4 |
| `src/project_standards/mcp_server/` | create | stdio adapter/resources/prompts/tools. | T5-T9 |
| `src/project_standards/cli.py` | modify | Local `project-standards mcp` launch. | T5 |
| `tests/mcp_services/` | create | Facade contract and security tests. | T2-T4 |
| `tests/mcp_server/` | create | Protocol, resource, prompt, tool, client tests. | T5-T10 |
| `.github/workflows/check.yml` | modify if needed | Run the existing test gate with MCP tests; no new workflow. | T10 |
| `README.md`, `docs/mcp-server.md`, `CHANGELOG.md` | modify/create | Client setup, reference, security boundary, troubleshooting, and an Unreleased feature record. | T11 |
| `docs/STATUS.md`, `docs/handoff/state.md`, `docs/handoff/specs-plans.md`, `docs/handoff/sessions/{YYYY-MM}.md` | modify | Verified unpublished-candidate status and durable closeout. | T12 |

### 5.4 Dependencies

| Dependency | Type | Version / constraint | Reason |
| --- | --- | --- | --- |
| Official `mcp` Python SDK | runtime | Exact stable-compatible constraint selected by T1 | Protocol implementation behind adapter. |
| Pydantic 2 | existing runtime | Existing repository constraint | Typed service and result contracts. |
| Codex CLI | external client | Current installed supported build | Required client smoke matrix. |
| Claude Code | external client | Current installed supported build | Required client smoke matrix. |

No MCP dependency is added until T1 records final official-source, license, conformance, and client evidence.

### 5.5 Required Internal Interfaces

These names and protocol-neutral shapes are the implementation contract unless T1 records an approved change in ADR 0025 and updates this plan through the discovered-work checkpoint before T2 starts. A literal implementer must not invent parallel models or expose SDK types from `mcp_services`.

| Interface | Inputs | Required result / invariant | Owning task |
| --- | --- | --- | --- |
| `McpServiceFacade.from_installed` | `InstalledDistribution`, exact `CatalogMajor` | Eagerly validates the complete bounded installed catalog—every selected family, payload declaration, payload byte, and aggregate digest—before constructing the facade; any invalid element aborts construction and no valid subset is exposed. | T2 |
| `McpServiceFacade.from_source` | Explicit `PackageRepository`, exact catalog major | Development/test-only construction; returns the same stable facts as installed construction for equivalent bytes. | T2 |
| `McpServiceFacade.catalog` | No mutable alias | `CatalogDescriptor` containing `catalog_major` and ordered exact `StandardDescriptor` values. | T2 |
| `McpServiceFacade.standard` | `standard_id`, exact `version` | One V2-derived `StandardDescriptor`; unknown ID/version is a structured not-found failure. | T2 |
| `McpServiceFacade.resource` | `standard_id`, exact `version`, declared `resource_id` | `ResourceContent` containing the exact `ResourceDescriptor` and verified bytes; each read rechecks the selected declaration, contained path, and current byte digest after startup validation; no arbitrary path input. | T2 |
| `McpServiceFacade.inspect_repo` | Explicit `repo_root` | `RepoInspectionSnapshot` containing only normalized root, desired/catalog/lock state, and bounded findings. | T3 |
| `McpServiceFacade.reconcile` | Explicit `repo_root` | Every public field from `ReconciliationPlan.to_jsonable()` plus `reconciliation_fingerprint`; no apply and no executor-only proposed bytes. A preview exists only where the authoritative planner produced a plan; every other outcome is a structured failure, and EC-005's findings requirement is satisfied by the T9 `reconcile_preview` tool composing `inspect_repo` (clarified 2026-07-30, T9 RED review F1). | T3 |
| `McpServiceFacade.invoke_read_provider` | Explicit root, exact standard/version/provider/operation, typed input | Only T1-approved non-mutating effects; exact `ProviderOperationResult`; timeout/cancellation returns a structured failure and leaves the repository unchanged. | T4 |
| `McpServiceFacade.validate_repo` | Explicit `repo_root` | `ValidationReport` produced by selecting applicable validate/verify/lint declarations from the current exact consumer resolution and invoking them only through `invoke_read_provider`. | T4 |
| `McpServiceFacade.drift_check` | Explicit `repo_root` | `DriftReport` preserving reconciliation actions/findings/fingerprint and applicable drift-check provider results; no invented confidence, relevance, or clean-state boolean. | T4 |
| `resolve_effective_root` | Explicit `repo_root`; optional keyword-only boundary inputs `configured_boundary` (the ADR 0026 launch-time boundary) and `client_roots` (client-advertised roots), both defaulting to none (parameter names frozen 2026-07-29, T5 RED review F3) | The normalized, symlink-resolved explicit root after containment validation. When T1 enables client roots, the explicit root must equal or descend from one advertised root; client roots may reject an input but never replace a missing `repo_root`, select a different repository, or widen the boundary. | T5 |
| `create_server` / `run_stdio` | Facade and T1-frozen adapter configuration | One selected-SDK adapter; protocol messages only on stdout; all logs on stderr; capabilities equal registrations. | T5 |

Protocol-neutral DTOs have these minimum fields:

| DTO | Required stable fields |
| --- | --- |
| `CatalogDescriptor` | exact `catalog_major` and ordered exact `StandardDescriptor` values |
| `StandardDescriptor` | `standard_id`, `title`, `status`, exact `package_version`, `exposure`, ordered `capabilities`, exact `relationships` (one `RelationshipSet`), ordered resource descriptors, ordered provider descriptors (`ProviderDescriptor` values) |
| `RelationshipSet` | `companions`, `extends`, `conflicts`: ordered standard-ID tuples, each defaulting to empty (independence is the empty default) |
| `ProviderDescriptor` | `provider_id`, `operation`, `kind`, `phase`, `effect`, `entrypoint` (payload-qualified; absent for documentation-only), `input_schema` and `output_schema` declared resource IDs (absent for documentation-only), and sorted unique `resources` |
| `ResourceDescriptor` | canonical URI, `resource_id`, role, media type, digest, `standard_id`, exact package version |
| `ResourceContent` | one `ResourceDescriptor` plus exact immutable bytes |
| `RepoInspectionSnapshot` | `repo_root` (normalized root identity, serialized as `.`), `state` (explicit authoritative state classification, including missing/invalid), `desired_config`, `consumer_catalog`, `central_lock` (each the parsed authoritative state or explicitly absent), and ordered bounded `findings` (field-by-field freeze 2026-07-29 from the T3 RED review; the SPEC-MS01 §9 sketch's `warnings` name is superseded and reconciled at T3 close-out) |
| `Finding` | `rule_id` mapped from `ControlFinding.code`, severity, `standard_id`, version, root-relative path, identity, message, remediation mapped from `hint`, and every optional line/locus/conflict/digest field when present |
| `reconcile_preview` tool result | Closed two-slot envelope with required nullable fields `preview` (the exact `McpServiceFacade.reconcile` projection) and `control_plane` (the exact `RepoInspectionSnapshot` projection), exactly one non-null; the slot follows the authoritative state classification (`initialized` publishes `preview`; every other classification publishes `control_plane` via `inspect_repo`), never a caught `ServiceError` code; both arms serialize verbatim, so DR-004 is preserved and EC-005 is satisfied at the tool layer (field freeze 2026-07-30, T9 RED review F1, T3.3 arbitration lineage) |
| `ReconciliationPreview` | all public `ReconciliationPlan.to_jsonable()` fields: `applicable`, `actions`, `units`, `findings`, `preconditions`, `resolution`, `verification_requests`, `provider_notices`, `namespace_prunes`, `catalog_refresh`, and `next_lock`; plus `reconciliation_fingerprint` |
| `ProviderOperationResult` | exact identity and operation, declared phase/effect, status, findings, bounded diagnostics, and every declared output-schema field |
| `ValidationReport` | normalized root identity serialized as `.`, exact selected standard/version/provider operations, ordered `ProviderOperationResult` values, and ordered findings |
| `DriftReport` | normalized root identity serialized as `.`, reconciliation fingerprint, authoritative actions/findings, ordered drift-check `ProviderOperationResult` values, and no synthesized clean/drift boolean unless an existing typed control-plane service supplies it |
| `ServiceError` | stable code, message, affected standard/path when applicable, severity when applicable, and remediation; never raw secret/file content |

All collections use the ordering already declared by package/control-plane models or an explicit documented key. The resolved absolute consumer root is used only for containment and service calls; stable results serialize that root as `.` and every child path relative to it. Timestamps and durations are absent from stable DTOs. Raw provider diagnostics are bounded supplemental text and never participate in fingerprints.

## 6. Test Strategy

- **Framework:** pytest through uv. Config: `pyproject.toml`; roots: `tests/mcp_services/` and `tests/mcp_server/`; shared fixtures extend current package/control-plane fixtures without changing package contracts.
- **Commands:** targeted `uv run pytest {path}::{test}`; file `uv run pytest {path}`; MCP subset `uv run pytest tests/mcp_services tests/mcp_server`; ordinary suite `uv run coverage run --source=project_standards -m pytest -m "not performance and not compatibility"`; compatibility `uv run pytest -m compatibility -n 4 --dist load --max-worker-restart=0`; performance `uv run pytest -m performance`; report `uv run coverage report`; static `uv run ruff format --check .`, `uv run ruff check .`, `uv run basedpyright`; audit `uv run pip-audit`.
- **Package parity:** build one candidate wheel, extract it once, put that directory first on `PYTHONPATH`, then run MCP integration and client smoke checks against the same bytes.
- **Invariant coverage:** use pytest parametrization/permutations for URI canonicalization, root/symlink containment, package-growth/tool-list invariance, relationship ordering, and deterministic normalization. Hypothesis is not a current repository dependency and shall not be added solely for this plan; a new property-testing dependency requires separately approved discovered work.

### 6.1 RED-GREEN-REFACTOR Contract

For T2-T10, add one focused failing behavior test, verify it fails only because the specified behavior is absent, implement the smallest production change, verify targeted and nearest regressions, refactor without changing behavior, then run task tests plus Ruff and BasedPyright. A missing planned symbol is asserted inside a collected black-box test so RED is not a collection/import failure. Commit `T{n}: {summary} ({FR/NFR ids}, {TC ids})`.

### 6.2 Test Categories

| Category | Purpose | Location |
| --- | --- | --- |
| Characterization | Pin existing package/control-plane output. | `tests/mcp_services/characterization/` |
| Unit | Service and mapping behavior. | `tests/mcp_services/`, `tests/mcp_server/` |
| Contract | Public service/protocol schemas and import boundary. | `tests/mcp_services/contract/`, `tests/mcp_server/contract/` |
| Integration | Installed/source distribution and stdio exchange. | `tests/mcp_server/integration/` |
| Security | Containment, digest, content exclusion, no writes. | `tests/mcp_services/security/`, `tests/mcp_server/security/` |
| End-to-end | Codex/Claude local setup and calls. | `tests/mcp_server/e2e/` plus recorded smoke evidence |

### 6.3 TDD Exceptions

| Task | Exception reason | Objective validation |
| --- | --- | --- |
| T1 | Decision research, ADRs, and dependency selection precede code. | Official-source register, ADR/frontmatter validation, dependency resolution, license/audit evidence. |
| T11 | Client docs and live smoke evidence are not wholly expressible as failing pytest behavior. | Installed-wheel protocol tests, `codex mcp list`, Claude `/mcp`/CLI inspection, documentation gates. |
| T12 | Integration close-out changes no behavior; its permanent `T12.0`/`T12.6` labels are intentionally non-contiguous, and `plan.py validate`/`sync` preserve them. | Full repository/package/docs gates, exact checklist-label projection, and diff allowlist. |

## 7. Execution Summary

| Task | Title | Phase | Depends on | Requirement(s) | Primary verification |
| --- | --- | --- | --- | --- | --- |
| T1 | Freeze protocol, SDK, clients, and boundary | P1 | None | FR-029, FR-030, NFR-011 | ADR/source/license/client gate |
| T2 | Build exact package-resource services | P2 | T1 | FR-001-003, FR-006, FR-015, FR-021, FR-026-027, NFR-005-007, NFR-010, NFR-013, IR-004, DR-001-002, DR-006, DR-009 | `uv run pytest tests/mcp_services/test_catalog.py tests/mcp_services/test_resources.py` |
| T3 | Build consumer inspection and reconciliation services | P2 | T2, T13 | FR-009, FR-011, FR-015, FR-017, FR-024, FR-026, FR-028, NFR-005-006, IR-004-005, IR-007, DR-004-005, DR-009 | `uv run pytest tests/mcp_services/test_consumer.py` |
| T4 | Build bounded non-mutating provider services | P2 | T2, T3 | FR-012-015, FR-026, NFR-005-006, IR-004, IR-009, DR-003, DR-008-009 | `uv run pytest tests/mcp_services/test_providers.py tests/mcp_services/test_provider_worker.py` |
| T5 | Add stdio adapter and capability boundary | P3 | T2, T3, T4 | FR-018, FR-024-025, NFR-003-004, NFR-006, NFR-008, NFR-013, IR-001, IR-006-008, DR-007 | `uv run pytest tests/mcp_server/test_transport.py` |
| T6 | Expose exact resources | P3 | T5 | FR-001-004, FR-006, FR-021, FR-027, NFR-001-002, NFR-005, NFR-007, IR-002, DR-002 | `uv run pytest tests/mcp_server/test_resources.py` |
| T7 | Add prompts and shared read fallback | P3 | T6 | FR-005, FR-008 | `uv run pytest tests/mcp_server/test_prompts.py tests/mcp_server/test_standard_read.py` |
| T8 | Add catalog and repo inspection tools | P4 | T5, T6, T7 | FR-007, FR-009, FR-021-024, NFR-012, IR-003, DR-005-006 | `uv run pytest tests/mcp_server/test_discovery_tools.py` |
| T9 | Add reconciliation and provider tools | P4 | T3, T4, T5, T7 | FR-011-014, FR-017-019, FR-022-024, FR-028, NFR-012, IR-003, IR-009, DR-004, DR-008 | `uv run pytest tests/mcp_server/test_consumer_tools.py` |
| T10 | Prove protocol, safety, determinism, and CI | P5 | T6, T7, T8, T9 | FR-010, FR-018, FR-025, FR-029, NFR-001, NFR-003-006, NFR-008-009, NFR-011-013, IR-008, DR-003, DR-007, DR-009 | `uv run pytest tests/mcp_services tests/mcp_server` |
| T11 | Prove installed-wheel clients and document use | P5 | T10 | FR-016, FR-020, FR-030, NFR-009-011 | candidate-wheel client smoke matrix |
| T12 | Run final gate and prepare handoff | P5 | T11 | All | complete scoped verification gate |
| T13 | Extend provider descriptors to the declared execution contract | P2 | T2 | FR-021, NFR-005, DR-001, DR-009 | `uv run pytest tests/mcp_services/test_catalog.py tests/mcp_services/contract/test_facade.py` |
| T14 | Dispatch composite providers with authoritative typed input | P2 | T4, T15 | FR-012-013, NFR-005, DR-009 | `uv run pytest tests/mcp_services/test_providers.py` |
| T15 | Publish the provider-dispatch-input authority seam | P2 | T4 | FR-015, NFR-005, DR-009 | `uv run pytest tests/control_plane/test_command_resolution.py` |

### 7.1 Checklist Execution Protocol

Before T1, the implementing agent must:

1. Run `git status --short --branch` and `git log -5 --oneline`; preserve unrelated work and confirm the approved plan commit is in the current branch history.
2. Run `uv run scripts/plan.py validate docs/plans/2026-07-24-project-standards-mcp-server-plan.md`.
3. If `.project-pipeline/2026-07-24-project-standards-mcp-server/` is absent, run `uv run scripts/plan.py generate docs/plans/2026-07-24-project-standards-mcp-server-plan.md`; otherwise run `uv run scripts/plan.py sync docs/plans/2026-07-24-project-standards-mcp-server-plan.md`.
4. Run `rg --no-filename '^## T[0-9]+:' .project-pipeline/2026-07-24-project-standards-mcp-server/p*.md | sed -E 's/^## (T[0-9]+):.*/\1/' | sort | uniq -c` and `rg --no-filename '^- \[[ x]\] T[0-9]+\.[0-9]+' .project-pipeline/2026-07-24-project-standards-mcp-server/p*.md | sed -E 's/^- \[[ x]\] (T[0-9]+\.[0-9]+).*/\1/' | sort | uniq -c`; every task and sub-task ID must appear exactly once. If not, stop before T1 and correct the master-plan grammar or checklist projection, then regenerate/sync and recheck.
5. Run `uv run scripts/plan.py next docs/plans/2026-07-24-project-standards-mcp-server-plan.md`; execute only a reported ready task. Update only checklist state fields and one-line `ev:` pointers to logs. Put durable discoveries in this master plan and run `plan.py sync`; do not silently add work in an ephemeral checklist.

## 8. Implementation Tasks

### Phase P1: Decision Gate

#### T1: Freeze protocol, SDK, clients, and service boundary

- **goal:** Produce accepted Step 09 decisions and an exact stable dependency contract before any MCP code. · **phase:** P1 · **depends_on:** [] · **requirements:** [FR-029, FR-030, NFR-011] · **priority:** must
- **files:** `docs/adr/adr-0025-project-standards-mcp-service-and-sdk-boundary.md` (create), `docs/adr/adr-0026-project-standards-mcp-local-read-only-transport.md` (create), `docs/adr/README.md` (modify), `docs/research/2026-07-28-project-standards-mcp-protocol-sdk-client-matrix.md` (create), `docs/research/2026-07-07-project-standards-mcp-specification-reference-pack.md` (modify), `docs/research/index.md` (modify), `docs/specs/2026-07-07-project-standards-mcp-enablement-roadmap-spec.md` (modify), `docs/specs/2026-07-07-project-standards-mcp-server-implementation-spec.md` (modify), `docs/specs/README.md` (modify), `pyproject.toml` (modify), `uv.lock` (modify)
- **preconditions:** approved `SPEC-RD01` 1.5 and `SPEC-MS01` 1.1; final 2026-07-28 protocol publication and official SDK release evidence are available; no `src/project_standards/mcp_*` implementation exists.
- **interface/data:** ADR 0025 must freeze facade names/shapes from §5.5, exact SDK/version constraint and packaging group, one adapter direction, a numeric provider timeout, worker termination/reaping and IPC cleanup, bounded result/diagnostic IPC, and capture of worker stdout/stderr without inheriting protocol stdout. It must require the worker to invoke the existing dispatcher with exact installed payload identity and typed JSON-safe input against the resolved effective consumer root so results remain equivalent to authoritative direct dispatch. ADR 0026 must freeze stdio/read-only scope, CLI form, URI canonicalization, explicit-root/client-root rules, exact capability/list-change semantics, the v1 tool/prompt/fallback registry, and remote/write deferral. The matrix must cite official sources and record exact executable probes for Codex and Claude. The implementer must prepare the evidence and candidate ADRs, then obtain recorded owner approval for the owner-owned decisions in `SPEC-RD01 OQ-001` and `SPEC-MS01 OQ-001`, `SPEC-MS01 OQ-002`, and `SPEC-MS01 OQ-007` before T1 GREEN. With that approval, T1 must resolve `SPEC-RD01 OQ-001` and `SPEC-RD01 OQ-002`; resolve `SPEC-MS01 OQ-001`, `SPEC-MS01 OQ-002`, `SPEC-MS01 OQ-003`, `SPEC-MS01 OQ-004`, and `SPEC-MS01 OQ-006`; and record an include/omit disposition for `SPEC-MS01 OQ-007`. `SPEC-MS01 OQ-005` remains open for T11's owner-approved real-consumer smoke decision. For each owning spec changed, append exactly one next sequential revision row summarizing all T1 question status/disposition updates, update `last_reviewed` and `docs/specs/README.md`, update the matrix and reference-pack entries in `docs/research/index.md`, and add a deviation row when an accepted outcome differs from the current assumption.
- **stop/backtrack:** if the final protocol is unavailable, no stable-compatible SDK/client combination passes, license/conformance evidence is unacceptable, recorded approval for any owner-owned T1 decision is absent, or a §5.5 service cannot be supplied without duplicating domain semantics, stop before dependency changes, spec-status changes, or T1 GREEN and return to `SPEC-MS01`/owner decision. Do not select a prerelease or hand-roll JSON-RPC implicitly.
- **acceptance:** official final protocol/SDK/license/conformance evidence is recorded (TC-T1-001); Codex/Claude feature matrix freezes required fallbacks (TC-T1-002); `SPEC-RD01 OQ-001`, `SPEC-RD01 OQ-002`, `SPEC-MS01 OQ-001`, `SPEC-MS01 OQ-002`, `SPEC-MS01 OQ-003`, `SPEC-MS01 OQ-004`, and `SPEC-MS01 OQ-006` are resolved, `SPEC-MS01 OQ-007` has an explicit include/omit disposition, `SPEC-MS01 OQ-005` remains explicitly assigned to T11, owning spec statuses/revisions/deviations and both indexes are current, ADR 0026 records the selected CLI form, the matrix and ADRs freeze observed client resource/prompt/root behavior, and accepted ADRs prohibit remote/write scope and SDK types beyond the adapter.
- **sub-tasks:**
  - **T1.0 CHARACTERIZE** — after the 2026-07-28 final publication, recheck the protocol, official SDK releases/docs/license/conformance, current Codex/Claude behavior, current package/control-plane service seams, the existing unbounded in-process provider dispatcher, and every namespaced owning-spec question listed in `interface/data`.
  - **T1.1 RED** — write the decision-gate evidence and candidate ADRs, then run their objective acceptance checks. Expected failure: no exact approved stable-compatible SDK constraint, accepted boundary ADRs, or final client matrix exists yet.
  - **T1.2 Verify RED** — confirm the gate fails only on unresolved Step 09 decisions, unavailable final releases, or missing recorded owner approval, not stale repository evidence; obtain and record approval for every owner-owned decision or stop before T1 GREEN.
  - **T1.3 GREEN** — with recorded owner approval, accept the service/SDK and local-transport ADRs; resolve `SPEC-RD01 OQ-001`, `SPEC-RD01 OQ-002`, `SPEC-MS01 OQ-001`, `SPEC-MS01 OQ-002`, `SPEC-MS01 OQ-003`, `SPEC-MS01 OQ-004`, and `SPEC-MS01 OQ-006`; disposition `SPEC-MS01 OQ-007`; preserve `SPEC-MS01 OQ-005` for T11; update owning statuses, one next sequential revision row per changed spec, `last_reviewed`, the spec index, the matrix/reference-pack rows in `docs/research/index.md`, and any required deviation row; freeze resource/root/capability/provider timeout/worker/direct-dispatch-parity contracts; add only the approved exact SDK constraint; and resolve `uv.lock`.
  - **T1.4 Verify GREEN** — validate ADR/research/spec Markdown, dependency resolution, license and `uv run pip-audit` results, revision-appropriate conformance probes, the Codex/Claude matrix, namespaced question statuses, sequential revisions/deviations, and exact spec/research indexes.
  - **T1.5 REFACTOR** — consolidate version-sensitive facts in the dated evidence matrix and adapter decisions; leave no MCP source module or duplicated protocol authority.
  - **T1.6 Verify Task** — run `uv lock --check`, `uv sync --locked --all-groups`, `uv run pip-audit`, and every exact protocol/client probe recorded in the matrix. Then run `MCP_T1_WHEEL_OUT="$(mktemp -d)"`, `MCP_T1_WHEEL_RUNTIME="$(mktemp -d)"`, `uv build --wheel --out-dir "$MCP_T1_WHEEL_OUT"`, `python -m zipfile -e "$MCP_T1_WHEEL_OUT"/project_standards-*.whl "$MCP_T1_WHEEL_RUNTIME"`, `export PYTHONPATH="$MCP_T1_WHEEL_RUNTIME${PYTHONPATH:+:$PYTHONPATH}"`, `uv run project-standards validate`, `uv run project-standards spec validate docs/specs/2026-07-07-project-standards-mcp-enablement-roadmap-spec.md docs/specs/2026-07-07-project-standards-mcp-server-implementation-spec.md`, `uv run project-standards spec lint --strict docs/specs/2026-07-07-project-standards-mcp-enablement-roadmap-spec.md docs/specs/2026-07-07-project-standards-mcp-server-implementation-spec.md`, `npx prettier --check docs/adr/adr-0025-project-standards-mcp-service-and-sdk-boundary.md docs/adr/adr-0026-project-standards-mcp-local-read-only-transport.md docs/adr/README.md docs/research/2026-07-28-project-standards-mcp-protocol-sdk-client-matrix.md docs/research/2026-07-07-project-standards-mcp-specification-reference-pack.md docs/research/index.md docs/specs/2026-07-07-project-standards-mcp-enablement-roadmap-spec.md docs/specs/2026-07-07-project-standards-mcp-server-implementation-spec.md docs/specs/README.md`, `npx markdownlint-cli2 --no-globs :docs/adr/adr-0025-project-standards-mcp-service-and-sdk-boundary.md :docs/adr/adr-0026-project-standards-mcp-local-read-only-transport.md :docs/adr/README.md :docs/research/2026-07-28-project-standards-mcp-protocol-sdk-client-matrix.md :docs/research/2026-07-07-project-standards-mcp-specification-reference-pack.md :docs/research/index.md :docs/specs/2026-07-07-project-standards-mcp-enablement-roadmap-spec.md :docs/specs/2026-07-07-project-standards-mcp-server-implementation-spec.md :docs/specs/README.md`, and `git diff --check`; assert every namespaced question status/revision/index/deviation duty above is satisfied, confirm no MCP source module exists yet, then commit with IDs.

### Phase P2: SDK-independent Services

#### T2: Build exact package-resource services

- **goal:** Return deterministic installed catalog, exact metadata, and digest-checked resource bytes without importing MCP. · **phase:** P2 · **depends_on:** [T1] · **requirements:** [FR-001, FR-002, FR-003, FR-006, FR-015, FR-021, FR-026, FR-027, NFR-005, NFR-006, NFR-007, NFR-010, NFR-013, IR-004, DR-001, DR-002, DR-006, DR-009] · **priority:** must
- **files:** `src/project_standards/mcp_services/__init__.py` (create), `src/project_standards/mcp_services/models.py` (create), `src/project_standards/mcp_services/catalog.py` (create), `tests/mcp_services/contract/test_facade.py` (create), `tests/mcp_services/test_catalog.py` (create), `tests/mcp_services/test_resources.py` (create)
- **preconditions:** T1 is done; ADR 0025 names the approved facade/dependency boundary; `tests/control_plane/test_distribution.py` and `tests/package_contract/test_repository.py` are green before RED.
- **interface/data:** export only `McpServiceFacade` and protocol-neutral DTO/error types from `mcp_services/__init__.py`. Construct production state only from `InstalledDistribution.load_catalog(exact_major)`, which must eagerly validate the complete bounded installed distribution before the facade becomes usable; source construction accepts an already validated `PackageRepository`. Resource lookup accepts IDs, never filesystem paths, and rechecks the selected declaration, contained path, and current byte digest before returning bytes. Cache only immutable catalog/descriptor facts inside one facade instance; cached content must not bypass the per-read byte/digest check.
- **stop/backtrack:** if `InstalledDistribution` or `PackageRepository` lacks a fact required by §5.5, stop and record an OQ/spec deviation; do not parse V1 manifests, CLI JSON/text, directory names, or Markdown to fill the gap. Any installed family/payload finding aborts facade construction rather than producing a partial catalog.
- **acceptance:** current and alternate catalog generations remain distinct (TC-T2-001); exact resources verify declaration/path/digest, preserve every descriptor field, and reject every invalid case (TC-T2-002, TC-T2-007); source fixture and installed projection expose equivalent stably normalized facts without consumer-repo scanning (TC-T2-003); the facade imports without MCP, descriptors use validated V2 package facts, and relationships preserve V2 semantics (TC-T2-004, TC-T2-005, TC-T2-006).
- **sub-tasks:**
  - **T2.0 CHARACTERIZE** — pin current `InstalledDistribution` and `PackageRepository` catalog/resource results without changing them.
  - **T2.1 RED** — add collected black-box facade tests for catalog generation, exact version/resource lookup, relationships, digest/path failures, source/installed parity, V2 descriptors, and the SDK import boundary.
  - **T2.2 Verify RED** — confirm assertions fail because the facade behavior is absent, not because tests fail to collect/import unrelated code.
  - **T2.3 GREEN** — add the smallest SDK-free typed facade over existing public APIs; no manifest parsing or mutable alias.
  - **T2.4 Verify GREEN** — rerun facade/resource tests and the nearest installed-distribution/package-repository regressions.
  - **T2.5 REFACTOR** — centralize only deterministic DTO mapping/cache ownership; keep domain semantics below the facade.
  - **T2.6 Verify Task** — run `uv run pytest tests/mcp_services/contract/test_facade.py tests/mcp_services/test_catalog.py tests/mcp_services/test_resources.py tests/control_plane/test_distribution.py tests/package_contract/test_repository.py`, `uv run ruff check src/project_standards/mcp_services tests/mcp_services`, `uv run ruff format --check src/project_standards/mcp_services tests/mcp_services`, and `uv run basedpyright`; commit with IDs.

#### T3: Build consumer inspection and reconciliation services

- **goal:** Inspect explicit `.standards/` state and return the existing reconciliation plan/fingerprint without reading unrelated content. · **phase:** P2 · **depends_on:** [T2, T13] · **requirements:** [FR-009, FR-011, FR-015, FR-017, FR-024, FR-026, FR-028, NFR-005, NFR-006, IR-004, IR-005, IR-007, DR-004, DR-005, DR-009] · **priority:** must
- **files:** `src/project_standards/mcp_services/consumer.py` (create), `tests/mcp_services/test_consumer.py` (create), `tests/mcp_services/security/test_consumer_boundaries.py` (create)
- **preconditions:** T2 is done; the same facade instance can resolve selected installed payloads; existing state/planner/executor tests are green.
- **interface/data:** implement the `inspect_repo` and `reconcile` methods from §5.5 by composing `detect_control_plane_state`/control-plane codecs, `PlannerRequest`, `plan_reconciliation`, and `reconciliation_fingerprint`. Each consumer-operation call reloads the current bounded `.standards/` snapshot; never cache consumer state across calls. Read only `.standards/config.toml`, `.standards/catalog.toml`, `.standards/lock.toml`, and exact paths already requested by authoritative planner/provider APIs. Map paths to root-relative stable values; never return file contents.
- **stop/backtrack:** reject nonexistent, non-directory, traversal, or root-escaping inputs before state loading; resolve symlinks and reject when the resolved target escapes an approved boundary rather than rejecting safe in-bound symlinks categorically. If stable preview fields cannot be preserved without changing the control-plane public schema, stop and return to the spec/ADR rather than inventing an MCP plan schema.
- **acceptance:** missing/partial/valid control-plane fixtures return typed snapshots and stable plan JSON, and a state change between calls is reflected without restarting the facade (TC-T3-001); fingerprints/preconditions match executor values (TC-T3-002); traversal, symlink escape, `.env`, credentials, and unrelated content are never read/returned (TC-T3-003, TC-T3-004); the snapshot preserves the bounded typed DR-005 fields (TC-T3-005).
- **sub-tasks:**
  - **T3.1 RED** — add snapshot/reconciliation/refresh/root/content-exclusion tests; expected failure is absent facade behavior.
  - **T3.2 Verify RED** — prove fixtures and existing planner outputs are valid and only the facade expectations fail.
  - **T3.3 GREEN** — compose current config/catalog/lock codecs and planner under normalized explicit roots; preserve stable serialization.
  - **T3.4 Verify GREEN** — targeted plus current control-plane planner/executor regressions.
  - **T3.5 REFACTOR** — share only path/result normalization needed by T2/T3.
  - **T3.6 Verify Task** — run `uv run pytest tests/mcp_services/test_consumer.py tests/mcp_services/security/test_consumer_boundaries.py tests/control_plane/test_state.py tests/control_plane/test_planner.py tests/control_plane/test_executor.py tests/control_plane/test_codec.py`, `uv run ruff check src/project_standards/mcp_services tests/mcp_services`, `uv run ruff format --check src/project_standards/mcp_services tests/mcp_services`, and `uv run basedpyright`; commit with IDs.

#### T4: Build bounded non-mutating provider services

- **goal:** Dispatch exact-payload validate/verify/lint/drift/helper operations with typed results and bounded execution while rejecting mutating effects. · **phase:** P2 · **depends_on:** [T2, T3] · **requirements:** [FR-012, FR-013, FR-014, FR-015, FR-026, NFR-005, NFR-006, IR-004, IR-009, DR-003, DR-008, DR-009] · **priority:** must
- **files:** `src/project_standards/mcp_services/providers.py` (create), `src/project_standards/mcp_services/provider_worker.py` (create), `src/project_standards/mcp_services/catalog.py` (modify), `src/project_standards/mcp_services/__init__.py` (modify), `src/project_standards/mcp_services/consumer.py` (modify), `tests/mcp_services/test_providers.py` (create), `tests/mcp_services/test_provider_worker.py` (create), `tests/mcp_services/security/test_provider_effects.py` (create), `tests/mcp_services/contract/test_facade.py` (modify)
- **preconditions:** T1 has frozen the numeric execution bound, worker lifecycle, and exact allowed helper set; T2-T3 are done; `tests/control_plane/test_providers.py` is green and confirms the authoritative dispatcher remains in-process/unbounded.
- **interface/data:** the mandatory allowlist is validate, verify, lint, and drift-check; add another operation only when ADR 0025 enumerates it. `validate_repo` uses T3's current exact resolution to select only applicable validate/verify/lint declarations. `drift_check` returns reconciliation actions/findings/fingerprint plus applicable drift-check results and does not invent a summary boolean. Reject every unlisted operation and every `ProviderEffect.MUTATION_PLAN` before worker creation. The worker receives the resolved effective consumer root, exact installed payload identity, and typed JSON-safe input; invokes the existing dispatcher against that root; and returns `ProviderOperationResult` only through bounded IPC. Its results must match authoritative direct dispatch for the same root, payload, operation, and input after the declared stable normalization. Capture worker stdout/stderr so neither Python-level nor file-descriptor diagnostics reach protocol stdout; bound returned diagnostics, terminate and reap the worker on timeout or cancellation, and close worker/IPC resources on every exit. Controlled-fixture before/after assertions must prove every supported operation leaves the consumer filesystem unchanged. Map root paths to stable root-relative paths, `ControlFinding.code` to `rule_id`, and `hint` to `remediation` without dropping identity fields.
- **stop/backtrack:** if the worker cannot enforce the numeric timeout, termination/reaping, bounded IPC, and stdout/stderr isolation while preserving direct-dispatch results, if a supported declared non-mutating operation changes the consumer filesystem, or if a result cannot preserve its declared output schema, stop and revisit ADR 0025. Never change authoritative dispatcher semantics, add a new sandboxing layer, run provider code in the MCP transport process, swallow a mutation plan, or weaken filesystem no-write assertions.
- **acceptance:** declared non-mutating operations preserve typed fields and stable normalization (TC-T4-001); unknown providers/operations and every mutating effect fail before dispatch (TC-T4-002); raw diagnostics are bounded and excluded from fingerprints (TC-T4-003); every Finding field required by DR-003 is schema-tested (TC-T4-004); a deliberately slow provider terminates at the T1-approved bound with a structured diagnostic (TC-T4-005); dispatch remains exact-payload-qualified and preserves declared result fields (TC-T4-006, TC-T4-007); worker results match authoritative direct dispatch for the same effective root and input, controlled-fixture files remain unchanged, and worker stdout/stderr cannot contaminate protocol stdout (TC-T4-008).
- **sub-tasks:**
  - **T4.0 CHARACTERIZE** — pin the current `invoke_provider` behavior: it executes verified provider bytes in-process without a timeout or cancellation boundary; record this against the T1 decision.
  - **T4.1 RED** — add validate/drift orchestration, allowlist, exact qualification, required Finding fields, typed-result, normalization, mutation-rejection, direct-dispatch-parity, filesystem-no-write, stdout/stderr-isolation, and deliberately slow-provider bound tests.
  - **T4.2 Verify RED** — confirm current dispatcher fixtures pass and only the missing service/bound contract fails.
  - **T4.3 GREEN** — implement the narrow provider service over existing declarations/dispatcher and run it against the resolved effective consumer root behind the T1-approved worker/timeout/IPC boundary; do not change authoritative CLI/control-plane provider semantics or add a new filesystem sandbox.
  - **T4.4 Verify GREEN** — targeted plus current provider/control-plane tests; confirm the slow fixture cannot hang the suite.
  - **T4.5 REFACTOR** — reuse T2 DTOs without exposing provider internals or SDK types.
  - **T4.6 Verify Task** — run `uv run pytest tests/mcp_services/test_providers.py tests/mcp_services/test_provider_worker.py tests/mcp_services/security/test_provider_effects.py tests/mcp_services/test_consumer.py tests/control_plane/test_providers.py tests/package_contract/test_payload_execution_contracts.py`, `uv run ruff check src/project_standards/mcp_services tests/mcp_services`, `uv run ruff format --check src/project_standards/mcp_services tests/mcp_services`, and `uv run basedpyright`; commit with IDs.

#### T13: Extend provider descriptors to the declared execution contract

- **goal:** Preserve the full V2 `ProviderDeclaration` execution contract in `ProviderDescriptor` and freeze both nested DTO shapes field-by-field per the owner direction of 2026-07-29. · **phase:** P2 · **depends_on:** [T2] · **requirements:** [FR-021, NFR-005, DR-001, DR-009] · **priority:** must
- **files:** `src/project_standards/mcp_services/models.py` (modify), `src/project_standards/mcp_services/catalog.py` (modify), `tests/mcp_services/contract/test_facade.py` (modify), `tests/mcp_services/test_catalog.py` (modify)
- **preconditions:** T2 is done and its battery is green; the owner disposition of the Codex-flagged DTO gap is recorded in `docs/TODO.md`; the amended §5.5 DTO rows define both shapes.
- **interface/data:** extend `ProviderDescriptor` with `entrypoint: str | None`, `input_schema: str | None`, `output_schema: str | None`, and sorted unique `resources: tuple[str, ...]`, each mapped one-to-one from the already validated `ProviderDeclaration` without re-deriving or re-validating execution semantics; documentation-only providers keep the three optional execution fields absent. `RelationshipSet` (`companions`, `extends`, `conflicts`) is ratified as built. No new public exports from `mcp_services/__init__.py`.
- **stop/backtrack:** if `ProviderDeclaration` lacks a fact the amended §5.5 requires, stop and record a spec deviation; do not parse manifests, invent fields, or weaken declaration validation.
- **acceptance:** provider descriptors preserve the declared execution contract for executable and documentation-only providers with deterministic resource ordering (TC-T13-001); the facade contract test freezes the exact field sets of both nested DTOs (TC-T13-002).
- **sub-tasks:**
  - **T13.1 RED** — extend catalog and facade contract tests to assert entrypoint/schema/resource facts per declaration kind and the exact frozen field sets of both nested DTOs.
  - **T13.2 Verify RED** — failures come only from the missing descriptor fields, never from collection, fixtures, or unrelated code.
  - **T13.3 GREEN** — add the four fields to `ProviderDescriptor` and map them in the descriptor builder; change nothing else.
  - **T13.4 Verify GREEN** — rerun the T2 facade/catalog/resource battery plus nearest installed-distribution/package-repository regressions.
  - **T13.5 REFACTOR** — none expected; record `none` when unused.
  - **T13.6 Verify Task** — run `uv run pytest tests/mcp_services/contract/test_facade.py tests/mcp_services/test_catalog.py tests/mcp_services/test_resources.py tests/control_plane/test_distribution.py tests/package_contract/test_repository.py`, `uv run ruff check src/project_standards/mcp_services tests/mcp_services`, `uv run ruff format --check src/project_standards/mcp_services tests/mcp_services`, and `uv run basedpyright`; commit with IDs.

#### T14: Dispatch composite providers with authoritative typed input

- **goal:** Make `validate_repo` and `drift_check` construct per-provider typed input equivalent to authoritative direct dispatch so real packaged providers succeed against real consumer roots, with provider failures isolated as typed per-result failures, per the T11 smoke discovery of 2026-07-30. · **phase:** P2 · **depends_on:** [T4, T15] · **requirements:** [FR-012, FR-013, NFR-005, DR-009] · **priority:** must
- **files:** `src/project_standards/mcp_services/providers.py` (modify), `src/project_standards/mcp_services/provider_worker.py` (modify — input construction moves worker-side per the 2026-07-30 B1 measurement), `src/project_standards/control_plane/provider_inputs.py` (modify — additive no-declared-authority distinction per the T14 review F1; the T15 frozen suite stays green unamended), `tests/mcp_services/test_providers.py` (modify), `tests/mcp_services/test_provider_worker.py` (modify — request-contract rows amended as recorded deviations)
- **preconditions:** T4 and T9 are done with green batteries; the T11 client-matrix evidence records the real-consumer failure (`-32602 provider failed with ValueError` for `adr@1.3/validate-adr` and `markdown-frontmatter@1.6/validate-frontmatter`); the empty-input dispatch sites are `providers.py` `validate_repo` and `drift_check`.
- **interface/data:** composite operations must build each applicable provider's typed input through the T15 public seam (`control_plane.provider_inputs.provider_dispatch_input`), never a parallel reimplementation (FR-015), with construction executed WORKER-SIDE: the worker request carries a small typed seam directive (standard id, operation, provider id, resolved consumer root) rather than the built input — the measured authoritative inputs (290 KB–4.8 MB on this repository) exceed the frozen `REQUEST_LIMIT_BYTES` and that bound is not raised; the worker calls the seam, and plan-bound providers build their own `ReconciliationPlan` in-worker because plans do not cross JSON. TC-T14-001's oracle compares composite results against in-process authoritative direct dispatch (the T4 parity precedent), not input bytes the parent never holds. Standards outside the seam's four families (fixture standards such as `alpha`) keep the existing generic dispatch so the frozen T4/T9/T10 proof nodes stand; a new frozen canary (TC-T14-004) pins that every applicable provider of the shipping catalog is seam-served, so a future family-less real standard fails loudly at test time. Input-side package resolution uses `require_reconciled=False` to match the dispatching worker's own gate. Input construction is deterministic under DR-009; a provider raising during dispatch yields a structured per-result failure in the existing `ProviderOperationResult` failure shape without aborting sibling providers or the composite report; `invoke_read_provider`'s caller-supplied input contract, the §5.5 facade signatures, and the T9 tool registration/schemas are unchanged.
- **stop/backtrack:** if the T15 seam cannot supply a provider's input for a reason its own contract does not cover, stop and route the gap back to T15; if a frozen T4/T9 test pins the whole-call abort behavior, stop for orchestrator arbitration before changing that oracle; do not weaken provider validation, tolerate empty snapshots in packaged providers, or change provider entrypoints.
- **acceptance:** composite dispatch input matches authoritative direct dispatch for the same provider and root (TC-T14-001); a real packaged provider validates a real consumer root through the facade (TC-T14-002); a failing provider isolates to a typed per-result failure while sibling providers complete (TC-T14-003).
- **sub-tasks:**
  - **T14.1 RED** — add a real-packaged-provider fixture path and the three contract tests; remove the echo-only masking that let empty input pass.
  - **T14.2 Verify RED** — failures come only from empty-input dispatch and whole-call abort, never from fixtures, collection, or unrelated code.
  - **T14.3 GREEN** — construct authoritative typed input for composite dispatch and isolate per-result failures; change nothing else.
  - **T14.4 Verify GREEN** — rerun the provider battery, the T9 consumer-tools and no-writes suites, and the nearest facade regressions.
  - **T14.5 REFACTOR** — none expected; record `none` when unused.
  - **T14.6 Verify Task** — run `uv run pytest tests/mcp_services/test_providers.py tests/mcp_server/security/test_no_writes.py tests/mcp_server/test_consumer_tools.py`, `uv run ruff check src/project_standards/mcp_services tests/mcp_services`, `uv run ruff format --check src/project_standards/mcp_services tests/mcp_services`, and `uv run basedpyright`; commit with IDs.

#### T15: Publish the provider-dispatch-input authority seam

- **goal:** Consolidate the four private per-standard provider-input constructions behind one public control-plane function so exactly one authority builds provider typed input, preserving every existing CLI and executor behavior byte-for-byte, per the T14.1 blocked-leg record of 2026-07-30. · **phase:** P2 · **depends_on:** [T4] · **requirements:** [FR-015, NFR-005, DR-009] · **priority:** must
- **files:** `src/project_standards/control_plane/provider_inputs.py` (create), `src/project_standards/control_plane/command_resolution.py` (modify), `src/project_standards/frontmatter_commands.py` (modify), `src/project_standards/validate_frontmatter.py` (modify), `src/project_standards/_filesystem.py` (modify), `src/project_standards/specs/cli.py` (modify), `src/project_standards/agent_handoff/cli.py` (modify), `src/project_standards/control_plane/executor.py` (modify), `tests/control_plane/test_command_resolution.py` (modify)
- **preconditions:** T4 is done; the four authoritative construction sites and their divergent shapes are recorded in the T14.1 evidence log; the full battery is green at the current baseline.
- **interface/data:** add a public `provider_dispatch_input` function whose published address is the dedicated `control_plane/provider_inputs.py` module — the sole control-plane home authorized to dispatch on package identity, per the owner decision of 2026-07-30 honoring the shared-module boundary contract (`test_shared_command_boundary_contains_no_package_dispatch`; the three shared modules stay generic). Payload-declared input shapes are the recorded post-hold retirement path for this registry. The function maps (selected package resolution, operation, provider identity, consumer root) to exactly the typed input the owning authoritative site builds today, performing its own file selection — the seam covers both halves: selection (which files a provider family reads) and construction (the typed input built from them). The pure selection functions currently above the tier boundary (`validate_frontmatter.collect_paths`, the project-spec path selection in `specs/cli.py`) relocate unchanged into the tier-neutral `_filesystem.py` so the seam can call them without circular imports; relocation is mechanical, with the original modules re-exporting or repointing. The four per-family input shapes are genuinely four and stay byte-identical — the `documents` array (five fields) for frontmatter providers, the three-field `documents` array for project-spec, the path-keyed snapshots plus `managed_*` facts (with `precondition_digest`) for agent-handoff, and the plan-bound verification snapshot (with `referenced_inputs`) for executor-run verify providers; no unified shape may be introduced. Move the four private constructions behind the seam and repoint their callers; the exact signature may adapt to what the call sites need, recorded as an interpretive freeze; the equivalence oracle must not import the moved implementation to generate its own expectations; no CLI flag, output, or exit-code changes; no MCP-module changes in this task; no provider, payload, or schema byte changes.
- **stop/backtrack:** if any call site's construction depends on CLI-parse-time state that cannot pass through a public signature, stop and record the coupling for orchestrator arbitration; do not change any provider, payload, or schema byte, and do not alter what any CLI command prints or returns.
- **acceptance:** the public seam returns each packaged provider's authoritative typed input, equal to the prior in-site construction, for every applicable provider on the full fixture and this repository (TC-T15-001); all four repointed callers keep byte-identical behavior under the existing battery (TC-T15-002).
- **sub-tasks:**
  - **T15.1 RED** — add the seam equivalence contract test across every applicable packaged provider on the full fixture and this repository; expected failure: the public seam does not exist.
  - **T15.2 Verify RED** — failures come only from the missing seam, never from fixtures, collection, or the existing constructions.
  - **T15.3 GREEN** — add the seam, move the four constructions behind it, repoint the callers; change nothing else.
  - **T15.4 Verify GREEN** — rerun the four repointed-caller suites and the ordinary battery; tallies must match the pre-change baseline exactly; statics clean.
  - **T15.5 REFACTOR** — none expected; record `none` when unused.
  - **T15.6 Verify Task** — run `uv run pytest tests/control_plane/test_command_resolution.py tests/control_plane/test_executor.py tests/control_plane/test_providers.py tests/test_adopt_manifest.py tests/test_validate_frontmatter.py`, the agent-handoff and spec CLI suites, `uv run ruff check` and `uv run ruff format --check` on the changed paths, and `uv run basedpyright`; commit with IDs.

### Phase P3: Protocol and Resources

#### T5: Add stdio adapter and capability boundary

- **goal:** Launch a protocol-clean local server whose advertised capabilities exactly match registered features. · **phase:** P3 · **depends_on:** [T2, T3, T4] · **requirements:** [FR-018, FR-024, FR-025, NFR-003, NFR-004, NFR-006, NFR-008, NFR-013, IR-001, IR-006, IR-007, IR-008, DR-007] · **priority:** must
- **files:** `src/project_standards/mcp_server/__init__.py` (create), `src/project_standards/mcp_server/entrypoint.py` (create), `src/project_standards/mcp_server/transport.py` (create), `src/project_standards/mcp_server/repo_access.py` (create), `src/project_standards/mcp_server/models.py` (create), `src/project_standards/cli.py` (modify), `tests/mcp_server/test_transport.py` (create), `tests/mcp_server/test_repo_access.py` (create), `tests/mcp_server/contract/test_import_boundary.py` (create)
- **preconditions:** T2-T4 are done; the exact SDK/revision/CLI/root/capability contracts in ADRs 0025-0026 are accepted; the selected SDK imports under all repository Python targets.
- **interface/data:** `entrypoint.py` constructs `McpServiceFacade.from_installed`, which completes the eager full-installed-distribution integrity check before stdio starts, applies only launch configuration frozen by T1, and calls `run_stdio`. `transport.py` is the only module that imports SDK server/protocol types. `repo_access.py` implements `resolve_effective_root`. At this task boundary, register no standard resources, prompts, or business tools; advertise only capabilities actually required by the selected SDK for an empty registry. Map every startup/root error to `ServiceError`/protocol error without stdout logging.
- **stop/backtrack:** if the SDK cannot run stdio without stdout contamination, cannot advertise an empty/truthful registry, or leaks protocol types into `mcp_services`, stop and return to T1. Do not add HTTP, a second launcher, or an SDK workaround in the service layer.
- **acceptance:** stdio discovery works with stderr-only logs (TC-T5-001, TC-T5-006); capabilities equal registered operations and omit writes/remote/list-change features not implemented (TC-T5-002); service modules import without the MCP SDK (TC-T5-003); `listChanged` is true only with an implemented and tested notification path (TC-T5-004); the CLI launches the server, and client roots may constrain eligibility but never replace or widen the explicit effective root (TC-T5-005, TC-T5-007).
- **sub-tasks:**
  - **T5.1 RED** — add subprocess protocol, stdout, capability, command, root-narrowing, and import-boundary tests.
  - **T5.2 Verify RED** — confirm failure is the absent command/adapter, not invalid protocol fixtures.
  - **T5.3 GREEN** — add one SDK transport adapter, explicit root-narrowing boundary, and `project-standards mcp`; register no resources/prompts/tools yet beyond truthful discovery.
  - **T5.4 Verify GREEN** — targeted transport and CLI regressions.
  - **T5.5 REFACTOR** — isolate revision-specific mapping in the adapter.
  - **T5.6 Verify Task** — run `uv run pytest tests/mcp_server/test_transport.py tests/mcp_server/test_repo_access.py tests/mcp_server/contract/test_import_boundary.py tests/control_plane/test_cli.py`, `uv run ruff check src/project_standards/mcp_server src/project_standards/cli.py tests/mcp_server`, `uv run ruff format --check src/project_standards/mcp_server src/project_standards/cli.py tests/mcp_server`, and `uv run basedpyright`; commit with IDs.

#### T6: Expose exact resources

- **goal:** Register generation-qualified catalog and exact version/resource templates backed only by T2. · **phase:** P3 · **depends_on:** [T5] · **requirements:** [FR-001, FR-002, FR-003, FR-004, FR-006, FR-021, FR-027, NFR-001, NFR-002, NFR-005, NFR-007, IR-002, DR-002] · **priority:** must
- **files:** `src/project_standards/mcp_server/resources.py` (create), `src/project_standards/mcp_server/transport.py` (modify), `src/project_standards/mcp_server/models.py` (modify), `src/project_standards/mcp_server/entrypoint.py` (modify), `tests/mcp_server/test_resources.py` (create)
- **preconditions:** T5 is done and protocol discovery is clean; T2 service tests are green; ADR 0026 contains the exact URI grammar/canonicalization rules for the selected revision.
- **interface/data:** register exactly `standards://catalog/{catalog_major}`, `standards://{standard_id}/{version}`, and `standards://{standard_id}/{version}/resources/{resource_id}` through selected-SDK templates/handlers. The catalog resource is compact metadata; the package resource is one exact `StandardDescriptor`; the payload resource returns `ResourceContent` bytes and declared media type only after T2 rechecks the selected declaration, contained path, and current byte digest. URI parsing must reject omitted generation/version, mutable aliases, percent-encoding/canonicalization mismatches, traversal, and undeclared IDs before service lookup. “Lazy” here means payload bytes enter MCP/model context only on a selected read; it never defers the eager full-distribution startup integrity check.
- **stop/backtrack:** any invalid family or payload at construction is a server-start failure, never a partial resource list. If the selected SDK cannot express the frozen URI templates without changing their identity, return to T1/ADR 0026 rather than add alternate URIs or per-package handlers.
- **acceptance:** list/read returns compact exact metadata and correct media bytes (TC-T6-001); fixture package/version expands resources without changing tool names (TC-T6-002); unknown/traversal/digest-invalid and partially invalid distributions fail closed (TC-T6-003); URI grammar and every resource-descriptor field match the locked exact-version contract (TC-T6-004, TC-T6-005).
- **sub-tasks:**
  - **T6.1 RED** — add protocol resource list/read/template, expansion, invalid-resource, and full-startup-failure tests.
  - **T6.2 Verify RED** — confirm service tests are green and protocol mapping is the only absence.
  - **T6.3 GREEN** — map T2 results into selected-SDK resource types.
  - **T6.4 Verify GREEN** — targeted resource plus transport tests.
  - **T6.5 REFACTOR** — keep URI parsing/canonicalization in one adapter helper.
  - **T6.6 Verify Task** — run `uv run pytest tests/mcp_server/test_resources.py tests/mcp_server/test_transport.py tests/mcp_services/test_catalog.py tests/mcp_services/test_resources.py`, `uv run ruff check src/project_standards/mcp_server tests/mcp_server`, `uv run ruff format --check src/project_standards/mcp_server tests/mcp_server`, and `uv run basedpyright`; commit with IDs.

#### T7: Add declared prompts and shared read fallback

- **goal:** Expose only declared prompt-role resources and provide the mandatory `standard_read` fallback whenever the frozen client-matrix condition holds. · **phase:** P3 · **depends_on:** [T6] · **requirements:** [FR-005, FR-008] · **priority:** must
- **files:** `src/project_standards/mcp_server/prompts.py` (create), `src/project_standards/mcp_server/tools.py` (create), `src/project_standards/mcp_server/transport.py` (modify), `src/project_standards/mcp_server/models.py` (modify), `tests/mcp_server/test_prompts.py` (create), `tests/mcp_server/test_standard_read.py` (create), `tests/mcp_server/test_resources.py` (modify)
- **preconditions:** T6 is done; T1 matrix explicitly states whether each primary client exposes prompts/resources to the model and whether `standard_read` is required; ADR 0026 enumerates any resource roles eligible to become prompts.
- **interface/data:** if the installed distribution has no T1-approved prompt-role declaration, expose no prompts and advertise that truthfully—never reinterpret `agent-summary`, templates, or prose as prompts. If prompts are approved, derive names/content only from exact declared resources. Evaluate the T1 matrix mechanically: if any supported primary client cannot give the model direct resource access, register `standard_read`; when that condition is true, registration is mandatory and the implementer has no discretion to omit it. Its input is one canonical resource URI and its output is the same descriptor/bytes mapping as T6, with no path argument. If every supported primary client provides direct model resource access, omit the tool and preserve the matrix evidence for that exact decision.
- **stop/backtrack:** if the client matrix is ambiguous or SDK/client behavior differs from T1 evidence, stop and refresh T1 rather than guessing. Do not create prompt text in server code or a second resource-reading implementation.
- **acceptance:** declared prompts list/get or the server truthfully advertises none (TC-T7-001); `standard_read` delegates to T2, rejects arbitrary paths, and is registered whenever at least one supported primary client lacks direct model resource access (TC-T7-002); a matrix fixture in which both clients provide direct access proves omission in only that case.
- **sub-tasks:**
  - **T7.1 RED** — add declared/absent prompt and shared-resource-tool parity tests.
  - **T7.2 Verify RED** — confirm exact resource reads are green and only prompt/fallback mapping is absent.
  - **T7.3 GREEN** — add declaration-derived prompts and the approved fallback without duplicate resource logic.
  - **T7.4 Verify GREEN** — targeted plus resource/metadata snapshots.
  - **T7.5 REFACTOR** — share one resource-to-protocol mapper.
  - **T7.6 Verify Task** — run `uv run pytest tests/mcp_server/test_prompts.py tests/mcp_server/test_standard_read.py tests/mcp_server/test_resources.py tests/mcp_server/test_transport.py`, `uv run ruff check src/project_standards/mcp_server tests/mcp_server`, `uv run ruff format --check src/project_standards/mcp_server tests/mcp_server`, and `uv run basedpyright`; commit with IDs.

### Phase P4: Generic Consumer Tools

#### T8: Add catalog and repository inspection tools

- **goal:** Register compact `standards_list` and `repo_inspect` tools over T2/T3. · **phase:** P4 · **depends_on:** [T5, T6, T7] · **requirements:** [FR-007, FR-009, FR-021, FR-022, FR-023, FR-024, NFR-012, IR-003, DR-005, DR-006] · **priority:** must
- **files:** `src/project_standards/mcp_server/tools.py` (modify), `src/project_standards/mcp_server/transport.py` (modify), `src/project_standards/mcp_server/resources.py` (modify), `src/project_standards/mcp_server/models.py` (modify), `tests/mcp_server/test_discovery_tools.py` (create), `tests/mcp_server/test_resources.py` (modify), `tests/mcp_server/test_standard_read.py` (modify), `tests/mcp_services/test_consumer.py` (modify)
- **preconditions:** T2/T3 service contracts, T5 transport, and T7's completed `tools.py` registry/fallback decision are green; T1 has frozen the exact tool names/metadata limits and selected-SDK structured-output shape.
- **interface/data:** `standards_list` takes no package-specific argument and returns the same `CatalogDescriptor` facts/URIs as the catalog resource. `repo_inspect` requires explicit `repo_root` and returns `RepoInspectionSnapshot`. Both schemas are typed, descriptions state authority and read-only effect, default text is bounded, relationships retain companion/extends/conflicts semantics, and neither tool reads resources or repository file contents itself.
- **stop/backtrack:** if a tool needs package-specific branching or a second DTO to satisfy the SDK, stop and fix the shared adapter mapping or revisit the frozen boundary. Do not add `standards_resolve`, recommendations, or per-standard tool names under this task.
- **acceptance:** structured catalog output equals the resource facts (TC-T8-001); repo inspection handles missing/partial/current state with explicit containment (TC-T8-002); metadata snapshot is compact and declares read-only effect (TC-T8-003); tools stay typed/generic and relationships preserve exact V2 declarations (TC-T8-004, TC-T8-005).
- **sub-tasks:**
  - **T8.1 RED** — add tool schema/result parity, root, relationship, and metadata snapshot tests.
  - **T8.2 Verify RED** — confirm T2/T3 services are green and registration/mapping alone is absent.
  - **T8.3 GREEN** — register two tools over service DTOs.
  - **T8.4 Verify GREEN** — targeted plus transport/resource tests.
  - **T8.5 REFACTOR** — centralize structured error mapping only.
  - **T8.6 Verify Task** — run `uv run pytest tests/mcp_server/test_discovery_tools.py tests/mcp_server/test_transport.py tests/mcp_server/test_resources.py tests/mcp_services/test_catalog.py tests/mcp_services/test_consumer.py`, `uv run ruff check src/project_standards/mcp_server tests/mcp_server`, `uv run ruff format --check src/project_standards/mcp_server tests/mcp_server`, and `uv run basedpyright`; commit with IDs.

#### T9: Add reconciliation and provider tools

- **goal:** Register non-mutating reconciliation, validation, drift, and approved helper tools with no alternate schemas or write path. · **phase:** P4 · **depends_on:** [T3, T4, T5, T7] · **requirements:** [FR-011, FR-012, FR-013, FR-014, FR-017, FR-018, FR-019, FR-022, FR-023, FR-024, FR-028, NFR-012, IR-003, IR-009, DR-004, DR-008] · **priority:** must
- **files:** `src/project_standards/mcp_server/tools.py` (modify), `src/project_standards/mcp_server/models.py` (modify), `src/project_standards/mcp_server/transport.py` (modify), `tests/mcp_server/test_consumer_tools.py` (create), `tests/mcp_server/security/test_no_writes.py` (create), `tests/mcp_server/security/__init__.py` (create; empty package marker required by the `tests.*` import convention — recorded T9.1 deviation), `tests/mcp_server/test_discovery_tools.py` (modify)
- **preconditions:** T3/T4 services, T5 transport, and T7's completed `tools.py` registry/fallback decision are green; T1 has either enumerated one generic helper tool and its non-mutating operations or explicitly omitted it.
- **interface/data:** always register `reconcile_preview(repo_root)`, `validate_repo(repo_root)`, and `drift_check(repo_root)`. Preview returns `McpServiceFacade.reconcile`; validation and drift map `McpServiceFacade.validate_repo` and `McpServiceFacade.drift_check` without performing provider selection or drift interpretation in `mcp_server`. Register a generic helper only if ADR 0025 names it and its exact schema. Every handler calls `McpServiceFacade`; `mcp_server` must not import `apply_reconciliation`, `apply_authoring_plan`, mutation schemas, provider entrypoints, or provider declarations directly.
- **stop/backtrack:** if authoritative service output cannot map losslessly to the frozen structured schema, or an operation reaches a mutating effect/write/syscall fixture, stop and return to T3/T4. Never sanitize away an unsafe action and return success, invoke CLI text, or add an apply callable.
- **acceptance:** protocol results preserve service/control-plane schemas and fingerprints (TC-T9-001, TC-T9-004); provider allowlist/roots/content exclusions hold through MCP (TC-T9-002); registry and subprocess fixtures prove zero writes/apply calls (TC-T9-003); every new tool has compact, reviewed, read-only metadata and bounded default text (TC-T9-005).
- **sub-tasks:**
  - **T9.1 RED** — add exact result parity, error, root, mutation-rejection, filesystem no-change, and tool-metadata-bound tests.
  - **T9.2 Verify RED** — confirm T3/T4 services are green and only tool registration/mapping is absent.
  - **T9.3 GREEN** — register the minimum approved tools; no executor/apply callable.
  - **T9.4 Verify GREEN** — targeted plus current planner/provider regressions.
  - **T9.5 REFACTOR** — deduplicate tool mapping without combining distinct domain services.
  - **T9.6 Verify Task** — run `uv run pytest tests/mcp_server/test_consumer_tools.py tests/mcp_server/security/test_no_writes.py tests/mcp_server/test_discovery_tools.py tests/mcp_services/test_consumer.py tests/mcp_services/test_providers.py tests/control_plane/test_planner.py tests/control_plane/test_providers.py`, `uv run ruff check src/project_standards/mcp_server tests/mcp_server`, `uv run ruff format --check src/project_standards/mcp_server tests/mcp_server`, and `uv run basedpyright`; commit with IDs.

### Phase P5: Hardening, Clients, and Handoff

#### T10: Prove protocol, safety, determinism, and CI

- **goal:** Close cross-cutting protocol and repository acceptance with stable fixtures and the existing CI gate. · **phase:** P5 · **depends_on:** [T6, T7, T8, T9] · **requirements:** [FR-010, FR-018, FR-025, FR-029, NFR-001, NFR-003, NFR-004, NFR-005, NFR-006, NFR-008, NFR-009, NFR-011, NFR-012, NFR-013, IR-008, DR-003, DR-007, DR-009] · **priority:** must
- **files:** `src/project_standards/mcp_server/transport.py` (modify — the single authorized T10.3 product change mapping unexpected handler exceptions to structured `-32603` `internal-error` refusals in both eras), `tests/mcp_server/contract/test_protocol_conformance.py` (create), `tests/mcp_server/contract/test_determinism.py` (create), `tests/mcp_server/contract/test_no_recommendations.py` (create), `tests/mcp_server/contract/test_import_boundary.py` (modify), `tests/mcp_server/integration/__init__.py` (create; empty package marker for the planned directory, required by the `tests.*` import convention), `tests/mcp_server/integration/test_server.py` (create), `tests/mcp_server/integration/test_registry_invariants.py` (create), `.github/workflows/check.yml` (modify only if current discovery does not already run these tests; unmodified at T10 — discovery already reaches these paths)
- **preconditions:** T6-T9 are done; every task-specific suite is green; T1 protocol/client evidence still matches the locked SDK and installed clients.
- **interface/data:** protocol fixtures cover initialize/discovery, resource template/list/read, prompt list/get when present, tool list/call, structured errors, and shutdown for the selected revision. At least one provider fixture writes to Python and file-descriptor stdout/stderr so the transcript proves worker output cannot contaminate protocol stdout. Golden tests compare stable fields verbatim, permute semantically unordered inputs to prove declared ordering, require root-relative paths, and reject timestamps/durations or hidden normalization. Registry invariants prove fixture package growth changes data/resources only, no recommendation surface exists, and no remote/write capability is reachable.
- **stop/backtrack:** a cross-cutting failure returns to the earliest owning task; T10 may fix only adapter mapping, test harness, or necessary existing-workflow discovery. Do not add features, weaken goldens, blanket-normalize new fields, or create a second CI workflow. If official conformance behavior has changed, return to T1.
- **acceptance:** full stdio transcript/capability/error schemas conform (TC-T10-001); golden normalization rejects every unlisted variance (TC-T10-002, TC-T10-004); CI runs MCP suites and proves no remote/write surface (TC-T10-003); the registry and service boundary expose no recommendation/confidence logic while no typed recommendation service exists (TC-T10-005); the complete import graph remains one-way and SDK-isolated (TC-T10-006); tool metadata/default text remains within T1-frozen bounds (TC-T10-007).
- **sub-tasks:**
  - **T10.1 RED** — add conformance transcript, deterministic-golden, tool-growth, no-remote/no-write, no-recommendation, complete import-graph, metadata-bound, and CI-presence tests.
  - **T10.2 Verify RED** — confirm failures identify uncovered cross-cutting contracts.
  - **T10.3 GREEN** — correct only adapter/test/CI integration defects; no new feature.
  - **T10.4 Verify GREEN** — all MCP service/server suites and nearest CLI/control-plane regressions.
  - **T10.5 REFACTOR** — remove only proven test/adapter duplication.
  - **T10.6 Verify Task** — run `uv run pytest tests/mcp_services tests/mcp_server tests/control_plane/test_cli.py tests/control_plane/test_planner.py tests/control_plane/test_providers.py tests/package_contract/test_repository.py`, `uv run ruff check src/project_standards/mcp_services src/project_standards/mcp_server tests/mcp_services tests/mcp_server`, `uv run ruff format --check src/project_standards/mcp_services src/project_standards/mcp_server tests/mcp_services tests/mcp_server`, `uv run basedpyright`, and the four package-contract commands in §13; commit with IDs.

#### T11: Prove installed-wheel clients and document use

- **goal:** Demonstrate the same candidate wheel in Codex and Claude Code and write accurate setup/reference/troubleshooting docs. · **phase:** P5 · **depends_on:** [T10] · **requirements:** [FR-016, FR-020, FR-030, NFR-009, NFR-010, NFR-011] · **priority:** must
- **files:** `README.md` (modify), `docs/mcp-server.md` (create), `CHANGELOG.md` (modify under `Unreleased` only), `docs/research/2026-07-28-project-standards-mcp-protocol-sdk-client-matrix.md` (modify), `docs/specs/2026-07-07-project-standards-mcp-server-implementation-spec.md` (modify), `docs/specs/README.md` (modify), `tests/mcp_server/e2e/test_installed_wheel.py` (create), `tests/mcp_server/e2e/__init__.py` (create; empty package marker required by the `tests.*` import convention — recorded T11 deviation F-N), `tests/mcp_server/test_standard_read.py` (modify — equivalence-suite accommodation), `tests/mcp_server/test_transport.py` (modify — equivalence-suite accommodation), candidate wheel/runtime (temporary)
- **preconditions:** T10 is done; source tests are green; current Codex and Claude versions match or intentionally supersede the versions recorded in T1; client smoke work has isolated temporary configuration and an owner-approved repo fixture.
- **interface/data:** the installed-wheel test constructs the facade/server from extracted package bytes and compares the complete stable catalog/resource/tool schemas with source-fixture results. The temporary candidate is identified by its SHA-256 and the final T12 commit because release-version finalization is not authorized; do not publish or install it as a replacement for a released artifact carrying the same base version. `docs/mcp-server.md` must carry repository-compliant frontmatter and contain prerequisites, install/version check, exact stdio configuration for each client, capability matrix, URI/tool schemas, explicit-root/read-only/security rules, equivalent CLI/CI commands, troubleshooting, and uninstall/disable steps. `CHANGELOG.md` records the additive feature under `Unreleased` without creating a versioned release section. Client evidence records wheel digest, version, invocation, observed capabilities, roots, prompts/resources/tools, fallback use, stdout/stderr result, and fixture identity; T12 adds the final commit. Record the owner's real-consumer dogfood decision against `SPEC-MS01 OQ-005`, update that question's status, append exactly one next sequential `SPEC-MS01` revision row summarizing the T11 decision, and update `last_reviewed` plus `docs/specs/README.md`.
- **stop/backtrack:** if source and wheel facts differ, stop and fix packaging/projection in the earliest owning task, discard the old temporary artifact/runtime, and restart T11.0 before documentation. If a primary client cannot satisfy the frozen v1 contract or the owner has not recorded the `SPEC-MS01 OQ-005` decision, return to T1 or stop for owner direction as applicable; do not make an unplanned packaging correction in T11, modify the user's persistent global client configuration, silently drop a primary client, add an unplanned compatibility tool, or self-authorize the real-consumer choice.
- **acceptance:** source and extracted-wheel outputs are equivalent (TC-T11-001); Codex and Claude smoke records cover tools/resources/prompts/roots/fallbacks (TC-T11-002); docs match exact invocation and equivalent CLI/CI commands (TC-T11-003); the recorded owner decision closes `SPEC-MS01 OQ-005`, and the owning spec revision/status/index match that evidence.
- **sub-tasks:**
  - **T11.0 CHARACTERIZE** — record the source launcher, protocol behavior, current Codex/Claude feature behavior, and current package version before changing documentation. Any wheel built for characterization is disposable and must not be reused after working-tree changes.
  - **T11.1 RED** — add installed/source equivalence and documented-command contract tests. Expected failure: the installed-wheel, client-evidence, or documentation contract is absent or incomplete; if it is already green, record that characterization and do not manufacture a failure.
  - **T11.2 Verify RED** — confirm any failure is the missing installed artifact/client/doc contract, not an incorrectly extracted wheel, stale client installation, or unrelated global configuration.
  - **T11.3 GREEN** — after any parity defect has been corrected in its owning task, add exact setup, capability matrix, tool/resource reference, read-only/root notes, equivalent CLI/CI commands, and troubleshooting; add the feature to `CHANGELOG.md` under `Unreleased` only; and record the owner-approved `SPEC-MS01 OQ-005` decision with one owning-spec revision/index update.
  - **T11.4 Verify GREEN** — after all production and documentation edits are complete, run `MCP_WHEEL_OUT="$(mktemp -d)"`, `MCP_WHEEL_RUNTIME="$(mktemp -d)"`, `uv build --wheel --out-dir "$MCP_WHEEL_OUT"`, `sha256sum "$MCP_WHEEL_OUT"/project_standards-*.whl`, `python -m zipfile -e "$MCP_WHEEL_OUT"/project_standards-*.whl "$MCP_WHEEL_RUNTIME"`, and `export PYTHONPATH="$MCP_WHEEL_RUNTIME${PYTHONPATH:+:$PYTHONPATH}"`; record that digest, then run installed-wheel equivalence, bounded client smokes, Project Standards validation, Prettier, markdownlint, and documented command checks against only those candidate bytes.
  - **T11.5 REFACTOR** — remove duplicated client/reference prose and derive repeated tool/resource facts from the frozen registration/schema evidence where practical.
  - **T11.6 Verify Task** — against the same `$MCP_WHEEL_RUNTIME`, run `sha256sum "$MCP_WHEEL_OUT"/project_standards-*.whl`, `uv run pytest tests/mcp_server/e2e/test_installed_wheel.py tests/mcp_services tests/mcp_server`, every exact client probe recorded by T1, `uv run project-standards validate`, `uv run project-standards spec validate docs/specs/2026-07-07-project-standards-mcp-server-implementation-spec.md`, `uv run project-standards spec lint --strict docs/specs/2026-07-07-project-standards-mcp-server-implementation-spec.md`, `npx prettier --check README.md docs/mcp-server.md CHANGELOG.md docs/research/2026-07-28-project-standards-mcp-protocol-sdk-client-matrix.md docs/specs/2026-07-07-project-standards-mcp-server-implementation-spec.md docs/specs/README.md`, `npx markdownlint-cli2 --no-globs :README.md :docs/mcp-server.md :CHANGELOG.md :docs/research/2026-07-28-project-standards-mcp-protocol-sdk-client-matrix.md :docs/specs/2026-07-07-project-standards-mcp-server-implementation-spec.md :docs/specs/README.md`, `uv run ruff check src/project_standards/mcp_services src/project_standards/mcp_server tests/mcp_services tests/mcp_server`, `uv run ruff format --check src/project_standards/mcp_services src/project_standards/mcp_server tests/mcp_services tests/mcp_server`, and `uv run basedpyright`; verify the digest still matches T11.4, `SPEC-MS01 OQ-005` plus its revision/index are current, and no versioned changelog section/version bump was created, then commit with IDs.

#### T12: Run final gate and prepare handoff

- **goal:** Produce a verified local MCP implementation candidate and release-readiness evidence, without release finalization or publication, with complete traceability and handoff. · **phase:** P5 · **depends_on:** [T11] · **requirements:** [FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-009, FR-010, FR-011, FR-012, FR-013, FR-014, FR-015, FR-016, FR-017, FR-018, FR-019, FR-020, FR-021, FR-022, FR-023, FR-024, FR-025, FR-026, FR-027, FR-028, FR-029, FR-030, NFR-001, NFR-002, NFR-003, NFR-004, NFR-005, NFR-006, NFR-007, NFR-008, NFR-009, NFR-010, NFR-011, NFR-012, NFR-013, IR-001, IR-002, IR-003, IR-004, IR-005, IR-006, IR-007, IR-008, IR-009, DR-001, DR-002, DR-003, DR-004, DR-005, DR-006, DR-007, DR-008, DR-009] · **priority:** must
- **files:** `docs/STATUS.md` (modify), `docs/handoff/state.md` (modify), `docs/handoff/specs-plans.md` (modify), `docs/handoff/sessions/{YYYY-MM}.md` (modify), `docs/plans/2026-07-24-project-standards-mcp-server-plan.md` (close-out only), `.project-pipeline/2026-07-24-project-standards-mcp-server/` (close-out only)
- **preconditions:** T1-T11 are done; no checklist task is blocked; all deviations/open questions have an approved disposition; T11 candidate digest/evidence is complete; the current branch/worktree and its approved integration target are known before closeout. T12 builds one fresh final candidate after pending closeout documentation edits and uses only that artifact for §13.
- **interface/data:** the trace audit maps every Source Requirements row to a task, test ID, checklist evidence line, and final result. Status/handoff must say “implementation verified; release unprepared and unpublished,” record commit plus wheel digest, and distinguish that state from a separately authorized prepared/unpublished release and a published release. The plan Close-out harvest records deviations/decisions/risks/deferred work; routine progress remains only in the soon-to-be-removed checklist state.
- **stop/backtrack:** on any §13 failure, missing evidence, unresolved blocker, or review finding, stop closeout, keep the plan active/checklists intact, and route work to the owning task or append a discovered task with the next ID followed by `plan.py sync`. Never mark complete because the candidate is merely built; never tag, push a release, publish, or delete evidence before the final commit.
- **acceptance:** every source requirement/test maps to green evidence (TC-T12-001); full repository/package/security/docs gates pass (TC-T12-002); status says implementation verified with release unprepared/unpublished and records no implementation outside scope, version bump, tag, or publication.
- **sub-tasks:**
  - **T12.0 CHARACTERIZE** — reconcile spec traceability, checklist evidence, deviations, risks, and open questions; stop and route any missing implementation evidence back to its owning task before editing closeout state.
  - **T12.6 Verify Task** — update status/handoff and harvest pending closeout notes, then run every command in §13 with the same extracted candidate wheel first on `PYTHONPATH`; complete final code review and resolve only in-scope blockers. If and only if the gate is green, set the plan/checklist complete, rerun `uv run scripts/plan.py validate docs/plans/2026-07-24-project-standards-mcp-server-plan.md`, commit the verified candidate, and merge into the approved repository branch if an isolated worktree was used. From that branch run `MCP_TARGET_BRANCH="$(git branch --show-current)"`, `test -n "$MCP_TARGET_BRANCH"`, `git push origin "HEAD:$MCP_TARGET_BRANCH"`, `test "$(git rev-parse HEAD)" = "$(git rev-parse "origin/$MCP_TARGET_BRANCH")"`, and `test -z "$(git status --short)"`. Remove generated checklist state and any task worktree only after those checks. Do not tag, publish, or release without separate authorization.

## 9. Cross-Cutting Requirements

| Concern | Applies? | How verified | Owning task |
| --- | --- | --- | --- |
| Error handling | yes | Structured protocol/service failure tests. | T5, T10 |
| Logging / observability | yes | Stdio transcript proves stdout clean and stderr bounded. | T5, T10 |
| Security | yes | Digest/path/root/content/no-write tests and dependency audit. | T2-T5, T9-T10 |
| Performance | yes | Bounded scan/cache tests and a deliberately slow provider timeout fixture. | T2, T4, T6 |
| Compatibility | yes | Source/wheel parity and Codex/Claude matrix. | T10-T11 |
| Documentation | yes | Configured Markdown gates and command verification. | T11-T12 |

## 10. Integration and Migration

### 10.1 Integration Sequence

1. Freeze the stable dependency and service boundary.
2. Prove SDK-independent package/consumer/provider services.
3. Add one stdio adapter, then resources/prompts and generic tools.
4. Harden protocol/security/CI, then test the same candidate wheel in both clients.
5. Prepare release evidence and stop before publication.

### 10.2 Data or State Migration

- **Required:** no · **Rollback supported:** yes, by reverting package changes · **Idempotent:** read-only operations only.
- The server owns no durable state. Consumer `.standards/` files are read but never changed.

### 10.3 Compatibility Plan

CLI, CI, and package/control-plane APIs remain primary and unchanged. MCP is an optional adapter. Resource/prompt client gaps are handled by the shared read tool, not a second content service. Production uses installed exact versions; source mode is explicit and must be equivalent.

## 11. Risks and Decisions

| ID | Risk | Likelihood | Impact | Mitigation | Owning task |
| --- | --- | --- | --- | --- | --- |
| R-001 | Final protocol/SDK pair is not stable-compatible. | med | high | Stop at T1; owner decides deferral or documented alternative. | T1 |
| R-002 | MCP layer duplicates domain semantics. | med | high | Import/boundary tests and service-first task order. | T2-T5 |
| R-003 | Client features differ from protocol support. | high | med | Freeze matrix and shared read fallback; verify both clients. | T1, T7, T11 |
| R-004 | Resource or repo access leaks unrelated bytes. | low | high | Exact declarations/digests, explicit roots, content-exclusion fixtures. | T2, T3, T9 |
| R-005 | Provider diagnostics break determinism. | med | med | DR-009 normalization and golden rejection of unlisted variance. | T4, T10 |
| R-006 | Read-only surface accidentally reaches executor/apply. | low | high | Effect allowlist, no-write registry/filesystem tests. | T4, T9, T10 |

| ID | Decision | Rationale | Affected task(s) |
| --- | --- | --- | --- |
| D-001 | Service facade precedes MCP registration. | Prevent SDK/domain coupling. | T2-T5 |
| D-002 | Installed exact payloads are production authority. | Preserve reproducibility and release authority. | T2, T6, T11 |
| D-003 | Reuse control-plane schemas and fingerprints. | Avoid a second consumer truth surface. | T3, T9 |
| D-004 | Explicit `repo_root` is always authoritative. | Client root support varies. | T3, T5, T8, T9 |
| D-005 | No writes or remote transport in v1. | Preserve bounded first release. | T1, T5, T9, T10 |

## 12. Open Questions

All nine questions are resolved (SPEC-RD01 at revision 1.6, SPEC-MS01 at revision 1.4; OQ-005 closed at T11 on 2026-07-30). The rows below preserve the original pre-resolution assumptions as authored; the resolutions live in the spec revision histories and the §14 close-out.

| ID | Question | Blocking? | Owner | Current assumption |
| --- | --- | --- | --- | --- |
| SPEC-RD01 OQ-001 | Which final MCP protocol revision and stable Python SDK release should implementation pin? | yes at T1 | Owner / implementer | Recheck after the final 2026-07-28 publication; no code before resolution. |
| SPEC-RD01 OQ-002 | What exact version-qualified resource URI grammar should be frozen? | yes at T1 | Implementer | Derive it from Catalog 5 standard ID, exact payload version, and declared resource ID; freeze canonicalization in ADR 0026. |
| SPEC-MS01 OQ-001 | Which final protocol/SDK pair is stable-compatible? | yes at T1 | Owner / implementer | Select after final 2026-07-28 publication; no code before resolution. |
| SPEC-MS01 OQ-002 | Should the entry point be `project-standards mcp` or a separate `project-standards-mcp`? | no, resolve at T1 | Owner | Prefer `project-standards mcp`; ADR 0026 records the final CLI-form decision. |
| SPEC-MS01 OQ-003 | Does either client require `standard_read`? | yes at T1/T7 | Implementer | Ship it if either supported primary client lacks direct model resource access. |
| SPEC-MS01 OQ-004 | How do selected-client roots constrain explicit tool roots? | yes at T1 | Implementer | Explicit `repo_root` remains mandatory; enabled client roots are additional narrowing boundaries only. |
| SPEC-MS01 OQ-005 | Which real consumer repo is appropriate for optional dogfood? | no; decide at T11 | Owner | Fixtures and this repo are mandatory; real-repo use needs separate approval. |
| SPEC-MS01 OQ-006 | What exact resources/prompts/roots semantics do current Codex and Claude Code builds expose after the final protocol/SDK selection? | yes at T1 | Implementer | Freeze both clients in the checked matrix and ADR behavior contract; explicit `repo_root` remains authoritative. |
| SPEC-MS01 OQ-007 | Should generic provider dispatch ship in v1? | no; disposition at T1 | Owner | Include only if its non-mutating allowlist reduces tool surface; specialized tools remain sufficient. |

## 13. Final Verification

- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run basedpyright`
- `MCP_WHEEL_OUT="$(mktemp -d)"`
- `MCP_WHEEL_RUNTIME="$(mktemp -d)"`
- `uv build --wheel --out-dir "$MCP_WHEEL_OUT"`
- `sha256sum "$MCP_WHEEL_OUT"/project_standards-*.whl`; record this as the final candidate digest.
- `python -m zipfile -e "$MCP_WHEEL_OUT"/project_standards-*.whl "$MCP_WHEEL_RUNTIME"`
- `export PYTHONPATH="$MCP_WHEEL_RUNTIME${PYTHONPATH:+:$PYTHONPATH}"`; reuse those extracted bytes for every remaining package/MCP/client check.
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
- `uv run scripts/plan.py validate docs/plans/2026-07-24-project-standards-mcp-server-plan.md`
- `uv run pytest tests/mcp_server/e2e/test_installed_wheel.py tests/mcp_server/integration/test_server.py tests/mcp_server/contract/test_protocol_conformance.py`
- Copy and execute every Codex and Claude Code smoke command verbatim from the frozen “Executable probes” table in `docs/research/2026-07-28-project-standards-mcp-protocol-sdk-client-matrix.md`; append the exact versions, commands, exit status, observed capabilities, fallback result, and stderr/stdout disposition to that matrix.
- `uv run project-standards agent-handoff validate --repo .`
- `uv run project-standards agent-handoff drift-check --repo .`
- `uv run project-standards agent-handoff size-report --repo .`
- `uv run project-standards agent-handoff shape-check --repo .`
- `git diff --check`
- Audit Appendix B against the final checklist logs: every source FR/NFR/IR/DR row must have green or explicit v1-omission evidence, and every `TC-*` ID must point to one passing target/evidence record.
- Inspect tool/resource/capability discovery and confirm no mutating, recommendation, or remote MCP surface exists. Any mismatch fails the gate and returns to the earliest owning task.
- Prepare candidate and handoff evidence with the state “implementation verified; release unprepared and unpublished”; record git commit and wheel digest, and do not bump/finalize a version, tag, publish, or release.

## 14. Close-out

- **Completed:** _pending_ · final commit _pending_
- **Deviations / decisions harvested from notes:** _pending close-out_
- **Risks closed / accepted:** _pending close-out_
- **Deferred work filed:** _pending close-out_

Teardown: harvest notes into this section and applicable ADR/handoff artifacts, set `status: complete`, commit the master plan with the candidate, merge/push the approved repository branch, prove local/remote parity, then remove `.project-pipeline/2026-07-24-project-standards-mcp-server/` and any task worktree.

## Appendices

### Appendix A. Interface or Schema Changes

#### A.1 Public Interfaces

| Interface | Current | Planned | Compatibility |
| --- | --- | --- | --- |
| `project-standards mcp` | absent | local stdio launcher | Additive; existing CLI unchanged. |
| MCP resources | absent | generation/exact-version URI templates | Additive MCP surface; required for enabled v1 server. |
| MCP tools | absent | small generic read-only set | Additive MCP surface; mandatory/conditional registrations follow §4 and never become per-package tools. |
| Python service facade | absent | SDK-independent typed internal-public boundary | Additive; existing APIs remain authoritative. |

#### A.2 Data Models

| Model | Field | Change | Validation | Migration |
| --- | --- | --- | --- | --- |
| Service DTOs | package/resource/repo/provider facts | add protocol-neutral projections | Pydantic/typed contract tests | none |
| MCP result models | structured content and errors | add adapter projections | SDK schema/protocol tests | none |
| Existing package/control-plane models | none | no semantic/schema change planned | existing package/control-plane gates | none |

### Appendix B. Test Matrix

| Test ID | Requirement | Task | Exact test target or evidence | Type |
| --- | --- | --- | --- | --- |
| TC-T1-001 | FR-029, NFR-011 | T1 | ADRs 0025-0026, the exact dependency/lock diff, and the official-source/license/conformance register in `docs/research/2026-07-28-project-standards-mcp-protocol-sdk-client-matrix.md` | external/contract |
| TC-T1-002 | FR-030 | T1 | The exact Codex and Claude Code executable probes and results in `docs/research/2026-07-28-project-standards-mcp-protocol-sdk-client-matrix.md` | external/contract |
| TC-T2-001 | FR-001, FR-002, FR-021 | T2 | `tests/mcp_services/test_catalog.py::test_catalog_generation_and_package_order_are_explicit` | contract |
| TC-T2-002 | FR-003, FR-006, FR-027 | T2 | `tests/mcp_services/test_resources.py::test_facade_rejects_any_invalid_installed_payload_at_construction` and `tests/mcp_services/test_resources.py::test_resource_read_rechecks_declaration_containment_and_digest` | security |
| TC-T2-003 | FR-015, FR-026, NFR-005, NFR-006, NFR-007, NFR-010, NFR-013, DR-009 | T2 | `tests/mcp_services/test_resources.py::test_source_and_installed_facades_are_equivalent_and_stably_ordered` and `tests/mcp_services/test_catalog.py::test_common_installed_reads_reuse_validated_catalog_without_repo_scan` | integration |
| TC-T2-004 | IR-004 | T2 | `tests/mcp_services/contract/test_facade.py::test_facade_exports_protocol_neutral_types_without_mcp_sdk` | contract |
| TC-T2-005 | DR-001 | T2 | `tests/mcp_services/test_catalog.py::test_descriptor_uses_v2_package_facts` | contract |
| TC-T2-006 | DR-006 | T2 | `tests/mcp_services/test_catalog.py::test_relationships_preserve_v2_declarations_and_empty_independence` | contract |
| TC-T2-007 | DR-002 | T2 | `tests/mcp_services/test_resources.py::test_resource_descriptor_preserves_declared_fields` | contract |
| TC-T3-001 | FR-009, FR-011, FR-015, FR-026, NFR-006, IR-004 | T3 | `tests/mcp_services/test_consumer.py::test_consumer_operations_reload_missing_partial_and_current_state` | integration |
| TC-T3-002 | FR-017, NFR-005, DR-004, DR-009 | T3 | `tests/mcp_services/test_consumer.py::test_preview_preserves_schema_fingerprint_preconditions_and_stable_order` | contract |
| TC-T3-003 | FR-024, FR-028, IR-007 | T3 | `tests/mcp_services/security/test_consumer_boundaries.py::test_repo_access_rejects_escape_and_excludes_unrelated_contents` | security |
| TC-T3-004 | IR-005 | T3 | `tests/mcp_services/security/test_consumer_boundaries.py::test_consumer_service_reads_only_authoritative_paths` | security |
| TC-T3-005 | DR-005 | T3 | `tests/mcp_services/test_consumer.py::test_snapshot_is_bounded_and_typed` | contract |
| TC-T4-001 | FR-012, FR-013, FR-026, NFR-005, NFR-006, IR-004, DR-009 | T4 | `tests/mcp_services/test_providers.py::test_validate_repo_selects_applicable_exact_providers`, `tests/mcp_services/test_providers.py::test_drift_check_preserves_reconciliation_and_typed_provider_results`, `tests/mcp_services/test_providers.py::test_validate_repo_reloads_the_current_resolution_between_calls`, and `tests/mcp_services/test_providers.py::test_typed_input_effective_config_and_root_are_forwarded` | contract |
| TC-T4-002 | FR-014, FR-015 | T4 | `tests/mcp_services/security/test_provider_effects.py::test_unknown_and_mutating_effects_fail_before_worker_start`, `tests/mcp_services/security/test_provider_effects.py::test_operation_allowlist_rejects_every_unapproved_operation`, `tests/mcp_services/security/test_provider_effects.py::test_supported_operations_never_change_the_consumer_filesystem`, `tests/mcp_services/security/test_provider_effects.py::test_composite_operations_never_change_the_consumer_filesystem`, `tests/mcp_services/security/test_provider_effects.py::test_provider_operations_reject_every_unsafe_root`, `tests/mcp_services/test_providers.py::test_typed_input_is_validated_recursively_before_any_worker`, and `tests/mcp_services/test_provider_worker.py::test_non_json_typed_input_is_refused_before_the_worker_starts` | security |
| TC-T4-003 | DR-008 | T4 | `tests/mcp_services/test_providers.py::test_provider_diagnostics_are_bounded_and_fingerprint_neutral`, and `tests/mcp_services/test_providers.py::test_oversized_structured_output_cannot_cross_ipc_unbounded` | unit |
| TC-T4-004 | DR-003 | T4 | `tests/mcp_services/test_providers.py::test_finding_model_requires_every_declared_field`, `tests/mcp_services/test_providers.py::test_absolute_provider_finding_paths_are_published_root_relative`, and `tests/mcp_services/test_providers.py::test_finding_paths_must_be_contained_in_the_consumer_root` | contract |
| TC-T4-005 | FR-012, FR-013 | T4 | `tests/mcp_services/test_providers.py::test_slow_provider_returns_bounded_diagnostic_and_worker_is_reaped`, `tests/mcp_services/test_providers.py::test_cancelled_invocation_terminates_and_releases_the_worker`, `tests/mcp_services/test_providers.py::test_termination_failures_never_claim_the_repository_is_unchanged`, `tests/mcp_services/test_providers.py::test_worker_group_termination_leaves_no_descendant`, `tests/mcp_services/test_providers.py::test_cooperative_shutdown_is_drained_instead_of_escalated`, `tests/mcp_services/test_providers.py::test_execution_bound_is_not_extended_after_the_streams_close`, and `tests/mcp_services/test_provider_worker.py::test_a_worker_that_never_reads_its_request_still_fails_within_the_bound` | integration |
| TC-T4-006 | IR-009 | T4 | `tests/mcp_services/test_providers.py::test_dispatch_is_exact_payload_qualified` | contract |
| TC-T4-007 | DR-008 | T4 | `tests/mcp_services/test_providers.py::test_provider_result_preserves_declared_fields`, `tests/mcp_services/test_providers.py::test_public_result_dtos_are_frozen_by_class_and_annotation`, `tests/mcp_services/test_providers.py::test_reports_are_typed_root_relative_and_free_of_timestamps`, and `tests/mcp_services/test_providers.py::test_provider_output_key_order_is_canonical_across_worker_processes` | contract |
| TC-T4-008 | FR-012, FR-013, FR-014, FR-015, NFR-006, DR-008 | T4 | `tests/mcp_services/test_provider_worker.py::test_worker_matches_direct_dispatch_and_isolates_output_without_writes`, `tests/mcp_services/test_provider_worker.py::test_worker_module_is_sdk_free_and_importable_by_name`, `tests/mcp_services/test_provider_worker.py::test_worker_releases_every_resource_on_all_four_completion_paths`, `tests/mcp_services/test_provider_worker.py::test_forged_ipc_frames_are_refused_by_the_parent`, and `tests/mcp_services/test_provider_worker.py::test_forged_error_frames_cannot_publish_attacker_selected_paths` | integration/security |
| TC-T5-001 | NFR-003, NFR-004 | T5 | `tests/mcp_server/test_transport.py::test_stdio_initialize_and_errors_keep_stdout_protocol_clean`, `tests/mcp_server/test_transport.py::test_every_sdk_advertised_revision_is_served_by_one_server`, `tests/mcp_server/test_transport.py::test_each_era_refuses_the_other_eras_opening_contract`, `tests/mcp_server/test_transport.py::test_transport_harness_speaks_the_protocol_against_a_bare_sdk_server`, and `tests/mcp_server/test_transport.py::test_sdk_register_still_contains_the_frozen_client_revision` | protocol |
| TC-T5-002 | FR-018, FR-025, NFR-008 | T5 | `tests/mcp_server/test_transport.py::test_capabilities_match_registry_and_omit_write_and_remote`, `tests/mcp_server/test_transport.py::test_no_remote_transport_entry_point_exists_in_the_adapter_or_cli`, `tests/mcp_server/test_transport.py::test_server_identity_and_instructions_are_static_truthful_and_era_stable`, `tests/mcp_server/test_transport.py::test_adapter_configuration_exposes_only_the_launch_time_boundary`, `tests/mcp_server/test_transport.py::test_transport_module_exposes_the_named_adapter_surface`, and `tests/mcp_server/test_transport.py::test_modern_list_result_contract_is_satisfiable_by_the_sdk` | contract |
| TC-T5-003 | NFR-006, NFR-013 | T5 | `tests/mcp_server/contract/test_import_boundary.py::test_service_package_imports_without_mcp_sdk`, `tests/mcp_server/contract/test_import_boundary.py::test_adapter_package_carries_the_planned_module_set`, `tests/mcp_server/contract/test_import_boundary.py::test_service_modules_never_import_the_sdk_or_the_adapter`, `tests/mcp_server/contract/test_import_boundary.py::test_only_the_transport_module_imports_the_sdk`, `tests/mcp_server/contract/test_import_boundary.py::test_protocol_modules_reach_repository_facts_only_through_the_services`, `tests/mcp_server/contract/test_import_boundary.py::test_no_service_signature_exposes_an_sdk_type`, and `tests/mcp_server/contract/test_import_boundary.py::test_service_annotations_actually_resolve` | contract |
| TC-T5-004 | IR-008, DR-007 | T5 | `tests/mcp_server/test_transport.py::test_list_changed_requires_notifications` | protocol |
| TC-T5-005 | IR-001 | T5 | `tests/mcp_server/test_transport.py::test_cli_launches_stdio_server`, `tests/mcp_server/test_transport.py::test_configured_root_boundary_option_reaches_adapter_configuration`, and `tests/mcp_server/test_transport.py::test_cli_rejects_an_invalid_configured_boundary_without_touching_stdout` | integration |
| TC-T5-006 | IR-006 | T5 | `tests/mcp_server/test_transport.py::test_logs_use_stderr_only`, `tests/mcp_server/test_transport.py::test_startup_integrity_failure_precedes_stdio_and_never_touches_stdout`, `tests/mcp_server/test_transport.py::test_server_writes_nothing_to_stdout_before_the_first_request`, and `tests/mcp_server/test_transport.py::test_malformed_launch_syntax_writes_no_stdout` | protocol |
| TC-T5-007 | FR-024, IR-007 | T5 | `tests/mcp_server/test_repo_access.py::test_client_roots_only_narrow_explicit_root`, `tests/mcp_server/test_repo_access.py::test_configured_boundary_narrows_exactly_like_client_roots`, `tests/mcp_server/test_repo_access.py::test_boundaries_never_replace_a_missing_repo_root`, `tests/mcp_server/test_repo_access.py::test_boundaries_never_widen_an_otherwise_rejected_root`, `tests/mcp_server/test_repo_access.py::test_resolve_effective_root_signature_is_the_frozen_boundary_shape`, `tests/mcp_server/test_repo_access.py::test_malformed_explicit_roots_are_refused_structurally`, `tests/mcp_server/test_repo_access.py::test_malformed_boundary_values_are_refused_structurally`, `tests/mcp_server/test_repo_access.py::test_nul_bearing_path_inputs_are_structured_refusals`, `tests/mcp_server/test_repo_access.py::test_repo_root_rejection_class_shares_one_stable_code`, `tests/mcp_server/test_repo_access.py::test_boundary_containment_rejections_are_independently_structured`, `tests/mcp_server/test_repo_access.py::test_safe_in_bound_symlinked_root_is_accepted_and_resolved`, `tests/mcp_server/test_repo_access.py::test_symlinked_root_that_escapes_the_boundary_is_refused`, `tests/mcp_server/test_repo_access.py::test_symlinked_client_boundary_cannot_escape_the_configured_boundary`, `tests/mcp_server/test_repo_access.py::test_nested_boundary_in_the_wrong_direction_is_refused`, `tests/mcp_server/test_repo_access.py::test_boundary_prefix_collisions_do_not_grant_containment`, `tests/mcp_server/test_repo_access.py::test_resolved_root_is_absolute_and_stable_across_working_directories`, `tests/mcp_server/test_repo_access.py::test_root_resolution_never_modifies_the_candidate_repository`, and `tests/mcp_server/test_repo_access.py::test_boundary_inputs_accept_the_declared_sequence_shape` | security |
| TC-T6-001 | FR-001, FR-002, FR-003, NFR-002 | T6 | `tests/mcp_server/test_resources.py::test_list_and_read_return_exact_metadata_and_bytes`, `tests/mcp_server/test_resources.py::test_binary_resource_reads_as_base64_with_its_declared_media_type`, `tests/mcp_server/test_resources.py::test_payload_bytes_enter_context_only_on_a_selected_read`, and `tests/mcp_server/test_resources.py::test_fixture_runtime_harness_serves_the_fixture_catalog` | protocol |
| TC-T6-002 | FR-004, FR-021, NFR-001, NFR-007 | T6 | `tests/mcp_server/test_resources.py::test_fixture_package_growth_changes_resources_not_tools`, `tests/mcp_server/test_resources.py::test_resource_templates_expose_the_two_parameterized_forms`, `tests/mcp_server/test_resources.py::test_declared_relationships_survive_the_protocol_projection`, and `tests/mcp_server/test_resources.py::test_metadata_requests_never_read_payload_bytes_through_the_facade` | integration |
| TC-T6-003 | FR-006, FR-027 | T6 | `tests/mcp_server/test_resources.py::test_invalid_distribution_fails_startup_and_changed_bytes_fail_read`, `tests/mcp_server/test_resources.py::test_non_canonical_and_undeclared_uris_are_refused_without_bytes`, `tests/mcp_server/test_resources.py::test_uri_rejection_precedes_any_service_lookup`, and `tests/mcp_server/test_resources.py::test_two_segment_form_fails_as_an_unknown_version` | security |
| TC-T6-004 | NFR-005, IR-002 | T6 | `tests/mcp_server/test_resources.py::test_uri_contract_is_generation_version_qualified_and_deterministic`, `tests/mcp_server/test_resources.py::test_refusal_codes_follow_the_negotiated_revision`, `tests/mcp_server/test_resources.py::test_resources_module_is_the_planned_registration_surface`, `tests/mcp_server/test_resources.py::test_resource_registrations_satisfy_the_transport_capability_contract`, and `tests/mcp_server/test_resources.py::test_instructions_stay_truthful_once_resources_are_registered` | contract |
| TC-T6-005 | DR-002 | T6 | `tests/mcp_server/test_resources.py::test_resource_descriptor_preserves_declared_fields` | contract |
| TC-T7-001 | FR-005 | T7 | `tests/mcp_server/test_prompts.py::test_prompts_derive_only_from_approved_resource_roles_or_are_absent` | protocol |
| TC-T7-002 | FR-008 | T7 | `tests/mcp_server/test_standard_read.py::test_standard_read_registration_follows_client_matrix_and_reuses_resource_service` | contract |
| TC-T8-001 | FR-007, FR-021, FR-022 | T8 | `tests/mcp_server/test_discovery_tools.py::test_standards_list_matches_catalog_resource` | protocol |
| TC-T8-002 | FR-009, FR-024, DR-005 | T8 | `tests/mcp_server/test_discovery_tools.py::test_repo_inspect_requires_contained_explicit_root_and_preserves_snapshot` | security |
| TC-T8-003 | FR-023, NFR-012 | T8 | `tests/mcp_server/test_discovery_tools.py::test_tool_metadata_is_compact_and_read_only` | snapshot |
| TC-T8-004 | IR-003 | T8 | `tests/mcp_server/test_discovery_tools.py::test_tools_are_typed_and_generic` | contract |
| TC-T8-005 | DR-006 | T8 | `tests/mcp_server/test_discovery_tools.py::test_relationships_preserve_v2_declarations` | contract |
| TC-T9-001 | FR-011, FR-012, FR-013, FR-017, FR-022, IR-003, DR-004, DR-008 | T9 | `tests/mcp_server/test_consumer_tools.py::test_consumer_tools_preserve_typed_service_results` | protocol |
| TC-T9-002 | FR-014, FR-024, FR-028, IR-009 | T9 | `tests/mcp_server/test_consumer_tools.py::test_provider_tools_enforce_exact_dispatch_root_allowlist_and_content_exclusion` | security |
| TC-T9-003 | FR-018, FR-019 | T9 | `tests/mcp_server/security/test_no_writes.py::test_registry_and_calls_cannot_reach_writes_or_apply` | security |
| TC-T9-004 | DR-004 | T9 | `tests/mcp_server/test_consumer_tools.py::test_preview_preserves_control_plane_schema` | contract |
| TC-T9-005 | FR-023, NFR-012 | T9 | `tests/mcp_server/test_consumer_tools.py::test_consumer_tool_metadata_is_compact_and_read_only` | snapshot |
| TC-T10-001 | FR-025, FR-029, NFR-003, NFR-004, NFR-011, IR-008, DR-003, DR-007 | T10 | `tests/mcp_server/contract/test_protocol_conformance.py::test_selected_revision_transcript_capabilities_errors_and_findings_conform` | protocol |
| TC-T10-002 | NFR-005 | T10 | `tests/mcp_server/contract/test_determinism.py::test_semantically_unordered_inputs_have_identical_stable_output` | regression |
| TC-T10-003 | FR-018, NFR-001, NFR-008, NFR-009 | T10 | `tests/mcp_server/integration/test_registry_invariants.py::test_package_growth_adds_data_only_and_registry_has_no_remote_or_write_surface` plus `.github/workflows/check.yml` discovery evidence | integration |
| TC-T10-004 | DR-009 | T10 | `tests/mcp_server/contract/test_determinism.py::test_only_declared_normalization_is_allowed` | regression |
| TC-T10-005 | FR-010 | T10 | `tests/mcp_server/contract/test_no_recommendations.py::test_v1_has_no_unbacked_recommendation_surface` | contract |
| TC-T10-006 | NFR-006, NFR-013 | T10 | `tests/mcp_server/contract/test_import_boundary.py::test_complete_adapter_import_graph_is_one_way_and_sdk_isolated` | contract |
| TC-T10-007 | NFR-012 | T10 | `tests/mcp_server/contract/test_protocol_conformance.py::test_registry_metadata_and_default_text_stay_within_frozen_bounds` | snapshot |
| TC-T11-001 | NFR-009, NFR-010 | T11 | `tests/mcp_server/e2e/test_installed_wheel.py::test_extracted_wheel_matches_source_contract` | end-to-end |
| TC-T11-002 | FR-030, NFR-011 | T11 | Exact Codex and Claude Code smoke commands/results appended to `docs/research/2026-07-28-project-standards-mcp-protocol-sdk-client-matrix.md` | end-to-end |
| TC-T11-003 | FR-016, FR-020 | T11 | `tests/mcp_server/e2e/test_installed_wheel.py::test_documented_commands_match_installed_entrypoint` plus README/reference Markdown gates | documentation |
| TC-T12-001 | Every source row, including the FR-010 omission | T12 | `uv run scripts/plan.py validate docs/plans/2026-07-24-project-standards-mcp-server-plan.md` plus a checklist-evidence audit for every source row and test ID | audit |
| TC-T12-002 | Every Must/Should and the FR-010 omission | T12 | Every command and manual assertion in §13 against one extracted candidate wheel | integration |
| TC-T13-001 | DR-001, NFR-005, DR-009 | T13 | `tests/mcp_services/test_catalog.py::test_provider_descriptors_preserve_declared_execution_contract` | contract |
| TC-T13-002 | FR-021 | T13 | `tests/mcp_services/contract/test_facade.py::test_nested_dto_shapes_are_frozen_field_by_field` | contract |
| TC-T14-001 | FR-012, NFR-005, DR-009 | T14 | `tests/mcp_services/test_providers.py::test_composite_dispatch_input_matches_authoritative_direct_dispatch` | contract |
| TC-T14-002 | FR-012, FR-013 | T14 | `tests/mcp_services/test_providers.py::test_real_packaged_provider_validates_real_consumer_root` | end-to-end |
| TC-T14-003 | FR-012, FR-013 | T14 | `tests/mcp_services/test_providers.py::test_provider_failure_isolates_to_typed_per_result_failure` | contract |
| TC-T14-004 | FR-012, FR-015 | T14 | `tests/mcp_services/test_providers.py::test_every_shipping_catalog_provider_is_seam_served` | contract |
| TC-T15-001 | FR-015, NFR-005, DR-009 | T15 | `tests/control_plane/test_command_resolution.py::test_provider_dispatch_input_matches_each_authoritative_construction` | contract |
| TC-T15-002 | FR-015 | T15 | Existing CLI and executor suites pass with pre-change tallies after the repoint | end-to-end |

### Appendix C. Deferred Work

| Item | Reason deferred | Follow-up |
| --- | --- | --- |
| FR-010 deterministic recommendations | No current typed recommendation service; Could priority. | Revisit only with evidence and spec/plan task. |
| Controlled writes | Explicitly excluded from v1. | Separate write-safety spec after local read-only value. |
| Remote transport | No current need and separate operational design required. | Independent roadmap Step 17 branch after Step 14 local read-only readiness; it does not depend on controlled writes. |
| Fleet reporting | Single-repo correctness first. | Independent roadmap Step 18 branch after Step 14 if a concrete fleet need emerges; it does not depend on controlled writes. |
