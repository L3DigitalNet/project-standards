---
schema_version: '1.1'
id: 'reference-aud53k-adoption-mechanics-audit'
title: 'Candidate 5.3.0 Adoption-Mechanics Audit'
description: 'Multi-agent mock-migration audit of the candidate 5.3.0 release across copies of every real v4 consumer repository, with cross-model verification of deduplicated findings.'
doc_type: 'reference'
status: 'active'
created: '2026-07-20'
updated: '2026-07-20'
reviewed: '2026-07-20'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'migration'
  - 'review'
  - 'validation'
aliases: []
related:
  - 'UPGRADING.md'
  - 'CHANGELOG.md'
---

# Candidate 5.3.0 Adoption-Mechanics Audit

Audit of the unreleased 5.3.0 candidate (commit `e69831f`, the issue #12/#13 relinquishment fix) run on 2026-07-20, before release. Seventeen scenario agents mock-migrated or mock-adopted **copies** of real `~/projects/` repositories against the candidate wheel; the real repositories were never modified. The 17 scenarios produced ~120 raw finding records, deduplicating to ~55 unique findings. The 14 most-reported clusters were adversarially verified in two waves: a Fable-model wave (13 verdicts before the run was stopped to conserve usage) and a complete independent Sonnet-model wave over all 14 clusters (14/14 verdicts, several with source-level root-cause analysis). Where the waves overlap they agree. The remaining ~25 singleton findings were not individually re-verified; they are inventoried in the appendix so nothing is lost with the scratchpad.

## Method

- **Runtime:** candidate wheel `project_standards-5.3.0-py3-none-any.whl` via the dogfood pattern (`PYTHONPATH=build/wheel-runtime`), invoked from scratchpad copies of each consumer repository (`rsync` excluding `.git`).
- **Scenarios:** 12 straight v4-to-v5 migrations covering every package mix present in the fleet, 2 ownership-relinquishment variants exercising the new 5.3.0 `*_ownership` options on customized CI files, 3 fresh adoptions.
- **Consumer realism:** agents were restricted to the public docs (`UPGRADING.md`, `README.md`, `standards/**`). Any step requiring guesswork or source reading was itself recorded as a docs finding.
- **Verification:** every deduplicated cluster re-reproduced from a fresh copy by a skeptical verifier empowered to rule `NOT_REPRODUCIBLE`, `AGENT_ERROR`, or `BY_DESIGN`, with severity adjustment in both directions.

## Audit-integrity notes

- Four "the real source repo is contaminated" findings were mis-attributions: runtime-retried agents re-`rsync`ed over their own already-migrated scratch copies without `--delete` and blamed the source. A full sweep of `~/projects/` found no `.standards/`, no `migration-plan.json`, and no audit-caused modification in any real repository. The two deleted `.code-workspace` files in `network-infrastructure{,-schema}` predate the audit (repo-root mtimes 2026-07-13).
- Verifier-corrected findings are retained below with their corrected verdicts rather than silently dropped, so the correction survives.

## Blockers (verified)

Real released consumers blocked, or every adopter's CI broken, with no documented escape.

| # | Cluster | Affected real repos | Verdict |
| --- | --- | --- | --- |
| B1 | `markdown_tooling.version: "1.0"` hard-aborts preview: `CP-MIGRATION-STATE "configured package options are invalid"` with no field, value, or hint, masking all other findings | Claude-Code-Plugins, control-center, docmend, homelab, agent-handoff-v3 | CONFIRMED blocker (Fable + Sonnet) |
| B2 | `CP-MALFORMED-CONTAINER` blocks migration on v4's own `(project-standards: python-tooling)` heading or literal `project-standards:` prose in `CLAUDE.md`/`AGENTS.md`; undocumented, misattributed | control-center (both scenarios) | CONFIRMED blocker (Sonnet) |
| B3 | Reconcile writes `.vscode/{tasks,settings,extensions}.json` as compact single-line JSON that fails the package's own generated Prettier workflow (`format.yml`, root globs, triggers on push) — every adopter with managed VS Code units goes red on first push | agent-configs, network-infrastructure-schema; generic to all adopters | CONFIRMED, upgraded to blocker (Sonnet) |

**B1 root cause (Sonnet source trace):** no shipped markdown-tooling schema accepts `contract_version` 1.0 (`const: "1.1"` in 1.2-1.5) while the migration provider copies the legacy pin verbatim. `plan_legacy_migration` already degrades this to a designed `CP-MIGRATION-CONFIG` finding with a hint, but `plan_reconciliation` re-validates the same config via `_resolve_enabled` (`control_plane/resolution.py:478`), whose `ControlPlaneConfigurationError` is uncaught — it aborts the preview and discards the entire accumulated findings list. Patching the legacy pin to 1.1 yields a rich, correct findings list, proving the pipeline works once the unguarded second validation is fixed.

**B3 root cause (Sonnet source trace):** both python-tooling and markdown-tooling providers render JSON semantic units with `json.dumps(..., separators=(",", ":"))`; the shared jsonc adapter (`control_plane/adapters/jsonc.py`) splices fragment text verbatim, so the defect is generic to every JSON-family composed target.

## Major (verified)

| # | Cluster | Affected | Verdict |
| --- | --- | --- | --- |
| M1 | Stale v4 job left in `validate-standards.yml` beside the new v5 job; CI breaks referencing the deleted `.project-standards.yml` | agent-pseudocode, homelab, network-infrastructure | CONFIRMED (Sonnet) |
| M2 | Migration-created `docs/usage.md` immediately fails the documented post-migration `validate` gate; editing the consumer-editable file then triggers `CP-DRIFT` | agent-pseudocode (+ cli-owned variant) | CONFIRMED (Fable + Sonnet) |
| M3 | `reconcile --check` exits 1 with zero diagnostics when a create-only target drifts from its lock digest | doc-proc-scripts, fresh scenarios | CONFIRMED (Fable) |
| M4 | Managed `CLAUDE.md`/`AGENTS.md` instruction blocks violate the package's own managed markdownlint rules (second H1 / MD025; 14 errors in agent-configs) | agent-configs, cc-usage-monitor, network-infrastructure-schema, Markdown-Keeper | CONFIRMED (Sonnet) |
| M5 | Customized `.markdownlint.json` blocks migration with no ownership escape, incl. a unicode-escape-only (semantically identical) diff | Claude-Code-Plugins, control-center, homelab | CONFIRMED (Sonnet) |
| M6 | Ownership-escape gaps in more packages: project-spec `validate-specs.yml` (one-comment diff blocks) and consumer-authored `docs/usage.md` (only remedy discards authored content) — same class as issues #12/#13 | docmend, doc-proc-scripts | CONFIRMED (Fable + Sonnet) |
| M7 | Documented `fix` step stales the lock; `validate` then fails `CP-DRIFT`; remedy (`reconcile --apply`) undocumented | l3digital, agent-pseudocode-cli-owned, network-infrastructure-schema | CONFIRMED (Fable + Sonnet) |
| M8 | Human-readable output omits path/identity/hint on all five `cli.py` finding call sites (JSON carries them); some findings print literal unexpanded `$target`/`$file` placeholders; duplicate lines per path | all migration scenarios | CONFIRMED (Fable 4x + Sonnet trace) |

## Downgraded and by-design (verifier corrections)

| Cluster | Original | Corrected verdict |
| --- | --- | --- |
| `CP-MIGRATION-PLATFORM-VERSION` on absent `standards_version` key or full release tags (`v4.3.0`, `v3.0.0`, `v1.2.0`) | blocker | PARTIALLY_CONFIRMED, minor: UPGRADING.md's table documents the one-line remedy and it verifiably works for both cases. Residue: the doc's claim that released CLIs wrote `"v3"` is empirically false (real repos hold full tags or no key), and the hint is JSON-only (M8). |
| python-tooling forces `[build-system] uv_build`; "no consumer escape for pyproject units" | major | PARTIALLY_CONFIRMED, minor: no `"none"` backend exists and `[build-system]` is written unconditionally, but the load-bearing "no escape" claim is refuted — `[tool.uv] package = false` is unclaimed by any contribution, survives reconcile untouched, and makes real `uv sync` succeed. The six pyproject `CP-CONSUMER-CONFLICT` units follow the documented align-or-remove contract. Residue: the `tool.uv` escape is undocumented. |
| Post-migration `validate` fails 8 previously-passing docs on v1-era frontmatter IDs | major | BY_DESIGN, minor: the typed-ID grammar shipped in v3.0.0 as a documented MAJOR change with remedy `validate-id --fix`; pre-existing debt surfaced by re-pinning, not a migration regression. |
| Family `adopt.md` banners and README package table lag the 5.3.0 catalog | docs | BY_DESIGN: `meta/versioning.md` §Release requirements defers version-pin bumps to the release commit on `main`; they are pending release-prep steps, not omissions. |
| `spec validate`/`spec lint` exit 2 when an enabled package matches zero files | minor | BY_DESIGN (Fable). |
| Refused `init --migrate --apply` output byte-identical to preview; no refusal statement | minor | CONFIRMED minor (Sonnet). |

## Docs and minor residue

- `UPGRADING.md` has no row for `CP-MIGRATION-STATE` (B1) or the cli-documentation usage-doc digest finding; it still pins/verifies 5.2.0 (release-prep step); `CP-CONSUMER-CONFLICT` guidance says "align with the package value" without ever stating that value (Fable CONFIRMED).
- A failing migration preview silently omits the legacy-retirement remove actions from its plan listing (Fable CONFIRMED, minor — the plan looks more complete than it is).
- Residue and noise: documented `--json > migration-plan.json` preview leaves the file in the worktree with no cleanup guidance; `validate` prints nothing on success; no-op `reconcile --apply` claims "lock updated last"; duplicate `coverage[toml]` in the rendered dev group; generated workflow serializes keys alphabetically; empty `.agents/agent-handoff/` dir left after legacy lock removal; migration silently adds an undeclared `**/*.template.md` frontmatter exclude.

## What worked

- Both relinquishment scenarios — the actual 5.3.0 fix — completed on real repos: customized `check.yml`, `scripts/check.py`, and `cli-docs-check.yml` preserved byte-for-byte via the new `*_ownership` options, with idempotent reconciles and clean legacy retirement.
- Legacy authority retirement (`.project-standards.yml` removal) matched the documented contract in every scenario that reached apply.
- Fresh `init --catalog 5` plus package enablement plus converged reconcile worked end to end on unadopted repos.
- The `CP-MIGRATION-PLATFORM-VERSION` and pyproject flows resolved cleanly once their documented (or discoverable) remedies were applied — evidence the contract design is sound where the escape hatch exists and is documented.

## Implications for the 5.3.0 release

At `e69831f`, the relinquishment fix was sound but the three verified blockers remained: B1 stopped five real consumers before preview (and its unguarded exception path suppressed all other diagnostics), B2 stopped consumers whose agent files mentioned `project-standards:` in prose, and B3 put new adopters' CI red on first push. M5/M6 continued the issue #12/#13 pattern for `.markdownlint.json`, the project-spec workflow, and the usage doc. The owner held the release and selected the expanded 5.3.0 remediation recorded below.

## Remediation outcome

The held 5.3.0 candidate now addresses every audit finding. Released 5.2 payload directories remain byte-identical; compatible successor payloads carry consumer-visible package changes. The engine and package changes each received an independent no-findings re-review after corrections. The repository's Catalog 5 dogfood state was regenerated from the released 5.2 baseline into the amended 5.3.0 candidate.

Final local verification used one freshly built and extracted 5.3.0 wheel: 3,030 ordinary tests, all 80 catalog-derived compatibility rows, 5 performance tests, 90% branch coverage, strict Ruff/BasedPyright checks, all package graph/schema/projection/catalog gates, 8 coherence tests, and `pip-audit` pass.

### Verified blockers and majors

| Finding | Disposition |
| --- | --- |
| B1 | Fixed. Migration normalizes the released Markdown Tooling 1.0 legacy contract to 1.1. Invalid provider configuration produces an inapplicable `CP-MIGRATION-CONFIG` plan while retaining all accumulated findings instead of escaping through a second resolution pass. |
| B2 | Fixed. Markdown marker recognition is bounded to actual managed-marker syntax; ordinary `project-standards:` prose no longer produces `CP-MALFORMED-CONTAINER`. |
| B3 | Fixed. Fresh JSON/JSONC targets use deterministic formatter-compatible rendering. Existing consumer lexical bytes remain untouched outside managed changes. A deterministic 10,000-value oracle reached a Prettier 3.8.3 fixed point with zero mismatches. |
| M1 | Fixed conservatively. Migration packages may declare exact known historical YAML units. The Project Specification migration retires only the released legacy job signature, preserves unrelated jobs, and blocks unknown or modified candidates. |
| M2 | Fixed. CLI Documentation 1.3 now emits a schema-valid typed usage-document ID and exposes `usage_ownership`; Markdown Frontmatter 1.4 excludes declared package templates, harness instructions, workflows, and handoff state/TODO from consumer frontmatter enforcement. |
| M3 | Fixed. Create-only byte drift produces a path-bearing diagnostic while genuine lock-only drift remains distinguishable. No-op and lock-only apply summaries now describe what happened. |
| M4 | Fixed. Agent Handoff 1.3, Markdown Tooling 1.5, and Python Tooling 1.4 wrap their bounded H1 blocks with local MD025 directives. The reconciled root instruction files use the same managed bytes. |
| M5 | Fixed. Markdown Tooling 1.5 adds `markdownlint_config_ownership`; consumer-owned lint configuration is preserved and excluded from package verification without suppressing self-hosted workflow inference. |
| M6 | Fixed. Project Specification 1.3 adds `workflow_ownership`, and CLI Documentation 1.3 adds `usage_ownership`; both relinquish only the selected target while preserving consumer bytes. |
| M7 | Fixed in the runbook. The documented sequence now runs `reconcile --apply` after authoring fixes and refreshes `uv.lock` when dependency-group changes require it. |
| M8 | Fixed. Human findings include severity, concrete path, identity, and hint; internal `$file`/`$target` scopes are hidden; duplicate human warnings are collapsed while JSON retains source provenance. |

### Corrected, by-design, and minor findings

| Finding group | Final disposition |
| --- | --- |
| Platform-version history | Documentation corrected to describe absent keys and full released tags and to give the exact normalization. |
| Non-package Python consumers | `[tool.uv] package = false` is now documented as the supported escape while the bounded package-owned tables retain align-or-remove semantics. |
| Typed frontmatter IDs | By design. The existing fix path remains authoritative and is now placed in the complete post-migration sequence. |
| Release banners and version pins | By design. They remain release-commit changes under `meta/versioning.md`, not candidate-remediation changes. |
| Zero matched specification files | By design. `spec validate` and `spec lint` retain their non-vacuous exit contract. |
| Refused migration apply | Fixed. Human and JSON output explicitly identify the refusal and report that no writes occurred. |
| Missing conflict values and option location | Fixed. The migration table and package-option map document the relevant values, ownership keys, and placement. |
| Hidden retirement actions | Fixed. Blocked previews retain safe conditional legacy-retirement actions with complete control-file metadata and comparable content digests. Apply still refuses every write while blocked. |
| Temporary report file | Fixed. The runbook writes the report to a temporary path and includes cleanup. |
| Successful validation silence | Documented as success behavior. |
| Misleading no-op apply message | Fixed with distinct no-op, lock-only, and mutation summaries. |
| Duplicate coverage dependency | Fixed by deterministic dependency de-duplication. |
| Alphabetical generated-workflow keys | By design. Deterministic semantic YAML is the contract; key order is not. |
| Empty legacy Agent Handoff directory | Fixed. The directory is pruned only after known manifest retirement and only when empty. |
| Undeclared template exclusion | Fixed. The default and migration exclusions are declared in the package schema and adoption documentation. |

## Appendix: singleton finding dispositions

The original singleton inventory was independently checked during remediation. Every item is either fixed, documented, or closed as an explicit contract choice.

| Finding | Final disposition |
| --- | --- |
| Agent Handoff scaffolds fail frontmatter validation | Fixed by Agent Handoff 1.3 plus the declared Frontmatter 1.4 exclusions. |
| Dev dependency-group remedy fails | Not reproduced. The align-or-remove route is covered by real provider and reconciliation tests; `uv lock` is now explicit. |
| Arbitrary consumer workflow still reads legacy config | Documented inventory responsibility; the exact known managed workflow unit is safely retired by M1. |
| Copy-adopted ADR drops from governance | Fixed in documentation: ADR validation is an explicit package-enable choice. |
| Package-option placement and key set absent | Fixed in the migration option map. |
| Older-major stock CI described as customized | Fixed: guidance now distinguishes released historical bytes, consumer customization, and ownership relinquishment. |
| `.editorconfig` said to resolve automatically | Fixed: documentation now describes property-level conflicts and align-or-remove behavior. |
| Relinquished files absent from preview | Fixed: preserve actions and human summaries explicitly identify retained consumer-owned files. |
| Missing `uv.lock` refresh | Fixed in the runbook. |
| Agent Handoff caps and warning volume | Fixed in documentation: hard-cap semantics, pre-existing-content handling, and targeted commands are explicit. |
| Half-applied recovery undocumented | Fixed. `init --migrate` is the migration recovery route; `reconcile --repair-state` remains limited to incomplete unified-control state. |
| Local Markdown tool prerequisites absent | Fixed. Node/npm installation and local `npx` requirements are explicit. |
| Enable default, preview exit, and `preserve` verb absent | Fixed in `docs/usage.md` and `UPGRADING.md`. |
| No raw content diff in preview | By design for bounded output and secret safety; comparable before/after digests, modes, identities, and summaries are provided. |
| Stale dual-authority plan and misleading error | Fixed. Only exact known control-file prefixes qualify as interrupted migration, and stale plan metadata is rejected at apply time. |
| Plan metadata and control-file actions inaccurate | Fixed. Control actions, content digests, modes, summaries, and counts reflect the actual before/after state. |
| ADR fix disagrees with validate | Fixed. Valid ADR IDs are accepted before the invalid-ADR manual branch, and output no longer reports contradictory actions. |
| Unused generated `scripts/check.py` | By design. It is the package's local gate artifact and has independent ownership from consumer CI. |
| VS Code check ignores script ownership | Fixed. The managed task delegates to the consumer-owned script. |
| ADR scaffold path fixed at `docs/adr/` | By design and explicitly documented by the ADR package. |
| `python_version` controls interpreter and tool targets | By design: one baseline prevents internally inconsistent generated tooling. |
| Duplicate bounded-takeover warning | Fixed in human output; JSON retains distinct provenance records. |
| `standards list` lacks selection facts | Fixed. Text output shows enablement, availability/selectability, default, requested, and resolved versions. |
| Re-running `init` lacks diagnosis | Fixed with `CP-INIT-STATE` and actionable routing. |
| Apply action count differs from preview | Fixed. Summaries count adopted, updated, removed, preserved, and lock publication consistently. |
