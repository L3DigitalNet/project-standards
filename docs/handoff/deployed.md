# Deployed

**Last updated:** 2026-07-19

> **Prepared, not published:** release 5.0.2 (additive internal `standard-bundle-authoring@2.1`, PATCH under the internal-additive classification rule) is prepared on `testing`. It appears below only after the owner lands it on `main` and pushes the signed tags.

This repo is consumed as a versioned standard: downstream repos pin a `standards-ref` to a git tag and call the reusable workflow under `.github/workflows/`. "Deployed" here means published git refs on `main`.

| Ref | What it is | Status |
| --- | --- | --- |
| `v1.0.0`–`v1.0.2` | Initial standards + validator + reusable workflow | published on `main` |
| `v1.1.0` | optional `consumer` field; `schema_version` accepts `1.1` | published on `main` |
| `v1.2.0` | adoption runbook (shipped then as `standards/adoption.md`, since relocated to `standards/markdown-frontmatter/adopt.md`); pinning hardened; validator crash-safety | published on `main` |
| `v1` (frozen) | last `v1.x` release — `v1.2.0` (commit `7450170`); does **not** advance to 2.0.0 (breaking), so `@v1` trackers stay on 1.2.0 | published on `main` |
| `v2.0.0` | lint/format + MADR-4, Python Tooling SSOT migration (uv_build, src/ layout, basedpyright, coverage, pip-audit), per-standard bundle restructure (`standards/<name>/` + `meta/`), Markdown Tooling Standard (`standards/markdown-tooling/` + `lint-markdown.yml@v2`), per-standard contract versions, Python baseline 3.13→3.14, `setup-uv` SHA-pin. **BREAKING** — `requires-python` `>=3.11`→`>=3.14`; see `CHANGELOG.md` migration notes. | published on `main` |
| `v2` (frozen) | last `2.x` release — `v2.0.0` (commit `3ece2c9`); does **not** advance to 3.0.0 (breaking), so `@v2` trackers stay on 2.0.0 | published on `main` |
| `v3.0.0` | `format-frontmatter` + opt-in `validate-references` + `project-standards fix`; `validate` runs all three validators; `.pre-commit-hooks.yaml`. **BREAKING** — `validate-id` now runs in the reusable CI workflow (old-style kebab ids fail) and `parse_frontmatter` rejects duplicate top-level keys; see `CHANGELOG.md` "Migration from v2" + [`UPGRADING.md`](../../UPGRADING.md). | published on `main` |
| `v3` (frozen) | last `3.x` release — `v3.0.0` (commit `e69ab6b`); does **not** advance to 4.0.0 (breaking), so `@v3` trackers stay on 3.0.0 | published on `main` |
| `v4.0.0` | Project Specification Standard (5th standard: tiered templates, `spec` CLI, `validate-specs.yml` reusable workflow). **BREAKING** — six validator/config strictness bumps (datetime dates, tag pattern, non-string keys, duplicate config keys, unquoted numeric `version`, nonexistent path → exit 2) + `validate-references` semantic corrections (opt-in only) + Python Tooling ruff floor `>=0.14` on re-sync; see `CHANGELOG.md` "Migration from v3" + [`UPGRADING.md`](../../UPGRADING.md). Release commit `c7c2fd8`; GitHub release live. | published on `main` |
| `v4.1.0` | Project Specification: `spec.reference_prefixes` config key + token hygiene (built-in `ADR` prefix, SPDX/license-token skip), opt-in `spec upgrade --config`. Backward-compatible loosening — **MINOR**; `@v4` inherits. Release commit `84c0054`; GitHub release live. | published on `main` |
| `v4.2.0` | Markdown Tooling: opt-in reusable Prettier gate (`format.yml` dual-role + adoptable `format.caller.yml`, pinned Prettier `3.8.3`, `prettier: false` opt-out), `markdown_tooling 1.0→1.1`, DEC-9→DEC-10, repo-local coherence tool. Additive/opt-in — **MINOR**. Release commit `6614612`; GitHub release live. | published on `main` |
| `v4.3.0` | CLI Documentation Standard (6th standard: `standards/cli-documentation/` bundle, adopt artifacts `docs/usage.md` scaffold + `cli-docs-check.yml` template + config fragment, `cli_documentation` contract `1.0` in `registry.json`), `--version` on all seven console scripts, `--help` fixed on the two sync commands, dogfood `docs/usage.md` + inventory-parity/installed-wrapper tests. Additive — **MINOR**; `@v4` inherits. Release commit `74db623`; GitHub release live. | published on `main` |
| `v4` (moving) | tracks the newest 4.x release (`v4.3.0`) | published on `main` |
| `v5.0.0` | Unified `.standards/` control plane, catalog 5 packages, migration and composition engine, source/wheel compatibility matrix, and updated reusable workflows. **BREAKING**; see [`UPGRADING.md`](../../UPGRADING.md). Release commit `8869a08`; signed tag and GitHub release assets live. | published on `main` |
| `v5.0.1` | Drift-audit corrections for bounded provider integrity, Agent Handoff error classification, package-contract enforcement, source/wheel parity, and current Catalog 5 documentation. **PATCH** — no immutable payload, catalog selection, public command, accepted input, or conforming consumer outcome changed. Release commit `0390b9e`; signed tag and GitHub release assets live. | published on `main` (Latest) |
| `v5` (moving) | tracks the newest 5.x release (`v5.0.1`) | published on `main` |
