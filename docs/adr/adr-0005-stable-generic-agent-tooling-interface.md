---
schema_version: '1.1'
id: 'adr-0005-project-standards-stable-generic-agent-tooling-interface'
title: 'ADR 0005: Stable Generic Agent and Tooling Interface'
description: 'Records the decision to keep future agent and MCP tools generic over standard id and operation rather than adding a tool per standard.'
doc_type: 'adr'
status: 'active'
created: '2026-07-07'
updated: '2026-08-09'
reviewed: '2026-08-09'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'standards-platform'
  - 'meta-repo'
  - 'tooling-interface'
aliases:
  - 'stable-generic-agent-tooling-interface'
related:
  - 'docs/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md'
  - 'docs/adr/adr-0006-standard-provider-plugin-model.md'
  - 'docs/adr/adr-0010-standard-resource-uris-and-index.md'
  - 'docs/adr/adr-0012-mcp-readiness-before-server-implementation.md'
  - 'docs/adr/adr-0021-standard-packaged-skill-installation-methodology.md'
  - 'docs/adr/adr-0022-standard-packaged-hook-installation-methodology.md'
  - 'docs/adr/adr-0025-mcp-service-and-sdk-boundary.md'
  - 'docs/adr/adr-0026-mcp-local-read-only-transport.md'
supersedes: []
superseded_by: null
source: []
confidence: 'high'
visibility: 'internal'
license: null
project:
  decision_makers:
    - 'chris'
  consulted: []
  informed: []
  amends: []
  amended_by: []
---

# ADR 0005: Stable Generic Agent and Tooling Interface

MADR status: **accepted**. Records decision D-005 of [SPEC-MT01](../specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md).

> **Amended 2026-08-09 (ADR 1.4 conformance assessment of 2026-08-05, findings §4 and C4).** The outcome now states the governed population, the applicability condition, and the axis this record constrains — growth of the tool surface **per standard** — and excludes the separate question of one tool per provider operation, which [ADR 0026](adr-0026-mcp-local-read-only-transport.md) decided for MCP v1. The rejection of a tool per standard is unchanged.

## Context and Problem Statement

As the number of standards grows, future agent and MCP tooling needs a way to expose operations over standards without the tool surface growing in lockstep with the standard count. Should future agent/MCP tools be generic over standard identity and operation, or should each standard get its own dedicated tool?

## Considered Options

- **Keep future agent/MCP tools generic over `standard_id` and operation** — a stable, small set of tools parameterized by which standard and which operation to perform.
- **Add a new tool for every standard** — give each standard its own dedicated agent/MCP tool.

## Decision Outcome

Chosen option: **keep future agent/MCP tools generic over `standard_id` and operation**, because per-standard tools do not scale and increase context and tool-surface clutter. Adding a new tool for every standard was rejected outright: the tool surface would grow linearly with the number of standards, wasting context and making tool selection harder for agents.

This decision governs how the agent- and MCP-facing tool surface scales with the size of the standard catalog, and applies whenever a tool is added to that surface. Within that population, a tool takes the standard as a parameter, so the tool count stays fixed as the catalog grows. The axis this record constrains is growth **per standard**.

It does not govern growth per provider operation, which is a different axis: a fixed set of specialized tools whose count does not depend on the standard count satisfies this decision, and declining a generic provider-dispatch tool is not a departure from it. [ADR 0026](adr-0026-mcp-local-read-only-transport.md) fixed the MCP v1 registry at six tools on exactly that reading, and its `standards_list` and `standard_read` take the standard and version as parameters, which is the property this record protects. This decision also does not govern which operations are exposed, the transport, the execution model, or the resource URI grammar. A tool decision made on the per-operation axis is outside this record and requires no exception to it.

### Consequences

- Good, because the tool surface stays stable regardless of how many standards exist.
- Good, because agents spend less context enumerating and selecting among tools.
- Bad, because generic tools must carry enough parameterization (standard id, operation) to cover every standard's needs, which can push complexity into tool arguments.
- Neutral, because this constrains how the provider plugin model ([ADR 0006](adr-0006-standard-provider-plugin-model.md)) and resource URIs ([ADR 0010](adr-0010-standard-resource-uris-and-index.md)) must be shaped to stay generic-tool-compatible.
