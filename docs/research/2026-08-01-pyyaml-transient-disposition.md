---
schema_version: '1.1'
id: 'research-w8fn3k-pyyaml-transient-disposition'
title: 'PyYAML Transient Import Failure Disposition'
description: 'EV-003: isolated installation matrix, versions, integrity observations, and the accepted disposition for issue #84 — the transient yaml.scanner import failure is the launch-overlaps-reinstall class of uv tool install --force, not a repository defect.'
doc_type: 'research'
status: 'active'
created: '2026-08-04'
updated: '2026-08-04'
reviewed: null
owner: 'project-standards'
consumer: 'agent'
tags:
  - 'issue-disposition'
  - 'installation'
  - 'verification-evidence'
aliases:
  - 'EV-003'
related:
  - 'docs/plans/2026-08-01-open-issue-resolution-program-plan.md'
source: []
confidence: 'high'
visibility: 'internal'
license: null
---

# PyYAML Transient Import Failure Disposition

EV-003 for plan `2026-08-01/open-issue-resolution-program` task T23 (brownfield-behavior, REQ-084, TC-T23-001). Issue #84: `reconcile --json` transiently crashed with `ModuleNotFoundError: No module named 'yaml.scanner'` at exact `v5.11.0`, with `yaml/scanner.py` present on disk afterward.

## Accepted disposition

**Not a repository-owned defect.** The reproduced cause class is uv's non-atomic replacement of the tool virtual environment during `uv tool install --force` while a CLI process launches or imports. No fix is implemented; the evidence-backed disposition below is retained. Any repository-side mitigation framed as "catch ImportError at the entry point" would miss real members of this class (see failure shapes).

## Isolated matrix and versions

Executed 2026-08-04 in isolated `UV_TOOL_DIR`/`UV_TOOL_BIN_DIR` environments (no checkout on `sys.path`, `PYTHONPATH` unset): exact `v5.11.0` (`ab75635`) and `v5.14.0` (`b4be9d2`), uv 0.11.6, uv-managed CPython 3.14.4, PyYAML 6.0.3, Fedora 44. Consumer fixture: `init --catalog 5` plus markdown-tooling, python-tooling, agent-handoff, and adr enabled (60-target plan, 32 YAML-bearing targets). Every frozen count was met exactly:

| Lane | Result |
| --- | --- |
| Fresh installs (8 × each version) | 16/16 clean, integrity green |
| Repeated paired previews (25 human+JSON pairs × each version) | 100/100 invocations clean |
| Concurrent `--force` reinstall vs launch, copy link-mode | 600/600 launches failed |
| Concurrent `--force` reinstall vs launch, hardlink link-mode | 400/400 launches failed |
| Integrity (`yaml/scanner.py` present + importable after settle) | 35/36; one torn-venv reading below |

Transience proof: one immediate re-run of a failing invocation, no reinstall in flight, returned the expected drift exit with clean stderr — matching the issue's "a later `--version` succeeded".

## Failure shapes observed (1,000 overlap hits)

- Submodule missing with parent package present — the `yaml.scanner` shape (198 total).
- Top-level package missing entirely; console script itself absent (`rc=127`).
- Hardlink mode additionally produced: misleading "circular import" `ImportError`s (`jsonschema`, `referencing`), `AttributeError: module 'idna' has no attribute 'IDNAError'`, and `FileNotFoundError` on single files inside present packages (`pydantic/version.py`, a `jsonschema_specifications` schema) — the closest structural analogue to the reported symptom.
- Zero of 1,000 hits mention `yaml` literally: a full-venv teardown kills the process at its earliest import, before PyYAML loads. Reproducing the literal string would need a PyYAML-only replacement window; the class is established without it.

## Residual bounds

- The reporter's interpreter was CPython 3.14.6; the matrix ran uv-selected 3.14.4. The mechanism is interpreter-independent (venv file replacement), but 3.14.6 was not separately exercised.
- One hardlink-mode integrity check found the tool venv still torn (no `bin/python`) after a reinstall loop exited; it self-healed on the next reinstall. The harness did not retain that reinstall's exit code, so whether the final overlapped install itself failed is unresolved. Sequential installs never exhibited this (16/16 clean).
- Whether a concurrent uv cache GC can produce the same window was not exercised.

## Safe consumer guidance

Do not invoke `project-standards` (including paired human/JSON previews) while a `uv tool install --force` of it is in flight; on a transient import error of any shape, re-run the command once before diagnosing. Raw lane logs and hit files are retained with the execution evidence for this task; harness scripts are re-runnable.
