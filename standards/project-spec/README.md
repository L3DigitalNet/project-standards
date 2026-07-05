# Project Specification Standard

- **Status:** Draft (version 0.1) — in development, reference-only; not registered for adoption or validation
- **Owner:** Project standards / repository template
- **Last updated:** 2026-07-04
- **Last source check:** _TBD_
- **Scope:** Format, structure, conventions, and tooling for authoring project specifications (software projects, features, subsystems, scripts, services) — reusable across repositories.

---

## Table of Contents

- [Project Specification Standard](#project-specification-standard)
  - [Table of Contents](#table-of-contents)
  - [1. Purpose](#1-purpose)
  - [2. Scope](#2-scope)
  - [3. Features](#3-features)
  - [4. Templates](#4-templates)
  - [5. Tooling](#5-tooling)
    - [Purpose](#purpose)
    - [Requirements](#requirements)
    - [Capabilities](#capabilities)
  - [6. Adoption](#6-adoption)
  - [7. Exceptions process](#7-exceptions-process)
  - [8. Update process / review cadence](#8-update-process--review-cadence)
  - [9. References and resources](#9-references-and-resources)
  - [10. Source register](#10-source-register)

## 1. Purpose

A **project specification** is the durable, reviewable definition of a software project, feature, or subsystem _before and while_ it is built: the problem it solves, its scope and non-goals, its requirements, its design, and the plan to deliver it. This standard defines a consistent, machine-checkable format for those specifications so that humans **and coding agents** can produce, read, and act on them reliably.

Without a shared format, specifications drift: every project invents its own structure, requirements are stated ambiguously, completion claims cannot be verified, and cross-references rot. That ad-hoc variability is expensive for humans and _especially_ for coding agents — an agent burns context re-reading an unfamiliar layout, spends tokens on prose it does not need, and has no deterministic way to confirm the work it produced satisfies the spec.

The Project Specification Standard answers that with three tiered templates (Light ⊂ Standard ⊂ Full), stable numbering and typed IDs, a built-in Agent Implementation Contract, and tooling that operates on the result ([§5](#5-tooling)). The payoff compounds: a spec written to this standard is a stable, referenceable contract that survives across sessions, tools, and implementers — and doubles as an executable work order an agent can be held to.

---

## 2. Scope

**In scope** — the format, structure, and conventions of a project specification (a pre- and during-implementation definition of a software project, feature, subsystem, script, or service): the three tiered templates and their canonical section/appendix registry; spec-specific frontmatter and lifecycle; ID and cross-reference conventions; the tier interchangeability guarantees; the Agent Implementation Contract; and the tooling and semantic review contract ([§5](#5-tooling)).

**Out of scope** — this standard does not govern:

- **Project execution** — tickets, boards, scheduling, and status tracking. A spec defines _what and why_; running the work lives in the consumer's project-management system.
- **Architecture decisions themselves** — a single hard-to-reverse decision is an **ADR** ([ADR Standard](../adr/README.md)); a spec _references_ ADRs (§8.3) rather than embedding them.
- **Canonical Markdown frontmatter** — spec documents use their **own** frontmatter schema (`spec_id`, `status`, `profile`, relations) and are **not** governed by the [Markdown Frontmatter Standard](../markdown-frontmatter/README.md). The two relate by reference, not schema inheritance; a consumer that adopts both excludes its spec files from the canonical frontmatter validator (as this repository does).
- **Implementation code and its tooling** — owned by the language standards ([Python Tooling](../python-tooling/README.md) and [Python Coding](../python-coding/README.md)).
- **General prose quality** — the semantic review layer (G8) checks only spec-specific concerns (testable requirements, terminology, traceability), not house writing style.

**Relationship to sibling standards** — a project spec is the _plan_; the sibling standards govern the artifacts the plan produces or references.

| Sibling | Relationship |
| --- | --- |
| ADR | A spec's design decisions (`D-`) link to ADRs; the ADR standard owns the decision record itself. |
| Markdown Frontmatter | Independent schema; specs are excluded from its validator. |
| Markdown Tooling | Still applies — a spec is ordinary `.md`, formatted by Prettier and linted by markdownlint. |
| Python Tooling / Coding | Govern the implementation a spec is realized in. |

**When to write a spec** — this standard defines the _format_; it does not mandate that every change have a spec. Reach for one when a project, feature, or subsystem is large or durable enough that its requirements, design, and plan are worth writing down and holding an implementer to. Pick the smallest profile that fits ([§4](#4-templates)) and upgrade additively as scope grows.

---

## 3. Features

The standard makes the following guarantees to an adopter. Each is a promise the [tooling](#5-tooling) delivers mechanically — a feature earns its place only by making a guarantee real.

- **G1 — Right-sized by tier.** Three profiles form a strict ladder (Light ⊂ Standard ⊂ Full); pick the smallest that fits and grow additively as scope demands.
- **G2 — Stable canonical numbering.** A section or appendix number denotes the same content in every tier. Upgrading a spec _inserts_ sections at their canonical numbers — it never renumbers or rewrites references.
- **G3 — Machine-checkable structure.** Every spec validates deterministically against a single canonical registry: numbering, annotated gaps, appendix lettering, cross-references, table shape, and frontmatter.
- **G4 — Stable, typed IDs.** Requirements, decisions, risks, and the rest carry stable prefixed IDs (`FR-`, `NFR-`, `D-`, …) that survive priority and status changes and are referenceable from commits, tests, and ADRs.
- **G5 — Built-in traceability.** Goals trace to requirements trace to tests, and completion claims are mechanically verifiable through the §17.3 matrix and the Appendix B verification gate.
- **G6 — Executable by an agent.** The Agent Implementation Contract (Appendix B) turns a spec into an actionable work order: implementation rules, prohibited behaviors, a completion/verification gate, and session handoff.
- **G7 — Typed frontmatter and lifecycle.** Canonical metadata (`spec_id`, `status`, `profile`, relations) carries a draft → review → approved → superseded lifecycle, with a sentinel `spec_id` that fails validation until it is filled in.
- **G8 — Two-layer review.** Deterministic structure checks (the tool) plus a defined semantic-review contract (an agent) — together stronger than either alone, because a validator cannot judge prose.

---

## 4. Templates

The standard ships three templates, one per project size and complexity:

- [Light template](templates/spec-light-template.md)
- [Standard template](templates/spec-standard-template.md)
- [Full template](templates/spec-full-template.md)

<!-- TODO: describe when to reach for each template and how they relate (subset/superset). -->

---

## 5. Tooling

The standard ships tooling — distributed as a `project-standards` CLI subcommand group with an optional reusable CI workflow — that operates on a repository's real specifications. It is **read-only plus guarded authoring**: it never rewrites a spec's prose, only analyzing it or generatively producing/extending structure. Every command is profile-agnostic (one code path serves all three tiers via the canonical registry) and offers machine-readable `--json` output. The capability set below is a considered draft, tiered into a v1 core and a planned wave; the surface is still subject to change.

> **Not the same as `check_specs.py`.** [`resources/check_specs.py`](resources/check_specs.py) validates the **three templates against each other** for mutual consistency — a maintainer tool for the standard itself. The `validate`/`lint` capabilities below run against a **consumer's own specs**. Same registry logic, opposite subject.

### Purpose

- Reduce time agents spend on repetitive tasks.
- Reduce agent token usage.
- Optimize agent context window usage.
- Provide programmatic and deterministic processes for routine and wide-ranging tasks.

### Requirements

- Tooling must be agnostic to the template used (light, standard, or full).
- Tooling maintained and distributed by the _Project Standards_ (`project-standards`) repository.
- Able to output in formats consumable by other tools (e.g., JSON, CSV).

### Capabilities

Grouped by what they do to a spec. Each notes the guarantee(s) from [§3](#3-features) it delivers and its build tier — **core** (v1) or **planned** (a later wave). A capability earns a place only by making a guarantee real; reporting-only views are marked planned.

**Analyze — read-only, never writes:**

- **`validate`** _(core)_ — the deterministic structural gate: canonical-registry conformance (numbering subset, annotated gaps, appendix lettering), cross-reference resolution, frontmatter key-set/enum/sentinel, and table shape. Hard pass/fail with CI exit codes — the contract downstream tooling relies on. → **G2, G3, G7**
- **`lint`** _(core)_ — advisory authoring quality on top of a valid spec: leftover sentinel or `<angle-bracket>` placeholders and un-deleted template guidance, per-spec ID uniqueness and `used ⊆ declared`, and status-aware traceability (an `approved` spec must map every `Must` requirement in §17.3). Warns without failing a draft. → **G4, G5, G7**
- **`extract`** _(core)_ — print a slice as raw Markdown or JSON: one ID row, a numbered section, a heading-matched section, or an appendix. The context-window optimizer — an agent pulls just §7 and the Deviations Log instead of the whole spec. → **G2, G4**
- **`next`** _(core)_ — print the next free ID for a prefix (e.g. `FR-013`), aware of the per-spec registry and the format rules (three digits; `MS-` single digit). Collision-free ID assignment. → **G4**
- **`status`** _(planned)_ — progress rollup: ID counts by prefix, Must/Should/Could split, traceability coverage, open and blocking `OQ-` counts, unchecked Definition-of-Done items, and milestone state. Human table or `--json`. A reporting view over data the commands above already expose. → **G5**

**Author — guarded generative; produces or extends structure, never rewrites existing prose:**

- **`new`** _(core)_ — scaffold a spec from a chosen profile: copy the template, mint a fresh `spec_id`, and fill frontmatter (owner, implementer, created, profile) and title, resolving the sentinel. → **G1, G7**
- **`upgrade`** _(core)_ — additive tier promotion (Light → Standard → Full): insert the missing canonical sections and appendices at their stable numbers, drop the now-satisfied omission notes, and set `profile:`. Purely additive — no renumbering, no reference rewrites. → **G1, G2**

**Semantic — a standard-defined contract, not a binary command:**

- **Review contract** _(core)_ — a checklist and prompt an agent runs _after_ `validate` and `lint` pass: weak or untestable language ("fast", "robust" without a criterion), terminology drift against the Glossary, requirement atomicity, goal-to-requirement coherence, and non-goal violations. The prose layer the deterministic tools cannot judge. → **G8**

---

## 6. Adoption

<!-- TODO: how consumers adopt this standard. See adopt.md once written. -->

_To be written — see [`adopt.md`](adopt.md)._

---

## 7. Exceptions process

<!-- TODO: how a project documents a deviation (ADR convention used by the sibling standards). -->

_To be written._

---

## 8. Update process / review cadence

<!-- TODO: triggers for review and light/full/immediate review cadence. -->

_To be written._

---

## 9. References and resources

**Tooling (preliminary):**

- [Tooling notes](resources/tooling-notes.md)
- [Validation tooling](resources/check_specs.py)

**Templates:**

- [Light template](templates/spec-light-template.md)
- [Standard template](templates/spec-standard-template.md)
- [Full template](templates/spec-full-template.md)

---

## 10. Source register

<!-- TODO: source-backed facts + register table once the standard cites external sources. -->

_To be written._
