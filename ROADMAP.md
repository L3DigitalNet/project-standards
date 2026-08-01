# Roadmap

This file tracks work planned for upcoming Project Standards releases. It is forward-looking planning, not a release commitment or a substitute for the release record in [CHANGELOG.md](CHANGELOG.md).

- [Roadmap](#roadmap)
  - [Planned releases](#planned-releases)
    - [5.14.0](#5140)
    - [5.15.0](#5150)
    - [5.16.0](#5160)
  - [Beyond](#beyond)

## Planned releases

### 5.14.0

- Promote Agent Handoff 1.8 as the Catalog 5 default while retaining 1.7. The new Claude Code and Codex SessionStart launchers select a usable Python 3.14 directly or through project-independent `uv`, fixing startup under rejecting Python shims ([issue #80](https://github.com/L3DigitalNet/project-standards/issues/80)).
- Ship the release-preparation safeguards staged on `testing`: require clean `main`, print the complete candidate-wheel and pre-tag verification sequence, use a fresh isolated wheel runtime, and make release-consistency checks honor deleted completed plans without weakening other required-path checks.
- Publish the post-5.13 documentation reconciliation: align MCP, CLI, release, and handoff documentation with shipped behavior; record the full drift audit; and prune completed implementation plans and stale release evidence from active documentation.
- Implement the optional durable document-reference tooling defined by [SPEC-GSF3](docs/specs/2026-07-31-durable-document-references-optional-tooling-spec.md) and its [active plan](docs/plans/2026-07-31-durable-document-references-optional-tooling-plan.md). The specification and plan are on `testing`; runtime implementation and qualification remain pending.

### 5.15.0

### 5.16.0

## Beyond
