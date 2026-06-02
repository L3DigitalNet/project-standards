# Project Standards

Shared standards, schemas, templates, and validation tooling for documentation across all projects. This repository is the single source of truth; individual projects consume it via a small config file and a reusable CI workflow rather than vendoring their own copies.

## Layout

```text
project-standards/
├── standards/    # human-readable standards (the governing documents)
├── schemas/      # machine-readable JSON Schemas
├── templates/    # copy-paste frontmatter snippets and document scaffolds
├── examples/     # validated worked examples
├── tools/        # the Python validator
├── tests/        # validator tests
└── .github/      # reusable CI workflows
```

## Markdown Frontmatter Standard

### What it is for

A small, portable, **tool-neutral** set of YAML frontmatter fields for project documentation. It gives every Markdown document consistent metadata for discovery, validation, and LLM/human workflows. It is deliberately **not** an Obsidian, Hugo, Jekyll, Quarto, or Pandoc schema — publishing-tool metadata goes under a `publish` namespace, not at the top level.

### Where the canonical standard lives

- **Standard (human-readable):** [`standards/markdown-frontmatter.md`](standards/markdown-frontmatter.md)
- **Schema (machine-readable):** [`schemas/markdown-frontmatter.schema.json`](schemas/markdown-frontmatter.schema.json) (JSON Schema Draft 2020-12)
- **Templates:** [`templates/`](templates/) · **Examples:** [`examples/`](examples/)

### Minimal frontmatter

```yaml
---
schema_version: '1.0'
id: 'replace-with-stable-id'
title: 'Human Title'
description: 'One-sentence description of the document.'
doc_type: 'note'
status: 'draft'
created: '2026-06-02'
updated: '2026-06-02'
tags: []
aliases: []
related: []
---
```

### Standard frontmatter

```yaml
---
schema_version: '1.0'
id: 'replace-with-stable-id'
title: 'Human Title'
description: 'One-sentence description of the document.'
doc_type: 'note'
status: 'draft'
created: '2026-06-02'
updated: '2026-06-02'
reviewed: null
owner: ''
tags: []
aliases: []
related: []
source: []
confidence: 'unknown'
visibility: 'internal'
license: null
---
```

See the standard for the full field definitions and the controlled values for `doc_type`, `status`, `confidence`, and `visibility`.

### Validate locally

```bash
# Install dependencies (uv manages the environment)
uv sync --dev

# Validate using the repo config (default: .project-standards.yml)
uv run validate-frontmatter --config .project-standards.yml

# Validate explicit files or globs against a specific schema
uv run validate-frontmatter --schema schemas/markdown-frontmatter.schema.json examples/*.md
```

The validator exits `0` when all checked files pass and non-zero when any file fails, printing file-specific errors.

### Add validation to another GitHub repository

Each consuming repo needs two small files.

**1. A config file `.project-standards.yml`** declaring which files the standard applies to:

```yaml
standards_version: 'v1.0.0'

markdown:
  frontmatter:
    schema: 'markdown-frontmatter'
    required: true
    include:
      - 'README.md'
      - 'docs/**/*.md'
      - 'CLAUDE.md'
      - 'AGENTS.md'
    exclude:
      - 'CHANGELOG.md'
      - 'LICENSE.md'
```

**2. A workflow** that calls the reusable workflow from this repo:

```yaml
name: Validate project standards

on:
  pull_request:
  push:
    branches:
      - main

jobs:
  validate:
    uses: chrisdpurcell/project-standards/.github/workflows/validate-markdown-frontmatter.yml@v1.0.0
    with:
      config-path: '.project-standards.yml'
```

The reusable workflow installs the validator from this repo (`uv tool install git+...`), so the consuming repo does not need to vendor the schema or the Python code — the bundled schema travels with the install.

### Pin to a release tag, not `main`

Reference the reusable workflow by **release tag** (`@v1.0.0`), not `@main`. Tags are the contract: a repo that passed validation yesterday should not fail today because the standard changed. Use `@main` only for the standards repo's own development or for deliberate test repos. GitHub also supports pinning by commit SHA for maximum stability.

## ADR Standard

Architecture Decision Records capture significant, hard-to-reverse decisions. This repo adopts the
[MADR](https://adr.github.io/madr/) format on top of the canonical frontmatter profile.

- **Standard:** [`standards/adr.md`](standards/adr.md) — when to write an ADR, MADR body structure,
  the MADR→canonical field/status mappings, ID/filename and `docs/decisions/` conventions, and the
  supersession workflow.
- **Templates:** [`templates/adr.md`](templates/adr.md) (full) plus `adr-minimal.md`,
  `adr-bare.md`, and `adr-bare-minimal.md` variants.
- **Example:** [`examples/adr.example.md`](examples/adr.example.md).

ADRs use `doc_type: adr` with kebab IDs like `adr-0001-short-title`. ADR-specific roles
(`decision_makers`, `consulted`, `informed`) live under the `project` extension namespace, so the
universal frontmatter vocabulary stays small.

## Versioning the standard

Use releases/tags as the contract (`v1.0.0`, `v1.1.0`, `v2.0.0`).

- **Additive change** → tag a new minor (`v1.1.0`), roll consuming repos forward when convenient.
- **Breaking change** → tag a new major (`v2.0.0`), leave old `v1.x` tags intact, migrate repos intentionally.

For private standards repos called by private consumers, enable cross-repository access under the standards repo's **Actions** settings.
