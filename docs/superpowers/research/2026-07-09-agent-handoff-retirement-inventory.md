---
schema_version: '1.1'
id: 'reference-6wf7d0-agent-handoff-retirement-inventory'
title: 'Agent Handoff Retirement Inventory'
description: 'Consumer-by-consumer migration ledger and deletion checkpoint for retiring the deprecated agent-handoff engine after Agent Handoff Standard 1.0 adoption.'
doc_type: 'reference'
status: 'active'
created: '2026-07-09'
updated: '2026-07-09'
reviewed: null
owner: 'project-standards'
consumer: 'agent'
tags:
  - 'agent-handoff'
  - 'inventory'
  - 'migration'
  - 'retirement'
aliases:
  - 'agent-handoff consumer inventory'
related:
  - 'docs/superpowers/specs/2026-07-09-agent-handoff-standard-package.md'
  - 'docs/superpowers/plans/2026-07-09-agent-handoff-standard-package.md'
  - 'standards/agent-handoff/resources/legacy-migration.md'
  - 'docs/adr/adr-0022-standard-packaged-hook-installation-methodology.md'
source: []
confidence: 'high'
visibility: 'internal'
license: null
---

# Agent Handoff Retirement Inventory

This is the deletion gate for the deprecated Agent Handoff engine. It inventories current local repositories, but it does not authorize bulk writes or deletion. Each consuming repository must migrate through its own reviewed change set, and the owner must approve deletion after every known consumer validates against the released v1 package.

## Inventory method

- Snapshot date: 2026-07-09.
- Workspace source: `/home/chris/projects/projects.sh status --json`, covering 26 managed repositories plus its tracked topic worktree.
- Evidence source: the feature branch's read-only `project-standards agent-handoff legacy-report --repo <path> --json` against every row.
- Knowledge-base check: llm-wiki contains a draft repo-local/global handoff stub but no maintained consumer inventory; this ledger is therefore canonical.
- Classification: registrations, per-harness hook copies, root companions, symlink layouts, and old engine/config references are evidence only. The local agent must decide what to preserve.
- Safety: no consumer was mutated by the scan. Dirty repositories and topic/no-upstream branches remain inventory-only.

## Consumer ledger

| Repository | Default branch | Current legacy evidence | Target profile | Migration change | v1 validation | Remaining blocker |
| --- | --- | --- | --- | --- | --- | --- |
| `Claude-Code-Plugins` | `main` | Dual registrations/hooks; root status/tasks | Dual | — | Pending | Repo-local reviewed migration |
| `ClaudeCodeStatusLine` | `main` | Instruction reference plus `handoff.md` | Determine locally | — | Pending | Classify evidence before adoption |
| `HomeBase` | `main` | Migrated from dual hooks and root companions | Dual | `ec3df46` | Pass | Recheck with published v5 before deletion |
| `Markdown-Keeper` | `main` | Migrated from dual hooks and root companions | Dual | `d373df1` | Pass | Recheck with published v5 before deletion |
| `Russ-Estate-Paperwork` | `main` | Dual registrations/hooks; root status/tasks | Dual | — | Pending | Repo-local reviewed migration |
| `agent-configs` | `main` | Dual registrations/hooks, engine references, root companions | Dual | — | Pending | Dirty owner work; inventory-only |
| `agent-handoff-v3` | `main` | Deprecated engine checkout itself | Not a consumer | — | Not applicable | Final deletion target; owner checkpoint required |
| `agent-pseudocode` | `main` | Dual registrations/hooks; root status/tasks | Dual | — | Pending | Repo-local reviewed migration |
| `cc-usage-monitor` | `main` | Migrated from dual hooks and root companions | Dual | `81d464d` | Pass | Recheck with published v5 before deletion |
| `control-center` | `main` | Migrated from dual hooks and root companions | Dual | `1be92ec` | Pass | Recheck with published v5 before deletion |
| `doc-proc-scripts` | `main` | Migrated from Codex hook, engine references, root companions | Codex | `e1db276` | Pass | Recheck with published v5 before deletion |
| `doc-proc-scripts-kate-decision` | `main` | Codex registration/hook; root status/tasks | Codex | — | Pending | Protected no-upstream topic worktree; inventory-only |
| `docmend` | `main` | Dual registrations/hooks; root status/tasks | Dual | — | Pending | Current `dev` branch requires repo-local review |
| `docs` | `main` | Symlinked Codex layout, `docs/state.md`, handoff references | Determine locally | — | Pending | Reconcile nonstandard legacy layout |
| `dotfiles` | `main` | Dual registrations/hooks; root status/tasks | Dual | — | Pending | Repo-local reviewed migration |
| `finances` | `main` | Dual registrations/hooks, root companions, handoff-like document | Dual | — | Pending | Classify extra handoff document |
| `homelab` | `main` | Dual registrations/hooks; root status/tasks | Dual | — | Pending | Repo-local reviewed migration |
| `hw-radar` | `main` | Dual registrations/hooks, root companions, monolithic handoff | Dual | — | Pending | Current `dev`; reconcile monolith locally |
| `l3digital` | `main` | None | Not a legacy consumer | — | Not applicable | None |
| `network-infrastructure` | `main` | None | Not a legacy consumer | — | Not applicable | None |
| `network-infrastructure-schema` | `main` | None | Not a legacy consumer | — | Not applicable | None |
| `progressive-apparel` | `main` | Migrated from Codex hook and root companions | Codex | `2b062b6` | Pass | Recheck with published v5 before deletion |
| `project-standards` | `main` | Old layout remains in dirty `testing` checkout; feature branch migrated | Dual | `bd3cee5` | Pass on feature branch | Integrate v5 feature branch |
| `star-trek-retro-remake` | `main` | Dual registrations/hooks; root status/tasks | Dual | — | Pending | Repo-local reviewed migration |
| `website-aboutme` | `main` | Migrated on required `testing` branch; `main` remains legacy | Dual | `ab6bc3d` (`testing`) | Pass on `testing` | Merge `testing` through the repo's protected flow; recheck published v5 |
| `website-l3digital.net` | `main` | Dual registrations/hooks; root status/tasks | Dual | — | Pending | Repo-local reviewed migration |

Summary: 21 repositories had concrete legacy layout or registration evidence, two rows require classification (`ClaudeCodeStatusLine` and the deprecated engine itself), and three have no legacy evidence. Seven repositories validate on v1 on their integration branch; `website-aboutme` also validates on `testing` but still needs its protected merge. Fourteen concrete-evidence default branches remain.

## Installed-wheel verification

Checked 2026-07-09 against the official [Claude Code Hooks reference](https://code.claude.com/docs/en/hooks) and [Codex Hooks reference](https://developers.openai.com/codex/hooks). The candidate wheel was built from this feature branch, installed into a disposable virtual environment with `PYTHONPATH` empty, and exercised from four temporary Git repositories outside the source checkout.

| Profile | Adoption | Validation | Hook transport probe |
| --- | --- | --- | --- |
| Claude-only | 17 creates, 0 errors | 0 findings | JSON `SessionStart` additional context; 1,063 bytes |
| Codex-only | 17 creates, 0 errors | 0 findings | Plain stdout developer context; 947 bytes |
| Dual | 19 creates, 0 errors | 0 findings | Claude 1,089 bytes; Codex 972 bytes |
| Manual | 15 creates, 0 errors | 0 findings | No hook or harness registration installed |

All automatic probes loaded the repository marker from `docs/handoff/state.md`, used the installed hook path as repository authority, and stayed below the 4,096-byte total output ceiling. The import resolved from the disposable environment's `site-packages`, proving the wheel does not require the source or deprecated engine checkout.

## Acceptance baseline

- Pass: npm audit; Ruff format/check; BasedPyright strict; 1,368 tests; 94% coverage; pip-audit; 8 coherence tests; frontmatter; spec validate/lint; standards graph; catalog freshness.
- Known unchanged broad Markdown backlog: Prettier reports two files under `docs/future-standards/`; markdownlint reports 463 errors confined to `docs/future-standards/**`.
- Required release condition: every file changed for Agent Handoff must pass targeted Prettier and markdownlint checks even while that unrelated backlog remains.

## Deletion checkpoint

Status: **blocked**.

- Consumer migrations and per-repository validation are incomplete.
- The candidate wheel is clone-independent, but v5.0.0 is not yet released and verified from its published artifact/ref.
- The final operational-dependency search has not been run after all migrations.
- Owner approval has not been requested because the preceding gates are not satisfied.

Do not delete `/home/chris/projects/agent-handoff-v3` or its remote repository until every ledger row is resolved, the released package passes the disposable probes, the final search is clean, and the owner explicitly approves deletion.
