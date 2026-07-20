# Adopt Python Tooling 1.4

Python Tooling 1.4 is reconciled by the V5 control plane; do not copy payload files or merge a printed `pyproject.toml` fragment.

## Suitability

Use this package for a Python project that wants one declared uv/build/layout/tooling baseline with managed CI and bounded editor/agent integration. It supports `uv_build`, Hatchling, or setuptools and `src` or flat layouts; select only options that match the repository's deliberate toolchain intent.

## Enable

Add the package to `.standards/config.toml`:

```toml
[standards.python-tooling]
enabled = true
version = "latest"

[standards.python-tooling.config]
contract_version = "1.1"
python_version = "3.14"
build_backend = "uv_build"
source_layout = "src"
additional_dev_dependencies = []
workflow_ownership = "managed"
script_ownership = "managed"

[standards.python-tooling.config.ruff]
line_length = 100
extend_exclude = [".claude", ".agents", ".codex", ".continue"]

[standards.python-tooling.config.type_checker]
name = "basedpyright"
mode = "strict"

[standards.python-tooling.config.pytest]
fail_under = 85
markers = []
coverage_exclude_also = []

[standards.python-tooling.config.coverage]
parallel = false
patch = []

[standards.python-tooling.config.pip_audit]
ignore_vulnerabilities = []

[standards.python-tooling.config.ci]
enabled = true
performance = true

[standards.python-tooling.config.vscode]
format_on_save = true

[standards.python-tooling.config.agent_instructions]
include_fix_commands = true
```

Set `coverage.parallel = true` to collect parallel data and combine it before reporting. `coverage.patch` accepts only `"subprocess"`; a non-empty list requires `parallel = true`, enables coverage.py subprocess startup patching, and selects `coverage[toml]>=7.10.0`. `workflow_ownership = "managed"` lets the package own `.github/workflows/check.yml`; `"consumer-owned"` leaves that path outside reconciliation, verification, and lock state. `script_ownership` makes the same decision for `scripts/check.py`: `"managed"` renders and verifies the enforcement script, while `"consumer-owned"` leaves a customized script entirely to the consumer.

Preview and apply:

```bash
project-standards reconcile --check
project-standards reconcile --apply
uv lock
python scripts/check.py
```

Commit `.standards/config.toml`, `.standards/lock.toml`, `uv.lock`, and the reconciled outputs together. The lock refresh is required because Python Tooling owns the development dependency group.

## Existing projects

Conflicting `pyproject.toml` keys or tables block before any write. Reconcile the consumer value with the selected package option, then rerun the preview. Unrelated tables, editor settings, tasks, extension recommendations, and instruction blocks are preserved.

For a V4 consumer, use the migration command instead of manually deleting legacy files:

```bash
project-standards init --catalog 5 --migrate
project-standards init --catalog 5 --migrate --apply
```

Modified recognized legacy files resolve in one of three ways: instruction and shared configuration targets (`CLAUDE.md`, `AGENTS.md`, `.editorconfig`, `.vscode/*`) are preserved automatically with a `CP-MIGRATION-BOUNDED-TAKEOVER` warning while the package takes over only its bounded units inside the file; a modified workflow requires the explicit `workflow_ownership = "consumer-owned"` decision in the legacy configuration, and a modified `scripts/check.py` requires the matching `script_ownership = "consumer-owned"` decision; any other modified recognized file blocks until its known content is restored.

## Disable

Set `enabled = false`, preview, and apply. The central lock removes only Python Tooling-owned units and preserves shared units still referenced by Markdown Tooling or another package.

## Troubleshooting

| Finding | Resolution |
| --- | --- |
| A `pyproject.toml` key conflicts | Make the repository intent explicit in the matching package option, then preview again. |
| `uv.lock` is stale after apply | Run `uv lock` and commit it with the config, central lock, and reconciled outputs. |
| A custom marker, coverage exclusion, Ruff exclusion, or dev dependency disappeared in preview | Add it to the corresponding closed option; migration preserves explicit supported intent only. |
| Shared EditorConfig or VS Code unit conflicts | Reconcile only the package-owned semantic property; preserve unrelated consumer settings. |
