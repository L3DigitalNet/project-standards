# Adopt the Markdown Frontmatter Standard

The current consumer package is [`markdown-frontmatter@1.5`](versions/1.5/adopt.md). Use it for schema-validated metadata over an explicit Markdown corpus, the repo-local authoring skill, the composed validation workflow, and provider-backed validate/inspect/fix operations.

## Configure and reconcile

```bash
project-standards standards enable markdown-frontmatter --version 1.5
project-standards reconcile
project-standards reconcile --apply
```

Options under `[standards.markdown-frontmatter.config]` select the independent document `contract_version`, caller or self-hosted workflow mode, bundled or custom schema, required/optional frontmatter, include/exclude globs, and reference validation. Exclude harness instructions, agent assets, workflow files, and `**/*.template.md`. A custom schema remains a consumer-owned referenced input.

Managed outputs include the repo-local Markdown Frontmatter skill, package summary, and the package-owned job in `.github/workflows/validate-standards.yml`. `workflow_mode = "caller"` uses the published `@v5` endpoint; `workflow_mode = "self-hosted"` also installs the endpoint in the consumer repository and makes the composed job call it locally. Consumer Markdown bodies remain consumer-owned.

## Migrate a V4 repository

```bash
project-standards init --catalog 5 --migrate
project-standards init --catalog 5 --migrate --apply
```

Migration maps `markdown.frontmatter`, recognizes exact released workflow and skill bytes, and selects self-hosted workflow delivery for the recognized legacy endpoint. It removes `.project-standards.yml` only after the complete unified state validates. Modified or unknown artifacts block apply and remain untouched.

## Verify and troubleshoot

```bash
project-standards validate
format-frontmatter --check
project-standards reconcile --check
```

Schema findings, invalid IDs, path escapes, managed-output overlap, and custom-schema ambiguity fail closed. Use `project-standards fix` only after reviewing its typed plan; custom schemas intentionally skip bundled fixes. See the [version-specific guide](versions/1.5/adopt.md) for exact options, outputs, migration rules, verification, and compliance checks.
