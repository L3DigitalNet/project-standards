# Architecture

**Last updated:** 2026-07-12

## Components

- `standards/` holds the nine catalog 5 families, their manifests, package guidance, templates, examples, and index.
- `meta/` holds repository policy such as the release contract; it is not a governed package.
- `src/project_standards/` implements the CLI, validators, spec engine, catalog 5 control plane, projections, and bounded legacy compatibility.
- `tests/` covers source and wheel behavior, package compatibility, migrations, scale, and documentation coherence.
- `.github/workflows/` contains reusable consumer workflows and repository gates.
- `docs/specs/` is the validated, indexed home for maintained Project Specification documents.
- `docs/handoff/` is the repo-local Agent Handoff knowledge and session-state surface.

## Relationships

- Catalog 5 consumers select immutable packages in `.standards/config.toml`; one lock records exact payload and configuration state.
- `reconcile` resolves, composes, applies, repairs, and checks drift transactionally while preserving consumer-owned content.
- The legacy `.project-standards.yml` validator and `adopt` bundles remain bounded migration and compatibility inputs through v5.
- This repo dogfoods frontmatter only on configured managed docs. ADR 0015 excludes `standards/**` so packages do not ship repo-specific metadata.
- Schemas, manifests, payloads, generated projections, provider output, and installed-wheel behavior form versioned package contracts.

## Standing backlog

- **Repo-root-relative link enforcement:** breaking and deferred to a future major.
- **MCP enablement:** complete SPEC-MT01 Step 07 before SPEC-RD01 or the thin, local, read-only-first SPEC-MS01 server.
- Packages remain independent by default. Profiles recommend combinations; the future MCP layer surfaces relationships without enforcing hidden dependencies.
- SPEC-MT01 ADRs 0001-0013 are accepted. Later MCP-server decisions remain deferred; see `specs-plans.md`.
