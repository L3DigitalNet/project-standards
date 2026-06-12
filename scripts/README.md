# scripts/

Developer helpers for `project-standards`.

## `check.py` — local CI gate

Runs the full verification suite in the same order CI does, stopping at the first failure and propagating its exit code:

```text
ruff format --check  →  ruff check  →  basedpyright  →  coverage run -m pytest  →  coverage report  →  pip-audit
```

Usage:

```bash
uv run python scripts/check.py
```

Pass/fail behaviour mirrors `.github/workflows/check.yml` exactly — if this script goes green locally, CI should go green. Run it before every commit that touches `src/project_standards/` or `tests/`.

### Dogfood relationship

`scripts/check.py` is the **dogfooded copy** of the Python Tooling bundle artifact:

```text
src/project_standards/bundles/python-tooling/check.py  ←→  scripts/check.py
```

`test_adopt_dogfood.py` asserts byte-identity between the two. If you edit either file, update the other to match — the test will catch any divergence in CI.

## `build-validate-id-pyz.sh` — standalone validator bundle

Builds `dist/validate-id.pyz`, a self-contained zipapp of `validate-id` for repos that cannot `uv tool install` the package. It bundles the package source from `src/project_standards/` directly (no copy in this directory is involved); see the script header for the PyYAML/jsonschema bundling details.

## `validate_id.py` — stale snapshot (do not use)

A superseded copy of the validator from before the `id_format` extraction. Nothing consumes it; it is kept only as history and is marked as stale in its header. Prefer deleting it.
