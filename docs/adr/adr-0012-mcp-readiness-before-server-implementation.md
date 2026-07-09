---
schema_version: '1.1'
id: 'adr-0012-project-standards-mcp-readiness-before-server-implementation'
title: 'ADR 0012: MCP Readiness Before Server Implementation'
description: 'Records the decision to defer any MCP server implementation until the meta-repo readiness gate passes so the server stays thin and generic.'
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
  - 'mcp-readiness'
  - 'sequencing'
aliases:
  - 'mcp-readiness-before-server-implementation'
related:
  - 'docs/superpowers/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md'
  - 'docs/adr/adr-0002-manifest-first-standard-discovery.md'
  - 'docs/adr/adr-0005-stable-generic-agent-tooling-interface.md'
  - 'docs/adr/adr-0007-standard-graph-validation-gate.md'
  - 'docs/adr/adr-0013-independent-standard-packages-and-relationship-taxonomy.md'
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

# ADR 0012: MCP Readiness Before Server Implementation

MADR status: **accepted**. Records decision D-012 of [SPEC-MT01](../superpowers/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md).

## Context and Problem Statement

An MCP server exposing standards could be built now, but the repository's manifests, resource declarations, and validation gates are still being established. If the server is built before that metadata is complete, when should it be implemented relative to the rest of the meta-repo work?

## Considered Options

- **Defer MCP server implementation until the meta-repo readiness gate passes** — finish manifests, resource declarations, and graph validation first, then build the server as a thin consumer of that data.
- **Build MCP immediately and backfill the repository later** — implement the server now and retrofit missing repository metadata afterward.

## Decision Outcome

Chosen option: **defer MCP server implementation until the meta-repo readiness gate passes**, because building the server first would encode missing repository metadata directly into server code and make every new standard a server-maintenance event, undermining the manifest-first discovery ([ADR 0002](adr-0002-manifest-first-standard-discovery.md)) and stable tooling interface ([ADR 0005](adr-0005-stable-generic-agent-tooling-interface.md)) already established. Building MCP immediately and backfilling later was rejected because it inverts the dependency: the server should be a thin, generic consumer of repository data ([ADR 0013](adr-0013-independent-standard-packages-and-relationship-taxonomy.md)), not a place where repository gaps get patched over.

### Consequences

- Good, because the server, once built, stays thin and generic instead of hardcoding workarounds for incomplete repository metadata.
- Good, because it forces the readiness gate (manifests, resources, graph validation) to be genuinely complete before anything depends on it.
- Bad, because MCP-based access to standards is delayed until the readiness gate passes.
- Neutral, because this sequencing decision is itself validated by the graph validation gate in [ADR 0007](adr-0007-standard-graph-validation-gate.md).
