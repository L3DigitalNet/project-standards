### Executive summary

Claude Code’s revisions substantively resolved all four prior findings: `upgrade` is now in scope, SPDX handling is explicitly scoped, coverage acceptance is measurable against the configured threshold, and both template copies are named with an existing parity test.

New internet research was performed for the remaining SPDX/license-token assumptions. Significant findings remain because the revised spec introduces a new compatibility/versioning contradiction around adding default config loading to `extract`/`next`/`upgrade`, and it leaves `extract` semantics internally inconsistent with the current implementation.

### Verdict

Needs major specification correction before planning/implementation

### Audit loop status

* Audit type: Follow-up audit
* Spec path: /home/chris/projects/project-standards/docs/superpowers/specs/2026-07-06-spec-validator-external-references-design.md
* Prior audit issue count: 4
* Resolved issue count: 4
* Still open issue count: 0
* Partially resolved issue count: 0
* New issue count: 2
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

I re-read the revised spec and retested the prior findings against the current repository: config parsing, ID scanning, CLI command wiring, `upgrade` validation/self-validation, `extract`/`next` behavior, template parity tests, Project Specification docs, CI gates, and the release-versioning contract.

I attacked the revised assumptions that adding `--config` to currently configless commands is “unchanged default behavior,” that `extract` can be fixed by passing config-derived prefixes into `parse_document`, that scoped SPDX handling is now documented honestly, and that the v4.1.0 minor-release classification matches the repo’s versioning standard.

I did not run tests or validator commands because the task is read-only and this repository’s normal `uv run` gates can write dependency/cache artifacts. Verification was limited to source, docs, workflow inspection, git inspection, and official SPDX web documentation.

### Prior findings status

#### SA-001: Config-aware references are not specified for `spec upgrade`

* Previous severity: High
* Current status: Resolved
* Evidence: The revised spec explicitly includes `upgrade` in “every ID-consuming command,” adds optional `--config` for `upgrade`, and requires passing prefixes to both source validation and output self-validation at lines 69-80. Acceptance criteria now require a lower-tier spec with `RQ-123` and `spec.reference_prefixes: ["RQ"]` to validate and upgrade cleanly at lines 127-129.
* Remaining action for Claude Code: None for the original `upgrade` omission. Address the new compatibility issue in SA-NEW-001.

#### SA-002: SPDX handling is under-specified and misses real license identifiers

* Previous severity: Medium
* Current status: Resolved
* Evidence: The revised spec now states this is a scoped zero-config promise, not blanket SPDX coverage, and explicitly documents `MIT-0`/`NTP-0` as requiring `reference_prefixes` at lines 38 and 104. Tests are required for zero-config examples and configured `MIT`/`NTP` behavior at line 120.
* Remaining action for Claude Code: None for the original under-specification. Keep the documentation honest that this is not complete SPDX recognition.

#### SA-003: Acceptance criteria do not prove “branch coverage does not regress”

* Previous severity: Low
* Current status: Resolved
* Evidence: Acceptance criteria now say branch coverage stays at or above the configured `fail_under = 85` threshold and explicitly say this is “not a baseline-delta claim” at line 129. Repository config sets `tool.coverage.run.branch = true` and `tool.coverage.report.fail_under = 85` in `pyproject.toml` lines 68-75.
* Remaining action for Claude Code: None.

#### SA-004: Template update target is ambiguous because there are two full-template copies

* Previous severity: Low
* Current status: Resolved
* Evidence: The revised spec names both full-template paths and states they must change together at line 94. Repository evidence confirms `tests/test_spec_packaging.py::test_bundled_template_is_byte_identical` compares all template tiers byte-for-byte between `src/project_standards/specs/templates` and `standards/project-spec/templates` at lines 15-18.
* Remaining action for Claude Code: None.

### New blocking issues

#### SA-NEW-001: Default config loading for previously configless commands conflicts with the versioning contract

* Severity: High
* Status: Confirmed
* Adversarial angle: A claimed backward-compatible minor release can still change default pass/fail behavior for existing CLI commands.
* Spec reference: Line 32 says adding optional `--config` to `extract`, `next`, and `upgrade` has “no changed default behavior.” Lines 75-80 say those commands gain `--config` defaulting to `.project-standards.yml`. Line 141 classifies the release as a backward-compatible minor bump, v4.0.0 to v4.1.0.
* Finding: `extract`, `next`, and `upgrade` currently do not load `.project-standards.yml` at all. Making them load `_DEFAULT_CONFIG` by default can introduce new exit-2 failures for invocations that previously operated only on an explicit spec file, especially when `.project-standards.yml` is unreadable, malformed, or contains an invalid new `spec.reference_prefixes` value. That is not “unchanged default behavior,” and the repo’s versioning standard classifies a validator CLI default change that changes pass/fail behavior as major.
* Repository evidence: Current `_run_extract` parses only `file`, `selector`, and `--json`, then calls `parse_document` directly (`src/project_standards/specs/cli.py` lines 105-112). Current `_run_next` parses only `file`, `prefix`, and `--json`, then calls `parse_document` directly at lines 132-140. Current `_run_upgrade` has no `--config` flag and validates source/output via `parse_document` at lines 472-548. `_DEFAULT_CONFIG` exists at line 48 but is currently used by `validate`/`lint` and `new`, not these three commands. The versioning standard says a validator CLI default changed so pass/fail differs is MAJOR (`meta/versioning.md` lines 102-106), and the previously-passing rule says any change that can turn a previously passing consumer document or workflow run into a failure is MAJOR at lines 112-118.
* External research evidence: Not applicable.
* Why it matters: If Claude Code implements the spec as written, it can ship a behavioral break under a minor release while the repo’s release contract promises `@v4` consumers do not inherit newly failing behavior. This is especially risky because the spec explicitly tells implementers to update `CHANGELOG.md` as v4.1.0.
* Recommended action for Claude Code: Revise the spec to choose one explicit compatibility strategy: make config use opt-in for the newly covered commands, preserve existing default behavior and document when `--config` is required, or acknowledge the default behavior change and re-evaluate whether this must be a major release under `meta/versioning.md`. If the default remains `.project-standards.yml`, the spec should explain why that does not violate the default-change rule.
* Suggested validation: Before implementation, define read-only compatibility cases for `spec extract`, `spec next`, and `spec upgrade` in a repo with an invalid or incompatible `.project-standards.yml`, then decide whether unchanged default invocations must continue to behave as v4.0.0 did.

### New non-blocking issues

#### SA-NEW-002: `extract` is listed as fixed by parse-time skip sets, but its ID selector path does not use `used_ids`

* Severity: Medium
* Status: Confirmed
* Adversarial angle: An acceptance criterion can be written and implemented in a way that does not actually test or change the command behavior it claims to protect.
* Spec reference: Line 75 says `_run_extract` should add `--config` and pass prefixes “so referenced ids aren’t extracted as spec-local.” Lines 123 and 128 require `extract` cases proving `RQ-123` is not extracted as spec-local.
* Finding: Current `extract` behavior for ID selectors is not driven by `doc.used_ids`; it checks whether the selector itself matches `ID_TOKEN`, then searches table rows in raw body text for that selector. Passing `reference_prefixes` into `parse_document` would change `used_ids`, but it would not by itself prevent `extract_slice(doc, "RQ-123")` from returning a row containing `RQ-123`. The spec does not decide whether `extract` should remain a raw selector over any table row, become restricted to spec-local declared IDs, or simply be excluded from config-aware ID parsing because it does not compute ID ownership.
* Repository evidence: `_run_extract` passes the parsed document to `extract_slice` (`src/project_standards/specs/cli.py` lines 105-112). `extract_slice` tests `ID_TOKEN.fullmatch(selector)` and calls `_id_row(body, selector)` (`src/project_standards/specs/commands/extract.py` lines 33-38). `_id_row` searches each table row for the selector string in raw body text at lines 26-30. It does not inspect `doc.used_ids`, `doc.declared_prefixes`, config, or registry ownership.
* External research evidence: Not applicable.
* Why it matters: Claude Code could implement the table row exactly as specified, add a superficial config flag, and still leave `extract` treating external-looking selectors as extractable ID rows. Conversely, changing `extract` to reject external selectors could be a real behavior change to a documented core command. The spec needs to choose the command contract before planning.
* Recommended action for Claude Code: Clarify `extract` semantics. If `extract ID` means “spec-local ID row only,” specify the required ownership check against declared/canonical prefixes and add negative tests for configured external IDs. If `extract` intentionally remains a raw row selector, remove it from the “ID-consuming command” skip-set wiring and acceptance criteria, or rephrase the criterion to avoid claiming config affects extraction.
* Suggested validation: Add a fixture with a table row containing `RQ-123` as an external reference and verify the chosen behavior for `project-standards spec extract RQ-123` with and without `spec.reference_prefixes`.

### Regressions

None found.

### Remaining ambiguities and decisions needed

* Ambiguity: Should `extract`, `next`, and `upgrade` load `.project-standards.yml` by default even though they currently ignore it?
* Why it matters: This decides whether the release remains minor or becomes a default-behavior change under the repo’s versioning contract.
* Recommended clarification: State exact default behavior for each new `--config` flag and reconcile it with `meta/versioning.md`.
* Blocking or non-blocking: Blocking.

* Ambiguity: Is `extract ID` a spec-local ID extractor or a raw table-row selector for any matching token?
* Why it matters: The current implementation is raw row matching; the spec’s config-aware wording implies ownership-aware extraction.
* Recommended clarification: Define the command contract and acceptance tests before implementation.
* Blocking or non-blocking: Non-blocking.

### Internet research performed

* Source name: SPDX License List
* URL: https://spdx.org/licenses/
* Access date: 2026-07-06
* What it was used to verify: Current SPDX identifier source and examples relevant to the spec’s scoped license-token handling.
* Relevant conclusion: The SPDX License List publishes standardized short identifiers and current examples include dotted/versioned identifiers such as `AGPL-3.0-or-later`, `BSD-3-Clause`, and `CC-BY-4.0`; the inspected list reports version `3.28.0 2026-02-20`.

* Source name: SPDX Specification 2.3.0, Annex D: SPDX License Expressions
* URL: https://spdx.github.io/spdx-spec/v2.3/SPDX-license-expressions/
* Access date: 2026-07-06
* What it was used to verify: SPDX license-expression grammar and identifier character assumptions.
* Relevant conclusion: SPDX `idstring` permits letters, digits, hyphens, and dots; license expressions can include identifiers such as `GPL-2.0-only OR BSD-3-Clause`, supporting the revised spec’s statement that it is handling only a scoped subset zero-config.

### Read-only validation performed

* `pwd`: confirmed repository root `/home/chris/projects/project-standards`.
* `git branch --show-current`: confirmed branch `testing`.
* `git status --short`: found existing local modification to `TODO.md` and untracked `docs/codex-reviews/`; audit did not touch them.
* `git log --oneline -n 5`: confirmed latest commit `9f33b96` applied the prior spec-review round.
* `git show --stat --oneline -1`: confirmed the latest commit changed only the spec under audit.
* `nl -ba docs/superpowers/specs/2026-07-06-spec-validator-external-references-design.md`: re-inventoried revised requirements, scope, command wiring, tests, acceptance criteria, and release impact.
* `rg --files src/project_standards tests .github standards/project-spec docs/superpowers/specs meta`: mapped the relevant source, tests, workflows, docs, and versioning files.
* Inspected `src/project_standards/specs/cli.py`: confirmed current `validate`/`lint` and `new` config handling, and confirmed current `extract`/`next`/`upgrade` do not load config.
* Inspected `src/project_standards/specs/config.py`: confirmed current `SpecConfig` has only `include`, `exclude`, and `present`.
* Inspected `src/project_standards/specs/document.py`: confirmed current ID scanning records every `ID_TOKEN` not in `NOT_AN_ID`.
* Inspected `src/project_standards/specs/registry.py`: confirmed `ID_TOKEN`, `NOT_AN_ID`, bundled template registry, and canonical-prefix sources.
* Inspected `src/project_standards/specs/commands/extract.py`: confirmed ID-selector extraction searches raw table rows and does not use `used_ids`.
* Inspected `src/project_standards/specs/commands/next_id.py`: confirmed `next` depends on `doc.used_ids`.
* Inspected `tests/test_spec_packaging.py`: confirmed existing byte-identical parity test for bundled and canonical template copies.
* Inspected `tests/test_spec_config.py`, `tests/test_spec_cli.py`, `tests/test_spec_extract.py`, and `tests/test_spec_next.py`: confirmed current coverage shape for config and command behavior.
* Inspected `.project-standards.yml`: confirmed current dogfood `spec:` block includes only `include`.
* Inspected `standards/project-spec/README.md`: confirmed `extract`, `next`, and `upgrade` are documented core commands and `upgrade` is additive.
* Inspected `.github/workflows/check.yml` and `.github/workflows/validate-specs.yml`: confirmed current CI gates and spec workflow behavior.
* Inspected `pyproject.toml`: confirmed branch coverage and `fail_under = 85`.
* Inspected `meta/versioning.md`: confirmed default behavior changes that can alter pass/fail are classified as MAJOR.
* Performed official web research on SPDX license-list and license-expression behavior.

### Recommended planning/implementation validation

* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest`
* Run only after implementation: `uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`
* Run only after implementation: `uv run project-standards spec validate --config .project-standards.yml`
* Run only after implementation: focused tests for `load_spec_config`, canonical-prefix collision rejection, `parse_document` skip behavior, `validate`, `lint`, `next`, and `upgrade` with configured external references.
* Run only after implementation: compatibility tests for `extract`, `next`, and `upgrade` default behavior in the presence of missing, valid, and invalid `.project-standards.yml`.
* Run only after implementation: an `extract` fixture proving the chosen behavior for external-reference selectors such as `RQ-123`.
* Run only after implementation: package/template parity tests confirming both full-template copies carry the ADR example.

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: /home/chris/projects/project-standards/docs/superpowers/specs/2026-07-06-spec-validator-external-references-design.md
* Audit round: 2
* Open issue IDs: SA-NEW-001, SA-NEW-002
* Resolved issue IDs: SA-001, SA-002, SA-003, SA-004
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: Whether the revised spec reconciles new default config loading with the versioning contract and defines `extract` semantics precisely enough for implementation and tests.