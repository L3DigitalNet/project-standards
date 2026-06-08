### Executive summary

The implementation plan needs major correction before Claude Code executes it. The core direction is sound, but the plan is not executable as written against the current repository state and it contains several spec-level correctness gaps around `--update`, lock writing, strict gate compliance, and the public JSON/fragments contract.

Internet research was required for the GitHub Actions and `uvx --from` assumptions. The ref-pinned workflow shape is broadly valid, but the plan still leaves Python/tool-runtime behavior and CI warning surfacing under-specified.

### Verdict

Needs major correction before execution

### Audit loop status

* Audit type: First audit
* Plan path: `/home/chris/projects/project-standards/docs/superpowers/plans/2026-06-08-check-drift.md`
* Significant findings remaining: Yes
* Blocking issue count: 5
* Non-blocking issue count: 3

### What the plan gets right

* Puts `check` inside `adopt/`, which matches the repo’s current engine/manifest structure and avoids duplicating render/path-safety logic.
* Uses rendered-byte sha256 hashes instead of version labels for drift decisions, matching the approved design.
* Keeps `adopt --dry-run` file-free and lock-free.
* Uses a ref-pinned `uvx --from git+https://...@ref` workflow command; official `uv` docs support git sources with branch/tag/commit refs.
* Adds TDD coverage categories for symlink safety, no-lock behavior, lock parsing, and CLI exit codes.

### Adversarial review performed

I inventoried the plan’s material claims across lock format, state machine, CLI flags, update/relock behavior, CI workflow delivery, packaging, docs, and validation gates. I then falsified those claims against the current source tree, manifests, tests, pyproject strict settings, workflow conventions, handoff pointer table, and the approved drift design spec.

I attacked the validation story for false positives: tests that would pass while JSON shape is wrong, `--force` appears to work but leaves future drift invisible, CI tests checking only substrings, and full-gate claims contradicted by missing imports/untyped samples. I did not run tests, builds, formatters, or validators because this audit is read-only and those commands can write caches/build artifacts.

### Blocking issues

#### CR-001: Plan lacks a required preflight for the current dirty, held, red-gate repo state

* Severity: High
* Status: Confirmed
* Adversarial angle: Sequencing and environment readiness
* Plan reference: The plan starts Task 1 implementation/commit flow immediately and says to keep the SSOT gate green after every task.
* Finding: The current repo is not in a safe baseline state for this plan. The working tree has many modified files plus untracked docs, and handoff state says `2.1.0` release is held while the full-repo SSOT gate is already red from concurrent in-flight work.
* Repository evidence: `git status --short` showed modified `.github/workflows/validate-markdown-frontmatter.yml`, `CHANGELOG.md`, `src/project_standards/cli.py`, `src/project_standards/validate_id.py`, tests, standards docs, plus untracked `docs/codex-reviews/`, `docs/superpowers/specs/README.md`, `scripts/README.md`, `src/project_standards/README.md`. Session state says `adopt` is implemented but not released, E3 held, and the full-repo SSOT gate is red from concurrent `validate_id.py`/formatting work.
* External research evidence: Not applicable.
* Why it matters: Executing this plan now would mix new commits and validation failures with unrelated in-flight work, making test results and release readiness ambiguous.
* Recommended action for Claude Code: Add an explicit preflight: confirm with the user whether implementation is still held; require a clean or intentionally-owned working tree; record the baseline gate status; do not begin Task 1 until the `2.1.0` ordering question is resolved.
* Suggested validation: Before implementation only, run `git status --short`, inspect recent commits, and run the existing SSOT gate after the current in-flight work is resolved.

#### CR-002: Task 11 cannot pass as written and violates the strict gate

* Severity: High
* Status: Confirmed
* Adversarial angle: Incremental executability and gate false positive
* Plan reference: Task 11 implementation lines around `apply_update`; Task 10/11 test snippets.
* Finding: `apply_update` calls `load_lock(dest_root)` before Task 12 imports `load_lock`, so Task 11’s “verify pass” claim is false. The same snippet defines unused `action_owner`, which Ruff will flag. The plan also includes untyped `capsys` test parameters and an untyped `_states` helper despite its own strict typing note.
* Repository evidence: `pyproject.toml` enables Ruff `F` rules and BasedPyright strict mode with `failOnWarnings = true`. The plan’s Task 11 snippet uses `fresh = load_lock(dest_root)` but imports only `StandardLock, merge_and_write` at that task; `load_lock` is imported later in Task 12. Task 10 uses bare `capsys`, and Task 11 has `def _states(tmp_path: Path):`.
* External research evidence: Not applicable.
* Why it matters: Claude Code following the task sequence will hit NameError or strict-gate failures before reaching the final gate, invalidating the plan’s TDD checkpoints.
* Recommended action for Claude Code: Move all required imports into the correct task, delete unused `action_owner`, and fully type every test/helper signature before implementation.
* Suggested validation: Run `uv run ruff check .` and `uv run basedpyright` after each task that changes Python, once implementation is allowed.

#### CR-003: `--update --force` leaves `local_edits` in the wrong lock table

* Severity: High
* Status: Confirmed
* Adversarial angle: Future false negative after a forced resync
* Plan reference: Task 11 `apply_update` restamp loop.
* Finding: The planned `apply_update` skips any `action.dest in sl.local_edits` when rebuilding artifacts, then calls `merge_and_write`, whose design preserves existing `local_edits`. After `--update --force` overwrites a local edit with the current template, the lock can still keep that dest under `[local_edits]`.
* Repository evidence: The approved spec says local-edits are never classified `STALE`; a `disk == tmpl` local edit is `CLEAN`, and lock-writing ops should repair to `tmpl_hash`. The plan’s `_classify` local-edit branch returns `LOCAL-EDIT` for any future `disk != tmpl`, never `STALE`. The Task 11 restamp loop excludes `sl.local_edits` from `new_artifacts`.
* External research evidence: Not applicable.
* Why it matters: A forced resync appears green today but future upstream template changes can be misreported as `LOCAL-EDIT` instead of failing as `STALE`.
* Recommended action for Claude Code: When a local edit is forced or already matches the template, remove it from `local_edits` and promote it to `artifacts` with the current template hash. Add a regression test that force-syncs a local edit, then simulates a later template bump and expects `STALE`.
* Suggested validation: Add tests for local-edit promotion on `--update --force` and for the “future template bump” state.

#### CR-004: Lock-write safety claim does not match the planned implementation

* Severity: High
* Status: Confirmed
* Adversarial angle: Crash consistency and rollback claim
* Plan reference: Spec Component 6 and Task 11.
* Finding: The spec requires file writes first, then one final atomic lock write. The plan instead loops over standards and calls `merge_and_write` once per standard. It also lacks the promised explicit “files updated; lock not written” error handling and does not test lock-write failure.
* Repository evidence: The spec states the lock is written “last, in a single atomic `write_lock`” and describes lock-write failure behavior. Task 11 calls `merge_and_write` inside `for sid, sl in lock.standards.items()`, which performs repeated lock reads/writes.
* External research evidence: Not applicable.
* Why it matters: A partial failure during the per-standard lock-write loop can leave mixed lock provenance. This weakens the plan’s recovery guarantees and makes the safety story harder to reason about.
* Recommended action for Claude Code: Build the complete updated `Lock` object in memory, prune artifacts/local edits correctly, and call `write_lock` once. Catch lock-write failure with the explicit operator guidance described in the spec.
* Suggested validation: Add failure-injection tests for file-write failure, final lock-write failure, and multi-standard partial update recovery.

#### CR-005: Public JSON/report contract omits standards grouping and fragment `SKIPPED`

* Severity: High
* Status: Confirmed
* Adversarial angle: Spec coverage and validation false positive
* Plan reference: Task 9 `states_to_json`, Task 7 `_whole_file_actions`, Task 13/self-review.
* Finding: The plan’s JSON returns a flat top-level `artifacts` list and no `standards` array, `contract_version`, or `fragments`. The approved spec’s JSON schema has `standards[].artifacts[]` and `standards[].fragments[]`, and the acceptance criteria require fragments marked `SKIPPED`.
* Repository evidence: `python-tooling/adopt.toml` has a `pyproject.toml` fragment and `adr/adopt.toml` has a `.project-standards.yml` fragment. The plan’s `_whole_file_actions` explicitly filters fragments out, and no later task adds them back to reports/JSON. The Task 9 JSON test only checks summary/exit code, so it would pass while the public schema is wrong.
* External research evidence: Not applicable.
* Why it matters: Consumers and CI integrations would build against a different machine-readable contract than the approved design, and fragment status would be invisible.
* Recommended action for Claude Code: Redesign `ArtifactState`/report generation to retain standard id, contract version, owners, and fragment `SKIPPED` entries, or explicitly revise the spec before implementation.
* Suggested validation: Snapshot-test the full JSON shape, including `standards`, `contract_version`, shared-artifact owners, and `fragments: [{"state": "SKIPPED"}]`.

### Non-blocking issues

#### CR-006: CI warning visibility is deferred but the spec requires it

* Severity: Medium
* Status: Confirmed
* Adversarial angle: CI false green
* Plan reference: Task 13 workflow and note deferring annotations.
* Finding: The spec says `LOCAL-EDIT`, `ORPHAN`, and `restamp-pending` must be surfaced via step summary and warnings on a green run. The plan says annotations are emitted by `check` “when it detects CI” or can be follow-up, but no task implements that behavior and the workflow has no summary/warning step.
* Repository evidence: Task 13 workflow only runs `project-standards check`; Task 13 tests assert substrings only. The approved spec explicitly requires `$GITHUB_STEP_SUMMARY` and `::warning::` visibility.
* External research evidence: GitHub reusable workflow docs confirm the planned workflow-call structure, but do not provide this missing app-level behavior.
* Why it matters: CI can pass while meaningful drift is buried in logs.
* Recommended action for Claude Code: Either implement CI warning/summary output in `check` now or add a workflow step that converts JSON output to summary/warnings. Add tests for this behavior.
* Suggested validation: Run a CI-like test with `GITHUB_STEP_SUMMARY` set and a `LOCAL-EDIT`, asserting summary/warning output.

#### CR-007: Handoff and adoption docs update scope is incomplete

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Documentation/state drift
* Plan reference: Task 14.
* Finding: Task 14 updates `architecture.md`, `deployed.md`, and `state.md`, but does not update `docs/handoff/specs-plans.md`, which currently has duplicate `check` design rows and still says implementation is held/awaiting plan. The final `git add` lists only Markdown/Python adopt docs, even though lock/check applies to all standards.
* Repository evidence: `docs/handoff/specs-plans.md` contains both a current `check drift design` row and a stale duplicate `check (drift detection) design` row. The plan’s file list says `standards/*/adopt.md`, but the commit command adds only `standards/markdown-tooling/adopt.md` and `standards/python-tooling/adopt.md`.
* External research evidence: Not applicable.
* Why it matters: Future sessions may read stale handoff state and consumers of Frontmatter/ADR adoption docs may miss lock/check guidance.
* Recommended action for Claude Code: Include `docs/handoff/specs-plans.md` and all affected `standards/*/adopt.md` files, or explicitly justify narrower docs scope.
* Suggested validation: After implementation, verify all handoff pointer/status rows and every standard adopt doc mention lock/check consistently.

#### CR-008: Workflow Python/tool assumptions need explicit verification

* Severity: Medium
* Status: Needs Claude verification
* Adversarial angle: External runtime compatibility
* Plan reference: Task 13 workflow.
* Finding: The repo package requires Python `>=3.14`, but the reusable drift workflow only installs `uv` and invokes `uvx`; it does not explicitly request Python 3.14. `setup-uv` supports a `python-version` input, and `uvx` supports `--python`. The plan should decide and test which mechanism guarantees the checker runs under a compatible Python.
* Repository evidence: `pyproject.toml` has `requires-python = ">=3.14"`. Task 13 workflow uses `setup-uv` plus `uvx --from ... project-standards check`, with no Python version input/flag.
* External research evidence: Astral’s `setup-uv` README documents `python-version`; `uv` docs say `uvx` is `uv tool run`, supports `--from` git sources, and tool environments have their own Python-version behavior.
* Why it matters: A consumer workflow should not depend on whatever interpreter happens to be present on `ubuntu-latest`.
* Recommended action for Claude Code: Verify `uvx --from git+... project-standards check` reliably selects/downloads Python 3.14 for this package, or specify `--python 3.14` / `setup-uv` `python-version: "3.14"`.
* Suggested validation: Add a workflow or local container smoke that prints `project-standards check --version` or Python version under the same command path.

### Missing considerations

* Blocking: Add a pre-implementation gate for current dirty tree, held `2.1.0`, and known red SSOT status.
* Blocking: Add local-edit promotion/removal rules for `--update --force` and `disk == tmpl` local-edits.
* Blocking: Add one-shot lock write, explicit final-lock failure messaging, and failure-injection tests.
* Blocking: Implement or revise the public JSON/fragments contract.
* Blocking: Fix strict typing/import/lint hazards in the task snippets.
* Non-blocking: Add CI warning/summary visibility for non-failing drift.
* Non-blocking: Update handoff pointer table and all affected adoption docs.
* Non-blocking: Verify Python 3.14 selection in reusable workflow execution.

### Internet research performed

* Source name: GitHub Docs — Reuse workflows  
  URL: https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows  
  Access date: 2026-06-08  
  What it was used to verify: Reusable workflow location and `jobs.<job_id>.uses` syntax.  
  Relevant conclusion: `.github/workflows/{file}@{ref}` caller syntax is valid; SHA is safest, tags/branches are allowed.

* Source name: GitHub Docs — Contexts reference  
  URL: https://docs.github.com/en/actions/reference/workflows-and-actions/contexts  
  Access date: 2026-06-08  
  What it was used to verify: `inputs` context in reusable workflows.  
  Relevant conclusion: `inputs.<name>` is available in workflows triggered by `workflow_call`.

* Source name: GitHub Docs — Expressions  
  URL: https://docs.github.com/en/actions/learn-github-actions/expressions  
  Access date: 2026-06-08  
  What it was used to verify: Use of `||` in expressions.  
  Relevant conclusion: GitHub Actions supports logical `||`, so the fallback expression shape is valid.

* Source name: Astral uv docs — Using tools  
  URL: https://docs.astral.sh/uv/guides/tools/  
  Access date: 2026-06-08  
  What it was used to verify: `uvx --from` with git refs.  
  Relevant conclusion: `uvx --from git+https://...@branch/tag/commit` is supported.

* Source name: Astral uv docs — Tools  
  URL: https://docs.astral.sh/uv/concepts/tools/  
  Access date: 2026-06-08  
  What it was used to verify: `uvx` tool environment behavior.  
  Relevant conclusion: `uvx` is an alias for `uv tool run`; tool environments use uv Python discovery and should have Python version behavior explicitly verified here.

* Source name: astral-sh/setup-uv README  
  URL: https://github.com/astral-sh/setup-uv  
  Access date: 2026-06-08  
  What it was used to verify: `setup-uv` inputs.  
  Relevant conclusion: `version`, `enable-cache`, and `python-version` inputs exist; the plan can pin Python explicitly.

* Source name: GitHub Marketplace — actions/checkout  
  URL: https://github.com/marketplace/actions/checkout  
  Access date: 2026-06-08  
  What it was used to verify: `actions/checkout@v6`.  
  Relevant conclusion: `@v6` exists; GitHub recommends `contents: read` permissions for checkout.

### Items Claude Code should verify before correcting the plan

* Whether `check` implementation is still held until `2.1.0` ships.
* Which current working-tree changes belong to the user versus this plan’s future implementation.
* Whether the current dirty drift spec is the authoritative contract or just formatting churn.
* Whether `uvx --from git+... project-standards check` reliably runs with Python 3.14 in a clean GitHub runner.
* Whether the public JSON contract should be the spec’s grouped `standards[]` schema or a newly revised flat schema.
* Which handoff docs are required by the repo’s v3 layout for implemented-but-not-tagged feature state.

### Suggested corrections for Claude Code's plan

* Add a preflight section before Task 1 for clean tree, release hold, and baseline gate status.
* Fix Task 11 imports and strict-gate issues before any code is written.
* Replace per-standard `merge_and_write` update restamping with a single in-memory lock rebuild plus one `write_lock`.
* Promote forced or template-matching `local_edits` into `artifacts`.
* Add tests for future-template-change behavior after `--update --force`.
* Implement the spec JSON shape or explicitly revise the spec.
* Add fragment `SKIPPED` reporting/tests.
* Implement CI summary/warning surfacing or make it an explicit follow-up outside acceptance.
* Add Python 3.14 workflow verification or pinning.
* Update `docs/handoff/specs-plans.md` and all relevant standard adoption docs.

### Read-only validation performed

* `pwd` confirmed repo root: `/home/chris/projects/project-standards`.
* `git branch --show-current` confirmed branch `testing`.
* `git log --oneline -n 10` confirmed the plan commit is current and recent.
* `git status --short` and `git diff --stat` established the dirty working tree and broad in-flight changes.
* `sed -n` read the full implementation plan.
* `sed -n` read the approved drift design spec, adopt engine, CLI, registry, manifest reader, errors, workflows, tests, changelog, and handoff pointer table.
* `rg --files` confirmed existing project structure and absence of `adopt/check.py`, `adopt/lock.py`, and the planned drift workflow/template.
* `rg -n` checked fragment/restamp/workflow references across plan, spec, source, tests, and existing workflows.
* `nl -ba` captured line-numbered evidence for the plan, spec, engine, manifests, pyproject, workflows, and handoff docs.
* `git diff -- docs/superpowers/plans/2026-06-08-check-drift.md` confirmed the plan file itself has no local diff.
* `git diff -- docs/superpowers/specs/2026-06-08-check-drift-design.md` showed the spec file is locally modified, mostly formatting but still current evidence.

### Recommended implementation validation

* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest`
* Run only after implementation: `uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`
* Run only after implementation: `uv build` plus the packaging test.
* Add targeted tests for local-edit force promotion, one-shot lock-write failure, fragments `SKIPPED`, full JSON schema, CI warning/summary behavior, and Python 3.14 workflow execution.

### Final recommendation

Claude Code should revise the plan using the findings above

### Review ledger for next loop

* Plan path: `/home/chris/projects/project-standards/docs/superpowers/plans/2026-06-08-check-drift.md`
* Audit round: 1
* Open issue IDs: CR-001, CR-002, CR-003, CR-004, CR-005, CR-006, CR-007, CR-008
* Resolved issue IDs:
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: preflight/release gating, Task 11 executability, local_edits promotion, single lock-write recovery, JSON/fragments contract, CI warning visibility, and Python 3.14 workflow verification.