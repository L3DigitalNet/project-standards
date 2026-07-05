# Design: `project-standards spec new` — Spec #2 (guarded-generative scaffold)

**Date:** 2026-07-04 **Status:** approved (brainstorming complete; awaiting plan) **Author:** session 2026-07-04

## Table of Contents

- [Design: `project-standards spec new` — Spec #2 (guarded-generative scaffold)](#design-project-standards-spec-new--spec-2-guarded-generative-scaffold)
  - [Table of Contents](#table-of-contents)
  - [Problem / Goal](#problem--goal)
  - [Scope decomposition (the write seam splits again)](#scope-decomposition-the-write-seam-splits-again)
  - [Decisions (locked during brainstorming)](#decisions-locked-during-brainstorming)
  - [Invariants — the consumer contract (must NOT change)](#invariants--the-consumer-contract-must-not-change)
  - [Component 1 — CLI surface](#component-1--cli-surface)
  - [Component 2 — Module layout \& reuse](#component-2--module-layout--reuse)
  - [Component 3 — The fill operation (`scaffold`)](#component-3--the-fill-operation-scaffold)
  - [Component 4 — `spec_id` minting](#component-4--spec_id-minting)
  - [Component 5 — Write model \& safety](#component-5--write-model--safety)
  - [Component 6 — Error handling \& exit codes](#component-6--error-handling--exit-codes)
  - [Component 7 — Testing](#component-7--testing)
  - [Acceptance criteria](#acceptance-criteria)
  - [Non-goals](#non-goals)
  - [Versioning \& docs impact](#versioning--docs-impact)
  - [Open implementation questions (for the plan, not blockers)](#open-implementation-questions-for-the-plan-not-blockers)

## Problem / Goal

Spec #1 shipped the read-only half of the `project-spec` tooling: a shared registry core parsed from the bundled templates, plus `validate`, `lint`, `extract`, and `next`. A consumer can now mechanically check a spec they have already written — but nothing helps them _start_ one. Today "create a spec" means hand-copying a template, hand-minting a `spec_id` that matches `^SPEC-[0-9A-Z]{4}$`, and hand-editing frontmatter — every step a chance to produce a spec that `validate` will immediately reject.

The goal of Spec #2 is the first **guarded-generative** command, `new`: scaffold a conformant spec from a chosen profile so that the very first thing the tool writes already passes `validate`. It delivers guarantees **G1** (a conformant starting point) and **G7** (deterministic tooling) from the standard's Features list. Like all the tooling it must be agent/CI-safe: no prompts, deterministic exit codes, and — because it now _writes files_ — a safety model that never destroys existing work.

The command is specified in prose today in [README §5](../../../standards/project-spec/README.md) under **Author — guarded generative**:

> **`new`** _(core)_ — scaffold a spec from a chosen profile: copy the template, mint a fresh `spec_id`, and fill frontmatter (owner, implementer, created, profile) and title, resolving the sentinel. → **G1, G7**

## Scope decomposition (the write seam splits again)

Spec #1 split the v1-core set along a read/write seam and deferred both generative authors to "Spec #2." Brainstorming refined that: `new` and `upgrade` sit on **opposite sides of a mutation-risk seam**, so they split into two specs of their own.

- **Spec #2 (this doc)** — **`new`** only. Writes a **brand-new file**; its worst case is refusing to clobber an existing one. It never touches prose a human has written, so the "never rewrites existing prose" guarantee holds _by construction_.
- **Spec #3 (future)** — **`upgrade`** (additive tier promotion, Light → Standard → Full). It must splice canonical sections into a document an author has already filled — an in-place mutation whose whole difficulty _is_ preserving surrounding prose. That is a materially higher risk profile and earns its own spec, built on the `new` scaffolding proven here.

`status` (a reporting rollup) and the **semantic-review contract** (a standard-defined checklist, not a binary command) remain deferred exactly as README §5 marks them.

## Decisions (locked during brainstorming)

1. **Scope = `new` only.** `upgrade` is Spec #3 (mutation-risk seam, above).
2. **Write model = explicit `PATH`, refuse-if-exists, `--stdout` preview.** `new … PATH` writes the file; refuses (exit 2) if `PATH` exists unless `--force`; `--stdout` prints to stdout and never touches disk. This is the safety spine of a file-writing command: re-running `new` can never silently overwrite an in-progress spec.
3. **`spec_id` = random, collision-checked, `--id` override.** Mint a random 4-char `[0-9A-Z]` id; scan the specs that Spec #1's `spec:` discovery finds and retry on collision; `--id SPEC-AB12` overrides for determinism. An empty corpus (no config, no specs) is **not** an error here — unlike `validate`, `new` must work in a repo that has no specs yet.
4. **Human fields via optional flags, template placeholder as fallback.** `--title`/`--owner`/`--implementer` fill their fields when passed; an omitted field keeps the template's own `'<…>'` placeholder verbatim. Machine fields (`spec_id`, `created`, `last_reviewed`) are always filled; `status` stays `draft`; `profile` is set by _selecting_ the tier's template file, not by rewriting a line.
5. **Fill mechanism = surgical line-rewrite.** Rewrite only the specific frontmatter lines that change (and the H1 title line iff `--title` is given); copy the rest of the template byte-for-byte. Rejected: parse-to-`SpecDocument`-and-re-serialize (the parser is lossy — drops comments, normalizes formatting), and named-placeholder templating (would mutate the canonical templates, breaking Spec #1's byte-identical dogfood guard, and add a runtime dependency).
6. **`--profile` is required.** No silent default; choosing a tier is a deliberate authoring act.
7. **`new` self-validates its output (fail-closed).** Before writing, `new` parses and validates the generated text in memory; if it is not `validate`-clean it refuses to write and reports the finding. This makes "`new` always emits a validate-clean scaffold" a runtime invariant, not just a test-time hope.

## Invariants — the consumer contract (must NOT change)

These hold for every `new` invocation and are asserted by tests:

- **I1 — Output validates.** `spec new --profile T` (any tier, any flag combination) produces text that `validate_document` accepts with zero findings. Enforced at runtime (decision 7) _and_ as a property test.
- **I2 — Never clobbers.** With a `PATH` that exists and no `--force`, `new` writes nothing and exits 2.
- **I3 — `--stdout` is pure.** With `--stdout`, no file is created or modified anywhere; output goes to stdout only.
- **I4 — Body is preserved verbatim.** Outside the rewritten frontmatter lines and the optional H1, the generated text is byte-identical to the selected bundled template. In particular `new` does **not** fill body `<…>` placeholders or delete guidance blockquotes — that is the author's job, which `lint` tracks.
- **I5 — Deterministic given its inputs.** `scaffold` is a pure function of `(template_text, opts, today, rng, existing_ids)`; identical inputs yield identical output. All nondeterminism is injected, never read internally.
- **I6 — No tracebacks.** Every bad input (missing `PATH`, bad `--id`, existing file, unreadable config) yields a clean message and exit 2, never a stack trace.

## Component 1 — CLI surface

```text
project-standards spec new --profile {light|standard|full} [PATH]
    [--id SPEC-XXXX]
    [--title TITLE] [--owner OWNER] [--implementer IMPLEMENTER]
    [--stdout] [--force]
```

- `--profile` — **required**; selects which bundled template is the base.
- `PATH` — positional; the destination file. Required **unless** `--stdout` is given. Supplying both `PATH` and `--stdout` is a contradictory instruction; how it is resolved (reject vs. prefer `--stdout`) is deferred to the plan — see open questions.
- `--id SPEC-XXXX` — supply the `spec_id` explicitly (still pattern- and collision-checked) instead of minting.
- `--title` / `--owner` / `--implementer` — fill the corresponding human field; omitted fields keep the template placeholder.
- `--stdout` — print the scaffold to stdout, write nothing.
- `--force` — permit overwriting an existing `PATH`.

The `spec` group is already early-dispatched from `src/project_standards/cli.py` (Spec #1); Spec #2 adds a `new` subparser inside `specs/cli.py`.

## Component 2 — Module layout \& reuse

One new command module; the rest is reuse of the Spec #1 subpackage.

| Path | Responsibility | New? |
| --- | --- | --- |
| `src/project_standards/specs/commands/new.py` | `scaffold(template_text, opts, *, today, rng, existing_ids) -> str` — **pure** template-text → filled-text. Plus `mint_spec_id(rng, existing_ids) -> str`. No I/O. | **new** |
| `src/project_standards/specs/cli.py` | `new` subparser + the I/O shell: resolve `today`, seed `rng`, run discovery for `existing_ids`, call `scaffold`, self-validate, then write-or-refuse / `--stdout`. | edit |
| `src/project_standards/specs/registry.py` | `TEMPLATES_DIR`, `TIER_FILES` — resolve the bundled template for the chosen tier. | reuse |
| `src/project_standards/specs/config.py` | `load_spec_config` + discovery — enumerate existing specs to collect their `spec_id`s (empty result tolerated). | reuse |
| `src/project_standards/specs/document.py`, `commands/validate.py` | `parse_document` + `validate_document` for the fail-closed self-check. | reuse |
| `tests/test_spec_new.py`, `tests/test_spec_new_cli.py` | Unit (pure `scaffold`) + CLI/integration. | **new** |

The purity boundary is the design's backbone: **all nondeterminism is a parameter of `scaffold`** (`today`, `rng`, `existing_ids`), so unit tests need no clock mocking and no filesystem — they call `scaffold(text, opts, today=date(2026,7,4), rng=Random(0), existing_ids={…})` and assert on the returned string. The one impure edge is the `cli.py` shell.

## Component 3 — The fill operation (`scaffold`)

`scaffold` operates on the raw text of the tier's template, matching frontmatter lines by a `^key:` anchor and rewriting only these:

| Key | New value | Note |
| --- | --- | --- |
| `spec_id` | minted or `--id` | drops the trailing `# placeholder…` comment |
| `created` | `today` as `'YYYY-MM-DD'` | single-quoted, matching template style |
| `last_reviewed` | `today` as `'YYYY-MM-DD'` | a fresh draft's baseline; avoids leaving the literal `'YYYY-MM-DD'` |
| `title` | `--title` value | only if `--title` given; else keep `'<Project / Feature Name>'` |
| `owner` | `--owner` value | only if given; else keep `'<person or team>'` |
| `implementer` | `--implementer` value | only if given; else keep `'<person, team, or coding agent>'` |

The **H1 line** (`` # `<Project / Feature Name>` — Specification (Standard) ``) is rewritten **only when `--title` is given** — the `— Specification (<Tier>)` suffix and formatting are preserved; only the back-ticked name is substituted. `profile` and the H1 tier word are **never** rewritten: selecting `spec-standard-template.md` already carries `profile: standard` and `(Standard)`.

Rewriting is confined to the frontmatter block (between the opening `---` and its closing `---`) plus that single H1 line, so decision 5's "body byte-identical" invariant (I4) is structural, not incidental. Values supplied via flags are emitted single-quoted with YAML-safe escaping so a title containing `'` or `:` cannot corrupt the frontmatter.

## Component 4 — `spec_id` minting

```text
mint_spec_id(rng, existing_ids):
    loop:
        candidate = "SPEC-" + 4 chars drawn from [0-9A-Z] via rng
        if candidate not in existing_ids: return candidate
```

- `existing_ids` is built by the `cli.py` shell: run `spec:` discovery (`load_spec_config` + `collect_spec_paths`), `parse_document` each hit, collect `frontmatter["spec_id"]`. Parse failures on individual existing specs are skipped (a malformed neighbor must not block scaffolding a new one).
- **Empty corpus is fine.** If discovery finds nothing (no `spec:` block, or it matches no files), `existing_ids` is empty and minting proceeds — `new` must not raise the `DiscoveryError` that `validate` raises, because a repo legitimately has zero specs before the first `new`.
- `--id` bypasses minting but is still validated against `^SPEC-[0-9A-Z]{4}$` (bad pattern → exit 2) **and** checked against `existing_ids` (collision → exit 2), so an explicit id can never introduce a duplicate.
- The `~1.6M`-value space (36⁴) makes collisions rare; the check makes them impossible within the discovered corpus. The RNG is injected (`random.Random`, seeded in the shell) so tests are deterministic.

## Component 5 — Write model \& safety

The `cli.py` shell, after `scaffold` returns and self-validation passes:

- **`--stdout`:** write the text to stdout, exit 0. No path is opened for writing (I3).
- **`PATH` given, does not exist:** create parent dirs as needed, write, exit 0.
- **`PATH` given, exists, no `--force`:** write nothing, print `refusing to overwrite existing file: <PATH> (use --force)`, exit 2 (I2).
- **`PATH` given, exists, `--force`:** overwrite, exit 0.

Writing is last: discovery, minting, `scaffold`, and self-validation all complete before any byte hits disk, so a failure in any of them leaves the filesystem untouched.

## Component 6 — Error handling \& exit codes

| Situation | Behavior | Exit |
| --- | --- | --- |
| Wrote file, or printed with `--stdout` | success | 0 |
| `PATH` exists, no `--force` | refuse, name the file | 2 |
| Missing `PATH` and no `--stdout` | usage error | 2 |
| Bad `--profile` value | argparse choice error | 2 |
| `--id` fails `^SPEC-[0-9A-Z]{4}$`, or collides | validation error, no write | 2 |
| Config present but unreadable / unparseable | `ConfigError` message, no write | 2 |
| **Generated text fails `validate_document`** | **fail-closed: no write, report finding(s)** | 2 |

There is no exit-1 case: `new` either produces a conformant scaffold (0) or refuses (2). Exit 1 is reserved by the tooling for "findings against a consumer's spec" (`validate`/`lint`), which `new` does not do. No path yields a traceback (I6).

## Component 7 — Testing

- **Unit — pure `scaffold`** (`tests/test_spec_new.py`): per tier, assert exact rewritten lines; assert omitted flags leave the template `'<…>'` verbatim; assert the `spec_id` comment is dropped; assert the H1 is rewritten **only** with `--title`; assert body bytes outside the frontmatter/H1 equal the template (I4); assert YAML-escaping of a title containing `'`/`:`.
- **Invariant — output validates** (I1): parametrized over all three tiers × {no flags, all flags}, assert `validate_document(parse_document(scaffold(...)))` is empty.
- **Minting:** seed `existing_ids` with the RNG's first candidate, assert the retry yields a different, non-colliding id; assert `--id` collision → error; assert bad `--id` pattern → error.
- **Empty corpus:** discovery finds no specs → minting still succeeds (no `DiscoveryError`).
- **CLI / integration** (`tests/test_spec_new_cli.py`): refuse-if-exists (I2); `--force` overwrites; `--stdout` creates no file (I3), checked by asserting the target dir is unchanged; exit codes per Component 6; parent-dir creation.
- **Dogfood:** `spec new --profile full --stdout` piped through `validate` is clean (end-to-end I1).
- **Coverage:** the suite keeps branch coverage ≥ the repo `fail_under` and the full gate green (`ruff format --check`, `ruff check`, `basedpyright`, `pytest`, `coverage report`, `pip-audit`).

## Acceptance criteria

- `project-standards spec new --profile {light,standard,full} PATH` writes a spec that `project-standards spec validate PATH` accepts with zero findings, for every tier.
- `--stdout`, `--force`, `--id`, `--title`, `--owner`, `--implementer` behave per Components 1/3/5; refuse-if-exists and all exit codes per Component 6 hold.
- `new` works in a repo with no existing specs and no `spec:` config.
- Invariants I1–I6 are covered by tests; the full gate is green.

## Non-goals

- **`upgrade`** (additive tier promotion) — Spec #3.
- **`status`** rollup and the **semantic-review contract** — deferred per README §5.
- **Interactive prompting** — flags only; agent/CI-safe.
- **Filling body `<…>` placeholders or deleting guidance blockquotes** — the author's job; `lint` reports them.
- **Registering `project-spec` as a standard / writing README §6 Adoption** — separate adoption work, unchanged by this spec.
- **A starter `spec:` config writer** — `adopt`-plane work, not `new`.

## Versioning \& docs impact

- Adding the `new` subcommand is an **additive, minor** change to the package's consumer contract — a new command surface, no change to existing `validate`/`lint`/`extract`/`next` behavior. Per `meta/versioning.md` this rides a minor bump.
- README §5 already lists `new` as a _core_ capability, so no standard-text change is required when it ships; its status simply moves from "specified" to "implemented." The CHANGELOG entry already owed (see `TODO.md`) should note `new`'s arrival alongside the pending release.
- `project-spec` remains an **unregistered, in-development** standard (excluded from validation/adopt); shipping `new` does not register it.

## Open implementation questions (for the plan, not blockers)

- **`PATH` + `--stdout` together:** silently prefer `--stdout` (write nothing) vs. reject as a usage error (exit 2). Leaning reject — an explicit `PATH` with `--stdout` is a contradictory instruction and a clean error is less surprising than a silently-ignored path.
- **Parent-dir creation:** auto-`mkdir -p` the destination's parents vs. require the directory to exist. Leaning auto-create (agent ergonomics), but it is a small surprise surface worth confirming.
- **`SL-*` / message spellings:** the exact wording of the refuse/collision messages is chosen during implementation; only the exit codes and behavior are frozen here.
- **`last_reviewed` on a brand-new draft:** set to `today` (this design) vs. leave as a placeholder. Chosen `today` to avoid emitting the literal `'YYYY-MM-DD'`; revisit if the standard later says an unreviewed draft should carry no review date.
