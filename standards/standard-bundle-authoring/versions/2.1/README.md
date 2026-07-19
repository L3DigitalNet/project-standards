# Standard Bundle Authoring V2

This standard defines the machine-checkable contract for authoring versioned standard packages. A package separates stable family identity, complete immutable payloads, and catalog-major channel policy. The authoritative system requirements are [SPEC-BA02](../../../../docs/specs/2026-07-10-standard-bundle-authoring-v2-spec.md); this document is the normative authoring guide for payload version `2.1`.

## Required package anatomy

```text
standards/<id>/
├── README.md
├── standard.toml
└── versions/
    └── <major.minor>/
        ├── README.md
        ├── agent-summary.md
        ├── config.schema.json
        ├── payload.toml
        └── ... every declared immutable resource
catalogs/
└── <catalog-major>.toml
```

The root `standard.toml` is a mutable family index. Each version directory is a complete payload whose bytes become immutable when first included in a released catalog. Catalog sources assign channel roles without changing either family or payload data.

## Family index

A family index uses `schema_version = "2.0"`, one `[standard]` table, and one `[[versions]]` entry for every indexed payload. The package ID is kebab-case and matches the family directory. Version entries use exact `major.minor` values, canonical `versions/<version>/payload.toml` paths, and aggregate SHA-256 digests. They sort by numeric major and minor. Family status is `draft`, `review`, `active`, `deprecated`, `archived`, or `superseded`.

Family and payload manifests never declare `latest`, default, retained, candidate, reference-only, or internal catalog roles. Use the [`standard.toml` template](templates/standard.toml).

## Payload manifest

Each payload uses `schema_version = "1.0"` and declares:

- exact package identity and one availability: `consumer`, `reference-only`, or `internal`;
- one closed Draft 2020-12 package-option schema;
- provided and consumed platform capabilities;
- companion, extension, and conflict relationships plus immutable decision evidence for each `extends` or `conflicts` edge;
- every resource, artifact, semantic contribution, provider, referenced extension, migration, legacy state, and legacy signature.

Unknown tables and fields are invalid. Consumer payloads require one adoption guide. Reference-only and internal payloads must not declare one. Every payload has exactly one canonical standard, agent summary, and config-schema resource. Use the [`payload.toml` template](templates/payload.toml).

## Package options

`config.schema.json` is a closed object schema using JSON Schema Draft 2020-12. Every property is required or has a deterministic default. Contract or behavior selectors are ordinary package options; they are not package versions. A referenced-extension option is a path string whose containment is enforced by the control plane. Start from the [`config.schema.json` template](templates/config.schema.json).

This internal package has no options, so its own schema is a closed empty object.

## Resources and outputs

Every resource is declared exactly once with an ID, role, safe relative path, media type, and raw-byte digest. Other regular payload files are declared once as an artifact source or static-contribution source and carry the digest fields defined by that declaration. Symlinks, undeclared files, absolute paths, traversal, case-fold collisions, and duplicate canonical paths are invalid.

Whole artifacts exclusively own one consumer file. Semantic contributions own the smallest normalized unit in a supported adapter:

| Adapter | Canonical selector forms |
| --- | --- |
| `whole-file` | `$file` |
| `toml` | `key:JSON_POINTER`, `table:JSON_POINTER` |
| `json`, `jsonc` | `key:JSON_POINTER`, `set:JSON_POINTER#value=IDENTITY`, `keyed-set:JSON_POINTER#KEY=IDENTITY` |
| `yaml` | `key:JSON_POINTER`, `keyed-set:JSON_POINTER#KEY=IDENTITY` |
| `editorconfig` | `property:SECTION#KEY` |
| `markdown-block` | `block:BLOCK_ID` |

Each contribution has exactly one static source or render provider. Static sources declare their digest. A shared identity is valid only when every reference normalizes to identical adapter, scope, value, and digest. See the [`contribution.toml` template](templates/contribution.toml).

## Providers

Executable providers are immutable payload resources addressed as `payload:RESOURCE_ID#EXPORTED_SYMBOL`; consumer configuration cannot name code. They declare a closed generic operation, kind, phase, effect, input schema, output schema, and referenced resources. Reconciliation providers run offline against immutable snapshots and never write the live repository. The platform executor is the sole writer.

Operation-to-phase/effect mappings are closed. Examples include `render` → `plan/content`, `validate` → `validate/findings`, `verify` → `verify/findings`, `migrate` → `plan/migration-report`, and authoring mutations such as `scaffold` → `authoring/mutation-plan`. Documentation-only providers declare no execution fields. See the [`provider.toml` template](templates/provider.toml).

## Referenced extensions

A referenced extension binds one path-valued option to a media type and the `repository-relative` path policy. It may recommend a directory under `.standards/extensions/<package>/`. The consumer owns the file; the package records its path and digest but never mutates or deletes it. See the [`extension.toml` template](templates/extension.toml).

## Migrations and legacy signatures

Migration endpoints are exact `package:MAJOR.MINOR` values or registered `legacy:STATE` tokens. An automatic migration names one migration provider. A manual migration names one instruction resource. Each declaration inventories all affected `config:*`, `artifact:ID`, and `contribution:ID` identities and at least one endpoint equals the containing payload version.

Legacy signatures recognize exact package-history bytes through `known_content_digests`. Unknown bounded blocks and every ownership-acquiring, locking, or destructive transition block automatic migration. A single-target whole-file signature may additionally declare `consumer_owned_intent_pointer`; this authorizes only the FR-037 consumer-owned preserve path and never adds observed bytes to package history. Raw migration input must explicitly supply the literal `consumer-owned` value through that pointer. Marker presence alone never proves ownership, and all other unknown or modified legacy bytes remain consumer-owned and block automatic migration. See the [`migration.toml`](templates/migration.toml) and [`legacy-signature.toml`](templates/legacy-signature.toml) templates.

## Integrity and catalog roles

Compute the aggregate payload digest from a canonical sorted inventory:

1. Hash the raw `payload.toml` bytes.
2. Encode `NORMALIZED_PATH NUL sha256:HEX LF` for `payload.toml` and every declared file.
3. Sort entries by normalized UTF-8 path bytes.
4. SHA-256 the concatenation and store it in the family index and every catalog reference.

A catalog source uses `schema_version = "1.0"`, its numeric `catalog_major`, and one exact package/version/digest/role entry. Consumer payloads use `default`, `retained`, or `candidate`; reference-only and internal payloads use their same-named roles. A catalog has exactly one ordinary default for each consumer family it offers. See the [`catalog.toml` template](templates/catalog.toml).

## Author workflow

Perform these steps in order; do not publish a catalog entry for an incomplete payload.

1. Select the next `major.minor` from the package compatibility change.
2. Copy the versioned templates into a new `versions/<version>/` directory.
3. Author complete documentation, options, resources, outputs, providers, extensions, and migrations.
4. Validate schemas, paths, scopes, provider contracts, and payload inventory.
5. Compute the aggregate digest and add the exact version/path/digest to the family index.
6. Prove source-tree, graph, projection, installed-wheel, migration, and compatibility behavior.
7. Add the exact digest to the target catalog with the correct role.
8. Compare released payloads with the tagged immutable baseline, classify the catalog diff, and publish under the required tool/catalog release level.

Use the repository commands:

```bash
uv run project-standards standards validate-packages --root .
uv run project-standards standards generate-package-schemas --root . --check
uv run project-standards standards sync-payload-projection --root . --check
uv run project-standards packages check-release --root . --baseline vPREVIOUS
```

The release check requires a real released tag and a working catalog matching the current tool major. Before publication, build both a direct wheel and an sdist-derived wheel and prove their family, payload, and catalog bytes match the canonical source without network access.

## Publication and recovery

Payloads may change before their first released catalog inclusion. After that point, correction requires a new package version; never edit or delete a released payload. Removing an advertised version or promoting a breaking candidate requires the catalog-major and tool-major transition defined by ADR 0024. Git history, signed tags, and published artifacts are the recovery source.

## Self-hosting status

`standard-bundle-authoring@2.1` demonstrates this contract as an `internal` payload. It declares a closed empty option schema, canonical documentation, and all author templates. It intentionally declares no adoption guide, consumer artifact, semantic contribution, referenced extension, migration, legacy signature, or executable provider.
