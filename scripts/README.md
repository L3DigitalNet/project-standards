# scripts/

Developer helpers for `project-standards`. Currently one script.

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
