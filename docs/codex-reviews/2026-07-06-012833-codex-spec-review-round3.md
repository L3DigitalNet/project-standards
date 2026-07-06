### Executive summary

Claude Code’s round-2 corrections resolved the two open findings from the prior pass: `upgrade` is now opt-in config-aware rather than default-loading `.project-standards.yml`, and `extract` is explicitly kept as a raw selector instead of being misdescribed as ownership-aware.

Significant findings still remain because the revised spec now overstates `next` compatibility. `next` is not made config-aware, but it still consumes `parse_document(...).used_ids`; the proposed global skip-set and dot-version rule can change `next` output for inputs that include canonical-prefix version-looking tokens. New internet research was performed only to re-check the unchanged SPDX/license-token assumptions.

### Verdict

Needs minor specification correction before planning/implementation

### Audit loop status

* Audit type: Follow-up audit
* Spec path: /home/chris/projects/project-standards/docs/superpowers/specs/2026-07-06-spec-validator-external-references-design.md
* Prior audit issue count: 6
* Resolved issue count: 6
* Still open issue count: 0
* Partially resolved issue count: 0
* New issue count: 1
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

I re-read the revised spec and retested the prior findings against the current repository: `upgrade` CLI wiring, config defaults, `extract` raw-row semantics, `next` use of `doc.used_ids`, config parsing, ID scanning, validation messages, template parity, CI gates, and the versioning contract.

I attacked the revised assumptions that opt-in `upgrade --config` fully resolves the compatibility issue, that leaving `extract` and `next` “untouched” means their behavior is byte-identical to v4.0.0, that the global skip set cannot affect non-validate commands, and that the scoped SPDX handling remains honest.

I did not run tests or validator commands because this audit is read-only and the repository’s usual `uv run` gates may write dependency/cache or coverage artifacts. Verification was limited to source, docs, workflow, git inspection, and official SPDX web documentation.

### Prior findings status

#### SA-001: Config-aware references are not specified for `spec upgrade`

* Previous severity: High
* Current status: Resolved
* Evidence: The spec now includes `upgrade` as the only non-validate/lint pass/fail gate needing resolved prefixes, adds an opt-in `--config`, and requires applying prefixes to both source validation and output self-validation at lines 69-85. Acceptance requires a lower-tier spec with `RQ-123` and `spec.reference_prefixes: ["RQ"]` to validate and `upgrade --config` cleanly at lines 134-136.
* Remaining action for Claude Code: None for the original omission.

#### SA-002: SPDX handling is under-specified and misses real license identifiers

* Previous severity: Medium
* Current status: Resolved
* Evidence: The spec explicitly narrows the zero-config promise to common shapes and documents `MIT-0`/`NTP-0` as requiring `reference_prefixes` at lines 38 and 109. Tests must cover both zero-config examples and configured `MIT`/`NTP` behavior at line 125.
* Remaining action for Claude Code: None for the original scope problem.

#### SA-003: Acceptance criteria do not prove “branch coverage does not regress”

* Previous severity: Low
* Current status: Resolved
* Evidence: Acceptance now requires branch coverage at or above configured `fail_under = 85` at line 137, and `pyproject.toml` sets branch coverage plus `fail_under = 85` at lines 68-75.
* Remaining action for Claude Code: None.

#### SA-004: Template update target is ambiguous because there are two full-template copies

* Previous severity: Low
* Current status: Resolved
* Evidence: The spec names both full-template copies and says both must change together at line 99. `tests/test_spec_packaging.py` already enforces byte identity for all tier templates at lines 15-18.
* Remaining action for Claude Code: None.

#### SA-NEW-001: Default config loading for previously configless commands conflicts with the versioning contract

* Previous severity: High
* Current status: Resolved
* Evidence: The spec no longer default-loads config for `extract`, `next`, or `upgrade`. It leaves `extract`/`next` unflagged and adds only opt-in `upgrade --config`, defaulting to no config load, at lines 75-85. Versioning rationale now classifies `upgrade --config` as a new opt-in flag at lines 149-154.
* Remaining action for Claude Code: None for the default-loading contradiction. Address the new narrower `next` compatibility issue in `SA-NEW-003`.

#### SA-NEW-002: `extract` is listed as fixed by parse-time skip sets, but its ID selector path does not use `used_ids`

* Previous severity: Medium
* Current status: Resolved
* Evidence: The spec now defines `extract ID` as a raw row selector, says it does not consult `used_ids`, `declared_prefixes`, or ownership, and explicitly leaves it unchanged at lines 80-82. Acceptance now says `extract` remains unflagged and byte-identical for the same inputs at line 136.
* Remaining action for Claude Code: None for `extract`.

### New blocking issues

None found.

### New non-blocking issues

#### SA-NEW-003: `next` compatibility promise ignores global parse-time skip effects

* Severity: Medium
* Status: Confirmed
* Adversarial angle: A command can remain configless and still change behavior if a shared parser’s `used_ids` output changes.
* Spec reference: Lines 80-83 say `next` is deliberately not config-aware and “gains nothing from the skip set.” Line 130 says `extract` and `next` are unaffected by config and still return today’s results. Line 136 requires `next` to produce byte-identical results to v4.0.0 for the same inputs.
* Finding: The config-derived skip set does not affect `next`, but the proposed built-in skip rules do. `next` calls `parse_document` and computes the next ID from `doc.used_ids`; the dot-version rule is global and can skip canonical-prefix tokens such as `FR-1.2`, `D-1.0`, or `R-2.0` that v4.0.0 would record as used IDs. That means `next FR`, `next D`, or `next R` can return a different next ID for the same file even though no `--config` flag was added.
* Repository evidence: Current `_run_next` parses the document and passes it to `next_free_id` (`src/project_standards/specs/cli.py` lines 132-140). `next_free_id` reads `doc.used_ids[prefix]` to choose the highest existing number (`src/project_standards/specs/commands/next_id.py` lines 8-18). Current `parse_document` records every `ID_TOKEN` match except prefixes in `NOT_AN_ID` (`src/project_standards/specs/document.py` lines 73-89). The spec’s proposed dot rule would change that shared parser output, including for canonical prefixes.
* External research evidence: Not applicable.
* Why it matters: Claude Code could implement the parser change correctly but still fail the spec’s byte-identical `next` acceptance criterion. Conversely, if it forces byte-identical `next` output, it may need a separate parsing mode that the spec does not describe. The implementation plan needs a precise compatibility target.
* Recommended action for Claude Code: Revise the spec to narrow the `next` compatibility claim. State that `next` remains config-independent and does not read `.project-standards.yml`, but its output may intentionally change when the shared parser stops counting version/SPDX-shaped false positives. If byte-identical output is truly required, specify a parser mode or explicit exception for `next`.
* Suggested validation: Add a focused compatibility test showing `next` ignores missing/malformed config, plus a separate parser-behavior test for canonical-prefix dot-version tokens that documents the intended `next` result.

### Regressions

None found.

### Remaining ambiguities and decisions needed

* Ambiguity: Does `next` need byte-identical v4.0.0 output for every possible same input, or only unchanged config behavior?
* Why it matters: The proposed shared parser skip rules can change `doc.used_ids`, and `next` uses `doc.used_ids` directly.
* Recommended clarification: Replace the byte-identical `next` acceptance criterion with an explicit “does not read config” compatibility criterion, or specify a separate parser mode if byte identity is mandatory.
* Blocking or non-blocking: Non-blocking.

### Internet research performed

* Source name: SPDX License List
* URL: https://spdx.org/licenses/
* Access date: 2026-07-06
* What it was used to verify: Current SPDX identifier examples and zero-version identifiers relevant to the spec’s scoped license-token handling.
* Relevant conclusion: The list publishes standardized short identifiers and currently reports version `3.28.0 2026-02-20`; examples include dotted identifiers such as `AGPL-3.0-or-later`, `BSD-3-Clause`, `CC-BY-4.0`, plus zero-version identifiers `MIT-0` and `NTP-0`.

* Source name: SPDX Specification 2.3.0, Annex D: SPDX License Expressions
* URL: https://spdx.github.io/spdx-spec/v2.3/SPDX-license-expressions/
* Access date: 2026-07-06
* What it was used to verify: SPDX license-expression grammar and identifier character assumptions.
* Relevant conclusion: SPDX `idstring` permits letters, digits, hyphens, and dots, and examples include compound expressions such as `GPL-2.0-only OR BSD-3-Clause`; this supports the spec’s statement that its zero-config behavior is a scoped token-hygiene subset, not full SPDX parsing.

### Read-only validation performed

* `pwd`: confirmed repository root `/home/chris/projects/project-standards`.
* `git branch --show-current`: confirmed branch `testing`.
* `git status --short`: found existing local modification to `TODO.md` and untracked `docs/codex-reviews/`; audit did not touch them.
* `git log --oneline -n 5`: confirmed latest commit `1b3f305` applied the prior spec-review round.
* `git show --stat --oneline -1`: confirmed the latest commit changed only the spec under audit.
* `nl -ba docs/superpowers/specs/2026-07-06-spec-validator-external-references-design.md`: re-inventoried revised requirements, compatibility claims, command wiring, tests, acceptance criteria, and versioning rationale.
* Inspected `src/project_standards/specs/cli.py`: confirmed current `validate`/`lint` and `new` config handling, and confirmed current `extract`/`next`/`upgrade` do not load config.
* Inspected `src/project_standards/specs/config.py`: confirmed current `SpecConfig` has only `include`, `exclude`, and `present`.
* Inspected `src/project_standards/specs/document.py`: confirmed current shared ID scanning feeds `used_ids`.
* Inspected `src/project_standards/specs/registry.py`: confirmed `ID_TOKEN`, `NOT_AN_ID`, template registry, and canonical-prefix sources.
* Inspected `src/project_standards/specs/commands/extract.py`: confirmed `extract` searches raw table rows and does not use ownership.
* Inspected `src/project_standards/specs/commands/next_id.py`: confirmed `next` depends on `doc.used_ids`.
* Inspected `src/project_standards/specs/commands/validate.py`: confirmed validation checks consume `used_ids` for ID findings.
* Inspected `tests/test_spec_packaging.py`: confirmed existing byte-identical parity test for bundled and canonical template copies.
* Inspected `tests/test_spec_config.py`, `tests/test_spec_cli.py`, `tests/test_spec_extract.py`, and `tests/test_spec_next.py`: confirmed current test coverage shape for config and command behavior.
* Inspected `.project-standards.yml`: confirmed current dogfood `spec:` block includes only `include`.
* Inspected `standards/project-spec/README.md`: confirmed current docs describe `extract`, `next`, and `upgrade` as core commands.
* Inspected `.github/workflows/check.yml` and `.github/workflows/validate-specs.yml`: confirmed current CI gates and spec workflow behavior.
* Inspected `pyproject.toml`: confirmed branch coverage and `fail_under = 85`.
* Inspected `meta/versioning.md`: confirmed default pass/fail changes are MAJOR and opt-in flags/config options can be MINOR.
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
* Run only after implementation: focused tests for `load_spec_config`, canonical-prefix collision rejection, parser skip behavior, `validate`, `lint`, `new` self-validation, and `upgrade --config`.
* Run only after implementation: compatibility tests proving `upgrade` without `--config` does not read missing/malformed `.project-standards.yml`.
* Run only after implementation: compatibility tests proving `extract` and `next` do not read config.
* Run only after implementation: a `next` fixture with canonical-prefix dot-version tokens documenting the intended changed or unchanged result.
* Run only after implementation: package/template parity tests confirming both full-template copies carry the ADR example.

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: /home/chris/projects/project-standards/docs/superpowers/specs/2026-07-06-spec-validator-external-references-design.md
* Audit round: 3
* Open issue IDs: SA-NEW-003
* Resolved issue IDs: SA-001, SA-002, SA-003, SA-004, SA-NEW-001, SA-NEW-002
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: Whether the revised spec narrows or explicitly defines `next` compatibility in the presence of shared parser skip-set changes.

