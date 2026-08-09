---
schema_version: '1.1'
id: 'adr-0004-project-standards-authority-map-and-conflict-free-composition'
title: 'ADR 0004: Authority Map and Conflict-Free Composition'
description: 'Records the decision to model standard ownership as authority tuples so arbitrary standards can be co-adopted without silent tooling conflicts.'
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
  - 'composition'
  - 'authority-map'
aliases:
  - 'authority-map-and-conflict-free-composition'
related:
  - 'docs/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md'
  - 'docs/adr/adr-0007-standard-graph-validation-gate.md'
  - 'docs/adr/adr-0011-dogfood-consumer-fixtures-for-standards-composition.md'
  - 'docs/adr/adr-0013-independent-standard-packages-and-relationship-taxonomy.md'
  - 'docs/adr/adr-0023-unified-consumer-standards-control-plane.md'
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

# ADR 0004: Authority Map and Conflict-Free Composition

MADR status: **accepted**. Records decision D-004 of [SPEC-MT01](../specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md).

> **Amended 2026-08-09 (ADR 1.4 conformance assessment of 2026-08-05, findings §4, C3, and B6).** The outcome now names the plane this record governs — authoring-time conflicts between package manifests in the standards graph — and excludes the consumer-file plane [ADR 0023](adr-0023-unified-consumer-standards-control-plane.md) governs. The authority-tuple declaration requirement moves out of `### Consequences` into the bounded outcome where policy belongs. The authority model, the conflict rule, and the rejection of precedence are unchanged.

## Context and Problem Statement

Consumers may co-adopt arbitrary combinations of standards, and two standards can silently claim ownership of the same tooling concern (for example, two standards both trying to own linting configuration for the same target). How should ownership be modeled so that arbitrary co-adoption can be proven conflict-free rather than merely hoped to be?

## Considered Options

- **Authority tuples** — model each ownership claim as a `(domain, target, concern, owner, mutability)` tuple that tooling can check for overlaps.
- **Rely on standard authors to notice conflicts manually** — leave conflict detection to human judgment during authoring.
- **Allow precedence rules to resolve authority conflicts** — permit overlapping claims and resolve them by an ordering/precedence mechanism.

## Decision Outcome

Chosen option: **use authority tuples (domain, target, concern, owner, mutability) to enforce conflict-free composition**, because arbitrary co-adoption is impossible to prove from prose alone. Relying on authors to notice conflicts manually was rejected as unscalable and error-prone once the number of standards grows. Allowing precedence rules to resolve conflicts was also rejected, because precedence hides design errors and makes co-adoption unpredictable rather than provably safe.

This decision governs ownership claims between standard packages in this repository's standards graph, and applies at authoring and graph-validation time to the authority tuples a package declares. Within that population, every standard must explicitly declare its authority tuples, and two overlapping mutating claims are a validation error rather than a resolvable precedence question.

It does not govern write-time ownership of bytes inside a consumer repository's files. Which package owns a semantic unit in a shared consumer file — a TOML key path, a JSON or JSONC key, a YAML mapping, an EditorConfig property, a task or hook identity, or a delimiter-bounded Markdown block — is governed by [ADR 0023](adr-0023-unified-consumer-standards-control-plane.md). The two planes are complementary rather than competing: this record proves before installation that two packages do not claim the same tooling concern, while ADR 0023 decides what happens when two installed packages touch one file. A consumer-file ownership question is outside this decision and requires no exception to it.

### Consequences

- Good, because ownership conflicts between co-adopted standards can be detected mechanically rather than by inspection.
- Good, because the authority map gives the graph validator ([ADR 0007](adr-0007-standard-graph-validation-gate.md)) a concrete structure to check.
- Bad, because declaring authority tuples adds authoring overhead to every standard and moves ownership work earlier, to a point where the author may not yet know every target.
- Neutral, because this authority model also underpins how independent standard packages relate to one another ([ADR 0013](adr-0013-independent-standard-packages-and-relationship-taxonomy.md)).
