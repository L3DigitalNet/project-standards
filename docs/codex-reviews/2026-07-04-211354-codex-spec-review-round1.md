### Executive summary

The specification is not ready for Claude Code to use as the basis for planning or implementation. The core direction fits the repository, but several contract-level ambiguities would let an implementation choose incompatible behavior for `validate` vs `lint`, pass CI without checking any specs, or accept unfilled templates as valid consumer specs.

Internet research was required for the `uv_build` packaging assumption. Official uv documentation supports the spec’s safe default of copying template Markdown under the Python module tree, but the unresolved packaging question should still be closed before implementation.

### Verdict

Needs major specification correction before planning/implementation

### Audit loop status

* Audit type: First audit
* Spec path: /home/chris/projects/project-standards/docs/superpowers/specs/2026-07-04-project-spec-tooling-design.md
* Significant findings remaining: Yes
* Blocking issue count: 3
* Non-blocking issue count: 4

### What the specification gets right

* Correctly separates read-only commands from future mutating `new` / `upgrade` work.
* Correctly identifies `check_specs.py` as a maintainer-template validator, not consumer tooling.
* Correctly follows the existing package shape: `src/project_standards/`, `project-standards` console script, reusable workflows, and wheel-bundled data.
* Correctly calls out non-UTF-8 / malformed input tracebacks as a class to avoid.

### Adversarial review performed

I challenged the consumer-vs-maintainer validation boundary, no-arg discovery and CI behavior, hard vs advisory rule placement, template packaging assumptions, current repository config shape, existing CLI dispatch patterns, `check_specs.py` parity claims, and whether acceptance criteria can pass without proving the intended contract.

I could not run `check_specs.py` through the repository’s preferred `uv run` path because `uv run` can write caches/environments in this read-only audit mode. A direct `python3` invocation was refused by the local wrapper.

### Blocking issues

#### SA-001: Consumer `validate` conflicts with template sentinel semantics

* Severity: High
* Status: Confirmed
* Adversarial angle: A CI gate could pass an unfilled template, or a dogfood test could require behavior that contradicts the standard.
* Spec reference: `Component 3`, `Component 4`, `Testing`, and `Acceptance criteria`: lines 47, 104-112, 121-122, 162, 169.
* Finding: The spec says the real consumer `validate` should pass on all three bundled templates, while the standard says `SPEC-____` is intentionally invalid and must fail validation until filled in. The spec also puts “leftover sentinel” under advisory `lint`, which conflicts with G7’s “sentinel spec_id fails validation until it is filled in.”
* Repository evidence: `standards/project-spec/README.md` says G7 includes a sentinel that fails validation until filled in. `standards/project-spec/resources/tooling-notes.md` says `SPEC-____` is intentionally invalid so a validator rejects an unfilled template. The templates currently contain `spec_id: SPEC-____`. `check_specs.py` is template-specific and expects the sentinel, so its behavior cannot be replaced by consumer `validate` without a separate mode or contract.
* External research evidence: Not applicable.
* Why it matters: Claude Code cannot reliably plan the validator until the spec decides whether `validate` rejects unfilled consumer specs. As written, acceptance criteria can pass while CI accepts placeholder specs.
* Recommended action for Claude Code: Split “template conformance” from “consumer spec validation.” Keep consumer `validate` rejecting `SPEC-____`; add a separate maintainer/template test or helper that permits the sentinel only for canonical templates.
* Suggested validation: Add fixtures proving `project-standards spec validate unfilled-template.md` exits `1`, while the template-maintainer test still proves the shipped templates are structurally interchangeable.

#### SA-002: Missing or empty `spec:` discovery behavior is undefined

* Severity: High
* Status: Confirmed
* Adversarial angle: The reusable CI workflow could pass without validating any spec files.
* Spec reference: Config and CI sections: lines 132-145, 164, 175, plus non-goals at 180-183 and 190.
* Finding: The spec says no-arg `validate` / `lint` use the `spec:` include set and that a `validate-specs.yml` workflow runs `project-standards spec validate`, but it does not define what happens when `spec:` is missing or resolves to zero files. Adoption wiring that would write the starter `spec:` block is explicitly out of scope.
* Repository evidence: Current `.project-standards.yml` has `markdown.frontmatter.include/exclude`, `python_tooling`, and `markdown_tooling`, but no `spec:` block. The current config loader pattern defaults missing known sections rather than failing merely because an unrelated top-level key is absent.
* External research evidence: Not applicable.
* Why it matters: A green CI job that checked zero specs is worse than no job; it creates false confidence and weakens the standard’s core promise.
* Recommended action for Claude Code: Define no-arg behavior explicitly. For example: missing `spec:` with no explicit paths exits `2`; an include set resolving to zero files exits `1` or `2` with a clear message; explicit file args bypass config discovery.
* Suggested validation: Add tests for missing `spec:`, empty include list, unmatched include glob, excludes removing all files, and explicit path args without a config block.

#### SA-003: ID registry and uniqueness rules are split between hard and advisory checks

* Severity: High
* Status: Confirmed
* Adversarial angle: Duplicate or undeclared IDs could pass the hard gate if only `validate` runs in CI.
* Spec reference: Lines 104, 121-122, 126, 170.
* Finding: Component 3 says `Appendix-A used ⊆ declared` is part of the per-file checks reproduced by `validate`, but Component 4 assigns `used ⊆ declared` and per-spec ID uniqueness to advisory `lint`, whose default exit code is always `0`.
* Repository evidence: `check_specs.py` treats an undeclared used prefix as a hard problem. Tooling notes say the parser should parse Appendix A and assert it matches the canonical map. The standard’s G4 requires stable, typed IDs; duplicate IDs make references ambiguous.
* External research evidence: Not applicable.
* Why it matters: If `validate-specs.yml` only runs `spec validate`, a spec with `ZZ-001` or duplicate `FR-001` can pass unless CI also opts into strict lint.
* Recommended action for Claude Code: Move ID uniqueness, used-prefix declaration, and Appendix-A “Defined In” compatibility into `validate`. Keep `lint` for placeholders, template guidance, and authoring-quality warnings.
* Suggested validation: Add invalid fixtures for duplicate `FR-001`, unknown prefix `ZZ-001`, prefix declared with wrong `Defined In`, and a tier using a prefix not allowed for that profile; all should make `validate` exit `1`.

### Non-blocking issues

#### SA-004: Approved Light traceability is underspecified

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Profile-agnostic lint can either falsely fail Light specs or silently skip traceability.
* Spec reference: `lint` behavior and acceptance criteria: lines 122 and 170.
* Finding: The spec says an approved spec must map every `Must` in §17.3, but Light explicitly omits §17.3.
* Repository evidence: `spec-light-template.md` says §17.2 and §17.3 are Standard-tier and only §17.1 exists; Standard and Full contain §17.3 traceability matrices.
* External research evidence: Not applicable.
* Why it matters: Claude Code will have to invent how `lint` handles approved Light specs.
* Recommended action for Claude Code: Define Light-profile traceability semantics, such as checking §17.1’s verification checklist or requiring upgrade to Standard before `approved`.
* Suggested validation: Add an approved Light fixture with Must requirements and define whether it passes, warns, or fails.

#### SA-005: `--json` is required but its schema is not specified

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Any syntactically valid JSON could satisfy acceptance without being useful to agents or CI.
* Spec reference: Lines 56, 117, 168, 196.
* Finding: `--json` is part of the consumer contract, but the schema is deferred as an “open implementation question.”
* Repository evidence: Existing CLI JSON surfaces, such as `project-standards list --json`, are concrete and testable. This spec does not define equivalent structures for findings, locations, slices, or `next`.
* External research evidence: Not applicable.
* Why it matters: Tool-to-tool consumption is a stated goal; without a schema, downstream callers cannot depend on stable fields.
* Recommended action for Claude Code: Specify minimal JSON objects for success and failure per command, including stable finding codes, severity, file, line, section/id, and message.
* Suggested validation: Add golden-output tests for `--json` on pass, findings, bad invocation, no match, and `next`.

#### SA-006: Documented template interchangeability guarantees are not preserved or retired

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Deleting `check_specs.py` could leave documented “tooling may rely on” guarantees untested.
* Spec reference: Lines 106, 112-113, 173.
* Finding: The spec explicitly declines to preserve shared example-ID and boilerplate guarantees because `check_specs.py` did not implement them, but `tooling-notes.md` still documents those as interchangeability guarantees.
* Repository evidence: `tooling-notes.md` says tooling may rely on shared example IDs and shared boilerplate. `check_specs.py` only enforces structural/template consistency and the cross-file Defined-In assertion.
* External research evidence: Not applicable.
* Why it matters: The implementation could remove the only maintainer script and still leave stronger guarantees in docs than tests enforce.
* Recommended action for Claude Code: Either add tests for the documented guarantees or revise `tooling-notes.md` to demote/remove them.
* Suggested validation: Add tests for shared example IDs / shared boilerplate, or assert the docs no longer promise those properties.

#### SA-007: Config-surface wording references a non-existent `files:` config

* Severity: Low
* Status: Confirmed
* Adversarial angle: A planner could chase the wrong config model.
* Spec reference: Line 141.
* Finding: The spec says the `spec:` block is separate from the frontmatter validator’s `files:` config, but the current repo uses `markdown.frontmatter.include` and `markdown.frontmatter.exclude`.
* Repository evidence: `.project-standards.yml` uses `markdown.frontmatter.include/exclude`; `validate_frontmatter.load_config` reads that nested shape.
* External research evidence: Not applicable.
* Why it matters: Minor, but this repo is a standards source of truth; config names should be exact.
* Recommended action for Claude Code: Replace `files:` with `markdown.frontmatter.include/exclude`.
* Suggested validation: No code validation needed; verify the edited wording against `.project-standards.yml` and `validate_frontmatter.load_config`.

### Missing specification considerations

* Blocking: Define separate consumer-validation vs template-maintainer validation semantics.
* Blocking: Define missing `spec:` block, empty include, unmatched glob, and explicit-path override behavior.
* Blocking: Decide which rules are hard `validate` failures vs advisory `lint` warnings.
* Non-blocking: Define the JSON schema and stable finding codes.
* Non-blocking: Define `extract` matching and ambiguity behavior for duplicate headings, partial heading matches, slug matches, multiple ID rows, and invalid selectors.
* Non-blocking: Define `next` behavior for empty-but-known prefixes, unknown prefixes, prefix spelling with/without trailing dash, and the ambiguous “empty-prefix (`→ -001`)” phrase.
* Non-blocking: Define reusable workflow inputs, including `standards-ref`, `config-path`, and whether strict lint is opt-in.
* Non-blocking: Define whether deleting `check_specs.py` needs a compatibility note or shim for maintainers.

### Ambiguities and decisions needed

* Ambiguity: Does `validate` reject `SPEC-____`, or does only `lint` warn?
  * Why it matters: This is the central G7 gate.
  * Recommended clarification: Consumer `validate` should reject it; template dogfood should use a maintainer-specific path.
  * Blocking or non-blocking: Blocking.

* Ambiguity: What does no-arg `spec validate` do without a `spec:` block?
  * Why it matters: Prevents vacuous CI success.
  * Recommended clarification: Exit non-zero unless explicit files are supplied.
  * Blocking or non-blocking: Blocking.

* Ambiguity: What exactly does “single canonical parser” prohibit?
  * Why it matters: The spec also requires both `registry.py` and `document.py` parsers.
  * Recommended clarification: Prohibit duplicate registry-rule extraction, not separate parsing of canonical templates vs consumer documents.
  * Blocking or non-blocking: Non-blocking.

* Ambiguity: What is the stable `--json` contract?
  * Why it matters: Agents and CI need stable fields.
  * Recommended clarification: Add JSON examples per command and failure mode.
  * Blocking or non-blocking: Non-blocking.

### Internet research performed

* Source name: uv documentation — Build backend
* URL: https://docs.astral.sh/uv/concepts/build-backend/
* Access date: 2026-07-05
* What it was used to verify: Current `uv_build` file-inclusion behavior for packaging Markdown template data.
* Relevant conclusion: uv’s wheel build includes the Python module tree by default and says there are no specific wheel includes; data should live under the module root or configured data directories. This supports the spec’s safe default of copying templates under `src/project_standards/specs/templates/`.

### Items Claude Code should verify before correcting the specification

* Verify the current templates’ sentinel, profile, section, appendix, and Appendix A shapes before changing the spec.
* Verify all current references to `check_specs.py` with `rg`.
* Verify whether `src/project_standards/specs/templates/*.md` lands in a built wheel after implementation.
* Verify no command-name conflict between top-level `project-standards validate` and nested `project-standards spec validate`.
* Verify `.project-standards.yml` can tolerate a new top-level `spec:` block without affecting existing validators.

### Suggested corrections for Claude Code’s specification

* Add a “consumer validate vs template-maintainer validation” section.
* Make `SPEC-____`, duplicate IDs, unknown prefixes, wrong prefix tier, and wrong Appendix-A mapping hard `validate` failures.
* Define missing/empty `spec:` behavior and make the CI workflow unable to pass vacuously.
* Specify JSON schemas and stable finding codes for every command.
* Define Light-profile traceability behavior.
* Update `tooling-notes.md` guarantees or require tests for the guarantees that remain.
* Correct the `files:` config wording.
* Tighten acceptance criteria so they include negative cases for discovery, placeholders, duplicate IDs, undeclared prefixes, JSON output, and no-match selectors.

### Read-only validation performed

* `pwd`: confirmed repository root `/home/chris/projects/project-standards`.
* `git status --short`: found modified `docs/superpowers/specs/README.md` and untracked spec file.
* `git branch --show-current`: confirmed branch `testing`.
* `git log --oneline -n 10`: confirmed recent `project-spec` commits and session closeout context.
* `sed` / `nl` on the spec: inventoried requirements, acceptance criteria, non-goals, and open questions.
* `sed` / `nl` on `standards/project-spec/README.md`, `resources/tooling-notes.md`, templates, and `check_specs.py`: checked the spec against the current standard and maintainer script.
* `rg --files`, `find .github`, and targeted `rg -n`: discovered relevant repo files and references.
* `sed` / `nl` on `.project-standards.yml`, `src/project_standards/cli.py`, `validate_frontmatter.py`, workflows, `pyproject.toml`, and packaging tests: checked repository fit.
* `git diff --stat`, `git diff --name-status`, and `git diff -- docs/superpowers/specs/README.md`: confirmed only the specs README is tracked-modified; the audited spec is untracked.
* `git ls-files --error-unmatch`: confirmed `check_specs.py` and templates are tracked; the audited spec is not yet tracked.
* `python3 standards/project-spec/resources/check_specs.py standards/project-spec/templates`: attempted direct read-only validation; local wrapper refused and instructed `uv run`, which I did not run in read-only mode.

### Recommended planning/implementation validation

* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest`
* Run only after implementation: `uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: build a wheel and verify `project_standards/specs/templates/*.md` is included.
* Run only after implementation: exercise `project-standards spec validate|lint|extract|next --json` against valid and invalid fixtures.
* Run only after implementation: test reusable `validate-specs.yml` behavior for missing config, empty config, valid config, and strict-lint opt-in.

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: /home/chris/projects/project-standards/docs/superpowers/specs/2026-07-04-project-spec-tooling-design.md
* Audit round: 1
* Open issue IDs: SA-001, SA-002, SA-003, SA-004, SA-005, SA-006, SA-007
* Resolved issue IDs:
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: consumer-vs-template validation semantics, missing `spec:` behavior, hard/advisory rule placement, JSON schema, and CI false-positive prevention

