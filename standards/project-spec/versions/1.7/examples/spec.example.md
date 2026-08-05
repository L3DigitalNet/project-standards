---
spec_id: SPEC-0001
title: 'Nightly Backup Verification Script'
status: approved # draft | review | approved | superseded
profile: light # this is the Light template; see header note for sibling profiles
owner: 'platform-team'
implementer: 'coding-agent'
created: '2026-07-05'
last_reviewed: '2026-07-05'
supersedes: null # SPEC id this replaces, if any
superseded_by: null # filled in when this spec is retired
related:
  adrs: []
  tickets: []
  repositories: []
  prior_specs: []
---

# `Nightly Backup Verification Script` — Specification (Light)

> This example is filled in and `approved`, illustrating a completed Light-tier spec — the state a real spec reaches after authoring, not the state `spec new` scaffolds it in. A freshly scaffolded spec still carries bracketed placeholder text and template guidance blockquotes; `project-standards spec lint` flags exactly that (`SL-PLACEHOLDER`, `SL-GUIDANCE`), and this document lints clean.

---

## Revision History

| Version | Date         | Author         | Change        |
| ------- | ------------ | -------------- | ------------- |
| 0.1     | `2026-07-05` | `coding-agent` | Initial draft |

**Spec lifecycle:** This document is **living until `approved`**, then **change-controlled**: post-approval edits require a new revision row and, for scope-affecting changes, re-approval by the owner. Implementation deviations are recorded in the [Deviations Log](#deviations-log), not silently patched into requirements. When replaced, set `status: superseded` and `superseded_by:` in the frontmatter.

---

## 1. Purpose & Background

Nightly backups run unattended via cron, and nobody finds out a backup silently failed — or completed but is unrestorable — until someone actually needs to restore from it. That gap has caused a near-miss before: a corrupted archive went undetected for eleven days because the backup job itself exited `0` even though the archive it wrote was empty.

This project adds a small script, run immediately after the nightly backup job, that confirms an archive for the last 24 hours exists and that a sample table restores cleanly from it — then pages the on-call channel if either check fails. The first release optimizes for catching total-failure and corruption cases cheaply; it deliberately does not attempt a full restore-and-diff every night, since that would take longer than the backup window allows.

> This project provides automated nightly verification of backup completeness and restorability so that the platform team can detect a broken backup within 24 hours, instead of discovering it during an actual disaster-recovery attempt.

---

## 2. Scope

### 2.1 In Scope

- Confirming a backup archive for the previous 24 hours exists at the configured storage location.
- Restoring one sample table from that archive into a scratch database and comparing its row count against a recorded baseline.
- Alerting the existing on-call channel when either check fails.

### 2.2 Out of Scope (Non-Goals — never)

Things this system is **intentionally never** going to do. The reason column prevents relitigating the exclusion later.

| ID | Non-Goal | Reason |
| --- | --- | --- |
| NG-001 | Replacing or reconfiguring the backup job itself | Out of scope for a verification script; the backup job is a separately owned, already-working system. |

### 2.3 Won't Have in v1 (deferred — not never)

Things that are goals eventually but **excluded from this release** to control scope. Distinct from Non-Goals: these have a revisit trigger.

| ID | Deferred Capability | Why Deferred | Revisit When |
| --- | --- | --- | --- |
| WH-001 | Full nightly restore-and-diff of every table | Would exceed the nightly backup window; sampling is cheaper | A false-negative from sampling is observed in production |

### 2.4 Boundaries

| Boundary | Description |
| --- | --- |
| System owns | The verification script and its recorded row-count baseline file. |
| System depends on | The backup storage location, the scratch restore target, the on-call alert channel. |
| System does not own | The nightly backup job, the production database it backs up. |

---

> **Sections §3–§6 are Standard/Full-tier** (Context, Goals, Stakeholders, Glossary) and are intentionally omitted at the Light profile.

## 7. Requirements

> At the Light profile, Requirements is functional-only (§7.1). Non-functional, interface, and data requirements (§7.2–§7.4) are Standard-tier.
>
> **Quality rule:** Each requirement is one testable statement with a stable ID, a rationale, an acceptance criterion, and a priority. Priorities: **Must** (release-blocking), **Should** (important, briefly deferrable), **Could** (nice-to-have, must not delay release). Anything "Won't" belongs in §2.3, not here.

### 7.1 Functional Requirements

| ID | Requirement | Rationale | Acceptance Criteria | Priority |
| --- | --- | --- | --- | --- |
| FR-001 | The system shall exit non-zero and page on-call when no backup archive dated within the last 24 hours exists at the configured storage location. | Silent total-failure is the exact gap this project closes. | Delete the newest archive in a test bucket; verification exits non-zero and the test alert fires. | Must |
| FR-002 | The system shall restore one sample table from the most recent archive into a scratch database and compare its row count against a recorded baseline. | Catches corruption/truncation that a completed backup job would still exit `0` on. | Feed a truncated archive fixture; verification detects the row-count mismatch and pages on-call. | Should |

---

> **Sections §8–§16 are Standard/Full-tier** (Architecture, Data Model, Behavior, UI/API, Errors, Security, Capacity, Risks, Compliance) and are intentionally omitted at the Light profile.

## 17. Testing and Acceptance

> At the Light profile, this is the Definition of Done only (§17.1). Test strategy (§17.2) and the traceability matrix (§17.3) are Standard-tier.

### 17.1 Definition of Done

- [x] All **Must** requirements implemented; acceptance criteria pass.
- [x] Automated tests cover required behavior, error cases, and edge cases.
- [x] Every Must/Should requirement maps to a passing verification (test, command, or documented manual check).
- [x] README / usage docs updated.
- [x] Security-sensitive behavior reviewed.
- [x] Deviations Log reviewed and accepted by owner.
- [x] No known blocking defects.

---

> **Sections §18–§20 are Standard/Full-tier** (Deployment, Implementation Plan, Success Evaluation) and are intentionally omitted at the Light profile.

## 21. Open Questions and Decisions

Questions may proceed on a recorded **current assumption** unless marked blocking. Blocking questions halt the affected work until answered ([Appendix B.1](#b1-implementation-rules)).

| ID | Question | Current Assumption | Blocking? | Owner | Needed By | Status |
| --- | --- | --- | --- | --- | --- | --- |
| OQ-001 | Should verification check every backup archive or only the newest one? | Only the newest archive is checked nightly; older archives are covered by the (separately owned) restore-test runbook. | No | platform-team | 2026-07-05 | Answered |

---

## Deviations Log

Maintained by the **implementer** during the build ([Appendix B](#appendix-b-agent-implementation-contract)). Any divergence from this spec is recorded here — never silently patched into requirements text.

| ID | Spec Reference | Deviation | Reason | Approved? |
| --- | --- | --- | --- | --- |
| DEV-001 | FR-002 | Restored a fixed table (`accounts`) each night instead of a rotating random sample. | Simpler to implement and to set a stable row-count baseline against. | Yes |

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
