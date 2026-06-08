# `project_standards` — source layout

This is the Python package that ships the validator, adopt engine, bundled schemas, and standard bundles for the **project-standards** tool suite.

---

## CLI surface

Three console scripts are registered by `pyproject.toml`:

| Command | Module | Purpose |
| --- | --- | --- |
| `project-standards adopt STANDARD …` | `cli.py` | Materialize a standard's files into a target repo |
| `project-standards list [--json]` | `cli.py` | List adoptable standards and their artifacts |
| `project-standards validate [FLAGS] [FILE …]` | `cli.py` | Run both validators (schema + id) in one pass |
| `validate-frontmatter [FLAGS] [FILE …]` | `validate_frontmatter.py` | Validate YAML frontmatter against the JSON Schema |
| `validate-id [FLAGS] [FILE …]` | `validate_id.py` | Validate `id` field format per `doc_type` |

`project-standards validate` is an early-dispatch alias that forwards its full argv to both `validate_frontmatter.main()` and `validate_id.main()` and returns the worst exit code so neither validator's errors can be masked by the other's success.

---

## Module map

```text
src/project_standards/
├── cli.py                        # Unified CLI: adopt | list | validate dispatch
├── validate_frontmatter.py       # Schema validator (Draft 2020-12 via jsonschema)
├── validate_id.py                # id-format validator (base-36 and ADR formats)
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
