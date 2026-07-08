# Standard Bundle Authoring Standard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Author the Standard Bundle Authoring Standard (SPEC-BA01) — the "standard for standards" — as a governed bundle under `standards/standard-bundle-authoring/`, plus its own worked-example `standard.toml`, a blank template, and the standards-index updates.

**Architecture:** Documentation deliverable only. The written contract (a standard `README.md`) defines the `standard.toml` manifest, authority tuples, relationship taxonomy, dotted config-namespace ownership, providers, resources, adoption modes, lifecycle, and the exception process. The machine schema, Pydantic model, fixtures, and graph validator are **out of scope** (SPEC-MT01 Steps 03–04). The bundle dogfoods the contract by shipping its own `standard.toml`.

**Tech Stack:** Markdown + YAML frontmatter (Markdown Frontmatter Standard); TOML (`standard.toml`); the repo's own validators (`validate-frontmatter`, `validate-id`, `project-standards spec`), markdownlint, and Prettier. No Python, no new dependencies.

**Source of truth:** `docs/superpowers/specs/2026-07-07-standard-bundle-authoring-standard.md` (SPEC-BA01, rev 0.3). Each task's acceptance is the named FR's acceptance criteria in that spec. The `standard.toml` field shapes follow SPEC-MT01 §9.

## Global Constraints

- **No code, no schema, no validator, no `registry.json` change** — those are SPEC-MT01 Steps 03–04 (spec NG / WH-001/002). This task produces documentation + TOML data only.
- **Internal/reference standard:** `adoption = "none"`; **no `adopt.md`**, no copy-adopt bundle, no consumer contract version (spec NG-001). Do **not** add it to `spec.include`, the adopt engine, or `src/project_standards/bundles/`.
- **Adoption-mode enum (FR-003):** exactly `validator | copy-adopt | cli | reference-only | none`. The seven current standards map: markdown-frontmatter/adr → `validator`; python-tooling/markdown-tooling/cli-documentation → `copy-adopt`; project-spec → `cli`; python-coding → `reference-only` (draft); this meta-standard → `none`.
- **Config namespaces are dotted paths (FR-006):** a parent (e.g. `markdown`) may be a shared container whose child paths (`markdown.frontmatter`, `markdown.adr`) are owned by different standards; meta keys (`standards_version`) are repo-owned, not standard-owned; duplicate ownership of the same path is invalid.
- **Manifest paths are bundle-relative and contained (FR-012):** resource/template paths must stay inside the declaring standard's own directory (no `..`, no absolute, no symlink escape); cross-bundle sharing only via the explicit `_shared` mechanism; a provider `entrypoint` is an import path or command reference, not a filesystem path.
- **Everything must stay green:** `standards/standard-bundle-authoring/README.md` is under `standards/**/*.md`, so it is frontmatter- and id-validated **and** markdownlint/Prettier-gated. `standards/README.md` is frontmatter-excluded but markdownlint/Prettier-gated. SPEC-BA01 must still pass `spec validate`/`lint`.
- **Branch `testing`; release freeze** — this change accrues to v5.0.0, no release cut. Commit style: `docs(v5): …`.

---

## File Structure

- **Create** `standards/standard-bundle-authoring/README.md` — the standard itself (the contract; FR-001…FR-014). One responsibility: define the bundle-authoring contract in prose + an annotated example.
- **Create** `standards/standard-bundle-authoring/standard.toml` — the meta-standard's own machine manifest (FR-010 worked example; dogfoods the contract).
- **Create** `standards/standard-bundle-authoring/templates/standard.toml` — a blank annotated `standard.toml` template for future standard authors.
- **Modify** `standards/README.md` — add the bundle row (non-adoptable marker) and update the bundle-anatomy text so `adopt.md` is required only for _adoptable_ standards.

No other files change. (If a "adopt.md is required for every standard" anatomy claim also lives outside `standards/README.md` — e.g. `AGENTS.md` — Task 4 greps for it and reconciles it too.)

---

### Task 1: Author the meta-standard `README.md` (the contract)

**Files:**

- Create: `standards/standard-bundle-authoring/README.md`
- Reference (read, do not edit): `standards/markdown-tooling/README.md` (frontmatter + house style), `docs/superpowers/specs/2026-07-07-standard-bundle-authoring-standard.md` (the FRs), SPEC-MT01 §9 (the `standard.toml` shape).

**Interfaces:**

- Produces: the field names/shape of `standard.toml` that Task 2 (worked example) and Task 3 (template) must match **exactly**. Author this README's manifest contract first; Tasks 2–3 copy its field names.

- [ ] **Step 1: Read the sibling pattern.** Read `standards/markdown-tooling/README.md` lines 1–20 for the frontmatter shape and the standard's prose voice; read SPEC-BA01 §7.1 (FR-001…FR-014) — those are this file's acceptance criteria.

- [ ] **Step 2: Write the frontmatter.** Use this exact shape (mint a fresh 6-char base36 token for the id — run `uv run python -c "from project_standards.id_format import random_token; print(random_token())"`):

```yaml
---
schema_version: '1.1'
id: 'reference-XXXXXX-standard-bundle-authoring'
title: 'Standard Bundle Authoring Standard'
description: 'The contract every standard bundle in this repository must declare: standard.toml manifest, authorities, relationships, dotted config-namespace ownership, providers, resources, adoption modes, lifecycle, and the exception process.'
doc_type: 'reference'
status: 'active'
created: '2026-07-07'
updated: '2026-07-07'
reviewed: null
owner: ''
consumer: 'mix'
tags:
  - 'standards-platform'
  - 'meta-repo'
  - 'manifests'
  - 'standard'
aliases:
  - 'standard-bundle-authoring'
  - 'meta-standard'
related:
  - 'docs/superpowers/specs/2026-07-07-standard-bundle-authoring-standard.md'
  - 'docs/adr/adr-0001-standard-bundle-authoring-contract.md'
---
```

- [ ] **Step 3: Author the body sections.** One `##` section per contract area; each satisfies the named FR's acceptance criteria (write real prose, not placeholders — the spec's acceptance text is the checklist):
  - **Purpose & Status** — the "standard for standards"; internal/reference, `adoption = "none"`, no `adopt.md`.
  - **Bundle anatomy** (FR-001) — a table of required vs optional files (`README.md` required; `standard.toml` required; `adopt.md` required **only for adoptable standards**, otherwise an explicit non-adoptable marker; optional `templates/`, `examples/`, `resources/`, `agent-summary.md`).
  - **The `standard.toml` manifest** (FR-002) — an annotated fenced `toml` example showing **every** field with a comment marking required vs optional, using SPEC-MT01 §9 as the shape (`[standard]` id/name/status/summary/adoption; `[versions]`; `[config]` namespaces; `[relations]`; `[resources]`; `[[authority]]`; `[[providers]]`). Use a representative adoptable standard (e.g. `markdown-tooling`) for the example so authorities/providers are non-empty and realistic.
  - **Adoption modes** (FR-003) — the five-value enum and the mapping table for all seven current standards (see Global Constraints).
  - **Authorities** (FR-004) — the tuple `(domain, target, concern, owner, mutates)` and the conflict rule (two mutating authorities over the same concern + overlapping target with different owners conflict unless an ADR-backed `extends` relation exists).
  - **Relationships** (FR-005) — `independent | companion | extends | conflicts | consumes_platform`, `independent` as default, no hidden `requires`.
  - **Config-namespace ownership** (FR-006) — dotted paths, parent delegation, reserved meta keys, with a worked table showing `markdown.frontmatter` (markdown-frontmatter), `markdown.adr` (adr), `spec` (project-spec), `standards_version` (meta). Model this as a `[config] namespaces = [...]` **array of dotted paths** — FR-006's dotted/nested model supersedes SPEC-MT01 §9's singular `namespace` field; Tasks 2–3 must use this same `namespaces` array.
  - **Providers** (FR-007) and **Resources** (FR-008) — provider declaration fields (operation/kind/entrypoint/optional) and resource descriptors (bundle-relative IDs → paths).
  - **Manifest safety** (FR-012) — bundle-relative containment, no `..`/absolute/symlink, first-party providers, entrypoint ≠ filesystem path.
  - **`adopt.toml` linkage** (FR-013) — reference the artifact manifest or declare non-adoptability; ownership/collision stay in the artifact plane.
  - **Lifecycle & exceptions** (FR-009) — `draft → review → active → deprecated → archived` (+ `superseded`); exceptions are ADR-backed.
  - **Manual conformance checklist** (FR-014) — a checklist mapping every **required** `standard.toml` field to a bundle, usable before the Step 03 schema exists.

- [ ] **Step 4: Validate the doc.**

Run: `uv run validate-frontmatter --config .project-standards.yml && uv run validate-id --config .project-standards.yml && ./node_modules/.bin/prettier --write standards/standard-bundle-authoring/README.md && ./node_modules/.bin/markdownlint-cli2 standards/standard-bundle-authoring/README.md` Expected: frontmatter ✓ (count increases by 1), id ✓, Prettier writes/clean, markdownlint `0 error(s)`.

- [ ] **Step 5: Commit.**

```bash
git add standards/standard-bundle-authoring/README.md
git commit -m "docs(v5): author Standard Bundle Authoring Standard (SPEC-BA01 FR-001..014)"
```

---

### Task 2: The meta-standard's own `standard.toml` (worked example)

**Files:**

- Create: `standards/standard-bundle-authoring/standard.toml`

**Interfaces:**

- Consumes: the field names defined in Task 1's manifest contract — this file must use exactly those keys.
- Produces: the first real `standard.toml` in the repo; the Step 03 schema (later) must accept it or record a deliberate supersession.

- [ ] **Step 1: Write the manifest.** Being internal/reference with `adoption = "none"`, it declares no consumer namespace, no authorities over consumer files, and no providers:

```toml
# The machine manifest for the Standard Bundle Authoring Standard.
# This meta-standard dogfoods the contract it defines. It is internal/reference
# (adoption = "none"): no consumer config namespace, no authorities over consumer
# files, no providers. Enforcement of the contract is future graph validation
# (SPEC-MT01 Step 04), not this bundle.

[standard]
id = "standard-bundle-authoring"
name = "Standard Bundle Authoring Standard"
status = "active"       # draft | active | deprecated | archived
summary = "The contract every standard bundle in this repository must declare."
adoption = "none"       # validator | copy-adopt | cli | reference-only | none

[versions]
supported = []          # internal/reference standards carry no consumer contract version
latest = ""

[config]
namespaces = []         # claims no key in .project-standards.yml

[relations]
companions = []
extends = []
conflicts = []
consumes_platform = []

[resources]
readme = "README.md"
template = "templates/standard.toml"

# No [[authority]] blocks — governs authoring, not a concern over consumer files.
# No [[providers]] blocks — reference-only, no executable hooks.
```

> **Decision (record if it diverges from OQ-002):** SPEC-BA01 OQ-002 assumed the meta-standard's own `standard.toml` would be the full annotated example including an authority. A `none`-adoption reference standard genuinely owns no authority, so the **comprehensive** annotated example lives in the README (Task 1, using a representative adoptable standard) while this file is the meta-standard's real minimal manifest. If you keep this split, add a `DEV-001` row to SPEC-BA01's Deviations Log noting it, and confirm the README's manifest field names match this file exactly.

- [ ] **Step 2: Verify against the conformance checklist.** Walk the README's manual conformance checklist (FR-014): every **required** field present. Confirm the TOML parses: `uv run python -c "import tomllib,pathlib; tomllib.loads(pathlib.Path('standards/standard-bundle-authoring/standard.toml').read_text()); print('toml ok')"` Expected: `toml ok`.

- [ ] **Step 3: Prettier-format.** Run: `./node_modules/.bin/prettier --check standards/standard-bundle-authoring/standard.toml 2>/dev/null || echo "toml not prettier-gated — skip"` (Prettier does not format `.toml`; this is a no-op check.)

- [ ] **Step 4: Commit.**

```bash
git add standards/standard-bundle-authoring/standard.toml
git commit -m "docs(v5): add standard-bundle-authoring standard.toml (FR-010 worked example)"
```

---

### Task 3: The blank `standard.toml` template

**Files:**

- Create: `standards/standard-bundle-authoring/templates/standard.toml`

**Interfaces:**

- Consumes: Task 1's field names. Every field the contract defines appears here, blank/annotated.

- [ ] **Step 1: Write the annotated template** (this is under `templates/`, so it is frontmatter-excluded; a `.toml` file is not frontmatter-validated regardless):

```toml
# standard.toml template — copy into standards/<id>/ and fill in.
# See ../README.md (Standard Bundle Authoring Standard) for each field's contract.

[standard]
id = ""                 # kebab-case, matches the directory name
name = ""               # human-readable
status = "draft"        # draft | active | deprecated | archived
summary = ""            # one sentence
adoption = "none"       # validator | copy-adopt | cli | reference-only | none

[versions]
supported = []          # e.g. ["1.0", "1.1"] for versioned standards; [] otherwise
latest = ""

[config]
namespaces = []         # dotted paths this standard owns, e.g. ["markdown.frontmatter"]

[relations]
companions = []         # advisory only, never auto-required
extends = []            # explicit extension only; requires an ADR
conflicts = []          # exceptional; prefer redesign
consumes_platform = []  # generic platform capabilities, not other standards

[resources]
readme = "README.md"    # bundle-relative paths only (no .., no absolute, no symlink escape)

# [[authority]]         # one block per owned concern; delete if none
# domain = ""           # e.g. "markdown"
# target = ""           # glob within the consumer repo, e.g. "**/*.md"
# concern = ""          # e.g. "physical-formatting"
# owner = ""            # the tool, e.g. "prettier"
# mutates = true

# [[providers]]         # one block per generic operation; delete if none
# operation = ""        # validate | fix | drift-check | id-next | extract
# kind = ""             # python | command | workflow | documentation-only
# entrypoint = ""       # import path or command reference (NOT a filesystem path)
# optional = true
```

- [ ] **Step 2: Verify it parses.** Run: `uv run python -c "import tomllib,pathlib; tomllib.loads(pathlib.Path('standards/standard-bundle-authoring/templates/standard.toml').read_text()); print('toml ok')"` Expected: `toml ok`.

- [ ] **Step 3: Commit.**

```bash
git add standards/standard-bundle-authoring/templates/standard.toml
git commit -m "docs(v5): add blank standard.toml template"
```

---

### Task 4: Update the standards index + bundle-anatomy text

**Files:**

- Modify: `standards/README.md`

- [ ] **Step 1: Find every "adopt.md required" anatomy claim.** Run: `rg -n "adopt\.md" standards/README.md AGENTS.md` and read the hits. The bundle-anatomy description must be reconciled so `adopt.md` is required only for _adoptable_ standards; internal/reference/cli standards use an explicit non-adoptable marker instead (this is SPEC-BA01's SA-005 DoD item).

- [ ] **Step 2: Add the index row.** In the `standards/README.md` table, add a row after the `Python Coding` row, matching the non-adoptable marker style already used there:

```markdown
| Standard Bundle Authoring | The contract every standard bundle must declare (`standard.toml`, authorities, relationships, namespaces) | [standard-bundle-authoring/](standard-bundle-authoring/) | — (**internal/reference**; governs how this repo authors standards, not consumer-adopted) |
```

- [ ] **Step 3: Reconcile the anatomy text** found in Step 1 (in `standards/README.md`, and `AGENTS.md` if it asserts the same) so it reads, in substance: "every standard has a `README.md` and a `standard.toml`; `adopt.md` is present only for adoptable standards — internal/reference and CLI-enforced standards carry an explicit non-adoptable marker instead." Keep edits minimal and in the file's existing voice.

- [ ] **Step 4: Validate.** Run: `./node_modules/.bin/prettier --write standards/README.md AGENTS.md && ./node_modules/.bin/markdownlint-cli2 standards/README.md AGENTS.md` Expected: Prettier clean, markdownlint `0 error(s)`. (`standards/README.md` and `AGENTS.md` are frontmatter-excluded — do not run `validate-frontmatter` expecting them.)

- [ ] **Step 5: Commit.**

```bash
git add standards/README.md AGENTS.md
git commit -m "docs(v5): list Standard Bundle Authoring in the standards index; fix adopt.md anatomy"
```

---

### Task 5: Full-gate verification + handoff

**Files:**

- Modify: `TODO.md` (check Step 02), `docs/handoff/specs-plans.md`, `docs/handoff/sessions/2026-07.md`, `STATUS.md`
- Modify (if the Task 2 split was taken): `docs/superpowers/specs/2026-07-07-standard-bundle-authoring-standard.md` (add the `DEV-001` row)

- [ ] **Step 1: Run the full repo gate.**

Run:

```bash
uv run validate-frontmatter --config .project-standards.yml
uv run validate-id --config .project-standards.yml
uv run project-standards spec validate --config .project-standards.yml
uv run project-standards spec lint --config .project-standards.yml
./node_modules/.bin/prettier --check "standards/**/*.md" "standards/**/*.toml" 2>/dev/null; ./node_modules/.bin/markdownlint-cli2
uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run pytest -q
```

Expected: frontmatter ✓ (one more file than before), id ✓, spec validate/lint OK, markdownlint 0, Prettier clean, ruff/basedpyright/pytest green (no Python changed, so 868 tests unchanged). If any FR is unmet, fix the doc and re-run — the spec's DoD is the gate.

- [ ] **Step 2: Tick SPEC-BA01's DoD** in the spec file against the finished bundle (or leave for owner acceptance per the DoD's owner-review line). Add the `DEV-001` Deviations row if Task 2's split was taken.

- [ ] **Step 3: Update handoff.** Check `Step 02` in the `TODO.md` v5.0.0 tracker (with date + commit); flip the `specs-plans.md` Step 02 row to "authored + validated"; add a `sessions/2026-07.md` row; add a `STATUS.md` Recent-Changes line. (Per the handoff-system-v3 skill.)

- [ ] **Step 4: Commit.**

```bash
git add TODO.md docs/handoff/specs-plans.md docs/handoff/sessions/2026-07.md STATUS.md docs/superpowers/specs/2026-07-07-standard-bundle-authoring-standard.md
git commit -m "docs(v5): Step 02 complete — Standard Bundle Authoring Standard authored + validated"
```

---

## Notes for the implementer

- **The spec is the content contract.** Every README section must satisfy the acceptance criteria of its FR in SPEC-BA01 rev 0.3. When in doubt, re-read the FR — do not invent requirements (Appendix B.2).
- **Field-name consistency is the top risk.** The README's manifest contract, `standard.toml`, and `templates/standard.toml` must use identical field names. Author Task 1's manifest section first; copy names into Tasks 2–3.
- **Nothing enters the machine layer.** No `registry.json`, `spec.include`, `src/project_standards/bundles/`, or new Python. If you feel the urge to add a schema, that's Step 03 — stop and record an `OQ-`.
- **Keep it dogfood-clean throughout** — the meta-standard README is validated by the very standards it sits beside.
