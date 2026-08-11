---
plan_format: 3
title: 'GitHub Workflow 1.2 Guidance Implementation Plan'
slug: 'github-workflow-1-2-guidance'
status: active
revision: 1
revises_revision: 0
revision_reason: 'initial plan'
pause_reason: ''
source: 'issue L3DigitalNet/project-standards#169; approved github-workflow design and specification'
spec_ref: 'docs/specs/2026-08-06-github-workflow-package-spec.md'
created: 2026-08-10
updated: 2026-08-10
owners:
  - 'Project Standards maintainers'
  - 'Coding agents under human review'
---

# GitHub Workflow 1.2 Guidance Implementation Plan

> **Definition, not state.** Authoring generated no `.project-pipeline` state. During execution, the orchestrator alone generates and mutates ephemeral state under `.project-pipeline/2026-08-10-github-workflow-1-2-guidance/execution/`.

## 1. Objective

Ship `github-workflow@1.2` as the v5.19 MINOR successor and activate it in Catalog 5. The package shall tell consumers when labels complement typed fields, reject label namespaces that duplicate typed or derived state, give a counterexample for every unordered pair of Priority, Size, Change risk, and Severity, and record that the obsolete MCP-first proposal is retired in favor of the already-approved `gh`-token REST boundary. The shipped `gh-workflow` binary and the organization schema remain unchanged.

## 2. Authority and Source Map

| Source | Source Role | Authority / Use | Version / Date | Affected Plan Surface |
| --- | --- | --- | --- | --- |
| `request` | normative | Author only a 1.2 candidate then activation plan; retain 1.1 immutability; include RED, package/projection/catalog validation, rexec discipline, and proportional gates. | 2026-08-10 | §§1, 3, 6–13; T1–T2 |
| `issue:L3DigitalNet/project-standards#169` | normative | Defines the three gaps, accepted label namespaces/prohibitions, MCP decision record, counterexample scope, package-version delivery, and unchanged-binary default. | body/comments verified 2026-08-10 | §§1, 3–7, 9–12; T1–T2 |
| `spec:docs/specs/2026-08-06-github-workflow-package-spec.md#21-open-questions-and-decisions` | decision | The approved package uses a nine-command stdlib CLI and REST only through the operator's `gh`-issued token; it is not an MCP client. | revision 1.8, 2026-08-09 | §§3–6; T1 |
| `repo:docs/specs/2026-08-06-github-workflow-package-design.md#constraints-assumptions-and-agent-applied-defaults` | decision | Repository-scoped work-state mutation belongs to the `gh`-backed tool, while organization schema changes remain human-applied and audit-only. | approved 2026-08-06 | §§3–6; T1 |
| `repo:standards/github-workflow/versions/1.1/skills/github-workflow/SKILL.md` | current-state evidence | Current delivered skill mandates the `gh-workflow` binary and contains neither label routing nor an MCP route. | package 1.1 | §§4–7; T1 |
| `repo:standards/github-workflow/versions/1.1/skills/github-workflow/references/field-vocabulary.md` | current-state evidence | It names the four field distinctions but has one Priority–Severity example and no label routing section. | package 1.1 | §§4–7; T1 |
| `repo:standards/github-workflow/standard.toml` | current-state evidence | Family index currently retains 1.0 and 1.1; a successor must be a new immutable entry. | `e24f50ef` | §§3–7; T1–T2 |
| `repo:catalogs/5.toml` | current-state evidence | Catalog currently makes 1.1 the default; activation must retain its published predecessors. | `e24f50ef` | §§4, 7, 9–12; T2 |
| `repo:standards/github-workflow/README.md` | current-state evidence | Mutable family navigation names 1.1 as current and must move only at activation. | `e24f50ef` | §§4, 7, 9–12; T2 |
| `repo:tests/package_contract/test_github_workflow_1_1.py` | current-state evidence | Existing successor-immutability, payload-integrity, projection, and catalog-role test patterns. | `e24f50ef` | §§4, 7, 9–12; T1–T2 |
| `repo:meta/versioning.md#release-requirements` | normative | Activation promotes the candidate to default, retains the predecessor, reconciles generated producer state, and verifies the exact release tree. | current | §§3, 7, 10, 12; T2 |
| `repo:docs/handoff/conventions.md#18-match-verification-to-the-changed-surface` | decision | Payload/catalog/digest work uses Tier 1 validators plus Markdown gates; candidate-wheel/full gate applies only where its surface requires it. | current | §§3, 7, 9, 12; T1–T2 |

Conflict precedence: #169's requested retirement governs its own obsolete MCP-first antecedent. The approved package design/specification and shipped 1.1 boundary establish the present `gh`-backed REST decision. No authority requires an MCP implementation or an ADR.

## 3. Scope, Boundaries, and Constraints

### 3.1 In Scope

- A complete immutable `standards/github-workflow/versions/1.2/` payload and corresponding symlink-only source projection, with package prose changed only where the issue requires it.
- Label guidance: `area/*`, `concern/*`, and `source/*` are optional categorization labels; `priority/*`, `status/*`, `size/*`, `severity/*`, `risk/*`, and `agent-ready` are prohibited duplicates of typed or derived state.
- Six distinct worked counterexamples, one for each pair among Priority, Size, Change risk, and Severity.
- A release-record statement that retires MCP-first design intent, selects the approved `gh`-token REST-only boundary, and says that no MCP `issue_read` path is endorsed; therefore no body-escaping procedure is supplied.
- 1.2 family/catalog activation, generated producer state, package contract coverage, release-current navigation, and release-facing validation.

### 3.2 Out of Scope and Deferred

- No organization Issue Type/Issue Field/label mutation, audit baseline change, consumer-repository change, or manual edit to consumer-managed artifacts.
- No MCP client/provider, `issue_read`/`issue_write` path, GraphQL path, API behavior change, or rebuild/change to `gh-workflow`; the 1.1 binary is carried byte-identically.
- No new or amended ADR. This is a package delivery/documentation record for an already-approved tool boundary, not a significant, costly-to-reverse architectural decision under ADR 1.5.
- No v5.19 release tagging, publishing, GitHub lifecycle mutation, handoff closeout, or subsequent consumer reconciliation beyond producer-mode activation proof.

### 3.3 Ownership and Preserved Behavior

| Boundary | Owner / Responsibility |
| --- | --- |
| T1 owns | The complete unadvertised 1.2 payload, its immutable-family/index/projection contract, and focused 1.2 package tests. |
| T2 owns | Catalog activation, family/current navigation, changelog retirement record, producer generated state, activation tests, and final release-ready proof. |
| Plan does not own | Organization schema, external GitHub data, consumer worktrees, ADR corpus #162, or runtime/tool behavior. |
| Must preserve | 1.0 and 1.1 bytes/digests, the 1.1 binary mode and bytes, option/schema/provider/artifact set, REST-only `gh` token boundary, typed-field semantics, and exact-selector behavior. |

### 3.4 Constraints and Authorization

- Cut a new complete V2 payload rather than editing the released 1.1 tree; manifests, resource/artifact digests, family index, projection, and package tests must agree.
- The binary remains byte-identical from 1.1. Do not run `scripts/build-gh-workflow.sh`, change Go source, or broaden tool behavior; a binary delta is a scope violation.
- Add documentation tests before documentation changes: correct-reason RED is the absence of required label guidance, pair examples, and MCP-retirement record, not a failing Go or external-GitHub test.
- Before payload work, run `uv run python scripts/family_preflight.py github-workflow`; it predicts declaration sites but does not replace validation.
- Run Git/history/index-dependent commands directly locally. `rexec` is remote-only and never mirrors `.git`; compatible CPU-heavy checks may use `rexec -- uv run basedpyright`, but catalog/release checks, Git queries, and plan-state commands must not.
- After payload or `src/**` changes, use `scripts/bootstrap-worktree.sh` before any candidate-runtime or pytest gate. Tier 1 package/catalog work otherwise uses the five validators and scoped Markdown checks first.

## 4. Current State and Target State

### 4.1 Current State

`github-workflow@1.1` is the Catalog 5 default. Its skill routes all mechanical GitHub operations through a Linux/amd64 `gh-workflow` binary under the operator's `gh` authentication. The approved specification says GitHub access is REST only, and no MCP path ships.

The field vocabulary correctly distinguishes Priority, Size, Change risk, and Severity, but the only worked independence example is Priority–Severity. It has no label namespace guidance. The family index, source projection, catalog, family-root navigation, generated `standards/catalog.md`, and producer `.standards` state identify 1.1 as current/default.

### 4.2 Target State

`github-workflow@1.2` is a complete, default Catalog 5 payload and 1.1 is retained. The delivered skill/reference pair gives a precise label-vs-field decision procedure and every required independence example. The release changelog records the deliberately non-MCP boundary and retirement of the superseded MCP-first proposal. No runtime call surface, token source, provider schema, organization schema, or binary byte changes.

### 4.3 Delta Summary

| Area | Current | Target | Must Preserve |
| --- | --- | --- | --- |
| Label routing | No package guidance. | Three allowed namespaces and six forbidden duplicates are explicit. | Labels remain optional categorization; typed fields remain authoritative. |
| Field independence | Six relations named; one worked example. | Six pairwise counterexamples. | Existing field values, pinning matrix, and meanings. |
| Transport record | Approved REST/`gh` boundary exists, while superseded MCP-first intent is unrecorded in release notes. | Changelog explicitly retires MCP-first and endorses the existing boundary. | No MCP behavior or migration claim. |
| Package lifecycle | 1.1 default, 1.0 retained. | 1.2 default, 1.1/1.0 retained and immutable. | Exact selections stay exact; no advertised version is removed. |

## 5. Change Surface and Architecture

### 5.1 Components and Ownership

| Component / Surface | Current Responsibility | Planned Responsibility | Paths / Contracts | Owning Task |
| --- | --- | --- | --- | --- |
| Delivered decision procedure | Skill has mutation/refusal mechanics but no label routing. | Add compact routing/refusal language; keep command surface unchanged. | `skills/github-workflow/SKILL.md` | T1 |
| Field reference | Defines fields and one example. | Own six pair examples and label namespaces/prohibitions. | `references/field-vocabulary.md` | T1 |
| Immutable payload contract | 1.1 manifest pins all delivered bytes. | 1.2 pins a complete successor while 1.1 remains intact; binary is equal. | `versions/1.2/payload.toml`, `standard.toml`, projection | T1 |
| Release record/activation | Catalog and mutable family pages name 1.1. | Promote 1.2/default, retain predecessors, record MCP retirement, regenerate producer state. | catalog, family roots, `CHANGELOG.md`, generated state | T2 |

### 5.2 Change-Surface Matrix

| Surface | Applies? | Invariant / Required Change | Proof | Task |
| --- | --- | --- | --- | --- |
| Behavior | yes | Delivered guidance changes; `gh-workflow` behavior and command surface do not. | PV-T1-001 | T1 |
| Architecture / dependency direction | yes | Retire obsolete MCP-first prose in favor of existing `gh`/REST boundary; do not add a transport. | PV-T1-001, PV-T2-001 | T1–T2 |
| Public interface | yes | Label routing is consumer-visible documentation; provider/config schemas and CLI flags do not change. | PV-T1-001 | T1 |
| Data / persistent state | no | No migration or new state. | PV-T2-001 | T2 |
| Configuration | yes | Catalog/default/lock selection advances; exact selectors retain old payloads. | PV-T2-001 | T2 |
| Security / trust | yes | Existing operator `gh` authentication only; no new MCP credential or body-round-trip surface. | PV-T1-001 | T1 |
| Compatibility / migration | yes | 1.0/1.1 remain byte-addressable and default moves only at activation. | PV-T1-001, PV-T2-001 | T1–T2 |
| Operations / deployment | yes | Release checks run locally where Git metadata is needed; no external deployment. | PV-T2-001 | T2 |
| Documentation | yes | Package/family/current/release documentation agrees. | PV-T1-001, PV-T2-001 | T1–T2 |
| Durable evidence | no | Committed tests and validators are reproducible evidence. | PV-T1-001, PV-T2-001 | T1–T2 |

### 5.3 Binding Decisions

| ID | Decision | Rationale | Source | Affected Task(s) |
| --- | --- | --- | --- | --- |
| D-001 | Use `area/*`, `concern/*`, and `source/*` only for categorization; prohibit field-shadowing namespaces and `agent-ready`. | Typed fields and the derived Ready predicate own operational state. | #169 | T1 |
| D-002 | Retire MCP-first in the changelog/package release record and retain the approved `gh`-token REST-only binary boundary. | This is the shipped, approved design; no MCP reader is endorsed, so its escaping trap is irrelevant. | #169; approved spec OQ-002 | T1–T2 |
| D-003 | Cut a MINOR 1.2 payload with the 1.1 binary byte-identical. | Consumer guidance changes require immutable versioned delivery; no tool behavior changed. | #169; `meta/versioning.md` | T1–T2 |
| D-004 | Do not create or amend an ADR. | The ADR threshold is significant and costly-to-reverse; this records a prior package implementation decision and is explicitly suitable for changelog treatment. | ADR 1.5; #169 acceptance | T2 |

## 6. Requirements and Acceptance

| ID | Requirement | Source | Priority | Owner Task | Task(s) | Proof(s) |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-001 | 1.2 shall document allowed `area/*`, `concern/*`, and `source/*` labels and prohibit `priority/*`, `status/*`, `size/*`, `severity/*`, `risk/*`, and `agent-ready` as replacements for typed/derived state. | #169 | Must | T1 | T1 | PV-T1-001 |
| REQ-002 | 1.2 shall contain one concrete counterexample for every pair among Priority, Size, Change risk, and Severity. | #169 | Must | T1 | T1 | PV-T1-001 |
| REQ-003 | The release record shall retire MCP-first in favor of the approved `gh`-token REST-only boundary, without adding an MCP read/mutation path or `issue_read` escaping procedure. | #169; package specification | Must | T2 | T1, T2 | PV-T1-001, PV-T2-001 |
| REQ-004 | 1.2 shall be a complete immutable successor/default; 1.0 and 1.1 remain retained, selectable, byte/digest intact, and the 1.1 binary is carried exactly. | #169; versioning policy | Must | T2 | T1, T2 | PV-T1-001, PV-T2-001 |
| REQ-005 | Activation shall update only producer-owned catalog/navigation/generated state and preserve organization schema, consumer repositories, ADR corpus, and runtime behavior. | request; #169 | Must | T2 | T2 | PV-T2-001 |

## 7. Verification and Evidence Strategy

- **Correct-reason RED:** add focused 1.2 package-contract tests first. On the 1.1-only tree they must fail because the 1.2 payload/index is absent and the required routing/examples/retirement text is absent; do not accept a failure caused by missing imports, stale wheel runtime, or a changed binary.
- **Payload proof:** test predecessor byte immutability, complete 1.2 manifest integrity, family-index digest, relative symlink-only projection, unchanged provider/config/artifact identities, binary byte/mode equality, all six exact pair examples, and all label routes/prohibitions.
- **Activation proof:** test catalog roles, exact/latest selection behavior, family-root version pointers, generated catalog/lock state, and changelog wording. Negative controls include a forbidden label route accepted as canonical, a missing pair, MCP wording that implies a supported path, a changed binary, a rewritten 1.1 digest, or an absent retained row.
- **Tier 1 commands:** run the five `project-standards standards` validators from convention 18, then scoped Prettier and markdownlint over changed tracked Markdown. Run direct-local Git/catalog/release commands; never through rexec.
- **Candidate runtime / gate:** after payload changes, `scripts/bootstrap-worktree.sh` then candidate-wheel-backed package pytest/dogfood only if the release version has advanced enough to resolve it. Run `scripts/verify.sh --full` at the final release-prep checkpoint, not during the unadvertised candidate cut; a `CP-RESOLUTION` before the version bump is expected evidence, not a defect to paper over.
- **Evidence:** command output and task commits are reproducible; no durable external evidence artifact is required.

## 8. Execution Summary

| Task | Title | Disposition | Work Type | Phase | Depends On | Requirement(s) | Primary Proof | Parallel / Conflict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T1 | Cut and prove the immutable GitHub Workflow 1.2 candidate | active | behavior | P1 | None | REQ-001–REQ-004 | PV-T1-001 | no / T2 consumes candidate and owns current pointers |
| T2 | Activate 1.2 and prove release-facing package selection | active | configuration | P2 | T1 | REQ-003–REQ-005 | PV-T2-001 | no / serialized catalog, family roots, changelog, generated state |

## 9. Implementation Tasks

### Phase P1: Immutable candidate

#### T1: Cut and prove the immutable GitHub Workflow 1.2 candidate

- **disposition:** active
- **outcome:** A complete but unadvertised `github-workflow@1.2` payload supplies the required label and field guidance and retains the 1.1 binary exactly.
- **work_type:** behavior
- **checkpoint:** one green candidate commit with required `Plan-*` checkpoint trailers.
- **boundary:** cross-task
- **depends_on:** []
- **dependency_reason:** none
- **requirements:** [REQ-001, REQ-002, REQ-003, REQ-004]
- **proof:** [PV-T1-001]
- **source_refs:** [issue:L3DigitalNet/project-standards#169, spec:docs/specs/2026-08-06-github-workflow-package-spec.md#21-open-questions-and-decisions, repo:standards/github-workflow/versions/1.1/skills/github-workflow/SKILL.md, repo:standards/github-workflow/versions/1.1/skills/github-workflow/references/field-vocabulary.md]
- **consumes:** [immutable 1.1 payload, approved REST-only boundary, V2 family contract]
- **produces:** [github-workflow-1.2-guidance-v1]
- **preserves:** [1.0/1.1 bytes and digests, 1.1 binary bytes/mode, option/config/provider schemas, tool command surface, organization schema]
- **invariants:** [one example per each of six unordered field pairs, prohibited labels never become an alternate field vocabulary, no MCP path implied, 1.2 is unadvertised until T2]
- **executor_discretion:** [exact prose placement and scenario wording, provided every required namespace/pairing/record condition remains explicit and tested]
- **files:** [`standards/github-workflow/versions/1.2/**` (new; owner T1), `standards/github-workflow/standard.toml` (modify; owner T1), `src/project_standards/payloads/github-workflow/1.2/**` (generated symlinks; owner T1), `tests/package_contract/test_github_workflow_1_2.py` (new; owner T1), `scripts/build-gh-workflow.sh` (inspect only; must remain unchanged)]
- **parallel_safe:** no
- **conflicts_with:** [T2]
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** Abort the candidate cut if predecessor bytes, binary equality, or manifest/projection integrity fails; restore the last green checkout and do not advance catalog/default state.
- **acceptance:** PV-T1-001 proves the complete 1.2 payload contains all required guidance and exact carry-forward boundaries while 1.1 remains immutable and 1.2 remains unadvertised.
- **sub-tasks:**
  - **T1.1 PRECHECK** — run `uv run python scripts/family_preflight.py github-workflow`; inspect 1.1 manifest, family index, source projection, and focused tests before creating 1.2.
  - **T1.2 RED** — create `test_github_workflow_1_2.py` with assertions for all allowed/prohibited label routes, six independently recognizable scenarios, REST-only/MCP-retirement text, binary equality/mode, predecessor digests, successor integrity, and unadvertised catalog role.
  - **T1.3 Verify RED** — run `uv run pytest tests/package_contract/test_github_workflow_1_2.py`; require failure because the missing 1.2 payload/guidance is the cause.
  - **T1.4 GREEN** — copy 1.1 into a new 1.2 payload, make only required skill/reference/version/manifest digest changes, copy the binary byte-identically, update the family index, and generate the symlink-only projection with the standard command.
  - **T1.5 Verify GREEN** — run the focused test plus package integrity/graph/projection checks; confirm no source or binary/tool change entered the diff.
  - **T1.6 Verify Task** — run PV-T1-001 and scoped Markdown checks; commit the candidate with required checkpoint trailers.

### Phase P2: Activation and release-facing proof

#### T2: Activate 1.2 and prove release-facing package selection

- **disposition:** active
- **outcome:** Catalog 5 defaults to 1.2, 1.1 is retained, current navigation/generated producer state is reconciled, and the changelog records the obsolete MCP-first retirement without an ADR.
- **work_type:** configuration
- **checkpoint:** one green activation commit with required `Plan-*` checkpoint trailers.
- **boundary:** configuration
- **depends_on:** [T1]
- **dependency_reason:** Activation consumes the complete/digest-verified 1.2 candidate and its focused contract proof.
- **requirements:** [REQ-003, REQ-004, REQ-005]
- **proof:** [PV-T2-001]
- **source_refs:** [issue:L3DigitalNet/project-standards#169, repo:meta/versioning.md#release-requirements, repo:catalogs/5.toml, repo:standards/github-workflow/README.md, repo:tests/package_contract/test_github_workflow_1_1.py::test_github_workflow_1_1__catalog_role__selects_the_successor_as_default]
- **consumes:** [github-workflow-1.2-guidance-v1]
- **produces:** [github-workflow-1.2-activation-v1]
- **preserves:** [all released rows/digests, exact selectors, consumer ownership, organization schema, 1.1 binary, no ADR/MCP/runtime change]
- **invariants:** [1.2 default exactly once; 1.1 and 1.0 retained; generated producer files only change through reconcile; changelog calls the boundary REST-only and rejects an MCP route]
- **executor_discretion:** [exact generated-file delta and changelog section placement dictated by release tooling; no manual editing of generated catalog/lock state]
- **files:** [`catalogs/5.toml` (modify; owner T2), `.standards/catalog.toml` (generated; owner T2), `.standards/lock.toml` (generated; owner T2), `standards/github-workflow/{README.md,adopt.md,agent-summary.md}` (modify; owner T2), `standards/README.md` (modify if current-package inventory changes; owner T2), `standards/catalog.md` (generated; owner T2), `CHANGELOG.md` (modify; owner T2), `tests/package_contract/test_current_catalog_activation.py` and `tests/test_release_consistency.py` (modify only if their current-selection assertions require 1.2; owner T2)]
- **parallel_safe:** no
- **conflicts_with:** [T1]
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** If reconcile or selection proof fails, retain the T1 candidate but revert only T2-owned activation/generated changes; do not edit predecessor entries or force a default.
- **acceptance:** PV-T2-001 proves 1.2 resolves as default, exact 1.0/1.1 selections remain available, all generated state is reconciliation-owned, and the release record neither implies MCP support nor creates an ADR.
- **sub-tasks:**
  - **T2.1 PRECHECK** — confirm T1's checkpoint/plan validation, recompute the 1.2 aggregate digest, and inspect all current GitHub Workflow catalog/navigation declarations.
  - **T2.2 RED** — extend selection/release-consistency assertions to expect 1.2 default with 1.1/1.0 retained and to require the MCP-retirement changelog statement; run targeted tests and capture the expected old-default failure.
  - **T2.3 GREEN** — update the Catalog 5 role rows and mutable current pointers; add the changelog entry; run producer `reconcile --apply` so `.standards` and generator-owned catalog output are regenerated rather than hand-edited.
  - **T2.4 Verify GREEN** — run targeted package/catalog tests; inspect exact selector/default resolution and generated-file ownership.
  - **T2.5 Verify Task** — run PV-T2-001, Tier 1 validators, scoped Markdown gates, candidate-runtime dogfood where the release version permits it, and final `scripts/verify.sh --full` only at release prep; commit with required checkpoint trailers.

## 10. Integration, Migration, and Recovery

### 10.1 Integration Sequence

1. T1 creates and proves the unadvertised immutable successor without touching Catalog/default state.
2. T2 advances the release composition, reconciles producer-owned generated files, and proves current/default and retained selection behavior together.
3. Release preparation performs the release-version bump, candidate-wheel extraction, direct-local Git-dependent checks, full gate, and publication under its separate authority.

### 10.2 Migration / State / Configuration Transition

- Required: catalog/default transition only; no consumer migration is required.
- Compatibility: exact `github-workflow@1.0` and `@1.1` selections remain unchanged; `latest` advances only through the 1.2 default after activation.
- Idempotency: `project-standards reconcile --apply` regenerates producer-owned state; a second run must converge without a diff.
- Point of no return: none before release publication; T2 may be reverted while preserving T1's unadvertised candidate.
- Recovery: restore the prior catalog/default/generated producer state as one coherent local revert; never mutate/delete released payloads or their digests.

### 10.3 Late Failure and Correction

A failed package/catalog/release proof blocks its owning task. After a completed checkpoint, add an append-only correction task with `corrects:` and `discovered_from:`, then rerun the affected proof; do not repurpose completed task definitions or manually edit generated state.

## 11. Risks, Assumptions, and Open Questions

### 11.1 Risks

| ID | Risk | Likelihood | Impact | Treatment | Owner / Task |
| --- | --- | --- | --- | --- | --- |
| R-001 | A prose-only change silently changes binary, provider, or schema bytes during successor copying. | medium | high | Explicit equality/delivery-surface tests and a no-build-script invariant. | T1 |
| R-002 | Activation changes catalog/default but leaves mutable family pointers or generated producer state stale. | medium | medium | T2 owns the complete current-pointer census and reconcile/selection proof. | T2 |
| R-003 | Wording could imply that an MCP escaping workaround is supported. | low | medium | Require an explicit no-MCP-path statement and negative text assertions. | T1–T2 |

### 11.2 Assumptions

| ID | Assumption | Impact if False |
| --- | --- | --- |
| A-001 | The 1.2 cut can retain the full 1.1 delivery/config/provider surface while changing skill/reference documentation and version-bearing artifacts only. | Stop T1 and obtain an owner decision before changing behavior or extending the package contract. |
| A-002 | The v5.19 release has authority to activate 1.2 after the candidate proof. | Leave T1 unadvertised and do not begin T2 until release coordination confirms activation. |

### 11.3 Open Questions

None. The `gh`/REST versus MCP decision is settled by #169 and the approved package specification; no external MCP capability is needed for this plan.

## 12. Final Verification

- T1 and T2 checkpoints each carry valid `Plan-*` identity trailers and the durable plan validates against the repository bridge.
- Every REQ-001–REQ-005 maps to passing Appendix B evidence.
- Package integrity, graph, schemas, source projection, rendered catalog, catalog roles, exact/default resolution, and scoped Markdown checks pass.
- Candidate-wheel dogfood and the full serial gate run only at the release-prep state that can resolve the target version; otherwise record the expected resolution boundary without weakening final verification.
- The final diff contains no 1.0/1.1 mutation, Go/source/binary change, organization schema change, consumer change, ADR, or manual generated-state edit.

## 13. Close-out

- **Completed:** pending.
- **Decisions / deviations harvested:** record #169's MCP-first retirement in the release changelog; no ADR is created or amended.
- **Risks closed / accepted:** pending final binary/predecessor and activation proof.
- **Deferred/discovered work filed:** a future MCP transport requires a new approved design/specification and issue; it is not a continuation of this documentation cut.
- **Source/ADR/handoff reconciliation:** release closeout owns handoff/issue updates; #162's ADR corpus freeze receives no #169 record.
- **Scratch teardown:** only after all checkpoint evidence is committed and no recovery information remains solely in `.project-pipeline`.

## Appendix A. Interface and State Contracts

| Contract | Owner / Producer Task | Consumer(s) | Current | Planned / States | Errors / Limits | Compatibility / Invariant | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `github-workflow-label-routing-v1` | T1 | Delivered agents / T2 | No label guidance. | Three categorization namespaces; six prohibited shadow namespaces/derived label. | A forbidden label is a documentation refusal, not a runtime schema mutation. | Typed fields and Ready derivation remain sole operational authority. | #169 |
| `github-workflow-field-independence-v1` | T1 | Delivered agents | One worked pair. | Six explicit pairwise counterexamples. | Each pair must be independently represented. | Field names/values/pinning unchanged. | #169 |
| `github-workflow-1.2-selection-v1` | T2 | Catalog resolver / consumers | 1.1 default; 1.0 retained. | 1.2 default; 1.1 and 1.0 retained. | Missing/digest-mismatched payload fails package validation. | Exact selectors remain exact; released rows permanent. | `meta/versioning.md` |

## Appendix B. Requirement-to-Proof Traceability

| Proof ID | Requirement(s) | Task | Method | Oracle | Command / Procedure | Expected Result | Negative Control | Environment | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PV-T1-001 | REQ-001–REQ-004 | T1 | RED/targeted package contract/integrity/projection | #169 text, 1.1 predecessor bytes, V2 manifest/family parser | `uv run pytest tests/package_contract/test_github_workflow_1_2.py`; Tier 1 package/graph/projection checks | RED fails for missing 1.2 requirements; GREEN proves all routes/examples, immutable predecessors, byte-identical binary, complete/indexed/projected candidate, unadvertised role. | Omit a pair/namespace, alter binary, add MCP wording, or rewrite 1.1. | local checkout; direct local Git metadata checks | ephemeral |
| PV-T2-001 | REQ-003–REQ-005 | T2 | catalog/reconcile/selection and release-record contract | catalog roles, resolver behavior, reconciliation-owned state, changelog | targeted activation tests; `uv run project-standards reconcile --apply`; Tier 1 validators; scoped Markdown checks | 1.2 default, 1.1/1.0 retained/exact-selectable, generated files converge, changelog retires MCP-first without implying support. | Keep 1.1 default, remove retained row, hand-edit generated output, or create ADR/MCP path. | local checkout; Git/history commands direct local | ephemeral |

## Appendix C. Durable Evidence

Not applicable: targeted tests, validators, generated-state diff review, and task checkpoint commits are inexpensive and reproducible from the committed repository.

## Appendix D. Deferred Work

| Item | Reason Deferred | Follow-up / Reopen Trigger |
| --- | --- | --- |
| GitHub MCP transport or body round-trip guidance | #169 selects retirement of MCP-first rather than implementation; no MCP read path is supported. | A new approved design/specification that selects an MCP transport and defines its security/escaping contract. |
