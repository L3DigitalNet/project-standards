### Executive summary

Claude Code’s revisions resolved the previous manifest-type, no-traceback, multi-fragment, and starter-validation defects, but significant findings remain. The destination-safety correction still misses symlinked parent directories, and the revised plan introduces a new release/CI risk by bumping `pyproject.toml` without committing the corresponding `uv.lock` change. New internet research was used for Python path/tempfile behavior and uv lockfile behavior.

### Verdict

Needs major correction before execution

### Audit loop status

* Audit type: Follow-up audit
* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-06-08-adopt-cli.md
* Prior audit issue count: 6
* Resolved issue count: 4
* Still open issue count: 0
* Partially resolved issue count: 2
* New issue count: 2
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

Re-read the revised plan, the prior audit ledger, the approved spec, git status/history, repo instructions, handoff state, conventions, package metadata, lockfile, CI workflow, registry code/data, validator include/exclude behavior, root scaffolds, standard examples/templates, and current plan diff. Retested prior findings for symlink handling, fragment target safety, manifest type validation, list/registry drift, and realistic frontmatter validation. Attacked validation false positives around uv lock freshness and ADR existing-config safety.

No tests, builds, `uv sync`, `uv lock`, formatters, package installs, or generators were run because this audit is read-only and those commands may modify the environment, lockfile, caches, or artifacts.

### Prior findings status

#### CR-001: Recoverable I/O failures can still escape as tracebacks

* Previous severity: High
* Current status: Resolved
* Evidence: The plan still maps source reads, fragment reads, temp creation, write, replace, and source-read failures through `WriteError` in lines 1052-1086 and 1099-1116, with failure-injection tests in lines 1142-1218.
* Remaining action for Claude Code: Keep these mappings during implementation.

#### CR-002: Adoption validation test is not executable as written

* Previous severity: High
* Current status: Resolved
* Evidence: The revised D1 test writes a real managed `docs/guide.md` from a valid shipped example, changes into the temp repo, calls `validate_frontmatter.main()`, asserts `rc == 0`, and checks `"validated"` in stdout. The validator prints `"no files matched"` on stderr for zero matches and `"✓ N file(s) validated"` on stdout for real matches.
* Remaining action for Claude Code: Keep the real managed-file fixture and stdout assertion.

#### CR-003: Invalid-manifest and list error paths do not satisfy the no-traceback contract

* Previous severity: High
* Current status: Resolved
* Evidence: `load_manifest()` now validates non-string `source`, `shared`, `dest`, and `target` fields in one loop before creating `Artifact` objects. `list` is inside the `AdoptError` / `RegistryError` boundary in lines 1506-1515.
* Remaining action for Claude Code: Parameterize malformed-manifest tests across all four fields if convenient, but the planned implementation now covers the defect.

#### CR-004: `list --json` omits the spec’s stable `contract_version` field

* Previous severity: Medium
* Current status: Partially resolved
* Evidence: `contract_version` is now emitted in JSON, and a drift-guard test was added. However, `_cmd_list()` still accepts `_contract_version(...) -> None` and prints/emits it, and `build_plan()` still treats `available_standards()` as the sole adoptable-id source. Bundle/registry drift is caught by tests only, not cleanly rejected at runtime.
* Remaining action for Claude Code: Make runtime list/adopt fail cleanly on bundle/registry drift, or derive adoptable ids from one registry-backed source so `contract_version: null` cannot be emitted.

#### CR-005: Fragment reporting cannot represent multiple fragments for one target

* Previous severity: Medium
* Current status: Resolved
* Evidence: `Report.fragments` is now `dict[str, list[str]]`, `execute_plan()` appends snippets per target, `format_report()` prints each snippet, and a same-target multi-fragment regression test was added.
* Remaining action for Claude Code: None.

#### CR-NEW-001: Destination safety resolves away symlinks before checking them

* Previous severity: High
* Current status: Partially resolved
* Evidence: The final-leaf symlink bug is fixed: `validate_dest()` returns `root / rel` without resolving the leaf, and tests now cover external, internal, and broken leaf symlinks plus unsafe fragment targets. The remaining gap is parent symlinks: `validate_dest()` performs only lexical normalization, then `_atomic_write()` calls `target.parent.mkdir(...)`, `tempfile.mkstemp(dir=target.parent, ...)`, and `os.replace(...)`. If `--dest/linkdir` is a symlink to outside the destination and the action writes `linkdir/file`, `abs_dest.is_symlink()` checks only the leaf path and the write can still occur outside `--dest`.
* Remaining action for Claude Code: Validate each existing parent component without following symlinked directories, or fail/skip when any existing path component under `--dest` is a symlink before writing.

### New blocking issues

#### CR-NEW-002: Version bump omits the lockfile update needed by this uv project

* Severity: High
* Status: Confirmed
* Adversarial angle: The plan’s release step changes package metadata but commits only `pyproject.toml`, while this repo’s lockfile records the editable project version and CI uses locked sync.
* Plan reference: C2 lines 1541-1558.
* Finding: The plan sets `pyproject.toml` to `version = "2.1.0"` and runs `uv sync`, but then stages only `pyproject.toml`. Current `uv.lock` records `project-standards` version `2.0.0`, and CI runs `uv sync --locked --all-groups`. If `uv sync` updates `uv.lock`, the plan leaves it uncommitted; if it does not, CI/reproducible locked sync can be stale.
* Repository evidence: `pyproject.toml` currently has `version = "2.0.0"`; `uv.lock` lines 395-398 record the editable package as version `2.0.0`; `.github/workflows/check.yml` line 27 runs `uv sync --locked --all-groups`.
* External research evidence: uv’s official locking/syncing docs say `uv run`/`uv sync` automatically lock/sync, and lock freshness is checked against project metadata. Source: https://docs.astral.sh/uv/concepts/projects/sync/ accessed 2026-06-08.
* Why it matters: The implementation can pass locally while leaving a dirty or stale lockfile, then fail the locked CI gate or ship mismatched release metadata.
* Recommended action for Claude Code: In C2, stage and commit `uv.lock` with `pyproject.toml` after the version bump/sync. Add a lock freshness check before committing.
* Suggested validation: After implementation, run `uv lock --check` and CI’s `uv sync --locked --all-groups`; verify `git diff --exit-code pyproject.toml uv.lock` after committing.

### New non-blocking issues

#### CR-NEW-003: ADR existing-config safety test can pass with only comment-level exclusion guidance

* Severity: Medium
* Status: Confirmed
* Adversarial angle: The plan claims the ADR fragment carries the template exclusion needed for validation safety, but the actual fragment makes the exclusion a commented example and the test only checks for a substring.
* Plan reference: A5 lines 451-466; D1 lines 1640-1650.
* Finding: The ADR fragment emits a real `markdown.adr` block, but the required `markdown.frontmatter.exclude` addition is commented out. The test only asserts `"**/*.template.md"` appears in output; it does not apply the exclusion or prove `validate-frontmatter` passes for an existing config that includes `docs/**/*.md`.
* Repository evidence: The validator collects configured includes/excludes from `.project-standards.yml` and applies excludes as real config values. The ADR template contains intentionally invalid placeholder dates, so a pre-existing config including `docs/**/*.md` will validate `docs/decisions/adr.template.md` unless a real exclude entry is present.
* External research evidence: Not applicable.
* Why it matters: Existing-config consumers can follow the reported fragment and still fail validation after adopting ADR. The validation check can pass while the intended safety behavior remains unproved.
* Recommended action for Claude Code: Make the ADR report provide an unambiguous real YAML addition for `markdown.frontmatter.exclude`, or explicitly label it as an operator action and add a test that constructs the corrected config and validates successfully.
* Suggested validation: Add an integration test with an existing config including `docs/**/*.md`, run `adopt adr`, apply the planned exclusion in the fixture, then run `validate_frontmatter.main(["--config", ".project-standards.yml"])` and assert success.

### Regressions

None found.

### Internet research performed

* Source name: Python `pathlib` documentation
* URL: https://docs.python.org/3/library/pathlib.html
* Access date: 2026-06-08
* What it was used to verify: Symlink/path behavior for `Path.resolve()`, `Path.is_symlink()`, and directory creation semantics.
* Relevant conclusion: The revised plan fixes final leaf symlink detection, but `is_symlink()` only checks the path itself; parent symlink components still need explicit handling.

* Source name: Python `tempfile` documentation
* URL: https://docs.python.org/3/library/tempfile.html#tempfile.mkstemp
* Access date: 2026-06-08
* What it was used to verify: `mkstemp(dir=...)` creates the temp file in the supplied directory.
* Relevant conclusion: Using a symlinked parent as `dir` is part of the remaining write-boundary risk.

* Source name: Astral uv locking and syncing documentation
* URL: https://docs.astral.sh/uv/concepts/projects/sync/
* Access date: 2026-06-08
* What it was used to verify: uv lockfile freshness and automatic lock/sync behavior.
* Relevant conclusion: The version bump should include `uv.lock` and a locked/freshness validation step.

* Source name: Astral uv build backend documentation
* URL: https://docs.astral.sh/uv/concepts/build-backend/
* Access date: 2026-06-08
* What it was used to verify: Whether bundle data under the module root remains a plausible wheel-inclusion strategy.
* Relevant conclusion: No new conflict found; wheel-inspection remains the right implementation validation.

### Read-only validation performed

* `pwd`, `git status --short`, `git branch --show-current`, `git log --oneline -n 10`, `git remote -v`: confirmed repo root, branch `testing`, modified plan file, untracked prior review artifacts, and canonical origin.
* Inspected `docs/handoff/state.md`, `AGENTS.md`, and `docs/handoff/conventions.md`: confirmed repo state, working rules, and validation expectations.
* Inspected the current plan with `nl`, `sed`, `rg`, and `git diff`: identified revisions since round 2 and retested prior findings.
* Inspected the approved spec: compared plan behavior against safety, registry, validation, packaging, and acceptance requirements.
* Inspected `pyproject.toml`, `uv.lock`, and `.github/workflows/check.yml`: found the version-bump/lockfile omission.
* Inspected `registry.py`, `registry.json`, `validate_frontmatter.py`, `.project-standards.yml`, shipped examples/templates, root workflows/configs, and standard docs: checked adoption validation, registry drift, config exclusion, and package-data claims.
* Ran `find . -maxdepth 3 -type l -ls`: checked current symlink shape in the repository while reasoning about destination safety.
* Consulted official Python and uv documentation for current external behavior.

### Recommended implementation validation

* Run only after correction/implementation: add a parent-symlink test where `dest_root/linkdir` points outside and action `dest="linkdir/file"` must not write outside `--dest`.
* Run only after correction/implementation: add runtime drift tests where a fake bundle has no registry contract version and `list`/`adopt` fail cleanly.
* Run only after correction/implementation: add the existing-config ADR test that applies the exclusion and validates successfully.
* Run only after implementation: after C2, run `uv lock --check` and `uv sync --locked --all-groups`; commit `uv.lock` with `pyproject.toml`.
* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest`
* Run only after implementation: `uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`
* Run only after implementation: build and inspect a wheel in a temp directory, then run the installed CLI from that wheel.

### Final recommendation

Claude Code should revise the plan using the findings above

### Review ledger for next loop

* Plan path: /home/chris/projects/project-standards/docs/superpowers/plans/2026-06-08-adopt-cli.md
* Audit round: 3
* Open issue IDs: CR-004, CR-NEW-001, CR-NEW-002, CR-NEW-003
* Resolved issue IDs: CR-001, CR-002, CR-003, CR-005
* Superseded issue IDs: None
* Significant findings remaining: Yes
* Next audit should focus on: parent-symlink write-boundary safety, uv.lock inclusion after the version bump, runtime registry/bundle drift failure, and ADR existing-config validation.