---
schema_version: '1.1'
id: 'adr-0007-project-standards-standard-graph-validation-gate'
title: 'ADR 0007: Standard Graph Validation Gate'
description: 'Records the decision to run standards-graph validation as part of the normal verification gate so manifest and composition drift fails CI.'
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
  - 'validation'
  - 'ci'
aliases:
  - 'standard-graph-validation-gate'
related:
  - 'docs/superpowers/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md'
  - 'docs/adr/adr-0001-standard-bundle-authoring-contract.md'
  - 'docs/adr/adr-0002-manifest-first-standard-discovery.md'
  - 'docs/adr/adr-0004-authority-map-and-conflict-free-composition.md'
  - 'docs/adr/adr-0008-consumer-config-namespace-registry.md'
  - 'docs/adr/adr-0018-standard-package-lifecycle-methodology.md'
  - 'docs/adr/adr-0019-packaged-artifact-parity-and-provenance.md'
  - 'docs/adr/adr-0020-standard-package-versioning-methodology.md'
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

# ADR 0007: Standard Graph Validation Gate

MADR status: **accepted**. Records decision D-007 of [SPEC-MT01](../superpowers/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md).

## Context and Problem Statement

The standard bundle authoring contract ([ADR 0001](adr-0001-standard-bundle-authoring-contract.md)) and the manifest-first discovery model ([ADR 0002](adr-0002-manifest-first-standard-discovery.md)) define what a compliant standard graph looks like, but a definition enforced only by memory or occasional manual review will drift as standards are added and changed. Where in the workflow should the standard graph be validated so that manifest and composition drift is actually caught?

## Considered Options

- **Add graph validation to the normal verification gate** — run it alongside the existing automated checks on every change.
- **Run validation manually before releases only** — treat it as a pre-release checklist item rather than a continuous check.

## Decision Outcome

Chosen option: **add graph validation to the normal verification gate**. A manifest model is only useful if it is continuously enforced, so validating the standard graph — manifests, authority conflicts ([ADR 0004](adr-0004-authority-map-and-conflict-free-composition.md)), and namespace ownership ([ADR 0008](adr-0008-consumer-config-namespace-registry.md)) — must run on every change rather than being deferred to a point where drift has already accumulated. Running validation manually before releases only was rejected because manual, infrequent checks let drift compound silently between releases and depend on a human remembering to run them.

### Consequences

- Good, because manifest and composition drift is caught at the change that introduces it, not weeks later.
- Good, because it makes the graph validator a load-bearing, continuously-exercised part of the repository rather than an optional tool.
- Bad, because every change touching a standard bundle now depends on the graph validator being correct and fast enough to run routinely.
- Neutral, because contributors must fix graph violations before merging rather than deferring them to a later cleanup pass.

### Confirmation

The verification gate fails any change that leaves the standard graph in an invalid state, and this is exercised continuously as part of normal CI rather than as a release-time-only step.
