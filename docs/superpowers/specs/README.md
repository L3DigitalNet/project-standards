# Design Specs

Design documents and brainstorming outputs for `project-standards`. Each spec captures the problem, options considered, and the chosen approach before implementation begins.

| Date | Spec | Status | What it covers |
| --- | --- | --- | --- |
| 2026-06-04 | [Linting / Formatting Stack](2026-06-04-linting-formatting-stack.md) | implemented (v1.3.0) | Research doc pinning the exact linting + formatting stack for frontmatter validation and the upcoming ADR/MADR standard |
| 2026-06-05 | [Handoff v3 Migration](2026-06-05-handoff-v3-migration-design.md) | approved | Migrate `project-standards` to the handoff-system-v3 `docs/handoff/` session-state layout |
| 2026-06-06 | [Python Tooling SSOT Adoption](2026-06-06-python-tooling-ssot-adoption-design.md) | approved | Adopt the Python Tooling SSOT Standard in this repo — `uv` build backend, `src/` layout, `basedpyright`, `pip-audit` |
| 2026-06-06 | [Standards Bundle Restructure](2026-06-06-standards-bundle-restructure-design.md) | approved | Per-standard bundle directories under `src/project_standards/bundles/` replacing the old flat layout |
| 2026-06-06 | [Per-Standard Versioning](2026-06-06-per-standard-versioning-design.md) | approved | Per-standard contract versions (`frontmatter`, `adr`, `python_tooling`, `markdown_tooling`) in `registry.json` |
| 2026-06-06 | [Markdown Tooling Standard](2026-06-06-markdown-tooling-standard-design.md) | approved | Define the Markdown Tooling governed standard (markdownlint, Prettier, EditorConfig) as a new adoptable bundle |
| 2026-06-08 | [Adopt CLI](2026-06-08-adopt-cli-design.md) | approved | The `project-standards adopt \| list` CLI — packaged scaffolder for materializing standard artifacts into target repos |
| 2026-06-08 | [Check / Drift Detection](2026-06-08-check-drift-design.md) | approved | The `project-standards check` command — detect drift between adopted artifacts and the canonical bundle |
| 2026-07-04 | [Project-Spec Tooling — Spec #1](2026-07-04-project-spec-tooling-design.md) | approved | The `project-standards spec validate \| lint \| extract \| next` read-only commands over a shared registry core; retires `check_specs.py` |
| 2026-07-06 | [Markdown-Tooling Formatter Authority (F5, Spec B)](2026-07-06-markdown-tooling-formatter-authority-design.md) | codex-converged (r5) | Ship an opt-in reusable repo-wide Prettier gate (`format.yml` + caller), superseding DEC-9; document formatter authority + `proseWrap`; add a repo-local config-coherence tool. Additive ⇒ MINOR (`markdown_tooling 1.1`) |
| 2026-07-07 | [MCP Meta-Repo Readiness — SPEC-MT01](2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md) | draft (Full spec) | Prerequisite: make the meta-repo manifest-driven + graph-validated so a future MCP server stays thin. Establishes the independent-standard-package contract (groups = recommendations, never hidden hard dependencies). Blocks SPEC-RD01/MS01 |
| 2026-07-07 | [MCP Enablement Roadmap — SPEC-RD01](2026-07-07-project-standards-mcp-enablement-roadmap-spec.md) | draft (Full spec) | Ordered sequencing from meta-repo readiness → MCP phases. Depends on SPEC-MT01; MCP implementation must not start until the readiness gate passes |
| 2026-07-07 | [MCP Server Implementation — SPEC-MS01](2026-07-07-project-standards-mcp-server-implementation-spec.md) | draft (Full spec) | Thin, local, read-only-first, manifest-driven MCP access layer over the standards graph — not a second standards implementation. Depends on SPEC-MT01 + SPEC-RD01; BLOCKED until the readiness gate passes |

> The three `SPEC-*` rows above are real Project Specification documents (project-spec frontmatter, gated by `spec validate`/`lint`), unlike the frontmatter-less design/brainstorming docs elsewhere in this table. Their supporting reference pack lives at [`../research/2026-07-07-project-standards-mcp-specification-reference-pack.md`](../research/2026-07-07-project-standards-mcp-specification-reference-pack.md).

Implementation plans for these specs live in [`../plans/`](../plans/).
