---
schema_version: '1.1'
id: 'runbook-j72kke-verify-implementation-workflow'
title: 'Verify Implementation Workflow'
description: 'Procedure for verifying a completed implementation against its specification, plan, quality gates, and observable behavior.'
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
  - 'docs/workflows/review-spec.md'
  - 'docs/handoff/specs-plans.md'
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# Verify Implementation Workflow

## Purpose

Structured procedure for verifying a completed implementation against its spec and plan before claiming the work is done. Verification means running things and observing outcomes — command output is evidence; assertions without output are not.

## Inputs

- The governing spec and plan, including their Definition-of-Done and acceptance criteria.
- The implementation: the commits or working-tree diff that claims to complete the work.
- The repository's quality gates. Discover the current, complete list from the repository's agent instructions, toolchain config, and CI workflows at verification time — gate lists drift, and a stale list verifies against the wrong bar.

## Workflow Steps

### Map Claims to Evidence

- List every plan task and every in-scope spec requirement / Definition-of-Done item.
- For each, identify the concrete evidence that proves it: a passing test, a command with expected output, an observable file or state.
- Flag any item with no verifiable evidence — that is a finding, not a pass.

### Run the Full Gate

- Run every quality gate the repository defines — formatters, linters, type checkers, test suites with coverage, security/dependency audits, documentation validators — not just the ones near the change.
- Run any change-specific validators the spec or plan names (schema checks, generated-artifact checks, contract validators).
- Prefer the repository's aggregate check command (a `check` script, make target, or CI-mirroring runner) when one exists, so nothing is skipped by hand-picking.
- Record actual pass/fail output. A failing gate stops verification: fix or report, never rationalize.

### Exercise the Behavior

- Drive the changed behavior end to end at least once through its real entry point — run the CLI, hit the endpoint, trigger the job, render the artifact. Passing tests alone do not verify the feature works where users invoke it.
- Check the negative path: the change rejects or reports what it is supposed to reject.

### Check the Deliverable Set

- Every file the plan says it creates or edits exists and matches the plan's intent; nothing extra was committed.
- Each planned commit exists, in order, with the tree green at each step (spot-check if the plan required commit-granular consistency).
- Documentation is kept in step: work queues, status documents, durable project knowledge, and the changelog where the change is release-visible — whichever of these the repository maintains.
- Traceability artifacts (requirement matrices, status tables) are updated to reflect reality — no `Passing` claims without the evidence recorded above.

### Handle Deviations

- Any divergence from the plan or spec — skipped step, changed approach, extra work — is written down (deviations log, review round, or session log), not silently absorbed.
- A deviation that changes spec-visible behavior requires updating the spec, not just noting the difference.

### Report the Outcome

- Report results with evidence: which gates ran, their output, which Definition-of-Done items passed, and any open findings.
- If the verification is a formal round (gating a release or milestone closure), save it to the repository's reviews location (commonly `docs/reviews/`) as `[YYYY-MM-DD]-[work-name]-verification.md` — same conventions as reviews: no frontmatter unless required, audience is the implementing agent, verdict up front (**VERIFIED**, **VERIFIED WITH FOLLOW-UPS**, or **NOT VERIFIED**).
- Otherwise record the outcome wherever the repository tracks status and session history.
- Never claim completion with a failing gate, an unexercised behavior, or an unmapped Definition-of-Done item.
