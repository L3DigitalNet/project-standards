---
schema_version: '1.1'
id: 'runbook-fp2fub-upgrading-from-v2-to-v3'
title: 'Upgrading from v2 to v3'
description: 'Step-by-step runbook for upgrading a consuming repository from project-standards v2 to v3.'
doc_type: 'runbook'
status: 'active'
created: '2026-06-09'
updated: '2026-06-09'
tags:
  - 'migration'
  - 'upgrade'
  - 'versioning'
aliases: []
related:
  - 'CHANGELOG.md'
  - 'standards/markdown-frontmatter/adopt.md'
---

# Upgrading from v2 to v3

`project-standards` `3.0.0` is a **major** release: re-pinning a repo from `@v2` to `@v3` can turn a previously-passing CI run red. This runbook is the step-by-step upgrade path. For the full list of changes see [`CHANGELOG.md`](CHANGELOG.md); for first-time adoption (not upgrade) see each standard's `adopt.md` (e.g. [`standards/markdown-frontmatter/adopt.md`](standards/markdown-frontmatter/adopt.md)).

## What breaks

Two changes can fail a repo that passed under `@v2`:

1. **`validate-id` now runs in CI.** The reusable workflow validates every managed document's `id`. Old-style kebab ids (e.g. `restart-netbox-after-config-change`) fail with `[id] prefix '…' is not a valid doc_type`.
2. **Duplicate top-level frontmatter keys are rejected.** The parser previously kept the last value silently; it now errors with `invalid YAML frontmatter: duplicate key '…'`.

`validate-references` is **opt-in** and stays off unless you enable it, so it cannot break an existing repo on upgrade.

## Before you start

- Python **3.14+** must be available — the validator requires it, and the pre-commit hooks pin `language_version: python3.14`.
- Upgrade on a branch and let CI run before merging.

## Steps

### 1. Re-pin both refs to `@v3`

In your caller workflow, bump the `uses:` pin **and** set `standards-ref` explicitly:

```yaml
jobs:
  validate:
    uses: L3DigitalNet/project-standards/.github/workflows/validate-markdown-frontmatter.yml@v3
    with:
      config-path: '.project-standards.yml'
      standards-ref: 'v3'
```

Set `standards-ref` to the same ref as your `uses:` pin so the workflow definition and the installed validator never drift.

### 2. Migrate `id` fields

Run the fixer from the new release against your repo:

```bash
uvx --from 'git+https://github.com/L3DigitalNet/project-standards@v3' \
  validate-id --fix --config .project-standards.yml
```

This regenerates non-ADR ids as `{doc_type}-{base36}-{slug}`. **ADR ids are not auto-fixed** — update them by hand to `adr-{NNNN}-{repo-name}-{short-title}`. If you use a custom `markdown.frontmatter.schema` path, id validation is skipped and this step is unnecessary.

### 3. Remove duplicate frontmatter keys

If validation reports `duplicate key '…'`, delete the duplicate top-level key from that document's frontmatter (the parser no longer silently keeps the last occurrence).

### 4. (Optional) Opt into cross-file checks

`validate-references` adds id-uniqueness, referential-integrity, supersede-reciprocity, date-ordering, and ADR-number checks. It is off by default; enable it only when ready:

```yaml
markdown:
  frontmatter:
    references:
      enabled: true
```

## Verify

```bash
uvx --from 'git+https://github.com/L3DigitalNet/project-standards@v3' \
  project-standards validate --config .project-standards.yml
```

Exit `0` means the schema, id, and (when enabled) reference checks all pass.

## Rollback

The upgrade is only pins plus id edits. To roll back, re-pin `@v3` → `@v2` and `standards-ref: "v2"`; regenerated ids remain valid under `@v2` (they satisfy the same format), so no content rollback is needed.
