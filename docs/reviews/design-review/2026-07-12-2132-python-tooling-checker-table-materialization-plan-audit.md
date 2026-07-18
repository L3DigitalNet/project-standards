# Python Tooling Checker Table Materialization Plan Audit — Round 2

## Executive summary

Four of the five round-1 findings are resolved. The scratch import boundary, real-payload lifecycle coverage, complete repository gate, and intermediate-schema matrix now match the repository and the amended design.

CR-001 is only partially resolved. The plan now provisions the Pyright wrapper's npm runtime before the oracle, but the oracle still sets only `UV_OFFLINE=1`; it does not force npm offline or otherwise prevent the wrapper from downloading during the supposedly network-isolated assertion. Two new non-blocking integration gaps were found: the exact Pyright pin is not carried into the later migration contract, and Task 6 modifies handoff state without running the repository's Agent Handoff conformance gates.

New internet research was required to verify how npm exposes strict offline mode. Official npm documentation confirms that `npm_config_offline=true` forces installs to make no network requests, while the plan currently supplies no corresponding npm constraint.

## Verdict

Needs major correction before execution

## Audit loop status

- Audit type: Follow-up audit
- Plan path: `docs/superpowers/plans/2026-07-12-python-tooling-checker-table-materialization.md`
- Prior audit issue count: 5
- Resolved issue count: 4
- Still open issue count: 0
- Partially resolved issue count: 1
- New issue count: 2
- Regression count: 0
- Significant findings remaining: Yes

## Adversarial review performed

- Re-read the committed plan, the amended originating design, the round-1 audit ledger, and the exact `ab23e61` reconciliation diff.
- Retested CR-001 under the same fresh-worker and empty-cache threat model, distinguishing setup-phase provisioning from enforcement during the oracle itself.
- Traced the `PYTHONPATH` seam through the import probe, generated subprocess environment, coverage lifecycle, and post-gate coverage JSON assertion.
- Mapped the new real-payload transition and disable/re-enable requirements to existing control-plane config editing, planner unit actions, TOML content, and central-lock models.
- Compared the expanded Task 6 commands to `AGENTS.md`, the check/coherence/graph workflows, the repository runner, and the Agent Handoff closeout contract.
- Rechecked every prohibited intermediate schema shape against the proposed exact-object validator and the current default-recursion boundary.
- Attacked the pinned dependency's later migration path through `additional_dev_dependencies`, provider-derived dev-group rendering, and the still-pending parallel-coverage Tasks 9 and 11 amendment.
- Did not execute tests, dependency resolution, Pyright provisioning, npm installation, generators, or formatters because those operations write caches or repository artifacts and are reserved for implementation.

## Prior findings status

### CR-001: The locked Pyright dependency does not create an offline executable

- Previous severity: High
- Current status: Partially resolved
- Evidence: Task 5 now correctly identifies the PyPI package as a runtime-installing wrapper, pins the wrapper exactly, provisions it in `.github/workflows/check.yml` immediately after `uv sync`, and treats that warm as setup rather than offline evidence (`plan:736-757`). However, the oracle environment at `plan:802-808` sets only `UV_OFFLINE=1`. The same plan explicitly acknowledges at line 738 that this variable does not govern the wrapper's npm download. The preflight `uv run {checker} --version` at lines 809-823 can therefore repopulate a missing Pyright cache from npm and pass instead of producing the promised missing-provision diagnostic. Official npm configuration documentation confirms that npm's own `offline` setting is what prevents network requests during install.
- Remaining action for the authoring agent: Make the oracle's isolation claim executable. At minimum, pass npm's strict offline configuration to the checker probe and generated gate, and use one explicit Pyright cache location shared by CI provisioning and the oracle. If the contract intends actual process-level network isolation rather than package-manager isolation, specify and validate that mechanism. Update the amended design's `UV_OFFLINE=1` wording at the same time.

### CR-002: The scratch `src/` package is not installed in the selected uv project

- Previous severity: High
- Current status: Resolved
- Evidence: The plan now states that the oracle uses the root locked tools rather than proving consumer dependency installation, sets `PYTHONPATH` to the scratch `src` directory, performs an explicit `import consumer_pkg` probe under the inherited environment, and asserts that coverage JSON contains `src/consumer_pkg/__init__.py` (`plan:798-854`). Those checks close both the original import failure and the validation-false-positive path where tests pass without exercising scratch source.
- Remaining action for the authoring agent: None.

### CR-003: Mandatory real checker lifecycle coverage is replaced by a generic fixture

- Previous severity: High
- Current status: Resolved
- Evidence: Task 4 now adds real Python Tooling cycles parameterized over both starting selections, checks pyproject content and exact checker lock scopes through `_assert_checker_state`, requires REMOVE and CREATE unit actions on each flip, and requires convergence after each state (`plan:666-704`). It also requires a real disable/re-enable proof retaining the non-default Pyright selection. `set_standard_enabled` preserves unrelated config bytes in `control_plane/config_edit.py:197-233`, so the retained-selection test is compatible with the actual edit path.
- Remaining action for the authoring agent: None.

### CR-004: Task 6 omits mandatory repository and package-contract gates

- Previous severity: High
- Current status: Resolved
- Evidence: Task 6 now includes generated-schema and projection checks, live package and graph validation, focused suites, Ruff, BasedPyright, pip-audit, `npm ci`, coherence, managed-Markdown validation, and the repository runner (`plan:891-908`). It also explicitly points to the workflow's catalog freshness command. These cover the omitted repository and package-contract gates identified in round 1.
- Remaining action for the authoring agent: None for CR-004; the separate Agent Handoff closeout omission is recorded as CR-NEW-002.

### CR-005: Static-validation tests cover only one rejected intermediate shape

- Previous severity: Medium
- Current status: Resolved
- Evidence: The rejection test is now parameterized across nullable type, `anyOf`, `oneOf`, `allOf`, `$ref`, and missing-type intermediates (`plan:280-312`), while the direct object positive case remains. Every design-named traversal boundary is represented.
- Remaining action for the authoring agent: None.

## New blocking issues

None found.

## New non-blocking issues

### CR-NEW-001: The exact Pyright pin is lost at the pending atomic migration

- Severity: Medium
- Status: Confirmed
- Adversarial angle: Followed the new exact wrapper requirement beyond Task 5 into the release-integration contract that will replace the root dependency group.
- Plan reference: Pinned wrapper file map and Task 5, lines 33-34 and 736-748; release ownership boundary, lines 23 and 933; Task 6 handoff, line 912.
- Finding: Task 5 creates an exact root requirement such as `pyright==X`, but the amended design and pending coverage integration still say only to add `pyright` through `additional_dev_dependencies`. Python Tooling owns the entire dev-group unit, so the later provider-derived pre-alignment and atomic migration will replace the root array. If Tasks 9 and 11 carry the bare name, the exact pin introduced to make runtime provisioning deterministic disappears when `uv.lock` is refreshed.
- Repository evidence: The current provider appends `additional_dev_dependencies` verbatim in `standards/python-tooling/versions/1.1/providers/python_tooling.py:91-100`. The design's release integration at `design:122` names `pyright` without requiring the resolved exact requirement string. The parallel-coverage plan has not yet been amended, and current release-candidate dependency arrays contain no Pyright requirement. The checker plan explicitly defers these writes to that later amendment.
- External research evidence: Not applicable.
- Why it matters: The checker plan can land safely before the atomic migration, but its deterministic provisioning contract will be undone at release unless the cross-plan handoff carries the exact requirement. A lock refresh alone resolves whatever version is current at that later time rather than preserving the reviewed wrapper/runtime pair.
- Recommended action for the authoring agent: Make Task 5's resolved exact requirement a named release-integration output. Amend the checker plan and design handoff so coverage Tasks 9 and 11 must put that exact string, not a bare `pyright`, in both migration intents and assert it survives the migrated config, dev group, and refreshed lock. The future coverage-plan audit should verify equality to the root pin.
- Suggested validation: After the atomic migration, parse the root and `.standards/config.toml` dependency requirements and assert the exact Pyright requirement matches the pre-migration reviewed pin before checking the refreshed lock and provisioned runtime version.

### CR-NEW-002: Handoff documents are changed without their conformance gates

- Severity: Medium
- Status: Confirmed
- Adversarial angle: Checked the claimed complete closeout against the repository-local Agent Handoff skill rather than only the Python/package CI workflows.
- Plan reference: Task 6 files and documentation commit, lines 885-919.
- Finding: Task 6 updates `docs/handoff/specs-plans.md`, `docs/STATUS.md`, and `docs/TODO.md` but does not run `project-standards agent-handoff validate --repo .` or `drift-check --repo .`. The repository-local skill requires those relevant validations at closeout. Focused Python tests do not substitute for checking the live handoff layout, pointers, and managed ownership state.
- Repository evidence: `.agents/skills/agent-handoff/SKILL.md:67-79` requires closeout validation and drift checking after current facts or future work change.
- External research evidence: Not applicable.
- Why it matters: Task 6 can commit an invalid or drifting handoff state while calling the repository gate complete, weakening the cold-resume contract the task is specifically updating.
- Recommended action for the authoring agent: Add both Agent Handoff commands after the documentation edits and before the final documentation commit. Keep any required handoff fixes within Task 6's explicit staging list.
- Suggested validation: Run `uv run project-standards agent-handoff validate --repo .` and `uv run project-standards agent-handoff drift-check --repo .` after the final docs edits, then inspect the diff and rerun the pointer checks if either command reports drift.

## Regressions

None found. The new findings arise from the expanded Pyright provisioning and closeout text; they do not reopen the resolved import, lifecycle, gate, or schema-shape defects.

## Internet research performed

- Source name: npm configuration documentation
- URL: <https://docs.npmjs.com/cli/using-npm/config/>
- Access date: 2026-07-12
- What it was used to verify: The strict npm offline switch and whether it prevents network requests during install.
- Relevant conclusion: npm's `offline` boolean forces install operations to make no network requests; `prefer-offline` is insufficient because it still fetches missing data. npm configuration can be supplied through `npm_config_*` environment variables.

- Source name: Pyright for Python repository
- URL: <https://github.com/RobertCraigie/pyright-python>
- Access date: 2026-07-12
- What it was used to re-verify: The wrapper's runtime npm installation and user-cache model after the plan introduced a provisioning phase.
- Relevant conclusion: The online setup step is a valid provisioning model, but a later `pyright --version` probe still needs an npm/offline or stronger isolation constraint if it is meant to prove the cache is already provisioned.

## Read-only validation performed

- `git status --short --branch` and `git log -7 --oneline`: confirmed the clean feature branch at `a9e443b`, with reconciliation commit `ab23e61` and the round-1 report committed separately.
- `git show --stat` and `git show ab23e61 -- <plan> <design>`: isolated the exact round-1 corrections and confirmed their file scope.
- Re-read the complete revised plan, amended design, and prior audit ledger with line-numbered inspections.
- Inspected current predicate/default logic, Python Tooling dependency rendering, config editing, planner/lock behavior, reconstruction and migration tests, repository runner, CI workflows, `AGENTS.md`, and the Agent Handoff skill with `rg`, `sed`, and `nl`.
- `git diff --check`: clean before this report write.
- `test -e .standards`: confirmed the feature-worktree root still has no `.standards/` directory.
- Consulted the official npm configuration documentation and rechecked the Pyright wrapper's authoritative repository documentation.

## Recommended implementation validation

- Run only after correction and implementation: provision Pyright into an explicit empty cache online, then rerun both the version probe and Pyright-selected oracle with npm strict offline mode and, if promised, process-level outbound network disabled.
- Run only after implementation: focused predicate/schema tests including every prohibited intermediate shape.
- Run only after implementation: both real checker transition cycles, the retained-Pyright disable/re-enable case, V4 migration, and exact lock-scope assertions.
- Run only after implementation: the complete-gate oracle for both checkers with the scratch import probe and coverage-source assertion.
- Run only after implementation: generated-schema, projection, package, graph, and catalog freshness checks.
- Run only after implementation: Ruff, BasedPyright, repository test runner, pip-audit, `npm ci`, coherence, and managed-Markdown validation.
- Run only after documentation updates: Agent Handoff validate and drift-check, then `git diff --check`, the root `.standards/` absence test, and final worktree inspection.
- Run only during the later atomic migration: assert the exact pinned Pyright requirement survives both migration intents, `.standards/config.toml`, the provider-rendered dev group, and the refreshed lock before rerunning both oracles.

## Final recommendation

The authoring agent should revise the plan using the findings above

## Review ledger for next loop

- Plan path: `docs/superpowers/plans/2026-07-12-python-tooling-checker-table-materialization.md`
- Audit round: 2
- Open issue IDs: CR-001, CR-NEW-001, CR-NEW-002
- Resolved issue IDs: CR-002, CR-003, CR-004, CR-005
- Superseded issue IDs: None
- Significant findings remaining: Yes
- Next audit should focus on: Enforced npm or process-level offline behavior after provisioning; exact Pyright pin propagation into the pending Tasks 9 and 11 migration contract; Agent Handoff closeout validation; and regression checks across the already-resolved import, lifecycle, repository-gate, and schema-shape corrections.
