# Deployed

**Last updated:** 2026-06-06

This repo is consumed as a versioned standard: downstream repos pin a `standards-ref` to a git tag and call the reusable workflow under `.github/workflows/`. "Deployed" here means published git refs on `main`.

| Ref | What it is | Status |
| --- | --- | --- |
| `v1.0.0`–`v1.0.2` | Initial standards + validator + reusable workflow | published on `main` |
| `v1.1.0` | optional `consumer` field; `schema_version` accepts `1.1` | published on `main` |
| `v1.2.0` | `standards/adoption.md` (now `standards/markdown-frontmatter/adopt.md`); pinning hardened; validator crash-safety | published on `main` |
| `v1` (moving) | tracks the newest release — currently `v1.2.0` (`2abea67`) | published on `main` |
| `2.0.0` | **LOCKED** target for the pending release: the 1.3.0 lint/format + MADR-4 work **plus** the Python Tooling SSOT migration (uv_build, src/ layout, basedpyright, coverage, pip-audit), **plus** the per-standard bundle restructure (`standards/<name>/` + `meta/`; docs-only, consumer contract unchanged). **BREAKING** — `requires-python` `>=3.11`→`>=3.13` forces a major bump. Version not yet applied to `pyproject.toml`/`CHANGELOG` header (release ritual does that). | **pending on `testing`, unreleased** |
