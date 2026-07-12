---
schema_version: '1.1'
id: 'adr-0023-project-standards-unified-consumer-standards-control-plane'
title: 'ADR 0023: Unified Consumer Standards Control Plane'
description: 'Establishes one neutral .standards control plane with explicit reconciliation, central ownership, and typed semantic composition.'
doc_type: 'adr'
status: 'active'
created: '2026-07-10'
updated: '2026-07-12'
reviewed: '2026-07-12'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'adr'
  - 'standards-platform'
  - 'control-plane'
  - 'composition'
aliases:
  - 'ADR 0023'
  - 'Unified consumer standards control plane'
related:
  - 'docs/specs/2026-07-10-consumer-standards-control-plane-spec.md'
  - 'docs/superpowers/specs/2026-07-10-root-artifact-ownership-semantic-composition-design.md'
  - 'docs/adr/adr-0003-separate-standard-and-artifact-manifests.md'
  - 'docs/adr/adr-0004-authority-map-and-conflict-free-composition.md'
  - 'docs/adr/adr-0006-standard-provider-plugin-model.md'
  - 'docs/adr/adr-0008-consumer-config-namespace-registry.md'
  - 'docs/adr/adr-0013-independent-standard-packages-and-relationship-taxonomy.md'
  - 'docs/adr/adr-0017-unified-standard-adoption-methodology.md'
  - 'docs/adr/adr-0019-packaged-artifact-parity-and-provenance.md'
  - 'docs/adr/adr-0021-standard-packaged-skill-installation-methodology.md'
  - 'docs/adr/adr-0022-standard-packaged-hook-installation-methodology.md'
  - 'docs/adr/adr-0024-catalog-scoped-package-version-channels.md'
  - 'docs/research/2026-07-12-python-tooling-consumer-owned-workflow-migration.md'
supersedes:
  - 'adr-0003-project-standards-separate-standard-and-artifact-manifests'
  - 'adr-0008-project-standards-consumer-config-namespace-registry'
  - 'adr-0017-project-standards-unified-standard-adoption-methodology'
superseded_by: null
source:
  - 'docs/specs/2026-07-10-consumer-standards-control-plane-spec.md'
  - 'docs/superpowers/specs/2026-07-10-root-artifact-ownership-semantic-composition-design.md'
  - 'docs/research/2026-07-12-python-tooling-consumer-owned-workflow-migration.md'
confidence: 'high'
visibility: 'internal'
license: null
project:
  decision_makers:
    - 'chris'
  consulted: []
  informed: []
---

# ADR 0023: Unified Consumer Standards Control Plane

MADR status: **accepted**.

## Context and Problem Statement

Standards currently reach consumers through package-specific guides, copied files, config fragments, workflows, skills, hooks, and specialized commands. The approach has useful safety checks but no single desired-state authority, applied-state authority, or complete reconciliation model. Multiple standards already target the same root files, and the current fragment path reports some required edits without applying or tracking them.

Consumers need one neutral entry point that remains independent of any particular standard, Git provider, or security policy. The platform must preserve consumer-owned content, keep validation read-only, work offline, support independently selected packages, and compose shared files without precedence.

How should a consumer repository declare, reconcile, and audit its installed standards and their repository artifacts?

## Decision Drivers

- One visible and reviewable consumer authority.
- No package-order behavior or hidden dependency between standards.
- Read-only validation and planning with explicit mutation.
- Offline, deterministic operation from the installed distribution.
- Safe update and removal based on exact ownership and provenance.
- Preservation of conventional paths required by external tools.
- Semantic composition that does not overwrite unrelated consumer content.
- Explicit ownership relinquishment without treating consumer bytes as package history.

## Considered Options

- Let any adopted standard bootstrap shared metadata as a ride-along.
- Preserve package-specific imperative adoption and provenance state.
- Establish one neutral `.standards/` control plane with explicit reconciliation.
- Move every managed artifact under `.standards/` and use links or wrappers.

## Decision Outcome

Chosen option: **establish one neutral `.standards/` control plane with explicit reconciliation**.

A consumer initializes the catalog once. Plain initialization creates exactly:

```text
.standards/
├── config.toml
├── catalog.toml
└── lock.toml
```

Initialization enables no standard. `config.toml` is the user-owned desired-state authority. It declares the catalog major, package enablement, package-version selector, and package options under owned namespaces. `catalog.toml` is the deterministic tool-owned snapshot of every package and version available from the installed distribution. `lock.toml` is the tool-owned applied-state and provenance authority.

Planning and validation are read-only. `reconcile` produces one complete virtual-tree plan from config, catalog, lock, package payloads, provider output, and live repository state. Only explicit `reconcile --apply` may mutate the repository. The platform executor is the sole writer, rechecks preconditions, applies contained atomic replacements, runs read-only verification, and writes the lock last.

Packages remain independently selectable. They may consume the generic platform but must not require another standard merely to obtain config, adoption, or a shared container. Catalog groups and companion relationships remain recommendations or compatibility declarations, not hidden installation dependencies.

### Consumer and package ownership

Required integration artifacts remain at conventional paths. A shared container such as `pyproject.toml`, `AGENTS.md`, `.editorconfig`, or VS Code settings is consumer-owned. A package owns only its declared semantic unit: a TOML key path, JSON/JSONC key or stable entry, YAML mapping, EditorConfig property, task or hook identity, or delimiter-bounded Markdown block.

The control plane owns the merge mechanism, not the surrounding content. It preserves every undeclared unit and blocks overlapping or ambiguous claims before writes. Identical shared units use a stable content-addressed identity and reference counting. No standard has precedence. Whole-file ownership is allowed only for exclusive declared destinations.

Semantic adapters must preserve unowned comments, ordering, quoting, and formatting. Physical-formatting authority is distinct from semantic ownership. A formatter may change bytes only through its explicit operation and must preserve normalized semantic values.

### Package and extension state

Package-owned durable resources that need no external discovery path live under `.standards/packages/STANDARD_ID/`. Every entry is declared, committed, centrally inventoried, and drift-checked. The namespace stores no cache, ignored runtime state, secrets, or duplicate lock.

Specialized consumer-owned inputs may live under `.standards/extensions/STANDARD_ID/` or another declared repository-relative path. The lock records their path and digest without claiming, overwriting, or deleting them.

### Central lock and lifecycle

The central lock replaces package-specific provenance locks. It records selected payloads, effective config, artifacts, semantic units, ownership, shared references, referenced inputs, policies, and content digests. Enabled-package applied records remain separate from persistent accepted-major authorization records defined by ADR 0024.

Disabling a package changes only its `enabled` flag in desired config. Successful reconciliation safely removes unchanged, exclusively owned applied units and package state while preserving selector/options, shared references still in use, create-only content, consumer content, and modified or ambiguous files. Any modified managed unit is a plan-wide conflict and remains untouched.

### Providers and payloads

Only immutable, catalog-trusted package payloads may declare providers. Consumer config cannot name executable entrypoints or external artifact sources. Read-only providers consume snapshots and return typed findings or content. Operations with mutating intent return bounded mutation plans; they never write the live repository directly.

The exact versioned payload and manifest contract is defined by the successor Standard Bundle Authoring specification. The control plane consumes that contract generically and contains no package-ID branches for ordinary behavior.

### Migration

V5 provides explicit preview/apply migration from `.project-standards.yml` and recognized installed artifacts. Successful migration retires the legacy YAML authority only after complete conversion and validation. Known whole-file package payloads are recognized through offline versioned signatures; exact matches receive reviewed replacement actions, while modified or ambiguous matches block instead of duplicating stale and current content.

One constrained owner-resolution path may preserve an unrecognized whole file without claiming it. The selected payload must statically bind one canonical `consumer_owned_intent_pointer` to a single-target `whole-file` legacy signature. Raw legacy input must explicitly select consumer ownership through that exact pointer; the migration provider must return `ownership = "consumer-owned"`, `disposition = "preserve"`, the exact observed target and digest, and an `intent_pointer` that echoes the declaration and names a recognized raw setting whose literal value is `consumer-owned`; and the resolved payload must materialize no artifact or contribution for the target. The engine verifies the claim target against the declared signature target instead of trusting the provider to choose the file. The plan exposes the preserved path and digest, apply remains bound to the observed bytes and file identity, and the central lock records no package ownership or managed unit for the file.

This exception relinquishes ownership; it does not infer package provenance, validate file semantics, or authorize a future takeover. Every observed unknown signature retains the ordinary unknown-digest finding unless one fully valid, statically target-bound claim clears it; an unknown signature with no claim still fails closed. Unknown bounded blocks and every adopt, replace, remove, shared-ownership, or package-lock transition still require declared exact content evidence and fail closed otherwise. Returning a consumer-owned whole file to managed ownership requires a separate previewed adoption or replacement after the consumer explicitly resolves the existing file.

V5 may retain read-only legacy validation compatibility. It never merges active YAML and TOML authorities. V6 removes the legacy fallback after migration evidence is complete.

### Consequences

- Good, because consumers receive one neutral standards entry point and one desired/applied state model.
- Good, because package composition and removal become deterministic, reviewable, and safe.
- Good, because standard packages remain independent while sharing platform services.
- Good, because required external discovery paths remain intact without granting whole-file ownership.
- Good, because a package can explicitly relinquish a whole file without misclassifying consumer bytes as package-shipped history.
- Good, because package-specific provenance locks and untracked fragment instructions are retired.
- Neutral, because package standards still document their own options and behavior while adoption mechanics move to the platform.
- Bad, because the platform must implement syntax-preserving semantic adapters, migrations, and a larger compatibility suite.
- Bad, because preserved consumer-owned files receive no package drift detection, updates, validation, or automatic path back to managed ownership.
- Bad, because every current package must be reconstructed as immutable versioned payloads before it can be advertised as V5-compatible.

### Confirmation

Conformance requires schema round trips, offline installed-wheel tests, real apply for every package/pair/full set, deterministic input-order tests, migration fixtures, path-safety tests, interruption recovery, reference-counted removal, and format-then-reconcile stability. Migration fixtures must prove that explicit consumer-owned whole-file preservation requires a static single-target pointer binding, emits no write or lock ownership, remains stale-plan-safe, rejects a provider-selected different target and simultaneous materialization, keeps unknown unclaimed, bounded, or managed content blocked, preserves known consumer-owned claims without an intent pointer, and requires a separate reviewed transition back to managed ownership. A package that fails the compatibility matrix is not advertised as control-plane compatible.

## More Information

- Controlling specification: [`2026-07-10-consumer-standards-control-plane-spec.md`](../specs/2026-07-10-consumer-standards-control-plane-spec.md)
- Semantic composition design: [`2026-07-10-root-artifact-ownership-semantic-composition-design.md`](../superpowers/specs/2026-07-10-root-artifact-ownership-semantic-composition-design.md)
- Version-channel decision: [`adr-0024-catalog-scoped-package-version-channels.md`](adr-0024-catalog-scoped-package-version-channels.md)
