# CLAUDE.md

**Session startup:** the repo hook injects live state; do not reread `docs/handoff/state.md`.

**Purpose:** source of truth for reusable standards. Catalog 5 has seven consumer packages plus reference-only **Python Coding** and internal **Standard Bundle Authoring**.

**Markdown Tooling:** Prettier and markdownlint remain the formatting and structure authorities; see `AGENTS.md` for the gate.

**`docs/handoff/` layout (read on demand):**

- `state.md` — live state and incidents (auto-injected)
- `deployed.md` — published consumer pins
- `architecture.md` — component graph and backlog
- `credentials.md` — credential references
- `conventions.md` — pattern library; check before adding patterns
- `specs-plans.md` — spec and plan pointers
- `sessions/` and `bugs/` — history and lessons

Maintained Project Specification documents live under `docs/specs/`.

## Non-Negotiables

- Dogfood the standards: `uv run project-standards validate --config .project-standards.yml` must pass.
- Never add frontmatter to `CLAUDE.md`, `AGENTS.md`, or `.claude/**`.
- Keep the `AGENTS.md` toolchain gate green; coherence tests require `npm ci`.
- The schema is a versioned contract — see `docs/handoff/conventions.md`.

<!-- BEGIN agent-handoff managed instructions -->
Use the repo-local `$agent-handoff` skill at startup and closeout.
Do not reread `docs/handoff/state.md` when SessionStart already injected it.
Keep current status and tasks in `docs/STATUS.md` and `docs/TODO.md`; route durable facts through `docs/handoff/`.
At closeout, update only changed facts, preserve user-authored work, store credential references only, and run relevant validation.
<!-- END agent-handoff managed instructions -->
