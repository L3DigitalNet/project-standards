# Standards

This directory holds the **governing standards** this repository defines. Each standard is a self-contained **bundle**. Its mutable root README is a current-family landing page that routes to the exact immutable version selected by Catalog 5.

The generated [standards catalog](catalog.md) exposes validated V2 family, payload, channel, capability, relationship, resource, provider, and managed-output facts. Regenerate it with `uv run project-standards standards render-catalog --root .`; use `--check` in verification to detect drift.

Consumer packages are enabled through `.standards/config.toml` and reconciled as one plan. Each family `adopt.md` points to its current immutable payload guide; those guides own package-specific suitability, closed options, outputs, migration, verification, and troubleshooting. Legacy V1 fragments and copy instructions are migration evidence only, never active V5 adoption authority.

| Standard | What it governs | Package | Catalog role | Bundle | Adopt |
| --- | --- | --- | --- | --- | --- |
| Markdown Frontmatter | Canonical, tool-neutral YAML metadata for Markdown documents | 1.4 | default | [markdown-frontmatter/](markdown-frontmatter/) | [adopt](markdown-frontmatter/adopt.md) |
| ADR | Architecture Decision Records (MADR on the frontmatter profile) | 1.2 | default | [adr/](adr/) | [adopt](adr/adopt.md) |
| Python Tooling SSOT | Python stack, layout, CI gate, and agent instructions | 1.7 | default | [python-tooling/](python-tooling/) | [adopt](python-tooling/adopt.md) |
| Markdown Tooling | Markdown/structured-text linting + formatting (markdownlint, Prettier, EditorConfig) | 1.7 | default | [markdown-tooling/](markdown-tooling/) | [adopt](markdown-tooling/adopt.md) |
| Project Specification | Tiered spec format, stable IDs, and a `project-standards spec` CLI | 1.4 | default | [project-spec/](project-spec/) | [adopt](project-spec/adopt.md) |
| CLI Documentation | User-facing CLI usage docs: help text, usage references, man pages, CI drift checks | 1.3 | default | [cli-documentation/](cli-documentation/) | [adopt](cli-documentation/adopt.md) |
| Agent Handoff | Repository-local project knowledge, bounded session continuity, repo-local skill and hooks, and conformance tooling | 1.4 | default | [agent-handoff/](agent-handoff/) | [adopt](agent-handoff/adopt.md) |
| Python Coding | Code-shape and agent-behavior rules for Python (companion to Python Tooling SSOT) | 0.6 | reference-only | [python-coding/](python-coding/) | — (**in-development draft**; not released for adoption) |
| Standard Bundle Authoring | The V2 family, payload, catalog, provider, relationship, and ownership contract | 2.5 | internal | [standard-bundle-authoring/](standard-bundle-authoring/) | — (**internal/reference**; governs this repository's packages) |

## Table of Contents

- [Standards](#standards)
  - [Table of Contents](#table-of-contents)
  - [Bundle anatomy](#bundle-anatomy)
  - [Not a governed standard](#not-a-governed-standard)

## Bundle anatomy

Every standard follows the same shape, so adding a new one is mechanical:

```text
standards/<standard-id>/
├── README.md                 # REQUIRED — family landing page
├── standard.toml             # REQUIRED — V2 family index and payload digests
└── versions/<version>/
    ├── payload.toml          # REQUIRED — immutable version contract
    ├── README.md             # REQUIRED — canonical versioned standard
    ├── config.schema.json    # REQUIRED — package options
    ├── adopt.md              # REQUIRED for consumer packages
    └── ...                   # Declared resources, providers, templates, and outputs
```

Every family ships a landing-page `README.md` and a V2 `standard.toml` index. Each indexed version points to one immutable `versions/<version>/payload.toml`; its aggregate digest covers the complete declared payload inventory. Consumer payloads include an adoption guide, while reference-only and internal payloads do not. Catalog 5 selects the seven default consumer packages shown above and advertises Python Coding and Standard Bundle Authoring only in their non-consumer roles. Standard-package docs under `standards/**` remain excluded from this repository's local markdown-frontmatter corpus by ADR 0015.

## Not a governed standard

[`../meta/versioning.md`](../meta/versioning.md) describes how _this repository_ is versioned and consumed. It is a meta document, not a standard you adopt.
