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

- Dogfood the standards through the extracted candidate-wheel runtime described in [README.md](README.md#developing-this-repository): `uv run project-standards validate` must pass with that runtime first on `PYTHONPATH`.
- Never add frontmatter to `CLAUDE.md`, `AGENTS.md`, or `.claude/**`.
- Keep the `AGENTS.md` toolchain gate green; coherence tests require `npm ci`.
- The schema is a versioned contract — see `docs/handoff/conventions.md`.

<!-- prettier-ignore-start -->

<!-- BEGIN project-standards:agent-handoff -->
<!-- markdownlint-disable MD025 -->
# Agent Handoff

Use the repo-local `agent-handoff` skill at session startup and closeout. Do not reread state already injected by SessionStart. Keep project knowledge inside this repository and store credential references only, never values.
<!-- markdownlint-enable MD025 -->
<!-- END project-standards:agent-handoff -->

<!-- prettier-ignore-end -->

<!-- prettier-ignore-start -->

<!-- BEGIN project-standards:markdown-tooling -->
<!-- markdownlint-disable MD025 -->
# Markdown and structured-text tooling

Prettier owns physical formatting and markdownlint owns Markdown structure. Do not add overlapping tools.

Enabled checks: format, lint.
Markdown scope: `**/*.md`.
Structured-config scope: `**/*.json`, `**/*.jsonc`, `**/*.yml`, `**/*.yaml`.
Lint additionally skips generated directories: `.pytest_cache/**`, `.ruff_cache/**`, `.venv/**`, `node_modules/**`.

Check formatting over exactly that scope, with Git as the corpus authority:

```bash
git ls-files -z -- ':(glob)**/*.md' ':(glob)**/*.json' ':(glob)**/*.jsonc' ':(glob)**/*.yml' ':(glob)**/*.yaml' | xargs -0 -r npx prettier --check --
```

Without Git, bound the same scope by glob instead:

```bash
npx prettier --check --no-error-on-unmatched-pattern -- '**/*.md' '**/*.json' '**/*.jsonc' '**/*.yml' '**/*.yaml'
```

Never check or write with a bare `.`: it reaches undeclared languages and Git-excluded scratch.

Lint Markdown structure over the same Git-tracked scope:

```bash
git ls-files -z -- ':(glob)**/*.md' ':(glob,exclude).pytest_cache/**' ':(glob,exclude).ruff_cache/**' ':(glob,exclude).venv/**' ':(glob,exclude)node_modules/**' | sed -z 's|^|:|' | xargs -0 -r npx markdownlint-cli2 --no-globs
```

Never lint a bare recursive glob: it descends into any independent Git repository checked out below this one.

Run the enabled checks before claiming completion.
<!-- markdownlint-enable MD025 -->
<!-- END project-standards:markdown-tooling -->

<!-- prettier-ignore-end -->

<!-- prettier-ignore-start -->

<!-- BEGIN project-standards:python-tooling -->
<!-- markdownlint-disable MD025 -->
# Python tooling

Use uv for environments and dependency changes. Ruff owns formatting, linting, and imports.
Use basedpyright in strict mode for type checking. Do not add a competing Python gate.

Run before claiming completion:

```bash
uv run ruff format --check src tests
uv run ruff check src tests
uv run basedpyright
uv run coverage run -m pytest
uv run coverage report
uv run pip-audit
```

When the gate reports formatting or lint findings, run:

```bash
uv run ruff format src tests
uv run ruff check src tests --fix
```
<!-- markdownlint-enable MD025 -->
<!-- END project-standards:python-tooling -->

<!-- prettier-ignore-end -->

<!-- prettier-ignore-start -->

<!-- BEGIN project-standards:github-workflow -->
<!-- markdownlint-disable MD025 -->
# GitHub Workflow

Load the repo-local `github-workflow` skill before creating or mutating GitHub work state — issues, field values, pull requests, lifecycle transitions, milestones — before triage, and before an organization-schema audit. This repository's work belongs to the `L3DigitalNet` organization. These rules bind even when the skill was never loaded:

- Never infer readiness: an open issue is not `Ready` until acceptance criteria exist and it was deliberately admitted to the executable queue.
- Never promote your own `Execution mode`, and never create, rename, or retire an organization issue type, field, or value — that schema is human-applied.
- A nontrivial pull request links the issue that governs it.
- Keep terminal state synchronized: `Done` closes as completed, `Dropped` closes as not planned, and a reopened issue returns to a nonterminal `Workflow` value in the same action.
- Durable follow-up work discovered while implementing becomes an issue before the session ends.

<!-- markdownlint-enable MD025 -->
<!-- END project-standards:github-workflow -->

<!-- prettier-ignore-end -->
