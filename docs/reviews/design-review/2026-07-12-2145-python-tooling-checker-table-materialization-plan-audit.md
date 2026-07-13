# Python Tooling Checker Table Materialization Plan Audit — Round 3

## Executive summary

CR-NEW-001 and CR-NEW-002 are resolved: the plan now hands the exact Pyright requirement to the pending migration tasks and runs both Agent Handoff conformance gates after its documentation edits.

CR-001 remains partially resolved. npm strict offline is correctly added to the oracle, but the new shared-cache wiring uses `${{ runner.temp }}` in `jobs.<job_id>.env`. GitHub's current context-availability contract does not permit the `runner` context at job-level `env`, so the proposed workflow is invalid before the provisioning or oracle steps execute. This is a regression introduced by the round-2 correction and remains blocking under the original High finding.

New internet research was required to verify the exact GitHub Actions expression scope. Official GitHub documentation confirms that `runner` is available to step-level keys but not `jobs.<job_id>.env`, and documents `$GITHUB_ENV` plus `$RUNNER_TEMP` as a supported way to make a runner-derived value available to subsequent steps.

## Verdict

Needs major correction before execution

## Audit loop status

- Audit type: Follow-up audit
- Plan path: `docs/superpowers/plans/2026-07-12-python-tooling-checker-table-materialization.md`
- Prior audit issue count: 3
- Resolved issue count: 2
- Still open issue count: 0
- Partially resolved issue count: 1
- New issue count: 0
- Regression count: 1
- Significant findings remaining: Yes

## Adversarial review performed

- Re-read the current plan, amended originating design, round-2 audit ledger, and exact `8bbf743` reconciliation diff.
- Retested the CR-001 correction across three boundaries: npm strict-offline propagation into the subprocess environment, cache-location equality between provisioning and test execution, and GitHub Actions expression availability at the proposed YAML scope.
- Verified the exact-pin handoff against the provider's verbatim `additional_dev_dependencies` rendering and the still-blocked Tasks 9 and 11 release boundary.
- Verified the new Agent Handoff commands against the repository-local skill and their placement after documentation edits and before the final commit.
- Re-attacked the already-resolved import seam, real-payload lifecycle, complete repository gate, and intermediate-schema matrix for regressions; none were introduced.
- Inspected the current check workflow structure to determine where the proposed cache setup would be inserted.
- Did not execute tests, dependency resolution, npm/Pyright provisioning, workflow runs, generators, or formatters because those operations are mutating and reserved for implementation.

## Prior findings status

### CR-001: The locked Pyright dependency does not create an offline executable

- Previous severity: High
- Current status: Partially resolved
- Evidence: The oracle now sets `npm_config_offline = "true"` alongside `UV_OFFLINE=1`, so the Pyright wrapper's npm install cannot silently heal a missing runtime cache (`plan:805-827`). The plan also intends provisioning and the test runner to share `PYRIGHT_PYTHON_CACHE_DIR`. However, its job-level YAML uses `PYRIGHT_PYTHON_CACHE_DIR: ${{ runner.temp }}/pyright-python-cache` (`plan:750-760`). GitHub's context-availability table permits only `github`, `needs`, `strategy`, `matrix`, `vars`, `secrets`, and `inputs` in `jobs.<job_id>.env`; `runner` is not available there. The workflow therefore cannot establish the shared cache as written.
- Remaining action for the authoring agent: Replace the invalid job-level expression with runner-executable wiring. A supported pattern is a setup step before provisioning that writes `PYRIGHT_PYTHON_CACHE_DIR=$RUNNER_TEMP/pyright-python-cache` to `$GITHUB_ENV`, which makes the value available to every subsequent step in that job. Alternatively, repeat a step-level `${{ runner.temp }}` environment value on both provisioning and test steps. Make the oracle require or explicitly report the shared cache variable so local execution cannot silently fall back to an unrelated default user cache. Update the plan and design wording to name the actual mechanism.

### CR-NEW-001: The exact Pyright pin is lost at the pending atomic migration

- Previous severity: Medium
- Current status: Resolved
- Evidence: Task 5 now defines the resolved `pyright==X.Y.Z` string as a named release-integration output, requires Tasks 9 and 11 to carry it verbatim rather than using the bare name, and records it in the commit and `docs/handoff/specs-plans.md` (`plan:748-764`). The design's normative carry-through bullet requires equality with the pre-migration root pin across both intents, `.standards/config.toml`, the provider-rendered dev group, and refreshed lock (`design:120-123`). That matches the provider's verbatim append behavior.
- Remaining action for the authoring agent: None in this plan. The future parallel-coverage amendment and its required fresh audit remain responsible for implementing and proving the handoff.

### CR-NEW-002: Handoff documents are changed without their conformance gates

- Previous severity: Medium
- Current status: Resolved
- Evidence: Task 6 now runs `uv run project-standards agent-handoff validate --repo .` and `drift-check --repo .` after updating `docs/handoff/specs-plans.md`, `docs/STATUS.md`, and `docs/TODO.md`, and before the final documentation commit (`plan:921-936`). This matches `.agents/skills/agent-handoff/SKILL.md:67-79` and the sibling coverage-plan convention.
- Remaining action for the authoring agent: None.

## New blocking issues

None found. The remaining blocking defect is tracked under partially resolved CR-001.

## New non-blocking issues

None found.

## Regressions

- The round-2 correction introduced an invalid GitHub Actions expression by placing `${{ runner.temp }}` in `jobs.<job_id>.env`. The `runner` context is available after a job is assigned to a runner and is allowed in step-level keys, but GitHub explicitly excludes it from job-level `env`. This prevents the intended CI provisioning contract from starting and is the remaining CR-001 defect.

No regressions were found in the exact-pin handoff, handoff gates, scratch import seam, lifecycle proofs, repository gate, or schema-shape coverage.

## Internet research performed

- Source name: GitHub Actions contexts reference
- URL: <https://docs.github.com/en/actions/reference/workflows-and-actions/contexts>
- Access date: 2026-07-12
- What it was used to verify: Context availability for `jobs.<job_id>.env` and step-level workflow keys.
- Relevant conclusion: `runner` is not an allowed context for `jobs.<job_id>.env`; it is allowed in step-level `env` and `run` scopes.

- Source name: GitHub Actions workflow commands
- URL: <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands>
- Access date: 2026-07-12
- What it was used to verify: A supported way to propagate a runner-derived cache path to later job steps.
- Relevant conclusion: A step can write `NAME=value` to `$GITHUB_ENV`, and all subsequent steps in the same job receive that environment variable. GitHub also exposes `$RUNNER_TEMP` inside runner-executed steps.

## Read-only validation performed

- `git status --short --branch` and `git log -8 --oneline`: confirmed the clean feature branch at `8770a6b`, with plan/design reconciliation at `8bbf743` and the round-2 report committed separately.
- `git show --stat` and `git show 8bbf743 -- <plan> <design>`: isolated the exact round-2 corrections and their file scope.
- Re-read the complete current plan, amended design, and round-2 audit ledger with line-numbered inspections.
- Inspected `.github/workflows/check.yml`, the Python Tooling dependency renderer, Agent Handoff skill, related plan conventions, and every new offline/pin/handoff reference using `rg`, `sed`, and `nl`.
- `git diff --check`: clean before this report write.
- `test -e .standards`: confirmed `.standards/` remains absent at the feature-worktree root.
- Consulted GitHub's official context-availability and workflow-command documentation.

## Recommended implementation validation

- Run only after correction and implementation: validate the changed workflow with the repository's workflow tests and a GitHub Actions-aware validator; confirm the cache setup step precedes provisioning and the test runner.
- Run only after implementation: provision Pyright into the explicit runner cache, then execute the version probe and both complete-gate oracle selections with uv and npm strict offline enabled.
- Run only after implementation: repeat the Pyright oracle with an empty explicit cache and npm offline enabled; require the planned diagnostic rather than a network download or fallback cache.
- Run only after implementation: focused schema, real checker lifecycle, V4 migration, reconstruction, and full control-plane suites.
- Run only after implementation: the complete repository package/graph/catalog, Ruff, BasedPyright, pip-audit, npm/coherence, managed-Markdown, and repository-runner gates.
- Run only after documentation updates: Agent Handoff validate and drift-check, followed by `git diff --check`, root `.standards/` absence, and final worktree inspection.
- Run only during the later atomic migration: assert the exact pinned Pyright requirement survives both intents, `.standards/config.toml`, the provider-rendered dev group, and refreshed lock before rerunning both oracles.

## Final recommendation

The authoring agent should revise the plan using the findings above

## Review ledger for next loop

- Plan path: `docs/superpowers/plans/2026-07-12-python-tooling-checker-table-materialization.md`
- Audit round: 3
- Open issue IDs: CR-001
- Resolved issue IDs: CR-NEW-001, CR-NEW-002
- Superseded issue IDs: None
- Significant findings remaining: Yes
- Next audit should focus on: Valid GitHub Actions cache propagation from `$RUNNER_TEMP` to provisioning and test steps; enforced explicit-cache use under npm strict offline; and regression checks across exact-pin propagation, handoff gates, importability, lifecycle, full repository validation, and schema-shape coverage.
