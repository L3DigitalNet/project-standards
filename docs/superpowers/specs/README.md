# Design Archive

Historical design and brainstorming documents for `project-standards`. Maintained Project Specification Standard documents live in [`../../specs/`](../../specs/README.md).

The BA02 filename retained here is a compatibility symlink for an immutable catalog 5 payload link; its maintained target is `docs/specs/2026-07-10-standard-bundle-authoring-v2-spec.md`.

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
| 2026-07-10 | [Pre-Step-07 Readiness Remediation](2026-07-10-pre-step-07-readiness-remediation-design.md) | approved for implementation planning | Reconcile SPEC-MT01 evidence and v5 docs, fix Agent Handoff bug-index shape targeting, and add a repository-only graph/catalog workflow without changing the reusable Python Tooling gate |
| 2026-07-10 | [Root-Artifact Ownership and Semantic Composition](2026-07-10-root-artifact-ownership-semantic-composition-design.md) | approved (adversarial review converged in round 2) | Keep shared root containers consumer-owned while standards own typed keys, entries, blocks, or sections composed by syntax-preserving adapters without package precedence |

The MCP specification set's supporting reference pack remains at [`../research/2026-07-07-project-standards-mcp-specification-reference-pack.md`](../research/2026-07-07-project-standards-mcp-specification-reference-pack.md). Implementation plans remain in [`../plans/`](../plans/).
