# Standards

This directory holds the **governing standards** this repository defines. Each standard is a self-contained **bundle** — open its folder and the standard renders.

| Standard | What it governs | Bundle | Adopt |
| --- | --- | --- | --- |
| Markdown Frontmatter | Canonical, tool-neutral YAML metadata for Markdown documents | [markdown-frontmatter/](markdown-frontmatter/) | [adopt](markdown-frontmatter/adopt.md) |
| ADR | Architecture Decision Records (MADR on the frontmatter profile) | [adr/](adr/) | [adopt](adr/adopt.md) |
| Python Tooling SSOT | Python stack, layout, CI gate, and agent instructions | [python-tooling/](python-tooling/) | [adopt](python-tooling/adopt.md) |
| Markdown Tooling | Markdown/structured-text linting + formatting (markdownlint, Prettier, EditorConfig) | [markdown-tooling/](markdown-tooling/) | [adopt](markdown-tooling/adopt.md) |
| Python Coding | Code-shape and agent-behavior rules for Python (companion to Python Tooling SSOT) | [python-coding/](python-coding/) | — (reference only; no artifacts to materialize) |

## Table of Contents

- [Standards](#standards)
  - [Table of Contents](#table-of-contents)
  - [Bundle anatomy](#bundle-anatomy)
  - [Not a governed standard](#not-a-governed-standard)

## Bundle anatomy

Every standard follows the same shape, so adding a new one is mechanical:

```text
standards/<standard-id>/
├── README.md      # REQUIRED — the governing standard itself
├── adopt.md       # REQUIRED — how to adopt this standard
├── templates/     # OPTIONAL — copy-paste scaffolds (placeholders; not frontmatter-validated)
└── examples/      # OPTIONAL — validated worked examples (real frontmatter; dogfooded)
```

A standard may be doc-only (just `README.md` + `adopt.md`) — see [python-tooling/](python-tooling/). A standard with no materializeable artifacts and no adoption workflow (currently [python-coding/](python-coding/)) has only a `README.md`.

## Not a governed standard

[`../meta/versioning.md`](../meta/versioning.md) describes how _this repository_ is versioned and consumed. It is a meta document, not a standard you adopt.
