# Python Tooling Standard

- **Package version:** 1.1
- **Availability:** Consumer-selectable
- **Companion:** Python Coding 0.5 (reference-only)

## Purpose

Python Tooling defines one reproducible Python project toolchain built around uv, Ruff, a selected Pyright-family type checker, pytest with coverage.py, pip-audit, and a deterministic local/CI gate. The V5 control plane owns individual semantic units rather than replacing shared root containers.

## Managed surfaces

The package delegates lifecycle and locking to the central control plane:

- `.python-version`, `.github/workflows/check.yml`, and `scripts/check.py` are exclusive whole-file units rendered from package options.
- `pyproject.toml` is composed through bounded TOML table and key contributions. Existing conflicting values block before any write.
- `.editorconfig` properties are shared by stable identity with Markdown Tooling where their values are identical.
- VS Code extensions, settings, and task labels are independent JSONC units. Unrelated recommendations, settings, and tasks remain consumer-owned.
- `AGENTS.md` and `CLAUDE.md` receive only the delimiter-bounded `python-tooling` block, so Agent Handoff and other packages retain their own blocks.

Disabling the package removes only centrally locked Python Tooling units. Re-enabling reconstructs them from the selected immutable payload.

## Options

The closed option schema controls:

- the independently selected `1.0` or `1.1` consumer contract and supported Python versions;
- build backend (`uv_build`, `hatchling`, or `setuptools`);
- `src` or flat source layout;
- Ruff line length;
- BasedPyright or Pyright, including checking mode;
- the mandatory pytest coverage floor;
- pip-audit vulnerability exceptions;
- CI triggers, performance tests, VS Code format-on-save behavior, and bounded agent instruction detail.

The type-checker choice fans out to dependency declarations, both Pyright-family configuration tables, the CI workflow, local check script, VS Code settings/tasks, and agent instructions. The inactive checker table and editor setting are explicitly set to `off`; the selected checker is the only dependency and command in the gate. The BasedPyright extension recommendation remains a reversible, package-owned editor aid even when the Pyright CLI is selected; the editor authority follows the selected settings, not the dormant recommendation.

## Build backends

Use `uv_build` for pure-Python packages unless project constraints require another backend. The selected backend owns the complete `[build-system]` table. See [Build Backend Guidance](build-backend.md).

## Verification gate

The rendered gate runs the mandatory commands in this order:

1. Ruff format check.
2. Ruff lint.
3. Selected type checker.
4. pytest under coverage, followed by the coverage report.
5. Optional performance tests.
6. pip-audit.

CI-disabled configurations retain an explicit manual-only workflow so the selected gate remains inspectable without running automatically.

## Migration

The automatic V4 migration recognizes only the legacy `python_tooling.version` setting and byte-identical files shipped by the V1 copy-adopt bundle. It preserves that consumer contract selector independently from the selected 1.1 package payload; both supported contract values render the same toolchain because the selector remains metadata-only. Known whole-file agent and VS Code content is retired into bounded contributions; shared EditorConfig and extension files are preserved while their package-owned units enter the central lock. Modified legacy content blocks migration instead of being overwritten.

The V1 root family manifest remains authoritative in this source checkout until the atomic Task 14 activation commit.

## Update process

Payload 1.1 is immutable. Behavioral or option changes require a new package version, new payload digest, catalog entry, migration edge where necessary, and source plus extracted-wheel compatibility evidence.
