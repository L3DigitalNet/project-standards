# Markdown Frontmatter Standard: Agent Summary

The canonical [README](README.md) is authoritative and wins if this summary conflicts with it.

Lifecycle: active. Adoption: `validator`.

## Use this summary when

Add, repair, or validate metadata on Markdown paths managed by `.project-standards.yml`.

## Core rules

- Every managed document has the eleven minimal fields in canonical order: `schema_version`, `id`, `title`, `description`, `doc_type`, `status`, `created`, `updated`, `tags`, `aliases`, and `related`. Most project docs use the richer standard profile.
- Quote strings and dates with single quotes. Use block-style non-empty lists with quoted items and `[]` for empty lists. Reject duplicate list items and unknown top-level fields; extensions belong under `publish`, `project`, or `x_project`.
- Ordinary IDs are `{doc_type}-{six-character-base36-token}-{frozen-kebab-slug}`. ADR IDs are `adr-NNNN-repo-name-short-title`. Generate ordinary IDs with tooling.
- Structure rules define schema, order, syntax, and ID shape. Field-value policy defines lifecycle, ownership, tags, relationships, confidence, visibility, and repository-local vocabulary; adopters should record that policy in an ADR.
- Never add managed-document frontmatter to `CLAUDE.md`, `AGENTS.md`, `.claude/**`, `.agents/**`, or `.codex/**`; exclude those harness files from managed scope.

## Commands and artifacts

```bash
project-standards validate --config .project-standards.yml
format-frontmatter --check --config .project-standards.yml
validate-id --config .project-standards.yml
validate-references --config .project-standards.yml
```

The aggregate validator covers schema, ID, and enabled reference checks. `format-frontmatter` checks or fixes canonical source style. The repo-local [agent skill](skills/markdown-frontmatter/SKILL.md) guides authoring and ID generation in adopting repositories.

## Boundaries and companions

This standard governs metadata, not Markdown body formatting. Markdown Tooling is a companion. ADR is a companion document profile; neither relation silently changes adoption behavior.

## Canonical resources

Use the [standard](README.md), [structure rules](structure.md), [field-value policy](field-values.md), and [adoption guide](adopt.md) for complete requirements.
