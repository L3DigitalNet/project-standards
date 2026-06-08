### Executive summary

Claude Code’s latest corrections resolve all findings that were open at the end of round 2. The plan is no longer blocked by the prior Ruff, `local_edits`, `--relock`, shared-artifact overwrite, or argparse issues.

Significant non-blocking findings remain. The main gaps are that the drift caller template is packaged but not wired into any adoption path, `check --update` writes a lock while preserving the old `tool_version`, and report/CI deduplication can hide `restamp-pending` on shared artifacts. New internet research was used to re-check current uv/setup-uv/GitHub Actions assumptions; no new external contradiction was found for the pinned Python/uvx strategy.

### Verdict

Needs minor correction before execution

### Audit loop status

* Audit type: Follow-up audit
* Plan path: `/home/chris/projects/project-standards/docs/superpowers/plans/2026-06-08-check-drift.md`
* Prior audit issue count: 11
* Resolved issue count: 11
* Still open issue count: 0
* Partially resolved issue count: 0
* New issue count: 3
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

I re-read the revised plan, the approved drift spec, current source layout, adopt engine, CLI, manifests, packaging test, workflows, changelog, and handoff pointer files. I retested the prior fixes for Ruff `PTH123`, `load_lock` narrowing, `merge_and_write` pruning, explicit `--relock` validation, shared-artifact update protection, and empty-`--relock` usage handling.

I also attacked new failure modes: whether the new caller workflow is actually reachable by consumers through `adopt`, whether lock provenance updates match the spec after `--update`, whether shared-artifact dedup can hide a `restamp-pending` warning, and whether current setup-uv/uv/GitHub Actions assumptions still match official docs. I did not run tests, build, ruff, basedpyright, validators, or package commands because this audit is read-only and those commands may write caches or artifacts.

### Prior findings status

#### CR-001: Plan lacks a required preflight for the current dirty, held, red-gate repo state

* Previous severity: High
* Current status: Resolved
* Evidence: Task 0 still blocks implementation until user clearance, clean/owned tree, baseline gate, and branch check are confirmed (`docs/superpowers/plans/2026-06-08-check-drift.md:39-53`). Current `git status --short` still shows unrelated dirty/untracked work, so the preflight remains necessary.
* Remaining action for Claude Code: Execute Task 0 before implementation.

#### CR-002: Task 11 cannot pass as written and violates the strict gate

* Previous severity: High
* Current status: Resolved
* Evidence: The CI summary write now uses `Path(summary_path).open(...)` (`docs/superpowers/plans/2026-06-08-check-drift.md:1131-1136`), and the plan no longer contains the prior `type: ignore[arg-type]`. This matches the repo’s selected Ruff `PTH` family (`pyproject.toml:43-44`).
* Remaining action for Claude Code: None beyond running the planned strict gate after implementation.

#### CR-003: `--update --force` leaves `local_edits` in the wrong lock table

* Previous severity: High
* Current status: Resolved
* Evidence: `merge_and_write` now removes newly written artifact destinations from this standard’s `local_edits` (`docs/superpowers/plans/2026-06-08-check-drift.md:370-376`) and adds an `adopt --force` regression test (`docs/superpowers/plans/2026-06-08-check-drift.md:535-552`).
* Remaining action for Claude Code: None beyond implementing and running the regression test.

#### CR-004: Lock-write safety claim does not match the planned implementation

* Previous severity: High
* Current status: Resolved
* Evidence: The plan still rebuilds the lock in memory and performs one final `write_lock` after file writes (`docs/superpowers/plans/2026-06-08-check-drift.md:1462-1507`), with recovery tests for lock-write failure (`docs/superpowers/plans/2026-06-08-check-drift.md:1370-1390`).
* Remaining action for Claude Code: None beyond implementation validation.

#### CR-005: Public JSON/report contract omits standards grouping and fragment `SKIPPED`

* Previous severity: High
* Current status: Resolved
* Evidence: `StandardStates` and `FragmentState` are in the model, JSON emits `standards[]`, owners, and `fragments`, and the plan now includes a full JSON snapshot test (`docs/superpowers/plans/2026-06-08-check-drift.md:725-744`, `983-1038`, `1087-1114`).
* Remaining action for Claude Code: None beyond running the tests.

#### CR-006: CI warning visibility is deferred but the spec requires it

* Previous severity: Medium
* Current status: Resolved
* Evidence: `emit_ci_annotations` emits warnings and step-summary rows for `LOCAL-EDIT`, `ORPHAN`, and `restamp_pending`, and tests now cover orphan/restamp visibility (`docs/superpowers/plans/2026-06-08-check-drift.md:1008-1017`, `1121-1136`).
* Remaining action for Claude Code: Address new shared-dedup visibility issue CR-NEW-006.

#### CR-007: Handoff and adoption docs update scope is incomplete

* Previous severity: Medium
* Current status: Resolved
* Evidence: Task 14 includes `docs/handoff/specs-plans.md` and all four standards’ `adopt.md` files (`docs/superpowers/plans/2026-06-08-check-drift.md:1714-1717`, `1745-1752`).
* Remaining action for Claude Code: Update only after implementation and successful gates.

#### CR-008: Workflow Python/tool assumptions need explicit verification

* Previous severity: Medium
* Current status: Resolved
* Evidence: The workflow still pins `uvx --python 3.14` (`docs/superpowers/plans/2026-06-08-check-drift.md:1673-1678`). Current uv docs confirm `uvx` is `uv tool run` and `--python` can request/download a specific Python.
* Remaining action for Claude Code: Smoke the workflow after implementation.

#### CR-NEW-001: `--relock` silently succeeds for unknown standards

* Previous severity: High
* Current status: Resolved
* Evidence: `relock` now validates all ids against `available_standards()` before writing anything and raises `UsageError` for unknown ids (`docs/superpowers/plans/2026-06-08-check-drift.md:1546-1550`, `1564-1570`).
* Remaining action for Claude Code: None beyond running the new test.

#### CR-NEW-002: Shared artifacts can let `--update` overwrite a local edit without `--force`

* Previous severity: High
* Current status: Resolved
* Evidence: `apply_update` now aggregates states by destination and treats any `LOCAL-EDIT`/`UNLOCKED` owner as protective unless `--force` is supplied (`docs/superpowers/plans/2026-06-08-check-drift.md:1393-1411`, `1443-1460`).
* Remaining action for Claude Code: None beyond running the regression test.

#### CR-NEW-003: `--relock` without standards relies on argparse instead of explicit usage validation

* Previous severity: Medium
* Current status: Resolved
* Evidence: The parser now uses `nargs="*"` and explicitly raises `UsageError("--relock requires at least one STANDARD")` (`docs/superpowers/plans/2026-06-08-check-drift.md:1207-1208`, `1265`, `1278-1279`).
* Remaining action for Claude Code: None beyond running the flag-matrix test.

### New blocking issues

None found.

### New non-blocking issues

#### CR-NEW-004: Drift caller template is packaged but not adopted or drift-checked

* Severity: Medium
* Status: Confirmed
* Adversarial angle: CI delivery can pass packaging tests while consumers receive no workflow through the established adopt path
* Plan reference: Task 13 CI delivery; Task 14 packaging/docs
* Finding: The plan creates `src/project_standards/bundles/_shared/drift-check.caller.yml`, packages it, and tests that it exists, but does not add it to any `adopt.toml` manifest or otherwise define a CLI/docs path that actually installs it into a consumer repo.
* Repository evidence: Current adopted workflow callers are manifest artifacts (`src/project_standards/bundles/markdown-frontmatter/adopt.toml:10-14`, `src/project_standards/bundles/markdown-tooling/adopt.toml:26-30`). The plan only creates the drift caller file and packaging assertion (`docs/superpowers/plans/2026-06-08-check-drift.md:1621-1642`, `1681-1697`, `1717`, `1729`); `rg` found no planned `adopt.toml` update for it. The spec says manifests are the source of truth for artifact sets (`docs/superpowers/specs/2026-06-08-check-drift-design.md:42`).
* External research evidence: Not applicable.
* Why it matters: The CI workflow can be “delivered” in the wheel but remain unreachable by `project-standards adopt`, and `check` will not detect drift in that caller workflow if it is not a locked artifact.
* Recommended action for Claude Code: Decide the delivery model. Either add the caller as a shared `workflow-caller` artifact in the relevant manifests, with dedup tests when multiple standards are adopted, or explicitly document it as manual-only and add validation proving the manual path is discoverable and intentional.
* Suggested validation: Add an adoption test that a consumer adopting the chosen standard set receives `.github/workflows/standards-drift.yml`, the lock records it, and a later template change is reported by `check`.

#### CR-NEW-005: `check --update` preserves stale `tool_version` while writing the lock

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Provenance field can remain stale after a successful lock-writing operation
* Plan reference: Task 11 `apply_update`
* Finding: `apply_update` writes a new lock but sets `tool_version=lock.tool_version`, not the current package version.
* Repository evidence: The design defines `tool_version` as the full tool release that last wrote the lock (`docs/superpowers/specs/2026-06-08-check-drift-design.md:100-105`). The planned `apply_update` creates `new_lock` with the prior `lock.tool_version` (`docs/superpowers/plans/2026-06-08-check-drift.md:1494-1496`), while `adopt` and `relock` use `version("project-standards")` (`docs/superpowers/plans/2026-06-08-check-drift.md:574`, `1599`).
* External research evidence: Not applicable.
* Why it matters: A lock can be rewritten by 2.2.0 while still claiming an older tool wrote it, undermining the lock’s provenance contract and operator debugging.
* Recommended action for Claude Code: Set `new_lock.tool_version` to `version("project-standards")` inside `apply_update` or pass the current tool version from `_cmd_check`.
* Suggested validation: Add a test with an old `tool_version` in the lock, run `check --update`, and assert the rewritten lock records `version("project-standards")`.

#### CR-NEW-006: Shared-artifact dedup can hide `restamp-pending` in report and CI annotations

* Severity: Medium
* Status: Confirmed
* Adversarial angle: A visible recovery flag can be dropped by report aggregation even though JSON still counts it
* Plan reference: Task 9 `_dedup_by_dest`, `format_check_report`, `emit_ci_annotations`
* Finding: `_dedup_by_dest` keeps the first artifact for equal-severity states and does not merge `restamp_pending`. For a shared artifact where one owner is `CLEAN` and another is `CLEAN` with `restamp_pending=True`, the human report and CI annotations can show no restamp warning.
* Repository evidence: `_dedup_by_dest` only replaces on strictly greater severity (`docs/superpowers/plans/2026-06-08-check-drift.md:1062-1068`); `format_check_report` and `emit_ci_annotations` both consume that deduped result (`docs/superpowers/plans/2026-06-08-check-drift.md:1077-1083`, `1126-1128`). Shared artifacts exist today in both markdown-tooling and python-tooling manifests (`src/project_standards/bundles/markdown-tooling/adopt.toml:16-24`, `src/project_standards/bundles/python-tooling/adopt.toml:40-48`). The spec says every `restamp-pending` should be visible on every check and CI warning path (`docs/superpowers/specs/2026-06-08-check-drift-design.md:82`, `259`).
* External research evidence: Not applicable.
* Why it matters: The recovery signal for a partial lock write can be invisible on a passing CI run, which is exactly the failure mode the `restamp-pending` flag was introduced to prevent.
* Recommended action for Claude Code: Merge deduped artifacts by destination: choose max severity, OR together `restamp_pending`, and preserve the unioned owners. Prefer a state-combining helper with targeted tests.
* Suggested validation: Add a shared `.editorconfig` test with one owner clean and one owner restamp-pending; assert the human report and CI warning/summary include `restamp-pending`.

### Regressions

None found.

### Internet research performed

* Source name: uv CLI reference  
  URL: https://docs.astral.sh/uv/reference/cli/  
  Access date: 2026-06-08  
  What it was used to verify: `uvx` behavior and `uv tool run` equivalence.  
  Relevant conclusion: `uvx` is an alias for `uv tool run`; the plan’s `uvx --from ... project-standards check` shape remains plausible.

* Source name: uv Python versions docs  
  URL: https://docs.astral.sh/uv/concepts/python-versions/  
  Access date: 2026-06-08  
  What it was used to verify: `--python 3.14` behavior.  
  Relevant conclusion: uv can request a specific Python with `--python` and download one when needed.

* Source name: astral-sh/setup-uv README  
  URL: https://github.com/astral-sh/setup-uv  
  Access date: 2026-06-08  
  What it was used to verify: setup-uv inputs and cache/Python behavior.  
  Relevant conclusion: setup-uv installs uv, supports `python-version`, and defaults cache behavior to `auto`; consider matching this repo’s existing consumer-cache guard.

* Source name: GitHub actions/checkout README  
  URL: https://github.com/actions/checkout  
  Access date: 2026-06-08  
  What it was used to verify: `actions/checkout@v6` and permissions guidance.  
  Relevant conclusion: `checkout@v6` is current in the official README, and `contents: read` matches the plan.

* Source name: Ruff PTH123 docs  
  URL: https://docs.astral.sh/ruff/rules/builtin-open/  
  Access date: 2026-06-08  
  What it was used to verify: Whether builtin `open()` is still flagged.  
  Relevant conclusion: `PTH123` still flags builtin `open()`; the revised `Path.open()` fix is correct.

* Source name: GitHub Actions workflow commands docs  
  URL: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands  
  Access date: 2026-06-08  
  What it was used to verify: `::warning::` and `GITHUB_STEP_SUMMARY` support.  
  Relevant conclusion: Warning annotations and Markdown step summaries are supported.

### Read-only validation performed

* `pwd`, `git branch --show-current`, `git log --oneline -n 10`, `git status --short`, and `git diff --stat` confirmed repo root, branch `testing`, recent round-2 plan commit, and a still-dirty tree.
* `nl -ba` and `rg -n` inspected the revised plan and located prior-fix areas for `Path.open`, `merge_and_write`, `--relock`, shared-artifact update, JSON/reporting, CI, and docs.
* `nl -ba` inspected the approved drift spec, current `engine.py`, `cli.py`, `manifest.py`, `errors.py`, `registry.py`, `pyproject.toml`, packaging tests, workflows, manifests, changelog, and handoff files.
* `rg --files` confirmed `adopt/check.py`, `adopt/lock.py`, `standards-drift.yml`, and `_shared/drift-check.caller.yml` do not yet exist in the repository.
* `git show --unified=60 be80894 -- docs/superpowers/plans/2026-06-08-check-drift.md` verified the latest committed corrections match the prior audit ledger.
* Web research checked official uv, setup-uv, GitHub Actions, actions/checkout, and Ruff documentation.

### Recommended implementation validation

* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest`
* Run only after implementation: `uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`
* Run only after implementation: `uv build` plus the packaging test.
* Add targeted tests for drift caller adoption/lock coverage, `check --update` refreshing `tool_version`, shared-artifact restamp visibility in human/CI output, and the existing prior-audit regressions.

### Final recommendation

Claude Code should revise the plan using the findings above

### Review ledger for next loop

* Plan path: `/home/chris/projects/project-standards/docs/superpowers/plans/2026-06-08-check-drift.md`
* Audit round: 3
* Open issue IDs: CR-NEW-004, CR-NEW-005, CR-NEW-006
* Resolved issue IDs: CR-001, CR-002, CR-003, CR-004, CR-005, CR-006, CR-007, CR-008, CR-NEW-001, CR-NEW-002, CR-NEW-003
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: consumer delivery path for the drift caller, current `tool_version` stamping during `check --update`, and shared-artifact report/CI merging for `restamp-pending`.