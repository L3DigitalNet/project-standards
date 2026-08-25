# Python Tooling family: Agent Summary

Current authority is the Catalog 5 consumer payload [`python-tooling@1.15`](versions/1.15/agent-summary.md). Its [versioned standard](versions/1.15/README.md) wins over this mutable navigation summary.

- Resolve options and resources from the selected immutable payload, never from `.project-standards.yml` under unified authority.
- Let the control plane compose `pyproject.toml`, EditorConfig, VS Code, workflows, and bounded instruction units. Preserve unrelated consumer values.
- Use uv for dependencies and environments, Ruff for formatting, linting, and imports, the selected Pyright-family checker for types, pytest plus coverage.py for tests, and pip-audit for dependency vulnerabilities.
- Treat conflicting claimed TOML keys or tables as a preflight failure; do not replace whole shared containers.
- Exempt a Ruff rule for one path with the typed `ruff.extend_per_file_ignores` option rather than widening `ruff.extend_ignore` repository-wide.
- Select a self-hosted runner pool for the managed Check job with `runner_labels`; empty keeps the GitHub-hosted runner and the byte-identical render.
- Set `ruff.enforce_line_length = true` to gate the declared `line_length` on prose too; `ruff.extend_select` cannot reach `E501`, because Ruff resolves `ignore` last.
- Run the rendered verification gate before claiming completion.
- Disable and migrate through the control plane so reference-counted shared units and central-lock ownership remain correct.

See the [current adoption guide](adopt.md) for exact options, migration, and recovery.
