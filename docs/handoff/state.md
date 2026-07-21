# Handoff State

## Current focus

- Project Standards 5.3.0 is published from release commit `9dcec77`. Signed `v5.3.0` and moving `v5` tags, the Latest GitHub release, and byte-verified wheel and sdist assets are live; issues #12/#13 are closed and the default branch has no open Dependabot alerts.
- Project Standards 5.3.1 is prepared on `main` as an authorized PATCH release. All 24 findings from `docs/reviews/2026-07-21-code-simplification.md` are implemented; shared package/schema, control-plane, CLI, sync, Agent Handoff, adapter, and spec helpers replace verified duplicates while package, catalog, schema, workflow, and immutable payload bytes remain unchanged.
- The exact 5.3.1 candidate wheel and sdist pass 3,063 ordinary tests, 80 compatibility rows, 5 performance tests, 90% coverage, Ruff, BasedPyright, package graph/schema/projection/catalog and PATCH-classification checks, Prettier, markdownlint, dependency audits, dogfood validation, and Agent Handoff conformance/drift. Publication still requires the signed release commit on `main`, hosted workflow proof, signed `v5.3.1` and moving `v5` tags, and byte-verified GitHub assets.

## Active incidents

- Engine deletion is blocked until all consumers validate, the final dependency search is clean, and the owner approves.
