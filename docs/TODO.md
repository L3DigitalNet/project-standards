# Project Tasks

## Purpose

This document is the user-visible and agent-visible work queue for the repo-local agent-handoff standard.

## Usage Instructions

- Write each actionable item as an unchecked Markdown task: `- [ ]`.
- When an item is completed during a session, change its marker to `- [x]`.
- During agent-handoff closeout, delete completed standalone items after recording current outcomes in `docs/STATUS.md`.
- Mirror any handoff task, todo, pending item, or follow-up here so the user can track it.
- Do not start or complete TODO items unless the user explicitly asks for that work.

<!-- LLM-EDIT-BOUNDARY: DO NOT EDIT ABOVE THIS LINE -->

## User tasks

- [ ] Define the repository policy and tooling for durable document references.

  Decide when identifiers such as `SPEC-MT01` must link to their canonical documents. Define checks for inconsistent or missing links, maintenance of `related:` frontmatter, graph generation, and safe reconciliation of detected drift.

- [ ] Define structure and formatting instructions for `docs/STATUS.md`.

  The current snapshot is concise; define durable formatting rules so future updates preserve that shape.

- [x] Create durable repo rule: `docs/superpowers/` is a forbidden path. Nothing should get saved here. Use `docs/plans/` and `docs/specs/` instead. _(Done 2026-07-19: the directory is deleted, its contents relocated, and the rule is recorded in `AGENTS.md` Working Rules.)_

- [x] Ensure full meta-repo tooling functionality is documented. _(Done 2026-07-19: audited the full tooling surface — CLI leaves/options, console scripts, `scripts/` helpers, workflows, pre-commit hooks, coherence suite — and closed the gaps: `.pre-commit-hooks.yaml` documented in `README.md`, repo-CI workflow inventory documented in `tests/README.md` § CI relationship, stale bundle-authoring `2.0` references bumped to `2.1`.)_

## Agent tasks

### Maintenance

- [ ] Finish Agent Handoff consumer retirement.

- [ ] Complete the approved future-artifact cleanup.

- [ ] Decide whether Python Coding 0.6 remains reference-only or proceeds toward consumer adoption.

- [ ] Correct the Standard Bundle Authoring documentation drift without rewriting historical evidence: update the current-authority reference from 2.2 to 2.5, correct the SPEC-BA02 index revision from 0.13 to 0.14, and verify the SPEC-CP01 and SPEC-DPEY index rows against their revision histories.

### Future programs

- [ ] Review and approve the Usage Documentation Site specification set before implementation planning.

- [ ] Complete the reviewed MCP implementation plan.
  - [ ] Resume T1 only after the final 2026-07-28 protocol publication and official stable Python SDK release evidence are available.
  - [ ] Verify the protocol, SDK, license, conformance, and current Codex/Claude client capabilities in the dated evidence matrix.
  - [ ] Create and accept ADRs 0025-0026, obtain the recorded owner decisions required by T1, resolve the assigned SPEC-RD01/SPEC-MS01 open questions, and update their revisions and indexes.
  - [ ] Pin the approved SDK dependency, update `uv.lock`, and pass the T1 lock, audit, client-probe, candidate-wheel, specification, and documentation gates.
  - [ ] Begin MCP source implementation at T2 only after T1 completes.

- [ ] Maintain the temporary MCP project change hold until implementation-plan T12 closes: avoid significant non-MCP features, architectural refactors, standards-package programs, release trains, or other broad repository changes. Keep necessary maintenance narrow, and obtain owner direction before any exception that could disturb the MCP baseline.

- [ ] Specify and release the provider-neutral `project-toolbox` standard, including its proven workflows and routing skill.
  - [ ] After release, design template-repository autopopulation against `project-toolbox`.

- [ ] Specify and release the `agent-managed-repo` standard after `project-toolbox`.
  - [ ] After release, reconcile this repository's GitHub settings against `agent-managed-repo`.
