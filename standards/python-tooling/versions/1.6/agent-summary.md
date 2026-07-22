# Python Tooling 1.6 Agent Summary

The canonical [README](README.md) is authoritative and wins if this summary conflicts with it.

- Resolve options and resources from the selected immutable payload; never read active behavior from `.project-standards.yml`.
- Let the control plane compose `pyproject.toml`, EditorConfig, VS Code, and bounded instruction units. Do not replace whole shared containers.
- Use uv for dependencies and environments, Ruff for formatting/lint/import sorting, the selected Pyright-family checker for types, pytest plus coverage.py for tests, and pip-audit for dependency vulnerabilities.
- Treat conflicting claimed TOML keys/tables as a preflight failure. Preserve unrelated consumer values byte-for-byte.
- Run the rendered verification gate before claiming completion.
- Disable or migrate through the control plane so reference-counted shared units and central-lock ownership remain correct.
