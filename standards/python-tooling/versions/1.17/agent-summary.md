# Python Tooling 1.17 Agent Summary

The canonical [README](README.md) is authoritative and wins if this summary conflicts with it.

- Resolve options and resources from the selected immutable payload; never read active behavior from `.project-standards.yml`.
- Let the control plane compose `pyproject.toml`, EditorConfig, VS Code, and bounded instruction units. Do not replace whole shared containers.
- Use uv for dependencies and environments, Ruff for formatting/lint/import sorting, the selected Pyright-family checker for types, pytest plus coverage.py for tests, and pip-audit for dependency vulnerabilities.
- Set `pytest.test_paths` (default `["tests"]`) to relocate or split pytest collection roots; they drive pytest `testpaths`, the checker `include`, Ruff `src`, and the VS Code `pytestArgs`, but not `coverage.run.source`.
- Declare every extra first-party root in `additional_source_roots`; with the layout root it renders the checker `extraPaths`, so local source resolves before an editable installation of the same distribution. Do not hand-edit `extraPaths` — it is a managed unit.
- Use the closed Ruff extension lists and coverage `omit` list for additive repository intent. Empty lists materialize no extra keys.
- Scope a rule exemption to a path with `ruff.extend_per_file_ignores` (glob to rule list) rather than `ruff.extend_ignore`, which drops the rule repository-wide. Entries compose into the package's own per-file ignores; they never replace them. Ruff's separate `[tool.ruff.lint.extend-per-file-ignores]` table stays consumer-owned.
- `runner_labels` selects the runner pool the managed Check job requests. It templates the job's own `runs-on` as a YAML block sequence — this workflow is self-contained, not a reusable-workflow caller — so every trigger honors it. Empty is the default and renders the byte-identical `runs-on: ubuntu-latest`. It is inert while `workflow_ownership = "consumer-owned"`.
- Set `ruff.enforce_line_length = true` to make the declared `line_length` a real gate; it drops `E501` from the rendered `ignore` list. The default keeps `E501` ignored, because `ruff format` never reflows comment, docstring, or string prose. `ruff.extend_select` cannot re-enable the rule — Ruff resolves `ignore` last.
- `build_backend = "uv_build"` renders `requires = ["uv_build>=0.11,<1.0"]`; adoption needs uv 0.11 or later, or uv warns that its own version falls outside the requirement. Do not narrow the bound in the consumer's file — the table is package-owned and reconciliation restores it.
- Use `build_backend = "none"` only for deliberately non-installable repositories; it omits `[build-system]` without removing development tooling.
- Fresh adoption leaves performance CI off. An explicit `ci.performance = true` retains pytest's ordinary exit-5 result when no performance tests are collected.
- Treat `/vscode/task_prefix` as a closed label-set selector: `""` keeps the five base labels and `"python: "` selects their prefixed forms. Restore missing lock-matching base tasks before switching an already hand-renamed consumer.
- Treat conflicting claimed TOML keys/tables as a preflight failure. Preserve unrelated consumer values byte-for-byte.
- Run the rendered verification gate before claiming completion. `scripts/check.py --help` prints usage and exits 0 without running any command; any other argument is a usage error that exits 2.
- Disable or migrate through the control plane so reference-counted shared units and central-lock ownership remain correct.
