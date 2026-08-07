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

Two full default `scripts/verify.sh` runs, both in a fully bootstrapped detached worktree. Run A was taken while a separate bootstrap measurement ran concurrently on the same machine; run B had the machine to itself. **Run B is the reference; run A is retained because the spread between them is itself a finding.**

| Lane             | Run B (clean) | Run A (contended) |
| ---------------- | ------------- | ----------------- |
| statics          | 3:44          | 5:22              |
| ordinary         | 7:55          | 10:24             |
| compatibility    | **11:53**     | **17:09**         |
| performance      | 0:23          | 0:32              |
| coverage combine | 0:00          | 0:00              |
| coverage report  | 0:01          | 0:03              |
| **TOTAL**        | **12:17**     | **17:45**         |

The issue's figures were close to right: the gate is ~12 minutes against its recorded ~13, and the compatibility matrix ~12 against its recorded ~10. No correction to those estimates is warranted. Run A's `user`-to-`real` ratio of ~10× confirms the concurrent structure already extracts most available parallelism.

Two findings do follow from the measurement:

- **Compatibility is the critical path.** At 11:53 against a 12:17 total, it alone accounts for essentially the whole gate; every other lane finishes inside its shadow. Any proposal that shortens statics or ordinary — including a lane-selection flag — buys nothing while compatibility runs. Gate wall clock is a compatibility-matrix problem exclusively.
- **The gate is highly sensitive to competing load.** One concurrent bootstrap inflated it by 45%. Timings quoted from a session where other work was in flight should be treated as upper bounds, and the gate should not be timed or judged against a busy machine.

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

Compatibility is the critical path at 11:53 of a 12:17 gate; skipping any other lane saves nothing measurable, and skipping compatibility is precisely the correctness risk the constraints forbid. Revisit only as part of shortening the compatibility matrix itself, which is the one change that would move gate wall clock.

## Guidance destinations

| Item                                 | Owning document                        |
| ------------------------------------ | -------------------------------------- |
| Family declaration-site checklist    | Standard Bundle Authoring package docs |
| Surface→suite verification map (R4)  | `docs/handoff/conventions.md`          |
| Worktree bootstrap + wheel staleness | execute-plan worker brief guidance     |

## Incidental findings (outside issue scope)

Both surfaced from the gate run and are recorded here as evidence; neither belongs to #133.

1. **`testing` HEAD is red on markdownlint.** 53 errors in 21 files, all under `.agents/skills/go-*/`, introduced by `d4d83bcc`. The vendored Go skill bundle landed without linter exclusions in `.markdownlint-cli2.jsonc`, matching the established pattern that byte-locked vendored copies receive their exclusions in the landing commit.
2. **`tests/mcp_services/test_providers.py` failures under the parallel ordinary lane.** Run A (contended) failed three: `test_cooperative_shutdown_is_drained_instead_of_escalated`, `test_slow_provider_returns_bounded_diagnostic_and_worker_is_reaped`, and `test_composite_dispatch_input_matches_authoritative_direct_dispatch`. Run B (clean) failed only `test_slow_provider_…_is_reaped`; the other two did not recur, and neither reproduced in isolation. All three are load-sensitive rather than a HEAD regression, and the slow-provider reaping test is the one that fails even on an unloaded machine.

   Two reproduction attempts outside the gate failed for reasons of their own, and both are instructive.

   Running the module while concurrently editing a repository file failed `test_real_packaged_provider_validates_real_consumer_root`, which digests the live tree — that test detects **any** concurrent writer, including the operator.

   Running the ordinary lane with bare `pytest` produced nine failures and five errors across `test_markdown_frontmatter_skill.py`, `test_validate_id_zipapp.py`, and `test_adopt_dogfood.py`. The cause is **environmental, not a repository defect**: an agent-harness plugin prepends a `python3` PATH shim that refuses bare invocations, and those suites spawn scripts calling `python3`. `scripts/verify.sh` is immune because line 187 exports `PATH="$VENV_BIN:$PATH"` and `.venv/bin/python3` shadows the shim. Re-running the same suites with a venv-first PATH passes all 33.

   That is a sharper statement of why the gate script is canonical than R2 alone makes: `scripts/verify.sh` does not merely sequence commands, it **constructs the environment** — venv-first PATH, `PYTHONPATH`, `TMPDIR`, per-lane basetemps, and `COVERAGE_FILE`. Bare `pytest` with the correct `PYTHONPATH` is still not equivalent, and its failures are indistinguishable from real defects. Never diagnose against bare `pytest`; reproduce through the gate.

   Related fragility, not currently biting: `real_tree_digest`'s `_UNWATCHED_TREES` excludes `.git`, `build`, `node_modules`, and the caches, but not `.project-pipeline` or `.scratch`, both of which exist and churn in the primary checkout during plan execution.
