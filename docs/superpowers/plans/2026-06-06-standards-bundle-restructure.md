# Standards Bundle Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganise `standards/` so each governing standard (Markdown Frontmatter, ADR, Python Tooling SSOT) is a self-contained bundle, move `versioning.md` to `meta/`, and keep the consumer contract and the green gate intact.

**Architecture:** Per-standard bundle directories `standards/<name>/{README.md, adopt.md, templates/, examples/}`; the flat top-level `templates/`/`examples/` trees dissolve into the bundles. Enforcement artifacts (reusable workflows, the `project_standards` package, the bundled schema) do not move — only documentation files and their internal links/globs change. Spec: [`docs/superpowers/specs/2026-06-06-standards-bundle-restructure-design.md`](../specs/2026-06-06-standards-bundle-restructure-design.md).

**Tech Stack:** Markdown, YAML config (`.project-standards.yml`), the `validate-frontmatter` Python validator, pytest, Ruff/basedpyright/coverage/pip-audit gate, Prettier, markdownlint-cli2, `git mv`.

---

## Authoritative path mapping (the contract every task obeys)

| Old path | New path |
| --- | --- |
| `standards/markdown-frontmatter.md` | `standards/markdown-frontmatter/README.md` |
| `standards/adoption.md` | `standards/markdown-frontmatter/adopt.md` |
| `standards/adr.md` | `standards/adr/README.md` |
| `standards/python-tooling-ssot-standard.md` | `standards/python-tooling/README.md` |
| `standards/versioning.md` | `meta/versioning.md` |
| `templates/frontmatter-minimal.yml`, `frontmatter-standard.yml` | `standards/markdown-frontmatter/templates/` |
| `templates/{concept,note,runbook,research,spec}.md` | `standards/markdown-frontmatter/templates/` |
| `templates/repo-pages/README.directory.template.md` | `standards/markdown-frontmatter/templates/repo-pages/` |
| `templates/adr.md`, `adr-minimal.md`, `adr-bare.md`, `adr-bare-minimal.md` | `standards/adr/templates/` |
| `examples/{concept,note,runbook}.example.md` | `standards/markdown-frontmatter/examples/` |
| `examples/adr.example.md` | `standards/adr/examples/` |

**Never change (consumer contract):** `.github/workflows/*.yml` filenames + bodies, `src/project_standards/**` (package, entry point, schema `$id`), git tags. The `…/blob/v1/…` permalinks in `adoption.md` §8 stay (immutable v1 reads of the old layout).

**Green definition** (run after each task unless noted):

```bash
uv run ruff format --check . && uv run ruff check . && uv run basedpyright \
  && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit \
  && uv run validate-frontmatter --config .project-standards.yml \
  && npx prettier --check .
```

---

## Task 0: Clean the working tree

**Files:** `standards/python-tooling-ssot-standard.md` (uncommitted link fixes from this session).

- [ ] **Step 1: Inspect the working tree**

Run: `git status --short` Expected: `M standards/python-tooling-ssot-standard.md` (markdown link fixes) and possibly `M project-standards.code-workspace` (unrelated session-start change).

- [ ] **Step 2: Commit only the link fixes (explicit path; never `git add .`)**

```bash
git add standards/python-tooling-ssot-standard.md
git commit -m "docs: convert python-tooling standard links to proper markdown links

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
git tag pre-restructure-baseline   # local marker for the Task 7 contract diff
```

Leave `project-standards.code-workspace` unstaged — it is not part of this work.

- [ ] **Step 3: Verify the standard file is now tracked-clean before moving it**

Run: `git status --short standards/python-tooling-ssot-standard.md` Expected: no output (clean).

---

## Task 1: Move files into bundles and rewire so the gate goes green

This is one atomic refactor: all moves + the two functional wiring edits + every internal link fix land in a single green commit. Do not commit between the move and the wiring — the gate is red in between by design.

**Files:**

- Create (dirs): `standards/markdown-frontmatter/{templates,examples}`, `standards/adr/{templates,examples}`, `standards/python-tooling/`, `meta/`
- Move: per the Authoritative path mapping above (via `git mv`)
- Modify: `.project-standards.yml`, `tests/test_validate_frontmatter.py`, and in-doc links in the moved docs + `src/project_standards/validate_frontmatter.py`, `src/project_standards/schemas/markdown-frontmatter.schema.json`, `tests/test_markdownlint_config.py`, `tests/README.md`

- [ ] **Step 1: Create bundle + meta directories**

```bash
mkdir -p standards/markdown-frontmatter/templates/repo-pages standards/markdown-frontmatter/examples \
         standards/adr/templates standards/adr/examples \
         standards/python-tooling meta
```

- [ ] **Step 2: `git mv` the standard docs (rename to README.md / adopt.md / meta)**

```bash
git mv standards/markdown-frontmatter.md          standards/markdown-frontmatter/README.md
git mv standards/adoption.md                      standards/markdown-frontmatter/adopt.md
git mv standards/adr.md                           standards/adr/README.md
git mv standards/python-tooling-ssot-standard.md  standards/python-tooling/README.md
git mv standards/versioning.md                    meta/versioning.md
```

- [ ] **Step 3: `git mv` the frontmatter-bundle templates and examples**

```bash
git mv templates/frontmatter-minimal.yml   standards/markdown-frontmatter/templates/
git mv templates/frontmatter-standard.yml  standards/markdown-frontmatter/templates/
git mv templates/concept.md                standards/markdown-frontmatter/templates/
git mv templates/note.md                   standards/markdown-frontmatter/templates/
git mv templates/runbook.md                standards/markdown-frontmatter/templates/
git mv templates/research.md               standards/markdown-frontmatter/templates/
git mv templates/spec.md                   standards/markdown-frontmatter/templates/
git mv templates/repo-pages/README.directory.template.md standards/markdown-frontmatter/templates/repo-pages/
git mv examples/concept.example.md   standards/markdown-frontmatter/examples/
git mv examples/note.example.md      standards/markdown-frontmatter/examples/
git mv examples/runbook.example.md   standards/markdown-frontmatter/examples/
```

- [ ] **Step 4: `git mv` the ADR-bundle templates and example**

```bash
git mv templates/adr.md              standards/adr/templates/
git mv templates/adr-minimal.md      standards/adr/templates/
git mv templates/adr-bare.md         standards/adr/templates/
git mv templates/adr-bare-minimal.md standards/adr/templates/
git mv examples/adr.example.md       standards/adr/examples/
```

- [ ] **Step 5: Confirm the old top-level trees are empty, then remove them**

```bash
rmdir templates/repo-pages templates examples
```

Expected: succeeds (dirs empty). If `rmdir` errors, run `git status` to find a stray file and move it to the right bundle.

- [ ] **Step 6: Rewrite the dogfood globs in `.project-standards.yml`**

Replace the `include:` list (currently `CHANGELOG.md`, `standards/**/*.md`, `examples/**/*.md`) with:

```yaml
include:
  - 'CHANGELOG.md'
  - 'standards/**/*.md'
  - 'meta/**/*.md'
```

In the `exclude:` list, replace the `templates/**` entry (and its two comment lines) with the two new excludes, keeping every other exclude unchanged:

```yaml
# Bundle templates carry intentional placeholders (YYYY-MM-DD, replace-with-stable-id)
# that do not satisfy the schema's date and id patterns.
- 'standards/**/templates/**'
# The standards index is a navigation landing page (like the root README), not a managed doc.
- 'standards/README.md'
```

- [ ] **Step 7: Repoint the example-discovery contract test**

In `tests/test_validate_frontmatter.py`, replace line ~819:

```python
EXAMPLE_FILES = sorted((_REPO_ROOT / "examples").glob("*.md"))
```

with:

```python
EXAMPLE_FILES = sorted(_REPO_ROOT.glob("standards/*/examples/*.md"))
```

Replace the assertion message (line ~825):

```python
    assert EXAMPLE_FILES, "expected worked examples under examples/"
```

with:

```python
    assert EXAMPLE_FILES, "expected worked examples under standards/*/examples/"
```

Update the module docstring bullet (line ~18) `the shipped ``examples/`` and bundled schema.` → `the shipped ``standards/*/examples/`` and bundled schema.`

- [ ] **Step 8: Fix in-doc links — `standards/markdown-frontmatter/README.md`**

These links are now two directories deep, so `../` becomes `../../`:

- Line ~37: `](../src/project_standards/schemas/markdown-frontmatter.schema.json)` → `](../../src/project_standards/schemas/markdown-frontmatter.schema.json)`
- Line ~37: `](../src/project_standards/validate_frontmatter.py)` → `](../../src/project_standards/validate_frontmatter.py)`
- Line ~417: `[`standards/versioning.md`](../standards/versioning.md)` → `[`meta/versioning.md`](../../meta/versioning.md)`
- Line ~421: `](../src/project_standards/validate_frontmatter.py)` → `](../../src/project_standards/validate_frontmatter.py)`
- Line ~421: `](../src/project_standards/schemas/markdown-frontmatter.schema.json)` → `](../../src/project_standards/schemas/markdown-frontmatter.schema.json)`
- Line ~426: `](../README.md#consuming-the-standards)` → `](../../README.md#consuming-the-standards)`
- Frontmatter `related:` (line ~22): `- 'standards/versioning.md'` → `- 'meta/versioning.md'`
- Example `related:` block (lines ~372–373): `- 'schemas/markdown-frontmatter.schema.json'` → `- 'src/project_standards/schemas/markdown-frontmatter.schema.json'`; `- 'templates/adr.md'` → `- 'standards/adr/templates/adr.md'`

- [ ] **Step 9: Fix in-doc links — `standards/adr/README.md`**

- Line ~37: `](markdown-frontmatter.md)` → `](../markdown-frontmatter/README.md)`
- Line ~117: `[`templates/`](../templates/)` → `[`templates/`](templates/)`
- Line ~117: `[`adr.md`](../templates/adr.md)` → `[`adr.md`](templates/adr.md)`
- Line ~123: `](markdown-frontmatter.md)` → `](../markdown-frontmatter/README.md)`
- Line ~149: `](markdown-frontmatter.md)` → `](../markdown-frontmatter/README.md)`
- Frontmatter `related:` (line ~22): `- 'templates/adr.md'` → `- 'standards/adr/templates/adr.md'`

- [ ] **Step 10: Fix frontmatter links — `standards/markdown-frontmatter/adopt.md`**

- `related:` (line ~22): `- 'standards/markdown-frontmatter.md'` → `- 'standards/markdown-frontmatter/README.md'`
- `related:` (line ~23): `- 'standards/versioning.md'` → `- 'meta/versioning.md'`
- Leave line ~24 `- 'README.md'` (root-relative) and the §8 `…/blob/v1/…` permalinks unchanged.

- [ ] **Step 11: Fix in-doc link — `meta/versioning.md`**

- Line ~34: `](markdown-frontmatter.md)` → `](../standards/markdown-frontmatter/README.md)`
- Leave line ~85 (the `L3DigitalNet/project-standards/.github/workflows/…@v1` reference) unchanged.

- [ ] **Step 12: Fix code/comment path strings (no behavior change)**

- `src/project_standards/validate_frontmatter.py` line ~5: `standards/markdown-frontmatter.md` → `standards/markdown-frontmatter/README.md`
- `src/project_standards/validate_frontmatter.py` line ~16: `examples/*.md` → `standards/markdown-frontmatter/examples/*.md`
- `src/project_standards/validate_frontmatter.py` line ~127: `standards/adr.md` → `standards/adr/README.md`
- `src/project_standards/schemas/markdown-frontmatter.schema.json` line ~5 `description`: `standards/markdown-frontmatter.md` → `standards/markdown-frontmatter/README.md` (leave line 3 `$id` unchanged)
- `tests/test_markdownlint_config.py` line ~28 comment: `Sources: standards/adr.md + the CHANGELOG.` → `Sources: standards/adr/README.md + the CHANGELOG.`
- `tests/README.md` line ~11: ``the shipped `examples/` must always validate`` → ``the shipped examples (`standards/*/examples/`) must always validate``
- `tests/README.md` line ~42: ``Each file under `examples/` is a worked example`` → ``Each file under a bundle's `examples/` (`standards/*/examples/`) is a worked example``

- [ ] **Step 13: Run the full green gate**

Run the **Green definition** command block at the top. Expected: all six tool steps pass; `validate-frontmatter` prints `✓ N file(s) validated` with N reflecting the bundle READMEs + 3 `adopt.md` (adopt.md exists only for frontmatter at this point) + 4 examples + `meta/versioning.md` + `CHANGELOG.md`; Prettier reports all files use its style. If `validate-frontmatter` flags a moved template, re-check the `standards/**/templates/**` exclude (Step 6).

- [ ] **Step 14: Dead-link sweep — no old paths survive in live docs**

```bash
grep -rnE "standards/(markdown-frontmatter|adr|versioning|adoption|python-tooling-ssot-standard)\.md|\]\((\.\./)?(templates|examples)/" \
  standards meta README.md src tests docs/handoff .project-standards.yml 2>/dev/null \
  | grep -vE "node_modules|\.venv|docs/superpowers|/blob/v1/"
```

Expected: no output. Any hit is a missed link — fix it and re-run Step 13.

- [ ] **Step 15: Commit the atomic move + rewiring**

```bash
# git mv already staged every rename + the old-tree deletions; these pathspecs
# pick up the post-move content edits. Do NOT list templates/ or examples/ —
# they no longer exist, and `git add` would error on a missing pathspec.
git add -A standards meta .project-standards.yml \
  src/project_standards/validate_frontmatter.py \
  src/project_standards/schemas/markdown-frontmatter.schema.json \
  tests/test_validate_frontmatter.py tests/test_markdownlint_config.py tests/README.md
git commit -m "refactor(standards): move each standard into a self-contained bundle

git mv the three governing standards + adoption + versioning into
standards/<name>/ bundles (+ meta/versioning.md); dissolve top-level
templates/ and examples/ into the bundles; rewire dogfood globs, the
example-discovery test, and all internal links. Consumer contract
(workflows, validator package, bundled schema) unchanged.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

(Use of `git add -A` is scoped to explicit pathspecs above, so nothing outside this change is staged.)

---

## Task 2: Create the standards index

**Files:** Create `standards/README.md` (excluded from frontmatter validation; no frontmatter).

- [ ] **Step 1: Write the index**

````markdown
# Standards

This directory holds the **governing standards** this repository defines. Each standard is a self-contained **bundle** — open its folder and the standard renders.

| Standard | What it governs | Bundle | Adopt |
| --- | --- | --- | --- |
| Markdown Frontmatter | Canonical, tool-neutral YAML metadata for Markdown documents | [markdown-frontmatter/](markdown-frontmatter/) | [adopt](markdown-frontmatter/adopt.md) |
| ADR | Architecture Decision Records (MADR on the frontmatter profile) | [adr/](adr/) | [adopt](adr/adopt.md) |
| Python Tooling SSOT | Python stack, layout, CI gate, and agent instructions | [python-tooling/](python-tooling/) | [adopt](python-tooling/adopt.md) |

## Bundle anatomy

Every standard follows the same shape, so adding a new one is mechanical:

```text
standards/<standard-id>/
├── README.md      # REQUIRED — the governing standard itself
├── adopt.md       # REQUIRED — how to adopt this standard
├── templates/     # OPTIONAL — copy-paste scaffolds (placeholders; not frontmatter-validated)
└── examples/      # OPTIONAL — validated worked examples (real frontmatter; dogfooded)
```

A standard may be doc-only (just `README.md` + `adopt.md`) — see [python-tooling/](python-tooling/).

## Not a governed standard

[`../meta/versioning.md`](../meta/versioning.md) describes how _this repository_ is versioned and consumed. It is a meta document, not a standard you adopt.
````

- [ ] **Step 2: Format, verify, commit**

Run: `npx prettier --write standards/README.md && uv run validate-frontmatter --config .project-standards.yml` Expected: Prettier writes/leaves the file; validator stays green (the index is excluded).

```bash
git add standards/README.md
git commit -m "docs(standards): add bundle index + anatomy

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Create the ADR and Python-tooling `adopt.md` files

**Files:** Create `standards/adr/adopt.md`, `standards/python-tooling/adopt.md` (both carry frontmatter and are validated).

- [ ] **Step 1: Write `standards/adr/adopt.md`**

````markdown
---
schema_version: '1.1'
id: 'adr-standard-adoption'
title: 'Adopt the ADR Standard'
description: 'How to adopt the ADR Standard in a consuming repository; it rides the frontmatter validator.'
doc_type: 'runbook'
status: 'active'
created: '2026-06-06'
updated: '2026-06-06'
reviewed: null
owner: ''
consumer: 'agent'
tags:
  - adoption
  - adr
aliases: []
related:
  - 'standards/adr/README.md'
  - 'standards/markdown-frontmatter/adopt.md'
source: []
confidence: 'high'
visibility: 'public'
license: null
---

# Adopt the ADR Standard

ADRs are **managed Markdown documents**: they carry full frontmatter and are validated by the same tooling as every other doc. There is **no separate ADR workflow**.

## 1. Adopt the Frontmatter Standard first

Follow [`../markdown-frontmatter/adopt.md`](../markdown-frontmatter/adopt.md) to add `.project-standards.yml` and the reusable validator workflow. ADR enforcement rides on top of it.

## 2. Let ADRs validate

Do **not** exclude `docs/adr/**` or `docs/decisions/**` in `.project-standards.yml` — ADRs are managed docs. Each carries frontmatter with `doc_type: adr` and an id like `adr-NNNN-repo-name-short-title` (see [the standard](README.md)).

## 3. (Optional) enforce MADR body sections

To assert every `doc_type: adr` document has the three MADR-required `##` sections, opt in:

```yaml
markdown:
  adr:
    require_sections: true
```

This rides the same frontmatter workflow — no extra job. See [the standard](README.md) for the section list.

## 4. Author from a template

Copy a scaffold from [`templates/`](templates/): `adr.md` (full), `adr-minimal.md`, `adr-bare.md`, `adr-bare-minimal.md`. A worked example is in [`examples/adr.example.md`](examples/adr.example.md).
````

- [ ] **Step 2: Write `standards/python-tooling/adopt.md`**

````markdown
---
schema_version: '1.1'
id: 'python-tooling-adoption'
title: 'Adopt the Python Tooling SSOT Standard'
description: 'How to adopt the Python Tooling SSOT Standard: copy the in-doc scaffolds and run the verification gate; there is no reusable workflow.'
doc_type: 'runbook'
status: 'active'
created: '2026-06-06'
updated: '2026-06-06'
reviewed: null
owner: ''
consumer: 'agent'
tags:
  - adoption
  - python
  - tooling
aliases: []
related:
  - 'standards/python-tooling/README.md'
source: []
confidence: 'high'
visibility: 'public'
license: null
---

# Adopt the Python Tooling SSOT Standard

Unlike the Markdown standards, this one is **not** enforced by the shared validator and ships **no reusable workflow**. Adoption is copy-the-scaffolds plus run-the-gate. The scaffolds live inline in [the standard](README.md).

## Steps

1. **Copy the scaffolds** from [the standard](README.md): the `pyproject.toml` baseline (§6), `.python-version`, `.editorconfig` (§14), `.vscode/` config (§13), `.github/workflows/check.yml` (§15), the agent entry points (§16–17), and optionally `scripts/check.py` (§18).
2. **Run the verification gate** (standard §2):

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run coverage run -m pytest
uv run coverage report
uv run pip-audit
```

3. **Migrating an existing repo?** Follow the staged migration guide (standard §21).
4. **Need an exception?** Record it as an ADR (standard §20); see the [ADR Standard](../adr/README.md).
````

- [ ] **Step 3: Format, verify, commit**

Run: `npx prettier --write standards/adr/adopt.md standards/python-tooling/adopt.md && uv run validate-frontmatter --config .project-standards.yml` Expected: validator green; the two new `adopt.md` files are now counted as validated.

```bash
git add standards/adr/adopt.md standards/python-tooling/adopt.md
git commit -m "docs(standards): add ADR and Python-tooling adopt guides

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Rewrite the root README for bundles (and add the missing Python section)

**Files:** Modify `README.md`.

- [ ] **Step 1: Replace the Repository layout block**

Replace the fenced `text` block under `## Repository layout` (currently the `standards/`/`templates/`/`examples/`/`src`/`tests`/`.github` tree) with:

```text
project-standards/
├── standards/                 # governing standards — one self-contained bundle per standard
│   ├── README.md              #   index + bundle anatomy
│   ├── markdown-frontmatter/  #   standard + adopt + templates/ + examples/
│   ├── adr/                   #   standard + adopt + templates/ + examples/
│   └── python-tooling/        #   standard + adopt (doc-only)
├── meta/                      # docs about THIS repo (e.g. versioning) — not governed standards
├── src/project_standards/     # the Python validator + bundled schema
├── tests/                     # validator tests
└── .github/                   # reusable CI workflows
```

- [ ] **Step 2: Update the Standards intro + Frontmatter links**

- The intro line under `## Standards`: replace `Each is a human-readable document under [`standards/`](standards/), enforced by the shared validator.` with `Each lives in its own bundle under [`standards/`](standards/) — see the [standards index](standards/README.md). All three are enforced or scaffolded from this repo.`
- Frontmatter **Standard** bullet: `[`standards/markdown-frontmatter.md`](standards/markdown-frontmatter.md)` → `[`standards/markdown-frontmatter/README.md`](standards/markdown-frontmatter/README.md)`
- Frontmatter **Templates/Examples** bullet: replace with `- **Templates:** [`templates/`](standards/markdown-frontmatter/templates/) · **Examples:** [`examples/`](standards/markdown-frontmatter/examples/) · **Adopt:** [`adopt.md`](standards/markdown-frontmatter/adopt.md)`

- [ ] **Step 3: Update the ADR subsection links**

- **Standard** bullet: `[`standards/adr.md`](standards/adr.md)` → `[`standards/adr/README.md`](standards/adr/README.md)`
- **Templates** bullet: `[`templates/adr.md`](templates/adr.md)` → `[`templates/adr.md`](standards/adr/templates/adr.md)`
- **Example** bullet: replace with `- **Example:** [`examples/adr.example.md`](standards/adr/examples/adr.example.md). · **Adopt:** [`adopt.md`](standards/adr/adopt.md).`

- [ ] **Step 4: Insert a new Python Tooling subsection (after the ADR subsection, before `## Consuming the standards`)**

```markdown
### Python Tooling SSOT Standard

The standard Python stack for agent-authored projects: `uv` + `uv_build`, `src/` layout, Ruff, basedpyright (strict), pytest + coverage (branch), pip-audit, a one-command verification gate, and the VS Code / agent-instruction conventions. Unlike the Markdown standards it is **not** validator-enforced and ships **no reusable workflow** — you adopt it by copying the in-doc scaffolds and running the gate.

- **Standard:** [`standards/python-tooling/README.md`](standards/python-tooling/README.md)
- **Adopt:** [`adopt.md`](standards/python-tooling/adopt.md)
```

- [ ] **Step 5: Update the adoption pointer, the inline ADR link, and the Versioning link**

- Adoption callout (the `> **Adopting with an agent?**` line): `[`standards/adoption.md`](standards/adoption.md)` → `[`standards/markdown-frontmatter/adopt.md`](standards/markdown-frontmatter/adopt.md)`
- The `### 3. Optional` / ADR config paragraph link `[ADR Standard](standards/adr.md)` → `[ADR Standard](standards/adr/README.md)`
- Under `## Versioning`: `[`standards/versioning.md`](standards/versioning.md)` → `[`meta/versioning.md`](meta/versioning.md)`

- [ ] **Step 6: Format, verify, commit**

Run: `npx prettier --write README.md && npx markdownlint-cli2 README.md && uv run validate-frontmatter --config .project-standards.yml` Expected: Prettier OK; markdownlint reports 0 errors; validator green (README still excluded).

```bash
git add README.md
git commit -m "docs(readme): bundle layout, per-bundle adopt links, add Python Tooling section

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Add the CHANGELOG entry

**Files:** Modify `CHANGELOG.md` (do **not** rewrite historical entries).

- [ ] **Step 1: Add a Changed entry under `## [Unreleased]`**

Immediately after the `## [Unreleased]` line, insert:

```markdown
### Changed

- **BREAKING (docs layout):** Restructured `standards/` into one self-contained bundle per governing standard — `standards/<name>/{README.md, adopt.md, templates/, examples/}`. The flat top-level `templates/` and `examples/` trees were dissolved into the bundles, and `versioning.md` moved to `meta/`. Added `standards/README.md` (index + bundle anatomy) and per-standard `adopt.md` entries. Doc deep-links change; the **consumer contract is unchanged** — reusable workflow names, the `validate-frontmatter` package + entry point, and the bundled schema path are identical.
```

- [ ] **Step 2: Format, verify, commit**

Run: `npx prettier --write CHANGELOG.md && uv run validate-frontmatter --config .project-standards.yml` Expected: validator green (CHANGELOG is in `include` and has frontmatter).

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): record standards bundle restructure (Unreleased)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Update handoff docs

**Files:** Modify `docs/handoff/architecture.md`, `docs/handoff/conventions.md`, `docs/handoff/deployed.md`, `docs/handoff/state.md`.

- [ ] **Step 1: Update the architecture component tree**

In `docs/handoff/architecture.md`, replace the `text` Components block with:

```text
project-standards
├── standards/          -> governing standards, one bundle each (markdown-frontmatter, adr, python-tooling) + README index
├── meta/               -> docs about this repo (versioning); not a governed standard
├── src/project_standards/ + tests/ -> the Python validator (validate_frontmatter.py) with bundled schema, and its pytest suite
├── .github/workflows/  -> reusable workflows consumers call (validate, lint-markdown, format)
└── docs/handoff/       -> agent session state (this v3 layout)
```

Also update the Relationships bullet `standards/, examples/, CHANGELOG.md carry canonical frontmatter and must validate.` → `the bundle README/adopt/example docs, meta/, and CHANGELOG.md carry canonical frontmatter and must validate.`

- [ ] **Step 2: Repoint stale paths in the other handoff docs**

- `docs/handoff/conventions.md`: replace every `standards/python-tooling-ssot-standard.md` with `standards/python-tooling/README.md` (2 occurrences, lines ~79 and ~83).
- `docs/handoff/deployed.md` line ~11: `standards/adoption.md` → `standards/markdown-frontmatter/adopt.md`.
- `docs/handoff/state.md`: `standards/python-tooling-ssot-standard.md` → `standards/python-tooling/README.md`; `versioning.md` → `meta/versioning.md`. Bump **Last updated** to the implementation date and note the restructure in the at-a-glance bullets.

- [ ] **Step 3: Format and commit**

Run: `npx prettier --write docs/handoff/architecture.md docs/handoff/conventions.md docs/handoff/deployed.md docs/handoff/state.md` (docs/handoff is excluded from frontmatter validation, so the validator is unaffected.)

```bash
git add docs/handoff/architecture.md docs/handoff/conventions.md docs/handoff/deployed.md docs/handoff/state.md
git commit -m "docs(handoff): reflect standards bundle restructure

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Final verification

- [ ] **Step 1: Full green gate**

Run the **Green definition** block from the top of this plan. Expected: every step passes.

- [ ] **Step 2: Dead-link sweep (whole repo, live docs only)**

```bash
grep -rnE "standards/(markdown-frontmatter|adr|versioning|adoption|python-tooling-ssot-standard)\.md|\]\((\.\./)?(templates|examples)/[^)]*\)" \
  . 2>/dev/null | grep -vE "node_modules|\.venv|/.git/|docs/superpowers|/blob/v1/|CHANGELOG.md"
```

Expected: no output. (CHANGELOG historical entries and `docs/superpowers/` plans/specs are intentionally excluded.)

- [ ] **Step 3: Confirm history was preserved on a moved file**

Run: `git log --follow --oneline -- standards/adr/README.md | head` Expected: history predating the move is visible (proves `git mv` kept provenance).

- [ ] **Step 4: Confirm the consumer contract is byte-identical**

Run: `git diff --stat pre-restructure-baseline -- .github/workflows src/project_standards` Expected: only the cosmetic docstring/`description` path edits in `src/project_standards/**` (validator.py, schema.json); **zero** changes under `.github/workflows/`.

- [ ] **Step 5: Remove the baseline marker**

Run: `git tag -d pre-restructure-baseline`

---

## Self-review notes

- **Spec coverage:** bundle anatomy (Task 2), migration map (Task 1 steps 2–5), functional wiring (Task 1 steps 6–7), accuracy sweeps (Task 1 steps 8–12, Task 4, Task 6), index/adopt/meta (Tasks 2–3), verification + release framing (Task 5 entry, Task 7). README Python-section gap (Task 4 step 4). All covered.
- **No placeholders:** every edit lists exact old→new strings or full file content; every command has an expected result.
- **Out of scope (release ritual, not this plan):** applying the `2.0.0` version to `pyproject.toml`/CHANGELOG header, moving the `v1`/`v2` tags, fast-forwarding `main`, and retargeting `adopt.md` version pins (`@v1`→`@v2`). These belong to the locked release, tracked in `deployed.md`.
