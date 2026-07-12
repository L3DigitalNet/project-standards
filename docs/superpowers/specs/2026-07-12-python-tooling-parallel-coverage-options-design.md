# Python Tooling Parallel Coverage Options Design

**Date:** 2026-07-12 **Status:** owner-approved; audit rounds 1-3 reconciled; implementation pending **Author:** Codex with Chris Purcell / L3DigitalNet

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
- A non-empty `patch` requires an explicitly present `parallel = true`; the schema rejects both false and omitted values before provider execution. This follows coverage.py's public subprocess guidance and does not rely on version-specific internal post-processing.
- Defaults preserve the current package output for consumers that do not opt in.
- The repository's disposable v5 migration selects `parallel = true` and `patch = ["subprocess"]`.
- `pytest-xdist>=3.8` remains explicit in `additional_dev_dependencies`; selecting parallel coverage does not implicitly select a test-distribution dependency or policy.
- Selecting the subprocess patch renders `coverage[toml]>=7.10.0`, the release that introduced `[run] patch`; configurations without a patch retain the current floorless dependency.
- Python Tooling gains a top-level `workflow_ownership = "managed" | "consumer-owned"` option, defaulting to `managed`. The distinct name avoids colliding with Markdown Tooling and Project Specification's `workflow_mode = "caller" | "self-hosted"` delivery axis.
- This repository's disposable v5 migration selects `workflow_ownership = "consumer-owned"`, preserving its optimized multi-phase `.github/workflows/check.yml` without package ownership or lock state.

## Alternatives rejected

1. **Enable parallel coverage for every Python Tooling consumer.** This is simpler but changes unrelated consumer output and adds subprocess behavior where it was not selected.
2. **Leave the settings consumer-owned after reconciliation.** This conflicts with the package-owned `[tool.coverage.run]` contribution and would make repeated reconciliation unable to prove the gate contract.
3. **Special-case this repository in the release fixture.** A fixture-only patch could make the proof pass while the actual V5 provider still deletes the settings; it would conceal rather than fix the contract gap.
4. **Teach the generic package to reproduce this repository's specialized release phases.** The compatibility-wheel prebuild, release replay, and performance marker topology are repository-specific and would overfit Python Tooling.
5. **Let migration replace the optimized root workflow.** This would restore the structural contract while regressing the release-verification optimization that triggered this work.

## Audit round 1 disposition

- **SA-001:** The reported `No data to report` failure is not reproducible with this repository's coverage 7.14.1. Since 7.14.0, reporting commands implicitly combine parallel files, and the live probe printed `Combined 1 file`. The package will nevertheless render explicit erase/combine steps for deterministic cleanup and compatibility with the selected 7.10.0 patch floor.
- **SA-002:** Accepted. The problem statement now distinguishes parent CLI parallel mode from config-driven subprocess capture and suffixing.
- **SA-003:** Accepted with a conditional `coverage[toml]>=7.10.0` floor when a patch is selected.
- **SA-004:** Accepted as a schema-coherence rule even though coverage's subprocess patch internally forces parallel mode.
- **SA-005:** Accepted; canonical coverage-run key order is specified below.
- **SA-006:** Accepted; default preservation refers to semantic contribution rendering, not a static resource.
- **SA-007:** Accepted; `_DEFAULT_CONFIG` must change in lockstep with the schema default.

## Audit round 2 disposition

- **SA-NEW-001:** Accepted. Coverage-option implementation keeps the V1 bundle/root script twin frozen. Atomic migration replaces only the root script, retires its obsolete `_DOGFOOD` mapping, and replaces that assertion with separate frozen-V1 and current-V2 checks.
- **SA-NEW-002:** Accepted. The schema conditional's `then` branch requires `parallel` to be present as well as `true`.
- **SA-NEW-003:** Accepted with a precision correction. Current coverage.py post-processing may force parallel for the subprocess patch, but the package follows the public requirement for explicit parallel configuration and does not rely on that internal behavior.
- **Root workflow preservation:** Owner-approved as a general workflow-ownership option. The root selects `consumer-owned`; default consumers remain `managed`.

## Audit round 3 disposition

- **SA-NEW-004:** Accepted. `/python_tooling/workflow_ownership` is a recognized legacy migration input, and the signature classifier consults its resolved value before emitting the workflow claim.
- **SA-NEW-005:** Accepted. The option is renamed to `workflow_ownership` so the ownership axis cannot be confused with the existing cross-package `workflow_mode` delivery axis.
- **SA-NEW-006:** Accepted. `ci.enabled` and `ci.performance` are documented and validated as managed-workflow-only settings; they do not govern a consumer-owned workflow.
- **Verification wiring:** `run_verify` conditionally excludes `.github/workflows/check.yml` only when `workflow_ownership = "consumer-owned"`; the other managed whole-file targets remain verified.

## Contract changes

### Configuration schema

`standards/python-tooling/versions/1.1/config.schema.json` gains the closed, fully defaulted `coverage` object. Unknown coverage keys and patch values fail package option validation before planning or writes. When raw input contains a non-empty patch, the schema conditional's `then` branch requires `parallel` to be present and equal to `true`; omission cannot fall through to the default.

The same schema adds top-level `workflow_ownership` with the closed values `managed` and `consumer-owned` and default `managed`. The `ci` options remain valid in both modes for config round-trip stability, but their documentation states that they affect only a managed workflow.

### Provider rendering

The Python Tooling provider renders the selected values into its bounded `[tool.coverage.run]` contribution:

- `parallel = true` is emitted only when selected.
- `patch = ["subprocess"]` is emitted only when selected.
- Canonical key order is `branch`, optional `parallel`, optional `patch`, then `source`.
- Default rendering of `table:/tool/coverage/run` remains unchanged as `branch` then `source`; the three static whole-file resources remain unaffected.
- `_DEFAULT_CONFIG` receives the exact schema-default `coverage` object and `workflow_ownership` value so default whole-file static-source verification remains active.
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

### Workflow ownership

The `check-workflow` payload contribution materializes only when `workflow_ownership = "managed"`, using the existing flat `when_any` predicate. In `consumer-owned` mode:

- the payload does not declare or lock `.github/workflows/check.yml`;
- migration recognizes `/python_tooling/workflow_ownership`, resolves it before signature classification, and emits the recognized workflow claim with `ownership = "consumer-owned"` and `disposition = "preserve"` instead of the default managed/adopt pair;
- `run_verify` excludes the workflow from its managed whole-file loop while continuing to verify `.python-version` and `scripts/check.py`;
- disable/re-enable leaves the workflow untouched;
- `.python-version` and `scripts/check.py` remain managed normally.

`ci.enabled` and `ci.performance` configure only a package-managed workflow. They are intentionally inert when the workflow is consumer-owned because Python Tooling neither parses nor governs consumer workflow triggers or commands.

The root release intent selects `consumer-owned`, so its optimized workflow continues calling `scripts/run_repository_tests.py`. This option is general: any consumer with a project-specific Python workflow may retain it while adopting the remaining Python Tooling contract.

### Legacy migration

The provider recognizes `/python_tooling/coverage` and `/python_tooling/workflow_ownership` as V4-to-V5 migration inputs and copies them through normal JSON-safe option handling. The resolved ownership value governs workflow signature classification in the same provider call. Schema validation then rejects invalid option values before reconciliation planning; legacy file-tamper signatures remain a separate fail-closed check. The disposable release fixture declares:

- `additional_dev_dependencies = ["types-PyYAML", "pytest-xdist>=3.8"]`;
- the `compatibility`, `performance`, and `release_replay` pytest markers;
- `coverage.parallel = true`;
- `coverage.patch = ["subprocess"]`.
- `workflow_ownership = "consumer-owned"`.

The migrated `.standards/config.toml` and composed `pyproject.toml` must retain those values. Modified legacy managed files still fail signature checks, while invalid legacy option values fail package schema validation.

## Files and ownership

| Surface | Responsibility |
| --- | --- |
| `standards/python-tooling/versions/1.1/config.schema.json` | Closed option contract and defaults |
| `standards/python-tooling/versions/1.1/providers/python_tooling.py` | Defaults, dependency floor, coverage rendering, gate orchestration, and legacy migration |
| `standards/python-tooling/versions/1.1/README.md` | Consumer-facing package option semantics |
| `standards/python-tooling/versions/1.1/payload.toml` and family/catalog metadata | Conditional workflow materialization plus resource and aggregate integrity |
| `tests/package_contract/test_python_tooling_reconstruction.py` | Option, rendering, rejection, migration, and source/wheel reconstruction coverage |
| `tests/package_compatibility/release_candidate.py` | Repository-specific disposable release intent |
| `tests/package_compatibility/test_release_candidate.py` | Atomic migration preservation and release evidence |
| `scripts/check.py` and `src/project_standards/bundles/python-tooling/check.py` | Frozen default legacy bytes before migration; unchanged by this option addition |
| `tests/test_adopt_dogfood.py` and frozen-runtime tests | Pre-migration twin contract; atomic-migration retirement and separate V1/V2 assertions |

## Failure behavior

- Unsupported patch names, extra coverage keys, or subprocess patch with false or omitted parallel mode fail schema validation before reconciliation.
- Missing coverage values receive schema defaults and preserve current consumer output.
- A selected subprocess patch without coverage.py 7.10.0 or newer is prevented by the rendered dependency floor.
- A parallel-aware generated gate erases stale data, writes suffixed data, combines once, and reports; any command failure stops the gate with its original exit code.
- A consumer-owned workflow is never rendered, claimed, locked, drift-checked, updated, or removed by Python Tooling.
- A release migration that drops `parallel`, `subprocess`, `pytest-xdist`, any phase marker, the optimized consumer-owned workflow, or the parallel-aware generated script fails the disposable release test before evidence can be refreshed.
- Payload or provider byte changes without regenerated digests fail package, graph, projection, and source/wheel reconstruction gates.

## Verification

Follow test-driven development:

1. Add failing option/default/rendering, dependency-floor, workflow-ownership, and cross-field rejection tests, including omitted `parallel`.
2. Add failing command-rendering tests for the conditional erase/run/combine/report sequence.
3. Add a failing end-to-end scratch-consumer test whose generated gate measures subprocess-only code and produces a non-empty report.
4. Add failing migration tests that require `/python_tooling/coverage` and `/python_tooling/workflow_ownership` recognition, plus a consumer-owned workflow claim with `ownership = "consumer-owned"` and `disposition = "preserve"`.
5. Add failing release assertions for the dependency, markers, coverage settings, generated script, and preserved consumer-owned workflow.
6. Implement the schema and provider changes.
7. Regenerate package digests, catalog metadata, and payload projections.
8. Run focused Python Tooling reconstruction and release-fixture tests.
9. During atomic migration, retire only the obsolete root-script `_DOGFOOD` mapping; retain a frozen V1 bundle digest check and add current V2 root-rendering evidence.
10. Compare subprocess-aware coverage evidence with the patch disabled to demonstrate the preserved behavior.
11. Run package/graph/schema/projection gates and the optimized repository gate.

## Acceptance criteria

- Python Tooling options remain closed and fully defaulted.
- Default consumers render the same coverage run table as before.
- Opted-in consumers render `branch`, `parallel = true`, `patch = ["subprocess"]`, and `source` in canonical order.
- Opted-in dependency rendering includes `coverage[toml]>=7.10.0`; default dependency rendering remains unchanged.
- Unsupported coverage options and patch-with-false-or-omitted-parallel configurations fail before writes.
- Default generated gates remain byte-identical; parallel-aware generated gates render erase/run/combine/report in that order.
- The parallel-aware generated gate runs end to end, measures subprocess-only code, reports non-empty data, and removes input shards.
- V4 migration recognizes and preserves the coverage object and `/python_tooling/workflow_ownership` setting.
- Managed workflow ownership retains current default bytes and lifecycle behavior; consumer-owned ownership emits a preserve claim, omits the contribution, and preserves the existing workflow across migrate/reconcile/disable/re-enable.
- Consumer-owned verification skips only `.github/workflows/check.yml`; `.python-version` and `scripts/check.py` remain managed and drift-checked.
- `ci.enabled` and `ci.performance` are documented as managed-workflow-only settings and do not affect consumer-owned workflow bytes or lifecycle.
- The disposable v5 root migration retains `pytest-xdist`, all three pytest markers, both coverage settings, the optimized consumer-owned workflow, and a working parallel-aware check script.
- Atomic source-root migration retires the root-script/V1-bundle twin assertion without changing frozen V1 bytes, and proves the new root script matches current V2 rendering.
- Source and extracted-wheel behavior remain identical.
- Package integrity, payload projection, combined coverage, performance, and disposable release replay gates pass.
