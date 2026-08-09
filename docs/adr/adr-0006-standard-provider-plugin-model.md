---
schema_version: '1.1'
id: 'adr-0006-project-standards-standard-provider-plugin-model'
title: 'ADR 0006: Standard Provider and Plugin Model'
description: 'Records the decision to bind generic operations to standards through a provider registry instead of central switch statements.'
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
  - 'providers'
aliases:
  - 'standard-provider-plugin-model'
related:
  - 'docs/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md'
  - 'docs/adr/adr-0005-stable-generic-agent-tooling-interface.md'
  - 'docs/adr/adr-0007-standard-graph-validation-gate.md'
  - 'docs/adr/adr-0017-unified-standard-adoption-methodology.md'
  - 'docs/adr/adr-0023-unified-consumer-standards-control-plane.md'
  - 'docs/adr/adr-0025-project-standards-mcp-service-and-sdk-boundary.md'
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
  amended_by:
    - 'adr-0023-project-standards-unified-consumer-standards-control-plane'
---

# ADR 0006: Standard Provider and Plugin Model

MADR status: **accepted**. Records decision D-006 of [SPEC-MT01](../specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md).

> **Amended by ADR 0023 (2026-07-10).** The principle this record decided is unchanged and still in force: standard-specific behavior must be pluggable, and adding a standard must not touch shared dispatch code. The **mechanism** named in the outcome is replaced. There is no per-capability registry and no registration step. Only immutable, catalog-trusted package payloads may declare providers, and `invoke_provider` resolves one from the selected payload's manifest by provider id and operation. The five capabilities this record named have become the declared operation contract, which the control plane consumes generically with no package-ID branches. `AdapterRegistry` in the control plane serves ADR 0023's semantic-composition model and is not the registry this record chose.
>
> **Amended 2026-08-09 (ADR 1.4 conformance assessment of 2026-08-05, findings §4, C2, and B6).** The outcome now states the governed population, the applicability condition, and the exclusions, and the explicit opt-out requirement moves out of `### Consequences` into the bounded outcome where policy belongs. Nothing this record decided changes.

## Context and Problem Statement

Generic operations such as validation, fixing, drift checking, ID generation, and extraction all need standard-specific behavior, but that behavior cannot live in one growing block of conditional logic if the standard count is to scale without touching tool code for every addition. How should generic operations bind to the standard-specific logic each standard requires?

## Considered Options

- **Provider registries** — a registry per capability (validators, fixers, drift checks, ID generation, extraction) that standards register implementations into, looked up by standard identity at call time.
- **Hardcode each standard in the CLI or MCP layer** — central switch statements or if/else chains dispatching on standard name.

## Decision Outcome

Chosen option: **use provider registries for validators, fixers, drift checks, ID generation, and extraction**. Standard-specific behavior must be pluggable so that adding a standard is a registration, not a change to shared dispatch code; this also gives the stable tooling interface ([ADR 0005](adr-0005-stable-generic-agent-tooling-interface.md)) and the graph validation gate ([ADR 0007](adr-0007-standard-graph-validation-gate.md)) a consistent seam to call through. Hardcoding each standard in the CLI or MCP layer was rejected because central switch statements grow linearly with the standard count and become a shared bottleneck and merge-conflict point.

This decision governs how a generic operation binds to the standard-specific behavior it needs, and applies whenever a standard package supplies behavior for such an operation. Within that population, a standard that supplies no implementation for an operation must declare that explicitly rather than silently no-op, and shared dispatch code must not gain a branch per standard.

It does not govern which operations exist, how a package's payload is selected or trusted, or where provider code executes. [ADR 0023](adr-0023-unified-consumer-standards-control-plane.md) governs payload trust and the declaration plane, and [ADR 0025](adr-0025-project-standards-mcp-service-and-sdk-boundary.md) governs execution isolation under the MCP server. A change to the resolution mechanism that keeps behavior out of shared dispatch code is within this decision's principle and requires no exception to it.

### Consequences

- Good, because adding or updating a standard's behavior is a localized, additive change to its own provider implementation.
- Good, because generic operations (CLI commands, MCP tools) stay stable and standard-agnostic, per [ADR 0005](adr-0005-stable-generic-agent-tooling-interface.md).
- Bad, because the resolution mechanism itself becomes infrastructure that must be maintained and kept consistent across capabilities.
- Neutral, because a standard's silence about a capability stops being ambiguous: absence is declared rather than inferred.
