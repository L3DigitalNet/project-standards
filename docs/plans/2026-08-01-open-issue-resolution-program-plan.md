---
plan_format: 3
title: 'Open-Issue Resolution Program Plan'
slug: 'open-issue-resolution-program'
size: full
status: active
revision: 3
revises_revision: 2
revision_reason: 'include the merged adr@1.4 candidate in the approved v5.15.0 boundary with its own verification task and proof'
pause_reason: ''
source: 'GitHub open-issue inventory frozen 2026-08-01T09:21:01Z; owner-approved TODO and v5.15.0 decisions; owner-authorized format-3 migration'
spec_ref: ''
created: 2026-08-01
updated: 2026-08-04
owners:
  - 'Chris Purcell / L3DigitalNet'
  - 'Coding agent under human review'
---

# Open-Issue Resolution Program Plan

> **Definition, not state.** The legacy checklist and logs at `.project-pipeline/2026-08-01-open-issue-resolution-program/` are historical, identity-less evidence. Format-3 execution state lives under its `execution/` child and starts without credited terminal tasks.

## 1. Objective

Resolve the 24 issues frozen at 2026-08-01T09:21:01Z and the three approved repository tasks through bounded, dependency-safe releases. The first release is v5.15.0: exactly CLI Documentation 1.6 plus issues #76, #77, #83, #84, #86, #87, #89, #95, #98, #105, #106, and #109. Immutable predecessor payloads, explicit publication authority, and installable evidence remain the dominant invariants.

## 2. Authority and Source Map

| Source | Source Role | Authority / Use | Version / Date | Affected Plan Surface |
| --- | --- | --- | --- | --- |
| request | normative | owner-approved issue boundary, prioritization, release policy, format-3 migration, and the 2026-08-04 decision to fold adr@1.4 into v5.15.0 | 2026-08-04 | §§1–13, T1–T37 |
| `external:https://github.com/L3DigitalNet/project-standards/pull/120` | current-state evidence | merged adr@1.4 candidate payload, its provider-input and example corrections, and the deferred release-boundary items | merged 2026-08-04 | REQ-907, T37 |
| `repo:docs/TODO.md` | normative | user and agent work queue, including retirement and program execution | 2026-08-02 | §§3–6, T29–T32 |
| `repo:docs/STATUS.md` | current-state evidence | published release and prepared-plan baseline | 2026-08-02 | §§4–5, T1, T35 |
| `repo:meta/versioning.md` | decision | accepted release classification and immutability contract | 2026-08-02 | §§3, 5, 10, T8, T28, T30, T35–T36 |
| `repo:docs/research/2026-07-09-agent-handoff-retirement-inventory.md` | operational evidence | bounded consumer-retirement inventory and remaining targets | 2026-08-02 | T32, Appendix C |
| `issue:L3DigitalNet/project-standards#55` | normative | accepted frozen issue outcome and issue-specific acceptance context | freeze 2026-08-01 | REQ and task owning issue #55 |
| `issue:L3DigitalNet/project-standards#62` | normative | accepted frozen issue outcome and issue-specific acceptance context | freeze 2026-08-01 | REQ and task owning issue #62 |
| `issue:L3DigitalNet/project-standards#75` | normative | accepted frozen issue outcome and issue-specific acceptance context | freeze 2026-08-01 | REQ and task owning issue #75 |
| `issue:L3DigitalNet/project-standards#76` | normative | accepted frozen issue outcome and issue-specific acceptance context | freeze 2026-08-01 | REQ and task owning issue #76 |
| `issue:L3DigitalNet/project-standards#77` | normative | accepted frozen issue outcome and issue-specific acceptance context | freeze 2026-08-01 | REQ and task owning issue #77 |
| `issue:L3DigitalNet/project-standards#80` | normative | accepted frozen issue outcome and issue-specific acceptance context | freeze 2026-08-01 | REQ and task owning issue #80 |
| `issue:L3DigitalNet/project-standards#83` | normative | accepted frozen issue outcome and issue-specific acceptance context | freeze 2026-08-01 | REQ and task owning issue #83 |
| `issue:L3DigitalNet/project-standards#84` | normative | accepted frozen issue outcome and issue-specific acceptance context | freeze 2026-08-01 | REQ and task owning issue #84 |
| `issue:L3DigitalNet/project-standards#86` | normative | accepted frozen issue outcome and issue-specific acceptance context | freeze 2026-08-01 | REQ and task owning issue #86 |
| `issue:L3DigitalNet/project-standards#87` | normative | accepted frozen issue outcome and issue-specific acceptance context | freeze 2026-08-01 | REQ and task owning issue #87 |
| `issue:L3DigitalNet/project-standards#88` | normative | accepted frozen issue outcome and issue-specific acceptance context | freeze 2026-08-01 | REQ and task owning issue #88 |
| `issue:L3DigitalNet/project-standards#89` | normative | accepted frozen issue outcome and issue-specific acceptance context | freeze 2026-08-01 | REQ and task owning issue #89 |
| `issue:L3DigitalNet/project-standards#90` | normative | accepted frozen issue outcome and issue-specific acceptance context | freeze 2026-08-01 | REQ and task owning issue #90 |
| `issue:L3DigitalNet/project-standards#91` | normative | accepted frozen issue outcome and issue-specific acceptance context | freeze 2026-08-01 | REQ and task owning issue #91 |
| `issue:L3DigitalNet/project-standards#95` | normative | accepted frozen issue outcome and issue-specific acceptance context | freeze 2026-08-01 | REQ and task owning issue #95 |
| `issue:L3DigitalNet/project-standards#98` | normative | accepted frozen issue outcome and issue-specific acceptance context | freeze 2026-08-01 | REQ and task owning issue #98 |
| `issue:L3DigitalNet/project-standards#99` | normative | accepted frozen issue outcome and issue-specific acceptance context | freeze 2026-08-01 | REQ and task owning issue #99 |
| `issue:L3DigitalNet/project-standards#101` | normative | accepted frozen issue outcome and issue-specific acceptance context | freeze 2026-08-01 | REQ and task owning issue #101 |
| `issue:L3DigitalNet/project-standards#102` | normative | accepted frozen issue outcome and issue-specific acceptance context | freeze 2026-08-01 | REQ and task owning issue #102 |
| `issue:L3DigitalNet/project-standards#105` | normative | accepted frozen issue outcome and issue-specific acceptance context | freeze 2026-08-01 | REQ and task owning issue #105 |
| `issue:L3DigitalNet/project-standards#106` | normative | accepted frozen issue outcome and issue-specific acceptance context | freeze 2026-08-01 | REQ and task owning issue #106 |
| `issue:L3DigitalNet/project-standards#107` | normative | accepted frozen issue outcome and issue-specific acceptance context | freeze 2026-08-01 | REQ and task owning issue #107 |
| `issue:L3DigitalNet/project-standards#108` | normative | accepted frozen issue outcome and issue-specific acceptance context | freeze 2026-08-01 | REQ and task owning issue #108 |
| `issue:L3DigitalNet/project-standards#109` | normative | accepted frozen issue outcome and issue-specific acceptance context | freeze 2026-08-01 | REQ and task owning issue #109 |

Conflict precedence: current explicit owner decisions govern release boundaries and authorization; accepted issue outcomes govern their defect or feature; repository implementation and tests establish current state only. The legacy plan grammar and identity-less checklist are superseded as execution mechanisms, while their approved issue outcomes remain preserved here.

## 3. Scope, Boundaries, and Constraints

### 3.1 In Scope

- The frozen issues #55, #62, #75–#77, #80, #83, #84, #86–#91, #95, #98, #99, #101, #102, and #105–#109.
- v5.15.0 as the exact owner-approved combined correction release, including the merged adr@1.4 candidate folded into its boundary on 2026-08-04.
- Immutable successor payloads, control-plane and tooling corrections, release qualification, issue disposition, MCP release documentation, and the two remaining Agent Handoff consumers.
- Later Agent Handoff, deferred tooling, Project Spec conformance, and conversion trains already retained by the approved program.
- Format-3 execution control through the repository-local bridge and identity-bearing task checkpoints.

### 3.2 Out of Scope and Deferred

- Issues opened after the inventory freeze unless appended under the discovered-work policy.
- Retiring `control_plane/provider_inputs.py`, self-hosted CI, Usage Documentation Site V2, and unrelated roadmap work.
- Rewriting published tags, release assets, predecessor payload bytes, or prior Git history.
- Treating legacy scratch completion markers as format-3 checkpoints; T30 and T1 evidence must be replayed.
- Issues #88 and #99 in v5.15.0; T36 owns their later release.

### 3.3 Ownership and Preserved Behavior

| Boundary | Owner / Responsibility | Failure / Change Requests Route To |
| --- | --- | --- |
| This repository | source, packages, control plane, tests, release metadata, and owner documentation | owning task or append-only correction |
| GitHub and consumer repositories | issue, publication, protected-branch, and remote truth after explicit authorization | operational task and owner gate |
| Immutable releases | published tags, assets, and advertised package versions | successor release; never rewrite |
| Generated execution state | repository-local `scripts/plan.py` only | bridge rejection, recovery, or plan-authoring revision |
| Must preserve | predecessor bytes, consumer-owned configuration, unrelated work, and fail-closed validation | task proof and final qualification |

### 3.4 Constraints and Authorization

| ID | Constraint / Authorization Boundary | Source | Affected Task(s) |
| --- | --- | --- | --- |
| C-001 | Run `scripts/verify.sh` for intermediate product tasks and `scripts/verify.sh --full` only at final content and release qualification gates. | `repo:AGENTS.md` | T2–T20, T25, T27–T28, T30–T36 |
| C-002 | Build and extract a fresh candidate wheel before installed-authority claims. | `repo:AGENTS.md` | T8, T25, T28, T35–T36 |
| C-003 | Publication, pushes, protected merges, releases, and issue writes require action-and-target-specific authorization. | request | T1, T8, T25, T28–T29, T32, T35–T36 |
| C-004 | Preserve immutable package predecessors and unrelated work; stage only task-owned changes. | request | all active tasks |
| C-005 | One serialized format-3 executor owns the whole plan; every state transition uses `scripts/plan.py state`. | request | all active tasks |

## 4. Current State and Target State

### 4.1 Current State

Project Standards 5.14.0 is published. CLI Documentation 1.6 and the merged adr@1.4 payload exist as unreleased candidates, and the approved v5.15.0 boundary is frozen apart from the owner's 2026-08-04 addition of adr@1.4. The adr@1.4 merge deliberately deferred its release-boundary items, so the tool release still reads 5.14.0, four root `README.md` references still name adr@1.3, and the `.standards` consumer-catalog projection is stale. T30 product changes and T1.1–T1.5 observations exist in Git and legacy scratch, but their commits/checklists do not carry the ordered format-3 `Plan-Id`, `Plan-Task`, `Plan-Revision`, `Plan-Definition-Digest`, `Plan-Status`, `Plan-Requirements`, and `Plan-Proofs` trailers. The byte-identical format-3 bridge and fresh execution state are present, every task is unstarted, and T30 is solely ready. Execution preflight remains blocked because the canonical bridge fails this repository's Ruff formatting, lint, and BasedPyright profiles.

### 4.2 Target State

The durable master validates as `plan_format: 3`; the byte-identical repository-local bridge passes repository static gates while retaining authoring, validation, state, recovery, and checkpoint identity. Execution resumes the existing generated format-3 state, replays T30 and T1 proof under valid checkpoints, completes v5.15.0 before later trains, and preserves durable operational/release evidence through close-out.

### 4.3 Delta Summary

| Area | Current | Target | Must Preserve | Risk / Unknown |
| --- | --- | --- | --- | --- |
| Execution contract | valid format-3 master and fresh `execution/` state; canonical bridge blocked by repository static profiles | byte-identical bridge passes repository gates and drives atomic transitions from T30 | old logs remain historical and untouched | no terminal state can be credited automatically |
| v5.15.0 | approved but unimplemented | published exact combined release | v5.14 and all payload predecessors | release aggregation remains broad |
| Later trains | approved dependency graph | sequenced after v5.15.0 | issue scope and owner gates | external approval latency |
| Consumer retirement | two protected consumers remain | verified retirement and remote parity | unrelated consumer changes | protected merge authorization |

## 5. Change Surface and Architecture

### 5.1 Components and Ownership

| Component / Surface | Current Responsibility | Planned Responsibility | Paths / Contracts | Owning Task(s) |
| --- | --- | --- | --- | --- |
| Agent Handoff engine/package | released 1.8 plus open authority issues | corrected successor and verified retirement | `src/project_standards/agent_handoff/`, package family | T1–T8, T32 |
| Control plane and adapters | planner/migration/TOML/JSONC current behavior | issue-specific corrections without intermediate release | `src/project_standards/control_plane/` | T9–T14 |
| Python/Markdown/CLI tooling | released predecessors plus candidates | bounded successors and exact release activation | `standards/` families | T16–T21, T31, T33–T36 |
| Project Spec features | accepted issues without approved child designs | approved spec/plan followed by implementation | `docs/specs/`, `docs/plans/` | T24–T28 |
| Release and tracker truth | published 5.14 plus frozen open set | qualified releases and reconciled frozen inventory | release metadata, GitHub, handoff | T8, T28–T30, T35–T36 |
| Execution state | byte-identical format-3 bridge, fresh identity-bound projection, and repository-static incompatibility | repository-compatible canonical bridge drives the existing projection | `scripts/plan.py`, `.project-pipeline/.../execution/` | plan authoring boundary |

### 5.2 Context / Control / Data / State Views

The control plane remains the sole package-composition and consumer-file authority. Package tasks create immutable successors; qualification tasks alone aggregate catalog/release metadata and external publication. Operational tasks never infer authority from the plan: they stop at their AUTHORIZATION stage until the exact external action is approved.

### 5.3 Change-Surface Matrix

| Surface | Current Owner | Target Change | Invariant / Preservation | Proof | Task |
| --- | --- | --- | --- | --- | --- |
| Observable behavior | subsystem owners | one regression-bounded correction per issue | no unrelated behavior changes | TC-T2-001–TC-T20-001 | T2–T20 |
| Architecture / dependency direction | control plane and V2 packages | retain authority while correcting bounded seams | no legacy authority restoration | TC-T10-001, TC-T31-001 | T10, T31 |
| Public / cross-task interface | package providers and CLI | successor-only compatible contracts | predecessors remain selectable | TC-T8-001, TC-T35-001 | T8, T35 |
| Data / persistent state | Git and immutable package history | additive checkpoints and successors | no history rewrite | TC-T30-001, TC-T35-001 | T30, T35 |
| Configuration / user-owned files | consumer plus typed provider spans | preserve undeclared/user-owned content | fail before unauthorized writes | TC-T13-001, TC-T19-001, TC-T33-001 | T13, T19, T33 |
| Security / trust boundary | validation and redaction owners | preserve fail-closed reporting and secret references | no values in evidence | TC-T7-001, TC-T11-001 | T7, T11 |
| Compatibility / migration | migration planner and package predecessors | actionable V4/V5 transition and successor coexistence | prior payload bytes unchanged | TC-T10-001, TC-T12-001 | T10, T12 |
| Operations / deployment | owner plus release/consumer workflows | explicit approval, proof, and recovery | no implied publication authority | TC-T32-001, TC-T35-001 | T32, T35 |
| Documentation / owner truth | repository docs and GitHub | current install/release/tracker truth | historical releases remain factual | TC-T22-001, TC-T29-001 | T22, T29 |
| Durable acceptance evidence | release and operational tasks | sanitized EV records | no secrets or unbounded logs | Appendix C | T1, T8, T23, T25, T28–T30, T32, T35–T36 |

### 5.4 Binding Decisions

| ID | Decision | Rationale | Alternatives Actually Considered | Source / ADR | Affected Task(s) |
| --- | --- | --- | --- | --- | --- |
| D-001 | v5.15.0 contains the exact twelve-issue set plus CLI Documentation 1.6. | owner-approved combined boundary avoids intermediate incompatible releases | separate control-plane/tooling releases rejected | request | T9–T14, T17–T18, T20, T23, T31, T33–T35 |
| D-002 | Issues #88/#99 follow v5.15.0. | shared tooling scope must not leak into the approved release | inclusion in v5.15.0 rejected | request | T16, T19, T36 |
| D-003 | Legacy task observations are replayed under format-3 checkpoints. | identity-less history cannot be credited safely | backfilled or inferred checkpoint identity rejected | request | T1, T30 |
| D-004 | T15 and T21 remain as superseded non-executable history. | preserve permanent task IDs while replacement qualifiers own acceptance | deletion or executable no-op tasks rejected | request | T15, T21, T35–T36 |
| D-005 | T31's retained “activated and qualified by T35” acceptance phrase declares release routing, not prior completion of T35. | preserve T31 task identity while preventing a circular completion interpretation | a separate release train or T35-before-T31 ordering rejected | request | T31, T35 |

## 6. Requirements and Acceptance

| ID | Requirement | Source | Priority | Owner Task | Task(s) | Proof(s) |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-080 | Close #80 from the published Agent Handoff 1.8 evidence. | #80 | Must | T1 | T1 | TC-T1-001 |
| REQ-075 | Pair Agent Handoff enrichment by semantic rule. | #75 | Must | T2 | T2 | TC-T2-001 |
| REQ-090 | Exclude lock-authenticated current artifacts from legacy findings. | #90 | Must | T3 | T3 | TC-T3-001 |
| REQ-091 | Run read-only commands against the currently locked payload before refresh. | #91 | Must | T4 | T4 | TC-T4-001 |
| REQ-101 | Make the documented pre-apply size/shape checkpoint usable or redefine it accurately. | #101 | Must | T5 | T5 | TC-T5-001 |
| REQ-102 | Detect legacy and managed startup handlers that would inject twice. | #102 | Must | T6 | T6 | TC-T6-001 |
| REQ-107 | Align engine and provider secret-reference policy after owner decision. | #107 | Must | T7 | T7 | TC-T7-001 |
| REQ-076 | Converge create-only→managed transitions over absent targets in one apply. | #76 | Must | T9 | T9 | TC-T9-001 |
| REQ-077 | Create declared empty managed artifacts instead of planning no-op. | #77 | Must | T9 | T9 | TC-T9-001 |
| REQ-083 | Produce an actionable V4 Python Tooling migration plan. | #83 | Must | T10 | T10 | TC-T10-001 |
| REQ-087 | Make managed successor drift actionable and intent-preserving. | #87 | Must | T11 | T11 | TC-T11-001 |
| REQ-098 | Validate selected Frontmatter IDs before retiring legacy authority. | #98 | Must | T12 | T12 | TC-T12-001 |
| REQ-105 | Coalesce TOML creates sharing an inline parent. | #105 | Must | T13 | T13 | TC-T13-001 |
| REQ-106 | Remove JSONC residue without losing comments or line endings. | #106 | Must | T14 | T14 | TC-T14-001 |
| REQ-088 | Bound Prettier to Markdown Tooling's declared corpus. | #88 | Must | T16 | T16 | TC-T16-001 |
| REQ-089 | Resolve local `src` source before an untyped editable install. | #89 | Must | T17 | T17 | TC-T17-001 |
| REQ-095 | Bound Ruff to declared Python source and test roots. | #95 | Must | T18 | T18 | TC-T18-001 |
| REQ-099 | Preserve or explicitly model Ruff plugin sub-tables. | #99 | Must | T19 | T19 | TC-T19-001 |
| REQ-086 | Support or explicitly reject monorepos with no implicit Python root. | #86 | Must | T20 | T20 | TC-T20-001 |
| REQ-108 | Prevent published MCP docs from presenting candidate installation as current. | #108 | Must | T22 | T22 | TC-T22-001 |
| REQ-109 | Reject fresh Python Tooling adoption before writing when consumer-owned PEP 621 project metadata is absent. | #109; owner decision 2026-08-01 | Must | T33 | T33 | TC-T33-001 |
| REQ-084 | Reproduce and fix, or evidence-dispose, the transient PyYAML failure. | #84 | Must | T23 | T23 | TC-T23-001 |
| REQ-062 | Add an approved conformance surface for shared Project Spec boilerplate. | #62 | Should | T24 | T24, T25 | TC-T24-001, TC-T25-001 |
| REQ-055 | Add an approved preservation-first house-format conversion path. | #55 | Should | T26 | T26, T27 | TC-T26-001, TC-T27-001 |
| REQ-900 | Preserve immutable predecessors and qualify each release train once. | Release contract | Must | T35 | T8, T28, T35, T36 | TC-T8-001, TC-T28-001, TC-T35-001, TC-T36-001 |
| REQ-901 | Leave no frozen issue open without an accepted disposition. | Owner request | Must | T29 | T29 | TC-T29-001 |
| REQ-902 | Classify owner-designated catalog majors as MAJOR, releases with a standard-package version advance as MINOR, and releases without one as PATCH. A newly introduced package or a newly advertised version above that package's prior advertised maximum is an advance; internal and reference-only packages count, while older retained history and unadvertised payloads do not. Advertised versions are permanent and cannot be removed in any release. | `docs/TODO.md`; owner decisions 2026-08-01 | Must | T30 | T30 | TC-T30-001 |
| REQ-903 | Replace Python Tooling 1.10's stale V1-authority statement in the already-planned compatible successor without changing 1.10. | `docs/TODO.md`; owner decision 2026-08-01 | Must | T31 | T31 | TC-T31-001 |
| REQ-904 | Manually converge and verify the two remaining Agent Handoff consumers, then close the retirement records. | `docs/TODO.md`; owner decision 2026-08-01 | Must | T32 | T32 | TC-T32-001 |
| REQ-905 | Publish the selected twelve-issue correction set together in v5.15.0, with no intermediate control-plane or Python Tooling release. | Owner decision 2026-08-02 | Must | T35 | T35 | TC-T35-001 |
| REQ-906 | Include the existing CLI Documentation 1.6 candidate in v5.15.0 while retaining 1.5 unchanged and selectable. | Owner decision 2026-08-02 | Must | T35 | T34, T35 | TC-T34-001, TC-T35-001 |
| REQ-907 | Include the merged adr@1.4 candidate in v5.15.0 while retaining adr@1.3 unchanged and selectable. The deferred release-boundary advance from adr@1.3 is already compelled by REQ-900's full local and hosted gate acceptance in T35. | Owner decision 2026-08-04; `external:https://github.com/L3DigitalNet/project-standards/pull/120` | Must | T37 | T37 | TC-T37-001 |

## 7. Verification and Evidence Strategy

### 7.1 Commands and Layers

- **Authoritative commands:** focused pytest/package tests; `uv run ruff format --check .`; `uv run ruff check .`; `uv run basedpyright`; package/graph/schema/projection checks; `scripts/verify.sh`; final `scripts/verify.sh --full`; Markdown tooling; Agent Handoff validation/drift; release and hosted checks.
- **Layers:** characterization, regression, property/layout, contract/schema, migration, real-tool integration, candidate/installed-wheel, release recovery, documentation inspection, and authorized operational acceptance.

### 7.2 Oracle and Negative-Control Policy

- Accepted issue reproductions, immutable predecessor bytes, provider/native tool behavior, package schemas, release policy, and independently observed remote/installed state are the oracles.
- Negative controls retain prior failing fixtures, malicious/tampered inputs, out-of-scope files, partial transitions, predecessor mutation checks, missing authorization, and repeat/no-op probes.
- Verification-only and operational tasks do not repair failures in place; they append correction work and rerun from their anchor.

### 7.3 Environments and Evidence

| Environment | Purpose | Prerequisites | Version / Provenance | Durable Evidence |
| --- | --- | --- | --- | --- |
| local source and candidate wheel | task regressions and installed parity | locked uv/npm inputs and fresh extracted wheel | commit, tool versions, wheel digest | EV-001–EV-005, EV-007–EV-010 |
| hosted GitHub checks/releases/issues | hosted acceptance and publication truth | exact commit and explicit action authorization | run IDs, tag/assets, issue IDs | EV-001–EV-005, EV-007–EV-009 |
| protected consumer repositories | Agent Handoff retirement | exact repository/branch, clean review, merge authority | branch OIDs and selected control plane | EV-006 |

Repeatable local output remains ephemeral. Release, issue, protected-branch, version-bound investigation, and program-closeout evidence is durable under Appendix C.

### 7.4 Failure Triage

A verification or operational task records the failed boundary, appends an owner-scoped correction task with `corrects` and `discovered_from`, waits for its checkpoint, then reruns the complete affected contract. Published artifacts are never rewritten.

## 8. Execution Summary

| Task | Title | Disposition | Work Type | Phase | Depends On | Requirement(s) | Primary Proof | Parallel / Conflict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T1 | Close #80 from v5.14.0 evidence | active | operational | P1 | T30 | REQ-080 | TC-T1-001 | no / serialized whole-plan executor |
| T2 | Correct enrichment pairing for #75 | active | behavior | P5 | T1, T35 | REQ-075 | TC-T2-001 | no / serialized whole-plan executor |
| T3 | Make legacy inventory lock-aware for #90 | active | behavior | P5 | T1, T35 | REQ-090 | TC-T3-001 | no / serialized whole-plan executor |
| T4 | Route read-only commands through locked payloads for #91 | active | behavior | P5 | T3 | REQ-091 | TC-T4-001 | no / serialized whole-plan executor |
| T5 | Restore the pre-apply report checkpoint for #101 | active | behavior | P5 | T4 | REQ-101 | TC-T5-001 | no / serialized whole-plan executor |
| T6 | Detect duplicate startup injection for #102 | active | behavior | P5 | T3 | REQ-102 | TC-T6-001 | no / serialized whole-plan executor |
| T7 | Align secret-reference policy for #107 | active | behavior | P5 | T1, T35 | REQ-107 | TC-T7-001 | no / serialized whole-plan executor |
| T8 | Qualify the Agent Handoff authority train | active | operational | P5 | T2, T3, T4, T5, T6, T7 | REQ-900 | TC-T8-001 | no / serialized whole-plan executor |
| T9 | Correct absent-artifact planning for #76/#77 | active | behavior | P1 | T30 | REQ-076, REQ-077 | TC-T9-001 | no / serialized whole-plan executor |
| T10 | Supply V4 transform evidence for #83 | active | behavior | P1 | T30 | REQ-083 | TC-T10-001 | no / serialized whole-plan executor |
| T11 | Make successor drift actionable for #87 | active | behavior | P2 | T9 | REQ-087 | TC-T11-001 | no / serialized whole-plan executor |
| T12 | Validate Frontmatter IDs before retirement for #98 | active | behavior | P2 | T10 | REQ-098 | TC-T12-001 | no / serialized whole-plan executor |
| T13 | Coalesce TOML creates for #105 | active | behavior | P2 | T9 | REQ-105 | TC-T13-001 | no / serialized whole-plan executor |
| T14 | Normalize JSONC deletion residue for #106 | active | behavior | P2 | T9 | REQ-106 | TC-T14-001 | no / serialized whole-plan executor |
| T15 | Superseded control-plane qualifier | superseded | verification | P2 | T9, T10, T11, T12, T13, T14, T23 | None | None | no / serialized whole-plan executor |
| T16 | Bound Markdown formatting scope for #88 | active | behavior | P6 | T35 | REQ-088 | TC-T16-001 | no / serialized whole-plan executor |
| T17 | Fix Python import precedence for #89 | active | behavior | P3 | T9, T10, T11, T12, T13, T14 | REQ-089 | TC-T17-001 | no / serialized whole-plan executor |
| T18 | Bound Ruff scope for #95 | active | behavior | P3 | T9, T10, T11, T12, T13, T14 | REQ-095 | TC-T18-001 | no / serialized whole-plan executor |
| T19 | Preserve Ruff plugin configuration for #99 | active | behavior | P6 | T35 | REQ-099 | TC-T19-001 | no / serialized whole-plan executor |
| T20 | Add a no-implicit-root layout for #86 | active | behavior | P3 | T17, T18 | REQ-086 | TC-T20-001 | no / serialized whole-plan executor |
| T21 | Superseded tooling qualifier | superseded | verification | P3 | T16, T17, T18, T19, T20, T31, T33 | None | None | no / serialized whole-plan executor |
| T22 | Correct MCP release docs for #108 | active | documentation | P5 | T1 | REQ-108 | TC-T22-001 | no / serialized whole-plan executor |
| T23 | Dispose of the PyYAML transient for #84 | active | brownfield-behavior | P1 | T30 | REQ-084 | TC-T23-001 | no / serialized whole-plan executor |
| T24 | Specify conformance linting for #62 | active | documentation | P7 | T36 | REQ-062 | TC-T24-001 | no / serialized whole-plan executor |
| T25 | Implement conformance linting for #62 | active | operational | P7 | T24 | REQ-062 | TC-T25-001 | no / serialized whole-plan executor |
| T26 | Specify house-format conversion for #55 | active | documentation | P8 | T25 | REQ-055 | TC-T26-001 | no / serialized whole-plan executor |
| T27 | Implement preservation-first conversion for #55 | active | behavior | P8 | T26 | REQ-055 | TC-T27-001 | no / serialized whole-plan executor |
| T28 | Qualify the feature release | active | operational | P8 | T27 | REQ-900 | TC-T28-001 | no / serialized whole-plan executor |
| T29 | Reconcile the tracker and close the program | active | operational | P9 | T8, T22, T23, T24, T25, T26, T27, T28, T32 | REQ-901 | TC-T29-001 | no / serialized whole-plan executor |
| T30 | Align catalog release-level classification | active | verification | P1 | None | REQ-902 | TC-T30-001 | no / serialized whole-plan executor |
| T31 | Correct the Python Tooling successor's authority statement | active | behavior | P3 | T20, T30 | REQ-903 | TC-T31-001 | no / serialized whole-plan executor |
| T32 | Finish Agent Handoff consumer retirement | active | operational | P1 | T30 | REQ-904 | TC-T32-001 | no / serialized whole-plan executor |
| T33 | Guard Python Tooling fresh adoption for #109 | active | behavior | P3 | T20, T31 | REQ-109 | TC-T33-001 | no / serialized whole-plan executor |
| T34 | Verify the CLI Documentation 1.6 candidate | active | brownfield-behavior | P1 | T30 | REQ-906 | TC-T34-001 | no / serialized whole-plan executor |
| T37 | Verify the ADR 1.4 candidate | active | brownfield-behavior | P1 | T30 | REQ-907 | TC-T37-001 | no / serialized whole-plan executor |
| T35 | Qualify and publish v5.15.0 | active | operational | P4 | T9, T10, T11, T12, T13, T14, T17, T18, T20, T23, T31, T33, T34, T37 | REQ-900, REQ-905, REQ-906 | TC-T35-001 | no / serialized whole-plan executor |
| T36 | Qualify deferred tooling successors | active | operational | P6 | T16, T19 | REQ-900 | TC-T36-001 | no / serialized whole-plan executor |

## 9. Implementation Tasks

### Phase P1: Entry Work and Independent Preconditions

#### T1: Close #80 from v5.14.0 evidence

- **disposition:** active
- **outcome:** Close #80 from the already-published v5.14.0 evidence without modifying or republishing release artifacts.
- **work_type:** operational
- **checkpoint:** one green commit containing EV-001 and the required ordered `Plan-*` trailers
- **boundary:** operational
- **depends_on:** [T30]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T30 before this outcome
- **requirements:** [REQ-080]
- **proof:** [TC-T1-001]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#80]
- **consumes:** [approved task inputs, exact repository and external state at authorization]
- **produces:** [t1 verified operational result]
- **preserves:** [immutable history, predecessor bytes, unrelated work, and action-specific authorization]
- **invariants:** [no external effect before authorization; failed proof cannot be reported as success]
- **executor_discretion:** [bounded evidence-capture mechanics and repository-conforming private helpers]
- **files:** [`docs/handoff/sessions/2026-08.md` (modify or create; owner T1), `docs/research/2026-08-01-agent-handoff-1-8-closeout-evidence.md` (modify or create; owner T1)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [EV-001]
- **recovery:** stop at the last verified boundary, do not repeat an unproven external effect, retain durable evidence, and use the task-specific no-op or recovery proof
- **acceptance:** TC-T1-001 proves exact v5.13.0/Agent Handoff 1.7 direct and harness-style launches reproduce the shim failure; direct, uv-fallback, and unavailable-runtime successor lanes behave correctly for both harnesses in published v5.14.0; hosted gates and asset bytes verify; issue #80 closes with exact evidence.
- **sub-tasks:**
  - **T1.1 AUTHORIZATION** — obtain current action-and-target-specific approval for every external write, publication, merge, or closure.
  - **T1.2 PREFLIGHT** — confirm exact targets, branch/release state, prerequisites, rollback boundary, and clean attributable scope.
  - **T1.3 APPLY** — perform only the authorized operational changes in the declared order.
  - **T1.4 VERIFY** — verify remote/installed/issue state and repository truth from independent observations.
  - **T1.5 PROVE NO-OP OR RECOVERY** — prove repeat convergence or the declared recovery path without rewriting immutable history.
  - **T1.6 CAPTURE EVIDENCE** — run TC-T1-001; commit sanitized durable evidence and the format-3 checkpoint.

#### T9: Correct absent-artifact planning for #76/#77

- **disposition:** active
- **outcome:** Create empty managed files and converge create-only→managed absent targets in one apply.
- **work_type:** behavior
- **checkpoint:** one green commit with the required ordered `Plan-*` checkpoint trailers
- **boundary:** internal
- **depends_on:** [T30]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T30 before this outcome
- **requirements:** [REQ-076, REQ-077]
- **proof:** [TC-T9-001]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#76, issue:L3DigitalNet/project-standards#77]
- **files:** [`src/project_standards/control_plane/planner.py` (modify or create; owner T9)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** keep the task open, restore the verified GREEN checkpoint if refactoring regresses proof, and append correction work when the approved boundary must expand
- **acceptance:** TC-T9-001 proves empty `py.typed`/`.gitkeep` and deleted-container policy transitions converge while verification stays fail-closed.
- **sub-tasks:**
  - **T9.1 RED** — add empty-CREATE and policy-transition regressions.
  - **T9.2 Verify RED** — confirm no-op/two-cycle behavior.
  - **T9.3 GREEN** — distinguish `None` from empty bytes and align policy authority.
  - **T9.4 Verify GREEN** — run planner/executor/lock matrices.
  - **T9.5 REFACTOR** — name lifecycle policy authority.
  - **T9.6 Verify Task** — control-plane tests, Ruff, BasedPyright, `scripts/verify.sh`; create the format-3 checkpoint commit.

#### T10: Supply V4 transform evidence for #83

- **disposition:** active
- **outcome:** Produce a Python Tooling migration plan or actionable package-specific finding.
- **work_type:** behavior
- **checkpoint:** one green commit with the required ordered `Plan-*` checkpoint trailers
- **boundary:** internal
- **depends_on:** [T30]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T30 before this outcome
- **requirements:** [REQ-083]
- **proof:** [TC-T10-001]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#83]
- **files:** [`src/project_standards/control_plane/migration.py` (modify or create; owner T10)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** keep the task open, restore the verified GREEN checkpoint if refactoring regresses proof, and append correction work when the approved boundary must expand
- **acceptance:** TC-T10-001 proves the issue fixture previews in human/JSON modes; missing evidence names package, transform, input, and safe action.
- **sub-tasks:**
  - **T10.1 RED** — add the exact V4 Python Tooling fixture.
  - **T10.2 Verify RED** — confirm the opaque evidence failure.
  - **T10.3 GREEN** — derive exact evidence or emit bounded diagnostics.
  - **T10.4 Verify GREEN** — run migration/transform/corruption parity tests.
  - **T10.5 REFACTOR** — centralize evidence without restoring legacy authority.
  - **T10.6 Verify Task** — migration tests, Ruff, BasedPyright, `scripts/verify.sh`; create the format-3 checkpoint commit.

#### T23: Dispose of the PyYAML transient for #84

- **disposition:** active
- **outcome:** Reproduce a repository-owned defect and fix it, or record a bounded no-reproduction disposition before v5.15.0.
- **work_type:** brownfield-behavior
- **checkpoint:** one green commit containing EV-003 and the required ordered `Plan-*` trailers
- **boundary:** internal
- **depends_on:** [T30]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T30 before this outcome
- **requirements:** [REQ-084]
- **proof:** [TC-T23-001]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#84]
- **files:** [`docs/research/2026-08-01-pyyaml-transient-disposition.md` (modify or create; owner T23)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [EV-003]
- **recovery:** preserve the isolated baseline and evidence; implement only a reproduced repository-owned defect, otherwise retain the bounded disposition without inventing a fix
- **acceptance:** TC-T23-001 proves fresh installs, concurrent install/launch, and repeated paired previews establish cause or a documented threshold; T35 remains blocked until the evidence-backed disposition is accepted.
- **sub-tasks:**
  - **T23.0 CHARACTERIZE** — freeze the isolated fresh-install, concurrent install/launch, and repeated paired-preview matrix.
  - **T23.1 Verify Baseline** — confirm the environment, versions, integrity checks, and evidence destination isolate repository behavior.
  - **T23.2 RED** — reproduce missing or partial installed bytes, or execute the accepted no-reproduction threshold.
  - **T23.3 Verify RED** — attribute a reproduced failure to the repository seam, or verify the bounded no-reproduction result.
  - **T23.4 GREEN** — implement only a proven repository fix or finalize the evidence-backed disposition.
  - **T23.5 Verify GREEN** — rerun the complete matrix and integrity checks without weakening its threshold.
  - **T23.6 REFACTOR** — remove duplication only when a proven fix introduced it; preserve the matrix and disposition.
  - **T23.7 Verify Task** — run TC-T23-001; commit EV-003 and the format-3 checkpoint.

#### T30: Align catalog release-level classification

- **disposition:** active
- **outcome:** Verify the landed catalog release-level classification against the owner-approved package-composition policy and preserve its immutable-package and forbidden-transition proof.
- **work_type:** verification
- **checkpoint:** one green commit containing EV-010 and the required ordered `Plan-*` trailers
- **boundary:** internal
- **depends_on:** []
- **dependency_reason:** none
- **requirements:** [REQ-902]
- **proof:** [TC-T30-001]
- **source_refs:** [request]
- **files:** [`docs/research/2026-08-01-release-level-classification-evidence.md` (create; owner T30)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [EV-010]
- **recovery:** block on any mismatch, retain bounded diagnostics, append a correction task instead of editing inside verification, and rerun from ANCHOR
- **acceptance:** TC-T30-001 proves a matching tool/catalog major increment is accepted as the owner's MAJOR designation unless another contract is forbidden; otherwise any standard-package version advance requires exactly MINOR and no standard-package version advance requires exactly PATCH. Per package ID, a newly introduced package or a newly advertised version above the prior advertised maximum is an advance; internal and reference-only packages count, while older retained history and unadvertised payloads do not. Advertised-version removal, package downgrade, immutable-byte violations, and same-catalog breaking-default promotion remain forbidden, and ADR 0024 plus `meta/versioning.md` use the same rule.
- **sub-tasks:**
  - **T30.1 ANCHOR** — record the landed implementation commit, accepted owner rule, focused matrix, and EV-010 destination.
  - **T30.2 VERIFY PREREQUISITES** — confirm repository state, immutable predecessor fixtures, tool versions, and authoritative policy text.
  - **T30.3 RUN** — execute the focused release/package CLI matrices, Ruff, BasedPyright, package contracts, and `scripts/verify.sh` without changing implementation.
  - **T30.4 TRIAGE** — classify any mismatch and append correction work; do not repair inside verification.
  - **T30.5 RERUN** — rerun the complete affected matrix after corrections or record why no rerun applies.
  - **T30.6 CAPTURE EVIDENCE** — run TC-T30-001; commit EV-010 and the format-3 checkpoint.

#### T32: Finish Agent Handoff consumer retirement

- **disposition:** active
- **outcome:** Manually converge the two remaining protected consumers and close the retirement records without creating generalized migration machinery.
- **work_type:** operational
- **checkpoint:** one green commit containing EV-006 and the required ordered `Plan-*` trailers
- **boundary:** operational
- **depends_on:** [T30]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T30 before this outcome
- **requirements:** [REQ-904]
- **proof:** [TC-T32-001]
- **source_refs:** [request]
- **consumes:** [approved task inputs, exact repository and external state at authorization]
- **produces:** [t32 verified operational result]
- **preserves:** [immutable history, predecessor bytes, unrelated work, and action-specific authorization]
- **invariants:** [no external effect before authorization; failed proof cannot be reported as success]
- **executor_discretion:** [bounded evidence-capture mechanics and repository-conforming private helpers]
- **files:** [`docs/research/2026-07-09-agent-handoff-retirement-inventory.md` (modify or create; owner T32)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [EV-006]
- **recovery:** stop at the last verified boundary, do not repeat an unproven external effect, retain durable evidence, and use the task-specific no-op or recovery proof
- **acceptance:** TC-T32-001 proves each remaining consumer has only the standards-managed Agent Handoff document/hook pair on its authoritative branch, passes `project-standards agent-handoff validate --repo .` and `drift-check --repo .` using its selected control plane, preserves unrelated work, and has remote parity after separately authorized publication; retirement records name the verified final state.
- **sub-tasks:**
  - **T32.1 AUTHORIZATION** — obtain current action-and-target-specific approval for every external write, publication, merge, or closure.
  - **T32.2 PREFLIGHT** — confirm exact targets, branch/release state, prerequisites, rollback boundary, and clean attributable scope.
  - **T32.3 APPLY** — perform only the authorized operational changes in the declared order.
  - **T32.4 VERIFY** — verify remote/installed/issue state and repository truth from independent observations.
  - **T32.5 PROVE NO-OP OR RECOVERY** — prove repeat convergence or the declared recovery path without rewriting immutable history.
  - **T32.6 CAPTURE EVIDENCE** — run TC-T32-001; commit sanitized durable evidence and the format-3 checkpoint.

#### T34: Verify the CLI Documentation 1.6 candidate

- **disposition:** active
- **outcome:** Review and qualify the existing CLI Documentation 1.6 candidate for inclusion in v5.15.0 without redesigning or overwriting unrelated in-flight work.
- **work_type:** brownfield-behavior
- **checkpoint:** one green commit with the required ordered `Plan-*` checkpoint trailers
- **boundary:** internal
- **depends_on:** [T30]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T30 before this outcome
- **requirements:** [REQ-906]
- **proof:** [TC-T34-001]
- **source_refs:** [request]
- **files:** [`standards/cli-documentation/standard.toml` (modify or create; owner T34)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** keep the task open, restore the verified GREEN checkpoint if refactoring regresses proof, and append correction work when the approved boundary must expand
- **acceptance:** TC-T34-001 proves 1.5 remains byte-identical/selectable; 1.6's Python, Go, and generic profiles validate; the Go workflow builds one explicit package and verifies the built command; package, graph, schema, projection, Markdown, and focused real-tool checks pass; any correction stays within the candidate contract.
- **sub-tasks:**
  - **T34.0 CHARACTERIZE** — inventory the in-flight candidate, its prior task evidence, shared-file ownership, and any unverified surface.
  - **T34.1 Verify Baseline** — confirm the candidate inventory and predecessor behavior match the current repository and immutable 1.5 bytes.
  - **T34.2 RED** — prove CLI Documentation 1.5 lacks the approved Go contract and exercise candidate negative controls.
  - **T34.3 Verify RED** — distinguish predecessor behavior and intentional negative controls from candidate defects.
  - **T34.4 GREEN** — preserve the existing candidate or apply only evidence-required corrections within its approved contract.
  - **T34.5 Verify GREEN** — run provider, workflow, Go, predecessor-byte, package, and projection matrices.
  - **T34.6 REFACTOR** — none unless candidate verification exposes duplicated contract material.
  - **T34.7 Verify Task** — run focused tests, package/graph/schema/projection checks, Markdown gates, and `scripts/verify.sh`; create the format-3 checkpoint commit.

#### T37: Verify the ADR 1.4 candidate

- **disposition:** active
- **outcome:** Review and qualify the merged adr@1.4 candidate for inclusion in v5.15.0 without redesigning its decision-boundary contract, altering immutable adr@1.3, or overwriting unrelated in-flight work.
- **work_type:** brownfield-behavior
- **checkpoint:** one green commit with the required ordered `Plan-*` checkpoint trailers
- **boundary:** internal
- **depends_on:** [T30]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T30 before this outcome
- **requirements:** [REQ-907]
- **proof:** [TC-T37-001]
- **source_refs:** [request, external:https://github.com/L3DigitalNet/project-standards/pull/120]
- **files:** [`standards/adr/standard.toml` (modify or create; owner T37)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** keep the task open, restore the verified GREEN checkpoint if refactoring regresses proof, and append correction work when the approved boundary must expand
- **acceptance:** TC-T37-001 proves adr@1.3 remains byte-identical and selectable; adr@1.4's declared resource digests and aggregate identity verify; its provider-input schema selects 1.4 and `run_migrate` preserves the requested version; the MADR section provider loads and reports findings; the example's stated exclusions match the boundary its Context and Problem Statement establishes; the deferred release-boundary items are inventoried and handed to T35 rather than advanced inside verification; package, graph, schema, projection, and Markdown checks pass; any correction stays within the candidate contract.
- **sub-tasks:**
  - **T37.0 CHARACTERIZE** — inventory the merged candidate, its PR review corrections, shared-file ownership, any surface the merge left unverified, and the exact deferred release-boundary items T35 must advance.
  - **T37.1 Verify Baseline** — confirm the candidate inventory matches the current repository and that immutable adr@1.3 bytes are unchanged.
  - **T37.2 RED** — prove adr@1.3 lacks the approved decision-boundary contract, and exercise candidate negative controls including a provider request whose declared version disagrees with the selected package.
  - **T37.3 Verify RED** — distinguish predecessor behavior and intentional negative controls from candidate defects.
  - **T37.4 GREEN** — preserve the merged candidate or apply only evidence-required corrections within its approved contract.
  - **T37.5 Verify GREEN** — run provider, payload-integrity, predecessor-byte, package, and projection matrices.
  - **T37.6 REFACTOR** — none unless candidate verification exposes duplicated contract material inside the successor.
  - **T37.7 Verify Task** — run focused tests, package/graph/schema/projection checks, Markdown gates, and `scripts/verify.sh`; create the format-3 checkpoint commit.

### Phase P2: Control-Plane Corrections

#### T11: Make successor drift actionable for #87

- **disposition:** active
- **outcome:** Explain drift and accept target rendering that exactly subsumes declared intent.
- **work_type:** behavior
- **checkpoint:** one green commit with the required ordered `Plan-*` checkpoint trailers
- **boundary:** internal
- **depends_on:** [T9]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T9 before this outcome
- **requirements:** [REQ-087]
- **proof:** [TC-T11-001]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#87]
- **files:** [`tests/control_plane/test_lifecycle.py` (modify or create; owner T11)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** keep the task open, restore the verified GREEN checkpoint if refactoring regresses proof, and append correction work when the approved boundary must expand
- **acceptance:** TC-T11-001 proves safe expected/observed/option evidence is present; equivalent successor intent needs no destructive temporary restore.
- **sub-tasks:**
  - **T11.1 RED** — reproduce opaque diagnostics and two-phase workaround.
  - **T11.2 Verify RED** — confirm old-lock drift blocks semantic equivalence.
  - **T11.3 GREEN** — enrich findings and add fail-closed equivalence planning.
  - **T11.4 Verify GREEN** — run drift/redaction/malicious-target tests.
  - **T11.5 REFACTOR** — separate evidence from authorization.
  - **T11.6 Verify Task** — tests, schema checks, Ruff, BasedPyright, `scripts/verify.sh`; create the format-3 checkpoint commit.

#### T12: Validate Frontmatter IDs before retirement for #98

- **disposition:** active
- **outcome:** Make migration predict complete selected-package validation.
- **work_type:** behavior
- **checkpoint:** one green commit with the required ordered `Plan-*` checkpoint trailers
- **boundary:** internal
- **depends_on:** [T10]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T10 before this outcome
- **requirements:** [REQ-098]
- **proof:** [TC-T12-001]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#98]
- **files:** [`tests/control_plane/test_migration.py` (modify or create; owner T12)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** keep the task open, restore the verified GREEN checkpoint if refactoring regresses proof, and append correction work when the approved boundary must expand
- **acceptance:** TC-T12-001 proves invalid IDs block before lock publication with reviewed repair guidance and no implicit document changes.
- **sub-tasks:**
  - **T12.1 RED** — add the legacy-ID false-success fixture.
  - **T12.2 Verify RED** — confirm `validate-id` fails after successful migration.
  - **T12.3 GREEN** — invoke complete selected-provider validation before retirement.
  - **T12.4 Verify GREEN** — run valid/invalid/referenced/no-write matrices.
  - **T12.5 REFACTOR** — expose one selected-package verification seam.
  - **T12.6 Verify Task** — migration/frontmatter tests and `scripts/verify.sh`; create the format-3 checkpoint commit.

#### T13: Coalesce TOML creates for #105

- **disposition:** active
- **outcome:** Render shared missing/empty inline parents atomically without duplicate keys.
- **work_type:** behavior
- **checkpoint:** one green commit with the required ordered `Plan-*` checkpoint trailers
- **boundary:** internal
- **depends_on:** [T9]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T9 before this outcome
- **requirements:** [REQ-105]
- **proof:** [TC-T13-001]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#105]
- **files:** [`src/project_standards/control_plane/adapters/toml.py` (modify or create; owner T13)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** keep the task open, restore the verified GREEN checkpoint if refactoring regresses proof, and append correction work when the approved boundary must expand
- **acceptance:** TC-T13-001 proves flat/nested, empty/nonempty, and ordering permutations yield valid TOML and preserve consumer values.
- **sub-tasks:**
  - **T13.1 RED** — add shared-parent CREATE permutations.
  - **T13.2 Verify RED** — confirm invalid or duplicate output.
  - **T13.3 GREEN** — coalesce inserts per inline-container locus.
  - **T13.4 Verify GREEN** — run adapter/planner batch matrices.
  - **T13.5 REFACTOR** — isolate coalescing from single-edit rendering.
  - **T13.6 Verify Task** — TOML/control-plane tests and `scripts/verify.sh`; create the format-3 checkpoint commit.

#### T14: Normalize JSONC deletion residue for #106

- **disposition:** active
- **outcome:** Remove newly empty lines/containers while preserving comments, CRLF, and surviving bytes.
- **work_type:** behavior
- **checkpoint:** one green commit with the required ordered `Plan-*` checkpoint trailers
- **boundary:** internal
- **depends_on:** [T9]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T9 before this outcome
- **requirements:** [REQ-106]
- **proof:** [TC-T14-001]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#106]
- **files:** [`src/project_standards/control_plane/adapters/jsonc.py` (modify or create; owner T14)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** keep the task open, restore the verified GREEN checkpoint if refactoring regresses proof, and append correction work when the approved boundary must expand
- **acceptance:** TC-T14-001 proves sole-member, comma-leading, comma-own-line, LF/CRLF, and comment-adjacent layouts converge safely.
- **sub-tasks:**
  - **T14.1 RED** — add the complete residue layout matrix.
  - **T14.2 Verify RED** — confirm residue rather than semantic corruption.
  - **T14.3 GREEN** — recompute spans after separator deletion and collapse proven-safe spans.
  - **T14.4 Verify GREEN** — run removal/byte/parse tests.
  - **T14.5 REFACTOR** — centralize post-deletion whitespace analysis.
  - **T14.6 Verify Task** — JSONC/control-plane tests and `scripts/verify.sh`; create the format-3 checkpoint commit.

#### T15: Superseded control-plane qualifier

- **disposition:** superseded
- **outcome:** Preserve the retired intermediate control-plane release boundary.
- **work_type:** verification
- **checkpoint:** historical non-executable boundary retained by the format-3 migration
- **boundary:** internal
- **depends_on:** [T9, T10, T11, T12, T13, T14, T23]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T9, T10, T11, T12, T13, T14, T23 before this outcome
- **requirements:** []
- **proof:** []
- **source_refs:** [request]
- **files:** [`docs/plans/2026-08-01-open-issue-resolution-program-plan.md` (historical; owner T15)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** [T35]
- **evidence:** []
- **recovery:** not executable; T35 owns correction and recovery
- **acceptance:** the task remains non-executable and T35 owns its replacement acceptance

### Phase P3: Python Tooling Corrections

#### T17: Fix Python import precedence for #89

- **disposition:** active
- **outcome:** Resolve managed `src` code as first-party typed source.
- **work_type:** behavior
- **checkpoint:** one green commit with the required ordered `Plan-*` checkpoint trailers
- **boundary:** internal
- **depends_on:** [T9, T10, T11, T12, T13, T14]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T9, T10, T11, T12, T13, T14 before this outcome
- **requirements:** [REQ-089]
- **proof:** [TC-T17-001]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#89]
- **files:** [`standards/python-tooling/standard.toml` (modify or create; owner T17)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** keep the task open, restore the verified GREEN checkpoint if refactoring regresses proof, and append correction work when the approved boundary must expand
- **acceptance:** TC-T17-001 proves strict tests do not resolve an untyped editable install first; other layouts remain compatible.
- **sub-tasks:**
  - **T17.1 RED** — add editable src-layout missing-stub fixture.
  - **T17.2 Verify RED** — capture wrong resolution ordering.
  - **T17.3 GREEN** — implement approved path/marker contract.
  - **T17.4 Verify GREEN** — run src/flat/marker/additional-root matrix.
  - **T17.5 REFACTOR** — derive import roots once.
  - **T17.6 Verify Task** — package/real BasedPyright tests and `scripts/verify.sh`; create the format-3 checkpoint commit.

#### T18: Bound Ruff scope for #95

- **disposition:** active
- **outcome:** Select only declared first-party source/test roots.
- **work_type:** behavior
- **checkpoint:** one green commit with the required ordered `Plan-*` checkpoint trailers
- **boundary:** internal
- **depends_on:** [T9, T10, T11, T12, T13, T14]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T9, T10, T11, T12, T13, T14 before this outcome
- **requirements:** [REQ-095]
- **proof:** [TC-T18-001]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#95]
- **files:** [`standards/python-tooling/versions/1.11/resources/check.py` (modify or create; owner T18)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** keep the task open, restore the verified GREEN checkpoint if refactoring regresses proof, and append correction work when the approved boundary must expand
- **acceptance:** TC-T18-001 proves nested projects and undeclared scripts remain untouched; every declared root is covered.
- **sub-tasks:**
  - **T18.1 RED** — add declared/nested/unrelated corpus.
  - **T18.2 Verify RED** — confirm dot reaches out-of-bound files.
  - **T18.3 GREEN** — derive deterministic Ruff arguments.
  - **T18.4 Verify GREEN** — run real Ruff selection tests.
  - **T18.5 REFACTOR** — share normalized roots where contracts coincide.
  - **T18.6 Verify Task** — package/real-tool tests and `scripts/verify.sh`; create the format-3 checkpoint commit.

#### T20: Add a no-implicit-root layout for #86

- **disposition:** active
- **outcome:** Support explicit roots without forcing `src` or `.` and reject empty unsuitable configurations.
- **work_type:** behavior
- **checkpoint:** one green commit with the required ordered `Plan-*` checkpoint trailers
- **boundary:** internal
- **depends_on:** [T17, T18]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T17, T18 before this outcome
- **requirements:** [REQ-086]
- **proof:** [TC-T20-001]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#86]
- **files:** [`tests/package_contract/test_python_tooling.py` (modify or create; owner T20)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** keep the task open, restore the verified GREEN checkpoint if refactoring regresses proof, and append correction work when the approved boundary must expand
- **acceptance:** TC-T20-001 proves explicit-root consumers get a bounded gate; src/flat predecessors remain unchanged.
- **sub-tasks:**
  - **T20.1 RED** — add mixed-monorepo and unsuitable-default fixtures.
  - **T20.2 Verify RED** — prove forced missing/widened roots.
  - **T20.3 GREEN** — add approved no-implicit-root mode.
  - **T20.4 Verify GREEN** — run fresh/migration/empty/predecessor matrices.
  - **T20.5 REFACTOR** — use one normalized root model.
  - **T20.6 Verify Task** — package/real-tool tests and `scripts/verify.sh`; create the format-3 checkpoint commit.

#### T21: Superseded tooling qualifier

- **disposition:** superseded
- **outcome:** Preserve the retired six-issue tooling release boundary.
- **work_type:** verification
- **checkpoint:** historical non-executable boundary retained by the format-3 migration
- **boundary:** internal
- **depends_on:** [T16, T17, T18, T19, T20, T31, T33]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T16, T17, T18, T19, T20, T31, T33 before this outcome
- **requirements:** []
- **proof:** []
- **source_refs:** [request]
- **files:** [`docs/plans/2026-08-01-open-issue-resolution-program-plan.md` (historical; owner T21)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** [T36]
- **evidence:** []
- **recovery:** not executable; T36 owns correction and recovery
- **acceptance:** the task remains non-executable and T36 owns its replacement acceptance

#### T31: Correct the Python Tooling successor's authority statement

- **disposition:** active
- **outcome:** Make the already-planned compatible Python Tooling successor state the current V5 package/control-plane authority without altering immutable 1.10.
- **work_type:** behavior
- **checkpoint:** one green commit with the required ordered `Plan-*` checkpoint trailers
- **boundary:** internal
- **depends_on:** [T20, T30]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T20, T30 before this outcome
- **requirements:** [REQ-903]
- **proof:** [TC-T31-001]
- **source_refs:** [request]
- **files:** [`standards/python-tooling/versions/1.11/README.md` (modify or create; owner T31)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** keep the task open, restore the verified GREEN checkpoint if refactoring regresses proof, and append correction work when the approved boundary must expand
- **acceptance:** TC-T31-001 proves Python Tooling 1.10 remains byte-identical; its planned successor contains no claim that the V1 root manifest is current authority, consistently identifies the selected V5 package/control plane as authoritative, and is activated and qualified by T35 rather than a separate release train.
- **sub-tasks:**
  - **T31.1 RED** — add a successor contract test that rejects the stale V1-authority statement and requires the current V5 authority statement.
  - **T31.2 Verify RED** — confirm the planned successor still carries the copied 1.10 contradiction.
  - **T31.3 GREEN** — make the smallest content correction across the successor surfaces that state package authority.
  - **T31.4 Verify GREEN** — run the focused successor contract and predecessor-byte checks.
  - **T31.5 REFACTOR** — remove duplicate wording only within the successor when byte-lock contracts permit it.
  - **T31.6 Verify Task** — run Python Tooling package tests, package/graph/schema/projection checks, and `scripts/verify.sh`; create the format-3 checkpoint commit.

#### T33: Guard Python Tooling fresh adoption for #109

- **disposition:** active
- **outcome:** Reject fresh adoption before any write when Python Tooling would create `pyproject.toml` without consumer-owned PEP 621 project metadata.
- **work_type:** behavior
- **checkpoint:** one green commit with the required ordered `Plan-*` checkpoint trailers
- **boundary:** internal
- **depends_on:** [T20, T31]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T20, T31 before this outcome
- **requirements:** [REQ-109]
- **proof:** [TC-T33-001]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#109]
- **files:** [`standards/python-tooling/versions/1.11/providers/python_tooling.py` (modify or create; owner T33)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** keep the task open, restore the verified GREEN checkpoint if refactoring regresses proof, and append correction work when the approved boundary must expand
- **acceptance:** TC-T33-001 proves an absent `pyproject.toml` or missing `[project]` table produces an actionable no-write finding that names the required consumer decision and installable/non-installable routes; existing valid `[project]` metadata is preserved; the documented apply → `uv lock` flow succeeds with the lock-resolved uv version; Python Tooling 1.10 remains byte-identical.
- **sub-tasks:**
  - **T33.1 RED** — add fresh installable and non-installable fixtures that currently reconcile a tool-only `pyproject.toml` and fail `uv lock`.
  - **T33.2 Verify RED** — confirm the failure is missing consumer-owned `[project]` metadata rather than dependency or backend resolution.
  - **T33.3 GREEN** — add the smallest fail-before-write provider/preflight finding and guided adoption documentation without generating project identity.
  - **T33.4 Verify GREEN** — prove invalid fresh adoption writes nothing and valid consumer-authored metadata reaches a successful real `uv lock`.
  - **T33.5 REFACTOR** — share metadata-presence checks only within the successor boundary; do not add project-identity inference.
  - **T33.6 Verify Task** — run Python Tooling package/real-uv tests, predecessor-byte checks, package contracts, and `scripts/verify.sh`; create the format-3 checkpoint commit.

### Phase P4: v5.15.0 Qualification and Publication

#### T35: Qualify and publish v5.15.0

- **disposition:** active
- **outcome:** Publish the owner-approved combined v5.15.0 release and close or disposition its twelve selected issues.
- **work_type:** operational
- **checkpoint:** one green commit containing EV-007 and the required ordered `Plan-*` trailers
- **boundary:** deployment
- **depends_on:** [T9, T10, T11, T12, T13, T14, T17, T18, T20, T23, T31, T33, T34, T37]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T9, T10, T11, T12, T13, T14, T17, T18, T20, T23, T31, T33, T34, T37 before this outcome
- **requirements:** [REQ-900, REQ-905, REQ-906]
- **proof:** [TC-T35-001]
- **source_refs:** [request]
- **consumes:** [approved task inputs, exact repository and external state at authorization]
- **produces:** [t35 verified operational result]
- **preserves:** [immutable history, predecessor bytes, unrelated work, and action-specific authorization]
- **invariants:** [no external effect before authorization; failed proof cannot be reported as success]
- **executor_discretion:** [bounded evidence-capture mechanics and repository-conforming private helpers]
- **files:** [`docs/research/2026-08-01-v5-15-release-evidence.md` (modify or create; owner T35)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** [T15]
- **superseded_by:** []
- **evidence:** [EV-007]
- **recovery:** stop at the last verified boundary, do not repeat an unproven external effect, retain durable evidence, and use the task-specific no-op or recovery proof
- **acceptance:** TC-T35-001 proves prior-release reproductions fail for the expected reasons; every selected correction and accepted #84 disposition passes source, candidate-wheel, installed, migration, adapter, real-tool, and predecessor-byte proofs; CLI Documentation 1.6 and the Python Tooling successor are advertised without altering predecessors; full local and hosted gates pass; signed tags and byte-verified assets are published only after authorization; issues #76, #77, #83, #84, #86, #87, #89, #95, #98, #105, #106, and #109 close or receive the accepted disposition.
- **sub-tasks:**
  - **T35.1 AUTHORIZATION** — obtain current action-and-target-specific approval for every external write, publication, merge, or closure.
  - **T35.2 PREFLIGHT** — confirm exact targets, branch/release state, prerequisites, rollback boundary, and clean attributable scope.
  - **T35.3 APPLY** — perform only the authorized operational changes in the declared order.
  - **T35.4 VERIFY** — verify remote/installed/issue state and repository truth from independent observations.
  - **T35.5 PROVE NO-OP OR RECOVERY** — prove repeat convergence or the declared recovery path without rewriting immutable history.
  - **T35.6 CAPTURE EVIDENCE** — run TC-T35-001; commit sanitized durable evidence and the format-3 checkpoint.

### Phase P5: Agent Handoff Authority and MCP Documentation

#### T2: Correct enrichment pairing for #75

- **disposition:** active
- **outcome:** Attach engine coordinates only to the matching provider rule.
- **work_type:** behavior
- **checkpoint:** one green commit with the required ordered `Plan-*` checkpoint trailers
- **boundary:** internal
- **depends_on:** [T1, T35]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T1, T35 before this outcome
- **requirements:** [REQ-075]
- **proof:** [TC-T2-001]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#75]
- **files:** [`src/project_standards/agent_handoff/cli.py` (modify or create; owner T2)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** keep the task open, restore the verified GREEN checkpoint if refactoring regresses proof, and append correction work when the approved boundary must expand
- **acceptance:** TC-T2-001 proves mixed forbidden/overlong paragraph findings keep correct rule, line, observed value, and limit regardless of order.
- **sub-tasks:**
  - **T2.1 RED** — add the mixed multi-paragraph FIFO-mispair fixture.
  - **T2.2 Verify RED** — confirm semantic misattribution.
  - **T2.3 GREEN** — match enrichment by rule identity and compatible measurement.
  - **T2.4 Verify GREEN** — run focused and full Agent Handoff tests.
  - **T2.5 REFACTOR** — centralize rule identity if useful.
  - **T2.6 Verify Task** — targeted tests, Ruff, BasedPyright, `scripts/verify.sh`; create the format-3 checkpoint commit.

#### T3: Make legacy inventory lock-aware for #90

- **disposition:** active
- **outcome:** Suppress legacy signatures authenticated as current by the applied lock.
- **work_type:** behavior
- **checkpoint:** one green commit with the required ordered `Plan-*` checkpoint trailers
- **boundary:** internal
- **depends_on:** [T1, T35]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T1, T35 before this outcome
- **requirements:** [REQ-090]
- **proof:** [TC-T3-001]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#90]
- **files:** [`src/project_standards/agent_handoff/legacy.py` (modify or create; owner T3)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** keep the task open, restore the verified GREEN checkpoint if refactoring regresses proof, and append correction work when the approved boundary must expand
- **acceptance:** TC-T3-001 proves managed hook/registration evidence is clean while unowned duplicates remain visible.
- **sub-tasks:**
  - **T3.1 RED** — reproduce locked-current false positives.
  - **T3.2 Verify RED** — confirm exact current signatures are misclassified.
  - **T3.3 GREEN** — add bounded lock-provenance authentication.
  - **T3.4 Verify GREEN** — run legacy and adversarial duplicate tests.
  - **T3.5 REFACTOR** — separate signature detection from provenance.
  - **T3.6 Verify Task** — targeted tests, Ruff, BasedPyright, `scripts/verify.sh`; create the format-3 checkpoint commit.

#### T4: Route read-only commands through locked payloads for #91

- **disposition:** active
- **outcome:** Use the applied payload before catalog refresh.
- **work_type:** behavior
- **checkpoint:** one green commit with the required ordered `Plan-*` checkpoint trailers
- **boundary:** internal
- **depends_on:** [T3]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T3 before this outcome
- **requirements:** [REQ-091]
- **proof:** [TC-T4-001]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#91]
- **files:** [`tests/agent_handoff/test_selected_routing.py` (modify or create; owner T4)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** keep the task open, restore the verified GREEN checkpoint if refactoring regresses proof, and append correction work when the approved boundary must expand
- **acceptance:** TC-T4-001 proves older V5 fixtures run `legacy-report` before reconciliation without mutation and disclose the locked basis.
- **sub-tasks:**
  - **T4.1 RED** — reproduce `selected command package is not reconciled`.
  - **T4.2 Verify RED** — confirm ordinary preview remains applicable.
  - **T4.3 GREEN** — resolve read authority from authenticated lock facts.
  - **T4.4 Verify GREEN** — run routing, tampered-lock, and missing-payload tests.
  - **T4.5 REFACTOR** — expose one read-authority resolver.
  - **T4.6 Verify Task** — targeted tests, Ruff, BasedPyright, `scripts/verify.sh`; create the format-3 checkpoint commit.

#### T5: Restore the pre-apply report checkpoint for #101

- **disposition:** active
- **outcome:** Make size/shape reports usable before apply or deliberately redefine the workflow.
- **work_type:** behavior
- **checkpoint:** one green commit with the required ordered `Plan-*` checkpoint trailers
- **boundary:** internal
- **depends_on:** [T4]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T4 before this outcome
- **requirements:** [REQ-101]
- **proof:** [TC-T5-001]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#101]
- **files:** [`UPGRADING.md` (modify or create; owner T5), `src/project_standards/control_plane/command_resolution.py` (modify or create; owner T5), `tests/agent_handoff/test_selected_routing.py` (modify or create; owner T4)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** keep the task open, restore the verified GREEN checkpoint if refactoring regresses proof, and append correction work when the approved boundary must expand
- **acceptance:** TC-T5-001 proves the documented checkpoint provides equivalent pre-write safety and an accurate diagnostic.
- **sub-tasks:**
  - **T5.1 RED** — reproduce enabled-but-unlocked refusal.
  - **T5.2 Verify RED** — confirm the state is normal and unmutated.
  - **T5.3 GREEN** — implement the approved desired-state report or workflow correction.
  - **T5.4 Verify GREEN** — run pre/post-apply reports and doc parity checks.
  - **T5.5 REFACTOR** — reuse T4 authority resolution where valid.
  - **T5.6 Verify Task** — targeted tests, documentation gates, `scripts/verify.sh`; create the format-3 checkpoint commit.

#### T6: Detect duplicate startup injection for #102

- **disposition:** active
- **outcome:** Block or report legacy SessionStart handlers that remain live beside managed handlers.
- **work_type:** behavior
- **checkpoint:** one green commit with the required ordered `Plan-*` checkpoint trailers
- **boundary:** internal
- **depends_on:** [T3]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T3 before this outcome
- **requirements:** [REQ-102]
- **proof:** [TC-T6-001]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#102]
- **files:** [`tests/agent_handoff/test_reconcile.py` (modify or create; owner T6)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** keep the task open, restore the verified GREEN checkpoint if refactoring regresses proof, and append correction work when the approved boundary must expand
- **acceptance:** TC-T6-001 proves matcher-less and differently matched legacy groups cannot yield a green double injection.
- **sub-tasks:**
  - **T6.1 RED** — reproduce both harness double-injection shapes.
  - **T6.2 Verify RED** — confirm reconcile/validate/drift are falsely green.
  - **T6.3 GREEN** — add shared semantic overlap detection.
  - **T6.4 Verify GREEN** — prove unrelated handlers remain consumer-owned.
  - **T6.5 REFACTOR** — centralize overlap semantics.
  - **T6.6 Verify Task** — targeted tests, Ruff, BasedPyright, `scripts/verify.sh`; create the format-3 checkpoint commit.

#### T7: Align secret-reference policy for #107

- **disposition:** active
- **outcome:** Apply the owner-selected uppercase-reference policy in engine and provider.
- **work_type:** behavior
- **checkpoint:** one green commit with the required ordered `Plan-*` checkpoint trailers
- **boundary:** internal
- **depends_on:** [T1, T35]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T1, T35 before this outcome
- **requirements:** [REQ-107]
- **proof:** [TC-T7-001]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#107]
- **files:** [`src/project_standards/agent_handoff/policy.py` (modify or create; owner T7)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** keep the task open, restore the verified GREEN checkpoint if refactoring regresses proof, and append correction work when the approved boundary must expand
- **acceptance:** TC-T7-001 proves env-reference and command-substitution cases produce identical safe findings; compatibility impact is documented.
- **sub-tasks:**
  - **T7.1 RED** — freeze the divergence matrix and owner decision.
  - **T7.2 Verify RED** — confirm only the named cases diverge.
  - **T7.3 GREEN** — implement the selected policy in engine/successor.
  - **T7.4 Verify GREEN** — run parity, redaction, and predecessor tests.
  - **T7.5 REFACTOR** — share data only without blurring authority.
  - **T7.6 Verify Task** — targeted/package tests and `scripts/verify.sh`; create the format-3 checkpoint commit.

#### T8: Qualify the Agent Handoff authority train

- **disposition:** active
- **outcome:** Publish T2–T7 in one release and close their issues.
- **work_type:** operational
- **checkpoint:** one green commit containing EV-002 and the required ordered `Plan-*` trailers
- **boundary:** deployment
- **depends_on:** [T2, T3, T4, T5, T6, T7]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T2, T3, T4, T5, T6, T7 before this outcome
- **requirements:** [REQ-900]
- **proof:** [TC-T8-001]
- **source_refs:** [request]
- **consumes:** [approved task inputs, exact repository and external state at authorization]
- **produces:** [t8 verified operational result]
- **preserves:** [immutable history, predecessor bytes, unrelated work, and action-specific authorization]
- **invariants:** [no external effect before authorization; failed proof cannot be reported as success]
- **executor_discretion:** [bounded evidence-capture mechanics and repository-conforming private helpers]
- **files:** [`docs/research/2026-08-01-agent-handoff-authority-release-evidence.md` (modify or create; owner T8)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [EV-002]
- **recovery:** stop at the last verified boundary, do not repeat an unproven release or issue effect, retain EV-002, and prove no-op convergence or successor recovery
- **acceptance:** TC-T8-001 proves predecessor bytes, candidate parity, full gate, hosted checks, assets, recovery decision, and six closures verify.
- **sub-tasks:**
  - **T8.1 AUTHORIZATION** — obtain exact release, issue-write, tag, asset, and publication authorization.
  - **T8.2 PREFLIGHT** — anchor the candidate, predecessor bytes, hosted prerequisites, recovery boundary, and EV-002 destination.
  - **T8.3 APPLY** — perform only the authorized Agent Handoff release and issue-closure effects.
  - **T8.4 VERIFY** — verify candidate, installed wheel, hosted checks, assets, and issue state independently.
  - **T8.5 PROVE NO-OP OR RECOVERY** — prove repeat convergence or prepare a fully qualified successor without rewriting history.
  - **T8.6 CAPTURE EVIDENCE** — run TC-T8-001; commit EV-002 and the format-3 checkpoint.

#### T22: Correct MCP release docs for #108

- **disposition:** active
- **outcome:** Lead current/future MCP docs with exact-release installation without rewriting v5.12.0.
- **work_type:** documentation
- **checkpoint:** one green commit with the required ordered `Plan-*` checkpoint trailers
- **boundary:** internal
- **depends_on:** [T1]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T1 before this outcome
- **requirements:** [REQ-108]
- **proof:** [TC-T22-001]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#108]
- **files:** [`docs/mcp-server.md` (modify or create; owner T22)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** restore the last green document checkpoint when references or owner truth fail; do not weaken the approved contract
- **acceptance:** TC-T22-001 proves candidate instructions are development-only and future releases cannot ship candidate-as-current prose.
- **sub-tasks:**
  - **T22.1 INVENTORY** — identify canonical owner truth, stale active claims, and exact references.
  - **T22.2 UPDATE** — make the bounded approved documentation or specification change.
  - **T22.3 VERIFY REFERENCES** — verify paths, commands, anchors, lifecycle truth, and applicable document tooling.
  - **T22.4 Verify Task** — run TC-T22-001; create the format-3 checkpoint commit.

### Phase P6: Deferred Tooling Successors

#### T16: Bound Markdown formatting scope for #88

- **disposition:** active
- **outcome:** Make local/workflow Prettier commands select only configured Markdown/structured text.
- **work_type:** behavior
- **checkpoint:** one green commit with the required ordered `Plan-*` checkpoint trailers
- **boundary:** internal
- **depends_on:** [T35]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T35 before this outcome
- **requirements:** [REQ-088]
- **proof:** [TC-T16-001]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#88]
- **files:** [`standards/markdown-tooling/standard.toml` (modify or create; owner T16)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** keep the task open, restore the verified GREEN checkpoint if refactoring regresses proof, and append correction work when the approved boundary must expand
- **acceptance:** TC-T16-001 proves languages and ignored scratch outside configured globs are never traversed.
- **sub-tasks:**
  - **T16.1 RED** — add mixed tracked/ignored corpus reproduction.
  - **T16.2 Verify RED** — confirm dot traversal exceeds scope.
  - **T16.3 GREEN** — render deterministic bounded invocation.
  - **T16.4 Verify GREEN** — run real Prettier set-parity tests.
  - **T16.5 REFACTOR** — share selection without new glob authority.
  - **T16.6 Verify Task** — package/real-tool tests and `scripts/verify.sh`; create the format-3 checkpoint commit.

#### T19: Preserve Ruff plugin configuration for #99

- **disposition:** active
- **outcome:** Keep undeclared plugin sub-tables consumer-owned or expose a bounded typed option.
- **work_type:** behavior
- **checkpoint:** one green commit with the required ordered `Plan-*` checkpoint trailers
- **boundary:** internal
- **depends_on:** [T35]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T35 before this outcome
- **requirements:** [REQ-099]
- **proof:** [TC-T19-001]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#99]
- **files:** [`standards/python-tooling/versions/1.12/config.schema.json` (modify or create; owner T19)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** keep the task open, restore the verified GREEN checkpoint if refactoring regresses proof, and append correction work when the approved boundary must expand
- **acceptance:** TC-T19-001 proves Typer's targeted B008 configuration reconciles without global suppression, source churn, or split-file workaround.
- **sub-tasks:**
  - **T19.1 RED** — reproduce table conflict and lint consequence.
  - **T19.2 Verify RED** — prove current options cannot express intent.
  - **T19.3 GREEN** — implement approved ownership/option contract.
  - **T19.4 Verify GREEN** — run plugin/governed-key/round-trip tests.
  - **T19.5 REFACTOR** — declare ownership once.
  - **T19.6 Verify Task** — package/control-plane tests and `scripts/verify.sh`; create the format-3 checkpoint commit.

#### T36: Qualify deferred tooling successors

- **disposition:** active
- **outcome:** Publish the post-v5.15.0 Markdown/Python Tooling successors for deferred issues #88 and #99.
- **work_type:** operational
- **checkpoint:** one green commit containing EV-008 and the required ordered `Plan-*` trailers
- **boundary:** deployment
- **depends_on:** [T16, T19]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T16, T19 before this outcome
- **requirements:** [REQ-900]
- **proof:** [TC-T36-001]
- **source_refs:** [request]
- **consumes:** [approved task inputs, exact repository and external state at authorization]
- **produces:** [t36 verified operational result]
- **preserves:** [immutable history, predecessor bytes, unrelated work, and action-specific authorization]
- **invariants:** [no external effect before authorization; failed proof cannot be reported as success]
- **executor_discretion:** [bounded evidence-capture mechanics and repository-conforming private helpers]
- **files:** [`docs/research/2026-08-01-deferred-tooling-release-evidence.md` (modify or create; owner T36)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** [T21]
- **superseded_by:** []
- **evidence:** [EV-008]
- **recovery:** stop at the last verified boundary, do not repeat an unproven external effect, retain durable evidence, and use the task-specific no-op or recovery proof
- **acceptance:** TC-T36-001 proves v5.15.0 and every predecessor remain byte-identical/selectable; the bounded Prettier corpus and Ruff plugin-ownership contracts pass source/candidate/installed proofs; full and hosted gates pass; publication and both closures follow explicit authorization.
- **sub-tasks:**
  - **T36.1 AUTHORIZATION** — obtain current action-and-target-specific approval for every external write, publication, merge, or closure.
  - **T36.2 PREFLIGHT** — confirm exact targets, branch/release state, prerequisites, rollback boundary, and clean attributable scope.
  - **T36.3 APPLY** — perform only the authorized operational changes in the declared order.
  - **T36.4 VERIFY** — verify remote/installed/issue state and repository truth from independent observations.
  - **T36.5 PROVE NO-OP OR RECOVERY** — prove repeat convergence or the declared recovery path without rewriting immutable history.
  - **T36.6 CAPTURE EVIDENCE** — run TC-T36-001; commit sanitized durable evidence and the format-3 checkpoint.

### Phase P7: Project Spec Conformance Feature

#### T24: Specify conformance linting for #62

- **disposition:** active
- **outcome:** Approve exact surfaces, phrasing policy, compatibility mode, and rollout.
- **work_type:** documentation
- **checkpoint:** one green commit with the required ordered `Plan-*` checkpoint trailers
- **boundary:** internal
- **depends_on:** [T36]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T36 before this outcome
- **requirements:** [REQ-062]
- **proof:** [TC-T24-001]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#62]
- **files:** [`docs/specs/2026-08-01-project-spec-conformance-plan-input.md` (modify or create; owner T24)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** restore the last green document checkpoint when references or owner truth fail; do not weaken the approved contract
- **acceptance:** TC-T24-001 proves byte-exact/structural/advisory checks and existing-consumer impact are explicit and reviewed.
- **sub-tasks:**
  - **T24.1 INVENTORY** — identify canonical owner truth, stale active claims, and exact references.
  - **T24.2 UPDATE** — make the bounded approved documentation or specification change.
  - **T24.3 VERIFY REFERENCES** — verify paths, commands, anchors, lifecycle truth, and applicable document tooling.
  - **T24.4 Verify Task** — run TC-T24-001; create the format-3 checkpoint commit.

#### T25: Implement conformance linting for #62

- **disposition:** active
- **outcome:** Execute the approved child plan and publish its behavior.
- **work_type:** operational
- **checkpoint:** one green commit containing EV-009 and the required ordered `Plan-*` trailers
- **boundary:** deployment
- **depends_on:** [T24]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T24 before this outcome
- **requirements:** [REQ-062]
- **proof:** [TC-T25-001]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#62]
- **consumes:** [approved #62 specification and child-plan checkpoints, exact release state, action-specific authorization]
- **produces:** [published conformance feature and issue disposition recorded in EV-009]
- **preserves:** [child-plan acceptance, predecessor behavior, immutable release history, and unrelated work]
- **invariants:** [the child plan completes before publication; no external effect occurs before authorization]
- **executor_discretion:** [release evidence capture and repository-conforming aggregation mechanics]
- **files:** [`docs/plans/2026-08-01-project-spec-conformance-plan.md` (modify or create; owner T25), `docs/research/2026-08-01-project-spec-conformance-release-evidence.md` (modify or create; owner T25)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [EV-009]
- **recovery:** stop at the last verified child-plan or release boundary, do not repeat an unproven publication, and qualify a successor rather than rewriting history
- **acceptance:** TC-T25-001 proves canonical/divergent/tailored/predecessor documents produce approved results and #62 closes after release.
- **sub-tasks:**
  - **T25.1 AUTHORIZATION** — obtain exact authorization to execute the approved child plan and publish/close #62 after its gates pass.
  - **T25.2 PREFLIGHT** — validate the child plan, branch, candidate inputs, publication target, rollback boundary, and EV-009 destination.
  - **T25.3 APPLY** — execute the child plan, then perform only the authorized release and issue effects.
  - **T25.4 VERIFY** — verify child completion, fresh candidate, full/hosted gates, assets, and issue state independently.
  - **T25.5 PROVE NO-OP OR RECOVERY** — prove repeat convergence or qualify a successor without rewriting published history.
  - **T25.6 CAPTURE EVIDENCE** — run TC-T25-001; commit EV-009 and the format-3 checkpoint.

### Phase P8: Project Spec Conversion Feature

#### T26: Specify house-format conversion for #55

- **disposition:** active
- **outcome:** Approve preservation, ambiguity, preview/apply, rollback, and semantic-review contracts.
- **work_type:** documentation
- **checkpoint:** one green commit with the required ordered `Plan-*` checkpoint trailers
- **boundary:** internal
- **depends_on:** [T25]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T25 before this outcome
- **requirements:** [REQ-055]
- **proof:** [TC-T26-001]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#55]
- **files:** [`docs/specs/2026-08-01-project-spec-conversion-plan-input.md` (modify or create; owner T26)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** restore the last green document checkpoint when references or owner truth fail; do not weaken the approved contract
- **acceptance:** TC-T26-001 proves unrecognized prose cannot be discarded; ambiguous choices remain explicit; rollback is defined; safe adoption for future canonical specs with an excluded/no-match legacy corpus remains supported and never forces conversion.
- **sub-tasks:**
  - **T26.1 INVENTORY** — identify canonical owner truth, stale active claims, and exact references.
  - **T26.2 UPDATE** — make the bounded approved documentation or specification change.
  - **T26.3 VERIFY REFERENCES** — verify paths, commands, anchors, lifecycle truth, and applicable document tooling.
  - **T26.4 Verify Task** — run TC-T26-001; create the format-3 checkpoint commit.

#### T27: Implement preservation-first conversion for #55

- **disposition:** active
- **outcome:** Execute the approved child plan, whose tasks own the behavior-change files, and publish the safe conversion surface.
- **work_type:** behavior
- **checkpoint:** one green commit with the required ordered `Plan-*` checkpoint trailers
- **boundary:** internal
- **depends_on:** [T26]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T26 before this outcome
- **requirements:** [REQ-055]
- **proof:** [TC-T27-001]
- **source_refs:** [request, issue:L3DigitalNet/project-standards#55]
- **files:** [`docs/plans/2026-08-01-project-spec-conversion-plan.md` (modify or create; owner T27)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** keep the task open, restore the verified GREEN checkpoint if refactoring regresses proof, and append correction work when the approved boundary must expand
- **acceptance:** TC-T27-001 proves conversion is explicit and opt-in; recognized structure maps deterministically; unmapped content stays intact/review-visible; apply is guarded; new-spec-only/no-match consumers retain their existing successful behavior.
- **sub-tasks:**
  - **T27.1 RED** — execute preservation/ambiguity regressions.
  - **T27.2 Verify RED** — confirm missing behavior, never fixture loss.
  - **T27.3 GREEN** — execute the child plan's minimal preview/guarded apply implementation within its declared file ownership.
  - **T27.4 Verify GREEN** — run property/integration/round-trip/rollback suites.
  - **T27.5 REFACTOR** — do not add heuristic rewriting.
  - **T27.6 Verify Task** — child completion, semantic audit, fresh candidate/full gate; create the format-3 checkpoint commit.

#### T28: Qualify the feature release

- **disposition:** active
- **outcome:** Publish #55 without regressing #62 or correction trains.
- **work_type:** operational
- **checkpoint:** one green commit containing EV-004 and the required ordered `Plan-*` trailers
- **boundary:** deployment
- **depends_on:** [T27]
- **dependency_reason:** ordering-only: preserve the approved prerequisite order T27 before this outcome
- **requirements:** [REQ-900]
- **proof:** [TC-T28-001]
- **source_refs:** [request]
- **consumes:** [approved task inputs, exact repository and external state at authorization]
- **produces:** [t28 verified operational result]
- **preserves:** [immutable history, predecessor bytes, unrelated work, and action-specific authorization]
- **invariants:** [no external effect before authorization; failed proof cannot be reported as success]
- **executor_discretion:** [bounded evidence-capture mechanics and repository-conforming private helpers]
- **files:** [`docs/research/2026-08-01-project-spec-feature-release-evidence.md` (modify or create; owner T28)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [EV-004]
- **recovery:** stop at the last verified boundary, do not repeat an unproven release or issue effect, retain EV-004, and qualify a successor rather than rewriting history
- **acceptance:** TC-T28-001 proves source/candidate/installed parity, migration safety, hosted checks, assets, recovery decision, and #55 closure verify.
- **sub-tasks:**
  - **T28.1 AUTHORIZATION** — obtain exact release, issue-write, tag, asset, and publication authorization.
  - **T28.2 PREFLIGHT** — anchor T27, candidate inputs, hosted prerequisites, recovery boundary, and EV-004 destination.
  - **T28.3 APPLY** — perform only the authorized feature release and issue-closure effects.
  - **T28.4 VERIFY** — verify source/candidate/installed parity, migration safety, hosted checks, assets, and issue state.
  - **T28.5 PROVE NO-OP OR RECOVERY** — prove repeat convergence or qualify a successor without rewriting history.
  - **T28.6 CAPTURE EVIDENCE** — run TC-T28-001; commit EV-004 and the format-3 checkpoint.

### Phase P9: Program Reconciliation and Close-out

#### T29: Reconcile the tracker and close the program

- **disposition:** active
- **outcome:** Account for every frozen issue, harvest durable outcomes, and retire active state.
- **work_type:** operational
- **checkpoint:** one green commit containing EV-005 and the required ordered `Plan-*` trailers
- **boundary:** operational
- **depends_on:** [T8, T22, T23, T24, T25, T26, T27, T28, T32]
- **dependency_reason:** ordering-only: closeout follows every frozen-issue release/disposition train, MCP documentation, PyYAML disposition, feature train, and consumer retirement
- **requirements:** [REQ-901]
- **proof:** [TC-T29-001]
- **source_refs:** [request]
- **consumes:** [approved task inputs, exact repository and external state at authorization]
- **produces:** [t29 verified operational result]
- **preserves:** [immutable history, predecessor bytes, unrelated work, and action-specific authorization]
- **invariants:** [no external effect before authorization; failed proof cannot be reported as success]
- **executor_discretion:** [bounded evidence-capture mechanics and repository-conforming private helpers]
- **files:** [`docs/research/2026-08-01-open-issue-program-closeout-evidence.md` (modify or create; owner T29)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [EV-005]
- **recovery:** stop at the last verified boundary, do not repeat an unproven external effect, retain durable evidence, and use the task-specific no-op or recovery proof
- **acceptance:** TC-T29-001 proves all 24 issues are closed or explicitly accepted; docs/releases/ledger agree; scratch is harvested and removed.
- **sub-tasks:**
  - **T29.1 AUTHORIZATION** — obtain current action-and-target-specific approval for every external write, publication, merge, or closure.
  - **T29.2 PREFLIGHT** — confirm exact targets, branch/release state, prerequisites, rollback boundary, and clean attributable scope.
  - **T29.3 APPLY** — perform only the authorized operational changes in the declared order.
  - **T29.4 VERIFY** — verify remote/installed/issue state and repository truth from independent observations.
  - **T29.5 PROVE NO-OP OR RECOVERY** — prove repeat convergence or the declared recovery path without rewriting immutable history.
  - **T29.6 CAPTURE EVIDENCE** — run TC-T29-001; commit sanitized durable evidence and the format-3 checkpoint.

## 10. Integration, Migration, and Recovery

### 10.1 Integration Sequence and Gates

1. Replay T30 and T1 under format-3 evidence/checkpoint identity; independently run T9, T10, T23, T32, and T34 when dependency-ready.
2. Complete T9–T14, then T17/T18, T20, T31, and T33.
3. Qualify and publish only the approved v5.15.0 aggregate in T35.
4. Complete Agent Handoff authority/MCP documentation and deferred tooling successors.
5. Complete separately approved Project Spec feature trains, then reconcile the program in T29.

### 10.2 Migration and Compatibility

- Legacy scratch remains at the work-item root for historical inspection; new state is generated under `execution/`.
- No legacy status is copied into format-3 state. T30 and T1 proofs are replayed and receive new identity-bearing checkpoints.
- Package changes remain successor-only; old and new versions coexist through catalog selection.
- A failed unpublished candidate is corrected and fully requalified. A post-publication defect receives a new successor; tags, assets, and advertised payloads are never replaced or deleted.
- Repeated operational actions must prove no-op convergence or stop for bounded recovery.

### 10.3 Rollout / Operational Authorization

T1, T8, T25, T28–T29, T32, and T35–T36 stop at AUTHORIZATION until the user approves the exact issue writes, publication, protected merge, push, tag, release, or closeout effect. Plan approval and generic continuation do not satisfy this gate.

### 10.4 Late Failure and Correction Loop

A task-level failure stays within the open task when its approved outcome is unchanged. A failure discovered after a checkpoint appends a correction task and reruns the blocked verifier. A changed requirement, release boundary, or acceptance target pauses execution and returns to plan-authoring revision.

## 11. Risks, Assumptions, and Open Questions

### 11.1 Risks

| ID | Risk | Likelihood | Impact | Treatment / Contingency | Owner / Task |
| --- | --- | --- | --- | --- | --- |
| R-001 | The combined v5.15.0 train becomes unreviewable. | medium | high | keep issue-local proofs and aggregate only after every owning checkpoint | T35 |
| R-002 | Predecessor bytes or published history drift. | low | high | successor-only edits, byte gates, and no rewrite recovery | T8, T28, T35–T36 |
| R-003 | Legacy evidence is mistaken for format-3 completion. | medium | high | isolate layouts and replay T30/T1 with required trailers | T1, T30 |
| R-004 | Adapter cleanup damages consumer-owned bytes. | medium | high | layout/property matrices and byte-preservation controls | T13, T14 |
| R-005 | External issues/releases/merges change without exact approval. | low | high | operational AUTHORIZATION stages and durable receipts | T1, T8, T25, T28–T29, T32, T35–T36 |
| R-006 | Deferred #88/#99 changes leak into v5.15.0. | medium | high | keep T16/T19 behind T35 and reject unexpected release content | T35, T36 |
| R-007 | A late failure is fixed inside verification and escapes task proof. | medium | high | append correction work and rerun from ANCHOR | verification tasks |

### 11.2 Assumptions

| ID | Assumption | Impact if False |
| --- | --- | --- |
| A-001 | No existing commit carries a complete matching format-3 checkpoint for this plan identity. | use `recover` instead of `generate` if a valid matching checkpoint is discovered |
| A-002 | The frozen issue outcomes and owner decisions preserved from the approved legacy master remain current. | pause affected tasks and obtain an owner-approved revision |
| A-003 | One serialized executor owns the complete plan. | stop execution until competing ownership is reconciled |

### 11.3 Open Questions

None.

## 12. Final Verification

- Every Must/Should requirement maps to a terminal owning task and passing Appendix B proof.
- Every active task has a validated identity-bearing checkpoint; superseded T15/T21 remain non-executable.
- Focused regressions, Ruff, BasedPyright, package/graph/schema/projection checks, Markdown gates, and applicable Agent Handoff gates pass.
- Final release tasks pass fresh source/candidate/installed checks, `scripts/verify.sh --full`, hosted checks, classification, artifact parity, and recovery gates.
- Immutable predecessors, consumer-owned configuration, unrelated work, and exact approved release contents are preserved.
- Appendix C evidence exists, is sanitized, and matches independently observed external state.
- GitHub, releases, status, TODO, roadmap, changelog, and handoff truth agree.
- No blocker, correction, unapproved deviation, stale authority reference, or orphan deferred item remains.

## 13. Close-out

- **Completed:** pending.
- **Implementation and acceptance checkpoints:** pending.
- **Decisions / deviations harvested:** pending.
- **Risks closed / accepted:** pending.
- **Deferred/discovered work filed:** pending.
- **Specification/ADR/documentation/handoff reconciliation:** pending.
- **Durable evidence verified:** pending.
- **Scratch teardown:** remove format-3 `execution/` only after durable harvest; remove preserved legacy scratch only after its useful evidence is superseded and explicitly reviewed.

## Appendix A. Interface and State Contracts

### A.1 Interfaces

| Contract | Owner / Producer Task | Consumer(s) | Current | Planned | Errors / Limits | Version / Compatibility | Invariants | Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Package successor selection | qualification task | consumers and later tasks | released predecessor selected | additive immutable successor advertised | missing/tampered payload fails closed | all predecessors remain selectable | one canonical payload per advertised version | request |
| Combined v5.15.0 boundary | T35 | later trains and consumers | approved, unpublished | exact twelve issues plus CLI Documentation 1.6 | unexpected issue/package content blocks | follows v5.14.0 without rewrite | one combined qualification and publication | request |
| Format-3 checkpoint | repository-local bridge | executor and recovery | identity-less legacy records | ordered `Plan-*` trailers bound to revision/digest | malformed, missing, or foreign identity is declined | legacy records receive no credit | commit exists before terminal state | request |

### A.2 State Transitions

| State / Version | Meaning | Entry Condition | Valid Transition | Invalid Transition Behavior | Recovery / Cleanup | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| legacy scratch | historical observation only | predates format-3 bridge | inspect or archive; never transition | current bridge ignores it as executable state | retain until T1/T30 replay and evidence review | plan owner |
| format-3 execution | authoritative live task state | active validated master and generated projection | only bridge-owned closed transitions | rejected atomically without write | validate, recover matching checkpoints, or revise plan | `scripts/plan.py` |
| unpublished release candidate | mutable candidate | owning tasks complete | qualify, correct, or abandon | no issue closure/publication | rebuild clean and rerun complete qualifier | release task |
| published release | immutable history | authorized publication and verified assets | successor release only | rewrite/delete prohibited | record defect and fully qualify successor | owner/release task |

### A.3 Configuration / Deployment Ownership

| Artifact | Format | Owned Span / Entry | Preserved Content | Atomicity / Conflict Rule | Owner Task |
| --- | --- | --- | --- | --- | --- |
| consumer configuration | TOML/JSONC/Markdown | typed package-owned units only | undeclared consumer bytes and comments | plan complete edit set before atomic apply | T9–T14, T19, T33 |
| package catalog/projection/lock | TOML/files/symlinks | qualification aggregation | predecessor files and selections | package/graph/schema/projection checks before release | T8, T28, T35–T36 |
| protected consumer branches | Git | reviewed Agent Handoff retirement commit/merge | unrelated branch work | exact target and authorization before mutation | T32 |

## Appendix B. Requirement-to-Proof Traceability

| Proof ID | Requirement(s) | Task | Method | Oracle | Command / Procedure | Expected Result | Negative Control | Environment | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TC-T1-001 | REQ-080 | T1 | operational acceptance | owner-approved release or operational contract plus independently observed repository and external state | execute the T1 operational lifecycle and its action-specific approval gates | exact v5.13.0/Agent Handoff 1.7 direct and harness-style launches reproduce the shim failure; direct, uv-fallback, and unavailable-runtime successor lanes behave correctly for both harnesses in published v5.14.0; hosted gates and asset bytes verify; issue #80 closes with exact evidence. | missing authorization, wrong target, failed external proof, or non-idempotent repeat prevents completion | local plus authorized GitHub/consumer scope | EV-001 |
| TC-T2-001 | REQ-075 | T2 | regression | accepted issue reproduction, immutable predecessor behavior, and task acceptance boundary | targeted tests, Ruff, BasedPyright, `scripts/verify.sh`. | mixed forbidden/overlong paragraph findings keep correct rule, line, observed value, and limit regardless of order. | the prior reproduction, a plausible hollow fix, or predecessor-byte mutation remains detectable | locked local source/candidate environment and hosted gate where declared | ephemeral |
| TC-T3-001 | REQ-090 | T3 | regression | accepted issue reproduction, immutable predecessor behavior, and task acceptance boundary | targeted tests, Ruff, BasedPyright, `scripts/verify.sh`. | managed hook/registration evidence is clean while unowned duplicates remain visible. | the prior reproduction, a plausible hollow fix, or predecessor-byte mutation remains detectable | locked local source/candidate environment and hosted gate where declared | ephemeral |
| TC-T4-001 | REQ-091 | T4 | integration regression | accepted issue reproduction, immutable predecessor behavior, and task acceptance boundary | targeted tests, Ruff, BasedPyright, `scripts/verify.sh`. | older V5 fixtures run `legacy-report` before reconciliation without mutation and disclose the locked basis. | the prior reproduction, a plausible hollow fix, or predecessor-byte mutation remains detectable | locked local source/candidate environment and hosted gate where declared | ephemeral |
| TC-T5-001 | REQ-101 | T5 | integration regression | accepted issue reproduction, immutable predecessor behavior, and task acceptance boundary | targeted tests, documentation gates, `scripts/verify.sh`. | the documented checkpoint provides equivalent pre-write safety and an accurate diagnostic. | the prior reproduction, a plausible hollow fix, or predecessor-byte mutation remains detectable | locked local source/candidate environment and hosted gate where declared | ephemeral |
| TC-T6-001 | REQ-102 | T6 | regression | accepted issue reproduction, immutable predecessor behavior, and task acceptance boundary | targeted tests, Ruff, BasedPyright, `scripts/verify.sh`. | matcher-less and differently matched legacy groups cannot yield a green double injection. | the prior reproduction, a plausible hollow fix, or predecessor-byte mutation remains detectable | locked local source/candidate environment and hosted gate where declared | ephemeral |
| TC-T7-001 | REQ-107 | T7 | contract regression | accepted issue reproduction, immutable predecessor behavior, and task acceptance boundary | targeted/package tests and `scripts/verify.sh`. | env-reference and command-substitution cases produce identical safe findings; compatibility impact is documented. | the prior reproduction, a plausible hollow fix, or predecessor-byte mutation remains detectable | locked local source/candidate environment and hosted gate where declared | ephemeral |
| TC-T8-001 | REQ-900 | T8 | operational acceptance | owner-approved release contract plus independently observed repository and external state | execute the T8 operational lifecycle and action-specific authorization gates | predecessor bytes, candidate parity, full gate, hosted checks, assets, recovery decision, and six closures verify. | missing authorization, wrong target, failed external proof, or non-idempotent repeat prevents completion | local plus authorized GitHub release scope | EV-002 |
| TC-T9-001 | REQ-076, REQ-077 | T9 | regression | accepted issue reproduction, immutable predecessor behavior, and task acceptance boundary | control-plane tests, Ruff, BasedPyright, `scripts/verify.sh`. | empty `py.typed`/`.gitkeep` and deleted-container policy transitions converge while verification stays fail-closed. | the prior reproduction, a plausible hollow fix, or predecessor-byte mutation remains detectable | locked local source/candidate environment and hosted gate where declared | ephemeral |
| TC-T10-001 | REQ-083 | T10 | integration regression | accepted issue reproduction, immutable predecessor behavior, and task acceptance boundary | migration tests, Ruff, BasedPyright, `scripts/verify.sh`. | the issue fixture previews in human/JSON modes; missing evidence names package, transform, input, and safe action. | the prior reproduction, a plausible hollow fix, or predecessor-byte mutation remains detectable | locked local source/candidate environment and hosted gate where declared | ephemeral |
| TC-T11-001 | REQ-087 | T11 | regression | accepted issue reproduction, immutable predecessor behavior, and task acceptance boundary | tests, schema checks, Ruff, BasedPyright, `scripts/verify.sh`. | safe expected/observed/option evidence is present; equivalent successor intent needs no destructive temporary restore. | the prior reproduction, a plausible hollow fix, or predecessor-byte mutation remains detectable | locked local source/candidate environment and hosted gate where declared | ephemeral |
| TC-T12-001 | REQ-098 | T12 | integration regression | accepted issue reproduction, immutable predecessor behavior, and task acceptance boundary | migration/frontmatter tests and `scripts/verify.sh`. | invalid IDs block before lock publication with reviewed repair guidance and no implicit document changes. | the prior reproduction, a plausible hollow fix, or predecessor-byte mutation remains detectable | locked local source/candidate environment and hosted gate where declared | ephemeral |
| TC-T13-001 | REQ-105 | T13 | property regression | accepted issue reproduction, immutable predecessor behavior, and task acceptance boundary | TOML/control-plane tests and `scripts/verify.sh`. | flat/nested, empty/nonempty, and ordering permutations yield valid TOML and preserve consumer values. | the prior reproduction, a plausible hollow fix, or predecessor-byte mutation remains detectable | locked local source/candidate environment and hosted gate where declared | ephemeral |
| TC-T14-001 | REQ-106 | T14 | property regression | accepted issue reproduction, immutable predecessor behavior, and task acceptance boundary | JSONC/control-plane tests and `scripts/verify.sh`. | sole-member, comma-leading, comma-own-line, LF/CRLF, and comment-adjacent layouts converge safely. | the prior reproduction, a plausible hollow fix, or predecessor-byte mutation remains detectable | locked local source/candidate environment and hosted gate where declared | ephemeral |
| TC-T16-001 | REQ-088 | T16 | contract regression | accepted issue reproduction, immutable predecessor behavior, and task acceptance boundary | package/real-tool tests and `scripts/verify.sh`. | languages and ignored scratch outside configured globs are never traversed. | the prior reproduction, a plausible hollow fix, or predecessor-byte mutation remains detectable | locked local source/candidate environment and hosted gate where declared | ephemeral |
| TC-T17-001 | REQ-089 | T17 | integration regression | accepted issue reproduction, immutable predecessor behavior, and task acceptance boundary | package/real BasedPyright tests and `scripts/verify.sh`. | strict tests do not resolve an untyped editable install first; other layouts remain compatible. | the prior reproduction, a plausible hollow fix, or predecessor-byte mutation remains detectable | locked local source/candidate environment and hosted gate where declared | ephemeral |
| TC-T18-001 | REQ-095 | T18 | contract regression | accepted issue reproduction, immutable predecessor behavior, and task acceptance boundary | package/real-tool tests and `scripts/verify.sh`. | nested projects and undeclared scripts remain untouched; every declared root is covered. | the prior reproduction, a plausible hollow fix, or predecessor-byte mutation remains detectable | locked local source/candidate environment and hosted gate where declared | ephemeral |
| TC-T19-001 | REQ-099 | T19 | contract regression | accepted issue reproduction, immutable predecessor behavior, and task acceptance boundary | package/control-plane tests and `scripts/verify.sh`. | Typer's targeted B008 configuration reconciles without global suppression, source churn, or split-file workaround. | the prior reproduction, a plausible hollow fix, or predecessor-byte mutation remains detectable | locked local source/candidate environment and hosted gate where declared | ephemeral |
| TC-T20-001 | REQ-086 | T20 | integration regression | accepted issue reproduction, immutable predecessor behavior, and task acceptance boundary | package/real-tool tests and `scripts/verify.sh`. | explicit-root consumers get a bounded gate; src/flat predecessors remain unchanged. | the prior reproduction, a plausible hollow fix, or predecessor-byte mutation remains detectable | locked local source/candidate environment and hosted gate where declared | ephemeral |
| TC-T22-001 | REQ-108 | T22 | documentation inspection | accepted issue reproduction, immutable predecessor behavior, and task acceptance boundary | targeted contract/documentation validation. | candidate instructions are development-only and future releases cannot ship candidate-as-current prose. | the prior reproduction, a plausible hollow fix, or predecessor-byte mutation remains detectable | locked local source/candidate environment and hosted gate where declared | ephemeral |
| TC-T23-001 | REQ-084 | T23 | characterization and regression | accepted issue reproduction, package integrity checks, and the frozen isolated matrix | execute the T23 characterization/fix-or-disposition lifecycle | fresh installs, concurrent install/launch, and repeated paired previews establish cause or a documented threshold; T35 remains blocked until the evidence-backed disposition is accepted. | an environment-only failure, incomplete matrix, hollow fix, or unsupported no-reproduction claim remains detectable | isolated locked local environments | EV-003 |
| TC-T24-001 | REQ-062 | T24 | documentation inspection | accepted issue reproduction, immutable predecessor behavior, and task acceptance boundary | doc gates, converged review, owner approval. | byte-exact/structural/advisory checks and existing-consumer impact are explicit and reviewed. | the prior reproduction, a plausible hollow fix, or predecessor-byte mutation remains detectable | locked local source/candidate environment and hosted gate where declared | ephemeral |
| TC-T25-001 | REQ-062 | T25 | operational acceptance | approved #62 specification and child-plan checkpoints plus independently observed release/issue state | execute the child plan and T25 operational publication lifecycle | canonical/divergent/tailored/predecessor documents produce approved results and #62 closes after release. | incomplete child state, missing authorization, wrong artifact, or premature issue closure prevents completion | local, hosted checks, and authorized GitHub release scope | EV-009 |
| TC-T26-001 | REQ-055 | T26 | documentation inspection | accepted issue reproduction, immutable predecessor behavior, and task acceptance boundary | doc gates, converged review, owner approval. | unrecognized prose cannot be discarded; ambiguous choices remain explicit; rollback is defined; safe adoption for future canonical specs with an excluded/no-match legacy corpus remains supported and never forces conversion. | the prior reproduction, a plausible hollow fix, or predecessor-byte mutation remains detectable | locked local source/candidate environment and hosted gate where declared | ephemeral |
| TC-T27-001 | REQ-055 | T27 | contract regression | accepted issue reproduction, immutable predecessor behavior, and task acceptance boundary | child completion, semantic audit, fresh candidate/full gate. | conversion is explicit and opt-in; recognized structure maps deterministically; unmapped content stays intact/review-visible; apply is guarded; new-spec-only/no-match consumers retain their existing successful behavior. | the prior reproduction, a plausible hollow fix, or predecessor-byte mutation remains detectable | locked local source/candidate environment and hosted gate where declared | ephemeral |
| TC-T28-001 | REQ-900 | T28 | operational acceptance | owner-approved release contract plus independently observed repository and external state | execute the T28 operational lifecycle and action-specific authorization gates | source/candidate/installed parity, migration safety, the full local gate, hosted checks, assets, recovery decision, and #55 closure verify. | missing authorization, wrong target, failed external proof, or non-idempotent repeat prevents completion | local plus authorized GitHub release scope | EV-004 |
| TC-T29-001 | REQ-901 | T29 | operational acceptance | owner-approved release or operational contract plus independently observed repository and external state | execute the T29 operational lifecycle and its action-specific approval gates | all 24 issues are closed or explicitly accepted; docs/releases/ledger agree; scratch is harvested and removed. | missing authorization, wrong target, failed external proof, or non-idempotent repeat prevents completion | local plus authorized GitHub/consumer scope | EV-005 |
| TC-T30-001 | REQ-902 | T30 | contract verification | owner-approved release policy, immutable predecessor fixtures, and the focused exact-level matrix | execute the T30 verification lifecycle without changing implementation | a matching tool/catalog major increment is accepted as the owner's MAJOR designation unless another contract is forbidden; otherwise any standard-package version advance requires exactly MINOR and no standard-package version advance requires exactly PATCH. Per package ID, a newly introduced package or a newly advertised version above the prior advertised maximum is an advance; internal and reference-only packages count, while older retained history and unadvertised payloads do not. Advertised-version removal, package downgrade, immutable-byte violations, and same-catalog breaking-default promotion remain forbidden, and ADR 0024 plus `meta/versioning.md` use the same rule. | a stale policy, hollow classifier, removed advertised version, downgrade, or predecessor-byte mutation remains detectable | locked local source and package-contract environment | EV-010 |
| TC-T31-001 | REQ-903 | T31 | contract regression | accepted issue reproduction, immutable predecessor behavior, and task acceptance boundary | run Python Tooling package tests, package/graph/schema/projection checks, and `scripts/verify.sh`. | Python Tooling 1.10 remains byte-identical; its planned successor contains no claim that the V1 root manifest is current authority, consistently identifies the selected V5 package/control plane as authoritative, and is routed to the T35 release train with no separate release train declared. | the prior reproduction, a plausible hollow fix, or predecessor-byte mutation remains detectable | locked local source/candidate environment and hosted gate where declared | ephemeral |
| TC-T32-001 | REQ-904 | T32 | operational acceptance | owner-approved release or operational contract plus independently observed repository and external state | execute the T32 operational lifecycle and its action-specific approval gates | each remaining consumer has only the standards-managed Agent Handoff document/hook pair on its authoritative branch, passes `project-standards agent-handoff validate --repo .` and `drift-check --repo .` using its selected control plane, preserves unrelated work, and has remote parity after separately authorized publication; retirement records name the verified final state. | missing authorization, wrong target, failed external proof, or non-idempotent repeat prevents completion | local plus authorized GitHub/consumer scope | EV-006 |
| TC-T33-001 | REQ-109 | T33 | integration regression | accepted issue reproduction, immutable predecessor behavior, and task acceptance boundary | run Python Tooling package/real-uv tests, predecessor-byte checks, package contracts, and `scripts/verify.sh`. | an absent `pyproject.toml` or missing `[project]` table produces an actionable no-write finding that names the required consumer decision and installable/non-installable routes; existing valid `[project]` metadata is preserved; the documented apply → `uv lock` flow succeeds with the lock-resolved uv version; Python Tooling 1.10 remains byte-identical. | the prior reproduction, a plausible hollow fix, or predecessor-byte mutation remains detectable | locked local source/candidate environment and hosted gate where declared | ephemeral |
| TC-T34-001 | REQ-906 | T34 | characterization and regression | accepted issue reproduction, immutable predecessor behavior, and task acceptance boundary | run focused tests, package/graph/schema/projection checks, Markdown gates, and `scripts/verify.sh`. | 1.5 remains byte-identical/selectable; 1.6's Python, Go, and generic profiles validate; the Go workflow builds one explicit package and verifies the built command; package, graph, schema, projection, Markdown, and focused real-tool checks pass; any correction stays within the candidate contract. | the prior reproduction, a plausible hollow fix, or predecessor-byte mutation remains detectable | locked local source/candidate environment and hosted gate where declared | ephemeral |
| TC-T37-001 | REQ-907 | T37 | characterization and regression | merged candidate payload, immutable adr@1.3 bytes, and the task acceptance boundary | run focused ADR provider and payload-contract tests, package/graph/schema/projection checks, Markdown gates, and `scripts/verify.sh`. | adr@1.3 remains byte-identical and selectable; adr@1.4's declared resource digests and aggregate identity verify; its provider-input schema selects 1.4 and `run_migrate` preserves the requested version; the MADR section provider loads and reports findings; the example's stated exclusions match its declared boundary; the deferred release-boundary items are inventoried for T35 and not advanced inside verification; package, graph, schema, projection, and Markdown checks pass. | a stale version constant, a mutated predecessor byte, or a digest that does not match its declared resource remains detectable | locked local source/candidate environment and hosted gate where declared | ephemeral |
| TC-T35-001 | REQ-900, REQ-905, REQ-906 | T35 | operational acceptance | owner-approved release or operational contract plus independently observed repository and external state | execute the T35 operational lifecycle and its action-specific approval gates | prior-release reproductions fail for the expected reasons; every selected correction and accepted #84 disposition passes source, candidate-wheel, installed, migration, adapter, real-tool, and predecessor-byte proofs; CLI Documentation 1.6 and the Python Tooling successor are advertised without altering predecessors; full local and hosted gates pass; signed tags and byte-verified assets are published only after authorization; issues #76, #77, #83, #84, #86, #87, #89, #95, #98, #105, #106, and #109 close or receive the accepted disposition. | missing authorization, wrong target, failed external proof, or non-idempotent repeat prevents completion | local plus authorized GitHub/consumer scope | EV-007 |
| TC-T36-001 | REQ-900 | T36 | operational acceptance | owner-approved release or operational contract plus independently observed repository and external state | execute the T36 operational lifecycle and its action-specific approval gates | v5.15.0 and every predecessor remain byte-identical/selectable; the bounded Prettier corpus and Ruff plugin-ownership contracts pass source/candidate/installed proofs; full and hosted gates pass; publication and both closures follow explicit authorization. | missing authorization, wrong target, failed external proof, or non-idempotent repeat prevents completion | local plus authorized GitHub/consumer scope | EV-008 |

## Appendix C. Durable Evidence

| Evidence ID | Producing Task | Path | Contents / Provenance | Privacy Exclusions | Retention Reason |
| --- | --- | --- | --- | --- | --- |
| EV-001 | T1 | docs/research/2026-08-01-agent-handoff-1-8-closeout-evidence.md | published v5.13/v5.14 launcher probes, hosted run, assets, and issue disposition | no credentials, private harness configuration, or unbounded logs | preserve the external issue-close basis after scratch teardown |
| EV-002 | T8 | docs/research/2026-08-01-agent-handoff-authority-release-evidence.md | release candidate, installed-wheel, hosted, artifact, and issue-closure matrix | no credentials, private consumer configuration, or raw CI logs | retain release and recovery evidence for the authority train |
| EV-003 | T23 | docs/research/2026-08-01-pyyaml-transient-disposition.md | isolated installation matrix, versions, integrity observations, and accepted disposition | no environment secrets, cache contents, or unrelated package inventory | retain the version-bound no-reproduction or defect-cause decision |
| EV-004 | T28 | docs/research/2026-08-01-project-spec-feature-release-evidence.md | feature release candidate, migration safety, hosted, asset, and issue-closure proof | no credentials, private consumer configuration, or raw CI logs | retain external release acceptance after scratch teardown |
| EV-005 | T29 | docs/research/2026-08-01-open-issue-program-closeout-evidence.md | frozen-issue reconciliation, release mapping, accepted dispositions, and final status | no credentials, private issue drafts, or unbounded API responses | retain the program completion basis |
| EV-006 | T32 | docs/research/2026-07-09-agent-handoff-retirement-inventory.md | per-consumer authoritative-branch, validation, drift, and parity outcomes | no credentials, private configuration bytes, or unrelated consumer diffs | retain the operational retirement record |
| EV-007 | T35 | docs/research/2026-08-01-v5-15-release-evidence.md | v5.15 source, wheel, installed, migration, hosted, artifact, publication, and issue matrix | no signing secrets, tokens, private consumer configuration, or raw CI logs | retain the combined release acceptance and recovery basis |
| EV-008 | T36 | docs/research/2026-08-01-deferred-tooling-release-evidence.md | deferred successor source, installed, hosted, artifact, publication, and issue matrix | no signing secrets, tokens, private consumer configuration, or raw CI logs | retain the post-v5.15 release acceptance basis |
| EV-009 | T25 | docs/research/2026-08-01-project-spec-conformance-release-evidence.md | child-plan completion, candidate, hosted, artifact, publication, and issue-closure proof | no signing secrets, tokens, private consumer configuration, or raw CI logs | retain the #62 release acceptance basis |
| EV-010 | T30 | docs/research/2026-08-01-release-level-classification-evidence.md | landed commit, owner policy, focused classification matrix, package gates, and verification summary | no credentials, private configuration, or unbounded command logs | create an identity-bearing verification checkpoint without backfilling legacy task history |

## Appendix D. Deferred Work

| Item | Reason Deferred | Source / Scope Relationship | Follow-up / Reopen Trigger |
| --- | --- | --- | --- |
| Issues opened after 2026-08-01T09:21:01Z | keep the frozen program convergent | outside approved inventory unless appended | owner approves a discovered/correction task |
| `control_plane/provider_inputs.py` retirement | explicitly excluded from this program | separate payload-declared input-shape roadmap | MCP hold and separate authority lift |
| Self-hosted CI and Usage Documentation Site V2 | independent future programs | repository TODO/approved v5.16 design | separately authorized specification and plan |
| Legacy execution scratch removal | old logs may still orient replay | migration evidence only, never executable state | T1/T30 replay is durable and owner reviews deletion |
