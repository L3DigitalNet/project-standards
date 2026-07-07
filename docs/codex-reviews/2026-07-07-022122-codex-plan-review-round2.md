### Executive summary

Claude Code’s revisions resolved all four prior findings. The plan now isolates the `cli_documentation.version` tests, uses the repo’s current workflow action posture, stages the Task 9 README edit, and strengthens installed-wrapper `--version` assertions.

One new non-blocking validation issue remains: the parity-pass evidence says “17 command entries,” while the plan requires 18 documented entries when the `spec` group overview is counted. New internet research was limited to verifying current external action and uv assumptions.

### Verdict

Needs minor correction before execution

### Audit loop status

* Audit type: Follow-up audit
* Plan path: `/home/chris/projects/project-standards/docs/superpowers/plans/2026-07-07-cli-documentation-standard.md`
* Prior audit issue count: 4
* Resolved issue count: 4
* Still open issue count: 0
* Partially resolved issue count: 0
* New issue count: 1
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

Retested the four prior corrections against the current plan and repository evidence: `validate-frontmatter` include fallback behavior, registry-gate ordering, workflow action pins, Task 9 staging, and installed-wrapper `--version` assertions.

Also re-attacked command inventory counts, usage-doc parity claims, raw-`sys.argv` script help/version behavior, registry/bundle atomicity, config validation flow, release-boundary claims, and CI-template external assumptions. I did not run tests, build commands, formatters, package installation, or Prettier/markdownlint because they may write caches or artifacts.

### Prior findings status

#### CR-001: Contract-version tests use `include: []`, which validates the whole repo instead of nothing

* Previous severity: High
* Current status: Resolved
* Evidence: Plan lines 590-604 now use a non-empty no-match include pattern and explicitly document that an empty include falls back to `_default_corpus()`. Repository evidence confirms `collect_paths()` only uses config includes when `include_patterns` is truthy and otherwise falls back to `_default_corpus()` at `src/project_standards/validate_frontmatter.py:416-427`. The registry/version gates run before path collection at `validate_frontmatter.py:747-827`.
* Remaining action for Claude Code: None for this issue.

#### CR-002: The shipped CI template uses stale, repo-inconsistent action refs

* Previous severity: Medium
* Current status: Resolved
* Evidence: Plan lines 187-190 now use `actions/checkout@v6` and SHA-pinned `astral-sh/setup-uv@fac544c07dec837d0ccb6301d7b5580bf5edae39 # v8.2.0`. Current repo workflows use the same pattern in `.github/workflows/check.yml`, `coherence.yml`, `validate-specs.yml`, and `validate-markdown-frontmatter.yml`.
* Remaining action for Claude Code: None for this issue. The upstream docs currently show newer `checkout@v7` and setup-uv `v8.3.0`, but the plan now matches current repo policy.

#### CR-003: Task 9 modifies `README.md` but does not stage it

* Previous severity: Medium
* Current status: Resolved
* Evidence: Plan lines 537-546 still modify `standards/cli-documentation/README.md`, and the Task 9 commit command now stages both `standards/cli-documentation/examples/` and `standards/cli-documentation/README.md`, followed by a clean-tree check at lines 546-548.
* Remaining action for Claude Code: None for this issue.

#### CR-004: The `--version` tests do not prove the stated `<prog> <version>` contract for six wrappers

* Previous severity: Medium
* Current status: Resolved
* Evidence: Plan lines 847-856 now assert exact installed-wrapper output for every `[project.scripts]` key: `f"{script} {package_version()}"`. `pyproject.toml` currently defines seven scripts at lines 14-21. The weaker in-process tests are now explicitly scoped to proving flag existence, with exact contract asserted only against installed wrappers.
* Remaining action for Claude Code: None for this issue.

### New blocking issues

None found.

### New non-blocking issues

#### CR-NEW-001: Usage-doc parity evidence undercounts the required command entries

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Validation attack / false sense of parity coverage.
* Plan reference: Task 8 lines 488-498 and commit trailer at lines 520-522; Task 11 inventory test at lines 775-791.
* Finding: The plan requires documenting 18 entries, but the parity-pass artifact says “all 17 command entries.” The required `docs/usage.md` structure includes 4 top-level leaves, the `spec` group overview, 6 `spec` verbs, and 7 standalone console scripts. Task 11’s inventory test also explicitly requires the `spec` overview heading plus every spec verb. The plan’s parity trailer likely counts only 10 leaves + 7 standalone scripts and omits the `spec` group overview from the durable option/exit-code parity evidence.
* Repository evidence: `pyproject.toml` defines seven console scripts. `src/project_standards/specs/cli.py` defines six spec verbs. The plan itself states the CLI surface is “10 leaf commands plus the `spec` group overview; seven `[project.scripts]` console scripts” at line 18. Task 8 requires the `spec` overview heading at line 491, and Task 11 asserts it at line 789.
* External research evidence: Not applicable.
* Why it matters: The usage-doc heading test can pass while the manual parity evidence omits the `spec` group overview’s help, options, and exit-status behavior. That weakens the plan’s main drift-prevention claim for `docs/usage.md`.
* Recommended action for Claude Code: Change the Task 8 parity text and commit trailer to account for 18 entries, or explicitly split it as “17 command leaves checked, plus `spec` group overview checked.” Add a required commit-body line for `parity: spec — options+exit codes vs --help: OK`.
* Suggested validation: After implementation, inspect the Task 8 commit body and `docs/usage.md` to confirm parity evidence covers `validate`, `fix`, `adopt`, `list`, `spec`, all six `spec` verbs, and all seven standalone scripts.

### Regressions

None found.

### Internet research performed

* Source name: `astral-sh/setup-uv` README  
  URL: https://raw.githubusercontent.com/astral-sh/setup-uv/main/README.md  
  Access date: 2026-07-07  
  What it was used to verify: Current setup-uv pinning examples, behavior, and whether setup-uv installs projects automatically.  
  Relevant conclusion: Current docs demonstrate SHA pinning with a version comment, and state setup-uv only installs uv; project install/sync remains a separate step.

* Source name: `actions/checkout` README  
  URL: https://raw.githubusercontent.com/actions/checkout/main/README.md  
  Access date: 2026-07-07  
  What it was used to verify: Current checkout major and security-relevant behavior.  
  Relevant conclusion: Upstream currently documents `v7`; the plan’s `v6` is still consistent with this repo’s current pinned workflow posture.

* Source name: uv CLI reference  
  URL: https://docs.astral.sh/uv/reference/cli/  
  Access date: 2026-07-07  
  What it was used to verify: `uv pip install --python` semantics for the CI template and installed-wrapper smoke test.  
  Relevant conclusion: `--python` targets a Python interpreter/request; local `uv help python` also confirms an install directory can be a supported request format.

### Read-only validation performed

* `pwd`: confirmed repository root is `/home/chris/projects/project-standards`.
* `git status --short`: confirmed the working tree is clean.
* `git branch --show-current`: confirmed branch is `testing`.
* `git log --oneline -n 10` and `git show --stat --oneline -1`: confirmed the latest commit is the round-1 plan correction.
* `sed -n` and `nl -ba` on the plan: re-read current Task 1-13 content and line-numbered the corrected areas.
* `rg --files`: inventoried repository files and confirmed the current draft, source, tests, workflows, and handoff/doc surfaces.
* Inspected `.project-standards.yml`: confirmed current include/exclude shape and the existing `cli-framework` interim exclude.
* Inspected `pyproject.toml`: confirmed Python 3.14 requirement and seven console scripts.
* Inspected `validate_frontmatter.py`, `cli.py`, `registry.py`, sync scripts, adopt manifest code, and related tests: verified current implementation assumptions and prior-finding fixes.
* `rg -n "setup-uv@|actions/checkout@"`: confirmed current repo workflow action-pin practice.
* `uv --version`, `uv help python`, and `uv help pip install`: inspected local uv behavior without installing or writing artifacts.
* `git diff --stat` and `git diff --check`: confirmed no local modifications or whitespace issues.

### Recommended implementation validation

* Run only after implementation: `uv run pytest tests/test_registry_cli_documentation.py -v`
* Run only after implementation: `uv run pytest tests/test_version_flag.py tests/test_usage_doc_inventory.py tests/test_installed_wrappers.py -v`
* Run only after implementation: inspect the Task 8 commit body and confirm parity evidence covers 18 entries, including the `spec` group overview.
* Run only after implementation: `uv run coverage run -m pytest && uv run coverage report`
* Run only after implementation: `uv run ruff format --check . && uv run ruff check . && uv run basedpyright`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run pytest tests/coherence`
* Run only after implementation: `npx prettier --check . && npx markdownlint-cli2`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml && uv run project-standards validate`
* Run only after implementation: `git status --short` after Tasks 9, 12, and 13.

### Final recommendation

Claude Code should revise the plan using the findings above

### Review ledger for next loop

* Plan path: `/home/chris/projects/project-standards/docs/superpowers/plans/2026-07-07-cli-documentation-standard.md`
* Audit round: 2
* Open issue IDs: CR-NEW-001
* Resolved issue IDs: CR-001, CR-002, CR-003, CR-004
* Superseded issue IDs: None
* Significant findings remaining: Yes
* Next audit should focus on: Task 8 parity-pass command-entry count and explicit coverage of the `spec` group overview.