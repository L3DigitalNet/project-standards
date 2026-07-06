### Executive summary

Claude Code’s latest revision resolves the prior packaging/caller-stub coverage finding (`CR-NEW-001`): the plan now explicitly adds `format.caller.yml` to both the wheel-contents guard and the caller-stub reference guard.

Significant findings still remain. The most important new issue is an internal contradiction in Task 3: the proposed test asserts `"npm ci"` is absent from `format.yml`, but the proposed replacement workflow includes that string in a comment, so the task’s own “expected PASS” cannot occur as written. New internet research was performed to re-check current external assumptions around GitHub Actions reusable workflow inputs, Prettier CLI behavior, and markdownlint-cli2 config support.

### Verdict

Needs major correction before execution

### Audit loop status

* Audit type: Follow-up audit
* Plan path: `/home/chris/projects/project-standards/docs/superpowers/plans/2026-07-06-markdown-tooling-formatter-authority.md`
* Prior audit issue count: 5
* Resolved issue count: 5
* Still open issue count: 0
* Partially resolved issue count: 0
* New issue count: 2
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

I re-read the revised plan, inspected the current diff, and retested the prior open finding against the actual adopt packaging/caller-stub tests. I also re-attacked the plan’s own validation claims for false positives, especially tests that search raw workflow text and tests that filter rendered violation strings.

Repository areas checked included the plan file, git status/log/diff, `package.json`, `package-lock.json`, `.project-standards.yml`, `registry.json`, workflows, markdownlint/Prettier configs, adopt manifests, adopt engine/manifest code, packaging tests, dogfood tests, markdownlint config tests, and stale documentation surfaces. I did not run mutating commands such as `npm ci`, `npm install`, `uv build`, formatter writes, package installs, or implementation tests that may write artifacts.

### Prior findings status

#### CR-001: Behavioral coherence test does not prove the shipped Prettier config

* Previous severity: High
* Current status: Resolved
* Evidence: The plan still passes explicit config paths to Prettier and markdownlint-cli2 in `tests/coherence/test_behavioral.py` at lines 604-627.
* Remaining action for Claude Code: None for this issue.

#### CR-002: Proposed Python test/support code is not compatible with the repo’s strict gates

* Previous severity: High
* Current status: Resolved
* Evidence: The plan still uses typed `dict[str, Any]` / `Config = dict[str, Any]` annotations and removes the unused `shutil` import. Current `pyproject.toml` confirms `typeCheckingMode = "strict"` and `failOnWarnings = true`.
* Remaining action for Claude Code: Verify with `uv run basedpyright` after implementation.

#### CR-003: Registry dogfood test can pass without updating `markdown_tooling.version`

* Previous severity: Medium
* Current status: Resolved
* Evidence: The plan parses `.project-standards.yml` with YAML and asserts `cfg["markdown_tooling"]["version"] == "1.1"` at lines 122-126.
* Remaining action for Claude Code: None for this issue.

#### CR-004: Final green-gate order can skip the Node behavioral coherence tests

* Previous severity: Medium
* Current status: Resolved
* Evidence: The global gate and Task 10 both run `npm ci` before the Python test suite / coherence rerun at lines 18 and 914-919.
* Remaining action for Claude Code: Verify after implementation that behavioral tests run rather than skip.

#### CR-NEW-001: Packaging validation does not actually prove `format.caller.yml` ships in the wheel

* Previous severity: Medium
* Current status: Resolved
* Evidence: Task 4 now lists `tests/test_adopt_packaging.py` and `tests/test_adopt_dogfood.py` as modified files at lines 325-326, and Step 5 explicitly instructs adding `project_standards/bundles/markdown-tooling/format.caller.yml` to the wheel `must` list and `"markdown-tooling/format.caller.yml": "format.yml"` to the caller-stub guard at lines 394-399.
* Remaining action for Claude Code: Implement exactly those two guard extensions.

### New blocking issues

#### CR-NEW-002: Task 3’s workflow test will fail on the proposed workflow comment

* Severity: High
* Status: Confirmed
* Adversarial angle: Validation self-contradiction / plan cannot execute as written
* Plan reference: Task 3, lines 212-219 and 231-236
* Finding: The proposed test asserts `assert "npm ci" not in text`, but the proposed replacement workflow includes the comment `no package.json/lockfile to \`npm ci\` from;`. After implementing the workflow exactly as shown, `uv run pytest tests/test_format_workflow.py -v` will fail even though the workflow command no longer runs `npm ci`.
* Repository evidence: The plan’s test reads the full workflow text at lines 215-219. The proposed workflow text contains `npm ci` in a comment at line 235. Current `.github/workflows/format.yml` also uses `npm ci`, so the failing-test phase remains valid; the problem is the post-edit expected pass.
* External research evidence: Not applicable.
* Why it matters: Claude Code cannot follow Task 3 as written and reach the stated PASS condition. This blocks the plan’s task-by-task execution and could lead to unnecessary workflow/comment churn or weakening the test incorrectly during implementation.
* Recommended action for Claude Code: Change the planned assertion to inspect parsed workflow step `run` commands rather than raw text, or remove/reword the comment so the raw-text assertion is true. Prefer parsed YAML: assert no step `run` equals or contains `npm ci`, while allowing explanatory comments.
* Suggested validation: After implementation, run `uv run pytest tests/test_format_workflow.py -v` and confirm the test fails before the workflow edit and passes after the exact planned workflow edit.

### New non-blocking issues

#### CR-NEW-003: The CUSTOMIZATIONS drift guard is vacuous because it filters on rendered text

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Validation false positive / maintainability drift
* Plan reference: Task 5, lines 504-540 and 554-560
* Finding: `test_declaration_agrees_with_existing_customizations` filters violations with `if "prettier" not in v.lower()`, but every declared violation string contains “Prettier” in either the owner or the rationale. That means the `violations` list is always empty, so this specific drift guard cannot detect contradictions with `CUSTOMIZATIONS`.
* Repository evidence: The plan’s `check_conformance` formats each violation as `[{c.name}] owned by {c.owner}: {c.why}`. Both Prettier-owned concerns contain “Prettier” via owner/rationale, and all markdownlint-owned concern rationales also mention Prettier at lines 519, 524, and 529.
* External research evidence: Not applicable.
* Why it matters: The plan claims this test guards against drift between the new declaration and the existing markdownlint customization source of intent, but it can pass while detecting nothing. Other tests still cover the shipped config, so this is not as severe as `CR-NEW-002`, but it weakens the maintainability promise of Component C.
* Recommended action for Claude Code: Avoid filtering rendered strings. Expose enough structured data to filter by `Concern.owner`, or add a helper that evaluates only `SPLIT` entries where `owner == "markdownlint"` against `CUSTOMIZATIONS`.
* Suggested validation: Add a temporary negative test or local mutation showing that removing/changing a markdownlint-owned customization causes `test_declaration_agrees_with_existing_customizations` to fail.

### Regressions

None found.

### Internet research performed

* Source name: GitHub Docs — Workflow syntax for GitHub Actions
* URL: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
* Access date: 2026-07-06
* What it was used to verify: `workflow_call` input typing.
* Relevant conclusion: `on.workflow_call.inputs.<input_id>.type` must be one of `boolean`, `number`, or `string`, so the plan’s boolean reusable input shape is aligned.

* Source name: GitHub Docs — Evaluate expressions in workflows and actions
* URL: https://docs.github.com/en/actions/reference/workflows-and-actions/expressions
* Access date: 2026-07-06
* What it was used to verify: expression comparison behavior and `format()` relevance.
* Relevant conclusion: GitHub documents loose equality comparisons; the plan’s stringification approach remains a plausible guard against boolean/string comparison pitfalls.

* Source name: Prettier CLI docs
* URL: https://prettier.io/docs/cli
* Access date: 2026-07-06
* What it was used to verify: `prettier . --check` behavior.
* Relevant conclusion: Official docs show `prettier . --check` as the CI-style formattedness check and document meaningful exit codes.

* Source name: Prettier configuration docs
* URL: https://prettier.io/docs/configuration
* Access date: 2026-07-06
* What it was used to verify: project-local configuration assumptions.
* Relevant conclusion: Prettier’s docs emphasize project-local configuration for consistent behavior across machines.

* Source name: markdownlint-cli2 README
* URL: https://github.com/DavidAnson/markdownlint-cli2
* Access date: 2026-07-06
* What it was used to verify: `--config` support.
* Relevant conclusion: Official project documentation shows `markdownlint-cli2 --config ...`, consistent with the plan’s explicit config use.

### Read-only validation performed

* `pwd`, `git status --short`, `git branch --show-current`, `git log --oneline -n 10`: confirmed repository root, branch `testing`, modified target plan, and untracked prior review artifacts.
* `nl -ba ... | sed -n` on the plan: re-read the full revised plan with line numbers.
* `git diff --stat`, `git diff --check`, `git diff -- docs/superpowers/plans/2026-07-06-markdown-tooling-formatter-authority.md`: confirmed the latest plan revision adds the CR-NEW-001 packaging/caller-stub corrections and has no whitespace errors.
* `rg --files` over workflows, source, tests, docs, and config: discovered relevant repo evidence.
* Inspected `tests/test_adopt_packaging.py` and `tests/test_adopt_dogfood.py`: confirmed the existing wheel and caller-stub guards are the correct targets for the now-resolved prior finding.
* Inspected `src/project_standards/bundles/markdown-tooling/adopt.toml`, `lint-markdown.caller.yml`, `src/project_standards/adopt/engine.py`, and `manifest.py`: confirmed the adopt/caller pattern and `{{ref}}` rendering model.
* Inspected `.github/workflows/format.yml`, `.github/workflows/check.yml`, `.github/workflows/lint-markdown.yml`: confirmed current workflow state and Task 3’s intended replacement surface.
* Inspected `package.json`, `package-lock.json`, `.project-standards.yml`, `registry.json`, `pyproject.toml`, `.markdownlint.json`, `.prettierrc.json`, `.markdownlint-cli2.jsonc`, and `.prettierignore`: confirmed current pins, strict type gates, config values, and ignore boundaries.
* Inspected `tests/test_markdownlint_config.py` and the formatter-authority design spec: confirmed `CUSTOMIZATIONS` and the intended declaration/drift relationship.
* `command -v markdownlint-cli2`, `markdownlint-cli2 --help`, `markdownlint-cli2 --version`, `command -v prettier`, `prettier --version`: confirmed local CLI availability and markdownlint-cli2 `--config` support. The global `prettier` is `3.8.1`, reinforcing why the plan’s pinned `npx prettier@3.8.3` / local dev-dep model matters.
* `rg` for stale Prettier/workflow claims in README, AGENTS, CLAUDE, Markdown Tooling docs, DEC docs, CHANGELOG, and UPGRADING: confirmed the stale surfaces the plan intends to update still exist.

### Recommended implementation validation

* Run only after correcting and implementing the plan: `uv run pytest tests/test_format_workflow.py -v`
* Run only after correcting and implementing the plan: `uv run pytest tests/coherence/test_declaration.py -v`
* Run only after implementation: `uv run pytest tests/test_adopt_packaging.py tests/test_adopt_dogfood.py tests/test_adopt_markdown_format.py -v`
* Run only after implementation: `npm ci && uv run pytest tests/coherence -v`
* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest && uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`
* Run only after implementation: `npx prettier@3.8.3 --check .`
* Run only after implementation: `npx markdownlint-cli2 '**/*.md'`
* Run only after implementation: `git diff --name-only main -- .github/workflows/lint-markdown.yml .github/workflows/validate-markdown-frontmatter.yml`

### Final recommendation

Claude Code should revise the plan using the findings above

### Review ledger for next loop

* Plan path: `/home/chris/projects/project-standards/docs/superpowers/plans/2026-07-06-markdown-tooling-formatter-authority.md`
* Audit round: 3
* Open issue IDs: CR-NEW-002, CR-NEW-003
* Resolved issue IDs: CR-001, CR-002, CR-003, CR-004, CR-NEW-001
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: whether Task 3’s `npm ci` assertion no longer conflicts with the proposed workflow text, and whether the CUSTOMIZATIONS drift guard filters by structured owner rather than the rendered word “Prettier”.