# Project Specifications

This directory is the durable home for Project Specification Standard documents that the repository keeps and maintains. Historical design and brainstorming artifacts remain under `docs/specs/archive/`; only active implementation plans remain under `docs/plans/`.

## Current specifications

| Specification | Status | Role |
| --- | --- | --- |
| [SPEC-MT01 — Meta-Repository MCP Readiness](2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md) | approved and locked rev 1.5; Opus spec review converged; complete historical contract | Historical Step 07 contract plus current 5.9.0 successor-state reconciliation |
| [SPEC-RD01 — MCP Enablement Roadmap](2026-07-07-project-standards-mcp-enablement-roadmap-spec.md) | approved and locked rev 1.8; read-only server delivered in 5.12.0 | Completed Step 08-through-14 read-only delivery; controlled-write and remote phases remain separately approved future work |
| [SPEC-MS01 — MCP Server Implementation](2026-07-07-project-standards-mcp-server-implementation-spec.md) | approved and locked rev 1.6; T1 decision gate closed 2026-07-28; `OQ-005` resolved 2026-07-30 at the T11 client/documentation gate; §9 field names and §10.3 `EC-005` wording reconciled to the implemented contract 2026-07-31 at the T12 final gate | SDK-independent services plus thin local read-only stdio adapter; boundary and transport decisions recorded in ADR 0025 and ADR 0026 |
| [SPEC-DPEY — Agent Handoff Standard Package](2026-07-09-agent-handoff-standard-package.md) | approved rev 1.2; released package version is whatever Catalog 5 currently marks `role = "default"` for `agent-handoff` — see [`docs/handoff/deployed.md`](../handoff/deployed.md); T32 retirement closeout completed 2026-08-04 | V1 baseline plus Catalog 5 precedence, the adaptive SessionStart launcher successor, and the completed T32 operational closeout |
| [SPEC-CP01 — Consumer Standards Control Plane](2026-07-10-consumer-standards-control-plane-spec.md) | approved rev 0.16; implemented | Catalog/config/lock/reconciliation control plane; declared-path provider correction, root dogfood, and FR-037/FR-038 evidence pass |
| [SPEC-BA02 — Standard Bundle Authoring V2](2026-07-10-standard-bundle-authoring-v2-spec.md) | approved rev 0.16; implemented | Immutable family/payload authoring contract including bounded direct package-config transforms |
| [SPEC-VAIC — V5 Adoption Integrity Correction Train](2026-07-26-v5-adoption-integrity-correction-train-spec.md) | approved rev 0.13; implemented and released in 5.9.0 | Issues #32 and #35-#49, immutable successors, exact-candidate qualification, and closed-issue regression preservation |
| [SPEC-VFCT — V5 Validation Fidelity Correction Train](2026-07-27-v5-validation-fidelity-correction-train-spec.md) | approved rev 0.4; implemented in 5.10.0 | Issues #50-#69: shared spec-engine, `standards show`, and control-plane planning loosening fixes (including #66's create-only removal guard), four new successor payloads, and the Catalog 5 default advance shipped in v5.10.0 |
| [SPEC-GHW1 — GitHub Workflow Standard Package](2026-08-06-github-workflow-package-spec.md) | approved rev 1.38; implemented and released, `github-workflow` currently at 1.8 | Org-schema-driven `gh-workflow` tool and skill; the 1.7 target behavior plus the DEV-032 risk-label correction shipped in 1.8 |
| [SPEC-055C — Project Specification Preservation-First Conversion](2026-08-01-project-spec-conversion-plan-input.md) | approved rev 0.2; issue #55 | Deterministic mapping and digest-bound apply for preservation-first Project Specification conversion |

## Future maintained specifications

| Specification set | Status | Release relationship |
| --- | --- | --- |
| [SPEC-GSF3 — Durable Document References Optional Tooling](2026-07-31-durable-document-references-optional-tooling-spec.md) | draft rev 0.2; currency-audited 2026-08-27 | Optional meta-repository tooling for canonical spec/ADR references, validation, and guarded reconciliation |
| [Usage Documentation Site](usage-documentation-site/README.md) | draft seven-spec set plus index; formal review pending | Dedicated post-v5 package program |

## Active design and decision inputs

These are informal design records, not Project Specification documents: they carry `doc_type: decision`, are outside the `spec validate` scope, and stay in this directory rather than `archive/` because `archive/` holds superseded and historical records only. A document moves there once its outcome is settled.

| Date | Document | Status | What it covers |
| --- | --- | --- | --- |
| 2026-08-01 | [Project Specification conformance linting design](2026-08-01-project-spec-conformance-plan-input.md) | active | Plan input for conformance linting over the maintained specification corpus |
| 2026-08-02 | [Usage Documentation Site V2 design](2026-08-02-usage-documentation-site-v2-design.md) | active | Design input behind the seven-spec Usage Documentation Site set above |
| 2026-08-06 | [github-workflow standard package design](2026-08-06-github-workflow-package-design.md) | active | Design input consumed by SPEC-GHW1; supersedes the preliminary administration design in `archive/` |
| 2026-08-16 | [project-toolbox standard package design](2026-08-16-project-toolbox-package-design.md) | active | Design record for the `project-toolbox` package family |

## Archive

| Specification | Status | Reason retained |
| --- | --- | --- |
| [SPEC-BA01 — Standard Bundle Authoring](archive/2026-07-07-standard-bundle-authoring-standard.md) | superseded by SPEC-BA02 | Versioned requirements and implementation history |

[`archive/`](archive/README.md) also holds the historical design documents for released features; its own index covers them. Archived design documents are informal records outside the `spec validate` scope.

Every specification listed here is gated by `project-standards spec validate` and `spec lint`. `.standards/config.toml` is the sole active selection authority; moving a maintained specification requires updating it, this index, and repository references in the same change.
