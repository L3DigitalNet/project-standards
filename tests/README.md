# Testing Strategy

This document defines how `project-standards` is tested. It is the human-facing
companion to the test code in this directory; read it before adding a new tool or
extending an existing suite.

`project-standards` is **standards-as-a-product**: it ships a JSON Schema and a
validator that *other* repositories consume by pinning to a release tag. A broken
release breaks every downstream consumer's CI. The test suite exists to make that
impossible — `main` must stay releasable at all times (see [AGENTS.md](../AGENTS.md)).

## Goals

| Goal | What it means in practice |
|---|---|
| **Protect the contract** | The schema and the shipped `examples/` must always validate. A change that breaks them must break a test first. |
| **Fast & hermetic** | No network, no global state, no real home directory. Everything runs against `tmp_path`. A full run is sub-second. |
| **Deterministic** | Same input → same result on every supported Python (3.11+). Version-dependent behaviour (e.g. `glob` `**` semantics) is pinned by regression tests. |
| **Behaviour over implementation** | Prefer asserting observable outputs (return values, exit codes, error strings) so refactors don't churn the suite. Reach into private helpers only when a unit is too awkward to reach through the public surface. |

## The three test layers

Every tool in this repo should be covered at the layers that apply to it. Most
tools touch all three.

### 1. Unit — pure functions

Test the small, side-effect-free pieces in isolation: parsers, path resolvers,
config loaders, data coercion. These are the cheapest tests and should cover every
branch, including the "weird input → safe fallback" paths (malformed YAML, a list
where a mapping was expected, a missing file).

> Example: `parse_frontmatter` returning `None` for a non-mapping block;
> `resolve_schema_path` treating a bare name as a bundled schema but a `.json`
> value as a filesystem path.

### 2. Integration — the CLI contract

Drive the tool the way CI and consumers do: through `main(argv)`, asserting the
**exit code** and stderr behaviour. The exit-code contract is part of the public
API and is documented per tool. For the validator:

| Exit code | Meaning |
|---|---|
| `0` | All matched files valid (or no files matched). |
| `1` | One or more validation errors. |
| `2` | Operator error — schema missing, unreadable, or not a valid JSON Schema. |

Every exit code must have at least one test that produces it.

### 3. Contract / dogfood — the shipped artifacts

These guard the *product*, not the code:

- **Shipped `examples/` validate.** Each file under `examples/` is a worked example
  the standard promises is correct. A parametrized test validates every one against
  the *real* bundled schema. If someone adds an example, it is tested automatically.
- **Bundled schemas are well-formed.** Each `schemas/*.schema.json` must be a valid
  Draft 2020-12 schema (`check_schema`). This catches a typo in the contract before
  it ships.

Templates are intentionally **excluded** from dogfood validation — they carry
placeholders (`YYYY-MM-DD`, `replace-with-stable-id`) that deliberately fail the
schema (see the `exclude` list in [.project-standards.yml](../.project-standards.yml)).

### 4. Regression — every fixed bug

When a bug is fixed, add a test that fails on the old behaviour and cite the cause
in the docstring. These never get deleted. Existing example:
`test_exclude_dir_glob_matches_nested_files` pins the `dir/**` exclusion bug where
`Path.glob`'s `**` matched files on 3.13+ but only directories on ≤3.12.

## Layout & naming conventions

```
tests/
  __init__.py
  README.md                     <- this file
  test_<module>.py              <- one file per tool module under tools/
  conftest.py                   <- shared fixtures/helpers (add when a 2nd tool needs them)
```

- **Mirror `tools/`.** A tool at `tools/foo.py` is tested by `tests/test_foo.py`.
  This is the documented convention (see [AGENTS.md](../AGENTS.md)) and is wired into
  `pyproject.toml` (`testpaths = ["tests"]`, pyright `include = ["tools", "tests"]`).
  Do **not** co-locate tests under `tools/`.
- **Test names describe the behaviour and the expectation:**
  `test_invalid_doc_type_fails`, `test_missing_frontmatter_returns_2`. The name
  should read as a sentence about what the code does.
- **Group with comment banners**, not test classes, unless a class earns its keep
  via shared setup. Keep functions flat and independently runnable.

## Fixtures & helpers

Reusable building blocks live at module scope (graduate them to `conftest.py` once a
second test module needs them). The validator suite establishes the patterns to copy:

| Helper | Purpose |
|---|---|
| `validator` fixture | A `Draft202012Validator` built from the real bundled schema. |
| `MINIMAL` / `STANDARD` dicts | Canonical valid frontmatter, kept as dicts so a test can mutate **one** field and assert the failure is attributable to that field. |
| `_doc(meta, ...)` | Renders a dict into a Markdown file with a YAML frontmatter block. |
| `_write` / `_check` | Write content to `tmp_path` and run it through the validator. |
| `workspace` fixture | A temp repo (with `monkeypatch.chdir`) for CLI/config tests. |

**The one-field-mutation pattern is the most important convention here:** start from
a known-good dict, change exactly one thing, and assert the error mentions that field.
It keeps negative tests precise and self-documenting.

## What must be tested (coverage policy)

This is the checklist a reviewer applies. It is deliberately about *categories*, not
a line-coverage percentage — covering every controlled vocabulary matters more than
hitting a number.

- [ ] **Happy path** — minimal and fully-populated valid input both pass.
- [ ] **Every controlled vocabulary** (`doc_type`, `status`, `confidence`,
      `visibility`, …) has at least one negative test for an out-of-vocabulary value.
- [ ] **Every required field** missing produces an error naming that field.
- [ ] **Every format constraint** (date pattern, id pattern, kebab tags,
      `uniqueItems`) has a negative test.
- [ ] **Every CLI exit code** (0/1/2) is produced by a test.
- [ ] **Every error/fallback branch** in parsing and config loading.
- [ ] **Shipped `examples/`** validate (dogfood) and **schemas** are well-formed.
- [ ] **A regression test** accompanies every bug fix.

## Running the tests

The full toolchain triad (all three must pass before committing per
[AGENTS.md](../AGENTS.md)):

```bash
uv run pytest          # behaviour
uv run ruff check .    # lint + import order
uv run pyright         # strict static types (tests are type-checked too)
```

`pytest` is configured in `pyproject.toml` (`testpaths`, `addopts = "-ra -q"`).
Useful invocations:

```bash
uv run pytest -k frontmatter         # filter by name
uv run pytest tests/test_x.py::test_y -v
uv run pytest --co -q                 # list collected tests without running
```

> Note: tests are **strictly typed**. pyright runs in `strict` mode over `tests/`,
> so annotate every fixture and test signature (`-> None`, typed params). This is
> intentional — the tests are first-class code, not throwaway scripts.

## Adding tests for a new tool

When you add `tools/<newtool>.py`:

1. Create `tests/test_<newtool>.py`.
2. Cover the three layers that apply: unit (pure helpers), integration (`main()`
   exit codes if it has a CLI), and contract/dogfood (if it reads or emits a
   shipped artifact).
3. Document its exit-code contract in a table in the test module docstring.
4. If shared fixtures emerge (a second tool needs the same helper), move them to
   `conftest.py` rather than copy-pasting.
5. Keep the triad green: `uv run pytest && uv run ruff check . && uv run pyright`.

## CI relationship

There are two enforcement gates with deliberately separate jobs:

- **The developer gate** ([.github/workflows/tests.yml](../.github/workflows/tests.yml))
  runs the toolchain triad — `ruff`, `pyright`, `pytest` — on push and PR, across a
  Python version matrix (3.11 / 3.13 / 3.14). This protects the validator's own
  logic. The matrix is load-bearing: it brackets the `glob('**')` behaviour change
  the exclude regression test guards against (see the Regression layer above).
- **The runtime gate** ([.github/workflows/validate-markdown-frontmatter.yml](../.github/workflows/validate-markdown-frontmatter.yml))
  is the *reusable* workflow consumers call. It runs the validator against managed
  Markdown — here and in consuming repos. It does **not** run pytest, and must not:
  downstream repos call it via `workflow_call` and should never inherit this repo's
  test toolchain.

Run the triad locally before every commit that touches `tools/` or `tests/` — CI is
the backstop, not a substitute for the local check:

```bash
uv run ruff check . && uv run pyright && uv run pytest
```
