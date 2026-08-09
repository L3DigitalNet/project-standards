# Project Standards Roadmap

This file tracks work planned for upcoming Project Standards releases. It is forward-looking planning, not a release commitment or a substitute for the release record in [CHANGELOG.md](CHANGELOG.md).

- [Project Standards Roadmap](#project-standards-roadmap)
  - [Planned releases](#planned-releases)
    - [5.18.0](#5180)
      - [ADR v1.5 and corpus remediation](#adr-v15-and-corpus-remediation)
      - [Python Tooling configuration](#python-tooling-configuration)
      - [Agent Handoff follow-ups](#agent-handoff-follow-ups)
      - [GitHub Workflow follow-ups](#github-workflow-follow-ups)
      - [Executable payload adoption guidance](#executable-payload-adoption-guidance)
      - [Test reliability and contract cleanup](#test-reliability-and-contract-cleanup)
  - [Beyond](#beyond)

## Planned releases

### 5.18.0

#### ADR v1.5 and corpus remediation

- Publish `adr` 1.5 with the amendment vocabulary from [#127](https://github.com/L3DigitalNet/project-standards/issues/127) as the Catalog 5 default, then work the corpus backlog in [#128](https://github.com/L3DigitalNet/project-standards/issues/128) using the 1.5 amendment form. Moved here from 5.17.0 by owner direction on 2026-08-08.

#### Python Tooling configuration

- Publish a Python Tooling successor that supports scoped Ruff per-file ignore extensions without replacing package defaults or disabling rules globally, as tracked in [#116](https://github.com/L3DigitalNet/project-standards/issues/116).

#### Agent Handoff follow-ups

- Make the pre-enable legacy inventory workflow reachable or align its runbook ordering, as tracked in [#130](https://github.com/L3DigitalNet/project-standards/issues/130).
- Align exclusion guidance with Markdown Tooling's typed exclusions option in [#139](https://github.com/L3DigitalNet/project-standards/issues/139).
- Add the actionable exact-selection upgrade finding in [#141](https://github.com/L3DigitalNet/project-standards/issues/141) and correct the 1.10 adoption-guide version mismatch in [#148](https://github.com/L3DigitalNet/project-standards/issues/148).

#### GitHub Workflow follow-ups

- Derive Issue Type guidance from the schema in [#144](https://github.com/L3DigitalNet/project-standards/issues/144) and settle the family-root adoption-document decision in [#145](https://github.com/L3DigitalNet/project-standards/issues/145).
- Correct the ledger mutation guidance in [#149](https://github.com/L3DigitalNet/project-standards/issues/149) and eliminate or explicitly resolve timestamp-only ledger churn in [#154](https://github.com/L3DigitalNet/project-standards/issues/154).

#### Executable payload adoption guidance

- Document narrow pre-commit exemptions for the immutable Agent Handoff and GitHub Workflow executables without weakening repository-wide added-file protection, as tracked in [#151](https://github.com/L3DigitalNet/project-standards/issues/151).

#### Test reliability and contract cleanup

- Collapse the duplicated retained-version digest assertions tracked in [#146](https://github.com/L3DigitalNet/project-standards/issues/146), preserving the promotion-contract documentation without changing payload or catalog bytes.
- Resolve the gate-parallelism failures tracked in [#147](https://github.com/L3DigitalNet/project-standards/issues/147) so the MCP timing and determinism tests pass reliably under the ordinary verification lane.

## Beyond
