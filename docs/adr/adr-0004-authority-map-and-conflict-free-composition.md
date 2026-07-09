---
schema_version: '1.1'
id: 'adr-0004-project-standards-authority-map-and-conflict-free-composition'
title: 'ADR 0004: Authority Map and Conflict-Free Composition'
description: 'Records the decision to model standard ownership as authority tuples so arbitrary standards can be co-adopted without silent tooling conflicts.'
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
  - 'composition'
  - 'authority-map'
aliases:
  - 'authority-map-and-conflict-free-composition'
related:
  - 'docs/superpowers/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md'
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

# ADR 0004: Authority Map and Conflict-Free Composition

MADR status: **accepted**. Records decision D-004 of [SPEC-MT01](../superpowers/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md).

## Context and Problem Statement

Consumers may co-adopt arbitrary combinations of standards, and two standards can silently claim ownership of the same tooling concern (for example, two standards both trying to own linting configuration for the same target). How should ownership be modeled so that arbitrary co-adoption can be proven conflict-free rather than merely hoped to be?

## Considered Options

- **Authority tuples** — model each ownership claim as a `(domain, target, concern, owner, mutability)` tuple that tooling can check for overlaps.
- **Rely on standard authors to notice conflicts manually** — leave conflict detection to human judgment during authoring.
- **Allow precedence rules to resolve authority conflicts** — permit overlapping claims and resolve them by an ordering/precedence mechanism.

## Decision Outcome

Chosen option: **use authority tuples (domain, target, concern, owner, mutability) to enforce conflict-free composition**, because arbitrary co-adoption is impossible to prove from prose alone. Relying on authors to notice conflicts manually was rejected as unscalable and error-prone once the number of standards grows. Allowing precedence rules to resolve conflicts was also rejected, because precedence hides design errors and makes co-adoption unpredictable rather than provably safe.

### Consequences

- Good, because ownership conflicts between co-adopted standards can be detected mechanically rather than by inspection.
- Good, because the authority map gives the graph validator ([ADR 0007](adr-0007-standard-graph-validation-gate.md)) a concrete structure to check.
- Bad, because every standard must now explicitly declare its authority tuples, adding authoring overhead.
- Neutral, because this authority model also underpins how independent standard packages relate to one another ([ADR 0013](adr-0013-independent-standard-packages-and-relationship-taxonomy.md)).
