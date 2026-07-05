### Executive summary

The implementation plan needs correction before Claude Code executes it. The plan is broadly aligned with the repository’s current `spec` tooling shape, but it has two blocking execution risks: parser-level failures bypass the planned `NewError`/`--json` contract, and the pasted test/code snippets will not pass the repo’s Ruff + BasedPyright strict gate as written.

Internet research was required for current Python `argparse`, `os.replace`, `pathlib`, `tempfile`, and PyYAML behavior. The strongest stale-assumption finding is that default `argparse` error handling exits before the plan’s JSON/error wrapper can run.

### Verdict

Needs major correction before execution

### Audit loop status

* Audit type: First audit
* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-07-04-project-spec-tooling-spec2.md
* Significant findings remaining: Yes
* Blocking issue count: 2
* Non-blocking issue count: 3

### What the plan gets right

* It correctly identifies the existing nested `project-standards spec` dispatch in `src/project_standards/cli.py` and `_VERBS` dispatch in `src/project_standards/specs/cli.py`.
* It matches the repo’s Python 3.14, Ruff, BasedPyright strict, coverage, and PyYAML dependency posture.
* The proposed pure-core/impure-shell split is consistent with the existing `specs.commands.*` modules.
* The write model uses the right general primitives: temp file in the destination directory plus `os.replace`, with explicit refusal for symlink targets and symlinked parents.
* The plan correctly recognizes that `collect_spec_paths` intentionally treats an empty corpus as `DiscoveryError`, so `new` needs a separate tolerant discovery path.

### Adversarial review performed

I inventoried and checked the plan’s material claims around files, module boundaries, command wiring, config discovery, template usage, ID minting, error codes, JSON output, write safety, validation gates, and static type/lint compatibility.

I falsified the plan against current repository evidence in `src/project_standards/specs/cli.py`, `config.py`, `document.py`, `registry.py`, bundled templates, existing tests, `pyproject.toml`, `.project-standards.yml`, and the design spec. I also attacked the validation plan for false positives: parser failures, missing JSON-code coverage, strict type checker failures, and file-permission side effects.

I did not run pytest, Ruff, BasedPyright, coverage, or `uv run` validation because those commands can write caches/artifacts or depend on environment mutation. They are listed under implementation validation instead.

### Blocking issues

#### CR-001: Parser failures bypass the `--json` and `NewError` contract

* Severity: High
* Status: Confirmed
* Adversarial angle: Test whether “`--json` on every outcome” survives failures raised by `argparse` before `_run_new` enters its `try` block.
* Plan reference: Lines 15-19 require no exit 1, no traceback, and JSON on every `--json` outcome; lines 756-768 parse arguments before the `try`; lines 810-811 catch only `NewError`; design lines 181-194 require bad profile and all failures to be exit 2 / JSON-capable.
* Finding: The plan’s `_run_new` calls `ap.parse_args(argv)` outside the `try`, and uses `required=True` plus `choices=...`. Missing `--profile`, bad `--profile`, unknown flags, and malformed argparse-level usage will call argparse’s default exit path before `NewError` handling can emit the required JSON object. In in-process tests this raises `SystemExit`; in the CLI it exits 2 with argparse stderr, not the frozen JSON payload.
* Repository evidence: Current `src/project_standards/specs/cli.py` uses `parse_args` in each subcommand and `run()` only catches `ConfigError` and `SpecParseError`, returning 2 or 1 respectively at lines 151-158. The plan’s proposed parser mirrors that pattern but claims a stronger JSON contract for `new`.
* External research evidence: Python 3.14 `argparse.ArgumentParser` defaults `exit_on_error=True`; invalid argument lists normally print to stderr and exit with status 2. `ArgumentParser.error()` prints usage/message to stderr and terminates with status 2. Source: https://docs.python.org/3.14/library/argparse.html, accessed 2026-07-05.
* Why it matters: The most basic bad invocations can violate invariant I7 and the frozen error-code contract. Automation using `--json` would see no JSON object for parser failures.
* Recommended action for Claude Code: Revise the plan to route parser errors through the same JSON-aware failure mechanism. Options include a custom `ArgumentParser` that raises `NewError`, `exit_on_error=False` plus explicit handling, or a pre-parse wrapper that detects `--json` and converts parser failures without leaking normal argparse output. Define which frozen `code` slug covers parser-level failures.
* Suggested validation: Add tests for `run(["new", "--json", "--stdout"])`, bad profile, unknown flag, and missing required values, asserting return code 2, exactly one JSON object on stdout, and no `SystemExit`.

#### CR-002: The pasted snippets will not pass the repo’s strict Ruff/BasedPyright gate

* Severity: High
* Status: Confirmed
* Adversarial angle: Check whether the step-by-step pasted code can satisfy the plan’s own “every task ends green” gate.
* Plan reference: Lines 20 and 1071-1076 require the full gate; lines 186-198 use `re.match` in tests without importing `re`; lines 283-290 import `ConfigError` and define `_cfg` without a return annotation; line 871 imports `os` in tests without using it; lines 201-207 pass `_Fixed()` to `mint_spec_id` annotated as `random.Random`.
* Finding: The plan’s test snippets are not gate-clean as written. `re` is missing in `tests/test_spec_new.py`. `ConfigError` and `os` are unused imports. `_cfg` lacks a return annotation under strict typing. The `_Fixed` RNG stub is not a `random.Random`, so BasedPyright strict is likely to reject it unless the function accepts a structural protocol or the test uses a typed compatible fake.
* Repository evidence: `pyproject.toml` enables Ruff `F` rules, strict BasedPyright over `src` and `tests`, and fail-on-warnings at lines 44-61. Existing tests are typed and imported carefully.
* External research evidence: Not applicable.
* Why it matters: Claude Code following the plan literally will hit static gate failures unrelated to the feature behavior, forcing unplanned repair work and weakening the plan’s executability.
* Recommended action for Claude Code: Correct the snippets before implementation: import `re`; remove unused imports; add `_cfg(...) -> SpecConfig`; either type the RNG parameter with a small protocol (`choice(str) -> str`) or use a real `random.Random`/monkeypatchable subclass compatible with the annotation.
* Suggested validation: Run Ruff and BasedPyright after each task that adds tests, not only at the end.

### Non-blocking issues

#### CR-003: Self-validation parse failures can still escape as exit 1 and non-JSON

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Force the generated scaffold to be malformed and see whether it maps to the promised `self_validation_failed` JSON failure.
* Plan reference: Lines 15-19 require `new` never return 1 and define `self_validation_failed`; lines 782-789 call `validate_document(parse_document("<new>", text), load_registry())` without catching `SpecParseError`.
* Finding: If `scaffold` or a future bundled template produces malformed frontmatter, `parse_document("<new>", text)` raises `SpecParseError`, which is not caught by `_run_new`. The existing top-level `run()` catches `SpecParseError` as exit 1, not exit 2, and it does not emit the `new` JSON object.
* Repository evidence: `src/project_standards/specs/cli.py` catches `SpecParseError` and returns 1 at lines 156-158. `parse_document` raises `SpecParseError` for malformed frontmatter in `src/project_standards/specs/document.py`.
* External research evidence: Not applicable.
* Why it matters: The fail-closed self-validation path is supposed to protect against invalid generated output. As written, one class of invalid generated output bypasses the planned error-code and JSON contract.
* Recommended action for Claude Code: Wrap `parse_document` in the self-validation block and convert `SpecParseError` into `NewError("self_validation_failed", ...)`, including a findings-style payload or documented error shape.
* Suggested validation: Add a unit/integration test that monkeypatches `scaffold` or template loading to return malformed frontmatter and asserts `--json` returns code `self_validation_failed` with exit 2.

#### CR-004: Atomic writes will likely leave generated files with `mkstemp` permissions

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Compare the proposed write primitive to existing repo atomic-write conventions and Python tempfile behavior.
* Plan reference: Lines 986-992 write via `tempfile.mkstemp`, `os.fdopen`, and `os.replace`; no chmod/mode preservation is specified.
* Finding: `mkstemp` creates files readable/writable only by the creating user. Replacing a target with that temp file can change an existing spec’s mode under `--force`, and new generated Markdown files may end up owner-only instead of normal umask-derived permissions.
* Repository evidence: Existing `src/project_standards/adopt/engine.py` explicitly avoids this problem: lines 202-204 state that overwrite should copy existing permissions and new files should use a umask-respecting `0o666` rather than `mkstemp`’s default `0600`.
* External research evidence: Python 3.14 `tempfile.mkstemp` docs state the created file is readable and writable only by the creating user; `os.replace` silently replaces an existing file and is atomic on success. Sources: https://docs.python.org/3.14/library/tempfile.html#tempfile.mkstemp and https://docs.python.org/3.14/library/os.html#os.replace, accessed 2026-07-05.
* Why it matters: This can create surprising permission drift for checked-in specs, especially on shared worktrees or when `--force` overwrites a previously normal Markdown file.
* Recommended action for Claude Code: Add the same mode handling used by the adopt engine: preserve target mode on overwrite; for new files, apply the process umask to `0o666` before replacement.
* Suggested validation: Add tests for new-file mode and forced-overwrite mode preservation, skipping or normalizing where platform semantics require.

#### CR-005: Validation does not actually prove every frozen JSON code slug

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Check whether the planned tests could pass while parts of the JSON contract are broken.
* Plan reference: Lines 19 and 1099 claim every frozen code slug is raised by some path; test snippets at lines 616-652 and 934-948 assert only success payloads and `bad_id`.
* Finding: The plan does not include JSON assertions for `exists`, `not_regular_file`, `symlinked_parent`, `id_collision`, `mkdir_failed`, `write_failed`, or `self_validation_failed`. Several write-safety tests check only return code 2, so `_emit_new_failure` could emit the wrong code or non-JSON output and still pass.
* Repository evidence: Existing spec CLI tests assert JSON shape for current commands, but no new test exists yet. The proposed tests are the source of truth for this implementation.
* External research evidence: Not applicable.
* Why it matters: The command’s JSON contract is explicitly a consumer automation surface. Weak assertions allow the implementation to pass while downstream agents/CI receive unstable or missing error codes.
* Recommended action for Claude Code: Add parametrized JSON failure tests for each frozen slug. For hard-to-trigger `mkdir_failed`/`write_failed`, use monkeypatching around `Path.mkdir`, `tempfile.mkstemp`, or `os.replace` rather than relying on host permissions.
* Suggested validation: Run `tests/test_spec_new_cli.py` with JSON failure matrix tests and verify stdout contains exactly one JSON object for every exit-2 path.

### Missing considerations

* Blocking: Parser-level JSON handling for argparse errors, including missing `--profile`, invalid profile, unknown flags, and `--help` behavior under `--json`.
* Blocking: Static gate correctness of the pasted tests under Ruff and strict BasedPyright before implementation begins.
* Non-blocking: Mode preservation/umask behavior for generated and overwritten files.
* Non-blocking: Self-validation should catch parse failures as `self_validation_failed`, not rely on the outer spec command’s generic parse handling.
* Non-blocking: JSON payload tests should cover every frozen `code` slug, not just `bad_id` and success payloads.
* Non-blocking: Template-read failures are not mapped to a clean `NewError`; Claude Code should decide whether to treat missing/corrupt bundled templates as `self_validation_failed` or another documented internal failure.

### Internet research performed

* Source name: Python 3.14 argparse documentation
* URL: https://docs.python.org/3.14/library/argparse.html
* Access date: 2026-07-05
* What it was used to verify: Default parser error/exit behavior and `exit_on_error`.
* Relevant conclusion: Default argparse errors exit with status 2 and print to stderr before the plan’s JSON wrapper can run.

* Source name: Python 3.14 os documentation
* URL: https://docs.python.org/3.14/library/os.html#os.replace
* Access date: 2026-07-05
* What it was used to verify: `os.replace` replacement and atomicity assumptions.
* Relevant conclusion: `os.replace` silently replaces existing files when permitted and is atomic on successful same-filesystem POSIX rename.

* Source name: Python 3.14 pathlib documentation
* URL: https://docs.python.org/3.14/library/pathlib.html#pathlib.Path.is_symlink
* Access date: 2026-07-05
* What it was used to verify: Symlink detection assumptions.
* Relevant conclusion: `Path.is_symlink()` returns true for symlinks, including broken symlinks, supporting the target/parent symlink refusal approach.

* Source name: Python 3.14 tempfile documentation
* URL: https://docs.python.org/3.14/library/tempfile.html#tempfile.mkstemp
* Access date: 2026-07-05
* What it was used to verify: Temp-file creation safety and permissions.
* Relevant conclusion: `mkstemp` creates secure temp files, but the file is readable/writable only by the creating user and must be deleted by the caller.

* Source name: PyYAML documentation
* URL: https://pyyaml.org/wiki/PyYAMLDocumentation
* Access date: 2026-07-05
* What it was used to verify: `safe_dump` availability and safe serialization behavior.
* Relevant conclusion: `safe_dump` serializes standard YAML tags and returns the produced stream when no stream is supplied; no conflict found with using PyYAML for scalar emission, but local tests still need to prove the exact scalar surface.

### Items Claude Code should verify before correcting the plan

* Verify the corrected parser strategy returns 2 rather than raising `SystemExit` for in-process `run([...])` tests.
* Verify `--json` parser failures produce exactly one stdout JSON object and no extra stdout.
* Verify Ruff and BasedPyright strict pass on the pasted test helpers before moving past each task.
* Verify malformed generated text maps to `self_validation_failed`, not the existing generic spec parse exit 1 path.
* Verify generated file modes for both new files and `--force` overwrites.
* Verify each frozen JSON `code` slug is exercised by at least one test.

### Suggested corrections for Claude Code's plan

* Replace default argparse failure handling for `new` with a JSON-aware parser/error path.
* Add tests for missing `--profile`, invalid profile, unknown option, and parser errors with `--json`.
* Fix the test snippets for strict static gates: add `import re`, remove unused imports, type `_cfg`, and make the RNG fake type-compatible.
* Catch `SpecParseError` during self-validation and map it to `NewError("self_validation_failed", ...)`.
* Add mode preservation/umask logic to `_write_new_file`, following the existing adopt engine pattern.
* Expand JSON failure tests to cover every frozen code slug.
* Add a test for template/scaffold malformed output and, if feasible, template-read failure handling.

### Read-only validation performed

* Inspected the plan at `/home/chris/projects/project-standards/docs/superpowers/plans/2026-07-04-project-spec-tooling-spec2.md`; established the proposed file changes, snippets, validation claims, and write model.
* Ran `git status --short`, `git branch --show-current`, and `git log --oneline -n 10`; established the repo is on branch `testing` and the plan/spec commits already exist.
* Ran `rg --files`; established the relevant source, tests, templates, specs, plans, and handoff files present in the repo.
* Inspected `src/project_standards/specs/cli.py`, `config.py`, `document.py`, `registry.py`, and `commands/validate.py`; established current command dispatch, error handling, discovery behavior, parsing, registry constants, and validation behavior.
* Inspected bundled spec templates; established the frontmatter keys, placeholders, H1 format, and profile-specific template files match the plan’s target.
* Inspected `pyproject.toml`; established Python 3.14, PyYAML, Ruff, strict BasedPyright, coverage, and pip-audit gates.
* Inspected existing spec CLI/config/validate tests; established current test style and existing exit-code behavior.
* Inspected `src/project_standards/adopt/engine.py`; established the repo already has an atomic-write pattern that preserves permissions and avoids `mkstemp`’s default mode drift.
* Attempted local no-write Python snippets to probe PyYAML behavior; the environment wrapper refused direct `python`/`python3` and required `uv run`, so no runtime PyYAML probe was used.
* Consulted official Python and PyYAML documentation listed above.

### Recommended implementation validation

* Run only after implementation: `uv run pytest tests/test_spec_new.py tests/test_spec_new_discovery.py tests/test_spec_new_cli.py -v`
* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest && uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`
* Run only after implementation: subprocess checks for `project-standards spec new --json` parser failures, verifying exit 2 and exactly one JSON object on stdout.
* Run only after implementation: mode checks for new file creation and `--force` overwrite preservation.

### Final recommendation

Claude Code should revise the plan using the findings above

### Review ledger for next loop

* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-07-04-project-spec-tooling-spec2.md
* Audit round: 1
* Open issue IDs: CR-001, CR-002, CR-003, CR-004, CR-005
* Resolved issue IDs: None
* Superseded issue IDs: None
* Significant findings remaining: Yes
* Next audit should focus on: parser/JSON error handling, strict Ruff/BasedPyright cleanliness of snippets, self-validation parse failure mapping, file mode preservation, and complete JSON code-slug test coverage.

