# Project Status

## Current snapshot

- Project Standards 5.14.0 is the published release at `b4be9d2e`; signed `v5.14.0` and `v5` tags are live.
- The exact release commit passed 4,323 ordinary tests, 133 compatibility tests, five performance tests, and 90% coverage locally.
- Hosted Check run `30725509522` passed the same release commit, including the corrected Agent Handoff launcher fixtures.
- GitHub's latest stable release carries the byte-verified wheel (`02d989a5…`) and sdist (`139808e7…`) assets.
- The 37-task open-issue program is active at format-3 revision 3: 17 done, 2 superseded, 16 not-started, and T35 blocked.
- Every approved v5.15.0 boundary task is `done` except T35, its publication task; T1 and T32 also closed independently.
- T35 is blocked by owner decision on 2026-08-04: additional repo changes join the v5.15.0 boundary, to be reassessed fresh.
- Python Tooling 1.11 is an unreleased candidate: first-party typed source resolution, Ruff bounded to declared roots, an explicit layout, and a fresh-adoption guard.
- CLI Documentation 1.6 and adr 1.4 are verified unreleased candidates with language-neutral rules, Go mappings, and a built-executable Go CI profile.
- The catalog carries those candidates while the tool release still reads 5.14.0, so the whole `agent-handoff` command group fails its lineage guard until release prep.
- `pip-audit` reports `cryptography` 49.0.0 vulnerable (PYSEC-2026-3552, fix 50.0.0); the release gate stays red until the lock advances.
- The tool release, four root `README.md` references, and the `.standards` projection still read 5.14.0/adr@1.3 by design until v5.15.0.
- Agent Handoff consumer retirement closed 2026-08-04: all four protected merges landed, `llm-wiki` validates, and `~/scripts` reconciles clean.
- Draft SPEC-GSF3 and its 14-task implementation plan define optional durable document-reference tooling; T1 is ready for a fresh implementation session.
- Go is supported alongside Python under ADR 0027 with a pinned module, Make gate, VS Code tasks, and path-filtered CI; language selection remains neutral.
- Usage Documentation Site V2 has an approved v5.16.0 design; new specs are queued, and SPEC-U000 through SPEC-U007 remain historical input.
- Self-hosted CI was deferred by owner decision; the reviewed future design belongs to `agent-managed-repo` governance.
- The required byte-identical plan bridge passes its package self-test, and Ruff excludes it as foreign vendored bytes this repository cannot own.
- Standard-governed Python, including `standards/**` payloads and the deployed `scripts/check.py`, stays linted so cross-standard breakage keeps surfacing.
- Next: settle the widened v5.15.0 boundary, revise the plan to match, then resume at T35.
