# Markdown Frontmatter Standard

This is the Catalog 5 family landing page for the active consumer package `markdown-frontmatter@1.3`. The immutable versioned payload, not this mutable landing page, defines the selected standard.

## Current authority

- [Markdown Frontmatter 1.3 standard](versions/1.3/README.md) — normative metadata, ID, and validation contract
- [Markdown Frontmatter 1.3 adoption guide](versions/1.3/adopt.md) — exact options, outputs, migration, and verification
- [Current family adoption guide](adopt.md) — concise enable/reconcile workflow
- [Markdown Frontmatter 1.3 agent summary](versions/1.3/agent-summary.md) — compact authoring and validation rules
- [Structure requirements](versions/1.3/structure.md) and [field-value policy](versions/1.3/field-values.md) — detailed document contract
- [Family index](standard.toml) — indexed payload and digest

## Use this standard when

Use Markdown Frontmatter for schema-validated metadata over an explicit Markdown corpus, stable document IDs, optional cross-file reference checks, canonical formatting, and a shared repo-local authoring skill. Package version `1.3` selects the immutable implementation; its independent `contract_version` option selects the document schema recorded as `schema_version` in managed files.

Markdown Tooling governs body formatting and linting. ADR is a companion document profile. Enable either separately when needed.

## Adopt

```bash
project-standards standards enable markdown-frontmatter --version 1.3
project-standards reconcile
project-standards reconcile --apply
project-standards validate
```

Review [adopt.md](adopt.md) before applying. Configure the managed corpus, exclusions, schema, reference checks, and workflow mode under `[standards.markdown-frontmatter.config]` in `.standards/config.toml`.

## Legacy boundary

Unversioned root references, templates, examples, V1 copy-adopt artifacts, and `.project-standards.yml` configuration are migration or compatibility evidence only. They do not define current Catalog 5 behavior. Use the exact `versions/1.3/` payload for normative requirements and reusable resources.
