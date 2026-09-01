---
schema_version: '1.1'
id: 'research-9bxmq3-release-train-wall-clock-options'
title: 'Release-Train Wall-Clock Options'
description: 'Measured per-lane cost of the 106-minute --full battery and the 2-hour hosted check job, with each candidate lever costed against the release gate claim it would weaken.'
doc_type: 'research'
status: 'active'
created: '2026-09-01'
updated: '2026-09-01'
reviewed: null
owner: 'project-standards'
consumer: 'agent'
tags:
  - release-gate
  - wall-clock
  - ci
  - pytest-xdist
  - rexec
aliases: []
related:
  - 'docs/research/2026-07-31-release-gate-wall-clock-spike.md'
confidence: 'high'
---

# Release-Train Wall-Clock Options

Research for issue #207. Recommendations only: nothing in `scripts/verify.sh`, `.github/workflows/**`, or `meta/versioning.md` was changed by this work. Every duration below is a recorded artifact, not a re-measurement — no lane was rerun for this report.

## 1. Measured breakdown

### 1a. Local `--full` battery (v5.27.0, worker CT 117, via `rexec`)

| Lane | Exit | Seconds | Share | Parallelism used |
| --- | --- | --- | --- | --- |
| statics | 0 | 77 | 1% | 1 process, 6 tools serially |
| ordinary | 1 | 3031 | 48% | **1 process** (`lane_ordinary_serial`, `scripts/verify.sh:312`) |
| compatibility | 0 | 3178 | 50% | **4** (`FULL_COMPAT_WORKERS`, `:70`, `:393`; set it with the env var `VERIFY_FULL_COMPAT_WORKERS`, and through rexec as `rexec --env VERIFY_FULL_COMPAT_WORKERS=16 -- scripts/verify.sh --full`, because rexec forwards nothing from the local environment) |
| performance | 0 | 66 | 1% | 1, deliberately alone (timing assertions) |
| coverage-report | 0 | 2 | ~0% | 1 |
| **total** |  | **6354** | **106 min** |  |

Battery 2 over the same tree plus a two-line test fix: 81 / 3035 / 3190 / 66 / 3 = 6375 s. The two batteries differ by 0.3%, which makes the lane figures reproducible rather than incidental.

### 1b. Worker capacity (measured 2026-09-01, `rexec --shell`)

`nproc` = **40**; `MemTotal` = 64 GiB; `/mnt/pytesttmp` = 16 GiB; load average 3.08 at probe time.

**The battery never uses more than 4 of 40 cores.** For 3031 s it uses one. Capacity is not the constraint; the mode is. Lever 5 ("would more workers help?") is answered by that line alone, and the `rexec` workspace lock does not constrain a battery that is already running — it serializes invocations, and only one battery is ever in flight. It does constrain the _start_: a concurrently running leg holding the workspace lock delays the launch (observed 2026-09-01, about 25 minutes), so check `rexec status` before launching one.

### 1c. Cost-driver attribution

| Lane | Driver | Evidence |
| --- | --- | --- |
| ordinary (3031 s) | **Process count, not test content.** Identical 5,405-test selection to the fast lane; `--full` drops `-n 16 --dist load` (`:304` vs `:312`) and keeps the trace coverage core instead of `sysmon` (`:225-233`). The 2026-07-31 spike measured the same selection at 259 s solo under `-n 16` on the 21-core workstation. | `scripts/verify.sh:304,312,225-233`; `docs/research/2026-07-31-release-gate-wall-clock-spike.md` |
| compatibility (3178 s) | **Rows × per-row lifecycle, at `-n 4`.** Each parametrized row runs ≥4 full `apply_reconciliation` passes, two `_assert_fixed_point` calls (each plan + apply + two whole-tree snapshots), and two `_assert_declared_validators` calls, each spawning one provider **subprocess** per VALIDATE provider per package. Rows are combinatorial: pairs over the catalog defaults, legacy pairs, and one partial-migration row per default. | `tests/package_compatibility/matrix.py:520-720`; `test_catalog_matrix.py:45-63` |

**Correction to the issue's stated driver.** The issue says the compatibility lane "installs wheels per case". It does not: `wheel_payload_distribution` and `source_payload_distribution` are `scope="session"` fixtures and the wheel is taken pre-built from `PROJECT_STANDARDS_COMPATIBILITY_WHEEL` (`tests/package_compatibility/conftest.py:33-60`), so one extraction happens per xdist worker, not per row. This matters for lever selection: wheel/environment caching has nothing left to win, while worker count scales the real cost (subprocess spawns and tree materialization) almost directly.

### 1d. Hosted `check` job (run 33467065452, green, 2026-09-01)

| Step | Duration |
| --- | --- |
| checkout → coverage erase (15 steps, incl. basedpyright 26 s) | 51 s |
| Ordinary tests with coverage (`-n 4`) | 28 m 28 s |
| **Compatibility matrix (`-n 4`)** | **1 h 35 m 16 s (75%)** |
| Performance gates | 1 m 46 s |
| Coverage report + pip-audit | 6 s |
| **job total** | **2 h 06 m 27 s** |

**Correction to the issue comment.** The 32 m 37 s figure came from a run that _failed_ at the ordinary step and therefore never reached the compatibility matrix; `1957.85s` is that pytest step's own duration. A green `check` is ~4× that. The last three green runs measured 2 h 06, 2 h 05, 1 h 58 (runs 33467065452, 33466902333, 33459338189). The PR critical path is therefore ~2 hours, and the compatibility matrix — not the ordinary suite — dominates it.

## 2. Lever 1 verdict: has the serial cross-check ever earned its cost?

**Search method (so an absence is interpretable).** The fast gate was adopted at v5.13.0 (`35a79560`, 2026-07-31); 14 trains have run `--full` pre-tag since (v5.14.0 … v5.27.0). Three sources were searched: (a) `grep -rn "VERIFY_FULL_EXIT\|verify.sh --full" .workflow/*.md .workflow/lessons/*.md`, which returns every recorded battery launch and outcome; (b) `docs/handoff/sessions/2026-07.md`, `2026-08.md` and `docs/handoff/conventions.md`; (c) `git log --grep` over `serial`, `isolation`, `order-dependen`, `flake` since `35a79560`.

**Finding: no recorded case in which serial execution surfaced a defect the parallel lane missed.** The two recorded `--full` reds since adoption both have non-parallelism causes:

| Battery | Red | Cause | Would `-n 16` have caught it? |
| --- | --- | --- | --- |
| v5.27.0 #1 | `test_git_mode_policy__…` | Reads the Git **index**; two payload files were committed with mode 100755 outside the inventory. | Yes — identical, the corpus is the index, not the process layout. |
| 2026-08-27 train | 7 reds | Worker `__pycache__`, stale test pins, skill mirror. All reproduced on single-file rerun. | Yes — all deterministic. |

**Interpretive limit:** this is a written record, not instrumentation. A divergence noticed and quietly fixed inside a session would not appear. The record is nonetheless the practice of these trains (every red lane is written into the orchestration state), so the absence is meaningful rather than empty.

**But the lane carries a second claim.** `--full` also varies the coverage core (trace, not `sysmon`) and is the configuration the coverage baseline was established under (`scripts/verify.sh:34-40`). Retiring the serial ordinary lane discards _two_ claims — isolation and coverage-core equivalence — not one. That is why the recommendation below narrows it rather than deleting it.

## 3. Levers, costed

Minutes saved are per train, over the 106-minute battery unless the row says CI. Compatibility scaling is extrapolated from the only two measured points for this lane (workstation: `-n 4` 605 s → `-n 8` 405 s, i.e. 1.49× for 2× workers), applied twice from the worker's `-n 4` = 3178 s.

| # | Lever | Saves | Size | Risk to the gate's claim | Implement now? |
| --- | --- | --- | --- | --- | --- |
| A | `VERIFY_FULL_COMPAT_WORKERS=16` on the 40-core worker | **25–35 min** | S (env var, no file edit) | **None.** Compatibility is parallel in both modes; no documented claim rests on the literal 4, which is workstation-era tuning for a 21-core box shared with interactive work. Memory headroom 64 GiB / 16 workers. | **Yes** |
| B | Sequence the battery after the activation commit; prove a scoped correction with a targeted remote run plus a lane-verdict record instead of a second battery | **up to 106 min** in the case that occurred | S (runbook text) | Low, _provided_ the re-run's provenance is recorded (see §4). Bounded by the index-sensitive lesson: index/history lanes are honest only after the commit. | Yes, as runbook wording |
| C | Split hosted `check` into parallel jobs and shard the compatibility matrix ~4 ways | **~90 min of PR critical path** (2 h 06 → ~30 min) | M (workflow edit) | **None** — same tests, same selection; sharding changes only which runner executes a row. Costs more billed minutes, not fewer. | Recommend (owner decision; workflow edit is out of this leg's scope) |
| D | `--lane <name>` selector | 60–106 min on any scoped correction | M (script + provenance record) | Medium: a lane-scoped re-run must not be readable as a whole-battery green. Needs §4's record to stay safe. | Recommend |
| E | Hash-keyed verdict reuse | Up to a full battery when only docs moved | L | **Highest.** This is the only lever that can produce a wrong green. Keep the digest whole-tree; see §4. | No — design first |
| F | Retire the serial ordinary lane for a randomized-order probe over shared-fixture suites | ~45 min | M | Medium: discards the coverage-core cross-check unless a separate trace-core coverage run replaces it. | No — adopt A+C first, revisit |
| G | `paths-ignore` on `check.yml` | **~0 min** (see §5) | S | Low for the proven set, but the set is four files. | Optional, documentation value only |

With A alone the battery projects to ~77 min (77 + 3031 + ~1430 + 66 + 2). With A and B, a train that needs one scoped correction costs one 77-minute battery plus a targeted run instead of 212 minutes.

## 4. Keeping the claim intact

The claim to preserve: _a given tag was proven by a coherent set of lane verdicts over the exact tree being tagged, statable from recorded artifacts alone._ Today that holds because one `--full` invocation writes all five `status<TAB>seconds` files over one tree. Levers B, D and E all break the "one invocation" part, so they need the tree identity written into the record instead:

- **Verdict record (per lane):** `lane`, `mode`, `worker_counts`, `exit`, `seconds`, `started_at`, and `tree_digest`.
- **`tree_digest` (state it exactly):** SHA-256 over the `git ls-files -s` output (path, mode, blob OID for every tracked file) concatenated with `path\0sha256(content)` for every dirty or untracked file the gate can see. It covers modes and untracked files because both have already produced a red here (`a8a30fd7`; the release-prep dirty set).
- **Input set:** whole tree, deliberately — **not** per-lane input sets. The 2026-07-31 spike already rejected diff-scoped selection for this repository (catalog-wide couplings: dogfood example lanes, §9 byte-locks, projection fan-out). Lever E is safe only in the "nothing changed at all" form; the moment it narrows to per-lane input sets it re-opens the rejected class.
- **Runbook citation:** the release step asserts five verdicts exist, all `exit=0`, all carrying the _same_ `tree_digest`, and that the digest equals the digest of the tree being tagged. A lane-scoped re-run is admissible exactly when its record's digest matches the others'; otherwise the battery is incoherent and the release stops. Fail-closed is preserved because a missing or mismatched record is a stop, not a skip.

## 5. CI trigger audit

| Workflow | Events | Paths filter |
| --- | --- | --- |
| `check.yml` | `pull_request` (all branches), `push` → `main` | **none** |
| `coherence.yml` | `pull_request`, `push` → `main` | none |
| `format.yml` | `pull_request`, `push` → `main`, `workflow_call` | none (caller narrows via `globs` input) |
| `go.yml` | `pull_request`, `push` → `main` | yes — `**/*.go`, `go.mod`, `go.sum`, `.golangci.yml`, `Makefile`, the workflow itself, 3 build scripts, 2 committed binaries |
| `lint-markdown.yml` | `pull_request`, `push` → `main`, `workflow_call` | yes — `**/*.md`, `.markdownlint.json`, `.markdownlint-cli2.jsonc`, the workflow itself |
| `validate-markdown-frontmatter.yml` | `workflow_call` only | n/a |
| `validate-specs.yml` | `pull_request`, `push` → `main`, `workflow_call` | yes — `**/*.md`, `src/**`, `.standards/config.toml`, `pyproject.toml` |
| `validate-standards-graph.yml` | `pull_request`, `push` → `main`, `testing` | none |
| `validate-standards.yml` | `pull_request`, `push` → `main` | none |

`check.yml` is the only unfiltered workflow whose cost is material (2 h vs ≤46 s for the others), and it is fully consumer-owned — absent from `.standards/lock.toml`, so no payload cut is needed to change it. Both `main` and `testing` are unprotected, so a skipped-vs-passing required-context trap does not exist.

### What `check.yml` legitimately needs to run for

Everything the pytest suite reads. Two classes make the answer nearly "everything":

1. **Live-file readers.** Confirmed live reads of the repository's own files include `README.md`, `AGENTS.md` and `CLAUDE.md` (`tests/test_no_stale_prettier_claims.py:8-18`), `docs/handoff/specs-plans.md` and a retired plan under `docs/plans/` (`tests/test_documentation_lifecycle.py:9,14`), `docs/plans/current-release.md` and `docs/plans/{completed,staged}.md` (`tests/package_contract/test_release_consistency.py`), `docs/reference/control-plane-diagnostics.md`, one file under `docs/research/` (`tests/mcp_server/integration/test_server.py:101`), plus `standards/**`, `catalogs/**`, `src/**`, `scripts/**`, `.standards/**`, `.agents/**`, `.claude/**`, `.codex/**`, `.github/**`, `pyproject.toml`, `Makefile` and `.pre-commit-hooks.yaml`.
2. **Index-corpus readers.** `tests/test_repository_hygiene.py:142` compares a curated inventory against `git ls-files -s` — **every tracked path, by mode**. No inclusion list shaped like `src/**` can select the change that broke it (`a8a30fd7` added payload files with mode 100755).

**Audit method and its two error directions.** Each top-level path was counted with a literal-substring grep over `tests/**/*.py`, then every non-zero result was re-checked for a `_ROOT`-anchored live read. The raw counts **over-count** badly — most hits are synthetic-consumer strings such as `repo / "AGENTS.md"` inside fixture repositories, which is why the issue comment's figures (34 / 25 / 26) overstate the live surface — and they **under-count** dynamically composed paths and the index-corpus readers above. Only paths with a zero raw count across both `tests/` and `src/` are treated as proven unread.

### Proposed filter

```yaml
# Literal files only, deliberately: a paths-ignore over a DIRECTORY also matches
# newly added files there, and an added file is exactly what the index-corpus
# tests exist to catch (a8a30fd7 added mode-100755 payload files).
paths-ignore:
  - 'ROADMAP.md'
  - '.rexec.toml'
  - '.golangci.yml'
  - 'go.sum'
```

`.golangci.yml` and `go.sum` remain gated by `go.yml`, which lists both. `ROADMAP.md` and `.rexec.toml` have no gate other than `lint-markdown.yml` / Prettier, which is correct for their content.

**False-negative risk, stated:** a _mode_ change (not a content change) on one of these four paths, in a PR touching nothing else, would skip the index-corpus hygiene test. Content edits cannot fail it.

**Measured value: approximately zero.** No recent PR has touched only those four paths. The honest result of this audit is that a `paths-ignore` is not the CI lever — lever C is. Recommending the filter anyway is defensible only as documentation of _why_ CI runs everything.

## 6. Recommendation

- **Cheapest safe adoption today:** lever A. Run the pre-tag battery as `rexec -- env VERIFY_FULL_COMPAT_WORKERS=16 scripts/verify.sh --full`. No file changes, no claim weakened, ~30 minutes off every train. If it proves out over a train or two, the owner can decide whether the default at `scripts/verify.sh:70` should move (a code change this report does not make).
- **Right long-term, even though it costs more up front:** lever D plus the §4 verdict record, then lever C for the hosted path. The record is the piece with lasting value: it converts "the gate ran" into "these five verdicts cover this exact tree", which is what makes any future reuse or lane-scoped re-run safe. Lever E should not be built until that record exists and has been exercised.
- **Do not adopt yet:** lever F. The serial ordinary lane has never been shown to earn its 45 minutes, but it carries the coverage-core cross-check as well, and A+C recover more time without giving up anything.

**Adopted 2026-09-01 (owner decision, issue #236 C4) — in the narrowed form this section asks for.** The lane is replaced rather than retired: `--full` now runs the identical selection at `-n 16 --dist load` under the default trace core, so the coverage-core cross-check against the `sysmon` fast gate survives intact and only the isolation claim of §2 — the one this report could find no evidence for — is given up. `--full` gains a `coverage-combine` lane, which the previous single-process data file made unnecessary.
