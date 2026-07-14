# Markdown Frontmatter Structure Requirements

This page defines the hard structure of a managed Markdown frontmatter block: fields, ordering, scalar syntax, list syntax, ID shape, validation, and compatibility. Use [Field Values](field-values.md) for semantic guidance on choosing values.

## Profiles

### Minimal frontmatter

Every managed document supports this minimal form. These eleven fields are required.

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

### Standard frontmatter

Use this richer form for most project documentation.

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

Optional relationship fields are permitted when needed: `supersedes`, `superseded_by`, `depends_on`, and `applies_to`.

## Field Set

| Field            | Required | Type                |
| ---------------- | -------: | ------------------- |
| `schema_version` |      Yes | string enum         |
| `id`             |      Yes | string              |
| `title`          |      Yes | string              |
| `description`    |      Yes | string              |
| `doc_type`       |      Yes | string enum         |
| `status`         |      Yes | string enum         |
| `created`        |      Yes | date string         |
| `updated`        |      Yes | date string         |
| `reviewed`       |       No | date string or null |
| `owner`          |       No | string              |
| `consumer`       |       No | string enum         |
| `tags`           |      Yes | array of strings    |
| `aliases`        |      Yes | array of strings    |
| `related`        |      Yes | array of strings    |
| `supersedes`     |       No | array of strings    |
| `superseded_by`  |       No | string or null      |
| `depends_on`     |       No | array of strings    |
| `applies_to`     |       No | array of strings    |
| `source`         |       No | array of strings    |
| `confidence`     |       No | string enum         |
| `visibility`     |       No | string enum         |
| `license`        |       No | string or null      |
| `publish`        |       No | object              |
| `project`        |       No | object              |
| `x_project`      |       No | object              |

The schema rejects unknown top-level fields. Project-specific metadata belongs under `project` or `x_project`; publishing metadata belongs under `publish`.

## Controlled Structural Values

These enum values are accepted by the schema:

| Field | Allowed values |
| --- | --- |
| `doc_type` | `index`, `note`, `concept`, `reference`, `runbook`, `spec`, `plan`, `adr`, `decision`, `research`, `template`, `log`, `prompt`, `schema` |
| `status` | `draft`, `active`, `review`, `deprecated`, `archived`, `superseded`, `stub` |
| `confidence` | `high`, `medium`, `low`, `unknown` |
| `visibility` | `private`, `internal`, `public` |
| `consumer` | `user`, `agent`, `mix`, `unknown` |

Do not invent new top-level enum values in a consuming repo. If repo-local classification is needed, use `tags`, `project`, or body content.

## Canonical Key Order

Keys must appear in this order when present:

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

## Scalar Value Rules

Use YAML frontmatter delimited by `---` at the very top of the file.

String values must be quoted:

```yaml
title: 'Markdown Frontmatter Standard'
id: 'reference-ove1rr-markdown-frontmatter-standard'
created: '2026-06-02'
```

Dates must be quoted strings in `YYYY-MM-DD` format. The schema accepts date-shaped strings; `format-frontmatter --check` enforces quote style.

Identifier-like numbers must be strings:

```yaml
schema_version: '1.1'
project:
  zip_code: '01234'
```

Use `null` only where the schema allows it. Prefer omitting optional fields or using an empty list when no value exists.

## List Rules

Non-empty lists must use block style:

```yaml
tags:
  - 'yaml'
  - 'frontmatter'
  - 'standards'
```

Empty lists must use `[]`:

```yaml
aliases: []
related: []
```

List items that are strings must be quoted. Array fields must not contain duplicate items; the schema rejects duplicates.

## ID Format

Ordinary documents use this form:

```text
{doc_type}-{6-char-base36-token}-{readable-slug}
```

Example:

```yaml
id: 'runbook-0f943i-restart-netbox-after-config-change'
doc_type: 'runbook'
```

Rules:

- the first segment must match `doc_type`;
- the token is exactly six characters from `[0-9a-z]`;
- the readable slug is lowercase kebab-case;
- the slug is frozen at creation and does not change when the title changes.

ADRs use this form:

```text
adr-{NNNN}-{repo-name}-{short-title}
```

Example:

```yaml
id: 'adr-0001-homelab-use-postgresql-for-persistent-storage'
doc_type: 'adr'
```

Generate ordinary IDs with tooling, not by hand. The random token prevents collisions across large corpora. ADR IDs use sequence numbers plus repo names for cross-repo uniqueness.

## Description Field

`description` is a structural retrieval hint. It must be present and non-empty.

Authoring rules:

1. Keep it one line.
2. Keep it under 280 characters.
3. Do not use Markdown.
4. State what the document is for and when to use it.
5. Do not include history, citations, or background explanation.

Good:

```yaml
description: 'Procedure for validating Markdown frontmatter before merging documentation changes.'
```

Bad:

```yaml
description: 'This document was created because YAML has a long history and many tools use different parsers.'
```

## Link Form

Document relationship fields should use repo-root-relative paths with extensions when they point to files in the same repository:

```yaml
related:
  - 'standards/markdown-frontmatter/field-values.md'
  - 'src/project_standards/schemas/markdown-frontmatter.schema.json'
```

Avoid bare filenames, bare IDs, absolute paths, and section anchors in frontmatter relationship fields. Body links may use section anchors.

`applies_to` is not a document-link field. It may hold component names, service names, commands, or repo-relative path scopes.

## Extensions

The only sanctioned top-level extension objects are:

- `publish` for publishing/export metadata;
- `project` for project-specific metadata;
- `x_project` as an alternate project-specific namespace.

Example:

```yaml
project:
  service: 'netbox'
  environment: 'home-lab'
```

Universal fields stay at the top level. Repo-local fields do not.

## Validation

Run schema, ID, and reference validation:

```bash
uv run project-standards validate
```

This invokes:

- `validate-frontmatter` for schema validation;
- `validate-id` for ID grammar;
- `validate-references` for opt-in repo-wide reference checks.

Run the formatter check for source-style requirements, including quote style, key order, and list layout:

```bash
uv run format-frontmatter --check
```

Exit codes:

| Code | Meaning                                        |
| ---: | ---------------------------------------------- |
|  `0` | All matched files passed, or no files matched. |
|  `1` | One or more documents failed validation.       |
|  `2` | Configuration, schema, or invocation error.    |

`validate-references` checks ID uniqueness, referential integrity, supersede reciprocity, date ordering, and ADR sequence uniqueness only when enabled:

```toml
[standards.markdown-frontmatter.config.references]
enabled = true
```

## Compatibility

The `schema_version` field versions the metadata schema's field set and controlled vocabularies. Version `1.1` is the current version for new documents. Existing `1.0` documents remain accepted by the bundled schema.

Adding optional fields or enum values is a compatible schema change. Removing a field or enum value, making a field required, or tightening a pattern is a breaking schema change. Release classification follows the [Versioning Standard](https://github.com/L3DigitalNet/project-standards/blob/v5/meta/versioning.md).
