### Executive summary

Claude Code’s revision resolved most prior findings, but one blocking workflow-condition issue remains. The revised spec correctly accounts for direct `push`/`pull_request` runs and safe glob argv construction, but its proposed condition `inputs.prettier != 'false'` is not reliable for a typed boolean `workflow_call` input: a caller-provided boolean `false` can compare unequal to the string `'false'`, so the opt-out may not opt out.

New internet research was required for current GitHub Actions expression/input semantics.

### Verdict

Needs major specification correction before planning/implementation

### Audit loop status

* Audit type: Follow-up audit
* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-07-06-markdown-tooling-formatter-authority-design.md`
* Prior audit issue count: 6
* Resolved issue count: 4
* Still open issue count: 0
* Partially resolved issue count: 2
* New issue count: 0
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

I re-read the revised spec and retested prior findings SA-001 through SA-006 against the current workflow shape, release/versioning contract, docs, package metadata, tests, and official GitHub Actions/Prettier/markdownlint action documentation.

The strongest retests were the `prettier` input condition across direct and reusable triggers, newline-delimited glob handling, file-set parity wording, the major-release update surface, coherence-tool placement versus typecheck/coverage scope, and cross-harness green-gate updates.

I did not run tests or formatting/lint commands because this is a read-only audit and those gates may write caches, package artifacts, or generated state.

### Prior findings status

#### SA-001: `if: inputs.prettier` can skip Prettier on this repo’s direct workflow triggers

* Previous severity: High
* Current status: Partially resolved
* Evidence: The spec now recognizes the dual-role workflow and requires direct-trigger coverage, but it specifies `if: ${{ inputs.prettier != 'false' }}` at lines 57 and 62. GitHub’s `inputs` context preserves boolean input values as booleans for reusable workflows, and GitHub expression equality uses loose type coercion when types differ. Comparing boolean `false` to string `'false'` is therefore not a safe proof that caller `prettier: false` skips the step. Repository evidence still shows `.github/workflows/lint-markdown.yml` is dual-triggered and currently uses direct-run fallbacks for `inputs.globs`.
* Remaining action for Claude Code: Replace the condition requirement with one that is proven for all three cases: direct event runs, reusable caller default/true, and reusable caller explicit boolean `false`. The spec should require tests against GitHub expression semantics, not just textual presence of the expression.

#### SA-002: The spec does not define safe handling for newline-delimited globs passed to Prettier

* Previous severity: High
* Current status: Resolved
* Evidence: The revised spec defines `globs` as newline-delimited data, passes it through `env:`, splits with `mapfile`, filters blanks, falls back to `**/*.md`, and passes `"${patterns[@]}"` to Prettier. It also requires tests for default, single, multiple newline-delimited, and shell-metacharacter cases.
* Remaining action for Claude Code: None beyond implementing the specified tests.

#### SA-003: Major-release update surface is incomplete against the repo’s own release contract

* Previous severity: Medium
* Current status: Partially resolved
* Evidence: The revised spec now includes `pyproject.toml`, regenerated `uv.lock`, README and `standards/*/adopt.md` `@v4` examples, the Markdown Tooling contract banner, registry/default changes, CHANGELOG, UPGRADING, and stale-reference grep guards. However, `meta/versioning.md` also requires major-release bumps for reusable workflow `standards-ref` defaults in `.github/workflows/validate-markdown-frontmatter.yml` and `.github/workflows/validate-specs.yml`; both currently contain `default: "v4"`. The revised checklist and acceptance criteria focus on `@v4` and `markdown_tooling` `1.0` references, so a grep guard could pass while `standards-ref` defaults still lag.
* Remaining action for Claude Code: Add explicit `standards-ref` default bumps and guard coverage for bare `v4` workflow defaults, not only `@v4` examples.

#### SA-004: “Same Markdown” coverage is not guaranteed when markdownlint ignores differ from Prettier ignores

* Previous severity: Medium
* Current status: Resolved
* Evidence: The revised spec explicitly states Prettier gates `globs` minus `.prettierignore`/`.gitignore`, while markdownlint can use `.markdownlint-cli2.jsonc`; it requires UPGRADING parity guidance and a file-set parity test.
* Remaining action for Claude Code: None beyond implementing the documented parity guidance and test.

#### SA-005: Proposed `tools/` location does not match current coverage/typecheck gates

* Previous severity: Medium
* Current status: Resolved
* Evidence: The revised spec moves the repo-local coherence checks under `tests/coherence/`, matching current `basedpyright.include = ["src", "tests"]` and pytest discovery. It also drops the unsupported “counts toward coverage” claim for a `tools/` module.
* Remaining action for Claude Code: None.

#### SA-006: Agent green-gate update names only `CLAUDE.md`, not the Codex-facing `AGENTS.md`

* Previous severity: Low
* Current status: Resolved
* Evidence: Component C now requires the green-gate line in both `CLAUDE.md` and `AGENTS.md`, and acceptance criteria include both files.
* Remaining action for Claude Code: None.

### New blocking issues

None found.

### New non-blocking issues

None found.

### Regressions

None found.

### Remaining ambiguities and decisions needed

* Ambiguity: What exact GitHub Actions expression should implement “direct runs and reusable true run; reusable false skips”?
* Why it matters: The current string comparison can fail the opt-out case, defeating the migration escape hatch.
* Recommended clarification: Specify an expression based on event type and boolean input semantics, and require tests that model GitHub’s typed boolean behavior.
* Blocking or non-blocking: Blocking.

* Ambiguity: Does the v5 release checklist include bare `standards-ref: v4` defaults in reusable validator workflows?
* Why it matters: `meta/versioning.md` treats those defaults as part of the major-release surface; stale defaults can make a `@v5` caller install the v4 validator by default.
* Recommended clarification: Add those workflow defaults explicitly to the rollout checklist and stale-reference guard.
* Blocking or non-blocking: Non-blocking.

### Internet research performed

* Source name: GitHub Docs — Expressions
* URL: https://docs.github.com/en/actions/reference/workflows-and-actions/expressions
* Access date: 2026-07-06
* What it was used to verify: Equality, type coercion, and truthiness in GitHub Actions expressions.
* Relevant conclusion: GitHub performs loose equality comparisons and coerces mismatched types to numbers; this makes boolean-versus-string comparisons unsafe for the proposed opt-out condition.

* Source name: GitHub Docs — Contexts, `inputs` context
* URL: https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#inputs-context
* Access date: 2026-07-06
* What it was used to verify: Reusable workflow input types.
* Relevant conclusion: `inputs.<name>` can be boolean, number, string, or choice; boolean workflow inputs are preserved as booleans.

* Source name: GitHub Docs — Workflow syntax for GitHub Actions
* URL: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
* Access date: 2026-07-06
* What it was used to verify: Workflow triggers, run-step behavior, and workflow-call input context.
* Relevant conclusion: The local workflow’s dual direct/reusable trigger shape remains relevant to the condition design.

* Source name: Prettier CLI documentation
* URL: https://prettier.io/docs/cli
* Access date: 2026-07-06
* What it was used to verify: Glob argv behavior, quoting guidance, `--check`, and ignore-path behavior.
* Relevant conclusion: The revised quoted-array argv approach aligns with Prettier’s guidance to let Prettier expand globs.

* Source name: Prettier Ignoring Code documentation
* URL: https://prettier.io/docs/ignore
* Access date: 2026-07-06
* What it was used to verify: `.prettierignore` and `.gitignore` behavior.
* Relevant conclusion: The revised file-set parity section correctly distinguishes Prettier ignores from markdownlint-only ignores.

* Source name: markdownlint-cli2-action `action.yml` at `v23`
* URL: https://raw.githubusercontent.com/DavidAnson/markdownlint-cli2-action/v23/action.yml
* Access date: 2026-07-06
* What it was used to verify: `globs` contract and Node runtime.
* Relevant conclusion: `globs` is newline-delimited, defaults to `*.{md,markdown}`, and the action runs on Node 24.

* Source name: markdownlint-cli2-action `package.json` at `v23`
* URL: https://raw.githubusercontent.com/DavidAnson/markdownlint-cli2-action/v23/package.json
* Access date: 2026-07-06
* What it was used to verify: Bundled `markdownlint-cli2` version.
* Relevant conclusion: `markdownlint-cli2-action` `23.2.0` depends on `markdownlint-cli2` `0.22.1`, matching the revised spec.

* Source name: actions/setup-node `v4` metadata
* URL: https://raw.githubusercontent.com/actions/setup-node/v4/action.yml
* Access date: 2026-07-06
* What it was used to verify: Node setup and cache inputs.
* Relevant conclusion: `setup-node@v4` supports `node-version`, `cache`, and `cache-dependency-path`.

### Read-only validation performed

* `pwd`, `git status --short`, `git branch --show-current`, `git log --oneline -n 10`, `git diff --stat`: confirmed repository root, branch `testing`, revised spec as the only modified tracked file, and an untracked prior review artifact.
* `nl -ba docs/superpowers/specs/2026-07-06-markdown-tooling-formatter-authority-design.md`: re-inventoried the revised spec and line references.
* `rg --files ...`: identified relevant workflows, docs, configs, source, tests, and bundle artifacts.
* Inspected `.github/workflows/lint-markdown.yml`, `format.yml`, `check.yml`, `validate-markdown-frontmatter.yml`, and `validate-specs.yml`: confirmed dual-trigger workflow shape, current markdownlint-only reusable gate, current repo-local Prettier gate, and stale `standards-ref` defaults.
* Inspected `package.json`, `package-lock.json`, `pyproject.toml`, `registry.json`, `.project-standards.yml`, and `src/project_standards/adopt/engine.py`: verified current pins, package version, typecheck/coverage scope, registry shape, dogfood config, and `major_ref()` behavior.
* Inspected Markdown Tooling docs/adopt guide, `meta/versioning.md`, README references, `CLAUDE.md`, `AGENTS.md`, and relevant tests: verified which prior documentation and rollout findings are now covered and which release-default gap remains.
* Inspected `.markdownlint-cli2.jsonc`, `.prettierignore`, `.prettierrc.json`, and `.markdownlint.json`: verified file-set parity assumptions and shipped config values.
* `git diff -- docs/superpowers/specs/...`: compared the revised spec against the prior version to isolate correction changes.

### Recommended planning/implementation validation

* Run only after implementation: workflow-shape tests proving the Prettier step runs on direct `push`/`pull_request`, runs for reusable default/true, and skips for reusable boolean `false`.
* Run only after implementation: tests for newline-delimited glob splitting, quoted argv, blank fallback, and shell-metacharacter patterns.
* Run only after implementation: stale-reference guard covering `@v4`, bare `standards-ref` `v4` defaults, and `markdown_tooling` `1.0` defaults outside intentionally historical docs.
* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest && uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`
* Run only after implementation: repo Prettier check through `npm ci && npx prettier --check .`
* Run only after implementation: markdownlint workflow-equivalent check for the repo’s Markdown globs.
* Run only after implementation: the new coherence job in CI with Node present, plus a local Node-absent skip-path check if feasible.

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-07-06-markdown-tooling-formatter-authority-design.md`
* Audit round: 2
* Open issue IDs: SA-001, SA-003
* Resolved issue IDs: SA-002, SA-004, SA-005, SA-006
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: the corrected GitHub Actions condition for typed boolean `prettier: false`, and explicit v5 handling of bare `standards-ref` defaults in reusable validator workflows.