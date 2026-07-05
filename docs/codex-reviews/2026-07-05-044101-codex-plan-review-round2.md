### Executive summary

Claude Code’s revisions resolve the H1/profile false-positive path for the CLI flow, but they do not resolve the repo-level `Validate Specs` CI failure. The plan now documents that gap and files it as pre-existing, but the workflow is still triggered by the planned `src/**` and Markdown changes and still runs a command that the current repo config cannot satisfy. Significant findings remain.

No new internet research was required in this follow-up; the remaining issues are repo-local plan/workflow/parser assumptions.

### Verdict

Needs major correction before execution

### Audit loop status

* Audit type: Follow-up audit
* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-07-05-project-spec-tooling-spec3.md
* Prior audit issue count: 3
* Resolved issue count: 1
* Still open issue count: 1
* Partially resolved issue count: 1
* New issue count: 0
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

Retested the prior findings against the revised plan and current repo state: H1/profile consistency, the `Validate Specs` workflow/config mismatch, and fenced-code heading handling. Re-read the revised plan, inspected the current CLI/config/validator/workflow code, checked bundled-vs-standard template identity, and compared the proposed fence scanner against the repo’s existing CommonMark-aware fence handling.

I did not run tests or workflow commands because this is a read-only audit and the relevant commands can write caches/artifacts.

### Prior findings status

#### CR-001: H1 tier suffix rewrite can silently fail while validation still passes

* Previous severity: High
* Current status: Resolved
* Evidence: The revised plan adds `test_check_upgradeable_rejects_wrong_h1_tier_suffix` at plan lines 720-729 and an explicit `_h1_tier` check in `check_upgradeable` at lines 751-780. `_run_upgrade` now runs `check_upgradeable` before `upgrade_text` at lines 943-947, so a validate-clean source with a stale/missing H1 tier suffix is refused before output/write.
* Remaining action for Claude Code: None for the CLI path. Optional hardening: make `_rewrite_h1_suffix` itself strict, but the revised precheck closes the prior user-visible false-positive path.

#### CR-002: Final gate omits the repo’s triggered `Validate Specs` CI workflow

* Previous severity: High
* Current status: Still open
* Evidence: The plan now acknowledges the gap at lines 1133-1134 and says not to fix it, but `.github/workflows/validate-specs.yml` still triggers on PRs touching `src/**` and `**/*.md` at lines 11-16 and runs `uv run project-standards spec validate --config ...` at lines 55-57. `.project-standards.yml` still has no top-level `spec:` block, and `collect_spec_paths()` raises `DiscoveryError` when no explicit files and no `spec.include` exist in `src/project_standards/specs/config.py:67-72`.
* Remaining action for Claude Code: Revise the plan so execution can produce a CI-green branch, or make the CI exception an explicit accepted release/integration risk approved by the user. Merely documenting the gap in `TODO.md` does not make the triggered workflow executable.

#### CR-003: Heading segmentation lacks an explicit fenced-code adversarial test

* Previous severity: Medium
* Current status: Partially resolved
* Evidence: The revised plan adds a simple fenced-heading test at lines 216-226 and implements `_heading_starts()` with a fence toggle at lines 252-266. However, that toggle treats any line beginning with three backticks or tildes as open/close and does not enforce CommonMark’s same-character and at-least-equal-length close rules. The repo already has a more precise fence model in `src/project_standards/validate_frontmatter.py:223-257`, with tests for same-character and longer outer fences in `tests/test_validate_frontmatter.py:1447-1466`.
* Remaining action for Claude Code: Add adversarial tests for four-backtick outer fences containing inner triple-backtick examples and for mixed `~~~` inside backtick fences, then reuse or mirror the existing robust fence-tracking logic.

### New blocking issues

None found.

### New non-blocking issues

None found.

### Regressions

None found.

### Internet research performed

No new external sources were consulted during this follow-up audit. The revised plan’s remaining disputed claims are local repository/workflow/parser behavior, and the Python filesystem assumptions were already checked in the prior audit.

### Read-only validation performed

* `pwd`: Confirmed repository root is `/home/chris/projects/project-standards`.
* `git status --short`, `git branch --show-current`, `git log --oneline -n 10`: Confirmed branch `testing`, recent plan r2 commit, and only untracked codex review docs.
* `nl -ba` on the revised plan: Re-read all 1154 lines and located the revised CR-001/CR-002/CR-003 handling.
* `nl -ba` on `.github/workflows/validate-specs.yml`, `.project-standards.yml`, and `src/project_standards/specs/config.py`: Confirmed the `Validate Specs` workflow still triggers and still has no repo-local `spec:` discovery config.
* `nl -ba` on `src/project_standards/specs/cli.py`, `commands/new.py`, `commands/validate.py`, and `registry.py`: Checked current integration points, validation limits, atomic-write source, and template registry behavior.
* `cmp -s` on canonical vs bundled tier templates: Confirmed light, standard, and full template copies are currently byte-identical.
* `rg`/`nl -ba` on existing fence logic and tests: Confirmed the repo already models same-character and equal-or-greater-length fence closing more strictly than the plan’s proposed `_heading_starts()`.

### Recommended implementation validation

* Run only after implementation: `uv run pytest tests/test_spec_upgrade_fixtures.py tests/test_spec_upgrade.py tests/test_spec_upgrade_cli.py -v`
* Run only after implementation: `uv run pytest tests/test_spec_new_cli.py tests/test_spec_new.py -v`
* Run only after correcting CR-002: `uv run project-standards spec validate --config .project-standards.yml`
* Run only after implementation: `uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit && uv run validate-frontmatter --config .project-standards.yml`
* Run only after implementation: targeted tests for nested/long fenced code blocks containing `##`/`###` lines inside authored spec sections.

### Final recommendation

Claude Code should revise the plan using the findings above

### Review ledger for next loop

* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-07-05-project-spec-tooling-spec3.md
* Audit round: 2
* Open issue IDs: CR-002, CR-003
* Resolved issue IDs: CR-001
* Superseded issue IDs: None
* Significant findings remaining: Yes
* Next audit should focus on: whether the plan makes the triggered `Validate Specs` workflow CI-executable or explicitly approved as an integration exception, and whether fenced-code heading segmentation handles CommonMark fence close rules rather than only simple triple-fence cases.