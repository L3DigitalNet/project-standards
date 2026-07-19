# Adopt Markdown Frontmatter 1.3

Use this package when a repository needs consistent, schema-validated metadata on a selected Markdown corpus. It supplies the standard, templates and examples, a repo-local authoring skill, a reusable CI caller, and version-selected validate, inspect, fix, and legacy-migration providers.

The common control-plane lifecycle—initialization, catalog selection, preview, apply, upgrade, disable, and removal—is defined in the [project-standards V5 CLI guide](https://github.com/L3DigitalNet/project-standards/blob/v5/docs/usage.md). This guide covers only the choices and verification specific to `markdown-frontmatter@1.3`.

## Suitability and boundaries

Adopt this package when Markdown metadata must be searchable, stable, or machine validated. The package governs only the leading YAML frontmatter block. Markdown body formatting belongs to the companion Markdown Tooling package; ADR body structure belongs to the companion ADR package.

Never add managed-document frontmatter to harness instructions or agent assets. Keep `AGENTS.md`, `CLAUDE.md`, `.agents/**`, `.claude/**`, and `.codex/**` excluded. A public landing-page `README.md` may also be excluded when its rendered metadata table would be undesirable.

## Enable and configure

Use the [V5 CLI guide](https://github.com/L3DigitalNet/project-standards/blob/v5/docs/usage.md) to initialize the repository when needed. Then enable the exact package:

```bash
project-standards standards enable markdown-frontmatter --version 1.3
```

Edit only the package options under `.standards/config.toml`. A complete explicit configuration is:

```toml
[standards.markdown-frontmatter]
enabled = true
version = "1.3"

[standards.markdown-frontmatter.config]
contract_version = "1.1"
workflow_mode = "caller"
schema = "markdown-frontmatter"
required = true
include = ["README.md", "docs/**/*.md"]
exclude = [
  "**/*.template.md",
  "AGENTS.md",
  "CLAUDE.md",
  ".agents/**",
  ".claude/**",
  ".codex/**",
  ".github/**",
  "node_modules/**",
]

[standards.markdown-frontmatter.config.references]
enabled = false
```

Follow the V5 CLI guide for preview and apply mechanics. Applying this package installs the repo-local skill under `.agents/skills/markdown-frontmatter/`, records the package summary under `.standards/packages/markdown-frontmatter/`, and composes the Frontmatter job into `.github/workflows/validate-standards.yml`. In `self-hosted` mode it also manages `.github/workflows/validate-markdown-frontmatter.yml`, which the composed job calls from the same commit. A second reconciliation must report no changes.

## Package options

| Option | Default | Purpose |
| --- | --- | --- |
| `contract_version` | `"1.1"` | Select the frontmatter document contract independently of package version `1.3`. |
| `workflow_mode` | `"caller"` | Use the published reusable workflow; select `"self-hosted"` when the endpoint must come from the same repository commit. |
| `schema` | `"markdown-frontmatter"` | Use the bundled schema; set to `"custom"` only with `schema_path`. |
| `schema_path` | omitted | Repository-relative path to a consumer-owned custom JSON Schema. |
| `required` | `true` | Require a frontmatter block on every selected document. |
| `include` | `README.md`, `docs/**/*.md` | Select managed Markdown paths. |
| `exclude` | harness, template, workflow, and dependency paths | Remove paths from the managed corpus. |
| `references.enabled` | `false` | Enable duplicate-ID and cross-document reference validation. |

The package selector and document-contract selector are different controls. `version = "1.3"` selects the immutable package payload; `contract_version = "1.1"` selects the schema behavior exposed by that payload.

## Custom schema input

For a custom contract, commit the schema inside the repository—prefer `.standards/extensions/markdown-frontmatter/`—and configure both fields:

```toml
[standards.markdown-frontmatter.config]
schema = "custom"
schema_path = ".standards/extensions/markdown-frontmatter/schema.json"
```

The extension remains consumer-owned. Reconciliation records its path and digest but never overwrites or deletes it. A missing file, symlink escape, path outside the repository, or overlap with a managed output blocks reconciliation.

## Bring existing documents into compliance

Run the formatter in check mode first:

```bash
format-frontmatter --check
```

The aggregate fix command formats frontmatter, repairs ordinary invalid IDs, constructs one complete typed mutation plan, applies it through the platform executor, and re-runs schema, ID, and enabled reference validation:

```bash
project-standards fix
```

ADR IDs require a repository-name segment and remain a manual repair. Custom schemas skip the bundled fix behavior because they may define a different ID contract.

Review every generated description, title, lifecycle value, owner, tag, and relationship. The formatter can establish safe structure; it cannot decide repository-specific semantics.

## Validate

Run the same contract locally that the generated workflow calls:

```bash
project-standards validate
format-frontmatter --check
```

`project-standards validate` runs schema validation, ID validation, optional reference validation, and unified control-plane validation. Exit codes are `0` for success, `1` for document findings or drift, and `2` for invalid configuration, schema, authority, or invocation.

The standalone commands remain available for focused diagnosis:

```bash
validate-frontmatter
validate-id
validate-references
```

An explicit `--config PATH` is a read-only V5 legacy/debug path. It emits the legacy warning and must not be combined with `.standards/` authority.

## Migrate a V4 consumer

When `.project-standards.yml` contains `markdown.frontmatter`, preview migration instead of running plain initialization:

```bash
project-standards init --catalog 5 --migrate
```

The migration maps the recognized namespace to package options and recognizes only the exact previously shipped Frontmatter workflow, skill, and skill-script bytes. A recognized workflow selects `workflow_mode = "self-hosted"`: migration adopts that path as the V5 reusable endpoint and composes a same-commit caller, so the first release run does not depend on an unpublished `v5` tag. Modified or unknown content blocks automatic ownership transfer and remains untouched. Review the complete report, then follow the V5 CLI guide's explicit migration-apply procedure without changing the inspected repository state.

The legacy YAML file is removed only after unified configuration, reconciliation, provider verification, and central-lock publication succeed.

## Compliance checklist

- [ ] `.standards/config.toml` enables `markdown-frontmatter@1.3` with accurate include and exclude patterns.
- [ ] Harness instructions and agent assets are excluded.
- [ ] Every selected document conforms to contract `1.1` or the declared custom schema.
- [ ] Ordinary IDs use `{doc_type}-{base36-6}-{frozen-kebab-slug}`; ADR IDs use the ADR format.
- [ ] `.agents/skills/markdown-frontmatter/` matches the selected payload.
- [ ] `.github/workflows/validate-standards.yml` contains the V5 Frontmatter job.
- [ ] In `self-hosted` mode, `.github/workflows/validate-markdown-frontmatter.yml` matches the selected payload and the composed job uses its local path.
- [ ] `project-standards validate` and `format-frontmatter --check` exit `0`.
- [ ] A second `project-standards reconcile` is a no-op.

## Authoritative resources

- [Standard](README.md)
- [Structure requirements](structure.md)
- [Field-value policy](field-values.md)
- [Option schema](config.schema.json)
- [Agent summary](agent-summary.md)
- [Repo-local skill](skills/markdown-frontmatter/SKILL.md)

The option schema governs package configuration, and `schemas/markdown-frontmatter.schema.json` governs document metadata. If prose conflicts with either schema, the applicable schema wins.
