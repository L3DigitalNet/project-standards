### Executive summary

Claude Code’s round-2 corrections resolve the remaining prior findings. The current spec now defines `restamp-pending`, read-path symlink handling via `UNSAFE`, and concrete `--update` behavior for absent-from-lock artifacts without the previously undefined `resolvable-UNLOCKED` category.

New internet research was performed for the external CI assumptions. Official uv and GitHub Actions documentation supports the revised ref-pinned `uvx --from git+...@ref` command, reusable workflow model, expression/input usage, warning annotations, and `$GITHUB_STEP_SUMMARY` visibility.

### Verdict

No significant findings remain

### Audit loop status

* Audit type: Follow-up audit
* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-06-08-check-drift-design.md`
* Prior audit issue count: 10
* Resolved issue count: 10
* Still open issue count: 0
* Partially resolved issue count: 0
* New issue count: 0
* Regression count: 0
* Significant findings remaining: No

### Adversarial review performed

Retested the prior findings against the revised spec, focusing on update crash/restamp semantics, read-only symlink classification, undefined `UNLOCKED` update behavior, lock-vs-manifest reconciliation, lock schema/version planes, CLI flags, exit codes, CI ref pinning, green-run warning visibility, and acceptance criteria false positives.

Repository fit was checked against the current adopt engine, manifest loader, CLI, error classes, registry, versioning docs, bundle manifests, workflows, and test conventions. Tests, builds, coverage, packaging, and validation gates were not run because this audit is read-only and those commands may write caches or artifacts.

### Prior findings status

#### SA-001: `--relock` contradicts the state machine

* Previous severity: High
* Current status: Resolved
* Evidence: The state machine keeps relocked customizations in `[S.local_edits]`, reports divergent entries as `LOCAL-EDIT`, and never evaluates them as template-backed `STALE` (`spec lines 57-60`, `209-215`).
* Remaining action for Claude Code: None.

#### SA-002: Lock-driven checking can miss newly-added or skipped artifacts

* Previous severity: High
* Current status: Resolved
* Evidence: The spec keeps standards lock-driven but makes artifacts manifest-driven, including lock-only reconciliation and adopt-skipped artifact behavior (`spec lines 35`, `45-75`, `191`, `240`).
* Remaining action for Claude Code: None.

#### SA-003: `--update` lacks write-safety and lock-consistency rules

* Previous severity: High
* Current status: Resolved
* Evidence: The revised spec defines `restamp-pending`, says it is visible on every run, requires any lock-writing operation to repair it, defines `UNSAFE` before reads, and adds acceptance tests for lock-write failure, later template change classification, and symlink read prevention (`spec lines 51-55`, `67-82`, `136`, `195-202`, `241-242`).
* Remaining action for Claude Code: None.

#### SA-004: CI command is not pinned to the workflow ref

* Previous severity: High
* Current status: Resolved
* Evidence: The spec requires a `standards-ref` input and a ref-pinned `uvx --from "git+https://github.com/L3DigitalNet/project-standards@${{ inputs.standards-ref || 'v2' }}" project-standards check` invocation (`spec lines 221-228`). Official uv docs support `uvx --from git+...@tag`, and GitHub docs support reusable workflow calls by `owner/repo/.github/workflows/file.yml@ref`.
* Remaining action for Claude Code: None.

#### SA-005: Lockfile version fields conflate contract versions and tool releases

* Previous severity: High
* Current status: Resolved
* Evidence: The lockfile separates `lockfile_version`, top-level `tool_version`, and per-standard `contract_version`; repo versioning docs define contract-plane `major.minor` separately from tool SemVer (`spec lines 98-123`; `meta/versioning.md` lines 49-52; `registry.json` lines 1-8).
* Remaining action for Claude Code: None.

#### SA-006: Exit-code contract omits existing `ManifestError` exit 3

* Previous severity: Medium
* Current status: Resolved
* Evidence: The spec maps `ManifestError` to exit 3, matching the current error class (`spec line 173`; `src/project_standards/adopt/errors.py` lines 19-24).
* Remaining action for Claude Code: None.

#### SA-007: Initial lockfile format is “versioned” but has no version field

* Previous severity: Medium
* Current status: Resolved
* Evidence: The lock example includes `lockfile_version = 1`, and unsupported or missing versions map to `LockError` exit 2 (`spec lines 100-103`, `123`).
* Remaining action for Claude Code: None.

#### SA-008: Machine-readable output and option combinations are under-specified

* Previous severity: Medium
* Current status: Resolved
* Evidence: The spec includes a CLI flag matrix and JSON schema with artifact states, owners, fragments, `restamp_pending`, summary counts, and `exit_code` (`spec lines 128-171`).
* Remaining action for Claude Code: None.

#### SA-009: CI warning-only `LOCAL-EDIT` output may be invisible

* Previous severity: Medium
* Current status: Resolved
* Evidence: The spec now requires `$GITHUB_STEP_SUMMARY` and `::warning::` annotations for `LOCAL-EDIT`, `ORPHAN`, and `restamp-pending` on green runs (`spec line 230`). GitHub docs confirm both mechanisms are supported.
* Remaining action for Claude Code: None.

#### SA-NEW-001: `resolvable-UNLOCKED` has no state-machine definition

* Previous severity: Medium
* Current status: Resolved
* Evidence: The undefined term was removed. `UNLOCKED` is now only present/divergent/no-baseline, `MISSING` handles absent artifacts, and `--update` explicitly writes `MISSING`, skips divergent `UNLOCKED` unless `--force`, and tests the absent-from-lock trio (`spec lines 33`, `70`, `136`, `240`).
* Remaining action for Claude Code: None.

### New blocking issues

None found.

### New non-blocking issues

None found.

### Regressions

None found.

### Remaining ambiguities and decisions needed

None found.

### Internet research performed

* Source name: uv Using tools guide
* URL: https://docs.astral.sh/uv/guides/tools/
* Access date: 2026-06-08
* What it was used to verify: `uvx`, `--from`, and git URL/tag/commit source support.
* Relevant conclusion: The spec’s ref-pinned `uvx --from git+https://...@ref project-standards check` model is supported.

* Source name: GitHub Actions reusable workflows docs
* URL: https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows
* Access date: 2026-06-08
* What it was used to verify: reusable workflow invocation by `owner/repo/.github/workflows/file.yml@ref`.
* Relevant conclusion: The spec’s caller-pinned reusable workflow model is supported.

* Source name: GitHub Actions contexts reference
* URL: https://docs.github.com/en/actions/reference/workflows-and-actions/contexts
* Access date: 2026-06-08
* What it was used to verify: `inputs` context/property dereference usage, including hyphenated input names.
* Relevant conclusion: `inputs.standards-ref` is valid property dereference syntax.

* Source name: GitHub Actions workflow commands docs
* URL: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands
* Access date: 2026-06-08
* What it was used to verify: warning annotations and `$GITHUB_STEP_SUMMARY`.
* Relevant conclusion: The green-run visibility requirements are technically supported.

### Read-only validation performed

* `pwd`: confirmed repository root.
* `git branch --show-current`, `git status --short`, `git log --oneline -n 10`: confirmed branch `testing`, dirty worktree, and latest spec-review commit.
* `git diff --stat`, `git diff --name-only`, `git diff -- .github/workflows/validate-markdown-frontmatter.yml`: inspected uncommitted changes and verified the spec file itself was not dirty.
* `git show --stat --oneline --no-renames -1`, `git show --no-ext-diff --unified=80 -- docs/superpowers/specs/2026-06-08-check-drift-design.md`: confirmed the latest committed spec revision specifically addressed SA-003 and SA-NEW-001.
* `nl -ba docs/superpowers/specs/2026-06-08-check-drift-design.md`: re-read and inventoried current spec requirements and line references.
* `rg -n` on state/update/lock terms in the spec: verified `resolvable-UNLOCKED` was removed and restamp/symlink terms were defined.
* `rg --files ...`: discovered relevant source, tests, workflows, standards, and docs; the extra `workflows` argument was nonexistent and only produced a read-only `rg` path error.
* `nl -ba` on `src/project_standards/adopt/engine.py`, `manifest.py`, `errors.py`, `cli.py`, `schemas/registry.json`, `meta/versioning.md`, `.github/workflows/validate-markdown-frontmatter.yml`, bundle manifests, and `pyproject.toml`: checked repository fit for path safety, manifest classes, exit codes, version planes, workflow patterns, and tooling gates.
* `rg -n` across `src`, `tests`, workflows, and the spec: checked for existing check/lock implementation, test conventions, and conflicting terminology.

### Recommended planning/implementation validation

* Run only after implementation: `uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit`.
* Run only after implementation: `uv run validate-frontmatter --config .project-standards.yml`.
* Run only after implementation: targeted fixture tests for every state, absent-from-lock trio, restamp lifecycle, final lock-write failure, later-template-change classification, symlinked leaf/ancestor reads, shared-artifact dedupe, relock table behavior, JSON shape, and flag matrix.
* Run only after implementation: rendered workflow tests proving caller and reusable drift workflows pin the same major ref and emit summaries/warnings for green `LOCAL-EDIT`, `ORPHAN`, and `restamp-pending`.

### Final recommendation

No significant findings remain; the audit/fix loop can stop

### Review ledger for next loop

* Spec path: `/home/chris/projects/project-standards/docs/superpowers/specs/2026-06-08-check-drift-design.md`
* Audit round: 3
* Open issue IDs: None
* Resolved issue IDs: SA-001, SA-002, SA-003, SA-004, SA-005, SA-006, SA-007, SA-008, SA-009, SA-NEW-001
* Superseded issue IDs:
* Significant findings remaining: No
* Next audit should focus on: No further audit needed unless the spec changes.