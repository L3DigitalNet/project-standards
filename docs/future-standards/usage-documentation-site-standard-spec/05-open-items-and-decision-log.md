---
spec_id: SPEC-U005
title: 'Usage Documentation Site Open Items and Decision Log Specification'
status: draft
profile: standard
owner: 'Project standards / repository template'
implementer: 'coding agent'
created: '2026-07-08'
last_reviewed: '2026-07-08'
supersedes: null
superseded_by: null
related:
  adrs: []
  tickets: []
  repositories:
    - 'L3DigitalNet/project-standards'
  prior_specs: []
---

# Usage Documentation Site Open Items and Decision Log — Specification (Standard)

## Revision History

| Version | Date       | Author  | Change                                         |
| ------- | ---------- | ------- | ---------------------------------------------- |
| 0.1     | 2026-07-08 | ChatGPT | Initial conformant Project Specification draft |

**Spec lifecycle:** This document is living until `approved`, then change-controlled. Implementation deviations are recorded in the Deviations Log, not silently patched into requirements.

---

## 1. Purpose & Background

Track accepted decisions, open questions, and implementation-control requirements for the usage-site standard while keeping the tracking document itself conformant to the Project Specification Standard.

---

## 2. Scope

### 2.1 In Scope

- Decision log maintenance.
- Open question tracking.
- Deferred work classification.
- Deviation handling.
- Release-readiness checklist.

### 2.2 Out of Scope (Non-Goals — never)

| ID | Non-Goal | Reason |
| --- | --- | --- |
| NG-001 | Replacing developer documentation, ADRs, project specs, or handoff systems | The new standard is strictly for user-facing usage documentation sites. |
| NG-002 | Creating a hosted public documentation platform | The standard governs repo-local local-browser sites only. |
| NG-003 | Replacing issue tracking or project boards | This spec captures standard-level decisions, not every implementation task. |

### 2.3 Won't Have in v1 (deferred — not never)

| ID | Deferred Capability | Why Deferred | Revisit When |
| --- | --- | --- | --- |
| WH-001 | Full prose-style linting with Vale | Useful but subjective and likely noisy in v1 | Repeated content-quality drift appears |
| WH-002 | External link checking as a required gate | Network checks are flaky in CI | A stable allowlist and retry policy exists |

### 2.4 Boundaries

| Boundary | Description |
| --- | --- |
| Distributor owns | `project-standards` standard text, templates, schemas, validators, registry entries, tests, and dogfood example. |
| Consuming repo owns | Actual tool-specific usage content and local adoption ADRs. |
| External platform owns | GitHub Issues UI and permissions; MkDocs and Material runtime behavior. |

---

## 3. Context

### 3.1 Current State

The earlier decision log is a simple Markdown list. It captures useful decisions but lacks Project Specification frontmatter, traceability, and standard sections.

### 3.2 Target State

Open items and decisions are captured in a conformant spec that can be validated with the rest of the bundle and used by implementation agents without losing decision history.

### 3.3 Assumptions

| ID | Assumption | Impact if False |
| --- | --- | --- |
| A-001 | Consuming repositories can install MkDocs and Material as development dependencies. | Adoption must document a non-Python invocation equivalent. |
| A-002 | GitHub issue forms are acceptable feedback intake for repositories that use GitHub Issues. | The feedback mechanism must be optional or repo-local alternatives must be documented. |

### 3.4 Constraints

| ID | Constraint | Source |
| --- | --- | --- |
| C-001 | Do not conflict with Markdown Frontmatter validation. | Markdown Frontmatter Standard |
| C-002 | Do not conflict with `docs/usage.md` in the existing CLI Documentation Standard. | CLI Documentation Standard |
| C-003 | Every governed standard must be dogfooded by the distributor repository. | Owner decision in this task |

---

## 4. Goals

| ID | Goal | Success Signal | Achieved By |
| --- | --- | --- | --- |
| G-001 | Preserve decision history | Accepted decisions are visible and traceable | FR-001 |
| G-002 | Keep open items actionable | Each open question has owner, needed-by, and blocking status | FR-002 |
| G-003 | Control deviations | Implementation deviations are recorded, not hidden | FR-003 |

---

> **§5 (Stakeholders and Users) is Full-tier** and is intentionally omitted at the Standard profile.

## 6. Glossary

| Term | Definition | Notes |
| --- | --- | --- |
| Distributor repository | `L3DigitalNet/project-standards`, the source of truth for standards and adoption artifacts. | Not the same as a consuming repository. |
| Consuming repository | A repository that adopts one or more standards from `project-standards`. | Owns its local content and deviations. |
| Usage documentation site | A repo-local MkDocs and Material site for user-facing instructions about using tools. | Not developer documentation. |
| Dogfood adoption | The distributor repository adopts and validates the standard it governs. | Required as interoperability proof. |
| Decision log | A table of accepted or rejected design choices for this standard. | Not a replacement for ADRs when a decision is costly to reverse. |
| Open item | A question or deferred decision that must be resolved or consciously deferred. | Tracked with `OQ-` rows. |

---

## 7. Requirements

### 7.1 Functional Requirements

| ID | Requirement | Rationale | Acceptance Criteria | Priority |
| --- | --- | --- | --- | --- |
| FR-001 | The system shall preserve accepted decisions from the earlier planning bundle. | The implementation should not lose design rationale. | Decision rows are present in §8.3 or §21. | Must |
| FR-002 | The system shall track open questions with current assumption, blocking status, owner, needed-by milestone, and status. | Agents need clear authority to proceed or stop. | Open question table contains required columns. | Must |
| FR-003 | The system shall track deviations with spec reference, deviation, reason, and approval status. | Deviations must be explicit. | Deviations Log is present and maintained. | Must |
| FR-004 | The system shall classify future work as open question, deferred capability, or deviation rather than loose prose. | Consistent classification prevents drift. | No untracked TODO list remains in released spec. | Should |

### 7.2 Non-Functional Requirements

| ID | Category | Requirement | Measurement / Acceptance Criteria | Priority |
| --- | --- | --- | --- | --- |
| NFR-001 | Maintainability | The implementation shall avoid creating parallel governance, validation, or instruction systems. | Review confirms reuse of existing standards patterns. | Must |
| NFR-002 | Interoperability | The implementation shall pass alongside all other governed standards in the distributor repository. | Full repository validation gate passes. | Must |
| NFR-003 | Usability | The adopted site shall be viewable in a local browser with one documented command. | `mkdocs serve` command works from the repository root. | Must |

### 7.3 Interface Requirements

| ID | Interface | Requirement | Contract / Format | Acceptance Criteria |
| --- | --- | --- | --- | --- |
| IR-001 | project-standards CLI | The system shall expose the standard through `project-standards list` and adoption through `project-standards adopt usage-documentation-site`. | Existing adopt/list conventions | Commands return expected output. |
| IR-002 | MkDocs site | The system shall expose a local browser-readable documentation site from `docs/usage/mkdocs.yml`. | MkDocs config contract | Strict build passes. |
| IR-003 | GitHub issue form | The system shall expose section feedback through `.github/ISSUE_TEMPLATE/tool-feedback.yml`. | GitHub issue-form contract | Prefilled fields match the JavaScript contract. |

### 7.4 Data Requirements

| ID | Data Entity | Requirement | Validation Rules | Ownership |
| --- | --- | --- | --- | --- |
| DR-001 | Standard bundle files | The system shall store governing standard text, adoption runbook, examples, templates, resources, and schemas in the standards bundle. | Paths match bundle anatomy. | Distributor repository |
| DR-002 | Adopt bundle files | The system shall store copy-adopt artifacts under the packaged adopt bundle. | Manifest paths resolve and tests pass. | Distributor repository |
| DR-003 | Usage site files | The system shall store dogfood and consumer site files under `docs/usage/`. | Generated output ignored; content pages managed. | Consuming repository or dogfood repository |
| DR-004 | Decision and open-item rows | The system shall store decision and open-item state in spec tables until resolved. | Rows use canonical ID prefixes and valid widths. | Spec bundle |

---

## 8. Architecture and Design

### 8.1 Architecture Summary

This document converts the prior open-items file into a valid Standard-profile spec. Decisions are split between design decisions and open questions, while unresolved issues remain explicit in §21.

### 8.2 Architecture Views

#### 8.2.1 Context View

```mermaid
flowchart LR
    Maintainer[Maintainer] --> StandardsRepo[project-standards repository]
    StandardsRepo --> StandardsBundle[standards bundle]
    StandardsRepo --> AdoptBundle[adopt bundle]
    ConsumerRepo[Consuming repository] --> AdoptBundle
    ConsumerRepo --> UsageSite[docs/usage site]
    UsageSite --> GitHubIssues[GitHub issue feedback]
```

#### 8.2.2 Container / Deployment View

```mermaid
flowchart LR
    CLI[project-standards CLI] --> Registry[contract registry]
    CLI --> AdoptEngine[adopt engine]
    AdoptEngine --> Templates[copy-adopt templates]
    MkDocs[MkDocs strict build] --> Content[docs/usage/content]
    Content --> Browser[local browser]
```

#### 8.2.3 Component View

| Component | Responsibility | Interfaces | Notes |
| --- | --- | --- | --- |
| Decision rows | Accepted design choices | §8.3 and §21 | Traceable by `D-` IDs |
| Open question rows | Unresolved choices | §21 | Traceable by `OQ-` IDs |
| Deviation rows | Implementation divergences | Deviations Log | Traceable by `DEV-` IDs |

### 8.3 Design Decisions

| ID | Decision | Rationale | Alternatives Considered | ADR |
| --- | --- | --- | --- | --- |
| D-001 | Accepted decisions belong in §8.3 and §21 rather than an ad hoc table only. | Project Spec tooling understands these sections. | Keep separate nonconformant decision log; rejected. | TBD local ADR |
| D-002 | Blocking open questions halt affected work. | Agent implementation contract requires deterministic stop points. | Let agents guess; rejected. | TBD local ADR |

> **§8.4 (Solution Alternatives Considered) is Full-tier** and is intentionally omitted at the Standard profile.

### 8.5 Design Constraints

- The implementation must follow existing `project-standards` bundle, registry, and validation conventions.
- The implementation must not create a second governance system outside existing standards, ADR, and Project Specification mechanisms.
- The implementation must keep user-facing usage content separate from developer, specification, ADR, and handoff content.

> **§8.6 (Dependency Policy) is Full-tier** and is intentionally omitted at the Standard profile.

---

## 9. Data Model

The system owns repository files, configuration keys, schema files, and validation findings rather than runtime application data. Persistent state is Git history and the files committed to the distributor or consuming repository.

| ID | Data Entity | Requirement | Validation Rules | Ownership |
| --- | --- | --- | --- | --- |
| DR-001 | Standard bundle files | The system shall store governing standard text, adoption runbook, examples, templates, resources, and schemas in the standards bundle. | Paths match bundle anatomy. | Distributor repository |
| DR-002 | Adopt bundle files | The system shall store copy-adopt artifacts under the packaged adopt bundle. | Manifest paths resolve and tests pass. | Distributor repository |
| DR-003 | Usage site files | The system shall store dogfood and consumer site files under `docs/usage/`. | Generated output ignored; content pages managed. | Consuming repository or dogfood repository |
| DR-004 | Decision and open-item rows | The system shall store decision and open-item state in spec tables until resolved. | Rows use canonical ID prefixes and valid widths. | Spec bundle |

---

## 10. Behavior and Workflows

### 10.1 Primary Workflow

```mermaid
sequenceDiagram
    actor Maintainer
    participant Spec
    participant Repo as project-standards
    participant Consumer as Consuming repository
    Maintainer->>Spec: Approve implementation scope
    Spec->>Repo: Implement standard bundle and validator support
    Repo->>Repo: Dogfood the standard
    Repo->>Consumer: Distribute adoptable artifacts
    Consumer-->>Repo: Feedback through issue form when docs are used
```

Steps:

1. Review accepted decisions from prior planning bundle.
2. Map them into design decision rows.
3. Review open items and classify blocking status.
4. Update traceability and milestones.
5. Resolve or defer open questions before release.

Expected result:

> The distributor repository contains a tested, registered, dogfooded `usage-documentation-site` standard that consuming repositories can adopt consistently.

### 10.2 Alternate Workflows

| ID | Trigger | Behavior | Expected Result |
| --- | --- | --- | --- |
| AW-001 | Use GitHub issues only | Move all decisions out of the spec | Rejected because implementation agents need context in the spec |
| AW-002 | Use ADR for every decision | Create many ADRs for routine implementation choices | Rejected because only costly decisions need ADRs |

### 10.3 Edge Cases

| ID | Edge Case | Expected Behavior |
| --- | --- | --- |
| EC-001 | Decision later changes | Add a new decision row or ADR and mark old decision superseded in prose |
| EC-002 | Open item becomes blocker | Set blocking status to Yes and halt affected milestone |

### 10.4 State Transitions

| State | Meaning | Entry Condition | Exit Condition |
| --- | --- | --- | --- |
| Open | Question unresolved | Owner answers or defers | Answered or Deferred |
| Accepted | Decision active | Superseding decision occurs | Superseded |
| Deviation Pending | Deviation awaiting approval | Owner approves or rejects | Approved or Rejected |

---

## 11. UI Pages / API Endpoints

This work has no hosted UI or API surface. The relevant user surfaces are local MkDocs pages, GitHub issue forms, and CLI commands.

| Page or Endpoint | Purpose | Key Actions | Authorization |
| --- | --- | --- | --- |
| §21 table | Open item tracking | Read and update statuses | Maintainer or agent |
| Deviations Log | Deviation tracking | Record divergence | Implementer |

**Accessibility & i18n:** v1 targets readable local-browser documentation in English. Formal localization is out of scope, but the content must avoid encoding implementation-only jargon into user-facing pages.

---

## 12. Error Handling and Recovery

### 12.1 Expected Failures

| ID | Failure Mode | User/System Behavior | Logging / Observability | Recovery |
| --- | --- | --- | --- | --- |
| ERR-001 | Untracked decision | Agent acts on unstated assumption | Review finds missing row | Add OQ or D row |
| ERR-002 | Unapproved deviation | Implementation diverges silently | Completion report reveals mismatch | Record DEV row and seek approval |

### 12.2 Retry and Idempotency

Adoption must remain idempotent. Existing file artifacts are skipped unless the operator explicitly passes `--force`; fragments are reported for manual merging. Validation commands must be safe to rerun.

### 12.3 Rollback / Recovery

Rollback is Git-based. Revert the implementation commit, remove generated scratch output, and rerun the repository validation gate. Consuming repositories recover by reverting the adoption commit or deleting the `docs/usage/` subtree and issue form if adoption was not yet accepted.

---

## 13. Security and Privacy

### 13.1 Authentication

GitHub authentication is required only for repository writes and issue creation in private repositories. Local MkDocs preview does not require authentication.

### 13.2 Authorization

| Actor / Role | Allowed Actions | Denied Actions |
| --- | --- | --- |
| Maintainer | Create and merge standard implementation changes | Bypass required validation without documented deviation |
| Consuming repo user | Read and use docs, submit feedback issues | Change distributor standard unless authorized |

### 13.3 Secrets

| Secret | Storage Location | Access Pattern | Rotation / Notes |
| --- | --- | --- | --- |
| GitHub token for CI | GitHub Actions secret or app token | Workflow only | Managed by repository policy; never documented in usage pages |

### 13.4 Sensitive Data

| Data | Classification | Storage | Transmission | Retention |
| --- | --- | --- | --- | --- |
| Issue feedback content | Internal or public depending on repo | GitHub Issues | GitHub web/API | Repository issue policy |

### 13.5 Threats and Mitigations

| Threat | Impact | Mitigation |
| --- | --- | --- |
| Prompt injection through docs or issue content | Future agents may treat user-facing prose or feedback as instructions. | Agent-instruction fragments must classify docs and issues as data, not authority. |
| Private repository feedback leakage | Prefilled local URLs or issue content may expose internal context. | Only path, section, anchor, URL, and user-provided fields are captured; no secrets are added. |

### 13.6 Hardening Checklist

- [ ] GitHub issue-form labels and permissions reviewed.
- [ ] Feedback links do not leak secrets.
- [ ] Generated site output is not committed.
- [ ] CI uses pinned project-standards release refs where reusable workflows are involved.

---

> **Sections §14 (Capacity and Scale Assumptions), §15 (Risks), and §16 (Compliance, Licensing, and Data Rights) are Full-tier** and are intentionally omitted at the Standard profile.

## 17. Testing and Acceptance

### 17.1 Definition of Done

- [ ] All Must requirements implemented.
- [ ] Registry, adopt, validation, and dogfood tests pass.
- [ ] The standard documentation and templates are validated or intentionally excluded according to repository policy.
- [ ] The `project-standards` repository adopts and dogfoods the new usage documentation site.
- [ ] Compatibility text is added to affected sibling standards.
- [ ] Deviations Log reviewed and accepted by owner.

### 17.2 Test Strategy

| Layer | Scope | Required Coverage | Required? |
| --- | --- | --- | --- |
| Unit / domain | registry, manifest, schema helper, and validator logic | success and failure cases | Yes |
| Integration / adapter | adopt dry-run and scratch-repo adoption | expected artifacts and idempotency | Yes |
| Snapshot / contract | template and schema fixtures | controlled output diff reviewed intentionally | Yes |
| End-to-end | dogfood MkDocs strict build | site builds and feedback assets are present | Yes |

### 17.3 Requirement-to-Test Traceability

| Requirement ID | Test / Verification Method                     | Status      |
| -------------- | ---------------------------------------------- | ----------- |
| FR-001         | Decision log review against previous bundle    | Not Started |
| FR-002         | Open question table column review              | Not Started |
| FR-003         | Deviations Log present and populated           | Not Started |
| FR-004         | Search for loose TODO markers in released spec | Not Started |

---

## 18. Deployment and Operations

### 18.1 Runtime Environment

| Item | Value |
| --- | --- |
| Runtime | Python package plus Node-free MkDocs runtime from Python dependencies |
| OS / Platform | Linux CI and local developer machines |
| Datastore | Git repository files only |
| External services | GitHub Issues for feedback intake |

Runtime services:

| Service | Purpose | Start Mode | Health Signal |
| --- | --- | --- | --- |
| MkDocs local server | Preview usage docs locally | Manual command | Browser loads local site |
| GitHub Issues | Capture section feedback | Hosted by GitHub | Issue form opens with prefilled context |

### 18.2 Configuration

| Setting | Required? | Default | Description |
| --- | --- | --- | --- |
| usage_documentation_site.version | Yes | 1.0 | Contract marker in `.project-standards.yml` |
| docs/usage/mkdocs.yml | Yes | provided by template | MkDocs site configuration |
| tool-feedback.yml | Yes | provided by template | GitHub issue-form contract |

**Environment matrix** — differences between environments:

| Aspect | Dev | Staging | Prod |
| --- | --- | --- | --- |
| Secrets source / auth / external APIs | Local Git checkout | GitHub repository with CI | GitHub repository with released tag |

### 18.3 Deployment Flow

1. Implement the standard bundle, adopt bundle, registry updates, validators, tests, and dogfood site in one branch.
2. Run the full repository validation gate.
3. Review generated or adopted files for accidental developer-content leakage into user-facing docs.
4. Merge to `main` after checks pass.
5. Cut the appropriate `project-standards` release according to `meta/versioning.md`.
6. Consumers adopt from the released tag.
7. Rollback by reverting the release commit before retagging if the release has not been published; after publication, follow release-policy correction guidance.

> **§18.4 (Rollout Controls) is Full-tier** and is intentionally omitted at the Standard profile.

### 18.5 Observability

Minimum signals:

- `project-standards list` shows the new standard.
- `project-standards adopt usage-documentation-site --dry-run` reports expected artifacts.
- `project-standards validate --config .project-standards.yml` passes.
- `project-standards spec validate --config .project-standards.yml` passes for these specs when included.
- `mkdocs build --strict -f docs/usage/mkdocs.yml` passes after dogfood adoption.

| Alert | Trigger | Severity | Owner / Action |
| --- | --- | --- | --- |
| Usage-site validation failure | A required validation command fails | Warning | Fix the standard or record a deviation before release |

### 18.6 Backup and Disaster Recovery

The system owns no external durable runtime data. Git history is the recovery mechanism for standard text, templates, schemas, and code.

### 18.7 Documentation Deliverables

Checklist tied to the DoD:

- [ ] Conformant decision and open-item spec.
- [ ] Updated master spec references.
- [ ] Resolved or explicitly deferred open items before release.

---

## 19. Implementation Plan

### MS-0 — Convert

1. Prior decision log converted.
2. Spec validates structurally.

### MS-1 — Classify

1. Open items categorized.
2. Blocking status is set.

### MS-2 — Resolve

1. Release-blocking items closed.
2. No blockers remain for implementation.

### Milestone Summary

| Milestone | Deliverable | Exit Criteria |
| --- | --- | --- |
| MS-0 Convert | Prior decision log converted | Spec validates structurally |
| MS-1 Classify | Open items categorized | Blocking status is set |
| MS-2 Resolve | Release-blocking items closed | No blockers remain for implementation |

---

> **§20 (Success Evaluation) is Full-tier** and is intentionally omitted at the Standard profile.

## 21. Open Questions and Decisions

| ID | Question | Current Assumption | Blocking? | Owner | Needed By | Status |
| --- | --- | --- | --- | --- | --- | --- |
| OQ-001 | Which decisions require formal ADRs in addition to spec rows? | Only dogfood adoption and any standards-conflict exception likely need ADRs. | No | Owner | MS-2 | Open |
| OQ-002 | Should the tag vocabulary include both `usage` and `workflow`? | Yes; define distinct meanings to avoid overlap. | No | Owner | MS-1 | Open |

---

## Deviations Log

| ID      | Spec Reference | Deviation                            | Reason | Approved? |
| ------- | -------------- | ------------------------------------ | ------ | --------- |
| DEV-001 | None           | No deviations recorded in this draft | N/A    | Pending   |

---

## References

### Standards

- Project Specification Standard.
- Markdown Frontmatter Standard.
- Markdown Tooling Standard.
- Python Tooling SSOT Standard.
- ADR Standard.
- CLI Documentation Standard.

### Project References

- usage-documentation-site-standard-spec/05-open-items-and-decision-log.md
- standards/adr/README.md

---

## Appendix A: ID Conventions

Stable IDs allow requirements to be referenced from commits, tests, issues, ADRs, and review comments. Section numbers match the Project Specification Standard's Standard profile.

| Prefix | Meaning                     | Defined In     |
| ------ | --------------------------- | -------------- |
| `G-`   | Goal                        | §4             |
| `NG-`  | Non-goal (never)            | §2.2           |
| `WH-`  | Won't have in v1 (deferred) | §2.3           |
| `A-`   | Assumption                  | §3.3           |
| `C-`   | Constraint                  | §3.4           |
| `FR-`  | Functional requirement      | §7.1           |
| `NFR-` | Non-functional requirement  | §7.2           |
| `IR-`  | Interface requirement       | §7.3           |
| `DR-`  | Data requirement            | §7.4           |
| `D-`   | Design decision             | §8.3           |
| `AW-`  | Alternate workflow          | §10.2          |
| `EC-`  | Edge case                   | §10.3          |
| `ERR-` | Error-handling requirement  | §12.1          |
| `MS-`  | Milestone                   | §19            |
| `OQ-`  | Open question               | §21            |
| `DEV-` | Deviation                   | Deviations Log |

The `R-` prefix is Full-tier and is not used at the Standard profile. Priority values are column values, not ID prefixes; IDs never change when priorities do.

---

## Appendix B: Agent Implementation Contract

Binding when this spec is implemented by a coding agent.

### B.1 Implementation Rules

The implementer shall:

- read this entire specification before making changes;
- preserve all explicit non-goals, won't-haves, constraints, and design constraints;
- treat Must requirements as mandatory and blocking open questions as hard stops for affected work;
- record any underspecified behavior as an `OQ-` row with a proposed default assumption;
- record any implementation divergence as a `DEV-` row rather than adapting silently;
- add or update tests for every implemented requirement;
- keep §17.3 current as completion evidence;
- follow the milestone order in §19;
- prefer small, reviewable changes.

### B.2 Prohibited Behaviors

The implementer shall not:

- invent requirements not present in this spec;
- remove existing behavior unless explicitly required;
- introduce external services or dependencies not agreed with the owner without an approved open question;
- store secrets in source control or print them in CI logs;
- ignore failing tests unrelated to the change without documenting them;
- treat examples as exhaustive or normative unless explicitly stated;
- mark a requirement complete without a verification entry in §17.3.

### B.3 Required Completion Report

At completion, provide:

- summary of changes and files changed;
- requirements implemented, each mapped to the test or command that proves it;
- tests added or changed;
- deviations and their approval status;
- known limitations and remaining open questions;
- documentation deliverables completed.

### B.4 Session Handoff

For multi-session implementations, record current milestone, in-progress requirement IDs, and unresolved open questions or deviations in the repository's session-state or handoff documents according to repository convention.

---

> **Appendix C (Optional Modules) is Full-tier** and is intentionally omitted at the Standard profile.

## Appendix D: Tailoring

This specification uses the Standard profile because the change spans one repository, several standards, packaged CLI behavior, validation machinery, and dogfooding requirements, but it does not introduce durable runtime data or external production services.

| Profile | Use For | Decision |
| --- | --- | --- |
| Light | Small single-session changes | Too small for this standard addition. |
| Standard | Typical feature or standards-bundle work | Selected. |
| Full | Multi-service systems, durable data, or external integrations | Not required for this change. |

Upgrade to Full only if the implementation introduces a durable service, external integration, release orchestration system, or substantial runtime data model beyond standard repository files.
