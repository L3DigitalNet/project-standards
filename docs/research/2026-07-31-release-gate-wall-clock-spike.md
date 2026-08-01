---
schema_version: '1.1'
id: 'research-g8t3vx-release-gate-wall-clock-spike'
title: 'Release-Gate Wall-Clock Spike'
description: 'Measured evidence for the v5.13.0 fast release gate: pytest-xdist parallelism, sysmon coverage, a 4M-inode pytest tmpfs, and a concurrent statics lane, with the read-safety fixes and equivalence proofs that make the parallel gate trustworthy.'
doc_type: 'research'
status: 'active'
created: '2026-07-31'
updated: '2026-07-31'
reviewed: null
owner: 'project-standards'
consumer: 'agent'
tags:
  - release-gate
  - pytest-xdist
  - coverage
  - sysmon
  - performance
aliases: []
related:
  - 'docs/handoff/conventions.md'
---

# Release-Gate Wall-Clock Spike

Measured 2026-07-31 on the 21-core workstation as the first work item of the v5.13.0 efficiency train. Goal: cut the release-gate verification wall-clock from the 2026-07-31 baselines — plain battery 16:22 tmpfs / 22:30 disk-backed, coverage battery 55:31 disk-backed — to a 5–8 minute gate.

## Result

The adopted gate ran fully green in **10:23 under real-usage load** (several external compute-intensive sessions active, load ~34 on 21 cores, thermal capping observed) — **5.3× faster than the 55:31 baseline in representative conditions**. Solo per-lane timings project a quiet-machine floor of **7:30–8:30**, inside the target band. The owner treats the contended numbers as representative; a follow-up TODO covers controlled-condition benchmarking to dial in `-n` values and lane concurrency.

## Adopted configuration

Three concurrent lanes, then a serial tail:

- **Ordinary lane:** `coverage run --source=project_standards -m pytest -m "not performance and not compatibility" -n 16 --dist load --max-worker-restart=0` with `COVERAGE_CORE=sysmon`. 4,191 tests; 4:19 solo, ~7:11 contended (CI serial equivalent: 26:00).
- **Compatibility lane:** `pytest -m compatibility -n 8 --dist load --max-worker-restart=0`. 133 tests; 6:45 solo, ~10:00 contended (was 10:05 at `-n 4` solo).
- **Statics lane (non-uv invocation path):** `.venv/bin/ruff format --check`, `.venv/bin/ruff check`, `.venv/bin/basedpyright`, resolved `node_modules/.bin/prettier --check . --cache` and `node_modules/.bin/markdownlint-cli2`, `.venv/bin/pip-audit` — ~2:20–3:25 total, fully hidden under the battery lanes; zero uv-cache contention by construction (no uv processes, the 2026-07-29 contention class cannot occur).
- **Serial tail:** performance lane alone (its assertions are timing-sensitive), then `coverage combine` + `coverage report`.

Environment: `PYTHONPATH` = extracted candidate wheel; `TMPDIR` + `--basetemp` on a dedicated tmpfs mounted with `nr_inodes=4194304`; `COVERAGE_FILE` pointed off-root so no coverage artifact ever appears in the repository during the run.

## Equivalence evidence (the harness is trustworthy)

- **Census parity:** 4,191 ordinary + 133 compatibility + 5 performance = 4,329, identical to the serial collection.
- **Coverage parity:** parallel+sysmon full-scale report `TOTAL 20898 1811 7728 943 90%` vs the v5.12.0 serial-trace CI reference `TOTAL 20895 1811 7728 943 90%` — misses, branches, and partials identical; the +3 statements are the lock-ordering fix shipped this train. A subset matrix additionally proved **byte-identical** reports across serial-trace, `-n 4`/`-n 8` trace, and sysmon runs.
- **sysmon core verified live in workers** (`core=SysMonitor` in every worker pid, branch coverage on, no fallback warning) on coverage 7.14.1 / Python 3.14.6.
- **Worker coverage mechanism:** `tests/conftest.py` passes the controller's serialized coverage config through xdist's `workerinput` — reaching exactly the worker interpreters. The `COVERAGE_PROCESS_START` / `patch = ["subprocess"]` / pytest-cov route was refuted with evidence: it also instruments test-spawned CLI subprocesses, inflating the report 4× with copies of the package imported from throwaway fixtures.

## Read-safety findings (all fixed)

Parallel execution exposed one defect class — **the live repository root treated as shared mutable state** — in four instances:

1. `format-frontmatter` acquired the repository lock before parsing arguments, selecting lock mode by string-sniffing; an invalid `--stdin --write` invocation took an exclusive lock on the live root and contention surfaced as `CP-BUSY` instead of the usage error (src fix, commit `97359ae`; GH-26 proof retargeted under DR-002).
2. The prettier-parity oracle created probe directories in the repository root (~every 2 s); moved to `build/prettier-probes/` — in-tree so the `**/*.md` `singleQuote` override still applies (A/B oracle proved byte-identical output).
3. The installed-wrappers wheel-source `copytree` raced transient files; ignore set widened (also ~3× faster, `node_modules` no longer copied).
4. xdist coverage workers saved `.coverage.<host>.<pid>` files into the root mid-run, racing the read-only digest proof and the `copytree`. Fixed at the root cause (`COVERAGE_FILE` off-root in the gate environment) plus defense-in-depth exclusions in both readers (commits `66c9163`, `a3358aa`).

Timing-grace tests (`test_cancelled_invocation…`, `test_cooperative_ shutdown…`) each flaked once under peak oversubscription and passed solo every time: **load-sensitive, not broken**. Operational rule: the release gate runs on a reasonably quiet machine; incidental flakes of this family under heavy load warrant a solo rerun, not a fix.

## Inode telemetry

Peak tmpfs usage: 394,356 inodes (ordinary lane alone), 768,844 (full sequential battery), ~465,000 (concurrent lanes). The default 1,048,576- inode `/tmp` is marginal for the sequential battery; the dedicated 4M-inode tmpfs leaves 5× headroom. Disk-backed `TMPDIR` (conventions §14) remains the documented fallback when no tmpfs is mounted.

## Rejected levers

- **MCP fixture file-count reduction:** not needed; primary levers met the target.
- **Frozen-venv / per-lane worktree suite parallelism:** xdist inside one environment already delivers the win; per-lane environments would duplicate setup and re-open the uv-contention class.
- **Diff-scoped test selection:** unsafe here (catalog-wide couplings: dogfood example lanes, §9 byte-locks, projection fan-out) and subsumed — the fast gate makes full lanes cheap.
- **Wheel-runtime build caching:** build+extract measures ≈1 s; no value.

## Run log

| Run | Configuration | Wall | Outcome |
| --- | --- | --- | --- |
| R1 | ordinary `-n auto`, tmpfs, no coverage | 3:24 | 3 concurrency failures → root-caused |
| R5 | sequential full gate, sysmon coverage, statics concurrent | 14:48 | compat bottleneck identified (10:05 at `-n 4`) |
| compat-n8 | compatibility alone `-n 8` | 6:45 | clean; adopted |
| R6 | concurrent lanes | 10:40 (loaded) | coverage-artifact race found |
| R7 | R6 + digest exclusion | 9:56 (loaded) | copytree race found (same artifact class) |
| R8 | R6 + `COVERAGE_FILE` off-root | **10:23 (loaded)** | **fully green — adopted** |
