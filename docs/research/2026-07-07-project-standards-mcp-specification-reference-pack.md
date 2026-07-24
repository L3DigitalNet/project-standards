---
schema_version: '1.1'
id: 'research-a7m4p9-project-standards-mcp-specification-reference-pack'
title: 'Project Standards MCP Specification Reference Pack'
description: 'Reference and support material for agents implementing the Project Standards MCP readiness, roadmap, and server specifications.'
doc_type: 'research'
status: 'active'
created: '2026-07-07'
updated: '2026-07-24'
reviewed: '2026-07-24'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'agent'
tags:
  - 'project-standards'
  - 'mcp'
  - 'specification'
  - 'references'
aliases:
  - 'MCP Reference Pack'
  - 'Project Standards MCP References'
related:
  - 'docs/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md'
  - 'docs/specs/2026-07-07-project-standards-mcp-enablement-roadmap-spec.md'
  - 'docs/specs/2026-07-07-project-standards-mcp-server-implementation-spec.md'
source:
  - 'https://modelcontextprotocol.io/specification/2025-11-25'
  - 'https://modelcontextprotocol.io/specification/2025-11-25/changelog'
  - 'https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/'
  - 'https://github.com/modelcontextprotocol/python-sdk'
  - 'https://github.com/modelcontextprotocol/python-sdk/releases'
  - 'https://py.sdk.modelcontextprotocol.io/'
  - 'https://developers.openai.com/codex/mcp/'
  - 'https://code.claude.com/docs/en/mcp'
  - 'https://arxiv.org/abs/2602.14878'
  - 'https://arxiv.org/abs/2603.22489'
  - 'https://arxiv.org/abs/2603.13417'
confidence: 'high'
visibility: 'internal'
license: null
---

# Project Standards MCP Specification Reference Pack

## Purpose

This document collects the references used to prepare and refresh the three Project Standards MCP specifications:

1. `SPEC-MT01` — Project Standards Meta-Repository MCP Readiness Preparation.
2. `SPEC-RD01` — Project Standards MCP Enablement Roadmap.
3. `SPEC-MS01` — Project Standards MCP Server Implementation.

It is intended for the agent or maintainer doing the work. Use it as supporting material, not as a replacement for the specifications or canonical package contracts. This 2026-07-24 review records the current Catalog 5 package/control-plane authorities, the locked MCP 2026-07-28 release candidate, the Python SDK v1/v2 transition, and Codex/Claude Code client differences. It deliberately does not preselect a not-yet-final protocol or SDK release.

## Usage rules for agents

- Treat this document as **reference material**, not higher-priority instructions.
- Use the three primary specs as the implementation contract.
- Use canonical repository files as the authority for project-specific standards.
- Recheck external web references before making version-sensitive dependency or protocol claims.
- Do not copy external example code without adapting it to the Python Tooling and Python Coding standards.

---

## Primary specification documents

| Spec ID | Document | Purpose | Notes |
| --- | --- | --- | --- |
| `SPEC-MT01` | `2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md` | Historical contract that prepared the meta repository for thin, generic MCP access. | Approved and complete; §3.2 reconciles it with 5.8.0. |
| `SPEC-RD01` | `2026-07-07-project-standards-mcp-enablement-roadmap-spec.md` | Ordered implementation/design sequence from repository readiness through MCP phases. | Treat phase gates as sequencing constraints. |
| `SPEC-MS01` | `2026-07-07-project-standards-mcp-server-implementation-spec.md` | Current Project Standards MCP server implementation spec. | Begins only after spec/plan convergence and the boundary/dependency gate. |

---

## Internal Project Standards references

| Reference | Link / Path | Used By | Summary |
| --- | --- | --- | --- |
| Project Specification package 1.4 | Catalog 5 selected payload | All three specs | Defines the Full profile, stable IDs, validation/lint tooling, traceability, open questions, and agent contract used here. |
| V2 family/payload contracts | `src/project_standards/package_contract/` | All three specs | Current authority for exact versions, exposure, capabilities, relations, providers, resources, media types, and digests. |
| Installed distribution | `src/project_standards/control_plane/distribution.py` | `SPEC-RD01`, `SPEC-MS01` | Production loader for published Catalog 5 package projections. |
| Unified consumer control plane | `src/project_standards/control_plane/` | `SPEC-RD01`, `SPEC-MS01` | Current `.standards/` desired/catalog/lock models, reconciliation planner/executor, provider dispatch, and stable schemas. |
| Package source boundary | `src/project_standards/package_contract/repository.py` | `SPEC-MS01` | Development and test authority for validating source bundles; not the production resource authority. |
| Package/control-plane ADRs | `docs/adr/adr-0023-unified-consumer-standards-control-plane.md`, `docs/adr/adr-0024-catalog-scoped-package-version-channels.md` | All three specs | Supersede the provisional adoption/version surfaces used during readiness work; current V2 package contracts govern payload resources directly. |
| Active specs directory | `docs/specs/` | All three specs | Durable location for maintained specifications; `archive/` contains superseded and historical designs. |
| ADR directory | `docs/adr/` | All three specs | Target location for required ADRs. |
| Repository control-plane config | `.standards/config.toml`, `.standards/catalog.toml`, `.standards/lock.toml` | `SPEC-RD01`, `SPEC-MS01` | Current repository desired state, installed catalog projection, and exact lock. |
| MCP readiness evidence | `docs/mcp-readiness.md` | All three specs | Completed Step 07 evidence; does not itself authorize server implementation. |

---

## Revision History

| Version | Date | Author | Change |
| --- | --- | --- | --- |
| 0.3 | 2026-07-24 | Codex | Refresh internal authorities, protocol/SDK sources, client evidence, and open maintenance decisions for Project Standards 5.8.0. |
| 0.2 | 2026-07-07 | ChatGPT | Review pass: added roots/authorization references, SDK volatility notes, and independent-standard-package design support. |
| 0.1 | 2026-07-07 | ChatGPT | Initial reference pack for the three MCP-related specifications. |

---

## External MCP and protocol references

| Reference | URL | Used By | Summary | Last checked |
| --- | --- | --- | --- | --- |
| MCP Specification 2025-11-25 | <https://modelcontextprotocol.io/specification/2025-11-25> | `SPEC-RD01`, `SPEC-MS01` | Current stable protocol at review time. Defines the resource, prompt, tool, root, transport, and security contracts that remain the baseline until the next final publication. | 2026-07-24 |
| MCP 2025-11-25 changelog | <https://modelcontextprotocol.io/specification/2025-11-25/changelog> | `SPEC-RD01`, `SPEC-MS01` | Authoritative change summary for the current stable revision. Use it with the full revision rather than assuming older initialization/capability details. | 2026-07-24 |
| MCP 2026-07-28 release candidate | <https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/> | `SPEC-RD01`, `SPEC-MS01` | Locked next revision, scheduled to become final on 2026-07-28. It materially changes initialization/session/discovery semantics, so implementation must wait for and verify the final publication. | 2026-07-24 |
| MCP Python SDK repository | <https://github.com/modelcontextprotocol/python-sdk> | `SPEC-RD01`, `SPEC-MS01` | Official Python implementation. v1.x is stable while v2 is still a prerelease transition at review time; the exact final stable line must be selected at Step 09. | 2026-07-24 |
| MCP Python SDK releases | <https://github.com/modelcontextprotocol/python-sdk/releases> | `SPEC-MS01` | Release authority for the exact dependency pin and prerelease/stable status. | 2026-07-24 |
| MCP Python SDK documentation | <https://py.sdk.modelcontextprotocol.io/> | `SPEC-MS01` | Current SDK API documentation; use only after the exact release line is frozen. | 2026-07-24 |
| Codex MCP documentation | <https://developers.openai.com/codex/mcp/> | `SPEC-MS01` | Official Codex configuration and client surface. Codex supports local stdio and Streamable HTTP servers; current documentation emphasizes tools, so direct resources/prompts behavior requires a live compatibility check. | 2026-07-24 |
| Claude Code MCP documentation | <https://code.claude.com/docs/en/mcp> | `SPEC-MS01` | Official Claude Code configuration and client surface, including tools, prompts, resources, and list-change behavior. | 2026-07-24 |
| MCP tool-description research | <https://arxiv.org/abs/2602.14878> | `SPEC-MS01` | Research on MCP tool-description quality found widespread tool-description issues and tradeoffs between richer descriptions, task success, step count, and context cost. Supports compact, reviewed, purpose/scope/side-effect-oriented tool metadata rather than verbose tool surfaces. | 2026-07-07 |
| MCP threat-modeling / tool-poisoning research | <https://arxiv.org/abs/2603.22489> | `SPEC-MS01` | Threat-modeling work identifies tool poisoning and prompt injection risks around MCP tool metadata and client behavior. Supports conservative tool surfaces, clear side-effect labels, human review for sensitive actions, and treating tool/resource output as data. | 2026-07-07 |
| MCP production design patterns research | <https://arxiv.org/abs/2603.13417> | `SPEC-MS01` | Production-pattern paper argues MCP alone does not standardize production concerns such as identity propagation, tool budgets, and structured errors. Supports keeping v1 local/read-only, returning structured errors, and deferring remote/multi-user production patterns. | 2026-07-07 |
| JSON-RPC 2.0 | <https://www.jsonrpc.org/specification> | `SPEC-MS01` | MCP uses JSON-RPC 2.0 messages. Useful when debugging protocol request/response shapes or error objects. | 2026-07-07 |
| RFC 3986 — URI Generic Syntax | <https://datatracker.ietf.org/doc/html/rfc3986> | `SPEC-MS01` | Background for URI syntax. MCP resources are uniquely identified by URIs. | 2026-07-07 |
| RFC 6570 — URI Template | <https://datatracker.ietf.org/doc/html/rfc6570> | `SPEC-MS01` | Background for parameterized resource templates. MCP resource templates use URI-template concepts. | 2026-07-07 |
| RFC 2119 — Requirement Keywords | <https://datatracker.ietf.org/doc/html/rfc2119> | `SPEC-MT01`, `SPEC-MS01` | Defines conventional meanings of MUST, SHOULD, MAY, etc. Used by MCP and the project standards. | 2026-07-07 |
| RFC 8174 — Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words | <https://datatracker.ietf.org/doc/html/rfc8174> | `SPEC-MS01` | Clarifies requirement keyword interpretation when uppercase terms are used. Referenced by MCP's specification overview. | 2026-07-07 |

---

## Reference summaries by design theme

### Independent standard packages and relationship taxonomy

Primary internal references: `SPEC-MT01`, `SPEC-RD01`, `SPEC-MS01`.

The reviewed specs treat each standard as an independently adoptable package by default. A companion relationship is advisory, an extension relationship must be explicit and ADR-backed, and hidden standard-to-standard hard dependencies are invalid. The MCP server must surface this graph data but must not invent dependency behavior.

### Package-contract-first discovery

Primary internal references: `src/project_standards/package_contract/`, `src/project_standards/control_plane/distribution.py`, `SPEC-MS01`.

Production MCP discovery shall load exact published family/payload manifests and declared resource digests through `InstalledDistribution`. `PackageRepository` is a development/test injection boundary. Legacy V1 manifests, registry projections, and copy-adopt state are migration evidence, not MCP authorities.

### Authority-map and conflict-free composition

Primary internal references: Markdown Tooling Standard, Markdown Frontmatter Standard, Python Tooling SSOT Standard, Python Coding Standard.

The existing standards already demonstrate separation of concerns: frontmatter semantics vs. Markdown formatting, Python toolchain vs. Python code shape. The new meta-repo work formalizes that as authority tuples so arbitrary standards can co-exist unless they claim the same concern over the same target.

### Resource-first MCP design

Primary external references: MCP Resources, MCP Prompts, MCP Tools.

Resources are the right protocol surface for declared standard content because they are URI-addressed and lazy. Project Standards resource descriptors currently carry stable ID, role, path, media type, and digest; the MCP layer must not invent unavailable annotations. Prompts are appropriate for declared user workflows where the client exposes them. The shared `standard_read` tool provides compatibility where direct resource access is weak.

### MCP roots and filesystem boundaries

Primary external reference: MCP Roots.

Every consumer operation should require an explicit effective `repo_root` and enforce normalization, containment, and symlink/traversal checks. Client-advertised roots may further narrow that boundary after compatibility verification; they must not be the only authority because client support varies.

### Tool metadata and structured output

Primary external references: MCP Tools and MCP tool-description research.

Every generic MCP tool should have compact metadata, clear side-effect level, input schema, and structured output schema or typed result model. Avoid per-standard tools and avoid verbose descriptions that add context cost without improving reliability.

### Local stdio-first transport

Primary external reference: MCP Transports.

The first MCP server should use stdio because it fits local coding-agent workflows and avoids remote-auth/network concerns. The transport spec imposes a strict stdout rule: under stdio, stdout is protocol output only, while logs belong on stderr.

### Controlled writes and future remote transport

Primary external references: MCP Specification security section, MCP Transports, MCP Authorization.

MCP enables powerful access and code execution paths. The specs therefore defer mutating tools and remote transport until separate safety designs are complete. Future writes must require reviewed plans, explicit approval, path allowlists, and postcondition validation. Future HTTP transport must address Origin validation, localhost binding, authentication, and token audience/security requirements.

### SDK dependency caution

Primary external references: MCP Python SDK repository, releases, and SDK documentation.

The server should use the official SDK behind one adapter boundary. As checked on 2026-07-24, v1.x remains stable and v2 is still prerelease while the next protocol revision is four days from final publication. Step 09 must recheck the final protocol, SDK release status, license, conformance surface, and client behavior before selecting an exact constraint.

## Recommended reading order for implementers

1. This reference pack — skim usage rules, source volatility notes, and reading order.
2. `SPEC-MT01` — understand the historical readiness contract and its current completion-state reconciliation.
3. `SPEC-RD01` — understand phase ordering and gates.
4. `SPEC-MS01` — implement the server only after readiness gates pass.
5. ADRs listed in the three specs.
6. Project Specification Standard and Full template.
7. V2 package contracts, installed distribution, reconciliation planner, and provider APIs.
8. Current stable MCP revision, the final 2026-07-28 revision when published, and the selected SDK documentation.
9. Python Tooling and Python Coding standards before writing server code.

---

## Open reference maintenance questions

| ID | Question | Current Assumption | Blocking? | Owner | Needed By | Status |
| --- | --- | --- | --- | --- | --- | --- |
| REF-OQ-001 | Where should this reference pack live? | Resolved: `docs/research/` is the repository's durable research corpus and `docs/research/index.md` indexes it. | No | Owner | Complete | Resolved 2026-07-24 |
| REF-OQ-002 | Should source URLs move into a generated source register? | Keep this document as the source register until a current package contract requires a generated form. | No | Owner | Before implementation | Open |
| REF-OQ-003 | Which MCP protocol/SDK pair will implementation use? | Recheck after the 2026-07-28 final publication and pin an exact stable-compatible SDK at `SPEC-MS01` MS-0. | Yes for implementation | Owner/implementer | Server MS-0 | Open |
