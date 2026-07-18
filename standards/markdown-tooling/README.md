# Markdown Tooling Standard

This is the Catalog 5 family landing page for the active consumer package `markdown-tooling@1.2`. The immutable versioned payload, not this mutable landing page, defines the selected standard.

## Current authority

- [Markdown Tooling 1.2 standard](versions/1.2/README.md) — normative Prettier, markdownlint, EditorConfig, and workflow contract
- [Markdown Tooling 1.2 adoption guide](versions/1.2/adopt.md) — exact options, managed outputs, migration, and verification
- [Current family adoption guide](adopt.md) — concise enable/reconcile workflow
- [Markdown Tooling 1.2 agent summary](versions/1.2/agent-summary.md) — compact authority and completion rules
- [Family index](standard.toml) — indexed payload and digest

## Use this standard when

Use Markdown Tooling to make Prettier the sole physical formatter for Markdown and supported JSON, JSONC, and YAML while markdownlint owns Markdown structure and diagnostics. Package 1.2 manages its two configs and lint/format workflows and composes only declared units in shared EditorConfig, VS Code, and agent-instruction containers.

## Adopt

```bash
project-standards standards enable markdown-tooling --version 1.2
project-standards reconcile
project-standards reconcile --apply
```

Review [adopt.md](adopt.md) before applying. Lint and format checks, workflow mode, triggers, globs, and typed exclusions are package options in `.standards/config.toml`.

## Legacy boundary

Root copy-adopt configs, reusable-workflow pins from earlier majors, `project-standards adopt markdown-tooling`, and `.project-standards.yml` fragments are migration evidence only. They do not define current Catalog 5 behavior.
