# Adopt the ADR Standard

The current consumer package is [`adr@1.6`](versions/1.6/adopt.md). Use it for MADR decision records, a create-only ADR scaffold, optional required-section validation, explicit decision-boundary authoring guidance, and opt-in amendment-relationship validation. Markdown Frontmatter is a companion, not a dependency; enable it separately when ADR metadata also needs schema and ID validation.

## Configure and reconcile

```bash
project-standards standards enable adr --version 1.6
project-standards reconcile
project-standards reconcile --apply
```

Package options live under `[standards.adr.config]`: `contract_version = "1.0"` retains the fundamental MADR document/body contract, `require_sections` enables the three required MADR headings, and `validate_amendments` independently checks reciprocal `project.amends` / `project.amended_by` entries and rejects amendment of a superseded ADR. Both checks default to `false`; package 1.6 adds no required scope heading and does not infer semantic scope or relationships from prose.

Upgrading from 1.5 changes nothing a consumer must edit: `validate_amendments` defaults to `false`, both amendment fields remain optional, and the create-only scaffold is byte-identical. Audit the complete ADR corpus before enabling the new check. A repository that invented its own amendment banner before 1.5 converts each occurrence once — see the conversion procedure in the [version-specific guide](versions/1.6/adopt.md); an unconverted banner is documentation debt, not a finding.

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

The provider reports incompatible contracts, modified create-only scaffolds, invalid snapshots, missing MADR sections, one-way amendment relationships, and amendments targeting superseded ADRs without overwriting the repository. Authoring review must separately reject outcomes broader than the evaluated problem and any requirement that treats an out-of-scope case as an exception.
