---
schema_version: '1.1'
id: 'reference-u6b3wn-project-standards-cli-usage'
title: 'project-standards CLI Usage Reference'
description: 'Canonical man-style usage reference for the project-standards command and the six standalone console scripts it ships.'
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
  - 'reference'
aliases:
  - 'project-standards-usage'
related:
  - 'standards/cli-documentation/README.md'
source: []
confidence: 'high'
visibility: 'public'
license: null
---

# project-standards

## NAME

`project-standards` — validate and fix managed Markdown frontmatter, work with project specs, and adopt the repository's copy-adopt standards.

## SYNOPSIS

```text
project-standards <command> [<args>...]
project-standards validate [<file>...] [--config <path>] [--schema <path>] [--glob <pattern>] [--no-require-frontmatter] [--quiet]
project-standards fix [<file>...] [--config <path>] [--glob <pattern>] [--quiet]
project-standards adopt <standard>... [--dest <dir>] [--force] [--dry-run]
project-standards list [--json]
project-standards spec <verb> [<args>...]
project-standards {--help | --version}
```

## DESCRIPTION

`project-standards` is the unified command-line surface for this repository's tooling. It exposes ten leaf commands under one entry point: the two frontmatter operations (`validate`, `fix`), the two adoption operations (`adopt`, `list`), and a nested `spec` command group of six verbs (`validate`, `lint`, `extract`, `next`, `new`, `upgrade`) that operate on project-specification documents.

`validate` and `fix` are thin front ends over the standalone validator family: `validate` runs `validate-frontmatter`, `validate-id`, and `validate-references` in sequence and returns the worst exit code, so a single call checks the whole frontmatter contract; `fix` formats and repairs in place, then re-runs the same check. The six standalone console scripts documented under [Standalone commands](#standalone-commands) remain installed for scripting and back-compatibility.

Profile selection (recorded adopter judgment, per the CLI Documentation Standard §3): **Packaged** — 10 leaf commands plus the `spec` group overview, documented on this single page because the two-group nesting stays navigable at this command count. The deep profile's generated per-command pages are not warranted here.

Output goes to standard output for success and results; validation violations, notes, and error summaries go to standard error. There is no interactive prompt; every command is non-interactive and driven entirely by arguments.

`--version` is recognized only as the **first** argument (`project-standards --version`). Because `validate`, `fix`, and `spec` are dispatched before the top-level argument parser runs, a `--version` placed after a subcommand is handled by that subcommand, not the top level — see [NOTES](#notes).

## OPTIONS

### Global options

- **`-h`, `--help`** — Show help for the tool or the named subcommand and exit 0. Available on every command and subcommand.
- **`--version`** — Print `project-standards <version>` and exit 0. Recognized only as the first argument (see [NOTES](#notes)). Scope: top-level dispatcher.

Each leaf command is documented below with its own synopsis, options, and exit status. Every `[project.scripts]` key is a public command.

### `validate`

Run `validate-frontmatter` (schema), `validate-id` (id format), and `validate-references` (cross-file, opt-in) over the configured file set. All three run; the worst exit code is returned, so a schema error, an id violation, or a reference error is never masked by another tool's success.

```text
project-standards validate [<file>...] [--config <path>] [--schema <path>] [--glob <pattern>] [--no-require-frontmatter] [--quiet]
```

Options (all flags are forwarded unchanged to every validator):

- **`<file>...`** — Zero or more Markdown files to validate. With no files, globs, or config includes, the underlying validators default to all `**/*.md` under the current directory.
- **`--config <path>`** — Project config file. Default: `.project-standards.yml`. A `--config` that names a non-existent file is an operator error (exit 2), never a silent default.
- **`--schema <path>`** — Custom JSON Schema to validate against. Frontmatter-only, and it also causes `validate-id` to skip (a custom schema may use a different id convention). Environment/config interaction: overrides the config's `markdown.frontmatter.schema`.
- **`--glob <pattern>`** — Glob (relative to the current directory) to validate instead of the config include list; combines with explicit `<file>` arguments. Note: this scopes `validate-frontmatter` and `validate-id`, but `validate-references` ignores it and always indexes the full configured set (see [NOTES](#notes)).
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
- **`--config <path>`** — Project config file. Default: `.project-standards.yml`. A non-existent `--config` exits 2.
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

List the adoptable standards and their artifacts. Applies the same registry/bundle parity guard as `adopt` before emitting anything.

```text
project-standards list [--json]
```

Options:

- **`--json`** — Emit the standards, their contract versions, and their artifacts as a JSON array instead of the default human-readable listing. Default: off (text).

Exit status: `0` success · `2` registry/bundle drift.

### `spec`

Command group: `validate | lint | extract | next | new | upgrade` over project specifications (the Project Specification Standard's document format). Running `project-standards spec` with no verb prints usage to standard error and exits 2; `project-standards spec --help` prints usage and exits 0.

```text
project-standards spec {validate | lint | extract | next | new | upgrade} [<args>...]
```

The six verbs are documented individually below. There are no group-level options other than `-h` / `--help`; each verb defines its own flags. An unrecognized verb exits 2.

### `spec validate`

Validate spec documents against the standard; every finding is an error.

```text
project-standards spec validate [<file>...] [--config <config>] [--json] [--strict]
```

Options:

- **`<file>...`** — Spec files to validate. Omit to use the `spec.include` globs from the config.
- **`--config <config>`** — Project config file. Default: `.project-standards.yml`.
- **`--json`** — Emit a JSON findings payload instead of the text `OK`/`FAIL` listing. Default: off.
- **`--strict`** — Accepted for symmetry with `spec lint`; `validate` already fails on any finding, so this flag does not change its exit code.

Exit status: `0` all specs clean · `1` any validation finding (a parse failure is reported as an `SV-PARSE` finding) · `2` config error.

### `spec lint`

Run the advisory lint checks over spec documents. Findings are warnings by default and do not fail the build.

```text
project-standards spec lint [<file>...] [--config <config>] [--json] [--strict]
```

Options:

- **`<file>...`** — Spec files to lint. Omit to use the `spec.include` globs.
- **`--config <config>`** — Project config file. Default: `.project-standards.yml`.
- **`--json`** — Emit a JSON findings payload. Default: off.
- **`--strict`** — Treat any lint finding as a failure. Default: off (warnings never fail). This flag is what turns a finding into a non-zero exit.

Exit status: `0` clean, or findings without `--strict` · `1` findings present and `--strict` set · `2` config error.

### `spec extract`

Print a single slice (a section or a tracked item) of one spec document, selected by a selector expression.

```text
project-standards spec extract <file> <selector> [--json]
```

Options:

- **`<file>`** — The spec document to read. Required positional.
- **`<selector>`** — The slice selector (for example a section heading or a requirement id). Required positional.
- **`--json`** — Emit the slice as a JSON object (`file`, `selector`, `kind`, `found`, `markdown`) instead of raw Markdown. Default: off.

Exit status: `0` slice found · `1` no match for the selector (or a spec parse error) · `2` invalid invocation.

### `spec next`

Print the next free tracked-item id for a given prefix within one spec document.

```text
project-standards spec next <file> <prefix> [--json]
```

Options:

- **`<file>`** — The spec document to scan. Required positional.
- **`<prefix>`** — The id prefix to allocate against (for example `REQ` or `NFR`). Required positional; matched case-insensitively and normalized to upper case in the output.
- **`--json`** — Emit `{file, prefix, next_id}` as JSON instead of the bare id. Default: off.

Exit status: `0` id computed · `1` spec parse error · `2` invalid prefix or invocation.

### `spec new`

Scaffold a new spec document at the chosen tier profile. Self-validates its own output before writing, so it never emits a spec that `spec validate` would reject.

```text
project-standards spec new [<path>] --profile {light | standard | full} [--id <spec-id>] [--title <title>] [--owner <owner>] [--implementer <implementer>] [--stdout] [--force] [--json] [--config <config>]
```

Options:

- **`<path>`** — Destination file to write. Required unless `--stdout` is given; mutually exclusive with `--stdout`. Writes are atomic and refuse to follow a symlinked target or symlinked parent.
- **`--profile {light | standard | full}`** — Spec tier to scaffold. Required. Allowed values: `light`, `standard`, `full`.
- **`--id <spec-id>`** — Use this spec id instead of minting one. Must match the spec-id pattern and must not already exist in the repo. Default: a fresh id is minted.
- **`--title <title>`** — Spec title to substitute into the scaffold. Default: the template placeholder.
- **`--owner <owner>`** — Owner field value. Default: template placeholder.
- **`--implementer <implementer>`** — Implementer field value. Default: template placeholder.
- **`--stdout`** — Write the scaffold to standard output instead of a file. Mutually exclusive with `<path>` and with `--force`.
- **`--force`** — Overwrite an existing destination file. No meaning with `--stdout`. Safety: destructive on `<path>`.
- **`--json`** — Emit a JSON result envelope (including on failure). Default: off.
- **`--config <config>`** — Project config file used to resolve reference prefixes and existing ids. Default: `.project-standards.yml`.

Exit status: `0` scaffold written or streamed · `2` any refusal — usage error, bad field value, bad or colliding `--id`, config error, id space exhausted, target-type conflict, or self-validation failure.

### `spec upgrade`

Upgrade a spec to a higher tier (additive only: `light` to `standard`/`full`, `standard` to `full`). Gates on the source being validation-clean and structurally upgradeable, and self-validates the result.

```text
project-standards spec upgrade <src> --to {standard | full} [--stdout] [--output <file>] [--in-place] [--force] [--json] [--config <config>]
```

Options:

- **`<src>`** — Source spec file to upgrade. Required positional; must be an existing regular file.
- **`--to {standard | full}`** — Target tier. Required. Allowed values: `standard`, `full`. The target must be strictly higher than the source tier.
- **`--stdout`** — Preview the upgraded spec on standard output. Mutually exclusive with `--in-place` and `--output`.
- **`-o`, `--output <file>`** — Write the upgraded spec to `<file>`. Refuses an existing target unless `--force`; refuses a target equal to the source (use `--in-place`). Mutually exclusive with `--in-place` and `--stdout`.
- **`-i`, `--in-place`** — Overwrite the source in place. Mutually exclusive with `--output` and `--stdout`.
- **`--force`** — Allow overwriting an existing `--output` target. Applies only with `--output`. Safety: destructive.
- **`--json`** — Emit a JSON result envelope (including on failure). Default: off.
- **`--config <config>`** — Project config file for reference prefixes. Default: none — with no `--config`, `.project-standards.yml` is never read, preserving the pre-4.0 default behavior exactly.

Exit status: `0` upgraded (written or previewed) · `2` any refusal — usage error, flag conflict, source not found or unreadable, source invalid or not upgradeable, or self-validation failure.

## EXIT STATUS

The table gives the repository-wide convention; per-command deviations are noted in each command's entry above.

| Code | Meaning                                                                    |
| ---- | -------------------------------------------------------------------------- |
| `0`  | Success                                                                    |
| `1`  | Findings — validation errors, remaining fix errors, or a not-found extract |
| `2`  | Operator error — bad invocation, missing/broken config, registry drift     |
| `3`  | Missing or malformed bundle manifest (`adopt` only)                        |

`spec lint` returns `1` only with `--strict`. `adopt` is the only command that reaches `3`. The top-level dispatcher returns the selected subcommand's code and falls back to argparse's exit `2` for an unknown command.

## ENVIRONMENT

- `NO_COLOR` — When set (to any value), disables ANSI color in `--help` output, honored through Python 3.14 `argparse`. The tool reads no color state of its own beyond this.
- `FORCE_COLOR` — Forces colored `--help` output where a terminal is not detected (also via `argparse`).
- `COLUMNS` — Sets the width `argparse` wraps `--help` to. Setting `NO_COLOR=1 COLUMNS=100` produces stable, comparable help text (the normalization the CI help-snapshot checks rely on).

No command reads an application-specific environment variable for configuration: all behavior is driven by arguments and the config file. `sync-vscode-colors` and `sync-standards-include` (below) shell out to `git` and therefore observe the ambient `git` environment.

## FILES

- `.project-standards.yml` — Default project config, read by `validate`, `fix`, the `spec` verbs, and the standalone validators. Overridable with `--config`.
- `.vscode/settings.json` — Read and written by `sync-vscode-colors` / `sync-standards-include` (the `folder-color.pathColors` block).
- Bundled schemas and spec templates ship inside the installed package (`project_standards/schemas/`, `project_standards/specs/templates/`) and are resolved automatically; they are not user-edited files.

## EXAMPLES

### Validate the whole configured file set

```bash
uv run project-standards validate --config .project-standards.yml
```

### Validate specific files without a config

```bash
uv run project-standards validate README.md docs/adr.md --no-require-frontmatter
```

### Fix frontmatter formatting and ids, then re-check

```bash
uv run project-standards fix --config .project-standards.yml
```

### Preview an adoption without writing anything

```bash
uv run project-standards adopt markdown-tooling --dry-run
```

### Adopt two standards into another repository

```bash
uv run project-standards adopt markdown-frontmatter python-tooling --dest ../my-repo
```

### List adoptable standards as JSON

```bash
uv run project-standards list --json
```

### Scaffold a new standard-tier spec

```bash
uv run project-standards spec new docs/specs/my-feature.md --profile standard --title "My Feature"
```

### Validate the project specs

```bash
uv run project-standards spec validate --config .project-standards.yml
```

### Preview a spec upgrade without writing

```bash
uv run project-standards spec upgrade docs/specs/my-feature.md --to full --stdout
```

## Standalone commands

Six console scripts are installed alongside `project-standards`. Each is a separate `[project.scripts]` entry point and therefore a public command. The `validate` and `fix` subcommands are the unified front ends over these; the standalone forms remain for scripting and back-compatibility.

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
- **`--config <path>`** — Project config file. Default: `.project-standards.yml`. A non-existent `--config` exits 2.
- **`--no-require-frontmatter`** — Do not fail files with no frontmatter block.
- **`-q`, `--quiet`** — Suppress success output.

Exit status: `0` all matched files valid (or none matched) · `1` validation errors · `2` operator error (config, schema, registry, or invocation).

### `validate-id`

Validate that frontmatter `id` fields follow `[doc_type]-[base36-6]-[readable-slug]`, and optionally repair them. Unified equivalents: `project-standards validate` (check) and `project-standards fix` (the `--fix` path).

```text
validate-id [<file>...] [--version] [--config <path>] [--quiet] [--glob <pattern>] [--schema <path>] [--fix]
```

Options:

- **`<file>...`** — Markdown files to validate. Omit to use the config include list.
- **`--version`** — Print the version and exit 0.
- **`--config <path>`** — Project config file. Default: `.project-standards.yml`. A non-existent `--config` exits 2.
- **`--quiet`** — Suppress per-file output; exit code only.
- **`--glob <pattern>`** — Validate files matching the pattern instead of the include list; combines with explicit files.
- **`--schema <path>`** — Custom schema override; when provided, id-format validation is skipped entirely (custom schemas may define different id conventions), and the command exits 0 with a note.
- **`--fix`** — Repair non-compliant ids in place, deriving the new id as `{doc_type}-{base36-token}-{slugify(title)}`. Safety: writes to disk. ADR ids (which require a repo-name segment) cannot be auto-derived and are skipped with a warning, which forces a non-zero exit.

Exit status: `0` all ids valid, or all fixable ids fixed · `1` violations remain (or ADR ids were skipped under `--fix`) · `2` operator error.

### `sync-vscode-colors`

Sync `folder-color.pathColors` in `.vscode/settings.json` from the `markdown.frontmatter.include` list in `.project-standards.yml`. Patterns containing `**` become `folderPath` entries; the rest become `filePath` entries. This is the inverse round-trip of `sync-standards-include`.

```text
sync-vscode-colors [<standards-file>] [<settings-file>]
sync-vscode-colors --version
sync-vscode-colors --help
```

This command uses raw positional arguments (no option parser); `--help`/`-h` and `--version` are intercepted before any positional is read. Any other leading token is treated as `<standards-file>`.

- **`<standards-file>`** — Project config to read include patterns from. Default: `<repo-root>/.project-standards.yml`. Positional 1.
- **`<settings-file>`** — VS Code settings file to rewrite. Default: `<repo-root>/.vscode/settings.json`. Positional 2. Safety: this file is rewritten in place.
- **`-h`, `--help`** — Print a one-paragraph usage summary and exit 0.
- **`--version`** — Print `sync-vscode-colors <version>` and exit 0.

Must run inside a git repository (defaults resolve against the repository root).

Exit status: `0` synced (or `--version`) · non-zero via `sys.exit(message)` when not in a git repo, when a required file is missing, or when the include block cannot be found (these print a message and exit `1`).

### `sync-standards-include`

Sync `markdown.frontmatter.include` in `.project-standards.yml` from the `folder-color.pathColors` entries in `.vscode/settings.json` that carry the project color. The inverse of `sync-vscode-colors`; `folderPath` entries are reconstructed with a `/**/*.md` suffix.

```text
sync-standards-include [<standards-file>] [<settings-file>]
sync-standards-include --version
sync-standards-include --help
```

Raw positional arguments, same contract as `sync-vscode-colors`: `--help`/`-h` and `--version` are intercepted before any positional is read; any other leading token is read as `<standards-file>`.

- **`<standards-file>`** — Project config whose include list is rewritten. Default: `<repo-root>/.project-standards.yml`. Positional 1. Safety: rewritten in place.
- **`<settings-file>`** — VS Code settings file to read colors from. Default: `<repo-root>/.vscode/settings.json`. Positional 2.
- **`-h`, `--help`** — Print a one-paragraph usage summary and exit 0.
- **`--version`** — Print `sync-standards-include <version>` and exit 0.

If no project-colored entries are found, the include list is emptied and a warning is printed to standard error. Must run inside a git repository.

Exit status: `0` synced (or `--version`) · non-zero via `sys.exit(message)` when not in a git repo, a required file is missing, or the `include:` block cannot be located (message printed, exit `1`).

### `format-frontmatter`

Autoformatter for managed Markdown frontmatter — the write-side companion to `validate-frontmatter`. Tokenizes the leading YAML block, applies deterministic transforms, and re-emits it preserving comments and line endings. Never changes the `id` value and never touches the document body. Unified equivalent: the format stage of `project-standards fix` (`format-frontmatter --write`).

```text
format-frontmatter [<file>...] [--version] [--config <config>] [--schema <schema>] [--glob <pattern>] [--check | --write] [--bump-updated] [--stdin] [--quiet]
```

Options:

- **`<file>...`** — Markdown files to format. Omit to use the config include list.
- **`--version`** — Print the version and exit 0.
- **`--config <config>`** — Project config file. Default: `.project-standards.yml`. A non-existent `--config` exits 2.
- **`--schema <schema>`** — Custom schema override; when set (or configured as a path) formatting is skipped with a note and exit 0.
- **`--glob <pattern>`** — Format files matching the pattern instead of the include list.
- **`--check`** — Report files that would change without writing. Mutually exclusive with `--write`. This is the default mode.
- **`--write`** — Rewrite files in place (atomic, mode-preserving). Mutually exclusive with `--check`. Safety: writes to disk.
- **`--bump-updated`** — When a file changes, also set its `updated` field to today's date.
- **`--stdin`** — Read one document from standard input and write the formatted result to standard output. Mutually exclusive with `<file>`, `--glob`, and `--write`.
- **`-q`, `--quiet`** — Suppress per-file output.

Exit status: `0` nothing to do, or all writes succeeded · `1` in check mode a file would change, or any mode encountered a refused (duplicate-key) block · `2` operator error, or an incompatible `--stdin` combination.

### `validate-references`

Opt-in cross-file frontmatter checks the JSON Schema cannot express: id uniqueness, referential integrity, supersede reciprocity, date ordering, and ADR sequence. Always a whole-repo pass — `<file>` and `--glob` are accepted (so `project-standards validate` can forward them) but do not scope the checks. Unified equivalent: the third stage of `project-standards validate`. Must run from the repository root.

```text
validate-references [<file>...] [--version] [--config <config>] [--schema <schema>] [--glob <pattern>] [--quiet]
```

Options:

- **`<file>...`** — Accepted and ignored for scoping (forwarded compatibility); the pass always indexes the full configured set.
- **`--version`** — Print the version and exit 0.
- **`--config <config>`** — Project config file. Default: `.project-standards.yml`. A non-existent `--config` exits 2.
- **`--schema <schema>`** — Custom schema override; when set (or configured as a path) reference validation is skipped with a note to standard error (even under `--quiet`) and exit 0.
- **`--glob <pattern>`** — Accepted and ignored for scoping (see `<file>`).
- **`-q`, `--quiet`** — Suppress the clean-run success line. Warnings and the custom-schema skip note still print.

Behavior notes: reference validation is opt-in — when the config does not enable it, the command exits 0 without checking anything. Warnings never fail the build; errors do. An empty index prints a note to standard error rather than a silent green summary (usually the sign of a wrong working directory).

Exit status: `0` references valid, disabled, or skipped under a custom schema · `1` one or more reference errors · `2` operator error (missing/broken config).

## NOTES

- **`--version` placement.** `--version` is a top-level flag only in first position (`project-standards --version`). `validate`, `fix`, and `spec` are early-dispatched before the top-level parser is built, so a trailing `--version` is handled by the dispatched target: after `validate` it is forwarded to the validators (which print a version and exit 0), while after `adopt` it is an argparse usage error and after `spec` it is an unknown verb — both exit 2. Put `--version` first.
- **`validate-references` scope.** The cross-file pass is repo-wide by design; scoping it to a subset would let a duplicate id or broken reference in an unselected document slip through. `<file>` / `--glob` are therefore forwarded but ignored by this stage even though `validate-frontmatter` and `validate-id` honor them.
- **Custom schemas disable id and format work.** When a custom (non-bundled) schema is selected, `validate-id`, `format-frontmatter`, `fix`, and `validate-references` skip their bundled-convention checks and exit 0 with a note — a custom-schema repository owns those conventions itself.
- **`sync-*` argv contract.** The two sync commands parse positionals directly with no option library, so they accept only `--help`/`-h` and `--version` as flags (intercepted before any positional is read); every other leading token is read as the first positional (a file path).

## SEE ALSO

- [`standards/cli-documentation/README.md`](../standards/cli-documentation/README.md) — the standard this document conforms to.
- [`src/project_standards/README.md`](../src/project_standards/README.md) — the package's implementation and developer reference.
