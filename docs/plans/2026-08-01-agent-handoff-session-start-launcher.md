# Agent Handoff SessionStart Launcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `agent-handoff@1.8` with working SessionStart commands for Codex and Claude Code when `uv-strict-python` shims reject direct hook execution.

**Architecture:** Clone immutable payload 1.7 into a new 1.8 payload and change only the two rendered harness registrations plus version-bound documentation and metadata. Each registration runs one bounded shell launcher that probes `python3` without consuming event stdin, otherwise invokes `uv` outside the consumer project with downloads disabled, then executes the unchanged shared hook.

**Tech Stack:** TOML/JSON package payloads, POSIX shell command hooks, Python 3.14, pytest, Project Standards package-contract tooling.

---

## Task 1: Pin the launcher regression contract

**Files:**

- Create: `tests/package_contract/test_agent_handoff_1_8.py`

- [ ] Write tests that load both rendered commands from payload 1.8 and execute each with valid SessionStart JSON.
- [ ] Add a rejecting `python3` shim first on `PATH`; provide a deterministic fake `uv` that records the exact arguments and delegates to `/usr/bin/python3`; require exit 0 and exactly one decoded context envelope.
- [ ] Add a no-`uv` lane with a valid isolated `python3`; require the same envelope and prove `uv` is not required.
- [ ] Add an unavailable-runtime lane; require nonzero exit, empty stdout, and one bounded prerequisite diagnostic on stderr.
- [ ] Run the focused test and observe RED because payload 1.8 does not exist.

## Task 2: Create the minimal immutable successor

**Files:**

- Create: `standards/agent-handoff/versions/1.8/**` from immutable `versions/1.7/**`
- Modify: `standards/agent-handoff/versions/1.8/resources/integration/claude-session-start.json`
- Modify: `standards/agent-handoff/versions/1.8/resources/integration/codex-session-start.toml`
- Modify: `standards/agent-handoff/versions/1.8/{README.md,adopt.md,agent-summary.md,payload.toml}`
- Modify: `standards/agent-handoff/versions/1.8/schemas/{provider-input.schema.json,migration-report.schema.json}`

- [ ] Copy 1.7 to 1.8 without changing predecessor bytes and update successor identity fields.
- [ ] Render the same launcher policy in both registrations, retaining `${CLAUDE_PROJECT_DIR}` for Claude Code and the Git-root expression for Codex.
- [ ] Recompute resource digests and the successor aggregate digest using package tooling.
- [ ] Run the focused regression tests and observe GREEN.

## Task 3: Activate and document 1.8

**Files:**

- Modify: `standards/agent-handoff/{standard.toml,README.md,adopt.md,agent-summary.md}`
- Modify: `catalogs/5.toml`
- Modify generated catalog/projection/lock surfaces selected by repository tooling.

- [ ] Register 1.8 as default and retain 1.7.
- [ ] Update mutable family navigation to 1.8 and document the interpreter fallback and failure recovery.
- [ ] Generate the source projection, package schemas, catalog, and reconciliation artifacts with repository commands.
- [ ] Run package validation, graph validation, schema freshness, and projection freshness checks.

## Task 4: Verify and independently review

**Files:**

- Delete after completion: `docs/plans/2026-08-01-agent-handoff-session-start-launcher.md`

- [ ] Build and extract a candidate wheel and run focused installed-wheel launcher probes.
- [ ] Run `scripts/verify.sh`, then `scripts/verify.sh --full` after the final content change.
- [ ] Run Agent Handoff validate and drift-check against the candidate wheel.
- [ ] Ask an independent subagent to inspect the complete diff, rerun focused direct/fallback/failure probes, and report findings without editing.
- [ ] Resolve any verified findings, rerun affected gates, delete this completed plan, and report the uncommitted diff without committing or pushing.
