---
schema_version: '1.1'
id: runbook-5ax5n4-adopt-the-adr-standard
title: 'Adopt the ADR Standard'
description: 'How to adopt the ADR Standard in a consuming repository; it rides the frontmatter validator.'
doc_type: 'runbook'
status: 'active'
created: '2026-06-06'
updated: '2026-06-08'
reviewed: null
owner: ''
consumer: 'agent'
tags:
  - 'adoption'
  - 'adr'
  - 'runbook'
aliases: []
related:
  - 'standards/adr/README.md'
  - 'standards/adr/examples/adr.example.md'
  - 'standards/markdown-frontmatter/adopt.md'
source: []
confidence: 'high'
visibility: 'public'
license: null
---

# Adopt the ADR Standard

ADRs are **managed Markdown documents**: they carry full frontmatter and are validated by the same tooling as every other doc. There is **no separate ADR workflow**.

## Quick adoption (CLI)

As of `v2`, the packaged CLI drops the ADR template and reports the config knobs in one command:

```bash
uvx --from 'git+https://github.com/L3DigitalNet/project-standards@v2' \
  project-standards adopt adr
```

This writes the ADR template to `docs/decisions/adr.template.md` (a `*.template.md` path your validation excludes, so its placeholder frontmatter never fails) and **reports** the `.project-standards.yml` additions — the `markdown.adr` block (§3) and the required `**/*.template.md` exclusion — for you to merge by hand (the CLI never edits an existing config in place). Adopt the Frontmatter Standard first (§1); the manual steps below remain the reference.

## 1. Adopt the Frontmatter Standard first

Follow [`../markdown-frontmatter/adopt.md`](../markdown-frontmatter/adopt.md) to add `.project-standards.yml` and the reusable validator workflow. ADR enforcement rides on top of it.

## 2. Let ADRs validate

Do **not** exclude `docs/adr/**` or `docs/decisions/**` in `.project-standards.yml` — ADRs are managed docs. Each carries frontmatter with `doc_type: adr` and an id like `adr-NNNN-repo-name-short-title` (see [the standard](README.md)). Note the id and the filename diverge: the **`id`** embeds the `repo-name` segment for global uniqueness (`adr-NNNN-repo-name-short-title`), but the **filename** omits it (`adr-NNNN-short-title.md`) — see the standard's "Directory and index convention".

## 3. (Optional) enforce MADR body sections

To assert every `doc_type: adr` document has the three MADR-required `##` sections, opt in:

```yaml
markdown:
  adr:
    version: '1.0' # OPTIONAL — pin the ADR contract version; must be compatible with the Frontmatter version
    require_sections: true
```

This rides the same frontmatter workflow — no extra job. See [the standard](README.md) for the section list.

**ADR/Frontmatter compatibility.** Each ADR contract version supports specific Frontmatter versions (ADR `1.0` supports Frontmatter `1.1`). If you also pin `markdown.frontmatter.version`, the validator rejects an incompatible pair. Omit `markdown.adr.version` to use the frozen default.

## 4. Author from a template

Copy a scaffold from [`templates/`](templates/): `adr.md` (full), `adr-minimal.md`, `adr-bare.md`, `adr-bare-minimal.md`. A worked example is in [`examples/adr.example.md`](examples/adr.example.md).
