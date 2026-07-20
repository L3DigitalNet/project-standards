# Adopt the ADR Standard

The current consumer package is [`adr@1.2`](versions/1.2/adopt.md). Use it for MADR decision records, a create-only ADR scaffold, and optional required-section validation. Markdown Frontmatter is a companion, not a dependency; enable it separately when ADR metadata also needs schema and ID validation.

## Configure and reconcile

```bash
project-standards standards enable adr --version 1.2
project-standards reconcile
project-standards reconcile --apply
```

Package options live under `[standards.adr.config]`: `contract_version` selects the document/body contract independently of package `1.2`, and `require_sections` enables the three required MADR headings. Reconciliation creates `docs/adr/adr.template.md` only when absent and never replaces consumer ADRs.

## Migrate a V4 repository

```bash
project-standards init --catalog 5 --migrate
project-standards init --catalog 5 --migrate --apply
```

Apply only after the preview has no ambiguity or conflict. Migration maps `markdown.adr` settings and claims only exact released scaffold bytes. Modified or unknown content remains untouched and blocks the atomic migration.

## Verify and troubleshoot

```bash
project-standards reconcile --check
project-standards validate
```

An incompatible Frontmatter contract, modified create-only scaffold, or missing MADR section is reported without overwriting the repository. Resolve the declared contract/options or preserve the consumer file and retry. See the [version-specific guide](versions/1.2/adopt.md) for the exact option schema, output policy, authoring workflow, and failure handling.
