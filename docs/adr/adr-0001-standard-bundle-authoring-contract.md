---
schema_version: '1.1'
id: 'adr-0001-project-standards-standard-bundle-authoring-contract'
title: 'ADR 0001: Standard Bundle Authoring Contract'
description: 'Records the decision to govern how standards are authored in this repository with a dedicated meta-standard (the Standard Bundle Authoring Standard).'
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
  - 'mcp-readiness'
aliases:
  - 'standard-bundle-authoring-contract'
related:
  - 'docs/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md'
  - 'docs/adr/adr-0002-manifest-first-standard-discovery.md'
  - 'docs/adr/adr-0007-standard-graph-validation-gate.md'
  - 'docs/adr/adr-0017-unified-standard-adoption-methodology.md'
  - 'docs/adr/adr-0018-standard-package-lifecycle-methodology.md'
  - 'docs/adr/adr-0019-packaged-artifact-parity-and-provenance.md'
  - 'docs/adr/adr-0020-standard-package-versioning-methodology.md'
  - 'docs/adr/adr-0021-standard-packaged-skill-installation-methodology.md'
  - 'docs/adr/adr-0022-standard-packaged-hook-installation-methodology.md'
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

# ADR 0001: Standard Bundle Authoring Contract

MADR status: **accepted**. Records decision D-001 of [SPEC-MT01](../specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md).

> **Amended 2026-08-09 (ADR 1.4 conformance assessment of 2026-08-05, findings §4 and B6).** The outcome now states the governed population, the applicability condition, and the exclusions this record has operated under since acceptance, and the non-adoptable-status requirement moves out of `### Consequences` into the bounded outcome where policy belongs. Nothing this record selected changes.

## Context and Problem Statement

Standards live as bundles under `standards/<id>/`, but nothing defines what a standard bundle _must_ declare — its identity, lifecycle, resources, authorities, capabilities, relationships, artifacts, or providers. As the count grows past a handful and future tooling (the standards graph, and later an MCP server) must discover, compose, and validate standards without hardcoding each one, informal per-`README` conventions cannot scale and cannot be checked mechanically. What contract must every standard bundle follow so that adding a standard is a data/documentation change rather than a tool-code change?

## Considered Options

- **A formal Standard Bundle Authoring Standard** — a meta-standard governing how standards are authored, versioned, validated, and composed (required files, manifests, authority rules, relationship rules, resource rules, CI gates).
- **Keep conventions informal** — document expectations only in prose across the individual standard READMEs.

## Decision Outcome

Chosen option: **create the Standard Bundle Authoring Standard**. Scaling the number of standards requires a "standard for standards": a single, machine-checkable contract makes adding a standard primarily a data/documentation/validation change, and gives the graph validator ([ADR 0007](adr-0007-standard-graph-validation-gate.md)) and manifest model ([ADR 0002](adr-0002-manifest-first-standard-discovery.md)) something concrete to enforce. Prose-only rules were rejected because neither agents nor CI can prove non-conflict or completeness from prose.

This decision governs the authoring contract for standard packages maintained in this repository under `standards/`, and applies whenever such a package is added here, materially revised, or validated. Within that population, a draft or reference-only standard must explicitly declare its non-adoptable status rather than being implicitly incomplete.

It does not govern the subject-matter rules any individual standard states, the documents of repositories that adopt those standards, or which standards a consumer chooses to adopt — each standard's own text governs the first, and [ADR 0023](adr-0023-unified-consumer-standards-control-plane.md) governs the consumer plane. A document outside `standards/` is outside this decision and requires no exception to it.

### Consequences

- Good, because every bundle becomes uniform and machine-discoverable, so new standards scale without tool changes.
- Good, because it gives the authority map, manifests, and graph validation a contract to check against.
- Bad, because it is one more standard to maintain, and existing standards must be retrofitted to comply (a later step).
- Neutral, because the non-adoptable status of a draft or reference-only standard becomes visible metadata rather than an implicit gap a reader has to infer.

### Confirmation

Graph validation fails any bundle that does not meet the authoring contract; the meta-standard ships with its own bundle and tests, and this repository dogfoods it.
