# Adopt ADR 1.4

Use this package when a repository needs MADR-based decision records, a standard scaffold, optional enforcement of MADR's three required sections, and explicit guidance for bounding the authority of each decision.

The common Catalog 5 control-plane lifecycle is documented by `project-standards`. This guide covers ADR-specific choices only.

## Enable and configure

```bash
project-standards standards enable adr --version 1.4
project-standards reconcile --apply
```

The package retains the two closed options:

```toml
[standards.adr]
enabled = true
version = "1.4"

[standards.adr.config]
contract_version = "1.0"
require_sections = false
```

`contract_version` remains `1.0`: package 1.4 does not add a required heading, frontmatter field, or semantic prose validator. Set `require_sections = true` only to require `## Context and Problem Statement`, `## Considered Options`, and `## Decision Outcome` on `doc_type: adr` snapshots.

## Frontmatter companion

Markdown Frontmatter is a companion, not a dependency. Enable it separately when the repository also wants schema, ID, date, and cross-document reference validation.

## Author and verify

Reconciliation creates `docs/adr/adr.template.md` only when that consumer-owned scaffold is absent. Copy it to `docs/adr/adr-NNNN-short-title.md`, replace every placeholder, and update the ADR index.

Before accepting the ADR, verify that it names the governed concern, governed population, applicability condition, exclusions, and reserved authority; that its question, options, and outcome have equal breadth; and that no optional section introduces additional policy. A case outside the boundary is out of scope and must not be treated as an exception.

```bash
project-standards reconcile --check
project-standards validate
```

The provider validates structure, not whether prose is semantically well bounded. Authoring review remains required.

## Existing create-only scaffolds

An existing `docs/adr/adr.template.md` is consumer-owned and is never overwritten during upgrade. A repository upgrading from 1.3 receives the revised canonical resources and agent summary but keeps its local scaffold bytes. Refresh that scaffold only through a separate reviewed change after comparing it with `standards://adr/1.4/resources/template`.

## Migration

Legacy `markdown.adr.version` and `markdown.adr.require_sections` settings migrate into package options. Migration claims only exact released scaffold bytes; modified or unknown content remains untouched and blocks the atomic migration.

## Troubleshooting

| Finding | Resolution |
| --- | --- |
| Existing scaffold differs from the released template | Preserve it as consumer content or refresh it in a separate reviewed change. |
| Required MADR section is missing | Add the canonical heading or intentionally disable `require_sections`. |
| Outcome governs more than the problem evaluated | Narrow the outcome or split the additional decision into its own ADR. |
| Out-of-scope case is said to require a waiver or supersession | Remove that requirement; only in-scope departures are exceptions. |
| Options use different populations | Rewrite them to answer one bounded question, unless scope itself is the decision. |
