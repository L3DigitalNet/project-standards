---
bug_id: '001'
date: '2026-06-07'
title: 'astral-sh/setup-uv@v8 tag withdrawn — broke reusable CI'
services: '[ci, github-actions]'
status: 'fixed'
---

# 001 — `astral-sh/setup-uv@v8` tag withdrawn

**Status:** fixed (shipped in `v2.0.0`, commit `3ece2c9`; fix authored in `ff28d70`).

## Symptom

Workflows pinned to `astral-sh/setup-uv@v8` fail at the install step before any gate runs: `Unable to resolve action astral-sh/setup-uv@v8, unable to find version v8`. Looked unrelated to project code because it dies in `setup-uv`.

## Cause

As of **setup-uv v8.0.0 (March 2026)** Astral stopped publishing moving major/minor tags — there is no `@v8` / `@v8.0` and none will be republished. Only immutable full-version tags (`v8.0.0`, `v8.1.0`, `v8.2.0`, …) and commit SHAs resolve. Deliberate supply-chain hardening (limits blast radius if a maintainer account is compromised), not a transient outage. Verified against the GitHub refs API on 2026-06-07: `git ls-remote` for `v8` returns 404; v7.x still carries moving `v7.6`/`v7.5` tags, confirming the v8.0.0 policy change.

## Blast radius

Three references, one consumer-facing: the **reusable** `validate-markdown-frontmatter.yml` (every downstream repo pinning it red-fails), the repo's own `check.yml`, and the Python Tooling standard's §15 `check.yml` template (any copy-adopter).

## Fix

SHA-pin with a trailing version comment (GitHub/Astral hardening guidance; Dependabot bumps the SHA): `astral-sh/setup-uv@fac544c07dec837d0ccb6301d7b5580bf5edae39 # v8.2.0`. Because the reusable workflow ships under a moving major tag, the fix only reached consumers when `v2` was repointed at the `2.0.0` release.

## Lesson

- A GitHub Action can withdraw its moving major tag. **SHA-pin third-party actions** (with a `# vX.Y.Z` comment + Dependabot), don't trust `@vN` to persist.
- Re-verify embedded action refs with `git ls-remote <repo> refs/tags/<tag>`; Python Tooling §25 records this audit check.
