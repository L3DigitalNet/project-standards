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

- [ ] Define structure and formatting instructions for `docs/STATUS.md`.

  The current snapshot is concise; define durable formatting rules so future updates preserve that shape. _(Owner 2026-07-29: deferred past implementation-plan T12 under the MCP hold.)_

- [ ] **Elevated Priority:** [frontmatter schema migration tool](feature-proposals/feature-proposal-frontmatter-migration.md):

  Specify the adapter-driven migration product from the linked starting brief; keep it separate from durable-reference reconciliation and automatic standards adoption.

- [ ] Assess each standards package for potentially adding a skill for using it.

  The skill would be owned by and ship with the package. The consumer could enable/disable it in the relevant config.

- [ ] In the markdown-frontmatter package: add a governed-document master index.

  Create a script that indexes all Markdown front-matter-governed documents in the consumer repository and generates an LLM-friendly master index for agents working in the repo to search documents and orient themselves.

- [ ] Review cli-documentation standard and ensure it handles Go CLI tools and their subcommands, flags, and options. If it does not, update it.

- [ ] In the python-coding package: Move governance of the Python expert skill (from the current owner `agent-configs` repo) to the python-coding standard.

- [ ] In the ADR standards package: release a versioned ADR template library.

  Turn the docs-only [ADR Library](../standards/adr/library/README.md) drafts into a set of pre-written ADR templates for common decisions. The released library must be versioned and maintained by the ADR standards package; the current drafts are reference input, not package payloads.

- [ ] In the ADR standards package: tighten ADR scoping and authoring guidance.

  Provide tighter guidance on how to write ADRs that are clear, concise, properly scoped, bounded to prevent forcing requirements on non-relevant stakeholders, etc. Particularly for scope, boundaries, and awareness of potentially affected stakeholders, provide a checklist or template for authors to follow.

  Agents have been quite terrible at writing properly scoped ADRs, and this is a major source of friction, amendments, superseding, etc.

- [ ] Create a script that is meant for use by the human-user of the consuming v5 repo.

  This will be a CLI tool that allows the user to select what standards packages they want to enable in their repo, and also choose any optional tooling/skills/features/etc. that they want to enable. The script will then generate the appropriate config files and add them to the repo.

## Agent tasks

### Maintenance

- [x] Migrate the consumer fleet to github-workflow 1.7 (MS-6 item 2). Completed 2026-08-31: all 24 locally
  cloned consumers at release 5.26.0, the five package-enabled ones at github-workflow 1.7 with byte-identical
  deployed binaries. Recorded in SPEC-GHW1 rev 1.37 and `docs/handoff/deployed.md`. Repair-on-touch of active
  PRs elsewhere remains the standing 1.7 behavior, not a task.

- [ ] Provide total-count truncation evidence for array-shaped list endpoints (security finding 4, deferred
  beyond NFR-007's server-misbehavior precondition).

- [ ] Re-measure the github-workflow session corpus (#191). Re-scoped 2026-08-31: the post-1.5 window was overtaken
  by 1.6 and 1.7 before it opened — 1.7 moved the surfaces F3/F4/F8 measure — so the measurement now runs against a
  post-1.7 window opening ~2026-09-11, with 1.7's baselines rather than 1.5's.

- [ ] Owner: decide whether to trim `AGENTS.md` and `CLAUDE.md`, which exceed their agent-handoff byte budgets.

  `handoff-validate` reports `AGENTS.md` 5461 against a 4096 cap and `CLAUDE.md` 4036 against 2048 — warnings, not
  errors, so nothing is blocked. Both grew again when the PR-admission rule landed (#208), which is the expected
  cost of stating a non-negotiable precisely. The question is whether the eager budget is still the right size for
  this repository or whether detail should move to a lazy document; both answers are defensible and it is a
  judgment call, not a defect.

- [ ] Fix [#209](https://github.com/L3DigitalNet/project-standards/issues/209) (P1): the `AGENTS.md` Prettier gate
  exits 123 on a clean tree because the Git corpus hands payload symlinks to Prettier. Triaged 2026-09-01 along with
  [#207](https://github.com/L3DigitalNet/project-standards/issues/207),
  [#210](https://github.com/L3DigitalNet/project-standards/issues/210), and
  [#215](https://github.com/L3DigitalNet/project-standards/issues/215) (all P2) and
  [#211](https://github.com/L3DigitalNet/project-standards/issues/211) (P3, bundle with the next markdown-tooling cut).

- [ ] [#218](https://github.com/L3DigitalNet/project-standards/issues/218) (P2): make the github-workflow standard
  itself exempt Agent Handoff documents from the T0-or-PR rule; this repository's `CLAUDE.md`/`AGENTS.md` carve-out
  (`d5792907`) is interim and comes out once the managed block carries it.

- [ ] Cut python-tooling 1.18 for the three adoption reports. #204 is a real guard defect (`build_backend = "none"`
  exempts the `[project]` check `uv lock` needs, and `adopt.md` lines 21 and 23 contradict each other); #205 and
  #206 are documentation gaps over mechanisms the key-ownership invariant already provides. Evidence is on each
  issue.

- [ ] Owner: resolve SPEC-GSF3 OQ-001, which blocks that plan's T1.

- [ ] Owner: define issue #129 (ADR mechanical guardrails). `Workflow: Needs definition`; the v5.17.0 starting
  brief at `docs/design/adr-conformance/2026-08-05-adr-mechanical-guardrails-v5.17-feature-proposal.md` is preserved
  as historical input, but a formal specification still needs owner decisions and current-state re-derivation.

- [ ] Migrate `agent-ventures` and `llm-wiki` off `.agents`-only skill trees onto the dual-tree layout, per the
  2026-08-26 session-corpus review's F2 finding.

- [ ] Authorize an MCP roadmap revision that distinguishes delivered v1 work from deferred write and remote phases.

- [ ] Benchmark the fast release gate under controlled conditions and dial in worker counts and lane concurrency.
  Now subsumed by research issue #207, which measured a 106-minute full battery and enumerated six levers.

  _(Owner 2026-07-31: the spike measured under real-usage load; `VERIFY_ORDINARY_WORKERS`/`VERIFY_COMPAT_WORKERS` overrides in `scripts/verify.sh` exist for the sweep.)_

- [ ] Retire `control_plane/provider_inputs.py` in favour of payload-declared provider input shapes.

  The T15 seam consolidated four private per-standard input constructions behind one fail-closed authority — correct for a shared module, but it keeps per-standard knowledge in the engine. The owner recorded payload-declared input shapes as that module's retirement path once the MCP hold lifted (freeze J-N, 2026-07-30, resolution A).

- [ ] Complete the approved future-artifact cleanup.

- [ ] Decide whether Python Coding 0.6 remains reference-only or proceeds toward consumer adoption.

### Future programs

#### Agent-managed repository

- [ ] Revisit self-hosted CI under `agent-managed-repo`; owner deferred it from v5.13.0 on 2026-07-31.

  Use the approved dedicated-group architecture and hardening program in `docs/research/2026-07-31-self-hosted-runner-security-review.md`.

- [ ] Author and approve the Usage Documentation Site specs from the [approved V2 design brief](specs/2026-08-02-usage-documentation-site-v2-design.md).

  Give the new specifications new IDs, dates, and filenames; preserve the original SPEC-U000 through SPEC-U007 bundle and transcript unchanged. Include the compatible CLI Documentation successor needed for a site-contained canonical CLI reference, then review the new set before implementation planning.

- [ ] Design template-repository autopopulation against the now-released `project-toolbox` (v5.21.0).

- [ ] Specify and release the `agent-managed-repo` standard after `project-toolbox`.
  - [ ] After release, reconcile this repository's GitHub settings against `agent-managed-repo`.
