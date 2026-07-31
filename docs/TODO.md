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

- [x] **Important:** cut release-gate verification wall-clock; implement with the v5.13.0 train. _(Done 2026-07-31: spike + adoption shipped. Gate green at 10:23 under real-usage load, 5.3× vs the 55:31 baseline; quiet floor in the 5–8 min target band. Evidence and adopted configuration: `docs/research/2026-07-31-release-gate-wall-clock-spike.md`; runner: `scripts/verify.sh`; MCP fixture-reduction lever not needed.)_

- [ ] ~~Move repository CI to the self-hosted runner; ship with the v5.13.0 train.~~ **Deferred from v5.13.0** _(owner decision 2026-07-31)_ after an adversarial security review refuted the design; hosted minutes are free for public repos, so speed was the only payoff.

  Revisit under the `agent-managed-repo`/governance program using the approved dedicated-group architecture and the ten-item hardening program in `docs/research/2026-07-31-self-hosted-runner-security-review.md` (several items are homelab-repo VM 200/Ansible work; two GitHub behaviors need empirical verification first).

- [x] Evaluate further release-process efficiency candidates for the v5.13.0 efficiency train. _(Done 2026-07-31, all five dispositioned: SHIPPED — trimmed local verification policy (fast gate for intermediate legs, `--full` at release prep), `scripts/release_prep.py`, local `prettier --cache`. REJECTED — frozen-venv/per-lane parallel suites (xdist in one venv already delivers the win) and diff-scoped test selection (catalog-wide couplings make it unsafe; the fast gate subsumes it); wheel-runtime build caching rejected inside the caching candidate (build+extract ≈1 s). Rationale: `docs/research/2026-07-31-release-gate-wall-clock-spike.md` §Rejected levers.)_

### Maintenance

- [ ] Benchmark the fast release gate under controlled conditions and dial in worker counts and lane concurrency. _(Owner 2026-07-31: the spike measured under real-usage load; `VERIFY_ORDINARY_WORKERS`/`VERIFY_COMPAT_WORKERS` overrides in `scripts/verify.sh` exist for the sweep.)_

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
