### Executive summary

The implementation plan needs correction before Claude Code executes it. The broad direction matches the repository: `format.yml` is currently repo-local, `markdown_tooling` is still `1.0`, Prettier is pinned in `package.json`, and the docs still contain DEC-9/no-workflow claims.

Internet research was required because the plan depends on current GitHub Actions, Prettier, and markdownlint-cli2 behavior. The main stale-assumption finding is that the proposed behavioral coherence test writes its test file outside the repository, but Prettier resolves configuration from the formatted file’s location upward, so that test will not necessarily use this repo’s `.prettierrc.json`.

### Verdict

Needs major correction before execution

### Audit loop status

* Audit type: First audit
* Plan path: `/home/chris/projects/project-standards/docs/superpowers/plans/2026-07-06-markdown-tooling-formatter-authority.md`
* Significant findings remaining: Yes
* Blocking issue count: 2
* Non-blocking issue count: 2

### What the plan gets right

* Correctly identifies the existing DEC-9 mismatch: Prettier is repo-enforced but not shipped as a reusable consumer workflow.
* Correctly keeps `lint-markdown.yml` and `validate-markdown-frontmatter.yml` out of scope.
* Correctly plans to add `markdownlint-cli2` to `package.json` and `package-lock.json`, matching `markdownlint-cli2-action@v23`’s bundled `markdownlint-cli2` version.
* Correctly treats the new Prettier workflow as opt-in/additive and a `markdown_tooling` minor contract bump.

### Adversarial review performed

I inventoried and falsified plan claims against the plan file, current workflows, package files, registry/config files, adopt engine, adopt tests, Markdown tooling docs, AGENTS/CLAUDE instructions, ignore files, and test/tooling configuration. I attacked the key assumptions around reusable workflow syntax, input coercion, pinned tool versions, config discovery, package/adopt behavior, type/lint compatibility, validation false positives, and final green-gate sequencing.

I did not run tests, `npm ci`, formatters, or build commands because this audit is read-only and those commands may create caches, `node_modules`, coverage artifacts, or build outputs.

### Blocking issues

#### CR-001: Behavioral coherence test does not prove the shipped Prettier config

* Severity: High
* Status: Confirmed
* Adversarial angle: Validation false positive / config-discovery mismatch
* Plan reference: Task 6, lines 565 and 590-612
* Finding: The plan claims the behavioral test consumes the root `.prettierrc.json`, but the proposed code writes `tmp_path / "adversarial.md"` outside the repository and invokes Prettier without `--config`. Prettier resolves configuration starting from the file being formatted, not from `cwd`, so the test can run with default Prettier options instead of the shipped config.
* Repository evidence: The proposed `_prettier_write` runs `node_modules/.bin/prettier --write /tmp/.../adversarial.md` with `cwd=_REPO`, but no `--config` argument. The repo’s actual `.prettierrc.json` is at the repository root.
* External research evidence: Prettier’s official configuration docs say configuration is resolved from the location of the formatted file upward. Prettier CLI docs confirm `prettier . --check` and `--write` behavior and config/ignore mechanics.
* Why it matters: The central guarantee of the plan is co-satisfaction of the shipped `.prettierrc.json` and `.markdownlint.json`. This test can pass or fail without testing that guarantee.
* Recommended action for Claude Code: Revise the test to pass explicit config paths, at least `--config <repo>/.prettierrc.json` for Prettier and preferably `--config <repo>/.markdownlint.json` or the repo `.markdownlint-cli2.jsonc` for markdownlint. Alternatively, place the temp file under a repo temp directory that is safely ignored and cleaned, but explicit config is cleaner.
* Suggested validation: After implementation, run `npm ci` and then `uv run pytest tests/coherence/test_behavioral.py -v`; include a negative test that changes/copies config options and proves the behavioral test is actually using the intended config.

#### CR-002: Proposed Python test/support code is not compatible with the repo’s strict gates

* Severity: High
* Status: Confirmed
* Adversarial angle: Executability as written
* Plan reference: Task 3 lines 185-186; Task 5 lines 470-518 and 541-543; Task 6 lines 574-575
* Finding: Several proposed snippets use bare `dict` type annotations under `basedpyright` strict mode, and Task 6 imports `shutil` without using it. The plan expects `uv run basedpyright tests/coherence` and the full Ruff gate to pass, but the code as written is likely to fail those gates.
* Repository evidence: `pyproject.toml` sets `typeCheckingMode = "strict"`, `include = ["src", "tests"]`, and `failOnWarnings = true`. The plan proposes `_load() -> dict`, `Callable[[dict, dict], bool]`, and `check_conformance(markdownlint: dict, prettier: dict)`, plus an unused `shutil` import.
* External research evidence: Not applicable.
* Why it matters: The plan’s own green gate includes Ruff and basedpyright. Following the plan literally can produce a non-green implementation even when behavior is otherwise correct.
* Recommended action for Claude Code: Replace bare `dict` annotations with `dict[str, Any]`, `Mapping[str, Any]`, or typed aliases plus casts where JSON/YAML parsing returns `Any`. Remove the unused `shutil` import or actually use it. Prefer parsing YAML/JSON into typed helper structures before assertion-heavy tests.
* Suggested validation: Run `uv run ruff check tests/coherence tests/test_format_workflow.py tests/test_registry_markdown_tooling.py` and `uv run basedpyright tests/coherence tests/test_format_workflow.py tests/test_registry_markdown_tooling.py` after writing the tests.

### Non-blocking issues

#### CR-003: Registry dogfood test can pass without updating `markdown_tooling.version`

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Validation false positive
* Plan reference: Task 2 lines 119-124 and 147-149
* Finding: `test_dogfood_config_selects_1_1` only checks that `.project-standards.yml` contains `markdown_tooling:` and any `version: "1.1"` or `version: '1.1'` anywhere in the file. The current config already contains `markdown.frontmatter.version: "1.1"`, so the test can pass after only the registry edit while `markdown_tooling.version` remains `1.0`.
* Repository evidence: `.project-standards.yml` has `markdown.frontmatter.version: "1.1"` at lines 7-9 and `markdown_tooling.version: "1.0"` at lines 61-62.
* External research evidence: Not applicable.
* Why it matters: The plan can pass its targeted test while failing to dogfood the new `markdown_tooling` contract version.
* Recommended action for Claude Code: Parse `.project-standards.yml` as YAML and assert `cfg["markdown_tooling"]["version"] == "1.1"`.
* Suggested validation: Run `uv run pytest tests/test_registry_markdown_tooling.py -v` and `uv run validate-frontmatter --config .project-standards.yml`.

#### CR-004: Final green-gate order can skip the Node behavioral coherence tests

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Validation false positive / ordering
* Plan reference: Task 6 lines 584-587 and Task 10 lines 877-884
* Finding: The behavioral tests are skip-guarded when `node_modules/.bin/prettier` or `markdownlint-cli2` is missing, but the final gate runs `coverage run -m pytest` before `npm ci`. In a clean checkout, the coherence behavioral tests can be skipped, then `npm ci` runs later, and the plan never reruns those tests.
* Repository evidence: The proposed skip guard checks for binaries under `node_modules/.bin`; the final gate orders `coverage run -m pytest` before `npm ci`.
* External research evidence: Not applicable.
* Why it matters: The final “complete gate” can report success without exercising the behavioral proof that the plan says is load-bearing.
* Recommended action for Claude Code: Move `npm ci` before `coverage run -m pytest`, or keep the main gate hermetic and add a post-`npm ci` `uv run pytest tests/coherence -v` step. The CI job is useful, but the final local validation should not silently skip the Node-backed proof.
* Suggested validation: From a clean checkout without `node_modules`, run the corrected gate and confirm `tests/coherence/test_behavioral.py` runs rather than skips.

### Missing considerations

* Blocking: The behavioral coherence test must explicitly prove it is using the shipped Prettier config, not default Prettier behavior.
* Blocking: The plan should revise supplied test code for strict Ruff/BasedPyright compatibility before implementation.
* Non-blocking: Tests for version and stale-doc claims should parse structured files or inspect targeted sections, not search for broad substrings.
* Non-blocking: The final validation order should ensure skip-guarded Node tests actually run after `npm ci`.

### Internet research performed

* Source name: Prettier CLI docs
* URL: https://prettier.io/docs/cli
* Access date: 2026-07-06
* What it was used to verify: `prettier .`, `--check`, exit behavior, directory recursion, and ignore behavior.
* Relevant conclusion: The planned repo-wide `prettier --check .` is aligned with Prettier’s CLI behavior.

* Source name: Prettier Configuration docs
* URL: https://prettier.io/docs/configuration
* Access date: 2026-07-06
* What it was used to verify: How Prettier discovers configuration files.
* Relevant conclusion: Config is resolved from the formatted file location upward, contradicting the Task 6 temp-file assumption.

* Source name: GitHub Actions contexts reference
* URL: https://docs.github.com/en/actions/reference/workflows-and-actions/contexts
* Access date: 2026-07-06
* What it was used to verify: `inputs` context availability, missing-property behavior, and job-level `if` context support.
* Relevant conclusion: The plan’s use of `inputs` in a job `if` is plausible, and nonexistent properties evaluate to an empty string.

* Source name: DavidAnson markdownlint-cli2-action `v23` action/package metadata
* URL: https://raw.githubusercontent.com/DavidAnson/markdownlint-cli2-action/v23/package.json
* Access date: 2026-07-06
* What it was used to verify: Bundled `markdownlint-cli2` version.
* Relevant conclusion: `markdownlint-cli2-action@v23` package metadata pins `markdownlint-cli2` to `0.22.1`.

* Source name: markdownlint-cli2 README
* URL: https://raw.githubusercontent.com/DavidAnson/markdownlint-cli2/main/README.md
* Access date: 2026-07-06
* What it was used to verify: CLI `--config`, configuration files, and glob/config behavior.
* Relevant conclusion: Explicit `--config` is available and should be used for the behavioral test if the target file is outside the repo tree.

### Items Claude Code should verify before correcting the plan

* Verify whether the behavioral test should use `.markdownlint.json` directly or `.markdownlint-cli2.jsonc` plus the rule config.
* Verify basedpyright’s exact diagnostics after replacing bare `dict` annotations with typed aliases.
* Verify the corrected final gate from a clean checkout where `node_modules` is absent.
* Verify that the new workflow caller is added to adopt dogfood/packaging tests, not only a new isolated test file.

### Suggested corrections for Claude Code's plan

* Add explicit `--config` arguments to the behavioral Prettier and markdownlint subprocess calls.
* Change all proposed bare `dict` annotations in new tests/support modules to strict-compatible types.
* Remove the unused `shutil` import from `tests/coherence/test_behavioral.py`.
* Parse `.project-standards.yml` as YAML for the `markdown_tooling.version == "1.1"` assertion.
* Reorder the final gate or add a post-`npm ci` `uv run pytest tests/coherence -v` command.
* Add a pin-alignment test that reads `package.json` and compares it to the workflow text, rather than hardcoding independent `3.8.3` constants in separate tests.

### Read-only validation performed

* `pwd`: confirmed repository root is `/home/chris/projects/project-standards`.
* `git status --short`, `git branch --show-current`, `git log --oneline -n 10`: confirmed branch `testing`, recent plan/spec commits, and no displayed local changes.
* `sed -n` on the plan file: inspected the full implementation plan.
* `rg --files`: discovered relevant repo files under workflows, standards, source, tests, and docs.
* `sed -n` on `package.json`, `package-lock.json`, `.github/workflows/format.yml`, `.github/workflows/check.yml`, `.github/workflows/lint-markdown.yml`: confirmed current Prettier-only package state and existing workflow shapes.
* `sed -n` on `.project-standards.yml` and `src/project_standards/schemas/registry.json`: confirmed `markdown_tooling` is currently `1.0` while frontmatter is already `1.1`.
* `sed -n` on adopt engine/manifest and adopt tests: confirmed `workflow-caller` support and current caller test coverage.
* `sed -n` on Markdown tooling docs, README, CLAUDE.md, AGENTS.md: confirmed stale Prettier no-workflow claims exist.
* `sed -n` on `.prettierignore`, `.markdownlint-cli2.jsonc`, `.gitignore`: confirmed current file-set ignore boundaries.
* `git diff --stat` and `git diff --check`: confirmed no current diff output and no whitespace-error output.

### Recommended implementation validation

* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest && uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`
* Run only after implementation: `npm ci && uv run pytest tests/coherence -v`
* Run only after implementation: `npx prettier@3.8.3 --check .`
* Run only after implementation: `npx markdownlint-cli2 '**/*.md'`
* Run only after implementation: `git diff --name-only main -- .github/workflows/lint-markdown.yml .github/workflows/validate-markdown-frontmatter.yml`

### Final recommendation

Claude Code should revise the plan using the findings above

### Review ledger for next loop

* Plan path: `/home/chris/projects/project-standards/docs/superpowers/plans/2026-07-06-markdown-tooling-formatter-authority.md`
* Audit round: 1
* Open issue IDs: CR-001, CR-002, CR-003, CR-004
* Resolved issue IDs:
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: corrected behavioral test config usage, strict Ruff/BasedPyright-compatible snippets, targeted YAML assertions, and final gate ordering.