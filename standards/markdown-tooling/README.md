# Markdown Tooling Standard

This is the Catalog 5 family landing page for the active consumer package `markdown-tooling@1.5`. The immutable versioned payload, not this mutable landing page, defines the selected standard.

## Current authority

- [Markdown Tooling 1.5 standard](versions/1.5/README.md) — normative Prettier, markdownlint, EditorConfig, and workflow contract
- [Markdown Tooling 1.5 adoption guide](versions/1.5/adopt.md) — exact options, managed outputs, migration, and verification
- [Current family adoption guide](adopt.md) — concise enable/reconcile workflow
- [Markdown Tooling 1.5 agent summary](versions/1.5/agent-summary.md) — compact authority and completion rules
- [Family index](standard.toml) — indexed payload and digest

## Use this standard when

Use Markdown Tooling to make Prettier the sole physical formatter for Markdown and supported JSON, JSONC, and YAML while markdownlint owns Markdown structure and diagnostics. Package 1.5 manages its two configs and lint/format workflows and composes only declared units in shared EditorConfig, VS Code, and agent-instruction containers.

## Adopt

```bash
project-standards standards enable markdown-tooling --version 1.5
project-standards reconcile
project-standards reconcile --apply
```

Review [adopt.md](adopt.md) before applying. Lint and format checks, workflow mode, triggers, globs, and typed exclusions are package options in `.standards/config.toml`.

## Released-version errata

In the immutable 1.5 README, “a modified … caller workflow remains blocking” applies only while its matching ownership option remains `managed`. Setting `lint_workflow_ownership` or `format_workflow_ownership` to `"consumer-owned"` preserves that customized caller and leaves it outside reconciliation, verification, and lock state. Modified managed config still blocks.

## Legacy boundary

Root copy-adopt configs, reusable-workflow pins from earlier majors, `project-standards adopt markdown-tooling`, and `.project-standards.yml` fragments are migration evidence only. They do not define current Catalog 5 behavior.
