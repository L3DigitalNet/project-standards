### Executive summary

Claude Code’s revisions substantively resolve all four prior findings: the behavioral test now passes explicit Prettier/markdownlint configs, the proposed Python snippets are strict-type friendlier, the `markdown_tooling` dogfood assertion now parses YAML, and the final gate installs Node dependencies before running skip-guarded coherence tests.

One new non-blocking validation gap remains: the plan says packaging coverage will confirm the new `format.caller.yml` ships in the wheel, but the proposed tests do not actually add that file to the existing wheel/caller-stub guards. No new internet research was required; this follow-up was about checking the revised plan against repository evidence and prior findings.

### Verdict

Needs minor correction before execution

### Audit loop status

* Audit type: Follow-up audit
* Plan path: `/home/chris/projects/project-standards/docs/superpowers/plans/2026-07-06-markdown-tooling-formatter-authority.md`
* Prior audit issue count: 4
* Resolved issue count: 4
* Still open issue count: 0
* Partially resolved issue count: 0
* New issue count: 1
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

I re-read the revised plan, diffed it against the prior committed version, and retested the four prior findings against current plan text and repository files. I inspected the current package/workflow/config/adopt/test surfaces most likely to falsify the plan: `package.json`, `.project-standards.yml`, `registry.json`, `.github/workflows/*.yml`, markdownlint/Prettier config, adopt manifests/engine, existing adopt packaging/dogfood tests, and stale documentation surfaces.

I did not run implementation tests, `npm ci`, `npm install`, `uv build`, formatters, or the plan’s validation gate because this audit is read-only and those commands may write artifacts, dependency directories, caches, lockfiles, or build output.

### Prior findings status

#### CR-001: Behavioral coherence test does not prove the shipped Prettier config

* Previous severity: High
* Current status: Resolved
* Evidence: The revised behavioral test now defines `_PRETTIER_CFG = str(_REPO / ".prettierrc.json")` and `_MDLINT_CFG = str(_REPO / ".markdownlint.json")`, then invokes Prettier with `--config` and markdownlint-cli2 with `--config` at plan lines 595-619. This directly addresses the prior temp-file config-discovery false positive.
* Remaining action for Claude Code: None for this issue; keep the explicit config arguments when implementing.

#### CR-002: Proposed Python test/support code is not compatible with the repo’s strict gates

* Previous severity: High
* Current status: Resolved
* Evidence: The revised snippets replace bare `dict` annotations with `dict[str, Any]` or a `Config = dict[str, Any]` alias at plan lines 107-126, 181-190, 431-442, and 480-525. The unused `shutil` import was removed from Task 6. The repo’s `pyproject.toml` still has `typeCheckingMode = "strict"` and `failOnWarnings = true`, so this correction is material.
* Remaining action for Claude Code: Verify with `uv run basedpyright` after implementation.

#### CR-003: Registry dogfood test can pass without updating `markdown_tooling.version`

* Previous severity: Medium
* Current status: Resolved
* Evidence: The revised test imports `yaml`, parses `.project-standards.yml`, and asserts `cfg["markdown_tooling"]["version"] == "1.1"` at plan lines 122-126. Current repo evidence confirms why this matters: `.project-standards.yml` has unrelated `markdown.frontmatter.version: "1.1"` while `markdown_tooling.version` is still `"1.0"`.
* Remaining action for Claude Code: None for this issue.

#### CR-004: Final green-gate order can skip the Node behavioral coherence tests

* Previous severity: Medium
* Current status: Resolved
* Evidence: The global constraint and final gate now put `npm ci` before the Python test suite and explicitly rerun `uv run pytest tests/coherence -v` after validation at plan lines 18 and 902-913. The expected result now says behavioral tests must run, not skip.
* Remaining action for Claude Code: Verify from a clean checkout or after removing `node_modules` that `tests/coherence/test_behavioral.py` runs after `npm ci`.

### New blocking issues

None found.

### New non-blocking issues

#### CR-NEW-001: Packaging validation does not actually prove `format.caller.yml` ships in the wheel

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Validation false positive / consumer adoption surface
* Plan reference: Task 4, especially lines 392-398
* Finding: The plan says `tests/test_adopt_packaging.py` will confirm the new file ships in the wheel, but Task 4 only creates `tests/test_adopt_markdown_format.py`, which reads `src/project_standards/bundles/markdown-tooling/format.caller.yml` from the source checkout. The existing packaging test’s `must` list does not include `project_standards/bundles/markdown-tooling/format.caller.yml`, and the existing caller-stub test only enumerates `validate-markdown-frontmatter.caller.yml` and `lint-markdown.caller.yml`.
* Repository evidence: `tests/test_adopt_packaging.py` currently checks `markdown-tooling/adopt.toml` but not `markdown-tooling/format.caller.yml`. `tests/test_adopt_dogfood.py` currently checks only the markdown-frontmatter and lint-markdown caller stubs in `test_caller_stubs_valid_and_reference_correct_workflow`.
* External research evidence: Not applicable.
* Why it matters: Source-checkout tests can pass while a packaged/wheel install used by consumers lacks the new caller template or fails to validate its rendered `@vN` reference. This is exactly the adoption path the plan is changing.
* Recommended action for Claude Code: Update the plan to modify `tests/test_adopt_packaging.py` so the wheel `must` list includes `project_standards/bundles/markdown-tooling/format.caller.yml`. Also extend `test_caller_stubs_valid_and_reference_correct_workflow` to include `"markdown-tooling/format.caller.yml": "format.yml"`.
* Suggested validation: After implementation, run `uv run pytest tests/test_adopt_packaging.py tests/test_adopt_dogfood.py tests/test_adopt_markdown_format.py -v`.

### Regressions

None found.

### Internet research performed

No new internet research was necessary for this follow-up. The changed claims were repository-local corrections to prior findings, and the prior audit already checked the relevant current external behavior for Prettier config discovery, GitHub Actions inputs, and markdownlint-cli2/action versioning.

### Read-only validation performed

* `pwd`, `git status --short`, `git branch --show-current`, `git log --oneline -n 10`: confirmed repository root, branch `testing`, current plan modification, and existing untracked prior review artifact.
* `sed -n` and `nl -ba` on the plan file: re-read the full revised plan with line numbers.
* `git diff --stat`, `git diff --check`, and `git diff -- docs/superpowers/plans/2026-07-06-markdown-tooling-formatter-authority.md`: confirmed the plan changes are limited to the audit-target plan file and directly address prior findings.
* `rg --files` over workflows, source, tests, docs, and config: discovered relevant repository evidence.
* Inspected `pyproject.toml`, `package.json`, `.project-standards.yml`, `registry.json`, `.github/workflows/*.yml`, `.markdownlint.json`, `.prettierrc.json`, `.markdownlint-cli2.jsonc`, `.prettierignore`, and `.gitignore`: confirmed current pins/configs/strict gates and ignore boundaries.
* Inspected `src/project_standards/adopt/engine.py`, `manifest.py`, `bundles/markdown-tooling/adopt.toml`, `lint-markdown.caller.yml`, `tests/test_adopt_packaging.py`, and `tests/test_adopt_dogfood.py`: confirmed current adopt/caller/packaging coverage and the new validation gap.
* `command -v markdownlint-cli2`, `markdownlint-cli2 --help`, `markdownlint-cli2 --version`, `command -v prettier`, `prettier --version`: confirmed local CLI availability and markdownlint-cli2 0.22.1 help/behavior without mutating files.
* `rg` for stale Prettier/workflow claims in README, AGENTS, CLAUDE, Markdown Tooling docs, and DEC docs: confirmed the plan’s targeted stale-claim surfaces still exist in the current repo.

### Recommended implementation validation

* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest && uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`
* Run only after implementation: `npm ci && uv run pytest tests/coherence -v`
* Run only after implementation: `uv run pytest tests/test_adopt_packaging.py tests/test_adopt_dogfood.py tests/test_adopt_markdown_format.py -v`
* Run only after implementation: `npx prettier@3.8.3 --check .`
* Run only after implementation: `npx markdownlint-cli2 '**/*.md'`
* Run only after implementation: `git diff --name-only main -- .github/workflows/lint-markdown.yml .github/workflows/validate-markdown-frontmatter.yml`

### Final recommendation

Claude Code should revise the plan using the findings above

### Review ledger for next loop

* Plan path: `/home/chris/projects/project-standards/docs/superpowers/plans/2026-07-06-markdown-tooling-formatter-authority.md`
* Audit round: 2
* Open issue IDs: CR-NEW-001
* Resolved issue IDs: CR-001, CR-002, CR-003, CR-004
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: whether the plan adds wheel packaging coverage and caller-stub/dogfood coverage for `markdown-tooling/format.caller.yml`.