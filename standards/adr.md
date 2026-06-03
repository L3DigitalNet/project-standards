---
schema_version: '1.1'
id: 'adr-standard'
title: 'Architecture Decision Record (ADR) Standard'
description: 'How to write Architecture Decision Records using the MADR format with canonical frontmatter.'
doc_type: 'reference'
status: 'active'
created: '2026-06-02'
updated: '2026-06-03'
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
  - 'templates/adr.md'
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

This standard adopts **[MADR](https://adr.github.io/madr/)** (Markdown Any Decision Records) as the body format, layered on top of the repository's [Markdown Frontmatter Standard](markdown-frontmatter.md) for metadata. General ADR background is at <https://adr.github.io/>.

## When to write an ADR

Write an ADR when a decision is **significant** and **costly to reverse**: choosing a datastore, a network segmentation model, an auth approach, a deployment target, a directory convention that many files will follow. Do not write an ADR for routine, easily-reversed choices — use a `doc_type: decision` note or an ordinary `note` for those.

## Frontmatter for ADRs

ADRs use the **standard** canonical frontmatter profile with `doc_type: adr`. MADR's own metadata maps onto canonical fields; ADR-specific people-roles live under the sanctioned `project` namespace (the schema rejects unknown top-level fields, so they cannot sit at the top level).

```yaml
---
schema_version: '1.1'
id: 'adr-0001-use-postgresql-for-persistent-storage'
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

**Required sections:**

1. **Context and Problem Statement** — the situation, forces, and the question being decided.
2. **Considered Options** — the meaningful options on the table.
3. **Decision Outcome** — the chosen option and the justification.
4. **Consequences** — the resulting good/bad/neutral effects.

**Optional sections** (include when they add value):

- **Decision Drivers** — qualities, constraints, or forces that weighed on the choice.
- **Confirmation** — how compliance with the decision is/will be verified (review, test, fitness function).
- **Pros and Cons of the Options** — per-option arguments.
- **More Information** — evidence, team agreement, revisit conditions, links.

Templates for each verbosity level live in [`templates/`](../templates/): [`adr.md`](../templates/adr.md) (full, with explanations), `adr-minimal.md` (required sections, with explanations), `adr-bare.md` (all sections, empty), and `adr-bare-minimal.md` (required sections, empty).

## ID and filename convention

- **`id`**: `adr-NNNN-short-title` in lowercase kebab-case, e.g. `adr-0001-use-netbox-as-source-of-truth`. `NNNN` is a zero-padded, repo-scoped sequence number.
- **Filename**: matches the `id` — `adr-NNNN-short-title.md`.
- **`title`**: human form, e.g. `ADR 0001: Use NetBox as source of truth`.

## Directory and index convention

In a consuming repository, ADRs live together under `docs/decisions/`, with a `README.md` index:

```text
docs/decisions/
├── README.md                                   # doc_type: index — links every ADR
├── adr-0001-use-netbox-as-source-of-truth.md
└── adr-0002-segment-iot-onto-its-own-vlan.md
```

The index `README.md` carries `doc_type: index` frontmatter and lists each ADR by number and title. (This standards repository documents the convention but does not itself host a `docs/decisions/` tree, since it is the source of the standard rather than a consumer of it.)

## Supersession workflow

When a new ADR replaces an old one, update **both** documents in the same change:

- New ADR: add the old ID to `supersedes`.
- Old ADR: set `superseded_by` to the new ID and `status: superseded`.

## References

- [MADR — Markdown Any Decision Records](https://adr.github.io/madr/)
- [Architectural Decision Records](https://adr.github.io/)
- [Markdown Frontmatter Standard](markdown-frontmatter.md)
