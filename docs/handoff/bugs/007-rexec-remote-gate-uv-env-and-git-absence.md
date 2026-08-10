---
bug_id: '007'
date: '2026-08-09'
title: 'remote gate blocked by a redirected uv environment, and .git absence misreports as ledger corruption'
services: '[rexec, tests, ledger, tooling]'
status: 'fixed'
---

# 007 — Remote gate blocked by a redirected uv environment

**Status:** fixed in `976d3715`. The gate's statics lane now runs on the worker. Its three pytest lanes still cannot, for the independent and unfixed reason in §Second cause; that is issue #167 and remote-execution#2.

## Symptom

`rexec -- scripts/verify.sh` — the workload `CLAUDE.md` named as the reason to use a remote worker — could not reach its first lane. It failed in preflight naming a path that looks local:

```text
verify: missing /…/worktree/.venv/bin/ruff — run: uv sync --all-groups
```

The advertised remedy does not repair it. Running `uv sync --all-groups` on the worker exits `0` and leaves `.venv` absent on every retry. Meanwhile `rexec doctor` reported `ready` and `rexec setup --check` reported `converged`.

## Cause

`.rexec.toml` set `UV_PROJECT_ENVIRONMENT = "{remote_cache}/python-env"`, copied from rexec's starter config together with its shipped rationale.

`scripts/verify.sh` resolves its entire toolchain through the literal path `$REPO_ROOT/.venv/bin`, deliberately: its header records that concurrent `uv run` invocations contend on the uv cache, so the gate invokes resolved binaries directly.

The redirect means `uv sync` never creates that path. Because `uv sync` itself honours the redirect, the error's own remedy re-populates the cache path instead.

The rationale that justified the setting was redundant on both clauses. `.venv/` is already a built-in rsync exclude, and transfers run `--delete` without `--delete-excluded`, so an excluded path is invisible to the deletion pass.

A worktree-local remote `.venv` therefore survives synchronization with the key unset, verified by planting a marker under it and re-syncing. The setting's only real benefit is surviving `rexec clean`.

Filed upstream as remote-execution#3.

## Second cause

With `.venv` and `node_modules` bootstrapped, statics passed and all three pytest lanes still failed at collection:

```text
LedgerError: consumer outcome agent-handoff contains an unused or disconnected amendment
```

That message is misleading. `.git` is never mirrored — a mandatory rexec exclusion for every checkout.

`_historical_consumer_tables` (`tests/issue_regressions/ledger.py:591`) runs `git log --follow` and, on non-zero exit, **falls back to seeding history from the current rows**. The seed then equals the present state, so the amendment chain starts at the current digest, matches nothing, and every amendment is reported unused.

This also corrects the premise on #167, which attributed the blocker to a git *worktree*'s pointer `.git`. Reproduced from the ordinary `testing` checkout, so no worktree-side remedy applies.

## Fix

`976d3715` removed the `[env]` key and recorded the prohibition in `.rexec.toml` itself. `5cfdfe4b` corrected `CLAUDE.md` to state what actually offloads.

The worker also needs a one-time `rexec --shell 'uv sync --all-groups'` and `rexec --shell 'npm ci'`: `.venv/` and `node_modules/` are excludes that `rexec setup` does not create. Both survive synchronization but not `rexec clean`, which silently re-arms the failure. Filed upstream as remote-execution#4.

## Lesson

- A `LedgerError` naming amendment integrity may mean the gitdir is absent. Check `git rev-parse` first; the fallback converts missing history into apparent corruption.
- A path that substitutes *current* data for *missing historical* data does not degrade gracefully; it manufactures a confident wrong answer under another error's name.
- `rexec doctor` reporting `ready` says the host baseline converged. It makes no claim that this project can run there.
- Excluded directories are also protected from deletion, because sync omits `--delete-excluded`. That makes a manual remote bootstrap look permanent until `rexec clean`.
- When a tool's error text names a remedy, verify the remedy acts on the same machine the failure is on. Both messages here named local fixes for remote absences.
- Do not copy `UV_PROJECT_ENVIRONMENT` from the rexec starter config into any repository whose scripts call `.venv/bin/<tool>` by path.
