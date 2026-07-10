# Project Specification Standard: Agent Summary

The canonical [README](README.md) is authoritative and wins if this summary conflicts with it.

## Use this summary when

Create, inspect, validate, or implement a durable specification for a project, feature, or subsystem.

## Core rules

- Choose the smallest adequate profile: Light for small or single-session work, Standard for typical features and services, and Full for multi-service, durable-data, external-integration, or multi-stakeholder work.
- Light, Standard, and Full use the same canonical section numbers and typed ID registry. Tier upgrades insert missing sections without renumbering existing sections or rewriting references.
- Keep requirements atomic and testable. Use stable registered prefixes such as `FR-`, `NFR-`, `D-`, and `T-`; declare spec-local IDs in Appendix A and keep external namespaces in `spec.reference_prefixes`.
- Maintain goal-to-requirement-to-test traceability. An approved spec must satisfy its status-aware traceability and Definition-of-Done contract.
- Follow Appendix B's Agent Implementation Contract for execution, verification, prohibited behavior, deviations, and session handoff.
- Run deterministic structure checks before semantic review. Semantic review checks weak language, terminology, atomicity, coherence, and non-goal violations.

## Commands and artifacts

```bash
project-standards spec validate --config .project-standards.yml
project-standards spec lint --config .project-standards.yml --strict
project-standards spec extract FILE SELECTOR
project-standards spec next FILE PREFIX
project-standards spec new PATH --profile TIER --title TITLE --stdout
project-standards spec upgrade FILE --to TIER --stdout
```

`validate`, `lint`, `extract`, and `next` are read-only. `new` and `upgrade` support preview-first operation, refuse unsafe overwrites without explicit force, self-validate generated results, and never rewrite existing prose.

## Boundaries and companions

Specifications use their own `spec_id`/`profile` frontmatter and are independent of Markdown Frontmatter; exclude spec paths from that validator. ADRs own durable architecture decisions, Markdown Tooling owns document formatting, and language standards own implementation code.

## Canonical resources

Use the [standard](README.md), [adoption guide](adopt.md), [templates](templates/), [example](examples/spec.example.md), and [tooling notes](resources/tooling-notes.md).
