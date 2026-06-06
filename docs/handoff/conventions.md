# Conventions

LLM-targeted pattern library for this repo. Check this file before adding a persistent pattern; add new patterns here before session end.

## Quick Reference

| # | Title | Applies when |
| --- | --- | --- |
| 1 | Dogfood the standards | Editing managed Markdown (`standards/**`, `meta/**`, `CHANGELOG.md`) |
| 2 | Never frontmatter agent-instruction files | Touching `CLAUDE.md`, `AGENTS.md`, `.claude/**` |
| 3 | Keep the toolchain green | Changing the validator or its tests |
| 4 | The schema is a versioned contract | Changing the schema or controlled vocabularies |
| 5 | Python tooling follows the SSOT standard | Adding or changing Python tooling, CI gate, or layout |
| 6 | Standards live in per-standard bundles | Adding/moving a standard, template, or example |

## 1. Dogfood the standards

**Applies when:** editing managed Markdown here — `standards/**` (bundle `README.md`, `adopt.md`, examples), `meta/**`, `CHANGELOG.md`. Per-standard `templates/` and the `standards/README.md` index are excluded.

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

**Applies when:** changing the validator (`src/project_standards/`) or its tests.

**Rule:** run all six before committing — every one must pass.

**Code:**

```bash
uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit
```

**Why:** `main` must stay releasable; consumers pin to tags.

**Sources:** pre-v3 `AGENTS.md`.

**Related:** 4.

## 4. The schema is a versioned contract

**Applies when:** changing `src/project_standards/schemas/markdown-frontmatter.schema.json` or the controlled vocabularies.

**Rule:** update `standards/`, templates, examples, tests, and `CHANGELOG.md` together, then cut a new tag (minor = additive, major = breaking).

**Why:** consumers pin to tags; a silent schema change breaks them.

**Sources:** pre-v3 `AGENTS.md`.

**Related:** 1, 3.

## 5. Python tooling follows the SSOT standard

**Applies when:** adding or changing Python tooling, the CI gate, package layout, or agent instructions for Python projects.

**Rule:** follow `standards/python-tooling/README.md` — `uv_build` backend, `src/` layout, `basedpyright` strict, branch coverage (`fail_under = 85`), `pip-audit`, and the six-step gate.

**Why:** ensures every Python project in this ecosystem is recoverable, repeatable, and self-explaining for agents.

**Sources:** `standards/python-tooling/README.md` (adopted 2026-06-06).

**Related:** 3.

## 6. Standards live in per-standard bundles

**Applies when:** adding, moving, or renaming a standard, template, or example.

**Rule:** each governing standard is a self-contained bundle — `standards/<name>/{README.md, adopt.md, templates/, examples/}` (`templates/`/`examples/` optional; Python-tooling is doc-only). The standard doc is always `README.md`; repo-meta (versioning) lives in `meta/`, not `standards/`. A new standard = copy the anatomy documented in `standards/README.md`.

**Why:** keeps each standard browseable and independently adoptable, and makes adding the next one mechanical.

**Sources:** `standards/README.md`; `docs/superpowers/specs/2026-06-06-standards-bundle-restructure-design.md`.

**Related:** 1, 5.
