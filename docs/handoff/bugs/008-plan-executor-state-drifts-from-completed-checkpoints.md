---
bug_id: '008'
date: '2026-08-09'
title: 'plan executor state records completed tasks as not-started, so handoff docs derived from it mislead'
services: '[execute-plan, handoff, docs]'
status: 'open'
---

# 008 — Plan executor state drifts from completed checkpoints

**Status:** open. `docs/handoff/specs-plans.md` is corrected; the executor state itself still records the drift and must be reconciled through the execute-plan skill, never by hand.

## Symptom

During a full open-issue triage, the ready state of the open-issue resolution program read three different ways across four documents:

- `docs/handoff/state.md` and `docs/STATUS.md` — T16, T19, T36 terminal; T24 ready.
- `docs/handoff/specs-plans.md` — "Remaining tail: T16/T19/T36 … Ready: T16, T19".
- `.project-pipeline/2026-08-01-open-issue-resolution-program/p4.md` and `p10.md` — all three tasks `not-started`, every subtask unchecked, no evidence recorded.

A reader who trusts the executor state concludes T24 is blocked behind T36 and therefore that #62 and #55 cannot start. That conclusion was drawn and published in a triage report and in comments on both issues before it was caught.

## Cause

The work completed but the state files were never advanced. The checkpoints are real and verifiable:

| Task | Checkpoint | Subject |
| --- | --- | --- |
| T16 | `50d0c364` | bound the documented Prettier scope to the declared corpus |
| T19 | `229a4bc1` | keep undeclared Ruff plugin sub-tables consumer-owned |
| T36 | `e13e1a66` | qualify and publish v5.16.0 |

All three landed 2026-08-05; #88 and #99 closed the same day with the v5.16.0 release. T36's own `depends_on` is `[T16, T19]`, so T24's gate has been satisfied since then.

`docs/handoff/specs-plans.md` was written from the executor state rather than from the checkpoints, so the drift propagated from a generated-state file into a durable handoff document, where it outlived the release that disproved it.

## Fix

`docs/handoff/specs-plans.md` now records the three tasks as complete with their checkpoint SHAs, names T24 as the ready task, and flags the executor state as stale. The `.project-pipeline` files are owned by the execute-plan skill and were deliberately left untouched.

## Lesson

- **A task's state file is a claim; its checkpoint commit is the evidence.** When the two disagree, the commit wins — verify with `git log -1 <sha>` and the issue's close date.
- **Do not derive durable handoff prose from generated executor state.** `specs-plans.md` outlives any execution, so it must cite checkpoints, not restate a pipeline file.
- Agreement between documents proves nothing when they share an upstream source. `state.md` and `STATUS.md` were right because they were written from release evidence.
- Verifying claims against source is worth its cost. Fourteen of twenty issues in this pass carried a wrong premise, and this one sat in the handoff surface itself.
