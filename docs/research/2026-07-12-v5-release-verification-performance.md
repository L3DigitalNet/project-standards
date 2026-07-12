---
schema_version: '1.1'
id: v5-release-verification-performance
title: Safely Reducing Project Standards v5 Release Verification Wall Time
description: Research on reducing the v5 release gate wall time while preserving coverage, per-row source and wheel parity, test isolation, and serial release and performance proofs.
doc_type: research
status: active
created: 2026-07-12
updated: 2026-07-12
reviewed: 2026-07-12
owner: project-standards
consumer: agent
tags:
  - v5
  - release-verification
  - pytest-xdist
  - coverage
  - performance
aliases:
  - v5 release gate performance
  - parallel catalog matrix verification
  - xdist coverage release verification
related:
  - docs/superpowers/plans/2026-07-12-release-verification-performance.md
source:
  - https://pytest-xdist.readthedocs.io/en/latest/distribution.html
  - https://pytest-xdist.readthedocs.io/en/latest/how-to.html
  - https://pytest-xdist.readthedocs.io/en/latest/how-it-works.html
  - https://pytest-xdist.readthedocs.io/en/latest/changelog.html
  - https://pytest-xdist.readthedocs.io/en/stable/crash.html
  - https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/plugin.py
  - https://github.com/pytest-dev/pytest-xdist/issues/1103
  - https://github.com/pytest-dev/pytest-xdist/issues/1296
  - https://coverage.readthedocs.io/en/latest/subprocess.html
  - https://coverage.readthedocs.io/en/latest/commands/cmd_combine.html
  - https://coverage.readthedocs.io/en/latest/changes.html
  - https://docs.pytest.org/en/stable/how-to/tmp_path.html
  - https://pytest-cov.readthedocs.io/en/latest/readme.html
  - https://tox.wiki/en/latest/user_guide.html
  - https://docs.github.com/en/actions/reference/runners/github-hosted-runners
  - https://docs.github.com/en/actions/reference/security/secure-use
  - https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs
  - https://github.com/pytest-dev/pytest-xdist/security
  - https://pypi.org/project/pytest-xdist/
confidence: high
visibility: public
license: Apache-2.0
---

# Safely Reducing Project Standards v5 Release Verification Wall Time

The safe optimization boundary is the catalog-derived correctness matrix, not the entire release gate. Run that matrix across local pytest-xdist workers while keeping performance thresholds, disposable release replay, and any timing-sensitive proof serial. Preserve source/wheel parity inside each test row so the same worker compares both distributions against the same isolated consumer state.

Two corrections are required before implementing the current [release-verification performance plan](../superpowers/plans/2026-07-12-release-verification-performance.md):

1. Make **every covered phase** write parallel-suffixed coverage data, erase once before the first phase, combine once after the last covered phase, and only then report. A plain `coverage combine` ignores and rewrites an existing combined `.coverage` file; therefore, running ordinary tests into `.coverage` and later combining only `.coverage.*` files would lose ordinary-test data. [official] (<https://coverage.readthedocs.io/en/latest/commands/cmd_combine.html>)
2. Do not use xdist 3.8 `-n auto` as the release contract. In an isolated live probe, 3.8.0 used `psutil.cpu_count()` when psutil was present and otherwise `sched_getaffinity()`/`os.cpu_count()`; it did not consult Python 3.13+'s `os.process_cpu_count()` or `PYTHON_CPU_COUNT`. The repository currently has no psutil dependency, so its result is affinity-based logical capacity and can change if the dependency graph later introduces psutil. Use an explicit, benchmarked worker count or `PYTEST_XDIST_AUTO_NUM_WORKERS`, with a conservative maximum. [official] (<https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/plugin.py>) [community, project issue] (<https://github.com/pytest-dev/pytest-xdist/issues/1103>, <https://github.com/pytest-dev/pytest-xdist/issues/1296>)

## ⚠ Existing solution

> **pytest-xdist 3.8 + coverage.py 7.14 + the existing check workflow** [official] (<https://pytest-xdist.readthedocs.io/en/latest/distribution.html>) — covers the needed local process fan-out and subprocess coverage collection. The repository owns phase orchestration in [`.github/workflows/check.yml`](../../.github/workflows/check.yml) and [`scripts/run_repository_tests.py`](../../scripts/run_repository_tests.py); adding tox, Nox, or cross-job sharding would add another orchestration layer without improving the per-row source/wheel comparison.

## Summary

| Angle | Sources | Strongest finding |
| --- | --: | --- |
| Official Docs | 10 | xdist can parallelize one isolated phase, while coverage's subprocess patch and parallel data files preserve worker execution for a later combined report. |
| Best Practices | 8 | Keep source and wheel in the same row, prebuild immutable artifacts once, use per-worker/per-test namespaces, and benchmark a fixed worker cap on the actual runner. |
| Footguns | 7 | Plain `coverage combine` can erase serial coverage, and xdist session fixtures execute once per worker, multiplying wheel builds and setup cost. |
| Existing Tools | 6 | pytest-xdist, coverage.py, pytest-cov, tox/Nox, and GitHub Actions all cover pieces; the first two plus the current repository orchestration cover this use case. |
| Security | 5 | Local xdist workers are execution processes, not sandboxes; they inherit the job environment and must retain the current read-only permissions, offline build, and network-denial controls. |
| Recent Changes | 4 | xdist 3.8 added loadscope reorder control; coverage 7.14 made reporting commands implicitly combine parallel files, but explicit combine semantics still rewrite an existing base file. |

**Queries:** 44 · **Results parsed:** 180+ · **Deep reads:** 5 · **Follow-up pass:** yes

## Official Documentation

- pytest-xdist workers are separate mini pytest runners: each performs full collection, and the controller requires every worker to collect the same test IDs in the same order. Parallel acceptance must therefore compare serial and distributed collection IDs or at least exact row counts before relying on the faster gate. [official] (<https://pytest-xdist.readthedocs.io/en/latest/how-it-works.html>)
- The default `--dist load` sends pending tests to the next available worker; `loadscope` groups an entire module or class. Because the catalog matrix is concentrated in one module, `loadscope` would place most or all of the target phase on one worker and defeat the intended speedup. [official] (<https://pytest-xdist.readthedocs.io/en/latest/distribution.html>)
- `patch = subprocess` instruments Python children created through `subprocess`, `os.system`, and exec/spawn families. Coverage also requires parallel data files and a combine step, and warns that children which do not terminate cleanly may not save data. [official] (<https://coverage.readthedocs.io/en/latest/subprocess.html>)
- Since coverage.py 7.14.0, reporting commands implicitly combine pending parallel files. An explicit `coverage combine` remains useful as a visible gate step, but it must receive only suffixed inputs or use `--append`; otherwise it ignores and rewrites an existing combined file. [official] (<https://coverage.readthedocs.io/en/latest/changes.html>, <https://coverage.readthedocs.io/en/latest/commands/cmd_combine.html>)
- `tmp_path` is unique to each test invocation, and xdist exposes `worker_id` and `testrun_uid` for resources that need worker- or run-level namespacing. These are the correct primitives for retaining lifecycle isolation. [official] (<https://docs.pytest.org/en/stable/how-to/tmp_path.html>, <https://pytest-xdist.readthedocs.io/en/latest/how-to.html>)

## Best Practices

### Recommended phase topology

| Order | Phase | Execution | Coverage | Preserved proof |
| --: | --- | --- | --- | --- |
| 1 | Erase prior coverage data | serial | `coverage erase` | No stale evidence from a prior run |
| 2 | Ordinary tests excluding matrix and performance markers | serial | `coverage run --parallel-mode -m pytest ...` | Existing deterministic coverage and isolation behavior |
| 3 | Catalog-derived source/wheel correctness matrix | xdist, local workers, `--dist load` | `coverage run --parallel-mode -m pytest -n N ...` with `patch = subprocess` | Per-row source/wheel equality and lifecycle coverage |
| 4 | Combine and report | serial | `coverage combine`, then `coverage report` | One unioned dataset and the existing 85% threshold |
| 5 | Performance markers | serial, no xdist, no coverage | none | Stable deterministic thresholds without worker/coverage noise |
| 6 | Disposable release replay | serial, no xdist | only if separately required | Ordered build/migration/release evidence |

Use `[tool.coverage.run] parallel = true` and `patch = ["subprocess"]` rather than relying on command-specific state. This makes both the serial controller and worker/child processes write `.coverage.*`; the explicit combine can then safely create `.coverage` from the full set. Keep the patch scoped to commands started under `coverage run`; do not export coverage startup variables globally into performance or release replay phases. [official] (<https://coverage.readthedocs.io/en/latest/subprocess.html>)

### Preserve parity and isolation at row granularity

- Keep `_exercise_both()` intact: each parametrized row must exercise source and wheel from the same worker and compare results immediately. Splitting source and wheel into separate CI jobs weakens parity because the two sides no longer share the same row inputs, runner state, or failure context.
- Continue giving each lifecycle a separate subtree under that row's `tmp_path`. This is already the strongest isolation surface in [`test_catalog_matrix.py`](../../tests/package_compatibility/test_catalog_matrix.py).
- Build the wheel once before worker fan-out, then let every worker extract or instantiate its own read-only `InstalledDistribution`. The current session-scoped fixture in [`tests/package_compatibility/conftest.py`](../../tests/package_compatibility/conftest.py) runs once **per worker**, so leaving the build there multiplies `uv build` by `N`. A controller/workflow prebuild is simpler than cross-worker locking; the official file-lock pattern is a fallback when orchestration cannot prebuild. [official] (<https://pytest-xdist.readthedocs.io/en/latest/how-to.html>)
- Cache only test-side catalog/default discovery within each worker process. Integration testing confirmed that production `InstalledDistribution` reloads are a fail-closed tamper check, so verified installed catalogs must not be cached across calls. Do not share consumer repositories, provider output, or coverage databases between workers.
- Keep the network-denial fixture and `uv build --offline`. The build occurs in a higher-scoped fixture before the function-scoped network monkeypatch, so offline mode remains a necessary independent control.

### Select workers from measured throughput, not a CPU label

xdist 3.8 cannot distinguish performance and efficiency cores, memory pressure, filesystem contention, or the cost of repeated session fixtures. A core count is therefore only a starting bound. Benchmark `N = 2`, `3`, `4`, and the runner's reported affinity count, recording median matrix wall time and peak RSS over at least three runs. Select the smallest `N` at the throughput knee and set it explicitly in CI; allow a local environment override through `PYTEST_XDIST_AUTO_NUM_WORKERS` if desired. [official] (<https://pytest-xdist.readthedocs.io/en/latest/distribution.html>) [community, project issue] (<https://github.com/pytest-dev/pytest-xdist/issues/1103>)

Do not make the workstation's 21-process affinity result the CI default. GitHub-hosted runner resources depend on runner class and repository context, and larger/self-hosted runners can differ again. [official] (<https://docs.github.com/en/actions/reference/runners/github-hosted-runners>)

### Acceptance evidence

| Severity | Required check | Failure prevented |
| --- | --- | --- |
| Critical | Compare exact collected node IDs or a deterministic manifest for serial and xdist matrix forms | Missing or differently ordered parametrized rows |
| Critical | Prove the final combined coverage is the union of ordinary and matrix phases and still meets `fail_under = 85` | Silent loss of serial `.coverage` data |
| High | Assert one wheel build per gate, not one per worker | Fixture duplication erasing the wall-time gain |
| High | Run matrix serially and with each candidate `N`; require identical pass/fail and row counts | Hidden test coupling or scheduler-sensitive behavior |
| High | Keep performance and release replay commands free of `-n`, xdist addopts, and coverage patching | Noisy thresholds or reordered release evidence |
| Medium | Record per-phase durations and worker count in CI logs | A faster subphase masking a slower total gate |

## Footguns and Gotchas

- **[critical] Coverage-data loss:** `coverage combine` ignores and rewrites an existing `.coverage`. If ordinary tests write `.coverage` and xdist workers write `.coverage.*`, a plain combine can preserve only the worker files. Use suffixed data for all covered phases and combine once. [official] (<https://coverage.readthedocs.io/en/latest/commands/cmd_combine.html>)
- **[high] Session fixture multiplication:** a session fixture is session-scoped **per worker**, not per controller run. The current source fixture and wheel-build fixture will each execute `N` times unless the immutable artifacts are prepared before fan-out or coordinated with a lock. [official] (<https://pytest-xdist.readthedocs.io/en/latest/how-to.html>)
- **[high] Unstable `-n auto` meaning in 3.8:** with psutil it prefers physical/logical system counts; without psutil it falls back to affinity or OS counts. The repository's current environment has no psutil, while a future transitive dependency could change the result without a workflow edit. This behavior and cgroup/HPC oversubscription are corroborated by the tagged implementation and two project issues. [official] (<https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/plugin.py>) [community, project issues] (<https://github.com/pytest-dev/pytest-xdist/issues/1103>, <https://github.com/pytest-dev/pytest-xdist/issues/1296>)
- **[high] Shared resources become races:** fixed paths, ports, environment mutations, or mutable caches that were safe serially can collide. Use `tmp_path`, `worker_id`, or `testrun_uid`; reserve `xdist_group` only for a small resource-bound subset. [official] (<https://docs.pytest.org/en/stable/how-to/tmp_path.html>, <https://pytest-xdist.readthedocs.io/en/latest/how-to.html>)
- **[high] Abrupt children lose coverage:** patching subprocess startup does not guarantee data from processes that crash or terminate without coverage shutdown. Treat an xdist worker crash as a gate failure, keep `--max-worker-restart=0` for release verification unless recovery behavior is itself being tested, and require a clean combine/report. [official] (<https://coverage.readthedocs.io/en/latest/subprocess.html>, <https://pytest-xdist.readthedocs.io/en/stable/crash.html>)
- **[medium] Distribution mode can remove parallelism:** `loadscope` groups module-level test functions by module. Applied to the one-file catalog matrix, it can serialize the entire phase. `load` is the appropriate first benchmark; `worksteal` is a follow-up only if row durations are demonstrably skewed. [official] (<https://pytest-xdist.readthedocs.io/en/latest/distribution.html>)
- **[medium] Coverage and parity are different proofs:** `[tool.coverage.run] source = ["src"]` measures the source tree. The wheel half can still prove behavioral parity without its extracted path contributing to the coverage percentage. If installed-wheel line coverage later becomes a requirement, add explicit `[paths]` remapping rather than assuming current coverage proves it.

## Existing Tools

| Tool | Maintenance | Authority | Link | Fit for use case |
| --- | --- | --- | --- | --- |
| pytest-xdist 3.8.0 | Released 2025-06-30; active | [official] | <https://pytest-xdist.readthedocs.io/en/latest/changelog.html> | Best fit for parallelizing only the independent catalog rows inside one job |
| coverage.py 7.14.1 | Locked in this repository; active 7.14 line | [official] | <https://coverage.readthedocs.io/en/latest/subprocess.html> | Direct subprocess measurement and parallel data combination without replacing the current coverage CLI |
| pytest-cov 7.x | Active | [official] | <https://pytest-cov.readthedocs.io/en/latest/readme.html> | Supports xdist and delegates subprocess measurement to coverage patching; useful alternative, but adds a dependency and does not solve phase orchestration |
| Existing `check.yml` / `run_repository_tests.py` | Repository-owned | repository | [workflow](../../.github/workflows/check.yml), [local gate](../../scripts/run_repository_tests.py) | Owns serial/parallel phase ordering without adding another task-runner dependency |
| tox / Nox | Active | [official] | <https://tox.wiki/en/latest/user_guide.html> | Useful for multi-environment isolation, but no material benefit for one Python 3.14 environment and one within-job matrix phase |
| GitHub Actions matrix / pytest-split | Active | [official] | <https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs> | Later option for cross-runner sharding; currently weakens same-row parity and adds artifact/coverage merge overhead |

The existing stack covers orchestration. A new custom scheduler, test splitter, or distributed service is not warranted for v5 release verification.

## Security and Compatibility

- xdist workers execute repository test code as ordinary child processes with the job's environment and filesystem permissions; process separation is not a security sandbox. Keep local `popen` workers only, retain `permissions: contents: read`, and do not use the remote/proxy gateway features for this gate. [official] (<https://pytest-xdist.readthedocs.io/en/latest/how-it-works.html>, <https://docs.github.com/en/actions/reference/security/secure-use>)
- The current compatibility suite's network monkeypatch and per-test temporary directories are compatible with local xdist. Preserve the independent `uv build --offline` protection because session fixture setup precedes the function-scoped network denial. [official] (<https://docs.pytest.org/en/stable/how-to/tmp_path.html>)
- Worker-specific environment variables and `worker_id` are safe for namespacing non-secret resource identifiers. Do not copy secrets into test names, paths, coverage contexts, or worker logs; GitHub notes that secrets can be exposed to any code with runner access. [official] (<https://pytest-xdist.readthedocs.io/en/latest/how-to.html>, <https://docs.github.com/en/actions/reference/security/secure-use>)
- pytest-xdist's GitHub security page listed no published advisories at research time, but also no project security policy. Absence of advisories is not evidence that parallel execution is a sandbox. [official] (<https://github.com/pytest-dev/pytest-xdist/security>)
- pytest-xdist 3.8.0 and pytest 9.0.3 loaded together in the isolated probe. The repository currently locks coverage 7.14.1 and pytest 9.0.3 but has neither pytest-xdist nor psutil in its lock; lock the added xdist version and test the actual resolved environment.

## Recent Changes

- pytest-xdist 3.8.0 (2025-06-30) added `--loadscope-reorder` / `--no-loadscope-reorder`. The default reorders scopes to improve parallel utilization, which is another reason not to use loadscope for proofs that rely on relative module order. [official] (<https://pytest-xdist.readthedocs.io/en/latest/changelog.html>)
- pytest-xdist 3.7.0 added atomic work stealing and merged multiple `xdist_group` markers. These features make grouped scheduling safer, but do not make session fixtures controller-global. [official] (<https://pytest-xdist.readthedocs.io/en/latest/changelog.html>)
- coverage.py 7.14.0 (2026-05-10) made report commands implicitly combine pending parallel files. This reduces the need for a separate command, but does not change the documented rule that an existing combined base file is ignored and rewritten by combination. [official] (<https://coverage.readthedocs.io/en/latest/changes.html>, <https://coverage.readthedocs.io/en/latest/commands/cmd_combine.html>)
- coverage.py 7.14.1 (2026-05-26), the repository's lock, changed HTML-report path rendering and classifiers rather than subprocess semantics. The relevant subprocess fixes landed earlier, so pinning 7.14.1 is compatible with this design but should not be described as introducing `patch = subprocess`. [official] (<https://coverage.readthedocs.io/en/latest/changes.html>)
- pytest-cov 7 removed its older `.pth` subprocess mechanism and now directs users to coverage's patch options, independently corroborating the selected subprocess mechanism. [official] (<https://pytest-cov.readthedocs.io/en/latest/readme.html>)

## Open Questions

| # | Question | Why unresolved |
| --: | --- | --- |
| 1 | What fixed worker count minimizes the matrix's median wall time on the exact `ubuntu-latest` runner used for the v5 release gate? | Requires the plan's missing serial baseline plus repeated `N = 2, 3, 4, affinity` measurements on the hosted runner; workstation CPU counts are not transferable. |
| 2 | Can the wheel be built once in a workflow step and passed to workers without changing the disposable release replay's artifact provenance? | The matrix fixture currently owns its own offline build; the release replay owner and evidence-digest interface were not yet present in the checked workflow. |
| 3 | Does the matrix contribute unique source-tree coverage needed to remain above 85%, or can it run outside coverage after parity is proven? | Requires comparing coverage JSON from ordinary-only and unioned phases. Until measured, preserve it in the combined covered phases. |
| 4 | Are any catalog rows materially duration-skewed enough for `worksteal` to outperform `load` after the wheel build is deduplicated? | Requires `--durations` evidence from the serial baseline; no scheduler should be selected from test count alone. |

## Handoff

Persisted at `docs/research/2026-07-12-v5-release-verification-performance.md`. Downstream consumers should read this artifact rather than re-running the sweep. Implementation should amend the existing performance plan with the coverage-combine correction, explicit worker-selection acceptance test, one-build artifact boundary, and serial/xdist collection-parity proof before changing the gate.

Validation note: the qdev frontmatter validator, generated research index, scoped Prettier, scoped markdownlint, local-link validation, and `git diff --check` passed for the two owned files. The broad markdownlint configuration also selected two unrelated in-progress plans and reported their inherited MD001 heading-increment errors; those files were outside this task's write boundary. The supplemental repository composite validator rejects the protocol-mandated date-prefixed filename-stem `id` under its newer frozen-ID convention; the qdev protocol's own research validator accepts it, matching the existing corpus workflow.

## Sources

| URL | Title | Date | Authority |
| --- | --- | --- | --- |
| <https://pytest-xdist.readthedocs.io/en/latest/distribution.html> | Running tests across multiple CPUs — pytest-xdist | current | official |
| <https://pytest-xdist.readthedocs.io/en/latest/how-to.html> | How-tos — pytest-xdist | current | official |
| <https://pytest-xdist.readthedocs.io/en/latest/how-it-works.html> | How it works? — pytest-xdist | current | official |
| <https://pytest-xdist.readthedocs.io/en/latest/changelog.html> | Changelog — pytest-xdist | 2025-06-30 release entry | official |
| <https://pytest-xdist.readthedocs.io/en/stable/crash.html> | When tests crash — pytest-xdist | current | official |
| <https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/plugin.py> | pytest-xdist 3.8.0 worker-count implementation | 2025-06-30 tag | official |
| <https://github.com/pytest-dev/pytest-xdist/issues/1103> | Improve autodetection of number of available CPUs | 2024-2026 | community, official project tracker |
| <https://github.com/pytest-dev/pytest-xdist/issues/1296> | Respect Python CPU-count overrides | 2026 | community, official project tracker |
| <https://pypi.org/project/pytest-xdist/> | pytest-xdist release and attestations | current | official |
| <https://coverage.readthedocs.io/en/latest/subprocess.html> | Managing processes — coverage.py | 7.14 documentation | official |
| <https://coverage.readthedocs.io/en/latest/commands/cmd_combine.html> | Combining data files — coverage.py | 7.14+ documentation | official |
| <https://coverage.readthedocs.io/en/latest/changes.html> | Change history — coverage.py | 2026-05 to 2026-06 | official |
| <https://pytest-cov.readthedocs.io/en/latest/readme.html> | pytest-cov overview and xdist support | current | official |
| <https://docs.pytest.org/en/stable/how-to/tmp_path.html> | Temporary directories and files in tests | pytest 9 documentation | official |
| <https://tox.wiki/en/latest/user_guide.html> | tox user guide | current | official |
| <https://docs.github.com/en/actions/reference/runners/github-hosted-runners> | GitHub-hosted runners reference | current | official |
| <https://docs.github.com/en/actions/reference/security/secure-use> | Secure use reference for GitHub Actions | current | official |
| <https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs> | Running variations of jobs in a workflow | current | official |
| <https://github.com/pytest-dev/pytest-xdist/security> | pytest-xdist security overview | current | official |
