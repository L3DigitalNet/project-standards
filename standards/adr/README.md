# Architecture Decision Record (ADR) Standard

This is the Catalog 5 family landing page for the active consumer package `adr@1.4`. The immutable versioned payload, not this mutable landing page, defines the selected standard.

## Current authority

- [ADR 1.4 standard](versions/1.4/README.md) — normative MADR, document, and decision-boundary guidance
- [ADR 1.4 adoption guide](versions/1.4/adopt.md) — exact options, outputs, migration, and verification
- [Current family adoption guide](adopt.md) — concise enable/reconcile workflow
- [ADR 1.4 agent summary](versions/1.4/agent-summary.md) — compact operating rules
- [Family index](standard.toml) — indexed payload and digest

## Use this standard when

Use ADRs for significant, costly-to-reverse architecture decisions. Package 1.4 retains the MADR 1.0 body contract while adding explicit authoring guidance for the governed concern, governed population, applicability condition, exclusions, and reserved authority. It also supplies a create-only ADR scaffold and optional validation of MADR's three required level-2 sections.

Markdown Frontmatter is a companion, not a package dependency; enable it separately when ADR metadata also needs schema and ID validation.

## Adopt

```bash
project-standards standards enable adr --version 1.4
project-standards reconcile
project-standards reconcile --apply
```

Review [adopt.md](adopt.md) before applying. Reconciliation preserves consumer-authored ADRs and creates the scaffold only when it is absent. Existing create-only scaffolds are not overwritten during an upgrade.

## Released-version errata

The immutable 1.1 README incorrectly says this repository has no `docs/adr/` tree. The repository already dogfooded the convention when 1.1 was published; retain the released payload bytes but treat that sentence as a known factual error.

## Legacy boundary

Copy-adopt commands, `.project-standards.yml` fragments, and unversioned V1 templates are migration evidence only. They do not define current Catalog 5 behavior. Use `.standards/config.toml`, the central lock, and the exact `versions/1.4/` payload.
