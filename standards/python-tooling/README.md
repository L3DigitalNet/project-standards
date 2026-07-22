# Python Tooling SSOT Standard

This is the Catalog 5 family landing page for the active consumer package `python-tooling@1.5`. The immutable versioned payload, not this mutable landing page, defines the selected standard.

## Current authority

- [Python Tooling 1.5 standard](versions/1.5/README.md) — normative toolchain, configuration, ownership, and verification contract
- [Python Tooling 1.5 adoption guide](versions/1.5/adopt.md) — complete options, outputs, migration, and recovery
- [Current family adoption guide](adopt.md) — concise enable/reconcile workflow
- [Python Tooling 1.5 agent summary](versions/1.5/agent-summary.md) — compact authority rules
- [Family index](standard.toml) — indexed payload and digest

## Use this standard when

Use Python Tooling for the uv/uv_build `src/` baseline, Ruff formatting and linting, BasedPyright strict checking, pytest with coverage.py, pip-audit, CI, VS Code, and bounded agent instructions. The control plane composes only declared package-owned tables, properties, and blocks and preserves unrelated consumer configuration.

## Adopt

```bash
project-standards standards enable python-tooling --version 1.5
project-standards reconcile
project-standards reconcile --apply
uv lock
python scripts/check.py
```

Review [adopt.md](adopt.md) before applying. Commit unified config, catalog, lock, dependency lock, and reconciled outputs together.

## Released-version errata

The immutable 1.1, 1.2, 1.3, and 1.4 READMEs contain wording written before the atomic Catalog 5 and Project Standards v5.0.0 release. Treat their statement that the V1 root remains authoritative until that release as release-time history. Catalog 5 now selects `python-tooling@1.5`; the immutable payload bytes remain unchanged.

In the immutable 1.4 README, the statement that a modified `scripts/check.py` remains blocking applies only while `script_ownership = "managed"`. Setting `script_ownership = "consumer-owned"` preserves the customized script and leaves it outside reconciliation, verification, and lock state. `.python-version` and modified managed outputs retain the stated blocking behavior.

## Legacy boundary

The unversioned copy-adopt toolchain, `project-standards adopt python-tooling`, and `.project-standards.yml` fragments are migration evidence only. They do not define current Catalog 5 composition or ownership.
