### Executive summary

The revision resolves most round-1 findings, including the relock contradiction, manifest-vs-lock reconciliation, CI ref pinning, version-plane separation, exit-code coverage, JSON schema, and green-run warning visibility. Significant findings remain because the revised `--update` crash-safety model can still leave provenance under-stamped in a way that later misclassifies stale artifacts as `LOCAL-EDIT`, and the spec now references an undefined `resolvable-UNLOCKED` update category.

New internet research was required for the revised CI and GitHub Actions assumptions; official uv and GitHub docs support the corrected ref-pinned execution and warning/summary mechanisms.

### Verdict

Needs major specification correction before planning/implementation

### Audit loop status

* Audit type: Follow-up audit
* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-06-08-check-drift-design.md`
* Prior audit issue count: 9
* Resolved issue count: 8
* Still open issue count: 0
* Partially resolved issue count: 1
* New issue count: 1
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

Retested the revised state machine, relock table split, manifest-vs-lock reconciliation, lock schema, CLI flags, JSON output, update write ordering, CI ref pinning, and GitHub warning visibility against the current dirty worktree. Attacked acceptance criteria for false green outcomes after partial update failure, skipped/adopt-existing artifacts, relocked custom files, shared artifacts, and undefined update states.

Could not run tests, build, packaging, or validation gates because this audit is read-only and those commands may write caches or artifacts.

### Prior findings status

#### SA-001: `--relock` contradicts the state machine

* Previous severity: High
* Current status: Resolved
* Evidence: The spec now separates `[S.artifacts]` from `[S.local_edits]`; divergent relock files are accepted as `LOCAL-EDIT` and never evaluated as template-backed `STALE` (`lines 49-57`, `196-202`).
* Remaining action for Claude Code: None for the original contradiction.

#### SA-002: Lock-driven checking can miss newly-added or skipped artifacts

* Previous severity: High
* Current status: Resolved
* Evidence: The spec now makes standards lock-driven but artifacts manifest-driven, including lock-only reconciliation (`lines 35`, `45-70`). Adopt-skipped files are explicitly `UNLOCKED` or `CLEAN` at check time (`line 180`).
* Remaining action for Claude Code: None for the original gap.

#### SA-003: `--update` lacks write-safety and lock-consistency rules

* Previous severity: High
* Current status: Partially resolved
* Evidence: Write safety is now specified: `validate_dest`, symlink guards, `_atomic_write`, file-first/lock-last ordering, and failure tests are required (`lines 182-190`, `229-230`). However, the crash-safety rule still permits an under-stamped lock to go green: if update writes disk bytes matching the current template but the final lock write fails, the next `check` reports `CLEAN` because `disk == tmpl` (`lines 63`, `73`, `188-189`). On a later template change, that same file has `disk != tmpl` and `disk != old lock_hash`, so the state machine reports `LOCAL-EDIT` (`line 67`) instead of `STALE`.
* Remaining action for Claude Code: Define a restamp-needed state or another lock-repair rule for `disk == tmpl` with stale/missing lock metadata, and explicitly define read-only symlink classification instead of only saying “symlink guards.”

#### SA-004: CI command is not pinned to the workflow ref

* Previous severity: High
* Current status: Resolved
* Evidence: The spec now requires `standards-ref` and `uvx --from "git+https://github.com/L3DigitalNet/project-standards@${{ inputs.standards-ref || 'v2' }}" project-standards check` (`lines 206-215`).
* Remaining action for Claude Code: None for the original pinning gap.

#### SA-005: Lockfile version fields conflate contract versions and tool releases

* Previous severity: High
* Current status: Resolved
* Evidence: The lockfile now has `lockfile_version`, top-level `tool_version`, and per-standard `contract_version`, matching repo version grammar in `meta/versioning.md` and `registry.json` (`lines 90-99`).
* Remaining action for Claude Code: None.

#### SA-006: Exit-code contract omits existing `ManifestError` exit 3

* Previous severity: Medium
* Current status: Resolved
* Evidence: Exit code `3` is now explicitly assigned to `ManifestError`, matching `adopt/errors.py` (`spec line 162`; repo `src/project_standards/adopt/errors.py:19-24`).
* Remaining action for Claude Code: None.

#### SA-007: Initial lockfile format is “versioned” but has no version field

* Previous severity: Medium
* Current status: Resolved
* Evidence: The lock example and versioning impact now include `lockfile_version = 1`, and unsupported/missing versions map to `LockError` exit 2 (`lines 90-95`, `115`, `259`).
* Remaining action for Claude Code: None.

#### SA-008: Machine-readable output and option combinations are under-specified

* Previous severity: Medium
* Current status: Resolved
* Evidence: The spec now includes a flag-combination matrix and a concrete JSON schema with artifact owners, fragments, summary counts, and exit code (`lines 134-159`).
* Remaining action for Claude Code: None for the original issue.

#### SA-009: CI warning-only `LOCAL-EDIT` output may be invisible

* Previous severity: Medium
* Current status: Resolved
* Evidence: The spec now requires `$GITHUB_STEP_SUMMARY` output and `::warning::` annotations for `LOCAL-EDIT`/`ORPHAN` on green runs (`line 217`).
* Remaining action for Claude Code: None.

### New blocking issues

None found.

### New non-blocking issues

#### SA-NEW-001: `resolvable-UNLOCKED` has no state-machine definition

* Severity: Medium
* Status: Confirmed
* Adversarial angle: `--update` can be implemented with invented overwrite semantics for unproven files.
* Spec reference: `lines 33`, `65-66`, `86`, `128`, `229`
* Finding: The state machine defines `UNLOCKED` only as “present, differs from current, no baseline.” The spec then says `--update` re-syncs `resolvable-UNLOCKED` artifacts while skipping “present-but-divergent `UNLOCKED`,” but no other `UNLOCKED` form exists.
* Repository evidence: Existing `adopt` skips present files without `--force` (`src/project_standards/adopt/engine.py:225-228`), so manifest artifacts absent from the lock are realistic. The current repo has no `check` implementation to clarify this term.
* External research evidence: Not applicable.
* Why it matters: Claude Code could either overwrite unknown present files without proof of ownership or fail to update an intended recoverable case. The acceptance tests cannot be precise while the state is undefined.
* Recommended action for Claude Code: Define the category or remove it. If the intended case is absent new artifacts, call it `MISSING`; if it is present and divergent with no baseline, require `--force`.
* Suggested validation: Fixture three absent-from-lock cases: absent on disk, present and equal to template, present and divergent. Assert default, `--update`, and `--update --force` behavior.

### Regressions

None found.

### Remaining ambiguities and decisions needed

* Ambiguity: Should `disk == tmpl` with stale or missing lock metadata be plain `CLEAN`, or should it require/restamp lock metadata before CI can go green?
  * Why it matters: Plain `CLEAN` can make later upstream template drift look like `LOCAL-EDIT` instead of `STALE`.
  * Recommended clarification: Add a lock-restamp rule/state and acceptance tests for final lock-write failure followed by a later template change.
  * Blocking or non-blocking: Blocking.

* Ambiguity: What exact state/exit code should read-only `check` use for symlinked leaf or symlinked ancestor destinations?
  * Why it matters: The spec says to use symlink guards, but the state table has no symlink state; following symlinks during hashing could read outside `--dest`.
  * Recommended clarification: Define symlinked destinations as a clear failure state or I/O/path-safety error, with no target-byte hashing.
  * Blocking or non-blocking: Blocking.

* Ambiguity: What is `resolvable-UNLOCKED`?
  * Why it matters: It changes whether `--update` can write a file with no provenance baseline.
  * Recommended clarification: Replace the term with defined states from the table.
  * Blocking or non-blocking: Non-blocking.

### Internet research performed

* Source name: uv Tools concept docs
  * URL: https://docs.astral.sh/uv/concepts/tools/
  * Access date: 2026-06-08
  * What it was used to verify: `uvx` isolation, cache/latest behavior, and why unpinned tool execution is unsafe for ref-aligned CI.
  * Relevant conclusion: The revised spec correctly rejects plain `uvx project-standards check`.

* Source name: uv Using tools guide
  * URL: https://docs.astral.sh/uv/guides/tools/
  * Access date: 2026-06-08
  * What it was used to verify: `uvx --from git+...@ref` support.
  * Relevant conclusion: The revised ref-pinned command is supported by official uv docs.

* Source name: GitHub Actions reusable workflows docs
  * URL: https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows
  * Access date: 2026-06-08
  * What it was used to verify: reusable workflow calls by `uses: owner/repo/.github/workflows/file.yml@ref` and input passing.
  * Relevant conclusion: The spec’s caller/ref model matches GitHub’s workflow model.

* Source name: GitHub Actions workflow commands docs
  * URL: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands
  * Access date: 2026-06-08
  * What it was used to verify: warning annotations and `$GITHUB_STEP_SUMMARY`.
  * Relevant conclusion: The revised green-run visibility requirement is technically supported.

### Read-only validation performed

* `pwd`: confirmed repository root.
* `git branch --show-current`, `git status --short`, `git log --oneline -n 10`, `git show --stat --oneline --no-renames -1`: confirmed branch `testing`, dirty worktree, and latest spec-review correction commit.
* `git diff --stat`, `git diff --name-only`: confirmed unrelated in-flight changes and no uncommitted spec edit.
* `rg --files`: discovered relevant source, tests, workflows, bundles, and docs.
* `nl -ba` on the spec: re-inventoried requirements and line references.
* `rg -n` on the spec for state/update/lock terms: found the undefined `resolvable-UNLOCKED` references.
* `nl -ba` on `adopt/engine.py`, `manifest.py`, `errors.py`, `cli.py`, `registry.json`, bundle `adopt.toml` files, workflow templates, `meta/versioning.md`, `pyproject.toml`, and adopt tests: checked repository fit for manifests, path safety, exit codes, version planes, workflow patterns, and existing test conventions.
* `rg -n 'kind = "(file|workflow-caller|fragment)"' src/project_standards/bundles/*/adopt.toml`: verified current artifact classes/counts from manifests.

### Recommended planning/implementation validation

* Run only after implementation: full SSOT gate: `uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit`.
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`.
* Run only after implementation: fixture tests for final lock-write failure, rerun restamp behavior, later-template-change classification, symlinked read paths, and all absent-from-lock artifact states.
* Run only after implementation: workflow rendering check that caller and reusable drift workflows use the same major ref and emit summaries/warnings for green `LOCAL-EDIT`.

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-06-08-check-drift-design.md`
* Audit round: 2
* Open issue IDs: SA-003, SA-NEW-001
* Resolved issue IDs: SA-001, SA-002, SA-004, SA-005, SA-006, SA-007, SA-008, SA-009
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: update crash/restamp semantics, read-only symlink classification, and removal or definition of `resolvable-UNLOCKED`.