# CLAUDE.md

**Session startup:** live state is injected by the shared repo-local SessionStart hook; do not read `docs/handoff/state.md` directly.

**Purpose:** single source of truth for reusable standards — defines seven released or v5-staged standards: **Markdown Frontmatter**, **ADR**, **Markdown Tooling**, **Python Tooling SSOT**, **Project Specification**, **CLI Documentation**, and **Agent Handoff** — plus two unreleased/reference standards: **Python Coding** and **Standard Bundle Authoring** (`adoption = "none"`, the `standard.toml` bundle contract).

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
- Keep the full toolchain gate listed in `AGENTS.md` green; coherence tests require `npm ci`.
- The schema is a versioned contract — see `docs/handoff/conventions.md`.

<!-- BEGIN agent-handoff managed instructions -->
Use the repo-local `$agent-handoff` skill at startup and closeout.
Do not reread `docs/handoff/state.md` when SessionStart already injected it.
Keep current status and tasks in `docs/STATUS.md` and `docs/TODO.md`; route durable facts through `docs/handoff/`.
At closeout, update only changed facts, preserve user-authored work, store credential references only, and run relevant validation.
<!-- END agent-handoff managed instructions -->
