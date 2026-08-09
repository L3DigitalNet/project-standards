---
schema_version: '1.1'
id: 'reference-cirycm-versioning-standard'
title: 'Versioning Standard'
description: 'How releases of this repository are numbered, tagged, and consumed under the catalog and package-composition contract.'
doc_type: 'reference'
status: 'active'
created: '2026-06-02'
updated: '2026-08-01'
reviewed: '2026-08-01'
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
  - [Release requirements](#release-requirements)
  - [Consuming repositories](#consuming-repositories)

> **Active post-v5 release policy (since 2026-07-18).** The active release is the version recorded in [`pyproject.toml`](../pyproject.toml)'s `version` field, published from the commit tagged with the matching full-version tag; the moving `v5` tag tracks it. The most recent dated section of [`CHANGELOG.md`](../CHANGELOG.md) names the same version and its release commit. This paragraph deliberately does not restate the number or commit so it cannot go stale across a release cut — `pyproject.toml` and `CHANGELOG.md` are already bumped by the release requirements below, so they stay authoritative without a separate update here. The package-composition classification and release requirements below apply; there is no active release freeze. Record changes under `## [Unreleased]` until the owner authorizes a release. Every consumer surface requires Python 3.14 or newer.

**Historical policy:** From 2026-07-07 until the v5.0.0 publication, the repository intentionally accumulated all release-affecting work under one v5 freeze. That freeze ended when release commit `8869a08` and the signed `v5.0.0` and `v5` refs were published.

## Purpose

This repository ships **several components under one version number**: seven standards — [Markdown Frontmatter](../standards/markdown-frontmatter/README.md), [ADR](../standards/adr/README.md), [Python Tooling SSOT](../standards/python-tooling/README.md), [Markdown Tooling](../standards/markdown-tooling/README.md), [Project Specification](../standards/project-spec/README.md), [CLI Documentation](../standards/cli-documentation/README.md), and [Agent Handoff](../standards/agent-handoff/README.md) — plus the **JSON schema** (`src/project_standards/schemas/`), the **validator CLI** (`src/project_standards/`, distributed as the `project-standards` package), and the **reusable workflows** (`.github/workflows/validate-markdown-frontmatter.yml`, `validate-specs.yml`). Consuming repositories pin a single git tag and receive all of them together.

All standards ship in one `project-standards` distribution. Under the V5 control-plane contract, a consumer first initializes a neutral `.standards/` catalog, config, and lock scaffold, then selects individual packages through `.standards/config.toml`; initialization enables none. Package-specific V1 adoption mechanics are migration inputs rather than current authority. Catalog 5 has seven consumer packages, [Python Coding](../standards/python-coding/README.md) as reference-only package `0.6` (0.5 remains advertised as released history), and [Standard Bundle Authoring](../standards/standard-bundle-authoring/README.md) as internal package `2.6` (2.0 through 2.5 remain advertised as released history).

This document defines what a release number promises, how to classify a change, and the operational requirements for cutting a release. It governs this repository's own releases; it is not the metadata standard for documents (see [`standards/markdown-frontmatter/README.md`](../standards/markdown-frontmatter/README.md)).

## What a version promises

Releases use the [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html) `MAJOR.MINOR.PATCH` grammar. Their level records the owner-designated catalog line and package composition, not inferred implementation impact.

> **Governing principle.** The owner designates a matching tool/catalog major. Otherwise, a newly introduced package or a new advertised maximum for any package is MINOR; a release without either is PATCH.

Every proposed release still receives explicit owner review for behavioral impact. The classifier does not infer a MAJOR from that impact: when the owner requires a MAJOR boundary, both tool and catalog majors advance together before publication.

## Version grammar

- **Tool release plane:** the SemVer `MAJOR.MINOR.PATCH` grammar for the git tag and `pyproject.toml` version; classification follows [Change classification](#change-classification), not behavioral-impact inference.
- **Catalog plane:** an integer major selected in `.standards/config.toml`; it matches the tool release major and defines the ordinary package defaults available to that consumer line.
- **Package release plane:** immutable `major.minor` payload identities advertised by the selected catalog.
- **Internal contract plane:** an optional package-owned selector such as `contract_version`, used only when one resolved package payload supports multiple schema or behavior contracts.

## Catalog and package channels

Within one catalog major, each package declares one non-breaking default for ordinary `version = "latest"` resolution. `latest` means the newest compatible version on the consumer's current default or explicitly accepted package-major track; it never means the numerically highest advertised version.

A catalog may also advertise retained versions and opt-in breaking candidates. Entering a non-default package major requires explicit `--allow-major STANDARD_ID@TARGET_MAJOR` authorization and a declared migration path. Successful entry records a durable accepted-major track in `.standards/lock.toml`, separate from enabled-package state, so disable/re-enable and compatible same-major updates preserve the consumer's intent. Exact package selectors remain exact.

A new advertised package maximum is MINOR, including an opt-in breaking candidate, reference-only package, or internal package. Advertising older retained history does not count as an advance. Promoting a breaking candidate to the ordinary `latest` default requires an owner-designated tool and catalog MAJOR; the same promotion within one catalog major is forbidden. Removing any advertised version or downgrading a package default is forbidden in every release. The consumer therefore opts into changed defaults once by changing catalog major; package-level `latest` then remains non-breaking within that selected catalog line.

## Package release and contract versions

Every advertised package release is permanent and remains a complete, immutable, offline-installable payload. A supported-version list or registry entry alone is not proof of availability: the installed distribution must carry the versioned manifest, schemas, migrations, resources, artifacts, providers, and integrity data required to reconcile it.

A package release may expose one or more internal contract versions. Those selectors describe schema or behavior choices _inside_ the resolved payload and are not package release identities. Legacy `registry.json` entries, V1 package manifests, and `.project-standards.yml` selectors remain V5 migration inputs only; `.standards/config.toml`, the catalog, and the central lock are the V5 authorities. The v5 read-only fallback is removed in v6 after migration evidence is complete.

### FM→ADR compatibility

The resolved ADR payload declares the Frontmatter contract versions it supports. Selection remains independent **subject to declared compatibility**, not arbitrary combination; the resolver and validator fail closed on an incompatible pair. This subject-level compatibility is separate from package release identity and catalog-channel selection.

## Component-level version markers

The following current markers are contract-plane inputs retained during V5 migration. They do not identify package payload releases and are deliberately decoupled from the tool release version:

- **`schema_version`** (Markdown Frontmatter) versions the metadata schema's **field set and controlled vocabularies** only. It has no patch component and is enum-gated by the JSON schema. It changes solely when those fields or vocabularies change, so a release can ship without touching it — the `1.1` schema is unchanged by the `2.0.0` release. See [`standards/markdown-frontmatter/README.md`](../standards/markdown-frontmatter/README.md).
- The **Python Tooling contract version** is the closed `contract_version` option inside the selected Python Tooling payload. It preserves supported toolchain-policy semantics independently from package release `1.12`.
- The **Markdown Tooling contract version** is the closed `contract_version` option inside the selected Markdown Tooling payload. The package options and managed lint/format workflows enforce its behavior independently from package release `1.14`.
- The **Agent Handoff contract version** is the closed `contract_version` option inside the selected Agent Handoff payload. The provider-backed validators and central lock enforce its layout/integration policy independently from package release `1.10`.

The **ADR standard** carries its own ADR contract version for body rules and Frontmatter compatibility; for document _metadata_ it remains a profile over the Frontmatter schema. Package payload releases and package-owned contract selectors remain distinct as described in [Package release and contract versions](#package-release-and-contract-versions). There are no per-standard git release tags: all immutable package payloads ship inside the one repository distribution.

## Change classification

After rejecting forbidden transitions, classify the release in this order:

1. A matching tool and catalog major increment is the owner's MAJOR designation.
2. Otherwise, a package-version advance requires exactly MINOR.
3. Otherwise, the release requires exactly PATCH.

Compute package-version advance independently for each package ID from advertised catalog entries. A newly introduced package advances the composition. For an existing package, only a newly advertised version greater than that package's prior advertised maximum advances it. Internal and reference-only packages count. Adding older retained history and adding an unadvertised repository payload do not count.

Forbidden transitions are not higher release levels. Every advertised catalog version is permanent; released payload deletion or mutation, catalog digest replacement, advertised-version removal, package default downgrade, mismatched tool/catalog majors, a non-advancing tool version, and breaking-default promotion within the same catalog major cannot be released. A matching-major breaking-default promotion remains an owner-designated MAJOR when none of those invariants is violated.

Consumer package changes are inherited only through catalog resolution and explicit reconciliation. Exact selectors remain pinned; `latest` advances only within its compatible default or accepted-major track.

## Release requirements

Every release MUST:

0. **Prepare and land the release on `main` first.** `scripts/release_prep.py` requires a clean `main` worktree: its version and changelog mutations, all manual release-current updates, and the release commit belong there. Review and commit that prepared tree on `main`, then build and validate that exact commit. The release commit and **both** tags — the full-version `vMAJOR.MINOR.PATCH` and the moving-major `vMAJOR` — MUST live on `main`. This is not optional polish: [`docs/handoff/deployed.md`](../docs/handoff/deployed.md) defines "Deployed" as _published git refs on `main`_, and every prior release (`v1.x`–`v3.x`) was cut there. A tag on a topic branch (`testing`) is not a release. Do the version-pin bumps (steps 3–6 below) in the release commit on `main`, not on a development branch.

   **Advance the catalog defaults, then reconcile — both before the verification block below.** Promote every successor payload this release activates to `role = "default"` in `catalogs/MAJOR.toml` and flip the predecessor it replaces to `role = "retained"`; a cut that ships without that flip is advertised but resolves for nobody. Then run `uv run project-standards reconcile --apply` in producer mode. It regenerates `.standards/catalog.toml` and `.standards/lock.toml` and re-renders the managed root workflows and delivered `.agents/` copies from the newly selected payloads. Those files are generated: reconcile rewrites them, no one edits them by hand. Both steps must land before the candidate wheel is built, because the verification block proves exactly the bytes they produce. When the re-render moves a digest-pinned managed workflow, [`tests/issue_regressions/ledger.toml`](../tests/issue_regressions/ledger.toml) needs a per-issue amendment record — each affected issue gets its own record quoting that issue's own old digest, never one bare digest swap covering several proofs.

   **Audit the user-facing documents against what the release actually ships.** `scripts/release_prep.py` sweeps [`README.md`](../README.md), [`UPGRADING.md`](../UPGRADING.md), [`ROADMAP.md`](../ROADMAP.md), `docs/usage.md`, `docs/mcp-server.md`, the two adoption prompts, `standards/*/README.md`, and `standards/*/adopt.md` for the outgoing version string, but the sweep only sees version literals. A claim that carries no version number is invisible to it and stays a judgment edit: an advertised package count, a capability list, an install example naming a package the release renames, or a `ROADMAP.md` section still calling "planned" what has already shipped. Close or renumber the roadmap sections this release settles and open the section for the next one, and reconcile every count and capability list with the catalog as activated above.

   **Before creating either tag or publishing, prove that exact release commit.** Confirm the locked environment and payload projection, build and extract the candidate wheel, put it first on `PYTHONPATH`, then run the serial release cross-check, managed-Markdown dogfood validation, and package-contract/release checks. `scripts/release_prep.py` remains mechanical and prints this handoff; it does not run the commands for the owner.

   ```bash
   uv sync --all-groups --locked
   npm ci
   uv run project-standards standards sync-payload-projection --root . --check --json
   uv build --clear --wheel --out-dir build/release-wheel
   rm -rf -- build/wheel-runtime
   uv run python -m zipfile -e build/release-wheel/project_standards-X.Y.Z-py3-none-any.whl build/wheel-runtime
   export PYTHONPATH="$PWD/build/wheel-runtime"
   scripts/verify.sh --full
   uv run project-standards validate
   uv run project-standards standards validate-packages --root . --json
   uv run project-standards standards validate-graph --root . --require-all-manifests --json
   uv run project-standards standards generate-package-schemas --root . --check --json
   uv run project-standards standards render-catalog --root . --check
   uv run project-standards packages check-release --root . --baseline vPREVIOUS --json
   ```

   Replace `X.Y.Z` with the release version and `vPREVIOUS` with the previous full release tag. `--clear` gives the release wheel a unique output directory, and only the generated `build/wheel-runtime` is removed before extraction; this prevents a stale wheel or old extraction from satisfying the gate. The candidate wheel must remain first on `PYTHONPATH` for every command after extraction; otherwise source-tree imports can hide a distribution defect.

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
6. **Update `UPGRADING.md` — version strings every release, structural rewrite on MAJOR only.** [`UPGRADING.md`](../UPGRADING.md) is the step-by-step major-upgrade runbook README.md points consumers to, and it carries an install example that names one exact release. Every release, including a MINOR or PATCH, updates that example and the `project-standards X.Y.Z` string it tells the reader to confirm, so a consumer following the runbook installs the release they are upgrading onto rather than the previous one. Precedent: `8a2d1b9a`, a MINOR, moved both. Nothing else in the document moves outside a MAJOR. On a MAJOR, additionally rewrite the document as **"Upgrading from v(N-1) to vN"** for the new pair, with the new major's breaking-change steps, and update the frontmatter `title` (and `id`, if it encodes the version) to match — both prior majors shipped it rewritten in the release commit. Confirm `README.md`'s pin example (e.g. `@v2` → `@v3`) names the current major pair.
7. **Publish the release and close it out.** The tags are not the publication; a release nobody can download from is unfinished work.
   - **Create the GitHub release** on the full-version tag with authored notes and both build artifacts attached: `gh release create vMAJOR.MINOR.PATCH --title "project-standards vMAJOR.MINOR.PATCH" --notes-file <notes> build/release-wheel/*.whl <sdist>`.
   - **Byte-verify the published assets.** Download the wheel and sdist back from the release and confirm each `sha256sum` equals the locally built candidate's. GitHub re-serving the bytes you uploaded is an assumption, not a fact, and the digests are what `docs/handoff/deployed.md` records.
   - **Confirm the release is marked "Latest"** rather than left as a draft, pre-release, or superseded by an out-of-order tag.
   - **Record the release in the handoff.** A new [`docs/handoff/deployed.md`](../docs/handoff/deployed.md) row is required — it is the definition of "Deployed" this checklist opens with — carrying the release commit, both tag objects, the byte-verified asset digests, and the classification. `docs/STATUS.md`, `docs/TODO.md`, `docs/handoff/state.md`, and a session log should follow through the repository's agent-handoff closeout convention.
   - **Regenerate [`docs/GH-WORKFLOWS.md`](../docs/GH-WORKFLOWS.md)** with `gh-workflow ledger` so the issue and pull-request ledger reflects the closures the release performed.
   - **Decide the consumer pin rollout explicitly**, and record the decision either way. Rolling the `@vMAJOR` consumers forward and deliberately deferring are both acceptable; leaving it unstated is not, because the next release cannot tell a skipped rollout from a forgotten one.
   - **Contribute the durable lessons to `llm-wiki`** — anything a later release cut would otherwise rediscover.

## Consuming repositories

Pin the reusable workflow and the CLI by **major tag** to receive releases on that owner-designated catalog line automatically:

```yaml
uses: L3DigitalNet/project-standards/.github/workflows/validate-markdown-frontmatter.yml@v5
```

- **`@vMAJOR`** (recommended) — tracks the latest release in that major. Catalog channels protect ordinary package defaults and prior advertised selections; breaking package candidates require explicit package-major authorization.
- **`@vMAJOR.MINOR.PATCH`** or a **commit SHA** — an immutable freeze, for repos that want byte-for-byte reproducibility and to adopt every change explicitly.
- **`@main`** — only for this repository's own development or deliberate test repos. Never pin a production consumer to `main`.

A **major upgrade is intentional work**: read the changelog migration notes, bump the pin from `@vN` to `@v(N+1)`, and re-run validation before merging.
