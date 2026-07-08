# Architecture

**Last updated:** 2026-07-07

## Components

```text
project-standards
├── standards/          -> governing standards, one bundle each (markdown-frontmatter, adr, python-tooling, markdown-tooling, project-spec, cli-documentation) + python-coding (draft, reference-only, unregistered) + standard-bundle-authoring (internal/reference meta-standard, adoption=none) + README index
├── meta/               -> docs about this repo (versioning); not a governed standard
├── src/project_standards/ + tests/ -> Python package: validator (validate_frontmatter.py) + bundled schema; the `project-standards` CLI (cli.py: validate|fix|spec|adopt|list); the spec engine (specs/: commands/ validate|lint|extract|next|new|upgrade over project specs, plus config/document/model/registry/templates); the adopt engine (adopt/); per-standard adopt bundles (bundles/<id>/adopt.toml + templates); pytest suite
├── .github/workflows/  -> reusable workflows consumers call (validate, validate-specs, lint-markdown, format)
└── docs/handoff/       -> agent session state (this v3 layout)
```

## Relationships

- Consumers add `.project-standards.yml` + call the reusable workflow; they do not vendor copies. The schema is the contract — changing it is a versioned change.
- The validator (`src/project_standards/`) reads `.project-standards.yml`, resolves the bundled schema shipped inside the package, and validates the configured include globs.
- This repo dogfoods its own standards: the bundle `README.md`/`adopt.md`/`examples/` docs, `meta/`, and `CHANGELOG.md` carry canonical frontmatter and must validate (the per-standard `templates/` and the `standards/README.md` index are excluded).
- The `adopt` CLI (`cli.py` + `adopt/`) materializes each standard's canonical artifacts from declarative `bundles/<id>/adopt.toml` manifests into a consumer repo. Bundle templates are the repo's _real working files_ (byte-identical dogfood test) or curated consumer scaffolds; they resolve via the same `Path(__file__)`-relative lookup as the bundled schema, so they ship in the wheel automatically. The future `check` (drift) command reads the same manifests.

## Standing backlog

- **Repo-root-relative link enforcement** — breaking; future major (deferred past `2.0.0`, which shipped without it).
- **MCP enablement program (specs ingested 2026-07-07; not started).** Ordered: **SPEC-MT01** (meta-repo readiness prep — `standard.toml` manifests, authority map, standards-graph validator, provider registry, generated index) → **SPEC-RD01** (sequencing roadmap) → **SPEC-MS01** (thin local read-only-first MCP server over the standards graph; not a second standards implementation). Hard gate: MCP server work must not begin until SPEC-MT01's readiness gate passes (SPEC-RD01 Step 07). Core architectural principle these lock in: **standards are independent packages by default**; standard groups/profiles are recommendations, never hidden hard dependencies — a future MCP layer surfaces relationships, never enforces them. Requires an ADR set (→ `docs/adr/`, not yet created) enumerated in each spec's §8.3 and summarized in `TODO.md`. Specs/paths: see `specs-plans.md`.
