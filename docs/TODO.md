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

- [ ] Execute the [open-issue resolution program](plans/2026-08-01-open-issue-resolution-program-plan.md).

  Remaining work is the feature phase T24–T29 for #62 (conformance linting) and #55 (house-format conversion); T24 is dependency-ready. #116 shipped in v5.18.0 as `python-tooling` 1.13. The deferred-tooling phase closed in v5.16.0 — see `docs/handoff/deployed.md` for what shipped.

- [x] Triage the v5.18.0 follow-ups #156–#167.

  Completed 2026-08-09 as part of a full triage of all 20 open issues except #168; every issue carries a verified comment. See `docs/handoff/sessions/2026-08.md`.

- [ ] Decide the release shape for the triaged backlog.

  `ROADMAP.md` scopes 5.19.0 to `project-toolbox` alone (owner direction 2026-08-09), which does not accommodate the 20 triaged issues. #168's title says v5.20.0 while its body says v5.19.0. The triage recommends inserting a consolidation train and moving `project-toolbox` to the release after; explicit deferral with recorded reasoning is the alternative.

- [x] Resolve the seven owner decisions blocking specification.

  All seven resolved 2026-08-10; each issue carries its decision, rejected alternatives, and release classification.

- [ ] Implement the `command` provider kind (#142).

  Extract the bounded runner from `mcp_services` so the control-plane CLI path shares it — that path dispatches in-process with no timeout today. Preserve every ADR 0025 property, including the third-descriptor result transport.

  Then define the subprocess resource transport, materialize the entrypoint to disk with mode `0755` and verify it against its payload digest, declare platform targets, gate committed binaries reproducibly, and record the ADR. `agent-handoff`'s 1499-line provider migrates once the runner lands.

- [ ] Add the create-only content-match advisory (#157).

  Compare the consumer's file content against the create-only artifact digest of every advertised version, in `validate` and `drift-check`. Engine-only, so PATCH. Amend ADR 0028 with the decision, the rejected refresh path, the customized-copy limit, and the dependency on permanent advertisement. Bug 006 closes against it.

- [ ] Ship `vscode.task_prefix` and the governing-option diagnostic (#153).

  A closed enum defaulting to `""`, implemented as option-gated contribution sets; reserved-label documentation in `adopt.md`; a migration note for consumers who already renamed.

  The diagnostic already names the owning package — only the governing option is missing, and `_classify_removed` sees just the `LockedUnit`. Verify whether an already-renamed consumer lands on `ActionKind.ADOPT`.

- [ ] Stabilize the two real-provider MCP proofs (#158).

  Inject `PROVIDER_TIMEOUT_SECONDS` in both, as nine other tests do. Measure unloaded timing first and record it: a result near 30 s is a production defect for consumers on modest hardware, not a test-isolation problem.

- [ ] Land the three ADR decisions before #162.

  #161 (ADR 0026 owns URI grammar, 0010 adopts by reference; both records carry a stale "open alignment item" claim closed at `e400f83f`), #160 (record ADR 0024's coupling as load-bearing, with a reader's map), #159 (new ADR owning the `.agents/` root, per-class allocation, `standard-id` keying, `.agents/skills/` grandfathered). #162 touches every active ADR body, so it goes last.

- [ ] Sweep #162 with `git grep`, never a recursive grep.

  Re-measured 2026-08-10 and the recorded scope holds: 46 tracked hits across 17 files (`adr-0025` 21, `adr-0026` 25). Raw `grep -r` reports 65 files because two git-excluded agent worktrees under `.claude/worktrees/` carry copies that must not be edited — the same inflation turned ADR 0024's 23 tracked files into 100 raw hits.

- [ ] Declare platform targets for the shipped `github-workflow` binary.

  `standards/github-workflow/versions/1.1/payload.toml` installs `bin/gh-workflow` as a plain `mode = "0755"` artifact with no platform declaration and no degradation path, though it is `ELF 64-bit x86-64` built `GOOS=linux GOARCH=amd64`. Harmless in the current internal population; covered by the same work as #142's item 5.

- [ ] Apply triage field values to the 20 issues.

  Twelve sit in Inbox with no Priority and seven at `Needs definition`. Priority is an owner call and `Execution mode` is never self-promoted, so nothing was applied.

- [ ] Reconcile the stale open-issue-program executor state.

  `.project-pipeline/2026-08-01-open-issue-resolution-program/p4.md` and `p10.md` record T16/T19/T36 as `not-started` although all three completed 2026-08-05 (`50d0c364`, `229a4bc1`, `e13e1a66`). Reconcile through the execute-plan skill, never by hand.

- [ ] Scope the 5.19.0 `project-toolbox` release.

  Owner direction 2026-08-09. #129 (`adr-conformance` foundation) remains open and unscheduled; both its prerequisites #127 and #128 are now closed, and its decision 10 must be re-derived from ADR 0028 as amended.

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
