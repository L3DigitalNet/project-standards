# Release-Preparation Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove release-only proof and orchestration while retaining the original control-plane compatibility, migration, and performance obligations.

**Architecture:** Restore direct repository CI phases and delete the disposable release certification subsystem. Keep immutable v5 payload APIs unchanged; change only this repository's selected Python Tooling options and active operational documentation.

**Tech Stack:** GitHub Actions, Python 3.14, uv, pytest, pytest-xdist, coverage.py, Ruff, BasedPyright.

---

## Task 1: Pin the simple repository gate

**Files:**

- Modify: `tests/test_repository_test_gate.py`
- Modify: `.github/workflows/check.yml`

- [ ] **Step 1: Replace custom-runner assertions with a failing direct-workflow contract**

Keep only tests that parse `.github/workflows/check.yml` and assert this ordered command sequence after dependency setup:

```python
assert test_commands == [
    'uv run coverage erase',
    'uv run coverage run -m pytest -m "not performance and not compatibility"',
    'uv run pytest -m compatibility -n 4 --dist load --max-worker-restart=0',
    'uv run pytest -m performance',
    'uv run coverage report',
]
```

Also assert `npm ci` precedes the ordinary test step and no workflow command contains `run_repository_tests` or `release_replay`.

- [ ] **Step 2: Run the focused test and confirm it fails against the custom runner**

Run:

```bash
uv run pytest tests/test_repository_test_gate.py -q
```

Expected: failure because `.github/workflows/check.yml` still delegates to `scripts/run_repository_tests.py`.

- [ ] **Step 3: Replace the custom runner step with the five direct commands**

Keep Node setup and `npm ci`, Python/uv setup, dependency sync, Ruff, BasedPyright, and pip-audit unchanged. Replace only the combined custom-runner step with the five named test/coverage phases from Step 1.

- [ ] **Step 4: Run the focused workflow contract**

Run:

```bash
uv run pytest tests/test_repository_test_gate.py -q
```

Expected: all tests pass.

## Task 2: Stop selecting release-only coverage behavior

**Files:**

- Modify: `.standards/config.toml`
- Modify: `.standards/lock.toml`
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `scripts/check.py`

- [ ] **Step 1: Add configuration assertions to the focused workflow test**

Assert that root `pyproject.toml` retains `compatibility` and `performance` markers plus `pytest-xdist>=3.8`, while omitting the `release_replay` marker, `tool.coverage.run.parallel`, `tool.coverage.run.patch`, and `tool.coverage.paths`.

- [ ] **Step 2: Run the focused test and confirm the old root selection fails it**

Run:

```bash
uv run pytest tests/test_repository_test_gate.py -q
```

Expected: failure on the release-only marker and parallel/subprocess coverage keys.

- [ ] **Step 3: Remove only the root opt-in values and reconcile**

In `.standards/config.toml`, retain `pytest-xdist>=3.8`, `pyright==1.1.411`, `workflow_ownership = "consumer-owned"`, and the `compatibility`/`performance` markers. Remove the explicit coverage object and `release_replay` marker. Apply the repository's normal reconciliation so generated `pyproject.toml`, `scripts/check.py`, `.standards/lock.toml`, and `uv.lock` match the selected defaults.

- [ ] **Step 4: Run the focused configuration and fixed-point checks**

Run:

```bash
uv run pytest tests/test_repository_test_gate.py tests/package_compatibility/test_current_catalog_activation.py -q
uv run project-standards reconcile --check --repo .
```

Expected: tests pass and reconciliation reports no mutating actions.

## Task 3: Delete disposable release certification

**Files:**

- Delete: `scripts/run_repository_tests.py`
- Delete: `tests/package_compatibility/release_candidate.py`
- Delete: `tests/package_compatibility/test_release_candidate.py`
- Delete: `tests/fixtures/package_compatibility/legacy/release-root/`
- Delete: `docs/reviews/2026-07-11-consumer-standards-control-plane-release-cut-evidence.md`
- Delete: `docs/research/2026-07-12-v5-release-verification-performance.md`
- Delete: `docs/superpowers/specs/2026-07-12-python-tooling-parallel-coverage-options-design.md`
- Delete: `docs/superpowers/plans/2026-07-12-python-tooling-parallel-coverage-options.md`
- Delete: release-preparation review files identified by exact path in the audit ledger

- [ ] **Step 1: Delete the release-only code, fixture, evidence, research, design, plan, and review files**

Use the approved audit inventory. Preserve control-plane implementation, generic workflow ownership, package reconstruction tests, compatibility matrix tests, performance tests, and immutable package payloads.

- [ ] **Step 2: Prove no active code reference remains**

Run:

```bash
! rg -n 'release_candidate|RELEASE_REPLAY|release_replay|run_repository_tests|PROJECT_STANDARDS_TEST_WORKERS|release-cut-evidence' --glob '!CHANGELOG.md' --glob '!docs/handoff/sessions/**' .
```

Expected: no matches outside preserved historical release notes or append-only session history.

- [ ] **Step 3: Run retained compatibility and performance collection checks**

Run:

```bash
uv run pytest --collect-only -q -m compatibility
uv run pytest --collect-only -q -m performance
```

Expected: both retained suites collect nonzero tests.

## Task 4: Synchronize active documentation and release truth

**Files:**

- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `scripts/README.md`
- Modify: `docs/mcp-readiness.md`
- Modify: `docs/STATUS.md`
- Modify: `docs/TODO.md`
- Modify: `docs/handoff/state.md`
- Modify: `docs/handoff/deployed.md`
- Modify: `docs/handoff/specs-plans.md`
- Modify: `docs/handoff/conventions.md`
- Modify: `docs/handoff/sessions/2026-07.md`
- Modify only if needed for accurate current traceability: `docs/specs/2026-07-10-consumer-standards-control-plane-spec.md`

- [ ] **Step 1: Replace active custom-runner instructions with direct gate commands**

Document the same five test/coverage phases used by CI. Do not add a new release-proof procedure.

- [ ] **Step 2: Remove active pointers to deleted artifacts**

Keep historical release facts in `CHANGELOG.md` and append-only session history. Remove deleted design/plan/evidence rows from active indexes and record v5 as published.

- [ ] **Step 3: Validate only affected documentation**

Run Prettier, markdownlint, managed Markdown validation, local-link validation, and `git diff --check` against the changed documentation paths.

Expected: no errors caused by the cleanup.

## Task 5: Verify once and remove temporary cleanup artifacts

**Files:**

- Delete: `docs/superpowers/specs/2026-07-18-release-preparation-cleanup-design.md`
- Delete: `docs/superpowers/plans/2026-07-18-release-preparation-cleanup.md`

- [ ] **Step 1: Run the retained gate once**

Run each direct CI phase once, followed by Ruff, BasedPyright, pip-audit, package validation, graph validation, schema generation check, payload projection check, coherence, and applicable documentation checks.

Expected: every retained required gate passes.

- [ ] **Step 2: Audit the final diff against the approved boundary**

Require no modifications under immutable `standards/*/versions/**`, no tag changes, no unrelated source refactor, and no new release-proof framework.

- [ ] **Step 3: Delete this temporary design and plan**

Remove both cleanup-only documents so the final tree contains no new process artifact.

- [ ] **Step 4: Commit the cleanup intentionally**

Stage the bounded cleanup, verify the staged diff, and create one signed cleanup commit. Do not push until the final diff and retained gates are green.
