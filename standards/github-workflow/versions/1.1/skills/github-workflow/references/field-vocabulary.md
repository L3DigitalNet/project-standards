# Issue Field Vocabulary

The authoritative value set for the seven organization-level Issue Fields, the field-pinning matrix, and the metadata deliberately not modeled. Values here are the vocabulary; `org-schema.yaml` is the machine-readable form of the same schema and is what `gh-workflow set` validates against. Selecting a value is agent judgment; applying it is the tool's job.

GitHub Issue Fields are appropriate for data that is structured, organization-wide, relatively low-cardinality, useful for filtering or automation, and semantically applicable across repositories. GitHub allows up to 25 organization Issue Fields; that capacity is not a target. The baseline uses seven.

## Workflow

**Type:** Single select

**Applies to:** All Issue Types

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

`Workflow` is the canonical operational lifecycle field. It answers a different question from GitHub's native open/closed state: native state answers whether the Issue is active, `Workflow` answers where that active work sits in its lifecycle.

**Required synchronization.** Terminal states stay consistent:

```text
Workflow = Done
    → Issue closed as completed

Workflow = Dropped
    → Issue closed as not planned

Issue reopened
    → Workflow must return to a valid nonterminal state
```

Do not maintain the two independently from memory. Route terminal transitions through `gh-workflow close` and `gh-workflow reopen`, which apply the pairing as an ordered, rerunnable sequence.

**Ready semantics.** `Ready` is an eligibility boundary that local-agent automation can act on, so it means all of:

- sufficient acceptance criteria exist
- no blocking decision remains
- required dependencies are satisfied
- required planning is complete
- work has been intentionally admitted to the executable queue

Never infer readiness merely because an Issue is open.

## Priority

**Type:** Single select

**Applies to:** All Issue Types

| Value                | Meaning                                   |
| -------------------- | ----------------------------------------- |
| **P0 Immediate**     | Interrupt current work                    |
| **P1 Next**          | Committed near-term work                  |
| **P2 Planned**       | Normal accepted backlog                   |
| **P3 Opportunistic** | Worth doing when convenient               |
| **P4 Someday**       | Valid work with no foreseeable commitment |

Leave `Priority` empty until triage if no deliberate prioritization has occurred.

Priority is a scheduling decision. It is not equivalent to:

```text
Priority ≠ Severity
Priority ≠ Change risk
Priority ≠ Size
```

A serious defect can be low priority if exposure is negligible. A relatively minor defect can be P0 if it blocks a release.

## Size

**Type:** Single select

**Applies to:** Bug, Feature, Task, Research

| Value | Operational meaning |
| --- | --- |
| **XS** | Localized, obvious change with minimal review surface |
| **S** | One coherent behavior or component |
| **M** | Multiple interacting files/components or meaningful uncertainty |
| **L** | Cross-component work, migration, significant uncertainty, or substantial review surface |
| **XL** | Too large for direct execution; decomposition required |

**Size is not time.** Do not define Size as hours, story points tied to time, model-token estimates, or expected agent session duration; agent-assisted development makes elapsed-time estimates particularly unstable. Size represents breadth, coupling, conceptual complexity, uncertainty, and review burden.

**XL invariant:**

```text
Size = XL
    → direct implementation prohibited
    → decompose into sub-issues
```

An XL Issue may remain as an Initiative or parent tracking object.

## Change risk

**Type:** Single select

**Applies to:** Bug, Feature, Task

| Value | Meaning |
| --- | --- |
| **R1 Low** | Localized, easily reversible, low coupling |
| **R2 Moderate** | Meaningful behavior or compatibility implications |
| **R3 High** | Significant trust boundary, persistence, concurrency, API, CI, or cross-system effects |
| **R4 Critical** | Destructive, difficult-to-reverse, security-sensitive, release-control, infrastructure, or broad systemic consequences |

Change risk measures how dangerous it is to implement this change incorrectly. It does not measure how bad the existing problem is — that is Severity, and only for Bugs.

Baseline treatment by risk:

| Risk | Baseline treatment |
| --- | --- |
| **R1** | Normal tests and review |
| **R2** | Acceptance-criteria trace plus focused regression coverage |
| **R3** | Independent review, negative testing, explicit rollback consideration |
| **R4** | Human-approved plan before implementation, independent verification, explicit recovery/rollback procedure |

## Execution mode

**Type:** Single select

**Applies to:** Bug, Feature, Task, Research

| Value | Meaning |
| --- | --- |
| **Unattended agent** | Authorized for autonomous dispatch to a local agent |
| **Interactive agent** | Agent implementation is allowed within a human-directed session |
| **Human only** | Agents may inspect or advise but not autonomously implement |

`Execution mode` expresses **authority**, not capability. An Issue being technically executable does not mean an unattended process is authorized to execute it.

**Do not encode model identity.** Values such as Claude, Codex, GPT, Local LLM, Claude preferred, or Codex preferred are prohibited: model routing changes frequently and is not a durable property of the work. Worker and model information belongs in execution logs, session evidence, PR metadata, and agent-evaluation records.

**Conservative default.** Unattended execution requires affirmative authorization:

```text
new Issue
    → Interactive agent by default

explicit promotion
    → Unattended agent
```

High-risk work does not become unattended merely because an agent believes it can perform the task, and an agent never promotes its own `Execution mode`.

## Target date

**Type:** Date

**Applies to:** Initiative, Feature, Task; optionally Bug and Research

Use `Target date` only when a date has genuine semantic meaning — a release deadline, contractual commitment, upstream dependency, deprecation date, event date, time-sensitive vulnerability remediation, or work that becomes materially less useful after a date.

Do not populate it merely because every Issue looks nicer with one. Empty is a valid and expected state.

## Severity

**Type:** Single select

**Applies to:** Bug only

| Value | Meaning |
| --- | --- |
| **S0 Critical** | Security compromise, corruption/data loss, unsafe operation, or system unusable |
| **S1 High** | Core capability unusable with no acceptable workaround |
| **S2 Moderate** | Material impairment with workaround or constrained exposure |
| **S3 Low** | Minor defect, cosmetic behavior, narrow edge case, or negligible operational consequence |

Severity is factual — what consequence does the defect produce. Priority is managerial — when should it be fixed relative to other work. Keeping them separate is what makes triage work.

## Field pinning

| Field          |   Bug    | Feature | Task | Initiative | Research |
| -------------- | :------: | :-----: | :--: | :--------: | :------: |
| Workflow       |    ✓     |    ✓    |  ✓   |     ✓      |    ✓     |
| Priority       |    ✓     |    ✓    |  ✓   |     ✓      |    ✓     |
| Size           |    ✓     |    ✓    |  ✓   |            |    ✓     |
| Change risk    |    ✓     |    ✓    |  ✓   |            |          |
| Execution mode |    ✓     |    ✓    |  ✓   |            |    ✓     |
| Target date    | Optional |    ✓    |  ✓   |     ✓      | Optional |
| Severity       |    ✓     |         |      |            |          |

Initiatives deliberately omit execution-oriented fields because an Initiative itself should normally not be directly implemented.

## Fields not to create

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

GitHub creates `Start date` as one of its default Issue Fields; there is no requirement to retain it.

Organization schema changes — adding, renaming, or retiring a field or a value — are human work. Agents audit and report drift with `gh-workflow audit`; they never mutate the organization schema.
