### Executive summary

The implementation plan needs major correction before Claude Code executes it. Most repository touchpoints and sequencing are grounded in the current repo, but one planned TDD test is structurally wrong and will not pass as written because it misunderstands how `validate-frontmatter` treats an empty `include:` list. Internet research was required for stale external assumptions around GitHub Actions, `setup-uv`, Python `argparse`, entry points, and packaging behavior.

### Verdict

Needs major correction before execution

### Audit loop status

* Audit type: First audit
* Plan path: `/home/chris/projects/project-standards/docs/superpowers/plans/2026-07-07-cli-documentation-standard.md`
* Significant findings remaining: Yes
* Blocking issue count: 1
* Non-blocking issue count: 3

### What the plan gets right

* Correctly identifies the current research draft path: `standards/cli-framework/cli-documentation-standards.md`.
* Correctly accounts for seven `[project.scripts]` console scripts in `pyproject.toml`.
* Correctly treats registry plus bundle registration as atomic because `cli.py` enforces registry/bundle parity.
* Correctly includes `docs/usage.md` in frontmatter validation rather than relying on a vacuous full-repo pass.
* Correctly recognizes that the two raw-`sys.argv` sync commands currently lack ordinary argparse `--help` behavior.

### Adversarial review performed

Performed claim inventory, falsification, blast-radius, failure-mode, validation attack, external-assumption, and maintainability passes. Strongest assumptions tested: validation counts and include/exclude behavior, current console-script inventory, registry/bundle parity, version-contract tests, installed-wrapper tests, generated workflow pins, handoff/doc surfaces, release-boundary claims, and stale external GitHub Action references.

Could not run `uv`, pytest, Prettier, markdownlint, or build commands because those may write caches, artifacts, or temporary build state. Those are listed under recommended implementation validation instead.

### Blocking issues

#### CR-001: Contract-version tests use `include: []`, which validates the whole repo instead of nothing

* Severity: High
* Status: Confirmed
* Adversarial angle: Validation false positive / executable plan failure.
* Plan reference: Task 10, `tests/test_registry_cli_documentation.py`, `_CONFIG_KNOWN` and `test_known_version_accepted_silently`.
* Finding: The proposed test assumes `include: []` isolates the validator from the corpus. In this repo, an empty include list is falsy, so `collect_paths()` falls back to `_default_corpus()` and validates all Markdown under the working directory. The known-version test can fail because unrelated repo files are included with no excludes.
* Repository evidence: Plan lines 589-615 define `include: []` and expect return code `0`. `src/project_standards/validate_frontmatter.py` uses `elif include_patterns:` and falls through to `_default_corpus()` when the include list is empty. `.project-standards.yml` currently needs substantial excludes for README, agent files, handoff docs, templates, draft areas, and examples.
* External research evidence: Not applicable.
* Why it matters: Task 10’s TDD loop cannot reliably turn green as written. It tests unrelated Markdown validity instead of the new `cli_documentation.version` gate, so Claude Code may chase false failures or weaken validation to satisfy a bad test.
* Recommended action for Claude Code: Change the fixture so the version-gate tests are corpus-isolated. Use a non-empty no-match include pattern, an explicit temporary valid Markdown file, or a `--glob` no-match invocation that still exercises config loading before path collection. Keep the unknown-version and non-string-version checks proving exit `2`.
* Suggested validation: After correcting the fixture, run `uv run pytest tests/test_registry_cli_documentation.py -v` and confirm the known-version test exits `0` without validating the repo corpus.

### Non-blocking issues

#### CR-002: The shipped CI template uses stale, repo-inconsistent action refs

* Severity: Medium
* Status: Confirmed
* Adversarial angle: External dependency freshness / supply-chain hardening.
* Plan reference: Task 3, `templates/cli-docs-check.yml`, lines 187-188.
* Finding: The template uses `actions/checkout@v4` and `astral-sh/setup-uv@v5`. Current repo workflows use `actions/checkout@v6` and a SHA-pinned `astral-sh/setup-uv` with a trailing version comment. The repo also has a durable bug record stating that `setup-uv` moving tags caused CI failures and that third-party actions should be SHA-pinned.
* Repository evidence: `.github/workflows/check.yml` uses `actions/checkout@v6` and `astral-sh/setup-uv@fac544c07dec837d0ccb6301d7b5580bf5edae39 # v8.2.0`. `docs/handoff/bugs/001-setup-uv-v8-tag-withdrawn.md` says to SHA-pin third-party actions and re-verify action refs.
* External research evidence: `actions/checkout` README currently documents newer `v7`, with `v6` improving credential handling versus older behavior. `setup-uv` README currently demonstrates a commit SHA pin with a `# v8.3.0` comment, not `@v5`. Access date: 2026-07-07.
* Why it matters: This plan would publish a new consumer-facing workflow template that is already behind the repo’s own hardening posture. Even if `@v5` still resolves, the template teaches weaker supply-chain practice than the repo’s standards now require.
* Recommended action for Claude Code: Update the template to match current repo policy: use the current approved checkout major and SHA-pin `setup-uv` with a version comment and explicit `version:` input, or intentionally document why this standard’s template differs.
* Suggested validation: Verify action refs with `git ls-remote` or GitHub release metadata before committing the template, then run the template through YAML parsing and the repo’s markdown/coherence checks.

#### CR-003: Task 9 modifies `README.md` but does not stage it

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Sequencing / dirty-worktree failure.
* Plan reference: Task 9, Step 1 and Step 3.
* Finding: Task 9 tells Claude Code to add `standards/cli-documentation/examples/usage.example.md` to the `related:` list in `standards/cli-documentation/README.md`, but the commit command stages only `standards/cli-documentation/examples/`.
* Repository evidence: Plan line 537 modifies `standards/cli-documentation/README.md`; line 546 stages only `standards/cli-documentation/examples/`. Later commit commands do not explicitly stage `standards/cli-documentation/README.md`.
* External research evidence: Not applicable.
* Why it matters: Following the plan literally leaves a modified README unstaged after Task 9. That breaks the plan’s “commit after every task” discipline and can leave the final branch dirty or omit the deferred related-link update.
* Recommended action for Claude Code: Stage both the example and the README in Task 9, or move the README related-list update into a later task that stages it explicitly.
* Suggested validation: Run `git status --short` after Task 9’s commit and confirm no uncommitted README change remains.

#### CR-004: The `--version` tests do not prove the stated `<prog> <version>` contract for six wrappers

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Validation attack / weak assertion.
* Plan reference: Task 7 version tests and Task 11 installed-wrapper smoke tests.
* Finding: The plan states every console script prints `<prog> <version>`, but most tests only assert that the package version appears, or that stdout contains any digit. The `prog` parameter in `test_argparse_mains_version_flag` is unused, the sync-main test sets `sys.argv` to module names with underscores, and the installed-wrapper smoke test only checks `any(ch.isdigit() for ch in proc.stdout)`.
* Repository evidence: Plan lines 355-379 do not assert exact `prog`; lines 840-844 accept any digit in stdout. `pyproject.toml` defines hyphenated console-script names, and the two sync modules are raw-`sys.argv` programs whose real wrapper names differ from module names.
* External research evidence: PyPA entry point docs state the entry-point name is the command launched after install. Python `argparse` docs state default `prog` derives from invocation context unless pinned. Access date: 2026-07-07.
* Why it matters: The core goal includes a user-facing version contract. A wrapper could print the wrong command name, a module name, or incidental output with digits and still pass the proposed smoke test.
* Recommended action for Claude Code: Strengthen the installed-wrapper test to assert exact stdout for every script: `<script-name> <package_version()>`. For in-process tests, either set `sys.argv[0]` to the console-script name or assert exact output only in the installed-wrapper test.
* Suggested validation: After implementation, run the installed-wrapper smoke test and manually spot-check `validate-frontmatter --version`, `sync-vscode-colors --version`, and `project-standards --version`.

### Missing considerations

* Blocking: The test fixture for `cli_documentation.version` must avoid the default Markdown corpus. This is CR-001.
* Non-blocking: The workflow template should follow the repo’s action-pin hardening and current checkout/setup-uv posture. This is CR-002.
* Non-blocking: Task commits should include a `git status --short` check after tasks that modify multiple surfaces.
* Non-blocking: The release boundary should explicitly say `pyproject.toml` and `uv.lock` version bumps happen only in the separate release decision, per `meta/versioning.md`, so `--version` returning `4.2.0` on `testing` is expected until release.
* Non-blocking: The option/exit-code parity pass is manual; the plan should require preserving the captures or checklist evidence somewhere durable enough for review.

### Internet research performed

* Source name: Python 3.14 `argparse` documentation  
  URL: https://docs.python.org/3.14/library/argparse.html  
  Access date: 2026-07-07  
  What it was used to verify: `ArgumentParser` color default, `prog` behavior, and generated help assumptions.  
  Relevant conclusion: Python 3.14 adds `color=True` by default and `prog` depends on invocation unless explicitly set.

* Source name: Python Packaging User Guide, Entry points specification  
  URL: https://packaging.python.org/en/latest/specifications/entry-points/  
  Access date: 2026-07-07  
  What it was used to verify: Console-script wrapper semantics.  
  Relevant conclusion: For console scripts, the entry-point name is the shell command, and installers set up wrappers in the scripts directory.

* Source name: Setuptools data files documentation  
  URL: https://setuptools.pypa.io/en/latest/userguide/datafiles.html  
  Access date: 2026-07-07  
  What it was used to verify: Man-page/data-files packaging assumptions.  
  Relevant conclusion: Non-package data files are not a reliable runtime retrieval mechanism; the plan’s SHOULD-if-practical man-page posture is reasonable.

* Source name: `astral-sh/setup-uv` README  
  URL: https://raw.githubusercontent.com/astral-sh/setup-uv/main/README.md  
  Access date: 2026-07-07  
  What it was used to verify: Current recommended setup-uv action reference and behavior.  
  Relevant conclusion: Current docs demonstrate a commit-SHA pin with a version comment and state that setup-uv only installs uv; project install/sync remains a separate step.

* Source name: `actions/checkout` README  
  URL: https://raw.githubusercontent.com/actions/checkout/main/README.md  
  Access date: 2026-07-07  
  What it was used to verify: Current checkout major and security-relevant differences.  
  Relevant conclusion: `v7` is current upstream, and `v6` improved credential storage compared with older behavior; the plan’s `@v4` template is stale relative to repo practice.

### Items Claude Code should verify before correcting the plan

* Confirm `validate_frontmatter.collect_paths()` still treats empty `include:` as “use default corpus.”
* Verify the current approved `actions/checkout` and `setup-uv` pins for consumer-facing templates.
* Verify whether `setup-uv@v5` still resolves if the plan intentionally wants a moving tag, then document why it rejects repo policy if kept.
* Decide whether `docs/usage.md` should record exact `--version` output before release or avoid concrete version output until the release commit.
* Verify all staged-file lists after tasks that modify one file but stage a sibling directory.

### Suggested corrections for Claude Code's plan

* Fix Task 10’s `_CONFIG_KNOWN` fixture so known-version tests do not validate the whole repository.
* Update `cli-docs-check.yml` to current action pins and setup-uv hardening.
* Add `standards/cli-documentation/README.md` to Task 9’s `git add`, or move that README edit to a task that stages it.
* Strengthen `--version` tests to assert exact `<script-name> <package_version()>` output for every installed wrapper.
* Add explicit final `git status --short` checks after Task 9, Task 12, and Task 13.
* Clarify the release boundary for `pyproject.toml` / `uv.lock` version bumps.

### Read-only validation performed

* `pwd`: confirmed repository root is `/home/chris/projects/project-standards`.
* `git status --short`: confirmed the working tree is clean.
* `git branch --show-current`: confirmed branch is `testing`.
* `git log --oneline -n 10`: confirmed the plan and approved spec are recent commits on this branch.
* `sed -n` on the plan: inspected all tasks and code snippets.
* `rg --files`: inventoried current repo files and verified the draft, spec, tests, workflows, bundles, and handoff files exist.
* Inspected `.project-standards.yml`: confirmed current interim `standards/cli-framework/**` exclude and managed-doc include/exclude behavior.
* Inspected `pyproject.toml`: confirmed Python 3.14 requirement and seven console scripts.
* Inspected `src/project_standards/cli.py`, `registry.py`, `validate_frontmatter.py`, adopt manifest code, sync scripts, and spec CLI: verified current implementation assumptions.
* Inspected related tests: confirmed hardcoded available-standards count, dogfood map, packaging checks, and CLI tests that plan must update.
* `rg -n "setup-uv@|actions/checkout@"`: found current repo action-pin practice and the plan’s stale template refs.
* Inspected `docs/handoff/bugs/001-setup-uv-v8-tag-withdrawn.md`: confirmed repo-local lesson to SHA-pin third-party actions.
* `git diff --stat` and `git diff --check`: confirmed no local modifications or whitespace issues in the current working tree.

### Recommended implementation validation

* Run only after implementation: `uv run pytest tests/test_registry_cli_documentation.py -v`
* Run only after implementation: `uv run pytest tests/test_version_flag.py tests/test_usage_doc_inventory.py tests/test_installed_wrappers.py -v`
* Run only after implementation: `uv run coverage run -m pytest && uv run coverage report`
* Run only after implementation: `uv run ruff format --check . && uv run ruff check . && uv run basedpyright`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run pytest tests/coherence`
* Run only after implementation: `npx prettier --check . && npx markdownlint-cli2`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml && uv run project-standards validate`
* Run only after implementation: `git status --short` after each task commit, especially Tasks 9, 12, and 13.
* Run only after implementation: verify action refs for any shipped workflow template before committing.

### Final recommendation

Claude Code should revise the plan using the findings above

### Review ledger for next loop

* Plan path: `/home/chris/projects/project-standards/docs/superpowers/plans/2026-07-07-cli-documentation-standard.md`
* Audit round: 1
* Open issue IDs: CR-001, CR-002, CR-003, CR-004
* Resolved issue IDs: None
* Superseded issue IDs: None
* Significant findings remaining: Yes
* Next audit should focus on: corrected version-gate test isolation, updated workflow action pins, Task 9 staging, and exact `--version` assertions.

