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

The relinquishment fix is sound, but three verified blockers remain at `e69831f`: B1 stops five real consumers before preview (and its unguarded exception path suppresses all other diagnostics), B2 stops any consumer whose agent files mention `project-standards:` in prose, and B3 puts every new adopter's CI red on first push. M5/M6 continue the issue #12/#13 pattern for `.markdownlint.json`, the project-spec workflow, and the usage doc. Decision required before release: expand 5.3.0 scope to cover the blockers (B1 is an engine guard + provider mapping fix; B3 is a provider serialization fix), or ship as-is and file them. The docs residue belongs in 5.3.0 release prep either way.

## Appendix: unverified singleton findings

Unique findings reported by one or two scenarios that were not individually re-verified. Treat severities as reported, not confirmed.

| Finding | Severity | Scenario(s) |
| --- | --- | --- |
| Converged fresh adoption immediately fails `validate`: agent-handoff's own generated scaffolds lack required frontmatter (M2-adjacent, different package) | major | fresh-l3digital |
| Documented resolution for the pyproject dev dependency-group conflict does not clear it (note: the Sonnet pyproject verifier resolved a dev-group conflict successfully in another repo, so this may be reporter error) | major | fresh-network-infra-schema |
| Migration leaves a consumer-authored workflow that reads `.project-standards.yml` untouched — orphaned automation beyond the managed caller (M1-adjacent) | major | agent-configs |
| V4 copy-adopted ADR standard silently drops out of governance during migration | docs | docmend |
| Where package options (for example the `*_ownership` keys) go in the legacy YAML during migration is undocumented, as is the accepted key set | docs | agent-configs, control-center |
| Stock-but-older-major released CI bytes (v2-era callers, `@v3` pins) hit the legacy-digest block with guidance written only for "customized" files | docs | agent-handoff-v3, control-center |
| UPGRADING.md claims `.editorconfig` customizations "resolve automatically", but property-level conflicts still hard-block | docs | agent-pseudocode-cli-owned |
| Relinquished consumer-owned files are silently absent from the migration plan instead of being explicitly confirmed as preserved | docs | agent-pseudocode-cli-owned |
| UPGRADING.md omits the `uv.lock` refresh required after migration rewrites the dev dependency group | docs | agent-configs, docmend |
| UPGRADING step-4 `agent-handoff validate` fails on pre-existing consumer content (byte caps), the error buried under ~300 warnings; migrated AGENTS.md itself exceeds the 4096-byte cap; elsewhere hard-cap violations warn but exit 0 | docs | homelab, doc-proc-scripts, claude-code-plugins, docmend, fresh-l3digital |
| Recovery from a half-applied migration works but is entirely undocumented | docs | network-infrastructure |
| markdown-tooling verify commands assume `markdownlint-cli2`/`prettier` are installed; no doc says how | docs | fresh-network-infra-schema |
| `standards enable` defaulting to latest, the reconcile preview exit-1 contract, and the plan verb `preserve` are undocumented | docs | fresh-l3digital, fresh-claudecodestatusline |
| No content diff for composed targets before apply; preview shows only digests and unit counts | minor | agent-configs, fresh-network-infra-schema |
| Bare `CP-STALE-PLAN` (divergent pre-existing `.standards/` beside legacy YAML) is undocumented; the dual-authority state reports an unrelated package-options error | minor | cc-usage-monitor, claude-code-plugins |
| Plan metadata oddities: boilerplate per-action summaries; `.standards/{config,catalog,lock}.toml` creation never listed; no-op actions report `before_digest != after_digest`; `before_digest` does not match observed pre-migration bytes | minor | cc-usage-monitor, markdown-keeper, website-aboutme |
| `fix` and `validate` disagree: `fix` demands manual ADR-id repairs that `validate` accepts, and prints "skipped" then "formatted" for the same file | minor | agent-pseudocode, network-infrastructure, fresh-claudecodestatusline |
| Migration creates `scripts/check.py` in a repo that never had one and whose consumer-owned CI never calls it | minor | agent-handoff-v3 |
| Managed VS Code "check" task is rewritten to inline commands even with `script_ownership = consumer-owned` | minor | agent-configs |
| ADR template created at fixed `docs/adr/` path, ignoring the repo's `docs/decisions/` layout | minor | control-center |
| `python_version` option couples the interpreter pin and lint/type targets in one knob | minor | control-center |
| Duplicate `CP-MIGRATION-BOUNDED-TAKEOVER` warning emitted twice for `.editorconfig` in one plan | minor | control-center-relinquish |
| `standards list` text output shows no versions, defaults, or selectability; reference-only families indistinguishable from consumer-selectable ones | minor | fresh-claudecodestatusline |
| `init --catalog 5` on an already-adopted repo gives a terse error with no diagnosis | minor | fresh-claudecodestatusline |
| Apply reports fewer actions than the preview plan listed (adopts not counted) | minor | fresh-claudecodestatusline |
