# Standards

This directory holds the **governing standards** this repository defines. Each standard is a self-contained **bundle** — open its folder and the standard renders.

| Standard | What it governs | Bundle | Adopt |
| --- | --- | --- | --- |
| Markdown Frontmatter | Canonical, tool-neutral YAML metadata for Markdown documents | [markdown-frontmatter/](markdown-frontmatter/) | [adopt](markdown-frontmatter/adopt.md) |
| ADR | Architecture Decision Records (MADR on the frontmatter profile) | [adr/](adr/) | [adopt](adr/adopt.md) |
| Python Tooling SSOT | Python stack, layout, CI gate, and agent instructions | [python-tooling/](python-tooling/) | [adopt](python-tooling/adopt.md) |
| Markdown Tooling | Markdown/structured-text linting + formatting (markdownlint, Prettier, EditorConfig) | [markdown-tooling/](markdown-tooling/) | [adopt](markdown-tooling/adopt.md) |
| Project Specification | Tiered spec format, stable IDs, and a `project-standards spec` CLI | [project-spec/](project-spec/) | [adopt](project-spec/adopt.md) |
| CLI Documentation | User-facing CLI usage docs: help text, usage references, man pages, CI drift checks | [cli-documentation/](cli-documentation/) | [adopt](cli-documentation/adopt.md) |
| Python Coding | Code-shape and agent-behavior rules for Python (companion to Python Tooling SSOT) | [python-coding/](python-coding/) | — (**in-development draft**, reference-only; not yet released for adoption) |
| Standard Bundle Authoring | The contract every standard bundle must declare (`standard.toml`, authorities, relationships, namespaces) | [standard-bundle-authoring/](standard-bundle-authoring/) | — (**internal/reference**; governs how this repo authors standards, not consumer-adopted) |

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
├── standard.toml  # REQUIRED — the machine manifest (see standard-bundle-authoring/)
├── adopt.md       # REQUIRED for adoptable standards — how to adopt (internal/draft: a non-adoptable marker instead)
├── templates/     # OPTIONAL — copy-paste scaffolds (placeholders; not frontmatter-validated)
├── examples/      # OPTIONAL — validated worked examples (real frontmatter; dogfooded)
└── resources/     # OPTIONAL — rationale/research notes (validated) — see project-spec/, cli-documentation/
```

Every standard ships a `README.md` and — per the [Standard Bundle Authoring Standard](standard-bundle-authoring/) — a `standard.toml` machine manifest; the existing bundles are retrofitted with theirs in `SPEC-MT01` Step 05. `adopt.md` is present for every standard **released for adoption** — including CLI-enforced ones like [project-spec/](project-spec/) — while only internal (`adoption = "none"`) standards like [standard-bundle-authoring/](standard-bundle-authoring/) and unreleased-draft documents like [python-coding/](python-coding/) carry an explicit non-adoptable marker instead. Beyond those, a standard may be doc-only (no `templates/` or `examples/`) — see [markdown-tooling/](markdown-tooling/), or [python-tooling/](python-tooling/) which adds a [`build-backend.md`](python-tooling/build-backend.md) appendix; [python-coding/](python-coding/) ships as an **in-development draft** (reference-only, unregistered, excluded from frontmatter validation until released).

## Not a governed standard

[`../meta/versioning.md`](../meta/versioning.md) describes how _this repository_ is versioned and consumed. It is a meta document, not a standard you adopt.
