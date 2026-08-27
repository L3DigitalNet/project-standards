# Architecture

**Last updated:** 2026-08-27

## Components

- `standards/` holds the eleven catalog 5 families, their manifests, package guidance, templates, examples, and index.
- `github-workflow@1.5` is the tenth family: skill, six references, org-schema oracle, and a committed `gh-workflow` binary.
- `project-toolbox` ships workflow checklists (repo-housekeeping, drift-detection) plus a routing skill, no providers/binaries (standards/project-toolbox/README.md; v5.21.0).
- `cmd/gh-workflow/` and `internal/ghworkflow/` are the first Go packages; `scripts/build-gh-workflow.sh` builds them reproducibly.
- `scripts/verify.sh` is the canonical local gate; `go.mod` plus `Makefile` carry the Go lane, now with sources and a `go-verify-binary` step.
- `meta/` holds repository policy such as the release contract; it is not a governed package.
- `src/project_standards/` implements the CLI, validators, specs, Catalog 5 control plane, MCP, projections, and bounded legacy compatibility.
- `tests/` covers source and wheel behavior, package compatibility, migrations, scale, and documentation coherence.
- `.github/workflows/` contains reusable consumer workflows and repository gates.
- `docs/specs/` is the validated, indexed home for maintained Project Specification documents.
- `docs/handoff/` is the repo-local Agent Handoff knowledge and session-state surface.

## Relationships

- Catalog 5 consumers select immutable packages in `.standards/config.toml`; one lock records exact payload and configuration state.
- `reconcile` resolves, composes, applies, repairs, and checks drift transactionally while preserving consumer-owned content.
- Legacy `.project-standards.yml`, `registry.json`, and copy-adopt bundles are migration and compatibility inputs only, not current authorities.
- This repo dogfoods frontmatter only on configured managed docs. ADR 0015 excludes `standards/**` so packages do not ship repo-specific metadata.
- Schemas, manifests, payloads, generated projections, provider output, and installed-wheel behavior form versioned package contracts.
- Advertising a family crosses eight layers: catalog, compatibility matrix, ledger amendments, performance lane, composition, MCP seam, resolution oracle, hygiene/routing.
- This repo self-hosts `github-workflow` for `L3DigitalNet` on both harnesses, so the package is proven through its own consumer path.

## Standing backlog

- **Repo-root-relative link enforcement:** breaking and deferred to a future major.
- **MCP expansion:** read-only stdio shipped in 5.12.0 under SPEC-MS01. SPEC-RD01 governs separately approved write and remote phases.
- Packages remain independent by default. Profiles recommend combinations; the MCP server surfaces declared relationships without enforcing hidden dependencies.
- ADRs 0001-0013 are accepted. ADRs 0025-0026 govern local read-only MCP; later write and remote decisions remain deferred. See `specs-plans.md`.
- ADR 0027 adopts Go alongside Python under neutral tooling: an independent gate, no shared toolchain, and no language preference in the standards.
- **Create-only delivery gap:** a create-only artifact cannot be revised for an existing consumer, and drift-check cannot see it. Bug 006; decision owed under #128.
- Bug 006 stays a platform constraint, not a `github-workflow` one: that package ships zero create-only artifacts and a guard test enforces it.
- **`github-workflow@1.0` release placement:** OQ-001 answered — ships in v5.17.0. Execution-discovered follow-ups sit in the plan §13 close-out register.
- **ADR corpus conformance:** 11 of 23 active ADRs state no boundary; five authorities contested, five unowned. See `docs/reviews/adr-conformance/`; scheduled as v5.18.0.
- **Owner deviation:** spec keeps `Unattended agent` owner-only, narrower than "all three by judgment"; no mechanism honors it yet.
- **Consumer-pin rollout** deferred to owner scheduling; `@v5` trackers inherit new versions automatically without a manual bump.
