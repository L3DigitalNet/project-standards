# AGENTS.md

**Session state:** injected at startup by the SessionStart hook (don't ritual-read `docs/handoff/state.md`), then this file, then `docs/handoff/conventions.md`.

**Full conventions reference:** [`docs/handoff/conventions.md`](docs/handoff/conventions.md) — LLM-targeted pattern library. Check it before adding persistent patterns.

## Repo Purpose

This repo is the **single source of truth** for reusable project standards. It defines seven released or v5-staged standards — **Markdown Frontmatter**, **ADR**, **Project Specification**, **Markdown Tooling** (copy-adopt markdownlint/Prettier/EditorConfig + optional `lint-markdown.yml`/`format.yml`), **Python Tooling SSOT**, **CLI Documentation**, and **Agent Handoff** — plus two unreleased/reference documents: **Python Coding** and **Standard Bundle Authoring** (`adoption = "none"`, defines `standard.toml`). Consumers use config + reusable workflows or copy-adopt scaffolds rather than vendoring standards. See [README.md](README.md) for the full surface.

## Structure

| Path | Purpose |
| --- | --- |
| `standards/<name>/` | per-standard bundles (`README.md` = the standard, `standard.toml` manifest, `adopt.md` for adoptable standards, optional `templates/` + `examples/`); `standards/README.md` is the index |
| `meta/` | repo-meta documents (e.g. `versioning.md`, the release contract) — not governed standards |
| `src/project_standards/` + `tests/` | the Python validator (with bundled schema) and its tests |
| `.github/workflows/` | the reusable workflows consumers call |
| `docs/handoff/` | durable Agent Handoff project knowledge and session state |
| `docs/superpowers/` | specs (`specs/`) and implementation plans (`plans/`) |

## Working Rules

- **Sub-agent policy (standing).** Individual sub-agents and headless Codex are pre-authorized. Agent teams and multi-agent orchestration are not; ask first with a rough cost sketch. Never use Fable; use Haiku only for trivial/mechanical work, Sonnet or better for substantive work, and Opus for judgment-heavy/adversarial review. Set the model explicitly.
- **Conventions-source self-containment.** This repo defines conventions, so it does **not** import external/global agent conventions. It dogfoods the repo-local **Agent Handoff** standard (`docs/handoff/` + project SessionStart hook). Do not layer global/workstation ownership onto it.
- **Dogfood the standards.** Managed Markdown (`CHANGELOG.md`, `UPGRADING.md`, `docs/usage.md`, `docs/workflows/**`, `meta/**`, `docs/adr/**`) must validate: `uv run project-standards validate --config .project-standards.yml`. `standards/**` is excluded from this repo's local frontmatter scope by ADR 0015 so standard packages do not ship repo-local metadata.
- **Never add frontmatter to agent-instruction files** — `CLAUDE.md`, `AGENTS.md`, `.claude/**`, `.agents/**`, `.codex/**`.
- **Keep the toolchain green** before committing validator/test changes: `uv run ruff format --check .`, `uv run ruff check .`, `uv run basedpyright`, `uv run coverage run -m pytest`, `uv run coverage report`, `uv run pip-audit`, `uv run pytest tests/coherence` (the markdownlint/Prettier co-satisfaction gate; needs `npm ci`).
- **The schema is a versioned contract** — see `docs/handoff/conventions.md` #4.
- `README.md` is the human-facing landing page, excluded from frontmatter validation.

<!-- BEGIN agent-handoff managed instructions -->
Use the repo-local `$agent-handoff` skill at startup and closeout.
Do not reread `docs/handoff/state.md` when SessionStart already injected it.
Keep current status and tasks in `docs/STATUS.md` and `docs/TODO.md`; route durable facts through `docs/handoff/`.
At closeout, update only changed facts, preserve user-authored work, store credential references only, and run relevant validation.
<!-- END agent-handoff managed instructions -->
