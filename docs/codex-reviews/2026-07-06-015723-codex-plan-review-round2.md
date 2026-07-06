### Executive summary

Claude Code’s revisions resolved the four prior findings. The corrected plan now uses a structurally valid CLI fixture for `validate`, adds the missing tooling-notes documentation, replaces stale SPDX examples with current/clearly-labeled forms, and adds JSON-safe `upgrade --config` malformed-config coverage.

New internet research was performed against official SPDX pages to re-check the revised license examples. No significant findings remain.

### Verdict

No significant findings remain

### Audit loop status

* Audit type: Follow-up audit
* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-07-06-spec-validator-external-references.md
* Prior audit issue count: 4
* Resolved issue count: 4
* Still open issue count: 0
* Partially resolved issue count: 0
* New issue count: 0
* Regression count: 0
* Significant findings remaining: No

### Adversarial review performed

Re-read the revised plan and rechecked the prior findings against the current repository evidence. Retested the strongest assumptions: valid-fixture selection for the CLI test, config threading points, `upgrade --config` error wrapping, docs coverage, template byte-identity scope, release-prep claims, and SPDX identifier examples.

Inspected relevant source, tests, fixtures, docs, config, CI, package metadata, and current git state. Did not run pytest, coverage, uv lock, Prettier, or markdownlint because those can write cache, coverage, lockfile, or formatted-file state.

### Prior findings status

#### CR-001: Task 4’s CLI validation test uses an invalid spec fixture

* Previous severity: High
* Current status: Resolved
* Evidence: Revised Task 4 now explicitly avoids the minimal invalid fixture and starts from `tests/fixtures/specs/valid_light.md`, injecting `RQ-123` into prose before `## Revision History` and asserting both the no-config failure and config-enabled success. Repository evidence confirms `valid_light.md` is a complete Light spec fixture with required frontmatter, sections, appendices, and declared IDs.
* Remaining action for Claude Code: Implement the test using the existing test file’s helper/import style and run the targeted CLI test after implementation.

#### CR-002: Tooling notes will become stale after the parser contract changes

* Previous severity: Medium
* Current status: Resolved
* Evidence: Revised Task 7 adds `standards/project-spec/resources/tooling-notes.md` to the docs files and gives specific edits for the ID extraction and suggested parse pipeline sections. Repository evidence confirms the current tooling notes still document only `NOT_AN_ID`, so the revised task addresses the stale surface directly.
* Remaining action for Claude Code: Apply the tooling-notes update alongside the README update and include both files in docs validation.

#### CR-003: Public SPDX examples use stale or inaccurate identifiers

* Previous severity: Low
* Current status: Resolved
* Evidence: Revised plan uses current GNU examples such as `GPL-3.0-only`, `AGPL-3.0-or-later`, and `LGPL-2.1-or-later`, and labels bare `GPL-3` as colloquial/not a current SPDX id. Official SPDX pages confirm `GPL-3.0-only`, `LGPL-2.1-or-later`, `MIT-0`, and `NTP-0` as short identifiers, and `GPL-3.0` as deprecated since License List 3.0.
* Remaining action for Claude Code: Keep the “bare GPL-3” wording explicitly colloquial in all public docs/changelog text.

#### CR-004: Upgrade config-error JSON path is specified but untested

* Previous severity: Medium
* Current status: Resolved
* Evidence: Revised Task 5 adds `test_upgrade_explicit_malformed_config_is_json_safe`, asserting `rc == 2` and JSON `code == "config_error"`. The plan also catches `ConfigError` inside `_run_upgrade` and re-raises `NewError("config_error", ...)`, matching the command’s JSON-safe envelope path.
* Remaining action for Claude Code: Implement the test using the existing `capsys.readouterr().out` pattern in `tests/test_spec_upgrade_cli.py`.

### New blocking issues

None found.

### New non-blocking issues

None found.

### Regressions

None found.

### Internet research performed

* Source name: SPDX License List
* URL: https://spdx.org/licenses/
* Access date: 2026-07-06
* What it was used to verify: Current SPDX License List version and example identifiers.
* Relevant conclusion: Current list is version `3.28.0 2026-02-20`; examples like `AGPL-3.0-or-later`, `CC-BY-4.0`, and `BSD-3-Clause` are present.

* Source name: SPDX GPL-3.0-only page
* URL: https://spdx.org/licenses/GPL-3.0-only.html
* Access date: 2026-07-06
* What it was used to verify: Current GPL v3 “only” short identifier.
* Relevant conclusion: `GPL-3.0-only` is a current SPDX short identifier.

* Source name: SPDX LGPL-2.1-or-later page
* URL: https://spdx.org/licenses/LGPL-2.1-or-later.html
* Access date: 2026-07-06
* What it was used to verify: Current LGPL 2.1 “or later” short identifier.
* Relevant conclusion: `LGPL-2.1-or-later` is a current SPDX short identifier.

* Source name: SPDX MIT-0 and NTP-0 pages
* URL: https://spdx.org/licenses/MIT-0.html and https://spdx.org/licenses/NTP-0.html
* Access date: 2026-07-06
* What it was used to verify: Zero-version SPDX identifiers that share the project-spec token shape.
* Relevant conclusion: `MIT-0` and `NTP-0` are current short identifiers and require config handling because their shape is indistinguishable from spec-local IDs.

### Read-only validation performed

* `pwd`: confirmed repository root is `/home/chris/projects/project-standards`.
* `git status --short`: confirmed existing dirty state remains `M TODO.md` and untracked `docs/codex-reviews/`.
* `git branch --show-current`: confirmed branch `testing`.
* `git log --oneline -n 10`: confirmed the latest commit applies plan-review round 1 corrections.
* `nl -ba docs/superpowers/plans/2026-07-06-spec-validator-external-references.md`: re-read the revised plan and line-numbered all tasks.
* `nl -ba` inspections of `document.py`, `registry.py`, `config.py`, `cli.py`, `validate.py`, and `upgrade.py`: verified current parser, config, CLI, validation, and upgrade behavior against the proposed changes.
* `nl -ba` inspections of relevant tests and fixtures: verified existing test helper patterns, valid fixture structure, upgrade fixture structure, and template parity guard.
* `rg` inspections of README, tooling notes, changelog, templates, config, workflows, and package files: confirmed prior stale docs/templates state and validation/tooling surfaces.
* `command -v markdownlint-cli2`, `test -x node_modules/.bin/...`: checked local formatter/linter binary availability without running mutating tools.
* Official SPDX page inspections: verified revised external-license examples.

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
* Run only after implementation: Prettier and markdownlint checks for changed Markdown files.
* Run only during release prep: `uv lock`, then inspect `uv.lock` to confirm only the project version changed unless dependency changes are intentional.

### Final recommendation

No significant findings remain; the audit/fix loop can stop

### Review ledger for next loop

* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-07-06-spec-validator-external-references.md
* Audit round: 2
* Open issue IDs: None
* Resolved issue IDs: CR-001, CR-002, CR-003, CR-004
* Superseded issue IDs: None
* Significant findings remaining: No
* Next audit should focus on: No significant findings remain; only re-audit if the plan changes again.