# Adopt Python Tooling 1.1

Python Tooling 1.1 is reconciled by the V5 control plane; do not copy payload files or merge a printed `pyproject.toml` fragment.

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

[standards.python-tooling.config.ruff]
line_length = 100

[standards.python-tooling.config.type_checker]
name = "basedpyright"
mode = "strict"

[standards.python-tooling.config.pytest]
fail_under = 85

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
project-standards migrate --catalog 5
project-standards migrate --catalog 5 --apply
```

Modified recognized legacy files require an explicit ownership decision.

## Disable

Set `enabled = false`, preview, and apply. The central lock removes only Python Tooling-owned units and preserves shared units still referenced by Markdown Tooling or another package.
