# scripts/

Developer helpers for `project-standards`.

## `verify.sh` — the repository release gate

Runs the repository's own verification as three concurrent lanes (statics through the non-uv path, the ordinary suite under coverage with pytest-xdist, and the compatibility matrix), then the timing-sensitive performance lane alone, then `coverage combine` and the report. `--full` reproduces the legacy serial battery for release-prep cross-checks. Expects the candidate wheel runtime on `PYTHONPATH` prerequisites and refuses to start without them; see the script header for the environment it establishes.

```bash
scripts/verify.sh            # fast gate (default)
scripts/verify.sh --full     # legacy serial battery
```

## `release_prep.py` — mechanical release preparation

Performs the judgment-free subset of `meta/versioning.md` behind one command: the scoped `pyproject.toml` version bump with `uv lock`, the `CHANGELOG.md` `[Unreleased]` conversion, a reviewed-never-rewritten report of outgoing-version references, and the wiring verification chain ending in `packages check-release`. It refuses a dirty or non-`main` worktree so the mutations belong to the release commit. It prints, but does not execute, the mandatory pre-tag locked `uv sync`, `npm ci`, read-only projection proof, isolated candidate-wheel, full-gate, dogfood, package-contract, and release-classification sequence. Tags, publication, and MAJOR-only prose stay manual.

```bash
uv run python scripts/release_prep.py X.Y.Z [--dry-run]
```

## `check.py` — Python Tooling dogfood gate

Runs the portable Python Tooling verification sequence, stopping at the first failure and propagating its exit code:

```text
ruff format --check  →  ruff check  →  basedpyright  →  coverage run -m pytest  →  coverage report  →  pip-audit
```

Usage:

```bash
uv run python scripts/check.py
```

This byte-locked dogfood artifact remains the generic consumer gate. The repository's own gate is `verify.sh` above; CI spells out its compatibility and performance phases directly in `.github/workflows/check.yml`.

### Dogfood relationship

`scripts/check.py` is the **dogfooded copy** of the Python Tooling bundle artifact:

```text
standards/python-tooling/versions/1.10/resources/check.py  ←→  scripts/check.py
```

`test_adopt_dogfood.py` asserts that the root artifact matches the current V2 reconciliation output. If you edit either file, update the package manifest and generated integrity metadata together — the test will catch any divergence in CI.

## `build-validate-id-pyz.sh` — standalone validator bundle

Builds `dist/validate-id.pyz`, a self-contained zipapp of `validate-id` for repos that cannot `uv tool install` the package. It bundles the package source from `src/project_standards/` directly; see the script header for the PyYAML/jsonschema bundling details.
