### Executive summary

Claude Code’s corrections resolve all prior open findings from round 2: the shared `.editorconfig` decision is now explicit, byte-unchanged YAML extraction has been replaced with semantic/syntax-validated extraction, and ADR `.project-standards.yml` fragment behavior is specified. Significant findings still remain because the revised spec now overgeneralizes “source templates from real working files” into consumer-facing scaffolds where this repo’s real files are not safe consumer templates, especially `.project-standards.yml` and agent instruction stubs.

New internet research was limited to re-checking the external assumptions still in scope: `uv_build` module-root packaging, `importlib.metadata.version()`, and YAML indentation rules.

### Verdict

Needs major specification correction before planning/implementation

### Audit loop status

* Audit type: Follow-up audit
* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-06-08-adopt-cli-design.md`
* Prior audit issue count: 7
* Resolved issue count: 7
* Still open issue count: 0
* Partially resolved issue count: 0
* New issue count: 2
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

Re-read the revised spec, prior round-2 ledger, git status/history, v3 handoff docs, repo instructions, package metadata, registry/validator code, root scaffolds, workflows, standards/adopt guides, tests, and release/versioning docs. Retested prior findings around shared `.editorconfig`, syntax-valid extraction, ADR fragments, packaging, safety, and acceptance criteria. Attacked the new “semantic extraction from real working files” rule against consumer-facing templates, then checked whether acceptance criteria could pass with repo-specific but syntactically valid generated files.

Could not check an implementation because none exists. I did not run tests, builds, installs, formatters, or validation commands that may write caches/artifacts.

### Prior findings status

#### SA-001: Multi-standard adoption can conflict on current overlapping scaffolds

* Previous severity: High
* Current status: Resolved
* Evidence: Decision #8 now explicitly makes the shared `.editorconfig` a reconciled superset, states the Python Tooling JSON/Markdown indentation change, requires Python-only/Markdown-only/combined tests, and records versioning impact.
* Remaining action for Claude Code: None for this issue; implementation must still update Python Tooling prose and changelog as specified.

#### SA-002: Root-level template packaging strategy conflicts with current `uv_build` resource behavior

* Previous severity: High
* Current status: Resolved
* Evidence: The spec keeps templates/manifests under `src/project_standards/bundles/<id>/` and uses the same `Path(__file__).parent` package-relative pattern as the existing schema and registry.
* Remaining action for Claude Code: Keep wheel inspection/install-run validation in the later plan.

#### SA-003: File-write safety boundaries are underspecified

* Previous severity: High
* Current status: Resolved
* Evidence: The safety contract now rejects unsafe destinations, source escapes, symlink destinations under `--force`, missing package sources, and maps I/O failures to exit 1.
* Remaining action for Claude Code: None beyond implementing the specified safety tests.

#### SA-004: Tooling inventory understates current ADR enforcement

* Previous severity: Medium
* Current status: Resolved
* Evidence: The inventory now states frontmatter validation, opt-in MADR section checks, and FM-to-ADR compatibility.
* Remaining action for Claude Code: None.

#### SA-005: Template extraction scope does not cover all current inline scaffolds clearly

* Previous severity: Medium
* Current status: Resolved
* Evidence: The spec now covers scaffolds inline in both standard READMEs and `adopt.md`, and adds a single-canonical-copy rule.
* Remaining action for Claude Code: None for extraction scope; see SA-NEW-003 for source-selection ambiguity.

#### SA-NEW-001: Byte-unchanged extraction can produce invalid workflow YAML

* Previous severity: High
* Current status: Resolved
* Evidence: The spec drops byte-unchanged extraction, requires semantic extraction from syntactically valid sources, and adds YAML/JSON/TOML parse tests plus no-tab-indentation YAML checks.
* Remaining action for Claude Code: None beyond implementing those tests.

#### SA-NEW-002: ADR config-fragment behavior is promised but not specified or tested

* Previous severity: Medium
* Current status: Resolved
* Evidence: The spec now defines `.project-standards.yml` ADR knobs as `kind = "fragment"`, says fragments are reported whether the target exists or not, and tests `adopt adr` plus `adopt markdown-frontmatter adr`.
* Remaining action for Claude Code: None.

### New blocking issues

#### SA-NEW-003: Consumer-facing scaffolds can be sourced from repo-specific working files

* Severity: High
* Status: Confirmed
* Adversarial angle: Test whether “semantic extraction from the repo’s real working files” is safe for every scaffold the CLI promises to generate.
* Spec reference: Lines 25, 28, 144, 148, 151, and 176.
* Finding: The spec is internally inconsistent and unsafe for consumer-facing templates. It says config files, including `.project-standards.yml`, are “reported, never edited,” but also lists the Markdown Frontmatter `.project-standards.yml` template as `kind=file`. It also says each template’s canonical source is the repo’s real working file and proposes byte-identical dogfood tests against root configs. That is valid for root `.markdownlint.json`, `.prettierrc.json`, `.editorconfig`, and probably `check.yml`; it is not valid for consumer templates like `.project-standards.yml`, `AGENTS.md`, or `CLAUDE.md`.
* Repository evidence: The repo root `.project-standards.yml` validates this standards repo’s own `CHANGELOG.md`, `standards/**/*.md`, and `meta/**/*.md`, and excludes `README.md` ([.project-standards.yml](/home/chris/projects/project-standards/.project-standards.yml:14)). The consumer adoption guide instead starts with `README.md` and `docs/**/*.md` ([standards/markdown-frontmatter/adopt.md](/home/chris/projects/project-standards/standards/markdown-frontmatter/adopt.md:69)). Root `AGENTS.md` is project-standards-specific and handoff-v3-specific ([AGENTS.md](/home/chris/projects/project-standards/AGENTS.md:3)), while the Python Tooling README contains generic agent templates ([standards/python-tooling/README.md](/home/chris/projects/project-standards/standards/python-tooling/README.md:975)).
* External research evidence: Not applicable.
* Why it matters: Acceptance could pass with syntactically valid files that do not satisfy the user goal. A generated `.project-standards.yml` copied from this repo could validate zero consumer docs or omit `README.md`/`docs/**/*.md`; generated agent stubs could copy repo-specific handoff instructions into unrelated consumers.
* Recommended action for Claude Code: Split templates into “dogfoodable root artifacts” and “curated consumer scaffolds.” State explicitly whether Markdown Frontmatter adoption writes a full `.project-standards.yml` when absent, reports a fragment when present, or always reports only. Exempt curated consumer scaffolds from root byte-identical dogfood tests and define their expected generic contents.
* Suggested validation: Add tests that generated consumer `.project-standards.yml` includes generic consumer paths, does not copy this repo’s `standards/**`/`meta/**` scope, and validates a fixture `README.md`/`docs/**/*.md`. Add tests that generated `AGENTS.md`/`CLAUDE.md` stubs contain generic Python Tooling text and no `docs/handoff` or project-standards repo-specific content.

### New non-blocking issues

#### SA-NEW-004: Partial-write recovery is named but not made testable

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Attack `--force` and I/O-failure paths for data-corruption behavior, not just exit code.
* Spec reference: Lines 119, 127, 140, 167, and 182.
* Finding: The spec maps “partial-write failure” to exit 1, but does not define whether writes are atomic, whether an existing file must remain intact on failed `--force`, or whether temporary files are cleaned up. The test list covers permission-denied exit behavior, not partial write rollback.
* Repository evidence: No implementation exists yet; this is a specification omission. The stated safety goal is CI/agent-safe, deterministic, and non-destructive by default, while `--force` intentionally overwrites regular files.
* External research evidence: Not applicable.
* Why it matters: A failed overwrite could truncate or corrupt a workflow/config while still satisfying the current “exit 1, no traceback” contract.
* Recommended action for Claude Code: Specify atomic write semantics for file and workflow-caller artifacts: write to a temp file in the target directory, then replace regular files only after the full write succeeds; preserve existing files on write failure; clean temp files on failure.
* Suggested validation: Add a failure-injection test for `--force` where the write fails after opening/writing a temp path, asserting the original file remains unchanged and the command exits 1.

### Regressions

None found.

### Remaining ambiguities and decisions needed

* Ambiguity: Is `.project-standards.yml` a full generated file for Markdown Frontmatter adoption, or always a reported fragment because it is a config file?
* Why it matters: The spec currently says both, which blocks reliable manifest design and acceptance testing.
* Recommended clarification: Define absent-target and existing-target behavior separately for Markdown Frontmatter’s full config and ADR’s config fragment.
* Blocking or non-blocking: Blocking.

* Ambiguity: Which artifacts are allowed to be byte-identical to this repo’s root files?
* Why it matters: Some root files are repo-specific, while others are true canonical shared configs.
* Recommended clarification: Enumerate dogfoodable root artifacts and curated consumer scaffolds separately.
* Blocking or non-blocking: Blocking.

* Ambiguity: Must `--force` preserve the original file if a write fails?
* Why it matters: This controls data-corruption risk during scaffolding.
* Recommended clarification: Specify atomic write/rollback expectations.
* Blocking or non-blocking: Non-blocking.

### Internet research performed

* Source name: uv Build backend docs
* URL: https://docs.astral.sh/uv/concepts/build-backend/
* Access date: 2026-06-08
* What it was used to verify: Whether package data under `src/project_standards/` is still a supported wheel layout.
* Relevant conclusion: Wheels include the module under the module root; uv docs state small data is commonly stored under the module root.

* Source name: Python `importlib.metadata` docs
* URL: https://docs.python.org/3/library/importlib.metadata.html
* Access date: 2026-06-08
* What it was used to verify: `importlib.metadata.version()` behavior and failure class.
* Relevant conclusion: `version(distribution_name)` returns the installed distribution version and raises `PackageNotFoundError` when not installed.

* Source name: YAML 1.2.2 specification
* URL: https://yaml.org/spec/1.2.2/
* Access date: 2026-06-08
* What it was used to verify: Whether tab-indented YAML workflow templates are valid.
* Relevant conclusion: YAML block indentation is spaces; tabs must not be used in indentation.

### Read-only validation performed

* `pwd && git status --short && git branch --show-current && git log --oneline -n 10`: confirmed repo root, branch `testing`, modified spec, untracked `docs/codex-reviews/`, and recent commit history.
* Inspected `docs/handoff/state.md`, `AGENTS.md`, `docs/handoff/conventions.md`, and the handoff-system-v3 skill summary: confirmed repo startup rules and v3 layout.
* `nl -ba docs/superpowers/specs/2026-06-08-adopt-cli-design.md`: inventoried current spec with line references.
* `git diff -- docs/superpowers/specs/2026-06-08-adopt-cli-design.md`: compared the current revision against the committed spec.
* `rg` over the spec, source, tests, and standards: mapped referenced commands, artifacts, manifests, bundles, entry points, and template claims.
* Inspected `pyproject.toml`, `src/project_standards/registry.py`, `src/project_standards/validate_frontmatter.py`, `registry.json`, `.project-standards.yml`, root configs, workflows, standards READMEs/adopt guides, tests, `README.md`, `CHANGELOG.md`, and `meta/versioning.md`.
* `find src_project_standards`/`find standards`/`find tests`: confirmed no current `bundles/` tree or CLI implementation exists yet, and current tests are validator/markdownlint focused.
* `nl` inspections of `.project-standards.yml`, `standards/markdown-frontmatter/adopt.md`, `AGENTS.md`, `CLAUDE.md`, and Python Tooling agent templates: confirmed consumer-template source ambiguity.

### Recommended planning/implementation validation

* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest`
* Run only after implementation: `uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`
* Run only after implementation: build the wheel, inspect wheel contents, install from the wheel, then run installed `project-standards list` and `project-standards adopt ... --dry-run`.
* Run only after implementation: parse every generated YAML/JSON/TOML artifact and assert no tab-indented YAML.
* Run only after implementation: adoption matrix for each standard alone, `markdown-frontmatter adr`, `markdown-tooling python-tooling`, and all four together.
* Run only after implementation: assert generated Markdown Frontmatter config is a consumer template, not this repo’s root `.project-standards.yml`.
* Run only after implementation: assert generated agent stubs are generic and contain no repo-specific handoff/project-standards instructions.
* Run only after implementation: failure-injection tests for atomic writes and `--force` preservation on partial write failure.

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-06-08-adopt-cli-design.md`
* Audit round: 3
* Open issue IDs: SA-NEW-003, SA-NEW-004
* Resolved issue IDs: SA-001, SA-002, SA-003, SA-004, SA-005, SA-NEW-001, SA-NEW-002
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: consumer-template source classification, `.project-standards.yml` write-vs-fragment behavior, dogfood byte-identical test scope, generated agent-stub content, and atomic write/partial-failure semantics.