---
schema_version: '1.1'
id: 'research-pe7k2m-plan-execution-efficiency'
title: 'Plan-Execution Efficiency: Measured Costs and Ranked Remedies'
description: 'Issue #133 findings: measured per-worker bootstrap, gate lane runtimes, and the new-family declaration surface from the 2026-08-06/07 github-workflow execution, with an adopt/defer/reject recommendation per candidate remedy.'
doc_type: 'research'
status: 'active'
created: '2026-08-07'
updated: '2026-08-07'
reviewed: null
owner: 'project-standards'
consumer: 'agent'
tags:
  - 'plan-execution'
  - 'process-efficiency'
  - 'verification-gate'
  - 'worktree-bootstrap'
aliases:
  - 'EV-133'
related:
  - 'docs/plans/2026-08-06-github-workflow-package-plan.md'
  - 'docs/reference/session-export-gh-workflows-implementation.md'
  - 'docs/handoff/conventions.md'
source: []
confidence: 'high'
visibility: 'internal'
license: null
---

# Plan-Execution Efficiency: Measured Costs and Ranked Remedies

Findings for issue #133. The 2026-08-06/07 execution of the `github-workflow` package plan (23 tasks, ~5 hours wall clock) was recorded as having three dominant time sinks. This report replaces the session's estimates with measurements taken on 2026-08-07 at `d4d83bcc`, and ranks the candidate remedies against what the measurements actually show.

The headline correction: **the per-worker environment bootstrap is not a time sink.** It costs seconds, not minutes. The remedy the issue proposed for it — seeding environments from the primary checkout — is rejected here in favour of a cheaper change that addresses the cost that is really there.

## Measurement method

- Bootstrap: `git worktree add --detach` into `~/.cache/`, then the full sequence a worker runs before any gate. Caches (`~/.cache/uv` 42 GB, `~/.npm` 8.5 GB) warm, matching a real worker on this machine. Result verified usable: `pytest 9.0.3` runs from the new `.venv`, and `build/wheel-runtime` is a complete extraction.
- Gate: one full `scripts/verify.sh` default run in that worktree, timed end to end.
- Declaration surface: `git grep` for the `github-workflow` family id across tracked files, excluding the family's own tree, generated artifacts, and documentation; each hit classified as hand-maintained or derived.

## Sink 1 — per-worker environment bootstrap: not real

| Step                   | Measured (under gate contention) |
| ---------------------- | -------------------------------- |
| `git worktree add`     | 1.6 s                            |
| `uv sync --all-groups` | 6.6 s                            |
| `npm ci`               | 7.5 s                            |
| `uv build --wheel`     | 3.4 s                            |
| wheel extract          | 1.0 s                            |
| **Total**              | **20.5 s**                       |

An uncontended run of the same sequence, including `make go-tools`, completed in ~3 s of measured wall time. `uv` populates `.venv` by copy-on-write reflink from the warm cache on this btrfs `/home`; `npm ci` reported `added 87 packages … in 575ms`. No bytes are copied, so a "fresh" 60-package environment materializes essentially for free.

The session export's "roughly 15 workers × 3–8 minutes of setup" (line 977) is an estimate written during the session, not a measurement. The real cost of those minutes was **agent round-trips**: each bootstrap command is a separate inference turn, and workers re-derived the procedure from the `verify.sh` preflight failure message rather than being handed it. Five turns at typical latency is the observed 3–8 minutes; the machine contributes 20 seconds of it.

## Sink 2 — gate runtimes

Full default `scripts/verify.sh`, one run:

| Lane             | Wall time | Notes                                          |
| ---------------- | --------- | ---------------------------------------------- |
| statics          | 5:22      | ran concurrently                               |
| ordinary         | 10:24     | ran concurrently, `-n` xdist                   |
| compatibility    | **17:09** | ran concurrently; **whole-gate critical path** |
| performance      | 0:32      | serial tail                                    |
| coverage combine | 0:00      | serial tail                                    |
| coverage report  | 0:03      | serial tail                                    |
| **TOTAL**        | **17:45** | `user` 178:39, `sys` 10:40                     |

Two corrections to the issue's figures. The gate is **17:45, not ~13 minutes**, and the compatibility matrix is **17:09, not ~10**. The `user`-to-`real` ratio of ~10× confirms the concurrent structure is already extracting most available parallelism.

The consequential finding is that **compatibility alone exceeds the entire rest of the gate**. It is not one lane among several; it is the critical path, and every other lane finishes inside its shadow. Any proposal that shortens statics or ordinary — including a lane-selection flag — buys nothing at all while compatibility runs. Gate wall clock is a compatibility-matrix problem exclusively.

## Sink 3 — new-family declaration surface

The issue listed eight sites. Measurement finds **nine hand-maintained collections**, and two of the issue's eight are already derived from a single authority and needed no edit for their own sake:

- `tests/package_compatibility/test_performance.py` derives from `catalog_default_ids()`.
- `tests/package_contract/test_current_catalog_activation.py` iterates `repository.families`.

The genuine hand-maintained sites, all literal and greppable:

| # | File | Symbol / role |
| --- | --- | --- |
| 1 | `catalogs/5.toml` | catalog entry |
| 2 | `.standards/config.toml` | self-hosting selection (seam canary) |
| 3 | `tests/package_compatibility/matrix.py` | `_MINIMAL_PACKAGE_CONFIG` |
| 4 | `tests/test_standards_composition.py` | `_CATALOG_NATIVE_FAMILIES` |
| 5 | `tests/control_plane/test_command_resolution.py` | `_SEAM_FAMILIES` frozen oracle |
| 6 | `tests/mcp_services/test_providers.py` | `AUTHORITATIVE_INPUT_OWNER` census |
| 7 | `src/project_standards/control_plane/provider_inputs.py` | dispatch branch + artifact list |
| 8 | `tests/test_repository_hygiene.py` | executable allowlist (payload + delivered) |
| 9 | `tests/package_contract/test_release_consistency.py`, `tests/agent_handoff/test_selected_routing.py` | shallow corpus; managed-markdown owner set |

Each was discovered only by running the previous layer's gate, costing eight serial worker dispatches. Because every site is a literal collection keyed by family id, an enumerating check can predict all nine in one pass without altering any gate's enforcement.

This is the dominant sink. Each cascade iteration paid a dispatch, a bootstrap, and a partial gate run — roughly 2–3 hours of the session's five.

## Ranked recommendations

| Ref | Recommendation | Disposition | Follow-up |
| --- | --- | --- | --- |
| R1 | New-family integration preflight (enumerating) | Adopt | #134 |
| R2 | Single-command worktree bootstrap | Adopt (revised) | #135 |
| R3 | Candidate-wheel staleness stamp | Adopt | #136 |
| R4 | Documented surface→suite verification map | Adopt (guidance) | #137 |
| R5 | Seeding `.venv` / `node_modules` from the checkout | Reject | — |
| R6 | Deriving declaration sites from one authority | Reject as primary | — |
| R7 | `verify.sh` lane-selection flag | Defer | — |

### R1 — New-family integration preflight (enumerating): **Adopt** (#134)

A read-only command taking a family id and reporting which of the nine sites do not mention it. It predicts the gates; it does not replace them. All nine layers keep their independent fail-closed enforcement, satisfying the issue's constraint that each "caught a real omission and must keep failing loudly". Highest leverage: it collapses the eight-dispatch cascade into one authored checklist at task-claim time.

### R2 — Single-command worktree bootstrap: **Adopt**, revised from the issue's proposal (#135)

`scripts/bootstrap-worktree.sh` running the five steps, referenced from the execute-plan worker brief. This targets the real cost — five agent turns — rather than the 20 seconds of machine time. It also removes the re-derivation step, since workers currently reconstruct the sequence from a failure message.

### R3 — Candidate-wheel staleness stamp: **Adopt** (#136)

`scripts/verify.sh` preflight checks that `build/wheel-runtime` _exists_, never that it is current. Hash `src/**` plus the payload projection into a stamp written beside the extraction; on mismatch, rebuild or fail with the actual reason. Small change; converts a confusing `CP-RESOLUTION: unavailable` into an actionable message. Value is diagnostic accuracy more than wall clock.

### R4 — Documented surface→suite verification map: **Adopt** as guidance (#137)

Destination: `docs/handoff/conventions.md`. Records which changed surfaces are fully covered by the five fast `standards …` validators and which genuinely require the wheel-runtime flow or the full gate. The payload/catalog/digest case is already established practice and should be written down.

### R5 — Seeding `.venv` / `node_modules` from the primary checkout: **Reject**

Saves ~15 seconds and introduces cross-worktree coupling, base-commit staleness checks, and absolute-path fragility in `.venv`. The measurement removes its entire justification.

### R6 — Deriving declaration sites from one authority: **Reject as primary** (revisit narrowly)

The redundancy across nine independently-enforced layers is what caught the omissions. Collapsing them into a shared root trades the property the issue's constraints protect. Sites that are pure restatements of the catalog entry could be derived individually later; that is a separate, narrower question than this issue.

### R7 — `verify.sh` lane-selection flag: **Defer**

Compatibility is the critical path at 17:09; skipping any other lane saves nothing measurable, and skipping compatibility is precisely the correctness risk the constraints forbid. Revisit only as part of shortening the compatibility matrix itself, which is the one change that would move gate wall clock.

## Guidance destinations

| Item                                 | Owning document                        |
| ------------------------------------ | -------------------------------------- |
| Family declaration-site checklist    | Standard Bundle Authoring package docs |
| Surface→suite verification map (R4)  | `docs/handoff/conventions.md`          |
| Worktree bootstrap + wheel staleness | execute-plan worker brief guidance     |

## Incidental findings (outside issue scope)

Both surfaced from the gate run and are recorded here as evidence; neither belongs to #133.

1. **`testing` HEAD is red on markdownlint.** 53 errors in 21 files, all under `.agents/skills/go-*/`, introduced by `d4d83bcc`. The vendored Go skill bundle landed without linter exclusions in `.markdownlint-cli2.jsonc`, matching the established pattern that byte-locked vendored copies receive their exclusions in the landing commit.
2. **Three failures in `tests/mcp_services/test_providers.py` under the parallel ordinary lane**: `test_cooperative_shutdown_is_drained_instead_of_escalated`, `test_slow_provider_returns_bounded_diagnostic_and_worker_is_reaped`, and `test_composite_dispatch_input_matches_authoritative_direct_dispatch`. The third passes in isolation in the primary checkout (87.98 s), so all three are load- or ordering-sensitive rather than a HEAD regression. The third asserts a value mismatch rather than timing out and warrants a closer look.
