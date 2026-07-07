# Design: CLI Documentation Standard

**Date:** 2026-07-07 **Status:** in codex spec-review (rounds 1–2 addressed; awaiting round 3) **Author:** session 2026-07-07

## Table of Contents

- [Design: CLI Documentation Standard](#design-cli-documentation-standard)
  - [Table of Contents](#table-of-contents)
  - [Problem / Goal](#problem--goal)
  - [Decisions (locked during brainstorming)](#decisions-locked-during-brainstorming)
  - [Background: ground truth](#background-ground-truth)
  - [Design](#design)
    - [1. The three-profile ladder](#1-the-three-profile-ladder)
    - [2. Cross-cutting normative rules](#2-cross-cutting-normative-rules)
    - [3. Content→destination mapping (exploding the monolith)](#3-contentdestination-mapping-exploding-the-monolith)
    - [4. `README.md` section outline](#4-readmemd-section-outline)
    - [5. Bundle layout](#5-bundle-layout)
    - [6. `adopt.md` (runbook)](#6-adoptmd-runbook)
    - [7. Adopt-engine plumbing](#7-adopt-engine-plumbing)
    - [8. Dogfood](#8-dogfood)
    - [9. Tests](#9-tests)
    - [10. Repo touchpoints (multi-file change list)](#10-repo-touchpoints-multi-file-change-list)
    - [11. Acceptance criteria](#11-acceptance-criteria)
      - [Bundle \& docs](#bundle--docs)
      - [Registration](#registration)
      - [Dogfood](#dogfood)
      - [Gate green (repo non-negotiable)](#gate-green-repo-non-negotiable)
      - [Release](#release)
  - [Versioning & release interplay](#versioning--release-interplay)
  - [Non-goals](#non-goals)
  - [Open questions](#open-questions)
  - [Audit trail](#audit-trail)

## Problem / Goal

The repo holds a 550-line research-prose draft (`standards/cli-framework/cli-documentation-standards.md`, tracked since `9c4e0e4`, mechanically cleaned in `e38678c`) describing a reusable framework for user-facing CLI usage documentation. It is a deep-research export, not a standard: it argues rather than governs, buries its reusable templates inside quadruple-backtick fences, and leans heavily on single-file-script distribution. A follow-up research pass (`docs/research/2026-07-07-cli-usage-docs-packaged-src-layout-python.md`, committed `bdab8e6`) filled in the packaged/`src/`-layout half: entry points as the parser source of truth, man-pages-in-wheels limitations, parser→docs generation tooling, multi-entry-point layouts, and installed-entry-point CI smoke testing.

The goal is to integrate this material as the repo's **sixth fully adoptable standard** — id `cli-documentation` — following the established bundle pattern (`standards/README.md` → "Bundle anatomy"): a normative `README.md`, an `adopt.md` runbook, copy-adopt `templates/`, a dogfooded `examples/` doc, a `resources/` rationale file, adopt-engine registration, tests, and a v4.3.0 release.

Task provenance: TODO.md "CLI Documentation Standard — integrate as a fully adoptable standard" (Phases 0–8; Phase 0 done in `9c4e0e4`, editorial quick-win done in `e38678c`). This spec is the system of record for the design; the TODO phases were its scope input.

## Decisions (locked during brainstorming)

1. **Fully adoptable standard, not a reference-only draft** — the sixth registered standard alongside Markdown Frontmatter, ADR, Python Tooling SSOT, Markdown Tooling, and Project Specification (TODO decision 2026-07-07).
2. **Id = `cli-documentation`** — the content governs CLI usage documentation, not CLI frameworks. Bundle dir renames `standards/cli-framework/` → `standards/cli-documentation/`; registry accessor `cli_documentation_default`; config key `cli_documentation`; adopt CLI arg `cli-documentation`.
3. **Full bundle explosion** — the monolith splits across `README.md` (normative), `adopt.md` (runbook), `templates/` (scaffolds), `examples/` (dogfooded), `resources/research-notes.md` (parked rationale; precedent `project-spec/resources/tooling-notes.md`). The `[S##]` source register **stays in the README** (house parity with `python-tooling`/`python-coding`); the resources file holds narrative rationale only.
4. **Three-profile tiered mandate** — Script ⊂ Packaged ⊂ Packaged-deep, selected by distribution shape and a **recorded adopter judgment** on usage-reference maintainability, guided by scale signals (§1; revised per codex SA-001 — nesting level alone is a signal, never an automatic trigger). Man page is SHOULD-if-practical everywhere: packaging reality (deprecated `data_files`, `sys.prefix`-scoped wheels, no `MANPATH` guarantee) demotes it from a mandate.
5. **CI = guidance + copy-adopt template only in 1.0** — the README mandates the checks; `templates/cli-docs-check.yml` ships as a copy-adopt workflow; **no** reusable `workflow_call` surface. Mirrors DEC-9 (Prettier shipped copy-adopt first, gained an opt-in reusable workflow in v4.2.0 once proven).
6. **Adopt materializes scaffolds + fragment** — `docs/usage.md` scaffold, `.github/workflows/cli-docs-check.yml`, and the `cli_documentation: version: "1.0"` config fragment. The single-file README template stays manual-copy (script repos rarely run `adopt`).
7. **Full dogfood** — this repo ships a real `docs/usage.md` covering its **entire public installed-command set** (the `project-standards` CLI in full plus the six standalone console scripts, per §1's grouped-page provision — codex SA-NEW-001) and holds itself to the standard; `examples/usage.example.md` is a trimmed copy carrying example frontmatter.
8. **One spec, one plan** — the plan sequences content-authoring tasks before code tasks (markdown-tooling precedent). Single release: v4.3.0.
9. **Contract version = fully validated label** — `cli_documentation.version` is recognized end-to-end (registry.json, registry.py, validator), like `markdown_tooling` (per the SA-001 precedent: a bare config key with no code is silently inert and rejected as a design).

## Background: ground truth

| Artifact | State today |
| --- | --- | --- | --- | --- | --- | --- |
| `standards/cli-framework/cli-documentation-standards.md` | Research draft, mechanically cleaned (`e38678c`): citation artifacts stripped, `[n]` markers keyed to a single Sources register, junk URLs dropped, table/fence defects fixed. Content structure still research-shaped (Executive Summary / Bottom line / Observation-Inference-Recommendation). |
| `.project-standards.yml` | Interim `standards/cli-framework/**` exclude (Phase 0, `9c4e0e4`) — to be **deleted** by this work. |
| `docs/research/2026-07-07-cli-usage-docs-packaged-src-layout-python.md` | Packaged-half research (`bdab8e6`), `confidence: high`. Feeds §1, §2, and the packaged-CLI README section. |
| Adopt engine | `cli.py:_assert_registry_bundle_parity` hard-fails (exit 2) unless a version-tracked standard has BOTH a registry contract AND a `bundles/<id>/` manifest; `adopt/manifest.py:available_standards` auto-discovers bundle dirs. Registration is therefore all-or-nothing within one change. |
| CLI surface to dogfood | `pyproject.toml` registers **seven** console scripts: `project-standards` (primary; top-level `validate`, `fix`, `adopt`, `list` + the `spec` group's `validate | lint | extract | next | new | upgrade` — 11 leaf commands) plus six standalone single-purpose commands (`validate-frontmatter`, `validate-id`, `sync-vscode-colors`, `sync-standards-include`, `format-frontmatter`, `validate-references`), all public (downstream CI invokes `validate-frontmatter`et al. directly) (codex SA-NEW-001). Exit codes 0/1/2(/3 where applicable). **No`--version` on any entry point today** — added by this work (codex SA-002). Profile selection recorded as **Packaged\*\* (§8). |
| Adopt engine overwrite semantics | **Confirmed safe for scaffolds** (`adopt/engine.py:260`): existing targets are skipped unless `--force`; fragments are reported, never written. Resolves former Open Question 3. |
| `src/project_standards/README.md` | Active package/CLI reference (console scripts, module map, registry keys, bundle list, config examples) — will go stale unless repositioned (codex SA-NEW-002; §10). |

## Design

### 1. The three-profile ladder

Profiles select by distribution shape; each is a superset of the previous (project-spec tiering idiom).

| Profile | Selection criterion | MUST | SHOULD / MAY |
| --- | --- | --- | --- |
| **Script** | Single-file, run in place, no packaging | `--help` + `--version`; compact README (per template); documented exit codes | usage doc MAY; man page MAY |
| **Packaged** | Installed via `[project.scripts]` entry points; single-page usage reference remains maintainable (see selection signals below) | Script tier **plus**: `docs/usage.md` with the man-style section registry, covering **every leaf command**, `NAME`/`SYNOPSIS` keyed to the **entry-point name** (never the module path or filename); CI smoke test of the **installed** entry point | man page SHOULD-if-practical (generated, shipped via build-backend `shared-data`, documented as best-effort — wheels cannot reach the system `MANPATH`) |
| **Packaged, deep** | Adopter selects it when the single-page reference is no longer maintainable (see selection signals below) | Packaged tier, except the usage reference MUST be **generated** per-command (`docs/cli/<command>.md`, pip-style) from parser metadata (sphinx-click / mkdocs-click / sphinxcontrib-typer / sphinx-argparse-cli); hand-maintained per-command pages are prohibited; plus one shared-concepts page (common env vars, exit codes, config) | docs-site hosting MAY (open question, non-blocking) |

**Profile selection is a recorded adopter judgment** (exactly like project-spec profile choice), guided by signals, not validator-checked numbers. Signals that Packaged-deep is warranted: more than ~5–7 **top-level** subcommands; **or** a second nesting level **combined with** a leaf-command count large enough that the single page demonstrably drifts or becomes unnavigable. Nesting alone does not force the deep profile (codex SA-001: a small two-group CLI like `project-standards` — 2 groups, ~8 leaf commands — remains Packaged; the mandate that changes at deep is _generated, never hand-maintained_, and that trade-off only pays for itself at scale). The Packaged tier's "every leaf command" MUST is the guard that keeps a shallow profile choice from hiding undocumented commands.

Multi-entry-point packages (several `[project.scripts]` keys in one `pyproject.toml`): one usage-reference page per **installed command name** by default, shared concepts factored into one cross-referenced page. **Grouped-page provision** (codex SA-NEW-001): closely related single-purpose commands from one distribution MAY share a combined reference page — or the primary command's usage doc — provided **each installed command gets its own complete entry** (`NAME`, `SYNOPSIS`, `OPTIONS`, `EXIT STATUS`), the man-page precedent for grouped related commands. Every `[project.scripts]` key is a public command unless the adopter explicitly classifies it as internal, in writing, in the usage doc.

### 2. Cross-cutting normative rules

Profile-independent, rewritten from research prose into requirement language:

- **One synopsis notation system per document** — GitHub CLI style (`<arg>`, `[arg]`, `{a \| b}`, `...`); never mixed with classic man-page typography. Pipes inside table cells escaped `\|` (root cause of the draft's malformed table).
- **Man-style section registry** for usage docs: `NAME`, `SYNOPSIS`, `DESCRIPTION`, `OPTIONS`, `EXIT STATUS`, `ENVIRONMENT`, `FILES`, `EXAMPLES`, `NOTES`/`CAVEATS`, `SEE ALSO` (+ optional `STANDARDS`, `HISTORY`).
- **Option-entry contract** — every documented option states spelling, value syntax, meaning, default, allowed values, exclusions/dependencies, scope, safety impact, env/config interaction, since/deprecated (where applicable).
- **Help-text boundary** — `--help` is concise orientation (usage line, common flags, 1–3 examples, pointer to full docs); the usage doc is the exhaustive contract. Help is generated from the parser, never hand-written separately.
- **Task-first, copy-paste-safe examples** — safety-biased (`--dry-run` before destructive), clearly fake placeholders for credentials/hosts/paths.
- **Exit codes enumerated** with conditions; `2` reserved for usage errors where the parser stack does that naturally (argparse default).
- **`prog` discipline** — `__main__.py` and the entry point call the same `main()`; `prog` pinned to the entry-point name so `python -m pkg` and the installed command agree in help output.
- **CI snapshot rules** — normalize `NO_COLOR` and terminal width before comparing help output (Python 3.14 argparse colors by default; Click rewraps by width); never assert on argparse section headings (drift across Python versions).
- **Accessibility & localization** — no color-only meaning; `NO_COLOR` supported; prose translates, command surface (names, options, placeholders, shell examples, env-var names) never does.
- **Evidence convention** — source-backed facts cite `[S##]` against the README's dated Source register; policy decisions are labeled as local standards.

### 3. Content→destination mapping (exploding the monolith)

| Current draft content | Destination |
| --- | --- |
| Four-artifact model, section registry, notation, help boundary, option contract, example style, exit/env/`NO_COLOR`/localization policies | `README.md` — as MUST/SHOULD/MAY rules (§2) |
| Packaged-half findings (entry points, man-page limits, generated docs, installed smoke test) | `README.md` — new packaged-CLI section, cited to the research report |
| Canonical usage-doc template, compact single-file README template (in-doc scaffolds) | `templates/usage-doc.md`, `templates/readme-single-file.md`; option-entry and example snippet blocks fold into the usage template |
| CI-check table + drift guidance | `README.md` (mandated checks) + `adopt.md` (how-to-comply) + `templates/cli-docs-check.yml` |
| Authoring/review checklist | `adopt.md` |
| Standards landscape, tooling comparisons, Observation→Inference→Recommendation rationale | `resources/research-notes.md` (+ pointers to both `docs/research/` reports) |
| Curated Sources register | `README.md` Source register, re-keyed `[n]` → `[S##]` |

The draft file itself is consumed by the rewrite and deleted (its content lives on across the bundle; git history preserves the original).

### 4. `README.md` section outline

House parity (numbered, ToC, frontmatter `doc_type: reference`):

Evidence convention · Requirement language (RFC 2119) · Version assumptions (Python 3.14 argparse behaviors, tool versions as template defaults to recheck) · 1 Purpose · 2 Scope & sibling relations (Markdown Tooling still formats the docs; Python Tooling owns the toolchain; Project Spec owns pre-implementation definition; frontmatter per Markdown Frontmatter where docs are managed) · 3 Profiles (§1 ladder + selection guidance) · 4 Usage-doc structure & notation · 5 Help-text boundary · 6 Option entries · 7 Examples · 8 Packaged CLIs (entry points, `prog` discipline, man-page best-effort, generated per-command docs, multi-entry-point layout) · 9 CI drift prevention (mandated checks + snapshot rules) · 10 Accessibility & localization · 11 Templates · 12 Adoption · 13 Exceptions process · 14 Update process / review cadence · 15 Source register.

### 5. Bundle layout

```text
standards/cli-documentation/
├── README.md                  # governing standard (frontmatter-validated)
├── adopt.md                   # runbook, doc_type: runbook (validated)
├── templates/                 # frontmatter-excluded (existing standards/**/templates/** glob)
│   ├── usage-doc.md           # canonical usage-doc scaffold (placeholders)
│   ├── readme-single-file.md  # compact script README scaffold
│   └── cli-docs-check.yml     # copy-adopt CI workflow: fresh install + installed --help smoke, NO_COLOR/width-normalized
├── examples/
│   └── usage.example.md       # trimmed copy of this repo's real usage doc (validated, real frontmatter)
└── resources/
    └── research-notes.md      # parked rationale + landscape (validated)
```

The Phase-0 interim exclude (`standards/cli-framework/**` in `.project-standards.yml`) is deleted in the same change; the four prose docs validate.

### 6. `adopt.md` (runbook)

Modeled on `standards/markdown-tooling/adopt.md` (closest doc-heavy copy-adopt analog). Contents: profile selection → what `adopt` materializes vs what is copied manually → filling the usage scaffold (entry-point name, section registry) → wiring the CI workflow template → the authoring/review checklist → conformance summary per profile.

### 7. Adopt-engine plumbing

Mechanical mirror of `markdown_tooling`:

- `registry.json` + `src/project_standards/registry.py`: `cli_documentation` contract `1.0`, accessor `cli_documentation_default`, version source.
- `src/project_standards/cli.py`: id added to `_REGISTRY_STANDARD_IDS` and the `_contract_version` dispatch map.
- `src/project_standards/bundles/cli-documentation/adopt.toml`: three artifacts — `docs/usage.md` scaffold (`kind = "file"`, source `templates/usage-doc.md`), `.github/workflows/cli-docs-check.yml` (`kind = "file"`), `cli_documentation: version: "1.0"` (`kind = "fragment"`). Bundle copies byte-identical to `standards/` sources (dogfood expectation enforced by existing manifest tests).
- `.project-standards.yml`: `cli_documentation: version: "1.0"` contract block (self-adoption) **and** `docs/usage.md` added to the frontmatter include globs (codex SA-003).

**Overwrite semantics (verified, was Open Question 3):** the engine already skips existing targets unless `--force` (`adopt/engine.py:260`, reported as "Skipped (already present)"), and fragments are reported, never written — scaffold materialization cannot clobber a consumer's real `docs/usage.md`. No engine change needed; the plan's adopt test asserts created-on-fresh / skipped-on-existing / fragment-reported behavior for this bundle.

### 8. Dogfood

- **Profile selection (recorded here per §1):** `project-standards` selects **Packaged**. Rationale: 2 command groups, 11 leaf commands, single-page reference maintainable; the deep profile's generated-pages trade-off does not pay for itself at this size (codex SA-001).
- **Public installed-command set (codex SA-NEW-001):** all seven `[project.scripts]` keys are public — the six standalone commands are consumer-facing (downstream CI invokes `validate-frontmatter` directly; none are classified internal). Documentation obligation under §1's grouped-page provision: `docs/usage.md` documents `project-standards` in full (**all 11 leaf commands**) plus a **Standalone commands** section giving each of the six its own complete entry (`NAME`, `SYNOPSIS`, `OPTIONS`, `EXIT STATUS`), cross-referenced to unified equivalents where one exists (e.g. `validate-frontmatter` ↔ `project-standards validate`).
- **`--version` is added to every installed command** (shared helper sourcing `importlib.metadata`) — the standard's Script-tier MUST, which no entry point currently satisfies (codex SA-002).
- Environment variables: enumerate what each command actually reads, if anything — verified during authoring.
- The usage doc carries canonical frontmatter (`doc_type: reference`) and is **added to the validator's include globs** in `.project-standards.yml` — without that include the acceptance command passes vacuously (codex SA-003).
- `examples/usage.example.md` derived from the real usage doc (trimmed; example frontmatter).
- **Installed-wrapper smoke tests** (codex SA-005 + SA-NEW-001): build the wheel, install it into a throwaway venv, then via the **installed wrappers** with `NO_COLOR` set: (a) loop over **all seven** `[project.scripts]` keys asserting `<cmd> --help` and `<cmd> --version` exit `0`; (b) deep-smoke `project-standards` with one nested subcommand (e.g. `spec validate --help`). Extends the wheel-building idiom in `tests/test_adopt_packaging.py`, not a plain dev-env subprocess (which misses broken entry-point metadata and `prog` drift). Lives in the pytest suite, so the existing `check` job covers it — no new CI workflow surface. (Consumers get the workflow template; this repo's equivalent lives in its test suite.)
- **Inventory-parity guard** (codex suggestion): a test comparing the `[project.scripts]` keys and the `project-standards` parser leaves against the entries present in `docs/usage.md`, so an added command cannot silently ship undocumented.

### 9. Tests

- Adopt-manifest coverage in the `tests/test_adopt_manifest.py` idiom, **including updating its released-standards expectation from four to five**.
- **Explicit byte-identity mappings** (codex SA-004 — the existing `tests/test_adopt_dogfood.py` `_DOGFOOD` map is hardcoded per standard and will not pick the new bundle up automatically): each shipped artifact (`templates/usage-doc.md`, `templates/cli-docs-check.yml`, and any other bundled copy) mapped to its `src/project_standards/bundles/cli-documentation/` twin.
- Registry↔bundle parity coverage: the new id present on both sides.
- **Contract-version validator tests** (codex suggestion): known `cli_documentation.version` accepted silently; unknown version exits `2`; non-string version exits `2`; registry default present; the dogfood config selects `1.0`.
- Frontmatter validation picks up README, adopt.md, examples, resources (templates excluded) **and provably includes `docs/usage.md`** (validated-file count or an explicit-path assertion — codex SA-003).
- Installed-wrapper smoke tests (§8): wheel → throwaway venv → all seven wrappers `--help`/`--version` exit `0`; deep-smoke `project-standards` with one nested subcommand.
- Inventory-parity guard (§8): `[project.scripts]` keys + `project-standards` parser leaves vs `docs/usage.md` entries.
- Adopt-behavior test for this bundle: created on fresh target, skipped on existing target, fragment reported (per §7 verified semantics).
- Wheel-content check that the `cli-documentation` bundle files and manifest ship in the wheel (extends `tests/test_adopt_packaging.py`).
- Existing gate stays green: ruff, basedpyright, pytest + coverage, pip-audit, `tests/coherence` (new prose is part of the lint corpus).

### 10. Repo touchpoints (multi-file change list)

| File | Change |
| --- | --- |
| `standards/cli-framework/` → `standards/cli-documentation/` | rename + full bundle explosion (§3, §5); draft file consumed |
| `.project-standards.yml` | delete interim exclude; add `cli_documentation` contract block; add `docs/usage.md` to include globs |
| `src/project_standards/registry.py`, `registry.json`, `cli.py` + the six standalone `main()` modules | contract registration (§7); `--version` on every installed command via a shared helper (§8) |
| `src/project_standards/README.md` | reposition as **implementation-internals reference** linking to `docs/usage.md` as the authoritative usage reference; refresh its command/registry/config/bundle facts (new standard, `cli_documentation` key, `--version`) so the repo does not ship two conflicting active CLI references (codex SA-NEW-002) |
| `src/project_standards/bundles/cli-documentation/` | manifest + artifact copies (§7) |
| `docs/usage.md` | new dogfood doc (§8) |
| `tests/` | new coverage (§9) |
| `standards/README.md` | table row (Bundle + Adopt link); bundle-anatomy note updated (README-only bucket currently says "currently just python-coding/"; also gains the `resources/` mention if absent) |
| root `README.md` | intro enumeration ("defines five" → six), ToC, directory tree, dedicated subsection, adoption map |
| root `CLAUDE.md` | Purpose line: six standards, add to enumerated list |
| `docs/handoff/architecture.md` | component graph standards list; backlog item cleared |
| `docs/handoff/specs-plans.md` | spec + plan pointer rows |
| `STATUS.md`, `docs/handoff/state.md` | at-a-glance state at release |
| `CHANGELOG.md`, `UPGRADING.md` | v4.3.0 entry; upgrading note: no action for existing adopters, with one explicit caveat — the validator now recognizes `cli_documentation.version`, so a consumer config that already carried that key with an unrecognized value (previously ignored) would newly exit `2` (codex non-blocking finding; no known such configs) |
| `TODO.md` | integration phases closed out at release |

### 11. Acceptance criteria

#### Bundle & docs

- `standards/cli-documentation/` matches §5 exactly. No **active** `cli-framework/` reference remains — code, config, bundle manifests, workflows, and current consumer-facing docs (root README, standards index, CLAUDE.md, architecture, state) are clean; **historical provenance references are exempt** (specs, research reports, codex-review audits, TODO phase history, session logs) (codex SA-006). Verification: `rg -n "cli-framework"` sweep, classifying each hit as active-stale (fail) or historical-provenance (pass).
- `README.md` is normative (requirement language throughout; no Executive Summary / Bottom line / Observation-Inference-Recommendation residue), with `[S##]` register and no orphaned `[n]` markers.
- Byte-level check: no Unicode private-use-area characters in any bundle file (`grep -P '[\x{E000}-\x{F8FF}]'` clean) — the research-export fingerprint.

#### Registration

- `project-standards adopt cli-documentation` materializes exactly the three §7 artifacts; `_assert_registry_bundle_parity` passes; unknown `cli_documentation.version` values exit `2`.

#### Dogfood

- `docs/usage.md` exists, conforms to the Packaged profile — all 11 `project-standards` leaf commands documented **plus a complete entry for each of the six standalone commands** (codex SA-NEW-001) — and `uv run validate-frontmatter --config .project-standards.yml` passes with the interim exclude deleted **and demonstrably validates `docs/usage.md`** (it appears in the validated-file set) (codex SA-003).
- Every installed command supports `--version`, prints the release version, and exits `0` (codex SA-002 + SA-NEW-001).
- The installed-wrapper smoke tests pass via the normal pytest gate: all seven wrappers `--help`/`--version`, plus one nested `project-standards` subcommand (codex SA-005 + SA-NEW-001).
- The inventory-parity guard passes: no `[project.scripts]` key or `project-standards` parser leaf is absent from `docs/usage.md`.
- `src/project_standards/README.md` is repositioned/refreshed per §10 with no stale command, registry, config, or bundle facts, and names `docs/usage.md` as the authoritative usage reference (codex SA-NEW-002).

#### Gate green (repo non-negotiable)

- `uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit && uv run pytest tests/coherence` all pass; prettier + markdownlint clean.

#### Release

- v4.3.0 tagged and released per `meta/versioning.md`; six doc surfaces updated (§10); `v4` moving tag advanced.

## Versioning & release interplay

New adoptable standard = **minor** at minimum per `meta/versioning.md` → **v4.3.0**. The `cli_documentation` contract starts at `1.0`. Purely additive for existing adopters (no UPGRADING action). Consumers reference new surfaces `@v4`.

## Non-goals

- No reusable `workflow_call` CI workflow in 1.0 (decision 5; revisit on demand like Prettier's DEC-9 → v4.2.0 path).
- No doc↔parser parity tooling shipped — parity checking is parser-specific; the standard mandates the check as guidance, adopters implement per their stack.
- No docs-site hosting mandate or tooling (open question 1).
- No localization tooling — the standard states the boundary only.
- No new validator for usage-doc structure (the frontmatter validator covers metadata only; structural validation of usage docs is a possible future contract bump, not 1.0).

## Open questions

| # | Question | Status |
| --- | --- | --- |
| 1 | Versioned-docs-hosting pattern for CLI reference pages (RTD selector vs `mike` vs single-version static) | Non-blocking; noted in `resources/research-notes.md`; research report Open Question 1 |
| 2 | Will the PEP 772 Packaging Council formalize man-page/OS-integration installation? | Non-blocking; revisit near any proposal; research report Open Question 2 |
| 3 | ~~Adopt-engine overwrite semantics for scaffold artifacts~~ | **Resolved** during codex round 2: engine skips existing targets unless `--force` (`adopt/engine.py:260`); fragments reported, never written (§7) |

## Audit trail

- 2026-07-07 — brainstorming complete: 4 clarifying decisions (profile tiering, CI shipping, adopt set, dogfood depth) + spec shape (one spec, one plan) ratified via bounded questions; design sections A (content) and B (bundle/plumbing/dogfood/release) approved.
- 2026-07-07 — codex spec-review round 1 (`docs/codex-reviews/2026-07-07-014246-codex-spec-review-round1.md`): verdict "needs major correction", SA-001..SA-006. All six addressed: profile-selection rule rewritten (nesting = signal, not trigger; "every leaf command" guard added; dogfood profile recorded as Packaged with rationale) [SA-001]; `--version` added to CLI scope + acceptance [SA-002]; `docs/usage.md` added to include globs with provable validation [SA-003]; explicit byte-identity test mappings + released-standards count update [SA-004]; smoke test specified as wheel → throwaway venv → installed wrapper [SA-005]; `cli-framework` sweep narrowed to active references with historical-provenance exemption [SA-006]; plus contract-version validator tests and the UPGRADING caveat from the non-blocking notes.
- 2026-07-07 — codex spec-review round 2 (`docs/codex-reviews/2026-07-07-014957-codex-spec-review-round2.md`): SA-001..SA-006 confirmed resolved; two new findings, both addressed. [SA-NEW-001] the package ships **seven** console scripts and the `project-standards` leaf inventory was wrong (11 leaves, incl. top-level `validate`/`fix`/`list`): ground truth corrected; §1 gained the grouped-page provision + public-unless-classified-internal rule; dogfood now covers the full installed-command set, `--version` on every wrapper, all-wrapper smoke, and an inventory-parity guard. [SA-NEW-002] `src/project_standards/README.md` added to touchpoints — repositioned as implementation-internals reference with `docs/usage.md` authoritative. Bonus: round-2 evidence resolved Open Question 3 (engine skip-on-existing at `adopt/engine.py:260`; fragments never written).
- Inputs: TODO.md integration phases (scope), `e38678c` editorial cleanup, `bdab8e6` packaged-half research.
