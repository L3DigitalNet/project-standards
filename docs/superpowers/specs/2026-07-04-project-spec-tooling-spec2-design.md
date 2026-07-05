# Design: `project-standards spec new` — Spec #2 (guarded-generative scaffold)

**Date:** 2026-07-04 **Status:** approved (brainstorming complete; codex spec-review converged r2 — 0 blocking) **Author:** session 2026-07-04

## Table of Contents

- [Design: `project-standards spec new` — Spec #2 (guarded-generative scaffold)](#design-project-standards-spec-new--spec-2-guarded-generative-scaffold)
  - [Table of Contents](#table-of-contents)
  - [Problem / Goal](#problem--goal)
  - [Scope decomposition (the write seam splits again)](#scope-decomposition-the-write-seam-splits-again)
  - [Decisions (locked during brainstorming)](#decisions-locked-during-brainstorming)
  - [Invariants — the consumer contract (must NOT change)](#invariants--the-consumer-contract-must-not-change)
  - [Component 1 — CLI surface \& flag matrix](#component-1--cli-surface--flag-matrix)
  - [Component 2 — Module layout \& reuse](#component-2--module-layout--reuse)
  - [Component 3 — The fill operation (`scaffold`)](#component-3--the-fill-operation-scaffold)
  - [Component 4 — `spec_id` minting \& tolerant discovery](#component-4--spec_id-minting--tolerant-discovery)
  - [Component 5 — Write model \& safety](#component-5--write-model--safety)
  - [Component 6 — Error handling \& exit codes](#component-6--error-handling--exit-codes)
    - [`--json` output contract](#--json-output-contract)
  - [Component 7 — Testing](#component-7--testing)
  - [Acceptance criteria](#acceptance-criteria)
  - [Non-goals](#non-goals)
  - [Versioning \& docs impact](#versioning--docs-impact)
  - [Open implementation questions (for the plan, not blockers)](#open-implementation-questions-for-the-plan-not-blockers)

## Problem / Goal

Spec #1 shipped the read-only half of the `project-spec` tooling: a shared registry core parsed from the bundled templates, plus `validate`, `lint`, `extract`, and `next`. A consumer can now mechanically check a spec they have already written — but nothing helps them _start_ one. Today "create a spec" means hand-copying a template, hand-minting a `spec_id` that matches `^SPEC-[0-9A-Z]{4}$`, and hand-editing frontmatter — every step a chance to produce a spec that `validate` will immediately reject.

The goal of Spec #2 is the first **guarded-generative** command, `new`: scaffold a conformant spec from a chosen profile so that the very first thing the tool writes already passes `validate`. It delivers guarantees **G1** (a conformant starting point) and **G7** (deterministic tooling) from the standard's Features list. Like all the tooling it must be agent/CI-safe: no prompts, deterministic exit codes, machine-readable `--json` (a **universal** tooling contract — README §5: "Every command … offers machine-readable `--json` output"), and — because it now _writes files_ — a safety model that never destroys existing work.

The command is specified in prose today in [README §5](../../../standards/project-spec/README.md) under **Author — guarded generative**:

> **`new`** _(core)_ — scaffold a spec from a chosen profile: copy the template, mint a fresh `spec_id`, and fill frontmatter (owner, implementer, created, profile) and title, resolving the sentinel. → **G1, G7**

## Scope decomposition (the write seam splits again)

Spec #1 split the v1-core set along a read/write seam and deferred both generative authors to "Spec #2." Brainstorming refined that: `new` and `upgrade` sit on **opposite sides of a mutation-risk seam**, so they split into two specs of their own.

- **Spec #2 (this doc)** — **`new`** only. Writes a **brand-new file**; its worst case is refusing to clobber an existing one. It never touches prose a human has written, so the "never rewrites existing prose" guarantee holds _by construction_.
- **Spec #3 (future)** — **`upgrade`** (additive tier promotion, Light → Standard → Full). It must splice canonical sections into a document an author has already filled — an in-place mutation whose whole difficulty _is_ preserving surrounding prose. That is a materially higher risk profile and earns its own spec, built on the `new` scaffolding proven here.

`status` (a reporting rollup) and the **semantic-review contract** (a standard-defined checklist, not a binary command) remain deferred exactly as README §5 marks them.

## Decisions (locked during brainstorming)

1. **Scope = `new` only.** `upgrade` is Spec #3 (mutation-risk seam, above).
2. **Write model = explicit `PATH`, refuse-if-exists, `--stdout` preview, atomic write.** `new … PATH` writes the file _atomically_ (temp file in the destination directory, then `os.replace`); refuses (exit 2) if `PATH` exists unless `--force`; `--stdout` prints to stdout and never touches disk. Re-running `new` can never silently overwrite an in-progress spec, and no failure ever leaves a partially-written file.
3. **`spec_id` = random, collision-checked, `--id` override, bounded retries.** Mint a random 4-char `[0-9A-Z]` id; scan the specs that discovery finds and retry on collision, up to a fixed attempt cap; `--id SPEC-AB12` overrides for determinism. An empty corpus (no config, no specs) is **not** an error here — unlike `validate`, `new` must work in a repo that has no specs yet.
4. **Human fields via optional flags, template placeholder as fallback.** `--title`/`--owner`/`--implementer` fill their fields when passed; an omitted field keeps the template's own `'<…>'` placeholder verbatim. Machine fields (`spec_id`, `created`, `last_reviewed`) are always filled; `status` stays `draft`; `profile` is set by _selecting_ the tier's template file, not by rewriting a line.
5. **Fill mechanism = surgical line-rewrite.** Rewrite only the specific frontmatter lines that change (and the H1 title line iff `--title` is given); copy the rest of the template byte-for-byte. Rejected: parse-to-`SpecDocument`-and-re-serialize (the parser is lossy — drops comments, normalizes formatting), and named-placeholder templating (would mutate the canonical templates, breaking Spec #1's byte-identical dogfood guard, and add a runtime dependency).
6. **`--profile` is required.** No silent default; choosing a tier is a deliberate authoring act.
7. **`new` self-validates its output (fail-closed).** Before writing, `new` parses and validates the generated text in memory; if it is not `validate`-clean it refuses to write and reports the finding. A **parse failure** of the generated text (`SpecParseError`, e.g. from a future template edit) is caught in the same block and mapped to `self_validation_failed` — it must not escape as the outer `spec` group's generic exit-1 parse path. This makes "`new` always emits a validate-clean scaffold" a runtime invariant, not just a test-time hope.
8. **`--json` is mandatory (universal tooling contract).** `new` offers `--json` for both success and failure, per README §5. The default (non-`--json`) output stays human-oriented.
9. **Flag values are serialized YAML-safely; control characters are rejected.** `--title`/`--owner`/`--implementer` values are emitted through a YAML scalar serializer (PyYAML), so quotes, colons, and Unicode are escaped correctly rather than hand-quoted. Values containing a newline, carriage return, or other C0/C1 control character, and the empty string, are rejected with a usage error (exit 2) — an agent-safe CLI must handle non-interactive input predictably. **`--title` additionally rejects the backtick** (`` ` ``): unlike owner/implementer (which land only in YAML frontmatter, where `emit_scalar` makes any character safe), the title is also substituted into the H1's Markdown **code span** (`` # `…` — Specification (T) ``), where a backtick would break the span. Rejecting is more predictable than inventing a code-span-escaping rule.

## Invariants — the consumer contract (must NOT change)

These hold for every `new` invocation and are asserted by tests:

- **I1 — Output validates.** `spec new --profile T` (any tier, any flag combination) produces text that `validate_document` accepts with zero findings. Enforced at runtime (decision 7) _and_ as a property test.
- **I2 — Never clobbers.** With a `PATH` that exists and no `--force`, `new` writes nothing and exits 2.
- **I3 — `--stdout` is pure.** With `--stdout`, no file is created or modified anywhere; output goes to stdout only.
- **I4 — Body is preserved verbatim.** Outside the rewritten frontmatter lines and the optional H1, the generated text is byte-identical to the selected bundled template. In particular `new` does **not** fill body `<…>` placeholders or delete guidance blockquotes — that is the author's job, which `lint` tracks.
- **I5 — Deterministic given its inputs.** `scaffold` is a pure function of `(template_text, opts, today, rng, existing_ids)`; identical inputs yield identical output. All nondeterminism is injected, never read internally.
- **I6 — No tracebacks.** Every bad input (missing `PATH`, bad `--id`, existing file, unreadable config, control-char flag value, non-regular target) yields a clean message and exit 2, never a stack trace.
- **I7 — `--json` on every outcome.** Success and every exit-2 failure emit a documented JSON object when `--json` is passed (see the [`--json` output contract](#--json-output-contract)); nothing else is printed to stdout in that mode.
- **I8 — Atomic write.** A completed `new` either leaves the destination as the full, validated scaffold or leaves it untouched — never a partial file (temp-file-plus-`os.replace`).

## Component 1 — CLI surface \& flag matrix

```text
project-standards spec new --profile {light|standard|full} [PATH]
    [--id SPEC-XXXX]
    [--title TITLE] [--owner OWNER] [--implementer IMPLEMENTER]
    [--stdout] [--force] [--json]
```

- `--profile` — **required**; selects which bundled template is the base.
- `PATH` — positional destination file. **Required unless `--stdout`.**
- `--id SPEC-XXXX` — supply the `spec_id` explicitly (still pattern- and collision-checked) instead of minting.
- `--title` / `--owner` / `--implementer` — fill the corresponding human field; omitted fields keep the template placeholder. Value grammar per decision 9.
- `--stdout` — print the scaffold to stdout, write nothing.
- `--force` — permit overwriting an existing **regular-file** `PATH`.
- `--json` — emit the machine-readable payload (Component 6) instead of human text, for success and failure alike.

The `spec` group is already early-dispatched from `src/project_standards/cli.py` (Spec #1); Spec #2 adds a `new` subparser inside `specs/cli.py`.

**Flag conflict matrix (frozen — not deferred).** Every combination has a defined outcome so the parser and test matrix need no invention:

| Combination | Outcome | Exit |
| --- | --- | --- |
| `PATH`, no `--stdout` | write to `PATH` (subject to refuse/force/safety) | 0 / 2 |
| `--stdout`, no `PATH` | print scaffold to stdout, write nothing | 0 |
| `PATH` **and** `--stdout` | usage error: "`--stdout` writes to stdout; do not also pass PATH" | 2 |
| neither `PATH` nor `--stdout` | usage error: "PATH is required unless --stdout" | 2 |
| `--force` with `--stdout` | usage error: "--force has no meaning with --stdout" | 2 |
| `--force` without a valid `PATH` | falls under the "neither" / "PATH+stdout" errors above | 2 |
| `--force` with a `PATH` that does not exist | allowed (no-op force); normal write | 0 |

## Component 2 — Module layout \& reuse

One new command module; the rest is reuse of the Spec #1 subpackage.

| Path | Responsibility | New? |
| --- | --- | --- |
| `src/project_standards/specs/commands/new.py` | `scaffold(template_text, opts, *, today, rng, existing_ids) -> str` — **pure** template-text → filled-text. Plus `mint_spec_id(rng, existing_ids, *, attempts) -> str` and `emit_scalar(value) -> str` (YAML-safe). No I/O. | **new** |
| `src/project_standards/specs/config.py` | Add `collect_existing_spec_ids(cfg) -> set[str]` — the **tolerant** discovery path (below). | edit |
| `src/project_standards/specs/cli.py` | `new` subparser + the I/O shell: validate the flag matrix, resolve `today`, seed `rng`, gather `existing_ids`, call `scaffold`, self-validate, then write-atomically-or-refuse / `--stdout`; render human or `--json`. | edit |
| `src/project_standards/specs/registry.py` | `TEMPLATES_DIR`, `TIER_FILES` — resolve the bundled template for the chosen tier. | reuse |
| `src/project_standards/specs/document.py`, `commands/validate.py` | `parse_document` + `validate_document` for the fail-closed self-check and for reading discovered specs' ids. | reuse |
| `tests/test_spec_new.py`, `tests/test_spec_new_cli.py` | Unit (pure `scaffold`/`mint`) + CLI/integration. | **new** |

The purity boundary is the design's backbone: **all nondeterminism is a parameter of `scaffold`** (`today`, `rng`, `existing_ids`), so unit tests need no clock mocking and no filesystem — they call `scaffold(text, opts, today=date(2026,7,4), rng=Random(0), existing_ids={…})` and assert on the returned string. The one impure edge is the `cli.py` shell.

## Component 3 — The fill operation (`scaffold`)

`scaffold` operates on the raw text of the tier's template, matching frontmatter lines by a `^key:` anchor and rewriting only these:

| Key | New value | Note |
| --- | --- | --- |
| `spec_id` | minted or `--id` | drops the trailing `# placeholder…` comment |
| `created` | `today` as `'YYYY-MM-DD'` | single-quoted, matching template style |
| `last_reviewed` | `today` as `'YYYY-MM-DD'` | a fresh draft's baseline; avoids leaving the literal `'YYYY-MM-DD'` |
| `title` | `emit_scalar(--title)` | only if `--title` given; else keep `'<Project / Feature Name>'` |
| `owner` | `emit_scalar(--owner)` | only if given; else keep `'<person or team>'` |
| `implementer` | `emit_scalar(--implementer)` | only if given; else keep `'<person, team, or coding agent>'` |

The **H1 line** (`` # `<Project / Feature Name>` — Specification (Standard) ``) is rewritten **only when `--title` is given** — the `— Specification (<Tier>)` suffix and formatting are preserved; only the back-ticked name is substituted. `profile` and the H1 tier word are **never** rewritten: selecting `spec-standard-template.md` already carries `profile: standard` and `(Standard)`.

Rewriting is confined to the frontmatter block (between the opening `---` and its closing `---`) plus that single H1 line, so decision 5's "body byte-identical" invariant (I4) is structural, not incidental.

**Value grammar & escaping (decision 9).** `--title`/`--owner`/`--implementer` values:

- are **rejected** (usage error, exit 2) if empty, or if they contain `\n`, `\r`, or any other C0/C1 control character — checked in the `cli.py` shell _before_ `scaffold` runs, so the failure is a clean argument error, not a downstream self-validation error;
- for `--title` only, are **additionally rejected** if they contain a backtick (it lands in the H1 code span — decision 9);
- are otherwise emitted into frontmatter via `emit_scalar`, a thin wrapper over PyYAML's scalar serialization, guaranteeing that apostrophes, colons, `#`, backticks, leading/trailing spaces, and non-ASCII produce valid, correctly-quoted YAML. This subsumes ad-hoc single-quoting and closes the "arbitrary value corrupts frontmatter" gap. (The H1 substitution is a plain text replacement inside the existing back-ticked span, which is why `--title` — and only `--title` — must exclude the backtick itself.)

## Component 4 — `spec_id` minting \& tolerant discovery

**Minting.**

```text
mint_spec_id(rng, existing_ids, *, attempts=1000):
    for _ in range(attempts):
        candidate = "SPEC-" + 4 chars drawn from [0-9A-Z] via rng
        if candidate not in existing_ids: return candidate
    raise SpecIdExhausted   # -> cli maps to exit 2 with "pass --id"
```

- The retry cap makes exhaustion a **bounded, deterministic failure** rather than an infinite loop — reachable only with a near-full corpus or a pathological injected RNG (a test can force it). The `cli.py` shell turns `SpecIdExhausted` into a clean exit-2 message advising `--id`.
- `--id` bypasses minting but is still validated against `^SPEC-[0-9A-Z]{4}$` (bad pattern → exit 2) **and** checked against `existing_ids` (collision → exit 2), so an explicit id cannot introduce a duplicate **against the parseable corpus**.
- The `~1.6M`-value space (36⁴) makes random collisions rare; the check makes them impossible within the discovered corpus. The RNG is injected (`random.Random`, seeded in the shell) so tests are deterministic.

**Tolerant discovery (resolves the `DiscoveryError` conflict).** `validate`/`lint` reuse `collect_spec_paths`, which _intentionally_ raises `DiscoveryError` (a subclass of `ConfigError`) when there is no `spec:` block, an empty include list, or a zero-match include — the "never a vacuous green run" guard. `new` needs the **opposite** empty-corpus behavior, so it does **not** call that helper directly. Instead a new sibling, `collect_existing_spec_ids(cfg)`:

- returns an **empty set** when discovery is empty — it catches `DiscoveryError` **narrowly** and treats it as "no existing ids";
- lets every **other** `ConfigError` (unreadable file, unparseable YAML) **propagate** → exit 2, so `new` still fails closed on a broken config, exactly as decision 2/I6 require;
- parses each discovered spec and collects `frontmatter["spec_id"]`; a spec that fails to parse is **skipped** (a malformed neighbor must not block scaffolding). Consequently duplicate detection is best-effort **over successfully-parsed specs** — a spec so malformed its id cannot be read cannot be collided against. This is an accepted, documented limitation, not an absolute guarantee.

## Component 5 — Write model \& safety

The `cli.py` shell, after `scaffold` returns and self-validation passes:

- **`--stdout`:** write the text (or the JSON payload) to stdout, exit 0. No path is opened for writing (I3).
- **`PATH` target-type check (before any write):** if `PATH` exists and is **not a regular file** (directory, FIFO, device, socket) → refuse, exit 2. If `PATH` **is a symlink** (to anything, including a nonexistent target) → refuse, exit 2 — `new` does not follow symlinks for writes, even with `--force`. This prevents a forced overwrite from redirecting through a symlink to an outside-repo file.
- **Parent-chain symlink check (before any write):** if **any existing ancestor directory** of `PATH` is a symlink → refuse, exit 2. Because `Path.exists()`/`is_file()` follow symlinks, refusing only a symlinked _final_ component would still let a symlinked _parent_ (`docs/link/spec.md`) redirect the write outside the apparent tree. `new` walks the existing prefix of the destination's parent chain and rejects a symlink anywhere in it. (Implementation note: check the ancestors that already exist; components `new` will create cannot yet be symlinks.)
- **`PATH` is an existing regular file, no `--force`:** write nothing, `refusing to overwrite existing file: <PATH> (use --force)`, exit 2 (I2).
- **`PATH` does not exist (or exists as a regular file with `--force`):** create missing parent directories with `Path.mkdir(parents=True, exist_ok=True)`; if a parent path component exists but is not a directory, that `mkdir` fails and is reported as exit 2 (no traceback). Then write **atomically**: write to a temp file in the destination's directory and `os.replace(tmp, PATH)` (atomic same-filesystem rename; overwrites in place under `--force`). **Mode handling mirrors `adopt/engine._atomic_write`** — on an overwrite the temp file copies the existing target's mode; for a new file it is `chmod`'d to a umask-respecting `0o666 & ~umask` so the result is not left at `mkstemp`'s owner-only `0600`. On any write error the temp file is removed and nothing replaces `PATH` (I8).

Writing is last: discovery, minting, `scaffold`, self-validation, and both target-type and parent-chain checks all complete before any byte is committed. The guarantee is scoped to the **destination file** (I8): a failure never leaves a partial or corrupt spec at `PATH`. Parent directories auto-created by `mkdir(parents=True)` are the one exception — an empty directory created just before a later write failure may remain (a benign artifact, not a corrupted spec). The spec deliberately does **not** promise directory rollback; narrowing the guarantee to the destination file is more honest than best-effort `rmdir` cleanup that could race another process.

## Component 6 — Error handling \& exit codes

| Situation | Behavior | Exit |
| --- | --- | --- |
| Wrote file, or printed with `--stdout` | success | 0 |
| `PATH` exists (regular file), no `--force` | refuse, name the file | 2 |
| `PATH` exists but is a dir/symlink/special file | refuse (target-type), even with `--force` | 2 |
| A parent directory in `PATH` is a symlink | refuse (parent-chain), even with `--force` | 2 |
| Any flag-matrix conflict (Component 1) | usage error (`flag_conflict`) | 2 |
| Argparse-level error (missing/invalid `--profile`, unknown flag) | JSON-aware parser raises → `usage` | 2 |
| `--id` fails `^SPEC-[0-9A-Z]{4}$`, or collides | validation error, no write | 2 |
| Empty / control-char `--title`/`--owner`/`--implementer` | usage error, no write | 2 |
| `spec_id` mint exhausted after the attempt cap | error advising `--id`, no write | 2 |
| Config present but unreadable / unparseable | `ConfigError` message, no write | 2 |
| Parent path component is a non-directory | `mkdir` failure message, no write | 2 |
| **Generated text fails `validate_document`** | **fail-closed: no write, report finding(s)** | 2 |

There is no exit-1 case: `new` either produces a conformant scaffold (0) or refuses (2). Exit 1 is reserved by the tooling for "findings against a consumer's spec" (`validate`/`lint`), which `new` does not do. No path yields a traceback (I6).

### `--json` output contract

With `--json`, stdout carries exactly one JSON object and nothing else (I7). Fields are frozen here so downstream agents/CI can depend on them.

**Success — file write:**

```json
{
  "ok": true,
  "spec_id": "SPEC-7F3Q",
  "profile": "standard",
  "path": "docs/specs/checkout.md",
  "written": true,
  "overwritten": false
}
```

**Success — `--stdout`:** `path` is `null`, `written` is `false`, and the scaffold text rides along so a caller need not re-read it:

```json
{ "ok": true, "spec_id": "SPEC-7F3Q", "profile": "light", "path": null, "written": false, "content": "---\nspec_id: SPEC-7F3Q\n…" }
```

**Failure (any exit-2 case):**

```json
{ "ok": false, "error": "refusing to overwrite existing file: docs/specs/checkout.md (use --force)", "code": "exists" }
```

`code` is a stable, low-cardinality slug (`usage`, `exists`, `not_regular_file`, `symlinked_parent`, `flag_conflict`, `bad_id`, `id_collision`, `bad_field_value`, `id_exhausted`, `config_error`, `mkdir_failed`, `write_failed`, `self_validation_failed`). `usage` covers **argparse-level** failures (missing/invalid `--profile`, unknown flag, missing required arg): the parser is made JSON-aware (a subclass whose `error()` raises rather than calling `sys.exit`) so even these emit the `--json` object and never leak argparse's stderr or a `SystemExit` — a raw argparse exit would violate I6/I7. For `self_validation_failed`, a `findings` array of the `validate` `Finding` records (the same `dataclasses.asdict` shape the existing commands emit) is included so automation sees exactly what failed.

## Component 7 — Testing

- **Unit — pure `scaffold`** (`tests/test_spec_new.py`): per tier, assert exact rewritten lines; assert omitted flags leave the template `'<…>'` verbatim; assert the `spec_id` comment is dropped; assert the H1 is rewritten **only** with `--title`; assert body bytes outside the frontmatter/H1 equal the template (I4).
- **Unit — `emit_scalar` / value grammar:** apostrophe, colon, `#`, backtick, leading/trailing space, non-ASCII → valid YAML that round-trips; newline, carriage return, a C0 control char, and empty string → rejected (exit 2 at the CLI); a **backtick in `--title`** → rejected (exit 2), while a backtick in `--owner`/`--implementer` is accepted (frontmatter-only, YAML-safe).
- **Invariant — output validates** (I1): parametrized over all three tiers × {no flags, all flags}, assert `validate_document(parse_document(scaffold(...)))` is empty.
- **Minting:** seed `existing_ids` with the RNG's first candidate, assert the retry yields a different, non-colliding id; assert `--id` collision → error; assert bad `--id` pattern → error; assert exhaustion (attempts=all-colliding via a stub) → `SpecIdExhausted` → exit 2.
- **Tolerant discovery:** no config, `spec:` with empty include, zero-match include → empty `existing_ids` (no error); malformed/unreadable config → propagates to exit 2; one malformed discovered spec among valid ones → skipped, others still collide-checked.
- **CLI / integration** (`tests/test_spec_new_cli.py`): the full flag-conflict matrix (Component 1) each to exit 2; refuse-if-exists (I2); `--force` overwrites a regular file; existing directory / symlink / broken-symlink target → refused even with `--force`; a **symlinked parent directory** in `PATH` → refused even with `--force`; parent path that is a file → exit 2; parent auto-creation on a fresh nested path; `--stdout` creates no file (I3), asserted by comparing the target dir before/after; atomic write leaves no temp file behind; every exit code per Component 6.
- **`--json`:** success (file + `--stdout`), overwrite refusal, id collision, self-validation failure → assert the documented payload shape and `code` slug; assert nothing else is on stdout.
- **Dogfood:** `spec new --profile full --stdout` piped through `validate` is clean (end-to-end I1).
- **Coverage:** the suite keeps branch coverage ≥ the repo `fail_under` and the full gate green (`ruff format --check`, `ruff check`, `basedpyright`, `pytest`, `coverage report`, `pip-audit`).

## Acceptance criteria

- `project-standards spec new --profile {light,standard,full} PATH` writes a spec that `project-standards spec validate PATH` accepts with zero findings, for every tier.
- `--stdout`, `--force`, `--id`, `--title`, `--owner`, `--implementer`, `--json` behave per Components 1/3/5/6; the flag-conflict matrix, refuse-if-exists, target-type refusal, and all exit codes hold.
- `new` works in a repo with no existing specs and no `spec:` config, and fails closed (exit 2) on an unreadable/unparseable config.
- Writes are atomic (destination file never partial); symlink targets, non-regular targets, and symlinked parent directories are refused; control-char/empty human-field values are rejected, and backticks are rejected in `--title`.
- Every command outcome supports `--json` with the documented payload.
- Invariants I1–I8 are covered by tests; the full gate is green.

## Non-goals

- **`upgrade`** (additive tier promotion) — Spec #3.
- **`status`** rollup and the **semantic-review contract** — deferred per README §5.
- **Interactive prompting** — flags only; agent/CI-safe.
- **Filling body `<…>` placeholders or deleting guidance blockquotes** — the author's job; `lint` reports them.
- **Registering `project-spec` as a standard / writing README §6 Adoption** — separate adoption work, unchanged by this spec.
- **A starter `spec:` config writer** — `adopt`-plane work, not `new`.
- **Cross-process/TOCTOU write locking** — the refuse-if-exists check and the atomic rename are not a lock against a concurrent writer racing between them; acceptable for a single-user local/CI CLI, called out so it is a known boundary, not an oversight.

## Versioning \& docs impact

- Adding the `new` subcommand is an **additive, minor** change to the package's consumer contract — a new command surface, no change to existing `validate`/`lint`/`extract`/`next` behavior. Per `meta/versioning.md` this rides a minor bump.
- README §5 already lists `new` as a _core_ capability **and** already promises `--json` on every command, so no standard-text change is required when it ships; its status simply moves from "specified" to "implemented," and adding `--json` _conforms_ to the existing contract rather than extending it. The CHANGELOG entry already owed (see `TODO.md`) should note `new`'s arrival alongside the pending release.
- `project-spec` remains an **unregistered, in-development** standard (excluded from validation/adopt); shipping `new` does not register it.

## Open implementation questions (for the plan, not blockers)

- **`emit_scalar` quoting style:** whether to force single-quoted scalars (matching the template's `'…'` style) or let PyYAML choose the minimal safe style. Leaning force-single-quoted for visual consistency with the untouched placeholder lines; either passes `validate`.
- **Message spellings:** the exact wording of the refuse/collision/mint-exhausted messages is chosen during implementation; only the exit codes, `--json` `code` slugs, and behavior are frozen here.
- **`last_reviewed` on a brand-new draft:** set to `today` (this design) vs. leave as a placeholder. Chosen `today` to avoid emitting the literal `'YYYY-MM-DD'`; revisit if the standard later says an unreviewed draft should carry no review date.
