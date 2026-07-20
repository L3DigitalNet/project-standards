# Adopt the Markdown Tooling Standard

The current consumer package is [`markdown-tooling@1.3`](versions/1.3/adopt.md). Use it for markdownlint and Prettier configuration, managed lint/format workflows, and bounded EditorConfig, VS Code, and agent-instruction contributions.

## Configure and reconcile

```bash
project-standards standards enable markdown-tooling --version 1.3
project-standards reconcile
project-standards reconcile --apply
```

Options under `[standards.markdown-tooling.config]` select the independent contract, lint/format behavior, CI triggers, Markdown/config globs, typed exclusions, and `workflow_mode`. Use `caller` for reusable `@v5` workflows or `self-hosted` for immutable in-repository jobs. The default is `caller`. The package owns its two configs and two workflow files, plus only its declared semantic units in shared containers.

## Migrate a V4 repository

```bash
project-standards init --catalog 5 --migrate
project-standards init --catalog 5 --migrate --apply
```

Migration maps `markdown_tooling.version`, transfers only exact exclusive files, and adopts exact shared units semantically. Modified root configuration is preserved and reported as a conflict; resolve local intent before retrying.

## Verify and troubleshoot

```bash
project-standards reconcile --check
npx --no-install markdownlint-cli2 '**/*.md'
npx --no-install prettier --check .
```

Conflicting shared properties, invalid exclusion records, disabled-tool/enabled-CI combinations, or modified managed files block apply. Do not replace consumer-owned container content to resolve a package unit. See the [version-specific guide](versions/1.3/adopt.md) for exact options, managed outputs, companions, migration, and failure handling.
