# Architecture Decision Record (ADR) Standard

This is the Catalog 5 family landing page for the active consumer package `adr@1.6`. The immutable versioned payload, not this mutable landing page, defines the selected standard.

## Current authority

- [ADR 1.6 standard](versions/1.6/README.md) — normative MADR, document, and decision-boundary guidance
- [ADR 1.6 adoption guide](versions/1.6/adopt.md) — exact options, outputs, migration, and verification
- [Current family adoption guide](adopt.md) — concise enable/reconcile workflow
- [ADR 1.6 agent summary](versions/1.6/agent-summary.md) — compact operating rules
- [Family index](standard.toml) — indexed payload and digest

## Use this standard when

Use ADRs for significant, costly-to-reverse architecture decisions. Package 1.6 retains the MADR 1.0 body contract while supplying a create-only ADR scaffold, decision-boundary guidance, optional validation of MADR's three required level-2 sections, and independent opt-in validation of reciprocal amendment relationships.

The sanctioned **partial amendment** vocabulary uses reciprocal `project.amends` / `project.amended_by` frontmatter lists, a blockquote amendment note between the title and Context and Problem Statement, and an optional `### Amendments` subsection under Decision Outcome. Package 1.6 can validate the reciprocal lists and reject amendment of a superseded ADR when `validate_amendments = true`. The option defaults to `false` and is independent of `require_sections`, so existing consumers keep their prior result until they opt in.

Markdown Frontmatter is a companion, not a package dependency; enable it separately when ADR metadata also needs schema and ID validation.

## Adopt

```bash
project-standards standards enable adr --version 1.6
project-standards reconcile
project-standards reconcile --apply
```

Review [adopt.md](adopt.md) before applying. Reconciliation preserves consumer-authored ADRs and creates the scaffold only when it is absent. Existing create-only scaffolds are not overwritten during an upgrade.

## Released-version errata

The immutable 1.1 README incorrectly says this repository has no `docs/adr/` tree. The repository already dogfooded the convention when 1.1 was published; retain the released payload bytes but treat that sentence as a known factual error.

## Legacy boundary

Copy-adopt commands, `.project-standards.yml` fragments, and unversioned V1 templates are migration evidence only. They do not define current Catalog 5 behavior. Use `.standards/config.toml`, the central lock, and the exact `versions/1.6/` payload.
