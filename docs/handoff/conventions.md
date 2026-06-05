# Conventions

LLM-targeted pattern library for this repo. Check this file before adding a persistent pattern; add new patterns here before session end.

## Quick Reference

| # | Title | Applies when |
| --- | --- | --- |
| 1 | Dogfood the standards | Editing managed Markdown (`standards/`, `examples/`, `CHANGELOG.md`) |
| 2 | Never frontmatter agent-instruction files | Touching `CLAUDE.md`, `AGENTS.md`, `.claude/**` |
| 3 | Keep the toolchain green | Changing the validator or its tests |
| 4 | The schema is a versioned contract | Changing the schema or controlled vocabularies |

## 1. Dogfood the standards

**Applies when:** editing managed Markdown here — `standards/`, `examples/`, `CHANGELOG.md`.

**Rule:** managed Markdown carries canonical frontmatter and must validate; run the validator before finishing.

**Code:**

```bash
uv run validate-frontmatter --config .project-standards.yml
```

**Why:** this repo is the source of the standard; if its own managed docs don't validate, the standard isn't credible.

**Sources:** pre-v3 `AGENTS.md` "General" section.

**Related:** 2, 4.

## 2. Never add frontmatter to agent-instruction files

**Applies when:** touching `CLAUDE.md`, `AGENTS.md`, or anything under `.claude/`, `.agents/`, `.codex/`.

**Rule:** these are harness configuration, not managed documents — never add frontmatter. They are excluded from validation in `.project-standards.yml`.

**Why:** frontmatter on a harness file is meaningless and would fail the schema's date/id patterns.

**Sources:** pre-v3 `AGENTS.md`; `.project-standards.yml`.

**Related:** 1.

## 3. Keep the toolchain green

**Applies when:** changing the validator (`tools/`) or its tests.

**Rule:** run all three before committing — every one must pass.

**Code:**

```bash
uv run pytest && uv run ruff check . && uv run pyright
```

**Why:** `main` must stay releasable; consumers pin to tags.

**Sources:** pre-v3 `AGENTS.md`.

**Related:** 4.

## 4. The schema is a versioned contract

**Applies when:** changing `schemas/markdown-frontmatter.schema.json` or the controlled vocabularies.

**Rule:** update `standards/`, templates, examples, tests, and `CHANGELOG.md` together, then cut a new tag (minor = additive, major = breaking).

**Why:** consumers pin to tags; a silent schema change breaks them.

**Sources:** pre-v3 `AGENTS.md`.

**Related:** 1, 3.
