# Project Status

## Current snapshot

- Project Standards 5.19.0 is published from release commit `127bd3dd`; signed `v5.19.0` and moving `v5` tags are live.
- The release assets are byte-verified: wheel `134d5abc…` and source distribution `c1605cde…`.
- The final local release battery passed with 5,016 ordinary tests, 141 compatibility cases, five performance tests, and 90% coverage.
- Hosted verification is green on the release commit. The first run found only cold-runner timing ceilings; `127bd3dd` calibrated the test bounds.
- Catalog 5 defaults: ADR 1.6, Agent Handoff 1.12, GitHub Workflow 1.2, Markdown Frontmatter 1.11, and Markdown Tooling 1.15.
- Project Specification 1.9 and Python Tooling 1.14 are also defaults. Every predecessor remains retained and selectable.
- Project Specification 1.9 ships strict conformance linting and the preservation-first import workflow. Issues #62 and #55 are closed as completed against 5.19.0.
- The open-issue resolution program is complete. Its frozen 24 issues plus the three appended reports are terminal: 25 completed, #84 accepted as an external-cause closure, and #124 closed as a duplicate.
- The three terminal child plans were retired after their checkpoint and release evidence was harvested. The program execution scratch was removed after its final checkpoint.
- `@v5` consumers inherit the moving tag. No exact-pin consumer repositories were changed during this release.
- Remaining product work is outside the completed train: #168 targets the 5.20.0 `project-toolbox` release, #129 remains deferred, and the Usage Documentation Site V2 specifications remain queued.
- `rexec` v0.2.0 remains the CPU-work path for synchronized-tree workloads. Git-dependent operations remain direct-local because `.git` is not transferred.
