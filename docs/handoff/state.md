# Handoff State

## Current focus

- Project Standards 5.3.1 is published from release commit `50d748c`. Signed `v5.3.1` and moving `v5` tags, the Latest GitHub release, and byte-verified wheel and sdist assets are live; issues #12/#13 remain closed and the default branch has no open Dependabot alerts.
- Project Standards 5.4.0 is prepared for authorized MINOR publication. Python Tooling 1.5 preserves consumer-only checker and pytest keys by managing canonical keys individually, and its declared 1.4→1.5 transition safely retires historical table locks. Markdown Tooling 1.6 code-wraps every configured instruction glob. Issues #14/#15 remain open until the release is live.
- The exact 5.4.0 candidate passes 3,066 ordinary tests, 80 compatibility rows, 5 performance tests, 90% coverage, Ruff, BasedPyright, package graph/schema/projection/catalog and MINOR-classification checks, Prettier, markdownlint, dependency audits, dogfood validation, and Agent Handoff conformance/drift. Publication still requires the release commit on `main`, hosted proof, signed `v5.4.0` and moving `v5` tags, and byte-verified GitHub assets.

## Active incidents

- Engine deletion is blocked until all consumers validate, the final dependency search is clean, and the owner approves.
