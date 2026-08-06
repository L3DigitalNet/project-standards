---
schema_version: '1.1'
id: 'decision-q3w8fn-github-workflow-package-design'
title: 'github-workflow standard package design'
description: 'Approved design for the github-workflow Catalog 5 consumer package: the GitHub Repository Administration Standard delivered with a mandatory skill.'
doc_type: 'decision'
status: 'active'
created: '2026-08-06'
updated: '2026-08-06'
tags:
  - 'standard'
aliases: []
related: []
---

# github-workflow standard package design

## Status and provenance

- Status: `approved`
- Operation: `create`
- Decision owner: repository owner
- Created and approved: `2026-08-06`
- Revision: 1.2 — 2026-08-06 owner-directed amendment: operator issue/PR summaries follow a packaged attention-first layout shipped as a sixth reference (D8). Prior: 1.1 (same day) Go skill tooling (D7); initial approval 2026-08-06.
- Prior design brief: none
- Working-state source: `.project-pipeline/github-workflow-package/design-discovery/` (removed after promotion)
- Design input: [GitHub Repository Administration Standard (preliminary)](archive/2026-08-06-github-repo-administration-preliminary-design.md)

This brief settles the package contract only. The GitHub operating model itself — object model, Issue Types, Issue Fields, lifecycle, invariants, adoption phases — is governed by the preliminary design input and is consumed here as settled.

## Problem and intended outcome

The GitHub Repository Administration Standard defines how organization-owned GitHub repositories function as the durable control plane for local-agent development: Issues as authorized work contracts, seven organization-level Issue Fields as typed metadata, PRs as execution evidence, and deterministic mechanisms rather than model judgment for policy. That standard currently exists only as an advice-style document. The outcome of this design is a Catalog 5 consumer package, `github-workflow`, that delivers the standard's adoption phases 1–2 to consumer repositories with a mandatory skill as the behavioral core, so that any agent session in a consuming repository operates the model consistently.

## Current context

- Governing authoring contract: Standard Bundle Authoring 2.6 (SPEC-BA02); payload schema 1.0; immutable digest-pinned versions under `standards/github-workflow/versions/X.Y/`.
- Direct structural precedent: `agent-handoff` 1.9 — managed skill artifacts under `.agents/skills/<name>/`, `agents/openai.yaml` companion, markdown-block contributions gated on a `harnesses` option, rendered `policy.toml` under `.standards/packages/<id>/`, Python providers.
- Bug 006: create-only artifacts cannot reach existing consumers and are invisible to drift-check; a resolution decision is owed under issue #128.
- Packages are independent by default; relationships are declared, never hidden dependencies.
- GitHub organization-level Issue Fields became generally available to organizations on GitHub Free in July 2026, exposed through the API and GitHub MCP.

## Scope

### In scope

- The v1.0 package contract: payload artifact set, contributions, config schema, skill boundary and structure, providers, capabilities, relations.
- The org-schema audit shape: a versioned in-package schema resource plus a skill-driven audit procedure over live organization state.

### Non-goals

- Redesigning the GitHub operating model settled by the design input.
- Adoption phases 3–6: Actions-based invariant enforcement, coordinator and claiming machinery, unattended dispatch, GitHub-hosted micro-agents.
- Personal-account repository support. The package targets organization-owned repositories only; all repositories are being migrated to the organization.
- GitHub Issue Forms delivery under `.github/ISSUE_TEMPLATE/`.
- Merge gating or any review automation.

### Deferred considerations

- Issue Forms as managed artifacts — reconsider when human web-UI issue capture becomes routine.
- Phase-3 deterministic invariant enforcement — reconsider after operating experience under phases 1–2.
- A `migrate` provider — add in a minor version if legacy label-based approximations are discovered in consumer repositories.

## Constraints, assumptions, and agent-applied defaults

Constraints:

- The skill mutates repository-scoped work state via `gh`; organization-level schema (Issue Types, Issue Fields) is audit-only for agents, with changes applied by humans.
- Providers must remain offline-deterministic within the reconcile model; no provider may perform network calls.
- The published payload must be organization-agnostic; the organization login is consumer configuration.

Assumptions:

- The Issue Fields GA API/MCP surface is stable enough to pin an audit procedure against. If false, the skill's audit procedure needs a version note, not a package redesign.

Agent-applied defaults (low consequence, reversible):

- The org-schema resource stays YAML, matching the design input's §35 rendering; it is a read-only reference the skill parses, and source fidelity aids the human audit conversation.
- Capability naming mirrors the `agent-handoff` convention.

## Selected design

Package `github-workflow` 1.0 delivers everything as `managed` artifacts — zero create-only artifacts, hence zero bug-006 exposure, and every delivered file is upgradeable and drift-visible.

### Skill

One mandatory skill, `github-workflow`. Trigger boundary: agents must load it before creating or mutating GitHub work state — issues, issue fields, PRs, lifecycle transitions, milestones — performing triage or an org-schema audit, or presenting an operator-requested issue/PR summary. Plain read-only queries (`gh issue view`, `gh pr list`) remain exempt. `SKILL.md` carries the decision procedures: Issue Type selection, field discipline, refusal rules, and when to consult each reference. Reference files provide progressive disclosure:

| Artifact | Consumer target | Content |
| --- | --- | --- |
| `SKILL.md` | `.agents/skills/github-workflow/SKILL.md` | Decision procedures, refusals, trigger boundary |
| `openai.yaml` | `.agents/skills/github-workflow/agents/openai.yaml` | Codex skill companion |
| `field-vocabulary.md` | `.agents/skills/github-workflow/references/` | Seven fields, values, pinning matrix, fields-not-to-create list |
| `org-schema.yaml` | `.agents/skills/github-workflow/references/` | Machine-readable baseline schema the audit compares against |
| `issue-structure.md` | `.agents/skills/github-workflow/references/` | Canonical issue body headings and the five Issue Type definitions |
| `pr-standard.md` | `.agents/skills/github-workflow/references/` | PR content standard and draft-PR policy |
| `review-checklist.md` | `.agents/skills/github-workflow/references/` | Layered PR-review checklist — discipline only, no gating |
| `summary-format.md` | `.agents/skills/github-workflow/references/` | Attention-first layout for operator-requested issue/PR summaries |
| `policy.toml` | `.standards/packages/github-workflow/policy.toml` | Rendered consumer configuration for the skill to read |
| `gh-workflow-audit` | `.agents/skills/github-workflow/bin/gh-workflow-audit` | Compiled Go audit tool (linux/amd64), mode 0755 |

### Contributions

A compact (~12-line) markdown-block contribution into `AGENTS.md` (Codex) and `CLAUDE.md` (Claude Code), gated on the `harnesses` option. It carries the skill mandate plus the standing invariants that must bind even when the skill was never loaded, because violating them is expensive before anyone notices:

- An Issue is the unit of authorized work; a nontrivial PR links its governing Issue (INV-008).
- Never infer readiness — `Workflow = Ready` plus `Execution mode` authorization, never "the issue is open" (INV-005).
- Never self-promote `Execution mode`; never mutate organization-level Issue Fields or Types — org schema changes are human-applied (INV-006).
- Terminal-state sync: `Done` → closed as completed; `Dropped` → closed as not planned (INV-010/011).
- Durable follow-up work discovered during implementation becomes an Issue, not prose (INV-015).

The organization name renders into the block from configuration.

### Configuration

Exactly two options:

| Option | Type | Purpose |
| --- | --- | --- |
| `organization` | string, required | GitHub organization login; renders into the managed block and `policy.toml`; the audit target |
| `harnesses` | array of `claude-code` \| `codex`, required | Gates the AGENTS.md and CLAUDE.md contributions and the `openai.yaml` artifact |

### Relations and capabilities

- `companions = ["agent-handoff"]` — advisory affinity: handoff closeout and Issue/PR closeout interleave in the same session tail. No dependency.
- `extends = []`, `conflicts = []`.
- Capabilities: `github-workflow.audit`, `github-workflow.validate`, `github-workflow.drift-check`.

### Providers

`render-semantic` (block and `policy.toml` from configuration), `validate`, `verify`, `drift-check`, `upgrade`. No `scaffold` (no create-only artifacts, no scaffolding need) and no `migrate` (no legacy predecessor). The org audit is skill-driven and is never a provider: providers run offline against files inside the reconcile transaction, and a network-dependent provider would break that model. Under D7 the audit is executed by a packaged Go binary the skill invokes; it runs only in agent sessions under the operator's `gh` authentication, never during reconcile.

### Trust boundaries

- Repository-scoped work-state mutation: agent-performed through the skill.
- Organization-level schema: agent-audited, human-applied.
- Reconcile/providers: offline and deterministic; the online audit lives only in the skill.

## Consequential decisions

### D0: Pre-discovery scoping

- Status: `approved` (user, 2026-08-06)
- Decisions: design-discovery before specification; v1.0 delivers adoption phases 1–2 only; org schema ships as a versioned package resource audited by the skill with human-applied changes; package and skill name `github-workflow`; organization-owned repositories only, no personal-account fallback.
- Rationale: phases 1–2 keep v1.0 free of enforcement machinery the design input itself defers; org-only keeps the skill single-surface (Issue Fields do not exist on personal accounts); human-applied org changes keep the package from owning un-drift-checkable external state.
- Reopen when: personal-account support only if the org migration is abandoned; phase 3+ after operating experience.

### D1: Skill boundary and structure

- Status: `approved` (user, 2026-08-06; agent recommendation accepted)
- Decision: one skill with the mutation-boundary trigger and thin on-demand references; the layered PR-review checklist is included as reference discipline with no automation.
- Alternatives rejected: two skills (workflow + admin audit) — fuzzy triage/admin boundary, double versioning, blurred mandatory-skill story; narrow skill with a fat managed block — inverts the repository's compact-block pattern and taxes every session's context.
- Reversibility: high — splitting into two skills later is an additive minor.
- Reopen when: the org-audit procedure grows to multi-org or multi-schema scale.

### D2: Payload artifact set

- Status: `approved` (user, 2026-08-06; agent recommendation accepted)
- Decision: the all-managed artifact set in Selected design; GitHub Issue Forms deferred entirely.
- Alternatives rejected: managed `.github/ISSUE_TEMPLATE` forms now — forms cannot populate Issue Fields, `.github/` is consumer-owned, per-repo `area/*` customization fights managed ownership, and agents author most issues here; a create-only seed form — bug 006 makes it unreachable for existing consumers and drift-invisible.
- Reopen when: human web-UI capture becomes routine.

### D3: Managed-block content

- Status: `approved` (user, 2026-08-06; agent recommendation accepted)
- Decision: skill mandate plus the five standing invariants listed in Selected design; organization name rendered from configuration.
- Alternatives rejected: pointer-only block — no invariant survives a skipped skill load; full inline rule summary — duplicates references and breaks the compact-block pattern.
- Reopen when: operating experience shows an invariant routinely violated despite the block — the response is phase-3 deterministic enforcement, not a bigger block.

### D4: Configuration schema

- Status: `approved` (user, 2026-08-06; agent recommendation accepted)
- Decision: exactly `organization` and `harnesses`.
- Alternatives rejected: `area_labels` (live GitHub labels are the source of truth; a config copy duplicates state), enabled Issue Type subsets (the vocabulary is fixed and org-scoped), project numbers (Projects are derived views), field-vocabulary customization (would fork the org-wide schema).
- Reversibility: additions are additive minors; `organization` may become a list if a second organization appears.

### D5: Relations and capabilities

- Status: `approved` (user, 2026-08-06)
- Decision: `companions = ["agent-handoff"]`; capabilities `github-workflow.audit`, `.validate`, `.drift-check`.

### D6: Provider set

- Status: `approved` (user, 2026-08-06; agent-applied default confirmed)
- Decision: `render-semantic`, `validate`, `verify`, `drift-check`, `upgrade`; no `scaffold`, no `migrate`; the org audit is never a provider.
- Reopen when: legacy label-based approximations are found needing migration signatures, or reconcile gains a sanctioned online phase.

### D7: Skill tooling in Go; audit ships as a per-platform binary

- Status: `approved` (user, 2026-08-06; owner directive)
- Decision: any executable shipped with the skill is implemented in Go (ADR 0027 lane). v1.0 ships the org audit as a compiled Go tool, `gh-workflow-audit`, delivered as a committed, digest-pinned managed artifact for `linux/amd64` only, reproducibly built (`CGO_ENABLED=0`, `-trimpath`, toolchain pinned by `go.mod`). The skill invokes the tool instead of prose `gh` command sequences.
- Agent recommendation differed: source-shipped, locally-built delivery was recommended to keep the payload platform-agnostic and text-diffable; the user selected committed binaries for zero consumer toolchain requirements.
- Agent-applied scoping default: single platform `linux/amd64`, justified by the all-Linux consumer fleet; additional platforms are an additive deferral.
- Residual risk: binary bytes enter the digest-pinned payload lineage (repo growth per payload version; artifacts not reviewable by diff). Mitigation: the reproducible-build requirement makes the binary independently rebuildable and verifiable from the repository Go source.
- Reopen when: a non-linux/amd64 consumer appears (add platforms), or payload growth becomes operationally painful (revisit source-built delivery).

### D8: Standardized attention-first operator summaries

- Status: `approved` (user, 2026-08-06; owner directive)
- Decision: operator-requested issue/PR summaries follow one packaged layout, shipped as a sixth reference (`summary-format.md`): scope header (target, timestamp, counts) → Needs-attention section (Blocked, Needs definition, terminal-sync mismatches, passed target dates) → Issues table (number, Type, title, Workflow, Priority, Size or Severity, Execution mode) → PRs table (number, title, governing Issue, state, CI, risk notes) → discovered-follow-ups tail. Presenting such a summary becomes an explicit skill trigger even though gathering is read-only.
- Alternative rejected: queue-first layout (table-led, attention as a flag column) — weaker at surfacing stuck work; the owner selected attention-first as recommended.
- Rationale: summaries exist to drive operator decisions; leading with what needs the human matches the control-plane philosophy, and a packaged layout makes reports comparable across sessions and agents.
- Reopen when: recurring summary needs appear that the fixed sections cannot express (e.g., milestone burn-down), warranting layout variants in a minor version.

## Complexity disposition

### Retained

- Packaged Go audit binary (D7) — deterministic, testable audit output in place of fragile prose command sequences; committed per-platform delivery is the owner-selected distribution.
- Reference-file split (six files) — guards `SKILL.md` size; progressive disclosure is an established repository pattern.
- Configuration-rendered `organization` — keeps the published payload org-agnostic; a hardcoded organization would force a payload version per org change.
- Full provider set minus `scaffold`/`migrate` — required by the Standard Bundle Authoring managed-artifact integrity contract.

### Deferred

- Issue Forms delivery — trigger: routine human web-UI capture.
- Phase-3 deterministic invariant enforcement — trigger: phases 1–2 operating experience.
- `migrate` provider — trigger: discovered legacy approximations needing signatures.

### Rejected

- Source-shipped, locally-built skill tooling — owner-rejected in favor of committed binaries; zero consumer toolchain requirement won.
- `go install` distribution for skill tooling — network dependency and a second version channel outside the payload digest contract.
- Two-skill split — fuzzy boundary, double versioning burden.
- Fat managed block — context tax on every session; pattern inversion.
- Configuration for area labels, Issue Type subsets, project numbers, or field customization — duplicated or forked state.
- Create-only seed templates — bug 006.
- Network-dependent audit provider — breaks the offline reconcile model.

### Preserved extension seams

- `organization` may become a list additively.
- Forms and `migrate` arrive as additive minors without contract breaks.
- Phase-3 enforcement can consume the same invariants the managed block names.

## Unresolved decisions

Blocking: none.

Non-blocking:

- Release-train placement (after the v5.17.0 ADR train) — owner decision at specification/plan stage.
- Exact `SKILL.md` prose, `gh`/GraphQL audit commands, and block wording — owned by spec-authoring and implementation.

## Downstream impact

- A new Project Specification (spec-authoring) formalizing this contract.
- Package implementation under `standards/github-workflow/`, catalog and index wiring, and `docs/handoff/architecture.md` updates at implementation time.
- No existing specification or plan becomes stale; this is a new package family.

## Sources

| Source | Classification | Material finding |
| --- | --- | --- |
| [`docs/specs/archive/2026-08-06-github-repo-administration-preliminary-design.md`](archive/2026-08-06-github-repo-administration-preliminary-design.md) | design input (user-approved) | The settled operating model: five Issue Types, seven org Issue Fields, lifecycle, invariants INV-001–016, six adoption phases, permission model |
| `standards/agent-handoff/versions/1.9/payload.toml` | current state | Payload vocabulary precedent: managed skill artifacts, harness-gated contributions, rendered policy, provider set |
| `docs/handoff/architecture.md` | repository decision | Bug 006 constraint on create-only artifacts; package independence; SBA 2.6 authority |
| `docs/handoff/specs-plans.md` | repository decision | Spec-first precedent (SPEC-DPEY) for the agent-handoff package |

## Spec-authoring handoff

- Design brief: `docs/specs/2026-08-06-github-workflow-package-design.md`
- Operation: `create`
- Status: `approved`
- Problem and outcome: package the GitHub Repository Administration Standard (phases 1–2) as Catalog 5 consumer package `github-workflow` with a mandatory skill.
- Scope boundary: package contract only; org-owned repositories; no enforcement automation, coordinator, Issue Forms, or personal-account support.
- Selected design: all-managed delivery — one skill with six reference files, compact invariant-bearing managed block, two-option config (`organization`, `harnesses`), `companions = ["agent-handoff"]`, offline provider set with the org audit skill-driven via `gh`.
- Approved consequential decisions:
  - D0 scoping (phases 1–2, org-only, audit-only org schema, name)
  - D1 single skill, mutation-boundary trigger, references incl. review checklist
  - D2 all-managed artifacts; Issue Forms deferred
  - D3 block = skill mandate + INV-005/006/008/010/011/015; config-rendered org
  - D4 config = `organization` + `harnesses` only
  - D5 companions agent-handoff; audit/validate/drift-check capabilities
  - D6 providers render-semantic/validate/verify/drift-check/upgrade; no scaffold/migrate
  - D7 skill tooling in Go; audit ships as committed linux/amd64 binary, reproducibly built
  - D8 operator summaries follow the packaged attention-first layout (summary-format.md); summary presentation is a skill trigger
- Agent-applied defaults:
  - org-schema resource in YAML (design-input §35 fidelity)
  - capability naming mirrors agent-handoff
- Assumptions:
  - Issue Fields GA API/MCP surface stable enough to pin the audit procedure
- Blocking decisions: none
- Non-blocking matters:
  - release-train placement — decide at spec/plan stage
  - SKILL.md prose, audit commands, block wording — spec-authoring/implementation
- Downstream impact:
  - new specification and new package family; no existing artifact staleness
- Material source artifacts:
  - `docs/specs/archive/2026-08-06-github-repo-administration-preliminary-design.md`
  - `standards/agent-handoff/versions/1.9/payload.toml`
  - `docs/handoff/architecture.md`
