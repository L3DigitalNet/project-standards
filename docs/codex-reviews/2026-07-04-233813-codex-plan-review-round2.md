### Executive summary

Claude Code’s revision resolves the parser/JSON handling, self-validation parse mapping, file-mode preservation, and JSON code-slug coverage findings from round 1. One blocking executability issue remains: several pasted test snippets still instruct “append” imports below existing code, which will likely fail Ruff `E402` under this repo’s strict gate if followed literally.

New internet research was performed against official Python 3.14 docs for the filesystem/parser assumptions. One new non-blocking cleanup issue was found in the write primitive: it no longer fully mirrors the existing `adopt/engine._atomic_write` interruption cleanup behavior.

### Verdict

Needs major correction before execution

### Audit loop status

* Audit type: Follow-up audit
* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-07-04-project-spec-tooling-spec2.md
* Prior audit issue count: 5
* Resolved issue count: 4
* Still open issue count: 0
* Partially resolved issue count: 1
* New issue count: 1
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

I re-read the revised plan, compared it to the round-1 ledger, and rechecked the relevant repository evidence in `src/project_standards/specs/cli.py`, `config.py`, `registry.py`, bundled templates, `adopt/engine.py`, `pyproject.toml`, the approved design spec, and current git state.

I retested the prior assumptions around argparse failure routing, strict Ruff/BasedPyright cleanliness, self-validation parse failures, atomic write mode handling, and full JSON slug coverage. I also attacked the revised write cleanup path against the existing repo atomic-write implementation.

I did not run pytest, Ruff, BasedPyright, coverage, `uv build`, or `pip-audit` because those commands may write caches/build artifacts or otherwise exceed read-only audit mode.

### Prior findings status

#### CR-001: Parser failures bypass the `--json` and `NewError` contract

* Previous severity: High
* Current status: Resolved
* Evidence: The revised plan adds `_NewArgParser.error()` that raises `_ArgparseError` instead of letting argparse exit, parses inside `_run_new`’s `try`, maps parser errors to `NewError("usage", ...)`, and adds JSON parser-failure tests for missing `--profile`, invalid choices, and unknown flags at plan lines 736-743, 824-828, and 660-679.
* Remaining action for Claude Code: Keep these tests and verify both in-process `run([...])` and subprocess behavior after implementation.

#### CR-002: The pasted snippets will not pass the repo’s strict Ruff/BasedPyright gate

* Previous severity: High
* Current status: Partially resolved
* Evidence: The plan fixes several prior strict-gate problems: it adds `re`/`random`, gives `_cfg` a `-> SpecConfig` annotation, removes unused-import patterns, and replaces the untyped RNG fake with real `random.Random` usage. However, multiple snippets still say `# append to ...` and include module-level imports inside appended blocks, such as `from project_standards.specs.commands.new import SpecIdExhausted, mint_spec_id` at lines 183-185, scaffold imports at lines 407-412, `import stat` at lines 933-934, and Task 7 imports at lines 1137-1139. This repo’s Ruff config selects `E` rules at `pyproject.toml` lines 44-46, so literal below-code imports risk `E402` and import-sort failures.
* Remaining action for Claude Code: Revise every task that introduces imports to explicitly merge them into the file’s top import block, including project imports and `stat`, not just `random`, `re`, `date`, and `os`.

#### CR-003: Self-validation parse failures can still escape as exit 1 and non-JSON

* Previous severity: Medium
* Current status: Resolved
* Evidence: The revised plan wraps `parse_document("<new>", text)` and maps `SpecParseError` to `NewError("self_validation_failed", ...)` at lines 842-845. It also adds a monkeypatched malformed-scaffold JSON test at lines 1227-1239.
* Remaining action for Claude Code: Verify the implemented path returns exit 2 and one JSON object under `--json`.

#### CR-004: Atomic writes will likely leave generated files with `mkstemp` permissions

* Previous severity: Medium
* Current status: Resolved
* Evidence: The revised write implementation preserves existing target mode on overwrite and applies `0o666 & ~umask` for new files at lines 1072-1081, with tests at lines 991-1008. This matches the existing adopt engine’s documented mode behavior at `src/project_standards/adopt/engine.py` lines 202-204.
* Remaining action for Claude Code: Run the mode tests on Linux after implementation.

#### CR-005: Validation does not actually prove every frozen JSON code slug

* Previous severity: Medium
* Current status: Resolved
* Evidence: Task 7 now adds explicit JSON code tests for `usage`, `flag_conflict`, `bad_id`, `bad_field_value`, `config_error`, `id_collision`, `id_exhausted`, `self_validation_failed`, `exists`, `not_regular_file`, `mkdir_failed`, `symlinked_parent`, and `write_failed` at lines 1122-1261. The self-review maps this to the frozen slug set at line 1342.
* Remaining action for Claude Code: Ensure the tests assert exactly one stdout JSON object and no stray stdout for each slug.

### New blocking issues

None found.

### New non-blocking issues

#### CR-NEW-001: Write cleanup no longer fully mirrors the repo’s existing interruption cleanup

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Compare the proposed “mirrors `adopt/engine._atomic_write`” safety claim against the actual existing atomic-write implementation.
* Plan reference: Lines 927-928 claim `_write_new_file` mirrors `adopt/engine._atomic_write`; lines 1068-1088 create a temp file and clean it only in `except OSError`; line 1341 repeats the mode/write-safety mirror claim.
* Finding: The revised `_write_new_file` catches `OSError` and removes the temp file, but unlike `adopt/engine._atomic_write`, it does not catch `BaseException` for interruption or unexpected non-`OSError` failures after `mkstemp`. A `KeyboardInterrupt` or unexpected exception during/after opening the temp file can leave `.spec-new-*.tmp` behind.
* Repository evidence: `src/project_standards/adopt/engine.py` lines 228-235 catches both `OSError` and `BaseException` and unlinks the temp file in both paths. The plan’s proposed implementation at lines 1085-1088 only handles `OSError`.
* External research evidence: Not applicable.
* Why it matters: This does not corrupt the destination file, but it weakens the plan’s “mirrors adopt engine” claim and leaves a realistic cleanup gap in the new writer’s failure-mode story.
* Recommended action for Claude Code: Add a `BaseException` cleanup branch matching `adopt/engine._atomic_write`, then re-raise.
* Suggested validation: Add a test that forces `KeyboardInterrupt` or another non-`OSError` after temp creation and asserts the temp file is removed and the destination is untouched.

### Regressions

None found.

### Internet research performed

* Source name: Python 3.14 argparse documentation
* URL: https://docs.python.org/3.14/library/argparse.html
* Access date: 2026-07-05
* What it was used to verify: Current `ArgumentParser` default exit behavior and parser customization assumptions.
* Relevant conclusion: `ArgumentParser` defaults to `exit_on_error=True`; overriding `error()` is a valid way for the plan to avoid default `sys.exit` on parser errors.

* Source name: Python 3.14 tempfile documentation
* URL: https://docs.python.org/3.14/library/tempfile.html#tempfile.mkstemp
* Access date: 2026-07-05
* What it was used to verify: `mkstemp` permission and cleanup assumptions.
* Relevant conclusion: `mkstemp` creates secure owner-only temp files and the caller is responsible for deletion.

* Source name: Python 3.14 os documentation
* URL: https://docs.python.org/3.14/library/os.html#os.replace
* Access date: 2026-07-05
* What it was used to verify: Atomic replacement behavior.
* Relevant conclusion: `os.replace` silently replaces an existing file when permitted and successful replacement is atomic on POSIX.

* Source name: Python 3.14 pathlib documentation
* URL: https://docs.python.org/3.14/library/pathlib.html#pathlib.Path.is_symlink
* Access date: 2026-07-05
* What it was used to verify: Symlink detection assumptions.
* Relevant conclusion: `Path.is_symlink()` returns true for symlinks, including broken symlinks.

### Read-only validation performed

* `git status --short`: established the plan and design spec are modified, with one untracked round-1 review artifact.
* `git branch --show-current`: established the repo is on `testing`.
* `git log --oneline -n 10`: established the latest committed baseline is the spec #2 implementation plan commit.
* `nl -ba docs/superpowers/plans/2026-07-04-project-spec-tooling-spec2.md`: inspected the revised plan line-by-line for prior findings and new failure modes.
* `git diff -- docs/superpowers/plans/2026-07-04-project-spec-tooling-spec2.md`: confirmed the plan’s round-2 corrections relative to the committed version.
* `nl -ba src/project_standards/specs/cli.py`, `config.py`, `registry.py`, and bundled templates: confirmed current command dispatch, parser behavior, discovery behavior, template keys, and tier file names.
* `nl -ba src/project_standards/adopt/engine.py`: compared the proposed atomic-write behavior to the repo’s existing permission and cleanup implementation.
* `nl -ba pyproject.toml`: confirmed Ruff selects `E` rules, BasedPyright is strict, and the Python/tooling gates match the plan.
* `nl -ba docs/superpowers/specs/2026-07-04-project-spec-tooling-spec2-design.md`: checked the plan against the approved design contract.
* Official Python docs listed above: verified current external assumptions for argparse, tempfile, os.replace, and pathlib symlink behavior.

### Recommended implementation validation

* Run only after implementation: `uv run ruff check tests/test_spec_new.py tests/test_spec_new_cli.py`
* Run only after implementation: `uv run basedpyright tests/test_spec_new.py tests/test_spec_new_cli.py`
* Run only after implementation: `uv run pytest tests/test_spec_new.py tests/test_spec_new_discovery.py tests/test_spec_new_cli.py -v`
* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest && uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`
* Run only after implementation: add/execute a non-`OSError` interruption cleanup test for `_write_new_file`.

### Final recommendation

Claude Code should revise the plan using the findings above

### Review ledger for next loop

* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-07-04-project-spec-tooling-spec2.md
* Audit round: 2
* Open issue IDs: CR-002, CR-NEW-001
* Resolved issue IDs: CR-001, CR-003, CR-004, CR-005
* Superseded issue IDs: None
* Significant findings remaining: Yes
* Next audit should focus on: top-of-file import placement for every appended test snippet, strict Ruff/BasedPyright executability, and BaseException temp-file cleanup parity with `adopt/engine._atomic_write`.

