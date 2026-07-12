---
schema_version: '1.1'
id: 'adr-0002-project-standards-manifest-first-standard-discovery'
title: 'ADR 0002: Manifest-First Standard Discovery'
description: 'Records the decision to make standard.toml the primary machine-readable manifest for standard metadata so tooling discovers standards without parsing prose.'
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
  - 'manifests'
aliases:
  - 'manifest-first-standard-discovery'
related:
  - 'docs/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md'
  - 'docs/adr/adr-0003-separate-standard-and-artifact-manifests.md'
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

# ADR 0002: Manifest-First Standard Discovery

MADR status: **accepted**. Records decision D-002 of [SPEC-MT01](../specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md).

## Context and Problem Statement

Standard bundles carry identity, lifecycle, and relationship metadata that tooling — the graph validator, future agent/MCP tools, and the registry — must read reliably. Today that metadata is scattered across prose in each `README.md`, which humans can read but machines cannot parse or validate. What should be the primary, machine-readable source of a standard's metadata so tooling can discover standards without parsing prose?

## Considered Options

- **`standard.toml` as the primary manifest** — a dedicated, per-bundle machine-readable manifest for standard metadata.
- **Encode everything in `README.md`** — keep metadata embedded in prose documentation.
- **Expand `registry.json` only** — push all standard metadata into the central registry rather than per-bundle manifests.

## Decision Outcome

Chosen option: **use `standard.toml` as the primary manifest for standard metadata**, because machine consumers need stable, validated metadata independent of prose. Encoding metadata only in `README.md` was rejected since prose cannot be validated mechanically. Expanding `registry.json` only was also rejected — a single registry would grow too broad and distant from each bundle, whereas a per-bundle manifest keeps ownership local to the standard it describes.

### Consequences

- Good, because standard metadata becomes stable, validated, and independent of prose edits.
- Good, because ownership of metadata stays local to each bundle rather than centralized in a distant registry.
- Bad, because every standard bundle must now maintain an additional manifest file in sync with its documentation.
- Neutral, because the registry ([ADR 0003](adr-0003-separate-standard-and-artifact-manifests.md)) and graph validator ([ADR 0007](adr-0007-standard-graph-validation-gate.md)) can now assume `standard.toml` as their primary data source.
