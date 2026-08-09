# Project Standards Roadmap

This file tracks work planned for upcoming Project Standards releases. It is forward-looking planning, not a release commitment or a substitute for the release record in [CHANGELOG.md](CHANGELOG.md).

- [Project Standards Roadmap](#project-standards-roadmap)
  - [Planned releases](#planned-releases)
    - [5.15.0](#5150)
      - [CLI Documentation v1.6](#cli-documentation-v16)
      - [ADR v1.4](#adr-v14)
      - [Python Tooling (v1.11 prep)](#python-tooling-v111-prep)
      - [Bug fixes and general improvements](#bug-fixes-and-general-improvements)
    - [5.16.0](#5160)
    - [5.17.0](#5170)
      - [GitHub Workflow v1.0](#github-workflow-v10)
      - [Caller-mode runner selection](#caller-mode-runner-selection)
      - [Agent Handoff v1.10](#agent-handoff-v110)
    - [5.18.0](#5180)
      - [ADR v1.5 and corpus remediation](#adr-v15-and-corpus-remediation)
  - [Beyond](#beyond)

## Planned releases

### 5.15.0

**Shipped as v5.15.0.** Kept for the planning record; [CHANGELOG.md](CHANGELOG.md) is what actually landed.

#### CLI Documentation v1.6

- Publish CLI Documentation 1.6 with language-neutral Python, Go, and generic profiles while retaining 1.5 unchanged and exactly selectable.

#### ADR v1.4

- Greatly improve ADR authoring guidance.

#### Python Tooling (v1.11 prep)

- Publish a Python Tooling successor for [#86](https://github.com/L3DigitalNet/project-standards/issues/86), [#89](https://github.com/L3DigitalNet/project-standards/issues/89), [#95](https://github.com/L3DigitalNet/project-standards/issues/95), and [#109](https://github.com/L3DigitalNet/project-standards/issues/109), including the approved V5 authority correction; retain 1.10 unchanged and selectable.

#### Bug fixes and general improvements

- Correct control-plane and migration issues [#76](https://github.com/L3DigitalNet/project-standards/issues/76), [#77](https://github.com/L3DigitalNet/project-standards/issues/77), [#83](https://github.com/L3DigitalNet/project-standards/issues/83), [#87](https://github.com/L3DigitalNet/project-standards/issues/87), [#98](https://github.com/L3DigitalNet/project-standards/issues/98), [#105](https://github.com/L3DigitalNet/project-standards/issues/105), and [#106](https://github.com/L3DigitalNet/project-standards/issues/106).
- Resolve or evidence-dispose the transient PyYAML failure in [#84](https://github.com/L3DigitalNet/project-standards/issues/84) before release qualification.
- Publish a Python Tooling successor for [#86](https://github.com/L3DigitalNet/project-standards/issues/86), [#89](https://github.com/L3DigitalNet/project-standards/issues/89), [#95](https://github.com/L3DigitalNet/project-standards/issues/95), and [#109](https://github.com/L3DigitalNet/project-standards/issues/109), including the approved V5 authority correction; retain 1.10 unchanged and selectable.

### 5.16.0

**Shipped as v5.16.0.** The deferred Markdown/Python Tooling issues [#88](https://github.com/L3DigitalNet/project-standards/issues/88) and [#99](https://github.com/L3DigitalNet/project-standards/issues/99) landed there — #88 in Markdown Tooling 1.13's corpus-bounded verification recipes, #99 in Python Tooling 1.12's leaf-addressable Ruff decomposition — alongside the rest of the defect cycle.

### 5.17.0

#### GitHub Workflow v1.0

- Advertise `github-workflow` 1.0 as Catalog 5's eighth consumer package: the repo-local `github-workflow` skill plus the committed static `gh-workflow` binary, whose frozen nine-subcommand surface (`audit`, `ledger`, `new`, `set`, `close`, `reopen`, `summary`, `receipt`, `check`) reads and mutates issues, pull requests, and organization-schema field values. `set --type` assigns an existing organization Issue Type, validating offline against `org-schema.yaml` and reading the response back rather than trusting the status code.

#### Caller-mode runner selection

- Publish Markdown Tooling 1.14, Project Specification 1.8, and Markdown Frontmatter 1.10 with the optional top-level `runner_labels` option for [#132](https://github.com/L3DigitalNet/project-standards/issues/132), so a caller-mode managed workflow reaches a self-hosted runner pool without a hand edit that trips `CP-MODIFIED-MANAGED`; retain 1.13, 1.7, and 1.9 unchanged and exactly selectable.

#### Agent Handoff v1.10

- Advertise Agent Handoff 1.10, which ships the SessionStart launcher as a reproducibly built static `linux/amd64` binary instead of a Python hook, removing the interpreter-resolution failure class at the cost of a narrower supported platform.

### 5.18.0

#### ADR v1.5 and corpus remediation

- Publish `adr` 1.5 with the amendment vocabulary from [#127](https://github.com/L3DigitalNet/project-standards/issues/127) as the Catalog 5 default, then work the corpus backlog in [#128](https://github.com/L3DigitalNet/project-standards/issues/128) using the 1.5 amendment form. Moved here from 5.17.0 by owner direction on 2026-08-08.

## Beyond
