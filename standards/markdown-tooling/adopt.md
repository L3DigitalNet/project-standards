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

The **linter** half ships a reusable workflow and a seedable rule set; the **formatter** half (Prettier) now also ships a reusable opt-in workflow alongside its copy-adopt config (DEC-10). The contract version is a validated label, not a body gate.

## Quick adoption (CLI)

As of `v3`, the packaged CLI materializes every artifact below in one command:

```bash
uvx --from 'git+https://github.com/L3DigitalNet/project-standards@v4' \
  project-standards adopt markdown-tooling
```

This drops `.markdownlint.json`, `.prettierrc.json`, the shared `.editorconfig` and `.vscode/extensions.json`, and both the `lint-markdown.yml` and `format.yml` workflow callers (pinned to the current released major). Existing files are skipped unless you pass `--force`. The manual steps below remain the reference for what each artifact is and how to wire it by hand.

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

4. **Wire the formatter workflow (opt-in).** Add a job calling the Prettier workflow (or adopt `format.caller.yml`, which the CLI writes as `.github/workflows/format.yml`):

   ```yaml
   jobs:
     format:
       uses: L3DigitalNet/project-standards/.github/workflows/format.yml@v4
   ```

   Format once and commit (`npx prettier@3.8.3 --write .`) before enabling the gate. Not ready to enforce yet? Pass `prettier: false` in the caller to defer — the whole job skips (a clean pass).

5. **Add the VS Code recommendations:** `esbenp.prettier-vscode` + `DavidAnson.vscode-markdownlint`. When the repo uses VS Code, also merge the standard's `[markdown]`/`[json]`/`[jsonc]`/`[yaml]` formatter blocks (standard §10) into `.vscode/settings.json` — in a repo that also adopted Python Tooling, that file already exists with the Python blocks; add these alongside, do not replace it.

6. **Add the agent instruction block.** Append the standard's §12 block to `AGENTS.md` (or the canonical instruction source it points to). In a repo that also adopted Python Tooling, the CLI-delivered `AGENTS.md` contains only the Python contract — the two blocks are designed to sit side by side.

7. **Select the contract version (optional)** in `.project-standards.yml`:

   ```yaml
   markdown_tooling:
     version: '1.1'
   ```

   This is validated-if-present metadata only — it runs no check by itself; the markdownlint workflow is the enforcement.

8. **Run the check contract** (standard "Core contract") to confirm clean.

9. **Need an exception?** Record an ADR; see the [ADR Standard](../adr/README.md).

Unlike the Markdown **Frontmatter** standard, the linter half ships a reusable workflow but no Python validator runs over Markdown bodies. The formatter half now ships an opt-in reusable workflow too (DEC-10), but its enforcement is opt-in — a consumer adopts `format.caller.yml` (or `prettier: false` to defer). The contract version is a validated label surfaced in `.project-standards.yml` — it is metadata only and runs no check by itself.
