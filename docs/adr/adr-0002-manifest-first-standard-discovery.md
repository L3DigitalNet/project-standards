---
schema_version: '1.1'
id: 'adr-0002-project-standards-manifest-first-standard-discovery'
title: 'ADR 0002: Manifest-First Standard Discovery'
description: 'Records the decision to make standard.toml the primary machine-readable manifest for standard metadata so tooling discovers standards without parsing prose.'
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
  - 'manifests'
aliases:
  - 'manifest-first-standard-discovery'
related:
  - 'docs/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md'
  - 'docs/adr/adr-0003-separate-standard-and-artifact-manifests.md'
  - 'docs/adr/adr-0007-standard-graph-validation-gate.md'
  - 'docs/adr/adr-0010-standard-resource-uris-and-index.md'
  - 'docs/adr/adr-0012-mcp-readiness-before-server-implementation.md'
  - 'docs/adr/adr-0017-unified-standard-adoption-methodology.md'
  - 'docs/adr/adr-0018-standard-package-lifecycle-methodology.md'
  - 'docs/adr/adr-0019-packaged-artifact-parity-and-provenance.md'
  - 'docs/adr/adr-0020-standard-package-versioning-methodology.md'
  - 'docs/adr/adr-0024-catalog-scoped-package-version-channels.md'
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
    - 'adr-0018-project-standards-standard-package-lifecycle-methodology'
    - 'adr-0024-project-standards-catalog-scoped-package-version-channels'
---

# ADR 0002: Manifest-First Standard Discovery

MADR status: **accepted**. Records decision D-002 of [SPEC-MT01](../specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md).

> **Amended by ADR 0018 (2026-07-09).** The "primary manifest" claim is narrowed to lifecycle. The family `standard.toml` is the canonical machine-readable source of a package family's lifecycle state and relationships, not of every metadata plane a package now has. Manifest-first discovery is otherwise in force, and prose remains a non-source.
>
> **Amended by ADR 0024 (2026-07-10).** Permanent per-release advertisement — every advertised version, its digest, and its channel role — is held centrally in `src/project_standards/catalogs/<major>.toml`. That is structurally the central registry this record rejected, reintroduced for a concern this record never evaluated: offline resolution and permanent version advertisement. Ownership of a family's own metadata stays with the family manifest, and the rejection of a registry as the home for _that_ metadata is unchanged.
>
> **Amended 2026-08-09 (ADR 1.4 conformance assessment of 2026-08-05, findings §4, C5, and B6).** The outcome now states the governed population, the applicability condition, and the exclusions this record has operated under since acceptance, and the in-sync manifest requirement moves out of `### Consequences` into the bounded outcome where policy belongs. Nothing this record selected changes.

## Context and Problem Statement

Standard bundles carry identity, lifecycle, and relationship metadata that tooling — the graph validator, future agent/MCP tools, and the registry — must read reliably. Today that metadata is scattered across prose in each `README.md`, which humans can read but machines cannot parse or validate. What should be the primary, machine-readable source of a standard's metadata so tooling can discover standards without parsing prose?

## Considered Options

- **`standard.toml` as the primary manifest** — a dedicated, per-bundle machine-readable manifest for standard metadata.
- **Encode everything in `README.md`** — keep metadata embedded in prose documentation.
- **Expand `registry.json` only** — push all standard metadata into the central registry rather than per-bundle manifests.

## Decision Outcome

Chosen option: **use `standard.toml` as the primary manifest for standard metadata**, because machine consumers need stable, validated metadata independent of prose. Encoding metadata only in `README.md` was rejected since prose cannot be validated mechanically. Expanding `registry.json` only was also rejected — a single registry would grow too broad and distant from each bundle, whereas a per-bundle manifest keeps ownership local to the standard it describes.

This decision governs where a standard package family's own identity, lifecycle, and relationship metadata is authored in this repository, and applies whenever a family under `standards/` is added or revised. Within that population, each family must maintain its `standard.toml` manifest in sync with its documentation.

It does not govern the per-version `payload.toml` that declares artifacts, resources, providers, and digests; the central catalog projection that advertises released versions; or the metadata a consuming repository keeps about its own installed standards. Those planes are governed by [ADR 0019](adr-0019-packaged-artifact-parity-and-provenance.md), [ADR 0024](adr-0024-catalog-scoped-package-version-channels.md), and [ADR 0023](adr-0023-unified-consumer-standards-control-plane.md) respectively. Metadata held outside a family manifest for one of those reasons is outside this decision and requires no exception to it.

### Consequences

- Good, because standard metadata becomes stable, validated, and independent of prose edits.
- Good, because ownership of metadata stays local to each bundle rather than centralized in a distant registry.
- Bad, because the in-sync manifest is an additional file per family, so documentation and metadata can now disagree in a way prose alone could not.
- Neutral, because the registry ([ADR 0003](adr-0003-separate-standard-and-artifact-manifests.md)) and graph validator ([ADR 0007](adr-0007-standard-graph-validation-gate.md)) can now assume `standard.toml` as their primary data source.
