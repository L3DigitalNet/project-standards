# Adopt the Project Specification Standard

The current consumer package is [`project-spec@1.3`](versions/1.3/adopt.md). Use it for Light, Standard, and Full project specifications with stable sections, typed identifiers, deterministic validation/linting, and provider-backed scaffold and upgrade operations.

## Configure and reconcile

```bash
project-standards standards enable project-spec --version 1.2
project-standards reconcile
project-standards reconcile --apply
```

Options under `[standards.project-spec.config]` select the independent contract, spec include globs, external reference prefixes, default profile, CI, and `workflow_mode`. Use `caller` for the reusable `@v5` workflow or `self-hosted` for an immutable in-repository job. Keep Project Specification and Markdown Frontmatter corpora disjoint.

Reconciliation manages `.github/workflows/validate-specs.yml`. Its reusable workflow runs bare `spec validate` and `spec lint --strict` commands so the CLI—not a workflow-level legacy override—resolves `.standards/` authority. Authoring commands such as `spec new` and `spec upgrade` return typed plans; the platform executor performs file writes after path and precondition checks.

## Migrate a V4 repository

```bash
project-standards init --catalog 5 --migrate
project-standards init --catalog 5 --migrate --apply
```

Migration maps the legacy `spec` namespace and exact released validation workflow. Modified, overlapping, or unclaimed state blocks the atomic apply without changing the repository.

## Verify and troubleshoot

```bash
project-standards spec validate
project-standards spec lint --strict
project-standards reconcile --check
```

An empty corpus, invalid profile, unsafe authoring path, schema overlap, or managed-workflow drift fails closed. Use `--stdout` to review scaffolds/upgrades without writing. See the [version-specific guide](versions/1.3/adopt.md) for exact options, commands, outputs, migration, disable semantics, and troubleshooting.
