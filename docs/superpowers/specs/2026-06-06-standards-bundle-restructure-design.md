# Design: Per-standard bundle restructure for `project-standards`

**Date:** 2026-06-06 **Status:** approved (brainstorming complete; awaiting implementation plan) **Author:** session 2026-06-06

## Table of Contents

- [Design: Per-standard bundle restructure for `project-standards`](#design-per-standard-bundle-restructure-for-project-standards)
  - [Problem / Goal](#problem--goal)
  - [Decisions (locked during brainstorming)](#decisions-locked-during-brainstorming)
  - [Invariants — the consumer contract (must NOT change)](#invariants--the-consumer-contract-must-not-change)
  - [Target layout](#target-layout)
    - [Bundle anatomy (the scale pattern — documented in `standards/README.md`)](#bundle-anatomy-the-scale-pattern--documented-in-standardsreadmemd)
  - [Migration map (all moves via `git mv` to preserve history)](#migration-map-all-moves-via-git-mv-to-preserve-history)
  - [Tooling \& contract updates](#tooling--contract-updates)
    - [Functional changes (affect behavior)](#functional-changes-affect-behavior)
    - [Accuracy sweeps (no behavior change; required for a self-consistent standards repo)](#accuracy-sweeps-no-behavior-change-required-for-a-self-consistent-standards-repo)
  - [Index, `adopt.md`, and `meta/` content](#index-adoptmd-and-meta-content)
    - [`standards/README.md` (index)](#standardsreadmemd-index)
    - [`adopt.md` per bundle (deliberately unequal — each matches its real adoption model)](#adoptmd-per-bundle-deliberately-unequal--each-matches-its-real-adoption-model)
    - [`meta/`](#meta)
  - [Verification plan](#verification-plan)
  - [Release framing](#release-framing)
  - [Non-goals](#non-goals)
  - [Open implementation details (resolve in the plan, not blocking design)](#open-implementation-details-resolve-in-the-plan-not-blocking-design)

## Problem / Goal

At the next release (the locked `2.0.0`), this repo governs **three** standards — Markdown Frontmatter, ADR, and Python Tooling SSOT. Today the human-readable surface is organised by _artifact type_, not by _standard_: five files sit flat under `standards/` (the three governing docs plus two meta docs — `versioning.md`, `adoption.md`), while each standard's templates and examples are scattered across flat top-level `templates/` and `examples/` trees. A reader cannot see "everything that belongs to the ADR standard" in one place, and a consumer cannot adopt one standard in isolation without wading through the others.

The goal is to restructure so the three standards are **clearly separated for both readers and consumers**, satisfying four outcomes the user selected together:

1. **Reader browse-ability** — one standard's pieces co-located.
2. **Independent adoption** — adopt just one standard with its own scoped entry.
3. **Scale for more standards** — a repeatable, documented per-standard pattern.
4. **Tidy meta vs governing** — separate the two meta docs from the governed set.

The complication: this repo ships **products**, not just docs. Downstream repos install the `validate-frontmatter` console script via `uv tool install git+...@<tag>` and call two **reusable workflows** pinned by exact filename. That consumer contract must be preserved byte-for-byte while the documentation surface is reorganised.

## Decisions (locked during brainstorming)

1. **Approach = full per-standard bundles** (chosen over index-over-flat and a docs-only hybrid). Each standard becomes a self-contained folder; the top-level `templates/` and `examples/` trees are dissolved into the bundles.
2. **Python Tooling stays doc-only.** Its scaffolds (pyproject baseline, `check.yml`, `AGENTS.md`/`CLAUDE.md` blocks, `.lsp.json`, `scripts/check.py`, `.vscode/*`) remain inline fenced code in the standard doc — **not** extracted into template files. The bundle pattern must therefore degrade gracefully to a README-only (+ `adopt.md`) bundle.
3. **Meta area + per-bundle `adopt.md`.** `versioning.md` (this repo's own release contract) moves to a `meta/` area outside the governing set. Each bundle gets its own `adopt.md`; the existing rich validator onboarding (`adoption.md`) stays with the frontmatter bundle and is reused by ADR.
4. **The standard file inside each bundle is `README.md`** (GitHub auto-renders it on folder open), not a descriptive `adr.md`-style name.
5. **The Python bundle folder is `python-tooling`** (short), though the doc's frontmatter `id` stays `python-tooling-ssot-standard`.
6. **Doc-type scaffolds belong to the frontmatter bundle.** `concept/note/runbook/research/spec` templates and examples demonstrate the `doc_type` + frontmatter profile, which the Frontmatter Standard owns. ADR's scaffolds live in the ADR bundle even though ADR builds on frontmatter.
7. **The reorg is not independently consumer-breaking** and rides inside the already-locked `2.0.0`; it does not force a major on its own (see Release framing).

## Invariants — the consumer contract (must NOT change)

Verified by reading the workflow bodies and the validator: none of these have any coupling to `standards/`, `templates/`, or `examples/` paths.

- The two **reusable workflows**, pinned by exact filename: `.github/workflows/validate-markdown-frontmatter.yml` and `.github/workflows/lint-markdown.yml` (`workflow_call`, referenced as `…@v1`). Renaming = breaking.
- The **Python package** `project_standards`, its `validate-frontmatter` console-script entry point, and the **bundled schema** at `src/project_standards/schemas/markdown-frontmatter.schema.json` (the path is the schema's own `$id`).
- All published **git tags** (`v1.x`, the moving `v1`).
- `.github/workflows/check.yml` and `format.yml` are dogfood-only (not `workflow_call`).

## Target layout

```text
standards/
├── README.md                       # INDEX (no frontmatter; landing page). 3-row table + bundle anatomy + meta pointer.
├── markdown-frontmatter/
│   ├── README.md                   # ← standards/markdown-frontmatter.md
│   ├── adopt.md                    # ← standards/adoption.md (rich validator onboarding; ADR reuses it)
│   ├── templates/                  # ← frontmatter-minimal.yml, frontmatter-standard.yml,
│   │                               #    concept.md, note.md, runbook.md, research.md, spec.md, repo-pages/…
│   └── examples/                   # ← concept.example.md, note.example.md, runbook.example.md
├── adr/
│   ├── README.md                   # ← standards/adr.md
│   ├── adopt.md                    # NEW (thin): rides frontmatter workflow + markdown.adr block + template pointer
│   ├── templates/                  # ← adr.md, adr-minimal.md, adr-bare.md, adr-bare-minimal.md
│   └── examples/                   # ← adr.example.md
└── python-tooling/
    ├── README.md                   # ← standards/python-tooling-ssot-standard.md (scaffolds stay inline)
    └── adopt.md                    # NEW (thin, different model): copy scaffolds + run the gate; no reusable workflow

meta/
└── versioning.md                   # ← standards/versioning.md (this repo's own release contract — not governed)

# UNCHANGED: src/project_standards/**, .github/workflows/**, pyproject.toml, scripts/, all git tags
```

### Bundle anatomy (the scale pattern — documented in `standards/README.md`)

```text
standards/<standard-id>/
├── README.md      # REQUIRED — the governing standard itself
├── adopt.md       # REQUIRED — how to adopt THIS standard (may defer shared steps to another bundle)
├── templates/     # OPTIONAL — copy-paste scaffolds (placeholders; never frontmatter-validated)
└── examples/      # OPTIONAL — validated worked examples (real frontmatter; dogfooded)
```

Adding a 4th standard = copy the shape. Optional folders simply don't appear when unused (Python tooling is the degenerate README-only case).

## Migration map (all moves via `git mv` to preserve history)

**→ `standards/markdown-frontmatter/`**

| From | To |
| --- | --- |
| `standards/markdown-frontmatter.md` | `…/README.md` |
| `standards/adoption.md` | `…/adopt.md` |
| `templates/frontmatter-minimal.yml`, `frontmatter-standard.yml` | `…/templates/` |
| `templates/{concept,note,runbook,research,spec}.md` | `…/templates/` |
| `templates/repo-pages/README.directory.template.md` | `…/templates/repo-pages/` |
| `examples/{concept,note,runbook}.example.md` | `…/examples/` |

**→ `standards/adr/`**

| From | To |
| --- | --- |
| `standards/adr.md` | `…/README.md` |
| `templates/adr.md`, `adr-minimal.md`, `adr-bare.md`, `adr-bare-minimal.md` | `…/templates/` |
| `examples/adr.example.md` | `…/examples/` |

**→ `standards/python-tooling/`**

| From                                        | To            |
| ------------------------------------------- | ------------- |
| `standards/python-tooling-ssot-standard.md` | `…/README.md` |

**→ `meta/`**

| From                      | To                   |
| ------------------------- | -------------------- |
| `standards/versioning.md` | `meta/versioning.md` |

**New files:** `standards/README.md` (index + anatomy), `standards/adr/adopt.md`, `standards/python-tooling/adopt.md`. **Disappears:** top-level `templates/` and `examples/` (fully absorbed).

## Tooling & contract updates

### Functional changes (affect behavior)

1. **`.project-standards.yml` dogfood globs.**
   - `include`: `CHANGELOG.md`, `standards/**/*.md`, `meta/**/*.md` (drop the now-redundant top-level `examples/**/*.md`; examples are caught by `standards/**/*.md`).
   - `exclude`: add `standards/**/templates/**` (placeholders — load-bearing; without it the `YYYY-MM-DD`/`replace-with-stable-id` placeholders fail validation) and `standards/README.md` (navigation landing page — same rationale as the existing root-`README.md` exclude). Bundle `README.md` standard docs and `adopt.md` files **do** validate.

2. **`tests/test_validate_frontmatter.py` example discovery (line ~819).** `EXAMPLE_FILES = sorted((_REPO_ROOT / "examples").glob("*.md"))` → `sorted(_REPO_ROOT.glob("standards/*/examples/*.md"))`; update the "expected worked examples under examples/" assertion message. The non-empty guard (`test_examples_directory_is_not_empty`) keeps protecting the contract; expected count = 4 (3 frontmatter + 1 ADR).

### Accuracy sweeps (no behavior change; required for a self-consistent standards repo)

| File(s) | Edit |
| --- | --- |
| Root `README.md` | Rewrite layout / Standards / Consuming sections → bundles, per-bundle `adopt.md` links, `meta/`. Largest doc edit. |
| `docs/handoff/architecture.md` | Update the component tree to the bundle layout. |
| Inter-doc links inside moved docs | Fix `standards/…`, `templates/…`, `examples/…` links to new relative paths (e.g. ADR→versioning, adopt→ADR). |
| `src/project_standards/validate_frontmatter.py` (docstrings), `…/schemas/*.json` (`description`) | Repoint `standards/adr.md` → `standards/adr/README.md`, etc. **The schema `$id` line stays.** |
| `tests/README.md`, `tests/test_markdownlint_config.py` (comment) | Update `examples/` and `standards/*.md` references. |
| `AGENTS.md`, `CLAUDE.md` | Sweep for stale `standards/` / `templates/` paths (do **not** add frontmatter to these). |
| `CHANGELOG.md` | 2.0.0 entry: docs reorg (BREAKING for doc deep-links; consumer workflow + validator + schema contract unchanged). |

**Verify during implementation:** `.markdownlint-cli2.jsonc` for any `templates/`/`examples/` path ignores that must follow the move. **Confirmed unchanged:** `.github/workflows/**`, `pyproject.toml` (no standards-path coupling; schema ships from `src/`), `scripts/check.py`, git tags.

## Index, `adopt.md`, and `meta/` content

### `standards/README.md` (index)

No frontmatter (excluded landing page). Contains: a one-line intro, a 3-row table (standard · one-liner · bundle link · adopt link), the **bundle anatomy** block above, and a labelled pointer to `meta/` as _non-governing_.

### `adopt.md` per bundle (deliberately unequal — each matches its real adoption model)

- **`markdown-frontmatter/adopt.md`** (heavy; relocated `adoption.md`): full validator onboarding — `.project-standards.yml`, calling `validate-markdown-frontmatter.yml@v1`, field rules, worked example, compliance checklist. The canonical "how the validator works" doc.
- **`adr/adopt.md`** (thin): "ADR rides the frontmatter validator — adopt that first (`../markdown-frontmatter/adopt.md`)," then ADR-only deltas: do **not** exclude `docs/decisions/**`; the opt-in `markdown.adr.require_sections` block; "copy a template from `./templates/`"; ID/filename convention pointer to README. No workflow of its own.
- **`python-tooling/adopt.md`** (thin, _different_ model): not validator-enforced, no reusable workflow. Adoption = copy the inline scaffolds (README §6/§13/§15/§16–17/§18), run the verification gate, follow the migration guide (README §21).

### `meta/`

`versioning.md` keeps its frontmatter and validates via the new `meta/**/*.md` include. The root README "Versioning" section and the standards index both link it, labelled "this repo's own release contract, not a governed standard."

## Verification plan

- Full toolchain gate: `uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit`.
- Dogfood: `uv run validate-frontmatter --config .project-standards.yml` — validates the 3 bundle READMEs + the 3 `adopt.md`s + 4 examples + `meta/versioning.md`; excludes templates + index.
- `npx prettier --check .` clean; markdownlint clean.
- Test `EXAMPLE_FILES` discovers exactly the 4 relocated examples; non-empty guard fires.
- **Dead-link sweep:** grep the repo for surviving `standards/*.md`, `templates/`, `examples/` paths that no longer resolve.

## Release framing

Under this repo's own versioning contract ("the contract is the consumer's _validation outcome_"), moving docs changes nothing a consumer depends on — config schema, workflow names, validator entry point, and bundled schema are untouched. A repo pinned `@v1` is wholly unaffected (old tags immutable); a repo moving to `@v2` sees identical validation behavior. The restructure therefore **does not force a major on its own** — it rides inside the already-locked `2.0.0` (whose break is the `requires-python` 3.13 bump). One major absorbs both; there is no second migration for consumers.

Handoff docs to update at release: `architecture.md` (tree), `deployed.md` / `state.md` (note the reorg in 2.0.0), and `conventions.md` if it records the layout.

## Non-goals

- Extracting Python-tooling scaffolds into template/example files (decided: doc-only for now).
- Renaming or restructuring the validator package, the reusable workflows, or the bundled schema location.
- Changing the validator's behavior, the schema contract, or the config schema shape.
- Adopting pre-commit hooks or repo-root-relative link enforcement (separate standing backlog items).

## Open implementation details (resolve in the plan, not blocking design)

- Exact relative-link rewrites inside each moved doc (depth changes from `standards/X.md` to `standards/X/README.md`).
- Whether `meta/` needs its own `README.md` (lean: no; the standards index links `meta/versioning.md` directly).
- Final wording of the three `adopt.md` files and the index table.
