---
schema_version: '1.1'
id: 'standards-adoption-procedure'
title: 'Standards Adoption & Compliance Procedure'
description: 'Step-by-step procedure for an agent to adopt the project-standards Markdown Frontmatter Standard in a consuming repository and bring it into compliance.'
doc_type: 'runbook'
status: 'active'
created: '2026-06-03'
updated: '2026-06-03'
reviewed: null
owner: ''
consumer: 'mix'
tags:
  - adoption
  - onboarding
  - compliance
  - frontmatter
aliases:
  - 'Adoption Procedure'
  - 'Onboarding Procedure'
related:
  - 'standards/markdown-frontmatter.md'
  - 'standards/versioning.md'
  - 'README.md'
source: []
confidence: 'high'
visibility: 'public'
license: null
---

# Standards Adoption & Compliance Procedure

> **You are an agent adopting this standard in another ("consuming") repository.**
> Follow this procedure end to end. It is self-contained: everything you need to
> make the changes is here. Where you want the authoritative source, the links in
> [§8](#8-authoritative-references-pinned) point at the pinned release.
>
> **Target release:** `project-standards` **v1.1.0** — pin the moving major tag
> **`@v1`** (it receives only backward-compatible updates; see [§7](#7-versioning--staying-in-compliance)).
> **Owner repo:** `github.com/L3DigitalNet/project-standards`.

## 0. What you are doing — definition of done

A repository is **compliant** when:

1. It has a `.project-standards.yml` config declaring which Markdown files are managed.
2. It has a CI workflow that calls the reusable validator, pinned to `@v1` **for both the workflow and the validator/schema**.
3. Every **managed** Markdown file carries conformant frontmatter (this section's rules), and every **excluded** file (templates, agent-instruction files) carries none.
4. `validate-frontmatter --config .project-standards.yml` exits `0` locally and in CI.

Do not modify any file under `.claude/`, `.agents/`, `.codex/`, or the repo's
`CLAUDE.md` / `AGENTS.md` — see [§4.1](#41-which-files-are-managed). Do not invent
new top-level frontmatter fields — see [§4.4](#44-formatting-rules).

## 1. Prerequisites

- The target is a **git repository** (ideally with GitHub Actions available for CI enforcement).
- [`uv`](https://docs.astral.sh/uv/) is installed locally (for the local validation in [§5](#5-validate-locally)). No checkout of the standards repo is needed — the validator and its bundled schema install from git.
- You know which directories hold the repo's Markdown documentation (e.g. `docs/`, `README.md`).

## 2. Step 1 — add the config (`.project-standards.yml`)

Create `.project-standards.yml` at the repo root. It declares the schema, whether
frontmatter is required, and which paths are validated (`include`) vs skipped
(`exclude`).

```yaml
standards_version: 'v1.1.0'

markdown:
  frontmatter:
    # Bundled schema name — resolves to the standard's JSON Schema. Do not change
    # unless you ship a custom schema.
    schema: 'markdown-frontmatter'
    # true = a managed file with no frontmatter block is an error.
    required: true
    include:
      - 'README.md'
      - 'docs/**/*.md'
    exclude:
      # Intentional placeholders / non-managed docs:
      - 'CHANGELOG.md'
      - 'LICENSE.md'
      # Agent-instruction files are harness config, never managed docs:
      - 'CLAUDE.md'
      - 'AGENTS.md'
      - '.claude/**'
      - '.agents/**'
      - '.codex/**'
      - '.github/**'
      # Tooling / generated content you do not want validated:
      - '.obsidian/**'
      - 'node_modules/**'
```

**How to choose `include` / `exclude` for this repo:**

- `include` the directories that hold real, maintained documentation. Start narrow
  (`README.md`, `docs/**/*.md`) and widen later.
- Always `exclude` agent-instruction files (`CLAUDE.md`, `AGENTS.md`, `.claude/**`,
  `.agents/**`, `.codex/**`) — adding frontmatter to them is forbidden.
- `exclude` template files with intentional placeholders, generated output, and
  vendored/third-party Markdown.
- The root `README.md` is a managed document by default, but you may `exclude` it
  if the repo prefers no frontmatter table on its landing page.
- `exclude` patterns match the **file path** via `fnmatch`; a trailing `/**`
  excludes everything beneath a directory.

## 3. Step 2 — add the CI workflow

Create `.github/workflows/validate-standards.yml` (the file must live under
`.github/workflows/`; GitHub only discovers workflows there):

```yaml
name: Validate project standards

on:
  pull_request:
  push:
    branches:
      - main

jobs:
  validate:
    uses: L3DigitalNet/project-standards/.github/workflows/validate-markdown-frontmatter.yml@v1
    with:
      config-path: '.project-standards.yml'
      standards-ref: 'v1'
```

> **⚠️ Pin BOTH refs.** `@v1` on the `uses:` line pins the **workflow definition**.
> The `standards-ref` input pins the **validator + bundled schema** that gets
> installed; it **defaults to `main`**, so if you omit it your validation silently
> floats on the latest unreleased schema. Always set `standards-ref` to the **same
> major** as the `uses:` pin (`'v1'`). For a fully immutable pin, set both to
> `v1.1.0`.

The reusable workflow installs the validator with `uv tool install git+…@<standards-ref>`;
the schema travels inside the wheel, so the consuming repo never vendors schema or
Python code.

If this repo and its consumers are **private**, enable cross-repository workflow
access under the standards repo's GitHub **Settings → Actions**.

## 4. Step 3 — bring documents into compliance

### 4.1 Which files are managed

- **Managed** = matches `include` and not `exclude`. Each must carry one conformant
  frontmatter block (the rules below).
- **Never carries frontmatter:** `CLAUDE.md`, `AGENTS.md`, and anything under
  `.claude/`, `.agents/`, `.codex/`. These are harness configuration. Exclude them;
  do not add metadata.

### 4.2 Required fields (the eleven)

Every managed document **must** have these, as the first thing in the file, inside
a `---` fenced YAML block:

```yaml
---
schema_version: '1.1'
id: 'replace-with-stable-id'
title: 'Human Title'
description: 'One-sentence description of the document.'
doc_type: 'note'
status: 'draft'
created: 'YYYY-MM-DD'
updated: 'YYYY-MM-DD'
tags: []
aliases: []
related: []
---
```

Set `schema_version` to `'1.1'` for new documents. (`'1.0'` is still accepted, so
pre-existing documents do not block compliance; prefer `'1.1'` going forward.)

### 4.3 Recommended optional fields (the standard profile)

For most documents, add these too. Place them in canonical order (see
[§4.4](#44-formatting-rules)):

```yaml
reviewed: null            # date string or null — last correctness review
owner: ''                 # person, team, repo, or role
consumer: 'unknown'       # intended reader: user | agent | mix | unknown
source: []                # array of sources (URLs/paths)
confidence: 'unknown'     # high | medium | low | unknown
visibility: 'internal'    # private | internal | public
license: null             # string or null
```

Optional relationship fields, used only when needed: `supersedes` (array),
`superseded_by` (string or null), `depends_on` (array), `applies_to` (array of
free-form scope identifiers).

### 4.4 Controlled values & formatting rules

**Controlled vocabularies** — these fields accept only these values:

| Field | Allowed values |
| --- | --- |
| `doc_type` | `index`, `note`, `concept`, `reference`, `runbook`, `spec`, `plan`, `adr`, `decision`, `research`, `template`, `log`, `prompt`, `schema` |
| `status` | `draft`, `active`, `review`, `deprecated`, `archived`, `superseded`, `stub` |
| `confidence` | `high`, `medium`, `low`, `unknown` |
| `visibility` | `private`, `internal`, `public` |
| `consumer` | `user`, `agent`, `mix`, `unknown` |

`stub` is a `status`, never a `doc_type`. Use `doc_type` (not `type`).

**Formatting rules** (the validator enforces the machine-checkable ones):

- **Quote all strings**, including dates: `created: '2026-06-03'`, not `2026-06-03`.
- **Dates** are `YYYY-MM-DD` strings.
- **Identifier-like numbers are strings**: `schema_version: '1.1'`, `zip_code: '01234'`.
- **Non-empty lists** use block style (`- 'item'` per line); **empty lists** use `[]`.
- **No duplicate items** in array fields.
- **`id`** is a stable kebab/numeric slug, lowercase, matching `^[a-z0-9][a-z0-9._-]*$`
  (e.g. `tailscale-acl-gotcha`, `adr-0001-use-postgres`).
- **`tags`** are lowercase, kebab-case for multiword, no leading `#`.
- **`description`** is one line, no Markdown, ≤280 chars; state what the doc is for.
- **No unknown top-level fields.** Project- or tool-specific metadata goes under one
  of the sanctioned extension objects: `publish` (publishing/export), `project`, or
  `x_project`. Each accepts any structure.
- **Links** (`related`, `supersedes`, `superseded_by`, `depends_on`, and body links)
  **SHOULD** be **repo-root-relative paths with extensions** (e.g.
  `docs/architecture.md`), not bare IDs or absolute paths. In v1.1 this is a
  documented **convention** (the validator does not yet enforce link shape); a future
  `2.0.0` will enforce it, so authoring paths now keeps you forward-compatible.
  `applies_to` is exempt — it holds free-form scope identifiers, not links.

**Canonical key order** — when present, keys appear in this order:

```text
schema_version, id, title, description, doc_type, status, created, updated,
reviewed, owner, consumer, tags, aliases, related, supersedes, superseded_by,
depends_on, applies_to, source, confidence, visibility, license,
publish, project, x_project
```

### 4.5 Worked example (a compliant standard-profile document)

```yaml
---
schema_version: '1.1'
id: 'restart-netbox-after-config-change'
title: 'Restart netbox after config change'
description: 'Procedure to safely reload netbox after editing its configuration.'
doc_type: 'runbook'
status: 'active'
created: '2026-03-10'
updated: '2026-06-03'
reviewed: '2026-06-03'
owner: 'platform-team'
consumer: 'user'
tags:
  - 'netbox'
  - 'restart'
aliases:
  - 'netbox-restart'
related:
  - 'docs/architecture.md'
source: []
confidence: 'high'
visibility: 'internal'
license: null
project:
  service: 'netbox'
  environment: 'home-lab'
---

# Restart netbox after config change

...document body...
```

### 4.6 Procedure to bring the repo into compliance

1. Enumerate the files matched by `include` minus `exclude`.
2. For each managed file with **no** frontmatter: prepend a block with at least the
   eleven required fields, inferring sensible values (`id` from the filename/slug,
   `title` from the H1, `created`/`updated` from git history or today, `doc_type`
   from the document's nature, `status: 'active'` for live docs).
3. For each managed file with **existing** frontmatter: reconcile it to the rules —
   fix field names (`type` → `doc_type`), quote strings/dates, replace disallowed
   enum values, remove unknown top-level keys (move them under `project`/`publish`),
   and order keys canonically.
4. Confirm no excluded/agent-instruction file has frontmatter.
5. Run the local validation ([§5](#5-validate-locally)) and fix every reported error.

## 5. Validate locally

Run the released validator directly — no checkout required:

```bash
uvx --from 'git+https://github.com/L3DigitalNet/project-standards@v1' \
  validate-frontmatter --config .project-standards.yml
```

**Exit codes:** `0` = all matched files valid (or none matched); `1` = one or more
documents failed (each error then a summary prints to stderr); `2` = configuration
or schema error (config/schema missing or invalid). Useful flags: `--glob PATTERN`
to add files, positional `FILE` args to check specific files, `--quiet` to suppress
success output, `--no-require-frontmatter` to not fail files lacking a block. Run
`validate-frontmatter --help` for the full list.

Compliance is reached when this exits `0`.

## 6. Compliance checklist

- [ ] `.project-standards.yml` exists at the repo root with `schema: 'markdown-frontmatter'`, `required: true`, and accurate `include`/`exclude`.
- [ ] `.github/workflows/validate-standards.yml` calls the reusable workflow with **both** `@v1` (on `uses:`) and `standards-ref: 'v1'`.
- [ ] Every managed Markdown file has a conformant frontmatter block (required fields present, controlled values valid, strings/dates quoted, no unknown top-level keys, canonical key order).
- [ ] No agent-instruction file (`CLAUDE.md`, `AGENTS.md`, `.claude/**`, `.agents/**`, `.codex/**`) carries frontmatter, and all are excluded.
- [ ] Links in frontmatter use repo-root-relative paths (convention).
- [ ] `validate-frontmatter --config .project-standards.yml` exits `0` locally.
- [ ] CI runs the workflow on PRs and `main`.

## 7. Versioning & staying in compliance

- **Pin the major tag `@v1`** (both the `uses:` ref and `standards-ref`). Within a
  major, a repo that passed validation yesterday will still pass today — additive
  fields and opt-in features only.
- **A major bump (`@v2`) is intentional work.** It may introduce a new required
  field or a stricter rule that newly-fails a previously-passing repo (for v1.x, the
  planned `2.0.0` will enforce repo-root-relative link paths). Read the changelog
  migration notes, bump both pins from `@v1` to `@v2`, and re-run validation before
  merging.
- For byte-for-byte reproducibility, pin both refs to a full version (`v1.1.0`) or a
  commit SHA instead of the moving major tag.

## 8. Authoritative references (pinned)

The governing documents at the current release (replace `v1` with `v1.1.0` for an
immutable read):

- **The standard** — [`standards/markdown-frontmatter.md@v1`](https://github.com/L3DigitalNet/project-standards/blob/v1/standards/markdown-frontmatter.md)
- **The JSON Schema** (authoritative contract) — [`schemas/markdown-frontmatter.schema.json@v1`](https://github.com/L3DigitalNet/project-standards/blob/v1/schemas/markdown-frontmatter.schema.json)
- **Versioning Standard** — [`standards/versioning.md@v1`](https://github.com/L3DigitalNet/project-standards/blob/v1/standards/versioning.md)
- **ADR Standard** (if adopting ADRs) — [`standards/adr.md@v1`](https://github.com/L3DigitalNet/project-standards/blob/v1/standards/adr.md)
- **Consumption overview** — [`README.md@v1`](https://github.com/L3DigitalNet/project-standards/blob/v1/README.md#consuming-the-standards)

Where this procedure and the JSON Schema disagree, **the schema is authoritative**.
