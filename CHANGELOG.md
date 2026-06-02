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
