# CLAUDE.md

**Session startup:** the repo hook injects live state; do not reread `docs/handoff/state.md`.

**Purpose:** source of truth for reusable standards. Catalog 5 has nine consumer packages plus reference-only **Python Coding** and internal **Standard Bundle Authoring**.

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

## Heavy Workloads

Run CPU-heavy commands through `rexec -- <command>`: `make go-check` and the full `scripts/verify.sh` — every lane, pytest included, passes remotely since rexec v0.3.0 with `[sync] git_context = true` (committed in `.rexec.toml`), which materializes a sanitized read-only Git context so the ledger seed's `git log` works on the worker (resolves #167 / remote-execution#2; all four lanes proven green remotely 2026-08-15). Worker CT 117 carries the dedicated `/mnt/pytesttmp` tmpfs and workstation umask parity (owned by homelab `provision-toolchain.sh`). Wheel/sdist builds stay local (~2 s compute vs ~12–15 s sync) unless batched before a remote gate needing them — the mirror carries `build/wheel-runtime` to the worker. Pull needed artifacts with `--pull`; declare missing worker tooling in the rexec config and converge with `rexec setup` — provisioning the worker is its purpose. `.venv/` and `node_modules/` are rsync excludes that `setup` does not create, so a new or `rexec clean`-ed worker needs a one-time `rexec --shell 'uv sync --all-groups --locked'` and `rexec --shell 'npm ci'`; skipping it fails as a missing local path, not a remote one (remote-execution#4), and omitting `--locked` risks tool-version skew that shadows real gate results. Never set `UV_PROJECT_ENVIRONMENT` in `.rexec.toml` — see the comment there. Signing, tagging, and publication stay local.

## Non-Negotiables

- Dogfood the standards through the extracted candidate-wheel runtime described in [README.md](README.md#developing-this-repository): `uv run project-standards validate` must pass with that runtime first on `PYTHONPATH`.
- Run the closeout handoff validators via `make handoff-validate` / `make handoff-drift-check` in this repo (they wrap the same wheel-runtime `PYTHONPATH`); the bare skill commands fail here by design.
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

This repository's work belongs to the `L3DigitalNet` organization. Route every GitHub work-state action through the row below — this table is complete, so a delegated worker needs nothing else to route correctly. Load the repo-local `github-workflow` skill (`SKILL.md`, one read, ~69 lines) before triage, an organization-schema audit, or any judgment call the table leaves to you.

| Action | Command |
| --- | --- |
| Create a typed issue | `gh-workflow new --type T --title S [--field Name=Value]` |
| Set field values or the Issue Type | `gh-workflow set --issue N [--type T] [--field Name=Value]` |
| Close as Done or Dropped | `gh-workflow close --issue N --as done\|dropped` |
| Reopen | `gh-workflow reopen --issue N --workflow VALUE` |
| Check Ready preconditions | `gh-workflow check --issue N` |
| Read one issue's state and gaps | `gh-workflow receipt --issue N` |
| Operator summary / schema audit | `gh-workflow summary` / `gh-workflow audit` |
| Comment, retitle, create or merge a PR | raw `gh` — see `SKILL.md` |
| Wait for CI | `gh pr checks N --watch --fail-fast` or `gh run watch ID --exit-status` |

The binary is at `.agents/skills/github-workflow/bin/gh-workflow` (and the `.claude/` twin). Its refusals name the valid values, so invoke it rather than looking a vocabulary up first. These rules bind even when the skill was never loaded:

- You author acceptance criteria, set `Workflow`, and admit work to `Ready` yourself; an issue whose criteria you could not write is `Needs definition`.
- Set `Execution mode` by judgment, but `Unattended agent` is the operator's grant.
- Never create, rename, or retire an organization issue type, field, or value — that schema is human-applied.
- A nontrivial pull request links the issue that governs it.
- Keep terminal state synchronized: `Done` closes as completed, `Dropped` closes as not planned, and a reopened issue returns to a nonterminal `Workflow` value in the same action. Merging a PR does not make its issue `Done`.
- Durable follow-up work discovered while implementing becomes an issue before the session ends.

<!-- markdownlint-enable MD025 -->
<!-- END project-standards:github-workflow -->

<!-- prettier-ignore-end -->

<!-- prettier-ignore-start -->

<!-- BEGIN project-standards:markdown-frontmatter -->
<!-- markdownlint-disable MD025 -->
# Markdown Frontmatter

Managed Markdown in this repository carries YAML frontmatter under the Markdown Frontmatter Standard: the eleven required fields in canonical order, every scalar quoted, and an id of the form `{doc_type}-{6-char base36 token}-{slug}`.

Create a new managed document with `scripts/new-doc-id --scaffold --doc-type <type> <name>` from the repo-local skill at `.claude/skills/markdown-frontmatter/`. Read that skill's `SKILL.md` before hand-authoring or repairing a frontmatter block.

The gate is `project-standards validate`.

`AGENTS.md`, `CLAUDE.md`, and anything under `.agents/**`, `.claude/**`, or `.codex/**` never carry frontmatter.
<!-- markdownlint-enable MD025 -->
<!-- END project-standards:markdown-frontmatter -->

<!-- prettier-ignore-end -->
