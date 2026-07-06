# Design: spec-validator external references & token hygiene (issue #3, F1–F4)

**Date:** 2026-07-06 **Status:** codex spec-review converged (round 3, verdict "minor correction"; SA-001…004 + SA-NEW-001/002/003 resolved) — awaiting user spec review **Author:** session 2026-07-06

## Table of Contents

- [Design: spec-validator external references \& token hygiene (issue #3, F1–F4)](#design-spec-validator-external-references--token-hygiene-issue-3-f1f4)
  - [Table of Contents](#table-of-contents)
  - [Problem / Goal](#problem--goal)
  - [Scope](#scope)
  - [Decisions (locked during brainstorming)](#decisions-locked-during-brainstorming)
  - [Root cause — one missing abstraction](#root-cause--one-missing-abstraction)
  - [Component 1 — Config: `spec.reference_prefixes`](#component-1--config-specreference_prefixes)
  - [Component 2 — The skip set (built-ins + config + shape rules)](#component-2--the-skip-set-built-ins--config--shape-rules)
  - [Component 3 — Wiring the skip set into every ID-consuming command](#component-3--wiring-the-skip-set-into-every-id-consuming-command)
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

Single subsystem: `src/project_standards/specs/` — `config.py` (config surface), `registry.py` (the token regex, the built-in denylist), `document.py` (the ID scan), `commands/validate.py` (the ID checks and their messages), `cli.py` (the command wiring) — plus the template copies that carry the §8.3 `ADR` column (the **standard and full** templates, in both the `src/…/specs/templates/` runtime location and the `standards/project-spec/templates/` docs location — four byte-identical files) and the `standards/project-spec/README.md` docs. The only CLI-surface change is _additive_: a single **opt-in** `--config` flag is added to `upgrade` (the one pass/fail gate, besides `validate`/`lint`, that re-validates a document), defaulting to _not_ loading config so unchanged invocations behave exactly as v4.0.0 — no new command, no changed flag semantics, no changed default behavior. `extract` and `next` are intentionally left untouched (§Component 3 explains why neither benefits from the skip set). No registry/template _contract_ change (canonical sections, appendices, frontmatter keys, and spec-local ID width all stay fixed).

## Decisions (locked during brainstorming)

1. **F2 mechanism:** a config key `spec.reference_prefixes` (not an in-document Appendix-A marker). External namespaces are repo-wide conventions, so repo-level config is their natural home; this extends the existing `SpecConfig` (already `include`/`exclude`) and leaves the versioned Appendix-A template contract untouched.
2. **F1 (ADR):** ship `ADR` as a _built-in_ reference prefix (always exempt, zero config) _and_ fix docs. Both `adr-0001-…` (the ADR standard's canonical lowercase form, already passing) and the tempting uppercase `ADR-0001` validate out of the box, so the shipped template's `ADR` column just works.
3. **F4 (licenses):** a **scoped** zero-config promise, not blanket SPDX coverage. Zero-config handles the _common_ shapes — skip tokens whose digits are immediately followed by `.`+digit (versioned SPDX/version strings such as `MPL-2.0`, `LGPL-2.1`, `CC-BY-4.0`), _and_ broaden the built-in `NOT_AN_ID` denylist with common family prefixes (`GPL LGPL AGPL MPL BSD EPL BY`). Zero-version SPDX ids that share the exact spec-local shape (`MIT-0`, `NTP-0`) are deliberately _not_ chased with an unbounded denylist — the consumer lists that family in `spec.reference_prefixes` (the general escape hatch, since `MIT`/`NTP` are valid reference prefixes). No new config key.
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

## Component 3 — Wiring the skip set into every ID-consuming command

The scan needs the config-derived reference prefixes, which `registry.py` (template-only, no config) must not import. Cleanest seam: `parse_document` in `document.py` gains an optional parameter `reference_prefixes: frozenset[str] = frozenset()`. Inside the scan loop (`document.py:83`), the existing `if pfx in NOT_AN_ID: continue` becomes a single `_skip(pfx, digits, tail)` predicate covering all four rows of the table above. Built-in prefix constants (`NOT_AN_ID`, and a new `BUILTIN_REFERENCE_PREFIXES = frozenset({"ADR"})`) stay in `registry.py` as the zero-config floor; the config layer only _adds_ to them.

**A command needs the resolved prefixes only if it runs `validate_document` — i.e. it is a pass/fail gate.** The only such command besides the already-config-aware `validate`/`lint` is `upgrade` (it re-validates both the source and the upgraded output). That is exactly the contradiction SA-001 flagged: a spec that `validate`s clean but cannot `upgrade`. Every `parse_document` call site and its treatment:

| Call site (`cli.py`) | Command | Config today | Change |
| --- | --- | --- | --- |
| `_run_setwide` (:87) | `validate`/`lint` | has `--config` | pass resolved prefixes |
| `_run_new` self-check (:370) | `new` | has `--config` | pass resolved prefixes (generated docs rarely carry refs, but keep it consistent) |
| `_run_upgrade` source + output (:507, :539) | `upgrade` | **none** | add an **opt-in** `--config`; when passed, apply prefixes to **both** the source validation and the output self-validation |
| `_run_extract` (:111) | `extract` | **none** | **no change** — see below |
| `_run_next` (:138) | `next` | **none** | **no change** — see below |
| `collect_existing_spec_ids` (`config.py:96`) | `new` corpus | n/a | **no change** — reads `spec_id` from frontmatter only, never body IDs |

`extract` and `next` are deliberately **not** made config-aware:

- `extract ID` is a raw row selector — `extract_slice` matches `ID_TOKEN.fullmatch(selector)` and searches raw table rows (`commands/extract.py`); it never consults `used_ids`, `declared_prefixes`, or ownership. Passing prefixes would not change its output, and restricting it to reject external selectors would be a real behavior change to a documented core command for no benefit. It stays a pure lookup.
- `next PREFIX` counts `used_ids[PREFIX]` to suggest the next number. It gains **no** `--config` flag and never reads `.project-standards.yml`, so `reference_prefixes` (a per-call param it does not pass) cannot affect it — and a canonical prefix can't be a reference prefix anyway (collision-rejected, Component 1). One honest caveat: `next` _does_ inherit the **unconditional** built-in skips (dot-rule, broadened `NOT_AN_ID`, built-in `ADR`) that apply to _every_ `parse_document` call, because those are not gated on config. So `next FR` on a file containing a version-shaped canonical token like `FR-1.2` may suggest a different number than v4.0.0 did — but that is the _correct_ consequence of no longer miscounting a version string as an `FR` id, and it changes a **suggestion**, never a pass/fail result (Validator-CLI MINOR: "new output that does not change any pass/fail result"). This is intended parser hygiene, not a config surface.

**Opt-in, not default-load (compatibility).** `upgrade`'s new `--config` defaults to **not loading any config** (unlike `validate`/`lint`, which default to `.project-standards.yml` because they were always config-driven to discover specs). This preserves v4.0.0 default behavior exactly: an `upgrade` invocation with no `--config` parses and validates precisely as it does today, so a repo with a missing/malformed `.project-standards.yml` cannot be newly broken. Reference prefixes take effect only when the consumer explicitly passes `--config` — the same flag they already pass to `validate`. This is what keeps the release MINOR under `meta/versioning.md` (see Versioning).

## Component 4 — Error message (F2's misleading chain)

Today an undeclared external prefix fires `SV-ID-UNDECLARED` ("used but not in Appendix A"); the consumer declares it, then hits `SV-ID-TIER`. With the skip set, a _configured_ reference prefix never reaches these checks. But a genuinely-unknown prefix still should, and its message must name the real resolution instead of the dead-end path:

> `[SV-ID-UNDECLARED] prefix RQ- is not a canonical spec-local prefix. If it names an external namespace (backlog, tickets, another spec), add it to spec.reference_prefixes; otherwise declare it in Appendix A with a canonical prefix.`

`SV-ID-TIER` keeps its meaning (a declared prefix used at the wrong tier) but is no longer reachable by mistaking an external reference for a spec-local ID.

**Machine contract:** `--json` serializes each `Finding` via `dataclasses.asdict` (`cli.py:_findings_payload`), so the human `message` string does appear in the payload, but the stable machine key is the `code` (`SV-ID-UNDECLARED`), which is unchanged. Rewording `message` is therefore not a contract break; tests assert on `code` for the machine contract and on the message text only as human-facing output.

## Component 5 — Docs & template (F1)

- **Template (§8.3 row, all copies):** seed the §8.3 Design-Decisions `ADR` column with a real `adr-0001-…` example value, so the column that today invites the wrong uppercase form models the right one. The `ADR` column appears in **both the standard and full templates**, each existing as a byte-identical pair — `src/project_standards/specs/templates/spec-{standard,full}-template.md` (the runtime templates `new`/`upgrade` read) and `standards/project-spec/templates/spec-{standard,full}-template.md` (the published docs copies): **four files**. All must change together; `tests/test_spec_packaging.py::test_bundled_template_is_byte_identical` already enforces the src↔docs parity per tier, so editing only one side of a pair turns CI red — no new parity test is needed, but the plan must edit all four.
- **Standard docs:** in `standards/project-spec/README.md`, document the **namespace split** explicitly — uppercase `PFX-NNN` are mintable, spec-local IDs (Appendix-A-declared, 3-digit); lowercase `adr-…` and any prefix listed in `spec.reference_prefixes` (plus the built-in `ADR`) are external references, exempt from the ID rules. Include a copy-pasteable `.project-standards.yml` snippet:

  ```yaml
  spec:
    include:
      - 'docs/specs/**/*.md'
    reference_prefixes: ['RQ', 'GAP', 'ADR'] # external namespaces this repo cites but does not mint
  ```

  Document the config key, the built-in `ADR`, and the **scoped** license-token handling (common shapes zero-config; exotic SPDX ids like `MIT-0` via `reference_prefixes`) so none of this is discoverable only by reading validator source.

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
- License scope: `MPL-2.0`, `LGPL-2.1`, `CC-BY-4.0`, `GPL-3` are skipped zero-config; `MIT-0`/`NTP-0` are **not** skipped zero-config but **are** skipped when `MIT`/`NTP` is in `reference_prefixes` (proves the documented escape hatch, honest about the scope boundary).
- Message: `SV-ID-UNDECLARED` emits the new text (human output); the finding `code` stays `SV-ID-UNDECLARED` in the `--json` payload (machine contract); `SV-ID-TIER` still fires for a real tier violation.

Integration: a full-profile spec citing `adr-0001-…`, `RQ-123` (configured), `MPL-2.0`, and `GPL-3` `validate`s clean; the same spec with `RQ-123` _not_ configured fails with the reworded `SV-ID-UNDECLARED`. Add a lower-tier fixture with a configured external reference (`RQ-123`, `spec.reference_prefixes: ["RQ"]`) that both `validate`s and `upgrade --config …`s cleanly, including the upgrade output's self-validation.

Compatibility (guards SA-NEW-001): `upgrade` **without** `--config` behaves exactly as v4.0.0 — assert it neither reads nor fails on a missing/malformed `.project-standards.yml`. `extract` and `next` gain no flag and never read config — assert that (they ignore even a malformed `.project-standards.yml`). Separately, add a parser-behavior test documenting the _intended_ effect of the global skips on a canonical-prefix version token: a fixture with `FR-1.2` shows `next FR` no longer counts it (a deliberate suggestion change, not a pass/fail change).

## Acceptance criteria

- The issue's minimal repro (`spec validate` over a spec citing an ADR, an external ID, and a license id) exits 0 with the documented config.
- A lower-tier spec containing a configured external reference (`RQ-123`, `spec.reference_prefixes: ["RQ"]`) both `validate`s and `upgrade --config …`s cleanly (source + output self-validation).
- Backward compatibility: `upgrade` with no `--config`, and `extract`/`next`, never read `.project-standards.yml` (even a malformed one cannot break them). The one intended, documented behavior change is that the global token-hygiene skips stop `next`/`validate` from miscounting version/SPDX-shaped false positives (e.g. `FR-1.2`) — a suggestion/loosening change, never a previously-passing → failing change.
- `uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit` all green; branch coverage stays at or above the configured `fail_under = 85` threshold (measurable via `coverage report`; not a baseline-delta claim).
- `uv run validate-frontmatter --config .project-standards.yml` and `spec validate` (dogfood) both pass.

## Non-goals

- No code-span / fenced-code exclusion from the scan. Scanning raw body text is a deliberate anti-evasion property — backticking an ID must not hide it from validation.
- No in-document Appendix-A reference marker (config is the chosen mechanism).
- No per-prefix width configuration (F3 is subsumed by skipping references).
- F5 (markdown-tooling formatter authority) — separate spec.

## Versioning & docs impact

A backward-compatible **loosening** that maps to the MINOR column of `meta/versioning.md`'s Validator-CLI row on every axis:

- `spec.reference_prefixes` is "a new config option with a backward-compatible default" (`[]` — a spec with no external refs is unaffected; a spec that previously _failed_ now passes, which is loosening, never a new failure).
- The token-hygiene changes (built-in `ADR`, dot-rule, broadened `NOT_AN_ID`) only ever make a previously-failing token pass — they cannot turn a passing document into a failure.
- `upgrade`'s `--config` is "a new opt-in flag." Because it defaults to _not loading_ config, no existing invocation changes outcome, so it does **not** trip the MAJOR "a default changed so pass/fail differs" clause or the previously-passing rule.

That is a **minor bump, v4.0.0 → v4.1.0**. The release must update `CHANGELOG.md` ([4.1.0] with the new config key, the opt-in `upgrade --config`, and the token-hygiene behavior), the `standards/project-spec/README.md` namespace-split docs + config example, and the §8.3 example row in **both** `spec-full-template.md` copies. Downstream `@v4` pins pick it up automatically via the moving `v4` tag.
