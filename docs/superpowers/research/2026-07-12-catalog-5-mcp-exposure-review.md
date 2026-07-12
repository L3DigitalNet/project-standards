---
schema_version: '1.1'
id: 'research-mcp5r1-catalog-5-exposure-review'
title: 'Catalog 5 MCP Exposure Review'
description: 'Package-by-package pre-release review of catalog 5 metadata, resources, providers, summaries, schemas, relationships, and outputs for later generic MCP exposure.'
doc_type: 'research'
status: 'active'
created: '2026-07-12'
updated: '2026-07-12'
reviewed: '2026-07-12'
owner: 'Project standards'
consumer: 'agent'
tags:
  - 'catalog-5'
  - 'mcp'
  - 'package-contract'
  - 'release-readiness'
aliases:
  - 'Catalog 5 MCP readiness review'
related:
  - 'docs/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md'
  - 'docs/specs/2026-07-07-project-standards-mcp-enablement-roadmap-spec.md'
  - 'docs/specs/2026-07-10-standard-bundle-authoring-v2-spec.md'
confidence: 'high'
visibility: 'internal'
license: null
---

# Catalog 5 MCP Exposure Review

**Outcome:** all nine catalog 5 packages are ready for later generic MCP exposure. No package-specific corrective release is required before v5.0.0.

This review covers the seven consumer packages, reference-only Python Coding, and internal Standard Bundle Authoring. The deferred `project-toolbox` and `agent-managed-repo` packages are outside catalog 5 and outside this gate. This is package-readiness evidence for SPEC-MT01; it is not the Step 07 readiness report and does not authorize MCP implementation.

## Review criteria

Every package was checked for:

- an exact family, payload, catalog role, and aggregate digest;
- one canonical standard, compact agent summary, and closed configuration schema;
- URI-safe declared resources whose paths, media types, and digests validate;
- provider entrypoints and declared schemas where the package exposes operations;
- typed outputs and authority scopes without whole-container conflicts;
- explicit companion, extension, conflict, and platform-capability relationships;
- a canonical README backlink and authority statement in its agent summary;
- source/projection parity and compatibility with the catalog 5 control plane.

## Package matrix

| Package | Version | Role | Availability | Resources | Providers | Outputs | Summary bytes | Closed schema | Canonical backlink |
| --- | --- | --- | --- | --: | --: | --: | --: | --- | --- |
| ADR | 1.1 | default | consumer | 12 | 2 | 1 | 722 | yes | yes |
| Agent Handoff | 1.1 | default | consumer | 29 | 8 | 18 | 2,730 | yes | yes |
| CLI Documentation | 1.1 | default | consumer | 13 | 3 | 1 | 1,055 | yes | yes |
| Markdown Frontmatter | 1.2 | default | consumer | 26 | 4 | 7 | 2,225 | yes | yes |
| Markdown Tooling | 1.2 | default | consumer | 17 | 6 | 25 | 1,537 | yes | yes |
| Project Specification | 1.1 | default | consumer | 23 | 9 | 1 | 1,671 | yes | yes |
| Python Coding | 0.5 | reference-only | reference-only | 3 | 1 | 0 | 2,598 | yes | yes |
| Python Tooling | 1.1 | default | consumer | 13 | 3 | 52 | 924 | yes | yes |
| Standard Bundle Authoring | 2.0 | internal | internal | 12 | 0 | 0 | 1,799 | yes | yes |

`Outputs` is the sum of whole artifacts and semantic contributions declared by the payload. Zero is expected for reference-only Python Coding and internal Standard Bundle Authoring.

## Finding resolved during review

Python Tooling was the only agent summary without an explicit link back to its canonical README. Because catalog 5 has not been published, the payload contract permits this pre-release correction in place. The summary now carries the same canonical-authority statement as the other packages; its resource, family, catalog, activation-fixture, and projection digests were refreshed together.

`test_catalog_agent_summaries_link_to_their_canonical_standard` now enforces the backlink and authority statement across every catalog entry, preventing the gap from recurring when packages are added or revised.

## Verification evidence

The following checks passed on 2026-07-12:

- `uv run pytest tests/package_contract` — 494 tests;
- `project-standards standards validate-packages --root . --json` — no findings;
- `project-standards standards validate-graph --root . --require-all-manifests --json` — no findings;
- generated catalog, package schemas, and installed payload projection freshness checks;
- the retained-document local-link audit — 1,924 links across 305 source Markdown files, zero failures;
- Prettier, markdownlint, Ruff format, and Ruff lint on the changed surfaces.

## Conclusion

Catalog 5 exposes enough validated identity, lifecycle, capability, relationship, resource, provider, schema, summary, and output metadata for a future MCP layer to remain generic. Step 07 may consume this review as package-readiness evidence; the separate readiness report must still confirm repository-wide graph, documentation, migration, compatibility, and housekeeping status before SPEC-MS01 begins.
