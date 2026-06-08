---
schema_version: '1.1'
id: 'python-tooling-ssot-standard'
title: 'Python Tooling SSOT Standard'
description: 'Standard Python tooling stack, layout, CI gate, and agent instructions for agent-authored Python projects.'
doc_type: 'reference'
status: 'active'
created: '2026-06-06'
updated: '2026-06-08'
reviewed: null
owner: ''
consumer: 'mix'
tags:
  - 'python'
  - 'tooling'
  - 'uv'
  - 'ruff'
  - 'standard'
aliases:
  - 'python-tooling-standard'
related:
  - 'meta/versioning.md'
  - 'standards/python-coding/README.md'
source: []
confidence: 'high'
visibility: 'internal'
license: null
---

# Python Tooling SSOT Standard

Status: Source-checked standard, contract version 1.0 (a copy-adopted label; selected by consumers via python_tooling.version — see meta/versioning.md) Owner: Project standards / repository template Last updated: 2026-06-07 Last source check: 2026-06-06 Scope: Python projects primarily authored or modified by Claude Code, Codex CLI, and VS Code-based agents.

---

## Evidence convention

This document separates **source-backed facts** from **project policy decisions**.

- Source-backed facts cite source IDs such as `[S04]`.
- Every source ID is listed in [Source register](#24-source-register), with `Last checked: 2026-06-06`.
- Policy decisions are explicitly local standards for this project ecosystem. They may be informed by sources, but the final choice is a standard, not a claim that the source mandates it.
- Version pins in examples are template defaults and must be rechecked when the standard is reviewed.

---

## 1. Purpose

This document defines the standard Python tooling stack, repository layout, editor configuration, CI gate, and agent instructions for Python projects.

The standard is optimized for projects where AI coding agents write most implementation code and the human operator acts as architect, reviewer, and project manager.

The goal is to make every repository recoverable, repeatable, and self-explaining:

- An agent can inspect the repository and identify the correct commands.
- The same underlying commands work in CLI, VS Code, and CI.
- Agent instructions are discoverable either directly or through an approved pointer/session handoff system.
- Types communicate intent to future agents.
- Tests define expected behavior.
- Dependency and environment state are reproducible.
- Tooling choices are boring, fast, and difficult to misconfigure.

Policy decision: prefer a small strict toolchain over many overlapping tools. This reduces contradictory feedback for LLM coding agents.

---

## 2. Core contract

Python projects must have one obvious verification gate. This is the command sequence that proves the repository is clean without mutating source files:

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run coverage run -m pytest
uv run coverage report
uv run pip-audit
```

Python projects may also expose a fix pass for local and agent use. This pass is allowed to modify source files:

```bash
uv run ruff format .
uv run ruff check . --fix
```

Source basis:

- `uv run` runs commands in the project environment and verifies that the lockfile and environment are in sync before command execution. [S04]
- Ruff provides Python linting and formatting. [S08]
- BasedPyright supports project configuration through `[tool.basedpyright]` in `pyproject.toml`. [S11]
- pytest is a Python testing framework and supports `pyproject.toml` configuration. [S13]
- coverage.py measures code coverage during test execution and reads `pyproject.toml` configuration when TOML support is available. [S15]
- pip-audit scans Python environments for packages with known vulnerabilities using the Python Packaging Advisory Database. [S16]

Policy decision: code is not complete until the verification gate passes, unless the final response explicitly reports what failed and why.

---

## 3. Standard stack

| Layer | Standard | Source-backed basis | Policy |
| --- | --- | --- | --- |
| Python version | Python 3.14 baseline | Python versions receive maintenance/stable, then security, then end-of-life phases. [S03] | Use `requires-python = ">=3.14"` unless project constraints require otherwise. |
| Project manager | `uv` | uv projects define dependencies in `pyproject.toml`; uv creates/manages `.python-version`, `.venv`, and `uv.lock` in project workflows. [S04] | uv owns dependency resolution, lockfile, virtual environment, and command execution. |
| Project config | `pyproject.toml` | PyPA describes `pyproject.toml` as configuration for packaging tools and other tools such as linters and type checkers. [S01] | Keep project/tool config centralized in `pyproject.toml` unless a tool requires otherwise. |
| Lockfile | `uv.lock` | uv creates `uv.lock` for projects and uses it during project commands. [S04] | Commit `uv.lock` for application/internal projects. |
| Virtual environment | `.venv/` | uv creates a project virtual environment; `.venv` is the default project environment path. [S04], [S05] | `.venv/` is local only and must not be committed. |
| Build backend | `uv_build` | uv provides a native `uv_build` backend and documents the `build-system` snippet. [S07] | Default for pure-Python packages; use another backend when project constraints require it. |
| Layout | `src/` layout | pytest good integration practices strongly suggest `src` layout, especially with default import mode. [S14] | Required for importable projects. |
| Formatter | `ruff format` | Ruff formatter is designed as a drop-in replacement for Black and integrates with Ruff. [S10] | Ruff owns Python formatting. |
| Linter/import sorter | `ruff check` | Ruff is a Python linter and formatter; Ruff configuration is supported in `pyproject.toml`. [S08], [S09] | Ruff owns linting and import sorting. |
| Type checker | `basedpyright` | BasedPyright supports `[tool.basedpyright]` in `pyproject.toml`. [S11] | Use strict type checking for new `src/` code. |
| Tests | `pytest` | pytest supports small readable tests and scales to complex tests. [S13] | pytest is the default test framework. |
| Coverage | `coverage.py` | coverage.py measures code coverage during test execution. [S15] | Branch coverage is enabled. |
| Vulnerability scan | `pip-audit` | pip-audit scans Python packages for known vulnerabilities. [S16] | Run in CI for normal application projects. |
| Editor standard | VS Code workspace config | VS Code stores workspace settings in `.vscode/settings.json`, and workspace settings are project-specific and shareable in version control. [S17] | Project behavior only, not personal UI preferences. |
| CI | GitHub Actions | uv documents using `astral-sh/setup-uv`, `actions/setup-python`, `uv sync`, and `uv run` in GitHub Actions. [S20] | CI runs the same gate as local/agent workflows. |

### Non-default tools

These tools are not part of the baseline unless a project-specific exception is documented:

- Poetry
- Pipenv
- PDM
- Black
- isort
- Flake8
- Pylint
- mypy
- tox
- nox
- Bandit
- pre-commit

Policy decision: this is not a claim that these tools are bad. It is a local standard to avoid overlapping tools that produce competing instructions for coding agents.

This list is a **per-project add prohibition**, not an automatic instruction to uninstall every matching executable from a workstation. A workstation may already contain tools installed through multiple layers: `uv tool`, `pip --user`, the OS package manager, editor extensions, npm, or a project-local virtual environment. Removing a pre-existing tool requires layer-specific review. [S34], [N01]

### Workstation provisioning boundary

This standard is primarily **repository-scoped**. It defines how each Python project declares and runs its own toolchain. Workstation provisioning is a separate layer.

If global command-line access is desired for ad-hoc work outside a project, install global development CLIs through `uv tool`, not `pip install --user` and not the OS package manager. `uv tool install` exposes executables on `PATH` while keeping each tool in an isolated virtual environment. [S34]

Default global development CLIs:

| Tool | Global via `uv tool` | Reason |
| --- | --: | --- |
| `ruff` | Yes | Useful for ad-hoc formatting/linting outside a project. |
| `basedpyright` | Yes | Useful as a standalone type checker and language-server executable. [S35] |
| `pip-audit` | Yes | Useful as a standalone audit utility. |
| `pytest` | No, for new projects | Test execution should normally run inside the project environment with `uv run pytest`; uv documents using `uv run` rather than isolated tool execution when the tool needs the project installed. [S34] |
| `coverage` | No, for new projects | Coverage is coupled to the project test environment and should normally run through `uv run coverage ...`. |

Existing global tools may be retained when they support known non-uv workflows. For example, a pre-existing system `pytest` may remain if it is load-bearing for existing scripts or test suites. This exception does not change the rule for new repositories: new projects must declare pytest and coverage in their project dev dependencies and invoke them through `uv run`. [S13], [S34], [N01]

Do not reconcile a workstation by deleting unrelated Python application/runtime libraries from `pip --user` or system site-packages. This standard governs the development-tooling stack, not every Python-based application installed on a machine. [N01]

Before removing an OS package, check reverse dependencies with the OS package manager and consider the blast radius. OS packages may be shared by unrelated workflows and often require elevated privileges. [N01]

---

## 4. Repository layout

Default layout:

```text
project-name/
	pyproject.toml
	uv.lock
	.python-version
	.gitignore
	.editorconfig
	README.md
	AGENTS.md        # full agent instructions or pointer to approved session memory/handoff source
	CLAUDE.md        # Claude-specific instructions or pointer when Claude Code is used
	.github/
		workflows/
			check.yml
	.vscode/
		extensions.json
		settings.json
		tasks.json
	src/
		package_name/
			__init__.py
			py.typed
	tests/
		unit/
		integration/
	scripts/
		check.py
```

Source basis:

- uv project documentation lists `pyproject.toml`, `.python-version`, `.venv`, and `uv.lock` as project structure components. [S04]
- pytest good integration practices strongly suggest `src` layout. [S14]
- VS Code stores shareable workspace settings in `.vscode`. [S17]
- VS Code tasks are configured from `.vscode/tasks.json`. [S18]
- EditorConfig files define coding style across editors and work well with version control. [S19]
- Codex reads `AGENTS.md` files before work and supports layered project guidance and fallback instruction filenames. [S31]
- Claude Code uses `CLAUDE.md` files and auto memory as complementary context systems loaded at the start of sessions. [S30]

Layout rules:

- Use `src/` layout for all importable projects.
- Put application/library code under `src/<package_name>/`.
- Put tests under `tests/`.
- Use `tests/unit/` and `tests/integration/` when the distinction is useful.
- Include `py.typed` for typed packages that are intended to expose typed interfaces to downstream users.
- Do not place importable **product** modules in the repository root — the package lives under `src/<package_name>/`.
- The `src/` requirement governs the **importable package/product only**. Python that is _not_ part of the package — repo tooling (e.g. `lint.py`, `format.py`, `scripts/check.py`), automation under `scripts/`, archived or finished-but-staged scripts, and non-product scripts kept elsewhere in a repo (e.g. a configs repo's `global/`) — **MAY live outside `src/`**.
- Such out-of-`src/` Python is still part of the repo: it is linted and formatted (§11) and SHOULD carry at least basic typing, but it need not be an importable package module and is not held to the strict-typing bar required of `src/` product code (§8).
- Avoid _ad hoc importable-module_ sprawl in the root; named repo-tooling scripts are fine, but product code belongs under `src/`.
- Project automation scripts belong in `scripts/` (or another clearly non-product location).
- `AGENTS.md` and `CLAUDE.md` may be full instruction files or thin pointer files.
- A pointer file is acceptable when it resolves to an approved session memory, handoff, or project-instructions system.
- Pointer files must make the canonical instruction source discoverable from a fresh CLI or VS Code agent session.
- Alternate instruction systems must preserve the verification gate, fix pass, dependency rules, typing rules, testing rules, and VS Code rules defined by this standard.
- Directories governed by **external programs** — `.claude/`, `.agents/`, `.codex/`, `.vscode/`, `.github/`, `.venv/`, `.continue/`, and the like — are owned by those tools and are **not linted, formatted, or type-checked** by this standard; exclude them from the toolchain (§6, §11).

Policy decision: the layout is optimized for import correctness and agent navigability, not minimum file count. Agent instruction files are treated as discoverable entry points, not necessarily as the only storage location for all instructions. The stack itself is mandatory for every repo that follows this standard; what is flexible is the **scope** of files the linter, formatter, and type checker run over — never whether the stack is present.

---

## 5. Python version policy

Default `pyproject.toml`:

```toml
requires-python = ">=3.14"
```

Default `.python-version`:

```text
3.14
```

Source basis:

- PyPA documents `requires-python` as project metadata under `[project]`. [S01]
- uv project workflows create/read `.python-version`; uv also documents using `.python-version` with GitHub Actions. [S04], [S20]
- CPython's devguide documents the status phases for Python versions: maintenance/stable, security, and end-of-life. [S03]

Rules:

- `pyproject.toml` defines the supported Python version range.
- `.python-version` defines the default local interpreter for the repository.
- Agents must not change the Python version unless the task explicitly requires it.
- Raise the baseline only after dependency compatibility is verified.
- For libraries intended for external reuse, supported Python versions may be broader, but the CI matrix must prove support.

Policy decision: Python 3.14 is the default baseline for this standard as of 2026-06-07 — the current stable CPython release. Raising the baseline is a MAJOR-level change for copy-adopting consumers (see [`meta/versioning.md`](../../meta/versioning.md)); projects with dependency or platform constraints may pin a lower `requires-python` per the rules above until their dependencies support 3.14.

---

## 6. `pyproject.toml` baseline

Use this as the default starting point for new Python projects.

Source basis:

- `pyproject.toml` is the packaging/tool configuration center. [S01], [S02]
- Dependency groups are defined in `pyproject.toml` and are suitable for development use cases such as linting and testing. [S06]
- uv documents `uv_build` as a native backend and shows the `[build-system]` snippet. [S07]
- Ruff, BasedPyright, pytest, and coverage.py support configuration through `pyproject.toml` or project configuration. [S09], [S11], [S13], [S15]

```toml
[project]
name = "example-project"
version = "0.1.0"
description = "Short project description."
readme = "README.md"
requires-python = ">=3.14"
dependencies = []

[dependency-groups]
dev = [
	"basedpyright",
	"coverage[toml]",
	"pip-audit",
	"pytest",
	"pytest-cov",
	"ruff",
]

[build-system]
requires = ["uv_build>=0.11,<0.12"]
build-backend = "uv_build"

[tool.ruff]
target-version = "py314"
line-length = 100
src = ["src", "tests"]
# Directories owned by external programs are never linted/formatted by this standard.
# Extend with vendored/generated/archived paths a project opts out of.
extend-exclude = [".claude", ".agents", ".codex", ".continue"]

[tool.ruff.lint]
select = [
	"E",    # pycodestyle errors
	"F",    # pyflakes
	"I",    # import sorting
	"B",    # bugbear
	"UP",   # pyupgrade
	"SIM",  # simplification
	"C4",   # comprehensions
	"PIE",  # misc improvements
	"PTH",  # pathlib
	"RET",  # return-value issues
	"RUF",  # Ruff-specific rules
]
ignore = [
	"E501", # formatter owns line wrapping
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = [
	"S101", # assert is normal in pytest tests if security rules are later enabled
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
docstring-code-format = true

[tool.basedpyright]
include = ["src", "tests"]
typeCheckingMode = "strict"
pythonVersion = "3.14"
pythonPlatform = "All"
failOnWarnings = true

[tool.pytest.ini_options]
minversion = "9.0"
testpaths = ["tests"]
addopts = [
	"-ra",
	"--strict-markers",
	"--strict-config",
]

[tool.coverage.run]
branch = true
source = ["src"]

[tool.coverage.report]
show_missing = true
skip_covered = true
fail_under = 85
```

Notes:

- The pytest table uses `[tool.pytest.ini_options]` as the standard table. pytest 9.0 also supports native TOML config under `[tool.pytest]`, but `[tool.pytest.ini_options]` remains supported and is safer for templates because it is recognized by pytest versions back to 6.0. [S13]
- Keep `minversion = "9.0"` in the active pytest table so older pytest versions fail explicitly instead of silently ignoring newer expectations.
- `fail_under = 85` is a default threshold, not a universal measure of quality.
- Branch coverage is required as a project policy because LLM-authored tests often cover happy paths while missing decision behavior.
- Project-specific packages may add more Ruff rules, but must not weaken the baseline without a documented exception.

---

## 7. Dependency policy

Agents must use `uv` for dependency changes.

Runtime dependency:

```bash
uv add package-name
```

Development dependency:

```bash
uv add --dev package-name
```

Remove dependency:

```bash
uv remove package-name
```

Source basis:

- uv supports project dependency management through `pyproject.toml`. [S04]
- uv verifies lockfile/environment sync before `uv run`. [S04], [S05]
- Dependency groups are appropriate for development dependencies such as linting and testing. [S06]

Rules:

- `uv.lock` must be updated and committed when dependencies change.
- Do not edit lockfiles manually.
- Do not add a dependency for trivial standard-library functionality.
- Do not add frameworks to solve small problems.
- Every new runtime dependency must have a reason.
- Prefer boring, maintained, widely used packages.
- Prefer libraries with type hints or usable stubs.
- Avoid abandoned packages unless there is no reasonable alternative.

Agent final responses must mention any dependency added or removed.

---

## 8. Type policy

Strict typing is mandatory for new `src/` code.

Scope: strict typing applies to `src/` product code and `tests/` (the default `[tool.basedpyright].include`). Repo tooling and automation scripts that live outside `src/` are linted and formatted (§11) and SHOULD carry at least basic typing, but they are not held to the strict-`src/` bar by default; a project MAY add specific paths to `[tool.basedpyright].include` to type-check them too.

Source basis:

- Python's `typing` module provides support for type hints; type annotations are not enforced by Python at runtime, but can be used by third-party tools such as type checkers, IDEs, and linters. [S21]
- Python's `typing` module includes advanced type-hinting vocabulary. [S21]
- `@dataclass(frozen=True)` emulates immutability by adding methods that raise `FrozenInstanceError` on mutation attempts. [S22]
- Pydantic models instantiate outputs that adhere to specified types and constraints; Pydantic guarantees output types/constraints, not raw input data. [S23]
- BasedPyright can be configured in `[tool.basedpyright]` and supports project baselines for staged adoption. [S11], [S12]

Required:

- All public functions must have parameter and return annotations.
- All public methods must have parameter and return annotations.
- Constructors must be typed.
- Module-level constants must be typed when the type is not obvious.
- Internal functions should be typed unless they are extremely small and obvious.
- `None` must be explicit as `T | None`.
- Collections must use parameterized types such as `list[str]`, `dict[str, int]`, and `Sequence[Path]`.
- Public interfaces must avoid vague `dict`, `list`, and `tuple` types.

Preferred constructs:

| Situation | Preferred construct | Source basis |
| --- | --- | --- | --- |
| External input/output validation | Pydantic model | [S23] |
| Internal immutable record | `@dataclass(frozen=True)` | [S22] |
| Mutable internal record | `@dataclass` | [S22] |
| Dictionary-shaped data that should remain a dictionary | `TypedDict` | [S21] |
| Structural behavior interface | `Protocol` | [S21] |
| Limited string options | `Literal` or `Enum` | [S21] |
| Semantically distinct string/int identifiers | `NewType` | [S21] |
| Path values | `pathlib.Path` | [S24] |
| Optional value | `T | None` | [S21] |

Discouraged:

- Implicit `Any`
- Untyped public functions
- Broad `dict[str, Any]` return values
- Boolean flags that should be enums or literals
- Stringly typed internal contracts
- `# type: ignore` without a reason
- Type weakening to silence diagnostics

Type ignore policy:

```python
# pyright: ignore[reportUnknownMemberType]  # Third-party package lacks type metadata for this dynamic attribute.
```

Do not use broad ignores:

```python
# type: ignore
```

Policy decision: types are treated as part of the agent-readable specification, not as decorative annotations.

---

## 9. Testing policy

pytest is the default test framework.

Source basis:

- pytest is designed for small readable tests and can scale to complex functional tests. [S13]
- pytest supports `pyproject.toml` configuration through `[tool.pytest.ini_options]` and, in pytest 9.0+, through native `[tool.pytest]`. [S13]
- pytest good integration practices document `src` layout recommendations. [S14]

Configuration policy:

- Use `[tool.pytest.ini_options]` in `pyproject.toml` for this standard.
- Do not use `[tool.pytest]` in template repositories unless the project explicitly requires pytest 9.0+ native TOML configuration and documents that exception.
- Keep `--strict-config` and `--strict-markers` in the active pytest table. A misplaced pytest table is a silent failure risk because pytest may still collect and run tests using defaults.

Every feature should have tests for:

- happy path
- invalid input
- boundary case
- expected failure behavior
- regression case when fixing a bug

Test naming:

```python
def test_<unit>__<condition>__<expected_result>() -> None:
		...
```

Example:

```python
def test_parse_config__missing_required_field__raises_validation_error() -> None:
		...
```

Agent rules:

- New behavior requires tests.
- Bug fixes require regression tests.
- Tests must assert behavior, not implementation details.
- Do not weaken tests to make implementation pass.
- Do not delete failing tests unless the intended behavior has changed and the change is explicit.
- Do not write tests that simply mirror the implementation.
- Prefer small unit tests for pure logic.
- Add integration tests for filesystem, network, database, CLI, or API boundaries.

Policy decision: tests are a behavior contract for future agents.

---

## 10. Coverage policy

Default:

```bash
uv run coverage run -m pytest
uv run coverage report
```

Source basis:

- coverage.py measures code coverage during test execution. [S15]
- coverage.py can read configuration from `pyproject.toml` when TOML support is available. [S15]
- coverage.py reports can include missed branches. [S25]

Rules:

- Branch coverage must be enabled.
- Default coverage threshold is 85%.
- Generated files may be excluded.
- Coverage threshold may be raised by project type.
- Coverage threshold may be temporarily lowered only with a documented migration plan.

Policy decision: do not treat high coverage as proof of correctness. LLM-authored tests can produce high coverage with weak assertions.

---

## 11. Ruff policy

Ruff owns:

- formatting
- linting
- import sorting
- modernization checks selected in this standard

Source basis:

- Ruff is documented as a Python linter and formatter. [S08]
- Ruff respects `pyproject.toml`, `ruff.toml`, and `.ruff.toml` configuration files. [S09]
- Ruff's formatter is designed as a drop-in replacement for Black, with direct integration with Ruff. [S10]
- Ruff's VS Code extension provides Python code formatting features. [S26]

Agents must not add Black, isort, Flake8, or Pylint unless the project standard is explicitly changed.

### Scope

Ruff lints and formats **all first-party Python in the repository**, including tooling and automation scripts outside `src/` — not just the package. Two categories are out of scope:

- **External-program directories** — `.claude/`, `.agents/`, `.codex/`, `.vscode/`, `.github/`, `.venv/`, `.continue/`, and similar. They are governed by the tools that own them and must not be linted, formatted, or type-checked.
- **Vendored, generated, or archived code** a project deliberately opts out of, via `[tool.ruff].extend-exclude` (and, for type checking, `[tool.basedpyright].exclude`).

The **stack is non-negotiable**: every project runs the full toolchain (uv, Ruff, BasedPyright, pytest + coverage, pip-audit). What a project may tune is the **scope** those tools cover (`extend-exclude`, `[tool.basedpyright].include`/`exclude`) — never the presence of a tool.

Default commands:

```bash
uv run ruff format .
uv run ruff check . --fix
```

Check-only commands:

```bash
uv run ruff format --check .
uv run ruff check .
```

Rules:

- Formatting disputes are resolved by Ruff.
- Imports are organized by Ruff.
- Do not manually fight formatter output.
- Do not add per-file ignores unless the reason is local and documented.
- Prefer fixing the code over ignoring the rule.

---

## 12. Security policy

Default vulnerability scan:

```bash
uv run pip-audit
```

Source basis:

- pip-audit scans Python environments for packages with known vulnerabilities and uses the Python Packaging Advisory Database via the PyPI JSON API. [S16]

Rules:

- CI must run `pip-audit` for normal application projects.
- Security-sensitive projects may add Bandit or other scanners.
- Bandit is not part of the universal baseline because it can add noise to small internal tools.
- Do not commit secrets.
- Do not hardcode API keys, tokens, passwords, or private endpoints.
- Use environment variables or secret managers for secrets.
- File paths, shell commands, URLs, and user input must be treated as untrusted at boundaries.

Add stronger security tooling when a project includes:

- authentication
- authorization
- public network services
- subprocess execution
- user-uploaded files
- secrets handling
- database writes
- payment or financial data
- personal data

Policy decision: pip-audit is the universal baseline; extra scanners are threat-model driven.

---

## 13. VS Code standard

VS Code configuration is included to make editor-based agents and human editing behave like CLI and CI.

VS Code is not the source of truth. It is a front end over the same `uv`, Ruff, BasedPyright, pytest, and coverage commands.

Source basis:

- VS Code workspace settings are project-specific, are stored in a `.vscode` folder at the project root, and can be shared in version control. [S17]
- VS Code tasks can run external tools, and workspace/folder tasks are configured in `.vscode/tasks.json`. [S18]
- VS Code Python testing can be configured with `python.testing.pytestEnabled` and related settings in `settings.json`. [S27]
- BasedPyright's VS Code extension provides VS Code language-server integration and depends on `ms-python` for automatic Python interpreter detection when BasedPyright is installed inside a virtual environment. [S28]
- BasedPyright's IDE documentation recommends disabling or uninstalling Pylance unless the project depends on Pylance-exclusive features. [S28]
- Ruff's editor integration provides formatting and code actions, including fix-all and organize-imports actions. [S26]
- The Python Environments extension provides VS Code UI support for environment/package management and supports managers including `uv`; this standard treats it as optional UI, not project authority. [S33]

Allowed workspace configuration:

```text
.vscode/
	extensions.json
	settings.json
	tasks.json
```

Workspace settings may define project behavior:

- interpreter path
- formatter
- linter
- type checker
- testing configuration
- task commands
- generated/cache file exclusions

Workspace settings must not define personal preferences:

- theme
- font
- minimap
- icon theme
- window layout
- zoom
- keybindings
- personal telemetry choices

### `.vscode/extensions.json`

```json
{
	"recommendations": [
		"ms-python.python",
		"charliermarsh.ruff",
		"detachhead.basedpyright",
		"tamasfe.even-better-toml",
		"redhat.vscode-yaml",
		"github.vscode-github-actions",
		"editorconfig.editorconfig"
	]
}
```

Policy decision: extension recommendations are intentionally limited to project behavior, syntax/config assistance, and quality gate integration.

### Python language-server policy

The standard Python language server is **BasedPyright**.

Use exactly one semantic/type authority and exactly one formatting/linting authority:

- Semantic/type authority: BasedPyright.
- Format/lint/import authority: Ruff.
- Test/debug/interpreter integration: VS Code Python extension plus `uv`.

Do not include `ms-python.vscode-pylance` in standard extension recommendations. Pylance has been intentionally removed from this standard. BasedPyright's IDE documentation recommends disabling or uninstalling Pylance unless the project depends on Pylance-exclusive features. [S28]

Do not add `python-lsp-server`, Jedi language server, or another Python language server to the standard VS Code recommendation unless a specific project records a documented exception.

The Python Environments extension, `ms-python.vscode-python-envs`, is optional. It may be used as a VS Code convenience layer for environment/package UI, but the repository authority remains `.python-version`, `pyproject.toml`, `uv.lock`, `.venv`, and `uv` commands. [S33]

Policy decision: editor tooling must not create overlapping authorities for the same concern. Agents should not add Pylance, Python Environments, or another language server merely because VS Code suggests it.

### `.vscode/settings.json`

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

	"files.exclude": {
		"**/__pycache__": true,
		"**/.pytest_cache": true,
		"**/.ruff_cache": true,
		"**/.mypy_cache": true,
		"**/.coverage": true
	}
}
```

### `.vscode/tasks.json`

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

VS Code agent rule:

- Use repository tasks when possible: `check`, `fix`, `test`, `typecheck`, `audit`.
- Treat BasedPyright as the Python language server and Ruff as the format/lint/import server.
- Do not modify `.vscode/settings.json` to bypass Ruff, BasedPyright, pytest, coverage, or uv.
- Do not add Pylance, Python Environments, `python-lsp-server`, Jedi language server, or another overlapping Python language server without a documented project exception.
- Do not add personal editor preferences to workspace settings.

### CLI-agent language-server policy

The same language-server authority rule applies outside VS Code. Claude Code, Codex, and other CLI coding agents should use **BasedPyright** as the Python semantic/type authority when they expose an LSP integration. BasedPyright provides both the `basedpyright` CLI and `basedpyright-langserver` script when installed. [S35]

Ruff remains the formatting/lint/import authority. Do not add Microsoft Pyright, Pylance, `python-lsp-server`, Jedi language server, or another Python language server to a CLI-agent integration unless a project records a documented exception.

For Claude Code, the standard local pattern is a small LSP-only plugin that points to `basedpyright-langserver` and disables any overlapping Pyright LSP plugin. Claude Code plugin manifests support `lspServers`, can refer to a separate `.lsp.json`, and skills-directory plugins can be disabled/reloaded by name. [S36]

Example `.lsp.json` pattern:

```json
{
	"basedpyright": {
		"command": "/absolute/path/to/basedpyright-langserver",
		"args": ["--stdio"],
		"extensionToLanguage": { ".py": "python", ".pyi": "python" }
	}
}
```

CLI-agent implementation rules:

- Prefer an absolute path for the LSP `command` unless the tool's plugin/runtime documentation guarantees the expected `PATH`.
- Use `--stdio` for stdio-based LSP clients.
- Use the agent tool's own plugin-management CLI rather than hand-editing multiple state files when enabling or disabling plugins.
- Keep LSP-only plugins free of model-context skill content unless the plugin intentionally provides instructions as well as tooling.
- Verify the effective LSP after changes, not merely the files on disk.

Policy decision: the standard is not VS Code-specific. The invariant is one semantic/type authority and one format/lint/import authority across every editing surface: VS Code, Claude Code, Codex, CI, and shell.

---

## 14. `.editorconfig`

Use this file in every repository. It is the **shared superset** `.editorconfig` that `project-standards adopt` materializes — the same file the Markdown Tooling standard adopts — so a repo that adopts both standards gets one reconciled floor instead of two divergent copies.

Source basis:

- EditorConfig helps maintain consistent coding styles across multiple editors/IDEs and is version-control friendly. [S19]
- EditorConfig supports properties such as charset, indentation, line endings, trailing whitespace, final newline, and `root = true`. [S19]

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = tab
indent_size = 2

[*.py]
indent_style = space
indent_size = 4

[*.toml]
indent_style = space
indent_size = 4

[*.{yml,yaml}]
indent_style = space
indent_size = 2

[*.md]
trim_trailing_whitespace = false
```

Policy decision: the global `indent_style = tab` makes JSON/JSONC and Markdown tab-indented to match Prettier (which emits tabs), while the language toolchains pin their own indentation — Python and TOML use 4 spaces (PEP 8 / ruff), and YAML uses 2 spaces because the YAML spec forbids tabs in indentation. This **reconciles** the previously documented "spaces for `*.{toml,yml,yaml,json,md}`" rule with the Markdown Tooling floor so the two standards share a single `.editorconfig`; because Python Tooling is copy-adopt (never inherited automatically), the change to JSON/Markdown indentation cannot newly-fail an existing consumer. Markdown trailing whitespace is not trimmed because Markdown uses trailing spaces intentionally for hard line breaks.

---

## 15. GitHub Actions standard

`.github/workflows/check.yml`:

Source basis:

- uv's GitHub Actions guide recommends `astral-sh/setup-uv`, documents use with `actions/setup-python`, and shows `uv sync` plus `uv run pytest`. [S20]
- uv's GitHub guide shows `python-version-file: ".python-version"`. [S20]
- uv's GitHub guide says pinning to a specific uv version is best practice. [S20]

```yaml
name: Check

on:
	pull_request:
	push:
		branches: ["main"]

jobs:
	check:
		runs-on: ubuntu-latest

		steps:
			- uses: actions/checkout@v6

			- uses: actions/setup-python@v6
				with:
					python-version-file: ".python-version"

			# SHA-pin setup-uv: as of v8.0.0 it publishes NO moving major/minor tag
			# (no `@v8`/`@v8.0`), so a tag pin no longer resolves. Pin a full-version
			# commit SHA with the version in a trailing comment (GitHub/Astral hardening
			# guidance) and let Dependabot bump it. Re-resolve the SHA when adopting.
			- uses: astral-sh/setup-uv@fac544c07dec837d0ccb6301d7b5580bf5edae39 # v8.2.0
				with:
					# Pin this to the current reviewed uv version when applying the template.
					# Example: version: "0.11.6" (the version this repo currently pins).
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

Rules:

- CI must use the lockfile.
- CI must not install dependencies outside uv.
- CI must run formatting check, lint, type check, tests, coverage report, and audit.
- CI failures must not be bypassed by weakening the standard without a documented exception.
- CI should be kept boring and transparent.

Policy decision: pin action major versions in templates; pin action SHAs or exact action versions for hardened/security-sensitive repositories.

---

## 16. Agent instruction interface

`AGENTS.md` is the default cross-agent entry point, but this standard does not require the complete instruction body to live inside `AGENTS.md`. A repository may use a custom session memory, handoff, or project-instruction system when the agent-visible result meets the same intent.

Source basis:

- Codex reads `AGENTS.md` files before doing work, layers global and project guidance, and supports configured fallback filenames for existing instruction files. [S31]
- Claude Code uses `CLAUDE.md` files and auto memory as complementary context systems; both are loaded at the start of conversations and are treated as context rather than enforced configuration. [S30]
- The public AGENTS.md convention describes `AGENTS.md` as a predictable place to give agents project context, build/test commands, and conventions. [S32]

Accepted patterns:

- Full `AGENTS.md` and full `CLAUDE.md` files.
- Thin `AGENTS.md` and/or `CLAUDE.md` pointer files that direct agents to the canonical instruction source.
- A repo-local handoff file, memory index, or project-standard file referenced from `AGENTS.md` or `CLAUDE.md`.
- A Codex fallback filename configured through Codex project-doc discovery.
- Claude Code auto memory, `.claude/rules/`, or another Claude-compatible mechanism, when the project entry point explains how to resolve the canonical instructions.

Non-negotiable outcomes:

- A fresh CLI agent session can discover the canonical instructions before editing code.
- A VS Code-based agent session can discover the same canonical instructions before editing code.
- The resolved instructions expose the verification gate and fix pass.
- The resolved instructions preserve this standard's dependency, typing, testing, security, and editor rules.
- The alternate system must not silently weaken this standard. Exceptions must be explicit and project-scoped.
- If the pointer or handoff source is unavailable, the agent must report that the instruction source cannot be resolved rather than guessing.

Policy decision: `AGENTS.md` and `CLAUDE.md` are agent-visible entry points. They may be compact pointers if the resolved instruction system is equivalent in effect.

### 16.1 Full `AGENTS.md` template

Copy this into `AGENTS.md`, or into the canonical instruction source reached by a thin `AGENTS.md` pointer. Adapt only where necessary.

````markdown
# Python Project Agent Instructions

## Operating model

This repository follows the Python Tooling SSOT Standard.

Use the existing project structure and tools. Do not replace the tooling stack unless explicitly instructed.

If this repository uses a custom session memory or handoff system, resolve that system before editing and treat the resolved instructions as the active implementation contract. Alternate systems are acceptable only when they preserve the verification gate, fix pass, dependency rules, typing rules, testing rules, security rules, and VS Code rules in this standard.

## Fix pass

When changing Python code, run the fix pass first:

```bash
uv run ruff format .
uv run ruff check . --fix
```

## Verification gate

Before considering work complete, run the non-mutating verification gate:

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run coverage run -m pytest
uv run coverage report
uv run pip-audit
```

Do not claim completion if any verification command fails.

## Dependency rules

- Use `uv add <package>` for runtime dependencies.
- Use `uv add --dev <package>` for development dependencies.
- Do not manually edit `uv.lock`.
- Do not add dependencies for trivial standard-library functionality.
- Explain any new dependency in the final response.

## Typing rules

- All new `src/` code must pass strict BasedPyright.
- Do not introduce untyped public functions.
- Do not use implicit `Any`.
- Do not use broad `dict`, `list`, or `tuple` contracts when a better type shape is available.
- Prefer Pydantic models for external input/output boundaries.
- Prefer dataclasses for internal records.
- Prefer `Protocol` for behavior-oriented interfaces.
- Prefer `TypedDict` only when the object is intentionally dictionary-shaped.
- Avoid `# type: ignore`; if unavoidable, include the exact rule and reason.

## Testing rules

- New behavior requires tests.
- Bug fixes require regression tests.
- Tests must assert behavior, not implementation details.
- Do not weaken or delete tests to make the suite pass unless the intended behavior explicitly changed.

## Style rules

- Ruff owns formatting, linting, and import sorting.
- Do not introduce Black, isort, Flake8, or Pylint unless instructed.
- Do not fight formatter output.

## VS Code rules

This repo may include VS Code settings and tasks.

Use these tasks when working in VS Code:

- `check`
- `fix`
- `test`
- `typecheck`
- `audit`

Do not change `.vscode/settings.json` to bypass project checks. Do not add personal editor preferences to workspace settings.
````

### 16.2 Thin `AGENTS.md` pointer template

Use this pattern when the repository intentionally keeps `AGENTS.md` small and stores the full working contract elsewhere.

```markdown
# Agent Instructions

This repository uses a custom session memory/handoff system as the canonical instruction source.

Before editing code:

1. Load the canonical instruction source: `<path-or-command>`.
2. Follow the resolved instructions as the active implementation contract.
3. If the canonical source is unavailable, stop and report that the instruction source cannot be resolved.

The resolved instructions must preserve the Python Tooling SSOT Standard, including the verification gate, fix pass, dependency rules, typing rules, testing rules, security rules, and VS Code rules.
```

Source basis: this block operationalizes the source-backed tool behavior documented in sections 2 through 15, and the agent-instruction discovery behavior documented for Codex, Claude Code, and AGENTS.md conventions. [S30], [S31], [S32]

---

## 17. Claude Code instruction block

Copy this into `CLAUDE.md` when the repository uses Claude Code, unless `CLAUDE.md` intentionally remains a thin pointer to `AGENTS.md` or another approved session memory/handoff source.

```markdown
# Claude Code Instructions

Follow `AGENTS.md` or the resolved canonical instruction source as the primary implementation contract.

## Claude-specific behavior

- If `CLAUDE.md` or `AGENTS.md` is a pointer, resolve the referenced session memory or handoff source before editing.
- Read `pyproject.toml`, the resolved agent instructions, and the relevant tests before editing.
- Prefer small, reviewable changes.
- Preserve the existing architecture unless asked to refactor.
- Use types to clarify intent before adding comments.
- Add or update tests with every behavior change.
- Run the verification gate before reporting completion.
- Report any command failures honestly with the relevant error summary.

## Do not

- Do not add dependencies without a clear reason.
- Do not weaken type checking to make errors disappear.
- Do not remove tests because they fail.
- Do not create parallel tooling systems.
- Do not add personal VS Code preferences.
```

Policy decision: `AGENTS.md` is the default cross-agent entry point; `CLAUDE.md` should only add Claude-specific behavior or point to the canonical session memory/handoff source. Thin pointer files are valid when the resolved instructions meet the same contract.

---

## 18. Optional local check script

A Python wrapper can make the quality gate easier for agents and humans to run.

`scripts/check.py`:

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

Run:

```bash
uv run python -m scripts.check
```

Policy decision: if this script is used, VS Code and CI may call it, but CI should remain explicit unless the team intentionally prefers a single script-based gate.

---

## 19. Project profiles

### 19.1 Library package

Use the baseline plus:

- `py.typed`
- careful public API typing
- changelog if externally consumed
- CI matrix if supporting multiple Python versions
- stricter backwards compatibility discipline

Recommended addition only when consumers need optional extras:

```toml
[project.optional-dependencies]
test = []
```

Source basis: PyPA documents `[project]` metadata and dependency fields in `pyproject.toml`. [S01], [S02]

### 19.2 CLI application

Add:

```toml
[project.scripts]
example = "package_name.cli:main"
```

Source basis: PyPA documents project metadata in `pyproject.toml`; uv project creation docs include command definitions with `[project.scripts]`. [S01], [S29]

CLI rules:

- `main()` returns an exit code.
- CLI parsing is separate from business logic.
- Business logic is testable without invoking subprocesses.
- Use `argparse` by default unless the CLI is complex enough to justify Typer or Click.
- Error messages should be useful and non-stack-trace by default.

### 19.3 FastAPI application

Recommended runtime dependencies:

```bash
uv add fastapi pydantic pydantic-settings uvicorn
```

Source basis: Pydantic models are appropriate for data validation/model creation at typed boundaries. [S23]

Additional rules:

- Use Pydantic v2 models at API boundaries.
- Keep route handlers thin.
- Put business logic outside route functions.
- Use dependency injection intentionally, not as hidden global state.
- Validate settings with `pydantic-settings`.
- Add tests for status codes, response models, validation failures, and error paths.

### 19.4 Automation/script project

Even for small automation projects:

- Use `uv`.
- Use `pyproject.toml`.
- Use `ruff`.
- Use at least basic typing.
- Include tests for non-trivial logic.

Source basis: uv supports project management with `pyproject.toml`; Ruff supports linting/formatting; Python typing is available to tools; pytest supports small readable tests. [S04], [S08], [S21], [S13]

Policy decision: a script project may omit packaging metadata only if it is truly throwaway. If it lives in Git, it should follow the standard.

---

## 20. Exceptions process

A project may deviate from this standard only when the exception is documented.

To adopt this standard, see [`adopt.md`](adopt.md).

Record the exception as a conformant ADR. Create or update a file under `docs/decisions/`, using a zero-padded numeric sequence number for `NNNN`:

```text
docs/decisions/adr-NNNN-python-tooling-exception.md
```

The ADR Standard ([`standards/adr/README.md`](../adr/README.md)) is the authority for the exact ADR shape — `id`, filename, frontmatter, and MADR section structure. Map the exception into MADR's required level-2 sections as follows:

```markdown
# ADR NNNN: Python tooling exception

## Context and Problem Statement

What project constraint requires deviating from the standard? (Accepted/in-force status lives in the ADR frontmatter `status` field, per the ADR Standard.)

## Considered Options

What alternatives were weighed — including conforming to the standard unchanged?

## Decision Outcome

What exception is allowed, and why this option over the others?

### Consequences

What does this cost in maintainability, agent reliability, CI complexity, or onboarding? Note when this exception should be revisited.
```

Examples of valid exceptions:

- Existing mature project already standardized on mypy.
- Library must support older Python versions.
- Security-sensitive service needs additional scanners.
- Project requires a build backend feature not available in `uv_build`.

Examples of invalid exceptions:

- Agent added a tool because it was familiar.
- Type checker was disabled to avoid fixing errors.
- Tests were removed because they failed.
- Formatter was changed because of style preference.

Policy decision: exceptions are allowed, but they must be explicit enough for future agents to preserve the reason.

---

## 21. Migration guide for existing projects

Use this sequence for existing repositories.

### Step 1: Inventory

Identify:

- Python versions currently used
- package manager
- lockfiles
- formatter
- linter
- type checker
- test framework
- CI checks
- VS Code settings
- existing agent instructions

### Step 2: Add uv without changing behavior

```bash
uv init --bare
uv sync
```

Source basis: uv supports project initialization and project dependency/environment management. [S04]

### Step 3: Add Ruff

```bash
uv add --dev ruff
uv run ruff format .
uv run ruff check . --fix
```

Source basis: Ruff supports linting, formatting, and `pyproject.toml` configuration. [S08], [S09], [S10]

### Step 4: Add pytest and coverage

```bash
uv add --dev pytest coverage[toml] pytest-cov
uv run coverage run -m pytest
uv run coverage report
```

Source basis: pytest supports Python tests and `pyproject.toml` config; coverage.py measures test execution coverage and reads `pyproject.toml` with TOML support. [S13], [S15]

### Step 5: Add BasedPyright

```bash
uv add --dev basedpyright
uv run basedpyright
```

Source basis: BasedPyright supports project configuration and baselines for staged adoption. [S11], [S12]

For messy existing projects, use a staged adoption plan rather than weakening the final standard.

### Step 6: Add VS Code config

Add:

```text
.vscode/extensions.json
.vscode/settings.json
.vscode/tasks.json
```

Source basis: VS Code workspace settings and tasks are stored in `.vscode`; BasedPyright documents its VS Code language-server setup and Pylance coexistence guidance. [S17], [S18], [S28]

### Step 7: Add CI

Add `.github/workflows/check.yml`.

CI must use `uv sync --locked --all-groups`.

Source basis: uv documents use in GitHub Actions with `setup-uv`, setup-python, `uv sync`, and `uv run`. [S20]

### Step 8: Add agent instruction entry points

Add or update:

```text
AGENTS.md
CLAUDE.md
```

These files may contain the full instructions or compact pointers to an approved session memory/handoff system.

Policy decision: agent instruction entry points are part of the repo contract, not optional documentation. The full instruction body may live elsewhere when the pointer system is reliable and preserves this standard's intent.

### Step 9: Ratchet strictness

Once the project is stable:

- reduce ignores
- increase coverage quality
- improve type specificity
- remove legacy tooling
- document remaining exceptions

Policy decision: staged adoption is allowed for existing code; new code should meet the standard.

---

## 22. Update process for this standard

This document should be reviewed when:

- Python releases a new stable version suitable as baseline.
- uv changes project or build backend behavior materially.
- Ruff changes recommended VS Code or config behavior materially.
- BasedPyright/Pyright changes strict mode behavior materially.
- pytest changes config conventions.
- VS Code Python tooling changes extension recommendations.
- CI action versions need updating.

Review cadence:

- Light review: quarterly
- Full review: annually
- Immediate review: after a toolchain-breaking change

Source basis: these tools are active projects whose documented behavior can change. The source register below records the exact sources checked for this version.

---

## 23. Source coverage map

| Section | Source IDs used |
| --- | --- |
| Purpose/core contract | [S04], [S08], [S11], [S13], [S15], [S16] |
| Standard stack | [S01], [S03], [S04], [S05], [S07], [S08], [S09], [S10], [S11], [S13], [S14], [S15], [S16], [S17], [S20], [S34], [S35], [N01] |
| Repository layout | [S04], [S14], [S17], [S18], [S19] |
| Python version policy | [S01], [S03], [S04], [S20] |
| `pyproject.toml` | [S01], [S02], [S06], [S07], [S09], [S11], [S13], [S15] |
| Dependency policy | [S04], [S05], [S06] |
| Type policy | [S11], [S12], [S21], [S22], [S23], [S24] |
| Testing policy | [S13], [S14] |
| Coverage policy | [S15], [S25] |
| Ruff policy | [S08], [S09], [S10], [S26] |
| Security policy | [S16] |
| Editor and agent integrations | [S17], [S18], [S26], [S27], [S28], [S33], [S35], [S36], [N01] |
| EditorConfig | [S19] |
| GitHub Actions | [S20] |
| Agent instruction interface | [S30], [S31], [S32], [S36] |
| Project profiles | [S01], [S02], [S04], [S08], [S13], [S21], [S23], [S29] |

---

## 24. Source register

| ID | Source | URL | What it supports | Last checked |
| --- | --- | --- | --- | --- |
| S01 | PyPA: Writing your `pyproject.toml` | [https://packaging.python.org/en/latest/guides/writing-pyproject-toml/](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) | `pyproject.toml`, `[build-system]`, `[project]`, `[tool]`, build backend metadata | 2026-06-06 |
| S02 | PyPA: `pyproject.toml` specification | [https://packaging.python.org/en/latest/specifications/pyproject-toml/](https://packaging.python.org/en/latest/specifications/pyproject-toml/) | Formal `pyproject.toml` table roles and build-system behavior | 2026-06-06 |
| S03 | Python Developer Guide: Status of Python versions | [https://devguide.python.org/versions/](https://devguide.python.org/versions/) | Python version lifecycle phases | 2026-06-06 |
| S04 | uv: Working on projects | [https://docs.astral.sh/uv/guides/projects/](https://docs.astral.sh/uv/guides/projects/) | uv project structure, `.python-version`, `.venv`, `uv.lock`, `uv run` | 2026-06-06 |
| S05 | uv: Locking and syncing | [https://docs.astral.sh/uv/concepts/projects/sync/](https://docs.astral.sh/uv/concepts/projects/sync/) | Automatic lock/sync behavior for `uv run`; `--locked` | 2026-06-06 |
| S06 | PyPA: Dependency Groups | [https://packaging.python.org/en/latest/specifications/dependency-groups/](https://packaging.python.org/en/latest/specifications/dependency-groups/) | `[dependency-groups]` for development dependencies | 2026-06-06 |
| S07 | uv: Build backend | [https://docs.astral.sh/uv/concepts/build-backend/](https://docs.astral.sh/uv/concepts/build-backend/) | `uv_build`, build backend snippet, limitations for pure-Python code | 2026-06-06 |
| S08 | Ruff documentation | [https://docs.astral.sh/ruff/](https://docs.astral.sh/ruff/) | Ruff as Python linter and formatter | 2026-06-06 |
| S09 | Ruff configuration | [https://docs.astral.sh/ruff/configuration/](https://docs.astral.sh/ruff/configuration/) | Ruff config file support and `pyproject.toml` behavior | 2026-06-06 |
| S10 | Ruff formatter | [https://docs.astral.sh/ruff/formatter/](https://docs.astral.sh/ruff/formatter/) | Ruff formatter, Black compatibility goal, formatter configuration | 2026-06-06 |
| S11 | BasedPyright config files | [https://docs.basedpyright.com/dev/configuration/config-files/](https://docs.basedpyright.com/dev/configuration/config-files/) | `[tool.basedpyright]` support and config behavior | 2026-06-06 |
| S12 | BasedPyright baseline | [https://docs.basedpyright.com/v1.36.1/benefits-over-pyright/baseline/](https://docs.basedpyright.com/v1.36.1/benefits-over-pyright/baseline/) | Baseline support for adopting stricter checks in existing projects | 2026-06-06 |
| S13 | pytest documentation / configuration | [https://docs.pytest.org/en/stable/](https://docs.pytest.org/en/stable/) and [https://docs.pytest.org/en/stable/reference/customize.html](https://docs.pytest.org/en/stable/reference/customize.html) | pytest purpose, `pyproject.toml` config, `[tool.pytest.ini_options]` support since pytest 6.0, and `[tool.pytest]` support since pytest 9.0 | 2026-06-06 |
| S14 | pytest good integration practices | [https://docs.pytest.org/en/stable/explanation/goodpractices.html](https://docs.pytest.org/en/stable/explanation/goodpractices.html) | `src` layout recommendation | 2026-06-06 |
| S15 | coverage.py configuration / PyPI docs | [https://coverage.readthedocs.io/en/latest/config.html](https://coverage.readthedocs.io/en/latest/config.html) and [https://pypi.org/project/coverage/](https://pypi.org/project/coverage/) | coverage.py measures coverage; `pyproject.toml` config support | 2026-06-06 |
| S16 | pip-audit PyPI documentation | [https://pypi.org/project/pip-audit/](https://pypi.org/project/pip-audit/) | Known-vulnerability scanning and Python Packaging Advisory Database source | 2026-06-06 |
| S17 | VS Code user/workspace settings | [https://code.visualstudio.com/docs/configure/settings](https://code.visualstudio.com/docs/configure/settings) | Workspace settings in `.vscode/settings.json` and project-specific behavior | 2026-06-06 |
| S18 | VS Code tasks | [https://code.visualstudio.com/docs/debugtest/tasks](https://code.visualstudio.com/docs/debugtest/tasks) | `.vscode/tasks.json` and running external tools from VS Code | 2026-06-06 |
| S19 | EditorConfig | [https://editorconfig.org/](https://editorconfig.org/) | Cross-editor coding style file and supported properties | 2026-06-06 |
| S20 | uv: GitHub Actions integration | [https://docs.astral.sh/uv/guides/integration/github/](https://docs.astral.sh/uv/guides/integration/github/) | `astral-sh/setup-uv` (SHA-pinned; no moving major/minor tag since v8.0.0), `actions/setup-python`, `python-version-file`, `uv sync`, `uv run`, cache support | 2026-06-07 |
| S21 | Python docs: `typing` | [https://docs.python.org/3/library/typing.html](https://docs.python.org/3/library/typing.html) | Type annotations, advanced type-hinting vocabulary, type checkers/IDEs/linters | 2026-06-06 |
| S22 | Python docs: `dataclasses` | [https://docs.python.org/3/library/dataclasses.html](https://docs.python.org/3/library/dataclasses.html) | `@dataclass`, `frozen=True`, frozen instance behavior | 2026-06-06 |
| S23 | Pydantic docs: models | [https://pydantic.dev/docs/validation/latest/concepts/models/](https://pydantic.dev/docs/validation/latest/concepts/models/) | Pydantic model validation and output type/constraint guarantee | 2026-06-06 |
| S24 | Python docs: `pathlib` | [https://docs.python.org/3/library/pathlib.html](https://docs.python.org/3/library/pathlib.html) | `Path` and object-oriented filesystem path handling | 2026-06-06 |
| S25 | coverage.py report command | [https://coverage.readthedocs.io/en/latest/commands/cmd_report.html](https://coverage.readthedocs.io/en/latest/commands/cmd_report.html) | Coverage report and missed branch reporting | 2026-06-06 |
| S26 | Ruff editor features | [https://docs.astral.sh/ruff/editors/features/](https://docs.astral.sh/ruff/editors/features/) | Ruff VS Code/editor formatting and code-action features | 2026-06-06 |
| S27 | VS Code Python testing | [https://code.visualstudio.com/docs/python/testing](https://code.visualstudio.com/docs/python/testing) | `python.testing.pytestEnabled`, pytest settings, VS Code Python test discovery | 2026-06-06 |
| S28 | BasedPyright IDE setup | [https://docs.basedpyright.com/latest/installation/ides/](https://docs.basedpyright.com/latest/installation/ides/) | BasedPyright VS Code extension, language-server setup, `ms-python` interpreter-detection dependency note, and Pylance disable/uninstall guidance | 2026-06-06 |
| S29 | uv: Creating projects | [https://docs.astral.sh/uv/concepts/projects/init/](https://docs.astral.sh/uv/concepts/projects/init/) | `uv init`, packaged project metadata, `[project.scripts]` example | 2026-06-06 |
| S30 | Claude Code Docs: How Claude remembers your project | [https://code.claude.com/docs/en/memory](https://code.claude.com/docs/en/memory) | `CLAUDE.md`, auto memory, startup loading, context-not-enforced behavior, concise instruction guidance | 2026-06-06 |
| S31 | OpenAI Codex: Custom instructions with `AGENTS.md` | [https://developers.openai.com/codex/guides/agents-md](https://developers.openai.com/codex/guides/agents-md) | Codex `AGENTS.md` discovery, layering, overrides, fallback filenames, project-doc size behavior | 2026-06-06 |
| S32 | AGENTS.md open format | [https://agents.md/](https://agents.md/) | AGENTS.md as a predictable agent instruction file for setup, tests, conventions, and project context | 2026-06-06 |
| S33 | VS Code Python Environments | [https://code.visualstudio.com/docs/python/environments](https://code.visualstudio.com/docs/python/environments) | Python Environments extension, environment/package UI, and support for managers including `uv` | 2026-06-06 |
| S34 | uv: Tools interface and using tools | [https://docs.astral.sh/uv/concepts/tools/](https://docs.astral.sh/uv/concepts/tools/) and [https://docs.astral.sh/uv/guides/tools/](https://docs.astral.sh/uv/guides/tools/) | `uv tool install`, isolated/persistent tool environments, executables on `PATH`, and `uv run` preference for project-aware tools such as pytest | 2026-06-06 |
| S35 | BasedPyright command-line and language server | [https://docs.basedpyright.com/latest/installation/command-line-and-language-server/](https://docs.basedpyright.com/latest/installation/command-line-and-language-server/) | `basedpyright` CLI and `basedpyright-langserver` availability from the Python package | 2026-06-06 |
| S36 | Claude Code plugins reference | [https://code.claude.com/docs/en/plugins-reference](https://code.claude.com/docs/en/plugins-reference) | Plugin manifest, `lspServers`, separate `.lsp.json`, skills-directory plugin behavior, reload and disable commands | 2026-06-06 |
| N01 | Workstation application notes | (internal session notes — not committed to this repo) | Applied sys76 workstation reconciliation findings: project-vs-workstation scope, global/per-project split, install-layer removal risk, global pytest exception, user-site scope boundary, and CLI-agent LSP gap | 2026-06-06 |

---

## 25. Audit notes for versions 1.2 through 1.6

Updated on 2026-06-06:

- Added explicit evidence convention.
- Added source IDs throughout the document.
- Added a source coverage map.
- Added a dated source register.
- Marked recommendations that are local policy decisions rather than externally mandated facts.
- Rechecked the main external references against current official documentation.
- Kept Python 3.13 as the standard baseline but explicitly labeled it as policy, not an upstream mandate.
- Kept uv/Ruff/BasedPyright/pytest/coverage/pip-audit as the standard stack and tied each external tool behavior to a current source.

Additional consistency polish for version 1.2 on 2026-06-06:

- Standardized terminology around the non-mutating `verification gate` and mutating `fix pass`.
- Aligned `AGENTS.md`, VS Code tasks, CI, and `scripts/check.py` around the same verification gate.
- Clarified that example GitHub Actions templates should pin the reviewed uv version when applied.
- Kept the source register and source coverage map unchanged because the polish pass did not introduce new factual claims.

Additional update for version 1.3 on 2026-06-06:

- Added explicit permission for alternate session memory and handoff systems.
- Clarified that `AGENTS.md` and `CLAUDE.md` are required discoverability entry points, not mandatory full-content storage locations.
- Added full and thin-pointer `AGENTS.md` patterns.
- Updated the Claude Code instruction section to support pointer-based instruction resolution.
- Added source references for Claude Code memory behavior, Codex `AGENTS.md` discovery/fallback behavior, and the AGENTS.md open format.

Additional update for version 1.4 on 2026-06-06:

- Updated the VS Code standard to match the active workstation decision: Pylance is not part of the standard stack.
- Added an explicit Python language-server policy: BasedPyright is the semantic/type authority; Ruff is the format/lint/import authority.
- Marked `ms-python.vscode-python-envs` as optional UI only, not a required extension or source of project authority.
- Added a source-register entry for VS Code Python Environments.

Additional update for version 1.5 on 2026-06-06:

- Corrected the template pytest configuration table to `[tool.pytest.ini_options]`.
- Added a testing policy note that `[tool.pytest]` is valid only for pytest 9.0+ native TOML configuration, while `[tool.pytest.ini_options]` is the standard table for this template because it remains supported and avoids silent inert configuration on older pytest versions.
- Updated the source register description for S13 to cover both pytest configuration tables and their version support.

Additional update for version 1.6 on 2026-06-06:

- Added a workstation provisioning boundary: the standard is repo-scoped first, and global CLI provisioning is a separate layer.
- Added `uv tool` as the preferred mechanism for global ad-hoc dev CLIs, while keeping pytest and coverage project-local for new repositories.
- Clarified that the non-default tool list prohibits adding tools to projects; it is not an automatic uninstall order for every workstation layer.
- Added guidance for layered removal review across `uv tool`, `pip --user`, OS packages, npm, editor extensions, and project virtual environments.
- Added an exception that a pre-existing global pytest may remain when it is load-bearing for existing non-uv workflows.
- Added a scope boundary that the standard governs the dev-tooling stack, not unrelated Python application/runtime libraries installed on a workstation.
- Generalized the VS Code language-server rule to editor and CLI-agent integrations, including a Claude Code LSP-only BasedPyright plugin pattern.

Baseline update on 2026-06-07:

- Raised the default Python baseline from 3.13 to 3.14 across the scaffolds: `requires-python = ">=3.14"`, `.python-version` `3.14`, Ruff `target-version = "py314"`, and BasedPyright `pythonVersion = "3.14"`. 3.14 is the current stable CPython release.
- Per [`meta/versioning.md`](../../meta/versioning.md), raising the required Python is a MAJOR-level change for a copy-adopting consumer that re-syncs; it rides the already-locked `2.0.0` release. The `python_tooling` contract-version label stays `1.0` — it is metadata-only and unenforced, so the validator behaves identically.

Action-pin fix on 2026-06-07:

- §15 `check.yml` template: replaced the unresolvable `astral-sh/setup-uv@v8` with a full-version commit SHA + trailing version comment (`@fac544c…39 # v8.2.0`). As of setup-uv v8.0.0 (March 2026) Astral publishes **no** moving major/minor tag, so `@v8`/`@v8.0` 404 — confirmed against the GitHub refs API on 2026-06-07. A copied template previously red-failed at the install step before any gate ran.
- Review reminder: when this standard is re-checked, verify every embedded action ref still resolves (a moving tag can be withdrawn, as setup-uv's was). The [S20] uv GitHub Actions guide already shows the SHA-pinned form, so re-reading the cited source catches this class of drift.

<!-- Citation reference-link definitions: every [Sxx]/[N01] marker in the body and in the source coverage map resolves to the Source register (section 24). GFM cannot anchor individual table rows, so all citations jump to the section. -->

[S01]: #24-source-register
[S02]: #24-source-register
[S03]: #24-source-register
[S04]: #24-source-register
[S05]: #24-source-register
[S06]: #24-source-register
[S07]: #24-source-register
[S08]: #24-source-register
[S09]: #24-source-register
[S10]: #24-source-register
[S11]: #24-source-register
[S12]: #24-source-register
[S13]: #24-source-register
[S14]: #24-source-register
[S15]: #24-source-register
[S16]: #24-source-register
[S17]: #24-source-register
[S18]: #24-source-register
[S19]: #24-source-register
[S20]: #24-source-register
[S21]: #24-source-register
[S22]: #24-source-register
[S23]: #24-source-register
[S24]: #24-source-register
[S25]: #24-source-register
[S26]: #24-source-register
[S27]: #24-source-register
[S28]: #24-source-register
[S29]: #24-source-register
[S30]: #24-source-register
[S31]: #24-source-register
[S32]: #24-source-register
[S33]: #24-source-register
[S34]: #24-source-register
[S35]: #24-source-register
[S36]: #24-source-register
[N01]: #24-source-register
