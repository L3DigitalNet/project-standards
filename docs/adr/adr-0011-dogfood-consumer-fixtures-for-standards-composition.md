---
schema_version: '1.1'
id: 'adr-0011-project-standards-dogfood-consumer-fixtures-for-standards-composition'
title: 'ADR 0011: Dogfood Consumer Fixtures for Standards Composition'
description: 'Records the decision to require dogfood consumer-repo fixtures that exercise standard composition, not just per-standard unit tests.'
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
  - 'testing'
  - 'fixtures'
aliases:
  - 'dogfood-consumer-fixtures-for-standards-composition'
related:
  - 'docs/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md'
  - 'docs/adr/adr-0004-authority-map-and-conflict-free-composition.md'
  - 'docs/adr/adr-0007-standard-graph-validation-gate.md'
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

# ADR 0011: Dogfood Consumer Fixtures for Standards Composition

MADR status: **accepted**. Records decision D-011 of [SPEC-MT01](../specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md).

> **Amended 2026-08-09 (ADR 1.4 conformance assessment of 2026-08-05, findings §4 B1–B3).** The outcome now states the governed population, the applicability condition, and the exclusions this record has operated under since acceptance. The fixture requirement is unchanged.

## Context and Problem Statement

Standards can each pass their own unit tests while still failing when adopted together by a real consumer repository — conflicting authorities, incompatible profiles, or broken composition are the kinds of failures per-standard tests cannot see. How should the repository verify that standards actually compose correctly for a consumer, rather than only verifying that each standard is internally correct?

## Considered Options

- **Require dogfood consumer fixtures** — maintain fixture consumer repositories that adopt combinations of standards and profiles, exercising pairwise and profile-based composition.
- **Test only individual standards in isolation** — rely solely on per-standard unit tests and skip composition-level testing.

## Decision Outcome

Chosen option: **require dogfood consumer fixtures that exercise pairwise and profile-based standard composition**, because pairwise and fixture tests catch composition failures that per-standard unit tests miss, giving the authority map and conflict-free composition model in [ADR 0004](adr-0004-authority-map-and-conflict-free-composition.md) and the graph validation gate in [ADR 0007](adr-0007-standard-graph-validation-gate.md) a real, adopted-repository surface to validate against. Testing standards only in isolation was rejected because it would let conflicting or incompatible standards pass CI individually while still failing for real consumers.

This decision governs how this repository proves that its own standard packages compose for a consumer, and applies to changes to a standard package that can affect co-adoption — authorities, relationships, shared destinations, or profiles. Within that population, composition must be exercised by consumer fixtures rather than inferred from per-standard unit tests passing.

It does not govern the test strategy of repositories that adopt these standards, the internal coverage any individual package maintains for its own behavior, or which specific combinations must exist as fixtures. A change confined to one package's internals, touching no shared surface, is outside this decision and requires no exception to it.

### Consequences

- Good, because composition failures (authority conflicts, broken profiles) are caught before a real consumer repository hits them.
- Good, because the fixtures double as living examples of how standards and groups are meant to be adopted together.
- Bad, because fixture consumer repositories add maintenance burden and must be kept in sync as standards evolve.
- Neutral, because fixtures shift some testing effort from per-standard authors to whoever maintains the composition suite.
