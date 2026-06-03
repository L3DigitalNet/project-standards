# AGENTS.md

## Project Purpose

This repository is the **single source of truth** for reusable documentation standards shared across projects. It _defines_ standards and _enforces_ them with a validator; other repositories _consume_ them via a small `.project-standards.yml` config plus a reusable CI workflow, rather than vendoring their own copies.

What lives here:

- `standards/` — the human-readable governing documents (Markdown Frontmatter Standard, ADR Standard)
- `schemas/` — machine-readable JSON Schemas
- `templates/` and `examples/` — copy-paste scaffolds and validated worked examples
- `tools/` + `tests/` — the Python validator and its tests
- `.github/workflows/` — the reusable workflow consumers call

See [README.md](README.md) for the full surface and consumption instructions.

## General

- **MANDATORY: stay self-contained.** Do not import external/global agent conventions into this repo — in particular the workstation **v3 handoff system** (its `docs/` lifetime-partitioning, SessionStart hooks, or tracked global config files). This repo is itself a conventions source. The single sanctioned exception is the self-contained session handoff below.
- **Session handoff.** [`working/HANDOFF.md`](working/HANDOFF.md) is the living handoff: read it at session start, keep it current during work, update it at session end. It is just one file plus `working/archive/<version>/` (frozen per-release planning docs) — no hooks, no global config, nothing outside `working/`. See the header of `HANDOFF.md` for the ritual. `working/**` is scratch space and is excluded from frontmatter validation.
- **Dogfood the standards.** Managed Markdown here (`standards/`, `examples/`, `CHANGELOG.md`) carries canonical frontmatter and must validate. Run the validator before finishing: `uv run validate-frontmatter --config .project-standards.yml`.
- **Never add frontmatter to agent-instruction files** — `CLAUDE.md`, `AGENTS.md`, and anything under `.claude/`, `.agents/`, `.codex/`. They are harness configuration, not managed documents.
- **Keep the toolchain green.** Before committing changes to the validator or tests, run `uv run pytest`, `uv run ruff check .`, and `uv run pyright` — all must pass.
- **The schema is a contract.** Changing `schemas/markdown-frontmatter.schema.json` or the controlled vocabularies is a versioned change: update `standards/`, templates, examples, tests, and the `CHANGELOG.md`, then cut a new tag (minor = additive, major = breaking). Consumers pin to tags, so `main` must stay releasable.
- `README.md` is the human-facing landing page and is intentionally excluded from frontmatter validation.
