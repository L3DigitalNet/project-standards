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

## Agent tasks

### Post-v5 maintenance

- [ ] Finish Agent Handoff consumer retirement.

  Refresh the consumer ledger, resolve remaining concrete-evidence default-branch rows through authorized workflows, run the final dependency search, and obtain owner approval before deleting the deprecated engine.

- [ ] Resolve the owner-reviewed future-artifact dispositions.

  Delete the two approved superseded transcripts, consolidate retained Project Specification guidance into its durable owner, then update `docs/future-standards/README.md` and inbound links.

- [ ] Decide and complete the Python Coding package's post-v5 status path.

  Keep 0.5 reference-only until its requirements, adoption posture, and release criteria are accepted or the package is deliberately retained as reference material.

- [ ] Review the Usage Documentation Site specification set.

  Treat the eight-document set as a separate program: reconcile requirements and decisions, obtain formal specification approval, then design and plan implementation.

- [ ] Continue MCP server enablement.

  Before SPEC-MS01 MS-0, recheck the MCP protocol, Python SDK, licensing, and client capabilities; resolve remaining owner decisions before implementation.

### Future package programs

- [ ] Create and release the provider-neutral `project-toolbox` standard.

  Develop this as its own design, review, implementation, and release cycle. Package the proven workflows and routing skill under `.agents/workflows/project-toolbox/`; retain `docs/workflows/` for local extensions.

  - [ ] Convert the installed Codex `review-orchestrator` skill into a managed `project-toolbox` workflow.

- [ ] Add template-repository autopopulation after `project-toolbox` is released.

  Design bootstrap and update flows against the released provider-neutral package.

- [ ] Create and release the `agent-managed-repo` standard.

  Develop this only after `project-toolbox` closes. Use `docs/future-standards/github-repository-governance-standard.md` as provisional input to a separate cycle.

- [ ] Reconcile this repository's GitHub settings with `agent-managed-repo`.

  After that package is released, apply its required-review, required-check, action-security, Dependabot, and release-policy rules here.
