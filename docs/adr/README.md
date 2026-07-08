---
schema_version: '1.1'
id: 'index-a3d7k2-architecture-decision-records'
title: 'Architecture Decision Records'
description: 'Index of the project-standards Architecture Decision Records, including the SPEC-MT01 meta-repository readiness decisions.'
doc_type: 'index'
status: 'active'
created: '2026-07-07'
updated: '2026-07-07'
reviewed: null
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'adr'
  - 'index'
  - 'decisions'
aliases: []
related:
  - 'docs/superpowers/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md'
---

# Architecture Decision Records

Decisions governing the `project-standards` repository, recorded in [MADR](https://adr.github.io/madr/) form. See the [ADR standard](../../standards/adr/README.md) for the format and the id/filename convention (the `id` embeds the repo name; the filename omits it).

ADRs **0001–0013** capture the meta-repository readiness decisions from [SPEC-MT01](../superpowers/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md) §8.3. They were **accepted** on 2026-07-07 (`status: active`, MADR `accepted`); changing one now requires a superseding ADR. The MCP-server decisions (SPEC-MS01 §8.3) are deferred to a later release and are not yet recorded here.

| ADR | Title | Decision | Status |
| --- | --- | --- | --- |
| [0001](adr-0001-standard-bundle-authoring-contract.md) | Standard Bundle Authoring Contract | D-001 | active |
| [0002](adr-0002-manifest-first-standard-discovery.md) | Manifest-First Standard Discovery | D-002 | active |
| [0003](adr-0003-separate-standard-and-artifact-manifests.md) | Separate Standard and Artifact Manifests | D-003 | active |
| [0004](adr-0004-authority-map-and-conflict-free-composition.md) | Authority Map and Conflict-Free Composition | D-004 | active |
| [0005](adr-0005-stable-generic-agent-tooling-interface.md) | Stable Generic Agent and Tooling Interface | D-005 | active |
| [0006](adr-0006-standard-provider-plugin-model.md) | Standard Provider and Plugin Model | D-006 | active |
| [0007](adr-0007-standard-graph-validation-gate.md) | Standard Graph Validation Gate | D-007 | active |
| [0008](adr-0008-consumer-config-namespace-registry.md) | Consumer Config Namespace Registry | D-008 | active |
| [0009](adr-0009-agent-summary-and-canonical-standard-split.md) | Agent Summary and Canonical Standard Split | D-009 | active |
| [0010](adr-0010-standard-resource-uris-and-index.md) | Standard Resource URIs and Index | D-010 | active |
| [0011](adr-0011-dogfood-consumer-fixtures-for-standards-composition.md) | Dogfood Consumer Fixtures for Standards Composition | D-011 | active |
| [0012](adr-0012-mcp-readiness-before-server-implementation.md) | MCP Readiness Before Server Implementation | D-012 | active |
| [0013](adr-0013-independent-standard-packages-and-relationship-taxonomy.md) | Independent Standard Packages and Relationship Taxonomy | D-013 | active |
