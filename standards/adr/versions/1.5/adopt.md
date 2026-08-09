# Adopt ADR 1.5

Use this package when a repository needs MADR-based decision records, a standard scaffold, optional enforcement of MADR's three required sections, explicit guidance for bounding the authority of each decision, and a sanctioned form for amending a decision without superseding it.

The common Catalog 5 control-plane lifecycle is documented by `project-standards`. This guide covers ADR-specific choices only.

## Enable and configure

```bash
project-standards standards enable adr --version 1.5
project-standards reconcile --apply
```

The package retains the two closed options:

```toml
[standards.adr]
enabled = true
version = "1.5"

[standards.adr.config]
contract_version = "1.0"
require_sections = false
```

`contract_version` remains `1.0`: package 1.5 does not add a required heading, frontmatter field, or semantic prose validator. Set `require_sections = true` only to require `## Context and Problem Statement`, `## Considered Options`, and `## Decision Outcome` on `doc_type: adr` snapshots.

## Upgrading from 1.4

1.5 is additive. Every ADR that is valid under 1.4 is valid under 1.5 unchanged: the amendment vocabulary is two optional, default-empty frontmatter lists, the amendment note and the `### Amendments` subsection are optional body content, and no field changes meaning. Change the selected version and reconcile; no ADR needs to be touched to complete the upgrade.

The revised scaffold reaches new consumers only. `docs/adr/adr.template.md` is create-only, so a repository that already has one keeps its bytes—see [Existing create-only scaffolds](#existing-create-only-scaffolds).

## Amendment vocabulary

1.5 adds a sanctioned form for a later change that narrows, restates, or partially replaces a decision an ADR governs while the rest stays in force. Supersession remains the all-or-nothing relationship; amendment is the partial one, and an amended ADR keeps its `status`.

The relationship is two optional lists under the existing `project` frontmatter namespace, reciprocal and updated in the same change:

```yaml
project:
  amends:
    - 'adr-0003-repo-name-earlier-decision' # this record amends that one
  amended_by:
    - 'adr-0009-repo-name-later-decision' # that one amends this record
```

The amendment itself is recorded on the amended record as a blockquote note immediately after the title, before `## Context and Problem Statement`, and—when it needs more room—in an optional `### Amendments` subsection nested under `## Decision Outcome`. See the standard's [Amendment workflow](README.md#amendment-workflow) for the note form, the amendment-versus-supersession rule, and the review that a post-acceptance amendment requires.

### Migrating ad hoc amendment banners

A repository that invented its own banner or inline-paragraph convention before 1.5 converts each occurrence once:

1. Keep the banner where it is if it already sits between the title and `## Context and Problem Statement`; otherwise move it there. Several notes share one blockquote, oldest first, separated by a bare `>` line.
2. Give each note the canonical lead—`> **Amended by ADR NNNN (YYYY-MM-DD).**`, or `> **Amended YYYY-MM-DD ({review}, {finding}).**` for a change made from a post-acceptance review rather than by a later ADR.
3. Add the amended record's `project.amended_by` entry and the amending record's `project.amends` entry in the same change. A self-amendment has no counterpart record; both lists stay empty and the note carries the relationship.
4. Move an inline amendment paragraph that is longer than a few sentences into `### Amendments` under `## Decision Outcome`, leaving a lead sentence in the note that ends `See [Amendments](#amendments).`
5. Confirm the record still reads as an amendment rather than a supersession: if nothing of the original governed decision remains in force, supersede instead.
6. Run the post-acceptance amendment review before publishing, and move `updated` on both records.

Conversion is documentation work; nothing in the package requires it, and an unconverted banner is not a finding.

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

An existing `docs/adr/adr.template.md` is consumer-owned and is never overwritten during upgrade. A repository upgrading from 1.4 receives the revised canonical resources and agent summary but keeps its local scaffold bytes, so the amendment pointer 1.5 adds to the scaffold does not reach it. Refresh that scaffold only through a separate reviewed change after comparing it with this payload's [`templates/adr.md`](templates/adr.md), which is the exact source of the managed artifact.

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
| Amendment leaves nothing of the original decision in force | Supersede instead: set `superseded_by` and `status: superseded` on the old record. |
| Amendment widens the governed concern, population, or applicability | Record it as a new ADR; an amendment may only narrow, restate, or replace within the existing boundary. |
| `amends` and `amended_by` name each other on only one side | Add the missing entry; the relationship is reciprocal and both records change together. |
| Amendment target is already `superseded` or `archived` | Amend the record now in force instead. |
