# Project Status

## Current snapshot

- Project Standards 5.1.0 is the current published release at `b69600d`; signed `v5.1.0`, the moving `v5` ref, and byte-verified GitHub release assets are live.
- Catalog 5 contains seven consumer packages plus reference-only Python Coding 0.6. The current defaults are ADR 1.2, Agent Handoff 1.2, CLI Documentation 1.2, Markdown Frontmatter 1.3, Markdown Tooling 1.3, Project Specification 1.2, and Python Tooling 1.2; internal Standard Bundle Authoring 2.2 is advertised but not consumer-selectable. Every superseded payload remains advertised.
- All 100 implementation-review findings have final dispositions: 96 accepted or adjusted corrections are implemented, four findings are closed with no change, and none is deferred or queued. All 14 consumer-documentation drift findings and both audit-discovered CLI defects are also corrected. Every consumer surface requires Python 3.14 or newer.
- The repository dogfoods the unified `.standards/` control plane; legacy `.project-standards.yml` authority is absent.
- The retained repository gate is direct: ordinary tests with coverage, the catalog-derived compatibility matrix on four xdist workers, performance tests, and a coverage report.
- Release-only replay, retained self-referential evidence, the custom test orchestrator, and their frozen predecessor fixture have been removed as unnecessary release-preparation machinery.
- Generic consumer-owned workflow support and optional parallel/subprocess coverage remain part of the immutable Python Tooling 1.2 package API; this repository simply no longer selects parallel coverage.
- Core control-plane, package, migration, source/wheel compatibility, composition, performance, formatting, typing, dependency, and documentation checks remain required.
- Verification claims are command-based; rerun the retained gate against current HEAD before claiming completion.
- MCP readiness Step 07 is complete. MCP server implementation still waits for its separately governed protocol and SDK refresh.
- Agent Handoff consumer retirement and the future `project-toolbox` and `agent-managed-repo` packages remain post-v5 work.
- A metadata-free agent adoption/update prompt is staged at `docs/working-adoption-prompt.md`; `docs/TODO.md` owns its next-release promotion.
- Housekeeping 2026-07-19: `docs/superpowers/` retired (designs → `docs/specs/archive/`, research → `docs/research/`, active plan → `docs/plans/`); completed plans, review audits, and `docs/codex-reviews/` deleted.
- Durable implementation history remains in `docs/handoff/sessions/2026-07.md`.
