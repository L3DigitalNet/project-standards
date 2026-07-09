# Adopt the Project Specification Standard

> **Target release:** `project-standards` **v4.0.0** — pin the moving major tag `@v4` (see [§5](#5-versioning--staying-in-compliance)). **The Project Specification Standard is available only from `v4.0.0` onward**: it first ships at the `v4.0.0` release, so no earlier tag (`v3` and below) carries the standard, its CLI, or the `validate-specs.yml` workflow — never pin this standard to a pre-v4 ref.

## 0. What you are doing — definition of done

A repository has adopted this standard when:

1. It has a `spec:` block in `.project-standards.yml` declaring contract version `1.0` and which files are project specs.
2. Every declared spec passes `project-standards spec validate` (the deterministic structural gate).
3. CI runs that same validation on every push/PR, pinned to a release tag.
4. Anyone authoring or extending a spec uses the CLI (`new`, `upgrade`, `next`) rather than hand-editing structure, so the guarantees in [§3](README.md#3-features) hold.

This standard has two adoption pieces. `project-standards adopt project-spec` seeds the repo-local configuration and CI caller. The `project-standards spec` CLI remains the only path that creates real spec documents, because specs need repository-specific titles, IDs, owners, and profile choices.

## 1. Prerequisites

- The target is a **git repository**, ideally with CI available for enforcement.
- [`uv`](https://docs.astral.sh/uv/) is installed locally, for local validation ([§4](#4-validation)). No checkout of this repo is needed — the CLI installs from git.
- **If the repo also adopts the [Markdown Frontmatter Standard](../markdown-frontmatter/README.md):** exclude the spec directory from its `markdown.frontmatter.include`/`exclude` globs. Project specs use their **own** frontmatter schema (`spec_id`, `status`, `profile`, `related`), not the canonical one — the two validators must never compete over the same files. This repository's own config does exactly that: `standards/project-spec/examples/**` is excluded from the Markdown Frontmatter Standard's validator (its dogfood example is a spec document, not a canonical-frontmatter one) and included instead in the [`spec:` block](#3-wire-the-tooling); a consuming repo's real specs directory needs the equivalent split.
- Decide where specs will live in the repo (e.g. `docs/specs/`). The tooling imposes no fixed location — the `spec:` config block's `include` globs are what actually matter.

## 2. Choose a template

Three tiers, matching project size — see [§4 Templates](README.md#4-templates) and the tailoring rules in each template's Appendix D:

- **Light** — scripts, small tools, single-session agent tasks.
- **Standard** — typical features and services.
- **Full** — multi-service systems, durable data, external integrations, or multiple stakeholders.

Scaffold one directly with the CLI — no manual template copying:

```bash
uvx --from 'git+https://github.com/L3DigitalNet/project-standards@v4' \
  project-standards spec new docs/specs/my-feature.md --profile standard --title 'My Feature'
```

This mints a fresh `spec_id`, fills `created`/`profile`/title into the frontmatter, and fail-closed self-validates the result before writing (a scaffold that would not pass `validate` is never written). Useful flags: `--owner`, `--implementer`, `--id SPEC-XXXX` (supply your own id instead of minting one), `--stdout` (preview without writing), `--force` (allow overwriting an existing file), `--json` (machine-readable result). Numbering is stable across all three profiles, so upgrading a spec later ([§3](#3-wire-the-tooling)) never renumbers or breaks existing cross-references.

## 3. Wire the tooling

Run the adopt command to materialize the workflow caller and print the config fragment:

```bash
uvx --from 'git+https://github.com/L3DigitalNet/project-standards@v4' \
  project-standards adopt project-spec --dest .
```

Merge the reported `spec:` fragment into `.project-standards.yml`, declaring which files are project specs:

<!-- prettier-ignore -->
```yaml
# Add the following to your .project-standards.yml.
spec:
  version: "1.0"
  include:
    - "docs/specs/**/*.md"
  exclude: []
```

`version` selects the Project Specification contract version bundled with the installed tool; `1.0` is the current default. `include`/`exclude` accept a string or a list of strings (glob patterns, matched the same way as the Markdown Frontmatter Standard's `include`/`exclude`). A missing `spec:` block is not an error by itself, but every `spec` subcommand that discovers files from config (`validate`, `lint`) requires either this block or explicit file arguments — an empty corpus is refused, not silently passed, so CI can never go green vacuously.

The full CLI surface, once specs exist:

| Command | Does | Example |
| --- | --- | --- |
| `spec validate [FILE...] [--config PATH] [--json]` | Hard pass/fail structural gate (exit 1 on any finding). | `project-standards spec validate` |
| `spec lint [FILE...] [--config PATH] [--strict] [--json]` | Advisory authoring-quality warnings; `--strict` turns warnings into a failing exit. | `project-standards spec lint --strict` |
| `spec extract FILE SELECTOR [--json]` | Print one ID row, numbered section, heading match, or appendix as raw Markdown. | `project-standards spec extract docs/specs/x.md §7` |
| `spec next FILE PREFIX [--json]` | Print the next free ID for a prefix (e.g. `FR-013`). | `project-standards spec next docs/specs/x.md FR` |
| `spec new PATH --profile TIER [...]` | Scaffold a new spec ([§2](#2-choose-a-template)). | see above |
| `spec upgrade SRC --to TIER [-i \| -o PATH \| --stdout]` | Additive tier promotion (Light→Standard→Full): inserts missing sections/appendices at their stable numbers; never renumbers or rewrites existing prose. Refuses (exit 2) unless `SRC` already passes `validate`, and unless its structural scaffolding (gaps, appendix lettering, subsection layout — not the authored requirement/section text) still matches the canonical template for its declared tier. | `project-standards spec upgrade docs/specs/x.md --to full -i` |

All commands default `--config` to `.project-standards.yml`, print human-readable output by default, and accept `--json` for machine consumption. `validate`/`lint` exit `1` on findings (or `--strict` warnings for `lint`); usage/config errors exit `2`.

## 4. Validation

**CI.** The adopt command writes `.github/workflows/validate-specs.yml` with this reusable workflow caller:

<!-- prettier-ignore -->
```yaml
name: Validate project specs

on:
  pull_request:
  push:
    branches:
      - main

jobs:
  validate-specs:
    uses: L3DigitalNet/project-standards/.github/workflows/validate-specs.yml@v4
    with:
      config-path: ".project-standards.yml"
      standards-ref: "v4"
      strict-lint: false
```

> **⚠️ Pin both refs**, exactly as for the [Markdown Frontmatter Standard](../markdown-frontmatter/adopt.md#3-step-2--add-the-ci-workflow): `@v4` on `uses:` pins the workflow definition; `standards-ref` pins the installed CLI. Set them to the same ref so they never drift; use a full version (`v4.0.0`) for a fully immutable pin.

The reusable workflow installs the CLI with `uv tool install git+…@<standards-ref>` (or runs in-place if invoked from this repo itself) and runs `spec validate` (always) and `spec lint --strict` (only if `strict-lint: true`) against the configured `spec:` block.

**Local.** Run the same check directly, no checkout required:

```bash
uvx --from 'git+https://github.com/L3DigitalNet/project-standards@v4' \
  project-standards spec validate --config .project-standards.yml
```

Adoption is complete when this exits `0` and CI runs it on every push/PR.

## 5. Versioning & staying in compliance

- **Keep `spec.version` quoted and current.** The current Project Specification contract is `1.0`. Unknown versions are configuration errors; unquoted numeric versions are rejected because YAML can silently lose precision.
- **Pin the major tag `@v4`** for both the `uses:` ref and `standards-ref`, matching the CI workflow above (`v4.0.0` is the first release that carries this standard). Within a major, additive changes only — a spec that validates clean today keeps validating clean tomorrow.
- **A major bump is intentional work**, same as for the other standards ([§7 Versioning & staying in compliance](../markdown-frontmatter/adopt.md#7-versioning--staying-in-compliance) documents the general policy). Read the CHANGELOG migration notes before re-pinning.

## 6. Authoritative references

- **The standard** — [`standards/project-spec/README.md`](README.md).
- **Consumption overview** — [`README.md`](../../README.md#consuming-the-standards).
- **Versioning Standard** — [`meta/versioning.md`](../../meta/versioning.md).

Where this procedure and the standard's own README disagree, the README is authoritative.
