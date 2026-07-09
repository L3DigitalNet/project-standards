# Architecture

**Last updated:** 2026-07-07

## Components

```text
project-standards
├── standards/          -> governing standards, one bundle each (markdown-frontmatter, adr, python-tooling, markdown-tooling, project-spec, cli-documentation) + python-coding (draft, reference-only, unregistered) + standard-bundle-authoring (internal/reference meta-standard, adoption=none) + README index
├── meta/               -> docs about this repo (versioning); not a governed standard
├── src/project_standards/ + tests/ -> Python package: validator (validate_frontmatter.py) + bundled schema; standard manifest model (standard_manifest.py) + standards graph validator (standards_graph/ and `project-standards standards validate-graph`); the `project-standards` CLI (cli.py: validate|fix|spec|adopt|standards|list); the spec engine (specs/: commands/ validate|lint|extract|next|new|upgrade over project specs, plus config/document/model/registry/templates); the adopt engine (adopt/); per-standard adopt bundles (bundles/<id>/adopt.toml + templates); pytest suite
├── .github/workflows/  -> reusable workflows consumers call (validate, validate-specs, lint-markdown, format)
└── docs/handoff/       -> agent session state (this v3 layout)
```

## Relationships

- Consumers add `.project-standards.yml` + call the reusable workflow; they do not vendor copies. The schema is the contract — changing it is a versioned change.
- The validator (`src/project_standards/`) reads `.project-standards.yml`, resolves the bundled schema shipped inside the package, and validates the configured include globs.
- This repo dogfoods its own frontmatter standard only on repo-local managed docs configured in `.project-standards.yml` (`CHANGELOG.md`, `UPGRADING.md`, `docs/usage.md`, `meta/**/*.md`, and `docs/adr/**/*.md`). Standard-package docs under `standards/**` are excluded from this repo's local frontmatter scope so packages do not accidentally ship project-standards-specific metadata; intentional standard artifacts there may still contain frontmatter when frontmatter is the artifact itself (templates, examples, skill metadata).
- The `adopt` CLI (`cli.py` + `adopt/`) materializes each standard's canonical artifacts from declarative `bundles/<id>/adopt.toml` manifests into a consumer repo. Bundle templates are the repo's _real working files_ (byte-identical dogfood test) or curated consumer scaffolds; they resolve via the same `Path(__file__)`-relative lookup as the bundled schema, so they ship in the wheel automatically. The future `check` (drift) command reads the same manifests.

## Standing backlog

- **Repo-root-relative link enforcement** — breaking; future major (deferred past `2.0.0`, which shipped without it).
- **MCP enablement program (specs ingested 2026-07-07; partially started).** Ordered: **SPEC-MT01** (meta-repo readiness prep — `standard.toml` manifests, authority map, standards-graph validator, provider registry, generated index) → **SPEC-RD01** (sequencing roadmap) → **SPEC-MS01** (thin local read-only-first MCP server over the standards graph; not a second standards implementation). Hard gate: MCP server work must not begin until SPEC-MT01's readiness gate passes (SPEC-RD01 Step 07). Core architectural principle these lock in: **standards are independent packages by default**; standard groups/profiles are recommendations, never hidden hard dependencies — a future MCP layer surfaces relationships, never enforces them. SPEC-MT01 ADRs 0001-0013 are accepted; later MCP-server ADRs remain deferred. Specs/paths: see `specs-plans.md`.
