# Project Status

## Current snapshot

- Project Standards 5.0.2 is the current patch release at `c731955`; signed `v5.0.2` and moving `v5` refs and GitHub release assets are live.
- Catalog 5 contains seven consumer packages plus reference-only Python Coding 0.5 and internal Standard Bundle Authoring 2.1 (2.0 remains advertised as released history; 2.1 shipped in 5.0.2 with its corrected SPEC-BA02 pointer).
- The accepted implementation-review corrections target 5.1.0. All consumer surfaces require Python 3.14 or newer, and remediation is limited to verified review corrections.
- The repository dogfoods the unified `.standards/` control plane; legacy `.project-standards.yml` authority is absent.
- The retained repository gate is direct: ordinary tests with coverage, the catalog-derived compatibility matrix on four xdist workers, performance tests, and a coverage report.
- Release-only replay, retained self-referential evidence, the custom test orchestrator, and their frozen predecessor fixture have been removed as unnecessary release-preparation machinery.
- Generic consumer-owned workflow support and optional parallel/subprocess coverage remain part of the immutable Python Tooling 1.1 package API; this repository simply no longer selects parallel coverage.
- Core control-plane, package, migration, source/wheel compatibility, composition, performance, formatting, typing, dependency, and documentation checks remain required.
- Verification claims are command-based; rerun the retained gate against current HEAD before claiming completion.
- MCP readiness Step 07 is complete. MCP server implementation still waits for its separately governed protocol and SDK refresh.
- Agent Handoff consumer retirement and the future `project-toolbox` and `agent-managed-repo` packages remain post-v5 work.
- Housekeeping 2026-07-19: `docs/superpowers/` retired (designs → `docs/specs/archive/`, research → `docs/research/`, active plan → `docs/plans/`); completed plans, review audits, and `docs/codex-reviews/` deleted.
- Durable implementation history remains in `docs/handoff/sessions/2026-07.md`.
