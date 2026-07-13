# Python Tooling Checker Table Materialization Plan Audit

## Executive summary

The plan needs major correction before execution. Its core predicate, schema-validation, payload, and provider steps align well with the approved design, but four blocking gaps make the proposed proof path unreliable: the PyPI `pyright` wrapper installs its npm payload at runtime outside `uv.lock`; the scratch `src/` project is not installed into the root environment selected by `UV_PROJECT`; the real Python Tooling lifecycle tests do not cover the required full checker transitions and disable/re-enable cycle; and the final verification set omits mandatory repository gates. One additional non-blocking gap leaves several explicitly required intermediate-schema shapes untested.

Internet research was required because the oracle depends on current uv, pytest, and Pyright wrapper behavior. The strongest stale assumption is that adding `pyright` to `uv.lock` and warming one developer cache creates a deterministic offline Pyright executable. The wrapper's own documentation says it installs the Pyright npm package at runtime into a user cache, so `UV_OFFLINE=1` does not establish that claim.

## Verdict

Needs major correction before execution

## Audit loop status

- Audit type: First audit
- Plan path: `docs/superpowers/plans/2026-07-12-python-tooling-checker-table-materialization.md`
- Significant findings remaining: Yes
- Blocking issue count: 4
- Non-blocking issue count: 1

## What the plan gets right

- The `OptionName | OptionPointer` grammar is disjoint and preserves the canonical bare spelling for top-level options.
- Cross-contract validation is correctly placed at `load_option_schema`, where both the manifest declarations and closed option schema are available.
- The provider guard and conditional payload declarations give defense in depth without changing the consumer-facing configuration schema or the unconditional VS Code mode keys.
- The plan keeps release-integration work in the parallel-coverage Tasks 9 and 11 amendment and preserves the root `.standards/` atomic-release boundary.
- The task decomposition, explicit file staging, generated-schema check, digest propagation, and handoff/TODO updates otherwise match repository conventions.

## Adversarial review performed

- Inventoried the plan's predicate grammar, traversal semantics, cross-contract validation, payload/provider changes, digest work, transition proofs, dependency changes, scratch oracle, final gate, and release ownership boundary.
- Traced current predicate evaluation and default recursion in `payload.py`, materialization filtering and previous-lock removal in `planner.py`, the Python Tooling provider, the live option schema and payload declarations, fixture construction, lifecycle helpers, migration tests, and reconstruction tests.
- Attacked the oracle under a fresh-CI model rather than the author's warmed workstation: empty Pyright runtime cache, root-selected uv environment, `src/` import behavior, and external npm access.
- Mapped the plan to the explicitly linked originating design, including its mandatory real checker lifecycle, offline complete-gate, schema-shape, and final verification obligations.
- Compared Task 6 to `AGENTS.md`, `docs/handoff/conventions.md`, and the repository's check, coherence, and graph workflows.
- Performed the external-assumption pass with official uv and pytest documentation, Microsoft's Pyright installation documentation, and the Pyright Python wrapper's authoritative repository.
- Did not run tests, generators, package-manager mutation commands, formatters, or dependency resolution because this audit is read-only and those commands can write caches or artifacts.

## Blocking issues

### CR-001: The locked Pyright dependency does not create an offline executable

- Severity: High
- Status: Confirmed
- Adversarial angle: Replayed the oracle from a fresh CI worker with no user-level Pyright npm cache instead of the locally warmed environment assumed by Task 5.
- Plan reference: Task 5 Step 1, lines 687-697; oracle environment and offline claim, lines 738-755 and 779-785.
- Finding: `uv.lock` will lock the Python wrapper, but the wrapper installs the Pyright npm package at runtime into a cache outside the uv environment. `UV_OFFLINE=1` controls uv, not npm. Running `uv run pyright --version` once during implementation only warms the author's current cache; it is not a repository artifact and is absent on a fresh CI runner. The proposed test can therefore either fail in a genuinely network-isolated environment or silently access npm while claiming to be offline.
- Repository evidence: `pyright` is currently absent from `pyproject.toml` and `uv.lock`; `.github/workflows/check.yml:29-47` performs only `uv sync` before the test runner and has no Pyright runtime-cache provisioning. The only planned cache warm is the one-off command at plan line 694. Current Node is v24.13.1, but Node availability does not supply the Pyright npm package.
- External research evidence: The [Pyright Python wrapper README](https://github.com/RobertCraigie/pyright-python) (accessed 2026-07-12) states that it checks for Node, then installs the Pyright npm package with npm and runs the downloaded JavaScript; it stores that package under a user cache. Microsoft's [Pyright installation documentation](https://github.com/microsoft/pyright/blob/main/docs/installation.md) (accessed 2026-07-12) identifies the PyPI package as a community-maintained wrapper rather than the npm distribution itself. The [uv CLI reference](https://docs.astral.sh/uv/reference/cli/) (accessed 2026-07-12) defines `UV_OFFLINE` as disabling network access for uv only.
- Why it matters: Task 5 is the plan's replacement for the known executability gap. If the alternate checker is not actually available from a fresh locked environment, the oracle is non-reproducible and the design's offline, deterministic-executable acceptance criterion remains unproven.
- Recommended action for the authoring agent: Replace the workstation-cache assumption with a repository- and CI-reproducible provisioning contract. Either lock and provision the actual Pyright runtime artifact through a mechanism that can run with outbound network disabled, or explicitly redesign the oracle and specification boundary so any online cache warm is a declared, reproducible prerequisite rather than evidence of an offline locked executable. Add the required CI/setup changes to the plan and file map.
- Suggested validation: On a fresh CI-equivalent worker with an empty `PYRIGHT_PYTHON_CACHE_DIR` and outbound network disabled, install only repository-locked dependencies and run the Pyright-selected oracle. Assert no user-home cache or npm network access is required.

### CR-002: The scratch `src/` package is not installed in the selected uv project

- Severity: High
- Status: Confirmed
- Adversarial angle: Followed Python import resolution through the exact `cwd`, `UV_PROJECT`, source layout, and test import proposed by the oracle.
- Plan reference: Task 5 Step 2, lines 709-725 and 738-777.
- Finding: The scratch test imports `consumer_pkg` from `repo/src/consumer_pkg`, but the environment sets `UV_PROJECT` to `_ROOT`. That tells every generated `uv run` command to use and synchronize the project-standards root environment, not the scratch consumer. The scratch project is never installed into that environment, and the generated pytest configuration has no `pythonpath = ["src"]`. Seeding a scratch `[project]` table does not change the selected uv project. The coverage phase is therefore expected to fail collection with `ModuleNotFoundError`, before the oracle can prove the intended gate.
- Repository evidence: The plan creates only `src/consumer_pkg` and `tests/test_consumer_pkg.py` at lines 712-725, then sets `UV_PROJECT = str(_ROOT)` at line 742. The current rendered pytest table in `standards/python-tooling/versions/1.1/providers/python_tooling.py:139-148` has `testpaths` and `addopts` but no `pythonpath`. The generated script invokes `uv run coverage run -m pytest`, and no plan step installs the scratch package or extends `PYTHONPATH`.
- External research evidence: The [uv CLI reference](https://docs.astral.sh/uv/reference/cli/) (accessed 2026-07-12) says `--project`/`UV_PROJECT` discovers and uses the project and virtual environment at the given directory while leaving relative command arguments tied to the current working directory. The [pytest good integration practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html) (accessed 2026-07-12) explain that a `src/` package is normally tested through an installed or editable install; pytest adds the tests directory for collection, not the sibling `src` directory as an import root.
- Why it matters: The plan's central end-to-end test is not executable as written. A quick workaround that drops the import would also weaken the oracle by no longer proving that the reconciled source layout is runnable.
- Recommended action for the authoring agent: Specify one coherent oracle environment. Preserve the root locked tool environment if desired, but explicitly make the scratch `src` package importable under that environment, for example through a controlled `PYTHONPATH` that the test asserts, or construct and install a locked scratch environment without violating the no-root-`.standards/` and offline constraints. State which boundary the oracle proves so root-tool reuse cannot be mistaken for a full consumer dependency installation.
- Suggested validation: Under the exact final oracle environment, run an explicit import probe for `consumer_pkg` before the generated gate, then run the full script and assert the coverage report includes the scratch source file.

### CR-003: Mandatory real checker lifecycle coverage is replaced by a generic fixture

- Severity: High
- Status: Confirmed
- Adversarial angle: Mapped every lifecycle acceptance criterion to a test operating on the real Python Tooling payload, rather than accepting generic engine behavior as package-level proof.
- Plan reference: Task 4, lines 530-671; Task 5 flip-back, lines 757-768; self-review claim, line 831.
- Finding: Task 4's full `alpha -> beta -> alpha` transition and disable/re-enable proof uses a synthetic `demo` payload. The real payload test covers only fresh exactly-one-scope planning, and the Task 5 Pyright case performs only `pyright -> basedpyright` plus convergence. No planned real-payload test performs `basedpyright -> pyright -> basedpyright`, a full cycle beginning from Pyright, or disable/re-enable while asserting the selected checker table and its exact lock unit disappear and return. This does not meet the design's mandatory checker-specific lifecycle and lock proofs.
- Repository evidence: Existing `test_python_tooling_fresh_apply_second_apply_drift_and_disable` at `tests/package_contract/test_python_tooling_reconstruction.py:703-750` disables the real package but does not re-enable it or assert checker-table lock units. Existing `test_python_tooling_real_apply_uses_selected_pyright_everywhere` at lines 753-793 performs only a fresh Pyright apply. The plan's only complete transition loop is the synthetic fixture at lines 545-621.
- External research evidence: Not applicable.
- Why it matters: The feature changes the real declaration IDs, provider rendering, semantic TOML scopes, and lock units. A generic static contribution proves planner mechanics but cannot catch payload-specific predicate, provider, scope, or lock regressions across all promised states. The originating design labels these proofs mandatory.
- Recommended action for the authoring agent: Add a real Python Tooling lifecycle test that applies BasedPyright, flips to Pyright, flips back, and checks file content, exact checker lock scopes, action kinds, and second-plan convergence at every state. Add a second real cycle beginning from Pyright, and extend the real disable/re-enable path to retain the selected configuration and prove its table and lock unit are removed and restored. Keep the generic engine test as complementary coverage.
- Suggested validation: Run the real-payload lifecycle test independently for both starting selections, then run it with the full control-plane suite and inspect the exact `next_lock.artifacts` checker scopes after every state.

### CR-004: Task 6 omits mandatory repository and package-contract gates

- Severity: High
- Status: Confirmed
- Adversarial angle: Compared the plan's claimed "full verification set" to the repository's mandatory local contracts and CI jobs, especially after adding a dependency and changing the package-contract model and payload.
- Plan reference: Task 6 Step 1, lines 796-814.
- Finding: The final set omits `uv run pip-audit`, the coherence gate (`npm ci` followed by `uv run pytest tests/coherence`), `validate-packages --json`, and `validate-graph --require-all-manifests --json`. It also omits the catalog freshness gate used by the graph workflow. `scripts/run_repository_tests.py` runs pytest phases and coverage; it does not run dependency audit or the live package/graph CLI validation. Adding `pyright` makes the missing dependency audit particularly material.
- Repository evidence: `AGENTS.md` requires pip-audit and the coherence suite before committing validator/test changes and separately requires `validate-packages`, `validate-graph`, schema generation check, and projection check for package contracts. `docs/handoff/conventions.md:52-68` repeats the pip-audit requirement. `.github/workflows/check.yml:46-47`, `.github/workflows/coherence.yml:18-33`, and `.github/workflows/validate-standards-graph.yml:30-37` run gates not present in Task 6. `scripts/run_repository_tests.py:38-83` contains only coverage/pytest/performance phases.
- External research evidence: Not applicable.
- Why it matters: The plan can report completion while a new dependency is vulnerable, the generated package graph is invalid, the catalog is stale, or the Node/Python coherence contract is broken. This violates explicit repository instructions and weakens release evidence.
- Recommended action for the authoring agent: Expand Task 6 to the complete repository-required gate, including dependency audit, package and graph validation, catalog freshness, and coherence after `npm ci`. Keep generated-schema, projection, frontmatter, root-absence, Ruff, BasedPyright, and repository-test checks. State which commands write caches/artifacts and run them only during implementation.
- Suggested validation: Execute the full expanded gate from a clean worktree, then prove `git status --short` contains only the intended implementation/documentation changes and `.standards/` remains absent.

## Non-blocking issues

### CR-005: Static-validation tests cover only one rejected intermediate shape

- Severity: Medium
- Status: Confirmed
- Adversarial angle: Compared the test matrix to every shape the design says must be rejected, not merely to the shared `child.get("type") != "object"` implementation branch.
- Plan reference: Task 2 Step 2, lines 233-313; design verification claim reflected by the self-review at line 831.
- Finding: The plan tests a nullable `type = ["object", "null"]` intermediate, but it does not test composed `anyOf`/`oneOf`/`allOf`, `$ref`, or missing-type intermediates. These are explicitly named contract boundaries in the originating design. The proposed implementation should reject them, but the plan leaves that behavior unpinned and vulnerable to later broadening of `_object_properties` or default recursion.
- Repository evidence: The current `_validate_default_contract` and `_apply_defaults` recurse only when `child.get("type") == "object"` at `src/project_standards/package_contract/payload.py:988-1014`; the proposed validator mirrors that exact-type boundary. The plan contains only the nullable rejection fixture at lines 279-304.
- External research evidence: Not applicable.
- Why it matters: The accepted design deliberately narrowed pointer traversal to the shapes covered by the engine's default contract. Missing regression cases make that safety boundary easier to loosen accidentally.
- Recommended action for the authoring agent: Parameterize the intermediate-shape rejection test across nullable type, `anyOf`, `oneOf`, `allOf`, `$ref`, and missing `type`, while retaining a positive direct-object case.
- Suggested validation: Run the focused option-schema tests and confirm each invalid shape fails through `load_option_schema` with the intended non-object-path diagnostic before planning.

## Missing considerations

- Blocking: A fresh-worker, network-disabled provenance model for the alternate checker is missing; covered by CR-001.
- Blocking: A coherent import/install boundary for the scratch `src` project is missing; covered by CR-002.
- Blocking: Real-payload transition and disable/re-enable coverage is incomplete; covered by CR-003.
- Blocking: The repository's complete required gate is not represented; covered by CR-004.
- Non-blocking: The full set of rejected intermediate-schema shapes is not pinned; covered by CR-005.

No data, authentication, secrets, production-service, networking-configuration, backup, or persistent-storage blast radius was found. The work is repository-local; its main operational risks are release-gate false positives, non-hermetic external downloads, and incomplete migration/lifecycle evidence.

## Internet research performed

- Source name: Pyright for Python repository
- URL: <https://github.com/RobertCraigie/pyright-python>
- Access date: 2026-07-12
- What it was used to verify: Runtime installation, Node selection, npm installation, and cache location of the PyPI `pyright` wrapper.
- Relevant conclusion: Installing the Python wrapper does not place the Pyright npm payload under uv lock control; the wrapper installs npm content at runtime into a user cache.

- Source name: Microsoft Pyright installation documentation
- URL: <https://github.com/microsoft/pyright/blob/main/docs/installation.md>
- Access date: 2026-07-12
- What it was used to verify: Status and installation model of the PyPI `pyright` package.
- Relevant conclusion: Microsoft documents the PyPI package as a community-maintained wrapper and the npm package as the direct CLI distribution.

- Source name: uv CLI reference and project run documentation
- URL: <https://docs.astral.sh/uv/reference/cli/>
- Access date: 2026-07-12
- What it was used to verify: `UV_PROJECT`, current-working-directory behavior, environment selection, and the scope of `UV_OFFLINE`.
- Relevant conclusion: `UV_PROJECT` selects the root project environment while relative command paths remain relative to the process working directory; `UV_OFFLINE` constrains uv rather than arbitrary subprocess package managers.

- Source name: pytest good integration practices
- URL: <https://docs.pytest.org/en/stable/explanation/goodpractices.html>
- Access date: 2026-07-12
- What it was used to verify: Import behavior and installation expectations for `src/` layout projects.
- Relevant conclusion: A `src/` package normally needs to be installed or otherwise added to the import path; test discovery does not make a sibling `src` directory importable by itself.

## Items the authoring agent should verify before correcting the plan

- Resolve the exact `pyright` Python wrapper version uv would select and confirm its npm version/cache behavior in a genuinely fresh home directory.
- Decide whether the complete-gate oracle is intended to prove only generated command/config execution with root tools or a complete installable scratch-consumer environment; state that boundary explicitly.
- Verify the chosen scratch import mechanism under the exact `UV_PROJECT`, `cwd`, and offline environment that the generated script inherits.
- Inspect the revised real-payload lock after every transition and disable/re-enable state rather than inferring it from file bytes.
- Reconcile the final gate with all current `AGENTS.md` package-contract and toolchain requirements before implementation begins.

## Suggested corrections for the authoring agent's plan

- Replace the local Pyright cache warm with a fresh-CI-reproducible, network-disabled provisioning strategy, or revise the design's offline claim before execution.
- Make `consumer_pkg` importable under the exact scratch oracle environment and state what the root-selected tool environment proves and does not prove.
- Add full real Python Tooling transition cycles from both checker selections and a real disable/re-enable lock proof.
- Expand Task 6 to include pip-audit, package validation, graph/catalog validation, and Node/Python coherence.
- Parameterize cross-contract rejection tests across every prohibited intermediate-schema shape.
- Re-audit the corrected plan before implementing it because the Pyright provisioning decision can change the file map, lock strategy, CI steps, and acceptance evidence.

## Read-only validation performed

- `git status --short --branch` and `git log -6 --oneline` in the feature worktree: confirmed branch `feature/python-tooling-parallel-coverage`, clean closeout at `0ee71e7`, plan commit `50c0776`, and design commit `c1c13e4` before this report was written.
- `git diff 50c0776..HEAD -- <plan>`: confirmed the closeout commit did not change the audited plan.
- Read the complete plan, linked design, design-review plan protocol, repository `AGENTS.md`, handoff conventions, and relevant existing design-review reports.
- Inspected `payload.py`, the generated payload schema, Python Tooling payload/config/provider, planner materialization and lock-removal paths, fixture helpers, lifecycle and migration tests, reconstruction tests, generated check script, root project metadata, lockfile, repository runner, and CI workflows with `rg`, `nl`, and `sed`.
- `node --version`, `uv --version`, and `python --version`: confirmed Node v24.13.1, uv 0.11.6, and Python 3.14.6 in the current environment; `pyright` is not currently installed in the worktree environment.
- `git diff --check`: clean before the report write.
- `test -e .standards`: confirmed `.standards/` is absent at the feature-worktree root.
- Consulted the four authoritative external sources listed above.

## Recommended implementation validation

- Run only after implementation: focused predicate and option-schema tests, including every prohibited intermediate schema shape.
- Run only after implementation: real-payload BasedPyright-to-Pyright-to-BasedPyright and Pyright-to-BasedPyright-to-Pyright lifecycle tests, plus disable/re-enable and exact lock assertions.
- Run only after implementation: the complete-gate oracle in a fresh cache/home with outbound network disabled and an explicit scratch-package import probe.
- Run only after implementation: `uv run project-standards standards validate-packages --root . --json`.
- Run only after implementation: `uv run project-standards standards validate-graph --root . --require-all-manifests --json` and the repository catalog freshness check.
- Run only after implementation: `uv run project-standards standards generate-package-schemas --root . --check` and `uv run project-standards standards sync-payload-projection --root . --check`.
- Run only after implementation: `uv run ruff format --check .`, `uv run ruff check .`, `uv run basedpyright`, `uv run python scripts/run_repository_tests.py`, and `uv run pip-audit`.
- Run only after implementation: `npm ci` followed by `uv run pytest tests/coherence -v`.
- Run only after implementation: `uv run project-standards validate --config .project-standards.yml`, the Agent Handoff validation required at closeout, `git diff --check`, and the explicit `.standards/` absence check.

## Final recommendation

The authoring agent should revise the plan using the findings above

## Review ledger for next loop

- Plan path: `docs/superpowers/plans/2026-07-12-python-tooling-checker-table-materialization.md`
- Audit round: 1
- Open issue IDs: CR-001, CR-002, CR-003, CR-004, CR-005
- Resolved issue IDs: None
- Superseded issue IDs: None
- Significant findings remaining: Yes
- Next audit should focus on: Fresh-CI Pyright provenance and true offline behavior; scratch `src` importability under the chosen uv environment; real-payload lifecycle and lock transitions from both starting selections; complete repository gate coverage; and the full rejected intermediate-schema matrix.
