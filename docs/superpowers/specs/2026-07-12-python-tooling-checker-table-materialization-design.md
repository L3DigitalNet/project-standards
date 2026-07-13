# Python Tooling Checker Table Materialization Design

**Date:** 2026-07-12 **Status:** owner-approved; contract audit converged after rounds 1–5 with no significant findings; oracle provisioning contract amended after plan-audit round 1 (CR-001) **Author:** Claude (Fable 5) with Chris Purcell / L3DigitalNet

## Problem and goal

Python Tooling 1.1 unconditionally declares both `table:/tool/basedpyright` and `table:/tool/pyright` contributions, and the provider renders the non-selected table with `typeCheckingMode = "off"`. BasedPyright refuses to parse a pyproject containing both tables. Verified against this branch's locked toolchain:

- basedpyright 1.39.6 exits 3 on the generated dual-table pyproject with `Pyproject file cannot have both 'pyright' and 'basedpyright' sections. pick one`, before any analysis runs.
- Removing `[tool.pyright]` alone returns the same project to exit 0.
- The rendered dev dependency is an unpinned `basedpyright`, so fresh consumers always install a current release with this behavior; no lock shields them.

Consequences: every fresh default consumer receives an invalid checker configuration; the generated `scripts/check.py` cannot pass its type-checking phase; the atomic v5 root migration would materialize the same fatal pair; parallel-coverage plan Task 9 (release replay) would fail. Selecting `pyright` repairs the CI gate — pyright ignores the unknown `[tool.basedpyright]` table — but not the editor surface, because the unconditionally recommended basedpyright extension parses the same pyproject.

The cause predates the parallel-coverage work. `MaterializationPredicate.option` accepts only a top-level option name and evaluates `config.get(option)`, while checker selection lives at `/type_checker/name`, so the payload cannot express conditional materialization for the two tables.

The goal is that exactly one checker table materializes for every schema-valid configuration, expressed declaratively in the payload, with transitions between checkers proven safe across plan, lock, migration, disable, and re-enable — without changing the consumer-facing option schema or any completed ownership-relinquishment and coverage behavior.

## Approved approach

Extend conditional materialization to accept a canonical nested option pointer in the existing predicate field.

### Predicate grammar

- `MaterializationPredicate.option` accepts either spelling: an existing top-level `OptionName`, or an absolute option pointer.
- An option pointer starts with `/`, contains two or more segments, and every segment matches the OptionName grammar `^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$`.
- A single-segment pointer (`/foo`) is noncanonical and rejected; top-level options keep their bare spelling, so every predicate has exactly one valid spelling.
- The segment grammar excludes RFC 6901 escapes (`~0`, `~1`), array indices, percent forms, and non-ASCII spellings entirely; option schemas are closed objects keyed by option names, so nothing expressible is lost.
- Operator semantics are unchanged: exactly one of `equals`/`contains`, type-exact comparison at the leaf.

### Matching semantics

- Pointer evaluation walks nested mappings segment by segment.
- An absent key or a non-mapping intermediate value yields a non-match for that predicate.
- Runtime non-match is defense in depth only. Along statically validated pointer paths, the option-schema default contract (`_validate_default_contract` plus recursive `_apply_defaults`) applies at every traversed level — the intermediate rule below restricts traversal to exactly the shapes that contract covers — so a missing target is unreachable for schema-valid consumer input.

### Static predicate validation

- Pointer grammar is pure syntax and validates during manifest model validation, which has no option-schema access.
- `load_option_schema(payload_dir, manifest)` is the authoritative cross-contract validator: every `when_any` predicate — both spellings — must name a declared property path in the closed option schema, and every non-leaf segment must traverse a direct `properties` child whose declared `type` is exactly `object`. Nullable, composed (`anyOf`/`oneOf`/`allOf`), `$ref`, and missing-type intermediates are rejected until explicit resolution semantics are designed.
- Violations fail package loading as `PC-OPTIONS` before planning or writes. Without this check, an authoring typo such as `/type_checker/nmae` would silently drop both checker tables, and the generated gate would run the checker with no configuration at all — fail-open.
- Static validation closes undeclared-path and non-total-traversal errors only. A valid path with an impossible literal (for example `equals = "basedpyrite"`) or a type-incompatible operator is not statically rejected; the mandated exactly-one-table planner proofs catch that class deterministically for Python Tooling.
- Existing shipped predicates (Agent Handoff's `startup` and `harnesses`) already conform and must continue to load unchanged.

### Python Tooling payload and provider

- `basedpyright-config` gains `when_any = [{ option = "/type_checker/name", equals = "basedpyright" }]`; `pyright-config` gains the `pyright` counterpart.
- `_checker_table` raises when asked to render a table that does not match the selected checker, so payload/engine skew fails loudly instead of emitting the fatal pair.
- The two VS Code mode keys (`basedpyright.analysis.typeCheckingMode`, `python.analysis.typeCheckingMode`) remain unconditional. In `settings.json` the inactive-checker `"off"` value is correct and desirable — it silences the non-selected language server — and namespaced settings keys carry no dual-authority conflict, unlike the pyproject tables.

### Sequencing

- Separate implementation plan; same branch and release train as the parallel-coverage design.
- Must land before parallel-coverage plan Task 9, which executes the migrated generated gate, and before the complete-gate oracle below. Coverage Tasks 7–8 do not execute the generated gate and may proceed independently.
- The parallel-coverage plan's Tasks 9 and 11 require a matching amendment for the Pyright carry-through and guarded dev-group pre-alignment defined under Release integration, plus a fresh plan audit of the amended tasks, before they execute; the prior plan audit covers only unchanged Tasks 1–8 and 10.

## Alternatives rejected

1. **Always render only `[tool.pyright]`.** Runtime-compatible with BasedPyright, but migration-unsafe: legacy consumers hold unclaimed `[tool.basedpyright]` bytes, so migration would add `[tool.pyright]` and recreate the fatal pair. It also abandons the basedpyright-specific configuration surface.
2. **Point BasedPyright at a separate `--project` configuration.** Duplicates configuration authority and breaks editor and language-server auto-discovery.
3. **Keep the narrowed coverage oracle and ship.** Hides a real shipped-package failure.
4. **Flatten `type_checker` into top-level scalar options.** Works with the existing flat predicate and avoids an engine change, but breaks the consumer-facing option schema — a versioned contract — and ripples through legacy migration mapping. The pointer extension is additive at every layer.
5. **Render empty content for the inactive table.** Requires new "empty content means absent unit" semantics across all adapters and leaves lock entries ambiguous.
6. **A distinct `option_pointer` predicate field.** Creates two valid spellings of the same predicate (`option = "startup"` versus `option_pointer = "/startup"`), violating the canonical-form discipline the contract enforces elsewhere; the overloaded field keeps the two syntaxes disjoint and unambiguous, and older engines reject pointer-bearing payloads loudly through pattern validation either way.

## Audit round 1 disposition

- **CTM-001:** Accepted. Grammar validation is syntax-only and stays in manifest model validation; `load_option_schema(payload_dir, manifest)` is the authoritative cross-contract validator, and an undeclared or structurally invalid predicate path fails package loading as `PC-OPTIONS` before planning or writes.
- **CTM-002:** Accepted. `_validate_default_contract` and `_apply_defaults` recurse only into children whose declared `type` is exactly `object`, so nullable, composed, or `$ref` intermediates escape the default contract. Every non-leaf pointer segment must now traverse a direct `properties` child with type exactly `object`; other intermediate shapes are rejected at schema load, which restores the totality argument along validated paths.
- **CTM-003:** Accepted. The Task 6 subprocess oracle hand-renders a fixed scope list and thereby omitted the second checker table. The complete-gate oracle now requires scratch control-plane initialization, actual reconciliation and apply, an exactly-one-checker-table assertion, and execution of the reconciled `scripts/check.py`.
- **CTM-004:** Accepted. `pyright` is absent from `pyproject.toml`, `uv.lock`, and the locked environment. It becomes a locked repository test dependency with a refreshed `uv.lock` so the offline oracle has a deterministic executable.
- **CTM-005:** Accepted. Verification and acceptance now require the V4-migration default proof, disable and re-enable proofs with lock assertions, second-plan convergence after each state, and at least one cycle beginning from a Pyright selection.
- **CTM-006:** Accepted. Static-validation claims are narrowed to undeclared paths and non-total traversal shapes. Literal-level validation against option enums and operator/type compatibility is an explicit non-goal; the exactly-one-table planner proofs deterministically catch an impossible literal for Python Tooling.
- **CTM-007:** Accepted. The payload projection is a path/symlink projection; the gate is `project-standards standards sync-payload-projection --check`, not content regeneration.
- **CTM-008:** Accepted. The open question is resolved as a non-goal: only regenerated schema descriptions document the widened grammar in this change; SBA prose remains untouched.

## Audit round 2 disposition

- **CTM-NEW-001:** Accepted. Python Tooling owns the whole `key:/dependency-groups/dev` unit, and the release-candidate legacy intent carries only `types-PyYAML` plus the coverage design's `pytest-xdist>=3.8`; a root-only direct Pyright dependency would conflict with or vanish from the provider-rendered dev group at migration. Pyright now flows through `additional_dev_dependencies` in both the disposable Task 9 intent and the transient Task 11 live intent, with survival assertions, a post-migration `uv.lock` refresh and check, and both oracle selections re-run after the atomic transition. The root selects BasedPyright and retains Pyright solely as the alternate-checker test dependency.
- **CTM-NEW-002:** Accepted. Verified in `_classify_desired`: with no lock entry, the planner adopts only a semantically equal pre-existing unit and otherwise emits `CP-CONSUMER-CONFLICT`; the live root dev array (`ruff>=0.14`, floorless `coverage[toml]`, different ordering, no Pyright) is not equal to the provider rendering. Tasks 9 and 11 must atomically pre-align `/dependency-groups/dev` to the exact provider-derived value before migration preview, never committing that pre-aligned legacy state separately, and prove preview applicability, migrated lock ownership, fixed-point convergence, and locked sync. A separate semantic-adoption mechanism is rejected as broader than this release needs.

## Audit round 3 disposition

- **CTM-NEW-003:** Accepted. The round-2 pre-alignment wording validated only the rewritten value and would have let an unguarded overwrite discard unexpected dependencies before preview, manufacturing adopt-equality and bypassing `CP-CONSUMER-CONFLICT`. Pre-alignment is now a guarded, bounded mutation: exact reviewed pre-write semantic value and source-byte digest preconditions, no write on any mismatch, a replacement derived through the installed provider from the pending migration config rather than a duplicated list, a rewrite of only `/dependency-groups/dev`, before/after and next-lock digest assertions, a negative drift-refusal test, and one shared guarded helper or equivalent contract for Tasks 9 and 11.
- **CTM-NEW-004:** Accepted. Ownership is now explicit: the checker implementation plan owns the predicate, schema, and provider implementation, the locked Pyright dependency, lifecycle tests, and the reconciliation-driven oracles; parallel-coverage Tasks 9 and 11 own the guarded disposable and live pre-alignment, migration intents, migrated-config assertions, lock refresh, and post-atomic oracle reruns. The parallel-coverage plan is amended before Task 9 and its amended Tasks 9 and 11 freshly audited; the prior plan audit remains valid only for unchanged Tasks 1–8 and 10.

## Audit round 4 disposition

- **CTM-NEW-005:** Accepted. Verified: the release replay starts from `copy_tracked_checkout` of the current unified root, no legacy overlay restores `pyproject.toml` or `uv.lock`, and `set_release_version` rewrites version strings in both files. A post-atomic replay would therefore hand the guard already-pre-aligned bytes — refusal breaks the replay, acceptance stops proving the guarded path. The Task 9 legacy overlay now carries frozen guarded-predecessor inputs (`pyproject.toml`, `uv.lock` — post-checker-implementation, pre-atomic, direct Pyright dependency included); post-atomic reconstruction restores those exact bytes before intent injection and pre-alignment; the proofs assert the guarded mutation actually occurs, so an already-aligned shortcut cannot pass; simulated pre-atomic and reconstructed post-atomic runs must produce equivalent release evidence; and the guard's source digest binds after `set_release_version` rewriting, so one canonical predecessor digest governs both runs (version-qualified dual digests are rejected as needless bookkeeping). The pre-alignment helper resolves the sparse migration configuration through the option schema to total effective options before invoking the render provider, since `_dependencies` requires the defaulted `type_checker`.

## Audit round 5 disposition

- **CTM-NEW-006:** Accepted. Verified: `declare_release_cut_intent` currently performs both intent injection and a hand-maintained before/after dev-group rewrite — the duplicated-list anti-pattern the round-3 contract already forbids — and the flow builds the installed distribution only afterward, so a provider-derived rewrite could not use the installed provider. The normative sequence is now: restore predecessor → set release version → build and extract the installed distribution → inject intent only → resolve options and render through that installed provider → guarded rewrite → preview/apply → refresh and check the lock. The proofs assert the rendering provider comes from the extracted installed tree, and the hand-maintained arrays are retired in favor of the guarded helper.
- **CTM-NEW-007:** Accepted. Verified: coverage-plan Task 9 Step 1 derives the overlay's required path set from every catalog-5 legacy-signature target plus `.project-standards.yml` and fails on a missing or extra entry, which would reject the new predecessor inputs. The authoritative overlay set is redefined as the exact union of the signature-target set, `.project-standards.yml`, and the guarded predecessor inputs `pyproject.toml` and `uv.lock`; the recomputation test enforces that union with no other extras.

## Contract changes

### Predicate model and generated schema

`MaterializationPredicate` in `src/project_standards/package_contract/payload.py` widens `option` to the two disjoint spellings with the grammar above, and `matches` gains nested traversal. The generated `src/project_standards/schemas/standard-payload.schema.json` is regenerated; the field description distinguishes bare top-level names from nested option pointers.

### Option-schema cross-contract validation

`load_option_schema` cross-checks every contribution and artifact `when_any` predicate against the loaded option schema's declared property paths, enforces the object-typed intermediate rule, and fails closed as `PC-OPTIONS` on any violation.

### Python Tooling 1.1 payload

`standards/python-tooling/versions/1.1/payload.toml` adds the two predicates; payload digests and catalog and family metadata are regenerated, and the payload path projection is verified with `project-standards standards sync-payload-projection --check`. The consumer-facing `config.schema.json` is byte-identical — no new options and no consumer migration.

### Provider

`standards/python-tooling/versions/1.1/providers/python_tooling.py` guards `_checker_table`. Selected-table rendering stays byte-identical to current output; the non-selected table is never rendered.

### Repository test dependencies

`pyright` becomes a pinned, locked repository test dependency — `pyproject.toml` plus a refreshed `uv.lock`. The PyPI package is a wrapper that installs its matching Pyright npm payload at runtime into a user cache outside uv's control, so the oracle contract is two-phase (amended after plan-audit round 1, CR-001): runtime provisioning (`uv run pyright --version`) is a declared setup-phase prerequisite equivalent to `uv sync` and `npm ci` — pinned wrapper version for deterministic payload content, network transport confined to environment setup, wired into CI beside dependency sync — and the oracle itself asserts the provisioned runtime, then executes the gate network-isolated (`UV_OFFLINE=1`, locked local environment). A one-time online cache warm is provisioning, never offline evidence. Before the atomic migration the root declares the dependency directly; through migration it travels as `additional_dev_dependencies` so the provider-rendered dev group retains it — see Release integration.

### Release integration

Python Tooling owns the entire `key:/dependency-groups/dev` unit, and the planner adopts a pre-existing unlocked unit only when it is semantically equal to the provider rendering — otherwise it emits `CP-CONSUMER-CONFLICT`. Two obligations follow for the parallel-coverage plan's release tasks:

- **Pyright carry-through.** The Task 9 disposable legacy intent and the Task 11 transient live intent both add `pyright` to `additional_dev_dependencies`. The release proofs assert it survives in `.standards/config.toml` and the migrated dev group, refresh and check `uv.lock` after the atomic migration, and re-run both complete-gate oracle selections after the transition. The root records BasedPyright as its selected checker and retains Pyright solely as an alternate-checker test dependency.
- **Dev-group pre-alignment (guarded).** Both release preparations pre-align `/dependency-groups/dev` through one guarded helper or an equivalent shared contract that asserts the exact reviewed pre-write semantic value and the source file's byte digest and refuses without writing on any mismatch; derives the replacement by rendering the installed provider's `key:/dependency-groups/dev` contribution from the pending migration config — never a duplicated dependency list — so adopt-equality holds by construction; rewrites only that unit; and asserts before/after semantic digests plus the next-lock digest. Unexpected dependency drift therefore refuses pre-alignment without mutation instead of being silently discarded, preserving the planner's `CP-CONSUMER-CONFLICT` protection. The pre-aligned state exists only inside the atomic release preparation, never as a separately committed legacy state, and the proofs cover migration preview applicability, migrated dev-group and lock ownership, fixed-point convergence, and a locked offline sync.

- **Guarded predecessor reconstruction.** The Task 9 legacy overlay carries frozen guarded-predecessor inputs — the post-checker-implementation, pre-atomic `pyproject.toml` and `uv.lock` bytes, direct Pyright dependency included — and the authoritative overlay path set is the exact union of the legacy-signature targets, `.project-standards.yml`, and those two predecessor inputs, enforced by the recomputation test with no other extras. Post-atomic reconstruction restores those exact bytes before intent injection and guarded pre-alignment, so the replay exercises the true predecessor rather than the already-migrated root. The normative operation sequence is: restore predecessor → set release version → build and extract the installed distribution → inject intent only → resolve options and render through that installed provider → guarded rewrite → preview/apply → refresh and check the lock; the proofs assert the rendering provider comes from the extracted installed tree, and intent injection no longer touches the dev group. The proofs assert the guarded mutation actually occurs — an already-aligned state cannot satisfy the test — and simulated pre-atomic and reconstructed post-atomic runs must produce equivalent release evidence. The guard's source digest binds after `set_release_version` rewriting, giving one canonical predecessor digest for both runs. The helper resolves the sparse migration configuration through the option schema to total effective options before invoking the render provider, because `_dependencies` requires the defaulted `type_checker`.

**Plan ownership.** The checker implementation plan owns the predicate, schema, and provider implementation, the locked Pyright dependency, the lifecycle tests, and the reconciliation-driven oracles. Parallel-coverage Tasks 9 and 11 own the guarded disposable and live pre-alignment, the frozen predecessor overlay and its post-atomic restoration, the migration intents, the migrated-config assertions, the lock refresh, and the post-atomic oracle reruns. The parallel-coverage plan is amended before Task 9, and the amended Tasks 9 and 11 receive a fresh plan audit before execution; the prior audit remains valid only for unchanged Tasks 1–8 and 10.

### Lifecycle and migration interplay

No new engine machinery is required for transitions: the planner already builds desired intents only from materialized contributions and keeps previous-lock targets in diff scope, so a checker transition removes the stale table's unit and lock entry and creates the new one through the same path as package disable. The ownership-relinquishment predicate evaluates per-target materialization and composes unchanged. The migration `affected` list retains both checker contributions as metadata; the desired tree governs actual materialization. No shipped test currently flips a `when_any` predicate between applies, so the transition proofs below are new mandatory coverage, not redundancy — and the migration and disable/re-enable promises in this section carry matching mandatory proofs of their own.

## Non-goals

- Documenting the widened predicate grammar in Standard Bundle Authoring 2.0 prose. SBA's README and templates do not document `when_any` at all today, so there is no stale author-facing text to correct; only the regenerated schema descriptions change here.
- Static validation of predicate literals against option enums or operator/type compatibility; the exactly-one-table planner proofs cover the residual class for Python Tooling.
- Any change to the consumer-facing option schema or to top-level predicate spellings and behavior.

## Files and ownership

| Surface | Responsibility |
| --- | --- |
| `src/project_standards/package_contract/payload.py` | Widened predicate grammar, nested matching, and `load_option_schema` cross-contract validation |
| `src/project_standards/schemas/standard-payload.schema.json` | Regenerated predicate contract and descriptions |
| `standards/python-tooling/versions/1.1/payload.toml` plus catalog/family metadata | Conditional checker-table declarations and integrity digests; projection gate via `sync-payload-projection --check` |
| `standards/python-tooling/versions/1.1/providers/python_tooling.py` | Selected-table-only rendering guard |
| `tests/package_contract/test_payload.py` and `tests/package_contract/test_payload_outputs.py` | Grammar, canonicality, matching, and static-validation coverage |
| `tests/control_plane/test_planner.py` and `tests/control_plane/test_lifecycle.py` | Exactly-one-table planning and checker-transition lifecycle proofs |
| `tests/package_contract/test_python_tooling_reconstruction.py` | Rendering, guard, and source/wheel reconstruction coverage |
| Reconciliation-driven complete-gate oracle beside the Task 6 subprocess oracle | Scratch control-plane apply, exactly-one-table assertion, and execution of the reconciled gate |
| `pyproject.toml` and `uv.lock` | Locked `pyright` test dependency for the offline Pyright oracle |
| `tests/package_compatibility/release_candidate.py` and `tests/package_compatibility/test_release_candidate.py` | Pyright carry-through, frozen guarded-predecessor overlay (`pyproject.toml`, `uv.lock`), and dev-group pre-alignment proofs, coordinated with coverage-plan Tasks 9 and 11 |

## Failure behavior

- A malformed, noncanonical, single-segment, escaped, indexed, or non-NFC pointer fails manifest validation before load completes.
- A well-formed predicate naming an undeclared path, or traversing a nullable, composed, `$ref`, or non-object intermediate, fails option-schema loading as `PC-OPTIONS` before planning or writes.
- At runtime, a missing pointer target or non-mapping intermediate is a non-match; along statically validated paths this state is unreachable for schema-valid configurations.
- A valid-path predicate with an impossible literal is not statically rejected; the exactly-one-table planner proofs fail instead.
- A migration intent that omits Pyright from `additional_dev_dependencies`, or a live dev group left semantically unequal to the provider rendering at migration preview, fails the release proofs with `CP-CONSUMER-CONFLICT` instead of silent adoption or replacement.
- Pre-alignment refuses without mutation when the observed dev group or source digest differs from the reviewed pre-write state; unexpected dependency drift surfaces as a refused release preparation, not a silent overwrite.
- A post-atomic replay that fails to restore the frozen predecessor bytes fails its proofs — the guard refuses the migrated bytes, and the mutation-occurred assertion rejects an already-aligned shortcut — instead of silently passing on post-migration state.
- An overlay entry outside the authoritative union — legacy-signature targets, `.project-standards.yml`, `pyproject.toml`, `uv.lock` — or a missing entry fails the overlay recomputation test.
- A guarded rewrite rendered by anything other than the provider from the extracted installed distribution, or performed before that distribution exists, fails the provenance assertion.
- The provider refuses to render a checker table that does not match the resolved selection.
- A checker transition, V4 migration, or disable/re-enable cycle that leaves a stale table, drops or retains a wrong lock entry, or fails second-plan convergence fails its lifecycle proof.
- Payload byte changes without regenerated digests fail package, graph, and source/wheel reconstruction gates; projection drift fails `sync-payload-projection --check`.
- An older engine reading a pointer-bearing payload fails loudly at predicate validation rather than mis-evaluating it.

## Verification

Follow test-driven development:

1. Add failing predicate syntax tests: canonical pointer acceptance; rejection of malformed, single-segment, escaped, indexed, and non-NFC spellings; type-sensitive `equals`/`contains` at nested leaves; missing-target and non-mapping-intermediate non-match.
2. Add failing cross-contract tests at `load_option_schema`: an undeclared path fails as `PC-OPTIONS`; nullable, composed, `$ref`, and missing-type intermediates fail; every existing shipped payload still loads.
3. Add failing planner tests: fresh apply materializes exactly one checker table for each checker selection.
4. Add failing lifecycle tests: `basedpyright → pyright → basedpyright` transitions remove the previously locked table, create and lock the newly selected table, and converge to an empty second plan after each step; disable removes the selected table and its lock unit; re-enable restores only the retained selection and converges; at least one full cycle begins from a Pyright selection.
5. Add a failing migration test: V4 migration produces only the default BasedPyright table and converges.
6. Add failing provider tests: `_checker_table` refuses the non-selected table; selected-table rendering is byte-identical to current output.
7. Implement the engine contract, cross-contract validation, payload predicates, and provider guard.
8. Add `pyright` as a locked repository test dependency and refresh `uv.lock`.
9. Regenerate the payload schema, package digests, and catalog metadata; run `sync-payload-projection --check`.
10. Add the reconciliation-driven complete-gate oracle: initialize a scratch control plane, reconcile and apply Python Tooling defaults, assert the composed pyproject contains exactly one checker table, then execute the reconciled `scripts/check.py` offline with the locked environment and pass; repeat with the Pyright selection.
11. Extend the release-candidate fixture and test in coordination with coverage-plan Tasks 9 and 11: carry `pyright` through `additional_dev_dependencies` in both intents; freeze the guarded-predecessor `pyproject.toml` and `uv.lock` bytes in the legacy overlay under the exact-union path set and restore them in post-atomic reconstruction; follow the normative sequence — restore predecessor, set release version, build and extract the installed distribution, inject intent only, resolve options and render through that installed provider, guarded rewrite, preview/apply, refresh and check the lock — asserting the provider comes from the extracted installed tree; pre-align `/dependency-groups/dev` through the guarded helper — provider-derived value from schema-resolved total options, exact pre-write value and digest preconditions bound after `set_release_version`, bounded single-unit rewrite, before/after and next-lock digest assertions, and a mutation-occurred assertion; add the negative test proving unexpected dependency drift refuses pre-alignment without mutation; prove simulated pre-atomic and reconstructed post-atomic runs produce equivalent release evidence; and prove preview applicability, migrated dev-group and lock ownership, fixed-point convergence, locked offline sync, and both oracle selections after the transition.
12. Run focused package-contract, control-plane, and Python Tooling reconstruction suites, then the repository gate.

## Acceptance criteria

- Exactly one checker table materializes for every schema-valid Python Tooling 1.1 configuration; the dual-table pair is unreachable from any accepted configuration.
- Top-level predicate spellings and behavior are unchanged; existing payloads load and evaluate identically.
- Every `when_any` path is statically proven against the closed option schema at option-schema load, including the object-typed intermediate rule.
- Checker transitions, V4 migration, and disable/re-enable cycles preserve lock integrity and second-plan convergence, including a cycle beginning from a Pyright selection.
- A reconciliation-driven scratch consumer composes exactly one checker table and passes the full reconciled gate end to end with the locked toolchain for both selections, superseding the narrowed subprocess oracle's executability boundary; that oracle remains valid for its own subprocess-coverage claim.
- The VS Code mode keys remain unconditional; the consumer-facing `config.schema.json` is byte-identical.
- All digests and generated schemas are regenerated, and `sync-payload-projection --check` passes.
- Both migration intents carry Pyright through `additional_dev_dependencies`; the migrated `.standards/config.toml`, dev group, and refreshed `uv.lock` retain it, and both oracle selections pass after the atomic transition.
- `/dependency-groups/dev` is pre-aligned through the guarded helper — provider-derived from schema-resolved total options, precondition-checked, bounded, digest-asserted — within the atomic release preparation; unexpected drift refuses without mutation; migration preview remains applicable with no `CP-CONSUMER-CONFLICT`, and the migrated unit converges to a fixed point.
- Post-atomic reconstruction restores the frozen predecessor `pyproject.toml` and `uv.lock` bytes under the exact-union overlay set, the guarded rewrite is rendered by the provider from the extracted installed distribution in the normative order, the guarded mutation provably occurs in both the simulated pre-atomic and reconstructed post-atomic runs, and both runs produce equivalent release evidence.
- The parallel-coverage plan is amended and its amended Tasks 9 and 11 freshly audited before Task 9 executes; the prior plan audit covers only unchanged Tasks 1–8 and 10.
- The change lands before parallel-coverage plan Task 9.
