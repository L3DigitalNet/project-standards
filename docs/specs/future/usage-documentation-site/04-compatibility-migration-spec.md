---
spec_id: SPEC-U004
title: 'Usage Documentation Site Compatibility and Migration Specification'
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

# Usage Documentation Site Compatibility and Migration — Specification (Standard)

## Revision History

| Version | Date       | Author  | Change                                         |
| ------- | ---------- | ------- | ---------------------------------------------- |
| 0.1     | 2026-07-08 | ChatGPT | Initial conformant Project Specification draft |

**Spec lifecycle:** This document is living until `approved`, then change-controlled. Implementation deviations are recorded in the Deviations Log, not silently patched into requirements.

---

## 1. Purpose & Background

Define the compatibility amendments and migration steps required so `usage-documentation-site` can coexist with every governed standard in `project-standards` without conflicting authority or validation behavior.

---

## 2. Scope

### 2.1 In Scope

- Markdown Frontmatter compatibility.
- CLI Documentation path compatibility.
- Markdown Tooling body-model compatibility.
- Python Tooling gate integration.
- Project Specification separation.
- ADR adoption-decision placement.
- Versioning and registry updates.
- Dogfood migration from `docs/usage.md` into `docs/usage/`.

### 2.2 Out of Scope (Non-Goals — never)

| ID | Non-Goal | Reason |
| --- | --- | --- |
| NG-001 | Replacing developer documentation, ADRs, project specs, or handoff systems | The new standard is strictly for user-facing usage documentation sites. |
| NG-002 | Creating a hosted public documentation platform | The standard governs repo-local local-browser sites only. |
| NG-003 | Rewriting unrelated standards wholesale | Only compatibility amendments needed for this standard should be made. |

### 2.3 Won't Have in v1 (deferred — not never)

| ID | Deferred Capability | Why Deferred | Revisit When |
| --- | --- | --- | --- |
| WH-001 | Full prose-style linting with Vale | Useful but subjective and likely noisy in v1 | Repeated content-quality drift appears |
| WH-002 | External link checking as a required gate | Network checks are flaky in CI | A stable allowlist and retry policy exists |
| WH-003 | Immediate removal of `docs/usage.md` without compatibility window | Existing CLI docs standard and examples reference it | Migration path is approved and examples updated |

### 2.4 Boundaries

| Boundary | Description |
| --- | --- |
| Distributor owns | `project-standards` standard text, templates, schemas, validators, registry entries, tests, and dogfood example. |
| Consuming repo owns | Actual tool-specific usage content and local adoption ADRs. |
| External platform owns | GitHub Issues UI and permissions; MkDocs and Material runtime behavior. |

---

## 3. Context

### 3.1 Current State

The existing standards were authored before the usage-site standard. The CLI Documentation Standard currently names `docs/usage.md`; Markdown Frontmatter and Markdown Tooling already own adjacent concerns; Project Specification uses its own schema and validates separately.

### 3.2 Target State

Every affected standard states a non-conflicting relationship to the new usage-site standard. The distributor repository dogfoods the new standard without losing existing CLI documentation guarantees.

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
| G-001 | Resolve all standards conflicts before release | Compatibility checklist has no unresolved blockers | FR-001, FR-002, FR-003 |
| G-002 | Preserve existing content contracts | CLI command documentation remains complete after migration | FR-004 |
| G-003 | Prove dogfood migration | Distributor usage site builds and old path is handled intentionally | FR-006 |

---

> **§5 (Stakeholders and Users) is Full-tier** and is intentionally omitted at the Standard profile.

## 6. Glossary

| Term | Definition | Notes |
| --- | --- | --- |
| Distributor repository | `L3DigitalNet/project-standards`, the source of truth for standards and adoption artifacts. | Not the same as a consuming repository. |
| Consuming repository | A repository that adopts one or more standards from `project-standards`. | Owns its local content and deviations. |
| Usage documentation site | A repo-local MkDocs and Material site for user-facing instructions about using tools. | Not developer documentation. |
| Dogfood adoption | The distributor repository adopts and validates the standard it governs. | Required as interoperability proof. |
| Canonical usage surface | The documentation location considered authoritative for user-facing usage content. | Must not be ambiguous. |

---

## 7. Requirements

### 7.1 Functional Requirements

| ID | Requirement | Rationale | Acceptance Criteria | Priority |
| --- | --- | --- | --- | --- |
| FR-001 | The implementation shall amend CLI Documentation to allow site-contained CLI usage references when this standard is adopted. | Avoids conflict with `docs/usage.md`. | CLI Documentation contains compatibility text. | Must |
| FR-002 | The implementation shall keep Markdown Frontmatter as metadata authority for rendered usage pages. | Avoids a parallel metadata schema. | Usage pages validate with canonical frontmatter. | Must |
| FR-003 | The implementation shall keep Markdown Tooling as Markdown body and structured-text formatting authority. | Avoids duplicate formatter/linter rules. | No usage-site rule contradicts Prettier or markdownlint defaults. | Must |
| FR-004 | The implementation shall integrate usage-site checks with Python Tooling verification rather than replacing that gate. | Python repos need one obvious aggregate gate. | Dogfood check command includes usage-site validation or documents separate docs gate. | Must |
| FR-005 | The implementation shall keep local adoption ADRs under `docs/decisions/`. | ADR Standard owns adoption-decision storage. | Adoption runbook and dogfood plan use `docs/decisions/`. | Must |
| FR-006 | The implementation shall choose and document the distributor migration strategy for existing `docs/usage.md`. | Dogfooding makes path ambiguity visible. | Strategy is merged and validation passes. | Must |

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
| DR-004 | Existing CLI usage reference | The system shall migrate or preserve `docs/usage.md` according to an explicit compatibility plan. | No ambiguous canonical usage surface remains. | Distributor repository |

---

## 8. Architecture and Design

### 8.1 Architecture Summary

Compatibility work is a set of narrow amendments. The new standard should not absorb sibling standards. It should define how its site layout composes with their existing authorities and then dogfood that composition in the distributor repository.

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
| CLI Documentation amendment | Explains site-aware usage-reference location | Standard README and adopt runbook | Prevents `docs/usage.md` ambiguity |
| Frontmatter alignment | Usage pages use canonical metadata | Usage page templates | Prevents validation conflict |
| Dogfood migration | Moves or cross-links existing CLI reference | `docs/usage/` and possibly `docs/usage.md` | Proves interoperability |

### 8.3 Design Decisions

| ID | Decision | Rationale | Alternatives Considered | ADR |
| --- | --- | --- | --- | --- |
| D-001 | Site standard owns location; CLI Documentation owns CLI content substance. | This separates site UX from command-reference semantics. | Make one standard supersede the other entirely; rejected. | TBD local ADR |
| D-002 | Local adoption ADRs remain in `docs/decisions/`. | ADR Standard already owns that convention. | Place governance under `docs/usage/`; rejected. | TBD local ADR |

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
| DR-004 | Existing CLI usage reference | The system shall migrate or preserve `docs/usage.md` according to an explicit compatibility plan. | No ambiguous canonical usage surface remains. | Distributor repository |

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

1. Inventory current standards interactions.
2. Apply compatibility text to affected standards.
3. Choose dogfood migration path for existing `docs/usage.md`.
4. Adopt site standard in distributor repository.
5. Run validators for every governed standard.

Expected result:

> The distributor repository contains a tested, registered, dogfooded `usage-documentation-site` standard that consuming repositories can adopt consistently.

### 10.2 Alternate Workflows

| ID | Trigger | Behavior | Expected Result |
| --- | --- | --- | --- |
| AW-001 | Keep two canonical usage surfaces | Leave `docs/usage.md` and `docs/usage/` both active | Rejected because authority is ambiguous |
| AW-002 | Exclude usage pages from frontmatter validation | Avoid canonical metadata work | Rejected because governed docs should validate by default |

### 10.3 Edge Cases

| ID | Edge Case | Expected Behavior |
| --- | --- | --- |
| EC-001 | Existing consumers use `cli-documentation` only | They continue using `docs/usage.md` under current contract |
| EC-002 | Consumers adopt both standards | Site layout becomes allowed canonical location for CLI usage reference |

### 10.4 State Transitions

| State | Meaning | Entry Condition | Exit Condition |
| --- | --- | --- | --- |
| Legacy | Only `docs/usage.md` exists | Site standard adopted | Dual |
| Dual | Both surfaces exist during migration | Canonical decision made | Site Canonical |
| Site Canonical | `docs/usage/` is authoritative | Old reference deprecated or redirected | Maintained |

---

## 11. UI Pages / API Endpoints

This work has no hosted UI or API surface. The relevant user surfaces are local MkDocs pages, GitHub issue forms, and CLI commands.

| Page or Endpoint | Purpose | Key Actions | Authorization |
| --- | --- | --- | --- |
| Standards README | Compatibility explanation | Read sibling relationships | Maintainer |
| Dogfood usage site | Proof of interoperability | Browse local site | User or maintainer |

**Accessibility & i18n:** v1 targets readable local-browser documentation in English. Formal localization is out of scope, but the content must avoid encoding implementation-only jargon into user-facing pages.

---

## 12. Error Handling and Recovery

### 12.1 Expected Failures

| ID | Failure Mode | User/System Behavior | Logging / Observability | Recovery |
| --- | --- | --- | --- | --- |
| ERR-001 | Canonical path ambiguity | Users and agents update the wrong doc | Review flags duplicate usage surfaces | Declare canonical path and migrate |
| ERR-002 | Frontmatter validation conflict | Usage pages fail canonical validator | Validation output names missing keys | Use canonical frontmatter or exclude with ADR |

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

| Requirement ID | Test / Verification Method | Status |
| --- | --- | --- |
| FR-001 | CLI Documentation compatibility text review | Not Started |
| FR-002 | Usage pages pass frontmatter validation | Not Started |
| FR-003 | Markdown Tooling passes over usage content | Not Started |
| FR-004 | Aggregate check or docs gate includes MkDocs strict build | Not Started |
| FR-005 | Dogfood adoption ADR path review | Not Started |
| FR-006 | `docs/usage.md` migration test or review | Not Started |

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

- [ ] Compatibility amendments in sibling standards.
- [ ] Migration note for existing `docs/usage.md`.
- [ ] Dogfood adoption ADR.

---

## 19. Implementation Plan

### MS-0 — Audit

1. Compatibility conflicts listed.
2. Owner resolves blockers.

### MS-1 — Amend

1. Sibling standards updated.
2. No contradictory canonical paths remain.

### MS-2 — Migrate

1. Dogfood usage content moved or cross-linked.
2. Strict build and CLI docs checks pass.

### MS-3 — Release

1. Versioning and changelog updated.
2. Consumers can adopt safely.

### Milestone Summary

| Milestone | Deliverable | Exit Criteria |
| --- | --- | --- |
| MS-0 Audit | Compatibility conflicts listed | Owner resolves blockers |
| MS-1 Amend | Sibling standards updated | No contradictory canonical paths remain |
| MS-2 Migrate | Dogfood usage content moved or cross-linked | Strict build and CLI docs checks pass |
| MS-3 Release | Versioning and changelog updated | Consumers can adopt safely |

---

> **§20 (Success Evaluation) is Full-tier** and is intentionally omitted at the Standard profile.

## 21. Open Questions and Decisions

| ID | Question | Current Assumption | Blocking? | Owner | Needed By | Status |
| --- | --- | --- | --- | --- | --- | --- |
| OQ-001 | Should `docs/usage.md` be retained as a redirect/index during migration? | Retain temporarily with a clear pointer to the MkDocs site if deletion is too disruptive. | No | Owner | MS-2 | Open |

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

- standards/cli-documentation/README.md
- docs/usage.md
- standards/markdown-frontmatter/README.md
- standards/project-spec/README.md

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
