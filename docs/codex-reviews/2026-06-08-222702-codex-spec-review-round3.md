### Executive summary

Claude Code’s round-3 corrections resolved the prior custom-schema CLI gap, forwarded `validate-references` flag compatibility blocker, and pre-commit Python 3.14 portability issue. Significant findings still remain because the revised reference-resolution text now contradicts itself on section-anchor handling: one section says anchors are stripped before path existence checks, while acceptance criteria says anchors do not resolve, and the governing standard says to use document-level links, not `#` links.

New internet research was limited to rechecking official pre-commit documentation for hook metadata, `language_version`, `pass_filenames`, installability, and `try-repo`.

### Verdict

Needs minor specification correction before planning/implementation

### Audit loop status

* Audit type: Follow-up audit
* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md`
* Prior audit issue count: 4
* Resolved issue count: 3
* Still open issue count: 0
* Partially resolved issue count: 1
* New issue count: 0
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

Retested the four open round-2 issues against the current spec and current repository evidence. Checked the revised CLI surfaces, custom-schema behavior, forwarded-flag compatibility, `project-standards validate` dispatch shape, pre-commit hook assumptions, Python version requirement, reference-resolution rules, standard link conventions, schema field types, nullable relationship examples, extension-object support, current reusable workflow, and absence of new implementation files.

Could not run validators, tests, pre-commit, package-manager commands, or workflow commands because this is a read-only audit and those checks can write caches, environments, artifacts, or state.

### Prior findings status

#### SA-008: Custom-schema behavior is unspecified for new formatter/fix commands

* Previous severity: Medium
* Current status: Resolved
* Evidence: The formatter CLI now includes `--schema` at spec lines 73-76, flag compatibility is explicit at lines 79-84, and `project-standards fix` now says it skips entirely under a custom schema at line 176. This matches the current `validate-id` skip model in `src/project_standards/validate_id.py:420-430`.
* Remaining action for Claude Code: None for this issue.

#### SA-NEW-001: `validate-references` can break existing forwarded `project-standards validate` flags

* Previous severity: High
* Current status: Resolved
* Evidence: The `validate-references` CLI now includes `--schema`, `--glob`, `--no-require-frontmatter`, `--quiet`, and files at spec lines 134-139. It also defines custom-schema skip behavior and a `--no-require-frontmatter` compatibility no-op. Current `project-standards validate` forwards the same validator argv to both validators in `src/project_standards/cli.py:130-185`, so the new validator contract now covers the forwarded flags.
* Remaining action for Claude Code: None for this issue.

#### SA-NEW-002: Pre-commit Python-version portability is unspecified

* Previous severity: Medium
* Current status: Resolved
* Evidence: Spec line 180 now requires every hook to set `language_version: python3.14`, document the Python 3.14 prerequisite, and run the `try-repo` smoke in a 3.14 environment. Repository evidence confirms `pyproject.toml:8` requires Python `>=3.14`. Official pre-commit docs confirm Python hook repos must be installable with `pip install .`, hook manifests support `language_version`, and `try-repo` is the supported local hook smoke path.
* Remaining action for Claude Code: None for this issue.

#### SA-NEW-003: Reference path and nullable scalar semantics are under-specified

* Previous severity: Medium
* Current status: Partially resolved
* Evidence: Spec line 166 now defines repo-root-relative paths, exact ID matching, null/empty-value ignores, absolute path rejection, and `../` escape rejection. That resolves most of the prior ambiguity. However, the same line says any `#section` anchor is stripped before the existence check, while acceptance criterion line 188 says “absolute paths/anchors do not” resolve. The governing standard says document links should be repo-root-relative paths with extensions and says to use document-level links, not section-level `#` links, in `standards/markdown-frontmatter/README.md:395-401`.
* Remaining action for Claude Code: Make anchor semantics single-valued. Either anchors are unresolvable warnings, or anchors are stripped only after emitting a warning, or anchors are accepted as document-level resolution despite being discouraged. Align B.3, acceptance criteria, and tests to the chosen behavior.

### New blocking issues

None found.

### New non-blocking issues

None found.

### Regressions

None found.

### Remaining ambiguities and decisions needed

* Ambiguity: Whether a reference like `standards/adr/README.md#decision-outcome` should resolve, warn, or be treated as dangling.
* Why it matters: The semantic validator’s behavior and tests will differ materially depending on this choice, and the current spec gives contradictory instructions.
* Recommended clarification: Prefer the standard-aligned rule: section anchors are not valid document references; treat them as warnings or unresolvable unless a future schema revision permits them.
* Blocking or non-blocking: Non-blocking, tracked by `SA-NEW-003`.

### Internet research performed

* Source name: pre-commit official documentation
* URL: https://pre-commit.com/
* Access date: 2026-06-09
* What it was used to verify: Python hook installability, `.pre-commit-hooks.yaml` fields, `language_version`, `pass_filenames`, `validate-manifest`, and `try-repo`.
* Relevant conclusion: The revised spec now matches the official hook model: Python hook repos must install via `pip install .`, hook metadata supports `language_version`, `pass_filenames: false` is valid for whole-repo checks, and `try-repo` is an appropriate smoke test.

### Read-only validation performed

* `git status --short`, `git branch --show-current`, and `git log --oneline -n 10`: confirmed branch `testing`, dirty unrelated files, and latest spec-review round commits.
* `nl -ba docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md`: re-read the round-3 spec and line-referenced the revised requirements.
* `rg` and `nl` over `src/project_standards/cli.py`, `validate_frontmatter.py`, and `validate_id.py`: confirmed current forwarded validator flags and custom-schema skip precedent.
* `rg --files`: confirmed no current `.pre-commit-hooks.yaml`, `format_frontmatter.py`, or `validate_references.py` implementation exists.
* Inspected `pyproject.toml`, `.github/workflows/validate-markdown-frontmatter.yml`, `.project-standards.yml`, and the bundled schema: confirmed Python `>=3.14`, current console scripts, current reusable workflow shape, config shape, relationship fields, null support, and extension mappings.
* Inspected `standards/markdown-frontmatter/README.md`, managed examples, and ADR example: confirmed repo-root link convention, `applies_to` exemption, no-section-anchor convention, extension-object examples, and `superseded_by: null`.

### Recommended planning/implementation validation

* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest`
* Run only after implementation: `uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run project-standards validate --config .project-standards.yml`
* Run only after implementation: `uv run project-standards validate --schema <custom-schema> --quiet`
* Run only after implementation: `uv run project-standards validate --no-require-frontmatter --quiet`
* Run only after implementation: `uv run format-frontmatter --check --config .project-standards.yml`
* Run only after implementation: `uv run validate-references --config .project-standards.yml` with `references.enabled: true`.
* Run only after implementation: add and run tests for the clarified `#section` anchor behavior.
* Run only after implementation: `pre-commit validate-manifest .pre-commit-hooks.yaml`
* Run only after implementation: `pre-commit try-repo . format-frontmatter-check --all-files` in a Python 3.14 environment.

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md`
* Audit round: 3
* Open issue IDs: SA-NEW-003
* Resolved issue IDs: SA-001, SA-002, SA-003, SA-004, SA-005, SA-006, SA-007, SA-008, SA-NEW-001, SA-NEW-002
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: whether the spec resolves the remaining contradiction around section-anchor reference handling and aligns B.3, acceptance criteria, and tests to one deterministic rule.

