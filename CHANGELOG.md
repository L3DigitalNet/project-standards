---
schema_version: "1.0"
id: "changelog"
title: "Changelog"
description: "Notable changes to the project-standards repository."
doc_type: "log"
status: "active"
created: "2026-06-02"
updated: "2026-06-02"
reviewed: null
owner: ""
tags:
  - changelog
aliases: []
related:
  - "markdown-frontmatter-standard"
source: []
confidence: "high"
visibility: "internal"
license: null
---

# Changelog

All notable changes to this project are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **ADR Standard** — Architecture Decision Records using the [MADR](https://adr.github.io/madr/)
  format layered on the canonical frontmatter profile.
- `standards/adr.md` — the governing ADR standard: when to write an ADR, MADR body structure
  (required vs optional sections), the MADR→canonical field and status mappings, ID/filename and
  `docs/decisions/` directory conventions, and the supersession workflow.
- `templates/adr.md` (full, with explanations) plus `templates/adr-minimal.md`,
  `templates/adr-bare.md`, and `templates/adr-bare-minimal.md` MADR variants. Replaces the prior
  simple ADR template.
- `examples/adr.example.md` — converted to MADR structure (PostgreSQL decision), with ADR roles
  under the `project` namespace.

### Changed

- Clarified scope in `standards/markdown-frontmatter.md`: agent-instruction files (`CLAUDE.md`,
  `AGENTS.md`, `.claude/`, `.agents/`, `.codex/`) must never carry frontmatter. Updated the README
  downstream-example config to exclude them.

## [0.1.0] — 2026-06-02

### Added

- **Markdown Frontmatter Standard** — a small, portable, tool-neutral metadata profile for
  project documentation.
- `standards/markdown-frontmatter.md` — the governing standard: field definitions, controlled
  values, formatting rules, and extension policy.
- `schemas/markdown-frontmatter.schema.json` — machine-readable JSON Schema (Draft 2020-12);
  eleven required fields, enum-validated `doc_type`/`status`/`confidence`/`visibility`,
  `YYYY-MM-DD` date pattern, and `publish`/`project`/`x_project` extension namespaces.
- `templates/` — `frontmatter-minimal.yml`, `frontmatter-standard.yml`, and document templates
  for note, concept, ADR, runbook, spec, and research types.
- `examples/` — validated worked examples for note, concept, ADR, and runbook documents.
- `tools/validate_frontmatter.py` — CLI validator (files, globs, or config-driven), shipping the
  bundled schema in the wheel for downstream installs.
- `tests/test_validate_frontmatter.py` — 15 cases covering valid and invalid frontmatter plus
  config include/exclude behaviour.
- `.github/workflows/validate-markdown-frontmatter.yml` — CI enforcement, reusable via
  `workflow_call` from downstream repositories.
- `.project-standards.yml` — validator configuration for this repo and the canonical example of
  the downstream config shape.
