# scripts/

Developer helpers for `project-standards`.

## `run_repository_tests.py` — optimized repository test gate

Runs the repository-specific test phases with one prebuilt compatibility wheel:

1. ordinary tests run serially under coverage;
2. the 56 catalog-derived source/wheel rows run across four local workers by default;
3. disposable release replay runs serially under coverage;
4. coverage data is combined and the configured threshold is enforced;
5. deterministic performance tests run serially without coverage or worker contention.

Usage:

```bash
uv run python scripts/run_repository_tests.py
```

Set `PROJECT_STANDARDS_TEST_WORKERS` to a positive integer to benchmark a different explicit matrix-worker count. CI pins four workers; the final July 2026 workstation baseline improved from 711.78 seconds serially to 177.10 seconds with four workers while retaining all 56 rows.

## `check.py` — Python Tooling dogfood gate

Runs the portable Python Tooling verification sequence, stopping at the first failure and propagating its exit code:

```text
ruff format --check  →  ruff check  →  basedpyright  →  coverage run -m pytest  →  coverage report  →  pip-audit
```

Usage:

```bash
uv run python scripts/check.py
```

This byte-locked dogfood artifact remains the generic consumer gate. This repository's CI uses `run_repository_tests.py` for its additional catalog compatibility and release-replay phases.

### Dogfood relationship

`scripts/check.py` is the **dogfooded copy** of the Python Tooling bundle artifact:

```text
src/project_standards/bundles/python-tooling/check.py  ←→  scripts/check.py
```

`test_adopt_dogfood.py` asserts byte-identity between the two. If you edit either file, update the other to match — the test will catch any divergence in CI.

## `build-validate-id-pyz.sh` — standalone validator bundle

Builds `dist/validate-id.pyz`, a self-contained zipapp of `validate-id` for repos that cannot `uv tool install` the package. It bundles the package source from `src/project_standards/` directly; see the script header for the PyYAML/jsonschema bundling details.
