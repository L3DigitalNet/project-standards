---
bug_id: '005'
date: '2026-08-04'
title: 'agent-handoff 1.8 SessionStart never runs because args selects exec form'
services: '[agent-handoff, claude-code, hooks]'
status: 'fixed'
---

# 005 — Agent Handoff SessionStart never runs under exec form

**Status:** fixed. Diagnosed and tracked as issues #122 and #124; shipped in Agent Handoff 1.9 as part of the v5.15.0 open-issue resolution program.

## Symptom

SessionStart appears healthy and injects repository context, but the `state.md` section is absent. Nothing fails loudly: the hook error is non-blocking, so the session starts normally and an agent that trusts `CLAUDE.md` — which says not to reread injected state — proceeds with no handoff state at all. Reported across eight repositories.

Running the payload's `session_start.py` directly renders the state block correctly, which is what makes the failure look like a hook-content problem when it is not.

## Cause

The Agent Handoff 1.8 Claude Code integration declares its hook with a `sh -c '…'` interpreter-selection wrapper **and** an empty `args` array. Claude Code has two spawn paths: with `command` alone the string reaches a shell, but the presence of `args` — including an empty one — selects exec form, where `command` is resolved as a literal executable via `posix_spawn`. The harness therefore looks for a file named `sh -c 'if python3 …'` and fails with `ENOENT`.

`args: []` was inert from 1.1 through 1.7 because `command` was then a bare script path, which is a valid `argv[0]` under either spawn path. Bug 004's fix introduced the wrapper, making 1.8 the first version where the two fields are mutually incompatible.

## Fix

Shipped. Agent Handoff 1.9 in v5.15.0 fixes the Claude SessionStart spawn form (#122; #124 duplicate): the rendered Claude entry reaches a shell, changing nothing else about the wrapper or its timeout, and leaving 1.8 byte-identical and selectable. See the `v5.15.0` row in `docs/handoff/deployed.md`.

## Lesson

- A hook registration's spawn form is part of its contract. Adding a shell wrapper to `command` is not a local change when a sibling field silently selects how `command` is interpreted.
- A non-blocking hook failure is a silent failure. Injection paths need a positive signal that the payload arrived, because "the session started fine" is indistinguishable from "the hook never ran".
- Verify the delivered artifact, not the artifact in isolation. Running the hook script by hand proved the script worked and hid the defect for a full day; the bug lived in how the harness was told to invoke it.
- Related: [004](004-agent-handoff-session-start-python-shim.md) fixed the interpreter-selection problem whose fix introduced this one.
