# Design: Adopt the Python Tooling SSOT Standard in `project-standards`

**Date:** 2026-06-06 **Status:** approved (brainstorming complete; awaiting implementation plan) **Author:** session 2026-06-06

## Table of Contents

- [Design: Adopt the Python Tooling SSOT Standard in `project-standards`](#design-adopt-the-python-tooling-ssot-standard-in-project-standards)
  - [Problem / Goal](#problem--goal)
  - [Decisions (locked during brainstorming)](#decisions-locked-during-brainstorming)
  - [The standard contract this adoption must satisfy](#the-standard-contract-this-adoption-must-satisfy)
  - [Workstreams](#workstreams)
    - [A. Layout migration → `src/`](#a-layout-migration--src)
    - [B. `pyproject.toml` rewrite (corrected baseline)](#b-pyprojecttoml-rewrite-corrected-baseline)
    - [C. Config artifacts](#c-config-artifacts)
    - [D. CI](#d-ci)
    - [E. Code \& test changes](#e-code--test-changes)
    - [F. Dogfood the new standard doc](#f-dogfood-the-new-standard-doc)
    - [G. Reference sweep (path/schema moves + new gate)](#g-reference-sweep-pathschema-moves--new-gate)
    - [H. Working-tree cleanup](#h-working-tree-cleanup)
  - [pytest config note](#pytest-config-note)
  - [Expected fix-up work (stricter tooling, fixed properly — never silenced)](#expected-fix-up-work-stricter-tooling-fixed-properly--never-silenced)
  - [Acceptance criteria](#acceptance-criteria)
  - [Out of scope / non-goals](#out-of-scope--non-goals)
  - [Risks](#risks)

## Problem / Goal

`standards/python-tooling-ssot-standard.md` (v1.5) defines the workstation's Python tooling stack: `uv` + `uv_build`, `src/` layout, `ruff`, `basedpyright` (strict), `pytest` + `coverage.py` (branch), `pip-audit`, a `.vscode/` workspace, a `.python-version`, a single `check.yml` CI gate, and `scripts/check.py`. This repo should become the **reference example** of that standard.

The complication: this repo's Python is not incidental. The `tools/` validator is a **shipped product** — downstream repos install `validate-frontmatter` via `uv tool install git+...@<tag>` and call reusable workflows. So the migration must preserve the wheel's ability to resolve the bundled schema by name, and must not damage the orthogonal **Markdown-standard product** (Prettier + markdownlint + the reusable `validate-markdown-frontmatter.yml` / `lint-markdown.yml` workflows) that this repo also ships.

User decision: **full literal compliance** with the Python standard, reconciled against the hybrid-product reality.

## Decisions (locked during brainstorming)

1. **Posture = full literal compliance.** Migrate the Python surface to the letter of the standard, including the consequences below.
2. **Package name = `project_standards`** (uv_build-native default; `src/project_standards/`). Changes the import path and the console-script target.
3. **Schema moves into the package** — `src/project_standards/schemas/markdown-frontmatter.schema.json`. Forced by `uv_build`: per current uv docs, _"all data files must be under the module root or a data directory"_, and `[tool.uv.build-backend].data` dirs land in the wheel's `.data/` (not the importable package). The repo-root `schemas/` directory is **retired**; the package copy is canonical.
4. **Editor config = merge.** Adopt the standard's Python editor rules + `.vscode` Python extensions/settings, but preserve the existing tab indentation for Prettier-owned filetypes (md/json/jsonc/yaml) and keep Prettier + markdownlint as the formatters/linters for _their_ filetypes. The Markdown stack is orthogonal to the Python standard, not an exception to it.
5. **`requires-python = ">=3.13"`; CI version matrix dropped.** ⚠️ Breaking for CLI consumers on 3.11/3.12, and retires the 3.11/3.13/3.14 matrix that _bracketed_ the `glob('**')` regression. The regression **test** stays (it is version-independent via `fnmatch`); CI simply no longer proves it across the 3.12/3.13 boundary. Accepted as part of literal compliance.
6. **Markdown product is preserved, not collapsed.** A _Python_ tooling standard does not govern Markdown linting/formatting. `check.yml` is the Python gate; the reusable Markdown workflows and Prettier dev gate coexist, out of the standard's scope.
7. **pytest config follows standard v1.5** — use `[tool.pytest.ini_options]` (the standard's table; works back to pytest 6.0) with `minversion = "9.0"`. v1.5 resolved the earlier table-name ambiguity; this repo simply matches it (see [pytest config note](#pytest-config-note)).

## The standard contract this adoption must satisfy

The non-mutating **verification gate** (standard §2) must pass:

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run coverage run -m pytest
uv run coverage report
uv run pip-audit
```

Plus the structural contract: `src/` layout (§4), `uv_build` backend (§3), strict `basedpyright` (§8), branch coverage ≥ 85% (§10), `pip-audit` in CI (§12), `.vscode/` with BasedPyright as the sole Python language server and Ruff as the sole format/lint authority (§13, v1.5), the standard `.editorconfig` rules for Python (§14), and the `check.yml` CI shape (§15). Agent entry points (§16) are already compliant — `CLAUDE.md`/`AGENTS.md` are thin pointers to the handoff system, an explicitly blessed pattern.

## Workstreams

### A. Layout migration → `src/`

| From | To | How |
| --- | --- | --- |
| `tools/validate_frontmatter.py` | `src/project_standards/validate_frontmatter.py` | `git mv` |
| `tools/__init__.py` | `src/project_standards/__init__.py` | `git mv` |
| `schemas/markdown-frontmatter.schema.json` | `src/project_standards/schemas/markdown-frontmatter.schema.json` | `git mv` |
| — | `src/project_standards/py.typed` | new (§4) |

- `tools/` and repo-root `schemas/` directories are removed after the moves.
- Tests stay **flat** (`tests/test_validate_frontmatter.py`, `tests/test_markdownlint_config.py`). The standard's `tests/unit/` + `tests/integration/` split is "when useful"; `tests/README.md` documents the banner-organized flat layout, and splitting is churn with no benefit here.

### B. `pyproject.toml` rewrite (corrected baseline)

Target content (`uv_build` pin set to the installed uv 0.11.6 line):

```toml
[project]
name = "project-standards"
version = "1.2.0"            # unchanged; version bump belongs to the release ritual
description = "Reusable project standards, templates, schemas, and validation tools."
license = "Apache-2.0"
license-files = ["LICENSE"]
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
  "jsonschema>=4.23.0",
  "pyyaml>=6.0.2",
]

[project.scripts]
validate-frontmatter = "project_standards.validate_frontmatter:main"

[dependency-groups]
dev = [
  "basedpyright",
  "coverage[toml]",
  "pip-audit",
  "pytest",
  "pytest-cov",
  "ruff",
  "types-PyYAML",     # basedpyright strict needs stubs for PyYAML
]

[build-system]
requires = ["uv_build>=0.11,<0.12"]  # matches installed uv 0.11.6 + standard §6 example
build-backend = "uv_build"

[tool.ruff]
target-version = "py313"
line-length = 100
src = ["src", "tests"]
# Vendored harness/agent-state Python must not be reformatted (byte-identical contract).
extend-exclude = [".claude/hooks", "docs/handoff"]

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM", "C4", "PIE", "PTH", "RET", "RUF"]
ignore = ["E501"]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
docstring-code-format = true

[tool.basedpyright]
include = ["src", "tests"]
typeCheckingMode = "strict"
pythonVersion = "3.13"
pythonPlatform = "All"
failOnWarnings = true

[tool.pytest.ini_options]            # per standard v1.5: ini_options (read by pytest 6.0+)
minversion = "9.0"                   # valid: resolved/installed pytest is 9.0.3
testpaths = ["tests"]
addopts = ["-ra", "--strict-markers", "--strict-config"]

[tool.coverage.run]
branch = true
source = ["src"]

[tool.coverage.report]
show_missing = true
skip_covered = true
fail_under = 85
```

- All `[tool.hatch.*]` tables and the `pyright` dev dependency are removed.
- No `[tool.uv.build-backend]` override is needed: `project-standards` normalizes to module `project_standards` under the default `src` module root.
- `extend-exclude` is repo-specific necessity (orthogonal to the standard), not a documented exception.
- **Regenerate and commit `uv.lock`** after the backend/deps/`requires-python` change (`uv lock`); `check.yml`'s `uv sync --locked` fails on a stale lock.
- **`coverage source = ["src"]` works because uv installs the project editable** (verified: an `_editable_impl_project_standards.pth` is present in `.venv` site-packages), so executed code resolves under `src/`. Fallback if a non-editable install is ever used: `source = ["project_standards"]`.

### C. Config artifacts

- **`.python-version`** → `3.13` (new).
- **`.vscode/extensions.json`** (new) → standard set (`ms-python.python`, `charliermarsh.ruff`, `detachhead.basedpyright`, `tamasfe.even-better-toml`, `redhat.vscode-yaml`, `github.vscode-github-actions`, `editorconfig.editorconfig`) **+** `esbenp.prettier-vscode`, `DavidAnson.vscode-markdownlint`. Explicitly **no** Pylance, Python Environments, `python-lsp-server`, or Jedi (§13 single-LS policy). The added two are not Python language servers.
- **`.vscode/settings.json`** (new) → standard's Python block verbatim (BasedPyright strict, Ruff format-on-save + code actions, pytest enabled, `files.exclude`) **+** Prettier as `editor.defaultFormatter` for `[markdown]`/`[json]`/`[jsonc]`/`[yaml]` and markdownlint enabled. Must not set Pylance or weaken `basedpyright.analysis.typeCheckingMode`.
- **`.vscode/tasks.json`** (new) → standard's `check` / `fix` / `test` / `typecheck` / `audit` verbatim.
- **`.editorconfig`** → unchanged. It already satisfies the standard for Python (`[*.py]` space/4) and YAML (`[*.{yml,yaml}]` space/2) and Markdown (`[*.md]` no-trim); the tab default is required for the Prettier-owned filetypes (the chosen merge).
- **`scripts/check.py`** (new) → standard §18 wrapper verbatim. Not added to `basedpyright.include`/`ruff.src` (matches the standard).
- **`project-standards.code-workspace`** → reverted to its committed form `{ "folders": [{ "path": "." }], "settings": {} }` (discards the stray type-checking-disable edit).

### D. CI

- **Replace `tests.yml` → `.github/workflows/check.yml`** (standard §15): `actions/checkout@v6`, `actions/setup-python@v6` with `python-version-file: ".python-version"`, `astral-sh/setup-uv@v8` (pinned uv version + `enable-cache: true`), `uv sync --locked --all-groups`, then the six gate steps (ruff format-check, ruff check, basedpyright, coverage run, coverage report, pip-audit). **Single 3.13 runner.**
- **Keep** `validate-markdown-frontmatter.yml`, `lint-markdown.yml`, `format.yml` (Markdown product). Update path filters: `tools/**` → `src/**`; `schemas/**` → `src/project_standards/schemas/**`.
- `dependabot.yml` unchanged (GitHub-Actions ecosystem only; orthogonal).

### E. Code & test changes

- **`find_bundled_schema`** ([validate_frontmatter.py](../../../src/project_standards/validate_frontmatter.py)) simplifies: with the schema in-package, source-checkout and wheel paths coincide → single candidate `Path(__file__).parent / "schemas" / filename`, with the missing-name fallback returning that canonical path (preserves the "surface a clear read error" contract + its unit test).
- **Imports** in `tests/test_validate_frontmatter.py`: `from tools.validate_frontmatter import ...` → `from project_standards.validate_frontmatter import ...`; `from tools import validate_frontmatter as vf` → `from project_standards import ...`.
- **`SCHEMA_PATH`** in tests: resolve via the package, not repo root — `Path(vf.__file__).parent / "schemas" / "markdown-frontmatter.schema.json"`.
- **`test_find_bundled_schema_resolves_installed_wheel_layout`**: rewrite for in-package resolution (the wheel and source layouts are now identical; the test asserts `<package>/schemas/` resolution).
- All assertions remain behavior-level; no test is weakened to pass.

### F. Dogfood the new standard doc

- `standards/python-tooling-ssot-standard.md` is under `standards/**`, which `.project-standards.yml` requires to validate. It currently has **no frontmatter** → the dogfood gate fails. Add canonical frontmatter matching the sibling standards: `schema_version: '1.1'`, stable `id`, `title`, `description`, `doc_type: 'reference'`, `status: 'active'`, `created`/`updated: '2026-06-06'`, `tags`, `aliases`, `related`. The visible "Status: ... 1.5 ..." prose line stays as the human-facing version banner.

### G. Reference sweep (path/schema moves + new gate)

The `tools/` → `src/project_standards/` and schema relocation touch references across the repo. A `git grep -E 'tools/|tools\.|schemas/'` enumerated them; the implementation must clear the full set, not a subset.

**Update** (real pointers):

- **Code/config:** `tests/test_validate_frontmatter.py` imports (workstream E); `tools/validate_frontmatter.py:16` docstring `--schema` example; `.project-standards.yml` header comments (L2 "Consumed by tools/…", L9 "resolves to schemas/…"); `validate-markdown-frontmatter.yml` path filters (workstream D).
- **Managed standards docs** (Prettier + markdownlint + frontmatter-validated — keep all three clean): `standards/markdown-frontmatter.md` — the `related:` entry (L21) and the prose links to schema/validator (L37, L421); `standards/adoption.md:280` (tag-pinned schema URL); `standards/versioning.md:32` (the "`tools/`" validator description).
- **Handoff + human docs:** `README.md` (component tree L13/L16; schema link L30 → becomes the deep nested path); `tests/README.md` (mirror-`tools/` wording, the `pyright`→`basedpyright` include note L61, triad → gate); `docs/handoff/architecture.md` (L10/L13/L21); `docs/handoff/conventions.md` (L46/L64 + §3 gate command + a new convention recording Python tooling follows the SSOT standard); `docs/handoff/state.md` (gate command + migration note); `AGENTS.md` (component table L18/L20 + Non-Negotiables gate); `CLAUDE.md` (Non-Negotiables gate).
- **New gate string** wherever the old triad appears: `uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit` (plus the existing `validate-frontmatter` dogfood).
- **`CHANGELOG.md`** — ADD a migration entry, flagging `requires-python` `>=3.11` → `>=3.13` as breaking for CLI consumers (exact version/section deferred to the release ritual).

**Leave unchanged** (changing these would be wrong):

- `CHANGELOG.md:116,119` — historical v1.x entries; the files _were_ at `tools/`/`schemas/` then.
- `standards/markdown-frontmatter.md:317,360,372,382-383` — illustrative examples of repo-root-relative link _style_, not pointers to this repo's schema.
- `tests/test_validate_frontmatter.py:425-426` — a synthetic `schemas/custom.schema.json` test input, not the real schema.

**Sub-decision — schema `$id`:** [markdown-frontmatter.schema.json](../../../src/project_standards/schemas/markdown-frontmatter.schema.json) sets `$id` to `…/main/schemas/markdown-frontmatter.schema.json`, which 404s after the move. The validator reads the schema from disk (never via `$id`) and no external `$ref` consumer is known, so it is low-risk. **Decided:** update `$id` to the new `…/main/src/project_standards/schemas/…` path for consistency. Tag-pinned links (e.g. `adoption.md@v1`) stay valid for the old `v1` tag and only update when a new major tag ships the new layout.

### H. Working-tree cleanup

- Revert the two stray broken edits: `tests/test_markdownlint_config.py` (restores the committed version — its inferred types already pass basedpyright; the added annotations included a syntax error) and `project-standards.code-workspace` (per C).

## pytest config note

Standard v1.5 already specifies the correct table, so this repo simply follows it — no correction to the standard is required (an earlier draft's "rename `[tool.pytest]`" instinct was superseded by v1.5).

- **Use `[tool.pytest.ini_options]`** with `minversion = "9.0"`. This table is read by pytest back to 6.0; native `[tool.pytest]` config exists only since pytest 9.0 (verified empirically — pytest 9.0.3 reads both tables), so `ini_options` is the portable, copy-everywhere choice.
- **`minversion = "9.0"` is satisfied** — uv resolves the unpinned `pytest` to **9.0.3** under `requires-python >=3.13`. The pairing also fails loudly on an older pytest (the table is still read on 8.x, so `minversion` aborts) rather than silently ignoring config — the reason v1.5 prefers `ini_options` over `[tool.pytest]`.

## Expected fix-up work (stricter tooling, fixed properly — never silenced)

- **basedpyright strict** is stricter than the current `pyright` strict: `types-PyYAML` added; `jsonschema` `iter_errors`/`check_schema` already carry `# pyright: ignore[reportUnknownMemberType]` (basedpyright honors the `pyright:` prefix); expect a small number of additional strict diagnostics to resolve. If basedpyright cannot find the venv under `uv run`, add `venvPath`/`venv` (kept minimal to match the standard otherwise).
- **Ruff new rule families** (`C4`, `PIE`, `PTH`, `RET`, `RUF`): run the fix pass, then resolve residual findings in `src/` and `tests/`.
- **88 → 100 line length** reflows some wraps; expected formatter churn.
- **Coverage ≥ 85% branch** is very likely given the existing suite; if a gap surfaces, add tests (do not lower the threshold).

## Acceptance criteria

1. `uv build` produces a wheel containing `project_standards/schemas/markdown-frontmatter.schema.json`, and a tool install of that wheel resolves the schema by name (the downstream `uv tool install` contract). Prototype-verified during design — a throwaway `uv_build` 0.11.6 build shipped `<pkg>/schemas/*.json` with no extra config; this criterion re-runs it against the real package.
2. The full verification gate passes: ruff format-check, ruff check, basedpyright (strict, 0), `coverage run -m pytest` (all tests green), coverage report ≥ 85% branch, pip-audit clean.
3. `uv run validate-frontmatter --config .project-standards.yml` passes (dogfood), including the newly-frontmattered standard doc.
4. The Markdown product still passes: `npx prettier --check .` and markdownlint clean.
5. `check.yml` runs the gate on a 3.13 runner; the three Markdown workflows retain correct path filters.

## Out of scope / non-goals

- The `1.3.0` release ritual (tag, move `v1`, fast-forward `main`) — separate, pre-existing next step.
- Versioning the migration / choosing the new SemVer level — the release ritual decides.
- Splitting tests into `unit/` + `integration/` directories.
- Adding a Python ecosystem entry to `dependabot.yml`.
- Any change to the Markdown standard, schema vocabulary, or reusable-workflow contracts beyond path filters.

## Risks

- **Wheel does not ship the schema** — **retired**: verified that `uv_build` 0.11.6 includes package data files (`<pkg>/schemas/*.json`) in the wheel by default. Acceptance #1 re-checks on the real build; `validate-markdown-frontmatter.yml`'s consuming-repo path exercises it end-to-end.
- **basedpyright strict surfaces broad third-party-typing noise** — mitigated by `types-PyYAML` and scoped, reasoned `# pyright: ignore[...]` only where a dependency genuinely lacks type metadata.
- **requires-python `>=3.13` breaks downstream CLI installs on 3.11/3.12** — accepted per the locked posture; recorded in `CHANGELOG.md` for the release.
