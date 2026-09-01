# Adopt Python Tooling 1.18

Python Tooling 1.18 is reconciled by the V5 control plane; do not copy payload files or merge a printed `pyproject.toml` fragment.

## Suitability

Use this package for a Python project that wants one declared uv/build/layout/tooling baseline with managed CI and bounded editor/agent integration. It supports `uv_build`, Hatchling, setuptools, or a deliberately non-installable mode and `src`, flat, or `explicit` layouts; select only options that match the repository's deliberate toolchain intent.

## Prerequisite: consumer-owned project metadata

Every adoption composes `[dependency-groups]`, `[tool.*]`, and — unless `build_backend = "none"` — `[build-system]` around metadata this package never authors. Declare the repository's own PEP 621 identity before enabling:

```toml
[project]
name = "your-distribution-name"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = []
```

A repository that is deliberately not a distribution sets `build_backend = "none"` as well. That option omits `[build-system]`; it does not remove the `[project]` requirement. uv classifies a `pyproject.toml` carrying `[project]` with no `[build-system]` as `source = { virtual = "." }`, which is exactly what the required `uv lock` step and every `uv run` command in the gate below need — and uv refuses any `pyproject.toml` with no `[project]` table at all, with `error: No 'project' table found`.

Reconcile therefore refuses before writing anything, for every backend selection, when an absent `pyproject.toml` or one with no `[project]` table would leave a file the required `uv lock` step cannot read (issues [#109](https://github.com/L3DigitalNet/project-standards/issues/109) and [#204](https://github.com/L3DigitalNet/project-standards/issues/204)); the block is `PT-PROJECT-METADATA`. Through 1.17 this check was skipped entirely under `build_backend = "none"`, so such a repository reached `uv lock` and failed there instead. Adopting 1.18 surfaces that same failure earlier; it breaks no adoption whose gate was passing.

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
runner_labels = []

[standards.python-tooling.config.ruff]
line_length = 100
enforce_line_length = false
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
task_prefix = ""

[standards.python-tooling.config.agent_instructions]
include_fix_commands = true
```

The empty `task_prefix` preserves the managed `check`, `fix`, `test`, `typecheck`, and `audit` labels. To select the only supported prefixed set, use:

```toml
[standards.python-tooling.config.vscode]
format_on_save = true
task_prefix = "python: "
```

Preview before applying. On a clean switch, the plan must REMOVE the five lock-matching unprefixed tasks and CREATE the five prefixed tasks. If the tasks were already renamed by hand, first restore the five unprefixed managed tasks to their lock-matching values while retaining any matching prefixed copies. Before restoration, reconciliation remains blocked and reports `/vscode/task_prefix`; after restoration, the plan can REMOVE the old tasks and ADOPT matching prefixed tasks (or CREATE any that are absent).

`additional_dev_dependencies` is the only supported way to add packages to the development group this standard owns: each entry is a PEP 508 requirement string appended to the rendered `[dependency-groups] dev` list, so a pytest plugin, a stub package, or a local uv workspace member is installed by `uv sync` and available to every `uv run` command in the gate. Editing the rendered `dev` list by hand is managed drift and blocks the next reconcile.

Set `coverage.parallel = true` to collect parallel data and combine it before reporting. `coverage.patch` accepts only `"subprocess"`; a non-empty list requires `parallel = true`, enables coverage.py subprocess startup patching, and selects `coverage[toml]>=7.10.0`. `workflow_ownership = "managed"` lets the package own `.github/workflows/check.yml`; `"consumer-owned"` leaves that path outside reconciliation, verification, and lock state. `script_ownership` makes the same decision for `scripts/check.py`: `"managed"` renders and verifies the enforcement script, while `"consumer-owned"` leaves a customized script entirely to the consumer.

`runner_labels` selects the runner pool the managed Check job requests, for example `runner_labels = ["self-hosted", "linux", "x64"]`. The default is empty, which renders `runs-on: ubuntu-latest` — byte-for-byte what 1.14 produced — so a repository that sets nothing sees no reconciliation change. A non-empty selection renders the labels as a YAML block sequence in the job's own `runs-on`, and GitHub allocates only a runner carrying every listed label. Labels are limited to letters, digits, `.`, `_`, and `-`, and must start with a letter or digit. Opting in rewrites `.github/workflows/check.yml`.

This package's workflow is self-contained: it declares its own job and fires on `push` and `pull_request`, so unlike the Markdown Tooling, Markdown Frontmatter, and Project Specification callers there is no `workflow_call` boundary and no trigger on which the selection is silently ignored. The option has no effect while `workflow_ownership = "consumer-owned"` — the package renders no workflow then — so pin `runs-on` in the owned file instead.

`enforce_line_length = true` makes the declared `line_length` a hard gate. The default `false` renders `ignore = ["E501"]`, which is what 1.14 shipped: `ruff format` rewraps code but never reflows comment, docstring, or string prose, so overlong prose passes every gate today. Opting in renders an empty `ignore` and the baseline `E` selector enforces the limit on every line. Expect existing findings on adoption; re-wrap the prose, or scope an exemption with `ruff.extend_per_file_ignores`. `ruff.extend_select` cannot substitute for this option, because Ruff resolves `ignore` after `extend-select` and the exclusion wins.

`build_backend = "uv_build"` renders `requires = ["uv_build>=0.11,<1.0"]`, which requires uv 0.11 or later. uv takes an in-process fast path for its own build backend only while the running uv satisfies that requirement, and prints `build_system.requires = [...] does not contain the current uv version X` when it does not; an older uv therefore reports that warning on every `uv sync` and `uv build` even though the commands succeed. The bound deliberately spans the whole pre-1.0 `uv_build` series rather than a single minor, because this payload is immutable and cannot track uv's release train (issue [#182](https://github.com/L3DigitalNet/project-standards/issues/182)). Verify with `uv --version` before adopting, and expect reconciliation from 1.15 or earlier to rewrite the `[build-system]` table once.

The Ruff `extend_include`, `extend_select`, and `extend_ignore` lists render their native tool keys always, as empty arrays when the option is empty; each is a separately owned key, and an empty array is inert in Ruff. The coverage `omit` list still emits its key only when nonempty. `build_backend = "none"` declares a deliberately non-installable repository and omits only `[build-system]`. Fresh adoption leaves performance CI off; set `ci.performance = true` only when the repository has matching performance tests.

### Declared roots must exist before the gate runs

Every declared source and test root is rendered into the checker `include` and the bounded Ruff commands, and nothing creates the directories. `pytest.test_paths` requires at least one entry, so a repository adopting the standard before it has written its first test still declares `tests/`. BasedPyright then exits non-zero on `File or directory "/repo/tests" does not exist.` with zero findings, and the gate stops before pytest.

`reconcile --check` reports each missing root as a `PT-DECLARED-ROOT-MISSING` warning naming the path. The warning does not block the reconcile; create the directory (an empty placeholder is enough — `.gitkeep` is the convention used for `docs/handoff/bugs/`), or drop the root from `pytest.test_paths`, `additional_source_roots`, or `source_layout`. Reconciliation never creates the directory itself: repository structure is consumer authority, and a declaration may legitimately precede the code it describes.

### Vendored or generated code and the type checker

`ruff.extend_exclude` scopes Ruff only. It does not reach BasedPyright or Pyright, and that is deliberate: both checkers ship their own default `exclude` list, a key-level unit has to render whether or not its option is empty, and an unconditional empty `exclude` would replace those defaults for every consumer.

Exclude such paths from the type checker by writing the key yourself:

```toml
[tool.basedpyright]
exclude = [".venv", "data", "vendored/frozen-tool"]
```

`exclude` is not declared by this package, so it is consumer-owned: reconciliation preserves it, `reconcile --check` keeps reporting `ok: true` with no findings, and it never becomes managed drift. The same holds for any other undeclared key in `[tool.basedpyright]`, `[tool.pyright]`, `[tool.pytest.ini_options]`, or `[tool.ruff]` — see the ownership rule below. Use it for version-locked release mirrors, checksum-verified vendored copies, and generated code, where reformatting or "fixing" the file is the wrong answer.

### Scoped per-file rule exemptions

`ruff.extend_ignore` silences a rule everywhere. When the exemption belongs to a path — permitting `Any` at dynamic test boundaries such as `SourceFileLoader`, JSON fixtures, and pytest monkeypatch seams, while `ANN401` still governs shipped code — declare it as a glob instead:

```toml
[standards.python-tooling.config.ruff.extend_per_file_ignores]
"tests/**/*.py" = ["ANN401"]
```

That renders into the package-owned per-file-ignore table without discarding what the package already puts there:

```toml
[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101", "ANN401"]
```

Each key is a Ruff path glob and each value is a nonempty list of rule selectors. Distinct globs render side by side, and several rules on one glob are all appended. Consumer entries render in sorted order, so the file does not change when the option's key order does. Delete an entry and only that entry disappears; the package default (`S101` for tests) stays.

Ruff's own `[tool.ruff.lint.extend-per-file-ignores]` table is not declared by this package, so writing it directly still works and reconciliation still preserves it. Prefer the option: its rule codes and glob shapes are validated at option resolution, the rendered value is part of the effective-config digest, and `reconcile --check` reports it as managed rather than leaving it unverified.

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

Conflicting managed `pyproject.toml` keys or tables block before any write. Reconcile the consumer value with the selected package option, then rerun the preview. Keys not declared by the package remain consumer-owned, including additional BasedPyright, Pyright, and pytest settings such as `exclude` and `pythonpath`, and every undeclared `[tool.ruff]` sub-table such as `[tool.ruff.lint.flake8-bugbear]`. Unrelated tables, editor settings, tasks, extension recommendations, and instruction blocks are preserved.

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
| The strict gate reports `reportMissingTypeStubs` for the repository's own package | The layout root now renders into the checker `extraPaths`, so local source resolves before the editable installation of the same distribution. Preview and apply 1.18; if the repository owned `extraPaths` itself, move those roots into `additional_source_roots` first. Shipping a `py.typed` marker remains a valid alternative and stays compatible. |
| Python lives only under selected subprojects and there is no repository-wide Python root | Set `source_layout = "explicit"` and declare every root in `additional_source_roots` plus `pytest.test_paths`. No `src` or `.` root is rendered, so unrelated nested projects and undeclared scripts stay outside the checker, Ruff, coverage, and pytest scopes. The mode requires at least one declared source root; an empty declaration fails option resolution. |
| Tests under an explicit root fail with `ModuleNotFoundError` for the subproject's own package | Declared roots set the checker, Ruff, coverage, and pytest **scopes**; none of them makes a package under a subproject **importable** by the root environment, so a `conftest.py` doing `from subproj.content.loader import ...` still fails. Two fixes, and they cover different ground. Write `pythonpath = ["subproj/src"]` into `[tool.pytest.ini_options]` yourself — an undeclared key there is consumer-owned and survives reconciliation, exactly as `exclude` does above — which fixes `pytest` and nothing else. Or make the subproject a uv workspace member and list it in `additional_dev_dependencies`, which installs it into the environment so every `uv run` command, not just pytest, can import it. |
| pytest needs an ini key this package has no option for, such as `asyncio_mode` or `pythonpath` | This package owns exactly `minversion`, `testpaths`, `addopts`, and `markers` in `[tool.pytest.ini_options]`, each as its own key-level unit. Every other key in that table is undeclared and therefore consumer-owned: write it straight into the managed table. Reconciliation preserves it through `reconcile --apply`, through `validate`, and through an option change that rewrites an owned key in the same table. Order the two steps correctly for a key a plugin registers — the package-owned `addopts` includes `--strict-config`, so pytest aborts with `ERROR: Unknown config option: asyncio_mode`, `collected 0 items`, exit code 4 while the plugin is absent. That message names neither `--strict-config` nor the missing plugin, so it reads like a fresh defect rather than the consequence of adding the key first. Add the plugin to `additional_dev_dependencies`, run `uv lock`, and only then add the key. Core pytest keys such as `pythonpath` are exempt: `--strict-config` rejects only keys no installed plugin registered. |
| An extra root is strictly typed but has no unit tests, so declaring it fails the coverage gate | Declare it as a table with `coverage = false` — for example `additional_source_roots = ["docs/handoff/bugs", { path = "scripts", coverage = false }]`. The root stays in the checker `include` and Ruff `src` values but is excluded from `coverage.run.source`. Plain strings keep the both-scope meaning. |
| Shared EditorConfig or VS Code unit conflicts | Reconcile only the package-owned semantic property; preserve unrelated consumer settings. |
