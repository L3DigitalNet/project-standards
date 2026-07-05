### Executive summary

Claude Code’s revision resolves most round-1 findings, especially the ID definition/reference split, YAML frontmatter parsing, non-vacuous discovery, workflow self-repo branch, section slicing, denylist, and built-wheel smoke test.

Significant findings remain. The plan still has one partially resolved prior bad-input boundary issue and introduces a new blocking CLI exit-code bug: `project-standards spec` with no verb returns success. New internet research was performed for the remaining workflow/build assumptions; no new external-doc conflict is blocking.

### Verdict

Needs major correction before execution

### Audit loop status

* Audit type: Follow-up audit
* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-07-04-project-spec-tooling-spec1.md
* Prior audit issue count: 8
* Resolved issue count: 7
* Still open issue count: 0
* Partially resolved issue count: 1
* New issue count: 5
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

Retested all prior CR-001 through CR-008 corrections against the revised plan, current templates, the approved design spec, existing CLI/error-boundary patterns, current `.project-standards.yml`, `validate_frontmatter.collect_paths()`, pyproject strictness, and the existing reusable workflow. Attacked validation false positives around traceability, ID uniqueness, no-arg CLI behavior, explicit-path discovery, JSON coverage, non-UTF-8 input handling, and strict type-checking.

Could not safely run pytest, coverage, `uv build`, formatters, or package-manager commands because they may write caches, `.coverage`, build artifacts, or generated state in this read-only audit.

### Prior findings status

#### CR-001: ID uniqueness treats valid references as duplicate definitions

* Previous severity: High
* Current status: Resolved
* Evidence: The revised plan adds `definition_sites()` and tests `FR-001` appearing in both §7.1 and §17.3 while counting only one definition. Task 5 uniqueness now iterates over `definition_sites()`, not all `doc.used_ids`.
* Remaining action for Claude Code: Keep the regression fixture and ensure uniqueness is applied to all definition-bearing prefixes, including the new DEV gap noted below.

#### CR-002: Regex frontmatter parsing cannot handle the templates’ inline YAML comments

* Previous severity: High
* Current status: Resolved
* Evidence: Task 3 now uses `yaml.safe_load()` for scalar frontmatter values and adds a raw-template test proving `profile: full # ...` parses to `full` and `spec_id` parses to `SPEC-____`.
* Remaining action for Claude Code: None for the prior issue.

#### CR-003: `collect_spec_paths()` falls back to the whole Markdown corpus for `spec: {include: []}`

* Previous severity: High
* Current status: Resolved
* Evidence: Task 4 now guards `if not explicit and not cfg.include` before calling `collect_paths()`, and adds missing-spec, zero-match, and empty-include tests.
* Remaining action for Claude Code: Address the new explicit-path/exclude mismatch separately.

#### CR-004: Proposed reusable workflow installs the published tag even for this repo

* Previous severity: High
* Current status: Resolved
* Evidence: Task 11 now branches on `github.repository == 'L3DigitalNet/project-standards'`, using `uv sync --dev` and `uv run project-standards spec validate` for this repo, and `uv tool install` only for consuming repos.
* Remaining action for Claude Code: None for the prior issue.

#### CR-005: Bad-input error boundary still permits tracebacks

* Previous severity: High
* Current status: Partially resolved
* Evidence: Unterminated frontmatter is now wrapped in `SpecParseError`, and Task 9 tests malformed frontmatter without traceback. However `_read()` converts `UnicodeDecodeError` into `ConfigError`, so non-UTF-8 specs exit `2` as config errors instead of the design-required graceful spec-input `exit 1`.
* Remaining action for Claude Code: Treat unreadable text caused by `UnicodeDecodeError` as a per-file parse/input finding for validate/lint and exit `1`; add a non-UTF-8 fixture test.

#### CR-006: `NOT_AN_ID` is not copied verbatim from `check_specs.py`

* Previous severity: Medium
* Current status: Resolved
* Evidence: Task 2 now carries the current full denylist from `check_specs.py`, including `WCAG`, `PII`, `URL`, `SPEC`, `CSRF`, `CORS`, `SSO`, `WAL`, and `PITR`, and adds regression coverage for `WCAG-2` and `PITR-1`.
* Remaining action for Claude Code: None for the prior issue.

#### CR-007: `extract §7` only returns the heading prelude, not the full section with subsections

* Previous severity: Medium
* Current status: Resolved
* Evidence: Task 3 adds level-aware `section_slice()` that stops at the next heading of the same or higher level; Task 7 asserts `extract §7` includes `FR-001`.
* Remaining action for Claude Code: None for the prior issue.

#### CR-008: Source-tree packaging test does not prove the built wheel contains templates

* Previous severity: Low
* Current status: Resolved
* Evidence: Task 12 adds `tests/test_spec_wheel_contents.py`, runs `uv build --wheel --out-dir <tmp_path>`, and inspects the wheel archive for all three bundled templates.
* Remaining action for Claude Code: None for the prior issue.

### New blocking issues

#### CR-NEW-001: Bare `project-standards spec` returns success

* Severity: High
* Status: Confirmed
* Adversarial angle: Bad-invocation exit-code invariant can silently pass CI/operator checks.
* Plan reference: Task 9 `specs.cli.run()`, lines 1412-1415.
* Finding: `run([])` prints usage and returns `0` because `argv[:1] == []`. But invoking the `spec` group without a verb is a bad invocation and should exit `2`.
* Repository evidence: The approved design says bad invocation/config errors exit `2`, and `extract`/`next` require a verb-specific invocation. Current `src/project_standards/cli.py` uses argparse `required=True` for normal top-level missing commands, which does not silently succeed.
* External research evidence: Not applicable.
* Why it matters: `project-standards spec` can be used incorrectly and still report success, violating the CLI contract and allowing weak smoke tests to pass without validating anything.
* Recommended action for Claude Code: Return `2` when `argv` is empty; reserve `0` only for explicit `-h` / `--help`.
* Suggested validation: Add `assert main(["spec"]) == 2` and `assert main(["spec", "--help"]) == 0`.

### New non-blocking issues

#### CR-NEW-002: Duplicate `DEV-*` definitions are explicitly skipped

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Validation false negative for a declared ID prefix.
* Plan reference: Task 3 `definition_sites()`, lines 468-478.
* Finding: The plan skips prefixes whose Appendix A “Defined In” value has no numeric section, explicitly naming `DEV-` / Deviations Log. That means duplicate `DEV-001` rows are never caught by `SV-ID-DUP`.
* Repository evidence: All templates declare `DEV-` in Appendix A with `Defined In` = `Deviations Log`; the approved design requires per-spec ID uniqueness as part of `validate`.
* External research evidence: Not applicable.
* Why it matters: `DEV-*` rows are part of the agent implementation contract. Duplicate deviation IDs break stable references just like duplicate requirement IDs.
* Recommended action for Claude Code: Support unnumbered definition sites by resolving the “Deviations Log” heading or by adding an explicit prefix-to-heading fallback for `DEV-`.
* Suggested validation: Add a `bad_dup_dev.md` fixture with two `DEV-001` rows and assert `SV-ID-DUP`.

#### CR-NEW-003: Traceability lint checks every `FR-*`, not every Must requirement

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Validation false positive against the template priority model.
* Plan reference: Task 6 `_traceability()`, lines 1032-1038.
* Finding: The plan warns for every `FR-*` not present in §17.3. The design requires Standard/Full approved specs to map every `Must` requirement, not every Functional Requirement.
* Repository evidence: The Standard template has `FR-001` priority `Must`, `FR-002` priority `Should`, and §17.3 only maps `FR-001`.
* External research evidence: Not applicable.
* Why it matters: An approved Standard spec could be lint-warned for omitting a `Should` requirement from traceability even though the design only requires Must mapping.
* Recommended action for Claude Code: Derive Must FR definitions from the §7.1 table’s priority column, then compare only those IDs to §17.3.
* Suggested validation: Add an approved Standard fixture where `FR-001` is Must and mapped, `FR-002` is Should and unmapped, and assert no `SL-TRACE` for `FR-002`.

#### CR-NEW-004: Explicit path arguments can still be removed by config excludes

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Discovery contract mismatch can produce no-match errors for explicitly named files.
* Plan reference: Task 4 `collect_spec_paths()`, line 656.
* Finding: The plan calls `validate_frontmatter.collect_paths(explicit, None, cfg.include, cfg.exclude)`. That helper applies `exclude` in all cases, including explicit paths. The design says explicit path/glob args “validate exactly those” and bypass config discovery.
* Repository evidence: `validate_frontmatter.collect_paths()` documents that explicit args bypass includes but `exclude` is applied in all cases. The design’s discovery table says explicit path/glob args validate exactly those.
* External research evidence: Not applicable.
* Why it matters: `project-standards spec validate path/to/spec.md` can fail with `DiscoveryError` or silently skip the named file if the config excludes it, contradicting the explicit invocation contract.
* Recommended action for Claude Code: For explicit spec paths, validate existence without applying `cfg.exclude`, or explicitly revise the design/plan if excludes should override explicit args.
* Suggested validation: Add a config with `spec.exclude: ["docs/**"]`, pass an explicit `docs/spec.md`, and assert the explicit file is still returned.

#### CR-NEW-005: Planned snippets are not strict-type-clean as written

* Severity: Medium
* Status: Confirmed
* Adversarial angle: The full gate can fail after implementation even if behavior tests pass.
* Plan reference: Task 9 `_findings_payload()` line 1338; Task 7 and Task 8 helper functions lines 1170 and 1256.
* Finding: `_findings_payload(results: list[tuple[Path, list]])` uses a bare `list` type argument, and test helpers `def _doc():` / `def _doc(name: str = ...)` omit return annotations. This repo runs BasedPyright strict with `failOnWarnings = true`.
* Repository evidence: `pyproject.toml` includes both `src` and `tests` under BasedPyright strict mode.
* External research evidence: Not applicable.
* Why it matters: The implementation may follow the plan exactly, pass local pytest slices, then fail the required full gate at the type-check step.
* Recommended action for Claude Code: Use precise types in snippets, e.g. `list[Finding]` and `-> SpecDocument`, before implementation rather than relying on Task 12 cleanup.
* Suggested validation: Run `uv run basedpyright` after the first task that introduces these files, not only at the end.

### Regressions

None found.

### Internet research performed

* Source name: uv build backend documentation
* URL: https://docs.astral.sh/uv/concepts/build-backend/
* Access date: 2026-07-05
* What it was used to verify: Whether `uv_build` includes files under the module root in built wheels.
* Relevant conclusion: The docs state wheel builds include the module under the module root and that small data files should live under the module root; the plan’s wheel-content test is still appropriate.

* Source name: astral-sh/setup-uv GitHub releases
* URL: https://github.com/astral-sh/setup-uv/releases
* Access date: 2026-07-05
* What it was used to verify: Current release state for `setup-uv`.
* Relevant conclusion: The release list shows `v8.2.0` and “Immutable releases and secure tags” at `v8.0.0`; the plan’s SHA/comment matches the existing repo workflow pattern.

* Source name: actions/checkout GitHub releases
* URL: https://github.com/actions/checkout/releases
* Access date: 2026-07-05
* What it was used to verify: Current release state for `actions/checkout`.
* Relevant conclusion: The release list shows newer releases than `v6`, including `v7.0.0`; no blocking issue was raised because the plan intentionally mirrors the repository’s existing `actions/checkout@v6` workflow.

### Read-only validation performed

* `pwd` — confirmed repository root is `/home/chris/projects/project-standards`.
* `git status --short` — confirmed only the plan file is modified, plus an untracked prior review artifact.
* `git branch --show-current` — confirmed current branch is `testing`.
* `git log --oneline -n 10` — confirmed recent plan/design commits.
* `wc -l` and `sed -n` on the plan — re-read the revised plan.
* `git diff -- docs/superpowers/plans/2026-07-04-project-spec-tooling-spec1.md` — compared round-2 changes against committed round-1 plan.
* `sed -n` / `nl -ba` on the approved design spec — checked CLI, discovery, JSON, testing, error handling, and acceptance contracts.
* `sed -n` on `standards/project-spec/resources/check_specs.py` — verified current parser primitives and denylist.
* `rg` / `sed -n` on project-spec templates — verified inline comments, traceability rows, priorities, Appendix A prefixes, and `DEV-` Defined In text.
* `sed -n` on `src/project_standards/validate_frontmatter.py` — verified `collect_paths()` applies excludes even with explicit paths.
* `sed -n` on `src/project_standards/cli.py` — checked existing early-dispatch/error-boundary style.
* `sed -n` on `.github/workflows/validate-markdown-frontmatter.yml` — verified existing self-repo vs consuming-repo workflow pattern.
* `sed -n` on `pyproject.toml` — verified BasedPyright strict mode includes `src` and `tests`.
* `git diff --stat` and `git diff --check` — checked modified plan footprint and whitespace errors.

### Recommended implementation validation

* Run only after implementation: `uv run pytest tests/test_spec_cli.py -v`, including new tests for `main(["spec"]) == 2` and non-UTF-8 input.
* Run only after implementation: `uv run pytest tests/test_spec_validate.py tests/test_spec_lint.py tests/test_spec_config.py -v`, including the new `DEV-` duplicate, Must-only traceability, and explicit-path/exclude cases.
* Run only after implementation: `uv run pytest tests/test_spec_cli.py tests/test_spec_extract.py tests/test_spec_next.py -v`, including JSON shape tests for lint and extract found/no-match.
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
* Audit round: 2
* Open issue IDs: CR-005, CR-NEW-001, CR-NEW-002, CR-NEW-003, CR-NEW-004, CR-NEW-005
* Resolved issue IDs: CR-001, CR-002, CR-003, CR-004, CR-006, CR-007, CR-008
* Superseded issue IDs: None
* Significant findings remaining: Yes
* Next audit should focus on: no-verb CLI exit code, non-UTF-8 input handling, DEV duplicate definitions, Must-only traceability, explicit-path discovery semantics, and BasedPyright-clean planned snippets.