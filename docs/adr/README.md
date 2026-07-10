---
schema_version: '1.1'
id: 'index-a3d7k2-architecture-decision-records'
title: 'Architecture Decision Records'
description: 'Index of the project-standards Architecture Decision Records, including the SPEC-MT01 meta-repository readiness decisions.'
doc_type: 'index'
status: 'active'
created: '2026-07-07'
updated: '2026-07-10'
reviewed: '2026-07-10'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'adr'
  - 'index'
  - 'decision'
aliases: []
related:
  - 'docs/superpowers/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md'
  - 'standards/adr/README.md'
  - 'standards/standard-bundle-authoring/README.md'
  - 'standards/markdown-frontmatter/field-values.md'
  - '.project-standards.yml'
  - 'docs/superpowers/specs/2026-07-10-consumer-standards-control-plane-spec.md'
  - 'docs/superpowers/specs/2026-07-10-root-artifact-ownership-semantic-composition-design.md'
  - 'docs/adr/adr-0023-unified-consumer-standards-control-plane.md'
  - 'docs/adr/adr-0024-catalog-scoped-package-version-channels.md'
---

# Architecture Decision Records

Decisions governing the `project-standards` repository, recorded in [MADR](https://adr.github.io/madr/) form. See the [ADR standard](../../standards/adr/README.md) for the format and the id/filename convention (the `id` embeds the repo name; the filename omits it).

ADRs **0001–0013** capture the original meta-repository readiness decisions from [SPEC-MT01](../superpowers/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md) §8.3. They were accepted on 2026-07-07; later decisions preserve that history through explicit amendment or supersession. ADRs **0014–0022** record repository field-value policy, local scope, packaged skills and hooks, adoption, lifecycle, provenance, and package versioning. ADR **0023** establishes the unified consumer control plane and supersedes ADRs 0003, 0008, and 0017. ADR **0024** establishes catalog-scoped package channels and supersedes ADR 0020. The MCP-server decisions (SPEC-MS01 §8.3) remain deferred to a later release.

| ADR | Title | Decision | Status |
| --- | --- | --- | --- |
| [0001](adr-0001-standard-bundle-authoring-contract.md) | Standard Bundle Authoring Contract | D-001 | active |
| [0002](adr-0002-manifest-first-standard-discovery.md) | Manifest-First Standard Discovery | D-002 | active |
| [0003](adr-0003-separate-standard-and-artifact-manifests.md) | Separate Standard and Artifact Manifests | D-003 | superseded by 0023 |
| [0004](adr-0004-authority-map-and-conflict-free-composition.md) | Authority Map and Conflict-Free Composition | D-004 | active |
| [0005](adr-0005-stable-generic-agent-tooling-interface.md) | Stable Generic Agent and Tooling Interface | D-005 | active |
| [0006](adr-0006-standard-provider-plugin-model.md) | Standard Provider and Plugin Model | D-006 | active |
| [0007](adr-0007-standard-graph-validation-gate.md) | Standard Graph Validation Gate | D-007 | active |
| [0008](adr-0008-consumer-config-namespace-registry.md) | Consumer Config Namespace Registry | D-008 | superseded by 0023 |
| [0009](adr-0009-agent-summary-and-canonical-standard-split.md) | Agent Summary and Canonical Standard Split | D-009 | active |
| [0010](adr-0010-standard-resource-uris-and-index.md) | Standard Resource URIs and Index | D-010 | active |
| [0011](adr-0011-dogfood-consumer-fixtures-for-standards-composition.md) | Dogfood Consumer Fixtures for Standards Composition | D-011 | active |
| [0012](adr-0012-mcp-readiness-before-server-implementation.md) | MCP Readiness Before Server Implementation | D-012 | active |
| [0013](adr-0013-independent-standard-packages-and-relationship-taxonomy.md) | Independent Standard Packages and Relationship Taxonomy | D-013 | active |
| [0014](adr-0014-markdown-frontmatter-field-value-policy.md) | Markdown Frontmatter Field Value Policy | local | active |
| [0015](adr-0015-exclude-standards-from-local-frontmatter-scope.md) | Exclude Standards from Local Frontmatter Scope | local | active |
| [0016](adr-0016-package-markdown-frontmatter-skill-with-standard.md) | Package Markdown Frontmatter Skill with Standard | local | active |
| [0017](adr-0017-unified-standard-adoption-methodology.md) | Unified Standard Adoption Methodology | local | superseded by 0023 |
| [0018](adr-0018-standard-package-lifecycle-methodology.md) | Standard Package Lifecycle Methodology | local | active |
| [0019](adr-0019-packaged-artifact-parity-and-provenance.md) | Packaged Artifact Parity and Provenance | local | active |
| [0020](adr-0020-standard-package-versioning-methodology.md) | Standard Package Versioning Methodology | local | superseded by 0024 |
| [0021](adr-0021-standard-packaged-skill-installation-methodology.md) | Standard-Packaged Skill Installation Methodology | local | active |
| [0022](adr-0022-standard-packaged-hook-installation-methodology.md) | Standard-Packaged Hook Installation Methodology | local | active |
| [0023](adr-0023-unified-consumer-standards-control-plane.md) | Unified Consumer Standards Control Plane | local | active |
| [0024](adr-0024-catalog-scoped-package-version-channels.md) | Catalog-Scoped Package Version Channels | local | active |
