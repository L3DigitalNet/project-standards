# Architecture Decision Record (ADR) Standard

- **Package version:** `1.4`
- **ADR contract:** `1.0`, selected independently with `contract_version`
- **Owner:** Project standards / repository template
- **Last updated:** 2026-08-03
- **Last source check:** 2026-06-07
- **Scope:** Architecture Decision Records in repositories governed by this package.

---

## Table of Contents

- [Architecture Decision Record (ADR) Standard](#architecture-decision-record-adr-standard)
  - [Table of Contents](#table-of-contents)
  - [Evidence convention](#evidence-convention)
  - [Purpose](#purpose)
  - [When to write an ADR](#when-to-write-an-adr)
  - [Bound the decision](#bound-the-decision)
    - [Decision-boundary review](#decision-boundary-review)
  - [Frontmatter for ADRs](#frontmatter-for-adrs)
    - [MADR field to canonical field](#madr-field-to-canonical-field)
    - [MADR status to canonical `status`](#madr-status-to-canonical-status)
  - [Body structure (MADR)](#body-structure-madr)
  - [Directory and index convention](#directory-and-index-convention)
  - [Supersession workflow](#supersession-workflow)
  - [References](#references)
  - [Source coverage map](#source-coverage-map)
  - [Source register](#source-register)

## Evidence convention

This document separates **source-backed facts** from **project policy decisions**.

- Source-backed facts cite source IDs such as `[S01]`.
- Every source ID is listed in the [Source register](#source-register), with `Last checked: 2026-06-07`.
- Policy decisions are explicit local choices for this project ecosystem—informed by sources, but not mandated by them. The ADR-specific choices are: the `id` embeds the `repo-name` while the filename omits it; ADRs live under `docs/adr/`; the MADR body-section check is opt-in and off by default; and authors must bound a decision explicitly without adding a required MADR heading.
- MADR is the single external authority for body structure and status vocabulary. Re-verify it against [S01] whenever this standard is reviewed—the upstream specification has shifted before.

---

## Purpose

An **Architecture Decision Record (ADR)** captures a single significant, hard-to-reverse decision: the context that forced it, the options considered, the option chosen, and the consequences. ADRs are the durable, reviewable memory of _why_ a system is the way it is.

This standard adopts **[MADR](https://adr.github.io/madr/)** (Markdown Architectural Decision Records) [S01] as the body format. The Markdown Frontmatter Standard is a compatible companion for metadata, not an installation dependency. General ADR background is at <https://adr.github.io/> [S02].

## When to write an ADR

Write an ADR when a decision is **significant** and **costly to reverse**: choosing a datastore, a network segmentation model, an authentication approach, a deployment target, or a directory convention that many files will follow. Do not write an ADR for routine, easily reversed choices—use a `doc_type: decision` note or an ordinary `note` for those.

Do not combine related decisions merely because they arise in the same project. Split decisions that are independently reversible, require materially different options or evidence, or govern different populations.

## Bound the decision

An ADR governs only the decision explicitly made within its stated boundary. The motivating problem, surrounding architecture, implementation consequences, and examples do not implicitly extend its authority to adjacent concerns.

Before evaluating options, define:

- **Governed concern** — the exact choice being made.
- **Governed population** — the systems, components, repositories, environments, or classes of change to which the decision applies.
- **Applicability condition** — the circumstances that bring an item within the governed population.
- **Exclusions** — realistic adjacent concerns or populations that the ADR explicitly does not govern.
- **Reserved authority** — related decisions that remain open and require their own decision record if they become significant.

An item outside the declared boundary is **out of scope**, not an exception. An exception is an item within the governed population that is permitted to depart from the chosen rule. Do not require an exception, waiver, or superseding ADR for a case the ADR never governed.

The ADR title, problem question, considered options, and decision outcome must describe the same decision at the same breadth. The outcome must not be broader than the problem that was evaluated, and the options must not silently use different populations or applicability conditions unless scope itself is the decision being evaluated.

Establish the boundary in **Context and Problem Statement**, then restate the operative boundary in **Decision Outcome**. A reader should be able to determine from the outcome alone:

1. What is required, prohibited, or selected.
2. Which population is governed.
3. When the decision applies.
4. What is explicitly outside its authority.

Optional sections may explain the decision but must not enlarge it. Decision drivers justify the choice; consequences describe effects; confirmation determines applicability and verifies in-scope conformance; and more information records supporting context. A normative requirement introduced only in an optional section must be moved into the bounded Decision Outcome or removed.

Use universal terms such as “all,” “any,” “every,” “always,” “never,” “the project,” “the repository,” “standard,” and “default” only with an explicit governed population and applicability condition. Selecting one mechanism does not govern adjacent mechanisms by implication. For example, choosing a relational datastore does not automatically govern caches, queues, search indexes, embedded state, analytical stores, or vendor-managed dependencies.

### Decision-boundary review

Before accepting an ADR, verify that:

- At least one realistic out-of-scope case is stated.
- A reasonable reader cannot interpret the outcome as governing that case.
- Every considered option answers the same bounded question.
- No consequence, confirmation statement, example, or implementation note creates additional policy.
- A change outside the boundary can proceed without an exception to this ADR.
- Each combined concern would have to be reconsidered together; otherwise split the ADR.

These are authoring requirements within the existing MADR sections. They do not add a required heading to the ADR contract.

## Frontmatter for ADRs

ADRs use the **standard** canonical frontmatter profile with `doc_type: adr`. MADR's own metadata maps onto canonical fields; ADR-specific people roles live under the sanctioned `project` namespace.

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
owner: 'repo-maintainers'
tags: []
aliases: []
related: []
supersedes: []
superseded_by: null
source: []
confidence: 'unknown'
visibility: 'internal'
license: null
project:
  decision_makers: []
  consulted: []
  informed: []
---
```

### MADR field to canonical field

| MADR field | Canonical home | Notes |
| --- | --- | --- |
| `status` | `status` (top level) | Mapped—see the status table below. |
| `date` | `updated` (and `created` on first write) | ISO `YYYY-MM-DD`. |
| `decision-makers` | `project.decision_makers` | List of people who made the decision. |
| `consulted` | `project.consulted` | Two-way input; subject-matter experts. |
| `informed` | `project.informed` | One-way; kept up to date. |
| "superseded by X" | `superseded_by` + `status: superseded` | Use `supersedes` on the replacement ADR. |

### MADR status to canonical `status`

MADR's decision-state vocabulary [S01] maps onto the canonical lifecycle enum. The MADR-native word may also be stated in prose at the top of the ADR body for readers familiar with MADR.

| MADR status  | Canonical `status` | Meaning                                       |
| ------------ | ------------------ | --------------------------------------------- |
| (drafting)   | `draft`            | Still being written.                          |
| `proposed`   | `review`           | Proposed; awaiting a decision.                |
| `accepted`   | `active`           | Decision is in force.                         |
| `rejected`   | `archived`         | Considered and declined; kept for the record. |
| `deprecated` | `deprecated`       | Superseded direction; avoid for new work.     |
| `superseded` | `superseded`       | Replaced by another ADR; set `superseded_by`. |

## Body structure (MADR)

**Required sections**—the three MADR 4.0 sections marked required [S01], each a level-2 (`##`) heading:

1. **Context and Problem Statement** — the situation, forces, decision boundary, and bounded question.
2. **Considered Options** — meaningful options that answer the same bounded question.
3. **Decision Outcome** — the chosen option, justification, and restated operative boundary.

**Optional sections** (include when they add value):

- **Decision Drivers** — qualities, constraints, or forces that weighed on the choice.
- **Consequences** (`### Consequences`, nested under Decision Outcome) — resulting good, bad, or neutral effects; not additional policy.
- **Confirmation** (`### Confirmation`, nested under Decision Outcome) — how applicability is determined and how in-scope compliance is verified.
- **Pros and Cons of the Options** — per-option arguments.
- **More Information** — evidence, agreement, revisit conditions, and links.

> **Opt-in section check.** Set `require_sections = true` in this package's `.standards/config.toml` options to have the selected provider assert that every `doc_type: adr` snapshot contains the three required `##` sections above. It is **off by default**, and optional sections are never required. Decision-boundary quality remains an authoring responsibility; this release does not infer semantic scope from prose.

Templates for each verbosity level live in [`templates/`](templates/): [`adr.md`](templates/adr.md) (full, with explanations), [`adr-minimal.md`](templates/adr-minimal.md) (required sections, with explanations), [`adr-bare.md`](templates/adr-bare.md) (all sections, empty), and [`adr-bare-minimal.md`](templates/adr-bare-minimal.md) (required sections, empty). Agents should normally use an explanatory template; the bare templates assume the author already understands the boundary rules.

- **`id`**: `adr-NNNN-repo-name-short-title` in lowercase kebab-case, for example `adr-0001-homelab-use-netbox-as-source-of-truth`. `NNNN` is a zero-padded, repository-scoped sequence number; the `repo-name` segment makes the ID globally unique.
- **Filename**: `adr-NNNN-short-title.md`, for example `adr-0001-use-netbox-as-source-of-truth.md`. The filename carries the `adr-` prefix but omits the repository name.
- **`title`**: human form, for example `ADR 0001: Use NetBox as source of truth`.

> **ADRs are the one document type where the filename and `id` intentionally differ.** The ID embeds the repository name for global uniqueness, while the filename omits it to remain short and repository-local.

## Directory and index convention

In a consuming repository, ADRs live together under `docs/adr/`, with a `README.md` index:

```text
docs/adr/
├── README.md
├── adr-0001-use-netbox-as-source-of-truth.md
└── adr-0002-segment-iot-onto-its-own-vlan.md
```

The index `README.md` carries `doc_type: index` frontmatter and lists each ADR by number and title.

## Supersession workflow

When a new ADR replaces an old one, update **both** documents in the same change:

- New ADR: add the old ID to `supersedes`.
- Old ADR: set `superseded_by` to the new ID and `status: superseded`.

A new ADR supersedes an old ADR only when it replaces a decision the old ADR actually governed. A new decision for an out-of-scope concern does not supersede the earlier ADR.

## References

- [MADR — Markdown Architectural Decision Records](https://adr.github.io/madr/)
- [Architectural Decision Records](https://adr.github.io/)

## Source coverage map

| Section                    | Source IDs used      |
| -------------------------- | -------------------- |
| Purpose / MADR adoption    | [S01], [S02]         |
| Frontmatter for ADRs       | [S01]                |
| Body structure             | [S01]                |
| Decision-boundary guidance | Local project policy |

## Source register

| ID | Source | URL | What it supports | Last checked |
| --- | --- | --- | --- | --- |
| S01 | MADR 4.0 — Markdown Architectural Decision Records | [https://adr.github.io/madr/](https://adr.github.io/madr/) | Required and optional sections; decision-status vocabulary | 2026-06-07 |
| S02 | Architectural Decision Records | [https://adr.github.io/](https://adr.github.io/) | General ADR background and rationale | 2026-06-07 |

MADR's latest release is **4.0.0** (2024-09-17), confirmed current on 2026-06-07.

[S01]: #source-register
[S02]: #source-register
