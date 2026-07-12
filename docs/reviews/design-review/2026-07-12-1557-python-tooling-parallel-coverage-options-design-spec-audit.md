# Specification Audit — Python Tooling Parallel Coverage Options Design

Audited document: `docs/superpowers/specs/2026-07-12-python-tooling-parallel-coverage-options-design.md`

## Executive summary

The specification is well-scoped, closed-schema-conscious, and correctly identifies that Python Tooling 1.1 cannot represent `[tool.coverage.run] parallel`/`patch` (confirmed: `providers/python_tooling.py:149` renders only `branch` + `source`). The core design — a closed, fully-defaulted `coverage` option with defaults that preserve current output — is sound and matches repository conventions.

However, the specification has one **blocking** defect: the new `parallel = true` / `patch = ["subprocess"]` options are incompatible with the Python Tooling package's own rendered local/CI gate, which runs `coverage run` → `coverage report` with **no `coverage combine`**. In parallel mode, coverage writes suffixed data files and `coverage report` then fails with "No data to report." This already affects this repository's dogfooded `scripts/check.py` (byte-identical twin of the adopt-bundle artifact shipped to consumers), whose pyproject already declares `parallel = true`. The specification's acceptance criteria verify only that the _bytes_ render, not that the resulting gate _works_, so they would pass while an opted-in consumer's gate is broken.

Internet research was required and performed (coverage.py `[run] patch` history and subprocess/parallel guidance). Key external finding: `[run] patch` was introduced in **coverage.py 7.10.0 (2025-07-24)**, but the provider pins `coverage[toml]` with no version floor — a `patch`-selecting consumer resolving an older coverage gets a hard config error.

## Verdict

**Needs major specification correction before planning/implementation.**

## Audit loop status

- Audit type: First audit
- Spec path: `docs/superpowers/specs/2026-07-12-python-tooling-parallel-coverage-options-design.md`
- Significant findings remaining: Yes
- Blocking issue count: 1 (SA-001)
- Non-blocking issue count: 6 (SA-002 – SA-007)

## What the specification gets right

- Correctly identifies the representational gap: `_coverage_run` (`python_tooling.py:149-151`) hard-codes `branch = true` + `source = …` and cannot emit `parallel`/`patch`. A default V5 migration would indeed drop the source checkout's settings.
- Chooses a closed, fully-defaulted option consistent with the existing schema style (`config.schema.json` uses `additionalProperties: false` and per-object `default` blocks throughout).
- Correctly decouples `pytest-xdist` from parallel coverage; the two are independent concerns and the spec keeps the xdist dependency explicit.
- The "Alternatives rejected" section is genuinely reasoned: rejecting the fixture-only patch (#3) is the right call because it would conceal, not fix, the provider gap.
- Defaults-preserve-output is the correct compatibility stance and is testable.
- The migration hook is accurately located: `run_migrate` (`python_tooling.py:614`) recognizes a fixed key set (`additional_dev_dependencies`, `ruff`, `pytest`); adding `coverage` there is the natural extension.

## Adversarial review performed

- **Requirement inventory:** enumerated the schema addition, provider rendering rules, migration recognition, disposable-fixture declarations, failure behaviors, and the eight acceptance criteria.
- **Falsification:** verified every referenced file exists (`config.schema.json`, `providers/python_tooling.py`, `payload.toml`, `tests/package_contract/test_python_tooling_reconstruction.py`, `tests/package_compatibility/release_candidate.py`, `tests/package_compatibility/test_release_candidate.py`); verified the source-checkout `[tool.coverage.run]` really declares `parallel`/`patch` (`pyproject.toml:78-82`); verified `pytest-xdist>=3.8` (`pyproject.toml:32`) and the three markers (`pyproject.toml:73-75`).
- **Blast-radius:** traced how `parallel`/`patch` interact with the package-rendered gate (`_commands`, `_local_commands`, `_workflow`, `_script`) and the adopt-bundle `check.py`.
- **Failure-mode:** tested the parallel-without-combine path and the older-coverage-version path.
- **Acceptance-criteria attack:** the criteria assert _rendered values_, not _gate operability_ — the central false positive.
- **External-assumption:** researched coverage.py `[run] patch` introduction version and subprocess/parallel/combine guidance (authoritative docs; see Internet research).
- **Minimality/maintainability:** examined the closed `patch` enum, the `_DEFAULT_CONFIG` sentinel coupling, and key-emission ordering.

Not fully checked: I did not execute any coverage run (read-only mode); the "No data to report" failure is asserted from coverage.py's documented behavior plus the provider's command sequence, not from a live run. The authoring agent should confirm with an actual run (see Recommended validation).

## Blocking issues

### SA-001: `parallel`/`patch` options break the package's own rendered coverage gate (no `coverage combine`)

- Severity: High
- Status: Confirmed
- Adversarial angle: Acceptance-criteria false positive — the criteria prove the option _renders_ but not that the resulting gate _runs_.
- Spec reference: "Approved approach"; "Provider rendering"; acceptance criteria "Opted-in consumers render `parallel = true` and `patch = ["subprocess"]`" and "Default consumers render the same coverage run table as before"; and the scoping claim under "Contract changes" that "workflow phase orchestration … remain … consumer-specific gate behavior."
- Finding: The Python Tooling package renders a local/CI gate that runs `coverage run -m pytest` immediately followed by `coverage report`, with **no `coverage combine`** and no `coverage erase`. In coverage parallel mode, `coverage run` writes suffixed data files (`.coverage.<host>.<pid>.<rand>`) rather than `.coverage`; `coverage report` then reads the (absent) `.coverage` and fails with "No data to report" (nonzero exit). The same applies to `patch = ["subprocess"]`, which coverage.py documents as _requiring_ both parallel mode and a combine step. Therefore any consumer that selects the new options **and uses the package-rendered gate** gets a broken coverage step. The specification's "Files and ownership" table does **not** list the gate-rendering surfaces (`_commands`, `_local_commands`, `_workflow`, `_script` in the provider; `scripts/check.py`; the adopt-bundle `check.py`), so the incompatibility is unaddressed. The spec's own scoping note ("orchestration … is consumer-specific") does not resolve this: the package still _ships_ a default gate that is incompatible with the package's own new option, with no warning.
- Repository evidence:
  - `standards/python-tooling/versions/1.1/providers/python_tooling.py:193-194` and `:212-213` — both `_commands` (CI) and `_local_commands` (local) emit `coverage run …` then `coverage report`, no combine.
  - `scripts/check.py:23-24` — the dogfooded/adopt-bundle gate does the same; its header (`scripts/check.py:7-11`) states it is byte-identical to `src/project_standards/bundles/python-tooling/check.py` (the artifact shipped to consumers), enforced by `test_adopt_dogfood.py`.
  - `pyproject.toml:78-82` — this repo already declares `parallel = true` and `patch = ["subprocess"]`, so `python scripts/check.py` is already latently broken here; the real gate only works because `.github/workflows/check.yml:41-43` calls `scripts/run_repository_tests.py`, which erases, runs each phase with `coverage run --parallel-mode`, then `coverage combine` before `coverage report` (`scripts/run_repository_tests.py:41,47,58,74,80-81`).
  - `rg 'combine' standards/python-tooling` returns nothing — the package has no combine step anywhere.
- External research evidence: coverage.py "Managing processes" documentation states that when measuring subprocess coverage "you will also need the parallel option to collect separate data for each process, and the `coverage combine` command to combine them together before reporting." (coverage.readthedocs.io, accessed 2026-07-12.)
- Why it matters: The option is presented as a reusable, closed _package_ option (the spec explicitly rejected a repo-only fixture patch to make it one). Offering an option that breaks the package's own default gate — with acceptance criteria that only check rendered bytes — ships a footgun and lets the release "prove" success while an opted-in consumer's gate fails. It also leaves this repository's own `scripts/check.py` inconsistent with its `pyproject.toml`.
- Recommended action for the authoring agent: Decide and specify one of:
  1. Have the package-rendered gate insert `coverage combine` (and `coverage erase`) around the report step when `coverage.parallel` is selected — and add the corresponding provider changes to the Files/ownership table; **or**
  2. Explicitly declare `parallel`/`patch` unsupported by the default gate, document in the README that selecting them requires a consumer-supplied combine step, and add an acceptance criterion asserting that behavior (plus reconcile this repo's `scripts/check.py`/pyproject inconsistency); **or**
  3. Add a rendered gate that runs `coverage run --parallel-mode` + `coverage combine` when parallel is selected, mirroring `run_repository_tests.py`. In all cases, add an acceptance criterion that proves the _coverage step succeeds_ (nonzero-line report), not merely that the table renders.
- Suggested validation (run only after implementation): in a scratch checkout with `parallel = true`, run the package-rendered gate end-to-end and confirm `coverage report` exits 0 with real data.

## Non-blocking issues

### SA-002: Premise/mechanism is imprecise — the gate forces `--parallel-mode` on the CLI

- Severity: Medium
- Status: Confirmed
- Adversarial angle: Falsifying the stated cause ("silently remove the optimization").
- Spec reference: "Problem and goal" — "Its V5 migration would therefore replace the root coverage table with the package default and silently remove the optimization."
- Finding: This repository's optimized gate passes `coverage run --parallel-mode` on the command line for every covered phase (`scripts/run_repository_tests.py:47,58,74`). The CLI flag forces parallel mode on the parent processes regardless of the pyproject setting, so removing pyproject `parallel = true` would **not** change the parent-process behavior the spec implies is at risk. The genuinely load-bearing config-file settings are: `patch = ["subprocess"]` (subprocess coverage capture, which has no CLI equivalent in the gate) and — for the suffixed/combinable naming of _subprocess_ data — `parallel = true` in the config file, because subprocess-patched coverage reads the config file, not the parent's CLI flags. The spec's conclusion (retain both settings) is likely correct, but its rationale conflates parent-process and subprocess behavior and offers no evidence of the actual before/after coverage delta.
- Repository evidence: `scripts/run_repository_tests.py:38-83` (CLI `--parallel-mode` on each phase + `combine`); `pyproject.toml:80-81`.
- External research evidence: coverage.py "Managing processes" — subprocess measurement needs the config `parallel` option and a combine step (accessed 2026-07-12).
- Why it matters: An imprecise premise can lead the authoring agent to write acceptance tests that assert the _values are present_ rather than that _subprocess coverage is actually measured and combined_, which is the behavior that would truly regress.
- Recommended action for the authoring agent: State precisely which behavior each setting preserves (patch → subprocess capture; config `parallel` → combinable suffixing of subprocess data given the CLI already forces parent parallel mode), and back the necessity claim with a measured before/after coverage total.
- Suggested validation (run only after implementation): compare `coverage report` totals with and without the two settings across the compatibility phase.

### SA-003: `patch = ["subprocess"]` requires coverage.py ≥ 7.10.0, but the provider pins no floor

- Severity: Medium
- Status: Confirmed
- Adversarial angle: External-dependency version assumption.
- Spec reference: "Approved approach" (`patch` array with `"subprocess"`); "Configuration schema".
- Finding: The `[run] patch` configuration option was introduced in **coverage.py 7.10.0 (2025-07-24)**. The Python Tooling provider declares `coverage[toml]` with no minimum version (`python_tooling.py:93`). A consumer that selects `patch = ["subprocess"]` but resolves coverage < 7.10.0 will hit a hard "unrecognized option `[run] patch=`" config error that fails _every_ coverage command, not a graceful no-op. This repo is safe today (lockfile pins coverage 7.14.1, `uv.lock:122-123`), but the option is a package-wide contract for all consumers.
- Repository evidence: `python_tooling.py:93`; `uv.lock:122-123`.
- External research evidence: coverage.py `CHANGES.rst` — "Version 7.10.0 — 2025-07-24 … A new configuration option: `[run] patch` … `patch = subprocess` measures coverage in Python subprocesses…" (github.com/nedbat/coveragepy, accessed 2026-07-12).
- Why it matters: The spec's stated goal is a _reproducible_ toolchain; shipping an option that silently depends on a recent coverage version without a floor undermines that for floorless/constrained resolutions.
- Recommended action for the authoring agent: Specify that the provider pin `coverage[toml]>=7.10.0` (unconditionally, or at least when `patch` is non-empty), and add a note/acceptance check for the version dependency.
- Suggested validation: dependency inspection of the rendered `[dependency-groups] dev`.

### SA-004: Schema permits the incoherent combination `patch = ["subprocess"]` with `parallel = false`

- Severity: Medium
- Status: Confirmed
- Adversarial angle: Internal consistency / cross-field validation gap.
- Spec reference: "Approved approach" — `parallel` and `patch` are described as independent required-defaulted fields.
- Finding: With `parallel` and `patch` as independent fields, the closed schema accepts `{ "parallel": false, "patch": ["subprocess"] }`. Coverage.py documents subprocess measurement as requiring parallel mode so per-process data files do not clobber each other; without it, subprocess and parent data collide on a single `.coverage` file. The spec does not note this coupling or forbid the combination.
- Repository evidence: `config.schema.json` object-per-field pattern (proposed `coverage` object would follow it); no cross-field constraint mechanism exists in the current schema.
- External research evidence: coverage.py "Managing processes" — "you will also need the parallel option to collect separate data for each process" (accessed 2026-07-12).
- Why it matters: A consumer could select a self-inconsistent configuration that renders and validates cleanly but produces clobbered/under-counted coverage.
- Recommended action for the authoring agent: Either document that `patch = ["subprocess"]` requires `parallel = true` (README + provider guard raising a clear error), or narrow the schema so the combination is not expressible. Note that JSON Schema draft 2020-12 can express this with `if/then` or `dependentSchemas` if a schema-level guard is preferred over a provider-level one.
- Suggested validation: negative option test asserting the incoherent combination is rejected or explicitly warned.

### SA-005: Key-emission order within `[tool.coverage.run]` is unspecified

- Severity: Low
- Status: Confirmed
- Adversarial angle: Byte-identity determinism.
- Spec reference: "Provider rendering" — "`parallel = true` is emitted only when selected", "`patch = ["subprocess"]` is emitted only when selected".
- Finding: The provider currently emits `branch` then `source` (`python_tooling.py:151`). The spec does not state where `parallel`/`patch` sit relative to those keys. Reconstruction/migration byte-identity checks depend on a fixed order, and this repo's hand-authored file uses `branch, parallel, patch, source` (`pyproject.toml:79-82`), which the composed output may not match unless specified.
- Repository evidence: `python_tooling.py:149-151`; `pyproject.toml:79-82`.
- External research evidence: Not applicable.
- Why it matters: Ambiguity here surfaces as a flaky/unspecified digest expectation during implementation.
- Recommended action for the authoring agent: State the canonical key order (e.g., `branch, parallel, patch, source`) in the contract.
- Suggested validation: reconstruction test asserting the exact rendered table bytes.

### SA-006: "immutable static resources" mischaracterizes the coverage-run surface

- Severity: Low
- Status: Confirmed
- Adversarial angle: Repository-fit precision.
- Spec reference: "Provider rendering" — "Default output remains byte-identical to the existing immutable static resources."
- Finding: `[tool.coverage.run]` is rendered as a semantic TOML contribution (`payload.toml:184-187`, scope `table:/tool/coverage/run`; provider `_render_toml` → `_coverage_run`). It is **not** one of the three immutable static whole-file resources (`.python-version`, `.github/workflows/check.yml`, `scripts/check.py`) that the `config == _DEFAULT_CONFIG` byte-identity guard protects (`python_tooling.py:343-347, 483-487, 540-544`). The default-preservation guarantee for the coverage table comes from unchanged _rendering_, not from a static-resource digest.
- Repository evidence: `payload.toml:184-187`; `python_tooling.py:343-347, 452-455`.
- External research evidence: Not applicable.
- Why it matters: Pointing the guarantee at the wrong mechanism can misdirect the implementer's test design (e.g., expecting a static-resource digest that does not exist for this table).
- Recommended action for the authoring agent: Reword to say default rendering of the `table:/tool/coverage/run` contribution is unchanged, and separately confirm the three static whole-file resources are unaffected.
- Suggested validation: reconstruction test comparing default-config coverage-run bytes to the current output.

### SA-007: `_DEFAULT_CONFIG` sentinel must be updated in lockstep with the schema default

- Severity: Low
- Status: Confirmed
- Adversarial angle: Implementation-trap / maintainability.
- Spec reference: "Files and ownership" — provider owns "Defaulting, rendering, and legacy migration".
- Finding: The provider uses a `_DEFAULT_CONFIG` dict (`python_tooling.py:325-341`) as a sentinel: for the three static whole-file targets, the byte-identity-vs-immutable-source guard only runs when `config == _DEFAULT_CONFIG` (`:483-487`, `:540-544`). If the schema gains a `coverage` default but `_DEFAULT_CONFIG` is not given the identical `coverage` entry, a pure-default consumer's resolved config will no longer equal the sentinel, silently bypassing that guard (output stays correct, but the drift assertion stops running — and any negative test that expects the guard to fire would break).
- Repository evidence: `python_tooling.py:325-341, 483-487, 540-544`.
- External research evidence: Not applicable.
- Why it matters: A non-obvious coupling in the exact file the spec changes; missing it degrades a safety check that one acceptance criterion (default byte-identity) implicitly relies on.
- Recommended action for the authoring agent: Add an explicit note that `_DEFAULT_CONFIG` must receive the new `coverage` default alongside the schema change.
- Suggested validation: unit test asserting a fully-default request still exercises the static-source equality guard.

## Missing specification considerations

- **Package gate compatibility with parallel/patch (Blocking):** the Files/ownership table omits every gate-rendering surface (`_commands`, `_local_commands`, `_workflow`, `_script`, `scripts/check.py`, adopt-bundle `check.py`). See SA-001.
- **coverage.py version floor (Non-blocking):** no requirement to pin `coverage[toml]>=7.10.0` for `patch`. See SA-003.
- **Cross-field coherence of `parallel`/`patch` (Non-blocking):** see SA-004.
- **Consumer documentation/warning (Non-blocking):** the README section is listed but the spec does not require it to warn that parallel/patch need a combine step. Fold into SA-001's option 2.
- **Migration fail-closed precision (Non-blocking):** the spec says "Modified or invalid legacy inputs continue to fail closed," but `run_migrate` copies the `coverage` blob verbatim via `_json_value` (mirroring how it treats `ruff`/`pytest`) and does not validate values; the file-digest fail-closed path (`PT-LEGACY-MODIFIED`, `python_tooling.py:644-652`) concerns _file tampering_, whereas invalid coverage _values_ are rejected later by schema validation. The spec should state where invalid `coverage` values are rejected so the fixture's "Modified or invalid legacy inputs … fail closed" assertion targets the right mechanism.

## Ambiguities and decisions needed

- **Is `parallel`/`patch` a general reusable option or effectively repo-only?**
  - Why it matters: If general (as framed), SA-001 must be resolved so opted-in consumers get a working gate. If effectively repo-only, exposing it as a closed _consumer_ option is questionable and the "reusable option" framing overstates scope.
  - Recommended clarification: State the intended consumer set and, if general, the supported gate path for parallel coverage.
  - Blocking (drives SA-001's resolution).
- **Canonical key order in `[tool.coverage.run]`.** See SA-005. Non-blocking.

## Internet research performed

- Source name: coverage.py — Managing processes (subprocess coverage)
  - URL: <https://coverage.readthedocs.io/en/latest/subprocess.html>
  - Access date: 2026-07-12
  - What it was used to verify: whether subprocess measurement requires parallel mode and a combine step.
  - Relevant conclusion: "you will also need the parallel option to collect separate data for each process, and the `coverage combine` command to combine them together before reporting." Confirms SA-001 and SA-004.
- Source name: coverage.py — Change history (`CHANGES.rst`)
  - URL: <https://github.com/nedbat/coveragepy/blob/master/CHANGES.rst>
  - Access date: 2026-07-12
  - What it was used to verify: the version that introduced the `[run] patch` option.
  - Relevant conclusion: introduced in "Version 7.10.0 — 2025-07-24." Confirms SA-003.

## Items the authoring agent should verify before correcting the specification

- Run the package-rendered gate (`scripts/check.py`) in a checkout with `parallel = true` and observe the `coverage report` "No data to report" failure firsthand (SA-001).
- Confirm the adopt-bundle `check.py` is byte-identical to `scripts/check.py` and decide whether the fix must touch both plus `_script`/`_local_commands`/`_commands`/`_workflow` (SA-001).
- Measure the coverage total with and without `patch`/config-`parallel` to prove which setting actually preserves coverage (SA-002).
- Confirm the resolved `coverage[toml]` floor and whether to pin ≥ 7.10.0 (SA-003).
- Decide whether the incoherent `patch`-without-`parallel` combination is guarded at the schema or provider layer (SA-004).
- Confirm the intended `[tool.coverage.run]` key order (SA-005).
- Confirm `_DEFAULT_CONFIG` will be updated alongside the schema default (SA-007).

## Suggested corrections for the authoring agent's specification

1. Resolve SA-001: choose combine-in-gate, documented-unsupported, or a parallel-aware rendered gate; add the affected provider/bundle surfaces to Files/ownership; add an acceptance criterion that the coverage step _succeeds_ under `parallel = true`.
2. Add a `coverage[toml]>=7.10.0` pin requirement for `patch` (SA-003).
3. Specify cross-field handling of `patch` vs `parallel` (SA-004).
4. Sharpen the problem statement to reflect the CLI `--parallel-mode` reality and identify the truly load-bearing settings with evidence (SA-002).
5. State the canonical key order in `[tool.coverage.run]` (SA-005).
6. Reword "immutable static resources" to reference the `table:/tool/coverage/run` contribution's rendering (SA-006).
7. Note the `_DEFAULT_CONFIG` lockstep requirement (SA-007).
8. Clarify where invalid legacy `coverage` values are rejected (missing-considerations).

## Read-only validation performed

- `find standards/python-tooling/versions/1.1 -type f` — confirmed `config.schema.json`, `providers/python_tooling.py`, `payload.toml`, `README.md`, and schema files exist at the spec's stated paths.
- `rg '\[tool.coverage.run\]' pyproject.toml` — confirmed the source checkout declares `branch/parallel/patch/source` (`pyproject.toml:78-82`).
- Read `providers/python_tooling.py` in full — confirmed `_coverage_run` renders only `branch`+`source`; `_commands`/`_local_commands` render `coverage run` → `coverage report` with no combine; `run_migrate` recognizes a fixed key set; `_DEFAULT_CONFIG` sentinel gates static-resource byte-identity.
- Read `config.schema.json` — confirmed closed schema, per-object defaults.
- `rg 'combine' standards/python-tooling` — confirmed no combine step in the package.
- Read `scripts/run_repository_tests.py` and `.github/workflows/check.yml` — confirmed the real gate uses CLI `--parallel-mode` + `coverage combine`.
- Read `scripts/check.py` — confirmed the byte-identical adopt-bundle twin runs `run`→`report` with no combine.
- `rg` over `payload.toml` — confirmed `coverage-run-config` contribution (`table:/tool/coverage/run`) and digest structure.
- Inspected `tests/package_contract/test_python_tooling_reconstruction.py` and `tests/package_compatibility/release_candidate.py` — confirmed current fixtures do not yet declare parallel/patch (new work) and that override-rejection tests exist.
- `rg 'coverage' uv.lock` — confirmed pinned coverage 7.14.1.

## Recommended planning/implementation validation

- `uv run project-standards validate --config .project-standards.yml` (dogfood gate).
- Focused reconstruction: `uv run pytest tests/package_contract/test_python_tooling_reconstruction.py` (run only after implementation).
- Release fixture: `uv run pytest tests/package_compatibility/test_release_candidate.py` (run only after implementation).
- Package/graph/projection/source-wheel gates and the optimized repository gate (`uv run python scripts/run_repository_tests.py`) — run only after implementation (writes coverage data).
- New: end-to-end run of the package-rendered gate under `parallel = true` asserting `coverage report` exits 0 with real data (run only after implementation).

## Final recommendation

The authoring agent should revise the specification using the findings above — principally SA-001 (the package-rendered gate cannot run parallel coverage without a combine step) — before this document is used as the basis for planning or implementation.

## Review ledger for next loop

- Spec path: `docs/superpowers/specs/2026-07-12-python-tooling-parallel-coverage-options-design.md`
- Audit round: 1
- Open issue IDs: SA-001, SA-002, SA-003, SA-004, SA-005, SA-006, SA-007
- Resolved issue IDs: none
- Superseded issue IDs: none
- Significant findings remaining: Yes
- Next audit should focus on: whether SA-001 is resolved (working gate under `parallel`/`patch`, Files/ownership updated, operability acceptance criterion added), the coverage version floor (SA-003), and the cross-field `patch`/`parallel` decision (SA-004).
