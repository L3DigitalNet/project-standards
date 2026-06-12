# Project Standards

Shared standards, schemas, templates, and tooling for documentation and Python projects across all repositories. This repository is the **single source of truth**: it _defines_ the standards, and other repositories _consume_ them — the **Frontmatter** and **ADR** standards through a small config file plus a reusable CI workflow, and the **Python Tooling** and **Markdown Tooling** standards by copying their scaffolds (Markdown Tooling adds an optional reusable lint workflow) — rather than vendoring their own copies.

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
    - [Python Coding Standard (draft)](#python-coding-standard-draft)
  - [Consuming the standards](#consuming-the-standards)
    - [Markdown standards (Frontmatter + ADR)](#markdown-standards-frontmatter--adr)
    - [Python Tooling SSOT](#python-tooling-ssot)
    - [Markdown Tooling](#markdown-tooling)
    - [Pin to a release tag, not `main`](#pin-to-a-release-tag-not-main)
  - [Versioning](#versioning)
  - [Developing this repository](#developing-this-repository)
  - [License](#license)

## Repository layout

```text
project-standards/
├── standards/                 # governing standards — one self-contained bundle per standard
│   ├── README.md              #   index + bundle anatomy
│   ├── markdown-frontmatter/  #   standard + adopt + templates/ + examples/
│   ├── adr/                   #   standard + adopt + templates/ + examples/
│   ├── python-tooling/        #   standard + adopt (doc-only)
│   ├── markdown-tooling/      #   standard + adopt (doc-only)
│   └── python-coding/         #   draft standard (reference-only; README only)
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
- **Schema:** [`src/project_standards/schemas/markdown-frontmatter.schema.json`](src/project_standards/schemas/markdown-frontmatter.schema.json) (JSON Schema Draft 2020-12)
- **Templates:** [`templates/`](standards/markdown-frontmatter/templates/) · **Examples:** [`examples/`](standards/markdown-frontmatter/examples/) · **Adopt:** [`adopt.md`](standards/markdown-frontmatter/adopt.md)

The standard defines **eleven required fields** plus a recommended optional set. Copy a ready-made block from [`templates/`](standards/markdown-frontmatter/templates/) (`frontmatter-minimal.yml` or `frontmatter-standard.yml`); the [standard](standards/markdown-frontmatter/README.md) gives the full field definitions and the controlled values for `doc_type`, `status`, `confidence`, `visibility`, and `consumer`.

### ADR Standard

Architecture Decision Records capture significant, hard-to-reverse decisions, using the [MADR](https://adr.github.io/madr/) format on top of the frontmatter profile above.

- **Standard:** [`standards/adr/README.md`](standards/adr/README.md) — when to write an ADR, MADR body structure, the MADR→canonical field/status mappings, ID/filename and `docs/decisions/` conventions, and the supersession workflow.
- **Templates:** [`templates/adr.md`](standards/adr/templates/adr.md) (full) plus `adr-minimal.md`, `adr-bare.md`, and `adr-bare-minimal.md`.
- **Example:** [`examples/adr.example.md`](standards/adr/examples/adr.example.md). · **Adopt:** [`adopt.md`](standards/adr/adopt.md).

ADRs use `doc_type: adr` with kebab IDs like `adr-0001-repo-name-short-title` — the **`id`** embeds the repo-name for cross-repo uniqueness, while the **filename** omits it (`adr-0001-short-title.md`). ADR-specific roles (`decision_makers`, `consulted`, `informed`) live under the `project` extension namespace, keeping the universal vocabulary small.

### Python Tooling SSOT Standard

The standard Python stack for agent-authored projects: `uv` + `uv_build`, `src/` layout, Ruff, basedpyright (strict), pytest + coverage (branch), pip-audit, a one-command verification gate, and the VS Code / agent-instruction conventions. Unlike the Markdown standards it is **not** validator-enforced and ships **no reusable workflow** — you adopt it by copying the in-doc scaffolds and running the gate.

- **Standard:** [`standards/python-tooling/README.md`](standards/python-tooling/README.md)
- **Adopt:** [`adopt.md`](standards/python-tooling/adopt.md)

### Markdown Tooling Standard

The recommended linting/formatting tools and settings for Markdown and the structured-text files Prettier handles (`json`/`jsonc`/`yaml`): **markdownlint** for Markdown structure, **Prettier** for formatting, and **EditorConfig** as the floor. The tool-specific complement to the tool-neutral Frontmatter standard; markdownlint ships a reusable workflow + seedable rule set, while Prettier is copy-adopt (no workflow).

- **Standard:** [`standards/markdown-tooling/README.md`](standards/markdown-tooling/README.md)
- **Adopt:** [`adopt.md`](standards/markdown-tooling/adopt.md)

### Python Coding Standard (draft)

Code-shape and agent-behavior rules for Python — the reference companion to the Python Tooling SSOT (the SSOT standardizes the toolchain; this document standardizes the code the toolchain checks). **In-development draft (version 0.4):** reference-only, unregistered (no contract version), excluded from frontmatter validation, and not adoptable via the CLI. It ships in the repository for review and early reference until released.

- **Standard:** [`standards/python-coding/README.md`](standards/python-coding/README.md)

## Consuming the standards

How a repository adopts each standard. The two **Markdown frontmatter standards** (Frontmatter + ADR) share one mechanism; **Python Tooling** and **Markdown Tooling** each adopt on their own. Each bundle's `adopt.md` is the canonical, step-by-step runbook — this section is the map.

> **Adopting with an agent?** Hand it the relevant `adopt.md` and let it follow the procedure end to end.

### Markdown standards (Frontmatter + ADR)

Add two files, pinned to a major tag:

1. **`.project-standards.yml`** at the repo root — declares which Markdown files are managed.
2. **`.github/workflows/validate-standards.yml`** — calls the reusable `validate-markdown-frontmatter.yml@v3` workflow, with `standards-ref` pinned to the same major.

ADR enforcement (managed ADR docs, plus the opt-in MADR section check) rides the **same** workflow — no extra job. Optional Markdown _body_ linting is a separate opt-in workflow (`lint-markdown.yml`).

- **Full runbook** (config, workflow, pinning, local validation, body-linting, compliance checklist): [`standards/markdown-frontmatter/adopt.md`](standards/markdown-frontmatter/adopt.md)
- **ADR specifics:** [`standards/adr/adopt.md`](standards/adr/adopt.md)

For local tooling, use `project-standards fix` (formats frontmatter and regenerates ids in one pass), the standalone `format-frontmatter` command, or the pre-commit hooks (`.pre-commit-hooks.yaml`) — see [`src/project_standards/README.md`](src/project_standards/README.md) for the full CLI reference.

### Python Tooling SSOT

No config or workflow — copy the in-doc scaffolds and run the verification gate. See [`standards/python-tooling/adopt.md`](standards/python-tooling/adopt.md).

### Markdown Tooling

Seed `.markdownlint.json` + `.editorconfig`, copy `.prettierrc.json`, and opt into the reusable `lint-markdown.yml@v3` workflow. See [`standards/markdown-tooling/adopt.md`](standards/markdown-tooling/adopt.md).

> **Availability:** `lint-markdown.yml` is available since `@v2`. The Frontmatter/ADR `validate-markdown-frontmatter.yml` workflow is available on any major tag.

### Pin to a release tag, not `main`

Reference reusable workflows by **major tag** (`@v3`), never `@main`: a repo that passed validation yesterday must not fail today because the standard changed. Breaking changes ship only as a new major (`@v4`); `@v3` receives bug fixes and backward-compatible updates. For an immutable pin, use a full version (`@v3.0.0`) or a commit SHA. The adopt guides explain the full rationale, and [`UPGRADING.md`](UPGRADING.md) is the step-by-step runbook for moving an existing repo across a major (e.g. `@v2` → `@v3`).

For private standards repos called by private consumers, enable cross-repository access under this repo's **Actions** settings.

## Versioning

Releases follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html), but the contract is the **consuming repo's validation outcome** — a release's level reflects the worst-case impact of any change across the standard, schema, validator, and workflow.

- **PATCH / MINOR** → safe to inherit on a moving major pin (`@v3`); a repo that passed yesterday still passes today.
- **MAJOR** → may newly-fail a previously-passing repo (a new required field, a stricter rule, even a validator bug fix); old `vN.x` tags stay intact, and consumers migrate intentionally.

See [`meta/versioning.md`](meta/versioning.md) for the full classification table, the previously-passing rule, and release requirements.

## Developing this repository

Working on the standards or the validator itself:

```bash
uv sync --dev                                                # set up the environment
uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit
uv run project-standards validate --config .project-standards.yml  # dogfood: schema, id, and references
```

## License

This project is licensed under the [Apache License 2.0](LICENSE).
