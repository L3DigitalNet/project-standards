---
schema_version: '1.1'
id: 'adr-0017-project-standards-unified-standard-adoption-methodology'
title: 'ADR 0017: Unified Standard Adoption Methodology'
description: 'Records the decision that standards expose a consistent adoption surface while preserving mode-specific enforcement and authoring mechanics.'
doc_type: 'adr'
status: 'superseded'
created: '2026-07-09'
updated: '2026-07-10'
reviewed: '2026-07-10'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'adr'
  - 'adoption'
  - 'standard'
  - 'standards-platform'
aliases:
  - 'ADR 0017'
  - 'Unified standard adoption methodology'
related:
  - 'standards/standard-bundle-authoring/README.md'
  - 'docs/adr/adr-0001-standard-bundle-authoring-contract.md'
  - 'docs/adr/adr-0003-separate-standard-and-artifact-manifests.md'
  - 'docs/adr/adr-0006-standard-provider-plugin-model.md'
  - 'docs/adr/adr-0010-standard-resource-uris-and-index.md'
  - 'docs/adr/adr-0013-independent-standard-packages-and-relationship-taxonomy.md'
  - 'docs/adr/adr-0018-standard-package-lifecycle-methodology.md'
  - 'docs/adr/adr-0019-packaged-artifact-parity-and-provenance.md'
  - 'docs/adr/adr-0020-standard-package-versioning-methodology.md'
  - 'docs/adr/adr-0021-standard-packaged-skill-installation-methodology.md'
  - 'docs/adr/adr-0023-unified-consumer-standards-control-plane.md'
supersedes: []
superseded_by: 'adr-0023-project-standards-unified-consumer-standards-control-plane'
source:
  - 'standards/standard-bundle-authoring/README.md'
  - 'docs/adr/adr-0001-standard-bundle-authoring-contract.md'
  - 'docs/adr/adr-0003-separate-standard-and-artifact-manifests.md'
  - 'docs/adr/adr-0006-standard-provider-plugin-model.md'
  - 'docs/adr/adr-0010-standard-resource-uris-and-index.md'
  - 'docs/adr/adr-0013-independent-standard-packages-and-relationship-taxonomy.md'
confidence: 'high'
visibility: 'internal'
license: null
project:
  decision_makers:
    - 'chris'
  consulted: []
  informed: []
---

# ADR 0017: Unified Standard Adoption Methodology

MADR status: **superseded** by [ADR 0023](adr-0023-unified-consumer-standards-control-plane.md).

## Context and Problem Statement

This repository defines reusable standards as packages that can reach consumers through different mechanics: documentation, validation, copied scaffolds, reusable workflows, agent resources, package tooling, specialized commands, and generated catalogs. The standard-bundle contract records those mechanics in manifests, and the artifact-plane contract separates standard metadata from installable files.

Those contracts still need one durable methodology for what "adoption" means across all standards. Without that methodology, each standard can grow a local interpretation of adoption. Consumers then have to infer whether adoption means reading an adoption guide, copying files, wiring CI, installing repo-local resources, running tooling, or some combination of those actions.

Tooling has a related problem. If adoption metadata is treated as a proxy for static files only, generated indexes and future consumers cannot reliably distinguish adoption mode, seed artifacts, provider commands, package resources, and deliberately non-adoptable standards.

The decision must govern standards as a class. It should not encode a release step, a temporary migration state, or the rationale for one package's implementation.

## Considered Options

- **Keep adoption mechanics per-standard and informal** - allow each standard to define its own consumer-facing adoption shape.
- **Require identical copy-adopt mechanics for every standard** - force all adoptable standards through the same static artifact mechanism.
- **Define a unified adoption methodology with mode-specific mechanics** - require a consistent consumer and tooling surface while allowing each standard to declare its actual enforcement and authoring mode.

## Decision Outcome

Chosen option: **define a unified adoption methodology with mode-specific mechanics**.

Every standard must declare its adoption posture in `standard.toml`. A standard released for downstream adoption must expose a consistent consumer-facing adoption surface:

- an `adopt.md` guide for the human procedure;
- `standard.toml` metadata for status, adoption mode, resources, config namespaces, providers, capabilities, authorities, and relationships;
- generated index/catalog visibility for humans, agents, and tooling;
- explicit provider declarations when validation, authoring, linting, formatting, scaffolding, upgrade, or drift-check behavior is fulfilled by first-party tooling;
- explicit artifact-plane declarations when adoption seeds files, config fragments, workflow callers, skills, templates, examples, or other repo-local resources.

A standard that is not released for downstream adoption must also be explicit: it declares a non-adoptable posture in `standard.toml`, omits consumer adoption resources, and explains that posture in its standard package. Non-adoptability is never inferred from a missing guide, missing provider, or missing artifact manifest.

`adopt.toml` remains the artifact-plane manifest. It describes static seed/scaffold resources an adoption engine can materialize into a consumer repository. It is not the manifest for every file a standard may eventually produce, and it is not a substitute for provider metadata.

Specialized tools remain valid adoption mechanics. A tool may generate final consumer content when that content needs repository-specific input, validation, generated IDs, path decisions, lifecycle fields, or other dynamic choices. When the same adoption procedure also installs static repo-local seed resources, those resources belong in the artifact plane.

Adoption mode describes how compliance is established or maintained. It does not decide whether the standard participates in adoption metadata. Standards may use different modes, but they must describe those modes consistently through the same package contract.

This ADR does not require all standards to have identical mechanics. It requires all standards to make their mechanics explicit in the same places.

### Consequences

- Good, because consumers see one adoption pattern across standards.
- Good, because generated indexes can distinguish adoption mode, seed artifacts, providers, package resources, and non-adoptable status without special cases.
- Good, because copy-adopt scaffolding can coexist with command-, workflow-, validator-, or package-based enforcement.
- Good, because dynamically authored content stays with the tooling that can validate and generate it correctly.
- Neutral, because `standard.toml` and `adopt.toml` remain separate manifests under the existing artifact-plane decision.
- Bad, because standards with previously informal or tool-only adoption surfaces may need new seed artifacts, docs, manifests, tests, or catalog behavior.

## More Information

- Standard bundle authoring contract: [`standards/standard-bundle-authoring/README.md`](../../standards/standard-bundle-authoring/README.md)
- ADR 0001, standard bundle authoring contract: [`adr-0001-standard-bundle-authoring-contract.md`](adr-0001-standard-bundle-authoring-contract.md)
- ADR 0003, separate standard and artifact manifests: [`adr-0003-separate-standard-and-artifact-manifests.md`](adr-0003-separate-standard-and-artifact-manifests.md)
- ADR 0006, standard provider plugin model: [`adr-0006-standard-provider-plugin-model.md`](adr-0006-standard-provider-plugin-model.md)
- ADR 0010, standard resource URIs and index: [`adr-0010-standard-resource-uris-and-index.md`](adr-0010-standard-resource-uris-and-index.md)
- ADR 0013, independent standard packages and relationship taxonomy: [`adr-0013-independent-standard-packages-and-relationship-taxonomy.md`](adr-0013-independent-standard-packages-and-relationship-taxonomy.md)
