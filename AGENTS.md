# AGENTS.md

**Session state:** the startup hook injects `docs/handoff/state.md`; do not reread it. Check `docs/handoff/conventions.md` before adding persistent patterns.

**Conventions:** [`docs/handoff/conventions.md`](docs/handoff/conventions.md)

## Repo Purpose

This repo is the source of truth for reusable project standards. Catalog 5 has eight consumer packages plus reference-only **Python Coding** and internal **Standard Bundle Authoring 2.6**. `.standards/config.toml` selects immutable packages; reconciliation composes them under one lock. See [README.md](README.md).

## Structure

| Path | Purpose |
| --- | --- |
| `standards/<name>/` | bundles: standard, manifest, adoption guide, templates, examples |
| `meta/` | repo policy, including the release contract |
| `src/project_standards/`, `tests/` | Python implementation and tests |
| `.github/workflows/` | reusable consumer workflows |
| `docs/specs/` | maintained Project Specification documents; `archive/` holds superseded specs and historical designs |
| `docs/handoff/` | durable Agent Handoff project knowledge and session state |
| `docs/plans/` | active implementation plans (completed plans are deleted) |
| `docs/research/` | research corpus and reference packs, indexed by `index.md` |

## Working Rules

- **Sub-agents.** Individual agents and headless Codex are pre-authorized via `cross-agent` skill or ad hoc. Never use Fable unless explicitly requested by the user; use Haiku only for mechanical work, Sonnet+ for substantive work, and Opus for adversarial review. Set the model and an appropriate effort level.
- **Self-containment.** This conventions source does not import global agent conventions. It dogfoods repo-local Agent Handoff; do not add workstation ownership.
- **Dogfood.** After extracting the candidate wheel and putting it first on `PYTHONPATH` as shown in [README.md](README.md#developing-this-repository), validate managed Markdown with `uv run project-standards validate`. ADR 0015 excludes `standards/**` so packages do not ship repo metadata.
- **Markdown Tooling.** Prettier and markdownlint remain the formatting and structure authorities.
- **`docs/superpowers/` is a forbidden path**; never recreate it. Specs go to `docs/specs/`, plans to `docs/plans/`, research to `docs/research/`, reviews to `docs/reviews/`.
- **Keep the toolchain green** before committing validator/test changes. `scripts/verify.sh` is the gate: it runs statics, the ordinary suite under coverage, and the compatibility matrix concurrently, then the performance lane alone, then `coverage combine` + `coverage report`. Build and extract the candidate wheel and run `npm ci` first; the script requires both. **Trimmed verification:** intermediate legs of a train run the fast gate. The full serial battery (`scripts/verify.sh --full`) runs only after the last content change and at release prep, where it doubles as the legacy cross-check against the coverage baseline. Hosted `Check` remains the every-push backstop.
- **Keep package contracts green.** Under `uv run project-standards standards`, run `validate-packages --root . --json`, `validate-graph --root . --require-all-manifests --json`, `generate-package-schemas --root . --check`, and `sync-payload-projection --root . --check`.
- **The schema is versioned** — see `docs/handoff/conventions.md` #4.
- `README.md` is the human-facing landing page, excluded from frontmatter validation.

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
