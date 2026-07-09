---
schema_version: '1.1'
id: 'reference-cirycm-versioning-standard'
title: 'Versioning Standard'
description: 'How releases of this repository are numbered, tagged, and consumed — a consumer-outcome contract over the standard, schema, validator, and workflow.'
doc_type: 'reference'
status: 'active'
created: '2026-06-02'
updated: '2026-07-09'
reviewed: null
owner: ''
consumer: 'mix'
tags:
  - 'versioning'
  - 'releases'
  - 'semver'
aliases: []
related:
  - 'standards/markdown-frontmatter/README.md'
  - 'standards/adr/README.md'
  - 'standards/python-tooling/README.md'
  - 'standards/markdown-tooling/README.md'
  - 'standards/cli-documentation/README.md'
  - 'docs/adr/adr-0020-standard-package-versioning-methodology.md'
source:
  - 'https://semver.org/spec/v2.0.0.html'
  - 'https://keepachangelog.com/en/1.1.0/'
confidence: 'high'
visibility: 'internal'
license: null
---

# Versioning Standard

## Table of Contents

- [Versioning Standard](#versioning-standard)
  - [Table of Contents](#table-of-contents)
  - [Purpose](#purpose)
  - [What a version promises](#what-a-version-promises)
  - [Version grammar](#version-grammar)
  - [Per-standard contract versions](#per-standard-contract-versions)
    - [FM→ADR compatibility](#fmadr-compatibility)
  - [Component-level version markers](#component-level-version-markers)
  - [Change classification](#change-classification)
  - [The previously-passing rule](#the-previously-passing-rule)
  - [Release requirements](#release-requirements)
  - [Consuming repositories](#consuming-repositories)
  - [Pre-1.0 releases](#pre-10-releases)

> **Active release policy — release freeze until v5.0.0 (set 2026-07-07).** The next release will be **v5.0.0**, carrying the Meta-Repository MCP-readiness work (`SPEC-MT01`) and every standards change that accrues before it. Until v5.0.0 ships, **no interim PATCH or MINOR release is cut** — all version-affecting changes (including per-standard contract-version bumps) accumulate under `## [Unreleased]` in the [CHANGELOG](../CHANGELOG.md) and are promoted together at the v5.0.0 cut. This deliberately removes per-change release friction while the standards platform is reshaped for the Meta-repo work. Keep classifying every change as you make it (the [previously-passing rule](#the-previously-passing-rule) still governs, so the aggregate rationale is ready at release), and keep contract-version bumps recorded in `[Unreleased]` — just do not tag a release between now and v5.0.0.

## Purpose

This repository ships **several components under one version number**: six standards — the [Markdown Frontmatter](../standards/markdown-frontmatter/README.md), [ADR](../standards/adr/README.md), [Python Tooling SSOT](../standards/python-tooling/README.md), [Markdown Tooling](../standards/markdown-tooling/README.md), [Project Specification](../standards/project-spec/README.md), and [CLI Documentation](../standards/cli-documentation/README.md) standards — plus the **JSON schema** (`src/project_standards/schemas/`), the **validator CLI** (`src/project_standards/`, distributed as the `project-standards` package), and the **reusable workflows** (`.github/workflows/validate-markdown-frontmatter.yml`, `validate-specs.yml`). Consuming repositories pin a single git tag and receive all of them together.

The two Markdown frontmatter standards (Frontmatter and ADR) are **enforced automatically**: a consumer pins the workflow and the validator checks its documents on every run. Project Specification is enforced the same way, via its own reusable workflow and `spec:` config block; its templates and tooling form contract `1.0`, selected with `spec.version`. The Python Tooling, Markdown Tooling, and CLI Documentation standards are **copy-adopted** — a consumer copies their scaffolds (and, for Markdown Tooling, optionally opts into the `lint-markdown.yml` workflow; CLI Documentation ships its own `cli-docs-check.yml`), so they are never inherited automatically and a change to them cannot newly-fail a consumer on its own. All six still ship under the same release tag. A seventh document, the [Python Coding standard](../standards/python-coding/README.md), ships in the repository as an **in-development, reference-only draft** with package version `0.4` — unregistered, excluded from validation and the adopt CLI, and not a consumer-selectable contract until registered. The [Standard Bundle Authoring standard](../standards/standard-bundle-authoring/README.md) likewise sits outside the release contract: an **internal/reference** meta-standard (`adoption = "none"`) at package version `1.0` that defines the `standard.toml` bundle contract this repository authors its own standards to. It is unregistered and not consumer-adopted, so it does not change the six-standard release count.

This document defines what a release number promises, how to classify a change, and the operational requirements for cutting a release. It governs this repository's own releases; it is not the metadata standard for documents (see [`standards/markdown-frontmatter/README.md`](../standards/markdown-frontmatter/README.md)).

## What a version promises

Releases follow [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html) (`MAJOR.MINOR.PATCH`), but the compatibility being versioned is **the consuming repository's validation outcome**, not a code API.

> **Governing principle.** A release tag is a contract about what happens to a consuming repository on its next pull. A release's level is the **worst-case impact of any single change** across all shipped components.

This reframing is what makes the moving major tag (`@v4`) safe to track unattended: within a major, a consumer that passed validation yesterday will still pass today.

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
| Markdown Tooling | `1.1` | `markdown_tooling.version` (optional) | no — copy-adopted label, metadata only |
| Project Specification | `1.0` | `spec.version` (optional; unset = default) | yes — `spec:` config + `validate-specs.yml` |
| CLI Documentation | `1.0` | `cli_documentation.version` (optional) | no — copy-adopted label, metadata only |

**Adding a bundled contract version is a MINOR tool release; removing one is MAJOR** (a consumer pinned to it would newly fail). Within a single standard's line, the previously-passing rule applies: an additive field/value is MINOR, a stricter rule or removed enum value is MAJOR.

### FM→ADR compatibility

ADR is a profile over the Frontmatter schema, so each ADR contract version declares the Frontmatter versions it supports (today: ADR `1.0` → Frontmatter `1.1`, which itself accepts `schema_version: '1.0'` documents). The validator rejects an incompatible configured pair (exit 2). "Independent" therefore means independently selected **subject to declared compatibility**, not any combination. A no-version config uses each standard's default and is always compatible. A configured `frontmatter.version` that is not bundled reports "unknown frontmatter version" (caught at schema resolution), not a compatibility error.

## Component-level version markers

The single release version is the only number a consumer pins. Three **component-level markers** version individual pieces of the repository and are deliberately **decoupled** from the release version — none is itself a release number:

- **`schema_version`** (Markdown Frontmatter) versions the metadata schema's **field set and controlled vocabularies** only. It has no patch component and is enum-gated by the JSON schema. It changes solely when those fields or vocabularies change, so a release can ship without touching it — the `1.1` schema is unchanged by the `2.0.0` release. See [`standards/markdown-frontmatter/README.md`](../standards/markdown-frontmatter/README.md).
- The **Python Tooling contract version** — the `1.0` label in the [Python Tooling standard](../standards/python-tooling/README.md)'s status banner — is a copy-adopted label: not machine-enforced and not a release version.
- The **Markdown Tooling contract version** — the `1.1` label in the [Markdown Tooling standard](../standards/markdown-tooling/README.md) — is a copy-adopted label like the Python Tooling one: validated as a known version when selected, but it does not enforce the standard's body rules (the `lint-markdown.yml` workflow does) and is not a release version.

The **ADR standard** now carries its own ADR contract version (`1.0`) for its body rules and Frontmatter-compatibility; for document _metadata_ it remains a profile over the frontmatter schema, so its docs still declare `schema_version` and its opt-in MADR section check lives in the validator. Each standard's `major.minor` **contract version** (see [Per-standard contract versions](#per-standard-contract-versions)) is distinct from the single **tool release version** on the git tag. There are still no per-standard _release tags_ — every standard ships together under the one repository tag, and a contract version is selected in config, not pinned separately.

## Change classification

Classify each release by the highest-severity change it contains.

| Component | MAJOR — migrate intentionally | MINOR — safe to inherit on `@vN` | PATCH — no consumer-visible change |
| --- | --- | --- | --- |
| **Frontmatter / ADR standard + schema** | New _required_ field; a rule made stricter (tighter enum or pattern); an enum value **removed**; a field removed or renamed | A new _optional_ field; an enum value **added**; a new template, example, or extension namespace | Wording or typo fix in non-normative prose |
| **Validator CLI** | Any change that makes a previously-passing document fail; a flag or command removed or renamed; a default changed so pass/fail differs; a config key removed or renamed; the minimum Python raised | A new opt-in flag or command; a new config option with a backward-compatible default; new output that does not change any pass/fail result | A crash or message-text fix with **no** outcome change; an internal refactor; a dependency bump with no behavior change |
| **Reusable workflow** | A `workflow_call` input removed or renamed; a default change — or any other behavior — that can fail a previously-passing caller | A new optional input with a default; a default change that cannot fail a previously-passing caller; a new opt-in capability | CI plumbing with no caller-visible effect (e.g. bumping a pinned action version) |
| **Python / Markdown Tooling standards** (copy-adopted) | Raising the required Python or a tool floor; removing or renaming a scaffold or the gate command; a default change that makes the verification gate newly fail | A new optional scaffold or recommended tool with a backward-compatible default; a new opt-in step | An editorial revision of the standard doc; a refreshed tool pin with no behavior change |
| **Bundled contract set** | A bundled contract version **removed** (a consumer pinned to it newly fails) | A bundled contract version **added** (selectable; nothing previously-passing changes) | — |

Because the Python and Markdown Tooling standards are **copy-adopted**, a consumer sees their changes only when it deliberately re-syncs the scaffolds — they are never inherited automatically on `@vN`. That row classifies the impact on a consumer that re-syncs; the previously-passing rule below applies to the validator-enforced surface.

## The previously-passing rule

> If any change can turn a **previously-passing** consumer document or workflow run into a **failure**, the release is **MAJOR** — without exception.

This holds even when the change is a genuine bug fix. If the validator was wrongly lenient and a fix causes real-world documents that passed yesterday to fail today, the fix waits for the next major version. The contract is the consumer's outcome, not the maintainer's intent. Ship the corrected, stricter behavior as the next `vN.0.0`, document the migration in the changelog, and let consumers adopt it deliberately.

The inverse is the freedom this buys: anything that _cannot_ newly-fail a passing consumer (additive standard fields, opt-in validator features, internal fixes, CI plumbing) is a minor or patch and flows to `@vN` trackers automatically.

## Release requirements

Every release MUST:

0. **Land the release on `main` first.** The release commit and **both** tags — the full-version `vMAJOR.MINOR.PATCH` and the moving-major `vMAJOR` — MUST live on `main`. Merge the release commit to `main` **before** tagging, then tag the commit as it exists on `main`. This is not optional polish: [`docs/handoff/deployed.md`](../docs/handoff/deployed.md) defines "Deployed" as _published git refs on `main`_, and every prior release (`v1.x`–`v3.x`) was cut there. A tag on a topic branch (`testing`) is not a release. Do the version-pin bumps (steps 3–6 below) in the release commit on `main`, not on the development branch.
1. **Tag a full version.** Create an annotated, GPG-signed tag `vMAJOR.MINOR.PATCH` on the release commit. Full-version tags are **immutable** — never deleted, moved, or repointed once pushed.
2. **Advance the moving major tag.** Maintain a `vMAJOR` tag that always points at the newest release within that major. Repoint it locally, then move it on the remote by **deleting and re-pushing** — not `git push --force`. The force flag is unnecessary for a tag move, can clobber branch history, and is blocked by this repository's force-push guard (`release-pipeline`):

   ```bash
   git tag -fs vN -m "project-standards vN (-> vN.M.P)" <release-commit>
   git push origin :refs/tags/vN   # delete the old remote tag
   git push origin vN              # re-push it at the release commit
   ```

   Only the moving major tag is ever repointed. Never delete or move a full-version tag once it is pushed.

3. **Bump the in-repo version references (MAJOR only).** A new major moves the moving-major tag, but the workflow defaults and usage examples still name the old one. In the release commit for a MAJOR, bump both, so a `@vN` caller that omits the `standards-ref` input runs the vN workflow against the vN validator (not the previous major's):
   - **Reusable-workflow defaults.** Bump every hardcoded `default: "vN-1"` for the `standards-ref` input to the new major in [`.github/workflows/validate-markdown-frontmatter.yml`](../.github/workflows/validate-markdown-frontmatter.yml) and [`.github/workflows/validate-specs.yml`](../.github/workflows/validate-specs.yml). This is the silent-drift trap: a caller pinned `@vN` on `uses:` but relying on the default `standards-ref` would otherwise install the previous major's CLI.
   - **In-repo usage examples.** Bump the `@vN` / `standards-ref: vN` refs in the doc examples — `README.md` and each `standards/*/adopt.md` — to the new major so copy-paste snippets pin the current line.

   With these carve-outs stated explicitly:
   - **(a) `UPGRADING.md` is not a find/replace.** It gets a _new_ `v(N-1)→vN` section (step 6), not a blanket rewrite of the historical runbook. Leave existing historical version references in it intact.
   - **(b) Fixed `blob/vN/…` permalinks are deliberate.** Any `.../blob/vN/...` permalink that pins a specific tagged snapshot is reviewed individually, not blanket-rewritten — some are meant to keep pointing at the old tag.
   - **(c) A standard's examples must never pin a tag that predates the standard.** When a new standard first ships in a MAJOR, its `adopt.md` examples MUST pin the new major in the same release commit, and its intro banner MUST state the first release that carries it. Precedent: `project-spec` first ships at `v4.0.0` — at the v4 cut its examples went `@v3`→`@v4` and [`standards/project-spec/adopt.md`](../standards/project-spec/adopt.md) gained the availability banner.

   Optional pre-release assertion: grep the reusable workflows for the `standards-ref` default and fail if any lags the `pyproject.toml` major — e.g. no `default: "vN-1"` may remain once `pyproject.toml` reads `N.0.0`.

4. **Bump the package version** in `pyproject.toml` and regenerate `uv.lock` in the release commit, so `uv tool install` resolves a version that matches the tag.
5. **Update the changelog** in the same commit: move entries from `## [Unreleased]` into a new `## [vMAJOR.MINOR.PATCH] — YYYY-MM-DD` section, following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). A MAJOR release MUST include migration notes describing what a consumer must change.
6. **Rewrite `UPGRADING.md` for the new major (MAJOR only).** [`UPGRADING.md`](../UPGRADING.md) is the step-by-step major-upgrade runbook README.md points consumers to, and both prior majors shipped it rewritten in the release commit. Its frontmatter `title` (and `id`, if it encodes the version) still reads "Upgrading from v(N-1) to vN" — rewrite the document as **"Upgrading from v(N-1) to vN"** for the new pair, with the new major's breaking-change steps, and update the frontmatter `title` (and `id` if applicable) to match. Confirm `README.md`'s pin example (e.g. `@v2` → `@v3`) names the current major pair.

## Consuming repositories

Pin the reusable workflow and the CLI by **major tag** to receive non-breaking fixes automatically:

```yaml
uses: L3DigitalNet/project-standards/.github/workflows/validate-markdown-frontmatter.yml@v4
```

- **`@vMAJOR`** (recommended) — tracks the latest release in that major. The previously-passing rule guarantees these updates never newly-fail a passing repo.
- **`@vMAJOR.MINOR.PATCH`** or a **commit SHA** — an immutable freeze, for repos that want byte-for-byte reproducibility and to adopt every change explicitly.
- **`@main`** — only for this repository's own development or deliberate test repos. Never pin a production consumer to `main`.

A **major upgrade is intentional work**: read the changelog migration notes, bump the pin from `@vN` to `@v(N+1)`, and re-run validation before merging.

## Pre-1.0 releases

While the major version is `0` (`0.y.z`), the standard SemVer caveat applies: the public contract is not yet stable, so a `0.y` bump may carry breaking changes and `0.0.z` carries additive ones. This repository is past `1.0.0`; the note is retained for forks that start fresh.
