---
schema_version: '1.1'
id: 'adr-0020-project-standards-standard-package-versioning-methodology'
title: 'ADR 0020: Standard Package Versioning Methodology'
description: 'Records the decision that every standard package declares package versions, while consumer-selectable contract versions remain explicit registry metadata.'
doc_type: 'adr'
status: 'superseded'
created: '2026-07-09'
updated: '2026-07-10'
reviewed: '2026-07-10'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'adr'
  - 'standard'
  - 'standards-platform'
  - 'versioning'
aliases:
  - 'ADR 0020'
  - 'Standard package versioning methodology'
related:
  - 'meta/versioning.md'
  - 'standards/standard-bundle-authoring/README.md'
  - 'docs/adr/adr-0001-standard-bundle-authoring-contract.md'
  - 'docs/adr/adr-0002-manifest-first-standard-discovery.md'
  - 'docs/adr/adr-0007-standard-graph-validation-gate.md'
  - 'docs/adr/adr-0008-consumer-config-namespace-registry.md'
  - 'docs/adr/adr-0013-independent-standard-packages-and-relationship-taxonomy.md'
  - 'docs/adr/adr-0017-unified-standard-adoption-methodology.md'
  - 'docs/adr/adr-0018-standard-package-lifecycle-methodology.md'
  - 'docs/adr/adr-0019-packaged-artifact-parity-and-provenance.md'
  - 'docs/adr/adr-0021-standard-packaged-skill-installation-methodology.md'
  - 'docs/adr/adr-0024-catalog-scoped-package-version-channels.md'
supersedes: []
superseded_by: 'adr-0024-project-standards-catalog-scoped-package-version-channels'
source:
  - 'meta/versioning.md'
  - 'standards/standard-bundle-authoring/README.md'
  - 'docs/adr/adr-0001-standard-bundle-authoring-contract.md'
  - 'docs/adr/adr-0002-manifest-first-standard-discovery.md'
  - 'docs/adr/adr-0007-standard-graph-validation-gate.md'
  - 'docs/adr/adr-0008-consumer-config-namespace-registry.md'
  - 'docs/adr/adr-0013-independent-standard-packages-and-relationship-taxonomy.md'
  - 'docs/adr/adr-0017-unified-standard-adoption-methodology.md'
  - 'docs/adr/adr-0018-standard-package-lifecycle-methodology.md'
  - 'docs/adr/adr-0019-packaged-artifact-parity-and-provenance.md'
confidence: 'high'
visibility: 'internal'
license: null
project:
  decision_makers:
    - 'chris'
  consulted: []
  informed: []
---

# ADR 0020: Standard Package Versioning Methodology

MADR status: **superseded** by [ADR 0024](adr-0024-catalog-scoped-package-version-channels.md).

## Context and Problem Statement

This repository treats standards as packages. A standard package has a `standard.toml` manifest, lifecycle state, adoption posture, package resources, optional packaged artifacts, and generated index/catalog visibility.

The repository also has a versioning policy with two major planes:

- the tool release plane, where the Python package, CLI, reusable workflows, and repository release tags use SemVer; and
- the standard contract plane, where downstream consumers select supported standard contract versions by configuration.

That leaves an important package-level question: must every standard package declare its own package version, even when it is draft, internal, reference-only, or not consumer-selectable?

The answer matters because standard packages can change in ways that are meaningful even when no downstream consumer can select them through registry-backed configuration. Their documentation, templates, examples, provider declarations, skills, resource manifests, lifecycle posture, and packaging metadata can all evolve. If such a package is allowed to be unversioned, maintainers and agents lose a simple way to reason about whether the package itself changed.

The repository needs a durable methodology that separates three concepts:

- the repository/tool release version;
- the standard package version declared by `standard.toml`; and
- the consumer-selectable contract version exposed through registry and configuration metadata.

This decision governs standard package versioning as a class. It does not decide lifecycle state, adoption mode, artifact provenance, or the compatibility impact of a particular change.

## Considered Options

- **Allow unversioned internal or reference packages** - require versions only when downstream consumers can select a package through configuration.
- **Version only released and adoptable packages** - require package versions for stable consumer-facing standards, but leave draft, review, internal, or non-adoptable packages unversioned.
- **Require every standard package to declare package versions** - make package version metadata mandatory in `standard.toml` for all standard packages, while keeping consumer-selectable versions explicit in registry/configuration metadata.

## Decision Outcome

Chosen option: **require every standard package to declare package versions**.

Every standard package must declare a non-empty `[versions]` table in `standard.toml`. The `supported` list must contain at least one version string, `latest` must be non-empty, and `latest` must be one of the supported versions.

The package version is the package's own versioned contract. It applies to the package's maintained documentation, manifest metadata, examples, templates, resources, provider declarations, skills, adoption scaffolds, and other package-owned surfaces. Package versions use the standard contract version shape defined by repository policy, currently `major.minor` strings.

Consumer-selectable contract versions are a separate concern. A package version does not automatically make a standard selectable by downstream consumers. Consumer-facing version selection exists only when the package is registered through the repository's registry/configuration surface. That registry declares known selectable versions and a default version for each registered standard namespace. Consumer configuration may then select an allowed version under that namespace, or omit it and receive the default.

The repository therefore recognizes three version planes:

| Plane | Source of truth | Version shape | Meaning |
| --- | --- | --- | --- |
| Tool release version | repository release tag and Python package metadata | SemVer | Version of the installed toolchain, CLI, workflows, and packaged distribution. |
| Standard package version | `standards/<id>/standard.toml` `[versions]` table | `major.minor` | Version of the standard package as maintained in this repository. |
| Consumer contract version | registry/configuration metadata for registered standards | `major.minor` | Version a downstream consumer may select or inherit by default. |

All standard packages participate in the standard package version plane. Only registered consumer-facing standards participate in the consumer contract version plane.

A package version must be reviewed whenever a maintained package surface changes. The package's `latest` value should advance when a change meaningfully alters the package contract, package artifacts, adoption behavior, validation behavior, or maintainer guidance. Previously supported versions must remain in `supported` while they are still accepted by repository tooling or compatibility policy.

Removing a supported package version, changing the meaning of an existing version, or making validation stricter for existing consumers is governed by the repository's versioning policy. Lifecycle changes, adoption exposure, artifact provenance, generated catalogs, tests, and release notes must be updated consistently when a version change affects them.

Graph validation and schema validation must reject missing or empty package version declarations. A package may be draft, review-only, reference-only, internal, or non-adoptable, but it must not be unversioned.

Exceptions to this methodology require an ADR. A package-level note or TODO item is not enough to exempt a standard package from declaring versions.

### Consequences

- Good, because every standard package has explicit version metadata regardless of adoption mode.
- Good, because draft, reference-only, and internal packages can evolve without being confused with unversioned packages.
- Good, because registry/configuration exposure remains an intentional consumer-facing act instead of an automatic result of package versioning.
- Good, because generated indexes, catalogs, tests, release notes, and future tooling can reason about all standard packages consistently.
- Neutral, because this decision does not make non-adoptable or reference-only packages adoptable.
- Bad, because every standard package change now requires maintainers to decide whether its package version should advance.

## More Information

- Repository versioning policy: [`meta/versioning.md`](../../meta/versioning.md)
- Standard bundle authoring contract: [`standards/standard-bundle-authoring/README.md`](../../standards/standard-bundle-authoring/README.md)
- ADR 0001, standard bundle authoring contract: [`adr-0001-standard-bundle-authoring-contract.md`](adr-0001-standard-bundle-authoring-contract.md)
- ADR 0002, manifest-first standard discovery: [`adr-0002-manifest-first-standard-discovery.md`](adr-0002-manifest-first-standard-discovery.md)
- ADR 0007, standard graph validation gate: [`adr-0007-standard-graph-validation-gate.md`](adr-0007-standard-graph-validation-gate.md)
- ADR 0008, consumer config namespace registry: [`adr-0008-consumer-config-namespace-registry.md`](adr-0008-consumer-config-namespace-registry.md)
- ADR 0013, independent standard packages and relationship taxonomy: [`adr-0013-independent-standard-packages-and-relationship-taxonomy.md`](adr-0013-independent-standard-packages-and-relationship-taxonomy.md)
- ADR 0017, unified standard adoption methodology: [`adr-0017-unified-standard-adoption-methodology.md`](adr-0017-unified-standard-adoption-methodology.md)
- ADR 0018, standard package lifecycle methodology: [`adr-0018-standard-package-lifecycle-methodology.md`](adr-0018-standard-package-lifecycle-methodology.md)
- ADR 0019, packaged artifact parity and provenance: [`adr-0019-packaged-artifact-parity-and-provenance.md`](adr-0019-packaged-artifact-parity-and-provenance.md)
