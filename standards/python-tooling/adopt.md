# Adopt the Python Tooling Standard

The current consumer package is [`python-tooling@1.8`](versions/1.8/adopt.md). Use it for the uv/uv_build `src/` baseline, Ruff, BasedPyright strict mode, pytest/coverage, pip-audit, CI, VS Code, and bounded agent instructions.

## Configure and reconcile

```bash
project-standards standards enable python-tooling --version 1.8
project-standards reconcile
project-standards reconcile --apply
uv lock
python scripts/check.py
```

Options under `[standards.python-tooling.config]` select the independent contract, Python/build/layout choices, additional development dependencies, Ruff exclusions, type checker, pytest markers, coverage exclusions, `coverage.parallel`, `coverage.patch`, `workflow_ownership`, `script_ownership`, audit exceptions, CI, VS Code, and instruction behavior. Setting `script_ownership = "consumer-owned"` leaves `scripts/check.py` outside reconciliation, verification, and lock state. Reconciliation composes only declared package-owned tables/properties/blocks and preserves unrelated project configuration.

Commit `.standards/config.toml`, `.standards/lock.toml`, `uv.lock`, and reconciled outputs together. The package owns the development dependency group, so `uv lock` is an explicit post-apply step.

## Migrate a V4 repository

```bash
project-standards init --catalog 5 --migrate
project-standards init --catalog 5 --migrate --apply
```

Migration maps `python_tooling.version`, preserves explicit repository toolchain intent, and recognizes only exact released whole/shared artifacts. A modified workflow requires the matching `workflow_ownership = "consumer-owned"` decision in the legacy configuration; a modified `scripts/check.py` requires `script_ownership = "consumer-owned"`. Other conflicting or modified values block before writes; resolve the intended option rather than forcing replacement.

## Verify and troubleshoot

```bash
project-standards reconcile --check
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run coverage run -m pytest
uv run coverage report
uv run pip-audit
```

Unsupported option combinations, conflicting TOML ownership, unsafe paths, or managed-unit drift fail closed. See the [version-specific guide](versions/1.8/adopt.md) for the complete option example, outputs, migration, disable semantics, and recovery guidance.
