# Project Status

## Current snapshot

- Project Standards 5.14.0 is the published release at `b4be9d2e`; signed `v5.14.0` and `v5` tags are live.
- The exact release commit passed 4,323 ordinary tests, 133 compatibility tests, five performance tests, and 90% coverage locally.
- Hosted Check run `30725509522` passed the same release commit, including the corrected Agent Handoff launcher fixtures.
- Package, graph, schema, projection, catalog, release-classification, managed-document, and Agent Handoff gates passed.
- GitHub's latest stable release carries the byte-verified wheel (`02d989a5…`) and sdist (`139808e7…`) assets.
- The 37-task open-issue program is active at format-3 revision 3, which added T37 to verify the merged adr@1.4 candidate.
- Draft SPEC-GSF3 and its 14-task implementation plan define optional durable document-reference tooling; T1 is ready for a fresh implementation session.
- Go is supported alongside Python under ADR 0027 with a pinned module, Make gate, VS Code tasks, and path-filtered CI; language selection remains neutral.
- CLI Documentation 1.6 is an unreleased candidate with language-neutral rules, explicit Go mappings, and a built-executable Go CI profile.
- Usage Documentation Site V2 has an approved v5.16.0 design; new specs are queued, and SPEC-U000 through SPEC-U007 remain historical input.
- The approved v5.15.0 boundary combines CLI Documentation 1.6 and adr@1.4 with twelve control-plane, migration, and Python Tooling issues; 5.14.0 remains published truth.
- adr@1.4 merged from PR #120 with its release-boundary items deferred, so the tool release, four root `README.md` references, and the `.standards` projection still read 5.14.0/adr@1.3.
- v5.15.0 implementation is prepared but no task has started: the format-3 master and fresh execution state are valid, with T30 as the sole ready task.
- Self-hosted CI was deferred by owner decision; the reviewed future design belongs to `agent-managed-repo` governance.
- The required byte-identical plan bridge passes its package self-test, and Ruff now excludes it alongside `scripts/check.py` as vendored byte-identical copies; BasedPyright never covered `scripts/`.
- Next: run an independent `execute-plan` preflight for T30, which is unblocked and remains the sole ready task.
- T1 tracker closeout and T32 consumer retirement remain independent.
