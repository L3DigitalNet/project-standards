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

- [ ] **Elevated Priority:** [frontmatter schema migration tool](feature-proposal-frontmatter-migration.md):

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

- [ ] Execute the [open-issue resolution program](plans/2026-08-01-open-issue-resolution-program-plan.md).

  Remaining work is the feature phase T24–T29 for #62 (conformance linting) and #55 (house-format conversion); T24 is dependency-ready. #116 stays deferred alongside them by owner decision (2026-08-05, defect fixes only). The deferred-tooling phase closed in v5.16.0 — see `docs/handoff/deployed.md` for what shipped.

- [ ] Deliver the v5.17.0 ADR train: amendment vocabulary (#127) plus corpus remediation (#128).

  Owner decision 2026-08-05: bundle both and target **5.17.0** (MINOR — `adr` 1.4 → 1.5 becomes the Catalog 5 default). Ship #127 as `adr` 1.5 first, then the 21 backlog items in `docs/reviews/adr-conformance/2026-08-05-1941-adr-1-4-conformance-assessment.md` §10 using the 1.5 amendment form. `adr` 1.5 must stay non-breaking or it cannot become the default within catalog major 5.

- [ ] Authorize an MCP roadmap revision that distinguishes delivered v1 work from deferred write and remote phases.

- [ ] Benchmark the fast release gate under controlled conditions and dial in worker counts and lane concurrency.

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

- [ ] Specify and release the provider-neutral `project-toolbox` standard, including its proven workflows and routing skill.
  - [ ] After release, design template-repository autopopulation against `project-toolbox`.

- [ ] Specify and release the `agent-managed-repo` standard after `project-toolbox`.
  - [ ] After release, reconcile this repository's GitHub settings against `agent-managed-repo`.
