# CLAUDE.md

**Session startup:** live state is injected by the SessionStart hook (`.claude/hooks/session_start.py`); do not read `docs/handoff/state.md` directly.

**Purpose:** single source of truth for reusable standards — defines five: **Markdown Frontmatter** and **ADR** (enforced by a Python validator downstream repos run via a reusable CI workflow), **Markdown Tooling** (copy-adopt markdownlint/Prettier/EditorConfig + optional reusable `lint-markdown.yml` and `format.yml` workflows), **Python Tooling SSOT** (copy-adopt scaffolds), and **Project Specification** (tiered spec format + stable IDs, validator-enforced via the `project-standards spec` CLI + `validate-specs.yml` CI) — plus **Python Coding**, an in-development reference-only draft (unregistered, excluded from validation/adopt).

**Document layout (read on demand):**

- `docs/handoff/state.md` — live state + active incidents (auto-injected)
- `docs/handoff/deployed.md` — published tags consumers pin to
- `docs/handoff/architecture.md` — component graph + standing backlog
- `docs/handoff/credentials.md` — credential references (none today)
- `docs/handoff/conventions.md` — pattern library (check before adding patterns)
- `docs/handoff/specs-plans.md` — spec/plan pointer table
- `docs/handoff/sessions/` — monthly session logs
- `docs/handoff/bugs/` — bug KB

## Non-Negotiables

- Dogfood the standards: `uv run validate-frontmatter --config .project-standards.yml` must pass before finishing.
- Never add frontmatter to `CLAUDE.md`, `AGENTS.md`, or `.claude/**`.
- Keep the toolchain green: `uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit && uv run pytest tests/coherence` (the last needs `npm ci` for the behavioral markdownlint/Prettier co-satisfaction tests).
- The schema is a versioned contract — see `docs/handoff/conventions.md`.
