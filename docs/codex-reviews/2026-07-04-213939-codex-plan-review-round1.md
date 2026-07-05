### Executive summary

The implementation plan needs major correction before Claude Code executes it. Several core parser, validation, discovery, and workflow steps are contradicted by the current repository evidence and would either fail the planned tests or ship false-positive/false-negative validation behavior.

Internet research was required for the workflow/build-backend assumptions. External docs confirm `uv_build` should include files under the module root, but the plan’s workflow pins and self-repo install path are stale relative to the repo’s current workflow pattern.

### Verdict

Needs major correction before execution

### Audit loop status

* Audit type: First audit
* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-07-04-project-spec-tooling-spec1.md
* Significant findings remaining: Yes
* Blocking issue count: 5
* Non-blocking issue count: 3

### What the plan gets right

The plan correctly scopes Spec #1 as read-only tooling, keeps the CLI under the existing `project-standards` console script, separates `registry.py` from `document.py`, preserves the consumer-vs-template sentinel distinction, and recognizes that `check_specs.py` must be replaced by pytest coverage rather than reused as the consumer validator.

### Adversarial review performed

I inventoried the plan’s material claims around parser behavior, ID semantics, config discovery, CLI error boundaries, CI workflow behavior, template packaging, and validation coverage. I falsified those claims against the current templates, `check_specs.py`, `validate_frontmatter.collect_paths`, existing workflows, the design spec, and official `uv_build` / GitHub Action release documentation.

Could not safely run the planned pytest/coverage/build commands because they may write caches, `.coverage`, or build artifacts. A direct `python3 standards/project-spec/resources/check_specs.py ...` probe was read-only but the repo wrapper rejected it and required `uv run`.

### Blocking issues

#### CR-001: ID uniqueness treats valid references as duplicate definitions

* Severity: High
* Status: Confirmed
* Adversarial angle: Validation false positive against the shipped template structure.
* Plan reference: Task 3 scans every `ID_TOKEN` in `doc.body`; Task 5 flags any repeated full ID as `SV-ID-DUP`.
* Finding: The plan does not distinguish ID definitions from ID references. It will mark valid specs as duplicate-ID failures whenever a requirement is referenced in the traceability matrix or a milestone heading is referenced again in the milestone summary.
* Repository evidence: `spec-standard-template.md` defines `FR-001` in §7.1 and references `FR-001` again in §17.3. It also uses `MS-0` in a milestone heading and the Milestone Summary. The plan’s `seen` set checks every occurrence from `doc.used_ids`, not just defining rows.
* External research evidence: Not applicable.
* Why it matters: Valid Standard/Full specs are expected to repeat requirement IDs for traceability. CI would reject conforming specs, and `tests/test_spec_validate.py::test_valid_specs_pass` would fail once the fixture keeps the required traceability row.
* Recommended action for Claude Code: Split parsed IDs into definitions and references. Enforce uniqueness only on definition sites, while still using all occurrences for format and declared-prefix checks as appropriate.
* Suggested validation: Add a valid fixture where `FR-001` appears in both §7.1 and §17.3 and assert `validate_document(...) == []`.

#### CR-002: Regex frontmatter parsing cannot handle the templates’ inline YAML comments

* Severity: High
* Status: Confirmed
* Adversarial angle: Parser assumption contradicted by the canonical templates.
* Plan reference: Task 3 `_scalar_frontmatter()` captures the whole text after `key:` as a raw string.
* Finding: Current templates have inline comments on `spec_id`, `status`, `profile`, `supersedes`, and `superseded_by`. The planned parser will read `profile: standard # ...` as the literal profile value, so `_check_frontmatter()` reports `SV-PROFILE`. The template conformance test would also see `spec_id` as `SPEC-____ # placeholder ...`, not the sentinel.
* Repository evidence: All three templates have `spec_id: SPEC-____ # placeholder ...` and `profile: light|standard|full # ...` in lines 2 and 5.
* External research evidence: Not applicable.
* Why it matters: The plan’s first valid-fixture parser test expects `doc.profile == "light"`, but copied templates keep inline comments unless the implementer removes them everywhere. The maintainer template test in Task 10 is guaranteed to fail against the bundled templates.
* Recommended action for Claude Code: Parse frontmatter with YAML for scalar values, while preserving a separate key-order extractor for ordering checks. Alternatively, explicitly strip YAML inline comments safely, but PyYAML is already a runtime dependency.
* Suggested validation: Add tests that parse the unmodified bundled templates and assert `profile` is `light|standard|full` and `spec_id` is `SPEC-____`.

#### CR-003: `collect_spec_paths()` falls back to the whole Markdown corpus for `spec: {include: []}`

* Severity: High
* Status: Confirmed
* Adversarial angle: Discovery contract can validate the wrong files instead of failing non-vacuously.
* Plan reference: Task 4 `collect_spec_paths()` calls `validate_frontmatter.collect_paths(explicit, None, cfg.include, cfg.exclude)` whenever `spec:` is present.
* Finding: `validate_frontmatter.collect_paths()` falls back to `_default_corpus()` when there are no explicit paths and `include_patterns` is empty. That contradicts the design spec, which says `spec:` present but empty/zero-match include sets must exit `2`.
* Repository evidence: `validate_frontmatter.collect_paths()` falls through to `_default_corpus()` when `include_patterns` is empty. The design spec requires exit `2` for empty include, unmatched glob, or excludes-remove-all.
* External research evidence: Not applicable.
* Why it matters: A consumer with an empty `spec:` block could accidentally validate every Markdown file in the repo, producing noisy failures or a misleading green result over non-spec files.
* Recommended action for Claude Code: Do not reuse `collect_paths()` in a way that permits default corpus fallback. For no explicit paths, require `cfg.include` to be non-empty, resolve those globs directly, apply excludes, and raise `DiscoveryError` on an empty result.
* Suggested validation: Add tests for `spec:\n  include: []\n`, omitted `include`, and excludes-removing-all; all should raise `DiscoveryError`.

#### CR-004: Proposed reusable workflow installs the published tag even for this repo

* Severity: High
* Status: Confirmed
* Adversarial angle: CI/deployment sequencing failure.
* Plan reference: Task 11 workflow always runs `uv tool install "git+https://github.com/L3DigitalNet/project-standards@${{ inputs.standards-ref || 'v3' }}"`.
* Finding: On this repo’s own push/PR runs, the new workflow would install the already-published `v3` tag instead of the checked-out implementation under test. Before release, that installed tool will not contain `project-standards spec`, so the workflow cannot validate the PR that adds it.
* Repository evidence: Existing `validate-markdown-frontmatter.yml` has a split path: this repo uses `uv sync --dev` plus `uv run ...`, while consuming repos use `uv tool install` from `standards-ref`. The plan says “mirror” that workflow but omits the split.
* External research evidence: GitHub release pages show the plan’s action pins are also stale relative to current releases: `setup-uv` latest listed release is `v8.2.0`, and `actions/checkout` lists newer releases than `v4`. Sources accessed 2026-07-05.
* Why it matters: The new CI workflow would fail in the implementation PR, or worse, validate an old package instead of the code being changed.
* Recommended action for Claude Code: Mirror the existing workflow’s self-repo vs consuming-repo branch. For `github.repository == 'L3DigitalNet/project-standards'`, run local `uv sync --dev` and `uv run project-standards spec ...`; only consumers should `uv tool install` from `standards-ref`.
* Suggested validation: Add workflow-shape tests asserting both local-source and consuming-repo branches exist, and that self-repo steps do not install from `@v3`.

#### CR-005: Bad-input error boundary still permits tracebacks

* Severity: High
* Status: Confirmed
* Adversarial angle: Failure-mode pass against malformed spec input.
* Plan reference: Task 9 catches only `ConfigError`; Task 2 copies `split_front_matter()` from `check_specs.py`.
* Finding: `check_specs.py`’s `split_front_matter()` uses `text.index("\n---\n", 4)`, which raises `ValueError` for a file that starts with `---\n` but lacks a closing fence. The planned CLI does not catch that exception around `parse_document()`.
* Repository evidence: `check_specs.py` line 87 uses `text.index`. The design spec requires malformed/non-UTF-8 specs to produce a graceful exit with no traceback.
* External research evidence: Not applicable.
* Why it matters: A malformed spec can crash the CLI instead of returning the documented `1` or `2`, breaking CI and violating the plan’s own “Never a traceback on bad input” constraint.
* Recommended action for Claude Code: Introduce a `SpecParseError`/`ConfigError` boundary for malformed frontmatter and parser failures, and test malformed frontmatter for validate/lint/extract/next.
* Suggested validation: Add a fixture containing an unterminated frontmatter fence and assert the CLI returns a clean nonzero code with no traceback text.

### Non-blocking issues

#### CR-006: `NOT_AN_ID` is not copied verbatim from `check_specs.py`

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Regression from existing maintainer parser behavior.
* Plan reference: Task 2 says to copy constants verbatim, then shows a shortened `NOT_AN_ID`.
* Finding: The plan omits existing denylist entries including `WCAG`, `PII`, `URL`, `SPEC`, `CSRF`, `CORS`, `SSO`, `WAL`, and `PITR`. It also adds `HTTPS`, so the shown set is not verbatim.
* Repository evidence: Current `check_specs.py` carries the larger denylist.
* External research evidence: Not applicable.
* Why it matters: Consumer specs that mention values like `WCAG-2` can be misclassified as project-spec IDs and receive false `SV-ID-FMT` / undeclared-prefix findings.
* Recommended action for Claude Code: Copy the current denylist exactly, then add explicit regression tests for at least `WCAG-2`, `PITR-1`, and a real project ID.
* Suggested validation: Unit-test `parse_document()` / `validate_document()` on prose containing known non-ID tokens.

#### CR-007: `extract §7` only returns the heading prelude, not the full section with subsections

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Validation attack on weak extract tests.
* Plan reference: Task 7 `_section_slice()` stops at the next Markdown heading of any level.
* Finding: For top-level sections such as `§7`, the regex stops before `### 7.1`, so it omits the actual requirement rows. The test only checks that output starts with a heading, so this bug can pass.
* Repository evidence: The templates define `## 7. Requirements` followed immediately by `### 7.1 Functional Requirements`, where the requirement table lives.
* External research evidence: Not applicable.
* Why it matters: The design describes `extract` as the context-window optimizer. Returning only the top-level heading text for `§7` is not a useful section slice.
* Recommended action for Claude Code: Make section slicing stop at the next heading of the same or higher level, not any heading. Add tests proving `extract §7` includes `FR-001`.
* Suggested validation: Assert `extract_slice(valid_standard, "§7").markdown` contains the §7.1 table row.

#### CR-008: Source-tree packaging test does not prove the built wheel contains templates

* Severity: Low
* Status: Confirmed
* Adversarial angle: Acceptance criterion not actually tested.
* Plan reference: Task 1 “wheel-inclusion check” imports the package from the source tree and checks `Path(specs.__file__).parent / "templates"`.
* Finding: That test proves the files exist in `src/`, not that a built wheel contains them.
* Repository evidence: The acceptance criteria require “A built wheel contains `project_standards/specs/templates/*.md`.”
* External research evidence: Official `uv_build` docs say wheel builds include the module under the module root, and small data files should live under that module root. Source: https://docs.astral.sh/uv/concepts/build-backend/ accessed 2026-07-05.
* Why it matters: The external assumption is probably correct, but the plan’s stated test does not verify the actual release artifact.
* Recommended action for Claude Code: Add a post-implementation packaging smoke test that builds the wheel and inspects the archive for the three templates.
* Suggested validation: Run only after implementation: `uv build`, then inspect the wheel contents for `project_standards/specs/templates/spec-*-template.md`.

### Missing considerations

* Blocking: The plan needs explicit definition-vs-reference ID semantics before implementing `validate` and `next`.
* Blocking: The parser needs malformed-frontmatter tests and a clean exception boundary.
* Blocking: Discovery tests must include empty include, omitted include inside present `spec:`, and excludes-remove-all.
* Blocking: The workflow must verify local source on this repo’s PRs before validating installed consumer behavior.
* Non-blocking: `extract` needs tests that prove top-level section selectors include child subsections.
* Non-blocking: The wheel inclusion acceptance criterion needs a real built-wheel inspection.
* Non-blocking: The ID denylist needs regression tests for standards/security acronyms.

### Internet research performed

* Source name: uv build backend documentation
* URL: https://docs.astral.sh/uv/concepts/build-backend/
* Access date: 2026-07-05
* What it was used to verify: Whether files under the Python module root are expected to be included in wheels by `uv_build`.
* Relevant conclusion: The docs state wheel builds include the module under the module root and that small data files should live under the module root, supporting the chosen placement but not replacing an artifact-level smoke test.

* Source name: astral-sh/setup-uv GitHub releases
* URL: https://github.com/astral-sh/setup-uv/releases
* Access date: 2026-07-05
* What it was used to verify: Current release/tag state for `setup-uv`.
* Relevant conclusion: The release list shows `v8.2.0` as latest and `v8.0.0` as “Immutable releases and secure tags,” while the plan uses `@v5`.

* Source name: actions/checkout GitHub releases
* URL: https://github.com/actions/checkout/releases
* Access date: 2026-07-05
* What it was used to verify: Current release/tag state for checkout action.
* Relevant conclusion: The release list shows newer checkout releases than the plan’s `@v4`, and the repository already uses `actions/checkout@v6`.

### Items Claude Code should verify before correcting the plan

* Confirm whether consumer spec frontmatter should be parsed as YAML values while preserving key order.
* Define which table rows/headings are ID definitions versus references.
* Confirm the desired section-slice semantics for top-level sections with subsections.
* Confirm the workflow should follow the existing self-repo/consumer split exactly.
* Confirm whether `spec:` with omitted `include` should be an exit-2 config error, not a default corpus scan.

### Suggested corrections for Claude Code's plan

* Replace regex scalar frontmatter parsing with YAML scalar parsing plus separate key-order extraction.
* Redesign ID parsing to separate definitions from references; enforce uniqueness only on definitions.
* Rework `collect_spec_paths()` so it never falls back to `_default_corpus()` for spec discovery.
* Add malformed spec parser exceptions and CLI tests proving no traceback escapes.
* Rewrite `validate-specs.yml` to mirror the existing local-source vs consuming-repo branch.
* Copy the full `NOT_AN_ID` denylist from `check_specs.py`.
* Fix section extraction to include nested subsections for top-level selectors.
* Add built-wheel artifact inspection to packaging validation.

### Read-only validation performed

* `pwd` — confirmed repository root is `/home/chris/projects/project-standards`.
* `git status --short` — confirmed working tree was clean.
* `git branch --show-current` — confirmed current branch is `testing`.
* `git log --oneline -n 10` — confirmed the plan and design were recently committed.
* `sed -n ... docs/superpowers/plans/2026-07-04-project-spec-tooling-spec1.md` — read the full implementation plan.
* `rg --files` — inventoried repository structure and relevant files.
* `sed -n ... docs/superpowers/specs/2026-07-04-project-spec-tooling-design.md` — checked the design contract.
* `sed -n ... standards/project-spec/resources/check_specs.py` — checked current parser/constants and maintainer validator behavior.
* `sed -n ... src/project_standards/validate_frontmatter.py` — checked `collect_paths()` fallback behavior.
* `sed -n ... src/project_standards/cli.py` — checked current early-dispatch and error-boundary style.
* `sed -n ... .github/workflows/*.yml` — checked existing workflow action pins and self-repo install pattern.
* `nl -ba ... standards/project-spec/templates/*.md` and `rg -n ...` — checked inline frontmatter comments, duplicate ID references, headings, appendices, and Appendix A.
* `python3 standards/project-spec/resources/check_specs.py standards/project-spec/templates` — read-only probe rejected by repo wrapper, establishing the script expects `uv run` invocation.

### Recommended implementation validation

* Run only after implementation: `uv run pytest tests/test_spec_packaging.py tests/test_spec_registry.py tests/test_spec_document.py tests/test_spec_config.py tests/test_spec_validate.py tests/test_spec_lint.py tests/test_spec_extract.py tests/test_spec_next.py tests/test_spec_cli.py tests/test_template_conformance.py tests/test_template_interchangeability.py tests/test_validate_specs_workflow.py -v`
* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest && uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`
* Run only after implementation: `uv build`, then inspect the wheel for the three bundled spec templates.

### Final recommendation

Claude Code should revise the plan using the findings above

### Review ledger for next loop

* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-07-04-project-spec-tooling-spec1.md
* Audit round: 1
* Open issue IDs: CR-001, CR-002, CR-003, CR-004, CR-005, CR-006, CR-007, CR-008
* Resolved issue IDs: None
* Superseded issue IDs: None
* Significant findings remaining: Yes
* Next audit should focus on: ID definition/reference semantics, YAML frontmatter parsing, spec discovery without default corpus fallback, CLI bad-input error handling, workflow self-repo install path, and artifact-level wheel validation.