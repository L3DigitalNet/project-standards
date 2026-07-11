# Consumer Standards Control Plane Package Migration and Release-Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Approved and in progress. The scratch-path convergence audit passed with no significant findings; owner approval followed on 2026-07-11. Tasks 1-2 are complete on `feature/v5-package-migration`.

**Goal:** Complete SPEC-CP01 MS-4 and the pre-release portion of MS-5 by reconstructing every current standard as an immutable V2 payload, migrating legacy consumers safely, activating catalog 5 in the distribution, proving the release-cut dogfood migration, and producing release-ready v5 evidence.

**Architecture:** Extend the generic control-plane core with one typed legacy-migration boundary and same-major catalog refresh. Reconstruct the nine current package families under `standards/*/versions/*`, project those bytes into the installed distribution, and activate them only after individual, pairwise, full-set, legacy, and offline-wheel gates pass. Package-specific behavior stays in versioned payload declarations and providers; shared control-plane code must not branch on package IDs.

**Tech Stack:** Python 3.14, Pydantic 2, JSON Schema Draft 2020-12, stdlib `tomllib`/`json`/`hashlib`/`fcntl`/`importlib.resources`/`pathlib`, PyYAML for bounded legacy parsing, argparse, pytest + coverage, BasedPyright strict, Ruff, `uv_build`, markdownlint, Prettier.

---

## Source of Truth

- `docs/superpowers/specs/2026-07-10-consumer-standards-control-plane-spec.md` (SPEC-CP01 rev 0.6), especially §§7–12, §17, §19 MS-4–MS-5, and Appendix B.
- `docs/superpowers/specs/2026-07-10-standard-bundle-authoring-v2-spec.md` (SPEC-BA02 rev 0.6), especially FR-024–FR-034 and §§10, 17, and 18.7.
- `docs/superpowers/specs/2026-07-10-root-artifact-ownership-semantic-composition-design.md`.
- `docs/adr/adr-0023-unified-consumer-standards-control-plane.md`.
- `docs/adr/adr-0024-catalog-scoped-package-version-channels.md`.
- `docs/superpowers/plans/2026-07-10-standard-bundle-authoring-v2-foundation.md`.
- `docs/superpowers/plans/2026-07-10-consumer-standards-control-plane-core.md`.
- `meta/versioning.md`.

## Scope Boundary

This is the final implementation layer before the existing v5 release checklist.

| This plan owns | This plan does not own |
| --- | --- |
| Migration-report/provider contracts and `init --migrate` | New control-plane semantics unrelated to real-package compatibility |
| Same-major catalog refresh during reconciliation | `project-toolbox` or `agent-managed-repo` design and implementation |
| Nine current V2 package reconstructions and providers | MCP server implementation |
| V1-manifest to V2-family activation | Deleting v5 legacy fallback; that remains a v6 gate |
| Real package composition, disposable release-cut dogfood, offline-wheel, and pilot-fixture evidence | Changing this repo's active authority before the atomic v5 release commit |
| Release-ready documentation and traceability | Agent Handoff engine deletion or protected consumer-branch integration |

The final task leaves `testing` ready for the separately tracked release commit. It does not change the checked-out package version from `4.3.0`, migrate this repo's active root authority, merge `main`, create tags, publish a release, or lift the release freeze.

## Plan-Pinned Contracts

These choices apply the approved specifications without adding new product behavior.

1. **Advertise reconstructed versions only.** Catalog 5 initially advertises the current V1-manifest `latest` version for each consumer/reference family and Standard Bundle Authoring `2.0`. Older `supported` values remain consumer-contract history unless independently reconstructed later.
2. **Initial catalog roles are fixed.** `adr@1.1`, `agent-handoff@1.1`, `cli-documentation@1.1`, `markdown-frontmatter@1.2`, `markdown-tooling@1.2`, `project-spec@1.1`, and `python-tooling@1.1` are `default`; `python-coding@0.5` is `reference-only`; `standard-bundle-authoring@2.0` is `internal`.
3. **Package version and consumer contract remain separate.** A package selector chooses the immutable payload. Existing schema/contract selectors migrate into package config fields such as `contract_version`; they never become the package selector.
4. **Migration output is typed data.** A version-selected `migrate` provider returns package config, recognized legacy signatures, ownership dispositions, and findings. It never writes `.standards/`, legacy files, package artifacts, or package locks.
5. **One migration executor.** `init --migrate --apply` stages the unified config/catalog and all planned artifacts, verifies preconditions, publishes artifact/control-plane bytes, writes the central lock last, verifies the result, and only then removes `.project-standards.yml` and imported package-specific locks while holding the exclusive directory lock. A partial publication remains explicit recoverable state.
6. **Migration preview is read-only.** `init --migrate` and `init --migrate --json` produce the same deterministic report and actions without creating `.standards/`, changing artifacts, or touching legacy files.
7. **Ambiguity blocks the whole migration.** Unknown YAML keys, unregistered namespaces, changed managed blocks, unknown artifact digests, unsafe paths, or an unimportable package lock make the plan non-applicable. No package migrates partially.
8. **Catalog refresh is part of reconciliation.** When the installed same-major catalog is newer, planning compares the committed and installed snapshots, preserves exact pins and compatible default-track behavior, and includes `.standards/catalog.toml` in the complete plan. Apply stages it with artifact changes and writes the central lock last. Older tools and catalog-major changes still fail closed.
9. **No package-ID branches in shared code.** Package recognition, options, outputs, providers, migrations, and legacy signatures come from installed payload declarations. An architecture test scans `control_plane/` for all nine IDs.
10. **V1 remains bounded compatibility, not dual authority.** Legacy-only repositories may validate with a warning during v5. Once `.standards/config.toml` exists, `.project-standards.yml` is an error. The old adopt bundles remain packaged only for legacy fallback until the v6 removal gate.
11. **Current repository activation is late.** Root `standard.toml` files switch to V2 family indexes, catalog 5 is added, and payload projection is synchronized only after every package payload validates in an isolated reconstruction fixture.
12. **Release actions stay separate.** This plan prepares version/pin/changelog/upgrade evidence only to the point required for a release commit review; the retained P3 tracker controls the actual version bump, merge, tags, GitHub release, and freeze lift.
13. **Dogfood uses a disposable release-cut checkout.** The versioning contract requires `pyproject.toml` to remain `4.3.0` on `testing` and move to `5.0.0` only in the atomic release commit on `main`. Therefore this plan proves the exact root migration in a temporary tracked-tree copy whose package metadata is changed to `5.0.0` before building the wheel. The source checkout retains `.project-standards.yml` until the release commit applies the already-proven migration.
14. **The complete `.standards/` tree is tracked after migration.** SPEC-CP01 A-001, FR-001, and IR-006 require `config.toml`, `catalog.toml`, `lock.toml`, declared package-owned entries, and consumer extensions to be committed and reviewable. This repository does not add `.standards/` to `.gitignore`; the directory first materializes in the disposable dogfood checkout, then in the real repository through the atomic v5 release commit.

## Requirement Allocation

| Approved requirement group | Plan evidence |
| --- | --- |
| CP01 FR-016, FR-028, DR-004 | Tasks 5–14 reconstruct complete real payloads, families, digests, catalog roles, and installed projections. |
| CP01 FR-018–FR-020, FR-034–FR-035, DR-005 | Tasks 1, 3, 7, 11, 13, and 15 close migration/provider result contracts, direct-writer conversion, package-local state, and selected-provider execution. |
| CP01 FR-021–FR-022, DR-006 | Tasks 1–3 and each package task provide whole-migration planning/apply, legacy fallback, exact signatures, and ambiguity refusal. |
| CP01 FR-023, NFR-006–NFR-007 | Task 16 derives individual, pairwise, full-set, fresh, migrated, preservation, and no-hardcode evidence from catalog 5. |
| CP01 FR-024, FR-030, FR-036 | Tasks 7–13 define closed package options, separate package/contract selectors, and declared referenced inputs where needed. |
| CP01 FR-025 | Task 4 implements same-major catalog refresh through the existing planner/executor boundary. |
| CP01 FR-027, IR-004 | Tasks 7, 11, 13, and 15 move validators and authoring commands to unified selected-package resolution while retaining bounded v5 fallback. |
| CP01 MS-4 and pre-release MS-5 | Tasks 14–18 activate catalog 5, prove compatibility/offline delivery, exercise a disposable release cut, and reconcile documentation/traceability. |
| BA02 FR-016–FR-019, IR-005, NFR-005 | Tasks 1–3 and provider-backed package tasks prove phase/effect bounds, installed dispatch, mutation/network spies, and forward/manual legacy migrations. |
| BA02 FR-024–FR-025 | Tasks 4, 14, 17, and 18 prove catalog release classification and prepare immutable-baseline evidence without performing the release. |
| BA02 FR-026–FR-028 | Tasks 5 and 18 self-host the V2 authoring standard, templates, authority notices, adoption guides, and CI workflow. |
| BA02 FR-029–FR-030, NFR-004, NFR-006 | Tasks 6–17 prove every real package, legacy signature, adapter corpus, pair/full composition, randomized order, and retained fallback classification. |
| BA02 FR-031, FR-033–FR-034, DR-008 | Tasks 5, 14, 16, and 17 prove self-hosting, no package-ID branches, source/wheel inventory parity, and offline installed execution. |

## Target File Structure

```text
catalogs/
└── 5.toml

standards/STANDARD_ID/
├── README.md
├── standard.toml
└── versions/PACKAGE_VERSION/
    ├── README.md
    ├── adopt.md                    # consumer packages only
    ├── agent-summary.md
    ├── config.schema.json
    ├── payload.toml
    ├── providers.py               # only when behavior is declared
    ├── provider-input.schema.json # only when executable providers exist
    ├── provider-output.schema.json
    ├── migration.md               # manual limitations/recovery when declared
    └── ...                        # every declared resource/output source

src/project_standards/
├── catalogs/                      # symlink-only projection
├── families/                      # symlink-only projection
├── payloads/                      # symlink-only projection
└── control_plane/
    ├── catalog_refresh.py
    └── migration.py

tests/
├── control_plane/
│   ├── test_catalog_refresh.py
│   └── test_migration.py
├── package_compatibility/
│   ├── helpers.py
│   ├── test_individual.py
│   ├── test_legacy.py
│   ├── test_pairs.py
│   ├── test_full_set.py
│   ├── test_installed_wheel.py
│   └── test_no_package_branches.py
└── fixtures/package_compatibility/
    ├── fresh/
    ├── legacy/
    └── expected/
```

Existing package resources remain canonical only when copied into a version directory and declared in `payload.toml`. The installed `payloads/`, `families/`, and `catalogs/` trees remain generated relative-file symlinks; authors never edit them directly.

---

### Task 1: Migration Report and Provider Contracts

**Files:** Modify `src/project_standards/package_contract/payload.py`, `src/project_standards/control_plane/{schemas,providers}.py`, and generated schemas; create `src/project_standards/control_plane/migration.py`; create `tests/control_plane/test_migration.py`; modify package-contract/provider schema tests.

- [x] Write failing model/schema tests for a `migration-report` provider effect, deterministic package results, recognized setting paths, legacy claims, artifact/lock dispositions, warnings/errors, duplicate claims, unsafe paths, undeclared signatures, and secret-value redaction.
- [x] Run `uv run pytest tests/package_contract/test_payload_execution_contracts.py tests/control_plane/test_schemas.py tests/control_plane/test_migration.py -q`; expect import/schema failures.
- [x] Remap the existing closed contract for `ProviderOperation.MIGRATE` from `(ProviderPhase.PLAN, ProviderEffect.MUTATION_PLAN)` to `(ProviderPhase.PLAN, ProviderEffect.MIGRATION_REPORT)`. Update the existing assertions in `tests/package_contract/test_payload_execution_contracts.py`, provider-result tests in `tests/control_plane/test_providers.py`, both full-fixture migrate providers under `tests/fixtures/package_contract/valid/full/`, and the automatic-migration provider check around `payload.py`'s legacy-endpoint validation. Do not weaken the `mutation-plan` contract for `fix`, `scaffold`, or `upgrade`.
- [x] Define frozen `MigratedPackage`, `LegacyClaim`, `LegacyDisposition`, `MigrationFinding`, and `MigrationReport` models in `control_plane/migration.py`. `MigratedPackage` contains `standard_id`, exact payload `version`, `selector`, validated package `config`, and recognized legacy JSON-pointer paths. `LegacyClaim` contains the payload-declared signature ID, target, observed digest, ownership class, and proposed disposition.
- [x] Add `migration-report.schema.json` to the generated control-plane schemas and make provider result validation select the schema implied by the declared effect.
- [x] Add human/JSON serialization that exposes paths, IDs, dispositions, and digests but no source content or configured secret value.
- [x] Run the focused tests, `uv run project-standards standards generate-package-schemas --root . --check`, Ruff, and BasedPyright; expect pass.
- [x] Commit: `feat(v5): define legacy migration reports`

### Task 2: Read-Only Legacy Discovery and Whole-Migration Planning

**Files:** Modify `src/project_standards/control_plane/migration.py`; create `tests/fixtures/package_compatibility/legacy/`; expand `tests/control_plane/test_migration.py`.

- [x] Add red fixtures for every current YAML namespace, unrelated top-level YAML, comments/anchors, malformed YAML, unknown namespaces/keys, recognized and modified bounded blocks, create-only files, centrally manageable files, referenced inputs, and the Agent Handoff provenance lock.
- [x] Add a red filesystem-spy test proving migration preview performs zero writes, renames, chmods, directory creation, network access, or direct provider mutation.
- [x] Implement `plan_legacy_migration(repo, distribution, catalog_major) -> LegacyMigrationPlan`. It loads `.project-standards.yml` once, selects only catalog-advertised default payloads with declared legacy endpoints, invokes each migration provider with immutable YAML/artifact/lock snapshots, and merges results in package-ID order.
- [x] Validate every provider-returned option object against the selected payload's `config.schema.json`. Preserve package-level `contract_version` values inside config and use `version = "latest"` for ordinary migrated selections.
- [x] Reject overlapping setting claims, undeclared YAML remainder, duplicate artifact claims, unknown signature digests, legacy symlinks, unsafe paths, modified managed content, and conflicting ownership before producing an applicable plan.
- [x] Render the complete proposed `config.toml`, installed catalog, initial central lock, artifact reconciliation plan, and visible legacy-removal actions without writing them.
- [x] Prove shuffled YAML mappings, provider discovery, filesystem enumeration, and package order yield byte-identical report/config/catalog/lock/plan output.
- [x] Run the focused migration tests; expect pass.
- [x] Commit: `feat(v5): plan complete legacy migrations`

### Task 3: Explicit Migration Apply and `init --migrate`

**Files:** Modify `src/project_standards/control_plane/{bootstrap,cli,executor,migration}.py` and `src/project_standards/cli.py`; expand `tests/control_plane/{test_bootstrap,test_cli,test_executor,test_migration}.py` and installed-wrapper tests.

- [ ] Write the complete CLI matrix for `project-standards init --catalog 5 --migrate [--apply] [--json] --repo PATH`, including incompatible flags, missing legacy state, already unified state, dual authority, preview, apply, repeat apply, and exit codes `0/1/2`.
- [ ] Add fault-injection tests before staging, after each artifact/control publication, before/after central-lock replacement, during verification, and before each legacy removal. Every failure must retain enough explicit state for a subsequent preview/recovery and must never delete legacy authority before unified validation succeeds.
- [ ] Extract executor staging/publication helpers only where migration and ordinary reconciliation require the same containment, precondition, mode, fsync, and cleanup behavior.
- [ ] Implement `apply_legacy_migration(plan)` under one exclusive `.standards/` directory lock. Re-read every legacy digest, stage every output, publish planned artifacts plus config/catalog, replace the central lock last, run selected verification providers, then remove `.project-standards.yml` and successfully imported package locks before releasing the lock.
- [ ] Refuse application when the preview is stale, non-applicable, missing its exact catalog/payload lineage, or produced by another repository path.
- [ ] Preserve unrelated consumer files and bounded-block surroundings byte-for-byte. A failed legacy-file removal reports recoverable dual authority and never edits either configuration file to hide it.
- [ ] Build and extract the test wheel, deny network, migrate a representative all-namespace repository, and assert a second reconciliation is a byte-level no-op.
- [ ] Run focused CLI/executor/migration and installed-wrapper tests; expect pass.
- [ ] Commit: `feat(v5): apply explicit control-plane migrations`

### Task 4: Same-Major Catalog Refresh

**Files:** Create `src/project_standards/control_plane/catalog_refresh.py`; modify `control_plane/{cli,executor,planner,resolution,state}.py`; create `tests/control_plane/test_catalog_refresh.py`; expand resolver/executor/end-to-end tests.

- [ ] Write failing tests for a newer installed release on catalog 5, a byte-identical catalog, compatible default updates, retained exact pins, accepted tracks, disabled packages, unavailable pins/tracks, older installed releases, changed catalog major, and release/digest tampering.
- [ ] Implement a pure `plan_catalog_refresh(committed, installed, desired, lock)` boundary. It accepts only a newer release on the same catalog major, validates the package-contract release diff, and returns old/new catalog lineage plus affected selections.
- [ ] Change reconciliation planning to resolve against the validated installed snapshot while retaining the committed catalog and lock as preconditions. Include `.standards/catalog.toml` as a tool-owned planned target only when bytes differ.
- [ ] Stage catalog refresh with artifact changes, verify the old catalog precondition immediately before publication, and write the new catalog digest/release to the central lock last.
- [ ] Prove default-track packages advance only compatibly, exact pins remain exact, accepted tracks do not normalize, and an unavailable selection blocks every write.
- [ ] Add human/JSON actions for catalog refresh without embedding catalog content.
- [ ] Run focused refresh, resolver, executor, recovery, and end-to-end tests; expect pass.
- [ ] Commit: `feat(v5): reconcile same-major catalog refreshes`

### Task 5: V2 Authoring Standard Self-Hosting Package

**Files:** Replace `standards/standard-bundle-authoring/standard.toml`; create `standards/standard-bundle-authoring/versions/2.0/**`; update its root README/templates and package-contract tests.

- [ ] Write red self-hosting tests requiring `standard-bundle-authoring@2.0` to be an `internal` payload with canonical standard, agent summary, closed empty option schema, V2 family/payload/catalog templates, and no consumer artifacts or executable providers.
- [ ] Create the `2.0` payload from SPEC-BA02. Include exact templates for `standard.toml`, `payload.toml`, `config.schema.json`, catalog entries, providers, contributions, extensions, migrations, and legacy signatures.
- [ ] Replace the root singleton manifest with a V2 family index whose only advertised reconstruction is `2.0`; compute and pin its aggregate digest.
- [ ] Update the root README authority notice: family landing guidance is current, while `versions/2.0/README.md` is normative for payload `2.0`.
- [ ] Add authoring workflow tests for create, validate, digest, index, catalog, projection, installed-wheel parity, and immutable-baseline checking.
- [ ] Run package validation and focused documentation/link tests; expect pass.
- [ ] Commit: `feat(v5): self-host bundle authoring v2`

### Task 6: Reference-Only Python Coding Reconstruction

**Files:** Replace `standards/python-coding/standard.toml`; create `standards/python-coding/versions/0.5/**`; add compatibility fixtures/tests.

- [ ] Write a red package test for a `reference-only` payload with canonical docs, agent summary, closed empty option schema, no adoption guide, no root artifacts, and documentation-only semantic-review capability.
- [ ] Reconstruct only `python-coding@0.5`. Declare the existing Python Tooling companion relationship without creating a hidden dependency.
- [ ] Prove the package is catalog-visible, cannot be enabled, writes no consumer path, and remains byte-identical through source and installed-wheel discovery.
- [ ] Run focused package and control-plane visibility tests; expect pass.
- [ ] Commit: `feat(v5): reconstruct python coding package`

### Task 7: Markdown Frontmatter Reconstruction and Unified Validators

**Files:** Replace `standards/markdown-frontmatter/standard.toml`; create `standards/markdown-frontmatter/versions/1.2/**`; modify frontmatter/id/reference/format CLI config-loading boundaries and tests.

- [ ] Write red option-schema tests for `contract_version`, schema selection, `required`, `include`, `exclude`, and reference-validation options. Reject executable paths and keep the package selector separate from the contract selector.
- [ ] Reconstruct `markdown-frontmatter@1.2` with canonical docs, templates, skill/script files, caller workflow, option schema, whole/create-only artifacts, semantic config/workflow contributions, and version-selected validate/inspect/fix providers.
- [ ] Add a declared legacy YAML endpoint that recognizes `markdown.frontmatter`, its installed workflow/skill signatures, and exact known managed bytes. Unknown or modified content must block migration.
- [ ] Refactor existing validators to resolve selected unified config by repository root. Retain explicit `--config` only for supported legacy/debug use, emit the v5 legacy warning, and reject dual authority.
- [ ] Convert formatter/fix behavior to return a typed mutation plan; route the public command through the platform executor while preserving its documented flags and exit codes.
- [ ] Prove fresh, legacy-migrated, custom-schema-reference, workflow, skill, and second-apply fixtures.
- [ ] Run all frontmatter/id/reference/formatter tests plus focused compatibility tests; expect pass.
- [ ] Commit: `feat(v5): reconstruct frontmatter package`

### Task 8: ADR Reconstruction and Frontmatter Composition

**Files:** Replace `standards/adr/standard.toml`; create `standards/adr/versions/1.1/**`; update ADR provider/config tests and compatibility fixtures.

- [ ] Write red option-schema tests for `contract_version` and `require_sections`, plus an independence test proving ADR does not require Frontmatter adoption merely because both can inspect ADR documents.
- [ ] Reconstruct `adr@1.1` with canonical docs, templates/examples, option schema, create-only scaffold, and version-selected validation providers.
- [ ] Map legacy `markdown.adr` into `config.require_sections` and `config.contract_version`; remove the printed `.project-standards.yml` fragment from active V2 outputs.
- [ ] Declare Frontmatter only as a companion and encode any shared compatibility metadata without a hidden capability or artifact dependency.
- [ ] Prove ADR alone, ADR plus Frontmatter, fresh adoption, legacy migration, disable/removal, and second-apply behavior.
- [ ] Run ADR, graph, provider, and focused compatibility tests; expect pass.
- [ ] Commit: `feat(v5): reconstruct adr package`

### Task 9: CLI Documentation Reconstruction

**Files:** Replace `standards/cli-documentation/standard.toml`; create `standards/cli-documentation/versions/1.1/**`; update CLI-doc workflow/provider tests and fixtures.

- [ ] Write red option-schema tests for profile, entrypoint, CI enablement, and workflow runner/language assumptions. Defaults must support the current simple Python profile without making Python or GitHub mandatory.
- [ ] Reconstruct `cli-documentation@1.1` with canonical docs, examples/templates, create-only usage documentation, and generated or semantically contributed workflow content.
- [ ] Map legacy `cli_documentation.version` into `contract_version`; recognize exact installed usage/workflow/config-fragment states and preserve edited usage documents as consumer-owned ambiguity.
- [ ] Bind workflow verification to the resolved payload and make disabled CI produce no workflow ownership.
- [ ] Prove Python, non-Python, CI-disabled, fresh, migrated, drift, disable, and second-apply cases.
- [ ] Run CLI Documentation and focused compatibility tests; expect pass.
- [ ] Commit: `feat(v5): reconstruct cli documentation package`

### Task 10: Markdown Tooling Reconstruction and Shared Configuration

**Files:** Replace `standards/markdown-tooling/standard.toml`; create `standards/markdown-tooling/versions/1.2/**`; update formatter/workflow/coherence tests and fixtures.

- [ ] Write red options for contract version, lint, format, CI callers, Markdown/config globs, and explicitly typed exclusions.
- [ ] Reconstruct `markdown-tooling@1.2` with markdownlint/Prettier sources, EditorConfig and VS Code semantic contributions, lint/format callers, and version-selected verification providers.
- [ ] Classify `.markdownlint.json` and `.prettierrc.json` as managed/extensible according to the approved ownership design. Compose `.editorconfig`, `.vscode/extensions.json`, and instruction exclusions semantically with other packages.
- [ ] Map `markdown_tooling.version` and exact V1 artifacts without keeping a YAML fragment. Modified root configuration must be preserved and reported before ownership transfer.
- [ ] Prove lint-only, format-only, CI-disabled, Frontmatter composition, Python Tooling composition, migrated, disable, formatter-stability, and second-apply cases.
- [ ] Run Markdown Tooling, coherence, Prettier, markdownlint, and focused compatibility tests; expect pass.
- [ ] Commit: `feat(v5): reconstruct markdown tooling package`

### Task 11: Project Specification Reconstruction and Typed Authoring Plans

**Files:** Replace `standards/project-spec/standard.toml`; create `standards/project-spec/versions/1.1/**`; modify spec config/provider/command tests and fixtures.

- [ ] Write red options for contract version, include patterns, external reference prefixes, default profile, and CI enablement. Keep project-spec document schemas independent from repository frontmatter schemas.
- [ ] Reconstruct `project-spec@1.1` with canonical docs, templates/example, workflow, option schema, and version-selected validate/lint/extract/id-next/scaffold/upgrade providers.
- [ ] Map legacy `spec` YAML and exact installed workflow/config fragment. Remove active YAML-grep behavior and bind every command to the resolved payload.
- [ ] Convert `spec new` and `spec upgrade` to return typed mutation plans and route public commands through the platform executor without changing documented dry-run, stdout, exit-code, or path-safety behavior.
- [ ] Prove fresh/migrated validation, scaffold, upgrade, workflow, disable, custom reference prefixes, and second-apply behavior.
- [ ] Run the complete spec suite and focused compatibility tests; expect pass.
- [ ] Commit: `feat(v5): reconstruct project spec package`

### Task 12: Python Tooling Reconstruction and Cross-Package Composition

**Files:** Replace `standards/python-tooling/standard.toml`; create `standards/python-tooling/versions/1.1/**`; update tooling/coherence tests and fixtures.

- [ ] Write a closed option schema for contract version, Python version, build backend, source layout, Ruff, type checker, pytest/coverage, pip-audit, CI, VS Code, and agent instructions. Type-checker selection must fan out coherently to `pyproject.toml`, workflow, editor tasks/settings, and instructions.
- [ ] Reconstruct `python-tooling@1.1` with canonical docs, build-backend guidance, workflow/script files, static sources, and semantic contributions for `pyproject.toml`, `.editorconfig`, VS Code, and bounded agent instructions.
- [ ] Preflight every claimed `pyproject.toml` key/table. Preserve conflicting consumer values and reject parent/child scope overlap before any write.
- [ ] Map legacy `python_tooling.version` plus exact V1 files. Whole agent-instruction and VS Code ownership must become bounded contributions; no package may replace the complete shared container.
- [ ] Prove real apply with Agent Handoff and Markdown Tooling, multiple type-checker selections, fresh/migrated state, disable/reference-count removal, drift, and second apply.
- [ ] Run Python Tooling, coherence, BasedPyright, Ruff, and focused compatibility tests; expect pass.
- [ ] Commit: `feat(v5): reconstruct python tooling package`

### Task 13: Agent Handoff Reconstruction and Lock Retirement

**Files:** Replace `standards/agent-handoff/standard.toml`; create `standards/agent-handoff/versions/1.1/**`; modify `src/project_standards/agent_handoff/**`, its CLI/tests, and compatibility fixtures.

- [ ] Write options for contract version, startup mode, and harness selection. Preserve create-only project knowledge and keep non-discovered policy under `.standards/packages/agent-handoff/`.
- [ ] Reconstruct `agent-handoff@1.1` with canonical docs, templates, skill, hook, integration sources, policy, legacy guidance, and version-selected scaffold/validate/drift/extract providers.
- [ ] Convert scaffold/upgrade/render operations to typed plans. Keep validation/extract providers read-only and bind every provider to immutable payload resources.
- [ ] Import recognized `.agents/agent-handoff/manifest.json` ownership into the central lock, preserve required package-local state, and remove the package-specific lock only after verification. Unknown versions, paths, owners, or digests block migration.
- [ ] Preserve consumer knowledge outside standard-owned artifacts and managed blocks. Compose AGENTS/CLAUDE, Claude settings, Codex config, and `.project-standards.yml` retirement through bounded semantic declarations/signatures.
- [ ] Prove all supported harness profiles, fresh adoption, legacy migration, modified knowledge preservation, drift, upgrade, disable/re-enable, lock retirement, and second apply.
- [ ] Run the full Agent Handoff suite plus focused compatibility tests; expect pass.
- [ ] Commit: `feat(v5): reconstruct agent handoff package`

### Task 14: Real Catalog 5 Activation and V1 Manifest Cutover

**Files:** Create `catalogs/5.toml`; finish all root V2 family indexes; synchronize `src/project_standards/{catalogs,families,payloads}/`; modify package data, graph/catalog generation, CLI activation, and related tests/docs.

- [ ] Build an isolated nine-family repository and require all payloads, digests, migration graphs, provider resources, option schemas, relationships, roles, and catalog entries to validate before touching repository root activation files.
- [ ] Add `catalogs/5.toml` with exactly the roles and versions pinned in this plan. Compute every family/catalog digest from the validated payload inventory.
- [ ] Replace V1 graph/catalog consumers with V2 package-repository facts. Keep historical V1 loaders only where the documented v5 legacy fallback still invokes them; do not make V2 `standard.toml` parse through the V1 model.
- [ ] Regenerate the human standards index/catalog from V2 families, payloads, roles, capabilities, resources, providers, outputs, and relations.
- [ ] Run `standards sync-payload-projection --root .`, review every generated relative-file symlink, and update package-data inclusion only if the built wheel otherwise omits a projected catalog/family/payload member.
- [ ] Activate the V5 adopt wrapper only after the installed catalog exposes all seven consumer defaults. V1 fallback remains available only for legacy-only installations or package versions not advertised by catalog 5.
- [ ] Keep `.standards/` absent from the source checkout and absent from `.gitignore` on `testing`. Assert the atomic v5 release patch later adds the complete tracked control plane together; a catalog-only directory is never a valid intermediate state.
- [ ] Prove source checkout and extracted wheel discover identical catalog/family/payload bytes and that no catalog-advertised resource is missing.
- [ ] Run package, graph/catalog, projection, registry, adoption, and installed-wrapper tests; expect pass.
- [ ] Commit: `feat(v5): activate current package catalog`

### Task 15: Unified Config Resolution and Public Provider Commands

**Files:** Create a focused shared config-resolution boundary under `src/project_standards/control_plane/`; modify top-level validation/fix, spec, Agent Handoff, and other provider-backed command dispatch; expand command/installed-wrapper tests.

- [ ] Write a command matrix covering unified state, v5 legacy-only fallback warning, dual authority, explicit supported override, selected payload version, disabled package, package not present, and provider refusal.
- [ ] Implement one repository-root resolver that returns selected payload plus validated effective package config. Package commands may not parse `.standards/config.toml` independently or read `.project-standards.yml` when unified authority exists.
- [ ] Route every declared validate/verify/inspect provider through the version-selected provider boundary. Route `fix`, `scaffold`, and `upgrade` plans through the executor-only mutation path.
- [ ] Preserve existing command names, flags, human/JSON output, stdout/stderr contracts, and exit codes unless SPEC-CP01 explicitly deprecates them.
- [ ] Add a source scan proving current direct-write provider entrypoints are absent from advertised payload declarations and shared code contains no package-ID dispatch.
- [ ] Run every provider-backed command from the extracted wheel with network denied; expect pass.
- [ ] Commit: `feat(v5): route commands through selected packages`

### Task 16: Real Package Compatibility Matrix

**Files:** Create `tests/package_compatibility/**`, including `test_performance.py`, and fixtures; update package-specific tests where matrix failures expose contract defects.

- [ ] Build a table-driven list from catalog 5 rather than hardcoding a count. Assert every consumer default passes fresh enable/apply/validate/disable/re-enable alone.
- [ ] Generate every unordered pair from the consumer-default list. Exercise fresh and migrated apply, all declared validators, shared ownership, removal, and second-apply byte identity.
- [ ] Exercise the full supported set once per fresh and all-namespace legacy correctness fixture under the ordinary non-performance gate.
- [ ] Mark only the 100-order requested/discovery permutation sweep as `performance`. Compare reports, config/catalog/lock, planned actions, and final files, and require completion within 30 seconds on the normal Linux CI runner.
- [ ] Add targeted mandatory matrices: Python Tooling + Agent Handoff + Markdown Tooling; ADR + Frontmatter; Project Spec + Frontmatter; every package contributing to VS Code, EditorConfig, workflows, or agent instructions.
- [ ] Assert a failure in any package row excludes that package from catalog 5 rather than weakening or skipping the row.
- [ ] Build/extract one session-scoped wheel, deny network, rerun the individual/pair/full correctness matrix against that shared installed payload tree, and compare source/wheel results. Do not rebuild the wheel per matrix row.
- [ ] Put repeated wheel build/extract cycles in `test_performance.py` under the `performance` marker; keep one installed-wheel individual/pair/full correctness pass in the default gate.
- [ ] Add performance assertions that the real catalog remains within the existing 100-package/1,000-artifact planning threshold.
- [ ] Run `uv run pytest tests/package_compatibility -m 'not performance' -q`; expect every correctness row pass. Run `uv run pytest tests/package_compatibility/test_performance.py -m performance -q` separately; expect the 100-order and repeated-wheel budgets to pass.
- [ ] Commit: `test(v5): prove current package compatibility`

### Task 17: Disposable Release-Cut Dogfood and Refresh Proof

**Files:** Create a release-candidate checkout helper and dogfood/refresh tests under `tests/package_compatibility/`; update release-checklist documentation. Do not replace the source checkout's `.project-standards.yml` in this task.

- [ ] Copy only the tracked repository tree to a temporary checkout, set its package metadata and lock to `5.0.0`, build/extract the wheel there, and assert the installed CLI reports `project-standards 5.0.0`. Never edit version metadata in the source checkout.
- [ ] Preview the temporary checkout's full legacy migration and save the human/JSON evidence in `docs/reviews/2026-07-11-consumer-standards-control-plane-release-cut-evidence.md`. Resolve every ambiguity in package declarations or explicit repository intent before apply.
- [ ] Apply the reviewed migration in the temporary checkout. Verify `.project-standards.yml` is removed only after unified validation, the Agent Handoff package lock is retired/imported, consumer-authored handoff knowledge remains byte-preserved, and every planned artifact is centrally locked.
- [ ] Run all validators and package commands through unified state in the temporary checkout. Confirm a second reconciliation produces no actions and changes no bytes.
- [ ] In the migrated disposable checkout, run `render-consumer-catalog --output .standards/catalog.toml --check` with its installed `5.0.0` tool release and require exact agreement with the tracked catalog. This is the real control-plane catalog drift check; it never runs against `.standards/` in the legacy-authority source checkout.
- [ ] Build a second same-major catalog snapshot in a fixture, preview/apply refresh, and prove compatible defaults update while exact pins, options, accepted tracks, and unrelated files remain unchanged.
- [ ] Search tracked runtime, workflow, docs, tests, and installed-wheel content for active `.project-standards.yml`, V1 manifest, package-specific lock, or direct-writer dependencies. Classify retained v5 fallback references explicitly; remove unintended active dependencies.
- [ ] Record the exact reviewed migration command, changed-path inventory, patch SHA-256, control-plane file digests, and replay result in `docs/reviews/2026-07-11-consumer-standards-control-plane-release-cut-evidence.md`. The test may retain the generated patch only as a temporary artifact; assert replaying it against a fresh temporary checkout yields the same digests as the dogfood run.
- [ ] Run dogfood validation, migration, drift, projection, catalog-refresh, and installed-wheel tests; expect pass.
- [ ] Commit: `test(v5): prove release-cut control-plane migration`

### Task 18: Documentation, Traceability, and Release-Ready Closeout

**Files:** Update SPEC-CP01/SPEC-BA02 traceability and deviations; `README.md`, `AGENTS.md`, `standards/README.md`, `standards/catalog.md`, `docs/usage.md`, package adoption guides, `CHANGELOG.md`, `UPGRADING.md`, `meta/versioning.md` only where pre-release policy text changes, `docs/reviews/2026-07-11-consumer-standards-control-plane-release-cut-evidence.md`, and canonical handoff/status/task/session pointers.

- [ ] Update every package adoption guide to package-specific suitability, options, outputs, migration, verification, and troubleshooting. Remove active V1 fragment/install instructions while preserving clearly labeled v5 legacy migration guidance.
- [ ] Document `init --migrate`, preview/apply ordering, ambiguity handling, same-major refresh, package versus contract selectors, provider-backed commands, and the v6 fallback-removal gate.
- [ ] Reconcile SPEC-CP01 and SPEC-BA02 requirement traceability with exact test/commit evidence. Mark a requirement complete only when its real-package and installed-wheel evidence passes; record every accepted deviation.
- [ ] Normalize all v5 specs/ADRs affected by implementation. Resolve or explicitly defer SPEC-MT01 OQ-005 and leave no stale status row or unexplained unchecked implemented DoD item.
- [ ] Add the package compatibility matrix and migration/refresh/release evidence to the durable docs without turning `docs/STATUS.md` into a changelog.
- [ ] Run an inline adversarial implementation review. Fix every Important-or-higher finding and rerun focused evidence before the full gate.
- [ ] Run the complete verification gate below and confirm hosted graph/catalog CI for the pushed `testing` commit.
- [ ] Update `docs/TODO.md` without deleting the retained v5 tracker: record MS-4 and disposable dogfood evidence under the CP01 follow-on, but leave that item open for the atomic release-commit migration. Leave release publication, Step 07, MCP, toolbox, repository-governance, and Agent Handoff retirement tasks open.
- [ ] Commit: `docs(v5): close package migration readiness`

## Verification Gates

Run fail-fast in this order:

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run coverage run -m pytest -m 'not performance'
uv run coverage report
uv run pytest -m performance tests/control_plane/test_scale.py tests/package_contract/test_scale.py
uv run pip-audit
npm ci
uv run pytest tests/coherence
npx prettier --check .
npx markdownlint-cli2 '**/*.md'
uv run project-standards validate --config .project-standards.yml
uv run project-standards spec validate --config .project-standards.yml
uv run project-standards spec lint --config .project-standards.yml --strict
uv run project-standards standards validate-packages --root . --json
uv run project-standards standards validate-graph --root . --require-all-manifests --json
uv run project-standards standards generate-package-schemas --root . --check
TARGET_TOOL_RELEASE="5.0.0"
git check-ignore -q build/catalog-scratch.probe
test ! -L build
mkdir -p build
CATALOG_SCRATCH="$(mktemp -d build/catalog-scratch.XXXXXX)"
trap 'rm -rf "$CATALOG_SCRATCH"' EXIT
uv run project-standards standards render-consumer-catalog \
  --root . \
  --catalog-major 5 \
  --output "$CATALOG_SCRATCH/catalog.toml" \
  --tool-release "$TARGET_TOOL_RELEASE"
uv run project-standards standards render-consumer-catalog \
  --root . \
  --catalog-major 5 \
  --output "$CATALOG_SCRATCH/catalog.toml" \
  --tool-release "$TARGET_TOOL_RELEASE" \
  --check
rm -rf "$CATALOG_SCRATCH"
trap - EXIT
test ! -e .standards
uv run project-standards standards sync-payload-projection --root . --check
uv run project-standards agent-handoff validate --repo .
uv run project-standards agent-handoff drift-check --repo .
uv run pytest tests/package_compatibility -m 'not performance' -q
uv run pytest tests/package_compatibility/test_performance.py -m performance -q
uv build
git diff --check
```

Expected results:

- All tests pass at or above the repository branch-coverage floor.
- Every catalog-derived individual, pairwise, full-set, migrated, and installed-wheel compatibility row passes.
- The exact same source and installed distribution payload/catalog digests are reported.
- Source-tree catalog rendering/checking uses only a cleaned temporary directory and leaves `.standards/` absent while legacy authority remains active.
- Migration preview is read-only; apply retires legacy authority only after unified verification.
- Same-major refresh preserves pins, options, and accepted-track boundaries.
- The disposable v5 release-cut checkout's second reconciliation is a byte-level no-op.
- Generated schemas, catalogs, family/payload projections, indexes, and docs are fresh.
- No shared control-plane source contains a current package ID branch.
- No active package-specific lock or unintended V1 runtime authority remains.
- The tree contains no unrelated user-owned changes.

## Plan Completion Criteria

- Catalog 5 advertises exactly the nine reconstructed versions and roles pinned by this plan.
- Every advertised payload is complete, immutable, digest-verified, and available offline from the built wheel.
- Every current namespace and recognized installed artifact migrates through a deterministic preview and explicit apply.
- Unknown or modified legacy state fails closed without deleting or overwriting consumer content.
- Package selectors remain independent from consumer contract/schema selectors.
- Current validate/verify/inspect/fix/scaffold/upgrade behavior resolves through the selected payload and executor boundary.
- Agent Handoff's package-specific provenance lock is imported and retired without changing consumer knowledge.
- Real individual, pairwise, full-set, migrated, randomized-order, and installed-wheel matrices pass.
- SPEC-CP01 MS-4 is complete; the pre-release MS-5 evidence and exact root migration patch are release-ready.
- This source checkout deliberately retains `.project-standards.yml` while its package metadata remains `4.3.0`; the disposable `5.0.0` checkout proves `.standards/` as the sole post-migration authority.
- The atomic release patch adds the complete `.standards/` tree as tracked state; neither the source-tree gate nor `.gitignore` creates a catalog-only intermediate authority.
- Actual v5 version bump, root-authority migration, `main` merge, signing, tag movement, GitHub release, and freeze lift remain controlled by the retained P3 release tasks.
