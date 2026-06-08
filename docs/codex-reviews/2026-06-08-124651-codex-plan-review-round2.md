### Executive summary

Claude Code’s revisions fixed the multi-fragment report model and most of the original I/O/list error-boundary problems, but the plan is still not ready to execute. A new blocking safety defect remains in the proposed destination handling: `Path.resolve()` is used before the symlink check, so the engine can write through a symlink instead of reporting it as skipped. Prior registry-drift and validation false-positive concerns are also only partially resolved.

New internet research was required for Python `pathlib` symlink-resolution behavior.

### Verdict

Needs major correction before execution

### Audit loop status

* Audit type: Follow-up audit
* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-06-08-adopt-cli.md
* Prior audit issue count: 5
* Resolved issue count: 2
* Still open issue count: 0
* Partially resolved issue count: 3
* New issue count: 1
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

Re-read the revised plan, prior audit ledger, current spec, git status/history, v3 handoff state, repo instructions, conventions, package metadata, validator/config code, registry, root scaffolds, workflows, standards docs, and plan diff. Retested prior fixes for I/O mapping, list error boundaries, invalid manifest handling, `list --json`, registry drift, fragment reporting, and the D1 validation path.

No tests, builds, packaging commands, `uv sync`, or formatter/linter commands were run because this audit is read-only and those commands may write environments, caches, or artifacts.

### Prior findings status

#### CR-001: Recoverable I/O failures can still escape as tracebacks

* Previous severity: High
* Current status: Resolved
* Evidence: The revised plan wraps source reads, fragment reads, directory creation, temp-file creation, write, and replace in `WriteError` mapping in B4/B5, and adds failure-injection tests for `mkstemp`, unreadable sources, and `os.replace`.
* Remaining action for Claude Code: Keep the new error mapping, and consider adding explicit `Path.mkdir` and fragment-read failure tests while implementing.

#### CR-002: Adoption validation test is not executable as written

* Previous severity: High
* Current status: Partially resolved
* Evidence: The subprocess/`uv run` problem is fixed by switching to in-process `validate_frontmatter.main()` with `monkeypatch.chdir(tmp_path)`. The invalid README fixture was removed. However, the revised test can now pass with zero managed files after the ADR template is excluded, so it does not prove the starter validates a realistic consumer `README.md` or `docs/**/*.md` file.
* Remaining action for Claude Code: Add a valid frontmatter-bearing `README.md` or `docs/*.md` fixture and assert validation returns 0 while actually validating at least one managed file.

#### CR-003: Invalid-manifest and list error paths do not satisfy the no-traceback contract

* Previous severity: High
* Current status: Partially resolved
* Evidence: `list` is now inside the `AdoptError` boundary, and the owned-destination collision no longer relies on the old `(kind, dest)` lookup. However, `manifest.py` still does not validate that `source`, `shared`, `dest`, and `target` are strings. A TOML manifest with `source = 1` or `dest = 1` can pass manifest loading and later raise a raw attribute/type error in `resolve_source()` or `validate_dest()`.
* Remaining action for Claude Code: Validate manifest field types at load time and add malformed-manifest tests for non-string `source`, `shared`, `dest`, and `target`.

#### CR-004: `list --json` omits the spec’s stable `contract_version` field

* Previous severity: Medium
* Current status: Partially resolved
* Evidence: `contract_version` is now emitted in `_cmd_list()`. The drift guard remains incomplete: `test_bundle_ids_match_registry_standards()` hardcodes the four expected ids instead of comparing to `registry.json`, and `build_plan()` still treats `available_standards()` as the only source of valid ids.
* Remaining action for Claude Code: Compare bundle ids to the registry-derived standards and fail cleanly on bundle/registry drift instead of allowing `contract_version: None`.

#### CR-005: Fragment reporting cannot represent multiple fragments for one target

* Previous severity: Medium
* Current status: Resolved
* Evidence: `Report.fragments` is now `dict[str, list[str]]`, `execute_plan()` appends snippets per target, `format_report()` prints every snippet, and a same-target multi-fragment regression test was added.
* Remaining action for Claude Code: None.

### New blocking issues

#### CR-NEW-001: Destination safety resolves away symlinks before checking them

* Severity: High
* Status: Confirmed
* Adversarial angle: The plan claims symlink destinations are skipped, but the proposed code resolves the symlink target first and then checks the resolved target for symlink status.
* Plan reference: `validate_dest()` and `execute_plan()` in plan lines 1013-1088; symlink test in lines 973-981.
* Finding: `validate_dest()` returns `(root / rel).resolve()`. `Path.resolve()` resolves symlinks, so `execute_plan()` receives the symlink target, not the link path. `abs_dest.is_symlink()` then checks the target and returns false for a regular target. Under `--force`, `_atomic_write()` writes to the target through the symlink path’s resolved destination instead of reporting `symlink_skipped`. The proposed test with `d.txt -> outside.txt` should fail as written. Fragment `target` paths are also never passed through `validate_dest()`, despite the spec requiring `dest` and `target` safety.
* Repository evidence: The spec requires existing symlink destinations to be skipped even under `--force` and destination paths including `target` to remain under `--dest`. The plan’s code resolves before symlink detection and only validates file/workflow `dest`, not fragment `target`.
* External research evidence: Python’s official `pathlib.Path.resolve()` docs state that it makes a path absolute while resolving symlinks: https://docs.python.org/3/library/pathlib.html#pathlib.Path.resolve
* Why it matters: The CLI’s write-safety contract is the core protection against clobbering consumer files. As written, a symlink destination can be followed and overwritten, and unsafe fragment targets can be reported without validation.
* Recommended action for Claude Code: Keep an unresolved candidate path for symlink checks, check `candidate.is_symlink()` before resolving the final destination, validate parent containment without following the final symlink, and validate fragment `target` paths as well as write `dest` paths.
* Suggested validation: Add tests for symlink-to-internal-target, symlink-to-external-target, and broken symlink destinations under `--force`; all should report `symlink_skipped` and preserve targets. Add tests that fragment `target = "../x"` and absolute fragment targets fail with exit 2 and no traceback.

### New non-blocking issues

None found.

### Regressions

None found.

### Internet research performed

* Source name: Python `pathlib` documentation
* URL: https://docs.python.org/3/library/pathlib.html#pathlib.Path.resolve
* Access date: 2026-06-08
* What it was used to verify: Whether `Path.resolve()` follows symlinks before the plan’s symlink check.
* Relevant conclusion: `Path.resolve()` resolves symlinks, confirming the proposed symlink skip logic is ordered incorrectly.

* Source name: Astral uv build backend documentation
* URL: https://docs.astral.sh/uv/concepts/build-backend/
* Access date: 2026-06-08
* What it was used to verify: Whether package data under the module root remains a plausible wheel-inclusion strategy.
* Relevant conclusion: The plan’s bundle location under `src/project_standards/` remains plausible, and the wheel-inspection test is still appropriate.

* Source name: Astral uv CLI documentation
* URL: https://docs.astral.sh/uv/reference/cli/
* Access date: 2026-06-08
* What it was used to verify: Current `uv build --out-dir` behavior and unchanged `uv run` assumptions from the prior audit.
* Relevant conclusion: No new conflict found; the prior `uv run` issue was addressed by switching to in-process validation.

### Read-only validation performed

* `pwd`, `git status --short`, `git branch --show-current`, `git log --oneline -n 10`: confirmed repo root, branch `testing`, modified plan, and untracked round-1 review artifact.
* Inspected `docs/handoff/state.md`, `AGENTS.md`, and `docs/handoff/conventions.md`: confirmed repo state and local validation rules.
* Inspected the revised plan with line numbers and `git diff`: identified changes made since round 1.
* Inspected the approved spec: compared plan behavior against CLI, safety, testing, registry, and acceptance requirements.
* Inspected `pyproject.toml`, `.project-standards.yml`, `registry.py`, `registry.json`, `validate_frontmatter.py`, root configs, workflows, and standard docs: checked repo evidence for plan claims.
* Performed official docs lookups for Python `pathlib` and uv packaging/CLI assumptions.

### Recommended implementation validation

* Run only after correction/implementation: `uv run pytest tests/test_adopt_safety.py -k "symlink or fragment" -v`
* Run only after correction/implementation: add malformed-manifest tests for non-string `source`, `shared`, `dest`, and `target`.
* Run only after correction/implementation: add registry/bundle drift tests that derive expected ids from `registry.json`.
* Run only after correction/implementation: add a realistic frontmatter-bearing README/docs fixture to the adoption validation test.
* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest`
* Run only after implementation: `uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`
* Run only after implementation: build and inspect a wheel in a temp directory, then run the installed CLI from that wheel.

### Final recommendation

Claude Code should revise the plan using the findings above

### Review ledger for next loop

* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-06-08-adopt-cli.md
* Audit round: 2
* Open issue IDs: CR-002, CR-003, CR-004, CR-NEW-001
* Resolved issue IDs: CR-001, CR-005
* Superseded issue IDs: None
* Significant findings remaining: Yes
* Next audit should focus on: symlink/fragment target safety, malformed manifest type validation, real managed-file starter validation, and registry/bundle drift enforcement.