---
schema_version: '1.1'
id: 'runbook-p5m7nf-upgrading-from-v3-to-v4'
title: 'Upgrading from v3 to v4'
description: 'Step-by-step runbook for upgrading a consuming repository from project-standards v3 to v4.'
doc_type: 'runbook'
status: 'active'
created: '2026-07-05'
updated: '2026-07-07'
tags:
  - 'migration'
  - 'upgrade'
  - 'versioning'
aliases: []
related:
  - 'CHANGELOG.md'
  - 'standards/markdown-frontmatter/adopt.md'
  - 'standards/project-spec/adopt.md'
---

# Upgrading from v3 to v4

`project-standards` `4.0.0` is a **major** release: re-pinning a repo from `@v3` to `@v4` can turn a previously-passing CI run red. This runbook is the step-by-step upgrade path. For the full list of changes see [`CHANGELOG.md`](CHANGELOG.md); for first-time adoption (not upgrade) see each standard's `adopt.md` (e.g. [`standards/markdown-frontmatter/adopt.md`](standards/markdown-frontmatter/adopt.md)).

## What breaks

The v4 validator rejects several inputs that v3 silently accepted or truncated. On re-pin, a repo that passed under `@v3` can newly fail on any of:

1. **`date` fields no longer accept datetime values.** A `created`/`updated`/`reviewed` value whose YAML parses as a full timestamp (e.g. an unquoted `2026-06-03T00:00:00`) previously had its time part silently dropped; it now fails. Fix: quote the value as a plain `'YYYY-MM-DD'` date.
2. **The `tags` pattern is tighter** — `^[a-z0-9]+(-[a-z0-9]+)*$`. A tag with a leading/trailing hyphen or consecutive hyphens now fails.
3. **Non-string frontmatter keys are rejected.** A bare YAML key that parses as a number or boolean now errors with a clear message.
4. **Config errors now exit 2 instead of passing silently:**
   - a duplicate top-level key in `.project-standards.yml` (previously the last occurrence silently won);
   - an unquoted numeric `version` value (e.g. `version: 1.10`, which parsed as the float `1.1`) — quote it: `version: '1.10'`;
   - an explicitly-named file argument that does not exist, or a typo'd `--config` path (previously a vacuous green run). This also applies to `format-frontmatter --config`.
5. **`validate-references` semantic corrections — only if you set `references.enabled: true`.** Supersede sets are merged per-id (not last-wins), ADR numbers sort numerically (`adr-0010` after `adr-0009`), and dates are compared as dates — violations these bugs masked are newly caught. An empty index no longer exits vacuously green, and skipped files surface as warnings. Repos without the opt-in are unaffected.

**Copy-adopters (Python Tooling SSOT), on re-sync only:** the ruff dev-group floor is now `>=0.14` (earlier versions reject the standard's `target-version = "py314"`), and `pytest-cov` is dropped from the scaffolds (the documented gate never used it). Nothing changes until you deliberately re-sync the scaffolds.

## What's new (opt-in)

The **Project Specification Standard** — tiered spec templates, stable IDs, and the `project-standards spec` CLI (`validate`/`lint`/`extract`/`next`/`new`/`upgrade`) with its own reusable `validate-specs.yml` workflow — first ships at `v4.0.0`. It is fully opt-in (a `spec:` config block; nothing is inherited automatically). To adopt it, follow [`standards/project-spec/adopt.md`](standards/project-spec/adopt.md).

## Markdown Tooling — optional: enforce Prettier (contract 1.1)

Prettier is now a shipped, opt-in gate (contract `markdown_tooling 1.1`, from `v4.2.0`). To enforce it in your repo:

1. Adopt the workflow: re-run `project-standards adopt markdown-tooling` (writes `.github/workflows/format.yml`) or add `uses: …/format.yml@v4`.
2. Format once: `npx prettier@3.8.3 --write .`, commit the result.
3. File-set parity: if you exclude generated Markdown from markdownlint via `.markdownlint-cli2.jsonc`, mirror those globs into `.prettierignore` so Prettier does not gate files markdownlint skips.
4. Not ready yet? Set `prettier: false` in the caller to defer (the whole job skips — a clean pass).

Nothing is required: unchanged consumers keep passing.

## v4.3.0 — CLI Documentation Standard (no action required)

v4.3.0: no action required. Caveat: the validator now recognizes `cli_documentation.version`; a config that already carried that key with an unrecognized value (previously ignored) now exits 2. No known such configs.

## Before you start

- Python **3.14+** must be available — the validator requires it.
- Upgrade on a branch and let CI run before merging.

## Steps

### 1. Re-pin both refs to `@v4`

In your caller workflow, bump the `uses:` pin **and** set `standards-ref` explicitly:

```yaml
jobs:
  validate:
    uses: L3DigitalNet/project-standards/.github/workflows/validate-markdown-frontmatter.yml@v4
    with:
      config-path: '.project-standards.yml'
      standards-ref: 'v4'
```

Set `standards-ref` to the same ref as your `uses:` pin so the workflow definition and the installed validator never drift. If you also call `lint-markdown.yml`, bump its `uses:` pin to `@v4` the same way.

### 2. Audit the config

Check `.project-standards.yml` for the newly-fatal config shapes: duplicate top-level keys, and unquoted numeric `version` values (`version: 1.1` → `version: '1.1'`). A bad config now exits 2 instead of validating under defaults.

### 3. Audit managed documents

Run the new validator against your repo before merging the pin bump:

```bash
uvx --from 'git+https://github.com/L3DigitalNet/project-standards@v4' \
  project-standards validate --config .project-standards.yml
```

Fix what it reports — typically datetime-shaped `created`/`updated`/`reviewed` values (quote them as `'YYYY-MM-DD'`), malformed tags, and non-string keys. `project-standards fix` (same flags) auto-formats frontmatter where it can.

### 4. (Opted-in repos) review `validate-references` results

If `references.enabled: true`, the corrected semantics may newly flag real supersede/ordering violations that v3's bugs masked. Each finding reflects a genuine inconsistency — fix the documents, not the config.

### 5. (Optional) adopt the Project Specification Standard

Add a `spec:` block and the `validate-specs.yml@v4` workflow per [`standards/project-spec/adopt.md`](standards/project-spec/adopt.md). Skipping this step changes nothing.

## Verify

```bash
uvx --from 'git+https://github.com/L3DigitalNet/project-standards@v4' \
  project-standards validate --config .project-standards.yml
```

Exit `0` means the schema, id, and (when enabled) reference checks all pass.

## Rollback

The upgrade is pins plus document/config fixes. To roll back, re-pin `@v4` → `@v3` and `standards-ref: "v3"`. Content fixed for v4 stays valid under v3 — v4 is strictly stricter on the enforced surface — so no content rollback is needed. A repo that adopted the Project Specification Standard must also remove (or stop calling) `validate-specs.yml`, which does not exist at the `v3` tag.
