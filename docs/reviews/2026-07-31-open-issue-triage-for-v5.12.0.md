---
schema_version: '1.1'
id: 'reference-o8k0xv-open-issue-triage-for-v5-12-0'
title: 'Open-Issue Triage for the v5.12.0 Release Train'
description: 'Owner-approved roll-in/defer disposition for all 32 open issues ahead of the v5.12.0 release that ships the MCP server.'
doc_type: 'reference'
status: 'active'
created: '2026-07-31'
updated: '2026-07-31'
reviewed: '2026-07-31'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'agent'
tags:
  - 'triage'
  - 'release'
---

# Open-Issue Triage for the v5.12.0 Release Train

Owner decision 2026-07-31: roll the Tier 1 and Tier 2 sets below into v5.12.0 in a fresh session. Tier 3 is conditional on timeline; Tier 4 defers. All 32 open issues (#55, #62, #75–#77, #78–#104) were distilled with per-issue source verification; #75/#76/#77, #88/#95, #100 were grep-confirmed unfixed on `testing` at commit `d180570`.

## Constraints binding the release train

- v5.12.0 ships the MCP server. Standards packages remain locked except minor-level version changes (owner 2026-07-29); released payloads are byte-immutable, so payload fixes ship as new minor payload versions.
- The MCP implementation is verified at commit `4d2ece9`, candidate wheel `8ed0b2e8…`. The release rebuilds and re-runs the full gate regardless (the version bump changes wheel bytes), but control-plane planner/migration/dispatch code is the surface MCP composite tools call through — changes there reopen the largest verification burden and are deferred.
- Frozen canary `TC-T14-004` automatically forces any new provider-bearing payload version to declare its provider-input family; no manual tracking needed.
- Release finalization (version bump, tag, publication) needs its own authorization; this document scopes only which fixes ride along.

## Tier 1 — roll in: docs-only, zero code risk

| Issue | Fix |
| --- | --- |
| #85 | `meta/versioning.md` names 5.10.0 as active. Fix structurally: stop embedding the minor/patch number in prose so the 5.12.0 cut cannot recur it. |
| #92 | Adoption prompt: replace the literal `>migration-plan.json` redirect with the `mktemp` external-file pattern (validated in the issue comments). |
| #93 | Document that markdown verification does not honor `.git/info/exclude` (docs option only). |
| #96 | Transient first `--version` probe failure after forced install: add a retry-once note; likely not fixable in-repo. |
| #103 | Extend the existing #44-style adopt-guide warning to `prettier --write` (upstream Prettier printer bug; warn and recommend first-run diff review). |

## Tier 2 — roll in: low-risk isolated fixes (minor payload bumps or diagnostics-only engine code)

| Issue | Fix | Notes |
| --- | --- | --- |
| #97 | markdown-frontmatter `new-doc-id` script: `python3 -` → `uv run python3 -` (2 call sites); new minor payload version. | Reproduced live on this workstation 2026-07-31 while authoring this document. Precedented by the #80-class fix. |
| #100 | Append `sha256:c6a0217de8adbab6e24038f98577de8fa2f90062b873cc97b6bd2c09f89dba2b` to markdown-tooling `known_content_digests`. | Third instance of the #10/#27 family; digest independently verified. Consider the structural fix as follow-up, not blocker. |
| #94 | agent-handoff credential checker: exempt command-substitution RHS (`TOKEN=$( … )`); name the offending line in the finding. | Isolated checker logic; new minor payload version. |
| #104 | Gitleaks tripping on managed `policy.toml` PEM header patterns: docs-only allowlist subsection in adopt.md. | The pattern re-render option is deferred with Tier 4-adjacent care; issue poses options — docs option chosen for this train. |
| #81 + #82 | `CP-CONSUMER-CONFLICT` hint generation: migration-mode-aware entry point (`init --catalog 5 --migrate`) and the missing markdownlint ownership-option line. | Same code path, one fix covers both; diagnostics text only. Completes the #37 work. |
| #78 | Structured JSONC adapter: strip the whitespace-only line left by obsolete-key removal. | Shared adapter — verify blast radius across packages that use JSONC removal before shipping. |
| #79 | TOML inline-table serialization spacing (`, ci = { performance = true }}` cosmetics). | Cosmetic, idempotent output fix. |

## Tier 3 — conditional: include only if the release timeline allows

- #80 (labeled `bug`, 10+ reproductions): Codex SessionStart hook fails under uv-strict shims. Needs a launcher-strategy decision first — `uv run python3` breaks consumers pinned below Python 3.14. Acceptance criteria are already specified in the issue.
- #88 + #95: markdown-tooling `prettier .` and python-tooling `ruff .` commands exceed declared scope; render bounded path arguments instead. Same defect class, two packages, two minor bumps.
- #99: key-level ownership for `[tool.ruff.lint]` sub-tables (precedented by #40).
- #86: mixed-monorepo layout — docs-only guidance plus a preview finding this train; the new no-implicit-root layout mode is an owner-scoped design item.
- #75: agent-handoff enrichment FIFO mispairing — diagnostics-only fix but needs careful multi-paragraph test coverage.

## Tier 4 — defer past v5.12.0

- Control-plane planner/migration/dispatch: #76, #77, #83, #87, #90, #91, #98, #101 (code half; its docs half may ride Tier 1), #102. Mitigations already in place: #77 fails closed via the #70/`f476c41` guardrail and no shipped payload declares an empty managed artifact; #76 is caught by the same guardrail; #83 has a documented two-phase workaround.
- #102 first needs a live reproduction: `agent_handoff/integrations/codex.py` has carried a `_is_legacy_command` conflict guard since `4cc5efb` (2026-07-09, pre-v5.11.0) that appears to cover the reported scenario — the issue may close with no change.
- #55, #62: explicit owner deferral comments dated 2026-07-27 stand.
- #84: unreproduced transient `yaml.scanner` import failure; monitor only.
