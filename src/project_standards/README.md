# project-standards source layout

This is the Python package that ships the Catalog 5 control plane, package-contract validators, provider runner, selected-package command adapters, and bounded V1 compatibility surfaces for the **project-standards** tool suite.

**Usage reference:** user-facing CLI documentation lives in [`docs/usage.md`](../../docs/usage.md); this file documents implementation internals.

---

## Table of Contents

- [project-standards source layout](#project-standards-source-layout)
  - [Table of Contents](#table-of-contents)
  - [CLI surface](#cli-surface)
  - [Validators and formatters](#validators-and-formatters)
    - [validate-frontmatter](#validate-frontmatter)
    - [validate-id](#validate-id)
      - [Standard format for all document types except ADR](#standard-format-for-all-document-types-except-adr)
      - [ADR document format](#adr-document-format)
    - [validate-references](#validate-references)
    - [format-frontmatter](#format-frontmatter)
    - [project-standards validate (combined command)](#project-standards-validate-combined-command)
    - [project-standards fix (combined fix command)](#project-standards-fix-combined-fix-command)
    - [project-standards spec (nested command group)](#project-standards-spec-nested-command-group)
    - [project-standards agent-handoff (nested command group)](#project-standards-agent-handoff-nested-command-group)
  - [Module map](#module-map)
  - [V5 control plane and package contract](#v5-control-plane-and-package-contract)
  - [Legacy compatibility boundary](#legacy-compatibility-boundary)
  - [Exit codes](#exit-codes)
  - [Configuration authority](#configuration-authority)
  - [Adding a standard package](#adding-a-standard-package)

## CLI surface

The installed `project-standards` entry point exposes these top-level command surfaces:

| Command | Module | Purpose |
| --- | --- | --- |
| `project-standards init …` | `control_plane/cli.py` | Create neutral unified state or preview/apply a V4 migration |
| `project-standards standards {list\|show\|enable\|disable\|version\|validate-graph\|render-catalog\|validate-packages\|render-consumer-catalog\|generate-package-schemas\|sync-payload-projection} …` | `standards_graph/cli.py` | Inspect selections and validate or generate package-contract artifacts |
| `project-standards reconcile …` | `control_plane/cli.py` | Plan, check, apply, or repair unified desired/applied state |
| `project-standards render STANDARD PROVIDER …` | `control_plane/cli.py` | Run one selected render provider and write its bytes to standard output |
| `project-standards validate [FLAGS] [FILE …]` | `cli.py`, `frontmatter_commands.py` | Run selected Frontmatter validation plus unified repository validation |
| `project-standards fix [FLAGS] [FILE …]` | `cli.py`, `frontmatter_commands.py` | Apply the selected Frontmatter fix plan, then revalidate |
| `project-standards spec {validate\|lint\|extract\|next\|new\|upgrade} …` | `specs/cli.py` | Nested command group over project specs — see [project-standards spec (nested command group)](#project-standards-spec-nested-command-group) |
| `project-standards packages check-release …` | `package_contract/cli.py` | Compare current packages with an immutable released baseline |
| `project-standards agent-handoff {validate\|drift-check\|size-report\|shape-check\|legacy-report\|upgrade} …` | `agent_handoff/cli.py` | Validate and maintain selected Agent Handoff 1.2 state, or use the warned V1 fallback when unified state is absent |
| `project-standards adopt …`, `project-standards list …` | `cli.py`, `adopt/` | Warned V1 compatibility surfaces retained for migration only |

Seven console scripts are registered by `pyproject.toml`:

| Script | Module | Purpose |
| --- | --- | --- |
| `validate-frontmatter [FLAGS] [FILE …]` | `validate_frontmatter.py` | Validate YAML frontmatter against the JSON Schema |
| `validate-id [FLAGS] [FILE …]` | `validate_id.py` | Validate `id` field format per `doc_type` |
| `validate-references [FLAGS]` | `validate_references.py` | Cross-file checks (id uniqueness, referential integrity, etc.) |
| `format-frontmatter [FLAGS] [FILE …]` | `format_frontmatter.py` | Reformat frontmatter (canonical key order, quoting, transforms) |
| `sync-vscode-colors …` | `sync_vscode_colors.py` | Legacy maintenance synchronization from include patterns to VS Code colours |
| `sync-standards-include …` | `sync_standards_include.py` | Legacy inverse synchronization from VS Code colours to include patterns |
| `project-standards …` | `cli.py` | Unified command dispatcher |

All seven installed scripts support `--help` and `--version`, with version output supplied by the shared `_version.py` helper. See [`docs/usage.md`](../../docs/usage.md) for the complete public contract.

When `.standards/` is authoritative, reconciled validation and maintenance commands resolve the exact applied payload and effective options from the central config, catalog, and lock. `render` intentionally resolves the desired selected payload without requiring applied-state parity so it can bootstrap a named consumer-owned file. Provider-backed reads consume immutable snapshots; provider-backed writes return typed plans that the platform executor applies after precondition checks. An explicit legacy `--config` cannot override unified authority.

When unified state is absent, the frontmatter, specification, and Agent Handoff commands may use their warned, bounded V1 fallback. The compatibility route preserves the historical provider or validator behavior and `.project-standards.yml` authority; it is not the authoring model for new packages.

---

## Validators and formatters

Three validators and one formatter provide the shared primitives for enforcing and repairing the managed-document contract. Under unified authority, selected provider functions use those primitives and return findings or one complete fix plan; direct console scripts and the warned V1 fallback invoke the standalone command functions.

### validate-frontmatter

Validates YAML frontmatter blocks against a JSON Schema (Draft 2020-12 via `jsonschema`). Entry point: `validate_frontmatter.main(argv)`.

**What it checks:**

- The file has a frontmatter block (`---…---`) — unless `--no-require-frontmatter` or `required: false` in config.
- The YAML block is valid and parses without error.
- Every field matches the JSON Schema (required fields present, types correct, enum values valid, date formats correct, etc.).
- Under unified authority, the selected package option chooses the bundled or custom schema. In the V1 fallback, the configured `version:` selects a bundled schema. The document's `schema_version` must be allowed by the effective schema.
- For ADR docs (`doc_type: adr`), when `require_sections: true`, enforces the three required `##` headings: `## Context and Problem Statement`, `## Considered Options`, `## Decision Outcome` (MADR 4.0).

**Key flags:**

| Flag | Default | Effect |
| --- | --- | --- |
| `FILE …` | (from config) | Files to validate; if omitted, uses `include`/`exclude` from config |
| `--config PATH` | None under unified authority; `.project-standards.yml` in the legacy fallback | Explicit legacy/debug config; rejected when `.standards/` is authoritative |
| `--schema PATH` | bundled schema | Override JSON Schema; skips built-in schema, uses the supplied file |
| `--glob PATTERN` | — | Additional glob relative to cwd |
| `--no-require-frontmatter` | — | Do not fail files with no frontmatter block |
| `--quiet` / `-q` | — | Suppress per-file output; exit code only |

**Custom schema and legacy bundled names:** `--schema PATH` always supplies a custom schema path; unified authority confines that path to the repository and snapshots its bytes. The V1 fallback also permits `markdown.frontmatter.schema:` in `.project-standards.yml` to name a bundled schema with a bare token such as `markdown-frontmatter`; `schema_value_is_path()` distinguishes those legacy config values from paths.

---

### validate-id

Validates the `id` field of each document against its `doc_type`. Entry point: `validate_id.main(argv)`.

**Files with no frontmatter, or missing `id` / `doc_type` fields, are silently skipped** — those structural errors belong to `validate-frontmatter`.

**Two id formats:**

#### Standard format for all document types except ADR

```text
{doc_type}-{base36token}-{readable-slug}
```

| Segment | Constraint |
| --- | --- |
| `{doc_type}` | Must be a valid `doc_type` enum value AND match the document's own `doc_type` field |
| `{base36token}` | Exactly 6 characters from `[0-9a-z]` (the base-36 alphabet) |
| `{readable-slug}` | Non-empty lowercase kebab-case — `[a-z0-9]+(-[a-z0-9]+)*`; no consecutive hyphens; frozen at creation time, NOT re-validated against the current title |

Example: `note-a3f9zk-tailscale-acl-tag-ordering-gotcha`

The readable-slug is generated via `slugify(title)` at creation but is never re-checked against a changed title. This ensures ids are stable even when documents are renamed.

#### ADR document format

```text
adr-{NNNN}-{repo-name}-{short-title}
```

| Segment | Constraint |
| --- | --- |
| `adr-` | Literal prefix |
| `{NNNN}` | Repo-scoped sequence number, ≥ 4 digits (e.g. `0001`, `0042`, `10000`) |
| `{repo-name}` | Kebab-case repository name; provides global uniqueness for cross-repo `related:` citations |
| `{short-title}` | Kebab-case short form of the decision title |

The suffix after `{NNNN}` must contain **at least two** hyphen-separated segments (repo-name + short-title minimum). `adr-0001-repo` (three segments total) is rejected — it is missing the short-title.

Example: `adr-0001-homelab-use-postgresql-for-persistent-storage`

**Key flags:**

| Flag | Default | Effect |
| --- | --- | --- |
| `FILE …` | (from config) | Files to validate; if omitted, uses `include`/`exclude` from config |
| `--config PATH` | None under unified authority; `.project-standards.yml` in the legacy fallback | Explicit legacy/debug config; rejected when `.standards/` is authoritative |
| `--schema PATH` | — | **Skip id validation entirely** — custom schemas may define different id conventions, so running the bundled rules would produce false positives |
| `--glob PATTERN` | — | Additional glob relative to cwd |
| `--quiet` / `-q` | — | Suppress per-file output; exit code only |
| `--no-require-frontmatter` | — | Accepted but ignored (id validation already skips files with no frontmatter) |
| `--fix` | — | Rewrite non-compliant ids in place (see below) |

**`--schema` skip logic:** When `--schema PATH` supplies a custom schema, or when the effective unified/V1 config selects a custom schema path, id validation prints a note and exits 0. A bare bundled name such as `markdown-frontmatter` is available only through V1 config and does not trigger the skip.

**`--fix` mode:**

Rewrites each non-compliant file's `id:` value in place:

1. Generates a fresh 6-char base-36 token using `secrets.choice(_BASE36_CHARS)`.
2. Derives the slug from the document's `title` via `slugify()`.
3. Constructs `{doc_type}-{token}-{slug}` and replaces the `id:` value.

**ADR docs are skipped** with a targeted warning to stderr — the `{repo-name}` segment cannot be auto-derived from document fields and must be set manually.

**Source preservation:** `_replace_frontmatter_id()` replaces only the value part of the `id:` line. Inline comments (`id: 'old-value'  # frozen at creation`) are captured as a trailing group and written back unchanged. `fix_file()` reconstructs the output line-by-line from the original decoded bytes so per-line endings (`\r\n`, `\n`, or bare `\r`) are preserved exactly — a bare-LF line in an otherwise-CRLF file is not converted.

---

### validate-references

Cross-file checks that JSON Schema cannot express. Entry point: `validate_references.main(argv)`. The selected package option controls this pass under unified authority; the V1 fallback reads `markdown.frontmatter.references.enabled` from `.project-standards.yml`.

**What it checks:**

- `id` uniqueness — no two documents share the same `id`.
- Referential integrity (warning) — every value in `related`, `depends_on`, `supersedes`, and `superseded_by` resolves, either as a known document `id` or as a file at that repo-root-relative path.
- Supersede reciprocity (warning) — `supersedes` ↔ `superseded_by` links are symmetric (both directions checked).
- Date ordering (error) — `created` ≤ `updated`, and `reviewed` ≥ `created` when present.
- ADR sequence (error) — no two ADRs share the same `adr-NNNN` number.

It is a repo-wide pass (no per-file mode). When `references_enabled` is false, `main()` returns 0 immediately — invoking it is always safe.

---

### format-frontmatter

Reformats frontmatter to canonical style. Entry point: `format_frontmatter.main(argv)`. `--write` also scaffolds a minimal schema-valid frontmatter block into a managed file that has none.

| Flag | Default | Effect |
| --- | --- | --- |
| `FILE …` | (from config) | Files to format; if omitted, uses `include`/`exclude` from config |
| `--write` | — | Rewrite files in place (also scaffolds missing frontmatter blocks) |
| `--check` | — | Check only; exit 1 if any file would change |
| `--stdin` | — | Read one document from stdin, write formatted result to stdout; incompatible with `FILE`, `--glob`, and `--write` |
| `--bump-updated` | — | Set `updated:` to today when the frontmatter block changes |
| `--config PATH` | None under unified authority; `.project-standards.yml` in the legacy fallback | Explicit legacy/debug config; rejected when `.standards/` is authoritative |
| `--glob PATTERN` | — | Additional glob relative to cwd |
| `--quiet` / `-q` | — | Suppress per-file output; exit code only |

**Transforms applied:**

- Reorder keys to canonical order.
- Quote all string values with single quotes.
- Rename `type` → `doc_type` (deny-listed alias).
- Render empty arrays as `[]`; non-empty arrays in block style.
- Preserve explicit `null` values (never stripped).
- Preserve the document body unchanged.

Works only with the bundled schema. Skips files under a custom schema.

---

### project-standards validate (combined command)

`project-standards validate [FLAGS] [FILE …]` first resolves the selected Markdown Frontmatter payload. Under unified authority it captures the requested documents, invokes the payload's validate providers (plus enabled companion validation), and validates the complete control-plane state without writing. The command returns the worst finding class so package or repository failures cannot be masked by another clean provider.

When unified authority is absent, the warned V1 fallback runs `validate-frontmatter`, `validate-id`, and `validate-references`, then returns their worst exit code. All flags (`--config`, `--schema`, `--glob`, `--no-require-frontmatter`, `--quiet`) preserve their established fallback semantics.

`--schema` supplies an explicit custom schema and causes bundled ID/reference conventions to skip where they are undefined. Reference checks also honor the selected package's effective option (or `references_enabled` in the V1 fallback).

`--help` is intercepted before forwarding and prints combined documentation.

**Dogfood command:**

```bash
uv run project-standards validate
```

---

### project-standards fix (combined fix command)

`project-standards fix [FLAGS] [FILE …]` resolves the selected Markdown Frontmatter payload, captures exact input state, requests one typed format-and-ID mutation plan, and applies that plan through the platform executor. It then runs the selected validation contract as a postcondition. A validation finding remains non-zero even when the preceding writes succeeded.

When unified authority is absent, the fallback uses the bundled authoring planner and the same executor, then runs the local schema, ID, and reference validators. `--schema`, `--no-require-frontmatter`, file, glob, and quiet options are accepted by both routes.

When an explicit or configured custom schema is active, `fix` prints a note and exits 0 without touching files because bundled formatting and ID transforms are semantically undefined for that schema.

---

### project-standards spec (nested command group)

`project-standards spec {validate|lint|extract|next|new|upgrade} …` is an early-dispatch group forwarded to `project_standards.specs.cli.run()`. It operates on project **specs**—maintained in this repo under `docs/specs/`—independently of the frontmatter/id/references validators above.

| Verb | Purpose |
| --- | --- |
| `spec validate [FILE …] [--config PATH]` | Validate spec documents through the selected package; the legacy fallback refuses a vacuous run when its config has no `spec:` block |
| `spec lint [FILE …] [--config PATH] [--strict]` | Lint spec documents for style/structure issues beyond schema validation; `--strict` turns warnings into a failing exit (default exits 0 with findings printed). `--strict` is also accepted on `spec validate` for argparse symmetry but is a no-op there — `validate` already exits 1 on any finding |
| `spec extract FILE SELECTOR [--json]` | Print a slice (ID row, numbered section, heading match, or appendix) from a spec document as raw Markdown |
| `spec next FILE PREFIX [--json]` | Print the next free ID for a prefix (e.g. `FR-013`), registry- and format-aware |
| `spec new` | Scaffold a new spec document from the canonical template, fail-closed self-validated before write |
| `spec upgrade SOURCE --to {standard\|full} [-i \| -o PATH \| --stdout] [--force] [--json]` | Additively promote a spec from a lower tier (`light`) to a higher tier (`standard`/`full`), inserting missing template-owned sections; triply fail-closed (source validation, upgradeability precheck, output self-validation) before any write |

Each verb is implemented in `src/project_standards/specs/cli.py`; `spec new` and `spec upgrade` share the `_NewArgParser`/`NewError`-style refusal contract (frozen `code` + `message` + `findings`, `--json` support) so both fail closed rather than emitting a document the validator would reject.

### project-standards agent-handoff (nested command group)

Under unified authority, `project-standards agent-handoff` routes manifest-declared providers for the selected Agent Handoff 1.2 payload. When unified state is absent, it emits the migration warning and routes the packaged V1 provider fallback. `validate` accumulates full conformance findings; `drift-check` limits findings to standard-owned artifacts, integrations, and provenance; `size-report` and `shape-check` expose policy views; `legacy-report` detects repo-local historical evidence without mutation; and `upgrade` refreshes only clean managed content.

Current adoption uses the unified control plane:

```bash
project-standards standards enable agent-handoff --version 1.2
project-standards reconcile
project-standards reconcile --apply
project-standards agent-handoff validate --repo . --json
```

The provider implementation lives under `agent_handoff/`. All consumer I/O is confined to a resolved repository root, dynamic writes carry content-hash preconditions, and central-lock ownership is published only after successful verification.

---

## Module map

```text
src/project_standards/
├── cli.py                  # Public dispatcher and V1 compatibility entry points
├── control_plane/         # Unified state, planning, providers, adapters, locking, executor
├── package_contract/      # V2 family/payload/catalog validation, schemas, release checks
├── provider_runner.py     # V1 packaged-provider compatibility dispatcher
├── frontmatter_commands.py
├── frontmatter_authoring.py
│                           # Selected Markdown Frontmatter command adapters and plans
├── specs/                 # Project Specification parser, commands, and selected providers
├── agent_handoff/         # Agent Handoff command adapters and conformance providers
├── standards_graph/       # Catalog inventory, selection, graph, and generation commands
├── schemas/               # Platform and compatibility schemas
├── families/              # Build projection of mutable family indexes/landings
├── payloads/              # Symlink-only build projection of immutable payloads
├── catalogs/              # Build projection of catalog sources
├── validate_frontmatter.py
├── validate_id.py
├── validate_references.py
├── format_frontmatter.py  # Standalone commands and bounded V1 fallback implementations
├── adopt/                 # Warned V1 adoption compatibility engine
├── bundles/               # Frozen V1 migration/adoption evidence
└── registry.py            # V1 contract-version compatibility registry
```

---

## V5 control plane and package contract

The active architecture has three distinct layers:

1. `package_contract/` validates mutable family indexes, complete immutable payloads, catalog sources, schemas, resources, providers, migrations, semantic ownership, projections, and release compatibility.
2. `control_plane/` resolves desired and applied state from `.standards/`, composes all enabled packages into one plan, captures immutable snapshots, invokes declared providers, and applies typed plans through the sole platform executor.
3. Public command adapters such as `frontmatter_commands.py`, `specs/cli.py`, and `agent_handoff/cli.py` resolve the exact selected package and delegate package-specific behavior without reading mutable family roots.

`src/project_standards/families/`, `payloads/`, and `catalogs/` are build projections. Family and payload files are authored under repository-root `standards/`; catalog sources are authored under repository-root `catalogs/`. The payload projection must contain relative file symlinks only, and wheel builds must prove projected bytes match canonical source bytes.

Providers execute offline from immutable payload resources and return their declared effect. They never receive authority to write the live repository. The platform executor validates paths, ownership, preconditions, and mutation-plan shape before changing consumer state.

## Legacy compatibility boundary

`adopt/`, `bundles/`, `registry.py`, and the standalone fallback implementations remain for exact V1 migration recognition and warned compatibility only. New packages and package versions must not be added through those surfaces. Current authoring uses family indexes, immutable payload manifests, catalog declarations, package schemas, providers, migrations, and the central control-plane lock.

The top-level `adopt` and `list` commands remain public during the V5 compatibility window, emit deprecation notices, and are scheduled for removal with the legacy fallback. They are not an alternative V5 ownership model.

---

## Exit codes

These are the common classes; command-group documentation in [`docs/usage.md`](../../docs/usage.md) defines the exact mapping for each surface.

| Code | Meaning |
| --- | --- |
| 0 | Command succeeded |
| 1 | Validation, drift, release-policy, or other command finding |
| 2 | Invalid invocation, unsafe state/path, unavailable authority, or configuration error on generic command surfaces |
| 3 | Agent Handoff package/provider prerequisite or internal failure; also a missing or malformed bundle prerequisite on the V1 adoption route |

---

## Configuration authority

Catalog 5 consumers use three central files:

- `.standards/config.toml` records desired package selectors and package options.
- `.standards/catalog.toml` records the exact committed catalog snapshot available to the consumer.
- `.standards/lock.toml` records applied versions, effective-option digests, managed ownership, referenced inputs, and the reconciled generation.

Commands resolve unified authority from the repository root and reject an explicit `.project-standards.yml` override or dual authority. A repository with no `.standards/` may use the warned V1 fallback during migration: `.project-standards.yml` remains a read-only authority input, while explicitly mutating fallback commands retain their documented writes. New configuration and new package behavior belong only in the unified plane.

## Adding a standard package

Follow the active internal [Standard Bundle Authoring 2.4 workflow](../../standards/standard-bundle-authoring/versions/2.4/README.md#author-workflow). In summary:

1. Create or update the mutable `standards/<id>/standard.toml` family index and author the complete new payload under `standards/<id>/versions/<major.minor>/` from the versioned templates.
2. Declare the closed package options, canonical standard, agent summary, every resource and output, providers, relationships, migrations, and legacy signatures in the payload. Do not add undeclared regular files.
3. Validate the payload and schemas, compute its aggregate digest, and index that exact version and digest in the family.
4. Add the exact package/version/digest with the correct role to the target catalog source.
5. Regenerate or check package schemas and the symlink-only build projection, then validate the package graph and generated catalog.
6. Prove source, direct-wheel, sdist-derived-wheel, migration, compatibility, and release-baseline behavior before publishing.

The minimum repository checks are:

```bash
uv run project-standards standards validate-packages --root . --json
uv run project-standards standards validate-graph --root . --require-all-manifests --json
uv run project-standards standards generate-package-schemas --root . --check
uv run project-standards standards sync-payload-projection --root . --check
```

Released payload directories are immutable. Correct released content with a new package version; never edit the published payload in place.
