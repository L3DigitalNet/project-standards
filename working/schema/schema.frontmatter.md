# Markdown Frontmatter Standard (PROPOSED V1.1)

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
consumer: 'unknown'
tags: []
aliases: []
related: []
source: []
confidence: 'unknown'
visibility: 'internal'
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
| `related` | Yes | array of strings | Related documents as repo-root-relative paths. |
| `source` | No | array of strings | Sources used to create or support the document. |
| `confidence` | No | string enum | Reliability signal for LLM and human use. |
| `visibility` | No | string enum | Exposure level. |
| `consumer` | No | string enum | Intended consumer/reader/implementer of the doc. |

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

### `consumer`

| Value     | Meaning                                       |
| --------- | --------------------------------------------- |
| `user`    | Intended to be read by humans.                |
| `agent`   | Intended to be read by LLM agents.            |
| `mix`     | Intended to be read by humans and LLM agents. |
| `unknown` | Intended end-user is not known.               |

## Formatting Rules

- Use YAML frontmatter delimited by `---` at the very top of the file.
- Use `snake_case` field names.
- Use ISO date strings in `YYYY-MM-DD` format.
- Use null only where the field is declared nullable (e.g. reviewed).
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

## Canonical key order

Agents **MUST** write keys in this order when present:

```text
schema_version
id
title
description
doc_type
status
created
updated
reviewed
owner
consumer
tags
aliases
related
supersedes
superseded_by
depends_on
applies_to
source
confidence
visibility
publish
project
x_project
```

## Scalar value rules

String values **MUST** be quoted. Single or double quotes are both acceptable; the validator enforces semantic validity, not source quote style.

Correct:

```yaml
title: 'YAML Frontmatter Standard'
id: 'yaml-frontmatter-standard'
created: '2026-06-01'
```

Incorrect:

```yaml
title: YAML Frontmatter Standard
id: yaml-frontmatter-standard
created: 2026-06-01
```

Date values **MUST** be strings in `YYYY-MM-DD` format and **MUST** be quoted.

Boolean values, if ever added to the schema, **MUST** be literal `true` or `false`, never `yes`, `no`, `on`, `off`, `y`, or `n`.

Identifier-like numbers **MUST** be strings:

```yaml
schema_version: '1.0'
zip_code: '01234'
```

Use `null` only if the schema explicitly allows it. Prefer omitting optional fields or using an empty list.

## List rules

Non-empty lists **MUST** use block style:

```yaml
tags:
  - 'yaml'
  - 'frontmatter'
  - 'standards'
```

Empty lists **MUST** use `[]`:

```yaml
aliases: []
related: []
```

List items that are strings **MUST** be quoted.

## Tags

`tags` are controlled vocabulary values for retrieval and classification.

Rules:

1. Do not include the leading `#`.
2. Use lowercase.
3. Use `kebab-case` for multiword tags.
4. Use `/` only for deliberate hierarchy.
5. Do not use spaces.
6. Where a project maintains a tag registry (for example `schemas/tag-registry.md`), every tag **MUST** appear in it before first use. Registry membership is a project-specific policy and is not enforced by the core validator.

Correct:

```yaml
tags:
  - 'yaml'
  - 'frontmatter'
  - 'agent-knowledge'
  - 'topic/metadata'
```

Incorrect:

```yaml
tags:
  - '#yaml'
  - 'Front Matter'
  - 'Agent Knowledge'
```

## Aliases

`aliases` are alternate names, abbreviations, acronyms, or likely search terms for the document.

Rules:

1. Use human-readable strings.
2. Preserve normal capitalization.
3. Use aliases only for genuine alternate names.
4. Empty list is allowed.

Example:

```yaml
aliases:
  - 'Frontmatter Standard'
  - 'YAML Metadata'
  - 'Markdown Metadata'
```

## Links and related documents

All document links — in `related`, `supersedes`, `superseded_by`, and in document bodies — **MUST** be written as a path relative to the repository root, including the file's extension (for example `schemas/markdown-frontmatter.schema.json`). This is the only permitted link form. Bare filenames, bare IDs, and absolute paths are not permitted: they do not resolve deterministically and collide across folders (many folders contain an `index.md`).

Use document-level links, not section-level (`#`) links, unless the schema is revised. Root-relative link form is enforced by `tools/validate_frontmatter.py`.

Correct:

```yaml
related:
  - 'schemas/markdown-frontmatter.schema.json'
  - 'templates/adr.md'
```

Incorrect:

```yaml
related:
  - 'adr.md'
  - 'tag-registry'
  - '/schemas/tag-registry.md'
  - 'schemas/markdown-frontmatter.md#tags'
```

## Description field

`description` is the primary retrieval hint for LLM agents.

Rules:

1. One line only.
2. Maximum 280 characters.
3. No Markdown.
4. State what the document is for and when to use it.
5. Do not include background, history, citations, or prose explanation.

Good:

```yaml
description: 'Specification for writing, validating, and maintaining YAML frontmatter in Markdown knowledge-base documents.'
```

Bad:

```yaml
description: 'This document was created because YAML has a long history and many tools use different parsers...'
```

## Valid frontmatter template

This template lists every universal top-level field in canonical order. Required fields must stay; optional fields may be omitted when unused (they are shown here at their default/empty values). Extension namespaces (`publish`, `project`/`x_project`) are documented under [Extensions](#extensions) and are not repeated here.

```yaml
---
schema_version: '1.0'
id: 'replace-with-kebab-case-id'
title: 'Replace With Human Title'
description: 'One-line description of what this document contains and when an agent should use it.'
doc_type: 'note'
status: 'draft'
created: '2026-06-01'
updated: '2026-06-01'
reviewed: null
owner: ''
consumer: 'unknown'
tags: []
aliases: []
related: []
supersedes: []
superseded_by: null
depends_on: []
applies_to: []
source: []
confidence: 'unknown'
visibility: 'internal'
---
```
