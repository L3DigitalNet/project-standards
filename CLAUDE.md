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
- Develop on `testing`, never on `main`. Both branches are governed: `testing` is this repository's declared `integration_branch` and `main` is the default branch, so every commit on either carries one of the four `Workflow-Admission` classes — the managed GitHub Workflow block below and `.agents/skills/github-workflow/references/pr-standard.md` own the mechanics; what is repository-specific is which class each route uses. Ordinary work, including leg-worktree cherry-picks, lands on `testing` through a draft PR whose `merge --pr N` writes `PR #N`. Agent Handoff documents (`docs/handoff/**`, `docs/STATUS.md`, `docs/TODO.md`) are transient agent-side state and commit directly to `testing` with `Workflow-Admission: handoff`, never through a PR; a trivial prose repair commits directly with `Workflow-Admission: T0`. `main` is publication-only: at release time the validated `testing` is merged into it as a fast-forward, which creates no commit, and the only commit authored there is `release: prepare vX.Y.Z` — the `release` class, matched by the `release_subject_prefix` this repository declares, and admitted on the author's word rather than enforced. `scripts/release_prep.py` pins `RELEASE_BRANCH = "main"` and refuses any other branch, so that commit is authored on `main` with `PROJECT_STANDARDS_RELEASE_COMMIT=1`; the tracked hook `scripts/githooks/main-branch-guard` (installed into `.git/hooks` by `scripts/bootstrap-worktree.sh` or `make githooks`) exists to admit it, and a deliberate exception needs `PROJECT_STANDARDS_MAIN_COMMIT_OVERRIDE=1`. After tagging, `testing` is fast-forwarded from `main`. Enforcement starts at the `admission_floor` recorded in `.standards/config.toml`; audit with `gh-workflow admission --branch testing`.

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

Create a new managed document with `scripts/new-doc-id --scaffold --doc-type <type> <name>` from the repo-local skill at `.claude/skills/markdown-frontmatter/`. Read that skill's `SKILL.md` before hand-authoring or repairing a frontmatter block.

The gate is `project-standards validate`.

`AGENTS.md`, `CLAUDE.md`, and anything under `.agents/**`, `.claude/**`, or `.codex/**` never carry frontmatter.
<!-- markdownlint-enable MD025 -->
<!-- END project-standards:markdown-frontmatter -->

<!-- prettier-ignore-end -->
