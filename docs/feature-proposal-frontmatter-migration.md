---
schema_version: '1.1'
id: 'concept-kvrcj7-project-standards-owned-frontmatter-schema-migration-tool'
title: 'Project Standards-owned frontmatter schema migration tool'
description: 'Starting brief for a safe adapter-driven managed frontmatter schema migration product.'
doc_type: 'concept'
status: 'draft'
created: '2026-07-31'
updated: '2026-07-31'
tags:
  - 'frontmatter'
  - 'metadata'
  - 'standard'
aliases: []
related:
  - 'docs/specs/2026-07-31-durable-document-references-optional-tooling-spec.md'
---

# Project Standards-owned frontmatter schema migration tool

The recommended product is a Project Standards-owned, adapter-driven frontmatter schema migration tool. It should complement the proposed [durable document references tooling](specs/2026-07-31-durable-document-references-optional-tooling-spec.md), not extend that tool into a second responsibility.

The following is suitable as a planned-product entry and starting brief.

## Proposed product: Managed Frontmatter Schema Migration

Provide a safe, deterministic tool for migrating a repository’s governed Markdown frontmatter from one explicitly identified document contract to another.

The product should separate:

- A generic migration engine owned by the `project-standards` wheel.
- Version-specific migration adapters shipped with the Markdown Frontmatter standard packages.
- Consumer-specific semantic decisions that remain under operator control.

A package upgrade must not automatically imply a document migration. Package versions, frontmatter `schema_version` values, and migration transitions are separate concepts.

### Recommended command surface

Candidate interface:

```text
project-standards frontmatter migrate \
  --from-schema <version> \
  --to-schema <version> \
  [--root <repo>] \
  [--json] \
  [--apply]
```

Recommended behavior:

- Without `--apply`: perform a read-only inventory and produce the complete migration plan.
- With `--apply`: recompute the plan against current bytes, repeat all safety checks, and apply it.
- A separate `--check` mode may verify that no migration remains and that the corpus conforms to the target contract.

The exact naming can change during design. The important point is to keep corpus migration separate from `reconcile`, which manages Project Standards-controlled artifacts and configuration.

## Product boundaries

### The engine owns

- Repository and corpus discovery.
- Source and target contract resolution.
- Migration-adapter selection.
- Parsing, classification, planning, safety checks, application, and reporting.
- Byte-preservation guarantees.
- Invocation of applicable post-migration validators.
- Detection of unresolved or ambiguous cases.

### The standard package owns

Each supported source-to-target transition should ship an explicit, immutable adapter describing:

- Added, removed, and renamed fields.
- Required defaults.
- Key-order changes.
- Type conversions.
- Enum additions, removals, and mappings.
- ID or relationship-format changes.
- Whether `updated` should change.
- Conditions requiring operator judgment.
- Compatibility with intermediate migrations.

Adapters should be tied to exact contract transitions, such as `1.1 → 1.2`. They should not attempt “best effort” transformation between arbitrary versions.

### The consumer/operator owns

- Selecting the target contract.
- Resolving semantic ambiguities.
- Authorizing protected-path changes.
- Updating consumer-owned generators, templates, or application code.
- Reviewing and committing the result.

## Functional requirements

### 1. Exact contract resolution

The tool must:

- Resolve immutable source and target schemas from the installed Project Standards distribution.
- Distinguish standard package version from document `schema_version`.
- Refuse unsupported transitions.
- Reject accidental downgrades unless a reversible downgrade adapter explicitly exists.
- Report a no-op when the selected standard release has no document-schema change.
- Support chained migrations only through declared intermediate edges.

No migration rule should be inferred solely by diffing two JSON Schemas. Schema differences can inform the plan, but the adapter remains authoritative because many valid transformations require semantic decisions.

### 2. Governed-corpus discovery

The tool should use the repository’s adopted configuration and standard scope rather than scanning every Markdown file indiscriminately.

It must:

- Respect configured inclusions and exclusions.
- Derive file counts dynamically.
- Use repository-relative paths in output.
- Prevent root escape and unsafe symlink traversal.
- Classify protected, excluded, generated, staging, and immutable-evidence paths.
- Refuse writes to protected paths unless the repository configuration and invocation explicitly authorize them.

For `llm-wiki`, `raw/**` must remain protected by default. A frontmatter-only migration there should require explicit operator authorization consistent with repository policy.

### 3. Complete inventory before mutation

Before offering apply, report:

- Documents by observed schema version.
- Documents already conforming to the target.
- Mechanically migratable documents.
- Documents requiring semantic review.
- Invalid or unparseable documents.
- Excluded and protected documents.
- Unknown fields and extension mappings.
- Conflicting field combinations.
- Potential ID or relationship collisions.
- Consumer-owned creation surfaces that may still emit the old schema.

Every selected document must be classified. “Skipped for an unknown reason” is not an acceptable outcome.

### 4. Versioned migration rules

Each rule should have a stable identifier and declare:

- Preconditions.
- Transformation.
- Postconditions.
- Whether it is reversible.
- Whether it is mechanical or requires an operator choice.
- Fields and value classes it can affect.
- Expected validation after application.

Prefer declarative operations for ordinary changes:

- `add`
- `remove`
- `rename`
- `move`
- `reorder`
- `set-default`
- `map-enum`
- `convert-type`

Permit a versioned implementation hook for transformations that cannot be expressed safely through declarative rules.

### 5. Ambiguity handling

The tool must never invent values for fields such as `doc_type`, `status`, ownership, or relationships.

When a required target value cannot be derived unambiguously, it must:

- Emit a blocking finding.
- Identify the document, rule, and affected field.
- List the valid target choices when available.
- Accept an explicit operator-provided mapping or decision.
- Include that decision in the resulting plan.

Apply must remain unavailable while blocking findings exist.

### 6. Preservation guarantees

The central correctness requirement is lossless migration outside the intended frontmatter edits.

The tool must:

- Preserve Markdown body bytes exactly.
- Preserve frontmatter values not targeted by a migration rule.
- Preserve nested mappings and extension fields.
- Preserve IDs and creation dates unless an adapter explicitly changes their contract.
- Avoid changing `updated` unless the transition policy requires it.
- Preserve newline convention, encoding, Unicode, and final-newline state.
- Produce minimal, reviewable diffs.

YAML comments, anchors, aliases, tags, quoting, and multiline scalar styles need an explicit design decision. Recommended policy:

- Preserve them losslessly when the chosen parser supports round trips.
- Otherwise block the affected document rather than silently discard or normalize them.

`format-frontmatter` may be reused for canonical rendering where authorized, but a schema migration must not unexpectedly reformat an entire corpus as a side effect.

### 7. Migration plan and report

The default read-only result should have both human-readable and versioned JSON forms.

The report should include:

- Resolved source and target contracts.
- Adapter identity and version.
- Repository root and selected scope.
- Per-file source hashes.
- Per-file rules to be applied.
- Semantic before/after changes without reproducing document bodies.
- Warnings and blockers.
- Aggregate counts.
- Protected and excluded paths.
- Required follow-up work.
- Expected validators and postconditions.

The JSON contract should build on the existing migration-report conventions, but the current `migrate-legacy` report should not simply be overloaded. That report concerns adoption of recognized historical package artifacts; document-schema migration needs file transformations, hashes, rule identities, and validation results.

### 8. Safe application

Apply should require explicit authorization and should:

1. Recompute the plan.
2. Verify every selected file still matches its planned hash.
3. Render and validate all proposed outputs before the first replacement.
4. Refuse to overwrite a concurrently modified target.
5. Write files through atomic per-file replacement.
6. Stop safely and report exact state if interrupted.
7. Run target validation.
8. Verify a second migration plan is empty.

The tool must not claim filesystem-level atomicity across multiple files. Recommended operational safety is:

- Permit unrelated dirty files.
- Refuse changes when any selected file has uncommitted modifications unless an explicit override is supplied.
- Never overwrite bytes that differ from the preflight hash.
- Report Git-based rollback instructions where Git is available.

A persistent in-repository migration journal should not be required for the initial release. Temporary execution state and a deterministic report are sufficient unless interruption recovery proves to require more.

### 9. Producer and template readiness

Migrating existing documents does not prevent old-schema documents from being created afterward.

The product therefore needs to distinguish:

- Standard-managed templates and skills, updated through normal Project Standards reconciliation.
- Governed Markdown documents, updated by this migration tool.
- Consumer-owned templates, generators, fixtures, and scripts, which the tool should detect or report but not rewrite as arbitrary source code.

The migration report should contain a “creation surfaces requiring review” section. The initial release may rely on explicitly configured producer paths rather than attempting broad source-code inference.

### 10. Validation integration

Recommended preconditions and postconditions include:

- Frontmatter parsing.
- Source-contract validation where possible.
- Target JSON Schema validation.
- ID validation and collision checks.
- Canonical frontmatter-format checks.
- Reference validation when relevant.
- The durable-reference checker when installed and enabled.
- Migration fixed-point verification.

The durable-reference product should remain the authority for formal document identities, links, indexes, and graph consistency. The migration engine may invoke it as a validation gate but should not duplicate its registry or reconciliation logic.

Derived consumer caches and indexes should not be silently mutated. The tool should report that they need rebuilding, or invoke a separately configured post-migration check only when that behavior is explicitly part of the repository contract.

## Required exit semantics

The CLI should provide stable, documented exit categories for:

- Migration unnecessary/current.
- Migration plan contains applicable changes.
- Blocking semantic decisions.
- Invalid source documents.
- Unsupported transition.
- Concurrent modification.
- Partial apply or interruption.
- Target validation failure.
- Invocation or configuration error.

Machine-readable output must distinguish these conditions without consumers parsing prose.

## Security and safety requirements

- No network access should be required for normal operation.
- Never emit Markdown bodies or secret-like field values into reports by default.
- Resolve all paths beneath the explicit repository root.
- Reject unsafe symlinks and path traversal.
- Bound file sizes and aggregate workload.
- Treat YAML as data; never permit executable constructors.
- Produce deterministic ordering regardless of filesystem enumeration.
- Make plan and check modes provably non-mutating.

## Minimum acceptance suite

The specification should require tests for:

- Added, removed, renamed, reordered, and type-converted fields.
- Enum mappings and ambiguous enum removals.
- Nested `project`, publication, or repository-extension mappings.
- Unknown local extension fields.
- Duplicate keys and malformed YAML.
- Comments, anchors, aliases, custom tags, and multiline scalars.
- Unicode, BOMs, CRLF/LF, missing final newlines, and embedded `---`.
- Empty bodies and large documents.
- ID and relationship collisions.
- Protected and excluded paths.
- Symlink and root-escape attempts.
- Dirty selected files versus unrelated dirty files.
- File changes between preview and apply.
- Interruption during a multi-file application.
- Deterministic JSON reports.
- Idempotent application and an empty second plan.
- Exact body-byte preservation.
- Installed-wheel and candidate-wheel behavior.
- A real-corpus dogfood migration with no hardcoded file counts.

## Initial-release scope

A useful first release should support:

- One explicit Markdown Frontmatter source-to-target transition.
- Repository-configured corpus discovery.
- Read-only inventory and plan.
- Blocking ambiguity findings.
- Explicit apply with stale-file protection.
- Lossless body preservation.
- Target validation and fixed-point verification.
- Human and JSON reports.
- Integration with existing ID, formatting, and reference validators.

This is enough to establish the architecture without prematurely building a universal migration language.

## Explicit non-goals

For the first release, exclude:

- Automatic standard adoption or selector changes.
- Automatic upgrades whenever a new package is installed.
- Arbitrary YAML or Markdown transformation.
- Editorial changes to document bodies.
- Automatic inference of semantic metadata.
- Rewriting consumer application code.
- Cross-repository fleet orchestration.
- Background watchers or services.
- A persistent reference registry.
- Link repair outside explicitly declared frontmatter-field transformations.
- Generic migration between undocumented or unknown contracts.

## Design questions to settle in the specification

The actual design should explicitly decide:

1. Whether adapters are data resources, Python providers, or a declarative core with a restricted provider escape hatch. I recommend the hybrid.
2. Whether YAML comments and scalar presentation are guaranteed to survive or cause a blocking finding.
3. How operator decisions are supplied and whether they can be saved as a reusable, reviewable mapping file.
4. Whether selected dirty files are always blocked or allowed through an explicit hash-guarded override.
5. How consumer-owned creation surfaces are declared.
6. Whether multi-edge migration runs as one reviewed plan or requires one apply per contract edge. I recommend one composed plan that retains every constituent rule identity.
7. Whether downgrades are excluded entirely from the first release. I recommend excluding them.
8. Whether `updated` reflects metadata migration time. I recommend adapter-defined behavior, defaulting to preservation.
9. Whether the command is nested under `frontmatter`, `migrate`, or a broader future migration namespace.
10. Whether the migration-report schema is extended compatibly or a dedicated document-migration-plan schema is introduced. I recommend a dedicated schema sharing common finding types.

The strongest architectural choice is the engine/adapter split: Project Standards provides one rigorously safe executor, while each frontmatter contract transition supplies the only transformations it is qualified to authorize. That gives `llm-wiki` a real G2 solution without embedding its schema history or migration mechanics inside the consumer repository.
