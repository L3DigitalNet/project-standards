# Project Specifications

This directory is the durable home for Project Specification Standard documents that the repository keeps and maintains. Historical design and brainstorming artifacts remain under `docs/superpowers/specs/`; only active implementation plans remain under `docs/superpowers/plans/`.

## Current specifications

| Specification | Status | Role |
| --- | --- | --- |
| [SPEC-MT01 — Meta-Repository MCP Readiness](2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md) | approved rev 0.9; Step 07 passed | Completed readiness gate; evidence is in [`docs/mcp-readiness.md`](../mcp-readiness.md) |
| [SPEC-RD01 — MCP Enablement Roadmap](2026-07-07-project-standards-mcp-enablement-roadmap-spec.md) | draft rev 0.6; Step 08 deferred | Sequencing from readiness through MCP delivery |
| [SPEC-MS01 — MCP Server Implementation](2026-07-07-project-standards-mcp-server-implementation-spec.md) | draft rev 0.5; implementation deferred | Thin, local, read-only-first MCP server |
| [SPEC-DPEY — Agent Handoff Standard Package](2026-07-09-agent-handoff-standard-package.md) | approved rev 0.5; implemented | Catalog 5 Agent Handoff package and retirement gates |
| [SPEC-CP01 — Consumer Standards Control Plane](2026-07-10-consumer-standards-control-plane-spec.md) | approved rev 0.11; FR-037/FR-038 implementation evidence passes; live-root dogfood deferred to the atomic release commit | Catalog/config/lock/reconciliation control plane |
| [SPEC-BA02 — Standard Bundle Authoring V2](2026-07-10-standard-bundle-authoring-v2-spec.md) | approved rev 0.12; nine-family implementation and migration evidence passes | Immutable family/payload authoring contract |

## Future maintained specifications

| Specification set | Status | Release relationship |
| --- | --- | --- |
| [Usage Documentation Site](future/usage-documentation-site/README.md) | draft seven-spec set plus index; formal review pending | Dedicated post-v5 package program |

## Archive

| Specification | Status | Reason retained |
| --- | --- | --- |
| [SPEC-BA01 — Standard Bundle Authoring](archive/2026-07-07-standard-bundle-authoring-standard.md) | superseded by SPEC-BA02 | Versioned requirements and implementation history |

Every specification listed here is gated by `project-standards spec validate` and `spec lint`. Until Task 11 moves the root to V2, `.project-standards.yml` selects the corpus; afterward `.standards/config.toml` is the sole configuration authority. Moving a document requires updating the active configuration, this index, and all repository references in the same change.
