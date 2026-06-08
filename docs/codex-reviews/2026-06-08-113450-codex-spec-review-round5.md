### Executive summary

Claude Code’s latest corrections resolved the omitted Markdown Tooling scaffold classification and the fragment-report wording. Significant findings still remain because the spec still has an internal `.vscode/*` scope contradiction, and the ADR template validation fix only proves the clean `adopt markdown-frontmatter adr` path, not `adopt adr` against an existing frontmatter config.

New internet research rechecked the external packaging/version/YAML assumptions; no official source contradicted those parts of the spec.

### Verdict

Needs major specification correction before planning/implementation

### Audit loop status

* Audit type: Follow-up audit
* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-06-08-adopt-cli-design.md`
* Prior audit issue count: 11
* Resolved issue count: 9
* Still open issue count: 0
* Partially resolved issue count: 2
* New issue count: 1
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

Re-read the revised spec, prior audit, git status/history, v3 handoff state, repo instructions, conventions, validator/config code, registry, package metadata, root scaffolds, workflows, `.vscode/*`, current standard READMEs/adopt guides, ADR templates, and versioning standard. Retested prior findings around template extraction, `.vscode` classification, fragment reporting, ADR template destination/exclusion, package-relative bundle loading, and generated syntax assumptions.

Acceptance criteria were attacked for false positives where combined clean-fixture validation passes but `adopt adr` still breaks an existing consumer config, and where tests could pass while a maintainer-authored manifest source path escapes the bundle tree. Could not check implementation behavior because no `src/project_standards/bundles/` tree or `adopt` CLI exists yet.

### Prior findings status

#### SA-001: Multi-standard adoption can conflict on current overlapping scaffolds

* Previous severity: High
* Current status: Resolved
* Evidence: Decision #8 and Component 6 continue to define shared `.editorconfig` ownership plus Python-only, Markdown-only, and combined adoption tests.
* Remaining action for Claude Code: None.

#### SA-002: Root-level template packaging strategy conflicts with current `uv_build` resource behavior

* Previous severity: High
* Current status: Resolved
* Evidence: The spec keeps manifests/templates under `src/project_standards/bundles/<id>/` and uses the package-relative pattern already used by `registry.py`.
* Remaining action for Claude Code: None beyond wheel inspection/install-run validation.

#### SA-003: File-write safety boundaries are underspecified

* Previous severity: High
* Current status: Resolved
* Evidence: Component 4 covers destination containment, symlink skipping, I/O error mapping, and temp-file plus `os.replace` atomic writes.
* Remaining action for Claude Code: None for destination-write safety.

#### SA-004: Tooling inventory understates current ADR enforcement

* Previous severity: Medium
* Current status: Resolved
* Evidence: The problem table still names frontmatter validation, opt-in MADR body-section checks, and FM-to-ADR compatibility.
* Remaining action for Claude Code: None.

#### SA-005: Template extraction scope does not cover all current inline scaffolds clearly

* Previous severity: Medium
* Current status: Resolved
* Evidence: Component 5 now explicitly marks `.vscode/settings.json`, `.vscode/tasks.json`, and Markdown Tooling `AGENTS.md`/settings blocks as illustrative/manual and out of manifest/single-canonical-copy scope.
* Remaining action for Claude Code: None for this issue.

#### SA-NEW-001: Byte-unchanged extraction can produce invalid workflow YAML

* Previous severity: High
* Current status: Resolved
* Evidence: The spec requires semantic extraction plus parse-valid generated YAML/JSON/TOML and no tab-indented YAML.
* Remaining action for Claude Code: None beyond implementing tests.

#### SA-NEW-002: ADR config-fragment behavior is promised but not specified or tested

* Previous severity: Medium
* Current status: Resolved
* Evidence: ADR `.project-standards.yml` knobs are now a `fragment`, reported under target-specific headings and covered in adoption matrix tests.
* Remaining action for Claude Code: None.

#### SA-NEW-003: Consumer-facing scaffolds can be sourced from repo-specific working files

* Previous severity: High
* Current status: Partially resolved
* Evidence: Decision #10 and Component 5 correctly put `.vscode/settings.json` and `.vscode/tasks.json` out of adopt scope, but line 149 still lists `.vscode/*` as dogfoodable root artifacts. That contradicts the table and acceptance criteria that only ship shared `.vscode/extensions.json`.
* Remaining action for Claude Code: Replace `.vscode/*` with `.vscode/extensions.json` in the dogfoodable artifact list and dogfood-test scope.

#### SA-NEW-004: Partial-write recovery is named but not made testable

* Previous severity: Medium
* Current status: Resolved
* Evidence: Component 4 and Component 6 now require atomic write semantics and a failure-injection test.
* Remaining action for Claude Code: None beyond implementing the test.

#### SA-NEW-005: ADR template destination and validation safety are unspecified

* Previous severity: High
* Current status: Partially resolved
* Evidence: The spec now defines `docs/decisions/adr.template.md`, `**/*.template.md` in the generated frontmatter starter, and a clean `adopt markdown-frontmatter adr` validation test. It does not handle `adopt adr` against an existing `.project-standards.yml` that includes `docs/**/*.md` but lacks `**/*.template.md`, which matches the current adoption guide’s starter.
* Remaining action for Claude Code: Specify how `adopt adr` remains validation-safe for existing frontmatter consumers, likely by reporting an explicit `markdown.frontmatter.exclude` fragment or using a destination outside typical managed docs.

#### SA-NEW-006: Fragment reporting text is still `pyproject.toml`-specific

* Previous severity: Low
* Current status: Resolved
* Evidence: Component 3 now reports fragments grouped by target file with “Add these sections to `<target>`”.
* Remaining action for Claude Code: None.

### New blocking issues

None found.

### New non-blocking issues

#### SA-NEW-007: Source-path safety is specified but not directly tested

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Attack the manifest safety boundary from the package side, not only the destination side.
* Spec reference: Lines 139-140, 181, 203.
* Finding: The safety contract rejects `source`/`shared` paths that escape the package bundle tree, but the safety test list only names unsafe destination paths and missing sources. The acceptance criterion says “unsafe path” broadly, but a plan could satisfy the enumerated tests while never proving absolute source paths, `../` source traversal, or shared-path escape are rejected.
* Repository evidence: No `adopt` implementation or tests exist yet. Existing `registry.py` uses a fixed package-relative path, while the proposed manifest engine will accept maintainer-authored relative paths.
* External research evidence: Not applicable.
* Why it matters: A bad packaged manifest should fail cleanly instead of reading unintended files from the source checkout or installed package environment. This is lower risk than destination escape, but it is still part of the stated safety contract.
* Recommended action for Claude Code: Add explicit source/shared safety tests for absolute paths, `../`, and resolved escapes outside `src/project_standards/bundles/`.
* Suggested validation: Run manifest parsing/plan tests with malicious `source` and `shared` values and assert exit 3 with no traceback and no file write.

### Regressions

None found.

### Remaining ambiguities and decisions needed

* Ambiguity: Does `.vscode/*` in the dogfoodable root-artifact list mean all VS Code files, or only `.vscode/extensions.json`?
* Why it matters: The rest of the spec excludes settings/tasks from adopt scope; the wildcard can reintroduce the cross-standard leak the revision was meant to close.
* Recommended clarification: Use the exact path `.vscode/extensions.json` everywhere dogfoodable artifacts are listed.
* Blocking or non-blocking: Blocking.

* Ambiguity: What should `adopt adr` do when the destination already has a frontmatter config that validates `docs/**/*.md` and lacks a template exclusion?
* Why it matters: The placeholder ADR template deliberately fails schema validation.
* Recommended clarification: Define an exclusion fragment/report requirement or choose a destination outside typical managed include globs.
* Blocking or non-blocking: Blocking.

### Internet research performed

* Source name: uv Build backend docs
* URL: https://docs.astral.sh/uv/concepts/build-backend/
* Access date: 2026-06-08
* What it was used to verify: Wheel/package-data assumptions for files placed under the module root.
* Relevant conclusion: uv’s wheel build includes the module under the module root, and small data files are commonly stored in the module root.

* Source name: Python `importlib.metadata` docs
* URL: https://docs.python.org/3/library/importlib.metadata.html
* Access date: 2026-06-08
* What it was used to verify: `version("project-standards")` behavior and failure mode.
* Relevant conclusion: `version()` returns installed distribution metadata and raises `PackageNotFoundError` when the distribution is not installed.

* Source name: YAML 1.2.2 specification
* URL: https://yaml.org/spec/1.2.2/
* Access date: 2026-06-08
* What it was used to verify: Tab indentation assumptions for generated YAML.
* Relevant conclusion: YAML block indentation is space-based; tabs must not be used for indentation.

### Read-only validation performed

* `pwd`, `git status --short`, `git branch --show-current`, `git log --oneline -n 10`: confirmed repo root, branch `testing`, modified spec, and untracked `docs/codex-reviews/`.
* Inspected `docs/handoff/state.md`, `AGENTS.md`, and `docs/handoff/conventions.md`: confirmed v3 startup state and repo working rules.
* `nl -ba docs/superpowers/specs/2026-06-08-adopt-cli-design.md`: inventoried current spec references.
* `git diff -- docs/superpowers/specs/2026-06-08-adopt-cli-design.md`: compared revised spec to the committed baseline.
* Inspected `src/project_standards/validate_frontmatter.py`, `registry.py`, `schemas/registry.json`, `.project-standards.yml`, `pyproject.toml`, `.editorconfig`, `.prettierrc.json`, `.markdownlint.json`, `.vscode/*`, workflows, standards READMEs/adopt guides, ADR templates, and `meta/versioning.md`.
* `find src/project_standards -maxdepth 3 -type f`: confirmed no current bundles/adopt CLI implementation exists.
* `rg` over standards/spec/source/tests: mapped inline scaffolds, current template exclusions, `.vscode` references, version labels, and validation assumptions.
* `python3` `fnmatchcase` check: confirmed `**/*.template.md` matches `docs/decisions/adr.template.md` under the validator’s exclusion semantics.

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

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-06-08-adopt-cli-design.md`
* Audit round: 5
* Open issue IDs: SA-NEW-003, SA-NEW-005, SA-NEW-007
* Resolved issue IDs: SA-001, SA-002, SA-003, SA-004, SA-005, SA-NEW-001, SA-NEW-002, SA-NEW-004, SA-NEW-006
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: narrowing `.vscode/*` to `.vscode/extensions.json`, making `adopt adr` safe for existing frontmatter configs, and adding explicit source/shared manifest path safety validation.