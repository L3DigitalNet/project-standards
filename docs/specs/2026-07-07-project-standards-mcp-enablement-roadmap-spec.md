---
spec_id: SPEC-RD01
title: 'Project Standards MCP Enablement Roadmap'
status: approved
profile: full
owner: 'Chris Purcell / L3DigitalNet'
implementer: 'Coding agent under human review'
created: '2026-07-07'
last_reviewed: '2026-07-24'
supersedes: null
superseded_by: null
related:
  adrs:
    - 'docs/adr/adr-0012-mcp-readiness-before-server-implementation.md'
    - 'docs/adr/adr-0005-stable-generic-agent-tooling-interface.md'
    - 'docs/adr/adr-0013-independent-standard-packages-and-relationship-taxonomy.md'
    - 'docs/adr/adr-0018-standard-package-lifecycle-methodology.md'
    - 'docs/adr/adr-0019-packaged-artifact-parity-and-provenance.md'
    - 'docs/adr/adr-0021-standard-packaged-skill-installation-methodology.md'
    - 'docs/adr/adr-0022-standard-packaged-hook-installation-methodology.md'
    - 'docs/adr/adr-0023-unified-consumer-standards-control-plane.md'
    - 'docs/adr/adr-0024-catalog-scoped-package-version-channels.md'

  tickets: []
  repositories:
    - 'L3DigitalNet/project-standards'
  prior_specs:
    - 'SPEC-MT01'
    - 'SPEC-CP01'
    - 'SPEC-BA02'
---

# Project Standards MCP Enablement Roadmap — Specification (Full)

## Revision History

| Version | Date | Author | Change |
| --- | --- | --- | --- |
| 1.3 | 2026-07-24 | Codex with Claude Opus review | Approve and re-lock the current-state and v1 runtime-authority reconciliation after high-effort Opus spec review convergence; record this roadmap's own approval and FR-016 evidence while leaving combined plan convergence open. |
| 1.2 | 2026-07-24 | Codex | Reopen for the narrow T2-T3 reconciliation of current state and v1 tool/runtime authority against the installed Catalog 5 contracts. |
| 1.1 | 2026-07-24 | Codex with Claude Opus review | Resolve lock-review findings by separating optional expansion from controlled writes, normalizing traceability statuses and ADR evidence, and making structured-output acceptance deterministic. |
| 1.0 | 2026-07-24 | Chris Purcell / L3DigitalNet with Codex | Approve and lock the converged roadmap after Claude Opus high-effort review; implementation remains blocked on the Step 09 final protocol, SDK, client, and service-boundary gate. |
| 0.9 | 2026-07-24 | Codex with Claude Opus review | Close the final review advisory by defining every traceability status used and normalizing the remote-deferral guard label. |
| 0.8 | 2026-07-24 | Codex with Claude Opus review | Clarify Step 08 convergence with Step 09 decisions still open, distinguish defined gates from executed evidence, declare completed prerequisite specs, map optional Steps 17-18, and align tool-phase terminology. |
| 0.7 | 2026-07-24 | Chris Purcell / L3DigitalNet with Codex | Refresh the roadmap for published Project Standards 5.8.0, Catalog 5 immutable V2 packages, the unified consumer control plane, Project Specification 1.4, and the July 2026 MCP protocol/SDK transition. Replace the obsolete pre-v5 starting point with completed Step 00-07 evidence, move unresolved MCP decisions into the implementation preflight, and require a converged implementation plan before coding. |
| 0.6 | 2026-07-12 | Chris Purcell / L3DigitalNet with Codex | Record SPEC-MT01 Step 07 as passed with no blocking gaps. The roadmap may proceed to Step 08 when v5 release priorities permit; protocol and SDK research remains required before server MS-0. |
| 0.5 | 2026-07-09 | Coding agent | Added package-methodology ADR references so future MCP phases inherit adoption, lifecycle, provenance, versioning, and skill-installation policy. |
| 0.4 | 2026-07-09 | Coding agent | Resolved accepted ADR references while leaving future MCP ADR placeholders unchanged. |
| 0.3 | 2026-07-07 | ChatGPT | Review pass: aligned sequencing with independent-standard-package validation, SDK caution, and tool/resource safety constraints. |
| 0.2 | 2026-07-07 | ChatGPT | Normalized `spec_id` from mnemonic placeholder to Project Spec-compatible `SPEC-[0-9A-Z]{4}` form and updated prior-spec references. |
| 0.1 | 2026-07-07 | ChatGPT | Initial ordered roadmap from meta-repository preparation through future MCP server implementation. |

**Spec lifecycle:** This approved revision is re-locked after narrow current-state and v1 runtime-authority review and remains change-controlled. `SPEC-MT01` is complete, while Step 08 remains open until the separately reviewed implementation plan also converges. Step 09 remains the next no-code decision gate after that plan review. Later controlled-write and remote-transport phases still require separate approval.

---

## 1. Purpose & Background

This roadmap defines the ordered design and implementation sequence for exposing the now-published Project Standards platform through a local Model Context Protocol (MCP) server without creating a second standards authority.

The key sequencing rule is:

> Do not build the MCP server until the standards repository is manifest-driven, graph-validated, and composition-safe enough that the server can remain generic.

Steps 00-07 established that foundation and are complete. Project Standards 5.8.0 now ships Catalog 5, immutable V2 package families and payloads, validated resource/provider declarations, and one `.standards/` reconciliation control plane. The remaining program begins by reconciling the MCP specifications and plan with those contracts, then builds a thin local server over installed package and control-plane APIs.

This roadmap is not the detailed MCP implementation spec. It is the program plan and dependency order. It states what must exist before each phase starts, what each phase must deliver, and what gates must pass before proceeding.

---

## 2. Scope

### 2.1 In Scope

- Ordered implementation phases from baseline inventory through MCP server hardening.
- Explicit sequencing to prove independent standard packages and relationship metadata before MCP consumes the graph.
- Dependencies and exit criteria for each phase.
- Design gates that prevent premature MCP implementation.
- A no-hard-dependency gate proving standards remain independently adoptable before MCP tooling relies on the graph.
- Required ADR/spec/doc deliverables by phase.
- Future MCP server inclusion at the correct point in the sequence.
- A recommended local-first MCP path: read-only resources first, generic tools second, controlled writes later, remote transport last if ever needed.
- Traceability between roadmap steps, requirements, and validation gates.

### 2.2 Out of Scope (Non-Goals — never)

| ID | Non-Goal | Reason |
| --- | --- | --- |
| NG-001 | Begin MCP implementation before `SPEC-MT01` readiness passes. | Premature implementation would encode missing repository metadata into server code. |
| NG-002 | Build a remote MCP service as the first MCP version. | Local stdio is simpler, safer, and enough for coding-agent workflows. |
| NG-003 | Make MCP required for standards adoption. | Standards must remain consumable through docs, CLI, and CI. |
| NG-004 | Create per-standard MCP tools. | The scalable model is generic tools over manifest-discovered standards. |
| NG-005 | Use MCP as the canonical source of standards truth. | The repository remains canonical; MCP exposes it. |
| NG-006 | Automate destructive writes without explicit review. | MCP tools can be model-controlled; write operations require plan-first and approval boundaries. |
| NG-007 | Introduce hidden hard standard-to-standard dependencies while preparing MCP. | Future MCP must consume an explicit graph; agents must not infer dependency order from prose. |

### 2.3 Won't Have in v1 (deferred — not never)

| ID | Deferred Capability | Why Deferred | Revisit When |
| --- | --- | --- | --- |
| WH-001 | Streamable HTTP remote MCP transport. | Local stdio covers the initial agent workflow and avoids auth/network risk. | After local MCP proves useful and remote/multi-user needs are concrete. |
| WH-002 | GitHub write/mutation tools inside MCP. | Local repo workflows should prove plan/apply semantics first. | After controlled local writes are stable and audited. |
| WH-003 | Semantic contradiction detector for standards prose. | Requires separate review/eval design. | After deterministic graph and resource contracts are stable. |
| WH-004 | Full multi-repo fleet dashboard. | Needs reliable per-repo status and drift primitives first. | After MCP can report one repo accurately. |
| WH-005 | Third-party standard plugin ecosystem. | First-party standard composition must mature first. | After first-party provider model is stable. |

### 2.4 Boundaries

| Boundary | Description |
| --- | --- |
| Roadmap owns | Sequencing, prerequisites, gates, deliverables, and phase dependencies from meta-prep through MCP rollout. |
| Roadmap depends on | Completed `SPEC-MT01`, `SPEC-CP01`, `SPEC-BA02`, ADRs 0023-0024, Catalog 5 package contracts, the existing CLI/control plane, Project Specification 1.4, and `SPEC-MS01`. |
| Roadmap does not own | The exact MCP code design, exact server SDK choice, remote hosting, or final UX of every MCP client. |

---

## 3. Context

### 3.1 Current State

Project Standards 5.8.0 is published from `d007ba0`. Catalog 5 contains seven consumer packages plus reference-only Python Coding and internal Standard Bundle Authoring. Every advertised version is an immutable V2 payload with integrity-checked resources, declared providers and schemas, explicit relationships, and source/wheel parity.

The unified `.standards/` control plane now owns consumer desired state, installed catalog state, applied-state provenance, deterministic reconciliation planning, explicit apply, recovery, and drift reporting. `InstalledDistribution` is the production boundary for package facts; `PackageRepository` is the source-repository validation boundary. Typed provider operations and structured reconciliation results already supply the non-MCP semantics the server should expose.

`SPEC-MT01` Step 07 passed on 2026-07-12. The old readiness gap no longer exists. Step 08 documentation reconciliation is active under `docs/plans/2026-07-24-project-standards-mcp-documentation-reconciliation-plan.md`. Step 09 remains the next no-code decision gate only after the T5 specification review and T7 implementation-plan review converge; it then freezes the protocol, SDK, client, and service boundary before code begins.

External MCP inputs are unusually time-sensitive on this review date. MCP `2025-11-25` is the latest stable protocol revision; the breaking `2026-07-28` revision is a locked release candidate scheduled four days later. The official Python SDK v1 line remains stable while v2 is pre-release with stable release targeted alongside the new protocol. The roadmap therefore forbids selecting a pre-release merely to make this document look current.

### 3.2 Target State

The final target state is a layered system:

```text
Layer 0 — Immutable Catalog 5 packages
  Family indexes, versioned payloads, resources, providers, schemas, and catalog channels.

Layer 1 — Package and control-plane APIs
  InstalledDistribution, PackageRepository, typed provider invocation, reconciliation planning.

Layer 2 — Existing CLI and CI
  Validates packages and consumer repos, reconciles desired state, and reports drift without MCP.

Layer 3 — Project Standards MCP server
  Local stdio adapter exposing package resources and generic read-only tools over Layers 1/2.

Layer 4 — Optional future expansion
  Controlled writes, multi-repo reporting, remote transport, GitHub integration.
```

### 3.3 Assumptions

| ID | Assumption | Impact if False |
| --- | --- | --- |
| A-001 | The future MCP server will target coding-agent workflows first. | If human UI is the primary target, roadmap should add UI/reporting work earlier. |
| A-002 | Local stdio MCP is sufficient for v1. | If remote is mandatory, auth and transport design must move earlier and become blocking. |
| A-003 | Existing package-contract and control-plane APIs can be exposed through a narrow public service boundary without duplicating their semantics. | If the current boundaries are too private or CLI-shaped, the implementation plan must add a tested public facade before the MCP adapter. |
| A-004 | Controlled writes are useful but not required for first value. | If writes are mandatory, plan-token and approval semantics become earlier blockers. |
| A-005 | Current repository tests can add MCP protocol and client-compatibility lanes without restructuring unrelated package tests. | If not, the implementation plan must isolate only the minimum MCP test harness work. |

### 3.4 Constraints

| ID | Constraint | Source |
| --- | --- | --- |
| C-001 | Use the Full Project Specification format. | User instruction. |
| C-002 | `SPEC-MT01` must precede MCP implementation. | Architecture sequencing decision. |
| C-003 | MCP tools remain generic over standards. | Scalability requirement. |
| C-004 | MCP server must not replace docs/CLI/CI. | Standards repository governance requirement. |
| C-005 | Local stdio is preferred before remote transport. | Security and complexity control. |
| C-006 | Sensitive/destructive operations require explicit review and plan-first semantics. | MCP tool safety and agent trust boundary. |
| C-007 | Consumer inspection and planning must use the unified `.standards/` control plane; legacy `.project-standards.yml`, V1 manifests, and copy-adopt engines are migration evidence only. | ADR 0023 and the published Catalog 5 architecture. |
| C-008 | Protocol, SDK, and client feature claims must be reverified at implementation preflight and exact dependency versions locked before code depends on them. | July 2026 MCP protocol and Python SDK transition. |

---

## 4. Goals

| ID | Goal | Success Signal | Achieved By |
| --- | --- | --- | --- |
| G-001 | Preserve the completed MCP-ready repository foundation. | `SPEC-MT01` remains passing and no MCP change bypasses Catalog 5 or the control plane. | FR-003, FR-004, FR-018 |
| G-002 | Build MCP on stable internal contracts, not hardcoded standards. | MCP reads exact payload and control-plane services and exposes generic resources/tools. | MS-1 through MS-4 |
| G-003 | Deliver value incrementally. | Read-only resource server works before planners, writes, or remote features. | FR-007 through FR-014 |
| G-004 | Keep operations safe. | Write tools require prior plan identity and explicit approval. | FR-015, FR-016 |
| G-005 | Preserve non-MCP usability. | Consumer repos can still adopt and validate standards without MCP. | FR-004, FR-005 |
| G-006 | Make the roadmap actionable by coding agents. | Each phase has dependencies, required inputs, and exit criteria. | §19 |
| G-007 | Preserve independent standard packages through the whole program. | The roadmap blocks MCP implementation until the standards graph proves no hidden hard dependencies and surfaces companion/extension relations. | FR-018, Step 04, Step 06, Step 07 |

---

## 5. Stakeholders and Users

| Role / Stakeholder | Concern | Involvement |
| --- | --- | --- |
| Standards owner / architect | Correct order, durable architecture, no premature server coupling. | Approves phase gates and ADRs. |
| Coding agent implementer | Needs unambiguous step order and exit criteria. | Implements phase work under this roadmap. |
| MCP server implementer | Needs clear prerequisites and server scope. | Starts only after readiness gate. |
| Consumer repo maintainer | Needs current adoption workflows to remain stable. | Tests real-world adoption and drift checks. |
| Human reviewer | Needs evidence that each phase is complete before the next starts. | Reviews completion reports and traceability matrix. |

---

## 6. Glossary

| Term | Definition | Notes / Not to be confused with |
| --- | --- | --- |
| Readiness gate | The set of repository conditions that must pass before MCP design/implementation starts. | Defined by `SPEC-MT01` and this roadmap. |
| Phase gate | Exit criteria that must pass before starting the next major phase. | Stronger than a task checklist. |
| Read-only MCP | MCP server exposing resources/prompts and non-mutating analysis tools only. | First server version. |
| Planning tool | Tool that returns an adoption, validation, drift, or write plan without mutating files. | Required before write tools. |
| Controlled write | Mutating operation constrained by prior reviewed plan and explicit user approval. | Deferred until read-only/planning layers are stable. |
| Generic MCP tool | Tool whose arguments include `standard_id`, operation, repo root, ref, or profile. | Opposite of per-standard tool. |
| Package service boundary | Narrow typed facade over installed Catalog 5 package facts, resources, relationships, and provider descriptors. | MCP consumes it; `InstalledDistribution`, package contracts, and the control plane remain authoritative. |
| Consumer control plane | `.standards/` desired/catalog/lock state plus deterministic reconciliation, provider, and drift behavior. | Replaces the roadmap's original adopt-engine assumptions. |
| Transport | MCP communication mechanism, e.g. stdio or Streamable HTTP. | Local stdio first; remote deferred. |

---

## 7. Requirements

### 7.1 Functional Requirements

| ID | Requirement | Rationale | Acceptance Criteria | Priority |
| --- | --- | --- | --- | --- |
| FR-001 | The roadmap shall require baseline inventory before design changes. | Existing strengths and gaps must be known before refactoring. | The completed inventory and this refresh cover Catalog 5 families/payloads, catalog channels, provider contracts, control-plane APIs, validators, workflows, tests, and docs. | Must |
| FR-002 | The roadmap shall require ADRs before implementing irreversible architecture choices. | Decisions should be durable and reviewable. | ADRs for manifest model, authority graph, generic tooling interface, provider model, and MCP readiness are approved or explicitly deferred. | Must |
| FR-003 | The roadmap shall require `SPEC-MT01` implementation before MCP implementation. | MCP must consume stable repo contracts. | `SPEC-MT01` Definition of Done passes. | Must |
| FR-004 | The roadmap shall preserve docs/CLI/CI as first-class interfaces. | MCP is optional access/orchestration, not the canonical system. | No phase removes existing non-MCP workflows. | Must |
| FR-005 | The roadmap shall require a typed package service boundary before MCP registration code. | MCP should not duplicate package loading, manifest parsing, relationship logic, or provider dispatch. | The boundary wraps installed-distribution and control-plane APIs, has direct tests, and returns SDK-independent models. | Must |
| FR-006 | The roadmap shall require the selected Catalog 5 payloads to pass package, graph, resource, and provider validation before MCP resource exposure. | MCP resources must come from version-qualified immutable package contracts. | All selected payloads validate and adding a new fixture payload requires no MCP registration branch. | Must |
| FR-007 | The first MCP implementation phase shall be read-only and local. | Early value with low risk. | Local stdio server lists/reads standards resources and returns repo status without writes. | Must |
| FR-008 | MCP resources shall be derived from exact V2 payload declarations exposed by `InstalledDistribution`. | New standards should appear without tool-code updates. | Adding a valid fixture payload creates resources automatically, while an invalid installed payload prevents startup. | Must |
| FR-009 | MCP tools shall be generic, not per-standard. | Tool surface must remain small and scalable. | Tool list remains stable when a new fixture standard is added. | Must |
| FR-010 | The roadmap shall add planning tools before write tools. | Writes should be reviewable and deterministic. | `reconcile_preview` or an equivalent control-plane preview exists before any apply tool. | Must |
| FR-011 | The roadmap shall require structured MCP tool outputs. | Agents and clients need reliable parsing and traceability. | Every tool result includes typed JSON structured content; findings-bearing results additionally include bounded human-readable text. | Should |
| FR-012 | The roadmap shall require validation/drift tools before adoption apply tools. | Users need confidence before mutating repos. | Read-only validation and drift reports work against at least one consumer fixture. | Must |
| FR-013 | The roadmap shall defer remote transport until local MCP proves useful. | Remote transport adds auth and DNS rebinding concerns. | Remote phase remains blocked until local server adoption criteria pass. | Must |
| FR-014 | The roadmap shall require security review before exposing write tools. | MCP tools can perform arbitrary actions if poorly scoped. | Write-tool ADR/spec includes approval, path allowlist, plan identity, and audit behavior. | Must |
| FR-015 | Controlled write tools shall require prior reviewed plan identity. | Prevents agent from applying unreviewed mutation. | Apply tool rejects stale/missing/mismatched plan IDs. | Should |
| FR-016 | The roadmap shall require a separate detailed MCP implementation spec before coding the server. | This roadmap is sequencing, not implementation design. | Refreshed MCP spec passes local gates and semantic review, then receives owner approval before Step 10 / MS-2 server coding starts. | Must |
| FR-017 | The roadmap shall include fleet/multi-repo reporting only after single-repo accuracy. | Fleet reports multiply errors if primitives are wrong. | Single-repo resource, status, validation, and drift tools pass fixtures first. | Should |
| FR-018 | The roadmap shall require independent-standard-package validation before server implementation. | The MCP server should consume explicit relationships, not infer hidden dependencies. | `SPEC-MT01` graph tests reject hidden hard dependencies and generated indexes show companions/extensions before Step 08 starts. | Must |
| FR-019 | The roadmap shall require MCP protocol/SDK source recheck before dependency selection. | MCP Python SDK and protocol guidance are version-sensitive. | MCP server implementation preflight cannot complete until the latest final protocol, stable SDK line, licenses, conformance status, and target-client capabilities are rechecked, recorded, and exactly constrained. | Must |
| FR-020 | The roadmap shall require a durable, validated, review-converged implementation plan before server code. | The refreshed specifications are too broad to execute safely from milestone prose alone. | One active master plan under `docs/plans/` traces every `SPEC-MS01` Must and Should requirement to dependency-ordered RED-GREEN-REFACTOR tasks and passes its plan validator plus opposite-provider review. | Must |

### 7.2 Non-Functional Requirements

| ID | Category | Requirement | Measurement / Acceptance Criteria | Priority |
| --- | --- | --- | --- | --- |
| NFR-001 | Sequencing | Later phases shall not start until prerequisite gates pass. | Completion report for each milestone names gate evidence. | Must |
| NFR-002 | Safety | Mutating features shall be delayed until read-only and planning features are stable. | No apply/write tools in first MCP release. | Must |
| NFR-003 | Maintainability | MCP implementation shall call package/control-plane service APIs instead of parsing prose, V1 manifests, or CLI text. | Code review verifies no per-standard switch statements and no duplicate package, provider, reconciliation, or finding semantics in the MCP layer. | Must |
| NFR-004 | Context efficiency | MCP resources shall support lazy access to standard docs/summaries/templates. | Client can fetch one standard summary without loading all standards. | Must |
| NFR-005 | Portability | Local server shall run from source checkout and an extracted/installed wheel with equivalent exposed package facts. | Contract tests cover both modes and compare normalized resource/tool results. | Should |
| NFR-006 | Observability | MCP tools shall return explicit findings and traceable resource links. | Structured outputs include rule IDs, standard IDs, paths, severity, and remediation. | Should |
| NFR-007 | Security | Remote transport shall require a separate threat model. | No remote phase begins without security ADR/spec. | Must |

### 7.3 Interface Requirements

| ID | Interface | Requirement | Contract / Format | Acceptance Criteria |
| --- | --- | --- | --- | --- |
| IR-001 | Project specs | Each major phase shall have or reference an approved spec. | Full/Standard/Light project-spec docs as appropriate. | MCP coding does not begin without MCP-specific spec. |
| IR-002 | ADRs | Architecture decisions shall be recorded in ADRs. | ADR Standard. | ADRs referenced from specs and implementation PRs. |
| IR-003 | Package/control-plane APIs | MCP shall consume typed package, resource, provider, and reconciliation-plan APIs behind an SDK-independent facade. | Python typed interfaces; JSON CLI output is a compatibility oracle, not the in-process implementation boundary. | Read-only MCP can list resources and inspect/plan against a consumer fixture without parsing subprocess prose. |
| IR-004 | MCP transport | First MCP version shall use stdio. | MCP stdio server process. | Client can launch server locally as subprocess. |
| IR-005 | MCP resources | Standards resources shall use exact payload-derived URIs. | Generation- and version-qualified `standards://...` scheme. | Resource discovery matches the complete validated `InstalledDistribution` and every read rechecks declaration, contained path, and digest integrity. |
| IR-006 | MCP tools | Tools shall expose generic operations. | Stable tool names and input/output schemas. | New standard fixture does not add tools. |
| IR-007 | Controlled writes | Apply tools shall require plan ID/hash. | Plan output + apply input contract. | Apply rejects mismatched plan. |

### 7.4 Data Requirements

| ID | Data Entity | Requirement | Validation Rules | Ownership |
| --- | --- | --- | --- | --- |
| DR-001 | Roadmap phase | Track step order, prerequisites, required inputs, exit criteria, and unlocks. | Unique step label; dependencies exist; no circular dependency. | This roadmap spec. |
| DR-002 | Readiness gate | Track blocking conditions before MCP. | All Must checklist items pass. | `SPEC-MT01`. |
| DR-003 | MCP resource descriptor | Generated from the exact selected payload's declared resources. | URI unique; payload identity/version and digest retained; path exists; media type declared. | Package service boundary. |
| DR-004 | MCP tool descriptor | Stable generic tool schemas. | Names stable; input/output schema defined; safety class declared. | MCP implementation spec. |
| DR-005 | Plan identity | Identifies reviewed mutation plan. | Hash or opaque ID tied to standard IDs, repo state, and action list. | Future write-tool design. |

---

## 8. Architecture and Design

### 8.1 Architecture Summary

The roadmap now starts from a completed platform rather than a proposed graph. Catalog 5 package manifests, immutable resources, providers, and relationships feed a narrow SDK-independent service facade. The same facade delegates consumer inspection and planning to the `.standards/` control plane. A local read-only MCP adapter registers protocol resources, prompts where clients support them, and a small set of generic tools. Controlled writes, remote transport, and fleet reporting remain later optional phases with separate approval gates.

### 8.2 Architecture Views

#### 8.2.1 Context View

```mermaid
flowchart LR
    StandardsRepo[Catalog 5 Packages] --> Services[Package and Control-Plane Services]
    Services --> CLI[Existing CLI / CI]
    Services --> MCP[Future MCP Server]
    MCP --> Agent[Claude Code / Codex / Other MCP Client]
    Agent --> Consumer[Consumer Repository]
    CLI --> Consumer
```

#### 8.2.2 Container / Deployment View

```mermaid
flowchart TB
    subgraph PhaseA[Meta Repo Preparation]
        ADRs[ADRs]
        Manifests[V2 family and payload manifests]
        Graph[Package and Graph Validators]
        Fixtures[Consumer Fixtures]
    end

    subgraph PhaseB[MCP Server]
        Stdio[Local stdio Transport]
        Resources[Resource Provider]
        Tools[Generic Tools]
        Plans[Planning Layer]
        Writes[Controlled Writes - Later]
    end

    ADRs --> Manifests --> Graph --> Fixtures --> Stdio
    Stdio --> Resources --> Tools --> Plans --> Writes
```

#### 8.2.3 Component View

| Component | Responsibility | Interfaces | Notes |
| --- | --- | --- | --- |
| `SPEC-MT01` | Defines the meta-repo changes required before MCP. | Full project spec. | Blocking prerequisite. |
| Package service facade | Exposes version-qualified package, resource, relationship, and provider facts from installed Catalog 5 data. | SDK-independent Python models. | May wrap existing internals; must not reinterpret them. |
| Consumer service facade | Exposes control-plane state, reconciliation plans, findings, and read-only provider results. | SDK-independent Python models. | No CLI-text parsing or writes in v1. |
| Read-only MCP server | Exposes standards resources and safe analysis. | MCP stdio. | First server version. |
| Generic MCP read layer | Provides `standards_list`, `repo_inspect`, `validate_repo`, and `drift_check`. | MCP tools with schemas. | No per-standard tools; no mutation. |
| Generic MCP planning layer | Provides later-phase `reconcile_preview` over the existing control-plane plan. | Stable reconciliation schema. | Planning precedes any separately governed apply tool. |
| Controlled write layer | Applies reviewed plans. | MCP tools with plan IDs. | Later phase only. |
| Remote transport layer | Optional Streamable HTTP. | MCP HTTP endpoint. | Requires separate security spec. |

### 8.3 Design Decisions

| ID | Decision | Rationale | Alternatives Considered | ADR |
| --- | --- | --- | --- | --- |
| D-001 | Complete `SPEC-MT01` before MCP implementation. | Prevents hardcoded server assumptions. | Start MCP now and refactor later. | `adr-0012-mcp-readiness-before-server-implementation.md` |
| D-002 | Local stdio first for MCP. | Simplest local agent integration and lowest security surface. | Streamable HTTP first. | Planned MCP boundary ADR in Step 09 |
| D-003 | Read-only MCP first. | Early value without mutation risk. | Start with adoption apply/write tools. | Planned MCP boundary ADR in Step 09 |
| D-004 | Generic tools only. | Stable tool surface as standards grow. | Per-standard tools. | `adr-0005-stable-generic-agent-tooling-interface.md` |
| D-005 | Payload-declared resources. | New package versions become visible automatically and exact version/digest identity survives exposure. | Hardcoded resource list. | ADR 0010 plus `SPEC-BA02` |
| D-006 | Plan-first controlled writes. | Mutations need reviewable intent and replay protection. | Direct apply commands from agent request. | Future controlled-write ADR in Step 15 |
| D-007 | Remote transport deferred. | HTTP transport requires auth/origin/security design. | Remote server first. | Planned MCP boundary ADR in Step 09 |
| D-008 | Independent-standard-package validation gates MCP implementation. | MCP must consume a composable graph, not repair dependency problems at runtime. | Let MCP auto-adopt or auto-require standards; rejected. | `adr-0013-independent-standard-packages-and-relationship-taxonomy.md` |
| D-009 | Recheck MCP spec/SDK before implementation starts. | MCP SDK and protocol releases are active; dependency decisions can stale quickly. | Freeze July 2026 research as final; rejected. | Planned protocol/SDK selection ADR in Step 09 |
| D-010 | Reuse the unified consumer control plane for repository state, reconciliation plans, findings, and provider execution. | ADR 0023 superseded the original adopt-engine and package-specific provenance model. | Preserve a parallel MCP-only adoption/drift model; rejected. | ADR 0023 |

### 8.4 Solution Alternatives Considered

| Alternative | Why Rejected |
| --- | --- |
| Build MCP directly over filesystem layout or CLI text. | Would duplicate package/control-plane semantics and couple the protocol layer to incidental presentation. |
| Build a CLI-only solution and skip MCP. | CLI remains required, but MCP adds lazy resource and tool integration for agents. |
| Build a remote MCP service first. | Adds security/auth complexity before proving local value. |
| Implement write tools first. | Higher risk; read-only and planning tools deliver value sooner and establish safety contracts. |
| Expose one MCP tool per standard. | Tool surface grows linearly with standards and wastes context. |

### 8.5 Design Constraints

- No MCP coding before the refreshed specs and implementation plan converge and Step 09 freezes the implementation boundary.
- No write tools before read-only and planning tools.
- No remote transport before local stdio proof and security spec.
- No per-standard tools unless an approved ADR proves a generic operation cannot represent the need.
- No standards canonical data stored only in MCP server code.
- No V1 manifest, legacy config, copy-adopt, or package-specific provenance path may become a current MCP authority.
- No SDK type may cross the MCP adapter boundary into package/control-plane services.
- No hidden mutation; every write requires plan review and explicit authorization.

### 8.6 Dependency Policy

| Dependency | Allowed? | Reason |
| --- | --- | --- |
| Official MCP Python SDK | Conditional after Step 09 | Select an exact stable release only after rechecking the final protocol, SDK support/conformance, license, and target-client behavior. Pre-release use requires explicit owner approval and a recorded risk disposition. |
| Existing `project-standards` package | Yes | Canonical implementation substrate. |
| New web framework | No for local stdio phase | Remote HTTP is deferred. |
| GitHub API client | Deferred | GitHub mutations and fleet reporting are later phases. |
| Persistent database | No for v1 | Local server can derive state from repo files and package metadata. |

---

## 9. Data Model

The roadmap itself uses phase records. The future MCP spec should turn relevant records into implementation tickets or project-spec milestones.

| Field             | Meaning                                                 |
| ----------------- | ------------------------------------------------------- |
| `step_label`      | Ordered phase identifier, e.g. `Step 03`.               |
| `name`            | Short phase name.                                       |
| `depends_on`      | Required earlier phases/gates.                          |
| `required_inputs` | Specs, ADRs, tests, docs, or artifacts needed to start. |
| `deliverables`    | Concrete files/code/docs produced.                      |
| `exit_criteria`   | Observable completion gate.                             |
| `unlocks`         | Next phase(s) allowed after completion.                 |

---

## 10. Behavior and Workflows

### 10.1 Primary Workflow

```mermaid
sequenceDiagram
    actor Owner
    participant Meta as SPEC-MT01 Work
    participant Gate as Readiness Gate
    participant MCPSpec as MCP Implementation Spec
    participant MCP as MCP Server
    participant Consumer as Consumer Repo Fixture

    Owner->>Meta: Complete manifests, graph validation, ADRs
    Meta->>Gate: Produce readiness report
    Gate-->>Owner: Pass / blockers
    Owner->>MCPSpec: Author detailed MCP spec after pass
    MCPSpec->>MCP: Implement read-only stdio server
    MCP->>Consumer: Inspect/list/read/validate without writes
    MCP-->>Owner: Structured reports and resource links
```

Steps:

1. Complete baseline inventory and ADR foundation.
2. Implement manifest/graph preparation in `SPEC-MT01`.
3. Retrofit standards and prove composition.
4. Pass MCP-readiness gate.
5. Write and approve detailed MCP implementation spec.
6. Implement local read-only stdio MCP resources.
7. Add generic non-mutating tools.
8. Add planning tools.
9. Add controlled write tools only after a separate safety review.
10. Consider remote/multi-repo features only after local proof.

Expected result:

> The MCP server arrives after the repository is ready, remains generic, and can scale with new standards through manifests and providers.

### 10.2 Alternate Workflows

| ID | Trigger | Behavior | Expected Result |
| --- | --- | --- | --- |
| AW-001 | Readiness gate fails. | Stop MCP work and repair meta-repo blockers. | No server work starts on unstable contracts. |
| AW-002 | MCP client requires an operation not covered by generic tools. | Add to OQ/ADR; prefer generic operation or prompt/resource. | Tool surface remains disciplined. |
| AW-003 | A write use case becomes urgent before planning tools. | Create separate safety spec; do not bypass plan-first order. | Writes remain controlled. |
| AW-004 | Remote MCP becomes mandatory. | Insert security/transport spec before implementation. | Remote is designed, not bolted on. |
| AW-005 | Existing consumer repo reveals standards graph gap. | Treat as regression against `SPEC-MT01`; fix graph/manifest before server workaround. | Repository remains canonical. |

### 10.3 Edge Cases

| ID | Edge Case | Expected Behavior |
| --- | --- | --- |
| EC-001 | New standard added after MCP v1 ships. | MCP resources and generic tools discover it through manifests without new tool names. |
| EC-002 | Standard declares no validator. | MCP reports no validator provider rather than inventing one. |
| EC-003 | Consumer repo has local exception. | MCP reports exception and links ADR/config if declared; otherwise reports unmanaged drift. |
| EC-004 | The installed distribution contains an undeclared, missing, escaping, or digest-mismatched resource. | Eager construction or the selected read fails closed with a structured integrity error; the server never exposes a valid subset or trusts generated documentation as runtime authority. |
| EC-005 | Client asks MCP to apply unplanned change. | Apply tool rejects request and asks for a plan-first workflow. |

### 10.4 State Transitions

```mermaid
stateDiagram-v2
    [*] --> MetaPrep
    MetaPrep --> ReadyForMCPSpec : readiness gate passes
    ReadyForMCPSpec --> MCPReadOnly : MCP spec approved
    MCPReadOnly --> MCPPlanning : read-only resources/tools pass fixtures
    MCPPlanning --> MCPControlledWrites : safety ADR/spec approved
    MCPControlledWrites --> MCPRemoteCandidate : local write tools stable
    MCPRemoteCandidate --> MCPRemote : remote transport spec approved
```

| State | Meaning | Entry Condition | Exit Condition |
| --- | --- | --- | --- |
| MetaPrep | Repository is being prepared. | Start of roadmap. | `SPEC-MT01` gate passes. |
| ReadyForMCPSpec | Detailed MCP spec may be written. | Manifests/graph/ADRs complete. | MCP implementation spec approved. |
| MCPReadOnly | Local read-only MCP exists. | Stdio server exposes resources and safe status tools. | Read-only fixture tests pass. |
| MCPPlanning | MCP can produce plans/reports. | Generic planning/drift/validation tools work. | Safety design approved. |
| MCPControlledWrites | MCP can apply reviewed plans. | Plan-first write tools exist. | Local use proves stable. |
| MCPRemoteCandidate | Remote may be considered. | Local controlled workflows stable. | Remote security spec approved. |
| MCPRemote | Optional remote MCP exists. | Transport/auth/security implemented. | Ongoing maintenance. |

---

## 11. UI Pages / API Endpoints

No web UI is in scope. Future MCP surfaces are protocol interfaces.

| Surface | Purpose | Key Actions | Authorization |
| --- | --- | --- | --- |
| Local MCP stdio server | Agent-facing local integration. | List/read resources, run generic tools. | User launches local process. |
| MCP resource URIs | Lazy standard content. | Read canonical standard docs/templates/summaries. | Local repo/package read access. |
| MCP tool schemas | Generic actions. | Inspect repo, validate, plan, drift check. | Client/user approval model. |
| Future remote MCP endpoint | Optional later transport. | Same capabilities over HTTP. | Requires separate auth/security design. |

---

## 12. Error Handling and Recovery

### 12.1 Expected Failures

| ID | Failure Mode | User/System Behavior | Logging / Observability | Recovery |
| --- | --- | --- | --- | --- |
| ERR-001 | MCP work requested before readiness. | Roadmap blocks and points to failing readiness items. | Completion report lists blockers. | Finish `SPEC-MT01` gates. |
| ERR-002 | Read-only MCP cannot validate the complete installed Catalog 5 distribution. | Server fails closed before stdio registration. | Structured startup error on stderr only. | Fix the installed family/payload declaration, resource path, bytes, or digest. |
| ERR-003 | Resource path missing. | Resource read returns structured error. | Error includes standard ID and URI. | Fix manifest/resource. |
| ERR-004 | Tool request targets unknown standard. | Tool returns validation error, not fallback guess. | Structured tool error. | Add manifest or correct ID. |
| ERR-005 | Apply requested without plan. | Apply tool refuses. | Tool error says plan required. | Run planning tool first. |
| ERR-006 | Remote transport security unknown. | Remote phase blocked. | OQ/ADR remains open. | Complete remote transport security spec. |

### 12.2 Retry and Idempotency

- Read-only tools may be retried safely.
- Planning tools are deterministic for a given repo state and standards ref.
- Apply tools, once introduced, must bind to a plan ID/hash and target repo state.
- Remote transport retry behavior is deferred to the remote MCP spec.

### 12.3 Rollback / Recovery

If MCP implementation exposes architecture gaps:

1. Stop adding MCP-specific workarounds.
2. Record the gap against `SPEC-MT01` or the MCP implementation spec.
3. Fix the manifest/graph/provider contract first.
4. Regenerate MCP resources/tools from the corrected contract.
5. Add regression tests so the gap does not reappear.

---

## 13. Security and Privacy

### 13.1 Authentication

Local stdio v1 requires no network authentication. The user/client launches the server as a subprocess. Remote authentication is deferred.

### 13.2 Authorization

| Actor / Role | Allowed Actions | Denied Actions |
| --- | --- | --- |
| Local user | Launch MCP server, approve tool calls, review plans. | N/A within local account boundary. |
| MCP server read-only phase | Read manifests, standards resources, consumer repo metadata. | Mutate files, call external services, perform writes. |
| MCP controlled-write phase | Apply approved plans to allowed paths. | Apply unplanned/stale/destructive changes. |
| Remote MCP phase | Deferred. | No remote access until security spec exists. |

### 13.3 Secrets

No secrets are required for local read-only MCP. Remote or GitHub-integrated phases may introduce credentials and require a separate secret model.

| Secret | Storage Location | Access Pattern | Rotation / Notes |
| --- | --- | --- | --- |
| None in v1 | N/A | N/A | Do not add tokens for local read-only server. |

### 13.4 Sensitive Data

| Data | Classification | Storage | Transmission | Retention |
| --- | --- | --- | --- | --- |
| Standards resources | Public/internal depending repo visibility | Local repo/package | Local stdio messages | No separate persistence |
| Consumer repo metadata | Internal | Local repo | Local stdio messages | No separate persistence in v1 |
| Plans/reports | Internal | Optional local files or transient tool results | Local stdio | Defined by MCP implementation spec |
| Secrets | Restricted | Not accessed in v1 | Not transmitted | N/A |

### 13.5 Threats and Mitigations

| Threat | Impact | Mitigation |
| --- | --- | --- |
| Premature MCP hardcoding. | New standards require code changes and server becomes policy source. | Completed readiness gate plus package-service facade prerequisite. |
| Tool poisoning / untrusted output. | Agent may treat repo data as instructions. | Keep instruction hierarchy explicit; expose standard docs as resources/data. |
| Unsafe write tool. | File corruption or unintended repo mutation. | Read-only first; plan-first writes; explicit approval; path allowlists. |
| Remote local-server attack. | Remote site interacts with local server. | Remote deferred; if used, bind localhost, validate origins, require auth. |
| Overbroad resource exposure. | Sensitive files leak into context. | Manifest-declared resources only; consumer root boundaries. |

### 13.6 Hardening Checklist

- [x] Read-only MCP before writes.
- [x] Local stdio before remote.
- [x] Generic tools before standard-specific exceptions.
- [ ] Refreshed MCP specs and implementation plan converge before coding server.
- [ ] Write-tool safety ADR completed before apply tools.
- [ ] Remote transport security spec completed before HTTP.
- [ ] Tool outputs structured and sanitized.
- [ ] Resource exposure restricted to manifests and approved repo roots.

---

## 14. Capacity and Scale Assumptions

| Dimension | v1 Expectation | Growth Assumption | Design Consequence |
| --- | --- | --- | --- |
| Package-family count | 9 in Catalog 5 | Dozens | Generic tools and payload-declared resources. |
| Consumer repos | 1–5 early dogfood repos | 20+ personal/org repos | Single-repo accuracy before fleet reporting. |
| MCP clients | Claude Code/Codex-like local agents | More clients later | Use protocol-conformant stdio and stable schemas. |
| Resource count | Hundreds at most | More with examples/templates | Lazy loading and resource annotations. |
| Tool count | Small stable set | Should remain small | Avoid per-standard tools. |

---

## 15. Risks

| ID | Risk | Likelihood | Impact | Mitigation | Owner |
| --- | --- | --- | --- | --- | --- |
| R-001 | MCP code starts from stale specifications or before the Step 09 dependency/client gate. | Med | High | Require converged specs/plan, accepted ADRs, and an exact stable dependency contract before the first RED test. | Standards owner |
| R-002 | Read-only MCP lacks enough value. | Low | Med | Include repo inspection, resource reading, validation status, and drift report in early tools. | MCP spec owner |
| R-003 | Tool surface grows too large. | Med | High | Generic tool ADR; review every proposed new tool as a new operation, not new standard. | MCP owner |
| R-004 | Controlled writes introduce risk. | Med | High | Defer writes; require plan identity and safety spec. | Security reviewer |
| R-005 | Different MCP clients behave differently. | Med | Med | Keep server protocol-simple, structured, and local first. | MCP implementer |
| R-006 | Remote transport becomes tempting too early. | Med | High | Explicitly defer until local adoption criteria pass. | Standards owner |
| R-007 | Existing package/control-plane internals leak MCP SDK types or force CLI-text parsing. | Med | High | Add one narrow SDK-independent service facade before protocol registration. | Tooling owner |

---

## 16. Compliance, Licensing, and Data Rights

- [ ] MCP SDK licensing reviewed before adding dependency.
- [ ] No remote data transmission in local read-only v1.
- [ ] Consumer repo privacy boundaries documented before repo inspection tools ship.
- [ ] Remote transport threat model completed before HTTP.
- [ ] Any GitHub integration reviews token scopes and repository access boundaries.

---

## 17. Testing and Acceptance

### 17.1 Definition of Done

- [x] `SPEC-MT01` readiness gate passes; see `docs/mcp-readiness.md`.
- [ ] Refreshed `SPEC-RD01`, `SPEC-MS01`, and the implementation plan pass local validation and Claude Opus review to convergence.
- [ ] Required MCP boundary and dependency ADRs are accepted before implementation code.
- [ ] Read-only local MCP can list/read exact V2 payload resources from a fully validated `InstalledDistribution`.
- [ ] Generic tools work against a standards repo and at least one consumer fixture.
- [ ] Adding a fixture standard changes resources/data but not top-level tools.
- [ ] Planning tools precede write tools.
- [ ] Write tools, if implemented, reject missing/stale/mismatched plan identity.
- [ ] Remote transport remains deferred unless separately approved.

### 17.2 Test Strategy

| Layer | Scope | Required Coverage | Required? |
| --- | --- | --- | --- |
| Meta readiness | `SPEC-MT01` graph/manifests/fixtures. | All Must readiness checks. | Yes |
| MCP unit | Resource URI generation, tool schemas, structured outputs. | Valid/invalid arguments and unknown standards. | Yes for MCP phase |
| MCP integration | Local stdio server lifecycle. | Start server, initialize, list resources/tools, read resource, call tools. | Yes for MCP phase |
| Consumer fixture | Repo inspection, reconciliation preview, validate, drift check. | At least one Python/docs repo fixture. | Yes |
| Safety | Controlled write plan/apply. | Missing plan, stale plan, path escape, symlink/path allowlist. | Required before write phase |
| Remote | HTTP transport/auth/origin. | Deferred. | No for v1 |

### 17.3 Requirement-to-Test Traceability

Status distinguishes completed evidence (`Passing`), an active prohibition (`Guard Active`), a specified but unexecuted future gate (`Gate Defined`), and implementation work that has begun but lacks complete acceptance evidence (`In Progress`) or has not begun (`Not Started`).

| Requirement ID | Test / Verification Method | Status |
| --- | --- | --- |
| FR-001 | `docs/mcp-readiness.md`, `docs/handoff/architecture.md`, Catalog 5 manifests, and the 2026-07-24 spec refresh evidence ledger. | Passing |
| FR-002 | Accepted ADRs 0005, 0012, 0013, 0018, 0019, and 0021-0024; Step 09 plan task covers remaining MCP-only decisions before code. | Passing |
| FR-003 | `docs/mcp-readiness.md`. | Passing |
| FR-004 | Published 5.8.0 verification plus future implementation regression gates. | Passing; Gate Defined |
| FR-005 | Current package/control-plane API tests plus planned facade contract tests. | In Progress |
| FR-006 | `docs/research/2026-07-12-catalog-5-mcp-exposure-review.md` and current package-contract gates. | Passing |
| FR-007 | Local read-only MCP smoke test. | Not Started |
| FR-008 | Fixture standard resource discovery test. | Not Started |
| FR-009 | Tool list snapshot test across fixture standard addition. | Not Started |
| FR-010 | Planning tool exists before apply tool registration. | Not Started |
| FR-011 | Structured output schema review. | Not Started |
| FR-012 | Validation/drift consumer fixture tests. | Not Started |
| FR-013 | Remote transport blocked until local evidence criteria. | Guard Active |
| FR-014 | Write safety ADR/spec review. | Not Started |
| FR-015 | Apply tool plan identity tests, when write phase starts. | Not Started |
| FR-016 | Refreshed `SPEC-MS01` and converged specification-review result. | Passing |
| FR-017 | Single-repo primitive fixture tests. | Not Started |
| FR-018 | `docs/mcp-readiness.md`; zero-finding required-manifest graph validation and composition tests. | Passing |
| FR-019 | 2026-07-24 stable/RC research baseline plus mandatory Step 09 final recheck and exact pin. | Gate Defined |
| FR-020 | `docs/plans/2026-07-24-project-standards-mcp-server-plan.md`, `scripts/plan.py validate`, and converged plan-review result. | In Progress |

---

## 18. Deployment and Operations

### 18.1 Runtime Environment

| Item | Value |
| --- | --- |
| Runtime | Python 3.14+ package and local MCP subprocess. |
| OS / Platform | Developer workstation / local coding-agent environment. |
| Datastore | None; immutable installed payload bytes and an explicitly selected consumer repository remain authoritative. |
| External services | None for read-only local v1. |
| Scheduling | None. |
| Hosting | Local process launched by MCP client. |

Runtime services:

| Service | Purpose | Start Mode | Health Signal |
| --- | --- | --- | --- |
| Project Standards MCP | Expose standards resources and generic tools. | Client-launched stdio subprocess. | Successful protocol discovery plus supported list/read/call operations for the selected final revision. |

### 18.2 Configuration

The v1 server has no behavior-changing environment-variable configuration. The launch command and selected Catalog 5 distribution determine package resources. Consumer operations receive an approved root from the client capability when supported or an explicit absolute `repo_root` argument. Read-only behavior is structural because no mutating tools are registered.

**Environment matrix:**

| Aspect | Dev | CI | User Local |
| --- | --- | --- | --- |
| MCP launch | Source checkout. | Integration test subprocess. | Installed package command. |
| Resources | Fixture + real standards. | Fixture + real standards. | Installed package or cloned repo. |
| Writes | Disabled until later phase. | Safety tests only. | Disabled by default. |

### 18.3 Deployment Flow

1. Preserve the completed `SPEC-MT01` readiness evidence.
2. Converge the refreshed roadmap, server specification, and implementation plan.
3. Recheck and record the final protocol, stable SDK, license, conformance, and target-client matrix; accept MCP boundary ADRs.
4. Add the SDK-independent package/control-plane service facade through RED-GREEN-REFACTOR tasks.
5. Add the client-launched stdio adapter and protocol contract tests.
6. Add version-qualified resource discovery/reads and only the client-compatible prompt surface.
7. Add generic non-mutating tools over package/control-plane services.
8. Dogfood with repository fixtures, an installed wheel, and an owner-approved real consumer repository.
9. Keep write and remote work outside the v1 implementation plan.
10. Release only through a separately authorized release task after every existing non-MCP gate remains green.

### 18.4 Rollout Controls

- Server starts read-only.
- No write tools are registered in v1.
- Remote transport absent until approved.
- Tool count reviewed in every server PR.
- New standard fixture must not add top-level tools.

### 18.5 Observability

Minimum signals:

- MCP startup errors to stderr only, never stdout outside protocol messages.
- Structured tool results with rule IDs and severities.
- Debug logging optional and disabled by default.
- Test fixtures capture protocol exchange failures.

| Alert | Trigger | Severity | Owner / Action |
| --- | --- | --- | --- |
| MCP startup failure | Complete installed-distribution validation fails. | Warning during dev / blocking in CI | Fix the invalid family, payload, resource declaration, contained path, bytes, or digest. |
| Tool schema regression | Integration test fails. | Blocking | Restore schema compatibility or version intentionally. |
| Resource integrity failure | Declared resource is missing, escapes its payload, or no longer matches its digest. | Blocking | Repair and republish the immutable payload; never expose a partial catalog. |

### 18.6 Backup and Disaster Recovery

No durable runtime data in read-only v1. Plans/reports, if later persisted, should be ordinary repo artifacts or temporary files documented by the MCP implementation spec.

### 18.7 Documentation Deliverables

- [x] This roadmap approved.
- [x] `SPEC-MT01` completed; Step 07 passed on 2026-07-12.
- [ ] Refreshed MCP implementation spec and plan converge after readiness.
- [ ] MCP ADRs for local stdio, read-only-first, generic tools, controlled writes, and remote deferral.
- [ ] User setup instructions for local MCP.
- [ ] Tool/resource reference generated from server schemas.
- [ ] Security notes for write and remote phases.

---

## 19. Implementation Plan

### Waves

| Wave | Scope | Exit Criteria |
| --- | --- | --- |
| Wave 0 | Repository readiness and contracts. | `SPEC-MT01` complete. |
| Wave 1 | Current MCP specification and implementation planning. | Refreshed specs and plan converge; boundary/dependency ADR work is explicitly sequenced. |
| Wave 2 | Local read-only MCP. | Resource server and safe generic tools pass fixtures. |
| Wave 3 | Planning and drift workflows. | Plans and reports work without writes. |
| Wave 4 | Controlled writes. | Safety model approved and apply tools pass tests. |
| Wave 5 | Optional expansion. | Remote/fleet specs approved separately. |

### Ordered Step List

| Step | Name | Depends On | Required Before Starting | Deliverables | Exit Criteria | Unlocks |
| --- | --- | --- | --- | --- | --- | --- |
| Step 00 | Baseline inventory | None | Current repo available. | Inventory of standards, registry, bundles, manifests, validators, tests, workflows. | Inventory reviewed. | Step 01 |
| Step 01 | ADR foundation | Step 00 | Inventory complete. | ADR drafts for manifest, authority graph, generic tooling, provider model, readiness. | ADR direction approved enough for implementation. | Step 02 |
| Step 02 | Meta-standard draft | Step 01 | ADR direction. | Standard Bundle Authoring Standard draft. | Defines required bundle contract. | Step 03 |
| Step 03 | Manifest schema/model | Step 02 | Meta-standard draft. | `standard.toml` schema/model and fixtures. | Valid/invalid fixtures pass/fail. | Step 04 |
| Step 04 | Standards graph validator | Step 03 | Manifest model. | Graph loader, authority/capability/resource/relationship validation, CLI. | Fake and real repo graph tests pass, including hidden dependency rejection. | Step 05 |
| Step 05 | Retrofit existing standards | Step 04 | Graph validator available. | Manifests/resources/authorities for all existing standards. | All existing standards pass graph validation. | Step 06 |
| Step 06 | Dogfood fixtures and generated index | Step 05 | Standards retrofitted. | Consumer fixtures, generated standards index, relationship catalog, freshness checks. | Pairwise/all-standard fixture checks pass and companion/extension metadata is visible. | Step 07 |
| Step 07 | MCP-readiness gate | Step 06 | `SPEC-MT01` traceability complete. | Readiness report. | No blocking gaps, no hidden hard dependencies, no stale generated indexes. | Step 08 |
| Step 08 | MCP specification and plan refresh | Step 07 | Readiness gate pass and current repository evidence. | Refreshed `SPEC-RD01`, `SPEC-MS01`, reference pack, and durable TDD implementation plan. | Local validators pass and Claude Opus spec/plan reviews converge. OQ-001 and other Step 09 decisions may remain open only when the converged plan binds them to a pre-code Step 09 gate. | Step 09 |
| Step 09 | Implementation boundary and dependency freeze | Step 08 | Converged spec and plan; final protocol/SDK releases available or owner accepts a documented alternative. | ADRs for service/SDK boundary, stdio/read-only scope, resource URI rules, protocol/SDK version selection, and remote deferral; exact dependency constraint and client matrix. | ADRs accepted; final protocol and stable SDK support are proven; no blocking client gap. | Step 10 |
| Step 10 | Service facade and MCP skeleton | Step 09 | Accepted boundary ADRs and exact dependency lock. | SDK-independent package/control-plane facade, package entrypoint, local stdio adapter, protocol tests. | Server starts from source and installed wheel, reports accurate capabilities, and keeps stdout protocol-clean. | Step 11 |
| Step 11 | Resource and prompt layer | Step 10 | Service facade available. | Payload-derived, version-qualified resources and only client-supported prompt exposure. | List/read resources pass; fixture payload appears without registration changes; prompt/tool fallback decisions match the client matrix. | Step 12 |
| Step 12 | Generic read-only tools | Step 11 | Resource layer. | `standards_list`, `repo_inspect`, plus `standard_read` only if the client matrix proves a primary client cannot give the model direct resource access. | Tool schemas and fixture calls pass; the fallback decision is justified by the frozen client matrix. | Step 13 |
| Step 13 | Validation and drift tools | Step 12 | Repo inspection working. | `validate_repo`, `drift_check`, structured findings. | Consumer fixture reports accurately. | Step 14 |
| Step 14 | Planning tools | Step 13 | Validation/drift stable. | `reconcile_preview` exposes the authoritative public `ReconciliationPlan.to_jsonable()` facts plus its reconciliation fingerprint, without provider mutation-plan preview or apply access. | Preview output is deterministic, content-safe, reviewable, and byte-equivalent in meaning to authoritative control-plane JSON. | Step 15; optional Step 17 or Step 18 design |
| Step 15 | Controlled write safety spec | Step 14 | Planning tools stable. | Separate safety spec/ADR for apply tools. | Approved by owner. | Step 16 |
| Step 16 | Controlled local write tools | Step 15 | Safety spec approved. | Separately specified apply tools that reuse reconciliation fingerprint/precondition checks. | Apply tests reject unsafe/stale/unplanned writes. | — |
| Step 17 | Multi-repo/fleet design | Step 14 | Single-repo workflows stable and a fleet use case exists. | Separate fleet reporting spec. | Approved if needed. | Optional fleet implementation |
| Step 18 | Remote transport design | Step 14 | Local use proves value; remote need exists. | Remote security/transport spec. | Approved threat model, auth, origin handling. | Optional remote implementation |

### MS-0 — Completed Repository Foundation

1. Complete Step 00 through Step 07.
2. Do not write MCP code.
3. Ensure standards graph and readiness report exist.
4. Ensure existing non-MCP workflows still pass.

### MS-1 — Reviewed Implementation Boundary

1. Complete Step 08 and Step 09.
2. Converge specifications and plan before implementation.
3. Freeze the service boundary, final protocol, stable SDK, exact dependency constraint, and target-client contract.

### MS-2 — Local Read-Only Server

1. Complete Step 10 through Step 12.
2. Implement only local read-only MCP server features.
3. Prove package resources and generic discovery/inspection tools from source and installed wheel.

### MS-3 — Validation and Planning

1. Complete Step 13 and Step 14.
2. Expose existing validation, drift, and authoritative reconciliation-preview semantics without writes or provider mutation-plan preview.
3. Ensure outputs are structured, deterministic, bounded, and content-safe.

### MS-4 — User Experience and Hardening

1. Document local MCP setup, resource URI rules, tool reference, and client-specific gaps.
2. Dogfood with fixtures, installed wheel, and an owner-approved consumer repository.
3. Run the complete repository gate and produce release-readiness evidence without publishing.

### MS-5 — Future Controlled Writes

1. Complete Step 15 and Step 16 only under a separate approved scope.
2. Reuse the control-plane executor; do not add an MCP writer.
3. Keep remote and GitHub writes out of scope.

### MS-6 — Optional Expansion

1. Step 17 may produce a separately approved fleet-reporting specification after single-repository workflows are stable.
2. Step 18 may produce a separately approved remote-transport specification only after local use proves value and a concrete remote need exists.
3. Neither optional design is part of the local read-only MCP release.

### Milestone Summary

| Milestone | Deliverable | Exit Criteria |
| --- | --- | --- |
| MS-0 Foundation | MCP-ready standards repository | `SPEC-MT01` passes readiness gate |
| MS-1 Reviewed boundary | Converged docs, ADRs, final protocol/SDK/client contract | No code starts with an unresolved dependency or client decision |
| MS-2 Read-only MCP | Local stdio resources and generic discovery/inspection tools | MCP reads exact payload resources and inspects repo fixtures from source and wheel |
| MS-3 Planning | Validation, drift, and reconciliation preview | Preview facts and findings are deterministic, structured, bounded, and non-mutating |
| MS-4 UX and hardening | Setup/reference docs and stable local candidate | Full gate, integration tests, client matrix, and dogfood pass |
| MS-5 Future writes | Separately governed plan-first apply tools | Separate safety approval and stale-plan tests pass |
| MS-6 Optional expansion | Separately governed fleet and/or remote designs | Step 17/18 need is demonstrated and each applicable specification is approved |

---

## 20. Success Evaluation

| Area | Target | Measurement |
| --- | --- | --- |
| Sequencing | No MCP implementation before readiness. | Step 07 complete before Step 10 starts. |
| Repository readiness | Standards are manifest-driven and graph-validated. | `SPEC-MT01` DoD passes. |
| MCP scalability | Adding a standard changes manifests/resources, not tools. | Fixture new standard test. |
| Safety | Writes are deferred and plan-first. | No write tools in read-only release; later apply rejects missing/stale plan. |
| Context efficiency | Agents lazy-load standard content. | Read one resource/summary without reading all standards. |
| Non-MCP compatibility | Existing docs/CLI/CI still work. | Existing test/check gate passes. |
| Operational usefulness | MCP helps inspect/adopt/validate standards in real repo. | Dogfood consumer repo evaluation. |

---

## 21. Open Questions and Decisions

| ID | Question | Current Assumption | Blocking? | Owner | Needed By | Status |
| --- | --- | --- | --- | --- | --- | --- |
| OQ-001 | Which final MCP protocol revision and stable Python SDK release should implementation pin? | On 2026-07-24, `2025-11-25` and SDK v1 are stable while the breaking `2026-07-28` protocol and SDK v2 are pre-release. Recheck after final publication and prefer an exact stable, conformance-tested combination. | Yes | Owner / MCP implementer | Step 09 | Open |
| OQ-002 | What exact version-qualified resource URI grammar should be frozen? | Derive it from Catalog 5 standard ID, exact payload version, and declared resource ID; record canonicalization and compatibility in the Step 09 ADR. | Yes | MCP implementer | Step 09 | Open |
| OQ-003 | Should MCP use package-bundled standards, live repo checkout, or both? | Installed wheel data is the production authority. Source checkout is a development/test mode and must produce equivalent exposed facts through an explicit injected repository service. | No | MCP implementer | Step 09 | Resolved |
| OQ-004 | Should controlled writes ever call GitHub directly? | No for v1; local repo writes first. | No | Standards owner | Step 15 | Open |
| OQ-005 | How should MCP clients surface approval for apply tools? | Server enforces plan identity; client UX varies. | No | MCP implementer | Step 15 | Open |
| OQ-006 | Should semantic review be an MCP prompt or tool? | Expose the declared provider only when the selected client surface can preserve its user-controlled semantics; otherwise omit it from v1 rather than reclassifying it as a model-controlled tool. | No | Standards owner | Step 11 | Open |
| OQ-007 | When is remote MCP justified? | Only after local server has recurring use and a concrete remote use case. | No | Standards owner | Step 18 | Open |

---

## Deviations Log

| ID      | Spec Reference | Deviation          | Reason         | Approved? |
| ------- | -------------- | ------------------ | -------------- | --------- |
| DEV-001 | N/A            | No deviations yet. | Initial draft. | Pending   |

---

## References

### Standards

- Project Specification Standard — `standards/project-spec/README.md`.
- Full Project Specification Template — `standards/project-spec/templates/spec-full-template.md`.
- Meta-repository MCP Readiness Preparation Spec — `SPEC-MT01`.
- Current package and control-plane source — `src/project_standards/package_contract/` and `src/project_standards/control_plane/`.
- MCP Specification 2025-11-25 — latest stable protocol on 2026-07-24.
- MCP 2026-07-28 release candidate — breaking next revision scheduled for final publication on 2026-07-28.
- MCP Python SDK main/v1 documentation — v1 is stable and v2 is pre-release on 2026-07-24; Step 09 rechecks the exact implementation target.
- Project Standards MCP Specification Reference Pack — supporting source register and reference summaries.

### Project References

- `docs/adr/` — ADRs created by Step 01/Step 09/Step 15.
- `docs/specs/` — durable location for maintained Project Specification documents.
- `.standards/config.toml` — current repository package-selection and configured-spec authority.
- `src/project_standards/package_contract/` — source-repository package discovery, graph, resource, provider, and catalog contracts.
- `src/project_standards/control_plane/` — installed-distribution, consumer state, provider, reconciliation-plan, finding, and executor boundaries.

---

## Appendix A: ID Conventions

| Prefix | Meaning                     | Defined In     |
| ------ | --------------------------- | -------------- |
| `G-`   | Goal                        | §4             |
| `NG-`  | Non-goal (never)            | §2.2           |
| `WH-`  | Won't have in v1 (deferred) | §2.3           |
| `A-`   | Assumption                  | §3.3           |
| `C-`   | Constraint                  | §3.4           |
| `FR-`  | Functional requirement      | §7.1           |
| `NFR-` | Non-functional requirement  | §7.2           |
| `IR-`  | Interface requirement       | §7.3           |
| `DR-`  | Data requirement            | §7.4           |
| `D-`   | Design decision             | §8.3           |
| `AW-`  | Alternate workflow          | §10.2          |
| `EC-`  | Edge case                   | §10.3          |
| `ERR-` | Error-handling requirement  | §12.1          |
| `R-`   | Risk                        | §15            |
| `MS-`  | Milestone                   | §19            |
| `OQ-`  | Open question               | §21            |
| `DEV-` | Deviation                   | Deviations Log |

Priority values (`Must/Should/Could`) are column values, not ID prefixes.

---

## Appendix B: Agent Implementation Contract

### B.1 Implementation Rules

The implementer shall:

- Read this roadmap, `SPEC-MT01`, and relevant ADRs before starting any phase.
- Do phases in order unless an approved `DEV-` row permits reordering.
- Treat completed Step 07 plus the Step 08-09 review and dependency gates as hard prerequisites to MCP implementation.
- Treat Step 15 as a hard gate before controlled writes.
- Record phase completion evidence in §17.3 or a linked completion report.
- Keep tool additions generic and justify any new top-level MCP tool through ADR/OQ.
- Preserve non-MCP workflows and tests throughout.

### B.2 Prohibited Behaviors

The implementer shall not:

- Start MCP server code before the refreshed specifications, plan, MCP ADRs, and dependency/client gate pass.
- Add per-standard MCP tools by default.
- Add remote transport before local stdio proof and remote security spec.
- Add write tools before planning tools and safety ADR.
- Store standards policy only in MCP server code.
- Bypass existing CLI/CI to make MCP tests pass.
- Reintroduce legacy V1 manifests, `.project-standards.yml`, copy-adopt, or package-specific provenance as current authorities.

### B.3 Required Completion Report (verification gate)

At completion of each phase, provide:

- Step label and summary.
- Deliverables completed.
- Requirements/milestones satisfied.
- Tests and commands run.
- ADRs/specs updated.
- Deviations and open questions.
- Whether the next phase is unblocked.

### B.4 Session Handoff

For multi-session work, record current step, next blocked/unblocked phase, unresolved `OQ-`/`DEV-` items, failing checks, and the next required gate in repository handoff docs.

---

## Appendix C: Optional Modules

### C.1 External Data Integration

No external data integration in early phases. Future GitHub/fleet integration must be specified separately.

### C.2 Scheduled Work, Throttling, and Circuit Breaker

No scheduled work for local v1. Remote/fleet phases may add polling, but require a separate spec.

### C.3 Identity / Entity Resolution

Relevant identities:

1. Standard IDs from manifests.
2. Resource URIs from resource descriptors.
3. Consumer repo roots from client roots or explicit arguments.
4. Plan IDs/hashes for controlled writes.

Ambiguous identities must fail closed.

### C.4 Scoring / Ranking / Decision Logic

No ranking in v1. Future standards relevance ranking should be derived from capabilities, repo inspection, and resource annotations, but should not hide deterministic applicability results.

### C.5 Relational Schema Examples

No database in v1.

---

## Appendix D: Tailoring Guide

This is a Full spec because the roadmap spans repository governance, standards metadata, validation architecture, ADRs, future MCP server design, safety gates, and multi-phase sequencing. Smaller profiles would under-specify dependencies and gates.
