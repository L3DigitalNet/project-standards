---
schema_version: '1.1'
id: 'adr-0005-project-standards-stable-generic-agent-tooling-interface'
title: 'ADR 0005: Stable Generic Agent and Tooling Interface'
description: 'Records the decision to keep future agent and MCP tools generic over standard id and operation rather than adding a tool per standard.'
doc_type: 'adr'
status: 'active'
created: '2026-07-07'
updated: '2026-07-09'
reviewed: '2026-07-07'
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
  - 'docs/adr/adr-0021-standard-packaged-skill-installation-methodology.md'
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
---

# ADR 0005: Stable Generic Agent and Tooling Interface

MADR status: **accepted**. Records decision D-005 of [SPEC-MT01](../specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md).

## Context and Problem Statement

As the number of standards grows, future agent and MCP tooling needs a way to expose operations over standards without the tool surface growing in lockstep with the standard count. Should future agent/MCP tools be generic over standard identity and operation, or should each standard get its own dedicated tool?

## Considered Options

- **Keep future agent/MCP tools generic over `standard_id` and operation** — a stable, small set of tools parameterized by which standard and which operation to perform.
- **Add a new tool for every standard** — give each standard its own dedicated agent/MCP tool.

## Decision Outcome

Chosen option: **keep future agent/MCP tools generic over `standard_id` and operation**, because per-standard tools do not scale and increase context and tool-surface clutter. Adding a new tool for every standard was rejected outright: the tool surface would grow linearly with the number of standards, wasting context and making tool selection harder for agents.

### Consequences

- Good, because the tool surface stays stable regardless of how many standards exist.
- Good, because agents spend less context enumerating and selecting among tools.
- Bad, because generic tools must carry enough parameterization (standard id, operation) to cover every standard's needs, which can push complexity into tool arguments.
- Neutral, because this constrains how the provider plugin model ([ADR 0006](adr-0006-standard-provider-plugin-model.md)) and resource URIs ([ADR 0010](adr-0010-standard-resource-uris-and-index.md)) must be shaped to stay generic-tool-compatible.
