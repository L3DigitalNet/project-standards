---
schema_version: '1.1'
id: 'adr-0000-repo-name-markdown-frontmatter-field-value-policy'
title: 'ADR 0000: Markdown Frontmatter Field Value Policy'
description: 'Decision record for this repository metadata frontmatter scope, field-value conventions, lifecycle triggers, ownership, tags, and migration procedure.'
doc_type: 'adr'
status: 'draft'
created: 'YYYY-MM-DD'
updated: 'YYYY-MM-DD'
reviewed: null
owner: 'repo-maintainers'
consumer: 'mix'
tags:
  - 'adr'
  - 'frontmatter'
  - 'metadata'
  - 'documentation'
aliases:
  - 'ADR 0000'
  - 'Frontmatter value policy'
related:
  - '.standards/config.toml'
supersedes: []
superseded_by: null
source:
  - 'https://github.com/L3DigitalNet/project-standards/blob/<standards-ref>/standards/markdown-frontmatter/README.md'
  - 'https://github.com/L3DigitalNet/project-standards/blob/<standards-ref>/standards/markdown-frontmatter/structure.md'
  - 'https://github.com/L3DigitalNet/project-standards/blob/<standards-ref>/standards/markdown-frontmatter/field-values.md'
confidence: 'medium'
visibility: 'internal'
license: null
project:
  decision_makers: []
  consulted: []
  informed: []
---

# Markdown Frontmatter Field Value Policy

MADR status: **proposed**.

## Context and Problem Statement

This repository is adopting or refining the Markdown Frontmatter Standard. Structural validation alone proves that fields exist and match the schema, but it does not tell contributors which paths are governed, which owner values are valid, when lifecycle fields change, or which tags should be used consistently.

The repository needs a local policy that keeps metadata predictable while still allowing repo-specific tags and extension fields.

## Decision Drivers

- Make managed Markdown searchable and consistent for humans, agents, and tooling.
- Keep harness-owned, generated, temporary, fixture, and vendored files outside the governed corpus.
- Define field-value lifecycle triggers before widening validation scope.
- Establish a canonical tag vocabulary while permitting documented repo-local extensions.
- Keep project-specific metadata under `project` or `x_project`, not unknown top-level fields.

## Considered Options

- **Keep only structural validation** - rely on the schema and avoid repo-local value policy.
- **Govern every tracked Markdown file** - apply the same metadata expectations to all Markdown.
- **Govern the durable documentation corpus with explicit value policy** - define managed paths, exclusions, field-value rules, tags, and migration procedure.

## Decision Outcome

Chosen option: **govern the durable documentation corpus with explicit value policy**, because this gives the repository useful metadata without forcing frontmatter onto operational files, temporary work products, fixtures, generated output, or harness configuration.

This ADR establishes the repo-local conventions for frontmatter values. It does not need to change the upstream schema.

### Governed Scope

When this ADR is accepted and reconciliation is applied, the `markdown-frontmatter` options in `.standards/config.toml` should govern these Markdown paths:

```yaml
include:
  - 'README.md'
  - 'docs/**/*.md'
```

### Excluded Scope

The governed scope must exclude files that should not carry project-standard frontmatter:

```yaml
exclude:
  - '**/*.template.md'
  - 'CHANGELOG.md'
  - 'LICENSE.md'
  - 'CLAUDE.md'
  - 'AGENTS.md'
  - '.claude/**'
  - '.agents/**'
  - '.codex/**'
  - '.github/**'
  - 'docs/handoff/**'
  - 'docs/reviews/**'
  - 'docs/superpowers/plans/**'
  - 'tests/fixtures/**'
  - 'node_modules/**'
```

Adjust the lists to match the repository. Each exclusion should have a semantic reason.

### Frontmatter Profile

Governed files should use the standard profile:

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

Keep `supersedes: []` and `superseded_by: null` in ADR frontmatter so future replacements have an obvious lifecycle slot. Add `depends_on` and `applies_to` only when they carry real information.

### Field Value Policy

| Field | Repository convention |
| --- | --- |
| `schema_version` | Use `'1.1'` for new documents. |
| `id` | Use `{doc_type}-{base36-6}-{slug}` except ADRs, which use `adr-{NNNN}-{repo-name}-{short-title}`. |
| `title` | Use the human title; ADR titles begin `ADR NNNN:`. |
| `description` | One-line retrieval hint explaining what the document is for. |
| `doc_type` | Use the mapping below. |
| `status` | Use the lifecycle table below. |
| `created` | Creation date; do not change during edits. |
| `updated` | Bump on meaningful content or lifecycle changes. |
| `reviewed` | Set only after correctness review. |
| `owner` | Use one of the owner roles below. |
| `consumer` | Default to `mix` for durable docs. |
| `tags` | Use global tags plus documented repo-local tags. |
| `aliases` | Search aids only; do not repeat the title. |
| `related` | Nearby context a reader would naturally consult. |
| `source` | Evidence, code, generated output, or standards that support the document. |
| `confidence` | Use the confidence table below. |
| `visibility` | Default to `internal` unless the document is safe for public release or must remain private. |
| `license` | Use `null` unless document-level reuse terms differ from the repo. |
| `project` | Repo-specific metadata, such as decision roles. |

### Owner Values

| Owner                  | Use when                                                |
| ---------------------- | ------------------------------------------------------- |
| `repo-maintainers`     | Default owner for cross-cutting repository docs.        |
| `docs-maintainers`     | Documentation structure, indexes, and metadata policy.  |
| `platform-maintainers` | Infrastructure, deployment, CI, and runtime operations. |
| `product-maintainers`  | Product- or package-specific documentation.             |

Replace or extend these values with roles that match the repository.

### Document Type Mapping

| Path or document class                                    | `doc_type`  |
| --------------------------------------------------------- | ----------- |
| `README.md`, `index.md`, directory landing pages          | `index`     |
| `docs/adr/adr-*.md`                                       | `adr`       |
| `docs/specs/**/*.md`                                      | `spec`      |
| `docs/reference/**/*.md` and stable catalogs              | `reference` |
| `docs/research/**/*.md`                                   | `research`  |
| setup, usage, troubleshooting, and operational procedures | `runbook`   |
| conceptual explanations and mental models                 | `concept`   |
| reusable prompts                                          | `prompt`    |
| reusable document templates                               | `template`  |
| durable notes without a narrower type                     | `note`      |

### Status Lifecycle

| Status | Use when | State-change trigger |
| --- | --- | --- |
| `draft` | Content is still being formed. | New document, major rewrite, or unresolved design choice. |
| `review` | Complete enough to inspect but not yet reliable. | Stale facts suspected, automated migration, or review requested. |
| `active` | Current and usable. | Maintainer approval or successful verification. |
| `deprecated` | Present but should not guide new work. | Replacement direction chosen or old interface retained for transition. |
| `superseded` | Replaced by another document. | Replacement exists and `superseded_by` is set. |
| `archived` | Historical only. | Retained for history and removed from active maintenance. |
| `stub` | Intentional placeholder. | Navigation or future-content placeholder created. |

### Confidence Lifecycle

| Confidence | Use when | State-change trigger |
| --- | --- | --- |
| `unknown` | No confidence assessment exists. | New scaffold or mechanical migration. |
| `low` | Plausible but weakly supported, stale, or contradicted. | Missing source, failed validation, or known uncertainty. |
| `medium` | Based on inspection or history, but not freshly verified end to end. | Agent review or partial evidence. |
| `high` | Sourced, current, reviewed, and directly verified. | Human correctness review, passing validation, or source-of-truth confirmation. |

### Canonical Tags

Use the upstream global tags where they fit:

```yaml
tags:
  - 'adr'
  - 'frontmatter'
  - 'documentation'
  - 'standard'
```

Repo-local tags are allowed when they are documented here or in a tag registry. They must be lowercase kebab-case and should not duplicate existing global tags by synonym.

### Relationship Rules

- Use `related` for nearby context, not every parent or sibling.
- Use `source` for evidence, not "see also" links.
- Use `supersedes` and `superseded_by` for replacement relationships.
- Use `depends_on` only when another document must remain valid.
- Use `applies_to` for components, commands, services, environments, or paths.
- Prefer repo-root-relative paths with file extensions.

### Migration Procedure

1. Confirm the current managed scope validates.
2. Inventory target Markdown files.
3. Exclude operational, temporary, harness-owned, generated, vendored, and fixture files.
4. Add or repair frontmatter while validation scope is still narrow.
5. Review semantic fields: `owner`, `consumer`, `doc_type`, `status`, `tags`, `aliases`, `related`, `source`, `confidence`, and `visibility`.
6. Widen the package `include` option only after target files are ready.
7. Run formatting and validation.

### Confirmation

This decision is confirmed when:

- this ADR is accepted;
- `.standards/config.toml` expresses the approved package scope;
- governed files carry conformant frontmatter;
- excluded files carry no project-standard frontmatter unless they intentionally use another metadata contract;
- validation exits `0`.

## Pros and Cons of the Options

### Keep only structural validation

- Good, because it keeps adoption lightweight.
- Bad, because values still drift between documents and repositories.
- Bad, because tools cannot rely on owners, lifecycle states, tags, or confidence values consistently.

### Govern every tracked Markdown file

- Good, because the rule is simple to state.
- Bad, because operational files, fixtures, generated output, and harness config have different metadata contracts.
- Bad, because it creates busywork and can damage files whose value depends on preserving unusual Markdown.

### Govern the durable documentation corpus with explicit value policy

- Good, because metadata applies where it improves discovery and maintenance.
- Good, because temporary and tool-owned files stay out of scope.
- Good, because repo-local values can expand the global vocabulary without weakening the shared schema.
- Neutral, because the include and exclude lists require maintenance.

## More Information

- Markdown Frontmatter Standard: upstream `standards/markdown-frontmatter/README.md` at the release tag this repo pins.
- Structure Requirements: upstream `standards/markdown-frontmatter/structure.md` at the release tag this repo pins.
- Field Values: upstream `standards/markdown-frontmatter/field-values.md` at the release tag this repo pins.
