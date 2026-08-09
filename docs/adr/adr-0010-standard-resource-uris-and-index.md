---
schema_version: '1.1'
id: 'adr-0010-project-standards-standard-resource-uris-and-index'
title: 'ADR 0010: Standard Resource URIs and Index'
description: 'Records the decision to treat standard resources as lazy-loadable, URI-addressable assets declared in manifests and surfaced through a generated index.'
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
  - 'resources'
aliases:
  - 'standard-resource-uris-and-index'
related:
  - 'docs/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md'
  - 'docs/adr/adr-0002-manifest-first-standard-discovery.md'
  - 'docs/adr/adr-0005-stable-generic-agent-tooling-interface.md'
  - 'docs/adr/adr-0009-agent-summary-and-canonical-standard-split.md'
  - 'docs/adr/adr-0017-unified-standard-adoption-methodology.md'
  - 'docs/adr/adr-0019-packaged-artifact-parity-and-provenance.md'
  - 'docs/adr/adr-0021-standard-packaged-skill-installation-methodology.md'
  - 'docs/adr/adr-0022-standard-packaged-hook-installation-methodology.md'
  - 'docs/adr/adr-0026-project-standards-mcp-local-read-only-transport.md'
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

# ADR 0010: Standard Resource URIs and Index

MADR status: **accepted**. Records decision D-010 of [SPEC-MT01](../specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md).

> **Amended 2026-08-09 (ADR 1.4 conformance assessment of 2026-08-05, findings §5 and C1).** The outcome now states the governed population and excludes the wire URI grammar a protocol server exposes, which [ADR 0026](adr-0026-project-standards-mcp-local-read-only-transport.md) froze separately for MCP v1. The declaration-and-index decision is unchanged, and the divergence between the two forms remains an open alignment item rather than an exception to this record.

## Context and Problem Statement

Standard bundles contain resources (references, templates, checklists, and other supporting files) that clients need to locate and load, but the repository has no declared, uniform way to address these resources or discover them without walking the filesystem. A future MCP server needs to expose resources directly from manifests. How should standard resources be addressed and discovered so that a server, or any other client, can surface them without rediscovering paths on its own?

## Considered Options

- **Lazy-loadable, URI-like resource declarations in manifests, surfaced via a generated index** — each standard declares its resources in its manifest with a URI-like identifier, and an index is generated from these declarations.
- **Let each client discover file paths independently** — clients walk the standard bundle directory tree at runtime to find resources.

## Decision Outcome

Chosen option: **lazy-loadable, URI-like resource declarations in manifests, surfaced via a generated index**, because a future MCP server can then expose resources directly from manifests without each client rediscovering paths, consistent with the manifest-first discovery model established in [ADR 0002](adr-0002-manifest-first-standard-discovery.md) and the stable tooling interface in [ADR 0005](adr-0005-stable-generic-agent-tooling-interface.md). Independent per-client discovery was rejected because it duplicates path-walking logic across clients and gives the eventual agent summary work in [ADR 0009](adr-0009-agent-summary-and-canonical-standard-split.md) no stable resource identifiers to reference.

This decision governs how a standard package declares its resources and how the generated catalog index addresses them, and applies to resources declared in a package manifest and published through `standards/catalog.md`. Within that population, a resource is declared in the manifest and addressed by its declared identifier rather than discovered by walking the directory tree.

It does not govern the wire URI grammar a server exposes across a protocol boundary. [ADR 0026](adr-0026-project-standards-mcp-local-read-only-transport.md) froze the MCP v1 grammar as a four-segment `standards://{standard_id}/{version}/resources/{resource_id}` form, disclosed that it differs from the three-segment form the shipped index emits, and explicitly declined to reconcile them. That divergence is an open index-and-producer alignment item flagged for owner decision; it is not a departure from this record, and a server URI form requires no exception here. This decision also does not govern how large or dynamic a resource may be beyond requiring that it be lazy-loadable by declaration.

### Consequences

- Good, because clients and a future MCP server address resources through stable, declared identifiers instead of filesystem paths.
- Good, because a generated index gives agents and tooling a single place to discover available resources across all standards.
- Bad, because every resource addition or move requires a manifest update rather than being picked up implicitly from the directory tree.
- Neutral, because resources must be lazy-loadable by declaration, which constrains how large or dynamic a resource can be.
