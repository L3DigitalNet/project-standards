---
schema_version: '1.1'
id: 'versioning-standard'
title: 'Versioning Standard'
description: 'How releases of this repository are numbered, tagged, and consumed — a consumer-outcome contract over the standard, schema, validator, and workflow.'
doc_type: 'reference'
status: 'active'
created: '2026-06-02'
updated: '2026-06-06'
reviewed: null
owner: ''
tags:
  - 'versioning'
  - 'releases'
  - 'semver'
aliases: []
related:
  - 'standards/markdown-frontmatter/README.md'
  - 'standards/adr/README.md'
  - 'standards/python-tooling/README.md'
source:
  - 'https://semver.org/spec/v2.0.0.html'
  - 'https://keepachangelog.com/en/1.1.0/'
confidence: 'high'
visibility: 'internal'
license: null
---

# Versioning Standard

## Purpose

This repository ships **several components under one version number**: three standards — the [Markdown Frontmatter](../standards/markdown-frontmatter/README.md), [ADR](../standards/adr/README.md), and [Python Tooling SSOT](../standards/python-tooling/README.md) standards — plus the **JSON schema** (`src/project_standards/schemas/`), the **validator CLI** (`src/project_standards/`, distributed as the `project-standards` package), and the **reusable workflow** (`.github/workflows/validate-markdown-frontmatter.yml`). Consuming repositories pin a single git tag and receive all of them together.

The two Markdown standards (Frontmatter and ADR) are **enforced automatically**: a consumer pins the workflow and the validator checks its documents on every run. The Python Tooling standard is **copy-adopted** — a consumer copies its scaffolds, so it is never inherited automatically and a change to it cannot newly-fail a consumer on its own. All three still ship under the same release tag.

This document defines what a release number promises, how to classify a change, and the operational requirements for cutting a release. It governs this repository's own releases; it is not the metadata standard for documents (see [`markdown-frontmatter.md`](../standards/markdown-frontmatter/README.md)).

## What a version promises

Releases follow [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html) (`MAJOR.MINOR.PATCH`), but the compatibility being versioned is **the consuming repository's validation outcome**, not a code API.

> **Governing principle.** A release tag is a contract about what happens to a consuming repository on its next pull. A release's level is the **worst-case impact of any single change** across all shipped components.

This reframing is what makes the moving major tag (`@v1`) safe to track unattended: within a major, a consumer that passed validation yesterday will still pass today.

## Version grammar

- **Contract plane (per standard):** `major.minor` — no patch component, matching `schema_version`. Registry keys and config values use this two-part form (`'1.0'`, `'1.1'`, `'2.0'`).
- **Tool release plane:** full SemVer `MAJOR.MINOR.PATCH` (the git tag / `pyproject.toml` version). "SemVer" in this document refers only to the tool plane.

## Per-standard contract versions

Each standard carries its own `major.minor` contract version, selected per standard in a consumer's `.project-standards.yml`. The tool release bundles a known set of these versions (in `registry.json`); selecting one is a config edit, not a new pin.

| Standard | Version marker | Selected by | Enforced? |
| --- | --- | --- | --- |
| Markdown Frontmatter | `schema_version` (`1.1`) | `markdown.frontmatter.version` (optional; unset = default) | yes — JSON schema |
| ADR | ADR contract `1.0` | `markdown.adr.version` (optional; unset = frozen default) | yes — body-rule + FM-compatibility check |
| Python Tooling | `1.0` | `python_tooling.version` (optional) | no — copy-adopted label, metadata only |

**Adding a bundled contract version is a MINOR tool release; removing one is MAJOR** (a consumer pinned to it would newly fail). Within a single standard's line, the previously-passing rule applies: an additive field/value is MINOR, a stricter rule or removed enum value is MAJOR.

### FM→ADR compatibility

ADR is a profile over the Frontmatter schema, so each ADR contract version declares the Frontmatter versions it supports (today: ADR `1.0` → Frontmatter `1.1`, which itself accepts `schema_version: '1.0'` documents). The validator rejects an incompatible configured pair (exit 2). "Independent" therefore means independently selected **subject to declared compatibility**, not any combination. A no-version config uses each standard's default and is always compatible. A configured `frontmatter.version` that is not bundled reports "unknown frontmatter version" (caught at schema resolution), not a compatibility error.

## Component-level version markers

The single release version is the only number a consumer pins. Two **component-level markers** version individual pieces of the repository and are deliberately **decoupled** from the release version — neither is itself a release number:

- **`schema_version`** (Markdown Frontmatter) versions the metadata schema's **field set and controlled vocabularies** only. It has no patch component and is enum-gated by the JSON schema. It changes solely when those fields or vocabularies change, so a release can ship without touching it — the `1.1` schema is unchanged by the `2.0.0` release. See [`markdown-frontmatter.md`](../standards/markdown-frontmatter/README.md).
- The **Python Tooling internal revision** — the `internal revision N.M` counter in the [Python Tooling standard](../standards/python-tooling/README.md)'s status banner — tracks **editorial revisions of that one document**. It is not machine-enforced and is not a release version.

The **ADR standard** carries no version of its own: it is a profile over the frontmatter schema, so it rides `schema_version`, and its only machine-checked rule — the opt-in MADR section check — lives in the validator and is covered by the release version. Each standard now carries its own `major.minor` **contract version** (see [Per-standard contract versions](#per-standard-contract-versions)); these remain distinct from the single **tool release version** on the git tag. There are still no per-standard _release tags_ — every standard ships together under the one repository tag, and a contract version is selected in config, not pinned separately.

## Change classification

Classify each release by the highest-severity change it contains.

| Component | MAJOR — migrate intentionally | MINOR — safe to inherit on `@vN` | PATCH — no consumer-visible change |
| --- | --- | --- | --- |
| **Frontmatter / ADR standard + schema** | New _required_ field; a rule made stricter (tighter enum or pattern); an enum value **removed**; a field removed or renamed | A new _optional_ field; an enum value **added**; a new template, example, or extension namespace | Wording or typo fix in non-normative prose |
| **Validator CLI** | Any change that makes a previously-passing document fail; a flag or command removed or renamed; a default changed so pass/fail differs; a config key removed or renamed; the minimum Python raised | A new opt-in flag or command; a new config option with a backward-compatible default; new output that does not change any pass/fail result | A crash or message-text fix with **no** outcome change; an internal refactor; a dependency bump with no behavior change |
| **Reusable workflow** | A `workflow_call` input removed or renamed; a default change — or any other behavior — that can fail a previously-passing caller | A new optional input with a default; a default change that cannot fail a previously-passing caller; a new opt-in capability | CI plumbing with no caller-visible effect (e.g. bumping a pinned action version) |
| **Python Tooling standard** (copy-adopted) | Raising the required Python or a tool floor; removing or renaming a scaffold or the gate command; a default change that makes the verification gate newly fail | A new optional scaffold or recommended tool with a backward-compatible default; a new opt-in step | An editorial revision (the internal revision counter); a refreshed tool pin with no behavior change |
| **Bundled contract set** | A bundled contract version **removed** (a consumer pinned to it newly fails) | A bundled contract version **added** (selectable; nothing previously-passing changes) | — |

Because the Python Tooling standard is **copy-adopted**, a consumer sees its changes only when it deliberately re-syncs the scaffolds — they are never inherited automatically on `@vN`. That row classifies the impact on a consumer that re-syncs; the previously-passing rule below applies to the validator-enforced surface.

## The previously-passing rule

> If any change can turn a **previously-passing** consumer document or workflow run into a **failure**, the release is **MAJOR** — without exception.

This holds even when the change is a genuine bug fix. If the validator was wrongly lenient and a fix causes real-world documents that passed yesterday to fail today, the fix waits for the next major version. The contract is the consumer's outcome, not the maintainer's intent. Ship the corrected, stricter behavior as the next `vN.0.0`, document the migration in the changelog, and let consumers adopt it deliberately.

The inverse is the freedom this buys: anything that _cannot_ newly-fail a passing consumer (additive standard fields, opt-in validator features, internal fixes, CI plumbing) is a minor or patch and flows to `@vN` trackers automatically.

## Release requirements

Every release MUST:

1. **Tag a full version.** Create an annotated, GPG-signed tag `vMAJOR.MINOR.PATCH` on the release commit. Full-version tags are **immutable** — never deleted, moved, or repointed once pushed.
2. **Advance the moving major tag.** Maintain a `vMAJOR` tag that always points at the newest release within that major. Repoint it locally, then move it on the remote by **deleting and re-pushing** — not `git push --force`. The force flag is unnecessary for a tag move, can clobber branch history, and is blocked by this repository's force-push guard (`release-pipeline`):

   ```bash
   git tag -fs vN -m "project-standards vN (-> vN.M.P)" <release-commit>
   git push origin :refs/tags/vN   # delete the old remote tag
   git push origin vN              # re-push it at the release commit
   ```

   Only the moving major tag is ever repointed. Never delete or move a full-version tag once it is pushed.

3. **Bump the package version** in `pyproject.toml` and regenerate `uv.lock` in the release commit, so `uv tool install` resolves a version that matches the tag.
4. **Update the changelog** in the same commit: move entries from `## [Unreleased]` into a new `## [vMAJOR.MINOR.PATCH] — YYYY-MM-DD` section, following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). A MAJOR release MUST include migration notes describing what a consumer must change.

## Consuming repositories

Pin the reusable workflow and the CLI by **major tag** to receive non-breaking fixes automatically:

```yaml
uses: L3DigitalNet/project-standards/.github/workflows/validate-markdown-frontmatter.yml@v1
```

- **`@vMAJOR`** (recommended) — tracks the latest release in that major. The previously-passing rule guarantees these updates never newly-fail a passing repo.
- **`@vMAJOR.MINOR.PATCH`** or a **commit SHA** — an immutable freeze, for repos that want byte-for-byte reproducibility and to adopt every change explicitly.
- **`@main`** — only for this repository's own development or deliberate test repos. Never pin a production consumer to `main`.

A **major upgrade is intentional work**: read the changelog migration notes, bump the pin from `@vN` to `@v(N+1)`, and re-run validation before merging.

## Pre-1.0 releases

While the major version is `0` (`0.y.z`), the standard SemVer caveat applies: the public contract is not yet stable, so a `0.y` bump may carry breaking changes and `0.0.z` carries additive ones. This repository is past `1.0.0`; the note is retained for forks that start fresh.
