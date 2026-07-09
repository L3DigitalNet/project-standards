# Standards Adoption & Compliance Procedure

> **You are an agent adopting this standard in another ("consuming") repository.** Follow this procedure end to end. It is self-contained: everything you need to make the changes is here. Where you want the authoritative source, the links in [§8](#8-authoritative-references-pinned) point at the pinned release.
>
> **Release note:** this source branch is accruing unreleased **v5.0.0** changes under the repository's release freeze. Snippets remain pinned to the current package major (`@v4`) until the release checklist bumps them. The repo-local skill install described here ships with v5.0.0 and is **not** present in released `@v4.3.0`. **Owner repo:** `github.com/L3DigitalNet/project-standards`.
>
> **Quick path.** The packaged CLI scaffolds this in one step — `uvx --from 'git+https://github.com/L3DigitalNet/project-standards@v4' project-standards adopt markdown-frontmatter` writes a starter `.project-standards.yml` (only when absent) and the validator workflow caller, both pinned to the current major. Starting with v5.0.0, the same adoption also writes the repo-local Markdown Frontmatter skill under `.agents/skills/markdown-frontmatter`. The detailed procedure below is the manual reference and remains the source of truth for the frontmatter rules.

## 0. What you are doing — definition of done

A repository is **compliant** when:

1. It has a `.project-standards.yml` config declaring which Markdown files are managed.
2. It has a CI workflow that calls the reusable validator, pinned to `@v4` **for both the workflow and the validator/schema**.
3. It has the standard-owned skill installed at `.agents/skills/markdown-frontmatter` so Claude Code and Codex CLI use the same operating layer. This is a v5.0.0+ adoption requirement.
4. Every **managed** Markdown file carries conformant frontmatter (this section's rules), and every **excluded** file (templates, agent-instruction files, agent-skill files) carries no managed-document frontmatter.
5. `uv run project-standards validate --config .project-standards.yml` exits `0` locally and in CI — this runs all three validators the installed workflow runs (schema, id format, references; see [§5](#5-validate-locally)).

Do not modify any file under `.claude/`, `.codex/`, or the repo's `CLAUDE.md` / `AGENTS.md`. The only standard-owned `.agents/` write is the installed skill at `.agents/skills/markdown-frontmatter`; do not add managed-document frontmatter to it. See [§4.1](#41-which-files-are-managed). Do not invent new top-level frontmatter fields — see [§4.4](#44-controlled-values--formatting-rules).

## 1. Prerequisites

- The target is a **git repository** (ideally with GitHub Actions available for CI enforcement).
- [`uv`](https://docs.astral.sh/uv/) is installed locally (for the local validation in [§5](#5-validate-locally)). No checkout of the standards repo is needed — the validator and its bundled schema install from git.
- You know which directories hold the repo's Markdown documentation (e.g. `docs/`, `README.md`).

## 2. Step 1 — add the config (`.project-standards.yml`)

Create `.project-standards.yml` at the repo root. It declares the schema, whether frontmatter is required, and which paths are validated (`include`) vs skipped (`exclude`).

<!-- This fence must stay byte-identical to the adopt bundle's
project-standards.starter.yml — the file `adopt markdown-frontmatter` writes as
.project-standards.yml (guarded by test_adopt_dogfood.py). The bare
prettier-ignore keeps Prettier's embedded formatting from rewriting its quote style. -->
<!-- prettier-ignore -->
```yaml
standards_version: "v4"

markdown:
  frontmatter:
    version: "1.1"
    schema: "markdown-frontmatter"
    required: true
    include:
      - "README.md"
      - "docs/**/*.md"
    exclude:
      # Intentional placeholders / template files (e.g. the ADR template):
      - "**/*.template.md"
      # Non-managed docs:
      - "CHANGELOG.md"
      - "LICENSE.md"
      # Agent-instruction files are harness config, never managed docs:
      - "CLAUDE.md"
      - "AGENTS.md"
      - ".claude/**"
      - ".agents/**"
      - ".codex/**"
      - ".github/**"
      # Tooling / generated content:
      - "node_modules/**"
    # Optional: cross-file checks (id uniqueness, referential integrity, date ordering, ADR-number
    # uniqueness). No-op unless enabled.
    # references:
    #   enabled: true
```

**Selecting a contract version (optional).** `markdown.frontmatter.version` pins which bundled Frontmatter contract validates your documents; omit it to use the tool's current default (today `1.1`, which also accepts legacy `schema_version: '1.0'` documents). A custom `schema:` path owns its own versioning — setting both a custom `schema:` path and `version` is a config error.

**How to choose `include` / `exclude` for this repo:**

- `include` the directories that hold real, maintained documentation. Start narrow (`README.md`, `docs/**/*.md`) and widen later.
- Always `exclude` agent-instruction and agent-skill files (`CLAUDE.md`, `AGENTS.md`, `.claude/**`, `.agents/**`, `.codex/**`) — adding managed-document frontmatter to them is forbidden. The Markdown Frontmatter skill installs under `.agents/**`, so this exclusion is required.
- `exclude` template files with intentional placeholders (the starter's `**/*.template.md` covers the ADR template — keep it), generated output, vendored/third-party Markdown, and tool-owned trees your repo carries (e.g. `.obsidian/**`).
- Cross-file reference checks are opt-in: uncomment the `references:` block and set `enabled: true` (see [§3](#3-step-2--add-the-ci-workflow)).
- The root `README.md` is a managed document by default, but you may `exclude` it if the repo prefers no frontmatter table on its landing page.
- `exclude` patterns match the **file path** via `fnmatch`; a trailing `/**` excludes everything beneath a directory.

## 3. Step 2 — add the CI workflow

Create `.github/workflows/validate-standards.yml` (the file must live under `.github/workflows/`; GitHub only discovers workflows there):

<!-- This fence must stay byte-identical to the adopt bundle's
validate-markdown-frontmatter.caller.yml rendered at the current major — the file
`adopt markdown-frontmatter` writes as validate-standards.yml (guarded by
test_adopt_dogfood.py). The bare prettier-ignore keeps Prettier's embedded
formatting from rewriting its quote style. -->
<!-- prettier-ignore -->
```yaml
name: Validate project standards

on:
  pull_request:
  push:
    branches:
      - main

jobs:
  validate:
    uses: L3DigitalNet/project-standards/.github/workflows/validate-markdown-frontmatter.yml@v4
    with:
      config-path: ".project-standards.yml"
      standards-ref: "v4"
```

> **⚠️ Pin BOTH refs.** `@v4` on the `uses:` line pins the **workflow definition**. The `standards-ref` input pins the **validator + bundled schema** that gets installed; it **defaults to the major tag `v4`** (a pinned major, _not_ `main`), so set it explicitly to the **same ref as your `uses:` pin** (`'v4'`), so the two never drift. For a fully immutable pin, set both to `v4.0.0`.

`validate-markdown-frontmatter.yml` runs **three** validators: schema (`validate-frontmatter`), id format (`validate-id`), and cross-file references (`validate-references`). `validate-references` is a no-op unless `references.enabled: true` in your config.

> **⚠️ Migration warning when re-pinning to `@v4`:** the v4 validator is stricter than v3 on several previously-silent inputs — `date` fields (`created`/`updated`/`reviewed`) now reject full datetime values, the `tags` pattern is tighter (no leading/trailing/consecutive hyphens), non-string frontmatter keys are rejected, and config errors (duplicate top-level config keys, an unquoted numeric `version`, a nonexistent explicit file or `--config` path) now exit 2 instead of passing silently. Consumers with `references.enabled: true` also get corrected cross-file semantics. Follow [`UPGRADING.md`](../../UPGRADING.md) — the step-by-step v3→v4 runbook — before bumping.

The reusable workflow installs the validator with `uv tool install git+…@<standards-ref>`; the schema travels inside the wheel, so the consuming repo never vendors schema or Python code.

If this repo and its consumers are **private**, enable cross-repository workflow access under the standards repo's GitHub **Settings → Actions**.

### Also — optional Markdown body linting

The workflow above validates the YAML _metadata_ block. A **separate, opt-in** reusable workflow lints the Markdown _body_ (heading levels, list style, etc.) with [`markdownlint-cli2`](https://github.com/DavidAnson/markdownlint-cli2) — independent, so frontmatter-only consumers never inherit a Node toolchain:

```yaml
jobs:
  lint-markdown:
    uses: L3DigitalNet/project-standards/.github/workflows/lint-markdown.yml@v4
    with:
      globs: '**/*.md' # optional; this is the default
```

Seed your repo's rules by copying this repo's published [`.markdownlint.json`](../../.markdownlint.json) (the workflow auto-discovers it; the action carries its own Node runtime, so no committed Node project is needed). The two workflows are adopted independently — run either, or both. The published config states **every** rule explicitly, so linting is deterministic and isn't shadowed by a contributor's personal editor/global markdownlint settings. As a consumer your only pin is `lint-markdown.yml@v4`; the underlying `markdownlint-cli2-action@v23` pin (which the explicit config values track) lives **inside** that reusable workflow and is a maintainer concern, not yours.

### Also — pre-commit integration

The standards repo ships six pre-commit hooks that consumers can run locally as a faster feedback loop before CI. (In a repo that also follows the Python Tooling SSOT Standard: using pre-commit solely for these non-Python hooks is explicitly sanctioned by that standard's non-default-tools scope note — no exception ADR is needed.) Add the following stanza to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/L3DigitalNet/project-standards
    rev: v4 # pin to the same major as your CI workflow
    hooks:
      - id: format-frontmatter-fix # auto-formats frontmatter (writes)
      # - id: format-frontmatter-check # read-only alternative
      - id: validate-id-check
      - id: validate-frontmatter
      - id: validate-references # no-op until references.enabled: true
```

`validate-references` runs over the whole repo (`pass_filenames: false`) and is a no-op until you set `references.enabled: true` in your `.project-standards.yml`. All hooks require **Python 3.14+** to be available to pre-commit (matching the `requires-python` of the package).

### Also — repo-local agent skill

The Markdown Frontmatter skill is owned by this standard and must be installed in each adopting repository at `.agents/skills/markdown-frontmatter`. Starting with v5.0.0, the packaged `project-standards adopt markdown-frontmatter` command writes:

- `.agents/skills/markdown-frontmatter/SKILL.md`
- `.agents/skills/markdown-frontmatter/agents/openai.yaml`
- `.agents/skills/markdown-frontmatter/scripts/new-doc-id`

If adopting manually, copy that directory from the pinned standard release. Do not install the canonical skill globally as the source of truth, and do not move it to `.claude/` or `.codex/`; the `.agents/` path is the shared repo-local discovery path for both Claude Code and Codex CLI. The starter config excludes `.agents/**`, so the skill's own skill metadata is never treated as managed document frontmatter.

## 4. Step 3 — bring documents into compliance

### 4.1 Which files are managed

- **Managed** = matches `include` and not `exclude`. Each must carry one conformant frontmatter block (the rules below).
- **Never carries managed-document frontmatter:** `CLAUDE.md`, `AGENTS.md`, and anything under `.claude/`, `.agents/`, `.codex/`. These are harness configuration or agent-skill files. Exclude them; do not add document metadata. The installed `.agents/skills/markdown-frontmatter/SKILL.md` has skill metadata, not this standard's document frontmatter.

### 4.2 Required fields (the eleven)

Every managed document **must** have these, as the first thing in the file, inside a `---` fenced YAML block:

```yaml
---
schema_version: '1.1'
id: 'note-xxxxxx-replace-with-readable-slug'
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

Set `schema_version` to `'1.1'` for new documents. (`'1.0'` is still accepted, so pre-existing documents do not block compliance; prefer `'1.1'` going forward.)

The `id` placeholder shows the required three-part shape — `{doc_type}-{6-char base-36 token}-{readable-slug}` — with `xxxxxx` standing in for the token. Replace the token and slug with real values per the rules in [§4.4](#44-controlled-values--formatting-rules) before relying on CI: `validate-id` rejects ids that do not match the format.

### 4.3 Recommended optional fields (the standard profile)

For most documents, add these too. Place them in canonical order (see [§4.4](#44-controlled-values--formatting-rules)):

```yaml
reviewed: null # date string or null — last correctness review
owner: 'repo-maintainers' # person, team, repo, or role
consumer: 'mix' # intended reader: user | agent | mix | unknown
source: [] # array of sources (URLs/paths)
confidence: 'unknown' # high | medium | low | unknown
visibility: 'internal' # private | internal | public
license: null # string or null
```

Optional relationship fields, used only when needed: `supersedes` (array), `superseded_by` (string or null), `depends_on` (array), `applies_to` (array of free-form scope identifiers).

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
- **`id`** is stable and frozen at creation, in the three-part format `{doc_type}-{6-char base-36 token}-{readable-slug}` (e.g. `note-13qo1q-tailscale-acl-gotcha`, `runbook-0f943i-restart-netbox-after-config-change`): the prefix must equal the document's `doc_type`, the token is exactly 6 characters from `[0-9a-z]`, and the slug is lowercase kebab-case. ADRs instead use `adr-{NNNN}-{repo-name}-{short-title}` with a zero-padded sequence number of at least four digits (e.g. `adr-0001-homelab-use-postgresql-for-persistent-storage` — the repo-name segment is required). Both formats are enforced by `validate-id`.
- **`tags`** are lowercase, kebab-case for multiword, no leading `#`.
- **`description`** is one line, no Markdown, ≤280 chars; state what the doc is for.
- **No unknown top-level fields.** Project- or tool-specific metadata goes under one of the sanctioned extension objects: `publish` (publishing/export), `project`, or `x_project`. Each accepts any structure.
- **Links** (`related`, `supersedes`, `superseded_by`, `depends_on`, and body links) **SHOULD** be **repo-root-relative paths with extensions** (e.g. `docs/architecture.md`), not bare IDs or absolute paths. In v1.1 this is a documented **convention** (the validator does not yet enforce link shape); a future `2.0.0` will enforce it, so authoring paths now keeps you forward-compatible. `applies_to` is exempt — it holds free-form scope identifiers, not links.

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
id: 'runbook-0f943i-restart-netbox-after-config-change'
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
  - 'infrastructure'
  - 'operations'
  - 'runbook'
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
2. For each managed file with **no** frontmatter: prepend a block with at least the eleven required fields, inferring sensible values (`id` generated in the three-part format of [§4.4](#44-controlled-values--formatting-rules) — the `doc_type` prefix, a freshly generated 6-character base-36 token, and a kebab-case slug of the title; `title` from the H1, `created`/`updated` from git history or today, `doc_type` from the document's nature, `status: 'active'` for live docs).
3. For each managed file with **existing** frontmatter: reconcile it to the rules — fix field names (`type` → `doc_type`), quote strings/dates, replace disallowed enum values, remove unknown top-level keys (move them under `project`/`publish`), and order keys canonically.
4. Confirm no excluded/agent-instruction file has frontmatter.
5. Run the local validation ([§5](#5-validate-locally)) and fix every reported error.

## 5. Validate locally

Run the released validator directly — no checkout required:

```bash
uvx --from 'git+https://github.com/L3DigitalNet/project-standards@v4' \
  project-standards validate --config .project-standards.yml
```

This runs all three validators — schema (`validate-frontmatter`), id format (`validate-id`), and cross-file references (`validate-references`, no-op unless `references.enabled: true`) — in a single pass.

**Auto-fix mode:** run `project-standards fix` (same flags) to format frontmatter, regenerate non-compliant ids, and then re-validate. This reduces the manual fixup burden when adopting the standard on an existing codebase. Skips entirely under a custom schema.

**Exit codes:** `0` = all matched files valid (or none matched); `1` = one or more documents failed (each error then a summary prints to stderr); `2` = configuration or schema error (config/schema missing or invalid). Useful flags: `--glob PATTERN` to validate a replacement glob instead of the configured include list, positional `FILE` args to check specific files, `--quiet` to suppress success output, `--no-require-frontmatter` to not fail files lacking a block.

Compliance is reached when this exits `0`.

## 6. Compliance checklist

- [ ] `.project-standards.yml` exists at the repo root with `schema: 'markdown-frontmatter'`, `required: true`, and accurate `include`/`exclude`.
- [ ] `.github/workflows/validate-standards.yml` calls the reusable workflow with **both** `@v4` (on `uses:`) and `standards-ref: 'v4'`.
- [ ] `.agents/skills/markdown-frontmatter/` exists and contains the standard-owned `SKILL.md`, `agents/openai.yaml`, and `scripts/new-doc-id` (v5.0.0+ adoption).
- [ ] Every managed Markdown file has a conformant frontmatter block (required fields present, controlled values valid, strings/dates quoted, no unknown top-level keys, canonical key order).
- [ ] No agent-instruction or agent-skill file (`CLAUDE.md`, `AGENTS.md`, `.claude/**`, `.agents/**`, `.codex/**`) carries managed-document frontmatter, and all are excluded.
- [ ] Links in frontmatter use repo-root-relative paths (convention).
- [ ] `project-standards validate --config .project-standards.yml` exits `0` locally.
- [ ] CI runs the workflow on PRs and `main`.

## 7. Versioning & staying in compliance

- **Pin the major tag `@v4`** (both the `uses:` ref and `standards-ref`). Within a major, a repo that passed validation yesterday will still pass today — additive fields and opt-in features only.
- **A major bump (`@v5`) is intentional work.** It may introduce a new required field or a stricter rule that newly-fails a previously-passing repo. Read the changelog migration notes, bump both pins from `@v4` to `@v5`, and re-run validation before merging.
- For byte-for-byte reproducibility, pin both refs to a full version (`v4.0.0`) or a commit SHA instead of the moving major tag.

## 8. Authoritative references (pinned)

The governing documents at the current release (replace `v4` with `v4.0.0` for an immutable read). The standard-owned skill is staged in this source branch and becomes a pinned release reference at v5.0.0; released `@v4` has no skill artifact.

- **The standard** — [`standards/markdown-frontmatter/README.md@v4`](https://github.com/L3DigitalNet/project-standards/blob/v4/standards/markdown-frontmatter/README.md)
- **The standard-owned skill** (v5.0.0+) — [`standards/markdown-frontmatter/skills/markdown-frontmatter/SKILL.md`](skills/markdown-frontmatter/SKILL.md)
- **The JSON Schema** (authoritative contract) — [`src/project_standards/schemas/markdown-frontmatter.schema.json@v4`](https://github.com/L3DigitalNet/project-standards/blob/v4/src/project_standards/schemas/markdown-frontmatter.schema.json)
- **Versioning Standard** — [`meta/versioning.md@v4`](https://github.com/L3DigitalNet/project-standards/blob/v4/meta/versioning.md)
- **ADR Standard** (if adopting ADRs) — [`standards/adr/README.md@v4`](https://github.com/L3DigitalNet/project-standards/blob/v4/standards/adr/README.md)
- **Consumption overview** — [`README.md@v4`](https://github.com/L3DigitalNet/project-standards/blob/v4/README.md#consuming-the-standards)

Where this procedure and the JSON Schema disagree, **the schema is authoritative**.
