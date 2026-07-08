# AGENTS.md

**Session state:** injected at startup by the SessionStart hook (don't ritual-read `docs/handoff/state.md`), then this file, then `docs/handoff/conventions.md`.

**Full conventions reference:** [`docs/handoff/conventions.md`](docs/handoff/conventions.md) — LLM-targeted pattern library. Check it before adding persistent patterns.

**Detailed review workflows:** not configured for this repo.

## Repo Purpose

This repository is the **single source of truth** for reusable standards shared across projects. It _defines_ six released standards — **Markdown Frontmatter**, **ADR**, and **Project Specification** (validator-enforced: downstream repos run a reusable CI workflow; Project Specification via the `project-standards spec` CLI plus `validate-specs.yml`), plus **Markdown Tooling** (copy-adopt scaffolds + optional reusable `lint-markdown.yml`/`format.yml` workflows), **Python Tooling SSOT**, and **CLI Documentation** (copy-adopt scaffolds). Two documents ship unreleased and outside that count: **Python Coding** (`standards/python-coding/`), an in-development reference-only draft, and **Standard Bundle Authoring** (`standards/standard-bundle-authoring/`), the internal/reference meta-standard (`adoption = "none"`) that defines the `standard.toml` bundle contract. Other repositories _consume_ the six released standards by config + workflow (validator-enforced) or by copying scaffolds (copy-adopt), rather than vendoring copies. See [README.md](README.md) for the full surface.

## Structure

| Path | Purpose |
| --- | --- |
| `standards/<name>/` | per-standard bundles (`README.md` = the standard, `standard.toml` manifest, `adopt.md` for adoptable standards, optional `templates/` + `examples/`); `standards/README.md` is the index |
| `meta/` | repo-meta documents (e.g. `versioning.md`, the release contract) — not governed standards |
| `src/project_standards/` + `tests/` | the Python validator (with bundled schema) and its tests |
| `.github/workflows/` | the reusable workflows consumers call |
| `docs/handoff/` | agent session state (handoff-system-v3) |
| `docs/superpowers/` | specs (`specs/`) and implementation plans (`plans/`) |

## Working Rules

- **v5 build-out — agent teams pre-authorized (until v5.0.0 releases).** For the Meta-repo / MCP-readiness effort you may use subagents, agent teams, and headless Codex **without asking each time**. Spawn only **Sonnet** (mechanical / parallel-breadth / transcription) or **Opus** (complex reasoning, design, review) by task complexity — **never Fable or Haiku**. Reverts to ask-first once v5.0.0 is cut. See `docs/handoff/state.md` (Ops notes) + the v5.0.0 tracker in `TODO.md`.
- **Conventions-source self-containment.** This repo defines conventions, so it does **not** import other external/global agent conventions. The single sanctioned exception is the workstation **v3 handoff system**, adopted 2026-06-05 (`docs/handoff/` + the SessionStart hook). Do not layer further global/workstation conventions on top of it.
- **Dogfood the standards.** Managed Markdown (`standards/**`, `meta/**`, `CHANGELOG.md` (per-standard `templates/` and the `standards/README.md` index excluded)) must validate: `uv run validate-frontmatter --config .project-standards.yml`.
- **Never add frontmatter to agent-instruction files** — `CLAUDE.md`, `AGENTS.md`, `.claude/**`, `.agents/**`, `.codex/**`.
- **Keep the toolchain green** before committing validator/test changes: `uv run ruff format --check .`, `uv run ruff check .`, `uv run basedpyright`, `uv run coverage run -m pytest`, `uv run coverage report`, `uv run pip-audit`, `uv run pytest tests/coherence` (the markdownlint/Prettier co-satisfaction gate; needs `npm ci`).
- **The schema is a versioned contract** — see `docs/handoff/conventions.md` #4.
- `README.md` is the human-facing landing page, excluded from frontmatter validation.
