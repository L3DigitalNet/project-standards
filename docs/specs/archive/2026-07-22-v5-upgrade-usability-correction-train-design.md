# V5 Upgrade Usability Correction Train Design

**Date:** 2026-07-22 **Status:** owner-authorized for autonomous implementation and release **Author:** Claude (Fable 5) with Chris Purcell / L3DigitalNet

## Problem and goal

Project Standards 5.5.0 exposes four consumer-facing defects reported from one real V4 → V5 migration. All four were filed as GitHub issues #20, #21, #22, and #23 on 2026-07-22, and the owner authorized this train's approach, scope, and release on the same day.

- Python Tooling 1.5 renders `[tool.basedpyright].include` (and the pyright equivalent) and `[tool.coverage.run].source` from `source_layout` alone. A repository whose first-party Python legitimately lives outside `src/` cannot express those roots through any declared option, so migration stops at two unresolvable `CP-CONSUMER-CONFLICT` findings and the only documented resolutions silently narrow the consumer's verification gate.
- `UPGRADING.md` § 3 presents the whole-file ownership escapes as the complete legacy-config surface and warns that unrecognized keys produce `CP-MIGRATION-UNCLAIMED-SETTING`. In fact every setting a selected package's migration provider recognizes is accepted under its legacy package namespace, and several are required to resolve `CP-CONSUMER-CONFLICT` before apply. Package adoption guides point at `.standards/config.toml`, which does not exist during migration.
- `CP-CONSUMER-CONFLICT` reports that a unit differs but never how. Both renderings omit the expected package value, the observed consumer value, and the option that governs the unit, so every conflict becomes a scratch-repository research task and the tempting resolution silently discards consumer intent.
- `project-standards init --catalog 5 --migrate` exits 1 for a blocked plan and for a fully applicable, error-free plan alike. The exit code carries no readiness signal, wrappers treat a good plan as failure, and the interactive invariant "resolve findings until the command succeeds" never terminates.

The goal is to make the blocked migration expressible, the diagnostics self-sufficient, the exit code informative, and the documentation truthful — while preserving fail-closed ownership, immutable released payloads, exact-version validation outcomes, and additive schema evolution. The corrections ship together as Project Standards 5.6.0 and close GitHub issues #20, #21, #22, and #23 only after publication evidence is available.

## Scope

In scope:

- author Python Tooling 1.6 with a closed additive `additional_source_roots` option merged into the rendered checker `include` and `coverage.run.source` values, recognized by the V4 legacy migration, and documented for the migration phase in its adoption guide;
- extend the package contract with optional per-contribution governing-option pointers, and extend `ControlFinding` and the public reconciliation-plan schema with optional expected/actual value, digest, and governing-option fields populated at both `CP-CONSUMER-CONFLICT` construction sites;
- author Standard Bundle Authoring 2.5 to document governing-option-pointer authoring and its bounded semantics;
- change the migration preview exit code to 0 for an applicable, error-free plan while blocked, refused, and errored paths remain nonzero;
- correct `UPGRADING.md` §§ 1 and 3 and `docs/usage.md` so the documented exit-code contract and legacy-config option surface match the implementation;
- retain every predecessor package version while advancing the compatible defaults in Catalog 5;
- publish and verify Project Standards 5.6.0, then close #20, #21, #22, and #23 with release evidence.

Out of scope:

- changing released Python Tooling 1.5, Standard Bundle Authoring 2.4, or any other released payload bytes;
- inferring source roots from repository content or accepting arbitrary consumer `include`/`source` values without a declared option;
- retrofitting governing-option metadata onto released payloads or claiming option knowledge where none is declared;
- carrying expected/actual raw byte contents for whole-file or byte-valued units (digests identify them instead);
- changing exit codes for apply, no-op, state-error, or reconcile paths;
- adding new runtime dependencies or test frameworks.

## Requirements

| ID | Requirement |
| --- | --- |
| FR-001 | Python Tooling 1.6 must accept a closed `additional_source_roots` option (unique, safe, relative path strings; default empty) and merge the declared roots, in declared order and deduplicated, after the layout-derived roots in both the rendered checker `include` value and the rendered `coverage.run.source` value, for both `source_layout` values and both checkers. |
| FR-002 | With `additional_source_roots` absent or empty, every Python Tooling 1.6 rendered unit must be byte-identical to Python Tooling 1.5 output for the same configuration. |
| FR-003 | Schema validation must reject absolute paths, parent traversal, empty strings, backslashes, and duplicate entries in `additional_source_roots` before any render or write. |
| FR-004 | The V4 legacy migration for Python Tooling 1.6 must recognize `/python_tooling/additional_source_roots` and carry the value into the migrated V5 configuration, so a consumer can resolve the reported include/source conflicts from `.project-standards.yml` before apply. |
| FR-005 | The package contract must accept an optional list of governing option pointers on a contribution; payloads without the field must load, plan, and verify exactly as today. |
| FR-006 | `CP-CONSUMER-CONFLICT` findings for semantic units must carry the expected package value and observed consumer value with full fidelity in JSON output and bounded truncation in human output; a JSON `null` unit value must serialize as an explicit null rather than disappearing as unset; byte-valued and whole-file conflicts must carry expected and actual content digests instead of raw bytes. |
| FR-007 | When the conflicting contribution declares governing option pointers, the finding must list them; when it declares an explicitly empty list, the finding must state that no declared option governs the unit; when the metadata is absent, the finding must omit the field without guessing. |
| FR-008 | Python Tooling 1.6 must declare governing option pointers for its option-governed `pyproject.toml` contributions, including the checker include and coverage-run units. |
| FR-009 | The public reconciliation-plan schema must gain the new optional finding fields as an additive revision with an advanced `schema_version`, regenerated through repository tooling; existing required fields and action shapes must not change. |
| FR-010 | `init --migrate` preview must exit 0 when the emitted plan is applicable and carries no error-severity finding; blocked previews, refused applies, failed applies, and state errors must retain their current nonzero codes, and apply/no-op paths must remain unchanged. |
| FR-011 | `UPGRADING.md` § 1 and `docs/usage.md` must document the corrected preview exit-code contract, and `UPGRADING.md` § 3 must document that every setting a selected package's migration provider recognizes is accepted under its legacy package namespace, with one nested example, scoping the `CP-MIGRATION-UNCLAIMED-SETTING` warning to keys no selected package recognizes. |
| FR-012 | The Python Tooling 1.6 adoption guide must state where a migrating V4 consumer sets package options before `.standards/config.toml` exists. |
| FR-013 | Standard Bundle Authoring 2.5 must document governing-option-pointer authoring, including the absent/empty/populated semantics and the prohibition on claiming options that cannot produce the unit's value. |
| FR-014 | Catalog 5 must retain all predecessor package versions and select Python Tooling 1.6 and Standard Bundle Authoring 2.5 as compatible defaults. |
| FR-015 | Project Standards 5.6.0 must be built once, verified from the extracted candidate wheel, published from `main`, and accompanied by signed immutable `v5.6.0` and moving `v5` tags plus byte-matching GitHub assets. |
| FR-016 | GitHub issues #20, #21, #22, and #23 must close only after the published release and supporting hosted evidence are available. |
| NFR-001 | No released payload, immutable full-version tag, historical catalog selection, or exact-version validation outcome may change; corrected diagnostics and exit codes may only become more informative. |
| NFR-002 | Every newly expressible state is bounded by declared closed options or declared package metadata; unknown consumer values continue to fail closed as conflicts. |
| NFR-003 | Focused regressions must demonstrate RED before implementation and GREEN afterward; release claims require fresh source, candidate-artifact, hosted-workflow, and downloaded-asset evidence. |
| NFR-004 | The train must satisfy the repository's MINOR release classification without turning a previously passing consumer outcome into a failure; the preview exit-code change converts a documented failure exit into success and newly fails no one. |

## Approved approach

### Python Tooling 1.6 additional source roots

Python Tooling 1.6 copies the complete 1.5 payload and changes only its config schema, provider, migrations, documentation, and integrity metadata. The config schema adds `additional_source_roots`: an array of unique strings with a safe-relative-path pattern and default `[]`, mirroring the existing additive options (`additional_dev_dependencies`, `ruff.extend_exclude`, `pytest.coverage_exclude_also`).

The provider's `_source_roots` helper gains the declared roots: layout-derived entries stay first, declared entries follow in declared order, and duplicates of already-present roots are skipped. The same merged lists feed the checker `include` key (basedpyright and pyright alike) and the `coverage.run.source` value, so both gate surfaces stay in lockstep by construction. An empty option renders byte-identical 1.5 output, which keeps reconciliation quiet for every existing consumer.

The 1.6 migration set wires `python-tooling-1-5-to-1-6` and `legacy-v4-to-1-6`. The legacy provider's recognized-key list adds `additional_source_roots`, so the value is claimed from the V4 YAML namespace, carried into V5 options, and covered by the existing `CP-MIGRATION-UNCLAIMED-SETTING` and `CP-MIGRATION-CONFIG` validation. No inference is added: a consumer value that still differs from the rendered merge remains a conflict.

### Governing-option pointers and conflict diagnostics

The package contract's contribution declaration gains an optional `governing_options` field: a list of option JSON pointers using the existing predicate pointer grammar. Absent metadata means unknown; an explicitly empty list is a declaration that no option can change the unit; a populated list names the options whose values feed the rendered unit. The contract validates that each pointer resolves against the payload's declared option schema, and Standard Bundle Authoring 2.5 documents the authoring rule: declare exactly the options that can change the rendered value, or an empty list for fixed units.

`ControlFinding` gains optional `expected`, `actual`, `expected_digest`, `actual_digest`, and `governing_options` fields, all omitted from JSON when unset. The semantic-unit planner site populates values (when JSON-representable) plus semantic digests and the owning contribution's declared pointers; the whole-file adapter site populates content digests only. Human rendering appends bounded, single-line expected/actual excerpts and the governing-option list to the existing finding format; JSON keeps full fidelity. The pydantic `PublicFindingSchema` gains the same optional fields, the embedded reconciliation-plan `schema_version` advances to `1.1`, and the generated JSON schema is regenerated through repository tooling. Python Tooling 1.6 declares pointers for its option-governed `pyproject.toml` contributions, so the exact conflicts reported in issue #20 become one-edit resolutions.

### Migration preview exit code

`_emit_migration_plan` returns 0 when the emitted plan is applicable — which by construction already implies no error-severity findings — and the invocation is not a refused apply; every other path keeps its current code. The JSON `ok`/`applicable` fields and the exit code therefore agree. Pinned tests move from asserting the old constant to asserting the readiness distinction: blocked preview 1, ready preview 0, refused apply 1, successful apply 0, no-op 0, state error 2.

### Documentation corrections

`docs/usage.md` replaces "Migration preview always exits 1 because it is an actionable, unapplied plan" with the readiness contract. `UPGRADING.md` § 1 documents the same contract beside the preview workflow. § 3 states that any setting a selected package's migration provider recognizes may be set under its legacy package namespace in `.project-standards.yml`, shows one nested example (`python_tooling.ruff.extend_exclude`), keeps the ownership-escape list as the whole-file subset, and scopes the `CP-MIGRATION-UNCLAIMED-SETTING` warning to keys no selected package recognizes. The Python Tooling 1.6 `adopt.md` troubleshooting section adds the migration-phase pointer required by FR-012; released adoption guides stay untouched.

### Package and release integration

Each successor payload is an immutable full copy with updated resources and integrity inventory. Family indexes and Catalog 5 retain old versions and advance only compatible defaults: Python Tooling 1.6 as the consumer default (MINOR) and Standard Bundle Authoring 2.5 as the internal authoring default (PATCH-classified additive internal entry). Source payload projections are regenerated from canonical version directories, and the rendered catalog, activation-test constants, and reconstruction tests refresh together.

The engine/schema extension and successor packages ship together as Project Standards 5.6.0 following the released 5.5.0 process: one candidate wheel and sdist for all artifact-sensitive checks, release commit merged from `testing` to `main`, signed `v5.6.0` and moving `v5` tags, GitHub release assets, all release-commit workflows green, downloaded-asset byte parity, `testing` synchronized, and only then issue closure.

## Alternatives rejected

1. **Narrow `coverage.run` ownership to canonical keys and treat `source` as extendable.** This resolves only half the report (the checker `include` key is already canonical), splits one logical option across two mechanisms, and weakens the managed-table contract without making the intent expressible. A single closed additive option covers both units symmetrically.
2. **Accept the consumer's existing `include`/`source` values when they are a superset of the rendered value.** Superset acceptance is inference: it would bless drift and typos as intent and break the fail-closed conflict boundary. Intent must be declared through an option.
3. **Document the current always-1 preview exit instead of changing it.** The gap is not only documentation: wrappers and CI gates genuinely cannot distinguish ready from blocked without parsing JSON, and the "pending plan" reading already conflicts with `ok: true`. Aligning the exit code with `applicable` is strictly more informative and newly fails no consumer.
4. **Carry raw expected/actual bytes on whole-file conflicts.** File contents can be large or binary and are already obtainable from the plan's action stream; digests identify the mismatch without bloating findings or leaking content into logs.
5. **Derive the governing option from `when_any` predicates.** Those predicates gate whether a contribution materializes, not which option renders its value; deriving would misname options and cannot express "no option governs this unit". Explicit declaration keeps the claim truthful and additive.
6. **Ship the diagnostics without a schema-version advance.** `additionalProperties: false` makes new finding fields a schema change; consumers pin to tags and deserve an explicit additive revision marker rather than a silent shape change.
7. **Patch `UPGRADING.md` § 3 by enumerating every package option inline.** The list would go stale with every package release; pointing at each package's declared migration surface keeps one source of truth.

## Failure behavior

- An `additional_source_roots` entry that is absolute, traversing, empty, duplicated, or non-string fails schema resolution before any render; migration surfaces the existing `CP-MIGRATION-CONFIG` finding rather than writing.
- A consumer `include`/`source` value that the merged render still cannot reproduce remains a `CP-CONSUMER-CONFLICT`, now carrying expected/actual values and the governing pointer to `additional_source_roots`.
- A declared governing-option pointer that does not resolve against the payload's option schema fails package-contract validation at load, blocking the payload rather than emitting wrong guidance.
- Findings for payloads without governing-option metadata omit the field entirely; no heuristic fills it.
- A blocked migration preview, refused apply, failed apply, and state error keep exit codes 1, 1, 1, and 2 respectively; only the applicable, error-free preview changes to 0.
- Any historical payload drift, package graph conflict, schema/projection drift, release-classification mismatch, failed gate, unsigned tag, failed hosted workflow, or artifact hash mismatch blocks publication or issue closure.

## Verification and acceptance

Implementation follows RED-GREEN-REFACTOR in this order:

1. Add contract regressions for `governing_options` (absent, empty, populated, unresolvable pointer) and finding-field serialization; prove the new cases fail.
2. Add the issue #20 fixture and prove Python Tooling 1.5 cannot express the second root, then author Python Tooling 1.6 and prove merged rendering, byte-identical empty-option output, schema rejection cases, legacy recognition, and end-to-end migration resolution of the reported conflict pair.
3. Prove the two `CP-CONSUMER-CONFLICT` sites emit enriched findings (values, digests, pointers, empty-declaration hint, absent-metadata omission) in JSON and truncated human form, and regenerate the reconciliation-plan schema at `1.1`.
4. Prove the preview exit-code matrix RED under the current constant, then apply the `_emit_migration_plan` change and update the pinned CLI and migration tests.
5. Author Standard Bundle Authoring 2.5, correct `UPGRADING.md` and `docs/usage.md`, and verify the documentation gate.
6. Integrate Catalog 5 (retain predecessors, advance defaults), regenerate projections and the rendered catalog, and refresh activation and reconstruction test constants.
7. Build the 5.6.0 wheel and sdist once, extract the wheel, and run Ruff, BasedPyright, ordinary coverage, the compatibility matrix, serial performance tests, coverage reporting, dependency audit, package/graph/schema/projection gates, Prettier, markdownlint, coherence, dogfood validation, reconciliation, and release-classification checks against that candidate.
8. Publish 5.6.0 from `main`, verify signed tags, GitHub release metadata, every release-commit workflow, and downloaded asset hashes; synchronize `testing`; close #20, #21, #22, and #23 with the released version and regression evidence.

Acceptance requires every FR/NFR above, exact predecessor-version proofs, a clean worktree, exact `main`/`testing`/remote parity after release, and no remaining open issue among #20/#21/#22/#23.
