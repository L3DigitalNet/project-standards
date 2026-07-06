# Design: spec-validator external references & token hygiene (issue #3, F1–F4)

**Date:** 2026-07-06 **Status:** brainstorming complete — awaiting user spec review **Author:** session 2026-07-06

## Table of Contents

- [Design: spec-validator external references \& token hygiene (issue #3, F1–F4)](#design-spec-validator-external-references--token-hygiene-issue-3-f1f4)
  - [Table of Contents](#table-of-contents)
  - [Problem / Goal](#problem--goal)
  - [Scope](#scope)
  - [Decisions (locked during brainstorming)](#decisions-locked-during-brainstorming)
  - [Root cause — one missing abstraction](#root-cause--one-missing-abstraction)
  - [Component 1 — Config: `spec.reference_prefixes`](#component-1--config-specreference_prefixes)
  - [Component 2 — The skip set (built-ins + config + shape rules)](#component-2--the-skip-set-built-ins--config--shape-rules)
  - [Component 3 — Wiring the skip set into the scan](#component-3--wiring-the-skip-set-into-the-scan)
  - [Component 4 — Error message (F2's misleading chain)](#component-4--error-message-f2s-misleading-chain)
  - [Component 5 — Docs & template (F1)](#component-5--docs--template-f1)
  - [Invariants — what must NOT change](#invariants--what-must-not-change)
  - [Component 6 — Testing](#component-6--testing)
  - [Acceptance criteria](#acceptance-criteria)
  - [Non-goals](#non-goals)
  - [Versioning & docs impact](#versioning--docs-impact)

## Problem / Goal

A downstream consumer (`docmend`) adopting the Project Specification standard filed [issue #3](https://github.com/L3DigitalNet/project-standards/issues/3): the `spec validate` ID checker rejects legitimate cross-references and misparses license identifiers, with error messages that lead the consumer into a dead end. Four of the five findings (F1–F4) live in one subsystem — the spec-validator's ID scan — and share one root cause. This design fixes them together. F5 (the markdown-tooling formatter-authority question) is a separate standard and gets its own spec (Spec B).

The validator's job is to enforce that a spec's **own, mintable** requirement IDs (`FR-007`, `NFR-003`, `MS-1`, …) are well-formed, declared in Appendix A, and valid at the document's tier. The bug is that it cannot tell those apart from tokens the spec merely _references_ — an ADR id, a backlog item (`RQ-123`), a gap-log entry (`GAP-56`) — or from tokens that only _look_ like IDs, such as SPDX license identifiers (`MPL-2.0`). Every one of those trips a rule intended for spec-local IDs, and the reference case has no supported escape at all.

## Scope

Single subsystem: `src/project_standards/specs/` — `config.py` (config surface), `registry.py` (the token regex, the built-in denylist), `document.py` (the ID scan), `commands/validate.py` (the ID checks and their messages) — plus the shipped `spec-full-template.md` and the `standards/project-spec/README.md` docs. No CLI-surface change, no new command, no registry/template _contract_ change (canonical sections, appendices, frontmatter keys, and spec-local ID width all stay fixed).

## Decisions (locked during brainstorming)

1. **F2 mechanism:** a config key `spec.reference_prefixes` (not an in-document Appendix-A marker). External namespaces are repo-wide conventions, so repo-level config is their natural home; this extends the existing `SpecConfig` (already `include`/`exclude`) and leaves the versioned Appendix-A template contract untouched.
2. **F1 (ADR):** ship `ADR` as a _built-in_ reference prefix (always exempt, zero config) _and_ fix docs. Both `adr-0001-…` (the ADR standard's canonical lowercase form, already passing) and the tempting uppercase `ADR-0001` validate out of the box, so the shipped template's `ADR` column just works.
3. **F4 (licenses):** a zero-config pair — skip tokens whose digits are immediately followed by `.`+digit (versioned SPDX/version strings), _and_ broaden the built-in `NOT_AN_ID` denylist with common SPDX family prefixes. No new config key.
4. **F3 (width):** _subsumed_, not a feature. Referenced IDs of any width validate because they are skipped entirely; spec-local IDs keep the fixed 3-digit (`MS`=1) contract. There is no per-prefix width setting.

## Root cause — one missing abstraction

The scan in `document.py` has exactly two categories: a token either matches `ID_TOKEN` and is treated as a spec-local ID, or its prefix is in the hardcoded `NOT_AN_ID` set and is ignored. There is no third category for "a token I reference but do not own." F2, F3, and F4 are all the same shape — a token that should not be validated as a spec-local ID but has nowhere to be classified. The fix introduces that third category as a **skip set**, assembled from three sources (built-in prefixes, config-declared reference prefixes, and shape rules) and applied at the single point where the scan decides whether a token counts.

## Component 1 — Config: `spec.reference_prefixes`

`SpecConfig` (a frozen dataclass in `config.py`) gains `reference_prefixes: list[str]`, parsed from the `spec:` block beside `include`/`exclude`, defaulting to `[]`. `load_spec_config` reads and validates it:

- Each entry must match `^[A-Z]{1,4}$` — same alphabet as `ID_TOKEN`'s prefix group. A malformed entry (lowercase, too long, punctuation) raises `ConfigError`, which the shell already maps to exit 2. A lowercase entry would never match `ID_TOKEN` anyway, so rejecting it early surfaces the mistake instead of silently doing nothing.
- An entry equal to a **canonical spec-local prefix** (any prefix declared in the bundled templates' Appendix A — `FR`, `NFR`, `MS`, …) is rejected with a distinct `ConfigError`. Allowing it would let a consumer silently switch off validation of their real requirement IDs, which is the opposite of the standard's purpose. The set of canonical prefixes is already available from the registry (`Registry.prefix_defined_in` / `tier_prefixes`).

## Component 2 — The skip set (built-ins + config + shape rules)

A token is **skipped** (not recorded in `used_ids`, so it faces none of `SV-ID-FMT` / `SV-ID-UNDECLARED` / `SV-ID-TIER`) when _any_ of these holds:

| Source | Rule | Clears |
| --- | --- | --- |
| Built-in denylist | prefix in `NOT_AN_ID` (existing acronyms + new SPDX families `GPL LGPL AGPL MPL BSD EPL BY`) | F4 bare |
| Built-in references | prefix `== "ADR"` | F1 |
| Config references | prefix in `spec.reference_prefixes` | F2 |
| Shape (version/SPDX) | the matched digits are immediately followed by `.` and another digit | F4 dot |

The dot rule is safe against real IDs: a spec-local ID at a sentence boundary (`…see FR-007.`) is followed by `.`+whitespace, never `.`+digit, so it is never skipped; `MPL-2.0` (`.`+`0`) is. The `BY` entry handles `CC-BY-4.0`, which `ID_TOKEN` tokenizes as `BY-4` (the `CC-` fragment has no adjacent digit). `ADR` is a distinct built-in _reference_ constant, kept separate from `NOT_AN_ID` so the two intents (a non-ID acronym vs. a real ID in another namespace) stay legible.

## Component 3 — Wiring the skip set into the scan

The scan needs the config-derived reference prefixes, which `registry.py` (template-only, no config) must not import. Cleanest seam: `parse_document` in `document.py` gains an optional parameter `reference_prefixes: frozenset[str] = frozenset()`. The `validate` and `lint` commands pass the value resolved from `SpecConfig`; `new`'s best-effort corpus parse (which only needs `spec_id`s) passes the default empty set. Inside the scan loop (`document.py:83`), the existing `if pfx in NOT_AN_ID: continue` becomes a single `_skip(pfx, digits, tail)` predicate covering all four rows of the table above. Built-in prefix constants (`NOT_AN_ID`, and a new `BUILTIN_REFERENCE_PREFIXES = frozenset({"ADR"})`) stay in `registry.py` as the zero-config floor; the config layer only _adds_ to them.

## Component 4 — Error message (F2's misleading chain)

Today an undeclared external prefix fires `SV-ID-UNDECLARED` ("used but not in Appendix A"); the consumer declares it, then hits `SV-ID-TIER`. With the skip set, a _configured_ reference prefix never reaches these checks. But a genuinely-unknown prefix still should, and its message must name the real resolution instead of the dead-end path:

> `[SV-ID-UNDECLARED] prefix RQ- is not a canonical spec-local prefix. If it names an external namespace (backlog, tickets, another spec), add it to spec.reference_prefixes; otherwise declare it in Appendix A with a canonical prefix.`

`SV-ID-TIER` keeps its meaning (a declared prefix used at the wrong tier) but is no longer reachable by mistaking an external reference for a spec-local ID.

## Component 5 — Docs & template (F1)

- **Template:** seed the `spec-full-template.md` §8.3 Design-Decisions `ADR` column with a real `adr-0001-…` example value, so the column that today invites the wrong uppercase form models the right one.
- **Standard docs:** in `standards/project-spec/README.md`, document the **namespace split** explicitly — uppercase `PFX-NNN` are mintable, spec-local IDs (Appendix-A-declared, 3-digit); lowercase `adr-…` and any prefix listed in `spec.reference_prefixes` (plus the built-in `ADR`) are external references, exempt from the ID rules. Document the config key, the built-in `ADR`, and the license-token handling so none of this is discoverable only by reading validator source.

## Invariants — what must NOT change

- Every spec that validates today still validates (this change only _loosens_). The dogfooded `standards/project-spec/examples/spec.example.md` must pass unchanged.
- Spec-local ID rules are untouched: `FR-007` is still 3-digit-or-fail, still must be declared in Appendix A, still tier-checked.
- Registry contract (canonical sections, appendices, frontmatter key order, spec-id pattern) is unchanged.
- Exit-code semantics unchanged: config errors → 2, validation findings → their existing code.

## Component 6 — Testing

Test-driven, per the repo's TDD discipline. Unit:

- `load_spec_config`: parses `reference_prefixes`; rejects bad shape; rejects a canonical-prefix collision; empty/default when absent.
- Skip set: a config reference prefix, the built-in `ADR`, each new `NOT_AN_ID` family, and the dot rule each cause the token to be absent from `used_ids`; a normal spec-local ID is still recorded.
- Boundary: `FR-007.` at a sentence end is _not_ skipped (dot rule only fires on `.`+digit).
- Message: `SV-ID-UNDECLARED` emits the new text; `SV-ID-TIER` still fires for a real tier violation.

Integration: a full-profile spec citing `adr-0001-…`, `RQ-123` (configured), `MPL-2.0`, and `GPL-3` validates clean; the same spec with `RQ-123` _not_ configured fails with the reworded `SV-ID-UNDECLARED`.

## Acceptance criteria

- The issue's minimal repro (`spec validate` over a spec citing an ADR, an external ID, and a license id) exits 0 with the documented config.
- `uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit` all green; branch coverage does not regress.
- `uv run validate-frontmatter --config .project-standards.yml` and `spec validate` (dogfood) both pass.

## Non-goals

- No code-span / fenced-code exclusion from the scan. Scanning raw body text is a deliberate anti-evasion property — backticking an ID must not hide it from validation.
- No in-document Appendix-A reference marker (config is the chosen mechanism).
- No per-prefix width configuration (F3 is subsumed by skipping references).
- F5 (markdown-tooling formatter authority) — separate spec.

## Versioning & docs impact

A backward-compatible **loosening** plus additive config: specs that failed on F1–F4 now pass, and nothing that passed regresses. Under the repo's per-standard/semantic versioning that is a **minor bump, v4.0.0 → v4.1.0**. The release must update `CHANGELOG.md` ([4.1.0] with the new config key and behavior), the `standards/project-spec/README.md` namespace-split docs, and the `spec-full-template.md` example row. Downstream `@v4` pins pick it up automatically via the moving `v4` tag.
