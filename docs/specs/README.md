# Project Specifications

This directory is the durable home for Project Specification Standard documents that the repository keeps and maintains. Historical design and brainstorming artifacts remain under `docs/specs/archive/`; only active implementation plans remain under `docs/plans/`.

## Current specifications

| Specification | Status | Role |
| --- | --- | --- |
| [SPEC-MT01 — Meta-Repository MCP Readiness](2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md) | approved rev 0.9; complete | Step 07 passed with no blocking gaps; evidence is in [`docs/mcp-readiness.md`](../mcp-readiness.md) |
| [SPEC-RD01 — MCP Enablement Roadmap](2026-07-07-project-standards-mcp-enablement-roadmap-spec.md) | draft rev 0.6; Step 08 deferred | Sequencing from readiness through MCP delivery |
| [SPEC-MS01 — MCP Server Implementation](2026-07-07-project-standards-mcp-server-implementation-spec.md) | draft rev 0.5; implementation deferred | Thin, local, read-only-first MCP server |
| [SPEC-DPEY — Agent Handoff Standard Package](2026-07-09-agent-handoff-standard-package.md) | approved rev 0.6; implementation complete; retirement pending | V1 baseline plus accepted Catalog 5 package `1.1` supersession and Task 18 retirement gates |
| [SPEC-CP01 — Consumer Standards Control Plane](2026-07-10-consumer-standards-control-plane-spec.md) | approved rev 0.13; implemented | Catalog/config/lock/reconciliation control plane; declared-path provider correction, root dogfood, and FR-037/FR-038 evidence pass |
| [SPEC-BA02 — Standard Bundle Authoring V2](2026-07-10-standard-bundle-authoring-v2-spec.md) | approved rev 0.13; implemented | Immutable family/payload authoring contract; FR-028 checklist interpretation clarified without payload changes |

## Future maintained specifications

| Specification set | Status | Release relationship |
| --- | --- | --- |
| [Usage Documentation Site](future/usage-documentation-site/README.md) | draft seven-spec set plus index; formal review pending | Dedicated post-v5 package program |

## Archive

| Specification | Status | Reason retained |
| --- | --- | --- |
| [SPEC-BA01 — Standard Bundle Authoring](archive/2026-07-07-standard-bundle-authoring-standard.md) | superseded by SPEC-BA02 | Versioned requirements and implementation history |

[`archive/`](archive/README.md) also holds the historical design documents for released features; its own index covers them. Archived design documents are informal records outside the `spec validate` scope.

Every specification listed here is gated by `project-standards spec validate` and `spec lint`. `.standards/config.toml` is the sole active selection authority; moving a maintained specification requires updating it, this index, and repository references in the same change.
