# Handoff-v3 Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate `project-standards` from its self-contained `working/HANDOFF.md` handoff onto the workstation handoff-system-v3 layout (`docs/handoff/` + Claude SessionStart hook), passing the v3 layout validator and the repo's own frontmatter/lint/format gates.

**Architecture:** Pure docs/config migration — no product code, schema, or tests change. Live state fans out by lifetime from one 12 KiB `HANDOFF.md` into `docs/handoff/{state,deployed,architecture,credentials,conventions,specs-plans}.md` + `sessions/` + `bugs/`. Two large planning docs move verbatim via `git mv` into `docs/superpowers/{specs,plans}/`. `CLAUDE.md`/`AGENTS.md` become slim v3 index files; the canonical SessionStart hook is installed byte-identical.

**Tech Stack:** Markdown, JSON (`.claude/settings.json`), Python (copied hook), bash (validators). Gates: `validate-layout.sh`, `uv run validate-frontmatter`, `uv run pytest/ruff/pyright`, `markdownlint-cli2`, `prettier --check`.

**Spec:** `docs/superpowers/specs/2026-06-05-handoff-v3-migration-design.md`

---

## File structure

| File | Responsibility |
| --- | --- |
| `docs/handoff/state.md` | Live state (≤2048 B), auto-injected by hook |
| `docs/handoff/deployed.md` | Published tags consumers pin to |
| `docs/handoff/architecture.md` | Component graph + standing backlog |
| `docs/handoff/credentials.md` | Credential references (none today) |
| `docs/handoff/conventions.md` | Durable pattern library (4 entries) |
| `docs/handoff/specs-plans.md` | Spec/plan pointer table |
| `docs/handoff/sessions/2026-06.md` | Monthly session log |
| `docs/handoff/bugs/INDEX.md` + `_regen_index.py` | Bug KB index + regenerator |
| `.claude/settings.json` | SessionStart hook registration (tracked) |
| `.claude/hooks/session_start.py` | Canonical hook copy (byte-identical) |
| `CLAUDE.md` | Slim v3 Claude index (rewrite) |
| `AGENTS.md` | Slim v3 Codex index + self-containment carve-out (rewrite) |
| `.project-standards.yml` | Add `docs/handoff/**` exclude |

Sources removed: `working/HANDOFF.md`, `working/README.md`, `working/linting-formatting/` (moved), `working/archive/` (moved).

---

### Task 1: Author the `docs/handoff/` core files

**Files:**

- Create: `docs/handoff/state.md`, `deployed.md`, `architecture.md`, `credentials.md`, `conventions.md`, `specs-plans.md`, `sessions/2026-06.md`

- [ ] **Step 1: Write `docs/handoff/state.md`**

```markdown
# State

**Last updated:** 2026-06-05

## State at a glance

- `1.3.0` is feature-complete on `testing` (DEC-1…9) but **unreleased** — the release ritual was deliberately out of scope. `main` holds releases; the moving `v1` tag tracks the newest. Exact delta: `git log main..testing`.
- Gate green (verified 2026-06-05): pytest **105**, ruff clean, pyright 0, validate-frontmatter ✓ 9, markdownlint 0, prettier `--check .` clean.
- Repo migrated to handoff-system-v3 on 2026-06-05 (this layout).

## Active incidents

- None.

## Session instructions

1. Live state is auto-injected by the SessionStart hook; check `git log` + working tree before acting. Do not re-apply committed changes.
2. Keep this file ≤2048 bytes — route long-lived content to its split file (history → `sessions/`, backlog → `architecture.md`, patterns → `conventions.md`).
3. Update **Last updated** and the bullets whenever state changes.
4. Next obvious work: run the `1.3.0` release ritual (cut tag, move `v1`, fast-forward `main`). See `deployed.md`.
```

- [ ] **Step 2: Write `docs/handoff/deployed.md`**

```markdown
# Deployed

**Last updated:** 2026-06-05

This repo is consumed as a versioned standard: downstream repos pin a `standards-ref` to a git tag and call the reusable workflow under `.github/workflows/`. "Deployed" here means published git refs on `main`.

| Ref | What it is | Status |
| --- | --- | --- |
| `v1.0.0`–`v1.0.2` | Initial standards + validator + reusable workflow | published on `main` |
| `v1.1.0` | optional `consumer` field; `schema_version` accepts `1.1` | published on `main` |
| `v1.2.0` | `standards/adoption.md`; pinning hardened; validator crash-safety | published on `main` |
| `v1` (moving) | tracks the newest release — currently `v1.2.0` (`2abea67`) | published on `main` |
| `1.3.0` | lint/format stack + MADR-4 ADR conventions + ADR section check | **pending on `testing`, unreleased** |
```

- [ ] **Step 3: Write `docs/handoff/architecture.md`**

````markdown
# Architecture

**Last updated:** 2026-06-05

## Components

```text
project-standards
├── standards/          -> human-readable governing docs (frontmatter, ADR, versioning, adoption)
├── schemas/            -> machine-readable JSON Schemas (markdown-frontmatter.schema.json)
├── templates/          -> copy-paste scaffolds (intentional placeholders; not validated)
├── examples/           -> validated worked examples (managed; carry frontmatter)
├── tools/ + tests/     -> the Python validator (validate_frontmatter.py) and its pytest suite
├── .github/workflows/  -> reusable workflows consumers call (validate, lint-markdown, format)
└── docs/handoff/       -> agent session state (this v3 layout)
```

## Relationships

- Consumers add `.project-standards.yml` + call the reusable workflow; they do not vendor copies. The schema is the contract — changing it is a versioned change.
- The validator (`tools/`) reads `.project-standards.yml`, resolves the bundled schema in `schemas/`, and validates the configured include globs.
- This repo dogfoods its own standards: `standards/`, `examples/`, `CHANGELOG.md` carry canonical frontmatter and must validate.

## Standing backlog

- **Pre-commit hooks** — deferred (decided during the 1.3.0 line).
- **`2.0.0` repo-root-relative link enforcement** — breaking; future major.
````

- [ ] **Step 4: Write `docs/handoff/credentials.md`**

```markdown
# Credentials

**Last updated:** 2026-06-05

No secret values are stored in this repo, and it needs none — it is a standards library validated by CI with no runtime credentials. Record **references only** (env var names, secret names, OpenBao `secret/<path>`) if that ever changes.

_No credentials referenced._
```

- [ ] **Step 5: Write `docs/handoff/conventions.md`**

````markdown
# Conventions

LLM-targeted pattern library for this repo. Check this file before adding a persistent pattern; add new patterns here before session end.

## Quick Reference

| # | Title | Applies when |
| --- | --- | --- |
| 1 | Dogfood the standards | Editing managed Markdown (`standards/`, `examples/`, `CHANGELOG.md`) |
| 2 | Never frontmatter agent-instruction files | Touching `CLAUDE.md`, `AGENTS.md`, `.claude/**` |
| 3 | Keep the toolchain green | Changing the validator or its tests |
| 4 | The schema is a versioned contract | Changing the schema or controlled vocabularies |

## 1. Dogfood the standards

**Applies when:** editing managed Markdown here — `standards/`, `examples/`, `CHANGELOG.md`.

**Rule:** managed Markdown carries canonical frontmatter and must validate; run the validator before finishing.

**Code:**

```bash
uv run validate-frontmatter --config .project-standards.yml
```

**Why:** this repo is the source of the standard; if its own managed docs don't validate, the standard isn't credible.

**Sources:** pre-v3 `AGENTS.md` "General" section.

**Related:** 2, 4.

## 2. Never add frontmatter to agent-instruction files

**Applies when:** touching `CLAUDE.md`, `AGENTS.md`, or anything under `.claude/`, `.agents/`, `.codex/`.

**Rule:** these are harness configuration, not managed documents — never add frontmatter. They are excluded from validation in `.project-standards.yml`.

**Why:** frontmatter on a harness file is meaningless and would fail the schema's date/id patterns.

**Sources:** pre-v3 `AGENTS.md`; `.project-standards.yml`.

**Related:** 1.

## 3. Keep the toolchain green

**Applies when:** changing the validator (`tools/`) or its tests.

**Rule:** run all three before committing — every one must pass.

**Code:**

```bash
uv run pytest && uv run ruff check . && uv run pyright
```

**Why:** `main` must stay releasable; consumers pin to tags.

**Sources:** pre-v3 `AGENTS.md`.

**Related:** 4.

## 4. The schema is a versioned contract

**Applies when:** changing `schemas/markdown-frontmatter.schema.json` or the controlled vocabularies.

**Rule:** update `standards/`, templates, examples, tests, and `CHANGELOG.md` together, then cut a new tag (minor = additive, major = breaking).

**Why:** consumers pin to tags; a silent schema change breaks them.

**Sources:** pre-v3 `AGENTS.md`.

**Related:** 1, 3.
````

- [ ] **Step 6: Write `docs/handoff/specs-plans.md`**

```markdown
# Specs And Plans

**Last updated:** 2026-06-05

| Item | Path | Status |
| --- | --- | --- |
| Handoff v3 migration design | `docs/superpowers/specs/2026-06-05-handoff-v3-migration-design.md` | approved |
| Handoff v3 migration plan | `docs/superpowers/plans/2026-06-05-handoff-v3-migration.md` | in progress |
| Linting/formatting stack (DEC-1…9 trail) | `docs/superpowers/specs/2026-06-04-linting-formatting-stack.md` | implemented (1.3.0) |
| v1.1.0 planning docs | `docs/superpowers/plans/v1.1.0/` | shipped |

## Storage

- Specs and design artifacts: `docs/superpowers/specs/`
- Implementation plans: `docs/superpowers/plans/`
```

- [ ] **Step 7: Write `docs/handoff/sessions/2026-06.md`**

```markdown
# Sessions — 2026-06

| Date | Headline | Commits | Bugs |
| --- | --- | --- | --- |
| 2026-06-04 | Locked DEC-1…8 (lint/format stack + MADR-4) — planning only | `d06cbab` | — |
| 2026-06-05 | Implemented 1.3.0 lint/format stack; DEC-6→6b, added DEC-9; gate green | `f0ef89a`…`414cfae` | — |
| 2026-06-05 | Migrated repo to handoff-system-v3 (`working/` → `docs/handoff/`) | _this session_ | — |
```

- [ ] **Step 8: Verify `state.md` is within the byte cap**

Run: `wc -c docs/handoff/state.md` Expected: a number **≤ 2048**.

- [ ] **Step 9: Commit**

```bash
git add docs/handoff/state.md docs/handoff/deployed.md docs/handoff/architecture.md \
  docs/handoff/credentials.md docs/handoff/conventions.md docs/handoff/specs-plans.md \
  docs/handoff/sessions/2026-06.md
git commit -m "Author docs/handoff/ core files (state, deployed, architecture, conventions, etc.)"
```

---

### Task 2: Install the bug KB (`docs/handoff/bugs/`)

**Files:**

- Create: `docs/handoff/bugs/_regen_index.py` (canonical copy), `docs/handoff/bugs/INDEX.md`

- [ ] **Step 1: Copy the canonical regenerator (verbatim, no formatter)**

```bash
mkdir -p docs/handoff/bugs
cp ~/projects/template-repo-v3-handoff/docs/handoff/bugs/_regen_index.py \
   docs/handoff/bugs/_regen_index.py
```

- [ ] **Step 2: Generate the empty index from the regenerator**

Run: `python3 docs/handoff/bugs/_regen_index.py` Expected: creates `docs/handoff/bugs/INDEX.md` containing `_No bugs recorded._`

- [ ] **Step 3: Verify the index is reproducible**

Run: `python3 docs/handoff/bugs/_regen_index.py && git add docs/handoff/bugs/INDEX.md && git diff --cached --quiet docs/handoff/bugs/INDEX.md && echo CLEAN` Expected: prints `CLEAN`

- [ ] **Step 4: Commit**

```bash
git add docs/handoff/bugs/_regen_index.py docs/handoff/bugs/INDEX.md
git commit -m "Add docs/handoff/bugs/ KB (empty index + regenerator)"
```

---

### Task 3: Relocate the two large planning docs, then delete `working/`

**Files:**

- Move: `working/linting-formatting/linting-formatting-stack.md` → `docs/superpowers/specs/2026-06-04-linting-formatting-stack.md`
- Move: `working/archive/v1.1.0/` → `docs/superpowers/plans/v1.1.0/`
- Delete: `working/HANDOFF.md`, `working/README.md`

- [ ] **Step 1: Move the DEC-1…9 decision trail into specs (preserves history)**

```bash
mkdir -p docs/superpowers/specs docs/superpowers/plans
git mv working/linting-formatting/linting-formatting-stack.md \
       docs/superpowers/specs/2026-06-04-linting-formatting-stack.md
```

- [ ] **Step 2: Move the v1.1.0 archive into plans**

```bash
git mv working/archive/v1.1.0 docs/superpowers/plans/v1.1.0
```

- [ ] **Step 3: Delete the now-obsolete handoff + working README**

```bash
git rm working/HANDOFF.md working/README.md
```

- [ ] **Step 4: Remove any empty leftover directories**

```bash
rmdir working/linting-formatting working/archive working 2>/dev/null || true
test ! -e working && echo "working/ gone"
```

Expected: prints `working/ gone`

- [ ] **Step 5: Verify the moves landed and `working/` is gone**

Run:

```bash
test -f docs/superpowers/specs/2026-06-04-linting-formatting-stack.md && \
test -d docs/superpowers/plans/v1.1.0 && test ! -e working && echo "MOVES OK"
```

Expected: prints `MOVES OK`. (The remaining `working/` reference in `AGENTS.md` is rewritten in Task 6; the repo-wide dangling-ref check runs in Task 8 Step 7.)

- [ ] **Step 6: Commit**

```bash
git add -A docs/superpowers/
git commit -m "Relocate working/ planning docs to docs/superpowers/; delete working/"
```

---

### Task 4: Install the Claude SessionStart hook + settings

**Files:**

- Create: `.claude/hooks/session_start.py` (byte-identical canonical copy)
- Create: `.claude/settings.json`

- [ ] **Step 1: Copy the canonical hook (cp, not Write — preserve the byte hash)**

```bash
mkdir -p .claude/hooks
cp ~/projects/agent-configs/global/claude/hooks/session_start.py \
   .claude/hooks/session_start.py
```

- [ ] **Step 2: Verify the hook is byte-identical to canonical**

Run:

```bash
cmp -s ~/projects/agent-configs/global/claude/hooks/session_start.py \
  .claude/hooks/session_start.py && echo "HASH MATCH" || echo "DRIFT"
```

Expected: prints `HASH MATCH`

- [ ] **Step 3: Verify the hook emits valid JSON**

Run: `python3 .claude/hooks/session_start.py </dev/null | python3 -m json.tool >/dev/null && echo "VALID JSON"` Expected: prints `VALID JSON`

- [ ] **Step 4: Write `.claude/settings.json`**

```json
{
	"hooks": {
		"SessionStart": [
			{
				"matcher": "startup|resume|clear|compact",
				"hooks": [
					{
						"type": "command",
						"command": "python3 \"${CLAUDE_PROJECT_DIR}/.claude/hooks/session_start.py\"",
						"timeout": 30
					}
				]
			}
		]
	}
}
```

- [ ] **Step 5: Verify settings.json is valid JSON and has the required markers**

Run:

```bash
python3 -m json.tool <.claude/settings.json >/dev/null && \
grep -F '"SessionStart"' .claude/settings.json && \
grep -F '"matcher": "startup|resume|clear|compact"' .claude/settings.json && \
grep -F 'CLAUDE_PROJECT_DIR' .claude/settings.json && echo "SETTINGS OK"
```

Expected: prints the matched lines then `SETTINGS OK`

- [ ] **Step 6: Commit**

```bash
git add .claude/hooks/session_start.py .claude/settings.json
git commit -m "Install Claude SessionStart hook + settings.json (handoff-v3)"
```

---

### Task 5: Rewrite `CLAUDE.md` as the slim v3 Claude index

**Files:**

- Modify (full replace): `CLAUDE.md`

- [ ] **Step 1: Replace `CLAUDE.md` with the v3 index**

```markdown
# CLAUDE.md

**Session startup:** live state is injected by the SessionStart hook (`.claude/hooks/session_start.py`); do not read `docs/handoff/state.md` directly.

**Purpose:** single source of truth for reusable documentation standards — defines the Markdown Frontmatter, ADR, and versioning standards and enforces them with a Python validator that downstream repos consume via a reusable CI workflow.

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
- Keep the toolchain green: `uv run pytest && uv run ruff check . && uv run pyright`.
- The schema is a versioned contract — see `docs/handoff/conventions.md`.
```

- [ ] **Step 2: Verify the byte cap (≤2048)**

Run: `wc -c CLAUDE.md` Expected: a number **≤ 2048**.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "Rewrite CLAUDE.md as slim handoff-v3 Claude index"
```

---

### Task 6: Rewrite `AGENTS.md` as the slim v3 Codex index with the self-containment carve-out

**Files:**

- Modify (full replace): `AGENTS.md`

- [ ] **Step 1: Replace `AGENTS.md`**

```markdown
# AGENTS.md

**Session state:** read `docs/handoff/state.md`, then this file, then `docs/handoff/conventions.md`.

**Full conventions reference:** [`docs/handoff/conventions.md`](docs/handoff/conventions.md) — LLM-targeted pattern library. Check it before adding persistent patterns.

**Detailed review workflows:** not configured for this repo.

## Repo Purpose

This repository is the **single source of truth** for reusable documentation standards shared across projects. It _defines_ standards (Markdown Frontmatter, ADR, versioning) and _enforces_ them with a Python validator; other repositories _consume_ them via a small `.project-standards.yml` plus a reusable CI workflow, rather than vendoring copies. See [README.md](README.md) for the full surface.

## Structure

| Path                       | Purpose                                              |
| -------------------------- | ---------------------------------------------------- |
| `standards/`               | human-readable governing documents                   |
| `schemas/`                 | machine-readable JSON Schemas                        |
| `templates/` + `examples/` | scaffolds and validated worked examples              |
| `tools/` + `tests/`        | the Python validator and its tests                   |
| `.github/workflows/`       | the reusable workflows consumers call                |
| `docs/handoff/`            | agent session state (handoff-system-v3)              |
| `docs/superpowers/`        | specs (`specs/`) and implementation plans (`plans/`) |

## Working Rules

- **Conventions-source self-containment.** This repo defines conventions, so it does **not** import other external/global agent conventions. The single sanctioned exception is the workstation **v3 handoff system**, adopted 2026-06-05 (`docs/handoff/` + the SessionStart hook). Do not layer further global/workstation conventions on top of it.
- **Dogfood the standards.** Managed Markdown (`standards/`, `examples/`, `CHANGELOG.md`) must validate: `uv run validate-frontmatter --config .project-standards.yml`.
- **Never add frontmatter to agent-instruction files** — `CLAUDE.md`, `AGENTS.md`, `.claude/**`, `.agents/**`, `.codex/**`.
- **Keep the toolchain green** before committing validator/test changes: `uv run pytest`, `uv run ruff check .`, `uv run pyright`.
- **The schema is a versioned contract** — see `docs/handoff/conventions.md` #4.
- `README.md` is the human-facing landing page, excluded from frontmatter validation.
```

- [ ] **Step 2: Verify the three validator marker lines + byte cap (≤4096)**

Run:

```bash
grep -F 'Session state:' AGENTS.md && \
grep -F 'Full conventions reference:' AGENTS.md && \
grep -F 'Detailed review workflows:' AGENTS.md && \
wc -c AGENTS.md
```

Expected: the three lines print, and `wc -c` is **≤ 4096**.

- [ ] **Step 3: Commit**

```bash
git add AGENTS.md
git commit -m "Rewrite AGENTS.md as slim handoff-v3 Codex index; v3 carve-out of self-containment rule"
```

---

### Task 7: Exclude `docs/handoff/**` from frontmatter validation

**Files:**

- Modify: `.project-standards.yml` (the `markdown.frontmatter.exclude` list)

- [ ] **Step 1: Add the exclude entry**

In `.project-standards.yml`, under `markdown.frontmatter.exclude:`, after the `.codex/**` line, add:

```yaml
# Agent session state (handoff-system-v3) is harness state, not managed docs.
- 'docs/handoff/**'
```

- [ ] **Step 2: Verify it parses and the validator still passes**

Run: `uv run validate-frontmatter --config .project-standards.yml` Expected: success — validates the same managed set (exit 0, "✓ 9" managed docs unchanged).

- [ ] **Step 3: Commit**

```bash
git add .project-standards.yml
git commit -m "Exclude docs/handoff/** from frontmatter validation (handoff state is not a managed doc)"
```

---

### Task 8: Full-gate verification

No new files. Run every gate the spec lists as acceptance criteria and fix any finding before the final confirmation.

- [ ] **Step 1: Normalize formatting (rides the repo's Prettier layer)**

Run: `npm run format` Expected: Prettier rewrites any non-conformant Markdown/JSON; re-stage + amend the relevant prior commit if it touches an already-committed file, or commit as a fixup.

- [ ] **Step 2: v3 layout validator**

Run: `~/projects/agent-configs/scripts/handoff/validate-layout.sh ~/projects/project-standards` Expected: `layout validation passed: /home/chris/projects/project-standards`

- [ ] **Step 3: Frontmatter validator (dogfood)**

Run: `uv run validate-frontmatter --config .project-standards.yml` Expected: exit 0; the managed-doc count is unchanged from before the migration.

- [ ] **Step 4: Python toolchain unchanged-green**

Run: `uv run pytest && uv run ruff check . && uv run pyright` Expected: pytest 105 passed, ruff clean, pyright 0 errors.

- [ ] **Step 5: Markdown lint + format check**

Run: `npx markdownlint-cli2 && npm run format:check` Expected: markdownlint 0 errors; `prettier --check .` reports all files formatted.

- [ ] **Step 6: Bug index reproducibility**

Run: `python3 docs/handoff/bugs/_regen_index.py && git diff --exit-code docs/handoff/bugs/INDEX.md` Expected: no diff (exit 0).

- [ ] **Step 7: No dangling `working/` references; directory gone**

Run:

```bash
git grep -n "working/" -- . ':(exclude)docs/superpowers/**' || echo "no refs"
test ! -e working && echo "working/ gone"
```

Expected: `no refs` then `working/ gone`.

- [ ] **Step 8: Final commit if Step 1 produced changes**

```bash
git add -A
git commit -m "Formatting normalization after handoff-v3 migration" || echo "nothing to commit"
```

---

## Self-review notes

- **Spec coverage:** every relocation-map row and authored-file in the spec maps to a task (Task 1 authored core, Task 2 bugs, Task 3 moves+delete, Task 4 hook, Task 5 CLAUDE.md, Task 6 AGENTS.md, Task 7 exclude, Task 8 acceptance criteria 1–7).
- **Validator markers:** Task 6 Step 2 asserts the three required `AGENTS.md` substrings; Task 4 Step 5 asserts the three `settings.json` greps; Task 4 Step 2 asserts the hook hash — all matching `validate-layout.sh`.
- **Byte caps:** `state.md` (Task 1 Step 8 ≤2048), `CLAUDE.md` (Task 5 Step 2 ≤2048), `AGENTS.md` (Task 6 Step 2 ≤4096).
- **Hook integrity:** copied via `cp` (Task 4 Step 1), never Written, so the PostToolUse formatter cannot alter its bytes and break the hash check.
