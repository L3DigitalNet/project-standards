# Design: Frontmatter validation + autocorrection suite

**Date:** 2026-06-08 **Status:** approved (brainstorming complete; codex spec-review converged round 3 — SA-001…008, SA-NEW-001…003 resolved) **Author:** session 2026-06-08

## Table of Contents

- [Problem / Goal](#problem--goal)
- [Decisions (locked during brainstorming)](#decisions-locked-during-brainstorming)
- [Invariants — the consumer contract (must NOT change)](#invariants--the-consumer-contract-must-not-change)
- [Sub-project A — `format-frontmatter` (autoformatter)](#sub-project-a--format-frontmatter-autoformatter)
  - [A.1 CLI surface](#a1-cli-surface)
  - [A.2 Transform pipeline (deterministic, idempotent)](#a2-transform-pipeline-deterministic-idempotent)
  - [A.3 Serializer — line-based reconstruction](#a3-serializer--line-based-reconstruction)
  - [A.4 Hardcoded refusal set (denylist)](#a4-hardcoded-refusal-set-denylist)
  - [A.5 Scaffold mode (part of default `--write`)](#a5-scaffold-mode-part-of-default---write)
  - [A.6 Fail-safe for unsupported YAML](#a6-fail-safe-for-unsupported-yaml)
  - [A.7 Testing](#a7-testing)
- [Sub-project B — `validate-references` (semantic validators)](#sub-project-b--validate-references-semantic-validators)
  - [B.1 CLI surface + config](#b1-cli-surface--config)
  - [B.2 Repo index](#b2-repo-index)
  - [B.3 Checks](#b3-checks)
  - [B.4 Testing](#b4-testing)
- [Sub-project C — ergonomics](#sub-project-c--ergonomics)
- [Acceptance criteria](#acceptance-criteria)
- [Non-goals](#non-goals)
- [Versioning impact](#versioning-impact)
- [Open implementation questions (for the plan, not blockers)](#open-implementation-questions-for-the-plan-not-blockers)

## Problem / Goal

The repo ships a read-only frontmatter validator (`validate-frontmatter`, JSON-Schema) and exactly one autocorrector — `validate-id --fix`, which rewrites a single field. Two whole classes of capability are absent:

1. **No general autoformatter.** Everything the schema checks but cannot fix — key order (JSON Schema structurally cannot enforce object key order), quoting, list style, missing required arrays, `type`→`doc_type` — is left for a human to fix by hand. Hand-fixing is exactly what drifts.
2. **No cross-field or cross-file validation.** JSON Schema cannot express `created ≤ updated`, repo-wide `id` uniqueness, or "this `related:` reference points at a real document." These are invisible to the current validator.

**Goal:** a complete frontmatter validation + autocorrection suite, shipped together in `2.1.0`, in three sub-projects:

- **A — `format-frontmatter`**: a whole-block autoformatter (the natural companion to `validate-id --fix`).
- **B — `validate-references`**: the semantic checks the schema cannot express.
- **C — ergonomics**: `project-standards fix`, extended `validate`, `--stdin`, and `.pre-commit-hooks.yaml`.

A and B are independent; C wraps A. Build order A → B → C; all three ship in one cohesive `2.1.0` (the already-implemented adopt CLI + `validate-id` ride along).

## Decisions (locked during brainstorming)

1. **Full suite A + B + C ships in one cohesive `2.1.0`** (release held until all three are green). The finished adopt CLI + `validate-id` work currently un-tagged on `testing` ships in the same tag.
2. **Serializer = surgical / line-based**, extending the `validate-id --fix` technique (`validate_id.py:333-349`). **No new runtime dependency** (no `ruamel.yaml`). Inline comments and per-line endings are preserved.
3. **A is a new module** `src/project_standards/format_frontmatter.py` + console script `format-frontmatter`, a sibling to `validate-frontmatter`/`validate-id`. It **does not touch `id`** — that stays `validate-id`'s responsibility (single responsibility); C's `project-standards fix` orchestrates both.
4. **A modes:** `--check` (default) and `--write`, mutually exclusive. The formatter is **idempotent** (`format∘format == format`), enforced by a property test.
5. **`doc_type` inference is fill/correct-only and ID-safe** — apply the standard's path rules (`README.md`/`index.md` → `index`; under `docs/research/` → `research`) **only when `doc_type` is missing or not a valid enum value**, and when scaffolding a new block. A valid explicit `doc_type` is **never** overridden. (Reversed from the round-0 "override even valid" rule: overriding a valid `doc_type` while the formatter leaves `id` untouched would create an `id`/`doc_type` mismatch that `validate-id` rejects — this repo's `standards/*/README.md` are validly `doc_type: 'reference'` with `reference-…` ids. See codex SA-001.)
6. **`updated:` is not bumped by default.** Auto-bump to today is available only via an explicit `--bump-updated` flag. A cosmetic reformat must not claim the document's content was updated.
7. **Scaffold-empty is part of the default `--write`**: an included, non-denylisted file with no frontmatter block gets a fabricated block in the same pass.
8. **A carries a hardcoded refusal set** (basenames `CLAUDE.md`/`AGENTS.md`/`GEMINI.md`; any path under `.claude/`, `.agents/`, `.codex/`) that overrides include/scaffold **unconditionally**, independent of config. Config decides *what is formatted*; the denylist guarantees *what can never be touched* even when a consumer's `exclude` is misconfigured.
9. **`schema_version` is injected only when missing** (= the bundled contract version); an existing value is never changed (a version change is a contract migration, not formatting).
10. **Unknown top-level keys are warn-only**, never auto-deleted (the formatter cannot know the author's intent; the schema's `additionalProperties:false` already errors on them).
11. **B is a new module** `src/project_standards/validate_references.py` + console script `validate-references`, a repo-wide pass. It is **opt-in via config** (`markdown.frontmatter.references.enabled`, default `false`) so a minor-version upgrade never newly-fails an existing consumer's CI.
12. **B dangling references are a warning, not an error** (exit 0). A reference resolves if it is an existing file path **or** a known `id` in the repo index; neither → warning. Rationale: ADR ids and `related:` legitimately cite *other repos'* ids, which are not locally resolvable.
13. **B checks and levels:** `id` uniqueness (**error**), referential integrity (**warning** on dangling), supersede reciprocity (**warning**), date ordering `created ≤ updated` and `reviewed ≥ created` (**error**), duplicate ADR `NNNN` sequence in one repo (**error**).
14. **C:** `project-standards fix` = `format-frontmatter --write` **first** (normalizes `type`→`doc_type` and fills missing `doc_type`), **then** `validate-id --fix` (id now derivable from a valid `doc_type`), **then a final `project-standards validate`** that fails if any id/schema check still fails — proving the fix postcondition (codex SA-002). `project-standards validate` is extended to also run `validate-references` (self-gates on config), **and the reusable consumer workflow runs it too** (codex SA-003). `format-frontmatter` gains `--stdin`. A root `.pre-commit-hooks.yaml` ships **both** a mutating and a check-only hook id per tool. `format-frontmatter`/`fix` **skip when a custom schema is configured**, mirroring `validate-id` (codex SA-008).

## Invariants — the consumer contract (must NOT change)

- The existing console scripts `validate-frontmatter`, `validate-id`, `project-standards` and all their current flags and exit codes.
- The `.project-standards.yml` config shape (new keys are strictly additive and opt-in).
- The bundled schema path (`src/project_standards/schemas/markdown-frontmatter.schema.json`, its own `$id`) and the bundled `registry.json` + `Registry` reader.
- `validate-id --fix` behavior (source-preserving id rewrite).
- **No existing consumer may newly-fail on upgrade**: B is opt-in; A is a new command that is never auto-run by the existing `validate` read path.

## Sub-project A — `format-frontmatter` (autoformatter)

### A.1 CLI surface

```text
format-frontmatter [FILE ...] [--config PATH] [--schema PATH] [--glob PATTERN]
                   [--check | --write] [--bump-updated] [--stdin]
                   [--no-require-frontmatter] [--quiet]
```

- Reuses `collect_paths` (`validate_frontmatter.py:232`), `load_config`, and `parse_frontmatter` — so include/exclude, `--glob`, and the `CLAUDE.md`/`.claude/**` config exclusions behave identically to the validator.
- **Flag compatibility:** accepts the same flag set as `validate-frontmatter`/`validate-id` — `--config`, `--schema`, `--glob`, `--no-require-frontmatter` (compat no-op; the formatter already skips no-frontmatter files unless scaffolding), `--quiet` — so `project-standards fix`/`validate` can forward their full argv unchanged without argparse errors (codex SA-008, SA-NEW-001).
- **`--check`** (default): report files that would change; **exit 1** if any would change or any is unparseable, else **0**.
- **`--write`**: apply changes in place using A.3; **exit 0** when all writable files succeed (even if changed), **1** if any file is unparseable/unwritable, **2** config error.
- **`--stdin`**: read one document from stdin, emit the formatted document to stdout, exit 0 (1 if unparseable). Mutually exclusive with `FILE`/`--glob`/`--write`. Path-dependent transforms are **disabled** in stdin mode: no path means no `doc_type` path-inference, no scaffolding, and the denylist cannot apply — stdin formats an **existing** block only and emits no-frontmatter input unchanged.
- **Custom schema:** when `markdown.frontmatter.schema` is a custom path (or `--schema` is passed), `format-frontmatter` **skips with a note and exits 0** — the canonical-order, `schema_version`, and `doc_type` transforms assume the bundled contract, and a consumer-owned schema may define different conventions. Mirrors `validate-id`'s existing custom-schema skip (codex SA-008).
- **Warnings never make `--check` "dirty":** unknown-key warnings and unsupported-YAML **skips** (A.6) print to stderr but exit 0 on their own; only a would-change file or an unparseable block makes `--check` exit 1.

### A.2 Transform pipeline (deterministic, idempotent)

Applied in this fixed order to the parsed mapping + raw source lines:

1. **Key rename** `type:` → `doc_type:` — only when `doc_type` is absent; if both are present, warn and leave both (don't clobber).
2. **`doc_type` path inference** (Decision 5) — **fill/correct only**: apply `README.md`/`index.md` → `index` and `docs/research/**` → `research` **only when `doc_type` is missing or not a valid enum value**. A valid value is left untouched, so the formatter never creates an `id`/`doc_type` mismatch without touching `id`.
3. **Inject `schema_version`** if missing (= bundled contract version from config/registry); never change an existing value.
4. **Inject missing required arrays** `tags`/`aliases`/`related` → `[]`.
5. **Quote normalization** — single-quote every scalar string, including dates and identifier-like numbers (`schema_version: '1.1'`).
6. **List normalization** — non-empty → block style (`- 'item'`); empty → `[]`; drop duplicate items preserving first-seen order.
7. **Canonical key reorder** to the 25-key order (`schema_version, id, title, description, doc_type, status, created, updated, reviewed, owner, consumer, tags, aliases, related, supersedes, superseded_by, depends_on, applies_to, source, confidence, visibility, license, publish, project, x_project`); unknown keys (warn-only) are preserved after the known keys in original relative order.
8. **(opt-in) `updated` bump** to today, only under `--bump-updated` and only when the file otherwise changed.

### A.3 Serializer — line-based reconstruction

The block is tokenized into **entries**, one per top-level key, each owning its source line(s): the key line (with any inline comment), plus **all following more-indented continuation lines** — whether a block list **or a nested mapping** (`publish`/`project`/`x_project` extension objects). A run of leading comment/blank lines attaches to the **following** key entry, so reordering moves a key's comment banner with it. Entries are re-emitted in canonical order, each contributing its source line(s) with **original per-line endings preserved**, exactly as `validate_id.py:333-349` does. For an extension object the top-level key is repositioned but its **nested content is preserved byte-for-byte** (no re-quoting inside the block), so the sanctioned `project:`/`publish:`/`x_project:` mappings in shipped examples format cleanly (codex SA-004); only top-level scalar values are re-quoted. The document body after the closing `---` is copied byte-for-byte. `--write` is **atomic** — the formatter writes a temp file and `os.replace`s it over the original, so an interrupted run never truncates a document.

### A.4 Hardcoded refusal set (denylist)

A module-level constant — basenames `{CLAUDE.md, AGENTS.md, GEMINI.md}` and any path with a component in `{.claude, .agents, .codex}` — is checked in the path-collection step. Matching files are dropped from the work set before any read/write, regardless of include or scaffold. This is defense-in-depth over the consumer's `exclude` (Decision 8).

### A.5 Scaffold mode (part of default `--write`)

For an included, non-denylisted file with **no** frontmatter block, fabricate a block that **passes the schema** yet is visibly incomplete:

- `schema_version` = bundled contract version.
- `id` = `{doc_type}-{base36(6)}-{slug}`, reusing `validate_id`'s token generator and `slugify` (extracted to a shared helper to avoid coupling). `doc_type` from the path rule else `note`; `slug` from the first `# H1` title if present, else the filename stem.
- `title` = first `# H1` text if present, else the humanized filename stem.
- `description` = a non-empty placeholder (`'TODO: one-sentence description.'`) — schema-valid but flagged for the author to replace.
- `doc_type` = path rule else `note`; `status` = `draft`.
- `created` = `updated` = today (date source injectable for tests).
- `tags` = `aliases` = `related` = `[]`.

Scaffold gets the file ~90% of the way. Because the `TODO:` placeholder is schema-valid (the schema only requires a non-empty `description`; the standard's stricter description rules are documented conventions, not machine-enforced — codex SA-006), `--write` **reports every scaffolded file distinctly** (`scaffolded: <path> — fill in title/description`) rather than implying completeness. Scaffolded blocks are deliberate *starting points*, not finished documents; the distinct report is the author's signal to fill them in.

### A.6 Fail-safe for unsupported YAML

Supported value shapes cover the entire standard surface: single-line scalars, empty flow list `[]`, block lists, and the sanctioned extension **mappings** (`publish`/`project`/`x_project`), handled as opaque blocks per A.3. If a block still contains a construct the line tokenizer cannot safely classify — anchors/aliases (`&`/`*`), merge keys (`<<`), or a multi-line `|`/`>` block scalar on a field the formatter would otherwise re-quote — it **skips that file with a warning** (exit 0 in `--check`; a skip is not a "would-change") rather than risk corrupting it. Correctness over coverage; these constructs appear in neither the standard's fields nor the shipped examples.

### A.7 Testing

`tests/test_format_frontmatter.py`: per-transform units; the **idempotence property test** (format twice → byte-identical); comment preservation (inline + leading banner); CRLF / mixed-ending preservation; denylist refusal; scaffold output passes `validate-frontmatter`; unsupported-YAML skip-with-warning; `--stdin` round-trip; `--check`/`--write` exit codes.

## Sub-project B — `validate-references` (semantic validators)

### B.1 CLI surface + config

```text
validate-references [FILE ...] [--config PATH] [--schema PATH] [--glob PATTERN]
                    [--no-require-frontmatter] [--quiet]
```

**Flag compatibility (codex SA-NEW-001):** `validate-references` accepts the *full* flag set that `project-standards validate` forwards to its validators — `--schema`, `--glob`, `--no-require-frontmatter`, `--quiet`, and `FILE` — so extending `validate` to call it never argparse-errors a previously-valid invocation like `project-standards validate --schema custom.json --quiet`. Under a custom schema (`--schema` or a config custom-schema path) it **skips with a note and exits 0**, mirroring `validate-id` (the reference/id/ADR checks assume the bundled id conventions). `--no-require-frontmatter` is a compat no-op — references already skip files lacking frontmatter.

New module `validate_references.py` (keeps `validate_frontmatter.py` from bloating). Opt-in config, added to `load_config`:

```yaml
markdown:
  frontmatter:
    references:
      enabled: true   # default false
```

When disabled, the tool runs no checks and exits 0 (so the unified `validate` can always call it).

### B.2 Repo index

Collect the included set (via `collect_paths`), parse each file's frontmatter, and build: `id → [paths]`, the set of all known ids, and per-doc `{created, updated, reviewed, related, depends_on, supersedes, superseded_by, doc_type, id, path}`. (`applies_to` is deliberately absent — it is free-form scope, not references; see B.3.)

### B.3 Checks

| Check | Level | Rule |
| --- | --- | --- |
| `id` uniqueness | **error** | any `id` mapped to ≥2 files |
| Referential integrity | **warning** | each value in `related`/`depends_on`/`supersedes`/`superseded_by` resolves to an existing file path **or** a known `id`; else warn. `applies_to` is **excluded** — the standard defines it as free-form scope identifiers (services, components, environments), not document links (`standards/markdown-frontmatter/README.md:397`; codex SA-005) |
| Supersede reciprocity | **warning** | if A `superseded_by` B and B is local, B should `supersedes` A (and vice-versa) |
| Date ordering | **error** | `created ≤ updated`; `reviewed ≥ created` when `reviewed` is present and non-null |
| ADR sequence | **error** | duplicate `NNNN` among `doc_type: adr` docs in this repo |

**Reference resolution (codex SA-NEW-003).** A reference value resolves if it is either: (a) a **repo-root-relative path including the file extension** (the standard's recommended link form) that exists on disk — absolute paths and `../`-escaping paths are treated as unresolvable, and a value carrying a `#section` anchor does **not** resolve as a path (the standard uses document-level links, not `#` links — `standards/markdown-frontmatter/README.md:395-401`); or (b) an **exact** match against a known `id` in the repo index (no fuzzy/prefix matching). **Null and empty values are ignored** — `superseded_by: null` (as in `standards/adr/examples/adr.example.md`) and empty arrays are not dangling references. Bare filenames and bare ids that are not in the index resolve via (b) only; if neither (a) nor (b) holds, it is a single dangling **warning**.

Exit codes: **0** = no errors (warnings allowed), **1** = ≥1 error, **2** = config error. Warnings print to stderr and never affect the exit code.

### B.4 Testing

`tests/test_validate_references.py`: a fixture per check (duplicate id → error; dangling ref → warning, exit 0; `created > updated` → error; `reviewed < created` → error; duplicate ADR number → error; missing reciprocity → warning; valid set → exit 0); plus the opt-in gate (disabled → zero checks).

## Sub-project C — ergonomics

- **`project-standards fix`** (new subcommand, early-dispatched like `validate` so `--config` is forwarded): runs `format_frontmatter.main(['--write', …])` **first** (normalizes `type`→`doc_type`, fills missing `doc_type`), **then** `validate_id.main(['--fix', …])` (id now derivable from a valid `doc_type`), **then a final read-only `validate`** (`validate-frontmatter` + `validate-id`); returns the worst exit code and **fails if the final pass is non-clean**. Format-first + final-validate proves no invalid id can survive a "successful" fix (codex SA-002). Skips entirely under a custom schema (SA-008).
- **Extend `project-standards validate`**: after `validate-frontmatter` + `validate-id`, also call `validate_references.main(…)`, which self-gates on config (no config read needed in `cli.py`). Fold into the existing `max()` exit. `validate` is the single read-only gate; `fix` is the single writer.
- **Reusable consumer workflow** (`.github/workflows/validate-markdown-frontmatter.yml`): add a `validate-references` step (gated on config) so a consumer who sets `references.enabled: true` actually gets CI coverage — today the workflow runs `validate-frontmatter` + `validate-id` as separate steps and would silently skip references (codex SA-003). A test asserts the workflow invokes the reference validator.
- **`--stdin`** on `format-frontmatter` (A.1) for editor format-on-save.
- **Root `.pre-commit-hooks.yaml`** exposing, per tool, a mutating and a check-only id: `format-frontmatter-fix` / `format-frontmatter-check`, `validate-id-fix` / `validate-id-check`, `validate-frontmatter`, `validate-references`. Each hook sets `language: python`, `types: [markdown]`, and the right `--write`/`--check`/`--fix` args. Per-file hooks (format / `validate-frontmatter` / `validate-id`) take the staged filenames; the **`validate-references` hook sets `pass_filenames: false`** because its cross-file checks (id uniqueness, ADR sequence) need the whole repo, not a staged subset. The package must be `pip install .`-able with matching console scripts (`format-frontmatter`, `validate-references` added to `[project.scripts]`); consumers reference `repo: https://github.com/L3DigitalNet/project-standards` + a pinned `rev`. Per official pre-commit docs, a Python hook repo must be installable and expose an executable matching each `entry` (codex SA-007). Because the package is `requires-python >= 3.14`, pre-commit (which installs Python hooks with `pip install .` against the *system* Python by default) needs Python 3.14 available: each hook sets `language_version: python3.14` and the manifest/docs state the 3.14 prerequisite, and the `try-repo` smoke runs in a 3.14 environment (codex SA-NEW-002).

Testing: `fix` dispatch (format→id-fix→final-validate, worst exit, final pass clean on `type:`+invalid-id / missing-arrays+invalid-id / path-inferred-`doc_type` fixtures); `validate` runs references when enabled; a reusable-workflow test asserts the `validate-references` invocation; `.pre-commit-hooks.yaml` passes `pre-commit validate-manifest`, every `entry` resolves to a real `[project.scripts]` console script, and `pre-commit try-repo . format-frontmatter-check --all-files` runs the hook successfully.

## Acceptance criteria

- New console scripts `format-frontmatter` and `validate-references` are registered and runnable.
- `format-frontmatter` is idempotent; preserves comments + per-line endings; **preserves `publish`/`project`/`x_project` nested bytes while reordering** (examples with `project:` format clean); enforces the denylist; scaffolds schema-valid blocks and **reports them distinctly**; skips genuinely-unsupported YAML (anchors/merge/block-scalars) safely; `--stdin` round-trips; **skips when a custom schema is configured**.
- `validate-references` is opt-in; implements all checks with the specified levels and exit codes; dangling = warning; `applies_to` raises no dangling warning; `superseded_by: null` is not flagged; repo-root-relative paths and exact ids resolve, absolute paths/anchors do not. It accepts the forwarded `--schema`/`--no-require-frontmatter`/`--glob` flags (skip-with-note under a custom schema), so `project-standards validate --schema custom.json --quiet` and `--no-require-frontmatter --quiet` still succeed with `references.enabled: true`.
- `project-standards fix` runs format→id-fix→final-validate and **leaves `project-standards validate` clean** for `type:`+invalid-id, missing-arrays+invalid-id, and path-inferred-`doc_type` fixtures. The extended `validate` runs `validate-references` when enabled; the **reusable workflow runs it too** (asserted by test). `.pre-commit-hooks.yaml` passes `pre-commit validate-manifest`, every `entry` maps to a real console script, and a `try-repo` smoke runs.
- **No new runtime dependency.** Full toolchain green: `ruff format --check`, `ruff check`, `basedpyright` 0/0/0, `pytest`, `coverage` ≥ the repo's current bar (~91%), `pip-audit`.
- **Dogfood:** the repo's `standards/**` + `meta/**` still pass `validate-frontmatter`; `format-frontmatter --check` on the repo is clean; `references.enabled: true` on this repo passes.
- Docs updated: `standards/markdown-frontmatter/README.md` + `adopt.md` (formatter, references, `fix`, pre-commit), `src/project_standards/README.md`, `CHANGELOG.md`; `deployed.md` + `state.md` on release.

## Non-goals

- No `ruamel.yaml` or any new runtime dependency.
- No reformatting of the document **body** — only the frontmatter block.
- No editing of **nested extension-object content** — `publish`/`project`/`x_project` blocks are repositioned as opaque units, never rewritten internally.
- No overriding a **valid** `doc_type` (inference is fill/correct-only — see Decision 5).
- No auto-fix for unknown-key removal, `id` uniqueness, references, or dates (B is check-only).
- No future-date validation.
- No configurable path-inference rules (only the standard's fixed `index`/`research` rules).
- No in-place editing of consumer config files.
- Not a major version — additive and opt-in (`2.1.0`).

## Open implementation questions (for the plan, not blockers)

- Exact comment-attachment rule (leading blank/comment lines → following key) and exact more-indented-continuation capture for nested extension objects — validate against real fixtures including the `id: '…'  # frozen` precedent and the shipped `project:` examples.
- Where to extract the shared `slugify` + base36-token generator so both `validate_id` and `format_frontmatter` use one copy (likely a small `id_format.py`); `cli.py` already imports both modules.
- Minimum `pre-commit` version to pin in docs; final `types`/`pass_filenames` tuning confirmed via `try-repo`.
- Confirm the coverage target the release must hold (current bar ~91%).
