# `project_standards` — source layout

This is the Python package that ships the validator, adopt engine, bundled schemas, and standard bundles for the **project-standards** tool suite.

---

## Table of Contents

- [`project_standards` — source layout](#project_standards--source-layout)
  - [Table of Contents](#table-of-contents)
  - [CLI surface](#cli-surface)
  - [Validators and formatters](#validators-and-formatters)
    - [validate-frontmatter](#validate-frontmatter)
    - [validate-id](#validate-id)
      - [Standard format — all `doc_type` values except `adr`](#standard-format--all-doc_type-values-except-adr)
      - [ADR format — `doc_type: adr`](#adr-format--doc_type-adr)
    - [validate-references](#validate-references)
    - [format-frontmatter](#format-frontmatter)
    - [project-standards validate (combined command)](#project-standards-validate-combined-command)
    - [project-standards fix (combined fix command)](#project-standards-fix-combined-fix-command)
    - [project-standards spec (nested command group)](#project-standards-spec-nested-command-group)
  - [Module map](#module-map)
  - [Adopt engine](#adopt-engine)
    - [Artifact kinds](#artifact-kinds)
    - [Ownership and deduplication](#ownership-and-deduplication)
  - [Contract-version registry (`registry.json`)](#contract-version-registry-registryjson)
  - [Exit codes](#exit-codes)
  - [Configuration file (`.project-standards.yml`)](#configuration-file-project-standardsyml)
  - [Adding a new standard](#adding-a-new-standard)

## CLI surface

Console scripts registered by `pyproject.toml`:

| Command | Module | Purpose |
| --- | --- | --- |
| `project-standards adopt STANDARD …` | `cli.py` | Materialize a standard's files into a target repo |
| `project-standards list [--json]` | `cli.py` | List adoptable standards and their artifacts |
| `project-standards validate [FLAGS] [FILE …]` | `cli.py` | Run all three validators (schema + id + references) in one pass |
| `project-standards fix [FLAGS] [FILE …]` | `cli.py` | Format frontmatter, fix ids, then re-validate (bundled schema only) |
| `project-standards spec {validate\|lint\|extract\|next\|new\|upgrade} …` | `specs/cli.py` | Nested command group over project specs — see [project-standards spec (nested command group)](#project-standards-spec-nested-command-group) |
| `validate-frontmatter [FLAGS] [FILE …]` | `validate_frontmatter.py` | Validate YAML frontmatter against the JSON Schema |
| `validate-id [FLAGS] [FILE …]` | `validate_id.py` | Validate `id` field format per `doc_type` |
| `validate-references [FLAGS]` | `validate_references.py` | Cross-file checks (id uniqueness, referential integrity, etc.) |
| `format-frontmatter [FLAGS] [FILE …]` | `format_frontmatter.py` | Reformat frontmatter (canonical key order, quoting, transforms) |

`project-standards validate` is an early-dispatch command that forwards its full argv to `validate_frontmatter.main()`, `validate_id.main()`, and `validate_references.main()` and returns the worst exit code so no validator's errors are masked by another's success. `validate-references` self-gates on `references_enabled` — it exits 0 immediately unless the repo has opted in via `.project-standards.yml`.

`project-standards fix` is an early-dispatch command that runs `format_frontmatter.main(["--write", …])`, then `validate_id.main(["--fix", …])`, and finally the full `validate` contract (schema + id + references). It skips entirely when a custom schema is in use (flag `--schema` or `markdown.frontmatter.schema:` pointing to a file path).

---

## Validators and formatters

Three validators and one formatter enforce and repair the managed-document contract. They share the same config file and the same `collect_paths()` logic, and are all invoked by `project-standards validate` / `project-standards fix`.

### validate-frontmatter

Validates YAML frontmatter blocks against a JSON Schema (Draft 2020-12 via `jsonschema`). Entry point: `validate_frontmatter.main(argv)`.

**What it checks:**

- The file has a frontmatter block (`---…---`) — unless `--no-require-frontmatter` or `required: false` in config.
- The YAML block is valid and parses without error.
- Every field matches the JSON Schema (required fields present, types correct, enum values valid, date formats correct, etc.).
- The `schema_version` matches the configured contract version if `version:` is pinned.
- For ADR docs (`doc_type: adr`), when `require_sections: true`, enforces the three required `##` headings: `## Context and Problem Statement`, `## Considered Options`, `## Decision Outcome` (MADR 4.0).

**Key flags:**

| Flag | Default | Effect |
| --- | --- | --- |
| `FILE …` | (from config) | Files to validate; if omitted, uses `include`/`exclude` from config |
| `--config PATH` | `.project-standards.yml` | Config file |
| `--schema PATH` | bundled schema | Override JSON Schema; skips built-in schema, uses the supplied file |
| `--glob PATTERN` | — | Additional glob relative to cwd |
| `--no-require-frontmatter` | — | Do not fail files with no frontmatter block |
| `--quiet` / `-q` | — | Suppress per-file output; exit code only |

**Custom schema and bundled schema names:** `--schema` accepts a path OR a bundled name (e.g. `markdown-frontmatter`). `schema_value_is_path()` in `validate_frontmatter.py` detects paths by looking for `/`, `\`, or `.json` suffix. A bare token is treated as a bundled name. The same logic governs `markdown.frontmatter.schema:` in the config file.

---

### validate-id

Validates the `id` field of each document against its `doc_type`. Entry point: `validate_id.main(argv)`.

**Files with no frontmatter, or missing `id` / `doc_type` fields, are silently skipped** — those structural errors belong to `validate-frontmatter`.

**Two id formats:**

#### Standard format — all `doc_type` values except `adr`

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

#### ADR format — `doc_type: adr`

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
| `--config PATH` | `.project-standards.yml` | Config file |
| `--schema PATH` | — | **Skip id validation entirely** — custom schemas may define different id conventions, so running the bundled rules would produce false positives |
| `--glob PATTERN` | — | Additional glob relative to cwd |
| `--quiet` / `-q` | — | Suppress per-file output; exit code only |
| `--no-require-frontmatter` | — | Accepted but ignored (id validation already skips files with no frontmatter) |
| `--fix` | — | Rewrite non-compliant ids in place (see below) |

**`--schema` skip logic:** When `--schema PATH` is provided on the CLI, OR when `markdown.frontmatter.schema:` in the config file is a path (detected by the `"/" in value or "\\" in value or value.endswith(".json")` check in `validate_id.py`), id validation prints a note and exits 0. A bare bundled name like `markdown-frontmatter` does NOT trigger the skip.

**`--fix` mode:**

Rewrites each non-compliant file's `id:` value in place:

1. Generates a fresh 6-char base-36 token using `secrets.choice(_BASE36_CHARS)`.
2. Derives the slug from the document's `title` via `slugify()`.
3. Constructs `{doc_type}-{token}-{slug}` and replaces the `id:` value.

**ADR docs are skipped** with a targeted warning to stderr — the `{repo-name}` segment cannot be auto-derived from document fields and must be set manually.

**Source preservation:** `_replace_frontmatter_id()` replaces only the value part of the `id:` line. Inline comments (`id: 'old-value'  # frozen at creation`) are captured as a trailing group and written back unchanged. `fix_file()` reconstructs the output line-by-line from the original decoded bytes so per-line endings (`\r\n`, `\n`, or bare `\r`) are preserved exactly — a bare-LF line in an otherwise-CRLF file is not converted.

---

### validate-references

Cross-file checks that JSON Schema cannot express. Entry point: `validate_references.main(argv)`. **Disabled by default** — opt in via `markdown.frontmatter.references.enabled: true` in `.project-standards.yml`.

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
| `--config PATH` | `.project-standards.yml` | Config file |
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

`project-standards validate [FLAGS] [FILE …]` runs all three validators in a single pass:

```python
rc_frontmatter = validate_frontmatter.main(validator_args)
rc_id = validate_id.main(validator_args)
rc_refs = validate_references.main(validator_args)
return max(rc_frontmatter, rc_id, rc_refs)
```

All flags (`--config`, `--schema`, `--glob`, `--no-require-frontmatter`, `--quiet`) are forwarded unchanged to all validators. The worst exit code is returned so no validator's errors can be masked by another's success.

`--schema` causes `validate-id` to skip automatically (custom schemas may use different id conventions). `validate-references` self-gates on `references_enabled`.

`--help` is intercepted before forwarding and prints combined documentation.

**Dogfood command:**

```bash
uv run project-standards validate --config .project-standards.yml
```

---

### project-standards fix (combined fix command)

`project-standards fix [FLAGS] [FILE …]` is a three-phase pipeline:

1. `format_frontmatter.main(["--write", …])` — reformat frontmatter in place.
2. `validate_id.main(["--fix", …])` — regenerate non-compliant ids in place.
3. Full `validate` contract — schema + id + references — as a postcondition.

Returns the worst exit code across all three phases. If the final validate fails (e.g. a duplicate-id reference error), the exit code is non-zero even though the write phases succeeded.

**Custom-schema skip (CR-001):** when `--schema` is passed, or `markdown.frontmatter.schema:` in the config is a path, `fix` prints a note and exits 0 without touching any files — bundled transforms are semantically undefined for non-standard schemas.

---

### project-standards spec (nested command group)

`project-standards spec {validate|lint|extract|next|new|upgrade} …` is an early-dispatch group forwarded to `project_standards.specs.cli.run()`. It operates on project **specs** — the `docs/superpowers/specs/` documents this repo's own SDD workflow produces — independently of the frontmatter/id/references validators above.

| Verb | Purpose |
| --- | --- |
| `spec validate [FILE …] [--config PATH]` | Validate spec documents against the configured `spec:` schema (exits 2 with no vacuous green run if `.project-standards.yml` has no `spec:` block) |
| `spec lint [FILE …] [--config PATH] [--strict]` | Lint spec documents for style/structure issues beyond schema validation; `--strict` turns warnings into a failing exit (default exits 0 with findings printed). `--strict` is also accepted on `spec validate` for argparse symmetry but is a no-op there — `validate` already exits 1 on any finding |
| `spec extract FILE SELECTOR [--json]` | Print a slice (ID row, numbered section, heading match, or appendix) from a spec document as raw Markdown |
| `spec next FILE PREFIX [--json]` | Print the next free ID for a prefix (e.g. `FR-013`), registry- and format-aware |
| `spec new` | Scaffold a new spec document from the canonical template, fail-closed self-validated before write |
| `spec upgrade SOURCE --to {standard\|full} [-i \| -o PATH \| --stdout] [--force] [--json]` | Additively promote a spec from a lower tier (`light`) to a higher tier (`standard`/`full`), inserting missing template-owned sections; triply fail-closed (source validation, upgradeability precheck, output self-validation) before any write |

Each verb is implemented in `src/project_standards/specs/cli.py`; `spec new` and `spec upgrade` share the `_NewArgParser`/`NewError`-style refusal contract (frozen `code` + `message` + `findings`, `--json` support) so both fail closed rather than emitting a document the validator would reject.

---

## Module map

```text
src/project_standards/
├── cli.py                        # Unified CLI: adopt | list | validate | fix dispatch
├── validate_frontmatter.py       # Schema validator (Draft 2020-12 via jsonschema)
├── validate_id.py                # id-format validator (base-36 and ADR formats)
├── validate_references.py        # Cross-file reference checker (opt-in)
├── format_frontmatter.py         # Frontmatter formatter (--write / --check)
├── registry.py                   # Contract-version registry (reads registry.json)
├── sync_standards_include.py     # Internal maintenance: sync include lists
├── sync_vscode_colors.py         # Internal maintenance: VS Code colour tokens
│
├── schemas/
│   ├── markdown-frontmatter.schema.json   # Bundled JSON Schema (Draft 2020-12)
│   └── registry.json                      # Contract-version compatibility matrix
│
├── adopt/
│   ├── engine.py      # build_plan() + execute_plan() — plan-and-execute model
│   ├── manifest.py    # adopt.toml reader; Artifact + Manifest dataclasses
│   └── errors.py      # AdoptError hierarchy with exit codes
│
└── bundles/
    ├── _shared/               # Artifacts shared across multiple standards
    │   ├── editorconfig
    │   └── vscode-extensions.json
    ├── adr/                   # ADR standard bundle
    ├── markdown-frontmatter/  # Markdown Frontmatter standard bundle
    ├── markdown-tooling/      # Markdown Tooling standard bundle
    └── python-tooling/        # Python Tooling standard bundle
```

---

## Adopt engine

The engine follows a **plan-then-execute** model:

1. **`build_plan(standard_ids)`** — reads each bundle's `adopt.toml`, resolves source paths, deduplicates shared artifacts, and raises `UsageError` on unknown standards or destination collisions between owned artifacts.

2. **`execute_plan(plan, dest_root, …)`** — classifies each action (create / skip / overwrite / symlink-skip), substitutes `{{ref}}` in workflow-caller files with the installed package's major ref (e.g. `v2`), and writes atomically via a temp-file + `os.replace`. Fragments are never written — they are collected in `Report.fragments` and printed so the operator can paste them in manually.

### Artifact kinds

| Kind | Written to disk? | Notes |
| --- | --- | --- |
| `file` | Yes (to `dest`) | Static file copied verbatim |
| `workflow-caller` | Yes (to `dest`) | `{{ref}}` replaced with `v<major>` at write time |
| `fragment` | No | Snippet printed for manual insertion into `target` |

### Ownership and deduplication

Each artifact declares `owner = true/false`. Shared artifacts (e.g. `.editorconfig`) reference a path under `bundles/_shared/` via `shared =` instead of `source =`. When two standards share the same source file, `build_plan` collapses them to one action. Two _different_ sources targeting the same destination is a manifest authoring bug and raises `UsageError` (exit 2).

---

## Contract-version registry (`registry.json`)

The registry encodes the two-plane versioning model:

- **Frontmatter** — maps contract version labels (`"1.0"`, `"1.1"`) to bundled schema file names; one label is the `default` used when no version is pinned.
- **ADR** — each ADR contract version declares `supports_frontmatter: […]`, the Frontmatter versions it is compatible with. The validator enforces this at config load time.
- **Python Tooling / Markdown Tooling** — flat lists of known label versions; validated as metadata only (never used to select a schema).

`cli.py` asserts at startup that the set of bundles and the set of registry-tracked standards are identical in both directions (bundle-only or registry-only → exit 2).

---

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | All files valid / adopt succeeded |
| 1 | Validation errors found (or recoverable I/O failure during adopt) |
| 2 | Invocation or config error (bad flags, unknown standard, registry/bundle drift) |
| 3 | Missing prerequisite (broken manifest, absent bundle source file) |

---

## Configuration file (`.project-standards.yml`)

```yaml
markdown:
  frontmatter:
    version: '1.0' # pin to a bundled Frontmatter contract version
    schema: my-schema.json # OR supply a custom schema path (mutually exclusive with version)
    include:
      - 'docs/**/*.md'
    exclude:
      - 'docs/decisions/**'
    required: true # fail files that have no frontmatter (default: true)
  adr:
    require_sections: true # enforce the three MADR-required ## headings
    version: '1.0' # pin to a bundled ADR contract version

python_tooling:
  version: '1.0' # metadata only; validated but not used to select a schema

markdown_tooling:
  version: '1.0' # metadata only; validated but not used to select a schema
```

---

## Adding a new standard

1. Create `bundles/<standard-id>/` with an `adopt.toml` and the artifact source files.
2. Add the standard's contract versions to `schemas/registry.json` under the appropriate key.
3. Add a `_contract_version()` mapping entry in `cli.py` (`_REGISTRY_STANDARD_IDS`).
4. The registry/bundle parity check in `_assert_registry_bundle_parity()` will catch any mismatch before any command emits output.
