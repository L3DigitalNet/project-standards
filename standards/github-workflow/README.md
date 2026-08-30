# GitHub Workflow Standard

This is the Catalog 5 family landing page for the consumer package `github-workflow@1.7`. The immutable versioned payload, not this mutable landing page, defines the selected standard.

## Current authority

- [GitHub Workflow 1.7 standard](versions/1.7/README.md) — applicability, configuration contract, and ownership boundary
- [GitHub Workflow 1.7 adoption guide](versions/1.7/adopt.md) — prerequisites, options, apply, and verification
- [Current family adoption guide](adopt.md) — concise enable/reconcile workflow and consumer-guard exemptions
- [GitHub Workflow 1.7 agent summary](versions/1.7/agent-summary.md) — compact package behavior
- [Family index](standard.toml) — indexed payload and digest

## Use this standard when

Use GitHub Workflow in a repository owned by a GitHub organization whose work is tracked as issues and pull requests, and whose agent sessions should follow one shared discipline before touching that work state. It treats an issue as the authorized work contract, organization-level issue fields as its typed operational metadata, and a pull request as execution evidence.

It does not apply to personal-account repositories: organization-level issue fields do not exist outside an organization, and the package offers no fallback that operates without them.

## Adopt

```bash
project-standards standards enable github-workflow --version 1.7
project-standards reconcile
project-standards reconcile --apply
```

Both configuration options are required. Review [the 1.7 adoption guide](versions/1.7/adopt.md) before applying.

## Boundary

The package reports differences between live organization schema and its versioned baseline; a human applies organization schema changes. It never sets the repository-local threshold for when a change requires a pull request, and it never manipulates rulesets, branch protection, or merge gating.

## Family authority

The family root is mutable navigation. The exact `versions/1.7/` payload is the current artifact; corrections to its normative content require a new package version rather than edits in place after publication.
