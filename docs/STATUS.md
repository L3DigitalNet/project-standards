# Project Status

## Current snapshot

- Project Standards 5.14.0 is the published release at `b4be9d2e`; signed `v5.14.0` and `v5` tags are live.
- The exact release commit passed 4,323 ordinary tests, 133 compatibility tests, five performance tests, and 90% coverage locally.
- Hosted Check run `30725509522` passed the same release commit, including the corrected Agent Handoff launcher fixtures.
- Package, graph, schema, projection, catalog, release-classification, managed-document, and Agent Handoff gates passed.
- GitHub's latest stable release carries the byte-verified wheel (`02d989a5…`) and sdist (`139808e7…`) assets.
- The 36-task open-issue program is active at format-3 revision 2 with its bounded one-pass Opus audit corrections integrated.
- Draft SPEC-GSF3 and its 14-task implementation plan define optional durable document-reference tooling; T1 is ready for a fresh implementation session.
- Go is supported alongside Python under ADR 0027 with a pinned module, Make gate, VS Code tasks, and path-filtered CI; language selection remains neutral.
- CLI Documentation 1.6 is an unreleased candidate with language-neutral rules, explicit Go mappings, and a built-executable Go CI profile.
- Usage Documentation Site V2 has an approved v5.16.0 design; new specs are queued, and SPEC-U000 through SPEC-U007 remain historical input.
- The approved v5.15.0 boundary combines CLI Documentation 1.6 with twelve control-plane, migration, and Python Tooling issues; 5.14.0 remains published truth.
- v5.15.0 implementation is prepared but no task has started: the format-3 master and fresh execution state are valid, with T30 as the sole ready task.
- Self-hosted CI was deferred by owner decision; the reviewed future design belongs to `agent-managed-repo` governance.
- The required byte-identical plan bridge passes its package self-test but fails this repository's Ruff formatting, lint, and BasedPyright gates.
- Next: make the canonical bridge compatible upstream, redeploy it byte-identically, rerun repository gates, then run an independent `execute-plan` preflight for T30.
- T1 tracker closeout and T32 consumer retirement remain independent.
