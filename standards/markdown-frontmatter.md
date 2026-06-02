---
schema_version: '1.0'
id: 'markdown-frontmatter-standard'
title: 'Markdown Frontmatter Standard'
description: 'Canonical, tool-neutral metadata profile for project Markdown documents.'
doc_type: 'reference'
status: 'active'
created: '2026-06-02'
updated: '2026-06-02'
reviewed: null
owner: ''
tags:
  - markdown
  - metadata
  - frontmatter
  - standard
aliases:
  - frontmatter-standard
related:
  - 'schemas/markdown-frontmatter.schema.json'
source: []
confidence: 'high'
visibility: 'internal'
license: null
---

# Markdown Frontmatter Standard

## Purpose

This standard defines a small, portable, tool-neutral set of YAML frontmatter fields for project documentation. It is **not** an Obsidian schema, a Hugo/Jekyll/Quarto schema, or a publishing schema. It is an internal project-document metadata standard intended to be portable across GitHub repositories, Markdown tooling, LLM workflows, and future publishing/export systems.

The machine-readable contract is [`schemas/markdown-frontmatter.schema.json`](../schemas/markdown-frontmatter.schema.json) (JSON Schema Draft 2020-12). The validator [`tools/validate_frontmatter.py`](../tools/validate_frontmatter.py) enforces this schema in CI and locally.

### Files that never carry frontmatter

Agent-instruction files are harness configuration, not managed documents, and must **never** carry frontmatter: `CLAUDE.md`, `AGENTS.md`, and anything under `.claude/`, `.agents/`, or `.codex/`. Consuming repositories exclude these in `.project-standards.yml` rather than adding metadata to them. The repo's human-facing root `README.md` is a managed document, but a repository may exclude it if it prefers not to render a frontmatter table on its landing page.

## Profiles

### Minimal frontmatter

Every managed document supports this minimal form. These eleven fields are **required**.

```yaml
---
schema_version: '1.0'
id: 'replace-with-stable-id'
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

### Standard frontmatter

Use this richer form for most project documentation.

```yaml
---
schema_version: '1.0'
id: 'replace-with-stable-id'
title: 'Human Title'
description: 'One-sentence description of the document.'
doc_type: 'note'
status: 'draft'
created: 'YYYY-MM-DD'
updated: 'YYYY-MM-DD'
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

## Field Definitions

| Field | Required | Type | Purpose |
| --- | --: | --- | --- |
| `schema_version` | Yes | string | Version of this metadata schema. |
| `id` | Yes | string | Stable document identifier independent of file path. |
| `title` | Yes | string | Human-readable document title. |
| `description` | Yes | string | One-sentence description of document purpose/content. |
| `doc_type` | Yes | string enum | Document type. Avoid `type` to reduce future publishing-tool collisions. |
| `status` | Yes | string enum | Lifecycle state of the document. |
| `created` | Yes | date string | Original creation date in `YYYY-MM-DD` format. |
| `updated` | Yes | date string | Last meaningful content update in `YYYY-MM-DD` format. |
| `reviewed` | No | date string or null | Last correctness review date. Distinct from `updated`. |
| `owner` | No | string | Person, team, repo, or role responsible for maintenance. |
| `tags` | Yes | array of strings | Discovery labels. Prefer lowercase kebab-case. |
| `aliases` | Yes | array of strings | Alternate names, abbreviations, or likely search terms. |
| `related` | Yes | array of strings | Related document IDs or relative paths. |
| `source` | No | array of strings | Sources used to create or support the document. |
| `confidence` | No | string enum | Reliability signal for LLM and human use. |
| `visibility` | No | string enum | Intended audience or exposure level. |
| `license` | No | string or null | License or reuse terms, if applicable. |

Optional relationship fields are also permitted when needed: `supersedes` (array), `superseded_by` (string or null), `depends_on` (array), and `applies_to` (array).

## Controlled Values

### `doc_type`

| Value       | Meaning                                                         |
| ----------- | --------------------------------------------------------------- |
| `index`     | Navigation or landing page.                                     |
| `note`      | General-purpose working note.                                   |
| `concept`   | Explanation of an idea, model, pattern, or principle.           |
| `reference` | Stable factual reference material.                              |
| `runbook`   | Operational procedure.                                          |
| `spec`      | Implementer-ready build/change specification.                   |
| `plan`      | Proposed approach, not necessarily accepted.                    |
| `adr`       | Architecture Decision Record.                                   |
| `decision`  | Smaller decision note that does not require full ADR structure. |
| `research`  | Findings from investigation or comparison.                      |
| `template`  | Reusable document, prompt, or content template.                 |
| `log`       | Chronological record.                                           |
| `prompt`    | LLM prompt or instruction artifact.                             |
| `schema`    | Metadata, validation, or data-structure definition.             |

### `status`

| Value        | Meaning                                            |
| ------------ | -------------------------------------------------- |
| `draft`      | Still being written or formed.                     |
| `active`     | Current and usable.                                |
| `review`     | Needs checking before relying on it.               |
| `deprecated` | Still present but should not be used for new work. |
| `archived`   | Historical only.                                   |
| `superseded` | Replaced by another document.                      |
| `stub`       | Placeholder or intentionally incomplete.           |

`stub` is a lifecycle **status**, not a document type. Do not create `doc_type: stub`.

### `confidence`

| Value     | Meaning                                                  |
| --------- | -------------------------------------------------------- |
| `high`    | Reviewed, sourced, or based on durable direct knowledge. |
| `medium`  | Reasonable but not recently reviewed or fully sourced.   |
| `low`     | Uncertain, provisional, or requires validation.          |
| `unknown` | No confidence assessment has been made.                  |

### `visibility`

| Value      | Meaning                         |
| ---------- | ------------------------------- |
| `private`  | Personal or sensitive material. |
| `internal` | Internal project material.      |
| `public`   | Safe for public release.        |

## Formatting Rules

- Use YAML frontmatter delimited by `---` at the very top of the file.
- Use `snake_case` field names.
- Use ISO date strings in `YYYY-MM-DD` format.
- Use `null` for unknown scalar values.
- Use `[]` for empty lists.
- Quote strings by default.
- Prefer lowercase kebab-case for tags.
- Prefer stable kebab-case IDs for ordinary documents.
- Prefer prefixed numeric IDs for ADRs, such as `adr-0001-use-netbox-as-source-of-truth`.
- Keep `updated` separate from `reviewed`.
- Use `doc_type`, not `type`.
- Use `related` for broad relationships.
- Use optional relationship fields (`supersedes`, `superseded_by`, `depends_on`, `applies_to`) only when needed.
- Put publishing-tool-specific metadata under the `publish` namespace, not as top-level fields.

## Extensions

The schema rejects unknown top-level fields. Project- and tool-specific metadata belongs in one of the sanctioned extension objects, each of which accepts any structure:

- **`publish`** — future publishing/export metadata.
- **`project`** — project-specific extensions.
- **`x_project`** — alternate namespace for project-specific extensions.

```yaml
publish:
  slug: ''
  permalink: ''
  draft: false
  weight: null
```

```yaml
project:
  service: 'netbox'
  environment: 'home-lab'
```

The field policy is: universal fields at the top level; project-specific fields under `project` or `x_project`; publishing-specific fields under `publish`.
