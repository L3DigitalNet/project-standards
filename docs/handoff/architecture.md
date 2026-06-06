# Architecture

**Last updated:** 2026-06-05

## Components

```text
project-standards
├── standards/          -> human-readable governing docs (frontmatter, ADR, versioning, adoption)
├── templates/          -> copy-paste scaffolds (intentional placeholders; not validated)
├── examples/           -> validated worked examples (managed; carry frontmatter)
├── src/project_standards/ + tests/ -> the Python validator (validate_frontmatter.py) with bundled schema, and its pytest suite
├── .github/workflows/  -> reusable workflows consumers call (validate, lint-markdown, format)
└── docs/handoff/       -> agent session state (this v3 layout)
```

## Relationships

- Consumers add `.project-standards.yml` + call the reusable workflow; they do not vendor copies. The schema is the contract — changing it is a versioned change.
- The validator (`src/project_standards/`) reads `.project-standards.yml`, resolves the bundled schema shipped inside the package, and validates the configured include globs.
- This repo dogfoods its own standards: `standards/`, `examples/`, `CHANGELOG.md` carry canonical frontmatter and must validate.

## Standing backlog

- **Pre-commit hooks** — deferred (decided during the 1.3.0 line).
- **`2.0.0` repo-root-relative link enforcement** — breaking; future major.
