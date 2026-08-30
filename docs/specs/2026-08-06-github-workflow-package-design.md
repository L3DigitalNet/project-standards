---
schema_version: '1.1'
id: 'decision-q3w8fn-github-workflow-package-design'
title: 'github-workflow standard package design'
description: 'Approved design for github-workflow 1.7: uniform low-friction PR admission, governing-work relationships, lifecycle coherence, and efficient paired operations.'
doc_type: 'decision'
status: 'active'
created: '2026-08-06'
updated: '2026-08-30'
tags:
  - 'standard'
aliases: []
related: []
---

# github-workflow standard package design

## Status and provenance

- Status: `approved`
- Operation: `revise`
- Decision owner: repository owner
- Created and initially approved: `2026-08-06`
- Revision: 1.8 — 2026-08-30 owner-approved `github-workflow` 1.7 design. Adds T0 editorial-only direct admission, canonical Final/Supporting/Standalone PR relationships, Issue/PR lifecycle coherence, and paired Ready/Merge/Final-disposition operations. Incorporates the owner-directed simplification pass: one operator instruction is sufficient authority, consumers receive uniform sane defaults, and recurring context and tool-call cost are design criteria. Supersedes D9's mandatory immediate PR receipt and D12's repository-defined semantic threshold while preserving repository ownership of branch topology and live enforcement. Prior revision: 1.7 — 2026-08-26 package-version-1.5 efficiency amendment (D13). Earlier history is retained in [Prior package decisions](#prior-package-decisions).
- Current implementation baseline: `github-workflow` 1.7, implemented and cut as an immutable payload in v5.26.0 and recorded in [SPEC-GHW1](2026-08-06-github-workflow-package-spec.md) revision 1.36. The preceding 1.6 baseline that this design revision was written against was reconciled in SPEC-GHW1 revision 1.34 and independently confirmed against the shipped implementation by a native verifier and headless Opus before promotion; 1.6 remains immutable and retained.
- Design input: [GitHub Repository Administration Standard (preliminary)](archive/2026-08-06-github-repo-administration-preliminary-design.md)
- Revision input: owner-supplied `PR Versus Direct Commits.md` memo plus the approved design-discovery record.

This brief owns the package's target operating contract. Version 1.6 remains immutable. The 1.7 revision deliberately changes the package's PR-admission and Issue/PR relationship model; where it conflicts with the preliminary design or earlier package decisions, this revision is authoritative for `github-workflow` 1.7.

## Problem and intended outcome

`github-workflow` 1.6 leaves PR existence to repository-local prose and infers a governing Issue only from GitHub closing keywords. That permits inconsistent admission, makes Supporting work indistinguishable from Final work, and cannot mechanically determine which object owns acceptance, risk, lifecycle, or terminal reconciliation.

The 1.7 outcome is one portable workflow that gives agents a useful PR admission boundary without turning a solo operator's instruction into approval ceremony. Every consumer receives the same semantics. Repository-owned branch topology and GitHub enforcement may narrow what is possible, but repositories do not configure parallel workflow dialects. Routine agent work should proceed from the operator's instruction to completion without a second permission artifact, repeated phase commands, empty boilerplate, or unnecessary receipts.

## Current context

- `github-workflow` 1.6 shipped in Project Standards v5.25.0 and is the Catalog 5 default before this revision.
- Version 1.7 will ship in a Project Standards release. Every locally cloned Project Standards consumer will then be updated, and consumers already using `github-workflow` will migrate to 1.7.
- Branch names, development branches, integration targets, promotion topology, merge method, and required-check identities belong to each repository or to live GitHub configuration.
- The package already owns Issue vocabulary, work-state mutations, summaries, receipts, Ready checks, and terminal Issue synchronization through one Go tool.
- The owner rejected a 2.0 cut for this coordinated rollout and authorized the same-major 1.7 migration.

## Scope

### In scope

- Topology-neutral direct and PR admission semantics.
- A narrow autonomous `T0 — Editorial-only` direct-admission class.
- Canonical Final, Supporting, and Standalone PR relationships.
- PR contract ownership, authoritative Change risk, review treatment, and Issue/PR lifecycle coherence.
- Structural, Ready, Merge, and Post-merge/disposition validation in one shared engine.
- Action-oriented summaries and explanatory receipts over the shared findings.
- Efficient commands that pair validation, mutation, reconciliation, and one resulting receipt.
- Coordinated 1.7 migration and repair of active work when touched.

### Non-goals

- Prescribing branch names, branch topology, integration-target names, merge method, or required-check names.
- Requiring an Issue for every PR or every task.
- Requiring repository-specific semantic permission switches.
- Requiring the operator to repeat an instruction in an Issue, comment, approval record, or break-glass token.
- Persisting another lifecycle or validation-phase state.
- Building an event-driven enforcement service, watcher registry, or lease protocol.
- Rewriting terminal PR history or existing Git history automatically.

## Design principles

1. The operator's task instruction authorizes autonomous completion through the normal workflow.
2. An explicit operator instruction selecting a specific workflow exception is sufficient authority for that action; it creates no standing or broader permission.
3. Validation is autonomous plumbing, not another operator approval gate.
4. Preserve controls when they protect high-consequence shared state or materially reduce error.
5. Prefer package-wide behavior over repository options; repository instructions and live enforcement may narrow behavior.
6. Prefer one invariant-pairing command over repeated read/check/mutate recipes.
7. Keep routine context small and move rare audit/recovery procedure into on-demand references.
8. Evaluate design by correctness, operator friction, configuration burden, duplicated authority, failure consequence, maintenance cost, recurring tokens, and tool-call round trips.

## Selected design

### Admission model

Admission occurs when new content first enters a repository-declared integration target. Topic and PR branches are construction state; a later content-preserving promotion does not repeat admission classification.

There are two ordinary autonomous outcomes:

1. A complete change satisfying T0 may be admitted directly when repository instructions and GitHub enforcement permit.
2. Every other new-content change uses PR admission.

`T0 — Editorial-only` is a conjunctive semantic predicate. Every changed hunk must be an unambiguous spelling, grammar, punctuation, or prose-reflow correction in ordinary human-facing explanatory text. The complete change must preserve all propositions, obligations, instructions, identifiers, references, and machine interpretation; touch no protected surface; be outside active governed work; contain no other change; affect at most three files and thirty added-plus-deleted lines; and pass applicable validation. Uncertainty requires a PR.

A direct T0 commit carries exactly one trailer:

```text
Workflow-Admission: T0
```

The trailer never appears on topic-branch commits or PR-mediated commits. It records the admission assertion for auditability; it does not prove that classification was correct.

A specific operator instruction may select another admission path without a secondary approval artifact or special break-glass grammar. The agent may not infer a wider exception. Repository instructions and live GitHub enforcement may prevent an action, and the agent does not weaken enforcement unless that distinct action is itself explicitly in scope.

### Governing work

Every PR contains exactly one canonical declaration under `## Governing work`:

```text
Final: #123
Supporting: #123
Standalone
```

The alternatives are mutually exclusive; the body contains exactly one of them.

- Final and Supporting resolve exactly one same-repository Issue. Cross-repository and additional Issue mentions are informational only.
- Final claims to satisfy all remaining acceptance criteria and authorizes `Done` only after successful admission and terminal reconciliation.
- Supporting contributes without claiming completion or implying an Issue lifecycle transition.
- Standalone makes the PR its own authoritative work contract, risk record, implementation evidence, and native lifecycle record.
- One Issue may have any number of Supporting PRs and at most one open Final PR.
- An open PR may change relationship only while draft and with auto-merge disabled. The relationship-specific contract and ordinary Ready gate then apply again.
- A merged or closed PR's relationship is immutable historical evidence. A historical error receives additive correction or explicit human handling rather than silent mutation.

### PR body and authoritative risk

At Ready, every PR has four required sections:

```text
## Summary
## Governing work
## Acceptance coverage
## Verification
```

Risk/compatibility notes and known limitations/follow-up appear only when material. Empty `None` sections are not required.

For Final and Supporting PRs, the Issue owns the intended outcome, acceptance criteria, Change risk, and `Workflow`. The PR's Acceptance coverage maps implementation and evidence to that contract without copying it.

For Standalone PRs, the PR owns its intended outcome and explicit criteria and declares authoritative `Change risk: R1 Low|R2 Moderate|R3 High|R4 Critical`. R4 is permitted without manufacturing an Issue or seeking a second operator approval. Before merge, R4 still requires a documented plan, recovery or rollback approach, negative testing, and independent verification. These are execution controls, not permission ceremony.

### GitHub-native closing

Canonical Final/Supporting/Standalone declarations alone establish package semantics. Agents omit GitHub closing keywords by default.

If deliberately present, the only accepted native closing form is exactly `Closes #N`. It is permitted only in the PR body of a Final PR and N must match the canonical governing Issue. Supporting and Standalone PRs, informational references, and constituent commits introduce no closing relationship. Legacy synonyms are removed or normalized when an active PR is repaired. Package correctness never depends on GitHub auto-close; Final reconciliation remains authoritative.

### Lifecycle semantics

- The governing Issue is the sole authoritative `Workflow` owner. Standalone uses native PR state and carries no Issue lifecycle.
- An open governed PR requires `In progress`, `In review`, or `Blocked`.
- A ready Final requires `In review` or `Blocked`. Final merge is prohibited while the Issue is `Blocked`.
- A Supporting PR may merge while the Issue is `Blocked` when its own evidence is sufficient and admission neither falsely resolves nor conceals the blocker.
- Supporting merge or closure is lifecycle-neutral and never authorizes `Done`.
- A merged Final authorizes convergence to `Workflow = Done` plus native Issue closed/completed.
- A closed-unmerged Final requires explicit disposition. PR closure alone never implies `In progress`, `In review`, `Blocked`, or `Dropped`.

PR events constrain which Issue states are coherent but do not independently become another `Workflow` writer. Paired package commands perform deterministic lifecycle mutations where the desired result is known.

### Validation and findings

One shared engine derives four predicate groups without persisting phase:

1. **Structural** — canonical relationship, same-repository Issue resolution, one-open-Final cardinality, closing-keyword discipline, and evidence integrity.
2. **Ready** — Structural plus relationship-specific contract completeness, authoritative risk, acceptance coverage, Verification, and lifecycle coherence.
3. **Merge** — Ready plus risk-proportionate review/verification, live required-check evidence, no blocking Final state, and no relevant state drift.
4. **Post-merge/disposition** — structural facts still meaningful after the event plus terminal synchronization or explicit disposition. Temporal pre-merge predicates are not rerun against post-event state.

Each finding has a stable code, phase, action category, effect, and message. Domain findings are distinct from invalid invocation and operational/API failure.

`gh-workflow check --pr N` infers the applicable next gate from observed state: draft → Ready, ready/open → Merge, terminal → Post-merge/disposition. Explicit phase selection remains optional for diagnostics and automation; ordinary workflow does not require it.

`receipt` describes one observed item and succeeds when reading and rendering succeed. `summary` aggregates attention and likewise does not become a gate. `check` alone returns an admission/reconciliation verdict.

Needs attention has six action-oriented categories, in order:

1. Blocked
2. Needs definition
3. PR admission blocked
4. Synchronization required
5. Disposition required
6. Target date passed

Draft PRs surface Structural defects but not ordinary incomplete Ready content. Ready PRs surface applicable Structural, Ready, and Merge findings. Terminal PRs surface Post-merge/disposition findings. Human output compresses one line per work item per category; JSON retains every stable finding.

### Efficient mutation commands

Agent-created PRs begin draft. Creation is not followed by a mandatory receipt/check sequence.

`gh-workflow ready --pr N` validates Structural and Ready predicates, moves a Final Issue from `In progress` to `In review` when deterministic, marks the PR ready, and returns one resulting receipt. Supporting and Standalone do not mutate Issue lifecycle merely by becoming ready. The operation is ordered, retryable, and reports coherent partial state.

`gh-workflow merge --pr N` revalidates Merge predicates, uses the repository-selected merge method, observes the terminal outcome, synchronizes a successfully merged Final Issue to `Done`, validates Post-merge convergence, and returns one result. Exact merge-method flags and GitHub mechanics belong to specification design; the package does not create a competing merge-method policy.

Auto-merge may defer the event but never orphan responsibility. The active merge operation retains observation until a known terminal outcome or safely disables/transfers responsibility before stopping. Routine guidance states that obligation in one line; it does not define watcher identities, leases, or a static ownership registry.

`gh-workflow close --pr N --as in-progress|in-review|blocked|dropped --reason S` pairs the judgment record, Final closure, governing-Issue mutation, and verification for an unmerged Final. It writes one immutable canonical disposition record, resumes idempotently after partial failure, and refuses conflicting history.

Ready and Merge validation are point-in-time. Combined operations keep validation adjacent to mutation; a relevant intervening change requires reevaluation. Raw GitHub or Git commands remain available when an explicit operator instruction selects a specific exception the package command does not represent.

### T0 audit

T0 classification remains semantic agent judgment; no CLI success certifies it. On explicit operator request, a bounded retrospective review locates exact T0 trailers and evaluates each complete diff against the immutable contract applicable at admission. Results are `Conforming`, `Suspected misclassification`, or `Unable to establish`. The review never rewrites history automatically. Audit guidance stays in an on-demand T0 reference, not routine context; a future helper may collect mechanical facts but never return semantic eligibility.

### Configuration and authority

The consumer configuration remains exactly:

| Option | Type | Purpose |
| --- | --- | --- |
| `organization` | string, required | GitHub organization login; block/policy rendering, audit target, and bare-repository completion |
| `harnesses` | array of `claude-code` \| `codex`, required | Harness-specific contributions and the Codex companion |

Version 1.7 adds no `admission_mode`, `native_closing`, branch-name, required-check, merge-method, or watcher-identity options. The package defines one semantic maximum. Repository instructions and live GitHub enforcement may narrow it and can never widen a package prohibition.

### Migration and rollout

- Version 1.6 remains immutable; all behavior changes ship as 1.7 payload and tool bytes.
- Existing open PRs receive no legacy validator mode. They are evaluated from observed state and repaired when touched or surfaced by normal summary/check.
- Installation does not create a per-repository PR migration ledger and does not rewrite terminal PR bodies or Git history.
- The rollout verifies that every selected local consumer resolves 1.7. Package reconciliation and remote active-work correction are separate checkpoints.
- Repositories already using `github-workflow` migrate to 1.7 during the post-release local-consumer update.

## Consequential decisions

### Prior package decisions

| Decision | Current disposition |
| --- | --- |
| D0 phases 1–2, org-owned repositories, audit-only org schema | Retained; 1.7 adds repository-scoped PR mechanics, not organization-schema mutation or event services. |
| D1 one mandatory skill with progressive references | Retained; rare T0 audit/recovery detail remains on demand. |
| D2 all-managed delivery | Retained. |
| D3 compact managed block | Retained in principle; 1.7 content prioritizes routing and load-bearing invariants within the context budget. |
| D4 config = organization + harnesses | Retained; new semantic switches are rejected. |
| D5 companions/capabilities | Retained; exact new capability names are specification detail. |
| D6 offline deterministic providers | Retained. |
| D7 one reproducibly built Go tool | Retained and extended with PR validation and paired mutations. |
| D8 attention-first summaries | Retained with six action-oriented categories. |
| D9 mandatory creation receipts | Superseded for PRs; combined operations return one useful resulting receipt without immediate ceremony. |
| D10 ledger | Ledger remains superseded by D13; single-tool consolidation remains. |
| D11 deterministic plumbing in the tool | Retained and extended to Ready, Merge, and Final disposition. |
| D12 PR existence is repository-local | Superseded semantically: T0 is the sole autonomous direct-admission class; topology and enforcement remain repository-owned. |
| D13 budgeted guidance, no ledger, agent self-definition | Retained. |

### D14: T0 or PR admission

- Status: `approved` (owner, 2026-08-30)
- Decision: the complete T0 predicate and exact audit trailer define the sole autonomous direct-admission exception; every other new-content change uses PR admission unless the owner explicitly directs a specific exception.
- Rationale: semantic impact, not size or provenance, is the only portable boundary. A narrow allowlist avoids editorial PR ceremony without turning “small” or “obvious” into loopholes.
- Reopen when: observed false classifications show the protected-surface or scope boundaries are unusable.

### D15: One governing-work relationship

- Status: `approved` (owner, 2026-08-30)
- Decision: every PR is exactly Final, Supporting, or Standalone; Final/Supporting bind one same-repository Issue; an Issue has at most one open Final; canonical declarations alone establish package authority.
- Rationale: one authoritative parent keeps acceptance, risk, lifecycle, and completion deterministic while Supporting PRs permit cross-cutting execution.
- Reopen when: real work repeatedly requires multi-parent authority rather than informational references and Issue disposition.

### D16: Compact PR contract and risk authority

- Status: `approved` (owner, 2026-08-30)
- Decision: four required Ready sections, optional material risk/follow-up prose, Issue-owned contracts for governed PRs, and PR-owned contracts for Standalone R1–R4. R4 retains technical controls but requires no ceremonial Issue or second approval.
- Rationale: durable evidence remains complete while empty boilerplate and duplicate authority are removed.
- Reopen when: Standalone R4 cannot demonstrate pre-merge planning and independent verification without a separate object.

### D17: Asymmetric lifecycle and derived validation

- Status: `approved` (owner, 2026-08-30)
- Decision: Issue `Workflow` remains authoritative; PR state imposes coherence constraints; Supporting is lifecycle-neutral; Final merge authorizes convergence; closed-unmerged Final requires disposition. Four predicate groups are derived, with an event boundary after Merge.
- Rationale: preserves one lifecycle owner while mechanically detecting contradictions and recovery needs.
- Reopen when: observed topologies require another lifecycle owner or make phase derivation ambiguous.

### D18: Paired Ready, Merge, and Final disposition

- Status: `approved` (owner, 2026-08-30)
- Decision: invariant-pairing commands combine validation, deterministic cross-object mutation, terminal observation, reconciliation, and one receipt. Auto-merge retains responsibility without a watcher taxonomy.
- Rationale: reduces tool calls, context, partial-failure recipes, and operator-visible bureaucracy while increasing validation/mutation adjacency.
- Residual risk: commands own more recovery logic and require rigorous idempotency and partial-state tests.
- Reopen when: coherent recovery cannot be implemented or routine use still requires repeated manual sequences.

### D19: Uniform zero-friction authority

- Status: `approved` (owner, 2026-08-30)
- Decision: one package-wide workflow replaces repository semantic options; the user's instruction is sufficient authority for normal completion and any explicitly selected specific exception. Internal checks do not ask the user to reconfirm permission.
- Rationale: permission restatement, per-repository policy selection, and static watcher ownership add friction and duplicated state without protecting another authority boundary.
- Residual risk: explicit exceptions have less independent retrospective authorization evidence, intentionally favoring direct owner authority and zero friction.
- Reopen when: uniform defaults cannot work across consumers without weakening repository-owned enforcement.

### D20: Coordinated repair-on-touch migration

- Status: `approved` (owner, 2026-08-30)
- Decision: ship 1.7, update every local Project Standards consumer, migrate existing adopters, validate active PRs from observed state, and repair incompatible open work when touched. No legacy mode or migration ledger.
- Rationale: the owner is coordinating the fleet; a second migration state system would add state and calls without changing authoritative objects.
- Reopen when: active-work volume proves too large for bounded repair-on-touch.

## Complexity and efficiency disposition

Every proposed rule was reevaluated through correctness value, operator friction, repository configuration burden, duplicated authority/state, failure consequence, maintenance cost, recurring context cost, and tool-call cost.

### Retained as required complexity

- T0 semantic judgment and protected surfaces prevent behavioral changes from bypassing review.
- One governing authority and one-open-Final cardinality prevent ambiguous acceptance, risk, and completion.
- Cross-object lifecycle validation prevents false `Done`, stale review state, and orphaned Final disposition.
- Risk-proportionate review preserves evidence where failure consequence justifies it.
- Paired terminal mutations own convergence where GitHub and Issue Field writes cannot be atomic.

### Simplified

- Four required PR sections instead of six.
- Inferred routine check target instead of mandatory `--through` calls.
- Combined Ready/Merge operations instead of repeated receipt/check/mutate/check recipes.
- One-line auto-merge responsibility instead of watcher leases or configured ownership.
- On-demand T0 audit guidance instead of another routine command surface.
- Repair-on-touch migration instead of a repository-local active-PR ledger.

### Removed or rejected

- `admission_mode` and `native_closing` repository options.
- Mandatory explicit upgrade choices and per-repository semantic defaults.
- Issue/comment/object-bound break-glass approval.
- R4 mandatory governing Issue and second plan approval.
- Empty risk/follow-up boilerplate.
- Mandatory immediate PR receipt and explicit Structural/Ready call sequence.
- Persisted validation phase, watcher identity, event service, and migration ledger.

### Efficiency effect

- Routine PR flow becomes one draft creation, one paired Ready call, and one paired Merge call instead of separate receipt, checks, lifecycle mutations, ready mutation, merge, Issue close, and post-merge reconciliation calls.
- The skill carries routing and ordinary invariants; detailed T0 audit, relationship repair, and recovery procedures load only when invoked.
- Uniform behavior removes config inspection and repository-by-repository semantic-policy interpretation from ordinary context.
- JSON preserves machine detail without forcing human output to repeat every finding.

## Unresolved matters

Blocking: none.

Specification-level details:

- Exact `ready` and `merge` flags, merge-method selection, JSON fields, stable finding codes, and retry messages.
- Exact placement of Standalone Change risk and R4 plan/recovery evidence within the four-section body.
- Exact managed-block and reference partition that preserves the context budget.

These may be selected during specification authoring only when they do not reopen the approved authority, lifecycle, admission, or efficiency model.

## Downstream impact

- Revise [SPEC-GHW1](2026-08-06-github-workflow-package-spec.md) from its verified 1.6 baseline to the approved 1.7 target.
- Implement a new immutable 1.7 payload, Go behavior, tests, references, adoption/upgrade guidance, and managed blocks.
- Publish 1.7 in a Project Standards release.
- Update all locally cloned Project Standards consumers and migrate repositories already using `github-workflow`.
- Normalize incompatible active PRs when touched; do not rewrite terminal evidence.

## Sources

| Source | Classification | Material finding |
| --- | --- | --- |
| [SPEC-GHW1](2026-08-06-github-workflow-package-spec.md) revision 1.34 | verified current state | Exact shipped 1.6 behavior and deviations; independent native and Opus baseline verification completed before this revision. |
| [GitHub Repository Administration Standard (preliminary)](archive/2026-08-06-github-repo-administration-preliminary-design.md) | prior approved design | Issue Types, fields, lifecycle, risk ladder, and earlier Issue/PR model. |
| Owner-supplied `PR Versus Direct Commits.md` memo | design input | PR admission rationale, Final/Supporting/Standalone relationships, and cross-object consistency proposal. |
| `standards/github-workflow/versions/1.6/**` | current implementation | Existing skill, references, provider, schema, and immutable payload boundary. |
| GitHub PR-linking, ruleset, and automatic-closing documentation verified 2026-08-30 | external facts | Native closing is target/config dependent; package semantics cannot depend on auto-close. |

## Spec-authoring handoff

- Design brief: `docs/specs/2026-08-06-github-workflow-package-design.md`
- Operation: `revise`
- Status: `approved`
- Target: `github-workflow` 1.7, based on the independently verified 1.6 master-spec baseline.
- Outcome: one uniform, low-friction workflow that treats the owner's instruction as sufficient authority, permits only T0 editorial direct admission autonomously, and uses canonical PR relationships plus paired commands for everything else.
- Preserve:
  - repository ownership of branch topology, integration-target names, merge method, and live required checks;
  - T0's full conjunctive predicate and exact trailer;
  - exactly one Final/Supporting/Standalone declaration, same-repository governed Issues, and one-open-Final cardinality;
  - Issue-owned lifecycle for governed PRs and PR-owned contract/lifecycle for Standalone;
  - R1–R4 Standalone, with R4 technical controls but no mandatory Issue or second approval;
  - four derived predicate groups and six action categories;
  - draft-first agent creation, paired Ready/Merge/Final-disposition operations, and retained auto-merge responsibility;
  - package-wide defaults with no new semantic config options;
  - repair-on-touch migration and fleet-wide 1.7 reconciliation.
- Do not introduce:
  - per-repository admission/native-closing switches;
  - mandatory Issue creation for Standalone or R4;
  - secondary permission artifacts;
  - persisted validation phase or watcher ownership;
  - mandatory empty sections, immediate receipts, or repeated phase commands;
  - branch-name conventions or duplicated required-check lists.
- Specification may decide exact flags, result schemas, finding codes, retry messages, section placement, and reference partition without reopening the approved model.
- Blocking decisions: none.
