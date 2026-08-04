# Adopt the ADR Standard

The current consumer package is [`adr@1.4`](versions/1.4/adopt.md). Use it for MADR decision records, a create-only ADR scaffold, optional required-section validation, and explicit decision-boundary authoring guidance. Markdown Frontmatter is a companion, not a dependency; enable it separately when ADR metadata also needs schema and ID validation.

## Configure and reconcile

```bash
project-standards standards enable adr --version 1.4
project-standards reconcile
project-standards reconcile --apply
```

Package options live under `[standards.adr.config]`: `contract_version = "1.0"` retains the fundamental MADR document/body contract, and `require_sections` enables the three required MADR headings. Package 1.4 adds no required scope heading and does not infer semantic scope from prose.

Reconciliation creates `docs/adr/adr.template.md` only when absent and never replaces consumer ADRs or an existing create-only scaffold. An existing scaffold receives the revised prompts only through a separate reviewed refresh.

## Migrate a V4 repository

```bash
project-standards init --catalog 5 --migrate
project-standards init --catalog 5 --migrate --apply
```

Apply only after the preview has no ambiguity or conflict. Migration claims only exact released scaffold bytes; modified or unknown content remains untouched and blocks the atomic migration.

## Verify and troubleshoot

```bash
project-standards reconcile --check
project-standards validate
```

The provider reports incompatible contracts, modified create-only scaffolds, invalid snapshots, and missing MADR sections without overwriting the repository. Authoring review must separately reject outcomes broader than the evaluated problem and any requirement that treats an out-of-scope case as an exception.
