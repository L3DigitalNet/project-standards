---
bug_id: '004'
date: '2026-08-01'
title: 'agent-handoff SessionStart failed through a rejecting Python shim'
services: '[agent-handoff, claude-code, codex, python, uv]'
status: 'fixed'
---

# 004 — Agent Handoff SessionStart failed through a Python shim

**Status:** fixed in the Agent Handoff 1.8 candidate; release and consumer reconciliation remain pending.

## Symptom

The package-managed Claude Code and Codex SessionStart commands exited before the shared hook ran when `python3` resolved to the `uv-strict-python` rejecting shim. Automatic startup emitted no handoff context even though Agent Handoff validation and direct platform-interpreter execution passed.

## Cause

Both registrations executed the executable hook path directly. Its `#!/usr/bin/env python3` shebang delegated interpreter selection to `PATH`, where the policy shim rejected direct Python invocation before hook code could inspect the event.

## Fix

Agent Handoff 1.8 renders an adaptive launcher for both harnesses. It probes a quiet Python 3.14-or-newer without consuming SessionStart stdin, then falls back to a quiet, project-independent `uv run --no-project --python 3.14 --no-python-downloads` preflight and execution. If neither runtime is usable, it emits one bounded stderr diagnostic, no stdout, and exits nonzero.

Regression tests cover both harnesses, noisy rejecting shims, direct Python, `uv` fallback, unavailable runtimes, failed `uv` resolution, provider/resource parity, and immutable 1.7 preservation.

## Lesson

- A managed hook command must control interpreter selection instead of relying on an environment-sensitive shebang.
- Runtime probes must not consume hook stdin or emit transport-corrupting stdout.
- A fallback executable's presence is insufficient; preflight the exact interpreter request before selecting it.
