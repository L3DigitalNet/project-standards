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
- **Dogfood.** Validate managed Markdown with `uv run project-standards validate`. ADR 0015 excludes `standards/**` so packages do not ship repo metadata.
- **Markdown Tooling.** Prettier and markdownlint remain the formatting and structure authorities.
- **Never add frontmatter to agent-instruction files** — `CLAUDE.md`, `AGENTS.md`, `.claude/**`, `.agents/**`, `.codex/**`.
- **Keep the toolchain green** before committing validator/test changes: Ruff format/check and BasedPyright from the source environment; then build/extract the candidate wheel and run ordinary pytest under coverage, the xdist compatibility matrix, serial performance tests, `coverage report`, `pip-audit`, and `tests/coherence` after `npm ci` with the extracted wheel first on `PYTHONPATH`.
- **Keep package contracts green.** Under `uv run project-standards standards`, run `validate-packages --root . --json`, `validate-graph --root . --require-all-manifests --json`, `generate-package-schemas --root . --check`, and `sync-payload-projection --root . --check`.
- **The schema is versioned** — see `docs/handoff/conventions.md` #4.
- `README.md` is the human-facing landing page, excluded from frontmatter validation.

<!-- prettier-ignore-start -->

<!-- BEGIN project-standards:agent-handoff -->
# Agent Handoff

Use the repo-local `agent-handoff` skill at session startup and closeout. Do not reread state already injected by SessionStart. Keep project knowledge inside this repository and store credential references only, never values.
<!-- END project-standards:agent-handoff -->

<!-- prettier-ignore-end -->

<!-- prettier-ignore-start -->

<!-- BEGIN project-standards:markdown-tooling -->
# Markdown and structured-text tooling

Prettier owns physical formatting and markdownlint owns Markdown structure. Do not add overlapping tools.

Enabled checks: format, lint.
Markdown scope: **/*.md.
Structured-config scope: **/*.json, **/*.jsonc, **/*.yml, **/*.yaml.

Run the enabled checks before claiming completion.
<!-- END project-standards:markdown-tooling -->

<!-- prettier-ignore-end -->

<!-- prettier-ignore-start -->

<!-- BEGIN project-standards:python-tooling -->
# Python tooling

Use uv for environments and dependency changes. Ruff owns formatting, linting, and imports.
Use basedpyright in strict mode for type checking. Do not add a competing Python gate.

Run before claiming completion:

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run coverage run -m pytest
uv run coverage report
uv run pip-audit
```

When the gate reports formatting or lint findings, run:

```bash
uv run ruff format .
uv run ruff check . --fix
```
<!-- END project-standards:python-tooling -->

<!-- prettier-ignore-end -->
