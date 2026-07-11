# Adopt ADR 1.1

Use this package when a repository needs MADR-based decision records, a standard scaffold, and optional enforcement of the three required MADR sections.

The common V5 control-plane lifecycle—initialization, preview, apply, disable, removal, and catalog updates—is documented by `project-standards`. This guide covers ADR-specific choices only.

## Enable and configure

Enable the package independently:

```bash
project-standards standards enable adr --version 1.1
project-standards reconcile --apply
```

The package has two closed options:

```toml
[standards.adr]
enabled = true
version = "1.1"

[standards.adr.config]
contract_version = "1.0"
require_sections = false
```

`contract_version` selects the ADR document/body contract independently of package version `1.1`. Set `require_sections = true` to require `## Context and Problem Statement`, `## Considered Options`, and `## Decision Outcome` on `doc_type: adr` snapshots.

## Frontmatter companion

Markdown Frontmatter is a companion, not a dependency. ADR alone can install the create-only scaffold and validate MADR sections. Enable Markdown Frontmatter separately when the repository also wants schema, ID, date, and cross-document reference validation. Neither package implicitly enables the other.

## Author and verify

Reconciliation creates `docs/adr/adr.template.md` only when that consumer-owned scaffold is absent. Existing bytes are preserved by the create-only policy. Copy it to `docs/adr/adr-NNNN-short-title.md`, replace every placeholder, and update the ADR index.

Verify selected state and provider behavior:

```bash
project-standards reconcile --check
project-standards validate
```

Legacy `markdown.adr.version` and `markdown.adr.require_sections` settings migrate into package options. The V2 package does not print or install a `.project-standards.yml` fragment.
