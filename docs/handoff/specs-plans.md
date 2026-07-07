# Specs And Plans

**Last updated:** 2026-07-07

> **Plan prune (2026-07-05, v4.0.0 prep):** implemented plan docs and the `v1.1.0/` planning archive were deleted — their designs live on as the durable record in `docs/superpowers/specs/`. Only the still-pending `check` drift plan remains under `docs/superpowers/plans/`. Rows below point to the retained specs; each design's implementation status (shipped release / commit) is recorded in `CHANGELOG.md` and `docs/superpowers/specs/README.md`.

| Item | Path | Status |
| --- | --- | --- |
| CLI Documentation standard design | `docs/superpowers/specs/2026-07-07-cli-documentation-standard-design.md` | approved (codex r3); plan implemented via SDD, executing on `testing` |
| CLI Documentation standard plan | `docs/superpowers/plans/2026-07-07-cli-documentation-standard.md` | executing via SDD (Task 12 of 13) |
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
- Implementation plans: `docs/superpowers/plans/` (only the pending `check` drift plan remains after the 2026-07-05 prune)
- `docs/superpowers/specs/README.md` — human-facing index of the specs directory (own status table, kept separate from this pointer table)
