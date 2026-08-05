# ADR Library

## Purpose

This directory collects draft Architectural Decision Record (ADR) templates for common repository management, software development, and operations practices. The drafts are reference inputs for a future versioned ADR package library; they are not released package payloads or accepted project decisions.

Before adoption, review and adapt each draft for the target repository, add the metadata required by that repository, resolve its placeholders, and record explicit acceptance.

## Development and language architecture

### [Go and Python Coexistence with Neutral Tooling](development/go-and-python-neutral-tooling.md)

Provides a draft for adopting Go alongside an existing Python implementation while keeping language selection neutral and defining one canonical Go tooling lane.

## Git and branch management

### [Branch Integration and Protection Strategy](git/branch-integration-and-protection.md)

Provides a draft for a simple `dev`/`main` branch relationship and local Git-hook safeguards intended to prevent ordinary development from being committed directly to `main`.

## Repository organization

### [Go Command and Internal Package Layout](repository-organization/go-command-and-internal-package-layout.md)

Provides a draft for Go products that build commands from `cmd/`, keep product code private under `internal/`, expose an optional public package surface, and separate developer tooling.

### [Executable-First Python Repository Layout](repository-organization/executable-first-python-layout.md)

Provides a draft for shipping literal extensionless Python executables from `bin/`, their shared core package from `lib/`, and unshipped developer tooling from `scripts/`.

### [Archive Archived Material as ZIP Files](repository-organization/archive-archived-material-as-zip.md)

Provides a draft for storing historical material in compressed `.zip` files under a default repository-root `.archived/` path, with a repository-specific alternative allowed.
