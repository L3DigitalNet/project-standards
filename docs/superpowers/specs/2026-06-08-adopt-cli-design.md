# Design: `adopt` CLI — packaged scaffolder for the `project-standards` standards

**Date:** 2026-06-08 **Status:** approved (brainstorming complete; awaiting implementation plan) **Author:** session 2026-06-08

## Problem / Goal

This repo ships two enforcement modalities — a packaged Python validator (`validate-frontmatter`, schema bundled in the wheel) and reusable `workflow_call` workflows — but only **two of the four released standards** actually ship enforcement tooling. The other two are prose a human copies by hand:

| Standard | Distributed tooling today |
| --- | --- |
| markdown-frontmatter | validator console script + reusable `validate-markdown-frontmatter.yml` |
| adr | frontmatter-validated only — no generator, no relationship checks |
| markdown-tooling | reusable `lint-markdown.yml` (markdownlint only); Prettier/EditorConfig are copy-adopt |
| python-tooling | copy-adopt configs + a hand-authored six-step gate; no reusable workflow, no scaffolder |

Manual copy-adopt is exactly what drifts. The goal is a **packaged `adopt` command** that materializes a chosen standard's canonical artifacts into a consumer repository, converting the two doc-only standards into real tooling and giving every standard a single, discoverable front door.

The command must be agent/CI-safe (no interactive prompts, idempotent, deterministic exit codes) and must never destroy a consumer's hand-tuned files.

## Decisions (locked during brainstorming)

1. **Scope = all four released standards, selectable at adopt time.** A single tool with the standards chosen as positional args — not four separate console scripts (which would fragment install/docs/discovery). `python-coding` is excluded (not a released standard).
2. **Command surface = a unified `project-standards` CLI** with subcommands, chosen over a second console script or a subcommand bolted onto `validate-frontmatter`. Rationale: this is the `git`/`uv`/`ruff`/`gh` shape, expandable on two independent axes without new entry points — a **new capability** is a new subcommand; a **new standard** is a new registry entry. The existing `validate-frontmatter` entry point is **kept as a back-compat alias**.
3. **Conflict policy = skip-if-exists by default, `--force` to overwrite.** Never clobber an existing consumer file by default; write only what is missing and print a summary of created vs skipped. Idempotent and re-runnable.
4. **`pyproject.toml` is reported, never edited.** python-tooling contributes TOML *fragments*, not a whole file, and a Python consumer almost always already has a `pyproject.toml`. The CLI prints the missing sections for the user to merge; it performs **no in-place TOML editing** (no round-trip TOML-writer dependency, zero risk to hand-tuned metadata).
5. **Canonical content lives in bundled template files; READMEs reference them.** Every scaffold currently pasted inline in a standard README is extracted into a real file under that bundle, packaged into the wheel, and the README links to it. One drift-proof source of truth.
6. **Engine = declarative per-bundle manifest (`adopt.toml`).** A generic engine reads each standard's manifest; adding a standard is **data, not code**. The same manifest is deliberately shaped to feed the future `check` (drift) command.

### Supersedes a prior decision

This design **reverses Decision #2 of the bundle-restructure spec** (`2026-06-06-standards-bundle-restructure-design.md`), which kept python-tooling's scaffolds inline as fenced code "not extracted into template files." Extracting them is now a prerequisite for `adopt` to have a canonical source to copy, and is in scope here (§4).

## Invariants — the consumer contract (must NOT change)

- The reusable workflows pinned by exact filename: `.github/workflows/validate-markdown-frontmatter.yml`, `.github/workflows/lint-markdown.yml` (`workflow_call`). Renaming = breaking.
- The Python package `project_standards`, the **existing `validate-frontmatter` console-script entry point** (kept as an alias), and the bundled schema at `src/project_standards/schemas/markdown-frontmatter.schema.json` (the path is the schema's own `$id`).
- All published git tags (`v1.x`, `v2.x`, the moving `v1`/`v2`).
- The `.project-standards.yml` config shape consumed by the validator.

## Component 1 — CLI surface & entry points

New module `src/project_standards/cli.py` with an `argparse` subcommand dispatcher exposed as `main()`:

```text
project-standards adopt <standard>... [--dest PATH] [--force] [--dry-run]
project-standards validate ...      # delegates to the existing validate_frontmatter logic
project-standards list              # lists adoptable standards and the artifacts each ships
```

- **Positional `<standard>...`** — one or more of `markdown-frontmatter`, `adr`, `markdown-tooling`, `python-tooling`. An unknown id is a usage error → exit **2**.
- **`--dest PATH`** — target repo root (default: current working directory).
- **`--force`** — overwrite existing files instead of skipping them. Does **not** cause `fragment` artifacts to be written (those are always reported, never written).
- **`--dry-run`** — print the resolved plan and write nothing.

`pyproject.toml` `[project.scripts]`:

```toml
[project.scripts]
project-standards = "project_standards.cli:main"
validate-frontmatter = "project_standards.validate_frontmatter:main"   # retained back-compat alias
```

The `validate` subcommand calls the same entry logic as the standalone alias, so there is a single implementation with two invocation paths.

## Component 2 — Manifest format (`adopt.toml`, one per bundle)

Each `standards/<id>/` gains an `adopt.toml` the engine reads. Adding a standard is data, not code.

```toml
[standard]
id = "markdown-tooling"

[[artifact]]
kind = "file"             # copy source -> dest; skip if dest exists (unless --force)
source = "templates/.markdownlint.json"
dest = ".markdownlint.json"

[[artifact]]
kind = "workflow-caller"  # file copy, but {{ref}} in the body is substituted with the
source = "templates/lint-markdown.caller.yml"   # current released major tag (derived from
dest = ".github/workflows/lint-markdown.yml"    # the package version — never hardcoded)

[[artifact]]
kind = "fragment"         # NEVER written; printed in the report for the user to merge
source = "templates/pyproject.python-tooling.toml"
target = "pyproject.toml"
```

Three `kind`s cover every artifact this repo ships:

- **`file`** — verbatim copy, skip-if-exists semantics.
- **`workflow-caller`** — a `file` whose body contains a `{{ref}}` placeholder substituted at write time with the current released **major** tag (e.g. `@v2`), derived from the package version so the pin is never hardcoded in the template.
- **`fragment`** — a snippet that belongs *inside* an existing file (`pyproject.toml`). Always reported, never written.

The version-ref derivation reuses the package version (`importlib.metadata.version("project-standards")`), taking its major component.

## Component 3 — Engine flow

1. **Resolve** requested standard ids against the bundled manifests (loaded via `importlib.resources`). Unknown id → exit **2**.
2. **Plan** — flatten the artifacts of all requested standards into one deduplicated action list. The same `dest` requested by two standards (e.g. `.editorconfig` from both python-tooling and markdown-tooling) collapses to a single action **iff** the sources are byte-identical; the same `dest` with **differing** sources is a hard error → exit **2** (it indicates a manifest bug, surfaced loudly rather than silently picking one).
3. **Classify** each action: `create` / `skip (exists)` / `overwrite (--force)` / `fragment-report`.
4. **Execute** — create parent directories as needed; write `file`/`workflow-caller` actions; collect `fragment` actions for the report. `--dry-run` skips all writes.
5. **Report** — print a grouped summary: created, skipped (already present), overwritten, and "add these sections to `pyproject.toml`" fragments printed verbatim.

Exit codes follow the workspace convention: `0` ok · `2` bad invocation (unknown standard, manifest conflict) · `3` missing prerequisite. `1` is reserved (not used by `adopt`).

## Component 4 — Template-extraction refactor (in scope)

Every scaffold currently inline in a README becomes a real file under `standards/<id>/templates/`; the README references it instead of pasting code.

| Standard | Templates extracted / sourced |
| --- | --- |
| markdown-frontmatter | `.project-standards.yml`, `validate-markdown-frontmatter.caller.yml` |
| adr | ADR template (already a file under `adr/templates/`); optional `docs/adr/` seed + index |
| markdown-tooling | `.markdownlint.json`, `.prettierrc.json`, `.editorconfig`, `.vscode/extensions.json`, `lint-markdown.caller.yml` |
| python-tooling | `pyproject.python-tooling.toml` (the reported fragment), `.python-version`, `.editorconfig`, `.vscode/*`, `check.caller.yml`, agent entry-point stubs, `scripts/check.py` |

### Packaging tension to resolve during implementation

The wheel is built from `src/` (precedent: the schema was moved into `src/project_standards/schemas/`). But the bundle architecture and convention 6 keep templates at repo-root `standards/<id>/templates/`. The build must therefore be configured to **force-include** `standards/**/templates/**` (and the `adopt.toml` manifests) as package data reachable at runtime via `importlib.resources` — keeping templates where the architecture mandates while still shipping them in the wheel.

The exact `uv_build` configuration key (e.g. the `[tool.uv.build-backend]` data/force-include mechanism) is an **implementation-time documentation check** against current `uv_build` docs — flagged, not assumed, per the "verify current docs before relying on them" rule. A build-and-inspect-the-wheel step in the plan must confirm the templates and manifests are present in the artifact.

### Dogfooding note

`templates/**` is currently **excluded** from frontmatter validation in `.project-standards.yml` (placeholders that don't satisfy the schema's date/id patterns). The extracted config files (`.markdownlint.json`, `.toml`, `.yml`, etc.) are not Markdown and are unaffected. No change to the validator's include/exclude globs is required.

## Component 5 — Testing

Per the Python Tooling SSOT gate (coverage ≥ 85, basedpyright strict):

- **Unit:** manifest parsing; plan flattening + dedupe; conflicting-dest detection (exit 2); skip / `--force` / `--dry-run` classification; `{{ref}}` substitution from package version; `fragment` reporting; unknown-standard exit code.
- **Integration:** `adopt` into a `tmp_path` →
  - first run creates all expected files;
  - re-run leaves every file unchanged and reports all as skipped (idempotency);
  - `--force` overwrites a modified file back to canonical;
  - a pre-existing `pyproject.toml` → the python-tooling fragment is **reported, not written**;
  - `--dry-run` writes nothing.
- **Dogfood test:** assert this repo's own root configs (`.markdownlint.json`, `.prettierrc.json`, `.editorconfig`, …) are byte-identical to the corresponding bundled templates. This is the ultimate dogfood and pre-emptively closes the drift loop the future `check` command will police.
- **Packaging test:** build the wheel and assert the templates + manifests are present and loadable via `importlib.resources`.

## Non-goals

- **The `check` (drift) command** — separate spec. The manifest is deliberately designed to feed it, but it is not built here.
- **In-place TOML/YAML merging** — explicitly rejected (Decision #4).
- **Interactive prompts** — `adopt` is non-interactive for CI/agent use.
- **A from-zero project generator** beyond dropping the listed artifacts.
- **`python-coding`** — not a released standard.

## Versioning impact

Additive: a new subcommand, a new entry point (existing one retained as an alias), and relocated-but-byte-unchanged template content. Consumers pin git tags and reusable-workflow filenames, not template file paths, so nothing in the consumer contract breaks. → **minor bump, `2.1.0`.**

## Open implementation questions (for the plan, not blockers)

1. Exact `uv_build` force-include configuration and a wheel-inspection verification step (§4).
2. Whether `list` output is plain text or `--json` (lean: plain text now; `--json` is trivial to add later and not required for the gap this closes).
3. Final on-disk template filenames for the caller stubs (`*.caller.yml`) versus reusing the exact deployed filename — the manifest `dest` decouples source name from destination name, so this is cosmetic.
