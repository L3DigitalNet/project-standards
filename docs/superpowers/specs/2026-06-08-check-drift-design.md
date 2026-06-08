# Design: `check` — drift detection for adopted standards artifacts

**Date:** 2026-06-08 **Status:** approved (brainstorming complete; refined by codex-review round 3; plan ready at `2026-06-08-check-drift.md`) **Author:** session 2026-06-08

## Table of Contents

- [Design: `check` — drift detection for adopted standards artifacts](#design-check--drift-detection-for-adopted-standards-artifacts)
  - [Table of Contents](#table-of-contents)
  - [Problem / Goal](#problem--goal)
  - [Decisions (locked during brainstorming; refined by codex-review round 1)](#decisions-locked-during-brainstorming-refined-by-codex-review-round-1)
  - [Invariants — what must NOT change](#invariants--what-must-not-change)
  - [Component 1 — The state machine (with manifest-vs-lock reconciliation)](#component-1--the-state-machine-with-manifest-vs-lock-reconciliation)
  - [Component 2 — The lockfile (`.project-standards.lock`)](#component-2--the-lockfile-project-standardslock)
  - [Component 3 — CLI surface, flags \& exit codes](#component-3--cli-surface-flags--exit-codes)
  - [Component 4 — Module architecture](#component-4--module-architecture)
  - [Component 5 — `adopt` writes the lock](#component-5--adopt-writes-the-lock)
  - [Component 6 — `--update` write-safety \& ordering](#component-6----update-write-safety--ordering)
  - [Component 7 — Bootstrap (`--relock`) for already-adopted repos](#component-7--bootstrap---relock-for-already-adopted-repos)
  - [Component 8 — CI delivery](#component-8--ci-delivery)
  - [Component 9 — Testing](#component-9--testing)
  - [Acceptance criteria](#acceptance-criteria)
  - [Non-goals](#non-goals)
  - [Versioning impact](#versioning-impact)

## Problem / Goal

The `adopt` CLI (shipping in `2.1.0`) materializes a standard's artifacts — markdownlint/Prettier/EditorConfig configs, caller workflows, `AGENTS.md`/`CLAUDE.md`, the `check.yml` gate — by **copying** them into a consumer repo. Copy-adopt trades the live-pin coupling of the reusable-workflow model for **silent staleness**: once copied, nothing tells a consumer when the upstream standard moves on, or when someone hand-edited their adopted copy. That staleness is the copy-adopt model's only real weakness, and today there is no tooling to surface it.

`check` closes the lifecycle. The repo now covers **adopt** (materialize) and **enforce** (`validate-frontmatter`, `validate-id` fail CI on schema violations); `check` adds **drift detection** — telling a consumer when an adopted artifact has fallen behind the bundle, diverged from it locally, gone missing, or fallen out of sync with the standard's current artifact set.

## Decisions (locked during brainstorming; refined by codex-review round 1)

1. **Provenance lockfile.** `adopt` writes `.project-standards.lock` recording, per adopted artifact, a content hash at adopt time, plus the per-standard contract version and the tool release that wrote it. `check` reads it. (Rejected: stateless content-diff against only the current bundle — cannot distinguish a deliberate customization from being behind.)
2. **Failure model: staleness fails, edits warn.** `STALE`, `MISSING`, and `UNLOCKED` → exit 1 (CI red). `LOCAL-EDIT` and `ORPHAN` → reported but exit 0. The standards program is **adopt-then-own**: a consumer may customize an adopted file; `check` tells them they have diverged but does not forbid it. (Rejected: strict — any non-CLEAN fails; advisory — exit 0 unless `--strict`.)
3. **Detect + safe `--update`.** `check` detects; `check --update` re-syncs `STALE` and `MISSING` artifacts to the current template and re-stamps the lock (incl. `restamp-pending` repair), **refusing** to overwrite `LOCAL-EDIT`s or present-but-divergent `UNLOCKED`s (those require `--force`). This keeps the red→green path from contradicting decision 2. (Rejected: detect-only; `--update` + `--force` as the default surface.)
4. **Fragments excluded in Phase 1.** Manifests are the source of truth for the artifact set; today they yield two artifact classes — whole-file (`file`/`workflow-caller`, written atomically, hash cleanly) and `fragment` (`python-tooling` → `pyproject.toml`, `adr` → `.project-standards.yml`). `adopt` never writes fragments — it only prints a snippet for the human to paste, with no anchoring markers — so there is no deterministic region for `check` to hash. Fragments are listed as `SKIPPED (unmanaged fragment)`, never failing. "Managed fragments with markers" is a clearly-scoped follow-on. (Rejected: whole-file-hash the target — the consumer owns most of `pyproject.toml`, so it would report `LOCAL-EDIT` permanently.)
5. **Reconciliation is manifest-driven.** [SA-002] The set of _standards_ checked is lock-driven (everything in the lock); the set of _artifacts_ within each is the standard's **current manifest**, reconciled against the lock's baselines. This catches upstream-added artifacts and adopt-skipped files, which a purely lock-driven check would silently ignore.

## Invariants — what must NOT change

- The consumer contract for existing commands (`adopt`, `list`, `validate`) is unchanged except that `adopt` now **additionally** writes `.project-standards.lock` (a new file — additive, not breaking).
- Bundle manifests (`bundles/<id>/adopt.toml`) are the single source of truth for what each standard contributes and for artifact counts; `check` resolves them exactly as `adopt` does (same `resolve_source`, same `_render`, same `validate_dest`/symlink guards).
- The repo's own SSOT gate stays green (`ruff format --check`, `ruff check`, `basedpyright`, `coverage`, `pip-audit`).

## Component 1 — The state machine (with manifest-vs-lock reconciliation)

For each **locked standard** S, `check` iterates every whole-file artifact in **S's current manifest**, plus any lock-only entries (reconciliation). Per artifact `dest` it computes up to three sha256 hashes:

- `tmpl_hash` — the **rendered** current bundle template (`{{ref}}` substituted, exactly as `adopt` would write it). Always computable from the bundle.
- `disk_hash` — the file as it is on disk now (or `ABSENT`).
- `lock_hash` — recorded in `.project-standards.lock`, from either the `[S.artifacts]` table (template-backed baseline) or the `[S.local_edits]` table (a relock-accepted customization), or `NONE` if absent from both.

Decision order (the symlink guard runs **first**, before any read):

```text
dest is a symlinked leaf, or has a symlinked ancestor within --dest:
                         ──► UNSAFE      (exit 1)   # never follow the link to hash — could read outside --dest

dest in [S.local_edits] (relock-accepted customization):
    disk ABSENT          ──► MISSING     (exit 1)
    disk == tmpl         ──► CLEAN       (exit 0)   # consumer re-synced to the standard; --update promotes to [artifacts]
    else                 ──► LOCAL-EDIT  (exit 0)   # still consumer-owned; never STALE

else (normal artifact):
    disk ABSENT:
        dest in lock     ──► MISSING     (exit 1)   # was adopted, now gone
        dest not in lock ──► MISSING     (exit 1)   # manifest requires it, never adopted (e.g. new upstream artifact)
    disk == tmpl:
        lock_hash == tmpl_hash ──► CLEAN          (exit 0)   # matches current standard, lock agrees
        else                   ──► CLEAN          (exit 0)   # + restamp-pending flag (lock missing/behind; see below)
    disk != tmpl:
        lock_hash NONE   ──► UNLOCKED    (exit 1)   # present, not current, no baseline → cannot prove it was ever the standard
        disk == lock_hash──► STALE       (exit 1)   # template-backed baseline, untouched, standard moved on
        disk != lock_hash──► LOCAL-EDIT  (exit 0)   # changed since the template-backed baseline

dest in lock but NOT in S's current manifest:
                         ──► ORPHAN      (exit 0)   # upstream removed/renamed; --update drops the lock entry (leaves the file)
```

Why **content hashes** drive state (not version numbers): it catches a template that changed without a contract bump, and it treats "consumer manually updated to current" (`disk == tmpl`) as `CLEAN`. The `contract_version` in the lock is the human-readable reason string (`STALE — adopted contract 1.0, bundle 1.1`) and the re-stamp source. **Hashes decide; versions narrate.**

**The restamp-pending rule** [SA-003]: a `disk == tmpl` artifact whose lock entry is missing or `!= tmpl_hash` is still `CLEAN` (exit 0) but carries a **`restamp-pending`** flag. This is the residue of a partial `--update` (file written, lock write failed) — left unnamed, it would silently read `CLEAN` now and then mis-classify as `LOCAL-EDIT` after the _next_ template change instead of `STALE`. Making it a named flag means: (a) every `check` run shows it (incl. the CI step-summary/annotation, like `LOCAL-EDIT`), so it cannot rot unseen; (b) any lock-writing op (`adopt`, `check --update`, `check --relock`) repairs the entry to `tmpl_hash` + current `contract_version`. `--update` restamps pending entries even when nothing else is stale.

`MISSING` is distinct from an **unreadable** file: absent → `MISSING` (exit 1); read error (permissions) → I/O failure (exit 1) with a clear message, never a traceback. A symlinked destination is never read at all → `UNSAFE` (exit 1).

State → exit-code summary:

| State      | Exit | Meaning                                                    |
| ---------- | ---- | ---------------------------------------------------------- |
| CLEAN      | 0    | on disk == current template (may carry `restamp-pending`)  |
| LOCAL-EDIT | 0    | consumer changed an adopted/accepted file                  |
| ORPHAN     | 0    | locked artifact no longer in the manifest                  |
| STALE      | 1    | adopted, untouched, standard advanced                      |
| MISSING    | 1    | manifest/lock artifact absent on disk                      |
| UNLOCKED   | 1    | present, differs from current, no baseline to attribute it |
| UNSAFE     | 1    | destination is a symlink (leaf or ancestor) — not hashed   |

## Component 2 — The lockfile (`.project-standards.lock`)

TOML, at the consumer repo root, **committed by the consumer**, self-identifying from v1. [SA-005/SA-007] The version planes are kept distinct: per-standard `contract_version` is the `major.minor` contract plane from `registry.json` (e.g. `1.1` for markdown-frontmatter, `1.0` for the others); `tool_version` is the full-SemVer tool release that last wrote the lock.

```toml
# Managed by `project-standards`. Do not edit by hand.
lockfile_version = 1
tool_version = "2.2.0"            # the project-standards release that last wrote this lock

[markdown-tooling]
contract_version = "1.0"         # per-standard contract plane (major.minor) from registry.json — NOT the tool SemVer

[markdown-tooling.artifacts]     # template-backed baselines (written by adopt, or relock of a matching file)
".markdownlint.json"                  = "sha256:ab12…"
".prettierrc.json"                    = "sha256:cd34…"
".editorconfig"                       = "sha256:ef56…"   # shared; identical hash under python-tooling
".vscode/extensions.json"             = "sha256:1234…"
".github/workflows/lint-markdown.yml" = "sha256:7890…"   # rendered: {{ref}} → v2

# [markdown-tooling.local_edits]  # present only when --relock accepted a divergent file (see Component 7)
```

Design points:

- **Hash over rendered bytes.** `workflow-caller` templates carry a `{{ref}}` placeholder that `adopt` substitutes with `v<major>` at write time. The lock stores the hash of what is actually on disk (post-substitution), so `check` must reuse the engine's `_render()` to produce `tmpl_hash`. This is the decisive reason `check` lives **inside** the adopt package (Component 4).
- **Shared artifacts** (`.editorconfig`, `.vscode/extensions.json`, written by both `markdown-tooling` and `python-tooling`) are recorded under each owning standard with an identical hash. The report dedupes by `dest` and shows the most severe state across owners.
- **Writing TOML without a new dependency.** `tomllib` is read-only. `lock.py` hand-rolls a small serializer for this constrained schema (top-level scalars + `[standard]` tables with `contract_version` and the `artifacts`/`local_edits` string→string sub-tables); destinations are quoted TOML keys.
- **Unsupported `lockfile_version`** (greater than the running tool supports, or missing) → `LockError` exit 2 with guidance to upgrade `project-standards`; never a silent mis-parse.
- Fragments are **never** recorded in the lock.

## Component 3 — CLI surface, flags & exit codes

```text
project-standards check [--dest DIR] [--update [--force]] [--json] [--quiet]
project-standards check --relock STANDARD [STANDARD ...] [--dest DIR] [--quiet]
```

- **Which standards are checked:** plain `check` is **lock-driven** — every standard in `.project-standards.lock`, no positional argument. `--relock` (Component 7) has no lock to read, so it takes the adopted standards **positionally**, like `adopt`.
- `--dest DIR` — consumer repo root (default: cwd), same as `adopt`.
- (default) — detect and report; exit code = the most severe per-artifact code.
- `--update` — bring the repo to green and repair lock provenance. Per state [SA-NEW-001]: `MISSING` → write the template + lock it (no existing file to clobber); `STALE` → overwrite with the template + restamp; `restamp-pending` `CLEAN` → restamp the lock only (no file write); `ORPHAN` → drop the lock entry (leave the file); `UNLOCKED` (present, divergent, no baseline) and `LOCAL-EDIT` → **skip** with "use `--force`"; `UNSAFE` → never written, reported. Restamps pending entries even when nothing else needs syncing.
- `--force` — only valid **with** `--update`; additionally overwrite `LOCAL-EDIT`s and divergent `UNLOCKED`s with the current template. Never overwrites an `UNSAFE` (symlinked) destination.
- `--relock` — bootstrap; mutually exclusive with `--update`/`--force` (Component 7).
- `--json` — machine-readable report (schema below); valid with the default and `--update` modes.
- `--quiet` — exit code only; suppress the human report.

**Flag-combination matrix** [SA-008] (invalid combinations exit 2 with a usage error, never relying on accidental argparse behavior):

| Combination | Result |
| --- | --- |
| `--force` without `--update` | error, exit 2 |
| `--relock` with `--update`/`--force` | error, exit 2 |
| `--relock` without positional standards | error, exit 2 |
| `--update --json` | apply update, emit post-update state as JSON |

**JSON schema** (`--json`), stable contract mirroring `list --json`'s discipline:

```json
{
	"lockfile_version": 1,
	"tool_version": "2.2.0",
	"standards": [
		{
			"id": "markdown-tooling",
			"contract_version": "1.0",
			"artifacts": [
				{
					"dest": ".markdownlint.json",
					"state": "CLEAN",
					"restamp_pending": false,
					"owners": ["markdown-tooling"]
				},
				{
					"dest": ".prettierrc.json",
					"state": "CLEAN",
					"restamp_pending": true,
					"owners": ["markdown-tooling"]
				},
				{
					"dest": ".editorconfig",
					"state": "STALE",
					"restamp_pending": false,
					"owners": ["markdown-tooling", "python-tooling"]
				}
			],
			"fragments": [{ "target": "pyproject.toml", "state": "SKIPPED" }]
		}
	],
	"summary": {
		"clean": 12,
		"restamp_pending": 1,
		"stale": 1,
		"local_edit": 1,
		"missing": 0,
		"unlocked": 0,
		"orphan": 0,
		"unsafe": 0,
		"exit_code": 1
	}
}
```

`restamp_pending` is a flag on a `CLEAN` artifact, not a separate state, so it never changes the exit code; it is counted in `summary` for visibility.

**Exit codes** (aligned with the existing CLIs, including `adopt`'s `ManifestError`): [SA-006] `0` = all `CLEAN`/`LOCAL-EDIT`/`ORPHAN`; `1` = any `STALE`/`MISSING`/`UNLOCKED`/`UNSAFE` or recoverable I/O failure; `2` = corrupt/missing/unsupported lock, bad invocation, or registry/bundle parity drift; `3` = `ManifestError` (a manifest/template is missing or unresolvable, or the package version can't resolve) — the same exit `3` `adopt` already returns, since `check` reads the same manifests and renders the same templates.

## Component 4 — Module architecture

`check` is built **inside the `adopt/` package** — drift is the inverse of adopt and must share manifest resolution, `_render()`, and the path-safety helpers, byte-for-byte. (Alternatives rejected: a top-level `check.py` sibling to `validate_id.py` would duplicate render/marker logic that must stay identical to the writer; a full engine refactor into a shared resolver is too much churn on code shipped days earlier.)

| Module | Responsibility |
| --- | --- |
| `adopt/lock.py` | `Lock` / `StandardLock` / `LockedArtifact` dataclasses; `load_lock` (validates `lockfile_version`), `write_lock`, `merge_and_write`, `sha256_bytes`, the hand-rolled TOML serializer. Pure I/O + parsing; mirrors `manifest.py` style. |
| `adopt/check.py` | `compute_states(lock, dest_root, registry)` → ordered `ArtifactState`s (manifest-vs-lock reconciliation + the hash rules); `apply_update(states, dest_root, *, force)`; `relock(standards, dest_root)`; `format_check_report(...)` and `states_to_json(...)`. |
| `adopt/engine.py` | `execute_plan` gains `Report.hashes: dict[dest, sha256]` so `adopt` can stamp the lock without re-rendering; `apply_update` reuses `validate_dest`, the symlink guards, `_render`, and `_atomic_write`. |
| `cli.py` | `check` subcommand + flag validation; `adopt` path calls `lock.merge_and_write(...)` after a successful, non-dry-run plan. |
| `adopt/errors.py` | add `LockError` (exit 2) for corrupt/unsupported lock; reuse the existing `AdoptError`/`ManifestError` boundary in `cli.main`. |

## Component 5 — `adopt` writes the lock

Every `adopt` / `adopt --force` run merges its written whole-file artifacts into `.project-standards.lock`, creating it if absent and recording `lockfile_version`, the run's `tool_version`, each standard's `contract_version` (from the registry), and each `dest`'s rendered hash under `[S.artifacts]`. `--dry-run` writes nothing (no files, no lock). Fragments are not recorded. The merge is per-standard: re-adopting one standard leaves other standards' lock entries intact.

**Adopt-skip interaction** [SA-002]: `execute_plan` skips a destination that already exists (without `--force`) and therefore does not record a hash for it. Such a file is consequently **not** in `[S.artifacts]`; at `check` time it surfaces as `UNLOCKED` (if it differs from the template) or `CLEAN` (if it happens to match). This is intentional and correct — an existing-but-unlocked file is exactly the un-reconciled state the consumer should resolve via `--update`/`--force` or `--relock`.

## Component 6 — `--update` write-safety & ordering

**Read-path symlink safety** [SA-003]: even the read-only default `check` classifies a destination that is a symlinked leaf, or that has a symlinked ancestor within `--dest`, as `UNSAFE` (exit 1) and **never follows the link to hash it** — reusing adopt's `is_symlink` + `_has_symlinked_ancestor` checks (`engine.py:150-162, 220`). This prevents `check` from reading bytes outside `--dest` via a planted symlink.

**Write-path safety:** `apply_update` carries the **same write-boundary guarantees as `adopt`**: `validate_dest` containment, refusal to write through a symlinked leaf/ancestor, and `_atomic_write` (temp-file + `os.replace`). It never writes outside `--dest`.

**Ordering & failure semantics:** update writes each file first (atomically, independently), then writes the lock **last**, in a single atomic `write_lock`. Consequences:

- A failure mid-update leaves some files updated (each atomically) and the lock **un-advanced**. The next `check` re-derives state from disk: updated files read `CLEAN` with `restamp-pending` set (`disk == tmpl` but `lock_hash` stale), not-yet-updated files remain `STALE`. No false green, and the pending flag is visible on every run.
- A failure of the final lock write (after files updated) → exit 1 with an explicit "files updated; lock not written — re-run `check --update` to restamp" message. Re-running restamps the pending entries idempotently (it sees `disk == tmpl` and writes `tmpl_hash`). The lock never advances ahead of a file that did not actually change, and the `restamp-pending` flag guarantees the under-stamped condition is surfaced (CI annotation) until repaired — closing the "later template change misreads as `LOCAL-EDIT`" gap.
- `ORPHAN` lock entries are pruned during the same lock write.

## Component 7 — Bootstrap (`--relock`) for already-adopted repos

Repos adopted under `2.1.0` have no lock. `check` with no lock present exits 2 with guidance (not a traceback): _"no `.project-standards.lock` found; run `project-standards adopt …` or `project-standards check --relock <standard>…` to baseline."_

`check --relock STANDARD...` resolves each named standard's manifest and, per whole-file artifact: [SA-001]

- `disk == tmpl` → record under `[S.artifacts]` at the current `contract_version` (a genuine template-backed baseline; reports `CLEAN` thereafter).
- `disk` present but `!= tmpl` → record under `[S.local_edits]` (an **accepted customization** baseline). Such entries report `LOCAL-EDIT` (exit 0) and are **never** classified `STALE`, because their hash was never a template — the separate table is what makes the state machine consistent.
- `disk ABSENT` → not recorded; surfaces as `MISSING` on the next `check` (the consumer never adopted it).

This delivers the zero-clobber migration honestly: relock writes files for nobody, baselines matching files as clean and customized files as accepted edits, and the documented caveat is that it cannot recover true adoption history — a file the consumer drifted _before_ relock is baselined as that consumer's accepted edit, not flagged as upstream staleness.

## Component 8 — CI delivery

A new reusable workflow lets consumers run drift detection in CI, mirroring `validate-markdown-frontmatter.yml`:

- **Ref-pinned execution** [SA-004]: the reusable workflow takes a `standards-ref` input and runs the checker from the **matching git ref**, exactly like the existing validator workflow, so the bundled manifests/templates the checker compares against are the same release the caller pinned:

  ```yaml
  uvx --from "git+https://github.com/L3DigitalNet/project-standards@${{ inputs.standards-ref || 'v2' }}" \ project-standards check
  ```

  Plain `uvx project-standards check` is rejected — `uvx` resolves to latest/cached unless a source is pinned, which would silently decouple the checker from the consumer's intended release.

- **Naming**: caller template `drift-check.caller.yml`; reusable workflow `.github/workflows/standards-drift.yml` — named to avoid colliding with the repo's internal `check.yml` gate **and** with the `check.yml` the `python-tooling` bundle ships to consumers. A single, standard-agnostic caller (it runs one lock-driven `check` over the whole repo, so unlike the per-standard validate/lint callers it is not bundle-scoped).
- **Surfacing non-failing drift on a green run** [SA-009]: because `LOCAL-EDIT`/`ORPHAN`/`restamp-pending` exit 0, the workflow writes a `$GITHUB_STEP_SUMMARY` table and emits `::warning::` annotations for each, so divergence (and a lock that needs restamping) is visible on a passing run rather than buried in logs.

Additive; may land in the same release or immediately after the core command.

## Component 9 — Testing

[Counts are derived from the manifests at test time, never hardcoded — SA-002 note.]

- Lock round-trip: `write_lock` → `load_lock` → structural equality; serializer key-quoting/escaping; `lockfile_version` accepted/missing/too-new (→ `LockError`).
- Every state via constructed fixtures: `CLEAN`, `STALE`, `LOCAL-EDIT`, `MISSING`, `UNLOCKED`, `ORPHAN`, `UNSAFE`, plus the `[local_edits]` → `LOCAL-EDIT`/promote-to-`CLEAN` edges.
- **Absent-from-lock trio** [SA-NEW-001]: a current-manifest artifact missing from the lock in all three disk states — absent (`MISSING`), present-and-equal-to-template (`CLEAN` + `restamp-pending`), present-and-divergent (`UNLOCKED`) — asserting default state/exit, `--update`, and `--update --force` behavior for each.
- **Restamp lifecycle** [SA-003]: simulate a `--update` whose file write succeeds but lock write fails → assert exit 1 and `restamp-pending` `CLEAN` on the next `check`; re-run `--update` → assert lock repaired; then bump the template → assert the file is now `STALE` (not `LOCAL-EDIT`). This is the regression test for the closed gap.
- **Read-path symlink** [SA-003]: a symlinked-leaf and a symlinked-ancestor destination → `UNSAFE` (exit 1), and assert the link target's bytes are never read.
- `{{ref}}` rendered-hash correctness for a `workflow-caller` artifact (lock hash matches on-disk rendered bytes).
- Shared-artifact dedup: a shared dest under two standards reported once at the most severe state.
- `--update`: re-syncs `STALE`/`MISSING` and repairs `restamp-pending` only, skips `LOCAL-EDIT` and divergent `UNLOCKED` without `--force`, prunes `ORPHAN`, re-stamps the lock for changed dests only; `--force` overwrites edits.
- `--update` safety (mirroring `test_adopt_safety.py`): symlinked leaf, symlinked ancestor, file-write failure injection, lock-write failure injection (asserting no false green), partial multi-file update.
- `--relock`: matching file → `[artifacts]`/`CLEAN`; divergent file → `[local_edits]`/`LOCAL-EDIT` and never `STALE`; absent file → `MISSING`.
- Fragments excluded: `pyproject.toml` / `.project-standards.yml` always `SKIPPED`.
- No-lock → clean exit 2 with guidance.
- CLI flag matrix: `--force` without `--update`, `--relock` with `--update`, `--relock` without standards → exit 2.
- Exit codes for every path incl. `ManifestError` → 3 (broken manifest/source fixture) and corrupt lock → 2.
- `--json` snapshot: field shape, dedupe representation, skipped fragments, summary + `exit_code`.
- `adopt` writes the lock with correct `contract_version`/`tool_version`; `--dry-run` does not.
- CI: rendered caller + reusable workflow both pin the same major ref; `LOCAL-EDIT` produces a step-summary/annotation on a green run.
- Dogfood via adopt-into-tempdir (the existing adopt test pattern).

## Acceptance criteria

- `project-standards check` reports a reconciled per-artifact state for every whole-file artifact in each locked standard's current manifest and marks fragments `SKIPPED`, honoring the exit-code table.
- `adopt` produces a `.project-standards.lock` (with `lockfile_version`, `tool_version`, per-standard `contract_version`) whose hashes make a fresh `check` report all-`CLEAN`.
- `check --update` returns a `STALE`/`MISSING` repo to green without touching `LOCAL-EDIT`s, using adopt's symlink/atomic-write protections, and never advances the lock past a file that did not change.
- `check --relock` baselines an already-adopted repo with zero file writes and never misreports a customized file as `STALE`.
- The reusable drift workflow runs the checker from the caller-pinned git ref.
- Full SSOT gate green; new code coverage in line with the adopt engine (~94%+).

## Non-goals

- Managed fragments (markers in `pyproject.toml` / `.project-standards.yml`) — future feature.
- A general file-diff/patch view — `check` reports state, not line-level diffs.
- Auto-committing the lock or the re-synced files — that is the consumer's git workflow.
- Cross-major lock migration tooling — `lockfile_version` reserves the surface; migration logic is out of scope until a v2 format exists.

## Versioning impact

New feature → **`2.2.0`**, landing after `2.1.0` (adopt) ships. `adopt` writing a lock and the new reusable workflow are both additive (new files), not breaking. The lock is self-identifying via `lockfile_version = 1` from the first release; an unsupported version is a clean `LockError` (exit 2), reserving room for future format changes without guesswork.
