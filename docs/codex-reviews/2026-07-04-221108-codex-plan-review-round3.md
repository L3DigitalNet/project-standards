### Executive summary

Claude Code’s round-3 revisions resolve the blocking findings from the prior audit: bare `project-standards spec` now exits `2`, non-UTF-8 specs are treated as spec-input failures at exit `1`, `DEV-*` duplicate definitions are covered, and explicit path arguments bypass `spec.exclude`.

Significant findings still remain, but they are now non-blocking. The remaining issues are validation-quality and strict-type-readiness gaps: Must traceability is not derived from the Priority column precisely, the registry primitive copy still risks BasedPyright strict failures, and the frozen `--json` contract is under-tested. No new internet research was required because the round-3 changes were internal plan/code-shape changes; unchanged workflow/build assumptions were already externally checked in the prior pass.

### Verdict

Needs minor correction before execution

### Audit loop status

* Audit type: Follow-up audit
* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-07-04-project-spec-tooling-spec1.md
* Prior audit issue count: 6
* Resolved issue count: 4
* Still open issue count: 0
* Partially resolved issue count: 2
* New issue count: 1
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

Retested the prior open ledger against the revised plan and current repository evidence: CLI no-verb behavior, non-UTF-8 handling, `DEV-` Defined-In resolution, Must-only traceability, explicit-path discovery, and strict typing. Re-read the revised plan, approved design spec, current templates, current CLI dispatch style, `validate_frontmatter.collect_paths()`, workflow pattern, and pyproject strictness.

Validation false positives were attacked around traceability parsing, JSON contract coverage, stale expected test counts, strict type-checking, and whether implementation validation could pass while the public command contract remains partially unproved.

Could not safely run pytest, coverage, `uv build`, formatters, `basedpyright`, or package-manager commands because this is a read-only audit and those commands may write caches, `.coverage`, build outputs, or other generated state.

### Prior findings status

#### CR-005: Bad-input error boundary still permits tracebacks

* Previous severity: High
* Current status: Resolved
* Evidence: Task 9 now splits `UnicodeDecodeError` from `OSError` in `_read()` and raises `SpecParseError` for non-UTF-8 input. `_run_setwide()` converts `SpecParseError` into an `SV-PARSE` finding and returns exit `1`; `run()` also catches `SpecParseError` for `extract`/`next` and returns exit `1`. The plan adds `test_non_utf8_spec_exits_1`.
* Remaining action for Claude Code: Keep the non-UTF-8 fixture and add an `extract` or `next` malformed-input assertion if coverage requires it.

#### CR-NEW-001: Bare `project-standards spec` returns success

* Previous severity: High
* Current status: Resolved
* Evidence: Task 9 `run()` now returns `0` only for explicit `-h`/`--help`; empty `argv` prints usage to stderr and returns `2`. The plan adds `test_bare_spec_is_exit2_but_help_is_exit0`.
* Remaining action for Claude Code: None.

#### CR-NEW-002: Duplicate `DEV-*` definitions are explicitly skipped

* Previous severity: Medium
* Current status: Resolved
* Evidence: Task 3 `_defined_in_slice()` now resolves unnumbered Defined-In headings such as `Deviations Log`; Task 5 adds `bad_dup_dev.md` and expects `SV-ID-DUP`. Current Light/Standard templates define `DEV-` as `Deviations Log` and contain a `## Deviations Log` heading.
* Remaining action for Claude Code: Keep the `bad_dup_dev.md` fixture.

#### CR-NEW-003: Traceability lint checks every `FR-*`, not every Must requirement

* Previous severity: Medium
* Current status: Partially resolved
* Evidence: The plan no longer checks every `FR-*`; `_must_frs()` reads §7.1 and only considers rows containing `Must`. However it checks `if ... "Must" in cells`, not the Priority column specifically. The Standard template defines Priority as the fifth column, and the design says `Must` is a priority value.
* Remaining action for Claude Code: Parse the §7.1 header, locate the `Priority` column, and require that specific cell to equal `Must`. Add a fixture where a `Should` row contains the word “Must” in another cell and assert it is not flagged.

#### CR-NEW-004: Explicit path arguments can still be removed by config excludes

* Previous severity: Medium
* Current status: Resolved
* Evidence: Task 4 `collect_spec_paths()` now returns sorted explicit files directly after existence checks and does not pass them through `collect_paths()` or `cfg.exclude`. The plan adds `test_explicit_path_survives_config_exclude`.
* Remaining action for Claude Code: None.

#### CR-NEW-005: Planned snippets are not strict-type-clean as written

* Previous severity: Medium
* Current status: Partially resolved
* Evidence: The prior bare `list` and unannotated test helpers are fixed. But Task 2 still instructs copying `split_front_matter` “verbatim from `check_specs.py`”; the current source function is `def split_front_matter(text):` with no parameter or return annotations, and the new `src/project_standards/specs/registry.py` will be under BasedPyright strict. `pyproject.toml` includes `src` and `tests` in strict mode with `failOnWarnings = true`.
* Remaining action for Claude Code: Do not copy untyped primitives verbatim into `src`; preserve semantics but add strict-clean signatures, especially `split_front_matter(text: str) -> tuple[str, str]`.

### New blocking issues

None found.

### New non-blocking issues

#### CR-NEW-006: JSON contract tests do not cover the frozen public surface

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Validation can pass while `--json` remains wrong for half the advertised command contract.
* Plan reference: Task 9 tests, lines 1545-1560; design JSON contract, lines 136-164 and testing requirement lines 209-211.
* Finding: The plan tests JSON for `validate` failure and `next`, but does not test `lint --json`, `extract --json` found, or `extract --json` no-match. The design explicitly freezes JSON shape for `validate`/`lint`, `extract`, and `next`, and calls for JSON golden-output tests for `validate`/`lint` findings, `extract` found/no-match, and `next`.
* Repository evidence: The approved design requires stable fields for all JSON modes and specifically lists JSON golden-output tests. Task 9 currently includes only `test_spec_validate_bad_exit1_json` and `test_spec_next_json`.
* External research evidence: Not applicable.
* Why it matters: `extract --json` could omit `markdown: null` on no-match, `lint --json` could use the wrong severity or result shape, or found/no-match extract output could drift while the planned tests still pass.
* Recommended action for Claude Code: Add explicit JSON tests for `spec lint --json`, `spec extract --json` found, and `spec extract --json` no-match.
* Suggested validation: Assert the exact top-level keys and representative values for all four JSON command surfaces, including `found: false` and `markdown is None` for extract no-match.

### Regressions

None found.

### Internet research performed

No new internet research was necessary in this follow-up pass. The round-3 changes under audit were internal plan corrections against repository-local contracts. The external workflow/build assumptions were unchanged from round 2, where they were already checked against current upstream sources.

### Read-only validation performed

* `pwd` — confirmed repository root is `/home/chris/projects/project-standards`.
* `git status --short` — confirmed only the plan is modified, plus two untracked prior review artifacts.
* `git branch --show-current` — confirmed branch is `testing`.
* `git log --oneline -n 10` — confirmed recent design and implementation-plan commits.
* `wc -l` on the plan — confirmed revised plan length is 1905 lines.
* `rg` over the plan for prior issue terms — located round-3 corrections for CR-005 and CR-NEW-001 through CR-NEW-005.
* `git diff -- docs/superpowers/plans/2026-07-04-project-spec-tooling-spec1.md` — reviewed the current plan changes against the committed prior version.
* `nl -ba` / `sed -n` on the plan — inspected Task 2, Task 3, Task 4, Task 5, Task 6, Task 9, Task 11, Task 12, and self-review sections.
* `nl -ba` / `sed -n` on the approved design spec — checked command behavior, JSON contract, error handling, discovery, and testing requirements.
* `sed -n` on `standards/project-spec/resources/check_specs.py` — verified copied primitive shapes and the untyped `split_front_matter`.
* `nl -ba` / `rg` on project-spec templates — verified §7.1 Priority column, §17.3 traceability rows, `DEV-` Defined-In text, and `## Deviations Log`.
* `sed -n` on `src/project_standards/cli.py` — checked existing early-dispatch and argparse/error-boundary patterns.
* `sed -n` on `src/project_standards/validate_frontmatter.py` — verified `collect_paths()` exclude behavior and helper availability.
* `sed -n` on `.github/workflows/validate-markdown-frontmatter.yml` — checked the existing workflow pattern mirrored by the plan.
* `nl -ba pyproject.toml` — verified BasedPyright strict mode includes both `src` and `tests`.
* `git diff --stat` and `git diff --check` — checked modified plan footprint and whitespace errors.

### Recommended implementation validation

* Run only after implementation: `uv run pytest tests/test_spec_cli.py -v`, including tests for bare `spec`, non-UTF-8 input, `lint --json`, `extract --json` found, and `extract --json` no-match.
* Run only after implementation: `uv run pytest tests/test_spec_lint.py -v`, including a Priority-column fixture where a non-Must row contains “Must” outside the Priority cell.
* Run only after implementation: `uv run pytest tests/test_spec_validate.py tests/test_spec_config.py -v`, including `bad_dup_dev.md` and explicit-path/exclude coverage.
* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest && uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`
* Run only after implementation: `uv build`, then inspect the wheel for `project_standards/specs/templates/*.md`.

### Final recommendation

Claude Code should revise the plan using the findings above

### Review ledger for next loop

* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-07-04-project-spec-tooling-spec1.md
* Audit round: 3
* Open issue IDs: CR-NEW-003, CR-NEW-005, CR-NEW-006
* Resolved issue IDs: CR-005, CR-NEW-001, CR-NEW-002, CR-NEW-004
* Superseded issue IDs: None
* Significant findings remaining: Yes
* Next audit should focus on: Priority-column traceability parsing, strict-clean registry primitive annotations, and complete JSON contract tests for lint and extract.