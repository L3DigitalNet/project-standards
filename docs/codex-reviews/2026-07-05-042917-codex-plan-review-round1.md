### Executive summary

The implementation plan needs major correction before Claude Code executes it. The core splice approach is plausible and mostly aligned with the repo, but two blocking issues remain: the H1 tier suffix rewrite can silently fail while validation still passes, and the plan’s final validation gate omits the repo’s `Validate Specs` CI workflow, which is triggered by this plan’s `src/**` and Markdown changes and appears incompatible with the current `.project-standards.yml` state.

Internet research was required for Python stdlib filesystem assumptions. Official Python 3.14 docs support the plan’s use of `mkstemp` + `os.replace` for race-resistant temp creation and atomic same-filesystem replacement; no stale external-doc conflict was found there.

### Verdict

Needs major correction before execution

### Audit loop status

* Audit type: First audit
* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-07-05-project-spec-tooling-spec3.md
* Significant findings remaining: Yes
* Blocking issue count: 2
* Non-blocking issue count: 1

### What the plan gets right

The plan correctly identifies the existing `specs/cli.py`, `commands/new.py`, validator, registry, and bundled templates as the relevant integration points. It preserves the repo’s Python 3.14, Ruff, BasedPyright, coverage, and pip-audit gates from `pyproject.toml`. It also correctly reuses the existing atomic-write pattern and avoids introducing a repo-config dependency for `upgrade`.

### Adversarial review performed

I inventoried the plan’s claims about file paths, new modules, CLI flags, JSON codes, validation gates, fixture construction, template locations, write safety, and docs updates. I checked them against the actual source tree, current `specs/cli.py`, `commands/new.py`, `validate.py`, `registry.py`, template files, tests, `.project-standards.yml`, CI workflows, and git state.

I attacked the validation claims by looking for outputs that could pass `validate_document()` while violating the plan’s intended behavior. The strongest false-positive path found is a malformed or edited H1 tier suffix: the planned implementation returns unchanged text if the regex misses, and the current validator does not check H1/profile consistency.

I did not run tests because the task is read-only and the relevant test commands can write caches or artifacts.

### Blocking issues

#### CR-001: H1 tier suffix rewrite can silently fail while validation still passes

* Severity: High
* Status: Confirmed
* Adversarial angle: Validation false positive / silent contract violation
* Plan reference: Lines 5, 40, 92, 149-159, 534-540, 887-895
* Finding: The planned `_rewrite_h1_suffix()` performs a regex substitution but does not verify that a substitution occurred. If a validate-clean source has an edited H1, missing suffix, ASCII hyphen instead of the expected em dash, or otherwise non-matching heading, `upgrade_text()` will still update `profile:` and return output whose H1 still says the old tier or no tier. The output self-validation gate will not catch this because the current validator checks frontmatter, numbered sections, appendices, references, IDs, and tables, but not H1 tier/profile consistency.
* Repository evidence: The plan’s regex returns `_H1_SUFFIX.sub(..., count=1)` with no replacement count check. Current `validate_document()` dispatches only `_check_frontmatter`, `_check_sections`, `_check_appendices`, `_check_references`, `_check_ids`, and `_check_tables`; no H1 check exists in `src/project_standards/specs/commands/validate.py:33-42`. The bundled template H1 has the expected tier suffix at `src/project_standards/specs/templates/spec-light-template.md:19`, but current validation does not enforce that shape.
* External research evidence: Not applicable.
* Why it matters: The plan promises additive tier promotion with the target tier reflected in the document. A stale H1 is user-visible, can mislead implementers, and can pass all planned runtime gates. This directly violates the plan’s own “output validates”/“template-faithful” intent because validation would not prove the intended behavior.
* Recommended action for Claude Code: Make `_rewrite_h1_suffix` strict. Either return a replacement count and raise/refuse when no H1 suffix is rewritten, or add an explicit precheck that the source H1 is canonical for its declared tier. Add validation after rewrite that the H1 contains the target tier.
* Suggested validation: Add tests for missing H1 suffix, wrong dash, old tier suffix not rewritten, and successful rewrite. Assert the bad cases return `source_not_upgradeable` or `self_validation_failed` and never write output.

#### CR-002: Final gate omits the repo’s triggered `Validate Specs` CI workflow

* Severity: High
* Status: Confirmed
* Adversarial angle: CI/deployment validation gap
* Plan reference: Lines 1056-1064
* Finding: The plan’s full gate omits `project-standards spec validate`, but this repo has a `Validate Specs` workflow that is triggered on pull requests touching `src/**`, Markdown, `.project-standards.yml`, or `pyproject.toml`. This implementation plan changes both `src/**` and Markdown files, so the workflow is relevant. Current `.project-standards.yml` has no top-level `spec:` block, while `collect_spec_paths()` raises `DiscoveryError` when no explicit files and no `spec.include` are present. The plan does not account for that CI path.
* Repository evidence: `.github/workflows/validate-specs.yml:11-16` triggers on PRs touching `src/**` and Markdown, and `.github/workflows/validate-specs.yml:55-57` runs `uv run project-standards spec validate --config ...` for this repo. `.project-standards.yml:1-62` contains no `spec:` block. `src/project_standards/specs/config.py:67-72` raises when no `spec.include` exists. The plan’s full gate at lines 1060-1062 includes Ruff, BasedPyright, coverage, pip-audit, and frontmatter validation, but not `spec validate`.
* External research evidence: Not applicable.
* Why it matters: Claude Code can follow the plan exactly, get the listed local gate green, and still fail the repo’s CI. This is a material executability gap, especially because the plan modifies the command whose workflow validation surface is already present.
* Recommended action for Claude Code: Before implementation, verify the current `Validate Specs` workflow behavior in a safe post-implementation validation context. Then either add the missing command to the plan’s validation section and fix the config/workflow mismatch, or explicitly revise the workflow/config as part of this plan if that is in scope.
* Suggested validation: After corrections and implementation, run the workflow-equivalent command `uv run project-standards spec validate --config .project-standards.yml` and ensure it exits successfully, or update the workflow/config so it has a deliberate non-vacuous target.

### Non-blocking issues

#### CR-003: Heading segmentation lacks an explicit fenced-code adversarial test

* Severity: Medium
* Status: Needs Claude verification
* Adversarial angle: Parser/splice robustness on validate-clean Markdown
* Plan reference: Lines 226-251, 389-418, 646-715
* Finding: `_top_blocks` and `_sub_blocks` split on raw `^## ` and `^### ` regexes without tracking fenced code blocks. A validate-clean authored section can plausibly include a Markdown example or code fence containing heading-looking lines. The current plan may fail closed via `check_upgradeable`, but it does not state or test that behavior. If the intent is to upgrade every validate-clean canonical spec, this is an under-specified edge case.
* Repository evidence: Current validators do not generally reject arbitrary non-numbered Markdown headings or heading-looking content inside sections; section validation is focused on numbered canonical headings and top-level gap coverage in `validate.py:81-104`. Existing templates already include fenced code blocks in Standard/Full templates, though the bundled examples inspected did not contain `## ` inside those fences.
* External research evidence: Not applicable.
* Why it matters: Specs commonly include Markdown snippets, Mermaid labels, shell output, or docs examples. A regex-only splicer should either explicitly reject such sources with a clear `source_not_upgradeable` reason or avoid splitting inside fenced blocks.
* Recommended action for Claude Code: Add tests with fenced code containing `## Example` and `### Example` inside an authored source section. Decide whether this is supported or deliberately refused, and document the behavior in the plan.
* Suggested validation: Add a pure `check_upgradeable` test and a CLI JSON test proving the chosen behavior.

### Missing considerations

* Blocking: H1/profile consistency must be enforced because current validation does not prove it.
* Blocking: CI parity must include the `Validate Specs` workflow or explicitly fix/skip its current config mismatch.
* Non-blocking: Fenced-code heading handling should be tested or deliberately documented as non-upgradeable.
* Non-blocking: The plan should add tests for `source_read_error`, `mkdir_failed`, `write_failed`, and `self_validation_failed` before relying on coverage pressure to discover missing branches.
* Non-blocking: The plan should state how `upgrade` reports a canonical-shape refusal for authored but unsupported Markdown constructs, so users are not surprised by `validate`-clean but non-upgradeable specs.

### Internet research performed

* Source name: Python 3.14 `os.replace` documentation
* URL: https://docs.python.org/3.14/library/os.html#os.replace
* Access date: 2026-07-05
* What it was used to verify: Atomic replacement and overwrite behavior.
* Relevant conclusion: `os.replace` replaces an existing file when permitted and successful renaming is atomic on POSIX, supporting the plan’s same-directory temp + replace approach.

* Source name: Python 3.14 `os.path.samefile` documentation
* URL: https://docs.python.org/3.14/library/os.path.html#os.path.samefile
* Access date: 2026-07-05
* What it was used to verify: Same-file detection for `-o OUT` equal to source.
* Relevant conclusion: `samefile` compares device/inode and raises if `stat` fails, so the plan’s exists-guarded use is directionally appropriate.

* Source name: Python 3.14 `tempfile.mkstemp` documentation
* URL: https://docs.python.org/3.14/library/tempfile.html#tempfile.mkstemp
* Access date: 2026-07-05
* What it was used to verify: Secure temporary file creation assumptions.
* Relevant conclusion: `mkstemp` is documented as race-resistant when the platform implements `O_EXCL`, and callers are responsible for cleanup, matching the plan’s cleanup path.

### Items Claude Code should verify before correcting the plan

* Verify whether `uv run project-standards spec validate --config .project-standards.yml` currently fails due to the missing `spec:` block, and decide whether this plan should fix that workflow/config mismatch.
* Verify whether H1 tier/profile consistency belongs in `upgrade` only or should become a validator rule.
* Verify whether fenced-code heading-like lines should be supported by the splicer or refused as non-canonical source shape.
* Verify that the final fixture triple is built against the bundled package templates used by `TEMPLATES_DIR`, not only the canonical `standards/project-spec/templates` copies, even though the current byte-identity test says they match.
* Verify that the final implementation still passes existing `spec new` symlink, mode preservation, and interrupt cleanup tests after extracting `_safe_atomic_write`.

### Suggested corrections for Claude Code's plan

* Add a strict H1 suffix rewrite contract: no match means refusal or self-validation failure, not silent success.
* Add tests for malformed/missing/stale H1 suffix and assert JSON error behavior.
* Add the `Validate Specs` CI-equivalent command to the final validation plan, or revise the workflow/config mismatch as an explicit task.
* Add fenced-code heading tests for `_top_blocks`/`_sub_blocks`/`check_upgradeable`.
* Add explicit branch tests for unreadable/non-UTF-8 source, `mkdir_failed`, `write_failed`, and forced `self_validation_failed`.
* Update the final gate checklist so it proves both local toolchain health and CI-relevant workflow behavior.

### Read-only validation performed

* `pwd`: Confirmed repository root is `/home/chris/projects/project-standards`.
* `git status --short && git branch --show-current && git log --oneline -n 10`: Confirmed branch `testing`, ahead of origin, with untracked codex review docs and recent Spec #3 plan/design commits.
* `sed -n` on the implementation plan: Read the full plan under audit.
* `rg --files`: Inventoried repository files and relevant source/test/doc areas.
* `sed -n` on `docs/superpowers/specs/2026-07-05-project-spec-tooling-spec3-design.md`: Checked design claims against the plan.
* `sed -n` on `src/project_standards/specs/cli.py`: Confirmed current `new` implementation, JSON error machinery, symlink guard, atomic write pattern, and current `_VERBS`.
* `sed -n` on `src/project_standards/specs/commands/new.py`: Confirmed `_rewrite_frontmatter` and H1 rewrite behavior available for reuse.
* `sed -n` on `src/project_standards/specs/registry.py`: Confirmed bundled template location, tier files, frontmatter splitting, heading parsing, and registry derivation.
* `sed -n` on `src/project_standards/specs/commands/validate.py`: Confirmed validation does not check H1/profile consistency.
* `rg` on templates and fixtures: Confirmed tier sections, appendices, omission notes, and fenced code presence in Standard/Full templates.
* `cmp -s` on canonical vs bundled templates: Confirmed current `standards/project-spec/templates` files are byte-identical to `src/project_standards/specs/templates`.
* `sed -n` on `.github/workflows/validate-specs.yml`, `.project-standards.yml`, and `specs/config.py`: Confirmed the CI workflow/config validation gap.
* Official Python docs lookup: Verified `os.replace`, `os.path.samefile`, and `tempfile.mkstemp` assumptions.

### Recommended implementation validation

* Run only after implementation: `uv run pytest tests/test_spec_upgrade_fixtures.py tests/test_spec_upgrade.py tests/test_spec_upgrade_cli.py -v`
* Run only after implementation: `uv run pytest tests/test_spec_new_cli.py tests/test_spec_new.py -v`
* Run only after implementation: `uv run project-standards spec validate --config .project-standards.yml`
* Run only after implementation: `uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit && uv run validate-frontmatter --config .project-standards.yml`
* Run only after implementation: exercise `upgrade` manually or via tests for default preview, `--json` preview, `-i`, `-o`, existing output without/with `--force`, source symlink, output symlink, symlinked parent, and malformed H1.

### Final recommendation

Claude Code should revise the plan using the findings above

### Review ledger for next loop

* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-07-05-project-spec-tooling-spec3.md
* Audit round: 1
* Open issue IDs: CR-001, CR-002, CR-003
* Resolved issue IDs: None
* Superseded issue IDs: None
* Significant findings remaining: Yes
* Next audit should focus on: H1/profile consistency enforcement, CI `Validate Specs` workflow parity, and fenced-code heading behavior.