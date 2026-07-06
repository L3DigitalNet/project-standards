### Executive summary

The implementation plan is not ready to execute as written. The main blocker is a planned CLI regression test that cannot pass after the proposed implementation because its fixture is not a valid project spec; `spec validate` will still return nonzero for unrelated structural findings.

Internet research was required for the SPDX/license assumptions. Official SPDX documentation confirms the plan’s parser approach is mostly compatible with current license identifiers, but some public-facing examples in the plan (`GPL-3`, `LGPL-2.1`) are stale or inaccurate as SPDX identifiers and should be corrected before release docs/changelog are written.

### Verdict

Needs major correction before execution

### Audit loop status

* Audit type: First audit
* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-07-06-spec-validator-external-references.md
* Significant findings remaining: Yes
* Blocking issue count: 1
* Non-blocking issue count: 3

### What the plan gets right

* It correctly identifies the single scan point in `parse_document` as the right place to separate spec-local IDs from external references.
* It keeps `upgrade --config` opt-in rather than default-loading `.project-standards.yml`, which matches the stated compatibility goal.
* It correctly avoids wiring config into `extract` and `next`; repository evidence shows `extract` searches raw rows and `next` only needs parsed spec-local IDs.
* It includes the four template copies that must stay byte-identical for Standard and Full.

### Adversarial review performed

I inventoried the plan’s material claims around `parse_document`, `NOT_AN_ID`, config parsing, `validate`/`lint`/`new`/`upgrade` call sites, template parity, docs, release prep, and validation gates.

I falsified those claims against the current repository files: `src/project_standards/specs/document.py`, `registry.py`, `config.py`, `cli.py`, `commands/validate.py`, `commands/upgrade.py`, related tests, templates, README/adopt docs, `meta/versioning.md`, `.project-standards.yml`, and CI workflow configuration.

I attacked validation false positives, especially tests that could pass or fail for the wrong reason. The strongest failing assumption is that Task 4’s minimal Markdown file can be expected to return `rc == 0` from `spec validate`.

I used official SPDX documentation for the external license identifier assumptions. I did not run tests because pytest/coverage can write cache and coverage artifacts, which is outside the read-only audit mode.

### Blocking issues

#### CR-001: Task 4’s CLI validation test uses an invalid spec fixture

* Severity: High
* Status: Confirmed
* Adversarial angle: Validation false positive / executable-as-written check.
* Plan reference: Task 4, `test_validate_honors_reference_prefixes`, lines 425-435.
* Finding: The proposed test writes only minimal frontmatter and `# 1. Overview`, then expects `run(["validate", ...]) == 0`. Even after `RQ-123` is skipped correctly, this document is still not a valid project spec. The validator checks exact frontmatter keys, status, profile, canonical gaps, and required appendices, so the test will fail for unrelated structural reasons.
* Repository evidence: `validate_document` always runs `_check_frontmatter`, `_check_sections`, `_check_appendices`, `_check_references`, `_check_ids`, and `_check_tables` (`src/project_standards/specs/commands/validate.py:33-41`). `_check_frontmatter` emits findings for missing canonical keys, missing/invalid `status`, and missing/invalid `profile` (`validate.py:45-78`). `_check_sections` emits `SV-GAP` for missing unannotated canonical sections (`validate.py:81-104`). `_check_appendices` requires Appendices A, B, and D (`validate.py:107-123`).
* External research evidence: Not applicable.
* Why it matters: Claude Code will implement the intended code and still hit a failing planned test. That can cause unnecessary code changes, weakened assertions, or a false conclusion that the implementation is wrong.
* Recommended action for Claude Code: Replace the Task 4 fixture with a known-valid spec fixture, then inject `RQ-123` into harmless prose and validate with a config containing `reference_prefixes: ['RQ']`. Alternatively, assert the CLI JSON output does not contain `SV-ID-UNDECLARED`, but `rc == 0` requires the whole spec to be structurally valid.
* Suggested validation: After correcting the test fixture, run the targeted Task 4 test first, then `uv run pytest tests/test_spec_cli.py -v` after implementation.

### Non-blocking issues

#### CR-002: Tooling notes will become stale after the parser contract changes

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Missing documentation / maintainability drift.
* Plan reference: Task 7 documents only `standards/project-spec/README.md`; Task 8 updates only `CHANGELOG.md`, `pyproject.toml`, and `uv.lock`.
* Finding: The plan changes the parse pipeline from “ID regex minus `NOT_AN_ID`” to “ID regex minus `NOT_AN_ID`, built-in reference prefixes, config reference prefixes, and dot-version shape rule,” but it does not update `standards/project-spec/resources/tooling-notes.md`.
* Repository evidence: `standards/project-spec/resources/tooling-notes.md` still documents the extraction regex and only the `NOT_AN_ID` denylist at lines 166-172, and the suggested parse pipeline says to index IDs with the regex minus `NOT_AN_ID` at lines 282-288. README links this file as “Tooling notes” in the Project Specification resources.
* External research evidence: Not applicable.
* Why it matters: This repo is the source of truth for downstream standards. Leaving the maintainer tooling notes stale makes future agents and implementers rediscover the new skip-set contract from code instead of docs.
* Recommended action for Claude Code: Add `standards/project-spec/resources/tooling-notes.md` to Task 7 or a separate docs task, updating the ID extraction and parse pipeline sections to describe built-in references, `spec.reference_prefixes`, and the dot-version skip rule.
* Suggested validation: Run Prettier/markdownlint on both changed docs and include the file in the final frontmatter validation gate.

#### CR-003: Public SPDX examples use stale or inaccurate identifiers

* Severity: Low
* Status: Confirmed
* Adversarial angle: External documentation freshness / release-note accuracy.
* Plan reference: Task 1 test string lines 59-60; README snippet lines 653-655; changelog text lines 722-723.
* Finding: The implementation will likely skip modern SPDX tokens correctly because `GPL-3.0-only` and similar tokens match `GPL-3` followed by `.`+digit, but the plan’s docs/changelog examples call `GPL-3` a common versioned SPDX license identifier and use deprecated GNU-family examples such as `LGPL-2.1`.
* Repository evidence: The plan’s docs/changelog snippets explicitly list `GPL-3` and `LGPL-2.1` as common versioned license identifiers.
* External research evidence: Official SPDX License List version `3.28.0 2026-02-20` says the list provides standardized short identifiers. Current list entries include `CC-BY-4.0` and `NTP-0`; deprecated GNU identifiers include `GPL-3.0` and `LGPL-2.1`, and SPDX explains that GNU identifiers were replaced in License List 3.0 by more explicit `-only` / `-or-later` identifiers. Source: https://spdx.org/licenses/ accessed 2026-07-06.
* Why it matters: This is a release-doc accuracy issue. Consumers may copy examples into policy docs and perpetuate invalid or deprecated SPDX forms.
* Recommended action for Claude Code: Change public docs/changelog examples to current identifiers such as `GPL-3.0-only`, `GPL-3.0-or-later`, `LGPL-2.1-only`, or `LGPL-2.1-or-later`. If retaining `GPL-3` as a colloquial false-positive example, label it as SPDX-like prose rather than an SPDX identifier.
* Suggested validation: Add at least one test case with a modern GNU SPDX form, e.g. `GPL-3.0-only` or `AGPL-3.0-or-later`, so the docs and tests align with current SPDX usage.

#### CR-004: Upgrade config-error JSON path is specified but untested

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Failure-mode and validation attack.
* Plan reference: Task 5, lines 536-547.
* Finding: The plan explicitly says malformed `--config` on `upgrade` should be converted into the command’s JSON-safe `NewError("config_error", ...)` path, but the proposed tests only cover “no `--config` ignores malformed default config.” They do not cover `upgrade --config bad.yml --json`.
* Repository evidence: `_run_upgrade` has its own JSON-safe `NewError` wrapper (`src/project_standards/specs/cli.py:472-557`). The public `run()` wrapper catches bare `ConfigError`, but that path prints a plain error and does not preserve the JSON envelope. The plan intends to catch `ConfigError` inside `_run_upgrade`, but no proposed test proves the JSON contract.
* External research evidence: Not applicable.
* Why it matters: The plan’s stated machine-output safety can regress silently. A malformed config passed explicitly to `upgrade --json` is an important operator failure mode for the new flag.
* Recommended action for Claude Code: Add a Task 5 test for `--config` pointing at malformed YAML with `--json`, asserting `rc == 2` and JSON payload `code == "config_error"`.
* Suggested validation: Run the new targeted upgrade config-error test plus the full `tests/test_spec_upgrade_cli.py` suite after implementation.

### Missing considerations

* Blocking: Correct Task 4’s invalid CLI fixture before implementation; otherwise the plan’s TDD loop will fail for the wrong reason.
* Non-blocking: Update `standards/project-spec/resources/tooling-notes.md` so the maintainer parse-pipeline docs match the new skip-set behavior.
* Non-blocking: Add tests for modern SPDX identifiers, not only deprecated or colloquial examples.
* Non-blocking: Add a JSON-mode test for `upgrade --config <malformed>` returning a structured `config_error`.
* Non-blocking: Consider making `_str_list` error messages key-specific for `spec.reference_prefixes`; the current helper’s message names only `spec.include/spec.exclude`.
* Non-blocking: Consider avoiding a second `load_spec_config(args.config)` in `_run_new` by threading the already-loaded config out of `_resolve_new_options`, reducing race and duplicate parsing.

### Internet research performed

* Source name: SPDX License List
* URL: https://spdx.org/licenses/
* Access date: 2026-07-06
* What it was used to verify: Current SPDX license identifier forms and deprecated GNU-family identifiers.
* Relevant conclusion: SPDX current list/version is `3.28.0 2026-02-20`; examples like `CC-BY-4.0`, `MIT-0`, and `NTP-0` are present; GNU-family identifiers such as `GPL-3.0`/`LGPL-2.1` are deprecated in favor of explicit `-only` / `-or-later` forms. The plan should not call `GPL-3` a current SPDX identifier.

### Items Claude Code should verify before correcting the plan

* Re-check the current `tests/fixtures/specs/valid_standard.md` or another valid fixture and choose an injection point for `RQ-123` that does not break structural validation.
* Confirm whether `standards/project-spec/resources/tooling-notes.md` is considered normative enough to update with Task 7; repository links indicate it is part of the Project Specification resources.
* Verify the final docs examples use current SPDX identifiers and still demonstrate the dot-version skip rule.
* Verify `upgrade --config <bad.yml> --json` returns the JSON-safe `config_error` envelope after implementation.
* Confirm the current working tree’s unrelated `TODO.md` deletion and untracked `docs/codex-reviews/` files are not included in implementation commits unless intentionally requested.

### Suggested corrections for Claude Code's plan

* Replace Task 4’s minimal CLI fixture with a valid project-spec fixture that would return `0` except for the external reference behavior being tested.
* Add `standards/project-spec/resources/tooling-notes.md` to the docs task and validation commands.
* Change public SPDX examples from `GPL-3` to current SPDX forms, or label them as colloquial/SPDX-like false positives.
* Add a Task 5 JSON config-error test for `upgrade --config`.
* Add a modern SPDX test case such as `GPL-3.0-only` or `AGPL-3.0-or-later`.
* Optionally make config list parsing errors mention `spec.reference_prefixes` when that key is malformed.

### Read-only validation performed

* `pwd`: confirmed repository root is `/home/chris/projects/project-standards`.
* `git status --short`: confirmed dirty tree with modified `TODO.md` and untracked `docs/codex-reviews/`.
* `git branch --show-current`: confirmed branch `testing`.
* `git log --oneline -n 10`: confirmed recent commits include the spec design and this implementation plan.
* `git diff --stat` and `git diff -- TODO.md`: confirmed the existing tracked change is an unrelated TODO deletion.
* `rg --files`: inventoried repository files and confirmed relevant source, tests, docs, workflows, and plan paths.
* `sed`/`nl` inspections of the plan: inventoried tasks, file claims, tests, commands, release prep, and self-review claims.
* `sed`/`nl` inspections of `src/project_standards/specs/document.py`, `registry.py`, `config.py`, `cli.py`, `commands/validate.py`, and `commands/upgrade.py`: verified current parser, config, validation, CLI, and upgrade behavior.
* `sed` inspections of related tests: checked current fixture/test patterns in document, config, CLI, validate, extract, next, packaging, and upgrade tests.
* `grep` inspections of templates and docs: confirmed four `<link if durable>` template rows and stale tooling notes for `NOT_AN_ID`-only parsing.
* `sed` inspections of `pyproject.toml`, `.project-standards.yml`, `CHANGELOG.md`, `meta/versioning.md`, Project Specification README, ADR README, and `validate-specs.yml`: verified toolchain floor, config shape, release contract, ADR lowercase ID convention, and CI behavior.
* Web inspection of official SPDX License List: verified current/deprecated license identifier assumptions.

### Recommended implementation validation

* Run only after implementation: `uv run pytest tests/test_spec_document.py -v`
* Run only after implementation: `uv run pytest tests/test_spec_config.py -v`
* Run only after implementation: `uv run pytest tests/test_spec_validate.py -v`
* Run only after implementation: `uv run pytest tests/test_spec_cli.py -v`
* Run only after implementation: `uv run pytest tests/test_spec_upgrade_cli.py -v`
* Run only after implementation: `uv run pytest tests/ -k spec -q`
* Run only after implementation: `uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`
* Run only after implementation: `uv run project-standards spec validate --config .project-standards.yml`
* Run only after implementation: Prettier/markdownlint checks for every changed Markdown file, including `standards/project-spec/README.md`, `standards/project-spec/resources/tooling-notes.md` if added, and `CHANGELOG.md`.
* Run only during implementation release prep: `uv lock`, then inspect that only the project version changed unless dependency changes are intentional.

### Final recommendation

Claude Code should revise the plan using the findings above

### Review ledger for next loop

* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-07-06-spec-validator-external-references.md
* Audit round: 1
* Open issue IDs: CR-001, CR-002, CR-003, CR-004
* Resolved issue IDs: None
* Superseded issue IDs: None
* Significant findings remaining: Yes
* Next audit should focus on: corrected Task 4 fixture validity, docs/tooling-notes coverage, SPDX example accuracy, and upgrade JSON config-error coverage.