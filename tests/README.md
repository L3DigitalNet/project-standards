# Testing Strategy

This document defines how `project-standards` is tested. It is the human-facing companion to the test code in this directory; read it before adding a new tool or extending an existing suite.

`project-standards` is **standards-as-a-product**: it ships a JSON Schema and a validator that _other_ repositories consume by pinning to a release tag. A broken release breaks every downstream consumer's CI. The test suite exists to make that impossible — `main` must stay releasable at all times (see [AGENTS.md](../AGENTS.md)).

## Table of Contents

- [Testing Strategy](#testing-strategy)
  - [Table of Contents](#table-of-contents)
  - [Goals](#goals)
  - [The test layers](#the-test-layers)
    - [1. Unit — pure functions](#1-unit--pure-functions)
    - [2. Security invariants — path safety](#2-security-invariants--path-safety)
    - [3. Integration — the CLI contract](#3-integration--the-cli-contract)
    - [4. Contract / dogfood — shipped artifacts](#4-contract--dogfood--shipped-artifacts)
    - [5. Packaging — the shipped wheel](#5-packaging--the-shipped-wheel)
    - [6. Regression — every fixed bug](#6-regression--every-fixed-bug)
  - [Layout \& naming conventions](#layout--naming-conventions)
  - [Fixtures \& helpers](#fixtures--helpers)
  - [What must be tested (coverage policy)](#what-must-be-tested-coverage-policy)
  - [Running the tests](#running-the-tests)
  - [Adding tests for a new tool](#adding-tests-for-a-new-tool)
  - [CI relationship](#ci-relationship)

## Goals

| Goal | What it means in practice |
| --- | --- |
| **Protect the contract** | The schema and the shipped examples (`standards/*/examples/`) must always validate. A change that breaks them must break a test first. |
| **Fast & hermetic** | No network, no global state, no real home directory. Everything runs against `tmp_path`. A full run (excluding packaging) is sub-second. |
| **Deterministic** | Same input → same result on every supported Python (3.14+). Version-dependent behaviour (e.g. `glob` `**` semantics) is pinned by regression tests. |
| **Behaviour over implementation** | Prefer asserting observable outputs (return values, exit codes, error strings) so refactors don't churn the suite. Reach into private helpers only when a unit is too awkward to reach through the public surface. |

## The test layers

Every tool in this repo should be covered at the layers that apply to it.

### 1. Unit — pure functions

Test the small, side-effect-free pieces in isolation: parsers, path resolvers, config loaders, data coercion. These are the cheapest tests and should cover every branch, including the "weird input → safe fallback" paths (malformed YAML, a list where a mapping was expected, a missing file).

> Examples: `parse_frontmatter` returning `None` for a non-mapping block; `resolve_schema_path` treating a bare name as a bundled schema but a `.json` value as a filesystem path; `build_plan` deduplicating shared artifacts; `resolve_source` rejecting `..`-traversal paths.

### 2. Security invariants — path safety

Path-safety assertions live in their own module (`test_adopt_safety.py`) because they are a distinct failure domain from functional correctness. A test that proves the engine refuses to write outside `--dest` is not a unit test of the engine's logic — it is a proof of a security contract. Keep these separate so a reviewer can audit them at a glance.

Invariants covered: absolute-path rejection, `..`-traversal rejection, lexical containment under `--dest`, symlinked-leaf skip, symlinked-ancestor skip.

### 3. Integration — the CLI contract

Drive the tool the way CI and consumers do: through `main(argv)`, asserting the **exit code** and stderr behaviour. The exit-code contract is part of the public API.

**Frontmatter / id validators** (`test_validate_frontmatter.py`, `test_validate_id.py`):

| Exit code | Meaning                                                                  |
| --------- | ------------------------------------------------------------------------ |
| `0`       | All matched files valid (or no files matched).                           |
| `1`       | One or more validation errors.                                           |
| `2`       | Operator error — schema missing, unreadable, or not a valid JSON Schema. |

**Adopt engine** (`test_adopt_cli.py`):

| Exit code | Meaning |
| --- | --- |
| `0` | Adopt succeeded (or dry-run completed). |
| `1` | Recoverable I/O failure during write (`WriteError`). |
| `2` | Invocation / manifest-authoring error — unknown standard, destination collision, registry/bundle drift, non-directory `--dest` (`UsageError`, `RegistryError`). |
| `3` | Missing prerequisite — broken or absent manifest, source file not in bundle tree, package version unresolvable (`ManifestError`). |

Every exit code must have at least one test that produces it.

### 4. Contract / dogfood — shipped artifacts

These guard the _product_, not the code:

- **Shipped examples validate.** Each file under a bundle's `examples/` (`standards/*/examples/`) is a worked example the standard promises is correct. A parametrized test validates every one against the _real_ bundled schema. If someone adds an example, it is tested automatically.
- **Bundled schemas are well-formed.** Each `src/project_standards/schemas/*.schema.json` must be a valid Draft 2020-12 schema (`check_schema`). This catches a typo in the contract before it ships.
- **Bundle source files match repo root.** Files that are both bundled (in `bundles/`) _and_ dogfooded in this repo (e.g. `.editorconfig`, `check.yml`) must be byte-identical. `test_adopt_dogfood.py` asserts this so that fixing the repo copy without updating the bundle (or vice versa) is caught immediately.
- **Bundle workflow callers have the correct `{{ref}}` substitution.** After materialization, workflow-caller files should reference `uses: …@v<major>`.

Templates are intentionally **excluded** from dogfood validation — they carry placeholders (`YYYY-MM-DD`, `replace-with-stable-id`) that deliberately fail the schema (see the `exclude` list in [.project-standards.yml](../.project-standards.yml)).

### 5. Packaging — the shipped wheel

`test_adopt_packaging.py` builds the wheel with `uv build` and inspects the zip to confirm that `bundles/` and all `adopt.toml` manifests are present. This is the only test that shells out — it is **slow** (several seconds). Filter it out during tight iteration:

```bash
uv run pytest -k "not packaging"
```

Run it before releasing and after any change to `pyproject.toml`, `MANIFEST.in`, or `bundles/`.

### 6. Regression — every fixed bug

When a bug is fixed, add a test that fails on the old behaviour and cite the cause in the docstring. These never get deleted. Existing example: `test_exclude_dir_glob_matches_nested_files` pins the `dir/**` exclusion bug where `Path.glob`'s `**` matched files on 3.13+ but only directories on ≤3.12 (a historical divergence — the repo now supports 3.14+ only, but the regression test stays as a guard).

## Layout & naming conventions

```text
tests/
  __init__.py
  README.md                         ← this file
  conftest.py                       ← shared fixtures/helpers (add when a 2nd module needs them)

  # Frontmatter + id validators
  test_validate_frontmatter.py      ← src/project_standards/validate_frontmatter.py
  test_validate_id.py               ← src/project_standards/validate_id.py

  # Adopt engine (split by concern — see note below)
  test_adopt_cli.py                 ← CLI surface: adopt | list | validate dispatch (cli.py)
  test_adopt_engine.py              ← build_plan / execute_plan / major_ref / format_report
  test_adopt_manifest.py            ← adopt.toml reader, available_standards, load_manifest
  test_adopt_safety.py              ← path-safety invariants (traversal, symlink, containment)
  test_adopt_dogfood.py             ← bundle vs repo-root byte identity; workflow-caller refs
  test_adopt_packaging.py           ← wheel contains bundles (slow — shells out to uv build)

  # Internal maintenance tools
  test_markdownlint_config.py       ← src/project_standards/… markdownlint config logic
  test_sync_standards_include.py    ← src/project_standards/sync_standards_include.py
  test_sync_vscode_colors.py        ← src/project_standards/sync_vscode_colors.py
```

**Adopt tests are split by concern, not by source module.** The adopt subpackage (`adopt/engine.py`, `adopt/manifest.py`, `adopt/errors.py`) has orthogonal concerns that would be awkward to mix in one file: functional logic, manifest parsing, path-security invariants, dogfood assertions, and a slow packaging build. Each concern gets its own module. This is the documented exception to the one-file-per-source-module rule.

For all other tools: mirror `src/project_standards/`. A tool at `src/project_standards/foo.py` is tested by `tests/test_foo.py`. This convention is wired into `pyproject.toml` (`testpaths = ["tests"]`, basedpyright `include = ["src", "tests"]`). Do **not** co-locate tests under `src/project_standards/`.

**Test names describe the behaviour and the expectation:** `test_invalid_doc_type_fails`, `test_missing_frontmatter_returns_2`, `test_validate_dest_rejects_traversal`. The name should read as a sentence about what the code does.

**Group with comment banners**, not test classes, unless a class earns its keep via shared setup. Keep functions flat and independently runnable.

## Fixtures & helpers

Reusable building blocks live at module scope (graduate them to `conftest.py` once a second test module needs them). The validator suite establishes the patterns to copy:

| Helper | Purpose |
| --- | --- |
| `validator` fixture | A `Draft202012Validator` built from the real bundled schema. |
| `MINIMAL` / `STANDARD` dicts | Canonical valid frontmatter, kept as dicts so a test can mutate **one** field and assert the failure is attributable to that field. |
| `_doc(meta, ...)` | Renders a dict into a Markdown file with a YAML frontmatter block. |
| `_write` / `_check` | Write content to `tmp_path` and run it through the validator. |
| `workspace` fixture | A temp repo (with `monkeypatch.chdir`) for CLI/config tests. |

**The one-field-mutation pattern is the most important convention here:** start from a known-good dict, change exactly one thing, and assert the error mentions that field. It keeps negative tests precise and self-documenting.

## What must be tested (coverage policy)

This is the checklist a reviewer applies. It is deliberately about _categories_, not a line-coverage percentage — covering every controlled vocabulary matters more than hitting a number.

- [ ] **Happy path** — minimal and fully-populated valid input both pass.
- [ ] **Every controlled vocabulary** (`doc_type`, `status`, `confidence`, `visibility`, …) has at least one negative test for an out-of-vocabulary value.
- [ ] **Every required field** missing produces an error naming that field.
- [ ] **Every format constraint** (date pattern, id pattern, kebab tags, `uniqueItems`) has a negative test.
- [ ] **Every CLI exit code** — 0/1/2 for validators; 0/1/2/3 for adopt — is produced by at least one test.
- [ ] **Every error/fallback branch** in parsing and config loading.
- [ ] **Shipped `examples/`** validate (dogfood) and **schemas** are well-formed.
- [ ] **Bundle↔repo byte identity** — every file in `_DOGFOOD` in `test_adopt_dogfood.py` stays in sync.
- [ ] **Path-safety invariants** — traversal, absolute paths, symlinked leaf, symlinked ancestor.
- [ ] **A regression test** accompanies every bug fix.

## Running the tests

The full gate (all six must pass before committing per [AGENTS.md](../AGENTS.md)):

```bash
uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit
```

`pytest` is configured in `pyproject.toml` (`testpaths`, `addopts = "-ra -q"`). Useful invocations:

```bash
uv run pytest -k frontmatter          # filter by name
uv run pytest tests/test_adopt_cli.py::test_adopt_creates_files -v
uv run pytest --co -q                  # list collected tests without running
uv run pytest -k "not packaging"       # skip the slow wheel-build test
```

> Note: tests are **strictly typed**. basedpyright runs in `strict` mode over `tests/`, so annotate every fixture and test signature (`-> None`, typed params). This is intentional — the tests are first-class code, not throwaway scripts.

## Adding tests for a new tool

When you add `src/project_standards/<newtool>.py`:

1. Create `tests/test_<newtool>.py`.
2. Cover the layers that apply: unit (pure helpers), security invariants (if the tool handles paths), integration (`main()` exit codes if it has a CLI), and contract/dogfood (if it reads or emits a shipped artifact).
3. If the tool has a CLI, document its exit-code contract in a table in the test module docstring.
4. If shared fixtures emerge (a second tool needs the same helper), move them to `conftest.py` rather than copy-pasting.
5. Keep the gate green: `uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit`.

When you add a new **subpackage** with orthogonal concerns (like `adopt/`), split tests by concern rather than by source module. Each concern file should have a single, auditable focus — a reviewer looking for path-safety tests should find them all in one place.

## CI relationship

There are two enforcement gates with deliberately separate jobs:

- **The developer gate** ([.github/workflows/check.yml](../.github/workflows/check.yml)) runs the full verification gate — `ruff format --check`, `ruff check`, `basedpyright`, `coverage run -m pytest`, `coverage report`, `pip-audit` — on push and PR, on Python 3.14. This protects the validator's own logic. The `glob('**')` behaviour change is guarded directly by its version-independent regression test (`test_exclude_dir_glob_matches_nested_files`, which exercises the `fnmatch`-based exclusion), so the gate no longer needs a Python version matrix to bracket it (see the Regression layer above).
- **The runtime gate** ([.github/workflows/validate-markdown-frontmatter.yml](../.github/workflows/validate-markdown-frontmatter.yml)) is the _reusable_ workflow consumers call. It runs the validator against managed Markdown — here and in consuming repos. It does **not** run pytest, and must not: downstream repos call it via `workflow_call` and should never inherit this repo's test toolchain.

Run the gate locally before every commit that touches `src/project_standards/` or `tests/` — CI is the backstop, not a substitute for the local check:

```bash
uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit
```
