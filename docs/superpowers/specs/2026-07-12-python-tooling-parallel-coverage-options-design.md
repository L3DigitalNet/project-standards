# Python Tooling Parallel Coverage Options Design

**Date:** 2026-07-12 **Status:** owner-approved; implementation pending **Author:** Codex with Chris Purcell / L3DigitalNet

## Problem and goal

The optimized repository gate writes suffixed coverage data across serial and pytest-xdist phases, then combines it once. The source checkout declares `parallel = true` and `patch = ["subprocess"]` under `[tool.coverage.run]`, but Python Tooling 1.1 cannot represent either setting. Its V5 migration would therefore replace the root coverage table with the package default and silently remove the optimization during the atomic source-root migration.

The goal is to make those coverage settings explicit, closed Python Tooling package options while preserving existing consumer defaults. The v5 release migration must retain this repository's parallel coverage behavior, `pytest-xdist` dependency, and phase markers without weakening source/wheel parity or legacy migration safety.

## Approved approach

Add a top-level `coverage` option object to Python Tooling 1.1:

```json
{ "coverage": { "parallel": false, "patch": [] } }
```

- `parallel` is a required, defaulted boolean.
- `patch` is a required, defaulted unique array whose only supported value is `"subprocess"`.
- Defaults preserve the current package output for consumers that do not opt in.
- The repository's disposable v5 migration selects `parallel = true` and `patch = ["subprocess"]`.
- `pytest-xdist>=3.8` remains explicit in `additional_dev_dependencies`; selecting parallel coverage does not implicitly select a test-distribution dependency or policy.

## Alternatives rejected

1. **Enable parallel coverage for every Python Tooling consumer.** This is simpler but changes unrelated consumer output and adds subprocess behavior where it was not selected.
2. **Leave the settings consumer-owned after reconciliation.** This conflicts with the package-owned `[tool.coverage.run]` contribution and would make repeated reconciliation unable to prove the gate contract.
3. **Special-case this repository in the release fixture.** A fixture-only patch could make the proof pass while the actual V5 provider still deletes the settings; it would conceal rather than fix the contract gap.

## Contract changes

### Configuration schema

`standards/python-tooling/versions/1.1/config.schema.json` gains the closed, fully defaulted `coverage` object. Unknown coverage keys and patch values fail package option validation before planning or writes.

### Provider rendering

The Python Tooling provider renders the selected values into its bounded `[tool.coverage.run]` contribution:

- `parallel = true` is emitted only when selected.
- `patch = ["subprocess"]` is emitted only when selected.
- Default output remains byte-identical to the existing immutable static resources.

The option does not change coverage thresholds, exclusions, test markers, worker counts, xdist distribution policy, or workflow phase orchestration. Those remain separate declared options or consumer-specific gate behavior.

### Legacy migration

The provider recognizes `/python_tooling/coverage` as a V4-to-V5 migration input and copies it through normal JSON-safe option handling. The disposable release fixture declares:

- `additional_dev_dependencies = ["types-PyYAML", "pytest-xdist>=3.8"]`;
- the `compatibility`, `performance`, and `release_replay` pytest markers;
- `coverage.parallel = true`;
- `coverage.patch = ["subprocess"]`.

The migrated `.standards/config.toml` and composed `pyproject.toml` must retain those values. Modified or invalid legacy inputs continue to fail closed.

## Files and ownership

| Surface | Responsibility |
| --- | --- |
| `standards/python-tooling/versions/1.1/config.schema.json` | Closed option contract and defaults |
| `standards/python-tooling/versions/1.1/providers/python_tooling.py` | Defaulting, rendering, and legacy migration |
| `standards/python-tooling/versions/1.1/README.md` | Consumer-facing package option semantics |
| `standards/python-tooling/versions/1.1/payload.toml` and family/catalog metadata | Resource and aggregate integrity |
| `tests/package_contract/test_python_tooling_reconstruction.py` | Option, rendering, rejection, migration, and source/wheel reconstruction coverage |
| `tests/package_compatibility/release_candidate.py` | Repository-specific disposable release intent |
| `tests/package_compatibility/test_release_candidate.py` | Atomic migration preservation and release evidence |

## Failure behavior

- Unsupported patch names or extra coverage keys fail schema validation before reconciliation.
- Missing coverage values receive schema defaults and preserve current consumer output.
- A release migration that drops `parallel`, `subprocess`, `pytest-xdist`, or any phase marker fails the disposable release test before evidence can be refreshed.
- Payload or provider byte changes without regenerated digests fail package, graph, projection, and source/wheel reconstruction gates.

## Verification

Follow test-driven development:

1. Add failing option/default/rendering tests.
2. Add a failing migration test that requires `/python_tooling/coverage` recognition.
3. Add failing release assertions for the dependency, markers, and coverage run settings.
4. Implement the schema and provider changes.
5. Regenerate package digests, catalog metadata, and payload projections.
6. Run focused Python Tooling reconstruction and release-fixture tests.
7. Run package/graph/schema/projection gates and the optimized repository gate.

## Acceptance criteria

- Python Tooling options remain closed and fully defaulted.
- Default consumers render the same coverage run table as before.
- Opted-in consumers render `parallel = true` and `patch = ["subprocess"]`.
- Unsupported coverage options fail before writes.
- V4 migration recognizes and preserves the coverage object.
- The disposable v5 root migration retains `pytest-xdist`, all three pytest markers, and both coverage settings.
- Source and extracted-wheel behavior remain identical.
- Package integrity, payload projection, combined coverage, performance, and disposable release replay gates pass.
