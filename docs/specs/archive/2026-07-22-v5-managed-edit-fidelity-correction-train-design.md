# V5 Managed-Edit Fidelity Correction Train Design

**Date:** 2026-07-22 **Status:** authored for autonomous implementation from the owner's resolve-open-issues directive; publication requires owner confirmation **Author:** Claude (Fable 5) with Chris Purcell / L3DigitalNet

## Problem and goal

Project Standards 5.6.0 leaves two consumer-facing defects, filed as GitHub issues #24 and #25 on 2026-07-22 from real consumer repositories.

- Python Tooling 1.6 `additional_source_roots` feeds the checker `include`, the Ruff `src` value, and `coverage.run.source` from one undifferentiated string list. A first-party tooling root that must be type-checked but not coverage-measured is still inexpressible: declaring it drags untested tooling into the coverage denominator and flips a green `fail_under` gate red, while omitting it re-creates the under-reported gate that issue #20 fixed. Consumers fall back to hand-maintained CLI root lists that duplicate — and can silently unscope — the declared configuration.
- When `reconcile --apply` rewrites a managed `pyproject.toml` unit addressed by a table or keyed-set scope, the TOML adapter splices the new fragment at the first owned statement and reduces every other owned statement to its extracted comments at the old byte offsets. Comments inside a multi-line managed array are displaced below the whole rewritten block, where they appear to annotate an unrelated setting; every rewritten statement also leaves its old line terminator behind as a stray blank line — one per statement, even with no comments involved. Key-scope updates are worse: interior comments in the replaced value span are silently deleted. The output parses and reconciles to `no-op`, so nothing flags the damage.

The goal is to make the checker-only tooling root declarable through a closed option and to make managed-unit rewrites preserve consumer comments at a meaningful anchor with no whitespace residue — while preserving fail-closed ownership, immutable released payloads, exact-version validation outcomes, and additive schema evolution. The corrections ship together as Project Standards 5.7.0 and close GitHub issues #24 and #25 only after publication evidence is available.

## Scope

In scope:

- author Python Tooling 1.7 whose `additional_source_roots` entries are either strings (today's both-scope meaning, unchanged) or tables `{ path = "...", coverage = false }` that join the checker `include` and Ruff `src` values but not `coverage.run.source`, recognized by the 1.6 → 1.7 and V4 legacy migrations and documented in the adoption guide;
- fix the TOML adapter so table- and keyed-set-scope updates consume the full replaced source region (statement spans, terminators, and comment-only gaps) and re-emit harvested comments above the statement with the same key or table path in the new fragment, falling back to above the whole fragment; key-scope updates re-emit interior value comments above the assignment;
- retain every predecessor package version while advancing the Python Tooling default in Catalog 5 to 1.7;
- document the comment-preservation contract for managed TOML regions;
- publish and verify Project Standards 5.7.0, then close #24 and #25 with release evidence.

Out of scope:

- changing released Python Tooling 1.6 or any other released payload bytes;
- a coverage-only root that is measured but not type-checked (not a supported gate state), and any second per-root flag beyond `coverage`;
- comment preservation changes to the YAML, JSONC, EditorConfig, Markdown, or whole-file adapters, whose update mechanics do not share the displaced-splice pattern;
- preserving consumer whitespace layout inside a rewritten managed fragment (the fragment's bytes belong to the package);
- changing REMOVE, CREATE, ADOPT, NOOP, or PRESERVE rendering behavior;
- adding new runtime dependencies or test frameworks.

## Requirements

| ID | Requirement |
| --- | --- |
| FR-001 | Python Tooling 1.7 must accept `additional_source_roots` entries that are strings or tables with a required `path` (same safe-relative-path constraints as strings) and an optional boolean `coverage` defaulting to `true`, rejecting unknown keys, and must merge every declared root into the rendered checker `include` and Ruff `src` values while merging only `coverage = true` roots into `coverage.run.source`. |
| FR-002 | With entries that are all strings (including the empty list), every Python Tooling 1.7 rendered unit must be byte-identical to Python Tooling 1.6 output for the same configuration, and a table entry with `coverage = true` must render identically to its string form. |
| FR-003 | Schema validation must reject malformed table entries — missing `path`, unknown keys, non-boolean `coverage`, and `path` values violating the string-entry pattern — before any render or write, and the provider must reject duplicate declared paths across mixed string and table forms. |
| FR-004 | The 1.6 → 1.7 package migration and the V4 legacy migration must carry `additional_source_roots` values, including table entries, into the migrated configuration unchanged. |
| FR-005 | Python Tooling 1.7 must retain the 1.6 governing-option declarations, with `additional_source_roots` still governing the checker include, Ruff, and coverage-run units. |
| FR-006 | A TOML table- or keyed-set-scope update must leave no blank-line residue: the replaced statements' full logical spans (line terminators included) and any comment-only gaps between selected statements are consumed by the rewrite. |
| FR-007 | Comments harvested from a rewritten TOML region — interior to a multi-line value, trailing an owned statement, or on their own line between owned statements — must re-emit directly above the statement whose full key or table path matches their anchor in the new fragment, and above the whole fragment when no matching statement exists; a key-scope update must re-emit interior value comments above the assignment rather than deleting them. |
| FR-008 | Rewritten output must stay idempotent: re-rendering the same change is byte-identical, and `reconcile --check` reports `no-op` immediately after an apply that preserved comments. |
| FR-009 | Catalog 5 must retain all predecessor package versions and select Python Tooling 1.7 as the compatible consumer default. |
| FR-010 | The Python Tooling 1.7 adoption guide must document the per-root table form, and the upgrade documentation must state the managed-TOML comment-preservation contract. |
| FR-011 | Project Standards 5.7.0 must be built once, verified from the extracted candidate wheel, published from `main`, and accompanied by signed immutable `v5.7.0` and moving `v5` tags plus byte-matching GitHub assets. |
| FR-012 | GitHub issues #24 and #25 must close only after the published release and supporting hosted evidence are available. |
| NFR-001 | No released payload, immutable full-version tag, historical catalog selection, or exact-version validation outcome may change; rendering may only become more faithful to consumer intent. |
| NFR-002 | Every newly expressible state is bounded by declared closed options; unknown consumer values continue to fail closed as conflicts. |
| NFR-003 | Focused regressions must demonstrate RED before implementation and GREEN afterward; release claims require fresh source, candidate-artifact, hosted-workflow, and downloaded-asset evidence. |
| NFR-004 | The train must satisfy the repository's MINOR release classification without turning a previously passing consumer outcome into a failure; comment-free rewrites change only by shedding blank-line residue. |

## Approved approach

### Python Tooling 1.7 per-root coverage scoping

Python Tooling 1.7 copies the complete 1.6 payload and changes only its config schema, provider, migrations, documentation, and integrity metadata. The `additional_source_roots` items schema becomes a `oneOf`: the existing constrained string, or an object with required `path` (same pattern), optional boolean `coverage` defaulting to `true`, and `additionalProperties: false`. One list remains the single declaration of first-party roots; the scope difference is explicit at the point of declaration.

The provider's `_source_roots` helper normalizes each entry to a `(path, coverage)` pair. Layout-derived entries stay first; declared paths follow in declared order into `include` (which feeds both checkers' `include` and Ruff `src`), and only `coverage = true` paths join the coverage `source` list. A duplicate declared path across entries — string or table — raises a validation error rather than silently resolving the conflict. String-only configurations render byte-identical 1.6 output, which keeps reconciliation quiet for every existing consumer.

The 1.7 migration set wires `python-tooling-1-6-to-1-7` and `legacy-v4-to-1-7` with the same affected-contribution surface as their 1.6 predecessors. Migrations carry the option value verbatim; no inference is added.

### TOML managed-region comment preservation

The TOML adapter's replacement path is restructured around three helpers. A collector walks the selected statements of a table- or keyed-set-scope update, harvests comment lines from each statement's full logical span and from comment-only gaps between selected statements, and anchors each comment to the statement it was attached to — its full key for assignments, its table path for headers, and the following selected statement for gap comments (a comment precedes its subject). A weaver scans the new fragment's statements and inserts each harvested comment directly above the statement with the matching anchor, or above the whole fragment when the anchor no longer exists. The rewrite then splices the woven fragment over the first selected statement's full span and consumes the remaining selected spans and comment-only gaps entirely, so no line terminators survive as blank lines.

Key-scope updates harvest interior comments from the replaced value span and insert them above the assignment line with the assignment's indentation before splicing the new value.

Woven comments become own-line consumer comments anchored above their key, so a subsequent update harvests them from the gap and re-weaves them to the same place: repeated rewrites reach a fixed point, and `reconcile --check` stays `no-op` after every apply. REMOVE keeps its existing in-place comment preservation; CREATE, ADOPT, NOOP, and PRESERVE are untouched.

### Package and release integration

Python Tooling 1.7 is an immutable full copy with updated resources and integrity inventory. The family index and Catalog 5 retain old versions and advance only the consumer default. Source payload projections are regenerated from the canonical version directory, and the rendered catalog, activation-test constants, and reconstruction tests refresh together, extending the 1.6 parity proof to 1.7.

The engine fix and successor package ship together as Project Standards 5.7.0 following the released 5.6.0 process: one candidate wheel and sdist for all artifact-sensitive checks, release commit merged from `testing` to `main`, signed `v5.7.0` and moving `v5` tags, GitHub release assets, all release-commit workflows green, downloaded-asset byte parity, `testing` synchronized, and only then issue closure.

## Alternatives rejected

1. **Split `additional_source_roots` into per-scope lists** (`additional_include_roots`, `coverage_source_roots`). Two lists let one first-party root be declared twice or drift apart; the object form keeps one declaration per root with the scope difference stated where the root is named.
2. **A `coverage_exclude_source_roots` subtraction list.** Declaring a root and then subtracting it elsewhere reads as a contradiction and spreads one intent across two options; subtraction after merge is also harder to validate closed.
3. **A second per-root flag for checker inclusion.** A coverage-only root that is not type-checked is not a supported gate state — coverage should only measure code the checker sees — and an undeclared root already expresses "neither scope".
4. **Drop managed-region comments and document the loss.** Deleting a consumer's "do not remove" note is silent data loss with a documentation apology; preservation is implementable with deterministic placement, so destruction is not the cheapest defensible option.
5. **Refuse annotated managed regions as a consumer-conflict finding.** This converts every naturally formatted consumer file into a blocked upgrade and demands manual comment relocation before each apply; it also requires a planner-visible signal and a schema revision for behavior the adapter can simply get right.
6. **Preserve comments verbatim at their original offsets.** The offsets belong to the old fragment; after a rewrite they are meaningless, which is exactly the reported displacement.

## Failure behavior

- An `additional_source_roots` table entry that is missing `path`, carries unknown keys, mistypes `coverage`, or violates the path pattern fails schema resolution before any render; a duplicate declared path fails provider validation; migration surfaces the existing `CP-MIGRATION-CONFIG` finding rather than writing.
- A consumer `include`/`src`/`source` value the merged render still cannot reproduce remains a `CP-CONSUMER-CONFLICT` carrying the governing pointer to `additional_source_roots`.
- A TOML rewrite whose woven output fails to parse raises the adapter's existing `ControlPlaneError` before any write; comment weaving cannot produce semantic change because comments are inert and the rendered value is re-validated against the declared semantic value.
- Comments in gaps containing unselected statements (interleaved unowned tables) are left untouched in place rather than guessed at.
- Any historical payload drift, package graph conflict, schema/projection drift, release-classification mismatch, failed gate, unsigned tag, failed hosted workflow, or artifact hash mismatch blocks publication or issue closure.

## Verification and acceptance

Implementation follows RED-GREEN-REFACTOR in this order:

1. Prove the TOML displacement RED with byte-exact adapter regressions — interior-array comments, own-line comments, absent-anchor fallback, key-scope interior comments, and comment-free blank-line residue — then apply the collector/weaver fix and prove GREEN plus the existing fixed-point and removal suites.
2. Reproduce issue #25 end-to-end from `init --catalog 5` through annotated apply and confirm anchored preservation with a `no-op` follow-up check.
3. Prove Python Tooling 1.6 cannot express the checker-only root, author 1.7, and prove merged rendering for mixed entries, byte-identical string-only output, schema and duplicate-path rejection, migration carriage, and 1.6/1.7 parity across the reconstruction matrix.
4. Integrate Catalog 5 (retain predecessors, advance the default), regenerate projections and the rendered catalog, and refresh activation and reconstruction constants.
5. Correct documentation: the 1.7 adoption guide's per-root form and the managed-TOML comment contract in the upgrade documentation.
6. Build the 5.7.0 wheel and sdist once, extract the wheel, and run the full repository gate — Ruff, BasedPyright, ordinary coverage, the compatibility matrix, serial performance tests, coverage reporting, dependency audit, package/graph/schema/projection gates, Prettier, markdownlint, coherence, dogfood validation, reconciliation, and release-classification checks — against that candidate.
7. Publish 5.7.0 from `main`, verify signed tags, GitHub release metadata, every release-commit workflow, and downloaded asset hashes; synchronize `testing`; close #24 and #25 with the released version and regression evidence.

Acceptance requires every FR/NFR above, exact predecessor-version proofs, a clean worktree, exact `main`/`testing`/remote parity after release, and no remaining open issue among #24/#25.
