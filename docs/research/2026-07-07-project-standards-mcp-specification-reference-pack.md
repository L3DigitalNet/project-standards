---
schema_version: '1.1'
id: 'research-a7m4p9-project-standards-mcp-specification-reference-pack'
title: 'Project Standards MCP Specification Reference Pack'
description: 'Reference and support material for agents implementing the Project Standards MCP readiness, roadmap, and server specifications.'
doc_type: 'research'
status: 'draft'
created: '2026-07-07'
updated: '2026-07-07'
reviewed: '2026-07-07'
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
  - 'https://modelcontextprotocol.io/specification/2025-06-18'
  - 'https://modelcontextprotocol.io/specification/2025-06-18/basic/transports'
  - 'https://modelcontextprotocol.io/specification/2025-06-18/server/resources'
  - 'https://modelcontextprotocol.io/specification/2025-06-18/server/tools'
  - 'https://modelcontextprotocol.io/specification/2025-06-18/server/prompts'
  - 'https://modelcontextprotocol.io/specification/2025-06-18/client/roots'
  - 'https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization'
  - 'https://modelcontextprotocol.io/specification/2025-06-18/client/sampling'
  - 'https://modelcontextprotocol.io/specification/2025-06-18/client/elicitation'
  - 'https://github.com/modelcontextprotocol/python-sdk'
  - 'https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/v1.x/README.md'
  - 'https://arxiv.org/abs/2602.14878'
  - 'https://arxiv.org/abs/2603.22489'
  - 'https://arxiv.org/abs/2603.13417'
confidence: 'high'
visibility: 'internal'
license: null
---

# Project Standards MCP Specification Reference Pack

## Purpose

This document collects the references used to prepare the three Project Standards MCP specifications:

1. `SPEC-MT01` — Project Standards Meta-Repository MCP Readiness Preparation.
2. `SPEC-RD01` — Project Standards MCP Enablement Roadmap.
3. `SPEC-MS01` — Project Standards MCP Server Implementation.

It is intended for the agent or maintainer doing the work. Use it as supporting material, not as a replacement for the specifications or the canonical standards. This reviewed version also records evidence used to tighten the final pass: independent standard relationships, resource-first MCP design, structured tool outputs, tool metadata quality, SDK version caution, and MCP security boundaries.

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
| `SPEC-MT01` | `2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md` | Prepare the meta repository so MCP can be thin, manifest-driven, and scalable. | Must complete before server implementation. |
| `SPEC-RD01` | `2026-07-07-project-standards-mcp-enablement-roadmap-spec.md` | Ordered implementation/design sequence from repository readiness through MCP phases. | Treat phase gates as sequencing constraints. |
| `SPEC-MS01` | `2026-07-07-project-standards-mcp-server-implementation-spec.md` | Actual Project Standards MCP server implementation spec. | Begins only after readiness gates pass. |

---

## Internal Project Standards references

| Reference | Link / Path | Used By | Summary |
| --- | --- | --- | --- |
| Project Specification Standard | `standards/project-spec/README.md` | All three specs | Defines the tiered Light/Standard/Full spec format, stable numbering, typed IDs, agent contract, validation/lint/extract/next/new/upgrade tooling, and semantic review contract. |
| Full Project Specification Template | `standards/project-spec/templates/spec-full-template.md` | All three specs | Provides the structure used for these specs: frontmatter, requirements, design, testing, implementation plan, traceability, open questions, deviations log, and agent implementation contract. |
| Markdown Frontmatter Standard | `standards/markdown-frontmatter/README.md` | `SPEC-MT01`, reference pack | Defines portable YAML frontmatter for managed Markdown docs. This reference pack uses its schema and ID conventions. |
| Markdown Tooling Standard | `standards/markdown-tooling/README.md` | `SPEC-MT01`, `SPEC-MS01` | Defines Prettier/markdownlint/EditorConfig authority boundaries for Markdown and adjacent structured text. Supports the authority-map model by showing how tools can coexist without conflict. |
| Python Tooling SSOT Standard | `standards/python-tooling/README.md` | `SPEC-MT01`, `SPEC-MS01` | Defines the repository's Python toolchain: uv, Ruff, BasedPyright, pytest, coverage, pip-audit, VS Code/editor rules, agent instruction interface, and verification gate. |
| Python Coding Standard | `standards/python-coding/README.md` | `SPEC-MT01`, `SPEC-MS01` | Defines code-shape, error handling, testing, dependencies, subprocess, filesystem, security, and agent trust-boundary rules for Python implementation. |
| ADR Standard | `standards/adr/README.md` | `SPEC-MT01`, `SPEC-RD01`, `SPEC-MS01` | Governs Architecture Decision Records. The specs require ADRs to lock in manifest-first discovery, authority mapping, generic MCP tools, transport decisions, and write/remote deferrals. |
| Existing package internals | `src/project_standards/README.md` | `SPEC-MT01`, `SPEC-RD01`, `SPEC-MS01` | Documents the current CLI surface, validators, fixers, adopt engine, registry, configuration file, and package layout. |
| Existing registry | `src/project_standards/schemas/registry.json` | `SPEC-MT01`, `SPEC-MS01` | Current machine-readable standard/version registry. The readiness spec expands this into richer graph metadata. |
| Adopt manifest loader | `src/project_standards/adopt/manifest.py` | `SPEC-MT01`, `SPEC-MS01` | Current pattern for discovering adoptable standards from bundle manifests and validating artifact declarations. Provides the model for manifest-first MCP expansion. |
| Adopt engine | `src/project_standards/adopt/engine.py` | `SPEC-MT01`, `SPEC-MS01` | Current generic planner/executor for adoption artifacts. Its dry-run, deduplication, collision detection, fragments, and atomic writes inform the MCP planning model. |
| Existing specs directory | `docs/specs/archive/` | All three specs | Likely migration target for the three primary specs if this remains the repository's spec convention. |
| ADR directory | `docs/adr/` | All three specs | Target location for required ADRs. |
| Repository validation config | `.project-standards.yml` | `SPEC-MT01`, `SPEC-RD01`, `SPEC-MS01` | Governs managed docs/spec paths and validation behavior. Must be updated if new specs/resources require inclusion/exclusion changes. |
| Local check script | `scripts/check.py` | `SPEC-MT01`, `SPEC-RD01`, `SPEC-MS01` | Candidate integration point for local verification gates, if present and current. |

---

## Revision History

| Version | Date | Author | Change |
| --- | --- | --- | --- |
| 0.2 | 2026-07-07 | ChatGPT | Review pass: added roots/authorization references, SDK volatility notes, and independent-standard-package design support. |
| 0.1 | 2026-07-07 | ChatGPT | Initial reference pack for the three MCP-related specifications. |

---

## External MCP and protocol references

| Reference | URL | Used By | Summary | Last checked |
| --- | --- | --- | --- | --- |
| MCP Specification 2025-06-18 | <https://modelcontextprotocol.io/specification/2025-06-18> | `SPEC-RD01`, `SPEC-MS01` | Authoritative protocol overview. Defines MCP as an open protocol for integrating LLM applications with external data/tools, uses JSON-RPC 2.0, and distinguishes resources, prompts, and tools. Includes security/trust principles: user consent, data privacy, tool safety, and sampling controls. | 2026-07-07 |
| MCP Transports | <https://modelcontextprotocol.io/specification/2025-06-18/basic/transports> | `SPEC-RD01`, `SPEC-MS01` | Defines stdio and Streamable HTTP. stdio launches the server as a subprocess and requires stdout to contain only valid MCP messages. Streamable HTTP requires additional security design such as Origin validation, localhost binding for local servers, and authentication. | 2026-07-07 |
| MCP Resources | <https://modelcontextprotocol.io/specification/2025-06-18/server/resources> | `SPEC-MT01`, `SPEC-RD01`, `SPEC-MS01` | Defines resources as URI-identified context/data exposed by servers, including resource templates, list/read operations, list-changed notifications, subscriptions, annotations, and common URI schemes. Supports lazy standard-resource design and resource annotation metadata. | 2026-07-07 |
| MCP Tools | <https://modelcontextprotocol.io/specification/2025-06-18/server/tools> | `SPEC-RD01`, `SPEC-MS01` | Defines tools as model-controlled functions with names, descriptions, input schemas, results, structured content, output schemas, and list/call protocol messages. Supports keeping tools few, generic, structured, and reviewed for safety. | 2026-07-07 |
| MCP Prompts | <https://modelcontextprotocol.io/specification/2025-06-18/server/prompts> | `SPEC-MT01`, `SPEC-MS01` | Defines prompts as user-controlled reusable templates/workflows that clients can list and retrieve with arguments. Supports standard-provided adoption/review/exception prompt resources. | 2026-07-07 |
| MCP Roots | <https://modelcontextprotocol.io/specification/2025-06-18/client/roots> | `SPEC-MS01` | Defines client-provided filesystem roots, root list changes, and security expectations for validating root URIs and path boundaries. Supports root-aware repo inspection. | 2026-07-07 |
| MCP Authorization | <https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization> | Future remote phase | Defines authorization guidance for HTTP transports and states that stdio implementations should not follow the HTTP authorization spec. Included to support remote-transport deferral and future threat modeling. | 2026-07-07 |
| MCP Sampling | <https://modelcontextprotocol.io/specification/2025-06-18/client/sampling> | `SPEC-MS01` future work only | Defines server-initiated LLM sampling through clients, including human-in-the-loop expectations and client capability declaration. The server spec excludes sampling from v1 because standards discovery does not need nested LLM calls. | 2026-07-07 |
| MCP Elicitation | <https://modelcontextprotocol.io/specification/2025-06-18/client/elicitation> | `SPEC-MS01` future work only | Defines server-initiated requests for additional user information through clients, with restrictions on sensitive information and schema-limited structured responses. The server spec excludes elicitation from v1 to keep the tool surface deterministic. | 2026-07-07 |
| MCP Python SDK — v1 stable branch | <https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/v1.x/README.md> | `SPEC-RD01`, `SPEC-MS01` | Official Python implementation. The v1 branch documents v1.x as the stable release line, recommends v1 for production, and advises package constraints such as `mcp>=1.27,<2` before stable v2 lands. Supports the server spec's default dependency assumption. | 2026-07-07 |
| MCP Python SDK — main/v2 pre-release README | <https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/README.md> | `SPEC-MS01` | Main README documents the v2 SDK line as alpha/beta pre-release, warns not to use v2 in production, and requires exact pins if testing it. Supports the SDK adapter boundary and implementation-time recheck. | 2026-07-07 |
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

### Manifest-first standard discovery

Primary internal references: `src/project_standards/adopt/manifest.py`, `src/project_standards/schemas/registry.json`, `SPEC-MT01`.

The existing repository already discovers adoptable standards through manifests rather than hardcoded lists. The MCP-ready design extends that idea from adoption artifacts to full standard metadata: resources, authorities, capabilities, relationships, providers, prompts, and validation behavior.

### Authority-map and conflict-free composition

Primary internal references: Markdown Tooling Standard, Markdown Frontmatter Standard, Python Tooling SSOT Standard, Python Coding Standard.

The existing standards already demonstrate separation of concerns: frontmatter semantics vs. Markdown formatting, Python toolchain vs. Python code shape. The new meta-repo work formalizes that as authority tuples so arbitrary standards can co-exist unless they claim the same concern over the same target.

### Resource-first MCP design

Primary external references: MCP Resources, MCP Prompts, MCP Tools.

Resources are the right place for canonical standard content because they are URI-addressed context and can be lazy-loaded. Resource annotations such as audience, priority, and last-modified metadata can help clients prioritize content. Prompts are appropriate for user-selected workflows. Tools are model-controlled functions, so the tool surface should stay small, stable, generic, and reviewed for description quality.

### MCP roots and filesystem boundaries

Primary external reference: MCP Roots.

The server implementation should prefer MCP roots when clients support them. When roots are unavailable, tools must require an explicit `repo_root` and enforce normalization, containment, and symlink/traversal checks before reading consumer repositories.

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

Primary external references: MCP Python SDK v1 branch and main/v2 README.

The server should prefer the official SDK but keep it behind an adapter boundary. As checked, the SDK v1 branch remains the production/stable line and recommends an upper bound such as `<2`; the main/v2 README describes v2 as pre-release and warns about breaking changes. The exact dependency version must be rechecked and pinned during implementation.

## Recommended reading order for implementers

1. This reference pack — skim usage rules, source volatility notes, and reading order.
2. `SPEC-MT01` — understand repository readiness, graph contracts, and independent-standard-package rules.
3. `SPEC-RD01` — understand phase ordering and gates.
4. `SPEC-MS01` — implement the server only after readiness gates pass.
5. ADRs listed in the three specs.
6. Project Specification Standard and Full template.
7. Existing package internals and adopt engine.
8. MCP Specification overview, Resources, Tools, Prompts, Roots, Transports, and Authorization.
9. Python Tooling and Python Coding standards before writing server code.

---

## Open reference maintenance questions

| ID | Question | Current Assumption | Blocking? | Owner | Needed By | Status |
| --- | --- | --- | --- | --- | --- | --- |
| REF-OQ-001 | Where should this reference pack live after migration? | Resolved (2026-07-07): ingested to `docs/research/`, beside the three specs under `docs/superpowers/`. `docs/research/` was rejected — its `index.md` is qdev-generated ("do not edit by hand"), so a hand-authored pack there would drift. Frontmatter conforms to the Markdown Frontmatter Standard but the path is not in the `.project-standards.yml` frontmatter include globs, so it is compatible-but-unenforced. | No | Owner | Before merge | Resolved |
| REF-OQ-002 | Should source URLs be mirrored into a formal source register table for validator support? | Keep this document as a Markdown source register until a resource-doc standard exists. | No | Owner | Before final review | Open |
| REF-OQ-003 | Which MCP SDK version will implementation use? | Recheck during `SPEC-MS01` MS-0 and pin exact version. | Yes for implementation | Owner/implementer | Server MS-0 | Open |
