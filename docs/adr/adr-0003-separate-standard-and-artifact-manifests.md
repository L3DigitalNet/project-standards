---
schema_version: '1.1'
id: 'adr-0003-project-standards-separate-standard-and-artifact-manifests'
title: 'ADR 0003: Separate Standard and Artifact Manifests'
description: 'Records the decision to keep the existing artifact-focused adopt.toml and reference it from standard.toml rather than merging everything into one manifest.'
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
  - 'manifests'
  - 'adopt-engine'
aliases:
  - 'separate-standard-and-artifact-manifests'
related:
  - 'docs/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md'
  - 'docs/adr/adr-0002-manifest-first-standard-discovery.md'
  - 'docs/adr/adr-0017-unified-standard-adoption-methodology.md'
  - 'docs/adr/adr-0019-packaged-artifact-parity-and-provenance.md'
  - 'docs/adr/adr-0021-standard-packaged-skill-installation-methodology.md'
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

# ADR 0003: Separate Standard and Artifact Manifests

MADR status: **superseded** by [ADR 0023](adr-0023-unified-consumer-standards-control-plane.md). Records historical decision D-003 of [SPEC-MT01](../specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md).

## Context and Problem Statement

`standard.toml` ([ADR 0002](adr-0002-manifest-first-standard-discovery.md)) now becomes the primary manifest for standard metadata, but each standard already has an `adopt.toml` that drives artifact planning and adoption behavior. Should the new standard manifest absorb `adopt.toml`'s artifact-focused fields, or should the two manifests stay separate?

## Considered Options

- **Preserve `adopt.toml` as artifact-focused and reference it from `standard.toml`** — keep the two manifests distinct, with the standard manifest pointing at the existing artifact manifest.
- **Merge all artifact fields into one large manifest in one step** — fold `adopt.toml`'s contents directly into `standard.toml`.

## Decision Outcome

Chosen option: **preserve `adopt.toml` as artifact-focused and reference it from `standard.toml`**, because the current adopt engine already has useful safety and planning behavior worth reusing as-is. Merging all artifact fields into one manifest in a single step was rejected as carrying higher migration risk, since the existing artifact planning already works and a large merge would put that working behavior at risk for no immediate benefit.

### Consequences

- Good, because the adopt engine's existing safety and planning behavior is preserved unchanged.
- Good, because migration risk is minimized by avoiding a large, one-step manifest merge.
- Bad, because standard metadata is now split across two files (`standard.toml` and `adopt.toml`) that must stay cross-referenced.
- Neutral, because a future ADR could revisit consolidation once both manifests have proven stable in practice.
