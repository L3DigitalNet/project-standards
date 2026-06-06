---
schema_version: '1.1'
id: 'changelog'
title: 'Changelog'
description: 'Notable changes to the project-standards repository.'
doc_type: 'log'
status: 'active'
created: '2026-06-02'
updated: '2026-06-06'
reviewed: null
owner: ''
tags:
  - changelog
aliases: []
related:
  - 'markdown-frontmatter-standard'
source: []
confidence: 'high'
visibility: 'internal'
license: null
---

# Changelog

All notable changes to this project are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Python tooling stack adopted from `standards/python-tooling-ssot-standard.md`:** `uv_build` backend, `src/` layout, the validator moved to `src/project_standards/` with the schema bundled inside the package, `basedpyright` (strict), branch coverage (`fail_under = 85`), and `pip-audit`. CI gate consolidated to `check.yml`.
- **Opt-in ADR section check (`markdown.adr.require_sections`).** A new, default-off config flag makes the validator additionally assert that every `doc_type: adr` document contains the three MADR-required level-2 sections — `## Context and Problem Statement`, `## Considered Options`, `## Decision Outcome`. The match is exact and case-sensitive; headings inside fenced code blocks (e.g. template snippets) and the optional MADR sections are correctly ignored. It lives under a separate `markdown.adr` config namespace, keeping the validator's frontmatter remit distinct. This repo enables it to dogfood the shipped ADR example. Additive (default off) → MINOR.
- **Opt-in Markdown body linting (Stack B).** A new reusable workflow `.github/workflows/lint-markdown.yml` runs `markdownlint-cli2` (via `DavidAnson/markdownlint-cli2-action@v23`) against the repo's published `.markdownlint.json`, finally executing the Markdown _body_ rules that previously shipped as config with no runner. It is **separate** from `validate-markdown-frontmatter.yml` so frontmatter-only consumers never inherit a Node toolchain — opt in with `uses: L3DigitalNet/project-standards/.github/workflows/lint-markdown.yml@v1`. The action bundles its own Node runtime and auto-discovers `.markdownlint.json`, so no committed Node project is required. Also adds `.markdownlint-cli2.jsonc` (a local-runner config that honors `.gitignore`, so a bare `npx markdownlint-cli2` matches CI) and a `github-actions` Dependabot entry to keep the action pins current. Additive — pin `@v1`.

### Changed

- **BREAKING (CLI consumers): `requires-python` raised `>=3.11` → `>=3.13`.** Installs via `uv tool install` now require Python 3.13+.
- **BREAKING (docs layout): `standards/` restructured into one self-contained bundle per governing standard** — `standards/<name>/{README.md, adopt.md, templates/, examples/}`. The flat top-level `templates/` and `examples/` trees were dissolved into the bundles, and `versioning.md` moved to `meta/`. Added `standards/README.md` (index + bundle anatomy) and per-standard `adopt.md` entries. Doc deep-links change; the **consumer contract is unchanged** — reusable workflow names, the `validate-frontmatter` package + entry point, and the bundled schema path are identical.
- **`.markdownlint.json` now states every rule explicitly (53 rules), not just the 13 overrides.** A consuming repo that seeds its config from ours now gets deterministic linting that isn't shadowed by a contributor's personal editor/global markdownlint settings, and is pinned against default drift across markdownlint versions. Behaviour is identical to the previous sparse config in a clean environment (verified: the repo lints with zero errors either way, and the explicit config validates against the v0.40.0 config schema). One subtlety encoded: `MD043` stays `true` (inert) rather than its schema-declared `headings: []` default, which would otherwise demand zero headings (a `tests/test_markdownlint_config.py` guard pins that and the customisations). Because the explicit values track a markdownlint version, the `markdownlint-cli2-action@v23` pin is load-bearing — re-verify on upgrade.
- **ADR Standard — body structure now lists three required sections, not four.** `standards/adr/README.md` previously marked **Consequences** as a fourth required section; MADR 4.0 (and the repo's own templates and worked example) treat it as an _optional_ `### Consequences` sub-section of Decision Outcome. The required set is now the three MADR-required `##` sections, matching the new opt-in validator check. Prose-only correction — no document that previously passed can newly fail.
- **`.markdownlint.json` — `MD024` (no-duplicate-heading) now `false`**, matching MADR 4.0's own `template/.markdownlint.yml` (was `{ siblings_only: true }`). MADR ADRs repeat option headings across the _Considered Options_ and _Pros and Cons_ sections; disabling the rule mirrors upstream tooling exactly. Strictly looser than before, so no previously-passing document can newly fail — additive.
- **ADR Standard — corrected the MADR acronym expansion** from "Markdown _Any_ Decision Records" to "Markdown _Architectural_ Decision Records" in `standards/adr/README.md`. MADR 4.0 (2024-09-17) reverted the name to "Architectural"; the prior wording tracked the superseded MADR 3.x spelling.
- **ADR Standard — `id` now embeds the repo-name for cross-repo uniqueness.** ADR ids become `adr-NNNN-repo-name-short-title` (e.g. `adr-0001-homelab-use-postgresql-for-persistent-storage`) so that an ADR referenced from another repository's `related:` list stays globally unambiguous across a fleet of repos. The **filename** keeps the `adr-NNNN-short-title.md` form — `adr-` prefix, no repo-name — making ADRs the one documented case where filename and `id` differ, consistent with the standard's existing "`id` is independent of file path" rule. Templates show the `repo-name` slot plus a save-as comment; the worked example and its two inbound `related:` references were updated to match. Deliberately diverges from MADR's bare-number filenames (MADR tooling is an optional convenience here, not a conformance target). Greenfield (no consumer ADRs exist yet) and filenames are not schema-validated, so nothing can newly fail — additive.

## [1.2.0] — 2026-06-03

### Added

- **Standards Adoption & Compliance Procedure** — `standards/adoption.md`, a self-contained, agent-oriented runbook for adopting the standards in a consuming repository: the config and CI setup (pinning both the workflow `@v1` and the `standards-ref` so the schema does not float on `main`), the full frontmatter rules and controlled vocabularies, a worked example, and a compliance checklist. Pin `@v1`.

### Changed

- **Reusable workflow — `standards-ref` default `main` → `v1`.** A consumer who pins `uses: …@v1` but omits `standards-ref` previously installed the validator and bundled schema from `main`, silently floating their validation on unreleased changes. The default now tracks the major tag, so the workflow pin and the validator/schema pin stay aligned by default. Non-breaking: within a major, `main` only accumulates additive changes, so this can never newly-fail a previously-passing caller (MINOR per the previously-passing rule).
- **README consuming guide** — the example now sets `standards-ref: 'v1'` with a "pin both refs" note, no longer excludes `docs/adr/**` / `docs/decisions/**` (ADRs are managed documents and should validate), and uses a current `standards_version` example.
- **Versioning Standard** — reworded the reusable-workflow row of the classification table so a default change that _cannot_ fail a previously-passing caller is explicitly MINOR (not MAJOR), aligning the table with the governing previously-passing rule.
- **Markdown Frontmatter Standard** — corrected example values that still referenced the former "YAML Frontmatter Standard" name.

### Fixed

- **Validator no longer crashes on malformed YAML.** A syntactically broken frontmatter block now reports a clean validation error and exits `1` (instead of dumping an uncaught traceback), and a malformed `.project-standards.yml` returns the documented config-error exit `2`. A single downstream typo can no longer crash the tool.

## [1.1.0] — 2026-06-03

### Added

- **`consumer` frontmatter field** — new optional standard-profile field with controlled values `user | agent | mix | unknown`, recording a document's intended reader. Added to the JSON schema, the standard, templates, examples, and validator tests. Additive: documents that omit it stay valid, so this reaches `@v1` consumers automatically.
- **Project license** — added the Apache-2.0 `LICENSE` file and Python package metadata so GitHub and built wheels identify the project license consistently.

### Changed

- **Frontmatter schema version → `1.1`** — the `schema_version` enum now accepts `'1.1'` alongside `'1.0'`; this repository's standard, templates, and examples declare `schema_version: '1.1'`. Existing `'1.0'` documents remain valid (the enum keeps both), so the bump is non-breaking.
- **Markdown Frontmatter Standard promoted to V1.1** — `standards/markdown-frontmatter.md` gained dedicated sections (scalar value rules, list rules, canonical key order, description, tags, aliases, links) and a valid-frontmatter template; its Versioning and Validation sections were trimmed to point at `standards/versioning.md` and the README rather than restate them.
- **`visibility` description** — narrowed to "Exposure level" now that `consumer` owns the audience dimension. Enum values unchanged; no validation outcome changes.
- **Link form is now a documented convention** — `related`, `supersedes`, `superseded_by`, `depends_on`, and body links SHOULD use repo-root-relative paths (extension included). This is convention only in `1.1.0`, not schema-enforced; path-pattern enforcement is planned for a future `2.0.0`. No `1.1.0` validation behaviour changes.
- **Versioning Standard** — the moving-major-tag step now documents deleting and re-pushing the tag (`git push origin :refs/tags/vN` then `git push origin vN`) instead of `git push --force`. Identical end state, but it avoids the force flag blocked by the repository's `release-pipeline` force-push guard and cannot clobber branch history.

## [1.0.2] — 2026-06-02

### Added

- **Versioning Standard** — `standards/versioning.md` governs how this repository's releases are numbered, tagged, and consumed. Defines the consumer-outcome contract (a release's level reflects the worst-case impact across the standard, schema, validator, and workflow), the per-component MAJOR/MINOR/PATCH classification table, the "previously-passing → now-failing is always MAJOR" rule, and the release requirements (signed full-version tags, the moving major tag, version + changelog bumps). The README `## Versioning` section is now a summary linking to it.

### Changed

- **Repository owner** — transferred from `chrisdpurcell` to the `L3DigitalNet` organization. Updated every in-repo reference to the canonical owner: the reusable workflow's `github.repository` self-identity guards and `uv tool install` URL, the README and `standards/versioning.md` adoption examples, and the JSON Schema `$id`. Not a MAJOR change under the versioning standard — GitHub redirects the old path, so previously-passing consumers continue to pass — but consumers should re-pin `uses:` to `L3DigitalNet/project-standards` rather than rely on the redirect.

## [1.0.1] — 2026-06-02

### Changed

- **CI — reusable validation workflow** — bumped `actions/checkout` (v4 → v6) and `astral-sh/setup-uv` (v5 → v7) so both run on Node 24, clearing the GitHub Actions Node 20 deprecation warning. Scoped uv's dependency cache to this repo via `enable-cache`, since only this repo ships the `uv.lock` the cache keys on; consuming repos (which install the validator with `uv tool install` from git) no longer emit the "cache will never get invalidated" warning. Behaviour-only change to CI plumbing — the validator, schema, and standards are untouched, so `@v1` consumers receive it with no validation impact.
- **Docs** — recommend pinning the reusable workflow and CLI by major tag (`@v1`) for automatic non-breaking fixes; full version tags (`@v1.0.1`) and commit SHAs remain available for immutable pins.

## [1.0.0] — 2026-06-02

### Added

- **ADR Standard** — Architecture Decision Records using the [MADR](https://adr.github.io/madr/) format layered on the canonical frontmatter profile.
- `standards/adr.md` — the governing ADR standard: when to write an ADR, MADR body structure (required vs optional sections), the MADR→canonical field and status mappings, ID/filename and `docs/decisions/` directory conventions, and the supersession workflow.
- `templates/adr.md` (full, with explanations) plus `templates/adr-minimal.md`, `templates/adr-bare.md`, and `templates/adr-bare-minimal.md` MADR variants. Replaces the prior simple ADR template.
- `examples/adr.example.md` — converted to MADR structure (PostgreSQL decision), with ADR roles under the `project` namespace.

### Changed

- Clarified scope in `standards/markdown-frontmatter.md`: agent-instruction files (`CLAUDE.md`, `AGENTS.md`, `.claude/`, `.agents/`, `.codex/`) must never carry frontmatter. Updated the README downstream-example config to exclude them.

### Fixed

- Validator exclude patterns now match via `fnmatch` on the file path instead of `Path.glob`, making directory excludes (e.g. `docs/decisions/**`) behave identically across Python versions. Previously such patterns silently failed to exclude nested files on Python ≤3.12, where a trailing `**` matches directories only.

## [0.1.0] — 2026-06-02

### Added

- **Markdown Frontmatter Standard** — a small, portable, tool-neutral metadata profile for project documentation.
- `standards/markdown-frontmatter.md` — the governing standard: field definitions, controlled values, formatting rules, and extension policy.
- `schemas/markdown-frontmatter.schema.json` — machine-readable JSON Schema (Draft 2020-12); eleven required fields, enum-validated `doc_type`/`status`/`confidence`/`visibility`, `YYYY-MM-DD` date pattern, and `publish`/`project`/`x_project` extension namespaces.
- `templates/` — `frontmatter-minimal.yml`, `frontmatter-standard.yml`, and document templates for note, concept, ADR, runbook, spec, and research types.
- `examples/` — validated worked examples for note, concept, ADR, and runbook documents.
- `tools/validate_frontmatter.py` — CLI validator (files, globs, or config-driven), shipping the bundled schema in the wheel for downstream installs.
- `tests/test_validate_frontmatter.py` — 15 cases covering valid and invalid frontmatter plus config include/exclude behaviour.
- `.github/workflows/validate-markdown-frontmatter.yml` — CI enforcement, reusable via `workflow_call` from downstream repositories.
- `.project-standards.yml` — validator configuration for this repo and the canonical example of the downstream config shape.
