# Release-Preparation Cleanup Design

**Date:** 2026-07-18

**Status:** owner-approved boundary; ready for cleanup planning

## Goal

Remove release-preparation machinery that is not pertinent to the original Consumer Standards Control Plane specification while preserving useful product behavior, published v5 contracts, and ordinary verification.

## Governing boundary

Keep a surface only when it directly implements or tests an original control-plane requirement, the atomic `.standards/` migration, normal package compatibility, deterministic performance limits, or the published v5 contract. Delete release-only orchestration, duplicated proof, retained process evidence, and documentation whose only purpose was to operate or justify that machinery.

Published `v5.0.0` package payloads remain immutable. The repository may stop selecting optional parallel-coverage behavior, but this cleanup does not rewrite or remove already-published package options.

## Retain

- The atomic migration from `.project-standards.yml` to `.standards/`.
- Core control-plane, package, migration, source/wheel, and composition tests.
- The catalog-derived compatibility matrix and deterministic performance tests.
- The normal Ruff, BasedPyright, pytest/coverage, package, documentation, and dependency gates.
- Generic consumer-owned workflow support and optional coverage settings already shipped as v5 package API.
- Signed release tags, GitHub release assets, release notes, and a concise deployed-release record.

## Delete or simplify

- Delete the disposable release-replay helper, test module, and frozen `release-root` fixture.
- Delete retained release-cut evidence and its self-currency, binary-patch, independent-Git-tree, and replay checks.
- Delete the custom repository test orchestrator and its dedicated tests.
- Replace the custom seven-phase runner with direct CI commands: ordinary coverage tests, compatibility tests, performance tests, coverage report, and dependency audit.
- Stop selecting subprocess/parallel coverage for this repository and remove the `release_replay` marker. Compatibility tests may still use pytest-xdist directly because the matrix is a retained original-spec gate; coverage does not need to span that separate phase.
- Delete the parallel-coverage/release-preparation design, plan, research, and review artifacts after transferring any still-current operational command to canonical documentation.
- Remove active references to deleted machinery and replace release-in-progress status with concise published-release truth.

## Safety constraints

- Do not alter immutable package payload bytes or the published tags.
- Do not remove a test solely because it is slow; remove it only when its asserted behavior is release-process proof duplicated by retained product tests.
- Do not weaken package compatibility, migration safety, source/wheel parity, or performance thresholds.
- Do not introduce replacement infrastructure, new frameworks, or another retained evidence system.

## Verification

Use one bounded verification sequence after cleanup:

1. Confirm deleted symbols and paths have no active references.
2. Run focused workflow/config/package tests.
3. Run the retained ordinary, compatibility, and performance phases once.
4. Run Ruff, BasedPyright, package/schema/projection checks, dependency audits, and applicable documentation checks once.
5. Confirm the cleanup diff contains no published payload changes and no unrelated edits.

## Completion criteria

- Normal CI no longer invokes disposable release replay or retained-evidence currency checks.
- No release-only fixture, helper, custom runner, or process artifact remains active.
- The original control-plane compatibility, migration, source/wheel, and performance obligations remain green.
- Active documentation describes the simple current gate and the completed v5 release.
- No new cleanup framework or permanent audit artifact is introduced beyond this temporary implementation boundary.
