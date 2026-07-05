---
schema_version: '1.1'
id: 'runbook-uw0j7m-adopt-the-markdown-tooling-standard'
title: 'Adopt the Markdown Tooling Standard'
description: 'How to adopt the Markdown Tooling Standard: seed the markdownlint rule set and EditorConfig, copy the Prettier config, and wire the reusable lint workflow.'
doc_type: 'runbook'
status: 'active'
created: '2026-06-07'
updated: '2026-07-05'
reviewed: null
owner: ''
consumer: 'agent'
tags:
  - 'adoption'
  - 'markdown'
  - 'linting'
  - 'formatting'
aliases: []
related:
  - 'standards/markdown-tooling/README.md'
source: []
confidence: 'high'
visibility: 'public'
license: null
---

# Adopt the Markdown Tooling Standard

The **linter** half ships a reusable workflow and a seedable rule set; the **formatter** half (Prettier) is copy-adopt with no workflow. The contract version is a validated label, not a body gate.

## Quick adoption (CLI)

As of `v3`, the packaged CLI materializes every artifact below in one command:

```bash
uvx --from 'git+https://github.com/L3DigitalNet/project-standards@v4' \
  project-standards adopt markdown-tooling
```

This drops `.markdownlint.json`, `.prettierrc.json`, the shared `.editorconfig` and `.vscode/extensions.json`, and the `lint-markdown.yml` workflow caller (pinned to the current released major). Existing files are skipped unless you pass `--force`. The manual steps below remain the reference for what each artifact is and how to wire it by hand.

## Steps

1. **Seed the rule set + floor.** Copy `.markdownlint.json` (the markdownlint rule set) and `.editorconfig` from this repo.

2. **Copy the formatter config (optional).** Copy `.prettierrc.json`; pin Prettier via a minimal `package.json` devDep or run `npx prettier@<version>`.

3. **Wire the reusable linter.** Add a job calling the workflow:

   ```yaml
   jobs:
     lint-markdown:
       uses: L3DigitalNet/project-standards/.github/workflows/lint-markdown.yml@v4
       with:
         globs: '**/*.md'
   ```

4. **Add the VS Code recommendations:** `esbenp.prettier-vscode` + `DavidAnson.vscode-markdownlint`. When the repo uses VS Code, also merge the standard's `[markdown]`/`[json]`/`[jsonc]`/`[yaml]` formatter blocks (standard §10) into `.vscode/settings.json` — in a repo that also adopted Python Tooling, that file already exists with the Python blocks; add these alongside, do not replace it.

5. **Add the agent instruction block.** Append the standard's §12 block to `AGENTS.md` (or the canonical instruction source it points to). In a repo that also adopted Python Tooling, the CLI-delivered `AGENTS.md` contains only the Python contract — the two blocks are designed to sit side by side.

6. **Select the contract version (optional)** in `.project-standards.yml`:

   ```yaml
   markdown_tooling:
     version: '1.0'
   ```

   This is validated-if-present metadata only — it runs no check by itself; the markdownlint workflow is the enforcement.

7. **Run the check contract** (standard "Core contract") to confirm clean.

8. **Need an exception?** Record an ADR; see the [ADR Standard](../adr/README.md).

Unlike the Markdown **Frontmatter** standard, the linter half ships a reusable workflow but no Python validator runs over Markdown bodies. The formatter half is copy-adopt only, with no workflow or programmatic enforcement. The contract version is a validated label surfaced in `.project-standards.yml` — it is metadata only and runs no check by itself.
