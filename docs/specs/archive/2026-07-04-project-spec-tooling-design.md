# Design: `project-standards spec` tooling — Spec #1 (registry core + read-only commands)

**Date:** 2026-07-04 **Status:** approved (brainstorming complete; awaiting plan) **Author:** session 2026-07-04

## Table of Contents

- [Design: `project-standards spec` tooling — Spec #1 (registry core + read-only commands)](#design-project-standards-spec-tooling--spec-1-registry-core--read-only-commands)
  - [Table of Contents](#table-of-contents)
  - [Problem / Goal](#problem--goal)
  - [Scope decomposition (two specs)](#scope-decomposition-two-specs)
  - [Decisions (locked during brainstorming)](#decisions-locked-during-brainstorming)
  - [Invariants — the consumer contract (must NOT change)](#invariants--the-consumer-contract-must-not-change)
  - [Component 1 — Module layout](#component-1--module-layout)
  - [Component 2 — The shared registry core](#component-2--the-shared-registry-core)
  - [Component 3 — `check_specs.py` retirement](#component-3--check_specspy-retirement)
  - [Component 4 — The four commands](#component-4--the-four-commands)
    - [`--json` output contract](#--json-output-contract)
  - [Component 5 — Config surface \& discovery](#component-5--config-surface--discovery)
  - [Component 6 — CI reusable workflow](#component-6--ci-reusable-workflow)
  - [Component 7 — Error handling](#component-7--error-handling)
  - [Component 8 — Testing](#component-8--testing)
  - [Acceptance criteria](#acceptance-criteria)
  - [Non-goals](#non-goals)
  - [Versioning \& docs impact](#versioning--docs-impact)
  - [Open implementation questions (for the plan, not blockers)](#open-implementation-questions-for-the-plan-not-blockers)

## Problem / Goal

The `project-spec` standard (5th standard, in-development draft) ships three tiered templates, a canonical section/ID/appendix registry, and a documented tooling contract in its [README §5](../../../standards/project-spec/README.md). That contract is prose today — no code operates on a consumer's real specs. Until the tooling exists, the README's §6 Adoption is deliberately parked ("adoption == run the tool," and the tool does not exist yet).

The goal is to build that tooling so a consumer (human or coding agent) can mechanically validate, lint, slice, and assign IDs against real specifications — delivering guarantees G2–G5 and G7 from the standard's Features list. The tool must be agent/CI-safe (no prompts, deterministic exit codes, `--json`), profile-agnostic (one code path for Light/Standard/Full via the canonical registry), and read-only in this first spec.

At design time, the only code over the templates was the since-retired `standards/project-spec/resources/check_specs.py` maintainer script, which validated the three templates against **each other**. The consumer tooling needed the same registry logic pointed at the **opposite subject** (a consumer's own specs). Building it right meant extracting that logic into a shared core rather than growing a second, drift-prone parser.

## Scope decomposition (two specs)

The v1-core capability set splits along a read/write seam:

- **Spec #1 (this doc)** — the shared registry core + the four **read-only** commands: `validate`, `lint`, `extract`, `next`. All are pure readers over the registry; `validate` is the gate the others and CI depend on. Ships verifiable value first.
- **Spec #2 (future)** — the **guarded-generative** authors `new` and `upgrade`, which additionally need raw template text and **mutate files** (a different risk profile). They build on the proven core from Spec #1.

`status` (a reporting rollup) and the **semantic-review contract** (a standard-defined checklist/prompt, not a binary command — it is documentation, not code) remain deferred exactly as README §5 marks them.

## Decisions (locked during brainstorming)

1. **Placement + CLI shape = a `specs/` subpackage exposed as a nested `project-standards spec <verb>` group.** New code lives under `src/project_standards/specs/`; commands surface as `project-standards spec validate|lint|extract|next`, dispatched from the existing `cli.py` with the same early-dispatch pattern used for `validate`/`fix`. Ships in the existing wheel — no second package. Matches README §5's "subcommand group" language.
2. **Registry sourcing = parse the bundled template at runtime; single source of truth.** A shared parser (factored out of `check_specs.py`) reads the bundled `spec-full-template.md` to build the canonical registry model. No generated data file, no hardcoded Python duplicate. This is cheap and non-duplicative **because the templates must ship in the wheel regardless** — Spec #2's `new`/`upgrade` need the raw template text, so the registry rides along for free.
3. **`check_specs.py` is retired, not slimmed.** Its per-file checks are re-expressed as **maintainer-mode tests over the shared core** (which expect the template sentinel/placeholders — not a consumer `validate` run); its one genuinely cross-file assertion moves into the pytest gate. See [Component 3](#component-3--check_specspy-retirement).
4. **Spec discovery = a dedicated `spec:` block in `.project-standards.yml` + explicit path args.** Kept schema-separate from the frontmatter validator's `markdown.frontmatter.include/exclude` config, because spec files are deliberately excluded from the canonical frontmatter validator (README §2). See [Component 5](#component-5--config-surface--discovery).
5. **This spec is read-only.** No command writes to a consumer's tree. (`--json` and stdout only.)

## Invariants — the consumer contract (must NOT change)

- **Exit codes** follow the repo convention: `0` ok · `1` findings · `2` bad invocation. `validate` uses all three; `extract` adds `1` = no match; `next` uses `0`/`2`.
- **One registry, one rule-set.** Conformance is defined by exactly one canonical registry, derived from `spec-full-template.md`. This prohibits a _second extraction of the registry rules_ (the drift `check_specs.py` retirement eliminates) — it does **not** forbid the two distinct parsers the design needs: `registry.py` (parse the canonical template → rules) and `document.py` (parse a consumer spec → the thing under test).
- **Profile-agnostic.** A single code path validates all three tiers by keying on canonical **number**, never document position, and allowing annotated gaps.
- **`--json` on every command** for tool-to-tool consumption.
- **Never a traceback on bad input.** Malformed/non-UTF-8 specs produce a located `exit 1`/`2` message, never a stack trace.

## Component 1 — Module layout

```text
src/project_standards/
├── cli.py                    # + early-dispatch a `spec` group (same pattern as `validate`/`fix`)
└── specs/
    ├── __init__.py
    ├── registry.py           # THE core: parse bundled full template → canonical Registry
    ├── model.py              # frozen dataclasses: Registry, SectionEntry, PrefixEntry, TableShape…
    ├── document.py           # parse a CONSUMER spec: frontmatter + headings + IDs + refs
    ├── config.py             # read the `spec:` block from .project-standards.yml
    ├── cli.py                # `spec` subparser → validate|lint|extract|next dispatch
    ├── commands/
    │   ├── __init__.py
    │   ├── validate.py       # deterministic gate → exit 0/1/2
    │   ├── lint.py           # advisory → warns, exit 0 (--strict promotes to 1)
    │   ├── extract.py        # slice by ID / §N / heading / appendix → md or --json
    │   └── next_id.py        # next free ID for a prefix
    └── templates/            # byte-identical copies of the 3 canonical templates (ship in wheel)
        ├── spec-full-template.md
        ├── spec-standard-template.md
        └── spec-light-template.md
```

**Core isolation boundary:** `registry.py` parses the _canonical template_ → the rules; `document.py` parses a _consumer spec_ → the thing under test. `validate` is then "does this `document` conform to this `registry`?" Each half is testable without the other, and every command reuses both.

**Wheel packaging:** `templates/` under `src/` is what makes the tool self-contained in an installed wheel, resolved by the same `Path(__file__)`-relative lookup the bundled schema and adopt bundles already use. A byte-identical dogfood test (the adopt-bundle idiom) keeps those copies honest against `standards/project-spec/templates/`. **Mechanism decided: a straight copy under `src/`** — the [uv build backend](https://docs.astral.sh/uv/concepts/build-backend/) includes the module tree by default (no bespoke wheel-include config), so data placed under `src/project_standards/specs/templates/` ships automatically, matching how the adopt bundles already work. (An implementation-time wheel-build check confirms inclusion; see acceptance criteria.)

## Component 2 — The shared registry core

Extract the parsing primitives `check_specs.py` already has — `gh_slug`, `split_front_matter`, `headings`, `section_numbers`, `numkey`, the `ID_TOKEN` regex + `NOT_AN_ID` denylist — into `specs/registry.py` and `specs/document.py`.

`registry.py` builds the canonical `Registry` model once from `templates/spec-full-template.md`:

- the canonical section-number set (top-level + subsections) and their titles;
- the appendix scheme (A/B/D required, C Full-only);
- the ID-prefix → "Defined In" § map (parsed from Appendix A);
- per-table column counts (the table-shape guarantee);
- the frontmatter key-set and order, and the `SPEC-____` sentinel;
- the tier subset maps — which § / prefixes each profile legitimately presents (so gaps are validated as _intentional_).

`document.py` parses a consumer spec into a comparable shape: frontmatter block + keys, headings → `{number → (title, line, slug)}`, used IDs (per prefix), and the §/anchor references. `validate` diffs `document` against `registry`.

## Component 3 — `check_specs.py` retirement

Categorizing `check_specs.py`'s eight checks: **seven are per-file** (frontmatter key-set/profile/**required-sentinel**; sections ⊆ canonical + ascending + gap annotation; appendix lettering; §/anchor resolution; ID format; Appendix-A used ⊆ declared + Defined-In resolvable; table column consistency). **One is cross-file**: that a shared prefix's "Defined In" § is identical across all three tiers (`main()` L275–282), the G2/G3 interchangeability guarantee no single-file pass can see.

**Why this is not a plain `spec validate` run.** `check_specs.py` _requires_ the `SPEC-____` sentinel to be present (L142) — the opposite of what consumer `validate` demands (it _rejects_ the sentinel, per G7). So the per-file checks map onto the shared registry/document core, but exercised in a **maintainer mode** that expects the sentinel and the template's `<angle-bracket>` placeholders, not onto the consumer `validate` command. Same parser, opposite frontmatter contract.

Therefore:

- **Delete** `standards/project-spec/resources/check_specs.py`.
- **Per-file half → a maintainer dogfood test** (`tests/test_template_conformance.py`) that drives the shared `registry.py` + `document.py` core over the three bundled templates in maintainer mode — asserting structural conformance (numbering, gaps, appendices, refs, ID format, table shape) **while expecting** the intentional sentinel/placeholders. Proves the templates the tool _ships_ are structurally sound without contradicting G7.
- **Cross-file half → a maintainer test** `tests/test_template_interchangeability.py` (~30 lines) asserting the cross-tier Defined-In identity using the shared `registry.py` parser.
- **Reconcile the two never-enforced guarantees.** `tooling-notes.md` §8 lists "shared example IDs identical" (#4) and "shared boilerplate identical" (#5) as things "tooling may rely on," but `check_specs.py` never enforced them. To avoid docs promising more than tests check, **demote** those two lines in §8 to "documented convention, not currently machine-checked" (in scope; no new enforcement added). Adding tests for them is explicitly deferred as out of scope for Spec #1.
- **Update references** to `check_specs.py` in README §8/§9 and `resources/tooling-notes.md` §11 to point at `spec validate` (consumer) + the two maintainer tests.

## Component 4 — The four commands

All share `registry.py` + `document.py` and offer `--json`.

| Command | Behavior | Exit codes | Selection | Guarantees |
| --- | --- | --- | --- | --- |
| **`validate`** | Deterministic gate — every **integrity** property: registry conformance (numbering subset, annotated gaps, appendix lettering), §/anchor resolution, frontmatter key-set/enum, **`spec_id` validity** (the `SPEC-____` sentinel _and_ any value not matching `^SPEC-[0-9A-Z]{4}$` both fail, per G7), **ID format**, **per-spec ID uniqueness**, **`used ⊆ declared`** prefixes, **Appendix-A "Defined In" resolves**, and table shape. The hard contract CI relies on. | `0` all pass · `1` any violation · `2` bad args/config | set-wide | G2, G3, G4, G7 |
| **`lint`** | Advisory **authoring-quality** on a spec that already passes `validate`: leftover `<angle-bracket>` placeholders and un-deleted template-guidance blockquotes; status-aware traceability (an `approved` **Standard/Full** spec must map every `Must` in §17.3 — see Light note below). Warns, never fails a draft. | `0` always · `--strict` promotes warnings to `1` | set-wide | G5 |
| **`extract`** | Print one slice as Markdown or `--json`: an ID row (`FR-013`), a section (`§7` / `§7.1`), a heading match, or an appendix. The context-window optimizer. | `0` found · `1` no match · `2` bad args | single-spec (required FILE) | G2, G4 |
| **`next`** | Print the next free ID for a prefix (`FR` → `FR-013`), registry-aware of format rules (3 digits; `MS` single digit). | `0` ok · `2` unknown/tier-invalid prefix / bad args | single-spec (required FILE) | G4 |

**Integrity vs. authoring quality — the hard/soft line.** Anything that makes a spec's IDs, references, or metadata _unsound_ (a duplicate `FR-001`, an undeclared `ZZ-` prefix, an unfilled `SPEC-____`, a dead `§`) is an **integrity** failure and lives in `validate` (hard, exit 1) — otherwise a CI job running only `spec validate` would let G4/G7 violations through. `lint` is reserved for **authoring polish** that a legitimate in-progress _draft_ may still have (unfilled `<angle-bracket>` tokens, template guidance not yet deleted, an `approved` spec whose traceability matrix is incomplete). This deliberately reallocates two items the README §5 draft had placed under `lint` (ID uniqueness + `used ⊆ declared`, and sentinel detection) into `validate`; see [Versioning & docs impact](#versioning--docs-impact) for the README §5 reconciliation this obligates.

**Light-profile traceability (`lint`).** Light omits §17.3, so the "map every `Must`" matrix check applies only to profiles that carry §17.3 (Standard/Full). For an `approved` **Light** spec, `lint` instead flags unchecked §17.1 (Definition of Done) items. A profile without §17.3 is never failed for lacking the matrix.

**Consumer `validate` vs. template-maintainer validation.** A canonical template is, by design, **not** a valid consumer spec: it carries the intentional `SPEC-____` sentinel (and `<angle-bracket>` placeholders) precisely so consumer `validate` **rejects** an unfilled spec (G7). Therefore the "prove the shipped templates are sound" check is **not** a `spec validate` invocation — it is a maintainer-mode assertion (see [Component 3](#component-3--check_specspy-retirement)) that checks structural conformance while _expecting_ the sentinel. The two are separate contracts over the same registry.

**Selection asymmetry.** `validate`/`lint` are set-wide (fall back to the `spec:` config globs when no path is given); `extract`/`next` operate on one spec (required FILE positional). This is an explicit part of the argparse contract.

### `--json` output contract

`--json` is part of the consumer contract, so its shape is fixed here (not deferred) — downstream agents/CI depend on stable fields.

**`validate` / `lint`** emit an array of per-file results:

```json
[
	{
		"file": "docs/specs/foo.md",
		"ok": false,
		"findings": [
			{
				"code": "SV-DUP-ID",
				"severity": "error",
				"line": 142,
				"locus": "FR-001",
				"message": "duplicate id FR-001"
			}
		]
	}
]
```

`code` is a stable string from a fixed namespace — `SV-*` for `validate` (severity `error`), `SL-*` for `lint` (severity `warning`). `locus` is the ID/§/appendix the finding attaches to (nullable). `line` is 1-based (nullable when file-level). The finding record is shared across both commands.

**`extract`** emits `{ "file", "selector", "kind": "id|section|heading|appendix", "found": true, "markdown": "…" }` — `found:false` with `markdown:null` on no match (still exit `1`). **`next`** emits `{ "file", "prefix": "FR", "next_id": "FR-013" }`.

The finding record (`code`/`severity`/`line`/`locus`/`message`) is shared across `validate` and `lint`. The exact per-check `code` strings are enumerated in the implementation plan, not here; the _shape_ is frozen.

## Component 5 — Config surface & discovery

`.project-standards.yml` gains a **`spec:` block**, read by `specs/config.py`:

```yaml
spec:
  include:
    - docs/specs/**/*.md
  exclude: [] # optional
```

The block is a **separate top-level key** from the frontmatter validator's `markdown.frontmatter.include/exclude` config, honoring the standard's schema-separation (spec files are excluded from the canonical frontmatter validator — README §2). It is additive: `validate_frontmatter.load_config` reads only the `markdown.frontmatter.*` subtree, so an added `spec:` key does not affect existing validators. Adopting `project-spec` (Spec #2 / adoption work) will write a starter `spec:` block; this spec only _reads_ it.

**Discovery & no-arg behavior (must not pass vacuously).** A green CI run that validated _zero_ specs is worse than no run — it manufactures false confidence. So discovery resolves as:

| Invocation | Resolution | Result |
| --- | --- | --- |
| Explicit path/glob args | Validate exactly those; **bypass** config discovery | normal `0/1` |
| No args, `spec:` present, ≥1 file matches | Validate the resolved include set (minus `exclude`) | normal `0/1` |
| No args, `spec:` **missing** | No discovery source | **exit `2`** — "no `spec:` config and no paths given" |
| No args, `spec:` present but 0 files match (empty include, unmatched glob, or excludes remove all) | Nothing to check | **exit `2`** — "spec discovery matched no files" |

Exit `2` (not `1`) because an empty target is a _configuration/invocation_ error, not a spec violation — and it makes the reusable `validate-specs.yml` unable to pass without actually checking specs.

## Component 6 — CI reusable workflow

**In scope for Spec #1 (decided).** A reusable `validate-specs.yml` (`workflow_call`), mirroring the existing `validate` workflow: check out, install the package, run `project-standards spec validate` (and optionally `spec lint --strict`). A thin wrapper that completes the end-to-end "how deployed" story and makes the foundation usable in CI the moment it lands.

## Component 7 — Error handling

The whole `spec` dispatch sits inside an error boundary like today's `cli.py`:

- config / arg errors → clean `exit 2` on stderr;
- a malformed or non-UTF-8 spec → graceful `exit 1` with a located message, **never a traceback** (the existing frontmatter validators carry latent traceback-on-bad-input bugs noted in `TODO.md`; we do not repeat that pattern);
- a corrupt _bundled_ template (registry parse failure) → `exit 2` internal error with a clear message.

## Component 8 — Testing

TDD, held to the repo gate (100% coverage, basedpyright strict, ruff, pytest):

- **`registry.py`** — parse the bundled full template; assert known invariants (canonical section count, the prefix→§ map, appendix scheme, table shapes, frontmatter key-set).
- **`validate` integrity fixtures** — one valid _consumer_ spec per tier (a real `spec_id` like `SPEC-7F3Q`, no placeholders) exits `0`; invalid specs each violating exactly one rule exit `1` with the specific located finding: unfilled `SPEC-____` sentinel, malformed real `spec_id` (`SPEC-123`, `SPEC-12_4`, `foo`), duplicate `FR-001`, undeclared prefix `ZZ-001`, prefix with wrong Appendix-A "Defined In", a prefix used in a tier that disallows it, unannotated gap, dead `§`/anchor, malformed ID, renamed frontmatter key, table column mismatch.
- **`lint` fixtures** — a draft with `<angle-bracket>` placeholders / un-deleted guidance warns at exit `0`, `--strict` → `1`; an `approved` Standard/Full spec missing a `Must` mapping warns; an `approved` **Light** spec is not failed for lacking §17.3 but is flagged for unchecked §17.1 items.
- **`extract` / `next`** — slice-by-ID / §N / heading / appendix (incl. no-match → exit `1`); next-ID assignment including the `MS` single-digit special case and a prefix with no existing IDs (`→ FR-001`).
- **Discovery fixtures** — explicit paths bypass config; missing `spec:` → exit `2`; empty include, unmatched glob, and excludes-remove-all each → exit `2` with a clear message.
- **`--json` golden-output tests** — stable fields for `validate`/`lint` findings, `extract` (found + no-match), and `next`.
- **Maintainer template-conformance test** — drives the shared core over the three bundled templates in maintainer mode (expects the sentinel/placeholders); proves what we ship is structurally sound.
- **Interchangeability test** — the cross-tier "Defined In identical" assertion ported from `check_specs.py`.

## Acceptance criteria

- `project-standards spec validate|lint|extract|next` exist, each with `--json` matching the frozen output contract and the exit codes above.
- `validate` **rejects** an unfilled `SPEC-____` spec _and_ a malformed real `spec_id` (`SPEC-123`, `foo`) (exit `1`), and passes a valid consumer fixture per tier (`SPEC-7F3Q`); it fails with a precise, located finding on each single-rule-violation fixture (duplicate ID, undeclared prefix, wrong Defined-In, tier-invalid prefix, unannotated gap, dead anchor, malformed ID, bad frontmatter key, table mismatch).
- `lint` warns (exit `0`) on a draft with `<angle-bracket>`/guidance placeholders; `--strict` returns `1`; Light-profile traceability behaves per the Light note (no matrix-absence failure).
- Discovery cannot pass vacuously: missing `spec:` and zero-match include sets exit `2`; explicit paths bypass config.
- `extract` returns the requested ID row / section / appendix (md and `--json`); `1` on no match.
- `next` returns the correct next ID per prefix, honoring format rules.
- `check_specs.py` is deleted; the maintainer template-conformance + interchangeability tests replace it; `tooling-notes.md` §8 guarantees #4/#5 demoted; README §8/§9 and `tooling-notes.md` §11 references updated.
- One canonical rule-set (`specs/registry.py`); no re-extraction of registry rules remains.
- A reusable `validate-specs.yml` (`workflow_call`) runs `spec validate` in CI.
- A built wheel contains `project_standards/specs/templates/*.md`.
- The full repo gate is green.

## Non-goals

- **`new` / `upgrade`** (guarded-generative authors) — Spec #2.
- **`status`** rollup and the **semantic-review contract** — deferred per README §5.
- **Writing to consumer specs** — this spec is read-only.
- **Adoption wiring** (an `adopt.toml` bundle for `project-spec`, writing the starter `spec:` block) — adoption work, unblocked _by_ this spec, not part of it.
- **Governing spec prose quality** — the semantic layer (G8), not a deterministic command.

## Versioning & docs impact

- New CLI surface (`spec` group) + a new `.project-standards.yml` `spec:` key = an **additive, minor** change to the package's consumer contract. No existing behavior changes.
- **README §5 reconciliation (obligated by this design).** The README §5 draft describes `lint` as covering ID uniqueness, `used ⊆ declared`, and leftover-sentinel detection. This design moves those **integrity** checks into `validate` (per G4/G7 — see [Component 4](#component-4--the-four-commands)). README §5's `validate`/`lint` capability descriptions must be updated to match when this ships; `lint` retains `<angle-bracket>`/guidance placeholders and traceability. This is a docs-plane correction of a draft standard, not a consumer-breaking change.
- Retiring `check_specs.py` changes the documented maintainer workflow (README §8/§9, `tooling-notes.md` §11) and demotes `tooling-notes.md` §8 guarantees #4/#5 to "documented, not machine-checked" — docs-plane updates, no consumer impact.
- `project-spec` remains an **unregistered, in-development** standard (excluded from validation/adopt); shipping its tooling does not register it. Registration + README §6 Adoption follow once Spec #2 and adoption wiring land.
- A CHANGELOG line is owed once this ships (tracked alongside the existing pending CHANGELOG note in `TODO.md`).

## Open implementation questions (for the plan, not blockers)

1. **Per-check `code` strings** — enumerate the stable `SV-*` / `SL-*` finding codes in the plan (the `--json` record _shape_ is frozen in [Component 4](#component-4--the-four-commands); only the specific code spellings remain to be listed).
2. **`extract` selector disambiguation** — behavior on a partial/duplicate heading match or an ambiguous selector (error vs. first-match); settle in the plan.
3. **`validate-specs.yml` inputs** — which `workflow_call` inputs to expose (`config-path`, whether `--strict` lint is an opt-in input); mirror the existing `validate` workflow's input surface.
