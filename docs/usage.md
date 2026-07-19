---
schema_version: '1.1'
id: 'reference-u6b3wn-project-standards-cli-usage'
title: 'project-standards CLI Usage Reference'
description: 'Canonical man-style usage reference for the project-standards command and the six standalone console scripts it ships.'
doc_type: 'reference'
status: 'active'
created: '2026-07-07'
updated: '2026-07-19'
reviewed: '2026-07-18'
owner: ''
consumer: 'mix'
tags:
  - 'cli'
  - 'usage'
  - 'reference'
aliases:
  - 'project-standards-usage'
related:
  - 'standards/cli-documentation/versions/1.1/README.md'
source: []
confidence: 'high'
visibility: 'public'
license: null
---

# project-standards

## NAME

`project-standards` — validate and author standards packages, work with project specs, materialize packaged standards, and maintain Agent Handoff repositories.

## SYNOPSIS

```text
project-standards <command> [<args>...]
project-standards validate [<file>...] [--config <path>] [--schema <path>] [--glob <pattern>] [--no-require-frontmatter] [--quiet]
project-standards fix [<file>...] [--config <path>] [--schema <path>] [--glob <pattern>] [--no-require-frontmatter] [--quiet]
project-standards init --catalog <major> [--migrate [--apply]] [--repo <dir>] [--json]
project-standards reconcile [--check | --apply] [--allow-major <standard>@<major>]... [--repair-state] [--repo <dir>] [--json]
project-standards render <standard-id> <provider-id> [--repo <dir>] [--json]
project-standards adopt <standard>... [--dest <dir>] [--force] [--dry-run]
project-standards adopt agent-handoff [<standard>...] [--dest <dir>] (--manual | --harness {claude-code | codex}...) [--force] [--dry-run] [--json]
project-standards list [--json]
project-standards spec <verb> [<args>...]
project-standards standards <verb> [<args>...]
project-standards packages <verb> [<args>...]
project-standards agent-handoff <verb> [<args>...]
project-standards {--help | --version}
```

## DESCRIPTION

`project-standards` is the unified command-line surface for this repository's tooling. It exposes 31 leaf commands under one entry point: two frontmatter operations (`validate`, `fix`), 5 control/adoption operations (`init`, `reconcile`, `render`, `adopt`, `list`), eleven `standards` operations, one repository-only `packages` release check, six `spec` verbs, and six `agent-handoff` verbs.

Under unified authority, `validate` and `fix` invoke the provider selected by the applied Markdown Frontmatter package. Read-only validation consumes one immutable file snapshot; `fix` applies only the provider's typed plan through the platform executor and then revalidates. The standalone schema, ID, reference, ID-fix, and format-write surfaces use the same selected payload while retaining their narrower output contracts. In v5 legacy-only repositories, these commands warn and retain the local validator sequence as a bounded compatibility path. The six standalone console-script names documented under [Standalone commands](#standalone-commands) remain installed for scripting and back-compatibility.

Profile selection (recorded adopter judgment, per the CLI Documentation Standard §3): **Packaged** — 31 leaf commands plus the `spec`, `standards`, `packages`, and `agent-handoff` group overviews, documented on this single page because the group nesting stays navigable at this command count. The deep profile's generated per-command pages are not warranted here.

Output goes to standard output for success and results; validation violations, notes, and error summaries go to standard error. There is no interactive prompt; every command is non-interactive and driven entirely by arguments.

`--version` is recognized only as the **first** argument (`project-standards --version`). The control-plane commands (`init`, `reconcile`, and `render`), `validate`, `fix`, `spec`, `standards`, `packages`, `agent-handoff`, and specialized Agent Handoff adoption are dispatched before the top-level argument parser runs. A `--version` placed after one of those commands belongs to the dispatched command rather than the top level — see [NOTES](#notes).

## OPTIONS

### Global options

- **`-h`, `--help`** — Show help for the tool or the named subcommand and exit 0. Available on every command and subcommand.
- **`--version`** — Print `project-standards <version>` and exit 0. Recognized only as the first argument (see [NOTES](#notes)). Scope: top-level dispatcher.

Each leaf command is documented below with its own synopsis, options, and exit status. Every `[project.scripts]` key is a public command.

### `validate`

Validate schema, ID format, and opt-in cross-file references over the configured file set. Unified repositories use the exact applied package provider and effective options; v5 legacy-only repositories run `validate-frontmatter`, `validate-id`, and `validate-references` and return their worst exit code.

```text
project-standards validate [<file>...] [--config <path>] [--schema <path>] [--glob <pattern>] [--no-require-frontmatter] [--quiet]
```

Options (the selected provider and legacy fallback accept the same surface):

- **`<file>...`** — Zero or more Markdown files to validate. With no files, globs, or config includes, the underlying validators default to all `**/*.md` under the current directory.
- **`--config <path>`** — Explicit legacy/debug config path. Unified authority resolves from `.standards/config.toml` by repository root and rejects this override; a path that does not exist is an operator error (exit 2).
- **`--schema <path>`** — Custom JSON Schema to validate against. Frontmatter-only, and it also causes `validate-id` to skip (a custom schema may use a different id convention). Environment/config interaction: overrides the config's `markdown.frontmatter.schema`.
- **`--glob <pattern>`** — Glob (relative to the current directory) to validate instead of the config include list; combines with explicit `<file>` arguments. Note: this scopes `validate-frontmatter` and `validate-id`, but `validate-references` ignores it and always indexes the full configured set (see [NOTES](#notes)).
- **`--no-require-frontmatter`** — Do not fail files that have no frontmatter block. Frontmatter-only; no effect on the id or reference passes.
- **`-q`, `--quiet`** — Suppress per-file success output. Exit code is unaffected.

When `.standards/` exists, `validate` also checks unified desired, applied, catalog, and artifact state without writing. Drift or dual authority exits 1. A legacy-only `.project-standards.yml` remains readable in V5 but emits a migration warning.

Exit status: `0` all valid · `1` validation or control-plane findings · `2` operator error (missing config, bad schema, registry problem).

### `fix`

Under unified authority, request one complete format-and-ID mutation plan from the selected package, apply it through the platform executor, then revalidate against the same provider contract (references included). The v5 legacy-only fallback retains the `format-frontmatter --write` plus `validate-id --fix` sequence.

```text
project-standards fix [<file>...] [--config <path>] [--schema <path>] [--glob <pattern>] [--no-require-frontmatter] [--quiet]
```

Options:

- **`<file>...`** — Markdown files to fix. Omit to use the config include list.
- **`--config <path>`** — Explicit legacy/debug config path. Unified authority resolves from `.standards/config.toml` and rejects this override; a non-existent path exits 2.
- **`--schema <path>`** — Custom JSON Schema override. Because the bundled formatter and ID rules are undefined for a custom schema, `fix` reports the skip and exits 0 without changing files.
- **`--glob <pattern>`** — Glob to select files instead of the include list; combines with explicit `<file>` arguments. Forwarded to each stage.
- **`--no-require-frontmatter`** — Do not require a frontmatter block when the post-fix validation runs. The fix itself still scaffolds schema-valid metadata, including an ID, for a selected document that has no frontmatter.
- **`-q`, `--quiet`** — Suppress per-file output.

Safety: `fix` writes to disk (frontmatter reformatting and id rewrites are in-place, atomic, mode-preserving). It skips entirely, with a note on standard error and exit 0, when a custom schema is in use (via `--schema <path>` or a selected package/legacy config schema path) — custom-schema repos own their own id and format conventions.

Exit status: `0` success (or skipped under a custom schema) · `1` findings remain after the fix · `2` operator error (missing/broken config).

### `init`

Create the neutral `.standards/` scaffold for one catalog major, or preview/apply one complete migration from legacy authority. Plain initialization creates only `config.toml`, `catalog.toml`, and `lock.toml`, with no enabled standards.

```text
project-standards init --catalog <major> [--migrate [--apply]] [--repo <dir>] [--json]
```

Options:

- **`--catalog <major>`** — Positive catalog major supplied by the installed distribution. Required.
- **`--migrate`** — Inspect `.project-standards.yml`, registered legacy artifacts, and package-specific provenance; emit one deterministic migration report and reconciliation plan without writing.
- **`--apply`** — Apply the exact migration planned from the current bytes. Requires `--migrate`; a blocked or ambiguous report is never partially applied.
- **`--repo <dir>`** — Repository to initialize. Default: current directory.
- **`--json`** — In plain-init mode, emit the created/idempotent state and exact three-file inventory. In migration mode, emit the complete package reports, findings, reconciliation plan, and apply result without proposed file content.

Always run migration preview first, resolve every unknown version, modified signature, overlapping claim, or unclassified artifact, and rerun the preview against unchanged bytes before apply. Apply stages the unified files and package outputs, verifies the complete state, publishes the central lock, and only then retires `.project-standards.yml` and recognized package locks. A stale preview or failed verification preserves recoverable legacy authority.

The command is idempotent only when all three existing files describe the same neutral state or the requested migration is already complete. Plain init refuses legacy YAML, partial state, symlinks, or different content. During v5, legacy-only validation remains a warned read-only compatibility path; v6 removes that fallback, so migration is the required upgrade boundary.

Exit status: `0` plain init succeeded, migration already complete, or migration apply succeeded · `1` migration preview has an actionable plan/findings or apply failed · `2` invalid arguments, unsafe paths, unavailable catalog, unsupported authority state, or inconsistent existing state.

### `reconcile`

Build one complete plan from `.standards/config.toml`, the committed catalog and lock, installed package payloads, and live repository content. Planning and checking are read-only. Only `--apply` publishes a conflict-free plan, runs read-only verification providers, and replaces the central lock last.

When the installed tool carries a newer compatible snapshot of the same configured catalog major, the plan includes a catalog refresh. Compatible `latest` selections may advance; exact pins, package options, accepted-major tracks, referenced extensions, and unrelated files remain unchanged. An older tool, unavailable pin/track, incompatible default change, or catalog-major mismatch refuses refresh.

```text
project-standards reconcile [--check | --apply] [--allow-major <standard>@<major>]... [--repair-state] [--repo <dir>] [--json]
```

Options:

- **`--check`** — Report pending mutations, lock changes, or conflicts without writing. Mutually exclusive with `--apply`.
- **`--apply`** — Apply the current conflict-free plan. The executor rechecks each precondition and does not retry automatically.
- **`--allow-major <standard>@<major>`** — Authorize one exact package and target major for this invocation. Repeat for independent authorizations.
- **`--repair-state`** — Preview a sanctioned missing-catalog or missing-lock recovery. Recovery writes require both this flag and `--apply`. Missing user config is never inferred.
- **`--repo <dir>`** — Repository to reconcile. Default: current directory.
- **`--json`** — Emit stable plan, action, finding, recovery, or apply fields without proposed file content.

The default mode displays the plan. Exit 1 means drift, a conflict, an authorization refusal, or a recoverable apply failure. Exit 2 means the command or control authority is invalid.

Exit status: `0` reconciled or apply succeeded · `1` drift/findings/apply failure · `2` invocation, authority, package, or filesystem boundary error.

### `render`

Render content from one enabled package's manifest-declared `render` provider. The command resolves the selected package and its effective configuration without building a reconciliation plan or resolving referenced-input files. This permits bootstrapping a consumer-owned file that the selected configuration names but that does not exist yet.

```text
project-standards render <standard-id> <provider-id> [--repo <dir>] [--json]
```

Arguments and options:

- **`<standard-id>`** — Enabled standard whose selected payload declares the provider. Required.
- **`<provider-id>`** — Provider declared by that exact selected payload with the `render` operation. Required.
- **`--repo <dir>`** — Initialized repository whose selected package state supplies the provider configuration. Default: current directory.
- **`--json`** — Emit `{ok, standard_id, provider_id, content}` instead of the raw rendered content.

`render` writes rendered bytes only to standard output through its public interface and has no destination or output-path option. The provider contract forbids repository writes, and installed provider resources are integrity-verified. The runner rechecks declared live snapshot targets and refuses detected changes, but it is not an operating-system sandbox and cannot detect a write to an undeclared path. A detected provider mutation is an integrity incident, not an automatic rollback; inspect and restore any affected path before continuing.

To create a consumer-owned file, render first to an external scratch file, review and validate those complete bytes, and then publish with a no-clobber redirection. Shell redirection is the explicit consumer-owned materialization step:

```bash
set -euo pipefail
workflow_path=.github/workflows/cli-docs-check.yml
scratch=$(mktemp "${TMPDIR:-/tmp}/cli-docs-check.XXXXXX")
trap 'rm -f -- "$scratch"' EXIT
project-standards render cli-documentation render-workflow --repo . >"$scratch"
less "$scratch"
actionlint "$scratch"
mkdir -p "$(dirname "$workflow_path")"
(set -o noclobber; cat -- "$scratch" >"$workflow_path")
```

If rendering or validation fails, `set -e` stops before publication and the trap removes the scratch file. If the destination already exists, Bash's `noclobber` open fails without truncating or overwriting the consumer file. The bounded provider runner also rejects an undeclared provider, a non-render operation, or a payload-selection mismatch.

Exit status: `0` content rendered · `2` invalid arguments, uninitialized or disabled state, unavailable package/provider, provider refusal, or non-UTF-8 content.

### `adopt`

Compatibility command for existing adoption scripts. It emits a V5 deprecation notice on every invocation.

For every current consumer package in catalog 5, the command wraps initialization, desired-state enablement, and `reconcile --apply`. The V1 bundle path remains only as a v5 compatibility implementation for non-catalog historical surfaces and is removed with the v6 legacy gate. V5 routing never honors `--force`; reconciliation conflicts remain authoritative.

```text
project-standards adopt <standard>... [--dest <dir>] [--force] [--dry-run]
project-standards adopt agent-handoff [<standard>...] [--dest <dir>] (--manual | --harness {claude-code | codex}...) [--force] [--dry-run] [--json]
```

Options:

- **`<standard>...`** — One or more standard ids to adopt (for example `markdown-frontmatter`, `python-tooling`, `markdown-tooling`, `adr`, `cli-documentation`, `agent-handoff`). Required.
- **`--dest <dir>`** — Destination directory to write artifacts into. Default: the current directory. Must already exist unless `--dry-run` is given (a non-existent `--dest` without `--dry-run` exits 2).
- **`--force`** — Overwrite existing managed files that would otherwise be skipped. Create-only artifacts remain skipped. Safety: destructive for generic managed files — prefer `--dry-run` first.
- **`--dry-run`** — Show what the V1 bundle path would write without changing files. For a V5-advertised package, use explicit `init`, `standards enable`, and `reconcile` preview instead; the wrapper refuses V5 `--dry-run` so it cannot create the initial scaffold during a nominally read-only call.
- **`--manual`** — Agent Handoff only. Select manual startup and declare no automatic harness. Mutually exclusive with `--harness`; one selection is required.
- **`--harness {claude-code | codex}`** — Agent Handoff only. Select an automatic startup profile. Repeat for both harnesses. Values must be unique; mutually exclusive with `--manual`.
- **`--json`** — Agent Handoff only. Emit the aggregate plan/report schema instead of human-readable changes.

Exit status: `0` success · `1` a file write failed · `2` invalid invocation, non-directory `--dest`, or registry/bundle drift · `3` a standard's bundle manifest is missing or malformed.

For a catalog-5 Agent Handoff selection, the wrapper preserves consumer knowledge and publishes ownership in the central `.standards/lock.toml` last; successful legacy migration retires the package-specific manifest. Only the retained V1 fallback writes its package provenance lock last. Another standard may share the same invocation and aggregate plan.

### `list`

List standards that have V1 packaged adopt artifacts. This v5 compatibility command emits a deprecation notice and is removed with the v6 fallback. Use `project-standards standards list` for the complete installed V5 catalog inventory.

```text
project-standards list [--json]
```

Options:

- **`--json`** — Emit the standards, their contract versions, and their artifacts as a JSON array instead of the default human-readable listing. Default: off (text).

Exit status: `0` success · `2` registry/bundle drift.

### `agent-handoff`

Command group for validating and maintaining an Agent Handoff repository. Unified authority routes the selected Agent Handoff 1.1 package; when unified state is absent, the command emits the V5 migration warning and uses the packaged V1 provider fallback. Running the group with no verb or with `--help` prints the group help and exits 0; an unknown verb exits 2.

```text
project-standards agent-handoff {validate | drift-check | size-report | shape-check | legacy-report | upgrade} [--repo <dir>] [--json]
```

All verbs accept **`--repo <dir>`** (default: current directory). Read-only reports accept **`--json`**. `upgrade` additionally accepts **`--dry-run`**.

| Verb | Purpose |
| --- | --- |
| `validate` | Accumulate layout, config, integration, artifact, provenance, reference, size, shape, and credential findings |
| `drift-check` | Report only standard-owned artifact, integration, and provenance drift |
| `size-report` | Project UTF-8 byte targets and hard caps into the common finding schema |
| `shape-check` | Project fatal eager-document and advisory lazy-document shape rules |
| `legacy-report` | Detect recognized and unclassified repo-local historical evidence without mutation |
| `upgrade` | Preview or apply a provenance-guarded refresh of standard-owned artifacts |

Exit status: `0` clean/success · `1` findings or recoverable apply failure · `2` usage/config error · `3` package/provider prerequisite or internal failure.

`legacy-report` is the report-only exception: a successfully emitted inventory exits `0` even when it contains findings. Human and JSON output retain every finding; `validate` and `drift-check` continue to exit `1` when their findings require failure.

### `agent-handoff validate`

Under unified authority, validate the complete selected Agent Handoff repository contract without writing files. Legacy-only repositories use the warned V1 provider fallback.

```text
project-standards agent-handoff validate [--repo <dir>] [--json]
```

### `agent-handoff drift-check`

Report only standard-owned skill, hook, integration, and provenance drift.

```text
project-standards agent-handoff drift-check [--repo <dir>] [--json]
```

### `agent-handoff size-report`

Report configured UTF-8 byte targets and hard caps through the common finding schema.

```text
project-standards agent-handoff size-report [--repo <dir>] [--json]
```

### `agent-handoff shape-check`

Report eager and lazy document-shape findings without other conformance checks.

```text
project-standards agent-handoff shape-check [--repo <dir>] [--json]
```

### `agent-handoff legacy-report`

Detect recognized and unclassified historical repository evidence without mutation or outside-repository inspection.

```text
project-standards agent-handoff legacy-report [--repo <dir>] [--json]
```

### `agent-handoff upgrade`

Preview or apply a provenance-guarded refresh of standard-owned artifacts. Existing consumer knowledge is never overwritten.

```text
project-standards agent-handoff upgrade [--repo <dir>] [--dry-run] [--json]
```

### `standards`

Command group for V5 catalog selection plus V1 graph/catalog maintenance and V2 package authoring. Running `project-standards standards` with no verb prints usage to standard error and exits 2; `project-standards standards --help` prints usage and exits 0.

```text
project-standards standards {list | show | enable | disable | version | validate-graph | render-catalog | validate-packages | render-consumer-catalog | generate-package-schemas | sync-payload-projection} [<args>...]
```

There are no group-level options other than `-h` / `--help`; each verb defines its own flags. An unrecognized verb exits 2.

### `standards list`

List the complete committed catalog with desired and applied summaries.

```text
project-standards standards list [--repo <dir>] [--json]
```

### `standards show`

Show catalog, desired, applied, and configuration-path facts for one standard.

```text
project-standards standards show <standard> [--repo <dir>] [--json]
```

### `standards enable`

Enable a consumer-selectable standard and optionally set its desired selector. This edits only `.standards/config.toml`.

```text
project-standards standards enable <standard> [--version <latest|major.minor>] [--repo <dir>] [--json]
```

### `standards disable`

Disable a standard while preserving its selector and options. This edits only `.standards/config.toml`.

```text
project-standards standards disable <standard> [--repo <dir>] [--json]
```

### `standards version`

Change one standard's desired selector while preserving its enablement and options. This edits only `.standards/config.toml`.

```text
project-standards standards version <standard> <latest|major.minor> [--repo <dir>] [--json]
```

Every successful selection edit reports that reconciliation remains pending. Run `reconcile` to preview the resulting repository changes. The package selector (`version = "latest"` or an exact `major.minor`) chooses an immutable payload. Package-owned options such as `contract_version` independently choose a supported document/schema behavior inside that resolved payload; `standards version` never rewrites those options.

Exit status: `0` inspection/edit succeeded · `2` invalid invocation, unknown or non-selectable standard, unavailable version, or unsafe control state.

### `standards validate-graph`

Validate the standard-manifest graph: resource containment, config namespace ownership, provider shape, authority conflicts, relationships, capabilities, and hidden-dependency rules.

```text
project-standards standards validate-graph [--root <path>] [--json] [--require-all-manifests]
```

Options:

- **`--root <path>`** — Repository root to inspect. Default: the current directory.
- **`--json`** — Emit `{ok, findings}` as JSON instead of text. Default: off.
- **`--require-all-manifests`** — Fail when any `standards/<id>/` directory lacks a `standard.toml`. Default: off, so partial retrofit checks can still run.

Exit status: `0` graph clean · `1` graph findings present · `2` invalid invocation or graph-load error.

### `standards render-catalog`

Render the manifest-derived standards catalog, or verify that its checked-in copy is current. Rendering first requires a clean graph with every standard manifest present.

```text
project-standards standards render-catalog [--root <path>] [--output <path>] [--check]
```

Options:

- **`--root <path>`** — Repository root to inspect. Default: the current directory.
- **`--output <path>`** — Catalog path inside the repository root. Default: `standards/catalog.md`.
- **`--check`** — Compare the output file with a fresh render without writing it. Default: off.

Exit status: `0` catalog written or fresh · `1` graph findings or stale output · `2` invalid invocation, unsafe output path, or load/write error.

### `standards validate-packages`

Validate every discovered V2 package family, immutable payload, catalog source, and cross-package graph without executing providers or writing files.

```text
project-standards standards validate-packages [--root <path>] [--json]
```

Options:

- **`--root <path>`** — Repository root to inspect. Default: the current directory. Symlinked or non-directory roots are rejected.
- **`--json`** — Emit the stable `{ok, findings}` envelope instead of human-readable diagnostics.

Exit status: `0` repository clean · `1` contract findings · `2` invalid invocation or unsafe/load-boundary error.

### `standards render-consumer-catalog`

Render the package/version/channel/digest portion of the selected catalog for the consumer control plane. The output path is required; there is no implicit repository destination.

```text
project-standards standards render-consumer-catalog --catalog-major <major> --output <path> [--root <path>] [--tool-release <version>] [--check] [--json]
```

Options:

- **`--catalog-major <major>`** — Catalog source to render from `catalogs/<major>.toml`. Required.
- **`--output <path>`** — Caller-selected output inside the repository root. Required. A symlink or escaping path is rejected.
- **`--root <path>`** — Repository root. Default: the current directory.
- **`--tool-release <version>`** — Release metadata to record. Default: the installed `project-standards` version.
- **`--check`** — Compare regenerated bytes without creating or changing the output.
- **`--json`** — Emit a machine-readable result or finding envelope.

Exit status: `0` written or fresh · `1` package findings or stale output · `2` invalid invocation, unsafe output, or load/write error.

### `standards generate-package-schemas`

Generate the three package-contract and six control-plane JSON Schemas from their strict typed models.

```text
project-standards standards generate-package-schemas [--root <path>] [--check] [--json]
```

Options:

- **`--root <path>`** — Repository root. Default: the current directory.
- **`--check`** — Compare all nine checked-in schemas without writing them.
- **`--json`** — Emit a machine-readable result.

Exit status: `0` written or fresh · `1` any of the nine generated schemas is stale · `2` invalid invocation or unsafe output boundary.

### `standards sync-payload-projection`

Synchronize relative file symlinks from canonical `standards/<id>/versions/<version>/` payloads into the installed package-data path. It never copies or edits canonical payload bytes.

```text
project-standards standards sync-payload-projection [--root <path>] [--check] [--json]
```

Options:

- **`--root <path>`** — Repository root. Default: the current directory.
- **`--check`** — Report missing, stale, unsafe, or non-symlink projection members without mutation.
- **`--json`** — Emit the stable finding envelope.

Apply mode removes stale projection symlinks and empty directories. It refuses regular files and directory symlinks instead of deleting them.

Exit status: `0` synchronized or fresh · `1` projection drift in check mode · `2` invalid invocation or an unsafe projection shape that apply mode refuses.

### `packages`

Repository-only release workflow group. It is separate from reusable standard-package authoring commands because it compares the working repository with this repository's Git release history.

```text
project-standards packages {check-release} [<args>...]
```

### `packages check-release`

Compare every previously released payload and catalog selection with a tagged baseline, then classify the proposed change under ADR 0024.

```text
project-standards packages check-release --baseline <ref> [--root <path>] [--previous-version <version>] [--json]
```

Options:

- **`--baseline <ref>`** — Released Git tag or commit to compare. Required. Option-like and unresolved refs are rejected.
- **`--root <path>`** — Repository root. Default: the current directory.
- **`--previous-version <version>`** — Baseline tool SemVer. Required when `<ref>` is not a `vMAJOR.MINOR.PATCH` tag; otherwise derived from the tag.
- **`--json`** — Emit classification and stable findings as JSON.

The command reads the baseline through argument-vector Git calls and only loads catalog-declared family and payload paths. It never changes versions, catalogs, tags, or payloads.

Exit status: `0` allowed `patch`, `minor`, or `major` classification · `1` forbidden transition or current package findings · `2` invalid invocation, unsafe ref/root, or unavailable baseline evidence.

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

- **`<file>...`** — Spec files to validate. Under unified authority, omit to use the selected package's `include_patterns`; the legacy fallback uses the config's `spec.include` globs.
- **`--config <config>`** — Explicit legacy/debug config. Under unified authority, omit this option: the command resolves the selected `project-spec` package and effective options through `.standards/` and rejects a legacy override. In a legacy-only repository, the fallback default is `.project-standards.yml`.
- **`--json`** — Emit a JSON findings payload instead of the text `OK`/`FAIL` listing. Default: off.
- **`--strict`** — Accepted for symmetry with `spec lint`; `validate` already fails on any finding, so this flag does not change its exit code.

Exit status: `0` all specs clean · `1` any validation finding (a parse failure is reported as an `SV-PARSE` finding) · `2` config error.

### `spec lint`

Run the advisory lint checks over spec documents. Findings are warnings by default and do not fail the build.

```text
project-standards spec lint [<file>...] [--config <config>] [--json] [--strict]
```

Options:

- **`<file>...`** — Spec files to lint. Under unified authority, omit to use the selected package's `include_patterns`; the legacy fallback uses the config's `spec.include` globs.
- **`--config <config>`** — Explicit legacy/debug config. Under unified authority, omit this option: the command resolves the selected `project-spec` package and effective options through `.standards/` and rejects a legacy override. In a legacy-only repository, the fallback default is `.project-standards.yml`.
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
- **`--config <config>`** — Explicit legacy/debug config used by the fallback to resolve reference prefixes and existing IDs. Under unified authority, omit this option: the selected `project-spec` package supplies those values through `.standards/` and rejects a legacy override. In a legacy-only repository, the fallback default is `.project-standards.yml`.

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
- **`--config <config>`** — Explicit legacy/debug config for reference prefixes. Under unified authority, omit this option: the selected `project-spec` package supplies effective options through `.standards/` and rejects a legacy override. In the legacy fallback the default is none, so omitting `--config` never reads `.project-standards.yml`.

Exit status: `0` upgraded (written or previewed) · `2` any refusal — usage error, flag conflict, source not found or unreadable, source invalid or not upgradeable, or self-validation failure.

## EXIT STATUS

The table gives the repository-wide convention; per-command deviations are noted in each command's entry above.

| Code | Meaning |
| --- | --- |
| `0` | Success |
| `1` | Findings — validation errors, remaining fix errors, or a not-found extract |
| `2` | Operator error — bad invocation, missing/broken config, registry drift |
| `3` | Package/provider prerequisite, malformed non-configuration authority, or internal failure |

`spec lint` returns `1` only with `--strict`. Agent Handoff and `adopt` can reach `3` as described in their command-specific entries. The top-level dispatcher returns the selected subcommand's code and falls back to argparse's exit `2` for an unknown command.

## ENVIRONMENT

- `NO_COLOR` — When set (to any value), disables ANSI color in `--help` output, honored through Python 3.14 `argparse`. The tool reads no color state of its own beyond this.
- `FORCE_COLOR` — Forces colored `--help` output where a terminal is not detected (also via `argparse`).
- `COLUMNS` — Sets the width `argparse` wraps `--help` to. Setting `NO_COLOR=1 COLUMNS=100` produces stable, comparable help text (the normalization the CI help-snapshot checks rely on).

No command reads an application-specific environment variable for configuration: all behavior is driven by arguments and the config file. `sync-vscode-colors` and `sync-standards-include` (below) shell out to `git` and therefore observe the ambient `git` environment.

## FILES

- `.standards/` — Desired, catalog, and lock state created by `init` and read by `reconcile`, `render`, and V5 catalog commands. `reconcile --apply` may replace managed state. `render` exposes no state-write path; if a provider violates its write prohibition, detection refuses the invocation but does not roll back the mutation.
- `.project-standards.yml` — V5 legacy-only/debug configuration read only when unified authority is absent. `validate`, `fix`, provider-backed `spec` verbs, and standalone validators resolve `.standards/config.toml` under unified authority and reject a legacy override or dual authority.
- `.vscode/settings.json` — Read and written by `sync-vscode-colors` / `sync-standards-include` (the `folder-color.pathColors` block).
- Bundled schemas and spec templates ship inside the installed package (`project_standards/schemas/`, `project_standards/specs/templates/`) and are resolved automatically; they are not user-edited files.

## EXAMPLES

### Validate the whole configured file set

```bash
uv run project-standards validate
```

### Validate specific files without a config

```bash
uv run project-standards validate README.md docs/adr.md --no-require-frontmatter
```

### Fix frontmatter formatting and ids, then re-check

```bash
uv run project-standards fix
```

### Preview a V4 migration without writing anything

```bash
uv run project-standards init --catalog 5 --migrate
```

### Enable two packages and preview reconciliation

```bash
project-standards standards enable markdown-frontmatter --version 1.2
project-standards standards enable python-tooling --version 1.1
project-standards reconcile
```

### List standards with packaged adopt artifacts as JSON

```bash
uv run project-standards list --json
```

### Scaffold a new standard-tier spec

```bash
uv run project-standards spec new docs/specs/my-feature.md --profile standard --title "My Feature"
```

### Validate the project specs

```bash
uv run project-standards spec validate
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

- **`--version` placement.** `--version` is a top-level flag only in first position (`project-standards --version`). `init`, `reconcile`, `render`, `agent-handoff`, `validate`, `fix`, `spec`, `standards`, and `packages` are early-dispatched before the top-level parser is built; specialized Agent Handoff adoption is also dispatched early. A trailing `--version` is therefore handled or rejected by the selected command rather than treated as the top-level version flag. For example, `validate --version` forwards the flag to the validators and exits 0, while `render --version`, generic `adopt --version`, `spec --version`, and `standards --version` are usage errors and exit 2. Put `--version` first.
- **`validate-references` scope.** The cross-file pass is repo-wide by design; scoping it to a subset would let a duplicate id or broken reference in an unselected document slip through. `<file>` / `--glob` are therefore forwarded but ignored by this stage even though `validate-frontmatter` and `validate-id` honor them.
- **Custom schemas disable id and format work.** When a custom (non-bundled) schema is selected, `validate-id`, `format-frontmatter`, `fix`, and `validate-references` skip their bundled-convention checks and exit 0 with a note — a custom-schema repository owns those conventions itself.
- **`sync-*` argv contract.** The two sync commands parse positionals directly with no option library, so they accept only `--help`/`-h` and `--version` as flags (intercepted before any positional is read); every other leading token is read as the first positional (a file path).

## SEE ALSO

- [`standards/cli-documentation/versions/1.1/README.md`](../standards/cli-documentation/versions/1.1/README.md) — the standard this document conforms to.
- [`src/project_standards/README.md`](../src/project_standards/README.md) — the package's implementation and developer reference.
