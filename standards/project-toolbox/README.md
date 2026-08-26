# Project Toolbox Standard

This is the Catalog 5 family landing page for the consumer package `project-toolbox@1.1`. The immutable versioned payload, not this mutable landing page, defines the selected standard.

## Current authority

- [Project Toolbox 1.1 standard](versions/1.1/README.md) — applicability, delivered inventory, and ownership boundary
- [Project Toolbox 1.1 adoption guide](versions/1.1/adopt.md) — prerequisites, apply, and verification
- [Current family adoption guide](adopt.md) — concise enable/reconcile workflow
- [Project Toolbox 1.1 agent summary](versions/1.1/agent-summary.md) — compact package behavior
- [Family index](standard.toml) — indexed payload and digest

## Use this standard when

Use Project Toolbox in a repository whose periodic maintenance is performed or assisted by agents and should follow one written, versioned procedure. The family is the durable home for proven cross-cutting workflows and tools — assets that fit no existing standard, or that span two or more of them.

Version 1.1 ships a deliberately minimal inventory: a repository-housekeeping sweep, a drift-detection sweep, and the routing skill that points at them, plus a `harnesses` option that gates the Codex-only `openai.yaml` skill sidecar.

## Adopt

```bash
project-standards standards enable project-toolbox --version 1.1
project-standards reconcile
project-standards reconcile --apply
```

The package has one configuration option, `harnesses`; enabling the family with defaults installs its complete inventory for both harnesses.

## Boundary

The package ships documents only — no executable providers, no scripts, no binaries. It requires no other standards package, though both workflows read `.standards/config.toml` and fold each installed package's own gates into the sweep rather than duplicating them. Nothing here mutates the repository outside reconciliation's delivery of its own managed files.

## Family authority

The family root is mutable navigation. The exact `versions/1.1/` payload is the current artifact; corrections to its normative content require a new package version rather than edits in place after publication. New toolbox assets land as additive minor versions of this family.
