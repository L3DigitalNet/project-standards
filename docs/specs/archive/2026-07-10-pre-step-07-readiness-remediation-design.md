# Pre-Step-07 Readiness Remediation Design

**Date:** 2026-07-10 **Status:** owner-approved; implementation complete **Author:** session 2026-07-10

## Problem and goal

SPEC-MT01 Steps 00-06 are implemented and the full local Python gate is green, but the repository is not ready to start Step 07 under its own roadmap. SPEC-RD01 requires complete SPEC-MT01 traceability before Step 07 starts. The controlling spec still presents implemented requirements as `Not Started`, release and handoff documents contain stale facts, and the repository-specific graph/catalog gate is visible only through the general pytest run.

The goal is to reconcile the implemented contract with its evidence, fix verified housekeeping defects, and add an explicit repository-only graph/catalog CI gate. The work must not change the generic Python Tooling verification contract or begin MCP server implementation.

The 2026-07-10 readiness inventory and adversarial review are incorporated into this design; their completed review artifacts were pruned before v5 after the accepted outcomes were preserved here and in session history.

## Approved approach

Use a hybrid of conservative reconciliation and repository-specific enforcement hardening:

1. Reconcile specifications, release notes, authoring guidance, and handoff pointers from existing implementation evidence.
2. Fix the Agent Handoff bug-index shape false positive with a regression test.
3. Add a dedicated repository-only workflow for graph validation and catalog freshness.
4. Preserve the generic Python Tooling `check.py` and `check.yml` byte-identical contract.
5. Defer owner-choice work until the no-input tranche is complete.

## Scope

### Included

- Complete the SPEC-MT01 requirement-to-test matrix with actual files, tests, commands, and accurate statuses.
- Resolve open questions already answered by accepted ADRs or implemented contracts.
- Keep FR-013 visible as a non-blocking `Should` gap unless evidence supports completion.
- Keep FR-019 and the readiness-report Definition-of-Done item pending for Step 07 itself.
- Update the Standard Bundle Authoring Standard for the repository's current nine bundles, seven artifact manifests, and ADRs 0017-0022.
- Remove stale “future Step 04” implementation comments from current manifest surfaces.
- Add the missing SPEC-MT01 Steps 02-06 v5 changelog and migration posture.
- Reconcile stale handoff plan/inventory pointers without rewriting append-only history.
- Fix Agent Handoff shape policy so `docs/handoff/bugs/INDEX.md` is not treated as a numbered bug record.
- Add explicit hosted CI for graph validation and catalog freshness on the active `testing` branch and released `main` branch.
- Add tests for the workflow contract and shape-policy correction.

### Deferred for owner input

- Repair versus explicit exclusion for `docs/future-standards/**` Markdown debt.
- GitHub ruleset changes, required reviews, and required status checks.
- Closing or changing remote issues and pull requests.
- Whether FR-013 advisory debt must be cleared before v5.0.0 or may remain documented.
- Root-artifact consolidation across Python Tooling and Markdown Tooling.
- Any rewriting of append-only historical session rows.
- Machine-enforced sorting or completeness validation for `docs/handoff/bugs/INDEX.md`.
- Trimming the advisory instruction-file size warnings in `AGENTS.md` and `CLAUDE.md` while preserving the repository's self-contained contract.

### Excluded

- MCP server code, MCP SDK selection, MCP runtime dependencies, or transport work.
- Changes to the generic Python Tooling gate inherited by consumer repositories.
- v5 release promotion, version bumps, tag movement, or release-freeze removal.
- Agent Handoff engine deletion or published-wheel retirement checks.

## Design decisions

### 1. Traceability records reality; it does not manufacture completion

Each FR-001 through FR-022 row receives a concrete status and evidence pointer. Implemented requirements become complete only when the current repository contains the claimed artifact and test. Known gaps remain explicit:

- FR-013: traced as a non-blocking `Should` gap unless every active standard has an agent summary or an explicit rationale.
- FR-019: traced to the Step 07 readiness report and remains pending until that report exists.

Definition-of-Done and documentation checkboxes follow the same rule. The SPEC-MT01 lifecycle stays `draft` until Step 07 produces a no-blocker report and the owner approves completion.

Blocking open questions already settled by ADRs 0001-0013 and the implemented manifests become resolved with links to their owners. Non-blocking questions that still represent genuine future choice remain open. The placeholder deviation row becomes an explicit “no deviations recorded” entry rather than a pending pseudo-deviation.

### 2. Repository enforcement stays separate from the reusable Python gate

`scripts/check.py` and `.github/workflows/check.yml` are dogfooded copies of the Python Tooling standard. Adding `project-standards standards ...` commands there would impose behavior specific to this repository on unrelated Python consumers and break the byte-identical source/bundle contract.

Create `.github/workflows/validate-standards-graph.yml` instead. It runs on every pull request and every push to `testing` or `main`, with no path filters. The `testing` trigger produces hosted evidence for the branch where v5 work lands; the `main` trigger continues enforcement after release. Avoiding path filters prevents a future manifest, registry, provider, resource, artifact, or renderer change from bypassing the gate.

The workflow uses the repository's current action and uv pins, installs the locked development environment, and runs two named steps:

```bash
uv run project-standards standards validate-graph --root . --require-all-manifests
uv run project-standards standards render-catalog --root . --check
```

The workflow job has a stable display name suitable for later branch-protection adoption. This design does not authorize changing GitHub rulesets.

### 3. Workflow shape is a tested contract

A focused Python test parses the new workflow and proves:

- `pull_request` and `push` to both `testing` and `main` remain enabled;
- the job has a stable display name;
- dependency installation uses `uv sync --locked --all-groups`;
- graph validation retains `--require-all-manifests`;
- catalog validation retains `--check`;
- the workflow does not use path filters;
- checkout and Python setup action references match the corresponding entries parsed from `.github/workflows/check.yml`;
- both the uv setup action reference and its `with.version` uv release match `.github/workflows/check.yml`.

The workflow test compares parsed workflow values instead of repeating action or uv pin literals. A coordinated dependency update therefore changes the reusable gate and repository-only workflow, while the test continues to enforce parity without becoming a third pin source.

The existing current-repository graph and catalog tests remain in place. The new workflow adds operational visibility and hosted evidence; it does not replace unit or integration coverage.

### 4. Bug-index policy targets numbered records only

The Agent Handoff standard requires `Cause`, `Fix`, and `Lesson` sections in numbered bug records. `bugs/INDEX.md` is an index governed only by the skill's sorting instruction; it has no machine-enforced shape profile. The current `docs/handoff/bugs/*.md` policy glob incorrectly applies bug-record requirements to the index.

Change the policy target to numbered filenames such as `docs/handoff/bugs/[0-9][0-9][0-9]-*.md`. Update shape-target discovery by separating the directory and filename pattern. Treat a filename containing any glob metacharacter (`*`, `?`, or `[`) as a glob; otherwise, use the literal-path branch. Reject those metacharacters in the directory component with an `AH-PATH-BOUNDARY` finding, validate the literal directory through the repository boundary, and apply the filename pattern with `Path.glob`. This keeps repository-boundary validation correct for bracket globs and avoids a hard-coded `INDEX.md` exception.

This remediation deliberately leaves `INDEX.md` without structural validation. Removing a known-invalid record check is narrower and safer than adding a new index grammar. Machine-enforced sorting or completeness is a separate owner-choice enhancement.

The fix updates both canonical and packaged policy copies and adds regression tests proving:

- a malformed numbered bug record still warns;
- `bugs/INDEX.md` is excluded from bug-record section checks;
- bracket-pattern discovery remains confined to the repository;
- a filename pattern containing `[` but no `*` uses glob discovery;
- a policy pattern with a glob metacharacter in its directory component is rejected.

### 5. Handoff history remains append-only

Current pointers may be corrected in `docs/STATUS.md`, `docs/TODO.md`, `docs/handoff/specs-plans.md`, and the active retirement inventory. Existing session rows are not rewritten merely to replace `this commit` or silence advisory shape warnings. A new compact session row records the remediation outcome and commit references at closeout.

## Files and ownership

| Surface | Responsibility |
| --- | --- |
| `docs/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md` | DoD, traceability, open-question, and deviation truth |
| `CHANGELOG.md`, `UPGRADING.md` | v5 consumer/release impact |
| `standards/standard-bundle-authoring/**` | Current standard-package authoring contract |
| `src/project_standards/standard_manifest.py` and generated schema | Remove stale implementation-state descriptions only |
| `.github/workflows/validate-standards-graph.yml` | Repository-only hosted graph/catalog gate |
| `tests/test_standards_graph_workflow.py` | Workflow contract |
| `standards/agent-handoff/resources/policy.toml` | Canonical shape target |
| `src/project_standards/bundles/agent-handoff/resources/policy.toml` | Packaged byte-identical policy |
| `src/project_standards/agent_handoff/validation.py` | Safe bracket-glob target discovery |
| `tests/agent_handoff/test_policy.py`, `tests/agent_handoff/test_validation.py` | Shape-policy regression coverage |
| `docs/handoff/specs-plans.md`, retirement inventory, status/task/session docs | Current project orientation |

## Failure behavior

- A malformed or incomplete standard graph fails the dedicated workflow before catalog checking.
- A stale catalog fails its named workflow step with the existing CLI message.
- A malformed workflow contract fails pytest even when GitHub Actions has not run.
- Agent Handoff continues treating numbered bug-shape problems as advisory warnings; excluding the index does not weaken numbered-record validation.
- Traceability gaps remain visible and block Step 07 only when the roadmap or requirement priority makes them blocking.

## Verification

Run focused tests after each change, then the repository gate:

```bash
uv run pytest tests/agent_handoff/test_policy.py tests/agent_handoff/test_validation.py -q
uv run pytest tests/test_standards_graph_workflow.py tests/test_standards_graph_cli.py tests/test_standards_graph_catalog.py -q
uv run project-standards standards validate-graph --root . --require-all-manifests --json
uv run project-standards standards render-catalog --root . --check
uv run project-standards spec validate --config .project-standards.yml
uv run project-standards spec lint --config .project-standards.yml --strict
uv run project-standards validate --config .project-standards.yml
uv run project-standards agent-handoff validate --repo .
uv run project-standards agent-handoff drift-check --repo .
uv run python scripts/check.py
npm ci
uv run pytest tests/coherence -v
git diff --check
```

Targeted Prettier and markdownlint checks apply to changed Markdown. The known broad `docs/future-standards/**` failures remain an explicit owner-choice item until resolved.

## Acceptance criteria

- SPEC-MT01 traceability has no blanket `Not Started` rows; every requirement has accurate evidence and status.
- Step-07-only work and advisory gaps remain visibly pending rather than falsely complete.
- Standard Bundle Authoring describes the current repository and recent package-methodology ADRs.
- v5 changelog and upgrading guidance cover the manifest/graph/catalog introduction.
- A dedicated repository-only workflow visibly enforces graph validity and catalog freshness on pushes to `testing` and `main`, and on pull requests.
- Generic Python Tooling gate files remain byte-identical and behaviorally unchanged.
- `bugs/INDEX.md` produces no numbered-bug section warning; malformed numbered records still do.
- Current handoff pointers no longer describe completed Step 06 work as pending or the integrated Agent Handoff package as feature-branch-only.
- Focused and full verification passes, aside from explicitly deferred broad Markdown debt.

## Owner questions after the no-input tranche

After implementing and verifying the scope above, ask the owner one question at a time about:

1. repair versus exclusion of `docs/future-standards/**` from broad Markdown workflows;
2. whether FR-013 advisory summary/rationale debt must block v5;
3. GitHub required-review and required-check ruleset adoption;
4. remote issue/PR cleanup;
5. root-artifact consolidation design;
6. whether to trim the advisory instruction-file size warnings;
7. whether the bug index needs machine-enforced sorting or completeness validation.
