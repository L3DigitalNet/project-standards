---
schema_version: '1.1'
id: 'adr-standard'
title: 'Architecture Decision Record (ADR) Standard'
description: 'How to write Architecture Decision Records using the MADR format with canonical frontmatter.'
doc_type: 'reference'
status: 'active'
created: '2026-06-02'
updated: '2026-06-05'
reviewed: null
owner: ''
tags:
  - adr
  - decisions
  - madr
  - standard
aliases:
  - adr-standard
  - madr-standard
related:
  - 'markdown-frontmatter-standard'
  - 'standards/adr/templates/adr.md'
source:
  - 'https://adr.github.io/madr/'
  - 'https://adr.github.io/'
confidence: 'high'
visibility: 'internal'
license: null
---

# Architecture Decision Record (ADR) Standard

## Purpose

An **Architecture Decision Record (ADR)** captures a single significant, hard-to-reverse decision: the context that forced it, the options considered, the option chosen, and the consequences. ADRs are the durable, reviewable memory of _why_ a system is the way it is.

This standard adopts **[MADR](https://adr.github.io/madr/)** (Markdown Architectural Decision Records) as the body format, layered on top of the repository's [Markdown Frontmatter Standard](../markdown-frontmatter/README.md) for metadata. General ADR background is at <https://adr.github.io/>.

## When to write an ADR

Write an ADR when a decision is **significant** and **costly to reverse**: choosing a datastore, a network segmentation model, an auth approach, a deployment target, a directory convention that many files will follow. Do not write an ADR for routine, easily-reversed choices — use a `doc_type: decision` note or an ordinary `note` for those.

## Frontmatter for ADRs

ADRs use the **standard** canonical frontmatter profile with `doc_type: adr`. MADR's own metadata maps onto canonical fields; ADR-specific people-roles live under the sanctioned `project` namespace (the schema rejects unknown top-level fields, so they cannot sit at the top level).

```yaml
---
schema_version: '1.1'
id: 'adr-0001-homelab-use-postgresql-for-persistent-storage'
title: 'ADR 0001: Use PostgreSQL for persistent storage'
description: 'One-sentence summary of the decision.'
doc_type: 'adr'
status: 'active'
created: '2026-06-02'
updated: '2026-06-02'
reviewed: null
owner: ''
tags: []
aliases: []
related: []
source: []
confidence: 'unknown'
visibility: 'internal'
license: null
supersedes: []
superseded_by: null
project:
  decision_makers: []
  consulted: []
  informed: []
---
```

### MADR field → canonical field

| MADR field | Canonical home | Notes |
| --- | --- | --- |
| `status` | `status` (top level) | Mapped — see the status table below. |
| `date` | `updated` (and `created` on first write) | ISO `YYYY-MM-DD`. |
| `decision-makers` | `project.decision_makers` | List of people who made the decision. |
| `consulted` | `project.consulted` | Two-way input; subject-matter experts. |
| `informed` | `project.informed` | One-way; kept up to date. |
| "superseded by X" | `superseded_by` + `status: superseded` | Use `supersedes` on the replacement ADR. |

### MADR status → canonical `status`

MADR's decision-state vocabulary maps onto the canonical lifecycle enum. The MADR-native word may also be stated in prose at the top of the ADR body for readers familiar with MADR.

| MADR status  | Canonical `status` | Meaning                                       |
| ------------ | ------------------ | --------------------------------------------- |
| (drafting)   | `draft`            | Still being written.                          |
| `proposed`   | `review`           | Proposed; awaiting a decision.                |
| `accepted`   | `active`           | Decision is in force.                         |
| `rejected`   | `archived`         | Considered and declined; kept for the record. |
| `deprecated` | `deprecated`       | Superseded direction; avoid for new work.     |
| `superseded` | `superseded`       | Replaced by another ADR; set `superseded_by`. |

## Body structure (MADR)

**Required sections** — the three MADR 4.0 marks required, each a level-2 (`##`) heading:

1. **Context and Problem Statement** — the situation, forces, and the question being decided.
2. **Considered Options** — the meaningful options on the table.
3. **Decision Outcome** — the chosen option and the justification.

**Optional sections** (include when they add value):

- **Decision Drivers** — qualities, constraints, or forces that weighed on the choice.
- **Consequences** (`### Consequences`, nested under Decision Outcome) — the resulting good/bad/neutral effects.
- **Confirmation** (`### Confirmation`, nested under Decision Outcome) — how compliance with the decision is/will be verified (review, test, fitness function).
- **Pros and Cons of the Options** — per-option arguments.
- **More Information** — evidence, team agreement, revisit conditions, links.

> **Opt-in section check.** Set `markdown.adr.require_sections: true` in `.project-standards.yml` to have the validator assert that every `doc_type: adr` document contains the three required `##` sections above (exact, case-sensitive, level-2 headings; headings inside code fences don't count). It is **off by default**, and the optional sections are never required — honoring MADR's short→large flexibility. This lives under a separate `markdown.adr` config key from the `markdown.frontmatter` settings.

Templates for each verbosity level live in [`templates/`](templates/): [`adr.md`](templates/adr.md) (full, with explanations), `adr-minimal.md` (required sections, with explanations), `adr-bare.md` (all sections, empty), and `adr-bare-minimal.md` (required sections, empty).

- **`id`**: `adr-NNNN-repo-name-short-title` in lowercase kebab-case, e.g. `adr-0001-homelab-use-netbox-as-source-of-truth`. `NNNN` is a zero-padded, repo-scoped sequence number; the **`repo-name` segment makes the id globally unique across every repository**, so an ADR stays unambiguous when referenced from another repo's `related:` list. The `adr-` prefix keeps it self-identifying as an ADR.
- **Filename**: `adr-NNNN-short-title.md`, e.g. `adr-0001-use-netbox-as-source-of-truth.md`. The filename carries the `adr-` prefix but **omits the `repo-name` segment** — it lives inside its own repo, where the repo is implied, so repeating the repo-name in every filename would be redundant.
- **`title`**: human form, e.g. `ADR 0001: Use NetBox as source of truth`.

> **ADRs are the one document type where the filename and `id` intentionally differ.** Both carry the `adr-NNNN-` prefix, but the **`id` additionally embeds the `repo-name`** for global uniqueness (it is path-independent by design — see the [Markdown Frontmatter Standard](../markdown-frontmatter/README.md)), while the **filename omits it** to stay short and repo-local. For every other `doc_type`, deriving the filename from the `id` slug remains the norm. (This deliberately diverges from upstream [MADR](https://adr.github.io/madr/) filenames, which start with the bare number; MADR tooling is an optional convenience here, not a conformance target, so at-a-glance `adr-` filenames win.)

## Directory and index convention

In a consuming repository, ADRs live together under `docs/decisions/`, with a `README.md` index:

```text
docs/decisions/
├── README.md                                       # doc_type: index — links every ADR
├── adr-0001-use-netbox-as-source-of-truth.md       # id: adr-0001-homelab-use-netbox-as-source-of-truth
└── adr-0002-segment-iot-onto-its-own-vlan.md       # id: adr-0002-homelab-segment-iot-onto-its-own-vlan
```

The index `README.md` carries `doc_type: index` frontmatter and lists each ADR by number and title. (This standards repository documents the convention but does not itself host a `docs/decisions/` tree, since it is the source of the standard rather than a consumer of it.)

## Supersession workflow

When a new ADR replaces an old one, update **both** documents in the same change:

- New ADR: add the old ID to `supersedes`.
- Old ADR: set `superseded_by` to the new ID and `status: superseded`.

## References

- [MADR — Markdown Architectural Decision Records](https://adr.github.io/madr/)
- [Architectural Decision Records](https://adr.github.io/)
- [Markdown Frontmatter Standard](../markdown-frontmatter/README.md)
