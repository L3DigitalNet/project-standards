---
schema_version: '1.1'
id: 'adr-0027-project-standards-adopt-go-alongside-python-with-neutral-tooling'
title: 'ADR 0027: Adopt Go Alongside Python with Neutral Tooling'
description: 'Adopts Go as a supported repository language with a canonical tooling lane while deferring language-selection policy.'
doc_type: 'adr'
status: 'active'
created: '2026-08-01'
updated: '2026-08-01'
reviewed: '2026-08-01'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'adr'
  - 'architecture'
  - 'go'
  - 'python'
  - 'tooling'
aliases:
  - 'ADR 0027'
  - 'Go adoption'
  - 'Go and Python coexistence'
related:
  - 'docs/adr/README.md'
  - 'docs/handoff/conventions.md'
  - 'standards/adr/library/development/go-and-python-neutral-tooling.md'
  - 'go.mod'
  - 'Makefile'
  - '.golangci.yml'
  - '.github/workflows/go.yml'
supersedes: []
superseded_by: null
source:
  - 'Owner approval, 2026-08-01'
  - 'go.mod'
  - 'Makefile'
  - '.golangci.yml'
  - '.github/workflows/go.yml'
  - '.vscode/tasks.json'
confidence: 'high'
visibility: 'internal'
license: null
project:
  decision_makers:
    - 'Chris Purcell'
  consulted:
    - 'Codex'
  informed: []
---

# ADR 0027: Adopt Go Alongside Python with Neutral Tooling

MADR status: **accepted** (2026-08-01; owner approval explicitly recorded after review).

## Context and Problem Statement

This repository maintains its existing implementation and standards platform in Python. It now also needs a complete Go development lane before the first repository-owned Go package is introduced.

Adding a second implementation language changes module, dependency, editor, verification, and CI architecture. Those boundaries must be deliberate without turning tooling readiness into a preference for Go, a migration mandate, or authority to retire Python.

## Decision Drivers

- Make Go work reproducible and independently verifiable before production Go code is introduced.
- Preserve the existing Python implementation and its standards-managed tooling without weakening either lane.
- Keep local, editor, and CI commands aligned behind one canonical owner.
- Pin executable tools and toolchains through reviewable repository authorities.
- Avoid selecting a preferred language before approved guidance exists for choosing between Go and Python.
- Preserve separate ownership boundaries for standards packages, repository tooling, hooks, and generated fixtures.

## Considered Options

- Adopt Go alongside Python with a neutral, canonical tooling lane.
- Defer Go adoption until language-selection guidance and the first Go implementation are approved together.
- Adopt Go as the preferred language for new repository-owned tooling.

## Decision Outcome

Chosen option: **adopt Go alongside Python with a neutral, canonical tooling lane**. Go is an approved repository language, and Go work has a defined build and verification contract. This decision assigns neither Go nor Python to a category of future work.

The following invariants apply:

- Go and Python coexist as supported repository languages. Neither is the repository-wide default or preferred choice.
- This decision does not authorize a Python-to-Go migration, production cutover, Python freeze, dependency removal, test retirement, or standards-package change.
- Language selection for new work or migration requires case-specific requirements or later approved guidance. Existing architecture and ownership boundaries take precedence.
- The repository has one root Go module, `github.com/L3DigitalNet/project-standards`. Another module or a Go workspace requires an independently justified ownership or distribution boundary.
- `go.mod` owns the minimum Go version, preferred toolchain, module dependencies, and module-tracked executable tools. `go.sum` owns module checksums.
- The root `Makefile` owns canonical Go commands. Local users, editor tasks, and CI invoke its targets rather than maintaining independent command lists.
- The canonical Go gate checks repository-scoped formatting, module tidiness and integrity, `go vet`, configured `golangci-lint` analysis, race-enabled tests with coverage, builds, and `govulncheck` when Go packages exist.
- `golangci-lint` is version-pinned and installed under the ignored repository-local `.tools/` directory. Its configuration uses a reviewed linter set; exclusions and disabled analyzers require a documented ownership or correctness reason.
- `govulncheck` is pinned as a module tool and invoked with `go tool`. `go vet` remains a first-party gate and is disabled inside `golangci-lint` to prevent duplicate ownership.
- The Go CI workflow installs the exact preferred toolchain and pinned tools, then invokes the canonical gate. VS Code recommends the Go extension and delegates repository operations to Make targets.
- Go tooling does not own Python, Markdown, shell, package-contract, handoff, skill, or harness validation. Those gates remain independent and applicable within their existing scopes.
- Repository-owned Go source may use the root module. A standard package, generated fixture, or externally distributed component does not join that module merely because it is stored in this repository.

Exact Go and tool versions are ordinary reviewed configuration owned by their declared files. Compatible upgrades do not require an ADR amendment. Changing the module boundary, canonical command owner, verification categories, coexistence policy, or language-neutral posture does.

### Consequences

- Good, because Go code can be introduced through a reproducible local and CI lane without waiting for a migration decision.
- Good, because one command owner prevents VS Code, CI, and local verification from drifting apart.
- Good, because Python remains supported and no migration authority is inferred from the presence of Go tooling.
- Bad, because the repository must maintain two language toolchains and their independent supply-chain checks while both remain active.
- Bad, because neutrality leaves each future language choice unresolved until general guidance or case-specific evidence settles it.
- Neutral, because package-specific Go checks report an explicit skip until the first Go package exists; module and configuration checks are active immediately.

### Confirmation

Conformance is confirmed when `make go-check` is the canonical local and CI entry point, pinned tool versions are provable, editor tasks delegate to Make targets, and Go changes do not remove or weaken applicable non-Go gates.

While no Go packages exist, vet, lint, test, build, and vulnerability-package scans must report an explicit skip rather than imply package-level verification. Once a package is added, those same targets must execute against it without a second gate definition.

## Pros and Cons of the Options

### Neutral Go and Python coexistence

- Good, because tooling readiness and language policy remain separate decisions.
- Good, because it preserves current Python authority while allowing bounded Go work.
- Bad, because future language choices may need additional analysis until general guidance exists.

### Defer Go adoption

- Good, because the repository would maintain only one active implementation-language toolchain until the first approved Go project.
- Bad, because the first Go implementation would also need to design and prove the tooling lane, coupling infrastructure decisions to product behavior.

### Prefer Go for new repository tooling

- Good, because new work would have an immediate language-selection rule.
- Bad, because no approved evidence or policy establishes that Go is the better choice for every repository-owned tool.
- Bad, because a preference could cause opportunistic migration or inappropriate language choices across distinct ownership and distribution boundaries.

## More Information

The implementation authorities are [`go.mod`](../../go.mod), [`Makefile`](../../Makefile), [`.golangci.yml`](../../.golangci.yml), the [Go CI workflow](../../.github/workflows/go.yml), and the [VS Code tasks](../../.vscode/tasks.json). Commands and versions live there rather than being duplicated in this ADR.

Revisit this decision when the repository is ready to define language-selection guidance, when the first Go package exposes a missing verification category, or when a component needs a module, distribution, or tooling boundary that the root lane cannot represent cleanly.
