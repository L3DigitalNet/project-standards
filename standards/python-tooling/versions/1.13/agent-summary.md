# Python Tooling 1.13 Agent Summary

The canonical [README](README.md) is authoritative and wins if this summary conflicts with it.

- Resolve options and resources from the selected immutable payload; never read active behavior from `.project-standards.yml`.
- Let the control plane compose `pyproject.toml`, EditorConfig, VS Code, and bounded instruction units. Do not replace whole shared containers.
- Use uv for dependencies and environments, Ruff for formatting/lint/import sorting, the selected Pyright-family checker for types, pytest plus coverage.py for tests, and pip-audit for dependency vulnerabilities.
- Set `pytest.test_paths` (default `["tests"]`) to relocate or split pytest collection roots; they drive pytest `testpaths`, the checker `include`, Ruff `src`, and the VS Code `pytestArgs`, but not `coverage.run.source`.
- Declare every extra first-party root in `additional_source_roots`; with the layout root it renders the checker `extraPaths`, so local source resolves before an editable installation of the same distribution. Do not hand-edit `extraPaths` — it is a managed unit.
- Use the closed Ruff extension lists and coverage `omit` list for additive repository intent. Empty lists materialize no extra keys.
- Scope a rule exemption to a path with `ruff.extend_per_file_ignores` (glob to rule list) rather than `ruff.extend_ignore`, which drops the rule repository-wide. Entries compose into the package's own per-file ignores; they never replace them. Ruff's separate `[tool.ruff.lint.extend-per-file-ignores]` table stays consumer-owned.
- Use `build_backend = "none"` only for deliberately non-installable repositories; it omits `[build-system]` without removing development tooling.
- Fresh adoption leaves performance CI off. An explicit `ci.performance = true` retains pytest's ordinary exit-5 result when no performance tests are collected.
- Treat conflicting claimed TOML keys/tables as a preflight failure. Preserve unrelated consumer values byte-for-byte.
- Run the rendered verification gate before claiming completion. `scripts/check.py --help` prints usage and exits 0 without running any command; any other argument is a usage error that exits 2.
- Disable or migrate through the control plane so reference-counted shared units and central-lock ownership remain correct.
