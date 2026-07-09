# AGENTS.md

**Session state:** injected at startup by the SessionStart hook (don't ritual-read `docs/handoff/state.md`), then this file, then `docs/handoff/conventions.md`.

**Full conventions reference:** [`docs/handoff/conventions.md`](docs/handoff/conventions.md) — LLM-targeted pattern library. Check it before adding persistent patterns.

**Detailed review workflows:** not configured for this repo.

## Repo Purpose

This repo is the **single source of truth** for reusable project standards. It defines six released standards — **Markdown Frontmatter**, **ADR**, **Project Specification**, **Markdown Tooling** (copy-adopt markdownlint/Prettier/EditorConfig + optional `lint-markdown.yml`/`format.yml`), **Python Tooling SSOT**, and **CLI Documentation** — plus two unreleased/reference documents: **Python Coding** and **Standard Bundle Authoring** (`adoption = "none"`, defines `standard.toml`). Consumers use config + reusable workflows or copy-adopt scaffolds rather than vendoring standards. See [README.md](README.md) for the full surface.

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

- **Sub-agent policy (updated 2026-07-08, standing — not v5-scoped).** Individual sub-agents (one `Agent` dispatch at a time — implementer/reviewer, Explore/Plan/general-purpose) and headless Codex may be used **without asking each time**, where appropriate. **Agent teams / multi-agent orchestration (the `Workflow` tool, fleets) are NOT pre-authorized** — the owner rescinded that on cost / token grounds; **ask first with a rough cost sketch** before any team fan-out. Models: **never Fable**; **Haiku OK for trivial / mechanical** work; **Sonnet** is the floor for substantive work and **Opus** for judgment-heavy / adversarial review; set the model explicitly.
- **Conventions-source self-containment.** This repo defines conventions, so it does **not** import other external/global agent conventions. The single sanctioned exception is the workstation **v3 handoff system**, adopted 2026-06-05 (`docs/handoff/` + the SessionStart hook). Do not layer further global/workstation conventions on top of it.
- **Dogfood the standards.** Managed Markdown (`CHANGELOG.md`, `UPGRADING.md`, `docs/usage.md`, `meta/**`, `docs/adr/**`) must validate: `uv run project-standards validate --config .project-standards.yml`. `standards/**` is excluded from this repo's local frontmatter scope by ADR 0015 so standard packages do not ship repo-local metadata.
- **Never add frontmatter to agent-instruction files** — `CLAUDE.md`, `AGENTS.md`, `.claude/**`, `.agents/**`, `.codex/**`.
- **Keep the toolchain green** before committing validator/test changes: `uv run ruff format --check .`, `uv run ruff check .`, `uv run basedpyright`, `uv run coverage run -m pytest`, `uv run coverage report`, `uv run pip-audit`, `uv run pytest tests/coherence` (the markdownlint/Prettier co-satisfaction gate; needs `npm ci`).
- **The schema is a versioned contract** — see `docs/handoff/conventions.md` #4.
- `README.md` is the human-facing landing page, excluded from frontmatter validation.
