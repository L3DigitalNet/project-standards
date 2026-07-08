# Design: `standard.toml` schema and model (SPEC-MT01 Step 03)

**Date:** 2026-07-07 **Status:** draft — SPEC-MT01 Step 03 (manifest schema/model + fixtures); brainstormed 2026-07-07 **Author:** session 2026-07-07

## Table of Contents

- [Design: `standard.toml` schema and model (SPEC-MT01 Step 03)](#design-standardtoml-schema-and-model-spec-mt01-step-03)
  - [Table of Contents](#table-of-contents)
  - [Problem and goal](#problem-and-goal)
  - [Scope](#scope)
  - [Decisions locked during brainstorming](#decisions-locked-during-brainstorming)
  - [Components](#components)
  - [Validation rules encoded in the model](#validation-rules-encoded-in-the-model)
  - [Data flow and errors](#data-flow-and-errors)
  - [Invariants — what must not change](#invariants--what-must-not-change)
  - [Dependency](#dependency)
  - [Non-goals (Step 04 and later)](#non-goals-step-04-and-later)
  - [Acceptance criteria](#acceptance-criteria)
  - [Testing](#testing)

## Problem and goal

The [Standard Bundle Authoring Standard](../../../standards/standard-bundle-authoring/README.md) (SPEC-BA01, approved) settled the `standard.toml` contract **in prose**: identity, adoption mode, config namespaces, capabilities, authorities, relationships, resources, providers, lifecycle, and manifest-safety rules. Nothing yet enforces that contract mechanically. This step — SPEC-MT01 Step 03 (`WH-001`) — mechanizes a **single manifest's** shape as a typed, validated model plus a generated JSON Schema and pass/fail fixtures, so Step 04's standards-graph validator has a trustworthy per-manifest foundation to build cross-standard rules on.

The goal is deliberately narrow: given one `standard.toml`, decide whether it conforms to the contract, and expose the conforming data as a typed object. Everything that requires comparing **two or more** standards is out of scope here (see [Non-goals](#non-goals-step-04-and-later)).

## Scope

One new module, one generated artifact, one fixture corpus, one test module:

- **The manifest model** — Pydantic v2 models and enums that mirror the `standard.toml` tables and encode every single-manifest rule from SPEC-BA01 (`FR-002`…`FR-014`).
- **The loader** — a function that reads a `standard.toml` off disk (`tomllib`), validates it through the model, resolves manifest paths against the bundle directory, and returns the typed object or raises a structured error.
- **The generated JSON Schema** — `model_json_schema()` output, committed under `schemas/` and guarded by a drift test (the model is the single source of truth).
- **Fixtures and tests** — valid and invalid `standard.toml` fixtures (one rule per invalid case), a parametrized pass/fail test, the drift test, and a test that the repository's one real manifest validates.

The `standard.toml` file is **external input at a boundary** — an untrusted on-disk file whose entire purpose is to be validated. Both the released `python-tooling` standard and the `python-coding` draft map external-input validation to a **Pydantic model** in their type-construct tables; this step follows that prescription, which also matches SPEC-MT01 §9's literal "Pydantic model."

## Decisions locked during brainstorming

1. **Pydantic v2 is the single source of truth.** Chosen over hand-rolled `jsonschema` + `dataclass` because the repo's own Python standards prescribe Pydantic for external-input/boundary validation (frozen dataclasses are reserved for _internal_ records). This reverses an initial lean toward the `validate_frontmatter.py` precedent, which uses JSON Schema only because it validates against _per-version_ contract schemas — a different driver.
2. **The JSON Schema is generated from the model** (`model_json_schema()`), not hand-authored — one source of truth yields both `WH-001` deliverables.
3. **The generated schema is committed and drift-tested** — `src/project_standards/schemas/standard.schema.json`, guarded by a test that regenerates from the model and asserts byte-equality, mirroring the repo's byte-lock-artifact pattern. It gives Step 04 and future MCP/consumer readers a stable, reviewable artifact.
4. **Step 03 stops at the single manifest.** No CLI subcommand, no cross-standard graph validation, no repo-wide gate wiring — all Step 04. Step 03 ships a library plus its fixtures and tests, including a test that the real `standard-bundle-authoring/standard.toml` validates (honoring SPEC-BA01 OQ-002's "Step 03 must accept it or record a supersession").

## Components

Each unit has one responsibility, follows an existing repo pattern, and is independently testable.

| Unit | File | Responsibility | Pattern it follows |
| --- | --- | --- | --- |
| Manifest model | `src/project_standards/standard_manifest.py` | Pydantic v2 models + enums for `[standard]`, `[versions]`, `[config]`, `[capabilities]`, `[relations]`, `[resources]`, `[[authority]]`, `[[providers]]`; all single-manifest validation rules. | new module; typed-view role like `registry.py` |
| Loader | same module | `load_standard_manifest(path) -> StandardManifest`: `tomllib` parse → `model_validate` → path resolution against the bundle dir; raises `StandardManifestError`. | error type like `RegistryError` / `ConfigError` |
| Generated schema | `src/project_standards/schemas/standard.schema.json` | Committed `model_json_schema()` output. | bundled schema like `markdown-frontmatter.schema.json` |
| Fixtures | `tests/fixtures/standards_manifests/{valid,invalid}/*.toml` | One rule per invalid fixture; representative valid manifests. | fixture layout like `tests/fixtures/specs/` |
| Tests | `tests/test_standard_manifest.py` | Parametrized fixtures pass/fail; schema drift test; real-manifest-validates test. | pytest + coverage gate |

The model module is intentionally the one place in the package that **omits `from __future__ import annotations`**: `python-coding` warns that modules whose annotations are consumed at runtime by Pydantic should avoid the future import unless covered by tests, and this module's field annotations are runtime-resolved. The omission is deliberate and noted in a module-header comment.

## Validation rules encoded in the model

Every rule below is a **single-manifest** rule — decidable from one file, no cross-standard context:

- **Enums.** `adoption` ∈ {`validator`, `copy-adopt`, `cli`, `reference-only`, `none`}; `status` ∈ {`draft`, `review`, `active`, `deprecated`, `archived`, `superseded`}; provider `kind` ∈ {`python`, `command`, `workflow`, `documentation-only`}; provider `operation` ∈ the known generic operations (`validate`, `fix`, `drift-check`, `id-next`, `extract`, …).
- **`extra = "forbid"` on every model.** A stray `requires` key (SPEC-BA01 `FR-005` — the reserved-and-invalid field) or any unknown key fails loudly rather than being silently ignored.
- **Required fields and tuple completeness** (`FR-014` checklist): `[standard]` id/name/status/summary/adoption; `[versions]` supported/latest; `[config]` namespaces; `[capabilities]` provides/consumes_platform; `[resources]` readme; each `[[authority]]` block's full `(domain, target, concern, owner, mutates)`; each `[[providers]]` block's operation/kind/optional (+ entrypoint for executable kinds).
- **Adoptability linkage (`FR-013`).** `adopt` is present in `[resources]` for adoptable modes and absent for `adoption = "none"`.
- **Dotted namespaces (`FR-006`).** Each `[config].namespaces` entry matches a dotted-path syntax (segments of config-key characters, dot-separated), no `..`; duplicate paths _within the one manifest_ are rejected. Cross-standard duplicate-owner detection is Step 04.
- **Path safety, syntactic (`FR-012`).** Resource, `adopt`, and template paths reject `..` segments and absolute paths at the model layer.
- **Provider entrypoint shape (`FR-012`).** `entrypoint` must look like an import path (`pkg.mod:func`) or a command reference, and is rejected if it looks like a filesystem path.

## Data flow and errors

```text
Path -> tomllib.loads(bytes) -> dict
     -> StandardManifest.model_validate(dict)   # aggregates ALL field errors
     -> path resolution vs. bundle dir          # catches symlink escape (needs the filesystem)
     -> StandardManifest  (typed)   OR   StandardManifestError
```

`StandardManifestError` subclasses `ValueError` (like `RegistryError`), wraps Pydantic's aggregated `ValidationError`, and is the type a future Step 04 CLI maps to exit code 2. Symlink-escape containment (the part of `FR-012` that a pure schema cannot see) lives in the **loader**, which knows the manifest's on-disk bundle directory and resolves each declared path against it; the model enforces only the syntactic half (no `..`, not absolute).

## Invariants — what must not change

- **No machine change to the shipped standards.** `registry.json`, the bundled adopt artifacts, and `.project-standards.yml` are untouched — Step 03 adds a reader, not a new consumer contract. (Retrofitting the seven existing standards with their own `standard.toml` is Step 05.)
- **SPEC-BA01 stays the contract.** The model encodes SPEC-BA01's rules; it does not invent new ones. A rule the model needs that SPEC-BA01 does not state is a spec gap to record, not a silent addition.
- **The one real manifest keeps validating.** `standards/standard-bundle-authoring/standard.toml` must pass, per SPEC-BA01 OQ-002.
- **Full dogfood gate stays green:** ruff format/check, basedpyright (strict), pytest + coverage, pip-audit, markdownlint, Prettier, plus the new schema drift test.

## Dependency

Adds **`pydantic>=2`** as a runtime dependency (`uv add pydantic`, `uv.lock` committed). This is policy-compliant under `python-tooling` §7 ("every new runtime dependency must have a reason"; "do not add a dependency for trivial standard-library functionality"): the standards' own construct tables prescribe Pydantic for boundary validation, and manifest validation is neither trivial nor standard-library-shaped. No other dependency is added; `tomllib` is standard library on the 3.14 baseline.

## Non-goals (Step 04 and later)

- The standards-graph loader and **cross-standard** validation: authority conflicts, duplicate namespace ownership across standards, relationship-graph acyclicity, `extends`-requires-an-ADR, and hidden-hard-dependency rejection (Step 04).
- The `project-standards standard validate` CLI subcommand and any verification-gate wiring (Step 04).
- Retrofitting the seven existing standards with `standard.toml` (Step 05).
- The generated standards index and relationship catalog (Step 06); the MCP-readiness gate (Step 07).

## Acceptance criteria

- `StandardManifest` and `load_standard_manifest` load and validate a `standard.toml`, returning a typed object or raising `StandardManifestError`.
- Every valid fixture loads; every invalid fixture raises, each targeting exactly one rule from [Validation rules](#validation-rules-encoded-in-the-model).
- `standards/standard-bundle-authoring/standard.toml` validates.
- `src/project_standards/schemas/standard.schema.json` is committed and equals `StandardManifest.model_json_schema()` (drift test green).
- `registry.json`, bundles, and `.project-standards.yml` are unchanged.
- Full gate green, coverage at the repo bar.

## Testing

- **Fixture corpus.** Valid manifests covering the adoptable shape (a representative `copy-adopt` standard with authorities + a provider) and the `adoption = "none"` shape (the meta-standard's own minimal manifest). Invalid manifests, one rule each: bad `adoption` value, bad `status`, a stray `requires` key, an unknown key, a missing required field, an incomplete authority tuple, a `..` in a resource path, an absolute resource path, a filesystem-path `entrypoint`, a malformed dotted namespace, and a duplicate namespace within the manifest.
- **Parametrized pass/fail test** over the corpus; invalid cases assert the error names the offending field.
- **Schema drift test** — regenerate from the model, compare byte-for-byte with the committed schema.
- **Real-manifest test** — `standards/standard-bundle-authoring/standard.toml` loads and validates.
- **Symlink-escape test** — a resource path that resolves (via symlink) outside the bundle dir is rejected by the loader.
