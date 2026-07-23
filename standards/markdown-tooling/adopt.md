# Adopt the Markdown Tooling Standard

The current consumer package is [`markdown-tooling@1.8`](versions/1.8/adopt.md). Use it for markdownlint and Prettier configuration, managed lint/format workflows, and bounded EditorConfig, VS Code, and agent-instruction contributions.

## Configure and reconcile

```bash
project-standards standards enable markdown-tooling --version 1.8
project-standards reconcile
project-standards reconcile --apply
```

Options under `[standards.markdown-tooling.config]` select the independent contract, lint/format behavior, CI triggers, Markdown/config globs, typed exclusions, `workflow_mode`, and the `lint_workflow_ownership` and `format_workflow_ownership` decisions. Use `caller` for reusable `@v5` workflows or `self-hosted` for immutable in-repository jobs. The default is `caller`. Each caller is managed by default; set its matching ownership option to `"consumer-owned"` to leave that caller outside reconciliation, verification, and lock state. The package owns its two configs and only the workflow files that remain managed, plus its declared semantic units in shared containers.

## Migrate a V4 repository

```bash
project-standards init --catalog 5 --migrate
project-standards init --catalog 5 --migrate --apply
```

Migration maps `markdown_tooling.version`, transfers only exact exclusive files, and adopts exact shared units semantically. Modified root configuration is preserved and reported as a conflict; resolve local intent before retrying.

## Verify and troubleshoot

```bash
project-standards reconcile --check
```

Run a local tool only when its matching `lint` or `format` option is `true`. For markdownlint, pass every selected `markdown_globs` value followed by each `lint` or `both` exclusion as a negative glob. For Prettier, pass every selected Markdown and config glob and supply each `format` or `both` exclusion through an additional ignore file. These local commands require the corresponding packages to be installed; the managed reusable lint caller supplies its own action runtime. The reconciled workflow is the canonical option-aware CI verification.

Conflicting shared properties, invalid exclusion records, disabled-tool/enabled-CI combinations, or modified managed files block apply. Do not replace consumer-owned container content to resolve a package unit. See the [version-specific guide](versions/1.8/adopt.md) for exact options, managed outputs, companions, migration, and failure handling.
