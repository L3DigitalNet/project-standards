---
schema_version: '1.1'
id: 'template-h2yvlz-go-command-and-internal-package-layout'
title: 'Go Command and Internal Package Layout'
description: 'Draft ADR template for Go products that build commands from `cmd/`, keep product code in `internal/`, and separate optional public packages and developer tooling.'
doc_type: 'template'
status: 'draft'
created: '2026-08-02'
updated: '2026-08-02'
reviewed: null
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'adr'
  - 'architecture'
  - 'go'
  - 'packaging'
  - 'repository'
aliases: []
related:
  - 'standards/adr/library/README.md'
  - 'standards/adr/library/repository-organization/executable-first-python-layout.md'
  - 'standards/adr/library/development/go-and-python-neutral-tooling.md'
  - 'standards/adr/versions/1.3/templates/adr.md'
source:
  - 'Owner requirement, 2026-08-02'
  - 'https://go.dev/doc/modules/layout'
  - 'https://pkg.go.dev/cmd/go'
  - 'https://github.com/golang-standards/project-layout'
confidence: 'high'
visibility: 'internal'
license: null
---

# ADR Library: Go Command and Internal Package Layout

## Description

This reusable draft is the Go companion to the [Executable-First Python Repository Layout](executable-first-python-layout.md). It places compiled product commands under `cmd/`, uses Go's compiler-enforced `internal/` boundary for private product code, reserves `pkg/` for an intentional external package API, and keeps developer tooling in `scripts/`.

Before adoption, confirm the root module boundary, identify each shipped command, decide whether any external package API is actually supported, define the canonical build targets, add required ADR metadata, and obtain explicit acceptance.

````markdown
# Use Go command and internal package layout

## Context and Problem Statement

This repository ships one or more compiled Go executables. It needs a clear distinction between command entrypoints, private shared product code, any deliberately supported external import surface, and development tooling.

The community-maintained “Standard Go Project Layout” is a useful collection of patterns, but it is not an official standard defined by the Go core team. The Go toolchain and module documentation provide the enforceable parts relevant here: a top-level `internal/` package cannot be imported by another module, and `cmd/` is a common convention for repositories that contain commands alongside importable packages.

This decision assumes one root Go module. A second module, workspace, or separately distributed component needs its own justified module and ownership boundary.

## Decision Drivers

- Make every shipped binary's source entrypoint visible and independently buildable.
- Prevent external consumers from depending on private product implementation packages.
- Publish an importable API only when the repository is prepared to support it.
- Keep developer, build, release, and documentation automation out of product binary discovery.
- Keep local, CI, and release builds aligned behind explicit command targets.

## Considered Options

- Use `cmd/`, `internal/`, optional `pkg/`, and `scripts/` for Go command products.
- Keep all application packages at the module root without an internal boundary.
- Put reusable product logic directly in each `cmd/<name>/main.go`.
- Treat `pkg/` as mandatory for every Go repository.

## Decision Outcome

Chosen option: **use `cmd/`, `internal/`, optional `pkg/`, and `scripts/` for Go command products**.

The canonical layout is:

```text
my-project/
├── cmd/                    # SHIPPED: command entrypoints
│   ├── my-app/
│   │   └── main.go         # builds the my-app executable
│   └── my-tool/
│       └── main.go         # builds the my-tool executable
├── internal/               # PRIVATE: product implementation packages
│   ├── config/
│   │   └── config.go
│   └── runner/
│       └── runner.go
├── pkg/                    # OPTIONAL PUBLIC: supported external import API
│   └── client/
│       └── client.go
├── scripts/                # INTERNAL: development, operations, and CI tooling
│   ├── release.sh
│   └── generate_docs.go
├── tests/                  # unit and integration tests where a separate tree helps
├── Makefile                # canonical development and release targets
├── go.mod
└── go.sum
```

### Strongly recommended full layout

The preceding tree is the minimum required to express this decision. The following is the strongly recommended default for a Go repository that also wants predictable homes for Project Standards packages, compatible agent workflows, and maintained documentation. It is a layout convention, not an obligation to create empty directories or adopt every related standard.

The tags identify namespace considerations:

- `[RES-G]` — reserved by Go or common development conventions; repurposing it can conflict with expected tool or contributor behavior.
- `[RES-PS]` — reserved within the Project Standards ecosystem; use may conflict with a current or future standards package, agent skill, or managed artifact.

```text
my-project/
├── .archived/              # [RES-PS] compressed historical project artifacts
├── .project-pipeline/      # [RES-PS] transient Project Pipeline execution state
├── .scratch/               # [RES-PS] temporary local work and scratch material
├── .standards/             # [RES-PS] Project Standards desired state and lock data
├── cmd/                    # [RES-G] SHIPPED: command entrypoints
│   ├── my-app/
│   │   └── main.go
│   └── my-tool/
│       └── main.go
├── internal/               # [RES-G] PRIVATE: compiler-enforced internal packages
│   ├── config/
│   │   └── config.go
│   └── runner/
│       └── runner.go
├── pkg/                    # [RES-G] OPTIONAL PUBLIC: supported external import API
│   └── client/
│       └── client.go
├── scripts/                # [RES-G] INTERNAL: development, build, and operations tooling
│   ├── release.sh
│   └── generate_docs.go
├── tests/                  # [RES-G] unit and integration tests
├── docs/                   # [RES-G] maintained project documentation
│   ├── adr/                # [RES-PS] accepted architecture decision records
│   ├── handoff/            # [RES-PS] durable Agent Handoff knowledge and state
│   ├── plans/              # [RES-PS] active implementation plans
│   ├── research/           # research reports and source-grounded findings
│   ├── resources/          # supporting files consumed by maintained documents
│   ├── references/         # maintained technical reference material
│   ├── reviews/            # design and implementation review records
│   ├── specs/              # [RES-PS] maintained project specifications
│   ├── templates/          # reusable repository document templates
│   ├── usage/              # [RES-PS] user-facing site documentation when its profile is adopted
│   └── workflows/          # reusable human and agent workflow procedures
├── Makefile
├── go.mod
└── go.sum
```

The recommended tree does not make every listed directory a shipped artifact. In particular, `.archived/`, `.project-pipeline/`, `.scratch/`, and `.standards/` are repository-control locations; `scripts/` is internal tooling; and `cmd/` is the product-command boundary.

The following invariants apply:

- Each shipped executable has a dedicated `cmd/<command-name>/main.go` package. The `main` package is a thin boundary that parses command-specific inputs, invokes package code, maps errors to the command's exit behavior, and owns no reusable product logic.
- A single command can be built with `go build ./cmd/<command-name>`. With the normal host target, its default output name is the command directory's name. Cross-platform release naming belongs to the release target, not to source-directory assumptions.
- `go build ./cmd/...` compiles every command package but, because it builds multiple packages, discards their output. It is a useful compilation check, not a release-binary materialization command. A `Makefile` or equivalent canonical target names every released binary and uses explicit `-o` output paths.
- Top-level `internal/` holds product implementation packages. Go prevents modules outside the repository module from importing them; code inside the module may import them according to normal package rules.
- `pkg/` is optional. Add it only for packages that are deliberately supported for external import and versioned as part of the repository's public API. Do not use `pkg/` as a generic dumping ground for private code.
- `scripts/` contains developer, build, release, CI, and documentation tools. It is not a product-command location, so `go build ./cmd/...` and release targets cannot include it accidentally.
- Tooling and tests cover command packages and internal packages. The strongly recommended full layout is an adoption guide, not a requirement to create every listed directory.

### Building and installation

The canonical `Makefile` or equivalent owns exact product output paths. For example:

```make
.PHONY: build

build:
	go build -o dist/my-app ./cmd/my-app
	go build -o dist/my-tool ./cmd/my-tool
```

| Action | Command | Outcome |
| --- | --- | --- |
| Compile every command package | `go build ./cmd/...` | Verifies all command packages compile; does not leave all binaries on disk. |
| Build one release binary | `go build -o dist/my-app ./cmd/my-app` | Writes the named product binary to the declared release path. |
| Install commands for local use | `go install ./cmd/...` | Installs command binaries to `GOBIN`, or its default under `GOPATH/bin` or `$HOME/go/bin`. |
| Run a one-file Go developer tool | `go run ./scripts/generate_docs.go` | Runs the named development tool without making it a product command. |

### Command entrypoint pattern

```go
package main

import (
	"errors"
	"os"

	"github.com/my-org/my-project/internal/runner"
)

func main() {
	if err := runner.Run(); err != nil {
		if errors.Is(err, runner.ErrUsage) {
			os.Exit(2)
		}
		os.Exit(1)
	}
}
```

### Consequences

- Good, because command names, build inputs, and release artifacts have an explicit source boundary.
- Good, because the compiler enforces the private implementation boundary for top-level `internal/` packages.
- Good, because an external package API is opt-in rather than accidentally created by product implementation paths.
- Bad, because a repository must maintain explicit build targets for each released binary; a broad package pattern is not a release artifact command.
- Bad, because `pkg/` carries an external compatibility promise and should remain absent when no such promise exists.
- Neutral, because `cmd/` and `pkg/` are conventions rather than language-mandated directory names; the `internal/` import restriction is the language-toolchain rule that gives this layout its private boundary.

### Confirmation

Conformance is confirmed when every shipped binary has a dedicated command package, its `main.go` delegates to private or public package code, no product logic is trapped in `main`, external modules cannot import top-level `internal/` packages, `pkg/` contains only intentionally supported public APIs, `scripts/` is absent from product build targets, and clean release builds produce the exact declared binaries.

## Pros and Cons of the Options

### `cmd/`, `internal/`, optional `pkg/`, and `scripts/`

- Good, because commands, private product code, supported public APIs, and developer tooling have distinct ownership boundaries.
- Good, because Go enforces the private boundary for `internal/` imports.
- Bad, because the layout should remain small and requires restraint against creating unused directories.

### Module-root packages without `internal/`

- Good, because a small single-command project can have fewer directories.
- Bad, because importable module-root packages can become accidental external API commitments.

### Product logic in `main.go`

- Good, because an initial prototype has fewer files.
- Bad, because shared logic becomes difficult to test, reuse, and keep consistent across commands.

### Mandatory `pkg/`

- Good, because an intended external API has one predictable location.
- Bad, because most command products do not need an external API, and an empty or unsupported `pkg/` falsely implies one.

## More Information

Record the module path, command names, supported platforms, exact build and release targets, `GOBIN` installation expectations, and any supported package API. The official [Organizing a Go module](https://go.dev/doc/modules/layout) guide is authoritative for the `internal/` boundary and recognizes `cmd/` as a useful convention; the [`go` command documentation](https://pkg.go.dev/cmd/go) is authoritative for build and install behavior.

The [Standard Go Project Layout](https://github.com/golang-standards/project-layout) repository is a community pattern reference, not an official Go standard. Revisit this decision when the repository gains another module, needs a separately distributed component, adds a supported external API, or changes the released command set.
````
