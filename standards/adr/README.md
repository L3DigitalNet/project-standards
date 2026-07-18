# Architecture Decision Record (ADR) Standard

This is the Catalog 5 family landing page for the active consumer package `adr@1.1`. The immutable versioned payload, not this mutable landing page, defines the selected standard.

## Current authority

- [ADR 1.1 standard](versions/1.1/README.md) — normative MADR and document contract
- [ADR 1.1 adoption guide](versions/1.1/adopt.md) — exact options, outputs, migration, and verification
- [Current family adoption guide](adopt.md) — concise enable/reconcile workflow
- [ADR 1.1 agent summary](versions/1.1/agent-summary.md) — compact operating rules
- [Family index](standard.toml) — indexed payload and digest

## Use this standard when

Use ADRs for significant, costly-to-reverse architecture decisions. Package 1.1 supplies a create-only ADR scaffold and optional validation of MADR's three required level-2 sections. Markdown Frontmatter is a companion, not a package dependency; enable it separately when ADR metadata also needs schema and ID validation.

## Adopt

```bash
project-standards standards enable adr --version 1.1
project-standards reconcile
project-standards reconcile --apply
```

Review [adopt.md](adopt.md) before applying. Reconciliation preserves consumer-authored ADRs and creates the scaffold only when it is absent.

## Legacy boundary

Copy-adopt commands, `.project-standards.yml` fragments, and unversioned V1 templates are migration evidence only. They do not define current Catalog 5 behavior. Use `.standards/config.toml`, the central lock, and the exact `versions/1.1/` payload.
