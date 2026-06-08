### Executive summary

The specification is not ready for Claude Code to use for planning or implementation. The core lock/state model has a blocking contradiction: `--relock` cannot both hash current disk bytes and then report those bytes as clean under the specified state machine. Additional blocking gaps remain around newly-added manifest artifacts, safe `--update`, CI version pinning, and the lockfile version fields.

Internet research was required for the CI/`uvx` assumption. Official uv docs confirm `uvx` runs tools from ephemeral/cached tool environments and defaults to package-name resolution/latest behavior unless a version/source is specified; GitHub docs confirm reusable workflows are pinned by `@ref`.

### Verdict

Needs major specification correction before planning/implementation

### Audit loop status

* Audit type: First audit
* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-06-08-check-drift-design.md`
* Significant findings remaining: Yes
* Blocking issue count: 5
* Non-blocking issue count: 4

### What the specification gets right

* Correctly identifies copy-adopt staleness as the lifecycle gap after `adopt`.
* Correctly keeps fragments out of Phase 1; current manifests have 15 `file`/`workflow-caller` artifacts and 2 `fragment` artifacts.
* Correctly anchors `check` inside the `adopt/` package so rendering, manifest resolution, and path safety can share existing code.
* Correctly requires `LOCAL-EDIT` to be advisory instead of overwriting consumer-owned changes by default.

### Adversarial review performed

I inventoried the state machine, lockfile contract, CLI flags, update/relock flows, CI delivery, versioning impact, tests, current manifests, current adopt engine behavior, and existing workflow patterns. I falsified the main requirements against current repo evidence in `src/project_standards/adopt/`, `src/project_standards/bundles/**/adopt.toml`, `src/project_standards/cli.py`, `.github/workflows/*.yml`, `meta/versioning.md`, and tests.

Could not run tests or build commands because this audit is read-only and those commands may write caches/artifacts.

### Blocking issues

#### SA-001: `--relock` contradicts the state machine

* Severity: High
* Status: Confirmed
* Adversarial angle: Bootstrap path can pass its own acceptance criteria without actually producing a clean baseline.
* Spec reference: `Component 1` says `disk_hash == lock_hash` and `disk_hash != tmpl_hash` means `STALE`; `Component 6` says `--relock` hashes current disk files and baselines drifted files as clean.
* Finding: These cannot both be true. If a previously adopted file was locally edited and no longer matches the current template, `--relock` records `lock_hash = disk_hash`; the next `check` sees `disk_hash != tmpl_hash` and `disk_hash == lock_hash`, so it reports `STALE`, not clean.
* Repository evidence: Current manifests include existing copy-adopt artifacts that existing repos may already have drifted; see `src/project_standards/bundles/*/adopt.toml`. The spec’s state machine is internally inconsistent at [2026-06-08-check-drift-design.md](/home/chris/projects/project-standards/docs/superpowers/specs/2026-06-08-check-drift-design.md:49) and relock claim at [2026-06-08-check-drift-design.md](/home/chris/projects/project-standards/docs/superpowers/specs/2026-06-08-check-drift-design.md:127).
* External research evidence: Not applicable.
* Why it matters: Existing adopters get the advertised zero-clobber migration path, but it immediately reports stale for customized files.
* Recommended action for Claude Code: Redesign or explicitly narrow `--relock`: either refuse non-current files, baseline them as `LOCAL-EDIT`, or add enough lock metadata to distinguish accepted local baselines from stale upstream templates.
* Suggested validation: Fixture with a disk file that differs from the current template; run `check --relock markdown-tooling`, then `check`, and assert the documented state and exit code.

#### SA-002: Lock-driven checking can miss newly-added or skipped artifacts

* Severity: High
* Status: Confirmed
* Adversarial angle: Upstream can add a new artifact and `check` can still pass because the artifact is not in the old lock.
* Spec reference: Plain `check` is lock-driven, `adopt` only merges written artifacts, and “not in the lock = not checked.”
* Finding: The spec does not define what happens when a locked standard’s current manifest contains a whole-file artifact absent from the lock. It also does not define what happens when `adopt` skips an existing file and therefore does not lock it.
* Repository evidence: `execute_plan` skips existing files by default at [engine.py](/home/chris/projects/project-standards/src/project_standards/adopt/engine.py:225). Component 5 says only written artifacts are merged into the lock at [2026-06-08-check-drift-design.md](/home/chris/projects/project-standards/docs/superpowers/specs/2026-06-08-check-drift-design.md:121). Current manifests are the stated source of truth and contain all artifact destinations.
* External research evidence: Not applicable.
* Why it matters: A consumer could miss a new required scaffold or keep a partially adopted standard forever while `check` ignores the gap.
* Recommended action for Claude Code: Specify manifest-vs-lock reconciliation for locked standards: new current artifacts, removed artifacts, renamed destinations, and skipped-at-adopt files.
* Suggested validation: Create a lock missing one current `markdown-tooling` artifact; `check` must report the documented state and exit code.

#### SA-003: `--update` lacks write-safety and lock-consistency rules

* Severity: High
* Status: Confirmed
* Adversarial angle: A failed update can leave disk and lock inconsistent, producing false green or unsafe writes.
* Spec reference: `--update` re-syncs stale artifacts and re-stamps the lock; tests only mention re-stamping updated dests.
* Finding: The spec does not define symlink handling, atomic writes, lock write ordering, rollback behavior, or partial failure semantics for `check --update`.
* Repository evidence: Existing `adopt` code has explicit symlink refusal and atomic writes at [engine.py](/home/chris/projects/project-standards/src/project_standards/adopt/engine.py:181) and [engine.py](/home/chris/projects/project-standards/src/project_standards/adopt/engine.py:220), with regression tests in [test_adopt_safety.py](/home/chris/projects/project-standards/tests/test_adopt_safety.py:43). The check spec does not carry those guarantees into update.
* External research evidence: Not applicable.
* Why it matters: If lock is advanced before a file update fails, a stale file can be misclassified as `LOCAL-EDIT` and exit 0. Symlinked paths can also escape the consumer repo unless explicitly refused.
* Recommended action for Claude Code: Specify that `apply_update` uses the same path/symlink/atomic-write protections as `adopt`, and define lock-write ordering plus failure outcomes.
* Suggested validation: Failure-injection tests for file write failure, lock write failure, symlink leaf, symlink parent, and mixed multi-file updates.

#### SA-004: CI command is not pinned to the workflow ref

* Severity: High
* Status: Confirmed
* Adversarial angle: A consumer pinned to `@v2` can run a different `project-standards` package version.
* Spec reference: CI delivery says the reusable workflow runs `uvx project-standards check`.
* Finding: `uvx project-standards check` does not specify a git ref or package version. The existing reusable validator workflow installs from `git+https://github.com/L3DigitalNet/project-standards@${{ inputs.standards-ref }}` to keep the runtime aligned with the workflow pin.
* Repository evidence: Current validator workflow has a `standards-ref` input and installs the package from the matching git ref at [validate-markdown-frontmatter.yml](/home/chris/projects/project-standards/.github/workflows/validate-markdown-frontmatter.yml:35) and [validate-markdown-frontmatter.yml](/home/chris/projects/project-standards/.github/workflows/validate-markdown-frontmatter.yml:83).
* External research evidence: uv docs state `uvx` is `uv tool run`, runs in an isolated tool environment, and uses latest/cached behavior unless a version/source is requested: https://docs.astral.sh/uv/concepts/tools/ accessed 2026-06-08. uv docs also show `--from git+...@tag` for alternate sources: https://docs.astral.sh/uv/guides/tools/ accessed 2026-06-08. GitHub docs require reusable workflow calls to use `@ref`: https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows accessed 2026-06-08.
* Why it matters: Drift detection depends on the bundled manifests/templates for the same release the consumer intended to run.
* Recommended action for Claude Code: Add a `standards-ref` input and specify a ref-pinned `uvx --from git+https://github.com/L3DigitalNet/project-standards@${{ inputs.standards-ref }} project-standards check`.
* Suggested validation: Inspect rendered caller workflow and reusable workflow; assert both use the same major ref.

#### SA-005: Lockfile version fields conflate contract versions and tool releases

* Severity: High
* Status: Confirmed
* Adversarial angle: The lock’s data contract can be implemented with the wrong version plane.
* Spec reference: Lock example uses `contract = "2.0.0"` and reason text `adopted 2.0.0, bundle 2.1.0`.
* Finding: Repo versioning defines per-standard contract versions as `major.minor` (`1.0`, `1.1`) and tool releases as full SemVer (`2.0.0`, `2.1.0`). The spec does not say whether the lock records the per-standard contract, tool package version, git ref, or all of them.
* Repository evidence: `meta/versioning.md` separates contract plane and tool release plane at [meta/versioning.md](/home/chris/projects/project-standards/meta/versioning.md:49). `registry.json` currently stores `1.1` and `1.0`, not `2.x.y`, at [registry.json](/home/chris/projects/project-standards/src/project_standards/schemas/registry.json:1).
* External research evidence: Not applicable.
* Why it matters: Human drift messages, future migrations, and lock compatibility depend on a precise version schema.
* Recommended action for Claude Code: Define lock fields explicitly, e.g. `contract_version`, `tool_version` or `bundle_ref`, and correct all examples.
* Suggested validation: Lock fixture asserts current registry contract values and installed package/ref metadata separately.

### Non-blocking issues

#### SA-006: Exit-code contract omits existing `ManifestError` exit 3

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Check may not be “consistent with existing CLIs” as claimed.
* Spec reference: Check exit codes list only `0`, `1`, and `2`.
* Finding: Existing adopt errors include `ManifestError` with exit code `3` for missing manifests/templates or unresolvable package version.
* Repository evidence: [errors.py](/home/chris/projects/project-standards/src/project_standards/adopt/errors.py:19) defines `ManifestError.exit_code = 3`; `cli.main` returns `exc.exit_code` at [cli.py](/home/chris/projects/project-standards/src/project_standards/cli.py:157).
* External research evidence: Not applicable.
* Why it matters: Bundle/source failures are realistic for `check` because it reads the same manifests and templates.
* Recommended action for Claude Code: Either include exit `3` in `check` or explicitly justify remapping manifest/package failures to `2`.
* Suggested validation: Broken manifest/source fixture for `project-standards check`.

#### SA-007: Initial lockfile format is “versioned” but has no version field

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Future lock migrations require guessing the initial format.
* Spec reference: Versioning impact says `lockfile_version` is reserved for future format changes.
* Finding: The TOML example does not include `lockfile_version`, even though the spec calls the lock format a versioned surface.
* Repository evidence: No existing lock implementation exists; the proposed format begins directly with `[markdown-tooling]`.
* External research evidence: Not applicable.
* Why it matters: The first shipped lock format should be self-identifying before consumers commit it across repos.
* Recommended action for Claude Code: Include `lockfile_version = 1` from the first release and specify unsupported-version behavior.
* Suggested validation: Load tests for supported, missing, and future lockfile versions.

#### SA-008: Machine-readable output and option combinations are under-specified

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Automation consumers can pass acceptance with an unstable JSON shape.
* Spec reference: `--json` “mirrors list --json”; `--quiet`, `--force`, `--update`, and `--relock` interactions are not fully defined.
* Finding: The spec does not define JSON fields, per-artifact schema, dedupe representation, skipped fragments, summary status, or invalid flag combinations such as `--force` without `--update`.
* Repository evidence: `list --json` has a stable schema tested in [test_adopt_cli.py](/home/chris/projects/project-standards/tests/test_adopt_cli.py:20). No equivalent schema is specified for check.
* External research evidence: Not applicable.
* Why it matters: CI and future tooling need stable output; ambiguous flags lead to argparse behavior becoming accidental contract.
* Recommended action for Claude Code: Specify JSON schema and invalid/valid flag matrix.
* Suggested validation: Snapshot-style unit tests for JSON output and CLI combination tests.

#### SA-009: CI warning-only `LOCAL-EDIT` output may be invisible

* Severity: Medium
* Status: Unclear
* Adversarial angle: Acceptance can pass while users never notice local divergence.
* Spec reference: `LOCAL-EDIT` exits 0 and CI runs `check`.
* Finding: The spec does not require warnings to be surfaced in GitHub Actions annotations or step summary. Because exit is 0, CI can go green while drift warnings are buried in logs.
* Repository evidence: Existing workflows use plain shell steps; no annotation/summary pattern is defined for drift check.
* External research evidence: GitHub reusable workflow docs confirm called workflows are ordinary jobs with inputs; they do not automatically elevate successful-step output into annotations.
* Why it matters: The goal is to tell consumers about hand-edited copies, not merely print text that may never be read.
* Recommended action for Claude Code: Decide whether CI should emit a step summary or warning annotations for `LOCAL-EDIT`.
* Suggested validation: Workflow test or documented manual check showing local edits are visible on a green run.

### Missing specification considerations

* Blocking: Define relock semantics for customized files, missing files, and partially adopted standards.
* Blocking: Define manifest-vs-lock reconciliation for added, removed, or renamed artifacts.
* Blocking: Define transactional behavior for `--update`, including lock write ordering and partial failures.
* Blocking: Define symlink behavior for both read-only checking and update writes.
* Blocking: Define CI install/version pinning so the checker uses the same bundle ref as the workflow.
* Non-blocking: Define JSON output schema and flag-combination behavior.
* Non-blocking: Include `lockfile_version` from the first format.
* Non-blocking: Derive artifact counts from manifests in tests instead of hardcoding `15` and `2`.
* Non-blocking: Decide how CI exposes `LOCAL-EDIT` warnings when exit code remains 0.

### Ambiguities and decisions needed

* Ambiguity: Should `--relock` make non-current disk files `CLEAN`, `LOCAL-EDIT`, or fail?
  * Why it matters: This determines the lock data model.
  * Recommended clarification: Pick one behavior and make the state machine satisfy it.
  * Blocking or non-blocking: Blocking.
* Ambiguity: Are current-manifest artifacts absent from the lock checked?
  * Why it matters: Added artifacts are a common form of upstream drift.
  * Recommended clarification: Add a state such as `UNLOCKED`, `NEW`, or `MISSING-FROM-LOCK`.
  * Blocking or non-blocking: Blocking.
* Ambiguity: Does `contract` mean per-standard contract version or tool release?
  * Why it matters: Current repo has both version planes.
  * Recommended clarification: Rename and split fields.
  * Blocking or non-blocking: Blocking.

### Internet research performed

* Source name: uv Tools concept docs
  * URL: https://docs.astral.sh/uv/concepts/tools/
  * Access date: 2026-06-08
  * What it was used to verify: `uvx` execution, caching, default version behavior.
  * Relevant conclusion: Plain `uvx project-standards check` is not inherently pinned to the workflow ref.
* Source name: uv Using tools guide
  * URL: https://docs.astral.sh/uv/guides/tools/
  * Access date: 2026-06-08
  * What it was used to verify: `--from git+...@tag` support.
  * Relevant conclusion: The workflow can run the command from an explicit git ref.
* Source name: GitHub Actions reusable workflows docs
  * URL: https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows
  * Access date: 2026-06-08
  * What it was used to verify: reusable workflow syntax and `@ref` behavior.
  * Relevant conclusion: Caller workflows pin reusable workflows by ref; runtime package install should align with that ref.

### Items Claude Code should verify before correcting the specification

* Confirm whether `--relock` is intended to accept local customizations silently, warn about them, or fail.
* Confirm whether newly added artifacts in a locked standard should fail CI.
* Confirm desired behavior for artifacts removed from the current manifest but still present in the lock.
* Confirm whether the drift workflow should install from git ref, PyPI, or both with a documented precedence.
* Confirm whether initial lock files should include `lockfile_version = 1`.

### Suggested corrections for Claude Code’s specification

* Redesign the lock/state model so `--relock` behavior is mathematically consistent.
* Add manifest-vs-lock reconciliation states and acceptance criteria.
* Expand `--update` safety requirements to match adopt’s symlink and atomic-write guarantees.
* Replace `uvx project-standards check` with a ref-pinned install/run pattern.
* Split lock metadata into explicit lockfile, contract, and tool/bundle version fields.
* Define JSON output schema, flag combinations, and all exit codes including manifest/package failures.
* Add tests for relock-customized, added-artifact, removed-artifact, symlink-update, and lock-write-failure cases.

### Read-only validation performed

* `pwd`: confirmed repository root is `/home/chris/projects/project-standards`.
* `git branch --show-current`: confirmed branch `testing`.
* `git status --short`: confirmed dirty working tree with 17 modified files.
* `git log --oneline -n 10`: confirmed latest spec commit and adopt CLI history.
* `sed -n` / `nl -ba` on the spec: inventoried all requirements and line references.
* `rg --files`: discovered repository structure.
* `nl -ba` on `cli.py`, `adopt/engine.py`, `adopt/manifest.py`, `adopt/errors.py`: verified current CLI, manifest, path-safety, render, and exit-code behavior.
* `nl -ba` on all `src/project_standards/bundles/*/adopt.toml`: verified 17 artifacts, 15 checkable whole-file artifacts, 2 fragments.
* `nl -ba` on workflows, tests, `meta/versioning.md`, `README.md`, and `CHANGELOG.md`: checked current CI, testing, and versioning conventions.
* `git diff --stat` and `git diff --name-only`: confirmed audit evidence comes from a dirty worktree.

### Recommended planning/implementation validation

* Run only after implementation: full SSOT gate: `uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit`.
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`.
* Run only after implementation: wheel packaging check that bundles, lock/check modules, and reusable workflow are present.
* Run only after implementation: fixture tests for clean adopt/check, relock customized files, added artifacts, removed artifacts, missing artifacts, symlinked destinations, update failures, corrupt lock, and JSON output.

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-06-08-check-drift-design.md`
* Audit round: 1
* Open issue IDs: SA-001, SA-002, SA-003, SA-004, SA-005, SA-006, SA-007, SA-008, SA-009
* Resolved issue IDs:
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: the revised state machine/lock schema, relock semantics, manifest-vs-lock reconciliation, update safety, and CI package-ref pinning.