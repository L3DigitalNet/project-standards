# Project Standards 5.1 Review Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILLS: Use `superpowers:test-driven-development` for every behavior change, `superpowers:verification-before-completion` before every commit, and either `superpowers:subagent-driven-development` or `superpowers:executing-plans` to execute the tasks in order.

**Goal:** Prepare Project Standards 5.1.0 with every accepted Fable 5 review correction, a Python 3.14-or-newer consumer floor, and no unrelated feature, cleanup, or deferred work.

**Architecture:** Preserve the Catalog 5 architecture and correct only the verified defect sites. Add lock schema 1.1 for create-only absences, keep shared helpers private and limited to repeated reviewed invariants, and cut exactly five immutable payload versions when released bytes or managed consumer artifacts must change. Each task follows RED-GREEN-REFACTOR and proves its diff against a finding-specific allowlist.

**Tech Stack:** Python 3.14, uv, Pydantic 2, `jsonschema`, PyYAML, pytest, coverage, Ruff, BasedPyright strict, pip-audit, GitHub Actions YAML, TOML/JSON/JSONC/Markdown, Prettier, and markdownlint.

---

## Sources of truth

- Approved design: `docs/specs/archive/2026-07-19-project-standards-review-remediation-design.md` at review-fix commit `0c48c2c`.
- Source review: `docs/fable-review/2026-07-19-project-standards-review.md`.
- Independent design review: `docs/reviews/2026-07-19-review-remediation-design-review.md` (user-owned evidence; read-only during implementation).
- Published baseline: signed `v5.0.2` from release commit `c731955`.
- Maintained contracts: `docs/specs/2026-07-10-consumer-standards-control-plane-spec.md`, `docs/specs/2026-07-10-standard-bundle-authoring-v2-spec.md`, `docs/specs/2026-07-09-agent-handoff-standard-package.md`, and `meta/versioning.md`.
- Repository rules: `AGENTS.md` and `docs/handoff/conventions.md`.

The review proposes remedies, but the approved design is authoritative where it narrows or rejects them.

## Non-negotiable scope contract

- Project Standards 5.0.2 is already published. This plan prepares 5.1.0 only; it does not create, move, or publish tags or releases.
- Every consumer surface requires a shebang-resolved Python 3.14 or newer. Do not add Python 3.13 compatibility, future-annotations imports, or a lower-runtime test lane.
- Implement corrections only. Do not add commands, options, workflows, packages, public APIs, generalized infrastructure, queue work, or opportunistic cleanup.
- No accepted finding is deferred. The four final no-change findings are closed decisions and receive no code, comment, test, documentation, or follow-up queue entry.
- Released payload directories remain byte- and mode-identical. New payloads are exactly:
  1. `agent-handoff@1.2`
  2. `project-spec@1.2`
  3. `markdown-frontmatter@1.3`
  4. `cli-documentation@1.2`
  5. `standard-bundle-authoring@2.2`

- Do not cut Python Tooling or Markdown Tooling payloads. F-100 changes only this repository's consumer-owned `.github/workflows/check.yml`.
- Do not modify or add `docs/reviews/**` or ignored `.superpowers/sdd/**`, and do not recreate retired documentation trees.
- Add no new test framework or dependency. Parser and round-trip invariants use deterministic exhaustive parameterization over their finite edge sets; do not add a property-testing library solely for this correction train.
- A helper is permitted only where the approved design names repeated correction sites. Keep it private and limited to those sites.

## Required protocol for every task

Before RED:

```bash
git status --short
task_base="$(git rev-parse HEAD)"
```

Confirm the tracked tree is clean and that any untracked `docs/reviews/` evidence is the pre-existing user-owned artifact. Record the task's finding IDs and the file allowlist printed below. Stop if a proposed edit does not directly correct those findings or a named deterministic payload consequence.

For each task:

1. Add the exact regression named by the task and run the focused command to observe the expected failure.
2. Make the smallest allowlisted correction that turns the focused gate green.
3. Refactor only when the task explicitly authorizes a private shared primitive; preserve behavior outside the regression.
4. Run Ruff format/check and BasedPyright for every touched Python surface, plus the task's focused gate.
5. Run package generation/reconstruction checks only for tasks that change a payload, catalog, schema, projection, lock, or managed dogfood output.
6. End with:

   ```bash
   git diff --name-status "$task_base"
   git diff --check "$task_base"
   ```

   Every changed path must match the task allowlist. Remove any unrelated edit; do not justify it after the fact.

7. Commit the narrow green task with the exact commit subject listed. Do not push during this plan.

Documentation-only tasks use a failing pre-edit inventory assertion in place of a pytest RED when no executable behavior exists. Payload tasks additionally prove all released version directories are unchanged before committing.

## Finding-to-task ledger

| Task | Findings | Correction boundary |
| --- | --- | --- |
| 1 | F-001 | Normalize null Claude hook containers only. |
| 2 | F-002 | Restore documented Project Spec reusable-workflow inputs and cut Project Spec 1.2. |
| 3-4 | F-003 | Add lock 1.1 absence records, then their lifecycle and conservative 1.0 inference. |
| 5 | F-004, F-057 | Stable `CP-BUSY` across initialized and render paths. |
| 6 | F-005 | Reject orphan bounded-block migration without whole-file removal. |
| 7 | F-008 | Select only real Markdown headings. |
| 8 | F-009 | One fence-masked Project Spec structural view. |
| 9 | F-007, F-030, F-031 | Normalize Agent Handoff links once and report the offending target. |
| 10 | F-010 | Remove unenforced Agent Handoff policy knobs. |
| 11 | F-011 | Successful legacy inventory returns zero while retaining findings. |
| 12 | F-019 | String-aware mutable-runtime JSONC sanitizer. |
| 13 | F-024 | Mutable Agent Handoff JSONC inspection parity. |
| 14 | F-027 | Fence-aware payload shape scans and accumulated Agent Handoff 1.2 provider mirrors. |
| 15 | F-029, F-033 | Restore supported `--view` parsing and guard missing upgrade resources. |
| 16 | F-032 | Preserve existing file modes in legacy Agent Handoff writes. |
| 14 and 17 | F-006, F-096 | Complete the Python 3.14 and mode-contract slices atomically in each affected payload. |
| 17 | F-069 | Name Standard Bundle Authoring 2.2 only after its payload exists. |
| 18 | F-012, F-041 | Bound v5 adoption activation and make installed-distribution fallback visible. |
| 19 | F-013, F-053 | Close partial staging handles and remove the five unused staging arguments. |
| 20 | F-014 | Validate provider finding fields at the runtime boundary. |
| 21 | F-015 | Move installed-distribution discovery inside all public error boundaries. |
| 22A | F-016 | Render canonically parseable migration TOML. |
| 22B | F-017 | Reject unobserved migration claim targets. |
| 23 | F-018 | Correct the internal-payload PATCH policy table. |
| 24 | F-021 | Preserve anchor/alias frontmatter with a warning and exit zero. |
| 25A | F-022 | Splice only the VS Code path-colors value. |
| 25B | F-078 | Rewrite only the frontmatter include block. |
| 26 | F-023 | Resolve local option-schema references from the root schema. |
| 27 | F-025, F-034 | Add stable validator aliases and caller permissions in Markdown Frontmatter 1.3. |
| 28 | F-026 | Derive spec lock and JSON modes from real parsers. |
| 29 | F-036, F-038 | Make the validate-id zipapp fail loud and prefer its sibling source tree. |
| 30 | F-037 | Pass the baseline ref through workflow environment data. |
| 31 | F-028, F-035, F-039 | Correct test and CI intent documentation without workflow redesign. |
| 32 | F-040, F-055, F-088 | One bounded descriptor-safe, no-clobber filesystem correction. |
| 33 | F-042, F-043, F-044, F-045 | Tighten existing manifest and registry ingestion boundaries. |
| 34 | F-046 | Emit one graph finding for a mislinked manifest. |
| 35 | F-047 | Consolidate exactly six typed digest wrappers. |
| 36 | F-048, F-049, F-051 | Correct state races, undeclared modes, and missing-target facts. |
| 37 | F-050, F-058, F-059, F-060, F-062 | Typed resolution failures and truthful JSON envelopes. |
| 38 | F-052, F-054 | Treat only LF and CRLF as newline boundaries. |
| 39 | F-056, F-061 | Bound reserved temporary cleanup and report recovery's applied prefix. |
| 40 | F-063, F-064, F-065, F-066, F-067 | Correct maintained navigation, release history, usage, and readiness text. |
| 41 | F-068 | Parse the bug-index frontmatter subset without leaking quote syntax. |
| 42 | F-070, F-071, F-072, F-073 | Correct frontmatter inference, disabled-reference silence, and scope matching. |
| 43 | F-074, F-075, F-076 | Lazy schema use, legacy-writer quarantine, and empty-block diagnostics. |
| 44 | F-079, F-085 | Canonical catalog discovery with one repository load. |
| 45 | F-080, F-081, F-082, F-083 | Correct package-contract invariants, roles, and bounded discovery. |
| 46 | F-084 | Classify catalog output failures with a private typed error. |
| 47 | F-086 | Add only the missing setup-uv version comment in CLI Documentation 1.2. |
| 48 | F-089, F-092, F-093, F-094 | Correct spec diagnostics and reuse structural fence masking. |
| 49 | F-090, F-091 | Share spec-new option resolution and remove the unreachable selected tail. |
| 50 | F-097 | Add exactly 42 missing test return annotations. |
| 51 | F-098 | Anchor repository fixtures in all 12 verified modules. |
| 52 | F-099 | Make Git-spawning tests hermetic under hostile global configuration. |
| 53 | F-100 | Feed the exact prebuilt wheel into repo-local compatibility CI. |
| 54 | None | Synchronize 5.1.0 release metadata and run the complete retained gate. |
| No change | F-020, F-077, F-087, F-095 | Closed decisions; no implementation or queue item. |

Every F-001 through F-100 appears once in this ledger. Task 54 is deterministic integration, not a new finding or feature.

---

## Phase 1: Core safety and Project Spec parsing

### Task 1: Normalize null Claude hook containers

**Findings:** F-001

**Files:**

- Modify: `src/project_standards/agent_handoff/integrations/claude.py`
- Modify: `tests/agent_handoff/test_claude.py`

- [ ] **RED:** Parameterize `test_merge_claude_accepts_null_hook_containers` over `{"hooks": null}` and `{"hooks": {"SessionStart": null}}`; assert a controlled merge rather than `AttributeError`.
- [ ] Run `uv run pytest tests/agent_handoff/test_claude.py -k null -q` and confirm the current implementation fails.
- [ ] **GREEN:** Normalize only null `hooks` and `SessionStart` containers to the existing empty-container semantics. Continue rejecting non-null values of the wrong type.
- [ ] Run `uv run pytest tests/agent_handoff/test_claude.py -q`, touched-file Ruff checks, and BasedPyright.
- [ ] **Scope audit:** Diff must contain only the two files above; run the required end-of-task commands.
- [ ] Commit: `fix(agent-handoff): normalize null Claude hooks`

### Task 2: Restore reusable Project Spec workflow inputs

**Findings:** F-002

**Files:**

- Modify: `.github/workflows/validate-specs.yml`
- Create: `standards/project-spec/versions/1.2/**`
- Modify: `standards/project-spec/standard.toml`
- Modify only as required by the new version: `standards/project-spec/README.md`, `standards/project-spec/adopt.md`, `standards/project-spec/agent-summary.md`
- Generate: `src/project_standards/payloads/project-spec/1.2/**`
- Generate/update: `catalogs/5.toml`, `standards/catalog.md`, `.standards/catalog.toml`, `.standards/lock.toml`
- Modify: `tests/test_validate_specs_workflow.py`
- Modify: `tests/package_contract/test_project_spec_reconstruction.py`
- Modify only deterministic compatibility expectations: `tests/package_compatibility/matrix.py`

- [ ] **RED:** Update `test_consumer_install_treats_the_requested_ref_as_data`, `test_direct_events_use_published_ref_and_run_strict_lint`, and the 1.2 reconstruction assertion so `workflow_call` inputs are honored, `strict-lint: false` relaxes only lint, and direct events retain published defaults.
- [ ] Run `uv run pytest tests/test_validate_specs_workflow.py tests/package_contract/test_project_spec_reconstruction.py -k 'requested_ref or strict_lint or self_host_mode' -q` and confirm the broken guards fail the new expectations.
- [ ] **GREEN:** Clone 1.1 into a new immutable 1.2 source tree, change only the reusable workflow input guards/expressions, advance the compatible Catalog 5 default, and synchronize the live consumer-owned workflow from that corrected managed resource.
- [ ] Run the focused tests and the four package-contract commands in the Payload task gate below.
- [ ] Run `git diff --exit-code v5.0.2 -- standards/project-spec/versions/1.1`.
- [ ] **Scope audit:** Permit only the listed payload consequences. No trigger, action-pin, Python Tooling, or other workflow change is allowed.
- [ ] Commit: `fix(project-spec): honor reusable workflow inputs`

### Task 3: Add the lock 1.1 absence-record codec

**Findings:** F-003, schema/codec seam

**Files:**

- Modify: `src/project_standards/control_plane/models.py`
- Modify: `src/project_standards/control_plane/codec.py`
- Modify: `src/project_standards/control_plane/schemas.py`
- Modify: `src/project_standards/schemas/consumer-lock.schema.json`
- Modify: `docs/specs/2026-07-10-consumer-standards-control-plane-spec.md`
- Modify: `tests/control_plane/test_models.py`
- Modify: `tests/control_plane/test_codec.py`
- Modify: `tests/control_plane/test_schemas.py`

- [ ] **RED:** Add `test_lock_rejects_duplicate_keys_across_artifacts_and_create_only_absences`, `test_lock_1_0_reads_and_lock_1_1_round_trips_create_only_absences`, and deterministic schema-closure coverage.
- [ ] Run `uv run pytest tests/control_plane/test_models.py tests/control_plane/test_codec.py tests/control_plane/test_schemas.py -k 'lock or absence' -q`; confirm the new partition is unsupported.
- [ ] **GREEN:** Add schema 1.1 `create_only_absences` records containing only path, adapter, normalized scope, owners, shared identity, versions, and provenance. Enforce natural-key uniqueness across live and absent partitions. Read 1.0 as an empty absence partition and emit canonical 1.1.
- [ ] Update only the maintained lock contract: config/catalog schemas stay 1.0 and 5.0.x downgrade remains unsupported.
- [ ] Run the focused tests, `uv run project-standards standards generate-package-schemas --root . --check`, Ruff, and BasedPyright.
- [ ] **Scope audit:** No planner lifecycle, config-schema bump, stale `LockedUnit`, or downgrade implementation belongs in this task.
- [ ] Commit: `fix(control-plane): model create-only absences`

### Task 4: Implement create-only absence lifecycle and conservative inference

**Findings:** F-003, planner/lifecycle seam

**Files:**

- Modify: `src/project_standards/control_plane/planner.py`
- Modify: `src/project_standards/control_plane/bootstrap.py`
- Modify: `src/project_standards/control_plane/recovery.py`
- Modify: `src/project_standards/control_plane/migration.py`
- Modify: `docs/specs/2026-07-10-consumer-standards-control-plane-spec.md`
- Modify: `tests/control_plane/test_planner.py`
- Modify: `tests/control_plane/test_lifecycle.py`
- Modify as required by canonical 1.1 writes: `tests/control_plane/test_bootstrap.py`, `tests/control_plane/test_recovery.py`
- Modify: `tests/control_plane/test_migration.py`

- [ ] **RED:** Add `test_deleted_create_only_unit_moves_to_absence_and_is_not_resurrected`, `test_legacy_lock_infers_absence_only_for_matching_version_and_config`, lifecycle coverage for consumer recreation and package disablement, and migration coverage requiring new/updated locks to emit schema 1.1.
- [ ] Run `uv run pytest tests/control_plane/test_planner.py tests/control_plane/test_lifecycle.py tests/control_plane/test_bootstrap.py tests/control_plane/test_recovery.py tests/control_plane/test_migration.py -k 'create_only or absence or schema_version' -q` and confirm deletion currently loses state or a mutation path writes the old schema.
- [ ] **GREEN:** Move deleted selected create-only units to absences, retain them across reconcile, return consumer-recreated units to live artifacts, remove records when the package is disabled, and infer a damaged 1.0 absence only when package version and effective configuration digest still match.
- [ ] Run the focused gate, Ruff, and BasedPyright.
- [ ] **Scope audit:** Do not infer after package/config drift and do not retain content or semantic hashes for absent bytes.
- [ ] Commit: `fix(control-plane): preserve create-only absence lifecycle`

### Task 5: Normalize lock contention as CP-BUSY

**Findings:** F-004, F-057

**Files:**

- Modify: `src/project_standards/control_plane/cli.py`
- Modify: `src/project_standards/control_plane/recovery.py`
- Modify: `src/project_standards/control_plane/config_edit.py`
- Modify only if a narrow typed mapping is required: `src/project_standards/control_plane/locking.py`
- Modify: `src/project_standards/standards_graph/cli.py`
- Modify: `tests/control_plane/test_cli.py`
- Modify: `tests/control_plane/test_recovery.py`
- Modify: `tests/control_plane/test_config_edit.py`

- [ ] **RED:** Add initialized-surface coverage for reconcile, init, validate, recovery, config edit, render, and the standards list/show/enable/disable/version boundaries; assert `CP-BUSY`, exit 1, no traceback, and equivalent JSON code.
- [ ] Run `uv run pytest tests/control_plane/test_cli.py tests/control_plane/test_recovery.py tests/control_plane/test_config_edit.py -k busy -q` and confirm raw contention escapes or is inconsistently rendered.
- [ ] **GREEN:** Map only the existing lock-contention condition to the stable finding at each public boundary.
- [ ] Run the focused tests, Ruff, and BasedPyright.
- [ ] **Scope audit:** Do not message-sniff, broadly catch `OSError`, reclassify other render failures, or change uninitialized legacy routing.
- [ ] Commit: `fix(control-plane): report stable busy findings`

### Task 6: Reject orphan bounded-block migration safely

**Findings:** F-005

**Files:**

- Modify: `src/project_standards/control_plane/migration.py`
- Modify: `tests/control_plane/test_migration.py`

- [ ] **RED:** Add `test_bounded_block_without_replacement_target_never_removes_whole_file`; assert `CP-MIGRATION-BOUNDED-ORPHAN`, no whole-file `REMOVE`, and unchanged surrounding consumer bytes.
- [ ] Run `uv run pytest tests/control_plane/test_migration.py -k bounded_block_without_replacement -q` and confirm the unsafe removal plan.
- [ ] **GREEN:** Mark only that orphaned bounded-block plan inapplicable with the new diagnostic.
- [ ] Run the focused module, Ruff, and BasedPyright.
- [ ] **Scope audit:** No executor capability, migration redesign, or whole-file signature change.
- [ ] Commit: `fix(control-plane): reject orphan bounded migrations`

### Task 7: Restrict heading extraction to Markdown headings

**Findings:** F-008

**Files:**

- Modify: `src/project_standards/specs/commands/extract.py`
- Modify: `tests/test_spec_extract.py`

- [ ] **RED:** Add `test_heading_selector_starts_at_matching_heading` and `test_heading_selector_does_not_match_prose`.
- [ ] Run `uv run pytest tests/test_spec_extract.py -k heading_selector -q` and confirm prose can satisfy the selector.
- [ ] **GREEN:** Match the requested selector only against parsed heading lines while preserving returned bytes and all other selector classes.
- [ ] Run the focused module, Ruff, and BasedPyright.
- [ ] **Scope audit:** Do not change section-sign, appendix, ID, or heading-hierarchy behavior.
- [ ] Commit: `fix(spec): match extract selectors on headings`

### Task 8: Introduce one fence-masked Project Spec structural view

**Findings:** F-009

**Files:**

- Modify: `src/project_standards/specs/registry.py`
- Modify: `src/project_standards/specs/document.py`
- Modify: `src/project_standards/specs/commands/validate.py`
- Modify: `src/project_standards/specs/commands/lint.py`
- Modify: `src/project_standards/specs/commands/upgrade.py`
- Modify: `tests/test_spec_registry.py`
- Modify: `tests/test_spec_document.py`
- Modify: `tests/test_spec_validate.py`
- Modify: `tests/test_spec_lint.py`
- Modify: `tests/test_spec_upgrade.py`

- [ ] **RED:** Add fence-mask unit coverage plus regressions proving fenced IDs, headings, placeholders, and upgrade examples do not become structure.
- [ ] Run `uv run pytest tests/test_spec_registry.py tests/test_spec_document.py tests/test_spec_validate.py tests/test_spec_lint.py tests/test_spec_upgrade.py -k fence -q` and confirm the false positives.
- [ ] **GREEN:** Add one internal line-preserving masked structural view and route only structural scans through it. Preserve original source for extraction, rendering, byte budgets, and line numbers.
- [ ] Run the five focused modules, Ruff, and BasedPyright.
- [ ] **Scope audit:** Do not introduce a general Markdown parser or duplicate this primitive later; Tasks 14 and 48 must reuse its invariant.
- [ ] Commit: `fix(spec): mask fenced structural examples`

---

## Phase 2: Agent Handoff corrections and payloads

### Task 9: Normalize and report Agent Handoff local links

**Findings:** F-007, F-030, F-031

**Files:**

- Create: `src/project_standards/agent_handoff/integrations/links.py`
- Modify: `src/project_standards/agent_handoff/validation.py`
- Modify: `src/project_standards/agent_handoff/cli.py`
- Modify: `tests/agent_handoff/test_validation.py`

- [ ] **RED:** Cover empty, `<>`, `<path with spaces>`, ordinary local, URL, mail, and fragment targets through mutable validation/helper boundaries. Require `AH-REFERENCE-MISSING` for empty targets and include the offending normalized target in the finding locus.
- [ ] Run `uv run pytest tests/agent_handoff/test_validation.py -k 'reference or link' -q` and confirm empty/angle targets are mishandled.
- [ ] **GREEN:** Add one private normalizer used by both mutable callers; callers keep their existing fence masking and URL/mail/fragment decisions.
- [ ] Run both modules, Ruff, and BasedPyright.
- [ ] **Scope audit:** No public API, new Markdown parser, selected-provider expectation, or import from immutable payload code. Task 14 adds and tests the self-contained selected-provider equivalent.
- [ ] Commit: `fix(agent-handoff): normalize local link targets`

### Task 10: Remove unenforced Agent Handoff policy knobs

**Findings:** F-010

**Files:**

- Modify: `src/project_standards/agent_handoff/policy.py`
- Modify: `standards/agent-handoff/resources/policy.toml`
- Modify: `src/project_standards/bundles/agent-handoff/resources/policy.toml`
- Modify: `tests/agent_handoff/test_policy.py`

- [ ] **RED:** Add `test_policy_contract_omits_unenforced_shape_options` for `max_heading_depth`, `prefer_bullets`, `require_overflow_pointer`, `require_pointer_for_details_over_chars`, and `append_only`, plus `test_mutable_policy_resource_matches_bundle` to pin byte parity between the two mutable policy resources.
- [ ] Run `uv run pytest tests/agent_handoff/test_policy.py -k 'policy_contract or mutable_policy_resource' -q` and confirm the dead knobs remain accepted while the parity guard runs.
- [ ] **GREEN:** Remove only those unused mutable-model and legacy-resource fields; keep all enforced thresholds unchanged.
- [ ] Run the focused module, Ruff, and BasedPyright; the RED parity assertion must remain green after the correction.
- [ ] **Scope audit:** Do not add stricter shape validation or edit released Agent Handoff 1.1. Task 14 mirrors the removal into 1.2.
- [ ] Commit: `fix(agent-handoff): remove dead shape options`

### Task 11: Return success for an emitted legacy inventory

**Findings:** F-011

**Files:**

- Modify: `src/project_standards/agent_handoff/cli.py`
- Modify only if status is encoded there: `src/project_standards/agent_handoff/providers.py`
- Modify: `docs/usage.md`
- Modify: `docs/specs/2026-07-09-agent-handoff-standard-package.md`
- Modify: `tests/agent_handoff/test_selected_routing.py`
- Modify as needed for existing CLI parity: `tests/agent_handoff/test_cli.py`

- [ ] **RED:** Parameterize selected/fallback and human/JSON legacy-report paths; require exit 0 when inventory emission succeeds while retaining error findings in the output.
- [ ] Run `uv run pytest tests/agent_handoff/test_selected_routing.py tests/agent_handoff/test_cli.py -k legacy_report -q` and confirm findings currently force failure.
- [ ] **GREEN:** Separate report-emission success from inventory content severity at the legacy-report boundary.
- [ ] Run both modules, Ruff, and BasedPyright.
- [ ] Update the maintained usage/spec exit taxonomy with the `legacy-report` success exception; run Prettier and focused markdownlint on both documents.
- [ ] **Scope audit:** Do not alter validate/drift exit contracts or suppress any finding.
- [ ] Commit: `fix(agent-handoff): treat legacy inventory as report success`

### Task 12: Add the mutable-runtime JSONC sanitizer

**Findings:** F-019

**Files:**

- Create: `src/project_standards/jsonc.py`
- Modify: `src/project_standards/sync_standards_include.py`
- Modify: `src/project_standards/sync_vscode_colors.py`
- Create: `tests/test_jsonc.py`
- Modify: `tests/test_sync_standards_include.py`
- Modify: `tests/test_sync_vscode_colors.py`

- [ ] **RED:** Add exhaustive string/comment/trailing-comma cases, including comment-like and comma text inside quoted strings, escaped quotes, inline comments, block comments, and controlled malformed input.
- [ ] Run `uv run pytest tests/test_jsonc.py tests/test_sync_standards_include.py tests/test_sync_vscode_colors.py -k 'jsonc or inline or trailing or malformed' -q` and confirm strict or regex parsing fails the invariant.
- [ ] **GREEN:** Implement one private lexical, string-aware sanitizer and use it only at the two mutable sync-tool parse boundaries.
- [ ] Run the three modules, Ruff, and BasedPyright.
- [ ] **Scope audit:** No trailing-comma regex, control-plane adapter refactor, public helper, new dependency, or payload import.
- [ ] Commit: `fix(jsonc): sanitize comments without changing strings`

### Task 13: Accept JSONC in mutable Agent Handoff inspection

**Findings:** F-024

**Files:**

- Modify: `src/project_standards/agent_handoff/validation.py`
- Modify: `tests/agent_handoff/test_validation.py`

- [ ] **RED:** Add `test_claude_settings_inspection_accepts_jsonc` with comments, trailing commas, and string-literal traps; malformed JSONC must still produce the current controlled finding.
- [ ] Run `uv run pytest tests/agent_handoff/test_validation.py -k jsonc -q` and confirm strict `json.loads` rejects valid settings.
- [ ] **GREEN:** Route only mutable Agent Handoff inspection through Task 12's internal sanitizer.
- [ ] Run the focused module, Ruff, and BasedPyright.
- [ ] **Scope audit:** Do not change writers or import the private control-plane JSONC adapter. Task 14 implements an equivalent local payload lexer rather than importing mutable code.
- [ ] Commit: `fix(agent-handoff): inspect Claude JSONC settings`

### Task 14: Complete the corrected Agent Handoff 1.2 payload atomically

**Findings:** Agent Handoff slices of F-006 and F-096, F-027, plus immutable mirrors required by F-007, F-010, and F-024

**Files:**

- Create: `standards/agent-handoff/versions/1.2/**`
- Modify: `standards/agent-handoff/standard.toml`
- Modify only as required by the new version: `standards/agent-handoff/README.md`, `standards/agent-handoff/adopt.md`, `standards/agent-handoff/agent-summary.md`
- Generate: `src/project_standards/payloads/agent-handoff/1.2/**`
- Generate/update: `catalogs/5.toml`, `standards/catalog.md`, `.standards/catalog.toml`, `.standards/lock.toml`
- Modify: `docs/specs/2026-07-09-agent-handoff-standard-package.md`
- Modify: `tests/package_contract/test_agent_handoff_reconstruction.py`
- Modify: `tests/agent_handoff/test_selected_routing.py`
- Modify: `tests/package_contract/test_current_catalog_activation.py`
- Modify only deterministic compatibility expectations: `tests/package_compatibility/matrix.py`

- [ ] **RED:** Add `test_agent_handoff_1_2_selected_provider_normalizes_link_targets`, `test_agent_handoff_1_2_requires_shebang_python_3_14`, and `test_agent_handoff_1_2_declares_source_and_install_modes`, plus reconstruction regressions for local JSONC lexer semantics, removed policy options, and `test_agent_handoff_shape_checks_ignore_fenced_structural_lines` covering headings, bullets, tables, rows, and headline scans.
- [ ] Run `uv run pytest tests/package_contract/test_agent_handoff_reconstruction.py tests/agent_handoff/test_selected_routing.py tests/package_contract/test_current_catalog_activation.py -k 'agent_handoff_1_2 or shape_checks_ignore_fenced' -q` and confirm no complete corrected 1.2 payload exists.
- [ ] **GREEN:** Clone 1.1 into 1.2, mirror the completed mutable corrections, add an equivalent self-contained JSONC lexer, reuse the Task 8 fence-masking invariant locally, state that the shebang-resolved consumer `python3` is 3.14+, and record the source-data/installed-mode contract. The payload imports neither `project_standards.jsonc` nor `control_plane.adapters.jsonc`.
- [ ] Keep `session_start.py` as payload data mode `100644`; retain managed artifact `mode = "0755"`. Update the maintained Agent Handoff spec in the same task.
- [ ] Advance only the compatible Agent Handoff default and generate the source projection and lock/catalog consequences.
- [ ] Run the focused reconstruction suite and the Payload task gate.
- [ ] Run `git diff --exit-code v5.0.2 -- standards/agent-handoff/versions/1.1`.
- [ ] **Scope audit:** Agent Handoff 1.2 is complete before it is advertised. No later task may mutate it; no extra payload behavior or policy tightening.
- [ ] Commit: `fix(agent-handoff): add corrected 1.2 provider`

### Task 15: Restore Agent Handoff view parsing and guard upgrade resources

**Findings:** F-029, F-033

**Files:**

- Modify: `src/project_standards/agent_handoff/cli.py`
- Modify: `tests/agent_handoff/test_selected_routing.py`
- Modify: `tests/agent_handoff/test_cli.py`

- [ ] **RED:** Cover `--view size` after `--repo`, `--view=size`, repeated view options under the existing parser rule, and a deliberately absent upgrade manifest resource yielding `CommandResolutionError`/exit 3 rather than `StopIteration`.
- [ ] Run `uv run pytest tests/agent_handoff/test_selected_routing.py tests/agent_handoff/test_cli.py -k 'view or missing_resource' -q` and confirm current routing fails.
- [ ] **GREEN:** Derive view selection from the existing parser-compatible option surface and guard the missing-resource lookup at the command boundary.
- [ ] Run both modules, Ruff, and BasedPyright.
- [ ] **Scope audit:** Add no option, argparse policy, or invented stale-lock trigger.
- [ ] Commit: `fix(agent-handoff): preserve view and resource errors`

### Task 16: Preserve existing modes in legacy Agent Handoff writes

**Findings:** F-032

**Files:**

- Modify: `src/project_standards/agent_handoff/paths.py`
- Modify: `tests/agent_handoff/test_paths.py`

- [ ] **RED:** Rewrite an existing `0600` file and assert it remains `0600`; preserve the current new-file mode expectation.
- [ ] Run `uv run pytest tests/agent_handoff/test_paths.py -k mode -q` and confirm replacement changes the existing mode.
- [ ] **GREEN:** Carry the observed existing mode through the bounded atomic replacement path.
- [ ] Run the focused module, Ruff, and BasedPyright.
- [ ] **Scope audit:** No unrelated path/writer refactor and no payload source-mode change.
- [ ] Commit: `fix(agent-handoff): preserve legacy write modes`

### Task 17: Cut Standard Bundle Authoring 2.2

**Findings:** Standard Bundle Authoring slices of F-006 and F-096, then F-069

**Files:**

- Create: `standards/standard-bundle-authoring/versions/2.2/**`
- Modify: `standards/standard-bundle-authoring/standard.toml`
- Modify: `standards/standard-bundle-authoring/README.md`, `standards/standard-bundle-authoring/agent-summary.md`
- Modify: `docs/specs/2026-07-10-standard-bundle-authoring-v2-spec.md`
- Modify after 2.2 exists: `AGENTS.md`, `standards/README.md`
- Generate: `src/project_standards/payloads/standard-bundle-authoring/2.2/**`
- Generate/update: `catalogs/5.toml`, `standards/catalog.md`, `.standards/catalog.toml`, `.standards/lock.toml`
- Modify: `tests/package_contract/test_self_hosting.py`
- Modify: `tests/package_contract/test_current_catalog_activation.py`

- [ ] **RED:** Add `test_standard_bundle_authoring_2_2_requires_python_3_14`, `test_standard_bundle_authoring_2_2_declares_artifact_mode_contract`, and `test_standard_bundle_authoring_2_2_is_internal_and_advertised`.
- [ ] Run `uv run pytest tests/package_contract/test_self_hosting.py tests/package_contract/test_current_catalog_activation.py -k standard_bundle_authoring_2_2 -q` and confirm 2.2 and both contracts are absent.
- [ ] **GREEN:** Clone Standard Bundle Authoring 2.1 into 2.2, state the Python 3.14 floor and that declared artifact mode—not source-tree executable bits—is the consumer contract, then update `AGENTS.md` and `standards/README.md` to name 2.2.
- [ ] Run the two focused modules and the Payload task gate.
- [ ] Run `git diff --exit-code v5.0.2 -- standards/standard-bundle-authoring/versions/2.0 standards/standard-bundle-authoring/versions/2.1`.
- [ ] **Scope audit:** Agent Handoff 1.2 is verify-only here. No syntax backport, lower-runtime lane, source-mode claim, sixth payload, or unrelated authoring change.
- [ ] Commit: `docs(packages): require Python 3.14 and declare artifact modes`

---

## Reusable payload task gate

Run this gate at the end of Tasks 2, 14, 17, 27, and 47, with the task's focused reconstruction tests first:

```bash
uv run project-standards standards validate-packages --root . --json
uv run project-standards standards validate-graph --root . --require-all-manifests --json
uv run project-standards standards generate-package-schemas --root . --check
uv run project-standards standards sync-payload-projection --root . --check
uv run project-standards standards render-catalog --root . --check
```

If the task changes `tests/package_compatibility/matrix.py`, verify that expectation immediately with one exact freshly built wheel before committing:

```bash
payload_artifacts="$(mktemp -d)"
uv build --wheel --out-dir "$payload_artifacts"
mapfile -t payload_wheels < <(find "$payload_artifacts" -maxdepth 1 -type f -name 'project_standards-*.whl' -print)
test "${#payload_wheels[@]}" -eq 1
PROJECT_STANDARDS_COMPATIBILITY_WHEEL="${payload_wheels[0]}" \
  uv run pytest -m compatibility -n 4 --dist load --max-worker-restart=0
```

The diff may include only the task's new canonical payload, its symlink-only projection, its family index/docs, Catalog 5, rendered catalog, local lock, and an explicitly named live dogfood artifact. A generated file does not excuse unrelated content.

---

## Phase 3: Legacy adoption, migration, and frontmatter boundaries

### Task 18: Bound v5 adoption activation and expose fallback

**Findings:** F-012, F-041

**Files:**

- Modify: `src/project_standards/cli.py`
- Modify: `tests/test_adopt_cli.py`

- [ ] **RED:** Extend `test_v5_adopt_activates_only_for_the_complete_default_set` with complete-plus-extra selecting v5 and missing-any-legacy-default rejecting v5. Add a case where `InstalledDistribution.current()` raises `OSError`; require a visible warning and the existing legacy fallback result.
- [ ] Run `uv run pytest tests/test_adopt_cli.py -k 'complete_default_set or distribution' -q` and confirm both edge contracts fail.
- [ ] **GREEN:** Change the activation check from equality to the verified default-set superset rule and catch only installed-distribution `OSError` at the fallback boundary.
- [ ] Run the focused module, Ruff, and BasedPyright.
- [ ] **Scope audit:** Do not add defaults, standards, package selection behavior, or a new exit classification; preserve `PackageContractError` and `ValueError` handling.
- [ ] Commit: `fix(adopt): bound v5 activation and warn on fallback`

### Task 19: Close partial staging and remove the unused destination

**Findings:** F-013, F-053

**Files:**

- Modify: `src/project_standards/control_plane/executor.py`
- Modify: `tests/control_plane/test_executor.py`

- [ ] **RED:** Extend `test_failure_returns_exact_published_prefix_and_preserves_previous_lock` with a nested staging failure that proves all descriptors and temporary files are cleaned. Characterize `_stage_bytes` behavior before signature change.
- [ ] Run `uv run pytest tests/control_plane/test_executor.py::test_failure_returns_exact_published_prefix_and_preserves_previous_lock -q` and confirm the partial-stage leak.
- [ ] **GREEN:** Close the partial staging resource on every failure path, remove `_stage_bytes.destination`, and update exactly the five verified call sites.
- [ ] Run `uv run pytest tests/control_plane/test_executor.py -q`, Ruff, and BasedPyright.
- [ ] **Scope audit:** Do not change publication order, any other staging signature, or filesystem helper architecture.
- [ ] Commit: `fix(control-plane): close partial staging resources`

### Task 20: Validate provider finding fields at runtime

**Findings:** F-014

**Files:**

- Modify: `src/project_standards/control_plane/providers.py`
- Modify only if needed for a private boundary model: `src/project_standards/control_plane/schemas.py`
- Modify: `tests/control_plane/test_providers.py`

- [ ] **RED:** Add `test_provider_rejects_invalid_finding_fields`, parameterized over severity `info`, integer code/path/identity, and invalid line/locus values.
- [ ] Run `uv run pytest tests/control_plane/test_providers.py -k invalid_finding_fields -q` and confirm malformed fields cross the boundary.
- [ ] **GREEN:** Validate the existing finding schema at provider ingress without coercion and return the current controlled provider error.
- [ ] Run the focused module, Ruff, and BasedPyright.
- [ ] **Scope audit:** No new severity, public model, coercion, or diagnostic schema redesign.
- [ ] Commit: `fix(control-plane): validate provider findings`

### Task 21: Put distribution discovery inside public error boundaries

**Findings:** F-015

**Files:**

- Modify: `src/project_standards/control_plane/cli.py`
- Modify: `tests/control_plane/test_cli.py`

- [ ] **RED:** Parameterize `test_distribution_discovery_failure_is_caught_by_all_entrypoints` over `run`, `run_init`, and `validate_repository`; retain render coverage.
- [ ] Run `uv run pytest tests/control_plane/test_cli.py -k distribution_discovery_failure -q` and confirm at least one discovery call escapes.
- [ ] **GREEN:** Move discovery inside each existing public error boundary without changing success behavior or existing error codes.
- [ ] Run the focused module, Ruff, and BasedPyright.
- [ ] **Scope audit:** Only call placement and its regression may change.
- [ ] Commit: `fix(control-plane): contain distribution discovery errors`

### Task 22A: Render canonically parseable migration TOML

**Findings:** F-016

**Files:**

- Modify: `src/project_standards/control_plane/migration.py`
- Modify: `tests/control_plane/test_migration.py`

- [ ] **RED:** Add `test_migrated_config_escapes_u007f_and_round_trips` for keys and values.
- [ ] Run `uv run pytest tests/control_plane/test_migration.py -k u007f -q` and confirm the rendered TOML is not canonically parseable.
- [ ] **GREEN:** Escape DEL through the existing bounded TOML renderer and reparse rendered config before returning a plan.
- [ ] Run the focused module, Ruff, and BasedPyright.
- [ ] **Scope audit:** No serializer replacement, formatting rewrite, claim-validation change, or adjacent migration cleanup.
- [ ] Commit: `fix(control-plane): render parseable migrated TOML`

### Task 22B: Reject unobserved migration claim targets

**Findings:** F-017

**Files:**

- Modify: `src/project_standards/control_plane/migration.py`
- Modify: `tests/control_plane/test_migration.py`

- [ ] **RED:** Add `test_retirement_views_reject_unobserved_claim_target`.
- [ ] Run `uv run pytest tests/control_plane/test_migration.py -k unobserved_claim_target -q` and confirm the unobserved claim is accepted.
- [ ] **GREEN:** Require retirement claims to name targets observed by the migration evidence.
- [ ] Run the focused module, Ruff, and BasedPyright.
- [ ] **Scope audit:** No provider-claim expansion, TOML rendering change, or valid-retirement behavior change.
- [ ] Commit: `fix(control-plane): reject unobserved migration claims`

### Task 23: Correct the internal-payload PATCH policy table

**Findings:** F-018

**Files:**

- Modify: `meta/versioning.md`
- Modify: `tests/package_contract/test_release.py`

- [ ] **RED:** Add `test_versioning_document_matches_internal_advertisement_classification` to compare the maintained table with the existing internal-additive classifier.
- [ ] Run `uv run pytest tests/package_contract/test_release.py -k internal_advertisement -q` and confirm the wording contradicts the executable rule.
- [ ] **GREEN:** Correct only the table cell explaining compatible internal payload advertisement as PATCH.
- [ ] Run the focused test plus Prettier and markdownlint on `meta/versioning.md`.
- [ ] **Scope audit:** Do not change `release.py`, consumer-visible classification, or any 5.0.2 record.
- [ ] Commit: `docs(versioning): align internal payload classification`

### Task 24: Preserve frontmatter containing anchors or aliases

**Findings:** F-021

**Files:**

- Modify: `src/project_standards/format_frontmatter.py`
- Modify: `tests/test_format_frontmatter.py`

- [ ] **RED:** Add `test_anchor_or_alias_anywhere_in_frontmatter_warns_and_preserves_bytes`, parameterized across mapping keys/values, list values, and block-list tokens.
- [ ] Run `uv run pytest tests/test_format_frontmatter.py -k 'anchor or alias' -q` and confirm an unsafe rewrite remains possible.
- [ ] **GREEN:** Detect anchor/alias tokens throughout the frontmatter token stream, leave bytes untouched, emit the warning, and retain exit 0.
- [ ] Run the focused module, Ruff, and BasedPyright.
- [ ] **Scope audit:** F-020 remains untouched; do not add YAML feature support or a new failure exit.
- [ ] Commit: `fix(frontmatter): preserve anchors and aliases`

### Task 25A: Splice VS Code path colors without reserialization

**Findings:** F-022

**Files:**

- Modify: `src/project_standards/sync_vscode_colors.py`
- Modify: `tests/test_sync_vscode_colors.py`

- [ ] **RED:** Prove only the existing `path-colors` value changes or a missing value is inserted without altering other bytes, including nested bracket, comment, escaped-string, and bracket-in-string traps.
- [ ] Run `uv run pytest tests/test_sync_vscode_colors.py -k 'preserv or splice or path_colors' -q` and confirm broad reserialization changes unrelated bytes.
- [ ] **GREEN:** Add a scanner local to `sync_vscode_colors.py` that finds the bounded value span without reusing or expanding Task 12's sanitizer.
- [ ] Run the focused module, Ruff, and BasedPyright.
- [ ] **Scope audit:** Do not reorder unrelated JSONC, change other VS Code keys, generalize the scanner, or edit the standards-include tool.
- [ ] Commit: `fix(sync): splice VS Code path colors`

### Task 25B: Scope the frontmatter include rewrite

**Findings:** F-078

**Files:**

- Modify: `src/project_standards/sync_standards_include.py`
- Modify: `tests/test_sync_standards_include.py`

- [ ] **RED:** Prove backslashes cannot trigger `re.error` and only `markdown.frontmatter.include` changes when another four-space `include` block exists.
- [ ] Run `uv run pytest tests/test_sync_standards_include.py -k 'scoped or backslash or frontmatter' -q` and confirm the broad replacement.
- [ ] **GREEN:** Use a callable replacement anchored beneath exactly one `markdown.frontmatter` block.
- [ ] Run the focused module, Ruff, and BasedPyright.
- [ ] **Scope audit:** Do not change exit codes, other include blocks, the VS Code tool, or F-077.
- [ ] Commit: `fix(sync): scope the frontmatter include rewrite`

### Task 26: Resolve option-schema references from the root

**Findings:** F-023

**Files:**

- Modify: `src/project_standards/package_contract/payload.py`
- Modify: `tests/package_contract/test_payload.py`

- [ ] **RED:** Add `test_option_schema_default_resolves_local_root_ref` and `test_option_schema_missing_ref_is_controlled_for_defaults_and_options`.
- [ ] Run `uv run pytest tests/package_contract/test_payload.py -k 'ref and (default or missing)' -q` and confirm child-context resolution fails.
- [ ] **GREEN:** Build the validator from the root option schema and route missing local references through the existing controlled package diagnostic.
- [ ] Run the focused module, Ruff, and BasedPyright.
- [ ] **Scope audit:** No remote reference support, draft change, or schema redesign.
- [ ] Commit: `fix(packages): resolve local option schema references`

### Task 27: Cut Markdown Frontmatter 1.3

**Findings:** F-025, F-034

**Files:**

- Modify: `src/project_standards/validate_id.py`
- Modify: `src/project_standards/validate_references.py`
- Create: `standards/markdown-frontmatter/versions/1.3/**`
- Modify: `standards/markdown-frontmatter/standard.toml`
- Modify only as required by the new version: `standards/markdown-frontmatter/README.md`, `standards/markdown-frontmatter/adopt.md`, `standards/markdown-frontmatter/agent-summary.md`
- Generate: `src/project_standards/payloads/markdown-frontmatter/1.3/**`
- Generate/update: `catalogs/5.toml`, `standards/catalog.md`, `.standards/catalog.toml`, `.standards/lock.toml`
- Generate managed caller output: `.github/workflows/validate-standards.yml`
- Modify: `tests/test_validate_id.py`
- Modify: `tests/test_validate_references.py`
- Modify: `tests/package_contract/test_markdown_frontmatter_reconstruction.py`
- Modify only deterministic compatibility expectations: `tests/package_compatibility/matrix.py`

- [ ] **RED:** Require stable public and retained private aliases for ADR ID and reference-value validators. Require the 1.3 managed caller to declare only `permissions: {contents: read}` and no private-usage suppressions.
- [ ] Run `uv run pytest tests/test_validate_id.py tests/test_validate_references.py tests/package_contract/test_markdown_frontmatter_reconstruction.py -k 'payload_api or public_alias or permissions' -q` and confirm the public names and 1.3 payload are absent.
- [ ] **GREEN:** Add public aliases without removing private aliases, clone 1.2 into 1.3, update only imports and the caller permission, then synchronize the compatible default and generated outputs.
- [ ] Run the focused tests and the Payload task gate.
- [ ] Run `git diff --exit-code v5.0.2 -- standards/markdown-frontmatter/versions/1.2`.
- [ ] **Scope audit:** No alias removal, broader API, trigger edit, YAML reordering, or separate payload cut.
- [ ] Commit: `fix(markdown-frontmatter): publish stable validator aliases`

### Task 28: Derive spec modes from the real parsers

**Findings:** F-026

**Files:**

- Modify: `src/project_standards/specs/cli.py`
- Modify: `tests/test_spec_cli.py`
- Modify: `tests/test_spec_new_cli.py`
- Modify: `tests/test_spec_upgrade_cli.py`

- [ ] **RED:** Cover `--in-pl`, `--outp`, `-io`, abbreviated `--js`, and malformed/uncertain argument streams. Require parser-compatible recognition and a safe write lock on uncertainty.
- [ ] Run `uv run pytest tests/test_spec_cli.py tests/test_spec_new_cli.py tests/test_spec_upgrade_cli.py -k 'lock_mode or abbreviated_json' -q` and confirm hand parsing diverges.
- [ ] **GREEN:** Ask the existing command parsers for lock and JSON modes while preserving accepted argparse abbreviations.
- [ ] Run all three modules, Ruff, and BasedPyright.
- [ ] **Scope audit:** Do not set `allow_abbrev=False`, add flags, or change accepted spellings.
- [ ] Commit: `fix(spec): derive modes from command parsers`

---

## Phase 4: CI, filesystem safety, and control-plane hardening

### Task 29: Correct validate-id zipapp failure and source precedence

**Findings:** F-036, F-038

**Files:**

- Modify: `scripts/build-validate-id-pyz.sh`
- Create: `tests/test_validate_id_zipapp.py`

- [ ] **RED:** Build the zipapp and prove supported CLI paths work, direct unsupported `jsonschema` calls fail loudly, and an alternate checkout chooses its sibling `src/project_standards` before the workstation fallback.
- [ ] Run `uv run pytest tests/test_validate_id_zipapp.py -q` and confirm the stub silently accepts unsupported calls or source precedence is wrong.
- [ ] **GREEN:** Raise `NotImplementedError` only from unsupported stub methods and place sibling source discovery ahead of the workstation fallback while preserving explicit argument and `PS_SRC` precedence.
- [ ] Run the focused module, `bash -n scripts/build-validate-id-pyz.sh`, Ruff on the new test, and BasedPyright.
- [ ] **Scope audit:** Do not bundle real `jsonschema`, change supported validation, or alter explicit source overrides.
- [ ] Commit: `fix(zipapp): fail loud and prefer sibling source`

### Task 30: Pass graph baseline refs through the environment

**Findings:** F-037

**Files:**

- Modify: `.github/workflows/validate-standards-graph.yml`
- Modify: `tests/test_standards_graph_workflow.py`

- [ ] **RED:** Require the resolved output to be assigned to `BASELINE_REF` under `env:` and the shell to use `"$BASELINE_REF"`.
- [ ] Run `uv run pytest tests/test_standards_graph_workflow.py -q` and confirm direct expression interpolation remains in shell code.
- [ ] **GREEN:** Move only the baseline value across the existing environment boundary.
- [ ] Run the focused test and Prettier on the workflow.
- [ ] **Scope audit:** No trigger, action pin, release-resolution, or other workflow hardening change.
- [ ] Commit: `fix(ci): pass graph baseline as environment data`

### Task 31: Correct test and CI intent documentation

**Findings:** F-028, F-035, F-039

**Files:**

- Modify: `tests/README.md`
- Modify comment only: `.github/workflows/coherence.yml`

- [ ] **RED inventory:** Use `rg` to show the documented suite tree omits `agent_handoff/`, `control_plane/`, `package_contract/`, `package_compatibility/`, and `coherence/`, and that current runtime/network/helper claims contradict the repository. Confirm no statement explains the intentional separate coherence job or `testing` trigger asymmetry.
- [ ] **GREEN:** Correct only the actual suite layout, helper convention, network/runtime claims, installed-wrapper behavior, `testing` graph-only policy, and intentional separately named coherence coverage.
- [ ] Run `npx prettier --check tests/README.md .github/workflows/coherence.yml` and `npx markdownlint-cli2 --no-globs ':tests/README.md'`.
- [ ] **Scope audit:** No test move, helper move, new `testing` trigger, workflow deletion, or workflow behavior change.
- [ ] Commit: `docs(tests): correct suite and CI intent`

### Task 32: Share the bounded no-clobber filesystem invariant

**Findings:** F-040, F-055, F-088

**Files:**

- Create: `src/project_standards/_filesystem.py`
- Modify: `src/project_standards/adopt/engine.py`
- Modify: `src/project_standards/control_plane/executor.py`
- Modify: `src/project_standards/specs/cli.py`
- Create/modify: `tests/test_filesystem.py`
- Modify: `tests/test_adopt_engine.py`
- Modify: `tests/test_adopt_safety.py`
- Modify: `tests/control_plane/test_executor.py`
- Modify: `tests/test_spec_new_cli.py`

- [ ] **RED:** Add parent/leaf swap and absent-destination races for legacy adopt, a fault-hook symlink swap during namespace pruning, and a target-created-after-inspection race for non-force `spec new`. Assert no escape, overwrite, or outside deletion.
- [ ] Run `uv run pytest tests/test_filesystem.py tests/test_adopt_engine.py tests/test_adopt_safety.py tests/control_plane/test_executor.py tests/test_spec_new_cli.py -k 'race or symlink or clobber or prune' -q` and confirm the three writers do not share the required invariant.
- [ ] **GREEN:** Add the smallest private descriptor-relative, no-follow/no-clobber primitives needed by exactly these three sites; preserve force and explicit-precondition behavior and executor applied-ID ordering.
- [ ] Run all five modules, Ruff, and BasedPyright.
- [ ] **Scope audit:** No public filesystem API, recursive deletion, path-following fallback, unrelated writer migration, or replace-only partial remedy.
- [ ] Commit: `fix(filesystem): enforce descriptor-safe no-clobber writes`

### Task 33: Tighten manifest and registry ingestion

**Findings:** F-042, F-043, F-044, F-045

**Files:**

- Modify: `src/project_standards/adopt/engine.py`
- Modify: `src/project_standards/adopt/manifest.py`
- Modify: `src/project_standards/registry.py`
- Modify: `tests/test_adopt_engine.py`
- Modify: `tests/test_adopt_manifest.py`
- Modify: `tests/test_validate_frontmatter.py`

- [ ] **RED:** Require identical source/destination with different artifact kinds to fail and Boolean modes to reject. Parameterize numeric registry members across both `_require_str_list`-managed fields and the separately parsed `adr.versions.<version>.supports_frontmatter`; require registry files missing `agent_handoff` to reject while direct `Registry()` defaults remain valid.
- [ ] Run `uv run pytest tests/test_adopt_engine.py tests/test_adopt_manifest.py tests/test_validate_frontmatter.py -k 'collision or mode or registry or agent_handoff' -q` and confirm permissive ingestion.
- [ ] **GREEN:** Enforce the existing typed domains at file-load boundaries only.
- [ ] Run all three modules, Ruff, and BasedPyright.
- [ ] **Scope audit:** No coercion, direct-constructor break, artifact-policy expansion, or change to accepted octal modes.
- [ ] Commit: `fix(validation): tighten manifest and registry inputs`

### Task 34: Emit one graph finding for a mislinked manifest

**Findings:** F-046

**Files:**

- Modify: `src/project_standards/standards_graph/validators.py`
- Modify: `tests/test_standards_graph_validators.py`

- [ ] **RED:** Add cases proving escape and mismatch findings do not also emit missing-manifest findings.
- [ ] Run `uv run pytest tests/test_standards_graph_validators.py -k 'escape or mismatch or missing' -q` and confirm duplicate diagnostics.
- [ ] **GREEN:** Stop the missing check after the more specific link diagnostic for that manifest.
- [ ] Run the focused module, Ruff, and BasedPyright.
- [ ] **Scope audit:** No graph discovery or diagnostic-code redesign.
- [ ] Commit: `fix(graph): avoid duplicate manifest findings`

### Task 35: Consolidate the six typed digest wrappers

**Findings:** F-047

**Files:**

- Modify: `src/project_standards/control_plane/codec.py`
- Modify exactly: `src/project_standards/control_plane/planner.py`
- Modify exactly: `src/project_standards/control_plane/snapshot.py`
- Modify exactly: `src/project_standards/control_plane/adapters/whole_file.py`
- Modify exactly: `src/project_standards/control_plane/migration.py`
- Modify exactly: `src/project_standards/control_plane/providers.py`
- Modify exactly: `src/project_standards/control_plane/adapters/markdown.py`
- Modify: `tests/control_plane/test_codec.py`

- [ ] **RED:** Characterize exact `sha256:` typed output in `test_content_digest_is_canonical` and count the six local wrappers before refactoring.
- [ ] Run `uv run pytest tests/control_plane/test_codec.py -k content_digest -q`; the new central helper should be absent.
- [ ] **GREEN:** Add private `control_plane.codec.content_digest` and replace exactly the six typed duplicates.
- [ ] Run `uv run pytest tests/control_plane -q`, Ruff, and BasedPyright.
- [ ] **Scope audit:** No public package-contract API, string-returning digest helper, seventh caller, or adjacent digest cleanup.
- [ ] Commit: `refactor(control-plane): centralize typed content digest`

### Task 36: Correct state, mode, and missing-target facts

**Findings:** F-048, F-049, F-051

**Files:**

- Modify: `src/project_standards/control_plane/state.py`
- Modify: `src/project_standards/control_plane/planner.py`
- Modify: `tests/control_plane/test_state.py`
- Modify: `tests/control_plane/test_planner.py`
- Modify: `tests/control_plane/test_executor.py`

- [ ] **RED:** Cover a disappearing `.standards` directory, an existing `0755` whole-file target with no declared mode, a missing target's creation mode, and a missing-target NOOP digest of `None`.
- [ ] Run `uv run pytest tests/control_plane/test_state.py tests/control_plane/test_planner.py tests/control_plane/test_executor.py -k 'deletion or undeclared_mode or missing_target' -q` and confirm the facts are wrong.
- [ ] **GREEN:** Reclassify only the deletion race as uninitialized/legacy, preserve observed mode when content changes and no mode is declared, and report no digest for an absent NOOP target.
- [ ] Run all three modules, Ruff, and BasedPyright.
- [ ] **Scope audit:** Extant unsafe state remains malformed; explicit modes, existing-target NOOP, and REMOVE facts remain unchanged.
- [ ] Commit: `fix(control-plane): report truthful state and target facts`

### Task 37: Replace resolution message sniffing with typed failures

**Findings:** F-050, F-058, F-059, F-060, F-062

**Files:**

- Modify: `src/project_standards/control_plane/diagnostics.py`
- Modify: `src/project_standards/control_plane/resolution.py`
- Modify: `src/project_standards/control_plane/command_resolution.py`
- Modify: `src/project_standards/control_plane/cli.py`
- Modify: `tests/control_plane/test_resolution.py`
- Modify: `tests/control_plane/test_command_resolution.py`
- Modify: `tests/control_plane/test_cli.py`

- [ ] **RED:** Cover both current major-authorization sites in `resolution.py` (the branches at pre-plan lines 403-405 and 548-550), both absent-companion sites in `command_resolution.py` (pre-plan lines 231 and 233), unrelated messages containing the same words, `--apply --json` reporting `"mode":"apply"`, and findings omitting `None` fields. Pin neighboring `ControlPlaneError` and `CommandResolutionError` cases to their current classifications.
- [ ] Run `uv run pytest tests/control_plane/test_resolution.py tests/control_plane/test_command_resolution.py tests/control_plane/test_cli.py -k 'allow_major or companion or authorization or json' -q` and confirm classification depends on strings or the envelope lies.
- [ ] **GREEN:** Add only the private typed failures needed for the two resolution conditions, preserve messages/exits, remove F-058's no-op wrapper, and serialize through `findings_to_jsonable`.
- [ ] Run all three modules, Ruff, and BasedPyright.
- [ ] **Scope audit:** No broad exception hierarchy, schema redesign, or unrelated reclassification.
- [ ] Commit: `fix(control-plane): type resolution failures`

### Task 38: Restrict parser boundaries to real newlines

**Findings:** F-052, F-054

**Files:**

- Modify: `src/project_standards/control_plane/adapters/markdown.py`
- Modify: `src/project_standards/control_plane/adapters/editorconfig.py`
- Modify: `tests/control_plane/test_adapters_markdown.py`
- Modify: `tests/control_plane/test_adapters_editorconfig.py`

- [ ] **RED:** Exhaustively parameterize non-newline `splitlines()` control characters plus LF and CRLF; prove stable spans and round trips for both adapters.
- [ ] Run `uv run pytest tests/control_plane/test_adapters_markdown.py tests/control_plane/test_adapters_editorconfig.py -q` and confirm another control is treated as a line boundary.
- [ ] **GREEN:** Split only at LF/CRLF boundaries and remove the now-dead Markdown branch.
- [ ] Run both modules, Ruff, and BasedPyright.
- [ ] **Scope audit:** No new dependency, Markdown fence semantic change, EditorConfig semantic change, or generalized parser rewrite.
- [ ] Commit: `fix(adapters): recognize only real newline boundaries`

### Task 39: Bound reserved temporaries and recovery reporting

**Findings:** F-056, F-061

**Files:**

- Modify: `src/project_standards/control_plane/bootstrap.py`
- Modify: `src/project_standards/control_plane/config_edit.py`
- Modify: `src/project_standards/control_plane/recovery.py`
- Modify only for a bounded name helper: `src/project_standards/control_plane/locking.py`
- Modify: `tests/control_plane/test_bootstrap.py`
- Modify: `tests/control_plane/test_config_edit.py`
- Modify: `tests/control_plane/test_recovery.py`
- Modify only if `locking.py` changes: `tests/control_plane/test_locking.py`

- [ ] **RED:** Cover standardized reserved names, cleanup of matching stale regular temporaries only under exclusive authority, preservation of symlinks/nonregular/user-named entries, and recovery failure before versus after catalog replacement.
- [ ] Run `uv run pytest tests/control_plane/test_bootstrap.py tests/control_plane/test_config_edit.py tests/control_plane/test_recovery.py tests/control_plane/test_locking.py -k 'temporary or stale or applied or catalog or reserved' -q` and confirm cleanup/reporting drift.
- [ ] **GREEN:** Centralize only the reserved-name spelling if needed, validate cleanup candidates under the existing lock/recovery authority, and append the catalog action only after replacement succeeds.
- [ ] Run the three required modules and, when `locking.py` changes, the full locking module; then run Ruff and BasedPyright.
- [ ] **Scope audit:** No glob cleanup, read-lock cleanup, symlink handling, nonregular deletion, or change to recovery ordering.
- [ ] Commit: `fix(control-plane): bound temporary cleanup and recovery facts`

---

## Phase 5: Maintained documentation, package contracts, and spec commands

### Task 40: Correct maintained navigation and usage facts

**Findings:** F-063, F-064, F-065, F-066, F-067

**Files:**

- Modify: `README.md`
- Modify: `docs/handoff/specs-plans.md`
- Modify: `docs/specs/archive/README.md`
- Modify: `docs/usage.md`
- Modify: `docs/mcp-readiness.md`
- Modify only if its inventory assertion changes: `tests/test_usage_doc_inventory.py`

- [ ] **RED inventory:** Prove the README table of contents has the stale entry, the historical index misstates 1.3.0, the top usage synopsis omits `--force`, the readiness command presents an old explicit `--config` path as current, and the coherence path omits `npm ci`.
- [ ] **GREEN:** Correct only those five documented facts. Use the repo-local Agent Handoff routing rules for `docs/handoff/specs-plans.md`; do not rewrite append-only session history.
- [ ] Run `uv run pytest tests/test_usage_doc_inventory.py -q`, `npx prettier --check README.md docs/handoff/specs-plans.md docs/specs/archive/README.md docs/usage.md docs/mcp-readiness.md`, and `npx markdownlint-cli2 --no-globs ':README.md' ':docs/handoff/specs-plans.md' ':docs/specs/archive/README.md' ':docs/usage.md' ':docs/mcp-readiness.md'`.
- [ ] **Scope audit:** No README restructuring, CLI behavior, release-history rewrite, new command, or test/workflow change.
- [ ] Commit: `docs: correct navigation and usage facts`

### Task 41: Regenerate the bug index without quote leakage

**Findings:** F-068

**Files:**

- Modify: `docs/handoff/bugs/_regen_index.py`
- Generate: `docs/handoff/bugs/INDEX.md`
- Create: `tests/test_bug_index_regeneration.py`

- [ ] **RED:** Add single-quoted `bug_id`, date, title, services, and status fixtures; require rendered values without quote or bracket syntax.
- [ ] Run `uv run pytest tests/test_bug_index_regeneration.py -q` and confirm the current subset parser leaks syntax.
- [ ] **GREEN:** Correct only the script's supported frontmatter scalar/list subset; do not add a general YAML engine.
- [ ] Run the focused test, `uv run python docs/handoff/bugs/_regen_index.py`, then prove a second regeneration produces no diff.
- [ ] Run Ruff and BasedPyright on the script/test and validate the generated Markdown with its existing exemption/gates.
- [ ] **Scope audit:** Only the generator, its regression, and deterministic index output may change; preserve handoff layout.
- [ ] Commit: `fix(handoff): parse quoted bug index fields`

### Task 42: Correct frontmatter inference and scope matching

**Findings:** F-070, F-071, F-072, F-073

**Files:**

- Modify: `src/project_standards/format_frontmatter.py`
- Modify: `src/project_standards/frontmatter_commands.py`
- Modify: `src/project_standards/validate_frontmatter.py`
- Modify: `tests/test_format_frontmatter.py`
- Modify: `tests/test_frontmatter_unified_config.py`
- Modify: `tests/test_validate_frontmatter.py`

- [ ] **RED:** Prove `old-docs/research/n.md` is not inferred as research while root/nested `docs/research/` is; disabled references with a custom schema are silent; ADR-only selection inherits ordinary include/exclude constants plus only `.standards/**`; and root `foo.template.md` matches `**/*.template.md`.
- [ ] Run `uv run pytest tests/test_format_frontmatter.py tests/test_frontmatter_unified_config.py tests/test_validate_frontmatter.py -k 'research or disabled or scope or root_glob' -q` and confirm the four boundaries diverge.
- [ ] **GREEN:** Anchor research-path inference, suppress the skip note only when references are disabled, share existing default-scope constants with the ADR-only augmentation, and make the current glob dialect handle root matches.
- [ ] Run all three modules, Ruff, and BasedPyright.
- [ ] **Scope audit:** No new document type, legacy `validate_references.py` behavior change, global `.standards/**` exclusion, or glob-dialect redesign.
- [ ] Commit: `fix(frontmatter): align inference and scope matching`

### Task 43: Delay schema use and improve frontmatter boundaries

**Findings:** F-074, F-075, F-076

**Files:**

- Modify: `src/project_standards/format_frontmatter.py`
- Modify: `src/project_standards/frontmatter_authoring.py`
- Modify: `src/project_standards/validate_id.py`
- Modify: `src/project_standards/validate_frontmatter.py`
- Modify: `tests/test_format_frontmatter.py`
- Modify: `tests/test_frontmatter_authoring.py`
- Verify only: `tests/test_validate_id.py`
- Modify: `tests/test_validate_frontmatter.py`

- [ ] **RED:** Remove/corrupt the bundled schema and prove `--help` still works while actual schema use raises the existing clean configuration error; require explicit UTF-8. Prove empty `---\n---\n# body` reports an empty/non-mapping block. Retain a characterization that `fix_file` imports still work while unified CLI fixes use the platform executor.
- [ ] Run `uv run pytest tests/test_format_frontmatter.py tests/test_frontmatter_authoring.py tests/test_validate_id.py tests/test_validate_frontmatter.py -k 'help or schema or empty or fix_file' -q` and confirm eager loading or the wrong diagnostic.
- [ ] **GREEN:** Load document types at first schema use through the existing error boundary, document `fix_file` as a legacy direct-write library path prohibited in unified execution, and distinguish an empty closed block without changing `parse_frontmatter()`'s `None` contract.
- [ ] Run all four modules, Ruff, and BasedPyright.
- [ ] **Scope audit:** Do not add an unnecessary public constant, delete compatibility writers/tests, route CLI writes backward, or add a new exception hierarchy.
- [ ] Commit: `fix(frontmatter): delay schema use and clarify empty blocks`

### Task 44: Discover canonical catalogs once

**Findings:** F-079, F-085

**Files:**

- Modify: `src/project_standards/package_contract/catalog.py`
- Modify: `src/project_standards/package_contract/cli.py`
- Modify: `src/project_standards/package_contract/projection.py`
- Modify: `tests/package_contract/test_cli.py`
- Modify: `tests/package_contract/test_projection.py`

- [ ] **RED:** Prove noncanonical `05.toml` is rejected or ignored consistently and that validating two canonical majors loads/hashes package families once while comparing each catalog with immutable repository copies.
- [ ] Run `uv run pytest tests/package_contract/test_cli.py tests/package_contract/test_projection.py -k 'canonical or load_once or 05' -q` and confirm duplicated or inconsistent discovery.
- [ ] **GREEN:** Centralize canonical major filename discovery for the command invocation and pass one loaded repository through catalog validation/projection.
- [ ] Run both modules, Ruff, and BasedPyright.
- [ ] **Scope audit:** No cross-command cache, public API, catalog-schema change, or altered immutable comparison.
- [ ] Commit: `fix(packages): load canonical catalogs once`

### Task 45: Correct package-contract invariants and roles

**Findings:** F-080, F-081, F-082, F-083

**Files:**

- Modify comments only: `src/project_standards/package_contract/integrity.py`
- Modify: `src/project_standards/package_contract/graph.py`
- Modify: `src/project_standards/package_contract/discovery.py`
- Verify only: `tests/package_contract/test_integrity.py`
- Modify: `tests/package_contract/test_graph.py`
- Modify: `tests/package_contract/test_discovery.py`

- [ ] **RED:** Prove internal/reference-only entries on another major do not require consumer migration paths, consumer roles still do, and a valid V2 index with more than 4096 bytes of leading blank/comment lines is discovered.
- [ ] Run `uv run pytest tests/package_contract/test_integrity.py tests/package_contract/test_graph.py tests/package_contract/test_discovery.py -k 'role or migration or preamble or pycache' -q` and confirm the behavioral defects.
- [ ] **GREEN:** Filter migration-path requirements by consumer role, scan the bounded V2 preamble line-by-line without a byte ceiling, accurately document the `__pycache__/*.pyc` exemption, and explain duplicated graph checks as defense-in-depth for manually constructed repositories.
- [ ] Run all three modules, Ruff, and BasedPyright.
- [ ] **Scope audit:** Keep safe V1 skipping, payload authority, migration reachability, graph checks, and exemption set unchanged.
- [ ] Commit: `fix(packages): align roles and V2 discovery invariants`

### Task 46: Type catalog output failures

**Findings:** F-084

**Files:**

- Modify: `src/project_standards/package_contract/cli.py`
- Modify: `tests/package_contract/test_cli.py`

- [ ] **RED:** Require output-path and output-write `OSError` cases to produce `bad_output`, while unrelated errors containing the word “output” remain `catalog_error`.
- [ ] Run `uv run pytest tests/package_contract/test_cli.py -k 'bad_output or catalog_error' -q` and confirm message sniffing.
- [ ] **GREEN:** Add a private typed output-path failure and classify only output-write `OSError` explicitly.
- [ ] Run the focused module, Ruff, and BasedPyright.
- [ ] **Scope audit:** No public exception, message change, or other command-code change.
- [ ] Commit: `fix(packages): type catalog output failures`

### Task 47: Cut CLI Documentation 1.2

**Findings:** F-086

**Files:**

- Create: `standards/cli-documentation/versions/1.2/**`
- Modify: `standards/cli-documentation/standard.toml`
- Modify only as required by the new version: `standards/cli-documentation/README.md`, `standards/cli-documentation/adopt.md`, `standards/cli-documentation/agent-summary.md`
- Generate: `src/project_standards/payloads/cli-documentation/1.2/**`
- Generate/update: `catalogs/5.toml`, `standards/catalog.md`, `.standards/catalog.toml`, `.standards/lock.toml`
- Modify: `tests/package_contract/test_cli_documentation_reconstruction.py`
- Modify: `tests/package_contract/test_projection.py`
- Modify only deterministic compatibility expectations: `tests/package_compatibility/matrix.py`

- [ ] **RED:** Require the already SHA-pinned setup-uv line in the 1.2 provider to carry trailing `# v8.3.2`, retain current major tags for GitHub-owned actions, and keep CLI Documentation 1.1 advertised and exactly selectable after 1.2 becomes the default.
- [ ] Run `uv run pytest tests/package_contract/test_cli_documentation_reconstruction.py tests/package_contract/test_projection.py -k 'setup_uv or reconstruction or projection' -q` and confirm 1.2 is absent.
- [ ] **GREEN:** Clone 1.1 into 1.2 and make that one provider-byte correction, then advance the compatible default and generate required consequences.
- [ ] Run the focused tests and the Payload task gate.
- [ ] Run `git diff --exit-code v5.0.2 -- standards/cli-documentation/versions/1.1`.
- [ ] **Scope audit:** Keep `actions/checkout@v7`, `actions/setup-python@v6`, the absent create-only workflow, and every Python/Markdown Tooling payload untouched.
- [ ] Commit: `fix(cli-documentation): annotate setup-uv pin`

### Task 48: Correct spec diagnostics and structural anchors

**Findings:** F-089, F-092, F-093, F-094

**Files:**

- Modify: `src/project_standards/specs/commands/validate.py`
- Modify: `src/project_standards/specs/config.py`
- Modify: `src/project_standards/specs/registry.py`
- Modify: `src/project_standards/specs/document.py`
- Modify: `tests/test_spec_validate.py`
- Modify: `tests/test_spec_config.py`
- Modify: `tests/test_spec_registry.py`
- Modify: `tests/test_spec_document.py`

- [ ] **RED:** Require undeclared canonical prefixes to name the missing Appendix A declaration, malformed `reference_prefixes` to name that field, a closing fence at EOF to terminate masking, and valid anchors from H1/H5/H6 outside fences while H2-H4 remain numbered sections.
- [ ] Run `uv run pytest tests/test_spec_validate.py tests/test_spec_config.py tests/test_spec_registry.py tests/test_spec_document.py -k 'prefix or appendix or fence or anchor or heading' -q` and confirm inaccurate diagnostics or structure.
- [ ] **GREEN:** Correct only the diagnostic labels, finish the EOF fence span, and collect H1-H6 for anchor slugs through Task 8's masked structural view while retaining H2-H4 section parsing.
- [ ] Run all four modules, Ruff, and BasedPyright.
- [ ] **Scope audit:** Do not duplicate fence masking, change validation rules/config shape, or promote H1/H5/H6 into numbered sections.
- [ ] Commit: `fix(spec): align diagnostics and structural anchors`

### Task 49: Share spec-new option resolution

**Findings:** F-090, F-091

**Files:**

- Modify: `src/project_standards/specs/cli.py`
- Modify: `tests/test_spec_new.py`
- Modify: `tests/test_spec_new_cli.py`
- Modify: `tests/test_spec_new_discovery.py`
- Modify: `tests/test_spec_selected_routing.py`

- [ ] **RED:** Characterize matching legacy/selected field and ID resolution, require self-validation to reuse the already-loaded legacy config, and prove the selected-write tail is unreachable.
- [ ] Run `uv run pytest tests/test_spec_new.py tests/test_spec_new_cli.py tests/test_spec_new_discovery.py tests/test_spec_selected_routing.py -k 'resolution or loaded_config or selected' -q` and confirm duplicated resolution or reload.
- [ ] **GREEN:** Extract the narrow shared field/ID resolution, pass the loaded config through self-validation, and delete only the unreachable tail.
- [ ] Run all four modules, Ruff, and BasedPyright.
- [ ] **Scope audit:** No ID grammar, provider call, JSON output, or write-authorization change.
- [ ] Commit: `fix(spec): share new-command option resolution`

---

## Phase 6: Test hermeticity, repository CI, and 5.1 integration

### Task 50: Add the verified test return annotations

**Findings:** F-097

**Files:**

- Modify: `tests/test_format_frontmatter.py`
- Modify: `tests/test_id_format.py`
- Modify: `tests/test_precommit_hooks.py`
- Modify: `tests/test_spec_document.py`

- [ ] **RED inventory:** Count the 42 verified missing test-function return annotations and the stale filename comment; record the exact pre-edit count.
- [ ] **GREEN:** Add exactly 42 `-> None` annotations and remove only that comment.
- [ ] Run Ruff format/check, BasedPyright, and `uv run pytest tests/test_format_frontmatter.py tests/test_id_format.py tests/test_precommit_hooks.py tests/test_spec_document.py -q`.
- [ ] Recount to prove no listed test function remains unannotated and no unrelated annotation changed.
- [ ] **Scope audit:** No future-annotations import, test cleanup, rename, or behavior change.
- [ ] Commit: `test: annotate verified test return types`

### Task 51: Anchor all verified repository fixtures

**Findings:** F-098

**Files:**

- Modify exactly these 12 modules:
  - `tests/test_usage_doc_inventory.py`
  - `tests/test_installed_wrappers.py`
  - `tests/control_plane/helpers.py`
  - `tests/control_plane/test_bootstrap.py`
  - `tests/control_plane/test_distribution.py`
  - `tests/control_plane/test_cli.py`
  - `tests/control_plane/test_end_to_end.py`
  - `tests/control_plane/test_migration.py`
  - `tests/test_frontmatter_unified_config.py`
  - `tests/package_contract/test_projection.py`
  - `tests/package_contract/test_public_provider_routing.py`
  - `tests/agent_handoff/test_selected_routing.py`

- [ ] **RED:** From a foreign temporary working directory, invoke `uv run --project /home/chris/projects/project-standards pytest` over the 12 modules and record every genuine repository-fixture failure.
- [ ] **GREEN:** Anchor only paths that are opened as repository fixtures. Preserve deliberately relative paths embedded in generated subprocess code and pure unopened relative `Path` values.
- [ ] Repeat the foreign-CWD command, then run Ruff and BasedPyright on the 12 files.
- [ ] **Scope audit:** The diff contains exactly the listed modules and only path anchoring needed by the failing inventory.
- [ ] Commit: `test: anchor repository fixtures independently of cwd`

### Task 52: Isolate Git-spawning tests from user configuration

**Findings:** F-099

**Files:**

- Modify: `tests/agent_handoff/test_hook.py`
- Modify: `tests/package_contract/test_release.py`
- Modify: `tests/package_contract/test_cli.py`

- [ ] **RED:** Run the three modules with a temporary global Git config containing `commit.gpgsign=true`; confirm the relevant Git subprocesses inherit hostile user state.
- [ ] **GREEN:** Give each relevant subprocess isolated global/system configuration through its test environment, without changing the real user config or product code.
- [ ] Rerun the hostile-config command, then Ruff and BasedPyright on the three modules.
- [ ] **Scope audit:** No product code, workstation configuration, unrelated subprocess, or signing-policy change.
- [ ] Commit: `test: isolate git subprocess configuration`

### Task 53: Reuse the exact candidate wheel in compatibility CI

**Findings:** F-100

**Files:**

- Modify: `.github/workflows/check.yml`
- Modify: `tests/test_repository_test_gate.py`
- Read-only contract: `tests/package_compatibility/conftest.py`

- [ ] **RED:** Add a workflow regression proving exactly one wheel is selected after the existing build, exported through `PROJECT_STANDARDS_COMPATIBILITY_WHEEL`, used for extraction, and available before the compatibility step.
- [ ] Run `uv run pytest tests/test_repository_test_gate.py -q` and confirm the workflow never exports the prebuilt artifact.
- [ ] **GREEN:** Add a bounded shell step that fails unless exactly one candidate wheel exists, writes its absolute path to `GITHUB_ENV`, and uses that exact path. Keep the existing fixture unchanged.
- [ ] Build one wheel into a fresh temporary artifact directory, set `PROJECT_STANDARDS_COMPATIBILITY_WHEEL` to its exact path, and run `uv run pytest -m compatibility -n 4 --dist load --max-worker-restart=0`.
- [ ] Run Prettier on the workflow and the focused pytest again.
- [ ] **Scope audit:** Repo-local CI only. No Python Tooling payload, fixture redesign, wildcard passed to pytest, second wheel build, trigger, or job redesign.
- [ ] Commit: `fix(ci): reuse exact wheel for compatibility tests`

### Task 54: Prepare 5.1.0 and run the retained release gate

**Findings:** No new finding; deterministic integration of all preceding correction tasks

**Files:**

- Modify: `pyproject.toml`
- Regenerate: `uv.lock`
- Modify: `CHANGELOG.md`
- Regenerate: `.standards/catalog.toml`
- Regenerate: `.standards/lock.toml`
- Modify deterministic fixture: `tests/fixtures/package_contract/valid/full/expected/catalog.toml`
- Modify: `docs/STATUS.md`
- Modify: `docs/handoff/state.md`
- Modify: `docs/handoff/specs-plans.md`
- Append concise truthful checkpoint: `docs/handoff/sessions/2026-07.md`
- Verify without modifying: `.python-version`, released payload directories, `docs/handoff/deployed.md`

- [ ] **Scope start:** Confirm every earlier task is committed, the tracked tree is clean, the only known untracked evidence remains `docs/reviews/`, and the ledger has no open accepted finding.
- [ ] Set the project version to 5.1.0, run `uv lock`, and move only this correction train from `[Unreleased]` into a dated 5.1.0 changelog section whose rationale is MINOR.
- [ ] Render Catalog 5 consumer metadata for tool release 5.1.0 and apply the local dogfood reconciliation so `.standards/lock.toml` is canonical lock schema 1.1 with the four new consumer defaults. Standard Bundle Authoring 2.2 remains advertised as internal and is not selected into the consumer lock.
- [ ] Update status/handoff text to say “prepared and verified, unpublished.” Do not add 5.1.0 to `docs/handoff/deployed.md` before publication.
- [ ] Assert `.python-version` is `3.14` and `pyproject.toml` retains `requires-python = ">=3.14"`.
- [ ] Run `uv run project-standards packages check-release --root . --baseline v5.0.2 --json` and require classification `minor`.
- [ ] Prove all old payloads are unchanged and exactly the five approved new version directories exist. Prove no new Python Tooling or Markdown Tooling payload was created.
- [ ] Run the complete pre-commit gate and immutable/version inventory below from one fresh build and extracted candidate wheel.
- [ ] **Scope audit:** Compare the complete branch diff with `v5.0.2`; every path must map to the ledger or a named deterministic release consequence. Remove anything else.
- [ ] Create a signed commit: `release: prepare project standards 5.1.0`.
- [ ] Run the post-commit signature, status, and parity proof below; the tracked tree must now be clean.
- [ ] Stop. Do not tag, move `v5`, push a release commit to `main`, or publish GitHub assets without explicit owner authorization after reviewing the gate evidence.

## Complete retained 5.1.0 pre-commit gate

Use fresh temporary artifact/runtime directories so stale builds cannot satisfy the gate:

```bash
uv sync --locked --all-groups
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
npm ci
npx prettier --check .
npx markdownlint-cli2

release_artifacts="$(mktemp -d)"
wheel_runtime="$(mktemp -d)"
uv build --out-dir "$release_artifacts"
mapfile -t candidate_wheels < <(find "$release_artifacts" -maxdepth 1 -type f -name 'project_standards-5.1.0-*.whl' -print)
test "${#candidate_wheels[@]}" -eq 1
candidate_wheel="${candidate_wheels[0]}"
uv run python -m zipfile -e "$candidate_wheel" "$wheel_runtime"
export PYTHONPATH="$wheel_runtime"
export PROJECT_STANDARDS_COMPATIBILITY_WHEEL="$candidate_wheel"

uv run project-standards standards validate-packages --root . --json
uv run project-standards standards validate-graph --root . --require-all-manifests --json
uv run project-standards standards generate-package-schemas --root . --check
uv run project-standards standards sync-payload-projection --root . --check
uv run project-standards standards render-catalog --root . --check
uv run project-standards packages check-release --root . --baseline v5.0.2 --json

uv run coverage erase
uv run coverage run --source=project_standards -m pytest -m "not performance and not compatibility"
uv run pytest -m compatibility -n 4 --dist load --max-worker-restart=0
uv run pytest -m performance
uv run coverage report
uv run pytest tests/coherence -q
uv run pip-audit

uv run project-standards validate
uv run project-standards agent-handoff validate --repo . --json
git diff --check
```

The ordinary suite contains source/direct-wheel/sdist-derived-wheel parity and package reconstruction coverage. Confirm its build-parity tests actually ran rather than relying only on the aggregate exit code.

Then run the explicit immutable/version inventory:

```bash
git diff --exit-code v5.0.2 -- \
  standards/adr/versions/1.1 \
  standards/agent-handoff/versions/1.1 \
  standards/cli-documentation/versions/1.1 \
  standards/markdown-frontmatter/versions/1.2 \
  standards/markdown-tooling/versions/1.2 \
  standards/project-spec/versions/1.1 \
  standards/python-coding/versions/0.5 \
  standards/python-tooling/versions/1.1 \
  standards/standard-bundle-authoring/versions/2.0 \
  standards/standard-bundle-authoring/versions/2.1

diff -u \
  <(
    {
      git ls-tree -d -r --name-only v5.0.2 standards | rg '/versions/[^/]+$'
      printf '%s\n' \
        standards/agent-handoff/versions/1.2 \
        standards/cli-documentation/versions/1.2 \
        standards/markdown-frontmatter/versions/1.3 \
        standards/project-spec/versions/1.2 \
        standards/standard-bundle-authoring/versions/2.2
    } | sort -u
  ) \
  <(find standards -mindepth 3 -maxdepth 3 -type d -path '*/versions/*' -print | sort)
```

Expected pre-commit result: all commands pass; release classification is `minor`; the candidate wheel is exactly version 5.1.0; the old payload diff is empty; and only the five approved new payload directories appear beyond the `v5.0.2` inventory. The remaining tracked diff is exactly the allowlisted Task 54 release metadata.

After the signed preparation commit, run:

```bash
git show --show-signature --no-patch --format=fuller HEAD
git status --short --branch
git diff --check HEAD^
```

Expected post-commit result: the signature is good, the tracked tree is clean, the commit diff passes `git diff --check`, and `docs/reviews/` remains untracked and unchanged.

## Completion checklist

- [ ] All 96 accepted/adjusted findings have a focused correction and green regression.
- [ ] F-020, F-077, F-087, and F-095 have no diff and no queue item.
- [ ] Every task's final diff matched its allowlist; the branch-wide diff contains no feature, opportunistic cleanup, or unrelated file.
- [ ] Python 3.14+ is the tool and consumer floor everywhere this train touches.
- [ ] Lock 1.0 reads and successful writes emit lock 1.1 without resurrecting deleted create-only content.
- [ ] Exactly five new payloads reconstruct and project; every released payload remains immutable.
- [ ] The exact prebuilt candidate wheel drives the four-worker compatibility phase.
- [ ] The extracted-wheel, package-contract, ordinary, compatibility, performance, coverage, coherence, formatting, lint, typing, audit, dogfood, and Agent Handoff gates pass.
- [ ] Project version and prepared release metadata say 5.1.0; hosted publication remains intentionally unperformed pending owner authorization.
