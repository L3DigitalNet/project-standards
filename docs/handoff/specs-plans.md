# Specs And Plans

**Last updated:** 2026-07-07

> **Plan prune (2026-07-05, v4.0.0 prep):** implemented plan docs and the `v1.1.0/` planning archive were deleted — their designs live on as the durable record in `docs/superpowers/specs/`. Only the still-pending `check` drift plan remains under `docs/superpowers/plans/`. Rows below point to the retained specs; each design's implementation status (shipped release / commit) is recorded in `CHANGELOG.md` and `docs/superpowers/specs/README.md`.

| Item | Path | Status |
| --- | --- | --- |
| MCP meta-repo readiness prep — **SPEC-MT01** | `docs/superpowers/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md` | **draft** (Full spec; ingested 2026-07-07). Prerequisite readiness work; establishes the independent-standard-package contract. Blocks SPEC-RD01/MS01. `spec validate`/`lint` green |
| MCP enablement roadmap — **SPEC-RD01** | `docs/superpowers/specs/2026-07-07-project-standards-mcp-enablement-roadmap-spec.md` | **draft** (Full spec; ingested 2026-07-07). Sequencing roadmap; depends on SPEC-MT01; gates MCP impl behind the readiness gate |
| MCP server implementation — **SPEC-MS01** | `docs/superpowers/specs/2026-07-07-project-standards-mcp-server-implementation-spec.md` | **draft** (Full spec; ingested 2026-07-07). Thin/local/read-only-first MCP server. **BLOCKED** until SPEC-MT01 readiness gate passes. Depends on SPEC-MT01 + SPEC-RD01 |
| MCP specification reference pack | `docs/superpowers/research/2026-07-07-project-standards-mcp-specification-reference-pack.md` | supporting material (`doc_type: research`) for the three MCP specs — **not** an implementation contract. Recheck MCP protocol/SDK versions before SPEC-MS01 MS-0 (REF-OQ-003) |
| SPEC-MT01 Step 00 — Baseline inventory | `docs/superpowers/research/2026-07-07-spec-mt01-baseline-inventory.md` | **done 2026-07-07** — factual map of current standards/registry/bundles/CLI/workflows/tests + the grounded readiness-gap list feeding Steps 01–07. First completed v5.0.0 work item |
| SPEC-MT01 Step 01 — ADR foundation | `docs/adr/` (`adr-0001`…`adr-0013` + `README.md` index) | **done + accepted 2026-07-07** — 13 meta-repo readiness ADRs, now `status: active` (MADR accepted); `docs/adr/**` dogfood-wired into frontmatter/id/section validation. SPEC-MS01 server ADRs deferred to the server phase |
| SPEC-MT01 Step 02 — Standard Bundle Authoring (spec) | `docs/superpowers/specs/2026-07-07-standard-bundle-authoring-standard.md` (**SPEC-BA01**, Light, rev 0.6) | **Implemented 2026-07-07** (bundle shipped; §17.1 DoD ticked, owner acceptance pending). Codex spec-review converged r2; the meta-standard's contract, brainstormed then scaffolded via `spec new` (dogfoods the Project Specification Standard). Internal/reference; doc-only (schema deferred to Step 03) |
| SPEC-MT01 Step 02 — Standard Bundle Authoring (plan) | `docs/superpowers/plans/2026-07-07-standard-bundle-authoring-standard.md` | **IMPLEMENTED 2026-07-07** (executing-plans, inline; `fbaf49d`…`83fe5fd`) — all 5 tasks: bundle authored (`standards/standard-bundle-authoring/` README + worked `standard.toml` + template) + repo-facing maps reconciled; CR-004 machine-layer diff empty; SPEC-BA01 §17.1 DoD ticked (owner acceptance pending); full gate green (868 tests). Codex plan-review had converged r3 before execution; audits in `docs/codex-reviews/` |
| CLI Documentation standard design | `docs/superpowers/specs/2026-07-07-cli-documentation-standard-design.md` | approved (codex r3); **RELEASED in `v4.3.0`** (2026-07-07) |
| CLI Documentation standard plan | `docs/superpowers/plans/2026-07-07-cli-documentation-standard.md` | implemented via SDD — all 13 tasks complete; **RELEASED in `v4.3.0`** (2026-07-07) |
| Markdown-Tooling formatter authority (issue #3 F5 — Spec B) design | `docs/superpowers/specs/2026-07-06-markdown-tooling-formatter-authority-design.md` | **RELEASED in `v4.2.0`** (opt-in reusable Prettier gate; `markdown_tooling 1.1`; DEC-9→DEC-10) |
| Markdown-Tooling formatter authority (Spec B) plan | `docs/superpowers/plans/2026-07-06-markdown-tooling-formatter-authority.md` | **RELEASED in `v4.2.0`** — 10-task TDD plan implemented via executing-plans + scoped opus review (0 Critical/Important); + `tests/coherence/` tool |
| spec-validator external references (issue #3 F1–F4) design | `docs/superpowers/specs/2026-07-06-spec-validator-external-references-design.md` | **RELEASED in `v4.1.0`** (`spec.reference_prefixes` + token hygiene) |
| spec-validator external references plan | `docs/superpowers/plans/2026-07-06-spec-validator-external-references.md` | **RELEASED in `v4.1.0`** (`1341dc0..84c0054`, whole-branch review READY-TO-MERGE) |
| project-spec tooling Spec #1 design | `docs/superpowers/specs/2026-07-04-project-spec-tooling-design.md` | approved (codex r2); plan implemented (`2a6c4c0`) |
| project-spec tooling Spec #2 design (`new` scaffold) | `docs/superpowers/specs/2026-07-04-project-spec-tooling-spec2-design.md` | approved (codex r2); plan implemented (`8d48c22`) |
| project-spec tooling Spec #3 design (`upgrade` tier promotion) | `docs/superpowers/specs/2026-07-05-project-spec-tooling-spec3-design.md` | approved (codex r3); plan implemented (`testing`) |
| Frontmatter suite (format/references/fix) design | `docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md` | approved (codex r3); plan implemented (shipped 3.0.0) |
| `check` drift design | `docs/superpowers/specs/2026-06-08-check-drift-design.md` | approved (codex spec-review converged r3) |
| `check` drift plan | `docs/superpowers/plans/2026-06-08-check-drift.md` | written; implementation HELD (targets 2.2.0) — **only surviving plan doc** |
| `adopt` CLI design | `docs/superpowers/specs/2026-06-08-adopt-cli-design.md` | approved (codex r6); plan implemented (shipped 3.0.0) |
| Markdown Tooling Standard design | `docs/superpowers/specs/2026-06-06-markdown-tooling-standard-design.md` | approved (audit r3); plan released (`v2.0.0`) |
| Per-standard versioning design | `docs/superpowers/specs/2026-06-06-per-standard-versioning-design.md` | approved (audit r2); plan released (`v2.0.0`) |
| Standards bundle restructure design | `docs/superpowers/specs/2026-06-06-standards-bundle-restructure-design.md` | approved; plan released (`v2.0.0`) |
| Python Tooling SSOT adoption design | `docs/superpowers/specs/2026-06-06-python-tooling-ssot-adoption-design.md` | approved; plan released (`v2.0.0`) |
| Handoff v3 migration design | `docs/superpowers/specs/2026-06-05-handoff-v3-migration-design.md` | approved; plan implemented |
| Linting/formatting stack (DEC-1…9 trail) | `docs/superpowers/specs/2026-06-04-linting-formatting-stack.md` | implemented (1.3.0) |

## Storage

- Specs and design artifacts: `docs/superpowers/specs/`
- Research / reference support docs: `docs/superpowers/research/` (chosen 2026-07-07 for the MCP reference pack; `docs/research/` was avoided because its `index.md` is qdev-generated)
- Implementation plans: `docs/superpowers/plans/` (only the pending `check` drift plan remains after the 2026-07-05 prune)
- `docs/superpowers/specs/README.md` — human-facing index of the specs directory (own status table, kept separate from this pointer table)
