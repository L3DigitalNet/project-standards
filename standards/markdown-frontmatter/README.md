---
schema_version: '1.1'
id: 'markdown-frontmatter-standard'
title: 'Markdown Frontmatter Standard'
description: 'Canonical, tool-neutral metadata profile for project Markdown documents.'
doc_type: 'reference'
status: 'active'
created: '2026-06-02'
updated: '2026-06-07'
reviewed: null
owner: ''
consumer: 'mix'
tags:
  - 'markdown'
  - 'metadata'
  - 'frontmatter'
  - 'standard'
aliases:
  - 'frontmatter-standard'
related:
  - 'src/project_standards/schemas/markdown-frontmatter.schema.json'
  - 'meta/versioning.md'
  - 'standards/markdown-tooling/README.md'
source: []
confidence: 'high'
visibility: 'internal'
license: null
---

# Markdown Frontmatter Standard

**Contract version:** `1.1` (declared per document as `schema_version`; selected by consumers via `markdown.frontmatter.version`). See [`meta/versioning.md`](../../meta/versioning.md#per-standard-contract-versions).

## Purpose

This standard defines a small, portable, tool-neutral set of YAML frontmatter fields for project documentation. It is **not** an Obsidian schema, a Hugo/Jekyll/Quarto schema, or a publishing schema. It is an internal project-document metadata standard intended to be portable across GitHub repositories, Markdown tooling, LLM workflows, and future publishing/export systems.

A **managed document** is any Markdown file this standard governs — one expected to carry conformant frontmatter and to validate against the schema. Consuming repositories declare which paths are managed, and which are excluded, in `.project-standards.yml`.

The machine-readable contract is [`src/project_standards/schemas/markdown-frontmatter.schema.json`](../../src/project_standards/schemas/markdown-frontmatter.schema.json) (JSON Schema Draft 2020-12). The validator [`src/project_standards/validate_frontmatter.py`](../../src/project_standards/validate_frontmatter.py) enforces this schema in CI and locally. Where this document and that schema disagree, **the schema is authoritative**: it is what the validator checks, and this document explains and expands on it.

This document specifies **schema version 1.1**, an additive revision that introduces the `consumer` field. Conforming documents set `schema_version: '1.1'` (see [Versioning and compatibility](#versioning-and-compatibility)).

### Files that never carry frontmatter

Agent-instruction files are harness configuration, not managed documents, and must **never** carry frontmatter: `CLAUDE.md`, `AGENTS.md`, and anything under `.claude/`, `.agents/`, or `.codex/`. Consuming repositories exclude these in `.project-standards.yml` rather than adding metadata to them. The repo's human-facing root `README.md` is a managed document, but a repository may exclude it if it prefers not to render a frontmatter table on its landing page.

This standard is deliberately tool-neutral about the Markdown _body_. How a document's body and adjacent config files are formatted and linted (Prettier, markdownlint, EditorConfig) is governed by the companion [Markdown Tooling Standard](../markdown-tooling/README.md).

## Profiles

### Minimal frontmatter

Every managed document supports this minimal form. These eleven fields are **required**.

```yaml
---
schema_version: '1.1'
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
schema_version: '1.1'
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
license: null
---
```

## Field definitions

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
| `consumer` | No | string enum | Intended reader/consumer of the document. |
| `tags` | Yes | array of strings | Discovery labels. Prefer lowercase kebab-case. |
| `aliases` | Yes | array of strings | Alternate names, abbreviations, or likely search terms. |
| `related` | Yes | array of strings | Related documents as repo-root-relative paths. |
| `source` | No | array of strings | Sources used to create or support the document. |
| `confidence` | No | string enum | Reliability signal for LLM and human use. |
| `visibility` | No | string enum | Exposure level. |
| `license` | No | string or null | License or reuse terms, if applicable. |

Optional relationship fields are also permitted when needed: `supersedes` (array), `superseded_by` (string or null), `depends_on` (array), and `applies_to` (array).

## Controlled values

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
| `unknown` | Intended consumer is not known.               |

## Formatting rules

General conventions. Topic-specific rules live in their own sections; this list covers only the rules with no dedicated home, then points to the rest.

- Use YAML frontmatter delimited by `---` at the very top of the file.
- Use `snake_case` field names.
- Use `doc_type`, not `type`.
- Keep `updated` separate from `reviewed` (see Field definitions).
- Prefer stable kebab-case IDs for ordinary documents; prefer prefixed numeric IDs for ADRs, such as `adr-0001-use-netbox-as-source-of-truth`. (The schema's `id` pattern is `^[a-z0-9][a-z0-9._-]*$`, so dots and underscores are also accepted after the first character — kebab-case is the recommended convention, not the full permitted set.)
- Use optional relationship fields (`supersedes`, `superseded_by`, `depends_on`, `applies_to`) only when needed.

Detailed rules live in dedicated sections: **Scalar value rules** (quoting, dates, nulls, identifier-like numbers), **List rules** (block style, empty lists, uniqueness), **Canonical key order**, **Description field**, **Tags**, **Aliases**, **Links and related documents**, and **Extensions**.

## Scalar value rules

String values **MUST** be quoted. Single or double quotes are both acceptable; the validator enforces semantic validity, not source quote style.

Correct:

```yaml
title: 'Markdown Frontmatter Standard'
id: 'markdown-frontmatter-standard'
created: '2026-06-01'
```

Incorrect:

```yaml
title: Markdown Frontmatter Standard
id: markdown-frontmatter-standard
created: 2026-06-01
```

Date values **MUST** be strings in `YYYY-MM-DD` format and **MUST** be quoted.

Boolean values, if ever added to the schema, **MUST** be literal `true` or `false`, never `yes`, `no`, `on`, `off`, `y`, or `n`.

Identifier-like numbers **MUST** be strings:

```yaml
schema_version: '1.1'
project:
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

Array fields **MUST NOT** contain duplicate items; the validator rejects duplicates (`uniqueItems`).

## Canonical key order

Keys **MUST** appear in this order when present:

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
license
publish
project
x_project
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
description: 'Specification for writing, validating, and maintaining Markdown frontmatter in knowledge-base documents.'
```

Bad:

```yaml
description: 'This document was created because YAML has a long history and many tools use different parsers...'
```

These are authoring rules. The validator checks only that `description` is present and non-empty; the one-line and 280-character limits are conventions, not machine-enforced.

## Tags

`tags` are controlled vocabulary values for retrieval and classification.

Rules:

1. Do not include the leading `#`.
2. Use lowercase.
3. Use `kebab-case` for multiword tags.
4. Do not use spaces.
5. Where a project maintains a tag registry (for example `schemas/tag-registry.md`), every tag **MUST** appear in it before first use. Registry membership is a project-specific policy and is not enforced by the core validator.

Correct:

```yaml
tags:
  - 'yaml'
  - 'frontmatter'
  - 'agent-knowledge'
  - 'document-metadata'
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

All document links — in `related`, `supersedes`, `superseded_by`, `depends_on`, and in document bodies — **SHOULD** be written as a path relative to the repository root, including the file's extension (for example `schemas/markdown-frontmatter.schema.json`). This is the recommended link form. Bare filenames, bare IDs, and absolute paths are discouraged: they do not resolve deterministically and collide across folders (many folders contain an `index.md`).

`applies_to` is **not** a document link — it holds free-form scope identifiers (services, components, environments) — so it is exempt from this convention.

Use document-level links, not section-level (`#`) links, until a future schema revision permits them.

This is currently a **documented convention**: the validator does **not** check link form, in frontmatter or in document bodies. Schema-enforced path patterns are planned for a future major (`2.0.0`) release, at which point bare-ID and absolute-path links will fail validation. Authoring to the convention now keeps documents forward-compatible with that change.

Recommended:

```yaml
related:
  - 'src/project_standards/schemas/markdown-frontmatter.schema.json'
  - 'standards/adr/templates/adr.md'
```

Discouraged:

```yaml
related:
  - 'adr.md'
  - 'tag-registry'
  - '/schemas/tag-registry.md'
  - 'schemas/markdown-frontmatter.md#tags'
```

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

## Versioning and compatibility

Two version numbers are in play, and they are **not** the same:

- **`schema_version`** (this document) — the version of the **metadata schema**: the field set and controlled vocabularies. It changes only when those change, and carries no patch component. This release moves it from `1.0` to `1.1` by adding the optional `consumer` field. The machine schema's `schema_version` enum lists every value still accepted (`["1.0", "1.1"]`), so existing `1.0` documents stay valid.
- **The repository release tag** (`vMAJOR.MINOR.PATCH`) — versions all four shipped components together (the standard, the JSON schema, the validator CLI, and the reusable workflow).

How a schema change maps to a release level (additive → minor; a field or controlled value removed, or a pattern tightened → major), the previously-passing rule, tagging, and the consumption model all live in [`meta/versioning.md`](../../meta/versioning.md) and are not repeated here.

## Validation

Frontmatter is validated by [`src/project_standards/validate_frontmatter.py`](../../src/project_standards/validate_frontmatter.py) — installed as the `validate-frontmatter` command — against [`src/project_standards/schemas/markdown-frontmatter.schema.json`](../../src/project_standards/schemas/markdown-frontmatter.schema.json), in CI and locally.

- **Run locally:** `uv run validate-frontmatter --config .project-standards.yml`. Run `validate-frontmatter --help` for the full flag list.
- **Exit codes:** `0` — all matched files valid (or none matched); `1` — one or more documents failed validation (each error, then a summary count, prints to stderr); `2` — configuration or schema error: a missing or invalid config or schema, an unknown standard version label (`markdown.frontmatter.version`, `markdown.adr.version`, `python_tooling.version`, or `markdown_tooling.version`), or an incompatible configured `frontmatter`↔`adr` version pair.

Configuration (`.project-standards.yml`), the reusable CI workflow, and how consuming repositories pin a release tag are documented in [the adoption guide](adopt.md); they are not repeated here.

## Valid frontmatter template

This template lists every universal top-level field in canonical order. Required fields must stay; optional fields may be omitted when unused (they are shown here at their default/empty values). Extension namespaces (`publish`, `project`/`x_project`) are documented under [Extensions](#extensions) and are not repeated here.

```yaml
---
schema_version: '1.1'
id: 'replace-with-stable-id'
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
license: null
---
```
