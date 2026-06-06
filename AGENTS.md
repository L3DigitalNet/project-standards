# AGENTS.md

**Session state:** read `docs/handoff/state.md`, then this file, then `docs/handoff/conventions.md`.

**Full conventions reference:** [`docs/handoff/conventions.md`](docs/handoff/conventions.md) — LLM-targeted pattern library. Check it before adding persistent patterns.

**Detailed review workflows:** not configured for this repo.

## Repo Purpose

This repository is the **single source of truth** for reusable documentation standards shared across projects. It _defines_ three standards (Markdown Frontmatter, ADR, Python Tooling SSOT) and _enforces_ the Markdown ones with a Python validator. Other repositories _consume_ the Markdown standards via a small `.project-standards.yml` plus a reusable CI workflow (rather than vendoring copies), and adopt the Python Tooling SSOT standard by copying its scaffolds. See [README.md](README.md) for the full surface.

## Structure

| Path | Purpose |
| --- | --- |
| `standards/<name>/` | per-standard bundles (`README.md` = the standard, `adopt.md`, optional `templates/` + `examples/`); `standards/README.md` is the index |
| `meta/` | repo-meta documents (e.g. `versioning.md`, the release contract) — not governed standards |
| `src/project_standards/` + `tests/` | the Python validator (with bundled schema) and its tests |
| `.github/workflows/` | the reusable workflows consumers call |
| `docs/handoff/` | agent session state (handoff-system-v3) |
| `docs/superpowers/` | specs (`specs/`) and implementation plans (`plans/`) |

## Working Rules

- **Conventions-source self-containment.** This repo defines conventions, so it does **not** import other external/global agent conventions. The single sanctioned exception is the workstation **v3 handoff system**, adopted 2026-06-05 (`docs/handoff/` + the SessionStart hook). Do not layer further global/workstation conventions on top of it.
- **Dogfood the standards.** Managed Markdown (`standards/**`, `meta/**`, `CHANGELOG.md` (per-standard `templates/` and the `standards/README.md` index excluded)) must validate: `uv run validate-frontmatter --config .project-standards.yml`.
- **Never add frontmatter to agent-instruction files** — `CLAUDE.md`, `AGENTS.md`, `.claude/**`, `.agents/**`, `.codex/**`.
- **Keep the toolchain green** before committing validator/test changes: `uv run ruff format --check .`, `uv run ruff check .`, `uv run basedpyright`, `uv run coverage run -m pytest`, `uv run coverage report`, `uv run pip-audit`.
- **The schema is a versioned contract** — see `docs/handoff/conventions.md` #4.
- `README.md` is the human-facing landing page, excluded from frontmatter validation.
