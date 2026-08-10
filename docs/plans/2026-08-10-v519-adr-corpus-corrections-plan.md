---
plan_format: 3
title: 'v5.19 ADR Corpus Corrections Implementation Plan'
slug: 'v519-adr-corpus-corrections'
status: active
revision: 1
revises_revision: 0
revision_reason: 'initial plan'
pause_reason: ''
source: 'issues L3DigitalNet/project-standards#161, #160, #159, and #162; owner decisions recorded 2026-08-10'
spec_ref: ''
created: 2026-08-10
updated: 2026-08-10
owners:
  - 'Project Standards maintainers'
---

# v5.19 ADR Corpus Corrections Implementation Plan

> **Definition, not state.** Plan authoring did not generate execution state. During execution, the orchestrator alone generates and mutates ephemeral state under `.project-pipeline/2026-08-10-v519-adr-corpus-corrections/execution/`.

## 1. Objective

Make the active Architecture Decision Record (ADR) corpus state one unambiguous authority for each of four settled documentation concerns before v5.19: ADR 0026 owns the four-segment Model Context Protocol (MCP) resource URI grammar while ADR 0010 adopts it by reference; ADR 0024 records why its coupled version-channel decision stays together; a new ADR allocates the platform-owned `.agents/` root; and every active ADR distinguishes evidence from current authority before ADRs 0025 and 0026 are atomically renamed with all tracked inbound references.

The work is documentation-only. It preserves every accepted `## Decision Outcome` sentence as historical decision text, adds cumulative amendments or a new record where governance changes, preserves stable ADR IDs, and changes no immutable standard payload, implementation behavior, release policy, GitHub work item, or Agent Handoff state.

## 2. Authority and Source Map

| Source | Source Role | Authority / Use | Version / Date | Affected Plan Surface |
| --- | --- | --- | --- | --- |
| `request` | normative | Exact four-task sequence, settled outcomes, release-wide T4 corpus-freeze entry gate, preservation rules, docs-only release boundary, validation floor, and prohibited mutations. | 2026-08-10 | §§1, 3–13; T1–T4 |
| `issue:L3DigitalNet/project-standards#161` | normative | Owner comment `5235622130`: ADR 0026 owns the four-segment grammar; ADR 0010 adopts it by reference and keeps its exclusion; producer divergence was resolved by `e400f83f`; no edge work or payload cut. | 2026-08-10 | §§3–6; T1 |
| `issue:L3DigitalNet/project-standards#160` | normative | Owner comment `5235640800`: ADR 0024 stays one record because the alternatives jointly determine advertisement, selectors, and classification; add rationale and a reader map; do not touch `meta/versioning.md`. | 2026-08-10 | §§3–6; T2 |
| `issue:L3DigitalNet/project-standards#159` | normative | Owner comment `5235656273`: a new ADR makes `.agents/` platform-owned and allocates subtrees per artifact class, defines coexistence/keying, grandfathers skills, accepts collision risk, and relates to ADRs 0016, 0021, and 0022. | 2026-08-10 | §§3–6; T3 |
| `issue:L3DigitalNet/project-standards#162` | normative | Owner comment `5235798257`: apply the repository-local evidence-versus-authority convention across all active ADRs; rename ADRs 0025/0026 last; use a Git-tracked census whose recorded scope is 46 hits across 17 files. | 2026-08-10 | §§3–7; T4 |
| `issue:L3DigitalNet/project-standards#157` | normative | Owner comment `5235741187` requires an ADR 0028 amendment recording the create-only generated-file decision; its integrated ADR checkpoint is a minimum input to T4's release-wide corpus freeze. | 2026-08-10 | §§3–7, 9–12; T4 entry gate |
| `issue:L3DigitalNet/project-standards#142` | normative | The owner decision requires a control-plane ADR recording the accepted command-provider direction, portability posture, and rejected alternative; its integrated ADR checkpoint is a minimum input to T4's release-wide corpus freeze. | 2026-08-10 | §§3–7, 9–12; T4 entry gate |
| `issue:L3DigitalNet/project-standards#169` | current-state evidence | The issue is open and permits either an ADR or changelog record for its MCP decision; no owner-approved ADR-writing outcome is settled at plan authoring. | 2026-08-10 | §§3, 9–12; conditional T4 entry gate |
| `issue:L3DigitalNet/project-standards#167` | current-state evidence | The issue is open and its final decision-record shape is not settled at plan authoring. | 2026-08-10 | §§3, 9–12; conditional T4 entry gate |
| `repo:standards/adr/versions/1.5/README.md#amendment-workflow` | decision | Amendments are cumulative, do not rewrite accepted outcome prose, keep active status, and use reciprocal fields only for an external ADR amendment. A widened concern needs a new record. | `5e1b04f1` | §§3–5, 9–10; T1–T3 |
| `repo:docs/adr/README.md#reading-this-corpus` | decision | Repository-local convention: `source` and More Information retain frozen evidence; `related` and body prose point to current authority. | `5e1b04f1` | §§4–7; T4 |
| `repo:docs/adr/adr-0010-standard-resource-uris-and-index.md#decision-outcome` | current-state evidence | Existing declaration/index boundary, explicit MCP wire-grammar exclusion, reciprocal relation to ADR 0026, and stale open-divergence statement. | `5e1b04f1` | §§4–5; T1 |
| `repo:docs/adr/adr-0026-project-standards-mcp-local-read-only-transport.md#resource-uri-grammar` | decision | Three permitted forms, the four-segment resource form, and canonicalization/error commitments that remain frozen. | `5e1b04f1` | §§4–6; T1 |
| `repo:src/project_standards/standards_graph/catalog.py::_render_package_catalog` | current-state evidence | Commit `e400f83f` changed the repository-backed catalog resource producer to the four-segment form on 2026-07-29. | `e400f83f` | §§4–7; T1 |
| `repo:src/project_standards/standards_graph/catalog.py::render_catalog` | current-state evidence | Commit `e400f83f` changed the graph-backed catalog resource producer to the same four-segment form on 2026-07-29. | `e400f83f` | §§4–7; T1 |
| `repo:docs/adr/adr-0024-catalog-scoped-package-version-channels.md#considered-options` | current-state evidence | The option set jointly determines advertisement, selectors, and classification. | `5e1b04f1` | §§4–6; T2 |
| `repo:docs/adr/adr-0024-catalog-scoped-package-version-channels.md#decision-outcome` | current-state evidence | One accepted record currently holds advertisement, selector/authorization, classification, and forbidden-transition rules. | `5e1b04f1` | §§4–6; T2 |
| `repo:docs/adr/adr-0016-package-markdown-frontmatter-skill-with-standard.md#decision-outcome` | current-state evidence | Special-case ownership and installed skill destination that the new root ADR must relate without widening. | `5e1b04f1` | §§4–6; T3 |
| `repo:docs/adr/adr-0021-standard-packaged-skill-installation-methodology.md#decision-outcome` | current-state evidence | Skill-subtree decision that expressly reserves `.agents/` root authority for a new ADR. | `5e1b04f1` | §§4–6; T3 |
| `repo:docs/adr/adr-0022-standard-packaged-hook-installation-methodology.md#decision-outcome` | current-state evidence | Hook-subtree decision that expressly reserves `.agents/` root authority for a new ADR. | `5e1b04f1` | §§4–6; T3 |
| `repo:.standards/config.toml` | operational evidence | ADR `1.5`, required ADR body sections, and Markdown Frontmatter validation are selected for the dogfood corpus. | `5e1b04f1` | §§3, 7, 12; T1–T4 |
| `repo:docs/handoff/conventions.md#13-keep-documentation-only-closeout-proportional` | operational evidence | Documentation-only work uses changed-surface validation rather than the implementation/release battery. | `5e1b04f1` | §§3, 7, 12–13; T1–T4 |

Conflict precedence: the explicit request fixes the sequence and preservation boundary. Within each issue, the latest owner comment narrows or resolves the issue body's alternatives. ADR 1.5 governs record mechanics, while current repository files establish the starting state only.

## 3. Scope, Boundaries, and Constraints

### 3.1 In Scope

- Self-amend ADRs 0010 and 0026 so the latter owns the unchanged four-segment MCP resource URI grammar, the former adopts it by reference while retaining its protocol-boundary exclusion, and both record the already-landed producer alignment.
- Self-amend ADR 0024 with the owner-approved joint-determination rationale, a reader map, and the accepted cost of keeping two review populations in one record.
- Add ADR 0029 as the next repository ADR, making `.agents/` a platform-owned root allocated by artifact class; relate it reciprocally to ADRs 0016, 0021, and 0022; index it in `docs/adr/README.md`.
- Apply the repository-local evidence-versus-current-authority convention to every ADR whose status is active after the release-wide corpus freeze.
- Begin T4 only after the release coordinator freezes the complete v5.19 ADR-writing set, confirms at minimum the integrated #157 ADR 0028 amendment and #142 control-plane ADR checkpoints, and includes every other owner-approved v5.19 ADR creation or amendment in the active-ADR census.
- Atomically rename the two consumer-owned ADR files and every tracked inbound path reference:
  - `docs/adr/adr-0025-project-standards-mcp-service-and-sdk-boundary.md` → `docs/adr/adr-0025-mcp-service-and-sdk-boundary.md`
  - `docs/adr/adr-0026-project-standards-mcp-local-read-only-transport.md` → `docs/adr/adr-0026-mcp-local-read-only-transport.md`
- Produce four serial, reviewable documentation checkpoints, each starting and ending green.

### 3.2 Out of Scope and Deferred

- No change to URI grammar, MCP behavior, the 32-code error taxonomy, implementation, tests beyond citation-path substitutions, or immutable `standards/**` payload bytes.
- No split, supersession, or substantive rewrite of ADR 0024; no change to `meta/versioning.md`.
- No relocation, reconciliation, or collision repair for existing `.agents/` content and no package payload destination change.
- No ADR renumbering or ID change. Filenames change; canonical frontmatter `id` values remain stable.
- No ADR package cut, catalog/digest/manifest change, v5.19 release cut, issue mutation/closure, pull request, Agent Handoff edit, or generated `.project-pipeline` state during authoring.
- No promotion of the repository-local evidence convention into the reusable ADR package. That would require separately authorized package work.
- No implementation or issue-state ownership for #157, #142, #169, #167, or any other external v5.19 stream. This plan consumes their integrated ADR checkpoints only when the owner has settled an ADR-writing outcome.

### 3.3 Ownership and Preserved Behavior

| Boundary | Owner / Responsibility |
| --- | --- |
| T1 owns | The two cumulative grammar-reconciliation amendments and proof that the accepted URI grammar did not change. |
| T2 owns | The cumulative ADR 0024 no-split rationale and reader map, with `meta/versioning.md` excluded. |
| T3 owns | ADR 0029's new root-allocation decision plus reciprocal relations and index entry. |
| T4 owns / aggregates | Final bytes of the active ADR corpus, `docs/adr/README.md`, both renamed ADR paths, and every tracked inbound path-reference update. Earlier tasks may contribute to these shared ADR/index paths only in the declared sequence. |
| Release coordinator owns | The final v5.19 ADR-writing-set declaration and integrated checkpoint inventory. It must include #157's ADR 0028 amendment, #142's required control-plane ADR, and every other issue later settled to create or amend an ADR. |
| Depends on | The four cluster decisions, the release coordinator's frozen ADR-writing set, every checkpoint in that set, ADR 1.5 amendment/boundary rules, current repository ADR numbering, and current Git-tracked reference corpus. |
| Does not own | Standard payloads, MCP/product behavior, release classification, GitHub lifecycle, handoff truth, or any untracked/worktree copy outside Git's corpus. |
| Must preserve | Accepted Decision Outcome wording, cumulative amendment history, ADR lifecycle status, stable canonical IDs, immutable package bytes, test semantics, and unrelated concurrent work. |

### 3.4 Constraints and Authorization

- Execute strictly `T1 → T2 → T3 → release-wide corpus freeze → T4`. The first three are disjoint in substantive intent but the owner requires this order; T4 is the universal conflictor and must be last after every v5.19 ADR-authoring checkpoint, including work outside this four-task graph.
- Block T4 until the release coordinator supplies a settled final ADR-writing set and confirms every listed checkpoint is integrated. The minimum set includes #157's ADR 0028 amendment and #142's required control-plane ADR; #169, #167, or any other stream enters only if an owner later settles it as ADR-writing work.
- Use self-amendment notes and `### Amendments` detail for T1/T2. Do not silently replace stale accepted prose; state the later correction and what remains in force.
- ADR 0029 is a new decision, not an amendment to ADR 0016, 0021, or 0022. Use reciprocal `related` path edges, not `amends`/`amended_by` or supersession.
- T4 enumerates the post-freeze tracked corpus with `git grep`/`git ls-files`. Never use recursive grep, which reaches excluded worktree copies.
- Perform both renames, all inbound path substitutions, and the convention sweep in one T4 checkpoint. No intermediate commit may contain a missing target or dangling old path.
- Run Git/index-dependent checks directly local. `.git` is not synchronized to rexec and cannot provide valid history, rename, path-census, or tracked-corpus evidence remotely.
- In every execution worktree, run `scripts/bootstrap-worktree.sh` before candidate-wheel-backed validation. No engine or payload change is planned, so the full `scripts/verify.sh` battery is outside this docs-only plan.

## 4. Current State and Target State

### 4.1 Current State

- The base tree has 24 active ADRs. ADRs 0003, 0008, 0017, and 0020 are superseded; T4's evidence-convention sweep must select by actual `status`, not by number range.
- ADR 0026 already freezes the four-segment resource form `standards://{standard_id}/{version}/resources/{resource_id}`. ADR 0010 already excludes wire grammar, and the pair's `related` entries are reciprocal.
- ADRs 0010 and 0026 both say producer alignment remains open. Commit `e400f83f` disproves that current-state claim: both catalog producers use the frozen four-segment form at base `5e1b04f1`.
- ADR 0024 remains active as one record and contains five Decision Outcome subsections spanning catalog advertisement, selectors/authorization, promotion, classification, and forbidden transitions. It does not yet record why the concerns are jointly decided or give the two reader populations a map.
- ADRs 0021 and 0022 reserve `.agents/skills/` and `.agents/hooks/` respectively and expressly leave root ownership for a new ADR. ADR 0016 owns one installed skill destination. No active ADR allocates the root.
- `docs/adr/README.md` defines evidence versus current authority, but the active corpus has not been swept against it.
- ADRs 0025 and 0026 are consumer-owned documents: the central lock and package manifests manage only `docs/adr/adr.template.md` under this directory.
- The issue #162 owner census recorded 21 `adr-0025` hits across 13 tracked files and 25 `adr-0026` hits across 16 tracked files, a union of 46 hits across 17 files. At base `5e1b04f1`, exact old filename strings occupy 40 lines across 16 files; the broader owner census also counts stable IDs and non-path textual citations. T4 must remeasure after the release-wide corpus freeze because both this graph and external checkpoints change the corpus.
- Outside this graph, #157 has a settled obligation to amend ADR 0028 and #142 has a settled obligation to deliver its required control-plane ADR checkpoint. Issues #169 and #167 remain open without an owner-approved ADR-writing outcome, so neither is presumed to create a record; the complete v5.19 ADR-writing set is not frozen at plan authoring.

### 4.2 Target State

- ADRs 0010 and 0026 read as accepted text plus cumulative correction: ADR 0026 owns the unchanged MCP v1 grammar, ADR 0010 follows it for catalog/index URI form without widening either governed population, and `e400f83f` closes the stale producer divergence.
- ADR 0024 remains one active record. Its amendment explains joint determination from the considered-options set, maps each reader to the relevant outcome subsections, and explicitly accepts review coupling without changing policy.
- ADR 0029 is active and indexed. Its Decision Outcome alone identifies allocation authority, governed population, applicability, exclusions, coexistence, keying, grandfathering, and accepted collision risk. ADRs 0016, 0021, and 0022 point back to it.
- Every ADR active after the release-wide corpus freeze consistently reserves frozen evidence for `source`/More Information and points `related`/body authority references at current owners. The census includes ADR 0029, the integrated #157/#142 ADR checkpoints, and every other owner-approved v5.19 ADR creation or amendment.
- The repository contains the short ADR 0025/0026 filenames, zero tracked references to either old filename, unchanged canonical IDs, and no partial rename checkpoint.

### 4.3 Delta Summary

| Area | Current | Target | Must Preserve |
| --- | --- | --- | --- |
| URI decision graph | Two records carry stale open-divergence claims. | ADR 0026 owns; ADR 0010 adopts by reference; amendments record the resolved producers. | Four-segment grammar, protocol exclusion, edge reciprocity, error taxonomy. |
| Catalog-channel record shape | Split question remains unrecorded. | One cumulative amendment records joint determination and reader map. | Original Decision Outcome, status, versioning policy, `meta/versioning.md`. |
| `.agents/` authority | Two subtrees and one special case exist without a root allocator. | New ADR 0029 owns platform allocation and relates to all three records. | Existing layout/destinations and consumer-authored coexistence. |
| Link semantics | Convention exists only in the index prose. | Every active ADR distinguishes frozen evidence from current authority. | Historical evidence links and immutable payload addresses. |
| ADR paths | Two filenames include the repository name. | Short title-derived filenames and every tracked inbound reference agree. | ADR numbers, IDs, titles, bodies except authorized amendments/link corrections. |

## 5. Change Surface and Architecture

### 5.1 Components and Ownership

| Component / Surface | Current Responsibility | Planned Responsibility | Paths / Contracts | Owning Task |
| --- | --- | --- | --- | --- |
| URI declaration/index decision | Declares resources and excludes protocol grammar, but cites stale divergence. | Adopts ADR 0026 grammar by reference and records producer convergence. | ADR 0010, issue #161 | T1; final bytes T4 |
| MCP transport decision | Owns grammar and stale divergence disclosure. | Retains grammar and positional-rejection rationale; amendment marks disclosure historical/resolved. | ADR 0026, `e400f83f` | T1; final bytes T4 |
| Catalog-channel decision | Carries coupled rules without a durable no-split rationale. | Self-amendment explains joint determination and reader routing. | ADR 0024, issue #160 | T2; final bytes T4 |
| `.agents/` allocation | Reserved by subtree ADRs but unowned at root. | ADR 0029 allocates artifact-class subtrees and defines coexistence/keying. | ADRs 0016/0021/0022/0029 | T3; final bytes T4 |
| ADR index | Defines reading conventions and indexes 0001–0028. | Indexes ADR 0029 and carries final short paths. | `docs/adr/README.md` | T3 contribution; T4 owner |
| Release-wide ADR corpus | Other v5.19 streams include mandatory #157 and #142 ADR checkpoints; the final set is not yet frozen. | Release coordinator freezes the settled ADR-writing set and confirms every checkpoint integrated before T4. | #157, #142; conditionally #169/#167 or other later-settled ADR work | external T4 entry gate |
| Active ADR link semantics | Mixed frozen evidence and current authority pointers. | All post-freeze active records conform to the index convention without rewriting decision substance. | post-freeze active ADR inventory | T4 |
| Repository reference graph | Old 0025/0026 paths appear in docs and two test-module docstrings. | Every tracked inbound path names the short filename; Python behavior is unchanged. | post-freeze `git grep` inventory | T4 |

### 5.2 Serial Composition

```text
T1 grammar ownership amendments
  → T2 ADR 0024 no-split amendment
    → T3 ADR 0029 + reciprocal root-allocation edges + index
      → external release-wide corpus freeze
        (#157 ADR 0028 + #142 control-plane ADR + every other settled v5.19 ADR checkpoint)
      → T4 complete post-freeze active-corpus convention sweep
         + atomic ADR 0025/0026 renames
         + every tracked inbound path update
```

T4 owns the shared final corpus so the first three checkpoints remain independently reviewable while the universal link/path sweep sees their final records exactly once. The external gate is not a task edge this child plan can execute: absence of a settled final set or any required integrated checkpoint blocks T4.

### 5.3 Change-Surface Matrix

| Surface | Applies? | Invariant / Required Change | Proof | Task |
| --- | --- | --- | --- | --- |
| Observable behavior | no | Documentation only; MCP, catalog, resolver, and test behavior remain byte-semantically unchanged. | PV-T4-001 | T4 |
| Architecture / dependency direction | yes | Decision authority edges become explicit: 0010 → 0026; 0016/0021/0022 ↔ 0029. | PV-T1-001, PV-T3-001 | T1, T3 |
| Public / cross-task interface | yes | ADR paths change atomically; canonical IDs do not. | PV-T4-001 | T4 |
| Data / persistent state | no | No migration or generated state. | PV-T4-001 | T4 |
| Configuration | no | `.standards/config.toml`, package config, and `meta/versioning.md` remain unchanged. | PV-T2-001, PV-T4-001 | T2, T4 |
| Security / trust | no | No runtime boundary changes; root allocation records ownership only. | PV-T3-001 | T3 |
| Compatibility / migration | yes | Old filename paths disappear in one checkpoint while IDs and historical evidence remain resolvable. | PV-T4-001 | T4 |
| Operations / deployment | no | No release, GitHub, reconciliation, or live operation. | PV-T4-001 | T4 |
| Documentation / ownership truth | yes | Four issue outcomes become explicit, navigable corpus truth. | PV-T1-001 through PV-T4-001 | T1–T4 |
| Durable evidence | no | Commits and repeatable validators are sufficient; no external/non-repeatable evidence exists. | PV-T4-001 | T4 |

### 5.4 Binding Decisions

| ID | Decision | Rationale | Source | Affected Task(s) |
| --- | --- | --- | --- | --- |
| D-001 | ADR 0026 owns the four-segment MCP resource URI grammar; ADR 0010 adopts it by reference without widening 0026 beyond MCP. | The grammar is a client compatibility freeze; declaration/index is ADR 0010's separate concern. | #161 owner decision | T1 |
| D-002 | Record `e400f83f` as closure of the producer divergence and retain the malformed positional-rejection rationale. | Current code and shipped catalog already agree; the ADR prose is stale, not the implementation. | #161 owner decision; `e400f83f` | T1 |
| D-003 | Keep ADR 0024 whole and self-amend it. | Advertisement is the shared substrate, and the considered alternatives jointly determine selectors and release classification. | #160 owner decision | T2 |
| D-004 | Do not modify `meta/versioning.md`. | The issue's accepted scope is the ADR rationale/reader map only; derived-policy drift is separate work. | #160 owner decision; request | T2 |
| D-005 | Create ADR 0029 for `.agents/` root allocation. | Existing ADRs reserve root authority and ADR 1.5 forbids widening them by amendment. | #159 owner decision | T3 |
| D-006 | Platform owns the root; new artifact classes require their own ADR and use `standard-id` keys; skills remain grandfathered. | This preserves reserved authority, regularizes coexistence, and avoids breaking installed consumers. | #159 owner decision | T3 |
| D-007 | Relate ADR 0029 reciprocally to ADRs 0016, 0021, and 0022 without amendment/supersession. | The new decision allocates the root while the earlier records retain their own governed populations. | #159 owner decision; request | T3 |
| D-008 | Treat `source`/More Information as frozen evidence and `related`/body prose as current authority across active ADRs only. | This is the repository-local convention; promotion into `adr@1.5` is out of scope. | `docs/adr/README.md`; #162 | T4 |
| D-009 | Rename 0025/0026 by filename only and update the full tracked inbound graph in the same commit. | IDs are stable identity; a split rename creates dangling references. | ADR 1.5 filename rule; #162 | T4 |
| D-010 | Use Git, not recursive filesystem traversal, as corpus authority. | Excluded agent worktrees contain copies and inflate unsafe recursive results. | #162 owner decision; repository convention | T4 |
| D-011 | Run T4 only after a release-wide v5.19 ADR corpus freeze that includes at minimum the integrated #157 ADR 0028 and #142 control-plane ADR checkpoints. | A corpus-wide semantic sweep and rename census is stale if any release ADR lands afterward. | request; #157; #142 | T4 |
| D-012 | Add other v5.19 work to the freeze only after its owner settles that it creates or amends an ADR; do not infer an ADR outcome for #169, #167, or another unresolved issue. | The final corpus must be exhaustive without converting unresolved alternatives into plan decisions. | request; live #169/#167 state | T4 |

## 6. Requirements and Acceptance

| ID | Requirement | Source | Priority | Owner Task | Task(s) | Proof(s) |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-001 | ADR 0026 shall remain the sole active owner of the unchanged MCP resource URI grammar; ADR 0010 shall adopt it by reference, retain its exclusion, and both shall record `e400f83f` as resolved producer alignment without rewriting accepted outcomes. | #161; request | Must | T1 | T1 | PV-T1-001 |
| REQ-002 | ADR 0024 shall remain active and unsplit, with a cumulative self-amendment explaining joint determination, mapping reader questions to outcome sections, and accepting review coupling; `meta/versioning.md` shall not change. | #160; request | Must | T2 | T2 | PV-T2-001 |
| REQ-003 | ADR 0029 shall allocate the platform-owned `.agents/` root per artifact class, define coexistence/keying/grandfathering and accepted risk, pass the four-part reader test, and have reciprocal `related` edges with ADRs 0016, 0021, and 0022 plus an index entry. | #159; request | Must | T3 | T3 | PV-T3-001 |
| REQ-004 | Every ADR active after the release-wide corpus freeze shall conform to the repository evidence-versus-current-authority convention while retaining historical evidence and accepted decision substance. | #162; request | Must | T4 | T4 | PV-T4-001 |
| REQ-005 | ADR 0025 and ADR 0026 shall use their short title-derived filenames in one atomic checkpoint, every tracked inbound path shall be updated, canonical IDs shall remain unchanged, and the old filename strings shall have zero tracked matches. | #162; request | Must | T4 | T4 | PV-T4-001 |
| REQ-006 | The implementation shall remain documentation-only: no immutable payload, product behavior, `meta/versioning.md`, GitHub state, handoff state, release state, or generated pipeline state shall change. | request | Must | T4 | T1, T2, T3, T4 | PV-T1-001, PV-T2-001, PV-T3-001, PV-T4-001 |
| REQ-007 | Execution shall be serial `T1 → T2 → T3 → release-wide corpus freeze → T4`, with one green commit per plan task and no partial rename commit. | request; #162 owner decision | Must | T4 | T4 | PV-T4-001 |
| REQ-008 | Before T4, the release coordinator shall settle the final v5.19 ADR-writing set and confirm all its checkpoints integrated, including at minimum #157's ADR 0028 amendment and #142's required control-plane ADR; any other issue enters only after an owner-approved ADR-writing decision, and an unsettled set or missing checkpoint shall block. | request; #157; #142; live #169/#167 state | Must | T4 | T4 | PV-T4-001 |

## 7. Verification and Evidence Strategy

- **Bridge and execution preflight:** run `uv run --no-project scripts/plan.py --version` and require `3.5.0`; run `uv run --no-project scripts/plan.py validate docs/plans/2026-08-10-v519-adr-corpus-corrections-plan.md --no-scratch`; in each new execution worktree run `scripts/bootstrap-worktree.sh` before candidate-wheel-backed checks.
- **ADR/frontmatter oracle:** with `PYTHONPATH="$PWD/build/wheel-runtime"`, run `uv run project-standards validate`. The selected ADR 1.5 configuration has `require_sections = true`, and the selected Markdown Frontmatter provider validates canonical fields, IDs, dates, and references.
- **Frontmatter formatting:** with the same candidate runtime, run `uv run format-frontmatter --check` and require no ordering/quoting/list findings in the managed corpus.
- **Git-tracked changed-surface formatting:** after reviewing and staging only task-owned paths, run `git diff --cached --name-only -z --diff-filter=ACMR -- '*.md' '*.json' '*.jsonc' '*.yml' '*.yaml' | xargs -0 -r npx prettier --check --` and `git diff --cached --name-only -z --diff-filter=ACMR -- '*.md' | sed -z 's|^|:|' | xargs -0 -r npx markdownlint-cli2 --no-globs`. This is the documentation-only scoped form of the repository's Git-authoritative Markdown gate and excludes unrelated tracked symlink projections.
- **Path and rename proof:** run direct-local `git grep` separately for `adr-0025` and `adr-0026` to retain the owner census; enumerate exact old filename matches and file union; after T4 require both exact-old-path searches to exit 1 with empty output, both new files tracked, and `git diff-tree --summary --find-renames T3_CHECKPOINT T4_CHECKPOINT` to report both renames.
- **Corpus-freeze oracle:** before T4, record the release coordinator's final v5.19 ADR-writing-set declaration and integrated checkpoint OIDs; require #157's ADR 0028 amendment and #142's control-plane ADR, then reconcile every other owner-approved ADR-writing issue into the set. If #169, #167, or another candidate remains unresolved such that the final set cannot be declared, stop before inventory.
- **Corpus/link oracle:** after the freeze, derive active ADRs from frontmatter `status`, inspect each active record's `source`, `related`, body links, and More Information against `docs/adr/README.md` line 46 semantics, and retain a concise per-file checklist in ephemeral task notes. `project-standards validate` then supplies the independent broken-reference/schema oracle.
- **Preservation proof:** use `git diff --word-diff=porcelain` scoped to each amended ADR to confirm original Decision Outcome prose remains and only frontmatter bookkeeping, amendment notes/details, and path/link corrections are added. Use `git diff --name-status` and `git diff --check` at every checkpoint.
- **Python citation-only proof:** T4 may change literal ADR paths in `tests/mcp_server/test_repo_access.py` and `tests/mcp_server/test_transport.py`; run `uv run ruff format --check` and `uv run ruff check` on every touched Python path and confirm no executable token outside the docstring/comment citation changes.
- **Negative controls:** a rewritten accepted sentence, a second ADR claiming grammar ownership, a missing reciprocal root-allocation edge, a missing #157/#142 checkpoint, an unsettled final ADR-writing set, a post-freeze ADR omitted from the census, an evidence link moved to current authority, a current-authority link left on a frozen version, one surviving old filename, an ID change, or a partial one-file rename must each fail the corresponding diff/search/manual oracle.
- **External environments:** live GitHub issue text is read-only authority for the final-set decision; implementation proof remains repository-local, with Git/index-dependent gates run directly local.
- **Evidence:** repeatable command output and the four Git checkpoints are sufficient; no durable `EV-###` artifact is required.
- **Late failure:** block the owning task. If a completed checkpoint is disproved, append a correction task with `corrects:` and `discovered_from:`; never rewrite completed task definitions or commit a partial rename as recovery.

## 8. Execution Summary

| Task | Title | Disposition | Work Type | Phase | Depends On | Requirement(s) | Primary Proof | Parallel / Conflict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T1 | Reconcile URI grammar ownership | active | documentation | P1 | None | REQ-001, REQ-006 | PV-T1-001 | no / T4 owns final shared ADR bytes |
| T2 | Record ADR 0024's load-bearing coupling | active | documentation | P2 | T1 | REQ-002, REQ-006 | PV-T2-001 | no / owner-mandated serial order; T4 owns final ADR bytes |
| T3 | Establish `.agents/` root allocation | active | documentation | P3 | T2 | REQ-003, REQ-006 | PV-T3-001 | no / owner-mandated serial order; T4 owns final ADR/index bytes |
| T4 | Sweep link semantics and atomically rename ADRs 0025/0026 | active | documentation | P4 | T1, T2, T3 | REQ-004, REQ-005, REQ-006, REQ-007, REQ-008 | PV-T4-001 | no / external corpus-freeze entry gate; conflicts with and aggregates all release ADR changes |

## 9. Implementation Tasks

### Phase P1: Grammar Authority Reconciliation

#### T1: Reconcile URI grammar ownership

- **disposition:** active
- **outcome:** ADRs 0010 and 0026 retain their accepted text and read cumulatively as one compatible authority graph: ADR 0026 owns the unchanged four-segment MCP resource grammar, ADR 0010 adopts it by reference while preserving its exclusion, and both record that `e400f83f` already aligned the producers.
- **work_type:** documentation
- **checkpoint:** one green documentation commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** []
- **dependency_reason:** none
- **requirements:** [REQ-001, REQ-006]
- **proof:** [PV-T1-001]
- **source_refs:** [issue:L3DigitalNet/project-standards#161, repo:docs/adr/adr-0010-standard-resource-uris-and-index.md#decision-outcome, repo:docs/adr/adr-0026-project-standards-mcp-local-read-only-transport.md#resource-uri-grammar, repo:src/project_standards/standards_graph/catalog.py::_render_package_catalog, repo:src/project_standards/standards_graph/catalog.py::render_catalog]
- **consumes:** [accepted ADR 0010/0026 text, ADR 1.5 self-amendment form, four-segment grammar, producer-alignment commit]
- **produces:** [uri-grammar-authority-reconciliation-v1]
- **preserves:** [all original Decision Outcome prose, ADR 0010's protocol-boundary exclusion, ADR 0026's permitted forms/canonicalization/error semantics, reciprocal `related` edges, stable IDs/status]
- **invariants:** [one grammar owner inside the active pair, adoption-by-reference does not widen ADR 0026, amendments remain cumulative, no code/payload change]
- **executor_discretion:** [exact amendment-note wording and whether each detailed correction needs its own paragraph under `### Amendments`, provided every settled fact and preservation rule is explicit]
- **files:** [`docs/adr/adr-0010-standard-resource-uris-and-index.md` (modify; owner T4), `docs/adr/adr-0026-project-standards-mcp-local-read-only-transport.md` (modify; owner T4)]
- **parallel_safe:** no
- **conflicts_with:** [T4]
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** if an amendment rewrites or broadens accepted authority, restore the task-owned files to the T1 base in the isolated worktree and reapply as cumulative notes/details; do not checkpoint until targeted validation is green
- **acceptance:** PV-T1-001 proves sole ownership/adoption-by-reference, producer-resolution accuracy, original-outcome preservation, unchanged IDs/edges/grammar, and the docs-only boundary
- **sub-tasks:**
  - **T1.1 INVENTORY** — capture the two frontmatter blocks, amendment histories, Decision Outcome text, reciprocal path edges, grammar table/rules, and `e400f83f` producer diff.
  - **T1.2 UPDATE** — add dated self-amendment notes/details that supersede the stale divergence claims without deleting them; state ownership, adoption-by-reference, producer alignment, retained positional-rejection rationale, and v2-successor consequence.
  - **T1.3 VERIFY REFERENCES** — confirm both current paths resolve, edges remain reciprocal, and no other ADR claims this MCP grammar as its governed concern.
  - **T1.4 Verify Task** — run PV-T1-001, targeted Prettier/markdownlint, candidate-wheel `project-standards validate`, `git diff --check`, and scoped word diff; commit with required trailers.

### Phase P2: Catalog-Channel Record Integrity

#### T2: Record ADR 0024's load-bearing coupling

- **disposition:** active
- **outcome:** ADR 0024 remains one active record whose cumulative self-amendment explains why advertisement, selectors/authorization, and release classification were jointly decided, tells each reader where to look, and accepts the review-coupling cost without changing the decision or `meta/versioning.md`.
- **work_type:** documentation
- **checkpoint:** one green documentation commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** [T1]
- **dependency_reason:** ordering-only: the owner-mandated cluster sequence places #160 after the independently green #161 checkpoint; T2 consumes no T1 artifact
- **requirements:** [REQ-002, REQ-006]
- **proof:** [PV-T2-001]
- **source_refs:** [issue:L3DigitalNet/project-standards#160, repo:docs/adr/adr-0024-catalog-scoped-package-version-channels.md#considered-options, repo:docs/adr/adr-0024-catalog-scoped-package-version-channels.md#decision-outcome]
- **consumes:** [accepted ADR 0024 text, owner-approved load-bearing rationale, ADR 1.5 self-amendment form]
- **produces:** [catalog-channel-joint-determination-rationale-v1]
- **preserves:** [all original Decision Outcome prose, active status, supersession/amendment relationships, release and selector semantics, `meta/versioning.md` bytes]
- **invariants:** [no split or supersession, advertisement is the shared substrate, the reader map explains rather than creates policy, self-amendment has no reciprocal ADR fields]
- **executor_discretion:** [compact table versus list for the reader map, and exact placement within `### Amendments` after Consequences/Confirmation]
- **files:** [`docs/adr/adr-0024-catalog-scoped-package-version-channels.md` (modify; owner T4)]
- **parallel_safe:** no
- **conflicts_with:** [T4]
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** if the amendment introduces policy or edits `meta/versioning.md`, discard only T2's uncommitted task-owned change and reapply explanatory text against the T1 checkpoint
- **acceptance:** PV-T2-001 proves the settled no-split rationale, reader map, accepted cost, original-outcome preservation, unchanged relationship/status fields except dates, and a byte-identical `meta/versioning.md`
- **sub-tasks:**
  - **T2.1 INVENTORY** — map Catalog channels, candidate/retained tracks, candidate exit, promotion, classification, and forbidden transitions to advertisement/selector/operator readers; snapshot `meta/versioning.md` digest.
  - **T2.2 UPDATE** — add the dated self-amendment note and detailed rationale/reader map without editing accepted outcome sentences.
  - **T2.3 VERIFY REFERENCES** — verify the amendment cites the existing option set and sections, creates no new counterpart relationship, and leaves `meta/versioning.md` untouched.
  - **T2.4 Verify Task** — run PV-T2-001, targeted Markdown gates, candidate-wheel validation, `git diff --check`, scoped word diff, and the `meta/versioning.md` digest comparison; commit with required trailers.

### Phase P3: `.agents/` Root Allocation

#### T3: Establish `.agents/` root allocation

- **disposition:** active
- **outcome:** New active ADR 0029 makes `.agents/` root allocation explicit and indexed, while ADRs 0016, 0021, and 0022 retain their narrower decisions and reciprocally relate to the new owner.
- **work_type:** documentation
- **checkpoint:** one green documentation commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** [T2]
- **dependency_reason:** ordering-only: the owner-mandated cluster sequence places #159 after the independently green #160 checkpoint; T3 consumes no T2 artifact
- **requirements:** [REQ-003, REQ-006]
- **proof:** [PV-T3-001]
- **source_refs:** [issue:L3DigitalNet/project-standards#159, repo:docs/adr/adr-0016-package-markdown-frontmatter-skill-with-standard.md#decision-outcome, repo:docs/adr/adr-0021-standard-packaged-skill-installation-methodology.md#decision-outcome, repo:docs/adr/adr-0022-standard-packaged-hook-installation-methodology.md#decision-outcome, repo:standards/adr/versions/1.5/README.md#amendment-workflow]
- **consumes:** [reserved-root authority in ADRs 0021/0022, ADR 0016 special-case destination, owner-approved allocation/coexistence/keying decision, next ADR sequence number]
- **produces:** [agents-root-allocation-v1, post-T3 active ADR corpus]
- **preserves:** [existing `.agents/skills/` and `.agents/hooks/` layouts, consumer-authored content, package ownership only of declared destinations, ADRs 0016/0021/0022 governed populations and amendment histories]
- **invariants:** [new artifact class requires its own ADR, new class subtree keys by standard-id, skill-id namespace is grandfathered, no package owns a whole shared subtree, reciprocal relations use paths and no amendment/supersession]
- **executor_discretion:** [concise MADR prose organization and examples that do not enlarge the owner-approved decision]
- **files:** [`docs/adr/adr-0029-agents-root-allocation.md` (create; owner T4), `docs/adr/adr-0016-package-markdown-frontmatter-skill-with-standard.md` (modify related only; owner T4), `docs/adr/adr-0021-standard-packaged-skill-installation-methodology.md` (modify related only; owner T4), `docs/adr/adr-0022-standard-packaged-hook-installation-methodology.md` (modify related only; owner T4), `docs/adr/README.md` (modify index/related/current corpus description; owner T4)]
- **parallel_safe:** no
- **conflicts_with:** [T4]
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** if numbering or an authority edge conflicts with intervening repository state, stop before creating a checkpoint and return the exact collision to the owner; otherwise remove only the uncommitted new file and reciprocal additions and retry from T2
- **acceptance:** PV-T3-001 proves ADR 0029's identity/frontmatter/required sections/four-part boundary, the exact settled decision, three reciprocal related pairs, index coverage, and absence of layout/payload changes
- **sub-tasks:**
  - **T3.1 INVENTORY** — recheck the highest ADR number, active statuses, three source records, and current index before allocating `0029` and its canonical ID.
  - **T3.2 UPDATE** — author ADR 0029 with platform allocation, artifact-class ADR condition, coexistence, package destination ownership, new `standard-id` keying, skill grandfathering, accepted collision risk, alternatives, exclusions, and confirmation.
  - **T3.3 VERIFY REFERENCES** — add and verify reciprocal `related` path edges on 0016/0021/0022 and the README index/description; confirm no `amends`, `amended_by`, supersession, payload, or filesystem-layout change.
  - **T3.4 Verify Task** — run PV-T3-001, targeted Markdown gates, frontmatter/ID/reference validation, `git diff --check`, and a scoped diff; commit with required trailers.

### Phase P4: Corpus-Wide Link and Path Reconciliation

#### T4: Sweep link semantics and atomically rename ADRs 0025/0026

- **disposition:** active
- **outcome:** The complete post-freeze active ADR corpus distinguishes frozen evidence from current authority, ADRs 0025/0026 have convention-conformant filenames, and every tracked inbound path resolves with no old filename remaining.
- **work_type:** documentation
- **checkpoint:** one atomic green documentation/citation commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** [T1, T2, T3]
- **dependency_reason:** consumes T1's amended grammar pair, T2's amended ADR 0024, and T3's new active ADR plus reciprocal/index updates; an external entry gate then requires the release coordinator's settled final v5.19 ADR-writing set and every integrated checkpoint so one last corpus sweep covers every resulting record and reference
- **requirements:** [REQ-004, REQ-005, REQ-006, REQ-007, REQ-008]
- **proof:** [PV-T4-001]
- **source_refs:** [issue:L3DigitalNet/project-standards#162, issue:L3DigitalNet/project-standards#157, issue:L3DigitalNet/project-standards#142, issue:L3DigitalNet/project-standards#169, issue:L3DigitalNet/project-standards#167, repo:docs/adr/README.md#reading-this-corpus, repo:standards/adr/versions/1.5/README.md#frontmatter-for-adrs, repo:docs/handoff/conventions.md#21-renaming-a-managed-artifact-is-a-cross-cutting-change]
- **consumes:** [release-wide-v5.19-adr-corpus-freeze-v1, post-freeze active ADR corpus, uri-grammar-authority-reconciliation-v1, catalog-channel-joint-determination-rationale-v1, agents-root-allocation-v1, Git-tracked inbound-reference census]
- **produces:** [evidence-authority-classified-active-adr-corpus-v1, short-adr-0025-0026-path-contract-v1]
- **preserves:** [accepted Decision Outcome wording except non-semantic link-target corrections, frozen evidence targets, stable ADR IDs/numbers/titles/statuses/amendments, Python executable behavior, all unrelated tracked/untracked work]
- **invariants:** [T4 last after all v5.19 ADR-authoring work, final ADR-writing set settled before inventory, #157 and #142 ADR checkpoints integrated, no unresolved outcome invented, Git is corpus authority, every post-freeze active ADR inspected once, one atomic checkpoint owns both renames and all references, zero old exact filename matches, no payload or GitHub/handoff/meta mutation]
- **executor_discretion:** [ordering of the per-file sweep and exact current-authority link target where the family landing page and selected current version are both accurate, provided the index convention and repository terminology decide consistently]
- **files:** [`docs/adr/adr-*.md` active after the release-wide freeze (inspect and modify where required; owner T4), `docs/adr/README.md` (modify; owner T4), `docs/adr/adr-0010-standard-resource-uris-and-index.md` (modify link semantics/path references if required; owner T4), `docs/adr/adr-0016-package-markdown-frontmatter-skill-with-standard.md` (modify link semantics/path references if required; owner T4), `docs/adr/adr-0021-standard-packaged-skill-installation-methodology.md` (modify link semantics/path references if required; owner T4), `docs/adr/adr-0022-standard-packaged-hook-installation-methodology.md` (modify link semantics/path references if required; owner T4), `docs/adr/adr-0024-catalog-scoped-package-version-channels.md` (modify link semantics/path references if required; owner T4), `docs/adr/adr-0029-agents-root-allocation.md` (modify link semantics/path references if required; owner T4), `docs/adr/adr-0025-project-standards-mcp-service-and-sdk-boundary.md` (rename/delete old path; owner T4), `docs/adr/adr-0025-mcp-service-and-sdk-boundary.md` (rename/create target; owner T4), `docs/adr/adr-0026-project-standards-mcp-local-read-only-transport.md` (rename/delete old path; owner T4), `docs/adr/adr-0026-mcp-local-read-only-transport.md` (rename/create target; owner T4), every post-freeze tracked file returned by exact-old-path `git grep` (path substitution only outside active ADR classification work; owner T4), touched `tests/mcp_server/*.py` citations (docstring/comment path substitution only; owner T4)]
- **parallel_safe:** no
- **conflicts_with:** [T1, T2, T3]
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** if the final ADR-writing set is unsettled or a required external checkpoint is missing, do not begin T4; if new ADR-authoring work is admitted after inventory but before commit, reverse both uncommitted `git mv` operations and substitutions together, integrate it, obtain a new freeze, and restart the census; on a later reference/frontmatter/Markdown failure, forward-repair the complete scoped set or reverse both uncommitted moves and all T4 substitutions together; never use recursive cleanup or touch unrelated files
- **acceptance:** PV-T4-001 proves the release-wide final ADR-writing set was settled, at minimum the #157 ADR 0028 and #142 control-plane ADR checkpoints were integrated, every post-freeze active ADR was classified, evidence/current-authority semantics are correct, both renames are detected together, exact old paths have zero tracked matches, new paths and all references validate, IDs and accepted prose remain stable, and only authorized documentation/citation paths changed
- **sub-tasks:**
  - **T4.0 CORPUS FREEZE** — obtain the release coordinator's settled final v5.19 ADR-writing set and integrated checkpoint inventory; require #157's ADR 0028 and #142's control-plane ADR, add any other owner-approved ADR work, and block rather than infer an outcome while the set remains unresolved.
  - **T4.1 INVENTORY** — after the freeze, derive the active ADR set from status; verify every checkpoint record is included; re-run separate broad `adr-0025`/`adr-0026` owner censuses and exact-old-path line/file unions with `git grep`; confirm neither target is managed.
  - **T4.2 UPDATE** — classify every active ADR's `source`, `related`, body, and More Information links; keep frozen evidence in evidence positions and repoint authority positions to current owners without changing policy prose.
  - **T4.3 RENAME** — `git mv` both ADRs to the short paths, then substitute every exact tracked inbound old path, including frontmatter, index/body links, specifications, research/review material, user docs, and test docstrings/comments.
  - **T4.4 VERIFY REFERENCES** — require zero exact-old-path matches; validate new path/anchor/frontmatter references; inspect `git diff-tree --summary --find-renames` candidate output; confirm IDs stayed unchanged and every post-freeze active ADR was checked.
  - **T4.5 Verify Task** — run PV-T4-001, candidate-wheel frontmatter/ADR/reference validation, staged task-diff Git-tracked Prettier/markdownlint, targeted Ruff on touched Python citations, `git diff --check`, and the authorized-path diff; commit the whole sweep with required trailers.

## 10. Integration, Migration, and Recovery

### 10.1 Integration Sequence

1. T1 lands and validates the reconciled URI decision graph without any path rename.
2. T2 lands and validates ADR 0024's self-amendment; its dependency is ordering-only and its diff remains disjoint from T1.
3. T3 lands ADR 0029, the three reciprocal relations, and index coverage.
4. The release coordinator settles the final v5.19 ADR-writing set and confirms every checkpoint integrated, including at minimum #157's ADR 0028 amendment and #142's control-plane ADR. Any later owner-approved #169/#167 or other ADR work joins the set; an unresolved set blocks here.
5. T4 re-inventories the post-freeze tracked state, performs the convention pass and both renames as one transaction, runs the integrated validation battery, and creates the final checkpoint.

No task may begin from a red prior checkpoint. T4 does not rely on the author's static file list as exhaustive; it resolves every current tracked inbound path after the release-wide freeze. The external prerequisite is an entry gate, not an invitation for this child plan to implement or mutate the prerequisite issues.

### 10.2 Documentation and Path Transition

- Required: yes, for ADR path identity only; no data/config/runtime migration exists.
- Compatibility period: none. Tracked repository references switch atomically in T4; stable ADR IDs continue to identify the records.
- Idempotency: after T4, rerunning exact-old-path searches returns no matches and applying the same substitution set yields no diff.
- Point of no return: the T4 checkpoint commit. Before it, both moves and substitutions are one reversible uncommitted task-owned set; a changed freeze invalidates that set.
- Rollback / forward repair: prefer forward repair to make the full path graph green. If a new ADR-writing checkpoint is admitted before commit, reverse both moves and all T4 substitutions together, integrate it, refreeze, and restart the census. After checkpoint, use an append-only correction task and a new commit.
- Recovery proof: PV-T4-001.

### 10.3 Late Failure and Correction

If final validation exposes a missed inbound path, post-freeze ADR omission, misclassified evidence link, broken reciprocal relation, or accepted-prose rewrite after an owning task is complete, append the next permanent correction task with `corrects:` and `discovered_from:`. Give the shared corpus paths `owner T4`, complete the correction checkpoint, and rerun the failed proof. Do not reopen or rewrite T1–T4 history.

## 11. Risks, Assumptions, and Open Questions

### 11.1 Risks

| ID | Risk | Likelihood | Impact | Treatment | Owner / Task |
| --- | --- | --- | --- | --- | --- |
| R-001 | A static pre-plan reference list misses paths added by this graph or another v5.19 ADR-writing stream. | medium | high | Freeze the release-wide ADR-writing set, then re-run Git-tracked broad and exact censuses and require zero old paths. | release coordinator, T4 |
| R-002 | A correction silently rewrites accepted governance instead of preserving amendment history. | medium | high | Scoped word-diff preservation checks and cumulative amendment form gate T1/T2; T4 changes only link targets/path literals in accepted prose. | T1, T2, T4 |
| R-003 | Evidence links are modernized and lose the version actually used to decide, or stale evidence is mistaken for authority. | medium | high | Per-active-record classification checklist uses the index's four-position convention and keeps frozen evidence resolvable. | T4 |
| R-004 | The rename is committed partially or recursive grep causes edits in excluded worktrees. | low | high | One T4 checkpoint, `git mv` both targets, Git-only census, rename-summary inspection, and zero-old-path gate. | T4 |
| R-005 | ADR 0029 widens subtree records or implies package ownership of consumer content. | low | high | Four-part boundary review, reciprocal `related` only, explicit coexistence/destination ownership, and no layout mutation. | T3 |
| R-006 | T4 starts before #157/#142 land or while another possible ADR outcome such as #169/#167 remains unsettled. | medium | high | Make the final-set declaration and integrated checkpoint inventory an explicit entry gate; absence blocks T4 without inventing an outcome. | release coordinator, T4 |
| R-007 | New ADR-writing work is admitted after T4 inventory, making the sweep stale. | low | high | Invalidate the freeze, reverse the uncommitted atomic rename set, integrate the checkpoint, refreeze, and restart the census. | release coordinator, T4 |

### 11.2 Assumptions

| ID | Assumption | Impact if False |
| --- | --- | --- |
| A-001 | ADR 0029 remains the next unused number when T3 begins. | T3 blocks before authoring and asks the repository owner to allocate the non-colliding identity; it does not renumber another record. |
| A-002 | The four cluster owner comments remain the latest applicable authority through execution. | A materially changed issue decision pauses the affected task and returns the minimum amendment request; execution does not reinterpret intent. |
| A-003 | The release coordinator can declare a settled final v5.19 ADR-writing set before T4. | T4 remains blocked; it does not treat the current issue list or active-record count as final. |

### 11.3 Open Questions

None within T1–T3. The owner decisions resolve grammar ownership, ADR 0024 record shape, and `.agents/` allocation. The release-wide ADR-writing set is an external T4 entry condition, not an executor choice; until it is settled, T4 is blocked.

## 12. Final Verification

- Re-run bridge `3.5.0` validation against the durable plan with `--no-scratch`; all four checkpoints and required trailers must exist in dependency order.
- Reconcile REQ-001 through REQ-008 to passing PV-T1-001 through PV-T4-001; no task may defer its own acceptance to final verification.
- Confirm the release coordinator's final ADR-writing-set declaration and checkpoint inventory precede T4, include #157's ADR 0028 amendment and #142's control-plane ADR, and include every other issue then settled to create or amend an ADR.
- From a bootstrapped candidate-wheel runtime, run `project-standards validate` and `format-frontmatter --check`; ADR required sections, frontmatter, IDs, and local references must pass.
- Stage only task-owned paths, then run the §7 Git-tracked task-diff Prettier and markdownlint commands; run targeted Ruff format/lint for any Python citation paths T4 touched.
- Run separate direct-local Git searches for both exact old filenames and require empty output/exit 1. Confirm both short target paths are tracked and canonical ADR IDs did not change.
- Inspect the broad owner census, post-freeze exact inbound-file inventory, T4 rename summary, and final `git diff --check`. Every inventoried path must either change to the short path or be documented as a stable non-path ADR ID/textual citation.
- Inspect all post-freeze active ADRs against the evidence-versus-current-authority checklist, including ADR 0029, the T1/T2 amendments, and records from every external checkpoint in the frozen set.
- Confirm the task range contains no changes under `standards/**`, `src/**`, package/catalog/lock/config surfaces, `meta/versioning.md`, GitHub state, Agent Handoff, or generated `.project-pipeline` state, except the two authorized Python test docstring/comment citation substitutions if present.
- Any failure routes to an append-only correction task; final verification does not edit implementation artifacts directly.

## 13. Close-out

- **Completed:** pending all four green checkpoints and final verification.
- **Decisions / deviations harvested:** retain the four cluster issue IDs, the external freeze's issue/checkpoint inventory, and applicable owner decisions in the plan/checkpoint trail; record any approved deviation before completion.
- **Risks closed / accepted:** close R-001–R-007 from observed proof; do not silently accept a failed freeze, census, or prose-preservation check.
- **Deferred/discovered work filed:** this plan does not mutate GitHub. Report any independently governed follow-up to the parent workflow for separate issue handling.
- **Source/ADR/handoff reconciliation:** the ADR corpus is the durable source outcome. Do not edit Agent Handoff or issue state under this child plan.
- **Scratch teardown:** remove only this plan's ephemeral execution directory after all task evidence is represented by commits and the final validation receipt; never remove the shared `.project-pipeline/` root.

## Appendix A. Interface and State Contracts

| Contract | Owner / Producer Task | Consumer(s) | Current | Planned / States | Errors / Limits | Compatibility / Invariant | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| URI grammar authority | T1 | T4, ADR readers | ADR 0026 freezes grammar; both ADRs cite stale divergence. | ADR 0026 owner, ADR 0010 adopter; `e400f83f` closes producers. | No grammar/error change; v2 successor must carry grammar or repair reference. | Preserve accepted text, exclusion, reciprocal edges, four-segment form. | #161 owner comment |
| Catalog-channel record shape | T2 | T4, release/consumer readers | One record with no durable no-split rationale. | One amended record with joint-determination rationale and reader map. | No split/supersession or `meta/versioning.md` edit. | Amendment explains; it does not create or alter policy. | #160 owner comment |
| `.agents/` allocation | T3 | T4, future artifact-class ADRs/packages/consumers | Root reserved; skills/hooks subtrees and one special case exist. | Platform allocates artifact classes; new class needs ADR and standard-id key; skills grandfathered. | Package owns only declared destination; consumer coexistence stays valid. | Existing paths/layouts unchanged; 0016/0021/0022 remain in force. | #159 owner comment |
| Release-wide ADR corpus freeze | release coordinator (external) | T4 | #157 and #142 require ADR checkpoints; other v5.19 ADR-writing outcomes may still be unsettled. | Settled final issue/checkpoint set, all integrated, with #157 ADR 0028 and #142 control-plane ADR mandatory. | Missing checkpoint or unsettled final set blocks; no issue outcome may be inferred. | T4 inventories only after the freeze and includes every active record from it. | request; #157; #142; live #169/#167 state |
| Evidence/current-authority placement | T4 | Active ADR readers | Convention documented but inconsistently applied. | `source`/More Information = frozen evidence; `related`/body = current authority. | Active ADRs only for semantic sweep; do not erase historical evidence. | Accepted policy prose and immutable evidence addresses remain intact. | `docs/adr/README.md` |
| ADR 0025/0026 paths | T4 | Every tracked inbound reference | Long filenames include repository name. | Short filenames; zero exact old paths. | One atomic commit; IDs/numbers unchanged; Git corpus only. | Both target files and all inbound paths resolve together. | #162 owner comment; ADR 1.5 |

## Appendix B. Requirement-to-Proof Traceability

| Proof ID | Requirement(s) | Task | Method | Oracle | Command / Procedure | Expected Result | Negative Control | Environment | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PV-T1-001 | REQ-001, REQ-006 | T1 | amendment/diff/reference inspection | #161 owner decision, ADR 1.5 accepted-text rule, `e400f83f`, frozen grammar table | Inspect scoped word diff and `e400f83f`; run targeted Markdown checks and candidate-wheel `project-standards validate`. | Two cumulative amendments state sole ownership/adoption and resolved producers; original outcomes, grammar, IDs, edges, and non-doc files are unchanged. | Delete/rewrite the stale outcome sentence, change one grammar token, make ADR 0010 a second owner, or remove its exclusion; inspection must reject each shape. | isolated local execution worktree | ephemeral |
| PV-T2-001 | REQ-002, REQ-006 | T2 | amendment/reader-map/digest inspection | #160 owner decision, existing considered options/subsections, ADR 1.5 self-amendment rule | Snapshot `meta/versioning.md`; inspect scoped word diff; run targeted Markdown and candidate-wheel validation. | One cumulative self-amendment records joint determination, reader routing, and accepted cost; original outcome and `meta/versioning.md` are unchanged. | Split/supersede the ADR, add a new policy sentence, omit one reader population, or alter `meta/versioning.md`; proof must fail. | isolated local execution worktree | ephemeral |
| PV-T3-001 | REQ-003, REQ-006 | T3 | boundary/frontmatter/reciprocity/index inspection | #159 owner decision, ADR 1.5 four-part boundary/amendment distinction, existing reserved-authority text | Inspect ADR 0029 and pairwise `related` paths; run frontmatter/ID/reference validation plus targeted Markdown gates. | ADR 0029 is active/indexed, states the entire settled decision from Outcome alone, and has reciprocal edges with 0016/0021/0022; no layout/payload change exists. | Omit 0016, use one-way relation, claim a package owns a subtree, key a new class by skill-id, or treat existing layout as violating; proof must fail. | isolated local execution worktree | ephemeral |
| PV-T4-001 | REQ-004, REQ-005, REQ-006, REQ-007, REQ-008 | T4 | release-freeze inspection, full active-corpus classification, atomic rename census, integrated static validation | Release coordinator's final issue/checkpoint set; #157/#142 decisions; live state for conditionally included issues; `docs/adr/README.md` convention; ADR 1.5 filename/ID rule; Git-tracked owner census; repository validators | Verify the settled set and integrated OIDs, requiring #157 ADR 0028 and #142 control-plane ADR; reconcile every other owner-approved ADR-writing issue; re-inventory with `git grep`/`git ls-files`; perform both `git mv`s and substitutions; require zero exact old paths; run candidate-wheel validate/frontmatter formatting, Git-tracked Prettier/markdownlint, targeted Ruff, rename-summary, and diff checks. | The release-wide set is settled and integrated before T4; every post-freeze active ADR is classified; both renames appear together; all tracked paths resolve; IDs/prose/payloads/runtime remain preserved; four plan checkpoints are green. | Omit #157 or #142, proceed with an unsettled set, omit a later-settled ADR, admit a new ADR after inventory without refreezing, leave one old path, rename an ID, modernize frozen evidence, retain stale authority in `related`, commit one move alone, or edit an excluded worktree; proof rejects each. | isolated local execution worktree with direct-local Git/index access and read-only live issue access | ephemeral |

## Appendix C. Durable Evidence

Not applicable: all acceptance evidence is inexpensive and reproducible from committed Markdown, Git history, and repository validators. Ephemeral command receipts may remain in this plan's execution logs until close-out.
