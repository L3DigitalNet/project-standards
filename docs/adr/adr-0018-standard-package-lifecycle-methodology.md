---
schema_version: '1.1'
id: 'adr-0018-project-standards-standard-package-lifecycle-methodology'
title: 'ADR 0018: Standard Package Lifecycle Methodology'
description: 'Records the decision that standard package lifecycle changes are governed transitions with required cross-surface updates.'
doc_type: 'adr'
status: 'active'
created: '2026-07-09'
updated: '2026-07-18'
reviewed: '2026-07-18'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'adr'
  - 'lifecycle'
  - 'standard'
  - 'standards-platform'
aliases:
  - 'ADR 0018'
  - 'Standard package lifecycle methodology'
related:
  - 'meta/versioning.md'
  - 'standards/standard-bundle-authoring/README.md'
  - 'docs/adr/adr-0001-standard-bundle-authoring-contract.md'
  - 'docs/adr/adr-0002-manifest-first-standard-discovery.md'
  - 'docs/adr/adr-0007-standard-graph-validation-gate.md'
  - 'docs/adr/adr-0013-independent-standard-packages-and-relationship-taxonomy.md'
  - 'docs/adr/adr-0017-unified-standard-adoption-methodology.md'
  - 'docs/adr/adr-0020-standard-package-versioning-methodology.md'
  - 'docs/adr/adr-0023-unified-consumer-standards-control-plane.md'
  - 'docs/adr/adr-0024-catalog-scoped-package-version-channels.md'
  - 'docs/specs/2026-07-10-standard-bundle-authoring-v2-spec.md'
supersedes: []
superseded_by: null
source:
  - 'meta/versioning.md'
  - 'standards/standard-bundle-authoring/README.md'
  - 'docs/adr/adr-0001-standard-bundle-authoring-contract.md'
  - 'docs/adr/adr-0002-manifest-first-standard-discovery.md'
  - 'docs/adr/adr-0007-standard-graph-validation-gate.md'
  - 'docs/adr/adr-0013-independent-standard-packages-and-relationship-taxonomy.md'
  - 'docs/adr/adr-0017-unified-standard-adoption-methodology.md'
  - 'docs/adr/adr-0023-unified-consumer-standards-control-plane.md'
  - 'docs/adr/adr-0024-catalog-scoped-package-version-channels.md'
  - 'docs/specs/2026-07-10-standard-bundle-authoring-v2-spec.md'
confidence: 'high'
visibility: 'internal'
license: null
project:
  decision_makers:
    - 'chris'
  consulted: []
  informed: []
---

# ADR 0018: Standard Package Lifecycle Methodology

MADR status: **accepted**.

> **Amended by ADRs 0023 and 0024.** The lifecycle principles in this ADR remain active, but Catalog 5/V2 supersedes the original copy-adopt and adoption-mode mechanics. Package-family lifecycle (`draft`, `active`, `deprecated`, and related states) remains distinct from per-release catalog channels. Immutable payload availability and catalog role govern current consumer exposure.

## Context and Problem Statement

This repository treats standards as package families. Each family has a `standard.toml` index, immutable version payloads, resources, providers, authorities, relationships, and generated catalog visibility.

The Standard Bundle Authoring Standard already defines lifecycle states for `standard.toml`: `draft`, `review`, `active`, `deprecated`, `archived`, and `superseded`. ADR 0017 defines what an adoptable standard must expose to consumers. Those decisions still leave one operational gap: changing a standard's lifecycle can affect many surfaces at once, and today that transition can be handled inconsistently.

For example, a standard could be marked active in `standard.toml` while its README still says draft, or it could remain visible as an adoption target after deprecation. A superseded standard might name its successor in prose but not in machine-readable metadata. A draft package might accidentally appear in generated catalogs as if it were stable.

The repository needs a durable methodology for lifecycle transitions so agents, maintainers, graph validation, and future generated catalogs all interpret a package's state the same way.

This decision governs standard packages as a class. It does not decide the compatibility impact or release-version classification of a lifecycle change; that remains governed by repository versioning policy and any later per-standard compatibility ADR.

## Considered Options

- **Keep lifecycle state as descriptive metadata only** - allow each standard to explain its state in prose, with `standard.toml` as a loose label.
- **Make lifecycle transitions release-manager judgment calls** - require maintainers to coordinate affected files manually at release time without a standing package contract.
- **Treat lifecycle transitions as governed package transitions** - require each lifecycle state and transition to update the same package, consumer, and tooling surfaces consistently.

## Decision Outcome

Chosen option: **treat lifecycle transitions as governed package transitions**.

The family `standard.toml` is the canonical machine-readable lifecycle source for a standard package family. The family's mutable landing page, immutable payload documentation, catalog source and generated catalog, graph validation behavior, and release notes must agree with that lifecycle state.

The lifecycle states are:

| State | Meaning | Consumer posture |
| --- | --- | --- |
| `draft` | Work in progress; shape may change without compatibility guarantees. | Not presented as a stable adoption target. |
| `review` | Candidate standard under active review; intended shape is visible but not final. | Not presented as a stable adoption target unless an explicit review program says otherwise. |
| `active` | Released standard intended for normal downstream use. | Presented through Catalog 5 when a version is declared consumer-available. |
| `deprecated` | Still available but no longer recommended for new adoption. | Existing consumers may continue; new consumers should be pointed to replacement or migration guidance. |
| `archived` | Retained for historical reference only. | Not presented as an adoption target. |
| `superseded` | Replaced by another standard or package. | Not presented as an adoption target except as historical context; successor and migration path must be explicit. |

A lifecycle transition is complete only when every applicable surface is updated together:

- `standards/<id>/standard.toml` lifecycle state and relationships;
- family and selected-payload README status language and lifecycle/migration notes;
- selected payload adoption guidance or an explicit non-consumer availability declaration;
- `standards/README.md`, the catalog source, and generated catalog visibility;
- payload availability, package providers, reusable workflows, and enable/reconcile behavior when the package is consumer-facing;
- package tests, graph-validation expectations, and dogfood fixtures affected by the transition;
- `CHANGELOG.md`, release notes, and major-upgrade guidance when consumers must take action;
- cross-references and frontmatter relationships for any predecessor, successor, companion, or superseding standard.

Lifecycle state and catalog availability are related but separate. A family may be `draft` with a `reference-only` payload or `active` with an `internal` payload. The lifecycle state says where the family is in its maturity and retirement path; payload availability and catalog role say how, or whether, a version reaches downstream consumers. V2 does not use the V1 `copy`, `cli`, or `none` adoption-mode enum.

`active` consumer-facing standards must satisfy ADR 0023 and SPEC-BA02. ADR 0017 remains historical context for the superseded V1 adoption model. A `deprecated`, `archived`, or `superseded` standard may keep documentation and historical resources, but must not be surfaced as a recommended default. A `superseded` standard must name its successor through machine-readable relationships where the schema supports it and through human-readable migration guidance.

Exceptions to this lifecycle methodology require an ADR. A one-off README note or TODO item is not enough when a package deliberately diverges from the lifecycle contract.

### Consequences

- Good, because package maturity, adoption visibility, and generated catalog behavior have one shared interpretation.
- Good, because lifecycle changes become auditable transitions rather than scattered prose edits.
- Good, because deprecating or superseding a standard requires replacement and migration guidance instead of silent disappearance.
- Good, because draft and review standards can remain visible to maintainers without looking stable to consumers.
- Neutral, because lifecycle does not replace catalog availability, relationship taxonomy, payload manifests, or versioning policy.
- Bad, because any lifecycle transition now has a wider update checklist and may require graph/catalog/tooling changes before it is complete.

## More Information

- Standard bundle authoring contract: [`standards/standard-bundle-authoring/README.md`](../../standards/standard-bundle-authoring/README.md)
- ADR 0001, standard bundle authoring contract: [`adr-0001-standard-bundle-authoring-contract.md`](adr-0001-standard-bundle-authoring-contract.md)
- ADR 0002, manifest-first standard discovery: [`adr-0002-manifest-first-standard-discovery.md`](adr-0002-manifest-first-standard-discovery.md)
- ADR 0007, standard graph validation gate: [`adr-0007-standard-graph-validation-gate.md`](adr-0007-standard-graph-validation-gate.md)
- ADR 0013, independent standard packages and relationship taxonomy: [`adr-0013-independent-standard-packages-and-relationship-taxonomy.md`](adr-0013-independent-standard-packages-and-relationship-taxonomy.md)
- ADR 0017, superseded V1 adoption methodology: [`adr-0017-unified-standard-adoption-methodology.md`](adr-0017-unified-standard-adoption-methodology.md)
- ADR 0023, current consumer control plane: [`adr-0023-unified-consumer-standards-control-plane.md`](adr-0023-unified-consumer-standards-control-plane.md)
- ADR 0024, current package channels: [`adr-0024-catalog-scoped-package-version-channels.md`](adr-0024-catalog-scoped-package-version-channels.md)
- SPEC-BA02, current V2 authoring contract: [`../specs/2026-07-10-standard-bundle-authoring-v2-spec.md`](../specs/2026-07-10-standard-bundle-authoring-v2-spec.md)
