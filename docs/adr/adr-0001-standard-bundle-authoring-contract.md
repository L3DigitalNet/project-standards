---
schema_version: '1.1'
id: 'adr-0001-project-standards-standard-bundle-authoring-contract'
title: 'ADR 0001: Standard Bundle Authoring Contract'
description: 'Records the decision to govern how standards are authored in this repository with a dedicated meta-standard (the Standard Bundle Authoring Standard).'
doc_type: 'adr'
status: 'review'
created: '2026-07-07'
updated: '2026-07-07'
reviewed: null
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'standards-platform'
  - 'meta-repo'
  - 'mcp-readiness'
aliases:
  - 'standard-bundle-authoring-contract'
related:
  - 'docs/superpowers/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md'
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

# ADR 0001: Standard Bundle Authoring Contract

MADR status: **proposed**. Records decision D-001 of [SPEC-MT01](../superpowers/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md).

## Context and Problem Statement

Standards live as bundles under `standards/<id>/`, but nothing defines what a standard bundle _must_ declare — its identity, lifecycle, resources, authorities, capabilities, relationships, artifacts, or providers. As the count grows past a handful and future tooling (the standards graph, and later an MCP server) must discover, compose, and validate standards without hardcoding each one, informal per-`README` conventions cannot scale and cannot be checked mechanically. What contract must every standard bundle follow so that adding a standard is a data/documentation change rather than a tool-code change?

## Considered Options

- **A formal Standard Bundle Authoring Standard** — a meta-standard governing how standards are authored, versioned, validated, and composed (required files, manifests, authority rules, relationship rules, resource rules, CI gates).
- **Keep conventions informal** — document expectations only in prose across the individual standard READMEs.

## Decision Outcome

Chosen option: **create the Standard Bundle Authoring Standard**. Scaling the number of standards requires a "standard for standards": a single, machine-checkable contract makes adding a standard primarily a data/documentation/validation change, and gives the graph validator ([ADR 0007](adr-0007-standard-graph-validation-gate.md)) and manifest model ([ADR 0002](adr-0002-manifest-first-standard-discovery.md)) something concrete to enforce. Prose-only rules were rejected because neither agents nor CI can prove non-conflict or completeness from prose.

### Consequences

- Good, because every bundle becomes uniform and machine-discoverable, so new standards scale without tool changes.
- Good, because it gives the authority map, manifests, and graph validation a contract to check against.
- Bad, because it is one more standard to maintain, and existing standards must be retrofitted to comply (a later step).
- Neutral, because draft or reference-only standards must now explicitly declare their non-adoptable status rather than being implicitly incomplete.

### Confirmation

Graph validation fails any bundle that does not meet the authoring contract; the meta-standard ships with its own bundle and tests, and this repository dogfoods it.
