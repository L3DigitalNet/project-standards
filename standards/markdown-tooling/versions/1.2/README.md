# Markdown Tooling Standard

- **Package version:** `1.2`
- **Markdown Tooling contract:** `1.1`, selected independently with `contract_version`
- **Status:** Source-checked, consumer-selectable standard
- **Last updated:** 2026-07-11
- **Scope:** Markdown plus the JSON, JSONC, and YAML files selected for Prettier formatting

## Purpose

This standard gives a repository one formatting authority and one Markdown-structure authority:

- Prettier owns physical formatting for the selected Markdown and structured-config files [S01], [S02].
- markdownlint owns Markdown structure and diagnostics [S03], [S04].
- EditorConfig supplies the cross-editor floor for encoding, line endings, indentation, final newlines, and Markdown trailing whitespace [S07].

The package is a managed control-plane package. It does not distribute instructions for manually copying configuration. The [adoption guide](adopt.md) describes package options and ownership; the project-standards distribution's `docs/usage.md` owns generic initialization, selection, plan, apply, update, and disable commands.

Python formatting, frontmatter semantics, and document identity are outside this standard. Python Tooling owns Python source. Markdown Frontmatter is a companion package that owns metadata schemas and validation; neither package depends on the other.

## Tool contract

The local repair commands are:

```bash
npx prettier --write .
npx markdownlint-cli2 --fix "**/*.md"
```

The corresponding non-mutating checks are:

```bash
npx prettier --check .
npx markdownlint-cli2 "**/*.md"
```

Repositories may narrow these commands to their package-selected globs. Prettier discovers `.prettierrc.json` while traversing selected paths and normally honors `.gitignore` and `.prettierignore` [S02]. `markdownlint-cli2` discovers `.markdownlint.json`, accepts CLI globs, and applies `--fix` without backups [S03].

Work over an enabled surface is incomplete until its selected checks pass, or the final report identifies the failed check and cause.

## Managed package surface

Package 1.2 exclusively manages the two configs and two managed caller workflows:

| Path | Contract |
| --- | --- |
| `.markdownlint.json` | Complete markdownlint rule configuration |
| `.prettierrc.json` | Prettier formatting configuration |
| `.github/workflows/lint-markdown.yml` | Managed caller of the reusable Markdown lint workflow at `@v5` |
| `.github/workflows/format.yml` | Managed caller of the reusable formatter workflow at `@v5` |

The package composes smaller units into shared consumer containers:

- per-property entries in `.editorconfig`;
- per-extension recommendation entries in `.vscode/extensions.json`;
- per-setting formatter entries under `[markdown]`, `[json]`, `[jsonc]`, and `[yaml]` in `.vscode/settings.json`;
- one option-rendered, bounded instruction block in each of `AGENTS.md` and `CLAUDE.md`.

Unrelated settings, extensions, properties, and instruction text remain consumer-owned. Disabling or upgrading this package removes or updates only its declared units. Empty shared objects or arrays can remain after the package's last unit is removed; the container itself is not package-owned.

## Package options

The closed package schema provides these options:

| Option | Default | Effect |
| --- | --- | --- |
| `contract_version` | `1.1` | Selects the independent standard contract |
| `lint` | `true` | Enables the managed markdownlint config and enforcement |
| `format` | `true` | Enables the managed Prettier config and enforcement |
| `ci.lint_caller` | `true` | Adds pull-request and `main` push triggers to the lint caller |
| `ci.format_caller` | `true` | Adds pull-request and `main` push triggers to the format caller |
| `markdown_globs` | `**/*.md` | Selects Markdown for lint and format callers |
| `config_globs` | JSON, JSONC, and YAML globs | Selects structured config for the format caller |
| `exclusions` | empty | Records a glob, `lint`/`format`/`both` applicability, and rationale |

If a tool is disabled, its corresponding caller option must also be false. A caller whose automatic option is false remains installed as manual-only `workflow_dispatch`; changing trigger policy does not churn file ownership. A disabled format caller passes `prettier: false` to the reusable workflow so a manual dispatch is a clean no-op.

Globs and reasons are declarative data. The schema rejects control characters, newlines, and strings that could escape the generated Markdown or managed markers. Providers serialize caller inputs as YAML scalars rather than concatenating config into YAML structure.

## CI enforcement

### Markdown lint

The managed lint caller sends newline-delimited `markdown_globs` and a typed `markdownlint` enforcement flag to `.github/workflows/lint-markdown.yml`. Exclusions that apply to lint are serialized as negative globs. The reusable workflow runs `DavidAnson/markdownlint-cli2-action@v24`, whose bundled Node runtime means a consumer does not need a committed Node project [S05], [S06]. A false enforcement flag skips the whole job, so a disabled manual-only caller is a clean no-op.

### Formatting

The managed format caller sends three typed inputs to `.github/workflows/format.yml`:

- `prettier` selects enforcement;
- `globs` is the newline-delimited combination of `markdown_globs` and `config_globs`;
- `exclusions` contains newline-delimited format or shared exclusion patterns.

The reusable workflow keeps `.` as its backward-compatible default. It transfers inputs through environment variables, splits them into quoted Bash arrays, and invokes pinned Prettier over `"${globs[@]}"`. Existing `.gitignore`, existing `.prettierignore`, and the repository-root temporary file for package exclusions remain separate `--ignore-path` arguments, so each pattern keeps its correct anchor and a missing terminal newline cannot merge entries. Config values never become shell source.

The lint and format callers are separate so repositories can select either authority independently. Neither workflow is coupled to frontmatter validation.

## Formatter policy

`.prettierrc.json` is the managed formatting contract. Its load-bearing choices are:

- `proseWrap: never`, so Prettier does not compete with a line-length lint rule [S01];
- `useTabs: true` and `tabWidth: 2` for non-Markdown indentation;
- a Markdown override using the formatter's Markdown printer;
- a JSONC override with `trailingComma: none`;
- `endOfLine: lf`.

Prettier is the only tool permitted to mutate Markdown, JSON, JSONC, or YAML formatting. Alternative formatters such as dprint or mdformat require a documented project exception because their ownership overlaps.

## Markdown lint policy

The managed `.markdownlint.json` enables the complete rule baseline and explicitly records deliberate deviations. Formatting-only rules that would fight Prettier are disabled or aligned with Prettier output. Structural rules remain markdownlint-owned.

Important invariants include:

- MD013 is disabled because Prettier owns wrapping and `proseWrap: never` is authoritative.
- MD024 is disabled to support repeated MADR option headings [S09].
- MD025 uses an empty `front_matter_title` selector so a frontmatter title does not replace the body H1.
- MD043 stays `true`; an empty `headings` list would mean that no headings are permitted [S08].
- MD060 accepts Prettier's table alignment instead of imposing a competing layout.

markdownlint diagnoses Markdown in VS Code. The package does not enable markdownlint fix-on-save, so Prettier remains the sole mutation authority [S10], [S11].

## Editor composition

EditorConfig contributions cover only the properties needed to align editors with the tool contract. Markdown uses two-space list indentation and preserves trailing spaces because two spaces can encode a hard line break. YAML uses spaces. Consumer sections and properties outside those exact scopes are preserved.

The VS Code recommendations are `esbenp.prettier-vscode` and `DavidAnson.vscode-markdownlint`. The package owns only those two set members. In settings, it owns `editor.defaultFormatter` for Markdown, JSON, JSONC, and YAML plus `editor.formatOnSave` for Markdown. Other keys under the same language object, such as `editor.wordWrap`, remain untouched.

## Agent guidance

The package renders its selected tools, globs, and typed exclusions into bounded `project-standards:markdown-tooling` blocks. The control plane manages the marker pair and its contents while preserving all text outside the block. The rendered guidance tells agents which checks are enabled and why an exclusion exists; it does not reproduce lifecycle commands or own the whole instruction file.

## Delegated lifecycle and central lock

Markdown Tooling delegates lifecycle mechanics to the unified project-standards control plane. Consumers select options in `.standards/config.toml`, preview reconciliation, and apply the plan using the generic CLI. The central lock in `.standards/lock.toml` records the resolved package, payload digest, and contribution state; this package does not create a private lock, manifest, or lifecycle command.

On update or disable, reconciliation uses the central lock plus current inspection to distinguish package-owned bytes from consumer content. Do not hand-edit exclusive managed files or bounded managed units to bypass checks; either change package options or document a conformant ADR exception.

## Migration and preservation

Automatic V4 migration recognizes `markdown_tooling.version` and exact released bytes for legacy configs, callers, EditorConfig, and VS Code recommendations. Exact whole files can transfer to managed ownership. Shared containers are never replaced wholesale: recognized units are adopted semantically, consumer siblings are preserved, and modified legacy content is reported for review.

Migration never writes from a provider, accesses the network, or emits an active legacy `.project-standards.yml` fragment. After successful apply, the ordinary central lock becomes the sole ownership record. Historical copy-adopt wording may be useful when explaining old inputs, but it is not an instruction for V2 consumers.

## Boundaries, companions, and exceptions

Markdown Frontmatter is a companion, not a dependency. It can be enabled independently and owns frontmatter schemas, key semantics, and document IDs. Python Tooling owns Python formatting. Markdown Tooling does not own arbitrary EditorConfig sections, VS Code settings, `.markdownlint-cli2.jsonc`, prose-style linting, or entire instruction files.

A repository can deviate only through a conformant ADR under `docs/adr/`. The ADR must identify the competing authority, explain why the standard configuration cannot serve the repository, and describe validation and rollback. Silencing a failure without resolving ownership is not an exception.

## Review triggers

Review this standard when Prettier changes Markdown or structured-config behavior, markdownlint adds or changes rules, the reusable actions change runtime or major version, EditorConfig semantics change, or the VS Code extensions change mutation behavior. Re-run package-contract, workflow, Prettier, and markdownlint coherence checks after any such update.

## Source register

| ID | Source | What it supports | Last checked |
| --- | --- | --- | --- |
| S01 | [Prettier options](https://prettier.io/docs/options) | Formatting options including `proseWrap`, indentation, line endings, and overrides | 2026-06-07 |
| S02 | [Prettier configuration and CLI](https://prettier.io/docs/configuration) | Config discovery, path selection, ignore behavior, and supported configuration names | 2026-06-07 |
| S03 | [markdownlint-cli2](https://github.com/DavidAnson/markdownlint-cli2) | Config discovery, CLI globs, gitignore behavior, and in-place fixes | 2026-06-07 |
| S04 | [markdownlint](https://github.com/DavidAnson/markdownlint) | Markdown-only linting and complete rule baseline | 2026-06-07 |
| S05 | [markdownlint-cli2-action](https://github.com/DavidAnson/markdownlint-cli2-action) | Action inputs and major-tag invocation | 2026-06-07 |
| S06 | [markdownlint-cli2 action metadata](https://raw.githubusercontent.com/DavidAnson/markdownlint-cli2-action/main/action.yml) | Bundled Node runtime | 2026-06-07 |
| S07 | [EditorConfig specification](https://spec.editorconfig.org/) | Root, encoding, line ending, indentation, final-newline, trailing-whitespace, and glob semantics | 2026-06-07 |
| S08 | [markdownlint rules](https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md) | Rule behavior and parameters, including MD025 and MD043 | 2026-06-07 |
| S09 | [MADR markdownlint configuration](https://github.com/adr/madr/blob/develop/.markdownlint.yml) | MADR's MD024 policy | 2026-06-07 |
| S10 | [Prettier VS Code extension](https://marketplace.visualstudio.com/items?itemName=esbenp.prettier-vscode) | Default formatter and format-on-save behavior | 2026-06-07 |
| S11 | [markdownlint VS Code extension](https://marketplace.visualstudio.com/items?itemName=DavidAnson.vscode-markdownlint) | Diagnostics and explicit fix behavior | 2026-06-07 |

[S01]: #source-register
[S02]: #source-register
[S03]: #source-register
[S04]: #source-register
[S05]: #source-register
[S06]: #source-register
[S07]: #source-register
[S08]: #source-register
[S09]: #source-register
[S10]: #source-register
[S11]: #source-register
