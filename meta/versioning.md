---
schema_version: '1.1'
id: 'reference-cirycm-versioning-standard'
title: 'Versioning Standard'
description: 'How releases of this repository are numbered, tagged, and consumed — a consumer-outcome contract over the standard, schema, validator, and workflow.'
doc_type: 'reference'
status: 'active'
created: '2026-06-02'
updated: '2026-07-18'
reviewed: '2026-07-18'
owner: 'Chris Purcell / L3DigitalNet'
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
  - 'docs/adr/adr-0024-catalog-scoped-package-version-channels.md'
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
  - [Catalog and package channels](#catalog-and-package-channels)
  - [Package release and contract versions](#package-release-and-contract-versions)
    - [FM→ADR compatibility](#fmadr-compatibility)
  - [Component-level version markers](#component-level-version-markers)
  - [Change classification](#change-classification)
  - [The previously-passing rule](#the-previously-passing-rule)
  - [Release requirements](#release-requirements)
  - [Consuming repositories](#consuming-repositories)
  - [Pre-1.0 releases](#pre-10-releases)

> **Active post-v5 release policy (since 2026-07-18).** Project Standards 5.0.1 is the current release. Normal Semantic Versioning classification and the release requirements below apply; there is no active release freeze. Record changes under `## [Unreleased]` until the owner authorizes a release. The moving `v5` tag tracks the newest 5.x release. A correction that preserves every previously passing consumer outcome may ship as PATCH or MINOR according to the tables below; a change that newly fails a consumer or changes an ordinary default incompatibly requires a new MAJOR and catalog-major transition.

**Historical policy:** From 2026-07-07 until the v5.0.0 publication, the repository intentionally accumulated all release-affecting work under one v5 freeze. That freeze ended when release commit `8869a08` and the signed `v5.0.0` and `v5` refs were published.

## Purpose

This repository ships **several components under one version number**: seven standards — [Markdown Frontmatter](../standards/markdown-frontmatter/README.md), [ADR](../standards/adr/README.md), [Python Tooling SSOT](../standards/python-tooling/README.md), [Markdown Tooling](../standards/markdown-tooling/README.md), [Project Specification](../standards/project-spec/README.md), [CLI Documentation](../standards/cli-documentation/README.md), and [Agent Handoff](../standards/agent-handoff/README.md) — plus the **JSON schema** (`src/project_standards/schemas/`), the **validator CLI** (`src/project_standards/`, distributed as the `project-standards` package), and the **reusable workflows** (`.github/workflows/validate-markdown-frontmatter.yml`, `validate-specs.yml`). Consuming repositories pin a single git tag and receive all of them together.

All standards ship in one `project-standards` distribution. Under the V5 control-plane contract, a consumer first initializes a neutral `.standards/` catalog, config, and lock scaffold, then selects individual packages through `.standards/config.toml`; initialization enables none. Package-specific V1 adoption mechanics are migration inputs rather than current authority. Catalog 5 has seven consumer packages, [Python Coding](../standards/python-coding/README.md) as reference-only package `0.5`, and [Standard Bundle Authoring](../standards/standard-bundle-authoring/README.md) as internal package `2.0`.

This document defines what a release number promises, how to classify a change, and the operational requirements for cutting a release. It governs this repository's own releases; it is not the metadata standard for documents (see [`standards/markdown-frontmatter/README.md`](../standards/markdown-frontmatter/README.md)).

## What a version promises

Releases follow [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html) (`MAJOR.MINOR.PATCH`), but the compatibility being versioned is **the consuming repository's validation outcome**, not a code API.

> **Governing principle.** A release tag is a contract about what happens to a consuming repository on its next pull. A release's level is the **worst-case impact of any single change** across all shipped components.

This reframing is what makes the current moving major tag (`@v5`) safe to track unattended: within a major, a consumer that passed validation yesterday will still pass today.

## Version grammar

- **Tool release plane:** full SemVer `MAJOR.MINOR.PATCH` for the git tag and `pyproject.toml` version. "SemVer" in this document refers to this plane.
- **Catalog plane:** an integer major selected in `.standards/config.toml`; it matches the tool release major and defines the ordinary package defaults available to that consumer line.
- **Package release plane:** immutable `major.minor` payload identities advertised by the selected catalog.
- **Internal contract plane:** an optional package-owned selector such as `contract_version`, used only when one resolved package payload supports multiple schema or behavior contracts.

## Catalog and package channels

Within one catalog major, each package declares one non-breaking default for ordinary `version = "latest"` resolution. `latest` means the newest compatible version on the consumer's current default or explicitly accepted package-major track; it never means the numerically highest advertised version.

A catalog may also advertise retained versions and opt-in breaking candidates. Entering a non-default package major requires explicit `--allow-major STANDARD_ID@TARGET_MAJOR` authorization and a declared migration path. Successful entry records a durable accepted-major track in `.standards/lock.toml`, separate from enabled-package state, so disable/re-enable and compatible same-major updates preserve the consumer's intent. Exact package selectors remain exact.

A MINOR tool release may advertise an opt-in breaking candidate when the ordinary default and every previously valid selection remain available. Promoting that candidate to the ordinary `latest` default, removing an advertised version, or incompatibly changing a same-catalog-major default requires a MAJOR tool release and catalog-major transition. The consumer therefore opts into changed defaults once by changing catalog major; package-level `latest` then remains non-breaking within that selected catalog line.

## Package release and contract versions

Every advertised package release is a complete, immutable, offline-installable payload. A supported-version list or registry entry alone is not proof of availability: the installed distribution must carry the versioned manifest, schemas, migrations, resources, artifacts, providers, and integrity data required to reconcile it.

A package release may expose one or more internal contract versions. Those selectors describe schema or behavior choices _inside_ the resolved payload and are not package release identities. Legacy `registry.json` entries, V1 package manifests, and `.project-standards.yml` selectors remain V5 migration inputs only; `.standards/config.toml`, the catalog, and the central lock are the V5 authorities. The v5 read-only fallback is removed in v6 after migration evidence is complete.

### FM→ADR compatibility

The resolved ADR payload declares the Frontmatter contract versions it supports. Selection remains independent **subject to declared compatibility**, not arbitrary combination; the resolver and validator fail closed on an incompatible pair. This subject-level compatibility is separate from package release identity and catalog-channel selection.

## Component-level version markers

The following current markers are contract-plane inputs retained during V5 migration. They do not identify package payload releases and are deliberately decoupled from the tool release version:

- **`schema_version`** (Markdown Frontmatter) versions the metadata schema's **field set and controlled vocabularies** only. It has no patch component and is enum-gated by the JSON schema. It changes solely when those fields or vocabularies change, so a release can ship without touching it — the `1.1` schema is unchanged by the `2.0.0` release. See [`standards/markdown-frontmatter/README.md`](../standards/markdown-frontmatter/README.md).
- The **Python Tooling contract version** is the closed `contract_version` option inside the selected Python Tooling payload. It preserves supported toolchain-policy semantics independently from package release `1.1`.
- The **Markdown Tooling contract version** is the closed `contract_version` option inside the selected Markdown Tooling payload. The package options and managed lint/format workflows enforce its behavior independently from package release `1.2`.
- The **Agent Handoff contract version** is the closed `contract_version` option inside the selected Agent Handoff payload. The provider-backed validators and central lock enforce its layout/integration policy independently from package release `1.1`.

The **ADR standard** carries its own ADR contract version for body rules and Frontmatter compatibility; for document _metadata_ it remains a profile over the Frontmatter schema. Package payload releases and package-owned contract selectors remain distinct as described in [Package release and contract versions](#package-release-and-contract-versions). There are no per-standard git release tags: all immutable package payloads ship inside the one repository distribution.

## Change classification

Classify each release by the highest-severity change it contains.

| Component | MAJOR — migrate intentionally | MINOR — safe to inherit on `@vN` | PATCH — no consumer-visible change |
| --- | --- | --- | --- |
| **Frontmatter / ADR standard + schema** | New _required_ field; a rule made stricter (tighter enum or pattern); an enum value **removed**; a field removed or renamed | A new _optional_ field; an enum value **added**; a new template, example, or extension namespace | Wording or typo fix in non-normative prose |
| **Validator CLI** | Any change that makes a previously-passing document fail; a flag or command removed or renamed; a default changed so pass/fail differs; a config key removed or renamed; the minimum Python raised | A new opt-in flag or command; a new config option with a backward-compatible default; new output that does not change any pass/fail result | A crash or message-text fix with **no** outcome change; an internal refactor; a dependency bump with no behavior change |
| **Reusable workflow** | A `workflow_call` input removed or renamed; a default change — or any other behavior — that can fail a previously-passing caller | A new optional input with a default; a default change that cannot fail a previously-passing caller; a new opt-in capability | CI plumbing with no caller-visible effect (e.g. bumping a pinned action version) |
| **Consumer package payload** | Removing/renaming a supported option, managed unit, provider operation, or contract; an incompatible default that makes a previously-valid selection fail | A backward-compatible option/provider/resource addition; a compatible same-major payload default | Editorial payload prose with no option, output, provider, migration, or conformance change |
| **Catalog / package payload set** | An advertised version removed; a same-catalog-major ordinary default changed incompatibly; a breaking candidate promoted to ordinary default | A compatible payload added; an opt-in breaking candidate advertised while the ordinary default and prior selections remain available | — |

An opt-in breaking candidate is MINOR only while existing defaults and selections remain valid. Promotion to the ordinary default is MAJOR.

Consumer package changes are inherited only through catalog resolution and explicit reconciliation. Exact selectors remain pinned; `latest` advances only within its compatible default or accepted-major track. The previously-passing rule applies to the resolved package behavior and the tool/workflow surface together.

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
uses: L3DigitalNet/project-standards/.github/workflows/validate-markdown-frontmatter.yml@v5
```

- **`@vMAJOR`** (recommended) — tracks the latest release in that major. The previously-passing rule protects ordinary defaults and prior valid selections; breaking package candidates require explicit package-major authorization.
- **`@vMAJOR.MINOR.PATCH`** or a **commit SHA** — an immutable freeze, for repos that want byte-for-byte reproducibility and to adopt every change explicitly.
- **`@main`** — only for this repository's own development or deliberate test repos. Never pin a production consumer to `main`.

A **major upgrade is intentional work**: read the changelog migration notes, bump the pin from `@vN` to `@v(N+1)`, and re-run validation before merging.

## Pre-1.0 releases

While the major version is `0` (`0.y.z`), the standard SemVer caveat applies: the public contract is not yet stable, so a `0.y` bump may carry breaking changes and `0.0.z` carries additive ones. This repository is past `1.0.0`; the note is retained for forks that start fresh.
