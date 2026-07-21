# Legacy Handoff Migration

Use the unified V5 `init --migrate` flow first. It automatically imports only exact Agent Handoff v1 configuration, bounded blocks, managed artifacts, and provenance-lock evidence. Use this guide for older or locally modified layouts that the fail-closed automatic migration refuses; those repositories still require human classification because their structure, local edits, and fact placement differ.

The standard owns no global environment. Every command and inspection in this guide is scoped to the adopting repository. Removing a retired checkout, home-level hook, or global skill is separate owner work after all consumers have migrated.

## Safety rules

- Start from a reviewed worktree. Preserve or commit local edits that overlap status, task, hook, skill, or configuration paths.
- Treat the legacy report as evidence, not a migration plan.
- Never emit or copy credential values. Preserve only environment-variable names, secret names, OpenBao paths, and retrieval instructions.
- Do not create a migration manifest, quarantine tree, conflict ledger, or automated content classifier.
- Remove legacy files only after useful content is preserved, v1 validates, and the diff is reviewed.

## 1. Inventory the repository

Run the read-only report before changing files:

```bash
project-standards agent-handoff legacy-report --repo . --json
```

Review every recognized and unclassified finding. Also inspect the repository history when two files appear to own the same fact. The report does not read home directories, sibling repositories, Git remotes, or the retired implementation checkout.

Common historical families include:

| Evidence | Typical meaning | Required judgment |
| --- | --- | --- |
| Root `STATUS.md` or `TODO.md` | Legacy builder-facing companions | Preserve current facts and user-owned tasks under `docs/`. |
| `docs/state.md` or `docs/handoff.md` | Older eager or monolithic state | Split facts by lifetime; do not copy the document wholesale. |
| Both `docs/state.md` and `docs/handoff/state.md` | Partial or mixed-generation migration | Reconcile conflicting current facts before deleting either source. |
| `.claude/hooks/session_start.py` or `.codex/hooks/session_start.py` | Per-harness hook copies | Retire only after the shared v1 hook and registration work. |
| `.agents/skills/handoff-system-v3/` or another old skill name | Retired repo-local operating procedure | Preserve legitimate local guidance, then adopt `.agents/skills/agent-handoff/`. |
| Stale settings, config, or instruction references | Possible duplicate startup injection | Reconcile handlers and remove old identities before trusting v1. |
| Unclassified handoff-like files | Unknown local convention | Inspect manually; do not guess a transformation. |

## 2. Preserve and route useful knowledge

Reconcile facts into the canonical v1 locations:

| Fact lifetime or purpose                  | Canonical destination                |
| ----------------------------------------- | ------------------------------------ |
| Current project snapshot                  | `docs/STATUS.md`                     |
| User and agent work queues                | `docs/TODO.md`                       |
| Next-session focus and active incidents   | `docs/handoff/state.md`              |
| Current deployment truth                  | `docs/handoff/deployed.md`           |
| Stable architecture and boundaries        | `docs/handoff/architecture.md`       |
| Credential names and retrieval references | `docs/handoff/credentials.md`        |
| Stable project patterns                   | `docs/handoff/conventions.md`        |
| Active specification and plan pointers    | `docs/handoff/specs-plans.md`        |
| Compact session history                   | `docs/handoff/sessions/<YYYY-MM>.md` |
| Durable bug causes, fixes, and lessons    | `docs/handoff/bugs/<id>-<slug>.md`   |

Prefer the newest supported fact when sources conflict, but preserve ambiguity for owner review. Drop obsolete narrative only after its durable value has been routed.

## 3. Preview V5 reconciliation

Choose exactly one startup profile.

After routing ambiguous legacy knowledge, configure the desired manual or automatic profile in `.standards/config.toml`, then preview:

```bash
project-standards reconcile --check
```

A blocked plan is expected while ambiguous markers, duplicate hooks, unmanaged skill files, or stale registrations remain. Resolve each conflict locally; do not force an unsafe overwrite. Existing knowledge documents are create-only and remain consumer-owned.

## 4. Retire obsolete repo-local artifacts

After content reconciliation and a clean preview:

1. Remove or disable legacy SessionStart registrations so only one injection path remains.
2. Remove legacy per-harness hook copies after confirming both selected harnesses reference `.agents/hooks/agent-handoff/session_start.py`.
3. Remove retired repo-local skill directories after preserving intentional local guidance.
4. Remove old root or direct-`docs/` knowledge files only after their useful facts exist in canonical v1 files.
5. Rerun the legacy report. Investigate every remaining blocker or unclassified item.

## 5. Apply, validate, and review

Apply the reviewed plan, then validate:

```bash
project-standards reconcile --apply
project-standards agent-handoff validate --repo .
project-standards agent-handoff drift-check --repo .
git diff --check
git status --short
git diff
```

For Claude Code or Codex, review and trust the exact project-local hook definition through the harness workflow. Confirm startup context is injected once, stays within the byte ceiling, and points only to repository-local knowledge.

Migration is complete only when validation passes, the repository diff is understood, no needed fact was lost, and legacy startup injection is inactive.

## Legacy source notice

The pinned evidence repository is MIT-licensed, `Copyright (c) 2026 Chris Purcell`. This guide is a fresh rewrite. Any future copied or substantially derived legacy content must retain the legacy MIT copyright and permission notice. Agent Handoff itself inherits the project-standards repository license and ships no nested license.
