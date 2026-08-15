# Markdown Frontmatter Field Values

This page explains how to choose consistent frontmatter values. Use [Structure Requirements](structure.md) for the hard schema, formatting, and validation contract.

## Expected Standard Profile

Most managed documents should use the standard profile:

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

For ordinary documents, add relationship fields (`supersedes`, `superseded_by`, `depends_on`, `applies_to`) only when they carry real information. ADR profiles may keep `supersedes: []` and `superseded_by: null` as explicit lifecycle placeholders.

## Field Purposes

| Field | Use it for |
| --- | --- |
| `schema_version` | Schema contract used by this document. New documents use `'1.1'`. |
| `id` | Stable identifier independent of title and path. |
| `title` | Human-readable title shown in indexes and search results. |
| `description` | One-line retrieval hint explaining what the document is for. |
| `doc_type` | Broad document kind from the standard enum. |
| `status` | Lifecycle state and whether the document should be relied on now. |
| `created` | Date the document was first created. |
| `updated` | Date of the last meaningful content or lifecycle change. |
| `reviewed` | Date of the last correctness review, or `null` if no such review happened. |
| `owner` | Stable role, team, repo, or person responsible for correctness. |
| `consumer` | Intended reader: humans, agents, both, or unknown. |
| `tags` | Discovery labels and shared vocabulary. |
| `aliases` | Alternate names a reader might search for. |
| `related` | Nearby documents a reader would naturally consult. |
| `supersedes` | Older documents this document replaces. |
| `superseded_by` | Replacement document when this one is superseded. |
| `depends_on` | Documents or standards this document requires to remain valid. |
| `applies_to` | Component, command, service, environment, or path scope. |
| `source` | Evidence used to create or support the document. |
| `confidence` | Trust level for factual claims. |
| `visibility` | Exposure level. |
| `license` | Reuse/license terms when relevant. |
| `publish` | Publishing/export metadata. |
| `project` / `x_project` | Repo-local extensions. |

## Document Types

| Value       | Use when                                                        |
| ----------- | --------------------------------------------------------------- |
| `index`     | Navigation, README-like landing pages, and directory indexes.   |
| `note`      | General durable note that does not fit a narrower type.         |
| `concept`   | Explanation of an idea, model, pattern, or principle.           |
| `reference` | Stable factual reference material.                              |
| `runbook`   | Operational procedure or step-by-step task.                     |
| `spec`      | Implementer-ready build/change specification.                   |
| `plan`      | Proposed approach, not necessarily accepted.                    |
| `adr`       | Architecture Decision Record.                                   |
| `decision`  | Smaller decision note that does not require full ADR structure. |
| `research`  | Findings from investigation or comparison.                      |
| `template`  | Reusable document, prompt, or content template.                 |
| `log`       | Chronological record.                                           |
| `prompt`    | LLM prompt or instruction artifact.                             |
| `schema`    | Metadata, validation, or data-structure definition.             |

Prefer the narrowest accurate `doc_type`. Do not add repo-local document types to the enum; use `tags` or `project` fields for finer classification.

## Lifecycle Values

`status` describes whether the document should be relied on today.

| Status | Use when | State-change trigger |
| --- | --- | --- |
| `draft` | Content is still being formed. | New document, major rewrite, or unresolved design choice. |
| `review` | Complete enough to inspect but not yet reliable. | Stale facts suspected, automated migration performed, or human review requested. |
| `active` | Current and usable. | Maintainer approval, successful verification, or completed review. |
| `deprecated` | Present but should not guide new work. | Replacement direction chosen, old interface documented for transition. |
| `superseded` | Replaced by another document. | Replacement exists and `superseded_by` is set. |
| `archived` | Historical only. | Retained for history and removed from active maintenance. |
| `stub` | Intentional placeholder. | Navigation or future-content placeholder is created. |

Lifecycle changes must update related fields:

- Update `updated` for meaningful content or lifecycle changes.
- Set `reviewed` only after a correctness review.
- Set `superseded_by` when moving to `superseded`.
- Prefer deleting temporary plans, reviews, and scratchpads over cycling them through statuses.

## Ownership

`owner` identifies who keeps a document correct. It is not necessarily the author, last editor, or reviewer.

Use a stable role or team by default:

```yaml
owner: 'platform-team'
```

Use a person's name only when that person is intentionally the durable owner:

```yaml
owner: 'Chris Purcell / L3DigitalNet'
```

Every adopting repo should define its own owner vocabulary in a repository ADR. If more than one role could own a document, choose the role that would decide whether a content change is correct. Put collaborators in the body or a `project` extension instead of stuffing multiple roles into `owner`.

## Consumers

| Consumer  | Use when                                                      |
| --------- | ------------------------------------------------------------- |
| `user`    | Primarily for human users or contributors.                    |
| `agent`   | Primarily for LLM agents, automation, or generated workflows. |
| `mix`     | Both humans and agents should rely on it.                     |
| `unknown` | Only during migration or intentionally unclassified drafts.   |

Default to `mix` for durable repository documentation unless the document is clearly human-only or automation-only.

## Confidence

`confidence` describes factual reliability, not writing quality.

| Confidence | Use when | State-change trigger |
| --- | --- | --- |
| `unknown` | No confidence assessment exists. | New scaffold, mechanical migration, or imported content. |
| `low` | Plausible but weakly supported, stale, contradicted, or partial. | Missing source, failed validation, stale path, or contradiction. |
| `medium` | Based on inspection or known history but not freshly verified end to end. | Agent review, partial test evidence, or source docs that may drift. |
| `high` | Sourced, current, reviewed, and directly verified. | Human correctness review, passing validation, generated output, or source-of-truth confirmation. |

Upgrade confidence only when evidence improves. Downgrade it when implementation changes, links break, validation fails, or readers find contradictions.

## Visibility And License

| Visibility | Use when                                   |
| ---------- | ------------------------------------------ |
| `private`  | Personal, sensitive, or not safe to share. |
| `internal` | Internal project material.                 |
| `public`   | Safe for public release.                   |

Set `license` only when the document has reuse terms that matter independently of the repository license. Otherwise use `null` or omit it.

## Tags

Tags are retrieval labels. They are a shared vocabulary, not a full taxonomy.

Rules:

1. Use lowercase kebab-case.
2. Do not include a leading `#`.
3. Prefer existing tags over synonyms.
4. Use enough tags to make the document discoverable, but avoid filler.
5. Repo-specific tags are allowed when they are documented by the repo.

### Canonical Global Tags

The following tags are the baseline global vocabulary. They are not exhaustive; they define common meanings so tools and agents can search consistently across repos.

| Tag | Use when |
| --- | --- |
| `adr` | Architecture Decision Records and ADR indexes. |
| `adoption` | Standards adoption procedures and rollout guidance. |
| `agent` | Agent-facing behavior, prompts, workflows, or LLM context. |
| `architecture` | System design, boundaries, components, and architectural tradeoffs. |
| `automation` | Scripts, generated output, scheduled tasks, or automated workflows. |
| `changelog` | Changelogs and release-history logs. |
| `ci` | Continuous integration gates and workflow behavior. |
| `cli` | Command-line interface behavior or usage. |
| `compliance` | Compliance procedures, required checks, and conformance workflows. |
| `config` | Configuration files, settings, and config schema. |
| `decision` | Smaller decision notes or decision support material. |
| `deployment` | Deployments, release targets, runtime rollout, or environment placement. |
| `docs` | Documentation structure or documentation maintenance. |
| `documentation` | Documentation governance, style, metadata, or authoring policy. |
| `frontmatter` | Markdown frontmatter, YAML metadata, or metadata policy. |
| `index` | Navigation or landing pages. |
| `infrastructure` | Hosts, containers, networks, storage, cloud, homelab, or platform infrastructure. |
| `it` | Workstation, device, helpdesk, enterprise IT, or general technology administration. |
| `markdown` | Markdown syntax, Markdown files, or Markdown tooling. |
| `metadata` | Metadata fields, metadata schemas, or metadata policy. |
| `network` | Network topology, routing, DNS, VLANs, VPNs, firewalls, or connectivity. |
| `onboarding` | First-time setup, adoption, or contributor onboarding material. |
| `operations` | Operational procedures, runtime behavior, or service maintenance. |
| `policy` | Rules, governance, exceptions, or required practice. |
| `release` | Versioning, changelog, packaging, and release process. |
| `research` | Investigation summaries or evidence-gathering notes. |
| `runbook` | Operational procedures. |
| `schema` | Data schema, validation schema, or metadata schema. |
| `security` | Security, secrets, access, trust, or exposure concerns. |
| `spec` | Build/change specifications. |
| `standard` | Reusable standards or standards adoption. |
| `testing` | Tests, test fixtures, verification, or quality gates. |
| `tooling` | Developer tools, validators, formatters, linters, or package tooling. |
| `validation` | Validators, validation commands, or validation policy. |

### Repo-Local Tags

A repo may extend the global set with local tags for products, services, packages, teams, or domains. Define them in the repo's frontmatter ADR or a tag registry. Do not add synonym tags that differ only in wording.

Good local tags:

```yaml
tags:
  - 'frontmatter'
  - 'standard'
  - 'metadata'
```

Poor local tags:

```yaml
tags:
  - 'front-matter'
  - 'metadata-standardization-document'
  - 'general'
```

## Aliases

Aliases are search aids for names a reader is likely to type but that do not belong in the title.

Use aliases for:

- acronyms;
- command names;
- former titles;
- product names;
- numbered decisions;
- common abbreviations.

Do not repeat the title as an alias. Empty aliases are better than filler.

Example:

```yaml
aliases:
  - 'ADR 0014'
  - 'Frontmatter value policy'
  - 'Metadata ADR'
```

## Relationships And Sources

Use relationship fields sparingly and deliberately.

| Field | Add when | Preferred reference form |
| --- | --- | --- |
| `related` | A reader would naturally consult the other document. | Repo-root-relative path with extension. |
| `source` | The document depends on evidence, code, output, or external material. | Repo-root-relative path or stable external URL. |
| `supersedes` | This document replaces older documents. | Repo-root-relative path when the older document remains. |
| `superseded_by` | This document has been replaced. | Repo-root-relative path to the replacement when possible. |
| `depends_on` | This document is not usable unless another artifact remains valid. | Repo-root-relative path with extension. |
| `applies_to` | The document governs a component, command, service, or path. | Component names, command names, or repo-relative paths. |

Rules:

- Use `source` for evidence, not "see also" links.
- Do not duplicate a path in `related` if it is already expressed by `supersedes`, `superseded_by`, or `depends_on`.
- Use `related` for nearby context, not every parent index or sibling document.
- Put section-specific links in the body, not frontmatter relationship fields.

## Extensions

Use `project` or `x_project` for metadata that is meaningful only inside one repo.

Example:

```yaml
project:
  decision_makers:
    - 'chris'
  consulted: []
  informed: []
```

Use `publish` only for publishing/export metadata:

```yaml
publish:
  slug: 'frontmatter-field-values'
  draft: false
  weight: 20
```

Do not add project-specific top-level fields.

## Repository Frontmatter ADRs

Each consuming repo should record its frontmatter value policy as an ADR before or during adoption. Use [`templates/repository-frontmatter-adr.md`](templates/repository-frontmatter-adr.md).

That ADR should define:

- governed path globs and excluded path globs;
- default frontmatter profile;
- owner values and owner-selection rules;
- `doc_type` mapping by path and document class;
- `status`, `reviewed`, and `confidence` transition triggers;
- `consumer`, `visibility`, and `license` defaults;
- canonical repo tags and extension rules;
- alias rules;
- relationship and source conventions;
- migration order and validation commands.

The ADR is where a repo may expand the canonical global tag vocabulary. The schema remains portable; repo policy supplies the local values.

## Worked Examples

### ADR

```yaml
---
schema_version: '1.1'
id: 'adr-0014-project-standards-markdown-frontmatter-field-value-policy'
title: 'ADR 0014: Markdown Frontmatter Field Value Policy'
description: 'Decision record for how project-standards applies and demonstrates Markdown frontmatter field-value policy.'
doc_type: 'adr'
status: 'active'
created: '2026-07-09'
updated: '2026-07-09'
reviewed: '2026-07-09'
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
related:
  - 'standards/markdown-frontmatter/field-values.md'
source:
  - 'standards/markdown-frontmatter/templates/repository-frontmatter-adr.md'
confidence: 'high'
visibility: 'internal'
license: null
---
```

### Runbook

```yaml
---
schema_version: '1.1'
id: 'runbook-0f943i-validate-frontmatter-before-merge'
title: 'Validate frontmatter before merge'
description: 'Procedure for running the frontmatter validators before merging documentation changes.'
doc_type: 'runbook'
status: 'active'
created: '2026-07-09'
updated: '2026-07-09'
reviewed: null
owner: 'docs-maintainers'
consumer: 'user'
tags:
  - 'frontmatter'
  - 'validation'
  - 'runbook'
aliases:
  - 'Frontmatter validation'
related:
  - 'standards/markdown-frontmatter/structure.md'
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---
```
