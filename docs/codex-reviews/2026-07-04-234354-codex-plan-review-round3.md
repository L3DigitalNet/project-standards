### Executive summary

Claude Code’s round-3 revision resolves the two remaining issues from round 2. The plan now gives explicit top-import instructions for the previously risky appended snippets, and the write path now includes `BaseException` cleanup plus an interruption regression test that matches the existing `adopt/engine._atomic_write` pattern.

New internet research was performed only to re-check the Python stdlib assumptions used by the corrected write/parser plan. No significant findings remain.

### Verdict

No significant findings remain

### Audit loop status

* Audit type: Follow-up audit
* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-07-04-project-spec-tooling-spec2.md
* Prior audit issue count: 6
* Resolved issue count: 6
* Still open issue count: 0
* Partially resolved issue count: 0
* New issue count: 0
* Regression count: 0
* Significant findings remaining: No

### Adversarial review performed

I re-read the current plan, rechecked the prior round-2 open ledger, and inspected the relevant repository evidence in `src/project_standards/specs/cli.py`, `config.py`, `registry.py`, `document.py`, `commands/validate.py`, `adopt/engine.py`, the bundled templates, `pyproject.toml`, the approved design spec, and current git state.

I retested the corrected import-placement instructions against Ruff/BasedPyright strictness, retested the atomic-write cleanup claim against the existing adopt implementation, re-attacked the JSON slug matrix for false positives, and checked whether the validation plan could pass while missing the prior failure modes.

I did not run pytest, Ruff, BasedPyright, coverage, `uv build`, `pip-audit`, or validator commands because this audit is read-only and those commands may write caches/build artifacts or otherwise exceed the allowed mode.

### Prior findings status

#### CR-001: Parser failures bypass the `--json` and `NewError` contract

* Previous severity: High
* Current status: Resolved
* Evidence: The plan still routes parser errors through `_NewArgParser.error()` into `_ArgparseError`, maps them to `NewError("usage", ...)`, and tests missing `--profile`, invalid `--profile`, and unknown flags with `--json` at plan lines 818-836 and 668-687.
* Remaining action for Claude Code: None beyond running the planned in-process and subprocess-equivalent validation after implementation.

#### CR-002: The pasted snippets will not pass the repo’s strict Ruff/BasedPyright gate

* Previous severity: High
* Current status: Resolved
* Evidence: The revised plan now explicitly tells implementers to merge imports into top import blocks for the affected test snippets at lines 182-192, 411-421, 940-947, and 1153-1159. Production snippets also now instruct top import placement for `new.py`, `config.py`, and Task 6 `cli.py` imports at lines 224-227, 345-348, 502-504, and 1048. The repo’s strict gates are confirmed in `pyproject.toml` lines 44-61.
* Remaining action for Claude Code: Keep import additions merged into existing sorted import blocks when implementing, then run the planned Ruff and BasedPyright gates.

#### CR-003: Self-validation parse failures can still escape as exit 1 and non-JSON

* Previous severity: Medium
* Current status: Resolved
* Evidence: The plan still catches `SpecParseError` around `parse_document("<new>", text)` and maps it to `NewError("self_validation_failed", ...)` at lines 848-854, with a malformed-scaffold JSON test at lines 1245-1257.
* Remaining action for Claude Code: None beyond executing the planned JSON failure-code tests.

#### CR-004: Atomic writes will likely leave generated files with `mkstemp` permissions

* Previous severity: Medium
* Current status: Resolved
* Evidence: The plan preserves existing mode on overwrite and applies `0o666 & ~umask` for new files at lines 1083-1092, with mode tests at lines 1002-1019. This matches the existing repository implementation in `src/project_standards/adopt/engine.py` lines 202-222.
* Remaining action for Claude Code: Run the mode tests on Linux after implementation.

#### CR-005: Validation does not actually prove every frozen JSON code slug

* Previous severity: Medium
* Current status: Resolved
* Evidence: Task 7 still covers every frozen JSON slug at lines 1167-1273, including forced paths for `id_exhausted`, `self_validation_failed`, and `write_failed`. The self-review maps the frozen slug set at line 1376.
* Remaining action for Claude Code: None beyond executing Task 7 and full-gate validation.

#### CR-NEW-001: Write cleanup no longer fully mirrors the repo’s existing interruption cleanup

* Previous severity: Medium
* Current status: Resolved
* Evidence: The revised `_write_new_file` now catches `BaseException`, unlinks the temp file, and re-raises at lines 1100-1105. Task 7 adds `test_write_cleanup_on_interruption`, monkeypatching `os.replace` to raise `KeyboardInterrupt` and asserting no temp or destination remains at lines 1276-1289. This matches `adopt/engine._atomic_write`, which catches `BaseException` and unlinks temp files at `src/project_standards/adopt/engine.py` lines 232-235.
* Remaining action for Claude Code: Run the new interruption cleanup test after implementation.

### New blocking issues

None found.

### New non-blocking issues

None found.

### Regressions

None found.

### Internet research performed

* Source name: Python 3.14 argparse documentation
* URL: https://docs.python.org/3.14/library/argparse.html
* Access date: 2026-07-05
* What it was used to verify: Current `ArgumentParser` defaults and parser customization assumptions.
* Relevant conclusion: `ArgumentParser` still defaults to `exit_on_error=True`, and long-option abbreviation remains enabled by default; overriding parser error handling remains the right approach for avoiding default `sys.exit` on parser errors.

* Source name: Python 3.14 tempfile documentation
* URL: https://docs.python.org/3.14/library/tempfile.html#tempfile.mkstemp
* Access date: 2026-07-05
* What it was used to verify: `mkstemp` file-handle, permissions, and cleanup assumptions.
* Relevant conclusion: `mkstemp` returns an open OS-level handle and path, creates the file securely, and leaves cleanup responsibility to the caller.

* Source name: Python 3.14 os documentation
* URL: https://docs.python.org/3.14/library/os.html#os.replace
* Access date: 2026-07-05
* What it was used to verify: Atomic replacement behavior.
* Relevant conclusion: `os.replace` replaces an existing file when permitted and successful replacement is atomic on POSIX.

* Source name: Python 3.14 pathlib documentation
* URL: https://docs.python.org/3.14/library/pathlib.html#pathlib.Path.is_symlink
* Access date: 2026-07-05
* What it was used to verify: Symlink detection assumptions.
* Relevant conclusion: `Path.is_symlink()` returns true for symlinks, including broken symlinks; `exists()` and `is_file()` follow symlinks by default.

### Read-only validation performed

* `git status --short`: confirmed the plan and design spec are modified, with prior review artifacts untracked.
* `git branch --show-current`: confirmed the repo is on `testing`.
* `git log --oneline -n 10`: confirmed the committed baseline includes the spec #2 implementation plan.
* `rg -n ... docs/superpowers/plans/2026-07-04-project-spec-tooling-spec2.md`: checked the revised plan for remaining append-import instructions, write cleanup changes, JSON slug coverage, and atomic-write claims.
* `nl -ba docs/superpowers/plans/2026-07-04-project-spec-tooling-spec2.md`: inspected the revised plan line-by-line around prior findings and the new Task 7 coverage.
* `git diff -- docs/superpowers/plans/2026-07-04-project-spec-tooling-spec2.md`: confirmed the round-3 corrections relative to the committed plan.
* `nl -ba src/project_standards/specs/cli.py`, `config.py`, `registry.py`, `document.py`, and `commands/validate.py`: confirmed current parser, dispatch, discovery, template, parse, and validation behavior the plan builds on.
* `nl -ba src/project_standards/adopt/engine.py`: confirmed the existing atomic write mode and `BaseException` cleanup behavior used as the comparison baseline.
* `nl -ba pyproject.toml`: confirmed Ruff selected rules and BasedPyright strict settings.
* `nl -ba docs/superpowers/specs/2026-07-04-project-spec-tooling-spec2-design.md`: checked the plan against the approved design contract.
* Official Python docs listed above: rechecked external stdlib assumptions for argparse, tempfile, `os.replace`, and symlink behavior.

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

### Final recommendation

No significant findings remain; the audit/fix loop can stop

### Review ledger for next loop

* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-07-04-project-spec-tooling-spec2.md
* Audit round: 3
* Open issue IDs: None
* Resolved issue IDs: CR-001, CR-002, CR-003, CR-004, CR-005, CR-NEW-001
* Superseded issue IDs: None
* Significant findings remaining: No
* Next audit should focus on: No further audit needed unless the plan changes materially before implementation.