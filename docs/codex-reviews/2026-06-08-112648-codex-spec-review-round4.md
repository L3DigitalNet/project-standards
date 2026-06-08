### Executive summary

Claude Code’s latest corrections resolved the atomic-write issue and much of the consumer-template source issue, but not all of it. Significant findings remain because the spec still misclassifies some consumer-facing `.vscode/*` scaffolds as dogfoodable root artifacts, leaves current Markdown Tooling inline scaffolds outside the extraction table, and does not define where the ADR template is written or how that placeholder template avoids breaking frontmatter validation.

New internet research rechecked the packaging/version/YAML assumptions. No external source contradicted the spec’s current package-data, `importlib.metadata.version()`, or no-tab YAML assumptions.

### Verdict

Needs major specification correction before planning/implementation

### Audit loop status

* Audit type: Follow-up audit
* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-06-08-adopt-cli-design.md`
* Prior audit issue count: 9
* Resolved issue count: 7
* Still open issue count: 0
* Partially resolved issue count: 2
* New issue count: 2
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

Re-read the current spec, prior round-3 audit, git status/history, v3 handoff state, repo instructions, package metadata, registry/validator code, root config/workflow scaffolds, current standards READMEs/adoption guides, ADR templates, and tests documentation. Retested prior fixes for shared `.editorconfig`, package-relative bundles, file-write safety, ADR fragment behavior, curated `.project-standards.yml` and agent stubs, generated syntax checks, and atomic write semantics.

Attacked the revised template-classification model against every current inline scaffold and against single-standard adoption. Also attacked acceptance criteria for false positives where root-byte-identical tests could pass while a consumer receives the wrong standard’s VS Code/tasks content, or where an ADR placeholder template could be generated into a managed path and fail validation.

Could not check implementation behavior because no `src/project_standards/bundles/` tree or `adopt` CLI implementation exists yet.

### Prior findings status

#### SA-001: Multi-standard adoption can conflict on current overlapping scaffolds

* Previous severity: High
* Current status: Resolved
* Evidence: Decision #8 and Component 6 now explicitly cover the shared `.editorconfig` superset and Python-only / Markdown-only / combined adoption tests.
* Remaining action for Claude Code: None for this issue.

#### SA-002: Root-level template packaging strategy conflicts with current `uv_build` resource behavior

* Previous severity: High
* Current status: Resolved
* Evidence: The spec keeps manifests/templates under `src/project_standards/bundles/<id>/` and uses the same package-relative pattern as `registry.py`.
* Remaining action for Claude Code: Keep the wheel inspection/install-run validation.

#### SA-003: File-write safety boundaries are underspecified

* Previous severity: High
* Current status: Resolved
* Evidence: Component 4 now rejects unsafe destination/source paths, skips symlink destinations even under `--force`, maps I/O failures, and specifies atomic writes.
* Remaining action for Claude Code: None beyond implementing tests.

#### SA-004: Tooling inventory understates current ADR enforcement

* Previous severity: Medium
* Current status: Resolved
* Evidence: The problem table and manifest text now describe frontmatter validation, opt-in MADR section checks, and FM-to-ADR compatibility.
* Remaining action for Claude Code: None.

#### SA-005: Template extraction scope does not cover all current inline scaffolds clearly

* Previous severity: Medium
* Current status: Partially resolved
* Evidence: The spec now says README and `adopt.md` scaffolds are in scope, but the template table still omits Markdown Tooling’s inline `.vscode/settings.json` block and Markdown Tooling `AGENTS.md` block from `standards/markdown-tooling/README.md`.
* Remaining action for Claude Code: Either include those scaffolds in the extraction/manifest model or explicitly mark them illustrative and explain why `adopt markdown-tooling` does not materialize them.

#### SA-NEW-001: Byte-unchanged extraction can produce invalid workflow YAML

* Previous severity: High
* Current status: Resolved
* Evidence: The spec now requires semantic extraction, parse-valid generated YAML/JSON/TOML, and no tab-indented YAML.
* Remaining action for Claude Code: None beyond implementing those tests.

#### SA-NEW-002: ADR config-fragment behavior is promised but not specified or tested

* Previous severity: Medium
* Current status: Resolved
* Evidence: ADR `.project-standards.yml` knobs are now a `fragment`, reported whether target exists or not, and covered by adoption matrix tests.
* Remaining action for Claude Code: None.

#### SA-NEW-003: Consumer-facing scaffolds can be sourced from repo-specific working files

* Previous severity: High
* Current status: Partially resolved
* Evidence: The `.project-standards.yml` starter and Python `AGENTS.md`/`CLAUDE.md` stubs are now curated, but `.vscode/*` remains classified as dogfoodable. Root `.vscode/settings.json` and `.vscode/tasks.json` include Markdown Tooling settings/tasks, while Python Tooling’s own inline scaffolds are Python-only. A Python-only adoption could therefore inherit Markdown Tooling behavior by copying root `.vscode/*`.
* Remaining action for Claude Code: Split `.vscode/settings.json` and `.vscode/tasks.json` into shared/per-standard/curated artifacts, or explicitly define the cross-standard superset policy and test Python-only, Markdown-only, and combined outputs.

#### SA-NEW-004: Partial-write recovery is named but not made testable

* Previous severity: Medium
* Current status: Resolved
* Evidence: Component 4 now specifies temp-file plus `os.replace` atomic writes, original preservation on failed `--force`, temp cleanup, exit 1, and a failure-injection test.
* Remaining action for Claude Code: None beyond implementing the test.

### New blocking issues

#### SA-NEW-005: ADR template destination and validation safety are unspecified

* Severity: High
* Status: Confirmed
* Adversarial angle: Test whether `adopt adr` can generate a placeholder ADR template while the default frontmatter config validates `docs/**/*.md`.
* Spec reference: Lines 149, 155, 180, 183, and 206.
* Finding: The spec says `adopt adr` drops an ADR template, but does not define its destination, whether it is under a managed Markdown include path, or whether the generated `.project-standards.yml` starter excludes template paths. Existing ADR templates contain placeholder dates like `YYYY-MM-DD`, which this repo explicitly treats as intentionally invalid for schema validation.
* Repository evidence: `standards/adr/templates/adr.md` contains placeholder `created`/`updated` values. `tests/README.md` states templates are excluded from dogfood validation because placeholders deliberately fail the schema. The ADR standard says ADRs live under `docs/decisions/`, while the Markdown Frontmatter adoption starter includes `docs/**/*.md`.
* External research evidence: Not applicable.
* Why it matters: Acceptance could pass by merely creating the file, while a consumer running `validate-frontmatter` immediately fails if the placeholder template lands under `docs/**/*.md`. Claude Code would have to invent the destination/exclusion contract during planning.
* Recommended action for Claude Code: Specify the ADR template destination and validation model. Either write it to an excluded template path and include that exclusion in the starter config, make it report-only, or define a schema-valid non-placeholder generated ADR seed with required user edits clearly outside validation.
* Suggested validation: Add an integration test for `adopt markdown-frontmatter adr` followed by `validate-frontmatter --config .project-standards.yml` against the generated fixture tree.

### New non-blocking issues

#### SA-NEW-006: Fragment reporting text is still `pyproject.toml`-specific

* Severity: Low
* Status: Confirmed
* Adversarial angle: Check whether the reporting contract matches the broadened fragment mechanism.
* Spec reference: Lines 108 and 121.
* Finding: The spec correctly generalizes `fragment` targets to `.project-standards.yml`, but the report step still says fragments are printed as “add these sections to `pyproject.toml`.”
* Repository evidence: ADR adoption now depends on a `.project-standards.yml` fragment, not only a `pyproject.toml` fragment.
* External research evidence: Not applicable.
* Why it matters: This is a small clarity bug, but it could produce a confusing report contract or weak acceptance assertions for ADR fragments.
* Recommended action for Claude Code: Generalize report wording and tests to group fragments by target file.
* Suggested validation: Assert `adopt adr` reports an `.project-standards.yml` fragment under a target-specific heading.

### Regressions

None found.

### Remaining ambiguities and decisions needed

* Ambiguity: Are `.vscode/settings.json` and `.vscode/tasks.json` shared superset artifacts, per-standard artifacts, curated scaffolds, or fragments?
* Why it matters: Root files currently mix Python and Markdown behavior; blindly dogfooding them can make single-standard adoption leak another standard’s behavior.
* Recommended clarification: Define these files separately from `.vscode/extensions.json` and test Python-only, Markdown-only, and combined outputs.
* Blocking or non-blocking: Blocking.

* Ambiguity: Does `adopt markdown-tooling` materialize the Markdown Tooling `AGENTS.md` block and VS Code settings block, or are they illustrative only?
* Why it matters: The spec’s “every inline scaffold” rule conflicts with the artifact table.
* Recommended clarification: Add them to the table or mark them explicitly illustrative.
* Blocking or non-blocking: Blocking.

* Ambiguity: Where does `adopt adr` write the ADR template?
* Why it matters: The existing template is intentionally placeholder-invalid and may break validation under the default `docs/**/*.md` include.
* Recommended clarification: Define destination plus exclusion/validation behavior.
* Blocking or non-blocking: Blocking.

### Internet research performed

* Source name: uv Build backend docs
* URL: https://docs.astral.sh/uv/concepts/build-backend/
* Access date: 2026-06-08
* What it was used to verify: Package-data expectations for files under the module root.
* Relevant conclusion: Wheel builds include the module under the module root; uv docs say small data is commonly stored in the module root.

* Source name: Python `importlib.metadata` docs
* URL: https://docs.python.org/3/library/importlib.metadata.html
* Access date: 2026-06-08
* What it was used to verify: `version(distribution_name)` behavior.
* Relevant conclusion: `version()` returns the installed distribution version and raises `PackageNotFoundError` when the distribution is not installed.

* Source name: YAML 1.2.2 specification
* URL: https://yaml.org/spec/1.2.2/
* Access date: 2026-06-08
* What it was used to verify: Tab indentation in YAML.
* Relevant conclusion: YAML block indentation is space-based; tab characters must not be used for indentation.

### Read-only validation performed

* `pwd`, `git status --short`, `git branch --show-current`, `git log --oneline -n 10`: confirmed repo root, branch `testing`, modified spec, and untracked `docs/codex-reviews/`.
* Inspected `docs/handoff/state.md`, `AGENTS.md`, and `docs/handoff/conventions.md`: confirmed v3 startup and repo working rules.
* `nl -ba docs/superpowers/specs/2026-06-08-adopt-cli-design.md`: inventoried current spec line references.
* `git diff -- docs/superpowers/specs/2026-06-08-adopt-cli-design.md`: compared revised spec against committed baseline.
* `rg --files`, `find src_project_standards` equivalent via `find src/project_standards`: confirmed no current bundles/adopt CLI implementation exists.
* Inspected `pyproject.toml`, `src/project_standards/registry.py`, `registry.json`, `validate_frontmatter.py`, `.project-standards.yml`, root configs, workflows, `.vscode/*`, standards READMEs/adopt guides, ADR templates, and `tests/README.md`.
* `rg` over spec and standards docs: mapped inline scaffolds, omitted Markdown Tooling scaffolds, VS Code/task references, template placeholder behavior, and ADR/template validation risk.

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
* Run only after implementation: assert Python-only adoption does not silently include Markdown-only `.vscode` settings/tasks unless the spec explicitly defines a shared superset.
* Run only after implementation: assert Markdown Tooling inline scaffolds are either packaged or explicitly marked illustrative.
* Run only after implementation: run generated `markdown-frontmatter adr` fixture through `validate-frontmatter` to prove ADR template handling does not break the starter config.

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-06-08-adopt-cli-design.md`
* Audit round: 4
* Open issue IDs: SA-005, SA-NEW-003, SA-NEW-005, SA-NEW-006
* Resolved issue IDs: SA-001, SA-002, SA-003, SA-004, SA-NEW-001, SA-NEW-002, SA-NEW-004
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: `.vscode/settings.json` and `.vscode/tasks.json` classification, omitted Markdown Tooling inline scaffolds, ADR template destination and validation behavior, and target-specific fragment reporting.