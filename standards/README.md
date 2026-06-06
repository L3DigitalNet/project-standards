# Standards

This directory holds the **governing standards** this repository defines. Each standard is a self-contained **bundle** — open its folder and the standard renders.

| Standard | What it governs | Bundle | Adopt |
| --- | --- | --- | --- |
| Markdown Frontmatter | Canonical, tool-neutral YAML metadata for Markdown documents | [markdown-frontmatter/](markdown-frontmatter/) | [adopt](markdown-frontmatter/adopt.md) |
| ADR | Architecture Decision Records (MADR on the frontmatter profile) | [adr/](adr/) | [adopt](adr/adopt.md) |
| Python Tooling SSOT | Python stack, layout, CI gate, and agent instructions | [python-tooling/](python-tooling/) | [adopt](python-tooling/adopt.md) |

## Bundle anatomy

Every standard follows the same shape, so adding a new one is mechanical:

```text
standards/<standard-id>/
├── README.md      # REQUIRED — the governing standard itself
├── adopt.md       # REQUIRED — how to adopt this standard
├── templates/     # OPTIONAL — copy-paste scaffolds (placeholders; not frontmatter-validated)
└── examples/      # OPTIONAL — validated worked examples (real frontmatter; dogfooded)
```

A standard may be doc-only (just `README.md` + `adopt.md`) — see [python-tooling/](python-tooling/).

## Not a governed standard

[`../meta/versioning.md`](../meta/versioning.md) describes how _this repository_ is versioned and consumed. It is a meta document, not a standard you adopt.
