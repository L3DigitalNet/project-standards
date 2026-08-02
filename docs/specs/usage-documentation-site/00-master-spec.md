---
spec_id: SPEC-U000
title: 'Usage Documentation Site Standard Master Specification'
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
  prior_specs:
    - 'docs/specs/future/usage-documentation-site/01-standard-readme-spec.md'
    - 'docs/specs/future/usage-documentation-site/02-adoption-bundle-spec.md'
    - 'docs/specs/future/usage-documentation-site/03-validation-spec.md'
    - 'docs/specs/future/usage-documentation-site/04-compatibility-migration-spec.md'
    - 'docs/specs/future/usage-documentation-site/05-open-items-and-decision-log.md'
    - 'docs/specs/future/usage-documentation-site/06-distributor-standard-addendum.md'
---

# Usage Documentation Site Standard Master — Specification (Standard)

## Revision History

| Version | Date       | Author  | Change                                         |
| ------- | ---------- | ------- | ---------------------------------------------- |
| 0.1     | 2026-07-08 | ChatGPT | Initial conformant Project Specification draft |

**Spec lifecycle:** This document is living until `approved`, then change-controlled. Implementation deviations are recorded in the Deviations Log, not silently patched into requirements.

---

## 1. Purpose & Background

Create a first-class, distributable Project Standards standard named `usage-documentation-site`. The standard defines a repo-local MkDocs and Material site for user-facing tool usage documentation, and the distributor repository must adopt it as dogfood in the same standards ecosystem it governs.

---

## 2. Scope

### 2.1 In Scope

- New standards bundle and adopt bundle for `usage-documentation-site`.
- Registry, versioning, validator, test, and standards-index integration.
- Dogfood adoption inside `L3DigitalNet/project-standards` as proof of interoperability.
- Compatibility amendments for sibling standards, especially CLI Documentation.
- Consuming-repo layout, feedback mechanism, content taxonomy, and validation model.

### 2.2 Out of Scope (Non-Goals — never)

| ID | Non-Goal | Reason |
| --- | --- | --- |
| NG-001 | Replacing developer documentation, ADRs, project specs, or handoff systems | The new standard is strictly for user-facing usage documentation sites. |
| NG-002 | Creating a hosted public documentation platform | The standard governs repo-local local-browser sites only. |
| NG-003 | Changing the Project Specification Standard itself | This spec consumes that standard rather than modifying it. |

### 2.3 Won't Have in v1 (deferred — not never)

| ID | Deferred Capability | Why Deferred | Revisit When |
| --- | --- | --- | --- |
| WH-001 | Full prose-style linting with Vale | Useful but subjective and likely noisy in v1 | Repeated content-quality drift appears |
| WH-002 | External link checking as a required gate | Network checks are flaky in CI | A stable allowlist and retry policy exists |
| WH-003 | Hosted publication workflow | Local usage is the target for v1 | A repository explicitly needs public docs hosting |

### 2.4 Boundaries

| Boundary | Description |
| --- | --- |
| Distributor owns | `project-standards` standard text, templates, schemas, validators, registry entries, tests, and dogfood example. |
| Consuming repo owns | Actual tool-specific usage content and local adoption ADRs. |
| External platform owns | GitHub Issues UI and permissions; MkDocs and Material runtime behavior. |

---

## 3. Context

### 3.1 Current State

The planning bundle exists as ordinary Markdown files with draft metadata. The distributor repository already governs several standards but does not yet provide a MkDocs and Material usage-site standard. The CLI Documentation Standard currently dogfoods a single `docs/usage.md` reference.

### 3.2 Target State

The distributor repository contains a registered, adoptable, tested, dogfooded `usage-documentation-site` standard. The previous draft files are converted into Project Specification Standard shape so an implementation agent can validate and execute the work consistently.

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
| G-001 | Create a distributable usage-site standard | `project-standards list` includes `usage-documentation-site` | FR-001, FR-002, FR-003 |
| G-002 | Prove interoperability by dogfooding | The distributor repository builds its own usage site under `docs/usage/` | FR-006, NFR-002 |
| G-003 | Prevent drift across consuming repos | Schemas, validators, tags, field IDs, and agent instructions are controlled | FR-004, FR-005, FR-007 |

---

> **§5 (Stakeholders and Users) is Full-tier** and is intentionally omitted at the Standard profile.

## 6. Glossary

| Term | Definition | Notes |
| --- | --- | --- |
| Distributor repository | `L3DigitalNet/project-standards`, the source of truth for standards and adoption artifacts. | Not the same as a consuming repository. |
| Consuming repository | A repository that adopts one or more standards from `project-standards`. | Owns its local content and deviations. |
| Usage documentation site | A repo-local MkDocs and Material site for user-facing instructions about using tools. | Not developer documentation. |
| Dogfood adoption | The distributor repository adopts and validates the standard it governs. | Required as interoperability proof. |

---

## 7. Requirements

### 7.1 Functional Requirements

| ID | Requirement | Rationale | Acceptance Criteria | Priority |
| --- | --- | --- | --- | --- |
| FR-001 | The system shall add `standards/usage-documentation-site/` as a first-class standards bundle. | The standards repo distributes standards through bundles. | Bundle contains README, adopt runbook, templates, examples, resources, and schemas. | Must |
| FR-002 | The system shall add `src/project_standards/bundles/usage-documentation-site/` as the copy-adopt bundle. | Consumers need deterministic scaffolding. | Adopt dry-run reports the expected files and fragments. | Must |
| FR-003 | The system shall register `usage_documentation_site.version` as a known contract marker. | The registry guards adopted standards against drift. | Unknown version fails and version `1.0` passes. | Must |
| FR-004 | The system shall provide JSON schemas for standard-owned YAML artifacts. | Schemas prevent drift in MkDocs and issue-form contracts. | Schema validation covers `mkdocs.yml` and `tool-feedback.yml`. | Must |
| FR-005 | The system shall define content-page validation beyond generic MkDocs and Markdown checks. | Page taxonomy and user-facing scope are standard-specific. | Validator or documented v1 plan checks required layout and page roles. | Must |
| FR-006 | The system shall make `L3DigitalNet/project-standards` adopt the standard it governs. | The distributor must dogfood every standard as proof of interoperability. | Repository contains and validates its own usage site. | Must |
| FR-007 | The system shall amend sibling standards that otherwise imply conflicting canonical usage-doc paths. | Avoiding standards conflict is part of the release contract. | `cli-documentation` compatibility text is merged. | Must |

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

---

## 8. Architecture and Design

### 8.1 Architecture Summary

The system is a new copy-adopted standard plus optional validator support. The standards bundle contains normative prose and reusable templates. The adopt bundle materializes safe artifacts into consumers. The distributor repository also adopts the standard locally so CI proves the new standard works beside existing standards.

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
| Standards bundle | Governing standard text and adoption runbook | Markdown files under `standards/usage-documentation-site/` | Required for documentation distribution |
| Adopt bundle | Packaged copy-adopt files and fragments | `adopt.toml` and source templates | Used by `project-standards adopt` |
| Registry integration | Known version and parity checks | `registry.json`, `registry.py`, `cli.py` | Prevents drift |
| Dogfood site | Distributor-owned usage site | `docs/usage/` | Proves interoperability |

### 8.3 Design Decisions

| ID | Decision | Rationale | Alternatives Considered | ADR |
| --- | --- | --- | --- | --- |
| D-001 | Create new sibling standard `usage-documentation-site`. | Site structure and CLI content rules are separate concerns. | Expand CLI Documentation into a site standard; rejected to avoid overload. | TBD local ADR |
| D-002 | Rendered usage pages use canonical Markdown Frontmatter by default. | Avoids conflict with frontmatter validation and supports standard search/retrieval. | Exclude usage pages from frontmatter validation; rejected for weaker governance. | TBD local ADR |
| D-003 | The distributor repository dogfoods the standard. | Every governed standard must demonstrate interoperability in the repository that ships it. | Defer dogfood to a later release; rejected by owner direction. | TBD local ADR |

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

1. Convert this planning bundle into conformant Project Specification Standard documents.
2. Implement the standards bundle and adopt bundle.
3. Update registry, versioning, validation, tests, and sibling standards.
4. Adopt the new standard in the distributor repository itself.
5. Run full validation including Project Spec validation and MkDocs strict build.

Expected result:

> The distributor repository contains a tested, registered, dogfooded `usage-documentation-site` standard that consuming repositories can adopt consistently.

### 10.2 Alternate Workflows

| ID | Trigger | Behavior | Expected Result |
| --- | --- | --- | --- |
| AW-001 | Manual adoption without central standard | Allow each repo to copy guidance independently | Rejected because it causes drift |
| AW-002 | Modify CLI Documentation only | Fold site behavior into existing CLI docs standard | Rejected because not every tool is a CLI and path ownership differs |

### 10.3 Edge Cases

| ID | Edge Case | Expected Behavior |
| --- | --- | --- |
| EC-001 | Existing `docs/usage.md` remains present | Compatibility text defines which surface is canonical during migration |
| EC-002 | Consuming repo lacks GitHub Issues | Standard documents the issue-form artifact as GitHub-specific and allows a recorded deviation |

### 10.4 State Transitions

| State | Meaning | Entry Condition | Exit Condition |
| --- | --- | --- | --- |
| Draft | Spec is being authored | Owner requests changes | Owner approves implementation |
| Implemented | Standard exists in repository | Implementation branch merged | Release preparation begins |
| Released | Standard is available to consumers | Release tag published | Next version supersedes it |

---

## 11. UI Pages / API Endpoints

This work has no hosted UI or API surface. The relevant user surfaces are local MkDocs pages, GitHub issue forms, and CLI commands.

| Page or Endpoint | Purpose | Key Actions | Authorization |
| --- | --- | --- | --- |
| `project-standards list` | Shows adoptable standards | List contract version and artifacts | Repository maintainer |
| `project-standards adopt usage-documentation-site` | Materializes scaffold | Create files or report fragments | Repository maintainer |
| Local MkDocs site | Readable usage docs | Browse, search, follow feedback links | Local user |

**Accessibility & i18n:** v1 targets readable local-browser documentation in English. Formal localization is out of scope, but the content must avoid encoding implementation-only jargon into user-facing pages.

---

## 12. Error Handling and Recovery

### 12.1 Expected Failures

| ID | Failure Mode | User/System Behavior | Logging / Observability | Recovery |
| --- | --- | --- | --- | --- |
| ERR-001 | Registry and bundle drift | CLI exits with registry error before writing | Error names registry-only and bundle-only standards | Update registry and bundle together |
| ERR-002 | MkDocs strict build failure | CI or local build fails | MkDocs emits broken link, nav, anchor, or tag diagnostics | Fix docs or record deviation |
| ERR-003 | Dogfood content leak | Developer-only material appears in usage site | Review or validator warning identifies scope drift | Move content out of `docs/usage/content/` |

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
| FR-001 | Standards bundle files exist and frontmatter validates | Not Started |
| FR-002 | Adopt dry-run reports expected artifacts | Not Started |
| FR-003 | Config with `usage_documentation_site.version: "1.0"` validates | Not Started |
| FR-004 | JSON schema tests cover valid and invalid YAML artifacts | Not Started |
| FR-005 | Usage-site validator or planned test fixture covers required taxonomy | Not Started |
| FR-006 | `mkdocs build --strict -f docs/usage/mkdocs.yml` passes in distributor repo | Not Started |
| FR-007 | CLI Documentation Standard includes compatibility text | Not Started |

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

- [ ] New governing README and adoption runbook.
- [ ] Templates, examples, schemas, and resources.
- [ ] Dogfood usage site under `docs/usage/`.
- [ ] Local adoption ADR under `docs/decisions/`.
- [ ] Compatibility notes in sibling standards.

---

## 19. Implementation Plan

### MS-0 — Foundation

1. Project spec bundle is conformant.
2. Spec validation target can include these files.

### MS-1 — Standard bundle

1. Governing README and adopt runbook are created.
2. Standard text is ready for review.

### MS-2 — Adopt and registry

1. Adopt bundle and registry integration are implemented.
2. `project-standards list` and adopt dry-run pass.

### MS-3 — Validation

1. Schemas and usage-site validation are implemented or explicitly scoped.
2. Tests prove valid and invalid cases.

### MS-4 — Dogfood

1. Distributor repository adopts its own usage site.
2. MkDocs strict build passes.

### MS-5 — Release readiness

1. Versioning, changelog, and compatibility docs are complete.
2. Repository gate passes.

### Milestone Summary

| Milestone | Deliverable | Exit Criteria |
| --- | --- | --- |
| MS-0 Foundation | Project spec bundle is conformant | Spec validation target can include these files |
| MS-1 Standard bundle | Governing README and adopt runbook are created | Standard text is ready for review |
| MS-2 Adopt and registry | Adopt bundle and registry integration are implemented | `project-standards list` and adopt dry-run pass |
| MS-3 Validation | Schemas and usage-site validation are implemented or explicitly scoped | Tests prove valid and invalid cases |
| MS-4 Dogfood | Distributor repository adopts its own usage site | MkDocs strict build passes |
| MS-5 Release readiness | Versioning, changelog, and compatibility docs are complete | Repository gate passes |

---

> **§20 (Success Evaluation) is Full-tier** and is intentionally omitted at the Standard profile.

## 21. Open Questions and Decisions

| ID | Question | Current Assumption | Blocking? | Owner | Needed By | Status |
| --- | --- | --- | --- | --- | --- | --- |
| OQ-001 | Should `usage-site validate` ship in the first release or be documented as planned? | Ship at least deterministic layout validation if implementation cost is modest. | No | Owner | MS-3 | Open |
| OQ-002 | Should the existing `docs/usage.md` be migrated immediately into `docs/usage/content/`? | Yes, because dogfooding is mandatory, but preserve compatibility during migration. | No | Owner | MS-4 | Open |

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

- standards/project-spec/README.md
- standards/README.md
- standards/cli-documentation/README.md
- standards/markdown-frontmatter/README.md
- meta/versioning.md

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
