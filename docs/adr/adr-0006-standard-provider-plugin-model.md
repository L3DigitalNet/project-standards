---
schema_version: '1.1'
id: 'adr-0006-project-standards-standard-provider-plugin-model'
title: 'ADR 0006: Standard Provider and Plugin Model'
description: 'Records the decision to bind generic operations to standards through a provider registry instead of central switch statements.'
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
  - 'providers'
aliases:
  - 'standard-provider-plugin-model'
related:
  - 'docs/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md'
  - 'docs/adr/adr-0005-stable-generic-agent-tooling-interface.md'
  - 'docs/adr/adr-0007-standard-graph-validation-gate.md'
  - 'docs/adr/adr-0017-unified-standard-adoption-methodology.md'
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

# ADR 0006: Standard Provider and Plugin Model

MADR status: **accepted**. Records decision D-006 of [SPEC-MT01](../specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md).

## Context and Problem Statement

Generic operations such as validation, fixing, drift checking, ID generation, and extraction all need standard-specific behavior, but that behavior cannot live in one growing block of conditional logic if the standard count is to scale without touching tool code for every addition. How should generic operations bind to the standard-specific logic each standard requires?

## Considered Options

- **Provider registries** — a registry per capability (validators, fixers, drift checks, ID generation, extraction) that standards register implementations into, looked up by standard identity at call time.
- **Hardcode each standard in the CLI or MCP layer** — central switch statements or if/else chains dispatching on standard name.

## Decision Outcome

Chosen option: **use provider registries for validators, fixers, drift checks, ID generation, and extraction**. Standard-specific behavior must be pluggable so that adding a standard is a registration, not a change to shared dispatch code; this also gives the stable tooling interface ([ADR 0005](adr-0005-stable-generic-agent-tooling-interface.md)) and the graph validation gate ([ADR 0007](adr-0007-standard-graph-validation-gate.md)) a consistent seam to call through. Hardcoding each standard in the CLI or MCP layer was rejected because central switch statements grow linearly with the standard count and become a shared bottleneck and merge-conflict point.

### Consequences

- Good, because adding or updating a standard's behavior is a localized, additive change to its own provider implementation.
- Good, because generic operations (CLI commands, MCP tools) stay stable and standard-agnostic, per [ADR 0005](adr-0005-stable-generic-agent-tooling-interface.md).
- Bad, because the registry itself becomes infrastructure that must be maintained and kept consistent across capabilities.
- Neutral, because standards without a provider for a given capability must explicitly opt out rather than silently no-op.
