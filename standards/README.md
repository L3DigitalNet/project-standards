# Standards

This directory holds the **governing standards** this repository defines. Each standard is a self-contained **bundle** — open its folder and the standard renders.

| Standard | What it governs | Bundle | Adopt |
| --- | --- | --- | --- |
| Markdown Frontmatter | Canonical, tool-neutral YAML metadata for Markdown documents | [markdown-frontmatter/](markdown-frontmatter/) | [adopt](markdown-frontmatter/adopt.md) |
| ADR | Architecture Decision Records (MADR on the frontmatter profile) | [adr/](adr/) | [adopt](adr/adopt.md) |
| Python Tooling SSOT | Python stack, layout, CI gate, and agent instructions | [python-tooling/](python-tooling/) | [adopt](python-tooling/adopt.md) |
| Markdown Tooling | Markdown/structured-text linting + formatting (markdownlint, Prettier, EditorConfig) | [markdown-tooling/](markdown-tooling/) | [adopt](markdown-tooling/adopt.md) |
| Project Specification | Tiered spec format, stable IDs, and a `project-standards spec` CLI | [project-spec/](project-spec/) | [adopt](project-spec/adopt.md) |
| Python Coding | Code-shape and agent-behavior rules for Python (companion to Python Tooling SSOT) | [python-coding/](python-coding/) | — (**in-development draft**, reference-only; not yet released for adoption) |

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

A standard may be doc-only (`README.md` + `adopt.md`, no `templates/` or `examples/`) — see [markdown-tooling/](markdown-tooling/), or [python-tooling/](python-tooling/) which adds a [`build-backend.md`](python-tooling/build-backend.md) appendix. A standard with no materializeable artifacts and no adoption workflow has only a `README.md` — currently just [python-coding/](python-coding/), which ships as an **in-development draft**: reference-only, unregistered (no contract version), and excluded from frontmatter validation until released.

## Not a governed standard

[`../meta/versioning.md`](../meta/versioning.md) describes how _this repository_ is versioned and consumed. It is a meta document, not a standard you adopt.
