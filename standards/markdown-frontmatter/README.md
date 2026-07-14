# Markdown Frontmatter Standard

**Current package:** `markdown-frontmatter@1.2`. **Document contract:** `1.1` (declared per document as `schema_version`; selected independently through `standards.markdown-frontmatter.config.contract_version`). See [Versioning](#versioning).

## Purpose

This standard defines a portable YAML frontmatter profile for project Markdown documents. It is intended for documentation that must be searchable, classifiable, maintainable, and useful to both humans and LLM agents.

It is not an Obsidian schema, a Hugo/Jekyll/Quarto schema, or a publishing schema. Publishing-specific and project-specific data belongs in the sanctioned extension objects described in [Field Values](field-values.md#extensions).

A **managed document** is any Markdown file this standard governs. Consuming repositories choose managed paths through the selected package options in `.standards/config.toml`; managed files must carry conformant frontmatter and validate against the selected schema.

## Standard Layout

The standard is split by responsibility:

| Page | Use it for |
| --- | --- |
| [Structure Requirements](structure.md) | Hard schema, key-order, quoting, ID, list, validation, and compatibility rules. |
| [Field Values](field-values.md) | Field meanings, lifecycle triggers, ownership, canonical global tags, aliases, relationship use, and repository-local extension policy. |
| [Adoption Procedure](adopt.md) | End-to-end setup in a consuming repository. |
| [Markdown Frontmatter Skill](skills/markdown-frontmatter/SKILL.md) | Standard-owned agent operating layer installed into adopting repos. |
| [Repository Frontmatter ADR template](templates/repository-frontmatter-adr.md) | ADR template for documenting a repo's own metadata policy before or during adoption. |

The bundled JSON Schema is authoritative for schema validation. The full local contract also includes ID validation, optional reference validation, and `format-frontmatter` checks for canonical source style.

## Core Profile

Every managed document has eleven required fields:

```yaml
---
schema_version: '1.1'
id: 'note-xxxxxx-human-title'
title: 'Human Title'
description: 'One-sentence description of the document.'
doc_type: 'note'
status: 'draft'
created: 'YYYY-MM-DD'
updated: 'YYYY-MM-DD'
tags: []
aliases: []
related: []
---
```

Most project documentation should use the standard profile, which adds the optional fields that carry ownership, audience, evidence, and exposure policy:

```yaml
---
schema_version: '1.1'
id: 'note-xxxxxx-human-title'
title: 'Human Title'
description: 'One-sentence description of the document.'
doc_type: 'note'
status: 'draft'
created: 'YYYY-MM-DD'
updated: 'YYYY-MM-DD'
reviewed: null
owner: 'repo-maintainers'
consumer: 'mix'
tags: []
aliases: []
related: []
source: []
confidence: 'unknown'
visibility: 'internal'
license: null
---
```

See [Structure Requirements](structure.md#profiles) for the exact structural contract and [Field Values](field-values.md#expected-standard-profile) for how to choose values.

## Managed Scope

Agent-instruction and agent-skill files are harness configuration, not managed documents, and must never carry managed-document frontmatter:

- `CLAUDE.md`
- `AGENTS.md`
- `.claude/**`
- `.agents/**`
- `.codex/**`

Exclude those files through the package's `exclude` option instead of adding document metadata to them. A repository may also exclude its root `README.md` if it prefers not to render a frontmatter table on its public landing page.

## Repo-Local Skill

This standard owns the `markdown-frontmatter` agent skill at [`skills/markdown-frontmatter/`](skills/markdown-frontmatter/). Adoption installs it into each consuming repository at `.agents/skills/markdown-frontmatter` so Claude Code and Codex CLI use the same repo-local operating layer for frontmatter authoring, ID generation, and validation.

The installed skill is intentionally excluded from managed-document frontmatter validation via `.agents/**`. Its `SKILL.md` carries agent-skill metadata, not this standard's document metadata profile.

This standard is deliberately tool-neutral about the Markdown body. Body formatting and linting live in the companion [Markdown Tooling Standard](../markdown-tooling/README.md).

## Repository Policy ADR

Structural conformance is not enough for consistent metadata. Each consuming repository should record a small ADR, based on [`templates/repository-frontmatter-adr.md`](templates/repository-frontmatter-adr.md), that defines:

- which paths are governed and which are excluded;
- the default frontmatter profile;
- repo-local owner roles;
- `doc_type`, `status`, `consumer`, `confidence`, and `visibility` rules;
- canonical repo tags and allowed extensions to the global tag set;
- relationship-field and source-field conventions;
- migration and confirmation steps.

This repo dogfoods that expectation in [`docs/adr/adr-0014-markdown-frontmatter-field-value-policy.md`](../../docs/adr/adr-0014-markdown-frontmatter-field-value-policy.md).

## Versioning

Three independent identities are in play:

- **Package payload `1.2`** selects immutable package resources, providers, and managed outputs through the consumer catalog.
- **Document contract `1.1`** is selected by `contract_version` and recorded in each document as `schema_version`. It changes when the metadata fields or controlled vocabularies change.
- **Tool/catalog release `5.x`** identifies the control-plane implementation and catalog snapshot that resolved and applied the package. It does not replace either package or document-contract versioning.

This documentation split and ADR-template addition do not add fields, remove fields, or change controlled vocabularies. New documents should still set `schema_version: '1.1'`.

Release classification and the previously-passing rule are defined in [`meta/versioning.md`](../../meta/versioning.md).

## Validation

Run schema, ID, and reference validation from a consuming repo:

```bash
uv run project-standards validate
```

That command runs schema validation, ID-format validation, and cross-file reference validation. Reference validation is a no-op unless the repo enables it.

Run the formatter check when you need to verify canonical source style, including quote style, key order, and list layout:

```bash
uv run format-frontmatter --check
```

The standalone commands are also available:

```bash
uv run validate-frontmatter
uv run validate-id
uv run validate-references
```

See [Structure Requirements](structure.md#validation) for exit codes and validation scope.
