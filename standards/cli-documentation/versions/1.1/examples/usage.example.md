---
schema_version: '1.1'
id: 'reference-e8r2vy-cli-usage-worked-example'
title: 'CLI Usage Reference — Worked Example'
description: 'Trimmed, validated worked example of the CLI Documentation Standard usage-reference format, derived from docs/usage.md in this repository.'
doc_type: 'reference'
status: 'active'
created: '2026-07-07'
updated: '2026-07-07'
reviewed: null
owner: ''
consumer: 'mix'
tags:
  - 'cli'
  - 'usage'
  - 'example'
aliases:
  - 'cli-usage-worked-example'
related:
  - 'standards/cli-documentation/README.md'
source: []
confidence: 'high'
visibility: 'public'
license: null
---

# project-standards

_This is a trimmed worked example of the [CLI Documentation Standard](../README.md)'s canonical usage-reference format. It derives from this repository's V5 command surface, kept down to `NAME`, `SYNOPSIS`, `DESCRIPTION`, four representative commands, `EXIT STATUS`, two examples, one standalone-command entry, and `SEE ALSO`—enough to show the section registry and option-entry shape without reproducing the whole reference._

## NAME

`project-standards` — validate and fix managed Markdown frontmatter, work with project specs, and materialize packaged standard artifacts.

## SYNOPSIS

```text
project-standards <command> [<args>...]
project-standards validate [<file>...] [--config <path>] [--schema <path>] [--glob <pattern>] [--no-require-frontmatter] [--quiet]
project-standards fix [<file>...] [--config <path>] [--glob <pattern>] [--quiet]
project-standards init --catalog <major> [--migrate] [--apply]
project-standards reconcile [--check | --apply | --recover]
project-standards adopt <standard>... [--dest <dir>] [--force] [--dry-run]
project-standards list [--json]
project-standards spec <verb> [<args>...]
project-standards {--help | --version}
```

## DESCRIPTION

`project-standards` is the unified command-line surface for this repository's tooling. V5 adds neutral control-plane initialization, package selection, reconciliation, provider rendering, and package validation while retaining frontmatter, specification, agent-handoff, and legacy adoption commands under one entry point.

Under unified authority, `validate` and `fix` invoke the exact selected Markdown Frontmatter package providers and effective options. Without `.standards/`, the warned V5 legacy path runs the standalone validator family against `.project-standards.yml`. The six standalone console scripts documented under [Standalone commands](#standalone-commands) remain installed for focused diagnosis and compatibility.

Profile selection (recorded adopter judgment, per the CLI Documentation Standard §3): **Packaged**—the command groups are documented on one usage page because the hierarchy remains navigable without generated per-command pages.

Output goes to standard output for success and results; validation violations, notes, and error summaries go to standard error. There is no interactive prompt; every command is non-interactive and driven entirely by arguments.

`--version` is recognized only as the **first** argument (`project-standards --version`). Because `validate`, `fix`, and `spec` are dispatched before the top-level argument parser runs, a `--version` placed after a subcommand is handled by that subcommand, not the top level.

## OPTIONS

Each leaf command is documented below with its own synopsis, options, and exit status. Every `[project.scripts]` key is a public command.

### `validate`

Run `validate-frontmatter` (schema), `validate-id` (id format), and `validate-references` (cross-file, opt-in) over the configured file set. All three run; the worst exit code is returned, so a schema error, an id violation, or a reference error is never masked by another tool's success.

```text
project-standards validate [<file>...] [--config <path>] [--schema <path>] [--glob <pattern>] [--no-require-frontmatter] [--quiet]
```

Options (all flags are forwarded unchanged to every validator):

- **`<file>...`** — Zero or more Markdown files to validate. With no files, globs, or config includes, the underlying validators default to all `**/*.md` under the current directory.
- **`--config <path>`** — Explicit read-only legacy/debug config. Unified repositories resolve authority from `.standards/` and reject this override; a named nonexistent file is an operator error (exit 2).
- **`--schema <path>`** — Custom JSON Schema to validate against. Frontmatter-only, and it also causes `validate-id` to skip (a custom schema may use a different id convention). Environment/config interaction: overrides the config's `markdown.frontmatter.schema`.
- **`--glob <pattern>`** — Glob (relative to the current directory) to validate instead of the config include list; combines with explicit `<file>` arguments. Note: this scopes `validate-frontmatter` and `validate-id`, but `validate-references` ignores it and always indexes the full configured set.
- **`--no-require-frontmatter`** — Do not fail files that have no frontmatter block. Frontmatter-only; no effect on the id or reference passes.
- **`-q`, `--quiet`** — Suppress per-file success output. Exit code is unaffected.

Exit status: `0` all valid · `1` validation findings · `2` operator error (missing config, bad schema, registry problem).

### `fix`

Format frontmatter (`format-frontmatter --write`), fix ids (`validate-id --fix`), then re-validate against the same contract as `validate` (references included), so a "successful" fix cannot hide a remaining error.

```text
project-standards fix [<file>...] [--config <path>] [--glob <pattern>] [--quiet]
```

Options:

- **`<file>...`** — Markdown files to fix. Omit to use the config include list.
- **`--config <path>`** — Explicit legacy/debug config. It cannot override active `.standards/` authority; a named nonexistent file exits 2.
- **`--glob <pattern>`** — Glob to select files instead of the include list; combines with explicit `<file>` arguments. Forwarded to each stage.
- **`-q`, `--quiet`** — Suppress per-file output.

Safety: `fix` writes to disk (frontmatter reformatting and id rewrites are in-place, atomic, mode-preserving). It skips entirely, with a note on standard error and exit 0, when a custom schema is in use (via `--schema` in the config or a config-level schema path) — custom-schema repos own their own id and format conventions.

Exit status: `0` success (or skipped under a custom schema) · `1` findings remain after the fix · `2` operator error (missing/broken config).

### `adopt`

Materialize one or more standards' artifacts into a destination directory. Runs a registry/bundle parity guard before planning, so drifted metadata fails cleanly instead of writing a partial result.

```text
project-standards adopt <standard>... [--dest <dir>] [--force] [--dry-run]
```

Options:

- **`<standard>...`** — One or more standard ids to adopt (for example `markdown-frontmatter`, `python-tooling`, `markdown-tooling`, `adr`, `cli-documentation`). Required.
- **`--dest <dir>`** — Destination directory to write artifacts into. Default: the current directory. Must already exist unless `--dry-run` is given (a non-existent `--dest` without `--dry-run` exits 2).
- **`--force`** — Overwrite existing files that would otherwise be skipped. Safety: destructive — it replaces on-disk files; prefer `--dry-run` first.
- **`--dry-run`** — Show what would be written without making any changes. Depends on nothing; when set, a non-existent `--dest` is accepted because nothing is written.

Exit status: `0` success · `1` a file write failed · `2` invalid invocation, non-directory `--dest`, or registry/bundle drift · `3` a standard's bundle manifest is missing or malformed.

### `list`

List standards that have packaged adopt artifacts. Applies the same registry/bundle parity guard as `adopt` before emitting anything.

```text
project-standards list [--json]
```

Options:

- **`--json`** — Emit the standards, their contract versions, and their artifacts as a JSON array instead of the default human-readable listing. Default: off (text).

Exit status: `0` success · `2` registry/bundle drift.

## EXIT STATUS

The table gives the repository-wide convention; per-command deviations are noted in each command's entry above.

| Code | Meaning                                                                    |
| ---- | -------------------------------------------------------------------------- |
| `0`  | Success                                                                    |
| `1`  | Findings — validation errors, remaining fix errors, or a not-found extract |
| `2`  | Operator error — bad invocation, missing/broken config, registry drift     |
| `3`  | Missing or malformed bundle manifest (`adopt` only)                        |

`spec lint` returns `1` only with `--strict`. `adopt` is the only command that reaches `3`. The top-level dispatcher returns the selected subcommand's code and falls back to argparse's exit `2` for an unknown command.

## EXAMPLES

### Validate the whole configured file set

```bash
uv run project-standards validate
```

### Preview reconciliation without writing anything

```bash
uv run project-standards reconcile
```

## Standalone commands

Six console scripts are installed alongside `project-standards`. Each is a separate `[project.scripts]` entry point and therefore a public command. In unified repositories the aggregate subcommands use selected package providers; the standalone forms remain for focused diagnosis and legacy compatibility.

### `validate-frontmatter`

The schema half of the Markdown Frontmatter Standard: detects a leading YAML frontmatter block, parses it safely, and validates it against the project's JSON Schema. This is also the hub the other validators import their primitives from. Unified equivalent: `project-standards validate` runs this first.

```text
validate-frontmatter [<file>...] [--version] [--schema <path>] [--glob <pattern>] [--config <path>] [--no-require-frontmatter] [--quiet]
```

Options:

- **`<file>...`** — Markdown files to validate. With no files, globs, or config includes, defaults to all `**/*.md` under the current directory.
- **`--version`** — Print the version and exit 0.
- **`--schema <path>`** — JSON Schema file to validate against; overrides the config schema.
- **`--glob <pattern>`** — Validate files matching the pattern (relative to the current directory) instead of the config include list; combines with explicit files.
- **`--config <path>`** — Explicit legacy/debug config. It cannot override active `.standards/` authority; a named nonexistent file exits 2.
- **`--no-require-frontmatter`** — Do not fail files with no frontmatter block.
- **`-q`, `--quiet`** — Suppress success output.

Exit status: `0` all matched files valid (or none matched) · `1` validation errors · `2` operator error (config, schema, registry, or invocation).

## SEE ALSO

- [`standards/cli-documentation/README.md`](../README.md) — the standard this document conforms to.
- [`src/project_standards/README.md`](https://github.com/L3DigitalNet/project-standards/blob/main/src/project_standards/README.md) — the package's implementation and developer reference.
