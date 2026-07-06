### Executive summary

Claude Code’s latest corrections resolve both prior open findings. Task 3 now checks parsed workflow `run:` steps instead of raw text, so the legitimate `npm ci` comment no longer makes the test fail. Task 5 now filters drift checks structurally by `Concern.owner`, so the CUSTOMIZATIONS guard is no longer vacuous.

New internet research was performed for the GitHub Actions reusable-workflow assumptions. The relevant current GitHub documentation supports the plan’s reusable workflow shape, `inputs` usage in job-level `if`, and the assumption that `actions/checkout` inside a called workflow checks out the caller repository.

### Verdict

No significant findings remain

### Audit loop status

* Audit type: Follow-up audit
* Plan path: `/home/chris/projects/project-standards/docs/superpowers/plans/2026-07-06-markdown-tooling-formatter-authority.md`
* Prior audit issue count: 7
* Resolved issue count: 7
* Still open issue count: 0
* Partially resolved issue count: 0
* New issue count: 0
* Regression count: 0
* Significant findings remaining: No

### Adversarial review performed

I re-read the revised plan, inspected the current plan diff, and re-tested the two prior open findings against the revised text and repository evidence. I re-attacked the workflow validation for false positives, the declaration/CUSTOMIZATIONS guard for vacuity, the packaging/caller-stub validation path, the final gate order, and the external GitHub Actions assumptions behind the reusable workflow.

Repository areas checked included the plan file, git status/log/diff, current `format.yml`, `check.yml`, `lint-markdown.yml`, package files, project standards config, registry, markdownlint/Prettier configs, adopt manifests and engine, packaging/dogfood tests, existing markdownlint customization tests, stale documentation surfaces, and handoff file presence. I did not run mutating commands, package installs, formatter writes, build commands, or pytest gates that may write temporary build/test artifacts.

### Prior findings status

#### CR-001: Behavioral coherence test does not prove the shipped Prettier config

* Previous severity: High
* Current status: Resolved
* Evidence: The plan still passes explicit `--config` paths to Prettier and markdownlint-cli2 in the behavioral subprocess helpers, so tmp-path corpus execution proves the repo’s shipped config rather than default discovery.
* Remaining action for Claude Code: Verify with `npm ci && uv run pytest tests/coherence/test_behavioral.py -v` after implementation.

#### CR-002: Proposed Python test/support code is not compatible with the repo’s strict gates

* Previous severity: High
* Current status: Resolved
* Evidence: The revised snippets use `dict[str, Any]`, `Config = dict[str, Any]`, and `cast(...)` where needed; current `pyproject.toml` keeps `typeCheckingMode = "strict"` and `failOnWarnings = true`.
* Remaining action for Claude Code: Verify with `uv run basedpyright` after implementation.

#### CR-003: Registry dogfood test can pass without updating `markdown_tooling.version`

* Previous severity: Medium
* Current status: Resolved
* Evidence: Task 2 parses `.project-standards.yml` as YAML and asserts `cfg["markdown_tooling"]["version"] == "1.1"` instead of using a broad substring check.
* Remaining action for Claude Code: None.

#### CR-004: Final green-gate order can skip the Node behavioral coherence tests

* Previous severity: Medium
* Current status: Resolved
* Evidence: The global gate and Task 10 run `npm ci` before the full pytest/coverage pass and before the explicit `uv run pytest tests/coherence -v`, so the behavioral tests should run rather than skip.
* Remaining action for Claude Code: Confirm the behavioral tests report run/pass, not skipped, after implementation.

#### CR-NEW-001: Packaging validation does not actually prove `format.caller.yml` ships in the wheel

* Previous severity: Medium
* Current status: Resolved
* Evidence: Task 4 explicitly adds `format.caller.yml` to `tests/test_adopt_packaging.py`’s wheel contents guard and adds `"markdown-tooling/format.caller.yml": "format.yml"` to the caller-stub reference guard in `tests/test_adopt_dogfood.py`.
* Remaining action for Claude Code: Implement those two guard extensions exactly.

#### CR-NEW-002: Task 3’s workflow test will fail on the proposed workflow comment

* Previous severity: High
* Current status: Resolved
* Evidence: Task 3 now builds `runs = [str(s.get("run", "")) for s in steps]` and asserts no parsed `run:` command invokes `npm ci`. The workflow comment may still mention `npm ci` without failing the test.
* Remaining action for Claude Code: Verify `uv run pytest tests/test_format_workflow.py -v` fails before and passes after the workflow edit.

#### CR-NEW-003: The CUSTOMIZATIONS drift guard is vacuous because it filters on rendered text

* Previous severity: Medium
* Current status: Resolved
* Evidence: Task 5 now imports `SPLIT` and computes `failing = [c.name for c in SPLIT if c.owner == "markdownlint" and not c.check(ml, pr)]`, filtering structurally by owner rather than searching rendered violation strings.
* Remaining action for Claude Code: Implement as written and verify a markdownlint-owned customization drift would fail the test.

### New blocking issues

None found.

### New non-blocking issues

None found.

### Regressions

None found.

### Internet research performed

* Source name: GitHub Docs — Contexts reference
* URL: https://docs.github.com/en/actions/reference/workflows-and-actions/contexts
* Access date: 2026-07-06
* What it was used to verify: Availability and behavior of the `inputs` context in job-level `if` expressions.
* Relevant conclusion: GitHub documents `inputs` as available for `jobs.<job_id>.if`, and nonexistent properties evaluate to an empty string, supporting the direct push/PR truth-table assumption.

* Source name: GitHub Docs — Reuse workflows
* URL: https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows
* Access date: 2026-07-06
* What it was used to verify: `workflow_call`, typed inputs, and job-level reusable workflow caller syntax.
* Relevant conclusion: The plan’s `workflow_call.inputs.prettier` boolean input and caller `jobs.<job_id>.uses` shape align with current GitHub documentation.

* Source name: GitHub Docs — Reusing workflow configurations
* URL: https://docs.github.com/en/actions/concepts/workflows-and-actions/reusing-workflow-configurations
* Access date: 2026-07-06
* What it was used to verify: Whether actions inside a called reusable workflow run in the caller repository context.
* Relevant conclusion: GitHub states that actions in a called workflow run as if part of the caller workflow, and `actions/checkout` checks out the caller repository, supporting the plan’s consumer-formatting model.

* Source name: actions/checkout README
* URL: https://github.com/actions/checkout
* Access date: 2026-07-06
* What it was used to verify: `actions/checkout@v6` existence and checkout defaults.
* Relevant conclusion: The repository documents Checkout v6 and states checkout defaults to the triggering repository/ref; current latest is v7, but the repo already uses `@v6`, so the plan remains consistent with local convention.

### Read-only validation performed

* `pwd`, `git status --short`, `git branch --show-current`, `git log --oneline -n 5`: confirmed repository root, branch `testing`, modified plan file, and existing untracked codex-review artifacts.
* `nl -ba docs/superpowers/plans/2026-07-06-markdown-tooling-formatter-authority.md | sed -n ...`: re-read the revised plan with line numbers.
* `git diff --check -- docs/superpowers/plans/2026-07-06-markdown-tooling-formatter-authority.md`: confirmed the plan diff has no whitespace errors.
* `git diff -- docs/superpowers/plans/2026-07-06-markdown-tooling-formatter-authority.md`: confirmed the latest revision specifically fixes CR-NEW-002 and CR-NEW-003 and preserves earlier corrections.
* Inspected `.github/workflows/format.yml`, `.github/workflows/check.yml`, `.github/workflows/lint-markdown.yml`: confirmed current workflow state and the intended replacement surfaces.
* Inspected `package.json`, `.project-standards.yml`, `registry.json`, `pyproject.toml`, `.python-version`, `.markdownlint.json`, `.prettierrc.json`, `.markdownlint-cli2.jsonc`, and `.prettierignore`: confirmed current pins/config values, strict Python gates, Python 3.14 target, and ignore boundaries.
* Inspected `src/project_standards/bundles/markdown-tooling/adopt.toml`, `lint-markdown.caller.yml`, `src/project_standards/adopt/engine.py`, and `manifest.py`: confirmed the workflow-caller artifact pattern and `{{ref}}` rendering.
* Inspected `tests/test_adopt_packaging.py`, `tests/test_adopt_dogfood.py`, and `tests/test_markdownlint_config.py`: confirmed the packaging/caller-stub targets and `CUSTOMIZATIONS` source the plan references.
* `rg` over README, AGENTS, CLAUDE, Markdown Tooling docs, DEC docs, CHANGELOG, and UPGRADING: confirmed stale Prettier/no-workflow documentation still exists and is in the plan’s update scope.
* `git remote -v` and upstream inspection: confirmed this is `L3DigitalNet/project-standards.git` on `origin/testing`, with no fork remote detected.

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
* Run only after implementation: `git status --short` after the handoff-state update, to ensure final documentation edits are committed or intentionally left for the session-end ritual.

### Final recommendation

No significant findings remain; the audit/fix loop can stop

### Review ledger for next loop

* Plan path: `/home/chris/projects/project-standards/docs/superpowers/plans/2026-07-06-markdown-tooling-formatter-authority.md`
* Audit round: 4
* Open issue IDs:
* Resolved issue IDs: CR-001, CR-002, CR-003, CR-004, CR-NEW-001, CR-NEW-002, CR-NEW-003
* Superseded issue IDs:
* Significant findings remaining: No
* Next audit should focus on: no further audit needed unless Claude Code changes the plan again before implementation.