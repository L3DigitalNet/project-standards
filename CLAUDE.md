# CLAUDE.md

**Session startup:** live state is injected by the SessionStart hook (`.claude/hooks/session_start.py`); do not read `docs/handoff/state.md` directly.

**Purpose:** single source of truth for reusable standards — defines six: **Markdown Frontmatter** and **ADR** (validator-enforced via a reusable CI workflow), **Markdown Tooling** (copy-adopt markdownlint/Prettier/EditorConfig + optional `lint-markdown.yml`/`format.yml`), **Python Tooling SSOT** (copy-adopt scaffolds), **Project Specification** (tiered specs + stable IDs, `project-standards spec` CLI + `validate-specs.yml`), and **CLI Documentation** (usage-doc standard, adopt-materialized scaffolds + `cli_documentation` contract) — plus two unreleased: **Python Coding** (reference-only draft) and **Standard Bundle Authoring** (internal/reference meta-standard, `adoption = "none"`, the `standard.toml` bundle contract).

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
