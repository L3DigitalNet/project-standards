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

### Release v5.13.0

- [ ] **Important:** cut release-gate verification wall-clock; implement with the v5.13.0 train. _(Owner 2026-07-31: spike first, immediately after v5.12.0 closes.)_

  Sequencing: the xdist read-safety/inode spike and the sysmon-vs-trace coverage diff run as the first work item after the v5.12.0 release closes, so the harness is proven before any 5.13.0 gate depends on it.

  Levers by value: pytest-xdist (spike dogfood read-safety and parallel inode pressure first); `COVERAGE_CORE=sysmon` coverage on Python 3.14; a pytest tmpfs with raised `nr_inodes` (~4M) to reclaim the ~40% disk-backed TMPDIR penalty (conventions §14); fewer full-battery runs per train (full battery only after the last content change and at release prep).

  Also bundle the two smaller levers: statics (prettier, markdownlint, basedpyright, pip-audit) run concurrently with the battery via a non-uv invocation path (~2–3 min return); MCP fixture file-count reduction through session-scoped fixture reuse, pursued only if the primary levers prove insufficient.

  Baseline to beat (measured 2026-07-31): plain battery 16:22 tmpfs / 22:30 disk-backed; coverage battery 55:31 disk-backed. Target: 5–8 minute release gate.

- [ ] Move repository CI from GitHub-hosted runners to the self-hosted runner on the Hetzner box; ship with the v5.13.0 train. _(Owner 2026-07-31.)_

  Restrict pull requests to administrators (owner-only) so the self-hosted runner never executes untrusted contributor code — the standard workflow-injection risk on self-hosted runners. Saves GitHub-hosted runner minutes and is potentially faster.

  Before migrating, load the gh-runner situational reference (`agent-configs` repo: `global/claude/context/gh-runner.md`) and re-check every workflow's `runs-on` target plus any downstream consumers of this repo's reusable workflows.

- [ ] Evaluate further release-process efficiency candidates for the v5.13.0 efficiency train. _(Owner 2026-07-31: the next version is all about process efficiency.)_

  Candidate: break the serial-venv constraint — a frozen venv with `uv run --no-sync`, or per-lane git worktrees with their own environments, so independent suites (package_contract, mcp_server, control_plane) run in parallel instead of queuing on one shared environment.

  Candidate: after the runner migration, make hosted CI the single authoritative full battery and trim local pre-push verification to targeted lanes plus statics — today every train pays the full battery twice, once locally and once in `Check`.

  Candidate: cache the candidate-wheel runtime keyed by `src/` and payload digests so unchanged builds skip the rebuild-and-extract cycle, and enable `prettier --cache` for the 1,150-file format gate.

  Candidate: script the mechanical release-prep steps behind one command — version-string sweep, changelog conversion, activation-constant advance, and the payload wiring order (digests → aggregate → manifests → projection → catalog) — so release prep costs minutes, not a session leg.

  Candidate: diff-scoped test selection for intermediate train legs (an impacted-lane map or pytest-testmon), reserving the full battery for the last content change and release prep.

### Maintenance

- [ ] Finish Agent Handoff consumer retirement.

  Four consumers owe protected merges to `main`: `docmend` and `hw-radar` from `dev`, `website-aboutme` and `website-l3digital.net` from `testing`; `~/scripts` needs `reconcile --apply`; `llm-wiki` has two consumer-side shape overflows.

  `control-center` stays on legacy config, blocked by issue #83, owner-handled — not engine-blocked. Details: `docs/research/2026-07-09-agent-handoff-retirement-inventory.md`.

- [ ] Retire `control_plane/provider_inputs.py` in favour of payload-declared provider input shapes.

  The T15 seam consolidated four private per-standard input constructions behind one fail-closed authority — correct for a shared module, but it keeps per-standard knowledge in the engine. The owner recorded payload-declared input shapes as that module's retirement path once the MCP hold lifted (freeze J-N, 2026-07-30, resolution A).

- [ ] Complete the approved future-artifact cleanup.

- [ ] Decide whether Python Coding 0.6 remains reference-only or proceeds toward consumer adoption.

### Future programs

- [ ] Review and approve the Usage Documentation Site specification set before implementation planning.

- [ ] Specify and release the provider-neutral `project-toolbox` standard, including its proven workflows and routing skill.
  - [ ] After release, design template-repository autopopulation against `project-toolbox`.

- [ ] Specify and release the `agent-managed-repo` standard after `project-toolbox`.
  - [ ] After release, reconcile this repository's GitHub settings against `agent-managed-repo`.
