# Python Tooling Standard

- **Package version:** 1.16
- **Availability:** Consumer-selectable
- **Companion:** Python Coding 0.6 (reference-only)

## Purpose

Python Tooling defines one reproducible Python project toolchain built around uv, Ruff, a selected Pyright-family type checker, pytest with coverage.py, pip-audit, and a deterministic local/CI gate. The V5 control plane owns individual semantic units rather than replacing shared root containers.

## Managed surfaces

The package delegates lifecycle and locking to the central control plane:

- `.python-version` is an exclusive whole-file unit rendered from package options. The package also manages `scripts/check.py` unless `script_ownership` is `consumer-owned`, and `.github/workflows/check.yml` unless `workflow_ownership` is `consumer-owned`.
- `pyproject.toml` is composed through bounded TOML table and key contributions. Python Tooling owns only its declared keys in the selected checker and pytest tables, so consumer settings such as `pythonpath` remain outside package ownership. The checker `extraPaths` key became a declared unit in 1.11: a repository that owned it before must move those roots into `additional_source_roots`, which renders them. Existing conflicting managed values block before any write.
- `[tool.ruff]` follows that same key-level rule from 1.12 on. The package owns each Ruff key it renders — `target-version`, `line-length`, `src`, `extend-exclude`, `extend-include`, the `[tool.ruff.lint]` scalars, the `per-file-ignores` table, and the `format` table — and nothing else. Every undeclared Ruff lint plugin sub-table, such as `[tool.ruff.lint.flake8-bugbear]` or `[tool.ruff.lint.extend-per-file-ignores]`, stays consumer-owned and survives reconciliation unchanged. Through 1.11 the whole `[tool.ruff]` table was one owned unit, so any such sub-table blocked adoption with no option able to express it.
- The selected checker's `extraPaths` declares import-resolution roots: the layout root first, then each `additional_source_roots` entry in declared order. `include` selects which files are checked and sets no resolution order, so without this unit an editable installation of the repository's own distribution answers local imports first and strict mode reports them as untyped third-party imports when the distribution ships no `py.typed` marker. A repository that already ships that marker keeps working unchanged.
- `.editorconfig` properties are shared by stable identity with Markdown Tooling where their values are identical.
- VS Code extensions, settings, and task labels are independent JSONC units. Unrelated recommendations, settings, and tasks remain consumer-owned. Managed `files.exclude` entries cover only caches the selected toolchain produces; no MyPy cache key is emitted, because MyPy is not a selectable type checker. The package reserves the five base labels `check`, `fix`, `test`, `typecheck`, and `audit` for its managed tasks.
- `AGENTS.md` and `CLAUDE.md` receive only the delimiter-bounded `python-tooling` block, so Agent Handoff and other packages retain their own blocks.

Disabling the package removes only centrally locked Python Tooling units. Re-enabling reconstructs them from the selected immutable payload.

## Options

The closed option schema controls:

- the independently selected `1.0` or `1.1` consumer contract and supported Python versions;
- build backend (`uv_build`, `hatchling`, `setuptools`, or the non-installable `none` mode);
- `src`, flat, or `explicit` source layout — `explicit` owns no implicit root, so the declared collection roots and `additional_source_roots` entries are the entire gate. It is the mixed-monorepo mode: neither an invented `src` root nor a repository-wide `.` sweep. A repository that selects it must declare at least one `additional_source_roots` entry; an empty declaration fails option resolution rather than planning a gate over nothing.
- pytest collection roots as `pytest.test_paths` (default `["tests"]`) — they drive pytest `testpaths`, the checker `include`, Ruff `src`, and the VS Code `pytestArgs` in declared order, but never `coverage.run.source` or the checker `extraPaths` on their own;
- extra first-party source roots as `additional_source_roots` entries — plain strings join the checker `include`, checker `extraPaths`, Ruff `src`, and `coverage.run.source` values, while `{ path = "...", coverage = false }` tables keep a strictly-typed tooling root out of coverage measurement;
- Ruff line length, whether that limit is enforced on prose (`ruff.enforce_line_length`), plus additive include, select, and ignore lists, and the scoped `ruff.extend_per_file_ignores` table;
- coverage omission paths;
- BasedPyright or Pyright, including checking mode;
- the mandatory pytest coverage floor;
- pip-audit vulnerability exceptions;
- workflow ownership, CI triggers, performance tests, VS Code format-on-save behavior, the closed `vscode.task_prefix` choice (`""` or `"python: "`), and bounded agent instruction detail;
- the `runner_labels` runner selection for the managed Check workflow.

`runner_labels` (1.15) selects the runner pool the managed Check job requests. While the option is empty — the default — the job renders `runs-on: ubuntu-latest`, so a 1.14 consumer who sets nothing re-renders byte-for-byte identical bytes. A non-empty selection renders the labels as a YAML block sequence under `runs-on:`, and GitHub then allocates only a runner carrying every listed label. Labels are limited to letters, digits, `.`, `_`, and `-`, and must start with a letter or digit.

Unlike the Markdown Tooling, Markdown Frontmatter, and Project Specification packages, this workflow is self-contained: it declares its own job rather than calling a reusable workflow, so the selection is templated straight into `runs-on` and reaches every trigger. There is no `workflow_call`-only path and therefore no event on which the labels are silently ignored. The option is inert while `workflow_ownership` is `consumer-owned`, because the package then renders no workflow at all; pin `runs-on` in the owned file instead.

`ruff.enforce_line_length` (1.15) decides whether the declared `line-length` is a gate. The default, `false`, renders `ignore = ["E501"]` and reproduces the 1.14 bytes: `ruff format` rewraps code to the limit but never reflows a comment, a docstring, or a string literal, so an always-selected E501 would fail on prose the formatter itself refuses to fix. Setting it to `true` renders an empty `ignore`, and the baseline `E` selector then enforces the declared limit on every line, prose included. The option exists because Ruff resolves `ignore` after `extend-select`: while the exclusion is rendered, no `ruff.extend_select` entry can reach E501, so there is no consumer-side route to a hard limit.

The default empty task prefix preserves the 1.13 labels and bytes. Selecting `"python: "` changes only the five labels; command strings, groups, problem matchers, and all other task fields remain unchanged. No other prefix spelling is accepted.

`workflow_ownership = "managed"` materializes, verifies, locks, and removes `.github/workflows/check.yml` with the package lifecycle. `workflow_ownership = "consumer-owned"` leaves that path outside package actions, verification, and lock state; the consumer is responsible for its validity and maintenance. The `ci.*` options remain schema-valid in consumer-owned mode but affect only a managed workflow, so they are inert while ownership remains with the consumer. Returning to managed ownership is a separate acquisition boundary and conflicts with unequal consumer bytes rather than overwriting them. `script_ownership` applies the same contract to `scripts/check.py`: managed mode renders, verifies, and locks the enforcement script, while consumer-owned mode leaves the path outside package actions so a customized gate survives migration and reconciliation.

The type-checker choice fans out to dependency declarations, both Pyright-family configuration tables, the managed CI workflow, local check script, VS Code settings/tasks, and agent instructions. The inactive checker table and editor setting are explicitly set to `off`; the selected checker is the only dependency and command in the gate. The BasedPyright extension recommendation remains a reversible, package-owned editor aid even when the Pyright CLI is selected; the editor authority follows the selected settings, not the dormant recommendation.

Ruff `extend_include`, `extend_select`, and `extend_ignore`, plus coverage `omit`, are closed additive lists. The three Ruff lists render their keys unconditionally, as empty arrays when the option is empty, because each is a separately owned key; an empty array is inert in Ruff. Coverage `omit` still emits no key when empty. Explicit `extend_ignore` entries may suppress baseline-selected rules when that is reviewed repository intent.

`ruff.extend_per_file_ignores` (1.13) exempts named rules for a path glob instead of for the whole repository. It is a table of Ruff glob to rule list:

```toml
[standards.python-tooling.config.ruff.extend_per_file_ignores]
"tests/**/*.py" = ["ANN401"]
"scripts/*.py" = ["T201"]
```

The entries extend rather than replace: the rendered `[tool.ruff.lint.per-file-ignores]` table keeps every package default — `"tests/**/*.py" = ["S101"]` becomes `["S101", "ANN401"]` above — and a glob the package does not ship is added beside it. Consumer globs and rules render in sorted order, so the unit does not depend on the order the option was written in. Removing an entry restores exactly the package default; removing the whole option renders the 1.12 bytes. Use it where `extend_ignore` would be wrong, such as permitting `Any` at dynamic test boundaries while `ANN401` still governs shipped code.

Ruff's own `[tool.ruff.lint.extend-per-file-ignores]` table is unaffected and stays consumer-owned, as the ownership rule above states. Both routes remain valid and Ruff unions them; prefer the option, because a package-rendered value is validated, digested, and reconciled.

`ruff.extend_exclude` scopes Ruff alone and deliberately does not flow into the type checker. The two tools do not share an exclusion contract: BasedPyright and Pyright carry their own default `exclude` list, so a package-rendered `exclude` key would have to be rendered unconditionally — key-level units cannot appear only when an option is non-empty — and an unconditional empty list would silently replace those defaults for every consumer. Type-checker exclusion is therefore consumer-owned: write `exclude` directly in `[tool.basedpyright]` (or `[tool.pyright]`). It is an undeclared key, so reconciliation preserves it and reports no drift, exactly as it does for `extraPaths` before 1.11 and for pytest `pythonpath`.

## Build backends

Use `uv_build` for pure-Python packages unless project constraints require another backend. The selected backend owns the complete `[build-system]` table. `build_backend = "none"` declares a deliberately non-installable repository and omits that table without removing any development tooling. See [Build Backend Guidance](build-backend.md).

`uv_build` renders `requires = ["uv_build>=0.11,<1.0"]` and therefore requires uv 0.11 or later. uv compares the running uv against that requirement to decide whether it may build through its own in-process backend, and warns when the version falls outside it. The bound spans the whole pre-1.0 `uv_build` series on purpose: a released payload is immutable, so a bound narrowed to one uv minor — as 1.15 and earlier shipped — turns into compatibility noise for every adopter as soon as uv publishes its next minor (1.16, issue #182). Upgrading from 1.15 or earlier rewrites the `[build-system]` table once; the unit identity and its managed policy are unchanged, so no migration edge is involved.

## Verification gate

The rendered gate runs the mandatory commands in this order:

1. Ruff format check.
2. Ruff lint.
3. Selected type checker.
4. pytest under coverage, followed by the coverage report.
5. Optional performance tests when `ci.performance = true`.
6. pip-audit.

The rendered `scripts/check.py` resolves its arguments before it runs anything: `-h` or `--help` prints usage and exits 0, any other argument is a usage error that exits 2, and a bare invocation runs the ordered gate and stops at the first failure. The script omits `from __future__ import annotations` for Python 3.14 and later, matching the Python Coding companion's annotation rule; targets below 3.14 keep the predecessor rendering.

Managed CI-disabled configurations retain an explicit manual-only workflow so the selected gate remains inspectable without running automatically.

## Migration

The automatic V4 migration recognizes the legacy `python_tooling.version`, Python Tooling option values, and byte-identical files shipped by the V1 copy-adopt bundle. It preserves the consumer contract selector independently from the selected 1.16 package payload; both supported contract values render the same toolchain because the selector remains metadata-only. Known whole-file agent and VS Code content is retired into bounded contributions; shared EditorConfig and extension files are preserved while their package-owned units enter the central lock.

Fresh 1.16 adoption defaults `ci.performance` to false.

An exact known workflow migrates according to the selected ownership. An unknown workflow remains blocking in managed mode. In consumer-owned mode, the explicit raw legacy intent authorizes only preservation of that single whole-file path; the migration preview labels it consumer-owned, preserved, and not semantically validated, and the control plane creates no workflow action, unit, or lock entry.

Instruction and shared configuration targets (`CLAUDE.md`, `AGENTS.md`, `.editorconfig`, `.vscode/extensions.json`, `.vscode/settings.json`, `.vscode/tasks.json`) declare `unknown_content_disposition = "preserve"`: consumer-modified content at those paths is preserved instead of blocking, the preview reports a `CP-MIGRATION-BOUNDED-TAKEOVER` warning per file, and steady-state reconciliation manages only the bounded package-owned units inside the preserved file. Superseded V1 boilerplate inside a preserved file is left for the consumer to remove. Modified `scripts/check.py`, `.python-version`, or a modified managed workflow remains blocking.

The selected V5 package payload and the `.standards/` control plane are the sole package authority; the retired V1 root family manifest has no remaining authority.

## Update process

Payload 1.16 becomes immutable after publication. Behavioral or option changes require a new package version, new payload digest, catalog entry, migration edge where necessary, and source plus extracted-wheel compatibility evidence.
