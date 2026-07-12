# Prospective updated guidance and instructions for project-spec specs

```markdown
# Project Specification Section Authoring Guide

## 1. Purpose

This guide defines how to populate the canonical Project Specification Standard templates completely and consistently.

It supplements the selected Light, Standard, or Full template. It does not replace, extend, or modify the template. When this guide conflicts with the applicable Project Specification Standard, its template, or its tooling, the standard is authoritative.

Apply guidance only to sections present in the selected canonical profile. Never add a higher-profile section to a lower-profile specification manually. Use the standard-provided profile-upgrade tooling when available.

## 2. Authoring boundary

The skill formalizes project context that already exists. It does not brainstorm the project, conduct product discovery, or design missing parts of the solution.

The skill may:

- consolidate information from the user, repository, design artifacts, ADRs, issues, prior specifications, and other authoritative sources;
- derive straightforward consequences of confirmed decisions;
- reorganize supplied information into the appropriate canonical sections;
- identify omissions, contradictions, and unresolved decisions;
- record assumptions and open questions using the template;
- improve precision, consistency, traceability, and testability.

The skill must not:

- invent project goals, features, requirements, architecture, or stakeholder needs;
- choose among consequential design alternatives that the available context has not resolved;
- add generic “best practices” as project requirements without evidence that they apply;
- disguise missing information with vague or conventional-sounding prose;
- ask broad discovery questions merely to make the document more detailed.

When a material decision is absent, record the gap in §21 where available. Ask the user only when it is genuinely blocking or an unexpected finding requires resolution.

## 3. Global content rules

### 3.1 Source fidelity

Every consequential statement must be one of:

- explicitly supported by available project context;
- a direct and low-risk derivation from that context;
- clearly identified as an assumption;
- clearly identified as an unresolved question.

Do not silently convert current implementation behavior into an approved requirement or design decision. Existing code is evidence of the current state, not automatically the intended target state.

### 3.2 Correct abstraction

Place information according to what it represents:

| Information type                          | Canonical location |
| ----------------------------------------- | ------------------ |
| Why the work exists                       | §1                 |
| What is included, excluded, or deferred   | §2                 |
| Existing conditions and imposed limits    | §3                 |
| Outcomes the project should achieve       | §4                 |
| People or roles affected                  | §5                 |
| Precise meaning of terms                  | §6                 |
| Required behavior and quality             | §7                 |
| Chosen technical structure and decisions  | §8                 |
| Persistent information structure          | §9                 |
| End-to-end behavior and state             | §10                |
| User-facing or machine-facing surface     | §11                |
| Failure and recovery behavior             | §12                |
| Security and privacy controls             | §13                |
| Expected load and growth                  | §14                |
| Uncertain events that could harm delivery | §15                |
| External obligations and rights           | §16                |
| Evidence required for acceptance          | §17                |
| Runtime and operational behavior          | §18                |
| High-level delivery sequence              | §19                |
| Post-launch outcome measurement           | §20                |
| Unresolved decisions                      | §21                |

Do not repeat the same statement in several sections merely because it is relevant to each. State it authoritatively once and cross-reference it where necessary.

### 3.3 Completeness over length

A short section can be complete. A long section can still be inadequate.

Do not judge completeness by:

- word count;
- number of rows;
- number of requirements;
- number of diagrams;
- presence of every conceivable best practice.

Judge completeness by whether all applicable known information is represented, important distinctions are preserved, and no material contradiction or unexplained gap remains.

### 3.4 No generic filler

Reject statements such as:

- “The system should be scalable.”
- “Security best practices will be followed.”
- “Errors will be handled gracefully.”
- “The interface should be user friendly.”
- “The application will have comprehensive tests.”
- “The architecture should be modular.”

Such statements are acceptable only when converted into project-specific, observable obligations supported by the available context.

### 3.5 Not-applicable sections

When the canonical template permits deletion of an inapplicable section:

1. Confirm that it is genuinely inapplicable.
2. Replace it with the template-prescribed one-line explanation when required.
3. Do not leave empty tables, placeholders, or fabricated entries.
4. Do not delete a section merely because available context is incomplete.

“Inapplicable” and “not yet decided” are different conditions.

### 3.6 Cross-section consistency

Before declaring the specification review-ready, confirm that:

- scope does not conflict with non-goals or deferred work;
- goals are supported by requirements;
- requirements do not introduce unapproved scope;
- architecture accounts for all material requirements;
- workflows agree with requirements and interfaces;
- failure handling covers identified dependency and workflow failures;
- security controls match the actual interfaces, actors, and data;
- test strategy can verify the stated acceptance criteria;
- milestones do not introduce new requirements or decisions;
- success evaluation measures the outcomes stated in §1 and §4;
- open questions accurately identify remaining uncertainty.

---

# Section Guidance

## Revision History

### Purpose

Record meaningful versions of the specification and why each version changed.

### Required coverage

Include the initial draft and every subsequent change that materially affects scope, requirements, design, acceptance, or approval state. Describe the substance of the change rather than writing “updated document.”

### Completion test

A reviewer can identify which version introduced or changed a consequential obligation and whether a post-approval change requires renewed approval.

### Avoid

- recording every formatting edit or autosave;
- changing approved content without adding a revision entry;
- using version numbers without a consistent progression;
- leaving the initial placeholder row intact.

---

## §1 Purpose & Background

### Purpose

Explain why the project exists and what successful completion changes.

### Required coverage

State:

- who or what experiences the problem;
- the present problem, limitation, or opportunity;
- why the work is being undertaken now;
- the desired outcome;
- the intended emphasis of the first release;
- any future capability the initial work must avoid blocking;
- durable or compounding value, when applicable.

Describe the problem before describing the solution. Include enough current context for a reader unfamiliar with the project to understand the motivation.

### Completion test

A reader can explain the project’s reason for existence, intended beneficiary, current pain, desired result, and first-release emphasis without reading the architecture section.

### Avoid

- opening with a list of technologies;
- describing implementation tasks instead of the problem;
- repeating the entire scope or requirements catalog;
- claiming business value that is not supported by supplied context;
- presenting an assumed solution as though it were the original problem.

---

## §2 Scope

### §2.1 In Scope

Describe the capabilities, workflows, integrations, data responsibilities, and operational outcomes included in the specified release.

Scope statements define boundaries, not implementation tasks. Prefer capability language such as “import records from the approved source” over task language such as “write an importer class.”

#### Completion test

Every major Must requirement falls within an in-scope capability, and no major in-scope capability is absent from the requirements.

### §2.2 Out of Scope — Non-Goals

Record capabilities or responsibilities the project intentionally will not provide.

Each non-goal must include the reason for exclusion. Use this section for durable boundaries, not work merely postponed from the first release.

#### Completion test

The entries prevent plausible but unwanted expansion of the project and are not contradicted elsewhere in the specification.

### §2.3 Won’t Have in v1

Record capabilities that may be desirable later but are deliberately excluded from the specified release.

Each entry must state:

- what is deferred;
- why it is deferred;
- an observable condition that would justify reconsideration.

A vague trigger such as “later” is insufficient.

#### Completion test

A future maintainer can distinguish permanent exclusions from deferred work and knows what event should reopen each deferred capability.

### §2.4 Boundaries

Define responsibility across the system boundary:

- data and behavior the system owns;
- external systems, people, or infrastructure it depends on;
- related systems, decisions, or processes it explicitly does not own.

Include operational responsibility where relevant, such as who owns backups, identity, source data quality, or provider availability.

#### Completion test

For each important component, data set, and dependency, ownership is explicit enough to determine where failures and change requests belong.

### Avoid throughout §2

- treating “not in v1” as a non-goal;
- listing individual code files or implementation steps;
- omitting integration and data ownership boundaries;
- using scope to introduce capabilities not supported by the source context;
- duplicating requirements verbatim.

---

## §3 Context

## §3.1 Current State

Describe the factual starting point:

- existing implementation or workflow;
- relevant repository structure;
- systems and dependencies already in use;
- known limitations and failure modes;
- prior decisions that remain binding;
- operational environment and deployment state;
- compatibility or migration concerns.

Distinguish verified facts from interpretations.

### Completion test

An implementer understands what already exists, what must be preserved or changed, and which current conditions shaped the specification.

## §3.2 Target State

Describe the coherent end state after the specified work is complete.

Focus on observable system and workflow changes. Do not repeat every requirement and do not introduce unapproved architecture.

### Completion test

The difference between current and target state is clear, and the target state is consistent with scope, goals, and requirements.

## §3.3 Assumptions

Record propositions treated as true for the purpose of the specification but not fully confirmed.

For each assumption:

- make the assumed condition precise;
- explain the material consequence if it proves false;
- indicate the fallback or decision that would need reconsideration when known.

Do not label confirmed facts or preferences as assumptions.

### Completion test

Every assumption that could materially change scope, design, cost, acceptance, or operations is visible and has a meaningful “impact if false.”

## §3.4 Constraints

Record externally imposed or explicitly non-negotiable limits, including:

- platform and compatibility requirements;
- hosting or infrastructure limits;
- legal and licensing restrictions;
- security and privacy obligations;
- schedule, cost, or resource limits;
- mandated tools or standards;
- operational restrictions.

Identify the source imposing each constraint.

### Completion test

Every design-limiting condition in the supplied context appears here or is referenced from another authoritative artifact.

### Avoid throughout §3

- presenting preferences as immutable constraints;
- treating unknowns as facts;
- describing the target state as a detailed implementation plan;
- omitting the source or consequence of a constraint;
- assuming existing behavior must be preserved without evidence.

---

## §4 Goals

### Purpose

Define the outcomes the project is intended to achieve.

### Required coverage

Each goal must:

- describe an outcome rather than an activity;
- have an observable success signal;
- map to the requirements that produce it;
- remain distinguishable from post-launch measurement in §20.

A goal may combine several requirements, but every mapped requirement should materially contribute to it.

### Completion test

Every goal is measurable enough to recognize success, and every Must requirement supports a goal, constraint, risk treatment, or explicit operational obligation.

### Avoid

- “build,” “implement,” or “create” as the primary outcome;
- restating individual requirements;
- using subjective success signals;
- listing aspirations unsupported by the available context;
- mapping a goal to unrelated requirements merely to fill the column.

---

## §5 Stakeholders and Users

### Purpose

Identify distinct roles whose needs, authority, or responsibilities affect the specification.

### Required coverage

For each relevant role, identify:

- its concern;
- how it interacts with or governs the project;
- whether it uses, operates, approves, secures, supplies data to, or maintains the system.

Use roles rather than personal names unless a named owner is operationally important.

Delete the section when the project is genuinely solo and no meaningful role distinctions exist.

### Completion test

Every materially different perspective that affects requirements, approval, operation, or security is represented once.

### Avoid

- listing the same person repeatedly under artificial roles;
- inventing enterprise stakeholders for a solo project;
- turning the section into a responsibility-assignment matrix;
- asserting concerns not present in the source context.

---

## §6 Glossary

### Purpose

Prevent ambiguous or inconsistent interpretation of domain and project terminology.

### Required coverage

Define:

- domain-specific terms;
- overloaded technical terms used with a project-specific meaning;
- abbreviations and acronyms not universally clear;
- similar concepts that must remain distinct;
- terms whose ordinary-language meaning differs from the specification’s meaning.

Definitions should be precise enough that two implementers use the term consistently.

### Completion test

No requirement, decision, workflow, or data entity depends on a term that a competent implementer could reasonably interpret in multiple ways.

### Avoid

- defining ordinary technical words without a project-specific reason;
- circular definitions;
- using examples instead of definitions;
- allowing the same concept to have several names;
- introducing glossary terms that never appear elsewhere.

---

## §7 Requirements

### General requirement rules

Each requirement must be:

- atomic;
- necessary;
- feasible within known constraints;
- unambiguous;
- independently verifiable;
- traceable to a goal, constraint, interface, risk treatment, or explicit source;
- written at the level of required behavior rather than incidental implementation.

Use one normative obligation per row. Acceptance criteria must prove the requirement itself, not merely show that related code exists.

Priority must reflect release consequences:

- **Must:** absence prevents acceptance of the specified release;
- **Should:** important and expected, but temporarily deferrable without invalidating the release;
- **Could:** beneficial but must not delay release.

Do not downgrade a requirement merely because it is difficult.

### §7.1 Functional Requirements

Describe behavior the system must perform in response to an input, event, state, or actor action.

Where relevant, identify:

- trigger or precondition;
- actor or source;
- required processing;
- observable output or state change;
- behavior for valid and invalid input.

#### Completion test

Every in-scope workflow and capability has sufficient functional requirements to determine what the system must do, including its material negative behavior.

### §7.2 Non-Functional Requirements

Describe measurable quality attributes, such as:

- performance and latency;
- reliability and availability;
- durability and recoverability;
- compatibility and portability;
- usability and accessibility;
- scalability and capacity;
- maintainability where an objective criterion exists;
- observability and auditability.

Specify the operating condition and measurement method or threshold. “Fast,” “reliable,” “maintainable,” and “secure” are not requirements without criteria.

#### Completion test

Every quality attribute that materially influenced the supplied design or acceptance expectations has an objective criterion.

### §7.3 Interface Requirements

Describe behavior at system boundaries, including:

- APIs;
- CLIs;
- user interfaces;
- files and serialization formats;
- databases and queues;
- hardware or network protocols;
- external services.

For each interface, cover applicable direction, contract, authentication, input/output format, errors, compatibility, versioning, pagination, ordering, and limits.

Reference a separate authoritative contract rather than duplicating it when one exists.

#### Completion test

Each external or user-visible boundary has enough contract detail to implement and test both sides without inventing protocol behavior.

### §7.4 Data Requirements

Describe required data lifecycle behavior:

- creation and ingestion;
- validation and normalization;
- ownership and authority;
- persistence and retrieval;
- update and deletion;
- migration and compatibility;
- retention and archival;
- import and export;
- provenance and audit;
- backup and restoration expectations.

Do not duplicate the physical data model from §9. This section states required data behavior; §9 describes the selected structure.

#### Completion test

Every important data entity has explicit ownership, lifecycle obligations, and validation behavior, and those obligations are consistent with §9, §13, and §18.

### Avoid throughout §7

- compound obligations joined by several unrelated “and” clauses;
- embedding a preferred library or class structure unless mandated;
- acceptance criteria such as “works correctly” or “tests pass”;
- repeating architecture descriptions as requirements;
- adding generic controls unsupported by context;
- assigning every item Must;
- retaining example rows or IDs.

---

## §8 Architecture and Design

This section records the design already established by the available context. It is not permission for the authoring skill to design missing parts of the project.

## §8.1 Architecture Summary

Describe in prose:

- major components and their responsibilities;
- principal data and control flows;
- runtime and deployment boundaries;
- trust boundaries;
- external dependencies;
- important coupling;
- the material decisions that shaped the design.

Explain how the architecture satisfies the principal requirements and constraints.

### Completion test

A technical reader understands the selected system shape and can relate each major component to its responsibilities and interfaces.

## §8.2 Architecture Views

Use only diagrams or component tables that clarify something not already obvious from prose.

Each view must:

- use the same names as the glossary and prose;
- show the correct boundary and level of detail;
- agree with runtime and interface descriptions;
- omit speculative components.

A diagram must communicate an actual relationship, not merely decorate the document.

### Completion test

Every included view answers a distinct architectural question, and no material contradiction exists among diagrams, prose, and tables.

## §8.3 Design Decisions

Record consequential selected decisions.

For each decision, include:

- the choice made;
- why it was made;
- relevant alternatives that were actually considered;
- an ADR reference when one exists or is required by repository convention.

Do not manufacture alternatives to make the table appear complete. A decision that deserves a durable independent record should reference an ADR rather than embedding the entire ADR in the spec.

### Completion test

The decisions most likely to be questioned or accidentally reversed are documented with enough rationale to prevent needless relitigation.

## §8.4 Solution Alternatives Considered

Record project-level alternatives already evaluated, such as:

- buy versus build;
- extending an existing tool;
- adopting a different system architecture;
- retaining the current state;
- not undertaking the project.

This differs from §8.3: §8.4 compares whole-solution approaches, while §8.3 records individual selected design decisions.

### Completion test

All materially considered whole-solution alternatives from the source context are represented, without inventing an artificial quota.

## §8.5 Design Constraints

List technical invariants the implementer must not violate.

Each constraint should be concrete enough that a reviewer can detect a violation. Reference the source constraint or decision where useful.

### Completion test

The implementation cannot comply with the requirements while silently violating a known architectural invariant.

## §8.6 Dependency Policy

Record dependencies whose use is approved, prohibited, or conditional when dependency choice materially affects:

- architecture;
- licensing;
- security;
- operations;
- cost;
- portability;
- maintenance.

State the reason and any conditions. Do not attempt to enumerate every transitive package.

### Completion test

An implementer can determine whether introducing or replacing a consequential dependency requires approval.

### Avoid throughout §8

- selecting a design because the section is empty;
- copying example architecture from the template;
- substituting diagrams for explanation;
- documenting low-level code organization as system architecture;
- using “modular,” “clean,” or “loosely coupled” without explaining actual boundaries;
- describing every implementation choice as an architectural decision.

---

## §9 Data Model

### Purpose

Define the selected persistent data structure concretely enough to implement, migrate, query, validate, and recover.

### Required coverage

For each material entity or record type, cover applicable:

- identity and natural keys;
- required and optional fields;
- relationships and cardinality;
- uniqueness and integrity constraints;
- normalized or denormalized representation;
- ownership and source of truth;
- access patterns;
- indexes required by those access patterns;
- lifecycle, retention, and archival;
- migration and compatibility;
- provenance needed to reproduce or explain results;
- deletion and cascade behavior;
- safe extension points.

Use concrete schema definitions when they already exist in the supplied design. Do not invent a physical schema when the design has not selected one.

### Completion test

The data requirements in §7.4 can be implemented without guessing entity identity, ownership, integrity rules, lifecycle, or material access patterns.

### Avoid

- listing only entity names;
- omitting uniqueness and ownership;
- adding indexes without a stated access pattern;
- treating JSON blobs as a substitute for deciding structure;
- specifying a database technology not established by context;
- duplicating sensitive-data and backup policies instead of cross-referencing them.

---

## §10 Behavior and Workflows

## §10.1 Primary Workflow

Describe the principal end-to-end path, including:

- trigger and preconditions;
- participating actors and systems;
- ordered behavior;
- material validations and decisions;
- persistence or state changes;
- observable result;
- handoff to external dependencies.

The workflow should connect requirements, interfaces, and components.

### Completion test

An implementer and tester can follow the expected happy path from trigger to outcome without inventing intermediate behavior.

## §10.2 Alternate Workflows

Record meaningful variations that still represent valid operation, such as:

- optional actor choices;
- alternate input sources;
- resumed or retried flows;
- authorized overrides;
- degraded but supported paths.

Do not use this section for faults; expected failures belong in §12.

### Completion test

Every supported deviation from the primary path that changes behavior or outcome is represented.

## §10.3 Edge Cases

Identify boundary and unusual conditions supported by the available context, such as:

- empty input;
- duplicate input;
- out-of-order events;
- stale data;
- maximum and minimum values;
- concurrent updates;
- partial records;
- ambiguous matches;
- repeated commands;
- timing boundaries.

State expected behavior, not merely the condition.

### Completion test

Known boundary cases that could produce materially different, unsafe, or surprising results have defined outcomes.

## §10.4 State Transitions

Use when the system has a meaningful lifecycle.

Define:

- valid states;
- entry and exit conditions;
- events or actors that cause transitions;
- invalid transitions and their behavior;
- terminal and recoverable states;
- expiry, cleanup, retry, suppression, or escalation behavior where applicable.

### Completion test

Every valid state transition is explainable, invalid transitions have defined handling, and workflow prose agrees with the state model.

### Avoid throughout §10

- restating requirements without showing sequence;
- documenting only the happy path;
- confusing alternate valid behavior with failure behavior;
- adding states not supported by the design;
- including a generic diagram that does not match the project.

---

## §11 UI Pages / API Endpoints

### Purpose

Define the minimum user-facing or machine-facing surface required by the release.

### Required coverage

For each applicable page, command surface, or endpoint, identify:

- purpose;
- principal actors;
- key actions;
- authorization;
- source of displayed or returned data;
- filtering, sorting, and pagination;
- empty, loading, validation, and error behavior;
- state-changing audit requirements;
- applicable latency expectations;
- accessibility and localization position.

For APIs, reference the authoritative contract and describe behavior not adequately expressed by its schema.

### Completion test

Every user-visible or externally callable requirement has an identified surface and enough behavioral context to implement its success, empty, denied, and failure states.

### Avoid

- designing visual styling without supplied design context;
- listing routes without behavior;
- omitting authorization from state-changing operations;
- duplicating an OpenAPI document;
- inventing an admin interface because one is common.

---

## §12 Error Handling and Recovery

## §12.1 Expected Failures

Identify failures derived from actual workflows, components, interfaces, and dependencies.

For each failure, define:

- what triggers or detects it;
- user-visible or system-visible behavior;
- whether processing stops, degrades, or fails closed;
- logging, metrics, and audit evidence;
- recovery path and responsible actor.

### Completion test

Every material dependency and workflow has its credible failure behavior defined, not merely its success path.

## §12.2 Retry and Idempotency

Define:

- which operations may be retried;
- transient versus permanent failure classification;
- attempt limits;
- delay or backoff behavior;
- provider retry instructions where applicable;
- idempotency keys or deduplication strategy;
- concurrency and replay behavior;
- throttling and circuit-breaking when required.

### Completion test

A repeated or interrupted operation cannot silently create duplicate or inconsistent results, and retry behavior cannot continue indefinitely.

## §12.3 Rollback / Recovery

Describe recovery from partial or failed execution:

- potentially inconsistent state;
- detection method;
- rollback or forward-repair method;
- data reconciliation;
- manual intervention;
- verification that recovery succeeded.

### Completion test

An operator can identify, repair, and verify a partial failure without reconstructing the recovery model from code.

### Avoid throughout §12

- “log and retry” without limits or classification;
- retrying permanent errors;
- declaring operations idempotent without a mechanism;
- focusing only on exceptions inside application code;
- omitting user-visible behavior and operator recovery.

---

## §13 Security and Privacy

Document controls established or required by the available context. Do not silently design a security model that has not been decided. Missing consequential security decisions must become open questions or blockers.

## §13.1 Authentication

Describe:

- actors that authenticate;
- authentication mechanism;
- trust root or identity provider;
- credential or session lifecycle;
- service-to-service identity;
- failure and revocation behavior where known.

## §13.2 Authorization

Define permissions by role or actor, including explicitly denied actions.

State default behavior when no rule grants access. Address administrative, automated, and service identities, not only end users.

## §13.3 Secrets

List secret identifiers or references, storage locations, access patterns, and rotation expectations.

Never include secret values.

## §13.4 Sensitive Data

Identify sensitive data and define:

- classification;
- storage location;
- protection in transit and at rest;
- retention;
- access boundaries;
- deletion or export obligations.

## §13.5 Threats and Mitigations

Record credible threats arising from the actual attack surface and data flows.

A mitigation must reduce the named threat. Avoid generic lists detached from the architecture.

## §13.6 Hardening Checklist

Resolve every canonical item by:

- referencing the section or decision that addresses it; or
- marking it not applicable with a project-specific reason.

Do not check an item merely because the control is conventional.

### Completion test for §13

The specification defines who and what may access the system, how identity and secrets are handled, which data needs protection, and how the principal project-specific threats are reduced.

### Avoid

- “follow security best practices”;
- storing secret values;
- assuming a private network eliminates authorization needs;
- treating authentication and authorization as interchangeable;
- marking checklist entries complete without evidence;
- inventing compliance requirements.

---

## §14 Capacity and Scale Assumptions

### Purpose

Record the expected workload that materially influences design.

### Required coverage

Use available evidence to provide realistic values or explicit ranges for:

- stored data volume;
- growth rate;
- request or job rate;
- concurrency;
- event frequency;
- payload sizes;
- retention horizon;
- external-provider quotas;
- other workload dimensions that shaped the design.

For each material figure, state the design consequence.

When the context provides no defensible estimate and the estimate affects design, record an open question rather than fabricating a number.

### Completion test

Every capacity-dependent design choice can be traced to an explicit workload assumption.

### Avoid

- arbitrary large round numbers;
- “must scale indefinitely”;
- numbers with no design consequence;
- treating maximum theoretical capacity as expected load;
- choosing infrastructure from an unsupported estimate.

---

## §15 Risks

### Purpose

Record uncertain events or conditions that could harm delivery or project outcomes.

### Required coverage

For each material risk, identify:

- the uncertain event or condition;
- likelihood;
- impact;
- mitigation, contingency, transfer, or explicit acceptance;
- owner.

Distinguish:

- project risk from a current defect;
- security threat from delivery risk;
- provider-specific operational behavior from general project risk;
- an assumption from the risk created if that assumption is wrong.

### Completion test

The important uncertainties visible in the supplied context have an accountable treatment, and mitigations appear elsewhere in the specification where they create requirements or design obligations.

### Avoid

- generic risks applicable to every software project;
- listing certain problems as uncertain risks;
- mitigation such as “monitor closely” without an action;
- unowned high-impact risks;
- duplicating §13.5.

---

## §16 Compliance, Licensing, and Data Rights

### Purpose

Record obligations imposed by regulation, licenses, contracts, terms of service, or ownership rights.

### Required coverage

Where applicable, identify:

- legal or regulatory regimes;
- data residency, retention, export, or deletion obligations;
- third-party service terms;
- API caching and redistribution limits;
- scraped or ingested data rights;
- open-source license compatibility;
- attribution or source-disclosure obligations;
- ownership of generated or transformed data.

Reference authoritative evidence rather than making unsupported legal conclusions.

When no relevant obligation is known, use the permitted one-line explanation rather than retaining an empty checklist.

### Completion test

Every applicable external obligation has a corresponding requirement, design control, or documented acceptance decision.

### Avoid

- generic legal disclaimers;
- assuming publicly accessible data is freely reusable;
- listing a regulatory regime without defining its effect;
- making a legal determination beyond the available evidence;
- retaining irrelevant checklist items.

---

## §17 Testing and Acceptance

## §17.1 Definition of Done

Tailor the checklist to the actual project while preserving canonical obligations.

Include all conditions required before the specified release can be accepted, including applicable:

- Must requirements;
- acceptance criteria;
- automated and manual verification;
- documentation;
- security review;
- migration or deployment verification;
- restore testing;
- deviation review;
- closure or acceptance of blockers.

### Completion test

It is possible to make an objective release decision from the checklist.

## §17.2 Test Strategy

For each applicable test layer, identify:

- what it verifies;
- important success and failure behavior;
- boundary and misuse cases;
- whether it is required;
- external systems or environments involved.

Choose layers based on the project. Do not require a layer merely because it appears in the template.

Avoid unsupported coverage percentages. Prefer behavioral coverage requirements tied to risks and acceptance criteria.

### Completion test

Every material requirement type, failure mode, integration boundary, migration, and operational obligation has an appropriate planned verification layer.

## §17.3 Requirement-to-Test Traceability

Include every requirement that must be verified.

Before implementation, the verification entry may identify:

- intended test type or location;
- concrete command;
- contract check;
- inspection procedure;
- controlled manual acceptance procedure.

After implementation, replace intentions with actual evidence.

A test reference is meaningful only when it proves the requirement’s acceptance criterion.

### Completion test

Every Must and Should requirement has a plausible verification method, and no verification entry merely asserts that testing will occur.

### Avoid throughout §17

- “all tests pass” as the only acceptance standard;
- mapping many unrelated requirements to one vague test;
- listing a test layer with no project-specific scope;
- treating code coverage alone as behavioral evidence;
- marking traceability Passing before evidence exists.

---

## §18 Deployment and Operations

## §18.1 Runtime Environment

Document the established target environment:

- runtime and version constraints;
- operating system or platform;
- deployable services and workers;
- datastore;
- external services;
- scheduling;
- hosting;
- process ownership;
- health signal for each runtime service.

### Completion test

An operator knows what runs, where it runs, how it starts, and how to determine whether it is healthy.

## §18.2 Configuration

List settings that materially affect behavior or deployment.

For each, define:

- identifier;
- whether required;
- default;
- meaning;
- validation or allowed values where needed;
- differences by environment.

List secret references, not values. Do not document every internal constant as configuration.

### Completion test

The implementation can establish valid development and production configuration without inventing defaults or environment behavior.

## §18.3 Deployment Flow

Describe the actual intended sequence:

- trigger;
- validation gates;
- artifact production or source delivery;
- configuration and secrets;
- migrations;
- rollout or restart;
- health and smoke checks;
- rollback.

Include ordering constraints and failure behavior.

### Completion test

A deployment and rollback can be executed in the correct order without inferring critical steps from repository code.

## §18.4 Rollout Controls

Define exposure controls already selected or required by risk:

- feature flags;
- kill switches;
- staged cohorts;
- canary criteria;
- migration reversibility;
- promotion and abort thresholds.

Do not add rollout machinery to low-risk work without supporting context.

### Completion test

For a risky release, operators can limit exposure, recognize failure, and reverse or disable the affected behavior.

## §18.5 Observability

Specify signals required to detect failure and evaluate requirements:

- health and readiness;
- structured logs;
- correlation or operation identifiers;
- metrics;
- traces where established;
- job/run records;
- audit events;
- heartbeat or freshness signals;
- actionable alerts.

For each alert, define the precise trigger, severity, owner, and response.

### Completion test

Each important failure mode and operational NFR produces observable evidence, and every alert has an actionable response.

## §18.6 Backup and Disaster Recovery

Use whenever the system owns durable data.

Define:

- RPO and RTO based on supplied project needs;
- assets included;
- backup method and cadence;
- retention;
- encryption;
- off-site or failure-domain separation;
- restore-test cadence and owner;
- disasters covered;
- explicitly uncovered scenarios.

A backup without a tested restoration path is insufficient.

### Completion test

An operator can determine how much data may be lost, how quickly service must recover, what is protected, and how restoration is proven.

## §18.7 Documentation Deliverables

List actual documents required by the project and repository conventions, such as:

- user documentation;
- configuration reference;
- deployment and rollback runbooks;
- incident procedures;
- backup restoration;
- secret rotation;
- API or CLI documentation;
- operator handoff.

Remove irrelevant generic deliverables rather than promising documentation that will not exist.

### Completion test

Every audience that must use, operate, maintain, or recover the system has an identified documentation artifact.

### Avoid throughout §18

- generic deployment steps unrelated to the repository;
- secret values in configuration tables;
- health checks that do not test meaningful readiness;
- alerts without thresholds or owners;
- backup claims without restore testing;
- adding operational infrastructure not selected by the project design.

---

## §19 Implementation Plan

### Purpose

Capture the high-level, dependency-safe delivery sequence required by the specification.

This is not the detailed implementation plan produced by a later planning skill.

### Required coverage

Define milestones that:

- deliver coherent, observable increments;
- respect technical dependencies;
- identify the requirements or capabilities advanced;
- have concrete deliverables;
- have observable exit criteria;
- avoid building later functionality on an unproven foundation.

Use Waves only when the project intentionally releases breadth incrementally. Milestones describe outcomes, not file-by-file tasks.

The authoring skill may derive obvious ordering from established dependencies. It must not resolve missing architectural decisions or invent a detailed execution strategy.

### Completion test

An implementer understands the major implementation order and proof required at each boundary, while a later planning skill still has meaningful task decomposition to perform.

### Avoid

- line-by-line implementation instructions;
- naming files and functions not established by design;
- introducing new scope or requirements;
- retaining irrelevant template milestones;
- exit criteria such as “milestone complete”;
- sequencing based only on convenience rather than dependencies.

---

## §20 Success Evaluation

### Purpose

Define how the project’s real-world outcome will be evaluated after release.

This differs from §17:

- §17 determines whether the implementation satisfies the specification.
- §20 determines whether the released system achieves the intended outcome.

### Required coverage

For each applicable outcome area, identify:

- target;
- measurement source;
- evaluation period or trigger where relevant;
- decision that follows success or failure.

Connect measures to §1 and §4. Include functionality, reliability, performance, cost, or operational usability only where meaningful to the project.

### Completion test

After release, an owner can gather the stated evidence and decide whether the project produced its intended value.

### Avoid

- copying acceptance criteria without a post-launch purpose;
- metrics unavailable from the observability design;
- vanity metrics with no decision consequence;
- targets unsupported by the supplied context;
- “monitor after launch” without a target or method.

---

## §21 Open Questions and Decisions

### Purpose

Make unresolved matters explicit without forcing the authoring skill to invent answers.

### Required coverage

Each open question must include:

- a decision-shaped question;
- the current assumption, when work may proceed provisionally;
- whether it blocks affected work or approval;
- owner;
- point by which it must be resolved;
- current status.

Use blocking status narrowly. A question is blocking when proceeding would require a consequential unsupported decision or could invalidate affected work.

Remove or update questions already answered by authoritative context.

### Completion test

Every material unresolved ambiguity has an owner and disposition, and no blocking question is concealed inside prose or an assumption table.

### Avoid

- generic questions such as “What database should we use?” without context;
- unanswered questions whose resolution does not affect the project;
- using an assumption to hide a blocking decision;
- assigning every question to the user by default;
- retaining answered questions as Open.

---

## Deviations Log

### Purpose

Record implementation divergence after implementation begins.

The authoring skill normally leaves this section empty after removing template example rows. It must not predict hypothetical deviations.

During implementation, each entry must identify:

- affected requirement or section;
- actual divergence;
- reason;
- approval state.

### Completion test

The approved specification remains intact while actual departures are visible and reviewable.

### Avoid

- silently editing requirements to match the implementation;
- using deviations to introduce unapproved scope;
- recording ordinary implementation choices as deviations;
- prepopulating speculative rows.

---

## References

### Purpose

Identify authoritative material used to understand, constrain, or verify the specification.

### Required coverage

Include applicable:

- ADRs;
- prior specifications;
- architecture documents;
- issues or approved design artifacts;
- API and data contracts;
- repository-relative source references;
- external standards;
- provider documentation;
- legal, license, or terms-of-service sources.

Prefer stable, repository-relative references for project material. Identify versions or dates where external material may change.

### Completion test

A reviewer can locate the evidence behind consequential context, constraints, contracts, and design decisions.

### Avoid

- dumping every document inspected;
- citing material not actually used;
- using search-result pages instead of authoritative sources;
- relying on raw URLs where repository conventions require references;
- treating the References section as a substitute for explaining rationale.

---

# Appendices

## Appendix A — ID Conventions

Preserve the canonical appendix for the selected profile.

Use official standard tooling to allocate and validate IDs when available. Do not maintain a separate prefix registry in the skill.

The authoring skill must:

- assign each semantic item a stable ID;
- avoid renumbering IDs because priority or order changes;
- remove unused example rows;
- use the prefixes available to the selected profile.

## Appendix B — Agent Implementation Contract

Preserve the canonical contract.

The authoring skill should verify that the completed specification gives a future implementer enough information to obey the contract, particularly:

- explicit requirements;
- preserved non-goals and constraints;
- visible open questions;
- measurable verification;
- high-level milestone order.

Do not add skill-specific workflow instructions to this appendix.

## Appendix C — Optional Modules

Include only modules applicable to the established project design. Delete unused modules according to the canonical template.

### C.1 External Data Integration

For each applicable source or destination, cover:

- purpose;
- direction and access method;
- authentication reference;
- trigger or cadence;
- data contract and schema validation;
- rate, cost, and terms restrictions;
- retry and failure isolation;
- raw-payload retention;
- duplicate and identity handling;
- health reporting.

Do not assume every integration uses the example adapter shape.

### C.2 Scheduled Work, Throttling, and Circuit Breaker

For applicable jobs, define:

- schedule and timezone behavior;
- jitter;
- concurrency;
- rate and cost limits;
- retry classification and caps;
- circuit-breaker thresholds;
- pause and recovery behavior;
- status visibility and notification.

Do not invent rate-control infrastructure when scheduling or provider limits do not require it.

### C.3 Identity / Entity Resolution

Where records are matched or merged, define:

- normalization;
- authoritative identifiers;
- exact and rule-based matching;
- ambiguity handling;
- confidence and review requirements;
- provenance;
- reversibility and correction.

Do not introduce fuzzy or probabilistic matching unless the established design requires it.

### C.4 Scoring / Ranking / Decision Logic

For automated decisions, define:

- exact inputs and sources;
- required versus optional inputs;
- validation and fallback behavior;
- algorithm, thresholds, and versioning;
- treatment of missing or low-confidence data;
- explanation and provenance;
- review, override, or appeal path where applicable.

Do not invent formulas or weights absent from the supplied design.

### C.5 Relational Schema Examples

This subsection is a depth reference, not project content.

Do not copy its example schema into the specification. Use it only to judge whether an actual relational schema has comparable specificity around keys, constraints, defaults, indexes, relationships, and provenance.

## Appendix D — Tailoring

Preserve the canonical appendix for the selected profile.

Use it to confirm:

- the smallest appropriate profile was selected;
- conditional sections were handled correctly;
- a profile upgrade is required when supplied context exceeds the current tier.

Do not place project-specific tailoring rules here unless the canonical template explicitly calls for them.

---

# Review-Readiness Gate

A specification is ready for semantic review only when all of the following are true:

1. The canonical template and profile remain structurally intact.
2. Every applicable section contains all relevant supplied context.
3. Every deleted or not-applicable section has the required explanation.
4. No material fact, requirement, or design decision was invented.
5. Unknowns are represented as assumptions or open questions.
6. No unresolved placeholder or template example remains.
7. Goals, requirements, architecture, workflows, tests, and milestones are mutually consistent.
8. Every requirement is atomic and verifiable.
9. Every consequential interface, failure mode, security boundary, and operational responsibility present in the context is represented.
10. No section relies on generic filler in place of project-specific information.
11. Official `project-spec` validation and linting pass when those tools are authoritative or available.
12. Any fallback-only result is clearly identified as preflight rather than official validation.
```
