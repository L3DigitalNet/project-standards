---
schema_version: '1.1'
id: 'adr-0015-project-standards-exclude-standards-from-local-frontmatter-scope'
title: 'ADR 0015: Exclude Standards from Local Frontmatter Scope'
description: 'Records the decision to exclude standards/** from project-standards local Markdown frontmatter validation and strip repo-local metadata from standard docs.'
doc_type: 'adr'
status: 'active'
created: '2026-07-09'
updated: '2026-07-10'
reviewed: '2026-07-10'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'adr'
  - 'frontmatter'
  - 'metadata'
  - 'standard'
aliases:
  - 'ADR 0015'
  - 'Standards frontmatter exclusion'
related:
  - '.project-standards.yml'
  - 'docs/adr/adr-0014-markdown-frontmatter-field-value-policy.md'
  - 'docs/adr/adr-0016-package-markdown-frontmatter-skill-with-standard.md'
  - 'docs/adr/adr-0021-standard-packaged-skill-installation-methodology.md'
  - 'docs/adr/README.md'
  - 'docs/adr/adr-0023-unified-consumer-standards-control-plane.md'
supersedes: []
superseded_by: null
source:
  - '.project-standards.yml'
  - 'docs/adr/adr-0014-markdown-frontmatter-field-value-policy.md'
confidence: 'high'
visibility: 'internal'
license: null
project:
  decision_makers:
    - 'chris'
  consulted: []
  informed: []
---

# ADR 0015: Exclude Standards from Local Frontmatter Scope

MADR status: **accepted**.

> **Amended by ADR 0023.** The published `standards/**` exclusion remains in force. After control-plane migration, package-managed resources under `.standards/packages/**` are also outside ordinary consumer-managed Markdown policy unless a package explicitly declares a document as consumer-owned input. The current `.project-standards.yml` scope remains transitional repository state.

## Context and Problem Statement

This repository publishes standards under `standards/**`. Those files are product content for consumers of the standards, not ordinary local project documentation. Applying this repository's local Markdown frontmatter policy to the standards tree risks making repo-specific metadata look like part of the content that should be copied, generated, or shipped to other repositories.

ADR 0014 records this repository's local frontmatter field-value policy. That policy should govern durable local docs such as release notes, meta docs, usage docs, and ADRs. It should not require standard-bundle docs to carry this repo's owner, lifecycle, relationship, or tag metadata, and standard documentation pages should not physically ship that repo-local metadata.

## Considered Options

- Keep validating `standards/**/*.md` as local managed documents - continue treating standard-bundle docs as part of this repo's frontmatter corpus.
- Exclude only templates and generated examples - leave standard READMEs and adoption docs governed, but keep obvious placeholders out of scope.
- Exclude `standards/**` from local frontmatter validation and strip repo-local metadata from standard docs - treat the standards tree as published standard content, not as this repo's local managed-document corpus.

## Decision Outcome

Chosen option: exclude `standards/**` from local frontmatter validation and strip repo-local metadata from standard docs, because the standards tree is the content this repository ships to consumers. The local frontmatter validator should not require that shipped content to carry this repository's own maintenance metadata, and standard documentation pages should not begin with this repo's local metadata block.

`.project-standards.yml` keeps `CHANGELOG.md`, `UPGRADING.md`, `docs/usage.md`, `meta/**/*.md`, and `docs/adr/**/*.md` in the local frontmatter corpus, but excludes `standards/**`.

Intentional standard artifacts under `standards/**` may still contain frontmatter when frontmatter is the artifact itself: examples, templates, and agent skill metadata. Those blocks are not this repository's local managed-document metadata.

This decision does not change the Markdown Frontmatter Standard, the schema, or consumer adoption guidance. A consuming repository may still decide to govern its own standards-like docs if those docs are local project documentation.

### Consequences

- Good, because standard-bundle docs are not accidentally coupled to this repository's local metadata policy.
- Good, because copied or generated standards content is less likely to carry `project-standards`-specific owner, lifecycle, and relationship metadata.
- Good, because the local frontmatter scope now matches the distinction between repo-local docs and published standard content.
- Bad, because frontmatter drift in intentional examples/templates inside `standards/**` is no longer caught by this repo's local frontmatter validator.
- Neutral, because `standards/**` remains covered by other gates where applicable, including Prettier, markdownlint, standards graph validation, and standard-specific tests.

## More Information

- Local scope config: [`.project-standards.yml`](../../.project-standards.yml)
- Field-value policy: [ADR 0014](adr-0014-markdown-frontmatter-field-value-policy.md)
