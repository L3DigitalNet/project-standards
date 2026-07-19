# Fable 5 Review — project-standards

## 1. Header

- **Project:** project-standards — source-of-truth repository for reusable standards (Catalog 5)
- **Repo path:** `/home/chris/projects/project-standards`
- **Reviewed commit:** `69c48655606a15288706515e4a0f965c839c585f` (branch `testing`, clean working tree)
- **Reviewer:** Claude Fable 5 (`claude-fable-5`), high effort — 12 parallel subsystem reviewers, one fresh-context adversarial verifier per finding (122 agents total)
- **Review date:** 2026-07-19
- **Verification note:** 109 raw findings from the 12 reviewers; the verifier pass **pruned 5** (refuted), **adjusted 4** (corrected location/evidence), and **downgraded 1** severity. The 104 verified findings were merged to **100 report findings** — 4 pairs were the same defect surfaced independently in a live source module and its released-payload mirror copy.

### Gate results at the reviewed commit (run during this review)

| Gate | Result |
| --- | --- |
| `uv run ruff format --check .` | 274 files already formatted |
| `uv run ruff check .` | All checks passed |
| `uv run basedpyright` | 0 errors, 0 warnings, 0 notes |
| `uv run pytest -m "not performance and not compatibility"` (candidate-wheel runtime on `PYTHONPATH`) | 2658 passed, 61 deselected |
| `standards validate-packages` / `validate-graph` / `render-catalog --check` / `sync-payload-projection --check` / `generate-package-schemas --check` | all OK (run by the standards-content reviewer, wheel runtime) |
| `packages check-release --baseline v5.0.1` | ok, classification = patch |
| `reconcile --check` / `project-standards validate` (dogfood) | drift = false / 34 files OK |
| `spec validate` + `spec lint --strict` (16 maintained specs) | all OK |
| Payload digest chain (all 10 payloads, every resource/artifact sha256 recomputed) | all match |

## 2. Executive Summary

The repository is in good health: every mechanical gate is green at the reviewed commit, the payload digest chain verifies byte-for-byte, release classification against `v5.0.1` is a clean `patch`, and the review found **no Critical findings**. The dominant risk is **consumer-facing defects frozen into the released `agent-handoff` 1.1 payload**: the SessionStart hook uses Python-3.14-only `except A, B:` syntax and dies with `SyntaxError` on any consumer running an older interpreter, and the provider's link-target parser raises `IndexError` on empty link targets — both require cutting an `agent-handoff` 1.2 payload (a consumer-visible, hence MINOR, change). The second risk cluster is control-plane edge cases: a create-only lock entry is silently dropped when a consumer deletes the unit (making reconcile non-convergent and resurrecting deleted content), the v4→v5 migration can whole-file-delete a bounded-block target the new package does not re-materialize, and lock contention surfaces as a raw traceback instead of a CP-BUSY finding. Third, the reusable `validate-specs.yml` workflow silently ignores consumers' `standards-ref` and `strict-lint` inputs because of never-true `github.event_name == 'workflow_call'` guards — and the tests assert the broken strings verbatim. The long tail (72 Low) is mostly hardening, structure, and doc-drift items in an otherwise disciplined codebase.

| Severity | Architecture | Structure | Correctness | Security | Performance | Testing | Convention | Docs | Total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Critical | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| High | 0 | 0 | 9 | 0 | 0 | 0 | 0 | 0 | 9 |
| Medium | 1 | 0 | 16 | 0 | 0 | 0 | 0 | 2 | 19 |
| Low | 1 | 17 | 28 | 5 | 2 | 2 | 9 | 8 | 72 |
| **Total** | **2** | **17** | **53** | **5** | **2** | **2** | **9** | **10** | **100** |

## 3. Coverage Ledger

| Area | Depth | Notes and gaps |
| --- | --- | --- |
| `src/project_standards/control_plane/` — core (planner, resolution, models, state, locking, paths, schemas, codec) | Deep | Every line read; lock semantics (flock on `.standards` dir fd, inode `is_current` check) and plan/apply TOCTOU (fingerprint + re-plan under exclusive lock, lock published last) checked and found sound. Two findings reproduced empirically in a scratch repo. |
| `src/project_standards/control_plane/` — execution (executor, providers, adapters/, distribution, catalog_refresh) | Deep | All files read incl. all 9 adapters; staging-leak finding reproduced with the repo's own executor fixture. Adapters reviewed by reading, not fuzzing. |
| `src/project_standards/control_plane/` — lifecycle (migration, cli, recovery, snapshot, bootstrap, command_resolution, config_edit, diagnostics) | Deep | All files read; two live reproductions (lock-contention traceback, U+007F TOML render). The bounded-block migration deletion (F-005) is verified by code-path analysis, not an end-to-end fixture run — no existing test exercises that path. |
| `src/project_standards/package_contract/` | Deep | All 13 modules read; digest-chain injectivity and the release-classification matrix verified against ADR 0024 and `test_release.py`. jsonschema `$ref` crash reproduced. Generated schema fixtures not re-audited. |
| Frontmatter toolchain (`validate_frontmatter`, `validate_id`, `validate_references`, `format_frontmatter`, `frontmatter_*`, `id_format`, `sync_*`, `_version`) | Deep | All 10 files read; six mechanically risky claims verified by executing minimal reproductions (fnmatch dialect, empty-frontmatter misdiagnosis, anchor-drop, JSONC crash, check/write asymmetry). |
| `cli.py`, `adopt/`, `standards_graph/`, `registry.py`, `standard_manifest.py`, `provider_runner.py`, `bundles/` | Deep | All Python read incl. bundle scripts and all seven `adopt.toml` manifests; 3.13 SyntaxError and TOML-bool findings verified by running them. Bundle data payloads (templates, JSON configs, SKILL.md) sampled, not line-audited. |
| `src/project_standards/agent_handoff/` | Deep | All modules incl. all five integrations read; both crash findings reproduced end-to-end against a scratch repo. Its test suite reviewed selectively. |
| `src/project_standards/specs/` | Deep | All 13 files read; templates structure-scanned. Four empirical repros (extract regex, fence-unaware validate, H1-anchor, argparse-abbreviation lock bypass). Fixture corpus under `tests/fixtures/specs` not audited. |
| `src/project_standards/payloads/` (released, consumer-side code) | Deep | All executable payload code read (incl. the 1038-line agent-handoff provider); every declared sha256 digest across all nine packages recomputed and verified; both crash findings dynamically confirmed (py_compile on 3.13; IndexError repro). Markdown/JSON-schema prose sampled. |
| `tests/` (151 files + fixtures + coherence) | Scanned→Deep | README + ~30 key modules read fully; tree-wide greps for markers, nondeterminism, assert-free tests, typing, cwd-relative paths. The seven per-standard reconstruction suites (~8k lines) skimmed via heads/greps only. Fixture trees structure-scanned. |
| `standards/`, `catalogs/`, `.standards/` | Deep | All indexes/payload.toml/providers read; digests recomputed for all 10 payloads; config validated against every package schema; `git diff v5.0.1..HEAD` confirms payload immutability holds; full read-only CLI check suite run (see gate table). Long normative prose (e.g. 1340-line python-coding README) sampled. `schemas/` does not exist at repo root — skipped. |
| `.github/`, `scripts/`, root configs, `uv.lock` | Deep | All 8 workflows + dependabot + scripts + configs read; `uv lock --check` clean; pre-commit entry points cross-checked against `[project.scripts]`; `workflow_call` event semantics confirmed against upstream GitHub issues. |
| `README.md`, `AGENTS.md`, `CLAUDE.md`, `UPGRADING.md`, `CHANGELOG.md`, `docs/` | Deep/Scanned | Core docs + meta/versioning + key ADRs read fully; ADRs 0002–0022 frontmatter/status-verified and skimmed; six large maintained specs (~6,800 lines) validated via `spec validate`/`spec lint --strict` rather than line-read; `docs/specs/archive/` checked for index consistency only (historical by design). |
| `docs/plans/`, `docs/research/`, `docs/handoff/sessions/` | Skipped | Working notes and append-only history, not product surface; only index parity was checked by the docs reviewer. |
| `build/`, `dist/`, `node_modules/`, `__pycache__` | Skipped | Generated/ephemeral artifacts. |

## 4. Severity & Category Rubric

**Severity**

- **Critical** — data loss, security breach, or crash on a normal path.
- **High** — incorrect behavior on a realistic input, or a clear violation of a stated project principle with downstream impact.
- **Medium** — correctness or maintainability issue with a workaround or a narrow trigger.
- **Low** — localized smell or minor convention drift.

**Confidence** — High / Medium / Low that the finding is real, as re-assessed by an independent fresh-context verifier agent (verdicts: CONFIRMED / ADJUSTED; REFUTED findings were pruned).

**Categories** — Architecture · Structure · Correctness · Security · Performance · Testing · Convention · Docs.

Reading note for the implementer: released payload bytes (`standards/<family>/versions/<major.minor>/` and `src/project_standards/payloads/<family>/<major.minor>/`) are **immutable** — any fix touching them means authoring the next payload version and wiring it per the documented order (payload.toml digests → aggregate digest → family `standard.toml` → `catalogs/5.toml` → `sync-payload-projection` → regenerate `standards/catalog.md`). The affected findings say so explicitly.

## 5. Findings

**F-001 — Handle null hooks/SessionStart values in merge_claude_settings**

- Category: Correctness · Severity: High · Confidence: High
- Location: src/project_standards/agent_handoff/integrations/claude.py:101-105
- Evidence:

```text
src/project_standards/agent_handoff/integrations/claude.py:101:    hooks_value = merged.setdefault("hooks", {})
    hooks = cast(dict[str, object], hooks_value)
    session_start_value = hooks.setdefault("SessionStart", [])
```

- Problem: A consumer .claude/settings.json containing '{"hooks": null}' or '{"hooks": {"SessionStart": null}}' passes \_session_start_groups (which maps None to []), but merge_claude_settings then calls setdefault, which returns the existing None value, and the subsequent .setdefault/.append raises AttributeError ('NoneType' object has no attribute 'setdefault'/'append'). The exception is not in any caught tuple (\_plan_dynamic catches IntegrationConflictError/RepositoryBoundaryError/UnicodeError; validation.\_claude_config catches json.JSONDecodeError/IntegrationConflictError/RepositoryBoundaryError; cli.run catches CommandResolutionError/OSError/RuntimeError), so `project-standards agent-handoff validate`, `drift-check`, and `adopt` crash with a traceback instead of reporting AH-CLAUDE-CONFIG-INVALID. Reproduced end-to-end: validate_repository and drift_check both raise AttributeError on a scratch repo with '{"hooks": null}'.
- Fix: In merge_claude_settings (claude.py lines 101-104), replace the two setdefault calls with None-tolerant assignment: `hooks_value = merged.get("hooks")` ; `if hooks_value is None: hooks_value = {}; merged["hooks"] = hooks_value` ; then `hooks = cast(dict[str, object], hooks_value)` ; `session_start_value = hooks.get("SessionStart")` ; `if session_start_value is None: session_start_value = []; hooks["SessionStart"] = session_start_value`. Non-dict/non-list non-None values already raise IntegrationConflictError in \_session_start_groups, so only None reaches these lines. Add '{"hooks": null}' and '{"hooks": {"SessionStart": null}}' cases to tests/agent_handoff/test_claude.py asserting merge_claude_settings_json succeeds and installs the managed group.
- Verification: uv run python3 -c "from project_standards.agent_handoff.integrations.claude import merge_claude_settings_json; merge_claude_settings_json('{\"hooks\": null}'); merge_claude_settings_json('{\"hooks\": {\"SessionStart\": null}}')" exits 0; then uv run pytest tests/agent_handoff/test_claude.py tests/agent_handoff/test_validation.py
- Dependencies: none
- Effort: S

**F-002 — Replace never-true `github.event_name == 'workflow_call'` guards in validate-specs.yml**

- Category: Correctness · Severity: High · Confidence: High
- Location: .github/workflows/validate-specs.yml:61,67,75 (tests locking the bug: tests/test_validate_specs_workflow.py:86,105,110)
- Evidence: `.github/workflows/validate-specs.yml:67:          PROJECT_STANDARDS_REF: ${{ github.event_name == 'workflow_call' && inputs.standards-ref || 'v5' }}`
- Problem: Inside a called reusable workflow, `github.event_name` is the CALLER's triggering event (push/pull_request/...) and is never the string 'workflow_call' (confirmed by actions/runner issue #3146 and github/docs issue #16515). Consequences: (1) line 67 — `github.event_name == 'workflow_call'` is always false, so the expression always evaluates to 'v5' and a consumer's `standards-ref` input (e.g. `standards-ref: v5.0.1` or a branch/SHA matching their `uses:` pin) is silently ignored; the consumer validates with whatever `v5` currently points at, defeating the pin. (2) lines 61 and 75 — `github.event_name != 'workflow_call'` is always true, so the `||` short-circuits and `strict-lint: false` is silently ignored: a consumer opting out of strict lint still fails CI on advisory warnings. The sibling reusable workflows already use the correct patterns (validate-markdown-frontmatter.yml uses `inputs.standards-ref` directly; format.yml/lint-markdown.yml use the `format('{0}', inputs.x) != 'false'` idiom with an SA-001 comment). tests/test_validate_specs_workflow.py asserts the broken strings verbatim, making the tests tautological.
- Fix: In .github/workflows/validate-specs.yml: (a) line 67 — change the env value to `${{ inputs.standards-ref || 'v5' }}` (on direct push/PR events `inputs.standards-ref` is empty so the fallback still yields 'v5'; on workflow_call the input's own default is 'v5'). (b) lines 61 and 75 — replace the parenthetical `(github.event_name != 'workflow_call' || inputs.strict-lint)` with `format('{0}', inputs.strict-lint) != 'false'` (empty on direct events → runs; typed boolean false from a caller → skips), matching format.yml's documented SA-001 pattern. (c) Update tests/test_validate_specs_workflow.py lines 86, 105, and 110 to assert the new expressions (assert behavior-relevant substrings `inputs.standards-ref || 'v5'` and `format('{0}', inputs.strict-lint) != 'false'`).
- Verification: uv run pytest tests/test_validate_specs_workflow.py; then in a consumer repo call the workflow with `strict-lint: false` and confirm the two 'Lint specs' steps are skipped, and with `standards-ref: <branch>` and confirm the Install step logs that ref in the git+https URL.
- Dependencies: none
- Effort: S

**F-003 — Carry forward create-only locked units absent from rendered content instead of dropping them**

- Category: Correctness · Severity: High · Confidence: High
- Location: src/project_standards/control_plane/planner.py:1264-1267 (root cause), src/project_standards/control_plane/planner.py:890-891 (interacting classification)
- Evidence:

```text
src/project_standards/control_plane/planner.py:1266:            if unit is None:
src/project_standards/control_plane/planner.py:1267:                continue
```

- Problem: When a consumer deletes a create-only semantic unit from a shared file, \_classify_desired returns PRESERVE (line 890), the rendered content therefore lacks the unit's scope, and \_locked_after silently drops the unit from next_lock. On the following reconcile the previous lock no longer records the unit, so_classify_desired hits the previous-is-None/current-is-None branch and plans CREATE: the consumer's deliberate deletion is reverted one cycle later. Reconciliation is non-convergent (validate reports drift immediately after a successful apply) and the create-only preservation contract is violated. Empirically confirmed: plan0 CREATE key:/tool (create-only, JSON); consumer deletes the key; plan1 = PRESERVE with next_lock.artifacts == []; plan2 (previous_lock = plan1.next_lock, file unchanged) = UPDATE re-inserting the deleted key into the consumer's file.
- Fix: In \_locked_after (planner.py, inside the `for group in target_groups:` loop), when `units.get(group.scope)` is None, look up `prior = previous.get((group.target.original, group.adapter.value, group.scope))`; if `prior is not None and prior.policy is ArtifactPolicy.CREATE_ONLY`, append `prior` unchanged to `locked` instead of `continue`. This keeps the create-only ownership record durable so every later plan classifies the unit as PRESERVE (line 890) and never resurrects it. Add a regression test in tests/control_plane/test_planner.py mirroring the scratchpad repro: create-only JSON contribution, apply, delete the key, assert plan1 keeps the artifact in next_lock and plan2 (using plan1.next_lock) produces no CREATE/UPDATE for that scope. Existing tests only cover edited (test_planner.py:207) and pre-existing (test_planner.py:264) create-only files, not deleted units.
- Verification: uv run pytest tests/control_plane/test_planner.py -k create_only; plus the new regression test asserting plan2 has no mutating action after a consumer deletes a create-only unit
- Dependencies: none
- Effort: M

**F-004 — Catch ControlPlaneBusyError in CLI read/plan paths so lock contention yields CP-BUSY instead of a traceback**

- Category: Correctness · Severity: High · Confidence: High
- Location: src/project_standards/control_plane/cli.py:665,473,733-738; src/project_standards/control_plane/recovery.py:403,459,518; src/project_standards/control_plane/config_edit.py:191-194
- Evidence: `src/project_standards/control_plane/cli.py:665:    except (ControlPlaneError, PackageContractError, OSError, ValueError) as exc:`
- Problem: ControlPlaneBusyError subclasses RuntimeError (locking.py:23), and only executor.py (lines 857, 1224) catches it. run(), run*init(), validate_repository(), plan_recovery()/apply_recovery() paths (recovery.py catches only ValueError/OSError), and config_edit's set_standard*\* all let it propagate; the top-level dispatcher in src/project_standards/cli.py calls \_reconcile_run/\_init_run/validate_repository with no boundary. Reproduced live: run(["--repo", repo, "--check"]) while another process holds the exclusive .standards lock raises uncaught ControlPlaneBusyError -> Python traceback. This violates spec NFR-009 ('concurrent mutation/read-versus-write fails with a stable finding') and the 0/1/2 exit-code contract.
- Fix: In src/project_standards/control_plane/cli.py, import ControlPlaneBusyError from control_plane.locking and add it to the except tuples at lines 665 (run), 473 (run_init), and add an `except ControlPlaneBusyError` in validate_repository (before the generic handlers), emitting_emit_error(json_mode, "CP-BUSY", str(exc), exit_code=1) in run/run_init and printing `CP-BUSY: <msg>` with return 1 in validate_repository. In recovery.py, add ControlPlaneBusyError (or RuntimeError) to the three `except ValueError, OSError:` clauses at lines 403, 459, 518, returning the existing refused-plan/CP-RECOVERY-APPLY results with a CP-BUSY code for the contention case. In config_edit.py \_edit_config, catch ControlPlaneBusyError and re-raise as ControlPlaneError("CP-BUSY: ...") or document that callers must catch it and add handling in src/project_standards/cli.py_try_v5_adopt. Add a CLI test that holds fcntl.LOCK_EX on .standards and asserts reconcile --check exits 1 with a CP-BUSY diagnostic.
- Verification: Re-run the repro: hold fcntl.LOCK_EX on <repo>/.standards in one process, then `project-standards reconcile --check --repo <repo>` must exit 1 printing a CP-BUSY diagnostic with no traceback; run the new test plus `uv run pytest tests/control_plane/test_cli.py tests/control_plane/test_recovery.py`.
- Dependencies: none
- Effort: M

**F-005 — Stop whole-file removal of bounded-block legacy targets the new package does not re-materialize**

- Category: Correctness · Severity: High · Confidence: High
- Location: src/project_standards/control_plane/migration.py:1308-1342,1547-1548
- Evidence: `src/project_standards/control_plane/migration.py:1329:            if claim.target.original in replacement_targets:`
- Problem: \_removal_actions emits a whole-file REMOVE ControlAction for every REMOVE-disposition claim, including BOUNDED_BLOCK signatures, skipping only targets present in reconciliation.targets. Planner targets come solely from selected payloads' artifacts/contributions plus the previous lock (planner.py_target_paths), so if the v5 payload no longer materializes content for a bounded-block target (dropped contribution, or a contribution whose materializes(effective_config) is false under the migrated options), the stripped outside-bytes view computed by \_retirement_views/\_strip_bounded_block (docstring: 'while preserving outside bytes') is never written and executor_remove_legacy unlinks the ENTIRE file — the whole-file digest in legacy_preconditions matches, so the precondition check passes. Consumer-owned bytes outside the managed block are deleted. No manifest validation ties bounded signature targets to contributions (package_contract/payload.py signature checks only ids/pointers), and no test in tests/control_plane/test_migration.py covers this path.
- Fix: In migration.py \_plan_legacy_migration, after plan_reconciliation, compute the set of bounded-block REMOVE claim targets (from \_retirement_views' bounded view) that are absent from reconciliation.targets; for each, either (a) append an explicit UPDATE ControlAction + executor support writing the stripped content bytes for that target instead of letting \_removal_actions emit a REMOVE, or (b) minimally, emit an error ControlFinding (e.g. CP-MIGRATION-BOUNDED-ORPHAN) making the plan inapplicable so apply is refused. Also change \_removal_actions to only emit target REMOVE actions for claims whose signature kind is WHOLE_FILE (pass the payloads map so the kind is known). Add a test: bounded-block signature on a file the v5 payload does not target, provider claims REMOVE, assert the plan does not delete the file / is not applicable.
- Verification: New test in tests/control_plane/test_migration.py constructing a payload with a bounded-block legacy signature whose target has surrounding consumer bytes and no v5 contribution to that target; assert after apply (or plan) that the file still exists with outside bytes preserved. `uv run pytest tests/control_plane/test_migration.py tests/control_plane/test_executor.py`.
- Dependencies: none
- Effort: M

**F-006 — Cut agent-handoff 1.2 with parenthesized except clauses in the SessionStart hook (SyntaxError on consumer Python < 3.14)**

- Category: Correctness · Severity: High · Confidence: High
- Location: src/project_standards/payloads/agent-handoff/1.1/hooks/session-start/session_start.py:101,235,246 and src/project_standards/payloads/agent-handoff/1.1/provider-resources/managed/hook.py:101,235,246 (byte-identical files) ; also src/project_standards/bundles/agent-handoff/hooks/session-start/session_start.py:101,235,246 (byte-identical copies: standards/agent-handoff/hooks/session-start/session_start.py, standards/agent-handoff/versions/1.1/hooks/session-start/session_start.py, standards/agent-handoff/versions/1.1/provider-resources/managed/hook.py, src/project_standards/payloads/agent-handoff/1.1/hooks/session-start/session_start.py)
- Evidence:

```text
src/project_standards/payloads/agent-handoff/1.1/hooks/session-start/session_start.py:101:    except OSError, subprocess.TimeoutExpired:
src/project_standards/bundles/agent-handoff/hooks/session-start/session_start.py:101:    except OSError, subprocess.TimeoutExpired:
```

- Problem: The hook uses PEP 758 unparenthesized multi-exception syntax (also `except InputError, UnicodeError:` at 235 and `except OSError, UnicodeError:` at 246), which is only valid on Python 3.14+. The hook is installed at .agents/hooks/agent-handoff/session_start.py mode 0755 and executed directly via its `#!/usr/bin/env python3` shebang by both harness integrations (claude-session-start.json runs `${CLAUDE_PROJECT_DIR}/.agents/hooks/agent-handoff/session_start.py`), i.e. under the consumer machine's system python3, not any project venv. Verified: py_compile under CPython 3.13.13 fails with `SyntaxError: multiple exception types must be parenthesized` at line 101. On Debian 13 (3.13), Ubuntu 24.04 (3.12), and similar hosts the hook crashes at every session start, so no session context is ever injected. agent-handoff is not a Python-only standard, and neither adopt.md nor README.md documents a Python 3.14 prerequisite (grep for 'python' in those docs returns nothing). The repo gate never catches this because ruff/basedpyright/pytest all run on 3.14.
- Fix: These are released catalog-5 bytes and immutable, so publish a new payload version: create standards/agent-handoff/versions/1.2/ (which projects to src/project_standards/payloads/agent-handoff/1.2/ via the symlink layout) as a copy of 1.1 with hooks/session-start/session_start.py and provider-resources/managed/hook.py changed only at lines 101, 235, 246 to parenthesized tuples: `except (OSError, subprocess.TimeoutExpired):`, `except (InputError, UnicodeError):`, `except (OSError, UnicodeError):` (keep both files byte-identical to each other). Recompute the sha256 digests for the `hook` resource and `hook` artifact entries in the new payload.toml, register 1.2 in the catalog, and leave 1.1 untouched. Optionally add a CI guard that py_compiles all hooks/ payload files under the oldest supported system Python (e.g. 3.11). The V1 bundle copy under src/project_standards/bundles/agent-handoff/hooks/session-start/session_start.py carries the identical defect and is fixed by the same edit there (bundles/ is not payload-frozen).
- Verification: /home/chris/.local/share/uv/python/cpython-3.13-linux-x86_64-gnu/bin/python3.13 -m py_compile src/project_standards/payloads/agent-handoff/1.2/hooks/session-start/session_start.py exits 0; `uv run project-standards validate` and `packages check-release` stay green; 1.1 bytes unchanged (git diff empty under standards/agent-handoff/versions/1.1/).
- Dependencies: Batch into the single agent-handoff 1.2 payload cut together with F-007, F-010, F-024, F-027.
- Effort: M

**F-007 — Fix IndexError in agent-handoff \_reference_findings on empty/whitespace/angle-bracket-only link targets (new payload version)**

- Category: Correctness · Severity: High · Confidence: High
- Location: src/project_standards/payloads/agent-handoff/1.1/providers/agent_handoff.py:649-652 ; also src/project_standards/agent_handoff/validation.py:468-471; src/project_standards/agent_handoff/cli.py:177-179
- Evidence:

```text
src/project_standards/payloads/agent-handoff/1.1/providers/agent_handoff.py:651:                raw_target.strip().strip("<>").split(maxsplit=1)[0].split("#", maxsplit=1)[0]
src/project_standards/agent_handoff/validation.py:470:                raw_target.strip().strip("<>").split(maxsplit=1)[0].split("#", maxsplit=1)[0]
```

- Problem: For a Markdown link whose target is whitespace-only or `<>` — e.g. `[text]( )` or `[text](<>)` in docs/handoff/state.md, docs/TODO.md, or any sessions/bugs log — `raw_target.strip().strip("<>")` yields the empty string, and `"".split(maxsplit=1)` returns `[]`, so `[0]` raises IndexError (reproduced). The provider runner wraps provider exceptions in ManifestError ('Python provider ... failed (IndexError)', provider_runner.py:102-103), so one malformed link in a consumer-edited handoff document aborts the entire `project-standards validate` run with an infrastructure error instead of emitting an AH-REFERENCE-MISSING finding. These documents are free-form and routinely edited by humans and agents, so the trigger is realistic. Secondary defect on the same line: `<path with spaces>` angle-bracket targets are truncated at the first space by `split(maxsplit=1)[0]`, producing spurious missing-reference findings for valid links.
- Fix: Released bytes are immutable — fold into the same new agent-handoff 1.2 payload as the hook fix. In providers/agent_handoff.py `_reference_findings`, replace the one-shot expression: first compute `cleaned = raw_target.strip()`; if it starts with '<' and ends with '>', use its inner text verbatim (no whitespace split); otherwise take `parts = cleaned.split(maxsplit=1)` and use `parts[0]` only when parts is non-empty. Then strip the '#fragment' and unquote as today. If the resulting target is empty, emit an AH-REFERENCE-MISSING finding (message: link target is empty) instead of crashing. Update the provider-code resource digest in the 1.2 payload.toml. The same guard must land in the live source module (src/project_standards/agent_handoff/validation.py:468-471 and cli.py:177-179), which is editable directly; the released provider copy requires the new payload version.
- Verification: Unit test: run_validate with a snapshot of docs/handoff/state.md containing `[x]( )`, `[x](<>)`, and `[x](<docs/handoff/a b.md>)` (with that file present as a regular snapshot) returns findings without raising; the first two yield AH-REFERENCE-MISSING, the third yields none.
- Dependencies: Batch into the single agent-handoff 1.2 payload cut together with F-006, F-010, F-024, F-027. Ship in the same agent-handoff 1.2 payload as the except-syntax fix.
- Effort: M

**F-008 — Constrain extract heading-selector regex to a single heading line**

- Category: Correctness · Severity: High · Confidence: High
- Location: src/project_standards/specs/commands/extract.py:52
- Evidence: `src/project_standards/specs/commands/extract.py:52:    m = re.search(rf"^#+\s.*{re.escape(selector)}.*?(?=^#+\s|\Z)", body, re.M | re.S)`
- Problem: With re.S the greedy `.*` between `^#+\s` and the selector crosses newlines, so the match always starts at the FIRST heading in the document and extends to the heading after the LAST occurrence of the selector anywhere in prose. Verified: on a body with sections 1-4, selector "Glossary" (a §3 heading) returns a slice starting at "## 1. Purpose"; selector "banana" (prose-only, not a heading) reports found=True with a multi-section slice. `spec extract <heading-text>` therefore returns wrong markdown for essentially every heading selector that is not in the first section, and false positives for non-heading text. The heading branch has zero tests (tests/test_spec_extract.py covers only §/appendix/id selectors).
- Fix: In extract_slice, replace line 52's pattern with one that keeps the selector on the heading line itself: `m = re.search(rf"^#+\s[^\n]*{re.escape(selector)}[^\n]*$.*?(?=^#+\s|\Z)", body, re.M | re.S)`. Add tests in tests/test_spec_extract.py: (a) selector matching a mid-document heading returns a slice that startswith that heading line; (b) selector appearing only in prose returns found=False.
- Verification: uv run python -c "from project_standards.specs.commands.extract import extract_slice; from project_standards.specs.document import parse_document; d=parse_document('t','---\na: b\n---\n## 1. One\nx\n## 2. Two\nbanana\n'); r=extract_slice(d,'Two'); assert r.markdown.startswith('## 2. Two'), r.markdown; assert not extract_slice(d,'banana').found"
- Dependencies: none
- Effort: S

**F-009 — Make document parsing and validate/lint fence-aware like the upgrade path**

- Category: Correctness · Severity: High · Confidence: High
- Location: src/project_standards/specs/registry.py:80-95, src/project_standards/specs/document.py:86-100, src/project_standards/specs/commands/validate.py:88-104,126-137,185-210, src/project_standards/specs/commands/lint.py:21-25
- Evidence: `src/project_standards/specs/registry.py:84:        if m := re.match(r"^(#{2,4})\s+(.*)$", line):`
- Problem: registry.headings(), the ID_TOKEN scan in parse_document, and every line scan in validate.py/lint.py ignore fenced code blocks, while upgrade.py deliberately tracks fences (\_FENCE_OPEN/\_FENCE_CLOSE, comment cites Codex CR-003) for the same hazard. Verified: injecting a ```markdown fence containing '## 5. Interfaces' and a malformed example table into an otherwise-valid light spec makes validate emit spurious SV-ORDER and SV-TABLE errors — validate exits 1 on a legitimate spec, and upgrade's Gate 1 (validate-clean) then refuses to upgrade it. SV-SECTION, SV-XREF, SV-GAP coverage, SL-PLACEHOLDER, and anchor slugs are similarly polluted by fenced examples (e.g. '## comment' lines in bash samples).
- Fix: Move \_FENCE_OPEN/\_FENCE_CLOSE from commands/upgrade.py into registry.py and add `def mask_fenced_code(body: str) -> str` that replaces every line inside a fence (and the fence delimiter lines) with an empty line, preserving line count. In document.parse_document, compute `masked = mask_fenced_code(body)` and use masked for headings(), section_numbers, \_anchor_slugs, declared_prefixes and the ID_TOKEN loop; store body unmasked (extract slices stay verbatim). In validate.py use mask_fenced_code(doc.body) for the omission-note scan in \_check_sections, \_check_references, and \_check_tables; in lint.py mask before the SL-PLACEHOLDER/SL-GUIDANCE line loop. Update upgrade.py imports to the moved constants.
- Verification: Repro: build a valid light spec, insert '`markdown\n## 5. Interfaces\n| a | b |\n|---|---|\n| 1 | 2 | 3 |\n`' before '## 2. Scope', run validate_document — it must return no findings (currently returns SV-ORDER + SV-TABLE). Then uv run pytest tests/test_spec_validate.py tests/test_spec_upgrade.py tests/test_spec_document.py
- Dependencies: none
- Effort: M

**F-010 — Enforce or remove dead policy knobs (max_heading_depth et al.)**

- Category: Correctness · Severity: Medium · Confidence: High
- Location: src/project_standards/agent_handoff/policy.py:46-48,66,70; src/project_standards/agent_handoff/policy.py:252-360 ; also src/project_standards/payloads/agent-handoff/1.1/resources/policy.toml:42-43,98,112 (identical provider-resources/managed/policy.toml)
- Evidence:

```text
src/project_standards/agent_handoff/policy.py:66:    require_pointer_for_details_over_chars: int | None = Field(default=None, gt=0)
...
policy.py:70:    append_only: bool = False
src/project_standards/payloads/agent-handoff/1.1/resources/policy.toml:42:prefer_bullets = true
```

- Problem: The policy schema declares max_heading_depth, prefer_bullets, require_overflow_pointer (ShapeDefaults, policy.py:46-48), require_pointer_for_details_over_chars (policy.py:66) and append_only (policy.py:70), and the shipped bundles/agent-handoff/resources/policy.toml sets all of them (max_heading_depth = 3, require_overflow_pointer = true, append_only = true, require_pointer_for_details_over_chars = 700), but check_document and the rest of this package never read any of them — they are silent no-ops on the bundled/legacy validation path. Meanwhile the released 1.1 packaged provider (standards/agent-handoff/versions/1.1/providers/agent_handoff.py:374-380) does enforce max_heading_depth, so the same repository validates differently depending on whether the v2 selected provider or the bundled providers.validate path runs.
- Fix: In policy.py check_document, implement at least max_heading_depth mirroring the 1.1 provider: `max_depth = policy.shape.defaults.max_heading_depth` then flag any line matching re.match(r'^(#{1,6})\s+', line) whose hash run exceeds max_depth. For prefer_bullets, require_overflow_pointer, require_pointer_for_details_over_chars, and append_only either implement equivalent checks or delete the fields from ShapeDefaults/DocumentPolicy and from bundles/agent-handoff/resources/policy.toml (note: the payloads/ and standards/ copies of policy.toml are immutable released bytes — change only the bundles/ copy and the schema), documenting the decision. The released payload's policy.toml (payloads/agent-handoff/1.1/resources/policy.toml:42-43,98,112) advertises the same unenforced knobs; removing or enforcing them in payload bytes requires the agent-handoff 1.2 cut.
- Verification: uv run pytest tests/agent_handoff/test_policy.py; add a test asserting a document with '#### deep heading' under max_heading_depth=3 produces an AH-SHAPE finding on the bundled path
- Dependencies: Batch into the single agent-handoff 1.2 payload cut together with F-006, F-007, F-024, F-027.
- Effort: M

**F-011 — Return exit code 1 from legacy-report --json when evidence is blocked**

- Category: Correctness · Severity: Medium · Confidence: High
- Location: src/project_standards/agent_handoff/cli.py:254-258
- Evidence:

```text
src/project_standards/agent_handoff/cli.py:254:        if args.json:
            # The selected provider owns the serialized evidence bytes.
            sys.stdout.write(result.content.decode("utf-8"))
            return 0
```

- Problem: On the v2 selected-command path, `legacy-report --json` unconditionally returns 0 after writing the provider content, while the text path on the very next line returns `_emit(evidence, as_json=False)` which returns 1 when the report is blocked. legacy_report can produce an error-severity finding (AH-LEGACY-DUPLICATE-HOOK, legacy.py:312 severity="error"), so the same repository yields exit 1 without --json and exit 0 with --json. The legacy provider fallback (providers.extract) returns 1 in both modes. This violates the stated exit-code contract (1 = findings) and breaks CI consumers that parse JSON and rely on the exit code.
- Fix: In cli.py \_run_read_command, change the json branch to `sys.stdout.write(result.content.decode("utf-8")); return 1 if evidence.blocked else 0`. Add a routing test (tests/agent_handoff/test_selected_routing.py) with a repo containing both .agents/hooks/agent-handoff/session_start.py and a legacy .claude/hooks/session_start.py registration, asserting `run(["legacy-report", "--repo", ..., "--json"]) == 1`.
- Verification: uv run pytest tests/agent_handoff/test_selected_routing.py -k legacy_report
- Dependencies: none
- Effort: S

**F-012 — Use superset (not equality) for the V5 adoptable-defaults gate in legacy adopt routing**

- Category: Correctness · Severity: Medium · Confidence: Medium
- Location: src/project_standards/cli.py:81-88
- Evidence: `src/project_standards/cli.py:88:    return defaults == set(_ADOPTABLE_STANDARD_IDS)`
- Problem: v5_catalog_has_all_adoptable_defaults requires the catalog's set of standards-with-defaults to EQUAL the seven legacy adoptable ids. Adding an eighth consumer standard with a default version to a future catalog — a purely additive change the versioning contract classifies as MINOR/PATCH-safe — makes the equality false, and_try_v5_adopt then fails every V2 adopt invocation with exit 2: "installed V2 catalog does not expose the complete consumer default set". The gate's stated purpose ("Return whether V2 can replace the complete legacy consumer surface") only needs coverage of the legacy seven, which a superset satisfies; equality turns allowed catalog growth into a hard CLI regression.
- Fix: In src/project_standards/cli.py change line 88 to `return defaults.issuperset(_ADOPTABLE_STANDARD_IDS)`. Add a unit test constructing a ConsumerCatalog with the seven legacy defaults plus one extra defaulted standard and asserting v5_catalog_has_all_adoptable_defaults returns True, and one with a missing legacy default asserting False.
- Verification: uv run pytest tests/test_adopt_cli.py (plus the new test) passes; a catalog fixture with 8 defaulted standards routes through \_try_v5_adopt instead of returning exit 2.
- Dependencies: none
- Effort: S

**F-013 — Clean up partially staged targets when \_stage_targets fails mid-loop**

- Category: Correctness · Severity: Medium · Confidence: High
- Location: src/project_standards/control_plane/executor.py:247-289, src/project_standards/control_plane/executor.py:758-766, src/project_standards/control_plane/executor.py:1146-1151
- Evidence: `src/project_standards/control_plane/executor.py:758:            staged = _stage_targets(`
- Problem: \_stage_targets builds its staged dict locally and only returns it on full success. If staging fails on target N>1 (fault hook, ENOSPC, permission error, or the st_dev check), the already-staged_StagedTarget entries for targets 1..N-1 are lost: their .project-standards-_.tmp files remain in the consumer repository and their parent directory descriptors leak (one fd per staged target). Callers \_apply_locked (line 758) and apply_legacy_migration (line 1146) initialize staged={} and only reassign after the call returns, so the finally-block \_cleanup_staged runs against the empty dict; created directories containing orphan temps also survive because rmdir fails silently under suppress(OSError). This violates the module's own tested invariant (test_executor.py repeatedly asserts `not list(repo.rglob(".project-standards-_.tmp"))`after failures) — the existing parametrized failure test only faults at ("stage", "alpha.txt"), the first target, so the case never fires in CI. Empirically confirmed: injecting a fault at ("stage", "nested/beta.txt") leaves /repo/.project-standards-<token>.tmp behind. Additionally,`target = targets[action.target]` at line 266 sits before the try block, so a KeyError from an action without a matching plan target leaks that action's parent_descriptor too.
- Fix: In \_stage_targets (executor.py), wrap the entire per-action loop body in a try/except BaseException that, before re-raising, cleans up everything staged so far: for each item in the local staged dict, `with suppress(OSError): os.unlink(item.temporary, dir_fd=item.source_descriptor)` and `with suppress(OSError): os.close(item.parent_descriptor)`. Also move `target = targets[action.target]` (line 266) inside the existing inner try so a KeyError closes the current parent_descriptor. Alternative equivalent shape: change the signature to accept the caller's staged dict and populate it in place so the callers' existing finally/\_cleanup_staged covers partial failure; if so, update both call sites (lines 758 and 1146) to pass the pre-initialized dict and drop the return-assignment. Then add a parametrize case ("stage", "nested/beta.txt", ()) to test_failure_returns_exact_published_prefix_and_preserves_previous_lock in tests/control_plane/test_executor.py — its existing `assert not list(repo.rglob(".project-standards-*.tmp"))` covers the regression.
- Verification: cd /home/chris/projects/project-standards && uv run pytest tests/control_plane/test_executor.py -q (with the new parametrize case; before the fix, a fault at ('stage','nested/beta.txt') leaves repo/.project-standards-\*.tmp — reproduced in this review)
- Dependencies: none
- Effort: S

**F-014 — Validate provider FINDINGS fields instead of blind casts in \_typed_result**

- Category: Correctness · Severity: Medium · Confidence: High
- Location: src/project_standards/control_plane/providers.py:516-531
- Evidence:

```text
src/project_standards/control_plane/providers.py:520:                        code=cast(str, table["code"]),
                        severity=cast("Literal['error', 'warning']", table["severity"]),
```

- Problem: ControlFinding is a plain dataclass with no runtime validation, and \_typed_result populates it from provider JSON via typing.cast only (code, severity, path, identity, message, hint, line, locus). The only prior validation is the provider's own payload-authored output schema, which the control plane does not require to constrain these types. Consequences on a buggy provider: (a) a severity outside {'error','warning'} (e.g. 'ERROR', 'info') silently bypasses the executor's post-apply gate `any(finding.severity == "error" ...)` (executor.py:637), so a failing verification is reported as success; (b) a non-string code/identity/path or non-int line produces mixed-type tuples in finding_sort_key (diagnostics.py:80-93), and sorted() in sort_findings raises TypeError inside_verify (executor.py:636) — after targets are already published — which the broad BaseException handler misclassifies as CP-APPLY-FAILED instead of CP-VERIFY. Every other provider effect in this module gets pydantic validation (MutationPlanSchema, MigrationReport); FINDINGS is the one unvalidated boundary.
- Fix: In providers.py \_typed_result, replace the cast-based construction with explicit runtime checks before building each ControlFinding: require isinstance str for code/path/identity/message/hint, require table['severity'] in ('error','warning'), require line to be int or None and locus to be str or None; raise ControlPlaneError('findings provider returned an invalid finding') on any violation (same error path as the existing not-a-dict check). Alternatively introduce a small pydantic model (e.g. ProviderFindingSchema in control_plane/schemas.py) and model_validate each raw finding, mapping ValidationError to the same ControlPlaneError. Add a unit test in tests/control_plane feeding a findings provider result with severity 'info' and with an integer code, asserting ControlPlaneError.
- Verification: cd /home/chris/projects/project-standards && uv run pytest tests/control_plane -k provider -q && uv run basedpyright src/project_standards/control_plane/providers.py
- Dependencies: none
- Effort: S

**F-015 — Move InstalledDistribution.current() inside the CLI error boundaries**

- Category: Correctness · Severity: Medium · Confidence: High
- Location: src/project_standards/control_plane/cli.py:389,608,704
- Evidence: `src/project_standards/control_plane/cli.py:608:    selected_distribution = distribution or InstalledDistribution.current()`
- Problem: InstalledDistribution.current() raises PackageContractError for a broken/corrupted installation (distribution.py:159-163 and many more raise sites), but in run() (line 608), run_init() (line 389), and validate_repository() (line 704) it is called BEFORE the try block that catches PackageContractError, and the top-level dispatcher in src/project_standards/cli.py invokes these functions with no surrounding boundary. A damaged wheel/payload install therefore produces an unhandled traceback instead of the documented stable `_emit_error` exit-2 diagnostic. run_render is unaffected because current() runs inside selected_command within its try.
- Fix: In src/project_standards/control_plane/cli.py, move the `selected_distribution = distribution or InstalledDistribution.current()` assignment to the first statement inside the existing `try:` block in run() (before detect_control_plane_state), in run_init() (before the `if not args.migrate` branch), and in validate_repository() (before detect_control_plane_state). No behavior change on the success path; PackageContractError then routes to the existing handlers (exit 2).
- Verification: Unit test monkeypatching InstalledDistribution.current to raise PackageContractError and asserting run([]), run_init(["--catalog","5"]), and validate_repository(tmp_path) return 2 (or 2/1 for validate) without raising; `uv run pytest tests/control_plane/test_cli.py`.
- Dependencies: none
- Effort: S

**F-016 — Re-parse rendered migration config; \_render_config emits unparseable TOML for U+007F strings**

- Category: Correctness · Severity: Medium · Confidence: High
- Location: src/project_standards/control_plane/migration.py:1093,1105-1123,1475
- Evidence: `src/project_standards/control_plane/migration.py:1093:        return json.dumps(value, ensure_ascii=False)`
- Problem: \_toml_value/\_toml_key serialize strings with json.dumps, which escapes U+0000-U+001F but leaves U+007F (DEL) literal; TOML forbids unescaped \x7f in basic strings. Reproduced: a DesiredConfig whose package config contains "x\x7fy" renders to bytes that parse_config rejects (ControlPlaneError: config is not valid TOML).\_plan_legacy_migration never re-parses config_content (line 1475) and the executor publishes the bytes verbatim, so a migration whose provider carries such a legacy value 'succeeds' and leaves the repository in MALFORMED state — breaking the transactional migration promise.
- Fix: In migration.py: (1) in \_plan_legacy_migration, immediately after `config_content = _render_config(desired)` call `parse_config(config_content)` (import from codec) and raise ControlPlaneError('migrated desired config could not be rendered canonically') on failure; (2) in_toml_value/\_toml_key, post-process the json.dumps result to replace "\x7f" with "\\u007F" so the rendered TOML is always valid. Add a unit test rendering a config containing "\x7f" and asserting parse_config round-trips.
- Verification: uv run python3 -c "from project_standards.control_plane.migration import \_render_config; from project_standards.control_plane.codec import parse_config; from project_standards.control_plane.models import DesiredConfig; d=DesiredConfig.model_validate({'project_standards':{'schema_version':'1.0','catalog':'5'},'standards':{'x-y':{'enabled':True,'version':'latest','config':{'n':'a\x7fb'}}}}); parse_config(\_render_config(d))" exits cleanly; `uv run pytest tests/control_plane/test_migration.py`.
- Dependencies: none
- Effort: S

**F-017 — Validate provider claim targets before \_retirement_views indexes legacy_files (KeyError crash)**

- Category: Correctness · Severity: Medium · Confidence: High
- Location: src/project_standards/control_plane/migration.py:639,1487-1491
- Evidence: `src/project_standards/control_plane/migration.py:639:            current = bounded.get(claim.target, legacy_files[claim.target.original])`
- Problem: providers.py validates that a migration report's signature ids are declared, but never that claim.target is among the signature's declared targets or exists on disk. \_retirement_views runs at migration.py:1487, before \_claim_findings (line 1533) would flag a mismatched claim. For a REMOVE claim on a BOUNDED_BLOCK signature whose target file was never read into the legacy_files cache (nonexistent file, or an arbitrary target), the eagerly-evaluated default `legacy_files[claim.target.original]` raises KeyError — which is not in run_init's except tuple (ControlPlaneError, PackageContractError, OSError, ValueError), so a buggy or hostile migrate provider crashes `project-standards init --catalog N --migrate` with a traceback instead of a content-safe finding or error.
- Fix: In migration.py \_retirement_views, replace line 639 with an explicit lookup: `source = bounded.get(claim.target); if source is None: source = legacy_files.get(claim.target.original); if source is None: raise ControlPlaneError("legacy claim targets an unobserved file")` (also guard `signatures[claim.signature_id]` similarly). Alternatively/additionally, in providers.py MIGRATION_REPORT handling, reject reports where any claim.target is not among the claimed signature's declared targets. Add a test invoking_retirement_views (or the plan path with a stub provider) with a REMOVE bounded claim on a missing target, asserting ControlPlaneError.
- Verification: uv run pytest tests/control_plane/test_migration.py -k retirement (new test); confirm plan_legacy_migration with a stub provider returning such a claim yields exit 2 with a stable message, not a traceback.
- Dependencies: none
- Effort: S

**F-018 — Reconcile meta/versioning.md classification table with the internal-additive PATCH rule**

- Category: Docs · Severity: Medium · Confidence: High
- Location: meta/versioning.md:119 (table) vs meta/versioning.md:86 (prose)
- Evidence: `meta/versioning.md:119: | **Catalog / package payload set** | An advertised version removed; a same-catalog-major ordinary default changed incompatibly; a breaking candidate promoted to ordinary default | A compatible payload added; an opt-in breaking candidate advertised while the ordinary default and prior selections remain available | — |`
- Problem: The change-classification table says any 'compatible payload added' is MINOR and leaves the PATCH cell empty ('—'), but §Catalog and package channels (line 86) and the shipped release.py rule (src/project_standards/package_contract/release.py:220-230) classify a purely additive internal-role advertisement as PATCH — exactly how the 5.0.2 release (adding standard-bundle-authoring@2.1) is classified. The normative classification table therefore contradicts the release the repo just cut and the tool's own check-release behavior; anyone classifying by the table would call 5.0.2 misversioned.
- Fix: In meta/versioning.md's Change classification table, 'Catalog / package payload set' row: change the MINOR cell to 'A compatible consumer-visible payload added; an opt-in breaking candidate advertised while the ordinary default and prior selections remain available' and change the PATCH cell from '—' to 'A purely additive advertisement of an internal-role payload (never consumer-selectable)'.
- Verification: Table row and line 86 prose agree; `uv run project-standards packages check-release --baseline v5.0.1` still classifies the 2.1 addition as patch.
- Dependencies: none
- Effort: S

**F-019 — Handle inline JSONC comments and trailing commas in both sync tools**

- Category: Correctness · Severity: Medium · Confidence: High
- Location: src/project_standards/sync_standards_include.py:54-58, src/project_standards/sync_vscode_colors.py:81-93
- Evidence: `src/project_standards/sync_standards_include.py:57:    clean = re.sub(r"(?m)^\s*//[^\n]*\n?", "", original)`
- Problem: Both tools strip only whole-line // comments before json.loads. VS Code settings.json is JSONC and routinely contains inline comments (`"key": true, // note`), /\*\*/ block comments, and trailing commas — all of which survive the strip and make json.loads raise an uncaught json.JSONDecodeError, so the tool dies with a raw traceback (exit 1) on a perfectly ordinary settings file. Verified: '{\n\t"editor.formatOnSave": true, // keep on\n...}' fails json.loads after the strip.
- Fix: In both files, replace the whole-line-only strip with a small shared JSONC sanitizer: walk the text character-by-character tracking in-string state (double quotes with backslash escapes); outside strings remove `//...` to end of line and `/*...*/` spans, then remove trailing commas before `}`/`]` with re.sub(r',\s\*([}\]])', r'\1', ...). Wrap json.loads in try/except json.JSONDecodeError and exit with a clean 'error: cannot parse {settings_path}: ...' message instead of a traceback. Add tests with an inline comment and a trailing comma to tests/test_sync_vscode_colors.py and tests/test_sync_standards_include.py.
- Verification: uv run pytest tests/test_sync_vscode_colors.py tests/test_sync_standards_include.py; plus a manual run against a settings.json containing '"a": 1, // x' must not traceback.
- Dependencies: none
- Effort: M

**F-020 — Make format-frontmatter --check report files that --write would scaffold**

- Category: Correctness · Severity: Medium · Confidence: High
- Location: src/project_standards/format_frontmatter.py:726-749 (check loop), src/project_standards/frontmatter_authoring.py:101-109 (write path plans with scaffold=True)
- Evidence: `src/project_standards/format_frontmatter.py:738:            text, path=path, scaffold=write, bump_updated=args.bump_updated`
- Problem: In the check-mode loop `write` is always False (the --write branch returned at line 724), so `scaffold=write` is a constant False. The write path (plan_frontmatter_format -> \_plan_entries) always calls format_text with scaffold=True. Consequence: a managed docs/\*.md file with no frontmatter passes `format-frontmatter --check` (exit 0) yet `format-frontmatter --write` mutates it by inserting a scaffold block — the paired pre-commit hooks format-frontmatter-check and format-frontmatter-fix disagree, so a CI check gives a green result that a subsequent write invalidates. Verified: format_text(scaffold=False) returns changed=False and format_text(scaffold=True) returns changed=True on the same input.
- Fix: In format_frontmatter.main's check loop (line 737-739), call format_text with scaffold=True (path is always non-None there). The existing `if changed:` handling then prints 'would reformat: {path}' and exits 1; the scaffold warning line ('scaffolded: ... fill in title/description') will also print — if that message is undesirable in check mode, suppress warnings starting with 'scaffolded:' and print 'would scaffold: {path}' instead. If the asymmetry is intentional, at minimum replace `scaffold=write` with `scaffold=False` plus a comment stating check mode deliberately ignores scaffold-pending files, and add a test pinning that choice.
- Verification: In a temp repo with docs/guide.md containing only '# Guide\n' and an include covering it: `uv run format-frontmatter --check --config <cfg> docs/guide.md` must exit 1 (currently exits 0), then `--write` exits 0 and the file gains a frontmatter block.
- Dependencies: none
- Effort: S

**F-021 — Refuse to reformat frontmatter containing anchors/aliases in block-list items**

- Category: Correctness · Severity: Medium · Confidence: High
- Location: src/project_standards/format_frontmatter.py:110-129 (tokenize guard), src/project_standards/format_frontmatter.py:286-335 (normalize_lists)
- Evidence: `src/project_standards/format_frontmatter.py:110:        if value[:1] in ("&", "*") or value.startswith("<<") or value[:1] in ("|", ">"):`
- Problem: tokenize's unsafe-construct guard only inspects the value on the `key:` line, not block-list item lines. For frontmatter like `tags:\n  - &a 'x'` plus `related:\n  - *a`, normalize_lists re-renders the tags list through yaml.BaseLoader and drops the `&a` anchor, while the aliasing entry is left untouched (its isolated parse fails with an undefined alias, which is silently `continue`d). The result is written by --write/fix as invalid YAML. Verified: format_text on such a document returns changed=True with zero warnings and the output raises FrontmatterParseError('found undefined alias'). A formatter run corrupts a previously-parseable file.
- Fix: In tokenize (format_frontmatter.py), while gathering continuation lines for an entry, check each continuation line: strip leading whitespace, and if it starts with '- ' inspect the text after the dash; if that text (after lstrip) starts with '&' or '*', return ([], f"unsupported YAML construct on key {key!r}") exactly like the existing key-line guard. This makes format_text emit the existing 'skipped (unsupported frontmatter)' warning and leave the file untouched. Add a regression test in tests/test_format_frontmatter.py asserting format_text on a doc with `tags:\n - &a 'x'\nrelated:\n - *a` returns changed=False with a 'skipped (unsupported frontmatter)' warning.
- Verification: uv run python -c "from pathlib import Path; from project_standards.format_frontmatter import format_text; from project_standards.validate_frontmatter import parse_frontmatter; doc='---\nid: \'note-abc123-x\'\ntitle: \'T\'\ndoc_type: \'note\'\ntags:\n - &a \'x\'\nrelated:\n - \*a\n---\nbody\n'; new,changed,w=format_text(doc,path=Path('docs/g.md')); assert not changed and w, (changed,w); parse_frontmatter(new)"
- Dependencies: none
- Effort: S

**F-022 — Stop deleting non-header comments when rewriting settings.json**

- Category: Correctness · Severity: Medium · Confidence: High
- Location: src/project_standards/sync_vscode_colors.py:79-107
- Evidence: `src/project_standards/sync_vscode_colors.py:80:    """Replace folder-color.pathColors in *settings_path*, preserving JSONC comments."""`
- Problem: rewrite_settings preserves only the // comment lines immediately after the opening '{'; every other comment in the user's settings.json (comments above later keys, section dividers) is stripped by the clean pass and never re-inserted, then the whole file is re-serialized with json.dumps — silently destroying user-authored content in a config file the tool does not own, while the docstring claims comments are preserved. Key ordering/indentation of unrelated settings is also rewritten wholesale.
- Fix: Replace the parse-and-dump approach with a targeted textual splice: locate the existing '"folder-color.pathColors"' array in the original text (bracket-matching from the key, honoring strings) and replace only that span with the newly serialized array (json.dumps(path_colors, indent='\t') re-indented to match), leaving every other byte — including all comments — untouched; if the key is absent, insert it before the final '}'. Alternatively, if wholesale rewrite is accepted behavior, change the docstring to say only header comments survive and print a warning when non-header comments are detected and dropped.
- Verification: Add a test in tests/test_sync_vscode_colors.py: settings.json with a '// mid-file comment' above another key must retain that comment after rewrite_settings; run uv run pytest tests/test_sync_vscode_colors.py.
- Dependencies: none
- Effort: M

**F-023 — Catch referencing/Unresolvable errors in option-schema default and options validation**

- Category: Correctness · Severity: Medium · Confidence: High
- Location: src/project_standards/package_contract/payload.py:1036-1045, src/project_standards/package_contract/payload.py:1110-1122
- Evidence: `src/project_standards/package_contract/payload.py:1041:            validator = cast("_SchemaValidator", Draft202012Validator(child))`
- Problem: \_validate_declared_defaults builds a Draft202012Validator rooted at the child property schema, so any property using '$ref': '#/$defs/...' with a 'default' raises jsonschema.exceptions.\_WrappedReferencingError (subclass of referencing.exceptions.Unresolvable, NOT a ValueError/PackageContractError) because '#' resolves against the child, not the document root. Empirically confirmed: PointerToNowhere escapes uncaught. \_validate_default_contract FORCES every optional property to carry a default, so the first author to use $ref on an optional property gets an unhandled traceback from `project-standards standards validate-packages` instead of a finding/exit-2 — violating the CLI exit-code contract. resolve_options (line 1114) has the same hole for schemas with unresolvable/external $refs that pass check_schema.
- Fix: In payload.py, wrap the two iter_errors call sites in try/except catching referencing.exceptions.Unresolvable (import referencing.exceptions): in_validate_declared_defaults raise PackageContractError('option schema default cannot be validated against a $ref property') from exc; in PackageOptionSchema.resolve_options raise PackageContractError('package options schema contains an unresolvable reference') from exc. Additionally, in \_validate_declared_defaults validate the default with a validator rooted at the full document (e.g. Draft202012Validator({\*\*child}, registry seeded with the document) or validate via the document root) so legitimate $ref defaults pass instead of erroring.
- Verification: uv run python -c "from pathlib import Path; import json, tempfile; ..." — simplest: add a pytest in tests/package_contract/test_payload.py that writes an option schema with $defs plus a property {'$ref': '#/$defs/x', 'default': 'a'} and asserts load_option_schema raises PackageContractError (not referencing.exceptions.Unresolvable); run uv run pytest tests/package_contract/test_payload.py
- Dependencies: none
- Effort: S

**F-024 — Make agent-handoff settings.json inspection JSONC-tolerant to match the declared jsonc adapter (new payload version)**

- Category: Correctness · Severity: Medium · Confidence: High
- Location: src/project_standards/payloads/agent-handoff/1.1/providers/agent_handoff.py:713-728 (used by validate/verify/drift-check via \_integration_findings)
- Evidence: `src/project_standards/payloads/agent-handoff/1.1/providers/agent_handoff.py:719:            parsed = _table(cast(object, json.loads(content)), name="Claude settings")`
- Problem: The `.claude/settings.json` contribution is declared with `adapter = "jsonc"` (payload.toml:354), and the control-plane jsonc adapter explicitly tolerates and preserves JSONC comments and trailing commas (control_plane/adapters/jsonc.py docstring and lexer). But `_session_group_state` parses the snapshot with strict `json.loads`, so any comment or trailing comma anywhere in a consumer's settings.json makes parsing fail, `valid` becomes False, and validate/verify/drift-check emit a false AH-CLAUDE-CONFIG-INVALID ('selected Agent Handoff integration is missing or malformed') even though reconcile just applied and accepted that same file. Reconcile-then-validate thus disagrees on the same bytes, which contradicts the transactional control-plane contract.
- Fix: In the new agent-handoff 1.2 payload's providers/agent_handoff.py, before json.loads in `_session_group_state` (kind == "claude"), neutralize JSONC the same way the control-plane adapter does: strip // and /\*\*/ comments outside strings and remove trailing commas (a small local lexer mirroring adapters/jsonc.py semantics — payload code must stay self-contained, do not import the private adapter). Keep the existing fallback `(marker in content, False)` for genuinely unparseable bytes. Update the provider-code digest in 1.2 payload.toml.
- Verification: Unit test: a settings.json snapshot containing `// comment` above a correct managed SessionStart group returns (True, True) from \_session_group_state and produces no AH-CLAUDE-CONFIG-INVALID finding from run_verify.
- Dependencies: Batch into the single agent-handoff 1.2 payload cut together with F-006, F-007, F-010, F-027. Ship in the same agent-handoff 1.2 payload as the other agent-handoff fixes.
- Effort: M

**F-025 — Re-export shared validator symbols publicly instead of importing private underscore APIs into immutable payload code**

- Category: Architecture · Severity: Medium · Confidence: High
- Location: src/project_standards/payloads/markdown-frontmatter/1.2/providers/frontmatter.py:28-34
- Evidence: `src/project_standards/payloads/markdown-frontmatter/1.2/providers/frontmatter.py:29:    _ADR_ID_RE,  # pyright: ignore[reportPrivateUsage]  # shared public-validator grammar`
- Problem: Release-immutable payload provider code imports private underscore symbols (`_ADR_ID_RE` from validate_id, `_ref_values` from validate_references, line 33) from the mutable runtime. Multiple immutable payload versions coexist inside newer wheels (standard-bundle-authoring ships 2.0 and 2.1 side by side), so a future runtime refactor that renames either private symbol — legitimate for a private API — breaks the released markdown-frontmatter 1.2 bytes at import time in a PATCH/MINOR wheel, violating the stated versioning contract that PATCH/MINOR must keep a previously-passing consumer passing. The pyright-ignore comments acknowledge the coupling but nothing enforces the symbols' stability.
- Fix: In the runtime (mutable, not payload bytes): add public aliases `ADR_ID_RE = _ADR_ID_RE` in src/project_standards/validate_id.py and `reference_values = _ref_values` in src/project_standards/validate_references.py, documented as payload-facing stable API, and add a test asserting both names exist (freezing the contract for already-released payloads that use the underscore names too — keep the underscore names as permanent aliases). Then, in the next markdown-frontmatter payload version, switch the imports to the public names and drop the pyright ignores.
- Verification: A new test in tests/ imports project_standards.validate_id.ADR_ID_RE and project_standards.validate_references.reference_values and asserts they are the same objects as the underscore names; `uv run basedpyright` clean without reportPrivateUsage suppressions in the new payload version.
- Dependencies: none
- Effort: S

**F-026 — Derive upgrade/new lock mode from real argparse parsing, not argv string scan**

- Category: Correctness · Severity: Medium · Confidence: High
- Location: src/project_standards/specs/cli.py:1213-1225, src/project_standards/specs/cli.py:419-421, src/project_standards/specs/cli.py:730, src/project_standards/specs/cli.py:1029
- Evidence:

```text
src/project_standards/specs/cli.py:1219:            argument in {"--in-place", "-i", "--output", "-o"}
src/project_standards/specs/cli.py:1220:            or argument.startswith("--output=")
src/project_standards/specs/cli.py:1221:            or (argument.startswith("-o") and len(argument) > 2)
```

- Problem: \_operation_lock_mode string-scans argv but argparse accepts spellings the scan misses: verified that `--in-pl`, `-io out.md`, and `--outp o.md` all parse as write operations (allow_abbrev defaults True; short options cluster) while the heuristic returns writes=False — so an in-place/output upgrade runs its file mutation under LockMode.READ, defeating the control-plane exclusivity the mode selection exists for. The same argv-scan pattern at lines 730/1029 (`json_mode = "--json" in argv`) misses `--js`, so abbreviated --json invocations emit plain-stderr errors instead of the I7 JSON envelope.
- Fix: In cli.py: (1) make \_NewArgParser pass allow_abbrev=False to super().**init** so long-option abbreviations are rejected for new/upgrade; (2) extract the upgrade parser construction from \_run_upgrade into a module-level `_upgrade_parser() -> _NewArgParser` and reuse it in both \_run_upgrade and \_operation_lock_mode: in_operation_lock_mode's upgrade branch, call `_upgrade_parser().parse_known_args(argv)` inside try/except (\_ArgparseError, SystemExit) and return LockMode.WRITE if parsing failed (fail-safe) or if ns.in_place or ns.output is not None, else READ. Do the same for the `new` branch using a `_new_parser()` helper (READ only when ns.stdout is True). Keep json_mode = "--json" in argv, which becomes exact once abbreviations are disabled; clustered `-io` is handled by the parse-based mode selection.
- Verification: uv run python -c "from project_standards.specs.cli import_operation_lock_mode; from project_standards.control_plane.locking import LockMode; assert \_operation_lock_mode('upgrade', ['s','--to','full','-io','out.md']) is LockMode.WRITE" and uv run pytest tests/test_spec_upgrade_cli.py tests/test_spec_new_cli.py
- Dependencies: none
- Effort: M

**F-027 — Make agent-handoff shape checks fence-aware in a new payload version**

- Category: Correctness · Severity: Medium · Confidence: High
- Location: standards/agent-handoff/versions/1.1/providers/agent_handoff.py:303-304, 374-380 (also_sections at 294-300 and \_table_lines at 307-317)
- Evidence:

```text
standards/agent-handoff/versions/1.1/providers/agent_handoff.py:377:        for line in text.splitlines()
standards/agent-handoff/versions/1.1/providers/agent_handoff.py:378:        if (match := re.match(r"^(#{1,6})\s+", line)) is not None
```

- Problem: \_shape_messages runs its heading-depth, bullet-count, bullet-length, table-row, and section-splitting scans over every physical line, ignoring code fences; only \_paragraphs (lines 320-337) tracks fence state. Reproduced at this commit: a docs/handoff/state.md containing a fenced bash block with the comment line '#### fenced comment heading' yields the message 'heading depth exceeds 3'. Under the live-state profile (severity = fatal) and contract_version 1.1, run_validate emits this as a severity=error finding, so a consumer whose terse state.md or TODO.md legitimately contains a code fence with '#'-comments or '- ' lines fails validation. Fenced '## ' lines similarly create phantom sections that trip allowed_sections/max_bullets_per_section. (This repo dogfoods contract 1.0, which downgrades AH-SHAPE to warning, so the repo itself only sees warnings.)
- Fix: The 1.1 payload bytes are immutable, so fix in a new agent-handoff payload version (versions/1.2): in \_shape_messages and its helpers (\_sections,\_bullets, \_table_lines, the heading-depth scan at lines 374-380, and the row/headline loop at 437-447), first strip fenced regions using the same fence-tracking logic \_reference_text already implements (lines 605-629), i.e., compute a fence-masked line list once and run all line-level scans over it. Wire the new version through standard.toml, catalogs/5.toml (additive default entry per MINOR rules), .standards/catalog.toml, and the payload projection.
- Verification: In the new payload, run: uv run python3 -c "exec snippet loading the 1.2 provider and calling \_shape_messages on a state.md containing a fenced block with '#### x' and three '- ...' lines under the live-state profile" and confirm no 'heading depth exceeds 3' or bullet messages; then uv run project-standards standards validate-packages --root . and the full gate.
- Dependencies: Batch into the single agent-handoff 1.2 payload cut together with F-006, F-007, F-010, F-024.
- Effort: L

**F-028 — Update stale layer-model claims and layout tree in tests/README.md**

- Category: Docs · Severity: Medium · Confidence: High
- Location: tests/README.md:31-123
- Evidence:

```text
tests/README.md:87: `test_adopt_packaging.py` builds the wheel with `uv build` and inspects the zip to confirm that `bundles/` and all `adopt.toml` manifests are present. This is the only test that shells out — it is **slow** (several seconds).
```

- Problem: The document contributors are told to read before touching the suite is stale on several load-bearing claims: (a) line 87 says test_adopt_packaging.py 'is the only test that shells out', but ~39 test modules import subprocess (wheel builds in package_compatibility/conftest.py, test_installed_wrappers.py, control_plane/test_end_to_end.py, lock-holder subprocesses in test_locking.py, git in 6 modules, Prettier/markdownlint in coherence); (b) line 31 claims 'No network... A full run (excluding packaging) is sub-second', but test_installed_wrappers.py pip-installs the wheel's dependencies (pydantic/jsonschema/pyyaml) from the network and the full run is minutes, not sub-second; (c) the layout tree (lines 101-123) lists ~15 top-level files plus a tests/conftest.py that does not exist, and omits all five subdirectory suites (agent_handoff/, control_plane/, package_contract/, package_compatibility/, coherence/) that hold most of the 151 test files; (d) lines 135/188 tell contributors to graduate shared helpers to conftest.py, while actual practice is importable helper modules (wheel_helpers.py, control_plane/helpers.py, package_contract/helpers.py, planner_helpers.py). New contributors following this doc will mis-place tests and helpers.
- Fix: Edit tests/README.md: (1) in the Goals table row 'Fast & hermetic', replace 'A full run (excluding packaging) is sub-second' with an accurate statement (ordinary suite runs in minutes; packaging/wheel/compatibility tests shell out and test_installed_wrappers needs network for dependency install); (2) in section 5, replace 'This is the only test that shells out' with a list of the shelling suites (adopt packaging, installed wrappers, package_compatibility wheel fixture, control_plane end-to-end, locking subprocesses, coherence Node tools, git-based release-baseline tests); (3) extend the layout tree with the five subdirectories and drop the nonexistent tests/conftest.py entry (or note conftest.py exists only in package_compatibility/); (4) update the fixtures section to name the shared helper modules (tests/wheel_helpers.py, tests/control_plane/helpers.py + planner_helpers.py, tests/package_contract/helpers.py, tests/standards_graph_helpers.py) as the graduation target instead of conftest.py.
- Verification: Re-read tests/README.md; confirm `grep -c subprocess tests/*.py tests/*/*.py` matches the doc's claim; run tests/coherence + one packaging test to sanity-check the described commands still work.
- Dependencies: none
- Effort: M

**F-029 — Accept --view in any argument position on the v2 validate path**

- Category: Convention · Severity: Low · Confidence: High
- Location: src/project_standards/agent_handoff/cli.py:369-375
- Evidence: `src/project_standards/agent_handoff/cli.py:371:    if operation is V2ProviderOperation.VALIDATE and filtered[:2] == ["--view", "size"]:`
- Problem: \_run_selected only recognizes --view when it is the first two tokens of argv. The internal size-report/shape-check prefixes always satisfy this, but a user invoking `agent-handoff validate --repo X --view size` (accepted by the legacy provider parser, providers.py:78, where --view is a documented position-independent argparse option) gets \_ArgumentError and exit 2 on the v2 path. Also `--view=size` is rejected. Same command, different generation, different behavior.
- Fix: In cli.py \_parse_v2, add `parser.add_argument("--view", choices=("full", "size", "shape"), default="full")` when operation is VALIDATE, delete the filtered[:2] special-casing in \_run_selected (lines 369-374), and derive `view` from the parsed namespace; keep the \_COMMANDS prefixes unchanged since they now parse identically.
- Verification: uv run pytest tests/agent_handoff/test_selected_routing.py; manually: uv run project-standards agent-handoff validate --repo <consumer> --view size exits 0/1, not 2
- Dependencies: none
- Effort: S

**F-030 — Extract shared Markdown link-target parsing helper**

- Category: Structure · Severity: Low · Confidence: High
- Location: src/project_standards/agent_handoff/cli.py:84,177-185; src/project_standards/agent_handoff/validation.py:43,468-476
- Evidence:

```text
src/project_standards/agent_handoff/cli.py:84:_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
src/project_standards/agent_handoff/validation.py:43:_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
```

- Problem: The link regex and the multi-step target normalization chain (strip, strip('<>'), split, fragment removal, unquote, scheme/mailto filtering) are duplicated byte-for-byte between cli.py \_read_snapshots and validation.py \_references. The copies have already drifted: validation strips code fences and inline code via_reference_text before matching, while the cli copy scans raw text (collecting spurious snapshot candidates from fenced code), and any fix to the shared parsing bug must be applied twice.
- Fix: Create src/project_standards/agent_handoff/integrations/links.py (or a module-level helper in validation.py imported by cli.py) exposing `iter_local_link_targets(text: str) -> Iterator[str]` containing the regex plus normalization and the empty/scheme/mailto filtering; replace both inline copies with calls to it. Keep validation's \_reference_text pre-processing at its call site.
- Verification: uv run pytest tests/agent_handoff/ and uv run basedpyright src/project_standards/agent_handoff/
- Dependencies: Apply after the empty-link-target IndexError fix so the guard lands once in the shared helper.
- Effort: S

**F-031 — Include the broken link target in AH-REFERENCE-MISSING findings**

- Category: Docs · Severity: Low · Confidence: High
- Location: src/project_standards/agent_handoff/validation.py:478-485
- Evidence: `src/project_standards/agent_handoff/validation.py:482:                    "local Markdown link target is missing or outside the repository",`
- Problem: Every broken link in a file produces a Finding with identical code, path, locus ("Markdown link"), and message — the offending target is never reported. A document with three broken links yields three byte-identical findings, giving the user no way to locate any of them, and the JSON report cannot distinguish them either.
- Fix: In validation.py \_references, pass the target into the finding, e.g. `locus=f"Markdown link: {target}"` (keep the message constant so sorting stays stable). Update any test in tests/agent_handoff/test_validation.py or test_selected_routing.py that asserts the old locus string.
- Verification: uv run pytest tests/agent_handoff/test_validation.py tests/agent_handoff/test_selected_routing.py
- Dependencies: none
- Effort: S

**F-032 — Preserve destination file mode in RepositoryRoot.write_bytes**

- Category: Correctness · Severity: Low · Confidence: High
- Location: src/project_standards/agent_handoff/paths.py:147-179
- Evidence:

```text
src/project_standards/agent_handoff/paths.py:158:                            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                            0o666,
```

- Problem: write_bytes stages into a temp file created with mode 0o666 (masked by umask) and os.replace()s it over the destination, so any pre-existing permissions on managed rewrites — e.g. a consumer who chmod 600'd .claude/settings.json, or non-default modes on CLAUDE.md/AGENTS.md/.codex/config.toml — are silently reset to the umask default on every adopt/upgrade that touches the file. The existing-file stat at lines 147-151 is only used for the symlink check; its st_mode is discarded.
- Fix: In paths.py write_bytes, when `metadata` (the pre-write os.stat of the existing leaf) is not None, call `os.fchmod(descriptor, stat_module.S_IMODE(metadata.st_mode))` on the staged temp descriptor before os.replace, so updates keep the consumer's mode while new files keep the current default.
- Verification: uv run pytest tests/agent_handoff/test_paths.py; add a test: chmod 0o600 an existing target, write_bytes, assert stat mode is still 0o600
- Dependencies: none
- Effort: S

**F-033 — Replace bare next() with a guarded lookup in \_upgrade_plan**

- Category: Correctness · Severity: Low · Confidence: Medium
- Location: src/project_standards/agent_handoff/cli.py:301-303
- Evidence: `resource = next(\n            item for item in selected.payload.manifest.resources if item.id == resource_id\n        )  — resource_id is from the hardcoded _UPGRADE_RESOURCES dict (lines 78-82); selected.payload resolves from InstalledDistribution.current(), i.e. the same wheel, whose only agent-handoff payload (payloads/agent-handoff/1.1/payload.toml) declares hook, skill, and skill-openai. The lock (selected.lock) only gates loop entry and never supplies the lookup key.`
- Problem: If a lock artifact matches a \_UPGRADE_RESOURCES target but the selected payload manifest has no resource with that id (possible with a stale lock written by a different payload generation), next() raises StopIteration. StopIteration is not a RuntimeError here (it is raised in plain code, not inside a generator frame), so run()'s except (CommandResolutionError, OSError, RuntimeError) does not catch it and the CLI dies with a traceback instead of the exit-3 error message. (Verifier adjustment: The unguarded next() and the StopIteration-escapes-exit-3-mapping mechanism are both real, but the claimed trigger is wrong: resource_id comes from the hardcoded_UPGRADE_RESOURCES map and the payload manifest ships in the same wheel (the sole packaged payload 1.1 declares all three ids), so a stale lock alone cannot cause it — only a future multi-version wheel with a repo pin to a manifest lacking an id makes it reachable. Worth fixing as defensive hardening; the proposed fix matches existing error style.)
- Fix: Change to `resource = next((item for item in selected.payload.manifest.resources if item.id == resource_id), None)` and `if resource is None: raise CommandResolutionError(f"selected Agent Handoff payload is missing resource {resource_id!r}")`, which run() already maps to exit 3.
- Verification: uv run pytest tests/agent_handoff/test_cli.py; add a unit test with a lock referencing a target whose resource id is absent from the payload manifest and assert exit code 3 with an error message
- Dependencies: none
- Effort: S

**F-034 — Add an explicit `permissions: contents: read` block to validate-standards.yml**

- Category: Security · Severity: Low · Confidence: High
- Location: .github/workflows/validate-standards.yml:1-10
- Evidence:

```text
.github/workflows/validate-standards.yml:1:jobs:
  frontmatter:
    name: Frontmatter
    uses: ./.github/workflows/validate-markdown-frontmatter.yml
```

- Problem: validate-standards.yml is the only workflow of the eight without a `permissions:` block, so its GITHUB_TOKEN gets the repository default (potentially write-all depending on repo settings). The called workflow's own `contents: read` downgrades what its jobs see, so the practical exposure is limited, but the repo's otherwise-uniform least-privilege convention (all 7 other workflows declare `permissions: contents: read`) is broken, and any future job added to this caller inherits the default token. The file's key order (jobs before name/on) also suggests it was machine-generated and never normalized.
- Fix: Add a top-level block to .github/workflows/validate-standards.yml: permissions: contents: read Optionally reorder keys to name/on/permissions/jobs to match the other workflows.
- Verification: grep -A1 '^permissions:' .github/workflows/validate-standards.yml shows 'contents: read'; workflow still passes on the next PR run.
- Dependencies: none
- Effort: S

**F-035 — Add the `testing` branch to push triggers of the gate workflows (or document the asymmetry)**

- Category: Testing · Severity: Low · Confidence: High
- Location: .github/workflows/check.yml:6; .github/workflows/coherence.yml:9; .github/workflows/validate-standards.yml:8-10; .github/workflows/validate-specs.yml:4-5; vs .github/workflows/validate-standards-graph.yml:6
- Evidence: `.github/workflows/check.yml:6:    branches: ["main"]`
- Problem: Development happens by direct commits to the `testing` branch (no PRs, per the repo's single-developer convention; `testing` is the current branch). validate-standards-graph.yml triggers on `push: branches: ["main", "testing"]`, but check.yml, coherence.yml, validate-standards.yml, validate-specs.yml, format.yml, and lint-markdown.yml only trigger on PRs and pushes to main. Result: the full Python gate (ruff/basedpyright/pytest/coverage/pip-audit), the frontmatter validation, and the spec gates never run in CI on the development branch — only the standards-graph gate does. A regression committed to testing is first caught in CI at merge to main. The inconsistency (graph workflow includes testing, the others do not) suggests drift rather than a deliberate cost decision.
- Fix: Change the push trigger in .github/workflows/check.yml line 6 (and, matching, coherence.yml line 9, validate-standards.yml lines 8-10, validate-specs.yml lines 4-5) from `branches: ["main"]` to `branches: ["main", "testing"]`, mirroring validate-standards-graph.yml. If the omission is intentional (local gate suffices, CI cost), instead add a one-line comment above each push trigger stating that testing-branch pushes are intentionally excluded.
- Verification: Push a trivial commit to testing and confirm the Check workflow appears in the Actions run list for that push.
- Dependencies: none
- Effort: S

**F-036 — Make the bundled jsonschema stub fail loudly instead of silently passing**

- Category: Correctness · Severity: Low · Confidence: High
- Location: scripts/build-validate-id-pyz.sh:80-90
- Evidence: `scripts/build-validate-id-pyz.sh:86:    def iter_errors(self, instance: object): return iter([])`
- Problem: The jsonschema stub baked into validate-id.pyz returns an empty error iterator from `Draft202012Validator.iter_errors` and no-ops `check_schema`. Today validate_id never calls these, but the stub is importable by everything in the bundled package: if a future refactor routes any validate_id code path through validate_frontmatter's schema validation (or a user pokes at the bundled modules), every document silently validates as conformant instead of failing — a validator that lies is worse than one that crashes.
- Fix: In the heredoc at scripts/build-validate-id-pyz.sh lines 80-90, change the stub methods to raise instead of no-op: `iter_errors` and `check_schema` should `raise NotImplementedError("jsonschema is stubbed out in validate-id.pyz; schema validation is unavailable")` (keep `__init__` accepting the schema so the module-level import continues to work only if no validator is instantiated at import time — if validate_frontmatter instantiates at import, raise from iter_errors/check_schema only).
- Verification: Rebuild with `bash scripts/build-validate-id-pyz.sh`; `python3 dist/validate-id.pyz --help` and a normal `--config` run still work; a Python snippet importing the bundled jsonschema and calling iter_errors raises NotImplementedError.
- Dependencies: none
- Effort: S

**F-037 — Pass the V2 baseline ref via env instead of inline `${{ }}` interpolation in run**

- Category: Security · Severity: Low · Confidence: High
- Location: .github/workflows/validate-standards-graph.yml:74-76
- Evidence: `.github/workflows/validate-standards-graph.yml:76:        run: uv run project-standards packages check-release --root . --baseline "${{ steps.v2-baseline.outputs.ref }}"`
- Problem: A step output (derived from git tag names matching `v[0-9]*`) is interpolated directly into a `run:` script. GitHub expands `${{ }}` before the shell sees the script, so a tag name containing shell metacharacters (e.g. `v1;curl ...` — `v[0-9]*` matches any suffix after the first digit) would be executed. Tags are maintainer-created here, so exploitability is low, but this is exactly the script-injection pattern GitHub's hardening guide says to avoid, and the repo's other workflows (format.yml, validate-markdown-frontmatter.yml, validate-specs.yml) consistently route dynamic values through `env:`.
- Fix: Change the 'Check released V2 payloads' step in .github/workflows/validate-standards-graph.yml to: env: BASELINE_REF: ${{ steps.v2-baseline.outputs.ref }}
        run: uv run project-standards packages check-release --root . --baseline "$BASELINE_REF"
- Verification: Next push to main/testing with released-payload changes runs the step successfully with the env-provided ref (visible in the step log).
- Dependencies: none
- Effort: S

**F-038 — Prefer the script's own repo source over the ~/projects checkout in build-validate-id-pyz.sh**

- Category: Correctness · Severity: Low · Confidence: High
- Location: scripts/build-validate-id-pyz.sh:34-47
- Evidence:

```text
scripts/build-validate-id-pyz.sh:39:elif [[ -d "$HOME/projects/project-standards/src/project_standards" ]]; then
    PS_PKG="$HOME/projects/project-standards/src/project_standards"
```

- Problem: The source-resolution order is argument > env var > `$HOME/projects/project-standards` > the script's own sibling `src/project_standards`. When the script is run from any checkout other than ~/projects/project-standards (a second clone, a worktree, CI), it silently bundles the workstation checkout's source instead of the repo it lives in — the built .pyz can contain code from a different branch/commit than the invoker intended, and the header's 'source-of-truth copy, no drift possible' claim is violated. The header documents the default but the surprising part is that the local sibling directory loses to a hardcoded home path.
- Fix: In scripts/build-validate-id-pyz.sh, swap the two elif branches so `$SCRIPT_DIR/../src/project_standards` (lines 41-42) is checked before `$HOME/projects/project-standards/src/project_standards` (lines 39-40), and update the header comment on line 22 to 'Default source: this repo's src/project_standards (falls back to ~/projects/project-standards)'.
- Verification: From a second checkout at a different commit, run `bash scripts/build-validate-id-pyz.sh` with no args and confirm the '→ source:' line prints that checkout's own src path.
- Dependencies: none
- Effort: S

**F-039 — Remove the redundant coherence.yml workflow (check.yml already runs tests/coherence)**

- Category: Structure · Severity: Low · Confidence: High
- Location: .github/workflows/coherence.yml:1-33; .github/workflows/check.yml:20-26,60-61; tests/test_action_runtime_versions.py:19,28,87-99; tests/README.md:198
- Evidence:

```text
coherence.yml:33 `run: uv run pytest tests/coherence -v` (verbatim); check.yml:26 `run: npm ci`; tests/test_action_runtime_versions.py:19/28 list ".github/workflows/coherence.yml" and lines 87-99 assert its setup-node step — deletion without updating these fails the suite.
```

- Problem: check.yml and coherence.yml trigger on identical events (pull_request, push to main). check.yml runs `npm ci` (lines 25-26) precisely so its ordinary pytest phase (`-m "not performance and not compatibility"`, testpaths=["tests"]) includes tests/coherence — the coherence tests only skip when node_modules/.bin/prettier is absent (tests/coherence/test_behavioral.py:17-18), which never happens after npm ci. So every PR runs the coherence suite twice, paying a second full checkout + Node + uv + `uv sync --locked --all-groups` job for tests already executed and already counted in check.yml's coverage phase. If the separate named status check is deliberately wanted, that intent is not recorded in the workflow comment (which only explains why Node is needed). (Verifier adjustment: The duplication is real and even deliberate-looking (commit 4d81602 added npm ci to check.yml so the ordinary phase runs tests/coherence, defeating the only skipif guard), but the fix's "dependencies: none" is wrong: deleting coherence.yml breaks tests/test_action_runtime_versions.py (lines 19, 28, 87-99 hardcode and assert that workflow) and leaves tests/README.md:198 stale, so those must be updated in the same change.)
- Fix: Delete .github/workflows/coherence.yml (its tests remain covered by check.yml's ordinary phase after npm ci). Alternatively, if a distinct 'Coherence' status check is intentionally required, add one sentence to the header comment in coherence.yml stating that it intentionally duplicates check.yml's run to provide a separately-named required check.
- Verification: After deletion, a PR run of check.yml shows tests/coherence tests executed (not skipped) in the 'Ordinary tests with coverage' step log.
- Dependencies: none
- Effort: S

**F-040 — Close the exists-then-replace race for non-force managed adopt writes**

- Category: Security · Severity: Low · Confidence: High
- Location: src/project_standards/adopt/engine.py:330-347
- Evidence: `src/project_standards/adopt/engine.py:330:        exists = abs_dest.exists()`
- Problem: For a MANAGED action where the preflight `exists` snapshot is False and --force is not given, execute_plan proceeds to_atomic_write with replace=True (os.replace), which clobbers any file created between the exists() check and publication. The Action.precondition_sha256/require_absent machinery that guards exactly this window is only populated by agent_handoff/planning.py; build_plan (the plain `project-standards adopt` path) leaves both at their defaults, making the line-341_check_precondition call a no-op there. The overwrite-protection contract ("skipped unless --force") is therefore only preflight-deep for legacy adopt; the same TOCTOU applies to the symlinked-ancestor check at line 325 (a parent swapped to a symlink after the check lets mkdir/replace write outside --dest). Local CLI, narrow window — low practical risk, but the engine is documented as path-safety-critical and already owns the atomic non-clobber primitive.
- Fix: In execute_plan in src/project_standards/adopt/engine.py, when `not exists and not force and action.install_policy is InstallPolicy.MANAGED and action.precondition_sha256 is None`, call \_atomic_write with replace=False (the existing hard-link publish that returns False on FileExistsError) and append to report.skipped on False — matching the create-only race semantics — instead of os.replace. Keep replace=True for force and precondition-carrying actions.
- Verification: uv run pytest tests/test_adopt_safety.py tests/test_adopt_engine.py passes; a new test that creates the destination file inside a monkeypatched render_action hook observes 'skipped', not an overwrite.
- Dependencies: none
- Effort: M

**F-041 — Do not silently fall back to legacy V1 adopt when reading the installed distribution fails with OSError**

- Category: Correctness · Severity: Low · Confidence: Low
- Location: src/project_standards/cli.py:234-238
- Evidence:

```text
src/project_standards/cli.py:237:    except PackageContractError, OSError, ValueError:
238:        return None
```

- Problem: \_try_v5_adopt treats PackageContractError (no/invalid V2 distribution — a legitimate legacy-fallback signal) identically to OSError (transient I/O failure reading an installed, possibly healthy distribution): both return None, and_cmd_adopt then materializes legacy V1 artifacts into the destination with no warning. On a repo whose catalog would have routed through the V5 control plane, a transient read failure silently produces the wrong artifact set instead of an error, and later checks at lines 246-247 show the code already knows how to report a broken installation as exit 2 — the inconsistency is only in this first probe.
- Fix: In \_try_v5_adopt in src/project_standards/cli.py, split the handler: keep `except (PackageContractError, ValueError): return None` for the not-a-V2-install case, but for OSError print `error: installed V2 distribution could not be read: {exc}` to stderr and return 2. Add a test monkeypatching InstalledDistribution.current to raise OSError and asserting adopt exits 2 without writing files.
- Verification: uv run pytest tests/test_adopt_cli.py passes including the new OSError-probe test.
- Dependencies: none
- Effort: S

**F-042 — Include artifact kind in build_plan destination-collision check**

- Category: Correctness · Severity: Low · Confidence: High
- Location: src/project_standards/adopt/engine.py:102-127
- Evidence: `src/project_standards/adopt/engine.py:104:                if str(existing.source_path) != str(src):`
- Problem: The dedupe path compares source_path, mode, and install_policy but never `kind`. Two artifacts with the same dest and same source but different kinds (file vs workflow-caller) merge into one Action that keeps `existing.kind` — whichever standard was listed first. Since workflow-caller substitutes {{ref}} and file does not, the rendered bytes for the shared dest become order-dependent, silently, instead of raising the UsageError this collision check exists to produce for authoring bugs.
- Fix: In build_plan in src/project_standards/adopt/engine.py, inside the `existing is not None` branch, add a check mirroring the mode check: `if existing.kind != art.kind: raise UsageError(f"destination collision at {art.dest!r}: {existing.standards[0]} and {sid} use different kinds")`. Add a test in tests/test_adopt_engine.py with two synthetic manifests sharing a dest+source but differing kinds, asserting UsageError.
- Verification: uv run pytest tests/test_adopt_engine.py passes including the new different-kinds collision test.
- Dependencies: none
- Effort: S

**F-043 — Make \_require_str_list reject non-string registry entries instead of coercing**

- Category: Correctness · Severity: Low · Confidence: High
- Location: src/project_standards/registry.py:119-122
- Evidence: `src/project_standards/registry.py:122:    return [str(v) for v in cast("list[Any]", obj)]`
- Problem: \_require_str_map raises RegistryError on a non-string value, but_require_str_list silently coerces any element with str(). A registry.json authoring slip like `"versions": [1.0]` loads as ["1.0"] instead of failing crisply, contradicting the module's own stated goal ("Fail crisply here") and the strict validation applied to the maps; the same silent coercion is repeated for adr supports lists at line 193.
- Fix: In src/project_standards/registry.py change_require_str_list to iterate and `raise RegistryError(f"registry {where}[{i}] is not a string")` for any element failing isinstance(v, str), returning the list unchanged; apply the same strictness to the supports_frontmatter list handling at line 193. Add a loader test with a numeric list element asserting RegistryError.
- Verification: uv run pytest tests/ -k registry passes including the new non-string-list-element test.
- Dependencies: none
- Effort: S

**F-044 — Reject boolean TOML values in adopt.toml artifact mode parsing**

- Category: Correctness · Severity: Low · Confidence: High
- Location: src/project_standards/adopt/manifest.py:90
- Evidence: `src/project_standards/adopt/manifest.py:90:    if isinstance(raw_mode, int) and 0 <= raw_mode <= 0o777:`
- Problem: bool is a subclass of int, so a manifest authoring typo `mode = true` parses successfully: verified `_parse_mode(tomllib.loads('mode = true')["mode"], ...)` returns True, which formats as mode 0001 and would chmod an installed artifact to 0o001 instead of failing manifest validation. Every other malformed mode shape (bad octal string, out-of-range int) raises ManifestError; booleans silently slip through the strict validation this loader otherwise enforces.
- Fix: In \_parse_mode in src/project_standards/adopt/manifest.py, add `if isinstance(raw_mode, bool):` raising the existing ManifestError ("must be an octal string or TOML integer...") before the `isinstance(raw_mode, int)` check. Add a test in tests/test_adopt_manifest.py asserting `mode = true` raises ManifestError.
- Verification: uv run pytest tests/test_adopt_manifest.py passes with the new boolean-mode rejection test.
- Dependencies: none
- Effort: S

**F-045 — Remove the hardcoded agent_handoff fallback from registry loading**

- Category: Convention · Severity: Low · Confidence: High
- Location: src/project_standards/registry.py:141 (also 54-55, 70-72)
- Evidence: `src/project_standards/registry.py:141:    ah = data.get("agent_handoff", {"default": "1.0", "versions": ["1.0"]})`
- Problem: All six other version-tracked standards fail with RegistryError when their registry.json section is missing, but a missing agent_handoff section is silently replaced by a fabricated {default: "1.0", versions: ["1.0"]} (duplicated as constructor defaults at lines 54-55/70-72). registry.json already contains the real section, so the fallback is dead tolerance code that (a) hardcodes a contract version the project convention says must be derived from data, and (b) defeats cli.py's_assert_registry_bundle_parity drift guard — a registry.json accidentally stripped of agent_handoff would still pass the version-tracked parity check with invented data instead of exiting 2.
- Fix: In src/project_standards/registry.py: change line 141 to `ah = data.get("agent_handoff")` so the existing isinstance-dict check raises RegistryError when absent; remove the `= "1.0"` / `= None`-with-["1.0"]-fallback defaults from Registry.**init** (make agent_handoff_default and agent_handoff_versions required like the other standards). Update any test constructing Registry without those kwargs.
- Verification: uv run pytest tests/ -k registry passes; deleting the agent_handoff key from a temp registry.json and calling load_registry raises RegistryError.
- Dependencies: none
- Effort: S

**F-046 — Suppress misleading SG-ARTIFACT-MANIFEST-MISSING when ESCAPE or MISMATCH already fired**

- Category: Correctness · Severity: Low · Confidence: High
- Location: src/project_standards/standards_graph/validators.py:140-171
- Evidence: `src/project_standards/standards_graph/validators.py:160:        if declared and node.artifact_manifest is None:`
- Problem: Discovery leaves node.artifact_manifest as None for three distinct reasons: the linked path escapes the repo, its parent mismatches the expected bundle dir, or the file is absent.\_validate_artifact_manifests emits SG-ARTIFACT-MANIFEST-ESCAPE or SG-ARTIFACT-MANIFEST-MISMATCH for the first two, but then line 160's `artifact_manifest is None` condition is still true, so the same node ALSO gets SG-ARTIFACT-MANIFEST-MISSING with the message "links an artifact manifest that does not exist" — factually wrong when the file exists but is mislinked, and a duplicate finding for one defect.
- Fix: In \_validate_artifact_manifests in src/project_standards/standards_graph/validators.py, set a local flag (e.g. `mislinked = True`) in both the ESCAPE and MISMATCH branches and change line 160 to `if declared and node.artifact_manifest is None and not mislinked:` (keep the `continue`, or `continue` directly from the ESCAPE/MISMATCH branches). Update/extend tests/test_standards_graph_validators.py to assert an escaping link yields exactly one finding.
- Verification: uv run pytest tests/test_standards_graph_validators.py passes; a fixture with a mismatched [artifacts].manifest link produces only SG-ARTIFACT-MANIFEST-MISMATCH.
- Dependencies: none
- Effort: S

**F-047 — Deduplicate the identical \_digest helper across control-plane modules**

- Category: Structure · Severity: Low · Confidence: High
- Location: src/project_standards/control_plane/planner.py:96-97, src/project_standards/control_plane/snapshot.py:45, src/project_standards/control_plane/adapters/whole_file.py:29-30, src/project_standards/control_plane/migration.py:425
- Evidence:

```text
src/project_standards/control_plane/planner.py:96:def _digest(content: bytes) -> Sha256Digest:
src/project_standards/control_plane/planner.py:97:    return Sha256Digest(f"sha256:{hashlib.sha256(content).hexdigest()}")
```

- Problem: The exact same two-line Sha256Digest wrapper is defined privately in four control-plane modules (planner.py:96, snapshot.py:45, adapters/whole_file.py:29, migration.py:425), plus two str-returning variants elsewhere (recovery.py:117, frontmatter_authoring.py:43). The digest format string ("sha256:...") is a cross-file contract (compared against payload inventory digests and lock digests); duplicating it invites a drift bug if one copy is ever changed.
- Fix: Add a public `content_digest(content: bytes) -> Sha256Digest` function in project_standards/package_contract/paths.py (next to Sha256Digest) with the same body; replace the four private Sha256Digest-returning `_digest` definitions in planner.py, snapshot.py, adapters/whole_file.py, and migration.py with imports of it. Leave the two str-returning variants alone or adapt them to call `.value`.
- Verification: uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest tests/control_plane
- Dependencies: none
- Effort: S

**F-048 — Handle .standards deletion race in detect_control_plane_state instead of reporting MALFORMED**

- Category: Correctness · Severity: Low · Confidence: High
- Location: src/project_standards/control_plane/state.py:258-274 (except clause at 263-268)
- Evidence:

```text
src/project_standards/control_plane/state.py:263:            except ValueError:
src/project_standards/control_plane/state.py:264:                return _state(
src/project_standards/control_plane/state.py:265:                    StateKind.MALFORMED,
src/project_standards/control_plane/state.py:266:                    normalized,
src/project_standards/control_plane/state.py:267:                    "control-plane directory is not a safe regular directory",
```

- Problem: The two-iteration retry loop only covers the absence-to-presence race (comment at state.py:258-259). If `.standards` is removed between the `control.exists()` check and `control_plane_lock` opening it, `_control_directory` raises ValueError ("control-plane directory does not exist") and the repository is reported MALFORMED with the misleading detail "control-plane directory is not a safe regular directory", when the true state is UNINITIALIZED (or LEGACY_ONLY). The broad `except ValueError` also swallows any ValueError escaping `_load_initialized_state` under the same wrong detail message. (Verifier adjustment: The deletion race is real and unguarded: locking.py:93-94 raises ValueError("control-plane directory does not exist") when .standards vanishes after the exists() check, and state.py:263's broad except mislabels it MALFORMED with a wrong detail instead of UNINITIALIZED/LEGACY_ONLY; only the evidence line numbers were off by one (except is at 263, not 264). The secondary swallowed-ValueError claim is structurally true but has no realistic trigger since parsed release strings are pattern-validated before ParsedToolRelease sees them.)
- Fix: In detect_control_plane_state, on ValueError from the `with control_plane_lock(...)` block, re-check `control.exists() or control.is_symlink()`: if the directory no longer exists, fall through to the legacy/uninitialized classification (i.e. `continue` the loop) instead of returning MALFORMED; only return MALFORMED when the path still exists. Optionally narrow the except by catching the lock-acquisition ValueError separately from `_load_initialized_state` (move the load call outside the try or wrap it in its own handler) so load-time errors are not mislabeled as directory-safety failures.
- Verification: uv run pytest tests/control_plane/test_state.py; add a test monkeypatching control_plane_lock to raise ValueError with the directory removed, asserting UNINITIALIZED rather than MALFORMED
- Dependencies: none
- Effort: S

**F-049 — Preserve live file mode when a whole-file artifact declares no mode**

- Category: Correctness · Severity: Low · Confidence: High
- Location: src/project_standards/control_plane/planner.py:1217 (with executor default at src/project_standards/control_plane/executor.py:277)
- Evidence: `src/project_standards/control_plane/planner.py:1217:        mode = desired[0].mode if adapter_kind is AdapterKind.WHOLE_FILE and desired else entry.mode`
- Problem: WholeArtifactDeclaration.mode defaults to None (payload.py:235). For a managed whole-file artifact without a declared mode, a consumer chmod (e.g. 0755) is never detected as drift (\_classify_desired checks mode only when previous.mode or group.mode is not None, planner.py:903/921-923), so the plan is NOOP — but on the next content UPDATE the PlannedTarget.mode is None and the executor stages with `target.mode or "0644"`, silently resetting the consumer's mode to 0644. The lifecycle is inconsistent: mode is neither owned (no drift finding) nor preserved (reset on update).
- Fix: In \_render_targets (planner.py:1217), fall back to the live entry mode when the artifact declares none: `mode = (desired[0].mode if desired[0].mode is not None else entry.mode) if adapter_kind is AdapterKind.WHOLE_FILE and desired else entry.mode`. For CREATE on a missing entry both are None and the executor's 0644 default still applies; for UPDATE of an existing file the consumer's mode is preserved, matching the undeclared-mode non-ownership already implied by the drift checks.
- Verification: uv run pytest tests/control_plane/test_planner.py tests/control_plane/test_executor.py; add a test: managed whole-file artifact with no declared mode, consumer chmod 0755, package content update — assert staged mode stays 0755
- Dependencies: none
- Effort: S

**F-050 — Replace substring-based classification of resolution authorization errors with a typed exception**

- Category: Architecture · Severity: Low · Confidence: High
- Location: src/project_standards/control_plane/resolution.py:248,403-411,545-550 (raise sites), src/project_standards/control_plane/cli.py:669 (dispatch)
- Evidence: `src/project_standards/control_plane/cli.py:669:        if "authorization" in message:`
- Problem: resolution.py raises all refusals as untyped ControlPlaneError strings, and the CLI classifies them by the substring "authorization" in the message: matching messages become an exit-1 CP-RESOLVE-MAJOR-AUTH finding, everything else becomes exit-2 CP-CONTROL-STATE. This is an implicit cross-file contract on message wording: rewording "package-major transition requires matching authorization" (resolution.py:403-404, 548-549) silently changes the CLI exit code, and adjacent authorization refusals ("several target majors were authorized for ..." at resolution.py:248, "accepted-major exit requires an exact target version" at resolution.py:411/545) take the other branch purely because of wording. The exit-code contract (1 = findings, 2 = bad invocation/config) is load-bearing for CI consumers.
- Fix: Add a dedicated exception, e.g. `class ControlPlaneAuthorizationError(ControlPlaneError)` in control_plane/diagnostics.py; raise it at resolution.py:403-404 and 548-549 (and at 248/411/545 if those are also intended to surface as findings — decide explicitly per site); in cli.py replace `if "authorization" in message:` with `except ControlPlaneAuthorizationError` (or isinstance check) so classification is typed, then keep the existing finding/exit behavior unchanged.
- Verification: uv run pytest tests/control_plane/test_cli.py tests/control_plane/test_resolution.py; confirm the CP-RESOLVE-MAJOR-AUTH path still exits 1 and message rewording no longer affects exit codes
- Dependencies: none
- Effort: M

**F-051 — Report after_digest as None for NOOP actions on missing targets**

- Category: Correctness · Severity: Low · Confidence: High
- Location: src/project_standards/control_plane/planner.py:1004-1005,1022
- Evidence: `src/project_standards/control_plane/planner.py:1022:    after = None if kind is ActionKind.REMOVE else _digest(rendered).value`
- Problem: When a target's entry is MISSING and the rendered content is empty (e.g. a package is disabled after the consumer already deleted the managed file), \_target_action classifies the action as NOOP but sets after_digest to sha256 of b"" (e3b0c442...), publicly asserting the file will exist with empty content when it will not exist at all. Empirically confirmed: disabled package + pre-deleted whole-file target yields action kind no-op with after_digest equal to digest(b""). This misleads consumers of the JSON plan surface and feeds a false fact into the apply fingerprint.
- Fix: In \_target_action (planner.py), change line 1022 so `after` is also None when the entry is missing and nothing is created: `after = None if kind is ActionKind.REMOVE or (kind is ActionKind.NOOP and entry.kind is EntryKind.MISSING) else _digest(rendered).value`. No behavior change for existing files (NOOP after_digest there equals the current content digest, which is truthful).
- Verification: uv run pytest tests/control_plane/test_planner.py; add an assertion that the NOOP action for a disabled package with an already-deleted target has after_digest None
- Dependencies: none
- Effort: S

**F-052 — Delete unreachable tail-line branch in markdown \_lines**

- Category: Structure · Severity: Low · Confidence: High
- Location: src/project_standards/control_plane/adapters/markdown.py:80-81
- Evidence:

```text
src/project_standards/control_plane/adapters/markdown.py:80:    if offset < len(text):
        result.append(MarkdownLine(text[offset:], offset, len(text), fence is None))
```

- Problem: str.splitlines(keepends=True) always partitions the full string — ''.join(text.splitlines(keepends=True)) == text, including a final segment with no trailing newline — so after the loop `offset == len(text)` unconditionally and the branch never executes. Dead code that implies splitlines could drop a trailing fragment, misleading future maintenance of the offset bookkeeping that block parsing depends on.
- Fix: Delete lines 80-81 of src/project_standards/control_plane/adapters/markdown.py (the `if offset < len(text):` branch), leaving `return tuple(result)`. No behavior change.
- Verification: cd /home/chris/projects/project-standards && uv run pytest tests/control_plane -k markdown -q && uv run coverage run -m pytest tests/control_plane -k markdown && uv run coverage report
- Dependencies: none
- Effort: S

**F-053 — Remove dead `destination` parameter from \_stage_bytes**

- Category: Structure · Severity: Low · Confidence: High
- Location: src/project_standards/control_plane/executor.py:209-244
- Evidence:

```text
src/project_standards/control_plane/executor.py:209:def _stage_bytes(
    parent_descriptor: int,
    destination: str,
    content: bytes,
    mode: str | None,
) -> str:
```

- Problem: The `destination` parameter is never used inside \_stage_bytes — the function generates a random temporary name and returns it; the eventual destination is passed separately to os.replace by every caller. The parameter is actively misleading at call sites: `_stage_bytes(control.descriptor, "catalog.toml", committed_catalog, "0644")` (line 728) reads as if it writes catalog.toml, when it stages the refresh BACKUP that is later renamed to .catalog-refresh.previous.toml. Ruff does not flag it because ARG rules are not enabled.
- Fix: Delete the `destination` parameter from \_stage_bytes' signature in executor.py and drop the corresponding argument at all six call sites (lines ~273, ~364, ~728, ~753, ~1139 — grep for `_stage_bytes(`). No behavior change.
- Verification: cd /home/chris/projects/project-standards && grep -n '\_stage_bytes(' src/project_standards/control_plane/executor.py && uv run basedpyright && uv run pytest tests/control_plane -q
- Dependencies: none
- Effort: S

**F-054 — Split on \n/\r\n explicitly instead of splitlines in line-oriented parsers**

- Category: Correctness · Severity: Low · Confidence: High
- Location: src/project_standards/control_plane/adapters/markdown.py:66, src/project_standards/control_plane/adapters/editorconfig.py:76
- Evidence: `src/project_standards/control_plane/adapters/markdown.py:66:    for physical in text.splitlines(keepends=True):`
- Problem: str.splitlines treats \v, \f, \x1c-\x1e, \x85, , and as line boundaries, but the surrounding logic assumes only \n/\r\n: markdown.py strips with `physical.rstrip("\r\n")` (line 67) and editorconfig.py computes value spans via `line.rstrip("\r\n")` (line 67), and both \_newline() helpers only know \n vs \r\n. A document containing e.g. inside prose or a value is split into extra pseudo-lines whose text retains the terminator; in markdown a fragment beginning with ``` after a split can flip the fence-state tracking that decides whether managed markers are top-level. The trailing re-parse of rendered output limits the blast radius to spurious ControlPlaneErrors or mis-detected markers rather than silent corruption, but parse decisions (fence state, marker detection, editorconfig property spans) diverge from what editors and Prettier consider a line.
- Fix: In markdown.py \_lines and editorconfig.py_parse, replace `text.splitlines(keepends=True)` with an explicit newline-only splitter, e.g. `re.split(r'(?<=\n)', text)` (keeps \n/\r\n terminators, treats all other control characters as ordinary line content), or iterate via text.split('\n') reconstructing offsets. Keep the existing offset arithmetic; add a regression test with a managed markdown block whose body contains and an editorconfig value containing \x85 asserting inspect/render round-trip unchanged.
- Verification: cd /home/chris/projects/project-standards && uv run pytest tests/control_plane -k 'markdown or editorconfig' -q
- Dependencies: none
- Effort: M

**F-055 — Use fd-based no-follow deletion for namespace prunes in \_publish_targets**

- Category: Security · Severity: Low · Confidence: High
- Location: src/project_standards/control_plane/executor.py:516-525
- Evidence:

```text
src/project_standards/control_plane/executor.py:516:    for namespace in plan.namespace_prunes:
        path = request.planner.repo / namespace
        try:
            for directory in sorted(path.rglob("*"), reverse=True):
                if directory.is_dir():
                    directory.rmdir()
            path.rmdir()
```

- Problem: Every other filesystem mutation in the executor goes through O_NOFOLLOW directory descriptors plus parent-identity rechecks (\_open_parent,\_assert_parent_current), but namespace pruning uses symlink-following Path operations. The planner's \_namespace_prunes checks namespace.is_symlink() at plan time (planner.py:1477) and the plan is re-derived under the lock (executor.py:707), but between that recheck and this loop a concurrent writer can swap .standards/packages/<ns> for a symlink; path.rglob() then resolves the symlinked anchor and directory.rmdir() removes empty directories at the symlink target outside the repository (Path.is_dir() also follows symlinks). Damage is bounded to removing empty directories, but it is exactly the TOCTOU class the rest of this file defends against, making the prune path the weakest link in an otherwise fd-disciplined writer.
- Fix: In \_publish_targets (executor.py), replace the Path-based prune with fd-based deletion: open the namespace via the existing \_open_parent(root_descriptor, ...) chain (which uses O_NOFOLLOW at every component), then walk it with os.fwalk(dir_fd=...) (topdown=False, follow_symlinks=False) removing directories via os.rmdir(name, dir_fd=parent_fd), and finally os.rmdir the namespace entry itself via its parent's descriptor. Keep the current behavior of raising CP-APPLY-PUBLISH on any remaining file. Preserve the applied.append(f"prune:{namespace}") record.
- Verification: cd /home/chris/projects/project-standards && uv run pytest tests/control_plane/test_executor.py tests/control_plane -k prune -q; manual check: fault-hook test that swaps .standards/packages/<ns> for a symlink to an outside dir before the prune phase and asserts the outside dir survives and the apply fails
- Dependencies: none
- Effort: M

**F-056 — Clean up orphaned bootstrap/config-edit staging temporaries (recovery regex misses them)**

- Category: Correctness · Severity: Low · Confidence: High
- Location: src/project_standards/control_plane/bootstrap.py:90; src/project_standards/control_plane/config_edit.py:120; src/project_standards/control_plane/recovery.py:63
- Evidence: `src/project_standards/control_plane/recovery.py:63:_STAGED_TEMPORARY = re.compile(r"^\.project-standards-[0-9a-f]{16}\.tmp$", re.ASCII)`
- Problem: Recovery's staged-temporary pattern only matches executor-style names (`.project-standards-<16hex>.tmp`, executor.py:215). Bootstrap stages `.{name}.<16hex>.tmp` (e.g. `.config.toml.abcd... .tmp`) and config_edit stages `.config.toml.<16hex>.tmp`. If the process is killed between staging and publish, those orphans persist in `.standards/` forever: state detection ignores them, no recovery path removes them, and they surface as untracked repo noise.
- Fix: Either unify all staging on the `.project-standards-<hex>.tmp` naming used by executor.py (change bootstrap.\_stage_file and config_edit.\_atomic_replace_config), or extend \_STAGED_TEMPORARY and the catalog-refresh recovery cleanup to also match `^\.(config|catalog|lock)\.toml\.[0-9a-f]{16}\.tmp$` and remove such orphans during recovery/refresh cleanup.
- Verification: uv run pytest tests/control_plane/test_recovery.py tests/control_plane/test_bootstrap.py tests/control_plane/test_config_edit.py; add a test seeding an orphan `.config.toml.<hex>.tmp` and asserting the chosen cleanup path removes it.
- Dependencies: none
- Effort: S

**F-057 — Differentiate render exit codes: recoverable runtime failures should not all exit 2**

- Category: Convention · Severity: Low · Confidence: High
- Location: src/project_standards/control_plane/cli.py:241-249
- Evidence: `src/project_standards/control_plane/cli.py:249:        return _emit_error(json_mode, "CP-RENDER", str(exc), exit_code=2)`
- Problem: run_render maps every failure — including lock contention (ControlPlaneBusyError is a RuntimeError, caught here), transient OSError, and provider runtime failures — to exit 2, which the project contract reserves for bad invocation/config; recoverable conditions should exit 1. A CI wrapper distinguishing 'retryable' (1) from 'fix your invocation' (2) gets the wrong signal for CP-BUSY.
- Fix: In run_render's except block, catch ControlPlaneBusyError separately and return_emit_error(json_mode, "CP-BUSY", str(exc), exit_code=1); optionally route OSError to exit 1 as well, keeping CommandResolutionError/ControlPlaneError/ValueError at 2.
- Verification: uv run pytest tests/control_plane/test_cli.py -k render; add a test holding the .standards exclusive lock and asserting `render` exits 1 with CP-BUSY.
- Dependencies: none
- Effort: S

**F-058 — Remove the no-op try/except in resolve_selected_package**

- Category: Structure · Severity: Low · Confidence: High
- Location: src/project_standards/control_plane/command_resolution.py:368-387
- Evidence:

```text
src/project_standards/control_plane/command_resolution.py:386:    except CommandResolutionError:
        raise
```

- Problem: The function body is wrapped in `try: ... except CommandResolutionError: raise`, which re-raises the only exception it catches — a pure no-op that suggests error handling exists where none does, and adds an indentation level.
- Fix: Delete the try/except wrapper in resolve_selected_package, keeping the body statements at function level unchanged.
- Verification: uv run ruff check src/project_standards/control_plane/command_resolution.py && uv run pytest tests/control_plane/test_command_resolution.py
- Dependencies: none
- Effort: S

**F-059 — Replace substring matching on exception messages with typed errors for classification**

- Category: Structure · Severity: Low · Confidence: High
- Location: src/project_standards/control_plane/cli.py:669; src/project_standards/control_plane/command_resolution.py:323
- Evidence: `src/project_standards/control_plane/cli.py:669:        if "authorization" in message:`
- Problem: run() classifies any caught error whose message contains 'authorization' as a resolution refusal (exit 1, CP-RESOLVE-MAJOR-AUTH finding) — an OSError or PackageContractError whose text happens to contain that word gets the wrong code, exit status, and JSON shape. Likewise resolve_enabled_companion treats any CommandResolutionError containing 'not present' or 'disabled' as an absent companion and silently returns None, so an unrelated future error message containing 'disabled' would be swallowed. Behavior is coupled to exact prose of error strings across modules.
- Fix: Introduce a typed exception (e.g. MajorAuthorizationError(ControlPlaneError)) raised at the resolution.py refusal sites and catch that type in cli.py run() instead of the substring test; similarly raise/catch distinct subclasses of CommandResolutionError (e.g. CompanionAbsentError) for the 'not present'/'disabled' cases in command_resolution.py, keeping messages unchanged.
- Verification: uv run pytest tests/control_plane/test_cli.py tests/control_plane/test_command_resolution.py tests/control_plane/test_resolution.py
- Dependencies: none
- Effort: M

**F-060 — Report the actual mode in the authorization-refusal JSON when --apply was requested**

- Category: Correctness · Severity: Low · Confidence: High
- Location: src/project_standards/control_plane/cli.py:685
- Evidence: `src/project_standards/control_plane/cli.py:685:                            "mode": "check" if cast("bool", args.check) else "plan",`
- Problem: When a major-authorization refusal is raised during `reconcile --apply --json` (planning happens before apply), the emitted JSON reports mode "plan" instead of "apply", so JSON consumers cannot tell an apply attempt was refused.
- Fix: Compute mode once near the top of run(): `mode = "apply" if args.apply else ("check" if args.check else "plan")` and use it at line 685.
- Verification: uv run pytest tests/control_plane/test_cli.py -k allow_major; add an assertion that `reconcile --apply --json` with an unauthorized major reports "mode": "apply".
- Dependencies: none
- Effort: S

**F-061 — Return applied action ids from failed recovery publishes instead of an empty tuple**

- Category: Correctness · Severity: Low · Confidence: High
- Location: src/project_standards/control_plane/recovery.py:412-460,463-519
- Evidence: `src/project_standards/control_plane/recovery.py:519:        return ApplyResult(False, (), False, "CP-RECOVERY-APPLY")`
- Problem: \_publish_catalog and \_publish_catalog_refresh_recovery accumulate an `applied` list, but their `except ValueError, OSError:` handlers return ApplyResult(False, (), ...). If os.fsync or a cleanup os.unlink fails AFTER os.replace published catalog.toml (or after some temporaries were removed), the caller and the reconcile --repair-state JSON report 'nothing applied' even though authority files were mutated. executor.py's equivalent handlers return tuple(applied) on failure, so this drifts from the established reporting contract and misleads operators diagnosing a half-completed recovery.
- Fix: In recovery.py, hoist `applied: list[str] = []` above the try in both \_publish_catalog and \_publish_catalog_refresh_recovery (in \_publish_catalog, append ".standards/catalog.toml" right after the os.replace succeeds), and change both failure returns to ApplyResult(False, tuple(applied), False, "CP-RECOVERY-APPLY").
- Verification: uv run pytest tests/control_plane/test_recovery.py; add a test faulting os.fsync after os.replace (monkeypatch) and asserting the failed ApplyResult lists ".standards/catalog.toml" in applied_action_ids.
- Dependencies: none
- Effort: S

**F-062 — Use findings_to_jsonable for the CP-RESOLVE-MAJOR-AUTH finding to keep JSON shape consistent**

- Category: Convention · Severity: Low · Confidence: High
- Location: src/project_standards/control_plane/cli.py:687
- Evidence: `src/project_standards/control_plane/cli.py:687:                            "findings": [asdict(finding)],`
- Problem: Every other JSON emission path serializes findings through findings_to_jsonable, which omits None-valued fields (line, locus); this one path uses dataclasses.asdict directly, so its finding objects include "line": null and "locus": null — an inconsistent public JSON shape for the same finding type.
- Fix: Replace `[asdict(finding)]` with `findings_to_jsonable([finding])` (already imported at cli.py:17) and drop the now-unused `from dataclasses import asdict` if nothing else uses it.
- Verification: uv run pytest tests/control_plane/test_cli.py -k json; assert the CP-RESOLVE-MAJOR-AUTH JSON finding has no null-valued keys.
- Dependencies: none
- Effort: S

**F-063 — Add the Pre-commit hooks section to the README table of contents**

- Category: Docs · Severity: Low · Confidence: High
- Location: README.md:26-27 (ToC), README.md:172 (section)
- Evidence: `README.md:172: ### Pre-commit hooks`
- Problem: The '### Pre-commit hooks' section was added under 'Consuming the standards' in this commit (69c4865), but the Table of Contents (README.md:24-27) jumps from 'Pin to a release tag, not `main`' straight to 'Versioning', so the new section is undiscoverable from the ToC while every sibling ### heading is listed.
- Fix: Insert `- [Pre-commit hooks](#pre-commit-hooks)` in the README ToC directly after the line 26 entry '- [Pin to a release tag, not `main`](#pin-to-a-release-tag-not-main)'.
- Verification: Every ##/### heading in README.md has a matching ToC entry; markdownlint and Prettier stay clean.
- Dependencies: none
- Effort: S

**F-064 — Correct the phantom '1.3.0' release references in the design-history indexes**

- Category: Docs · Severity: Low · Confidence: High
- Location: docs/handoff/specs-plans.md:47; docs/specs/archive/README.md:15
- Evidence:

```text
docs/handoff/specs-plans.md:47: | Linting/formatting stack (DEC-1…9 trail) | `docs/specs/archive/2026-06-04-linting-formatting-stack.md` | implemented (1.3.0) |
```

- Problem: No 1.3.0 release ever existed: git tags go v1.2.0 → v2.0.0, CHANGELOG has no 1.3.0 section, and deployed.md freezes v1 at 1.2.0. The lint/format stack targeted 1.3.0 but actually shipped inside 2.0.0, so both index rows point readers at a nonexistent release when tracing where the feature landed.
- Fix: In docs/handoff/specs-plans.md:47 change 'implemented (1.3.0)' and in docs/specs/archive/README.md:15 change 'implemented (v1.3.0)' to 'implemented (shipped in v2.0.0; originally targeted an unreleased 1.3.0)'.
- Verification: grep -rn '1\.3\.0' docs/handoff docs/specs returns only session-log history rows (which are append-only and stay untouched).
- Dependencies: none
- Effort: S

**F-065 — Make the two adopt agent-handoff synopses in usage.md agree on --force**

- Category: Docs · Severity: Low · Confidence: High
- Location: docs/usage.md:43 vs docs/usage.md:203
- Evidence: `docs/usage.md:43: project-standards adopt agent-handoff [<standard>...] [--dest <dir>] (--manual | --harness {claude-code | codex}...) [--dry-run] [--json]`
- Problem: The top-level SYNOPSIS omits [--force] from the specialized agent-handoff adopt form, while the command-section synopsis (line 203) includes it. The implementation accepts it: cli.py \_parse_early_adopt handles --force and src/project_standards/agent_handoff/providers.py:48 declares parser.add_argument("--force", ...). The two synopses for the same command contradict each other, and the CLI Documentation Standard this doc dogfoods is drift-gated.
- Fix: In docs/usage.md line 43, add [--force] to match line 203: `project-standards adopt agent-handoff [<standard>...] [--dest <dir>] (--manual | --harness {claude-code | codex}...) [--force] [--dry-run] [--json]`.
- Verification: diff of the two synopsis lines shows the identical option surface; usage-doc parity tests still pass.
- Dependencies: none
- Effort: S

**F-066 — Mark the legacy --config verification command in mcp-readiness.md as historical/non-reproducible**

- Category: Docs · Severity: Low · Confidence: High
- Location: docs/mcp-readiness.md:58
- Evidence: `docs/mcp-readiness.md:58: uv run project-standards validate --config .project-standards.yml`
- Problem: The doc is status: active and presents this as one of the commands backing the Step 07 pass, but `.project-standards.yml` no longer exists (STATUS.md: 'legacy `.project-standards.yml` authority is absent') and under unified authority an explicit --config override is rejected with exit 2 (docs/usage.md:84, UPGRADING.md:102). An agent re-running the documented evidence commands today gets a hard failure on this line while every other command still works.
- Fix: In docs/mcp-readiness.md, either change line 58 to the current form `uv run project-standards validate` or add a note in the Verification Commands intro that the --config invocation reflects the pre-migration 2026-07-12 repository state and is superseded by plain `validate` under the unified control plane.
- Verification: Every command in the Verification Commands block either runs successfully at HEAD or is explicitly labeled historical.
- Dependencies: none
- Effort: S

**F-067 — Note the npm ci coherence step in README's developer command block**

- Category: Convention · Severity: Low · Confidence: High
- Location: README.md:199-212; AGENTS.md:32
- Evidence: `README.md:206: uv run coverage run --source=project_standards -m pytest -m "not performance and not compatibility"`
- Problem: AGENTS.md:32 and CLAUDE.md require running `tests/coherence` after `npm ci` as part of the pre-commit toolchain gate, but README's 'Developing this repository' block never runs npm ci. Because tests/coherence/test_behavioral.py skips itself when node_modules is absent ('Node dev deps not installed (run `npm ci`)…'), a contributor following only the README gets a silently green run that never exercised the behavioral coherence gate the agent instructions call required.
- Fix: Add `npm ci` (before the pytest line) to the README developing block, or append one sentence after the block: 'Run `npm ci` first so the tests/coherence behavioral gate executes instead of skipping; see AGENTS.md for the full pre-commit gate.'
- Verification: Following the README block verbatim on a fresh clone reports the coherence behavioral tests as executed (not skipped) in the pytest summary.
- Dependencies: none
- Effort: S

**F-068 — Strip single quotes in bugs/\_regen_index.py so INDEX.md renders clean values**

- Category: Correctness · Severity: Low · Confidence: High
- Location: docs/handoff/bugs/\_regen_index.py:19,32; docs/handoff/bugs/INDEX.md:7-9
- Evidence: `docs/handoff/bugs/_regen_index.py:19:        fields[key.strip()] = value.strip().strip('"')`
- Problem: Bug frontmatter uses single-quoted values (bug_id: '001', services: '[ci, github-actions]'), but the parser strips only double quotes. The generated INDEX.md therefore renders every cell with literal quotes ('001', '2026-06-07', '[ci, github-actions]'), and the later .strip("[]") on services is a no-op because the surrounding quotes shield the brackets — the table is functional but every regeneration reproduces the quoting artifacts.
- Fix: In docs/handoff/bugs/\_regen_index.py line 19, change .strip('"') to .strip('\'"') (strip both quote characters), then regenerate INDEX.md with `python3 docs/handoff/bugs/_regen_index.py` so cells read 001 / 2026-06-07 / ci, github-actions without quotes and the services bracket-strip takes effect.
- Verification: Run python3 docs/handoff/bugs/\_regen_index.py; INDEX.md rows contain no leading/trailing apostrophes and services cells contain no brackets.
- Dependencies: none
- Effort: S

**F-069 — Update AGENTS.md to name Standard Bundle Authoring 2.1 as the internal package**

- Category: Docs · Severity: Low · Confidence: High
- Location: AGENTS.md:9 ; also standards/README.md:19
- Evidence:

```text
AGENTS.md:9: This repo is the source of truth for reusable project standards. Catalog 5 has seven consumer packages plus reference-only **Python Coding** and internal **Standard Bundle Authoring 2.0**.
standards/README.md:19:| Standard Bundle Authoring | The V2 family, payload, catalog, provider, relationship, and ownership contract | 2.0 | internal | [standard-bundle-authoring/](standard-bundle-authoring/) | — (**internal/reference**; governs this repository's packages) |
```

- Problem: Since the 5.0.2 preparation, 2.1 is the family's current authority (CHANGELOG 5.0.2, docs/STATUS.md:7, docs/handoff/conventions.md:118, README.md:126 all say 2.1; 2.0 is only released history). docs/TODO.md:29 claims all stale bundle-authoring 2.0 references were bumped to 2.1 in the same task, but AGENTS.md — the primary per-session agent context file — was missed, so every agent session starts with stale catalog state.
- Fix: In AGENTS.md line 9, change 'internal **Standard Bundle Authoring 2.0**' to 'internal **Standard Bundle Authoring 2.1**' (or drop the version number to match CLAUDE.md's versionless phrasing). standards/README.md:19 has the same stale 2.0 reference; update both files in one commit.
- Verification: grep -n 'Standard Bundle Authoring' AGENTS.md shows 2.1 (or no version); grep -rn 'Authoring 2.0' AGENTS.md returns nothing.
- Dependencies: none
- Effort: S

**F-070 — Anchor the docs/research/ path rule to path segments**

- Category: Correctness · Severity: Low · Confidence: High
- Location: src/project_standards/format_frontmatter.py:450-457
- Evidence: `src/project_standards/format_frontmatter.py:453:    if "docs/research/" in posix or posix.startswith("docs/research/"):`
- Problem: The substring test matches any path merely containing 'docs/research/' — e.g. 'old-docs/research/notes.md' or 'mydocs/research/x.md' — so infer_doc_type/scaffold assigns doc_type 'research' to files outside the standard's docs/research/ tree. The startswith clause is redundant (a subset of the `in` test), suggesting the segment-boundary intent was lost.
- Fix: Replace the condition with `posix.startswith("docs/research/") or "/docs/research/" in posix` (segment-anchored), in \_infer_doc_type in format_frontmatter.py. Add a test asserting Path('old-docs/research/n.md') infers None (or 'index'/'note' per the other rules) rather than 'research'.
- Verification: uv run python -c "from pathlib import Path; from project_standards.format_frontmatter import \_infer_doc_type; assert_infer_doc_type(Path('old-docs/research/n.md')) != 'research'"
- Dependencies: none
- Effort: S

**F-071 — Check references-enabled before printing the custom-schema skip note**

- Category: Convention · Severity: Low · Confidence: High
- Location: src/project_standards/frontmatter_commands.py:389-396, src/project_standards/validate_references.py:344-352
- Evidence: `src/project_standards/frontmatter_commands.py:389:    if effective.get("schema") == "custom" and surface in {"validate-id", "validate-references"}:`
- Problem: In the unified path, the custom-schema note is emitted before the references-enabled check, so `validate-references` in a repo with a custom schema and references DISABLED prints 'note: custom schema in use; skipping reference validation' on every run. The legacy standalone main deliberately orders it the other way (disabled -> silent return 0 at validate_references.py:344-345, note only when the operator actually enabled references, per the comment at 347-351). The unified surface therefore emits a misleading note implying a configured check was skipped when none was configured.
- Fix: In run_locked_standalone_validate (frontmatter_commands.py), for surface == 'validate-references' move the references-enabled early-return (lines 394-396) above the custom-schema note, or restrict the note at line 389-392 to `surface == 'validate-id' or (surface == 'validate-references' and references enabled)`.
- Verification: In a unified-config repo with schema: custom and references disabled, `uv run validate-references` produces no output and exits 0 (currently prints the note).
- Dependencies: none
- Effort: S

**F-072 — Deduplicate the hardcoded ADR-branch include/exclude scope in run_validate**

- Category: Structure · Severity: Low · Confidence: High
- Location: src/project_standards/frontmatter_commands.py:577-582, src/project_standards/validate_frontmatter.py:766-784
- Evidence: `src/project_standards/frontmatter_commands.py:581:                    ["**/*.template.md", "AGENTS.md", "CLAUDE.md", ".standards/**"],`
- Problem: The adr-only branch of run_validate hardcodes a second copy of the document scope that silently diverges from the markdown-frontmatter unified defaults in config_from_unified_options (it omits '.claude/**', '.agents/**', '.codex/**', '.github/**', 'node_modules/**' and adds '.standards/**'). Two hand-maintained copies of the same corpus definition will drift further; today an adr-only repo already validates ADR docs in trees the frontmatter package deliberately excludes.
- Fix: Extract module-level constants DEFAULT_INCLUDE and DEFAULT_EXCLUDE in validate_frontmatter.py holding the lists currently inlined at lines 769 and 774-783 (add '.standards/**' to DEFAULT_EXCLUDE if that is the intended shared behavior, or keep it as an adr-branch addition `[\*DEFAULT_EXCLUDE, ".standards/**"]`); use them in config_from_unified_options and in frontmatter_commands.run_validate's adr branch.
- Verification: uv run pytest tests/ -k "adr and validate" and grep -rn 'docs/\*\*/\*.md"' src/project_standards — the literal list should appear once.
- Dependencies: none
- Effort: S

**F-073 — Fix default exclude '**/\*.template.md' not matching repo-root files under fnmatch\*\*

- Category: Correctness · Severity: Low · Confidence: High
- Location: src/project_standards/validate_frontmatter.py:443-468 (fnmatch exclusion), src/project_standards/validate_frontmatter.py:774-783 (unified defaults), src/project_standards/frontmatter_commands.py:581 (adr branch)
- Evidence: `src/project_standards/validate_frontmatter.py:775:                "**/*.template.md",`
- Problem: Exclusion uses fnmatchcase, where '**/' requires a literal '/' in the candidate — fnmatchcase('foo.template.md', '**/_.template.md') is False (verified) while nested 'docs/foo.template.md' matches. Path.glob's '\*\*/' matches zero directories, so the shipped default exclude behaves differently at the repo root than its glob-dialect spelling implies: a root-level _.template.md named explicitly (e.g. by a pre-commit hook passing staged files) or matched by a consumer include like '_.md' is validated instead of excluded. The collect_paths docstring documents the '_-spans-separators' direction of the dialect asymmetry but not this opposite direction.
- Fix: In collect_paths' is_excluded (validate_frontmatter.py), for each pattern starting with '\*\*/' additionally test fnmatchcase(key, pattern[3:]) (i.e. also match the root-level form); document this in the existing pattern-dialect comment. This also fixes the same default list in config_from_unified_options and the copy in frontmatter_commands.py:581 without touching them.
- Verification: uv run python -c "from project_standards.validate_frontmatter import collect_paths" plus a unit test: a tmp repo with root 'foo.template.md', include ['*.md'], default excludes -> collect_paths must drop it.
- Dependencies: none
- Effort: S

**F-074 — Load the doc_type enum lazily and with explicit UTF-8 in format_frontmatter**

- Category: Structure · Severity: Low · Confidence: High
- Location: src/project_standards/format_frontmatter.py:34-37
- Evidence: `src/project_standards/format_frontmatter.py:36:    json.loads(_SCHEMA_PATH.read_text())["properties"]["doc_type"]["enum"]`
- Problem: VALID_DOC_TYPES is computed at import time, so a wheel with a missing/corrupt bundled schema kills even `format-frontmatter --help` (and any importer, e.g. frontmatter_authoring) with a raw traceback — the exact failure mode validate_id.\_load_doc_types documents avoiding ('at import time a broken wheel would kill even validate-id --help'). Additionally read_text() omits encoding='utf-8', so it decodes with the locale encoding, unlike every other read in the package.
- Fix: Replace the module-level constant with a lazy accessor mirroring validate_id: a functools.cache function `_valid_doc_types() -> frozenset[str]` reading_SCHEMA_PATH with encoding='utf-8' and mapping OSError/json.JSONDecodeError/KeyError/TypeError to a clean error; update the three users (VALID_DOC_TYPES uses in infer_doc_type and frontmatter_authoring imports at line 21/169/201/221/262/285) to call it. Keep a module attribute alias only if backward compatibility of the name is required, implemented via **getattr**.
- Verification: Temporarily rename the schema file in an extracted wheel and confirm `format-frontmatter --help` exits 0; uv run pytest tests/test_format_frontmatter.py.
- Dependencies: none
- Effort: M

**F-075 — Remove or clearly quarantine the production-dead fix_file direct-write path**

- Category: Structure · Severity: Low · Confidence: High
- Location: src/project_standards/validate_id.py:319-337 (\_atomic_write_bytes), src/project_standards/validate_id.py:478-495 (fix_file)
- Evidence:

```text
src/project_standards/validate_id.py:478:def fix_file(
    path: Path,
    valid_doc_types: frozenset[str] | None = None,
    existing_ids: set[str] | None = None,
) -> FixResult:
```

- Problem: No CLI path calls fix_file anymore: validate-id --fix routes through plan_frontmatter_id_fix + apply_authoring_plan in both the unified and legacy branches, and grep shows fix_file/\_atomic_write_bytes referenced only by tests. This keeps alive a second, divergent write path that bypasses the control-plane plan/lock/precondition machinery (no precondition digest, no lock) — exactly the kind of unmanaged mutation the V5 transactional model exists to prevent — and tests spend effort pinning behavior no product path exercises.
- Fix: If fix_file is not a supported library API for external consumers, delete fix_file and \_atomic_write_bytes from validate_id.py along with their dedicated tests in tests/test_validate_id.py (keeping plan_fix_content and its tests, which the planner uses); update the check_file docstring at line 244 which references fix_file. If it IS supported API, add a docstring note that it bypasses control-plane locking and must not be used inside a unified-config repo.
- Verification: grep -rn 'fix_file\|\_atomic_write_bytes' src/ returns only plan-path code; uv run pytest tests/test_validate_id.py tests/test_cli_fix.py passes.
- Dependencies: none
- Effort: M

**F-076 — Report an empty frontmatter block accurately instead of 'not terminated'**

- Category: Correctness · Severity: Low · Confidence: High
- Location: src/project_standards/validate_frontmatter.py:292-306, src/project_standards/validate_frontmatter.py:71 (\_FRONTMATTER_RE)
- Evidence:

```text
src/project_standards/validate_frontmatter.py:304:    if re.match(r"\A---[ \t]*\r?\n", text):
        return "frontmatter block is not terminated by ---"
```

- Problem: \_FRONTMATTER_RE requires at least one body line between the fences, so a zero-body block '---\n---\n' never matches; \_no_frontmatter_reason's fallback probe then reports 'frontmatter block is not terminated by ---' while the author is looking at a visibly terminated (empty) block — a misdiagnosis of exactly the kind the helper exists to prevent (verified: parse_frontmatter returns None and the reason string is the untermination message).
- Fix: In _no_frontmatter_reason (validate_frontmatter.py), before the unterminated probe add: if re.match(r"\A---[ \t]_\r?\n---[ \t]\_(?:\r?\n|$)", text): return "frontmatter block is empty (not a YAML mapping)". Keep parse_frontmatter's None contract unchanged. Add a test in tests covering '---\n---\n# body'.
- Verification: uv run python -c "from project_standards.validate_frontmatter import \_no_frontmatter_reason; print(\_no_frontmatter_reason('---\n---\n# b\n'))" prints the new empty-block message.
- Dependencies: none
- Effort: S

**F-077 — Return exit code 2 for invocation/config errors in the sync tools**

- Category: Convention · Severity: Low · Confidence: High
- Location: src/project_standards/sync_standards_include.py:48,98-101,122-125; src/project_standards/sync_vscode_colors.py:43,55-59,126-129; docs/usage.md:753,774
- Evidence:

```text
docs/usage.md:753: "Exit status: `0` synced (or `--version`) · non-zero via `sys.exit(message)` when not in a git repo, when a required file is missing, or when the include block cannot be found (these print a message and exit `1`)." — the exit-1 behavior is the documented per-tool contract, not drift from it.
```

- Problem: sys.exit(str) always exits with status 1. Missing files, not-in-a-git-repo, an unlocatable include: block, and missing markdown.frontmatter.include are all operator/config errors, which the repo's stated CLI contract (and every other CLI in this package, e.g. ConfigError -> exit 2) maps to exit 2. Scripts distinguishing 'recoverable finding' (1) from 'bad invocation' (2) misclassify every sync-tool failure. (Verifier adjustment: Evidence and exit-1 behavior are accurate, but the repo's stated contract for these two tools is exit 1, documented at docs/usage.md:753 and :774 ("these print a message and exit 1"), and the CLI docs standard only reserves exit 2 where an argparse-style parser does so naturally — these tools have no parser. Downgraded from Medium/stated-contract-violation to Low/consistency smell; any fix must also update usage.md:753,774 or it introduces doc drift.)
- Fix: In both files, replace each `sys.exit(f"error: ...")` with `print(f"error: ...", file=sys.stderr); raise SystemExit(2)` (or a small `_fail2(msg)` helper per file). Update tests asserting these paths (tests/test_sync_standards_include.py, tests/test_sync_vscode_colors.py) to expect returncode 2.
- Verification: cd /tmp && uv run sync-vscode-colors /nonexistent.yml; echo $? # must print 2 (after also handling the git-root case)
- Dependencies: none
- Effort: S

**F-078 — Use a callable replacement and anchor the include: rewrite regex**

- Category: Correctness · Severity: Low · Confidence: High
- Location: src/project_standards/sync_standards_include.py:90-96
- Evidence:

```text
src/project_standards/sync_standards_include.py:92:    updated = re.sub(
        r"(    include:\n)((?:      [^\n]*\n)*)",
        f"    include:\n{new_items}",
        content,
    )
```

- Problem: Two defects in one statement: (1) new_items is passed as a re.sub replacement STRING, so backslash sequences in patterns are interpreted — a filePath containing a single backslash (e.g. 'docs\\x.md' from a Windows-authored settings file) raises re.error('bad escape \\x') as an uncaught traceback (verified), and '\\\\' silently halves to '\\'; (2) the pattern is unanchored to markdown.frontmatter, so re.sub rewrites EVERY 4-space-indented 'include:' block in the file, not just the frontmatter one.
- Fix: Change the re.sub call to use a callable replacement (`lambda m: "    include:\n" + new_items`) which disables escape processing, and pass count=1 (or anchor the pattern to the frontmatter context, e.g. match 'markdown:\n' ... 'frontmatter:' ... 'include:' with a non-greedy prefix) so only the first/frontmatter include block is replaced. Add a test with a pattern containing a backslash and a config containing a second ' include:' block.
- Verification: uv run pytest tests/test_sync_standards_include.py after adding the backslash-pattern test; the current code raises re.error on it.
- Dependencies: none
- Effort: S

**F-079 — Avoid rebuilding and re-hashing the full repository once per catalog major**

- Category: Performance · Severity: Low · Confidence: High
- Location: src/project_standards/package_contract/cli.py:108-120
- Evidence:

```text
src/project_standards/package_contract/cli.py:112:    repositories = (
        [build_package_repository(root, catalog_major=major) for major in majors]
```

- Problem: \_validated_repositories calls build_package_repository once per discovered catalog major; each call re-discovers families, re-parses every manifest, and re-SHA256-hashes every payload byte via validate_payload_integrity. During a catalog-major transition (catalogs/5.toml and catalogs/6.toml both present — the exact state ADR 0024 majors are designed for), validate-packages does the entire integrity pass twice for identical bytes, doubling the dominant cost of the command.
- Fix: Build the repository once (build_package_repository(root) with no catalog), then for each major load and validate the catalog against the already-loaded family_map/payload_map (load_catalog_source + validate_catalog_source, wrapping failures into PC-CATALOG-INVALID findings exactly as build_package_repository does), and run validate_package_graph per (repository, catalog) pair — requires letting validate_package_graph accept the catalog separately or constructing PackageRepository copies via dataclasses.replace(repository, catalog=...).
- Verification: uv run pytest tests/package_contract/ -k 'cli or end_to_end'; optionally time `uv run project-standards standards validate-packages` with two catalog files present before/after
- Dependencies: none
- Effort: M

**F-080 — Correct the validate_payload_integrity docstring about **pycache** exemption**

- Category: Docs · Severity: Low · Confidence: High
- Location: src/project_standards/package_contract/integrity.py:164, src/project_standards/package_contract/integrity.py:126-131
- Evidence: `src/project_standards/package_contract/integrity.py:164:    """Verify every payload byte before returning its canonical aggregate identity."""`
- Problem: The docstring claims every payload byte is verified, but \_live_files (lines 126-131) silently exempts **pycache** directories and their .pyc files from the inventory and digest chain — deliberate, so the dogfooded runtime can import payload Python without tripping integrity, but undocumented. A future session reading the docstring will assume total coverage and may treat the pycache carve-out as a bug (or, worse, extend the exemption pattern without understanding the trade-off).
- Fix: Amend the validate_payload_integrity docstring to state the one exemption ('every payload byte except interpreter-generated **pycache**/\*.pyc, which are ephemeral and excluded from the digest chain') and add a brief intent comment at the **pycache** branch in \_live_files explaining why .pyc bytes are exempt (runtime imports of payload Python create them; non-.pyc content inside **pycache** still fails).
- Verification: uv run ruff format --check . && uv run pytest tests/package_contract/test_integrity.py
- Dependencies: none
- Effort: S

**F-081 — Exclude internal and reference-only catalog entries from migration entry/exit path requirements**

- Category: Correctness · Severity: Low · Confidence: Medium
- Location: src/project_standards/package_contract/graph.py:459-489
- Evidence:

```text
src/project_standards/package_contract/graph.py:460:            if entry.version.major == default.version.major:
                continue
```

- Problem: The PC-MIGRATION-ENTRY/PC-MIGRATION-EXIT loop iterates every catalog entry of a family that has a consumer default, filtering only by major — not by role. If a family ever mixes a consumer default with an internal or reference-only entry on another major (availability is per payload version, so this is representable), the non-selectable entry would be required to have consumer migration entry/exit paths, contradicting the internal-additive PATCH rule's premise that internal entries 'cannot change any consumer's resolution'. Currently latent: catalog 5 has no mixed family (standard-bundle-authoring and python-coding have no default), so no live breakage.
- Fix: In graph.py \_validate_migrations, skip entries whose role is CatalogRole.INTERNAL or CatalogRole.REFERENCE_ONLY before the_reachable checks (add 'if entry.role in {CatalogRole.INTERNAL, CatalogRole.REFERENCE_ONLY}: continue' after the same-major continue), and add a test with a family holding a consumer default plus an internal entry on another major asserting no PC-MIGRATION-ENTRY/EXIT findings.
- Verification: uv run pytest tests/package_contract/test_graph.py
- Dependencies: none
- Effort: S

**F-082 — Guard against silent family drop when schema_version sits past the 4096-byte preamble window**

- Category: Correctness · Severity: Low · Confidence: High
- Location: src/project_standards/package_contract/discovery.py:68-76
- Evidence: `src/project_standards/package_contract/discovery.py:73:            prefix = stream.read(4096)`
- Problem: \_has_v2_preamble reads only the first 4096 bytes and matches comments-then-schema_version. A genuine V2 standards/<id>/standard.toml whose leading comment block exceeds 4096 bytes is silently classified as non-V2: the family disappears from discovery, validation, and projection with zero findings (the silent-skip is designed for legacy V1 manifests, but it also swallows valid V2 files). A standards author adding a long header comment could un-index a family without any signal until consumer breakage.
- Fix: In \_has_v2_preamble, when the 4096-byte prefix consists solely of comment/blank lines (i.e. the regex fails only because the window ended), read further (loop reading 4096-byte chunks until a non-comment line or EOF), or simply raise/emit a PC-FAMILY-MANIFEST-MISSING-style finding when standards/<id>/standard.toml exists, parses as TOML, and declares schema_version = "2.0" but was not matched by the preamble heuristic.
- Verification: Add a discovery test with a standard.toml containing >4096 bytes of leading comments before schema_version = "2.0" and assert it is discovered (or produces a finding); uv run pytest tests/package_contract/test_discovery.py
- Dependencies: none
- Effort: M

**F-083 — Remove or annotate unreachable graph re-checks duplicated from the payload validator**

- Category: Structure · Severity: Low · Confidence: High
- Location: src/project_standards/package_contract/graph.py:106-133, src/project_standards/package_contract/graph.py:382-386, src/project_standards/package_contract/graph.py:417-426
- Evidence: `src/project_standards/package_contract/graph.py:131:                    "extends and conflicts must have exact payload-owned ADR evidence",`
- Problem: The PC-RELATION-EVIDENCE block (graph.py:106-133), the unregistered-legacy-state endpoint check (382-386), and the unused-legacy-state check (417-426) re-implement invariants that PayloadManifest.\_resource_identity_and_config_schema already raises on (payload.py:758-778 'relation evidence must exactly match...', 894-899 'unregistered legacy state', 915-916 'unused legacy state'). Any payload violating them fails load_payload_manifest and never reaches validate_package_graph via the CLI, so these graph findings are unreachable dead paths kept only for hand-built repositories in tests; the duplicated logic can silently diverge from the loader's rules.
- Fix: Either delete the three duplicated checks from graph.py (relation-evidence block in \_validate_relations; the legacy_state_ids membership branch and the trailing unused-legacy-state finding in \_validate_migrations), or keep them and add a one-line comment on each stating they are defense-in-depth for repositories constructed without load_payload_manifest, referencing the payload.py validator as the authoritative copy.
- Verification: uv run pytest tests/package_contract/test_graph.py tests/package_contract/test_payload.py; uv run coverage report to confirm no coverage drop below 85%
- Dependencies: none
- Effort: S

**F-084 — Replace substring sniffing when choosing the render-consumer-catalog JSON error code**

- Category: Structure · Severity: Low · Confidence: High
- Location: src/project_standards/package_contract/cli.py:219-221
- Evidence: `src/project_standards/package_contract/cli.py:220:        code = "bad_output" if "output" in str(exc) else "catalog_error"`
- Problem: The machine-readable JSON error code is chosen by checking whether the exception message contains the substring 'output'. Any unrelated PackageContractError whose text happens to include 'output' is misreported as bad_output, and rewording the_resolved_output messages silently flips codes — brittle coupling between human text and the JSON contract.
- Fix: Introduce a distinct exception type (e.g. class \_OutputPathError(PackageContractError)) raised by_resolved_output, and select code = 'bad_output' via isinstance(exc, \_OutputPathError) in the except clause of_run_render_consumer_catalog; keep 'catalog_error' for everything else.
- Verification: uv run pytest tests/package_contract/test_cli.py; uv run basedpyright
- Dependencies: none
- Effort: S

**F-085 — Unify catalog-major discovery between cli.\_catalog_majors and projection.\_catalog_sources**

- Category: Structure · Severity: Low · Confidence: High
- Location: src/project_standards/package_contract/cli.py:84-105, src/project_standards/package_contract/projection.py:72-93
- Evidence: `src/project_standards/package_contract/cli.py:101:            if major >= 1:`
- Problem: cli.\_catalog_majors accepts any int()-parseable stem (a stray 'catalogs/05.toml' yields major 5), then build_package_repository loads 'catalogs/5.toml', which does not exist, producing a misleading PC-CATALOG-INVALID 'cannot read catalog source' finding. projection.\_catalog_sources applies the canonical check 'str(major) == path.stem' (projection.py:89) and silently ignores the same file. The two duplicated discovery routines disagree on what counts as a catalog source, so validate-packages and sync-payload-projection see different catalog sets for non-canonical filenames.
- Fix: Add the canonical-stem guard to cli.\_catalog_majors (after 'major = int(path.stem)', require 'str(major) == path.stem' before appending), or extract one shared discovery helper (e.g. in catalog.py) returning (major, path) pairs and call it from both cli.\_catalog_majors and projection.\_catalog_sources.
- Verification: Add a test creating catalogs/05.toml beside catalogs/5.toml and assert validate-packages reports no PC-CATALOG-INVALID for the phantom 5.toml; run uv run pytest tests/package_contract/test_cli.py tests/package_contract/test_projection.py
- Dependencies: none
- Effort: S

**F-086 — Pin actions/checkout and actions/setup-python by commit SHA in rendered consumer workflows, matching the setup-uv pin**

- Category: Security · Severity: Low · Confidence: High
- Location: src/project_standards/payloads/python-tooling/1.1/providers/python_tooling.py:268-272, src/project_standards/payloads/cli-documentation/1.1/providers/cli_documentation.py:48,60, src/project_standards/payloads/python-tooling/1.1/resources/check.yml:15-19
- Evidence: `src/project_standards/payloads/python-tooling/1.1/providers/python_tooling.py:268:        "      - uses: actions/checkout@v7",`
- Problem: The rendered consumer CI workflows pin astral-sh/setup-uv to a full commit SHA (line 272: `astral-sh/setup-uv@11f9893b...# v8.3.2`) but reference actions/checkout@v7 and actions/setup-python@v6 by mutable tags (cli_documentation.py additionally uses the setup-uv SHA without a version comment at line 60). Mixed pinning is inconsistent, and mutable tags in workflows this repo installs into every consumer mean a compromised or force-moved upstream tag executes in all consumer CI — the exact exposure the SHA pin on setup-uv was chosen to avoid. This is consumer-side supply-chain surface, where the stated security bar is highest.
- Fix: In the next python-tooling and cli-documentation payload versions: replace `actions/checkout@v7` and `actions/setup-python@v6` with full 40-char commit SHAs plus trailing `# vN` comments in python_tooling.py_workflow, cli_documentation.py_workflow, and the static resources/check.yml (which must stay byte-identical to the default \_workflow rendering — the code asserts this at python_tooling.py:510-513, so regenerate check.yml from the new renderer and update its digest); add the `# v8.3.2` comment to the setup-uv line in cli_documentation.py.
- Verification: grep -n 'uses:' over the new payload versions shows only SHA-pinned actions with version comments; the python-tooling default-config render test (static check-workflow-source equality) passes with the regenerated check.yml.
- Dependencies: none
- Effort: S

**F-087 — Rename used underscore-prefixed provider parameters (\_resources) where the body actually reads them**

- Category: Convention · Severity: Low · Confidence: High
- Location: src/project_standards/payloads/cli-documentation/1.1/providers/cli_documentation.py:112,139; src/project_standards/payloads/markdown-frontmatter/1.2/providers/frontmatter.py:101,128
- Evidence: `src/project_standards/payloads/cli-documentation/1.1/providers/cli_documentation.py:139:    legacy = _resources.get("legacy-workflow")`
- Problem: run_verify in cli_documentation.py declares its second parameter `_resources` (underscore = unused by project-wide convention, as every other provider uses it) but reads it at line 139 for the legacy-workflow comparison; frontmatter.py run_fix does the same (`_resources` declared at line 101, used at line 128 via_bundled_schema(\_resources)). The misleading name invites a future maintainer to treat the resource map as droppable (e.g. declaring `resources = []` for the provider in payload.toml), which would silently break legacy-compatibility verification and id-only fix planning.
- Fix: In the next cli-documentation and markdown-frontmatter payload versions, rename the parameter to `resources` in cli_documentation.py run_verify and frontmatter.py run_fix (update the two internal references); no behavior change. Update the provider-code digests in the new payload.toml files.
- Verification: grep -n '\_resources' in both new provider files shows underscore names only on providers that never read the map; `uv run ruff check` and `uv run basedpyright` stay clean.
- Dependencies: none
- Effort: S

**F-088 — Close the exists-check/os.replace TOCTOU in \_safe_atomic_write**

- Category: Correctness · Severity: Low · Confidence: High
- Location: src/project_standards/specs/cli.py:583-585, src/project_standards/specs/cli.py:609
- Evidence:

```text
src/project_standards/specs/cli.py:583:    overwritten = target.is_file()
src/project_standards/specs/cli.py:584:    if overwritten and not force:
src/project_standards/specs/cli.py:585:        raise NewError("exists", f"refusing to overwrite existing file: {target} (use --force)")
```

- Problem: The no-clobber guard checks target.is_file() and later os.replace()s unconditionally (line 609). In legacy (uninitialized control-plane) mode selected_command takes no lock at all (command_resolution.py:344-352 yields before control_plane_lock), so two concurrent `spec new PATH` invocations both pass the not-exists check and the loser's file is silently replaced — violating the 'refusing to overwrite existing file' contract the scope's ID-allocation-race concern is about.
- Fix: In \_safe_atomic_write, split the final rename: when `not overwritten and not force`, use `os.link(tmp, target)` inside the existing try, catch FileExistsError and raise NewError('exists', ...) after unlinking tmp, then `tmp.unlink(missing_ok=True)` on success; keep os.replace(tmp, target) for the force/overwrite path. (os.link fails atomically with EEXIST if a concurrent writer won.)
- Verification: uv run pytest tests/test_spec_new_cli.py; manual: pre-create target between the check and rename in a unit test by monkeypatching os.replace's precondition, or simply assert os.link path raises NewError('exists') when target appears after the initial check.
- Dependencies: none
- Effort: S

**F-089 — Correct SV-ID-UNDECLARED message: condition is undeclared-in-Appendix-A, not non-canonical**

- Category: Docs · Severity: Low · Confidence: High
- Location: src/project_standards/specs/commands/validate.py:149-159
- Evidence: `src/project_standards/specs/commands/validate.py:153:                    f"prefix {pfx}- is not a canonical spec-local prefix. If it names an "`
- Problem: The guard is `pfx not in doc.declared_prefixes` (the document's own Appendix A rows), not membership in the canonical registry. A spec that uses a fully canonical prefix (e.g. FR-) but whose Appendix A table dropped that row gets the finding "prefix FR- is not a canonical spec-local prefix", which is factually wrong and sends the author toward reference_prefixes instead of restoring the Appendix A row.
- Fix: Change the message to state the actual condition, e.g. f"prefix {pfx}- is not declared in this spec's Appendix A. If it names an external namespace (backlog, tickets, another spec), add it to spec.reference_prefixes; otherwise declare it in Appendix A." Update any test asserting the old wording (grep tests/ for 'canonical spec-local prefix').
- Verification: grep -rn 'canonical spec-local prefix' tests/ src/ then uv run pytest tests/test_spec_validate.py
- Dependencies: none
- Effort: S

**F-090 — Deduplicate legacy vs selected spec-id resolution in cli.py**

- Category: Structure · Severity: Low · Confidence: High
- Location: src/project_standards/specs/cli.py:445-504 and 507-536
- Evidence:

```text
src/project_standards/specs/cli.py:519:    if args.spec_id is not None:
src/project_standards/specs/cli.py:520:        if not re.match(SPEC_ID_PATTERN, args.spec_id):
src/project_standards/specs/cli.py:521:            raise NewError("bad_id", f"--id {args.spec_id!r} does not match {SPEC_ID_PATTERN}")
```

- Problem: \_resolve_new_options (445-485) and_selected_new_options (507-536) contain the identical field-check loop and the identical --id validation / collision / mint_spec_id block, and collect_existing_spec_ids (config.py) is re-implemented as_selected_existing_ids (488-504). Any future change to ID grammar or collision policy must be made in two or three places; additionally \_run_new's legacy self-validation reloads the config a second time at line 798 (`load_spec_config(args.config)`) outside the NewError wrapper, so a ConfigError there would bypass the I7 JSON envelope.
- Fix: Extract a helper `_resolve_spec_options(args, existing_ids: set[str]) -> NewOptions` containing the field-check loop and the --id/mint logic; have \_resolve_new_options and_selected_new_options call it with their respective existing_ids sources. Make_resolve_new_options also return the loaded SpecConfig and reuse it at line 798 instead of calling load_spec_config again.
- Verification: uv run pytest tests/test_spec_new.py tests/test_spec_new_cli.py tests/test_spec_new_discovery.py tests/test_spec_selected_routing.py
- Dependencies: none
- Effort: M

**F-091 — Delete unreachable selected-write branch at end of \_run_new**

- Category: Structure · Severity: Low · Confidence: High
- Location: src/project_standards/specs/cli.py:830-831
- Evidence:

```text
src/project_standards/specs/cli.py:830:        if runtime.payload is not None:
src/project_standards/specs/cli.py:831:            return _write_selected_new(args, opts, runtime)
```

- Problem: This branch is dead: when runtime.payload is not None and --stdout is absent, \_run_new already returned at lines 761-762 (`if not args.stdout: return _write_selected_new(...)`), and every --stdout invocation returns inside the `if args.stdout:` block at lines 812-828. Control only reaches line 830 with payload None, so the guard can never fire; it misleads readers into thinking there is a second selected write path.
- Fix: Delete lines 830-831, leaving `return _write_new_file(args, opts, text)` as the sole tail of the try block.
- Verification: uv run pytest tests/test_spec_new_cli.py tests/test_spec_selected_routing.py && uv run coverage run -m pytest tests/test_spec_new_cli.py (branch shows 0 hits today)
- Dependencies: none
- Effort: S

**F-092 — Fix misleading \_str_list error message for reference_prefixes**

- Category: Correctness · Severity: Low · Confidence: High
- Location: src/project_standards/specs/config.py:32-41,107-109
- Evidence: `src/project_standards/specs/config.py:41:    raise ConfigError("spec.include/spec.exclude must be strings or lists of strings")`
- Problem: \_str_list is also used for spec.reference_prefixes (line 107-109), so a consumer who writes `reference_prefixes: [1, 2]` gets the exit-2 error "spec.include/spec.exclude must be strings or lists of strings", pointing them at the wrong config keys.
- Fix: Add a `field: str` parameter to \_str_list and raise ConfigError(f"spec.{field} must be a string or a list of strings"); pass "include", "exclude", and "reference_prefixes" at the three call sites (lines 105-108).
- Verification: uv run python -c "from pathlib import Path; from project_standards.specs.config import load_spec_config; import tempfile,os; p=Path(tempfile.mkdtemp())/'c.yml'; p.write_text('spec:\n reference_prefixes: [1]\n'); load_spec_config(p)" — error message must name reference_prefixes. Then uv run pytest tests/test_spec_config.py
- Dependencies: none
- Effort: S

**F-093 — Handle frontmatter fence terminating at EOF without trailing newline**

- Category: Correctness · Severity: Low · Confidence: High
- Location: src/project_standards/specs/registry.py:68-73
- Evidence: `src/project_standards/specs/registry.py:72:    end = text.index("\n---\n", 4)`
- Problem: split_front_matter only recognizes a closing fence followed by a newline. A spec whose final line is the closing `---` with no trailing newline (files saved by editors that don't enforce a final newline) raises ValueError from .index — surfaced as "malformed frontmatter fence: substring not found", an unhelpful message for a document GitHub renders as valid frontmatter.
- Fix: In split_front_matter, wrap the index call: `try: end = text.index("\n---\n", 4)` / `except ValueError:` — if `text.endswith("\n---")` return `(text[4:-4], "")`, else `raise ValueError("unterminated frontmatter fence")` (also improving the error text).
- Verification: uv run python -c "from project_standards.specs.registry import split_front_matter; fm,b=split_front_matter('---\na: b\n---'); assert fm=='a: b' and b==''" then uv run pytest tests/test_spec_registry.py tests/test_spec_document.py
- Dependencies: none
- Effort: S

**F-094 — Include H1 (and H5/H6) headings in anchor-slug collection**

- Category: Correctness · Severity: Low · Confidence: High
- Location: src/project_standards/specs/registry.py:80-87, src/project_standards/specs/document.py:57-71,86
- Evidence: `src/project_standards/specs/registry.py:84:        if m := re.match(r"^(#{2,4})\s+(.*)$", line):`
- Problem: headings() only collects levels 2-4, and \_anchor_slugs derives valid anchors from it, so a link to the document's own H1 anchor — which GitHub does generate — is flagged as dead. Verified: adding `[top](#project--feature-name--specification-light)` to an otherwise-valid light spec yields a spurious SV-ANCHOR error, failing validate on a link that works on GitHub. H5/H6 anchors are likewise rejected.
- Fix: Add a level range to registry.headings (e.g. `def headings(body, *, pattern=r"^(#{2,4})\s+(.*)$")` or a second function `all_headings` using `#{1,6}`), keep section parsing on 2-4, and in document.parse_document build slugs via `_anchor_slugs(all_headings(body))` while sections continue to use the 2-4 scan.
- Verification: uv run python: parse the light template with spec_id filled plus a `[top](#project--feature-name--specification-light)` link; validate_document must return no SV-ANCHOR (currently returns one). Then uv run pytest tests/test_spec_validate.py tests/test_spec_document.py
- Dependencies: Interacts with the fence-masking change (both touch headings()); apply after it if both are taken.
- Effort: S

**F-095 — Require markdown string when selected extract provider reports found**

- Category: Correctness · Severity: Low · Confidence: High
- Location: src/project_standards/specs/cli.py:343-364
- Evidence: `src/project_standards/specs/cli.py:348:            or not (isinstance(markdown, str) or markdown is None)`
- Problem: The boundary validation of provider-returned extract content accepts found=True together with markdown=None; the non-JSON output path then executes `print(payload["markdown"])` and writes the literal string "None" to stdout with exit 0 — corrupt output from a malformed provider response that the validation was meant to fail closed on.
- Fix: After the existing isinstance checks, add: `if found and not isinstance(markdown, str): raise ConfigError("selected extract provider returned invalid content")`.
- Verification: uv run pytest tests/test_spec_selected_routing.py (add a case with structured_output {'found': True, 'markdown': None, ...} asserting ConfigError/exit 2)
- Dependencies: none
- Effort: S

**F-096 — Align executable bit on versioned payload scripts across families**

- Category: Structure · Severity: Low · Confidence: High
- Location: standards/agent-handoff/versions/1.1/hooks/session-start/session_start.py:1 (git mode), standards/markdown-frontmatter/versions/1.2/skills/markdown-frontmatter/scripts/new-doc-id:1 (git mode)
- Evidence: `git ls-files -s output: '100644 41dcb41... standards/agent-handoff/versions/1.1/hooks/session-start/session_start.py' vs '100755 8d71e52... standards/markdown-frontmatter/versions/1.2/skills/markdown-frontmatter/scripts/new-doc-id'`
- Problem: The two immutable payloads treat source-tree executable bits inconsistently: markdown-frontmatter's versioned new-doc-id is committed 100755 while agent-handoff's versioned session_start.py is committed 100644, even though both declare mode = "0755" in their payload [[artifacts]] entries (and the mutable family copy of session_start.py is 100755). There is no runtime impact today because reconcile applies the declared mode from the lock, but any future flow that copies payload files preserving tree mode (e.g., executing directly from an extracted wheel) would get a non-executable hook, and the asymmetry invites confusion about whether tree mode is contract-relevant.
- Fix: Do not chmod the released 1.1 file in place without first confirming `uv run project-standards packages check-release --baseline v5.0.1 --json` still reports ok (a git mode change alters the tree even though sha256 payload digests cover bytes only). Preferred: when the next agent-handoff payload version is cut (see the fence-awareness finding), commit versions/<next>/hooks/session-start/session_start.py with mode 100755, and document in standards/standard-bundle-authoring (next version) whether versioned payload scripts carry the executable bit.
- Verification: git ls-files -s standards/_/versions/_/hooks/**/_.py standards/_/versions/\*/skills/**/scripts/\* shows a consistent policy; uv run project-standards packages check-release --baseline <current release> --json reports ok with empty findings.
- Dependencies: none
- Effort: S

**F-097 — Add -> None annotations to 42 unannotated test functions**

- Category: Convention · Severity: Low · Confidence: High
- Location: tests/test_format_frontmatter.py (32 functions), tests/test_id_format.py:6-27 (5), tests/test_precommit_hooks.py:10-32 (3), tests/test_spec_document.py:71,92 (2)
- Evidence: `tests/test_id_format.py:6: def test_slugify_basic():`
- Problem: tests/README.md:179 states the suite's convention: 'annotate every fixture and test signature (`-> None`, typed params)'. 42 test functions across four modules (test_format_frontmatter.py 32, test_id_format.py 5, test_precommit_hooks.py 3, test_spec_document.py 2) omit the return annotation; basedpyright strict infers None so the gate stays green and the drift is invisible. The same four files (plus tests/test_validate_references.py, tests/agent_handoff/test_config.py, tests/agent_handoff/test_model.py) also lack the `from __future__ import annotations` header the rest of the suite carries.
- Fix: Append `-> None` to every `def test_...():` in the four files (find them with `grep -rn '^def test_.*():$' tests --include='*.py'`), and add `from __future__ import annotations` as the first import in tests/test_precommit_hooks.py, tests/test_validate_references.py, tests/test_id_format.py, tests/test_format_frontmatter.py, tests/agent_handoff/test_config.py, tests/agent_handoff/test_model.py. Also drop the redundant filename comment `# tests/test_precommit_hooks.py` at tests/test_precommit_hooks.py:1.
- Verification: grep -rn '^def test*.*():$' tests --include='\_.py' returns nothing; uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run pytest tests/test_format_frontmatter.py tests/test_id_format.py tests/test_precommit_hooks.py tests/test_spec_document.py -q
- Dependencies: none
- Effort: S

**F-098 — Anchor cwd-relative fixture paths to Path(**file**) in ten test modules**

- Category: Structure · Severity: Low · Confidence: High
- Location: tests/test_usage_doc_inventory.py:16, tests/test_installed_wrappers.py:27, tests/control_plane/helpers.py:9, tests/control_plane/test_bootstrap.py:21, tests/control_plane/test_distribution.py:20, tests/control_plane/test_cli.py:22, tests/control_plane/test_end_to_end.py:19, tests/control_plane/test_migration.py:63-64, tests/test_frontmatter_unified_config.py:51, tests/package_contract/test_projection.py:162, tests/package_contract/test_public_provider_routing.py:31, tests/agent_handoff/test_selected_routing.py:32
- Evidence: `tests/test_usage_doc_inventory.py:16: _USAGE = Path("docs/usage.md").read_text(encoding="utf-8")`
- Problem: These modules resolve fixture/repo paths relative to the process cwd (worst case at module import: test_usage_doc_inventory.py reads docs/usage.md and test_installed_wrappers.py reads pyproject.toml at collection time), so invoking pytest from any directory other than the repo root fails collection or FileNotFoundErrors mid-test. The rest of the suite consistently anchors with Path(**file**).resolve().parents[N] (e.g. package_contract/helpers.py, package_compatibility/matrix.py), so this is silent inconsistency waiting to bite IDE runners or `cd tests && pytest` invocations.
- Fix: In each listed module, define \_ROOT = Path(**file**).resolve().parents[N] (N=1 for tests/, 2 for tests/<pkg>/) and prefix every bare Path("tests/..."), Path("src/..."), Path("pyproject.toml"), Path("docs/usage.md"), Path("standards") and Path.cwd() usage with it (tests/test_installed_wrappers.py:59,150,209,211 uses Path.cwd() as the repo root — replace with_ROOT). Do not touch tests/test_standards_graph_model.py:82-83, where relative Paths are pure values never opened.
- Verification: cd /tmp && uv run --project /home/chris/projects/project-standards pytest /home/chris/projects/project-standards/tests/test_usage_doc_inventory.py /home/chris/projects/project-standards/tests/control_plane/test_bootstrap.py -q (collection and tests pass from a foreign cwd)
- Dependencies: none
- Effort: S

**F-099 — Isolate git-spawning tests from the developer's global git config**

- Category: Testing · Severity: Low · Confidence: High
- Location: tests/agent_handoff/test_hook.py:153-176, tests/package_contract/test_release.py:270-297, tests/package_contract/test_cli.py:140-157
- Evidence: `tests/agent_handoff/test_hook.py:163:            ["git", "commit", "--no-verify", "-q", "-m", f"commit-{index}"],`
- Problem: test_context_limits_commits_and_status_lines runs seven `git commit` subprocesses that inherit ~/.gitconfig: on any machine with global `commit.gpgsign = true` and an unavailable or passphrase-protected key, the commits fail and the test errors — violating the README:31 'no real home directory' hermeticity goal. test_release.py and test_cli.py already isolate hooks (`-c core.hooksPath=/dev/null`) and tag signing (`-c tag.gpgSign=false`) but also omit `commit.gpgsign=false`, so the mitigation is ad hoc and incomplete. It passes today only because this workstation's signing key has no passphrase and CI runners have no global config.
- Fix: In tests/agent_handoff/test_hook.py test_context_limits_commits_and_status_lines, pass env to every git subprocess.run with {\*\*os.environ, 'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_NOSYSTEM': '1'} (keeping the existing per-repo user.name/user.email config), or add '-c', 'commit.gpgsign=false' to the commit invocations. Apply the same GIT_CONFIG_GLOBAL/GIT_CONFIG_NOSYSTEM env (replacing the piecemeal -c flags) to the git commands in tests/package_contract/test_release.py:275-297 and tests/package_contract/test_cli.py:138-157.
- Verification: git config --global commit.gpgsign true (temporarily, or run with HOME pointed at a dir whose .gitconfig sets commit.gpgsign=true and no key) then uv run pytest tests/agent_handoff/test_hook.py::test_context_limits_commits_and_status_lines tests/package_contract/test_release.py -q; restore config
- Dependencies: none
- Effort: S

**F-100 — Wire PROJECT_STANDARDS_COMPATIBILITY_WHEEL into the CI compatibility phase**

- Category: Performance · Severity: Low · Confidence: High
- Location: tests/package_compatibility/conftest.py:19-58, .github/workflows/check.yml:64
- Evidence: `tests/package_compatibility/conftest.py:19: _PREBUILT_WHEEL = "PROJECT_STANDARDS_COMPATIBILITY_WHEEL"`
- Problem: The wheel_payload_distribution fixture supports reusing a pre-built wheel via the PROJECT_STANDARDS_COMPATIBILITY_WHEEL env var, but nothing anywhere (CI, docs, scripts) ever sets it — the escape hatch is dead code. Consequently the CI compatibility step (`uv run pytest -m compatibility -n 4 --dist load`) makes each of the 4 xdist worker sessions rebuild the wheel with `uv build --offline` (session-scoped fixtures are per-worker), i.e. 4 redundant builds per run, even though the same job already built the candidate wheel into dist/ two steps earlier — and the wheel actually exercised by the compatibility rows is a fresh rebuild rather than the exact candidate artifact the rest of the gate verified.
- Fix: In .github/workflows/check.yml, before the 'uv run pytest -m compatibility ...' step add a step that resolves the built wheel path and exports it, e.g. `echo "PROJECT_STANDARDS_COMPATIBILITY_WHEEL=$(ls ${{ github.workspace }}/dist/project_standards-*.whl)" >> "$GITHUB_ENV"` (after the existing wheel-build step). No test code changes needed — conftest.py already validates and uses the path.
- Verification: PROJECT_STANDARDS_COMPATIBILITY_WHEEL=$(ls dist/project_standards-\*.whl) uv run pytest -m compatibility -n 4 --dist load -q passes locally after `uv build --wheel --out-dir dist`; CI compatibility step duration drops by the wheel-build time per worker
- Dependencies: none
- Effort: S

## 6. Remediation Plan

Work the phases top to bottom; inside a phase, order is free unless a Dependencies field says otherwise. Detail lives in each finding.

**Phase 1 — High-severity fixes editable in place** (no payload cut required; each standalone)

- F-001, F-002, F-003, F-004, F-005, F-008, F-009

**Phase 2 — the `agent-handoff` 1.2 payload cut** (one coordinated batch: author the new payload version once, fold every fix in, wire family `standard.toml` + `catalogs/5.toml`, run `sync-payload-projection`; note this addition is consumer-visible, so the next tool release becomes at least MINOR — see Open Question 1)

- F-006, F-007 (High) · F-010, F-024, F-027 (Medium) — the source-module mirrors named inside F-007 and F-010 can land immediately with Phase 1; only the payload copies wait for the 1.2 cut.

**Phase 3 — remaining Medium**

- F-011, F-012, F-013, F-014, F-015, F-016, F-017, F-018, F-019, F-020, F-021, F-022, F-023, F-025, F-026, F-028

**Phase 4 — Low, grouped by area for efficient batching**

- Control plane: F-047, F-048, F-049, F-050, F-051, F-052, F-053, F-054, F-055, F-056, F-057, F-058, F-059, F-060, F-061, F-062
- Package contract: F-079, F-080, F-081, F-082, F-083, F-084, F-085
- Frontmatter tools: F-070, F-071, F-072, F-073, F-074, F-075, F-076, F-077, F-078
- CLI / adopt / graph: F-040, F-041, F-042, F-043, F-044, F-045, F-046
- Agent handoff: F-029, F-030, F-031, F-032, F-033
- Specs: F-088, F-089, F-090, F-091, F-092, F-093, F-094, F-095
- CI and scripts: F-034, F-035, F-036, F-037, F-038, F-039
- Payload/standards content (mind immutability — several imply future payload versions): F-086, F-087, F-096
- Tests: F-097, F-098, F-099, F-100
- Docs: F-063, F-064, F-065, F-066, F-067, F-068, F-069

## 7. Open Questions

1. **When to cut `agent-handoff` 1.2 relative to the prepared 5.0.2 release.** 5.0.2 is already prepared on `testing` as a PATCH. Adding the 1.2 payload to Catalog 5 is consumer-visible, so the release carrying it must be at least MINOR (5.1.0). Options: (a) publish 5.0.2 as prepared, then follow with 5.1.0 carrying the payload fixes — preserves the already-classified PATCH but delays the fix for a consumer-crashing hook; (b) fold everything into a single 5.1.0 and abandon the 5.0.2 tag — fewer releases for consumers to absorb, but discards prepared release work and re-opens its classification. Both are defensible; the choice is release-cadence policy, which is the owner's.
2. **Supported Python floor for consumer-side payload code.** The repo itself requires Python ≥ 3.14, but hooks and providers shipped in payloads execute under whatever interpreter the consumer repo has (the SessionStart hook crash in F-006 exists precisely because repo-level syntax policy leaked into consumer-side code). Decide the consumer-side floor (e.g. 3.11+) and encode it: a stated rule in the bundle-authoring standard, plus a CI `py_compile`/matrix check for every file under `payloads/**/hooks/` and `payloads/**/providers/`. Tradeoff: a low floor constrains syntax available to payload authors; a high floor knowingly breaks consumers on older interpreters — but either should be an explicit contract, not an accident.
3. **Whether to normatively unify the CLI exit-code contract.** F-011, F-057, and F-077 each show a tool deviating from the documented 0 / 1 / 2(/3) convention in a different direction. Fixing them piecemeal restores local consistency, but exit codes are consumer-observable behavior: under the "previously-passing consumer" rule in `meta/versioning.md`, tightening a code from 0→1 in a released tool can newly fail a consumer's CI and would need to ride a MAJOR. A written per-tool exit-code table (in `docs/usage.md` or the bundle-authoring standard) would decide which deviations are bugs to fix now versus documented behavior frozen until v6. Needs an owner call on where that line sits.
