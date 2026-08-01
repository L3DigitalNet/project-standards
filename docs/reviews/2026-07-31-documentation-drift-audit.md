---
schema_version: '1.1'
id: 'reference-9jnl3p-documentation-drift-audit'
title: 'Documentation Drift Audit'
description: 'Full repository documentation-to-implementation and implementation-to-documentation audit at the post-v5.13.0 testing commit.'
doc_type: 'reference'
status: 'active'
created: '2026-07-31'
updated: '2026-07-31'
reviewed: '2026-07-31'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'agent'
tags:
  - 'documentation'
  - 'review'
  - 'validation'
aliases:
  - '2026-07-31 drift audit'
related:
  - 'README.md'
  - 'docs/usage.md'
  - 'meta/versioning.md'
  - 'docs/STATUS.md'
source: []
confidence: 'high'
visibility: 'internal'
license: null
---

# Documentation Drift Audit

## Header

| Field | Value |
| --- | --- |
| Date | 2026-07-31 |
| Repository | `/home/chris/projects/project-standards` |
| Branch | `testing` |
| Reviewed commit | `988ffe581cf9faf245f0a542ffb08e8ad7d6b8ce` |
| Comparison base | `v5.13.0` / `52d23ca` for release-state comparison; the audit itself covered the full tracked tree |
| Audit mode | Full |
| Candidate distribution | `project_standards-5.13.0-py3-none-any.whl`, SHA-256 `84812edba91199a6f0fa078bab96ae6fad8c95166081aa98306330f3202a6f0f` |
| Coordinator | Root Codex coordinator; the active root model was not exposed, so this report does not claim a Sol model identity |

## Working-Tree Baseline

The audit began on a dirty tree. The pre-existing tracked modifications were `README.md`, `docs/STATUS.md`, `docs/TODO.md`, `docs/handoff/deployed.md`, `docs/handoff/sessions/2026-07.md`, and `docs/handoff/state.md`; `ROADMAP.md` was an untracked user file. The baseline branch tip, `origin/testing`, and `origin/main` all resolved to `988ffe5`. No baseline change was reset, stashed, discarded, or attributed to this audit.

## Executive Summary

The selected Catalog 5 control plane is internally consistent: reconciliation is at a fixed point, all seven consumer packages resolve to their locked defaults, package/graph/schema/projection checks pass, and the candidate wheel matches the published v5.13.0 asset digest. Drift was concentrated in mutable public and maintainer documentation, not in generated package projections.

The audit confirmed 21 findings: 9 high, 7 medium, and 5 low. Seventeen were remediated and independently verified. Four remain blocked because a safe correction requires an owner-controlled policy, specification, or immutable-package decision. No critical finding was identified.

The highest-impact repairs add the shipped `mcp` command to the public CLI contract; correct its Python floor and readiness state; replace stale release/CI handoff claims; enforce completed-plan lifecycle without leaving dangling authority links; and make release preparation use clean `main`, locked prerequisites, a unique wheel, a fresh runtime, and the full pre-tag verification sequence.

## Bottom Line

Within the recorded full-tree coverage, mutable documentation and the two small implementation support surfaces now agree with the observed v5.13.0 repository state. The repository is **not** claimed universally drift-free: four authority conflicts remain blocked, historical handoff advisories remain, and configured reference validation does not detect every deleted path form that the independent scan found.

## Authority Model

| Domain | Primary authority | Secondary evidence |
| --- | --- | --- |
| Standards selection and ownership | `.standards/config.toml`, `.standards/catalog.toml`, `.standards/lock.toml`, Catalog 5 manifests | Package, graph, schema, projection, and reconciliation checks |
| CLI and configuration | Installed candidate-wheel parsers and command handlers | `docs/usage.md`, inventory tests, selected package schemas |
| MCP behavior | ADR 0025, ADR 0026, SPEC-MS01, installed server code and contract tests | `docs/mcp-server.md`, protocol/client evidence matrix |
| Specifications and plans | Approved maintained specs and active ADRs | `docs/handoff/specs-plans.md`, tests, implementation, Git history |
| Release policy | `meta/versioning.md`, package release-consistency implementation, signed tags and published assets | `scripts/release_prep.py`, `scripts/verify.sh`, deployed/session records, hosted Check |
| Handoff lifecycle | Agent Handoff 1.7 plus `docs/handoff/conventions.md` | `docs/STATUS.md`, `docs/TODO.md`, state, deployed, and monthly session record |
| Formatting and metadata | Markdown Tooling 1.11 and Markdown Frontmatter 1.7 | Prettier, markdownlint, frontmatter/id/reference validators |

When sources conflicted, approved normative documents took precedence over mutable prose; observed implementation took precedence for public behavior only where no approved requirement said otherwise. Immutable released payload bytes were never edited.

## Adopted Standards and Effective Options

Catalog 5 release `5.13.0` resolves the following `latest` selectors:

| Standard | Resolved package | Material effective options |
| --- | --- | --- |
| ADR | 1.3 | Contract 1.0; required sections enabled |
| Agent Handoff | 1.7 | Contract 1.0; Claude Code and Codex; automatic startup |
| CLI Documentation | 1.5 | Contract 1.0 |
| Markdown Frontmatter | 1.7 | Contract 1.1; required; self-hosted workflow; explicit include/exclude scope |
| Markdown Tooling | 1.11 | Contract 1.1; self-hosted workflow |
| Project Specification | 1.5 | Contract 1.1; self-hosted workflow; 18 configured specification paths |
| Python Tooling | 1.10 | Contract 1.0; consumer-owned workflow; strict Ruff/BasedPyright/pytest/coverage gate; performance lane enabled |

Python Coding 0.6 remains reference-only and Standard Bundle Authoring 2.6 remains internal; both were included where they provide repository authority.

## Scope and Exclusions

The inventory contained 1,191 tracked documentation-like artifacts (`.md`, `.mdx`, `.rst`, `.txt`, `.adoc`, or `.asciidoc`). The audit covered both directions: documented claims against authoritative implementation, and public/operator behavior against required documentation.

Excluded from present-tense semantic findings were intentionally historical immutable payloads, vendored test fixtures, superseded V1 compatibility bundles, archived designs considered only as history, and external protocol/client facts that would require a fresh web research pass. Historical material was still mechanically checked for integrity and links where repository policy requires it.

## Coverage Summary

This grouped ledger assigns every baseline artifact one final disposition. Groups are disjoint and total 1,191.

| Path/group | Count | Document class | Applicable standards | Authority sources | Worker | Depth | Finding IDs | Uninspected dependencies | Disposition |
| --- | --: | --- | --- | --- | --- | --- | --- | --- | --- |
| `standards/**` | 522 | Versioned and mutable standards documentation | All package standards; Standard Bundle Authoring 2.6 | Catalog, family indexes, payload manifests, schemas, providers | Terra standards lane | Mechanical; current canonical surfaces deep | DRIFT-0009 | External upstream tool behavior; immutable historical assertions | inspected-mechanical |
| `src/project_standards/payloads/**` | 456 | Installed payload projections and resources | Selected Catalog 5 packages | Canonical `standards/**` sources and projection generator | Terra mechanical lane | Derived | None | Candidate sdist parity beyond published digest | generated-and-verified |
| `tests/**` documentation-like paths | 49 | Test documentation and fixtures | Python Tooling 1.10; package contracts | Test configuration and executable fixtures | Terra implementation/spec lanes | Mechanical; maintained README deep | DRIFT-0019 | Fixture prose not presented as product documentation | inspected-mechanical |
| `src/project_standards/bundles/**` | 19 | Frozen V1 compatibility documentation | Legacy compatibility contract | Bundle loader and compatibility tests | Terra mechanical lane | Excluded/history | None | Line-by-line historical semantics | historical-or-superseded |
| Root, `meta/**`, other `src/**`, and maintained `docs/**` | 145 | Public, maintainer, spec, ADR, handoff, plan, research, and workflow documentation | ADR 1.3; Agent Handoff 1.7; CLI Documentation 1.5; Markdown Frontmatter 1.7; Markdown Tooling 1.11; Project Specification 1.5; Python Tooling 1.10 | Parsers, schemas, specs, ADRs, source, tests, Git/release state | Five Terra semantic lanes plus coordinator | Deep | DRIFT-0001–DRIFT-0008, DRIFT-0010–DRIFT-0021 | Fresh external source fetches; blocked owner judgments | inspected-deep |

Configured mechanical coverage additionally included 36 Markdown Frontmatter documents, 18 Project Specification documents, 1,153 remaining Markdown files after the three completed-plan deletions and this report's addition, all package manifests, and all generated catalog/projection outputs.

## Findings

Each confirmed finding was normalized against the drift-audit finding schema. Confidence is shown numerically; `1.00` means repository evidence was direct and unambiguous.

| ID | Severity | Classification / subject | Applicable standard | Status | Evidence and disposition |
| --- | --- | --- | --- | --- | --- |
| DRIFT-0001 | High | documentation-omission / contract | CLI Documentation 1.5 | verified | `project-standards mcp` shipped but `docs/usage.md` and its 31-leaf oracle omitted it. Added the 32nd leaf, lifecycle/output/exit contract, and RED/GREEN inventory coverage. |
| DRIFT-0002 | High | documentation-contradiction / contract | CLI Documentation 1.5 | verified | `docs/mcp-server.md` claimed Python 3.10 while `pyproject.toml` requires 3.14. Corrected to 3.14. |
| DRIFT-0003 | High | documentation-stale / lifecycle | Project Specification 1.5 | verified | `docs/mcp-readiness.md` described T1 as unstarted after MCP shipped. Preserved Step 07 as history and added the v5.12/v5.13 successor state. |
| DRIFT-0004 | Medium | documentation-contradiction / behavioral | Markdown Frontmatter 1.7 | verified | Four standalone `--config` entries described legacy YAML as the default under unified authority. Corrected precedence and rejection behavior. |
| DRIFT-0005 | High | documentation-stale / operations | Agent Handoff 1.7 | verified | `RUN4PLACEHOLDER` remained in deployed state. Replaced it with successful Check `30666389705` and scoped that run to post-release test/gate corrections. |
| DRIFT-0006 | High | standard-conformance / lifecycle | Agent Handoff 1.7 | verified | `docs/STATUS.md` had become a historical changelog and contradicted the published MCP/release state. Reduced it to a current snapshot while retaining history in durable owners. |
| DRIFT-0007 | High | standard-conformance / traceability | Project Specification 1.5; ADR 1.3 | verified | Three completed plans remained active. Deleted them under policy, transferred surviving authority to specs/ADRs/Git history, removed nine dangling references and three dead digest exemptions, and made the release scan omit only worktree-deleted plans from its historical sweep while current surfaces remain fail-closed. |
| DRIFT-0008 | High | cross-document-conflict / lifecycle | Repository release contract | blocked | v5.13.0 documentation calls the release MINOR by owner designation while `check-release` and `meta/versioning.md` classify its observable change as PATCH. The published immutable tag cannot be relabeled; owner policy is required. |
| DRIFT-0009 | High | documentation-stale / contract | Python Tooling 1.10 | blocked | The current immutable 1.10 README says the retired V1 root remains authoritative. Repair requires a separately authorized successor payload and Catalog promotion, not an in-place edit. |
| DRIFT-0010 | Medium | documentation-stale / lifecycle | Agent Handoff 1.7 | verified | Handoff state focused on a completed release and an ended incident. Routed current focus to consumer retirement and controlled benchmark work; cleared active incidents. |
| DRIFT-0011 | Medium | cross-document-conflict / ownership | Agent Handoff 1.7 | verified | Deferred self-hosted CI remained under the completed v5.13 release. Moved it to the owner-selected `agent-managed-repo` future program without changing its substance. |
| DRIFT-0012 | Medium | standard-conformance / metadata | Markdown Frontmatter 1.7 | verified | The research index predated two indexed 2026-07-31 reports. Advanced and canonically formatted its metadata. |
| DRIFT-0013 | Medium | cross-document-conflict / traceability | Project Specification 1.5; Agent Handoff 1.7 | blocked | The active Agent Handoff plan has 88 unchecked rows and cites SPEC-DPEY rev 0.5 while handoff says Tasks 1–17 complete and the approved spec is rev 0.8; package/retirement facts also conflict. Owner-controlled reconciliation is required. |
| DRIFT-0014 | Medium | documentation-stale / lifecycle | Project Specification 1.5 | blocked | Approved, locked SPEC-RD01 still contains present-tense pre-implementation states after v5.12 delivery. Only the deleted-plan evidence pointer was safely repaired; a full revision requires specification change control. |
| DRIFT-0015 | High | cross-document-conflict / workflow | Python Tooling 1.10; repository release contract | verified | Release authority omitted mandatory prerequisites/full proof; helper output used an ambiguous wheel glob and an impossible dirty-tree branch switch. The workflow now requires clean `main`, locked prerequisites, read-only projection proof, a cleared unique wheel, fresh runtime, full gate, and pre-tag checks, with RED/GREEN tests. |
| DRIFT-0016 | Medium | documentation-underspecified / workflow | CLI Documentation 1.5 | verified | README called installation forced but omitted `uv tool install --force`. The exact command now matches the stated update behavior. |
| DRIFT-0017 | Low | documentation-stale / example | Markdown Tooling 1.11 | verified | Release-gate research named `npx` although the gate resolves `node_modules/.bin` tools. Corrected the observed command path. |
| DRIFT-0018 | Low | documentation-stale / literal | None | verified | Dependabot commentary named the superseded markdownlint action major. Reworded it around moving action tags. |
| DRIFT-0019 | Low | documentation-stale / literal | Python Tooling 1.10 | verified | `tests/README.md` misstated pytest `addopts`. Synchronized it with `pyproject.toml`. |
| DRIFT-0020 | Low | documentation-stale / literal | Python Tooling 1.10 | verified | `scripts/README.md` pointed the dogfood twin at Python Tooling 1.4. Updated it to 1.10. |
| DRIFT-0021 | Low | documentation-stale / literal | None | verified | README called `scripts/check.py` the repository gate. Corrected the tree description to the actual `scripts/verify.sh` gate and helper role. |

All verified records have confidence `1.00`. DRIFT-0008, DRIFT-0009, DRIFT-0013, and DRIFT-0014 have confidence `0.99`: the conflict is directly evidenced, while the correct owner resolution is intentionally undetermined.

### Rejected or Merged Candidates

- The repeated `project-standards --version || project-standards --version` command is an intentional one-retry probe, not duplication drift.
- The future-artifact-cleanup TODO is defined by repository history and was preserved exactly.
- The immutable Standard Bundle Authoring 2.0 broken path is historical, already corrected by 2.1, and covered by the mutable family erratum.
- The editable-source `installed catalog projection is unavailable` result is not control-plane drift; the tracked source projection is a symlink deliberately rejected by installed-distribution loading. Every corresponding candidate-wheel command passed.
- The 241 remaining monthly-session length advisories are inherited, non-failing historical records. They were not converted into 241 findings or mass-rewritten.
- SAT-004 was merged into DRIFT-0007 because deleting the completed MCP plan also removes its stale authoring-time state.

## Documentation Fixes

- Added complete `mcp` CLI coverage; corrected MCP prerequisites and readiness successor state.
- Corrected unified/legacy configuration precedence in standalone command reference entries.
- Reconciled release, deployment, status, TODO, session, and current handoff state.
- Synchronized release preparation across README, versioning policy, script/operator reference, gate diagnostic, and handoff conventions.
- Corrected research metadata and stale tool/version/configuration literals.
- Removed completed plan paths and rewrote surviving ADR/spec/research references to durable authorities.

## Standards-Conformance Fixes

- Applied Agent Handoff 1.7 lifecycle and routing rules to STATUS, TODO, state, deployed state, and the session record.
- Applied Project Specification plan-lifecycle policy by deleting only the three completed plans; the active Agent Handoff plan remains untouched and blocked.
- Applied Markdown Frontmatter 1.7 canonical metadata to the research index and this report.
- Preserved every immutable standards payload and declined an unauthorized package upgrade for Python Tooling 1.10.

## Implementation Fixes

- `scripts/release_prep.py` now rejects non-`main`, prints a coherent commit-before-verification path, and emits deterministic candidate/full-gate commands.
- `tests/test_release_prep.py` pins prerequisites, order, unique/fresh artifact handling, exact target wheel selection, and non-`main` refusal.
- The release-consistency characterized-document registry no longer retains three absent plan paths; a regression test requires every exemption path to exist.
- Release-consistency omits worktree-deleted plans only from the unclassified historical sweep; current package surfaces remain fail-closed before commit.
- The CLI usage inventory test now derives a 32-leaf contract including `mcp`.
- `scripts/verify.sh` now reports the same safe candidate build/extraction procedure as release authority.

No dependency, lockfile, public package, schema, generated payload, or standards selection changed.

## Managed and Generated Artifact Actions

No generated output was edited directly. Reconciliation remained at `drift:false`; package schemas, payload projection, and generated catalog were current. No reconciliation apply or standards upgrade was needed. Agent Handoff create-only files were edited as repository-owned current state, then validated through the selected package. The three completed plans were ordinary tracked plan documents, not managed generated artifacts.

## Blocked Findings

### DRIFT-0008 — Release classification authority conflict

**Verified fact:** the published v5.13.0 record states MINOR by owner designation, while the release-consistency classifier returns PATCH with no findings against v5.12.0. **Blocked judgment:** whether owner-designated train level is a permitted policy exception is not defined. **Required decision:** amend the future release contract or explicitly prohibit owner overrides; do not mutate the published tag.

### DRIFT-0009 — Immutable Python Tooling 1.10 authority statement

**Verified fact:** the current selected payload contains a false pre-v5 V1-authority sentence. **Blocked judgment:** immutable 1.10 cannot be edited and the audit was not authorized to publish/select 1.11. **Required decision:** authorize a successor payload/Catalog promotion or accept a documented current-version erratum strategy.

### DRIFT-0013 — Agent Handoff active-plan/spec state

**Verified fact:** active plan checkboxes, approved spec revision, package version, and handoff progress do not agree. **Blocked judgment:** repository evidence cannot safely decide whether to collapse the plan to Task 18, revise the spec, or reclassify retirement work. **Required decision:** reconcile these authorities in one owner-approved plan/spec checkpoint.

### DRIFT-0014 — Locked MCP roadmap lifecycle

**Verified fact:** SPEC-RD01 retains pre-implementation statuses after delivery. **Blocked judgment:** a wholesale factual refresh would materially revise an approved locked specification. **Required decision:** authorize a successor revision that distinguishes completed v1 delivery from still-deferred write/remote phases.

## Validation Commands and Results

| Command/scope | Result |
| --- | --- |
| Candidate-wheel `reconcile --check --json` | Pass: `ok:true`, `drift:false` |
| `project-standards validate` and `validate-references` under candidate wheel | Pass: 36 configured documents |
| `project-standards spec validate` and `spec lint` | Pass: 18/18 configured specifications |
| Agent Handoff `validate` and `drift-check` | Pass; 241 inherited non-failing monthly-session advisories, no current state warning |
| Package validation, graph, schema freshness, payload projection, catalog render | Pass |
| CLI usage inventory focused test | RED on omitted `mcp`; GREEN: 7 passed |
| Release-prep/version focused tests | RED on missing prerequisites/artifact/branch contracts; GREEN: 14 passed |
| Release-consistency focused suite | RED on three absent exemption paths, completed-plan deletion, and current-surface deletion; GREEN: 53 passed. The paired deletion regressions prove that only deleted plans leave the historical sweep while deleted current package documentation remains required. |
| Ruff format/check and BasedPyright on changed Python | Pass |
| Targeted Prettier and markdownlint; final whole configured Markdown scan | Pass; 0 markdownlint issues in 1,153 files after deletions and report addition |
| `bash -n scripts/verify.sh`; YAML parse; `git diff --check` | Pass |
| Hosted GitHub Check for `988ffe5` | Pass: run `30666389705`; applies to post-release gate/test corrections, not tagged `52d23ca` bytes |

The final serial `scripts/verify.sh --full` was started after this report, then stopped at the owner's direction because concurrent repository work was still in progress. It is not completion evidence for this audit. Closeout relies on the focused suites and package, documentation, static, handoff, and diff gates recorded above; the hosted Check remains evidence only for the pre-audit commit identified in the table.

## Files Changed

- Public/reference docs: `README.md`, `docs/usage.md`, `docs/mcp-server.md`, `docs/mcp-readiness.md`, `meta/versioning.md`, `scripts/README.md`, `tests/README.md`.
- Handoff/current state: `docs/STATUS.md`, `docs/TODO.md`, `docs/handoff/conventions.md`, `docs/handoff/deployed.md`, `docs/handoff/sessions/2026-07.md`, `docs/handoff/specs-plans.md`, `docs/handoff/state.md`.
- ADR/spec/research: ADR 0025, ADR 0026, SPEC-RD01, MCP protocol/client matrix, release-gate research, research index, and this report.
- Workflow/source/tests: `.github/dependabot.yml`, `scripts/release_prep.py`, `scripts/verify.sh`, `src/project_standards/package_contract/release_consistency.py`, `tests/test_release_prep.py`, `tests/test_usage_doc_inventory.py`, and `tests/package_contract/test_release_consistency.py`.
- Deleted under completed-plan policy: the 2026-07-19 v5.1 review-remediation plan and the two 2026-07-24 MCP plans.

## Pre-Existing Changes Preserved

The README roadmap link and reusable-workflow table-of-contents addition remain. The pre-existing v5.13 release facts in STATUS, TODO, deployed state, session history, and handoff state were reconciled rather than discarded. The untracked `ROADMAP.md` was never edited. No unrelated file was formatted, deleted, committed, pushed, or otherwise changed.

## Remaining Uncertainties

- External MCP protocol, SDK, client, and third-party tool facts were not freshly fetched; current repository research was treated as evidence, not re-researched.
- Immutable historical payload prose was mechanically checked and sampled semantically, not revalidated line by line against every historical upstream behavior.
- Configured `validate-references` passed while nine deleted-plan references still existed; the independent literal/path scan found and removed them. Expanding validator semantics to cover every frontmatter and prose path form is a recommendation, not part of this remediation.
- The 241 historical Agent Handoff advisories remain non-failing and inherited.
- The four blocked findings require authority beyond safe audit remediation.

## Model Utilization

- **Luna assignments:** none; Luna was not exposed in the available model set.
- **Terra assignments:** six initial lanes covered mechanical inventory, CLI/public contract, specifications/ADRs/traceability, standards packages, release/handoff truth, and development workflow/operations. Terra also performed all substantive remediation and independent review.
- **Luna → Terra escalations:** the mechanical inventory and deterministic validation lane used Terra because Luna was unavailable.
- **Terra → coordinator escalations:** release MINOR/PATCH authority, immutable Python Tooling 1.10 correction, Agent Handoff plan/spec authority, and locked MCP roadmap lifecycle.
- **Mechanical fixes:** counts, dates, versions, command paths, action commentary, pytest settings, dogfood pointers, and dead registry entries.
- **Semantic fixes:** CLI/MCP behavior, status/deployment/readiness state, plan lifecycle, ADR ownership, and release workflow authority.
- **Implementation fixes:** release-prep branch/output behavior, release-consistency registry invariant, CLI inventory coverage, and gate diagnostics.
- **Independent reviews:** a standards/package reviewer checked CLI and release commands; a specification/traceability reviewer checked lifecycle and deleted-plan fallout; the mechanical lane reran deterministic controls.
- **Assignments exceeding original scope:** the exemption invariant exposed one older absent 2026-07-25 plan entry, which the coordinator separately approved for same-kind removal. Independent review expanded the release fix from missing gate prose to prerequisites, unique artifact handling, and coherent branch ordering.
- **Mixed-model routing limitations:** all workers used `gpt-5.6-terra`; neither Luna nor a model-identified Sol root was available. Reliable token and cost totals were unavailable and are not fabricated.
