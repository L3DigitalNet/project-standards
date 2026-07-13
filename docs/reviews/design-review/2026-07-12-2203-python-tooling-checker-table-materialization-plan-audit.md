# Python Tooling Checker Table Materialization Plan Audit — Round 4

## Executive summary

CR-001 is resolved. The plan now establishes `PYRIGHT_PYTHON_CACHE_DIR` inside a runner-executed setup step using `$RUNNER_TEMP`, publishes it through `$GITHUB_ENV`, and provisions the Pyright runtime only after that publication. GitHub's current workflow contract confirms that this makes the cache location available to every subsequent step in the job, including the test runner.

The oracle retains npm strict offline and uv offline enforcement and now reports the cache location when provisioning is missing. CR-NEW-001 and CR-NEW-002 remain resolved, and no regression was found in exact-pin propagation, Agent Handoff validation, scratch-project importability, real-payload lifecycle coverage, the repository gate, or the intermediate-schema matrix.

No significant findings remain. The audit/fix loop can stop, and the plan is ready for implementation.

## Verdict

No significant findings remain

## Audit loop status

- Audit type: Follow-up audit
- Plan path: `docs/superpowers/plans/2026-07-12-python-tooling-checker-table-materialization.md`
- Prior audit issue count: 1
- Resolved issue count: 1
- Still open issue count: 0
- Partially resolved issue count: 0
- New issue count: 0
- Regression count: 0
- Significant findings remaining: No

## Adversarial review performed

- Re-read the current plan, amended originating design, round-3 audit ledger, and exact `6012e02` reconciliation diff.
- Re-tested the remaining CR-001 mechanism across the GitHub Actions scope boundary: runner-time path construction, `$GITHUB_ENV` publication, step ordering, provisioning, and inheritance by later test steps.
- Re-checked the oracle's isolation boundary: uv offline mode, npm strict offline mode, provisioned-runtime preflight, cache-location diagnostic, and network-isolated generated-gate execution.
- Re-attacked the exact Pyright pin handoff and the Agent Handoff conformance gates for regressions introduced by the round-3 correction.
- Re-attacked the already-resolved scratch import seam, real-payload transition cycles, disable/re-enable proof, complete repository gate, and intermediate-schema rejection matrix.
- Inspected the current workflow structure to confirm the two planned setup steps are inserted immediately after dependency synchronization and before all consumers.
- Did not execute tests, dependency resolution, npm/Pyright provisioning, workflow runs, generators, or formatters because those operations are mutating and reserved for implementation.

## Prior findings status

### CR-001: The locked Pyright dependency does not create an offline executable

- Previous severity: High
- Current status: Resolved
- Evidence: Task 5 now inserts a `Set Pyright cache location` step immediately after dependency synchronization. That runner-executed step writes `PYRIGHT_PYTHON_CACHE_DIR=$RUNNER_TEMP/pyright-python-cache` to `$GITHUB_ENV`, followed by `Provision Pyright runtime` and then the remaining job steps (`plan:750-761`). GitHub documents `$GITHUB_ENV` as the supported channel for making environment values available to subsequent steps, and `$RUNNER_TEMP` is available inside runner-executed `run` steps. The invalid job-level `${{ runner.temp }}` expression is gone. The oracle continues to set `npm_config_offline = "true"` and `UV_OFFLINE=1`, performs the checker version preflight before executing the generated gate, and reports the cache location in its missing-provision diagnostic (`plan:806-830`). The design names the same runtime-provisioning and cache-publication contract (`design:116`).
- Remaining action for the authoring agent: None.

### CR-NEW-001: The exact Pyright pin is lost at the pending atomic migration

- Previous severity: Medium
- Current status: Resolved
- Evidence: The round-3 correction does not alter the named `pyright==X.Y.Z` release-integration output or the requirement that coverage Tasks 9 and 11 carry it verbatim in `additional_dev_dependencies` (`plan:759`; `design:122`).
- Remaining action for the authoring agent: None in this plan. The future parallel-coverage amendment and its required fresh audit remain responsible for implementing and proving the handoff.

### CR-NEW-002: Handoff documents are changed without their conformance gates

- Previous severity: Medium
- Current status: Resolved
- Evidence: Task 6 still runs Agent Handoff `validate` and `drift-check` after documentation edits and before the final commit (`plan:927-928`). The cache-wiring correction does not affect that sequencing.
- Remaining action for the authoring agent: None.

## New blocking issues

None found.

## New non-blocking issues

None found.

## Regressions

None found. The round-3 correction removes the invalid job-level expression without weakening npm strict-offline enforcement, the explicit-cache CI contract, exact-pin propagation, handoff validation, scratch importability, real-payload lifecycle coverage, the complete repository gate, or schema-shape coverage.

## Internet research performed

- Source name: GitHub Actions contexts reference
- URL: <https://docs.github.com/en/actions/reference/workflows-and-actions/contexts>
- Access date: 2026-07-12
- What it was used to verify: The corrected mechanism no longer depends on the unavailable `runner` context at `jobs.<job_id>.env` scope.
- Relevant conclusion: The prior invalid job-level expression has been removed; runner-derived values may instead be established during runner-executed steps.

- Source name: GitHub Actions workflow commands
- URL: <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands>
- Access date: 2026-07-12
- What it was used to verify: Propagation of a runner-derived cache path to provisioning and later test steps.
- Relevant conclusion: Writing `NAME=value` to `$GITHUB_ENV` makes that environment variable available to subsequent steps in the same job. The plan's setup-step ordering therefore establishes one shared Pyright cache before provisioning and testing.

## Read-only validation performed

- `git status --short --branch`: confirmed the clean `feature/python-tooling-parallel-coverage` branch at the round-3 audit and reconciliation commits.
- `git diff --check`: clean before this report write.
- `test -e .standards`: confirmed `.standards/` remains absent at the feature-worktree root.
- Re-read the complete round-3 audit and inspected the corrected plan/design references with `rg` and line-oriented reads.
- Inspected the current `.github/workflows/check.yml` ordering and the proposed insertion point after dependency synchronization.
- Re-checked GitHub's official context-availability and workflow-command documentation.

## Recommended implementation validation

- Validate the changed workflow with the repository's workflow tests and a GitHub Actions-aware validator; confirm cache setup precedes provisioning and every test consumer.
- Provision Pyright into the explicit runner cache, then execute the version probe and both complete-gate oracle selections with uv and npm strict offline enabled.
- Repeat the Pyright oracle with an empty explicit cache and npm offline enabled; require the planned diagnostic rather than a network download or fallback cache.
- Run the focused schema, real checker lifecycle, V4 migration, reconstruction, and full control-plane suites.
- Run the complete repository package/graph/catalog, Ruff, BasedPyright, pip-audit, npm/coherence, managed-Markdown, and repository-runner gates.
- Run Agent Handoff validate and drift-check after documentation updates, followed by `git diff --check`, root `.standards/` absence, and final worktree inspection.
- During the later atomic migration, assert the exact pinned Pyright requirement survives both intents, `.standards/config.toml`, the provider-rendered dev group, and refreshed lock before rerunning both oracles.

## Final recommendation

No significant findings remain; the audit/fix loop can stop

## Review ledger for next loop

- Plan path: `docs/superpowers/plans/2026-07-12-python-tooling-checker-table-materialization.md`
- Audit round: 4
- Open issue IDs: None
- Resolved issue IDs: CR-001, CR-NEW-001, CR-NEW-002
- Superseded issue IDs: None
- Significant findings remaining: No
- Next audit should focus on: Not applicable. Implementation may proceed. The separately required amendment and fresh audit of parallel-coverage Tasks 9 and 11 remain outside this converged plan audit.
