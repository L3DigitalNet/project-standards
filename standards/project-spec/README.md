# Project Specification Standard

This is the Catalog 5 family landing page for the active consumer package `project-spec@1.2`. The immutable versioned payload, not this mutable landing page, defines the selected standard.

## Current authority

- [Project Specification 1.2 standard](versions/1.2/README.md) — normative profiles, identifiers, traceability, and tooling contract
- [Project Specification 1.2 adoption guide](versions/1.2/adopt.md) — exact options, outputs, authoring operations, migration, and verification
- [Current family adoption guide](adopt.md) — concise enable/reconcile workflow
- [Project Specification 1.2 agent summary](versions/1.2/agent-summary.md) — compact operating rules
- [Family index](standard.toml) — indexed payload and digest

## Use this standard when

Use Light, Standard, or Full specifications for durable project, feature, or subsystem requirements and design. Package 1.2 provides stable canonical sections, typed identifiers, deterministic validation and linting, provider-backed scaffold and upgrade plans, and a managed validation workflow. Consumer-authored specifications remain consumer-owned.

## Adopt

```bash
project-standards standards enable project-spec --version 1.2
project-standards reconcile
project-standards reconcile --apply
```

Review [adopt.md](adopt.md) before applying. Project Specification uses its own document schema and remains independent of Markdown Frontmatter.

## Release-status correction

The immutable 1.1 README contains wording written before Catalog 5 and Project Standards v5.0.0 were published. Treat any statement that this payload is not released as release-time history. Catalog 5 now selects `project-spec@1.2`; the immutable 1.1 payload bytes remain unchanged.

## Legacy boundary

The `spec` block in `.project-standards.yml`, V1 workflow adoption, and unversioned copy-adopt resources are migration evidence only. Under unified authority, bare `project-standards spec` commands resolve `project-spec@1.2` through `.standards/`; an explicit `--config` is legacy/debug input and cannot override that authority.
