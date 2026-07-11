# ADR 1.1 summary

The canonical [README](README.md) is authoritative and wins if this summary conflicts with it.

- Package version: `1.1`; ADR contract option: `1.0`.
- Availability: consumer.
- Managed output: create-only `docs/adr/adr.template.md`.
- Optional `require_sections` validates the three MADR-required level-2 headings on ADR documents.
- Markdown Frontmatter is a companion only. ADR can be enabled, reconciled, disabled, and removed without selecting Frontmatter.
- Legacy `markdown.adr.version` maps to `contract_version`; `require_sections` retains its boolean value.
- No V2 output contains a `.project-standards.yml` fragment.

Use [adopt.md](adopt.md) for package-specific adoption and verification.
