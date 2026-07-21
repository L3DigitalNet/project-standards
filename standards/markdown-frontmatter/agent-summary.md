# Markdown Frontmatter family: Agent Summary

Current authority is the Catalog 5 consumer payload [`markdown-frontmatter@1.4`](versions/1.4/agent-summary.md). Its [versioned standard](versions/1.4/README.md) wins over this mutable navigation summary.

- Apply metadata rules only to paths selected by the package options in `.standards/config.toml`.
- Keep the independent package version and document `contract_version` distinct.
- Preserve canonical field order, quoting, list form, ID rules, lifecycle values, and extension boundaries from the selected payload.
- Never add managed-document frontmatter to `CLAUDE.md`, `AGENTS.md`, `.claude/**`, `.agents/**`, or `.codex/**`; exclude harness files from managed scope.
- Use the package's selected validation and fix providers; custom schemas remain consumer-owned inputs and intentionally skip bundled authoring transforms.
- Treat Markdown Tooling and ADR as companions, not implicit dependencies.

Enable `markdown-frontmatter@1.4`, preview with `project-standards reconcile`, and apply only after reviewing the plan. See the [current adoption guide](adopt.md) for the complete procedure.
