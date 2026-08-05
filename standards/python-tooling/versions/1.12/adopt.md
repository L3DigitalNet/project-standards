# Adopt Python Tooling 1.12

Python Tooling 1.12 is reconciled by the V5 control plane; do not copy payload files or merge a printed `pyproject.toml` fragment.

## Suitability

Use this package for a Python project that wants one declared uv/build/layout/tooling baseline with managed CI and bounded editor/agent integration. It supports `uv_build`, Hatchling, setuptools, or a deliberately non-installable mode and `src`, flat, or `explicit` layouts; select only options that match the repository's deliberate toolchain intent.

## Prerequisite: consumer-owned project metadata

An installable adoption composes `[dependency-groups]`, `[build-system]`, and `[tool.*]` around metadata this package never authors. Declare the repository's own PEP 621 identity before enabling:

```toml
[project]
name = "your-distribution-name"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = []
```

A repository that is deliberately not a distribution sets `build_backend = "none"` instead and needs no `[project]` table.

Reconcile refuses before writing anything when neither decision is on record — an absent `pyproject.toml` or one with no `[project]` table blocks with `PT-PROJECT-METADATA`, because the alternative is a file the required `uv lock` step below cannot read (issue #109).

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
additional_source_roots = []
additional_dev_dependencies = []
workflow_ownership = "managed"
script_ownership = "managed"

[standards.python-tooling.config.ruff]
line_length = 100
extend_exclude = [".claude", ".agents", ".codex", ".continue"]
extend_include = []
extend_select = []
extend_ignore = []

[standards.python-tooling.config.type_checker]
name = "basedpyright"
mode = "strict"

[standards.python-tooling.config.pytest]
fail_under = 85
markers = []
coverage_exclude_also = []
test_paths = ["tests"]

[standards.python-tooling.config.coverage]
parallel = false
patch = []
omit = []

[standards.python-tooling.config.pip_audit]
ignore_vulnerabilities = []

[standards.python-tooling.config.ci]
enabled = true
performance = false

[standards.python-tooling.config.vscode]
format_on_save = true

[standards.python-tooling.config.agent_instructions]
include_fix_commands = true
```

Set `coverage.parallel = true` to collect parallel data and combine it before reporting. `coverage.patch` accepts only `"subprocess"`; a non-empty list requires `parallel = true`, enables coverage.py subprocess startup patching, and selects `coverage[toml]>=7.10.0`. `workflow_ownership = "managed"` lets the package own `.github/workflows/check.yml`; `"consumer-owned"` leaves that path outside reconciliation, verification, and lock state. `script_ownership` makes the same decision for `scripts/check.py`: `"managed"` renders and verifies the enforcement script, while `"consumer-owned"` leaves a customized script entirely to the consumer.

The Ruff `extend_include`, `extend_select`, and `extend_ignore` lists render their native tool keys always, as empty arrays when the option is empty; each is a separately owned key, and an empty array is inert in Ruff. The coverage `omit` list still emits its key only when nonempty. `build_backend = "none"` declares a deliberately non-installable repository and omits only `[build-system]`. Fresh adoption leaves performance CI off; set `ci.performance = true` only when the repository has matching performance tests.

The rendered `scripts/check.py` takes no arguments. `python scripts/check.py --help` prints usage and exits 0 without running a gate command, and any other argument exits 2 as a usage error, so a help probe or a typo never starts the toolchain.

Preview and apply:

```bash
project-standards reconcile --check
project-standards reconcile --apply
uv lock
python scripts/check.py
```

Commit `.standards/config.toml`, `.standards/lock.toml`, `uv.lock`, and the reconciled outputs together. The lock refresh is required because Python Tooling owns the development dependency group.

## Existing projects

Conflicting managed `pyproject.toml` keys or tables block before any write. Reconcile the consumer value with the selected package option, then rerun the preview. Keys not declared by the package remain consumer-owned, including additional BasedPyright, Pyright, and pytest settings such as `extraPaths` and `pythonpath`. Unrelated tables, editor settings, tasks, extension recommendations, and instruction blocks are preserved.

For a V4 consumer, use the migration command instead of manually deleting legacy files:

```bash
project-standards init --catalog 5 --migrate
project-standards init --catalog 5 --migrate --apply
```

A consumer-owned workflow is outside reconciliation, so nothing in this package reports on it — including hosted GitHub configuration that depends on it. Branch-protection and ruleset required status checks key off the workflow job's display name, which lives outside Git, so renaming a consumer-owned check job can silently orphan a required context and leave later pull requests unmergeable while every local check passes. Inspect the hosted required contexts before and after any job rename, and coordinate the rename with the branch-protection or ruleset update.

Modified recognized legacy files resolve in one of three ways: instruction and shared configuration targets (`CLAUDE.md`, `AGENTS.md`, `.editorconfig`, `.vscode/*`) are preserved automatically with a `CP-MIGRATION-BOUNDED-TAKEOVER` warning while the package takes over only its bounded units inside the file; a modified workflow requires the explicit `workflow_ownership = "consumer-owned"` decision in the legacy configuration, and a modified `scripts/check.py` requires the matching `script_ownership = "consumer-owned"` decision; any other modified recognized file blocks until its known content is restored.

## Disable

Set `enabled = false`, preview, and apply. The central lock removes only Python Tooling-owned units and preserves shared units still referenced by Markdown Tooling or another package.

## Troubleshooting

During a V4 → V5 migration, `.standards/config.toml` does not exist yet: set the same package options under the `python_tooling:` namespace in `.project-standards.yml` and re-preview; every setting the migration provider recognizes is accepted there.

| Finding | Resolution |
| --- | --- |
| A `pyproject.toml` key conflicts | Make the repository intent explicit in the matching package option, then preview again. |
| `uv.lock` is stale after apply | Run `uv lock` and commit it with the config, central lock, and reconciled outputs. |
| A custom marker, coverage exclusion, Ruff exclusion, or dev dependency disappeared in preview | Add it to the corresponding closed option; migration preserves explicit supported intent only. |
| Tests live somewhere other than `tests/` (or in more than one directory) | Set `pytest.test_paths` to the collection roots — for example `test_paths = ["qa/unit", "qa/integration"]`. They drive pytest `testpaths`, the checker `include`, the Ruff `src` value, and the VS Code `pytestArgs`, but never `coverage.run.source` on their own. |
| First-party Python lives outside the layout roots (repository tooling, an extra package root) | Declare each extra root in `additional_source_roots`; it merges after the collection roots into the checker `include`, the Ruff `src` value, and `coverage.run.source`, and after the layout root into the checker `extraPaths`. |
| The strict gate reports `reportMissingTypeStubs` for the repository's own package | The layout root now renders into the checker `extraPaths`, so local source resolves before the editable installation of the same distribution. Preview and apply 1.12; if the repository owned `extraPaths` itself, move those roots into `additional_source_roots` first. Shipping a `py.typed` marker remains a valid alternative and stays compatible. |
| Python lives only under selected subprojects and there is no repository-wide Python root | Set `source_layout = "explicit"` and declare every root in `additional_source_roots` plus `pytest.test_paths`. No `src` or `.` root is rendered, so unrelated nested projects and undeclared scripts stay outside the checker, Ruff, coverage, and pytest scopes. The mode requires at least one declared source root; an empty declaration fails option resolution. |
| An extra root is strictly typed but has no unit tests, so declaring it fails the coverage gate | Declare it as a table with `coverage = false` — for example `additional_source_roots = ["docs/handoff/bugs", { path = "scripts", coverage = false }]`. The root stays in the checker `include` and Ruff `src` values but is excluded from `coverage.run.source`. Plain strings keep the both-scope meaning. |
| Shared EditorConfig or VS Code unit conflicts | Reconcile only the package-owned semantic property; preserve unrelated consumer settings. |
