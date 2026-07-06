### Executive summary

Claude Code’s round-3 revisions resolve the two remaining prior findings. The specification now gives a coercion-safe `prettier` condition for typed GitHub Actions boolean inputs and explicitly includes bare `standards-ref: "v4"` workflow defaults in the v5 major-release update surface.

New internet research was performed to re-check GitHub Actions expression/input semantics and the external formatter/action assumptions. No significant findings remain.

### Verdict

No significant findings remain

### Audit loop status

* Audit type: Follow-up audit
* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-07-06-markdown-tooling-formatter-authority-design.md`
* Prior audit issue count: 6
* Resolved issue count: 6
* Still open issue count: 0
* Partially resolved issue count: 0
* New issue count: 0
* Regression count: 0
* Significant findings remaining: No

### Adversarial review performed

I re-read the current spec, compared it against the round-2 diff, and retested prior findings SA-001 through SA-006 against repository evidence: workflow triggers and inputs, versioning policy, release surfaces, docs/adopt examples, registry/package pins, configs, tests, and agent green-gate files.

The strongest retests were the GitHub Actions `prettier` opt-out condition for direct/reusable runs, bare `standards-ref` defaults during a v5 major bump, newline-delimited glob handling, markdownlint/Prettier file-set parity, coherence-tool placement under `tests/`, and cross-harness `CLAUDE.md`/`AGENTS.md` updates.

I did not run tests, formatters, package-manager installs, or workflow execution because this is a read-only audit and those checks may write caches, generated state, or dependency artifacts. I also could not prove live GitHub Actions evaluation in GitHub’s runner; the spec now correctly requires that proof during planning/implementation validation.

### Prior findings status

#### SA-001: `if: inputs.prettier` can skip Prettier on this repo’s direct workflow triggers

* Previous severity: High
* Current status: Resolved
* Evidence: The spec now replaces the unsafe boolean/string comparison with `if: ${{ format('{0}', inputs.prettier) != 'false' }}` at lines 57 and 62, and requires a truth-table test for direct trigger, reusable `true`, and reusable boolean `false`. GitHub docs confirm workflow-call inputs require declared types, boolean values are preserved in the `inputs` context, loose equality coerces mismatched types numerically, and string conversion maps boolean `false` to `'false'`. Repository evidence still shows `.github/workflows/lint-markdown.yml` is dual-role with direct `push`/`pull_request` plus `workflow_call`.
* Remaining action for Claude Code: None for the specification. Implementation must still prove the expression with the truth-table test the spec now requires.

#### SA-002: The spec does not define safe handling for newline-delimited globs passed to Prettier

* Previous severity: High
* Current status: Resolved
* Evidence: Still resolved. Current lines 58-69 specify passing `globs` via `env`, splitting newline-delimited data with `mapfile`, filtering blanks, falling back to `**/*.md`, and passing quoted argv to Prettier. Lines 154-155 require default, single, multiple, and shell-metacharacter glob tests.
* Remaining action for Claude Code: None beyond implementing the specified tests.

#### SA-003: Major-release update surface is incomplete against the repo’s own release contract

* Previous severity: Medium
* Current status: Resolved
* Evidence: Current line 131 explicitly adds the bare `standards-ref: "v4"` defaults in `.github/workflows/validate-markdown-frontmatter.yml` and `.github/workflows/validate-specs.yml` to the v5 update checklist, and line 149 makes them acceptance criteria. Repository evidence confirms both workflows currently have `default: "v4"` for `standards-ref`, and `meta/versioning.md` lines 136-145 requires those defaults to move on a major release.
* Remaining action for Claude Code: None for the specification. Implementation should include the specified stale-reference guard.

#### SA-004: “Same Markdown” coverage is not guaranteed when markdownlint ignores differ from Prettier ignores

* Previous severity: Medium
* Current status: Resolved
* Evidence: Still resolved. Current line 74 states Prettier honors `.prettierignore`/`.gitignore`, not `.markdownlint-cli2.jsonc`, and requires UPGRADING parity guidance. Line 157 requires a file-set parity test. Local `.markdownlint-cli2.jsonc` and `.prettierignore` currently mirror the repo-local ignored paths.
* Remaining action for Claude Code: None beyond implementing the documented parity guidance and tests.

#### SA-005: Proposed `tools/` location does not match current coverage/typecheck gates

* Previous severity: Medium
* Current status: Resolved
* Evidence: Still resolved. Current line 88 places the coherence checks under `tests/coherence/`, matching `pyproject.toml` lines 56-70 where BasedPyright includes `src` and `tests`, pytest discovers `tests`, and coverage source remains `src`.
* Remaining action for Claude Code: None.

#### SA-006: Agent green-gate update names only `CLAUDE.md`, not the Codex-facing `AGENTS.md`

* Previous severity: Low
* Current status: Resolved
* Evidence: Still resolved. Current line 113 requires updating both `CLAUDE.md` and `AGENTS.md`; line 149 includes both files in acceptance criteria. Repository evidence confirms both files carry green-gate/toolchain instructions today.
* Remaining action for Claude Code: None.

### New blocking issues

None found.

### New non-blocking issues

None found.

### Regressions

None found.

### Remaining ambiguities and decisions needed

None found.

### Internet research performed

* Source name: GitHub Docs — Expressions
* URL: https://docs.github.com/en/actions/reference/workflows-and-actions/expressions
* Access date: 2026-07-06
* What it was used to verify: GitHub Actions loose equality, numeric coercion, truthiness, string conversion, and `format()` expression behavior.
* Relevant conclusion: The spec’s `format('{0}', inputs.prettier) != 'false'` approach addresses the prior boolean-vs-string coercion problem.

* Source name: GitHub Docs — Contexts, `inputs` context
* URL: https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#inputs-context
* Access date: 2026-07-06
* What it was used to verify: What the `inputs` context represents for reusable workflows.
* Relevant conclusion: Reusable workflow inputs are accessed through `inputs`, supporting the spec’s truth-table requirement.

* Source name: GitHub Docs — Workflow syntax for GitHub Actions
* URL: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
* Access date: 2026-07-06
* What it was used to verify: `workflow_call` input typing/defaults and caller input type matching.
* Relevant conclusion: `workflow_call.inputs` requires `type`, supports `boolean`, and defaults are typed, so the spec’s boolean input surface is valid.

* Source name: Prettier CLI documentation
* URL: https://prettier.io/docs/cli
* Access date: 2026-07-06
* What it was used to verify: `--check`, path/glob argv behavior, and quoting guidance.
* Relevant conclusion: Quoted argv that lets Prettier expand globs is aligned with official guidance.

* Source name: Prettier Ignoring Code documentation
* URL: https://prettier.io/docs/ignore
* Access date: 2026-07-06
* What it was used to verify: `.prettierignore` and `.gitignore` behavior.
* Relevant conclusion: The spec correctly distinguishes Prettier ignores from markdownlint-specific ignores.

* Source name: markdownlint-cli2-action `action.yml` at `v23`
* URL: https://raw.githubusercontent.com/DavidAnson/markdownlint-cli2-action/v23/action.yml
* Access date: 2026-07-06
* What it was used to verify: Action input contract and runtime.
* Relevant conclusion: `globs` is newline-delimited, defaults to `*.{md,markdown}`, and the action runs on Node 24.

* Source name: markdownlint-cli2-action `package.json` at `v23`
* URL: https://raw.githubusercontent.com/DavidAnson/markdownlint-cli2-action/v23/package.json
* Access date: 2026-07-06
* What it was used to verify: Bundled `markdownlint-cli2` version.
* Relevant conclusion: `markdownlint-cli2-action` `23.2.0` depends on `markdownlint-cli2` `0.22.1`, matching the spec.

* Source name: actions/setup-node `v4` metadata
* URL: https://raw.githubusercontent.com/actions/setup-node/v4/action.yml
* Access date: 2026-07-06
* What it was used to verify: Node setup inputs.
* Relevant conclusion: `setup-node@v4` supports `node-version` and npm cache inputs; the spec’s no-cache reusable-workflow choice is consistent with consumer repos lacking a lockfile.

### Read-only validation performed

* `pwd`, `git status --short`, `git branch --show-current`, `git log --oneline -n 10`, `git diff --stat`: confirmed repository root, branch `testing`, the spec as the only modified tracked file, and prior review artifacts as untracked files.
* `nl -ba docs/superpowers/specs/2026-07-06-markdown-tooling-formatter-authority-design.md`: inventoried the revised spec and line references.
* `git diff -- docs/superpowers/specs/2026-07-06-markdown-tooling-formatter-authority-design.md`: isolated the round-3 corrections for SA-001 and SA-003.
* `rg --files`: identified relevant workflows, docs, configs, source, tests, and bundled artifacts.
* Inspected `.github/workflows/lint-markdown.yml`, `format.yml`, `check.yml`, `validate-markdown-frontmatter.yml`, and `validate-specs.yml`: confirmed dual-trigger Markdown workflow shape, repo-local Prettier gate, current green gates, and existing `standards-ref` defaults.
* Inspected `package.json`, `pyproject.toml`, `registry.json`, `.project-standards.yml`, and `src/project_standards/adopt/engine.py`: verified current pins, version state, typecheck/test scope, registry shape, dogfood config, and `major_ref()` behavior.
* Inspected `standards/markdown-tooling/README.md`, `standards/markdown-tooling/adopt.md`, `meta/versioning.md`, `README.md`, `CLAUDE.md`, `AGENTS.md`, and `tests/test_adopt_dogfood.py`: verified release-surface obligations, stale-reference targets, and cross-harness green-gate requirements.
* Inspected `.markdownlint.json`, `.prettierrc.json`, `.markdownlint-cli2.jsonc`, and `.prettierignore`: verified config coherence assumptions and ignore parity context.
* Ran `rg -n '@v4|standards-ref: ?"?v4|markdown_tooling|contract version `1\.0`|v4' ...`: located current v4 and `markdown_tooling` references that the spec’s major-release checklist and guard must address.

### Recommended planning/implementation validation

* Run only after implementation: workflow-shape tests proving the Prettier step runs on direct `push`/`pull_request`, runs for reusable default/true, and skips for reusable boolean `false`.
* Run only after implementation: tests for newline-delimited glob splitting, quoted argv, blank fallback, and shell-metacharacter patterns.
* Run only after implementation: stale-reference guard covering `@v4`, bare `standards-ref` `v4` defaults, and `markdown_tooling` `1.0` defaults outside intentionally historical docs.
* Run only after implementation: pin-alignment test for workflow Prettier `3.8.3` vs `package.json`, and local `markdownlint-cli2` vs `markdownlint-cli2-action@v23`.
* Run only after implementation: coherence corpus tests for declaration conformance, Prettier-to-markdownlint co-satisfaction, and fixed-point stability.
* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest && uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`
* Run only after implementation: repo Prettier check through `npm ci && npx prettier --check .`
* Run only after implementation: markdownlint workflow-equivalent check for the repo’s Markdown globs.
* Run only after implementation: the new coherence CI job with Node present, plus a local Node-absent skip-path check if feasible.

### Final recommendation

No significant findings remain; the audit/fix loop can stop

### Review ledger for next loop

* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-07-06-markdown-tooling-formatter-authority-design.md`
* Audit round: 3
* Open issue IDs: None
* Resolved issue IDs: SA-001, SA-002, SA-003, SA-004, SA-005, SA-006
* Superseded issue IDs:
* Significant findings remaining: No
* Next audit should focus on: None; the audit/fix loop can stop.