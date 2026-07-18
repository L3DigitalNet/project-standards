---
schema_version: '1.1'
id: 'adr-0014-project-standards-markdown-frontmatter-field-value-policy'
title: 'ADR 0014: Markdown Frontmatter Field Value Policy'
description: 'Decision record for how project-standards applies and demonstrates Markdown frontmatter field-value policy.'
doc_type: 'adr'
status: 'active'
created: '2026-07-09'
updated: '2026-07-18'
reviewed: '2026-07-18'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'adr'
  - 'frontmatter'
  - 'metadata'
  - 'standard'
aliases:
  - 'ADR 0014'
  - 'Frontmatter value policy'
  - 'Metadata field values'
related:
  - 'standards/markdown-frontmatter/versions/1.2/README.md'
  - 'standards/markdown-frontmatter/versions/1.2/structure.md'
  - 'standards/markdown-frontmatter/versions/1.2/field-values.md'
  - 'standards/markdown-frontmatter/versions/1.2/templates/repository-frontmatter-adr.md'
  - '.standards/config.toml'
  - 'docs/adr/README.md'
  - 'docs/adr/adr-0015-exclude-standards-from-local-frontmatter-scope.md'
  - 'docs/adr/adr-0023-unified-consumer-standards-control-plane.md'
supersedes: []
superseded_by: null
source:
  - '.standards/config.toml'
  - 'standards/markdown-frontmatter/versions/1.2/templates/repository-frontmatter-adr.md'
  - 'standards/markdown-frontmatter/versions/1.2/field-values.md'
  - 'docs/adr/adr-0015-exclude-standards-from-local-frontmatter-scope.md'
confidence: 'high'
visibility: 'internal'
license: null
project:
  decision_makers:
    - 'chris'
  consulted: []
  informed: []
---

# ADR 0014: Markdown Frontmatter Field Value Policy

MADR status: **accepted**.

> **Amended by ADR 0023.** This repository-local field-value policy remains in force. `.standards/config.toml` is the current consumer configuration authority; `.project-standards.yml` is legacy migration input only. Managed project documentation includes `docs/workflows/**`.

## Context and Problem Statement

The Markdown Frontmatter Standard already defines the field set and schema rules, but consumers have been inconsistent about how to use the fields. Some documents omit optional fields that should carry ownership, evidence, or lifecycle meaning; other documents use tags, owners, confidence values, and relationship fields inconsistently between repositories.

The `project-standards` repository needs to demonstrate the expected repo-local policy layer: the schema stays global and portable, while each repo records the values and lifecycle triggers it uses locally. This repository also needs an exemplar ADR that consuming repositories can imitate when they adopt the new frontmatter ADR template.

## Decision Drivers

- Keep the Markdown Frontmatter schema portable and validator-neutral.
- Make field values consistent enough for humans, agents, and future tools to consume.
- Define a canonical global tag vocabulary while allowing documented repo-local tags.
- Avoid forcing a mass metadata migration into this standards-doc split.
- Dogfood the repository-frontmatter ADR template in the repository that publishes it.

## Considered Options

- **Keep the standard structural only** - leave field-value policy entirely to consuming repos.
- **Put all field-value rules into the single standard README** - keep one page as the entire standard.
- **Split structure and values, then dogfood a repo-local ADR** - keep hard schema rules separate from semantic field guidance, add a reusable ADR template, and record this repo's policy in an accepted ADR.

## Decision Outcome

Chosen option: **split structure and values, then dogfood a repo-local ADR**, because structural validation and semantic consistency are different concerns. The schema should continue to say which fields and enum values exist; the values guide and ADR template should explain how a repo chooses owners, lifecycle states, tags, relationships, and migration rules.

This decision does not change `schema_version`, the JSON schema, or validator behavior. New documents still use `schema_version: '1.1'`.

### Governed scope

The `standards.markdown-frontmatter.config` table in `.standards/config.toml` is the source of truth for this repository's managed Markdown scope. It includes the release and upgrade documents, usage and MCP-readiness documentation, workflow documentation, `meta/**/*.md`, and `docs/adr/**/*.md`.

ADR 0015 excludes `standards/**` from this repository's local frontmatter scope so standard-package content is not required to carry repo-local metadata. The current config also excludes templates, the root README, agent-instruction and agent-configuration files, and handoff documents. This ADR does not widen that scope.

### Frontmatter profile

New or materially edited managed documents should use the standard profile:

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
owner: 'Chris Purcell / L3DigitalNet'
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

Existing managed documents with `owner: ''` are not invalidated by this ADR; they are migration backlog to fix when the file is next materially edited.

### Owner values

Use these owner values unless a later ADR expands them:

| Owner | Use when |
| --- | --- |
| `Chris Purcell / L3DigitalNet` | Default owner for ADRs, meta docs, release docs, and repo-wide policy. |
| `project-standards maintainers` | Future group owner if maintenance broadens beyond the current single-owner form. |

If a file has a more specific maintainer in the future, record the long-lived role in `owner` and put collaborators in the body or `project` extension.

### Document type mapping

| Path or document class | `doc_type` |
| --- | --- |
| `meta/**/*.md`, stable factual docs | `reference` |
| `docs/usage.md`, operational procedures | `runbook` |
| `docs/adr/adr-*.md` | `adr` |
| `docs/adr/README.md` | `index` |
| `CHANGELOG.md` | `log` |
| Metadata/schema documents | `schema` when the document is primarily a schema reference; otherwise `reference` |

The root `README.md` and `standards/**` remain excluded by current policy.

### Lifecycle triggers

| Field | Trigger |
| --- | --- |
| `updated` | Meaningful content change, lifecycle change, or relationship change. |
| `reviewed` | Human correctness review or explicit owner approval. |
| `status: draft` | New or unsettled content. |
| `status: review` | Content is complete enough to inspect but not yet reliable. |
| `status: active` | Current standard, ADR, runbook, or reference material. |
| `status: deprecated` | Kept during transition but no longer recommended for new work. |
| `status: superseded` | Replacement exists and `superseded_by` is set. |
| `status: archived` | Historical only. |
| `status: stub` | Intentional placeholder. |

Do not use frontmatter statuses for temporary plans, reviews, or handoff state that are outside managed scope.

### Consumer, confidence, and visibility

Default values for new managed docs:

| Field | Default | Use a different value when |
| --- | --- | --- |
| `consumer` | `mix` | The document is clearly human-only (`user`) or automation/agent-only (`agent`). |
| `confidence` | `high` for accepted standards/ADRs after validation; `medium` for inspected but not fully reviewed docs; `unknown` for scaffolds. | Evidence improves or degrades. |
| `visibility` | `internal` | The document is safe to publish (`public`) or contains sensitive material (`private`). |
| `license` | `null` | Document-level reuse terms differ from the repository. |

`confidence: high` requires evidence: accepted decision, source-of-truth document, direct verification, or passing relevant validation.

### Canonical tags

This repository uses the global tags defined in the Markdown Frontmatter Standard and these repo-local tags:

| Tag | Use when |
| --- | --- |
| `standards-platform` | Meta-repository, standard graph, bundle, or MCP-readiness work. |
| `meta-repo` | Decisions and specs about this repository as a standards platform. |
| `versioning` | Release, contract-version, or compatibility policy. |
| `markdown-tooling` | Markdown Tooling Standard material. |
| `python-tooling` | Python Tooling Standard material. |
| `project-spec` | Project Specification Standard material. |
| `cli-documentation` | CLI Documentation Standard material. |
| `mcp` | MCP-readiness or future MCP server material. |

Repo-local tags must remain lowercase kebab-case. Do not add synonyms that only rename an existing tag.

### Aliases

Use aliases only for search terms a reader is likely to type:

- ADRs include `ADR NNNN`.
- Renamed documents keep former titles as aliases when useful.
- CLI/runbook docs may include command names.
- Do not repeat the title as an alias.

### Relationships and sources

Use repo-root-relative paths with extensions in relationship fields whenever possible.

| Field | Use in this repo |
| --- | --- |
| `related` | Nearby standard, ADR, spec, or meta doc a reader would naturally consult. |
| `source` | Evidence backing claims, including standards pages, templates, specs, generated outputs, or external authoritative references. |
| `supersedes` / `superseded_by` | Replacement trail for standards, ADRs, and durable references. |
| `depends_on` | Only when the document cannot be used without another artifact. |
| `applies_to` | Commands, standards, workflows, paths, or components governed by the document. |

Do not list every parent index or sibling document.

### Migration posture

This ADR improves future consistency but does not require a mass rewrite of existing frontmatter. When touching a managed document for meaningful content changes, bring its metadata closer to this policy in the same patch when that is safe and scoped.

### Confirmation

This decision is confirmed when:

- the Markdown Frontmatter Standard has separate structure and field-value pages;
- the bundle includes a repository-frontmatter ADR template;
- this ADR validates as an active example;
- the ADR index includes ADR 0014;
- validation through the selected Catalog 5 Markdown Frontmatter package exits `0` against `.standards/config.toml`.

## Pros and Cons of the Options

### Keep the standard structural only

- Good, because it avoids new prose and adoption work.
- Bad, because inconsistent `owner`, `tags`, `confidence`, and relationship use remains unsolved.
- Bad, because tools cannot assume shared meanings across repos.

### Put all field-value rules into the single standard README

- Good, because there is only one page to open.
- Bad, because structural rules and semantic guidance have different audiences and change rates.
- Bad, because the existing README was already doing too much.

### Split structure and values, then dogfood a repo-local ADR

- Good, because hard validation rules are easy to find.
- Good, because semantic guidance can grow without obscuring the schema contract.
- Good, because consuming repos get a concrete ADR template plus a real example.
- Neutral, because readers now follow one extra link.

## More Information

The reusable template lives at [`standards/markdown-frontmatter/versions/1.2/templates/repository-frontmatter-adr.md`](../../standards/markdown-frontmatter/versions/1.2/templates/repository-frontmatter-adr.md). The global value guidance lives at [`standards/markdown-frontmatter/versions/1.2/field-values.md`](../../standards/markdown-frontmatter/versions/1.2/field-values.md).
