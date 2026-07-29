# Project Specifications

This directory is the durable home for Project Specification Standard documents that the repository keeps and maintains. Historical design and brainstorming artifacts remain under `docs/specs/archive/`; only active implementation plans remain under `docs/plans/`.

## Current specifications

| Specification | Status | Role |
| --- | --- | --- |
| [SPEC-MT01 — Meta-Repository MCP Readiness](2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md) | approved and locked rev 1.4; Opus spec review converged; complete historical contract | Historical Step 07 contract plus current 5.9.0 successor-state reconciliation |
| [SPEC-RD01 — MCP Enablement Roadmap](2026-07-07-project-standards-mcp-enablement-roadmap-spec.md) | approved and locked rev 1.6; Step 09 decision gate closed 2026-07-28 | Completed Step 08 documentation gate and Step 09-through-18 sequencing |
| [SPEC-MS01 — MCP Server Implementation](2026-07-07-project-standards-mcp-server-implementation-spec.md) | approved and locked rev 1.3; T1 decision gate closed 2026-07-28; implementation starting | SDK-independent services plus thin local read-only stdio adapter; boundary and transport decisions recorded in ADR 0025 and ADR 0026 |
| [SPEC-DPEY — Agent Handoff Standard Package](2026-07-09-agent-handoff-standard-package.md) | approved rev 0.8; implementation complete; retirement pending | V1 baseline plus accepted Catalog 5 package `1.1` supersession and Task 18 retirement gates |
| [SPEC-CP01 — Consumer Standards Control Plane](2026-07-10-consumer-standards-control-plane-spec.md) | approved rev 0.15; implemented | Catalog/config/lock/reconciliation control plane; declared-path provider correction, root dogfood, and FR-037/FR-038 evidence pass |
| [SPEC-BA02 — Standard Bundle Authoring V2](2026-07-10-standard-bundle-authoring-v2-spec.md) | approved rev 0.15; implemented | Immutable family/payload authoring contract including bounded direct package-config transforms |
| [SPEC-VAIC — V5 Adoption Integrity Correction Train](2026-07-26-v5-adoption-integrity-correction-train-spec.md) | approved rev 0.12; implemented and released in 5.9.0 | Issues #32 and #35-#49, immutable successors, exact-candidate qualification, and closed-issue regression preservation |
| [SPEC-VFCT — V5 Validation Fidelity Correction Train](2026-07-27-v5-validation-fidelity-correction-train-spec.md) | approved rev 0.3; implemented in 5.10.0 | Issues #50-#69: shared spec-engine, `standards show`, and control-plane planning loosening fixes (including #66's create-only removal guard), four new successor payloads, and the Catalog 5 default advance shipped in v5.10.0 |

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
