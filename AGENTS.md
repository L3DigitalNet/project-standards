# AGENTS.md

**Session state:** the startup hook injects `docs/handoff/state.md`; do not reread it. Check `docs/handoff/conventions.md` before adding persistent patterns.

**Conventions:** [`docs/handoff/conventions.md`](docs/handoff/conventions.md)

## Repo Purpose

This repo is the source of truth for reusable project standards. Catalog 5 has seven consumer packages plus reference-only **Python Coding** and internal **Standard Bundle Authoring 2.0**. `.standards/config.toml` selects immutable packages; reconciliation composes them under one lock. See [README.md](README.md).

## Structure

| Path | Purpose |
| --- | --- |
| `standards/<name>/` | bundles: standard, manifest, adoption guide, templates, examples |
| `meta/` | repo policy, including the release contract |
| `src/project_standards/`, `tests/` | Python implementation and tests |
| `.github/workflows/` | reusable consumer workflows |
| `docs/specs/` | maintained Project Specification documents |
| `docs/handoff/` | durable Agent Handoff project knowledge and session state |
| `docs/superpowers/` | historical designs, research, and implementation plans |

## Working Rules

- **Sub-agents.** Individual agents and headless Codex are pre-authorized. Ask before agent teams or orchestration, with a cost sketch. Never use Fable; use Haiku only for mechanical work, Sonnet+ for substantive work, and Opus for adversarial review. Set the model.
- **Self-containment.** This conventions source does not import global agent conventions. It dogfoods repo-local Agent Handoff; do not add workstation ownership.
- **Dogfood.** Validate managed Markdown with `uv run project-standards validate --config .project-standards.yml`. ADR 0015 excludes `standards/**` so packages do not ship repo metadata.
- **Markdown Tooling.** Prettier and markdownlint remain the formatting and structure authorities.
- **Never add frontmatter to agent-instruction files** — `CLAUDE.md`, `AGENTS.md`, `.claude/**`, `.agents/**`, `.codex/**`.
- **Keep the toolchain green** before committing validator/test changes: Ruff format/check, BasedPyright, `uv run python scripts/run_repository_tests.py`, `pip-audit`, and `tests/coherence` after `npm ci`. The repository test runner keeps ordinary/release/performance phases serial and parallelizes only the source/wheel compatibility matrix.
- **Keep package contracts green.** Under `uv run project-standards standards`, run `validate-packages --root . --json`, `validate-graph --root . --require-all-manifests --json`, `generate-package-schemas --root . --check`, and `sync-payload-projection --root . --check`. Keep `.standards/` absent until atomic v5 release commit.
- **The schema is versioned** — see `docs/handoff/conventions.md` #4.
- `README.md` is the human-facing landing page, excluded from frontmatter validation.

<!-- BEGIN agent-handoff managed instructions -->
Use the repo-local `$agent-handoff` skill at startup and closeout.
Do not reread `docs/handoff/state.md` when SessionStart already injected it.
Keep current status and tasks in `docs/STATUS.md` and `docs/TODO.md`; route durable facts through `docs/handoff/`.
At closeout, update only changed facts, preserve user-authored work, store credential references only, and run relevant validation.
<!-- END agent-handoff managed instructions -->
