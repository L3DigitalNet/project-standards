# Project Specification Standard

- **Package version:** `1.4`
- **Specification contract:** `1.1`, selected independently with `contract_version`
- **Status:** Active consumer package, managed by the V5 control plane.
- **Owner:** Project standards / repository template
- **Last updated:** 2026-07-19
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
- **Architecture decisions themselves** — a single hard-to-reverse decision is an **ADR** ([ADR Standard](https://github.com/L3DigitalNet/project-standards/blob/v5/standards/adr/README.md)); a spec _references_ ADRs (§8.3) rather than embedding them.
- **Canonical Markdown frontmatter** — spec documents use their **own** frontmatter schema (`spec_id`, `status`, `profile`, relations) and are **not** governed by the [Markdown Frontmatter Standard](https://github.com/L3DigitalNet/project-standards/blob/v5/standards/markdown-frontmatter/README.md). The two relate by reference, not schema inheritance; a consumer that adopts both excludes its spec files from the canonical frontmatter validator (as this repository does).
- **Implementation code and its tooling** — owned by the language standards ([Python Tooling](https://github.com/L3DigitalNet/project-standards/blob/v5/standards/python-tooling/README.md) and [Python Coding](https://github.com/L3DigitalNet/project-standards/blob/v5/standards/python-coding/README.md)).
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

The standard ships three templates — **profiles** — that form a strict ladder: **Light ⊂ Standard ⊂ Full**. Full is canonical; Light and Standard are pruned views of it that keep the **same section and appendix numbers**, so a section means the same thing in every profile and upgrading is purely additive (G1, G2).

| Profile | Template | Use for |
| --- | --- | --- |
| **Light** | [`spec-light-template.md`](templates/spec-light-template.md) | Scripts, small tools, single-session agent tasks. |
| **Standard** | [`spec-standard-template.md`](templates/spec-standard-template.md) | Typical features and services. |
| **Full** | [`spec-full-template.md`](templates/spec-full-template.md) | Multi-service systems, durable data, external integrations, or multiple stakeholders. |

**How the tiers relate.** Because lower tiers omit higher-tier sections but keep the canonical numbers, their numbering has **intentional, annotated gaps** — an omission note (`> **§N … is Full-tier** and is intentionally omitted`) marks every one, so "deliberately absent" is always distinguishable from "accidentally missing." Upgrading inserts the missing sections at their canonical numbers and clears the omission notes; it never renumbers sections or rewrites `§`/ID references. (The `upgrade` command, [§5](#5-tooling), performs this mechanically.)

**Choosing a profile.** Pick the smallest that fits, then upgrade if the project grows:

- Owns durable data → at least **Standard** (it carries Backup/DR at §18.6; Light does not).
- Talks to external paid or rate-limited APIs, makes automated decisions users must trust, or spans multiple services or stakeholders → **Full**.
- Implemented by a coding agent → the Agent Implementation Contract (Appendix B) applies at every tier; it is the cheapest section and the highest-leverage one.

Each template's own **Appendix D (Tailoring)** carries the authoritative per-tier guidance; the full canonical section registry and the tooling contract live in [`resources/tooling-notes.md`](resources/tooling-notes.md).

---

## 5. Tooling

The standard ships tooling — distributed as a `project-standards` CLI subcommand group with an optional reusable CI workflow — that operates on a repository's real specifications. It is **read-only plus guarded authoring**: it never rewrites a spec's prose, only analyzing it or generatively producing/extending structure. Every command is profile-agnostic (one code path serves all three tiers via the canonical registry) and offers machine-readable `--json` output. The capability set below is a considered draft, tiered into a v1 core and a planned wave; the surface is still subject to change.

> **Consumer vs. maintainer checks.** The `validate`/`lint` capabilities below run against a **consumer's own specs**. This repository's three bundled templates are checked by `tests/test_template_conformance.py` and `tests/test_template_interchangeability.py` so template drift is caught in the normal pytest gate.

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

- **`validate`** _(core)_ — the deterministic structural gate: canonical-registry conformance (numbering subset, annotated gaps, appendix lettering), cross-reference resolution, frontmatter key-set/enum/sentinel, `spec_id` pattern, per-spec ID uniqueness, `used ⊆ declared`, canonical Defined-In mappings, tier-valid prefixes, and table shape. Hard pass/fail with CI exit codes — the contract downstream tooling relies on. → **G2, G3, G7**
- **`lint`** _(core)_ — advisory authoring quality on top of a valid spec: `<angle-bracket>` placeholders, un-deleted template guidance, and status-aware traceability (an `approved` spec must map every `Must` requirement in §17.3, or complete §17.1 at Light tier). Warns without failing a draft. → **G4, G5, G7**
- **`extract`** _(core)_ — print a slice as raw Markdown or JSON: one ID row, a numbered section, a heading-matched section, or an appendix. The context-window optimizer — an agent pulls just §7 and the Deviations Log instead of the whole spec. → **G2, G4**
- **`next`** _(core)_ — print the next free ID for a prefix (e.g. `FR-013`), aware of the per-spec registry and the format rules (three digits; `MS-` single digit). Collision-free ID assignment. → **G4**
- **`status`** _(planned)_ — progress rollup: ID counts by prefix, Must/Should/Could split, traceability coverage, open and blocking `OQ-` counts, unchecked Definition-of-Done items, and milestone state. Human table or `--json`. A reporting view over data the commands above already expose. → **G5**

**Author — guarded generative; produces or extends structure, never rewrites existing prose:**

- **`new`** _(core)_ — scaffold a spec from a chosen profile: copy the template, mint a fresh `spec_id`, and fill frontmatter (owner, implementer, created, profile) and title, resolving the sentinel. → **G1, G7**
- **`upgrade`** _(core)_ — additive tier promotion (Light → Standard → Full): insert the missing canonical sections and appendices at their stable numbers, drop the now-satisfied omission notes, and set `profile:`. Purely additive — no renumbering, no reference rewrites. → **G1, G2**

**Semantic — a standard-defined contract, not a binary command:**

- **Review contract** _(core)_ — a checklist and prompt an agent runs _after_ `validate` and `lint` pass: weak or untestable language ("fast", "robust" without a criterion), terminology drift against the Glossary, requirement atomicity, goal-to-requirement coherence, and non-goal violations. The prose layer the deterministic tools cannot judge. → **G8**

#### External references vs. spec-local IDs

Uppercase `PFX-NNN` tokens are **spec-local IDs** you mint — they must be declared in Appendix A and are width- and tier-checked. Tokens you only **reference** are exempt:

- Lowercase ids such as an ADR's `adr-0001-…` are ignored automatically.
- The `ADR` prefix is a built-in reference, so `ADR-0001` is accepted too.
- Versioned SPDX license identifiers are ignored via the trailing-`.`+digit rule — e.g. `MPL-2.0`, `CC-BY-4.0`, and the current GNU forms `GPL-3.0-only` / `LGPL-2.1-or-later`. A bare colloquial `GPL-3` (not a current SPDX id) is caught by the built-in license-family denylist. A **zero-version** SPDX id like `MIT-0` or `NTP-0` shares a spec-local ID's exact shape — list its family (`MIT`, `NTP`) in `reference_prefixes`.
- Any other external namespace (a backlog `RQ-123`, a gap log `GAP-56`, tickets) goes in the package's `reference_prefixes` option:

```toml
[standards.project-spec.config]
reference_prefixes = ["RQ", "GAP", "MIT"]
```

Reference prefixes are exempt from the Appendix-A, width, and tier checks. A prefix that collides with a canonical spec-local prefix (e.g. `FR`) is rejected — that would disable validation of your own IDs. Only `validate`, `lint`, and `upgrade` consult the selected package options; `extract` and `next` do not need configuration.

---

## 6. Adoption

The V5 control plane selects this package from the catalog, stores its closed options in `.standards/config.toml`, and reconciles the managed `validate-specs.yml` caller. The `project-standards spec` commands resolve the selected package version before reading templates or validating documents. Authored specifications remain consumer-owned. See [`adopt.md`](adopt.md) for package-specific enablement, options, authoring, verification, migration, and disable behavior.

---

## 7. Exceptions process

Three different things get called a "deviation"; the test for a true exception to _this standard_ is simple — **does the deterministic tooling refuse it?**

1. **Tailoring** — choosing a profile, deleting a conditional section (§11, §18.6) with an annotated reason, upgrading a tier. Tooling-safe **by construction**: the templates and validator are built to accept these (profile gaps, annotated omissions, additive upgrades). Not an exception.
2. **Implementation deviations** — where the _built software_ diverges from what a spec requires. Recorded in that spec's **Deviations Log** (`DEV-` IDs) per the Agent Implementation Contract. The log is itself a canonical section, so it too is tooling-safe. Not an exception.
3. **Deviating from the standard itself** — dropping a canonical section, changing the numbering or ID scheme, using a different frontmatter schema, abandoning the tiered templates. This is exactly the class of deviation the tooling **cannot absorb**, and it is the exceptions process.

**An exception forfeits the machine guarantees — and an ADR does not restore them.** The deterministic tooling ([§5](#5-tooling)) rests on these invariants; a case-3 deviation will make `validate` report the spec as non-conformant and may cause `extract` / `next` / `upgrade` to mis-parse or refuse it. Documenting the exception in an ADR records _why_; it does not teach the tool to accept it. The consumer must **also scope the tooling to exclude the non-conforming spec** (or accept its failures) — the same way this repository excludes files from the frontmatter validator. That cost is deliberate: an exception opts a spec out of the guarantees (G2–G7) that make the standard worth adopting, so prefer tailoring (case 1) wherever it suffices.

When an exception is genuinely warranted, document it as a conformant ADR under `docs/adr/`, using a zero-padded sequence number for `NNNN`:

```text
docs/adr/adr-NNNN-project-spec-exception.md
```

The [ADR Standard](https://github.com/L3DigitalNet/project-standards/blob/v5/standards/adr/README.md) is the authority for the ADR's shape (`id`, filename, frontmatter, MADR sections). State what the standard requires, what the project does instead, **which tooling guarantees are forfeited and how the tool is scoped around them**, and why built-in tailoring does not already cover it.

- **Valid exceptions:** an existing project with a heavily-invested house spec format it cannot migrate yet; a domain that needs a section the canonical registry does not model; a regulated context requiring a fixed external template.
- **Invalid exceptions:** deleting a required section to avoid writing it; inventing a private ID scheme on preference; skipping the Agent Implementation Contract because "the agent will figure it out."

---

## 8. Update process / review cadence

Review this standard when:

- **A template changes** — a canonical section or appendix is added, removed, or renumbered. Any such change must preserve the interchangeability guarantees (G2); run `tests/test_template_conformance.py` and `tests/test_template_interchangeability.py` to prove the three profiles still agree.
- The **spec frontmatter schema** (`spec_id`, `status`, `profile`, relations) or its lifecycle changes.
- The **ID prefix registry** (Appendix A) or ID format changes.
- The **Agent Implementation Contract** (Appendix B) changes.
- A **referenced external standard** shifts — ISO/IEC/IEEE 29148, IEEE 1016, ISO/IEC/IEEE 42010, the [ADR Standard](https://github.com/L3DigitalNet/project-standards/blob/v5/standards/adr/README.md) / MADR, or the OpenAPI Specification (the templates cite these; verify citations on review).
- The **tooling contract or capability set** ([§5](#5-tooling)) changes.

Review cadence:

- Light review: quarterly.
- Full review: annually.
- Immediate review: after any template-breaking change, a frontmatter/ID-scheme change, or an upstream standard revision.

Until the standard is released for adoption it is under active development and reviewed continuously; the cadence above takes effect at first release.

---

## 9. References and resources

**Tooling (preliminary):**

- [Tooling notes](resources/tooling-notes.md)
- Maintainer template conformance test: `tests/test_template_conformance.py`
- Maintainer template interchangeability test: `tests/test_template_interchangeability.py`

**Templates:**

- [Light template](templates/spec-light-template.md)
- [Standard template](templates/spec-standard-template.md)
- [Full template](templates/spec-full-template.md)

---

## 10. Source register

This register records the external standards the **templates** draw structure and terminology from. The README body itself is policy prose and carries no inline citations, so the register stands alone rather than resolving `[Sxx]` markers. It is the check target for [§8](#8-update-process--review-cadence)'s "a referenced external standard shifts" review trigger; the `Last checked` date is when each edition was last confirmed current.

| ID | Source | URL | What it grounds in the templates | Last checked |
| --- | --- | --- | --- | --- |
| S01 | ISO/IEC/IEEE 29148:2018 — Systems and software engineering — Requirements engineering | [iso.org/standard/72089](https://www.iso.org/standard/72089.html) | §7 requirements structure and quality criteria ("The system shall …"; testable, necessary, unambiguous) | 2026-07-04 |
| S02 | IEEE 1016-2009 — Software Design Descriptions | [standards.ieee.org/ieee/1016/4502](https://standards.ieee.org/ieee/1016/4502) | §8 Architecture and Design — design-description structure and views | 2026-07-04 |
| S03 | ISO/IEC/IEEE 42010:2022 — Architecture description (2nd ed.) | [standards.ieee.org/ieee/42010/6846](https://standards.ieee.org/ieee/42010/6846) | §8 architecture concepts — stakeholders, concerns, viewpoints, views | 2026-07-04 |
| S04 | OpenAPI Specification | [spec.openapis.org](https://spec.openapis.org/) | §7.3 Interface Requirements and §11 — HTTP API contracts | 2026-07-04 |

Notes from the 2026-07-04 verification pass:

- All four editions were confirmed current on 2026-07-04. **OpenAPI's current release is 3.2.0** (2025-09-19); the templates cite "OpenAPI Specification" without pinning a version, so no template change is required — pin to a specific version only if a spec needs a particular contract dialect.
- **IEEE 830-1998** appears in the templates only as an explicitly **superseded** caution (replaced by 29148:2018); it is not an authority and is not tracked as a live source here.
- The **ADR / MADR** relationship is owned by the sibling [ADR Standard](https://github.com/L3DigitalNet/project-standards/blob/v5/standards/adr/README.md) and tracked in its own source register (MADR 4.0.0); it is not duplicated here.
