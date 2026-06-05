# Project Standards

Shared standards, schemas, templates, and validation tooling for documentation across all projects. This repository is the **single source of truth**: it _defines_ the standards, and other repositories _consume_ them through a small config file plus a reusable CI workflow — rather than vendoring their own copies.

- **Looking for what's standardised here?** See [Standards](#standards).
- **Adopting the standards in your own repo?** See [Consuming the standards](#consuming-the-standards).

## Repository layout

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

## Standards

The standards this repository defines. Each is a human-readable document under [`standards/`](standards/), enforced by the shared validator.

### Markdown Frontmatter Standard

A small, portable, **tool-neutral** set of YAML frontmatter fields for project documentation, giving every Markdown document consistent metadata for discovery, validation, and LLM/human workflows. It is deliberately **not** an Obsidian, Hugo, Jekyll, Quarto, or Pandoc schema — publishing-tool metadata goes under a `publish` namespace, never at the top level.

- **Standard:** [`standards/markdown-frontmatter.md`](standards/markdown-frontmatter.md)
- **Schema:** [`schemas/markdown-frontmatter.schema.json`](schemas/markdown-frontmatter.schema.json) (JSON Schema Draft 2020-12)
- **Templates:** [`templates/`](templates/) · **Examples:** [`examples/`](examples/)

Minimal frontmatter (the eleven required fields):

```yaml
---
schema_version: '1.1'
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

Standard frontmatter (recommended for most documents):

```yaml
---
schema_version: '1.1'
id: 'replace-with-stable-id'
title: 'Human Title'
description: 'One-sentence description of the document.'
doc_type: 'note'
status: 'draft'
created: '2026-06-02'
updated: '2026-06-02'
reviewed: null
owner: ''
consumer: 'unknown'
tags: []
aliases: []
related: []
source: []
confidence: 'unknown'
visibility: 'internal'
license: null
---
```

See the standard for full field definitions and the controlled values for `doc_type`, `status`, `confidence`, `visibility`, and `consumer`.

### ADR Standard

Architecture Decision Records capture significant, hard-to-reverse decisions, using the [MADR](https://adr.github.io/madr/) format on top of the frontmatter profile above.

- **Standard:** [`standards/adr.md`](standards/adr.md) — when to write an ADR, MADR body structure, the MADR→canonical field/status mappings, ID/filename and `docs/decisions/` conventions, and the supersession workflow.
- **Templates:** [`templates/adr.md`](templates/adr.md) (full) plus `adr-minimal.md`, `adr-bare.md`, and `adr-bare-minimal.md`.
- **Example:** [`examples/adr.example.md`](examples/adr.example.md).

ADRs use `doc_type: adr` with kebab IDs like `adr-0001-short-title`. ADR-specific roles (`decision_makers`, `consulted`, `informed`) live under the `project` extension namespace, keeping the universal vocabulary small.

## Consuming the standards

A consuming repository adopts the standards by adding **two files** — a config that says _which files to check_, and a workflow that _runs the shared validator in CI_. This is the same regardless of which standards you use.

> **Adopting with an agent?** Hand it [`standards/adoption.md`](standards/adoption.md) — a self-contained, step-by-step onboarding & compliance procedure (config, CI pinning, the full frontmatter rules, a worked example, and a compliance checklist).

```text
some-repo/
├── .project-standards.yml          # config — repo root
└── .github/
    └── workflows/
        └── validate-standards.yml  # workflow — must live under .github/workflows/
```

The config may live anywhere as long as the workflow's `config-path` points to it, but the repo root is the default. The workflow has no choice: GitHub only discovers workflows under `.github/workflows/`.

### 1. Config — `.project-standards.yml`

Declares which files the standard applies to:

```yaml
standards_version: 'v1.2.0'

markdown:
  frontmatter:
    schema: 'markdown-frontmatter'
    required: true
    include:
      - 'README.md'
      - 'docs/**/*.md'
    exclude:
      - 'CHANGELOG.md'
      - 'LICENSE.md'
      # Agent-instruction files are harness configuration, not managed docs — never frontmatter.
      - 'CLAUDE.md'
      - 'AGENTS.md'
      - '.claude/**'
      - '.agents/**'
      - '.codex/**'
      - '.github/**'
      - '.obsidian/**'
```

ADRs are **managed** documents (they carry full frontmatter — see the ADR Standard), so do **not** exclude `docs/adr/**` or `docs/decisions/**`; let them validate.

To additionally check that each ADR carries its required body sections, add the opt-in `markdown.adr` block (default off, and enforced by the same frontmatter workflow below):

```yaml
markdown:
  adr:
    require_sections: true # every `doc_type: adr` doc must have the 3 MADR-required `##` sections
```

This asserts `## Context and Problem Statement`, `## Considered Options`, and `## Decision Outcome` are present (exact, level-2 headings; optional MADR sections are never required). See the [ADR Standard](standards/adr.md).

### 2. Workflow — `.github/workflows/validate-standards.yml`

Calls the reusable workflow from this repo:

```yaml
name: Validate project standards

on:
  pull_request:
  push:
    branches:
      - main

jobs:
  validate:
    uses: L3DigitalNet/project-standards/.github/workflows/validate-markdown-frontmatter.yml@v1
    with:
      config-path: '.project-standards.yml'
      standards-ref: 'v1'
```

> **Pin both refs.** `@v1` on the `uses:` line pins the **workflow definition**; `standards-ref` pins the **validator + bundled schema** that gets installed. Keep them on the same major (`v1`) so your validation can't drift onto unreleased changes. (`standards-ref` defaults to `v1`, but set it explicitly to make the pin obvious; use a full version like `v1.2.0` for an immutable pin.)

The reusable workflow installs the validator with `uv tool install git+...`, so the consuming repo does not vendor the schema or the Python code — the bundled schema travels with the install.

### 3. Optional — Markdown body linting

The frontmatter workflow validates the YAML _metadata_ block. A **separate, opt-in** reusable workflow lints the Markdown _body_ (heading levels, list style, etc.) with [`markdownlint-cli2`](https://github.com/DavidAnson/markdownlint-cli2). It is independent so frontmatter-only consumers never inherit a Node toolchain:

```yaml
jobs:
  lint-markdown:
    uses: L3DigitalNet/project-standards/.github/workflows/lint-markdown.yml@v1
    with:
      globs: '**/*.md' # optional; this is the default
```

Seed your repo's rules by copying this repo's published [`.markdownlint.json`](.markdownlint.json) (the workflow auto-discovers it; the action carries its own Node runtime, so no committed Node project is needed). The two workflows are adopted independently — run either, or both.

The published config states **every** rule explicitly (not just the customised ones), so your linting result is deterministic and isn't shadowed by a contributor's personal editor/global markdownlint settings. Because the explicit values are pinned to a specific markdownlint version, pin the action by major tag (`@v23`) and re-check the config when you bump it. An annotated, commented copy of the same rule set lives at [`working/linting-formatting/markdownlint.jsonc`](working/linting-formatting/markdownlint.jsonc).

### Pin to a release tag, not `main`

Reference the reusable workflow by **major tag** (`@v1`), not `@main`. Tags are the contract: a repo that passed validation yesterday should not fail today because the standard changed. The major tag is safe to track because any change that could fail a previously-passing repo — a new required field, a stricter rule — ships only as a new major (`@v2`); `@v1` receives just bug fixes and backward-compatible updates. For an immutable pin, use a full version tag (`@v1.0.1`) or a commit SHA. Use `@main` only for this repo's own development or deliberate test repos.

### Run the check locally (optional)

Validate before pushing, using the released tool directly — no checkout of this repo required:

```bash
uvx --from git+https://github.com/L3DigitalNet/project-standards@v1 \
  validate-frontmatter --config .project-standards.yml
```

The validator exits `0` when all checked files pass and non-zero when any file fails, printing file-specific errors.

## Versioning

Releases follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html), but the contract is the **consuming repo's validation outcome** — a release's level reflects the worst-case impact of any change across the standard, schema, validator, and workflow.

- **PATCH / MINOR** → safe to inherit on a moving major pin (`@v1`); a repo that passed yesterday still passes today.
- **MAJOR** → may newly-fail a previously-passing repo (a new required field, a stricter rule, even a validator bug fix); old `vN.x` tags stay intact, and consumers migrate intentionally.

See [`standards/versioning.md`](standards/versioning.md) for the full classification table, the previously-passing rule, and release requirements.

For private standards repos called by private consumers, enable cross-repository access under this repo's **Actions** settings.

## Developing this repository

Working on the standards or the validator itself:

```bash
uv sync --dev                                                # set up the environment
uv run pytest                                                # validator tests
uv run ruff check .                                          # lint
uv run pyright                                               # type-check
uv run validate-frontmatter --config .project-standards.yml  # dogfood the standard
```

## License

This project is licensed under the [Apache License 2.0](LICENSE).
