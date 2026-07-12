---
schema_version: '1.1'
id: 'adr-0024-project-standards-catalog-scoped-package-version-channels'
title: 'ADR 0024: Catalog-Scoped Package Version Channels'
description: 'Defines non-breaking catalog defaults, opt-in breaking package candidates, durable accepted-major authorization, and catalog-major promotion.'
doc_type: 'adr'
status: 'active'
created: '2026-07-10'
updated: '2026-07-10'
reviewed: '2026-07-10'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'adr'
  - 'standards-platform'
  - 'versioning'
  - 'catalog'
aliases:
  - 'ADR 0024'
  - 'Catalog-scoped package version channels'
related:
  - 'docs/specs/2026-07-10-consumer-standards-control-plane-spec.md'
  - 'meta/versioning.md'
  - 'docs/adr/adr-0018-standard-package-lifecycle-methodology.md'
  - 'docs/adr/adr-0019-packaged-artifact-parity-and-provenance.md'
  - 'docs/adr/adr-0020-standard-package-versioning-methodology.md'
  - 'docs/adr/adr-0023-unified-consumer-standards-control-plane.md'
supersedes:
  - 'adr-0020-project-standards-standard-package-versioning-methodology'
superseded_by: null
source:
  - 'docs/specs/2026-07-10-consumer-standards-control-plane-spec.md'
  - 'meta/versioning.md'
confidence: 'high'
visibility: 'internal'
license: null
project:
  decision_makers:
    - 'chris'
  consulted: []
  informed: []
---

# ADR 0024: Catalog-Scoped Package Version Channels

MADR status: **accepted**.

## Context and Problem Statement

The repository has one SemVer release for the `project-standards` distribution, while each standard package evolves on its own `major.minor` line. Earlier policy treated package `latest` as the numerically highest bundled version and treated adding a package version as an ordinary additive tool release. That does not safely support publishing an opt-in breaking package major before the entire catalog is ready for another major release.

Consumers need automatic non-breaking updates within their chosen catalog line, exact pins when desired, and an explicit way to test breaking package candidates. Package authorization must remain durable across disable/re-enable without silently changing the ordinary default for other consumers.

How should tool releases, catalog majors, package versions, selectors, breaking candidates, and package-owned contract versions interact?

## Decision Drivers

- `version = 'latest'` must remain non-breaking for an unchanged catalog major.
- Breaking package versions should be publishable for opt-in testing before catalog-wide promotion.
- Candidate entry and exit must be explicit, reversible, and package/major scoped.
- Exact pins must remain exact.
- Accepted intent must survive reconciliation and disable/re-enable.
- Every advertised version must be installable offline from immutable payloads.
- Tool, package, selector, and internal contract versions must remain distinct.

## Considered Options

- Make every breaking package major require an immediate `project-standards` major release.
- Let `latest` select the numerically highest package version.
- Require exact pins for every candidate and provide no durable accepted track.
- Use catalog-scoped default and candidate channels with explicit major authorization.

## Decision Outcome

Chosen option: **use catalog-scoped default and candidate channels with explicit major authorization**.

The version planes are distinct:

- The `project-standards` distribution uses SemVer `MAJOR.MINOR.PATCH`.
- A consumer selects the matching catalog major in `.standards/config.toml`.
- Each standard package release uses immutable `major.minor` identity.
- The consumer selects `latest` or an exact package version independently for each standard.
- A package option such as `contract_version` may select a supported schema or behavior contract inside the resolved package payload; it is not the package release version.

### Catalog channels

Within one catalog major, every installable package version is advertised with lifecycle/channel metadata. Each package declares one non-breaking default for ordinary `latest` resolution. Other advertised majors may be retained or breaking candidates.

Absent matching current authorization or a recorded accepted-major track, `latest` resolves only to the catalog's declared non-breaking default. It does not mean the numerically highest version. A same-major tool release may add compatible versions or advertise an opt-in breaking candidate without changing that default.

Every advertised version has a complete immutable payload embedded in the installed distribution. Catalog resolution never downloads package content.

### Candidate entry and retained tracks

Entering a non-default package major requires explicit `--allow-major STANDARD_ID@TARGET_MAJOR` authorization and a declared migration path. Entry may combine authorization with `latest`, which selects the newest compatible version on the target major, or with an exact pin.

Successful entry writes a minimal accepted-major authorization record in the central lock, separate from enabled-package applied state. The record identifies the standard, accepted non-default major, and authorizing catalog lineage. The lineage is diagnostic provenance, not resolver input.

An accepted track survives ordinary reconciliation and package disablement. Re-enabling with `latest` resumes the accepted major without another flag and follows compatible updates within that major. If the catalog no longer advertises a compatible version, resolution fails closed; it never falls back to the ordinary default.

Exact selectors remain pinned even when an accepted track exists.

### Candidate exit and transition

Any non-promotion package-major transition requires authorization for the target major and a declared migration or rollback path. Exiting an accepted major requires an exact target version, including while the package is disabled.

Successful transition to another non-default major replaces the accepted-track record. Successful exit to the selected catalog's default major removes it. After an exact transition, changing that selector to `latest` on the already authorized major requires no new authorization.

Missing-lock recovery never reconstructs authorization history. A candidate selector without its accepted record must be reauthorized.

### Catalog-major promotion

Promoting a breaking candidate to the ordinary default requires a new `project-standards` catalog major. The consumer's explicit catalog-major transition authorizes the new catalog defaults for packages that followed the prior default; it does not require redundant per-package flags.

Exact selectors remain fixed. Accepted tracks on a different major remain sticky. Any accepted-track record matching the new default major is no longer exceptional and is removed whether the package is enabled or disabled.

The ordinary meaning of `latest` therefore changes only when the consumer explicitly opts into a new catalog major.

### Tool release classification

Advertising an opt-in breaking package candidate is non-breaking at the tool plane when the ordinary default and all previously valid selections remain available. It may ship in a MINOR release. Removing an advertised version, changing a same-major ordinary default incompatibly, or promoting a breaking package major to the default requires a MAJOR tool release.

### Consequences

- Good, because ordinary `latest` consumers receive automatic compatible updates without surprise major transitions.
- Good, because breaking package lines can receive real opt-in testing before catalog-wide promotion.
- Good, because exact pins, accepted tracks, and default followers retain distinct intent.
- Good, because disable/re-enable does not silently revoke authorization or downgrade a package.
- Good, because catalog-major opt-in is the single boundary for promoted defaults.
- Neutral, because the central lock stores current exceptional authorization while Git history supplies historical auditability.
- Bad, because the resolver, release policy, migration graph, and compatibility suite become more complex.
- Bad, because every advertised historical or candidate version must remain packaged and verified while supported.

### Confirmation

Resolver and release-policy tests cover ordinary defaults, exact pins, candidate entry through `latest` and exact selectors, authorization scope, same-major updates, disable/re-enable, unavailable retained tracks, exact-target exit, replacement/removal of authorization records, catalog promotion, missing-lock recovery, and offline installation of every advertised version.

## More Information

- Controlling specification: [`2026-07-10-consumer-standards-control-plane-spec.md`](../specs/2026-07-10-consumer-standards-control-plane-spec.md)
- Unified control-plane decision: [`adr-0023-unified-consumer-standards-control-plane.md`](adr-0023-unified-consumer-standards-control-plane.md)
- Repository versioning policy: [`meta/versioning.md`](../../meta/versioning.md)
