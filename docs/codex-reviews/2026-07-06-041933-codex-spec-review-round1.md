### Executive summary

The specification identifies a real Markdown Tooling coherence gap and chooses a plausible major-release direction, but it is not ready for Claude Code to use as the basis for planning/implementation. The main blockers are in the reusable workflow details: the proposed `if: inputs.prettier` guard does not account for this workflow’s existing direct `push`/`pull_request` triggers, and the spec does not define a safe, correct way to pass newline-delimited Markdown globs to Prettier.

Internet research was required because the spec depends on current GitHub Actions, `setup-node`, `npx`, Prettier CLI, and `markdownlint-cli2-action` behavior. The most important stale-assumption finding is that the spec treats `workflow_call` inputs as if they cover the workflow’s direct triggers too.

### Verdict

Needs major specification correction before planning/implementation

### Audit loop status

* Audit type: First audit
* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-07-06-markdown-tooling-formatter-authority-design.md`
* Significant findings remaining: Yes
* Blocking issue count: 2
* Non-blocking issue count: 4

### What the specification gets right

* Correctly identifies that the current reusable `lint-markdown.yml` enforces markdownlint only, while `.prettierrc.json` is copied and recommended but not enforced for consumers.
* Correctly treats on-by-default Prettier enforcement as a breaking change that belongs in a new major line.
* Correctly preserves `validate-markdown-frontmatter.yml` as Node-free for frontmatter-only consumers.
* Correctly recognizes that a repo-local coherence proof should pin tool versions and test behavior, not only static config assertions.
* Correctly keeps `.prettierrc.json` and `.markdownlint.json` value changes out of scope.

### Adversarial review performed

I inventoried the spec’s workflow, documentation, coherence-tool, versioning, rollout, acceptance, and testing requirements, then checked them against the repository’s current workflows, bundle artifacts, docs, registry, config, tests, package metadata, and release standard.

The strongest assumptions tested were: `workflow_call` input defaults, direct `push`/`pull_request` behavior, newline-delimited globs, shell-safe Prettier invocation, “same Markdown” coverage between markdownlint and Prettier, pin alignment with `markdownlint-cli2-action@v23`, package/version rollout requirements, and whether a `tools/` implementation would actually be covered by the current Python gates.

Could not verify live GitHub CI status or the linked issue body; the GitHub issue page fetch failed and search returned no result. I did not run tests or formatters because they may create caches/artifacts and the audit is read-only.

### Blocking issues

#### SA-001: `if: inputs.prettier` can skip Prettier on this repo’s direct workflow triggers

* Severity: High
* Status: Confirmed
* Adversarial angle: A workflow-shape test can pass while `lint-markdown.yml` does not actually run Prettier on the repo’s own `push`/`pull_request` events.
* Spec reference: Component A lines 56-57; acceptance criteria lines 127 and 132; testing line 136.
* Finding: The spec says the Prettier step is guarded by `if: inputs.prettier`, but `.github/workflows/lint-markdown.yml` is both reusable and directly triggered by `push`/`pull_request`. `workflow_call` input defaults apply to called workflows; the existing workflow already has to use `inputs.globs || '**/*.md'` because `inputs.globs` is empty on this repo’s direct runs. The spec does not define equivalent behavior for the new boolean input.
* Repository evidence: Current `lint-markdown.yml` has `push`, `pull_request`, and `workflow_call` triggers, and comments explicitly state that on this repo’s push/PR runs `inputs.globs` is empty and requires a fallback. The spec proposes only `if: inputs.prettier`.
* External research evidence: GitHub docs define `on.workflow_call.inputs` for values passed from caller workflows and say the `inputs` context is used “within the called workflow”; they also define boolean defaults under `workflow_call`, not general direct event triggers. Source: GitHub Docs, https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onworkflow_callinputs, accessed 2026-07-06.
* Why it matters: The repo could add the input and the test requested by the spec, yet the new Prettier step could be skipped on direct PR/push runs. That weakens dogfooding and can make acceptance criteria falsely pass.
* Recommended action for Claude Code: Specify the intended behavior for non-`workflow_call` events and require an expression/test that proves Prettier runs by default for both direct and called workflow invocations, while skipping only when a reusable caller explicitly sets `prettier: false`.
* Suggested validation: Add workflow-shape tests that inspect both the reusable-call default and the direct-trigger fallback/condition, not only that the input exists.

#### SA-002: The spec does not define safe handling for newline-delimited globs passed to Prettier

* Severity: High
* Status: Confirmed
* Adversarial angle: The documented “newline-delimited globs” surface can break or be interpreted as shell script rather than Prettier argv.
* Spec reference: Component A lines 54-57; existing workflow contract lines 35-39; acceptance line 127.
* Finding: The existing workflow documents `globs` as newline-delimited for markdownlint-cli2-action. The spec says to run `npx --yes prettier@<PIN> --check` over `inputs.globs`, but does not specify how to convert a newline-delimited string into safely quoted Prettier arguments. A naive `run: npx --yes prettier@3.8.3 --check ${{ inputs.globs }}` would be fragile for multiple globs, whitespace, shell metacharacters, or newline-separated values.
* Repository evidence: `.github/workflows/lint-markdown.yml` describes `globs` as newline-delimited and passes the raw value to an action input, not to a shell command. The spec changes that contract by adding a shell-based Prettier step without defining argument construction.
* External research evidence: Prettier’s CLI accepts `[file/dir/glob ...]` and explicitly warns not to forget quotes around globs so Prettier, not the shell, expands them. GitHub Actions docs state that multi-line `run` commands execute each line in the shell. Sources: Prettier CLI, https://prettier.io/docs/cli, accessed 2026-07-06; GitHub Actions workflow syntax, https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax, accessed 2026-07-06.
* Why it matters: The acceptance criteria could pass for the single default glob but fail for the documented multi-glob caller interface, or worse, encourage unsafe shell interpolation.
* Recommended action for Claude Code: Specify a safe argv construction strategy for Prettier globs, including newline splitting, empty input fallback, quoting, and tests for multiple globs.
* Suggested validation: Add tests for default glob, one explicit glob, newline-delimited multiple globs, and a glob containing characters that must not be shell-expanded.

### Non-blocking issues

#### SA-003: Major-release update surface is incomplete against the repo’s own release contract

* Severity: Medium
* Status: Confirmed
* Adversarial angle: A release can satisfy the spec’s listed acceptance criteria while leaving stale `@v4` and `1.0` consumer-facing references.
* Spec reference: Versioning & rollout lines 111-114; acceptance line 131.
* Finding: The spec mentions package `5.0.0`, registry/default changes, `.project-standards.yml`, CHANGELOG, and UPGRADING, but it does not require updating all major-release references required by `meta/versioning.md`, including README examples, all relevant `standards/*/adopt.md` examples, workflow defaults where applicable, and the Markdown Tooling standard’s own contract-version banner.
* Repository evidence: `meta/versioning.md` requires major releases to bump in-repo version references in README and each `standards/*/adopt.md`, bump `pyproject.toml` and regenerate `uv.lock`, update CHANGELOG, and rewrite UPGRADING. Current `standards/markdown-tooling/README.md` says contract version `1.0`; `standards/markdown-tooling/adopt.md` shows `@v4` and `markdown_tooling.version: '1.0'`.
* External research evidence: Not applicable.
* Why it matters: Consumers could receive a v5 change with stale copy/paste instructions or contradictory version metadata.
* Recommended action for Claude Code: Add an explicit rollout/update-surface checklist matching `meta/versioning.md`, including Markdown Tooling status banner, README, adoption docs, pyproject/uv.lock, and relevant workflow examples/defaults.
* Suggested validation: Add or reuse tests/grep checks that fail on stale `@v4` examples or stale `markdown_tooling` `1.0` default references after the major bump, excluding historical UPGRADING/changelog sections intentionally left unchanged.

#### SA-004: “Same Markdown” coverage is not guaranteed when markdownlint ignores differ from Prettier ignores

* Severity: Medium
* Status: Confirmed
* Adversarial angle: The two gates can check different Markdown files while the spec claims they check the same Markdown.
* Spec reference: Component A line 54; non-goal line 123; acceptance line 127.
* Finding: The spec says Prettier runs over the same Markdown that markdownlint lints, while also saying no `.prettierignore` is shipped. But markdownlint can discover `.markdownlint-cli2.jsonc` ignores that Prettier does not read. Consumers with generated Markdown excluded from markdownlint can become newly red under Prettier unless they independently mirror those ignores.
* Repository evidence: This repo has `.markdownlint-cli2.jsonc` ignores for `docs/codex-reviews/**`, `docs/handoff/**`, and `tests/fixtures/specs/**`, and a separate `.prettierignore` that mirrors them. The standard does not ship `.markdownlint-cli2.jsonc` or `.prettierignore`.
* External research evidence: Prettier docs state `.prettierignore` is the mechanism to exclude files, and that Prettier also follows `.gitignore` from the run directory. Source: Prettier Ignoring Code, https://prettier.io/docs/ignore, accessed 2026-07-06.
* Why it matters: The new gate may be stricter than markdownlint for reasons unrelated to formatter authority, especially in repos with generated Markdown.
* Recommended action for Claude Code: Clarify that Prettier and markdownlint file-set parity depends on `.prettierignore`/`.gitignore` mirroring any markdownlint-only ignores, or explicitly state that Prettier intentionally gates a broader Markdown set.
* Suggested validation: Add an acceptance case for a caller with multiple globs and/or ignored generated Markdown, proving the intended file set.

#### SA-005: Proposed `tools/` location does not match current coverage/typecheck gates

* Severity: Medium
* Status: Confirmed
* Adversarial angle: The spec can claim the coherence tool “counts toward coverage” while the current coverage config excludes it.
* Spec reference: Component C lines 72 and 97; acceptance line 132.
* Finding: The spec proposes `tools/markdown_coherence/` and says the tool is imported by pytest so it counts toward coverage. Current coverage config measures only `src`, and basedpyright includes only `src` and `tests`. A `tools/` implementation may run in tests but will not be included in the coverage denominator unless config changes.
* Repository evidence: `pyproject.toml` has `[tool.coverage.run] source = ["src"]` and `[tool.basedpyright] include = ["src", "tests"]`. The spec also says `src/project_standards/` gains nothing.
* External research evidence: Not applicable.
* Why it matters: The planned safety gate may be less protected than the spec says, and regressions in the repo-local tool can escape type/coverage expectations.
* Recommended action for Claude Code: Decide whether the tool belongs under `src` as internal package code, or keep it under `tools/` and explicitly update coverage/typecheck/lint expectations. If it remains outside coverage, remove the “counts toward coverage” claim.
* Suggested validation: Add tests that fail if the coherence module is omitted from intended typecheck/coverage scope.

#### SA-006: Agent green-gate update names only `CLAUDE.md`, not the Codex-facing `AGENTS.md`

* Severity: Low
* Status: Confirmed
* Adversarial angle: A later Codex session can miss the new local gate even though Claude sees it.
* Spec reference: Component C line 97.
* Finding: The spec says to add the tool to the repo green-gate toolchain list in `CLAUDE.md`, but this repo also has `AGENTS.md` with a parallel “Keep the toolchain green” rule for Codex.
* Repository evidence: `CLAUDE.md` and `AGENTS.md` both contain green-gate instructions. The user-provided repo instructions identify `AGENTS.md` as the Codex-facing instruction file.
* External research evidence: Not applicable.
* Why it matters: The repo’s cross-harness instructions can diverge, especially because this audit is running under Codex.
* Recommended action for Claude Code: Add the new coherence gate to both `CLAUDE.md` and `AGENTS.md`, or explain why only Claude should carry it.
* Suggested validation: Search both files for the new command/gate after the spec correction is implemented.

### Missing specification considerations

* Blocking: Direct `push`/`pull_request` behavior for the new `prettier` input and step condition.
* Blocking: Safe conversion of newline-delimited `globs` into Prettier CLI arguments.
* Non-blocking: Explicit file-set parity policy between markdownlint ignores and Prettier ignores.
* Non-blocking: Complete v5 rollout checklist aligned to `meta/versioning.md`.
* Non-blocking: Whether `tools/markdown_coherence/` should be typechecked and included in coverage.
* Non-blocking: Codex-facing `AGENTS.md` update alongside `CLAUDE.md`.
* Non-blocking: A test that the reusable workflow’s own path filters include config files whose changes should exercise the new Prettier behavior, if direct PR/push coverage is intended.

### Ambiguities and decisions needed

* Ambiguity: Should the new Prettier step run on direct `push`/`pull_request` invocations of `.github/workflows/lint-markdown.yml`, or only when called by consumers?
* Why it matters: The current workflow has both roles; the spec’s condition only covers the reusable-call role.
* Recommended clarification: State the exact condition for direct and reusable invocations.
* Blocking or non-blocking: Blocking.

* Ambiguity: Are `inputs.globs` trusted shell text, newline-delimited data, or a list-like data contract?
* Why it matters: Prettier invocation safety and multi-glob correctness depend on this.
* Recommended clarification: Define parsing and quoting behavior.
* Blocking or non-blocking: Blocking.

* Ambiguity: Should Prettier check exactly the markdownlint file set, or every Markdown file matched by `globs` except `.prettierignore`/`.gitignore`?
* Why it matters: Consumers with generated Markdown need predictable migration guidance.
* Recommended clarification: Document the intended scope and required ignore-file mirroring.
* Blocking or non-blocking: Non-blocking.

### Internet research performed

* Source name: GitHub Docs — Reuse workflows
* URL: https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows
* Access date: 2026-07-06
* What it was used to verify: `workflow_call` inputs and caller-provided typed values.
* Relevant conclusion: Reusable workflows define inputs under `workflow_call`, and caller input types must match boolean/number/string.

* Source name: GitHub Docs — Workflow syntax for GitHub Actions
* URL: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onworkflow_callinputs
* Access date: 2026-07-06
* What it was used to verify: `on.workflow_call.inputs` defaults and `run` shell behavior.
* Relevant conclusion: `workflow_call` inputs have typed defaults for called workflows; multi-line `run` commands execute in the shell.

* Source name: Prettier CLI documentation
* URL: https://prettier.io/docs/cli
* Access date: 2026-07-06
* What it was used to verify: CLI argument/glob behavior and quoting guidance.
* Relevant conclusion: Prettier accepts file/dir/glob arguments and recommends quoting globs so Prettier, not the shell, expands them.

* Source name: Prettier Ignoring Code documentation
* URL: https://prettier.io/docs/ignore
* Access date: 2026-07-06
* What it was used to verify: `.prettierignore` and `.gitignore` behavior.
* Relevant conclusion: `.prettierignore` is the explicit mechanism for excluding files; Prettier also follows `.gitignore` from the run directory.

* Source name: npm Docs — npx
* URL: https://docs.npmjs.com/cli/v10/commands/npx/
* Access date: 2026-07-06
* What it was used to verify: `npx --yes` behavior and argument parsing.
* Relevant conclusion: `--yes` suppresses the install prompt; npx flags must precede positional arguments.

* Source name: markdownlint-cli2-action `action.yml` at `v23`
* URL: https://raw.githubusercontent.com/DavidAnson/markdownlint-cli2-action/v23/action.yml
* Access date: 2026-07-06
* What it was used to verify: action inputs, default glob, and Node runtime.
* Relevant conclusion: `globs` defaults to `*.{md,markdown}`, `config` defaults empty, and the action runs using `node24`.

* Source name: markdownlint-cli2-action `package.json` at `v23`
* URL: https://raw.githubusercontent.com/DavidAnson/markdownlint-cli2-action/v23/package.json
* Access date: 2026-07-06
* What it was used to verify: bundled `markdownlint-cli2` version.
* Relevant conclusion: `markdownlint-cli2-action` `23.2.0` depends on `markdownlint-cli2` `0.22.1`.

* Source name: actions/setup-node `v4` metadata
* URL: https://raw.githubusercontent.com/actions/setup-node/v4/action.yml
* Access date: 2026-07-06
* What it was used to verify: Node setup and cache inputs.
* Relevant conclusion: `setup-node@v4` supports `node-version` and optional package-manager caching inputs.

### Items Claude Code should verify before correcting the specification

* Verify actual GitHub Actions expression behavior for `inputs.prettier` on direct `push` and `pull_request` triggers.
* Verify the desired shell-safe implementation for newline-delimited `inputs.globs`.
* Verify whether `prettier --check` should use only `inputs.globs` or additionally honor an ignore path/policy aligned with markdownlint.
* Verify whether `tools/markdown_coherence/` should be added to coverage/typecheck config or relocated.
* Verify all v5-required reference updates against `meta/versioning.md`.
* Verify whether the linked issue #3 is publicly accessible or whether the spec should avoid depending on unverifiable issue context.

### Suggested corrections for Claude Code’s specification

* Define the Prettier step condition for both direct and reusable workflow invocations; require a test for direct-trigger default behavior.
* Specify safe glob handling for Prettier, including newline splitting, quoting, empty fallback, and multi-glob tests.
* Add a file-set parity section explaining how `.markdownlint-cli2.jsonc`, `.prettierignore`, and `.gitignore` interact.
* Expand rollout requirements to include `pyproject.toml`, `uv.lock`, README, all relevant `standards/*/adopt.md` snippets, Markdown Tooling status/contract banners, and workflow defaults/examples required by `meta/versioning.md`.
* Resolve the `tools/` versus coverage/typecheck contradiction.
* Update both `CLAUDE.md` and `AGENTS.md` if the coherence gate becomes part of the repo-local green gate.

### Read-only validation performed

* `pwd`, `git status --short`, `git branch --show-current`, `git log --oneline -n 10`, `git diff --stat`: confirmed repository root, clean working tree, branch `testing`, recent Spec B commit, and no local diff.
* `sed -n` / `nl -ba` on the spec: inventoried requirements, scope, acceptance criteria, and testing claims.
* `rg --files` and hidden-file discovery: identified workflows, configs, bundle artifacts, docs, tests, and handoff files relevant to the spec.
* Inspected `.github/workflows/lint-markdown.yml`, `.github/workflows/format.yml`, `.github/workflows/check.yml`: verified current markdownlint-only reusable gate, repo-local Prettier gate, and Python check gate.
* Inspected `package.json`, `pyproject.toml`, `src/project_standards/schemas/registry.json`, `.project-standards.yml`, and `src/project_standards/adopt/engine.py`: verified current Prettier pin, Python package version, contract registry, dogfood config, and `major_ref()` behavior.
* Inspected `.markdownlint.json`, `.prettierrc.json`, `.markdownlint-cli2.jsonc`, `.prettierignore`, and bundle copies: verified current config values, ignored paths, and shipped artifact shape.
* Inspected `standards/markdown-tooling/README.md`, `standards/markdown-tooling/adopt.md`, `meta/versioning.md`, `CLAUDE.md`, and `AGENTS.md`: verified current docs contradict or constrain parts of the spec.
* Inspected relevant tests including `tests/test_markdownlint_config.py`, `tests/test_adopt_dogfood.py`, and workflow/package tests: verified existing guard patterns and gaps.
* Used external official docs/source URLs listed above to verify GitHub Actions, Prettier, npx, setup-node, and markdownlint action assumptions.

### Recommended planning/implementation validation

* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest && uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`
* Run only after implementation: repo Prettier check through `npm ci && npx prettier --check .`
* Run only after implementation: markdownlint workflow-equivalent check for the repo’s Markdown globs.
* Run only after implementation: the new coherence gate command, including tampered-config negative cases.
* Run only after implementation: workflow-shape tests proving `prettier: false` skips the step and all other direct/called cases run it.

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-07-06-markdown-tooling-formatter-authority-design.md`
* Audit round: 1
* Open issue IDs: SA-001, SA-002, SA-003, SA-004, SA-005, SA-006
* Resolved issue IDs:
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: direct-trigger Prettier behavior, safe glob handling, file-set parity, complete v5 rollout surface, and coherence-tool placement versus coverage/typecheck gates.