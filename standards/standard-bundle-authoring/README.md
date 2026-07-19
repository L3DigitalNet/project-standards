# Standard Bundle Authoring Standard

This is the Catalog 5 family landing page for the active internal package `standard-bundle-authoring@2.1`. Version 2.1 is the current authority for this repository; it is not staged and consumers cannot enable it. Version 2.0 remains advertised as released history.

## Current authority

- [Standard Bundle Authoring 2.1 standard](versions/2.1/README.md) — normative family, payload, catalog, provider, migration, and ownership contract
- [Standard Bundle Authoring 2.1 agent summary](versions/2.1/agent-summary.md) — compact authoring rules
- [Versioned templates](versions/2.1/templates/) — canonical package-authoring templates
- [Family index](standard.toml) — indexed payloads and digests
- [SPEC-BA02](../../docs/specs/2026-07-10-standard-bundle-authoring-v2-spec.md) — approved system requirements

## Use this standard when

Use version 2.1 when authoring or reviewing package families, immutable payloads, catalog declarations, closed option schemas, resources, semantic contributions, providers, migrations, compatibility evidence, or release-level classification in this repository.

The package is `internal`: it declares no consumer outputs or executable providers and has no adoption guide. Follow the [versioned author workflow](versions/2.1/README.md#author-workflow) and start from the [versioned templates](versions/2.1/templates/).

## Legacy boundary

Singleton V1 manifests, root copy templates, and pre-cutover reconstruction notes are historical migration evidence only. The root `standard.toml` is now the V2 family index, Catalog 5 advertises versions 2.0 and 2.1 with the `internal` role, and released payload bytes are immutable — 2.1 exists precisely because 2.0's SPEC-BA02 pointer could not be edited in place after release.
