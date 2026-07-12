# Adopt Markdown Tooling 1.2

This package manages the Markdown Tooling configuration, caller workflows, and bounded shared-container contributions. Use the generic lifecycle commands documented in the project-standards CLI usage reference at `docs/usage.md` to initialize a repository, enable this package, preview or apply reconciliation, update its selected version, and disable it.

## Package options

Configure these fields under the `markdown-tooling` package selection:

- `contract_version`: the independent Markdown Tooling contract selector; package 1.2 supports `1.1`.
- `workflow_mode`: `caller` uses reusable workflows pinned to `v5`; `self-hosted` installs immutable in-repository jobs without a remote standards dependency.
- `lint` and `format`: enable markdownlint structure checks and Prettier physical-format checks independently.
- `ci.lint_caller` and `ci.format_caller`: add automatic push and pull-request triggers to the corresponding managed caller. A disabled caller remains installed with only `workflow_dispatch`, so toggling enforcement does not churn ownership.
- `markdown_globs`: Markdown included by the lint caller and described in the bounded agent guidance.
- `config_globs`: JSON, JSONC, and YAML scope passed with `markdown_globs` to the managed formatter caller and described in bounded agent guidance.
- `exclusions`: typed `{glob, applies_to, reason}` records. `applies_to` is `lint`, `format`, or `both`; every exception is reviewable instead of being an untyped ignore string.

When `lint` or `format` is false, its matching CI caller option must also be false. Disabling both caller options produces manual-only workflows; it does not remove the managed caller files.

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

Generic plan, apply, update, and disable behavior is delegated to the unified control plane. The central `.standards/lock.toml` records ownership; this package creates no package-local lock.

## Verify and troubleshoot

```bash
project-standards reconcile --check
npx --no-install markdownlint-cli2 '**/*.md'
npx --no-install prettier --check .
```

| Finding | Resolution |
| --- | --- |
| A disabled tool still has its CI caller enabled | Disable the matching caller option or enable the tool. |
| Shared container contribution conflicts | Preserve unrelated content and reconcile only the declared property, recommendation, or managed block. |
| Managed config or workflow drift | Restore the locked bytes or change package options and reconcile deliberately. |
| V4 artifact is modified | Resolve ownership manually; automatic migration accepts only exact released bytes. |
