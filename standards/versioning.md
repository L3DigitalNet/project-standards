---
schema_version: '1.0'
id: 'versioning-standard'
title: 'Versioning Standard'
description: 'How releases of this repository are numbered, tagged, and consumed — a consumer-outcome contract over the standard, schema, validator, and workflow.'
doc_type: 'reference'
status: 'active'
created: '2026-06-02'
updated: '2026-06-02'
reviewed: null
owner: ''
tags:
  - versioning
  - releases
  - semver
aliases: []
related:
  - 'markdown-frontmatter-standard'
  - 'adr-standard'
source:
  - 'https://semver.org/spec/v2.0.0.html'
  - 'https://keepachangelog.com/en/1.1.0/'
confidence: 'high'
visibility: 'internal'
license: null
---

# Versioning Standard

## Purpose

This repository ships **four things under one version number**: the
**standard** (`standards/`), the **JSON schema** (`schemas/`), the **validator
CLI** (`tools/`, distributed as the `project-standards` package), and the
**reusable workflow** (`.github/workflows/validate-markdown-frontmatter.yml`).
Consuming repositories pin a single git tag and receive all four together.

This document defines what a release number promises, how to classify a change,
and the operational requirements for cutting a release. It governs this
repository's own releases; it is not the metadata standard for documents (see
[`markdown-frontmatter.md`](markdown-frontmatter.md)).

## What a version promises

Releases follow [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html)
(`MAJOR.MINOR.PATCH`), but the compatibility being versioned is **the consuming
repository's validation outcome**, not a code API.

> **Governing principle.** A release tag is a contract about what happens to a
> consuming repository on its next pull. A release's level is the **worst-case
> impact of any single change** across all four shipped components.

This reframing is what makes the moving major tag (`@v1`) safe to track
unattended: within a major, a consumer that passed validation yesterday will
still pass today.

## Change classification

Classify each release by the highest-severity change it contains.

| Component | MAJOR — migrate intentionally | MINOR — safe to inherit on `@vN` | PATCH — no consumer-visible change |
| --- | --- | --- | --- |
| **Standard / schema** | New *required* field; a rule made stricter (tighter enum or pattern); an enum value **removed**; a field removed or renamed | A new *optional* field; an enum value **added**; a new template, example, or extension namespace | Wording or typo fix in non-normative prose |
| **Validator CLI** | Any change that makes a previously-passing document fail; a flag or command removed or renamed; a default changed so pass/fail differs; a config key removed or renamed; the minimum Python raised | A new opt-in flag or command; a new config option with a backward-compatible default; new output that does not change any pass/fail result | A crash or message-text fix with **no** outcome change; an internal refactor; a dependency bump with no behavior change |
| **Reusable workflow** | A `workflow_call` input removed or renamed; a default changed so a caller's outcome differs; any behavior that can fail a previously-passing caller | A new optional input with a default; a new opt-in capability | CI plumbing with no caller-visible effect (e.g. bumping a pinned action version) |

## The previously-passing rule

> If any change can turn a **previously-passing** consumer document or workflow
> run into a **failure**, the release is **MAJOR** — without exception.

This holds even when the change is a genuine bug fix. If the validator was
wrongly lenient and a fix causes real-world documents that passed yesterday to
fail today, the fix waits for the next major version. The contract is the
consumer's outcome, not the maintainer's intent. Ship the corrected, stricter
behavior as the next `vN.0.0`, document the migration in the changelog, and let
consumers adopt it deliberately.

The inverse is the freedom this buys: anything that *cannot* newly-fail a
passing consumer (additive standard fields, opt-in validator features,
internal fixes, CI plumbing) is a minor or patch and flows to `@vN` trackers
automatically.

## Release requirements

Every release MUST:

1. **Tag a full version.** Create an annotated, GPG-signed tag
   `vMAJOR.MINOR.PATCH` on the release commit. Full-version tags are
   **immutable** — never deleted, moved, or repointed once pushed.
2. **Advance the moving major tag.** Maintain a `vMAJOR` tag that always points
   at the newest release within that major. Repoint it locally, then move it on
   the remote by **deleting and re-pushing** — not `git push --force`. The force
   flag is unnecessary for a tag move, can clobber branch history, and is
   blocked by this repository's force-push guard (`release-pipeline`):

   ```bash
   git tag -fs vN -m "project-standards vN (-> vN.M.P)" <release-commit>
   git push origin :refs/tags/vN   # delete the old remote tag
   git push origin vN              # re-push it at the release commit
   ```

   Only the moving major tag is ever repointed. Never delete or move a
   full-version tag once it is pushed.
3. **Bump the package version** in `pyproject.toml` and regenerate `uv.lock` in
   the release commit, so `uv tool install` resolves a version that matches the
   tag.
4. **Update the changelog** in the same commit: move entries from
   `## [Unreleased]` into a new `## [vMAJOR.MINOR.PATCH] — YYYY-MM-DD` section,
   following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). A MAJOR
   release MUST include migration notes describing what a consumer must change.

## Consuming repositories

Pin the reusable workflow and the CLI by **major tag** to receive
non-breaking fixes automatically:

```yaml
uses: L3DigitalNet/project-standards/.github/workflows/validate-markdown-frontmatter.yml@v1
```

- **`@vMAJOR`** (recommended) — tracks the latest release in that major. The
  previously-passing rule guarantees these updates never newly-fail a passing
  repo.
- **`@vMAJOR.MINOR.PATCH`** or a **commit SHA** — an immutable freeze, for repos
  that want byte-for-byte reproducibility and to adopt every change explicitly.
- **`@main`** — only for this repository's own development or deliberate test
  repos. Never pin a production consumer to `main`.

A **major upgrade is intentional work**: read the changelog migration notes,
bump the pin from `@vN` to `@v(N+1)`, and re-run validation before merging.

## Pre-1.0 releases

While the major version is `0` (`0.y.z`), the standard SemVer caveat applies:
the public contract is not yet stable, so a `0.y` bump may carry breaking
changes and `0.0.z` carries additive ones. This repository is past `1.0.0`; the
note is retained for forks that start fresh.
