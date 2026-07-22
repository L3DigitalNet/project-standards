# Markdown Tooling family: Agent Summary

Current authority is the Catalog 5 consumer payload [`markdown-tooling@1.6`](versions/1.6/agent-summary.md). Its [versioned standard](versions/1.6/README.md) wins over this mutable navigation summary.

- Prettier is the sole physical-formatting authority for Markdown and supported JSON, JSONC, and YAML.
- markdownlint owns Markdown structure and diagnostics. Do not add an overlapping formatter or structural linter.
- The package manages `.prettierrc.json`, `.markdownlint.json`, and separate lint/format workflows while contributing only bounded units to shared containers.
- `lint` and `format` are independently selectable. Disabled callers remain manual workflows and explicitly skip enforcement.
- Keep `.gitignore`, `.prettierignore`, configured globs, and typed exclusions as distinct inputs; do not treat configuration as shell source.
- Markdown Frontmatter is a companion, not a dependency, and remains the authority for metadata semantics and document IDs.

Run the checks selected by the package before completion. See the [current adoption guide](adopt.md) for exact options, migration, and troubleshooting.
