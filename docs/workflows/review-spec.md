---
schema_version: '1.1'
id: 'runbook-ujviau-review-specification-workflow'
title: 'Review Specification Workflow'
description: 'Evidence-based procedure for reviewing a specification against repository ground truth before planning or implementation.'
doc_type: 'runbook'
status: 'active'
created: '2026-07-10'
updated: '2026-07-10'
reviewed: null
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'agent'
tags:
  - 'meta-repo'
  - 'standards-platform'
aliases: []
related:
  - 'docs/workflows/review-plan.md'
  - 'docs/workflows/verify-implementation.md'
  - 'docs/handoff/specs-plans.md'
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# Review Specification Workflow

## Purpose

Structured procedure for reviewing a specification document before it is planned or implemented. The review is evidence-based: every claim the spec makes is checked against ground truth, never accepted on the spec's own authority.

## Inputs

- The spec under review, pinned to a specific state (commit hash or working tree).
- The ground truth it makes claims about: source code, tests, configs, CI workflows, architecture decisions, governing standards, and predecessor specs.
- The repository's conventions for where specs and reviews live. Discover these from the repository's agent instructions and documentation layout; do not assume paths from memory.

## Workflow Steps

### Prepare

- Read the spec end to end before recording any findings.
- Identify the governing documents: accepted architecture decisions, adopted standards, and any related or superseded specs.
- Record the review target state (commit hash or "working tree after `<ref>`") in the review header.

### Initial Review

Check each dimension and verify against ground truth:

- **Factual accuracy.** Every file path, command, count, commit hash, test name, and API/CLI reference in the spec exists and behaves as stated in the current repository — verify live, not from memory or from the spec's own citations.
- **Completeness.** Requirements cover the stated goals; error and edge cases are addressed; no undefined terms, silent TBDs, or unstated assumptions.
- **Internal consistency.** Sections do not contradict each other; requirement IDs are unique; tables and matrices agree with the prose.
- **External consistency.** No conflict with accepted architecture decisions, adopted standards, or sibling specs; any intentional deviation is explicit and justified.
- **Scope discipline.** Everything in the spec traces to the stated goal; flag scope creep and orphaned requirements.
- **Testability.** Every requirement and Definition-of-Done item is verifiable by a command, test, or observable state.
- **Risks and open questions.** Each is tracked with a resolution path, not left implicit.

### Classify Findings

- 🔴 **Blocking** — the spec cannot be implemented as written, or implementing it as written produces a wrong result.
- 🟡 **Should fix** — causes rework, implementer confusion, or avoidable fix-up commits.
- 🟢 **Optional** — polish; no functional consequence.

Number findings `F1`, `F2`, … in severity order. Each finding states the defect, the evidence (what was checked and how), and a concrete fix.

### Report Findings

- Document findings in a new Markdown file saved to the repository's reviews location (commonly `docs/reviews/`).
- Naming convention: `[YYYY-MM-DD]-[spec-name]-review.md`.
- Format and structure:
  - Audience: the LLM agent that wrote the spec.
  - Reviews are ephemeral; do not add frontmatter or metadata unless the repository's conventions require it.
  - Do not include suggestions for new features or out-of-scope extensions. Focus on the current spec and its intended functionality.
  - Include:
    - Verdict: **APPROVE**, **APPROVE AFTER REVISION**, or **REVISE AND RE-REVIEW**.
    - Summary of the review and its method.
    - What was verified and held (so later rounds do not re-check it).
    - Findings with severity, evidence, and recommended fixes.

### Subsequent Review Rounds

- Follow the same process as the initial review.
- Update the same review document: append a clearly labeled round section rather than creating a new file.
- Re-verify against the repository's current state — ground truth may have moved since the previous round.
- Verify each prior finding's fix against ground truth — do not accept "fixed" on assertion.
- Track round-to-round progress. The review has converged when a round produces no 🔴 findings and no new 🟡 findings; record the converged verdict.
