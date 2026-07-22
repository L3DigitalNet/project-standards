# Python Tooling Standard

- **Package version:** 1.7
- **Availability:** Consumer-selectable
- **Companion:** Python Coding 0.5 (reference-only)

## Purpose

Python Tooling defines one reproducible Python project toolchain built around uv, Ruff, a selected Pyright-family type checker, pytest with coverage.py, pip-audit, and a deterministic local/CI gate. The V5 control plane owns individual semantic units rather than replacing shared root containers.

## Managed surfaces

The package delegates lifecycle and locking to the central control plane:

- `.python-version` is an exclusive whole-file unit rendered from package options. The package also manages `scripts/check.py` unless `script_ownership` is `consumer-owned`, and `.github/workflows/check.yml` unless `workflow_ownership` is `consumer-owned`.
- `pyproject.toml` is composed through bounded TOML table and key contributions. Python Tooling owns only its declared keys in the selected checker and pytest tables, so consumer settings such as `extraPaths` and `pythonpath` remain outside package ownership. Existing conflicting managed values block before any write.
- `.editorconfig` properties are shared by stable identity with Markdown Tooling where their values are identical.
- VS Code extensions, settings, and task labels are independent JSONC units. Unrelated recommendations, settings, and tasks remain consumer-owned.
- `AGENTS.md` and `CLAUDE.md` receive only the delimiter-bounded `python-tooling` block, so Agent Handoff and other packages retain their own blocks.

Disabling the package removes only centrally locked Python Tooling units. Re-enabling reconstructs them from the selected immutable payload.

## Options

The closed option schema controls:

- the independently selected `1.0` or `1.1` consumer contract and supported Python versions;
- build backend (`uv_build`, `hatchling`, or `setuptools`);
- `src` or flat source layout;
- extra first-party source roots as `additional_source_roots` entries — plain strings join the checker `include`, Ruff `src`, and `coverage.run.source` values, while `{ path = "...", coverage = false }` tables keep a strictly-typed tooling root out of coverage measurement;
- Ruff line length;
- BasedPyright or Pyright, including checking mode;
- the mandatory pytest coverage floor;
- pip-audit vulnerability exceptions;
- workflow ownership, CI triggers, performance tests, VS Code format-on-save behavior, and bounded agent instruction detail.

`workflow_ownership = "managed"` materializes, verifies, locks, and removes `.github/workflows/check.yml` with the package lifecycle. `workflow_ownership = "consumer-owned"` leaves that path outside package actions, verification, and lock state; the consumer is responsible for its validity and maintenance. The `ci.*` options remain schema-valid in consumer-owned mode but affect only a managed workflow, so they are inert while ownership remains with the consumer. Returning to managed ownership is a separate acquisition boundary and conflicts with unequal consumer bytes rather than overwriting them. `script_ownership` applies the same contract to `scripts/check.py`: managed mode renders, verifies, and locks the enforcement script, while consumer-owned mode leaves the path outside package actions so a customized gate survives migration and reconciliation.

The type-checker choice fans out to dependency declarations, both Pyright-family configuration tables, the managed CI workflow, local check script, VS Code settings/tasks, and agent instructions. The inactive checker table and editor setting are explicitly set to `off`; the selected checker is the only dependency and command in the gate. The BasedPyright extension recommendation remains a reversible, package-owned editor aid even when the Pyright CLI is selected; the editor authority follows the selected settings, not the dormant recommendation.

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

Managed CI-disabled configurations retain an explicit manual-only workflow so the selected gate remains inspectable without running automatically.

## Migration

The automatic V4 migration recognizes the legacy `python_tooling.version`, Python Tooling option values, and byte-identical files shipped by the V1 copy-adopt bundle. It preserves the consumer contract selector independently from the selected 1.7 package payload; both supported contract values render the same toolchain because the selector remains metadata-only. Known whole-file agent and VS Code content is retired into bounded contributions; shared EditorConfig and extension files are preserved while their package-owned units enter the central lock.

An exact known workflow migrates according to the selected ownership. An unknown workflow remains blocking in managed mode. In consumer-owned mode, the explicit raw legacy intent authorizes only preservation of that single whole-file path; the migration preview labels it consumer-owned, preserved, and not semantically validated, and the control plane creates no workflow action, unit, or lock entry.

Instruction and shared configuration targets (`CLAUDE.md`, `AGENTS.md`, `.editorconfig`, `.vscode/extensions.json`, `.vscode/settings.json`, `.vscode/tasks.json`) declare `unknown_content_disposition = "preserve"`: consumer-modified content at those paths is preserved instead of blocking, the preview reports a `CP-MIGRATION-BOUNDED-TAKEOVER` warning per file, and steady-state reconciliation manages only the bounded package-owned units inside the preserved file. Superseded V1 boilerplate inside a preserved file is left for the consumer to remove. Modified `scripts/check.py`, `.python-version`, or a modified managed workflow remains blocking.

The V1 root family manifest remains authoritative in this source checkout until the atomic v5 release commit.

## Update process

Payload 1.7 is immutable after publication. Behavioral or option changes require a new package version, new payload digest, catalog entry, migration edge where necessary, and source plus extracted-wheel compatibility evidence.
