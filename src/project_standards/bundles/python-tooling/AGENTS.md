# Python Project Agent Instructions

## Operating model

This repository follows the Python Tooling SSOT Standard. Use the existing project structure and tools. Do not replace the tooling stack unless explicitly instructed.

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

- Use `uv add <package>` for runtime deps, `uv add --dev <package>` for dev deps.
- Do not manually edit `uv.lock`. Explain any new dependency.

## Typing rules

- All new `src/` code must pass strict BasedPyright. No untyped public functions, no implicit `Any`.
- Avoid `# type: ignore`; if unavoidable, include the exact rule and reason.

## Testing rules

- New behavior requires tests; bug fixes require regression tests. Assert behavior, not implementation.

## Style rules

- Ruff owns formatting, linting, and import sorting. Do not introduce Black, isort, Flake8, or Pylint.
