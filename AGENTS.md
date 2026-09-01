# AGENTS.md

**Session state:** the startup hook injects `docs/handoff/state.md`; do not reread it. Check `docs/handoff/conventions.md` before adding persistent patterns.

**Conventions:** [`docs/handoff/conventions.md`](docs/handoff/conventions.md)

## Repo Purpose

This repo is the source of truth for reusable project standards. Catalog 5 has nine consumer packages plus reference-only **Python Coding** and internal **Standard Bundle Authoring 2.7**. `.standards/config.toml` selects immutable packages; reconciliation composes them under one lock. See [README.md](README.md).

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
- **Bootstrap a fresh checkout or worktree with one command.** `scripts/bootstrap-worktree.sh` runs the whole sequence the gate requires — `uv sync`, `npm ci`, the projection check, the wheel build, extraction, its staleness stamp, and `make go-tools` — in about 10 seconds. Run it first in any new execute-plan worktree, and again after any change under `src/**` or to a payload under `standards/**`; do not reconstruct the sequence from a preflight failure message.
- **Enumerate a new family's declaration sites before authoring** — `docs/handoff/conventions.md` #19. Run `uv run python scripts/family_preflight.py <family-id>` first: nine hand-maintained collections declare a family beyond its own payload tree, and discovering them one gate failure at a time cost roughly 2–3 hours of the last family's adoption. The check predicts those gates and replaces none of them.
- **Match verification to the surface you changed** — `docs/handoff/conventions.md` #18. Payload, catalog, digest, and manifest edits are fully covered by the five `standards …` validators plus the Markdown gate, in seconds. Reserve the full gate for engine, control-plane, and test changes.
- **Keep the toolchain green** before committing validator/test changes. `scripts/verify.sh` is the gate: it runs statics, the ordinary suite under coverage, and the compatibility matrix concurrently, then the performance lane alone, then `coverage combine` + `coverage report`. Build and extract the candidate wheel and run `npm ci` first; the script requires both, and refuses a stale runtime by name. **Trimmed verification:** intermediate legs of a train run the fast gate. The full serial battery (`scripts/verify.sh --full`) runs only after the last content change and at release prep, where it doubles as the legacy cross-check against the coverage baseline. Hosted `Check` remains the every-push backstop.
- **Use rexec v0.2 accurately.** CPU-intensive work compatible with a synchronized tree uses `rexec -- <command>`; explicit rexec invocation is remote-only, so run directly when local execution is intended. The sole configuration is the schema-1 root `.rexec.toml`; after a client/configuration change, run `rexec config show`, `rexec doctor`, and `rexec setup --check`. `.git` is never synchronized, so Git-history, branch, index, and `git ls-files` workloads stay local. See `docs/handoff/conventions.md` #22.
- **Keep package contracts green.** Under `uv run project-standards standards`, run `validate-packages --root . --json`, `validate-graph --root . --require-all-manifests --json`, `generate-package-schemas --root . --check`, and `sync-payload-projection --root . --check`.
- **The schema is versioned** — see `docs/handoff/conventions.md` #4.
- **Develop on `testing`, never on `main`.** `testing` is this repository's declared `integration_branch`, so it is governed and every commit on it — including leg-worktree cherry-picks — carries one of the four `Workflow-Admission` classes the GitHub Workflow block below defines. Ordinary work goes through a draft PR and `merge --pr N`; Agent Handoff documents (`docs/handoff/**`, `docs/STATUS.md`, `docs/TODO.md`) commit directly under the `handoff` class, and a trivial prose repair under `T0`. See `CLAUDE.md`'s Non-Negotiables for the `main` fast-forward and the release commit's own class.
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
git ls-files -s -z -- ':(glob)**/*.md' ':(glob)**/*.json' ':(glob)**/*.jsonc' ':(glob)**/*.yml' ':(glob)**/*.yaml' | sed -zn '/^120000 /!s/^[^\t]*\t//p' | xargs -0 -r npx prettier --check --
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

This repository's work belongs to the `L3DigitalNet` organization. Route every GitHub work-state action through the table below; every row is a `gh-workflow` subcommand unless it says raw `gh`. Load the `github-workflow` skill for triage, a schema audit, T0 or relationship judgment, or rare recovery.

| Action | Command |
| --- | --- |
| Create a typed issue | `new --type T --title S [--field Name=Value]` |
| Set fields or Issue Type | `set --issue N [--type T] [--field Name=Value]` |
| Close or reopen an issue | `close --issue N --as done\|dropped` / `reopen --issue N --workflow V` |
| Check or read an issue or PR | `check`/`receipt --issue N` or `--pr N`; `check --pr N --through PHASE` |
| Summary / schema audit | `summary` / `audit` |
| Open a draft PR | raw `gh pr create --draft --body-file PATH` |
| Ready, then merge | `ready --pr N` / `merge --pr N [--method M] [--auto]` |
| Close an open Final unmerged | `close --pr N --as OUTCOME --reason S` |
| Classify admission | `admission --branch B [--offline]` |

All ten accept `--output human|json`; the binary is at `.agents/skills/github-workflow/bin/gh-workflow` and its `.claude/` twin, and its refusals name valid values. These rules bind even when the skill was never loaded:

- An operator instruction is sufficient authority for the action it names. You author acceptance criteria and admit work to `Ready`; open state never implies it.
- Every commit on a governed branch carries one `Workflow-Admission` trailer: `T0` (trivial prose repair, no protected surface), `PR #N` (written by `merge`), `handoff` (touches only `docs/handoff/**`, `docs/STATUS.md`, `docs/TODO.md`), or `release`. A commit mixing handoff and other paths is not handoff: like all other work it starts as a draft PR declaring `Final: #N`, `Supporting: #N`, or `Standalone` under `## Governing work`.
- Keep terminal state paired: `Done` closes as completed, `Dropped` as not planned; reopen returns a nonterminal `Workflow` value.
- Never create shadow state labels, mutate organization schema, or bypass live enforcement.
- A related finding you can address this session needs no issue: fix it here when this repository owns it, file it against the owning upstream repository, ask the operator only when it needs its own session.

<!-- markdownlint-enable MD025 -->
<!-- END project-standards:github-workflow -->

<!-- prettier-ignore-end -->

<!-- prettier-ignore-start -->

<!-- BEGIN project-standards:markdown-frontmatter -->
<!-- markdownlint-disable MD025 -->
# Markdown Frontmatter

Managed Markdown in this repository carries YAML frontmatter under the Markdown Frontmatter Standard: the eleven required fields in canonical order, every scalar quoted, and an id of the form `{doc_type}-{6-char base36 token}-{slug}`.

Create a new managed document with `scripts/new-doc-id --scaffold --doc-type <type> <name>` from the repo-local skill at `.agents/skills/markdown-frontmatter/`. Read that skill's `SKILL.md` before hand-authoring or repairing a frontmatter block.

The gate is `project-standards validate`.

`AGENTS.md`, `CLAUDE.md`, and anything under `.agents/**`, `.claude/**`, or `.codex/**` never carry frontmatter.
<!-- markdownlint-enable MD025 -->
<!-- END project-standards:markdown-frontmatter -->

<!-- prettier-ignore-end -->
