---
spec_id: SPEC-7F3Q
title: Example Project
status: draft
profile: light
owner: Example Team
implementer: Example Agent
created: '2026-07-04'
last_reviewed: '2026-07-04'
supersedes: null # SPEC id this replaces, if any
superseded_by: null # filled in when this spec is retired
related:
  adrs: []
  tickets: []
  repositories: []
  prior_specs: []
---

# `Project Feature Name` — Specification (Light)

> Template notes:
>
> This is the **Light** spec template — for scripts, small tools, and single-session agent tasks. Two sibling templates exist for larger work: `spec-standard-template.md` (typical features and services) and `spec-full-template.md` (multi-service systems, durable data, external integrations). If this project outgrows Light, copy your content into the next template up (see [Appendix D](#appendix-d-upgrading-this-spec)).
>
> **Numbering is stable across all three profiles** (it matches `spec-full-template.md`). A Light spec omits the Standard/Full-only sections, so section **and appendix** numbers have intentional gaps — e.g. this template jumps §2 → §7 and A → B → D. That is expected, not missing content; it means a section keeps the same number no matter which profile a spec uses, and upgrading a tier only _adds_ sections.
>
> 1. Replace `angle bracket` placeholders. Delete guidance blockquotes and "Suggested prompts" lists once used.
> 2. **Prose-first for the narrative section** (Purpose); tables only for enumerable facts. Do not fill a table with one-word cells when a paragraph would explain more.
> 3. Requirements must be specific, testable, necessary, feasible, traceable, and unambiguous. Use "The system shall…" for mandatory behavior. Never write "fast," "easy," "robust," or "secure" without a measurable criterion.
>
> **Standards note:** Structure and terminology borrow from ISO/IEC/IEEE 29148:2018 (requirements) without claiming formal compliance. (IEEE 830-1998 is superseded; do not use it as an authority.)

---

## Revision History

| Version | Date           | Author     | Change        |
| ------- | -------------- | ---------- | ------------- |
| 0.1     | `YYYY MM DD` | `author` | Initial draft |

**Spec lifecycle:** This document is **living until `approved`**, then **change-controlled**: post-approval edits require a new revision row and, for scope-affecting changes, re-approval by the owner. Implementation deviations are recorded in the [Deviations Log](#deviations-log), not silently patched into requirements. When replaced, set `status: superseded` and `superseded_by:` in the frontmatter.

---

## 1. Purpose & Background

Describe, in prose, the problem this software, feature, or subsystem solves.

Include:

- The user, business, operational, or technical problem, and who has it.
- What event, pain point, or opportunity triggered the work now.
- What outcome should exist after successful implementation.
- The intended first-release scope: what is deliberately optimized for now, and what must remain possible later.
- The compounding value or long-term asset, if any (accumulated data history, audit trail, automation reliability, reusable platform capability, reduced toil).

Author notes:

- Who needs this system, and what job are they trying to complete?
- Why are existing tools insufficient?
- What must the MVP accomplish without overbuilding?
- What future directions should not be blocked by early design choices?

Example framing:

> This project provides `capability` so that `user system` can `desired outcome` without `current pain or failure mode`.

---

## 2. Scope

### 2.1 In Scope

- `included capability`
- `included workflow`
- `included integration`

### 2.2 Out of Scope (Non-Goals — never)

Things this system is **intentionally never** going to do. The reason column prevents relitigating the exclusion later.

| ID     | Non-Goal                                 | Reason  |
| ------ | ---------------------------------------- | ------- |
| NG-001 | `thing we are intentionally not doing` | `why` |

### 2.3 Won't Have in v1 (deferred — not never)

Things that are goals eventually but **excluded from this release** to control scope. Distinct from Non-Goals: these have a revisit trigger.

| ID | Deferred Capability | Why Deferred | Revisit When |
| --- | --- | --- | --- |
| WH-001 | `feature deferred to avoid scope creep` | `cost risk uncertainty missing validation` | `trigger milestone metric user demand date` |

### 2.4 Boundaries

| Boundary | Description |
| --- | --- |
| System owns | `data behavior APIs jobs UI files` |
| System depends on | `external services databases queues hardware user actions` |
| System does not own | `systems data decisions or processes outside this scope` |

---

> **Sections §3–§6 are Standard/Full-tier** (Context, Goals, Stakeholders, Glossary) and are intentionally omitted at the Light profile.

## 7. Requirements

> At the Light profile, Requirements is functional-only (§7.1). Non-functional, interface, and data requirements (§7.2–§7.4) are Standard-tier.
>
> **Quality rule:** Each requirement is one testable statement with a stable ID, a rationale, an acceptance criterion, and a priority. Priorities: **Must** (release-blocking), **Should** (important, briefly deferrable), **Could** (nice-to-have, must not delay release). Anything "Won't" belongs in §2.3, not here.

### 7.1 Functional Requirements

| ID | Requirement | Rationale | Acceptance Criteria | Priority |
| --- | --- | --- | --- | --- |
| FR-001 | The system shall `specific behavior`. | `why this exists` | `how to verify it` | Must |
| FR-002 | The system shall `specific behavior`. | `why this exists` | `how to verify it` | Should |

---

> **Sections §8–§16 are Standard/Full-tier** (Architecture, Data Model, Behavior, UI/API, Errors, Security, Capacity, Risks, Compliance) and are intentionally omitted at the Light profile.

## 17. Testing and Acceptance

> At the Light profile, this is the Definition of Done only (§17.1). Test strategy (§17.2) and the traceability matrix (§17.3) are Standard-tier.

### 17.1 Definition of Done

- [ ] All **Must** requirements implemented; acceptance criteria pass.
- [ ] Automated tests cover required behavior, error cases, and edge cases.
- [ ] Every Must/Should requirement maps to a passing verification (test, command, or documented manual check).
- [ ] README / usage docs updated.
- [ ] Security-sensitive behavior reviewed.
- [ ] Deviations Log reviewed and accepted by owner.
- [ ] No known blocking defects.

---

> **Sections §18–§20 are Standard/Full-tier** (Deployment, Implementation Plan, Success Evaluation) and are intentionally omitted at the Light profile.

## 21. Open Questions and Decisions

Questions may proceed on a recorded **current assumption** unless marked blocking. Blocking questions halt the affected work until answered ([Appendix B.1](#b1-implementation-rules)).

| ID | Question | Current Assumption | Blocking? | Owner | Needed By | Status |
| --- | --- | --- | --- | --- | --- | --- |
| OQ-001 | `question` | `assumption this spec proceeds on` | No | `owner` | `milestone date` | Answered |

---

## Deviations Log

Maintained by the **implementer** during the build ([Appendix B](#appendix-b-agent-implementation-contract)). Any divergence from this spec is recorded here — never silently patched into requirements text.

| ID | Spec Reference | Deviation | Reason | Approved? |
| --- | --- | --- | --- | --- |
| DEV-001 | `FR xxx n` | `what was done differently` | `why` | No / Pending |

---

## Appendix A: ID Conventions

Stable IDs allow requirements to be referenced from commits, tests, issues, ADRs, and review comments — and let an implementer's completion claims be mechanically checked. Section numbers below match `spec-full-template.md`, so an ID keeps the same "Defined In" reference across every profile.

| Prefix | Meaning                     | Defined In     |
| ------ | --------------------------- | -------------- |
| `NG-`  | Non-goal (never)            | §2.2           |
| `WH-`  | Won't have in v1 (deferred) | §2.3           |
| `FR-`  | Functional requirement      | §7.1           |
| `OQ-`  | Open question               | §21            |
| `DEV-` | Deviation                   | Deviations Log |

Higher-tier ID prefixes (`G- A- C- NFR- IR- DR- D- AW- EC- ERR- R- MS-`) are defined in the Standard/Full templates. Priority values (`Must/Should/Could`) are column values, not ID prefixes — IDs never change when priorities do.

---

## Appendix B: Agent Implementation Contract

Binding when this spec is implemented by a coding agent. (Applies equally well to human contractors.)

### B.1 Implementation Rules

The implementer shall:

- Read this entire specification before making changes; per session thereafter, re-read at minimum §7 (Requirements), §21 (Open Questions), and the Deviations Log.
- Preserve all explicit non-goals and won't-haves.
- Treat **Must** requirements as mandatory and **blocking** open questions as hard stops for the affected work.
- On encountering underspecified behavior: file an `OQ-` row **with a proposed default assumption** and proceed on it only if non-blocking — never guess silently.
- On any divergence from the spec: record a `DEV-` row (spec reference, what, why) rather than adapting silently.
- Add or update tests for every implemented requirement.
- Prefer small, reviewable changes; avoid broad refactors unless the spec requires them.
- Document any discovered mismatch between the spec and existing code as a `DEV-` or `OQ-` row.

### B.2 Prohibited Behaviors

The implementer shall not:

- Invent requirements not present in this spec.
- Remove existing behavior unless explicitly required.
- Introduce external services or dependencies not agreed with the owner without an approved `OQ-`.
- Store secrets in source control or print them in CI logs.
- Ignore failing tests unrelated to the change without documenting them.
- Treat examples as exhaustive or normative unless explicitly stated.
- Mark a requirement complete without a test or check that proves it.

### B.3 Required Completion Report (verification gate)

At completion, provide:

- Summary of changes and files changed.
- **Each Must requirement mapped to the test or command that proves it.** Claims without verification are not accepted.
- Tests added or changed.
- Deviations (`DEV-` rows) and their approval status.
- Known limitations and remaining open questions.
- Documentation updated (README / usage).

### B.4 Session Handoff

For multi-session implementations: record in-progress requirement IDs and unresolved `OQ-`/`DEV-` items in the repository's session-state/handoff documents at the end of each session, per the repo's documentation convention. The spec records _what and why_; handoff docs record _where work stands_.

---

> **Appendix C (Optional Modules) is Full-tier** — external-integration, scheduling, entity-resolution, and scoring modules — and is intentionally omitted at the Light profile.

## Appendix D: Upgrading This Spec

Pick the smallest profile that fits; upgrade if the project grows.

| Upgrade to | When | Adds |
| --- | --- | --- |
| **Standard** (`spec-standard-template.md`) | Typical features and services | §3 Context, §4 Goals, §6 Glossary, §7.2–§7.4, §8 Architecture, §9 Data Model, §10 Behavior, §11 UI/API, §12 Error Handling, §13 Security, §17.2–§17.3 Testing, §18 Deployment, §19 Implementation Plan, References |
| **Full** (`spec-full-template.md`) | Multi-service systems, durable data, external integrations, or multiple stakeholders | Everything in Standard plus §5 Stakeholders, §8.4 Alternatives, §8.6 Dependency Policy, §14 Capacity, §15 Risks, §16 Compliance, §18.4 Rollout Controls, §20 Success Evaluation, §19 Waves, and Appendix C optional modules |

Because numbering is stable across profiles, upgrading is **additive**: insert the missing sections at their canonical numbers, set `profile:` in the frontmatter, and no existing section or ID reference has to change.
