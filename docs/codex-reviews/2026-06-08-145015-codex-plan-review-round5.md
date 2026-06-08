### Executive summary

Claude Code’s latest corrections resolved the registry/bundle runtime-drift issue and mostly fixed the release/changelog/handoff sequencing issue. Significant findings remain because the planned `project-standards validate ...` dispatcher will not forward validator flags such as `--config`, and the plan’s `pyproject.toml` script replacement no longer matches the current dirty worktree: it would drop an in-progress `sync-vscode-colors` console script if followed literally.

New internet research was required for the `argparse` delegation assumption.

### Verdict

Needs major correction before execution

### Audit loop status

* Audit type: Follow-up audit
* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-06-08-adopt-cli.md
* Prior audit issue count: 9
* Resolved issue count: 8
* Still open issue count: 0
* Partially resolved issue count: 1
* New issue count: 2
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

Re-read the revised plan, current design spec, git status/history, dirty worktree diffs, `pyproject.toml`, `uv.lock`, CI workflow, registry reader/data, validator CLI entry point, handoff docs, release contract, changelog, tags, and prior issue ledger.

Retested prior fixes for registry/bundle parity, `list`/`adopt` drift guarding, release commit sequencing, unreleased handoff state, `uv.lock` release handling, ADR exclusion validation, symlink parent safety, fragment reporting, and no-traceback error boundaries. Attacked new assumptions around `argparse.REMAINDER` delegation and current `[project.scripts]` edit safety.

No tests, builds, `uv sync`, `uv lock`, formatters, package installs, generators, or tag commands were run because this audit is read-only and those commands may write lockfiles, caches, environments, build artifacts, or git state.

### Prior findings status

#### CR-001: Recoverable I/O failures can still escape as tracebacks

* Previous severity: High
* Current status: Resolved
* Evidence: The plan still maps source reads, fragment reads, mkdir/mkstemp/write/replace failures, and source read failures through `WriteError`, with failure-injection coverage.
* Remaining action for Claude Code: Preserve those error boundaries during implementation.

#### CR-002: Adoption validation test is not executable as written

* Previous severity: High
* Current status: Resolved
* Evidence: D1 still validates a real managed `docs/guide.md` from the shipped valid example using `validate_frontmatter.main(["--config", ".project-standards.yml"])` and asserts non-vacuous output.
* Remaining action for Claude Code: Preserve the real managed fixture.

#### CR-003: Invalid-manifest and list error paths do not satisfy the no-traceback contract

* Previous severity: High
* Current status: Resolved
* Evidence: `load_manifest()` validates non-string manifest fields before constructing `Artifact`, and `list`/`adopt` run inside clean `RegistryError` / `AdoptError` boundaries.
* Remaining action for Claude Code: Keep `list` and `adopt` under the clean CLI boundary.

#### CR-004: `list --json` omits the spec’s stable `contract_version` field

* Previous severity: Medium
* Current status: Resolved
* Evidence: Lines 1467-1525 add `_assert_registry_bundle_parity()`, emit `contract_version`, and call the parity guard before both `list` and `adopt`.
* Remaining action for Claude Code: Add direct failure-injection tests for registry-only and bundle-only drift if possible, but the runtime behavior is now planned.

#### CR-005: Fragment reporting cannot represent multiple fragments for one target

* Previous severity: Medium
* Current status: Resolved
* Evidence: `Report.fragments` remains `dict[str, list[str]]`, and the multi-fragment formatting test is still planned.
* Remaining action for Claude Code: None.

#### CR-NEW-001: Destination safety resolves away symlinks before checking them

* Previous severity: High
* Current status: Resolved
* Evidence: The plan still keeps the leaf unresolved, checks symlinked leaves and ancestors, and includes the parent-symlink escape regression.
* Remaining action for Claude Code: Preserve both symlink tests.

#### CR-NEW-002: Version bump omits the lockfile update needed by this uv project

* Previous severity: High
* Current status: Resolved
* Evidence: C2 now explicitly avoids the version bump, while E3 groups `pyproject.toml`, `uv.lock`, and the dated changelog in the release commit with `uv lock && uv lock --check`.
* Remaining action for Claude Code: Keep the release commit atomic.

#### CR-NEW-003: ADR existing-config safety test can pass with only comment-level exclusion guidance

* Previous severity: Medium
* Current status: Resolved
* Evidence: The ADR fragment reports the required `**/*.template.md` exclusion, and D1 includes an existing-config validation test that applies it and succeeds.
* Remaining action for Claude Code: Preserve that validation test.

#### CR-NEW-004: Release-state steps conflict with the repo’s release contract

* Previous severity: Medium
* Current status: Partially resolved
* Evidence: The main sequencing problem is fixed: C2 defers the version bump, E2 adds changelog content under `Unreleased` and marks handoff state as implemented but not released, and E3 requires user approval before version bump/tag/deployed-state updates. Residual issue: E2’s file list still says `docs/handoff/deployed.md` will be modified at lines 1955-1957, while line 1981 says not to touch `deployed.md`.
* Remaining action for Claude Code: Remove `docs/handoff/deployed.md` from E2’s modified-file list and keep deployed-state changes only in E3 after tags exist.

### New blocking issues

#### CR-NEW-005: `project-standards validate --config ...` will fail before delegation

* Severity: High
* Status: Confirmed
* Adversarial angle: CLI delegation and validation false positive.
* Plan reference: Lines 1548-1554.
* Finding: The plan adds `p_validate.add_argument("rest", nargs=argparse.REMAINDER)` and then calls `parser.parse_args(argv)`. With this shape, `main(["validate", "--config", ".project-standards.yml"])` is rejected by the outer parser as an unrecognized argument before `validate_frontmatter.main()` is called. The plan has no test for `project-standards validate --config ...`.
* Repository evidence: `validate_frontmatter.main()` defines `--config`, `--schema`, `--glob`, `--quiet`, and other validator flags. Repo docs and CI repeatedly use `validate-frontmatter --config .project-standards.yml`. A read-only local Python reproduction of the planned parser exited 2 for `["validate", "--config", "x"]`.
* External research evidence: Python 3.14 argparse docs say `parse_args()` exits on invalid/unrecognized arguments, and `parse_known_args()` is the documented mechanism for forwarding unrecognized arguments to another parser or program. Source: https://docs.python.org/3/library/argparse.html, accessed 2026-06-08.
* Why it matters: A required advertised subcommand, `project-standards validate ...`, would be unusable for the normal validator invocation shape. The standalone alias still works, so tests that only smoke `validate-frontmatter` can pass while the new unified CLI is broken.
* Recommended action for Claude Code: Revise the dispatcher so `validate` delegates all trailing args without requiring a `--` separator. The simplest safe shape is early command dispatch: if the selected command is `validate`, call `validate_frontmatter.main(argv_after_validate)` before the adopt/list parser tries to parse validator flags. Alternatively, use a carefully tested `parse_known_args()` approach.
* Suggested validation: Add tests for `main(["validate", "--config", ".project-standards.yml", "--quiet"])` and `project-standards validate --help` delegation. Update the C2 smoke test to exercise `uv run project-standards validate --help` or a real `--config` invocation, not only the legacy `validate-frontmatter` alias.

#### CR-NEW-006: C2 would overwrite an in-progress console script in `pyproject.toml`

* Severity: High
* Status: Confirmed
* Adversarial angle: Dirty-worktree safety and current-repo mismatch.
* Plan reference: Lines 1589-1601.
* Finding: C2 says to replace the `[project.scripts]` block with only `project-standards` and `validate-frontmatter`. The current worktree already has an uncommitted `sync-vscode-colors = "project_standards.sync_vscode_colors:main"` entry, plus matching untracked source and test files. Executing the plan literally would remove that in-progress script entry.
* Repository evidence: `git status --short` shows modified `pyproject.toml` and untracked `src/project_standards/sync_vscode_colors.py` / `tests/test_sync_vscode_colors.py`. `git diff -- pyproject.toml` shows the only pyproject change is the added `sync-vscode-colors` script.
* External research evidence: Not applicable.
* Why it matters: The repo instructions require understanding local work before editing. Dropping this entry would damage unrelated in-progress work and make the untracked script less accessible/package-consistent.
* Recommended action for Claude Code: Revise C2 to preserve all existing `[project.scripts]` entries and add only `project-standards = "project_standards.cli:main"`. Add an explicit pre-edit check for dirty `pyproject.toml` and require Claude to merge with current contents rather than replacing the block.
* Suggested validation: Before editing, inspect `git diff -- pyproject.toml`. After editing, verify `[project.scripts]` contains `project-standards`, `validate-frontmatter`, and any pre-existing entries such as `sync-vscode-colors`.

### New non-blocking issues

None found.

### Regressions

None found.

### Internet research performed

* Source name: Python `argparse` documentation
* URL: https://docs.python.org/3/library/argparse.html
* Access date: 2026-06-08
* What it was used to verify: Current `argparse` behavior for unrecognized options and forwarding unknown args.
* Relevant conclusion: The planned `parse_args()` + `REMAINDER` delegation is not safe for forwarding validator options like `--config`; `parse_known_args()` or early delegation is needed.

### Read-only validation performed

* `pwd`, `git status --short`, `git branch --show-current`, `git log --oneline -n 10`, `git remote -v`, `git diff --stat`: confirmed repo root, branch `testing`, recent plan commits, and dirty worktree.
* Inspected `git diff -- pyproject.toml`, `.vscode/settings.json`, `src/project_standards/sync_vscode_colors.py`, and `tests/test_sync_vscode_colors.py`: confirmed the uncommitted console-script work that C2 would overwrite.
* Inspected the revised plan with `rg`, `sed`, and `nl`: retested prior issue areas and identified the validate-delegation bug.
* Inspected `docs/superpowers/specs/2026-06-08-adopt-cli-design.md`: confirmed the spec requires `project-standards validate ...` delegation.
* Inspected `src/project_standards/validate_frontmatter.py`: confirmed validator flags that must pass through.
* Ran a read-only Python reproduction of the planned `argparse` parser: confirmed `validate --config x` exits 2 as unrecognized.
* Inspected `meta/versioning.md`, `CHANGELOG.md`, `docs/handoff/deployed.md`, `docs/handoff/specs-plans.md`, `docs/handoff/state.md`, `docs/handoff/architecture.md`, `docs/handoff/sessions/2026-06.md`, and `git tag --list 'v2*'`: checked release-state and handoff sequencing.
* Inspected `pyproject.toml`, `uv.lock`, `.github/workflows/check.yml`, `registry.py`, `registry.json`, and `.project-standards.yml`: checked package scripts, locked CI expectations, registry defaults, and validation scope.

### Recommended implementation validation

* Run only after correcting the plan: add a test proving `project_standards.cli.main(["validate", "--config", ".project-standards.yml", "--quiet"])` delegates successfully.
* Run only after implementation: `uv run project-standards validate --config .project-standards.yml --quiet`
* Run only after implementation: verify `[project.scripts]` preserves pre-existing entries and adds `project-standards`.
* Run only after implementation: add registry/bundle drift tests for both directions and verify both `list` and `adopt` fail cleanly.
* Run only after implementation: `uv run pytest tests/test_adopt_cli.py -v`
* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest`
* Run only after implementation: `uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`
* Run only after implementation: build and inspect a wheel in a temp directory, then run the installed CLI from that wheel.
* Run only after user-approved release: verify `v2.1.0` and moving `v2` point at the intended release commit before updating `deployed.md`.

### Final recommendation

Claude Code should revise the plan using the findings above

### Review ledger for next loop

* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-06-08-adopt-cli.md
* Audit round: 5
* Open issue IDs: CR-NEW-004, CR-NEW-005, CR-NEW-006
* Resolved issue IDs: CR-001, CR-002, CR-003, CR-004, CR-005, CR-NEW-001, CR-NEW-002, CR-NEW-003
* Superseded issue IDs: None
* Significant findings remaining: Yes
* Next audit should focus on: validate-subcommand flag delegation, preserving current dirty `[project.scripts]` entries, and removing `deployed.md` from E2’s pre-release file list.

