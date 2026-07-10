# Python Tooling SSOT Standard: Agent Summary

The canonical [README](README.md) is authoritative and wins if this summary conflicts with it.

Lifecycle: active. Adoption: `copy-adopt`.

## Use this summary when

Create, adopt, migrate, or verify a Python repository toolchain and its agent-facing gate.

## Core rules

- One tool owns each concern: uv manages environments, dependencies, and lockfiles; Ruff formats, lints, and sorts imports; BasedPyright checks types in strict mode; pytest plus coverage verifies behavior and branches; pip-audit checks dependencies.
- Use a `src/` layout for importable projects, a committed `uv.lock` for applications and internal projects, a project `.venv/`, and centralized `pyproject.toml` configuration.
- Use `uv_build` by default for pure-Python packages. Keep packages and runtime data beneath `src/<normalized_name>/`, declare commands in `[project.scripts]`, and use another backend only when project constraints require it.
- Put the gate's tools in the `dev` dependency group. Change dependencies with `uv add`, `uv add --dev`, or `uv remove`; never edit the lockfile manually.
- Strict typing applies to new `src/` product code and tests. Ruff covers all first-party Python while excluding external-program, vendored, generated, or archived paths explicitly.
- Do not add competing baseline tools such as Poetry, Black, isort, Flake8, Pylint, mypy, tox, nox, or pre-commit as a duplicate Python gate without a documented exception.

## Verification gate

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run coverage run -m pytest
uv run coverage report
uv run pip-audit
```

Run `uv run ruff format .` and `uv run ruff check . --fix` as the mutating fix pass. Work is not complete until the non-mutating gate passes or the failure is explicitly reported.

## Adoption and boundaries

`project-standards adopt python-tooling` copy-adopts `.python-version`, CI, editor configuration, agent entry points, and a check script while reporting `pyproject.toml` sections for manual merge. [Python Coding](../python-coding/README.md) is a reference-only companion for code shape; it is not a hidden dependency or second toolchain.

## Canonical resources

Use the [standard](README.md), [adoption guide](adopt.md), and [build-backend mechanics](build-backend.md).
