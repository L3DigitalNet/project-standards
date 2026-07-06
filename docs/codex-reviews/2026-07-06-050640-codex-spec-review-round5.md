### Executive summary

Claude Code’s round-5 revision substantively resolves the three remaining round-4 findings. The spec now includes the missing documentation surfaces, defines `prettier: false` as a whole-job opt-out, and specifies the Node dev dependency, lockfile, and `npm ci` execution model for coherence tests.

New internet research was performed to re-check the current GitHub Actions, Prettier, and `markdownlint-cli2-action` assumptions. No new blocking or non-blocking findings were identified.

### Verdict

No significant findings remain

### Audit loop status

* Audit type: Follow-up audit
* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-07-06-markdown-tooling-formatter-authority-design.md`
* Prior audit issue count: 3
* Resolved issue count: 3
* Still open issue count: 0
* Partially resolved issue count: 0
* New issue count: 0
* Regression count: 0
* Significant findings remaining: No

### Adversarial review performed

I re-read the revised spec and retested the prior open findings against current repository evidence: the existing `format.yml`, `lint-markdown.yml`, adopt bundle manifests, caller rendering, package/lock files, registry/config version state, release rules, Markdown Tooling docs, root README, agent instruction files, formatter/linter configs, and existing test patterns.

The strongest retests were whether stale “no Prettier workflow” public and agent-facing claims are now in scope; whether `prettier: false` skips the whole formatter job rather than only the final command; whether lockfile-pinned Node behavioral tests are specified clearly enough; and whether the opt-in/minor-release framing still matches `meta/versioning.md`.

I did not run tests, formatters, package-manager installs, workflow executions, `npm ci`, or any command that could write caches/build artifacts or mutate repository state.

### Prior findings status

#### SA-NEW-001: Documentation update surface misses stale public and agent-facing “no Prettier workflow” claims

* Previous severity: Medium
* Current status: Resolved
* Evidence: The revised spec now explicitly includes root `README.md`, `CLAUDE.md`, and `AGENTS.md` in Component B and acceptance criteria. It also requires a stale-phrase guard for the prior “copy-adopt (no workflow)” and “lint-markdown only” claims.
* Remaining action for Claude Code: Implement the specified doc updates and stale-phrase guard during the implementation phase.

#### SA-NEW-002: Node pin/lockfile and CI install path are under-specified

* Previous severity: Medium
* Current status: Resolved
* Evidence: The revised spec now requires adding `markdownlint-cli2@0.22.1` to `package.json` devDependencies, regenerating and committing `package-lock.json`, running `npm ci` before the Node subprocess tests in the dedicated CI job, and asserting package/lockfile agreement.
* Remaining action for Claude Code: Implement the devDependency/lockfile update and CI/test execution model exactly as specified.

#### SA-NEW-003: `prettier: false` may skip only the Prettier step, not the workflow’s dependency failure surface

* Previous severity: Medium
* Current status: Resolved
* Evidence: The revised spec requires job-level gating with `if: ${{ format('{0}', inputs.prettier) != 'false' }}` and acceptance tests that assert the whole job/workflow result for direct, reusable true/default, and reusable false cases.
* Remaining action for Claude Code: Implement a job-level condition and verify the truth table at job-result level, not only by matching a step condition.

### New blocking issues

None found.

### New non-blocking issues

None found.

### Regressions

None found.

### Remaining ambiguities and decisions needed

None found.

### Internet research performed

* Source name: GitHub Docs — Contexts reference
* URL: https://docs.github.com/en/actions/reference/workflows-and-actions/contexts
* Access date: 2026-07-06
* What it was used to verify: Availability of the `inputs` context in `jobs.<job_id>.if` and behavior of nonexistent properties.
* Relevant conclusion: `inputs` is allowed in job-level `if`, and missing properties evaluate to an empty string, supporting the spec’s direct-trigger truth table.

* Source name: GitHub Docs — Expressions
* URL: https://docs.github.com/en/actions/reference/workflows-and-actions/expressions
* Access date: 2026-07-06
* What it was used to verify: Loose equality coercion and string conversion behavior.
* Relevant conclusion: The spec’s `format('{0}', inputs.prettier) != 'false'` requirement is justified for typed boolean input handling.

* Source name: GitHub Docs — Workflow syntax for GitHub Actions
* URL: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
* Access date: 2026-07-06
* What it was used to verify: Reusable workflow caller semantics and action reference examples.
* Relevant conclusion: The reusable workflow/caller model and `jobs.<job_id>.uses` pattern fit GitHub Actions syntax.

* Source name: `actions/checkout@v6` action metadata
* URL: https://raw.githubusercontent.com/actions/checkout/v6/action.yml
* Access date: 2026-07-06
* What it was used to verify: Existence and runtime metadata for the checkout action version used by existing workflows and the spec snippet.
* Relevant conclusion: `actions/checkout@v6` exists and uses `node24`.

* Source name: `actions/setup-node@v4` action metadata
* URL: https://raw.githubusercontent.com/actions/setup-node/v4/action.yml
* Access date: 2026-07-06
* What it was used to verify: Node setup inputs and cache behavior.
* Relevant conclusion: `setup-node@v4` provisions Node and supports npm cache inputs, but does not install dependencies by itself; the spec’s separate `npm ci` requirement for the coherence job is necessary.

* Source name: Prettier CLI documentation
* URL: https://prettier.io/docs/cli
* Access date: 2026-07-06
* What it was used to verify: `prettier . --check`, exit codes, config lookup, and ignore-path behavior.
* Relevant conclusion: `prettier . --check` is the documented repo-wide check form and returns distinct success/unformatted/error exit codes.

* Source name: Prettier Ignoring Code documentation
* URL: https://prettier.io/docs/ignore
* Access date: 2026-07-06
* What it was used to verify: `.prettierignore`, `.gitignore`, VCS directory, and `node_modules` ignore behavior.
* Relevant conclusion: The spec’s ignore/parity guidance is consistent with Prettier’s documented defaults.

* Source name: `markdownlint-cli2-action@v23` package metadata
* URL: https://raw.githubusercontent.com/DavidAnson/markdownlint-cli2-action/v23/package.json
* Access date: 2026-07-06
* What it was used to verify: Bundled `markdownlint-cli2` version.
* Relevant conclusion: `markdownlint-cli2-action@v23` version `23.2.0` depends on `markdownlint-cli2@0.22.1`, matching the revised spec.

### Read-only validation performed

* `pwd`, `git status --short`, `git branch --show-current`, `git log --oneline -n 10`, `git diff --stat`: confirmed repository root, branch `testing`, modified spec file, and one untracked prior review artifact.
* `nl -ba docs/superpowers/specs/2026-07-06-markdown-tooling-formatter-authority-design.md`: inventoried the current round-5 spec text and line-level requirements.
* `git diff -- docs/superpowers/specs/2026-07-06-markdown-tooling-formatter-authority-design.md`: verified the round-5 changes directly address the round-4 findings.
* `rg --files`: discovered relevant workflows, bundle manifests, package files, docs, configs, and tests.
* Inspected `.github/workflows/format.yml`, `lint-markdown.yml`, `check.yml`, `validate-markdown-frontmatter.yml`, and `validate-specs.yml`: confirmed current workflow shape, direct triggers, reusable surfaces, and existing Node/Python setup patterns.
* Inspected `src/project_standards/bundles/markdown-tooling/adopt.toml`, `lint-markdown.caller.yml`, `src/project_standards/adopt/engine.py`, and `manifest.py`: confirmed current artifact list and `{{ref}}`/`major_ref()` behavior.
* Inspected `package.json` and `package-lock.json`: confirmed current lockfile contains only `prettier@3.8.3`, so the spec’s lockfile update requirement is necessary.
* Inspected `meta/versioning.md`, `registry.json`, `.project-standards.yml`, and relevant validator tests: confirmed the `markdown_tooling 1.0 → 1.1` additive/default-known-version approach fits the repo’s versioning model.
* Inspected `standards/markdown-tooling/README.md`, `standards/markdown-tooling/adopt.md`, root `README.md`, `CLAUDE.md`, and `AGENTS.md`: confirmed the exact stale claims the spec now requires updating.
* Inspected `.prettierrc.json`, `.markdownlint.json`, `.markdownlint-cli2.jsonc`, and `.prettierignore`: confirmed formatter/linter scope and ignore-parity assumptions.
* Inspected `tests/test_markdownlint_config.py`, `tests/test_adopt_dogfood.py`, `tests/test_adopt_packaging.py`, `tests/test_adopt_manifest.py`, `tests/test_adopt_cli.py`, and registry-related tests: confirmed the proposed test locations and patterns fit existing coverage.
* Ran `rg -n` over docs/workflows/configs/tests for DEC-9, Prettier, copy-adopt, no workflow, `format.yml`, `markdown_tooling`, `@v4`, and `standards-ref`: verified stale surface and versioning references relevant to the spec.
* Inspected `.github/dependabot.yml`: confirmed existing GitHub Actions update coverage for action pins.

### Recommended planning/implementation validation

* Run only after implementation: workflow truth-table test for direct run, reusable default/true, and reusable `prettier: false`, asserting whole job/workflow behavior.
* Run only after implementation: adopt integration test proving `adopt markdown-tooling` writes `format.caller.yml`, renders `{{ref}}` to `v<major>`, and includes the artifact in packaging.
* Run only after implementation: stale-doc guard covering root `README.md`, `standards/markdown-tooling/README.md`, `standards/markdown-tooling/adopt.md`, `CLAUDE.md`, `AGENTS.md`, `CHANGELOG.md`, and `UPGRADING.md`.
* Run only after implementation: package-lock consistency check after adding `markdownlint-cli2@0.22.1`.
* Run only after implementation: pin-alignment test for workflow Prettier `3.8.3` vs `package.json`, and local `markdownlint-cli2` vs `markdownlint-cli2-action@v23`.
* Run only after implementation: coherence corpus tests for declaration conformance, Prettier-to-markdownlint co-satisfaction, and fixed-point stability.
* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest && uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`
* Run only after implementation: repo Prettier check through the revised `format.yml` path.
* Run only after implementation: markdownlint workflow-equivalent check for the repo’s Markdown globs.
* Run only after implementation: the new coherence CI job with `npm ci` before pytest.

### Final recommendation

No significant findings remain; the audit/fix loop can stop

### Review ledger for next loop

* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-07-06-markdown-tooling-formatter-authority-design.md`
* Audit round: 5
* Open issue IDs: None
* Resolved issue IDs: SA-001, SA-004, SA-005, SA-006, SA-NEW-001, SA-NEW-002, SA-NEW-003
* Superseded issue IDs: SA-002, SA-003
* Significant findings remaining: No
* Next audit should focus on: No significant findings remain; no next audit is needed unless the spec changes again.