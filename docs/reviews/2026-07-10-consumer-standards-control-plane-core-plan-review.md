# Review: Consumer Standards Control Plane Core Implementation Plan

**Plan:** `docs/superpowers/plans/2026-07-10-consumer-standards-control-plane-core.md` **Spec:** `docs/superpowers/specs/2026-07-10-consumer-standards-control-plane-spec.md` (SPEC-CP01 rev 0.5, approved) **Review target state:** working tree after `de8f2bb` (only uncommitted changes are user-authored additions to `docs/TODO.md` and `docs/workflows/housekeeping.md`) **Workflow:** `docs/workflows/review-plan.md`

## Round 1 — 2026-07-10

Verdict: **APPROVE AFTER REVISION**

Two blocking findings, both with surgical fixes: one verification-gate command fails against the current tree for a reason this plan cannot resolve (F1), and the synthetic-wheel offline-install mechanism the plan builds on is broken in the executing agent environment today (F2). Everything else verified clean: no phantom requirement IDs, no pinned-contract/spec contradictions, all other gate commands run as written, and the plan honors every condition from the converged spec review. If the F2 fix follows the recommended mechanism, no re-review round is needed; a different mechanism choice warrants a targeted re-check of Tasks 3, 5, and 18 only.

### Method

- **Executed:** full test suite baseline (`uv run pytest`: 1 failed, 1692 passed); every CLI gate command from the plan's Verification Gates section with its exact flags; Prettier 3.8.3 and markdownlint against the plan file; a live Prettier range-ignore experiment; `fcntl.flock` on a directory descriptor; the Task 1 model snippet under the repo's Pydantic 2.13 (runtime validation) and BasedPyright strict (clean).
- **Traced:** SPEC-CP01 rev 0.5 section/requirement inventory and milestone scope; the Requirement Allocation table against spec text; all 10 Plan-Pinned Contracts against spec, ADR 0023/0024, `meta/versioning.md`, and SPEC-BA02 rev 0.6; every cited symbol, path, fixture, and version against live source; task ordering and per-commit file lists; the converged spec review's conditions (F1–F10) against plan tasks.

### Verified and held (do not re-check in later rounds)

- SPEC-CP01 is rev 0.5, approved; §§7–12, §17.3, §19 MS-0–MS-5, and Appendix B exist. Requirement ID ranges are FR-001–036, IR-001–006, DR-001–007, NFR-001–009; every plan-cited ID exists. Spot-checked allocation rows (FR-017, FR-026, FR-030, FR-035, DR-002–003, FR-001–006) match spec text.
- MS-1–MS-3 are generic-core scope in the spec; MS-4 owns real-package migration, MS-5 dogfood/release. The plan's layer table matches. FR-020 is bundled under MS-3 in the spec's milestone summary but its acceptance is Agent-Handoff-specific; the plan's deferral is disclosed in its allocation table and is a defensible partition, not an omission.
- None of the 10 Plan-Pinned Contracts contradicts spec text. Notably: NFR-009 itself prohibits a lock artifact (pin 5 agrees); the spec pins no numeric exit codes or error-code strings (0/1/2, `CP-BUSY`, `CP-PROVIDER-INTEGRITY` are conforming elaborations); spec §9 examples use quoted catalog majors (`catalog = '5'`); §13.2/§13.3 match pins 6 and 10.
- SPEC-BA02 is rev 0.6; its FR-007 matches pin 1. `PackageOptionSchema` exists at `src/project_standards/package_contract/payload.py:989` with the `namespace` property and `resolve_options` method the plan calls. `StrictModel`, `KebabId` (`family.py`), and `PackageVersion` (`paths.py`) are importable today.
- ADR 0023/0024 (both accepted) and `meta/versioning.md` support the plan's init shape, executor-only/lock-last apply, adapter ownership set, `--allow-major` accepted-track semantics, and integer-major/quoted-TOML encoding. The converged spec review (three rounds, APPROVE) imposed conditions F1–F10, all now spec text; the plan honors each.
- Ground truth: `tests/fixtures/package_contract/valid/full` with `expected/catalog.toml` and `catalogs/5.toml` exists; the rendered catalog has no self-digest today (Task 2 is net-new as claimed); the projection covers payloads only, not catalogs (Task 3 net-new as claimed); no `control_plane` exists anywhere; the six new schema filenames collide with nothing; no `init`/`reconcile`/`standards enable|disable|version|list|show` command collides; `docs/usage.md` exists; pyproject has `requires-python >= 3.14`, `uv_build`, Pydantic ≥ 2.13.4, PyYAML; version is 4.3.0.
- Gates: pytest-repeat is absent, so the plan's `--count`-unavailable claim and shell-loop workaround are correct; the `performance` marker is registered under `--strict-markers`; coverage floor is 85 with branch coverage; Ruff select list has no INP/ALL/D rules and E501 is ignored, so plan snippets are lint-safe; every Verification Gates CLI command and flag exists and exits 0 today **except** `standards validate-packages --root .` (F1); `npm ci` is correctly sequenced before `tests/coherence` (which skips without it); the plan file itself passes Prettier and markdownlint; `docs/superpowers/plans/**` and `docs/reviews/**` are outside the frontmatter include set.
- The Task 1 snippet (recursive PEP 695 `JsonValue`, `KebabId`-keyed dicts, `Literal["latest"] | PackageVersion`) validates at runtime under the repo's Pydantic and is BasedPyright-strict clean. `fcntl.flock` with `LOCK_SH`/`LOCK_EX | LOCK_NB` on an open directory descriptor works on this kernel/filesystem (pin 5 executable as written).
- Prettier 3.8.3 (the repo's pin) preserves content between `<!-- prettier-ignore-start/end -->` markers in Markdown verbatim — pin 7's premise holds upstream (see F7 for the repo-novelty note).
- The uncommitted `docs/TODO.md` hunk is the user task the plan's final completion criterion protects; the criterion is accurate and necessary.
- Commit-granular consistency: each task's commit stages only files its steps create or edit; no task consumes an artifact a later task creates (except F4's `__init__.py` ordering nit); commit messages match the repo's `feat(v5):`/`docs(v5):` style.

### Findings

#### F1 🔴 Verification gate `standards validate-packages --root . --json` fails against any tree this plan can produce

**Defect:** The Verification Gates list includes `uv run project-standards standards validate-packages --root . --json` as a fail-fast step. Run live today it exits 1 with `PC-NO-FAMILIES: repository contains no loadable V2 package family` — the repo root has no V2 families, and creating them is explicitly the follow-on migration plan's job (the plan's own scope table defers "Current V2 payloads" to the follow-on). Task 18's gate run therefore fails by design, not by implementation error. **Evidence:** Live execution at `de8f2bb` → exit 1, `PC-NO-FAMILIES`. V2 families exist only under `tests/fixtures/package_contract/`. Neither `AGENTS.md` nor `.github/workflows/check.yml` runs this command today; the plan authored it. **Fix:** In the Verification Gates block, point the command at a root that has families — e.g. `--root tests/fixtures/package_contract/valid/full` (mirroring how the plan's `render-consumer-catalog` gate already targets that fixture) — or delete the line and let the follow-on plan introduce it when root families exist. If a synthetic-catalog root built by Task 18 is intended, name that root explicitly in the gate.

#### F2 🔴 The offline synthetic-wheel install mechanism is broken in the executing environment, and Tasks 3, 5, and 18 build on it

**Defect:** The plan's wheel proofs ("installs offline", "Build/install a synthetic wheel offline", Task 18's full offline lifecycle) inherit the existing helper pattern `["uv", "pip", "install", "--offline", "--no-deps", "--target", ...]` (`tests/package_contract/test_end_to_end.py:144`). In the agent execution environment, the first `uv` on PATH is the `uv-strict-python` plugin shim (`~/.claude/plugins/cache/l3digitalnet-plugins/uv-strict-python/0.2.1/hooks/shims/uv`), which rejects every mutating `uv pip` subcommand with exit 1 ("legacy interface"). The baseline already fails: `uv run pytest` → 1 failed (`test_wheel_rediscovery_is_offline_and_matches_source_facts`), 1692 passed. Every new test the plan writes with the same mechanism fails identically, and the plan's `coverage run -m pytest` gate cannot go green where the plan will actually be executed. CI passes only because the shim doesn't exist there. **Evidence:** Live full-suite run (1 failed/1692 passed); shim source shows `pip` + non-read-only subcommand → exit 1; real `uv` 0.11.6 at `~/.local/bin/uv` accepts `uv pip install`. **Fix:** Pin the install mechanism in the plan and repair the one existing call site while touching this area. Recommended: replace the subprocess `uv pip install --target` call with stdlib extraction of the pure-Python wheel (`zipfile.ZipFile(wheel).extractall(target)` — a wheel with no scripts/data needs nothing more, and it is deterministic and inherently offline), in a shared helper used by `tests/package_contract` and the new `tests/control_plane/helpers.py`. Add `tests/package_contract/test_end_to_end.py` (or its helper) to the plan's "Also modify" list, and state in Tasks 3/5/18 that wheel installation uses the shared helper, not `uv pip`. An alternative — resolving the real uv binary past the shim — also works but hardcodes knowledge of the harness into tests; prefer the stdlib route.

#### F3 🟡 The six new JSON Schemas are not covered by the named drift gate

**Defect:** Task 2 says "Generate and check the six JSON Schemas from the strict models" and then runs `standards generate-package-schemas --root . --check` expecting it to catch drift. That command generates only from the fixed tuple `_SCHEMA_MODELS` in `src/project_standards/package_contract/schemas.py:23-27` (exactly three models: `FamilyManifest`, `PayloadManifest`, `CatalogSource`) and compares only those. Unless that generator is extended, the gate passes trivially while the six new `consumer-*`/`mutation-plan`/`provider-input`/`reconciliation-plan` schemas can drift silently — and `package_contract/schemas.py` is absent from the plan's "Also modify" list. **Evidence:** `package_contract/schemas.py:23-27` (`_SCHEMA_MODELS`), `:87` (`generate_package_schemas`), `:110-116` (check compares only those three); plan's "Also modify" line names `catalog.py` and `projection.py` but not `schemas.py`. **Fix:** Add `src/project_standards/package_contract/schemas.py` (or a new control-plane schema generator registered into the same CLI command) to Task 2's Files line, and make Task 2's red test assert the six new schema files are produced and checked by the gate command.

#### F4 🟡 Task 6 creates `adapters/toml.py` two tasks before `adapters/__init__.py` exists

**Defect:** Task 6's Files line creates `control_plane/adapters/toml.py`, but `adapters/__init__.py` is created in Task 9. The Task 6 and Task 7–8 commits ship an implicit namespace package that contradicts the plan's own Target File Structure. No current gate fails on it (Ruff selects no INP rules; namespace imports resolve at runtime), so it survives to Task 9 as a latent inconsistency and a trap for the implementer or any interim wheel build. **Evidence:** Plan Task 6 Files line vs Task 9 Files line vs Target File Structure (which lists `adapters/__init__.py`); `pyproject.toml` Ruff `select` list contains no `INP`. **Fix:** Add `control_plane/adapters/__init__.py` to Task 6's Files line ("Create `control_plane/config_edit.py` and `control_plane/adapters/{__init__,toml}.py`"); Task 9 then extends the existing package.

#### F5 🟢 `--tool-release 4.3.0` is a hardcoded literal coupled to the current version

**Defect:** The render gate pins `--tool-release 4.3.0`. It matches `pyproject.toml` version 4.3.0 today, and the golden `expected/catalog.toml` carries `release = "4.3.0"` via `package_version()` — but any version bump during execution silently desynchronizes the plan's gate literal from the test-driven value. Harmless under the current release freeze. **Fix:** Add a one-line note to the gate ("4.3.0 = current `pyproject.toml` version; update together") or derive it in the gate invocation.

#### F6 🟢 Existing top-level `list` command overlaps the new `standards list`

**Defect:** Top-level `project-standards list` ("list standards with packaged adopt artifacts", `cli.py:369`) coexists with the plan's new `standards list`. No parser collision, but Task 17 deprecates `adopt` without saying whether its companion `list` gets the same notice, leaving a UX seam. **Fix:** One sentence in Task 17 stating whether top-level `list` gains the deprecation notice now or in the follow-on.

#### F7 🟢 Prettier range-exclusion markers are new to this repo

**Defect:** Pinned Contract 7 and Task 13 rely on `<!-- prettier-ignore-start/end -->` range markers; the repo today uses only single-node `<!-- prettier-ignore -->` (documented in `docs/handoff/conventions.md`). Verified live against the pinned Prettier 3.8.3 that range markers preserve enclosed Markdown verbatim, so the mechanism works — but it is unprecedented in-repo and Task 13 is the first to prove it under the gates. **Fix:** None required (Task 13's format-then-reconcile no-op test already covers it). Optionally record the pattern in `docs/handoff/conventions.md` when Task 13 lands.

#### F8 🟢 `.github/workflows/check.yml` is listed as modified, but no step clearly needs a CI change

**Defect:** Task 18 lists CI among its files, yet the existing unscoped `uv run pytest -m performance` CI step automatically picks up the new `tests/control_plane/test_scale.py`, and no other plan gate is CI-enforced today (check.yml runs only ruff/basedpyright/pytest/coverage/pip-audit — the CLI validators, Prettier, markdownlint, and coherence gates are local-only). As written the implementer cannot tell what CI edit is intended. **Fix:** Either state the intended CI change in Task 18 (e.g. "no change needed — confirm the unscoped performance step covers the new marker") or drop `check.yml` from the file list.

## Round 2 — 2026-07-10

Verdict: **APPROVE — converged**

**Review target state:** working tree after `106047c` (`docs(v5): resolve control-plane core plan review`); only uncommitted changes remain the same user-authored `docs/TODO.md` / `docs/workflows/housekeeping.md` hunks from Round 1. All eight Round 1 findings were re-verified against ground truth — the failing checks were re-run, not accepted on assertion. No finding survives and no new finding was introduced. Round 1's convergence condition (F2 fixed via the recommended stdlib mechanism) was met exactly, so this round is the confirming record.

### Fix verification

- **F1 ✅ fixed and re-run.** The gate now reads `standards validate-packages --root tests/fixtures/package_contract/valid/full --json`. Executed verbatim → `{"ok": true, "findings": []}`, exit 0 (was exit 1 `PC-NO-FAMILIES` at `de8f2bb`).
- **F2 ✅ fixed and re-run.** The revision follows the recommended route precisely: new shared `tests/wheel_helpers.py` (`extract_pure_python_wheel`, stdlib `zipfile`, contract documented in the docstring), the existing call site in `tests/package_contract/test_end_to_end.py` converted from the `uv pip install --offline` subprocess to the helper, and Tasks 3/5/18 rewritten to name `tests.wheel_helpers.extract_pure_python_wheel` explicitly. Full suite re-run in the shim environment: **1693 passed, 0 failed** (was 1 failed / 1692 passed). The helper and modified test pass `ruff format --check`, `ruff check`, and BasedPyright strict (0 errors). The socket-deny monkeypatch still guards the post-extract phase, and extraction is offline by construction.
- **F3 ✅ fixed by trace.** Task 2's Files line and the "Also modify" list now include `package_contract/cli.py`; the new step registers the control-plane generator into the existing `generate-package-schemas` path so one command checks all nine generated schemas (3 existing + 6 new), explicitly without making `package_contract.schemas` import the control plane; a new red step asserts the mutated-schema → exit 1 / restored → exit 0 drift behavior.
- **F4 ✅ fixed by trace.** Task 6 now creates `control_plane/adapters/{__init__,toml}.py`; Task 9's Files line changed to "extend `adapters/__init__.py`". No implicit namespace package at any commit; matches the Target File Structure.
- **F5 ✅ fixed and re-run.** The gate now derives `TOOL_RELEASE` from `project_standards._version.package_version`. Executed verbatim → prints `4.3.0`, and the render gate with the derived value exits 0 (`OK consumer catalog: expected/catalog.toml`).
- **F6 ✅ fixed by trace.** Task 17 adds the top-level `list` deprecation notice in the same task, with an explicit division: `standards list` is the supported catalog inventory; legacy `list` keeps its V1 scope until the follow-on.
- **F7 ✅ fixed by trace.** Task 13's Files line adds `docs/handoff/conventions.md` and a step recording the verified range-exclusion pattern, distinguished from the single-node `prettier-ignore` convention. (`docs/handoff/**` is exempt from the Prettier/markdownlint gates, so the edit adds no gate exposure.)
- **F8 ✅ fixed by trace.** `check.yml` was removed from Task 18's Files line and the "Also modify" list, replaced by an explicit confirm-only step that the existing unscoped `-m performance` CI step discovers the new scale test.

### New-content checks (this round)

- The revised plan document and the committed review file pass Prettier and markdownlint; `validate-frontmatter` remains green.
- The commit's collateral edits (`docs/STATUS.md`, `docs/handoff/state.md`, `docs/handoff/specs-plans.md`, session log) are bookkeeping consistent with the plan revision; the new plan Status line accurately restates Round 1's convergence condition.
- Commit-granular consistency holds after the edits: `package_contract/cli.py` appears in both Task 2's Files line and the "Also modify" list; the pre-landed `tests/wheel_helpers.py` is documented in the plan as a remediation prerequisite rather than a task deliverable, so no task re-creates it.

### Round tracking

| Round | Date       | 🔴  | 🟡  | 🟢  | Verdict                |
| ----- | ---------- | --- | --- | --- | ---------------------- |
| 1     | 2026-07-10 | 2   | 2   | 4   | APPROVE AFTER REVISION |
| 2     | 2026-07-10 | 0   | 0   | 0   | APPROVE — converged    |
