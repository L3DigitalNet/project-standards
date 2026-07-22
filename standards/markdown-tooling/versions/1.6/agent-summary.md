# Markdown Tooling 1.6: Agent Summary

The canonical [standard](README.md) is authoritative. Use the [adoption guide](adopt.md) for package-specific options, outputs, migration, and ownership; use `docs/usage.md` from the project-standards distribution for generic lifecycle commands.

Prettier is the sole physical-formatting authority for Markdown and supported JSON, JSONC, and YAML. markdownlint owns Markdown structure and diagnostics. Never add an overlapping formatter or structural linter.

The package manages `.prettierrc.json`, `.markdownlint.json`, and distinct lint/format caller workflows. Each caller can be relinquished with its `lint_workflow_ownership` or `format_workflow_ownership` option; a customized legacy `.markdownlint.json` can be preserved with `markdownlint_config_ownership = "consumer-owned"`, which also removes that path from package verification and lock state. It contributes only bounded EditorConfig properties, VS Code settings and extension entries, and managed Markdown instruction blocks. Preserve all unrelated consumer content.

`lint` and `format` select checks independently. CI caller options select automatic triggers; a disabled caller remains present as a manual `workflow_dispatch` workflow and passes a false enforcement flag so the reusable job skips. Typed exclusions name their tool scope and rationale. The format caller passes selected Markdown/config globs and exclusions to the reusable workflow, which keeps `.gitignore`, `.prettierignore`, and configured exclusions as separate ignore sources without treating config as shell source.

Run the enabled checks before completion:

```bash
npx prettier --check .
npx markdownlint-cli2 "**/*.md"
```

Markdown Frontmatter is a companion, not a dependency. This package never validates frontmatter semantics or document IDs.
