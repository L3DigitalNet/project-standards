### Executive summary

The specification needs correction before Claude Code uses it for planning or implementation. The main blockers are internal contradictions in the dogfood profile, missing acceptance coverage for a `--version` requirement the spec itself makes mandatory, and a false-positive validation path where `docs/usage.md` can be present but not actually frontmatter-validated by this repo’s current config.

Internet research was required because the spec depends on current Python packaging and argparse behavior. Official docs support the entry-point, argparse color/prog, PEP 772, and wheel/man-page assumptions; no major stale-assumption conflict was found externally.

### Verdict

Needs major specification correction before planning/implementation

### Audit loop status

* Audit type: First audit
* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-07-07-cli-documentation-standard-design.md`
* Significant findings remaining: Yes
* Blocking issue count: 3
* Non-blocking issue count: 3

### What the specification gets right

* It correctly identifies the existing `standards/cli-framework/**` exclusion as interim repo state.
* It matches the repo’s adopt-engine shape: registry plus `bundles/<id>/adopt.toml` must stay in parity.
* It correctly avoids adding a reusable `workflow_call` surface for 1.0 and treats the consumer CI as copy-adopt.
* It explicitly calls out adopt overwrite semantics as a required plan-time check before shipping scaffold artifacts.
* It includes release, docs, registry, tests, and handoff touchpoints instead of treating the new standard as only prose.

### Adversarial review performed

I inventoried the spec’s material requirements around bundle layout, adopt-engine registration, dogfood docs, validation gates, release/versioning, acceptance criteria, and external packaging assumptions. I falsified those claims against the current repo config, CLI implementation, registry, adopt engine, manifest tests, packaging tests, README/index docs, and versioning contract.

The strongest assumptions tested were: “project-standards is Packaged, not Packaged-deep”; “the normal pytest gate proves installed-entry-point behavior”; “docs/usage.md will be frontmatter-validated”; “existing manifest tests enforce bundle byte identity”; “v4.3.0 is purely additive”; and “external packaging assumptions are current.”

Could not safely run the full gate, `uv run`, package builds, or validation commands because this audit is read-only and those commands may write caches, build artifacts, coverage data, or dependency state.

### Blocking issues

#### SA-001: Dogfood profile contradicts the standard’s own deep-profile rule

* Severity: High
* Status: Confirmed
* Adversarial angle: Can the spec’s dogfood target satisfy the profile it assigns itself?
* Spec reference: Lines 62, 72-76, 150, 196.
* Finding: The spec classifies `project-standards` as the Packaged profile, but its own profile table says “any second nesting level (subcommand groups)” selects Packaged, deep. The current CLI has top-level `project-standards spec` and nested `project-standards spec {validate|lint|extract|next|new|upgrade}` commands, which is exactly a second nesting level.
* Repository evidence: `pyproject.toml` exposes `project-standards` as a `[project.scripts]` entry point. `src/project_standards/specs/cli.py` declares `_USAGE = "usage: project-standards spec {validate|lint|extract|next|new|upgrade} ..."` and creates nested parsers for those subcommands. The spec itself says `project-standards` has `spec` and `adopt` subcommand groups but still labels it Packaged.
* External research evidence: Python Packaging User Guide confirms `console_scripts` wrappers are created for installed entry points and that the entry-point name is the command name. URL: https://packaging.python.org/en/latest/specifications/entry-points/ Access date: 2026-07-07.
* Why it matters: Claude Code could write a single `docs/usage.md` and acceptance tests for Packaged conformance while the standard’s own rules require generated per-command docs for this repo. That makes the dogfood example either non-conformant or the profile ladder internally incoherent.
* Recommended action for Claude Code: Decide whether `project-standards` is intentionally an exception to Packaged-deep, or revise the profile rule so this CLI remains Packaged. If it is Packaged-deep, update dogfood, layout, acceptance criteria, and tests to require generated per-command docs plus shared concepts.
* Suggested validation: Inspect the implemented docs after revision and verify they satisfy the selected profile’s explicit MUSTs, especially command-depth handling.

#### SA-002: Mandatory `--version` requirement is not carried into implementation scope or acceptance

* Severity: High
* Status: Confirmed
* Adversarial angle: Can acceptance pass while the standard’s base Script-tier MUST is violated?
* Spec reference: Lines 72-74, 150-152, 196-197.
* Finding: The profile ladder says Script MUST include `--help` plus `--version`, and Packaged/Packaged-deep are supersets. But the dogfood section and acceptance criteria only require `project-standards --help` plus one subcommand smoke test. They never require adding or testing `project-standards --version`.
* Repository evidence: `src/project_standards/cli.py` defines the top-level parser and subcommands without any `--version` argument. `rg` found `--version` references in the research draft, but not a top-level implementation or test for `project-standards --version`.
* External research evidence: Not applicable.
* Why it matters: Claude Code can satisfy every written acceptance criterion while shipping a dogfood CLI that violates the standard’s own mandatory base requirement. This undermines the credibility of the new standard and hides a user-visible CLI contract gap.
* Recommended action for Claude Code: Add an explicit decision: either the standard requires `--version` and this work adds/tests it for `project-standards`, or the requirement is softened/excepted with rationale. Reflect that in touchpoints and acceptance criteria.
* Suggested validation: After implementation, run an installed-entry-point smoke test for both `project-standards --help` and `project-standards --version`, asserting exit `0` and the expected release version format.

#### SA-003: `docs/usage.md` can escape frontmatter validation

* Severity: High
* Status: Confirmed
* Adversarial angle: Can “validate-frontmatter passes” be a false positive for the new dogfood doc?
* Spec reference: Lines 153, 168, 196.
* Finding: The spec expects the plan to resolve whether `docs/usage.md` is included in frontmatter validation, but acceptance only says `uv run validate-frontmatter --config .project-standards.yml` passes. The current config does not include `docs/**/*.md` or `docs/usage.md`, so a new `docs/usage.md` could be missing/invalid frontmatter and the cited command would still pass.
* Repository evidence: `.project-standards.yml` includes only `CHANGELOG.md`, `UPGRADING.md`, `standards/**/*.md`, and `meta/**/*.md`; it excludes `docs/handoff/**` but does not include `docs/usage.md`. The spec touchpoint for `.project-standards.yml` only says delete the interim exclude and add `cli_documentation`, not add `docs/usage.md` to the include list.
* External research evidence: Not applicable.
* Why it matters: The dogfood documentation could fail the Markdown Frontmatter Standard while the acceptance gate passes, creating false confidence around the new standard’s example and self-adoption.
* Recommended action for Claude Code: Make the spec require either adding `docs/usage.md` to the frontmatter include set or validating it explicitly with a file/path-specific command. Remove “plan-time question” wording from acceptance-critical behavior.
* Suggested validation: After implementation, run frontmatter validation in a way that demonstrably checks `docs/usage.md`, and include a negative test or explicit config assertion that `docs/usage.md` is in scope.

### Non-blocking issues

#### SA-004: Existing manifest tests do not automatically enforce new bundle byte identity

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Does the claimed test coverage already exist?
* Spec reference: Lines 143, 157.
* Finding: The spec says bundle copies are byte-identical to `standards/` sources and implies existing manifest tests enforce that. Current tests only enforce byte identity for a hardcoded `_DOGFOOD` mapping and a few specific doc fences; they will not automatically compare new `cli-documentation` templates/workflow files to their `standards/` counterparts unless new mappings/tests are added.
* Repository evidence: `tests/test_adopt_dogfood.py` maps only `_shared`, markdown-tooling, python-tooling, and ADR files. `test_every_manifest_source_resolves_to_one_file` checks existence only. `tests/test_adopt_manifest.py` currently expects four released standards.
* External research evidence: Not applicable.
* Why it matters: Manual-copy users and `project-standards adopt cli-documentation` users could receive divergent scaffolds while the existing test suite stays green.
* Recommended action for Claude Code: Update the spec’s test requirements to name the exact byte-identity checks for `templates/usage-doc.md`, `templates/readme-single-file.md`, and `templates/cli-docs-check.yml` against bundled artifact copies.
* Suggested validation: Add a focused test mapping every `standards/cli-documentation/templates/*` file that is shipped via the bundle to its packaged `src/project_standards/bundles/cli-documentation/*` twin.

#### SA-005: Installed-entry-point smoke test is underspecified

* Severity: Medium
* Status: Unclear
* Adversarial angle: Can the smoke test pass without proving a packaged installed wrapper works?
* Spec reference: Lines 73, 152, 160, 197.
* Finding: The research basis requires a clean install and invocation of the installed command, but the design says only “subprocess `project-standards --help` + one subcommand” inside the normal pytest gate. That may exercise the local development environment rather than a freshly built/installed wheel or tool install.
* Repository evidence: `tests/test_adopt_packaging.py` builds a wheel and checks bundle contents, but does not run the installed `project-standards` entry point from that wheel. The current spec does not state whether the new smoke test should use a built wheel, a temp venv, `uv tool install`, or the ambient `uv run` environment.
* External research evidence: Python Packaging User Guide confirms installers create command wrappers for `console_scripts`; Python argparse docs note `prog` defaults depend on how the program was invoked, making wrapper-vs-module invocation observable. URLs: https://packaging.python.org/en/latest/specifications/entry-points/ and https://docs.python.org/3.14/library/argparse.html Access date: 2026-07-07.
* Why it matters: A direct subprocess in the dev env can miss broken entry-point metadata, broken wheel packaging, or `prog` differences that only appear through the installed wrapper.
* Recommended action for Claude Code: Specify the intended smoke mechanism. If the requirement is truly “installed entry point,” require a temp install from the built wheel or another isolated installed-command proof.
* Suggested validation: After implementation, build the wheel into a temp directory, install into an isolated env, then run `project-standards --help`, `project-standards --version`, and one representative subcommand.

#### SA-006: “No `cli-framework/` path remains anywhere” is overbroad

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Can acceptance force unrelated historical-doc churn?
* Spec reference: Lines 107, 186.
* Finding: The acceptance criterion says no `cli-framework/` path remains anywhere in code, config, docs, or workflows. Current repo evidence includes historical/spec/research/TODO references to the old path. Some should be updated, but “anywhere in docs” is broader than necessary and could force edits to historical research, review logs, or audit artifacts where old-path provenance is legitimate.
* Repository evidence: `rg` finds `standards/cli-framework/...` in the target spec, the research document’s `related`/intro, and TODO phase history, among other docs. Git history is explicitly part of the provenance in the spec.
* External research evidence: Not applicable.
* Why it matters: Overbroad acceptance either fails forever on legitimate provenance references or encourages noisy historical rewrites unrelated to the standard’s functional adoption.
* Recommended action for Claude Code: Narrow the criterion to active source-of-truth references: code, config, bundle manifests, current consumer docs, current README/index/adopt docs, and non-historical handoff pointers. Permit historical/provenance references where explicitly labeled.
* Suggested validation: Use an `rg` sweep after implementation, classify remaining hits as active stale references vs. historical provenance, and fail only on active stale references.

### Missing specification considerations

* Dogfood profile selection: Blocking. The spec must reconcile the `project-standards` CLI’s second nesting level with the Packaged-deep rule.
* `--version` behavior: Blocking. The spec must decide whether to add/test `project-standards --version` or weaken the MUST.
* `docs/usage.md` validation scope: Blocking. The spec must require concrete inclusion or explicit validation.
* Installed-wrapper proof: Non-blocking but important. The smoke test should define whether it proves an installed wheel/tool wrapper or only the dev environment.
* Byte-identity testing for new bundle artifacts: Non-blocking. The spec should require explicit tests rather than relying on current generic tests.
* Active-vs-historical stale path policy: Non-blocking. The `cli-framework` sweep should be scoped to avoid unnecessary historical-doc churn.
* Release compatibility of `cli_documentation.version`: Non-blocking but should be clarified. The spec should explain why adding validation for a previously ignored top-level config key remains safe under the previously-passing rule, or document any migration concern.

### Ambiguities and decisions needed

* Ambiguity: Is `project-standards` Packaged or Packaged-deep under the proposed standard?
* Why it matters: It changes required docs layout, generation tooling, acceptance criteria, and dogfood claims.
* Recommended clarification: State the selected profile and either comply with or revise the second-nesting-level rule.
* Blocking or non-blocking: Blocking.

* Ambiguity: Does this work add `project-standards --version`?
* Why it matters: The standard requires it, but the implementation scope omits it.
* Recommended clarification: Add a touchpoint and acceptance test for `--version`, or revise the profile MUST.
* Blocking or non-blocking: Blocking.

* Ambiguity: How exactly is `docs/usage.md` frontmatter-validated?
* Why it matters: Current config would not validate it.
* Recommended clarification: Require adding `docs/usage.md` to `.project-standards.yml` include or validating it explicitly.
* Blocking or non-blocking: Blocking.

* Ambiguity: What counts as an installed-entry-point smoke test?
* Why it matters: Ambient subprocess execution may not prove wheel/entry-point installation.
* Recommended clarification: Specify temp wheel install/tool install vs. dev-env invocation.
* Blocking or non-blocking: Non-blocking.

### Internet research performed

* Source name: Python 3.14 argparse documentation
* URL: https://docs.python.org/3.14/library/argparse.html
* Access date: 2026-07-07
* What it was used to verify: `argparse.ArgumentParser` color default, `prog` behavior, and invocation-sensitive help output.
* Relevant conclusion: Supports the spec’s need to normalize color and be explicit about `prog`.

* Source name: Python Packaging User Guide, Entry points specification
* URL: https://packaging.python.org/en/latest/specifications/entry-points/
* Access date: 2026-07-07
* What it was used to verify: `console_scripts` / installed wrapper behavior.
* Relevant conclusion: Supports using installed entry-point names as the user-facing command contract.

* Source name: Python Packaging User Guide, Binary distribution format
* URL: https://packaging.python.org/en/latest/specifications/binary-distribution-format/
* Access date: 2026-07-07
* What it was used to verify: Wheel `.data` layout and install-scheme limitations.
* Relevant conclusion: Supports the spec’s “man page best effort” direction; wheel install paths are scheme-key based and do not define arbitrary system locations.

* Source name: setuptools Data Files Support
* URL: https://setuptools.pypa.io/en/latest/userguide/datafiles.html
* Access date: 2026-07-07
* What it was used to verify: Data-file reliability and recommended package-resource approach.
* Relevant conclusion: Supports caution around non-package data files; official docs recommend package-internal resources for runtime data and state no reliable facility for non-package data retrieval.

* Source name: PEP 772
* URL: https://peps.python.org/pep-0772/
* Access date: 2026-07-07
* What it was used to verify: Packaging Council governance status and date.
* Relevant conclusion: Confirms PEP 772 is accepted and last modified/resolved on 2026-04-16.

### Items Claude Code should verify before correcting the specification

* Whether the intended dogfood profile is Packaged or Packaged-deep.
* Whether `project-standards --version` should be added to the CLI as part of this work.
* Whether `docs/usage.md` should be added to `.project-standards.yml` include globs or validated by an explicit file command.
* Whether the installed-entry-point smoke test should build/install a wheel in a temp environment.
* Whether adding `cli_documentation.version` validation can newly fail any known consumer configs or needs release-note wording.
* Which remaining `cli-framework` references after implementation are active stale references versus historical provenance.

### Suggested corrections for Claude Code’s specification

* Reconcile `project-standards` with the Packaged-deep rule or revise the rule.
* Add explicit `--version` scope and acceptance criteria, or remove/soften the MUST.
* Make `docs/usage.md` validation concrete instead of plan-time.
* Specify the installed-entry-point smoke-test mechanism.
* Add explicit byte-identity tests for all new copied bundle artifacts.
* Narrow the `cli-framework` sweep criterion to active references.
* Add validator tests for `cli_documentation.version`: known version silent, unknown version exit `2`, non-string version exit `2`, registry default included, and dogfood config selects `1.0`.

### Read-only validation performed

* Inspected the spec file with `sed`/`nl`: inventoried requirements, acceptance criteria, profile rules, dogfood claims, release claims, and touchpoints.
* Ran `git status --short`, `git branch --show-current`, `git log --oneline -n 10`, and `git diff --stat`: confirmed branch `testing`, recent spec commits, and no local diff output.
* Listed repo files with `rg --files`: confirmed current standards, source, tests, bundle, research, and handoff surfaces.
* Inspected `.project-standards.yml`: confirmed `docs/usage.md` is not currently in validation include globs.
* Inspected `src/project_standards/cli.py`, `src/project_standards/specs/cli.py`, and `pyproject.toml`: confirmed entry-point shape, nested `spec` command group, registry parity hooks, and no top-level `--version` implementation.
* Inspected `src/project_standards/registry.py` and `src/project_standards/validate_frontmatter.py`: confirmed current hardcoded contract-version fields and metadata validation only for python/markdown tooling.
* Inspected adopt tests and packaging tests: confirmed existing four-standard expectations and hardcoded byte-identity coverage that will not automatically cover the new standard.
* Searched for `cli-framework`, `cli-documentation`, `cli_documentation`, and `--version`: confirmed stale-path surfaces and missing implementation coverage.
* Inspected `meta/versioning.md`, `README.md`, `standards/README.md`, `TODO.md`, and research docs: checked release classification, standard count, bundle anatomy, and source assumptions.
* Consulted official external docs listed above for argparse, entry points, wheel layout, setuptools data files, and PEP 772.

### Recommended planning/implementation validation

* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest`
* Run only after implementation: `uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run pytest tests/coherence`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`, with proof that `docs/usage.md` is included.
* Run only after implementation: `project-standards adopt cli-documentation --dry-run` or an equivalent isolated CLI test proving the three artifacts and fragment.
* Run only after implementation: build/install an isolated package artifact and smoke `project-standards --help`, `project-standards --version`, and one nested subcommand via the installed wrapper.
* Run only after implementation: `rg -n "cli-framework"` and classify any remaining hits as active stale references or historical provenance.
* Run only after implementation: package-content check that the `cli-documentation` bundle files and manifest are included in the wheel.

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-07-07-cli-documentation-standard-design.md`
* Audit round: 1
* Open issue IDs: SA-001, SA-002, SA-003, SA-004, SA-005, SA-006
* Resolved issue IDs:
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: dogfood profile/profile ladder consistency, `--version` scope, `docs/usage.md` validation proof, installed-wrapper smoke specificity, byte-identity tests, and narrowed stale-path acceptance.

