# Deployed

**Last updated:** 2026-06-07

This repo is consumed as a versioned standard: downstream repos pin a `standards-ref` to a git tag and call the reusable workflow under `.github/workflows/`. "Deployed" here means published git refs on `main`.

| Ref | What it is | Status |
| --- | --- | --- |
| `v1.0.0`–`v1.0.2` | Initial standards + validator + reusable workflow | published on `main` |
| `v1.1.0` | optional `consumer` field; `schema_version` accepts `1.1` | published on `main` |
| `v1.2.0` | adoption runbook (shipped then as `standards/adoption.md`, since relocated to `standards/markdown-frontmatter/adopt.md`); pinning hardened; validator crash-safety | published on `main` |
| `v1` (frozen) | last `v1.x` release — `v1.2.0` (commit `7450170`); does **not** advance to 2.0.0 (breaking), so `@v1` trackers stay on 1.2.0 | published on `main` |
| `v2.0.0` | lint/format + MADR-4, Python Tooling SSOT migration (uv_build, src/ layout, basedpyright, coverage, pip-audit), per-standard bundle restructure (`standards/<name>/` + `meta/`), Markdown Tooling Standard (`standards/markdown-tooling/` + `lint-markdown.yml@v2`), per-standard contract versions, Python baseline 3.13→3.14, `setup-uv` SHA-pin. **BREAKING** — `requires-python` `>=3.11`→`>=3.14`; see `CHANGELOG.md` migration notes. | published on `main` |
| `v2` (moving) | tracks the newest 2.x release — currently `v2.0.0` | published on `main` |
