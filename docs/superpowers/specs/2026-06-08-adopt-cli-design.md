# Design: `adopt` CLI — packaged scaffolder for the `project-standards` standards

**Date:** 2026-06-08 **Status:** approved (brainstorming complete; codex-review rounds 1–2 applied; awaiting plan) **Author:** session 2026-06-08

## Problem / Goal

This repo ships two enforcement modalities — a packaged Python validator (`validate-frontmatter`, schema bundled in the wheel) and reusable `workflow_call` workflows — but only **two of the four released standards** ship a *programmatic adoption path*. The other two are prose a human copies by hand:

| Standard | Distributed tooling today |
| --- | --- |
| markdown-frontmatter | validator console script + reusable `validate-markdown-frontmatter.yml` |
| adr | frontmatter validation **+ opt-in MADR body-section check + FM→ADR compatibility gate** (validator-enforced); lacks a generator / index / relationship tooling |
| markdown-tooling | reusable `lint-markdown.yml` (markdownlint only); Prettier/EditorConfig are copy-adopt |
| python-tooling | copy-adopt configs + a hand-authored six-step gate; no reusable workflow, no scaffolder |

Manual copy-adopt is exactly what drifts. The goal is a **packaged `adopt` command** that materializes a chosen standard's canonical artifacts into a consumer repository, converting the two doc-only standards into real tooling and giving every standard a single, discoverable front door.

The command must be agent/CI-safe (no interactive prompts, idempotent, deterministic exit codes, path-safe) and must never destroy or write outside a consumer's tree.

## Decisions (locked during brainstorming; refined by codex-review round 1)

1. **Scope = all four released standards, selectable at adopt time**, and adopting any combination — including all four together — is a **required, supported workflow** (not a degenerate edge case). `python-coding` is excluded (not a released standard).
2. **Command surface = a unified `project-standards` CLI** with subcommands (`adopt`, `validate`, `list`), chosen over a second console script or a subcommand on `validate-frontmatter`. This is the `git`/`uv`/`ruff`/`gh` shape — new capability = new subcommand; new standard = new bundle. The existing `validate-frontmatter` entry point is **kept as a back-compat alias**.
3. **Conflict policy = skip-if-exists by default, `--force` to overwrite** regular files only. Idempotent and re-runnable.
4. **Existing config files are never edited in place** (no in-place TOML/YAML rewriting, no round-trip-writer dependency). "Edit" means *modifying a file the consumer already has*: the python-tooling `pyproject.toml` sections and the ADR `markdown.adr` `.project-standards.yml` block are `fragment`s — printed for the user to merge, reported whether or not the target exists, never written. **Writing a whole brand-new starter file when none exists** is *not* an edit — that is the ordinary `kind=file` skip-if-exists path (e.g. the markdown-frontmatter `.project-standards.yml` starter is written only when absent, skipped when present).
5. **Canonical content + manifests live under the package** at `src/project_standards/bundles/<id>/`, resolved at runtime by a `Path(__file__).parent`-relative lookup — the **same proven, wheel-safe pattern the bundled schema and `registry.json` already use** (`src/project_standards/schemas/`). This supersedes the round-0 idea of keeping canonical templates at repo-root `standards/<id>/templates/`; see "Supersedes" below. The repo-root `standards/<id>/` READMEs *reference* the packaged files.
6. **Engine = declarative per-bundle manifest (`adopt.toml`).** A generic engine reads each standard's manifest; adding a standard is **data, not code**. The manifest is deliberately shaped to also feed a future `check` (drift) command.
7. **Canonical templates are sourced from the repo's real working files, and extraction is *semantic*, not byte-copy.** The canonical source for each template is the repo's actual functioning config (e.g. root `.github/workflows/check.yml`, root `.editorconfig`, root `.markdownlint.json`) — **not** the code fence rendered inside a README/`adopt.md`. This matters because this repo's Prettier config emits **tabs**, so YAML fences in prose are tab-indented, but YAML forbids tabs in indentation; the real workflow files use spaces and are valid. Every generated `.yml`/`.yaml`/`.json`/`.toml` artifact must therefore be syntactically valid and is parse-validated after generation (Component 6). The round-0 "byte-unchanged" framing is dropped.
8. **Shared artifacts have a single canonical owner, and the shared `.editorconfig` is a deliberate reconciled policy.** Files more than one standard needs (`.editorconfig`, `.vscode/extensions.json`) are stored once as a **superset** under a shared bundle and *referenced* by each standard's manifest — never copied divergently. Deduplication is by shared identity, not content comparison. The shared `.editorconfig` is the repo's **root `.editorconfig`** (the real superset both standards coexist under in this repo): it keeps Python Tooling's `[*.py]` and TOML space rules and the 2-space YAML rule, and adopts the Markdown Tooling floor (global `indent_style = tab`, so JSON/Markdown are tab-indented to match Prettier). This **deliberately changes** Python Tooling's previously *documented* §14 `.editorconfig` (which specified spaces for `*.{toml,yml,yaml,json,md}`) for the JSON/Markdown case. Because Python Tooling is copy-adopt — never inherited automatically — this cannot newly-fail an existing consumer; for the standard's contract it is a clarifying/minor change. Python Tooling's §14 prose and the versioning impact are updated to say so, and Python-only / Markdown-only / combined adoption are each tested.
9. **Templates fall into two classes** — *dogfoodable root artifacts* and *curated consumer scaffolds* — because some of this repo's real files are repo-specific and unsafe to ship to consumers. Decision #7's "source from the real working file" rule applies **only** to dogfoodable artifacts (see Component 5). Curated scaffolds are authored generic and exempted from the byte-identical dogfood test.
10. **`adopt` only materializes files with a single unambiguous owner or a safe *additive* union.** Files that more than one standard would each contribute *into* — `AGENTS.md`, `CLAUDE.md`, `.vscode/settings.json`, `.vscode/tasks.json` — are **not** auto-merged (merging two standards' editor settings or agent instructions into one file is the cross-standard leak this rule prevents). `.vscode/extensions.json` is the one safe union (a list of recommendations) and ships as a shared superset. The agent stub (`AGENTS.md`/`CLAUDE.md`) has exactly one owner — python-tooling, curated, skip-if-exists; other standards' agent/settings blocks remain **illustrative** in their docs (documented manual steps), and `.vscode/settings.json`/`tasks.json` are **out of adopt scope** (manual copy from the standard). This keeps single-standard adoption from silently inheriting another standard's behavior.

### Supersedes prior decisions

- **Reverses round-0 §4 of this spec** (canonical templates at repo-root `standards/<id>/templates/`, and the "byte-unchanged" framing). Codex SA-002 confirmed `uv_build` does not support force-including an arbitrary root tree as importable package resources; the repo's working precedent is data files under `src/project_standards/` resolved relative to `__file__`. Templates therefore move under the package, sourced semantically from the repo's real working files; the bundle READMEs reference them.
- **Reverses Decision #2 of the bundle-restructure spec** (`2026-06-06-standards-bundle-restructure-design.md`), which kept python-tooling's scaffolds inline. Extracting them is a prerequisite for `adopt` to have a canonical source.

## Invariants — the consumer contract (must NOT change)

- The reusable workflows pinned by exact filename: `.github/workflows/validate-markdown-frontmatter.yml`, `.github/workflows/lint-markdown.yml` (`workflow_call`). Renaming = breaking.
- The Python package `project_standards`, the **existing `validate-frontmatter` console-script entry point** (kept as an alias), the bundled schema at `src/project_standards/schemas/markdown-frontmatter.schema.json` (the path is the schema's own `$id`), and the bundled `registry.json` + its `Registry` reader.
- All published git tags (`v1.x`, `v2.x`, the moving `v1`/`v2`).
- The `.project-standards.yml` config shape consumed by the validator (including the `markdown.adr` block).

## Component 1 — CLI surface & entry points

New module `src/project_standards/cli.py` with an `argparse` subcommand dispatcher exposed as `main()`:

```text
project-standards adopt <standard>... [--dest PATH] [--force] [--dry-run]
project-standards validate ...      # delegates to the existing validate_frontmatter logic
project-standards list [--json]     # lists adoptable standards and the artifacts each ships
```

- **Positional `<standard>...`** — one or more of `markdown-frontmatter`, `adr`, `markdown-tooling`, `python-tooling`. Unknown id → exit **2**. The set of valid ids is cross-checked against the bundled standards (the same standards the existing `registry.py` knows), so the two never drift.
- **`--dest PATH`** — target repo root (default: CWD). Must be an existing directory → otherwise exit **2**.
- **`--force`** — overwrite existing **regular** files instead of skipping. Never writes through a symlink (see Safety contract). Never causes a `fragment` to be written.
- **`--dry-run`** — print the resolved plan and write nothing. Exit **0**.

`pyproject.toml` `[project.scripts]`:

```toml
[project.scripts]
project-standards = "project_standards.cli:main"
validate-frontmatter = "project_standards.validate_frontmatter:main"   # retained back-compat alias
```

The `validate` subcommand calls the same entry logic as the standalone alias — one implementation, two invocation paths.

## Component 2 — Manifest format (`adopt.toml`, one per bundle)

Each `src/project_standards/bundles/<id>/` gains an `adopt.toml` the engine reads.

```toml
[standard]
id = "markdown-tooling"

[[artifact]]
kind = "file"                  # copy source -> dest; skip if dest exists (unless --force)
owner = true                   # this standard is the sole source of this dest
source = ".markdownlint.json"  # relative to this bundle dir
dest = ".markdownlint.json"    # relative to --dest; must be safe (see Safety contract)

[[artifact]]
kind = "file"                  # SHARED superset file owned by the _shared bundle
shared = "_shared/.editorconfig"   # canonical path under bundles/; referenced, not copied here
dest = ".editorconfig"

[[artifact]]
kind = "workflow-caller"       # file copy, but {{ref}} -> current released major tag (e.g. @v2)
owner = true
source = "lint-markdown.caller.yml"
dest = ".github/workflows/lint-markdown.yml"

[[artifact]]
kind = "fragment"              # NEVER written; printed in the report for the user to merge
owner = true
source = "pyproject.python-tooling.toml"
target = "pyproject.toml"
```

Artifact attributes:

- **`kind`** — `file` (verbatim copy, skip-if-exists), `workflow-caller` (a `file` whose body contains a `{{ref}}` placeholder substituted at write time with the current released **major** tag, derived from `importlib.metadata.version("project-standards")` so the pin is never hardcoded; used **only** by standards that ship a reusable workflow — markdown-frontmatter and markdown-tooling), or `fragment` (a snippet belonging *inside* an existing file; always reported, never written).
- **`owner = true`** vs **`shared = "<path>"`** — an *owned* artifact is sourced from this bundle; a *shared* artifact references a single canonical file under `bundles/_shared/`. Multiple standards may reference the same `shared` file; it is emitted once.

`workflow-caller` is reserved for genuine reusable-workflow callers. Python Tooling has **no** reusable workflow, so its `check.yml` is a plain `kind = "file"` standalone workflow (space-indented, parse-valid), not a caller.

**`fragment` targets** are not limited to `pyproject.toml`. The ADR standard's `markdown.adr` knobs for `.project-standards.yml` are also a `fragment` (`target = ".project-standards.yml"`) — reported, never written — for the same reason TOML is: the CLI does no in-place YAML/TOML editing. This keeps a single fragment mechanism across both config files.

### Shared / superset artifacts

`.editorconfig` and `.vscode/extensions.json` are needed by both python-tooling and markdown-tooling but are **not** byte-identical in the repo today (root `.editorconfig` is `indent_style = tab` globally; python-tooling's inline copy uses spaces; VS Code extension lists differ). They become **superset** files under `bundles/_shared/`: a single `.editorconfig` carrying the union of per-language rules (the repo's current root `.editorconfig` already is this superset), and a single `extensions.json` recommending the union of all standards' extensions. Each standard's manifest references the shared file; selecting both standards emits it once.

## Component 3 — Engine flow & exit codes

1. **Resolve** requested ids against the bundled standards. Unknown id → exit **2**.
2. **Plan** — flatten artifacts of all requested standards into one action list, resolving `shared` references to their single canonical source. Identity is the resolved source path, so a `shared` file referenced by two standards collapses to one action. Two **owned** artifacts targeting the same `dest` is an authoring bug → exit **2** (surfaced loudly).
3. **Validate safety** of every action against the Safety contract (below). Any violation → exit **2**.
4. **Classify** each action: `create` / `skip (exists)` / `overwrite (--force)` / `skip (symlink, never written)` / `fragment-report`.
5. **Execute** — create parent directories under `--dest`; write `file`/`workflow-caller` actions; collect `fragment` actions for the report. `--dry-run` skips all writes.
6. **Report** — grouped summary: created, skipped (already present), overwritten, symlink-skipped, and fragments **grouped by target file** under a per-target heading ("Add these sections to `<target>`:") — so the `pyproject.toml` and `.project-standards.yml` fragments are reported distinctly, each printed verbatim.

**Exit-code contract** (resolves the round-1 ambiguity):

| Code | Meaning | Cases |
| --- | --- | --- |
| `0` | Success | normal run, all-skipped run, and `--dry-run` |
| `1` | Recoverable runtime / I-O failure | permission denied, unwritable `--dest`, partial-write failure |
| `2` | Bad invocation / authoring error | unknown standard; `--dest` not an existing directory; two owned artifacts → same dest; unsafe manifest path (`..`, absolute, escapes `--dest`); bad args |
| `3` | Missing prerequisite | a manifest-referenced template/manifest absent from the package; package version unresolvable via `importlib.metadata` |

This mirrors the workspace convention (`0` ok · `1` recoverable · `2` bad invocation · `3` missing prereq) and the validator's existing use of exit 2 for operator/packaging errors (`RegistryError`, `ConfigError`).

## Component 4 — Safety contract (write-boundary rules)

Because the engine treats manifest *conflicts* as bugs worth failing on, manifest *safety* is in scope too:

- **Destination paths** (`dest`, `target`) must be **relative** and must normalize to a path **contained under `--dest`**. Reject absolute paths and any `..` traversal → exit **2**. The containment check uses the realpath of `--dest` and refuses any resolved target that escapes it.
- **Source paths** (`source`, `shared`) must resolve **inside the package bundle tree**; a source escaping the bundle, or absent from the package, is exit **3**.
- **Symlinks:** if an existing `dest` is a symlink, it is treated as "exists" and **skipped — even under `--force`** (the engine never writes *through* a symlink, so it cannot clobber a file outside `--dest`). Reported in the symlink-skipped group.
- **I-O errors** (permission denied, read-only filesystem) map to exit **1**, not a stack trace.
- **Atomic writes:** each `file`/`workflow-caller` artifact is written to a temp file in the **target directory**, then `os.replace`d into place only after the full write succeeds. A mid-write failure leaves any existing destination **intact** (a failed `--force` never truncates the original) and removes the temp file; the command exits **1**. A failure-injection test asserts this.

## Component 5 — Template-extraction refactor (in scope)

Every scaffold currently pasted inline **in a standard README *or* its `adopt.md`** becomes a single canonical file under `src/project_standards/bundles/<id>/` (or `bundles/_shared/`); the prose then **references** that file instead of duplicating it. Extraction is **semantic** (generated YAML/JSON/TOML must parse, Component 6), and each template belongs to one of two source classes (Decision #9):

- **Dogfoodable root artifacts** — generic, repo-agnostic config whose canonical source *is* the repo's real working file (valid by construction). The byte-identical dogfood test applies. These are: `.markdownlint.json`, `.prettierrc.json`, shared `.editorconfig`, shared `.vscode/extensions.json`, `check.yml`, `.python-version`, `scripts/check.py`. (`.vscode/settings.json`/`tasks.json` are **not** in this set — they are out of adopt scope per Decision #10.)
- **Generated workflow-caller stubs** — `validate-markdown-frontmatter.caller.yml`, `lint-markdown.caller.yml`. These have **no byte-identical root source**: this repo *defines* the reusable workflows (`workflow_call` providers under `.github/workflows/`); it never calls them from itself, and the caller snippets exist only in adopt prose. So they are authored/templated (carry `{{ref}}`), **exempt from the byte-identical dogfood test**, and validated instead by: parses as YAML, references the correct reusable-workflow filename, and substitutes the current major `@vN` ref.
- **Curated consumer scaffolds** — files where this repo's own copy is repo-specific and must **not** be shipped to consumers. Authored generic, exempt from the dogfood test, with their own content tests. These are: the markdown-frontmatter `.project-standards.yml` **starter** (includes consumer paths like `README.md`/`docs/**`, *not* this repo's `standards/**`/`meta/**` scope) and the python-tooling generic `AGENTS.md`/`CLAUDE.md` agent stubs (sourced from the python-tooling README's generic templates, *not* this repo's handoff-v3-specific root `AGENTS.md`/`CLAUDE.md`).

| Standard | Templates materialized by `adopt` | Class |
| --- | --- | --- |
| markdown-frontmatter | `.project-standards.yml` starter (`kind=file`, written only when absent) | **curated** |
| markdown-frontmatter | `validate-markdown-frontmatter.caller.yml` (`kind=workflow-caller`) | generated |
| adr | ADR template → `docs/decisions/adr.template.md` (`kind=file`, skip-if-exists); `markdown.adr` knobs for `.project-standards.yml` (`kind=fragment`, reported) | dogfoodable / fragment |
| markdown-tooling | `.markdownlint.json`, `.prettierrc.json` (`kind=file`); refs shared `.editorconfig`, `.vscode/extensions.json` | dogfoodable |
| markdown-tooling | `lint-markdown.caller.yml` (`kind=workflow-caller`) | generated |
| python-tooling | `pyproject.python-tooling.toml` (`kind=fragment`), `.python-version`, `check.yml` (`kind=file`, standalone workflow, space-indented), `scripts/check.py`; refs shared `.editorconfig`, `.vscode/extensions.json` | dogfoodable |
| python-tooling | `AGENTS.md` / `CLAUDE.md` agent entry-point stubs (`kind=file`, single owner) | **curated** |
| _shared | superset `.editorconfig`, superset `.vscode/extensions.json` | dogfoodable |

**Not materialized (illustrative / manual, per Decision #10):** `.vscode/settings.json` and `.vscode/tasks.json` (per-standard, per-environment — auto-merging leaks behavior across standards), and the markdown-tooling `AGENTS.md`/settings blocks currently inline in its README. These stay as documented copy-from-the-standard steps; their inline blocks are explicitly marked illustrative, and the single-canonical-copy test treats them as out-of-scope (not manifest sources).

**Single-canonical-copy rule:** each manifest `source`/`shared` maps to exactly one file in the package, and the standard's docs link to it rather than re-pasting it. A test enforces this (Component 6). **Python Tooling's §14 `.editorconfig` prose is updated** to reflect the reconciled shared policy (Decision #8) rather than its old spaces-for-JSON/Markdown wording.

### ADR template destination & validation safety

The shipped ADR template carries intentional placeholder frontmatter (`YYYY-MM-DD` dates, `replace-with-stable-id`) that **deliberately fails the schema** — exactly why this repo excludes `standards/**/templates/**` from validation. So `adopt adr` writes it to a **template path that the consumer's validation excludes**: `docs/decisions/adr.template.md`, and the markdown-frontmatter `.project-standards.yml` **starter's `exclude` list covers `**/*.template.md`** (mirroring this repo's own template exclusion). A consumer authors a real ADR by copying the template to `docs/decisions/NNNN-title.md` and filling it in.

**Existing-config safety:** a consumer who already has a `.project-standards.yml` that includes `docs/**/*.md` but lacks the template exclusion would otherwise validate the placeholder template and fail. Because the CLI never edits an existing config in place (Decision #4), the ADR `fragment` for `.project-standards.yml` therefore **also reports the required `markdown.frontmatter.exclude` addition** (`**/*.template.md`) alongside the `markdown.adr` block — so the operator adds both. When `adopt` writes the starter fresh (markdown-frontmatter adopted into a config-less repo), the exclusion is already present. Two integration tests cover this: (a) clean `adopt markdown-frontmatter adr` into a config-less fixture → `validate-frontmatter` **passes**; (b) `adopt adr` against a fixture whose pre-existing config includes `docs/**/*.md` without the exclusion → the report contains the exclude fragment, and applying it makes `validate-frontmatter` pass.

**Packaging:** templates and manifests ship in the wheel automatically because they live under `src/project_standards/` and are loaded by a `Path(__file__).parent / "bundles" / …` lookup — identical resolution from a source checkout and a `uv tool install` wheel, exactly as `registry.py` loads `registry.json` today. No `force-include` and no `importlib.resources` anchor gymnastics required. (A post-implementation wheel-inspection + install-and-run step still confirms presence.)

### Dogfooding note

`templates/**` is currently excluded from frontmatter validation in `.project-standards.yml`. The extracted files now live under `src/project_standards/bundles/**` (non-Markdown configs + a few `.md` agent stubs). The plan must confirm these do not enter the validator's Markdown include globs (they are under `src/`, which the current config does not include), so no glob change is required — verified during implementation.

## Component 6 — Testing

Per the Python Tooling SSOT gate (coverage ≥ 85, basedpyright strict):

- **Unit:** manifest parsing; plan flattening; shared-reference resolution; owned-dest-collision detection (exit 2); skip / `--force` / `--dry-run` classification; `{{ref}}` substitution from package version; `fragment` reporting (target present *and* absent); unknown-standard exit 2; missing-template exit 3.
- **Safety unit tests:** absolute `dest`, `../` traversal, a `dest` escaping `--dest`, a symlink destination (skipped even under `--force`), missing source template (exit 3), non-directory `--dest` (exit 2), permission-denied write (exit 1). **Source-side too:** a manifest with an absolute `source`/`shared`, a `../`-traversing `source`/`shared`, or one resolving outside `src/project_standards/bundles/` → exit **3**, no traceback, no file written.
- **Integration (adoption matrix):** `adopt` into a `tmp_path`, covering each standard alone, `markdown-frontmatter adr`, `markdown-tooling python-tooling`, and all four together →
  - first run creates all expected files; re-run reports all as skipped (idempotency);
  - `--force` overwrites a modified regular file back to canonical;
  - **combined `adopt markdown-tooling python-tooling`** succeeds and emits the shared `.editorconfig` / `.vscode/extensions.json` exactly once; **Python-only** and **Markdown-only** adoption each receive the same shared `.editorconfig` (the reconciled superset), asserting the Decision #8 policy explicitly;
  - a pre-existing `pyproject.toml` → the python-tooling fragment is reported, not written; an absent one → fragment reported with create-it guidance;
  - `adopt adr` and `adopt markdown-frontmatter adr` → the `markdown.adr` block is in the report (under a `.project-standards.yml` target heading) and **no `.project-standards.yml` is edited in place**;
  - **`adopt markdown-frontmatter adr` into a fixture, then `validate-frontmatter --config .project-standards.yml` → passes** (the placeholder `docs/decisions/adr.template.md` is excluded by the starter's `**/*.template.md` rule, proving the ADR template does not break consumer validation);
  - the shared `.vscode/extensions.json` is the union of both standards' recommendations; `.vscode/settings.json`/`tasks.json` are **not** written by `adopt` (Decision #10);
  - `--dry-run` writes nothing.
- **Generated-syntax tests:** every generated `.yml`/`.yaml` artifact parses as YAML and contains **no tab indentation**; every generated `.json`/`.toml` parses. `check.yml` is compared against the valid canonical workflow, never the Markdown-fence bytes.
- **Workflow-caller tests:** each generated caller stub parses as YAML, `uses:` the correct reusable-workflow filename, substitutes the current major `@vN` ref, and is **excluded** from the byte-identical dogfood set (no root caller source exists).
- **Curated-scaffold content tests (Decision #9):** the generated `.project-standards.yml` starter includes generic consumer paths (`README.md`, `docs/**/*.md`), does **not** carry this repo's `standards/**`/`meta/**` scope, and validates a fixture consumer tree; the generated `AGENTS.md`/`CLAUDE.md` stubs contain the generic python-tooling text and **no** `docs/handoff`/project-standards-specific content.
- **Atomic-write failure-injection test:** force a write failure after the temp file is opened and assert the pre-existing destination is unchanged and the command exits 1.
- **Dogfood test (dogfoodable artifacts only):** this repo's root working configs for the *dogfoodable* set (`.markdownlint.json`, `.prettierrc.json`, `.editorconfig`, `.github/workflows/check.yml`, …) are byte-identical to their bundled (`_shared`/standard) templates — the ultimate dogfood and a pre-emptive close of the drift loop the future `check` command will police. **Curated consumer scaffolds are explicitly excluded** from this test (their content differs from this repo's repo-specific copies by design).
- **Single-canonical-copy test:** every `adopt.toml` `source`/`shared` resolves to exactly one packaged file.
- **Packaging test:** build the wheel, assert templates + manifests are present, install from the wheel, and run `project-standards list` and `project-standards adopt … --dry-run` from the installed tool.

## Acceptance criteria

- `project-standards adopt <any subset, incl. all four>` into a clean dir produces the documented files and a correct created/skipped/fragment report; re-run is a no-op; `--force` re-canonicalizes.
- `list` prints every released standard and its artifact destinations (plain text); `--json` emits the same data with a stable schema: an array of standards, each `{id, contract_version, artifacts: [{kind, dest|target, source|shared, owner}]}`.
- Every generated YAML/JSON/TOML artifact is syntactically valid (no tab-indented YAML).
- Invalid manifest (owned dest collision, missing source, unsafe path) fails with the exit code in the Component 3 table — never a traceback.
- The installed-from-wheel tool behaves identically to the source checkout (templates resolve).
- Generated curated scaffolds are **generic**: the `.project-standards.yml` starter targets consumer paths (not this repo's `standards/**`/`meta/**` scope) and the agent stubs carry no repo-specific handoff content.
- A failed `--force` overwrite never corrupts or truncates the existing destination (atomic write); the command exits 1.
- The full SSOT gate stays green; `validate-frontmatter --config .project-standards.yml` still passes.

## Non-goals

- **The `check` (drift) command** — separate spec; the manifest is shaped to feed it.
- **In-place TOML/YAML merging** — explicitly rejected (Decision #4).
- **Interactive prompts.**
- **A from-zero project generator** beyond dropping the listed artifacts.
- **An `adr` generator / `docs/adr/` seed / index / relationship checker** — out of scope here; `adopt adr` only drops the ADR template and the existing config knobs.
- **`python-coding`** — not a released standard.

## Versioning impact

Additive: a new subcommand, a new entry point (existing one retained as alias), and relocated template content. Consumers pin git tags and reusable-workflow filenames, not template file paths, so nothing in the consumer contract breaks. The one normative content change — Python Tooling's documented `.editorconfig` JSON/Markdown indentation reconciled to the shared superset (Decision #8) — is a **clarifying/minor** change to a copy-adopt standard: copy-adopt standards are never inherited automatically, so it cannot newly-fail an existing consumer. → **minor bump, `2.1.0`.** The `CHANGELOG.md` must note (a) the relocation of copy-adopt scaffolds out of README/`adopt.md` sections into packaged bundles, and (b) the Python Tooling `.editorconfig` reconciliation.

## Open implementation questions (for the plan, not blockers)

1. Final on-disk filenames for caller stubs (`*.caller.yml`) — cosmetic, since the manifest `dest` decouples source name from destination name.
2. Exact content of the shared superset `.vscode/extensions.json` (the union of Python + Markdown recommendations) — the union is unambiguous; only ordering is a detail. The shared `.editorconfig` is resolved (Decision #8: the repo root file).
