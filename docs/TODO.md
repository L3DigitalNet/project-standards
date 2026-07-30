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

- [ ] **HIGH PRIORITY — reconcile the retirement records for the retired `agent-handoff-v3` engine repository.** The owner retired the deprecated engine on 2026-07-30: the private GitHub repository `chrisdpurcell/agent-handoff-v3` was **archived read-only**, and the local checkout `/home/chris/projects/agent-handoff-v3` was **deleted**. Three repository documents still instruct a reader not to delete it and pin evidence to a local path that no longer exists, so they are unresolvable as written. Everything needed to close them is inlined below, so **no clone of the archive is required**; the archive is the fallback of last resort, not the working source. This is narrow documentation maintenance and is intended to be compatible with the MCP change hold, but confirm with the owner before widening it.
  - [ ] Rewrite the **Deletion checkpoint** in `docs/research/2026-07-09-agent-handoff-retirement-inventory.md` (currently the last section, status **blocked**). It states "Do not delete `/home/chris/projects/agent-handoff-v3` or its remote repository until every ledger row is resolved, the released package passes the disposable probes, the final search is clean, and the owner explicitly approves deletion." Record the actual outcome instead: gate 2 (published release) and gate 4 (owner approval) were satisfied, gate 1 was satisfied for engine retirement but not for full v5 adoption, and gate 3 was never run inside this repository. Do not silently delete the checkpoint; it is the record of how the retirement was authorized. Note that archiving is reversible on GitHub, but the local checkout deletion is not.
  - [ ] Correct the **Consumer ledger** in the same file against verified 2026-07-30 state. `agent-configs` is no longer "Pending / dirty owner work" — it migrated to the package on 2026-07-26 and now passes validate and drift-check at exit 0. `doc-proc-scripts-kate-decision` is no longer a pending "protected no-upstream topic worktree" — it was a Git worktree of `doc-proc-scripts` pinned to the local-only branch `codex/kate-integration-model` (tip `2d28849`, 2026-07-07); the worktree was removed and the branch deleted on 2026-07-30 after proving `main` carried a newer superset of every file on it, so the row should close as resolved and the artifact no longer exists to inspect.
  - [ ] Record that no repository on the machine ran the v3 engine as of 2026-07-30, verified by sweeping every clone under `~/projects` and `~/scripts`, the twelve worktrees under `~/.config/superpowers/worktrees/`, and loose clones under `~/` for a `.claude/`, `.codex/`, or `.agents/` `session_start.py` and for a root `STATUS.md`/`TODO.md` pair. The final v3 installation found anywhere was the `doc-proc-scripts` worktree above; it was Codex-side only, which a Claude-path-only search does not detect.
  - [ ] Update the four repositories migrated to catalog 5 on 2026-07-30: `website-aboutme` (`c06dc05`, `testing`), `progressive-apparel` (`a6adee7`, `main`), `website-l3digital.net` (`bf27833`, `testing`), and the `projects` meta-repo (`3fd7aee`, `main`). Four consumers still owe a protected merge to `main`: `docmend` and `hw-radar` from `dev`, `website-aboutme` and `website-l3digital.net` from `testing`.
  - [ ] Record the published-release recheck the ledger defers per row as done: 19 of 21 package consumers pass both validate and drift-check at exit 0 against published `5.11.0`. Two exceptions remain, neither a package defect — `llm-wiki` exits 1 on two consumer shape overflows (`docs/TODO.md:29` at 224 characters against 160, `docs/handoff/state.md:8` at 141 against 140), and `~/scripts` exits 3 with "selected command package is not reconciled: agent-handoff" and needs `reconcile --apply`.
  - [ ] Resolve the two pins that will dangle: `docs/plans/2026-07-09-agent-handoff-standard-package.md` line 18 names "Pinned legacy evidence source: `/home/chris/projects/agent-handoff-v3` commit `56b24df7279572c485c2512783b0cc7e5395429b`", and line 1291 repeats the pre-deletion approval gate. `docs/research/2026-07-09-agent-handoff-ingestion-inventory.md` line 23 pins the same path and commit in its `source` frontmatter. Annotate them as no longer resolvable at that local path rather than rewriting the history they record; the commit itself still exists in the read-only archive. Note that the frontmatter `source` value can no longer be validated against a live local target.
  - [ ] **Do not remove the v3 detection logic.** `src/project_standards/agent_handoff/legacy.py`, `integrations/claude.py`, and `integrations/codex.py`, the seven `legacy-migration.md` copies under `standards/agent-handoff/`, the `bundles/agent-handoff/resources/` copy, `docs/adoption-prompt.md`, and five `tests/agent_handoff/` modules reference v3 only by **name**, as detection strings for a legacy layout. The engine repository being gone does not mean legacy repositories are gone, so deleting these would silently break legacy detection and migration. A sweep that treats every `agent-handoff-v3` or `handoff-system-v3` occurrence as dead is wrong; 25 tracked files mention it and none requires the checkout.
  - [ ] Run the outstanding final operational-dependency search inside this repository and record the result, since gate 3 of the deletion checkpoint was never executed. A read-only sweep on 2026-07-30 found no file requiring the checkout, but that was not captured as this repository's own evidence.
  - [ ] Preserve these engine facts, which exist in no active repository and otherwise require re-cloning the archive. Final engine HEAD was `11ccbf7` (2026-07-27) and the pinned evidence commit was `56b24df7279572c485c2512783b0cc7e5395429b`. Schema version was 3.4. The engine was **dual-harness**: one canonical hook installed byte-identically to both `.claude/hooks/session_start.py` and `.codex/hooks/session_start.py`, with the Codex side registered in `.codex/config.toml` under `[[hooks.SessionStart]]` as `bash -c 'python3 "$(git rev-parse --show-toplevel)/.codex/hooks/session_start.py"'`. Its layout was root `STATUS.md` and `TODO.md` beside `docs/handoff/{state,deployed,architecture,credentials,conventions,specs-plans}.md`, `docs/handoff/sessions/`, and `docs/handoff/bugs/`, with a repo-local skill directory named `handoff-system-v3`. Its validators lived at `agent-handoff-v3/scripts/handoff/` as `validate-layout.sh` (18,502 bytes), `_handoff-lib.sh` (5,168 bytes), `validate-shape.sh` (267 bytes), and `size-report.sh` (261 bytes). Its specification was `docs/specs/agent-handoff-v3.md` at 746 lines and 64,831 bytes. No copy was taken into any active repository, so the read-only GitHub archive is the only remaining source for it and for the four validator scripts.
  - [ ] Note that `control-center` is the only repository still on a legacy `.project-standards.yml` and is unrelated to the engine retirement. It is blocked by issue #83, the V4 Python Tooling package-transform evidence check, and the owner is handling it manually. No ledger row should treat it as engine-blocked.

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
  - [ ] Continue with T11 (installed-wheel client proof and documentation) when directed. _(Owner 2026-07-30: OQ-005 smoke set = mandatory fixtures + this repo + `~/scripts`; a default-on codex `mcp_2026_07_28` flag authorizes a narrow T1 matrix refresh inline; T10 context ceilings stay reviewed test constants.)_
  - [ ] At T11, re-check whether codex-cli has enabled `mcp_2026_07_28` by default (flag registered disabled in 0.146.0, openai/codex#34747) before capturing the FR-030 probe evidence.

- [ ] Maintain the temporary MCP project change hold until implementation-plan T12 closes: avoid significant non-MCP features, architectural refactors, standards-package programs, release trains, or other broad repository changes. Keep necessary maintenance narrow, and obtain owner direction before any exception that could disturb the MCP baseline. _(Owner 2026-07-29: standards packages stay locked until the MCP server is live, except minor-level version changes; standards v5.12.0 ships with the MCP server.)_

- [ ] Specify and release the provider-neutral `project-toolbox` standard, including its proven workflows and routing skill.
  - [ ] After release, design template-repository autopopulation against `project-toolbox`.

- [ ] Specify and release the `agent-managed-repo` standard after `project-toolbox`.
  - [ ] After release, reconcile this repository's GitHub settings against `agent-managed-repo`.
