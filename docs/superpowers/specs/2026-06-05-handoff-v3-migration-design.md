# Design: Migrate `project-standards` to handoff-system-v3

**Date:** 2026-06-05 **Status:** approved (brainstorming complete; awaiting implementation plan) **Author:** session 2026-06-05

## Problem

`project-standards` deliberately opted **out** of the workstation v3 handoff system. Three places asserted this self-containment:

- `AGENTS.md`: _"MANDATORY: stay self-contained. Do not import external/global agent conventions into this repo — in particular the workstation v3 handoff system."_
- `working/HANDOFF.md` header: _"Deliberately not the workstation v3 handoff system."_
- `working/README.md`: described the self-contained `working/` convention.

The repo instead used a self-contained handoff: a single `working/HANDOFF.md` plus `working/archive/<version>/` and `working/README.md`. No `docs/` directory existed; there was no `docs/handoff/` layout, no SessionStart hook.

The user has decided to reverse this and adopt v3. This is a **governance change** to a conventions-source repo, not a mechanical file move, so it is specced and planned before execution.

## Decisions (locked during brainstorming)

1. **Scope = Full v3** — both the `docs/handoff/` layout **and** the Claude SessionStart hook (a tracked byte-identical copy of the canonical agent-configs hook).
2. **`working/` is deleted entirely** — every piece relocates to its v3 home by lifetime.
3. **`AGENTS.md` self-containment rule = carve-out** — keep the broader "this repo is a conventions source; do not import _other_ external/global conventions" principle, but rewrite the handoff paragraph so v3 is the single sanctioned exception, adopted 2026-06-05.
4. **`.project-standards.yml`** gains an explicit `docs/handoff/**` exclude (with comment) — instructive, since this file is the canonical downstream example; it documents that handoff state is _not_ a managed document.
5. **No `CHANGELOG.md` entry** — the changelog tracks the standards _product_ that consumers pin to; an internal handoff migration is not consumer-facing.
6. **The 46 KiB DEC-1…9 trail moves verbatim** (`git mv`) into `docs/superpowers/specs/`, preserving history — not summarized.

## The v3 contract this migration must satisfy

Verified against `~/projects/agent-configs/scripts/handoff/validate-layout.sh` and the `template-repo-v3-handoff` reference repo.

- **Layout:** `docs/handoff/{state,deployed,architecture,credentials,conventions,specs-plans}.md` plus `docs/handoff/sessions/` and `docs/handoff/bugs/` directories. Each member in exactly one parent (no mixed `docs/` + `docs/handoff/`).
- **`state.md` ≤ 2048 bytes** (hook truncates beyond; validator records over-cap).
- **Claude block** (triggered by `.claude/` existing):
  - `CLAUDE.md` present, ≤ 2048 bytes.
  - `.claude/settings.json`: valid JSON, contains a `SessionStart` hook, matcher exactly `startup|resume|clear|compact`, command anchored with `${CLAUDE_PROJECT_DIR}`.
  - `.claude/hooks/session_start.py`: present, references `hookSpecificOutput`/`additionalContext`, and **byte-identical** to the canonical source `agent-configs/global/claude/hooks/session_start.py` (sha256 `a846751c9c750263c5bd16aa58688256a4c3b1e5d64151834da5e629d95443a5`, 6147 bytes). The validator runs `cmp -s` and reports drift on any mismatch.
- **Codex block** (triggered by `AGENTS.md` existing): `AGENTS.md` must contain the three exact marker substrings `Session state:`, `Full conventions reference:`, and `Detailed review workflows:`.

## Content relocation map

| Source (deleted after move) | Destination | Transform |
| --- | --- | --- |
| `working/HANDOFF.md` → _Current state_ + gate-green readout | `docs/handoff/state.md` | Compress to ≤ 2 KiB live slice |
| `working/HANDOFF.md` → 1.3.0 history / DEC summary | `docs/handoff/sessions/2026-06.md` | Two session rows (06-04 planning, 06-05 impl) with commit refs |
| `working/HANDOFF.md` → _Locked decisions_, backlog (pre-commit deferred; 2.0.0 link enforcement) | `docs/handoff/architecture.md` | Component graph + standing backlog |
| `working/linting-formatting/linting-formatting-stack.md` (46 KiB DEC-1…9 trail) | `docs/superpowers/specs/2026-06-04-linting-formatting-stack.md` | `git mv` verbatim; row in `specs-plans.md` |
| `working/archive/v1.1.0/` (plans + schema proposals) | `docs/superpowers/plans/v1.1.0/` | `git mv` verbatim; row in `specs-plans.md` |
| `working/README.md` | — | Delete (obsoleted by v3) |
| Published tags v1.0.x–v1.2.0 + pending 1.3.0 | `docs/handoff/deployed.md` | "Deployed" = published git refs consumers pin to |
| `AGENTS.md` _General_ rules (dogfood, no-frontmatter-on-agent-files, toolchain-green, schema-is-a-contract) | `docs/handoff/conventions.md` | 4 numbered entries (durable patterns, not live state) |
| (repo has no secrets) | `docs/handoff/credentials.md` | "No secret values stored" note |

## Index-file rewrites

- **`CLAUDE.md`** — replace the `@AGENTS.md` stub with the v3 slim Claude index (purpose + doc-layout pointers + non-negotiables), ≤ 2 KiB. Drops the `@AGENTS.md` import; CLAUDE.md becomes a standalone Claude index. Live state is injected by the hook, so it instructs the agent **not** to read `state.md` directly.
- **`AGENTS.md`** — reshape to the v3 Codex index: the three marker lines at top, then `## Repo Purpose`, `## Structure`, `## Working Rules`. The self-containment paragraph becomes the carve-out (Decision 3). Stays ≤ 4 KiB. The detailed working rules now live in `conventions.md`; `AGENTS.md` keeps a short pointer.
- **`.claude/`** — add tracked `settings.json` (hook registration, copied from the canonical template) and `hooks/session_start.py` (canonical copy). The existing `.claude/settings.local.json` (MCP search permissions) is left untouched.

## New `docs/handoff/` file contents (authored, not moved)

- **`state.md`** — live slice: "1.3.0 feature-complete on `testing` (DEC-1…9), unreleased; awaiting release ritual." Gate-green readout (pytest 105, ruff clean, pyright 0, validate-frontmatter ✓9, markdownlint 0, prettier clean, verified 2026-06-05). Active incidents: none. Session instructions.
- **`deployed.md`** — table of published tags on `main` (v1.0.x…v1.2.0), the moving `v1` tag tracking newest, and 1.3.0 pending on `testing`.
- **`architecture.md`** — component graph (`standards/`, `schemas/`, `templates/`, `examples/`, `tools/`+`tests/`, `.github/workflows/`) and standing backlog (pre-commit hooks deferred; 2.0.0 repo-root-relative link enforcement, breaking).
- **`credentials.md`** — "No secret values stored in this repo" note.
- **`conventions.md`** — Quick Reference + 4 numbered entries ported from `AGENTS.md`: (1) Dogfood the standards, (2) Never add frontmatter to agent-instruction files, (3) Keep the toolchain green, (4) The schema is a versioned contract.
- **`specs-plans.md`** — rows for this migration design, the moved DEC trail spec, and the moved v1.1.0 plans.
- **`bugs/INDEX.md`** + **`bugs/_regen_index.py`** — canonical copies; index seeded empty ("No bugs recorded.").
- **`sessions/2026-06.md`** — the two session rows.

## Validation (acceptance criteria)

1. `~/projects/agent-configs/scripts/handoff/validate-layout.sh ~/projects/project-standards` → passes.
2. `uv run validate-frontmatter --config .project-standards.yml` → still ✓ (no new managed docs introduced; `docs/handoff/**` excluded).
3. `uv run pytest`, `uv run ruff check .`, `uv run pyright` → unchanged green (no code touched).
4. `markdownlint-cli2` + `prettier --check .` → clean on the new Markdown.
5. `python3 docs/handoff/bugs/_regen_index.py && git diff --exit-code docs/handoff/bugs/INDEX.md` → no diff.
6. No tracked file references `working/` after the move (`git grep working/`).
7. `working/` directory no longer exists.

## Non-goals

- Releasing 1.3.0 (explicitly out of scope; remains on `testing`).
- Any change to the standards product, schema, validator code, or tests.
- Centralizing repo-level `CLAUDE.md`/`AGENTS.md` anywhere outside this repo.
