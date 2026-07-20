# Python Coding Standard

This is the Catalog 5 family landing page for the draft reference-only package `python-coding@0.6`. The immutable versioned payload, not this mutable landing page, defines the selected standard.

## Current authority

- [Python Coding 0.6 standard](versions/0.6/README.md) — normative code-shape, boundary, typing, testing, and agent-behavior guidance
- [Python Coding 0.6 agent summary](versions/0.6/agent-summary.md) — compact review and implementation rules
- [Family index](standard.toml) — indexed payload and digest

## Use this standard when

Use Python Coding as reference guidance when designing, implementing, debugging, testing, or reviewing Python code. It prioritizes correctness, explicit boundaries, precise typing, specific failures, behavior-based tests, and measured performance.

[Python Tooling](../python-tooling/README.md) is the companion executable toolchain contract. It owns uv, Ruff, BasedPyright, pytest, coverage, pip-audit, repository scaffolds, and CI.

## Availability

Package `0.6` is `reference-only`: it has no consumer artifacts, configuration options, adoption guide, or executable provider. Read the versioned standard directly. The package is not part of the seven-package consumer default set and cannot be enabled as a normal reconciliation target.

## Released-version errata

The immutable 0.5 tree diagram labels the mutable family `README.md` as `this document`; the authoritative path is `standards/python-coding/versions/0.5/README.md`.

## Legacy boundary

The family root is mutable navigation. The exact `versions/0.6/` payload is the current reference artifact; corrections to its normative content require a new package version rather than edits in place after publication.
