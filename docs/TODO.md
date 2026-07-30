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

  Decide when identifiers such as `SPEC-MT01` must link to their canonical documents. Define checks for inconsistent or missing links, maintenance of `related:` frontmatter, graph generation, and safe reconciliation of detected drift. _(Owner 2026-07-29: deferred past implementation-plan T12 under the MCP hold.)_

- [ ] Define structure and formatting instructions for `docs/STATUS.md`.

  The current snapshot is concise; define durable formatting rules so future updates preserve that shape. _(Owner 2026-07-29: deferred past implementation-plan T12 under the MCP hold.)_

- [x] Decide the `standards://` URI alignment flagged in ADR 0026: the shipped catalog index publishes three-segment resource URIs (and `render_catalog` can emit a two-segment form) while the served MCP grammar is the four-segment SPEC-MS01 form with no alias. Aligning the producers, `SPEC-MS01`, and ADR 0010 on one form is an owner decision outside T1. _(Decided 2026-07-29: the four-segment SPEC-MS01 form is canonical everywhere; both producers align in a narrow directed commit after T3, before T6. Tracked as an agent task below.)_

- [x] Review the T2 DTO shapes chosen under the overnight "sane defaults" directive.

  `mcp_services` exports nested `RelationshipSet` and summary-level `ProviderDescriptor` (identity/operation/kind/phase/effect), which the plan §5.5 DTO table implies but does not define field-by-field. Both Codex reviews flagged the gap; rationale is in the T2 evidence logs. Ratify or direct a §5.5 amendment before T6/T8 map them onto protocol surfaces. _(Reviewed 2026-07-29: extend `ProviderDescriptor` with entrypoint, schema references, and resource set via a §5.5 amendment before T3; `RelationshipSet` is ratified as built. Tracked as an agent task below.)_

- [x] Create durable repo rule: `docs/superpowers/` is a forbidden path. Nothing should get saved here. Use `docs/plans/` and `docs/specs/` instead. _(Done 2026-07-19: the directory is deleted, its contents relocated, and the rule is recorded in `AGENTS.md` Working Rules.)_

- [x] Ensure full meta-repo tooling functionality is documented. _(Done 2026-07-19: audited the full tooling surface — CLI leaves/options, console scripts, `scripts/` helpers, workflows, pre-commit hooks, coherence suite — and closed the gaps: `.pre-commit-hooks.yaml` documented in `README.md`, repo-CI workflow inventory documented in `tests/README.md` § CI relationship, stale bundle-authoring `2.0` references bumped to `2.1`.)_

## Agent tasks

### Maintenance

- [ ] Finish Agent Handoff consumer retirement.

- [ ] Complete the approved future-artifact cleanup.

- [ ] Decide whether Python Coding 0.6 remains reference-only or proceeds toward consumer adoption.

### Future programs

- [ ] Review and approve the Usage Documentation Site specification set before implementation planning.

- [ ] Complete the reviewed MCP implementation plan.
  - [x] Resume T1 only after the final 2026-07-28 protocol publication and official stable Python SDK release evidence are available. _(Done 2026-07-28: final publication and `mcp` 2.0.0 verified twice.)_
  - [x] Verify the protocol, SDK, license, conformance, and current Codex/Claude client capabilities in the dated evidence matrix. _(Done 2026-07-28: `docs/research/2026-07-28-project-standards-mcp-protocol-sdk-client-matrix.md`.)_
  - [x] Create and accept ADRs 0025-0026, obtain the recorded owner decisions required by T1, resolve the assigned SPEC-RD01/SPEC-MS01 open questions, and update their revisions and indexes. _(Done 2026-07-28 with recorded owner approvals; SPEC-RD01 1.6, SPEC-MS01 1.3.)_
  - [x] Pin the approved SDK dependency, update `uv.lock`, and pass the T1 lock, audit, client-probe, candidate-wheel, specification, and documentation gates. _(Done 2026-07-28: commit `d695d46`.)_
  - [x] Begin MCP source implementation at T2 only after T1 completes. _(Done 2026-07-28: commit `e06da3b` — SDK-free facade construction plus exact catalog/standard/resource services, Codex-reviewed RED and GREEN, full battery green under the rebuilt candidate wheel.)_
  - [x] Extend `ProviderDescriptor` (entrypoint, schema references, resource set), define both DTOs field-by-field in plan §5.5, and update `models.py` plus the T2 contract tests. _(Done 2026-07-29: discovered-work task T13, commit `b8effb1`.)_
  - [x] Continue with T3 (consumer inspection and reconciliation services) when directed. _(Done 2026-07-29: commit `6e4e7e8` after Codex RED and GREEN reviews; five harvest items recorded in plan notes.)_
  - [x] Align both `standards://` producers on the four-segment form and regenerate `standards/catalog.md`. _(Done 2026-07-29: commit `e400f83`, 917 rows; ships in standards v5.12.0 with the MCP server.)_
  - [x] Continue with T4 (bounded non-mutating provider services) when directed. _(Done 2026-07-29: commit `b2b9964` after Codex RED and GREEN reviews; two rejected sandbox-architecture demands recorded as T10 hardening candidates in plan notes.)_
  - [x] Continue with T5 (stdio adapter and capability boundary) when directed. _(Done 2026-07-29: commit `72794ea` after Codex RED and GREEN reviews; `project-standards mcp` serves both protocol eras from the low-level SDK server; contract amendments at `e071aa7`.)_
  - [x] Continue with T6 (expose exact resources) when directed. _(Done 2026-07-29: commit `92380e0` after Codex RED and GREEN reviews; exact catalog/package/payload resources served on both eras with a compact field-masked catalog body.)_
  - [x] Continue with T7 (declared prompts and shared read fallback) when directed. _(Done 2026-07-29: commit `572d84b` after Codex RED and GREEN reviews; prompts truthfully absent, matrix-gated `standard_read` fallback live.)_
  - [x] Finish T8 (catalog and repository inspection tools). _(Done 2026-07-30: commit `614e7e2` after rerun Codex RED and GREEN reviews, all findings accepted; discovery tools registered unconditionally with closed typed schemas.)_
  - [x] Continue with T9 (reconciliation and provider tools) when directed. _(Done 2026-07-30: commit `7b46a30` after Codex RED and GREEN reviews, all findings dispositioned; contract amendments `223fcd5`.)_
  - [x] Continue with T10 (protocol, safety, determinism, and CI proof) when directed. _(Done 2026-07-30: commit `e30862f` after Codex RED and GREEN reviews, all findings dispositioned; ADR 0026 taxonomy amendments `2c75bea`/`0323bb1`.)_
  - [ ] Continue with T11 (installed-wheel client proof and documentation) when directed.
  - [ ] At T11, re-check whether codex-cli has enabled `mcp_2026_07_28` by default (flag registered disabled in 0.146.0, openai/codex#34747) before capturing the FR-030 probe evidence.

- [ ] Maintain the temporary MCP project change hold until implementation-plan T12 closes: avoid significant non-MCP features, architectural refactors, standards-package programs, release trains, or other broad repository changes. Keep necessary maintenance narrow, and obtain owner direction before any exception that could disturb the MCP baseline. _(Owner 2026-07-29: standards packages stay locked until the MCP server is live, except minor-level version changes; standards v5.12.0 ships with the MCP server.)_

- [ ] Specify and release the provider-neutral `project-toolbox` standard, including its proven workflows and routing skill.
  - [ ] After release, design template-repository autopopulation against `project-toolbox`.

- [ ] Specify and release the `agent-managed-repo` standard after `project-toolbox`.
  - [ ] After release, reconcile this repository's GitHub settings against `agent-managed-repo`.
