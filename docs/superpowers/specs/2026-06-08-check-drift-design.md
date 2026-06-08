# Design: `check` — drift detection for adopted standards artifacts

**Date:** 2026-06-08 **Status:** approved (brainstorming complete; awaiting plan) **Author:** session 2026-06-08

## Table of Contents

- [Problem / Goal](#problem--goal)
- [Decisions (locked during brainstorming)](#decisions-locked-during-brainstorming)
- [Invariants — what must NOT change](#invariants--what-must-not-change)
- [Component 1 — The state machine](#component-1--the-state-machine)
- [Component 2 — The lockfile (`.project-standards.lock`)](#component-2--the-lockfile-project-standardslock)
- [Component 3 — CLI surface & exit codes](#component-3--cli-surface--exit-codes)
- [Component 4 — Module architecture](#component-4--module-architecture)
- [Component 5 — `adopt` writes the lock](#component-5--adopt-writes-the-lock)
- [Component 6 — Bootstrap for already-adopted repos](#component-6--bootstrap-for-already-adopted-repos)
- [Component 7 — CI delivery](#component-7--ci-delivery)
- [Component 8 — Testing](#component-8--testing)
- [Acceptance criteria](#acceptance-criteria)
- [Non-goals](#non-goals)
- [Versioning impact](#versioning-impact)

## Problem / Goal

The `adopt` CLI (shipping in `2.1.0`) materializes a standard's artifacts — markdownlint/Prettier/EditorConfig configs, caller workflows, `AGENTS.md`/`CLAUDE.md`, the `check.yml` gate — by **copying** them into a consumer repo. Copy-adopt trades the live-pin coupling of the reusable-workflow model for **silent staleness**: once copied, nothing tells a consumer when the upstream standard moves on, or when someone hand-edited their adopted copy. That staleness is the copy-adopt model's only real weakness, and today there is no tooling to surface it.

`check` closes the lifecycle. The repo now covers **adopt** (materialize) and **enforce** (`validate-frontmatter`, `validate-id` fail CI on schema violations); `check` adds **drift detection** — telling a consumer when an adopted artifact has fallen behind the bundle or diverged from it locally.

## Decisions (locked during brainstorming)

1. **Provenance lockfile.** `adopt` writes `.project-standards.lock` recording, per adopted artifact, the standard's contract version and a content hash at adopt time. `check` reads it. (Rejected: stateless content-diff against only the current bundle — cannot distinguish a deliberate customization from being behind, and cannot report "adopted 2.0.0".)
2. **Failure model: staleness fails, edits warn.** `STALE` and `MISSING` → exit 1 (CI red). `LOCAL-EDIT` → reported but exit 0. The standards program is **adopt-then-own**: a consumer may customize an adopted file; `check` tells them they have diverged but does not forbid it. (Rejected: strict — any non-CLEAN fails; advisory — exit 0 unless `--strict`.)
3. **Detect + safe `--update`.** `check` detects; `check --update` re-syncs only `STALE`-and-unedited artifacts and re-stamps the lock, **refusing** to overwrite `LOCAL-EDIT`s (those still require `--force`). This keeps the red→green path from contradicting decision 2. (Rejected: detect-only; detect + `--update` + `--force` as the default surface.)
4. **Fragments excluded in Phase 1.** Of 17 artifacts across the four standards, 15 are `file`/`workflow-caller` (whole-file writes — hash cleanly) and 2 are `fragment` (`python-tooling` → `pyproject.toml`, `adr` → `.project-standards.yml`). `adopt` never writes fragments — it only prints a snippet for the human to paste, with no anchoring markers — so there is no deterministic region for `check` to hash. Fragments are listed as `unmanaged fragment (skipped)`, never `STALE`/`LOCAL-EDIT`. "Managed fragments with markers" is a clearly-scoped follow-on, not in this spec. (Rejected: whole-file-hash the target — the consumer owns most of `pyproject.toml`, so it would report `LOCAL-EDIT` permanently.)

## Invariants — what must NOT change

- The consumer contract for existing commands (`adopt`, `list`, `validate`) is unchanged except that `adopt` now **additionally** writes `.project-standards.lock` (a new file — additive, not breaking).
- Bundle manifests (`bundles/<id>/adopt.toml`) are the single source of truth for what each standard contributes; `check` resolves them exactly as `adopt` does (same `resolve_source`, same `_render`).
- The repo's own SSOT gate stays green (`ruff format --check`, `ruff check`, `basedpyright`, `coverage`, `pip-audit`).

## Component 1 — The state machine

Per checkable artifact (`file`/`workflow-caller`), `check` computes three sha256 hashes and derives state from **content**, not version numbers:

- `lock_hash` — recorded in `.project-standards.lock` (what `adopt` wrote)
- `disk_hash` — the file as it is on disk now
- `tmpl_hash` — the **rendered** current bundle template (`{{ref}}` substituted, exactly as `adopt` would write it)

```text
file absent on disk?            ──► MISSING     (exit 1)
disk_hash == tmpl_hash?         ──► CLEAN        (exit 0)   # matches current standard
  else (differs from current template):
    disk_hash == lock_hash?     ──► STALE        (exit 1)   # untouched since adopt; standard moved on
    disk_hash != lock_hash?     ──► LOCAL-EDIT   (exit 0)   # consumer changed it; not current → warn
```

Rationale for hash-driven (not version-driven) state:

- Catches a template that changed **without** a contract-version bump.
- Treats "consumer manually updated the file to current" (`disk == tmpl`, `disk != lock`) as `CLEAN`, not a phantom edit.
- The `contract` version in the lock is used only for the human-readable reason string (`STALE — adopted 2.0.0, bundle 2.1.0`) and for re-stamping. **Hashes decide; versions narrate.**

`MISSING` is distinct from an **unreadable** file: absent → `MISSING` (exit 1); read error (permissions, etc.) → I/O failure (exit 1) with a clear message, never a traceback.

## Component 2 — The lockfile (`.project-standards.lock`)

TOML, at the consumer repo root, **committed by the consumer**, keyed by the `dest` (the actual on-disk relative path):

```toml
# Managed by `project-standards`. Do not edit by hand.
[markdown-tooling]
contract = "2.0.0"

[markdown-tooling.artifacts]
".markdownlint.json"                  = "sha256:ab12…"
".prettierrc.json"                    = "sha256:cd34…"
".editorconfig"                       = "sha256:ef56…"   # shared; identical hash under python-tooling
".vscode/extensions.json"             = "sha256:1234…"
".github/workflows/lint-markdown.yml" = "sha256:7890…"   # rendered: {{ref}} → v2
```

Design points:

- **Hash over rendered bytes.** `workflow-caller` templates carry a `{{ref}}` placeholder that `adopt` substitutes with `v<major>` at write time. The lock stores the hash of what is actually on disk (post-substitution), so `check` must reuse the engine's `_render()` to produce `tmpl_hash`. This is the decisive reason `check` lives **inside** the adopt package (see Component 4).
- **Shared artifacts** (`.editorconfig`, `.vscode/extensions.json` are written by both `markdown-tooling` and `python-tooling`) are recorded under each owning standard with an identical hash. The report dedupes by `dest` and shows `STALE` if stale under **any** owner.
- **Writing TOML without a new dependency.** `tomllib` is read-only. `lock.py` hand-rolls a small serializer for this flat `string → string` table schema rather than adding `tomli-w`.
- Fragments are **never** recorded in the lock.

## Component 3 — CLI surface & exit codes

New `check` subcommand on the `project-standards` CLI:

```text
project-standards check [--dest DIR] [--update] [--force] [--json] [--quiet]
project-standards check --relock STANDARD [STANDARD ...] [--dest DIR]
```

- **Which standards are checked:** plain `check` is **lock-driven** — it checks every standard present in `.project-standards.lock`, no positional argument. `--relock` (Component 6) has no lock to read, so it takes the adopted standards **positionally**, like `adopt`.
- `--dest DIR` — consumer repo root (default: cwd), same as `adopt`.
- (default) — detect and report; exit code = the most severe per-artifact code.
- `--update` — re-sync `STALE`-and-unedited artifacts to the current template, re-stamp the lock; **skip** `LOCAL-EDIT` (print "use `--force`").
- `--force` — with `--update`, additionally overwrite `LOCAL-EDIT`s.
- `--relock` — bootstrap: stamp the lock from current on-disk state (see Component 6).
- `--json` — machine-readable state report (mirrors `list --json`).
- `--quiet` — exit code only.

Exit codes (consistent with the existing CLIs): `0` = all `CLEAN`/`LOCAL-EDIT`; `1` = any `STALE`/`MISSING`/recoverable I/O failure; `2` = corrupt/missing lock, bad invocation, or registry/bundle drift.

## Component 4 — Module architecture

`check` is built **inside the `adopt/` package** — drift is the inverse of adopt and must share manifest resolution, `_render()`, and the path-safety helpers, byte-for-byte. (Alternatives considered and rejected: a top-level `check.py` sibling to `validate_id.py` — would duplicate `_render`/render logic that must stay identical to the writer, risking writer/reader drift; a full engine refactor into a shared artifact-resolver core — too much churn on code shipped days earlier.)

| Module | Responsibility |
| --- | --- |
| `adopt/lock.py` | `Lock` / `LockedArtifact` dataclasses; `load_lock`, `write_lock`, `merge_and_write`, `sha256_bytes`. Pure I/O + parsing; mirrors `manifest.py` style. |
| `adopt/check.py` | `compute_states(standards, dest_root, registry)` → ordered `ArtifactState`s (combines lock + resolved bundle + on-disk hashes); `apply_update(...)`; `format_check_report(...)`. |
| `adopt/engine.py` | `execute_plan` gains `Report.hashes: dict[dest, sha256]` so `adopt` can stamp the lock without re-rendering. |
| `cli.py` | `check` subcommand; `adopt` path calls `lock.merge_and_write(...)` after a successful, non-dry-run plan. |
| `adopt/errors.py` | add `LockError` (exit 2) for a corrupt/unparseable lock; reuse the existing `AdoptError` boundary in `cli.main`. |

## Component 5 — `adopt` writes the lock

Every `adopt` / `adopt --force` run merges its written `file`/`workflow-caller` artifacts into `.project-standards.lock`, creating it if absent and recording each standard's current contract version plus each `dest`'s rendered hash. `--dry-run` writes nothing (no files, no lock). Fragments are not recorded. The merge is per-standard: re-adopting one standard leaves other standards' lock entries intact.

## Component 6 — Bootstrap for already-adopted repos

Repos adopted under `2.1.0` have no lock. `check` with no lock present exits 2 with guidance (not a traceback): *"no `.project-standards.lock` found; run `project-standards adopt …` or `project-standards check --relock` to baseline."*

`check --relock STANDARD...` hashes current on-disk files for the named standards and stamps the lock at the **current** contract with current disk hashes — treating present state as the baseline. Honest caveat (documented in help + the standard's adopt doc): `--relock` cannot recover true adoption history, so a file the consumer already drifted is baselined as clean. This gives existing adopters a **zero-clobber** path onto the lock, unlike `adopt --force`.

## Component 7 — CI delivery

A new reusable workflow lets consumers run drift detection in CI, mirroring `validate-markdown-frontmatter.yml`:

- Caller template: a single, standard-agnostic `drift-check.caller.yml` (it runs one lock-driven `check` over the whole repo, so unlike the per-standard validate/lint callers it is not bundle-scoped).
- Reusable workflow: `.github/workflows/standards-drift.yml` — named to avoid colliding with the repo's internal `check.yml` gate **and** with the `check.yml` the `python-tooling` bundle ships to consumers.
- Runs `uvx project-standards check` against the consumer checkout.

Additive; may land in the same release or immediately after the core command.

## Component 8 — Testing

- Lock round-trip: `write_lock` → `load_lock` → structural equality; hand-rolled serializer escaping.
- Each state via constructed fixtures: `CLEAN`, `STALE`, `LOCAL-EDIT`, `MISSING`, plus the `disk == tmpl, disk != lock` → `CLEAN` edge.
- `{{ref}}` rendered-hash correctness for a `workflow-caller` artifact (lock hash matches on-disk rendered bytes).
- Shared-artifact dedup: `.editorconfig` under two standards reported once.
- `--update`: re-syncs `STALE` only, skips `LOCAL-EDIT`, re-stamps the lock for updated dests only; `--force` overwrites edits.
- Fragments excluded: `pyproject.toml` / `.project-standards.yml` never `STALE`/`LOCAL-EDIT`.
- No-lock → clean exit 2 with guidance; `--relock` baselines current state.
- Exit codes for every path; corrupt lock → `LockError` exit 2.
- `adopt` writes the lock; `--dry-run` does not.
- Dogfood via adopt-into-tempdir (the existing adopt test pattern).

## Acceptance criteria

- `project-standards check` reports per-artifact state for all 15 whole-file artifacts and skips the 2 fragments, with the exit-code contract above.
- `adopt` produces a `.project-standards.lock` whose hashes make a fresh `check` report all-`CLEAN`.
- `check --update` returns a `STALE` repo to green without touching `LOCAL-EDIT`s.
- Full SSOT gate green; new code coverage in line with the adopt engine (~94%+).

## Non-goals

- Managed fragments (markers in `pyproject.toml` / `.project-standards.yml`) — future feature.
- A general file-diff/patch view — `check` reports state, not line-level diffs.
- Auto-committing the lock or the re-synced files — that is the consumer's git workflow.
- Detecting drift in artifacts the consumer never adopted (not in the lock = not checked).

## Versioning impact

New feature → **`2.2.0`**, landing after `2.1.0` (adopt) ships. `adopt` writing a lock and the new reusable workflow are both additive (new files), not breaking. The `.project-standards.lock` format is itself a versioned surface; a `lockfile_version` field is reserved for future format changes.
