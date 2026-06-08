---
schema_version: '1.1'
id: runbook-b07x48-adopt-the-python-tooling-ssot-standard
title: 'Adopt the Python Tooling SSOT Standard'
description: 'How to adopt the Python Tooling SSOT Standard: copy the in-doc scaffolds and run the verification gate; there is no reusable workflow.'
doc_type: 'runbook'
status: 'active'
created: '2026-06-06'
updated: '2026-06-06'
reviewed: null
owner: ''
consumer: 'agent'
tags:
  - 'adoption'
  - 'python'
  - 'tooling'
aliases: []
related:
  - 'standards/python-tooling/README.md'
source: []
confidence: 'high'
visibility: 'public'
license: null
---

# Adopt the Python Tooling SSOT Standard

Unlike the Markdown standards, this one is **not** enforced by the shared validator and ships **no reusable workflow**. Adoption is copy-the-scaffolds plus run-the-gate. The scaffolds live inline in [the standard](README.md).

## Quick adoption (CLI)

As of `v2`, the packaged CLI materializes the scaffolds in one command:

```bash
uvx --from 'git+https://github.com/L3DigitalNet/project-standards@v2' \
  project-standards adopt python-tooling
```

This writes `.python-version`, `.github/workflows/check.yml`, `scripts/check.py`, the agent entry points (`AGENTS.md`/`CLAUDE.md`), and the shared `.editorconfig` and `.vscode/extensions.json`. The `pyproject.toml` sections are **reported, not written** (the CLI never edits an existing config in place) — copy the printed block into your `pyproject.toml`. Existing files are skipped unless you pass `--force`. Then run the verification gate (below). The manual steps remain the reference for what each scaffold is.

## Steps

1. **Copy the scaffolds** from [the standard](README.md): the `pyproject.toml` baseline (§6), `.python-version`, `.editorconfig` (§14), `.vscode/` config (§13), `.github/workflows/check.yml` (§15), the agent entry points (§16–17), and optionally `scripts/check.py` (§18).
2. **Run the verification gate** (standard §2):

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run coverage run -m pytest
uv run coverage report
uv run pip-audit
```

3. **Migrating an existing repo?** Follow the staged migration guide (standard §21).
4. **Need an exception?** Record it as an ADR (standard §20); see the [ADR Standard](../adr/README.md).
