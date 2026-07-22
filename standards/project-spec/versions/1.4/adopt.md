# Adopt Project Specification 1.4

Use this package for tiered project specifications with stable section numbers, typed IDs, deterministic validation, and provider-backed authoring. The common V5 control-plane lifecycle—initialization, preview, apply, update, disable, removal, and catalog refresh—is documented by `project-standards`. This guide covers Project Specification choices and verification.

## Enable and configure

Initialize the consumer control plane when the repository does not already have one, then enable the package and apply the reviewed reconciliation plan:

```bash
project-standards init --catalog 5
project-standards standards enable project-spec --version 1.4
project-standards reconcile
project-standards reconcile --apply
```

The package has seven closed options in `.standards/config.toml`:

```toml
[standards.project-spec]
enabled = true
version = "1.4"

[standards.project-spec.config]
contract_version = "1.1"
workflow_mode = "caller"
workflow_ownership = "managed"
include_patterns = ["docs/specs/**/*.md"]
reference_prefixes = ["RQ", "GAP"]
default_profile = "standard"
ci = true
```

- `contract_version` selects the document contract independently of package version `1.4`.
- `workflow_mode` selects a reusable `v5` caller or an immutable `self-hosted` workflow.
- `workflow_ownership` defaults to `managed`; select `consumer-owned` during migration to preserve a customized legacy validation workflow and keep that path outside reconciliation and lock state.
- `include_patterns` is the nonempty set of consumer-root-relative specification globs used by `validate` and `lint` discovery.
- `reference_prefixes` lists uppercase external ID namespaces that may be cited but not defined by a specification. Canonical spec-local prefixes such as `FR` are rejected.
- `default_profile` is `light`, `standard`, or `full` and is used when a provider request does not select a profile explicitly.
- `ci` controls the package-managed validation caller. When false, the stable caller remains present with its job disabled; changing the option does not transfer ownership.

Project specifications have their own `spec_id`, status, profile, and relationship frontmatter. If Markdown Frontmatter is also enabled, keep the two packages' `include_patterns` disjoint so one document is not governed by two metadata schemas.

## Author and inspect specifications

All selected-mode paths are relative to the consumer root. Absolute paths, traversal, and symlinked parents or leaves are refused.

```bash
project-standards spec new docs/specs/my-feature.md \
  --profile standard \
  --title "My Feature"
project-standards spec validate
project-standards spec lint --strict
project-standards spec extract docs/specs/my-feature.md §7
project-standards spec next docs/specs/my-feature.md FR
project-standards spec upgrade docs/specs/my-feature.md --to full --stdout
```

`new --stdout` and `upgrade --stdout` use the read-only preview provider and write nothing. File-producing `new` and `upgrade` requests return typed mutation plans that the platform executor applies with containment, symlink, precondition, and mode checks. Tier upgrades are additive: they insert missing canonical sections without renumbering existing sections or rewriting authored prose.

## Managed output and CI

Reconciliation manages `.github/workflows/validate-specs.yml`. The caller invokes the reusable workflow at `v5` and requests strict linting. Both caller and self-hosted modes run bare `spec validate` and `spec lint --strict` commands; the CLI resolves `.standards/` authority and the selected package without an explicit legacy `--config` override.

Verify the selected state and the reconciled caller:

```bash
project-standards reconcile --check
project-standards spec validate
project-standards spec lint --strict
```

Validation findings exit `1`. Usage, selected-package, configuration, containment, and authoring refusals exit `2`. `lint` exits `1` only with `--strict` and at least one warning.

## Migration and disable behavior

Automatic migration maps the legacy specification settings semantically into the seven closed package options and recognizes only the exact released validation caller bytes. A customized legacy caller blocks by default; setting `workflow_ownership: "consumer-owned"` in the legacy configuration preserves it without claiming the path. Settings owned by other selected packages are migrated by those packages; other modified or unclaimed state blocks apply without changing the repository.

Preview and apply a repository migration through the generic boundary:

```bash
project-standards init --catalog 5 --migrate
project-standards init --catalog 5 --migrate --apply
```

Disabling the package and reconciling removes its managed workflow and lock ownership. Consumer-authored specification documents remain untouched:

```bash
project-standards standards disable project-spec
project-standards reconcile
project-standards reconcile --apply
```

## Package resources

- [Canonical standard](README.md)
- [Agent summary](agent-summary.md)
- [Worked example](examples/spec.example.md)
- [Light, Standard, and Full templates](templates/)
- [Tooling notes](resources/tooling-notes.md)

## Troubleshooting

| Finding | Resolution |
| --- | --- |
| No specification files match configured `include_patterns` | Package 1.4 and later compatible 1.x versions report an informational success without invoking validation providers. Add the first specification when ready. |
| Markdown Frontmatter also selects a spec | Make the two package corpora disjoint; project specs use their own metadata schema. |
| Authoring path is unsafe or already changed | Re-preview and resolve the path/precondition; do not bypass the executor. |
| Managed workflow drift | Restore the selected caller/self-hosted bytes or change `workflow_mode` and reconcile. |
