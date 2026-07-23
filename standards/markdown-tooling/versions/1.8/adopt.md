# Adopt Markdown Tooling 1.7

This package manages the Markdown Tooling configuration, caller workflows, and bounded shared-container contributions. Use the generic lifecycle commands documented in the project-standards CLI usage reference at `docs/usage.md` to initialize a repository, enable this package, preview or apply reconciliation, update its selected version, and disable it.

## Package options

Configure these fields under the `markdown-tooling` package selection:

- `contract_version`: the independent Markdown Tooling contract selector; package 1.7 supports `1.1`.
- `workflow_mode`: `caller` uses reusable workflows pinned to `v5`; `self-hosted` installs immutable in-repository jobs without a remote standards dependency. The default is `caller`.
- `lint` and `format`: enable markdownlint structure checks and Prettier physical-format checks independently.
- `ci.lint_caller` and `ci.format_caller`: add automatic push and pull-request triggers to the corresponding managed caller. A disabled caller remains installed with only `workflow_dispatch`, so toggling enforcement does not churn ownership.
- `lint_workflow_ownership` and `format_workflow_ownership`: `managed` (the default) lets the package render, verify, and lock the corresponding caller workflow; `consumer-owned` leaves that path outside reconciliation, verification, and lock state so a customized caller stays with the consumer.
- `markdownlint_config_ownership`: `managed` (the default) lets the package own `.markdownlint.json`; `consumer-owned` preserves a customized legacy config and keeps that path outside reconciliation, verification, and lock state.
- `markdown_globs`: Markdown included by the lint caller and described in the bounded agent guidance.
- `config_globs`: JSON, JSONC, and YAML scope passed with `markdown_globs` to the managed formatter caller and described in bounded agent guidance.
- `exclusions`: typed `{glob, applies_to, reason}` records. `applies_to` is `lint`, `format`, or `both`; every exception is reviewable instead of being an untyped ignore string.

When `lint` or `format` is false, its matching CI caller option must also be false. Disabling both caller options produces manual-only workflows; it does not remove the managed caller files.

The managed instruction blocks display selected globs as inline code. Because the schema excludes backticks from glob values, this preserves wildcard characters literally without creating ambiguous Markdown emphasis.

## Managed outputs

The package exclusively manages these whole files:

- `.markdownlint.json`
- `.prettierrc.json`
- `.github/workflows/lint-markdown.yml`
- `.github/workflows/format.yml`

It composes only declared semantic units in these consumer containers:

- EditorConfig global, Markdown, and YAML properties in `.editorconfig`
- the Prettier and markdownlint recommendation entries in `.vscode/extensions.json`
- each declared formatter setting under the Markdown, JSON, JSONC, and YAML objects in `.vscode/settings.json`
- one `markdown-tooling` managed block in each of `AGENTS.md` and `CLAUDE.md`

Unrelated properties, recommendations, settings, and instruction text remain consumer-owned. A later package may share an identical contribution through the same normalized shared identity without depending on this package.

## Boundaries and companions

Prettier is the sole physical-formatting authority for supported structured text. markdownlint owns Markdown structure and diagnostics; it does not fix on save. This package does not own Python formatting, frontmatter schemas, document IDs, arbitrary VS Code settings, or whole instruction files.

Markdown Frontmatter is a companion only. Either package can be enabled independently, and this package has no hidden dependency on it.

## Migration

The automatic V4 migration maps only `markdown_tooling.version` into `contract_version` and recognizes exact released bytes for the two configs, two callers, legacy shared EditorConfig, and legacy VS Code recommendations. Exact exclusive files transfer to managed ownership; exact shared containers are preserved while their declared units are adopted semantically.

Modified legacy root configuration is reported as a migration conflict and preserved. Resolve the local intent before retrying migration; the provider never writes the repository, accesses the network, or emits an active `.project-standards.yml` fragment.

A `.markdownlint.json` that is byte-for-byte the shipped config re-serialized with literal (non-escaped) UTF-8 punctuation is accepted as known legacy content and migrates to managed ownership of the escaped bytes; it is not treated as a modified config.

Generic plan, apply, update, and disable behavior is delegated to the unified control plane. The central `.standards/lock.toml` records ownership; this package creates no package-local lock.

## Verify and troubleshoot

```bash
project-standards reconcile --check
```

Run a local tool only when its matching `lint` or `format` option is `true`:

- For markdownlint, pass every selected `markdown_globs` value followed by each exclusion whose `applies_to` value is `lint` or `both`, prefixed with `!`.
- For Prettier, pass every selected `markdown_globs` and `config_globs` value and supply each exclusion whose `applies_to` value is `format` or `both` through an additional `--ignore-path` file.

These local commands require the corresponding packages to be installed; the managed reusable lint caller supplies its own action runtime. With `npx --no-install`, install the repository's lockfile-defined Node dependencies first, normally with `npm ci`. The reconciled workflow is the canonical option-aware CI verification.

| Finding | Resolution |
| --- | --- |
| A disabled tool still has its CI caller enabled | Disable the matching caller option or enable the tool. |
| Shared container contribution conflicts | Preserve unrelated content and reconcile only the declared property, recommendation, or managed block. |
| Managed config or workflow drift | Restore the locked bytes or change package options and reconcile deliberately. |
| V4 artifact is modified | A modified `.editorconfig` or `.vscode/extensions.json` is preserved automatically with a `CP-MIGRATION-BOUNDED-TAKEOVER` warning; a modified caller workflow is preserved by declaring `lint_workflow_ownership` or `format_workflow_ownership` as `"consumer-owned"` in the legacy configuration before migrating; a modified `.markdownlint.json` is preserved with `markdownlint_config_ownership = "consumer-owned"`; other modified exclusive configs block until their known content is restored. |
