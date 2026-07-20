# Python Tooling SSOT Standard

This is the Catalog 5 family landing page for the active consumer package `python-tooling@1.4`. The immutable versioned payload, not this mutable landing page, defines the selected standard.

## Current authority

- [Python Tooling 1.4 standard](versions/1.4/README.md) — normative toolchain, configuration, ownership, and verification contract
- [Python Tooling 1.4 adoption guide](versions/1.4/adopt.md) — complete options, outputs, migration, and recovery
- [Current family adoption guide](adopt.md) — concise enable/reconcile workflow
- [Python Tooling 1.4 agent summary](versions/1.4/agent-summary.md) — compact authority rules
- [Family index](standard.toml) — indexed payload and digest

## Use this standard when

Use Python Tooling for the uv/uv_build `src/` baseline, Ruff formatting and linting, BasedPyright strict checking, pytest with coverage.py, pip-audit, CI, VS Code, and bounded agent instructions. The control plane composes only declared package-owned tables, properties, and blocks and preserves unrelated consumer configuration.

## Adopt

```bash
project-standards standards enable python-tooling --version 1.4
project-standards reconcile
project-standards reconcile --apply
uv lock
python scripts/check.py
```

Review [adopt.md](adopt.md) before applying. Commit unified config, catalog, lock, dependency lock, and reconciled outputs together.

## Release-status correction

The immutable 1.1 README contains wording written before the atomic Catalog 5 and Project Standards v5.0.0 release. Treat its statement that the V1 root remains authoritative until that release as release-time history. Catalog 5 now selects `python-tooling@1.4`; the immutable 1.1 payload bytes remain unchanged.

## Legacy boundary

The unversioned copy-adopt toolchain, `project-standards adopt python-tooling`, and `.project-standards.yml` fragments are migration evidence only. They do not define current Catalog 5 composition or ownership.
