### Executive summary

Claude Code’s corrections resolved the major round-1 formatter, ID-safety, workflow, extension-object, `applies_to`, scaffold-placeholder, and pre-commit smoke-test gaps. Significant findings still remain because the revised spec introduces a CLI compatibility blocker: extending `project-standards validate` to call `validate-references` can break existing `--schema` / `--no-require-frontmatter` invocations unless the new validator accepts those forwarded flags.

New internet research was required for the pre-commit hook assumptions. Official pre-commit docs confirm that Python hooks install the repo with `pip install .` and default to the system Python unless `language_version` is specified, which matters because this repo requires Python `>=3.14`.

### Verdict

Needs major specification correction before planning/implementation

### Audit loop status

* Audit type: Follow-up audit
* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md`
* Prior audit issue count: 8
* Resolved issue count: 7
* Still open issue count: 0
* Partially resolved issue count: 1
* New issue count: 3
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

Retested all prior `SA-*` findings against the revised spec and current repository evidence. Rechecked formatter ordering, `doc_type` inference, `project-standards fix`, reusable workflow coverage, extension-object handling, `applies_to` semantics, custom-schema behavior, pre-commit acceptance criteria, current CLI flag forwarding, schema fields, managed examples, and frontmatter standard link conventions.

Could not run validators, tests, pre-commit, or package-manager commands because this is a read-only audit and those commands can write caches, environments, or artifacts.

### Prior findings status

#### SA-001: Unconditional `doc_type` path inference contradicts current managed docs and can break IDs

* Previous severity: High
* Current status: Resolved
* Evidence: Spec lines 50 and 89-90 now make path inference fill/correct-only and explicitly preserve valid explicit `doc_type`; current `standards/*/README.md` files remain valid `doc_type: 'reference'` documents.
* Remaining action for Claude Code: None for this issue.

#### SA-002: `project-standards fix` order can exit clean while leaving invalid IDs

* Previous severity: High
* Current status: Resolved
* Evidence: Spec lines 59, 169, and 182 now require format first, then `validate-id --fix`, then final read-only validation with fixtures covering `type:` plus invalid ID, missing arrays plus invalid ID, and path-inferred `doc_type`.
* Remaining action for Claude Code: None for this issue.

#### SA-003: Consumer reusable workflow is missing from the `validate-references` rollout

* Previous severity: High
* Current status: Resolved
* Evidence: Spec lines 59, 171, 175, and 182 now require the reusable consumer workflow to run the reference validator and include a test asserting that invocation.
* Remaining action for Claude Code: None for this issue.

#### SA-004: Unsupported-YAML rule excludes schema-valid extension objects

* Previous severity: High
* Current status: Resolved
* Evidence: Spec lines 100, 122, 180, and 191 now treat `publish`/`project`/`x_project` as opaque extension mappings whose nested content is preserved byte-for-byte.
* Remaining action for Claude Code: None for this issue.

#### SA-005: `applies_to` is incorrectly treated as a document reference

* Previous severity: Medium
* Current status: Resolved
* Evidence: Spec lines 149 and 156 explicitly exclude `applies_to` from the repo index and referential-integrity checks, matching `standards/markdown-frontmatter/README.md`.
* Remaining action for Claude Code: None for this issue.

#### SA-006: Scaffold placeholder can pass all stated acceptance while remaining incomplete

* Previous severity: Medium
* Current status: Resolved
* Evidence: Spec lines 113 and 118 now acknowledge the schema-valid `TODO:` placeholder and require `--write` to report scaffolded files distinctly as author action items.
* Remaining action for Claude Code: None for this issue.

#### SA-007: Pre-commit hook acceptance is too weak

* Previous severity: Medium
* Current status: Resolved
* Evidence: Spec lines 173, 175, and 182 now require hook language, hook IDs, filename behavior, console-script mapping, `pre-commit validate-manifest`, and a `try-repo` smoke test.
* Remaining action for Claude Code: None for this issue; see `SA-NEW-002` for a separate Python-version portability gap.

#### SA-008: Custom-schema behavior is unspecified for new formatter/fix commands

* Previous severity: Medium
* Current status: Partially resolved
* Evidence: Spec lines 59, 82, 169, and 180 now say `format-frontmatter` and `fix` skip under custom schemas. However, the `format-frontmatter` CLI surface at lines 73-75 does not include `--schema`, while line 82 refers to `--schema` being passed; line 169 only says `fix` forwards `--config`, not whether `--schema` is accepted and propagated.
* Remaining action for Claude Code: Add `--schema` to the formatter/fix CLI contract and tests, or remove `--schema` from the custom-schema rule and define config-only behavior.

### New blocking issues

#### SA-NEW-001: `validate-references` can break existing forwarded `project-standards validate` flags

* Severity: High
* Status: Confirmed
* Adversarial angle: An additive validator can violate the spec’s own “current flags must not change” invariant.
* Spec reference: Lines 63, 133, 169-170.
* Finding: The spec extends `project-standards validate` to call `validate_references.main(…)`, but the new `validate-references` CLI surface does not accept existing forwarded flags such as `--schema` and `--no-require-frontmatter`. Current `project-standards validate` forwards those flags to both validators, and `validate-id` explicitly accepts `--no-require-frontmatter` for compatibility.
* Repository evidence: `src/project_standards/cli.py` advertises and forwards `--schema`, `--glob`, `--no-require-frontmatter`, `--quiet`, and files; `src/project_standards/validate_id.py` accepts `--schema` and hidden `--no-require-frontmatter`; `src/project_standards/validate_frontmatter.py` accepts both.
* External research evidence: Not applicable.
* Why it matters: Existing valid commands like `project-standards validate --schema custom.json --quiet` could start failing with argparse errors after a minor release, contradicting lines 63 and 67.
* Recommended action for Claude Code: Specify that `validate-references` accepts all flags forwarded by `project-standards validate`. Define custom-schema behavior, likely skip-with-note like `validate-id`, and make `--no-require-frontmatter` a compatibility no-op.
* Suggested validation: Add tests for `project-standards validate --schema <custom> --quiet`, `project-standards validate --no-require-frontmatter --quiet`, and the same flags with `references.enabled: true`.

### New non-blocking issues

#### SA-NEW-002: Pre-commit Python-version portability is unspecified

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Hook smoke tests can pass locally while consumers without Python 3.14 cannot install the hook repo.
* Spec reference: Lines 173, 175, 182, 203.
* Finding: The spec requires `language: python` hooks but does not address this repo’s `requires-python = ">=3.14"`. Official pre-commit docs say Python hooks install the repository with `pip install .` and default to the system Python unless `language_version` is set.
* Repository evidence: `pyproject.toml` requires Python `>=3.14`; no `.pre-commit-hooks.yaml` exists yet.
* External research evidence: Official pre-commit documentation, https://pre-commit.com/, accessed 2026-06-09, documents Python hook installation via `pip install .` and `language_version` behavior.
* Why it matters: Consumers can adopt the hook manifest and fail before the tool runs if their default pre-commit Python is below 3.14.
* Recommended action for Claude Code: Specify whether hooks set `language_version: python3.14`, document the Python 3.14 prerequisite, and validate the hook in a CI environment that has Python 3.14 available.
* Suggested validation: Run only after implementation: `pre-commit validate-manifest .pre-commit-hooks.yaml` and `pre-commit try-repo . format-frontmatter-check --all-files` in an environment where the intended Python version is explicit.

#### SA-NEW-003: Reference path and nullable scalar semantics are under-specified

* Severity: Medium
* Status: Confirmed
* Adversarial angle: A semantic validator can produce false positives or false negatives if “existing file path” and nullable fields are not defined.
* Spec reference: Lines 149, 156-157, 184.
* Finding: The spec says references resolve to an existing file path or known ID, but does not define the path base, normalization, section-anchor handling, or how `superseded_by: null` is treated. The standard says document links should be repo-root-relative paths with extensions and no section anchors.
* Repository evidence: `standards/markdown-frontmatter/README.md` defines repo-root-relative path convention and excludes section links; `standards/adr/examples/adr.example.md` has `superseded_by: null` in managed frontmatter.
* External research evidence: Not applicable.
* Why it matters: Implementations could resolve paths relative to the current file or cwd, treat `null` as a dangling reference, or accept section anchors the standard discourages.
* Recommended action for Claude Code: Define reference normalization precisely: repo-root-relative paths with extensions, no absolute paths, no section anchors, IDs matched exactly, and `superseded_by: null` ignored.
* Suggested validation: Add fixtures for repo-root paths, same-basename paths in different directories, section anchors, absolute paths, known IDs, external IDs, and `superseded_by: null`.

### Regressions

None found.

### Remaining ambiguities and decisions needed

* Ambiguity: Whether `format-frontmatter` and `project-standards fix` accept `--schema` as a CLI flag or only inspect config-level custom schemas.
* Why it matters: The spec references `--schema` but omits it from the formatter CLI surface and fix forwarding contract.
* Recommended clarification: Add the flag and propagation semantics, or remove the flag reference.
* Blocking or non-blocking: Non-blocking, tracked by `SA-008`.

* Ambiguity: Whether `validate-references` should skip, warn, or run under custom schemas.
* Why it matters: Existing `project-standards validate --schema` must remain compatible.
* Recommended clarification: Mirror `validate-id` skip behavior for custom schemas.
* Blocking or non-blocking: Blocking, tracked by `SA-NEW-001`.

* Ambiguity: Exact reference resolution rules for paths, IDs, `null`, and anchors.
* Why it matters: A semantic validator needs deterministic behavior.
* Recommended clarification: Define repo-root path resolution and nullable-field handling.
* Blocking or non-blocking: Non-blocking, tracked by `SA-NEW-003`.

### Internet research performed

* Source name: pre-commit official documentation
* URL: https://pre-commit.com/
* Access date: 2026-06-09
* What it was used to verify: Python hook installation, `.pre-commit-hooks.yaml` fields, `pass_filenames`, `validate-manifest`, `try-repo`, and `language_version`.
* Relevant conclusion: The revised spec correctly adds manifest and smoke validation, but should also address Python version selection because the hook repo requires Python `>=3.14`.

### Read-only validation performed

* `git status --short`, `git branch --show-current`, and `git log --oneline -n 10`: confirmed branch `testing`, dirty unrelated files, and the round-1 spec commit.
* `nl -ba docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md`: re-read the revised spec and line-referenced requirements.
* `rg` over the revised spec: checked all prior finding areas and new CLI/pre-commit/custom-schema claims.
* Inspected `.project-standards.yml`, `pyproject.toml`, `.github/workflows/validate-markdown-frontmatter.yml`, `src/project_standards/cli.py`, `validate_frontmatter.py`, `validate_id.py`, and the bundled schema.
* Used `rg` to confirm no current `.pre-commit-hooks.yaml`, `format_frontmatter.py`, or `validate_references.py` exists.
* Inspected Markdown Frontmatter standard sections for `applies_to`, extension objects, link conventions, and managed examples.

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
* Run only after implementation: `uv run validate-references --config .project-standards.yml` with references enabled.
* Run only after implementation: `pre-commit validate-manifest .pre-commit-hooks.yaml`
* Run only after implementation: `pre-commit try-repo . format-frontmatter-check --all-files`

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-06-08-frontmatter-suite-design.md`
* Audit round: 2
* Open issue IDs: SA-008, SA-NEW-001, SA-NEW-002, SA-NEW-003
* Resolved issue IDs: SA-001, SA-002, SA-003, SA-004, SA-005, SA-006, SA-007
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: forwarded CLI flag compatibility for `validate-references`, custom-schema semantics for formatter/fix/reference validation, pre-commit Python 3.14 behavior, and exact reference-resolution/null handling.

