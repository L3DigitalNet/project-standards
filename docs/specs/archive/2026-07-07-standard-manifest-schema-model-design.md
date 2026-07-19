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
  - [Canonical schema generation](#canonical-schema-generation)
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

Every rule below is a **single-manifest** rule — decidable from one file, no cross-standard context. Fixed-shape tables forbid unknown keys; the one intentionally open table is `[resources]`.

- **Enums (closed).** `adoption` ∈ {`validator`, `copy-adopt`, `cli`, `reference-only`, `none`}; `status` ∈ {`draft`, `review`, `active`, `deprecated`, `archived`, `superseded`}; provider `kind` ∈ {`python`, `command`, `workflow`, `documentation-only`}.
- **Provider `operation` (open vocabulary).** A non-empty lowercase kebab token, **not** a closed enum — SPEC-MT01 lists operations by example (`validate`, `fix`, `drift-check`, `id-next`, `extract`, `semantic-review`, …) and the set is meant to grow, so freezing it here would bake a false contract. The known operations are documented; membership/registry checks are Step 04.
- **`extra = "forbid"` on fixed-shape models** — `[standard]`, `[versions]`, `[config]`, `[capabilities]`, `[relations]`, and every `[[authority]]` / `[[providers]]` block. A stray `requires` key (SPEC-BA01 `FR-005`, reserved-and-invalid) or any unknown key fails loudly. `[resources]` is exempt (next rule).
- **`[resources]` is an open URI-safe-ID → path mapping** (`FR-008`, adr-0010): required `readme`; conditional `adopt`; known optional `agent_summary` and `template`; plus **arbitrary URI-safe resource IDs** (lowercase, URI-safe token) whose values are safe bundle-relative paths. Modeled as a constrained `dict`, not a closed submodel, so future resource IDs are not rejected.
- **Identity (`FR-001` / checklist).** `[standard].id` is **kebab-case** (model-level regex); the loader additionally asserts `id` **equals the parent bundle directory name** (needs the path, so loader-level).
- **Required fields and tuple completeness** (`FR-014` checklist): `[standard]` id/name/status/summary/adoption; `[versions]` supported/latest; `[config]` namespaces; `[capabilities]` provides/consumes_platform; `[resources]` readme; each `[[authority]]` block's full `(domain, target, concern, owner, mutates)`; each `[[providers]]` block's operation/kind/optional.
- **Provider fields (`FR-007`).** Optional `input_schema` / `output_schema` are accepted (SPEC-MT01 "Should"). `entrypoint` is **required for executable kinds** (`python`/`command`/`workflow`) and **omitted for `documentation-only`**. Per-kind grammar (`FR-012`):
  - `python` — a dotted import path plus a colon-separated object: `module.path:object` (e.g. `project_standards.markdown_tooling:check_drift`).
  - `command` — a single bare command token (`[A-Za-z0-9._-]+`): no path separators, no `..`, not absolute, no whitespace or shell metacharacters (`| ; & $ \` < > ( )`).
  - `workflow` — a named reference token under the same safe-token rule; richer workflow-reference semantics are deferred to Step 04.
  - All kinds reject anything that looks like a filesystem path (contains `/` or `\`), an absolute path, `..`, or shell-metacharacter/pipeline strings.
- **Adoptability linkage (`FR-013`).** `adoption = "none"` **must not** declare an `adopt` resource (enforced). The positive rule — a _released_ adoptable standard has `adopt.md` — depends on `status` plus the file existing on disk, so it is deferred to Step 04; Step 03 enforces only the negative.
- **Dotted namespaces and reserved meta keys (`FR-006`).** Each `[config].namespaces` entry is a dotted path (config-key segments, dot-separated), no `..`; a **reserved repo-meta key** (`standards_version`) is rejected; duplicate paths _within the one manifest_ are rejected. Cross-standard duplicate-owner detection is Step 04.
- **`latest` ∈ `supported`.** When both are non-empty, `latest` must be a member of `supported` — a single-manifest consistency check.
- **Path safety, syntactic (`FR-012`).** All resource / `adopt` / template paths reject `..` segments and absolute paths at the model layer; symlink-escape resolution is loader-level (see [Data flow](#data-flow-and-errors)).

**Not schema-enforceable (policy or deferred).** SPEC-BA01's "providers are first-party" and "no network access by default" are policy statements, not properties a manifest schema can check — they stay documented in the standard, and any mechanical check is deferred. `relations.extends` is validated only for **array shape** in Step 03; the ADR-backed and acyclicity checks are Step 04.

## Data flow and errors

```text
Path -> path.read_text(encoding="utf-8") -> tomllib.loads(str) -> dict
     -> StandardManifest.model_validate(dict)      # aggregates ALL field errors
     -> loader post-checks: id == bundle dir name; declared paths resolve inside the bundle dir (symlink-safe)
     -> StandardManifest  (typed)   OR   StandardManifestError
```

`tomllib.loads` takes a `str`, so the loader reads the file as UTF-8 text first (matching `adopt/manifest.py`); `tomllib.load(fp)` on a binary handle is the equivalent alternative. `StandardManifestError` subclasses `ValueError` (like `RegistryError`) and is the **single** error type the loader raises — it wraps Pydantic's aggregated `ValidationError`, a `tomllib.TOMLDecodeError` (malformed TOML), and `OSError` (missing/unreadable file), so no raw parser or I/O traceback leaks past the boundary. It is the type a future Step 04 CLI maps to exit code 2. Symlink-escape containment (the part of `FR-012` a pure schema cannot see) lives in the loader, which resolves each declared path against the manifest's on-disk bundle directory; the model enforces only the syntactic half (no `..`, not absolute). The loader additionally asserts each declared resource file **exists** within the bundle — SPEC-MT01 requires missing resource paths to fail, and the loader is the on-disk boundary that can see it.

The **generated JSON Schema is a permissive view** of the model: `StringConstraints` patterns, enums, `required`, and `additionalProperties: false` carry over, but Pydantic does **not** emit the cross-field / custom-validator rules (`latest ∈ supported`, reserved / duplicate namespaces, `adoption = "none"` forbids `adopt`, per-kind entrypoint grammar, path safety, resource-ID key syntax). Those are **model-only**; a consumer validating with the raw schema alone gets weaker checks than `load_standard_manifest`. Tests make this split explicit (see [Testing](#testing)).

## Canonical schema generation

`StandardManifest.model_json_schema()` returns a `dict`, so a single **canonical writer** owns serialization and is used both to write the committed file and inside the drift test:

- inject `$schema` (JSON Schema Draft 2020-12) and `$id`, matching the shape of the existing `markdown-frontmatter.schema.json`;
- serialize with `json.dumps(schema, indent=2, ensure_ascii=False)` **preserving key order** (Pydantic emits a meaningful order — do **not** `sort_keys`) plus a trailing newline;
- the drift test regenerates through this same helper and asserts byte-equality with the committed `standard.schema.json`; a second test asserts the file parses as a valid JSON Schema.

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

- `StandardManifest` and `load_standard_manifest` load and validate a `standard.toml`, returning a typed object or raising `StandardManifestError` (never a raw `TOMLDecodeError` / `OSError` / `ValidationError`).
- Every valid fixture loads; every invalid fixture raises, each targeting exactly one rule from [Validation rules](#validation-rules-encoded-in-the-model).
- Identity checks hold: a bad-`id` or id/directory-mismatch manifest is rejected; a manifest claiming the reserved `standards_version` namespace is rejected.
- `standards/standard-bundle-authoring/standard.toml` validates.
- The loader rejects a manifest declaring a resource file that does not exist within the bundle.
- `src/project_standards/schemas/standard.schema.json` is committed, is produced by the canonical writer, and equals a fresh regeneration byte-for-byte (drift test green); the committed file parses as a JSON Schema.
- Every valid fixture also validates against the generated JSON Schema; the schema-expressible invalid fixtures fail it; the model-only invalid fixtures are documented as such.
- `registry.json`, bundles, and `.project-standards.yml` are unchanged.
- Full gate green, coverage at the repo bar.

## Testing

- **Valid fixtures.** A fully-populated `copy-adopt` manifest (authorities; a `python` provider with `module:object` `entrypoint` + `input_schema` / `output_schema`; a second provider with a bare `command` token `entrypoint`; `agent_summary` + `template` + a bundle-specific resource ID; companions); the `adoption = "none"` minimal shape; and a `documentation-only` provider with no `entrypoint`.
- **Invalid fixtures, one rule each:** bad `adoption`, bad `status`, a stray `requires` key, an unknown key in a fixed-shape table, a missing required field, an incomplete authority tuple, an executable provider missing `entrypoint`, a `documentation-only` provider _with_ an `entrypoint`, a filesystem-path `entrypoint`, a shell-metacharacter / pipeline `entrypoint`, a `..` / absolute resource path, an unsafe path on an arbitrary resource ID, a malformed resource ID, a malformed dotted namespace, the reserved `standards_version` namespace, a duplicate namespace, and `latest` not in `supported`.
- **Loader / boundary tests** (not just `model_validate` on prebuilt dicts): malformed TOML, a missing manifest file, a non-table root, an id / parent-directory mismatch, and a **declared resource file that does not exist** each raise `StandardManifestError` with no raw traceback.
- **Parametrized pass/fail test** over the corpus; invalid cases assert the error names the offending field.
- **Schema drift + parse tests** — regenerate via the canonical writer, compare byte-for-byte; assert the committed file parses as a JSON Schema.
- **Schema-vs-fixture semantic tests** — every valid fixture validates against the generated JSON Schema; the schema-expressible invalid fixtures (enum, `additionalProperties`, `required`, `pattern`, extra-value type) fail it; an explicit `_MODEL_ONLY` set records the invalid fixtures the schema cannot express (cross-field and custom-validator rules), each still rejected by the model.
- **Real-manifest test** — `standards/standard-bundle-authoring/standard.toml` loads and validates.
- **Symlink-escape test** — a resource path that resolves via symlink outside the bundle dir is rejected by the loader.
