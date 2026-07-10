---
schema_version: '1.1'
id: 'adr-0008-project-standards-consumer-config-namespace-registry'
title: 'ADR 0008: Consumer Config Namespace Registry'
description: 'Records the decision to require declared ownership of top-level project-standards.yml config namespaces so standards cannot collide.'
doc_type: 'adr'
status: 'superseded'
created: '2026-07-07'
updated: '2026-07-10'
reviewed: '2026-07-10'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'standards-platform'
  - 'meta-repo'
  - 'config'
aliases:
  - 'consumer-config-namespace-registry'
related:
  - 'docs/superpowers/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md'
  - 'docs/adr/adr-0007-standard-graph-validation-gate.md'
  - 'docs/adr/adr-0020-standard-package-versioning-methodology.md'
  - 'docs/adr/adr-0023-unified-consumer-standards-control-plane.md'
supersedes: []
superseded_by: 'adr-0023-project-standards-unified-consumer-standards-control-plane'
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

# ADR 0008: Consumer Config Namespace Registry

MADR status: **superseded** by [ADR 0023](adr-0023-unified-consumer-standards-control-plane.md). Records historical decision D-008 of [SPEC-MT01](../superpowers/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md).

## Context and Problem Statement

Each standard a consumer adopts may need its own configuration in the consumer's `project-standards.yml`, but if any standard can add arbitrary top-level keys, two standards can collide on the same key or a typo can silently create an unowned key. How should top-level config namespaces in the consumer config file be assigned so that standards cannot collide?

## Considered Options

- **Require config namespace ownership** — each standard declares the top-level namespace(s) it owns, and the graph validator rejects duplicate namespace claims and undeclared top-level keys.
- **Allow standards to add arbitrary config keys** — no registry, standards write whatever top-level keys they need.

## Decision Outcome

Chosen option: **require config namespace ownership, with the graph validator rejecting duplicate namespaces and undeclared top-level config keys**. The consumer config file must not become a collision-prone dumping ground, so ownership has to be declared and mechanically enforced by the same graph validation gate ([ADR 0007](adr-0007-standard-graph-validation-gate.md)) that checks the rest of the standard graph. Allowing standards to add arbitrary config keys was rejected because it leaves namespace collisions and undeclared keys undetectable until they cause a runtime conflict.

### Consequences

- Good, because namespace collisions between standards are caught by validation instead of surfacing as confusing runtime config conflicts.
- Good, because a consumer's `project-standards.yml` stays legible: every top-level key is traceable to the standard that owns it.
- Bad, because standards must explicitly declare their namespace(s) up front, adding a small authoring step.
- Neutral, because an undeclared top-level key is treated as an error rather than being silently ignored or accepted.
