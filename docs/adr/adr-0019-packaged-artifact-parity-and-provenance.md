---
schema_version: '1.1'
id: 'adr-0019-project-standards-packaged-artifact-parity-and-provenance'
title: 'ADR 0019: Packaged Artifact Parity and Provenance'
description: 'Records the decision that standard package artifacts must declare provenance and prove packaged copies by parity test or deterministic transform.'
doc_type: 'adr'
status: 'active'
created: '2026-07-09'
updated: '2026-07-18'
reviewed: '2026-07-18'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'adr'
  - 'packaging'
  - 'provenance'
  - 'standard'
  - 'standards-platform'
aliases:
  - 'ADR 0019'
  - 'Packaged artifact parity and provenance'
related:
  - 'standards/standard-bundle-authoring/versions/2.0/README.md'
  - 'docs/adr/adr-0002-manifest-first-standard-discovery.md'
  - 'docs/adr/adr-0003-separate-standard-and-artifact-manifests.md'
  - 'docs/adr/adr-0007-standard-graph-validation-gate.md'
  - 'docs/adr/adr-0010-standard-resource-uris-and-index.md'
  - 'docs/adr/adr-0016-package-markdown-frontmatter-skill-with-standard.md'
  - 'docs/adr/adr-0017-unified-standard-adoption-methodology.md'
  - 'docs/adr/adr-0018-standard-package-lifecycle-methodology.md'
  - 'docs/adr/adr-0020-standard-package-versioning-methodology.md'
  - 'docs/adr/adr-0021-standard-packaged-skill-installation-methodology.md'
  - 'docs/adr/adr-0023-unified-consumer-standards-control-plane.md'
  - 'docs/adr/adr-0024-catalog-scoped-package-version-channels.md'
supersedes: []
superseded_by: null
source:
  - 'standards/standard-bundle-authoring/versions/2.0/README.md'
  - 'docs/adr/adr-0002-manifest-first-standard-discovery.md'
  - 'docs/adr/adr-0003-separate-standard-and-artifact-manifests.md'
  - 'docs/adr/adr-0007-standard-graph-validation-gate.md'
  - 'docs/adr/adr-0010-standard-resource-uris-and-index.md'
  - 'docs/adr/adr-0016-package-markdown-frontmatter-skill-with-standard.md'
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

# ADR 0019: Packaged Artifact Parity and Provenance

MADR status: **accepted**.

> **Amended by ADRs 0023 and 0024.** Provenance now applies to each immutable versioned payload and to semantic units recorded in the central consumer lock. The lock replaces package-specific provenance locks. Explicitly referenced consumer inputs carry path and digest evidence without transferring managed ownership.

## Context and Problem Statement

This repository treats Catalog 5 standards as packages with three related surfaces:

- the complete immutable payload under `standards/<id>/versions/<version>/`, where humans and agents author the canonical documentation, examples, templates, skills, resources, providers, and `payload.toml` declarations;
- the source packaging projection under `src/project_standards/{catalogs,families,payloads}/`, which exposes canonical catalogs, family indexes, and payload bytes to the build without creating a second maintained payload; and
- the installed `project_standards/{catalogs,families,payloads}/` namespaces, where the control plane reads the exact catalog, family, and payload bytes shipped in a wheel.

This decision was originally recorded against the V1 layout: unversioned files under `standards/<id>/` and copy-adopt bundles under `src/project_standards/bundles/<id>/`. Those paths remain historical migration and compatibility evidence only. ADRs 0023 and 0024 preserve the one-authority provenance rule while moving current authority to immutable V2 payloads, their manifests, and the package projection.

The remaining problem is provenance. Agents and maintainers need to know which versioned payload file is canonical, how its manifest declares it, and what proves that source-tree and installed-package views have not drifted. Without that rule, package projections or generated artifacts can become parallel unsynchronized copies. A consumer may then receive stale scaffolding even though the standard's documentation looks current.

The repository needs a durable methodology for artifact provenance so packaged bundles are distribution surfaces, not accidental second sources of truth.

This decision governs standard package artifacts as a class. It does not decide lifecycle state, adoption mode, or release-version classification.

## Considered Options

- **Treat projected or historical bundle files as independent copies** - allow packaging surfaces to be maintained separately from the authored versioned payload.
- **Generate every packaged artifact from the versioned payload** - require all installable artifacts to be produced by a build step from the authored package.
- **Require explicit provenance with parity tests or deterministic transforms** - let artifacts be mirrored, generated, or package-only, but require each reusable artifact to have one declared source of truth and a testable packaging path.

## Decision Outcome

Chosen option: **require explicit provenance with parity tests or deterministic transforms**.

Every reusable standard artifact must have one declared provenance class:

| Class | Meaning | Required proof |
| --- | --- | --- |
| Source-owned | The canonical artifact is authored under `standards/<id>/versions/<version>/`; projected and installed views are distribution surfaces. | Source/projection/wheel byte parity, unless a transform is declared. |
| Generated | The packaged artifact is produced from another source by a deterministic transform. | Transform declaration plus test coverage for the generated output. |
| Package-owned | The artifact exists only for installed tooling or adopt-engine execution and has no authored-standard counterpart. | Package test proving it is referenced and installed/loaded correctly. |
| External-owned | The artifact is intentionally sourced from another standard or shared artifact area. | Explicit shared-artifact reference; no sibling-bundle path shortcuts. |

Source-owned artifacts are the default for human-authored standard resources: README-adjacent templates, examples, standard-owned skills, workflow callers, config fragments, and other files that maintainers edit as part of the standard package. The containing `payload.toml` declares each source and digest. The source projection and both direct-wheel and sdist-derived-wheel builds must preserve those bytes unless the manifest explicitly declares a deterministic transform.

Generated artifacts are allowed when byte identity is the wrong contract. A generated artifact may normalize paths, inject package metadata, concatenate fragments, or otherwise adapt a source artifact for installation. The transform must be deterministic, local, documented, and covered by tests that fail on stale output.

Package-owned artifacts are allowed when the file is truly part of installed tooling rather than standard-authored content. They still must be discoverable from the payload manifest, provider declaration, or tests. A package-owned artifact is not a place to hide a second copy of standard prose, templates, examples, or skills.

External-owned artifacts are allowed only through explicit shared-artifact mechanisms. A standard must not point directly into a sibling payload to reuse a file. Cross-package reuse must be visible to graph validation and generated catalogs.

The versioned `payload.toml` declares what the control plane can materialize into a consumer repository and the exact canonical source and digest for each artifact. Projection checks and package tests must make it possible to answer "which file do I edit?" and "what proves every packaged view is current?" Historical V1 `adopt.toml` files describe the retired copy-adopt plane and do not establish current package authority.

When ownership of an artifact moves into a standard package, the old source copy must be retired or converted into a documented consumer mirror. Parallel unsynchronized source copies are drift, even if they are temporarily identical.

Exceptions to this provenance methodology require an ADR or an explicit manifest-backed exception that graph validation can surface. A one-off comment is not enough for a durable package artifact.

### Consequences

- Good, because maintainers and agents know which file to edit for each standard artifact.
- Good, because consumers do not receive stale packaged scaffolding when standard-owned resources change.
- Good, because package tests can catch drift between canonical versioned payloads, source projections, and installed distributions.
- Good, because generated artifacts remain possible without pretending they are byte-identical mirrors.
- Neutral, because `payload.toml` owns the artifact-installation plane; this ADR states the provenance expectations around those artifacts.
- Bad, because adding or moving packaged artifacts requires manifest updates, projection and package-parity tests, generated-output tests, or a documented package-owned rationale.

## More Information

- Standard bundle authoring contract: [`standards/standard-bundle-authoring/versions/2.0/README.md`](../../standards/standard-bundle-authoring/versions/2.0/README.md)
- ADR 0002, manifest-first standard discovery: [`adr-0002-manifest-first-standard-discovery.md`](adr-0002-manifest-first-standard-discovery.md)
- ADR 0003, separate standard and artifact manifests: [`adr-0003-separate-standard-and-artifact-manifests.md`](adr-0003-separate-standard-and-artifact-manifests.md)
- ADR 0007, standard graph validation gate: [`adr-0007-standard-graph-validation-gate.md`](adr-0007-standard-graph-validation-gate.md)
- ADR 0010, standard resource URIs and index: [`adr-0010-standard-resource-uris-and-index.md`](adr-0010-standard-resource-uris-and-index.md)
- ADR 0016, Markdown Frontmatter skill ownership: [`adr-0016-package-markdown-frontmatter-skill-with-standard.md`](adr-0016-package-markdown-frontmatter-skill-with-standard.md)
- ADR 0017, unified standard adoption methodology: [`adr-0017-unified-standard-adoption-methodology.md`](adr-0017-unified-standard-adoption-methodology.md)
