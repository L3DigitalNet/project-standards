---
schema_version: '1.1'
id: 'markdown-tooling-adoption'
title: 'Adopt the Markdown Tooling Standard'
description: 'How to adopt the Markdown Tooling Standard: seed the markdownlint rule set and EditorConfig, copy the Prettier config, and wire the reusable lint workflow.'
doc_type: 'runbook'
status: 'active'
created: '2026-06-07'
updated: '2026-06-07'
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

## Steps

1. **Seed the rule set + floor.** Copy `.markdownlint.json` (the markdownlint rule set) and `.editorconfig` from this repo.

2. **Copy the formatter config (optional).** Copy `.prettierrc.json`; pin Prettier via a minimal `package.json` devDep or run `npx prettier@<version>`.

3. **Wire the reusable linter.** Add a job calling the workflow:

   ```yaml
   jobs:
     lint-markdown:
       uses: L3DigitalNet/project-standards/.github/workflows/lint-markdown.yml@v2
       with:
         globs: '**/*.md'
   ```

4. **Add the VS Code recommendations:** `esbenp.prettier-vscode` + `DavidAnson.vscode-markdownlint`.

5. **Select the contract version (optional)** in `.project-standards.yml`:

   ```yaml
   markdown_tooling:
     version: '1.0'
   ```

   This is validated-if-present metadata only — it runs no check by itself; the markdownlint workflow is the enforcement.

6. **Run the check contract** (standard "Core contract") to confirm clean.

7. **Need an exception?** Record an ADR; see the [ADR Standard](../adr/README.md).

Unlike the Markdown **Frontmatter** standard, the linter half ships a reusable workflow but no Python validator runs over Markdown bodies. The formatter half is copy-adopt only, with no workflow or programmatic enforcement. The contract version is a validated label surfaced in `.project-standards.yml` — it is metadata only and runs no check by itself.
