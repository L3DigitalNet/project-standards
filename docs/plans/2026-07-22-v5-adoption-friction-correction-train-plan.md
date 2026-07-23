---
title: 'V5 Adoption Friction Correction Train Implementation Plan'
slug: 'v5-adoption-friction-correction-train'
size: full
status: complete # active | complete  (coarse lifecycle only; live progress lives in the per-phase checklists)
source: 'GitHub issues #26-#31 against Project Standards 5.7.0'
spec_ref: 'docs/specs/2026-07-22-v5-adoption-friction-correction-train-design.md'
created: 2026-07-22
updated: 2026-07-23
owners:
  - 'Claude (Fable 5) with Chris Purcell / L3DigitalNet'
test_framework: pytest
---

# V5 Adoption Friction Correction Train Implementation Plan

> **This file is definition, not state.** Committed to `docs/plans/2026-07-22-{slug}-plan.md`, read-only during implementation except at two checkpoints: (1) inserting discovered work as a new task, followed by `plan.py sync`; (2) close-out harvest. Live progress lives in per-phase checklists under `.project-pipeline/2026-07-22-{slug}/` (`p1.md`, `p2.md`, ...), not here. A session working one phase opens only that phase's checklist.

## 1. Objective

Ship Project Standards 5.8.0 resolving GitHub issues #26–#31: python-tooling 1.8 with declarable pytest collection roots, markdown-tooling 1.8 accepting the proven legacy markdownlint byte form, markdown-frontmatter 1.5 with a `workflow_ownership` relinquishment escape, an acceptance-widening minimal-escape frontmatter serializer that reaches a fixed point with the pinned Prettier, `format-frontmatter` skip diagnostics, a factual legacy-authority note, and a self-diagnosable whole-file conflict pointer — with no previously-passing consumer outcome turning into a failure.

## 2. Background

The governing specification is `docs/specs/2026-07-22-v5-adoption-friction-correction-train-design.md` (codex adversarial review, four rounds, final verdict `ready`). It records the investigation evidence: `testpaths` is hardcoded with no governing option; the blocked consumer `.markdownlint.json` (digest `4c1c089d…`) is a consumer-side re-serialization no release ever shipped; the quote fight enters only through double-quoted/unquoted input because single-quoted input already bypasses the emitter; the payload model forbids combining `consumer_owned_intent_pointer` with `unknown_content_disposition`; and the previously-passing rule makes any pass-to-fail change MAJOR, which this MINOR train must not contain.

## 3. Scope

### 3.1 In Scope

- The spec's in-scope list: three successor payloads (python-tooling 1.8, markdown-tooling 1.8, markdown-frontmatter 1.5), four engine corrections (serializer, CLI hardening, legacy note, conflict pointer), Catalog 5 default advancement with full predecessor retention, documentation, and the 5.8.0 release preparation.

### 3.2 Out of Scope

- The spec's out-of-scope list verbatim — most critically: no released payload byte changes, no Prettier configuration changes, no parsed-JSON comparison mode, no automatic consumer-job retirement, no new dependencies or test frameworks.
- Publishing tags/releases without explicit owner authorization (T13 is gated on it).

### 3.3 Assumptions

- The repository working tree equals released 5.7.0 for `src/` (verified during spec authoring); if false, re-baseline before P1.
- The pinned Prettier (repo `package-lock.json`, currently 3.8.x) normalizes YAML frontmatter quotes as observed in issue #26; the T3 oracle corpus verifies this empirically and is authoritative on divergence.

### 3.4 Constraints

- Dogfood runtime: the full suite and any dogfood/adopt/legacy test requires the extracted candidate wheel first on `PYTHONPATH` (`uv build --wheel`, extract to `build/{runtime}`, then `PYTHONPATH=$PWD/build/{runtime} uv run pytest`); rebuild the runtime after every engine or payload change before running those suites. Coverage under that runtime uses `--source=project_standards`, not the pyproject `src` path.
- Never run two `uv run` pytest suites concurrently; never edit docs or `.standards/` while a suite runs.
- Payload wiring order (per `docs/handoff/conventions.md` and prior trains): edit canonical `standards/{family}/versions/{new}/` copy → per-resource digests in `payload.toml` → aggregate via `package_contract.integrity.validate_payload_integrity` → `[[versions]]` in family `standard.toml` → `[[packages]]` in `catalogs/5.toml` → `sync-payload-projection` → regenerate `standards/catalog.md`.
- Released payload bytes are immutable; new payloads are full immutable copies; catalog retains every predecessor.
- Markdown gates (Prettier + markdownlint) and the frontmatter gate must stay green on every commit; `uv run project-standards validate` must pass with the candidate runtime.
- Commit at Verify Task on `testing`; message format `T{n}: {summary} ({FR ids}, {TC ids})`.

## 4. Source Requirements

| ID | Requirement (abbreviated — spec text is authoritative) | Source | Priority | Task(s) |
| --- | --- | --- | --- | --- |
| FR-001 | python-tooling 1.8 `pytest.test_paths` option renders managed `testpaths` | spec_ref | must | T7 |
| FR-002 | Collection roots feed checker include, Ruff src, pytestArgs; overlap semantics pinned | spec_ref | must | T7 |
| FR-003 | `/pytest/test_paths` governance on all four affected contributions | spec_ref | must | T7 |
| FR-004 | Byte-identical defaults; schema rejection; migration carriage without invention | spec_ref | must | T7 |
| FR-005 | markdown-tooling 1.8 accepts literal-form digest in `legacy-markdownlint-config` | spec_ref | must | T8 |
| FR-006 | markdown-frontmatter 1.5 `workflow_ownership` with intent-pointer relinquishment branch | spec_ref | must | T9 |
| FR-007 | Ownership-escape documentation and full claim-matrix verification | spec_ref | must | T9, T11 |
| FR-008 | Minimal-escape emission with acceptance preservation for scalars and block-list items | spec_ref | must | T1, T2 |
| FR-009 | Mutual fixed point with pinned Prettier over the full corpus; oracle authoritative | spec_ref | must | T3 |
| FR-010 | Help states default mode; named-file skip diagnostics; mode-resolution unit | spec_ref | must | T4 |
| FR-011 | Factual legacy-authority note; all three call-site routes tested | spec_ref | must | T5 |
| FR-012 | Whole-file conflict first-difference pointer, expected-side content only | spec_ref | must | T6 |
| FR-013 | Catalog 5 retains predecessors and advances the three defaults | spec_ref | must | T10 |
| FR-014 | Adoption guides, UPGRADING.md, and serialization documentation updated | spec_ref | must | T7, T8, T9, T11 |
| FR-015 | 5.8.0 built once, candidate-verified, published from main with signed tags and assets | spec_ref | must | T12, T13 |
| FR-016 | Issues #26–#31 close only after publication evidence; #29 records non-reproduction | spec_ref | must | T13 |
| FR-017 | CHANGELOG entries under Unreleased, converted in the release commit | spec_ref | must | T11, T12 |
| NFR-001 | No released bytes/tags/selections change; no exact-version pass-to-fail; uniform widening | spec_ref | must | T7, T8, T9, T12 |
| NFR-002 | Closed options; unknown values fail closed; unknown caller without intent stays blocked | spec_ref | must | T7, T9 |
| NFR-003 | RED before GREEN (except designated equivalence refactors); fresh release evidence | spec_ref | must | T12 |
| NFR-004 | Previously-passing rule holds; MINOR classification; additive shifts documented | spec_ref | must | T12 |

## 5. Repository and Architecture Context

### 5.1 Relevant Components

| Component | Purpose | Paths |
| --- | --- | --- |
| Frontmatter formatter | Scalar/list serialization, CLI | `src/project_standards/format_frontmatter.py` |
| Path collection | include/exclude/explicit-file resolution | `src/project_standards/validate_frontmatter.py` |
| Command resolution | Legacy-authority note, state resolution | `src/project_standards/control_plane/command_resolution.py` |
| Conflict rendering | CP-CONSUMER-CONFLICT findings | `src/project_standards/control_plane/planner.py`, `control_plane/cli.py`, `control_plane/diagnostics.py` |
| Migration engine | Claims, relinquishment, legacy signatures | `src/project_standards/control_plane/migration.py` |
| python-tooling family | Payload 1.7 → 1.8 | `standards/python-tooling/` |
| markdown-tooling family | Payload 1.7 → 1.8 | `standards/markdown-tooling/` |
| markdown-frontmatter family | Payload 1.4 → 1.5 | `standards/markdown-frontmatter/` |
| Catalog and projections | Version advertisement, defaults, symlinks | `catalogs/5.toml`, `src/project_standards/payloads/`, `standards/catalog.md` |

### 5.2 Existing Behavior

See spec §Evidence. Load-bearing specifics: `_emit_single_quoted` (`format_frontmatter.py:157-159`) and its call sites; the single-quoted verbatim bypass (`:243`); `normalize_lists` decode-and-rebuild (`:308-358`); silent named-file exclusion drop (`validate_frontmatter.py:485`); `emit_legacy_authority_warning` one function/three call sites; `_pytest_key` hardcoded `testpaths` and `_source_roots` hardcoded `tests` (`python_tooling.py:82-99,192-203`) plus `pytestArgs` (`:447`); mutual exclusion of intent pointer and preserve disposition (`package_contract/payload.py:645-650`); relinquishment gate (`migration.py:1185-1209`).

### 5.3 Files Expected to Change

| Path | Action | Purpose | Owning task |
| --- | --- | --- | --- |
| `src/project_standards/format_frontmatter.py` | modify | Minimal-escape emitter, list preservation, CLI | T1, T2, T4 |
| `src/project_standards/validate_frontmatter.py` | modify | Named-file skip diagnostics | T4 |
| `src/project_standards/control_plane/command_resolution.py` | modify | Factual legacy-authority note | T5 |
| `src/project_standards/control_plane/planner.py` + `cli.py` + `diagnostics.py` | modify | First-difference pointer | T6 |
| `standards/python-tooling/versions/1.8/**` | create | Successor payload | T7 |
| `standards/markdown-tooling/versions/1.8/**` | create | Successor payload | T8 |
| `standards/markdown-frontmatter/versions/1.5/**` | create | Successor payload | T9 |
| `standards/*/standard.toml`, `catalogs/5.toml`, `src/project_standards/payloads/**`, `src/project_standards/catalogs/5.toml`, `standards/catalog.md`, family `README.md`/`agent-summary.md` | modify | Version advertisement and defaults | T7, T8, T9, T10 |
| `tests/**` (new regressions, reconstruction, activation constants) | create/modify | Proofs per task | T1–T10 |
| `tests/fixtures/observed_consumers/**` | create | Literal-form markdownlint bytes + provenance | T8 |
| `UPGRADING.md`, `docs/usage.md`, `CHANGELOG.md` | modify | FR-014/FR-017 documentation | T11 |
| `pyproject.toml`, `CHANGELOG.md` (release conversion) | modify | 5.8.0 release preparation | T12 |

### 5.4 Dependencies

| Dependency | Type | Version / constraint | Reason |
| --- | --- | --- | --- |
| Prettier (via `npm ci`) | dev | pinned by `package-lock.json` | FR-009 oracle tests |
| No new runtime/test deps | runtime | n/a | Spec out-of-scope list |

## 6. Test Strategy

- **Framework:** pytest, run through uv. Config: `pyproject.toml` · Test root: `tests/` · Shared fixtures: `tests/conftest.py`, `tests/fixtures/`.
- **Commands:** (permanent reference palette — the `{…}` slots are filled per run, not at authoring)
  - Targeted: `uv run pytest {path}::{test}` · File: `uv run pytest {path}` · Subset: `uv run pytest {path} -k "{expr}"`
  - Dogfood/full (candidate runtime): `PYTHONPATH=$PWD/build/{runtime} uv run pytest`
  - Lint / format / types: `uv run ruff check .` · `uv run ruff format --check .` · `uv run basedpyright`
  - Markdown gates: `npx prettier --check .` · `npx markdownlint-cli2`
- **Coverage is a diagnostic, not a gate.** `uv run coverage run --source=project_standards -m pytest` under the candidate runtime locates untested paths. Acceptance is the Test Cases (Appendix B) going green — never a coverage percentage.

### 6.1 RED-GREEN-REFACTOR contract

For each behavior-changing task:

1. **RED** — one focused failing test for the next behavior; one behavior per test; descriptive name; minimal local fixtures. The test must fail because behavior is _wrong or absent_, not merely uncalled — assert on real output, not that a mock was invoked.
2. **Verify RED** — run the narrowest test; confirm failure is caused by the missing behavior, not by syntax/import/collection/fixture/environment/unrelated defects. Do not proceed past a wrong-reason failure. This gate is the whole point of RED.
3. **GREEN** — smallest production change that satisfies the failing test; no unrelated refactoring; no speculative behavior.
4. **Verify GREEN** — re-run targeted; run nearest regression; confirm no unexpected warnings or side effects.
5. **REFACTOR** — improve structure, remove duplication, improve names/boundaries; preserve behavior; keep tests green. If REFACTOR reddens a test, revert to this task's GREEN commit, record why in notes, and do not advance with a red tree.
6. **Verify Task** — task tests + ruff + basedpyright + applicable integration/build checks; then commit `T{n}: {summary} ({REQ/FR ids}, {TC ids})`.

### 6.2 Test categories

Unit and regression tests live beside their subjects in `tests/` (repo convention: flat `tests/test_*.py` plus `tests/control_plane/`, `tests/package_contract/`); reconstruction/activation proofs live in `tests/package_contract/`. Brownfield tasks add a `T{n}.0 CHARACTERIZE` sub-task where current behavior must be pinned before change.

### 6.3 TDD exceptions

| Task | Exception reason | Objective validation |
| --- | --- | --- |
| T3 | Verification-harness expansion (the real fight went RED in T1.1); a class with no divergence has no meaningful RED | full parity run, no skips permitted |
| T7, T8, T9 (scaffold step only) | Predecessor-equivalent payload scaffolds are generated state | integrity validation + reconstruction gates |
| T10 | Catalog/projection regeneration is generated state proven by existing gates | package/graph/schema/projection suites + dogfood validate |
| T11 | Documentation-only | Markdown gates + frontmatter gate + doc-coherence tests |
| T12 | Release preparation (build, gate orchestration, changelog conversion) | Full candidate-runtime gate + release-classification check |
| T13 | Publication and issue closure (owner-gated operational task) | Hosted workflow evidence + asset byte parity + issue state |

## 7. Execution Summary (dependency index)

| Task | Title | Phase | Depends on | Requirement(s) | Primary verification |
| --- | --- | --- | --- | --- | --- |
| T1 | Minimal-escape scalar emitter with acceptance preservation | P1 | None | FR-008 | `uv run pytest tests/test_format_frontmatter.py` |
| T2 | Block-list item spelling preservation | P1 | T1 | FR-008 | `uv run pytest tests/test_format_frontmatter.py` |
| T3 | Pinned-Prettier fixed-point oracle corpus | P1 | T2 | FR-009 | `uv run pytest tests/test_frontmatter_prettier_parity.py` |
| T4 | format-frontmatter skip diagnostics and mode resolution | P1 | T1 | FR-010 | `uv run pytest tests/test_format_frontmatter.py tests/test_validate_frontmatter.py` |
| T5 | Factual legacy-authority note | P1 | None | FR-011 | `uv run pytest tests/control_plane/test_command_resolution.py` |
| T6 | Whole-file conflict first-difference pointer | P1 | None | FR-012 | `uv run pytest tests/control_plane/` |
| T7 | python-tooling 1.8 payload | P2 | T1, T2, T3, T4, T5, T6 | FR-001, FR-002, FR-003, FR-004, FR-014 | `uv run pytest tests/package_contract/ -k python_tooling` |
| T8 | markdown-tooling 1.8 payload | P2 | T7 | FR-005, FR-014 | `uv run pytest tests/package_contract/ -k markdown_tooling` |
| T9 | markdown-frontmatter 1.5 payload | P2 | T8 | FR-006, FR-007, FR-014, NFR-002 | `uv run pytest tests/package_contract/ -k markdown_frontmatter` |
| T10 | Catalog 5 integration and projections | P3 | T7, T8, T9 | FR-013 | candidate-runtime package/graph/projection gates |
| T11 | Documentation and changelog | P4 | T1, T2, T3, T4, T5, T6, T10 | FR-007, FR-014, FR-017 | markdown + frontmatter gates |
| T12 | 5.8.0 candidate build and full gate | P5 | T11 | FR-015, FR-017, NFR-001, NFR-003, NFR-004 | full extracted-runtime gate |
| T13 | Publish 5.8.0 and close issues (owner-gated) | P5 | T12 | FR-015, FR-016 | hosted evidence + asset parity |

## 8. Implementation Tasks

### Phase P1: Engine corrections

#### T1: Minimal-escape scalar emitter with acceptance preservation

- **goal:** Key-line scalars are emitted per the FR-008 cost model, with every 5.7.0-accepted spelling preserved verbatim and control-character values emitted losslessly.
- **phase:** P1 · **depends_on:** [] · **requirements:** [FR-008] · **priority:** must

##### T1 Context

`_requote_scalar_line` keeps its single-quoted bypass unchanged. New behavior: a well-formed double-quoted scalar is kept double-quoted when the decoded value's double-style cost (count of `"` plus `\`) is strictly lower than single-style cost (count of `'`), or when the value contains control characters (which force double-quoted emission with the full YAML escape table: `\n`, `\t`, `\r`, `\xNN`, `\\`, `\"`); ties and cheaper-single values convert to single quotes exactly as today. Unquoted plain scalars quote in the minimal style of their raw text. Replace `_emit_single_quoted` with `_emit_scalar(value)` implementing the rule; keep the old name as a thin delegate only if other call sites need staging until T2. The scaffolding/bump/infer call sites emit values that contain no quotes/control characters, so their output is unchanged; assert that.

##### T1 Files

| Action | Path | Purpose |
| --- | --- | --- |
| modify | `src/project_standards/format_frontmatter.py` | `_emit_scalar`, requote/double-quote handling |
| test | `tests/test_format_frontmatter.py` | New regressions + updated expectations |

##### T1 Acceptance Criteria

- A double-quoted apostrophe scalar (`"Apple's"`) is preserved and not reported as needing reformatting (verified by TC-T1-001).
- A single-quoted doubled-apostrophe scalar (`'Apple''s'`) stays byte-identical and unflagged (verified by TC-T1-002).
- An escape-free double-quoted scalar (`"Hello"`) still converts to `'Hello'` (verified by TC-T1-003).
- A double-quoted control-character scalar (`"a\nb"`) round-trips losslessly instead of emitting literal control bytes (verified by TC-T1-004).
- An unquoted apostrophe scalar emits double-quoted with the parsed value unchanged (verified by TC-T1-005).
- The formatter's output for an apostrophe-bearing document is byte-stable under the pinned Prettier — the real cross-tool fight goes RED before any emitter change (verified by TC-T1-008; requires `npm ci`; a missing Node toolchain is a task failure, not a skip).
- The complete emitter contract is table-driven: both quote-count cost branches, ties resolving to single, backslash counting, the full control-character escape set, and the block-scalar/flow-list/null exclusions (verified by TC-T1-006).
- A frozen corpus of 5.7.0-canonical documents — key-line scalars in every accepted class — reports no reformatting and produces identical bytes through both current-default and exact markdown-frontmatter 1.4 routing (verified by TC-T1-007).

##### T1 Test Cases

| ID | Test | Type | Expected result |
| --- | --- | --- | --- |
| TC-T1-001 | `test_minimal_double_quoted_scalar_is_preserved` | regression | no `would reformat`; bytes unchanged |
| TC-T1-002 | `test_legacy_single_quoted_spelling_stays_accepted` | regression | bytes unchanged; check exit 0 |
| TC-T1-003 | `test_escape_free_double_quoted_still_normalizes_to_single` | unit | `"Hello"` → `'Hello'` |
| TC-T1-004 | `test_control_character_scalar_round_trips_losslessly` | regression | emitted YAML parses to identical value |
| TC-T1-005 | `test_unquoted_apostrophe_scalar_emits_minimal_double` | unit | `Apple's plan` → `"Apple's plan"`; value equal |
| TC-T1-006 | `test_emitter_contract_table` | contract | every cost/tie/escape/exclusion row correct |
| TC-T1-007 | `test_frozen_5_7_0_corpus_stays_green_both_routings` | regression | zero reformat reports; byte identity |
| TC-T1-008 | `test_formatter_output_stable_under_pinned_prettier` | integration | Prettier makes no change to formatter output |

##### T1 Sub-tasks (instructions)

- **T1.1 RED** — run `npm ci` (fail the task if unavailable). Add TC-T1-001, TC-T1-004, TC-T1-005, TC-T1-008, and the behavior-changing rows of TC-T1-006 (double-preservation branches and control-character escape rows; the tie rule lands with the unchanged-behavior rows in T1.3, since ties already resolve to single today) to `tests/test_format_frontmatter.py` / `tests/test_frontmatter_prettier_parity.py`. Expected failures: the current emitter rewrites `"Apple's"` to `'Apple''s'` (reported as reformat), re-emits the decoded `a\nb` as literal-newline single-quoted output, single-quotes the unquoted apostrophe raw text, fails every new-behavior contract row, and its `'Apple''s'` output is rewritten by the pinned Prettier (the issue #26 fight, demonstrated live).
- **T1.2 Verify RED** — `uv run pytest tests/test_format_frontmatter.py tests/test_frontmatter_prettier_parity.py -k "minimal_double_quoted or control_character or unquoted_apostrophe or emitter_contract or stable_under_pinned"`; confirm every failure is wrong output, not collection errors or missing Node tooling.
- **T1.3 GREEN** — implement `_emit_scalar` and the double-quoted preservation branch in `_requote_scalar_line`; add TC-T1-002/003 (acceptance-preservation pins of unchanged behavior), the unchanged-behavior TC-T1-006 rows (tie rule included), and TC-T1-007 (frozen 5.7.0 corpus through current-default and exact-1.4 selection routing).
- **T1.4 Verify GREEN** — `uv run pytest tests/test_format_frontmatter.py tests/test_frontmatter_prettier_parity.py`; existing quoting tests updated only where the spec changes the expectation (`test_double_quoted_becomes_single_quoted` narrows to escape-free input).
- **T1.5 REFACTOR** — consolidate cost computation into one pure function; keep tests green.
- **T1.6 Verify Task** — rebuild the candidate runtime (`uv build --wheel` + extract), then `PYTHONPATH=$PWD/build/{runtime} uv run pytest tests/test_format_frontmatter.py tests/test_frontmatter_prettier_parity.py tests/test_validate_frontmatter.py` and `PYTHONPATH=$PWD/build/{runtime} uv run project-standards validate` · `uv run ruff check .` · `uv run ruff format --check .` · `uv run basedpyright` · commit.

#### T2: Block-list item spelling preservation

- **goal:** `normalize_lists` keeps any list item whose current spelling is an accepted canonical form, while still applying block-style conversion, first-wins dedupe, and indentation. · **phase:** P1 · **depends_on:** [T1] · **requirements:** [FR-008] · **priority:** must
- **files:** `src/project_standards/format_frontmatter.py` (modify), `tests/test_format_frontmatter.py` (test)
- **acceptance:** `- 'Apple''s'` stays byte-identical (TC-T2-001); `- "Apple's"` is preserved, not re-spelled (TC-T2-002); an unquoted item still gains minimal quoting and flow lists still convert (TC-T2-003); dedupe keeps the first occurrence's spelling (TC-T2-004); a frozen 5.7.0-canonical list corpus reports no reformatting through both current-default and exact-1.4 routing (TC-T2-005).
- **sub-tasks:**
  - **T2.1 RED** — add TC-T2-001 and TC-T2-002. Expected failure: reconstruction re-emits both via the emitter, re-spelling `"Apple's"` (and, pre-T1, `'Apple''s'` survives only coincidentally — assert byte identity to make the lexical guarantee explicit).
  - **T2.2 Verify RED** — targeted run; failures are wrong re-spelling, not parse errors.
  - **T2.3 GREEN** — extract original item spellings from `entry.lines` before the BaseLoader decode; preserve an item's spelling when it is in the acceptance set for its decoded value; re-spell others via `_emit_scalar`. Add TC-T2-003/004/005.
  - **T2.4 Verify GREEN** — `uv run pytest tests/test_format_frontmatter.py`.
  - **T2.5 REFACTOR** — share the acceptance-set predicate with `_requote_scalar_line`; keep green.
  - **T2.6 Verify Task** — rebuild candidate runtime; `PYTHONPATH=$PWD/build/{runtime} uv run pytest tests/test_format_frontmatter.py tests/test_frontmatter_prettier_parity.py` + `project-standards validate` under the runtime + ruff + format + basedpyright; commit.

#### T3: Pinned-Prettier fixed-point oracle corpus

- **goal:** Formatter output is byte-stable under the pinned Prettier and Prettier output passes the formatter check, over the full FR-009 corpus, with any cost-model divergence resolved toward Prettier. · **phase:** P1 · **depends_on:** [T2] · **requirements:** [FR-009] · **priority:** must
- **files:** `tests/test_frontmatter_prettier_parity.py` (create), `src/project_standards/format_frontmatter.py` (modify only on divergence)
- **acceptance:** For every corpus document: `format --write` → `npx prettier --write` produces no change, and `prettier --write` → `format-frontmatter --check` exits 0 (TC-T3-001); corpus covers apostrophes, double quotes, both kinds, single/repeated backslashes, escaped and literal line breaks, tabs, control characters, CJK, dates, identifier-like numbers, and list items in both accepted spellings (TC-T3-002).
- **TDD note:** the real cross-tool fight went RED in T1.1 (TC-T1-008). This task expands the oracle to the full FR-009 corpus — a verification-harness extension (§6.3): each new corpus class either passes (parity holds) or exposes a genuine divergence, which then gets its own RED→GREEN cycle toward Prettier's output. The parity tests require `npm ci`; a missing Node toolchain fails the task rather than skipping.
- **sub-tasks:**
  - **T3.1 RED** — extend the corpus with every FR-009 class (both quote kinds, repeated backslashes, escaped and literal line breaks, tabs, control characters, CJK, dates, identifier-like numbers, list items in both spellings) plus TC-T3-002 asserting corpus completeness. Expected failure: any class where `_emit_scalar` diverges from Prettier; if all classes pass, record "no divergence" in `notes.md` and treat this task under its §6.3 exception.
  - **T3.2 Verify RED** — full parity run after `npm ci`; every failure must be a real byte diff, never a skip.
  - **T3.3 GREEN** — fix divergences in `_emit_scalar` toward Prettier's observed output; record each divergence and resolution in `notes.md` for close-out harvest into the spec deviation record.
  - **T3.4 Verify GREEN** — full parity run plus `uv run pytest tests/test_format_frontmatter.py`.
  - **T3.5 REFACTOR** — none expected; record `none`.
  - **T3.6 Verify Task** — rebuild candidate runtime; parity + formatter suites under `PYTHONPATH=$PWD/build/{runtime}` + `project-standards validate` + static gates; commit.

#### T4: format-frontmatter skip diagnostics and mode resolution

- **goal:** An explicitly named file dropped by config exclusion or the frontmatter denylist produces a stderr diagnostic; `--help` states check is the default; `--check` resolves through an explicit mode-resolution unit. · **phase:** P1 · **depends_on:** [T1] · **requirements:** [FR-010] · **priority:** must
- **files:** `src/project_standards/validate_frontmatter.py` (modify `collect_paths` reporting), `src/project_standards/format_frontmatter.py` (modify: help text, mode unit, denylist diagnostics), `tests/test_validate_frontmatter.py` + `tests/test_format_frontmatter.py` (test)
- **acceptance:** Naming an excluded file prints `skipped (excluded by config): PATH` to stderr with exit code unchanged (TC-T4-001); naming a denylisted file prints `skipped (never-frontmatter file): PATH` (TC-T4-002); `--help` output contains the default-mode statement (TC-T4-003); mode-resolution unit returns check for no-flag and `--check`, write for `--write` (TC-T4-004); `validate-frontmatter`'s shared `collect_paths` callers keep exit behavior (no regression in existing suites).
- **sub-tasks:**
  - **T4.1 RED** — add TC-T4-001/002 asserting the stderr diagnostics. Expected failure: current code drops both silently.
  - **T4.2 Verify RED** — targeted; silent-drop confirmed as the failure.
  - **T4.3 GREEN** — report named-and-dropped files from `collect_paths` (return or callback carrying the skip reason; only explicitly named files produce diagnostics — include/glob-derived paths stay silent), print denylist skips for named files in both loops, add the help-text default statement, and introduce the mode-resolution unit consumed at `write = ...`; add TC-T4-003/004.
  - **T4.4 Verify GREEN** — `uv run pytest tests/test_format_frontmatter.py tests/test_validate_frontmatter.py`.
  - **T4.5 REFACTOR** — none expected; record `none`.
  - **T4.6 Verify Task** — rebuild candidate runtime; task tests + `project-standards validate` under `PYTHONPATH=$PWD/build/{runtime}` + static gates + `docs/usage.md` accuracy check deferred to T11 (note it); commit.

#### T5: Factual legacy-authority note

- **goal:** The legacy-authority message becomes a factual note that does not contradict UPGRADING.md §2, across all three call-site routes. · **phase:** P1 · **depends_on:** [] · **requirements:** [FR-011] · **priority:** must
- **files:** `src/project_standards/control_plane/command_resolution.py` (modify), `tests/control_plane/test_command_resolution.py` + route tests (modify/create)
- **acceptance:** Note text is `note: reading legacy .project-standards.yml authority; the V5 control plane takes over after migration` on stderr, once per process (TC-T5-001); the text contains no imperative "migrate before using" phrasing (TC-T5-002); all three routes emit it in legacy-only state (TC-T5-003).
- **sub-tasks:**
  - **T5.1 RED** — update the pinned assertion to the new text and add route coverage. Expected failure: current warning text.
  - **T5.2 Verify RED** — targeted; old text is the failure.
  - **T5.3 GREEN** — reword the message in `emit_legacy_authority_warning` only.
  - **T5.4 Verify GREEN** — `uv run pytest tests/control_plane/test_command_resolution.py` plus the agent-handoff CLI suite.
  - **T5.5 REFACTOR** — none expected; record `none`.
  - **T5.6 Verify Task** — rebuild candidate runtime; task tests + agent-handoff CLI suite + `project-standards validate` under `PYTHONPATH=$PWD/build/{runtime}` + static gates; commit.

#### T6: Whole-file conflict first-difference pointer

- **goal:** Whole-file `CP-CONSUMER-CONFLICT` findings on text targets carry the first differing line number and a bounded expected-side excerpt; consumer content never appears. · **phase:** P1 · **depends_on:** [] · **requirements:** [FR-012] · **priority:** must
- **files:** `src/project_standards/control_plane/planner.py` (modify), `src/project_standards/control_plane/diagnostics.py` (modify: additive finding fields), `src/project_standards/control_plane/cli.py` (modify rendering), `tests/control_plane/` (test)
- **acceptance:** A whole-file text conflict renders `first difference: line N` plus `expected: {bounded excerpt}` under the digests (TC-T6-001); the excerpt bound is deterministic — at most 120 characters of the expected line, with a `…` truncation marker when cut — and an overlong expected line is truncated in terminal, JSON, and serialized findings (TC-T6-004); the actual/consumer line never appears in any output even when it contains a secret-like marker (TC-T6-002); binary/undecodable targets keep digest-only rendering (TC-T6-003); the schema change is additive (existing findings tests pass unmodified except where they assert the absence of extra lines).
- **sub-tasks:**
  - **T6.1 RED** — add TC-T6-001 and TC-T6-002 (fixture consumer file contains a canary string; assert it appears nowhere in rendered/serialized findings). Expected failure: digest-only rendering lacks the pointer (TC-T6-001).
  - **T6.2 Verify RED** — targeted; missing pointer is the failure; the canary assertion passes trivially pre-change and guards the GREEN.
  - **T6.3 GREEN** — compute the first differing line during planning for whole-file text conflicts, thread additive fields through diagnostics, render them in `cli.py` with the 120-character + `…` bound; add TC-T6-003/004.
  - **T6.4 Verify GREEN** — `uv run pytest tests/control_plane/`.
  - **T6.5 REFACTOR** — none expected; record `none`.
  - **T6.6 Verify Task** — rebuild candidate runtime; control-plane suite + `project-standards validate` under `PYTHONPATH=$PWD/build/{runtime}` + static gates; commit.

### Phase P2: Successor payloads

#### T7: python-tooling 1.8 payload

- **goal:** python-tooling 1.8 renders declared pytest collection roots across the pytest, checker, Ruff, and VS Code units with governance, byte-identical defaults, closed validation, and verbatim migrations. · **phase:** P2 · **depends_on:** [T1, T2, T3, T4, T5, T6] · **requirements:** [FR-001, FR-002, FR-003, FR-004, FR-014] · **priority:** must

##### T7 Context

Author `standards/python-tooling/versions/1.8/` as a full copy of 1.7 changing config schema (`pytest.test_paths`), provider (`_pytest_key`, `_source_roots`, `_setting`), contributions' `governing_options`, migrations (`python-tooling-1-7-to-1-8`, `legacy-v4-to-1-8` with the enumerated affected delta: `pytest-testpaths`, `vscode-pytest-args`, checker and Ruff contributions), `adopt.md`/`README.md`/`agent-summary.md`, and integrity metadata. Follow the payload wiring order from §3.4. Cross-option overlap: first-wins include dedupe; `additional_source_roots` coverage semantics preserved for overlapping paths. Catalog default advancement is T10's job — this task ends with the payload advertised with `role = "retained"` (a valid role that does not advance selection; the same applies to the T8.0 and T9.0 scaffolds) and reconstruction-tested; T10 performs the retained→default flips for all three successors.

##### T7 Files

| Action | Path | Purpose |
| --- | --- | --- |
| create | `standards/python-tooling/versions/1.8/**` | Successor payload (full copy + delta) |
| modify | `standards/python-tooling/standard.toml` | `[[versions]]` 1.8 |
| modify | `catalogs/5.toml` | `[[packages]]` 1.8 advertisement |
| create | `src/project_standards/payloads/python-tooling/1.8/**` | Symlinked projection |
| test | `tests/package_contract/test_python_tooling_reconstruction.py` + option/migration tests | Proofs |

##### T7 Acceptance Criteria

- 1.7 cannot express a non-default collection root (characterization, TC-T7-001).
- `pytest.test_paths = ["qa/tests"]` renders `testpaths`, checker `include`, Ruff `src`, and `pytestArgs` accordingly, with coverage sources unchanged (TC-T7-002).
- Undeclared configurations render byte-identical to 1.7, including overlap configs declaring `tests` in `additional_source_roots` (TC-T7-003).
- Empty/duplicate/unsafe/unknown-key values fail schema resolution (TC-T7-004).
- All four affected contributions govern with `/pytest/test_paths`; conflicts name it (TC-T7-005).
- Migrations carry values verbatim, both migration paths omit an undeclared `pytest.test_paths` (no invention), and the affected list covers the payload delta (TC-T7-006).
- Multi-root declarations preserve declared order after the layout root; overlaps with `additional_source_roots` in both string and table form dedupe first-wins in `include` while keeping their declared coverage semantics (TC-T7-007).

##### T7 Test Cases

| ID | Test | Type | Expected result |
| --- | --- | --- | --- |
| TC-T7-001 | `test_1_7_cannot_express_alternate_collection_root` | characterization | 1.7 schema rejects `pytest.test_paths` |
| TC-T7-002 | `test_test_paths_renders_across_all_four_units` | unit | four rendered units carry the roots |
| TC-T7-003 | `test_default_and_overlap_configs_render_byte_identical_to_1_7` | regression | byte equality |
| TC-T7-004 | `test_test_paths_schema_rejections` | unit | each invalid form fails closed |
| TC-T7-005 | `test_governing_options_name_test_paths_on_conflict` | integration | conflict prints `/pytest/test_paths` |
| TC-T7-006 | `test_migrations_carry_values_and_affected_list_covers_delta` | contract | verbatim carriage; no invented option; delta covered |
| TC-T7-007 | `test_multi_root_ordering_and_cross_option_overlap_semantics` | unit | order and coverage semantics pinned |

##### T7 Sub-tasks (instructions)

- **T7.0 CHARACTERIZE** — TC-T7-001 pinning the 1.7 rejection; then stage the 1.8 scaffold: a predecessor-equivalent full copy wired per §3.4 (digests, family `standard.toml`, catalog advertisement, projection) whose schema/provider/contributions still match 1.7 behavior. The scaffold is generated state, validated by the integrity and reconstruction gates, not by a RED.
- **T7.1 RED** — add TC-T7-002 against the staged 1.8. Expected failure: the 1.8 schema still rejects `pytest.test_paths` / the provider still renders hardcoded `tests` — missing behavior, not a missing payload.
- **T7.2 Verify RED** — targeted under the rebuilt candidate runtime; failure is the absent option behavior.
- **T7.3 GREEN** — implement the schema/provider/governance/migration delta per Context; add TC-T7-003/004/005/006/007; rebuild the runtime.
- **T7.4 Verify GREEN** — `PYTHONPATH=$PWD/build/{runtime} uv run pytest tests/package_contract/ -k python_tooling` covering all seven TCs.
- **T7.5 REFACTOR** — none expected on a payload copy; record `none`.
- **T7.6 Verify Task** — package-contract + graph/schema suites under the candidate runtime + static gates; commit.

#### T8: markdown-tooling 1.8 payload

- **goal:** markdown-tooling 1.8 accepts the observed literal-form `.markdownlint.json` digest so a consumer holding either byte form migrates cleanly. · **phase:** P2 · **depends_on:** [T7] · **requirements:** [FR-005, FR-014] · **priority:** must
- **files:** `standards/markdown-tooling/versions/1.8/**` (create, full copy; resources byte-identical), `standards/markdown-tooling/standard.toml` + `catalogs/5.toml` (modify), `src/project_standards/payloads/markdown-tooling/1.8/**` (create), `tests/fixtures/observed_consumers/markdownlint-literal-cjk.json` + provenance note (create), `tests/package_contract/` + migration tests (test)
- **acceptance:** The fixture's digest equals `sha256:4c1c089d0552a6118f6a8b7d85bae1bd762da41d601d1c489bdb9143f6a2d548` and is parsed-JSON-equal to the shipped resource (TC-T8-001); the 1.8 migration proof is parameterized over BOTH byte forms — shipped escaped and observed literal — each blocking under 1.7 signatures only for the literal form and completing cleanly under 1.8 to managed ownership of the current escaped bytes with zero findings (TC-T8-002); provenance metadata carries date/digest with no repository identifier (TC-T8-003, inspection assertion).
- **sub-tasks:**
  - **T8.0 CHARACTERIZE** — pin the 1.7 literal-form block from the observed fixture; stage the 1.8 scaffold (predecessor-equivalent full copy, wired per §3.4, resources byte-identical).
  - **T8.1 RED** — TC-T8-002's literal-form 1.8 leg against the staged scaffold. Expected failure: the 1.8 signature still lists only the escaped digest, so the literal form still blocks — missing behavior, not a missing payload.
  - **T8.2 Verify RED** — targeted under the rebuilt candidate runtime.
  - **T8.3 GREEN** — add the literal-form digest to the signature lineage, re-point migrations, update docs; rebuild runtime; add TC-T8-001/003 and the escaped-form parameterization.
  - **T8.4 Verify GREEN** — `PYTHONPATH=$PWD/build/{runtime} uv run pytest tests/package_contract/ -k markdown_tooling` covering both parameterized forms.
  - **T8.5 REFACTOR** — none expected; record `none`.
  - **T8.6 Verify Task** — suites + static gates; commit.

#### T9: markdown-frontmatter 1.5 payload

- **goal:** markdown-frontmatter 1.5 offers `workflow_ownership` relinquishment for `validate-standards.yml` through the intent-pointer path, with the full claim matrix fail-closed. · **phase:** P2 · **depends_on:** [T8] · **requirements:** [FR-006, FR-007, FR-014, NFR-002] · **priority:** must
- **files:** `standards/markdown-frontmatter/versions/1.5/**` (create: config schema `workflow_ownership`, `when_any` gates on the four workflow contributions, signature `consumer_owned_intent_pointer`, provider branch, migrations, docs incl. minimal-escape serialization description), `standards/markdown-frontmatter/standard.toml` + `catalogs/5.toml` (modify), `src/project_standards/payloads/markdown-frontmatter/1.5/**` (create), `tests/package_contract/` + migration tests (test)
- **acceptance:** 1.4 blocks a customized caller with no available escape (characterization, TC-T9-001); under 1.5, each of the six claim-matrix states — missing, malformed, unknown-with-intent, unknown-without-intent, known, consumer-owned — has its own concrete test exercising preview, apply (or refusal), and second-apply convergence, asserting exact caller bytes, materialization state, and finding code/hint (TC-T9-002 relinquishment leg, TC-T9-003 blocked leg, TC-T9-004 managed/known legs, TC-T9-005 failure-state legs); the 1.5 signature declares `consumer_owned_intent_pointer` and no `unknown_content_disposition` (TC-T9-006, explicit shape assertion); 1.5 docs describe minimal-escape quoting (inspection within doc-coherence tests).
- **sub-tasks:**
  - **T9.0 CHARACTERIZE** — TC-T9-001 pinning the 1.4 dead end; stage the 1.5 scaffold (predecessor-equivalent full copy, wired per §3.4).
  - **T9.1 RED** — TC-T9-002 against the staged scaffold. Expected failure: the 1.5 schema still rejects `workflow_ownership`, so the relinquishment path is absent — missing behavior, not a missing payload.
  - **T9.2 Verify RED** — targeted under the rebuilt candidate runtime.
  - **T9.3 GREEN** — implement option, gates, pointer, and provider branch per spec approach; add TC-T9-003/004/005/006; rebuild runtime.
  - **T9.4 Verify GREEN** — `PYTHONPATH=$PWD/build/{runtime} uv run pytest tests/package_contract/ -k markdown_frontmatter` covering all six matrix states across preview/apply/convergence.
  - **T9.5 REFACTOR** — none expected; record `none`.
  - **T9.6 Verify Task** — suites + static gates; commit.

### Phase P3: Catalog integration

#### T10: Catalog 5 integration and projections

- **goal:** Catalog 5 advances the three defaults (python-tooling 1.8, markdown-tooling 1.8, markdown-frontmatter 1.5), retains every predecessor, and all generated state is regenerated and consistent. · **phase:** P3 · **depends_on:** [T7, T8, T9] · **requirements:** [FR-013] · **priority:** must
- **files:** `catalogs/5.toml` + `src/project_standards/catalogs/5.toml` (modify: role flips), `standards/catalog.md` (regenerate), family `README.md`/`agent-summary.md` landing pages (modify), `tests/package_contract/test_current_catalog_activation.py` (`_PACKAGES`/`_RETAINED_CATALOG_ENTRIES`), version-named dogfood tests, `.standards/` refresh via `reconcile --apply` (modify)
- **acceptance:** Activation constants list the three new defaults with predecessors retained (TC-T10-001); projections and rendered catalog match canonical sources (existing drift gates); `uv run project-standards validate` passes with the candidate runtime first on `PYTHONPATH` (TC-T10-002); release classification reports MINOR (TC-T10-003, may be re-verified in T12).
- **sub-tasks:**
  - **T10.1 RED** — update activation constants expectations first. Expected failure: catalog still selects old defaults.
  - **T10.2 Verify RED** — targeted activation test failure under the candidate runtime.
  - **T10.3 GREEN** — flip roles, regenerate projections/catalog/landing pages, rebuild runtime, `reconcile --apply` (last, per closeout ordering).
  - **T10.4 Verify GREEN** — package/graph/schema/projection suites + dogfood validate under the candidate runtime.
  - **T10.5 REFACTOR** — none; record `none`.
  - **T10.6 Verify Task** — the suites above + markdown gates (catalog.md changed) + static gates; commit.

### Phase P4: Documentation

#### T11: Documentation and changelog

- **goal:** UPGRADING.md, docs/usage.md, and CHANGELOG.md document every consumer-visible change and disposition of this train. · **phase:** P4 · **depends_on:** [T1, T2, T3, T4, T5, T6, T10] · **requirements:** [FR-007, FR-014, FR-017] · **priority:** must
- **files:** `UPGRADING.md` (modify: §3 ownership-escape table `markdown_frontmatter` row, serialization convergence, `test_paths` option surface, legacy-note rewording, markdownlint byte-form acceptance), `docs/usage.md` (modify: skip diagnostics, default mode), `CHANGELOG.md` (modify: #26–#31 entries under Unreleased, incl. #29 non-reproduction/hardening and #27 sanitized provenance)
- **acceptance:** A named per-document checklist, every item verified present and accurate: `UPGRADING.md` — §3 ownership table `markdown_frontmatter` row; serialization convergence statement (both forms accepted, Prettier resting state, legacy spellings stay valid); `pytest.test_paths` surface; markdownlint byte-form acceptance; legacy-note rewording; the consumer-owned caller obligations including job wiring and the documented path back to `managed`. `standards/python-tooling/versions/1.8/adopt.md` — `test_paths` option with all four rendered units. `standards/markdown-tooling/versions/1.8/adopt.md` — accepted legacy byte form. `standards/markdown-frontmatter/versions/1.5/adopt.md` + `agent-summary.md` — `workflow_ownership` escape and minimal-escape quote rule replacing the single-quote rule. `docs/usage.md` — skip diagnostics and default mode. `CHANGELOG.md` — #26–#31 entries incl. #29 non-reproduction/hardening and #27 sanitized provenance. Reconstruction/doc-coherence suites green over the three versioned guides; markdown + frontmatter gates green; UPGRADING §2's prescribed commands no longer contradict any emitted message.
- **sub-tasks:**
  - **T11.1 RED** — not applicable (TDD exception §6.3); copy the acceptance checklist above into `notes.md` and tick per document.
  - **T11.2 Verify RED** — n/a.
  - **T11.3 GREEN** — write the documentation.
  - **T11.4 Verify GREEN** — `npx prettier --check .` · `npx markdownlint-cli2` · frontmatter/doc-coherence suites.
  - **T11.5 REFACTOR** — editorial pass; record `none` if unneeded.
  - **T11.6 Verify Task** — gates above + `PYTHONPATH=$PWD/build/{runtime} uv run pytest tests/ -k "coherence or docs"`; commit.

### Phase P5: Release

#### T12: 5.8.0 candidate build and full gate

- **goal:** One candidate wheel and sdist pass the complete repository gate, release classification is MINOR, and no previously-passing outcome regressed. · **phase:** P5 · **depends_on:** [T11] · **requirements:** [FR-015, FR-017, NFR-001, NFR-003, NFR-004] · **priority:** must
- **files:** `CHANGELOG.md` (modify: Unreleased → 5.8.0), `pyproject.toml` (modify: version), `uv.lock` (regenerate: embeds the project version), `tests/fixtures/package_contract/valid/full/expected/catalog.toml` (regenerate via `render_consumer_catalog`), `tests/test_version_consistency.py` expectations (verify), `build/` candidate artifacts (create, untracked)
- **acceptance:** The exact gate sequence, run serially against one candidate: `uv sync --dev` · `uv run ruff format --check . && uv run ruff check . && uv run basedpyright` · `uv build --wheel --out-dir dist` (plus sdist) · extract wheel to `build/candidate-5.8.0` · `export PYTHONPATH="$PWD/build/candidate-5.8.0"` · `uv run coverage erase` · `npm ci` · `uv run coverage run --source=project_standards -m pytest -m "not performance and not compatibility"` · `uv run pytest -m compatibility -n 4 --dist load --max-worker-restart=0` · `uv run pytest -m performance` · `uv run coverage report` · `uv run pip-audit` · `npx prettier --check .` · `npx markdownlint-cli2` · the standards-graph gate exactly as CI runs it: `uv run project-standards standards validate-packages --root .` · `uv run project-standards standards validate-graph --root . --require-all-manifests` · `uv run project-standards standards generate-package-schemas --root . --check` · `uv run project-standards standards sync-payload-projection --root . --check` · `uv run project-standards standards render-catalog --root . --check` · `uv run project-standards validate` · reconcile check no-op · `packages check-release` against the released 5.7.0 baseline classifying MINOR with no forbidden findings; lock/project version relationship verified before building; all of the above run freshly against the final release-commit tree (earlier T10 runs do not qualify it); evidence recorded in logs.
- **sub-tasks:**
  - **T12.1 RED** — n/a (TDD exception; the gate itself is the objective validation).
  - **T12.2 Verify RED** — n/a.
  - **T12.3 GREEN** — changelog conversion, version bump, `uv lock` regeneration, golden regeneration, then the acceptance gate sequence exactly.
  - **T12.4 Verify GREEN** — every gate command green; classification MINOR.
  - **T12.5 REFACTOR** — none; record `none`.
  - **T12.6 Verify Task** — commit the release-prep as the candidate release commit on `testing`.
- **BLOCKER GATE:** publication beyond this point requires explicit owner authorization.

#### T13: Publish 5.8.0 and close issues (owner-gated)

- **goal:** 5.8.0 published from `main` with signed `v5.8.0` + moving `v5` tags, byte-verified assets, green release-commit workflows; issues #26–#31 closed with evidence. · **phase:** P5 · **depends_on:** [T12] · **requirements:** [FR-015, FR-016] · **priority:** must
- **files:** release artifacts and GitHub state (external); `docs/handoff/` records per closeout ritual
- **acceptance:** Merge `testing` → `main`; signed immutable `v5.8.0` and moving `v5`; GitHub release with byte-matching assets; all release-commit workflows green; downloaded-asset parity; #26–#31 closed citing 5.8.0 evidence, #29 with the non-reproduction record and shipped hardening, #27 with sanitized provenance; the final publication/issue/handoff docs commit lands BEFORE the last synchronization step; then clean worktree and exact equality of local `main`, local `testing`, `origin/main`, and `origin/testing` are verified.
- **sub-tasks:**
  - **T13.1 RED** — n/a (operational).
  - **T13.2 Verify RED** — n/a.
  - **T13.3 GREEN** — execute the release process only after owner authorization (do not start otherwise; set the task `blocked` with `blocker: owner authorization pending`).
  - **T13.4 Verify GREEN** — hosted workflow evidence + asset hashes.
  - **T13.5 REFACTOR** — n/a; record `none`.
  - **T13.6 Verify Task** — issue closures verified; final handoff docs commit; synchronize branches last; verify clean status and four-way `main`/`testing` local/remote parity.

## 9. Cross-Cutting Requirements

| Concern | Applies? | How verified | Owning task |
| --- | --- | --- | --- |
| Error handling | yes | Schema rejections and claim-matrix findings fail closed (TC-T7-004, TC-T9-005) | T7, T9 |
| Security (secret handling) | yes | Conflict-pointer non-disclosure canary (TC-T6-002) | T6 |
| Compatibility (previously-passing rule) | yes | Acceptance-preservation and byte-identity regressions (TC-T1-002, TC-T2-001, TC-T7-003); MINOR classification | T1, T2, T7, T12 |
| Documentation | yes | Markdown/frontmatter/coherence gates + FR-014 checklist | T11 |
| Performance | no | — | — |
| Logging / observability | no | — | — |

## 10. Integration and Migration

### 10.1 Integration Sequence

1. P1 engine corrections (waves per the dependency index: T1/T5/T6 → T2/T4 → T3). 2. P2 payload authorings, strictly serialized T7 → T8 → T9 (shared catalog/family files; the `depends_on` chain is authoritative — the payloads are conceptually independent but must never run concurrently). 3. P3 catalog integration after all payloads. 4. P4 docs after behavior is final. 5. P5 release.

### 10.2 Data or State Migration

- **Required:** yes (package migrations 1.7→1.8 ×2, 1.4→1.5, legacy V4 re-points) · **Rollback supported:** yes (predecessors retained; exact pins unaffected) · **Idempotent:** yes (reconcile converges to no-op).

### 10.3 Compatibility Plan

Old and new package versions coexist in Catalog 5; only defaults advance. Engine behavior changes are uniformly acceptance-widening (NFR-001).

## 11. Risks and Decisions

| ID | Risk | Likelihood | Impact | Mitigation | Owning task |
| --- | --- | --- | --- | --- | --- |
| R-001 | Prettier's actual YAML quote algorithm diverges from the FR-008 cost model | med | med | T3 oracle corpus authoritative; divergences fixed toward Prettier and harvested to the spec | T3 |
| R-002 | Payload byte/digest wiring mistakes (order-sensitive) | med | high | §3.4 wiring order; integrity validation; reconstruction suites | T7, T8, T9 |
| R-003 | This repo's own managed docs flag under new emitter (dogfood churn) | low | med | Acceptance-only design means no newly-flagged content; verified by dogfood validate in T10/T12 | T10, T12 |
| R-004 | Release classification disputes (new options / signature additions) | low | high | check-release run early in T10 and finally in T12 | T10, T12 |

| ID | Decision | Rationale | Affected task(s) |
| --- | --- | --- | --- |
| D-001 | Spec is authoritative for all six issue resolutions (codex r4 `ready`) | Four-round adversarial convergence | all |
| D-002 | T13 requires explicit owner authorization before any publication step | Repo release policy; spec status line | T13 |

## 12. Open Questions

| Question | Blocking? | Owner | Current assumption |
| -------- | --------- | ----- | ------------------ |
| None     | no        | —     | —                  |

## 13. Final Verification (definition of done)

Run at close-out; evidence in checklists/notes, summary in §14.

- Full suite green under the extracted 5.8.0 candidate: `PYTHONPATH=$PWD/build/{runtime} uv run pytest`.
- Static: `uv run ruff check .` · `uv run ruff format --check .` · `uv run basedpyright`.
- Gates: coverage report, `uv run pip-audit`, `npx prettier --check .`, `npx markdownlint-cli2`, dogfood `project-standards validate`, `reconcile --check` no-op, `packages check-release` MINOR.
- Every in-scope requirement maps to a completed task; every acceptance criterion satisfied.
- Every task `done` or `skipped` with a reason; no open blocker (T13 owner gate resolved or explicitly outstanding); risks closed or accepted.
- Clean worktree; after T13, exact equality of local `main`, local `testing`, `origin/main`, and `origin/testing`.

## 14. Close-out

- **Completed:** 2026-07-23 · release commit `d007ba0` published as 5.8.0 (signed `v5.8.0` + moving `v5`, nine green release-commit workflow runs including `Check` `30002838425`, byte-verified assets, issues #26–#31 closed).
- **Deviations / decisions harvested from notes:**
  1. Known-digest relinquishment is intent-pointer-free by engine constraint (known history cannot use owner-resolution); the relinquishment claim proper serves only unknown callers. The issue #28 consumer (customized caller, unknown digest) still lands byte-intact — precedented by markdown-tooling's own provider.
  2. The `.standards/` reconcile deferred from T10 to T12: the release-lineage guard fails closed until the pyproject version advances, mirroring the 5.7.0 train.
  3. Prettier 3 honors `.gitignore`, so the parity harness pins `--ignore-path os.devnull` behind a committed mutation-guard test; parity probe files must live inside the repository tree because the `**/*.md` singleQuote override is path-relative.
  4. FR-009 divergence record: none. Prettier is quote/escape-preserving (not cost-minimizing) for 6 of the 13 corpus classes, so no non-canonical seed converges for those classes, but the FR-008 cost model matched pinned Prettier 3.8.3 exactly wherever Prettier does normalize.
  5. The inherited misnamed `legacy-v4-to-1-3` migration id carries forward into the markdown-frontmatter 1.5 copy under the immutable-copy rule.
  6. Markdown Frontmatter 1.5 example/template files carry generic infra-flavored example strings byte-identical to the released 1.4 payload — mandatory immutable carry-forward, accepted.
- **Risks closed / accepted:** R-001 closed (oracle corpus green, no cost-model divergence); R-002 closed (integrity/reconstruction suites plus the T12 reconcile no-op); R-003 closed (dogfood validate passes under the candidate); R-004 closed (`check-release --baseline v5.7.0` → minor, no findings).
- **Deferred work filed:** backlog-triaged minors from the final review (redundant `order` list, multi-line block-list continuation fixture, `splitlines()` Unicode line counting, `expected:` label reuse, TC-T7-003/TC-T7-006 coverage widening, dedicated `workflow_ownership` bad-enum test) and the confirmed-dead `plan_whole_file` cleanup candidate — none release-blocking, recorded in the session record.

Teardown: harvest notes here (+ ADRs/issues) → set `status: complete`, update `updated` → commit master → `rm -rf .project-pipeline/2026-07-22-{slug}/`.

<!-- markdownlint-disable MD025 -->

# Appendices

<!-- markdownlint-enable MD025 -->

## Appendix A. Interface or Schema Changes

### A.1 Public Interfaces

| Interface | Current | Planned | Compatibility |
| --- | --- | --- | --- |
| `format-frontmatter` CLI | dead `--check`, silent skips | explicit mode unit, skip diagnostics | exit codes unchanged |
| `CP-CONSUMER-CONFLICT` finding | digests only (whole-file) | + first-difference line, expected excerpt | additive fields |
| Legacy-authority message | imperative warning | factual note | same channel/guard |

### A.2 Data Models

| Model | Field | Change | Validation | Migration |
| --- | --- | --- | --- | --- |
| python-tooling config schema | `pytest.test_paths` | add | unique safe relative paths, min 1 | verbatim carriage |
| markdown-frontmatter config | `workflow_ownership` | add | enum managed/consumer-owned | verbatim carriage |
| markdown-tooling signature | `known_content_digests` | add | second digest (observed form) | n/a (new payload) |
| Control-plane finding schema | first-difference fields | add | additive, optional | n/a |

## Appendix B. Test Matrix (traceability)

| Test ID | Requirement | Task | Test path | Type |
| --- | --- | --- | --- | --- |
| TC-T1-001 | FR-008 | T1 | `tests/test_format_frontmatter.py::test_minimal_double_quoted_scalar_is_preserved` | regression |
| TC-T1-002 | FR-008, NFR-004 | T1 | `tests/test_format_frontmatter.py::test_legacy_single_quoted_spelling_stays_accepted` | regression |
| TC-T1-003 | FR-008 | T1 | `tests/test_format_frontmatter.py::test_escape_free_double_quoted_still_normalizes_to_single` | unit |
| TC-T1-004 | FR-008 | T1 | `tests/test_format_frontmatter.py::test_control_character_scalar_round_trips_losslessly` | regression |
| TC-T1-005 | FR-008 | T1 | `tests/test_format_frontmatter.py::test_unquoted_apostrophe_scalar_emits_minimal_double` | unit |
| TC-T1-006 | FR-008 | T1 | `tests/test_format_frontmatter.py::test_emitter_contract_table` | contract |
| TC-T1-007 | FR-008, NFR-001, NFR-004 | T1 | `tests/test_format_frontmatter.py::test_frozen_5_7_0_corpus_stays_green_both_routings` | regression |
| TC-T1-008 | FR-009 | T1 | `tests/test_frontmatter_prettier_parity.py::test_formatter_output_stable_under_pinned_prettier` | integration |
| TC-T2-001 | FR-008, NFR-004 | T2 | `tests/test_format_frontmatter.py::test_legacy_single_quoted_list_item_stays_byte_identical` | regression |
| TC-T2-002 | FR-008 | T2 | `tests/test_format_frontmatter.py::test_minimal_double_quoted_list_item_preserved` | regression |
| TC-T2-003 | FR-008 | T2 | `tests/test_format_frontmatter.py::test_unquoted_and_flow_list_items_still_normalize` | unit |
| TC-T2-004 | FR-008 | T2 | `tests/test_format_frontmatter.py::test_dedupe_keeps_first_occurrence_spelling` | unit |
| TC-T2-005 | FR-008, NFR-004 | T2 | `tests/test_format_frontmatter.py::test_frozen_5_7_0_list_corpus_stays_green_both_routings` | regression |
| TC-T3-001 | FR-009 | T3 | `tests/test_frontmatter_prettier_parity.py::test_formatter_prettier_mutual_fixed_point` | integration |
| TC-T3-002 | FR-009 | T3 | `tests/test_frontmatter_prettier_parity.py::test_corpus_covers_required_classes` | contract |
| TC-T4-001 | FR-010 | T4 | `tests/test_format_frontmatter.py::test_named_excluded_file_prints_skip_diagnostic` | regression |
| TC-T4-002 | FR-010 | T4 | `tests/test_format_frontmatter.py::test_named_denylisted_file_prints_skip_diagnostic` | regression |
| TC-T4-003 | FR-010 | T4 | `tests/test_format_frontmatter.py::test_help_states_check_is_default` | unit |
| TC-T4-004 | FR-010 | T4 | `tests/test_format_frontmatter.py::test_mode_resolution_unit_contract` | unit |
| TC-T5-001 | FR-011 | T5 | `tests/control_plane/test_command_resolution.py::test_legacy_note_text_and_once_guard` | unit |
| TC-T5-002 | FR-011 | T5 | `tests/control_plane/test_command_resolution.py::test_legacy_note_has_no_imperative_phrasing` | unit |
| TC-T5-003 | FR-011 | T5 | `tests/control_plane/test_command_resolution.py::test_all_three_routes_emit_note` | integration |
| TC-T6-001 | FR-012 | T6 | `tests/control_plane/test_conflict_pointer.py::test_whole_file_conflict_renders_first_difference` | unit |
| TC-T6-002 | FR-012 | T6 | `tests/control_plane/test_conflict_pointer.py::test_consumer_content_never_disclosed` | regression |
| TC-T6-003 | FR-012 | T6 | `tests/control_plane/test_conflict_pointer.py::test_binary_target_stays_digest_only` | unit |
| TC-T6-004 | FR-012 | T6 | `tests/control_plane/test_conflict_pointer.py::test_overlong_expected_line_truncates_with_marker` | regression |
| TC-T7-001 | FR-001 | T7 | `tests/package_contract/test_python_tooling_test_paths.py::test_1_7_cannot_express_alternate_collection_root` | characterization |
| TC-T7-002 | FR-001, FR-002 | T7 | `tests/package_contract/test_python_tooling_test_paths.py::test_test_paths_renders_across_all_four_units` | unit |
| TC-T7-003 | FR-004, NFR-001 | T7 | `tests/package_contract/test_python_tooling_test_paths.py::test_default_and_overlap_configs_render_byte_identical_to_1_7` | regression |
| TC-T7-004 | FR-004, NFR-002 | T7 | `tests/package_contract/test_python_tooling_test_paths.py::test_test_paths_schema_rejections` | unit |
| TC-T7-005 | FR-003 | T7 | `tests/package_contract/test_python_tooling_test_paths.py::test_governing_options_name_test_paths_on_conflict` | integration |
| TC-T7-006 | FR-004 | T7 | `tests/package_contract/test_python_tooling_test_paths.py::test_migrations_carry_values_and_affected_list_covers_delta` | contract |
| TC-T7-007 | FR-002 | T7 | `tests/package_contract/test_python_tooling_test_paths.py::test_multi_root_ordering_and_cross_option_overlap_semantics` | unit |
| TC-T8-001 | FR-005 | T8 | `tests/package_contract/test_markdown_tooling_legacy_forms.py::test_observed_fixture_digest_and_parsed_equality` | contract |
| TC-T8-002 | FR-005 | T8 | `tests/package_contract/test_markdown_tooling_legacy_forms.py::test_both_byte_forms_migrate_cleanly_on_1_8` | integration |
| TC-T8-003 | FR-005 | T8 | `tests/package_contract/test_markdown_tooling_legacy_forms.py::test_observed_fixture_provenance_is_sanitized` | contract |
| TC-T9-001 | FR-006 | T9 | `tests/package_contract/test_markdown_frontmatter_workflow_ownership.py::test_1_4_customized_caller_has_no_escape` | characterization |
| TC-T9-002 | FR-006 | T9 | `tests/package_contract/test_markdown_frontmatter_workflow_ownership.py::test_consumer_owned_relinquishes_and_preserves_caller` | integration |
| TC-T9-003 | FR-006, NFR-002 | T9 | `tests/package_contract/test_markdown_frontmatter_workflow_ownership.py::test_unknown_caller_without_intent_stays_blocked_with_actionable_hint` | integration |
| TC-T9-004 | FR-006 | T9 | `tests/package_contract/test_markdown_frontmatter_workflow_ownership.py::test_managed_default_composes_and_known_digest_migrates` | integration |
| TC-T9-005 | FR-007 | T9 | `tests/package_contract/test_markdown_frontmatter_workflow_ownership.py::test_claim_matrix_failure_states` | contract |
| TC-T9-006 | FR-006 | T9 | `tests/package_contract/test_markdown_frontmatter_workflow_ownership.py::test_signature_declares_pointer_without_preserve_disposition` | contract |
| TC-T10-001 | FR-013 | T10 | `tests/package_contract/test_current_catalog_activation.py` | contract |
| TC-T10-002 | FR-013 | T10 | dogfood `project-standards validate` under candidate runtime | e2e |
| TC-T10-003 | NFR-004 | T10 | `packages check-release` classification | contract |

## Appendix C. Deferred Work (identified at authoring)

| Item | Reason deferred | Follow-up |
| ---- | --------------- | --------- |
| None | —               | —         |
