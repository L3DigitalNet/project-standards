---
name: agent-handoff
description: Use when starting or closing an agent session, routing durable repository facts, maintaining status or task state, recording bugs, or reconciling a legacy handoff layout.
---

# Agent Handoff

Keep project knowledge in the repository and route it by lifetime. Eager state stays small; durable facts remain lazy and discoverable.

## Startup

- If SessionStart already injected `docs/handoff/state.md` and Git context, do not reread them ritualistically.
- In manual mode, read `docs/handoff/state.md`, inspect the current repository's Git state, and use the lazy pointers below.
- Read only this repository. Do not inspect home-directory globals, workstation state, or sibling repositories for project handoff.

## Fact routing

| Fact | Canonical owner |
| --- | --- |
| Current project snapshot | `docs/STATUS.md` |
| User-visible future work | `docs/TODO.md` |
| In-flight work or active incident | `docs/handoff/state.md` |
| Deployment truth | `docs/handoff/deployed.md` |
| Component graph or standing structural backlog | `docs/handoff/architecture.md` |
| Credential name, environment variable, secret name, or OpenBao path | `docs/handoff/credentials.md` |
| Stable project pattern | `docs/handoff/conventions.md` |
| Active specification or plan pointer | `docs/handoff/specs-plans.md` |
| Compact permanent session record | `docs/handoff/sessions/YYYY-MM.md` |
| Durable bug or gotcha | `docs/handoff/bugs/NNN-slug.md` |

Never store credential values. Keep completed work out of eager `state.md`; summarize current results in `docs/STATUS.md` and preserve history in the session log.

For bugs, allocate the lowest unused three-digit ID, never renumber an existing record, and keep `docs/handoff/bugs/INDEX.md` sorted by ID. A fixed bug remains as a durable gotcha; an obsolete record may become a one-line tombstone when stable links depend on its ID.

## Closeout

Update only facts changed during the session. Preserve user-authored task sections. Remove a completed standalone agent task after its current result is reflected in `docs/STATUS.md`; keep completed substeps that explain progress on a still-open parent. Append a compact session row when it adds durable value, then run relevant validation.

## Legacy reconciliation

Migration is an agent-guided review inside the current repository, not an automated converter. Inventory old evidence, map useful content to the canonical `docs/STATUS.md`, `docs/TODO.md`, and `docs/handoff/` owners, and preserve ambiguity for owner review.

Do not create a standard-owned migration manifest, conflict ledger, quarantine tree, converter, or global/fleet state. Do not compose hooks by guessing. Preserve useful content, install the selected v1 profile, validate the complete result, inspect the diff, and only then delete obsolete repo-local artifacts.

## Common mistakes

- Treating `docs/STATUS.md` as history instead of a current snapshot.
- Keeping completed work in eager state after a durable session record exists.
- Inventing migration structure instead of preserving uncertain evidence.
- Reading global or sibling state that lies outside the repository boundary.
