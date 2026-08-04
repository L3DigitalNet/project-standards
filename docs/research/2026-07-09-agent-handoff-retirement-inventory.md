---
schema_version: '1.1'
id: 'reference-6wf7d0-agent-handoff-retirement-inventory'
title: 'Agent Handoff Retirement Inventory'
description: 'Consumer-by-consumer migration ledger and deletion checkpoint for retiring the deprecated agent-handoff engine after Agent Handoff Standard 1.0 adoption.'
doc_type: 'reference'
status: 'active'
created: '2026-07-09'
updated: '2026-08-04'
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
  - 'docs/specs/2026-07-09-agent-handoff-standard-package.md'
  - 'docs/plans/2026-07-09-agent-handoff-standard-package.md'
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
| `Claude-Code-Plugins` | `main` | Migrated from dual registrations/hooks and root companions | Dual | `0fdbd98` | Pass | Recheck with published v5 before deletion |
| `ClaudeCodeStatusLine` | `main` | Ignored, untracked local developer notes; no tracked registration or layout | Not a legacy consumer | — | Not applicable | Deliberate public-distribution boundary; no adoption |
| `HomeBase` | `main` | Migrated from dual hooks and root companions | Dual | `ec3df46` | Pass | Recheck with published v5 before deletion |
| `Markdown-Keeper` | `main` | Migrated from dual hooks and root companions | Dual | `d373df1` | Pass | Recheck with published v5 before deletion |
| `Russ-Estate-Paperwork` | `main` | Migrated from dual hooks and root companions | Dual | `ab71b83` | Pass | Recheck with published v5 before deletion |
| `agent-configs` | `main` | Migrated from dual registrations/hooks and root companions | Dual | `2026-07-26` | Pass (validate + drift-check exit 0) | Recheck with published v5 before deletion |
| `agent-handoff-v3` | `main` | Deprecated engine checkout itself | Not a consumer | — | Not applicable | **Retired 2026-07-30**: GitHub repository archived read-only; local checkout `/home/chris/projects/agent-handoff-v3` deleted. See Deletion checkpoint and Engine record below. |
| `agent-pseudocode` | `main` | Migrated from dual registrations/hooks and root companions | Dual | `21ade51` | Pass | Recheck with published v5 before deletion |
| `cc-usage-monitor` | `main` | Migrated from dual hooks and root companions | Dual | `81d464d` | Pass | Recheck with published v5 before deletion |
| `control-center` | `main` | Migrated from dual hooks and root companions | Dual | `1be92ec` | Pass | Recheck with published v5 before deletion |
| `doc-proc-scripts` | `main` | Migrated from Codex hook, engine references, root companions | Codex | `e1db276` | Pass | Recheck with published v5 before deletion |
| `doc-proc-scripts-kate-decision` | `main` | **Resolved 2026-07-30**: was a Git worktree of `doc-proc-scripts` pinned to local-only branch `codex/kate-integration-model` (tip `2d28849`, 2026-07-07) | Codex | — | Not applicable — artifact removed | Closed: worktree removed and branch deleted 2026-07-30 after proving `main` carried a newer superset of every file on the branch; the artifact no longer exists to inspect |
| `docmend` | `main` | Migrated on required `dev` branch; `main` remains legacy | Dual | `1657e2e` (`dev`) | Pass on `dev` | Closed 2026-08-04 (T32): `dev` and `main` converged (both at `ee6883ce`); recheck published v5 |
| `projects` | `main` | Migrated from zero-byte Codex marker and nonstandard `docs/` handoff layout | Dual | `3da7641`; catalog 5 migration `3fd7aee` (`main`, 2026-07-30) | Pass | Recheck with published v5 before deletion |
| `dotfiles` | `main` | Migrated from dual registrations/hooks and root companions | Dual | `baf8705` | Pass | Recheck with published v5 before deletion |
| `finances` | `main` | Migrated from dual hooks and root companions; historical brief classified | Dual | `f3e1d01` | Pass | Recheck with published v5 before deletion |
| `homelab` | `main` | Migrated from dual registrations/hooks and root companions | Dual | `ceba125` | Pass | Recheck with published v5 before deletion |
| `hw-radar` | `main` | Migrated on required `dev`; root companions and monolith retired | Dual | `cbe77be` (`dev`) | Pass on `dev` | Closed 2026-08-04 (T32): PR #15 merged `dev`→`main` 2026-07-29; `main` contains `dev`; recheck published v5 |
| `l3digital` | `main` | None | Not a legacy consumer | — | Not applicable | None |
| `network-infrastructure` | `main` | None | Not a legacy consumer | — | Not applicable | None |
| `network-infrastructure-schema` | `main` | None | Not a legacy consumer | — | Not applicable | None |
| `progressive-apparel` | `main` | Migrated from Codex hook and root companions | Codex | `2b062b6`; catalog 5 migration `a6adee7` (`main`, 2026-07-30) | Pass | Recheck with published v5 before deletion |
| `project-standards` | `main` | Migration and package adoption are integrated on `testing` | Dual | `bd3cee5` | Pass on `testing` | Promote v5, then recheck the published artifact |
| `star-trek-retro-remake` | `main` | Migrated from dual hooks and root companions | Dual | `9d4e19e` | Pass | Recheck with published v5 before deletion |
| `website-aboutme` | `main` | Migrated on required `testing` branch; `main` remains legacy | Dual | `ab6bc3d` (`testing`); catalog 5 migration `c06dc05` (`testing`, 2026-07-30) | Pass on `testing` | Closed 2026-08-04 (T32): protected merge `testing`→`main` completed via PR #1; recheck published v5 |
| `website-l3digital.net` | `main` | Migrated on required `testing` branch; `main` remains legacy | Dual | `87dabc2` (`testing`); catalog 5 migration `bf27833` (`testing`, 2026-07-30) | Pass on `testing` | Closed 2026-08-04 (T32): protected merge `testing`→`main` completed via PR #1; recheck published v5 |

Summary: 21 repositories had concrete legacy layout or registration evidence, `ClaudeCodeStatusLine` is a resolved local-only non-consumer classification, the deprecated engine (retired 2026-07-30 — see Deletion checkpoint and Engine record) was the final deletion target, and three repositories have no legacy evidence. Fifteen repositories validate on v1 on their default or feature integration branch; `docmend` and `hw-radar` validate on `dev`, while `website-aboutme` and `website-l3digital.net` validate on `testing`. **All four protected merges are complete as of 2026-08-04 (T32):** `docmend` and `hw-radar` converged earlier (branch identity / PR #15), and both website repositories merged `testing`→`main` via their PR #1.

## 2026-07-30 reconciliation

- **No-v3-installations sweep.** Swept every clone under `~/projects` and `~/scripts`, the twelve worktrees under `~/.config/superpowers/worktrees/`, and loose clones under `~/` for a `.claude/`, `.codex/`, or `.agents/` `session_start.py` and for a root `STATUS.md`/`TODO.md` pair. Result: no repository on the machine ran the v3 engine as of 2026-07-30. The final v3 installation found anywhere was the `doc-proc-scripts-kate-decision` worktree (see Consumer ledger, resolved above); it was Codex-side only, which a Claude-path-only search does not detect.
- **Catalog 5 migrations (2026-07-30).** Four repositories migrated to the catalog 5 package: `website-aboutme` (`c06dc05`, `testing`), `progressive-apparel` (`a6adee7`, `main`), `website-l3digital.net` (`bf27833`, `testing`), and the `projects` meta-repo (`3fd7aee`, `main`). Four consumers still owe a protected merge to `main`: `docmend` and `hw-radar` from `dev`, and `website-aboutme` and `website-l3digital.net` from `testing`.
- **Published-release recheck (published `5.11.0`).** 19 of 21 package consumers pass both `validate` and `drift-check` at exit 0. Two exceptions remain, neither a package defect: `llm-wiki` exits 1 on two consumer shape overflows (`docs/TODO.md:29` at 224 characters against a 160 limit, `docs/handoff/state.md:8` at 141 characters against a 140 limit — limits and overflow reported in `llm-wiki`'s own installed copies, not this repository's); `~/scripts` exits 3 with "selected command package is not reconciled: agent-handoff" and needs `reconcile --apply`.
- **Control center note.** `control-center` is the only repository still on a legacy `.project-standards.yml`. This is unrelated to the engine retirement: it is blocked on issue #83 (the V4 Python Tooling package-transform evidence check), and the owner is handling it manually. Its ledger row above should not be read as engine-blocked.

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

Status: **retired 2026-07-30** — engine deletion executed. This section is preserved as the authorization record of how that outcome was reached, not deleted; the original four gates below are dispositioned against what actually occurred, gate by gate.

- **Gate 1 (every consumer migrated and validated) — satisfied for engine retirement, not for full v5 adoption.** Every known consumer that ran the v3 engine has migrated off it (Consumer ledger above; the 2026-07-30 no-v3-installations sweep in "2026-07-30 reconciliation" above found none remaining). Full v5 adoption is not complete: four consumers still owe a protected merge to `main` (`docmend`, `hw-radar` from `dev`; `website-aboutme`, `website-l3digital.net` from `testing`), and two of 21 consumers fail the published-release recheck for reasons unrelated to the engine (`llm-wiki` shape overflows, `~/scripts` needs `reconcile --apply`; see "2026-07-30 reconciliation" above). None of this residual work depends on the engine checkout continuing to exist. **Residual work closed 2026-08-04 (T32):** all four protected merges are complete (ledger rows above), `llm-wiki`'s shape overflows are resolved (`agent-handoff validate` exits 0; the two inventoried lines no longer exist), and `~/scripts` reconciles clean (`ok: true, drift: false`) with no apply needed.
- **Gate 2 (released package passes the disposable probes against its published artifact) — satisfied.** `agent-handoff` shipped in the published `5.11.0` release; the published-release recheck above confirms 19 of 21 consumers pass `validate` and `drift-check` at exit 0 against it, with the two exceptions being consumer-side, not package defects.
- **Gate 3 (final operational-dependency search is clean) — not run inside this repository at decision time; run now as this repository's own dated evidence.** The 2026-07-30 read-only cross-repository sweep referenced in the owner's TODO task was not captured as `project-standards`'s own evidence. Run 2026-07-30 inside this repository:

  ```bash
  git ls-files | xargs grep -lIE 'agent-handoff-v3|handoff-system-v3' 2>/dev/null | wc -l
  git ls-files | xargs grep -lIF '/home/chris/projects/agent-handoff-v3' 2>/dev/null
  ```

  Result: 31 tracked files mention `agent-handoff-v3` or `handoff-system-v3` by name (name-only detection strings, `legacy-migration.md` resource mirrors, and archival design/session records — none requires the checkout to exist or to be readable). Only 4 files pin the literal local path `/home/chris/projects/agent-handoff-v3` as evidence: `docs/TODO.md`, `docs/plans/2026-07-09-agent-handoff-standard-package.md`, `docs/research/2026-07-09-agent-handoff-ingestion-inventory.md`, and this file — all four are documentation pins annotated as no longer locally resolvable (see the dangling-pin annotations in those files and above), not runtime dependencies. **Discrepancy flagged:** the owner's TODO task states "25 tracked files mention it"; this repository's own 2026-07-30 sweep found 31. The most likely explanation is that the TODO's count did not include the 6 `src/project_standards/payloads/agent-handoff/1.1`–`1.6/resources/legacy-migration.md` generated payload mirrors (31 − 6 = 25), but that was not independently confirmed. Either count supports the same conclusion: no tracked file in this repository requires the deleted checkout.

- **Gate 4 (owner explicitly approves deletion) — satisfied.** The owner directed the 2026-07-30 retirement: the private GitHub repository `chrisdpurcell/agent-handoff-v3` was archived read-only, and the local checkout `/home/chris/projects/agent-handoff-v3` was deleted.

**Reversibility note:** archiving the GitHub repository is reversible (an owner can unarchive it at any time); the local checkout deletion is not — the archive is now the only remaining source for anything not preserved elsewhere (see "Engine record (archive-only facts)" below).

## Engine record (archive-only facts)

These facts exist in no active repository and otherwise require re-cloning the archive. Preserved here verbatim from the owner's 2026-07-30 retirement-reconciliation task record.

- Final engine HEAD was `11ccbf7` (2026-07-27), and the pinned evidence commit was `56b24df7279572c485c2512783b0cc7e5395429b`.
- Schema version was 3.4.
- The engine was **dual-harness**: one canonical hook installed byte-identically to both `.claude/hooks/session_start.py` and `.codex/hooks/session_start.py`, with the Codex side registered in `.codex/config.toml` under `[[hooks.SessionStart]]` as `bash -c 'python3 "$(git rev-parse --show-toplevel)/.codex/hooks/session_start.py"'`.
- Its layout was root `STATUS.md` and `TODO.md` beside `docs/handoff/{state,deployed,architecture,credentials,conventions,specs-plans}.md`, `docs/handoff/sessions/`, and `docs/handoff/bugs/`, with a repo-local skill directory named `handoff-system-v3`.
- Its validators lived at `agent-handoff-v3/scripts/handoff/` as `validate-layout.sh` (18,502 bytes), `_handoff-lib.sh` (5,168 bytes), `validate-shape.sh` (267 bytes), and `size-report.sh` (261 bytes).
- Its specification was `docs/specs/agent-handoff-v3.md` at 746 lines and 64,831 bytes.
- No copy was taken into any active repository, so the read-only GitHub archive is the only remaining source for it and for the four validator scripts.
