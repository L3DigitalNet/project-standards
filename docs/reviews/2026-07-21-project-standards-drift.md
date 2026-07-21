---
schema_version: '1.1'
id: 'reference-wboffl-project-standards-drift'
title: 'Project Standards Consumer Documentation Drift Audit'
description: 'Claim-level audit of consumer-facing documentation against the implementation at the reviewed commit.'
doc_type: 'reference'
status: 'active'
created: '2026-07-21'
updated: '2026-07-21'
reviewed: '2026-07-21'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'documentation'
  - 'review'
  - 'validation'
aliases: []
related:
  - 'README.md'
  - 'UPGRADING.md'
  - 'docs/usage.md'
source: []
confidence: 'high'
visibility: 'internal'
license: null
---

# Project Standards Consumer Documentation Drift Audit

## Header

| Field | Value |
| --- | --- |
| Project | Project Standards 5.3.0 candidate |
| Repository | `/home/chris/projects/project-standards` |
| Reviewed commit | `88a6f88b241473ced90d35af20b653ed992de915` |
| Reviewer | Codex (GPT-5), high effort; three-agent audit swarm plus fresh-context verifier |
| Review date | 2026-07-21 |
| Baseline worktree | Pre-existing dirty tree: 80 modified tracked files and 214 untracked paths; baseline status hash `fbacb1f741dd3b6b77ed88acb9a02a9876998ed3297d7bfae6f19d71d7051e2a`. |
| Verification | 17 documentation findings and 3 implementation bugs after verifier pass; 2 candidate clusters were pruned and 1 finding was downgraded. |

## Executive Summary

The documentation is broadly accurate at the command and package-contract level, but its release and current-package navigation are materially out of sync with the reviewed commit. The highest-impact gap advertises the nonexistent `v5.3.0` tag as an installable immutable release, while the repository records 5.2.0 as published. Mutable adoption guides also lag three Catalog 5 defaults and omit their new ownership controls; migration, verification, and schema-generation references contain narrower discrepancies. The reverse pass additionally found three implementation bugs that should be fixed in code rather than normalized in documentation.

| Severity | Contradiction | Stale | Omission | Underspecified | Aspirational | Total |
| --- | --: | --: | --: | --: | --: | --: |
| Critical | 0 | 0 | 0 | 0 | 0 | 0 |
| High | 0 | 0 | 0 | 0 | 1 | 1 |
| Medium | 3 | 4 | 4 | 0 | 0 | 11 |
| Low | 2 | 2 | 1 | 0 | 0 | 5 |
| **Total** | **5** | **6** | **5** | **0** | **1** | **17** |

## Coverage Ledger

The audit inventory contains 608 tracked Markdown paths. Canonical package sources are reviewed directly; installed family/payload projections are checked for symlink parity and then accounted for through the opened canonical source. Internal maintainer material that an external package author could reasonably follow is included conservatively.

| Consumer-facing document or group | Depth | Notable gaps |
| --- | --- | --- |
| `README.md` | Deep | Release-state and six current-version links are stale. |
| `UPGRADING.md`, `CHANGELOG.md`, `meta/versioning.md` | Deep | Release status, fallback wording, and migration-code coverage drift. |
| `docs/usage.md`, `docs/adoption-prompt.md` | Deep | Usage has version, lifecycle, and schema-count drift; the adoption prompt's preserve semantics were observed and verified accurate. |
| `docs/workflows/*.md`, `scripts/README.md`, `src/project_standards/README.md` | Deep | Included conservatively as public integrator/maintainer guidance; two stale authority pointers found. |
| Installed help for 7 console entry points and all root/leaf command groups | Deep | Exact-commit wheel exercised; all public command groups and parser surfaces reverse-scanned. |
| `standards/adr/**` (24 Markdown files) | Deep/Scanned | Canonical docs deep-read; templates/examples scanned; no surviving drift. |
| `standards/agent-handoff/**` (60 Markdown files) | Deep/Scanned | Canonical docs and consumer skill deep-read; projections scanned; no surviving drift. |
| `standards/cli-documentation/**` (28 Markdown files) | Deep/Scanned | Mutable guide is stale; fresh composition exposed one implementation bug. |
| `standards/markdown-frontmatter/**` (52 Markdown files) | Deep/Scanned | Canonical docs, schema, skill, and templates checked; no documentation finding survived. |
| `standards/markdown-tooling/**` (15 Markdown files) | Deep/Scanned | Mutable guide and immutable migration/verification wording drift. |
| `standards/project-spec/**` (24 Markdown files) | Deep/Scanned | Source-check and upgrade guidance drift; conditional deletion is an implementation bug. |
| `standards/python-coding/**` (6 Markdown files) | Deep/Scanned | Reference-only but externally readable; no package-local drift beyond global version navigation. |
| `standards/python-tooling/**` (20 Markdown files) | Deep/Scanned | Mutable guide and immutable migration/release-status wording drift. |
| `standards/standard-bundle-authoring/**` (10 Markdown files) | Deep/Scanned | Internal package-author surface included conservatively; verification command omission found. |
| `standards/README.md`, `standards/catalog.md` | Deep | Index version table is stale; generated catalog matches Catalog 5. |
| `src/project_standards/bundles/**` (19 legacy-bundle Markdown files) | Scanned | Frozen V1 compatibility evidence; no current-authority finding. |
| `src/project_standards/families/**` (9 installed family indexes) | Scanned | Relative-symlink projections; canonical targets reviewed above. |
| `src/project_standards/payloads/**` (175 installed payload Markdown symlinks) | Scanned | Canonical payloads reviewed; `sync-payload-projection --check` passed. |
| `.standards/packages/markdown-frontmatter/agent-summary.md`, `.agents/skills/{agent-handoff,markdown-frontmatter}/SKILL.md` | Deep | Installed consumer-facing dogfood outputs match their selected payloads. |

The reverse code-to-documentation pass covered CLI parsers and observed help, all public console entry points, selected and retained package schemas/providers, user-visible diagnostics, all reusable-workflow inputs, pre-commit hooks, and package projections. No public Python SDK contract exists beyond the CLI. Internal status, handoff, plans, research, prior reviews, future-standard drafts, agent instructions, and test fixtures were classified as non-consumer product documentation; they were opened only when needed as implementation or release-state evidence.

## Severity and Drift-type Rubric

Severity follows the consumer-impact bar:

- **Critical:** documentation actively leads a consumer into a broken or destructive action, such as data loss or an incorrect security step.
- **High:** documented behavior contradicts actual behavior on a common path, such as a wrong flag, default, or exit code.
- **Medium:** stale or omitted behavior has a workaround or a narrow trigger.
- **Low:** a minor wording problem, example defect, or cosmetic omission that still creates real drift.

Confidence is **High**, **Medium**, or **Low** according to whether the discrepancy is real and correctly attributed to documentation rather than implementation.

Drift types are:

- **Contradiction:** documentation says one thing and implementation does another.
- **Stale:** documentation describes removed or changed behavior.
- **Omission:** real consumer behavior is undocumented.
- **Underspecified:** documentation implies behavior but leaves it ambiguous.
- **Aspirational:** documentation describes behavior that is not implemented.

## Findings

### D-001 — Stop advertising the unpublished 5.3.0 candidate as an installable release

- **Drift type:** Aspirational · **Severity:** High · **Confidence:** High
- **Doc location** (`README.md:134-141,175-177,219-228`): “Install the exact release from its immutable Git tag”; `@v5.3.0`; “must report `project-standards 5.3.0`”; and `rev: v5.3.0`. `CHANGELOG.md:38-40` contains both `## [Unreleased]` and `## [5.3.0] — 2026-07-20`. `meta/versioning.md:53` says “Project Standards 5.1.1 is published”.
- **Code location** (`docs/STATUS.md:5-6`): “Project Standards 5.2.0 is the current published release at `4d2cc41`” and “An unreleased 5.3.0 candidate on `testing`”. `pyproject.toml:1-3` contains `version = "5.3.0"`, which is candidate package metadata, while `meta/versioning.md:135-161` requires a release to have a full-version tag and changelog promotion. The exact Git probe produced no `v5.3.0` tag; `v5` and `v5.2.0` both resolve to `4d2cc414b4296b0cd6c7513fdc3f3bf5cc4ead7f`.
- **Discrepancy:** consumer docs turn candidate metadata into a nonexistent immutable installation target. A new consumer who copies the command or pre-commit revision cannot resolve the advertised tag.
- **Fix:** in `README.md:134-141`, state that 5.3.0 is an unreleased candidate and that the current published release is 5.2.0; change the install URL and expected version to `v5.2.0` and `project-standards 5.2.0`. Change the full-version examples at `README.md:177,226` to `v5.2.0`. In `CHANGELOG.md`, move the 5.3.0 entries back under `## [Unreleased]` and remove the dated 5.3.0 heading until release. In `meta/versioning.md:53`, replace the 5.1.1 publication sentence with “Project Standards 5.2.0 is published from release commit `4d2cc414b4296b0cd6c7513fdc3f3bf5cc4ead7f`; the moving `v5` tag tracks it.”
- **Verification:** `git tag --list v5.3.0` remains empty, `git rev-parse v5^{commit}` equals `git rev-parse v5.2.0^{commit}`, and every installable full-version example names `v5.2.0` until 5.3.0 is actually released.
- **Dependencies:** none · **Effort:** M

### D-002 — Synchronize current-package navigation with Catalog 5

- **Drift type:** Stale · **Severity:** Medium · **Confidence:** High
- **Doc location** (`README.md:58-130`): “with current authority in the exact versioned payload linked below”, followed by links naming ADR `1.1`, Python Tooling `1.1`, Markdown Tooling `1.2`, CLI Documentation `1.2`, Python Coding `0.5`, and Standard Bundle Authoring `2.2`. `standards/README.md:13-19` likewise lists Python Tooling `1.2`, Markdown Tooling `1.3`, CLI Documentation `1.2`, and Standard Bundle Authoring `2.2`. Additional stale pointers occur at `docs/usage.md:19-20,833-835`, `scripts/README.md:23-29`, and `src/project_standards/README.md:345-347`.
- **Code location** (`catalogs/5.toml:10-14,40-44,70-80,100-104,124-128,148-152`): the current entries pair `version = "1.2"` / `role = "default"` for ADR, `1.3` for CLI Documentation, `1.5` for Markdown Tooling, `1.4` for Python Tooling, and `version = "0.6"` / `role = "reference-only"` plus `version = "2.3"` / `role = "internal"` for the other two packages.
- **Discrepancy:** landing pages that claim to route to exact current authority send consumers to retained payloads, obscuring current options and fixes.
- **Fix:** update the six root `README.md` package/version links and adjacent labels to ADR 1.2, Python Tooling 1.4, Markdown Tooling 1.5, CLI Documentation 1.3, Python Coding 0.6, and Standard Bundle Authoring 2.3. Update the four stale rows in `standards/README.md`. Change both CLI Documentation links in `docs/usage.md` to 1.3, the Python Tooling resource pointer in `scripts/README.md` to 1.4, and the Standard Bundle Authoring workflow pointer in `src/project_standards/README.md` to 2.3.
- **Verification:** compare every corrected version to `catalogs/5.toml`; run `project-standards standards render-catalog --root . --check` and search the corrected files for the superseded version strings.
- **Dependencies:** none · **Effort:** M

### D-003 — Update the CLI Documentation family guide for package 1.3

- **Drift type:** Stale · **Severity:** Medium · **Confidence:** High
- **Doc location** (`standards/cli-documentation/adopt.md:1-15,34`): “The current consumer package is `cli-documentation@1.2`”, enables `--version 1.2`, and routes to `versions/1.2/adopt.md`.
- **Code location** (`catalogs/5.toml:40-44`; `standards/cli-documentation/versions/1.3/config.schema.json:12-16`): Catalog 5 says `version = "1.3"` and `role = "default"`; the option schema says `"enum": ["referenced", "consumer-owned"]` and `"default": "referenced"`.
- **Discrepancy:** the mutable guide directs adopters to a retained payload and never explains how a customized legacy workflow can be preserved.
- **Fix:** change all package and guide references in `standards/cli-documentation/adopt.md` from 1.2 to 1.3. In the configuration paragraph, add: “`workflow_ownership = "referenced"` verifies and locks the reviewed workflow; `"consumer-owned"` preserves a customized legacy workflow without a reference or CI enablement.” Mirror the exact migration behavior from `versions/1.3/adopt.md:61-63`.
- **Verification:** re-read `versions/1.3/config.schema.json:12-16` and `versions/1.3/adopt.md:61-63`; confirm the mutable guide enables and links 1.3.
- **Dependencies:** none · **Effort:** M

### D-004 — Update the Markdown Tooling family guide for package 1.5

- **Drift type:** Stale · **Severity:** Medium · **Confidence:** High
- **Doc location** (`standards/markdown-tooling/adopt.md:1-13,26-32`): “The current consumer package is `markdown-tooling@1.3`”, enables 1.3, and says the package owns both workflow files without an ownership qualification.
- **Code location** (`catalogs/5.toml:70-80`; `standards/markdown-tooling/versions/1.5/config.schema.json:6-15`): Catalog 5 says `version = "1.5"` and `role = "default"`; both ownership options use `"enum": ["managed", "consumer-owned"]` and `"default": "managed"`.
- **Discrepancy:** adopters miss both the current package and the supported per-caller relinquishment path.
- **Fix:** change package references and commands in `standards/markdown-tooling/adopt.md` from 1.3 to 1.5. Add both ownership options to the option paragraph and state: “Each caller is managed by default; set its matching ownership option to `"consumer-owned"` to leave that caller outside reconciliation, verification, and lock state.” Change the final version-specific link to `versions/1.5/adopt.md`.
- **Verification:** compare the guide with `versions/1.5/config.schema.json:6-15` and run `project-standards standards show markdown-tooling --json` in an initialized Catalog 5 consumer.
- **Dependencies:** none · **Effort:** M

### D-005 — Update the Python Tooling family guide for package 1.4

- **Drift type:** Stale · **Severity:** Medium · **Confidence:** High
- **Doc location** (`standards/python-tooling/adopt.md:1-17,40`): “The current consumer package is `python-tooling@1.2`”, enables 1.2, and lists `workflow_ownership` but not script ownership.
- **Code location** (`catalogs/5.toml:124-128`; `standards/python-tooling/versions/1.4/config.schema.json:115-119`): Catalog 5 says `version = "1.4"` and `role = "default"`; both ownership options use `"enum": ["managed", "consumer-owned"]` and `"default": "managed"`.
- **Discrepancy:** the current guide omits the supported way to preserve a customized `scripts/check.py` and points consumers to an older payload.
- **Fix:** change all 1.2 package and guide references in `standards/python-tooling/adopt.md` to 1.4. Add `script_ownership` to the options paragraph and state that `"consumer-owned"` leaves `scripts/check.py` outside reconciliation, verification, and lock state. In migration guidance, distinguish the matching script and workflow ownership decisions as `versions/1.4/adopt.md:82` does.
- **Verification:** re-read `versions/1.4/config.schema.json:115-119` and `versions/1.4/adopt.md:58,82`; confirm the mutable guide enables and links 1.4.
- **Dependencies:** none · **Effort:** M

### D-006 — Add a mutable erratum for Markdown Tooling caller relinquishment

- **Drift type:** Contradiction · **Severity:** Medium · **Confidence:** High
- **Doc location** (`standards/markdown-tooling/versions/1.5/README.md:145-151`): “A modified config or caller workflow remains blocking until its known content is restored.”
- **Code location** (`standards/markdown-tooling/versions/1.5/providers/markdown_tooling.py:420-442`): a relinquished unknown caller is claimed with `"ownership": "consumer-owned"`, `"disposition": "preserve"`, and an `intent_pointer`.
- **Discrepancy:** the immutable standard makes restoration sound mandatory even though package 1.5 deliberately preserves a modified caller after the matching ownership option is selected.
- **Fix:** do not edit immutable 1.5 bytes. Add a “Released-version errata” section to `standards/markdown-tooling/README.md`: “In the immutable 1.5 README, ‘a modified … caller workflow remains blocking’ applies only while its matching ownership option remains `managed`. Setting `lint_workflow_ownership` or `format_workflow_ownership` to `"consumer-owned"` preserves that customized caller and leaves it outside reconciliation, verification, and lock state. Modified managed config still blocks.”
- **Verification:** re-read `versions/1.5/providers/markdown_tooling.py:420-442` and confirm the mutable erratum distinguishes config from relinquished caller behavior.
- **Dependencies:** D-004 · **Effort:** S

### D-007 — Add a mutable erratum for Python Tooling script relinquishment

- **Drift type:** Contradiction · **Severity:** Medium · **Confidence:** High
- **Doc location** (`standards/python-tooling/versions/1.4/README.md:57-65`): “Modified `scripts/check.py`, `.python-version`, or a modified managed workflow remains blocking.”
- **Code location** (`standards/python-tooling/versions/1.4/providers/python_tooling.py:673-719`): `script_ownership == "consumer-owned"` binds `legacy-check-script`; an unknown matching script becomes consumer-owned with disposition `preserve`.
- **Discrepancy:** the immutable README omits the explicit exception introduced by its own package version, so a consumer may unnecessarily discard a customized enforcement script.
- **Fix:** do not edit immutable 1.4 bytes. Add a “Released-version errata” section to `standards/python-tooling/README.md`: “In the immutable 1.4 README, the statement that a modified `scripts/check.py` remains blocking applies only while `script_ownership = "managed"`. Setting `script_ownership = "consumer-owned"` preserves the customized script and leaves it outside reconciliation, verification, and lock state. `.python-version` and modified managed outputs retain the stated blocking behavior.”
- **Verification:** re-read `versions/1.4/providers/python_tooling.py:673-719` and confirm the mutable erratum describes the two script ownership modes.
- **Dependencies:** D-005 · **Effort:** S

### D-008 — Extend the Python Tooling release-status correction to all affected payloads

- **Drift type:** Stale · **Severity:** Low · **Confidence:** High
- **Doc location** (`standards/python-tooling/README.md:29-31`): “The immutable 1.1 README contains wording written before the atomic Catalog 5 and Project Standards v5.0.0 release.”
- **Code location** (`standards/python-tooling/versions/1.1/README.md:63`; `standards/python-tooling/versions/1.2/README.md:63`; `standards/python-tooling/versions/1.3/README.md:65`; `standards/python-tooling/versions/1.4/README.md:65`): every payload says, “The V1 root family manifest remains authoritative in this source checkout until the atomic v5 release commit.”
- **Discrepancy:** the mutable correction names only 1.1 although the same stale release-time sentence remains in 1.2 through 1.4.
- **Fix:** in `standards/python-tooling/README.md:29-31`, replace “The immutable 1.1 README” with “The immutable 1.1, 1.2, 1.3, and 1.4 READMEs” and replace the final singular “1.1 payload bytes” with “payload bytes”.
- **Verification:** search all four versioned READMEs for `V1 root family manifest remains authoritative` and confirm the mutable correction names all four.
- **Dependencies:** D-005 · **Effort:** S

### D-009 — Make Markdown Tooling verification option-aware

- **Drift type:** Omission · **Severity:** Medium · **Confidence:** High
- **Doc location** (`standards/markdown-tooling/versions/1.5/adopt.md:52-58`): verification unconditionally runs `markdownlint-cli2 '**/*.md'` and `prettier --check .`.
- **Code location** (`standards/markdown-tooling/versions/1.5/config.schema.json:16-70`; `standards/markdown-tooling/versions/1.5/README.md:87`): `"lint"` and `"format"` are Boolean options; `markdown_globs` defaults to `["**/*.md"]`; `config_globs` defaults to JSON/JSONC/YAML patterns; exclusions carry `glob`, `applies_to`, and `reason`. The README says, “Exclusions that apply to lint are serialized as negative globs” and “A false enforcement flag skips the whole job”.
- **Discrepancy:** the guide's commands can check files outside the selected contract, ignore configured exclusions, invoke a disabled tool, and fail when a consumer relies on the action's bundled Node runtime rather than local Node dependencies.
- **Fix:** after `project-standards reconcile --check` in `versions/1.5/adopt.md`, make local commands conditional: run markdownlint only when `lint = true`, with every selected `markdown_glob` plus lint/both exclusions as negative globs; run Prettier only when `format = true`, over the selected Markdown and config globs while honoring format/both exclusions. Add: “These local commands require the corresponding packages to be installed; the managed reusable lint caller supplies its own action runtime. The reconciled workflow is the canonical option-aware CI verification.” Mirror the same qualification in mutable `standards/markdown-tooling/adopt.md`.
- **Verification:** reconcile one non-default config with a disabled tool, custom globs, and both exclusion types; confirm the documented local invocation matches the rendered caller and does not run the disabled tool.
- **Dependencies:** D-004 · **Effort:** M

### D-010 — Qualify the legacy fallback as read-only authority, not read-only behavior

- **Drift type:** Contradiction · **Severity:** Medium · **Confidence:** High
- **Doc location** (`UPGRADING.md:23-27`): “The v5 tool keeps a warned read-only fallback for a repository that still has only `.project-standards.yml`.”
- **Code location** (`src/project_standards/cli.py:470-549`): when unified `fix` resolution returns no result, the fallback loads legacy configuration, creates an authoring plan, calls `apply_authoring_plan`, and then validates. `src/project_standards/README.md:340-343` states that legacy YAML is a “read-only authority input, while explicitly mutating fallback commands retain their documented writes.”
- **Discrepancy:** “read-only fallback” implies no compatibility command writes, but `fix` and other explicitly mutating fallback commands can write. Consumers may make an unsafe assumption about a migration checkout.
- **Fix:** replace the sentence in `UPGRADING.md:27` with: “The v5 tool keeps a warned fallback for a repository that still has only `.project-standards.yml`. The YAML is a read-only authority input: v5 never rewrites it or merges YAML and TOML authority, but explicitly mutating compatibility commands such as `fix` retain their documented repository writes.”
- **Verification:** re-read `src/project_standards/cli.py:470-549` and confirm the revised sentence distinguishes authority mutation from command output mutation.
- **Dependencies:** none · **Effort:** S

### D-011 — Cover every migration finding promised by the upgrade guide

- **Drift type:** Omission · **Severity:** Medium · **Confidence:** High
- **Doc location** (`docs/usage.md:125-135`): “`UPGRADING.md` documents each preview finding and its resolution.” `UPGRADING.md:66-75` lists only the common platform-version, unclaimed-setting, digest/package-modified, bounded-takeover, owner-resolution, and consumer-conflict findings.
- **Code location** (`src/project_standards/control_plane/migration.py:721-731,895-921,981-992,1151-1159,1411-1422,1559-1573`): the engine also emits `CP-MIGRATION-LEGACY-BLOCK`, `CP-MIGRATION-SETTING-MISSING`, `CP-MIGRATION-SETTING-OVERLAP`, `CP-MIGRATION-CLAIM-OVERLAP`, `CP-MIGRATION-UNCLAIMED-ARTIFACT`, `CP-MIGRATION-BOUNDED-ORPHAN`, and `CP-MIGRATION-CONFIG`. Representative exact guidance is `message="legacy bounded content is ambiguous"` with `hint="restore a known managed block or remove the partial markers"`.
- **Discrepancy:** operators following the promise encounter undocumented blocking codes and must inspect source to determine the prescribed correction.
- **Fix:** change `docs/usage.md:131` to “UPGRADING.md documents common preview findings and their resolutions; for any other code, follow the emitted path, identity, and hint.” Add seven rows to `UPGRADING.md` using the engine's exact guidance: restore a known block or remove partial markers; update the provider declaration or legacy configuration; make setting claims disjoint; make package claims disjoint; make the selected provider claim or preserve the artifact; add a replacement that preserves content outside the managed block; and correct legacy values or provider mapping.
- **Verification:** enumerate `_finding("CP-MIGRATION-..."` calls in `migration.py` and confirm each code is either in the table or covered by the revised emitted-hint rule.
- **Dependencies:** none · **Effort:** M

### D-012 — Document reconciliation after frontmatter fixes

- **Drift type:** Omission · **Severity:** Medium · **Confidence:** High
- **Doc location** (`docs/usage.md:54-57`): “`fix` applies only the provider's typed plan through the platform executor and then revalidates.” It does not say that changed consumer-owned document bytes can make the central lock stale.
- **Code location** (`src/project_standards/control_plane/cli.py:255-259,730-737`): reconciliation drift includes `plan.next_lock != previous_lock`, and validation emits `CP-DRIFT` when the lock needs refresh. An exact-wheel probe ran `project-standards fix`, then `validate --quiet`; fix exited 0 but validation emitted `CP-DRIFT: unified standards state requires reconciliation` and exited 1.
- **Discrepancy:** a consumer can follow the documented repair command successfully and immediately fail the documented validation gate because referenced-input digests were not reconciled.
- **Fix:** after the `fix` lifecycle paragraph in `docs/usage.md`, add: “After `project-standards fix`, run `project-standards reconcile --check`, review the digest-only plan, and run `project-standards reconcile --apply` before the final `project-standards validate`.” Add the same sequence to the `fix` command's verification example.
- **Verification:** in a unified consumer with a referenced Markdown input, run the documented four-command sequence and confirm final `project-standards validate` exits 0.
- **Dependencies:** none · **Effort:** S

### D-013 — Complete the Standard Bundle Authoring verification command set

- **Drift type:** Omission · **Severity:** Medium · **Confidence:** High
- **Doc location** (`standards/standard-bundle-authoring/versions/2.3/README.md:100-122`): “Prove source-tree, graph, projection, installed-wheel, migration, and compatibility behavior”, but the printed command block omits `validate-graph` and `render-catalog --check`.
- **Code location** (`.github/workflows/validate-standards-graph.yml:33-46`): the repository gate runs `uv run project-standards standards validate-graph --root . --require-all-manifests` and `uv run project-standards standards render-catalog --root . --check` in addition to the three commands printed by the standard.
- **Discrepancy:** a literal package author can run every command printed by the standard and still miss relationship/catalog drift that the actual gate rejects.
- **Fix:** preserve immutable 2.3 bytes. Add a “Released-version errata” section to `standards/standard-bundle-authoring/README.md` with the complete current command block, inserting `uv run project-standards standards validate-graph --root . --require-all-manifests` after `validate-packages` and `uv run project-standards standards render-catalog --root . --check` after projection sync. State that all commands are required before the release check.
- **Verification:** compare the erratum block line-for-line with `.github/workflows/validate-standards-graph.yml:33-46`; run all five package/graph/schema/projection/catalog commands.
- **Dependencies:** none · **Effort:** M

### D-014 — Correct generated schema counts

- **Drift type:** Contradiction · **Severity:** Low · **Confidence:** High
- **Doc location** (`docs/usage.md:425-439`): “three package-contract and six control-plane JSON Schemas”, “all nine checked-in schemas”, and “any of the nine generated schemas”.
- **Code location** (`src/project_standards/package_contract/schemas.py:24-28`; `src/project_standards/control_plane/schemas.py:159-167`): the registries contain three package-contract models and seven control-plane models, ten total.
- **Discrepancy:** the reference undercounts the generated control-plane and total schema surface, confusing maintainers who verify generated outputs.
- **Fix:** in `docs/usage.md:427,436,439`, change “six” to “seven” and both occurrences of “nine” to “ten”.
- **Verification:** count `_SCHEMA_MODELS` entries in both cited modules and run `project-standards standards generate-package-schemas --root . --check`.
- **Dependencies:** none · **Effort:** S

### D-015 — Replace the retired housekeeping configuration relation

- **Drift type:** Stale · **Severity:** Low · **Confidence:** High
- **Doc location** (`docs/workflows/housekeeping.md:17-20`): frontmatter `related` lists `.project-standards.yml`.
- **Code location** (`src/project_standards/control_plane/state.py:24`; `src/project_standards/README.md:340-343`): legacy YAML is the `LEGACY_ONLY` compatibility state; current unified authority uses `.standards/config.toml`, catalog, and lock.
- **Discrepancy:** current housekeeping guidance links readers to the retired V4 authority file.
- **Fix:** replace `.project-standards.yml` with `.standards/config.toml` in `docs/workflows/housekeeping.md:18`.
- **Verification:** run `project-standards validate docs/workflows/housekeeping.md` and confirm the related path exists in a unified checkout.
- **Dependencies:** none · **Effort:** S

### D-016 — Record the completed Project Spec source check

- **Drift type:** Contradiction · **Severity:** Low · **Confidence:** High
- **Doc location** (`standards/project-spec/versions/1.2/README.md:3-9`): “Last source check: _TBD_”.
- **Code location** (`standards/project-spec/versions/1.2/README.md:227-240`): every source-register row says `2026-07-04`, followed by “All four editions were confirmed current on 2026-07-04.”
- **Discrepancy:** the header says verification is pending while the same immutable document records a completed check.
- **Fix:** preserve immutable 1.2 bytes. Add a “Released-version errata” section to `standards/project-spec/README.md`: “The immutable 1.2 README's `Last source check: TBD` header is stale; its source register records the completed check on 2026-07-04.”
- **Verification:** re-read the four `Last checked` cells and the verification note at `versions/1.2/README.md:231-240`.
- **Dependencies:** none · **Effort:** S

### D-017 — Prefer the guarded spec-upgrade command in templates

- **Drift type:** Omission · **Severity:** Low · **Confidence:** Medium
- **Doc location** (`standards/project-spec/templates/spec-light-template.md:21-25`; `standards/project-spec/templates/spec-standard-template.md:21-25`; `standards/project-spec/templates/spec-full-template.md:928-945`): “copy your content into the next template up”; “copy your content into that template”; and “copy your filled-in sections into the larger template and update `profile:` in the frontmatter.”
- **Code location** (`src/project_standards/specs/cli.py:451-460`; `docs/usage.md:585-604`): `project-standards spec upgrade <src> --to {standard | full}` provides stdout, output, or in-place modes, gates on a clean source, and self-validates the result.
- **Discrepancy:** the most prominent upgrade instructions omit the safer supported command and imply manual copy-up is the normal path.
- **Fix:** in all three mutable templates, make `project-standards spec upgrade <src> --to <profile> --stdout` the preview step and document `--output` or `--in-place` for the reviewed write. Retain manual copying only as a fallback for a spec the command refuses, followed by `project-standards spec validate` and `project-standards spec lint`.
- **Verification:** search the three mutable templates for `spec upgrade`; run the documented preview on the Light example and validate/lint the result.
- **Dependencies:** none · **Effort:** M

## Remediation Plan

1. **Published-release safety:** D-001.
2. **Current authority and adoption routing:** D-002, D-003, D-004, D-005.
3. **Ownership, migration, and verification correctness:** D-006, D-007, D-008, D-009, D-010, D-011, D-012, D-013.
4. **Low-impact reference corrections:** D-014, D-015, D-016, D-017.

## Bugs Found

### B-001 — Conditional Project Spec section deletion is rejected

- **Documentation/intended behavior:** `standards/project-spec/versions/1.2/README.md:167-175` says deleting a conditional section with an annotated reason is “Tooling-safe by construction” and that templates and validator accept it. The Full template repeats the one-line-reason rule at `versions/1.2/templates/spec-full-template.md:21-25,928-930`.
- **Observed implementation:** `src/project_standards/specs/commands/validate.py:96-108` recognizes an omitted section only when a blockquote line contains the literal words `tier` and `omitted` plus a recognized section number. Deleting §11 with a plain annotated reason produces `SV-GAP`; retaining the heading and a one-line N/A reason passes.
- **Disposition:** treat this as an implementation defect. Implement the documented conditional-omission contract in the validator, or make a separately approved normative change; do not document the current false rejection as intended behavior.

### B-002 — Human `standards list` output omits promised catalog and applied facts

- **Documentation/intended behavior:** `docs/usage.md:315-325` says `standards list` lists “the complete committed catalog with desired and applied summaries”.
- **Observed implementation:** `src/project_standards/standards_graph/cli.py:136-144` prints only the ID, enabled marker, and requested version. `src/project_standards/control_plane/config_edit.py:270-299` computes status, selectable, available, default, candidate, requested, resolved, and configuration facts, and JSON output exposes them.
- **Disposition:** treat the text-mode omission as an implementation defect because the documented richer inspection surface is already computed and returned by JSON. Do not narrow the reference to match the incomplete human output.

### B-003 — Fresh CLI Documentation and Frontmatter defaults compose into an invalid repository

- **Documentation/intended behavior:** `standards/cli-documentation/versions/1.3/adopt.md:61-65` says packages remain independently selectable. The CLI Documentation payload creates `docs/usage.md` from its template (`payload.toml:111-116`), while the template begins directly with `# toolname` (`templates/usage-doc.md:1-5`).
- **Observed implementation:** Markdown Frontmatter 1.3 defaults `required = true` and includes `docs/**/*.md` (`standards/markdown-frontmatter/versions/1.3/config.schema.json:22-28`). In an exact-commit wheel probe, enabling both default packages and applying reconciliation created the headerless usage document; immediate `project-standards validate` failed with `docs/usage.md: frontmatter is required`.
- **Disposition:** treat this as a package-composition implementation defect. Make the create-only CLI template satisfy the selected Frontmatter contract or make composition negotiate the requirement; do not tell consumers that independently selectable packages require a manual undocumented repair.

## Open Questions

None.

## Bug remediation outcome

Recorded 2026-07-21 after a verification session against `testing` HEAD. The 17 documentation findings (D-001 through D-017) remain queued; this section closes only the three implementation bugs.

| Bug | Outcome |
| --- | --- |
| B-001 | Fixed. `spec validate` now implements the documented conditional-omission contract: the gap recognizer accepts a blockquote that names the deleted section and carries an omission marker (`omitted`, `omission`, `does not apply`, or `not applicable`), instead of requiring tier-note wording. A marker is still required so template preambles that name section numbers cannot cover real gaps, and the `SV-GAP` message now states the accepted annotation shape. Covered by the `valid_standard_conditional_omission.md` fixture and marker/guard tests in `tests/test_spec_validate.py`. |
| B-002 | Verified already fixed at the reviewed commit's successor `778c29a`. The `standards list` text view prints availability, advertised versions, the default, the desired selector, and the applied version, matching the revised `docs/usage.md` reference; `tests/control_plane/test_config_edit.py` asserts the enriched line format. |
| B-003 | Verified already fixed at `778c29a`. The CLI Documentation 1.3 usage-document template now carries schema-valid frontmatter, and a fresh Catalog 5 consumer enabling CLI Documentation and Markdown Frontmatter defaults reconciles and immediately validates cleanly (re-probed against the rebuilt candidate wheel). `tests/package_contract/test_cli_documentation_reconstruction.py` validates the template against the Markdown Frontmatter 1.4 schema. |
