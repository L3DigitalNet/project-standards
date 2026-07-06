### Executive summary

Claude Code’s round-4 revision changes the design from a v5/default-on Prettier addition inside `lint-markdown.yml` to a v4.x, opt-in, separate reusable `format.yml` workflow. That resolves or supersedes the prior round’s issues, but the redesign introduces several specification gaps around stale documentation surfaces, opt-out semantics, and Node pin/lockfile validation.

New internet research was required because the revised spec depends on current GitHub Actions expression/workflow semantics, Prettier CLI scope/ignore behavior, `actions/setup-node@v4`, and `markdownlint-cli2-action@v23`.

### Verdict

Needs minor specification correction before planning/implementation

### Audit loop status

* Audit type: Follow-up audit
* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-07-06-markdown-tooling-formatter-authority-design.md`
* Prior audit issue count: 6
* Resolved issue count: 4
* Still open issue count: 0
* Partially resolved issue count: 0
* New issue count: 3
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

I re-read the revised spec, diffed it against the committed baseline, and retested SA-001 through SA-006 against repository evidence: current workflows, adopt manifests, `major_ref()` rendering, registry/config version state, release rules, Markdown Tooling docs, root README, agent instruction files, Node package files, and existing tests.

The strongest retests were the switch from v5/default-on to v4.x opt-in, whether existing consumers can newly fail, whether `format.yml` can safely become dual-role, whether the `prettier: false` escape hatch actually prevents workflow failure modes, whether a new bundle caller fits the adopt engine, and whether the documentation update surface covers all stale “Prettier has no workflow” claims.

I did not run tests, formatters, package-manager installs, workflow executions, or `npm ci` because this audit is read-only and those commands may write caches, build artifacts, or dependency state.

### Prior findings status

#### SA-001: `if: inputs.prettier` can skip Prettier on this repo’s direct workflow triggers

* Previous severity: High
* Current status: Resolved
* Evidence: The current spec still requires a string-safe condition, `format('{0}', inputs.prettier) != 'false'`, and a truth-table test for direct runs, reusable default/true, and reusable boolean false. GitHub docs confirm `workflow_call` inputs are typed and `format()` stringifies replacement values.
* Remaining action for Claude Code: Keep the truth-table test. Also address SA-NEW-003, which is a broader opt-out-workflow false-positive not covered by SA-001.

#### SA-002: The spec does not define safe handling for newline-delimited globs passed to Prettier

* Previous severity: High
* Current status: Superseded
* Evidence: The redesigned spec removes the Prettier `globs` input entirely and specifies `npx --yes prettier@3.8.3 --check .`; the test section now explicitly asserts repo-wide `--check .` and “no `globs`.”
* Remaining action for Claude Code: None for the original glob-injection issue.

#### SA-003: Major-release update surface is incomplete against the repo’s own release contract

* Previous severity: Medium
* Current status: Superseded
* Evidence: The current spec no longer proposes a v5 major release; it classifies the change as v4.x MINOR because the new Prettier caller is opt-in and `lint-markdown.yml` remains unchanged. The v5 `standards-ref` default update surface no longer applies to this design.
* Remaining action for Claude Code: None for the prior v5 surface. Address SA-NEW-001 for the new minor-release documentation surface.

#### SA-004: “Same Markdown” coverage is not guaranteed when markdownlint ignores differ from Prettier ignores

* Previous severity: Medium
* Current status: Resolved
* Evidence: The current spec explicitly states Prettier uses `.prettierignore`/`.gitignore`, markdownlint uses `.markdownlint-cli2.jsonc`, and `UPGRADING.md` must document mirroring markdownlint-only ignores into `.prettierignore`. It also requires a file-set parity test.
* Remaining action for Claude Code: None beyond implementing the specified docs and tests.

#### SA-005: Proposed `tools/` location does not match current coverage/typecheck gates

* Previous severity: Medium
* Current status: Resolved
* Evidence: The spec keeps the coherence tooling under `tests/coherence/`, matching `pyproject.toml` where BasedPyright includes `src` and `tests`, pytest discovers `tests`, and coverage source remains `src`.
* Remaining action for Claude Code: None.

#### SA-006: Agent green-gate update names only `CLAUDE.md`, not the Codex-facing `AGENTS.md`

* Previous severity: Low
* Current status: Resolved
* Evidence: The spec requires updating the green-gate line in both `CLAUDE.md` and `AGENTS.md`.
* Remaining action for Claude Code: None for the green-gate line. Broader purpose/surface text is covered by SA-NEW-001.

### New blocking issues

None found.

### New non-blocking issues

#### SA-NEW-001: Documentation update surface misses stale public and agent-facing “no Prettier workflow” claims

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Acceptance criteria could pass while the repo still tells humans and agents that Prettier has no reusable workflow.
* Spec reference: Component B and acceptance criteria name `docs/superpowers/specs/2026-06-04-linting-formatting-stack.md`, `standards/markdown-tooling/README.md`, `standards/markdown-tooling/adopt.md`, `CHANGELOG.md`, `UPGRADING.md`, and only the green-gate lines in `CLAUDE.md`/`AGENTS.md`.
* Finding: The spec omits root `README.md` and the purpose/surface text in `CLAUDE.md`/`AGENTS.md`, all of which currently describe Markdown Tooling as only `lint-markdown.yml` plus copy-adopt Prettier/no workflow.
* Repository evidence: `README.md` says “Prettier is copy-adopt (no workflow)” and the Markdown Tooling adoption map only mentions `lint-markdown.yml@v4`. `CLAUDE.md` and `AGENTS.md` describe Markdown Tooling as copy-adopt Prettier/EditorConfig plus optional `lint-markdown.yml`.
* External research evidence: Not applicable.
* Why it matters: The spec’s docs acceptance could pass while the human landing page and agent startup instructions remain stale, causing future planners or adopters to miss the new opt-in formatter workflow.
* Recommended action for Claude Code: Add root `README.md` and the relevant purpose/surface text in `CLAUDE.md`/`AGENTS.md` to the required documentation update surface, not just the green-gate command lines.
* Suggested validation: Add a stale-phrase check for “Prettier is copy-adopt (no workflow)”, “no reusable workflow”, and Markdown Tooling adoption snippets that mention `lint-markdown.yml` but not `format.yml`, excluding historical sections where explicitly intended.

#### SA-NEW-002: Node pin/lockfile and CI install path are under-specified

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Pin-alignment tests could pass textually while the Node behavioral tests run uninstalled, float through `npx`, or leave `package-lock.json` inconsistent.
* Spec reference: Component C says `markdownlint-cli2` `0.22.1` is added to `package.json` devDeps, and the dedicated CI job provisions uv + Node. Acceptance requires pin mismatch detection.
* Finding: The spec does not require updating `package-lock.json`, nor does it define whether the new Node CI job runs `npm ci` before subprocess tests or instead invokes explicit `npx --yes prettier@3.8.3` / `npx --yes markdownlint-cli2@0.22.1`.
* Repository evidence: `package.json` and `package-lock.json` are both tracked and currently list only `prettier@3.8.3`. The existing check workflow provisions uv only. The existing `format.yml` uses `npm ci`, but the new design removes `npm ci` from the format workflow.
* External research evidence: `actions/setup-node@v4` supports Node setup and npm caching inputs, but setup-node alone does not install package dependencies.
* Why it matters: A spec implementation could update `package.json` only, leaving the lockfile stale; or CI could provision Node but not install the local devDeps the tests intend to prove. That weakens the “same versions CI enforces” guarantee.
* Recommended action for Claude Code: State that adding `markdownlint-cli2` to devDeps requires regenerating/committing `package-lock.json`, and specify the behavioral-test execution model: either `npm ci` before pytest in the Node job or explicit pinned `npx --yes <tool>@<version>` invocations.
* Suggested validation: After implementation, verify `package.json` and `package-lock.json` agree, and run the dedicated Node coherence job from a clean checkout.

#### SA-NEW-003: `prettier: false` may skip only the Prettier step, not the workflow’s dependency failure surface

* Severity: Medium
* Status: Confirmed
* Adversarial angle: The opt-out acceptance test could prove the check step is skipped while the workflow still fails before reaching it.
* Spec reference: Component A snippet places the `if:` only on “Check formatting (Prettier)”; acceptance says the workflow “skips iff a caller sets `prettier: false`” and that `prettier: false` defers enforcement.
* Finding: The spec does not say whether checkout/setup-node or any future install/setup steps are also conditional, or whether the whole job should be job-gated. If only the Prettier check step is conditional, a caller using `prettier: false` can still fail due setup-node/network/action failures.
* Repository evidence: Current `format.yml` has checkout, setup-node, `npm ci`, then Prettier check. The revised spec keeps setup-node and an `npx` Prettier check but shows the condition only on the check step.
* External research evidence: GitHub workflow syntax supports step/job `if:` conditions; setup-node is an external action with its own runtime and dependency surface.
* Why it matters: The escape hatch is a migration/deferral mechanism. It should avoid formatter-enforcement failures, including dependency setup needed only for formatter enforcement.
* Recommended action for Claude Code: Specify whether `prettier: false` gates the entire `prettier` job or every Node/Prettier-dependent step. The truth-table validation should assert the workflow/job result, not only the final Prettier command step.
* Suggested validation: Add workflow-shape tests that model `prettier: false` and assert no Node setup or Prettier command is required for a successful opt-out path.

### Regressions

None found.

### Remaining ambiguities and decisions needed

* Ambiguity: Whether the new formatter workflow’s opt-out should skip only enforcement or the entire Node-dependent job.
* Why it matters: Determines whether `prettier: false` is a reliable migration escape hatch.
* Recommended clarification: Define job-level versus step-level gating and test the whole opt-out path.
* Blocking or non-blocking: Non-blocking.

* Ambiguity: Whether Node behavioral tests use installed devDeps from `npm ci` or explicit pinned `npx --yes tool@version`.
* Why it matters: Determines whether `package.json`/`package-lock.json` are the real execution source or only metadata.
* Recommended clarification: Pick one execution model and make lockfile/update validation match it.
* Blocking or non-blocking: Non-blocking.

* Ambiguity: Full stale-documentation surface for the new opt-in `format.yml`.
* Why it matters: Root README and agent instructions are evidence future agents and humans actually read.
* Recommended clarification: Include `README.md`, `CLAUDE.md`, and `AGENTS.md` surface text in the spec’s docs checklist.
* Blocking or non-blocking: Non-blocking.

### Internet research performed

* Source name: GitHub Docs — Expressions
* URL: https://docs.github.com/en/actions/reference/workflows-and-actions/expressions
* Access date: 2026-07-06
* What it was used to verify: `format()` behavior and expression semantics relevant to the `prettier` boolean input condition.
* Relevant conclusion: The spec’s string-safe `format('{0}', inputs.prettier) != 'false'` condition remains appropriate for the prior SA-001 issue.

* Source name: GitHub Docs — Workflow syntax for GitHub Actions
* URL: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
* Access date: 2026-07-06
* What it was used to verify: `workflow_call` input typing/default behavior and conditional workflow semantics.
* Relevant conclusion: Boolean workflow-call inputs are valid, but the spec still needs to clarify whether opt-out gating is step-level or job-level.

* Source name: Prettier CLI documentation
* URL: https://prettier.io/docs/cli
* Access date: 2026-07-06
* What it was used to verify: `prettier . --check`, directory traversal, supported-file discovery, exit codes, and glob/path behavior.
* Relevant conclusion: `prettier .` checks all Prettier-supported files under the directory, not only Markdown/YAML/JSON.

* Source name: Prettier Ignoring Code documentation
* URL: https://prettier.io/docs/ignore
* Access date: 2026-07-06
* What it was used to verify: `.prettierignore`, `.gitignore`, `node_modules`, and VCS-directory ignore behavior.
* Relevant conclusion: The spec’s ignore/parity framing is directionally correct.

* Source name: `markdownlint-cli2-action` `action.yml` at `v23`
* URL: https://raw.githubusercontent.com/DavidAnson/markdownlint-cli2-action/v23/action.yml
* Access date: 2026-07-06
* What it was used to verify: Action input contract, newline-delimited `globs`, default glob, and Node runtime.
* Relevant conclusion: The prior SA-002 newline-glob hazard is superseded by the new no-globs Prettier design.

* Source name: `markdownlint-cli2-action` `package.json` at `v23`
* URL: https://raw.githubusercontent.com/DavidAnson/markdownlint-cli2-action/v23/package.json
* Access date: 2026-07-06
* What it was used to verify: Bundled `markdownlint-cli2` version.
* Relevant conclusion: `markdownlint-cli2-action@v23` bundles `markdownlint-cli2@0.22.1`, matching the spec’s intended local pin.

* Source name: `actions/setup-node` `v4` metadata
* URL: https://raw.githubusercontent.com/actions/setup-node/v4/action.yml
* Access date: 2026-07-06
* What it was used to verify: setup-node inputs and runtime.
* Relevant conclusion: `setup-node@v4` can provision Node and supports npm cache inputs, but it does not by itself install `package.json` devDeps.

### Read-only validation performed

* `pwd`, `git status --short`, `git branch --show-current`, `git log --oneline -n 10`, `git diff --stat`: confirmed repository root, branch `testing`, and the spec as the modified tracked file.
* `nl -ba docs/superpowers/specs/2026-07-06-markdown-tooling-formatter-authority-design.md`: inventoried current round-4 spec text and line-level requirements.
* `git diff -- docs/superpowers/specs/2026-07-06-markdown-tooling-formatter-authority-design.md`: isolated the redesign from v5/default-on to v4.x opt-in separate workflow.
* `rg --files`: identified relevant workflows, configs, bundle manifests, docs, tests, package files, and schemas.
* Inspected `.github/workflows/format.yml`, `lint-markdown.yml`, `check.yml`, `validate-markdown-frontmatter.yml`, and `validate-specs.yml`: confirmed current workflow shape, direct triggers, reusable workflow surfaces, and v4 defaults.
* Inspected `src/project_standards/bundles/markdown-tooling/adopt.toml`, `lint-markdown.caller.yml`, `src/project_standards/adopt/engine.py`, and `manifest.py`: verified current adopt artifact list, caller rendering, and `major_ref()` behavior.
* Inspected `package.json` and `package-lock.json`: confirmed only `prettier@3.8.3` is currently pinned and the lockfile would need updating if `markdownlint-cli2` becomes a devDep.
* Inspected `pyproject.toml`, `registry.json`, and `.project-standards.yml`: confirmed current version state, test/typecheck coverage shape, and current `markdown_tooling` `1.0` default.
* Inspected `standards/markdown-tooling/README.md`, `standards/markdown-tooling/adopt.md`, root `README.md`, `CLAUDE.md`, and `AGENTS.md`: found stale “Prettier no workflow/copy-adopt only” surfaces not covered by the revised spec.
* Inspected `.prettierrc.json`, `.markdownlint.json`, `.markdownlint-cli2.jsonc`, and `.prettierignore`: verified current formatter/linter config assumptions and ignore parity context.
* Inspected `tests/test_markdownlint_config.py`, `tests/test_adopt_dogfood.py`, `tests/test_adopt_packaging.py`, and `tests/test_adopt_manifest.py`: verified current test patterns and where new caller/pin/coherence checks would need to land.
* Ran `rg -n` over docs/workflows/configs for `DEC-9`, `Prettier`, `copy-adopt`, `no reusable`, `format.yml`, `contract version`, `markdown_tooling`, `@v4`, and `standards-ref`: located stale doc/update surfaces relevant to the revised design.

### Recommended planning/implementation validation

* Run only after implementation: workflow truth-table test for direct run, reusable default/true, and reusable `prettier: false`, asserting whole job/workflow behavior, not just the Prettier command step.
* Run only after implementation: test that `prettier: false` does not require Node setup or formatter dependency installation if that is the intended escape hatch.
* Run only after implementation: adopt integration test proving `adopt markdown-tooling` writes `format.caller.yml`, renders `{{ref}}` to `v<major>`, and includes the artifact in packaging.
* Run only after implementation: stale-doc guard covering root `README.md`, `standards/markdown-tooling/README.md`, `standards/markdown-tooling/adopt.md`, `CLAUDE.md`, `AGENTS.md`, CHANGELOG, and UPGRADING.
* Run only after implementation: package-lock consistency check after adding `markdownlint-cli2` devDep, or explicit pinned `npx --yes` tests if the package files are not the execution source.
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
* Run only after implementation: the new coherence CI job with Node present, plus a Node-absent skip-path check if feasible.

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-07-06-markdown-tooling-formatter-authority-design.md`
* Audit round: 4
* Open issue IDs: SA-NEW-001, SA-NEW-002, SA-NEW-003
* Resolved issue IDs: SA-001, SA-004, SA-005, SA-006
* Superseded issue IDs: SA-002, SA-003
* Significant findings remaining: Yes
* Next audit should focus on: Whether the spec adds the missing docs surfaces, clarifies full opt-out/job behavior, and defines the Node devDep/lockfile/CI install model.