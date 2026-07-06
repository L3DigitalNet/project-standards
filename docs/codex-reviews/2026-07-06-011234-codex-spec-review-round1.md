### Executive summary

The specification is not ready for Claude Code to use as the basis for planning or implementation. It correctly identifies the current validator’s core two-bucket parsing problem, but it leaves one core command path (`spec upgrade`) outside the new config-aware parsing model while also claiming no CLI-surface change and preserving tier-upgrade guarantees. That is a blocking repo-fit gap.

Internet research was required for the SPDX/license-token assumptions. Official SPDX sources confirm the spec’s dot-version handling covers many identifiers, but the proposed denylist/dot-rule combination still misses real SPDX identifiers such as `MIT-0` and `NTP-0`.

### Verdict

Needs major specification correction before planning/implementation

### Audit loop status

* Audit type: First audit
* Spec path: /home/chris/projects/project-standards/docs/superpowers/specs/2026-07-06-spec-validator-external-references-design.md
* Significant findings remaining: Yes
* Blocking issue count: 1
* Non-blocking issue count: 3

### What the specification gets right

* It correctly narrows the change to the Project Specification validator ID scan and associated docs/tests.
* It matches the current repo shape: `config.py`, `registry.py`, `document.py`, `commands/validate.py`, bundled templates, and `standards/project-spec/README.md` all exist.
* It correctly identifies that current `parse_document` records any `ID_TOKEN` match unless its prefix is in `NOT_AN_ID`.
* It preserves the fixed spec-local ID widths and rejects using config to disable canonical spec-local prefixes.
* It includes focused unit and integration tests for config parsing, skip behavior, boundary punctuation, and error text.

### Adversarial review performed

I inventoried the spec’s requirements, then checked them against the current CLI/config/document/registry/validator implementation, project-spec docs, workflow config, templates, test coverage, changelog, and versioning contract. I attacked the strongest claims: “validate/lint wiring is sufficient,” “this change only loosens,” “license identifiers are handled,” “no CLI-surface change,” “dogfood validation proves success,” and “minor release is correct.”

I could not run validation or test commands because the environment is read-only and `uv run` attempted to create cache temp files. I therefore limited verification to source/docs/workflow inspection and official web documentation.

### Blocking issues

#### SA-001: Config-aware references are not specified for `spec upgrade`

* Severity: High
* Status: Confirmed
* Adversarial angle: A spec can pass the new `validate` path but still fail a core Project Specification command because the spec only wires config references into `validate` and `lint`.
* Spec reference: Lines 65-67 specify passing `SpecConfig` reference prefixes only from `validate` and `lint`; line 32 says “No CLI-surface change”; lines 82-87 preserve registry/template invariants; lines 100-104 acceptance criteria omit `upgrade`.
* Finding: The design does not say how `project-standards spec upgrade` will handle configured external references. Current `upgrade` has no `--config` option and validates both source and output using `validate_document(parse_document(...), reg)` with no config-derived skip set. A Light/Standard spec containing configured external references like `RQ-123` could validate clean after this feature, then fail `upgrade` as `source_invalid` or `self_validation_failed`.
* Repository evidence: `spec upgrade` is a core authoring command in the standard docs, described as additive tier promotion with no reference rewrites (`standards/project-spec/README.md` lines 160-163). The current CLI validates upgrade source at `src/project_standards/specs/cli.py` lines 505-518 and validates upgraded output at lines 537-548, both through `parse_document` without config. The command table includes `upgrade` as a live verb at lines 560-567. Current `parse_document` accepts only `(path, text)` and records every non-denylisted `ID_TOKEN` at `document.py` lines 73-88.
* External research evidence: Not applicable.
* Why it matters: The Project Specification standard’s tier interchangeability guarantee is part of the product contract. If Claude Code implements the spec as written, users can get a contradictory state: “this spec validates” but “this valid spec cannot upgrade.” The spec also blocks the obvious fix by asserting no CLI-surface change without deciding an alternative.
* Recommended action for Claude Code: Extend the specification to cover every command that validates or parses IDs for command semantics, especially `upgrade`. Decide whether `upgrade` gains `--config`, reads the default config, accepts reference prefixes some other way, or explicitly forbids configured references during upgrade with a documented tradeoff. The first two options are more consistent with the existing standard.
* Suggested validation: Add an implementation validation case where a lower-tier spec containing `RQ-123` with `spec.reference_prefixes: ["RQ"]` validates and upgrades successfully, including output self-validation.

### Non-blocking issues

#### SA-002: SPDX handling is under-specified and misses real license identifiers

* Severity: Medium
* Status: Confirmed
* Adversarial angle: The acceptance criteria can pass for `MPL-2.0`/`GPL-3` while other legitimate SPDX identifiers still fail the ID scanner.
* Spec reference: Lines 38 and 56-63 define the SPDX/license handling as a dot-version shape rule plus denylist prefixes `GPL LGPL AGPL MPL BSD EPL BY`; line 80 says to document “license-token handling”; line 102 accepts a minimal repro with “a license id.”
* Finding: The proposed rules do not fully define the intended license-token scope. They cover many dotted SPDX identifiers, but real SPDX short identifiers such as `MIT-0` and `NTP-0` match the repo’s `ID_TOKEN` shape and are not covered by the dot rule or listed denylist. Under the proposed design they would still become spec-local ID candidates and fail width/declaration checks.
* Repository evidence: `ID_TOKEN` is `\b([A-Z]{1,4})-([0-9]+)\b` in `registry.py` line 20. `NOT_AN_ID` currently omits `MIT` and `NTP` at lines 21-42. `document.py` lines 83-88 would record these matches unless skipped.
* External research evidence: Official SPDX License List says it provides standardized short identifiers and permanent URLs; the list version inspected is `3.28.0 2026-02-20` (SPDX License List, https://spdx.org/licenses/, accessed 2026-07-06). SPDX pages identify `MIT-0` and `NTP-0` as short identifiers (https://spdx.org/licenses/MIT-0.html and https://spdx.org/licenses/NTP-0.html, accessed 2026-07-06).
* Why it matters: A partial hardcoded denylist creates false confidence: the named license repro passes, but consumers still hit the same bug with other valid license identifiers. It also makes future SPDX additions a maintenance hazard.
* Recommended action for Claude Code: Clarify whether the feature promises only the known issue’s license examples or robust SPDX-token hygiene. If robust, prefer a shape-based rule that covers SPDX-like version suffixes without enumerating families, or explicitly include a documented denylist maintenance strategy and tests for zero-version identifiers such as `MIT-0` and `NTP-0`.
* Suggested validation: Add tests proving `MIT-0`, `NTP-0`, `BSD-3-Clause`, `GPL-3.0-or-later`, `MPL-2.0`, and `CC-BY-4.0` are not recorded as spec-local IDs, while a true spec-local ID at sentence end remains recorded.

#### SA-003: Acceptance criteria do not prove “branch coverage does not regress”

* Severity: Low
* Status: Confirmed
* Adversarial angle: A stated quality gate can pass without proving the property it claims.
* Spec reference: Line 103 says the full Python gate must be green and “branch coverage does not regress.”
* Finding: The listed command sequence runs coverage and reports against the configured threshold, but it does not compare branch coverage against a baseline. The repo config enables branch coverage and `fail_under = 85`, but that is not the same as detecting regression from the previous branch-coverage percentage.
* Repository evidence: `pyproject.toml` lines 68-75 enables branch coverage, reports coverage, and enforces total `fail_under = 85`. The Check workflow runs `coverage run -m pytest` and `coverage report` at `.github/workflows/check.yml` lines 41-45, with no baseline comparison.
* External research evidence: Not applicable.
* Why it matters: Claude Code could reduce branch coverage while staying above the threshold and still satisfy the written acceptance command.
* Recommended action for Claude Code: Either remove the “does not regress” wording or define how to compare against the baseline branch coverage from the current branch/main. Keep the existing threshold gate as the minimum.
* Suggested validation: Record the pre-change `coverage report` branch/total values, rerun after implementation, and explicitly compare them, or revise the acceptance criterion to “coverage remains above the configured threshold.”

#### SA-004: Template update target is ambiguous because there are two full-template copies

* Severity: Low
* Status: Confirmed
* Adversarial angle: A docs/template acceptance check could update only one copy and leave the shipped package or standard docs stale.
* Spec reference: Line 32 names “the shipped `spec-full-template.md`”; line 79 says “Template”; line 115 says update “the `spec-full-template.md` example row.”
* Finding: The repository has both the runtime bundled template under `src/project_standards/specs/templates/spec-full-template.md` and the standard distribution copy under `standards/project-spec/templates/spec-full-template.md`. The spec does not explicitly say both must be updated or how parity is verified.
* Repository evidence: Both files exist and currently contain the same §8.3 row with `<link if durable>` at `src/.../spec-full-template.md` lines 243-247 and `standards/.../spec-full-template.md` lines 243-247. The runtime registry uses `src/project_standards/specs/templates` via `registry.py` lines 11-16.
* External research evidence: Not applicable.
* Why it matters: Updating only the docs copy would not affect `project-standards spec new`; updating only the bundled copy would leave published standard docs stale. The acceptance criteria do not force parity.
* Recommended action for Claude Code: Name both template paths explicitly and add a parity/conformance validation expectation.
* Suggested validation: Add or reuse a test/inspection that verifies the §8.3 ADR example is present in both template locations, and that the bundled template still passes template conformance.

### Missing specification considerations

* Blocking: Config-aware behavior for `spec upgrade`, including whether the command accepts `--config`, reads `.project-standards.yml`, or has another explicit contract.
* Non-blocking: SPDX/license-token scope. The spec should decide whether it handles only reported examples or all SPDX-looking identifiers that collide with `ID_TOKEN`.
* Non-blocking: Concrete baseline method for “branch coverage does not regress.”
* Non-blocking: Explicit update targets for both bundled and docs template copies.
* Non-blocking: JSON output/error-message expectations. The spec changes `SV-ID-UNDECLARED` text but does not state whether tests should cover human output, JSON payloads, or both.
* Non-blocking: Consumer docs should show a `.project-standards.yml` example with `spec.reference_prefixes`, not only prose.

### Ambiguities and decisions needed

* Ambiguity: Should `spec upgrade` consume `spec.reference_prefixes`?
* Why it matters: Without this decision, a spec can validate but fail tier promotion.
* Recommended clarification: Specify exact `upgrade` config behavior and tests.
* Blocking or non-blocking: Blocking.

* Ambiguity: Is SPDX handling example-specific or intended to be robust for the SPDX License List?
* Why it matters: Hardcoded family prefixes miss real identifiers.
* Recommended clarification: Define supported license-token shapes and include representative official SPDX examples.
* Blocking or non-blocking: Non-blocking.

* Ambiguity: Which `spec-full-template.md` is “the shipped” template?
* Why it matters: Runtime scaffolding and published docs are separate files.
* Recommended clarification: List both paths or state the synchronization mechanism.
* Blocking or non-blocking: Non-blocking.

### Internet research performed

* Source name: SPDX Specification 2.3.0, Annex D: SPDX License Expressions
* URL: https://spdx.github.io/spdx-spec/v2.3/SPDX-license-expressions/
* Access date: 2026-07-06
* What it was used to verify: SPDX expression grammar and examples.
* Relevant conclusion: SPDX license identifiers can include letters, digits, hyphens, and dots; examples include dotted/versioned identifiers and compound expressions, so license-token handling should not rely only on a few examples.

* Source name: SPDX License List
* URL: https://spdx.org/licenses/
* Access date: 2026-07-06
* What it was used to verify: Current SPDX license-list purpose and version.
* Relevant conclusion: The SPDX License List publishes standardized short identifiers and was at version `3.28.0 2026-02-20`.

* Source name: SPDX MIT-0 license page
* URL: https://spdx.org/licenses/MIT-0.html
* Access date: 2026-07-06
* What it was used to verify: Whether `MIT-0` is a real SPDX short identifier.
* Relevant conclusion: `MIT-0` is a real SPDX short identifier and is not covered by the spec’s proposed denylist/dot rule.

* Source name: SPDX NTP-0 license page
* URL: https://spdx.org/licenses/NTP-0.html
* Access date: 2026-07-06
* What it was used to verify: Whether `NTP-0` is a real SPDX short identifier.
* Relevant conclusion: `NTP-0` is a real SPDX short identifier and is not covered by the spec’s proposed denylist/dot rule.

* Source name: GitHub issue #3
* URL: https://github.com/L3DigitalNet/project-standards/issues/3
* Access date: 2026-07-06
* What it was used to verify: The downstream issue details referenced by the spec.
* Relevant conclusion: Could not verify from the available web result; repository evidence and the spec text were used instead.

### Items Claude Code should verify before correcting the specification

* Reproduce the current `upgrade` failure mode with a lower-tier spec containing an external configured prefix, without writing artifacts.
* Confirm whether project-spec consumers are expected to use `upgrade` with config-scoped specs.
* Confirm desired SPDX support scope: reported examples only, broad SPDX identifier hygiene, or a narrower documented set.
* Confirm whether docs/template parity is already enforced elsewhere or needs an explicit test.
* Confirm whether the release should remain `v4.1.0` after any `upgrade` CLI/config decision.

### Suggested corrections for Claude Code’s specification

* Add a section covering every command affected by config-aware ID parsing: `validate`, `lint`, and `upgrade` at minimum.
* Resolve the `upgrade` config contract and update acceptance criteria with an upgrade fixture containing configured external references.
* Replace or supplement the SPDX denylist with a documented strategy that covers real non-dotted identifiers like `MIT-0` and `NTP-0`, or explicitly narrow the promise.
* Name both template paths that must change: `src/project_standards/specs/templates/spec-full-template.md` and `standards/project-spec/templates/spec-full-template.md`.
* Make the coverage acceptance criterion measurable or remove the “does not regress” phrase.
* Add validation expectations for JSON output if the changed `SV-ID-UNDECLARED` message is part of the machine-readable contract.
* Include a config example in the standard docs for `spec.reference_prefixes`.

### Read-only validation performed

* `pwd`: confirmed repository root `/home/chris/projects/project-standards`.
* `git branch --show-current`: confirmed branch `testing`.
* `git status --short`: found existing local modification to `TODO.md`; audit did not touch it.
* `git log --oneline -n 10`: confirmed latest commit is the spec under audit.
* `sed -n` / `nl -ba` on the spec: inventoried requirements, scope, decisions, tests, acceptance criteria, and release impact.
* `rg --files src/project_standards tests .github standards/project-spec`: mapped relevant repository surfaces.
* Inspected `src/project_standards/specs/config.py`: confirmed current `SpecConfig` has only `include`, `exclude`, and `present`.
* Inspected `src/project_standards/specs/registry.py`: confirmed `ID_TOKEN`, `NOT_AN_ID`, template registry, and canonical prefix derivation.
* Inspected `src/project_standards/specs/document.py`: confirmed current ID scan skips only `NOT_AN_ID`.
* Inspected `src/project_standards/specs/cli.py`: confirmed `validate`/`lint` parse via config paths, `upgrade` validates source/output without config, and `upgrade` is a live verb.
* Inspected `src/project_standards/specs/commands/validate.py`: confirmed ID format, undeclared-prefix, tier, and duplicate-definition checks.
* Inspected `src/project_standards/specs/commands/next_id.py` and `extract.py`: checked secondary parse consumers.
* Inspected `.project-standards.yml`: confirmed current dogfood spec include points to `standards/project-spec/examples/**/*.md`.
* Inspected `standards/project-spec/README.md`: confirmed `upgrade` is documented as core and additive, and update cadence includes tooling/template changes.
* Inspected both full-template copies: confirmed both currently have the §8.3 ADR placeholder row.
* Inspected `.github/workflows/check.yml` and `validate-specs.yml`: confirmed current CI gates and spec workflow behavior.
* Inspected `pyproject.toml`: confirmed branch coverage is enabled with a total threshold but no baseline-regression comparison.
* Inspected `CHANGELOG.md` and `meta/versioning.md`: checked versioning and release-impact claims.
* Attempted `uv run python - ...`: could not run because `uv` attempted to create a cache temp file on a read-only filesystem.
* Attempted `PYTHONPATH=src python - ...`: repository wrapper refused direct `python -` and instructed use of `uv run`.
* Performed official web research on SPDX license-expression and license-list behavior.

### Recommended planning/implementation validation

* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest`
* Run only after implementation: `uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`
* Run only after implementation: `uv run project-standards spec validate --config .project-standards.yml`
* Run only after implementation: focused tests for `load_spec_config`, `parse_document` skip behavior, `validate`, `lint`, and `upgrade` with configured external references.
* Run only after implementation: package/template tests that confirm both bundled and standards template copies carry the ADR example.
* Run only after implementation: a coverage baseline comparison if “branch coverage does not regress” remains an acceptance criterion.

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: /home/chris/projects/project-standards/docs/superpowers/specs/2026-07-06-spec-validator-external-references-design.md
* Audit round: 1
* Open issue IDs: SA-001, SA-002, SA-003, SA-004
* Resolved issue IDs:
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: Whether the revised spec resolves `upgrade` config handling, tightens SPDX-token scope, makes coverage acceptance measurable, and names both template update targets.

