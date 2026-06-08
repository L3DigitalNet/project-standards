# Architecture

**Last updated:** 2026-06-08

## Components

```text
project-standards
├── standards/          -> governing standards, one bundle each (markdown-frontmatter, adr, python-tooling, markdown-tooling) + README index
├── meta/               -> docs about this repo (versioning); not a governed standard
├── src/project_standards/ + tests/ -> Python package: validator (validate_frontmatter.py) + bundled schema; the `project-standards` CLI (cli.py: adopt|list|validate); the adopt engine (adopt/); per-standard adopt bundles (bundles/<id>/adopt.toml + templates); pytest suite
├── .github/workflows/  -> reusable workflows consumers call (validate, lint-markdown, format)
└── docs/handoff/       -> agent session state (this v3 layout)
```

## Relationships

- Consumers add `.project-standards.yml` + call the reusable workflow; they do not vendor copies. The schema is the contract — changing it is a versioned change.
- The validator (`src/project_standards/`) reads `.project-standards.yml`, resolves the bundled schema shipped inside the package, and validates the configured include globs.
- This repo dogfoods its own standards: the bundle `README.md`/`adopt.md`/`examples/` docs, `meta/`, and `CHANGELOG.md` carry canonical frontmatter and must validate (the per-standard `templates/` and the `standards/README.md` index are excluded).
- The `adopt` CLI (`cli.py` + `adopt/`) materializes each standard's canonical artifacts from declarative `bundles/<id>/adopt.toml` manifests into a consumer repo. Bundle templates are the repo's _real working files_ (byte-identical dogfood test) or curated consumer scaffolds; they resolve via the same `Path(__file__)`-relative lookup as the bundled schema, so they ship in the wheel automatically. The future `check` (drift) command reads the same manifests.

## Standing backlog

- **Pre-commit hooks** — deferred (decided during the 1.3.0 line).
- **Repo-root-relative link enforcement** — breaking; future major (deferred past `2.0.0`, which shipped without it).
