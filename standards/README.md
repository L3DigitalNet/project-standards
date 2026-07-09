# Standards

This directory holds the **governing standards** this repository defines. Each standard is a self-contained **bundle** — open its folder and the standard renders.

The generated [standards catalog](catalog.md) exposes manifest-derived lifecycle, version, capability, relationship, resource, provider, artifact-provenance, and repo-local skill facts. Regenerate it with `uv run project-standards standards render-catalog --root .`; use `--check` in verification to detect drift.

| Standard | What it governs | Bundle | Adopt |
| --- | --- | --- | --- |
| Markdown Frontmatter | Canonical, tool-neutral YAML metadata for Markdown documents | [markdown-frontmatter/](markdown-frontmatter/) | [adopt](markdown-frontmatter/adopt.md) |
| ADR | Architecture Decision Records (MADR on the frontmatter profile) | [adr/](adr/) | [adopt](adr/adopt.md) |
| Python Tooling SSOT | Python stack, layout, CI gate, and agent instructions | [python-tooling/](python-tooling/) | [adopt](python-tooling/adopt.md) |
| Markdown Tooling | Markdown/structured-text linting + formatting (markdownlint, Prettier, EditorConfig) | [markdown-tooling/](markdown-tooling/) | [adopt](markdown-tooling/adopt.md) |
| Project Specification | Tiered spec format, stable IDs, and a `project-standards spec` CLI | [project-spec/](project-spec/) | [adopt](project-spec/adopt.md) |
| CLI Documentation | User-facing CLI usage docs: help text, usage references, man pages, CI drift checks | [cli-documentation/](cli-documentation/) | [adopt](cli-documentation/adopt.md) |
| Python Coding | Code-shape and agent-behavior rules for Python (companion to Python Tooling SSOT; package version 0.4) | [python-coding/](python-coding/) | — (**in-development draft**, reference-only; not yet released for adoption) |
| Standard Bundle Authoring | The contract every standard bundle must declare (`standard.toml`, authorities, relationships, namespaces; package version 1.0) | [standard-bundle-authoring/](standard-bundle-authoring/) | — (**internal/reference**; governs how this repo authors standards, not consumer-adopted) |

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
├── templates/     # OPTIONAL — copy-paste scaffolds, including placeholder frontmatter when teaching it
├── examples/      # OPTIONAL — worked examples that may carry standard-specific frontmatter
├── skills/        # OPTIONAL — standard-owned agent skills installed by adoption
└── resources/     # OPTIONAL — rationale/research notes — see project-spec/, cli-documentation/
```

Every standard ships a `README.md` and — per the [Standard Bundle Authoring Standard](standard-bundle-authoring/) — a `standard.toml` machine manifest with a non-empty package version. `adopt.md` is present for every standard **released for adoption** — including CLI-enforced ones like [project-spec/](project-spec/) — while only internal (`adoption = "none"`) standards like [standard-bundle-authoring/](standard-bundle-authoring/) and unreleased-draft documents like [python-coding/](python-coding/) carry an explicit non-adoptable marker instead. Beyond those, a standard may be doc-only (no `templates/` or `examples`) — see [markdown-tooling/](markdown-tooling/), may ship standard-owned skills — see [markdown-frontmatter/](markdown-frontmatter/), may seed support scaffolding while leaving authored content to a CLI — see [project-spec/](project-spec/), or may add appendices such as [python-tooling/](python-tooling/)'s [`build-backend.md`](python-tooling/build-backend.md). Standard-package docs under `standards/**` are excluded from this repository's local markdown-frontmatter corpus by ADR 0015; [python-coding/](python-coding/) additionally ships as an **in-development draft** (reference-only and unregistered as a consumer-selectable contract).

## Not a governed standard

[`../meta/versioning.md`](../meta/versioning.md) describes how _this repository_ is versioned and consumed. It is a meta document, not a standard you adopt.
