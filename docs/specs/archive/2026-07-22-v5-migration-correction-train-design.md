# V5 Migration Correction Train Design

**Date:** 2026-07-22 **Status:** owner-authorized for autonomous implementation and release **Author:** Codex with Chris Purcell / L3DigitalNet

## Problem and goal

Project Standards 5.4.0 exposes three consumer-facing defects in versioned V5 surfaces.

- Markdown Tooling migration recognizes only exact historical `format.yml` bytes. A V4 consumer that followed the published opt-out and set `prettier: false` is classified as modified legacy content instead of having that supported choice translated into V5 options. Migration then reports `CP-CONSUMER-CONFLICT`, `CP-MIGRATION-LEGACY-DIGEST`, and `MT-LEGACY-MODIFIED`.
- Project Spec treats a configured but empty specification corpus as a discovery error. A fresh adopter can therefore enable the package and its CI caller before writing the first specification, yet both validation and strict lint exit 2 with `spec discovery matched no files`.
- Agent Handoff measures complete `AGENTS.md` and `CLAUDE.md` files against consumer-content budgets. The calculation includes exact managed instruction blocks contributed by Agent Handoff and other selected packages, so package adoption can make a previously compliant consumer exceed its budget without adding consumer-authored guidance.

The goal is to make all three supported adoption states safe while preserving fail-closed ownership, immutable released payloads, exact-version behavior, and the distinction between package-managed and consumer-owned content. The corrections ship together as Project Standards 5.5.0 and close GitHub issues #16, #17, and #18 only after publication evidence is available.

## Scope

In scope:

- extend the legacy-signature contract so a whole YAML or TOML file may be recognized by a canonical semantic digest while the engine retains its exact source bytes for adoption, lock construction, retirement, and replay;
- author Markdown Tooling 1.7 so the documented V4 `prettier: false` caller is recognized and migrated to `format = false` plus `ci.format_caller = false`;
- author Standard Bundle Authoring 2.4 to document semantic whole-file signature authoring and its fail-closed constraints;
- author Project Spec 1.4 so selected-package validation and linting treat a configured, valid, empty discovery result as a successful no-op;
- author Agent Handoff 1.4 so size reporting excludes only exact, lock-authenticated managed Markdown blocks and the legacy fallback excludes only its exact historical Agent Handoff block;
- retain every predecessor package version while advancing the compatible defaults in Catalog 5;
- publish and verify Project Standards 5.5.0, then close #16, #17, and #18 with release evidence.

Out of scope:

- recognizing arbitrary customized legacy workflows or inferring unbounded YAML intent;
- changing released Markdown Tooling 1.6, Project Spec 1.3, Agent Handoff 1.3, or Standard Bundle Authoring 2.3 payload bytes;
- making absent Project Spec configuration, empty include patterns, or explicit missing paths succeed;
- excluding marker-shaped instruction text that is malformed, unlocked, consumer-owned, or digest-drifted from Agent Handoff budgets;
- changing the configured byte caps or target values;
- adding a new serialization or property-testing dependency for bounded exact-shape cases.

## Requirements

| ID | Requirement |
| --- | --- |
| FR-001 | A whole-file legacy signature may opt into YAML or TOML semantic normalization; raw signatures and bounded-block signatures retain their current behavior. |
| FR-002 | Semantic normalization must reject malformed input, duplicate keys, anchors, aliases, non-string or noncanonical mapping keys, non-finite values, and other non-JSON data before provider invocation or writes. |
| FR-003 | A semantic whole-file signature must authenticate only enumerated known semantic digests while retaining the exact observed source bytes separately from the canonical signature bytes. |
| FR-004 | Markdown Tooling 1.7 must migrate the exact supported V4 `prettier: false` caller to disabled format options and converge without legacy-digest or consumer-conflict findings. |
| FR-005 | Unsupported or consumer-customized V4 format callers must remain unrecognized and fail closed without mutation. |
| FR-006 | Project Spec 1.4 selected-package `validate` and `lint --strict` must exit 0 when valid nonempty `include_patterns` match no files; JSON output must be `[]`, and human output must state that no specification files matched. |
| FR-007 | Project Spec 1.3 exact selection must retain the current empty-corpus exit-2 behavior, as must absent configuration, empty include patterns, and explicit nonexistent paths under every version. |
| FR-008 | Agent Handoff 1.4 must calculate instruction-file size after excluding exact top-level managed Markdown block envelopes whose bodies match corresponding lock-bound `markdown-block` units. |
| FR-009 | The Agent Handoff command snapshot must expose all lock-bound Markdown block units without changing the existing current-package `managed_units` meaning used by providers and verification. |
| FR-010 | Malformed, nested, duplicated, unlocked, or digest-drifted managed-block lookalikes must remain counted and must not be silently normalized or removed. |
| FR-011 | Legacy V4 size reporting must exclude only the exact historical Agent Handoff managed block delimited by its canonical legacy markers. |
| FR-012 | Catalog 5 must retain all predecessor package versions and select Markdown Tooling 1.7, Project Spec 1.4, Agent Handoff 1.4, and Standard Bundle Authoring 2.4 as compatible defaults. |
| FR-013 | Project Standards 5.5.0 must be built once, verified from the extracted candidate wheel, published from `main`, and accompanied by signed immutable `v5.5.0` and moving `v5` tags plus byte-matching GitHub assets. |
| FR-014 | GitHub issues #16, #17, and #18 must close only after the published release and supporting hosted evidence are available. |
| NFR-001 | No released payload, immutable full-version tag, historical catalog selection, or exact-version command behavior may change. |
| NFR-002 | Every newly accepted state is bounded by package-declared history or lock-authenticated ownership; unknown consumer bytes continue to fail closed or remain counted. |
| NFR-003 | Focused regressions must demonstrate RED before implementation and GREEN afterward; release claims require fresh source, candidate-artifact, hosted-workflow, and downloaded-asset evidence. |
| NFR-004 | The package additions and compatible behavior extensions must satisfy the repository's MINOR release classification without turning a previously passing consumer outcome into a failure. |

## Approved approach

### Semantic whole-file legacy signatures

The existing `LegacySignatureDeclaration.format` field becomes valid for whole-file signatures as well as bounded blocks. For a whole-file signature with `format = "yaml"` or `format = "toml"`, inspection parses the complete file using the engine's strict legacy parsers and serializes the JSON-compatible value to canonical JSON. The digest of those canonical bytes is compared with the package's enumerated `known_content_digests`.

Inspection retains two byte views and two corresponding digests:

- **source content and source digest:** the exact observed file bytes, used for historical adapter inspection, adopted lock semantic/content digests, removal-action `before_digest` values, apply preconditions, and replay;
- **signature content and signature digest:** canonical semantic bytes used only to authenticate the declared historical shape and exposed to the migration provider snapshot for an exact provider claim.

Raw whole-file signatures continue to use the same bytes for both views. Bounded-block behavior remains unchanged. A semantic digest therefore proves that the observed file represents a package-declared historical shape without falsely claiming that canonicalized bytes were present on disk.

The package contract accepts `format` on a whole-file signature but still forbids block delimiters there. Standard Bundle Authoring 2.4 documents that semantic recognition is appropriate only for closed historical YAML or TOML shapes, that every accepted semantic form must be enumerated, and that it does not authorize arbitrary consumer customization.

### Markdown Tooling 1.7 migration

Markdown Tooling 1.7 copies the complete 1.6 payload and changes only its versioned migration contract, provider, documentation, and integrity metadata. Its V4 format-caller signature uses whole-file YAML normalization and enumerates the supported enabled and disabled caller semantics from package history.

The migration provider classifies the recognized disabled semantic digest explicitly. It maps that state to both `format = false` and `ci.format_caller = false`, preventing reconciliation from recreating the caller that the consumer disabled. Recognized enabled history retains the current defaults. No content-shape heuristic is added: a different action, ref, input, job, or consumer extension has a different semantic digest and remains blocked for explicit owner disposition.

### Project Spec 1.4 empty-corpus semantics

The selected-package runtime already carries the exact installed payload version. Project Spec 1.4 uses that authority when resolving configured discovery for `validate` and `lint`:

- explicit paths continue to require regular existing files;
- selected configuration must still supply a schema-valid nonempty `include_patterns` list;
- when those patterns match zero files under version 1.4 or later in the same major line, resolution returns an empty set rather than raising `DiscoveryError`;
- version 1.3 retains the current error.

The existing set-wide runner naturally returns exit 0 and JSON `[]` for an empty result. Human mode emits one informational `OK` line stating that no specification files matched so an empty success is visible rather than silent. Provider invocation is skipped because there are no documents. `spec new` keeps its current best-effort empty-corpus behavior.

### Agent Handoff 1.4 consumer-content budgets

The Agent Handoff command adds a new snapshot collection containing every lock unit whose adapter is `markdown-block`, regardless of owning package. The existing `managed_units` collection remains restricted to Agent Handoff so no current provider contract changes meaning. The generic provider snapshot path declaration recognizes the new collection as metadata and validates its referenced targets without treating the container name as a repository path.

Agent Handoff 1.4 parses each budgeted instruction file once. A block is excludable only when all of these are true:

1. its top-level Prettier envelope has exactly one canonical `BEGIN project-standards:{namespace}` marker, one matching `END` marker, and the expected ignore envelope;
2. the envelope is neither nested, duplicated, overlapping, nor partially marked;
3. a lock unit targets that file with adapter `markdown-block` and the corresponding namespace scope;
4. the block body semantic digest equals the lock unit's semantic digest.

Qualifying envelopes, including their marker and Prettier-control lines, are removed from the byte count. All other bytes remain consumer-controlled for budgeting. Parsing uncertainty is fail-closed: the raw file length is used for any ambiguous candidate rather than subtracting bytes that may belong to the consumer.

The V4 fallback does not have a central lock. Its existing core size reporter therefore strips only one exact, well-formed block between the historical `BEGIN agent-handoff managed instructions` and matching end marker. Any malformed or multiple legacy block remains counted.

### Package and release integration

Each successor payload is an immutable full copy with updated version, documentation, provider or contract resources, manifest declarations, and integrity inventory. Family indexes and Catalog 5 retain old versions and advance only compatible defaults. Source payload projections are regenerated from canonical version directories.

The engine/schema extension and successor packages ship together as Project Standards 5.5.0. Release preparation updates the tool version, lock, changelog, current status, and deployment truth. The repository uses one candidate wheel and sdist for all artifact-sensitive checks, merges the verified release commit from `testing` to `main`, publishes signed `v5.5.0` and moving `v5` tags plus GitHub assets, waits for all release-commit workflows, downloads the assets to prove byte parity, synchronizes `testing`, and only then closes the issues.

## Alternatives rejected

1. **Enumerate exact raw `format.yml` byte variants.** This could cover the single report but would make harmless YAML whitespace, quoting, or key-order differences fail even when the closed historical meaning is identical. Semantic signatures provide the intended package-history boundary without accepting arbitrary shapes.
2. **Let the Markdown Tooling provider parse arbitrary `content_base64`.** Provider inference without a package-declared digest would bypass the engine's authentication boundary and could translate unknown consumer customization into package options.
3. **Treat empty Project Spec discovery as success for every version and configuration shape.** That rewrites immutable 1.3 behavior and makes absent or incomplete configuration pass vacuously. The change belongs to the 1.4 selected contract only.
4. **Disable the Project Spec CI caller until a spec exists.** This moves lifecycle state into consumer configuration, requires a second adoption step, and leaves the CLI's configured-empty behavior inconsistent.
5. **Subtract a fixed managed-block byte allowance.** Block sizes vary by package version, selection, and configuration. A fixed allowance can undercount consumer content or become stale.
6. **Strip every matching marker pair.** Marker text is not ownership proof. The lock and body digest are required so consumer-authored or drifted blocks remain counted.
7. **Budget only Agent Handoff's block.** Other selected packages contribute to the same instruction files, so package adoption would still consume the consumer budget.

## Failure behavior

- Invalid or ambiguous semantic YAML/TOML produces a migration finding before provider invocation or writes; unknown semantic digests retain the current modified-legacy and consumer-conflict behavior.
- A recognized semantic file whose exact bytes change between preview and apply fails the migration precondition even when its meaning is unchanged.
- A migration provider claim must match the inspected signature ID, target, known flag, and semantic digest. A mismatch remains a provider-contract failure.
- Project Spec 1.4 still exits 2 for invalid patterns, absent selection, empty pattern lists, explicit missing files, symlinked inputs, or provider/configuration errors.
- Agent Handoff counts the complete raw instruction file when managed-block parsing is ambiguous. A valid envelope with no matching lock unit, wrong adapter or scope, or wrong semantic digest remains counted.
- Any historical payload drift, package graph conflict, schema/projection drift, release-classification mismatch, failed gate, unsigned tag, failed hosted workflow, or artifact hash mismatch blocks publication or issue closure.

## Verification and acceptance

Implementation follows RED-GREEN-REFACTOR in this order:

1. Add engine contract and migration regressions for semantic whole-file YAML/TOML, raw-byte retention, malformed inputs, unknown digests, preview/apply preconditions, and unchanged raw/bounded behavior; prove the new cases fail.
2. Add the issue #16 V4 fixture and prove the disabled caller is rejected under 1.6, then author Standard Bundle Authoring 2.4 and Markdown Tooling 1.7 and prove disabled/enabled migration, convergence, and unknown-customization refusal.
3. Add version-selected empty-corpus regressions and prove 1.3 fails while the intended 1.4 behavior is absent, then author Project Spec 1.4 and prove human, JSON, validate, strict-lint, explicit-path, invalid-config, lifecycle, and installed-wheel behavior.
4. Add issue #18 fixtures containing Agent Handoff, Markdown Tooling, and Python Tooling blocks plus malformed, unlocked, and drifted lookalikes; prove the 1.3 reporter counts managed bytes, then author Agent Handoff 1.4 and the all-package lock snapshot and prove exact subtraction and fail-closed cases. Add the exact legacy-block fallback regression separately.
5. Run focused package-contract, migration, command, provider, lifecycle, catalog, source/wheel reconstruction, and coherence suites; regenerate schema and payload projections only through repository tooling.
6. Build the 5.5.0 wheel and sdist once, extract the wheel, and run Ruff, BasedPyright, ordinary coverage, the xdist compatibility matrix, serial performance tests, coverage reporting, dependency audit, package/graph/schema/projection gates, Prettier, markdownlint, coherence, dogfood validation, reconciliation, and release-classification checks against that candidate.
7. Publish 5.5.0 from `main`, verify signed tags, GitHub release metadata, every release-commit workflow, and downloaded asset hashes; synchronize `testing`; close #16, #17, and #18 with the released version and regression evidence.

Acceptance requires every FR/NFR above, exact predecessor-version proofs, a clean worktree, exact `main`/`testing`/remote parity after release, and no remaining open issue among #16/#17/#18.
