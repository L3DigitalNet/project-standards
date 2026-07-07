# Design: CLI Documentation Standard

**Date:** 2026-07-07 **Status:** approved (brainstorming complete; awaiting codex spec-review) **Author:** session 2026-07-07

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
4. **Three-profile tiered mandate** — Script ⊂ Packaged ⊂ Packaged-deep, selected by distribution shape and subcommand-tree size (§1). Man page is SHOULD-if-practical everywhere: packaging reality (deprecated `data_files`, `sys.prefix`-scoped wheels, no `MANPATH` guarantee) demotes it from a mandate.
5. **CI = guidance + copy-adopt template only in 1.0** — the README mandates the checks; `templates/cli-docs-check.yml` ships as a copy-adopt workflow; **no** reusable `workflow_call` surface. Mirrors DEC-9 (Prettier shipped copy-adopt first, gained an opt-in reusable workflow in v4.2.0 once proven).
6. **Adopt materializes scaffolds + fragment** — `docs/usage.md` scaffold, `.github/workflows/cli-docs-check.yml`, and the `cli_documentation: version: "1.0"` config fragment. The single-file README template stays manual-copy (script repos rarely run `adopt`).
7. **Full dogfood** — this repo ships a real `docs/usage.md` for the `project-standards` CLI and holds itself to the standard; `examples/usage.example.md` is a trimmed copy of it carrying example frontmatter.
8. **One spec, one plan** — the plan sequences content-authoring tasks before code tasks (markdown-tooling precedent). Single release: v4.3.0.
9. **Contract version = fully validated label** — `cli_documentation.version` is recognized end-to-end (registry.json, registry.py, validator), like `markdown_tooling` (per the SA-001 precedent: a bare config key with no code is silently inert and rejected as a design).

## Background: ground truth

| Artifact | State today |
| --- | --- |
| `standards/cli-framework/cli-documentation-standards.md` | Research draft, mechanically cleaned (`e38678c`): citation artifacts stripped, `[n]` markers keyed to a single Sources register, junk URLs dropped, table/fence defects fixed. Content structure still research-shaped (Executive Summary / Bottom line / Observation-Inference-Recommendation). |
| `.project-standards.yml` | Interim `standards/cli-framework/**` exclude (Phase 0, `9c4e0e4`) — to be **deleted** by this work. |
| `docs/research/2026-07-07-cli-usage-docs-packaged-src-layout-python.md` | Packaged-half research (`bdab8e6`), `confidence: high`. Feeds §1, §2, and the packaged-CLI README section. |
| Adopt engine | `cli.py:_assert_registry_bundle_parity` hard-fails (exit 2) unless a version-tracked standard has BOTH a registry contract AND a `bundles/<id>/` manifest; `adopt/manifest.py:available_standards` auto-discovers bundle dirs. Registration is therefore all-or-nothing within one change. |
| CLI surface to dogfood | `project-standards` entry point with `spec` (validate/new/upgrade) and `adopt` subcommand groups; exit codes 0/1/2(/3 where applicable). Under the deep-tree threshold → Packaged profile. |

## Design

### 1. The three-profile ladder

Profiles select by distribution shape; each is a superset of the previous (project-spec tiering idiom).

| Profile | Selection criterion | MUST | SHOULD / MAY |
| --- | --- | --- | --- |
| **Script** | Single-file, run in place, no packaging | `--help` + `--version`; compact README (per template); documented exit codes | usage doc MAY; man page MAY |
| **Packaged** | Installed via `[project.scripts]` entry points; ≤ ~5–7 top-level subcommands; one nesting level | Script tier **plus**: `docs/usage.md` with the man-style section registry, `NAME`/`SYNOPSIS` keyed to the **entry-point name** (never the module path or filename); CI smoke test of the **installed** entry point | man page SHOULD-if-practical (generated, shipped via build-backend `shared-data`, documented as best-effort — wheels cannot reach the system `MANPATH`) |
| **Packaged, deep** | Above the subcommand threshold, or any second nesting level (subcommand groups) | Packaged tier, except the usage reference MUST be **generated** per-command (`docs/cli/<command>.md`, pip-style) from parser metadata (sphinx-click / mkdocs-click / sphinxcontrib-typer / sphinx-argparse-cli); hand-maintained per-command pages are prohibited; plus one shared-concepts page (common env vars, exit codes, config) | docs-site hosting MAY (open question, non-blocking) |

The subcommand threshold is stated as guidance ("roughly 5–7 top-level subcommands or any second nesting level"), not a validator-checked number — profile selection is a judgment the adopter records, exactly like project-spec profile choice.

Multi-entry-point packages (several `[project.scripts]` keys in one `pyproject.toml`): one usage-reference page per **installed command name**, shared concepts factored into one cross-referenced page.

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
- `.project-standards.yml`: `cli_documentation: version: "1.0"` contract block (self-adoption).

**Plan-time verification item:** confirm the adopt engine's behavior when a destination file already exists — a scaffold materialization must not clobber a consumer's real `docs/usage.md`. If the engine overwrites unconditionally, the manifest or engine needs a skip-if-exists mode for scaffold artifacts **before** this bundle ships; that finding would become a plan task, not a silent behavior change.

### 8. Dogfood

- Real `docs/usage.md` documenting the `project-standards` CLI (Packaged profile): entry-point name, `spec`/`adopt` subcommand groups, exit codes, environment variables (enumerate what the CLI actually reads, if anything — verified during authoring), task-first examples.
- `examples/usage.example.md` derived from it (trimmed; example frontmatter).
- Installed-entry-point smoke test in the pytest suite (subprocess `project-standards --help` + one subcommand, `NO_COLOR` set) rather than a new CI workflow — the existing `check` job runs pytest, so the standard's mandated check is satisfied without new workflow surface. (Consumers get the workflow template; this repo's equivalent lives in its test suite.)
- Frontmatter question resolved at plan time: whether `docs/usage.md` falls under the validator's include globs and therefore carries canonical frontmatter (expected: yes, `doc_type: reference`).

### 9. Tests

- Adopt-manifest test for the new bundle (byte-identical materialization + manifest validation) in `tests/test_adopt_manifest.py` idiom.
- Registry↔bundle parity coverage: the new id present on both sides.
- Frontmatter validation picks up README, adopt.md, examples, resources (templates excluded).
- Installed-entry-point smoke test (§8).
- Existing gate stays green: ruff, basedpyright, pytest + coverage, pip-audit, `tests/coherence` (new prose is part of the lint corpus).

### 10. Repo touchpoints (multi-file change list)

| File | Change |
| --- | --- |
| `standards/cli-framework/` → `standards/cli-documentation/` | rename + full bundle explosion (§3, §5); draft file consumed |
| `.project-standards.yml` | delete interim exclude; add `cli_documentation` contract block |
| `src/project_standards/registry.py`, `registry.json`, `cli.py` | contract registration (§7) |
| `src/project_standards/bundles/cli-documentation/` | manifest + artifact copies (§7) |
| `docs/usage.md` | new dogfood doc (§8) |
| `tests/` | new coverage (§9) |
| `standards/README.md` | table row (Bundle + Adopt link); bundle-anatomy note updated (README-only bucket currently says "currently just python-coding/"; also gains the `resources/` mention if absent) |
| root `README.md` | intro enumeration ("defines five" → six), ToC, directory tree, dedicated subsection, adoption map |
| root `CLAUDE.md` | Purpose line: six standards, add to enumerated list |
| `docs/handoff/architecture.md` | component graph standards list; backlog item cleared |
| `docs/handoff/specs-plans.md` | spec + plan pointer rows |
| `STATUS.md`, `docs/handoff/state.md` | at-a-glance state at release |
| `CHANGELOG.md`, `UPGRADING.md` | v4.3.0 entry; upgrading note = none required (purely additive) |
| `TODO.md` | integration phases closed out at release |

### 11. Acceptance criteria

#### Bundle & docs

- `standards/cli-documentation/` matches §5 exactly; no `cli-framework/` path remains anywhere in the repo (code, config, docs, workflows).
- `README.md` is normative (requirement language throughout; no Executive Summary / Bottom line / Observation-Inference-Recommendation residue), with `[S##]` register and no orphaned `[n]` markers.
- Byte-level check: no Unicode private-use-area characters in any bundle file (`grep -P '[\x{E000}-\x{F8FF}]'` clean) — the research-export fingerprint.

#### Registration

- `project-standards adopt cli-documentation` materializes exactly the three §7 artifacts; `_assert_registry_bundle_parity` passes; unknown `cli_documentation.version` values exit `2`.

#### Dogfood

- `docs/usage.md` exists, conforms to the Packaged profile, and `uv run validate-frontmatter --config .project-standards.yml` passes with the interim exclude deleted.
- The installed-entry-point smoke test passes via the normal pytest gate.

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
| 3 | Adopt-engine overwrite semantics for scaffold artifacts | **Plan-time verification item** (§7) — must be resolved before the bundle ships |

## Audit trail

- 2026-07-07 — brainstorming complete: 4 clarifying decisions (profile tiering, CI shipping, adopt set, dogfood depth) + spec shape (one spec, one plan) ratified via bounded questions; design sections A (content) and B (bundle/plumbing/dogfood/release) approved.
- Inputs: TODO.md integration phases (scope), `e38678c` editorial cleanup, `bdab8e6` packaged-half research.
