# Specification and Design Archive

Superseded specifications and informal design records for `project-standards`, including owner-approved designs awaiting implementation. Maintained Project Specification Standard documents live in [`../`](../README.md). Design documents here are not project-spec-conformant and are outside the `spec validate` scope by design.

## Superseded specifications

| Date | Spec | Status | What it covers |
| --- | --- | --- | --- |
| 2026-07-07 | [SPEC-BA01 — Standard Bundle Authoring](2026-07-07-standard-bundle-authoring-standard.md) | superseded by SPEC-BA02 | Versioned requirements and implementation history for the V1 authoring contract |

## Design documents

| Date | Design | Outcome | What it covers |
| --- | --- | --- | --- |
| 2026-06-04 | [Linting / Formatting Stack](2026-06-04-linting-formatting-stack.md) | implemented (shipped in v2.0.0; originally targeted an unreleased 1.3.0) | Research doc pinning the exact linting + formatting stack for frontmatter validation and the ADR/MADR standard |
| 2026-06-05 | [Handoff v3 Migration](2026-06-05-handoff-v3-migration-design.md) | implemented | Migrate `project-standards` to the handoff-system-v3 `docs/handoff/` session-state layout |
| 2026-06-06 | [Python Tooling SSOT Adoption](2026-06-06-python-tooling-ssot-adoption-design.md) | released (v2.0.0) | Adopt the Python Tooling SSOT Standard in this repo — `uv` build backend, `src/` layout, `basedpyright`, `pip-audit` |
| 2026-06-06 | [Standards Bundle Restructure](2026-06-06-standards-bundle-restructure-design.md) | released (v2.0.0) | Per-standard bundle directories under `src/project_standards/bundles/` replacing the old flat layout |
| 2026-06-06 | [Per-Standard Versioning](2026-06-06-per-standard-versioning-design.md) | released (v2.0.0) | Per-standard contract versions (`frontmatter`, `adr`, `python_tooling`, `markdown_tooling`) in `registry.json` |
| 2026-06-06 | [Markdown Tooling Standard](2026-06-06-markdown-tooling-standard-design.md) | released (v2.0.0) | Define the Markdown Tooling governed standard (markdownlint, Prettier, EditorConfig) as a new adoptable bundle |
| 2026-06-08 | [Adopt CLI](2026-06-08-adopt-cli-design.md) | shipped (3.0.0) | The `project-standards adopt \| list` CLI — packaged scaffolder for materializing standard artifacts into target repos |
| 2026-06-08 | [Check / Drift Detection](2026-06-08-check-drift-design.md) | superseded by the CP01/V2 control plane | The v2.2 `project-standards check` command — drift detection between adopted artifacts and the canonical bundle |
| 2026-07-04 | [Project-Spec Tooling — Spec #1](2026-07-04-project-spec-tooling-design.md) | implemented | The `project-standards spec validate \| lint \| extract \| next` read-only commands over a shared registry core |
| 2026-07-04 | [Project-Spec Tooling — Spec #2](2026-07-04-project-spec-tooling-spec2-design.md) | implemented | The `spec new` guarded generative scaffold command |
| 2026-07-05 | [Project-Spec Tooling — Spec #3](2026-07-05-project-spec-tooling-spec3-design.md) | implemented | The `spec upgrade` tier-promotion command |
| 2026-07-06 | [Spec-Validator External References](2026-07-06-spec-validator-external-references-design.md) | released (v4.1.0) | `spec.reference_prefixes` + token hygiene (issue #3 F1–F4) |
| 2026-07-06 | [Markdown-Tooling Formatter Authority (F5, Spec B)](2026-07-06-markdown-tooling-formatter-authority-design.md) | released (v4.2.0) | Opt-in reusable repo-wide Prettier gate (`format.yml` + caller) superseding DEC-9; `markdown_tooling 1.1` |
| 2026-07-07 | [CLI Documentation Standard](2026-07-07-cli-documentation-standard-design.md) | released (v4.3.0) | The CLI Documentation standard bundle |
| 2026-07-07 | [Standard Manifest Schema Model](2026-07-07-standard-manifest-schema-model-design.md) | implemented (2026-07-08) | The `standard.toml` Pydantic model, loader, generated JSON Schema, and fixture corpus (SPEC-MT01 Step 03) |
| 2026-07-10 | [Pre-Step-07 Readiness Remediation](2026-07-10-pre-step-07-readiness-remediation-design.md) | implemented (2026-07-10) | Reconcile SPEC-MT01 evidence and v5 docs, fix bug-index shape targeting, add repository-only graph/catalog CI |
| 2026-07-10 | [FR-013 Agent-Summary Coverage](2026-07-10-fr-013-agent-summary-coverage-design.md) | implemented (2026-07-10) | Nine compact summaries, 3,000-byte enforcement, generated catalog URIs |
| 2026-07-10 | [Root-Artifact Ownership and Semantic Composition](2026-07-10-root-artifact-ownership-semantic-composition-design.md) | adopted by ADR 0023 | Consumer-owned shared root containers with typed package-owned semantic units composed by syntax-preserving adapters |
| 2026-07-12 | [Python Tooling Checker-Table Materialization](2026-07-12-python-tooling-checker-table-materialization-design.md) | implemented (5.0.x) | Canonical checker selection, exact `pyright==1.1.411`, conditional payload rendering, migration/lifecycle contracts |
| 2026-07-19 | [Project Standards Review Remediation](2026-07-19-project-standards-review-remediation-design.md) | owner-approved; implementation pending | Evidence-based final dispositions and compatibility-first 5.1.0 corrections for F-001 through F-100 |
| 2026-07-22 | [V5 Migration Correction Train](2026-07-22-v5-migration-correction-train-design.md) | released (5.5.0) | Versioned corrections for semantic V4 workflow migration, empty Project Spec corpora, and consumer-only Agent Handoff size budgets |
| 2026-07-22 | [V5 Upgrade Usability Correction Train](2026-07-22-v5-upgrade-usability-correction-train-design.md) | released (5.6.0) | Python Tooling 1.6 additional source roots, enriched conflict diagnostics with governing-option pointers, migration preview exit-code contract, and upgrade-doc corrections (issues #20–#23) |
| 2026-07-22 | [V5 Managed-Edit Fidelity Correction Train](2026-07-22-v5-managed-edit-fidelity-correction-train-design.md) | released (5.7.0) | Python Tooling 1.7 per-root coverage scoping for `additional_source_roots` and anchored TOML managed-region comment preservation (issues #24–#25) |

Research and reference packs live in [`../../research/`](../../research/index.md). Active implementation plans live in [`../../plans/`](../../plans/); completed plans are deleted.
