---
schema_version: '1.1'
id: 'research-is01jt-agent-handoff-ingestion-inventory'
title: 'Agent Handoff Legacy Ingestion Inventory'
description: 'Pinned source, licensing, ownership, and disposition inventory for the Agent Handoff v1 package rewrite.'
doc_type: 'research'
status: 'active'
created: '2026-07-09'
updated: '2026-07-09'
reviewed: '2026-07-09'
owner: 'project-standards'
consumer: 'agent'
tags:
  - 'standard'
  - 'migration'
  - 'inventory'
aliases:
  - 'agent-handoff ingestion inventory'
related:
  - 'docs/superpowers/specs/2026-07-09-agent-handoff-standard-package.md'
  - 'docs/superpowers/plans/2026-07-09-agent-handoff-standard-package.md'
source:
  - '/home/chris/projects/agent-handoff-v3@56b24df7279572c485c2512783b0cc7e5395429b'
confidence: 'high'
visibility: 'internal'
license: null
---

# Agent Handoff Legacy Ingestion Inventory

This inventory freezes the legacy evidence used to build `agent-handoff` v1. The legacy checkout is read-only and pinned to commit `56b24df7279572c485c2512783b0cc7e5395429b`; no runtime or release artifact may depend on that checkout.

## License and ownership verification

The pinned commit's root `LICENSE` is the MIT License and identifies `Copyright (c) 2026 Chris Purcell`. Its redistribution condition requires the copyright and permission notice in copies or substantial portions. `git log --follow` and per-path author scans show only `Chris Purcell <168346341+chrisdpurcell@users.noreply.github.com>` for every retained or referenced path below.

The v1 package content created in Task 4 is a fresh rewrite from the approved specification and behavior inventory, not a verbatim or substantial file copy. It inherits the project-standards root Apache-2.0 license and has no nested package license. If later implementation copies or substantially derives legacy source or test content, that file or the distribution's applicable notice surface must retain the legacy MIT copyright and permission notice.

## Disposition map

The “history evidence” column records the most recent path commit reachable from the pin. All rows are also covered by the pinned root MIT license and sole-author history described above.

| Legacy source at pinned commit | Disposition | History evidence | New owner or use |
| --- | --- | --- | --- |
| `agent-handoff-v3/global/hooks/session_start.py` | rewrite | `4ed3b59` (2026-07-01) | Canonical v1 hook at `standards/agent-handoff/hooks/session-start/session_start.py` |
| `agent-handoff-v3/resources/handoff-policy.toml` | rewrite | `e694037` (2026-07-09) | V1 policy at `standards/agent-handoff/resources/policy.toml` |
| `agent-handoff-v3/scripts/handoff/_handoff_policy.py` | rewrite | `071928c` (2026-07-09) | Typed Python policy provider |
| `agent-handoff-v3/scripts/handoff/validate-layout.sh` | rewrite | `56b24df` (2026-07-09) | Python validation provider |
| `agent-handoff-v3/scripts/handoff/size-report.sh` | rewrite | `071928c` (2026-07-09) | Python size-report view |
| `agent-handoff-v3/scripts/handoff/validate-shape.sh` | rewrite | `071928c` (2026-07-09) | Python shape-check view |
| `agent-handoff-v3/skills/.agents/skills/handoff-system-v3/SKILL.md` | rewrite | `56b24df` (2026-07-09) | V1 `agent-handoff` skill |
| `agent-handoff-v3/skills/.agents/skills/handoff-system-v3/agents/openai.yaml` | rewrite | `a81708b` (2026-06-22) | V1 skill interface metadata |
| `agent-handoff-v3/scripts/handoff/install-globals.sh` | discard | `56b24df` (2026-07-09) | Prohibited global and fleet ownership; inventory only |
| `agent-handoff-v3/scripts/handoff/claude-bootstrap.sh` | discard | `e694037` (2026-07-09) | Prohibited global and fleet ownership; inventory only |
| `agent-handoff-v3/scripts/handoff/validate-globals.sh` | discard | `56b24df` (2026-07-09) | Prohibited global validation; inventory only |
| `agent-handoff-v3/global/claude/settings.json` | document-only | `a4a676b` (2026-06-08) | Structural evidence for Claude integration fixtures; no copied content |
| `agent-handoff-v3/global/codex/config.toml` | document-only | `d8c8556` (2026-06-14) | Structural evidence for Codex integration fixtures; no copied content |
| `agent-handoff-v3/STATUS.md` | document-only | `f363355` (2026-07-09) | Structural evidence for `docs/STATUS.md`; no copied content |
| `agent-handoff-v3/TODO.md` | document-only | `f363355` (2026-07-09) | Structural evidence for `docs/TODO.md`; no copied content |
| `scripts/tests/claude-bootstrap.bats` | ingest | `e694037` (2026-07-09) | Behavior-level migration/profile acceptance corpus |
| `scripts/tests/install-globals.bats` | ingest | `56b24df` (2026-07-09) | Negative corpus for prohibited global/fleet behavior |
| `scripts/tests/session-start.bats` | ingest | `56b24df` (2026-07-09) | Hook behavior acceptance corpus |
| `scripts/tests/size-report.bats` | ingest | `56b24df` (2026-07-09) | UTF-8 size and threshold behavior corpus |
| `scripts/tests/validate-globals.bats` | ingest | `e694037` (2026-07-09) | Negative corpus for global-boundary validation |
| `scripts/tests/validate-layout.bats` | ingest | `56b24df` (2026-07-09) | Layout and accumulated-finding behavior corpus |
| `scripts/tests/validate-shape.bats` | ingest | `56b24df` (2026-07-09) | Document-shape behavior corpus |
| `tests/unit/test_session_start.py` | ingest | `4ed3b59` (2026-07-01) | Pytest hook behavior corpus |
| `tests/unit/test_handoff_policy.py` | ingest | `e694037` (2026-07-09) | Pytest policy behavior corpus |

`scripts/tests/run.sh`, `tests/unit/test_bugs_index.py`, `tests/unit/test_scrub_guard.py`, the legacy `_handoff-lib.sh`, and `agent-handoff-v3/global/README.md` were inspected as neighboring inventory context but are not direct v1 source inputs. Their useful behavior must enter through an explicit future test or specification requirement, not implicit copying.

## Ingestion rules

- Preserve behavior-level cases, not legacy product identity or global ownership.
- Rewrite all runtime paths to the v1 `docs/` and `.agents/` layout.
- Treat unknown historical evidence as reportable ambiguity, never as permission to transform it.
- Keep migration agent-guided and validate before removing any legacy repo-local artifact.
- Do not import global installers, sibling-repository scanners, home-directory state, deterministic converters, quarantine trees, or fleet orchestration.
