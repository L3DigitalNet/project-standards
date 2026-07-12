# Python Tooling Parallel Coverage Options Design

**Date:** 2026-07-12 **Status:** owner-approved; audit round 1 reconciled; implementation pending **Author:** Codex with Chris Purcell / L3DigitalNet

## Problem and goal

The optimized repository gate writes suffixed coverage data across serial and pytest-xdist phases, then combines it once. Its parent `coverage run` commands already force `--parallel-mode`; the source checkout's `patch = ["subprocess"]` is what enables child-process measurement, while config-level `parallel = true` preserves explicit suffixed-data semantics for those children. Python Tooling 1.1 cannot represent either setting. Its V5 migration would replace the root coverage table with the package default and remove subprocess capture plus the explicit parallel contract during the atomic source-root migration.

The goal is to make those coverage settings explicit, closed Python Tooling package options while preserving existing consumer defaults. The v5 release migration must retain this repository's parallel coverage behavior, `pytest-xdist` dependency, and phase markers without weakening source/wheel parity or legacy migration safety.

## Approved approach

Add a top-level `coverage` option object to Python Tooling 1.1:

```json
{ "coverage": { "parallel": false, "patch": [] } }
```

- `parallel` is a required, defaulted boolean.
- `patch` is a required, defaulted unique array whose only supported value is `"subprocess"`.
- A non-empty `patch` requires `parallel = true`; the schema rejects the contradictory combination before provider execution. Coverage.py also forces parallel mode internally for its subprocess patch, but the rendered package configuration must not state otherwise.
- Defaults preserve the current package output for consumers that do not opt in.
- The repository's disposable v5 migration selects `parallel = true` and `patch = ["subprocess"]`.
- `pytest-xdist>=3.8` remains explicit in `additional_dev_dependencies`; selecting parallel coverage does not implicitly select a test-distribution dependency or policy.
- Selecting the subprocess patch renders `coverage[toml]>=7.10.0`, the release that introduced `[run] patch`; configurations without a patch retain the current floorless dependency.

## Alternatives rejected

1. **Enable parallel coverage for every Python Tooling consumer.** This is simpler but changes unrelated consumer output and adds subprocess behavior where it was not selected.
2. **Leave the settings consumer-owned after reconciliation.** This conflicts with the package-owned `[tool.coverage.run]` contribution and would make repeated reconciliation unable to prove the gate contract.
3. **Special-case this repository in the release fixture.** A fixture-only patch could make the proof pass while the actual V5 provider still deletes the settings; it would conceal rather than fix the contract gap.

## Audit round 1 disposition

- **SA-001:** The reported `No data to report` failure is not reproducible with this repository's coverage 7.14.1. Since 7.14.0, reporting commands implicitly combine parallel files, and the live probe printed `Combined 1 file`. The package will nevertheless render explicit erase/combine steps for deterministic cleanup and compatibility with the selected 7.10.0 patch floor.
- **SA-002:** Accepted. The problem statement now distinguishes parent CLI parallel mode from config-driven subprocess capture and suffixing.
- **SA-003:** Accepted with a conditional `coverage[toml]>=7.10.0` floor when a patch is selected.
- **SA-004:** Accepted as a schema-coherence rule even though coverage's subprocess patch internally forces parallel mode.
- **SA-005:** Accepted; canonical coverage-run key order is specified below.
- **SA-006:** Accepted; default preservation refers to semantic contribution rendering, not a static resource.
- **SA-007:** Accepted; `_DEFAULT_CONFIG` must change in lockstep with the schema default.

## Contract changes

### Configuration schema

`standards/python-tooling/versions/1.1/config.schema.json` gains the closed, fully defaulted `coverage` object. Unknown coverage keys and patch values fail package option validation before planning or writes. A schema conditional rejects `patch = ["subprocess"]` unless `parallel = true`.

### Provider rendering

The Python Tooling provider renders the selected values into its bounded `[tool.coverage.run]` contribution:

- `parallel = true` is emitted only when selected.
- `patch = ["subprocess"]` is emitted only when selected.
- Canonical key order is `branch`, optional `parallel`, optional `patch`, then `source`.
- Default rendering of `table:/tool/coverage/run` remains unchanged as `branch` then `source`; the three static whole-file resources remain unaffected.
- `_DEFAULT_CONFIG` receives the exact schema-default `coverage` object so default whole-file static-source verification remains active.
- Dependency rendering selects `coverage[toml]>=7.10.0` only when `patch` is non-empty.

The option does not change coverage thresholds, exclusions, test markers, worker counts, or xdist distribution policy. Those remain separate declared options or consumer-specific behavior.

### Package-rendered gate

Default configurations retain the current `coverage run` then `coverage report` sequence byte for byte. When `coverage.parallel` is true, both CI and local generated gates render:

```text
coverage erase
coverage run --parallel-mode ...
coverage combine
coverage report
```

This sequence applies through `_commands`, `_local_commands`, `_workflow`, and `_script`. It removes stale shards before measurement, works across the full supported patch floor beginning with coverage 7.10.0, and reports from one combined data file. An end-to-end scratch-consumer test must prove the generated gate captures code executed only in a subprocess and exits successfully with a non-empty report.

The current root `scripts/check.py` and V1 adopt-bundle twin remain frozen legacy-signature bytes before atomic migration. The root CI uses `scripts/run_repository_tests.py`; atomic V5 migration replaces the root script with the non-default, parallel-aware Python Tooling rendering.

### Legacy migration

The provider recognizes `/python_tooling/coverage` as a V4-to-V5 migration input and copies it through normal JSON-safe option handling. Schema validation then rejects invalid coverage values before reconciliation planning; legacy file-tamper signatures remain a separate fail-closed check. The disposable release fixture declares:

- `additional_dev_dependencies = ["types-PyYAML", "pytest-xdist>=3.8"]`;
- the `compatibility`, `performance`, and `release_replay` pytest markers;
- `coverage.parallel = true`;
- `coverage.patch = ["subprocess"]`.

The migrated `.standards/config.toml` and composed `pyproject.toml` must retain those values. Modified legacy managed files still fail signature checks, while invalid legacy option values fail package schema validation.

## Files and ownership

| Surface | Responsibility |
| --- | --- |
| `standards/python-tooling/versions/1.1/config.schema.json` | Closed option contract and defaults |
| `standards/python-tooling/versions/1.1/providers/python_tooling.py` | Defaults, dependency floor, coverage rendering, gate orchestration, and legacy migration |
| `standards/python-tooling/versions/1.1/README.md` | Consumer-facing package option semantics |
| `standards/python-tooling/versions/1.1/payload.toml` and family/catalog metadata | Resource and aggregate integrity |
| `tests/package_contract/test_python_tooling_reconstruction.py` | Option, rendering, rejection, migration, and source/wheel reconstruction coverage |
| `tests/package_compatibility/release_candidate.py` | Repository-specific disposable release intent |
| `tests/package_compatibility/test_release_candidate.py` | Atomic migration preservation and release evidence |
| `scripts/check.py` and `src/project_standards/bundles/python-tooling/check.py` | Frozen default legacy bytes before migration; unchanged by this option addition |

## Failure behavior

- Unsupported patch names, extra coverage keys, or subprocess patch without explicit parallel mode fail schema validation before reconciliation.
- Missing coverage values receive schema defaults and preserve current consumer output.
- A selected subprocess patch without coverage.py 7.10.0 or newer is prevented by the rendered dependency floor.
- A parallel-aware generated gate erases stale data, writes suffixed data, combines once, and reports; any command failure stops the gate with its original exit code.
- A release migration that drops `parallel`, `subprocess`, `pytest-xdist`, any phase marker, or the parallel-aware generated script fails the disposable release test before evidence can be refreshed.
- Payload or provider byte changes without regenerated digests fail package, graph, projection, and source/wheel reconstruction gates.

## Verification

Follow test-driven development:

1. Add failing option/default/rendering, dependency-floor, and cross-field rejection tests.
2. Add failing command-rendering tests for the conditional erase/run/combine/report sequence.
3. Add a failing end-to-end scratch-consumer test whose generated gate measures subprocess-only code and produces a non-empty report.
4. Add a failing migration test that requires `/python_tooling/coverage` recognition.
5. Add failing release assertions for the dependency, markers, coverage settings, and generated script.
6. Implement the schema and provider changes.
7. Regenerate package digests, catalog metadata, and payload projections.
8. Run focused Python Tooling reconstruction and release-fixture tests.
9. Compare subprocess-aware coverage evidence with the patch disabled to demonstrate the preserved behavior.
10. Run package/graph/schema/projection gates and the optimized repository gate.

## Acceptance criteria

- Python Tooling options remain closed and fully defaulted.
- Default consumers render the same coverage run table as before.
- Opted-in consumers render `branch`, `parallel = true`, `patch = ["subprocess"]`, and `source` in canonical order.
- Opted-in dependency rendering includes `coverage[toml]>=7.10.0`; default dependency rendering remains unchanged.
- Unsupported coverage options and patch-without-parallel configurations fail before writes.
- Default generated gates remain byte-identical; parallel-aware generated gates render erase/run/combine/report in that order.
- The parallel-aware generated gate runs end to end, measures subprocess-only code, reports non-empty data, and removes input shards.
- V4 migration recognizes and preserves the coverage object.
- The disposable v5 root migration retains `pytest-xdist`, all three pytest markers, both coverage settings, and a working parallel-aware check script.
- Source and extracted-wheel behavior remain identical.
- Package integrity, payload projection, combined coverage, performance, and disposable release replay gates pass.
