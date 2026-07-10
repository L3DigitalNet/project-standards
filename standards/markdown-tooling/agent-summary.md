# Markdown Tooling Standard: Agent Summary

The canonical [README](README.md) is authoritative and wins if this summary conflicts with it.

Lifecycle: active. Adoption: `copy-adopt`.

## Use this summary when

Format or structurally lint Markdown and adjacent JSON, JSONC, or YAML, or adopt the repository's reusable documentation workflows.

## Core rules

- Prettier is the sole physical-formatting authority. Preserve the shipped configuration, including `proseWrap: 'never'`, and accept its output instead of hand-formatting around it.
- markdownlint owns Markdown structure and diagnostics. Its rules are tuned to avoid competing with Prettier; fix content rather than weakening the rule set.
- EditorConfig supplies the shared editor floor. Markdown keeps `trim_trailing_whitespace = false` because two trailing spaces can be a meaningful hard break.
- Exactly one tool may mutate a file on save: Prettier formats; markdownlint diagnoses. Do not enable markdownlint fix-on-save alongside Prettier.
- Copy-adopt the configs and caller workflows. The reusable `lint-markdown.yml` gate is active when adopted; `format.yml` is opt-in and can be deferred with `prettier: false`.
- Keep formatter and linter ignore boundaries aligned so local checks, editor behavior, and CI operate on the same scope.

## Commands and artifacts

```bash
npx prettier --write .
npx markdownlint-cli2 --fix "**/*.md"
npx prettier --check .
npx markdownlint-cli2 "**/*.md"
project-standards adopt markdown-tooling
```

Run the fix pass before the non-mutating completion checks. The adopt command installs the standard configs, shared EditorConfig and VS Code recommendations, and reusable workflow callers.

## Boundaries and companions

This standard does not validate YAML frontmatter semantics or IDs. Markdown Frontmatter is a companion with separate Python validation and a separate workflow. Do not add competing formatters or structural linters without a conformant ADR exception.

## Canonical resources

Read the [standard](README.md) for the exact configuration and authority rationale, and the [adoption guide](adopt.md) for copy-adopt steps.
