<!-- Imported 2026-08-06 as the preserved design input for the github-workflow
     package design. The document predates this repository's Markdown structure
     standard and numbers its sections as top-level headings; restructuring 41
     headings would rewrite a historical record, so MD025/MD001 are disabled
     file-wide instead. All other lint rules remain active. -->
<!-- markdownlint-disable MD025 MD001 -->

# GitHub Repository Administration Standard for Local AI Agents

**Date:** August 6, 2026 **Applies to:** L3DigitalNet repositories and local development workflows **Primary execution environment:** Local workstation agents, principally Claude Code and Codex CLI **GitHub plan constraint:** L3DigitalNet organization on GitHub Free **GitHub-hosted AI policy:** Optional; not part of the core architecture

## Executive Summary

GitHub should function as the **durable control plane, system of record, policy boundary, and audit history** for repository work. AI reasoning and implementation should remain primarily on the local workstation using Claude Code, Codex CLI, or future equivalent agents.

The architecture should therefore not depend on GitHub Copilot coding agents, GitHub Agentic Workflows, or any other GitHub-hosted model execution. Those facilities may be used selectively for narrow, token-light, event-local tasks where their proximity to GitHub provides a clear advantage, but the repository-management model must remain fully functional without them.

The recommended operating model is:

```text
GitHub
  ├── Issues        → authoritative work contracts
  ├── Issue Fields  → typed workflow and planning metadata
  ├── PRs           → authoritative implementation and verification history
  ├── Projects      → derived operational views
  ├── Milestones    → bounded delivery/release grouping
  ├── ADRs/specs    → durable architectural and behavioral authority
  ├── Actions       → deterministic independent validation
  └── Rulesets      → non-negotiable policy enforcement

Local workstation
  ├── Claude Code   → planning, implementation, investigation
  ├── Codex CLI     → implementation, review, verification
  └── Coordinators  → dispatch, claims, metadata synchronization
```

The central design principle is:

> **Use agents where interpretation is required and deterministic mechanisms where correctness should not depend on interpretation.**

GitHub-native objects should preserve durable intent, execution evidence, dependencies, decisions, and status. Local agent sessions should be treated as ephemeral workers that consume and update that durable state.

GitHub Issue Fields, which became generally available to organizations on GitHub Free in July 2026, are particularly useful for this model because they provide organization-wide typed metadata attached directly to Issues rather than to a single Project. GitHub explicitly describes Issue Fields as the source of truth when the same metadata is also exposed through Projects.

## Bottom Line / Recommendation

Standardize the repository-administration model around five rules:

1. **An Issue is the canonical unit of authorized work.**
2. **A PR is the canonical record of executing and validating that work.**
3. **Typed Issue Fields hold cross-repository operational metadata.**
4. **Projects are projections of canonical Issue state, not an independent database.**
5. **Local agents perform reasoning and implementation; deterministic GitHub mechanisms enforce policy.**

For Issues, standardize on these seven organization-level fields:

| Field              | Purpose                                      |
| ------------------ | -------------------------------------------- |
| **Workflow**       | Lifecycle and work eligibility               |
| **Priority**       | Ordering and commitment                      |
| **Size**           | Change/review surface                        |
| **Change risk**    | Risk introduced by implementation            |
| **Execution mode** | Authorized level of agent autonomy           |
| **Target date**    | Real deadline when one exists                |
| **Severity**       | Consequence of an existing defect; Bugs only |

Together with GitHub's native Issue Type, Assignee, Milestone, sub-issue, dependency, and linked-PR relationships, these fields provide enough structure for deterministic agent dispatch and useful reporting without turning GitHub into an over-engineered project-management system.

---

# 1. Design Constraints

## 1.1 Primary agents are local

Claude Code and Codex CLI operating on the development workstation are the normal execution environment.

They may interact with GitHub through mechanisms such as:

- `git`
- GitHub CLI (`gh`)
- GitHub REST or GraphQL APIs
- GitHub MCP
- repository-specific scripts or coordinators

The GitHub object model must therefore be **agent-provider independent**.

Nothing important should depend on whether the active worker happens to be:

- Claude Code
- Codex CLI
- a local LLM
- a future coding agent
- a human

Worker identity is execution metadata, not repository work semantics.

## 1.2 GitHub-hosted AI is non-foundational

The repository system must not require:

- Copilot coding agent
- GitHub Agentic Workflows
- GitHub-hosted Claude or Codex
- GitHub AI credits

GitHub-hosted AI may still be appropriate for small tasks such as:

- lightweight Issue triage
- short Issue clarification
- classification
- PR summarization
- small repository-status summaries
- simple documentation checks

These should remain optional optimizations.

This restriction also prevents uncertainty around GitHub AI-credit accounting between the personal Copilot Pro+ entitlement and repositories owned by L3DigitalNet from becoming an architectural dependency.

## 1.3 GitHub Free must be sufficient

The control plane should use features available to L3DigitalNet without requiring an organization-plan upgrade unless a future capability produces enough value to justify it.

Issue Fields satisfy this requirement. They are generally available to GitHub organizations on Free, Team, and Enterprise plans. GitHub provides four default organization fields—`Priority`, `Effort`, `Start date`, and `Target date`—which can be customized or supplemented.

---

# 2. Architectural Principle: Separate State, Execution, and Enforcement

The repository administration system should have three conceptual planes.

## 2.1 Control plane — GitHub

GitHub answers:

- What work exists?
- Why does it exist?
- Is it approved?
- Is it ready?
- What blocks it?
- What is its priority?
- Who or what is working on it?
- What implementation satisfies it?
- Was that implementation validated?
- What ultimately happened to the work?

## 2.2 Execution plane — local agents

Local agents answer:

- What does the repository currently do?
- What implementation is appropriate?
- What files must change?
- What tests are necessary?
- What unexpected conditions exist?
- What follow-up work was discovered?
- Does the implementation satisfy the Issue?

Agents operate on repository state but should not define the repository's authority model ad hoc.

## 2.3 Enforcement plane — deterministic mechanisms

GitHub Actions, rulesets, validators, scripts, and repository policy answer:

- Is this branch allowed to merge?
- Did required checks pass?
- Is required metadata present?
- Is the Issue eligible for dispatch?
- Does the PR link to an authorized Issue?
- Is a high-risk change receiving the required review?
- Is a state transition legal?

The model should not be responsible for deciding whether its own output passes a deterministic rule.

---

# 3. Canonical GitHub Object Model

## 3.1 Issue — authoritative work contract

An Issue should represent a discrete unit of authorized work.

It should answer:

- What outcome is required?
- Why is the work necessary?
- What is in scope?
- What is explicitly out of scope?
- What constitutes completion?
- What constraints govern the solution?
- What dependencies exist?

The Issue should contain enough durable information that a new Claude Code or Codex session can understand the work without requiring the original agent conversation.

An Issue is therefore more than a reminder.

It is a **work contract**.

## 3.2 Pull request — authoritative execution record

A PR should represent an implementation attempt against one or more authorized Issues.

It owns:

- the patch
- commits
- implementation notes
- validation results
- CI results
- review findings
- revisions
- final merge disposition

The Issue explains **what and why**.

The PR explains **how and with what evidence**.

For nontrivial work, PRs should explicitly link their governing Issue.

## 3.3 Project — derived operational view

Projects should provide:

- queues
- dashboards
- filtered views
- planning views
- blocked-work views
- priority views
- release views
- charts

They should not become another authoritative work database.

GitHub explicitly recommends centralizing Issue metadata in Issue Fields rather than maintaining equivalent Project-specific fields. Issue Fields live on the Issue itself and remain consistent across Projects, whereas Project fields can have different values for the same Issue in different Projects.

Therefore:

```text
Issue Field = authoritative
Project column/view = projection
```

## 3.4 ADRs and specifications — durable decisions

Important architectural or behavioral constraints should remain version-controlled in the repository.

Examples include:

- ADRs
- specifications
- compatibility contracts
- execution plans
- security policy
- coding standards

A closed Issue or PR should not become the only place where a durable architectural decision exists.

The Issue or PR should link to the governing document.

## 3.5 Milestones — bounded delivery objectives

Use Milestones for genuine bounded objectives such as:

- a release
- a migration phase
- a launch
- a defined project increment

Do not use Milestones merely as another priority field.

---

# 4. Standard Issue Types

Use a deliberately small Issue Type vocabulary.

## Bug

Existing behavior violates an intended contract.

Examples:

- regression
- incorrect output
- crash
- reliability defect
- broken integration

## Feature

Introduces a new user-visible or system-visible capability.

## Task

Bounded work that is neither a defect nor a new capability.

Examples include:

- maintenance
- refactoring
- dependency work
- documentation
- CI changes
- infrastructure work
- cleanup

## Initiative

A parent planning object representing a larger objective implemented through sub-issues.

An Initiative should generally not itself be dispatched to an implementation agent.

## Research

A bounded investigation intended to reduce uncertainty and produce a durable result.

A Research Issue must still have acceptance criteria.

Example:

> Determine whether library X satisfies requirements A–D and publish the recommendation in `docs/research/...`.

Research is work, not merely an open question.

---

# 5. Standard Organization-Level Issue Fields

GitHub Issue Fields are appropriate for data that is:

- structured
- organization-wide
- relatively low-cardinality
- useful for filtering, querying, or automation
- semantically applicable across repositories

GitHub allows up to 25 organization Issue Fields. That capacity should not be interpreted as a target.

The recommended baseline uses seven.

---

# 6. Field: Workflow

**Type:** Single select

**Applies to:** All Issue Types

## Values

| Value | Meaning |
| --- | --- |
| **Inbox** | Captured but not fully triaged |
| **Needs definition** | Scope, acceptance criteria, governing decision, or other required information is insufficient |
| **Ready** | Authorized, sufficiently specified, unblocked, and eligible for work |
| **In progress** | Active implementation or investigation is occurring |
| **Blocked** | Work cannot continue until a defined dependency or decision is resolved |
| **In review** | Deliverable exists and awaits acceptance or verification |
| **Done** | Acceptance criteria have been satisfied |
| **Dropped** | Intentionally abandoned, rejected, obsolete, duplicate, or superseded |

## Purpose

`Workflow` should be the canonical operational lifecycle field.

It answers a different question from GitHub's native open/closed state.

Native state answers:

```text
Is this Issue active?
```

Workflow answers:

```text
Where is this active work in its lifecycle?
```

## Required synchronization

Terminal states should remain consistent:

```text
Workflow = Done
    → Issue closed as completed

Workflow = Dropped
    → Issue closed as not planned

Issue reopened
    → Workflow must return to a valid nonterminal state
```

This synchronization should eventually be deterministic.

Do not require an agent to remember to maintain both independently.

## Ready semantics

`Ready` is particularly important because local-agent automation can treat it as an eligibility boundary.

`Ready` should mean:

- sufficient acceptance criteria exist
- no blocking decision remains
- required dependencies are satisfied
- required planning is complete
- work has been intentionally admitted to the executable queue

An agent should never infer readiness merely because an Issue is open.

---

# 7. Field: Priority

**Type:** Single select

**Applies to:** All Issue Types

## Values

| Value                  | Meaning                                   |
| ---------------------- | ----------------------------------------- |
| **P0 — Immediate**     | Interrupt current work                    |
| **P1 — Next**          | Committed near-term work                  |
| **P2 — Planned**       | Normal accepted backlog                   |
| **P3 — Opportunistic** | Worth doing when convenient               |
| **P4 — Someday**       | Valid work with no foreseeable commitment |

Leave Priority empty until triage if no deliberate prioritization has occurred.

## Important distinction

Priority is a scheduling decision.

It is not equivalent to:

```text
Priority ≠ Severity
Priority ≠ Change risk
Priority ≠ Size
```

A serious defect can be low priority if exposure is negligible.

A relatively minor defect can be P0 if it blocks a release.

---

# 8. Field: Size

**Type:** Single select

**Applies to:** Bug, Feature, Task, Research

## Values

| Value | Operational meaning |
| --- | --- |
| **XS** | Localized, obvious change with minimal review surface |
| **S** | One coherent behavior or component |
| **M** | Multiple interacting files/components or meaningful uncertainty |
| **L** | Cross-component work, migration, significant uncertainty, or substantial review surface |
| **XL** | Too large for direct execution; decomposition required |

## Size is not time

Do not define Size as:

- hours
- story points tied to time
- model-token estimates
- expected agent session duration

Agent-assisted development makes elapsed-time estimates particularly unstable.

Instead Size should represent:

- breadth
- coupling
- conceptual complexity
- uncertainty
- review burden

## XL invariant

```text
Size = XL
    → direct implementation prohibited
    → decompose into sub-issues
```

An XL Issue may remain as an Initiative or parent tracking object.

---

# 9. Field: Change Risk

**Type:** Single select

**Applies to:** Bug, Feature, Task

## Values

| Value | Meaning |
| --- | --- |
| **R1 — Low** | Localized, easily reversible, low coupling |
| **R2 — Moderate** | Meaningful behavior or compatibility implications |
| **R3 — High** | Significant trust boundary, persistence, concurrency, API, CI, or cross-system effects |
| **R4 — Critical** | Destructive, difficult-to-reverse, security-sensitive, release-control, infrastructure, or broad systemic consequences |

## Purpose

Change Risk measures:

> **How dangerous is implementing this change incorrectly?**

It does not measure:

> How bad is the existing problem?

That belongs to Severity for Bugs.

## Suggested policy mapping

| Risk | Baseline treatment |
| --- | --- |
| **R1** | Normal tests and review |
| **R2** | Acceptance-criteria trace plus focused regression coverage |
| **R3** | Independent review, negative testing, explicit rollback consideration |
| **R4** | Human-approved plan before implementation, independent verification, explicit recovery/rollback procedure |

For local agent orchestration, this field can eventually drive dispatch and review policy deterministically.

---

# 10. Field: Execution Mode

**Type:** Single select

**Applies to:** Bug, Feature, Task, Research

## Values

| Value | Meaning |
| --- | --- |
| **Unattended agent** | Authorized for autonomous dispatch to a local agent |
| **Interactive agent** | Agent implementation is allowed within a human-directed session |
| **Human only** | Agents may inspect or advise but not autonomously implement |

## Why this field matters

The primary agents are local and powerful.

An Issue being technically executable should not automatically mean an unattended process is authorized to execute it.

`Execution mode` therefore expresses **authority**, not capability.

## Do not encode model identity

Do not use values such as:

- Claude
- Codex
- GPT
- Local LLM
- Claude preferred
- Codex preferred

Model routing changes frequently and is not a durable property of the work.

Worker/model information belongs in:

- execution logs
- session evidence
- PR metadata
- agent-evaluation records

## Conservative default

Unattended execution should require affirmative authorization.

For example:

```text
new Issue
    → Interactive agent by default

explicit promotion
    → Unattended agent
```

High-risk work should not become unattended merely because an agent believes it can perform the task.

---

# 11. Field: Target Date

**Type:** Date

**Applies to:** Initiative, Feature, Task; optionally Bug and Research

Use Target Date only when a date has genuine semantic meaning.

Examples:

- release deadline
- contractual commitment
- upstream dependency
- deprecation date
- event date
- time-sensitive vulnerability remediation
- work that becomes materially less useful after a date

Do not populate Target Date merely because every Issue appears visually nicer with one.

Empty is a valid and expected state.

---

# 12. Field: Severity

**Type:** Single select

**Applies to:** Bug only

## Values

| Value | Meaning |
| --- | --- |
| **S0 — Critical** | Security compromise, corruption/data loss, unsafe operation, or system unusable |
| **S1 — High** | Core capability unusable with no acceptable workaround |
| **S2 — Moderate** | Material impairment with workaround or constrained exposure |
| **S3 — Low** | Minor defect, cosmetic behavior, narrow edge case, or negligible operational consequence |

## Severity versus Priority

Severity is factual:

```text
What consequence does the defect produce?
```

Priority is managerial:

```text
When should it be fixed relative to other work?
```

Keeping these separate enables much better triage.

---

# 13. Recommended Field Pinning

| Field          |   Bug    | Feature | Task | Initiative | Research |
| -------------- | :------: | :-----: | :--: | :--------: | :------: |
| Workflow       |    ✓     |    ✓    |  ✓   |     ✓      |    ✓     |
| Priority       |    ✓     |    ✓    |  ✓   |     ✓      |    ✓     |
| Size           |    ✓     |    ✓    |  ✓   |            |    ✓     |
| Change risk    |    ✓     |    ✓    |  ✓   |            |          |
| Execution mode |    ✓     |    ✓    |  ✓   |            |    ✓     |
| Target date    | Optional |    ✓    |  ✓   |     ✓      | Optional |
| Severity       |    ✓     |         |      |            |          |

Initiatives deliberately omit execution-oriented fields because the Initiative itself should normally not be directly implemented.

---

# 14. Native GitHub Metadata

Do not reproduce native relationships as custom fields.

## Issue Type

Canonical classification of the primary nature of the work.

## Assignee

Use Assignee for the entity accountable for the current work.

Do not create a duplicate `Owner` field.

Where local agents operate through the human GitHub identity rather than dedicated GitHub identities, actual agent identity should remain execution metadata rather than being overloaded into Assignee.

## Milestone

Canonical bounded delivery grouping.

Do not create a duplicate `Release` Issue Field unless a genuine requirement appears that Milestones cannot satisfy.

## Parent and sub-issues

Use native hierarchy.

Do not create:

- `Parent ID`
- `Epic`
- `Child issues` text lists

## Dependencies

Use GitHub-native blocking relationships wherever possible.

Do not maintain a free-text `Blocked by` field in parallel.

## Linked branches and PRs

Use GitHub's native relationships.

Do not create:

- `PR URL`
- `Implementation branch`
- `PR number`

as manually maintained Issue Fields.

## Open/closed disposition

Use native Issue state and close reason.

Workflow may mirror terminal semantics for operational purposes, but synchronization should be deterministic.

---

# 15. Label Standard

Labels remain useful for **multi-valued facets** and metadata that should apply to both Issues and PRs.

Recommended label namespaces:

```text
area/<component>

concern/security
concern/performance
concern/reliability
concern/compatibility
concern/documentation

source/audit
source/user-report
source/agent-found
source/dependency
```

Repository-specific `area/*` labels are particularly appropriate because components vary by repository.

## Do not use labels for typed Issue Field concepts

Avoid:

```text
priority/*
status/*
size/*
severity/*
risk/*
agent-ready
```

Those concepts should have one canonical typed representation.

GitHub now supports typed organization Issue Fields and exposes them consistently across repository Issue lists and Projects, making legacy label-based approximations unnecessary for these dimensions.

---

# 16. Information That Belongs in the Issue Body

Structured fields should not replace the work contract.

The Issue body should contain narrative or high-cardinality information.

Recommended canonical structure:

```markdown
## Outcome

What must become true when this Issue is complete.

## Context

Why the work exists and relevant background.

## Scope

What is included.

## Out of scope

Explicit boundaries where ambiguity would otherwise exist.

## Acceptance criteria

Observable conditions required for completion.

## Constraints

Relevant technical, architectural, compatibility, security, or repository-policy requirements.

## Evidence / references

Relevant reproduction information, logs, specifications, ADRs, external references, or prior work.

## Verification

Any specific validation required beyond normal repository policy.
```

Not every Issue requires every heading.

The principle is:

> Fields describe the work operationally; the body defines the work semantically.

---

# 17. Issue Forms

Issue Forms should improve capture quality, but they should not become a second metadata system.

Use Issue Forms to elicit:

- desired outcome
- reproduction information
- context
- acceptance criteria
- constraints
- evidence

Use Issue Fields for:

- Priority
- Workflow
- Size
- Risk
- Execution authorization
- Target Date
- Severity

Where field population cannot occur directly through the chosen Issue Form mechanism, a local administrative agent, GitHub API operation, or deterministic automation can populate the fields during triage.

GitHub exposes Issue Fields through its APIs and MCP integration, enabling agent tools to read and update those values programmatically.

---

# 18. Local-Agent Work Lifecycle

The recommended lifecycle is:

```text
Capture
   ↓
Inbox
   ↓
Triage
   ├── Dropped
   └── Needs definition
           ↓
         Ready
           ↓
     coordinator claim
           ↓
      In progress
           ↓
       draft PR
           ↓
       In review
           ↓
   ┌───────┴─────────┐
   ↓                 ↓
revision           accepted
   ↓                 ↓
In progress          Done
```

Blocked work branches from any active pre-review or implementation state:

```text
Ready / In progress
        ↓
      Blocked
        ↓
blocker resolved
        ↓
previous appropriate state
```

---

# 19. Agent Dispatch

A local coordinator should eventually query for eligible work rather than having agents independently search and self-claim arbitrary Issues.

Example eligibility query:

```text
Workflow = Ready
AND Execution mode = Unattended agent
AND no unresolved dependency
AND no live claim
AND repository policy passes
```

The coordinator then:

1. selects work according to Priority and policy
2. records or establishes the claim
3. dispatches the appropriate local worker
4. transitions Workflow to `In progress`
5. provides the Issue and governing repository context to the agent

Agents should not autonomously reinterpret `P1`, `Ready`, or similar metadata as authorization to execute.

---

# 20. Claiming

When multiple local agents can execute concurrently, claiming must become deterministic.

The undesirable model is:

```text
Claude searches Ready Issues
Codex searches Ready Issues

both independently choose Issue #42
```

The preferred model is:

```text
Coordinator
    ↓
atomically chooses Issue #42
    ↓
assigns claim
    ↓
dispatches exactly one worker
```

The claim mechanism may eventually use:

- coordinator-owned local state
- a GitHub field
- assignment
- a narrowly scoped label
- another deterministic registry

The important property is not the implementation mechanism.

The invariant is:

> **Only one execution authority may hold a live claim on a directly executable Issue unless explicit parallelism is designed into that Issue.**

---

# 21. Pull Request Standard

A nontrivial implementation PR should reference its governing Issue.

Recommended PR content:

## Summary

What changed.

## Governing work

Issue or plan being implemented.

## Acceptance coverage

How the implementation satisfies the Issue's acceptance criteria.

## Verification

Commands and checks actually executed.

## Risk / compatibility notes

Material behavioral, migration, security, or compatibility implications.

## Follow-up

Discovered work intentionally excluded from the current PR.

Follow-up work that will survive the PR should become Issues.

Do not leave significant future work only as:

- review comments
- prose TODOs in the PR
- agent-session notes

---

# 22. Draft PR Policy

For substantial work, local agents should normally create a draft PR once a coherent implementation exists and externalized review or CI becomes useful.

A draft PR gives GitHub a durable representation of active execution without implying acceptance.

However, because the agent itself runs locally and remains observable, there is no need to require a draft PR immediately when a task begins merely to prove that an agent is working.

The correct boundary is:

> Open the PR when repository-visible implementation state becomes useful.

---

# 23. Review Model

Agent-generated code should not be trusted merely because another agent reports that it looks correct.

Use layers:

```text
Implementation agent
        ↓
Deterministic validation
        ↓
Independent review agent where useful
        ↓
Human acceptance for consequential changes
```

For higher-risk work, review should explicitly examine:

1. acceptance-criteria coverage
2. repository conventions and governing ADRs
3. unintended scope expansion
4. test adequacy
5. negative-path behavior
6. rollback or recovery implications
7. security and trust boundaries
8. CI or policy changes
9. duplicate abstractions
10. evidence integrity

An implementation agent should not be allowed to weaken the mechanisms judging its own work without heightened review.

---

# 24. GitHub Actions

GitHub Actions should primarily provide **independent deterministic validation**, not duplicate the reasoning already available through local Claude and Codex subscriptions.

Good uses include:

- tests
- linting
- static analysis
- type checking
- schema validation
- documentation checks
- PR metadata checks
- Issue/PR linkage validation
- release checks
- policy validation
- lightweight synchronization
- security scanning

Avoid using Actions merely to:

- repeat expensive local LLM reasoning
- invoke a cloud agent for every Issue event
- reproduce work already performed interactively
- create additional AI-consumption paths without clear value

If expensive deterministic workloads become significant, self-hosted runners are an architectural option because local or server-side compute can still report GitHub Checks without making hosted Actions the primary compute platform.

---

# 25. Rulesets and Deterministic Policy

Rulesets should encode invariants that should remain true regardless of which agent is operating.

Examples:

- no direct pushes to the default branch
- required checks before merge
- required review for defined risk classes
- controlled workflow modifications
- controlled release branches
- force-push restrictions

The pattern is:

```text
Agent:
    "I believe this change is valid."

Policy:
    "Prove the required deterministic conditions."

Human:
    "Accept the remaining judgment."
```

---

# 26. Permission Model for Local Agents

A supervised local implementation agent generally needs broad operational access but should remain constrained by repository policy.

Reasonable capabilities include:

- repository read
- Issue read
- Issue comments
- Issue Field updates where authorized
- branch creation
- push to nonprotected branches
- PR creation and updates
- PR comments
- reading CI results

Capabilities that should remain protected include:

- direct push to protected default branch
- modifying repository rules
- changing secrets
- altering Actions permission policy
- changing organization security configuration
- destructive repository administration
- silently bypassing required checks

The important safety boundary is therefore not necessarily that Claude or Codex possesses no GitHub write capability.

It is:

> The agent cannot unilaterally bypass the repository's independent enforcement boundaries.

---

# 27. Unattended Local Agents

Interactive agents and unattended automation should eventually have different privilege envelopes.

An interactive Claude Code or Codex session operates under active human supervision.

An unattended coordinator or scheduled local agent should have narrower authority.

For unattended automation, prefer:

- GitHub App identity
- narrowly scoped credentials
- explicit repository access
- enumerated writable operations
- deterministic eligibility checks
- bounded concurrency

Do not give an unattended process the full authority of the personal GitHub account merely because doing so is convenient.

---

# 28. GitHub-Hosted Agent Policy

GitHub-hosted AI should be considered an optional execution environment rather than a repository-management dependency.

Appropriate uses include narrow tasks where GitHub event locality is valuable:

```text
Issue opened
    → classify using a small model
    → apply approved field/label recommendation

PR opened
    → produce short summary

scheduled
    → summarize stale work
```

Inappropriate default uses include:

- repository-wide architectural analysis
- complex implementation
- long debugging loops
- multi-round code review
- large migrations
- work already economically covered by local Claude Code or Codex subscriptions

If GitHub Agentic Workflows are ever adopted for these lightweight purposes, GitHub's own architecture provides a useful security pattern even if the implementation mechanism differs: agents run read-only by default and request narrowly declared writes through separate validated outputs. GitHub explicitly describes this separation as reducing blast radius and defending against prompt injection.

That pattern is worth copying into local automation:

```text
Reasoning process
      ↓
structured proposed operation
      ↓
policy validator
      ↓
narrow GitHub mutation
```

---

# 29. Fields Not to Create

Do not create metadata merely because GitHub supports it.

| Candidate             | Reason to omit                                      |
| --------------------- | --------------------------------------------------- |
| **Start date**        | Actual transition to In progress is more meaningful |
| **Completion date**   | Derivable from Issue closure                        |
| **Owner**             | Duplicates Assignee                                 |
| **Repository**        | Intrinsic                                           |
| **PR URL**            | Native relationship                                 |
| **Parent ID**         | Native hierarchy                                    |
| **Blocked by**        | Native dependency relationship                      |
| **Release**           | Normally Milestone                                  |
| **Agent/model**       | Execution detail, not work semantics                |
| **Progress %**        | False precision for knowledge work                  |
| **Hours estimate**    | Particularly weak under agent execution             |
| **Status note**       | Narrative belongs in PR/comment                     |
| **Acceptance status** | Workflow and close reason already express it        |
| **Agent ready**       | Derived from Workflow + Execution mode + blockers   |
| **Review status**     | PR-native state                                     |
| **Branch**            | Native Git/PR state                                 |

GitHub automatically creates `Start date` as one of its default Issue Fields, but there is no requirement to retain it.

---

# 30. Derived State Instead of Stored State

Whenever possible, compute facts rather than storing them twice.

Examples:

```text
agent-ready =
    Workflow == Ready
    AND Execution mode == Unattended agent
    AND blockers == 0
    AND validation == pass
```

Do not create another boolean field:

```text
Agent Ready = Yes
```

Similarly:

```text
has-implementation =
    linked PR exists
```

Do not create:

```text
Implementation Started = Yes
```

And:

```text
completed-at =
    Issue closed timestamp
```

Do not create:

```text
Completion Date
```

The general rule is:

> **Store decisions and irreducible facts; derive consequences.**

---

# 31. Optional Future Fields

Additional fields should be added only after repeated experience demonstrates a concrete query or policy that cannot be expressed cleanly with the baseline schema.

## Impact

Potential future field:

```text
I1 — Critical
I2 — Major
I3 — Moderate
I4 — Minor
```

Impact could become useful for portfolio ranking across multiple products.

Do not add it initially unless a concrete distinction between Impact and Priority is needed.

## Confidence

Could theoretically represent uncertainty in a Research or triage result.

Prefer evidence in the Issue body unless actual automation requires a typed confidence value.

## Estimate

Avoid initially.

Agent-assisted implementation makes traditional effort estimates particularly noisy.

---

# 32. Recommended Initial Project Views

If a GitHub Project is introduced, keep views operational and derive them from Issue state.

## Work queue

```text
Workflow = Ready
sort Priority
then Change risk
```

## Active work

```text
Workflow IN [In progress, Blocked, In review]
```

## Agent queue

```text
Workflow = Ready
AND Execution mode = Unattended agent
```

## Human-attention queue

```text
Workflow IN [Needs definition, Blocked]
OR Execution mode = Human only
```

## High-risk

```text
Change risk IN [R3, R4]
AND Workflow != Done
AND Workflow != Dropped
```

## Bugs

```text
Type = Bug
sort Severity
then Priority
```

## Upcoming commitments

```text
Target date exists
AND Workflow NOT IN [Done, Dropped]
sort Target date
```

These are views over canonical Issue metadata.

They should not introduce their own competing workflow fields.

---

# 33. Recommended Repository Administration Roles

Even when all roles ultimately execute under one developer's supervision, conceptual role separation improves agent prompts and permission boundaries.

## Triage

Responsible for:

- Issue Type
- Priority recommendation
- Severity
- Size estimate
- Change risk estimate
- execution-policy recommendation
- duplicate detection
- missing-information identification

## Planner

Responsible for:

- refining scope
- acceptance criteria
- decomposition
- dependencies
- identifying relevant ADRs/specifications
- producing implementation plans where required

## Coordinator

Responsible for:

- finding eligible work
- claims
- concurrency
- dispatch
- stale-claim recovery
- lifecycle synchronization

## Implementer

Responsible for:

- repository modification
- tests
- commits
- PR creation
- implementation evidence

## Reviewer

Responsible for:

- independent analysis
- acceptance coverage
- correctness
- regression risk
- policy adherence

## Human operator

Responsible for:

- ambiguous scope decisions
- acceptance of material work
- privilege and policy changes
- high-risk authorization
- protected merge decisions

These need not initially be separate programs.

They are boundaries around responsibilities.

---

# 34. Recommended Invariants

The following invariants are suitable candidates for later deterministic enforcement.

```text
INV-001
Every directly executable nontrivial Issue has acceptance criteria.

INV-002
Workflow = Ready implies no known blocking dependency.

INV-003
Workflow = Ready implies required planning is complete.

INV-004
Size = XL cannot be directly dispatched.

INV-005
Unattended execution requires Execution mode = Unattended agent.

INV-006
A local agent may not self-promote Execution mode.

INV-007
One directly executable Issue has at most one live claim.

INV-008
A PR implementing planned work links its governing Issue.

INV-009
Workflow = Done requires the Issue's acceptance criteria to be satisfied.

INV-010
Workflow = Done corresponds to GitHub closed/completed.

INV-011
Workflow = Dropped corresponds to GitHub closed/not-planned.

INV-012
R3/R4 changes receive heightened independent review.

INV-013
R4 work requires explicit human authorization before implementation.

INV-014
Protected-branch policy cannot be bypassed by the implementation agent.

INV-015
Durable follow-up work discovered during implementation becomes an Issue.

INV-016
Derived state is not separately persisted unless a demonstrated operational need exists.
```

---

# 35. Recommended Baseline Schema

```yaml
issue_types:
  - Bug
  - Feature
  - Task
  - Initiative
  - Research

issue_fields:
  Workflow:
    type: single_select
    values:
      - Inbox
      - Needs definition
      - Ready
      - In progress
      - Blocked
      - In review
      - Done
      - Dropped

  Priority:
    type: single_select
    values:
      - P0 — Immediate
      - P1 — Next
      - P2 — Planned
      - P3 — Opportunistic
      - P4 — Someday

  Size:
    type: single_select
    values:
      - XS
      - S
      - M
      - L
      - XL

  Change risk:
    type: single_select
    values:
      - R1 — Low
      - R2 — Moderate
      - R3 — High
      - R4 — Critical

  Execution mode:
    type: single_select
    values:
      - Unattended agent
      - Interactive agent
      - Human only

  Target date:
    type: date

  Severity:
    type: single_select
    values:
      - S0 — Critical
      - S1 — High
      - S2 — Moderate
      - S3 — Low
```

---

# 36. Adoption Sequence

## Phase 1 — canonical work model

Establish:

- Issue Types
- seven Issue Fields
- definitions
- body structure
- label namespaces
- Issue/PR relationship

Do not automate yet.

The objective is to verify that the data model represents real work cleanly.

## Phase 2 — views and manual operation

Use the model manually with Claude Code and Codex.

Observe:

- ambiguous values
- fields that are never used
- frequently missing information
- transitions that cause friction
- queries that are difficult to express

Prefer deleting unnecessary metadata over adding more.

## Phase 3 — deterministic validation

Introduce checks for high-value invariants such as:

- Ready requirements
- XL decomposition
- PR/Issue linkage
- terminal state synchronization
- required review based on Change Risk

## Phase 4 — local coordinator

Add controlled dispatch:

```text
GitHub query
    ↓
eligibility validator
    ↓
claim
    ↓
Claude Code / Codex
    ↓
PR
```

The coordinator, rather than individual agents, should own concurrency.

## Phase 5 — unattended local execution

Only after the workflow semantics are stable should selected Issues become eligible for unattended agents.

Use explicit `Execution mode = Unattended agent`.

## Phase 6 — optional GitHub-hosted micro-agents

If beneficial, add narrow GitHub-hosted automation for jobs where:

- context is small
- model consumption is low
- latency is unimportant
- event locality matters
- outputs can be strictly bounded

The rest of the system should remain unchanged if these jobs are disabled.

---

# 37. Final Recommended Operating Model

The resulting control flow is:

```text
                    ┌───────────────────┐
                    │   Human / Agent   │
                    │   captures work   │
                    └─────────┬─────────┘
                              │
                              ▼
                       GitHub Issue
                              │
                         Workflow:
                           Inbox
                              │
                              ▼
                           Triage
                              │
             ┌────────────────┼─────────────────┐
             │                │                 │
             ▼                ▼                 ▼
          Dropped     Needs definition        Ready
                              │                 │
                              └───────┬─────────┘
                                      │
                              eligibility checks
                                      │
                                      ▼
                               Local coordinator
                                      │
                                 atomic claim
                                      │
                                      ▼
                         Claude Code / Codex CLI
                                      │
                                 local branch
                                      │
                                      ▼
                                  Draft PR
                                      │
                        deterministic GitHub CI
                                      │
                        independent agent review
                                      │
                                      ▼
                              Human acceptance
                                      │
                                      ▼
                                   Merge
                                      │
                                      ▼
                             Issue → Done
                                      │
                                      ▼
                         Project view reflects
                            canonical state
```

The architecture deliberately makes GitHub-hosted AI absent from the critical path.

---

# 38. Conclusions

The highest-value use of GitHub in a local-agent development environment is not as an AI execution platform.

It is as a **durable, queryable, policy-enforced coordination substrate**.

The local agents are replaceable workers.

GitHub retains:

- intent
- authorization
- lifecycle
- dependencies
- history
- evidence
- policy
- final disposition

This separation provides three important properties.

### Continuity

A Claude Code session can end and Codex can resume from durable repository state.

### Agent independence

Changing model providers does not require redesigning the project-management system.

### Determinism

Agents perform semantic work, while GitHub and repository tooling enforce the conditions that should not depend on model judgment.

The recommended Issue metadata set is intentionally compact:

```text
Type
Workflow
Priority
Size
Change Risk
Execution Mode
Target Date when meaningful
Severity for Bugs
```

Everything else should first be evaluated as:

1. native GitHub metadata,
2. a native GitHub relationship,
3. narrative Issue content,
4. a label,
5. or derived state

before another custom field is created.

That constraint is important. The objective is not maximum metadata collection.

The objective is **maximum useful information with minimum duplicated state**.

---

# Recommendations

1. Adopt the five Issue Types: **Bug, Feature, Task, Initiative, Research**.
2. Standardize the seven Issue Fields defined in this document.
3. Make `Workflow = Ready` the durable work-eligibility boundary.
4. Make `Execution mode = Unattended agent` an explicit authorization requirement for autonomous local execution.
5. Keep model identity out of Issue semantics.
6. Keep Projects derivative of Issue Fields.
7. Use GitHub-native hierarchy, dependency, milestone, assignment, and PR relationships rather than duplicating them.
8. Use PRs as implementation/evidence records, not as substitutes for Issues.
9. Move persistent architectural decisions into version-controlled ADRs/specifications.
10. Gradually encode lifecycle and review invariants in deterministic tooling.
11. Centralize unattended dispatch and claims rather than allowing workers to independently self-claim.
12. Keep protected merges, repository policy, secrets, and other consequential administration outside an implementation agent's unilateral authority.
13. Use GitHub Actions mainly for independent deterministic verification.
14. Treat GitHub-hosted AI as an optional micro-automation layer rather than part of the core system.
15. Resist adding metadata until repeated workflow experience demonstrates that the baseline schema cannot answer a real operational question.

# Uncertainties and Items to Validate Through Use

The primary remaining uncertainties are operational rather than architectural:

- Whether `Workflow` requires all eight proposed states in practice.
- Whether `Execution mode` should default to Interactive or initially remain unset until triage.
- Whether Size is useful enough for every Research Issue.
- Whether Target Date deserves pinning on Bugs and Research.
- Whether `source/*` labels provide enough long-term value to justify maintaining them.
- Whether a dedicated Project becomes useful given actual concurrent Issue volume.
- Which mechanism should eventually represent an atomic local-agent claim.
- At what Change Risk boundary independent Codex/Claude cross-review should become mandatory.
- Whether an `Impact` field eventually becomes necessary for portfolio-level prioritization.

These should be answered through operating experience rather than by expanding the initial schema speculatively.

# Sources

GitHub announced general availability of organization-level Issue Fields on July 2, 2026, including availability for organizations on GitHub Free, organization-wide consistency, repository Issue-list integration, Projects integration, API access, and GitHub MCP support.

GitHub's Issue Field documentation establishes that Issue Fields are organization-level metadata and distinguishes them from Project-local custom fields. GitHub specifically recommends Issue Fields as the source of truth when the same metadata is needed across Projects.

GitHub's current Copilot plans distinguish individual Pro/Pro+/Max subscriptions from organization Business/Enterprise licensing and use GitHub AI Credits as the consumption mechanism for Copilot model use. This supports keeping GitHub-hosted AI consumption separate from the core repository-control architecture.

GitHub Agentic Workflows currently implements a security architecture in which AI execution is read-only by default and write operations are handled through declared, validated safe outputs. Although this report does not recommend GitHub Agentic Workflows as the primary execution environment, its privilege-separation pattern is applicable to local-agent administration.
