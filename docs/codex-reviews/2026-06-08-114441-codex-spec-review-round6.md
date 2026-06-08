### Executive summary

Claude Code’s latest corrections resolved the three prior open findings around `.vscode` scope, ADR template validation safety for existing configs, and source/shared manifest path tests. One new non-blocking repo-fit issue remains: workflow-caller stubs are classified as dogfoodable root artifacts even though this repo has reusable workflow definitions, not root caller workflow files, so the stated source and byte-identical dogfood rule cannot be satisfied as written.

New internet research rechecked the packaging, package-version, and YAML indentation assumptions. No official source contradicted those parts of the spec.

### Verdict

Needs minor specification correction before planning/implementation

### Audit loop status

* Audit type: Follow-up audit
* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-06-08-adopt-cli-design.md`
* Prior audit issue count: 12
* Resolved issue count: 12
* Still open issue count: 0
* Partially resolved issue count: 0
* New issue count: 1
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

Re-read the current spec, prior audit ledger, git status/history, v3 handoff state, repo instructions, conventions, package metadata, validator/config code, registry, root scaffolds, `.vscode/*`, workflows, standards READMEs/adopt guides, ADR templates, and versioning standard. Retested prior fixes for `.vscode` scoping, ADR template exclusion/reporting, and source/shared safety tests.

Acceptance criteria were attacked for false positives where tests could pass while the caller workflow stubs lack a real dogfood source. Implementation behavior could not be checked because no `src/project_standards/bundles/` tree or `adopt` CLI exists yet.

### Prior findings status

#### SA-001: Multi-standard adoption can conflict on current overlapping scaffolds

* Previous severity: High
* Current status: Resolved
* Evidence: Shared `.editorconfig` and `.vscode/extensions.json` ownership remains explicit, with Python-only, Markdown-only, and combined adoption tests.
* Remaining action for Claude Code: None.

#### SA-002: Root-level template packaging strategy conflicts with current `uv_build` resource behavior

* Previous severity: High
* Current status: Resolved
* Evidence: Bundles remain under `src/project_standards/bundles/<id>/`, using the package-relative pattern already used by `registry.py`.
* Remaining action for Claude Code: None beyond wheel inspection/install-run validation.

#### SA-003: File-write safety boundaries are underspecified

* Previous severity: High
* Current status: Resolved
* Evidence: Destination containment, symlink skipping, I/O error handling, and temp-file plus `os.replace` atomic writes are specified.
* Remaining action for Claude Code: None.

#### SA-004: Tooling inventory understates current ADR enforcement

* Previous severity: Medium
* Current status: Resolved
* Evidence: The spec continues to describe ADR frontmatter validation, opt-in MADR body checks, and FM-to-ADR compatibility.
* Remaining action for Claude Code: None.

#### SA-005: Template extraction scope does not cover all current inline scaffolds clearly

* Previous severity: Medium
* Current status: Resolved
* Evidence: The spec now covers README and `adopt.md` inline scaffolds and explicitly excludes illustrative/manual settings/tasks and Markdown Tooling agent blocks from manifest source scope.
* Remaining action for Claude Code: None.

#### SA-NEW-001: Byte-unchanged extraction can produce invalid workflow YAML

* Previous severity: High
* Current status: Resolved
* Evidence: The spec requires semantic extraction and parse-valid generated YAML/JSON/TOML, with no tab-indented YAML.
* Remaining action for Claude Code: None beyond implementing tests.

#### SA-NEW-002: ADR config-fragment behavior is promised but not specified or tested

* Previous severity: Medium
* Current status: Resolved
* Evidence: ADR `.project-standards.yml` knobs are fragments, reported under target-specific headings, and covered in adoption matrix tests.
* Remaining action for Claude Code: None.

#### SA-NEW-003: Consumer-facing scaffolds can be sourced from repo-specific working files

* Previous severity: High
* Current status: Resolved
* Evidence: `.vscode/settings.json` and `.vscode/tasks.json` are now explicitly out of adopt scope; the dogfoodable list names only shared `.vscode/extensions.json`.
* Remaining action for Claude Code: None for the prior `.vscode` scope issue.

#### SA-NEW-004: Partial-write recovery is named but not made testable

* Previous severity: Medium
* Current status: Resolved
* Evidence: Atomic write semantics and a failure-injection test are specified.
* Remaining action for Claude Code: None.

#### SA-NEW-005: ADR template destination and validation safety are unspecified

* Previous severity: High
* Current status: Resolved
* Evidence: The spec defines `docs/decisions/adr.template.md`, `**/*.template.md` starter exclusion, and an existing-config test where the report includes the needed exclude fragment and applying it makes validation pass.
* Remaining action for Claude Code: None.

#### SA-NEW-006: Fragment reporting text is still `pyproject.toml`-specific

* Previous severity: Low
* Current status: Resolved
* Evidence: Fragment reporting is grouped by target file with “Add these sections to `<target>`”.
* Remaining action for Claude Code: None.

#### SA-NEW-007: Source-path safety is specified but not directly tested

* Previous severity: Medium
* Current status: Resolved
* Evidence: Safety tests now explicitly cover absolute, `../`, and outside-bundle `source`/`shared` paths with exit 3 and no writes.
* Remaining action for Claude Code: None.

### New blocking issues

None found.

### New non-blocking issues

#### SA-NEW-008: Workflow-caller stubs have no dogfoodable root source

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Test whether every artifact classified as “dogfoodable root artifact” actually has a real root working file to dogfood against.
* Spec reference: Lines 28, 30, 149, 155, 157, 196.
* Finding: The spec classifies `validate-markdown-frontmatter.caller.yml` and `lint-markdown.caller.yml` as dogfoodable root artifacts, but this repo does not have root caller workflow files. It has reusable workflow definitions under `.github/workflows/validate-markdown-frontmatter.yml` and `.github/workflows/lint-markdown.yml`; the consumer caller snippets exist only in docs/adopt prose.
* Repository evidence: `find .github/workflows` shows `check.yml`, `format.yml`, `lint-markdown.yml`, and `validate-markdown-frontmatter.yml`, with no `*.caller.yml`. `rg` finds caller `uses:` snippets in `standards/*/adopt.md`, while the root workflow files are `workflow_call` providers.
* External research evidence: Not applicable.
* Why it matters: Claude Code would have to invent whether caller stubs are curated files, generated from reusable workflow metadata, or extracted from prose. The byte-identical dogfood test cannot apply to files that have no root working counterpart.
* Recommended action for Claude Code: Reclassify workflow-caller stubs as curated/generated consumer scaffolds exempt from root byte-identical dogfood, or define a concrete semantic generator/source from the reusable workflow metadata and test that instead.
* Suggested validation: Add tests that generated caller YAML parses, points at the correct reusable workflow filename, substitutes the current major ref, and is not included in the root byte-identical dogfood set unless a real root caller source exists.

### Regressions

None found.

### Remaining ambiguities and decisions needed

* Ambiguity: What is the authoritative source and test class for `*.caller.yml` workflow-caller stubs?
* Why it matters: The spec currently says their source is the repo’s real working files, but no such root caller files exist.
* Recommended clarification: Mark caller stubs as curated/generated consumer scaffolds, or define exactly how they are derived from the reusable workflow definitions.
* Blocking or non-blocking: Non-blocking.

### Internet research performed

* Source name: uv Build backend docs
* URL: https://docs.astral.sh/uv/concepts/build-backend/
* Access date: 2026-06-08
* What it was used to verify: Wheel/package-data assumptions for files placed under the module root.
* Relevant conclusion: uv’s wheel build includes the module under the module root, and small data files may live under the module root.

* Source name: Python `importlib.metadata` docs
* URL: https://docs.python.org/3/library/importlib.metadata.html
* Access date: 2026-06-08
* What it was used to verify: `version("project-standards")` behavior and failure mode.
* Relevant conclusion: `version()` reads installed distribution metadata; `PackageNotFoundError` is raised when the distribution is unavailable.

* Source name: YAML 1.2.2 specification
* URL: https://yaml.org/spec/1.2.2/
* Access date: 2026-06-08
* What it was used to verify: Tab indentation assumptions for generated YAML.
* Relevant conclusion: YAML block indentation is space-based; tabs must not be used for indentation.

### Read-only validation performed

* `pwd`, `git status --short`, `git branch --show-current`, `git log --oneline -n 10`: confirmed repo root, clean working tree, branch `testing`, and latest spec-review convergence commit.
* Inspected `docs/handoff/state.md`, `AGENTS.md`, and `docs/handoff/conventions.md`: confirmed v3 startup state and repo working rules.
* `nl -ba docs/superpowers/specs/2026-06-08-adopt-cli-design.md`: inventoried current spec requirements and line references.
* `git diff -- docs/superpowers/specs/2026-06-08-adopt-cli-design.md`: confirmed no uncommitted spec diff.
* `find src/project_standards -maxdepth 4 -type f`: confirmed no current bundles/adopt implementation exists.
* `rg` and targeted `sed` over standards, workflows, config, source, tests, and `.vscode`: mapped current scaffolds, workflow providers/caller snippets, exclusions, and registry/package behavior.
* `python3` `fnmatchcase` check: confirmed `**/*.template.md` matches `docs/decisions/adr.template.md`.
* Opened official uv, Python, and YAML documentation for external assumption verification.

### Recommended planning/implementation validation

* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest`
* Run only after implementation: `uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`
* Run only after implementation: build the wheel, inspect bundled manifests/templates, install from the wheel, and run installed `project-standards list` plus `project-standards adopt ... --dry-run`.
* Run only after implementation: adoption matrix for each standard alone, `markdown-frontmatter adr`, `markdown-tooling python-tooling`, and all four together.
* Run only after implementation: assert `.vscode/settings.json` and `.vscode/tasks.json` are never packaged or written by `adopt`.
* Run only after implementation: assert `adopt adr` is validation-safe against an existing config with `include: ["docs/**/*.md"]`.
* Run only after implementation: add malicious manifest tests for absolute/escaping `source` and `shared` paths.
* Run only after implementation: assert workflow-caller stubs are generated from their specified source class and excluded from byte-identical root dogfood tests unless real root caller files are added.

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-06-08-adopt-cli-design.md`
* Audit round: 6
* Open issue IDs: SA-NEW-008
* Resolved issue IDs: SA-001, SA-002, SA-003, SA-004, SA-005, SA-NEW-001, SA-NEW-002, SA-NEW-003, SA-NEW-004, SA-NEW-005, SA-NEW-006, SA-NEW-007
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: clarifying the workflow-caller stub source/classification and ensuring the dogfood test applies only to artifacts with real root working-file sources.