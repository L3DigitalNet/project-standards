---
schema_version: '1.1'
id: spec-mt01-baseline-inventory
title: 'SPEC-MT01 Step 00 — Baseline Inventory'
description: 'Factual inventory of the project-standards repository as it exists before the Meta-repo readiness work — standards, registry, adopt manifests, schemas, CLI/validators, workflows, config namespaces, tests, and the observable authority map — plus the self-description gaps SPEC-MT01 closes.'
doc_type: reference
status: active
created: '2026-07-07'
updated: '2026-07-07'
reviewed: '2026-07-07'
owner: project-standards
consumer: agent
tags:
  - mcp
  - meta-repo
  - inventory
  - standards
  - spec-mt01
aliases:
  - MT01 baseline inventory
  - Step 00 inventory
related:
  - docs/superpowers/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md
  - docs/superpowers/specs/2026-07-07-project-standards-mcp-enablement-roadmap-spec.md
  - docs/superpowers/research/2026-07-07-project-standards-mcp-specification-reference-pack.md
confidence: high
visibility: internal
license: null
---

# SPEC-MT01 Step 00 — Baseline Inventory

This is the **Step 00 (Baseline inventory)** deliverable for `SPEC-MT01` (see `SPEC-RD01` §19). It is a factual snapshot of the repository _before_ the manifest/graph work begins, so every later step (the meta-standard, `standard.toml`, the graph validator, the retrofit) reads from a single agreed map rather than re-deriving current state. It records **what is**, not what should change.

**Snapshot:** package `4.3.0` · `requires-python >=3.14` · captured 2026-07-07 on `testing` at `add1a07`.

## 1. Standards (`standards/`)

Seven standard directories exist. Only **five** are fully machine-described (an `adopt.md`, a bundle under `src/project_standards/bundles/`, and a `registry.json` entry). `project-spec` is adoptable through its CLI but has neither a bundle nor a registry entry; `python-coding` is an in-development draft that is unregistered and excluded from validation.

| id (dir) | `adopt.md` | machine bundle | registry entry | adoption model | status |
| --- | --- | --- | --- | --- | --- |
| `markdown-frontmatter` | yes | yes | `frontmatter` | validator-enforced (reusable workflow) | active |
| `adr` | yes | yes | `adr` | validator-enforced (rides frontmatter) | active |
| `python-tooling` | yes | yes | `python_tooling` | copy-adopt scaffolds | active |
| `markdown-tooling` | yes | yes | `markdown_tooling` | copy-adopt scaffolds | active |
| `cli-documentation` | yes | yes | `cli_documentation` | copy-adopt scaffolds | active |
| `project-spec` | yes | **no** | **none** | CLI-enforced (`spec` subcommand); no copy-adopt bundle | active |
| `python-coding` | **no** | no | none | not adoptable | **draft v0.4, reference-only** |

Per-standard bundle contents (in `standards/<id>/`):

- **`markdown-frontmatter`** — README; templates `concept.md`, `note.md`, `research.md`, `runbook.md`, `spec.md`, `frontmatter-minimal.yml`, `frontmatter-standard.yml`; examples `concept.example.md`, `note.example.md`, `runbook.example.md`.
- **`adr`** — README; templates `adr.md`, `adr-minimal.md`, `adr-bare.md`, `adr-bare-minimal.md`; example `adr.example.md`.
- **`python-tooling`** — README + `build-backend.md` appendix; no templates/examples (copy-adopt scaffolds live in the machine bundle).
- **`markdown-tooling`** — README only (config scaffolds live in the machine bundle).
- **`project-spec`** — README + `tooling-notes.md` resource; templates `spec-full-template.md`, `spec-standard-template.md`, `spec-light-template.md`; example `spec.example.md`.
- **`cli-documentation`** — README; templates `cli-docs-check.yml`, `readme-single-file.md`, `usage-doc.md`; example `usage.example.md`; resource `research-notes.md`.
- **`python-coding`** — README only (draft).

## 2. Machine registry — `src/project_standards/schemas/registry.json`

The registry is the central contract-version artifact `SPEC-MT01` expands into richer graph metadata. It is currently minimal and **structurally heterogeneous**, and its keys do not match the directory names.

```json
{
	"frontmatter": { "default": "1.1", "versions": { "1.1": "markdown-frontmatter" } },
	"adr": {
		"default": "1.0",
		"versions": { "1.0": { "supports_frontmatter": ["1.1"] } }
	},
	"python_tooling": { "default": "1.0", "versions": ["1.0"] },
	"markdown_tooling": { "default": "1.1", "versions": ["1.0", "1.1"] },
	"cli_documentation": { "default": "1.0", "versions": ["1.0"] }
}
```

Observations:

- **Key-name mismatch:** registry keys (`frontmatter`, `python_tooling`, …) differ from directory ids (`markdown-frontmatter`, `python-tooling`). Underscores vs hyphens.
- **Shape mismatch:** `frontmatter` maps version → schema name; `adr` maps version → an object (`supports_frontmatter` compatibility); the other three are bare version-string arrays.
- **Missing standards:** `project-spec` and `python-coding` have no entry.
- Sole reader: `src/project_standards/registry.py` (`RegistryError` on failure). Two-plane version model documented in `meta/versioning.md`.

## 3. Adopt manifests — the current `adopt.toml` model

`adopt.toml` is **artifact-focused only** (what files/fragments/callers to materialize) — it carries no identity, authority, capability, resource, or relationship metadata. It is the precursor `SPEC-MT01` keeps as the artifact plane beneath the new `standard.toml`. Artifact kinds observed: `file`, `fragment`, `workflow-caller`. Shared artifacts use `shared = "_shared/..."` and omit `owner`; owned artifacts use `source = ...` + `owner = true`.

| standard | artifacts (`kind` → dest/target) |
| --- | --- |
| `adr` | file `adr.template.md` → `docs/adr/adr.template.md`; fragment → `.project-standards.yml` |
| `cli-documentation` | file `usage-doc.md` → `docs/usage.md`; file `cli-docs-check.yml` → `.github/workflows/cli-docs-check.yml`; fragment → `.project-standards.yml` |
| `markdown-frontmatter` | file `project-standards.starter.yml` → `.project-standards.yml`; workflow-caller → `.github/workflows/validate-standards.yml` |
| `markdown-tooling` | file `markdownlint.json` → `.markdownlint.json`; file `prettierrc.json` → `.prettierrc.json`; shared `editorconfig` → `.editorconfig`; shared `vscode-extensions.json` → `.vscode/extensions.json`; workflow-callers → `.github/workflows/lint-markdown.yml` + `format.yml` |
| `python-tooling` | fragment `pyproject.python-tooling.toml` → `pyproject.toml`; files → `.python-version`, `.github/workflows/check.yml`, `scripts/check.py`, `AGENTS.md`, `CLAUDE.md`, `.vscode/settings.json`, `.vscode/tasks.json`; shared → `.editorconfig`, `.vscode/extensions.json` |

`_shared/` holds `editorconfig` and `vscode-extensions.json` (referenced by both markdown-tooling and python-tooling — the one place today where two standards deliberately share a single canonical artifact).

## 4. Schemas (`src/project_standards/schemas/`)

- **`registry.json`** — contract-version registry (see §2).
- **`markdown-frontmatter.schema.json`** — JSON Schema (draft 2020-12), `additionalProperties: false`. Required: `schema_version, id, title, description, doc_type, status, created, updated, tags, aliases, related`. `schema_version` ∈ `{1.0, 1.1}`; `doc_type` a 14-value enum; `status` a 7-value enum; `id` pattern `^[a-z0-9][a-z0-9._-]*$`; dates `^\d{4}-\d{2}-\d{2}$`.

There is **no** `standard.toml` schema and **no** authority-map schema yet — both are `SPEC-MT01` deliverables (Step 03/04).

## 5. Validator / CLI surface

Console scripts (`pyproject.toml [project.scripts]`): `project-standards`, `validate-frontmatter`, `validate-id`, `validate-references`, `format-frontmatter`, `sync-vscode-colors`, `sync-standards-include` (seven).

`project-standards` subcommands (`cli.py`): `validate`, `fix`, `spec`, `adopt`, `list`. The `spec` group (`specs/cli.py`): `validate`, `lint`, `extract`, `next`, `new`, `upgrade`.

Package modules (`src/project_standards/`), by role:

- **Validators:** `validate_frontmatter.py` (schema; also hosts the opt-in `markdown.adr` body-section check), `validate_id.py` (id format), `validate_references.py` (opt-in cross-file: id uniqueness, referential integrity, date ordering, ADR-number uniqueness).
- **Fixer:** `format_frontmatter.py` (+ shared `id_format.py`).
- **Sync utils:** `sync_standards_include.py`, `sync_vscode_colors.py`.
- **Registry reader:** `registry.py`.
- **Adopt engine (`adopt/`):** `engine.py` (`build_plan`/`execute_plan`/`format_report`), `manifest.py` (reads `adopt.toml`), `errors.py` (exit-coded `AdoptError` hierarchy).
- **Spec engine (`specs/`):** `cli.py`, `config.py`, `document.py`, `model.py`, `registry.py`, and `commands/{validate,lint,extract,next_id,new,upgrade}.py`.

No `standards_graph/` package and no `standards validate-graph` command exist yet (Step 04 deliverable). No provider registry (Step: `SPEC-MT01` FR-009).

## 6. Reusable workflows (`.github/workflows/`)

| File | `name:` | reusable (`workflow_call`)? | job name |
| --- | --- | --- | --- |
| `validate-markdown-frontmatter.yml` | Validate Markdown Frontmatter | **yes** (consumer-called) | `validate` |
| `lint-markdown.yml` | Lint Markdown | **yes** | `lint` |
| `format.yml` | Format | **yes** | `prettier` |
| `validate-specs.yml` | Validate Specs | **yes** | `validate-specs` |
| `check.yml` | Check | no — repo-internal CI | `check` |
| `coherence.yml` | Coherence | no — repo-internal CI | `coherence` |

Four reusable workflows are the consumer-facing enforcement surface; two are internal-only.

## 7. Config namespaces currently claimed

`.project-standards.yml` is the consumer config. `SPEC-MT01` (FR-005/DR-004) formalizes namespace ownership so standards cannot collide; the current claimants are:

| Top-level key | Owner | Notes |
| --- | --- | --- |
| `standards_version` | meta / versioning | the consumed-version pin, not a standard |
| `markdown` | markdown-frontmatter | holds `markdown.frontmatter.*`; `markdown.frontmatter.references` drives `validate_references` |
| `markdown.adr` (sub-namespace) | adr | `version`, `require_sections` (opt-in body-section check) |
| `python_tooling` | python-tooling | `version` (contract selection) |
| `markdown_tooling` | markdown-tooling | `version` |
| `cli_documentation` | cli-documentation | `version` |
| `spec` | project-spec | `spec.include` (which files `spec validate`/`lint` check) |

There is no machine-checked namespace registry today; ownership is implicit.

## 8. Test suite shape

- **868 tests** (collection count) across **47 `tests/test_*.py` files**.
- **`tests/coherence/`** — `test_behavioral.py`, `test_declaration.py`, `test_pins.py` (+ `declaration.py`, `corpus/adversarial.md`); backs the `coherence.yml` workflow (needs `npm ci` for the behavioral corpus).
- **Packaging tests:** `test_adopt_packaging.py`, `test_spec_packaging.py`, `test_spec_wheel_contents.py`, `test_installed_wrappers.py`, `test_version_consistency.py`.
- **`tests/fixtures/specs/`** — 18 spec fixture `.md` files (approved/valid/bad/upgrade/draft), excluded from markdownlint/Prettier as generated parser inputs.

## 9. Observable authority map (raw material for Step 04)

What each standard governs and the tool that enforces it today — the empirical basis for the future authority tuples (`SPEC-MT01` FR-004). This is observed, not the manifest.

| Standard | Concern owned | Enforcing tool / authority | Config namespace |
| --- | --- | --- | --- |
| `markdown-frontmatter` | canonical YAML frontmatter on managed Markdown | `validate_frontmatter.py` + schema; ids via `validate_id.py`; cross-file via `validate_references.py`; CI `validate-markdown-frontmatter.yml` | `markdown.frontmatter` |
| `adr` | Architecture Decision Records (MADR on the FM profile) | opt-in body-section check in `validate_frontmatter.py`; registry FM→ADR compatibility; ships `adr.template.md` | `markdown.adr` |
| `python-tooling` | Python stack / layout / CI gate / agent instructions | ruff + basedpyright(strict) + pytest + coverage + pip-audit; gate via `scripts/check.py` / `check.yml` | `python_tooling` |
| `markdown-tooling` | Markdown / structured-text lint + format | Prettier (`.prettierrc.json`) + markdownlint (`.markdownlint.json`) + EditorConfig; CI `lint-markdown.yml` + `format.yml` | `markdown_tooling` |
| `project-spec` | tiered spec format, stable IDs | `project-standards spec` CLI; CI `validate-specs.yml` | `spec` |
| `cli-documentation` | user-facing CLI usage docs + drift | ships `docs/usage.md` template + `cli-docs-check.yml`; `test_usage_doc_inventory.py` | `cli_documentation` |
| `python-coding` | code-shape / agent-behavior rules for Python | none yet (draft) | — |

Cross-cutting: the `cli.py` dispatcher owns `validate/fix/spec/adopt/list`; the adopt engine owns `adopt.toml` resolution across the five bundled standards; `registry.py` is the sole reader of `registry.json`.

## 10. Readiness gaps (grounded) — the Step 01–07 delta

The following are the concrete deltas between this baseline and `SPEC-MT01`'s target state. They are the input to the remaining steps; each will need its own design/plan.

1. **No `standard.toml` manifest** — only artifact-focused `adopt.toml`. (Steps 02–03: meta-standard + manifest schema.)
2. **No authority map** — ownership in §9 is observed, not declared or machine-checked. (Step 04.)
3. **No standards-graph validator** and no `standards validate-graph` command / `standards_graph` package. (Step 04.)
4. **Registry is minimal + heterogeneous** — no capabilities, resources, relationships, or providers; key names diverge from dir ids; shapes differ per standard. (Steps 03–04.)
5. **`project-spec` is not self-describing** — adoptable via CLI yet absent from `registry.json` and has no bundle. (Step 05 retrofit must reconcile CLI-enforced standards into the model.)
6. **`python-coding` unregistered** — draft with no manifest; needs an explicit draft/non-adoptable declaration under the new model. (Step 05.)
7. **No relationship taxonomy / independence declarations** — companions (e.g. markdown-frontmatter ↔ markdown-tooling, python-tooling ↔ python-coding) are prose-only, not typed graph edges. (Steps 03–04, `SPEC-MT01` FR-021/FR-022.)
8. **No config-namespace registry** — namespace ownership (§7) is implicit. (`SPEC-MT01` FR-005.)
9. **No agent summaries / resource indexes / provider declarations** — nothing to lazy-load or dispatch generically yet. (`SPEC-MT01` FR-007/FR-009/FR-013.)
10. **No dogfood consumer fixtures for composition** or generated standards index. (Step 06.)

Nothing above is fixed by this inventory — Step 00 only maps the ground. The readiness gate (Step 07) verifies that Steps 01–06 have closed these gaps.
