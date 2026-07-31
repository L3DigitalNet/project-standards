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

  Decide when identifiers such as `SPEC-MT01` must link to their canonical documents, and define checks for missing or inconsistent links, `related:` frontmatter maintenance, graph generation, and drift reconciliation. _(Owner 2026-07-29: deferred past implementation-plan T12 under the MCP hold.)_

- [ ] Define structure and formatting instructions for `docs/STATUS.md`.

  The current snapshot is concise; define durable formatting rules so future updates preserve that shape. _(Owner 2026-07-29: deferred past implementation-plan T12 under the MCP hold.)_

- [ ] Assess each standards package for potentially adding a skill for using it. The skill would be owned by and ship with the package. The consumer could enable/disable it in the relevant config.

- [ ] In the markdown-frontmatter package: Create a script that indexes all Markdown front-matter-governed documents in the consumer repository and generates an LLM-friendly master index for agents working in the repo to search documents and orient themselves.

- [ ] In the python-coding package: Move governance of the Python expert skill (from the current owner `agent-configs` repo) to the python-coding standard.

- [ ] Create a script that is meant for use by the human-user of the consuming v5 repo. This will be a CLI tool that allows the user to select what standards packages they want to enable in their repo, and also choose any optional tooling/skills/features/etc. that they want to enable. The script will then generate the appropriate config files and add them to the repo.

## Agent tasks

### Active program (MCP)

- [ ] Complete the reviewed MCP implementation plan.
  - [x] Continue with T11 (installed-wheel client proof and documentation) when directed. _(Done 2026-07-30: commit `df25964` after Codex RED and GREEN reviews; the smoke-discovered dispatch defect was fixed via discovered-work T15 `75c9653` and T14 `1abf8d9`; SPEC-MS01 OQ-005 resolved at revision 1.4.)_
  - [x] At T11, re-check whether codex-cli has enabled `mcp_2026_07_28` by default before capturing the FR-030 probe evidence. _(Done 2026-07-30: 0.146.0 is still the latest stable and the flag remains default-disabled; no matrix refresh triggered.)_
  - [ ] Continue with T12 (final gate and handoff) when directed.

- [ ] Maintain the temporary MCP project change hold until implementation-plan T12 closes.

  Avoid significant non-MCP features, architectural refactors, standards-package programs, release trains, or other broad repository changes. Keep necessary maintenance narrow, and obtain owner direction before any exception that could disturb the MCP baseline.

  _(Owner 2026-07-29: standards packages stay locked until the MCP server is live, except minor-level version changes; standards v5.12.0 ships with the MCP server.)_

### Maintenance

- [ ] Finish Agent Handoff consumer retirement.

  Four consumers owe protected merges to `main`: `docmend` and `hw-radar` from `dev`, `website-aboutme` and `website-l3digital.net` from `testing`; `~/scripts` needs `reconcile --apply`; `llm-wiki` has two consumer-side shape overflows.

  `control-center` stays on legacy config, blocked by issue #83, owner-handled — not engine-blocked. Details: `docs/research/2026-07-09-agent-handoff-retirement-inventory.md`.

- [ ] Complete the approved future-artifact cleanup.

- [ ] Decide whether Python Coding 0.6 remains reference-only or proceeds toward consumer adoption.

### Future programs

- [ ] Review and approve the Usage Documentation Site specification set before implementation planning.

- [ ] Specify and release the provider-neutral `project-toolbox` standard, including its proven workflows and routing skill.
  - [ ] After release, design template-repository autopopulation against `project-toolbox`.

- [ ] Specify and release the `agent-managed-repo` standard after `project-toolbox`.
  - [ ] After release, reconcile this repository's GitHub settings against `agent-managed-repo`.
