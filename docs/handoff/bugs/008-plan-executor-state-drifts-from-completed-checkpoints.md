---
bug_id: '008'
date: '2026-08-09'
title: 'superseded pre-format-3 checklists remained at the work-item root and were read as live executor state'
services: '[execute-plan, handoff, docs]'
status: 'fixed'
---

# 008 — Superseded plan checklists were read as live executor state

**Status:** fixed 2026-08-10. The superseded artifacts are deleted locally and `docs/handoff/specs-plans.md` is corrected. Filed upstream as [agent-configs#23](https://github.com/L3DigitalNet/agent-configs/issues/23).

## Symptom

During a full open-issue triage, the ready state of the open-issue resolution program read three different ways across four documents:

- `docs/handoff/state.md` and `docs/STATUS.md` — T16, T19, T36 terminal; T24 ready.
- `docs/handoff/specs-plans.md` — "Remaining tail: T16/T19/T36 … Ready: T16, T19".
- `.project-pipeline/2026-08-01-open-issue-resolution-program/p4.md` and `p10.md` — all three tasks `not-started`, every subtask unchecked, no evidence recorded.

A reader who trusts those checklists concludes T24 is blocked behind T36 and therefore that #62 and #55 cannot start. That conclusion was drawn and published in a triage report and in comments on both issues before it was caught.

## Cause

**The first diagnosis recorded here was wrong.** It attributed the drift to executor state that was never advanced. The executor state was correct throughout.

The work item carried two checklist trees. The pre-format-3 bridge wrote checklists to the work-item root; format 3 relocates execution state to `<work-item>/execution/`, and the migration left the older tree in place — ten `p*.md` files, `logs/`, and `notes.md`, all dated 2026-08-01/02 — beside the current `execution/` tree dated 2026-08-05.

The superseded files sit at the more prominent path, use different phase numbering, and carry the older bridge's generated header instructing a reader to edit them as live state. The triage read those.

The authoritative revision-4 state recorded T16, T19, and T36 as `done` with their checkpoint commits, and `plan.py` never consulted the superseded copies:

```console
$ uv run scripts/plan.py state <master> T16 --status done --commit 50d0c364
error: T16: transition done -> done is not permitted

$ uv run scripts/plan.py next <master>
ready:
  T24  [not-started]  Specify conformance linting for #62
```

| Task | Checkpoint | Subject |
| --- | --- | --- |
| T16 | `50d0c364` | bound the documented Prettier scope to the declared corpus |
| T19 | `229a4bc1` | keep undeclared Ruff plugin sub-tables consumer-owned |
| T36 | `e13e1a66` | qualify and publish v5.16.0 |

## Fix

The superseded root-level `p*.md`, `logs/`, and `notes.md` were deleted. `validate` and `next` return identical output before and after, confirming they were inert. `.project-pipeline/` is gitignored, so nothing was committed and no other checkout is affected.

`docs/handoff/specs-plans.md` records the three tasks as complete with their checkpoint SHAs and names T24 as ready.

The bridge gap — migration leaving superseded checklists at the work-item root with no removal, marker, or diagnostic — is [agent-configs#23](https://github.com/L3DigitalNet/agent-configs/issues/23). It was present through bridge 3.5.0, the last deployed generation; the deployed bridge (this repository's `scripts/plan.py` copy included) was retired on 2026-08-17 by `agent-configs` ADR-0023, and the engine now ships only inside the `plan-authoring`/`execute-plan` skill binaries. The `plan.py` invocations recorded under "Cause" are the historical transcript, not a current interface.

## Lesson

- **Locate the state root before reading state.** Two checklist trees existed and the stale one sat at the shallower path. `plan.py next` reads only the authoritative tree.
- **A generated "edit this file" header is not evidence that a file is live.** The superseded checklists carried the same authoritative header as the current ones.
- **Prefer the tool's answer to the file's contents.** Every `plan.py` command was correct throughout; only direct file reading was wrong.
- **Verify the cause, not just the symptom.** This record's first version saw the contradiction and misattributed it, queuing a fix for state that was already correct.
