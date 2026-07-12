---
schema_version: '1.1'
id: 'adr-0013-project-standards-independent-standard-packages-and-relationship-taxonomy'
title: 'ADR 0013: Independent Standard Packages and Relationship Taxonomy'
description: 'Records the decision to treat standards as independently adoptable packages by default, with explicit companion and extension relationships and groups as non-binding recommendation profiles.'
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
  - 'independence'
  - 'relationships'
aliases:
  - 'independent-standard-packages-and-relationship-taxonomy'
related:
  - 'docs/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md'
  - 'docs/adr/adr-0004-authority-map-and-conflict-free-composition.md'
  - 'docs/adr/adr-0007-standard-graph-validation-gate.md'
  - 'docs/adr/adr-0017-unified-standard-adoption-methodology.md'
  - 'docs/adr/adr-0018-standard-package-lifecycle-methodology.md'
  - 'docs/adr/adr-0020-standard-package-versioning-methodology.md'
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

# ADR 0013: Independent Standard Packages and Relationship Taxonomy

MADR status: **accepted**. Records decision D-013 of [SPEC-MT01](../specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md).

## Context and Problem Statement

Standards could be modeled as independent packages a consumer picks and chooses among, or as suites with implicit dependencies on one another. If standards secretly require one another, arbitrary adoption breaks and dependency resolution gets pushed onto agents instead of being checked mechanically. How should standards be modeled so that adoption stays composable and dependency resolution stays mechanical rather than implicit?

## Considered Options

- **Independent packages with an explicit relationship taxonomy** — treat each standard as independently adoptable by default, model relationships explicitly (independent, companion, extends, conflicts, consumes_platform), and treat standard groups as non-binding recommendation profiles.
- **Suites with implicit dependencies** — group standards into suites where membership implies required co-adoption of other standards.

## Decision Outcome

Chosen option: **treat standards as independent packages by default, model relationships with an explicit taxonomy (independent, companion, extends, conflicts, consumes_platform), and treat standard groups as recommendation profiles rather than hidden dependency suites**, because arbitrary adoption of standards fails if standards secretly require one another, and hidden hard dependencies push dependency resolution into agents instead of graph validation ([ADR 0007](adr-0007-standard-graph-validation-gate.md)). Modeling standards as suites with implicit dependencies was rejected because it harms composability and future MCP scalability, and conflicts with the conflict-free composition model already established in [ADR 0004](adr-0004-authority-map-and-conflict-free-composition.md). This is the through-line principle of the whole meta-repo effort.

### Consequences

- Good, because consumers can adopt any standard independently without silently pulling in undeclared dependencies.
- Good, because the explicit relationship taxonomy gives the graph validator a mechanical basis for checking conflicts and required companions.
- Bad, because relationships that used to be implicit in a suite must now be declared explicitly for every standard.
- Neutral, because groups become optional recommendation profiles rather than authoritative adoption units, changing how they are documented and consumed.
