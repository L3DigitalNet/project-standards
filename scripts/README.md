# scripts/

Developer helpers for `project-standards`.

## `check.py` — Python Tooling dogfood gate

Runs the portable Python Tooling verification sequence, stopping at the first failure and propagating its exit code:

```text
ruff format --check  →  ruff check  →  basedpyright  →  coverage run -m pytest  →  coverage report  →  pip-audit
```

Usage:

```bash
uv run python scripts/check.py
```

This byte-locked dogfood artifact remains the generic consumer gate. Repository CI spells out its additional compatibility and performance phases directly in `.github/workflows/check.yml`.

### Dogfood relationship

`scripts/check.py` is the **dogfooded copy** of the Python Tooling bundle artifact:

```text
standards/python-tooling/versions/1.2/resources/check.py  ←→  scripts/check.py
```

`test_adopt_dogfood.py` asserts that the root artifact matches the current V2 reconciliation output. If you edit either file, update the package manifest and generated integrity metadata together — the test will catch any divergence in CI.

## `build-validate-id-pyz.sh` — standalone validator bundle

Builds `dist/validate-id.pyz`, a self-contained zipapp of `validate-id` for repos that cannot `uv tool install` the package. It bundles the package source from `src/project_standards/` directly; see the script header for the PyYAML/jsonschema bundling details.
