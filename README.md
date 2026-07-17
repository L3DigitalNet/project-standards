# Project Standards

Shared standards, schemas, templates, and tooling for documentation, Python projects, CLI documentation, project specifications, and repository-local agent continuity. This repository is the **single source of truth**: it _defines_ the standards, and other repositories _consume_ immutable packages through unified config/reconciliation, managed or create-only outputs, reusable workflows, repo-local skills, and the `project-standards` CLI rather than vendoring their own implementations. Copy-adopt bundles remain v5 migration fallback only.

- **Looking for what's standardised here?** See [Standards](#standards).
- **Adopting the standards in your own repo?** See [Consuming the standards](#consuming-the-standards).

## Table of Contents

- [Project Standards](#project-standards)
  - [Table of Contents](#table-of-contents)
  - [Repository layout](#repository-layout)
  - [Standards](#standards)
    - [Markdown Frontmatter Standard](#markdown-frontmatter-standard)
    - [ADR Standard](#adr-standard)
    - [Python Tooling SSOT Standard](#python-tooling-ssot-standard)
    - [Markdown Tooling Standard](#markdown-tooling-standard)
    - [Project Specification Standard](#project-specification-standard)
    - [CLI Documentation Standard](#cli-documentation-standard)
    - [Agent Handoff Standard](#agent-handoff-standard)
    - [Python Coding Standard (draft)](#python-coding-standard-draft)
    - [Standard Bundle Authoring Standard (internal/reference)](#standard-bundle-authoring-standard-internalreference)
  - [Consuming the standards](#consuming-the-standards)
    - [Current consumer packages](#current-consumer-packages)
    - [Pin to a release tag, not `main`](#pin-to-a-release-tag-not-main)
  - [Versioning](#versioning)
  - [Developing this repository](#developing-this-repository)
  - [License](#license)

## Repository layout

```text
project-standards/
├── standards/                 # governing standards — one self-contained bundle per standard
│   ├── README.md              #   index + bundle anatomy
│   ├── markdown-frontmatter/  #   standard + adopt + templates/ + examples/ + skills/
│   ├── adr/                   #   standard + adopt + templates/ + examples/
│   ├── python-tooling/        #   standard + immutable payload + providers
│   ├── markdown-tooling/      #   standard + immutable payload + providers
│   ├── project-spec/          #   standard + adopt + templates/ + examples/ + CLI (spec)
│   ├── cli-documentation/     #   standard + adopt + templates/ + examples/ + resources/
│   ├── agent-handoff/         #   standard + adopt + templates/ + skill + shared hook
│   ├── python-coding/         #   draft standard (reference-only; README only)
│   └── standard-bundle-authoring/ # internal/reference meta-standard (README + standard.toml + template)
├── meta/                      # docs about THIS repo (e.g. versioning) — not governed standards
├── src/project_standards/     # the Python validator + bundled schema
├── tests/                     # validator tests
├── scripts/                   # optional helper — check.py runs the verification gate
├── docs/                      # agent session-handoff state + specs/plans (not consumer-facing)
└── .github/                   # reusable CI workflows
```

Each standard is a self-contained **bundle**: the deep detail lives in the bundle, and this README stays a map. See [`standards/README.md`](standards/README.md) for the bundle index and anatomy.

## Standards

The standards this repository defines. Each lives in its own bundle under [`standards/`](standards/) — see the [standards index](standards/README.md).

### Markdown Frontmatter Standard

A small, portable, **tool-neutral** set of YAML frontmatter fields for project documentation, giving every Markdown document consistent metadata for discovery, validation, and LLM/human workflows. It is deliberately **not** an Obsidian, Hugo, Jekyll, Quarto, or Pandoc schema — publishing-tool metadata goes under a `publish` namespace, never at the top level.

- **Standard:** [`standards/markdown-frontmatter/README.md`](standards/markdown-frontmatter/README.md)
- **Structure:** [`structure.md`](standards/markdown-frontmatter/structure.md) · **Field values:** [`field-values.md`](standards/markdown-frontmatter/field-values.md)
- **Schema:** [`src/project_standards/schemas/markdown-frontmatter.schema.json`](src/project_standards/schemas/markdown-frontmatter.schema.json) (JSON Schema Draft 2020-12)
- **Skill:** [`skills/markdown-frontmatter/`](standards/markdown-frontmatter/skills/markdown-frontmatter/) — installed repo-local at `.agents/skills/markdown-frontmatter` for Claude Code and Codex CLI.
- **Templates:** [`templates/`](standards/markdown-frontmatter/templates/) · **Examples:** [`examples/`](standards/markdown-frontmatter/examples/) · **Adopt:** [`adopt.md`](standards/markdown-frontmatter/adopt.md)

The standard defines **eleven required fields** plus a recommended optional set. Copy a ready-made block from [`templates/`](standards/markdown-frontmatter/templates/) (`frontmatter-minimal.yml` or `frontmatter-standard.yml`); the [structure guide](standards/markdown-frontmatter/structure.md) gives the hard field and controlled-value contract, and the [field-values guide](standards/markdown-frontmatter/field-values.md) explains ownership, lifecycle, tags, aliases, relationships, and repo-local extensions.

### ADR Standard

Architecture Decision Records capture significant, hard-to-reverse decisions, using the [MADR](https://adr.github.io/madr/) format on top of the frontmatter profile above.

- **Standard:** [`standards/adr/README.md`](standards/adr/README.md) — when to write an ADR, MADR body structure, the MADR→canonical field/status mappings, ID/filename and `docs/adr/` conventions, and the supersession workflow.
- **Templates:** [`templates/adr.md`](standards/adr/templates/adr.md) (full) plus `adr-minimal.md`, `adr-bare.md`, and `adr-bare-minimal.md`.
- **Example:** [`examples/adr.example.md`](standards/adr/examples/adr.example.md). · **Adopt:** [`adopt.md`](standards/adr/adopt.md).

ADRs use `doc_type: adr` with kebab IDs like `adr-0001-repo-name-short-title` — the **`id`** embeds the repo-name for cross-repo uniqueness, while the **filename** omits it (`adr-0001-short-title.md`). ADR-specific roles (`decision_makers`, `consulted`, `informed`) live under the `project` extension namespace, keeping the universal vocabulary small.

### Python Tooling SSOT Standard

The standard Python stack for agent-authored projects: `uv` + `uv_build`, `src/` layout, Ruff, basedpyright (strict), pytest + coverage (branch), pip-audit, a one-command verification gate, CI, and bounded VS Code / agent-instruction contributions. The V5 package composes these surfaces through the unified executor and preserves explicit repository toolchain intent during migration.

- **Standard:** [`standards/python-tooling/README.md`](standards/python-tooling/README.md)
- **Adopt:** [`adopt.md`](standards/python-tooling/adopt.md)

### Markdown Tooling Standard

The recommended linting/formatting tools and settings for Markdown and the structured-text files Prettier handles (`json`/`jsonc`/`yaml`): **markdownlint** for Markdown structure, **Prettier** for formatting, and **EditorConfig** as the floor. The V5 package manages the two configs plus `lint-markdown.yml` and `format.yml` caller/self-hosted workflows while composing only declared units in shared EditorConfig, VS Code, and instruction containers.

- **Standard:** [`standards/markdown-tooling/README.md`](standards/markdown-tooling/README.md)
- **Adopt:** [`adopt.md`](standards/markdown-tooling/adopt.md)

### Project Specification Standard

Tiered format (Light ⊂ Standard ⊂ Full), stable canonical numbering, typed IDs, and provider-backed `validate`/`lint`/`extract`/`next`/`new`/`upgrade` commands. The selected package manages a reusable or self-hosted validation workflow; authoring writes are applied only from typed plans through the unified executor.

- **Standard:** [`standards/project-spec/README.md`](standards/project-spec/README.md)
- **Templates:** [`templates/`](standards/project-spec/templates/) · **Example:** [`examples/spec.example.md`](standards/project-spec/examples/spec.example.md) · **Adopt:** [`adopt.md`](standards/project-spec/adopt.md)

### CLI Documentation Standard

User-facing CLI usage documentation — help text, the canonical usage reference, man pages, and CI checks that catch drift. A strict profile ladder (**Script ⊂ Packaged ⊂ Packaged-deep**) scales the requirement to a CLI's distribution shape. The V5 package creates the usage scaffold once and verifies a reviewed consumer-owned workflow rendered by its selected provider.

- **Standard:** [`standards/cli-documentation/README.md`](standards/cli-documentation/README.md)
- **Templates:** [`templates/`](standards/cli-documentation/templates/) · **Example:** [`examples/usage.example.md`](standards/cli-documentation/examples/usage.example.md) · **Adopt:** [`adopt.md`](standards/cli-documentation/adopt.md)

### Agent Handoff Standard

Repository-local project knowledge and bounded session continuity for coding agents. Agent Handoff creates consumer-owned status, task, and lifetime-routed knowledge under `docs/`; installs a repo-local `agent-handoff` skill; optionally registers one shared SessionStart hook for Claude Code and Codex; and validates layout, drift, provenance, document budgets, and credential references without owning workstation-global state.

- **Standard:** [`standards/agent-handoff/README.md`](standards/agent-handoff/README.md)
- **Skill:** [`skills/agent-handoff/`](standards/agent-handoff/skills/agent-handoff/) — installed repo-local at `.agents/skills/agent-handoff/`.
- **Adopt:** [`adopt.md`](standards/agent-handoff/adopt.md) · **Migration:** [`resources/legacy-migration.md`](standards/agent-handoff/resources/legacy-migration.md)

### Python Coding Standard (draft)

Code-shape and agent-behavior rules for Python — the reference companion to Python Tooling. **In-development package `0.5`:** reference-only and not consumer-selectable.

- **Standard:** [`standards/python-coding/README.md`](standards/python-coding/README.md)

### Standard Bundle Authoring Standard (internal/reference)

The "standard for standards" — the V2 family/payload/catalog contract every package declares: immutable releases, option schemas, channels, relationships, resources, providers, migrations, semantic ownership, and integrity. **Internal package `2.0`:** its family availability and catalog role are `internal`, so it governs this repository and is not consumer-selectable.

- **Standard:** [`standards/standard-bundle-authoring/README.md`](standards/standard-bundle-authoring/README.md)

## Consuming the standards

V5 consumers use one catalog/config/lock plane. Initialization is neutral and enables no package:

```bash
project-standards init --catalog 5
project-standards standards enable markdown-frontmatter --version 1.2
project-standards reconcile
project-standards reconcile --apply
```

Commit `.standards/config.toml`, `.standards/catalog.toml`, `.standards/lock.toml`, and reconciled outputs together. The package selector chooses an immutable payload; package options such as `contract_version` remain independent. Each bundle's `adopt.md` links to the current version-specific options, outputs, migration, verification, and troubleshooting.

> **Adopting with an agent?** Hand it the relevant `adopt.md` and let it follow the procedure end to end.

### Current consumer packages

| Package | Current payload | Adoption guide |
| --- | --- | --- |
| Markdown Frontmatter | `1.2` | [`standards/markdown-frontmatter/adopt.md`](standards/markdown-frontmatter/adopt.md) |
| ADR | `1.1` | [`standards/adr/adopt.md`](standards/adr/adopt.md) |
| Python Tooling | `1.1` | [`standards/python-tooling/adopt.md`](standards/python-tooling/adopt.md) |
| Markdown Tooling | `1.2` | [`standards/markdown-tooling/adopt.md`](standards/markdown-tooling/adopt.md) |
| Project Specification | `1.1` | [`standards/project-spec/adopt.md`](standards/project-spec/adopt.md) |
| CLI Documentation | `1.1` | [`standards/cli-documentation/adopt.md`](standards/cli-documentation/adopt.md) |
| Agent Handoff | `1.1` | [`standards/agent-handoff/adopt.md`](standards/agent-handoff/adopt.md) |

For a V4 repository, do not create `.standards/` separately. Preview the complete migration, resolve every ambiguity, then apply the same command explicitly:

```bash
project-standards init --catalog 5 --migrate
project-standards init --catalog 5 --migrate --apply
```

The migration removes `.project-standards.yml` only after unified validation and lock publication. During v5, legacy-only validation remains a warned read-only fallback; v6 removes it.

### Pin to a release tag, not `main`

Reference reusable workflows by **major tag** (`@v5` after release), never `@main`. For an immutable pin, use a full version (`@v5.0.0`) or a commit SHA. [`UPGRADING.md`](UPGRADING.md) is the v4-to-v5 migration runbook.

For private standards repos called by private consumers, enable cross-repository access under this repo's **Actions** settings.

## Versioning

Releases follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html), but the contract is the **consuming repo's validation outcome** — a release's level reflects the worst-case impact of any change across the standard, schema, validator, and workflow.

- **PATCH / MINOR** → safe to inherit on a moving major pin (`@v5`); a repo that passed yesterday still passes today.
- **MAJOR** → may newly-fail a previously-passing repo (a new required field, a stricter rule, even a validator bug fix); old `vN.x` tags stay intact, and consumers migrate intentionally.

See [`meta/versioning.md`](meta/versioning.md) for the full classification table, the previously-passing rule, and release requirements.

## Developing this repository

Working on the standards or the validator itself:

```bash
uv sync --dev                                                # set up the environment
uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run python scripts/run_repository_tests.py && uv run pip-audit
uv run project-standards validate                              # dogfood: schema, id, and references
```

## License

This project is licensed under the [Apache License 2.0](LICENSE).
