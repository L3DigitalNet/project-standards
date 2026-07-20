---
schema_version: '1.1'
id: 'log-atsd8b-changelog'
title: 'Changelog'
description: 'Notable changes to the project-standards repository.'
doc_type: 'log'
status: 'active'
created: '2026-06-02'
updated: '2026-07-20'
reviewed: '2026-07-20'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'changelog'
aliases: []
related:
  - 'standards/markdown-frontmatter/versions/1.3/README.md'
  - 'standards/markdown-frontmatter/versions/1.3/structure.md'
  - 'standards/markdown-frontmatter/versions/1.3/field-values.md'
  - 'docs/adr/adr-0014-markdown-frontmatter-field-value-policy.md'
  - 'docs/adr/adr-0015-exclude-standards-from-local-frontmatter-scope.md'
  - 'docs/adr/adr-0016-package-markdown-frontmatter-skill-with-standard.md'
  - 'standards/agent-handoff/versions/1.2/README.md'
  - 'docs/research/2026-07-09-agent-handoff-retirement-inventory.md'
  - '.standards/config.toml'
source: []
confidence: 'high'
visibility: 'internal'
license: null
---

# Changelog

All notable changes to this project are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [5.2.0] — 2026-07-20

### Fixed

- The V4→V5 migration platform gate accepts the `"v3"` tag every released v3/v4 CLI actually wrote to `standards_version`, alongside `"v4"`; an unrecognized tag now produces a single `CP-MIGRATION-PLATFORM-VERSION` finding instead of also double-firing `CP-MIGRATION-UNCLAIMED-SETTING` (issue #9).
- Python Tooling 1.3 and Markdown Tooling 1.4 add the released v4-era `.editorconfig` digest, the released v4-era `check.yml` digest, and the released v3-era `check.py` digest to their legacy signatures, so pristine v3/v4 adoptions are recognized during migration (issue #10 and the previously unfiled check-workflow gap).
- The `build-validate-id-pyz.sh` zipapp build resolves PyYAML through `uv run --with` instead of the removed `uv pip install --target` interface.

### Added

- Legacy whole-file signatures may declare `unknown_content_disposition = "preserve"` (bounded takeover): migration preserves consumer-modified content at targets the package manages only through bounded units, reports a `CP-MIGRATION-BOUNDED-TAKEOVER` warning, and steady-state reconciliation takes over just the managed units inside the preserved file. Python Tooling 1.3 applies it to `CLAUDE.md`, `AGENTS.md`, `.editorconfig`, and `.vscode/*`; Markdown Tooling 1.4 applies it to `.editorconfig` and `.vscode/extensions.json` (issue #11).
- Standard Bundle Authoring 2.3 documents digest lineage and the bounded-takeover signature field.
- `UPGRADING.md` documents every common migration preview finding and its resolution procedure.

## [5.1.1] — 2026-07-20

> **Why PATCH:** this release corrects Catalog 4 migration planning for repositories that adopted only a subset of the seven Catalog 5 defaults. It preserves every previously passing consumer outcome and changes no immutable package payload, catalog selection, accepted configuration, or default. `packages check-release --baseline v5.1.0` classifies the release as patch. Project Standards 5.1.1 is published from release commit `784d7bb`.

### Added

- **Copy/paste agent adoption and update guidance.** The promoted prompt routes fresh adoption, V5 updates, and V4 migration; requires preview-before-apply, preservation and fixed-point verification, and sanitized upstream issue reports for adoption or upgrade irregularities.

### Fixed

- **Partial V4 adoption migrates only the packages physically present in legacy configuration.** Missing namespaces no longer crash unrelated default providers or enroll packages merely because a known artifact exists. Explicitly present empty namespaces remain adopted and migrate with package defaults; malformed selected namespaces still fail closed.
- **Provider failures identify their trusted coordinate.** Content-safe errors now include the standard, payload version, provider id, and exception type without exposing raw provider exception text or consumer content.

## [5.1.0] — 2026-07-20

> **Why MINOR:** all seven Catalog 5 consumer defaults advance to backward-compatible immutable payload versions: `adr@1.2`, `agent-handoff@1.2`, `cli-documentation@1.2`, `markdown-frontmatter@1.3`, `markdown-tooling@1.3`, `project-spec@1.2`, and `python-tooling@1.2`. A same-major repin can therefore receive corrected managed bytes, while every superseded version remains advertised and exactly selectable. Reference-only `python-coding@0.6` and internal `standard-bundle-authoring@2.2` are not consumer defaults and do not raise the classification. `packages check-release --baseline v5.0.2` classifies the complete correction train as minor. Project Standards 5.1.0 is published from release commit `b69600d`.

### Added

- **Nine immutable correction payloads.** ADR 1.2, Markdown Tooling 1.3, Python Coding 0.6, and Python Tooling 1.2 correct released documentation without mutating their predecessors. Agent Handoff 1.2 carries the accepted runtime, documentation, Python-floor, and artifact-shape corrections; Project Specification 1.2 restores its reusable-workflow inputs; Markdown Frontmatter 1.3 exposes the stable validator aliases and caller permissions; CLI Documentation 1.2 annotates the existing setup-uv pin; and internal Standard Bundle Authoring 2.2 records the Python 3.14 and executable-mode contracts. All prior payloads remain byte- and mode-identical.

### Changed

- **Python 3.14 or newer is the explicit consumer floor.** Tool metadata, affected runtime payloads, reusable workflows, and top-level installation and migration guidance consistently require Python 3.14 or newer.
- **Consumer locks write schema 1.1.** Successful writes preserve create-only absences without claiming deleted bytes still exist; schema 1.0 remains readable, while the first successful mutation canonicalizes the lock to 1.1.
- **Compatibility CI reuses the exact candidate wheel.** The repository workflow exports the single wheel it already built and drives all compatibility workers from that artifact instead of allowing a second build.

### Fixed

- **5.1.0 consumer documentation and CLI help are synchronized.** Root installation, migration, catalog, reusable-workflow inputs, package defaults, adoption guidance, immutable-pin examples, and terminal-color behavior now match Catalog 5.1.0 and its Python 3.14 floor. Agent Handoff policy-view aliases retain their invoked names, hide and reject `--view` overrides, and specialized adoption help exposes `--manual`, `--harness`, and `--json` without entering the generic adoption path.
- **All 96 accepted or adjusted implementation-review findings.** Corrections cover bounded control-plane safety, atomic filesystem operations, typed error boundaries, package and catalog validation, frontmatter and Project Specification parsing, Agent Handoff behavior, maintained documentation, and test hermeticity. The remaining four findings have final no-change dispositions because their proposed edits were invalid, incompatible, or cosmetic; none is deferred or queued.
- **Repository tests are independent of ambient state.** Verified fixtures resolve from the repository rather than the caller's working directory, and Git-spawning tests ignore hostile user signing configuration without changing repository signing policy.

## [5.0.2] — 2026-07-19

> **Why PATCH:** the only catalog change additively advertises the new **internal** payload `standard-bundle-authoring@2.1`. Internal payloads are never consumer-selectable, so no consuming repository's resolution, immutable released payload, public command, or conforming consumer outcome changes; `packages check-release --baseline v5.0.1` classifies the transition as patch under the internal-additive rule below. Prepared on `testing`; the owner cuts the tags on `main`.

### Added

- **`standard-bundle-authoring@2.1`.** New internal payload correcting the 2.0 README's SPEC-BA02 pointer to the maintained location `docs/specs/2026-07-10-standard-bundle-authoring-v2-spec.md`. The released 2.0 payload is byte-identical to its v5.0.1 baseline and remains advertised in Catalog 5; 2.1 is the family's current authority.

### Changed

- **Additive internal catalog advertisements classify as PATCH.** `packages check-release` previously raised any catalog-entry difference to MINOR. Purely additive entries with the `internal` role now stay PATCH, because internal payloads are never consumer-selectable and cannot change a consuming repository's validation outcome — the compatibility this repository versions. Removals, digest or role changes, and any consumer-visible addition keep their existing levels; the change only relaxes classification, so no previously passing release becomes forbidden.
- **`docs/superpowers/` is retired.** Historical design documents moved to `docs/specs/archive/` (indexed by its README), research and reference packs consolidated into `docs/research/` (indexed by `index.md`), and the active Agent Handoff implementation plan moved to `docs/plans/`. The BA02 compatibility symlink is gone — payload 2.1 carries the corrected link instead.

### Removed

- **Completed ephemeral documents.** The implemented Python Tooling checker-table materialization plan, its four design-review audit documents, and the empty `docs/codex-reviews/` directory. Plans and reviews are ephemeral; specs and ADRs are the durable record.

## [5.0.1] — 2026-07-18

> **Why PATCH:** this release corrects internal provider integrity, command error classification, repository enforcement, and current documentation without changing any immutable package payload, catalog selection, public command, accepted input, or conforming consumer outcome.

### Fixed

- **Declared provider integrity checks are bounded to declared inputs.** Provider execution no longer scans or hashes the whole repository. It rechecks only declared file and directory snapshots, including immediate directory membership, entry type, and permission bits, so unrelated repository activity cannot produce false mutation findings while declared writes remain blocked.
- **Agent Handoff command failures use the documented exit taxonomy.** Missing or malformed operator configuration exits 2, invalid catalog or lock state and internal prerequisites exit 3, and recoverable upgrade-apply failures return an `AH-APPLY-FAILED` finding with exit 1 instead of escaping as an internal error.
- **Current Catalog 5 documentation and CLI reference match the shipped implementation.** Public help now lists the supported `fix` options; maintained specifications, ADRs, family landing pages, usage guidance, status, and authority links consistently distinguish mutable navigation from immutable payload authority and V5 routing from retained V1 compatibility.

### Changed

- **Repository package drift enforcement now covers every generated contract.** The graph workflow checks packages, graph structure, generated schemas, payload projection, and catalog rendering. Package tests prove exact source, direct-wheel, and sdist-derived-wheel parity without changing immutable payloads or catalog selections.

## [5.0.0] — 2026-07-17

> **Why MAJOR:** v5 replaces the legacy `.project-standards.yml` and package-specific provenance plane with the unified `.standards/` control plane, activates immutable catalog-5 packages, and carries validator and tooling changes that may newly fail a previously-passing v4 consumer. Follow [`UPGRADING.md`](UPGRADING.md) to preview and apply the migration before repinning workflows and the CLI.

### Added

- **Consumer standards control plane and V4 migration.** V5 initializes the neutral three-file `.standards/` scaffold, resolves catalog/package/contract selectors, composes whole-file and semantic units in one virtual tree, and applies reviewed plans through one lock-last executor. `init --migrate` produces human/JSON previews for every current legacy namespace and exact artifact signature; explicit apply verifies unified state before retiring `.project-standards.yml` and package-specific locks. Same-major catalog refresh, recovery, package-major authorization, and v5-only warned legacy fallback are covered end to end.
- **Versioned package-contract authoring and current-package activation.** Strict V2 family indexes, immutable payloads, closed option schemas, catalogs, integrity inventories, semantic contributions, bounded providers, and migrations now back all nine current packages. Catalog 5 advertises the seven consumer packages; source/direct-wheel/sdist-wheel parity, offline provider execution, release classification, schema/projection drift, and package graph gates pass without package-ID branches in shared control-plane code.
- **Real package compatibility and release-cut proof.** Catalog-derived tests cover seven individual defaults, all 21 unordered pairs, the full set, every legacy namespace, shared ownership/removal, consumer-state preservation, validators, deterministic order sweeps, installed-wheel parity, and scale budgets. A disposable tracked-tree checkout builds `5.0.0`, migrates through the installed CLI, runs the complete provider-backed command matrix, proves byte-level fixed-point convergence, verifies same-major refresh preservation, and replays the recorded binary patch to identical control-plane digests.
- **Unified consumer standards control-plane architecture.** ADR 0023 establishes a neutral `.standards/` desired/applied-state plane with explicit reconciliation, a central provenance lock, immutable package payloads, conventional-path integration, and typed semantic composition of consumer-owned shared files. ADR 0024 defines catalog-scoped package channels: ordinary `latest` remains non-breaking within the selected catalog major, while breaking package candidates require explicit package-major authorization until a later catalog-major promotion. The decisions supersede the conflicting legacy adoption, namespace, manifest, and package-versioning ADRs and reconcile the retained lifecycle, provenance, skill, hook, frontmatter, and repository versioning policies.
- **Compact agent summaries for all nine standard packages.** Every manifested standard now provides a canonical-linked `agent-summary.md`, declares it as `resources.agent_summary`, and exposes a generated `standards://<id>/agent_summary` catalog URI. Repository readiness enforces nine-of-nine coverage, the canonical-authority notice, and a 3,000 UTF-8 byte maximum while keeping each README normative.
- **Standard Bundle Authoring Standard.** The ninth repository bundle defines the authoring contract for all nine standards, including manifest identity, adoption modes, versions, config namespaces, capabilities, relationships, resources, artifact linkage, authorities, providers, lifecycle, and explicit agent-context decisions.
- **Typed standard manifests and provider execution.** A strict `standard.toml` model, generated JSON Schema, nine real manifest retrofits, and a generic provider runner make standard metadata and supported operations machine-discoverable without hardcoded per-standard parsing.
- **Standards graph, composition proof, and hosted enforcement.** Graph validation now checks authority, namespace, capability, relationship, resource, provider, artifact-linkage, and hidden-dependency rules. Individual, pairwise, and all-standard fixtures prove safe composition; `standards/catalog.md` provides a generated human index; and a dedicated GitHub Actions workflow checks the graph and catalog on pull requests and pushes to `testing` and `main`.
- **Agent Handoff Standard `1.0`.** A new opt-in, repository-confined standard packages project memory under `docs/`, a repo-local `$agent-handoff` skill, and one dependency-free shared SessionStart hook for Claude Code and Codex. `project-standards adopt agent-handoff` supports manual, Claude-only, Codex-only, and dual profiles; the `agent-handoff` command group adds `validate`, `drift-check`, `size-report`, `shape-check`, read-only `legacy-report`, and provenance-guarded `upgrade`. Adoption never writes outside the target repository or overwrites consumer-owned knowledge. The legacy migration guide deliberately leaves structural reconciliation to the consuming repo's local agent; the old engine is not retired until the tracked consumer inventory is clean and the owner approves deletion.
- **Artifact lifecycle and provenance metadata.** Packaged `adopt.toml` artifacts now declare provenance and an `install_policy` of `managed` or `create-only`, with optional canonical-source, deterministic-transform, and POSIX-mode metadata. This separates refreshable standard-owned artifacts from consumer-owned create-once knowledge while retaining the existing collision-safe adoption engine.

### Changed

- **GitHub Action runtimes refreshed for v5.** Live repository workflows and current V2 package/provider output now use `actions/checkout@v7`, `actions/setup-node@v6`, Node 24, and SHA-pinned `astral-sh/setup-uv` v8.3.2. Lockfile-free reusable formatting explicitly disables setup-node's automatic package-manager cache; workflows that run `npm ci` retain explicit npm caching. Node 24 actions require GitHub Actions Runner v2.327.1 or newer. Registered legacy workflow bytes remain unchanged for exact migration recognition.
- **Release verification now parallelizes only the compatibility matrix.** The repository gate prebuilds one offline wheel, runs all 56 catalog-derived source/wheel lifecycle rows across four explicit pytest-xdist workers, keeps ordinary tests, disposable release replay, and performance thresholds serial, and combines suffixed coverage data before enforcing the existing 85% floor. The final measured matrix wall time fell from 711.78 seconds serially to 177.10 seconds locally. Catalog-default discovery is cached per worker, a release-input digest rejects stale evidence before the expensive replay begins, and coverage data is removed even when a phase fails.
- **Markdown indentation now matches Prettier and markdownlint.** The shared `.editorconfig` keeps tabs for JSON/JSONC but overrides Markdown to two spaces, matching Prettier's CommonMark list output and MD007's `indent: 2`. The dogfood root, packaged shared artifact, and both owning standards describe the same copy-adopt behavior.
- **Current package payloads reconstructed for V5.** ADR `1.1`, Agent Handoff `1.1`, CLI Documentation `1.1`, Markdown Frontmatter `1.2`, Markdown Tooling `1.2`, Project Specification `1.1`, Python Coding `0.5`, Python Tooling `1.1`, and Standard Bundle Authoring `2.0` now ship immutable package payloads. The seven consumer packages replace V1 fragment/copy-adopt authority with closed options, managed or create-only outputs, semantic ownership, typed providers, exact legacy migration, and central locking.
- **Standard metadata and artifact planes are linked explicitly.** Seven artifact-bearing standards now connect their canonical `standard.toml` metadata to packaged `adopt.toml` manifests with validated provenance, while the two non-adoptable bundles remain explicit through `reference-only` or `none` adoption modes.
- **Markdown Frontmatter Standard split into structure and field-value guidance.** The canonical entry point now links to separate structure/schema rules (`structure.md`) and semantic field-value policy (`field-values.md`), plus a new repository-frontmatter ADR template for consumers that need to document governed scope, owner roles, lifecycle triggers, canonical tags, and repo-local extensions, including baseline IT, network, infrastructure, and deployment tags. This repo dogfoods the guidance with ADR 0014 and records ADR 0015 to exclude `standards/**` from the local markdown-frontmatter corpus so published standard content is not required to carry repo-local metadata. No schema fields, enum values, validator behavior, or `schema_version` changed; new documents still use `schema_version: '1.1'`.
- **Markdown Frontmatter Standard now owns and ships the `markdown-frontmatter` skill.** The standard bundle carries the canonical skill under `standards/markdown-frontmatter/skills/markdown-frontmatter/`; the packaged adopt bundle installs it repo-local at `.agents/skills/markdown-frontmatter/` for Claude Code and Codex CLI, including the executable `new-doc-id` helper. The adopt engine now supports an explicit artifact `mode` for installed scripts so fresh adopters receive executable helper files. ADR 0016 records the ownership decision, and the old `agent-configs` source copy is retired. This is an adoption-surface addition only: no schema fields, enum values, validator behavior, or `schema_version` changed.
- **ADR Standard — canonical ADR directory moved from `docs/decisions/` to `docs/adr/`.** The ADR bundle (`standards/adr/README.md` directory/index convention and `adopt.md`), the adopt manifest (`project-standards adopt adr` now writes `docs/adr/adr.template.md`, previously `docs/decisions/adr.template.md`), and the "exception ADR" location referenced by the Markdown Tooling, Project Specification, and Python Tooling standards — plus the Markdown Frontmatter `concept`/`runbook` examples and the root README pointer — now all prescribe `docs/adr/`. Backward-compatible for existing consumers: the frontmatter validator never enforced ADR location and `adopt adr` is skip-if-exists, so a repo already keeping ADRs under `docs/decisions/` continues to validate — only the recommended path and the freshly-adopted template destination move. **Package impact: `adr` package `1.0` → `1.1` (recommended-path + adopt-destination change); its independently selected ADR document contract remains `1.0`. The Markdown Tooling / Project Specification / Python Tooling references are documentation-consistency corrections. Refresh the family and catalog integrity metadata as part of the v5.0.0 cut, per `meta/versioning.md`.**

### Fixed

- **Agent Handoff local-reference validation no longer reports links inside Markdown code examples and now URL-decodes repository paths.** Percent-encoded paths such as `%20` resolve to their real local files, while inline, fenced, and indented code samples are excluded from link checking. Real missing local links remain errors.

### Security

- **Dev-tooling bump: `markdownlint-cli2` `0.22.1` → `0.23.0`** (markdownlint `0.40.0` → `0.41.0`), the reusable `lint-markdown.yml` action `DavidAnson/markdownlint-cli2-action` `v23` → `v24`, and `tests/coherence/test_pins.py` updated so the local pin and the CI-bundled version stay in lock-step. Clears two moderate npm advisories in transitive dev-only dependencies — js-yaml merge-key quadratic DoS (`GHSA-h67p-54hq-rp68`; now `5.2.0`) and markdown-it smartquotes quadratic DoS (`GHSA-6v5v-wf23-fmfq`; now `14.2.0`); `npm audit` reports 0 vulnerabilities. markdownlint 0.41 adds **no new rules** (it refines MD022/MD028/MD035/MD042/MD051/MD060 and removes inline-directive handling), and the repo's 85-file corpus lints clean under it, so consumer-visible risk via the `@v5` reusable workflow is low — the action bump ships with v5.0.0 rather than as a silent interim change.

## [4.3.0] - 2026-07-07

### Added

- **CLI Documentation Standard registered — sixth adoptable standard.** A new bundle (`standards/cli-documentation/`: `README.md`, `adopt.md`, `templates/`, `examples/`, `resources/`) governs user-facing CLI usage documentation — the four-artifact model (`--help` / usage doc / man page / README), option-entry and synopsis conventions, and task-first examples. Adopt artifacts: a `docs/usage.md` scaffold and a `cli-docs-check.yml` CI workflow template, plus a `.project-standards.yml` config fragment. Registered end-to-end like the other version-tracked standards: a `cli_documentation` contract (version `1.0`) in `registry.json`, the adopt-engine manifest/parity gate, and the `project-standards adopt cli-documentation` CLI path.
- **`--version` on all seven installed console scripts**, via a shared helper — previously only some commands reported their version.
- **`--help` on the two sync-style commands** (`sync-vscode-colors`, `sync-standards-include`) — previously `--help` was treated as a positional filename argument and produced a confusing per-file error instead of usage text.
- **`docs/usage.md`** — this repository dogfoods the new standard: a canonical usage document covering all seven installed console scripts (`project-standards`, `validate-frontmatter`, `validate-id`, `validate-references`, `format-frontmatter`, `sync-vscode-colors`, `sync-standards-include`) and the `spec` subcommand group.
- **Installed-wrapper smoke tests and a usage-doc inventory-parity guard** — new tests confirm the packaged console scripts run correctly once installed (not just in-source) and that `docs/usage.md` enumerates exactly the commands the package ships, so the two surfaces cannot silently drift apart.

### Changed

- **`src/project_standards/README.md` repositioned as an implementation-internals reference** — user-facing CLI usage documentation now lives in `docs/usage.md` (the CLI Documentation Standard's canonical artifact); the source README documents module layout, the adopt engine, and the contract-version registry for contributors. Its "Adding a new standard" checklist is expanded to cover `registry.py`, the validator gate, and bundle/fixture ripple effects, closing gaps a contributor previously had to discover by trial and error.

## [4.2.0] - 2026-07-06

### Added

- **Markdown Tooling: opt-in reusable Prettier gate.** A new `format.yml` reusable workflow (dual-role) plus the adoptable `format.caller.yml` enforce `prettier --check .` repo-wide (pinned Prettier `3.8.3`), with a `prettier: false` job-level opt-out. `adopt markdown-tooling` now also writes `.github/workflows/format.yml`. Contract `markdown_tooling` bumped `1.0 → 1.1`. Supersedes DEC-9 (see DEC-10). Additive/opt-in — no existing consumer is affected until they adopt.

## [4.1.0] - 2026-07-06

### Added

- **Project Specification:** `spec.reference_prefixes` config key — declare external ID namespaces (backlog, tickets, ADRs) the spec cites but does not mint, exempting them from the Appendix-A, width, and tier checks. Validated for shape and rejected on collision with a canonical spec-local prefix.
- **Project Specification:** opt-in `--config` on `spec upgrade` so it honors `reference_prefixes` during source and output validation. Defaults to not loading config, so existing `upgrade` invocations are unchanged.

### Changed

- **Project Specification:** the ID scan now skips the sibling ADR standard's ids (built-in `ADR` reference prefix; lowercase `adr-…` was already ignored) and versioned SPDX license identifiers (`MPL-2.0`, `CC-BY-4.0`, `GPL-3.0-only`, `LGPL-2.1-or-later`, …), plus common license-family prefixes for bare colloquial forms like `GPL-3`. Zero-version SPDX ids (`MIT-0`, `NTP-0`) share a spec-local id's shape — declare their family in `reference_prefixes`.
- **Project Specification:** `SV-ID-UNDECLARED` now names `spec.reference_prefixes` as the resolution instead of dead-ending at Appendix A.
- **Project Specification:** the §8.3 template `ADR` column models a real `adr-0001-…` example.

All changes are a backward-compatible loosening (a previously-passing spec cannot newly fail); `@v4` consumers inherit them automatically.

## [4.0.0] — 2026-07-05

> **Why MAJOR:** six independent validator/config strictness bumps below each newly-fail a previously-passing document or config, and the Python Tooling SSOT's ruff floor raise newly-fails a previously-passing re-sync — the previously-passing rule in `meta/versioning.md` applies "without exception" to each on its own. The Project Specification Standard's registration is additive (MINOR) and the `pytest-cov` removal is a no-op (PATCH, confirmed via `git log -p` on commit `752ad32`: the gate command never used it), but a release is classified by its **worst** change, so this ships as `4.0.0`.

**Migration from `v3`.** This is a major release; adopt it deliberately. The full step-by-step runbook is [`UPGRADING.md`](UPGRADING.md); the essentials:

- **Re-pin both refs to `@v4`.** Bump the reusable-workflow pin `validate-markdown-frontmatter.yml@v3` → `@v4` **and** set `standards-ref: 'v4'` — match it to your `uses:` pin so the workflow definition and the installed validator never drift. Same for `lint-markdown.yml` if you call it.
- **Audit documents and config before re-pinning — v4 rejects what v3 silently accepted.** Datetime-shaped `created`/`updated`/`reviewed` values now fail (quote as `'YYYY-MM-DD'`); tags with leading/trailing/consecutive hyphens fail; non-string frontmatter keys fail; duplicate top-level config keys, unquoted numeric config `version` values, and nonexistent explicit file/`--config` paths now exit 2 instead of passing silently.
- **Repos with `references.enabled: true`:** the corrected cross-file semantics (per-id supersede merging, numeric ADR ordering, date-typed ordering) may newly flag real violations that v3's bugs masked. Repos without the opt-in are unaffected.
- **Copy-adopters (Python Tooling SSOT), on re-sync only:** ruff dev-group floor is now `>=0.14`; `pytest-cov` is dropped from the scaffolds.
- **New, opt-in:** the **Project Specification Standard** (`spec:` config block, `project-standards spec` CLI, `validate-specs.yml@v4` reusable workflow) is available from `v4.0.0` onward — see [`standards/project-spec/adopt.md`](standards/project-spec/adopt.md). Nothing is inherited without the config block.

### Added

- **Project Specification Standard registered — `project-standards spec` command group.** A fifth governed standard (`standards/project-spec/`): three tiered spec templates (Light ⊂ Standard ⊂ Full) with stable canonical numbering and typed IDs, plus a CLI operating on a repository's real specs — `validate` (deterministic structural gate: numbering, annotated gaps, appendix lettering, cross-references, frontmatter, ID uniqueness/tier/format, table shape), `lint` (advisory: unfilled placeholders, un-deleted template guidance, status-aware traceability), `extract` (print one ID row, section, heading match, or appendix), `next` (next free ID for a prefix), `new` (scaffold from a template, fail-closed self-validated before writing), and `upgrade` (additive Light→Standard→Full tier promotion — inserts missing sections/appendices at their stable numbers, never renumbers, gated on the source already validating clean and its scaffolding matching the canonical template for its tier). A new reusable CI workflow (`.github/workflows/validate-specs.yml`, `workflow_call` with `config-path`/`standards-ref`/`strict-lint` inputs) runs `spec validate`/`spec lint --strict` against a consumer's declared `spec:` config block. Unlike the copy-adopt standards, nothing is seeded into a consumer repo — installing `project-standards` gives the full tool surface directly. Full adoption procedure: [`standards/project-spec/adopt.md`](standards/project-spec/adopt.md). **Additive — MINOR** per `meta/versioning.md`'s "Bundled contract set" row (a new, opt-in standard; nothing previously-passing is affected).
- **`adopt python-tooling` now also delivers `.vscode/settings.json` and `.vscode/tasks.json`.** The standard's §13 always mandated all three `.vscode` files, but the adopt CLI only ever shipped `extensions.json` — `adopt.md` never disclosed the gap. Additive (skip-if-exists) — **MINOR**.

### Changed

- **`validate-frontmatter` — six independent strictness bumps, each MAJOR on its own (previously-passing rule):**
  - Frontmatter `date`-typed fields (`created`, `updated`, `reviewed`) now reject a `datetime` value outright instead of silently truncating it to a date — a document whose YAML parsed a value as a full timestamp (e.g. an unquoted `2026-06-03T00:00:00`) now fails instead of passing with data silently dropped.
  - A config `version` field (`markdown.frontmatter.version`, `markdown.adr.version`, etc.) given as an unquoted number now exits 2 (`"{key} must be a quoted string..."`) instead of parsing as a float and silently losing precision (`1.10` → `1.1`).
  - The `tags` field's pattern tightened to `^[a-z0-9]+(-[a-z0-9]+)*$` (in-place 1.1 schema change) — a previously-accepted tag with, e.g., a leading/trailing hyphen or consecutive hyphens now fails.
  - `.project-standards.yml` config files with a duplicate top-level key now exit 2 (`_UniqueKeyLoader`) instead of silently keeping only the last occurrence — the config analog of the frontmatter duplicate-key rejection that shipped in `3.0.0`.
  - A non-string frontmatter key (e.g. a bare YAML key that parses as a number or boolean) is now explicitly rejected with a clear message instead of whatever downstream behavior it previously triggered.
  - An explicitly-named file argument that does not exist, or a typo'd `--config` path, now exits 2 instead of silently falling through to a vacuous green run.
- **Python Tooling SSOT — ruff dev-group floor raised `>=0.9.0` → `>=0.14`.** Required because `target-version = "py314"` is rejected outright by ruff 0.9–0.11 and only preview-supported in 0.12–0.13 (verified against 0.9.0/0.12.0/0.13.0/0.14.0) — the previously-recommended floor could not actually run the standard's own shipped config. Raising a tool floor is **MAJOR** for a consumer that re-syncs, per `meta/versioning.md`'s Python/Markdown Tooling row.
- **Python Tooling SSOT — `pytest-cov` dropped from §6, the fragment, and this repo's own dev group.** Confirmed via commit history that nothing in the standard's documented verification gate ever used it — the gate has always run `coverage run -m pytest` directly, and a second coverage entry point is exactly the overlapping-tools problem the standard's §3 prohibits. **PATCH — no consumer-visible change** (a re-syncing consumer's working gate command is unaffected).
- **Frontmatter template `id` placeholders reworded** from the literal `replace-with-stable-id` to format-teaching hints, and the Python Tooling standard gained a pre-commit scope note. Both docs-plane, no schema/validator change — **PATCH**.

### Fixed

- **`validate-references` semantic corrections — affect only consumers who set `markdown.frontmatter.references.enabled: true`.** These change cross-file check outcomes; a consumer who has the check enabled may see a previously-passing run newly flag or newly pass:
  - Supersede sets are now merged per-id across the index instead of last-wins, so a document superseded from multiple sources is reconciled correctly rather than dropping all but the last relationship.
  - ADR sequence numbers are compared **numerically**, not lexically — `adr-0010` now sorts after `adr-0009`, so duplicate/ordering violations that lexical comparison masked are newly caught.
  - `created`/`updated`/`reviewed` dates are parsed as dates for ordering rather than compared as strings.
  - A run over an empty index, or one that skips a custom-schema repo, no longer exits silently green as a vacuous no-op.
  - Files skipped from the index are now surfaced as warnings instead of vanishing silently.

  (Pure-internal refactors and error-path hardening — e.g. the `Index.ids` removal and `UnicodeDecodeError` handling — are intentionally omitted here: they do not change outcomes for well-formed inputs.)

- **`format-frontmatter` / CLI fixes** (to commands shipped in `3.0.0`):
  - `format-frontmatter --config <nonexistent-path>` now exits 2 (`"config file not found"`) instead of silently formatting and writing under repo defaults — the same previously-passing-rule fix already applied to `validate-frontmatter`.
  - `format-frontmatter` no longer tracebacks on non-UTF-8 input; it reports a clean per-file error and the run continues.
  - `project-standards validate --help` — the `--glob` help text is corrected: the flag **replaces** the config include list, it does not add to it.
- **Doc-consistency fixes** (docs-plane, **PATCH**):
  - Markdown Frontmatter README's Tags section corrected from the stale `^[a-z0-9][a-z0-9-]*$` to the enforced `^[a-z0-9]+(-[a-z0-9]+)*$`.
  - Markdown Tooling `adopt.md` gained two missing adoption steps.
  - Frontmatter `adopt.md`'s §2 example config byte-locked to the shipped starter — it had drifted to omit the `**/*.template.md` exclusion, which would have led a manual adopter to wrongly validate template placeholder frontmatter.

The migration notes at the top of this section are the consumer-facing summary; [`UPGRADING.md`](UPGRADING.md) is the step-by-step runbook.

## [3.0.0] — 2026-06-09

> **Note for release planning:** This release is **3.0.0 / MAJOR**. Two independent changes each individually require a major bump per the **"The previously-passing rule"** section and the **Validator CLI** + **Reusable workflow** rows of the Change-classification table in `meta/versioning.md`: (1) `validate-id` now runs in the reusable CI workflow, so consumers with old-style kebab ids will newly fail on re-pin; (2) `parse_frontmatter` now rejects duplicate top-level YAML keys, which can fail a previously-passing document that happened to contain them.

**Migration from `v2`.** This is a major release; adopt it deliberately. The full step-by-step runbook is [`UPGRADING.md`](UPGRADING.md); the essentials:

- **Re-pin both refs to `@v3`.** Bump the reusable-workflow pin `validate-markdown-frontmatter.yml@v2` → `@v3` **and** set `standards-ref: 'v3'` — match it to your `uses:` pin so the workflow definition and the installed validator never drift.
- **Audit `id` fields before re-pinning — CI now runs `validate-id` on every managed document.** Ids in the old recommended kebab style (e.g. `restart-netbox-after-config-change`) now fail with `[id] prefix '…' is not a valid doc_type`. Run `validate-id --fix --config .project-standards.yml` to auto-regenerate non-ADR ids as `{doc_type}-{base36}-{slug}`; ADR ids are not auto-fixed — update them by hand to `adr-{NNNN}-{repo-name}-{short-title}`. Repos on a custom `markdown.frontmatter.schema` path are exempt (`validate-id` skips automatically).
- **Remove any duplicate top-level frontmatter keys.** The YAML parser now rejects them (previously the last value silently won); symptom: `invalid YAML frontmatter: duplicate key '…'`. Fix: delete the duplicate.
- **`validate-references` stays off until you opt in.** Re-pinning does not enable the cross-file checks; add `markdown.frontmatter.references.enabled: true` to `.project-standards.yml` only when ready. Omitting it produces no new failures.

### Added

- **`format-frontmatter` command** — reformats YAML frontmatter to canonical style (`--write` to rewrite in place, `--check` to report-only). Applies canonical key ordering, single-quote-wraps all string values, renames the deny-listed `type` alias to `doc_type`, renders empty arrays as `[]` and non-empty arrays in block style, and preserves the document body unchanged. Skips files under a custom schema.
- **`validate-references` command** — opt-in cross-file checker (`markdown.frontmatter.references.enabled: true`). Enforces id uniqueness (error), referential integrity (warning — each value in `related`/`depends_on`/`supersedes`/`superseded_by` must resolve as a known document `id` or a repo-root-relative path), supersede reciprocity (warning, both directions), date ordering (error — `created` ≤ `updated`, and `reviewed` ≥ `created` when present), and ADR-number uniqueness (error — no two ADRs share the same `adr-NNNN`). Self-gates: exits 0 immediately when not enabled, so adding it to CI is a no-op until the repo opts in.
- **`project-standards fix` subcommand** — three-phase pipeline: format frontmatter (`--write`), regenerate non-compliant ids (`--fix`), then re-run the full `validate` contract (schema + id + references) as a postcondition. Skips entirely under a custom schema (CR-001). Postcondition failure (e.g. duplicate-id reference error) surfaces as a non-zero exit even after successful write phases.
- **`project-standards validate` also runs `validate-references`.** The combined `validate` command now invokes all three validators — `validate-frontmatter`, `validate-id`, and `validate-references` — returning the worst exit code. `validate-references` is a no-op when `references.enabled` is false, so existing repos without the opt-in are unaffected.
- **`validate-id` command** — validates that `id` fields conform to the project-standards format. Two formats are enforced: `{doc_type}-{6-char base36 token}-{readable-slug}` for all standard doc types (e.g. `note-a3f9zk-tailscale-acl-gotcha`); `adr-{NNNN}-{repo-name}-{short-title}` for ADRs. The readable-slug is validated as well-formed kebab-case but is **not** matched against the current `title` — ids are frozen at creation time and must remain stable after a document is renamed. Files with no frontmatter, or missing/invalid `id`/`doc_type`, are silently skipped (those gaps are caught by `validate-frontmatter`). When a custom schema is in use — either via the `--schema` CLI flag or `markdown.frontmatter.schema` pointing to a file path in the config — id validation is skipped entirely (custom schemas may define different id conventions).
- **`project-standards` CLI with an `adopt <standard>...` subcommand** that materializes a chosen standard's canonical artifacts into a consumer repo (plus `list` and a back-compat `validate` subcommand). Adopting any subset — including all four standards together — is supported; runs are idempotent (skip-if-exists, `--force` to overwrite regular files only), path-safe (never writes through a symlink or outside `--dest`), and use atomic writes (a failed `--force` never truncates the original). `fragment` artifacts (the `pyproject.toml` and `.project-standards.yml` sections) are **reported for manual merge, never written**. The existing `validate-frontmatter` console script is retained as a back-compat alias.
- **Per-standard `adopt.toml` manifests and bundled templates** under `src/project_standards/bundles/`, resolved at runtime by the same `Path(__file__)`-relative, wheel-safe lookup the bundled schema/registry already use. A generic engine reads each manifest, so adding a standard is data, not code.
- **`.pre-commit-hooks.yaml`** — consumers can use this repo as a pre-commit source (`repo: https://github.com/L3DigitalNet/project-standards`). Six hooks: `format-frontmatter-fix`, `format-frontmatter-check`, `validate-id-fix`, `validate-id-check`, `validate-frontmatter`, and `validate-references` (whole-repo, `pass_filenames: false`).
- **`standards/python-coding/` — Python Coding standard (in-development draft).** Code-shape and agent-behavior rules for Python; the reference companion to the Python Tooling SSOT. Ships as a **draft (version 0.4)**: reference-only, unregistered (no contract version), excluded from frontmatter validation, and not adoptable via the CLI. First present in the `3.0.0` tree; outside the release contract until registered.

### Changed

- **`validate-markdown-frontmatter.yml` now also runs `validate-id` and `validate-references`.** `validate-references` is a self-gated no-op unless the calling repo enables it, so there is no breakage for repos that have not opted in. Consumers whose managed documents carry old-style kebab ids (e.g. `restart-netbox-after-config-change`) will begin failing the `validate-id` step once they re-pin to the new release tag. Per the **"The previously-passing rule"** in `meta/versioning.md`, any stricter validator or workflow behavior that can fail a previously-passing consumer requires a **major** version bump. Consumers on a custom (non-bundled) `markdown.frontmatter.schema` are unaffected — `validate-id` skips automatically.
- **Copy-adopt scaffolds relocated** out of README/`adopt.md` prose into packaged bundles (documentation reorganization; non-breaking — consumers pin git tags and reusable-workflow filenames, not template paths). Each standard's `adopt.md` now references `project-standards adopt <id>`.
- **Python Tooling `.editorconfig` JSON/Markdown indentation reconciled** to the shared superset floor (global `indent_style = tab`; `[*.py]`/`[*.toml]` 4 spaces; YAML 2 spaces). A clarifying change to a copy-adopt standard — copy-adopt standards are never inherited automatically, so it cannot newly-fail an existing consumer.

## [2.0.0] — 2026-06-07

**Migration from `v1`.** This is a major release; adopt it deliberately:

- **Re-pin to `@v2`.** Bump the reusable-workflow pin `validate-markdown-frontmatter.yml@v1` → `@v2` and set `standards-ref: 'v2'` (the workflow now defaults `standards-ref` to `v2`). The opt-in body linter `lint-markdown.yml@v2` becomes available at this tag.
- **The validator CLI now requires Python 3.14+.** Installing the `project-standards` package via `uv tool install` needs Python 3.14 (`requires-python` `>=3.11` → `>=3.14`).
- **Copy-adopters, on re-sync only:** the Python Tooling baseline is now 3.14, and the §15 CI template SHA-pins `astral-sh/setup-uv` (the old `@v8` tag no longer resolves).
- **Doc deep-links moved** into the per-standard bundles (`standards/<name>/…`) and `meta/`. The **validation contract is unchanged** — reusable-workflow names, the `validate-frontmatter` entry point, and the bundled schema path are identical — so a repo that passed on `@v1` keeps passing after re-pinning to `@v2`.

### Added

- **Python tooling stack adopted from `standards/python-tooling-ssot-standard.md`:** `uv_build` backend, `src/` layout, the validator moved to `src/project_standards/` with the schema bundled inside the package, `basedpyright` (strict), branch coverage (`fail_under = 85`), and `pip-audit`. CI gate consolidated to `check.yml`.
- **Opt-in ADR section check (`markdown.adr.require_sections`).** A new, default-off config flag makes the validator additionally assert that every `doc_type: adr` document contains the three MADR-required level-2 sections — `## Context and Problem Statement`, `## Considered Options`, `## Decision Outcome`. The match is exact and case-sensitive; headings inside fenced code blocks (e.g. template snippets) and the optional MADR sections are correctly ignored. It lives under a separate `markdown.adr` config namespace, keeping the validator's frontmatter remit distinct. This repo enables it to dogfood the shipped ADR example. Additive (default off) → MINOR.
- **Opt-in Markdown body linting (Stack B).** A new reusable workflow `.github/workflows/lint-markdown.yml` runs `markdownlint-cli2` (via `DavidAnson/markdownlint-cli2-action@v23`) against the repo's published `.markdownlint.json`, finally executing the Markdown _body_ rules that previously shipped as config with no runner. It is **separate** from `validate-markdown-frontmatter.yml` so frontmatter-only consumers never inherit a Node toolchain — opt in with `uses: L3DigitalNet/project-standards/.github/workflows/lint-markdown.yml@v2`. The action bundles its own Node runtime and auto-discovers `.markdownlint.json`, so no committed Node project is required. Also adds `.markdownlint-cli2.jsonc` (a local-runner config that honors `.gitignore`, so a bare `npx markdownlint-cli2` matches CI) and a `github-actions` Dependabot entry to keep the action pins current. Additive — pin `@v2`.
- **Per-standard contract versions.** Each standard now carries its own `major.minor` contract version, selected independently in `.project-standards.yml` (`markdown.frontmatter.version`, `markdown.adr.version`, `python_tooling.version`). A bundled registry (`src/project_standards/schemas/registry.json`) maps versions to schemas and records ADR→Frontmatter compatibility, which the validator now enforces. All keys are optional and default to today's behaviour — a config with no `version:` keys validates byte-identically. The Python Tooling internal-revision counter is replaced by contract version `1.0`. Additive — see `meta/versioning.md`.
- **Markdown Tooling Standard (`standards/markdown-tooling/`).** A new governed bundle documenting the recommended linting/formatting tools and settings for Markdown and the structured-text files Prettier handles: **markdownlint** (the seedable `.markdownlint.json` rule set + the reusable `lint-markdown.yml@v2` workflow), **Prettier** (copy-adopt formatter config; no reusable workflow, DEC-9), and **EditorConfig**. Source-backed, parallel to the Python Tooling standard, and cross-linked from the tool-neutral Frontmatter standard. Adds a validated `markdown_tooling` contract version (`1.0`) to `registry.json`, recognized by the validator (`markdown_tooling.version`; unknown values exit 2) like `python_tooling.version`. Additive — MINOR.

### Changed

- **Python Tooling standard — lint/format/type-check scope made explicit and flexible.** The `src/` requirement now governs the importable package/product only; repo tooling, `scripts/`, archived, and non-product Python may live outside `src/` (still linted + formatted, not held to the strict-`src/` typing bar). Directories owned by external programs (`.claude/`, `.agents/`, `.codex/`, `.vscode/`, `.github/`, `.venv/`, `.continue/`, …) are excluded from the toolchain (baseline gains `[tool.ruff].extend-exclude`). The full stack stays mandatory — only file _scope_ is tunable. Loosening only; nothing previously-passing newly fails.
- **BREAKING (CLI consumers): `requires-python` raised `>=3.11` → `>=3.14`.** Installs via `uv tool install` now require Python 3.14+. The repo dogfoods its own Python Tooling baseline — `.python-version`, Ruff `target-version`, and BasedPyright `pythonVersion` all track 3.14.
- **BREAKING (Python Tooling standard, copy-adopted): default Python baseline raised 3.13 → 3.14.** `standards/python-tooling/` now scaffolds `requires-python = ">=3.14"`, `.python-version` `3.14`, Ruff `target-version = "py314"`, and BasedPyright `pythonVersion = "3.14"` (3.14 is the current stable CPython release). Per `meta/versioning.md`, raising the required Python is MAJOR for a consumer that re-syncs scaffolds; the `python_tooling` contract-version label stays `1.0` (metadata-only, unenforced).
- **BREAKING (docs layout): `standards/` restructured into one self-contained bundle per governing standard** — `standards/<name>/{README.md, adopt.md, templates/, examples/}`. The flat top-level `templates/` and `examples/` trees were dissolved into the bundles, and `versioning.md` moved to `meta/`. Added `standards/README.md` (index + bundle anatomy) and per-standard `adopt.md` entries. Doc deep-links change; the **consumer contract is unchanged** — reusable workflow names, the `validate-frontmatter` package + entry point, and the bundled schema path are identical.
- **`.markdownlint.json` now states every rule explicitly (53 rules), not just the 13 overrides.** A consuming repo that seeds its config from ours now gets deterministic linting that isn't shadowed by a contributor's personal editor/global markdownlint settings, and is pinned against default drift across markdownlint versions. Behaviour is identical to the previous sparse config in a clean environment (verified: the repo lints with zero errors either way, and the explicit config validates against the v0.40.0 config schema). One subtlety encoded: `MD043` stays `true` (inert) rather than its schema-declared `headings: []` default, which would otherwise demand zero headings (a `tests/test_markdownlint_config.py` guard pins that and the customisations). Because the explicit values track a markdownlint version, the `markdownlint-cli2-action@v23` pin is load-bearing — re-verify on upgrade.
- **ADR Standard — body structure now lists three required sections, not four.** `standards/adr/README.md` previously marked **Consequences** as a fourth required section; MADR 4.0 (and the repo's own templates and worked example) treat it as an _optional_ `### Consequences` sub-section of Decision Outcome. The required set is now the three MADR-required `##` sections, matching the new opt-in validator check. Prose-only correction — no document that previously passed can newly fail.
- **`.markdownlint.json` — `MD024` (no-duplicate-heading) now `false`**, matching MADR 4.0's own `template/.markdownlint.yml` (was `{ siblings_only: true }`). MADR ADRs repeat option headings across the _Considered Options_ and _Pros and Cons_ sections; disabling the rule mirrors upstream tooling exactly. Strictly looser than before, so no previously-passing document can newly fail — additive.
- **ADR Standard — corrected the MADR acronym expansion** from "Markdown _Any_ Decision Records" to "Markdown _Architectural_ Decision Records" in `standards/adr/README.md`. MADR 4.0 (2024-09-17) reverted the name to "Architectural"; the prior wording tracked the superseded MADR 3.x spelling.
- **ADR Standard — `id` now embeds the repo-name for cross-repo uniqueness.** ADR ids become `adr-NNNN-repo-name-short-title` (e.g. `adr-0001-homelab-use-postgresql-for-persistent-storage`) so that an ADR referenced from another repository's `related:` list stays globally unambiguous across a fleet of repos. The **filename** keeps the `adr-NNNN-short-title.md` form — `adr-` prefix, no repo-name — making ADRs the one documented case where filename and `id` differ, consistent with the standard's existing "`id` is independent of file path" rule. Templates show the `repo-name` slot plus a save-as comment; the worked example and its two inbound `related:` references were updated to match. Deliberately diverges from MADR's bare-number filenames (MADR tooling is an optional convenience here, not a conformance target). Greenfield (no consumer ADRs exist yet) and filenames are not schema-validated, so nothing can newly fail — additive.
- **ADR Standard promoted to the source-checked documentation tier.** `standards/adr/README.md` gains an Evidence convention, `[Sxx]` citations at the load-bearing MADR claims, a dated **Source register**, a Source coverage map, and a "Last source check" status banner — matching the Python/Markdown Tooling standards (previously it followed the narrative tier like the Frontmatter standard). MADR was re-verified against the live spec on 2026-06-07: **4.0.0 (2024-09-17) is the current release**, and the acronym, the three required + five optional sections, the status vocabulary, and the MADR→canonical field mappings all match. Also refreshed stale `updated`/`reviewed` dates on the ADR README and worked example to their true last-edit dates. Docs-only — no schema, validator, or consumer-contract change; additive.

### Fixed

- **CI — `astral-sh/setup-uv@v8` no longer resolves; SHA-pinned to `v8.2.0`.** As of setup-uv v8.0.0 (March 2026) Astral publishes **no** moving major/minor tag, so `@v8`/`@v8.0` return 404 (verified against the GitHub refs API on 2026-06-07; latest is v8.2.0). This broke three references: the **consumer-facing** reusable workflow `validate-markdown-frontmatter.yml` (any repo pinning it red-fails at the `setup-uv` step before validation runs), the repo's own `check.yml`, and the Python Tooling standard's §15 `check.yml` template. All now pin `astral-sh/setup-uv@fac544c07dec837d0ccb6301d7b5580bf5edae39 # v8.2.0` (full-version commit SHA + trailing version comment, per GitHub/Astral supply-chain hardening guidance; Dependabot bumps the SHA). Strictly a fix — a currently-failing run can only become passing — so it rides the locked `2.0.0`. **Consumers tracking a moving `@vN` tag receive the fix only once that tag is repointed at the next release.**
- **Internal-consistency audit cleanup (docs/metadata/test).** A multi-agent consistency sweep found no contract-surface defects but a set of self-non-conformance and drift nits, now fixed: refreshed stale frontmatter `updated` dates on 7 managed docs (`meta/versioning.md`, the Frontmatter README + adopt + 3 examples, the Python Tooling README — whose frontmatter date also disagreed with its in-body banner); added the missing `source`/`confidence`/`visibility`/`license` fields and corrected `consumer` to `mix` on the Python Tooling README for parity with the other standards; added the Markdown Tooling standard to `meta/versioning.md`'s `related:`; removed redundant id-as-alias entries (ADR, Markdown Tooling); documented that the schema's `id` pattern also permits `.`/`_`; completed the validator's exit-code-2 description (unknown version label + FM↔ADR incompatibility); pointed the markdownlint test's source comment at the Markdown Tooling standard and tightened its rule-count guard from `>= 50` to `== 53`; fixed the N01 source-register row and the `v1` tag's commit SHA in `deployed.md`; and refreshed the §15 template's uv-version example. Docs/test only — no schema, validator behaviour, or consumer-contract change.

## [1.2.0] — 2026-06-03

### Added

- **Standards Adoption & Compliance Procedure** — `standards/adoption.md`, a self-contained, agent-oriented runbook for adopting the standards in a consuming repository: the config and CI setup (pinning both the workflow `@v1` and the `standards-ref` so the schema does not float on `main`), the full frontmatter rules and controlled vocabularies, a worked example, and a compliance checklist. Pin `@v1`.

### Changed

- **Reusable workflow — `standards-ref` default `main` → `v1`.** A consumer who pins `uses: …@v1` but omits `standards-ref` previously installed the validator and bundled schema from `main`, silently floating their validation on unreleased changes. The default now tracks the major tag, so the workflow pin and the validator/schema pin stay aligned by default. Non-breaking: within a major, `main` only accumulates additive changes, so this can never newly-fail a previously-passing caller (MINOR per the previously-passing rule).
- **README consuming guide** — the example now sets `standards-ref: 'v1'` with a "pin both refs" note, no longer excludes `docs/adr/**` / `docs/decisions/**` (ADRs are managed documents and should validate), and uses a current `standards_version` example.
- **Versioning Standard** — reworded the reusable-workflow row of the classification table so a default change that _cannot_ fail a previously-passing caller is explicitly MINOR (not MAJOR), aligning the table with the governing previously-passing rule.
- **Markdown Frontmatter Standard** — corrected example values that still referenced the former "YAML Frontmatter Standard" name.

### Fixed

- **Validator no longer crashes on malformed YAML.** A syntactically broken frontmatter block now reports a clean validation error and exits `1` (instead of dumping an uncaught traceback), and a malformed `.project-standards.yml` returns the documented config-error exit `2`. A single downstream typo can no longer crash the tool.

## [1.1.0] — 2026-06-03

### Added

- **`consumer` frontmatter field** — new optional standard-profile field with controlled values `user | agent | mix | unknown`, recording a document's intended reader. Added to the JSON schema, the standard, templates, examples, and validator tests. Additive: documents that omit it stay valid, so this reaches `@v1` consumers automatically.
- **Project license** — added the Apache-2.0 `LICENSE` file and Python package metadata so GitHub and built wheels identify the project license consistently.

### Changed

- **Frontmatter schema version → `1.1`** — the `schema_version` enum now accepts `'1.1'` alongside `'1.0'`; this repository's standard, templates, and examples declare `schema_version: '1.1'`. Existing `'1.0'` documents remain valid (the enum keeps both), so the bump is non-breaking.
- **Markdown Frontmatter Standard promoted to V1.1** — `standards/markdown-frontmatter.md` gained dedicated sections (scalar value rules, list rules, canonical key order, description, tags, aliases, links) and a valid-frontmatter template; its Versioning and Validation sections were trimmed to point at `standards/versioning.md` and the README rather than restate them.
- **`visibility` description** — narrowed to "Exposure level" now that `consumer` owns the audience dimension. Enum values unchanged; no validation outcome changes.
- **Link form is now a documented convention** — `related`, `supersedes`, `superseded_by`, `depends_on`, and body links SHOULD use repo-root-relative paths (extension included). This is convention only in `1.1.0`, not schema-enforced; path-pattern enforcement is planned for a future `2.0.0`. No `1.1.0` validation behaviour changes.
- **Versioning Standard** — the moving-major-tag step now documents deleting and re-pushing the tag (`git push origin :refs/tags/vN` then `git push origin vN`) instead of `git push --force`. Identical end state, but it avoids the force flag blocked by the repository's `release-pipeline` force-push guard and cannot clobber branch history.

## [1.0.2] — 2026-06-02

### Added

- **Versioning Standard** — `standards/versioning.md` governs how this repository's releases are numbered, tagged, and consumed. Defines the consumer-outcome contract (a release's level reflects the worst-case impact across the standard, schema, validator, and workflow), the per-component MAJOR/MINOR/PATCH classification table, the "previously-passing → now-failing is always MAJOR" rule, and the release requirements (signed full-version tags, the moving major tag, version + changelog bumps). The README `## Versioning` section is now a summary linking to it.

### Changed

- **Repository owner** — transferred from `chrisdpurcell` to the `L3DigitalNet` organization. Updated every in-repo reference to the canonical owner: the reusable workflow's `github.repository` self-identity guards and `uv tool install` URL, the README and `standards/versioning.md` adoption examples, and the JSON Schema `$id`. Not a MAJOR change under the versioning standard — GitHub redirects the old path, so previously-passing consumers continue to pass — but consumers should re-pin `uses:` to `L3DigitalNet/project-standards` rather than rely on the redirect.

## [1.0.1] — 2026-06-02

### Changed

- **CI — reusable validation workflow** — bumped `actions/checkout` (v4 → v6) and `astral-sh/setup-uv` (v5 → v7) so both run on Node 24, clearing the GitHub Actions Node 20 deprecation warning. Scoped uv's dependency cache to this repo via `enable-cache`, since only this repo ships the `uv.lock` the cache keys on; consuming repos (which install the validator with `uv tool install` from git) no longer emit the "cache will never get invalidated" warning. Behaviour-only change to CI plumbing — the validator, schema, and standards are untouched, so `@v1` consumers receive it with no validation impact.
- **Docs** — recommend pinning the reusable workflow and CLI by major tag (`@v1`) for automatic non-breaking fixes; full version tags (`@v1.0.1`) and commit SHAs remain available for immutable pins.

## [1.0.0] — 2026-06-02

### Added

- **ADR Standard** — Architecture Decision Records using the [MADR](https://adr.github.io/madr/) format layered on the canonical frontmatter profile.
- `standards/adr.md` — the governing ADR standard: when to write an ADR, MADR body structure (required vs optional sections), the MADR→canonical field and status mappings, ID/filename and `docs/decisions/` directory conventions, and the supersession workflow.
- `templates/adr.md` (full, with explanations) plus `templates/adr-minimal.md`, `templates/adr-bare.md`, and `templates/adr-bare-minimal.md` MADR variants. Replaces the prior simple ADR template.
- `examples/adr.example.md` — converted to MADR structure (PostgreSQL decision), with ADR roles under the `project` namespace.

### Changed

- Clarified scope in `standards/markdown-frontmatter.md`: agent-instruction files (`CLAUDE.md`, `AGENTS.md`, `.claude/`, `.agents/`, `.codex/`) must never carry frontmatter. Updated the README downstream-example config to exclude them.

### Fixed

- Validator exclude patterns now match via `fnmatch` on the file path instead of `Path.glob`, making directory excludes (e.g. `docs/decisions/**`) behave identically across Python versions. Previously such patterns silently failed to exclude nested files on Python ≤3.12, where a trailing `**` matches directories only.

## [0.1.0] — 2026-06-02

### Added

- **Markdown Frontmatter Standard** — a small, portable, tool-neutral metadata profile for project documentation.
- `standards/markdown-frontmatter.md` — the governing standard: field definitions, controlled values, formatting rules, and extension policy.
- `schemas/markdown-frontmatter.schema.json` — machine-readable JSON Schema (Draft 2020-12); eleven required fields, enum-validated `doc_type`/`status`/`confidence`/`visibility`, `YYYY-MM-DD` date pattern, and `publish`/`project`/`x_project` extension namespaces.
- `templates/` — `frontmatter-minimal.yml`, `frontmatter-standard.yml`, and document templates for note, concept, ADR, runbook, spec, and research types.
- `examples/` — validated worked examples for note, concept, ADR, and runbook documents.
- `tools/validate_frontmatter.py` — CLI validator (files, globs, or config-driven), shipping the bundled schema in the wheel for downstream installs.
- `tests/test_validate_frontmatter.py` — 15 cases covering valid and invalid frontmatter plus config include/exclude behaviour.
- `.github/workflows/validate-markdown-frontmatter.yml` — CI enforcement, reusable via `workflow_call` from downstream repositories.
- `.project-standards.yml` — validator configuration for this repo and the canonical example of the downstream config shape.
