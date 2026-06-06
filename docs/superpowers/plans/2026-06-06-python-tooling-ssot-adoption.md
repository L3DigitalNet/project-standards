# Python Tooling SSOT Adoption Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate this repo's Python surface to full literal compliance with `standards/python-tooling-ssot-standard.md` (v1.5), making it the reference example, without damaging the orthogonal Markdown-standard product.

**Architecture:** Staged migration where every task ends green and committable. The existing pytest suite (105 tests) is the safety net: each structural change is followed by running the suite + the relevant tool. The riskiest change (build backend → `uv_build` with the schema relocated into the package) is verified by building the wheel and inspecting it.

**Tech Stack:** uv 0.11.6 + `uv_build`, Python 3.13, ruff, basedpyright (strict), pytest + coverage.py (branch), pip-audit. Markdown product (orthogonal): Prettier 3.8.3 + markdownlint.

**Spec:** `docs/superpowers/specs/2026-06-06-python-tooling-ssot-adoption-design.md` (read it first).

**Global rules for every task:**

- Never `git add .` / `git add -A` — stage by explicit path (repo non-negotiable).
- The package import name is `project_standards`; the distribution name stays `project-standards`.
- After any Markdown/JSON/YAML edit, run `node_modules/.bin/prettier --write <files>` before committing (the repo dogfoods Prettier). If `node_modules/` is absent, run `npm ci` once.
- Commit messages end with the repo's co-author trailer: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

---

## File structure (created / moved / modified)

**Moved (`git mv`, history preserved):**

- `tools/validate_frontmatter.py` → `src/project_standards/validate_frontmatter.py`
- `tools/__init__.py` → `src/project_standards/__init__.py`
- `schemas/markdown-frontmatter.schema.json` → `src/project_standards/schemas/markdown-frontmatter.schema.json`

**Created:**

- `src/project_standards/py.typed` (empty marker)
- `.python-version`
- `.vscode/extensions.json`, `.vscode/settings.json`, `.vscode/tasks.json`
- `scripts/check.py`
- `.github/workflows/check.yml`

**Modified:**

- `pyproject.toml` (full rewrite — build backend, package, deps, all `[tool.*]`)
- `uv.lock` (regenerated)
- `src/project_standards/validate_frontmatter.py` (`find_bundled_schema`, docstring example)
- `tests/test_validate_frontmatter.py` (imports, `SCHEMA_PATH`, wheel-layout test)
- `src/project_standards/schemas/markdown-frontmatter.schema.json` (`$id`)
- `.project-standards.yml` (comments), `README.md`, `AGENTS.md`, `CLAUDE.md`, `tests/README.md`
- `standards/markdown-frontmatter.md`, `standards/adoption.md`, `standards/versioning.md`, `standards/python-tooling-ssot-standard.md` (frontmatter)
- `docs/handoff/architecture.md`, `docs/handoff/conventions.md`, `docs/handoff/state.md`
- `CHANGELOG.md`
- `.github/workflows/validate-markdown-frontmatter.yml`, `lint-markdown.yml`, `format.yml` (path filters)

**Removed:**

- `.github/workflows/tests.yml` (superseded by `check.yml`)
- Empty `tools/` and `schemas/` directories (after the moves)

---

## Task 1: Establish a green baseline (revert stray working-tree edits)

The working tree carries two stray, broken edits from a prior session. Start from green.

**Files:**

- Revert: `tests/test_markdownlint_config.py`, `project-standards.code-workspace`

- [ ] **Step 1: Inspect the stray edits (confirm they are the known breakage)**

Run: `git diff tests/test_markdownlint_config.py project-standards.code-workspace` Expected: a syntax error in the test (`[k for k: str in config ...]`) and `python.languageServer`/`python.analysis.typeCheckingMode` keys added to the workspace file.

- [ ] **Step 2: Revert both to their committed form**

```bash
git checkout -- tests/test_markdownlint_config.py project-standards.code-workspace
```

- [ ] **Step 3: Verify the baseline gate is green**

Run: `uv run pytest -q && uv run ruff check . && uv run pyright` Expected: pytest all pass (105), ruff clean, pyright 0 errors.

- [ ] **Step 4: No commit needed**

These were uncommitted edits; reverting leaves the tree at the last commit. Confirm: `git status --short` shows only the untracked `standards/python-tooling-ssot-standard.md` (and `node_modules/` if present, which `.gitignore` covers). Proceed.

---

## Task 2: Structural cut — `src/` layout + `uv_build` + package rename (kept green)

This is the atomic core: move files, switch the build backend, rename the package, fix imports, and relocate the schema — all together so `uv sync` and the test suite stay green. Type-checker stays `pyright` here; it swaps to basedpyright in Task 4.

**Files:**

- Move: the three files listed in File Structure
- Create: `src/project_standards/py.typed`
- Modify: `pyproject.toml`, `src/project_standards/validate_frontmatter.py`, `tests/test_validate_frontmatter.py`

- [ ] **Step 1: Move the package and schema into `src/`**

```bash
mkdir -p src/project_standards/schemas
git mv tools/__init__.py src/project_standards/__init__.py
git mv tools/validate_frontmatter.py src/project_standards/validate_frontmatter.py
git mv schemas/markdown-frontmatter.schema.json src/project_standards/schemas/markdown-frontmatter.schema.json
: > src/project_standards/py.typed
git add src/project_standards/py.typed
rmdir tools schemas 2>/dev/null || true
```

- [ ] **Step 2: Simplify `find_bundled_schema` to the single in-package path**

In `src/project_standards/validate_frontmatter.py`, replace the whole function:

```python
def find_bundled_schema(name: str) -> Path:
    """Resolve a bundled schema *name* to its on-disk path.

    The schema ships inside the package (``project_standards/schemas/``), so the
    same relative path resolves whether the validator runs from a source checkout
    or from a ``uv tool install`` wheel. A missing name returns the canonical
    (non-existent) path so the caller surfaces a clear read error.
    """
    return Path(__file__).parent / "schemas" / f"{name}.schema.json"
```

- [ ] **Step 3: Update the docstring usage example in the same file**

Change the line (in the module docstring, ~line 16):

```text
    validate-frontmatter --schema schemas/markdown-frontmatter.schema.json examples/*.md
```

to:

```text
    validate-frontmatter --schema src/project_standards/schemas/markdown-frontmatter.schema.json examples/*.md
```

- [ ] **Step 4: Rewrite `pyproject.toml` (intermediate — still pyright)**

Replace the entire file with:

```toml
[project]
name = "project-standards"
version = "1.2.0"
description = "Reusable project standards, templates, schemas, and validation tools."
license = "Apache-2.0"
license-files = ["LICENSE"]
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "jsonschema>=4.23.0",
    "pyyaml>=6.0.2",
]

[project.scripts]
validate-frontmatter = "project_standards.validate_frontmatter:main"

[dependency-groups]
dev = [
    "pytest>=8.3.0",
    "ruff>=0.9.0",
    "pyright>=1.1.390",
]

[build-system]
requires = ["uv_build>=0.11,<0.12"]
build-backend = "uv_build"

[tool.ruff]
line-length = 88
target-version = "py311"
extend-exclude = [".claude/hooks", "docs/handoff"]

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM"]

[tool.pyright]
typeCheckingMode = "strict"
pythonVersion = "3.11"
include = ["src", "tests"]
venvPath = "."
venv = ".venv"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra -q"
```

- [ ] **Step 5: Update test imports and `SCHEMA_PATH`**

In `tests/test_validate_frontmatter.py`, change the import block from `from tools.validate_frontmatter import (...)` to `from project_standards.validate_frontmatter import (...)` (same names), and add a module import for path resolution. The resulting import additions:

```python
import project_standards.validate_frontmatter as _vf
from project_standards.validate_frontmatter import (
    collect_paths,
    find_bundled_schema,
    load_config,
    main,
    missing_adr_sections,
    parse_frontmatter,
    resolve_schema_path,
    validate_file,
)
```

Change the `SCHEMA_PATH` definition (keep `_REPO_ROOT` for `examples/`):

```python
_REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = Path(_vf.__file__).parent / "schemas" / "markdown-frontmatter.schema.json"
```

- [ ] **Step 6: Rewrite the wheel-layout contract test**

Replace `test_find_bundled_schema_resolves_installed_wheel_layout` (and its `from tools import ...` line) with:

```python
def test_find_bundled_schema_resolves_from_package_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The schema ships inside the package (project_standards/schemas/). Simulate an
    # installed layout and confirm find_bundled_schema resolves <package>/schemas/.
    from project_standards import validate_frontmatter as vf

    pkg = tmp_path / "project_standards"
    (pkg / "schemas").mkdir(parents=True)
    schema = pkg / "schemas" / "markdown-frontmatter.schema.json"
    schema.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(vf, "__file__", str(pkg / "validate_frontmatter.py"))
    assert vf.find_bundled_schema("markdown-frontmatter") == schema
```

- [ ] **Step 7: Re-lock and sync**

```bash
uv lock
uv sync
```

Expected: resolution succeeds; the project builds with `uv_build` and installs editable.

- [ ] **Step 8: Normalize import order and run the toolchain**

```bash
uv run ruff check . --fix
uv run ruff format .
uv run ruff check . && uv run pyright && uv run pytest -q
```

Expected: ruff clean, pyright 0, pytest all pass.

- [ ] **Step 9: Verify the wheel ships the schema (acceptance #1, dry run)**

```bash
uv build --wheel
python3 -c "import zipfile,glob; print('\n'.join(zipfile.ZipFile(sorted(glob.glob('dist/*.whl'))[-1]).namelist()))" | grep schemas
rm -rf dist
```

Expected: prints `project_standards/schemas/markdown-frontmatter.schema.json`.

- [ ] **Step 10: Commit**

```bash
git add pyproject.toml uv.lock src/project_standards tests/test_validate_frontmatter.py
git commit -m "refactor: src/ layout + uv_build backend; relocate schema into package"
```

---

## Task 3: Python 3.13 baseline + Ruff line-length 100 + expanded rule set

**Files:**

- Modify: `pyproject.toml`, `.python-version` (created in Task 6 — not yet), any `src/`/`tests/` files Ruff reflows.

- [ ] **Step 1: Bump version policy and Ruff config in `pyproject.toml`**

Set `requires-python = ">=3.13"`. Replace the `[tool.ruff]` and `[tool.ruff.lint]` sections, and add format + per-file-ignores:

```toml
[tool.ruff]
target-version = "py313"
line-length = 100
src = ["src", "tests"]
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
```

Also change `[tool.pyright]` `pythonVersion = "3.11"` to `pythonVersion = "3.13"` (pyright is swapped out entirely in Task 4).

- [ ] **Step 2: Re-lock (requires-python changed) and sync**

```bash
uv lock && uv sync
```

- [ ] **Step 3: Run the fix pass, then resolve residual findings**

```bash
uv run ruff format .
uv run ruff check . --fix
uv run ruff check .
```

Expected after fixes: ruff clean. The new families (`C4`, `PIE`, `PTH`, `RET`, `RUF`) may flag a few spots in `src/project_standards/validate_frontmatter.py` — fix the code (do not add ignores) until `ruff check .` is clean. `S101` is per-file-ignored in tests; it is not otherwise selected.

- [ ] **Step 4: Verify types and tests still pass**

Run: `uv run pyright && uv run pytest -q` Expected: pyright 0, pytest all pass.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock src/project_standards tests
git commit -m "chore: Python 3.13 baseline; Ruff line-length 100 + expanded rule set"
```

---

## Task 4: Swap pyright → basedpyright (strict)

**Files:**

- Modify: `pyproject.toml`, `src/project_standards/validate_frontmatter.py` (only if strict surfaces new diagnostics)

- [ ] **Step 1: Update dependencies and type-checker config in `pyproject.toml`**

In `[dependency-groups].dev`, remove `"pyright>=1.1.390"` and add `"basedpyright"` and `"types-PyYAML"`. Remove the `[tool.pyright]` table and add:

```toml
[tool.basedpyright]
include = ["src", "tests"]
typeCheckingMode = "strict"
pythonVersion = "3.13"
pythonPlatform = "All"
failOnWarnings = true
```

- [ ] **Step 2: Re-lock and sync**

```bash
uv lock && uv sync
```

- [ ] **Step 3: Run basedpyright and resolve strict findings**

Run: `uv run basedpyright` Expected initially: possibly a small number of strict diagnostics. Resolve them properly:

- Missing PyYAML types are covered by `types-PyYAML` (added in Step 1).
- Existing `# pyright: ignore[reportUnknownMemberType]` comments are honored by basedpyright (same prefix).
- If basedpyright reports it cannot find the environment, add `venvPath = "."` and `venv = ".venv"` to `[tool.basedpyright]`.
- Fix any remaining diagnostic by tightening types, not by broad ignores. Re-run until `uv run basedpyright` reports 0 errors / 0 warnings.

- [ ] **Step 4: Confirm tests still pass**

Run: `uv run pytest -q` Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock src/project_standards tests
git commit -m "chore: replace pyright with basedpyright (strict)"
```

---

## Task 5: Add coverage + pip-audit + strict pytest config

**Files:**

- Modify: `pyproject.toml`

- [ ] **Step 1: Add dev deps, coverage config, and strict pytest options in `pyproject.toml`**

In `[dependency-groups].dev` add `"coverage[toml]"`, `"pip-audit"`, `"pytest-cov"`. Replace the `[tool.pytest.ini_options]` table and append coverage tables:

```toml
[tool.pytest.ini_options]
minversion = "9.0"
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

- [ ] **Step 2: Re-lock and sync**

```bash
uv lock && uv sync
```

- [ ] **Step 3: Run the coverage gate and the audit**

```bash
uv run coverage run -m pytest
uv run coverage report
uv run pip-audit
```

Expected: tests pass; `coverage report` total ≥ 85% with branch coverage; pip-audit reports no known vulnerabilities. If coverage is < 85%, add behavior tests for the uncovered branches `coverage report` names (do **not** lower `fail_under`). If `pip-audit` flags a dependency, update it via `uv add` and re-run.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock tests
git commit -m "chore: add coverage (branch, fail_under 85) + pip-audit; strict pytest"
```

---

## Task 6: Editor + script config artifacts

**Files:**

- Create: `.python-version`, `.vscode/extensions.json`, `.vscode/settings.json`, `.vscode/tasks.json`, `scripts/check.py`

- [ ] **Step 1: Create `.python-version`**

```text
3.13
```

- [ ] **Step 2: Create `.vscode/extensions.json` (standard set + Prettier/markdownlint)**

```json
{
	"recommendations": [
		"ms-python.python",
		"charliermarsh.ruff",
		"detachhead.basedpyright",
		"tamasfe.even-better-toml",
		"redhat.vscode-yaml",
		"github.vscode-github-actions",
		"editorconfig.editorconfig",
		"esbenp.prettier-vscode",
		"DavidAnson.vscode-markdownlint"
	]
}
```

- [ ] **Step 3: Create `.vscode/settings.json` (Python from standard + Prettier for md/json/yaml)**

```json
{
	"python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
	"python.testing.pytestEnabled": true,
	"python.testing.unittestEnabled": false,
	"python.testing.pytestArgs": ["tests"],
	"[python]": {
		"editor.defaultFormatter": "charliermarsh.ruff",
		"editor.formatOnSave": true,
		"editor.codeActionsOnSave": {
			"source.fixAll.ruff": "explicit",
			"source.organizeImports.ruff": "explicit"
		}
	},
	"ruff.nativeServer": "on",
	"basedpyright.analysis.typeCheckingMode": "strict",
	"[markdown]": { "editor.defaultFormatter": "esbenp.prettier-vscode" },
	"[json]": { "editor.defaultFormatter": "esbenp.prettier-vscode" },
	"[jsonc]": { "editor.defaultFormatter": "esbenp.prettier-vscode" },
	"[yaml]": { "editor.defaultFormatter": "esbenp.prettier-vscode" },
	"files.exclude": {
		"**/__pycache__": true,
		"**/.pytest_cache": true,
		"**/.ruff_cache": true,
		"**/.mypy_cache": true,
		"**/.coverage": true
	}
}
```

- [ ] **Step 4: Create `.vscode/tasks.json` (standard §13 verbatim)**

```json
{
	"version": "2.0.0",
	"tasks": [
		{
			"label": "check",
			"type": "shell",
			"command": "uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit",
			"group": "test",
			"problemMatcher": []
		},
		{
			"label": "fix",
			"type": "shell",
			"command": "uv run ruff format . && uv run ruff check . --fix",
			"problemMatcher": []
		},
		{
			"label": "test",
			"type": "shell",
			"command": "uv run pytest",
			"group": "test",
			"problemMatcher": []
		},
		{
			"label": "typecheck",
			"type": "shell",
			"command": "uv run basedpyright",
			"problemMatcher": []
		},
		{
			"label": "audit",
			"type": "shell",
			"command": "uv run pip-audit",
			"problemMatcher": []
		}
	]
}
```

- [ ] **Step 5: Create `scripts/check.py` (standard §18 verbatim)**

```python
from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence

COMMANDS: tuple[tuple[str, ...], ...] = (
    ("uv", "run", "ruff", "format", "--check", "."),
    ("uv", "run", "ruff", "check", "."),
    ("uv", "run", "basedpyright"),
    ("uv", "run", "coverage", "run", "-m", "pytest"),
    ("uv", "run", "coverage", "report"),
    ("uv", "run", "pip-audit"),
)


def run_command(command: Sequence[str]) -> int:
    print(f"\n$ {' '.join(command)}", flush=True)
    completed = subprocess.run(command, check=False)
    return completed.returncode


def main() -> int:
    for command in COMMANDS:
        return_code = run_command(command)
        if return_code != 0:
            return return_code
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Format the JSON, lint the script, and smoke-test the wrapper**

```bash
node_modules/.bin/prettier --write .vscode/
uv run ruff check scripts/check.py
uv run python -m scripts.check
```

Expected: Prettier rewrites the `.vscode/*.json` to the repo tab style; ruff clean on the script; `scripts.check` runs the full gate and exits 0.

- [ ] **Step 7: Commit**

```bash
git add .python-version .vscode scripts/check.py
git commit -m "chore: add .python-version, .vscode workspace, scripts/check.py"
```

---

## Task 7: CI — `check.yml` replaces `tests.yml`; fix Markdown-workflow path filters

**Files:**

- Create: `.github/workflows/check.yml`
- Remove: `.github/workflows/tests.yml`
- Modify: `.github/workflows/validate-markdown-frontmatter.yml`, `lint-markdown.yml`, `format.yml`

- [ ] **Step 1: Create `.github/workflows/check.yml`**

```yaml
name: Check

on:
  pull_request:
  push:
    branches: ['main']

jobs:
  check:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v6

      - uses: actions/setup-python@v6
        with:
          python-version-file: '.python-version'

      - uses: astral-sh/setup-uv@v8
        with:
          version: '0.11.6'
          enable-cache: true

      - name: Sync dependencies
        run: uv sync --locked --all-groups

      - name: Check formatting
        run: uv run ruff format --check .

      - name: Lint
        run: uv run ruff check .

      - name: Type check
        run: uv run basedpyright

      - name: Test with coverage
        run: uv run coverage run -m pytest

      - name: Coverage report
        run: uv run coverage report

      - name: Dependency audit
        run: uv run pip-audit
```

- [ ] **Step 2: Remove the superseded developer gate**

```bash
git rm .github/workflows/tests.yml
```

- [ ] **Step 3: Update path filters in the three Markdown-product workflows**

In `.github/workflows/validate-markdown-frontmatter.yml`, replace every `"tools/**"` filter with `"src/**"` and every `"schemas/**"` filter with `"src/project_standards/schemas/**"` (under both `push.paths` and `pull_request.paths`).

In `.github/workflows/lint-markdown.yml` and `.github/workflows/format.yml`: no `tools/`/`schemas/` filters exist — leave them unchanged.

- [ ] **Step 4: Verify YAML is well-formed**

Run: `uv run python -c "import glob,yaml; [yaml.safe_load(open(f)) for f in glob.glob('.github/workflows/*.yml')]; print('ok')"` Expected: `ok`.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/check.yml .github/workflows/validate-markdown-frontmatter.yml
git rm --cached .github/workflows/tests.yml 2>/dev/null || true
git commit -m "ci: replace tests.yml with standard check.yml; fix Markdown-workflow path filters"
```

---

## Task 8: Reference sweep + schema `$id` + dogfood the standard doc

This task clears every stale `tools/`/`schemas/` reference and makes the new standard doc validate. Apply the transformation, then prove completeness with a grep.

**Transformation rules:**

- `tools/validate_frontmatter.py` → `src/project_standards/validate_frontmatter.py`
- `tools/` (as the package/validator location) → `src/project_standards/`
- `schemas/markdown-frontmatter.schema.json` → `src/project_standards/schemas/markdown-frontmatter.schema.json` (and relative `../schemas/...` → `../src/project_standards/schemas/...`)
- old toolchain triad (`uv run pytest`, `uv run ruff check .`, `uv run pyright`) → the six-step gate

**Files & exact edits:**

- [ ] **Step 1: Schema `$id`**

In `src/project_standards/schemas/markdown-frontmatter.schema.json`, change the `$id`:

```json
"$id": "https://raw.githubusercontent.com/L3DigitalNet/project-standards/main/src/project_standards/schemas/markdown-frontmatter.schema.json",
```

- [ ] **Step 2: `.project-standards.yml` comments**

- Line 2: `# Consumed by tools/validate_frontmatter.py and the CI workflow.` → `# Consumed by src/project_standards/validate_frontmatter.py and the CI workflow.`
- Line 9: `# Bundled schema name (resolves to schemas/markdown-frontmatter.schema.json),` → `# Bundled schema name (resolves to src/project_standards/schemas/markdown-frontmatter.schema.json),`

- [ ] **Step 3: `README.md`**

- Component tree line `├── schemas/      # machine-readable JSON Schemas` → remove the standalone `schemas/` row, and change `├── tools/        # the Python validator` to `├── src/project_standards/  # the Python validator + bundled schema`. (The schema now lives inside the package; reflect that.)
- Line 30 (Schema link): update both the link text and the target path to `src/project_standards/schemas/markdown-frontmatter.schema.json`.

- [ ] **Step 4: `AGENTS.md`**

- Structure table: remove the `schemas/` row, and change the `tools/` + `tests/` row so its path cell reads `src/project_standards/` + `tests/` with the description "the Python validator (with bundled schema) and its tests".
- The "Keep the toolchain green" bullet (line ~30): replace its three commands (`uv run pytest`, `uv run ruff check .`, `uv run pyright`) with the six-step gate — `uv run ruff format --check .`, `uv run ruff check .`, `uv run basedpyright`, `uv run coverage run -m pytest`, `uv run coverage report`, `uv run pip-audit`.

- [ ] **Step 5: `CLAUDE.md` Non-Negotiables**

In the "Non-Negotiables" list, replace the "Keep the toolchain green" command chain `uv run pytest && uv run ruff check . && uv run pyright` with `uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit`.

- [ ] **Step 6: `tests/README.md`**

- Replace `tools/` references (lines ~43, 57, 61, 114, 129) with `src/project_standards/` — e.g. "one file per tool module under `src/project_standards/`" and "A tool at `src/project_standards/foo.py` is tested by `tests/test_foo.py`". In the include note, change `pyright` with `include = ["tools", "tests"]` to `basedpyright` with `include = ["src", "tests"]`.
- Replace the "triad" run blocks with the six-step gate.

- [ ] **Step 7: `standards/markdown-frontmatter.md` (real links only)**

- Line 21 (`related:` frontmatter): `- 'schemas/markdown-frontmatter.schema.json'` → `- 'src/project_standards/schemas/markdown-frontmatter.schema.json'`
- Line 37: update the two prose links — the schema link target `../schemas/markdown-frontmatter.schema.json` → `../src/project_standards/schemas/markdown-frontmatter.schema.json`, and the validator link target `../tools/validate_frontmatter.py` → `../src/project_standards/validate_frontmatter.py` (and their visible link-text paths to match).
- Line 421: same two links → `src/project_standards/...` paths.
- **Do NOT change** lines 317, 360, 372, 382, 383 — these are illustrative examples of link _style_, not pointers to this repo's schema.

- [ ] **Step 8: `standards/adoption.md` and `standards/versioning.md`**

- `adoption.md:280`: the `@v1` tag-pinned URL stays as-is (valid for the old `v1` tag); add a parenthetical note only if desired — otherwise leave (it documents the published v1 layout). Skip.
- `versioning.md:32`: in the "four things under one version number" sentence, change the validator-CLI path from `tools/` to `src/project_standards/` (the "distributed as the `project-standards` package" wording stays).

- [ ] **Step 9: `tests/test_validate_frontmatter.py` (verify, do not change line 425-426)**

Confirm `resolve_schema_path("schemas/custom.schema.json")` on lines ~425-426 is left as-is (synthetic test input, not a real path).

- [ ] **Step 10: Handoff docs**

- `docs/handoff/architecture.md`: in the component tree, merge the `schemas/` and `tools/ + tests/` lines into one row — `src/project_standards/ + tests/` → "the Python validator (validate_frontmatter.py) with bundled schema, and its pytest suite". In the relationships list, change "The validator (`tools/`) … resolves the bundled schema in `schemas/`" to "The validator (`src/project_standards/`) … resolves the bundled schema shipped inside the package".
- `docs/handoff/conventions.md`: lines 46/64 `tools/` → `src/project_standards/`; convention #3 code block → the six-step gate; add a new convention "Python tooling follows the SSOT standard" pointing at `standards/python-tooling-ssot-standard.md`.
- `docs/handoff/state.md`: update the "Gate green" line to name the six-step gate, and add a one-line note that the repo adopted the Python Tooling SSOT standard.

- [ ] **Step 11: Add frontmatter to the standard doc**

Prepend to `standards/python-tooling-ssot-standard.md` (before the `# Python Tooling SSOT Standard` H1):

```yaml
---
schema_version: '1.1'
id: 'python-tooling-ssot-standard'
title: 'Python Tooling SSOT Standard'
description: 'Standard Python tooling stack, layout, CI gate, and agent instructions for agent-authored Python projects.'
doc_type: 'reference'
status: 'active'
created: '2026-06-06'
updated: '2026-06-06'
reviewed: null
owner: ''
consumer: 'agent'
tags:
  - python
  - tooling
  - uv
  - ruff
  - standard
aliases:
  - python-tooling-standard
related: []
---
```

- [ ] **Step 12: `CHANGELOG.md` entry**

Add an entry under the newest in-progress section (match the file's existing heading style), text:

```markdown
- **Python tooling stack** adopted from `standards/python-tooling-ssot-standard.md`: `uv_build` backend, `src/` layout, the validator moved to `src/project_standards/` with the schema bundled inside the package, `basedpyright` (strict), branch coverage (`fail_under = 85`), and `pip-audit`. CI gate consolidated to `check.yml`.
- **BREAKING (CLI consumers):** `requires-python` raised `>=3.11` → `>=3.13`. Installs via `uv tool install` now require Python 3.13+.
```

- [ ] **Step 13: Format, dogfood, and prove the sweep is complete**

```bash
node_modules/.bin/prettier --write .
uv run validate-frontmatter --config .project-standards.yml
git grep -nE 'tools/|tools\.|from tools|import tools' -- . ':(exclude)uv.lock' ':(exclude)docs/superpowers/**' ':(exclude)CHANGELOG.md' | grep -v node_modules
```

Expected: Prettier clean; `validate-frontmatter` reports all managed files valid (including the newly-frontmattered standard doc); the final `git grep` returns **no** `tools/` validator/path references (matches in `CHANGELOG.md` history and `docs/superpowers/**` are excluded/allowed). Investigate and fix any unexpected match.

- [ ] **Step 14: Commit**

```bash
git add -- README.md AGENTS.md CLAUDE.md tests/README.md .project-standards.yml \
  standards/markdown-frontmatter.md standards/versioning.md standards/python-tooling-ssot-standard.md \
  src/project_standards/schemas/markdown-frontmatter.schema.json \
  docs/handoff/architecture.md docs/handoff/conventions.md docs/handoff/state.md CHANGELOG.md
git commit -m "docs: sweep tools//schemas/ references to src/ layout; dogfood standard doc; update schema \$id"
```

---

## Task 9: Final verification (full gate + wheel acceptance)

**Files:** none (verification only).

- [ ] **Step 1: Run the full verification gate**

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run coverage run -m pytest
uv run coverage report
uv run pip-audit
```

Expected: all pass; coverage ≥ 85% branch.

- [ ] **Step 2: Run the Markdown product gate**

```bash
node_modules/.bin/prettier --check .
uv run validate-frontmatter --config .project-standards.yml
```

Expected: Prettier clean; frontmatter validation passes.

- [ ] **Step 3: Acceptance #1 — wheel ships the schema and resolves by name**

```bash
uv build --wheel
python3 -c "import zipfile,glob; n=zipfile.ZipFile(sorted(glob.glob('dist/*.whl'))[-1]).namelist(); assert 'project_standards/schemas/markdown-frontmatter.schema.json' in n, n; print('schema in wheel: OK')"
uv tool install --force ./dist/*.whl
validate-frontmatter --schema "$(python3 -c 'import project_standards.validate_frontmatter as v,pathlib; print(pathlib.Path(v.__file__).parent/"schemas"/"markdown-frontmatter.schema.json")')" examples/note.example.md
uv tool uninstall project-standards
rm -rf dist
```

Expected: "schema in wheel: OK"; the installed `validate-frontmatter` command runs and validates the example. (`dist/` is gitignored.)

- [ ] **Step 4: Confirm clean tree and final state**

Run: `git status --short` Expected: clean (no stray modifications). If `uv.lock` changed during verification, commit it:

```bash
git add uv.lock && git commit -m "chore: refresh uv.lock"
```

---

## Self-review (completed by plan author)

**Spec coverage:** Workstream A → Task 2; B → Tasks 2–5; C → Task 6; D → Task 7; E → Task 2; F → Task 8 (Step 11); G → Task 8; H → Task 1; pytest-config note → Task 5; acceptance criteria → Task 9. All spec sections map to a task.

**Placeholder scan:** No "TBD"/"handle edge cases"/"similar to". Code-bearing steps show full code; mechanical doc edits give explicit transformation rules + a completeness grep. The one judgment step (fixing Ruff/basedpyright residuals) names the exact tools, the "fix not silence" rule, and a concrete re-run-until-clean exit condition.

**Type/name consistency:** Import package `project_standards` and dist name `project-standards` used consistently; `find_bundled_schema` single-arg signature unchanged; `SCHEMA_PATH` derives from `_vf.__file__`; entry point `project_standards.validate_frontmatter:main` matches the move.
