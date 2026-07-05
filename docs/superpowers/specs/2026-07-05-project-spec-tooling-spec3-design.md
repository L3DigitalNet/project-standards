# Design: `project-standards spec upgrade` — Spec #3 (additive tier promotion)

**Date:** 2026-07-05 **Status:** in codex spec-review (round 1 → revised for SA-001…006; upgradeability precheck added) **Author:** session 2026-07-05

## Table of Contents

- [Design: `project-standards spec upgrade` — Spec #3 (additive tier promotion)](#design-project-standards-spec-upgrade--spec-3-additive-tier-promotion)
  - [Table of Contents](#table-of-contents)
  - [Problem / Goal](#problem--goal)
  - [Scope — the last v1-core tool, the far side of the mutation seam](#scope--the-last-v1-core-tool-the-far-side-of-the-mutation-seam)
  - [Decisions (locked during brainstorming)](#decisions-locked-during-brainstorming)
  - [The load-bearing property — enforced, not assumed](#the-load-bearing-property--enforced-not-assumed)
  - [Invariants — the consumer contract (must NOT change)](#invariants--the-consumer-contract-must-not-change)
  - [Component 1 — CLI surface \& flag matrix](#component-1--cli-surface--flag-matrix)
  - [Component 2 — Tier rules \& direction](#component-2--tier-rules--direction)
  - [Component 3 — Execution flow (the doubly-fail-closed pipeline)](#component-3--execution-flow-the-doubly-fail-closed-pipeline)
  - [Component 4 — The splice (`upgrade_text`)](#component-4--the-splice-upgrade_text)
    - [Unit-ownership model](#unit-ownership-model)
    - [Three pure transformation passes](#three-pure-transformation-passes)
  - [Component 5 — Module layout \& reuse](#component-5--module-layout--reuse)
  - [Component 6 — Write model \& safety](#component-6--write-model--safety)
  - [Component 7 — Error handling \& exit codes](#component-7--error-handling--exit-codes)
    - [`--json` output contract](#--json-output-contract)
  - [Component 8 — Testing](#component-8--testing)
  - [Acceptance criteria](#acceptance-criteria)
  - [Non-goals](#non-goals)
  - [Versioning \& docs impact](#versioning--docs-impact)
  - [Open implementation questions (for the plan, not blockers)](#open-implementation-questions-for-the-plan-not-blockers)

## Problem / Goal

Spec #1 shipped the read-only tooling (`validate`, `lint`, `extract`, `next`); Spec #2 shipped `new`, the guarded-generative scaffold. Both authoring aids meet an author at the *start* of a spec. Neither helps a spec that has **outgrown its tier** — a Light spec for a script that has become a service, a Standard spec that now spans multiple services and durable data. Today "upgrade the profile" means hand-copying a higher-tier template, hand-transplanting every filled section into it, hand-reconciling the omission notes, and hoping the result still `validate`s. Every step risks corrupting author work or producing a non-conformant spec.

The goal of Spec #3 is `upgrade`: **additive tier promotion (Light → Standard → Full)** that mechanizes exactly the procedure the standard already documents in prose. The Light template's Appendix D ("Upgrading This Spec") states the contract:

> Because numbering is stable across profiles, upgrading is **additive**: insert the missing sections at their canonical numbers, set `profile:` in the frontmatter, and no existing section or ID reference has to change.

`upgrade` delivers guarantees **G1** (a conformant document) and **G2** (stable numbering / additive structure) from the standard's Features list, and completes the **v1-core** tool surface (README §5 lists `upgrade` as *core*, alongside the already-shipped `new`). Like every command it is agent/CI-safe: no prompts, deterministic exit codes, machine-readable `--json`.

The command is specified in prose today in [README §5](../../../standards/project-spec/README.md) under **Author — guarded generative**:

> **`upgrade`** _(core)_ — additive tier promotion (Light → Standard → Full): insert the missing canonical sections and appendices at their stable numbers, drop the now-satisfied omission notes, and set `profile:`. Purely additive — no renumbering, no reference rewrites. → **G1, G2**

## Scope — the last v1-core tool, the far side of the mutation seam

Spec #2 split the two generative authors along a **mutation-risk seam**: `new` writes a brand-new file (its worst case is refusing to clobber), while `upgrade` must splice canonical structure into a document an author has already filled — an in-place mutation whose whole difficulty *is* preserving surrounding prose. Spec #2 built and proved the write-safety machinery (atomic write, symlink/parent refusal, mode preservation, fail-closed self-validation); Spec #3 reuses that machinery and adds the one thing it lacks: a splice that edits real author content without touching a byte of it.

`status` (a reporting rollup) and the **semantic-review contract** (a standard-defined checklist, not a binary command) remain deferred exactly as README §5 marks them.

## Decisions (locked during brainstorming)

1. **Write model = preview-first; explicit `-i`/`-o`.** A bare `upgrade SRC --to T` prints the upgraded document to stdout and writes nothing (a dry run). `-i`/`--in-place` atomically rewrites `SRC`; `-o OUT` writes a new file (refuse-if-exists unless `--force`). Mutating author work is never the silent default; the common intent is one flag away.
2. **Fidelity = template-faithful.** The output matches the target tier's *full* shape: missing top-level sections **and** subsections (§7.2–§7.4, §17.2–§17.3, §8.4…), the unnumbered `## References` section, reconciled tier-variant prose (§7/§17 reduction-note intros, Appendix A footer, Appendix D title, H1 suffix), and reconciled omission notes. This is exactly what Appendix D's table lists as what an upgrade "Adds." A minimal "top-level sections only" upgrade was rejected: it would pass `validate` (subsection gaps are not gap-checked — see [the load-bearing property](#the-load-bearing-property--enforced-not-assumed)) yet leave the stale `> At the Light profile…` intros in a Standard spec — wrong prose the tool would have vouched for.
3. **Input guard = `validate`-clean *and* upgradeable-shape (two-stage, fail-closed).** `upgrade` first requires the source to be `validate`-clean (zero findings; otherwise refuse, exit 2, `source_invalid`, print findings). It then runs an **upgradeability precheck** (decision 10) that `validate` does *not* subsume — because `validate` only gap-checks top-level numbered sections, a `validate`-clean spec can still carry author prose in an inter-section gap, an edited Appendix A/B/D, or a non-canonical subsection shape (§7.3 without §7.2). The splice cannot safely absorb those, so the precheck refuses them (exit 2, `source_not_upgradeable`, naming the deviation). Lenient/best-effort was rejected (it lets a drifted source mis-splice); `validate`-alone was rejected once Codex spec-review (round 1, SA-001/002/003) empirically showed `validate` does not enforce the splice's structural assumptions.
4. **Mechanism = source-as-spine, unit splice.** Keep the *source* text as the spine so author bytes are preserved **by construction** (never re-serialized); slice each missing unit's pristine body from the *target-tier template* and splice it at its canonical position; reconcile the tier-variant prose. Target-as-spine transplant (risks corrupting author content on extract/re-inject) and parse-to-model-and-re-serialize (the parser is lossy — drops comments, normalizes formatting) were rejected. This is the direct analog of `new`'s "surgical line-rewrite."
5. **`--to` is required; `light` is not a valid target.** Choosing a tier is a deliberate authoring act (mirrors `new`'s required `--profile`). Nothing upgrades *to* Light.
6. **Additive-only.** Same-tier and downgrade (Standard→Light, Full→Standard) are refused (exit 2, `not_upgradeable`). A direct multi-step jump (Light→Full) is allowed — it is simply "target unit-set minus source unit-set."
7. **`upgrade` self-validates its output (fail-closed).** Before delivering, it parses and validates the spliced text in memory; if it is not `validate`-clean it refuses and reports the finding(s), mapped to `self_validation_failed`. Inherited directly from `new`'s I1.
8. **`--json` is mandatory (universal tooling contract).** Every outcome — success and every exit-2 failure — emits a documented JSON object under `--json` (README §5).
9. **The splice never needs an RNG or a clock.** Unlike `new`, `upgrade` preserves the existing `spec_id`, `created`, and `last_reviewed`; it mints nothing. All pure passes are functions of `(source_text, target_template_text, target_tier)` only.
10. **Upgradeability precheck = source scaffolding must be canonical for its tier.** Beyond `validate`, `upgrade` checks that everything *outside* the source's authored section/subsection **bodies** — the inter-section and inter-subsection gaps (dividers, blank lines, omission/reduction notes), Appendices A/B/D, and the subsection *membership* of every section — is byte-identical to what the source's declared-tier bundled template has there. A source that deviates (author prose in a gap, an edited Appendix A/B/D, an extra or non-canonical subsection) is **refused** (`source_not_upgradeable`) with the deviation named, rather than risking silent author-content loss or a mis-ordered splice. This is deliberately conservative — it favors a clear refusal over a clever merge — and it is what makes decision 4's "gaps are pure filler" property *true by precondition* instead of assumed. `upgrade` does not attempt to *preserve* non-canonical scaffolding; the author restores canonical structure (or re-runs `new` and moves content) first.

## The load-bearing property — enforced, not assumed

Component 4's splice rests on one structural property:

> **Author content lives only *inside* canonical sections — never in the inter-section/inter-subsection gaps.** Between two consecutive headings, the document holds only *filler*: a `---` divider, blank lines, and omission/reduction-note blockquotes.

`validate` does **not** guarantee this. Codex spec-review (round 1) empirically confirmed that a `validate`-clean spec can carry author prose in a top-level gap, prose inside Appendix A/D, or a subsection like §7.3 without §7.2 — all returning zero findings (`validate.py` only gap-checks *top-level* numbered sections and never inspects gap or appendix prose). So the property is **enforced by the upgradeability precheck** (decision 10), not assumed from `validate`:

- The precheck compares the source against its declared-tier bundled template *outside authored section bodies*. If the gaps, notes, Appendices A/B/D, or subsection membership deviate, `upgrade` refuses (`source_not_upgradeable`) before touching anything.
- Within a source that passes the precheck, the property holds by construction, so the splice may insert **only at heading boundaries** and edit **only canonical filler** — it never slices through author prose.

This also resolves the subsection-shape question: the precheck refuses a non-canonical subsection set (e.g. §7.3 without §7.2), so within an upgradeable source every section's subsections are exactly the source tier's. Missing subsections are then inserted at their **canonical numeric position** (Component 4), never merely "after the last present one" — an ordering that would otherwise risk an `SV-ORDER` output.

## Invariants — the consumer contract (must NOT change)

These hold for every `upgrade` invocation and are asserted by tests:

- **U1 — Output validates.** For any additive `(source, target)`, the delivered text is `validate`-clean. Enforced at runtime (decision 7) and as a property test over all tier pairs.
- **U2 — Author bytes are preserved verbatim.** Every canonical section/subsection present in the source appears in the output byte-for-byte, including comments, spacing, and author-added table rows. No renumbering; no `§`/ID reference rewrite.
- **U3 — Template-faithful.** Upgrading a tier fixture yields the next fixture: `upgrade(valid_light, →standard)` is byte-identical to the `valid_standard` fixture (given identical author-filled cells), and likewise light→full, standard→full. This pins fidelity mechanically.
- **U4 — Preview is pure.** Default / `--stdout` create or modify no file anywhere; output goes to stdout only.
- **U5 — Additive-only.** Same-tier or downgrade targets write nothing and exit 2.
- **U6 — Fail-closed on both ends.** A non-`validate`-clean source is refused before any splice (`source_invalid`, findings reported); a source that fails the upgradeability precheck is refused before any splice (`source_not_upgradeable`, deviation named); a spliced output that fails `validate` is refused before any write (`self_validation_failed`). All exit 2.
- **U7 — Atomic in-place / output write.** `-i` and `-o` either leave the destination as the full validated upgrade or leave it untouched — never partial (temp-file + `os.replace`). Symlink targets, non-regular targets, and symlinked in-tree parents are refused even with `--force`.
- **U8 — No tracebacks.** Every bad input (missing `SRC`, unreadable source, invalid source, bad `--to`, flag conflict, same/down tier, existing `-o` target, non-regular/symlink target) yields a clean message and exit 2, never a stack trace.
- **U9 — `--json` on every outcome.** Success and every exit-2 failure emit a documented JSON object when `--json` is passed; nothing else is printed to stdout in that mode.

## Component 1 — CLI surface & flag matrix

```text
project-standards spec upgrade SRC --to {standard|full}
    [--stdout] [-o OUT | --output OUT] [-i | --in-place]
    [--force] [--json]
```

- `SRC` — **required** positional; the existing spec to upgrade.
- `--to {standard|full}` — **required**; target tier (decision 5).
- no output flag / `--stdout` — **preview**: print to stdout, write nothing (decision 1).
- `-i` / `--in-place` — atomically rewrite `SRC`.
- `-o OUT` / `--output OUT` — write to a new path; refuse-if-exists unless `--force`.
- `--force` — permit overwriting an existing regular-file `OUT` (qualifies `-o` only).
- `--json` — machine-readable payload (Component 7) for success and failure alike.

**Flag conflict matrix (frozen).** Every combination has a defined outcome:

| Combination | Outcome | Exit |
| --- | --- | --- |
| neither `-i` nor `-o` (with/without `--stdout`) | preview to stdout | 0 |
| `-i` alone | atomic in-place rewrite of `SRC` | 0 / 2 |
| `-o OUT` alone | atomic write to `OUT` (refuse/force/safety) | 0 / 2 |
| `-i` **and** `-o` | usage error: "choose one of --in-place or --output" | 2 |
| `-i` **and** `--stdout` | usage error: "--stdout previews; do not also pass --in-place" | 2 |
| `--stdout` **and** `-o` | usage error: "choose one of --stdout or --output" | 2 |
| `--force` with `-i` or `--stdout` | usage error: "--force only applies to --output" | 2 |
| `-o OUT` where `OUT` resolves to `SRC` | usage error: "output equals source; use --in-place" | 2 |

The `spec` group is early-dispatched from `src/project_standards/cli.py`; Spec #3 registers an `upgrade` handler in `specs/cli.py`'s `_VERBS`, adds it to `_USAGE`, and updates the top-level help string at `cli.py:245`.

## Component 2 — Tier rules & direction

`--to` names the *target*; the *source* tier is read from the source's `profile:` frontmatter. Direction is enforced against the registry's tier ladder (`light ⊂ standard ⊂ full`):

| Source → Target | Behavior | Code |
| --- | --- | --- |
| light→standard, light→full, standard→full | proceed | — |
| X→X (same tier) | refuse: "already at profile `X`" | `not_upgradeable` |
| standard→light, full→standard, full→light | refuse: "downgrade is not supported; upgrade is additive-only" | `not_upgradeable` |

A source whose `profile:` is missing or not a known tier is caught by decision 3's input `validate` (it is a frontmatter finding) → `source_invalid`, not `not_upgradeable`.

## Component 3 — Execution flow (the doubly-fail-closed pipeline)

```text
read SRC ──▶ parse + validate SRC ──(findings)──▶ REFUSE exit 2 (source_invalid + findings)
                    │ clean
                    ▼
           tier-direction check ──(same / down)──▶ REFUSE exit 2 (not_upgradeable)
                    │ additive
                    ▼
      upgradeability precheck ──(scaffold deviates)──▶ REFUSE exit 2 (source_not_upgradeable)
                    │ canonical shape
                    ▼
   upgrade_text(source, target_template, target_tier)   ← pure, in memory
                    │
                    ▼
   self-validate OUTPUT (validate_document) ──(findings)──▶ REFUSE exit 2 (self_validation_failed)
                    │ clean
                    ▼
   deliver:  default/--stdout → stdout   |   -i → atomic rewrite SRC   |   -o → atomic write OUT
```

Three fail-closed gates precede any write: `validate`-clean, then upgradeable-shape (the precheck that makes the splice's structural assumptions true), then output self-validation. The dangerous middle — an in-place rewrite of author work — is bracketed by proofs of correctness on both ends.

## Component 4 — The splice (`upgrade_text`)

`upgrade_text(source_text, target_template_text, *, target_tier) -> str` is a pure function (decision 9) composed of the passes below. It operates on **raw text** — slicing and concatenating substrings — so author-owned spans are copied verbatim and never re-serialized (decision 4, U2).

### Unit-ownership model

Every unit is classified once; its class decides where its bytes come from:

| Ownership | Units | Byte source |
| --- | --- | --- |
| **Author-owned** — keep source verbatim | Revision History, §1–§2, any shared section whose subsection-set is unchanged, shared leaf subsections (e.g. §7.1), Deviations Log, §21, `## References` when already present | **source** |
| **Template-owned** — take from target | all inter/intra-section filler (omission notes, reduction-note intros, dividers), Appendix A (its ID-prefix table must grow with the tier), Appendix B (Agent Implementation Contract — tier-variant), Appendix D (tailoring guide) | **target template** |
| **Missing** — insert | every section/subsection/appendix in `tier_units(target) − tier_units(source)` | **target template** |
| **Rewritten in place** | frontmatter `profile:`, H1 `(Tier)` suffix | line rewrite |

Ownership is derived from the registry (`tier_sections`, `appendices`) diffed against the parsed heading sets of both texts — nothing tier-specific is hardcoded in `upgrade`. Appendices A, B, and D are treated as template-owned (replaced wholesale from the target tier) because their content is canonical boilerplate the standard owns and **all three are tier-variant** — Appendix A's prefix table *must* grow to declare the new tier's ID prefixes (`G- NFR- IR- DR-` …) or the upgraded spec fails `validate`; Appendix B (Agent Implementation Contract) gains tier-specific rules between Light/Standard/Full and must not be left stale in a higher-tier output; Appendix D is the tier's tailoring guide. Wholesale replacement is **safe because the precheck (decision 10) has already confirmed the source's Appendix A/B/D byte-match the source-tier template** — so there is no author content in them to lose. A source with an edited Appendix A, B, or D is refused (`source_not_upgradeable`) before the splice, never silently overwritten. (This answers Codex SA-003 and SA-NEW-001: replacement can neither delete `validate`-clean author content nor leave a stale lower-tier Appendix B, because a non-canonical appendix makes the source non-upgradeable and a canonical one is replaced from the target tier.)

### Three pure transformation passes

1. **Whole-section insertion (anchor + positional).** For each omission-note blockquote in the source (identified by the same `> … tier … omitted` shape `validate._check_sections` parses), replace *that single line* with the target template's span for its covered range — sliced from the first covered `## N` heading to just before the next section present in the *source*. That span carries the inserted sections **and** the target's own narrower omission notes (so a light→standard jump keeps Standard's `§5`-note, which Standard still omits). Units with no note anchor (`## References` — silently absent in Light) insert **positionally** by canonical ordering relative to their shared neighbors (after Deviations Log, before Appendix A).
2. **Intra-section subsection insertion.** For each shared section whose target subsection-set ⊋ source's (§7 and §17 on light→standard; §8, §18, §19 on standard→full): delete the known reduction-note intro (`> At the Light profile…`), then insert each missing subsection sliced from the target at its **canonical numeric position** (not merely after the last present subsection — that would mis-order a source that legitimately has a later subsection). The precheck (decision 10) has already guaranteed the source's subsection set is the source tier's, so within an upgradeable source the missing subsections are a clean suffix; canonical-position insertion is the robust rule regardless.
3. **Template-owned replacement + line rewrites.** Replace the Appendix A, B, and D bodies with the target tier's (all three are tier-variant boilerplate; the precheck guarantees the source's are canonical, so nothing author-written is lost); rewrite `profile:` (reuse `new._rewrite_frontmatter`) and rewrite the H1 `— Specification (Light)` suffix to `(Standard)` / `(Full)` (a small new rewriter — `new._rewrite_h1` substitutes only the back-ticked name, not the suffix).

Because passes 1–2 read *which* sections and notes to insert by diffing the two texts against the registry, `upgrade` follows template evolution automatically: no fact like "§5 stays omitted at Standard" is written in its code — it falls out of copying the target template's own span.

## Component 5 — Module layout & reuse

| Path | Responsibility | New? |
| --- | --- | --- |
| `src/project_standards/specs/commands/upgrade.py` | pure passes: `upgrade_text(...)`, the upgradeability precheck `check_upgradeable(source_text, source_tier_template) -> str \| None`, unit-diff helper, section/appendix slicers, H1-suffix rewriter. No I/O. | **new** |
| `src/project_standards/specs/cli.py` | `_run_upgrade` shell + `upgrade` in `_VERBS`/`_USAGE`: flag-matrix, `validate` gate, tier-direction check, upgradeability precheck, output self-validate gate, deliver (stdout / `-i` / `-o`). **No `--config`** — `upgrade` operates on an explicit `SRC` and needs no repo config (decision resolves Codex SA-005). | edit |
| `src/project_standards/cli.py` | add `upgrade` to the `spec` group help string (`:245`). | edit |
| `specs/registry.py`, `specs/document.py` | `tier_sections`/`appendices`, `TEMPLATES_DIR`/`TIER_FILES`, `section_slice`, heading/number parsers, `numkey()` ordering. | reuse |
| `specs/commands/validate.py`, `specs/document.py` | `parse_document` + `validate_document` for the input and output gates. | reuse |
| `specs/commands/new.py`, `specs/cli.py` | `_rewrite_frontmatter` (set `profile:`); the `NewError` / `_emit_new_failure` JSON-error machinery; and the **extracted** atomic-write safety primitive `_safe_atomic_write(target, text, *, force) -> bool` (target-type + symlinked-parent refusal, `mkstemp`+`os.replace`, mode preservation) factored out of `new`'s `_write_new_file`. `upgrade` keeps its own overwrite policy (`-i` overwrites as the normal path) and its own JSON payload in `_run_upgrade` — it does **not** reuse `_write_new_file` wholesale (resolves Codex SA-004). | reuse / extract |
| `tests/test_spec_upgrade.py`, `tests/test_spec_upgrade_cli.py` | pure-pass units + CLI/integration. | **new** |

The purity boundary mirrors Spec #2: all logic lives in pure `str -> str` passes in `upgrade.py`; the one impure edge is `_run_upgrade` in `cli.py`. `upgrade` needs no RNG and no clock (decision 9), so its pure tests are even simpler than `new`'s.

## Component 6 — Write model & safety

The `cli.py` shell, after `upgrade_text` returns and output self-validation passes:

- **default / `--stdout`:** write the text (or JSON payload) to stdout, exit 0. No path is opened for writing (U4).
- **`-i` / `--in-place`:** atomically rewrite `SRC` — the **normal** overwrite path (unlike `new`, where overwrite is `--force`-gated). Use the extracted `_safe_atomic_write` primitive (Component 5): refuse a symlink target (incl. broken) or any non-regular existing target; refuse a symlinked in-tree ancestor (walk bounded to cwd); write via `mkstemp` in the destination directory + `os.replace`; **preserve the source's mode** on overwrite. An in-place upgrade through a symlink is still refused. `_run_upgrade` supplies its own JSON payload (Component 7), not `new`'s.
- **`-o OUT`:** atomic write to `OUT`; refuse (exit 2) if `OUT` exists as a regular file without `--force`; same target-type and symlinked-parent refusals as `-i`; auto-create missing parents with `mkdir(parents=True, exist_ok=True)` (a non-directory parent component → `mkdir_failed`, exit 2). `OUT` resolving to `SRC` is a flag conflict (Component 1), not an overwrite.

Writing is last: read, input-validate, direction-check, splice, output-validate, and all target-type / parent-chain checks complete before any byte is committed (U7). The guarantee is scoped to the destination file, exactly as in Spec #2 (an empty parent directory auto-created just before a later write failure may remain — a benign artifact, not a corrupt spec).

## Component 7 — Error handling & exit codes

| Situation | Behavior | Exit |
| --- | --- | --- |
| Wrote file (`-i`/`-o`), or printed (default/`--stdout`) | success | 0 |
| `SRC` missing / not a regular file | `source_not_found` / read error, no write | 2 |
| `SRC` unreadable / undecodable | `source_read_error`, no write | 2 |
| `SRC` fails input `validate` | `source_invalid` + findings, no splice | 2 |
| `SRC` scaffolding deviates from its tier template (gap prose, edited Appendix A/B/D, non-canonical subsection) | `source_not_upgradeable` + deviation named, no splice | 2 |
| Same-tier or downgrade `--to` | `not_upgradeable`, no write | 2 |
| Any flag-matrix conflict (Component 1) | `flag_conflict`, no write | 2 |
| Argparse-level error (missing `SRC`/`--to`, bad `--to`, unknown flag) | JSON-aware parser → `usage` | 2 |
| `-o OUT` exists (regular file), no `--force` | `exists`, no write | 2 |
| `-i`/`-o` target is a dir/symlink/special file | `not_regular_file`, even with `--force` | 2 |
| A parent directory of the target is a symlink | `symlinked_parent`, even with `--force` | 2 |
| Parent path component is a non-directory | `mkdir_failed`, no write | 2 |
| **Spliced output fails `validate_document`** | **fail-closed: no write, report finding(s)** — `self_validation_failed` | 2 |

There is no exit-1 case: `upgrade` either produces a conformant upgrade (0) or refuses (2). Exit 1 stays reserved for findings against a consumer's spec (`validate`/`lint`). No path yields a traceback (U8).

### `--json` output contract

With `--json`, stdout carries exactly one JSON object and nothing else (U9). Fields are frozen so downstream agents/CI can depend on them.

**Success — `-i` / `-o` write:**

```json
{
  "ok": true,
  "spec_id": "SPEC-7F3Q",
  "from_profile": "light",
  "to_profile": "standard",
  "path": "docs/specs/checkout.md",
  "written": true,
  "mode": "in_place"
}
```

`mode ∈ {"stdout", "in_place", "output"}`. For `-o`, `path` is `OUT`; for `-i`, `path` is `SRC`.

**Success — preview (default / `--stdout`):** `path` is `null`, `written` is `false`, `mode` is `"stdout"`, and the upgraded text rides along:

```json
{ "ok": true, "spec_id": "SPEC-7F3Q", "from_profile": "light", "to_profile": "full", "path": null, "written": false, "mode": "stdout", "content": "---\nspec_id: SPEC-7F3Q\n…" }
```

**Failure (any exit-2 case):**

```json
{ "ok": false, "error": "source has 2 validation finding(s); fix them before upgrading", "code": "source_invalid", "findings": [ … ] }
```

`code` extends `new`'s frozen slug set with **`source_not_found`**, **`source_read_error`**, **`source_invalid`** (carries the input `validate` `findings`), **`source_not_upgradeable`** (the upgradeability-precheck refusal, decision 10), and **`not_upgradeable`** (tier direction). Reused from `new`: `usage`, `flag_conflict`, `exists`, `not_regular_file`, `symlinked_parent`, `mkdir_failed`, `write_failed`, `self_validation_failed`. **`config_error` is not in `upgrade`'s set** — `upgrade` takes an explicit `SRC` and reads no repo config (Codex SA-005). `source_invalid` and `self_validation_failed` include a `findings` array of the `validate` `Finding` records (the `dataclasses.asdict` shape the existing commands emit). The parser is JSON-aware (a subclass whose `error()` raises rather than calling `sys.exit`) so even argparse errors emit the `--json` object.

## Component 8 — Testing

- **Unit — pure passes** (`tests/test_spec_upgrade.py`): for light→standard, light→full, standard→full assert (a) author sections byte-identical (U2); (b) the exact inserted sections/subsections present at canonical positions; (c) reduction-note intros removed; (d) omission notes reconciled to the target set (target-tier notes remain, filled-section notes gone); (e) `profile:` and H1 `(Tier)` suffix correct.
- **Template-faithful round-trip (U3 — the fidelity anchor):** with author-filled cells held identical, `upgrade_text(valid_light, standard_template, "standard")` is **byte-identical to the `valid_standard` fixture**; likewise light→full and standard→full against their fixtures. Any template drift or splice bug fails this exact-equality test. (The plan will likely need to author an **aligned fixture pair/triple** — the same author-filled cells across light/standard/full — since the existing `valid_light.md`/`valid_standard.md` fixtures were written independently and may not share identical cells.)
- **Output-validates property (U1):** parametrized over all three tier pairs and over `{minimally-filled, fully-filled}` sources, assert `validate_document(parse_document(upgrade_text(...)))` is empty.
- **Upgradeability precheck (Codex SA-001/002/003, SA-NEW-001):** each of these `validate`-clean-but-non-canonical sources is refused with `source_not_upgradeable` before any splice — (a) author prose inserted into a top-level gap (before/after an omission note); (b) extra author prose inside Appendix A, Appendix B, and Appendix D; (c) a non-canonical subsection shape (Light with `### 7.3` but no `### 7.2`; Standard with `### 8.6` but no `### 8.4`). A canonical source passes the precheck.
- **Appendix B is upgraded, not left stale (Codex SA-NEW-001):** a Light→Standard and a Standard→Full output contains the *target* tier's Appendix B exactly (asserted within the U3 round-trip, which now covers Appendix B byte-for-byte).
- **Canonical subsection insertion:** for an upgradeable source, missing subsections land at their canonical numeric position and the output is ordered (no `SV-ORDER`) — asserted by the U3 round-trip and a targeted §7/§17 case.
- **Direction / guard:** same-tier and each downgrade → `not_upgradeable` (exit 2); a source with a missing/unknown `profile:` → `source_invalid` (not `not_upgradeable`); a source with any `validate` finding → `source_invalid` + findings.
- **No config coupling (Codex SA-005):** a malformed `.project-standards.yml` in the repo does **not** affect `upgrade FILE` — it reads no config.
- **CLI / integration** (`tests/test_spec_upgrade_cli.py`, patterned on `test_spec_new_cli.py`): the full flag-conflict matrix each → exit 2; `-i` atomic rewrite + **mode preservation** (pre-set an unusual mode, assert preserved); `-o` refuse-if-exists / `--force` overwrite; existing dir / symlink / broken-symlink target and a symlinked parent → refused even with `--force`; parent auto-creation; `-o OUT == SRC` → conflict; default and `--stdout` create no file (U4, assert target dir unchanged); atomic write leaves no temp file; every exit code per Component 7.
- **`--json`:** success (`-i`, `-o`, preview), `source_invalid` (with `findings`), **`source_not_upgradeable`** (gap prose, edited Appendix A/B/D, and non-canonical subsection sources — each emits `ok:false`, `code:"source_not_upgradeable"`, and a deviation message), `not_upgradeable`, `exists`, `self_validation_failed` → assert documented payload shape and `code`; assert nothing else on stdout.
- **Dogfood:** `upgrade valid_light --to full --stdout` piped through `validate` is clean (end-to-end U1).
- **Coverage:** the suite keeps branch coverage ≥ the repo `fail_under` and the full gate green (`ruff format --check`, `ruff check`, `basedpyright`, `pytest`, `coverage report`, `pip-audit`).

## Acceptance criteria

- `project-standards spec upgrade SRC --to {standard,full}` transforms a `validate`-clean, upgradeable-shape source into a `validate`-clean target-tier spec, preserving every author-filled section byte-for-byte, for every additive tier pair. Standard→Full inserts the Full-only sections **and Appendix C's optional modules** wholesale (as missing units); the author deletes any unused modules afterward.
- Upgrading a tier fixture reproduces the next fixture byte-for-byte (U3).
- Preview is the default and writes nothing; `-i` rewrites `SRC` atomically with mode preserved; `-o` writes a new file (refuse-if-exists / `--force`); symlink and non-regular targets and symlinked parents are refused even with `--force`; `-o` resolving to `SRC` (incl. via symlink, by `samefile`) is a flag conflict.
- A non-`validate`-clean source, a non-upgradeable-shape source (gap prose / edited Appendix A/B/D / non-canonical subsection), a same-tier or downgrade target, and every flag conflict are refused (exit 2) with a clean message; the spliced output is self-validated before any write.
- Every command outcome supports `--json` with the documented payload and `code` slug; no path yields a traceback.
- Invariants U1–U9 are covered by tests; the full gate is green.

## Non-goals

- **Downgrade / tier reduction** — additive-only (decision 6).
- **Filling inserted sections' `<…>` placeholders** — inserted sections arrive as pristine template stubs; filling them is the author's job, which `lint` tracks.
- **Fabricating a Revision-History entry** for the upgrade — `upgrade` does not invent author-log content. (Revisit only if the standard later mandates an upgrade audit trail.)
- **Upgrading a non-`validate`-clean source** — fail-closed (decision 3); the author fixes findings first.
- **Preserving or merging non-canonical scaffolding** — a source with gap prose, an edited Appendix A/B/D, or a non-canonical subsection shape is *refused* (decision 10), not accommodated. `upgrade` restructures canonical specs; it is not a general Markdown merge tool. The author restores canonical structure (or moves the stray content into a section body) first.
- **`status` rollup and the semantic-review contract** — deferred per README §5.
- **Registering `project-spec` as a standard / writing README §6 Adoption** — separate adoption work; shipping `upgrade` completes the v1-core *tooling* but does not itself register the standard (though it unblocks that decision — see Versioning & docs impact).
- **Cross-process/TOCTOU write locking** — the refuse-if-exists check and the atomic rename are not a lock against a concurrent writer; acceptable for a single-user local/CI CLI, called out as a known boundary shared with `new`.

## Versioning & docs impact

- Adding the `upgrade` subcommand is an **additive, minor** change to the package's consumer contract — a new command surface, no change to `validate`/`lint`/`extract`/`next`/`new`. Per `meta/versioning.md` this rides a minor bump.
- README §5 already lists `upgrade` as a *core* capability and already promises `--json` on every command, so no standard-text change is required when it ships; its status simply moves from "specified" to "implemented." With `upgrade` shipped, the **v1-core tool surface is complete** — which is the precondition the adoption track was waiting on (README §6 Adoption + registering `project-spec`). The CHANGELOG entry already owed (see `TODO.md`) should note `upgrade`'s arrival alongside `new` and the pending release.
- **Package developer docs (Codex SA-006):** `src/project_standards/README.md`'s CLI table (`:30-44`) currently omits the nested `project-standards spec` command group entirely, and `src/project_standards/cli.py:245` help lists only `validate|lint|extract|next|new`. This plan adds `upgrade` to the `cli.py` help string; updating the package README's CLI table to document the `spec` group (all six verbs) is in scope for the plan's final docs task so developer-facing docs do not go stale.
- `project-spec` remains an **unregistered, in-development** standard until the separate adoption work runs; shipping `upgrade` does not register it, but removes the "incomplete tooling" objection to advertising it.

## Open implementation questions (for the plan, not blockers)

- **Upgradeability precheck implementation:** the exact comparison for "scaffolding matches the source-tier template outside authored bodies." The leading candidate: run the splice's own block/subsection segmentation, mask each leaf section/subsection body to a sentinel in both the source and the source-tier template, and require byte-equality of the masked results (headings, gaps, notes, Appendices A/B/D, and subsection membership must match; author bodies are ignored). A useful internal self-check: reshaping a canonical source to its *own* tier must be the identity. Only the *contract* (refuse `source_not_upgradeable` on any deviation) is frozen here; the plan pins the algorithm.
- **Section/appendix slicing primitive:** whether `upgrade` reuses `document.section_slice` as-is for pulling a target-template span, or needs a thin sibling that returns the span *including* trailing filler up to the next heading (needed so an inserted section carries its following omission note / divider). Leaning a small dedicated slicer in `upgrade.py` keyed on heading offsets, to keep `document.py` focused on read-only extraction.
- **Reduction-note identification:** the `> At the Light profile…` intros are matched today only informally. The plan should decide whether to match them by a precise regex (`profile` + a `§n.n` reference, no `omitted`) or to derive their removal purely structurally (any blockquote in a shared section's pre-first-subsection filler that the target template's corresponding filler lacks). The structural derivation is more robust to wording changes and is preferred if it proves clean.
- **`-o` path-equality test:** how to decide `OUT == SRC` (both may be relative, one a symlink) — likely `os.path.samefile` when both exist, falling back to normalized-path comparison when `OUT` does not yet exist.
- **Exact message spellings:** wording of the `not_upgradeable` / `source_invalid` / conflict messages is chosen during implementation; only exit codes, `--json` `code` slugs, and behavior are frozen here.
