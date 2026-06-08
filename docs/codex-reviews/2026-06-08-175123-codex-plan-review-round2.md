### Executive summary

Claude Code’s revisions resolve most of the prior audit findings, but significant findings remain. The plan is closer, but it is still not ready to execute because it leaves a strict-gate failure in the proposed code, only partially fixes `local_edits` promotion, and introduces/retains unsafe `--relock` and shared-artifact update edge cases.

New internet research was required for the revised Ruff/CI/uv assumptions. The Python pin direction is supported by current `uv`/`setup-uv` docs; the main external conflict found is Ruff `PTH123`, which confirms the planned `open()` call will be flagged under this repo’s selected `PTH` lint family.

### Verdict

Needs major correction before execution

### Audit loop status

* Audit type: Follow-up audit
* Plan path: `/home/chris/projects/project-standards/docs/superpowers/plans/2026-06-08-check-drift.md`
* Prior audit issue count: 8
* Resolved issue count: 6
* Still open issue count: 0
* Partially resolved issue count: 2
* New issue count: 3
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

I re-read the revised plan, the approved drift spec, current repo state, CLI/adopt engine/manifest/registry code, bundled manifests, packaging tests, workflow conventions, handoff pointer table, and strict tool config. I retested prior fixes for preflight gating, strict-gate executability, local edit promotion, one-shot lock writing, JSON/fragments, CI warnings, docs scope, and Python pinning.

I also attacked new failure modes: typoed `--relock` standards, lock writes after no-op relock, shared artifacts with mixed owner states, argparse false positives, and Ruff false positives in proposed snippets. I did not run tests, build, ruff, basedpyright, or validators because this is read-only and those commands may write caches/build artifacts.

### Prior findings status

#### CR-001: Plan lacks a required preflight for the current dirty, held, red-gate repo state

* Previous severity: High
* Current status: Resolved
* Evidence: Task 0 now explicitly blocks implementation until the user clears the `2.2.0` start, the tree is clean or intentionally owned, the baseline gate is recorded green or acknowledged, and the branch is confirmed as `testing` (`docs/superpowers/plans/2026-06-08-check-drift.md:39-53`). Current `git status --short` still shows a dirty tree, so this preflight remains necessary.
* Remaining action for Claude Code: Execute Task 0 exactly before implementation; do not bypass it.

#### CR-002: Task 11 cannot pass as written and violates the strict gate

* Previous severity: High
* Current status: Partially resolved
* Evidence: The original missing import/unused-name/untyped-test issues were mostly corrected, but the revised Task 9 snippet uses `open(summary_path, ...)` (`docs/superpowers/plans/2026-06-08-check-drift.md:1075-1078`). This repo selects Ruff `PTH` rules (`pyproject.toml:43-44`), and Ruff’s official `PTH123` rule flags builtin `open()` in favor of `Path.open()`. The plan also still uses a `# type: ignore[arg-type]` where its own gate note says to narrow `load_lock` instead (`docs/superpowers/plans/2026-06-08-check-drift.md:1302`).
* Remaining action for Claude Code: Replace the CI summary write with `Path(summary_path).open(...)`, narrow `load_lock` in the test instead of ignoring the union, and re-check all snippets against `ruff check` + `basedpyright`.

#### CR-003: `--update --force` leaves `local_edits` in the wrong lock table

* Previous severity: High
* Current status: Partially resolved
* Evidence: `apply_update` now promotes `disk_hash == tmpl_hash` into `[artifacts]` (`docs/superpowers/plans/2026-06-08-check-drift.md:1391-1395`). However `merge_and_write`, used by `adopt`/`adopt --force`, still preserves this standard’s `[local_edits]` untouched (`docs/superpowers/plans/2026-06-08-check-drift.md:360-373`), and `_cmd_adopt` calls it after writing artifacts (`docs/superpowers/plans/2026-06-08-check-drift.md:546-562`). A forced re-adopt can therefore write the template and still leave the dest in `local_edits`, causing a future template bump to report `LOCAL-EDIT` instead of `STALE`.
* Remaining action for Claude Code: Change `merge_and_write` to remove newly written artifact destinations from `local_edits`; add an `adopt --force` regression test that proves future template changes become `STALE`.

#### CR-004: Lock-write safety claim does not match the planned implementation

* Previous severity: High
* Current status: Resolved
* Evidence: Task 11 now rebuilds a whole `Lock` in memory and calls `write_lock` once after file writes (`docs/superpowers/plans/2026-06-08-check-drift.md:1372-1417`), with an explicit lock-write failure test (`docs/superpowers/plans/2026-06-08-check-drift.md:1306-1327`).
* Remaining action for Claude Code: Keep the one-shot lock write and add the extra failure-mode tests listed below.

#### CR-005: Public JSON/report contract omits standards grouping and fragment `SKIPPED`

* Previous severity: High
* Current status: Resolved
* Evidence: Task 7 introduces `StandardStates` and `FragmentState`; Task 9 emits the grouped `standards[]` schema, owner lists, summary, and `fragments` entries (`docs/superpowers/plans/2026-06-08-check-drift.md:585-590`, `1041-1057`).
* Remaining action for Claude Code: Add a full JSON snapshot test, not only spot assertions.

#### CR-006: CI warning visibility is deferred but the spec requires it

* Previous severity: Medium
* Current status: Resolved
* Evidence: Task 9 adds `emit_ci_annotations`; Task 13 states the workflow relies on the command emitting warnings and step summary for non-failing drift (`docs/superpowers/plans/2026-06-08-check-drift.md:1065-1080`, `1566-1571`).
* Remaining action for Claude Code: Fix the Ruff `open()` issue under CR-002 and test `ORPHAN` plus `restamp_pending`, not only `LOCAL-EDIT`.

#### CR-007: Handoff and adoption docs update scope is incomplete

* Previous severity: Medium
* Current status: Resolved
* Evidence: Task 14 now includes `docs/handoff/specs-plans.md` and all four standards’ `adopt.md` files (`docs/superpowers/plans/2026-06-08-check-drift.md:1605-1610`, `1638-1645`).
* Remaining action for Claude Code: Apply the docs updates only after implementation and gate success.

#### CR-008: Workflow Python/tool assumptions need explicit verification

* Previous severity: Medium
* Current status: Resolved
* Evidence: Task 13 pins `uvx --python 3.14` (`docs/superpowers/plans/2026-06-08-check-drift.md:1567-1571`). Current `uv` docs confirm `uvx` is `uv tool run` and `--python` selects the interpreter for the run environment.
* Remaining action for Claude Code: Smoke the workflow path after implementation.

### New blocking issues

#### CR-NEW-001: `--relock` silently succeeds for unknown standards

* Severity: High
* Status: Confirmed
* Adversarial angle: Typoed input can create a false-green lock
* Plan reference: Task 12 `relock`; Task 10 parser
* Finding: `relock` skips any standard whose `registry.default_contract(sid)` is `None` before calling `build_plan([sid])`. For `project-standards check --relock typo`, the plan can write an empty/no-op lock and return success instead of reporting an unknown standard.
* Repository evidence: The existing adopt engine validates unknown standards in `build_plan` (`src/project_standards/adopt/engine.py:60-69`), but the planned `relock` bypasses that by continuing on `contract is None` (`docs/superpowers/plans/2026-06-08-check-drift.md:1470-1476`). The spec says `--relock` takes standards positionally “like `adopt`” and resolves each named standard’s manifest (`docs/superpowers/specs/2026-06-08-check-drift-design.md:135`, `238`).
* External research evidence: Not applicable.
* Why it matters: A typo during bootstrap could produce a lock with no standards; a later check over that lock can appear green while nothing is actually tracked.
* Recommended action for Claude Code: Validate all `--relock` standard ids before writing any lock. Let `build_plan`/`UsageError` reject unknown ids, or explicitly check against `available_standards()` and fail with exit 2.
* Suggested validation: Add tests that `check --relock not-a-standard` returns 2, writes no lock, and cannot make a subsequent `check` falsely green.

#### CR-NEW-002: Shared artifacts can let `--update` overwrite a local edit without `--force`

* Severity: High
* Status: Needs Claude verification
* Adversarial angle: Shared-destination aggregation can violate local-edit safety
* Plan reference: Task 11 `apply_update`
* Finding: `apply_update` chooses one “most severe” state per dest using `_SEVERITY`, where `STALE` outranks `LOCAL-EDIT`, then writes any dest whose chosen state is `STALE`/`MISSING`. For shared artifacts, that can overwrite a relock-accepted local edit if another owner of the same dest classifies it as `STALE`.
* Repository evidence: `_SEVERITY` ranks `LOCAL-EDIT` below `STALE` (`docs/superpowers/plans/2026-06-08-check-drift.md:990-994`), and `apply_update` writes based on that single chosen state (`docs/superpowers/plans/2026-06-08-check-drift.md:1358-1370`). The manifests show `.editorconfig` and `.vscode/extensions.json` are shared by `markdown-tooling` and `python-tooling` (`src/project_standards/bundles/markdown-tooling/adopt.toml:16-24`, `src/project_standards/bundles/python-tooling/adopt.toml:40-48`). The spec says `LOCAL-EDIT` is skipped unless `--force` (`docs/superpowers/specs/2026-06-08-check-drift-design.md:138-139`).
* External research evidence: Not applicable.
* Why it matters: The safety promise is destination-level: do not clobber consumer-owned edits without `--force`. Owner-level mixed state should not allow one standard to overwrite another standard’s accepted edit on the same path.
* Recommended action for Claude Code: Aggregate shared destinations with protective precedence: `UNSAFE` always skip; if any owner is `LOCAL-EDIT`, skip unless `--force`; if any owner is divergent `UNLOCKED`, skip unless `--force`; only then sync `STALE`/`MISSING`/restamp cases.
* Suggested validation: Add a shared-artifact regression test with one owner in `[local_edits]` and another owner stale, then assert plain `--update` does not write the file and `--update --force` does.

### New non-blocking issues

#### CR-NEW-003: `--relock` without standards relies on argparse instead of explicit usage validation

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Flag-matrix false positive
* Plan reference: Task 10 parser and tests
* Finding: The spec says invalid combinations exit 2 with a usage error and should not rely on accidental argparse behavior, including `--relock` without positional standards. The plan uses `nargs="+"`, so `main(["check", "--relock"])` will raise argparse `SystemExit` rather than returning through the CLI’s `UsageError` boundary, and the plan has no test for this matrix row.
* Repository evidence: Spec flag matrix requirement is explicit (`docs/superpowers/specs/2026-06-08-check-drift-design.md:144-151`). The planned parser uses `nargs="+"` (`docs/superpowers/plans/2026-06-08-check-drift.md:1201-1207`), and planned flag tests cover only `--force` without `--update` and `--relock` with `--update` (`docs/superpowers/plans/2026-06-08-check-drift.md:1142-1148`).
* External research evidence: Not applicable.
* Why it matters: Console execution exits 2, but in-repo `main([...])` tests and callers get an exception path instead of the project’s normal clean return-code behavior.
* Recommended action for Claude Code: Use `nargs="*"` plus explicit `UsageError("--relock requires at least one STANDARD")`, or catch argparse exits consistently; add the missing flag-matrix test.
* Suggested validation: Add `assert main(["check", "--dest", str(tmp_path), "--relock"]) == 2` and assert the stderr message is project-controlled.

### Regressions

None found.

### Internet research performed

* Source name: Ruff docs — builtin-open (PTH123)  
  URL: https://docs.astral.sh/ruff/rules/builtin-open/  
  Access date: 2026-06-08  
  What it was used to verify: Whether selected Ruff `PTH` rules flag builtin `open()`.  
  Relevant conclusion: `PTH123` checks uses of `open()` and recommends `Path.open()`, so the planned CI summary code conflicts with this repo’s Ruff selection.

* Source name: uv docs — Tools  
  URL: https://docs.astral.sh/uv/concepts/tools/  
  Access date: 2026-06-08  
  What it was used to verify: `uvx` behavior.  
  Relevant conclusion: `uvx` is exactly an alias for `uv tool run`.

* Source name: uv docs — CLI reference  
  URL: https://docs.astral.sh/uv/reference/cli/  
  Access date: 2026-06-08  
  What it was used to verify: `--python` on tool/run environments.  
  Relevant conclusion: `--python` selects the interpreter for the run environment and may also be set by `UV_PYTHON`.

* Source name: astral-sh/setup-uv README  
  URL: https://github.com/astral-sh/setup-uv  
  Access date: 2026-06-08  
  What it was used to verify: Python pinning alternatives in GitHub Actions.  
  Relevant conclusion: `setup-uv` supports a `python-version` input that sets `UV_PYTHON`; the plan’s `uvx --python 3.14` is a valid direct pinning strategy.

* Source name: GitHub Docs — Workflow commands  
  URL: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands  
  Access date: 2026-06-08  
  What it was used to verify: Warning annotations and `GITHUB_STEP_SUMMARY`.  
  Relevant conclusion: `::warning::` commands and writing Markdown to `GITHUB_STEP_SUMMARY` are supported.

### Read-only validation performed

* `pwd`, `git branch --show-current`, `git log --oneline -n 10`, `git status --short`, and `git diff --stat` confirmed repo root, branch `testing`, recent plan-review commit, and current dirty tree.
* `nl -ba docs/superpowers/plans/2026-06-08-check-drift.md` and targeted `sed -n` ranges re-read the revised plan and located changed task details.
* `nl -ba docs/superpowers/specs/2026-06-08-check-drift-design.md` and `git diff -- docs/superpowers/specs/2026-06-08-check-drift-design.md` checked the approved design and local spec drift.
* `rg --files src/project_standards tests .github/workflows standards docs/handoff` confirmed current source/test/workflow structure and that `adopt/check.py`, `adopt/lock.py`, and the drift workflow do not exist yet.
* `nl -ba` inspected `engine.py`, `cli.py`, `registry.py`, `errors.py`, `manifest.py`, bundled `adopt.toml` manifests, `pyproject.toml`, packaging tests, existing workflow, and `docs/handoff/specs-plans.md`.
* `rg -n` checked plan references for strict-gate, JSON, CI, lock, `relock`, and drift terms.
* Web research inspected current official docs for Ruff, uv, setup-uv, and GitHub Actions workflow commands.

### Recommended implementation validation

* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest`
* Run only after implementation: `uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`
* Run only after implementation: `uv build` plus the packaging test.
* Add targeted tests for unknown `--relock`, `--relock` without standards, `adopt --force` local-edit promotion, shared-artifact local-edit protection, file-write failure before final lock write, full JSON snapshots, and CI annotations for `ORPHAN` plus `restamp_pending`.

### Final recommendation

Claude Code should revise the plan using the findings above

### Review ledger for next loop

* Plan path: `/home/chris/projects/project-standards/docs/superpowers/plans/2026-06-08-check-drift.md`
* Audit round: 2
* Open issue IDs: CR-002, CR-003, CR-NEW-001, CR-NEW-002, CR-NEW-003
* Resolved issue IDs: CR-001, CR-004, CR-005, CR-006, CR-007, CR-008
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: Ruff/PTH strict-gate compliance, `merge_and_write` local-edit pruning for adopt/adopt --force, explicit `--relock` validation, shared-artifact update aggregation, and complete flag-matrix tests.