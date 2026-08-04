# Project Status

## Current snapshot

- Project Standards 5.14.0 is the published release at `b4be9d2e`; signed `v5.14.0` and `v5` tags are live.
- The exact release commit passed 4,323 ordinary tests, 133 compatibility tests, five performance tests, and 90% coverage locally.
- Hosted Check run `30725509522` passed the same release commit, including the corrected Agent Handoff launcher fixtures.
- GitHub's latest stable release carries the byte-verified wheel (`02d989a5…`) and sdist (`139808e7…`) assets.
- The open-issue program is active at format-3 revision 4: 41 tasks — 17 done, 3 superseded, 20 not-started, and T35 blocked.
- Revision 4 widened v5.15.0 to the whole Agent Handoff surface plus the mid-cycle control-plane unblock; ready work is T2, T3, T7, and T22.
- T35 keeps a stale blocker: the bridge has no `blocked` → `not-started` transition, so it clears only when the task genuinely starts.
- Python Tooling 1.11 is an unreleased candidate: first-party typed source resolution, Ruff bounded to declared roots, an explicit layout, and a fresh-adoption guard.
- CLI Documentation 1.6 and adr 1.4 are verified unreleased candidates with language-neutral rules, Go mappings, and a built-executable Go CI profile.
- The catalog carries those candidates at tool release 5.14.0, so every command building a planner request fails its lineage guard (issue #123, planned as T39/T40).
- `pip-audit` reports `cryptography` 49.0.0 vulnerable (PYSEC-2026-3552, fix 50.0.0); the release gate stays red until the lock advances.
- The tool release, four root `README.md` references, and the `.standards` projection still read 5.14.0/adr@1.3 by design until v5.15.0.
- Agent Handoff consumer retirement closed 2026-08-04: all four protected merges landed, `llm-wiki` validates, and `~/scripts` reconciles clean.
- Draft SPEC-GSF3 and its 14-task implementation plan define optional durable document-reference tooling; T1 is ready for a fresh implementation session.
- Go is supported alongside Python under ADR 0027 with a pinned module, Make gate, VS Code tasks, and path-filtered CI; language selection remains neutral.
- Usage Documentation Site V2 has an approved v5.16.0 design; new specs are queued, and SPEC-U000 through SPEC-U007 remain historical input.
- Self-hosted CI was deferred by owner decision; the reviewed future design belongs to `agent-managed-repo` governance.
- The required byte-identical plan bridge passes its package self-test, and Ruff excludes it as foreign vendored bytes this repository cannot own.
- Standard-governed Python, including `standards/**` payloads and the deployed `scripts/check.py`, stays linted so cross-standard breakage keeps surfacing.
- Agent Handoff 1.8's SessionStart hook never runs — `args: []` selects exec form (issues #122/#124, bug 005, planned as T38).
- Next: execute the ready Agent Handoff tasks T2, T3, and T7, then T22, working toward the T35 qualification gate.
