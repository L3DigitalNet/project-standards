### Executive summary

Claude Code’s revisions resolved the parent-symlink write-boundary gap, the uv lockfile omission, and the ADR existing-config validation gap. Significant findings still remain because the registry/bundle drift guard is still only partial, and this revision exposes a release-process issue: the plan separates the version bump from the changelog/release commit and tells Claude to mark handoff/deployment docs as released before the user-approved tag exists.

New internet research was performed against official Python and uv documentation; it did not introduce new conflicts with the symlink or lockfile fixes.

### Verdict

Needs minor correction before execution

### Audit loop status

* Audit type: Follow-up audit
* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-06-08-adopt-cli.md
* Prior audit issue count: 8
* Resolved issue count: 7
* Still open issue count: 0
* Partially resolved issue count: 1
* New issue count: 1
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

Re-read the revised plan, the approved design spec, git status/history, repo instructions, handoff state/conventions, release/versioning docs, current deployed/specs-plan state, changelog format, package metadata, lockfile, CI workflow, registry code/data, validator include/exclude behavior, ADR template, frontmatter example, current symlink shape, and prior findings.

Retested the prior fixes for recoverable I/O mapping, executable validation fixtures, malformed manifest/list no-traceback behavior, JSON `contract_version`, multi-fragment reporting, symlink parent safety, uv lockfile inclusion, and ADR template-exclusion validation. Attacked validation false positives around registry/bundle drift, release-state truth, and pre-tag handoff updates.

No tests, builds, `uv sync`, `uv lock`, formatters, package installs, generators, or tag commands were run because this audit is read-only and those commands may write lockfiles, caches, build artifacts, environments, or git state.

### Prior findings status

#### CR-001: Recoverable I/O failures can still escape as tracebacks

* Previous severity: High
* Current status: Resolved
* Evidence: The plan maps source reads, fragment reads, mkdir/mkstemp/write/replace failures, and source read failures through `WriteError` in the planned engine code, with failure-injection tests for `mkstemp`, unreadable sources, and failed replace.
* Remaining action for Claude Code: Preserve those error boundaries during implementation.

#### CR-002: Adoption validation test is not executable as written

* Previous severity: High
* Current status: Resolved
* Evidence: The D1 validation test now writes a real managed `docs/guide.md` from a shipped valid example, changes into the temp repo, calls `validate_frontmatter.main(["--config", ".project-standards.yml"])`, asserts `rc == 0`, and asserts stdout contains `"validated"`.
* Remaining action for Claude Code: Keep the non-vacuous fixture and stdout assertion.

#### CR-003: Invalid-manifest and list error paths do not satisfy the no-traceback contract

* Previous severity: High
* Current status: Resolved
* Evidence: `load_manifest()` validates non-string `source`, `shared`, `dest`, and `target` values before constructing `Artifact`; `list` now runs inside the `RegistryError` / `AdoptError` boundary and has a clean malformed-manifest test.
* Remaining action for Claude Code: Preserve the CLI error boundary for both `list` and `adopt`.

#### CR-004: `list --json` omits the spec’s stable `contract_version` field

* Previous severity: Medium
* Current status: Partially resolved
* Evidence: `list --json` now emits `contract_version`, and `list` fails cleanly if an adoptable bundle has no registry contract version. However, runtime drift handling is still one-directional: `_cmd_list()` derives entries from `available_standards()`, so a registry-known standard missing from bundles can be silently omitted at runtime, and `build_plan()`/`adopt` still uses `available_standards()` as the sole valid-id source with no registry cross-check.
* Remaining action for Claude Code: Add a runtime registry/bundle equality guard used by both `list` and `adopt`, or derive adoptable IDs from one registry-backed mapping and fail cleanly when bundles and registry diverge in either direction.

#### CR-005: Fragment reporting cannot represent multiple fragments for one target

* Previous severity: Medium
* Current status: Resolved
* Evidence: `Report.fragments` is now `dict[str, list[str]]`; `execute_plan()` appends snippets per target; `format_report()` prints each snippet; and the same-target multi-fragment regression test is present.
* Remaining action for Claude Code: None.

#### CR-NEW-001: Destination safety resolves away symlinks before checking them

* Previous severity: High
* Current status: Resolved
* Evidence: The plan now keeps the leaf unresolved, checks the leaf symlink, checks existing parent symlinks with `_has_symlinked_ancestor()`, and adds a regression test where `--dest/linkdir` points outside and `linkdir/f.txt` is skipped without writing outside `--dest`.
* Remaining action for Claude Code: Keep both leaf and ancestor symlink tests.

#### CR-NEW-002: Version bump omits the lockfile update needed by this uv project

* Previous severity: High
* Current status: Resolved
* Evidence: C2 now modifies `uv.lock`, runs `uv lock && uv lock --check`, uses `uv sync --locked --all-groups`, and stages `pyproject.toml uv.lock` together. This matches the repo’s locked CI gate.
* Remaining action for Claude Code: Preserve the lock freshness check and commit `uv.lock` with the version bump.

#### CR-NEW-003: ADR existing-config safety test can pass with only comment-level exclusion guidance

* Previous severity: Medium
* Current status: Resolved
* Evidence: The ADR fragment now labels the template exclusion as required, and D1 adds a test proving that an existing config including `docs/**/*.md` validates after applying the `**/*.template.md` exclusion.
* Remaining action for Claude Code: Keep the existing-config validation test and make the report wording unambiguous for operators.

### New blocking issues

None found.

### New non-blocking issues

#### CR-NEW-004: Release-state steps conflict with the repo’s release contract

* Severity: Medium
* Status: Confirmed
* Adversarial angle: Release sequencing, deployment truth, and handoff-state accuracy.
* Plan reference: C2 lines 1570-1600; E2 lines 1941-1984; E3 lines 1986-1988.
* Finding: The plan bumps `pyproject.toml`/`uv.lock` in C2, then later adds the changelog and marks handoff/deployment state as released in E2, while E3 says tagging happens only if the user asks. That conflicts with the repo’s release contract requiring the version bump, lockfile regeneration, and changelog in the release commit, and it would make `deployed.md` / `specs-plans.md` claim `2.1.0` is released before a published git ref exists.
* Repository evidence: `meta/versioning.md` says every release must tag a full version, advance the moving major tag, bump `pyproject.toml` and regenerate `uv.lock` in the release commit, and update the changelog in the same commit. `docs/handoff/deployed.md` defines “Deployed” as published git refs on `main`; current tags are only `v2.0.0` and `v2`. The current changelog format includes a dated version heading, while the plan’s new heading is only `## [2.1.0]`.
* External research evidence: Not applicable.
* Why it matters: Future agents or consumers could trust false deployment state, try to use `v2.1.0` before it exists, or tag a release that does not match the repo’s own release requirements.
* Recommended action for Claude Code: Revise the plan so implementation docs say “implemented, pending release” until the user approves tagging. Either move the version bump, `uv.lock`, and changelog into one final release-prep commit, or explicitly document why this release is intentionally split. Do not mark `deployed.md` or `specs-plans.md` as released until the tag and moving `v2` update actually happen. Include the dated changelog heading and the session row expected by the handoff layout.
* Suggested validation: Before marking release state, verify `git tag --list 'v2*'` and `git tag --points-at HEAD`; after user-approved release, verify `v2.1.0` and `v2` point at the intended release commit and that `deployed.md` matches those refs.

### Regressions

None found.

### Internet research performed

* Source name: Python `pathlib` documentation
* URL: https://docs.python.org/3/library/pathlib.html
* Access date: 2026-06-08
* What it was used to verify: Current symlink/path behavior relevant to `Path.resolve()`, `Path.is_symlink()`, `Path.mkdir()`, and ancestor checks.
* Relevant conclusion: The revised parent-symlink guard is directionally correct; symlinked ancestors need explicit checking before mkdir/mkstemp/replace.

* Source name: Python `tempfile.mkstemp` documentation
* URL: https://docs.python.org/3/library/tempfile.html#tempfile.mkstemp
* Access date: 2026-06-08
* What it was used to verify: `mkstemp(dir=...)` creates the temp file in the supplied directory.
* Relevant conclusion: Checking symlinked parents before calling `mkstemp(dir=target.parent)` is necessary and now planned.

* Source name: Astral uv locking and syncing documentation
* URL: https://docs.astral.sh/uv/concepts/projects/sync/
* Access date: 2026-06-08
* What it was used to verify: uv lockfile freshness and locked sync behavior.
* Relevant conclusion: The plan’s new `uv lock`, `uv lock --check`, and `uv sync --locked --all-groups` steps are appropriate.

* Source name: Astral uv CLI reference
* URL: https://docs.astral.sh/uv/reference/cli/#uv-lock
* Access date: 2026-06-08
* What it was used to verify: `uv lock --check` semantics.
* Relevant conclusion: `uv lock --check` asserts the lockfile would remain unchanged and exits if it is missing or stale.

### Read-only validation performed

* `pwd`, `git status --short`, `git branch --show-current`, `git log --oneline -n 10`, `git remote -v`, `git diff --stat`: confirmed repo root, branch `testing`, modified plan file only, untracked prior review artifacts, canonical origin, and recent plan/spec commits.
* Inspected `docs/handoff/state.md`, `AGENTS.md`, and `docs/handoff/conventions.md`: confirmed v3 layout, repo working rules, and validation expectations.
* Inspected the current plan with `nl`, `sed`, `rg`, and `git diff`: retested all prior issue areas and identified the release-state sequencing issue.
* Inspected `docs/superpowers/specs/2026-06-08-adopt-cli-design.md`: compared current plan behavior against the approved CLI, safety, packaging, validation, and versioning requirements.
* Inspected `pyproject.toml`, `uv.lock`, and `.github/workflows/check.yml`: confirmed current version `2.0.0`, lockfile project version `2.0.0`, and CI’s `uv sync --locked --all-groups`.
* Inspected `registry.py`, `registry.json`, `validate_frontmatter.py`, `.project-standards.yml`, ADR template, and frontmatter example: checked registry/default-version assumptions and ADR template-exclusion validation.
* Ran `find . -maxdepth 4 -type l -ls`: checked current repo symlinks while reasoning about destination safety.
* Inspected `meta/versioning.md`, `CHANGELOG.md`, `docs/handoff/deployed.md`, `docs/handoff/specs-plans.md`, `docs/handoff/sessions/2026-06.md`, and `git tag --list 'v2*'`: found the release-contract mismatch and current published refs.
* Ran a read-only Python `fnmatch.fnmatchcase` check: confirmed `docs/decisions/adr.template.md` matches `**/*.template.md`.

### Recommended implementation validation

* Run only after correction/implementation: add runtime drift tests for both directions: extra bundle without registry entry and registry-known standard missing its bundle; verify both `list` and `adopt` fail cleanly.
* Run only after correction/implementation: run the parent-symlink test where `dest_root/linkdir` points outside and `linkdir/file` is never written.
* Run only after correction/implementation: run the ADR existing-config test that applies `**/*.template.md` and validates successfully.
* Run only after implementation: `uv lock --check`
* Run only after implementation: `uv sync --locked --all-groups`
* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest`
* Run only after implementation: `uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`
* Run only after implementation: build and inspect a wheel in a temp directory, then run the installed CLI from that wheel.
* Run only after user-approved release: verify `v2.1.0` and moving `v2` point at the intended release commit before marking `deployed.md` as published.

### Final recommendation

Claude Code should revise the plan using the findings above

### Review ledger for next loop

* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-06-08-adopt-cli.md
* Audit round: 4
* Open issue IDs: CR-004, CR-NEW-004
* Resolved issue IDs: CR-001, CR-002, CR-003, CR-005, CR-NEW-001, CR-NEW-002, CR-NEW-003
* Superseded issue IDs: None
* Significant findings remaining: Yes
* Next audit should focus on: runtime registry/bundle drift handling for both `list` and `adopt`, plus release/changelog/handoff sequencing before any released/deployed claims.