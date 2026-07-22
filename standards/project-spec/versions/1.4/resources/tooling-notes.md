# Spec Template Tooling Notes

Reference for building programmatic tooling (validators, generators, spec managers, CI checks) over the three specification templates:

- `spec-light-template.md`
- `spec-standard-template.md`
- `spec-full-template.md`

The `project-standards spec validate` command and the maintainer pytest checks enforce the machine-checkable subset of this document. Read this before assuming anything about structure — several deliberate design choices will trip a naive parser (see [Gotchas](#9-gotchas--anti-patterns)).

## Table of Contents

- [Spec Template Tooling Notes](#spec-template-tooling-notes)
  - [Table of Contents](#table-of-contents)
  - [1. Mental model: one canonical registry, three subset views](#1-mental-model-one-canonical-registry-three-subset-views)
  - [2. Stable numbering with intentional gaps](#2-stable-numbering-with-intentional-gaps)
  - [3. Canonical section registry (from Full)](#3-canonical-section-registry-from-full)
  - [4. Appendix scheme](#4-appendix-scheme)
  - [5. ID conventions](#5-id-conventions)
    - [5.1 Prefix registry (Appendix A — identical "Defined In" across all tiers)](#51-prefix-registry-appendix-a--identical-defined-in-across-all-tiers)
    - [5.2 Format](#52-format)
    - [5.3 Example IDs are placeholders](#53-example-ids-are-placeholders)
  - [6. Cross-references](#6-cross-references)
  - [7. Frontmatter schema](#7-frontmatter-schema)
  - [8. Interchangeability guarantees (what tooling may rely on)](#8-interchangeability-guarantees-what-tooling-may-rely-on)
  - [9. Gotchas / anti-patterns](#9-gotchas--anti-patterns)
  - [10. Placeholder / unfilled detection](#10-placeholder--unfilled-detection)
  - [11. Validation](#11-validation)
  - [12. Suggested parse pipeline](#12-suggested-parse-pipeline)

---

## 1. Mental model: one canonical registry, three subset views

The templates form a strict tier ladder — **Light ⊂ Standard ⊂ Full** — and **Full is canonical**. Light and Standard are not independent documents; they are _pruned views_ of Full that keep the **same section and appendix numbers**. A section that exists in more than one tier has the **same number in every tier**.

The profile is declared in frontmatter (`profile: light | standard | full`) and in the title (`# … — Specification (Light)`).

**Design intent for tooling:** validate any spec against a _single_ canonical map (Full's), key on section **number** (stable) rather than document position (varies), and treat a tier upgrade as an additive operation (insert missing sections at their canonical numbers — no renumbering, no reference rewrites).

---

## 2. Stable numbering with intentional gaps

Because lower tiers omit higher-tier sections but keep canonical numbers, **their numbering has gaps by design**. This is correct, not corruption.

| Tier | Top-level sections present | Gaps (live only in higher tiers) |
| --- | --- | --- |
| Light | 1, 2, 7, 17, 21 | 3–6, 8–16, 18–20 |
| Standard | 1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 17, 18, 19, 21 | 5, 8.4, 8.6, 14, 15, 16, 18.4, 20 |
| Full | 1–21 (all) | — (canonical) |

**"Sequential" means:** Full is strictly `1..21` with monotonic subsections and no holes; Light/Standard present numbers are each a member of Full's set, appear in ascending order, and a hole is legitimate **only** where a higher-tier section is omitted.

Every gap is marked with a blockquote **omission note** so a reader (and a tool) can tell "intentionally absent" from "accidentally missing":

```markdown
> **§5 (Stakeholders and Users) is Full-tier** and is intentionally omitted at the Standard profile.
```

Notes may cover a **range** (`> **Sections §3–§6 … are … intentionally omitted**`) or a list (`§14 (…), §15 (…), and §16 (…)`). A gap **without** an omission note is a defect.

---

## 3. Canonical section registry (from Full)

Top-level sections (each has the subsections shown in Full; unnumbered sections **Revision History**, **Deviations Log**, **References** also appear):

| § | Title | Light | Standard | Full |
| --- | --- | :-: | :-: | :-: |
| 1 | Purpose & Background | ✅ | ✅ | ✅ |
| 2 | Scope (2.1–2.4) | ✅ | ✅ | ✅ |
| 3 | Context (3.1–3.4) | — | ✅ | ✅ |
| 4 | Goals | — | ✅ | ✅ |
| 5 | Stakeholders and Users | — | — | ✅ |
| 6 | Glossary | — | ✅ | ✅ |
| 7 | Requirements (7.1 FR; 7.2 NFR; 7.3 IR; 7.4 DR) | 7.1 only | ✅ | ✅ |
| 8 | Architecture and Design (8.1–8.6) | — | 8.1–8.3, 8.5 | ✅ |
| 9 | Data Model | — | ✅ | ✅ |
| 10 | Behavior and Workflows (10.1–10.4) | — | ✅ | ✅ |
| 11 | UI Pages / API Endpoints | — | ✅ | ✅ |
| 12 | Error Handling and Recovery (12.1–12.3) | — | ✅ | ✅ |
| 13 | Security and Privacy (13.1–13.6) | — | ✅ | ✅ |
| 14 | Capacity and Scale Assumptions | — | — | ✅ |
| 15 | Risks | — | — | ✅ |
| 16 | Compliance, Licensing, and Data Rights | — | — | ✅ |
| 17 | Testing and Acceptance (17.1 DoD; 17.2 Strategy; 17.3 Traceability) | 17.1 only | ✅ | ✅ |
| 18 | Deployment and Operations (18.1–18.7) | — | 18.1–18.3, 18.5–18.7 | ✅ |
| 19 | Implementation Plan (Waves; MS-0…MS-5; Milestone Summary) | — | no Waves | ✅ |
| 20 | Success Evaluation | — | — | ✅ |
| 21 | Open Questions and Decisions | — | ✅ | ✅ |

Full has **65 numbered headings** total (top-level + subsections). The registry tests derive the exact canonical count from the bundled Full template.

---

## 4. Appendix scheme

Appendix **letters are stable across tiers**, exactly like section numbers.

| Letter | Title (Full)                            | Light | Standard | Full |
| ------ | --------------------------------------- | :---: | :------: | :--: |
| A      | ID Conventions                          |  ✅   |    ✅    |  ✅  |
| B      | Agent Implementation Contract (B.1–B.4) |  ✅   |    ✅    |  ✅  |
| C      | Optional Modules (C.1–C.5)              |   —   |    —     |  ✅  |
| D      | Tailoring                               |  ✅   |    ✅    |  ✅  |

- **Appendix C (Optional Modules) is Full-only.** Light and Standard skip C — an annotated appendix gap, mirroring the section-gap logic.
- **Appendix D is the tailoring appendix in all three**, but its _title_ varies by tier: Light "Upgrading This Spec", Standard "Tailoring", Full "Tailoring Guide". Match on the **letter D**, not the title.

---

## 5. ID conventions

### 5.1 Prefix registry (Appendix A — identical "Defined In" across all tiers)

| Prefix | Meaning                     | Defined In     | Light | Standard | Full |
| ------ | --------------------------- | -------------- | :---: | :------: | :--: |
| `G-`   | Goal                        | §4             |   —   |    ✅    |  ✅  |
| `NG-`  | Non-goal (never)            | §2.2           |  ✅   |    ✅    |  ✅  |
| `WH-`  | Won't have in v1 (deferred) | §2.3           |  ✅   |    ✅    |  ✅  |
| `A-`   | Assumption                  | §3.3           |   —   |    ✅    |  ✅  |
| `C-`   | Constraint                  | §3.4           |   —   |    ✅    |  ✅  |
| `FR-`  | Functional requirement      | §7.1           |  ✅   |    ✅    |  ✅  |
| `NFR-` | Non-functional requirement  | §7.2           |   —   |    ✅    |  ✅  |
| `IR-`  | Interface requirement       | §7.3           |   —   |    ✅    |  ✅  |
| `DR-`  | Data requirement            | §7.4           |   —   |    ✅    |  ✅  |
| `D-`   | Design decision             | §8.3           |   —   |    ✅    |  ✅  |
| `AW-`  | Alternate workflow          | §10.2          |   —   |    ✅    |  ✅  |
| `EC-`  | Edge case                   | §10.3          |   —   |    ✅    |  ✅  |
| `ERR-` | Error-handling requirement  | §12.1          |   —   |    ✅    |  ✅  |
| `R-`   | Risk                        | §15            |   —   |    —     |  ✅  |
| `MS-`  | Milestone                   | §19            |   —   |    ✅    |  ✅  |
| `OQ-`  | Open question               | §21            |  ✅   |    ✅    |  ✅  |
| `DEV-` | Deviation                   | Deviations Log |  ✅   |    ✅    |  ✅  |

A prefix present in a tier's Appendix A resolves to the **same "Defined In"** section in every tier — this is the core interchangeability guarantee. The available prefix _set_ is a strict subset per tier (Light ⊂ Standard ⊂ Full; Standard = Full minus `R-`).

### 5.2 Format

- **Non-milestone IDs are zero-padded to 3 digits:** `FR-001`, `G-002`, `NG-001`, `DEV-001`.
- **Milestones are 1 digit:** `MS-0` … `MS-5` (a deliberately bounded set; do **not** zero-pad them, and do **not** extract them with a `\d{3}` pattern).
- Priority values (`Must` / `Should` / `Could`) are table **column values**, never ID prefixes — an ID never changes when its priority changes.

Extraction regex that captures **all** ID types including milestones:

```text
\b([A-Z]{1,4})-([0-9]+)\b       # then validate: MS → 1 digit; everything else → 3 digits
```

A raw regex match is not yet a spec-local ID — skip it when any of four conditions holds: its prefix is standards/acronym noise that matches the shape but is not an ID (`HTTP-…`, `AES-…`, `ISO-…`, `SHA-…`, `RPO`, `RTO`, …), carried in the spec registry's `NOT_AN_ID` denylist; its prefix is the built-in `ADR` reference prefix (ADR ids are minted by the sibling [ADR Standard](https://github.com/L3DigitalNet/project-standards/blob/v5/standards/adr/README.md), not here); its prefix is listed in the selected package's `reference_prefixes` option (external namespaces the spec only cites, e.g. a backlog `RQ-123` or a zero-version license family like `MIT`); or its digits are immediately followed by `.`+digit — a version/SPDX shape such as `MPL-2.0` (a real ID at a sentence end, `FR-007.`, is `.`+space and never matches). Only the remaining tokens are spec-local IDs.

### 5.3 Example IDs are placeholders

Every filled-in ID in the templates (`FR-001`, `FR-002`, `NG-001`, `WH-001`, `A-001`, …) is a **template placeholder**. The same example IDs appearing in a shared section across all three files is **intended consistency**, not a cross-file duplication bug. Uniqueness is required **within a single spec only**.

---

## 6. Cross-references

| Kind | Form | Resolves to |
| --- | --- | --- |
| Section reference | `§N` or `§N.M` (e.g. `§7.1`, `§13.6`) | a number in the **canonical (Full) registry** — _not_ the current file's own sections, since lower tiers reference higher-tier sections by their stable number |
| Appendix reference | `Appendix X` / `Appendix C.n` | a lettered appendix; `Appendix C.n` is valid only in Full |
| Intra-doc link | descriptive text linked to `#slug` | a heading **in the same file** (anchors are file-local) |

**GitHub slug algorithm** (for resolving `#anchor` links): lowercase; strip backticks; drop every character that is not a word char, space, or hyphen; replace spaces with hyphens. E.g. `### B.3 Required Completion Report (verification gate)` → `b3-required-completion-report-verification-gate`.

Format convention: sections are cited with the `§` glyph (not the word "Section"); keep it uniform.

---

## 7. Frontmatter schema

YAML, identical **key set and order** across all three files:

```yaml
spec_id: SPEC-____ # sentinel; real ids match ^SPEC-[0-9A-Z]{4}$ (base36×4, e.g. SPEC-7F3Q)
title: '<Project / Feature Name>'
status: draft # draft | review | approved | superseded
profile: light|standard|full
owner: '<person or team>'
implementer: '<person, team, or coding agent>'
created: 'YYYY-MM-DD'
last_reviewed: 'YYYY-MM-DD'
supersedes: null # SPEC id this replaces, if any
superseded_by: null # filled when retired
related:
  adrs: []
  tickets: []
  repositories: []
  prior_specs: []
```

- **`spec_id` sentinel is `SPEC-____`** (four underscores). It is _intentionally invalid_ against the real-id pattern `^SPEC-[0-9A-Z]{4}$` so a validator rejects an **unfilled** template instead of accepting it as a numbered spec. A spec-creation tool must replace it with a freshly assigned id. (Underscores are not in base36, so `SPEC-XXXX` would be a bad sentinel — `X` is a valid base36 char and would pass validation.)
- `profile` is an enum and **must match the file's tier**.
- `status` is an enum; the inline comment documents the allowed values.

---

## 8. Interchangeability guarantees (what tooling may rely on)

1. A section/subsection **number denotes the same content** in every tier it appears in (same heading title too).
2. **Appendix letters are stable**; the tailoring appendix is always **D**.
3. Every shared **ID prefix maps to the same "Defined In"** section across tiers.
4. **Shared example IDs are identical** in shared sections — documented convention, **not currently machine-checked**.
5. Shared **boilerplate is identical** (spec-lifecycle paragraph, Must/Should/Could definitions, "The system shall", the Agent Implementation Contract) — except where a lower tier legitimately drops a reference to a section it lacks — documented convention, **not currently machine-checked**.
6. A given logical **table has the same column count** across tiers (FR = 5 cols, NG = 3, WH = 4, Boundaries = 2, OQ = 7, DEV = 5, Revision History = 4, Appendix A = 3).

---

## 9. Gotchas / anti-patterns

Things a naive parser gets wrong — each is a **deliberate** design choice:

| Assumption that breaks | Reality |
| --- | --- |
| "Sections are sequential `1,2,3,…`" | Light/Standard have **intentional gaps**. Validate against the canonical registry, allow annotated holes. |
| "Extract IDs with `[A-Z]+-\d{3}`" | Misses milestones (`MS-0`, 1 digit). Use `[A-Z]+-\d+` then validate width per prefix. |
| "The same ID in two files = duplicate" | Example IDs are shared placeholders **by design**. Uniqueness is per-file. |
| "`spec_id: SPEC-____` is malformed data" | It's the **fill-me-in sentinel**, engineered to fail validation. |
| "Appendix C exists everywhere" | **Full-only.** Light/Standard skip C (annotated). |
| "Match the tailoring appendix by title" | Title varies per tier; match on **letter D**. |
| "A missing §14 in Standard is an error" | §14 is Full-tier; its absence is annotated and expected. |
| "Section refs resolve within the file" | Lower tiers reference higher-tier sections by canonical number — resolve against **Full**, not the local file. |

---

## 10. Placeholder / unfilled detection

A spec is still an unfilled template if any of these are present — useful for a "did the author complete it?" gate:

- `spec_id: SPEC-____` (the sentinel)
- `<angle-bracket>` tokens (e.g. `<Project / Feature Name>`, `<goal>`) — the placeholder convention
- literal `YYYY-MM-DD` dates
- the `> **Template instructions (delete before publishing):**` blockquote
- "Suggested prompts:" guidance lists
- example IDs still at `-001`/`-002` with placeholder text

---

## 11. Validation

Consumer specs are checked with the packaged CLI:

```bash
project-standards spec validate [FILE ...]
```

With unified authority, the command resolves the selected Project Specification package from `.standards/`. An explicit `--config PATH` is reserved for read-only legacy/debug operation and cannot override an active unified control plane.

Exit `0` = all selected specs conform, including a configured include set that currently matches no files under package 1.4 or a later compatible 1.x version; `1` = at least one finding; `2` = bad invocation or discovery/configuration error. Empty configured discovery reports an informational success and skips provider invocation. Suitable for CI / pre-commit. Validation checks: frontmatter key-set/profile/sentinel; section subset + ascending order + gap annotation; appendix lettering; `§`/anchor reference resolution; ID format; Appendix-A registry (used ⊆ declared, Defined-In identity); per-spec ID uniqueness; and table column consistency.

Maintainer template consistency is covered by pytest instead of a standalone script:

- `tests/test_template_conformance.py` checks each bundled template has no structural findings beyond the intentional `SPEC-____` sentinel.
- `tests/test_template_interchangeability.py` checks the cross-tier "Defined In identical for shared prefixes" guarantee.

It intentionally does **not** judge prose (terminology drift, "Context" vs "Background" in shared boilerplate). That layer is better covered by an LLM review — the two together (deterministic structure + semantic prose) are stronger than either alone.

---

## 12. Suggested parse pipeline

1. Split YAML frontmatter from body; read `profile`.
2. Extract headings → build `{number → (title, line, slug)}`; compute GitHub slugs.
3. Load the **canonical registry** once from `spec-full-template.md`; validate this file's numbers as an ordered subset of it.
4. Index IDs with `\b([A-Z]{1,4})-(\d+)\b`, then skip a match when its prefix is in the `NOT_AN_ID` denylist, is a built-in reference prefix (`ADR`), is listed in the consumer's `spec.reference_prefixes`, or its digits are immediately followed by `.`+digit (a version/SPDX shape such as `MPL-2.0`). Only the remaining tokens are spec-local IDs to validate for format.
5. Resolve `§`/`Appendix` references against the canonical registry; resolve `#anchors` against this file's slugs.
6. Parse Appendix A into the prefix→"Defined In" map; assert it matches the canonical map.
