# Project Status

## Current snapshot

- Project Standards 5.0.1 is the current patch release at `0390b9e`; signed `v5.0.1` and moving `v5` refs and GitHub release assets are live.
- `main` includes the follow-up Node dependency setup fix at `4d81602`.
- Catalog 5 contains seven consumer packages plus reference-only Python Coding 0.5 and internal Standard Bundle Authoring 2.0.
- The repository dogfoods the unified `.standards/` control plane; legacy `.project-standards.yml` authority is absent.
- The retained repository gate is direct: ordinary tests with coverage, the catalog-derived compatibility matrix on four xdist workers, performance tests, and a coverage report.
- Release-only replay, retained self-referential evidence, the custom test orchestrator, and their frozen predecessor fixture have been removed as unnecessary release-preparation machinery.
- Generic consumer-owned workflow support and optional parallel/subprocess coverage remain part of the immutable Python Tooling 1.1 package API; this repository simply no longer selects parallel coverage.
- Core control-plane, package, migration, source/wheel compatibility, composition, performance, formatting, typing, dependency, and documentation checks remain required.
- Verification claims are command-based; rerun the retained gate against current HEAD before claiming completion.
- MCP readiness Step 07 is complete. MCP server implementation still waits for its separately governed protocol and SDK refresh.
- Agent Handoff consumer retirement and the future `project-toolbox` and `agent-managed-repo` packages remain post-v5 work.
- Durable implementation history remains in `docs/handoff/sessions/2026-07.md`.
