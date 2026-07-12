# Project Specifications

This directory is the durable home for Project Specification Standard documents that the repository keeps and maintains. Historical design and brainstorming artifacts remain under `docs/superpowers/specs/`; only active implementation plans remain under `docs/superpowers/plans/`.

## Current specifications

| Specification | Status | Role |
| --- | --- | --- |
| [SPEC-MT01 — Meta-Repository MCP Readiness](2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md) | draft rev 0.7; Step 07 open | Readiness gate for the catalog-backed MCP program |
| [SPEC-RD01 — MCP Enablement Roadmap](2026-07-07-project-standards-mcp-enablement-roadmap-spec.md) | draft; blocked by SPEC-MT01 | Sequencing from readiness through MCP delivery |
| [SPEC-MS01 — MCP Server Implementation](2026-07-07-project-standards-mcp-server-implementation-spec.md) | draft; blocked by SPEC-MT01 | Thin, local, read-only-first MCP server |
| [SPEC-DPEY — Agent Handoff Standard Package](2026-07-09-agent-handoff-standard-package.md) | approved rev 0.5; implemented | Catalog 5 Agent Handoff package and retirement gates |
| [SPEC-CP01 — Consumer Standards Control Plane](2026-07-10-consumer-standards-control-plane-spec.md) | approved rev 0.7; implemented except release-cut migration | Catalog/config/lock/reconciliation control plane |
| [SPEC-BA02 — Standard Bundle Authoring V2](2026-07-10-standard-bundle-authoring-v2-spec.md) | approved rev 0.8; implemented | Immutable family/payload authoring contract |

## Future maintained specifications

| Specification set | Status | Release relationship |
| --- | --- | --- |
| [Usage Documentation Site](future/usage-documentation-site/README.md) | draft seven-spec set plus index; formal review pending | Dedicated post-v5 package program |

## Archive

| Specification | Status | Reason retained |
| --- | --- | --- |
| [SPEC-BA01 — Standard Bundle Authoring](archive/2026-07-07-standard-bundle-authoring-standard.md) | superseded by SPEC-BA02 | Versioned requirements and implementation history |

Every specification listed here is gated by `project-standards spec validate` and `spec lint`. Moving a document requires updating `.project-standards.yml`, this index, and all repository references in the same change.
