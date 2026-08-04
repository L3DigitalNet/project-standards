---
schema_version: '1.1'
id: 'research-m2rq8v-release-level-classification-evidence'
title: 'Release-Level Classification Verification Evidence'
description: 'EV-010: verification evidence for the landed catalog release-level classification (T30, REQ-902, TC-T30-001) — landed commit, owner policy, focused matrix results, package gates, and disposition of external failures.'
doc_type: 'research'
status: 'active'
created: '2026-08-04'
updated: '2026-08-04'
reviewed: null
owner: 'project-standards'
consumer: 'agent'
tags:
  - 'release-classification'
  - 'verification-evidence'
  - 'versioning'
aliases:
  - 'EV-010'
related:
  - 'docs/plans/2026-08-01-open-issue-resolution-program-plan.md'
  - 'meta/versioning.md'
  - 'docs/adr/adr-0024-catalog-scoped-package-version-channels.md'
source: []
confidence: 'high'
visibility: 'internal'
license: null
---

# Release-Level Classification Verification Evidence

EV-010 for plan `2026-08-01/open-issue-resolution-program` task T30 (verification, REQ-902, TC-T30-001). This record verifies the landed catalog release-level classification without changing implementation; it does not backfill legacy task history.

## Verified state

- Landed implementation commit: `e10083ad2d6059568eb3eb8ac4c7b0c45c80d5c9` ("feat(release): align catalog release classification").
- Committed state verified: `3f310ee122440e46f9d087f36752a8835578b7f2` on `testing`, clean worktree, 2026-08-04.
- Runtime: fresh candidate wheel `project_standards-5.14.0` extracted to `build/wheel-runtime` at the verified HEAD (dogfood contract).

## Owner policy (REQ-902)

A matching tool/catalog major increment is the owner's MAJOR designation. Otherwise a standard-package version advance requires exactly MINOR, and a release without one requires exactly PATCH. Per package ID, a newly introduced package or a newly advertised version above the prior advertised maximum is an advance; internal and reference-only packages count, while older retained history and unadvertised payloads do not. Advertised-version removal, package downgrade, immutable-byte violations, and same-catalog breaking-default promotion remain forbidden.

Same-rule cross-check: `meta/versioning.md` ("Change classification") and ADR 0024 ("Tool release classification") state this rule identically in substance. PASS.

## Focused classification matrix

| Surface | Command | Result |
| --- | --- | --- |
| Release classifier + consistency + CLI matrix | `pytest tests/package_contract/test_release.py test_cli.py test_release_consistency.py` (wheel-runtime `PYTHONPATH`) | 94 passed, exit 0 |
| Rerun after triage (unchanged HEAD) | same selection | 94 passed, exit 0 |

The matrix covers MAJOR designation acceptance, per-package advance computation (new package, new advertised maximum, internal and reference-only inclusion, retained history and unadvertised payload exclusion), exact-level enforcement, and the forbidden-transition set (advertised-version removal, downgrade, immutable-byte violation, same-catalog breaking-default promotion).

## Package gates

| Gate | Result |
| --- | --- |
| `ruff format --check .` | pass (513 files) |
| `ruff check .` | pass |
| `basedpyright` | 0 errors, 0 warnings |
| `tests/package_contract/` full suite | 1147 passed; failures below classified external |
| `scripts/verify.sh` | skipped — owner authorization 2026-08-04 (redundant for this seam; release gate is the catch-all) |

## External failures and disposition

`tests/package_contract/test_python_tooling_reconstruction.py` gate-oracle tests (4 parametrizations) fail because their consumer gates run a real `pip-audit`, which now reports CVE-2026-69247 against `cryptography 49.0.0` (fixed in 50.0.0) — an upstream advisory published after the implementation landed. No failure exercises the classification seam. The same advisory affects this repository's own environment and must be resolved by a dependency advance before the v5.15.0 release gate; the owner accepted release-time handling on 2026-08-04.

## Verdict

TC-T30-001 satisfied: the landed classification matches the owner-approved package-composition policy, the immutable-package and forbidden-transition proofs are preserved and green, and ADR 0024 plus `meta/versioning.md` state the same rule.
