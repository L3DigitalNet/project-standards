---
schema_version: '1.1'
id: 'adr-0018-project-standards-standard-package-lifecycle-methodology'
title: 'ADR 0018: Standard Package Lifecycle Methodology'
description: 'Records the decision that standard package lifecycle changes are governed transitions with required cross-surface updates.'
doc_type: 'adr'
status: 'active'
created: '2026-07-09'
updated: '2026-07-09'
reviewed: '2026-07-09'
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

## Context and Problem Statement

This repository now treats standards as packages. Each package has a `standard.toml` manifest, an adoption posture, resources, providers, authorities, relationships, and generated index/catalog visibility.

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

`standard.toml` is the canonical machine-readable lifecycle source for a standard package. The package's human-facing documentation, adoption surface, generated indexes/catalogs, graph validation behavior, and release notes must agree with that lifecycle state.

The lifecycle states are:

| State | Meaning | Consumer posture |
| --- | --- | --- |
| `draft` | Work in progress; shape may change without compatibility guarantees. | Not presented as a stable adoption target. |
| `review` | Candidate standard under active review; intended shape is visible but not final. | Not presented as a stable adoption target unless an explicit review program says otherwise. |
| `active` | Released standard intended for normal downstream use. | Presented through the adoption surface required by ADR 0017 when its adoption mode is consumer-facing. |
| `deprecated` | Still available but no longer recommended for new adoption. | Existing consumers may continue; new consumers should be pointed to replacement or migration guidance. |
| `archived` | Retained for historical reference only. | Not presented as an adoption target. |
| `superseded` | Replaced by another standard or package. | Not presented as an adoption target except as historical context; successor and migration path must be explicit. |

A lifecycle transition is complete only when every applicable surface is updated together:

- `standards/<id>/standard.toml` lifecycle state and relationships;
- standard README status language and lifecycle/migration notes;
- `adopt.md` or the explicit non-adoptable marker required by ADR 0017;
- `standards/README.md` and any generated index or catalog visibility;
- `registry.json`, adopt CLI behavior, reusable workflows, or provider exposure when the standard is registered or adoptable through tooling;
- package tests, graph-validation expectations, and dogfood fixtures affected by the transition;
- `CHANGELOG.md`, release notes, and major-upgrade guidance when consumers must take action;
- cross-references and frontmatter relationships for any predecessor, successor, companion, or superseding standard.

Lifecycle state and adoption mode are related but separate. A standard may be `draft` with `adoption = "reference-only"`, or `active` with `adoption = "none"` when it is internal to this repository. The lifecycle state says where the package is in its maturity and retirement path; adoption mode says how, or whether, it reaches downstream consumers.

`active` consumer-facing standards must satisfy ADR 0017. A `deprecated`, `archived`, or `superseded` standard may keep documentation and historical resources, but must not be surfaced as a recommended adoption target. A `superseded` standard must name its successor through machine-readable relationships where the schema supports it and through human-readable migration guidance.

Exceptions to this lifecycle methodology require an ADR. A one-off README note or TODO item is not enough when a package deliberately diverges from the lifecycle contract.

### Consequences

- Good, because package maturity, adoption visibility, and generated catalog behavior have one shared interpretation.
- Good, because lifecycle changes become auditable transitions rather than scattered prose edits.
- Good, because deprecating or superseding a standard requires replacement and migration guidance instead of silent disappearance.
- Good, because draft and review standards can remain visible to maintainers without looking stable to consumers.
- Neutral, because lifecycle does not replace adoption mode, relationship taxonomy, artifact manifests, or versioning policy.
- Bad, because any lifecycle transition now has a wider update checklist and may require graph/catalog/tooling changes before it is complete.

## More Information

- Standard bundle authoring contract: [`standards/standard-bundle-authoring/README.md`](../../standards/standard-bundle-authoring/README.md)
- ADR 0001, standard bundle authoring contract: [`adr-0001-standard-bundle-authoring-contract.md`](adr-0001-standard-bundle-authoring-contract.md)
- ADR 0002, manifest-first standard discovery: [`adr-0002-manifest-first-standard-discovery.md`](adr-0002-manifest-first-standard-discovery.md)
- ADR 0007, standard graph validation gate: [`adr-0007-standard-graph-validation-gate.md`](adr-0007-standard-graph-validation-gate.md)
- ADR 0013, independent standard packages and relationship taxonomy: [`adr-0013-independent-standard-packages-and-relationship-taxonomy.md`](adr-0013-independent-standard-packages-and-relationship-taxonomy.md)
- ADR 0017, unified standard adoption methodology: [`adr-0017-unified-standard-adoption-methodology.md`](adr-0017-unified-standard-adoption-methodology.md)
