# Standard Bundle Authoring

This directory is the package-family landing page for the Standard Bundle Authoring standard. During the V5 reconstruction, the root [`standard.toml`](standard.toml) remains the operational V1 manifest until the atomic catalog activation. It is migration history, not the V2 payload index.

The normative contract for package version `2.0` is [`versions/2.0/README.md`](versions/2.0/README.md). Its versioned resources and templates are authoritative for that payload. This landing page provides navigation only and must not be used as a substitute for the selected payload.

## Staged V2 payload

`standard-bundle-authoring@2.0` is the staged `internal` payload. It governs how this repository authors package families, immutable payloads, catalog declarations, providers, migrations, and compatibility evidence. Consumers cannot enable it, and it declares no consumer artifacts or executable providers.

Start with the [2.0 author workflow](versions/2.0/README.md#author-workflow) and copy the versioned files under [`versions/2.0/templates/`](versions/2.0/templates/). The root [`templates/standard.toml`](templates/standard.toml) entry point mirrors the current family-index template for source-tree discoverability.

## Authority history

The singleton-manifest contract remains the bounded V1 runtime until the planned catalog cutover. The approved [SPEC-BA02](../../docs/specs/2026-07-10-standard-bundle-authoring-v2-spec.md) supersedes its authoring guidance; Task 14 replaces the root manifest only after all package reconstructions validate together. Released V2 payloads are immutable and remain addressable through the family index and catalog history.
