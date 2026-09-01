# Python Tooling SSOT Standard

This is the Catalog 5 family landing page for the active consumer package `python-tooling@1.18`. The immutable versioned payload, not this mutable landing page, defines the selected standard.

## Current authority

- [Python Tooling 1.18 standard](versions/1.18/README.md) — normative toolchain, configuration, ownership, and verification contract
- [Python Tooling 1.18 adoption guide](versions/1.18/adopt.md) — complete options, outputs, migration, and recovery
- [Current family adoption guide](adopt.md) — concise enable/reconcile workflow
- [Python Tooling 1.18 agent summary](versions/1.18/agent-summary.md) — compact authority rules
- [Family index](standard.toml) — indexed payload and digest

## Use this standard when

Use Python Tooling for the uv/uv_build `src/` baseline, Ruff formatting and linting, BasedPyright strict checking, pytest with coverage.py, pip-audit, CI, VS Code, and bounded agent instructions. The control plane composes only declared package-owned tables, properties, and blocks and preserves unrelated consumer configuration.

Package 1.18 adds no option and renders no byte differently. It corrects the adoption guide's self-contradictory account of `build_backend = "none"` and stops `PT-PROJECT-METADATA` from short-circuiting on that selection, so the guard now evaluates for every adoption (issue [#204](https://github.com/L3DigitalNet/project-standards/issues/204)). It also documents the two adoption traps behind issues [#205](https://github.com/L3DigitalNet/project-standards/issues/205) and [#206](https://github.com/L3DigitalNet/project-standards/issues/206): declared source roots scope the checkers without making a subproject package importable, and any `[tool.pytest.ini_options]` key outside `minversion`/`testpaths`/`addopts`/`markers` is consumer-owned and may be written straight into the managed table.

**Behavior change on upgrade.** A `build_backend = "none"` consumer with no `[project]` table now blocks at `reconcile --check` with `PT-PROJECT-METADATA` where 1.17 reported nothing. That repository was already failing at the required `uv lock` step — uv refuses any `pyproject.toml` without a `[project]` table, whatever the backend — so 1.18 surfaces an existing failure earlier rather than breaking a working adoption. Add the PEP 621 metadata and leave `[build-system]` absent; uv then treats the repository as `source = { virtual = "." }`.

The predecessor 1.17 adds no option. It advances the `astral-sh/setup-uv` action pinned in the rendered CI workflow to `v10.0.1` (issue #201), which is the only byte that moves. `enable-cache` stays an explicit `true` rather than `auto` — v10 makes `auto` disable the cache for `release`, tag pushes, `pull_request_target`, and `workflow_run` — so the gate keeps the caching behavior it was measured under, and none of those four events triggers this workflow anyway. Reconciling from 1.16 or earlier rewrites the workflow file.

The predecessor 1.16 adds no option either. It corrects the rendered `[build-system]` requirement for `build_backend = "uv_build"` to `uv_build>=0.11,<1.0`, so a current uv no longer warns that its own version falls outside the pin, and states uv 0.11 as the adoption prerequisite. Reconciling from 1.15 or earlier rewrites that one table.

The predecessor 1.15 retains the scoped `ruff.extend_per_file_ignores` table and the closed `vscode.task_prefix` choice, and adds two opt-in options whose defaults render exactly the 1.14 bytes: `runner_labels` selects the runner pool the managed Check job requests, templating the job's own `runs-on`; `ruff.enforce_line_length` makes the declared `line_length` a real gate by dropping `E501` from the rendered ignore list, which no consumer could do before because Ruff resolves `ignore` after `extend-select`.

## Adopt

```bash
project-standards standards enable python-tooling --version 1.18
project-standards reconcile
project-standards reconcile --apply
uv lock
python scripts/check.py
```

Review [adopt.md](adopt.md) before applying. Commit unified config, catalog, lock, dependency lock, and reconciled outputs together.

## Released-version errata

The immutable 1.1 through 1.10 READMEs state that consumer `extraPaths` settings remain outside package ownership. That was accurate when they shipped. Python Tooling 1.11 declares the selected checker's `extraPaths` as a managed unit (issue #89) so local source resolves before an editable installation of the same distribution; a repository that owned that key moves its roots into `additional_source_roots`.

The immutable 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, and 1.10 READMEs contain wording written before the atomic Catalog 5 and Project Standards v5.0.0 release. Treat their statement that the V1 root remains authoritative until that release as release-time history. Catalog 5 now selects `python-tooling@1.18`; the immutable payload bytes remain unchanged.

The immutable 1.1 through 1.9 READMEs name Python Coding 0.5 as the reference-only companion. That literal was written before Python Coding 0.6 shipped and was never refreshed in the released payloads. The current companion is Python Coding 0.6; treat the earlier literal as release-time history, not as a statement that 0.5 is the compatible version. Python Tooling 1.10 and every later version name 0.6 directly.

In the immutable 1.4 README, the statement that a modified `scripts/check.py` remains blocking applies only while `script_ownership = "managed"`. Setting `script_ownership = "consumer-owned"` preserves the customized script and leaves it outside reconciliation, verification, and lock state. `.python-version` and modified managed outputs retain the stated blocking behavior.

## Legacy boundary

The unversioned copy-adopt toolchain, `project-standards adopt python-tooling`, and `.project-standards.yml` fragments are migration evidence only. They do not define current Catalog 5 composition or ownership.
