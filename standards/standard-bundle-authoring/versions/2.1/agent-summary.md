# Standard Bundle Authoring V2 summary

The canonical [README](README.md) is authoritative and wins if this summary conflicts with it.

Use V2 packages as three separate layers:

- `standards/<id>/standard.toml`: mutable family identity plus exact indexed versions and aggregate digests.
- `standards/<id>/versions/<major.minor>/`: complete immutable payload with `payload.toml`, closed option schema, docs, and every declared resource.
- `catalogs/<major>.toml`: exact package/version/digest entries with channel roles; family and payload manifests never declare `latest` or roles.

Authoring order: create a version directory, author all declarations, validate schemas and content, compute the canonical inventory digest, index the payload, prove source/graph/projection/wheel/compatibility parity, assign a catalog role, then run the immutable-baseline release check.

Key rules:

- Payload availability is `consumer`, `reference-only`, or `internal`.
- Consumer payloads require an adoption guide; the other two forbid one.
- Every payload has exactly one canonical standard, agent summary, and closed Draft 2020-12 config schema.
- Every regular payload file is declared and digested; symlinks and undeclared files are invalid.
- Contributions own normalized adapter scopes, never shared whole containers.
- Providers resolve only through `payload:RESOURCE#SYMBOL`, run offline, return their declared effect, and never write the live repository.
- Extensions remain consumer-owned. Migrations use exact package or registered legacy endpoints and enumerate all effects and recognized signatures.
- Released payload bytes are immutable; corrections use a new package version.

This `2.1` payload is internal and ships authoring templates only. It has no consumer outputs or executable providers.
