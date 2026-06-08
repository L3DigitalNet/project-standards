### Executive summary

The implementation plan is not ready for Claude Code to execute as written. The overall architecture is aligned with the approved spec, but several mandatory safety and validation guarantees are not actually achieved by the proposed code/tests. Internet research was required for current `uv_build` and `uv run` behavior; it confirmed the package-data direction is plausible, but it also falsified one validation-test assumption about running `uv run` from a temporary consumer directory.

### Verdict

Needs major correction before execution

### Audit loop status

* Audit type: First audit
* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-06-08-adopt-cli.md
* Significant findings remaining: Yes
* Blocking issue count: 3
* Non-blocking issue count: 2

### What the plan gets right

The plan correctly keeps the existing `validate-frontmatter` entry point, uses bundled package data under `src/project_standards/`, preserves skip-if-exists behavior, treats fragments as report-only, avoids in-place TOML/YAML merging, and explicitly tests symlink destinations and wheel packaging. The proposed bundle set also matches the four released standards and correctly excludes `python-coding`.

### Adversarial review performed

I inventoried the plan’s claims about bundle paths, CLI behavior, exit codes, packaging, workflow caller rendering, validation tests, release/versioning, and handoff updates. I falsified those claims against the current repo files, the approved design spec, `pyproject.toml`, `.project-standards.yml`, the validator implementation, current standard docs, root config/workflow files, and official uv documentation.

I did not run tests, builds, `uv sync`, or packaging commands because this audit is read-only and those commands can write environments, caches, or build artifacts.

### Blocking issues

#### CR-001: Recoverable I/O failures can still escape as tracebacks

* Severity: High
* Status: Confirmed
* Adversarial angle: The plan promises deterministic exit code 1 for recoverable write failures, but the proposed code only catches part of the write path.
* Plan reference: `engine.py` `_atomic_write()` and `execute_plan()` in plan lines 995-1039; exit-code contract in spec lines 126-131.
* Finding: `_atomic_write()` calls `target.parent.mkdir(...)` and `tempfile.mkstemp(...)` before entering the `try` block, so permission errors, read-only filesystems, or temp-file creation failures can raise raw `OSError` instead of `WriteError`. `_render()` also calls `read_bytes()` outside any I/O error mapping. The plan’s tests inject only `os.replace` failure, leaving the stated permission-denied/unwritable cases unproved.
* Repository evidence: The plan states recoverable I/O failures should map to exit 1, while current proposed code only wraps file write and `os.replace` after temp creation. The approved spec explicitly includes “permission denied, unwritable `--dest`, partial-write failure” as exit 1 cases.
* External research evidence: Not applicable.
* Why it matters: The CLI safety contract says bad filesystem state must not produce tracebacks. A consumer running `adopt --force` in a partially unwritable repo could see an uncaught exception instead of the documented exit code/report.
* Recommended action for Claude Code: Wrap directory creation, temp-file creation, source reads, fragment reads, writes, and replace cleanup in explicit error handling that maps recoverable I/O to `WriteError`.
* Suggested validation: Add tests monkeypatching `Path.mkdir`, `tempfile.mkstemp`, source `read_bytes`, and `os.replace` to raise `OSError`; assert `main([...])` returns 1, stderr is clean, and existing destination contents are preserved.

#### CR-002: Adoption validation test is not executable as written

* Severity: High
* Status: Confirmed
* Adversarial angle: The plan’s integration validation can fail for reasons unrelated to the adopt implementation, so it does not prove the ADR/frontmatter safety claim.
* Plan reference: D1 test in plan lines 1357-1418; starter config in lines 359-384.
* Finding: The test writes `README.md` without frontmatter while the planned starter sets `required: true` and includes `README.md`, so the validator should reject that file. The test also runs `uv run validate-frontmatter` with `cwd=tmp_path`; official uv docs say project discovery is based on the current working directory, so this subprocess is outside the repo project environment unless a project/venv is discovered there. Finally, `import subprocess` is appended mid-file, which risks Ruff `E402` under the repo’s selected `E` rules.
* Repository evidence: The planned starter includes `README.md` and `required: true`. The validator loads `required` and `include` from config and validates included files; the schema requires frontmatter fields such as `schema_version`, `id`, `title`, `doc_type`, `created`, and `updated`. `pyproject.toml` selects Ruff `E` rules.
* External research evidence: Astral uv CLI docs state `uv run` discovers the project from the current working directory and uses a project environment only when used in a project: https://docs.astral.sh/uv/reference/cli/ (accessed 2026-06-08).
* Why it matters: The test can fail before it validates the intended ADR-template exclusion behavior. A plan that expects this to pass will stall implementation or invite weakening the starter config.
* Recommended action for Claude Code: Move imports to the top, give the fixture README valid frontmatter, and validate using the in-process `validate_frontmatter.main()` with `monkeypatch.chdir(tmp_path)` or a subprocess tied explicitly to the repo project environment.
* Suggested validation: Add one clean config-less fixture test that adopts `markdown-frontmatter adr`, writes a valid managed README, and asserts the validator returns 0; add a separate fixture proving an ADR template is excluded by `**/*.template.md`.

#### CR-003: Invalid-manifest and list error paths do not satisfy the no-traceback contract

* Severity: High
* Status: Confirmed
* Adversarial angle: The plan claims invalid manifests and missing prerequisites produce documented exit codes, but not every CLI path catches those errors.
* Plan reference: CLI `main()` in plan lines 1234-1298; build-plan collision code in lines 834-878; spec acceptance in lines 205-208.
* Finding: `main()` returns `_cmd_list(args.json)` before entering the `try/except AdoptError`, so `project-standards list` can traceback on `ManifestError` from missing/malformed bundle data. The owned-dest collision logic also indexes `by_key[key]` while checking a prior destination; if two owned artifacts target the same destination with different kinds, `by_key[key]` can be absent and raise `KeyError` instead of `UsageError`.
* Repository evidence: `_cmd_list()` calls `available_standards()` and `load_manifest()` directly. The approved spec requires invalid manifest cases to fail with the exit-code table and “never a traceback.”
* External research evidence: Not applicable.
* Why it matters: This is a packaged CLI. Broken or drifted bundle metadata should produce deterministic operator-facing errors, not stack traces, especially for `list`, which is the discovery command.
* Recommended action for Claude Code: Catch `AdoptError` around all subcommands that touch bundles, including `list`. Rewrite collision detection to check destination collisions independent of `(kind, dest)` lookup and add explicit malformed-manifest tests.
* Suggested validation: Add tests for `list` with a missing/malformed manifest, two owned artifacts sharing a destination, mixed `file`/`workflow-caller` same destination, and missing source files; assert documented exit codes and no traceback.

### Non-blocking issues

#### CR-004: `list --json` omits the spec’s stable `contract_version` field

* Severity: Medium
* Status: Confirmed
* Adversarial angle: The plan’s JSON output can pass its tests while failing the approved CLI schema.
* Plan reference: `_cmd_list()` in plan lines 1234-1249; spec acceptance in lines 205-206.
* Finding: The approved spec says `list --json` emits `{id, contract_version, artifacts: [...]}`. The plan emits only `{id, artifacts}` and the tests only assert artifact data. The plan also does not cross-check adoptable IDs against the bundled registry despite the spec’s drift-prevention requirement.
* Repository evidence: `src/project_standards/schemas/registry.json` contains known contract versions for frontmatter, ADR, python_tooling, and markdown_tooling; the plan’s list implementation does not read it.
* External research evidence: Not applicable.
* Why it matters: `list --json` is an API-shaped output. Omitting the version field makes downstream automation less stable and misses a cheap registry/bundle drift check.
* Recommended action for Claude Code: Add `contract_version` to the list output from the registry defaults and add a test that bundle IDs and registry standards stay aligned.
* Suggested validation: Assert `project-standards list --json` includes all four standards with `contract_version` and expected artifacts.

#### CR-005: Fragment reporting cannot represent multiple fragments for one target

* Severity: Medium
* Status: Confirmed
* Adversarial angle: The generic manifest engine is meant to scale by data, but the report data structure silently overwrites same-target fragments.
* Plan reference: `Report.fragments: dict[str, str]` and `execute_plan()` in plan lines 975-1027; `format_report()` in lines 1110-1119.
* Finding: `report.fragments[action.target] = ...` stores only one fragment per target. If two standards later contribute fragments to the same file, the later one overwrites the earlier one. The spec says fragments are grouped by target, not reduced to one fragment per target.
* Repository evidence: Current manifests happen to target different files (`pyproject.toml` and `.project-standards.yml`), but the manifest format is intentionally generic and future standards are data-driven.
* External research evidence: Not applicable.
* Why it matters: This can silently drop operator instructions while all current tests still pass.
* Recommended action for Claude Code: Store fragments as `dict[str, list[str]]` or a list of fragment records, and format every fragment under its target heading.
* Suggested validation: Add a unit test with two fragment actions sharing the same `target` and assert both snippets appear in the report.

### Missing considerations

* Blocking: permission-denied, `mkdir`, `mkstemp`, source-read, and fragment-read failures need explicit tests and exit-code assertions.
* Blocking: `list` should be covered by the same clean error boundary as `adopt`.
* Blocking: invalid manifest tests should include owned destination collision, missing source, unsafe source, unsafe destination, and mixed artifact kinds.
* Non-blocking: adoption matrix should include all four standards together, `--force`, real `--dry-run` no-write behavior, and `.vscode/settings.json`/`tasks.json` not written.
* Non-blocking: the pre-existing `.project-standards.yml` ADR case described in the spec needs an actual test proving the report includes the required `**/*.template.md` exclusion.
* Non-blocking: `list --json` should have a tested stable schema including `contract_version`.

### Internet research performed

* Source name: Astral uv build backend documentation
* URL: https://docs.astral.sh/uv/concepts/build-backend/
* Access date: 2026-06-08
* What it was used to verify: Whether package data under `src/project_standards/` is expected to be included in wheels with `uv_build`.
* Relevant conclusion: The module under the default `src/<module-name>/**` root is included in wheels, and the docs say small data files are usually stored in the module root. The plan’s package-data location is plausible, but the wheel-inspection test remains necessary.

* Source name: Astral uv CLI `uv run` documentation
* URL: https://docs.astral.sh/uv/reference/cli/
* Access date: 2026-06-08
* What it was used to verify: Whether `uv run validate-frontmatter` from a pytest `tmp_path` still uses this repo’s project environment.
* Relevant conclusion: `uv run` discovers the project from the current working directory; outside a project it uses a discovered venv/interpreter. The D1 subprocess is not a reliable way to invoke this repo’s validator from `tmp_path`.

### Items Claude Code should verify before correcting the plan

* Confirm whether `basedpyright` accepts the proposed `_cmd_list()` typing and `# type: ignore[assignment]`; prefer avoiding the ignore entirely.
* Confirm the exact `uv_build` wheel contents after adding bundles, but only after implementation.
* Confirm `importlib.metadata.version("project-standards")` works under `uv run pytest` before relying on `major_ref()` in unit tests.
* Confirm the generated markdown-frontmatter starter validates a realistic consumer fixture with valid frontmatter.
* Confirm the registry/bundle ID mapping is intentionally one-to-one for the four released standards.

### Suggested corrections for Claude Code's plan

* Expand I/O error handling so every recoverable filesystem failure returns exit 1 without traceback.
* Fix D1 validation tests: top-level imports, valid frontmatter fixture, and in-process or project-bound validator invocation.
* Wrap `list` in the same `AdoptError` boundary as `adopt`.
* Rewrite owned-destination collision detection and add malformed-manifest tests.
* Add `contract_version` to `list --json` and test registry/bundle alignment.
* Change fragment reporting to allow multiple snippets per target.
* Add missing acceptance tests for all-four adoption, `--force`, real dry-run no-write, pre-existing ADR config exclusion reporting, and excluded `.vscode/settings.json`/`tasks.json`.

### Read-only validation performed

* `pwd`, `git status --short`, `git branch --show-current`, `git log --oneline -n 10`: confirmed repo root, clean working tree, branch `testing`, and plan commit present.
* Inspected `docs/handoff/state.md`, `AGENTS.md`, and `docs/handoff/conventions.md`: confirmed repo session rules and validation gates.
* Inspected the full plan file: inventoried proposed files, code, tests, commands, commits, and release steps.
* `rg --files`: confirmed current repo structure and absence of existing `adopt` implementation.
* Inspected `pyproject.toml`, `.project-standards.yml`, `registry.py`, `validate_frontmatter.py`, schema JSON, root workflows/configs, and relevant standard docs/templates.
* Inspected approved spec `docs/superpowers/specs/2026-06-08-adopt-cli-design.md`: compared plan against CLI, safety, testing, and acceptance contracts.
* `git diff --stat` and `git diff --check`: confirmed no current local diff and no existing whitespace diff to account for.
* Official uv documentation lookup: verified current external assumptions for wheel inclusion and `uv run` project discovery.

### Recommended implementation validation

* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest`
* Run only after implementation: `uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`
* Run only after implementation: `uv run pytest tests/test_adopt_manifest.py tests/test_adopt_engine.py tests/test_adopt_safety.py tests/test_adopt_cli.py tests/test_adopt_dogfood.py tests/test_adopt_packaging.py -v`
* Run only after implementation: build and inspect a wheel in a temp directory, then install/run the CLI from that wheel as the plan describes.

### Final recommendation

Claude Code should revise the plan using the findings above

### Review ledger for next loop

* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-06-08-adopt-cli.md
* Audit round: 1
* Open issue IDs: CR-001, CR-002, CR-003, CR-004, CR-005
* Resolved issue IDs: None
* Superseded issue IDs: None
* Significant findings remaining: Yes
* Next audit should focus on: I/O error mapping, D1 validation test viability, invalid-manifest/list CLI error handling, list JSON contract/registry drift, and multi-fragment reporting.