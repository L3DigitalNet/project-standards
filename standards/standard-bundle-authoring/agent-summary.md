# Standard Bundle Authoring Standard: Agent Summary

The canonical [README](README.md) is authoritative and wins if this summary conflicts with it.

Lifecycle: active. Adoption: `none`; this is an internal authoring contract.

## Use this summary when

Create, revise, review, graph-validate, or catalog a standard bundle under `standards/<id>/`.

## Core rules

- Every bundle has a canonical `README.md` and machine-readable `standard.toml`. Adoptable standards also have `adopt.md`; non-adoptable standards state that boundary explicitly.
- Keep the standard plane (`standard.toml`: identity, package versions, config, capabilities, relations, resources, authorities, providers) separate from the artifact plane (`adopt.toml`: files installed into consumer repositories).
- Declare one of five adoption modes: `validator`, `copy-adopt`, `cli`, `reference-only`, or `none`. A package keeps a non-empty `versions.supported` list and selects `versions.latest` from it.
- Claim consumer config through unique dotted namespaces. Use `companions` for advisory relationships, ADR-backed `extends` for real extensions, and exceptional `conflicts`; never add a hidden `requires` relation.
- Declare resource IDs as lowercase URI-safe tokens mapped to contained bundle-relative paths. A compact `agent-summary.md` targets at most 3,000 UTF-8 bytes, links to the canonical README, and states that the README wins on conflict.
- Declare each authority as `(domain, target, concern, owner, mutates)` and each generic provider with an operation, kind, optionality, and executable entrypoint when applicable. Avoid overlapping mutating owners.
- Link packaged artifacts through `[artifacts].manifest`, record provenance and install policy in `adopt.toml`, and keep any installed-wheel runtime manifest mirror byte-identical to its canonical source.

## Commands and artifacts

```bash
project-standards standards validate-graph --root . --require-all-manifests
project-standards standards render-catalog --root .
project-standards standards render-catalog --root . --check
```

Use [`templates/standard.toml`](templates/standard.toml) as the manifest scaffold. The schema/model and graph validator own mechanical conformance; semantic review still checks truthful capabilities, authorities, relationships, resources, and provider behavior.

## Boundaries and companions

This meta-standard governs standards authored in this repository. It is not consumer-adopted, provides no consumer configuration or runtime operation, and does not authorize MCP server behavior.

## Canonical resources

Read the [standard](README.md) for the complete field contract, safety rules, artifact linkage, lifecycle, exceptions, and author checklist.
