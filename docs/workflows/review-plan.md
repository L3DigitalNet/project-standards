---
schema_version: '1.1'
id: 'runbook-ykorlh-review-implementation-plan-workflow'
title: 'Review Implementation Plan Workflow'
description: 'Evidence-based procedure for reviewing an implementation plan against its specification and live repository state.'
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
  - 'docs/workflows/review-spec.md'
  - 'docs/workflows/verify-implementation.md'
  - 'docs/handoff/specs-plans.md'
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# Review Implementation Plan Workflow

## Purpose

Structured procedure for reviewing an implementation plan before execution. A plan review is stricter than a spec review: the plan's snippets, commands, and orderings will be executed verbatim, so every one of them is checked against ground truth, not read for plausibility.

## Inputs

- The plan under review, pinned to a specific state (commit hash or working tree).
- The spec or design the plan implements (read for coherence; do not re-litigate a spec that already passed review).
- The live repository the plan will run against: source, tests, fixtures, configs, CI workflows, and toolchain versions.
- The repository's conventions for where plans and reviews live. Discover these from the repository's agent instructions and documentation layout; do not assume paths from memory.

## Workflow Steps

### Prepare

- Read the plan end to end before recording any findings.
- Read the governing spec/design and note which of its requirements the plan claims to satisfy.
- Identify the quality gates this repository enforces (formatters, linters, type checkers, test suites, CI checks) from its agent instructions, toolchain config, and CI workflows — the plan will be judged against these, so establish the current list first.
- Record the review target state (commit hash or "working tree after `<ref>`") in the review header.

### Initial Review

Check each dimension by executing or tracing against ground truth:

- **Snippets survive the gates.** Every code snippet passes the formatter, linter, type checker, and style limits it will face. Run the repository's actual tools against the snippet where practical.
- **Commands run as written.** Every command in the plan is executable in this repository with the stated working directory, flags, and dependencies.
- **Ground-truth premises hold.** Every cited file path, function signature, test name, count, commit hash, and config value exists and matches the plan's description — verified live, not from memory.
- **Test-first states are real.** For each test the plan writes before its implementation, trace that the test actually fails at that point in the sequence — and for the stated reason.
- **Task ordering and dependencies.** No task consumes an artifact a later task creates; file lists match the steps that edit them; staged files are all actually modified.
- **Commit-granular consistency.** Each planned commit leaves the tree green and internally consistent — claims committed in one task must not cite evidence created by a later task.
- **Gate coverage.** Every artifact the plan creates or edits is exercised by at least one gate the plan itself runs; flag latent failures that only detonate in later CI (e.g., a new file no plan step ever formats or lints).
- **Spec coverage.** Every in-scope spec requirement maps to a plan task; deviations from the spec are explicit.

### Classify Findings

- 🔴 **Blocking** — executing the plan as written fails a gate, breaks CI, or produces a wrong result.
- 🟡 **Should fix** — causes out-of-plan fix-up commits, rework, or implementer confusion.
- 🟢 **Optional** — polish; no functional consequence.

Number findings `F1`, `F2`, … in severity order. Each finding states the defect, the evidence (what was run or traced), and a concrete fix — preferably as the exact plan edit.

### Report Findings

- Document findings in a new Markdown file saved to the repository's reviews location (commonly `docs/reviews/`).
- Naming convention: `[YYYY-MM-DD]-[plan-name]-review.md`.
- Format and structure:
  - Audience: the LLM agent that wrote the plan.
  - Reviews are ephemeral; do not add frontmatter or metadata unless the repository's conventions require it.
  - Do not include suggestions for new features or out-of-scope extensions. Focus on the current plan and its intended execution.
  - Include:
    - Verdict: **APPROVE**, **APPROVE AFTER REVISION**, or **REVISE AND RE-REVIEW**.
    - Summary of the review and its method (what was executed vs. traced).
    - What was verified and held (so later rounds do not re-check it).
    - Findings with severity, evidence, and recommended plan edits.

### Subsequent Review Rounds

- Follow the same process as the initial review.
- Update the same review document: append a clearly labeled round section rather than creating a new file.
- Re-verify against the repository's current state — ground truth may have moved since the previous round.
- Verify each prior finding's fix against ground truth — re-run the failing check, do not accept "fixed" on assertion.
- Track round-to-round progress. The review has converged when a round produces no 🔴 findings and no new 🟡 findings; record the converged verdict.
