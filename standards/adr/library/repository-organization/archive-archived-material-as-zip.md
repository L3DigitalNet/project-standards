---
schema_version: '1.1'
id: 'template-kco71x-archive-archived-material-as-zip'
title: 'Archive Archived Material as ZIP Files'
description: 'Draft ADR template for storing archival material in ZIP files under a default `.archived/` path instead of loose archive-directory contents.'
doc_type: 'template'
status: 'draft'
created: '2026-08-02'
updated: '2026-08-02'
reviewed: null
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'adr'
  - 'archive'
  - 'documentation'
  - 'repository'
aliases: []
related:
  - 'standards/adr/library/README.md'
  - 'standards/adr/versions/1.3/templates/adr.md'
source:
  - 'Owner requirement, 2026-08-02'
confidence: 'high'
visibility: 'internal'
license: null
---

# ADR Library: Archive Archived Material as ZIP Files

## Description

This reusable draft keeps historical material compact by storing each cohesive archived unit in a compressed `.zip` file instead of as loose files in an archive-like directory. It strongly recommends a repository-root `.archived/` directory as the default archival location.

Before adoption, either accept `.archived/` as the primary archival path or explicitly record the target repository's alternative, confirm the material is no longer active source, choose any required index or retention metadata, adapt repository-specific details, add the required ADR metadata, and obtain explicit acceptance.

```markdown
# Archive archived material as ZIP files

## Context and Problem Statement

This repository retains some material for historical reference after it is no longer active source, maintained documentation, or a supported runtime artifact. Leaving that material as loose files beneath directories such as `.archived/`, `archive/`, `archived/`, or `old/` increases file counts, clutters ordinary repository browsing, and leaves historical source visible to formatters, linters, and other source-oriented tooling.

The repository needs a durable archival convention that retains the historical bytes without treating them as part of the active working corpus. The default primary archival path is the repository-root `.archived/` directory. A repository may intentionally select another location when its structure calls for one; the default is a strong recommendation, not a mandatory layout. This decision governs archival storage only. It does not authorize deletion, archival of active material, or relaxation of checks for files that remain active outside an archive-like directory.

## Decision Drivers

- Keep historical material available without keeping it in the ordinary source tree.
- Reduce repository file counts and navigation clutter.
- Keep archived code and text out of ordinary formatter and linter discovery.
- Preserve each archived unit's internal paths and contents together.
- Make archive locations and their contents unambiguous during review.

## Considered Options

- Store archived material as compressed `.zip` files under the default `.archived/` path, with an explicit repository-specific override when needed.
- Retain archived material as loose files in archive-like directories.
- Delete material that is no longer active.

## Decision Outcome

Chosen option: **store archived material as compressed `.zip` files under the default `.archived/` path, with an explicit repository-specific override when needed**. When material moves into the default `.archived/` directory or another intentionally designated archival location, move the cohesive archival unit into a `.zip` file instead of retaining its individual files there.

The following invariants apply:

- The library's default primary archival path is the repository-root `.archived/` directory. Repositories should use it unless an explicitly recorded structure or ownership reason requires another path.
- A repository may choose a different primary archival location. That choice is local policy, does not require a migration to `.archived/`, and applies the same ZIP-payload rules.
- The selected archival location holds compressed `.zip` archival payloads, not loose archived source trees or collections of historical files.
- Each ZIP contains one cohesive archival unit. Related files keep their relative-path hierarchy inside the ZIP; do not create one ZIP per individual file merely to satisfy this policy.
- A directory is not archival merely because its name sounds old; active material must not be compressed under this decision.
- An archive index, manifest, or other active navigation aid may remain outside a ZIP when the repository needs it. It identifies the ZIP payload and is not itself archived material.
- References that formerly named an archived loose file are updated to identify the ZIP and, where useful, its internal path. A repository must not leave links that falsely claim a removed loose file still exists.
- ZIP storage is archival retention, not deletion. Preserve any required provenance, retention, licensing, or recovery information before moving the material.
- Ordinary source tooling does not need to traverse ZIP contents. A security, legal, provenance, or recovery process that requires archive inspection must name and inspect the ZIP explicitly.

### Consequences

- Good, because `.archived/` gives repositories a predictable, unobtrusive default that keeps archival material separate from active source.
- Good, because archive directories contain substantially fewer files and are easier to browse.
- Good, because historical code and text no longer enter ordinary source-based formatting and linting scope as loose files.
- Good, because related archived material and its internal layout travel together as one retained artifact.
- Bad, because readers must inspect or extract a ZIP before viewing or diffing its contents.
- Bad, because direct links to individual archived files are no longer ordinary repository paths and need deliberate replacement.
- Neutral, because repositories may select another archival path and this decision does not prescribe a repository-wide command, retention period, or archive naming scheme beyond the `.zip` format.

### Confirmation

Conformance is confirmed during archival review when `.archived/`, or the repository's explicitly declared alternative, contains the relevant archival unit as a compressed `.zip`, no loose archived payload remains there, the ZIP preserves the expected internal paths, and active references no longer point to removed loose files.

## Pros and Cons of the Options

### Compressed ZIP files under `.archived/` by default

- Good, because one archive represents a cohesive historical unit while reducing filesystem clutter.
- Good, because the default path establishes a recognizable archival home without preventing a repository-specific override.
- Good, because ordinary source tooling sees the ZIP as an artifact rather than as active source files.
- Bad, because content inspection requires an explicit extraction or archive-listing step.

### Loose files in archive-like directories

- Good, because individual archived files remain directly browseable and linkable.
- Bad, because file counts, source-tool discovery, and repository clutter remain high.

### Delete inactive material

- Good, because it removes the material and its maintenance burden completely.
- Bad, because it loses readily available historical evidence and may violate retention or recovery needs.

## More Information

Record whether the repository uses the default `.archived/` path or its explicitly chosen alternative, plus its ZIP naming convention, any index or manifest format, and any retention or inspection requirements. Revisit this decision if the repository needs active historical files to remain directly linkable or if its archive format, retention obligations, tooling boundaries, or selected archival path change.
```
