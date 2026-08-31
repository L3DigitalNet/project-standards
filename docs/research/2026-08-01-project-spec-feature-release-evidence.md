---
schema_version: '1.1'
id: 'research-gw67x6-project-spec-feature-release-evidence'
title: 'Project Specification feature release evidence'
description: 'Retained evidence for the consolidated Project Standards 5.19.0 release.'
doc_type: 'research'
status: 'active'
created: '2026-08-12'
updated: '2026-08-31'
reviewed: '2026-08-12'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'release'
  - 'validation'
aliases: []
related:
  - 'CHANGELOG.md'
  - 'ROADMAP.md'
  - 'Open-Issue Resolution Program Plan (docs/plans/2026-08-01-open-issue-resolution-program-plan.md, deleted under the completed-plan policy in 923cb63d)'
source:
  - 'https://github.com/L3DigitalNet/project-standards/releases/tag/v5.19.0'
confidence: 'high'
visibility: 'internal'
license: null
---

# Project Specification feature release evidence

## Outcome

Project Standards 5.19.0 was published from `main` commit `127bd3dd67102b9fccee28a6eed02986c7140977`. It consolidates the completed Project Specification conformance and conversion work with the rest of the 5.19 train. All 19 issues cited by the release are closed as completed and carry release references.

## Prepared release

- Preparatory activation and current-reference commit: `dd43c0b8`.
- Mechanical release-preparation commit: `907fc4ca`.
- Integrated contract-correction commit: `297adf3a`.
- Final hosted-ceiling correction and release commit: `127bd3dd`.
- Catalog 5 promoted exactly Agent Handoff 1.12, Markdown Frontmatter 1.11, Markdown Tooling 1.15, and Python Tooling 1.14 while retaining their predecessors.
- The eight reviewed current-reference findings were corrected, and producer reconciliation converged to a no-op on its second preview.
- Project Specification 1.9 is selected and contains both the #62 conformance contract and the #55 preservation-first import workflow.

## Verification

The final direct-local full gate completed successfully on the prepared tree: statics in 0:58, 5,016 ordinary tests in 36:30, 141 compatibility cases in 45:34, five performance tests in 0:42, 90% coverage, and 83:46 total. The candidate validation, package, graph, schema, catalog, projection, and release classification checks also passed; the release classified as minor against v5.18.0.

The first hosted run exposed only cold-runner timing ceilings: observed 8.887 s against 7.5 s and 33.749 s against 30 s. Behavior, deterministic output, ordinary tests, and compatibility were green. Commit `127bd3dd` changed only those two environment-sensitive bounds to 10 s and 40 s; its focused proof was 2 passed in 33.42 s. The final hosted receipts on that exact commit are:

| Workflow                   | Run           | Result  |
| -------------------------- | ------------- | ------- |
| Check                      | `31566383442` | success |
| Coherence                  | `31566383515` | success |
| Format                     | `31566383532` | success |
| Validate project standards | `31566383561` | success |
| Validate standards graph   | `31566383445` | success |

## Publication

- Signed immutable tag `v5.19.0`: tag object `e8460a29d86ee68c748a5f0974d8f2b60fbceee0`.
- Signed moving tag `v5`: tag object `ae60b9e7f5a976e4a882a1bf93495c3b6b2a13b4`.
- Both tags dereference to release commit `127bd3dd`.
- Wheel SHA-256: `134d5abc5a86e5ef63dd2bd9a5844b53807f2d45a8ee930e0e39bc377b31a752`.
- Source distribution SHA-256: `c1605cdecf1a75aac4668ea6e578618fc9e06a2b90a1870dd972b68b298a950b`.
- Freshly downloaded GitHub assets matched both local digests byte for byte.
- The GitHub release is neither draft nor prerelease and is the current 5.x release.

## Issue dispositions and recovery

The GitHub Workflow tool closed #55, #62, #140, #142, #143, #153, #156–#167, and #169 with native completed reasons and `Workflow = Done` after adding links to the published release. The first closeout pass omitted the latter 17 lifecycle transitions; the 2026-08-12 reconciliation corrected them and regenerated the ledger. Full-version tags and published assets are immutable. Recovery from any later documentation or ledger discrepancy must consume these receipts; it must not move the full tag, replace an asset, rerun release qualification, or reopen completed product work merely to repair closeout prose.
