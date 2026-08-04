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

- [ ] In the ADRE standards package: tighten ADR scoping and authoring guidance.

  Provide tigher guidance on how to write ADRs that are clear, concise, properly scoped, bounded to prevent forcing requirements on non-relevant stakeholders, etc. Particularly for scope, boundaries, and awareness of potentially affected stakeholders, provide a checklist or template for authors to follow.

  Agents have been quite terrible at writing properly scoped ADRs, and this is a major source of friction, ammendments, superseding, etc.

- [ ] Create a script that is meant for use by the human-user of the consuming v5 repo.

  This will be a CLI tool that allows the user to select what standards packages they want to enable in their repo, and also choose any optional tooling/skills/features/etc. that they want to enable. The script will then generate the appropriate config files and add them to the repo.

## Agent tasks

### Maintenance

- [x] Define whether owner-designated release levels may exceed `check-release` and `meta/versioning.md` classification.

  Resolved 2026-08-01: only the owner designates MAJOR. Otherwise, a newly introduced package or an advertised version above that package's prior advertised maximum is exactly MINOR; no package advance is exactly PATCH.

  Internal and reference-only packages count; retained older versions and unadvertised payloads do not. Advertised versions are permanent and cannot be removed, even in a MAJOR release. T30 implemented the contract in `e10083ad`.

- [x] Finish Agent Handoff consumer retirement.

  Closed 2026-08-04 by T32 (`73e42d0f`). Both remaining protected merges landed as PR #1 in `website-aboutme` and `website-l3digital.net`; `docmend` and `hw-radar` were already converged.

  `llm-wiki` shape overflows are resolved and `~/scripts` reconciles clean. `control-center` stays on legacy config, blocked by issue #83, owner-handled — not engine-blocked. Ledger: `docs/research/2026-07-09-agent-handoff-retirement-inventory.md`.

- [ ] Execute the [open-issue resolution program](plans/2026-08-01-open-issue-resolution-program-plan.md).

  The owner-approved v5.15.0 boundary is T9–T14, T17, T18, T20, T23, T31, T33–T35, and T37. Every boundary task is `done` except T35; T1 and T32 closed independently.

  Revision 3 stands at 17 done, 2 superseded, 16 not-started, and T35 blocked: the owner withheld publication on 2026-08-04 to widen the v5.15.0 boundary, so a plan revision likely precedes resume.

  Remaining not-started work is post-v5.15.0: T2–T8, T16, T19, T22, T24–T29, and T36. Never credit legacy scratch state.

- [ ] Authorize an MCP roadmap revision that distinguishes delivered v1 work from deferred write and remote phases.

- [ ] Benchmark the fast release gate under controlled conditions and dial in worker counts and lane concurrency.

  _(Owner 2026-07-31: the spike measured under real-usage load; `VERIFY_ORDINARY_WORKERS`/`VERIFY_COMPAT_WORKERS` overrides in `scripts/verify.sh` exist for the sweep.)_

- [ ] Retire `control_plane/provider_inputs.py` in favour of payload-declared provider input shapes.

  The T15 seam consolidated four private per-standard input constructions behind one fail-closed authority — correct for a shared module, but it keeps per-standard knowledge in the engine. The owner recorded payload-declared input shapes as that module's retirement path once the MCP hold lifted (freeze J-N, 2026-07-30, resolution A).

- [ ] Advance `cryptography` past PYSEC-2026-3552 before the v5.15.0 release gate.

  `pip-audit` reports `cryptography` 49.0.0 vulnerable (aliases GHSA-g6cj-pr64-35w5, CVE-2026-69247); the fix is 50.0.0. It is a transitive dependency, so the lock needs the advance.

- [ ] Restore mid-cycle control-plane access: scope the lineage assertion, then add a producer role (issue #123).

  `build_planner_request` calls `plan_catalog_refresh` unconditionally, so `validate`, `drift-check`, `shape-check`, `size-report`, `legacy-report`, `standards show`, `reconcile --check`, and `reconcile --plan` all fail with `catalog changed but its tool release did not advance`.

  Owner decision 2026-08-04, two parts. First, assert lineage only on catalog-advancing paths (`reconcile --apply`, `init`, `upgrade`); nothing else decides lineage, and no severity changes.

  Second, add `role` to `[project_standards]`, defaulting to `"consumer"`. `"producer"` permits exactly one thing: installed catalog ≠ committed catalog at the same tool release, so advancing commands run mid-cycle.

  `ControlHeader` is a strict model pinned to `schema_version = "1.0"`, so `role` is a versioned contract change requiring header schema 1.1, migration, compatibility rows, and consumer documentation. Precedent: `ConsumerLock` accepts `["1.0", "1.1"]`.

  Belongs in the widened v5.15.0 boundary; the master plan requires a plan-authoring revision before T35 resumes.

- [ ] Complete the approved future-artifact cleanup.

- [ ] Decide whether Python Coding 0.6 remains reference-only or proceeds toward consumer adoption.

### Future programs

#### Agent-managed repository

- [ ] Revisit self-hosted CI under `agent-managed-repo`; owner deferred it from v5.13.0 on 2026-07-31.

  Use the approved dedicated-group architecture and hardening program in `docs/research/2026-07-31-self-hosted-runner-security-review.md`.

- [ ] Author and approve v5.16.0 Usage Documentation Site specs from the [approved V2 design brief](specs/2026-08-02-usage-documentation-site-v2-design.md).

  Give the new specifications new IDs, dates, and filenames; preserve the original SPEC-U000 through SPEC-U007 bundle and transcript unchanged. Include the compatible CLI Documentation successor needed for a site-contained canonical CLI reference, then review the new set before implementation planning.

- [ ] Specify and release the provider-neutral `project-toolbox` standard, including its proven workflows and routing skill.
  - [ ] After release, design template-repository autopopulation against `project-toolbox`.

- [ ] Specify and release the `agent-managed-repo` standard after `project-toolbox`.
  - [ ] After release, reconcile this repository's GitHub settings against `agent-managed-repo`.
