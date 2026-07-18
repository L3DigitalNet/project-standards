# Standard Bundle Authoring Standard

This is the Catalog 5 family landing page for the active internal package `standard-bundle-authoring@2.0`. Version 2.0 is released and authoritative for this repository; it is not staged and consumers cannot enable it.

## Current authority

- [Standard Bundle Authoring 2.0 standard](versions/2.0/README.md) — normative family, payload, catalog, provider, migration, and ownership contract
- [Standard Bundle Authoring 2.0 agent summary](versions/2.0/agent-summary.md) — compact authoring rules
- [Versioned templates](versions/2.0/templates/) — canonical package-authoring templates
- [Family index](standard.toml) — indexed payload and digest
- [SPEC-BA02](../../docs/specs/2026-07-10-standard-bundle-authoring-v2-spec.md) — approved system requirements

## Use this standard when

Use version 2.0 when authoring or reviewing package families, immutable payloads, catalog declarations, closed option schemas, resources, semantic contributions, providers, migrations, compatibility evidence, or release-level classification in this repository.

The package is `internal`: it declares no consumer outputs or executable providers and has no adoption guide. Follow the [versioned author workflow](versions/2.0/README.md#author-workflow) and start from the [versioned templates](versions/2.0/templates/).

## Legacy boundary

Singleton V1 manifests, root copy templates, and pre-cutover reconstruction notes are historical migration evidence only. The root `standard.toml` is now the V2 family index, Catalog 5 advertises version 2.0 with the `internal` role, and released payload bytes are immutable.
