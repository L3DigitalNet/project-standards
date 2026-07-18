# CLI Documentation Standard

This is the Catalog 5 family landing page for the active consumer package `cli-documentation@1.1`. The immutable versioned payload, not this mutable landing page, defines the selected standard.

## Current authority

- [CLI Documentation 1.1 standard](versions/1.1/README.md) — normative profile and documentation contract
- [CLI Documentation 1.1 adoption guide](versions/1.1/adopt.md) — exact options, outputs, provider workflow, migration, and verification
- [Current family adoption guide](adopt.md) — concise enable/reconcile workflow
- [CLI Documentation 1.1 agent summary](versions/1.1/agent-summary.md) — compact package behavior
- [Family index](standard.toml) — indexed payload and digest

## Use this standard when

Use the Script, Packaged, or Packaged-deep profile to keep parser-generated help, canonical usage documentation, optional generated man pages, README onboarding, and CI drift checks aligned. Package 1.1 creates `docs/usage.md` only when absent. Optional CI is rendered by a package provider, reviewed by the consumer, and published as a consumer-owned referenced input.

## Adopt

```bash
project-standards standards enable cli-documentation --version 1.1
project-standards reconcile
project-standards reconcile --apply
```

Review [adopt.md](adopt.md) before applying, especially the preview and no-clobber publication steps for an enabled workflow.

## Release-status correction

The immutable 1.1 README contains wording written before Catalog 5 and Project Standards v5.0.0 were published. Treat any statement that this payload is not released as release-time history. Catalog 5 now selects `cli-documentation@1.1`; the immutable payload bytes remain unchanged.

## Legacy boundary

Copy-adopt workflows, `project-standards adopt cli-documentation`, and `.project-standards.yml` fragments are migration evidence only. They do not define current Catalog 5 behavior.
