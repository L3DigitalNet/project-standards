Claude Code note: consider using the `superpowers:receiving-code-review` skill.

# Codex Review Orchestrator Plan

## Review Orchestrator Metadata

- repo_root: `/home/chris/projects/project-standards`
- repo_name: `project-standards`
- mode: manual readiness and housekeeping sweep
- budget: deep
- scope: repository-wide, with emphasis on work required before SPEC-MT01 Step 07
- current_branch: `testing`
- head_commit: `85b3b029d00c2ee8a0bd51b7147a5baae2679a41`
- working_tree_state: clean at review start
- execution_profile_used: main-session only; repository policy did not authorize a multi-child sweep
- search_enabled: local repository and read-only GitHub state
- codex_cli_mode: interactive
- orchestrator_version: `1.0`

## Disposition

Do not start Step 07 yet. The implementation is healthy, but the roadmap requires `SPEC-MT01` traceability to be complete before Step 07 starts. The controlling spec still shows all FR-001 through FR-022 rows as `Not Started`, all Definition-of-Done and documentation-deliverable boxes unchecked, four blocking open questions open, and its placeholder deviation row pending.

Once the pre-Step-07 reconciliation items below are complete, Step 07 can begin. Step 07 itself should produce the readiness report and decide whether any remaining advisory debt is blocking.

## Pre-Step-07 Findings

### PS-001 — SPEC-MT01 traceability is not complete

- severity: blocker
- evidence:
  - `SPEC-RD01` Step 07 says `SPEC-MT01` traceability must be complete before starting.
  - `SPEC-MT01` §17.3 still marks FR-001 through FR-022 `Not Started`.
  - §17.1 and §18.7 still have no completed checklist items.
  - OQ-001, OQ-003, OQ-007, and OQ-008 remain blocking and open even though the implemented manifest/graph design appears to answer them.
  - DEV-001 remains a pending placeholder rather than an explicit no-deviation closure.
- action:
  - Map every requirement to the actual test, command, ADR, and document evidence.
  - Resolve or explicitly defer every open question and deviation.
  - Check only items supported by current evidence; leave the readiness-report item for Step 07.

### PS-002 — Standard Bundle Authoring has live contract drift

- severity: important
- evidence:
  - Its purpose text still says there are eight bundles and six packaged artifact manifests; the repository now has nine bundles and seven packaged artifact manifests after Agent Handoff landed.
  - Its own `standard.toml` says graph validation is future Step 04 work.
  - FR-013 requires each active standard to provide an agent summary or explain why it does not. Only Agent Handoff ships `agent-summary.md`; Python Coding records an explicit rationale. The other active standards do neither, and no conformance test enforces the requirement.
  - The manual authoring checklist does not ask for the FR-013 summary-or-rationale decision.
- action:
  - Reconcile the standard, template, example, and checklist with ADRs 0017-0022 and the current nine-bundle repository.
  - Decide whether a manifest `summary` satisfies FR-013. If not, add compact summaries or explicit rationale and a test.

### PS-003 — Required v5 release and migration documentation is incomplete

- severity: important
- evidence:
  - `[Unreleased]` records Agent Handoff and artifact lifecycle work but omits the Standard Bundle Authoring standard, `standard.toml` model/schema, graph validator, provider runner, composition fixtures, and generated catalog.
  - SPEC-MT01 §18.7 requires an `UPGRADING.md` or migration note for manifest introduction. The v5 section currently documents only Agent Handoff migration.
- action:
  - Add classified v5 changelog entries for the SPEC-MT01 Steps 02-06 surfaces.
  - Add the manifest/graph migration posture to `UPGRADING.md`, including an explicit no-action statement where consumers are unaffected.

### PS-004 — The broad Markdown workflows are currently red on `testing`

- severity: important
- evidence:
  - `npx prettier --check .` fails on two files under `docs/future-standards/`.
  - `npx markdownlint-cli2 "**/*.md"` reports 463 errors, all under four `docs/future-standards/` files.
  - Those files are absent from `main`, so the last green `main` workflows do not exercise this branch-only backlog. A future `testing` to `main` pull request will run the broad workflows against it.
- action:
  - Either repair the future-standard drafts or explicitly exclude that archival/incubator tree from both Prettier and markdownlint with a documented ownership rationale.
  - Re-run the actual workflow commands before Step 07 declares existing non-MCP workflows green.

### PS-005 — Graph/catalog enforcement is indirect and must be stated honestly

- severity: moderate
- evidence:
  - `scripts/check.py` and `.github/workflows/check.yml` do not invoke `validate-graph` or `render-catalog --check` explicitly.
  - The normal pytest run does execute current-repo graph and catalog freshness tests, so the present full gate is enforcing both indirectly.
  - SPEC-MT01 FR-011's traceability text says the CI/check script includes graph validation.
- action:
  - Either document the pytest tests as the intentional gate integration or add explicit commands to the local/CI gates and their byte-identical packaged twin.
  - Prefer an explicit command if operators should see a graph-specific failure before the full test suite.

## Step 07 Deliverables

These belong inside Step 07 rather than before it:

- Produce the Markdown and/or JSON MCP-readiness report required by IR-006 and FR-019.
- Prove the graph has no findings, the catalog is fresh, and no hidden hard dependency exists.
- Record non-blocking advisory gaps separately from blockers.
- Complete the remaining SPEC-MT01 Definition of Done, documentation checklist, and requirement traceability from current evidence.
- Move SPEC-MT01 from draft to its approved/completed lifecycle state only after owner review.
- Update `docs/STATUS.md`, `docs/TODO.md`, handoff pointers, and the session record with the readiness outcome. Do not start MCP server code during this step.

## Housekeeping Findings

### HK-001 — Handoff pointers and ledgers contain stale completion text

- severity: moderate
- evidence:
  - `docs/handoff/specs-plans.md` says only the old `check` plan survives, while ten plan files are present.
  - Its Step 05 row says eight standards and says Step 06 remains; the repository now has nine standards and Step 06 is complete.
  - Its Step 06 row still says `this closeout` rather than commit `39b9f76`.
  - The Step 06 plan is implemented but every task checkbox remains unchecked.
  - The Agent Handoff retirement inventory still calls `testing` dirty and describes the package as living on a feature branch; current `testing` is clean and integrated.
  - Session rows still contain `this commit`/`this closeout` placeholders. Because session logs are append-only, decide whether to preserve these as historical debt or add a compact correction row rather than rewriting history.
- action: reconcile current pointers and add only append-safe corrections to session history.

### HK-002 — Agent Handoff dogfood is green but noisy

- severity: moderate
- evidence:
  - `agent-handoff validate` exits 0 with no errors.
  - `size-report` emits two warnings for `AGENTS.md` and `CLAUDE.md` exceeding advisory targets.
  - `shape-check` emits 129 warnings, primarily grandfathered June/July session rows.
  - Three warnings are false positives: the `docs/handoff/bugs/*.md` policy applies bug-record sections (`Cause`, `Fix`, `Lesson`) to `bugs/INDEX.md`, although the standard defines the index as a different document shape.
- action:
  - Fix the policy/validator so `INDEX.md` is not treated as a numbered bug record and add a regression test.
  - Decide whether historical session rows are intentionally grandfathered. Avoid rewriting append-only history merely to silence advisory warnings.
  - Trim the instruction files only if doing so preserves this repo's self-contained contract.

### HK-003 — Remote issue and pull-request state is stale

- severity: moderate
- evidence:
  - Issue #3 remains open even though F1-F4 shipped in v4.1.0 and F5 shipped in v4.2.0.
  - Draft PR #4 is merge-dirty and superseded by the already-released implementation.
  - Dependabot PR #1 (`setup-node` v4 to v6) is green but unresolved.
  - Dependabot PR #2 (`checkout` v6 to v7) fails because Dependabot updated workflows without updating the byte-identical Python Tooling bundle/scaffold surfaces.
- action:
  - Close issue #3 and PR #4 with links to the shipped commits/releases.
  - Review PR #1 for the v5 line.
  - Handle checkout v7 as a coordinated source/bundle/doc parity update, then supersede or close PR #2.

### HK-004 — GitHub settings work is real and still outstanding

- severity: moderate
- evidence:
  - The active `main` ruleset prevents deletion, non-fast-forward updates, and unsigned commits.
  - It does not require pull requests, approvals, or status checks.
  - No branch-protection object exists outside the ruleset.
  - The TODO's candidate check labels do not exactly match all displayed check names. Current jobs display `check`, `coherence`, `Prettier`, `Markdown`, `Frontmatter`, and `Specs`.
- action:
  - Apply required checks/review policy only with owner approval, as already recorded.
  - Use observed check contexts rather than guessed lowercase workflow labels.

### HK-005 — Task queue cleanup and design questions remain

- severity: low
- evidence:
  - `docs/TODO.md` contains a blank user checkbox that should not be deleted without owner confirmation.
  - The root-file consolidation question for Python Tooling and Markdown Tooling is still unanswered. Several destinations are tool-required (`.github/workflows/`, `.vscode/`) or conventionally root-discovered (`pyproject.toml`, `.editorconfig`, Prettier/markdownlint config), so any consolidation requires a per-artifact compatibility analysis.
  - The `spec new` symlinked-parent and OpenAPI pin items remain explicitly non-blocking.
- action: preserve user intent, clarify the blank task, and schedule the root-artifact design analysis separately from Step 07.

### HK-006 — Hosted CI has no evidence for the current v5 branch

- severity: moderate
- evidence:
  - `testing` is 111 commits ahead of `main` and synchronized with `origin/testing`.
  - Push workflows run on `main`, and there is no open `testing` to `main` pull request.
  - Recent hosted runs therefore validate released `main`, not the current v5 branch.
- action: obtain a hosted pull-request or equivalent workflow run before the readiness gate is declared complete or before release promotion.

## Verification Evidence

Passed during this review:

- `uv run python scripts/check.py`: Ruff format/check, BasedPyright, 1,368 tests, 94% branch coverage, and pip-audit.
- `project-standards standards validate-graph --require-all-manifests --json`: zero findings.
- `project-standards standards render-catalog --check`: fresh.
- managed frontmatter validation and format check: pass.
- project-spec validation and strict lint: pass.
- Agent Handoff drift check: zero findings; full validation: zero errors with advisory warnings.
- `uv lock --check`, `npm audit`, and `git diff --check`: pass.
- worktree and `origin/testing` synchronization: clean.

Known red checks:

- broad Prettier: two future-standard draft files.
- broad markdownlint: 463 findings, all in `docs/future-standards/`.

## Repo Scan Summary

- primary_repo_pattern: `library-cli-tooling`
- secondary_repo_patterns: `meta-repo`, `mcp-agent-tool`, `ai-prompt-workflow`
- language_signals: Python, shell
- framework_signals: pytest, CLI tooling, agent workflow, planned MCP
- artifact_signals: ADRs, conventions, GitHub Actions, generated catalog, tests
- sensitivity_signals: scanner hits are fixture/document vocabulary, not evidence of sensitive runtime data
- deployment_signals: GitHub Actions and package release tags
- packaging_signals: Python wheel plus copy-adopt artifacts
- nested_repo_signals: none
- existing_review_artifacts: prior spec/plan reviews through 2026-07-07
- unknowns_that_reduce_confidence: none for local readiness; hosted CI is absent for `testing`

## Conventions Inputs

- conventions_inputs_found: `docs/handoff/conventions.md`, standard-packaged handoff conventions
- conventions_maturity: high, with stale handoff and warning debt
- likely_convention_heavy_reviews: conventions, documentation/runbook, architecture boundary
- missing_conventions_hotspots: no explicit policy for grandfathering migrated session-shape debt

## Available And Missing Review Skills

- available_review_skills: architecture boundary, conventions, documentation/runbook, test suite, comprehensive code, dependency supply chain, CI/CD, release readiness, MCP/agent tool boundary
- missing_review_skills: none required for the selected local sweep

## Run Now

### release-readiness-review

- canonical_prompt: `perform a release readiness review`
- applicable: yes
- expected_value: critical
- confidence: high
- run_recommendation: run_now
- default_execution_group: delivery-and-runtime
- why_selected_or_skipped: Step 07 is a hard readiness gate and v5 release work is active.
- key_signals: release freeze, draft traceability, green local gate, red broad Markdown workflows
- blocking_unknowns: hosted CI for `testing`
- latest_existing_report: none specific to the current 111-commit v5 delta

### documentation-and-runbook-review

- canonical_prompt: `perform a documentation review`
- applicable: yes
- expected_value: high
- confidence: high
- run_recommendation: run_now
- default_execution_group: repo-shape-and-intent
- why_selected_or_skipped: controlling specs, handoff ledgers, changelog, and upgrading guide drift.
- key_signals: incomplete traceability, stale counts, missing migration notes
- blocking_unknowns: none
- latest_existing_report: no current repository-wide documentation review

### test-suite-review

- canonical_prompt: `perform a test review`
- applicable: yes
- expected_value: high
- confidence: high
- run_recommendation: run_now
- default_execution_group: broad-integrative
- why_selected_or_skipped: Step 07 depends on exact requirement-to-test mapping.
- key_signals: 1,368 passing tests, indirect graph/catalog gate, missing FR-013 conformance test
- blocking_unknowns: none
- latest_existing_report: no current requirement-traceability review

## Consider Next

- `ci-cd-review`: hosted `testing` coverage, required-check names, and coordinated action updates.
- `dependency-supply-chain-review`: unresolved action upgrades and release-time audit posture.
- `conventions-review`: Agent Handoff false-positive/warning policy and append-only history.
- `mcp-and-agent-tool-boundary-review`: run after Step 07, before implementation work begins.

## Not Applicable

- frontend, desktop packaging, data migration, retrieval, background-job, observability, and performance reviews lack meaningful runtime signals for this repository.

## Execution Order

- 1: documentation-and-runbook-review
- 2: release-readiness-review
- 3: ci-cd-review
- 4: test-suite-review
- 5: conventions-review

## Planning Risks And Unknowns

- missing_evidence_that_could_change_prioritization: hosted CI on `testing`
- environment_limitations: multi-child orchestration not authorized by repository policy
- search_or_profile_limitations: GitHub checks were read-only; no settings or issue state changed

## Claude Handoff

- highest_value_reviews_to_run_first: SPEC-MT01 traceability/documentation, then readiness/CI
- reviews_likely_to_change_conventions: conventions and documentation/runbook
- reviews_to_revisit_after_major_changes: MCP/agent tool boundary after Step 07
- follow_up_questions_for_human_if_needed: whether advisory agent-summary gaps are release-blocking; whether to repair or exclude `docs/future-standards/`; approval for GitHub ruleset changes
